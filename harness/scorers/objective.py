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

from . import wrapping

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
# committed material this harness can read, so the material that came from
# it can be named exactly, in any shape it is pasted back in — and
# everything else is the agent's writing, however it chose to format it.
#
# The UNIT of provenance is the SENTENCE, and the decision is taken after
# hard wrapping is undone. It used to be the LINE, and a line is not a unit
# of anything: the same words re-broken across different lines were a
# different set of lines, so a paste re-wrapped, re-selected, punctuated,
# tabled or salted with invisibles walked past the scan; and a genuine
# paragraph hard-wrapped at 72 lost two of ITS OWN lines because a wrap
# happened to land where the seed's line ends did.

# The floor on a piece of seed material. A sentence shorter than this the
# agent could plausibly have written itself: "Thanks," and a bare name are
# in every reply and in some seeds, and claiming them for the seed would
# take the agent's own sign-off away from it. Inside a MARKED quotation
# there is no floor — the markup already says the block is a quotation, so
# a short sentence in it needs only to be the seed's.
_SEED_MATERIAL_FLOOR = 24

# The floor on a piece of seed material matched WHOLE — a sentence of the
# seed's, reproduced end to end. Lower than the run floor on purpose: an
# exact sentence match is far stronger evidence of a paste than the same
# number of characters appearing as a fragment of a longer seed sentence,
# which prose about the same subject arrives at by accident. Still well
# above "Thanks," and a bare name, which is what the floor exists for.
_SEED_SENTENCE_FLOOR = 12

# A blockquote marker: any indent, a `>`, and any run of spaces after it.
# Applied repeatedly, so `> > ` and `>  ` unwrap too. Unlimited indent on
# purpose — an indented deliverable is still the deliverable, and one to
# three spaces (or a tab) in front of a reply used to cost it the checks
# its own opening satisfies.
_QUOTE_MARKER_RE = re.compile(r"^[^\S\n]*>[^\S\n]*")
_FENCE_RE = re.compile(r"^[^\S\n]*(`{3,}|~{3,})")
_LIST_MARKER_RE = re.compile(r"^[^\S\n]*(?:[-*+•]|\d+[.)])[^\S\n]+")

# The tags that are WRAPPER and nothing else, and only when they carry no
# attributes. A bare `<blockquote>`, `</details>` or `<pre>` is markup the
# agent wrapped around something; `<span title="we can leverage this">`,
# `<img alt="...synergy...">` and `<!-- circle back -->` are text the agent
# WROTE, attribute values included, and each of those used to switch the
# avoid-list ban off by the simple trick of being a line with a tag on it.
# A tag outside this set, or one carrying an attribute, stays exactly as it
# arrived — including mid-line, where a general tag strip once let
# `I<leverage synergy robust> was looking...` normalise onto a seed line and
# be dropped whole.
_WRAPPER_TAGS = ("blockquote", "details", "summary", "pre", "code", "div",
                 "p", "br")
_BARE_WRAPPER_TAG_RE = re.compile(
    r"</?(?:" + "|".join(_WRAPPER_TAGS) + r")\s*/?>", re.I)
# The block wrappers that bracket a quotation. `<summary>` is the LABEL on a
# `<details>` rather than part of what it discloses, but the label's TEXT is
# still the agent's, so it is not a delimiter: only its tags come off.
_HTML_BLOCK_TAG = r"blockquote|details|pre"
_HTML_BLOCK_OPEN_RE = re.compile(rf"^\s*<({_HTML_BLOCK_TAG})\s*>\s*$", re.I)
_HTML_BLOCK_CLOSE_RE = re.compile(rf"^\s*</({_HTML_BLOCK_TAG})\s*>\s*$", re.I)

# A Markdown table's alignment row: pipes, dashes and colons only. It is the
# table's own scaffolding, like a fence delimiter, and carries no words.
_TABLE_RULE_RE = re.compile(r"^[^\S\n]*\|[-:|\s]*\|[^\S\n]*$")

