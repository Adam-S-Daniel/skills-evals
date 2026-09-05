"""Objective (scriptable) checks against an eval output workspace.

Each check type inspects the workspace files a fixture points at and returns
(passed: bool, detail: str). Check types are registered in CHECKS; fixtures
reference them by their `type` field.
"""

from __future__ import annotations

import fnmatch
import glob
import hashlib
import json
import os
import re
from collections import Counter

# Remote action ref: owner/repo[/path]@ref — excludes local (./) and docker:// refs.
USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)(\s*#.*)?\s*$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


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


def uses_refs_sha_pinned(workspace: str, patterns: list[str],
                         platform_prefix: str | None = None) -> tuple[bool, str]:
    """Every remote (non-local, non-docker) `uses:` ref is a bare full
    40-character commit SHA — never a tag, an abbreviated SHA, or anything
    else.

    Locates each `uses:` value with a real YAML parse (`_uses_value_nodes`,
    the same composed-tree walk `pin_comment_absent` uses) and tests the
    node's own `.value` against `SHA_RE` — never a line regex, which a
    quoted pin (the quote characters land inside the captured "ref") or a
    `uses:`-shaped line inside a `run: |` block scalar (prose, not a mapping
    key) both defeat.

    `platform_prefix`, when given, skips a cross-repo reference to this
    account's own platform repo (case-folded, matching `platform_refs_on_tag`'s
    own comparison): that ref is meant to stay on its release TAG, not a
    SHA, so scoring it here would fail the one thing the carve-out requires.
    `platform_refs_on_tag` is what actually checks such a ref, in whichever
    files the fixture points it at.
    """
    import yaml
    bad = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                text = f.read()
            try:
                doc = yaml.compose(text, Loader=yaml.SafeLoader)
            except yaml.YAMLError:
                continue  # yaml_parses reports this; nothing to check here
            if doc is None:
                continue
            rel = os.path.relpath(path, workspace)
            for value_node in _uses_value_nodes(doc):
                ref = value_node.value
                if not isinstance(ref, str) or not _is_remote_action(ref):
                    continue
                if (platform_prefix
                        and platform_prefix.casefold() in ref.casefold()):
                    continue  # platform_refs_on_tag's business, not ours
                if not SHA_RE.match(ref.rsplit("@", 1)[-1]):
                    lineno = value_node.start_mark.line + 1
                    bad.append(f"{rel}:{lineno} {ref}")
    return (not bad, "all remote refs SHA-pinned" if not bad
            else "unpinned: " + "; ".join(bad))


def _mapping_value_nodes(node, key: str, _seen: set | None = None) -> list:
    """Every YAML *value* Node bound to a literal `key` mapping key, found by
    walking the composed document tree — never by scanning the raw text for
    the key's name, which could also match inside another field or a
    comment. Recurses into every Mapping/Sequence node so it finds `key`
    wherever it appears: a step, a job-level reusable-workflow call, a
    composite action's `runs.steps`, or a `with:` block.

    `_seen` tracks visited nodes by `id()`: `yaml.compose` resolves an alias
    (`*x`) to the SAME node object anchored by `&x`, so a self-referential
    anchor (`a: &x\n  b: *x`) makes a node its own descendant — an unguarded
    walk recurses forever. A node already visited contributes nothing new.
    """
    import yaml
    if _seen is None:
        _seen = set()
    node_id = id(node)
    if node_id in _seen:
        return []
    _seen.add(node_id)
    out = []
    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            if isinstance(key_node, yaml.ScalarNode) and key_node.value == key:
                out.append(value_node)
            out.extend(_mapping_value_nodes(key_node, key, _seen))
            out.extend(_mapping_value_nodes(value_node, key, _seen))
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            out.extend(_mapping_value_nodes(item, key, _seen))
    return out


def _uses_value_nodes(node, _seen: set | None = None) -> list:
    """Every YAML *value* Node bound to a literal `uses:` mapping key — see
    `_mapping_value_nodes`."""
    return _mapping_value_nodes(node, "uses", _seen)


def _line_has_trailing_comment(line: str, after_column: int) -> bool:
    """Does `line` carry a `#` comment starting at or after `after_column`?

    `after_column` is the value node's own `end_mark.column` — the point
    where its textual representation (quotes included, for a quoted scalar)
    actually ends. Anchoring the search there, rather than scanning the
    whole line from its start, is what keeps a `#` embedded INSIDE a quoted
    value (e.g. `uses: "ref # not a comment"`) from being mistaken for a
    trailing comment: that `#` sits before the value's own end_mark, so it is
    never examined. YAML still requires the character before a genuine
    comment-opening `#` to be whitespace or the start of the line.
    """
    idx = line.find("#", after_column)
    return idx != -1 and (idx == 0 or line[idx - 1] in " \t")


def pin_comment_absent(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    """No `uses:` ref carries a trailing version comment.

    Rule 2 (reversed 2026-08-20 — see cms-platform's github-actions-sha-pinning
    skill): a `uses:` line ends at its ref, third-party SHA or cms-platform
    tag alike, with nothing after it. Locates each `uses:` node with a real
    YAML parse (`yaml.compose`, which keeps line numbers) rather than a regex
    over the file, then reads only THAT line's raw text to decide whether a
    comment trails it. A regex over the whole file can't reliably tell a
    `uses:` value's line from any other, and mistaking one for the other is
    exactly the class of bug locating the node structurally first avoids.

    Two known limits, both a consequence of inspecting only the value node's
    own line:

    - A version comment moved to the line ABOVE the step (rather than
      trailing the `uses:` line itself) is invisible — nothing here looks at
      any line but the value node's own.
    - A comment trailing a YAML ALIAS (`*x`) is invisible: `yaml.compose`
      resolves the alias to the SAME Node object as its anchor (`&x`), so
      `value_node.end_mark` reports the ANCHOR's line, not the alias
      occurrence's — a comment on the alias's own line is checked against
      the wrong line entirely.

    Both are the kind of intent a strict text match can't see either way;
    the fixture's `comment_removal` judge dimension covers them instead of
    this scoring them structurally.
    """
    import yaml
    bad = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                text = f.read()
            try:
                doc = yaml.compose(text, Loader=yaml.SafeLoader)
            except yaml.YAMLError:
                continue  # yaml_parses reports this; nothing to check here
            if doc is None:
                continue
            lines = text.splitlines()
            rel = os.path.relpath(path, workspace)
            for value_node in _uses_value_nodes(doc):
                lineno = value_node.end_mark.line
                if lineno >= len(lines):
                    continue
                raw = lines[lineno]
                if _line_has_trailing_comment(raw, value_node.end_mark.column):
                    bad.append(f"{rel}:{lineno + 1} {raw.strip()}")
    return (not bad, "no trailing comment on any uses: pin" if not bad
            else "version comment present: " + "; ".join(bad))


def platform_refs_on_tag(workspace: str, patterns: list[str],
                         platform_prefix: str | None = None,
                         tag: str | None = None,
                         min_refs: int | None = None) -> tuple[bool, str]:
    """The carve-out, checked structurally: every `uses:` value node whose
    leaf names `platform_prefix` (a cross-repo reference to this account's
    own cms-platform) must carry `@<tag>` exactly — never a SHA, never a
    different tag — and every `platform_ref:` value node must equal `tag`
    too.

    Replaces a `file_matches` must_match/must_not_match regex pair that
    decided two independent YAML values by scanning raw concatenated text: a
    `# was platform_ref: v0.1.104` comment left above a drifted
    `platform_ref: v0.1.99` line satisfied `must_match` on the comment alone,
    and `platform_ref: "v0.1.104"` (quoted) or `platform_ref:  v0.1.104`
    (extra space) defeated the regex's exact literal spacing even though both
    are the correct value. This instead composes the tree (`yaml.compose`,
    the same pass `_mapping_value_nodes` uses) and compares each leaf node's
    own parsed `.value` against `tag` lexically — a comment is not a node,
    and YAML quoting/whitespace around a scalar is not part of its value.

    `min_refs`, when given, restores the presence half a `must_match` regex
    used to supply for free: without it, this check asserts only "every
    platform ref FOUND is on the tag", which passes vacuously if the ref was
    deleted, routed around (a local `./` swap), or never there in the first
    place. `min_refs` counts platform `uses:` value nodes only — not
    `platform_ref:` nodes, which are a separate leg entirely — so it stays a
    structural count, not a `files_unchanged`-style presence guard: an
    edited-but-still-correct file with the same ref count still passes. The
    count is of DISTINCT `(file, line)` locations, not of node visits: an
    anchored `uses:` value referenced again elsewhere via a YAML alias
    (`*x`) is the same physical ref and must not inflate the count — see
    the de-duplication note below, which applies here too.

    The count can also undershoot for a reason that has nothing to do with
    how many platform refs exist: a file that fails to parse, or one with no
    content at all, contributes zero ref nodes and silently lowers the
    count exactly as a genuinely deleted ref would — the detail names only
    the resulting number, not which file (if any) could not be read.

    The prefix match is case-folded on both sides: a GitHub `owner/repo`
    path is case-insensitive, so `adam-s-daniel/cms-platform/...` is the same
    cross-repo reference as `Adam-S-Daniel/cms-platform/...` and must not go
    unrecognised (and uncounted) merely by casing.

    An anchored/aliased `platform_ref:` (or `uses:`) is reported once, at the
    anchor's own line, not once per alias occurrence: `yaml.compose` resolves
    an alias to the SAME Node object as its anchor, so a value used via two
    aliases is visited twice but is one problem, not two — the same
    consequence `pin_comment_absent` documents for a trailing comment on an
    alias's own line. `bad` is de-duplicated before being joined for this
    reason.

    A `platform_ref:` key can also bind to a MappingNode rather than a
    scalar — a composite action DECLARING an input named `platform_ref`
    (`inputs: {platform_ref: {description: ..., required: true}}`) uses the
    same key for something that is not a version literal at all. Only a
    `yaml.ScalarNode` bound to that key is a value to compare; anything else
    is skipped rather than compared (and never counted — only `uses:` nodes
    feed `min_refs`).
    """
    import yaml
    if not platform_prefix or not tag:
        return (False, "platform_prefix/tag not configured")
    bad = []
    ref_locations: set[tuple[str, int]] = set()
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                text = f.read()
            try:
                doc = yaml.compose(text, Loader=yaml.SafeLoader)
            except yaml.YAMLError:
                continue  # yaml_parses reports this; nothing to check here
            if doc is None:
                continue
            rel = os.path.relpath(path, workspace)
            for value_node in _uses_value_nodes(doc):
                ref = value_node.value
                if (not isinstance(ref, str)
                        or platform_prefix.casefold() not in ref.casefold()):
                    continue
                ref_locations.add((rel, value_node.start_mark.line))
                expected = ref.rsplit("@", 1)[0] + "@" + tag
                if ref != expected:
                    lineno = value_node.start_mark.line + 1
                    bad.append(f"{rel}:{lineno} uses: {ref} (expected @{tag})")
            for value_node in _mapping_value_nodes(doc, "platform_ref"):
                if not isinstance(value_node, yaml.ScalarNode):
                    continue
                if value_node.value != tag:
                    lineno = value_node.start_mark.line + 1
                    bad.append(f"{rel}:{lineno} platform_ref: {value_node.value} "
                              f"(expected {tag})")
    ref_count = len(ref_locations)
    if min_refs is not None and ref_count < min_refs:
        bad.append(f"only {ref_count} platform uses: ref(s) found across "
                  f"{patterns} (expected at least {min_refs})")
    bad = list(dict.fromkeys(bad))
    return (not bad, f"every platform ref pinned to {tag}" if not bad
            else "; ".join(bad))


# Any table-shaped row, of ANY cell count — deliberately not anchored to
# exactly 3 cells (nor to a 40-hex last cell), so a row with the wrong
# number of cells, or a malformed (e.g. shortened) sha, is still recognised
# as a row rather than silently failing to match at all. Cell count and the
# sha cell are both validated separately in _load_pins_reference, so either
# kind of malformed row is reported instead of just vanishing. This is
# deliberately loose enough to also classify a 1-cell line like `| note |`
# as a "row" (it has a leading and trailing `|` and nothing else); that
# never bites in practice because PINS.md is policed by `files_unchanged`
# (byte-identical to the seed), so no malformed row of any shape can be
# introduced into it by an audited run.
PINS_TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
# The markdown alignment row under a table header (`|---|---|---|`, optional
# `:` for alignment) — a table-shaped row with no meaningful cell content,
# never a pin.
PINS_SEPARATOR_RE = re.compile(r"^\|[\s:-]+\|[\s:-]+\|[\s:-]+\|\s*$")


def _load_pins_reference(workspace: str, reference: str) -> tuple[dict[str, str], list[str]]:
    """({action: sha}, [malformed row descriptions]), read lexically off a
    PINS.md-shaped markdown table.

    The table's action-name and SHA cells are read as literal text — this
    never decides code SHAPE, so a plain line regex over the reference
    file's own leaf content is the right tool, unlike locating a `uses:`
    node in a workflow (which _uses_value_nodes does via a real YAML parse).

    A table-shaped row whose sha cell is not a valid 40-hex value, OR whose
    cell count isn't exactly 3 (a dropped Tag column, a stray extra column),
    is reported as malformed rather than silently dropped: `PINS_TABLE_ROW_RE`
    used to require BOTH the sha cell to already be valid hex AND exactly 3
    cells to match at all, so either kind of malformed row just failed to
    match and the action vanished from the requirement set entirely —
    indistinguishable from the action never having been listed. The header
    row (`| Action | Tag | SHA |`) and the markdown alignment row beneath it
    are table-shaped too, so both are recognised and skipped explicitly
    rather than by accident.
    """
    try:
        with open(os.path.join(workspace, reference), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return {}, []
    out: dict[str, str] = {}
    malformed = []
    for line in text.splitlines():
        if PINS_SEPARATOR_RE.match(line):
            continue
        m = PINS_TABLE_ROW_RE.match(line)
        if not m:
            continue
        cells = [cell.strip() for cell in m.group(1).split("|")]
        if len(cells) != 3:
            malformed.append(f"{reference}: row has {len(cells)} cell(s), "
                            f"expected 3: {line.strip()!r}")
            continue
        action, _tag_cell, sha = cells
        if action.casefold() == "action":
            continue  # header row
        if SHA_RE.match(sha):
            out[action] = sha
        else:
            malformed.append(f"{reference}: {action}: invalid sha {sha!r}")
    return out, malformed


def pins_match_reference(workspace: str, patterns: list[str],
                         reference: str | None = None,
                         platform_prefix: str | None = None) -> tuple[bool, str]:
    """Every action a reference file (PINS.md) lists is pinned, in the given
    files, to exactly the SHA that reference gives it — not merely a
    40-hex-character value that happens to be present.

    Binds to the seed's own offline source of truth rather than a
    fixture-hardcoded SHA list, so a hallucinated-but-well-formed SHA (one
    that satisfies `uses_refs_sha_pinned` by shape alone) still fails here.
    Also checks completeness: an action the reference lists but that has no
    `uses:` pin at all in the given files fails too, so a stub file that
    drops the real pin down to a comment naming the action does not pass
    vacuously.

    `uses:` values are located the same way `uses_refs_sha_pinned` and
    `pin_comment_absent` do — a real YAML parse via `_uses_value_nodes` —
    never a text regex deciding where the code's structure is.

    Compares with `.casefold()`: `SHA_RE` and `uses_refs_sha_pinned` both
    accept uppercase hex, so an all-uppercase-but-otherwise-correct audit
    must not fail here on case alone.

    The binding is a two-way closure, not a one-way whitelist: as well as
    every PINS.md action being correctly pinned, every remote `uses:` found
    in the given files must itself have a PINS.md row — otherwise a newly
    ADDED third-party action PINS.md never named, however well-formed its
    SHA, would score a perfect run simply by being absent from the table
    this check otherwise iterates.

    `platform_prefix`, when given, excludes a cross-repo reference to this
    account's own platform repo from that closure: PINS.md is a third-party
    pin ledger, and a platform ref staying on its release tag is
    `platform_refs_on_tag`'s business, checked separately (with its own
    `min_refs` presence guard) over its own `paths` — a fixture configures
    those as a superset of this check's, not the identical file set, so a
    platform ref that lands in one of THIS check's files is still caught
    there too. Without the exclusion, an agent that reorganises which file
    carries the platform ref (e.g. consolidating a job into the file this
    check scans) would be failed here too, for a carve-out this check does
    not police.

    A malformed row in the reference file itself (a table-shaped row whose
    sha cell isn't valid 40-hex) fails the check directly rather than
    silently dropping that action from the requirement set — see
    `_load_pins_reference`.
    """
    import yaml
    if not reference:
        return (False, "no reference file configured")
    pins, malformed = _load_pins_reference(workspace, reference)
    if not pins and not malformed:
        return (False, f"{reference}: no pin table rows found")
    found: dict[str, list[tuple[str, int, str]]] = {action: [] for action in pins}
    undeclared = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                text = f.read()
            try:
                doc = yaml.compose(text, Loader=yaml.SafeLoader)
            except yaml.YAMLError:
                continue  # yaml_parses reports this; nothing to check here
            if doc is None:
                continue
            rel = os.path.relpath(path, workspace)
            for value_node in _uses_value_nodes(doc):
                ref = value_node.value
                if not isinstance(ref, str) or not _is_remote_action(ref):
                    continue
                if (platform_prefix
                        and platform_prefix.casefold() in ref.casefold()):
                    continue  # platform_refs_on_tag's business, not ours
                action, _, ref_val = ref.partition("@")
                lineno = value_node.start_mark.line + 1
                if action in found:
                    found[action].append((rel, lineno, ref_val))
                else:
                    undeclared.append(f"{rel}:{lineno} {action}: "
                                      f"not listed in {reference}")
    problems = list(malformed) + undeclared
    for action, expected_sha in pins.items():
        refs = found[action]
        if not refs:
            problems.append(f"{action}: no `uses:` pin found "
                            f"({reference} gives {expected_sha})")
            continue
        for rel, lineno, ref_val in refs:
            if ref_val.casefold() != expected_sha.casefold():
                problems.append(f"{rel}:{lineno} {action}@{ref_val} "
                                f"({reference} gives {expected_sha})")
    return (not problems, f"every {reference} pin present and correct"
            if not problems else "; ".join(problems))


def yaml_parses(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    import yaml
    bad = []
    for pattern in patterns:
        for path in sorted(glob.glob(os.path.join(workspace, pattern))):
            if not os.path.isfile(path):
                continue
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
                    seed: str | None = None, by: str = "path") -> tuple[bool, str]:
    """The matched files' content must survive, relative to the seed workspace.

    `by="path"` (default): every matched file must be byte-identical to the
    seed file at the SAME relative path — a rename, even of untouched
    content, is a failure. This is what every existing fixture wants: a
    ruleset or a fake binary that must not be touched OR moved.

    `by="digest"`: compares the MULTISET of sha256 content digests across
    all matched files, ignoring which filename holds which content. A file
    that got renamed (content preserved, path changed) still passes; a file
    whose content changed, or one that vanished outright (e.g. a naive
    rename that clobbered another file instead of disambiguating), does not
    — its digest is missing from the resulting bag. This is the mode a
    rename task needs: correct behaviour is EXPECTED to move content to new
    paths, so path identity is not the property to protect, content
    survival is.
    """
    if seed is None:
        return (False, "seed workspace not provided")
    if by not in ("path", "digest"):
        return (False, f"files_unchanged: unknown by={by!r}, expected 'path' or 'digest'")

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

    if by == "digest":
        def digests(snapshot_dict):
            return [hashlib.sha256(data).hexdigest() for data in snapshot_dict.values()]
        before_counts, after_counts = Counter(digests(before)), Counter(digests(after))
        if before_counts == after_counts:
            return (True, f"content preserved by digest ({sum(before_counts.values())} file(s))")
        lost = before_counts - after_counts
        gained = after_counts - before_counts
        problems = []
        if lost:
            problems.append(f"{sum(lost.values())} file(s)' content missing from the result")
        if gained:
            problems.append(f"{sum(gained.values())} file(s) with unexpected/new content in the result")
        return (False, "; ".join(problems) if problems else "digest multiset changed")

    problems = [f"{rel}: removed" for rel in sorted(set(before) - set(after))]
    problems += [f"{rel}: added" for rel in sorted(set(after) - set(before))]
    problems += [f"{rel}: modified" for rel in sorted(set(before) & set(after))
                 if before[rel] != after[rel]]
    return (not problems,
            f"unchanged ({', '.join(sorted(before)) or 'no files matched'})"
            if not problems else "; ".join(problems))


def _capped_join(names: list[str], limit: int = 40) -> str:
    """", "-join, but a huge listing doesn't dump every name into `detail`."""
    if len(names) <= limit:
        return ", ".join(names)
    return f"{', '.join(names[:limit])}, and {len(names) - limit} more"


def dir_listing_matches(workspace: str, patterns: list[str], expected: list[str] | None = None,
                        expected_file: str | None = None, seed: str | None = None,
                        ignore: list[str] | None = None) -> tuple[bool, str]:
    """The sorted immediate-entry listing of one directory must equal an
    expected list of names.

    `patterns` names exactly one directory, relative to the workspace (e.g.
    `["inbox"]`) — this is not a glob, unlike every other check here; it is
    listed once and compared whole, which is what a rename task needs: the
    property under test is which NAMES exist afterward, not any one file's
    content.

    The expected names come from exactly one of:
      - `expected`: an inline list in the fixture.
      - `expected_file`: a path read from the pristine `seed` directory (never
        the runtime workspace, so a run that deletes or edits its own copy of
        that file cannot change what "expected" means) — one name per
        non-blank line.

    `ignore`: optional list of `fnmatch` glob patterns (compared as data,
    never a regex) for entry names to drop from the listing before
    comparing — for a name that is inherently non-deterministic (e.g. a
    wall-clock-stamped log file) and so cannot itself appear in `expected`.
    Anything NOT matching an ignore pattern is still compared normally, so
    this narrows what is excused, not what is checked.
    """
    if len(patterns) != 1:
        return (False, f"dir_listing_matches takes exactly one directory, got {patterns!r}")
    directory = patterns[0]
    if os.path.isabs(directory):
        return (False, f"{directory}: must be a workspace-relative path, not absolute")
    workspace_real = os.path.realpath(workspace)
    target = os.path.join(workspace, directory)
    target_real = os.path.realpath(target)
    if os.path.commonpath([workspace_real, target_real]) != workspace_real:
        return (False, f"{directory}: resolves outside the workspace")
    if not os.path.isdir(target):
        return (False, f"{directory}: not a directory")
    actual = sorted(os.listdir(target))
    if ignore:
        actual = [name for name in actual
                 if not any(fnmatch.fnmatch(name, pat) for pat in ignore)]

    if expected is not None and expected_file is not None:
        return (False, "dir_listing_matches: give expected or expected_file, not both")
    if expected_file is not None:
        if seed is None:
            return (False, "seed workspace not provided")
        try:
            with open(os.path.join(seed, expected_file), encoding="utf-8") as f:
                expected = [line.strip() for line in f if line.strip()]
        except (OSError, UnicodeDecodeError) as exc:
            return (False, f"{expected_file}: {exc}")
    elif expected is None:
        return (False, "dir_listing_matches: expected or expected_file is required")
    if not isinstance(expected, list):
        return (False, f"dir_listing_matches: expected must be a list, "
                       f"got {type(expected).__name__}")
    expected = sorted(expected)

    if actual == expected:
        return (True, f"{directory}/ matches the expected listing ({len(actual)} entries)")
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    problems = []
    if missing:
        problems.append("missing: " + _capped_join(missing))
    if extra:
        problems.append("unexpected: " + _capped_join(extra))
    return (False, "; ".join(problems) if problems
            else f"listing differs: {_capped_join(actual)} != {_capped_join(expected)}")


def file_digests_match(workspace: str, patterns: list[str],
                       sha256: str | None = None) -> tuple[bool, str]:
    """Every path in `patterns` (workspace-relative, NOT a glob) must exist
    and its content must hash to the exact `sha256` hex digest given.

    Unlike `files_unchanged(by="digest")`, which compares a MULTISET of
    digests against the seed with no fixed identity, this pins one exact,
    known-in-advance digest to one or more named paths — "this specific
    document's bytes ended up at this specific final name." More than one
    path is for a disambiguated pair that is expected to still be
    byte-identical copies of the SAME document (e.g. `foo.pdf` and
    `foo (2).pdf`), not two different documents.
    """
    if not patterns:
        return (False, "file_digests_match: at least one path is required")
    if not sha256:
        return (False, "file_digests_match: sha256 is required")
    problems = []
    for rel in patterns:
        full = os.path.join(workspace, rel)
        if not os.path.isfile(full):
            problems.append(f"{rel}: not found")
            continue
        with open(full, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        if digest != sha256:
            problems.append(f"{rel}: digest {digest} != expected {sha256}")
    return (not problems, f"{', '.join(patterns)}: digest matches" if not problems
            else "; ".join(problems))


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
                       must_not_match=None, transcript=None) -> tuple[bool, str]:
    """Regex assertions over the agent's final reply.

    The transcript is what the agent handed the operator, so it is where a
    "say it needs elevation, and give the exact line" rule is decidable. In
    objective-only mode there is no transcript and the check fails saying so
    — a missing transcript is not a passing one. `patterns` is accepted for
    signature parity with every other check and ignored.
    """
    if transcript is None:
        return (False, "no transcript (objective-only run, or the agent produced none)")
    return _text_matches(transcript, must_match or [], must_not_match or [], "transcript")


CHECKS = {
    "uses_refs_sha_pinned": uses_refs_sha_pinned,
    "pin_comment_absent": pin_comment_absent,
    "yaml_parses": yaml_parses,
    "non_remote_refs_unchanged": non_remote_refs_unchanged,
    "changeset_triggers": changeset_triggers,
    "required_checks_early_skip": required_checks_early_skip,
    "event_only_workflows_unfiltered": event_only_workflows_unfiltered,
    "files_unchanged": files_unchanged,
    "file_digests_match": file_digests_match,
    "file_matches": file_matches,
    "transcript_matches": transcript_matches,
    "pins_match_reference": pins_match_reference,
    "platform_refs_on_tag": platform_refs_on_tag,
    "dir_listing_matches": dir_listing_matches,
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
        if check["type"] in ("non_remote_refs_unchanged", "files_unchanged", "dir_listing_matches"):
            kwargs["seed"] = seed
        if check["type"] == "files_unchanged":
            kwargs["by"] = check.get("by", "path")
        if check["type"] == "changeset_triggers":
            kwargs["changeset"] = check.get("changeset", [])
            kwargs["expect_triggered"] = check.get("expect_triggered", [])
            kwargs["expect_skipped"] = check.get("expect_skipped", [])
        elif check["type"] in ("file_matches", "transcript_matches"):
            kwargs["must_match"] = check.get("must_match", [])
            kwargs["must_not_match"] = check.get("must_not_match", [])
            if check["type"] == "transcript_matches":
                kwargs["transcript"] = transcript
        elif check["type"] == "uses_refs_sha_pinned":
            kwargs["platform_prefix"] = check.get("platform_prefix")
        elif check["type"] == "pins_match_reference":
            kwargs["reference"] = check.get("reference")
            kwargs["platform_prefix"] = check.get("platform_prefix")
        elif check["type"] == "platform_refs_on_tag":
            kwargs["platform_prefix"] = check.get("platform_prefix")
            kwargs["tag"] = check.get("tag")
            kwargs["min_refs"] = check.get("min_refs")
        elif check["type"] == "dir_listing_matches":
            kwargs["expected"] = check.get("expected")
            kwargs["expected_file"] = check.get("expected_file")
            kwargs["ignore"] = check.get("ignore")
        elif check["type"] == "file_digests_match":
            kwargs["sha256"] = check.get("sha256")
        passed, detail = fn(workspace, check.get("paths", []), **kwargs)
        results.append({"id": check["id"], "passed": passed, "detail": detail})
    return results
