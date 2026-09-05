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

    Deliberately does NOT treat `!cancelled()` as equivalent to `always()`:
    close in effect for a job that must run regardless of the upstream
    matrix's outcome, but a different expression — `job_if_equals` asserts
    exact equality with what the skill actually prescribes, not semantic
    equivalence with every plausible variant nobody wrote.
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
# multi-job wiring from its inversion.
_OUTCOME_GATE_RE = re.compile(
    r"(?P<neg>!\s*)?"
    r"(?:contains\([^)]*?,\s*'(?P<contains_outcome>failure|success)'\)"
    r"|\.result\s*==\s*'(?P<eq_outcome>failure|success)'"
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
    """
    other = "success" if outcome == "failure" else "failure"
    for m in _OUTCOME_GATE_RE.finditer(step_if):
        named = m.group("contains_outcome") or m.group("eq_outcome") or m.group("bare_outcome")
        negated = bool(m.group("neg"))
        if named == outcome and not negated:
            return True
        if named == other and negated:
            return True
    return False


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
                       job_if_equals: str | None = None,
                       job_needs_nonempty: bool = False,
                       job_permissions_include: dict | None = None,
                       if_contains: str | None = None,
                       if_gates_on_outcome: str | None = None,
                       with_present: list[str] | None = None,
                       with_equals: dict | None = None,
                       with_tag_ref: str | None = None,
                       log_file_matches_download: bool = False,
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
    written against the bare `always()` spelling.

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
        if job_if_equals is not None and _normalize_expr(job_body.get("if")) != job_if_equals:
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
            f"with_tag_ref={with_tag_ref!r}) — found {len(qualifying)} of "
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
    "file_matches": file_matches,
    "transcript_matches": transcript_matches,
    "workflow_step_uses": workflow_step_uses,
    "no_event_interpolation_in_run": no_event_interpolation_in_run,
    "post_failure_comment_reference_valid": post_failure_comment_reference_valid,
}


_CHECK_META_KEYS = {"id", "description", "type", "paths"}
_WORKFLOW_STEP_USES_KEYS = {
    "uses_suffix", "job", "job_if_equals", "job_needs_nonempty",
    "job_permissions_include", "if_contains", "if_gates_on_outcome", "with_present",
    "with_equals", "with_tag_ref", "log_file_matches_download", "unique_with_key",
    "min_matches",
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

    A `workflow_step_uses` check's keys are validated against a fixed set
    before running: an unrecognized key (a typo like `job_ifequals`) raises
    rather than being silently dropped from `kwargs` — dropped, the fixture
    would run a WEAKER check than written and still report green, which is
    worse than failing loudly at load time.
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
        elif check["type"] == "workflow_step_uses":
            extra = set(check) - _CHECK_META_KEYS - _WORKFLOW_STEP_USES_KEYS
            if extra:
                raise ValueError(f"unknown workflow_step_uses constraint key(s) in "
                                f"check {check.get('id')!r}: {sorted(extra)}")
            for key in _WORKFLOW_STEP_USES_KEYS:
                if key in check:
                    kwargs[key] = check[key]
        elif check["type"] == "post_failure_comment_reference_valid":
            if "uses_suffix" in check:
                kwargs["uses_suffix"] = check["uses_suffix"]
        passed, detail = fn(workspace, check.get("paths", []), **kwargs)
        results.append({"id": check["id"], "passed": passed, "detail": detail})
    return results