# Characters that take up no width and can hide a banned term inside a word,
# or break a paste into pieces the seed index cannot match: the soft hyphen,
# the zero-width and bidi marks, the invisible operators, the combining
# grapheme joiner, the Mongolian vowel separator, the variation selectors,
# the BOM, a stray NUL, and the two blank glyphs `\s` does not match
# (Braille blank, Hangul filler). `lever­age` and `deep​ dive` read
# to the operator as the banned terms and are scored as them, and one
# U+2062 per line no longer buys a paste its provenance back.
_INVISIBLE_RE = re.compile(
    "[\u00ad\u034f\u061c\u180b-\u180e\u200b-\u200f\u2060-\u2064"
    "\u206a-\u206f\u2800\u3164\ufe00-\ufe0f\ufeff\uffa0\x00]")

# A sentence ends at `.`, `!`, `?` or `;` FOLLOWED BY WHITESPACE, or at the
# end of a line. The trailing-whitespace requirement is what keeps
# `dana.whitcombe@example.com` in one piece; the line boundary is what ends
# a list item and a table row, neither of which is punctuated.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?;])[^\S\n]+")

# Everything that is not a letter, a digit or a space, dropped before two
# pieces of text are compared. Provenance is about WORDS: a paste that
# swapped every full stop for an exclamation mark, or ran the material
# through a Markdown table, is the same material.
_UNWORD_RE = re.compile(r"[^\w\s]|_", re.UNICODE)


class FixtureError(ValueError):
    """A fixture asks for something this scorer cannot honour as written."""


class SeedTooLarge(FixtureError):
    """A seed file is bigger than the provenance index will read.

    Named rather than silent: a truncated index answers "not the seed's" for
    every sentence past the cap, which reads as the agent having written the
    material it actually pasted.
    """


# The provenance index reads at most this much of any one seed file. A cap
# is needed because the index is rebuilt per check and holds each file's
# whole text casefolded; a MiB is far above any writing fixture's seed (the
# largest in this repo is under 2 KB) and far below a file worth holding.
# Past it the read RAISES rather than truncating — see `SeedTooLarge`.
_SEED_READ_CAP = 1 << 20

def _key(text: str) -> str:
    """`text` reduced to the words in it.

    Casefolded, every character that is not a letter, a digit or a space
    dropped, whitespace collapsed. Two pieces of text with the same key say
    the same thing: provenance is about WORDS, so a paste that swapped every
    full stop for an exclamation mark, ran the material through a Markdown
    table, or re-wrapped it at a different column is the same material.
    """
    return re.sub(r"\s+", " ", _UNWORD_RE.sub(" ", text.casefold())).strip()


def _sentences(line: str) -> list[str]:
    """One logical line split into the sentences it carries."""
    return [part.strip() for part in _SENTENCE_SPLIT_RE.split(line)
            if part.strip()]


def _strip_wrapper(line: str) -> tuple[str, bool]:
    """(`line` with its wrapper removed, was it wrapper and nothing else?).

    Wrapper is leading whitespace, `>` runs with any number of spaces after
    them, list markers, and the bare tags in `_WRAPPER_TAGS`. Everything
    else is the agent's text and stays exactly as it arrived — an HTML
    comment, a tag outside that set, a tag carrying attributes, and the
    attribute values with it.
    """
    stripped = line
    while True:
        shorter = _LIST_MARKER_RE.sub("", _QUOTE_MARKER_RE.sub(
            "", stripped, count=1), count=1)
        if shorter == stripped:
            break
        stripped = shorter
    stripped = stripped.strip()
    bare = _BARE_WRAPPER_TAG_RE.sub("", stripped).strip()
    return bare, bool(stripped) and not bare


def _dequote(line: str) -> str:
    """`line` with its blockquote markers removed, however nested.

    Tags and fence delimiters stay: this is what the block scan reads, and a
    fence or an HTML wrapper inside a `> ` quote has to still look like one.
    """
    while True:
        shorter = _QUOTE_MARKER_RE.sub("", line, count=1)
        if shorter == line:
            return line
        line = shorter


