#!/usr/bin/env python3
"""Run an eval fixture.

Usage:
    python3 harness/run_eval.py evals/<skill> --arm objective-only
    python3 harness/run_eval.py evals/<skill> --arm both [--registry NAME=PATH ...]
        [--roster PATH] [--no-judge]
    python3 harness/run_eval.py evals/guidance/<id> --arm both [--guidance PATH]

For a skill fixture, the model precedence is `--model` > the fixture's
`model:` > the committed roster > error.

`--arm objective-only` scores a workspace as-is (no agent invocation) — the
pristine seed should FAIL the fixture's checks; a correctly reworked copy
should PASS. `--arm with_skill|without_skill|both` runs the agent under test
(the Claude Code CLI, headless) on a fresh copy of the seed, scores it with
the objective checks and the LLM judge, and writes a summary + report under
`--results-dir` (default `results/`).

TWO SUBJECTS. `subject: skill` (the default) copies one skill from a registry
into `<workspace>/.claude/skills/` and runs with `--setting-sources project`.
`subject: guidance` (#97) delivers a payload assembled from an
`_agent-guidance` checkout into a FRESH per-arm config dir, through the real
fleet-memory hook, and runs with `--setting-sources user,project` — with a
magic-token guard per arm that makes a mis-delivered arm INCONCLUSIVE (exit 2)
rather than a quiet number. See `_run_guidance` below, harness/guidance.py,
and DESIGN.md "Guidance subject".
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import guidance  # noqa: E402
from scorers import judge, objective  # noqa: E402


def load_fixture(eval_dir: Path) -> dict:
    """The fixture, or a named configuration error.

    A-N1-2. A-N1 typed the mapping-valued KEYS; the container that holds them
    was never typed at all. Measured on f9115ce: a fixture whose root is a
    LIST was `AttributeError: 'list' object has no attribute 'get'` and rc 1,
    and an EMPTY file (YAML `None`) was `TypeError: argument of type
    'NoneType' is not iterable` raised inside A-N1's own `_require_mapping` —
    both outside the rc-2 contract, and the second one inside the very
    predicate added to keep shapes out of the harness.
    """
    path = eval_dir / "fixture.yaml"
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise guidance.GuidanceError(
            f"{path} must be a YAML mapping of fixture keys, got "
            f"{type(doc).__name__}"
            + (" (the file is empty)" if doc is None else f": {doc!r}"))
    return doc


# Every timeout knob a fixture can set, as (key, path-to-its-mapping). Each is
# read with `.get(key, <default>)`, which returns the VALUE whenever the key is
# PRESENT — so an explicit YAML null (`guard:` / `  timeout_s:`) yielded None
# and `subprocess.run(timeout=None)` waited forever: measured against a CLI
# that never returns, the only backstop in CI is the 45-minute job kill, with
# no summary and no artifact written. A string yielded a TypeError traceback
# and rc 1, outside the "configuration problem" contract (rc 2, a named
# message, no traceback).
TIMEOUT_KNOBS = (
    ("timeout_s", ()),           # the agent leg, both subjects
    ("setup_timeout_s", ()),     # the fixture's `setup:` hook
    ("timeout_s", ("guard",)),   # the guidance subject's per-arm delivery guard
    ("timeout_s", ("judge",)),   # the judge call
)

# Every fixture key the harness reads as a MAPPING. The knob parents above
# are derived rather than repeated, so a new nested knob cannot arrive without
# its parent being type-checked; `env:` is the one that is not a timeout
# parent and has the identical defect — `(env_spec or {}).items()` on a
# present non-mapping is an AttributeError traceback and rc 1, outside the
# rc-2 configuration contract, exactly as `(fixture.get("guard") or
# {}).get(...)` was.
MAPPING_FIXTURE_KEYS = tuple(dict.fromkeys(
    [parent for _key, parents in TIMEOUT_KNOBS for parent in parents] + ["env"]))


class MappingFixtureKeyError(guidance.GuidanceError):
    """`_require_mapping` refused a key. Carries WHICH key, so `main()` can
    route the `judge:` one onto `invalid_judge_block` — #81's named error,
    which writes report.md and one summary.json per arm — while every other
    key keeps the plain rc-2 configuration line. Without the key the two
    guards could only be ordered, and whichever ran first silently decided
    the error type for a fixture both of them refuse."""

    def __init__(self, key: str, message: str):
        self.key = key
        super().__init__(message)


def _require_mapping(fixture: dict, key: str, fixture_path: Path) -> None:
    """A PRESENT `key:` is a mapping, or an explicit null. Anything else is a
    named configuration error at fixture load.

    An explicit null is fine and means "absent": `(fixture.get("guard") or
    {})` and `(env_spec or {})` both fall back on it, and every committed
    fixture that omits the key is untouched by this. A truthy non-mapping is
    not fine — YAML will hand over a list, a string or a number just as
    happily, and each of them reaches `.get()`/`.items()` on the wrong type
    and dies with an AttributeError traceback instead of naming the rule.
    """
    if not isinstance(fixture, dict):
        raise guidance.GuidanceError(
            f"{fixture_path}: expected a mapping of fixture keys, got "
            f"{type(fixture).__name__} — `{key}:` cannot be looked up in it. "
            "A-N1-2: this predicate used to assume its own argument's shape, "
            "so an empty fixture file died with a TypeError inside it.")
    if key not in fixture or fixture[key] is None or isinstance(fixture[key], dict):
        return
    raise MappingFixtureKeyError(
        key,
        f"{fixture_path}: `{key}:` must be a mapping (or absent), got "
        f"{type(fixture[key]).__name__} {fixture[key]!r}. The value's TYPE is "
        "named as well as its repr because the repr alone does not say it: "
        "`True` and `3` read as a bool and an int only if you already know "
        "YAML's spelling rules. The harness reads the key with "
        "`.get()`/`.items()`, so "
        "a list, a string or a number here is not a configuration it can run "
        "— it used to reach the wrong type and die with an AttributeError "
        "traceback instead of naming the rule.")


def validate_mapping_keys(fixture: dict, fixture_path: Path) -> None:
    """Every mapping-typed fixture key, checked ONCE at load — before any
    subject branch, any path is derived and any CLI is invoked."""
    for key in MAPPING_FIXTURE_KEYS:
        _require_mapping(fixture, key, fixture_path)
    guidance.check_env_block(fixture.get("env"), f"{fixture_path}: `env:`")


# The CEILING every knob above is checked against, and the predicate that
# applies it, both live in harness/guidance.py — beside the GuidanceError they
# raise, and where EVERY source of a timeout can reach them. Round 2 put them
# here, in the fixture loader, and `--timeout` on the command line overrode the
# checked value afterwards with an unchecked one: `--timeout 2200000` was still
# rc 1 and a bare `OverflowError`. `main()` now runs the same predicate on the
# flag (see the `--timeout` check there), run_canary.py and run_propagation.py
# run it on theirs, and
# `test_every_harness_subprocess_timeout_names_its_validated_source` inventories
# every `subprocess` timeout under harness/ so a new sink cannot arrive with no
# validated source behind it.
#
# Re-exported under this module's own name because it is part of run_eval's
# published surface: `test_the_timeout_ceiling_is_the_workflow_job_budget`
# anchors it to eval.yml's `eval` job.
MAX_TIMEOUT_S = guidance.MAX_TIMEOUT_S

# The bound on this module's own local `git` calls. Named rather than inlined
# so the sink check and the `timeout=` argument are provably the same value:
# the pin compares the two expressions, not two beliefs about them.
GIT_TIMEOUT_S = 10


def validate_timeouts(fixture: dict, fixture_path: Path) -> None:
    """Coerce-and-check every timeout knob ONCE, at fixture load, before any
    subject branch or subprocess. Absent is fine — the caller's default
    applies, and a fixture with a valid or absent knob is untouched by this,
    so every committed fixture scores byte-identically.

    """
    for key, parents in TIMEOUT_KNOBS:
        node = fixture
        for parent in parents:
            # NOT `node = {}` on a non-mapping. Normalising the bad container
            # away let `guard: [1]` through validation and on into
            # `(fixture.get("guard") or {}).get("timeout_s", 300)`, which is
            # an AttributeError traceback and rc 1 — the same defect this
            # predicate closes for the leaf, one level up. Checked here as
            # well as in `validate_mapping_keys` so this function is sound for
            # a direct caller, not only for the one order main() calls them in.
            if not isinstance(node, dict):
                node = None
                break
            _require_mapping(node, parent, fixture_path)
            node = node.get(parent)
        if not isinstance(node, dict) or key not in node:
            continue
        guidance.check_timeout(node[key], ".".join(parents + (key,)),
                               guidance.FIXTURE_TIMEOUT_REMEDY,
                               prefix=f"{fixture_path}: ")


REGISTRIES_YML = Path(__file__).parent / "registries.yml"

_REQUIRED_REGISTRY_FIELDS = ("name", "url", "layout")


def _normalize_registry_url(url: str) -> str:
    """Case-insensitive, trailing-slash- and .git-suffix-insensitive form of
    a registry URL, so `https://github.com/Org/repo/`, `...repo.git`, and a
    differently-cased host or path all match the same registries.yml entry.
    """
    url = url.strip().rstrip("/")
    if url.lower().endswith(".git"):
        url = url[:-4]
    return url.lower()


def _layout_parts(layout: str) -> list[str]:
    """Split a registries.yml `layout` glob into path segments and check it
    ends in the skill-name placeholder immediately before `SKILL.md` — the
    one shape `_skill_md_glob` can substitute into. Shared by load-time
    validation and `_skill_md_glob` itself so the two can never drift apart:
    a layout that "passes" at load time (e.g. `skills/bundle*/SKILL.md`,
    which merely ends with the substring `*/SKILL.md`) but is rejected at
    arm time by a stricter check used to raise uncaught, deep inside a run.
    """
    parts = layout.split("/")
    if len(parts) < 2 or parts[-1] != "SKILL.md" or parts[-2] != "*":
        raise ValueError(f"layout {layout!r} must end in '*/SKILL.md'")
    if any("**" in part for part in parts):
        raise ValueError(
            f"layout {layout!r} contains a '**' segment — recursive globs "
            "are rejected: against a registry with a stale copy under, "
            "say, .git/, the sorted-first match could come from there")
    return parts


def _load_registries_config(path: Path = REGISTRIES_YML) -> list[dict]:
    """harness/registries.yml: [{name, url, layout}, ...] — this harness's own
    record of registry name/URL/layout, kept in step by hand with agentskills'
    scripts/skills_registries.yml (see test/run_tests.py::TestIssue63) rather
    than importing that file at run time: this harness must resolve using
    only its own checkout plus the registry under test.

    Shape-validated on load with one clear message per problem — a bare
    KeyError/TypeError from a malformed file is not something a contributor
    editing registries.yml by hand should have to decode.
    """
    if not path.is_file():
        raise ValueError(f"{path} not found")
    try:
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path} is not valid YAML: {exc}") from exc
    if not isinstance(doc, dict) or not doc.get("registries"):
        raise ValueError(f"{path} is empty or missing a top-level 'registries:' key")
    entries = doc["registries"]
    if not isinstance(entries, list):
        raise ValueError(f"{path}'s 'registries:' must be a list")

    seen_names: set[str] = set()
    seen_urls: set[str] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"{path} registries[{i}] must be a mapping")
        # Presence first (a genuinely absent or blank field), then type —
        # `not entry.get(f)` alone would misreport a wrong-typed-but-present
        # value (`name: no` parses as the bool False) as "missing" instead of
        # naming the real problem.
        missing = [f for f in _REQUIRED_REGISTRY_FIELDS
                  if entry.get(f) is None or entry.get(f) == ""]
        if missing:
            raise ValueError(
                f"{path} registries[{i}] is missing required field(s): "
                f"{', '.join(missing)}")
        bad_type = [f for f in _REQUIRED_REGISTRY_FIELDS
                   if not isinstance(entry.get(f), str)]
        if bad_type:
            raise ValueError(
                f"{path} registries[{i}] field(s) must be strings: " +
                ", ".join(f"{f!r} is {type(entry[f]).__name__}" for f in bad_type))
        name, url, layout = entry["name"], entry["url"], entry["layout"]
        if name in seen_names:
            raise ValueError(f"{path} has a duplicate registry name {name!r}")
        seen_names.add(name)
        norm_url = _normalize_registry_url(url)
        if norm_url in seen_urls:
            raise ValueError(f"{path} has a duplicate registry url {url!r}")
        seen_urls.add(norm_url)
        try:
            _layout_parts(layout)
        except ValueError as exc:
            raise ValueError(
                f"{path} entry {name!r} has layout {layout!r}: {exc}") from exc
        if Path(layout).is_absolute():
            raise ValueError(
                f"{path} entry {name!r} has an absolute layout {layout!r} — "
                "layouts are globbed relative to the registry checkout")
        if ".." in Path(layout).parts:
            raise ValueError(
                f"{path} entry {name!r} has layout {layout!r} containing "
                "'..' — layouts must stay within the registry checkout")
    return entries


def _parse_registry_flags(values: list[str] | None) -> dict[str, str]:
    """Repeatable --registry NAME=PATH entries. A bare PATH (no "=") is the
    pre-#63 single-path form and is taken as the agentskills entry, so the
    legacy invocation (`--registry ../agentskills`) keeps working unchanged.
    An empty PATH (`--registry agentskills=`, or a bare empty string) is
    rejected here rather than silently resolving to the current directory.
    A NAME repeated across two flags (bare or explicit) is rejected too —
    silently taking the last one made a copy-pasted or re-ordered invocation
    "work" while quietly dropping the first flag's registry.
    """
    out: dict[str, str] = {}
    for value in values or []:
        name, sep, path = value.partition("=")
        if sep:
            if not path:
                raise ValueError(
                    f"--registry {value!r}: empty PATH after '=' for "
                    f"registry {name!r}")
            key = name
        else:
            if not value:
                raise ValueError(
                    "--registry '': empty value — expected NAME=PATH, or a "
                    "bare PATH (legacy, taken as the agentskills entry)")
            key = "agentskills"
            path = value
        if key in out:
            raise ValueError(
                f"--registry {value!r}: registry {key!r} given more than "
                f"once (already {out[key]!r}) — repeated --registry flags "
                "for the same name silently last-won; pass it once")
        out[key] = path
    return out


def _parse_registry_env(value: str | None) -> dict[str, str]:
    """$SKILLS_EVALS_REGISTRIES: the same NAME=PATH shape, comma-separated. A
    bare entry (no "=") is taken as the agentskills entry too, the same as
    the --registry flag's legacy bare-PATH form (see _parse_registry_flags)
    — previously this silently dropped a bare entry instead, which was the
    one shape the CLI flag treats as meaningful. A NAME repeated across two
    entries (bare or explicit) is rejected too, the same as
    _parse_registry_flags — silently taking the last one made a re-ordered
    or copy-pasted env value "work" while quietly dropping the first entry's
    registry.
    """
    out: dict[str, str] = {}
    for item in (value or "").split(","):
        item = item.strip()
        if not item:
            continue
        name, sep, path = item.partition("=")
        if sep:
            if not path:
                raise ValueError(
                    f"$SKILLS_EVALS_REGISTRIES entry {item!r}: empty PATH "
                    f"after '=' for registry {name!r}")
            key = name
        else:
            key = "agentskills"
            path = item
        if key in out:
            raise ValueError(
                f"$SKILLS_EVALS_REGISTRIES entry {item!r}: registry {key!r} "
                f"given more than once (already {out[key]!r}) — repeated "
                "entries for the same name silently last-won; pass it once")
        out[key] = path
    return out


def resolve_registries(cli_values: list[str] | None, env_value: str | None,
                       base_dir: Path, agentskills_dir: str | None = None) -> dict[str, dict]:
    """Map every registry named in harness/registries.yml to a local checkout.

    Sources, in order: a --registry NAME=PATH flag (repeatable; a bare PATH
    means agentskills) merged BY NAME with $SKILLS_EVALS_REGISTRIES (same
    shape; a flag wins over an env entry naming the same registry, but an env
    entry for a DIFFERENT registry still applies even when a flag is also
    given), then `agentskills_dir` for the agentskills entry specifically
    (the harness's pre-#63 override — callers pass $AGENTSKILLS_DIR), then a
    sibling-directory default `../<name>` next to `base_dir` — the same
    convention agentskills' own skills_registries.yml uses for the registries
    it doesn't live in.

    An override naming a registry not listed in harness/registries.yml
    (a typo'd `--registry cms_platform=...`, say) is rejected here rather
    than silently discarded — the pre-fix behavior fell back to that
    registry's sibling default instead, which can "work" by accident and
    makes a bad override unverifiable from the exit code alone.
    """
    overrides_cli = _parse_registry_flags(cli_values)
    overrides_env = _parse_registry_env(env_value)
    config = _load_registries_config()
    known = {entry["name"] for entry in config}
    unknown = sorted((set(overrides_cli) | set(overrides_env)) - known)
    if unknown:
        names = ", ".join(repr(n) for n in unknown)
        raise ValueError(
            f"unknown registry name(s) {names} in --registry / "
            "$SKILLS_EVALS_REGISTRIES — not listed in harness/registries.yml "
            f"(known registries: {', '.join(sorted(known))})")

    resolved = {}
    for entry in config:
        name = entry["name"]
        if name in overrides_cli:
            path = Path(overrides_cli[name]).expanduser().resolve()
            source = "--registry flag"
        elif name in overrides_env:
            path = Path(overrides_env[name]).expanduser().resolve()
            source = "$SKILLS_EVALS_REGISTRIES"
        elif name == "agentskills" and agentskills_dir:
            path = Path(agentskills_dir).expanduser().resolve()
            source = "$AGENTSKILLS_DIR"
        else:
            path = (base_dir / ".." / name).resolve()
            source = "sibling default"
        resolved[name] = {"name": name, "path": path, "layout": entry["layout"],
                          "url": entry["url"], "source": source}
    return resolved


def _validate_registry_paths(registries: dict[str, dict]) -> None:
    """Fail fast on any EXPLICITLY overridden registry (a --registry flag,
    $SKILLS_EVALS_REGISTRIES entry, or $AGENTSKILLS_DIR) whose resolved path
    is not a directory — a typo'd override is a config mistake worth catching
    before any arm spends agent budget, not several minutes later as a
    confusing skill_not_found. Sibling-default entries are left alone here:
    most of registries.yml (e.g. agentskills-private) is never checked out
    locally and is fine to stay unresolved unless a fixture actually needs
    it — that path is checked lazily, per-arm, in _run_arm instead.
    """
    for name, entry in registries.items():
        if entry["source"] == "sibling default":
            continue
        if not entry["path"].is_dir():
            raise ValueError(
                f"registry {name!r} ({entry['source']}) does not resolve "
                f"to a directory")


def registry_for_url(registries: dict[str, dict], url: str) -> dict:
    """The registries.yml entry (path + layout) whose url matches a fixture's
    `registry:` field. Raises with a message naming harness/registries.yml —
    the file to edit — rather than failing silently or crashing deep inside
    a glob.
    """
    target = _normalize_registry_url(url)
    for entry in registries.values():
        if _normalize_registry_url(entry["url"]) == target:
            return entry
    known = ", ".join(sorted(registries)) or "(none configured)"
    raise ValueError(
        f"unknown registry {url!r} — not listed in harness/registries.yml "
        f"(known registries: {known})")


def _skill_md_glob(layout: str, skill: str) -> str:
    """Substitute `skill` for the skill-name placeholder in a registries.yml
    `layout` glob (the segment immediately before `SKILL.md`), leaving any
    earlier `*` (a bundle/plugin wildcard) untouched. Returns the FULL glob
    ending in `/SKILL.md` — callers must glob for FILES and take `.parent`,
    never glob for a directory: a skill dir with no SKILL.md (a stub left by
    a rename, a bundle mid-migration) must fail closed as skill_not_found
    rather than "installing" whatever happens to sit in that directory.
    """
    parts = _layout_parts(layout)
    parts[-2] = skill
    return "/".join(parts)


_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_skill_name(skill: str) -> None:
    """A skill name must be a single, non-empty path segment with no path or
    glob metacharacters. It flows unvalidated into both a registry glob and a
    shutil.copytree destination: `../../x` would escape the registry on read
    and the workspace on write, `*` would install whichever skill happens to
    glob-match first, and `""` would install the whole registry container.
    """
    if not _SKILL_NAME_RE.fullmatch(skill) or skill in (".", ".."):
        raise ValueError(
            f"invalid skill name {skill!r}: must be a single non-empty path "
            "segment with no path or glob metacharacters")


#: THE TRUSTED ROSTER (ADR 0001, #147). `main` is ruleset-protected and
#: pull-request-only, so an arm, the judge, the preflight model or a
#: `catalogue_seen` entry cannot appear here or vanish from here without a
#: reviewed commit — which is the one property the published
#: `roster/latest.json` on `eval-results` never had.
TRUSTED_ROSTER = Path(__file__).resolve().parent.parent / "evals" / "roster.yml"


def _resolve_roster(cli_value: Path | None) -> Path:
    """Model roster: --roster, else $EVAL_ROSTER, else the COMMITTED file.

    THE DEFAULT USED TO BE `roster/latest.json`, materialised by CI from the
    `eval-results` branch and pointed at by `$EVAL_ROSTER` — a branch other
    jobs on other machines write to, which the design treats as untrusted
    input. That made one line on that branch decide which models every
    unpinned fixture ran against, and fourteen review rounds on PR #129
    could not make a local check over it safe (issue #147). The roster the
    harness RUNS ON is `evals/roster.yml` now; `roster/latest.json` is an
    exhibit for the explorer and is read by no decision.

    `--roster` and `$EVAL_ROSTER` stay as overrides for tests and local runs
    (ADR 0001, decision 1). Neither is set by `eval.yml` any more.

    Whether a missing roster is an error depends on the fixture — see
    select_models(): it is for an unpinned one, and it is not for a pinned one.
    """
    if cli_value:
        return Path(cli_value).expanduser()
    env = os.environ.get("EVAL_ROSTER")
    if env:
        return Path(env).expanduser()
    return TRUSTED_ROSTER


def read_roster(roster_path: Path | None) -> tuple[dict | None, str | None]:
    """(roster, problem). Never raises, and never returns a half-shaped roster.

    YAML AND JSON, DECIDED BY CONTENT AND NOT BY EXTENSION (#147). The
    trusted roster is YAML, because a human edits it in a reviewed pull
    request and YAML is what every other hand-edited file in this repo is;
    a `--roster` pointing at a published `roster/latest.json` is still JSON.
    JSON is a subset of YAML 1.2, so `yaml.safe_load` reads both and there
    is no extension sniff to get wrong — a file named `.json` holding YAML,
    or the reverse, reads the same either way.

    The NEVER-RAISES, NEVER-HALF-SHAPED CONTRACT IS UNCHANGED, and it is
    what this function is for. Every one of these shapes was reachable and
    three of them crashed with an AttributeError three frames down: a
    top-level list, `arms` as a list of strings, `judge` as a string, a
    truncated file, an empty file. A named problem is the whole difference
    between a run that says what is wrong and a stack trace in a CI log.
    The problem names the same three cases it always did — absent/empty,
    unreadable, not a mapping — so nothing downstream has to learn a new
    vocabulary for a parser change.
    """
    if roster_path is None:
        return None, "no roster path was resolved"
    path = Path(roster_path)
    # The basename, not the full path (see select_models' own messages,
    # round 2 item 15): this problem string flows unchanged into
    # select_models' return value, which the caller writes into
    # summary.json — and eval.yml commits that file to the public
    # eval-results branch.
    if not path.is_file() or path.stat().st_size == 0:
        return None, f"no model roster at {path.name}"
    try:
        with open(path, encoding="utf-8") as f:
            document = yaml.safe_load(f)
    # `yaml.YAMLError` covers a truncated or otherwise unparseable
    # document (it is `ScannerError`/`ParserError`'s base), and the JSON
    # errors stay named beside it because `json` is still in this module's
    # vocabulary and a caller reading the message wants the class that
    # fired, not a category. `RecursionError` is here for the same reason
    # roster.read_json has it: a deeply nested document exhausts the
    # parser's stack rather than failing to parse, and used to escape as a
    # traceback carrying the runner's absolute paths.
    except (yaml.YAMLError, json.JSONDecodeError, OSError, UnicodeDecodeError,
            ValueError, RecursionError) as exc:
        return None, f"model roster at {path.name} is unreadable ({type(exc).__name__})"
    if not isinstance(document, dict):
        return None, f"model roster at {path.name} is not a mapping"
    return document, None


def roster_models(roster: dict | None) -> tuple[list[str], str | None, bool, int]:
    """(arm ids, judge id, judge-is-also-an-arm, skipped) out of a roster document.

    Anything the wrong shape is dropped here rather than trusted downstream.
    `judge.is_arm` is the roster's own flag; membership in `arms` is the fact
    behind it, and an older roster carrying no flag must not read as consent.

    `skipped` counts `arms` entries dropped for being the wrong shape (not a
    dict with a string `id`). It matters because dropping them silently once
    let the judge-is-arm check pass against an EMPTIED set: a malformed
    `arms` list (e.g. raw strings instead of `{id, reason}` objects) parsed
    to `arm_ids == []`, so `judge_id in arm_ids` was always False even when
    the roster's own (unparsed) entries plainly named that judge as an arm.
    """
    entries = roster.get("arms") if isinstance(roster, dict) else None
    arm_ids = []
    skipped = 0
    if isinstance(entries, list):
        for a in entries:
            if isinstance(a, dict) and isinstance(a.get("id"), str) and a["id"]:
                arm_ids.append(a["id"])
            else:
                skipped += 1
    judge_entry = roster.get("judge") if isinstance(roster, dict) else None
    judge_id = judge_entry.get("id") if isinstance(judge_entry, dict) else None
    if not isinstance(judge_id, str) or not judge_id:
        judge_id = None
    flagged = bool(isinstance(judge_entry, dict) and judge_entry.get("is_arm"))
    return (arm_ids, judge_id,
           flagged or (judge_id is not None and judge_id in arm_ids), skipped)


def select_models(fixture: dict, args: argparse.Namespace) -> tuple:
    """(agent model, judge model, error) for this run.

    Precedence: `--model` > the fixture's pin > the roster > nothing runs.

    FAIL CLOSED. The runner used to fall through to the CLI's own default
    model whenever the fixture pinned nothing and the roster was absent,
    empty, truncated or the wrong shape — which publishes a badge for a model
    nobody chose and makes every week-over-week comparison a comparison
    against a different model. An unpinned fixture with no usable roster is a
    runner-level error naming the path it looked for, and it leaves through
    the normal exit-2 path. A fixture that pins BOTH `model:` and
    `judge.model:` never needs the roster and is unaffected: it still runs
    with no roster at all. Pinning only one still reads the roster for the
    other.

    The roster's arms are ordered cheapest tier first, so `arms[0]` is the
    WEAKEST model in the set. That is deliberate for a single-arm run — a
    floor effect is as signal-free as a ceiling effect, and the matrix runner
    that will run every arm is where the per-fixture calibration belongs. A
    fixture that needs a specific one keeps its pin.
    """
    pinned_agent = args.model or fixture.get("model")
    pinned_judge = (fixture.get("judge") or {}).get("model")
    needs_agent = not pinned_agent
    needs_judge = not pinned_judge and not getattr(args, "no_judge", False)
    if not needs_agent and not needs_judge:
        return pinned_agent, pinned_judge, None

    path = _resolve_roster(getattr(args, "roster", None))
    roster, problem = read_roster(path)
    if problem:
        missing = [w for need, w in ((needs_agent, "model"),
                                     (needs_judge, "judge model")) if need]
        return None, None, f"{problem}, and this fixture pins no {' or '.join(missing)}"
    arm_ids, judge_id, judge_is_arm, skipped = roster_models(roster)
    raw_arms = roster.get("arms") if isinstance(roster, dict) else None
    if isinstance(raw_arms, list) and raw_arms and not arm_ids:
        # Non-empty `arms` that parses to zero usable ids is a broken
        # roster, not "no arms configured" — and it is unsafe to trust for
        # ANYTHING this roster names (including the judge), regardless of
        # whether this particular run even needed an arm from it.
        return None, None, (f"the model roster at {path.name} lists "
                            f"{len(raw_arms)} arm entry/entries but none has "
                            f"a usable string `id` (skipped {skipped}); this "
                            f"roster cannot be trusted for a model pick")
    if needs_agent and not arm_ids:
        return None, None, (f"the model roster at {path.name} names no usable "
                            f"arm, and this fixture pins no model")
    if needs_judge and not judge_id:
        return None, None, (f"the model roster at {path.name} names no usable "
                            f"judge, and this fixture pins no judge model")
    if needs_judge and judge_is_arm:
        return None, None, (f"the model roster at {path.name} names a judge "
                            f"that is also an arm; a model must not grade its "
                            f"own run. Pin `judge.model:` in the fixture to "
                            f"override")
    return (pinned_agent or arm_ids[0]), (pinned_judge or judge_id), None


_VAR_RE = re.compile(r"\$(\w+)|\$\{([^}]*)\}")


def expand(value: str, env: dict) -> str:
    """`$VAR` / `${VAR}` resolved against `env`, in ONE pass.

    Not `os.path.expandvars`: that reads `os.environ`, so a `WORKSPACE`
    already set in the harness's own environment won every time and
    `$WORKSPACE/bin` resolved to the OUTER path — which silently removed the
    fixture's fake from PATH and left whatever real tool was next on it, under
    bypassPermissions. One pass also means the substituted text is never
    re-scanned, so a workspace path holding a `$` cannot expand again.
    """
    return _VAR_RE.sub(lambda m: env.get(m.group(1) or m.group(2), m.group(0)), value)


# The ONLY inherited variables an arm receives, for every fixture. An
# ALLOWLIST, deliberately: a denylist forwards everything nobody thought to
# name, and what reaches the arm then depends on the operator's shell.
# Measured under the denylist this replaces, through `run_eval.py --arm
# without_skill` with a stand-in `claude` that dumps its own environment:
# `GH_HOST`, `GH_ENTERPRISE_TOKEN` and `GITHUB_ENTERPRISE_TOKEN` — the other
# half of `gh`'s own credential resolution — arrived verbatim, and so did
# `AWS_*`, `NPM_TOKEN`, `GITLAB_TOKEN`, `OPENAI_API_KEY`, `HF_TOKEN`,
# `SSH_AUTH_SOCK`, `KUBECONFIG`, `DOCKER_CONFIG`, `GIT_ASKPASS`,
# `PYTHONPATH`, `LD_PRELOAD`, and variables whose VALUES name the operator's
# own checkout. The arm's workspace is its cwd under bypassPermissions, `env`
# is one of the first things a shell reaches for, and `_write_summary` writes
# the arm's transcript to `results/<skill>/<ts>/<arm>/transcripts/raw.json`,
# which `.github/workflows/eval.yml` pushes to the public `eval-results`
# branch — so a variable that reaches the arm is a variable an arm can
# publish.
#
# Each entry carries the reason the CLI or the operating system needs it. A
# name is added here only because something in `run_agent`'s invocation,
# `_run_arm`, or eval.yml demonstrably needs it — never because a test
# wanted it.
_ALLOWED_ENV = (
    "PATH",                # find the CLI, and the fixture's own stand-ins
    "HOME",                # the CLI's config, cache and credential store
    "USER",                # some tools shell out and read it; cheap to keep
    "LOGNAME",             # the POSIX spelling of the same thing
    "SHELL",               # what the CLI spawns for its own tool calls
    "TERM",                # terminal capabilities; absent, some tools hang
    "LANG",                # locale: decides the CLI's default text encoding
    "LANGUAGE",            # locale fallback list, same reason
    "TZ",                  # local time in anything the agent formats
    "TMPDIR",              # where the CLI and its children write temp files
    "TMP",                 # the same, spelled the other way
    "TEMP",                # and the third spelling
    "HTTP_PROXY",          # a runner may only reach the API through a proxy
    "HTTPS_PROXY",         # the API is HTTPS, so this is the load-bearing one
    "NO_PROXY",            # hosts that must bypass it
    "ALL_PROXY",           # the catch-all spelling some clients read
    "http_proxy",          # not an alias: clients read one case or the other
    "https_proxy",         # the lower-case spelling curl and requests prefer
    "no_proxy",            # the lower-case bypass list, read by the same clients
    "all_proxy",           # the lower-case catch-all, for completeness of the pair
    "SSL_CERT_FILE",       # a corporate CA bundle, or TLS fails outright
    "SSL_CERT_DIR",        # the directory spelling of the same bundle
    "NODE_EXTRA_CA_CERTS", # the CLI is a Node program; this is its CA hook
    "REQUESTS_CA_BUNDLE",  # anything Python the CLI shells out to
    "CURL_CA_BUNDLE",      # anything curl-based it shells out to
)

# Prefixes, for families whose members are not knowable in advance.
_ALLOWED_ENV_PREFIXES = (
    "ANTHROPIC_",  # the API credential: eval.yml exports ANTHROPIC_AUTH_TOKEN
                   # step-locally, local runs use ANTHROPIC_API_KEY. Forwarded
                   # by design — the CLI cannot authenticate otherwise — which
                   # also makes it one of the variables the arm's own
                   # published transcript could leak (see "a variable that
                   # reaches the arm is a variable an arm can publish" above);
                   # nothing here redacts it before raw.json is written.
    "CLAUDE_",     # the CLI's own knobs, including CLAUDE_CODE_OAUTH_TOKEN.
                   # Also carries CLAUDE_BIN, which only the harness itself
                   # reads (run_agent/judge.score/run_canary via os.environ,
                   # never the CLI) — a residue of the prefix, not something
                   # under test needing it — and CLAUDE_CODE_USE_BEDROCK/
                   # _VERTEX with none of the AWS_*/GOOGLE_APPLICATION_
                   # CREDENTIALS that would authenticate them: this allowlist
                   # assumes the first-party API, which is what eval.yml
                   # uses. Adding those credential families to reach
                   # Bedrock/Vertex would undo B1's own point.
    "LC_",         # the per-category locale settings LANG does not cover
    "XDG_",        # config/cache/data/state/runtime dirs the CLI writes under
)

# Emptied rather than dropped. `GH_TOKEN`/`GITHUB_TOKEN` are not on the
# allowlist, so they no longer arrive on their own — but an arm under
# bypassPermissions can call a real `gh` by absolute path, past the stand-in
# on PATH, and an ABSENT token sends `gh` looking in its config and the
# keyring for another one. Empty stops that search; `GH_CONFIG_DIR` points it
# inside the workspace, where there is no host and no credential to find.
_BLANKED_ENV = ("GH_TOKEN", "GITHUB_TOKEN")
_WORKSPACE_GH_CONFIG = ".gh/config"


def agent_env(workspace: Path, env_spec: dict | None,
              source: dict | None = None) -> dict:
    """The environment the agent under test runs in.

    A fixture's `env:` mapping is applied over an allowlisted slice of the
    harness's own environment, with `$WORKSPACE` (and any other `$VAR`)
    expanded against the workspace the arm actually got — a temp dir the
    fixture cannot know in advance. That is what lets a seed put a fake
    binary on the agent's PATH (`PATH: "$WORKSPACE/bin:$PATH"`), the Class B
    "fake `gh` on the seed workspace's PATH" move DESIGN.md prescribes,
    without the seed carrying an absolute path. Values are strings; a
    non-string is stringified rather than rejected, since YAML will happily
    hand over an int.

    What the arm receives, and nothing else:

      * the names in `_ALLOWED_ENV` and the prefixes in
        `_ALLOWED_ENV_PREFIXES` that are present in `source`, forwarded
        verbatim — every other inherited variable is dropped;
      * the harness's own `WORKSPACE`, `GH_CONFIG_DIR` (inside the
        workspace) and `GH_TOKEN`/`GITHUB_TOKEN` (empty strings);
      * the fixture's own `env:` block, applied last, so a fixture that
        wants a name back can say so.

    `gh`'s token variables do not reach it from the harness's environment:
    `GH_TOKEN` and `GITHUB_TOKEN` arrive empty, and `GH_ENTERPRISE_TOKEN`,
    `GITHUB_ENTERPRISE_TOKEN` and `GH_HOST` are not on the list. A fixture's
    own `env:` block can still name anything it likes — it is applied last,
    and no fixture here names one of those.

    What IS refused, here at the function that builds the child's environment
    and by the same predicate `guidance.agent_env` uses, is a name or value
    the OS itself will not take: a name with an `=` in it reached
    `subprocess.run(env=...)` and came back as `ValueError: illegal
    environment variable name` — rc 1 and a traceback, after the arm had
    started. The allowlist decides what is INHERITED; this predicate decides
    what is spellable at all, so neither widens nor narrows the other.

    `source` is the parent environment to filter, defaulting to `os.environ`
    — a test can hand over a mapping it built rather than mutating the
    process's own environment, which is what makes "the arm received exactly
    these names" decidable without depending on the operator's shell.
    """
    guidance.check_env_block(env_spec, "the fixture's `env:`")
    parent = os.environ if source is None else source
    env = {key: value for key, value in parent.items()
           if key in _ALLOWED_ENV or key.startswith(_ALLOWED_ENV_PREFIXES)}
    env["WORKSPACE"] = str(workspace)
    for key in _BLANKED_ENV:
        env[key] = ""
    env["GH_CONFIG_DIR"] = str(workspace / _WORKSPACE_GH_CONFIG)
    for key, value in (env_spec or {}).items():
        env[str(key)] = expand(str(value), env)
    return env


# Both spellings `expand()` honours, so a fixture cannot opt out of the
# guard below by writing the braced one. `${WORKSPACE}` failed a
# `startswith("$WORKSPACE")` test, which returned as if the fixture had put
# nothing of its own on PATH.
_WORKSPACE_SPELLINGS = ("$WORKSPACE", "${WORKSPACE}")


def assert_stand_ins_on_path(workspace: Path, env: dict, env_spec: dict | None) -> None:
    """A fixture that prepends `$WORKSPACE/<dir>` to PATH must actually get it.

    The failure this catches is silent and total: the arm runs the REAL tool
    the fixture meant to fake, under bypassPermissions, and scores whatever
    that tool happened to say. Raising is the right end for it — a harness
    that cannot honour a fixture's `env:` block has no result worth writing.

    `$WORKSPACE/bin` and `${WORKSPACE}/bin` are the same fixture: `expand()`
    resolves both, so both are guarded here.
    """
    spec = str((env_spec or {}).get("PATH", ""))
    if not spec.startswith(_WORKSPACE_SPELLINGS):
        return
    wanted = Path(expand(spec.split(os.pathsep, 1)[0], dict(env)))
    got = Path(env["PATH"].split(os.pathsep)[0])
    if got != wanted:
        raise RuntimeError(f"fixture PATH resolved to {got}, expected {wanted}")
    stand_ins = ([p for p in sorted(wanted.iterdir())
                  if p.is_file() and os.access(p, os.X_OK)] if wanted.is_dir() else [])
    if not stand_ins:
        raise RuntimeError(
            f"no executable stand-in in {wanted}, which the fixture puts first "
            "on PATH: the arm would run the real tool instead")


def run_setup(workspace: Path, fixture: dict) -> dict | None:
    """Run the fixture's `setup:` command, if any, in the workspace before
    anything else touches it — before the agent, and before objective-only
    scoring of a freshly copied seed.

    Some fixtures need to build state a checked-in seed can't hold cleanly
    (nested git repositories, for instance: a bare repo and a clone of it
    committed as literal files would embed one git checkout inside another,
    which `git add -A` on the harness's own bookkeeping commit treats as a
    submodule boundary rather than plain files). `setup:` names a shell
    command, run with `cwd=workspace` and `$WORKSPACE` (plus any other
    `$VAR`) expanded the same way `env:` values are (see `agent_env`) — one
    pass, against the ALLOWLISTED environment, never `os.environ` directly
    (see `expand`'s own docstring for why that distinction matters: a
    `WORKSPACE` already set in the harness's own environment would otherwise
    win over the one this run actually got), so a fixture can write `bash
    $WORKSPACE/setup.sh` or a bare `bash setup.sh` interchangeably.

    Returns `None` when the fixture has no `setup:` (every existing fixture)
    or the command exits 0. Otherwise returns a `{"error": "setup_failed",
    "detail": ...}` dict — the same error-dict convention `run_agent` uses —
    so a failing setup script fails the arm/run with a named error and a
    captured stderr/stdout tail, never a bare traceback out of a check that
    assumed setup had already put its files in place.
    """
    timeout = fixture.get("setup_timeout_s", 60)
    guidance.check_timeout(timeout, "run_eval.run_setup(timeout=)",
                           guidance.SINK_TIMEOUT_REMEDY)
    setup_cmd = fixture.get("setup")
    if not setup_cmd:
        return None
    env = agent_env(workspace, fixture.get("env"))
    cmd = expand(str(setup_cmd), env)
    try:
        result = subprocess.run(["bash", "-c", cmd], cwd=workspace,
                                capture_output=True, text=True, timeout=timeout,
                                env=env)
    except subprocess.TimeoutExpired:
        return {"error": "setup_failed", "detail": f"setup timed out after {timeout}s"}
    if result.returncode != 0:
        return {"error": "setup_failed",
                "detail": result.stderr.strip() or result.stdout.strip()}
    return None


def run_agent(workspace: Path, prompt: str, arm: dict) -> dict:
    """Run the agent under test (the Claude Code CLI, headless) on the workspace.

    `arm` carries: name ("with_skill"/"without_skill"), skill + registry (Path,
    only for with_skill), optional model, optional timeout (default 600s),
    optional env (the fixture's `env:` mapping, see agent_env).

    This replaces the old `-> str` transcript stub with a richer dict. Success
    dicts have no "error" key and carry transcript/usage/cost_usd/num_turns/
    duration_ms/raw. Error dicts always have an "error" key — one of
    "invalid_skill_name", "skill_not_found", "skill_install_failed", "timeout",
    "nonzero_exit", "invalid_json", "agent_error" — plus a "detail". Callers
    MUST check `"error" in result` rather than relying on exceptions; only
    skill installation and process invocation failures are turned into error
    dicts here, nothing is raised.
    """
    # S1-a-2. The predicate sits HERE, at the function that hands the value
    # to the OS, and not only at the sources a table can name. Measured on
    # f9115ce: rebinding this call site's `timeout` to an unvalidated fixture
    # key (`fixture.get("agent_timeout_s", 600)`) left the source inventory,
    # the flag pin and all 120 TestIssue97 tests green while a fixture
    # reproduced `OverflowError: timeout is too large`, rc 1.
    timeout = arm.get("timeout", 600)
    guidance.check_timeout(timeout, "run_eval.run_agent(timeout=)",
                           guidance.SINK_TIMEOUT_REMEDY)
    if arm["name"] == "with_skill":
        skill = arm["skill"]
        try:
            _validate_skill_name(skill)
        except ValueError as exc:
            return {"error": "invalid_skill_name", "detail": str(exc)}
        registry = arm["registry"]
        # Registry layouts vary (agentskills' plugins/<bundle>/skills/<skill>/,
        # cms-platform's flat skills/<skill>/, adamdaniel.ai's
        # .claude/skills/<skill>/ — see harness/registries.yml). `layout`
        # carries the glob for the registry under test, defaulting to
        # agentskills' shape for callers that predate #63. Globs for the
        # SKILL.md FILE (not the containing directory) and takes its parent,
        # so a skill directory with no SKILL.md — a stub left by a rename, a
        # bundle mid-migration — fails closed as skill_not_found instead of
        # "installing" whatever's actually in there. Sorted so multiple
        # matches pick deterministically.
        layout = arm.get("layout", "plugins/*/skills/*/SKILL.md")
        skill_md_glob = _skill_md_glob(layout, skill)
        matches = sorted(p.parent for p in registry.glob(skill_md_glob) if p.is_file())
        if not matches:
            # The registry's NAME (arm_config's own, when _run_arm resolved
            # it — falling back to the checkout dir's basename otherwise)
            # plus the RELATIVE glob, never the resolved absolute path: this
            # detail reaches summary.json, which eval.yml commits to the
            # public eval-results branch (item 6, #129 review round 4 — the
            # same treatment select_models' own roster-path messages use).
            registry_label = arm.get("registry_name") or registry.name
            return {"error": "skill_not_found",
                    "detail": f"no SKILL.md matched {registry_label}/{skill_md_glob}"}
        skill_src = matches[0]
        skill_dest = workspace / ".claude" / "skills" / skill
        try:
            shutil.copytree(skill_src, skill_dest)
        except OSError as exc:
            # FileExistsError (the destination dir already exists) and
            # NotADirectoryError (a seed shipping .claude/skills itself as a
            # regular FILE, so os.makedirs can't create skill_dest under it)
            # both land here — both are a seed/workspace layout problem, not
            # something to raise out of run_agent's "nothing is raised"
            # contract, but "already exists" is only true of the first one
            # (N1, #129 review round 6) — a generic wording that names the
            # exception type covers both honestly. The skill name, not
            # `skill_dest`'s absolute workspace path — this detail reaches
            # summary.json, which eval.yml commits to the public
            # eval-results branch.
            return {"error": "skill_install_failed",
                    "detail": f"could not install {skill}/ into the seed "
                              f"workspace ({type(exc).__name__})"}

    # `setting_sources` and `env_override` are the guidance subject's two
    # seams (#97): guidance is delivered into USER memory by the fleet hook,
    # so a guidance arm is invoked with `user,project` and with the scrubbed
    # allowlist environment its arm built. Both default to exactly what skill
    # arms have always had — `project`, and this harness's own environment
    # with the fixture's `env:` applied — so skill fixtures are byte-identical
    # across this change.
    cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p", prompt,
           "--output-format", "json", "--permission-mode", "bypassPermissions",
           "--setting-sources", arm.get("setting_sources", "project")]
    if arm.get("model"):
        cmd += ["--model", arm["model"]]

    try:
        result = subprocess.run(cmd, cwd=workspace, capture_output=True,
                                text=True, timeout=timeout,
                                env=arm.get("env_override")
                                or agent_env(workspace, arm.get("env")))
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "detail": f"agent timed out after {timeout}s"}

    if result.returncode != 0:
        return {"error": "nonzero_exit",
                "detail": result.stderr.strip() or result.stdout.strip(),
                "returncode": result.returncode}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"error": "invalid_json",
                "detail": f"{result.stdout[:500]!r}: {e}"}

    if data.get("is_error"):
        return {"error": "agent_error", "detail": data.get("result", ""), "raw": data}

    return {
        "transcript": data.get("result"),
        "usage": data.get("usage"),
        "cost_usd": data.get("total_cost_usd"),
        "num_turns": data.get("num_turns"),
        "duration_ms": data.get("duration_ms"),
        "raw": data,
    }


# The arm's workspace is the agent's cwd, and it can read every byte of it:
# `pwd`, `git log`, `ls -a`, `cat bin/gh`, `env`. So neither the directory
# name nor the baseline commit's identity may name this repository, this
# harness or the arm — `/tmp/skills-evals-with_skill-XXXX` and a commit
# authored by "skills-evals harness" told the agent what it was being
# measured with before it had read a single line of the seed.
WORKSPACE_PREFIX = "workspace-"
SEED_COMMIT_IDENTITY = ("ci@example.com", "ci")
SEED_COMMIT_MESSAGE = "initial commit"

# Where `materialize_workspace` records the workspace's own absolute path,
# and where a stand-in binary in `<workspace>/bin/` reads it from.
#
# Under `.git/`, deliberately, and it is the whole of the mechanism:
#   * `git status` never shows it, and no objective check in this repository
#     globs into `.git/` — both measured — so it changes no check's verdict;
#   * `cp -a` of the WHOLE workspace carries it — and it still names the
#     ORIGINAL, so a copy of the workspace records where the original does;
#   * a bare copy, or a hard link, of the binary alone never has it, so a
#     copy in some other `bin/` has nothing to read and refuses.
# The rule it replaces deduced the location from a directory NAME — a copy
# of the binary in any `.../bin/` recorded into that directory's parent,
# which put the record somewhere no check looks.
WORKSPACE_ANCHOR = ".git/workspace-root"


class SetupFailedError(RuntimeError):
    """Raised by `materialize_workspace` when the fixture's `setup:` command
    (see `run_setup`) fails. Carries the same `{"error": "setup_failed",
    "detail": ...}` dict `run_setup` returns, plus the half-built workspace
    it was raised over — `materialize_workspace` cannot simply swallow the
    error (a fixture that needed setup and didn't get it must not silently
    score a workspace that never had it), and the caller still owns cleanup
    of the temp dir, since the exception fires before `materialize_workspace`
    returns one.
    """

    def __init__(self, workspace: Path, detail: dict):
        self.workspace = workspace
        self.detail = detail
        super().__init__(detail.get("detail", ""))


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run git in `cwd` with a fixed local identity (don't rely on global
    config, and don't name this repository or this harness — see
    `SEED_COMMIT_IDENTITY`). `errors="replace"` — a workspace an agent has
    been let loose in can carry non-UTF-8 bytes git itself doesn't treat as
    binary (its own heuristic only looks for a NUL byte early in the
    content), and a diff or log that embeds them raw must not crash the
    whole run over it.
    """
    email, name = SEED_COMMIT_IDENTITY
    return subprocess.run(
        ["git", "-c", f"user.email={email}",
         "-c", f"user.name={name}", *args],
        cwd=cwd, check=True, capture_output=True, text=True, errors="replace",
    )


def materialize_workspace(seed: Path, fixture: dict | None = None) -> Path:
    """A fresh arm workspace: the seed copied in, under a baseline git commit.

    Extracted from `_run_arm` so a test can build the workspace the arm
    actually gets rather than a hand-rolled lookalike — what an agent can
    read in here is a property of THIS function, and a copy in a test would
    drift away from it silently.

    `fixture` is optional and defaults to `None`: every existing caller that
    only needs the plain committed-and-anchored workspace (no `setup:`) can
    keep calling `materialize_workspace(seed)` unchanged. When a fixture IS
    given and carries a `setup:` command, `run_setup` runs it BEFORE the
    baseline commit — a setup script (e.g. disarm-inherited-reach's) builds
    real git repositories in the workspace and deletes its own machinery as
    its last step, and committing first would let that machinery survive
    into the "seed" commit even though it no longer exists on disk (see
    `run_setup`'s own docstring). A failing setup raises `SetupFailedError`
    rather than returning it, since this function's only other return shape
    is a ready-to-use `Path` with nothing to attach an error to.
    """
    workspace = Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX))
    try:
        shutil.copytree(seed, workspace, dirs_exist_ok=True)
        if fixture is not None:
            setup_result = run_setup(workspace, fixture)
            if setup_result is not None:
                raise SetupFailedError(workspace, setup_result)
        _git("init", "-q", cwd=workspace)
        _git("add", "-A", cwd=workspace)
        _git("commit", "-q", "-m", SEED_COMMIT_MESSAGE, cwd=workspace)
        # After the baseline commit, so the anchor is never part of it. A
        # stand-in in `<workspace>/bin/` reads this to find where its
        # invocation log goes; without it, it refuses to serve or record
        # anything at all.
        anchor = workspace / WORKSPACE_ANCHOR
        anchor.parent.mkdir(parents=True, exist_ok=True)
        anchor.write_text(f"{workspace}\n", encoding="utf-8")
    except SetupFailedError:
        # The caller still owns cleanup here (see the class docstring) --
        # `_run_arm`'s handler needs the half-built workspace to inspect.
        raise
    except Exception:
        # Anything else (a failed `_git` call, a `copytree` I/O error, ...)
        # means this function is not handing the workspace back to anyone,
        # so it must not leak the `mkdtemp` directory it created.
        shutil.rmtree(workspace, ignore_errors=True)
        raise
    return workspace


def _nested_repo_dirs(workspace: Path) -> list[Path]:
    """Every directory anywhere under `workspace` (any depth, not just the
    top level — a copy at `$WORKSPACE/scratch/throwaway` is just as
    gitlink-collapsed as one directly under the workspace) that is itself a
    git repository (standalone, or a linked worktree) — the workspace's own
    bookkeeping repo (see `_run_arm`) collapses each to a single gitlink
    line in `git diff`, hiding exactly what changed inside from the judge.
    `.git` and `.claude` directories are pruned from the walk wherever they
    appear (not just at the top), and a nested repo's own working tree is
    not walked into any further once found — its last commit is what
    `_nested_repo_diff` shows, not a search for repos nested inside it. A
    bare repository (e.g. a fixture's `prod.git`) has no nested `.git`
    marker of its own — the directory IS the git dir — so it is never
    picked up here; its raw internals (objects, hooks/*.sample) are
    excluded from the bookkeeping repo entirely instead (see
    `evals/disarm-inherited-reach/seed/setup.sh`'s `.git/info/exclude`
    entry) since they are not a working tree to show a patch for.

    A directory that is ITSELF a bare repository (or any other git-dir
    shape `objective._looks_like_a_git_dir` recognizes) is pruned from the
    walk too, round 3 N4: its internals (`objects/`, `refs/`, `hooks/`) can
    never legitimately contain a nested working tree's own `.git` marker,
    so descending into them is pure waste — and, for a real object store,
    a walk of thousands of loose-object subdirectories for nothing.
    """
    out = []
    for root, dirs, _files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in (".git", ".claude")]
        root_path = Path(root)
        if root_path == workspace:
            continue
        if (root_path / ".git").exists():
            out.append(root_path)
            dirs[:] = []
        elif objective._looks_like_a_git_dir(root):
            dirs[:] = []
    return sorted(out)


def _nested_repo_diff(workspace: Path, dirs: list[Path]) -> str:
    """The last-commit patch for each nested repo dir in `dirs`, labelled by
    its path relative to `workspace` — what a script running inside a
    gitlink-collapsed copy actually did, which the workspace's own `git
    diff` cannot show (a gitlink is a single line: the commit SHA it now
    points at, not a patch).
    """
    guidance.check_timeout(GIT_TIMEOUT_S, "run_eval._nested_repo_diff(timeout=)",
                           guidance.SINK_TIMEOUT_REMEDY)
    sections = []
    for d in dirs:
        rel = d.relative_to(workspace)
        log = subprocess.run(
            ["git", "-C", str(d), "log", "--stat", "-p", "-1", "--format=%H %s"],
            capture_output=True, text=True, errors="replace",
            timeout=GIT_TIMEOUT_S)
        if log.returncode != 0 or not log.stdout.strip():
            sections.append(f"=== {rel} (no commits) ===")
        else:
            sections.append(f"=== {rel}: last commit ===\n{log.stdout}")
    return "\n\n".join(sections)


_DIFF_HEADER_RE = re.compile(r"^diff --git a/.* b/(.*)$")


def _summarize_binary_blobs(workspace: Path, diff: str) -> str:
    """Replace each changed file's diff body with a short `Binary file
    <path> (<n> bytes)` summary when the file's actual on-disk bytes are
    not valid UTF-8 (round 3 N6) — decided directly against the real file,
    not trusted to git's own per-diff binary-vs-text decision.

    `git diff` prints "Binary files ... differ" for most binary content,
    but its own detection (a NUL byte within a sampled prefix) can miss a
    genuinely binary file too small to reliably contain one by chance — a
    git loose object is a zlib-compressed stream of a few dozen bytes for
    a small commit, and it is exactly as likely to be free of 0x00 as any
    other byte value. Left classified as "text", its raw non-UTF-8 bytes
    get embedded straight into the diff; decoded with `errors="replace"`
    (see `_git`, called with `text=True`), those become a wall of U+FFFD
    replacement characters — unreadable, and mostly useless, judge input.
    Deciding by UTF-8-decodability instead targets the actual failure mode
    (the lossy text decode) rather than approximating git's own heuristic.
    The scenario this closes: an agent leaves a bare clone in the
    workspace (`git clone --bare checkout mirror`), and its loose objects
    (a small repo has no packs at all) are added to the bookkeeping diff
    as plain new files.
    """
    if "diff --git " not in diff:
        return diff
    chunks = re.split(r"(?m)^(?=diff --git )", diff)
    out = []
    for chunk in chunks:
        header, _, _ = chunk.partition("\n")
        m = _DIFF_HEADER_RE.match(header)
        if not m:
            out.append(chunk)
            continue
        path = m.group(1)
        try:
            data = (workspace / path).read_bytes()
        except OSError:
            out.append(chunk)
            continue
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            out.append(f"{header}\nBinary file {path} ({len(data)} bytes)\n")
        else:
            out.append(chunk)
    return "".join(out)


def _build_judge_diff(workspace: Path) -> str:
    """The text handed to the judge as "what changed": the workspace's own
    bookkeeping diff, plus — for any top-level directory that is itself a
    git repository and therefore collapsed to a single gitlink line in that
    diff — its own last commit, so the judge can see what actually happened
    inside a scratch copy the agent made rather than just a gitlink SHA
    changing.
    """
    _git("add", "-A", cwd=workspace)
    diff = _git("diff", "--cached", "--", ".", ":!.claude", cwd=workspace).stdout
    diff = _summarize_binary_blobs(workspace, diff)
    nested = _nested_repo_diff(workspace, _nested_repo_dirs(workspace))
    if nested:
        diff = f"{diff}\n\n# Nested repository contents (collapsed to gitlinks above)\n{nested}"
    return diff


def _write_summary(results_dir: Path, skill: str | None, arm_name: str,
                   timestamp: str, error: dict | None, agent: dict | None,
                   objective_checks: list | None, judge_result: dict | None,
                   raw: dict | None, key: str | None = None,
                   extra: dict | None = None) -> None:
    """One arm's summary.json (+ raw transcript).

    `key` is the results-tree path for this subject — a skill's own name, or
    `guidance/<section id>` — and defaults to `skill`, which is what every
    skill arm has always written. `extra` carries the guidance subject's own
    fields (subject/section/mode/bytes/delivery/guard).
    """
    arm_dir = results_dir / (key or skill) / timestamp / arm_name
    arm_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    if skill is not None:
        summary["skill"] = skill
    summary.update({
        "arm": arm_name,
        "timestamp": timestamp,
        "error": error,
        "agent": agent,
        "objective_checks": objective_checks,
        "judge": judge_result,
    })
    if extra:
        summary.update(extra)
    with open(arm_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    if raw is not None:
        transcripts_dir = arm_dir / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        with open(transcripts_dir / "raw.json", "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)


# How much of an error detail one report table cell carries. The full
# detail is always in summary.json; this is the reader's version.
_REPORT_CELL_CHARS = 200


def _render_report(skill: str, prompt: str, timestamp: str, arm_summaries: list[dict]) -> str:
    lines = [
        f"# Eval report: {skill}",
        "",
        f"- Prompt: {prompt.strip()}",
        f"- Timestamp: {timestamp}",
        "",
        "| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in arm_summaries:
        checks = s.get("objective_checks")
        objective_str = f"{sum(1 for c in checks if c['passed'])}/{len(checks)}" if checks else "-"

        jd = s.get("judge") or {}
        if "overall" in jd:
            judge_str = f"{jd['overall']:.1f}"
        elif "error" in jd:
            judge_str = "error"
        else:
            judge_str = "-"

        agent = s.get("agent") or {}
        cost = agent.get("cost_usd")
        cost_str = f"{cost:.4f}" if isinstance(cost, (int, float)) else "-"
        turns_str = str(agent.get("num_turns")) if agent.get("num_turns") is not None else "-"
        duration_str = str(agent.get("duration_ms")) if agent.get("duration_ms") is not None else "-"

        err = s.get("error")
        # Error details can carry multiline stderr or `|`s — keep the table
        # intact. The cut is marked: an error cut off mid-sentence at
        # exactly 200 characters reads as the whole error, and the reader
        # has no way to tell there is more of it in summary.json, which
        # keeps the detail in full.
        err_str = ""
        if err:
            err_str = " ".join(
                f"{err['type']}: {err['detail']}".split()).replace("|", "\\|")
            if len(err_str) > _REPORT_CELL_CHARS:
                err_str = err_str[:_REPORT_CELL_CHARS - 1] + "…"

        lines.append(f"| {s['arm']} | {objective_str} | {judge_str} | {cost_str} | "
                     f"{turns_str} | {duration_str} | {err_str} |")
    return "\n".join(lines) + "\n"


def _run_arm(arm_name: str, fixture: dict, seed: Path, registries: dict[str, dict],
            args: argparse.Namespace, timestamp: str,
            selection: tuple | None = None) -> dict:
    """Materialize a workspace, invoke the agent, score it, write results, clean up.

    `selection` is `select_models()`'s answer, resolved ONCE by main() and
    passed in: the roster is one file describing one run, and re-reading it per
    arm let two arms of the same run disagree if it changed underneath them.
    A selection error is checked and recorded FIRST, before any workspace is
    materialized (mkdtemp/copytree/git init) — a run this arm will never make
    is not worth building one only to shutil.rmtree it straight back out.
    """
    agent_model, roster_judge_model, selection_error = (
        selection if selection is not None else select_models(fixture, args))
    if selection_error:
        # A runner-level error, recorded on the arm exactly like an agent
        # failure, so it leaves through main()'s existing exit-2 path instead
        # of running the agent on a model nobody chose. Checked BEFORE
        # materializing anything: a workspace this run will never use (no
        # agent is ever invoked) is not worth an mkdtemp + copytree + a git
        # init/add/commit only to shutil.rmtree it two lines later.
        error = {"type": "model-selection", "detail": selection_error}
        _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                       error, None, None, None, None)
        return {"arm": arm_name, "error": error, "agent": None,
                "objective_checks": None, "judge": None}

    # run_setup (inside materialize_workspace, before the bookkeeping commit)
    # can fail — a fixture's `setup:` script (e.g. disarm-inherited-reach's)
    # builds real git repositories in the workspace and then deletes its own
    # machinery (setup.sh, any template dir) as its last step, and committing
    # first would let that machinery survive into the "seed" commit even
    # though it no longer exists on disk (see `materialize_workspace`'s and
    # `run_setup`'s own docstrings). `materialize_workspace` raises rather
    # than returning an error dict here, so the failure is caught outside its
    # own try/finally and the half-built workspace it still made is cleaned
    # up via the exception's own `workspace` attribute.
    try:
        workspace = materialize_workspace(seed, fixture)
    except SetupFailedError as exc:
        error = {"type": exc.detail["error"], "detail": exc.detail.get("detail", "")}
        _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                       error, None, None, None, None)
        shutil.rmtree(exc.workspace, ignore_errors=True)
        return {"arm": arm_name, "error": error, "agent": None,
                "objective_checks": None, "judge": None}
    try:
        assert_stand_ins_on_path(workspace, agent_env(workspace, fixture.get("env")),
                                 fixture.get("env"))

        arm_config = {
            "name": arm_name,
            "model": agent_model,
            "timeout": args.timeout or fixture.get("timeout_s", 600),
            "env": fixture.get("env"),
        }
        # A bad `registry:` (missing field, wrong type, unknown URL, or a
        # resolved path that doesn't exist) becomes an error dict here — the
        # same shape run_agent returns for skill_not_found — rather than an
        # uncaught KeyError/ValueError. _run_arm's only exception handling is
        # the `finally:` below, so anything raised here used to kill the
        # WHOLE run (including --arm both's other arm) with a bare
        # traceback: no report.md, no summary.json, and main() never reached
        # its documented `return 2`. A TRUTHY non-string `registry:` (a
        # list, an int, a mapping, a bool — YAML will happily hand over any
        # of these) used to reach _normalize_registry_url's `.strip()` with
        # the raw value and raise an uncaught AttributeError/TypeError;
        # `invalid_registry_field` closes that alongside the missing/blank
        # case above.
        registry_error = None
        if arm_name == "with_skill":
            registry_value = fixture.get("registry")
            if not registry_value:
                registry_error = {
                    "error": "missing_registry_field",
                    "detail": f"fixture for skill {fixture.get('skill')!r} has "
                              "no (or a blank) 'registry:' field"}
            elif not isinstance(registry_value, str):
                registry_error = {
                    "error": "invalid_registry_field",
                    "detail": f"fixture for skill {fixture.get('skill')!r} has "
                              "a 'registry:' field that must be a string, "
                              f"not {type(registry_value).__name__}"}
            else:
                try:
                    entry = registry_for_url(registries, registry_value)
                except ValueError as exc:
                    registry_error = {"error": "unknown_registry", "detail": str(exc)}
                else:
                    if not entry["path"].is_dir():
                        # The registry's NAME and layout, not its resolved
                        # absolute path — this detail reaches summary.json,
                        # which eval.yml commits to the public eval-results
                        # branch (item 6, #129 review round 4).
                        registry_error = {
                            "error": "registry_not_found",
                            "detail": f"registry {entry['name']!r} has no "
                                      f"local checkout for layout "
                                      f"{entry['layout']!r}"}
                    else:
                        arm_config["skill"] = fixture["skill"]
                        arm_config["registry"] = entry["path"]
                        arm_config["layout"] = entry["layout"]
                        arm_config["registry_name"] = entry["name"]

        result = registry_error if registry_error is not None else run_agent(
            workspace, fixture["prompt"], arm_config)

        error = None
        agent_summary = None
        objective_checks = None
        judge_result = None
        raw = result.get("raw")

        if "error" in result:
            error = {"type": result["error"], "detail": result.get("detail", "")}
        else:
            agent_summary = {
                "cost_usd": result.get("cost_usd"),
                "num_turns": result.get("num_turns"),
                "duration_ms": result.get("duration_ms"),
                "usage": result.get("usage"),
            }
            # The SAME fixture errors the objective-only path names, at the
            # one call site that has a transcript and so is the only place
            # `SeedTooLarge` can actually fire: an uncaught one here came
            # out of the list comprehension in `main` as a traceback and
            # exit 1, losing both arms' artifacts with it. Recorded as an
            # arm error, in the shape `run_setup` already uses, which
            # `main` turns into exit 2.
            try:
                objective_checks = objective.run_checks(
                    fixture, str(workspace), str(seed),
                    transcript=result.get("transcript"))
            except objective.FixtureError as exc:
                error = {"type": "invalid_fixture", "detail": str(exc)}
                _write_summary(args.results_dir, fixture["skill"], arm_name,
                               timestamp, error, agent_summary, None, None, raw)
                return {"arm": arm_name, "error": error,
                        "agent": agent_summary, "objective_checks": None,
                        "judge": None}

            if not args.no_judge:
                diff = _build_judge_diff(workspace)
                judge_cfg = fixture.get("judge", {})
                try:
                    judge_result = judge.score(
                        fixture["judge_rubric"], result.get("transcript") or "", diff,
                        model=roster_judge_model,
                        timeout=judge_cfg.get("timeout_s", 120),
                        weights=judge_cfg.get("weights"),
                    )
                except guidance.GuidanceError:
                    # S1-a-2. A sink's own timeout refusal is a CONFIGURATION
                    # error, not a judge result: recorded as `{"error": ...}`
                    # it would score the arm and exit 0/1 with the rule never
                    # named. Re-raised so main()'s rc-2 contract holds.
                    raise
                except Exception as exc:  # noqa: BLE001 — record, never crash the run
                    judge_result = {"error": str(exc)}

        _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                       error, agent_summary, objective_checks, judge_result, raw)

        return {"arm": arm_name, "error": error, "agent": agent_summary,
                "objective_checks": objective_checks, "judge": judge_result}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _write_pre_run_error(args: argparse.Namespace, fixture: dict,
                         error_type: str, detail: str) -> str:
    """Record a fixture-level error as the artifacts a run would have left.

    A pre-run refusal that only printed to stdout left `results/` with
    nothing in it, so the reason the run produced no numbers was visible
    only to whoever watched it happen. The report and one summary.json per
    arm carry the named error instead, in the shape `_render_report` and
    `_write_summary` already use for an arm that failed.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    error = {"type": error_type, "detail": detail}
    arm_names = (["with_skill", "without_skill"] if args.arm == "both"
                 else [args.arm])
    for arm_name in arm_names:
        _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                       error, None, None, None, None)
    report = _render_report(fixture["skill"], fixture.get("prompt", ""),
                            timestamp,
                            [{"arm": name, "error": error} for name in arm_names])
    report_path = args.results_dir / fixture["skill"] / timestamp / "report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    return timestamp


# ---------------------------------------------------------------------------
# The `guidance` subject (#97)
#
# A skill arm installs a skill and runs with `--setting-sources project`. A
# guidance arm delivers a payload the way the fleet does — the real
# fleet-memory.sh hook, into a FRESH scratch config dir — and runs with
# `--setting-sources user,project`. Every arm then PROVES its delivery with a
# magic-token probe before it is allowed to score anything: on a machine
# carrying the fleet hook the real ~/.claude/CLAUDE.md already IS the
# guidance, so an unisolated `without` arm reports a null delta that reads as
# "the guidance does nothing".
# ---------------------------------------------------------------------------

SKILL_ARMS = ("objective-only", "with_skill", "without_skill", "both")

DEFAULT_GUIDANCE_ARMS = {"with_guidance": {"mode": "section"},
                         "without_guidance": {"mode": "none"}}

_ARM_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

# A-N2-2. An arm name becomes more paths than the arm directory, and the two
# it also becomes were unmodelled. Measured on f9115ce, both rc 1 and both a
# traceback:
#   * an arm named `report.md` collided with the run's OWN report — the arm's
#     summary.json and transcripts/raw.json were written first, then
#     `_render_report` opened the arm DIRECTORY for writing:
#     `IsADirectoryError: [Errno 21]`;
#   * `a` * 255 (and 256, and 4096) was `OSError: [Errno 36] File name too
#     long`, out of the per-arm workspace's mkdtemp rather than out of the
#     arm directory, because that path carries a prefix as well as the name.
#
# The files a run writes INTO the run directory, beside the per-arm dirs, and
# the ones it writes INSIDE an arm dir. Only the first class can collide with
# an arm name; the second is why an arm called `summary.json` is harmless.
# `test_the_arm_name_refusal_covers_every_file_the_run_writes` parses this
# module and refuses any write-open whose filename is in neither tuple, so a
# new run-directory file cannot arrive without being classified.
REPORT_NAME = "report.md"
RUN_DIR_FILES = (REPORT_NAME,)
ARM_DIR_FILES = ("summary.json", "raw.json")

# The prefix every per-arm workspace's mkdtemp carries, named once so the
# length cap below and the call sites cannot drift apart.
ARM_WORKSPACE_PREFIX = "skills-evals-"
# mkdtemp appends 8 random characters to the prefix it is given, and the
# longest single filesystem component is 255 bytes on every filesystem this
# runs on. The workspace is the tightest consumer of an arm name, so it is
# what the cap is derived from rather than a number someone picked.
_NAME_MAX = 255
_MKDTEMP_RANDOM_LEN = 8
MAX_ARM_NAME_LEN = (_NAME_MAX - len(ARM_WORKSPACE_PREFIX) - 1
                    - _MKDTEMP_RANDOM_LEN)

# The anchor `_names_a_new_directory` measures against. Any absolute path that
# is not the filesystem root works; it never exists and is never written.
_ARM_NAME_ANCHOR = Path("/arm-name-check")


def _names_a_new_directory(name: str) -> bool:
    """Does `name` name a NEW directory directly under a run directory?

    A2-N2. The character class above accepts `.` and `..`, which are the two
    names that do NOT. Measured through main(), one arm per run: an arm named
    `..` wrote `summary.json` and `transcripts/raw.json` one level ABOVE the
    timestamped run directory — into the per-key directory that accumulates
    run history on the public `eval-results` branch — and `.` wrote into the
    run directory itself, on top of whatever was there.

    Stated as the property rather than as a blocklist of the two names that
    break it today: join the name to an anchor, normalise it the way the
    filesystem will, and require the result to be a direct child of the
    anchor still called what it was called. `...` and `.hidden` pass — they
    really are new directories — and only `.` and `..` do not.
    """
    joined = Path(os.path.normpath(_ARM_NAME_ANCHOR / name))
    return joined.parent == _ARM_NAME_ANCHOR and joined.name == name

# The placeholder a guidance fixture writes where the run's magic token goes.
# The token is fresh per run, so a fixture cannot name it; `transcript_matches`
# patterns (and any other check string) get it substituted in at score time.
TOKEN_PLACEHOLDER = "$MAGIC_TOKEN"
# The CONTROL arm's own token, delivered to it and to nothing else.
DECOY_PLACEHOLDER = "$DECOY_TOKEN"


def _validate_arm_entry(name: str, entry: dict) -> dict:
    if isinstance(name, str) and name in RUN_DIR_FILES:
        raise guidance.GuidanceError(
            f"invalid arm name {name!r}: the run writes "
            f"{', '.join(RUN_DIR_FILES)} into the run directory itself, "
            "beside the per-arm directories, so an arm of that name is a "
            "directory where a file has to go — the arm's own summary.json "
            "and transcripts/raw.json are written first and the report then "
            "fails with IsADirectoryError, after the run has spent every arm")
    if isinstance(name, str) and len(name) > MAX_ARM_NAME_LEN:
        raise guidance.GuidanceError(
            f"invalid arm name of {len(name)} characters: an arm name may be "
            f"at most {MAX_ARM_NAME_LEN}. It becomes a directory name under "
            "results/ AND the per-arm workspace "
            f"`{ARM_WORKSPACE_PREFIX}<name>-XXXXXXXX`, which is the longer of "
            f"the two; past {_NAME_MAX} bytes the filesystem refuses it with "
            "`File name too long` part-way into the run instead of naming a "
            "rule here")
    if (not isinstance(name, str) or not _ARM_NAME_RE.fullmatch(name)
            or not _names_a_new_directory(name)):
        raise guidance.GuidanceError(
            f"invalid arm name {name!r}: arm names become directory names "
            "under results/, so they must be a single path segment that "
            "names a NEW directory — `.` and `..` are neither, and an arm "
            "named `..` writes its summary one level above the run "
            "directory, into the history the public results branch carries")
    if not isinstance(entry, dict) or "mode" not in entry:
        raise guidance.GuidanceError(f"arm {name!r} must be a mapping with a `mode:`")
    unknown = sorted(set(entry) - {"mode", "objective_checks"})
    if unknown:
        # A typo'd `objective_check:` would drop the arm's whole check list
        # and still report green, which is worse than failing at load time.
        raise guidance.GuidanceError(
            f"arm {name!r} has unknown key(s) {unknown} — an arm takes `mode:` "
            "and an optional `objective_checks:`")
    mode = entry["mode"]
    if mode not in guidance.MODES:
        raise guidance.GuidanceError(
            f"arm {name!r} has unknown mode {mode!r} — expected one of "
            f"{', '.join(guidance.MODES)}")
    # Name and expectation must agree. The guard derives its expectation from
    # the MODE, so a `with_*` arm carrying `mode: none` would be a control arm
    # wearing a treatment arm's name — the summary would read as a delivered
    # arm that saw nothing, which is precisely the shape of a real failure.
    if name.startswith("with_") and mode == "none":
        raise guidance.GuidanceError(
            f"arm {name!r} is named as a treatment arm but carries "
            "`mode: none` — rename it or give it a mode that delivers")
    if not name.startswith("with_") and mode != "none" and name.startswith("without_"):
        raise guidance.GuidanceError(
            f"arm {name!r} is named as a control arm but carries "
            f"`mode: {mode}` — rename it or give it `mode: none`")
    return {"name": name, "mode": mode,
            "objective_checks": entry.get("objective_checks")}


def guidance_arms(fixture: dict, arm_flag: str, ablation: bool = False) -> list[dict]:
    """The arms to run, in declaration order.

    Default pair `section` / `none` — "does this section teach the behavior".
    `ablation: [full, full-minus-section]` is the second pair, `--ablation`,
    which the matrix runner schedules monthly: the marginal value of the
    section IN SITU inside a 56 KB always-on file, which is the question that
    decides whether it keeps paying for its bytes.
    """
    if ablation:
        modes = fixture.get("ablation")
        if not isinstance(modes, list) or len(modes) != 2:
            raise guidance.GuidanceError(
                "--ablation needs the fixture to declare `ablation:` as a list "
                "of exactly two modes (e.g. [full, full-minus-section])")
        declared = {f"ablation_{str(m).replace('-', '_')}": {"mode": m} for m in modes}
        if len(declared) != 2:
            raise guidance.GuidanceError(
                f"`ablation: {modes}` names the same mode twice")
    else:
        # ABSENT means "take the default pair". PRESENT means "these are my
        # arms", and an empty, null or non-mapping value is a fixture error —
        # `fixture.get("arms") or DEFAULT_GUIDANCE_ARMS` made the check below
        # dead code, so `arms: {}`, `arms:` and `arms: []` all silently ran
        # somebody else's `section`/`none` pair under this fixture's name.
        declared = (DEFAULT_GUIDANCE_ARMS if "arms" not in fixture
                    else fixture["arms"])
        if not isinstance(declared, dict) or not declared:
            raise guidance.GuidanceError(
                "`arms:` must be a mapping of arm name -> {mode: ...}, and a "
                f"non-empty one; got {declared!r}. Omit the key entirely to "
                "take the default "
                f"{'/'.join(a['mode'] for a in DEFAULT_GUIDANCE_ARMS.values())}"
                " pair.")
    arms = [_validate_arm_entry(name, entry) for name, entry in declared.items()]
    if arm_flag in ("both", "all"):
        return arms
    for arm in arms:
        if arm["name"] == arm_flag:
            return [arm]
    raise guidance.GuidanceError(
        f"--arm {arm_flag!r} names no arm in this fixture (declared: "
        f"{', '.join(a['name'] for a in arms)}; or `both` for all of them)")


def substitute_token(value, token: str, decoy: str | None = None):
    """Replace the fixture's `$MAGIC_TOKEN` placeholder with this run's token,
    recursively, in a copy — the fixture dict itself is never mutated.

    `$DECOY_TOKEN` is the control arm's own token, and is substituted only for
    an arm that HAS one (`mode: none`). Left alone elsewhere it stays a
    literal, and a check looking for it fails loudly rather than passing on a
    placeholder nobody filled in.
    """
    if isinstance(value, str):
        out = value.replace(TOKEN_PLACEHOLDER, token)
        return out if decoy is None else out.replace(DECOY_PLACEHOLDER, decoy)
    if isinstance(value, list):
        return [substitute_token(item, token, decoy) for item in value]
    if isinstance(value, dict):
        return {key: substitute_token(item, token, decoy)
                for key, item in value.items()}
    return value


def _guard_error(guard: dict) -> dict:
    """The error block for an arm whose delivery could not be proved.

    Two distinguishable shapes, both INCONCLUSIVE and both exit 2, neither
    ever PASS or FAIL: `guard_error` (the probe could not run at all — no
    credential, CLI missing; a guard that cannot run is never a skipped
    guard) and `guard_miss` (it ran and disagreed with this arm's mode).
    """
    if guard["error"]:
        return {"type": "guard_error",
                "detail": f"delivery guard could not run: {guard['error']['type']}: "
                          f"{guard['error']['detail']}"}
    if guard.get("contaminated"):
        return {"type": "guard_contaminated",
                "detail": "the delivery guard's probe reported a token this "
                          "arm was NOT delivered — a control arm reporting the "
                          "TREATMENT token, or a treatment arm reporting the "
                          "control's DECOY. Either way this arm read memory "
                          "the harness never delivered to it, so the per-arm "
                          "isolation did not hold and every number in this run "
                          "is suspect; no score is written for it"}
    expectation = "the magic word" if guard["expected"] else "no magic word"
    observed = "saw it" if guard["observed"] else "did not see it"
    return {"type": "guard_miss",
            "detail": f"delivery guard expected {expectation}, the probe "
                      f"{observed} — this arm did not read the token it was "
                      "delivered (a treatment arm its payload's, a control arm "
                      "its decoy), so it never read its own scratch user "
                      "memory; no score is written for it"}


def _run_guidance_arm(arm: dict, fixture: dict, seed: Path, ctx: dict,
                      args: argparse.Namespace, timestamp: str) -> dict:
    """Materialize a scratch dir, deliver, guard, invoke, score, clean up."""
    scratch = Path(tempfile.mkdtemp(
        prefix=f"{ARM_WORKSPACE_PREFIX}{arm['name']}-"))
    try:
        workspace, home = scratch / "ws", scratch / "home"
        config, tmpdir = scratch / "config", scratch / "tmp"
        for path in (workspace, home, config, tmpdir):
            path.mkdir(parents=True)
        if seed.is_dir():
            shutil.copytree(seed, workspace, dirs_exist_ok=True)
        _git("init", "-q", cwd=workspace)
        _git("add", "-A", cwd=workspace)
        _git("commit", "-q", "--allow-empty", "-m", "seed", cwd=workspace)

        delivery = ctx["delivery"]
        # The token THIS arm is delivered. A treatment arm gets the run's
        # magic token; the control gets a DECOY of its own, so that its guard
        # can ask a question with a wrong answer — "does this arm read its own
        # scratch user memory?" — instead of the vacuous "no magic word?", the
        # one answer a `none` arm gave whether it was clean or contaminated.
        decoy = ctx["decoys"].get(arm["name"])
        arm_token = decoy if decoy is not None else ctx["token"]
        # Every token this run minted that was NOT delivered to this arm.
        # Symmetric by construction: the treatment token for a control arm,
        # the control's decoy for a treatment arm, and any other control's
        # decoy for a control arm. Reporting one of these means the arm read
        # memory nobody delivered to it.
        forbidden = tuple(other for other in (ctx["token"], *ctx["decoys"].values())
                          if other != arm_token)
        payload = guidance.assemble(ctx["guidance_dir"], ctx["row"], arm["mode"],
                                    token=arm_token)
        info = guidance.deliver(
            ctx["guidance_dir"], scratch=scratch, home=home, payload=payload,
            dest_dir=config if delivery == "user" else workspace)
        env = guidance.agent_env(workspace=workspace, home=home, tmpdir=tmpdir,
                                 config_dir=config, env_spec=fixture.get("env"))
        # A delivery that provably did not happen is not a guard question.
        # `installed` and the hook's returncode are offline and free; the
        # guard costs a real model call and can only answer the AMBIGUOUS
        # "the probe did not see the token" — which is what a sabotaged hook
        # (prints `fleet-guidance: current`, writes nothing, exits 0) used to
        # get reported as. Both facts land in the arm's `extra` either way.
        extra = {"subject": "guidance", "section": ctx["section"],
                 "mode": arm["mode"], "bytes": info["bytes"],
                 "delivery": delivery, "hook_verdict": info["verdict"],
                 "installed": info["installed"], "decoy": decoy,
                 "hook_returncode": info["returncode"], "guard": None}
        if info["returncode"] is not None and (
                not info["installed"] or info["returncode"] != 0):
            error = {"type": "delivery_failed",
                     "detail": (
                         f"the hook exited {info['returncode']} and the marked "
                         f"block is {'present' if info['installed'] else 'ABSENT'} "
                         f"in {info['dest']} — this arm was never delivered "
                         "its payload, so nothing about it is measurable; no "
                         "guard call was made and no score is written")}
            _write_summary(args.results_dir, None, arm["name"], timestamp,
                           error, None, None, None, None,
                           key=ctx["key"], extra=extra)
            return {"arm": arm["name"], "mode": arm["mode"], "error": error,
                    "agent": None, "objective_checks": None, "judge": None,
                    "guard": None, "inconclusive": True}

        setting_sources = guidance.SETTING_SOURCES[delivery]
        # The guard's preflight model: the fixture's own `model:` pin when it
        # has one, else the CLI's default. When the model roster (#67) lands,
        # its `preflight` entry — the cheapest model that can answer a
        # tool-free probe — is what this line consults instead.
        preflight_model = args.model or fixture.get("model")
        guard = guidance.run_guard(
            workspace=workspace, token=arm_token,
            expected=guidance.guard_expectation(arm["mode"]), env=env,
            # The other side, for EVERY arm: it must not report a token it
            # was not delivered.
            forbidden_tokens=forbidden,
            setting_sources=setting_sources, model=preflight_model,
            timeout=(fixture.get("guard") or {}).get("timeout_s", 300))

        extra["guard"] = guard

        if not guard["ok"]:
            error = _guard_error(guard)
            _write_summary(args.results_dir, None, arm["name"], timestamp,
                           error, None, None, None, None,
                           key=ctx["key"], extra=extra)
            return {"arm": arm["name"], "mode": arm["mode"], "error": error,
                    "agent": None, "objective_checks": None, "judge": None,
                    "guard": guard, "inconclusive": True}

        arm_config = {
            "name": arm["name"],
            "model": args.model or fixture.get("model"),
            "timeout": args.timeout or fixture.get("timeout_s", 600),
            "setting_sources": setting_sources,
            "env_override": env,
        }
        result = run_agent(workspace, fixture["prompt"], arm_config)

        error = None
        agent_summary = None
        objective_checks = None
        judge_result = None
        raw = result.get("raw")

        if "error" in result:
            error = {"type": result["error"], "detail": result.get("detail", "")}
        else:
            agent_summary = {
                "cost_usd": result.get("cost_usd"),
                "num_turns": result.get("num_turns"),
                "duration_ms": result.get("duration_ms"),
                "usage": result.get("usage"),
            }
            checks = arm["objective_checks"] or fixture.get("objective_checks", [])
            scored = dict(fixture)
            scored["objective_checks"] = substitute_token(
                checks, ctx["token"], decoy)
            objective_checks = objective.run_checks(
                scored, str(workspace), str(seed), transcript=result.get("transcript"))

            if not args.no_judge and fixture.get("judge_rubric"):
                _git("add", "-A", cwd=workspace)
                # `:!CLAUDE.md` only under the project-delivery fallback, where
                # the hook wrote the payload INTO the workspace: without it the
                # judge would be handed the whole delivered corpus as if the
                # agent had written it, which under `mode: full` is 56 KB of
                # diff that says nothing about the agent's work.
                excludes = [":!.claude"]
                if delivery == "project":
                    excludes.append(":!CLAUDE.md")
                diff = _git("diff", "--cached", "--", ".", *excludes,
                            cwd=workspace).stdout
                judge_cfg = fixture.get("judge", {})
                try:
                    judge_result = judge.score(
                        fixture["judge_rubric"], result.get("transcript") or "",
                        diff, model=judge_cfg.get("model"),
                        timeout=judge_cfg.get("timeout_s", 120),
                        weights=judge_cfg.get("weights"))
                except guidance.GuidanceError:
                    # S1-a-2. A sink's own timeout refusal is a CONFIGURATION
                    # error, not a judge result: recorded as `{"error": ...}`
                    # it would score the arm and exit 0/1 with the rule never
                    # named. Re-raised so main()'s rc-2 contract holds.
                    raise
                except Exception as exc:  # noqa: BLE001 — record, never crash the run
                    judge_result = {"error": str(exc)}

        _write_summary(args.results_dir, None, arm["name"], timestamp, error,
                       agent_summary, objective_checks, judge_result, raw,
                       key=ctx["key"], extra=extra)
        return {"arm": arm["name"], "mode": arm["mode"], "error": error,
                "agent": agent_summary, "objective_checks": objective_checks,
                "judge": judge_result, "guard": guard, "inconclusive": False}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _render_guidance_report(section: str, prompt: str, timestamp: str,
                            delivery: str, arm_bytes: dict,
                            arm_summaries: list[dict]) -> str:
    """The guidance report. Its header names the MODE PAIR, because "with vs
    without" is meaningless here without it — `section` vs `none` and `full`
    vs `full-minus-section` are different questions about the same section.
    """
    modes = ", ".join(f"{s['arm']}={s['mode']}" for s in arm_summaries)
    lines = [
        f"# Eval report: guidance/{section}",
        "",
        f"- Modes: {modes}",
        f"- Delivery: {delivery}",
        f"- Prompt: {prompt.strip()}",
        f"- Timestamp: {timestamp}",
        "",
        "| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in arm_summaries:
        checks = s.get("objective_checks")
        objective_str = (f"{sum(1 for c in checks if c['passed'])}/{len(checks)}"
                         if checks else "-")
        jd = s.get("judge") or {}
        if "overall" in jd:
            judge_str = f"{jd['overall']:.1f}"
        elif "error" in jd:
            judge_str = "error"
        else:
            judge_str = "-"
        agent = s.get("agent") or {}
        cost = agent.get("cost_usd")
        cost_str = f"{cost:.4f}" if isinstance(cost, (int, float)) else "-"
        guard = s.get("guard") or {}
        if guard.get("ok"):
            guard_str = "ok (saw it)" if guard.get("expected") else "ok (clean)"
        elif guard.get("observed") is None:
            guard_str = "INCONCLUSIVE (probe failed)"
        else:
            guard_str = (f"INCONCLUSIVE (expected {guard.get('expected')}, "
                         f"observed {guard.get('observed')})")
        err = s.get("error")
        err_str = (" ".join(f"{err['type']}: {err['detail']}".split())
                   .replace("|", "\\|")[:200] if err else "")
        lines.append(f"| {s['arm']} | {s['mode']} | {arm_bytes.get(s['arm'], '-')} | "
                     f"{guard_str} | {objective_str} | {judge_str} | {cost_str} | "
                     f"{err_str} |")
    return "\n".join(lines) + "\n"


def _run_guidance(args: argparse.Namespace, fixture: dict) -> int:
    """`subject: guidance` — the whole run, from section id to exit code."""
    section = fixture.get("section")
    if not isinstance(section, str) or not section:
        print(f"{args.eval_dir / 'fixture.yaml'} has `subject: guidance` but no "
              "(or a non-string) `section:` — the id of a row in "
              "_agent-guidance's agents-md/eval-coverage.yml")
        return 2
    if "/" in section or section in (".", ".."):
        print(f"invalid section id {section!r}: it becomes a results/ path segment")
        return 2

    key = f"guidance/{section}"
    seed = args.eval_dir / "seed"

    if args.arm == "objective-only":
        # N-f. A guidance fixture's checks are PER ARM, so a top-level
        # `objective_checks:` is usually absent — and `run_checks` over zero
        # checks printed `{"checks": []}` and exited 0, which reads as "every
        # check passed". Say so instead. This is the convention
        # check-guidance-coverage.js states in its own header: an empty
        # measurement is not a passing one.
        if not fixture.get("objective_checks"):
            print(f"{args.eval_dir / 'fixture.yaml'} declares no top-level "
                  "`objective_checks:` — objective-only has nothing to score. "
                  "A guidance fixture's checks are per arm; run it with "
                  "`--arm both` (or a named arm) instead.")
            return 2
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            if seed.is_dir():
                shutil.copytree(seed, workspace)
            else:
                workspace.mkdir(parents=True)
            results = objective.run_checks(fixture, str(workspace), str(seed))
        print(json.dumps({"subject": "guidance", "section": section,
                          "arm": args.arm, "checks": results}, indent=2))
        return 0 if all(r["passed"] for r in results) else 1

    if not isinstance(fixture.get("prompt"), str) or not fixture["prompt"]:
        print(f"{args.eval_dir / 'fixture.yaml'} is missing a string `prompt:`")
        return 2

    try:
        arms = guidance_arms(fixture, args.arm, args.ablation)
        guidance_dir = guidance.require_guidance_dir(guidance.resolve_guidance_dir(
            args.guidance, os.environ.get("AGENT_GUIDANCE_DIR"),
            Path(__file__).resolve().parent.parent))
        row = guidance.find_row(guidance.load_manifest(guidance_dir), section,
                                guidance_dir)
    except guidance.GuidanceError as exc:
        print(f"guidance configuration error: {exc}")
        return 2

    ctx = {"guidance_dir": guidance_dir, "row": row, "section": section,
           "key": key, "delivery": args.delivery,
           # One fresh token per RUN, shared by every arm: the control arm
           # looks for the SAME token the treatment arm was given, which is
           # what turns "the control saw it" into proof of contamination.
           "token": guidance.new_token(),
           # Every `none` arm's decoy, minted HERE rather than inside the arm
           # that gets it. A TREATMENT arm's guard needs them too — a
           # treatment probe reporting a control's decoy is the same per-arm
           # isolation failure seen from the other side — and an arm cannot
           # be handed a token that does not exist until its own turn comes.
           "decoys": {arm["name"]: guidance.new_decoy_token()
                      for arm in arms if arm["mode"] == "none"}}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        arm_summaries = [_run_guidance_arm(arm, fixture, seed, ctx, args, timestamp)
                         for arm in arms]
    except guidance.GuidanceError as exc:
        # A checkout missing the hook, a heading that has drifted from its
        # manifest row, a payload that cannot be read: all configuration, all
        # exit 2, none of them a traceback out of the middle of a run.
        print(f"guidance configuration error: {exc}")
        return 2

    report_dir = args.results_dir / key / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)
    arm_bytes = {}
    for arm in arm_summaries:
        summary_path = report_dir / arm["arm"] / "summary.json"
        with open(summary_path, encoding="utf-8") as f:
            arm_bytes[arm["arm"]] = json.load(f)["bytes"]
    report = _render_guidance_report(section, fixture["prompt"], timestamp,
                                     args.delivery, arm_bytes, arm_summaries)
    with open(report_dir / REPORT_NAME, "w", encoding="utf-8") as f:
        f.write(report)

    inconclusive = [s for s in arm_summaries if s["inconclusive"]]
    for arm_summary in inconclusive:
        guard = arm_summary["guard"]
        # A `delivery_failed` arm never reached the guard, so there is no
        # expected/observed pair to report — only the delivery's own detail.
        preamble = (f"guard expected {guard['expected']}, observed "
                    f"{guard['observed']} — ") if guard else "delivery — "
        print(f"INCONCLUSIVE {arm_summary['arm']} (mode "
              f"{arm_summary['mode']}): {preamble}"
              f"{arm_summary['error']['detail']}")
    if inconclusive:
        print("INCONCLUSIVE: at least one arm could not prove its delivery; "
              "no score was written for it. This is never a PASS and never a "
              "FAIL.")
        return 2

    errored_arms = [s["arm"] for s in arm_summaries if s["error"]]
    if errored_arms:
        print(f"Runner-level error in arm(s): {', '.join(errored_arms)}")
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_dir", type=Path)
    # Deliberately NOT an argparse `choices=` list any more: a guidance
    # fixture declares its own arm names (the delivery canary declares five,
    # one per mode), which argparse cannot know at parse time. Validated per
    # subject below instead, with the same exit code (2) and a message that
    # names the arms this fixture actually has.
    parser.add_argument("--arm", default="objective-only",
                        help="objective-only | with_skill | without_skill | both "
                             "for a skill fixture; both, or any arm name the "
                             "fixture declares, for a guidance fixture")
    parser.add_argument("--guidance", default=None,
                        help="path to an _agent-guidance checkout (guidance "
                             "fixtures only); else $AGENT_GUIDANCE_DIR, else the "
                             "sibling ../_agent-guidance")
    parser.add_argument("--delivery", default="user", choices=list(guidance.DELIVERIES),
                        help="how the guidance reaches the agent: `user` (the "
                             "production path — the fleet hook writes "
                             "$CLAUDE_CONFIG_DIR/CLAUDE.md, the CLI reads it as "
                             "user memory) or `project` (the fallback for a CLI "
                             "that does not honour CLAUDE_CONFIG_DIR for memory)")
    parser.add_argument("--ablation", action="store_true",
                        help="run the fixture's `ablation:` mode pair (full vs "
                             "full-minus-section) instead of its arms")
    parser.add_argument("--workspace", type=Path, default=None,
                        help="objective-only: score this workspace instead of the pristine seed")
    parser.add_argument("--registry", action="append", default=None,
                        help="registry checkout, repeatable: NAME=PATH (name from "
                             "harness/registries.yml), or a bare PATH (legacy) taken "
                             "as the agentskills entry; unknown names and empty "
                             "paths are rejected. Merges by name with "
                             "$SKILLS_EVALS_REGISTRIES (same NAME=PATH,NAME=PATH "
                             "shape; a bare entry there is also taken as "
                             "agentskills), then $AGENTSKILLS_DIR for agentskills "
                             "specifically, then a sibling checkout ../<name> next "
                             "to this repo for any name still unresolved")
    parser.add_argument("--model", default=None,
                        help="override the fixture's model for the agent")
    parser.add_argument("--roster", type=Path, default=None,
                        help="override the committed evals/roster.yml model "
                             "roster (tests and deliberate local runs only)")
    parser.add_argument("--no-judge", action="store_true", help="skip judge scoring")
    parser.add_argument("--timeout", type=int, default=None,
                        help="override the fixture's agent timeout (seconds); "
                             f"1..{guidance.MAX_TIMEOUT_S}, the same ceiling "
                             "the fixture's own `timeout_s:` is held to")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                        help="root directory for run outputs (summaries + reports)")
    args = parser.parse_args()

    # S1-a. The FLAG is checked before anything else — before the fixture is
    # loaded, before either subject branch, before any CLI call — because it
    # is the OTHER source of the value that reaches
    # `subprocess.run(timeout=...)`, and it OVERRIDES the fixture knob
    # `validate_timeouts` has just bounded (`args.timeout or
    # fixture.get("timeout_s", 600)`, twice below). Round 2 bounded the knob
    # and left the override unchecked, so the defect the ceiling was added to
    # close came straight back through the flag beside it: measured on
    # a6d165d, `--timeout 2200000` was rc 1 and a bare `OverflowError`,
    # `--timeout 2701` was accepted above the job budget, and `--timeout 3000`
    # against a scored leg that never returns did not come back at all.
    # argparse's `type=int` bounds nothing: it rejects `abc` and accepts every
    # integer there is, negative and absurd alike.
    #
    # `is not None` and not a truthiness test: `--timeout 0` is falsy, so
    # `args.timeout or ...` would silently fall back to the fixture's value
    # rather than honour a nonsense flag — a zero must be REFUSED by name, not
    # quietly ignored.
    if args.timeout is not None:
        try:
            guidance.check_timeout(args.timeout, "--timeout",
                                   guidance.CLI_TIMEOUT_REMEDY)
        except guidance.GuidanceError as exc:
            print(f"configuration error: {exc}")
            return 2

    fixture = None
    try:
        fixture = load_fixture(args.eval_dir)
        validate_mapping_keys(fixture, args.eval_dir / "fixture.yaml")
        validate_timeouts(fixture, args.eval_dir / "fixture.yaml")
    except MappingFixtureKeyError as exc:
        # A malformed `judge:` is #81's `invalid_judge_block` — named in
        # stdout AND recorded as report.md plus one summary.json per arm, so
        # a run that produced no numbers says why in `results/` rather than
        # only to whoever watched it. The load-time guard here refuses it
        # before the later `isinstance(judge_cfg, dict)` check can, so that
        # check would otherwise never be reached for a non-mapping and the
        # artifacts would silently stop being written. Only when the fixture
        # is well-formed enough to have a usable `skill:` — `_write_pre_run_
        # error` derives every path it writes from that name.
        skill_name = fixture.get("skill") if isinstance(fixture, dict) else None
        usable_skill = isinstance(skill_name, str)
        if usable_skill:
            try:
                _validate_skill_name(skill_name)
            except ValueError:
                usable_skill = False
        if exc.key == "judge" and usable_skill:
            print(f"invalid_judge_block: {exc}")
            _write_pre_run_error(args, fixture, "invalid_judge_block", str(exc))
            return 2
        print(f"fixture configuration error: {exc}")
        return 2
    except guidance.GuidanceError as exc:
        print(f"fixture configuration error: {exc}")
        return 2
    seed = args.eval_dir / "seed"

    # Two subjects: a skill copied into the workspace (the original, and
    # untouched by #97), and the fleet guidance delivered into user memory by
    # the real fleet-memory.sh hook. Everything below this branch is the skill
    # path exactly as it was.
    subject = fixture.get("subject", "skill")
    if subject == "guidance":
        try:
            return _run_guidance(args, fixture)
        except guidance.GuidanceError as exc:
            # The sink checks (S1-a-2) raise from inside whichever function
            # was about to spawn. Caught HERE so every one of them lands on
            # the rc-2 configuration contract instead of a traceback.
            print(f"configuration error: {exc}")
            return 2
    if subject != "skill":
        print(f"{args.eval_dir / 'fixture.yaml'} has unknown subject "
              f"{subject!r} — expected 'skill' or 'guidance'")
        return 2
    if args.arm not in SKILL_ARMS:
        print(f"--arm {args.arm!r} is not valid for a skill fixture "
              f"(expected one of {', '.join(SKILL_ARMS)})")
        return 2

    # Validated ONCE, here, before any path is derived from the fixture:
    # `_write_summary` and `report_path` below both build a filesystem path
    # out of `fixture["skill"]` unconditionally, for every arm — a fixture
    # missing "skill" or "prompt" used to die with a bare KeyError deep
    # inside _run_arm/_render_report, and a `skill:` containing `../` was
    # never rejected before those paths were built (run_agent's own check
    # only fires for the with_skill arm, by which point _write_summary has
    # already used the raw name for with_skill AND without_skill). Presence
    # first (a genuinely absent or blank field, same as
    # _load_registries_config's own missing check), then type — a TRUTHY
    # non-string `skill:`/`prompt:` (a list, an int) used to sail past a
    # bare `not fixture.get(f)` check and die later with an uncaught
    # TypeError from re.fullmatch or subprocess.run.
    required = ["skill"] if args.arm == "objective-only" else ["skill", "prompt"]
    missing = [f for f in required
              if fixture.get(f) is None or fixture.get(f) == ""]
    if missing:
        print(f"{args.eval_dir / 'fixture.yaml'} is missing required "
              f"field(s): {', '.join(missing)}")
        return 2
    bad_type = [f for f in required if not isinstance(fixture.get(f), str)]
    if bad_type:
        print(f"{args.eval_dir / 'fixture.yaml'} field(s) must be strings: " +
              ", ".join(f"{f!r} is {type(fixture[f]).__name__}" for f in bad_type))
        return 2

    # Validated HERE, before anything derives a path from it. It used to
    # run after the judge-mode guard below, and only for a non-objective-only
    # arm — so a fixture carrying both `skill: ../../ESCAPED` and a judge
    # mode this runner refuses had `_write_pre_run_error` build
    # `<results-dir>/../../ESCAPED/<timestamp>/report.md` and write it,
    # two directories above where the operator pointed the run. Every path
    # this function builds comes off this name, so the check comes first
    # and applies to every arm.
    try:
        _validate_skill_name(fixture["skill"])
    except ValueError as exc:
        print(f"invalid fixture: {exc}")
        return 2

    # `judge:` written as anything but a mapping — a list, a string, a
    # number, a bare `true`; YAML hands over all of them — used to reach
    # `.get("mode")` and raise an uncaught AttributeError: exit 1, a
    # traceback, and none of the artifacts a fixture-level refusal is
    # supposed to leave. Named and recorded like every other pre-run
    # refusal, and for every arm: a malformed block is malformed whether or
    # not this run would have reached the judge.
    judge_cfg = fixture.get("judge")
    if judge_cfg is None or judge_cfg == "":
        judge_cfg = {}
    if not isinstance(judge_cfg, dict):
        detail = (f"fixture's `judge:` block is a {type(judge_cfg).__name__}, "
                  "not a mapping: it must carry keys like `mode:`, `model:` "
                  "and `references:`, or be left out entirely")
        print(f"invalid_judge_block: {detail}")
        _write_pre_run_error(args, fixture, "invalid_judge_block", detail)
        return 2

    # A fixture whose `judge:` block asks for an instrument this runner
    # cannot drive is refused before any arm starts, rather than scored with
    # the wrong one. `_run_arm` still calls `judge.score()` with the three
    # keywords it knew before #81 — no mode, no references — so a
    # `judge.mode: pairwise` fixture used to be scored by the ABSOLUTE judge
    # against a ranking rubric: measured on recruiter-reply, exit 0 and a
    # report reading "Judge overall | 7.5", which is not a rank and means
    # nothing there. Wiring `_run_arm` onto `judge.score_fixture` belongs to
    # #97 (https://github.com/Adam-S-Daniel/skills-evals/issues/97); until
    # then the run either passes --no-judge or does not happen.
    #
    # The mode is casefolded, exactly as `judge.score()` casefolds it, so
    # `mode: Absolute` is absolute rather than "a mode this runner cannot
    # drive yet" — which said nothing true about a spelling of the mode the
    # runner does drive.
    #
    # objective-only is exempt because it runs no judge at all: these
    # fixtures are meant to exit 1 there with "no transcript", which is the
    # documented asymmetry rather than a runner error.
    judge_mode = judge_cfg.get("mode", "absolute")
    normalised_mode = (judge_mode.strip().casefold()
                       if isinstance(judge_mode, str) else judge_mode)
    if (args.arm != "objective-only" and not args.no_judge
            and normalised_mode not in (None, "", "absolute")):
        # Front-loaded: `_render_report` truncates this cell to 200
        # characters, and the three sentences of provenance that used to
        # open it pushed the issue, its URL and the flag that makes the run
        # work off the end of the report a reader actually sees.
        detail = (f"cannot drive judge mode {judge_mode!r} yet: re-run with "
                  "--no-judge and read the objective column. #97 "
                  "https://github.com/Adam-S-Daniel/skills-evals/issues/97 "
                  "wires the call site onto judge.score_fixture(); until "
                  "then _run_arm still calls judge.score() with the "
                  "arguments it knew before #81, so scoring this fixture "
                  "here would rank it with the absolute judge.")
        print(f"judge_mode_unsupported: {detail}")
        _write_pre_run_error(args, fixture, "judge_mode_unsupported", detail)
        return 2

    # Resolved and validated before ANY arm starts, including objective-only:
    # a bad --registry/$SKILLS_EVALS_REGISTRIES override used to be silently
    # ignored for objective-only (it never reaches resolve_registries at
    # all), so a typo'd override "worked" there while failing everywhere else.
    try:
        registries = resolve_registries(
            args.registry, os.environ.get("SKILLS_EVALS_REGISTRIES"),
            Path(__file__).resolve().parent.parent, os.environ.get("AGENTSKILLS_DIR"))
        _validate_registry_paths(registries)
    except ValueError as exc:
        print(f"registry configuration error: {exc}")
        return 2

    if args.arm == "objective-only":
        # `objective.FixtureError` — a `strip_seed:` written as anything but
        # a boolean, a seed file over the provenance read cap — is a fixture
        # error, and every other fixture error here is a named line and exit
        # 2. These two came out as an uncaught traceback and exit 1, which
        # is the code a legitimately FAILING eval returns: a fixture that
        # could not be scored at all was indistinguishable, to a CI job
        # reading the exit code, from one whose agent wrote a bad reply.
        try:
            if args.workspace:
                # An explicitly given workspace is scored as-is — the
                # caller's own responsibility to have already run any
                # `setup:` themselves (or to be scoring a hand-built
                # workspace that never needed it).
                workspace = args.workspace
                results = objective.run_checks(fixture, str(workspace),
                                               str(seed))
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    workspace = Path(tmp) / "ws"
                    shutil.copytree(seed, workspace)
                    setup_error = run_setup(workspace, fixture)
                    if setup_error is not None:
                        print(f"setup failed: {setup_error['detail']}")
                        return 2
                    results = objective.run_checks(fixture, str(workspace),
                                                   str(seed))
        except guidance.GuidanceError as exc:
            # run_setup's and the objective git checks' sink checks land here.
            print(f"configuration error: {exc}")
            return 2
        except objective.FixtureError as exc:
            # `SeedTooLarge` is a `FixtureError`, so one clause covers both.
            print(f"invalid_fixture: {exc}")
            _write_pre_run_error(args, fixture, "invalid_fixture", str(exc))
            return 2

        print(json.dumps({"skill": fixture["skill"], "arm": args.arm,
                          "checks": results}, indent=2))
        return 0 if all(r["passed"] for r in results) else 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arm_names = ["with_skill", "without_skill"] if args.arm == "both" else [args.arm]
    try:
        # Resolved once: one trusted-roster read, one model choice, both arms.
        selection = select_models(fixture, args)
        arm_summaries = [_run_arm(name, fixture, seed, registries, args,
                                  timestamp, selection)
                         for name in arm_names]
    except guidance.GuidanceError as exc:
        # Every subprocess sink `_run_arm` can reach — run_setup, run_agent,
        # _nested_repo_diff, judge.score, the objective git checks — checks
        # its timeout on entry and raises this. Named rc 2, never a
        # traceback and never `Runner-level error in arm(s)`.
        print(f"configuration error: {exc}")
        return 2

    report = _render_report(fixture["skill"], fixture["prompt"], timestamp, arm_summaries)
    report_path = args.results_dir / fixture["skill"] / timestamp / REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    errored_arms = [s["arm"] for s in arm_summaries if s["error"]]
    if errored_arms:
        print(f"Runner-level error in arm(s): {', '.join(errored_arms)}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
