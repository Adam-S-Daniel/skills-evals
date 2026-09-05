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
    "yaml_parses": yaml_parses,
    "non_remote_refs_unchanged": non_remote_refs_unchanged,
    "changeset_triggers": changeset_triggers,
    "required_checks_early_skip": required_checks_early_skip,
    "event_only_workflows_unfiltered": event_only_workflows_unfiltered,
    "files_unchanged": files_unchanged,
    "file_digests_match": file_digests_match,
    "file_matches": file_matches,
    "transcript_matches": transcript_matches,
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
        elif check["type"] == "dir_listing_matches":
            kwargs["expected"] = check.get("expected")
            kwargs["expected_file"] = check.get("expected_file")
            kwargs["ignore"] = check.get("ignore")
        elif check["type"] == "file_digests_match":
            kwargs["sha256"] = check.get("sha256")
        passed, detail = fn(workspace, check.get("paths", []), **kwargs)
        results.append({"id": check["id"], "passed": passed, "detail": detail})
    return results