def _seed_index(seed: str | None) -> tuple[set[str], list[str]]:
    """(the seed's sentences, one word-key per seed FILE) — all as keys.

    Every text file under `seed` is read; a file carrying a NUL in its first
    `_SEED_READ_CAP` bytes is taken for a binary and skipped, which is how
    the fake binaries a Class B seed ships stay out of the index. Each
    file's wrapper-stripped lines are joined by a space before the key is
    taken, so a sentence the seed hard-wrapped is one run in the index; the
    files are kept APART, so a run can never span a boundary that was never
    adjacent to begin with.
    """
    sentences: set[str] = set()
    wholes: list[str] = []
    if not seed or not os.path.isdir(seed):
        return sentences, wholes
    for root, dirs, files in os.walk(seed):
        dirs.sort()
        for name in sorted(files):
            path = os.path.join(root, name)
            try:
                with open(path, "rb") as f:
                    raw = f.read(_SEED_READ_CAP + 1)
            except OSError:
                continue
            if b"\x00" in raw:
                continue
            if len(raw) > _SEED_READ_CAP:
                raise SeedTooLarge(
                    f"seed file {os.path.relpath(path, seed)!r} is larger "
                    f"than the {_SEED_READ_CAP}-byte provenance read cap: a "
                    "truncated index would call the material past the cap "
                    "the agent's own writing")
            text = _INVISIBLE_RE.sub("", raw.decode("utf-8", errors="replace"))
            here = []
            for line in text.splitlines():
                if _FENCE_RE.match(line) or _TABLE_RULE_RE.match(line):
                    continue
                body, only_wrapper = _strip_wrapper(line)
                if body and not only_wrapper:
                    here.append(body)
            if not here:
                continue
            flat = " ".join(here)
            wholes.append(_key(flat))
            sentences.update(key for key in map(_key, _sentences(flat)) if key)
    return sentences, wholes


def _is_seed_material(key: str, index: tuple[set[str], list[str]],
                      run_floor: int, sentence_floor: int) -> bool:
    """Is this sentence the SEED's rather than the agent's?

    Two ways to be, with different floors because they are different
    strengths of evidence:

    - it is a contiguous run of some seed file's own text, and long enough
      (`run_floor`) that the agent could not plausibly have arrived at those
      words in that order by writing about the same subject;
    - it IS one of the seed's sentences, whole. An exact sentence match is
      much stronger evidence than a substring, so it earns a lower floor
      (`sentence_floor`) — a short line of the seed's, reproduced end to
      end, is a paste where the same words as a fragment of a longer seed
      sentence would not be.

    Neither can fire on a sentence carrying a word the seed does not have in
    that position: both are exact comparisons over the word key.
    """
    sentences, wholes = index
    if not key:
        return False
    if len(key) >= sentence_floor and key in sentences:
        return True
    # Padded on both sides so a run has to line up on WORD boundaries: an
    # unpadded substring test matches "ana whitcombe" inside "dana
    # whitcombe", which is a fragment of a word rather than a run of the
    # seed's text.
    padded = f" {key} "
    return (len(key) >= run_floor
            and any(padded in f" {whole} " for whole in wholes))


def _wrapped_blocks(content: list[str]) -> list[tuple[int, int]]:
    """(first, last) for every fenced or HTML-wrapped block.

    An unclosed fence or tag runs to the end, as it does in CommonMark.
    """
    out: list[tuple[int, int]] = []
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
        end = min(j, len(content) - 1)
        out.append((i, end))
        i = end + 1
    return out


def _quote_runs(raw: list[str]) -> list[tuple[int, int]]:
    """(first, last) for every run of blockquote lines."""
    out, start = [], None
    for i, line in enumerate(raw):
        if _QUOTE_MARKER_RE.match(line):
            if start is None:
                start = i
        elif start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(raw) - 1))
    return out

