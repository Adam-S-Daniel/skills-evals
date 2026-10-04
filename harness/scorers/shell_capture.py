"""Reject dispatch/discovery captures using lexical extraction and a shell AST."""

from __future__ import annotations

import glob
from pathlib import Path
import re
import shlex


def _children(node):
    import bashlex
    for value in vars(node).values():
        if isinstance(value, bashlex.ast.node):
            yield value
        elif isinstance(value, list):
            yield from (child for child in value if isinstance(child, bashlex.ast.node))


def _command_words(node):
    return [part.word for part in getattr(node, 'parts', []) if part.kind == 'word']


def _sequence(nodes, states):
    for node in nodes:
        states, unsafe = _flow(node, states)
        if unsafe:
            return states, True
    return states, False


def _flow(node, states):
    """Track dispatch along AST paths without joining exclusive if branches."""
    if node.kind == 'command':
        states, unsafe = _sequence(_children(node), states)
        if unsafe:
            return states, True
        words = _command_words(node)
        if words[:3] == ['gh', 'run', 'list'] and True in states:
            return states, True
        if words[:3] == ['gh', 'workflow', 'run']:
            return {True}, False
        return states, False
    if node.kind == 'if':
        segments = []
        for part in node.parts:
            if part.kind == 'reservedword':
                segments.append((part.word, []))
            elif segments:
                segments[-1][1].append(part)
        outputs = set()
        remaining = states
        has_else = False
        for keyword, parts in segments:
            if keyword in {'if', 'elif'}:
                remaining, unsafe = _sequence(parts, remaining)
            elif keyword in {'then', 'else'}:
                branch, unsafe = _sequence(parts, remaining)
                outputs.update(branch)
                has_else |= keyword == 'else'
            else:
                continue
            if unsafe:
                return states, True
        return outputs | (set() if has_else else remaining), False
    return _sequence(_children(node), states)


def _unsafe_capture(trees):
    return _sequence(trees, {False})[1]


def _mentions_dispatch(text):
    # This is a lexical token check only, used when an AST cannot be built.
    # Parsed command shape is always decided by _flow, never by this token.
    if re.search(r'(?<![A-Za-z0-9_])gh\s+workflow\s+run(?![A-Za-z0-9_])', text):
        return True
    lexer = shlex.shlex(text, posix=True, punctuation_chars=';&|()<>')
    lexer.whitespace_split = True
    tokens = []
    try:
        for token in lexer:
            tokens = (tokens + [token])[-3:]
            if tokens == ['gh', 'workflow', 'run']:
                return True
    except ValueError:
        pass
    return False


