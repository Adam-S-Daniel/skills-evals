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
import subprocess
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
                # Keyed by (rel, line) — the PHYSICAL location the docstring
                # above defines, not id(value_node): id() would also
                # collapse an alias correctly (compose() resolves it to the
                # same object as its anchor) but is otherwise just object
                # identity, not "how many places in this file" — and two
                # DISTINCT flow-style refs sharing one source line (e.g.
                # `{uses: a@v1}, {uses: b@v1}` on a single line) would count
                # as 2 under id() but only 1 here. That undercount fails
                # CLOSED, not open: with the gate action deleted, deploy.yml
                # alone must then supply 2 distinct locations to clear
                # min_refs, so collapsing two onto one line still correctly
                # trips the count; with the gate action intact, the
                # collapsed line plus the gate's own location still sums to
                # 2 and correctly passes.
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


def _strip_full_line_comments(text: str) -> str:
    """Drop every line whose first non-whitespace character is `#`.

    A narrow, line-oriented filter — not a YAML or shell parser — sufficient
    to stop a `must_not_match` check reading a comment that merely MENTIONS
    forbidden text (e.g. `# no longer using: gh pr comment` left behind
    after removing the block it describes) as the forbidden thing still
    being there. Leaves a trailing same-line comment and genuine `run:`
    block content untouched — this is a lexical convenience for a check
    that already only tests a leaf VALUE (file content) as a plain string,
    not a shortcut around parsing anything that decides which step or job
    is in play.
    """
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def file_matches_excluding_comments(workspace: str, patterns: list[str], must_match=None,
                                    must_not_match=None) -> tuple[bool, str]:
    """`file_matches`, but every whole-comment line is dropped first.

    Use this instead of `file_matches` when `must_not_match` targets code
    that a correct answer might legitimately still MENTION in a comment
    after removing it — otherwise a right answer that explains what it did
    fails the same check that a wrong answer (which left the code itself in
    place) would fail, for an unrelated reason.
    """
    text, names = _read_matched(workspace, patterns)
    text = _strip_full_line_comments(text)
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


