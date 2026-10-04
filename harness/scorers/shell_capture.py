"""Reject the concatenated dispatch/discovery command substitution via a shell AST."""

from __future__ import annotations

import glob
from pathlib import Path


def _nodes(node):
    """Walk bashlex's node children, including substitution commands."""
    import bashlex
    yield node
    for value in vars(node).values():
        if isinstance(value, bashlex.ast.node):
            yield from _nodes(value)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, bashlex.ast.node):
                    yield from _nodes(child)


def _command_words(node):
    return [part.word for part in getattr(node, 'parts', []) if part.kind == 'word']


def _unsafe_capture(trees):
    for tree in trees:
        for substitution in _nodes(tree):
            if substitution.kind != 'commandsubstitution':
                continue
            for sequence in _nodes(substitution.command):
                if sequence.kind != 'list':
                    continue
                # A list may contain unrelated semicolon-separated chains;
                # inspect each &&-connected group independently.
                group = []
                for part in sequence.parts + [None]:
                    if part is not None and part.kind == 'operator' and part.op == '&&':
                        continue
                    if part is not None and part.kind != 'operator':
                        # Preserve the boundary of each && operand. Commands
                        # in mutually exclusive branches or a semicolon list
                        # within ONE operand do not form a cross-operand chain.
                        group.append([_command_words(node) for node in _nodes(part)
                                      if node.kind == 'command'])
                        continue
                    dispatch = next((i for i, commands in enumerate(group)
                                     if any(words[:3] == ['gh', 'workflow', 'run']
                                            for words in commands)), None)
                    if dispatch is not None and any(words[:3] == ['gh', 'run', 'list']
                                                    for commands in group[dispatch + 1:]
                                                    for words in commands):
                        return True
                    group = []
    return False


def _substitutions(text):
    """Lexically delimit prose's $(...) examples; the parser decides shape.

    Markdown text is not shell. Delimiting balanced parentheses and quotes
    only extracts candidate examples; it never decides which commands or
    operators a candidate contains.
    """
    offset = 0
    while (start := text.find('$(', offset)) >= 0:
        depth, quote, escape, cursor = 1, None, False, start + 2
        while cursor < len(text) and depth:
            char = text[cursor]
            if escape:
                escape = False
            elif char == '\\' and quote != "'":
                escape = True
            elif quote:
                if char == quote:
                    quote = None
            elif char in "'\"":
                quote = char
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            cursor += 1
        yield 'capture=' + text[start:cursor]
        offset = cursor


def _transcript_shell(transcript):
    from markdown_it import MarkdownIt
    for token in MarkdownIt().parse(transcript):
        if token.type in {'fence', 'code_block'}:
            if not token.info or token.info.split()[0].lower() in {'bash', 'sh', 'shell', 'zsh'}:
                yield token.content
        elif token.type == 'inline':
            for child in token.children or []:
                if child.type == 'code_inline':
                    yield child.content
                elif child.type == 'text':
                    yield from _substitutions(child.content)


def shell_capture_safe(workspace: str, patterns: list[str], source='files',
                       transcript=None) -> tuple[bool, str]:
    """No dispatch followed by discovery in the same && capture.

    Missing scripts or reply pass this negative check. Unsupported shell
    syntax fails closed rather than treating a parser failure as safety.
    Transcript is the supplied final reply, not historical tool requests.
    bashlex 0.18 also rejects some valid single-line && captures; these fail
    closed. A newline before the closing parenthesis avoids that limitation.
    """
    import bashlex
    if source not in {'files', 'transcript'}:
        raise ValueError('shell_capture_safe source must be files or transcript')
    if source == 'transcript':
        candidates = [('reply shell example', text)
                      for text in _transcript_shell(transcript or '')]
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
                        candidates.append((str(relative), path.read_text()))
                except (OSError, UnicodeError, ValueError):
                    return False, 'shell candidate could not be read safely'
    for name, text in candidates:
        try:
            trees = bashlex.parse(text + "\n:\n")
        except (bashlex.errors.ParsingError, NotImplementedError):
            return False, f'{name}: shell syntax could not be verified'
        if _unsafe_capture(trees):
            return False, f'{name}: dispatch and discovery share an && command substitution'
    return True, 'no concatenated dispatch/discovery capture'
