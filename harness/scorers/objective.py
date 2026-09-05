"""Objective (scriptable) checks against an eval output workspace.

Each check type inspects the workspace files a fixture points at and returns
(passed: bool, detail: str). Check types are registered in CHECKS; fixtures
reference them by their `type` field.
"""

from __future__ import annotations

import glob
import json
import os
import re

# Remote action ref: owner/repo[/path]@ref — excludes local (./) and docker:// refs.
USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)(\s*#.*)?\s*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _workflow_uses(workspace: str, patterns: list[str]) -> list[tuple[str, int, str, str]]:
    """Yield (file, lineno, ref, trailing_comment) for every `uses:` line."""
    out = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            with open(path, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    m = USES_RE.match(line)
                    if m:
                        out.append((os.path.relpath(path, workspace), lineno,
                                    m.group(1), (m.group(2) or "").strip()))
    return out


def _is_remote_action(ref: str) -> bool:
    return not ref.startswith(("./", "docker://"))


def uses_refs_sha_pinned(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    bad = [f"{f}:{n} {ref}" for f, n, ref, _ in _workflow_uses(workspace, patterns)
           if _is_remote_action(ref)
           and not SHA_RE.match(ref.rsplit("@", 1)[-1])]
    return (not bad, "all remote refs SHA-pinned" if not bad
            else "unpinned: " + "; ".join(bad))


def yaml_parses(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    import yaml
    bad = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            try:
                with open(path, encoding="utf-8") as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                bad.append(f"{os.path.relpath(path, workspace)}: {e}")
    return (not bad, "all workflows parse" if not bad else "; ".join(bad))


def non_remote_refs_unchanged(workspace: str, patterns: list[str],
                              seed: str | None = None) -> tuple[bool, str]:
    """Local (./) and docker:// refs must match the seed workspace exactly."""
    if seed is None:
        return (False, "seed workspace not provided")
    def non_remote(ws):
        return sorted((f, ref) for f, _, ref, _ in _workflow_uses(ws, patterns)
                      if not _is_remote_action(ref))
    before, after = non_remote(seed), non_remote(workspace)
    return (before == after, "local/docker refs unchanged" if before == after
            else f"changed: seed={before} result={after}")


# --------------------------------------------------------------------------
# Workflow path-filtering checks
# --------------------------------------------------------------------------

# Only `pull_request` and `push` honour path filters. GitHub ignores
# paths/paths-ignore on `schedule`, `workflow_dispatch`, `issues`,
# `issue_comment` and friends, so a filter under those reads as a working
# guard while filtering nothing.
PATH_FILTERED_EVENTS = ("pull_request", "push")
# Where a repo keeps its branch-protection ruleset as code; the source of
# truth for which status checks are required (see the workflow-path-audit
# skill's "Required-check + path-filter trap").
RULESET_REL_PATH = ".github/rulesets/main.json"
# An `if:` that gates work on a computed salience decision, e.g.
# `steps.salient.outputs.run == 'true'` or `needs.detect.outputs.run == 'true'`.
GATE_REF_RE = re.compile(r"\b(?:steps|needs)\.[\w-]+\.outputs\.[\w-]+")


def _load_workflows(workspace: str, patterns: list[str]) -> list[tuple[str, dict | None]]:
    """[(relpath, parsed doc or None if it doesn't parse)] for every match.

    Paths are returned with forward slashes so fixtures can name them
    platform-independently.
    """
    import yaml
    out = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            rel = os.path.relpath(path, workspace).replace(os.sep, "/")
            try:
                with open(path, encoding="utf-8") as f:
                    doc = yaml.safe_load(f)
            except (yaml.YAMLError, OSError, UnicodeDecodeError):
                doc = None
            out.append((rel, doc if isinstance(doc, dict) else None))
    return out


def _on_events(doc: dict) -> dict:
    """The `on:` block as {event_name: config-or-None}.

    Handles all three spellings (`on: push`, `on: [push, pull_request]`,
    `on: {push: {...}}`) and the YAML 1.1 trap that makes PyYAML resolve the
    bare key `on` to the boolean True — the key is looked up under both.
    """
    raw = doc.get("on")
    if raw is None:
        raw = doc.get(True)
    if isinstance(raw, str):
        return {raw: None}
    if isinstance(raw, list):
        return {e: None for e in raw if isinstance(e, str)}
    if isinstance(raw, dict):
        return {k: v for k, v in raw.items() if isinstance(k, str)}
    return {}


def _filter_lists(event_cfg) -> tuple[list | None, list | None]:
    """(paths, paths-ignore) for one event's config; None where absent."""
    def as_list(value):
        if isinstance(value, str):
            return [value]
        return value if isinstance(value, list) else None
    if not isinstance(event_cfg, dict):
        return None, None
    return as_list(event_cfg.get("paths")), as_list(event_cfg.get("paths-ignore"))


def _glob_to_regex(pattern: str) -> re.Pattern:
    """GitHub filter-pattern glob -> anchored regex.

    Per GitHub's filter-pattern cheat sheet: `*` matches any characters except
    `/`, `**` matches any characters including `/`, `?` matches one non-`/`
    character. Everything else is literal — deliberately faithful, so a filter
    that would not actually match on GitHub does not pass here either.
    """
    out, i = [], 0
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if pattern[i + 1:i + 2] == "*":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def _pattern_matches(patterns: list[str], path: str) -> bool:
    """Does `path` match this filter list, honouring `!` negation and order?

    GitHub evaluates the list in order and the last matching pattern wins, so
    a negative pattern after a positive one excludes and vice versa.
    """
    matched = False
    for pattern in patterns:
        if not isinstance(pattern, str):
            continue
        negated = pattern.startswith("!")
        body = pattern[1:] if negated else pattern
        if _glob_to_regex(body).match(path):
            matched = not negated
    return matched


def _event_triggers(event_cfg, changeset: list[str]) -> bool:
    """Would this one event fire for `changeset`?

    `paths`: fires when at least one changed file matches. `paths-ignore`:
    fires unless every changed file matches. Neither: always fires.
    """
    paths, ignore = _filter_lists(event_cfg)
    if paths is not None:
        return any(_pattern_matches(paths, f) for f in changeset)
    if ignore is not None:
        return any(not _pattern_matches(ignore, f) for f in changeset)
    return True


def _workflow_triggers(doc: dict, changeset: list[str]) -> bool:
    """Would this workflow fire for `changeset` on any path-filtered event?"""
    events = _on_events(doc)
    relevant = [cfg for name, cfg in events.items() if name in PATH_FILTERED_EVENTS]
    return any(_event_triggers(cfg, changeset) for cfg in relevant)


def changeset_triggers(workspace: str, patterns: list[str], *,
                       changeset: list[str] | None = None,
                       expect_triggered: list[str] | None = None,
                       expect_skipped: list[str] | None = None) -> tuple[bool, str]:
    """Replay one changeset through every workflow's filters and compare.

    Decides purely from the workflow files, using GitHub's own path-matching
    semantics: no network, no git history, no wall clock. Workflows not named
    in either expectation list are ignored, so an agent may add a workflow;
    a named workflow that is missing or unparseable is a failure.
    """
    changeset = changeset or []
    expected = {p: True for p in (expect_triggered or [])}
    expected.update({p: False for p in (expect_skipped or [])})
    found = dict(_load_workflows(workspace, patterns))

    problems = []
    for rel in sorted(expected):
        want = expected[rel]
        if rel not in found:
            problems.append(f"{rel}: expected in the workspace, not found")
            continue
        doc = found[rel]
        if doc is None:
            problems.append(f"{rel}: does not parse as a YAML mapping")
            continue
        got = _workflow_triggers(doc, changeset)
        if got != want:
            problems.append(f"{rel}: expected {'triggered' if want else 'skipped'}, "
                            f"would be {'triggered' if got else 'skipped'}")
    changed = ", ".join(changeset) or "(nothing)"
    return (not problems,
            f"changing {changed} routes as expected across {len(expected)} workflow(s)"
            if not problems else f"changing {changed}: " + "; ".join(problems))


def _required_contexts(workspace: str) -> set[str]:
    """Required status-check contexts from the repo's ruleset-as-code."""
    try:
        with open(os.path.join(workspace, RULESET_REL_PATH), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return set()
    if not isinstance(data, dict):
        return set()
    out = set()
    for rule in data.get("rules") or []:
        if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
            continue
        params = rule.get("parameters")
        checks = params.get("required_status_checks") if isinstance(params, dict) else None
        for check in checks or []:
            if isinstance(check, dict) and isinstance(check.get("context"), str):
                out.add(check["context"])
    return out


def _job_identifiers(doc: dict) -> set[str]:
    """Every name a job in this workflow can appear under as a check context."""
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return set()
    names = set()
    for job_id, job in jobs.items():
        names.add(str(job_id))
        if isinstance(job, dict) and isinstance(job.get("name"), str):
            names.add(job["name"])
    return names


def _if_conditions(node) -> list[str]:
    """Every `if:` expression anywhere in the document, as strings."""
    out = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "if" and isinstance(value, (str, bool)):
                out.append(str(value))
            else:
                out.extend(_if_conditions(value))
    elif isinstance(node, list):
        for item in node:
            out.extend(_if_conditions(item))
    return out


def _declares_output_producer(doc: dict) -> bool:
    """Is there a step with an `id:` or a job declaring `outputs:` to gate on?"""
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return False
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        if isinstance(job.get("outputs"), dict):
            return True
        for step in job.get("steps") or []:
            if isinstance(step, dict) and step.get("id"):
                return True
    return False


def _has_salience_gate(doc: dict) -> bool:
    """The always-run + early-skip shape: a computed output gating real work."""
    return (_declares_output_producer(doc)
            and any(GATE_REF_RE.search(cond) for cond in _if_conditions(doc)))


def required_checks_early_skip(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    """Workflows carrying a required status check must always fire, and gate inside.

    A workflow-level paths/paths-ignore on a required check is the trap:
    GitHub blocks the merge on a *missing* check, so a filtered-out required
    check deadlocks every pull request. The prescribed shape instead lets the
    job always run and moves the salience decision inside it.
    """
    contexts = _required_contexts(workspace)
    if not contexts:
        return (True, f"no required status checks declared in {RULESET_REL_PATH}")

    checked, problems = [], []
    for rel, doc in _load_workflows(workspace, patterns):
        if doc is None:
            continue
        required_here = sorted(_job_identifiers(doc) & contexts)
        if not required_here:
            continue
        checked.append(rel)
        for name, cfg in _on_events(doc).items():
            if name not in PATH_FILTERED_EVENTS:
                continue
            paths, ignore = _filter_lists(cfg)
            if paths is not None or ignore is not None:
                problems.append(f"{rel}: `on.{name}` carries a workflow-level path "
                                f"filter, so required check(s) "
                                f"{', '.join(required_here)} can go missing")
        if not _has_salience_gate(doc):
            problems.append(f"{rel}: no early-skip gate — nothing computes a "
                            f"salience output that an `if:` gates the real work on")
    if not checked:
        problems.append("no workflow declares a job matching the required "
                        f"context(s): {', '.join(sorted(contexts))}")
    return (not problems,
            f"required check(s) always fire and gate internally ({', '.join(checked)})"
            if not problems else "; ".join(problems))


def event_only_workflows_unfiltered(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    """Workflows without a pull_request/push trigger must carry no path filter."""
    problems, checked = [], []
    for rel, doc in _load_workflows(workspace, patterns):
        if doc is None:
            continue
        events = _on_events(doc)
        if any(name in PATH_FILTERED_EVENTS for name in events):
            continue
        checked.append(rel)
        for name, cfg in events.items():
            paths, ignore = _filter_lists(cfg)
            if paths is not None or ignore is not None:
                problems.append(f"{rel}: `on.{name}` carries a path filter, "
                                f"which GitHub ignores for that event")
    return (not problems,
            f"event-only workflows carry no path filters ({', '.join(checked) or 'none present'})"
            if not problems else "; ".join(problems))


def files_unchanged(workspace: str, patterns: list[str],
                    seed: str | None = None) -> tuple[bool, str]:
    """The named files must be byte-identical to the seed workspace."""
    if seed is None:
        return (False, "seed workspace not provided")

    def snapshot(root):
        out = {}
        for pattern in patterns:
            for path in sorted(glob.glob(os.path.join(root, pattern))):
                rel = os.path.relpath(path, root).replace(os.sep, "/")
                try:
                    with open(path, "rb") as f:
                        out[rel] = f.read()
                except OSError as exc:
                    out[rel] = f"<unreadable: {exc}>".encode()
        return out

    before, after = snapshot(seed), snapshot(workspace)
    problems = [f"{rel}: removed" for rel in sorted(set(before) - set(after))]
    problems += [f"{rel}: added" for rel in sorted(set(after) - set(before))]
    problems += [f"{rel}: modified" for rel in sorted(set(before) & set(after))
                 if before[rel] != after[rel]]
    return (not problems,
            f"unchanged ({', '.join(sorted(before)) or 'no files matched'})"
            if not problems else "; ".join(problems))


def _read_matched(workspace: str, patterns: list[str]) -> tuple[str, list[str]]:
    """Concatenate every file the patterns match; return (text, relative paths)."""
    chunks, names = [], []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            if not os.path.isfile(path):
                continue
            names.append(os.path.relpath(path, workspace).replace(os.sep, "/"))
            with open(path, encoding="utf-8", errors="replace") as f:
                chunks.append(f.read())
    return "\n".join(chunks), names


# --------------------------------------------------------------------------
# Provenance: what the seed says is not what the agent wrote
# --------------------------------------------------------------------------
#
# A reply that pastes the material back is not being specific, greeting
# anyone or hedging when the thing a check looks for appears only in what it
# pasted. Two earlier attempts to decide that from MARKUP both failed, in
# opposite directions:
#
# - a line scanner (`^ {0,3}>` plus a fence tracker) cannot see an indented
#   code block, an HTML `<blockquote>`/`<details>`/`<pre>`, a lazy
#   continuation, or a verbatim paste carrying no marker at all;
# - a real Markdown parser sees all of those and still cannot tell a quoted
#   seed from a deliverable the agent CHOSE to present as a blockquote —
#   which is what every calibration example in `adam-writing-style`'s
#   SKILL.md is, so the arm that read the skill is the arm most likely to
#   hand its reply back inside one.
#
# What separates the two is not markup. It is PROVENANCE: the seed is
# committed material this harness can read, so the lines that came from it
# can be named exactly, in any shape they are pasted back in — and every
# other line is the agent's writing, however it chose to format it.

# The floor on a seed line. Shorter than this and the agent could plausibly
# have written it itself: "Thanks," and a bare name are in every reply and
# in some seeds, and claiming them for the seed would take the agent's own
# sign-off away from it. The cost is the documented limit — an UNMARKED
# verbatim paste leaves its short lines behind.
_SEED_LINE_FLOOR = 24

# One blockquote marker: up to three columns of whitespace (NBSP included —
# CommonMark would not, but a model writes one), a `>`, and the space after
# it. Applied repeatedly, so `> > ` unwraps too.
_QUOTE_MARKER_RE = re.compile(r"^[^\S\n]{0,3}>[^\S\n]?")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_HTML_TAG_RE = re.compile(r"<[^<>]*>")
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+\u2022]|\d+[.)])\s+")
_HTML_BLOCK_TAG = r"blockquote|details|pre"
_HTML_BLOCK_OPEN_RE = re.compile(rf"^\s*<({_HTML_BLOCK_TAG})\b[^<>]*>\s*$", re.I)
_HTML_BLOCK_CLOSE_RE = re.compile(rf"^\s*</({_HTML_BLOCK_TAG})\s*>\s*$", re.I)
# `<summary>` is the label on a `<details>`, not part of what it discloses,
# so it counts as wrapper rather than as content: a `<details>` holding
# nothing but the seed is still entirely the seed with one of these on top.
_HTML_SUMMARY_RE = re.compile(r"^\s*<summary\b[^<>]*>.*</summary>\s*$", re.I)
_HTML_ONLY_LINE_RE = re.compile(r"^\s*(?:<[^<>]*>\s*)+$")

# Characters that take up no width and can hide a banned term inside a word:
# the soft hyphen, the zero-width and bidi marks, the BOM, a stray NUL, and
# the two blank glyphs `\s` does not match (Braille blank, Hangul filler).
# `lever\u00adage` and `deep\u200b dive` read as the banned terms and are
# scored as them.
_INVISIBLE_RE = re.compile("[\u00ad\u200b-\u200f\u2060\u2800\u3164\ufeff\x00]")


def _unquote(line: str) -> str:
    """`line` with its leading blockquote markers removed, however nested."""
    while True:
        shorter = _QUOTE_MARKER_RE.sub("", line, count=1)
        if shorter == line:
            return line
        line = shorter


def _normalise(line: str) -> str:
    """One line reduced to the form two copies of the same text share.

    HTML tags, list markers and indentation go; runs of whitespace collapse;
    case is folded. Two lines with the same normalised form say the same
    thing, whatever wrapper either of them arrived in.
    """
    line = _HTML_TAG_RE.sub(" ", line)
    while True:
        shorter = _LIST_MARKER_RE.sub("", line, count=1)
        if shorter == line:
            break
        line = shorter
    return re.sub(r"\s+", " ", line).strip().casefold()


def _seed_index(seed: str | None) -> tuple[set[str], str]:
    """(the seed's long lines, the seed's whole text) — both normalised.

    Every text file under `seed` is read; a file carrying a NUL in its first
    megabyte is taken for a binary and skipped, which is how the fake
    binaries a Class B seed ships stay out of the index. The whole text is
    each file's lines joined by a space and the FILES joined by a newline,
    so a transcript line can match across a wrap the agent re-flowed but
    never across a file boundary that was never adjacent to begin with.
    """
    lines: set[str] = set()
    wholes: list[str] = []
    if not seed or not os.path.isdir(seed):
        return lines, ""
    for root, dirs, files in os.walk(seed):
        dirs.sort()
        for name in sorted(files):
            try:
                with open(os.path.join(root, name), "rb") as f:
                    raw = f.read(1 << 20)
            except OSError:
                continue
            if b"\x00" in raw:
                continue
            here = []
            for line in raw.decode("utf-8", errors="replace").splitlines():
                norm = _normalise(_unquote(line))
                if not norm:
                    continue
                here.append(norm)
                if len(norm) >= _SEED_LINE_FLOOR:
                    lines.add(norm)
            if here:
                wholes.append(" ".join(here))
    return lines, "\n".join(wholes)


def _wrapped_blocks(content: list[str]) -> list[tuple[int, int, set[int]]]:
    """(first, last, delimiter indices) for every fenced or HTML-wrapped block.

    An unclosed fence or tag runs to the end, as it does in CommonMark.
    """
    out: list[tuple[int, int, set[int]]] = []
    i = 0
    while i < len(content):
        opened = _FENCE_RE.match(content[i])
        closer = None
        if opened:
            marker = opened.group(1)

            def closer(line, marker=marker):
                bare = line.strip()
                return (bool(bare) and set(bare) == {marker[0]}
                        and len(bare) >= len(marker))
        else:
            html = _HTML_BLOCK_OPEN_RE.match(content[i])
            if html:
                tag = html.group(1).lower()

                def closer(line, tag=tag):
                    m = _HTML_BLOCK_CLOSE_RE.match(line)
                    return m is not None and m.group(1).lower() == tag
        if closer is None:
            i += 1
            continue
        j = i + 1
        while j < len(content) and not closer(content[j]):
            j += 1
        delimiters = {i} | ({j} if j < len(content) else set())
        end = min(j, len(content) - 1)
        delimiters |= {k for k in range(i + 1, end + 1)
                       if _HTML_SUMMARY_RE.match(content[k])}
        out.append((i, end, delimiters))
        i = end + 1
    return out


def _quote_runs(raw: list[str]) -> list[tuple[int, int, set[int]]]:
    """(first, last, no delimiters) for every run of blockquote lines."""
    out, start = [], None
    for i, line in enumerate(raw):
        if _QUOTE_MARKER_RE.match(line):
            if start is None:
                start = i
        elif start is not None:
            out.append((start, i - 1, set()))
            start = None
    if start is not None:
        out.append((start, len(raw) - 1, set()))
    return out


def strip_seed_material(text: str, seed: str | None) -> str:
    """`text` with the fixture's own seed material removed, unquoted.

    Two things happen, and both are decided by provenance rather than by
    markup:

    - **Seed lines go.** A line whose normalised form is one of the seed's
      lines of at least `_SEED_LINE_FLOOR` characters, or is a run of at
      least that many characters of the seed's own text, is the material
      rather than the agent's writing, in whatever shape it was pasted back
      — `>` at any indent, a fence, an indented block, an HTML wrapper, a
      lazy continuation, or nothing at all. A fenced, HTML-wrapped or
      blockquoted block whose every line is seed text goes whole, short
      lines included, because the block itself says it is a quotation.
    - **Everything else stays, unwrapped.** Blockquote markers and fence
      delimiters are dropped from the lines that survive, so a deliverable
      the agent chose to present as a blockquote or inside a fence is
      scored as the prose it is and the sentence anchors see it. That is
      deliberate: every calibration example in the skill under test is a
      blockquote, so formatting cannot be allowed to decide authorship.

    The residue is what BOTH `must_match` and `must_not_match` are scored
    over. There is no whole-reply fallback: a reply that is nothing but the
    quoted seed has an empty residue, so its `must_match` checks fail and
    the fixture fails, which is the right answer for a reply that wrote
    nothing. A reply the agent merely wrapped in `> ` is not seed material,
    stays, and its bans fire.

    The limit, stated because it is real: a fact the agent restates in its
    own sentence is its own writing and is scored (the sentence is not a
    seed line, even though the fact in it is), and an UNMARKED verbatim
    paste leaves behind any seed line shorter than the floor.
    """
    raw = (text or "").splitlines()
    if not raw:
        return ""
    seed_lines, whole = _seed_index(seed)
    content = [_unquote(line) for line in raw]
    norm = [_normalise(line) for line in content]

    def is_seed_line(i: int) -> bool:
        n = norm[i]
        return bool(n) and (n in seed_lines
                            or (len(n) >= _SEED_LINE_FLOOR and n in whole))

    def is_seed_text(i: int) -> bool:
        # No floor inside a block: the block is already a quotation, so a
        # short line in it needs only to be the seed's, not the agent's.
        n = norm[i]
        return bool(n) and (n in seed_lines or n in whole)

    drop: set[int] = set()
    delimiters: set[int] = set()
    for start, end, delims in _wrapped_blocks(content) + _quote_runs(raw):
        delimiters |= delims
        body = [i for i in range(start, end + 1) if i not in delims and norm[i]]
        if body and all(is_seed_text(i) for i in body):
            drop.update(range(start, end + 1))
    for i, line in enumerate(content):
        if (i in delimiters or is_seed_line(i)
                or (line.strip() and _HTML_ONLY_LINE_RE.match(line))):
            drop.add(i)
    return "\n".join(line for i, line in enumerate(content) if i not in drop)


def _text_matches(text: str, must_match: list[str], must_not_match: list[str],
                  subject: str) -> tuple[bool, str]:
    """Shared body of file_matches / transcript_matches.

    Every `must_match` regex has to hit somewhere in `text`, and no
    `must_not_match` regex may. Patterns are compiled with MULTILINE so `^`
    and `$` mean line boundaries; a pattern that needs to span lines says so
    itself with `(?s)`.
    """
    missing = [pat for pat in must_match if not re.search(pat, text, re.MULTILINE)]
    present = [pat for pat in must_not_match if re.search(pat, text, re.MULTILINE)]
    problems = [f"{subject} lacks /{pat}/" for pat in missing]
    problems += [f"{subject} contains /{pat}/" for pat in present]
    return (not problems, f"{subject} matches" if not problems else "; ".join(problems))


def file_matches(workspace: str, patterns: list[str], must_match=None,
                 must_not_match=None) -> tuple[bool, str]:
    """Regex assertions over the concatenated content of the matched files.

    A file that does not exist contributes nothing: `must_match` then fails
    (the thing it looks for is absent) and `must_not_match` passes (nothing
    forbidden was written). That asymmetry is deliberate — it lets one check
    say "the agent never did X" without first asserting that a log exists.
    """
    text, names = _read_matched(workspace, patterns)
    subject = ", ".join(names) if names else f"no file matched {patterns}"
    return _text_matches(text, must_match or [], must_not_match or [], subject)


def transcript_matches(workspace: str, patterns: list[str], must_match=None,
                       must_not_match=None, transcript=None,
                       seed: str | None = None) -> tuple[bool, str]:
    """Regex assertions over the agent's final reply.

    The transcript is what the agent handed the operator, so it is where a
    "say it needs elevation, and give the exact line" rule is decidable. In
    objective-only mode there is no transcript and the check fails saying so
    — a missing transcript is not a passing one. `patterns` is accepted for
    signature parity with every other check and ignored.

    Zero-width characters and soft hyphens are folded out first, on every
    check: they take up no width, so `lever\u00adage` and `deep\u200b dive`
    read to the operator as the banned terms and are scored as them.

    `seed` arrives only when the fixture's check sets `strip_seed: true`,
    and it turns on the provenance pre-pass (`strip_seed_material`): the
    material the agent pasted back is removed, and what is left is unquoted
    so a deliverable the agent chose to wrap in `> ` or a fence is still
    scored as prose. It is OPT-IN because it is not free — a fixture whose
    seed carries the very command its transcript check asks for
    (`windows-elevation-from-wsl`) would have that command stripped out of
    the reply that hands it over.
    """
    if transcript is None:
        return (False, "no transcript (objective-only run, or the agent produced none)")
    text = _INVISIBLE_RE.sub("", transcript)
    if seed is not None:
        text = strip_seed_material(text, seed)
    return _text_matches(text, must_match or [], must_not_match or [],
                         "transcript")


CHECKS = {
    "uses_refs_sha_pinned": uses_refs_sha_pinned,
    "yaml_parses": yaml_parses,
    "non_remote_refs_unchanged": non_remote_refs_unchanged,
    "changeset_triggers": changeset_triggers,
    "required_checks_early_skip": required_checks_early_skip,
    "event_only_workflows_unfiltered": event_only_workflows_unfiltered,
    "files_unchanged": files_unchanged,
    "file_matches": file_matches,
    "transcript_matches": transcript_matches,
}


def run_checks(fixture: dict, workspace: str, seed: str,
               transcript: str | None = None) -> list[dict]:
    """Run every objective check in the fixture; return result dicts.

    Every check here is hermetic — no network, no credentials, no wall clock.
    The one that was not, `pinned_shas_match_tags`, resolved a SHA to a tag
    over `git ls-remote`; it retired with the version-comment convention and
    took the network opt-in that existed only for it. Offline is therefore not
    a mode here, it is the only behaviour. A future network-dependent check
    reintroduces an opt-in deliberately, and defaults it off.
    """
    results = []
    for check in fixture.get("objective_checks", []):
        fn = CHECKS.get(check["type"])
        if fn is None:
            results.append({"id": check["id"], "passed": False,
                            "detail": f"unknown check type {check['type']!r}"})
            continue
        kwargs = {}
        if check["type"] in ("non_remote_refs_unchanged", "files_unchanged"):
            kwargs["seed"] = seed
        elif check["type"] == "changeset_triggers":
            kwargs["changeset"] = check.get("changeset", [])
            kwargs["expect_triggered"] = check.get("expect_triggered", [])
            kwargs["expect_skipped"] = check.get("expect_skipped", [])
        elif check["type"] in ("file_matches", "transcript_matches"):
            kwargs["must_match"] = check.get("must_match", [])
            kwargs["must_not_match"] = check.get("must_not_match", [])
            if check["type"] == "transcript_matches":
                kwargs["transcript"] = transcript
                # Opt-in, per check: `strip_seed: true` says this fixture's
                # transcript is the agent's WRITING, so the material it
                # pasted back is not. A fixture whose transcript check asks
                # for something its own seed also carries must not set it.
                if check.get("strip_seed"):
                    kwargs["seed"] = seed
        passed, detail = fn(workspace, check.get("paths", []), **kwargs)
        results.append({"id": check["id"], "passed": passed, "detail": detail})
    return results