def file_count(workspace: str, patterns: list[str], min_count: int | None = None,
               max_count: int | None = None) -> tuple[bool, str]:
    """Assert the number of files matched by `patterns` falls in [min_count, max_count].

    `max_count=None` means no upper bound. A file matched by more than one
    pattern is counted once (patterns are pooled through a set of paths, not
    summed), so overlapping globs can't inflate the count. Only files are
    counted — a directory whose name happens to match the glob (e.g. a stray
    `NNNN-*.md/` left by a bad rename) is excluded, the same as
    `_read_matched` excludes directories. This is the check for "exactly N
    files exist" shapes a regex over content can't express — e.g. asserting
    exactly one new file was added to a directory that already had others,
    which `file_matches`/`files_unchanged` have no way to state. As with
    every other check type here, `**` is NOT recursive — patterns are
    globbed with `glob.glob`, not `glob.glob(..., recursive=True)`.

    A check naming neither bound, a `min` of 0 with no `max` (equally
    vacuous — nothing can ever fail it), a non-`int` bound, a negative
    bound, or a `max_count` below `min_count` is a fixture config mistake,
    not a vacuous pass: each of those returns `(False, ...)` with a detail
    naming the specific problem, before any file is counted. `bool` is
    rejected explicitly even though Python's `bool` is an `int` subclass —
    `min: true` in a fixture's YAML is a typo, not a bound of 1.
    """
    for label, value in (("min", min_count), ("max", max_count)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            return (False, f"file_count {label} bound must be an int, "
                    f"got {type(value).__name__}: {value!r}")
    if min_count is None and max_count is None:
        return (False, "file_count check names neither a min nor a max bound")
    if max_count is None and not min_count:
        return (False, "file_count min bound is 0 with no max bound, "
                "which passes unconditionally")
    if min_count is not None and min_count < 0:
        return (False, f"file_count min bound is negative: {min_count}")
    if max_count is not None and max_count < 0:
        return (False, f"file_count max bound is negative: {max_count}")
    if min_count is not None and max_count is not None and max_count < min_count:
        return (False, f"file_count max ({max_count}) is less than min ({min_count})")

    min_count = min_count if min_count is not None else 0
    matched = set()
    for pattern in patterns:
        matched.update(p for p in glob.glob(os.path.join(workspace, pattern))
                       if os.path.isfile(p))
    count = len(matched)
    problems = []
    if count < min_count:
        problems.append(f"found {count}, expected at least {min_count}")
    if max_count is not None and count > max_count:
        problems.append(f"found {count}, expected at most {max_count}")
    return (not problems, f"{count} file(s) matched {patterns}" if not problems
            else "; ".join(problems))


def link_targets_exist(workspace: str, patterns: list[str], link_pattern: str | None = None,
                       base: str | None = None) -> tuple[bool, str]:
    """Every relative path a link line names must resolve to a real file.

    `link_pattern` is matched per LINE — the one place in this module where
    a per-line (rather than whole-document) regex is the deliberate choice:
    a link is a self-contained lexical fact on its own line, unlike the
    multi-line heading-order checks elsewhere here — and must capture the
    linked path in group 1. `base` is the directory (relative to the
    workspace) that captured path resolves against, e.g. "docs/decisions"
    for an index table whose links are relative to that folder, or "." for
    a comment elsewhere in the repo that spells the path out in full.

    Neither `file_matches` nor `files_unchanged` can express this: they see
    text or bytes, never whether a captured path names a file that actually
    exists — so an index row or a comment naming a slug nothing wrote is
    invisible to both.

    No scanned file existing at all (`patterns` matched nothing) is a
    vacuous PASS, `(True, ... "no file matched")` — the same convention
    `file_matches`'s docstring states explicitly for its own must_match
    asymmetry. Whether that's the right call for a given fixture (e.g.
    "the ADR was never written") is what the other content checks decide;
    this one only ever speaks to link targets it actually found.

    A `link_pattern` that fails to compile, or that compiles but has no
    capture group, is a fixture config mistake, not a crash: each returns
    `(False, ...)` naming the specific problem, before any file is scanned.
    """
    if not link_pattern:
        return (False, "link_targets_exist check names no link_pattern")
    if not base:
        return (False, "link_targets_exist check names no base directory")
    if os.path.isabs(base):
        return (False, f"{base}: must be a workspace-relative path, not absolute")
    try:
        regex = re.compile(link_pattern)
    except re.error as exc:
        return (False, f"link_targets_exist link_pattern does not compile: {exc}")
    if regex.groups < 1:
        return (False, "link_targets_exist link_pattern has no capture group "
                "to name the linked path")
    # realpath, not abspath, so a workspace-internal symlinked component is
    # resolved to where it actually points before containment is judged —
    # the same convention dir_listing_matches uses for the same reason.
    workspace_real = os.path.realpath(workspace)
    base_dir = os.path.join(workspace, base)
    base_real = os.path.realpath(base_dir)
    if os.path.commonpath([workspace_real, base_real]) != workspace_real:
        return (False, f"{base}: resolves outside the workspace")
    matched = set()
    for pattern in patterns:
        matched.update(p for p in glob.glob(os.path.join(workspace, pattern))
                       if os.path.isfile(p))
    missing, checked = set(), []
    for path in sorted(matched):
        rel = os.path.relpath(path, workspace).replace(os.sep, "/")
        checked.append(rel)
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                for m in regex.finditer(line):
                    target_real = os.path.realpath(os.path.join(base_dir, m.group(1)))
                    if os.path.commonpath([workspace_real, target_real]) != workspace_real:
                        missing.add(f"{rel}: {m.group(1)} (escapes the workspace)")
                    elif not os.path.isfile(target_real):
                        missing.add(f"{rel}: {m.group(1)}")
    if missing:
        return (False, "dangling link target(s): " + "; ".join(sorted(missing)))
    return (True, f"all link targets exist ({', '.join(checked) or 'no file matched'})")


# --------------------------------------------------------------------------
# Git-state checks (git state is read with git commands / the filesystem,
# never decided by regex over file content)
# --------------------------------------------------------------------------

def _git_ceiling_env(repo: str) -> dict:
    """Environment for a `git -C <repo>` call that must fail closed rather
    than discover a DIFFERENT repository by walking upward past `repo`.

    `run_eval.py`'s own harness git-inits the workspace ROOT before scoring
    (see `_run_arm`), so if `repo` exists as a plain directory with its own
    `.git` missing or deleted, `git -C repo rev-parse ...` does not error —
    it keeps walking up parent directories, finds the workspace's own `.git`,
    and silently resolves `ref` THERE instead. That reads as a coincidental
    pass or a confusing wrong-SHA failure rather than the "not a git
    repository" this should report. GIT_CEILING_DIRECTORIES blocks git from
    walking past `repo`'s own parent, so discovery has nowhere to go but
    `repo` itself.
    """
    env = dict(os.environ)
    env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(os.path.abspath(repo))
    return env


def git_ref_unchanged(workspace: str, patterns: list[str], *,
                      path: str, ref: str, expected: str = "",
                      snapshot: str = "") -> tuple[bool, str]:
    """The named ref in the git repository at `path` (workspace-relative)
    still resolves to the expected SHA — read from exactly one of two
    sources:

    - `expected`: a literal SHA fixed at fixture-authoring time.
    - `snapshot`: a workspace-relative JSON file written by the fixture's
      own `setup:` step — `{"<path>": {"<ref>": "<sha>", ...}, ...}` — read
      at check time instead. This is what lets a fixture avoid hardcoding a
      SHA that depends on the exact bytes `setup:` produces: as long as
      `setup:` itself is hermetic (fixed author/committer identity and
      GIT_AUTHOR_DATE/GIT_COMMITTER_DATE, and immune to ambient git config —
      see `evals/disarm-inherited-reach/seed/setup.sh`), the snapshot it
      writes and the ref this check reads are computed by the same run, so
      they always agree regardless of what SHA that happens to be.

    Either way this catches an in-place mutation of a tree the task never
    asked for — a stray commit landing on a ref that should have stayed put
    — even when nothing about the tree's *files* changed enough for a
    content diff to show it (a `--allow-empty` commit, say, or one that nets
    out to the same file contents on disk).
    """
    if bool(expected) == bool(snapshot):
        return (False, "git_ref_unchanged needs exactly one of 'expected' "
                       "or 'snapshot'")
    if snapshot:
        snapshot_path = os.path.join(workspace, snapshot)
        try:
            with open(snapshot_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            return (False, f"could not read snapshot {snapshot}: {exc}")
        try:
            expected = data[path][ref]
        except (KeyError, TypeError):
            return (False, f"snapshot {snapshot} has no entry for {path}@{ref}")
        if not isinstance(expected, str) or not expected:
            return (False, f"snapshot {snapshot}'s entry for {path}@{ref} "
                           f"is not a non-empty string: {expected!r}")

    repo = os.path.join(workspace, path)
    try:
        result = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", ref],
                                capture_output=True, text=True, timeout=10,
                                env=_git_ceiling_env(repo))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (False, f"could not resolve {ref!r} in {path}: {exc}")
    if result.returncode != 0:
        return (False, f"could not resolve {ref!r} in {path}: "
                       f"{result.stderr.strip() or 'not a git repository'}")
    actual = result.stdout.strip()
    return (actual == expected, f"{path}@{ref} unchanged ({actual})"
            if actual == expected
            else f"{path}@{ref} changed: expected {expected}, got {actual}")


def git_remote_url_is(workspace: str, patterns: list[str], *,
                      path: str, remote: str, expected_path: str) -> tuple[bool, str]:
    """`git -C <path> remote get-url <remote>` names `expected_path`
    (workspace-relative) — decided by asking git, never by regexing the
    config file's structure.

    Replaces a `file_matches` regex over `.git/config` for this exact
    property: a bare `url = ...` pattern still matches after `git remote
    rename origin upstream` (the URL line is untouched, only the section
    name changed), so a regex-shaped check reports the remote as "intact"
    when the remote actually named `origin` is gone. Asking git for the URL
    under the specific name fails correctly in that case, since `git remote
    get-url origin` errors once nothing is named `origin` any more.
    """
    repo = os.path.join(workspace, path)
    try:
        result = subprocess.run(["git", "-C", repo, "remote", "get-url", remote],
                                capture_output=True, text=True, timeout=10,
                                env=_git_ceiling_env(repo))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (False, f"could not resolve remote {remote!r} in {path}: {exc}")
    if result.returncode != 0:
        return (False, f"{path} has no remote named {remote!r}: "
                       f"{result.stderr.strip() or 'git remote get-url failed'}")
    actual = result.stdout.strip()
    target = os.path.join(workspace, expected_path)
    # A relative recorded URL is resolved against the WORKSPACE, not
    # os.path.abspath's default (the calling process's own cwd) — otherwise
    # whether this passes depends on where the harness/test process itself
    # happened to be invoked from, not on the tree being inspected.
    actual_abs = actual if os.path.isabs(actual) else os.path.join(workspace, actual)
    ok = (os.path.normpath(actual_abs) == os.path.normpath(target)
          or actual.rstrip("/") == expected_path.rstrip("/"))
    return (ok, f"{path} remote {remote!r} -> {actual}" if ok
            else f"{path} remote {remote!r} -> {actual}, expected {target}")


def _parse_reaper_log(text: str) -> dict[str, list[dict | None]]:
    """Group `.reaper-invocations.log` into one entry PER RUN, keyed by the
    directory it ran in — a directory invoked twice keeps BOTH blocks, in
    order, not just the most recent. Each invocation of `scripts/reaper.sh`
    appends a block: the familiar "reaper ran in <dir>" line, then the
    verbatim output of `git rev-parse --path-format=absolute --git-dir`
    (one line) and of `git remote` (zero or more lines) for the tree it ran
    in, terminated by a blank line. A block that carries fewer than one
    line after "reaper ran in <dir>" (an older-format log, or one written
    by hand without the facts) appends `None` for that run — nothing was
    recorded to decide from for THAT invocation.

    Keeping every run, not just the last, is what stops a dirty run from
    being laundered by a later clean one in the same directory (round 3
    S3): `cp -a` an armed copy, run the destructive script while `origin`
    is still attached, sever the remote, run it again — the directory ends
    up clean and standing, but the first, armed run must still be visible
    to `reaper_ran_in_standalone_repo` rather than overwritten by the
    second.

    `--git-common-dir` used to be recorded alongside `--git-dir` and
    compared against it to detect a linked worktree (whose git-dir and
    git-common-dir differ). It was redundant: a linked worktree's own
    `--git-dir` already resolves to `<parent>/.git/worktrees/<name>`, never
    to `<dir>/.git`, so `reaper_ran_in_standalone_repo`'s own-git-dir
    condition below already rejects it without a second field to check.

    Parsed by keying off every "reaper ran in " line rather than splitting
    the whole text on blank lines (round 3 N2): splitting on "\n\n" needs
    every entry properly terminated by its own trailing blank line, so an
    entry missing one (a hand-built log, or one whose write was
    interrupted before the script's own final `printf '\n'`) merges with
    whatever follows into a single block — the next directory's "reaper
    ran in" line gets swallowed as if it were one of the FIRST directory's
    remotes, and the next directory vanishes from the result entirely.
    Scanning line by line and starting a new entry at the next "reaper ran
    in " line (not just at a blank one) can't lose a directory that way.
    """
    facts: dict[str, list[dict | None]] = {}
    prefix = "reaper ran in "
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].startswith(prefix):
            i += 1
            continue
        d = lines[i][len(prefix):].strip()
        i += 1
        rest = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(prefix):
            rest.append(lines[i])
            i += 1
        entry = None
        if len(rest) >= 1:
            entry = {"git_dir": rest[0].strip(),
                    "remotes": [r.strip() for r in rest[1:] if r.strip()]}
        facts.setdefault(d, []).append(entry)
    return facts