def strip_seed_material(text: str, seed: str | None) -> str:
    """`text` with the fixture's own seed material removed, unwrapped.

    The unit of provenance is the SENTENCE, never the line, and the decision
    is taken after hard wrapping is undone. In order:

    1. **Invisibles fold out.** Zero-width characters, soft hyphens,
       variation selectors and the rest take up no width, so they can hide a
       banned term inside a word and break a paste into pieces no index
       matches. They go first, everywhere.
    2. **Wrapper comes off, and only wrapper.** Leading whitespace, `>` runs
       with any number of spaces after them, list markers, fence delimiter
       lines, a table's alignment row, and the bare tags in `_WRAPPER_TAGS`
       when they carry NO attributes. Everything else is the agent's text
       and stays exactly as it arrived — an HTML comment, a tag outside that
       set, a tag with attributes, and its attribute values with it.
    3. **Hard wrapping is undone**, paragraph by paragraph, by the same
       `wrapping` helpers the judge normalises drafts with, so the two
       cannot read the same draft differently. Table pipes are words'
       punctuation and fall out with the rest at key time.
    4. **Each logical line splits into sentences** at `.`, `!`, `?` and `;`
       followed by whitespace, and at the line break that ends a list item
       or a table row.
    5. **A sentence is the SEED's** when its word key (casefolded,
       punctuation dropped, whitespace collapsed) is a long enough
       contiguous run of some seed file's own text, or IS one of the seed's
       sentences whole — see `_is_seed_material` for why those two carry
       different floors. Inside a MARKED quotation (a fence, an HTML
       wrapper, a `>` run) there is no floor at all: the markup already says
       the block is a quotation. A paragraph every sentence of which is the
       seed's, and which carries at least one piece of seed material above
       the floor, goes WHOLE — that is an unmarked paste, and its short
       lines ("Hi Adam,", a bare name) came with it.
    6. **The residue is what is left**, the kept sentences re-joined with
       their line and paragraph breaks, and BOTH `must_match` and
       `must_not_match` are scored over it.

    Two consequences are the point rather than side effects. A sentence the
    agent COMPOSED from the seed's phrases — two seed runs joined by its own
    connective, a seed clause inside its own sentence — carries a word
    ordering the seed does not have and is the agent's writing, so it stays
    and is scored. And a deliverable the agent chose to present as a
    blockquote or inside a fence is not seed material either: it stays,
    unwrapped, and its bans fire. Every calibration example in the skill
    under test is a blockquote, so formatting cannot be allowed to decide
    authorship.

    There is no whole-reply fallback: a reply that is nothing but the quoted
    seed has an empty residue, so its `must_match` checks fail and the
    fixture fails, which is the right answer for a reply that wrote nothing.

    The limit, stated because it is real: a sentence the agent built around
    a fact is its own writing and is scored, even though the fact in it came
    from the seed — and by the same rule, a sentence that reproduces the
    seed's own words end to end is the seed's even when the skill told the
    agent to write exactly that (a plain certifications listing, core move
    8). Dropping it costs no check: the thing a check looks for is never
    only in a line the agent could have copied.
    """
    raw = _INVISIBLE_RE.sub("", text or "").splitlines()
    if not raw:
        return ""
    index = _seed_index(seed)

    # Wrapper off, once, per line. `dequoted` keeps the tags and the fence
    # delimiters so the block scan below can still see them; `payload` is
    # what the agent actually wrote on that line, empty where the line was
    # wrapper and nothing else.
    dequoted, payload = [], []
    for line in raw:
        body, only_wrapper = _strip_wrapper(line)
        dequoted.append(_dequote(line))
        payload.append("" if (only_wrapper or _FENCE_RE.match(line)
                              or _TABLE_RULE_RE.match(line)) else body)

    # Lines inside a marked quotation. There the floor is nil: the markup
    # already says the block is a quotation, so a short sentence in it needs
    # only to be the seed's, not to be beyond the agent's own reach.
    marked: set[int] = set()
    for start, end in _wrapped_blocks(dequoted) + _quote_runs(raw):
        marked.update(range(start, end + 1))

    groups: list[list[int]] = []
    current: list[int] = []
    for i, body in enumerate(payload):
        if body:
            current.append(i)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    width = wrapping.wrap_width([[payload[i] for i in g] for g in groups])

    out: list[str] = []
    for group in groups:
        paragraph: list[list[dict]] = []
        for part in wrapping.unwrap_indices([payload[i] for i in group], width):
            source = [group[k] for k in part]
            # Inside a marked quotation there is no floor: the markup has
            # already said the block is a quotation, so a short sentence in
            # it needs only to be the seed's.
            quoted = all(i in marked for i in source)
            line = []
            for sentence in _sentences(" ".join(payload[i] for i in source)):
                key = _key(sentence)
                line.append({
                    "text": sentence,
                    "seed": _is_seed_material(key, index, 0, 0),
                    "above": _is_seed_material(
                        key, index,
                        0 if quoted else _SEED_MATERIAL_FLOOR,
                        0 if quoted else _SEED_SENTENCE_FLOOR)})
            paragraph.append(line)

        # One rule, over the paragraph's sentences in order: a maximal RUN
        # of consecutive sentences that are all the seed's goes whole, as
        # long as the run carries at least one piece of seed material above
        # the floor. A paste arrives as exactly that — a stretch of the
        # material, nothing else in it — and the short pieces inside the
        # stretch ("Hi Adam,", a bare name, a `To:` header, a fragment a
        # trailing `!` chopped out of a longer sentence) came with it.
        # Anything the agent wrote breaks the run, and a sentence carrying
        # so much as one word the seed does not have there is not the
        # seed's, so it breaks the run too.
        flat = [entry for line in paragraph for entry in line]
        i = 0
        while i < len(flat):
            if not flat[i]["seed"]:
                i += 1
                continue
            j = i
            while j < len(flat) and flat[j]["seed"]:
                j += 1
            if any(entry["above"] for entry in flat[i:j]):
                for entry in flat[i:j]:
                    entry["drop"] = True
            i = j

        rendered = [" ".join(entry["text"] for entry in line
                             if not entry.get("drop"))
                    for line in paragraph]
        rendered = [line for line in rendered if line]
        if rendered:
            out.append("\n".join(rendered))
    return "\n\n".join(out)


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
    "transcript_matches": {"must_match", "must_not_match", "strip_seed"},
    "workflow_step_uses": _WORKFLOW_STEP_USES_KEYS,
    "post_failure_comment_reference_valid": {"uses_suffix"},
    "files_unchanged": {"by"},
    "dir_listing_matches": {"expected", "expected_file", "ignore"},
    "file_digests_match": {"sha256"},
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
            # Opt-in, per check: `strip_seed: true` says this fixture's
            # transcript is the agent's WRITING, so the material it
            # pasted back is not. A fixture whose transcript check asks
            # for something its own seed also carries must not set it.
            #
            # A real boolean, not a truthy value: read by truthiness,
            # `strip_seed: "no"` and `strip_seed: "false"` both turn the
            # pre-pass ON, which is the opposite of what the fixture says
            # and silent about it. YAML already parses `true`/`false`/`yes`/
            # `no` to booleans, so anything arriving here as a string was
            # quoted on purpose or is a typo — either way the fixture does
            # not mean what it says.
            strip_seed = kwargs.pop("strip_seed", False)
            if not isinstance(strip_seed, bool):
                raise FixtureError(
                    f"check {check.get('id')!r}: strip_seed must be a "
                    f"boolean, not {strip_seed!r} — a non-boolean is read "
                    "by truthiness, so a value meaning 'no' turns the seed "
                    "pre-pass on")
            if strip_seed:
                kwargs["seed"] = seed
        passed, detail = fn(workspace, check.get("paths", []), **kwargs)
        results.append({"id": check["id"], "passed": passed, "detail": detail})
    return results