def _substitutions(text, *, prose=False):
    """Extract active substitution bodies, including nested $() and backticks.

    Quotes, escaped characters, comments and heredocs delimit lexical candidates.
    Arithmetic is traversed for nested substitutions but never parsed itself.
    Prose has no surrounding shell quote state; candidate bodies still do.
    """
    candidates = []

    def scan(cursor, stop=None, depth=1, shell=True, limit=None):
        quote = None
        ansi_quote = False
        heredocs = []
        cases = []
        command_start = True
        limit = len(text) if limit is None else limit
        while cursor < limit:
            char = text[cursor]
            if shell and quote == "'":
                if ansi_quote and char == '\\':
                    cursor += 2
                    continue
                if char == quote:
                    quote = None
                    ansi_quote = False
                    if cases and cases[-1] == 'subject':
                        cases[-1] = 'await-in'
                cursor += 1
                continue
            if shell and quote is None and text.startswith("$'", cursor):
                quote, ansi_quote = "'", True
                command_start = False
                cursor += 2
                continue
            if char == '\\':
                command_start = False
                cursor += 2
                continue
            if shell and quote is None and text.startswith('<<', cursor) and not text.startswith('<<<', cursor):
                start = cursor + 2
                strip_tabs = start < limit and text[start] == '-'
                start += int(strip_tabs)
                while start < limit and text[start] in ' \t':
                    start += 1
                end, delimiter_quote = start, None
                while end < limit:
                    char = text[end]
                    if char == '\\' and delimiter_quote != "'":
                        end += 2
                        continue
                    if delimiter_quote:
                        if char == delimiter_quote:
                            delimiter_quote = None
                    elif char in "'\"":
                        delimiter_quote = char
                    elif char in ' \t\r\n;|&()<>':
                        break
                    end += 1
                raw = text[start:end]
                try:
                    words = shlex.split(raw)
                except ValueError:
                    words = []
                if len(words) == 1:
                    quoted = any(char in raw for char in "'\"\\")
                    heredocs.append((words[0], quoted, strip_tabs))
                    cursor = end
                    continue
            if shell and quote is None and char == '\n' and heredocs:
                cursor += 1
                for delimiter, quoted, strip_tabs in heredocs:
                    body_start = cursor
                    while cursor < limit:
                        newline = text.find('\n', cursor, limit)
                        end = limit if newline < 0 else newline
                        line = text[cursor:end]
                        if (line.lstrip('\t') if strip_tabs else line) == delimiter:
                            break
                        cursor = end + (newline >= 0)
                    if not quoted:
                        scan(body_start, shell=False, limit=cursor)
                    if cursor < limit:
                        newline = text.find('\n', cursor, limit)
                        cursor = limit if newline < 0 else newline + 1
                heredocs = []
                command_start = True
                continue
            if stop == '`' and char == '`' and quote is None:
                return cursor + 1, True
            if shell and quote is None:
                # Case pattern ')' is a lexical delimiter of an arm, not of
                # its enclosing substitution. bashlex cannot parse case, so
                # preserve its complete body for the fail-closed token check.
                if cases and cases[-1] == 'body' and text.startswith(';;', cursor):
                    cases[-1] = 'pattern'
                    cursor += 2
                    continue
                if char.isalpha() and (cursor == 0 or text[cursor - 1] in ' \t\r\n;|&()<>'):
                    end = cursor
                    while end < limit and (text[end].isalnum() or text[end] == '_'):
                        end += 1
                    if end == limit or text[end] in ' \t\r\n;|&()<>':
                        word = text[cursor:end]
                        if command_start and word == 'case':
                            cases.append('subject')
                            command_start = False
                        elif cases and cases[-1] == 'subject':
                            cases[-1] = 'await-in'
                            command_start = False
                        elif word == 'in' and cases and cases[-1] == 'await-in':
                            cases[-1] = 'pattern'
                            command_start = False
                        elif command_start and word == 'esac' and cases:
                            cases.pop()
                            command_start = False
                        elif command_start and word in {'then', 'do', 'else', 'elif', 'if', 'while', 'until', '!'}:
                            command_start = True
                        else:
                            command_start = False
                        cursor = end
                        continue
                if cases and cases[-1] == 'pattern' and char == ')':
                    cases[-1] = 'body'
                    command_start = True
                    cursor += 1
                    continue
            if shell and quote is None and cases and cases[-1] == 'subject' and char == '$' and not text.startswith('$(', cursor):
                cases[-1] = 'await-in'
            if text.startswith('$(', cursor):
                arithmetic = text.startswith('$((', cursor)
                start = cursor + (3 if arithmetic else 2)
                end, complete = scan(start, ')', 2 if arithmetic else 1, limit=limit)
                if not arithmetic:
                    candidates.append((text[start:end - 1 if complete else end], complete))
                cursor = end
                if shell and quote is None and cases and cases[-1] == 'subject':
                    cases[-1] = 'await-in'
                command_start = False
                continue
            if char == '`':
                start = cursor + 1
                end, complete = scan(start, '`', limit=limit)
                body = text[start:end - 1 if complete else end]
                # Traditional nested backticks escape their delimiters in
                # the outer capture; parse the body after that lexical layer.
                candidates.append((body.replace('\\`', '`'), complete))
                cursor = end
                continue
            if shell and quote:
                if char == quote:
                    quote = None
                    if cases and cases[-1] == 'subject':
                        cases[-1] = 'await-in'
            elif shell and char in "'\"":
                quote = char
                command_start = False
            elif shell and char == '#' and (cursor == 0 or text[cursor - 1] in ' \t\r\n;|&()<>'):
                newline = text.find('\n', cursor, limit)
                cursor = limit if newline < 0 else newline + 1
                command_start = True
                continue
            elif stop == ')' and char == '(':
                depth += 1
            elif stop == ')' and char == ')':
                depth -= 1
                if not depth:
                    return cursor + 1, True
            if shell and quote is None and char in ';\n|&(':
                command_start = True
            cursor += 1
        return limit, stop is None

    scan(0, shell=not prose)
    return candidates


def _transcript_shell(transcript):
    from markdown_it import MarkdownIt
    for token in MarkdownIt().parse(transcript):
        if token.type in {'fence', 'code_block'}:
            label = token.info.split()[0].lower() if token.info else ''
            if label in {'bash', 'sh', 'shell', 'console', 'zsh'} or (not label and _mentions_dispatch(token.content)):
                yield token.content, False
        elif token.type == 'inline':
            for child in token.children or []:
                if child.type == 'code_inline' and _mentions_dispatch(child.content):
                    yield child.content, False
                elif child.type == 'text' and _mentions_dispatch(child.content):
                    yield child.content, True


def shell_capture_safe(workspace: str, patterns: list[str], source='files',
                       transcript=None) -> tuple[bool, str]:
    """Reject dispatch followed by discovery in one command substitution.

    Only substitution bodies reach bashlex 0.18. Unsupported syntax elsewhere
    in a script or prose does not invalidate its independent captures. A body
    with a dispatch token that cannot be parsed fails closed.
    """
    import bashlex
    if source not in {'files', 'transcript'}:
        raise ValueError('shell_capture_safe source must be files or transcript')
    if source == 'transcript':
        candidates = [('reply shell example', text, prose)
                      for text, prose in _transcript_shell(transcript or '')]
    else:
        candidates = []
        root = Path(workspace).resolve()
        for pattern in patterns:
            for hit in glob.iglob(str(root / pattern), recursive=True, include_hidden=True):
                path = Path(hit)
                try:
                    relative = path.relative_to(root)
                    if '.git' in relative.parts:
                        continue
                    if not path.resolve().is_relative_to(root):
                        return False, 'shell candidate escapes workspace'
                    if path.is_file():
                        candidates.append((str(relative), path.read_text(), False))
                except (OSError, UnicodeError, ValueError):
                    return False, 'shell candidate could not be read safely'
    for name, text, prose in candidates:
        for body, complete in _substitutions(text, prose=prose):
            try:
                if not complete:
                    raise bashlex.errors.ParsingError('incomplete substitution', body, len(body))
                trees = bashlex.parse(body + '\n')
            except (bashlex.errors.ParsingError, NotImplementedError):
                if _mentions_dispatch(body):
                    return False, f'{name}: shell syntax could not be verified'
                continue
            if _unsafe_capture(trees):
                return False, f'{name}: dispatch and discovery share a command substitution'
    return True, 'no concatenated dispatch/discovery capture'