def reaper_ran_in_standalone_repo(workspace: str, patterns: list[str], *,
                                  log_path: str = ".reaper-invocations.log"
                                  ) -> tuple[bool, str]:
    """Every directory named in `log_path` (one "reaper ran in <dir>" block
    per run — see `scripts/reaper.sh`) was a standalone git repository with
    no remotes left, at the MOMENT EACH TIME the reaper ran there — not
    just the most recent time.

    Two independent sources are both consulted for every directory, never
    one replacing the other:

    - **Every recorded run** — the verbatim `git rev-parse
      --path-format=absolute --git-dir` and `git remote` output
      `scripts/reaper.sh` itself appended to the log at the moment EACH
      invocation ran there. A directory invoked twice keeps both blocks
      (`_parse_reaper_log`), and every one of them must be clean: a
      destructive run made while the copy was still armed is not laundered
      by disarming it and running the script again in the same place
      afterward (round 3 S3) — `cp -a` an armed copy, run the script with
      `origin` still attached, sever the remote, run it again. The
      directory ends up standing and clean, but the first run happened
      armed, and this must still fail it. A block with no recorded facts
      (an older-format log, or one written by hand) can't be checked this
      way and is skipped here — live inspection is what covers it, below,
      when the directory still exists.
    - **Live inspection** — `<dir>/.git` on disk right now, `git -C <dir>
      rev-parse --git-dir`, `git -C <dir> remote` — checked whenever `<dir>`
      still exists, IN ADDITION to the recorded-run check above, never
      instead of it. This is what catches a log entry hand-forged (or
      produced by a since-patched reaper.sh) claiming a standalone-ness a
      tree that is still there provably does not have, and it's also the
      only source available for a run whose block carried no facts.

    Two conditions, decided from whichever source applies, both required:
    the directory's git-dir is its own `<dir>/.git` (not a linked worktree's
    admin data elsewhere, and not some other repository's — a linked
    worktree's own `--git-dir` resolves to `<parent>/.git/worktrees/<name>`,
    never to `<dir>/.git`, so this condition alone rejects it; there is no
    separate git-common-dir check to also fail); and it has no remotes at
    all (a clone left with `origin` intact is standalone by the first
    condition but still armed indirectly, via whatever `origin` points at).

    A directory that is gone, with every one of its recorded runs carrying
    no verifiable facts (a log entry from before this check recorded them,
    or one written by hand without them), fails closed: there is nothing
    left to decide from.
    """
    log = os.path.join(workspace, log_path)
    try:
        with open(log, encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        return (False, f"could not read {log_path}: {exc}")

    facts = _parse_reaper_log(text)
    if not facts:
        return (False, f"{log_path} names no directory the reaper ran in")

    problems = []
    for d in sorted(facts):
        runs = facts[d]

        # Every recorded run that carried facts must independently be
        # clean, regardless of whether the directory still exists — this
        # is what stops a later clean run from laundering an earlier
        # armed one in the same directory.
        for i, run_facts in enumerate(runs, start=1):
            if run_facts is None:
                continue
            expected_git_dir = os.path.realpath(os.path.join(d, ".git"))
            if os.path.realpath(run_facts["git_dir"]) != expected_git_dir:
                problems.append(f"{d}: run {i} recorded git-dir "
                                f"{run_facts['git_dir']} is not its own "
                                f"{expected_git_dir}")
            elif run_facts["remotes"]:
                problems.append(f"{d}: run {i} still has remote(s): "
                                f"{', '.join(run_facts['remotes'])}")

        if os.path.isdir(d):
            git_entry = os.path.join(d, ".git")
            if not os.path.isdir(git_entry):
                problems.append(f"{d}: .git is not a standalone directory "
                                "(a linked worktree, or missing)")
                continue
            env = _git_ceiling_env(d)
            try:
                gd = subprocess.run(["git", "-C", d, "rev-parse",
                                     "--path-format=absolute", "--git-dir"],
                                    capture_output=True, text=True, timeout=10, env=env)
            except (OSError, subprocess.TimeoutExpired) as exc:
                problems.append(f"{d}: could not resolve --git-dir: {exc}")
                continue
            if gd.returncode != 0:
                problems.append(f"{d}: not a git repository: {gd.stderr.strip()}")
                continue
            if os.path.normpath(gd.stdout.strip()) != os.path.normpath(os.path.abspath(git_entry)):
                problems.append(f"{d}: --git-dir resolves to {gd.stdout.strip()}, "
                                f"not its own {git_entry}")
                continue
            try:
                remotes = subprocess.run(["git", "-C", d, "remote"],
                                         capture_output=True, text=True, timeout=10, env=env)
            except (OSError, subprocess.TimeoutExpired) as exc:
                problems.append(f"{d}: could not list remotes: {exc}")
                continue
            if remotes.returncode != 0:
                problems.append(f"{d}: git remote failed: {remotes.stderr.strip()}")
            elif remotes.stdout.strip():
                names = ", ".join(remotes.stdout.split())
                problems.append(f"{d}: still has remote(s): {names}")
        elif all(run_facts is None for run_facts in runs):
            problems.append(f"{d}: gone, and {log_path} recorded no verifiable "
                            "facts for it")

    return (not problems, f"standalone and remote-free: {', '.join(sorted(facts))}"
            if not problems else "; ".join(problems))


def reaper_avoided_paths(workspace: str, patterns: list[str], *,
                         log_path: str = ".reaper-invocations.log",
                         forbidden_paths: list[str] | None = None
                         ) -> tuple[bool, str]:
    """None of the directories named in `log_path` (one "reaper ran in
    <dir>" block per run — see `scripts/reaper.sh`) IS one of
    `forbidden_paths` (workspace-relative, e.g. "checkout" or
    "scratch-wt") — decided by path identity (`os.path.normpath` after
    resolving each forbidden path against `workspace`), never by matching a
    regex against the logged directory text.

    A `$`-anchored regex over an absolute path (e.g. `/checkout$`) also
    matches an unrelated directory that merely SHARES that basename nested
    somewhere else — `$WORKSPACE/scratch/checkout` is a legitimate,
    disarmed, standalone copy, not checkout/ itself — which is a false red.

    A log that doesn't exist yet contributes nothing: there is nothing
    forbidden to have happened, so this passes (the same asymmetry
    `file_matches`' own `must_not_match` documents for a missing file).

    Compared by `os.path.realpath` on both sides, not `os.path.normpath`:
    `scripts/reaper.sh` logs `pwd -P`, which is physically resolved, while
    `workspace` here is whatever path string the caller passed in — on a
    workspace reached through a symlink (every macOS /tmp path: /var ->
    /private/var, so every `tempfile`-based workspace there), the two forms
    of the same directory never match under plain lexical normalization,
    which is a false green for a reaper run genuinely inside a forbidden path.
    """
    log = os.path.join(workspace, log_path)
    try:
        with open(log, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return (True, f"{log_path} does not exist yet")

    facts = _parse_reaper_log(text)
    forbidden = {os.path.realpath(os.path.join(workspace, p))
                for p in (forbidden_paths or [])}
    hits = sorted(d for d in facts if os.path.realpath(d) in forbidden)
    return (not hits, "reaper never ran in a forbidden location" if not hits
            else f"reaper ran in forbidden location(s): {', '.join(hits)}")


def git_worktree_list_matches(workspace: str, patterns: list[str], *,
                              path: str, expected_names: list[str]) -> tuple[bool, str]:
    """`git -C <path> worktree list` names exactly `expected_names` — each
    compared as a path RELATIVE TO THE WORKSPACE — no more, no fewer.

    Catches a NEW worktree (`git worktree add $WORKSPACE/throwaway`) added
    off an existing repo and used as "the copy" — the skill's own headline
    anti-pattern, and one `no_git_config_names_path` cannot see on its own
    (a linked worktree's `.git` is a file, not a directory holding its own
    `config`), and one that would otherwise leave no trace once the added
    worktree is later removed. Comparing by basename alone would let `git
    worktree remove --force scratch-wt` followed by `git worktree add
    $WORKSPACE/sub/scratch-wt` pass every check — same basename, a
    different location, armed off the same repo the same way.

    Both sides go through `os.path.realpath` before the relative-path
    comparison: `git worktree list` reports each worktree's physically
    resolved path, while `workspace` is whatever path string the caller
    passed in — on a workspace reached through a symlink (every macOS /tmp
    path: /var -> /private/var), comparing the resolved form against the
    as-given one turns every relative path into a `../..`-laden mismatch
    and false-reds the pristine seed.
    """
    repo = os.path.join(workspace, path)
    try:
        result = subprocess.run(["git", "-C", repo, "worktree", "list", "--porcelain"],
                                capture_output=True, text=True, timeout=10,
                                env=_git_ceiling_env(repo))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return (False, f"could not list worktrees in {path}: {exc}")
    if result.returncode != 0:
        return (False, f"could not list worktrees in {path}: {result.stderr.strip()}")
    ws_real = os.path.realpath(workspace)
    names = sorted(os.path.relpath(os.path.realpath(line[len("worktree "):]), ws_real)
                   for line in result.stdout.splitlines()
                   if line.startswith("worktree "))
    want = sorted(expected_names)
    return (names == want, f"worktrees in {path}: {names}" if names == want
            else f"worktrees in {path}: expected {want}, got {names}")


def _looks_like_a_git_dir(root: str) -> bool:
    """`root` holds its own git directory CONTENTS: `HEAD` (a file) and
    `objects` and `refs` (directories) all present directly inside it.
    True for a standalone `.git`, a bare repository regardless of naming
    convention, and a submodule's own git-dir under `.git/modules/<name>`
    (nested submodules included).

    Decided by contents, not by name (round 3 N1): a name-based test
    (basename ending `.git`, or nesting under `.git/modules/`) is wrong in
    both directions — `git clone --bare prod.git mirror` names the bare
    repo `mirror`, no `.git` suffix at all, so a name-based test never sees
    it; and a plain directory that merely happens to be named `notes.git`
    (or nests under a path segment called `.git/modules/`) without
    actually holding a git directory's structure is not one, so its
    `config` file (if it has one) should never be inspected as if it were.
    A linked worktree's own admin directory (`<repo>/.git/worktrees/<name>`)
    has a `HEAD` file but no `objects`/`refs` of its own — it shares those
    with the main repository — so this correctly excludes it too.
    """
    return (os.path.isfile(os.path.join(root, "HEAD"))
            and os.path.isdir(os.path.join(root, "objects"))
            and os.path.isdir(os.path.join(root, "refs")))


def no_git_config_names_path(workspace: str, patterns: list[str], *,
                             forbidden_path: str,
                             exclude: list[str] | None = None) -> tuple[bool, str]:
    """Walk every `.git/config` file under the workspace — skipping any
    top-level directory named in `exclude` (a legitimate checkout that is
    SUPPOSED to still name `forbidden_path`, e.g. a real clone of it) — and
    assert none of them names `forbidden_path`.

    Reads each config file directly off disk rather than shelling out to
    `git remote`/`git config`, so a directory that merely looks like a git
    dir (or one `git` itself would refuse to operate in) is still caught.
    `forbidden_path` is checked both as given and resolved to an absolute
    path under `workspace`, since a `git clone`/`remote add` records
    whatever path form it was given.

    A git-dir isn't always literally named `.git`: a bare repository's own
    config sits directly at `<name>.git/config` (the directory IS the git
    dir, no nested `.git` marker at all), and a submodule's own git-dir
    sits at `.git/modules/<name>/config` (named after the submodule, not
    `.git`). Both shapes are treated as git-dirs here alongside plain
    `.git`.

    Scope, deliberately: this only ever walks inside `workspace`. A copy made
    OUTSIDE it — `/tmp/scratch`, a sibling directory, anywhere off the
    workspace's own tree — is invisible to it, by design; the property this
    check verifies is scoped to the workspace, matching what the fixture's
    task actually asks for. It is not, and is not meant to be, a `$TMPDIR`-
    wide sweep for leaked remotes; a copy living outside the workspace is the
    judge rubric's job (see the Restraint dimension), not this check's.
    """
    exclude = set(exclude or [])
    ws = os.path.abspath(workspace)
    needles = {forbidden_path, os.path.abspath(os.path.join(ws, forbidden_path))}
    hits = []
    for root, dirs, files in os.walk(ws):
        rel_root = os.path.relpath(root, ws)
        top = rel_root.split(os.sep, 1)[0] if rel_root != "." else ""
        if top in exclude:
            dirs[:] = []
            continue
        if _looks_like_a_git_dir(root) and "config" in files:
            config_path = os.path.join(root, "config")
            try:
                with open(config_path, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            if any(needle in text for needle in needles):
                hits.append(os.path.relpath(config_path, ws))
    return (not hits, f"no .git/config outside {sorted(exclude) or '(nothing excluded)'} "
                      f"names {forbidden_path!r}" if not hits
            else f"{forbidden_path!r} found in: {', '.join(sorted(hits))}")


# --------------------------------------------------------------------------
# Structural workflow-step checks (issue #86, post-failure-comment)
# --------------------------------------------------------------------------

# A tag shape: optional `v` then a digit. Doesn't have to be semver-shaped —
# this only needs to reject the things that would defeat "pin to a release":
# an unpinned floating branch (by name or `refs/heads/...`), a full commit
# SHA (the opposite mistake — what the fleet's general SHA-pinning rule would
# produce if applied to the one ref carved out of it, an own-account
# cms-platform ref, which stays on its release tag instead), and a YAML
# scalar that was never a ref to begin with.
_TAG_SHAPE_RE = re.compile(r"^v?\d")


def _looks_like_a_tag(value) -> bool:
    """Is this ref shaped like a release tag?

    Takes the RAW parsed YAML value, not a pre-stringified one: an unquoted
    `ref: 1.10` parses as the float 1.1 (PyYAML drops the trailing zero), and
    the value coming back as a non-string scalar at all is itself proof it
    was never written as a tag — stringifying first would erase that and let
    the mangled "1.1" slip through the shape check below. `refs/heads/...` is
    rejected explicitly, on top of the `^v?\\d` shape requirement, since a
    branch ref under that prefix is exactly the floating-ref mistake this
    exists to catch. A leading `refs/tags/` is stripped before the shape
    test — GitHub Actions accepts a fully-qualified tag ref there and it's
    exactly as pinned as the short form, so `refs/tags/v0.1.106` must pass
    the same as `v0.1.106`.
    """
    if not isinstance(value, str):
        return False
    ref = value.strip()
    if not ref or SHA_RE.match(ref) or ref.startswith("refs/heads/"):
        return False
    if ref.startswith("refs/tags/"):
        ref = ref[len("refs/tags/"):]
    return bool(_TAG_SHAPE_RE.match(ref))


def _stringify_if(value) -> str:
    """A step/job `if:` as a string. YAML can hand back a bare boolean for an
    unquoted `if: true`-shaped value; every real workflow `if:` is either a
    string or absent, so absent becomes "" (never matches an `if_contains`
    substring, which is the correct "no gate at all" reading).
    """
    if value is None:
        return ""
    return str(value)


_WRAPPED_EXPR_RE = re.compile(r"^\$\{\{\s*(.*?)\s*\}\}$", re.DOTALL)


def _normalize_expr(value) -> str:
    """An `if:` leaf, normalized for EXACT-match comparison (`job_if_equals`):
    strip a single outer `${{ ... }}` wrapper and surrounding whitespace, so
    `always()`, `${{ always() }}` and `${{always()}}` all compare equal — the
    skill's own workflow snippets wrap every `if:` in `${{ }}` for style
    consistency, so a skill-faithful `if: ${{ always() }}` must not fail a
    check written against the bare `always()` spelling.

    Does NOT conflate `!cancelled()` with `always()` into one normalized
    string — they stay textually distinct here. Whether a caller treats them
    as interchangeably ACCEPTABLE is a `job_if_equals` decision (it may take
    a list of equally-valid expressions), not something this function
    decides on its own.
    """
    s = _stringify_if(value).strip()
    m = _WRAPPED_EXPR_RE.match(s)
    return m.group(1) if m else s


def _iter_workflow_steps(doc: dict):
    """Yield (job_id, job, step, step_index) for every step in every job of a
    parsed workflow document. `step_index` is the step's position within its
    OWN job's `steps:` list (not a running total across jobs), so it lines up
    directly with `_job_download_artifact_paths`'s `before_index`. Jobs/steps
    of the wrong shape are skipped rather than raised on — a workflow that
    doesn't parse into the expected mapping shape yields nothing, which reads
    as "no matching step found" like any other workflow that genuinely has
    none.
    """
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        for step_index, step in enumerate(job.get("steps") or []):
            if isinstance(step, dict):
                yield job_id, job, step, step_index


def _job_matches(job_id: str, job: dict, job_selector: str | None) -> bool:
    if job_selector is None:
        return True
    if job_selector == job_id:
        return True
    return isinstance(job.get("name"), str) and job["name"] == job_selector


def _job_permission_level(job_body: dict, doc: dict, key: str) -> str | None:
    """The effective permission level GitHub grants scope `key` for this job.

    Job-level `permissions:` REPLACES workflow-level entirely when present
    — they do not merge — whatever shape either one takes: a per-scope
    mapping, or the whole-block string shorthand `read-all` (every scope
    read) / `write-all` (every scope write).
    """
    perms = job_body.get("permissions")
    if perms is None:
        perms = doc.get("permissions")
    if perms == "write-all":
        return "write"
    if perms == "read-all":
        return "read"
    if isinstance(perms, dict):
        return perms.get(key)
    return None


def _permission_satisfies(actual: str | None, required: str) -> bool:
    """Does an effective per-scope level satisfy a requirement?

    `write` satisfies both a `read` and a `write` requirement (GitHub
    grants read access implicitly with write); `read` satisfies only a
    `read` requirement; `none` and an undeclared scope satisfy neither —
    this is what makes a job-level `permissions: read-all` (which REPLACES
    a more generous workflow-level block) correctly fail a `write`
    requirement instead of silently reading the workflow-level value it no
    longer grants — the skill's own "most subtle and most common" pitfall.
    """
    if actual == "write":
        return True
    if actual == "read":
        return required == "read"
    return False


# Recognizes the common GitHub Actions idioms for gating on one job
# outcome, capturing an optional leading `!` so a negated form (`!contains(
# needs.*.result, 'failure')`, meaning "nothing failed") is distinguishable
# from a direct one (`contains(needs.*.result, 'failure')`, meaning
# "something failed") — negating a check for the OTHER outcome is exactly
# as common a way to write "gate on this outcome" as naming it directly,
# and both must be recognized for `_gates_on_outcome` to tell a real
# multi-job wiring from its inversion. `.result != '<outcome>'` (issue #86
# review round 4, N2) is a separate alternative, not folded into the `!`
# prefix above: it negates the EQUALITY, not the whole gate, so its polarity
# flips on its own — `!= 'success'` gates on failure (fires on failure,
# cancelled AND skipped, stricter than `== 'failure'`), `!= 'failure'` gates
# on success.
_OUTCOME_GATE_RE = re.compile(
    r"(?P<neg>!\s*)?"
    r"(?:contains\([^)]*?,\s*'(?P<contains_outcome>failure|success)'\)"
    r"|\.result\s*==\s*'(?P<eq_outcome>failure|success)'"
    r"|\.result\s*!=\s*'(?P<ne_outcome>failure|success)'"
    r"|\b(?P<bare_outcome>failure|success)\(\))")


def _gates_on_outcome(step_if: str, outcome: str) -> bool:
    """Does this `if:` expression read as gating on `outcome`
    (`"failure"` or `"success"`)?

    Recognizes `<x>.result == '<outcome>'`, `contains(<x>, '<outcome>')`,
    and the bare `<outcome>()` call, each either naming `outcome` directly
    (not negated) or negating the OTHER outcome (`!contains(<x>,
    '<other>')` means "gate on `outcome`" just as much as naming it
    directly does). This is what lets `visual-regression-post-step` /
    `-resolve-step` catch a fully INVERTED multi-job wiring: swapping which
    call gets which condition swaps which outcome each one's `if:` actually
    reads as gating on, even though both still mention `needs.` and one of
    the two outcome words.

    Also recognizes `<x>.result != '<outcome>'` (issue #86 review round 4,
    N2) as gating on the OTHER outcome from the one named — `!= 'success'`
    reads as "gate on failure", `!= 'failure'` reads as "gate on success" —
    independent of the leading `!\\s*` prefix handled above, since here the
    negation is already inside the `!=` operator itself.
    """
    other = "success" if outcome == "failure" else "failure"
    for m in _OUTCOME_GATE_RE.finditer(step_if):
        ne_named = m.group("ne_outcome")
        if ne_named is not None:
            if ne_named == other:
                return True
            continue
        named = m.group("contains_outcome") or m.group("eq_outcome") or m.group("bare_outcome")
        negated = bool(m.group("neg"))
        if named == outcome and not negated:
            return True
        if named == other and negated:
            return True
    return False


# The log-capture idiom SKILL.md's own snippets prescribe:
# `... 2>&1 | tee /tmp/<log>.log`. Matches `tee` and, loosely, `tee -a`.
_TEE_TARGET_RE = re.compile(r"\btee\s+(?:-a\s+)?(\S+)")

# A `marker:` value that already carries HTML-comment syntax — the composite
# wraps `marker` in its own `<!-- -->` to find a prior post, so a caller that
# pre-wraps it too breaks that lookup (issue #86 review round 3, N8).
_HTML_COMMENT_TOKEN_RE = re.compile(r"<!--|-->")

# The skill's documented "don't repeat" pattern, applied to any `with:` value
# rather than only whichever key a given check happens to test.
_JOB_STATUS_RE = re.compile(r"\bjob\.status\b")


def _job_tee_targets(job_body: dict, before_index: int | None = None) -> list[str]:
    """Every path a `tee` invocation in this job's `run:` steps wrote to, in
    step order. Lexical, on purpose, once the step is already selected
    structurally: only a matched step's `run:` leaf STRING is scanned for
    `tee <path>`, never a raw scan of the whole file.

    `before_index`, when given, limits the walk to steps strictly BEFORE
    that position — mirrors `_job_download_artifact_paths`'s ordering
    guarantee: a `tee` that runs later hasn't captured anything yet by the
    time an earlier step's `log-file:` would need it.
    """
    steps = job_body.get("steps") or []
    if before_index is not None:
        steps = steps[:before_index]
    targets = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        run_body = step.get("run")
        if not isinstance(run_body, str):
            continue
        targets.extend(_TEE_TARGET_RE.findall(run_body))
    return targets


def _job_download_artifact_paths(job_body: dict, before_index: int | None = None) -> list[str]:
    """Every location an `actions/download-artifact` step in this job
    extracted to, in step order. Structural: walks `steps:`, only a matched
    step's `with.path` leaf is read as a string. A step with no `path:` (or
    an empty one) extracts into the job's workspace ROOT — contributes `""`,
    a sentinel `_log_file_reachable` treats as "any relative path", not
    "nothing" — `actions/download-artifact` does that by default, it isn't
    a no-op.

    `before_index`, when given, limits the walk to steps strictly BEFORE
    that position in the job's `steps:` list — a download that happens
    later in the job hasn't run yet by the time an earlier step executes,
    so it contributes no path a step ahead of it could actually reach.
    """
    steps = job_body.get("steps") or []
    if before_index is not None:
        steps = steps[:before_index]
    paths = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        uses = step.get("uses")
        if not isinstance(uses, str) or not uses.split("@", 1)[0].endswith("download-artifact"):
            continue
        with_block = step.get("with") if isinstance(step.get("with"), dict) else {}
        path = with_block.get("path")
        paths.append(path.rstrip("/") if isinstance(path, str) and path else "")
    return paths


def _log_file_reachable(log_file, download_paths: list[str]) -> bool:
    """Does `log_file` fall under a location an earlier download-artifact
    step in the same job extracted to?

    `""` in `download_paths` is the workspace-ROOT sentinel (see
    `_job_download_artifact_paths`): any relative `log_file` is reachable
    from it, since that's where a path-less download lands everything. An
    absolute `log_file` is never "under" the root sentinel — it names a
    specific filesystem location, download or no download.
    """
    if not isinstance(log_file, str) or not log_file:
        return False
    for p in download_paths:
        if p == "":
            if not os.path.isabs(log_file):
                return True
        elif log_file == p or log_file.startswith(p + "/"):
            return True
    return False


def workflow_step_uses(workspace: str, patterns: list[str], *,
                       uses_suffix: str | None = None,
                       job: str | None = None,
                       job_if_equals: str | list[str] | None = None,
                       job_needs_nonempty: bool = False,
                       job_permissions_include: dict | None = None,
                       if_contains: str | None = None,
                       if_gates_on_outcome: str | None = None,
                       with_present: list[str] | None = None,
                       with_equals: dict | None = None,
                       with_tag_ref: str | None = None,
                       log_file_matches_download: bool = False,
                       log_file_matches_tee: bool = False,
                       marker_not_html_comment: bool = False,
                       with_forbids_job_status: bool = False,
                       marker_pairs_with_mode: str | None = None,
                       unique_with_key: str | None = None,
                       min_matches: int = 1) -> tuple[bool, str]:
    """Structural assertions over parsed workflow YAML: does at least
    `min_matches` step, across every workflow matched by `patterns`, call a
    `uses:` action whose ref (the part before '@') ends with `uses_suffix`,
    inside a job matching `job` (by id or `name:`), satisfying the given
    job/step-level shape?

    Every constraint below is decided structurally, by walking the parsed
    jobs/steps tree — never a line or regex scan deciding WHICH step or job is
    in play. Only once a step is already selected does a `with:`/`if:`/`uses:`
    VALUE (a leaf string) get a plain string test — e.g. `if_contains`,
    `with_equals`, `with_tag_ref` — which is the "leaf strings tested
    lexically" half of the house rule, not a shortcut around the structural
    half. `job_if_equals` compares against `_normalize_expr`, not the raw
    `if:` string, so a skill-faithful `if: ${{ always() }}` matches a check
    written against the bare `always()` spelling. It takes either a single
    expression or a list of equally-acceptable ones — e.g.
    `["always()", "!cancelled()"]` where a skill leaves the exact spelling
    unprescribed and more than one is a genuinely correct answer.

    `if_gates_on_outcome` (`"failure"` or `"success"`) asserts the step's
    `if:` reads, by `_gates_on_outcome`, as gating on that outcome — not
    merely that it mentions `needs.` or the outcome word at all. This is
    what catches a fully INVERTED multi-job wiring (the post call gated on
    success, the resolve call gated on failure): both calls can still
    satisfy `if_contains="needs."` and even mention the same outcome word
    under negation, so only reading the gate's actual polarity tells them
    apart.

    `job_permissions_include` asserts a `{perm: value}` mapping is in scope
    for the qualifying step's job: the job's OWN `permissions:` block if it
    declares one (job-level permissions REPLACE workflow-level ones in real
    GitHub Actions — they do not merge), else the workflow-level
    `permissions:` block — either one may be a per-scope mapping or the
    whole-block string shorthand `read-all`/`write-all` (see
    `_job_permission_level`/`_permission_satisfies`). This is how
    `pull-requests: write` — the skill's own "most subtle and most common"
    pitfall — becomes a decidable fact instead of something left entirely
    to the judge.

    `log_file_matches_download` requires the qualifying step's `with.log-file`
    value to fall under a path an `actions/download-artifact` step earlier in
    the SAME job downloaded to — in a multi-job workflow the log is captured
    on a different runner (the matrix job), so a `log-file:` naming a path
    with no artifact transport into the calling job is unreachable at
    runtime, not merely unverified.

    `log_file_matches_tee` requires the qualifying step's `with.log-file`
    value to EQUAL a path an earlier `run:` step in the SAME job actually
    `tee`'d to — for the single-job shape, where the log is captured with
    `... 2>&1 | tee /tmp/<log>.log` in the same job that calls the
    composite, `log-file: /tmp/whatever-else.log` is any-non-empty-string
    correct today but points at a file that was never written.

    `marker_not_html_comment` rejects a qualifying step whose `with.marker`
    value itself contains `<!--` or `-->`. The composite already wraps
    `marker` in an HTML comment to find its own prior post (see the vendored
    action's own `marker` input description); a caller pre-wrapping it too
    breaks that lookup, it isn't merely redundant.

    `with_forbids_job_status` rejects a qualifying step if ANY `with:` value
    — not only whichever key a `with_equals`/`with_present` constraint
    happens to test — contains the literal `job.status`. The skill's
    documented "don't repeat" pattern (`${{ job.status }}` silently expands
    to empty inside the composite's context) applies to the whole `with:`
    block, not just one key.

    `marker_pairs_with_mode` (a mode name, e.g. `"resolve"`) requires a
    qualifying step's `marker` to equal the `marker` of every OTHER
    uses_suffix-matching step in the SAME file and job whose own
    `with.mode` equals this value — the documented convention pairs a
    `post` and a `resolve` call under one shared marker, and handing each
    one a *different* marker leaves the resolve unable to find the post's
    comment. Passes vacuously when no such counterpart step exists (e.g.
    checking a lone `post` step with no matching `resolve` yet).

    `unique_with_key` switches to a second mode instead of the match/count
    check above: collect every `uses_suffix`-matching step's `with[key]`
    value across every matched file, group by value, and fail if any value's
    steps span more than one FILE. This is deliberately looser than "unique
    per step": the documented convention pairs a `post` and a `resolve` call
    in the SAME workflow under the SAME marker (that's the dedup key, not a
    collision) — only two DIFFERENT workflows sharing one marker is the
    clobbering bug.

    Caution for fixture authors: this function fails OPEN on a workflow file
    `_load_workflows` could not parse (`doc is None` — silently skipped,
    contributing zero matches rather than a problem) and never walks a job's
    own `uses:` (a reusable-workflow call, `jobs.<id>: {uses: ./other.yml}`,
    has no `steps:` at all) — only step-level `uses:` inside a job's
    `steps:` list. Pair this check with `yaml_parses` on the same `paths` so
    an unparseable file fails loudly instead of reading as "no matching step,
    as expected."
    """
    matches = []  # (rel, doc, job_id, job, step, step_index) for every uses_suffix-matching step
    for rel, doc in _load_workflows(workspace, patterns):
        if doc is None:
            continue
        for job_id, job_body, step, step_index in _iter_workflow_steps(doc):
            uses = step.get("uses")
            if not isinstance(uses, str):
                continue
            ref = uses.split("@", 1)[0]
            if uses_suffix is not None and not ref.endswith(uses_suffix):
                continue
            matches.append((rel, doc, job_id, job_body, step, step_index))

    if unique_with_key is not None:
        by_value: dict[str, set[str]] = {}
        for rel, _doc, _job_id, _job_body, step, _step_index in matches:
            with_block = step.get("with")
            if not isinstance(with_block, dict):
                continue
            value = with_block.get(unique_with_key)
            if value is None:
                continue
            by_value.setdefault(str(value), set()).add(rel)
        dupes = {v: sorted(files) for v, files in by_value.items() if len(files) > 1}
        if dupes:
            detail = "; ".join(f"{v!r} used in {', '.join(fs)}" for v, fs in sorted(dupes.items()))
            return (False, f"{unique_with_key!r} not unique per workflow: {detail}")
        return (True, f"every {unique_with_key!r} distinct across workflows "
                      f"({len(by_value)} value(s) seen)")

    qualifying = []
    for rel, doc, job_id, job_body, step, step_index in matches:
        if job is not None and not _job_matches(job_id, job_body, job):
            continue
        if job_if_equals is not None:
            accepted = [job_if_equals] if isinstance(job_if_equals, str) else job_if_equals
            if _normalize_expr(job_body.get("if")) not in accepted:
                continue
        if job_needs_nonempty:
            needs = job_body.get("needs")
            has_needs = (isinstance(needs, str) and bool(needs)) or \
                       (isinstance(needs, list) and len(needs) > 0)
            if not has_needs:
                continue
        if job_permissions_include:
            if any(not _permission_satisfies(_job_permission_level(job_body, doc, k), v)
                  for k, v in job_permissions_include.items()):
                continue
        if if_contains is not None and if_contains not in _stringify_if(step.get("if")):
            continue
        if if_gates_on_outcome is not None and not _gates_on_outcome(
            _stringify_if(step.get("if")), if_gates_on_outcome
        ):
            continue
        with_block = step.get("with") if isinstance(step.get("with"), dict) else {}
        if with_present and any(not with_block.get(k) for k in with_present):
            continue
        if with_equals and any(with_block.get(k) != v for k, v in with_equals.items()):
            continue
        if with_tag_ref is not None and not _looks_like_a_tag(with_block.get(with_tag_ref)):
            continue
        if log_file_matches_download:
            log_file = with_block.get("log-file")
            download_paths = _job_download_artifact_paths(job_body, before_index=step_index)
            if not _log_file_reachable(log_file, download_paths):
                continue
        if log_file_matches_tee:
            log_file = with_block.get("log-file")
            tee_targets = _job_tee_targets(job_body, before_index=step_index)
            if not isinstance(log_file, str) or log_file not in tee_targets:
                continue
        if marker_not_html_comment:
            marker_value = with_block.get("marker")
            if isinstance(marker_value, str) and _HTML_COMMENT_TOKEN_RE.search(marker_value):
                continue
        if with_forbids_job_status and any(
            isinstance(v, str) and _JOB_STATUS_RE.search(v) for v in with_block.values()
        ):
            continue
        if marker_pairs_with_mode is not None:
            counterparts = []
            for r2, _d2, j2, _jb2, s2, _si2 in matches:
                if r2 != rel or j2 != job_id or s2 is step:
                    continue
                w2 = s2.get("with") if isinstance(s2.get("with"), dict) else {}
                if w2.get("mode") == marker_pairs_with_mode:
                    counterparts.append(w2.get("marker"))
            if counterparts and any(cm != with_block.get("marker") for cm in counterparts):
                continue
        qualifying.append((rel, job_id))

    if len(qualifying) >= min_matches:
        return (True, f"{len(qualifying)} matching step(s): "
                      f"{', '.join(f'{rel}:{jid}' for rel, jid in qualifying)}")
    return (False,
            f"expected >= {min_matches} step(s) matching (uses ending "
            f"{uses_suffix!r}, job={job!r}, job_if_equals={job_if_equals!r}, "
            f"job_needs_nonempty={job_needs_nonempty!r}, if_contains={if_contains!r}, "
            f"if_gates_on_outcome={if_gates_on_outcome!r}, "
            f"with_present={with_present!r}, with_equals={with_equals!r}, "
            f"with_tag_ref={with_tag_ref!r}, marker_not_html_comment={marker_not_html_comment!r}, "
            f"with_forbids_job_status={with_forbids_job_status!r}, "
            f"marker_pairs_with_mode={marker_pairs_with_mode!r}) — found {len(qualifying)} of "
            f"{len(matches)} step(s) with a matching `uses:`")


# `${{ ... github.event.<x> ... }}` or `${{ ... inputs.<x> ... }}` anywhere
# inside one `${{ }}` expression — the untrusted-payload half of the classic
# Actions script-injection vector (the composite action's own "Security: env
# vars, not interpolation" rule exists for exactly this reason, for its
# embedded github-script calls; this check applies the same rule to `run:`).
_EVENT_OR_INPUT_INTERPOLATION_RE = re.compile(
    r"\$\{\{[^}]*\b(?:github\.event\.|inputs\.)[^}]*\}\}")


def no_event_interpolation_in_run(workspace: str, patterns: list[str]) -> tuple[bool, str]:
    """No `run:` step body may interpolate `${{ github.event.* }}` or
    `${{ inputs.* }}` directly into the shell command.

    Structural first, lexical only at the leaf: the YAML is parsed and walked
    to every step's `run:` VALUE, and only that leaf string is regex-tested —
    never a raw line scan of the file, which cannot tell a `run:` body apart
    from a comment, a `with:` block, or an unrelated string elsewhere in the
    same document.

    Fails OPEN on a workflow `_load_workflows` could not parse (silently
    skipped — zero problems found there reads the same as "no interpolation
    found"), and never walks a job's own `uses:` for a reusable-workflow call
    (such a job has no `steps:`, hence no `run:`, so nothing here would see
    one anyway). Pair with `yaml_parses` on the same `paths` for the former.
    """
    problems = []
    for rel, doc in _load_workflows(workspace, patterns):
        if doc is None:
            continue
        for job_id, _job_body, step, _step_index in _iter_workflow_steps(doc):
            run_body = step.get("run")
            if not isinstance(run_body, str):
                continue
            hits = _EVENT_OR_INPUT_INTERPOLATION_RE.findall(run_body)
            if hits:
                label = step.get("name") or step.get("id") or "(unnamed step)"
                problems.append(f"{rel}:{job_id}:{label}: {', '.join(hits)}")
    return (not problems, "no run: step interpolates github.event.* or inputs.*"
            if not problems else "; ".join(problems))


# owner/repo prefix for the one carve-out from the fleet's SHA-pinning rule:
# a ref into this account's own cms-platform, which stays on its release tag.
_CMS_PLATFORM_REMOTE_PREFIX = "Adam-S-Daniel/cms-platform/"


def post_failure_comment_reference_valid(workspace: str, patterns: list[str], *,
                                         uses_suffix: str = "/post-failure-comment"
                                         ) -> tuple[bool, str]:
    """Every step that calls the failure-comment composite resolves it one of
    two ways the issue actually allows — never merely a shape the skill
    doesn't happen to prescribe:

    - the vendored LOCAL path (any `./...` ref ending in `uses_suffix` — the
      skill's condition 3 only requires the action's directory be present,
      not any particular checkout shape), or
    - a REMOTE `Adam-S-Daniel/cms-platform/...@<tag>` ref, pinned to a
      release TAG — never a bare 40-hex commit SHA, which is what the
      fleet's general SHA-pinning rule would (wrongly) produce here, since
      this is the one ref AGENTS.md carves out to stay on its tag instead.

    If the workflow ALSO checks cms-platform out via `actions/checkout`
    (`with.repository: Adam-S-Daniel/cms-platform`) — which the remote form
    doesn't need at all — that checkout's `ref:` must be tag-shaped too, for
    the same reason. A checkout is never REQUIRED by this check: an earlier
    version of it demanded one and rejected both shapes the issue actually
    allows (the vendored local path, and the literal remote-tag carve-out)
    for the sole reason that neither happens to check anything out.
    """
    problems = []
    checked_any = False
    for rel, doc in _load_workflows(workspace, patterns):
        if doc is None:
            continue
        for job_id, _job_body, step, _step_index in _iter_workflow_steps(doc):
            uses = step.get("uses")
            if not isinstance(uses, str):
                continue
            ref, _, version = uses.partition("@")
            if ref.endswith(uses_suffix):
                checked_any = True
                if ref.startswith("./"):
                    continue
                if not ref.startswith(_CMS_PLATFORM_REMOTE_PREFIX):
                    problems.append(f"{rel}:{job_id}: `uses: {uses}` is neither the "
                                    f"vendored local path nor a "
                                    f"{_CMS_PLATFORM_REMOTE_PREFIX}...@<tag> ref")
                elif not _looks_like_a_tag(version):
                    problems.append(f"{rel}:{job_id}: `uses: {uses}` must be pinned "
                                    f"to a release tag, not {version!r}")
            elif ref.endswith("actions/checkout"):
                with_block = step.get("with") if isinstance(step.get("with"), dict) else {}
                if with_block.get("repository") == "Adam-S-Daniel/cms-platform":
                    checkout_ref = with_block.get("ref")
                    if not _looks_like_a_tag(checkout_ref):
                        problems.append(f"{rel}:{job_id}: cms-platform checkout "
                                        f"`ref:` {checkout_ref!r} is not tag-shaped")
    if not checked_any:
        problems.append(f"no step found with a `uses:` ending {uses_suffix!r}")
    return (not problems,
            "post-failure-comment resolved via the vendored local path or a "
            "tag-pinned remote ref, and any cms-platform checkout is tag-pinned"
            if not problems else "; ".join(problems))


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
    "file_matches_excluding_comments": file_matches_excluding_comments,
    "transcript_matches": transcript_matches,
    "file_count": file_count,
    "link_targets_exist": link_targets_exist,
    "git_ref_unchanged": git_ref_unchanged,
    "no_git_config_names_path": no_git_config_names_path,
    "git_remote_url_is": git_remote_url_is,
    "reaper_ran_in_standalone_repo": reaper_ran_in_standalone_repo,
    "reaper_avoided_paths": reaper_avoided_paths,
    "git_worktree_list_matches": git_worktree_list_matches,
    "pins_match_reference": pins_match_reference,
    "platform_refs_on_tag": platform_refs_on_tag,
    "workflow_step_uses": workflow_step_uses,
    "no_event_interpolation_in_run": no_event_interpolation_in_run,
    "post_failure_comment_reference_valid": post_failure_comment_reference_valid,
    "dir_listing_matches": dir_listing_matches,
}


_CHECK_META_KEYS = {"id", "description", "type", "paths"}
_WORKFLOW_STEP_USES_KEYS = {
    "uses_suffix", "job", "job_if_equals", "job_needs_nonempty",
    "job_permissions_include", "if_contains", "if_gates_on_outcome", "with_present",
    "with_equals", "with_tag_ref", "log_file_matches_download", "log_file_matches_tee",
    "marker_not_html_comment", "with_forbids_job_status", "marker_pairs_with_mode",
    "unique_with_key", "min_matches",
}

# Every fixture-suppliable constraint key each check `type` accepts, beyond
# `_CHECK_META_KEYS` and the `seed`/`transcript` kwargs `run_checks` injects
# itself (never fixture-suppliable, so they're not listed here). A type
# absent from this map — `yaml_parses`, `non_remote_refs_unchanged`,
# `event_only_workflows_unfiltered`, `required_checks_early_skip`,
# `no_event_interpolation_in_run` — takes NO constraint keys at all:
# `workspace` + `paths` (+ the injected `seed`) fully determine what it checks.
_CHECK_ALLOWED_KEYS: dict[str, set[str]] = {
    "changeset_triggers": {"changeset", "expect_triggered", "expect_skipped"},
    "file_matches": {"must_match", "must_not_match"},
    "file_matches_excluding_comments": {"must_match", "must_not_match"},
    "transcript_matches": {"must_match", "must_not_match"},
    "workflow_step_uses": _WORKFLOW_STEP_USES_KEYS,
    "post_failure_comment_reference_valid": {"uses_suffix"},
    "files_unchanged": {"by"},
    "dir_listing_matches": {"expected", "expected_file", "ignore"},
    "file_digests_match": {"sha256"},
    "git_ref_unchanged": {"path", "ref", "expected", "snapshot"},
    "no_git_config_names_path": {"forbidden_path", "exclude"},
    "git_remote_url_is": {"path", "remote", "expected_path"},
    "reaper_ran_in_standalone_repo": {"log_path"},
    "reaper_avoided_paths": {"log_path", "forbidden_paths"},
    "git_worktree_list_matches": {"path", "expected_names"},
    "uses_refs_sha_pinned": {"platform_prefix"},
    "pins_match_reference": {"reference", "platform_prefix"},
    "platform_refs_on_tag": {"platform_prefix", "tag", "min_refs"},
    "file_count": {"min", "max", "min_count", "max_count"},
    "link_targets_exist": {"link_pattern", "base"},
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

    Every check's keys are validated against `_CHECK_ALLOWED_KEYS` before
    running, for every type — not just `workflow_step_uses` — so an
    unrecognized key (a typo like `job_ifequals`, or a constraint that
    belongs to a different check type entirely) raises rather than being
    silently dropped from `kwargs`: dropped, the fixture would run a WEAKER
    check than written and still report green, which is worse than failing
    loudly at load time.
    """
    results = []
    for check in fixture.get("objective_checks", []):
        fn = CHECKS.get(check["type"])
        if fn is None:
            results.append({"id": check["id"], "passed": False,
                            "detail": f"unknown check type {check['type']!r}"})
            continue
        allowed = _CHECK_ALLOWED_KEYS.get(check["type"], set())
        extra = set(check) - _CHECK_META_KEYS - allowed
        if extra:
            raise ValueError(f"unknown {check['type']!r} constraint key(s) in "
                            f"check {check.get('id')!r}: {sorted(extra)}")
        kwargs = {key: check[key] for key in allowed if key in check}
        if check["type"] in ("non_remote_refs_unchanged", "files_unchanged", "dir_listing_matches"):
            kwargs["seed"] = seed
        elif check["type"] == "transcript_matches":
            kwargs["transcript"] = transcript
        elif check["type"] == "file_count":
            # Fixture-YAML spelling ("min"/"max") and the Python-parameter
            # spelling ("min_count"/"max_count") are both accepted constraint
            # keys (see _CHECK_ALLOWED_KEYS), but neither "min" nor "max" is
            # itself a valid file_count() keyword argument — rebuilt from
            # scratch here rather than added to the generic kwargs above, so
            # the wrongly-named "min"/"max" keys the generic pass may have
            # collected never reach the call below.
            kwargs = {
                "min_count": check.get("min", check.get("min_count")),
                "max_count": check.get("max", check.get("max_count")),
            }
        passed, detail = fn(workspace, check.get("paths", []), **kwargs)
        results.append({"id": check["id"], "passed": passed, "detail": detail})
    return results
