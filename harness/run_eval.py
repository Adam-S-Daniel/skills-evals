#!/usr/bin/env python3
"""Run an eval fixture.

Usage:
    python3 harness/run_eval.py evals/<skill> --arm objective-only
    python3 harness/run_eval.py evals/<skill> --arm both [--registry NAME=PATH ...]
        [--roster PATH] [--no-judge]
    python3 harness/run_eval.py evals/guidance/<id> --arm both [--guidance PATH]
    python3 harness/run_eval.py evals/<skill> --arm both [--fixture NAME]
        [--trials N]

`evals/<skill>` is either one flat fixture (`evals/<skill>/fixture.yaml`) or
a skill directory of nested ones (`evals/<skill>/<name>/fixture.yaml`, each
with its own `seed/`), never both. Named as a skill directory, every nested
fixture runs, or the one `--fixture NAME` selects; a nested fixture can also
be named by its own directory. `--trials N` (default 1) runs each arm N times
and writes the aggregate beside the per-trial summaries — see "Fixture layout"
and "Trials" below (#66).

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
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from cli_json import (bounded_tool_trace, failed_run_detail,  # noqa: E402
                      normalize_cli_result, secret_values, tool_events)
import guidance  # noqa: E402
import guidance_violations  # noqa: E402
from scorers import judge, objective  # noqa: E402
import seed_prep  # noqa: E402
import answer_leak  # noqa: E402


FIXTURE_FILE = "fixture.yaml"
SEED_DIR = "seed"

# The run directory's name: UTC, second resolution, sortable as text.
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
_TIMESTAMP_RE = re.compile(r"\d{8}T\d{6}Z")


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
    path = eval_dir / FIXTURE_FILE
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


def validate_followups(fixture: dict, fixture_path: Path) -> None:
    """`followups:` is absent, null, or a non-empty list of non-blank
    strings, checked once at load like every other key the harness reads.

    Each entry is sent as one further user turn after the prompt (see
    `run_agent`). Anything else would reach `claude -p` as a stringified
    list or an empty prompt, so it is a named configuration error (rc 2)
    instead.
    """
    value = fixture.get("followups") if isinstance(fixture, dict) else None
    if value is None:
        return
    if (not isinstance(value, list) or not value
            or not all(isinstance(item, str) and item.strip() for item in value)):
        raise guidance.GuidanceError(
            f"{fixture_path}: `followups:` must be a non-empty list of "
            f"non-blank strings (or absent), got {type(value).__name__} "
            f"{value!r}. Each entry is one further user turn sent with "
            "`--resume` after the prompt, identically in both arms.")


def validate_effort(fixture: dict, fixture_path: Path) -> None:
    """`effort:` is absent, null, or one of guidance.EFFORT_LEVELS, checked
    once at load. Anything else would reach `claude --effort` and fail as the
    agent's error, so it is a named configuration error (rc 2) instead."""
    value = fixture.get("effort") if isinstance(fixture, dict) else None
    try:
        guidance.check_effort(value)
    except guidance.GuidanceError as exc:
        raise guidance.GuidanceError(f"{fixture_path}: `effort:` {exc}") from None


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
    record of registry name/URL/layout, kept in step by hand with adam-agentskills'
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
    pre-#63 single-path form and is taken as the adam-agentskills entry, so
    the legacy invocation (`--registry ../adam-agentskills`) keeps working
    unchanged. An empty PATH (`--registry adam-agentskills=`, or a bare empty
    string) is rejected here rather than silently resolving to the current
    directory.
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
                    "bare PATH (legacy, taken as the adam-agentskills entry)")
            key = "adam-agentskills"
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
    bare entry (no "=") is taken as the adam-agentskills entry too, the same
    as the --registry flag's legacy bare-PATH form (see _parse_registry_flags)
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
            key = "adam-agentskills"
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
    means adam-agentskills) merged BY NAME with $SKILLS_EVALS_REGISTRIES (same
    shape; a flag wins over an env entry naming the same registry, but an env
    entry for a DIFFERENT registry still applies even when a flag is also
    given), then `agentskills_dir` for the adam-agentskills entry specifically
    (the harness's pre-#63 override — callers pass $AGENTSKILLS_DIR, whose
    name outlived the agentskills -> adam-agentskills rename since renaming a
    public env var is out of scope), then a sibling-directory default
    `../<name>` next to `base_dir` — the same convention adam-agentskills'
    own skills_registries.yml uses for the registries it doesn't live in.

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
        elif name == "adam-agentskills" and agentskills_dir:
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
    most of registries.yml (e.g. adam-agentskills-private) is never checked out
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
#: `roster/latest.json` on `persistent/eval-results` never had.
TRUSTED_ROSTER = Path(__file__).resolve().parent.parent / "evals" / "roster.yml"


def _resolve_roster(cli_value: Path | None) -> Path:
    """Model roster: --roster, else $EVAL_ROSTER, else the COMMITTED file.

    THE DEFAULT USED TO BE `roster/latest.json`, materialised by CI from the
    `persistent/eval-results` branch and pointed at by `$EVAL_ROSTER` — a branch other
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
    # persistent/eval-results branch.
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
# which `.github/workflows/eval.yml` pushes to the public `persistent/eval-results`
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
                   # nothing here redacts it before raw.json is written, so
                   # eval.yml leaves raw.json out of its artifacts (#289).
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
    # `deps:` first, so a `setup:` command can use what it installed.
    deps_error = seed_prep.install_deps(
        workspace, fixture, agent_env(workspace, fixture.get("env")), timeout)
    if deps_error is not None:
        return deps_error
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
    optional env (the fixture's `env:` mapping, see agent_env), optional
    followups (the fixture's `followups:` list, see ADR 0009), optional
    permission_mode (guidance.PERMISSION_MODES; default
    guidance.DEFAULT_PERMISSION_MODE, `auto`), optional effort
    (guidance.EFFORT_LEVELS; None passes no `--effort`, the CLI's default).

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
    # Checked at the sink too, before anything is installed or spawned: the
    # value becomes an argv element, and an unknown one is a configuration
    # error (GuidanceError, rc 2 through main), never a CLI failure scored as
    # the agent's.
    permission_mode = guidance.check_permission_mode(
        arm.get("permission_mode", guidance.DEFAULT_PERMISSION_MODE))
    effort = guidance.check_effort(arm.get("effort"))
    if arm["name"] == "with_skill":
        skill = arm["skill"]
        try:
            _validate_skill_name(skill)
        except ValueError as exc:
            return {"error": "invalid_skill_name", "detail": str(exc)}
        registry = arm["registry"]
        # Registry layouts vary (adam-agentskills' plugins/<bundle>/skills/<skill>/,
        # cms-platform's flat skills/<skill>/, adamdaniel.ai's
        # .claude/skills/<skill>/ — see harness/registries.yml). `layout`
        # carries the glob for the registry under test, defaulting to
        # adam-agentskills' shape for callers that predate #63. Globs for the
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
            # public persistent/eval-results branch (item 6, #129 review round 4 — the
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
            # persistent/eval-results branch.
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
    # `--verbose` makes `--output-format json` print the whole message array
    # (every turn's `type: result`), not only the LAST result. An agent that
    # starts a background subagent answers, then answers again when the
    # subagent reports; without the flag the first answer is dropped and the
    # scorer sees only the follow-up text (CLI 2.1.289, probed). The flag is
    # also the CLI's own config override, so the output shape no longer
    # depends on the machine's verbose setting. `normalize_cli_result`
    # accepts both shapes.
    cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p", prompt,
           "--output-format", "json", "--verbose",
           # One `--permission-mode` flag, never alongside
           # `--dangerously-skip-permissions` (guidance.PERMISSION_MODES).
           "--permission-mode", permission_mode,
           "--setting-sources", arm.get("setting_sources", "project"),
           # The account's claude.ai MCP connectors (mail, drive, GitHub)
           # load even under `--setting-sources project` (CLI 2.1.289,
           # measured); strict means only `--mcp-config` servers, of which
           # the harness passes none.
           "--strict-mcp-config"]
    # No transcript under the real HOME for a one-turn arm. A follow-up turn
    # `--resume`s the session, and a non-persisted session cannot be resumed
    # ("No conversation found", measured), so a multi-turn arm persists and
    # `_archive_session_dir` moves what it wrote out of the profile.
    if not arm.get("followups"):
        cmd.append("--no-session-persistence")
    if arm.get("model"):
        cmd += ["--model", arm["model"]]
    # After the prompt like every flag, so a follow-up turn, which reuses
    # this command with only the prompt replaced, keeps it.
    if effort is not None:
        cmd += ["--effort", effort]
    # Auto-memory off, applied last (guidance.CLI_FORCED_ENV): a skill arm
    # runs under the real HOME, so its memory would land in the operator's
    # profile.
    env = guidance.cli_child_env(arm.get("env_override")
                                 or agent_env(workspace, arm.get("env")))

    # `followups:` (ADR 0009): each entry is one more user turn in the SAME
    # session and workspace — the first call's flags plus `--resume
    # <session_id>`, the text in the prompt's place. Every turn gets the
    # whole `timeout`. The first turn's error details carry no label, so a
    # fixture without `followups:` behaves exactly as before.
    texts = [prompt, *(arm.get("followups") or [])]
    projects = _session_projects_dir(env)
    session_dir = projects / _munged_project_name(workspace) if projects else None
    preexisting = session_dir is not None and os.path.lexists(session_dir)
    # Every call's tool events (#89), for `transcripts/tool_trace.json`. The
    # scorers never see them: they are attached to the returned dict under
    # `tool_trace` only, beside `raw`. Every attempted CLI call gets a slot,
    # even when its evidence is unavailable or it observed no tool calls.
    secrets = secret_values(env, dict(os.environ))
    calls: list[list[dict]] = []
    trace_complete = True

    def traced(answer: dict) -> dict:
        if calls:
            answer["tool_trace"] = bounded_tool_trace(calls, complete=trace_complete)
        return answer

    # The finally covers every return below: a multi-turn arm's transcript
    # leaves the profile whether the arm succeeded or not.
    try:
        turns: list[dict] = []
        for index, text in enumerate(texts):
            label = f"follow-up {index} of {len(texts) - 1}: " if index else ""
            turn_cmd = cmd
            if index:
                session_id = turns[-1].get("session_id")
                if not isinstance(session_id, str) or not session_id:
                    return traced({"error": "invalid_json",
                                   "detail": f"{label}the previous result has no "
                                             "session_id to resume"})
                turn_cmd = [*cmd[:2], text, *cmd[3:], "--resume", session_id]
            calls.append([])
            try:
                result = subprocess.run(turn_cmd, cwd=workspace, capture_output=True,
                                        text=True, timeout=timeout, env=env)
            except subprocess.TimeoutExpired:
                trace_complete = False
                return traced({"error": "timeout",
                               "detail": f"{label}agent timed out after {timeout}s"})

            if result.returncode != 0:
                try:
                    decoded = json.loads(result.stdout)
                    calls[-1] = tool_events(decoded, secrets)
                    normalize_cli_result(decoded)
                    trace_complete = trace_complete and isinstance(decoded, list)
                except ValueError:
                    trace_complete = False
                return traced({"error": "nonzero_exit",
                               "detail": label + failed_run_detail(result.stdout,
                                                                   result.stderr),
                               "returncode": result.returncode})

            try:
                decoded = json.loads(result.stdout)
                calls[-1] = tool_events(decoded, secrets)
                data = normalize_cli_result(decoded)
                trace_complete = trace_complete and isinstance(decoded, list)
            except json.JSONDecodeError as e:
                trace_complete = False
                # Shape only. The array form starts with the `system/init`
                # message (cwd, tool and connector names), and this detail
                # reaches summary.json, so no slice of stdout is echoed.
                return traced({"error": "invalid_json",
                               "detail": f"{label}stdout is not valid JSON ({e.msg} at "
                                         f"character {e.pos} of {len(result.stdout)})"})
            except ValueError as e:
                trace_complete = False
                return traced({"error": "invalid_json", "detail": f"{label}{e}"})

            if data.get("is_error"):
                detail = data.get("result", "")
                return traced({"error": "agent_error",
                               "detail": f"{label}{detail}" if label else detail,
                               "raw": data})
            turns.append(data)

        if len(turns) > 1:
            return traced(_combine_turns(turns, texts[1:]))
        data = turns[0]
        return traced({
            "transcript": data.get("result"),
            "usage": data.get("usage"),
            "cost_usd": data.get("total_cost_usd"),
            "num_turns": data.get("num_turns"),
            "duration_ms": data.get("duration_ms"),
            "raw": data,
        })
    finally:
        if session_dir is not None and not preexisting:
            _archive_session_dir(session_dir, arm.get("session_scratch"))


# The CLI's own project-directory name (2.1.289, read from its bundle and
# matched by the `memory_paths` its init event reports): every character
# outside [A-Za-z0-9] becomes "-". Past 200 characters the CLI truncates and
# appends a hash of its own, which this harness does not reproduce, so a name
# that long is never touched.
_PROJECT_NAME_MAX = 200


def _munged_project_name(workspace: Path) -> str:
    """The `~/.claude/projects/<name>` the CLI keys a session started in
    `workspace` by. The real path: the child's cwd resolves symlinks."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(workspace))


def _session_projects_dir(env: dict) -> Path | None:
    """Where the child's CLI writes session transcripts: `$CLAUDE_CONFIG_DIR/
    projects`, else `$HOME/.claude/projects`, read from the CHILD's env."""
    config = env.get("CLAUDE_CONFIG_DIR")
    if config:
        return Path(config) / "projects"
    home = env.get("HOME")
    return Path(home) / ".claude" / "projects" if home else None


def session_archive_dir() -> Path:
    """The harness-owned archive for transcripts a multi-turn arm had to
    persist: `$XDG_STATE_HOME/skills-evals/sessions`, else
    `~/.local/state/skills-evals/sessions`. Outside every checkout, so a
    transcript (host paths, fixture data) never rides into a results tree."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "skills-evals" / "sessions"


def _archive_session_dir(session_dir: Path, scratch=None) -> Path | None:
    """Move the project directory THIS arm's CLI created out of the profile.

    The caller only asks for a directory that did not exist before the arm's
    first turn, so nothing another session wrote is touched. Left alone: a
    name past the CLI's truncation length (the CLI would have written a
    different, hashed name), a symlink or non-directory, and a directory
    inside the arm's own `scratch` (the guidance arm's scratch config dir,
    which the arm removes with the rest of its scratch). Returns where it
    went, else None; an OSError is swallowed — housekeeping never fails an
    arm."""
    if len(session_dir.name) > _PROJECT_NAME_MAX:
        return None
    if session_dir.is_symlink() or not session_dir.is_dir():
        return None
    if scratch and Path(os.path.realpath(session_dir)).is_relative_to(
            os.path.realpath(scratch)):
        return None
    try:
        archive = session_archive_dir()
        archive.mkdir(parents=True, exist_ok=True)
        slot = Path(tempfile.mkdtemp(prefix=f"{session_dir.name}.", dir=archive))
        dest = slot / session_dir.name
        shutil.move(str(session_dir), str(dest))
        return dest
    except OSError:
        return None


def _sum_usage(total, part):
    """Add one turn's usage-shaped value into the running total: numbers
    add, mappings merge key by key, anything else takes the latest value."""
    def is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if is_number(total) and is_number(part):
        return total + part
    if isinstance(total, dict) and isinstance(part, dict):
        merged = dict(total)
        for key, value in part.items():
            merged[key] = _sum_usage(merged[key], value) if key in merged else value
        return merged
    return part if part is not None else total


# What separates one turn's reply from the next in a multi-turn transcript.
# The judge reads the whole conversation, so it sees the follow-up the agent
# was answering, not two replies run together.
FOLLOWUP_MARKER = "\n\n--- user follow-up ---\n{text}\n--- agent reply ---\n"


def _combine_turns(turns: list[dict], followups: list[str]) -> dict:
    """`run_agent`'s success dict for a session of several CLI calls.

    The transcript is every reply in order with each follow-up between them.
    A resumed call's `total_cost_usd` and `modelUsage` are already CUMULATIVE
    for the session (measured on Claude Code 2.1.289: the resumed result's
    cost and per-model tokens equal the sums over both calls), so those two
    come from the LAST call; summing them would count the first call twice.
    Its `usage`, `num_turns` and `duration_ms` cover that call alone, so
    those are summed. `raw` is the last call's result object (so its
    `result` is the final reply) with those totals, and every call's own
    result object under `turns`.
    """
    transcript = turns[0].get("result") or ""
    for text, data in zip(followups, turns[1:]):
        transcript += FOLLOWUP_MARKER.format(text=text) + (data.get("result") or "")
    totals = {key: turns[-1].get(key)
              for key in ("total_cost_usd", "modelUsage")}
    for key in ("usage", "num_turns", "duration_ms"):
        value = None
        for turn in turns:
            if turn.get(key) is not None:
                value = turn[key] if value is None else _sum_usage(value, turn[key])
        totals[key] = value
    return {
        "transcript": transcript,
        "usage": totals["usage"],
        "cost_usd": totals["total_cost_usd"],
        "num_turns": totals["num_turns"],
        "duration_ms": totals["duration_ms"],
        "raw": {**turns[-1], **totals, "turns": turns},
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
            # `strip_agent_context:` before setup; its guard after, on the
            # workspace exactly as the agent gets it (harness/seed_prep.py).
            seed_prep.prepare_seed(workspace, fixture)
            setup_result = (run_setup(workspace, fixture)
                            or seed_prep.seed_guard(workspace, fixture))
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


# ---------------------------------------------------------------------------
# What ran (#202). The owner's decision of 2026-09-27 unpinned the harness —
# CI now always installs the npm latest (#203, 2026-09-28) — so every run
# records the version it actually got, and the model(s) that actually served
# each arm, rather than leaving either to a pin or a flag.
# ---------------------------------------------------------------------------

HARNESS_NAME = "claude-code"


def _permission_mode(args: argparse.Namespace) -> str:
    """The run's `--permission-mode`. A caller that built its own Namespace
    without one gets the default — the mode run_agent and the judge then
    launch with, so the summary records what actually ran."""
    return getattr(args, "permission_mode", None) or guidance.DEFAULT_PERMISSION_MODE


def _effort(args: argparse.Namespace, fixture: dict) -> str | None:
    """The agent arms' `--effort`: the run's `--effort` > the fixture's
    `effort:` > None, the CLI's own default (no flag passed). The same
    precedence as `--model` over `model:`."""
    return getattr(args, "effort", None) or (
        fixture.get("effort") if isinstance(fixture, dict) else None)

# The bound on the `--version` probe. Named rather than inlined so the sink
# check and the `timeout=` argument are provably the same value.
VERSION_TIMEOUT_S = 30
#: A version string longer than this is cut: it is the CLI's own output,
#: recorded into a summary.json the public persistent/eval-results branch carries.
VERSION_MAX_CHARS = 64
#: Every character a version string needs — the same set the workflows'
#: install step keeps (`${version//[^A-Za-z0-9._() -]/}`). Anything else is
#: dropped: the version lands in a markdown code span in report.md, where a
#: backtick or a link would be rendered, not recorded.
_VERSION_JUNK = re.compile(r"[^A-Za-z0-9._() -]")
#: `models_used` validation: model ids are short strings, and a result is
#: served by a handful of them. Anything else is junk and is ignored.
MODEL_ID_MAX_CHARS = 128
MODELS_USED_MAX = 16


def claude_version() -> str | None:
    """The first line of `<CLAUDE_BIN or claude> --version`, reduced to
    version characters, stripped, capped at VERSION_MAX_CHARS — or None, with
    a one-line warning on stderr naming only an exit status or an exception
    class, never the CLI's output.

    Never raises for the CLI's sake: a run whose version could not be read
    still runs and records `null`. (The timeout predicate raises before the
    spawn, like every sink's, and that is a configuration error.)
    """
    guidance.check_timeout(VERSION_TIMEOUT_S, "run_eval.claude_version(timeout=)",
                           guidance.SINK_TIMEOUT_REMEDY)
    why = None
    try:
        # `subprocess.run(timeout=)` already does what the workflows' `timeout
        # -k 10 60` does (#203 round 1): on expiry it SIGKILLs the child
        # (`process.kill()` in its TimeoutExpired handler) and reaps it, so a
        # CLI that ignores SIGTERM cannot outlive the probe.
        result = subprocess.run(
            [os.environ.get("CLAUDE_BIN", "claude"), "--version"],
            capture_output=True, text=True, timeout=VERSION_TIMEOUT_S)
        if result.returncode != 0:
            why = f"exit {result.returncode}"
        else:
            # The whole stdout, first line taken here: no shell pipe, so no
            # `head` closing the pipe under the CLI.
            lines = (result.stdout or "").splitlines()
            first = _VERSION_JUNK.sub("", lines[0]) if lines else ""
            version = first.strip()[:VERSION_MAX_CHARS].strip()
            if version:
                return version
            why = "no version in its output"
    except Exception as exc:  # noqa: BLE001 — record null, never crash the run
        why = type(exc).__name__
    print(f"warning: harness: could not read the Claude Code version ({why}); "
          "recording null", file=sys.stderr)
    return None


def models_used(*results) -> list[str]:
    """The sorted model ids that served one or more CLI results.

    Each result is the CLI's `--output-format json` object; its `modelUsage`
    is keyed by the model id that served the turns. Only string keys of
    1..MODEL_ID_MAX_CHARS printable characters count — no whitespace, and no
    backtick or pipe, which would break report.md's line — and at most
    MODELS_USED_MAX are kept; an absent or malformed `modelUsage`
    contributes nothing.
    """
    found: set[str] = set()
    for result in results:
        usage = result.get("modelUsage") if isinstance(result, dict) else None
        if not isinstance(usage, dict):
            continue
        found.update(key for key in usage if _is_model_id(key))
    return sorted(found)[:MODELS_USED_MAX]


#: The per-model counts `model_tokens` keeps from the CLI's `modelUsage`, as
#: (summary name, `modelUsage` key). The names are `usage`'s own, so a
#: per-model figure reads like the arm's total. Its other keys (thinking
#: tokens, web searches, cost, context window) are not kept; its
#: `canonicalModel` is, as `canonical_model`.
MODEL_TOKEN_FIELDS = (
    ("input_tokens", "inputTokens"),
    ("output_tokens", "outputTokens"),
    ("cache_read_input_tokens", "cacheReadInputTokens"),
    ("cache_creation_input_tokens", "cacheCreationInputTokens"),
)
#: The largest token count kept, per count and per total. A larger figure
#: is junk, not a measurement (a trial's whole budget is far below it), and
#: a sum of figures near the float range would overflow to Infinity, which
#: is not JSON. Past it a count or total is null.
MAX_TOKEN_COUNT = 10 ** 12
#: `cross_model.flagged` is set when more than this fraction of a trial's
#: tokens (the four MODEL_TOKEN_FIELDS, summed over every model) were spent
#: on models other than the arm's own `--model`: the trial's work was done
#: MOSTLY by another model (a subagent's), so its scores describe that model
#: at least as much as the arm's. A half leaves room for the CLI's own small
#: calls on other models (compaction, helpers) without flagging. A flag
#: only: no score, gate or threshold reads it.
CROSS_MODEL_SHARE_THRESHOLD = 0.5
#: A canonical model id, after `canonical_model_id` has removed the
#: spellings around it.
_CANONICAL_ID = re.compile(r"claude-[a-z0-9]+(?:[.-][a-z0-9]+)*")
#: The spellings `canonical_model_id` removes, in this order: a bracketed
#: variant suffix (`[1m]`), a Bedrock `<region>.anthropic.` prefix and
#: `-v<n>:<n>` suffix, a Vertex `@<date>` suffix, and a `-YYYYMMDD` date
#: suffix (a dated snapshot is the same model).
_ID_SUFFIX_VARIANT = re.compile(r"\[[^\]]*\]$")
_ID_PREFIX_BEDROCK = re.compile(r"^(?:[a-z]{2,4}\.)?anthropic\.")
_ID_SUFFIX_BEDROCK = re.compile(r"-v\d+(?::\d+)?$")
_ID_SUFFIX_DATE = re.compile(r"(?:-|@)\d{8}$")


def canonical_model_id(model) -> str | None:
    """The canonical id `model` names, or None when it is not a full model
    id: an alias such as `sonnet` cannot be resolved here, because the
    alias table lives in the CLI and the harness keeps no copy of it (the
    roster's probe, scripts/probe_model_defaults.py, resolves aliases per
    CI run and commits none). Unknown, never a guess."""
    if not isinstance(model, str):
        return None
    text = _ID_SUFFIX_VARIANT.sub("", model.strip())
    text = _ID_PREFIX_BEDROCK.sub("", text)
    text = _ID_SUFFIX_BEDROCK.sub("", text)
    text = _ID_SUFFIX_DATE.sub("", text)
    return text if _CANONICAL_ID.fullmatch(text) else None


def _token_count(value):
    return value if (_is_number(value) and 0 <= value <= MAX_TOKEN_COUNT) else None


def model_usage(result) -> dict:
    """The per-model token accounting of one CLI result, from `modelUsage`:
    `{"tokens", "dropped", "complete"}`.

    `tokens` is `{model id: {name: count, ..., "canonical_model": id}}` for
    every MODEL_TOKEN_FIELDS name, model ids sorted and validated as
    `models_used()` validates them, at most MODELS_USED_MAX. A count the CLI
    did not report, or reported as anything but a finite number from 0 to
    MAX_TOKEN_COUNT, is null: missing, never zero. `canonical_model` is the
    entry's own `canonicalModel` when it is a model id, else null.

    `dropped` counts the entries left out: an invalid model id, an entry
    that is not an object, or one past MODELS_USED_MAX. `complete` is true
    only for a `modelUsage` object with at least one entry and none dropped;
    an incomplete accounting is never read as a whole.

    The CLI's `modelUsage` covers "every model call made through the query
    pipeline ... main loop, Task subagents, sidechains, and internal calls
    such as compaction" (the SDK schema text bundled in Claude Code 2.1.292),
    so a subagent on another model appears under its own key. It is
    cumulative per session, so a multi-turn arm's last result already holds
    every turn (`_combine_turns`).
    """
    usage = result.get("modelUsage") if isinstance(result, dict) else None
    if not isinstance(usage, dict):
        return {"tokens": {}, "dropped": 0, "complete": False}
    out, dropped = {}, 0
    for key in sorted(usage, key=str):
        entry = usage[key]
        if not _is_model_id(key) or not isinstance(entry, dict) \
                or len(out) == MODELS_USED_MAX:
            dropped += 1
            continue
        out[key] = {name: _token_count(entry.get(source))
                    for name, source in MODEL_TOKEN_FIELDS}
        canonical = entry.get("canonicalModel")
        out[key]["canonical_model"] = canonical if _is_model_id(canonical) else None
    return {"tokens": out, "dropped": dropped,
            "complete": bool(out) and dropped == 0}


def model_tokens(result) -> dict:
    """`model_usage(result)["tokens"]`."""
    return model_usage(result)["tokens"]


def _entry_total(counts) -> float | None:
    """The four counts of one `model_tokens` entry summed, or None when any
    is missing or invalid or the sum is past MAX_TOKEN_COUNT."""
    if not isinstance(counts, dict):
        return None
    values = [_token_count(counts.get(name)) for name, _ in MODEL_TOKEN_FIELDS]
    if any(v is None for v in values):
        return None
    return _token_count(sum(values))


def model_usage_total(tokens: dict, complete: bool) -> float | None:
    """Every model's four counts summed: the improvement loop's tokens
    (ADR 0005, 2026-10-07 addendum). None when the accounting is incomplete,
    empty, any count is missing, or the total is past MAX_TOKEN_COUNT."""
    if not complete or not isinstance(tokens, dict) or not tokens:
        return None
    totals = [_entry_total(counts) for counts in tokens.values()]
    if any(t is None for t in totals):
        return None
    return _token_count(sum(totals))


def _cross_model_parts(tokens: dict, own: str | None,
                       complete: bool = True) -> tuple | None:
    """(tokens on other models, all tokens) of one `model_tokens` block, or
    None when it cannot be told: an incomplete accounting, an own model that
    is not a full model id, an entry whose model cannot be resolved, no
    tokens, or any count missing (a partial sum would misstate the share).
    Models are compared by `canonical_model_id`, an entry's
    `canonical_model` first."""
    own_id = canonical_model_id(own)
    if not complete or own_id is None or not isinstance(tokens, dict) \
            or not tokens:
        return None
    other = total = 0
    for model, counts in tokens.items():
        entry_total = _entry_total(counts)
        entry_id = canonical_model_id(counts.get("canonical_model") or model) \
            if isinstance(counts, dict) else None
        if entry_total is None or entry_id is None:
            return None
        total += entry_total
        if entry_id != own_id:
            other += entry_total
    if _token_count(total) is None or total <= 0:
        return None
    return other, total


def cross_model(tokens: dict, own: str | None, *, complete: bool = True,
                dropped: int = 0) -> dict:
    """A trial summary's `cross_model` block: the arm's own `model` (null when
    the arm passed no `--model`) and its `canonical_model`
    (`canonical_model_id`, null when it cannot be resolved), whether the
    accounting is `complete` and how many entries were `dropped`,
    `other_share` (the fraction of the tokens spent on other models), the
    `threshold`, and `flagged` (`other_share` above it). `other_share` and
    `flagged` are null, unknown, whenever the share cannot be told."""
    parts = _cross_model_parts(tokens, own, complete)
    share = parts[0] / parts[1] if parts else None
    return {"model": own, "canonical_model": canonical_model_id(own),
            "complete": bool(complete), "dropped": dropped,
            "other_share": share, "threshold": CROSS_MODEL_SHARE_THRESHOLD,
            "flagged": None if parts is None else _over_threshold(*parts)}


def _over_threshold(other, total) -> bool:
    """`other / total` above CROSS_MODEL_SHARE_THRESHOLD, compared exactly
    (rationals, not floats): a float share can round onto the threshold."""
    return Fraction(other) > Fraction(CROSS_MODEL_SHARE_THRESHOLD) * Fraction(total)


def _is_model_id(key) -> bool:
    return (isinstance(key, str) and 0 < len(key) <= MODEL_ID_MAX_CHARS
            and key.isprintable() and not any(c.isspace() for c in key)
            and "`" not in key and "|" not in key)


def _harness_line(harness_version: str | None, arm_summaries: list[dict]) -> str:
    """report.md's one line naming the harness and each arm's models."""
    models = "; ".join(
        f"{s['arm']}={', '.join(s.get('models_used') or []) or 'none recorded'}"
        for s in arm_summaries)
    version = f"`{harness_version}`" if harness_version else "version unknown"
    return f"- Harness: Claude Code {version}; models used: {models}"


def _write_summary(results_dir: Path, skill: str | None, arm_name: str,
                   timestamp: str, error: dict | None, agent: dict | None,
                   objective_checks: list | None, judge_result: dict | None,
                   raw: dict | None, key: str | None = None,
                   extra: dict | None = None, *,
                   harness_version: str | None = None,
                   permission_mode: str | None = None,
                   models: list | None = None,
                   tool_trace: dict | None = None,
                   judge_models: list | None = None,
                   arm_dir: Path | None = None,
                   effort: str | None = None,
                   agent_usage: dict | None = None,
                   agent_model: str | None = None) -> None:
    """One arm's summary.json (+ raw transcript).

    `key` is the results-tree path for this subject — a skill's own name, or
    `guidance/<section id>` — and defaults to `skill`, which is what every
    skill arm has always written. `extra` carries the guidance subject's own
    fields (subject/section/mode/bytes/delivery/guard).

    Every summary, error paths included, records `harness` (the CLI version
    read once per run, or null, plus `permission_mode`, the mode every agent
    and judge call of the run was launched with) and `models_used` /
    `judge_models_used`
    (`models_used()` of the agent's and the judge's results; empty when that
    call never ran) — #202. The `harness` block also records `effort`, the
    `--effort` level every agent call of the arm was launched with, or null
    when none was passed (the CLI's default).

    `model_tokens` (`model_usage()` of the agent's result, passed as
    `agent_usage`; `{}` when that call never produced one) and `cross_model`
    (`cross_model()` of it and `agent_model`, the arm's own `--model`) are in
    every summary too. An aggregate summary passes `sum_model_usage()` of
    its trials.

    `arm_dir` (#66) names the directory to write into when it is not the
    default `<results>/<key or skill>/<timestamp>/<arm>/`: a nested fixture's
    arm directory, or one trial's `trial-<k>/` inside an arm directory. Left
    as None, the path is the one every caller before #66 got.
    """
    if arm_dir is None:
        arm_dir = results_dir / (key or skill) / timestamp / arm_name
    arm_dir.mkdir(parents=True, exist_ok=True)
    usage = agent_usage or {"tokens": {}, "dropped": 0, "complete": False}
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
        "harness": {"name": HARNESS_NAME, "version": harness_version,
                    "permission_mode": permission_mode, "effort": effort},
        "models_used": list(models or []),
        "judge_models_used": list(judge_models or []),
        "model_tokens": dict(usage["tokens"]),
        "cross_model": cross_model(usage["tokens"], agent_model,
                                   complete=usage["complete"],
                                   dropped=usage["dropped"]),
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
    if tool_trace is not None:
        transcripts_dir = arm_dir / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        with open(transcripts_dir / TOOL_TRACE_NAME, "w", encoding="utf-8") as f:
            json.dump(tool_trace, f, indent=2)


# How much of an error detail one report table cell carries. The full
# detail is always in summary.json; this is the reader's version.
_REPORT_CELL_CHARS = 200


def _render_report(skill: str, prompt: str, timestamp: str, arm_summaries: list[dict],
                   harness_version: str | None = None) -> str:
    lines = [
        f"# Eval report: {skill}",
        "",
        f"- Prompt: {prompt.strip()}",
        f"- Timestamp: {timestamp}",
        _harness_line(harness_version, arm_summaries),
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

        err_str = _error_cell(s.get("error"))

        lines.append(f"| {s['arm']} | {objective_str} | {judge_str} | {cost_str} | "
                     f"{turns_str} | {duration_str} | {err_str} |")
    lines += guidance_violations.render([
        {"arm": s["arm"], "stats": {"aggregate": {
            "guidance_violations": guidance_violations.aggregate([s])}}}
        for s in arm_summaries])
    return "\n".join(lines) + "\n"


def _error_cell(err: dict | None) -> str:
    """One error, as report text that cannot break a table or a list.

    Error details can carry multiline stderr or `|`s — keep the table
    intact. The cut is marked: an error cut off mid-sentence at exactly 200
    characters reads as the whole error, and the reader has no way to tell
    there is more of it in summary.json, which keeps the detail in full.
    """
    if not err:
        return ""
    err_str = " ".join(
        f"{err['type']}: {err['detail']}".split()).replace("|", "\\|")
    if len(err_str) > _REPORT_CELL_CHARS:
        err_str = err_str[:_REPORT_CELL_CHARS - 1] + "…"
    return err_str


# ---------------------------------------------------------------------------
# Trials (#66). One trial is one `_run_arm` call: a fresh workspace, a fresh
# agent call, the judge on that trial alone. The CLI has no temperature flag,
# so repeating the arm is the only way to see run-to-run spread (DESIGN.md,
# "Harness-wide rules").
#
# ON DISK, by the number of trials asked for:
#
#   --trials 1 (the default)   <arm>/summary.json            that trial, plus `n: 1`
#                              <arm>/transcripts/raw.json
#   --trials N, N > 1          <arm>/trial-<k>/summary.json  each trial, plus `trial: k`
#                              <arm>/trial-<k>/transcripts/raw.json
#                              <arm>/summary.json            the aggregate
#
# At N = 1 the arm summary IS the trial, field for field what this harness
# wrote before trials existed, with `n: 1` appended; no `trial-1/` copy of it
# is written. At N > 1 the arm summary describes no single trial, so the four
# single-trial fields carry what stays true of the whole arm: `error` is null
# only when NO trial errored, and `agent`, `objective_checks` and `judge` are
# null — the numbers are under `aggregate`. A reader of the single-trial
# shape therefore finds no check list and no judge result there, rather than
# one trial's standing in for the arm.
# ---------------------------------------------------------------------------

TRIAL_DIR_PREFIX = "trial-"

# A typo guard, not a statistical claim: every trial is a paid agent call and
# a paid judge call, per arm, per fixture. DESIGN.md asks for N >= 3.
MAX_TRIALS = 20


def _is_number(value) -> bool:
    """A finite real number, and not a bool. A judge's `overall`, a
    dimension's score and a cost are all read off JSON a model or a CLI
    produced; anything else there is left out of the statistics rather than
    averaged. `math.isfinite` raises on an int too large for a float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _stats(values: list) -> dict | None:
    """`n`, `mean`, `min`, `max` and `sum` of a list of numbers, or None for
    an empty one — there is no mean of nothing, and a 0.0 there would read as
    a score."""
    if not values:
        return None
    total = sum(values)
    return {"n": len(values), "mean": total / len(values),
            "min": min(values), "max": max(values), "sum": total}


# The per-trial efficiency figures the harness records, as (name, path into
# the trial summary's `agent` block). `usage` is the CLI's own token block; a
# CLI that omits a key leaves that trial missing from that metric.
EFFICIENCY_METRICS = (
    ("cost_usd", ("cost_usd",)),
    ("num_turns", ("num_turns",)),
    ("duration_ms", ("duration_ms",)),
    ("input_tokens", ("usage", "input_tokens")),
    ("output_tokens", ("usage", "output_tokens")),
    ("cache_creation_input_tokens", ("usage", "cache_creation_input_tokens")),
    ("cache_read_input_tokens", ("usage", "cache_read_input_tokens")),
)
# `tool_errors` is the one metric not in a summary: it is counted from the
# trial's `transcripts/tool_trace.json` (see `_trial_tool_errors`), so adding
# it to the summary's `agent` block would change every summary this harness
# writes, which the one-trial default must not do (#66).
EFFICIENCY_NAMES = (*(name for name, _ in EFFICIENCY_METRICS), "tool_errors")


def _tool_error_count(tool_trace: dict | None) -> int | None:
    """How many tool calls of one trial ended in an error, from its tool trace.

    Counted by DISTINCT tool-use id: a result repeated under one id (a replayed
    message) is one failed call. A result with no usable id is counted as it
    stands, since there is nothing to deduplicate on.

    New traces explicitly record whether every CLI call supplied complete
    evidence. Lost evidence or a size cap makes the count None, which the
    aggregate reports as missing rather than as a silent undercount. Legacy
    trials without a trace or without the completeness field retain their
    previous interpretation.
    """
    if tool_trace is None:
        return 0
    if tool_trace.get("complete") is False or tool_trace.get("omitted_events"):
        return None
    ids, unidentified = set(), 0
    for event in tool_trace.get("events") or []:
        if (isinstance(event, dict) and event.get("kind") == "tool_result"
                and event.get("is_error") is True):
            if isinstance(event.get("id"), str):
                ids.add(event["id"])
            else:
                unidentified += 1
    return len(ids) + unidentified


def _trial_tool_errors(trial_dir: Path) -> int | None:
    """`_tool_error_count` of the trace one trial wrote under `trial_dir`.
    No trace file is a trial that made no tool call; a file that cannot be
    read as a trace is unknown."""
    path = trial_dir / "transcripts" / TOOL_TRACE_NAME
    if not path.exists():
        return 0
    try:
        trace = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return _tool_error_count(trace) if isinstance(trace, dict) else None


def _metric_stats(values: list, n_trials: int) -> dict:
    """`n`, `n_missing`, `mean`, `median`, `min`, `max` and `sum` of one
    efficiency metric. `n_missing` is the trials that did not report it.
    Unlike `_stats`, an empty list still returns a block (every figure null),
    so a reader can tell "no trial reported it" from "the key is absent"."""
    if not values:
        return {"n": 0, "n_missing": n_trials, "mean": None, "median": None,
                "min": None, "max": None, "sum": None}
    total = sum(values)
    return {"n": len(values), "n_missing": n_trials - len(values),
            "mean": total / len(values), "median": statistics.median(values),
            "min": min(values), "max": max(values), "sum": total}


def efficiency_stats(trials: list[dict],
                     tool_errors: list | None = None) -> dict:
    """`_metric_stats` for every `EFFICIENCY_NAMES` entry over `trials`
    (per-trial summaries). A trial without an `agent` block, or whose value
    is absent or not a finite number, counts in `n_missing`.

    `tool_errors` is one count (or None) per trial, in trial order, from
    `_trial_tool_errors`; the summaries do not carry it. Without it every
    trial is missing for that metric. Only a trial with an `agent` block (an
    agent call that returned) can have one."""
    out = {}
    for name, path in EFFICIENCY_METRICS:
        values = []
        for trial in trials:
            value = trial.get("agent")
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
            if _is_number(value):
                values.append(value)
        out[name] = _metric_stats(values, len(trials))
    counted = [
        count for index, trial in enumerate(trials)
        if isinstance(trial.get("agent"), dict) and tool_errors is not None
        and index < len(tool_errors)
        and _is_number(count := tool_errors[index])]
    out["tool_errors"] = _metric_stats(counted, len(trials))
    return out


def efficiency_delta(with_stats: dict, without_stats: dict) -> dict:
    """Per metric, `with` minus `without` of the mean and of the median, from
    two `efficiency_stats` blocks. Negative means the `with` arm used less.
    A delta is null when either side has no value for the metric. This
    reports a difference; it does not say which metric matters or whether the
    difference is enough."""
    out = {}
    for name in EFFICIENCY_NAMES:
        a, b = with_stats.get(name) or {}, without_stats.get(name) or {}
        entry = {"with_n": a.get("n"), "without_n": b.get("n")}
        for figure in ("mean", "median"):
            x, y = a.get(figure), b.get(figure)
            entry[f"delta_{figure}"] = (
                x - y if _is_number(x) and _is_number(y) else None)
        out[name] = entry
    return out


def _trial_usage(trial: dict) -> tuple:
    """(model_tokens, complete) of one trial summary: (None, False) when it
    has none (its agent call produced no result, or the summary predates the
    field). `complete` is its `cross_model.complete`, false when absent."""
    tokens = trial.get("model_tokens") if isinstance(trial, dict) else None
    if not isinstance(tokens, dict) or not tokens:
        return None, False
    block = trial.get("cross_model")
    return tokens, isinstance(block, dict) and block.get("complete") is True


def _trial_count(tokens: dict, complete: bool, model: str, name: str):
    """One trial's `name` count for `model`: the recorded value; zero for a
    model a COMPLETE trial did not use; None (missing) for a model an
    incomplete trial does not show, since it may be the one dropped."""
    if model in tokens:
        counts = tokens[model]
        return _token_count(counts.get(name)) if isinstance(counts, dict) else None
    return 0 if complete else None


def _arm_model(trials: list[dict]) -> str | None:
    """The arm's own model as its trial summaries recorded it."""
    for trial in trials:
        block = trial.get("cross_model") if isinstance(trial, dict) else None
        if isinstance(block, dict) and isinstance(block.get("model"), str):
            return block["model"]
    return None


def _token_models(trials: list[dict]) -> tuple:
    """(the sorted model ids across the trials, at most MODELS_USED_MAX, and
    how many past that cap were left out)."""
    found = sorted({model for trial in trials
                    for model in (_trial_usage(trial)[0] or {})})
    return found[:MODELS_USED_MAX], max(0, len(found) - MODELS_USED_MAX)


def sum_model_usage(trials: list[dict]) -> dict:
    """`model_usage()`'s shape for an arm: per model and count, the sum over
    the trials that recorded `model_tokens`. A model a complete trial did not
    use adds zero; one an incomplete trial does not show makes that sum null,
    as does any missing count. `complete` only when EVERY trial recorded a
    complete accounting (one whose entries were all dropped, or that produced
    no result, did not) and no model was left out. An aggregate summary's
    `model_tokens` and `cross_model`."""
    measured = [(tokens, complete) for tokens, complete in map(_trial_usage, trials)
                if tokens is not None]
    models, cut = _token_models(trials)
    out = {}
    for model in models:
        out[model] = {}
        for name, _ in MODEL_TOKEN_FIELDS:
            values = [_trial_count(t, c, model, name) for t, c in measured]
            out[model][name] = (_token_count(sum(values))
                                if all(v is not None for v in values) else None)
        names = {t[model].get("canonical_model") for t, _ in measured
                 if isinstance(t.get(model), dict)}
        out[model]["canonical_model"] = names.pop() if len(names) == 1 else None
    dropped = cut + sum(
        trial["cross_model"]["dropped"] for trial in trials
        if isinstance(trial, dict) and isinstance(trial.get("cross_model"), dict)
        and isinstance(trial["cross_model"].get("dropped"), int)
        and not isinstance(trial["cross_model"]["dropped"], bool))
    # Every trial, not only those with tokens: a trial whose entries were all
    # dropped, or that produced no result, leaves the arm's total unknown.
    return {"tokens": out, "dropped": dropped,
            "complete": bool(trials) and not cut
            and all(_trial_usage(trial)[1] for trial in trials)}


def model_token_stats(trials: list[dict]) -> dict:
    """`_metric_stats` per model and per MODEL_TOKEN_FIELDS count, over every
    trial: a trial with no `model_tokens` is missing; one that recorded other
    models but not this one used zero of it when it was complete, and is
    missing when it was not."""
    out = {}
    for model in _token_models(trials)[0]:
        out[model] = {}
        for name, _ in MODEL_TOKEN_FIELDS:
            values = []
            for trial in trials:
                tokens, complete = _trial_usage(trial)
                if tokens is None:
                    continue
                value = _trial_count(tokens, complete, model, name)
                if value is not None:
                    values.append(value)
            out[model][name] = _metric_stats(values, len(trials))
    return out


def cross_model_stats(trials: list[dict]) -> dict:
    """An arm's `cross_model` aggregate: its own `model`, the `threshold`,
    `n` (trials whose share could be told), `n_unknown` (every other trial:
    an incomplete accounting, entries all dropped, no result, an unresolved
    model), `flagged_trials`, and `other_share` and `flagged` pooled over the
    `n` trials' tokens. Those two are null, unknown, when `n` is 0 or
    `n_unknown` is not."""
    own = _arm_model(trials)
    other = total = n = n_unknown = flagged = 0
    for trial in trials:
        tokens, complete = _trial_usage(trial)
        parts = _cross_model_parts(tokens or {}, own, complete)
        if parts is None:
            n_unknown += 1
            continue
        n += 1
        other, total = other + parts[0], total + parts[1]
        flagged += _over_threshold(*parts)
    known = n and not n_unknown
    return {"model": own, "threshold": CROSS_MODEL_SHARE_THRESHOLD, "n": n,
            "n_unknown": n_unknown, "flagged_trials": flagged,
            "other_share": other / total if known else None,
            "flagged": _over_threshold(other, total) if known else None}


def aggregate_trials(trials: list[dict],
                     tool_errors: list | None = None) -> dict:
    """One arm's trial summaries, reduced to the fields an aggregate carries.

    `trials` is the list of per-trial summaries in trial order (trial 1
    first), each in the shape `_write_summary` writes. `tool_errors` is the
    optional per-trial tool-error count `efficiency_stats` takes.

    EVERY TRIAL COUNTS IN `n`. A trial whose `error` is set is counted in
    `errors` and listed in `trial_errors`; it is in no score mean or pass
    rate. `scored` is `n - errors`, the number of trials the objective
    figures are over. Each statistic also carries its own `n`, because the
    three are not always over the same trials: a scored trial whose judge
    call failed is in the objective and cost figures and not in the judge's.

    The `aggregate` block:

      * `objective` — null when no trial was scored. Otherwise its own `n`
        (the scored trials), `passed` and `total` (integer counts summed
        over them), `mean_passed` and `mean_total` (those counts divided by
        that `n`), and `checks`: one entry per check id in first-seen order,
        with how many times it was scored (`n` — once per scored trial,
        unless the fixture uses one id for several checks), how many of
        those passed, and `pass_rate`.
      * `judge` — null when no scored trial has a judge result (`--no-judge`,
        or nothing was scored). Otherwise `n` (results with a numeric
        `overall`), `errors` (results without one: the judge call failed or
        answered something unusable), `overall` (`_stats`, or null when
        `n` is 0) and `dimensions`: `_stats` per dimension name, matched
        trimmed and casefolded, over the results counted in `n`.
      * `cost_usd` — `_stats` over every trial's finite numeric agent cost,
        including errored trials, or null when none reported a usable cost.
      * `cost_unknown_trials` — trials without a usable agent cost. A zero
        cost is known; an absent or invalid cost is unknown, not free.
      * `efficiency` — `efficiency_stats` over the same trials as
        `cost_usd` (errored trials with an agent block included): one block
        per `EFFICIENCY_METRICS` name, each with `n`, `n_missing`, `mean`,
        `median`, `min`, `max` and `sum`. Added alongside the figures above,
        which are unchanged.
      * `model_tokens` — `model_token_stats`: the same block per model id and
        per `MODEL_TOKEN_FIELDS` count, from each trial's `model_tokens`.
      * `cross_model` — `cross_model_stats`: how many trials spent more than
        `CROSS_MODEL_SHARE_THRESHOLD` of their tokens on models other than
        the arm's own, and that share pooled over the arm.
    """
    scored = [t for t in trials if not t.get("error")]
    trial_errors = [
        {"trial": index, "type": t["error"].get("type"),
         "detail": t["error"].get("detail", "")}
        for index, t in enumerate(trials, start=1) if t.get("error")]

    objective_stats = None
    if scored:
        by_id: dict = {}
        passed = total = 0
        for trial in scored:
            for check in trial.get("objective_checks") or []:
                # Keyed by the id's repr: a fixture may write any YAML value
                # as an id, a list included, and a list is not a dict key.
                entry = by_id.setdefault(
                    repr(check["id"]), {"id": check["id"], "n": 0, "passed": 0})
                entry["n"] += 1
                total += 1
                if check.get("passed"):
                    entry["passed"] += 1
                    passed += 1
        for entry in by_id.values():
            entry["pass_rate"] = entry["passed"] / entry["n"]
        objective_stats = {
            "n": len(scored), "passed": passed, "total": total,
            "mean_passed": passed / len(scored),
            "mean_total": total / len(scored),
            "checks": list(by_id.values())}

    judge_stats = None
    judged = [t["judge"] for t in scored if isinstance(t.get("judge"), dict)]
    if judged:
        usable = [j for j in judged
                  if "error" not in j and _is_number(j.get("overall"))]
        by_name: dict = {}
        for result in usable:
            for dim in result.get("dimensions") or []:
                if not isinstance(dim, dict) or not _is_number(dim.get("score")):
                    continue
                name = str(dim.get("name", "")).strip()
                by_name.setdefault(name.casefold(),
                                   {"name": name, "scores": []})["scores"].append(
                                       dim["score"])
        judge_stats = {
            "n": len(usable), "errors": len(judged) - len(usable),
            "overall": _stats([j["overall"] for j in usable]),
            "dimensions": [{"name": d["name"], **_stats(d["scores"])}
                           for d in by_name.values()]}

    costs = [t["agent"]["cost_usd"] for t in trials
             if isinstance(t.get("agent"), dict)
             and _is_number(t["agent"].get("cost_usd"))]

    violations = guidance_violations.aggregate(trials)
    return {"n": len(trials), "errors": len(trial_errors),
            "scored": len(scored), "trial_errors": trial_errors,
            "aggregate": {"objective": objective_stats, "judge": judge_stats,
                          "cost_usd": _stats(costs),
                          "cost_unknown_trials": len(trials) - len(costs),
                          "efficiency": efficiency_stats(trials, tool_errors),
                          "model_tokens": model_token_stats(trials),
                          "cross_model": cross_model_stats(trials),
                          **({"guidance_violations": violations} if violations is not None else {})}}


def _trials_error(stats: dict) -> dict | None:
    """The aggregate summary's `error`: null only when no trial errored.

    Deliberately not "null while some trial was scored". `error` is the field
    every reader of the single-trial shape already treats as "this arm has no
    clean score", and an arm with an errored trial has a mean over the
    survivors, which is not the same measurement as its sibling arm's.
    """
    if not stats["errors"]:
        return None
    kinds: dict = {}
    for entry in stats["trial_errors"]:
        kinds[entry["type"]] = kinds.get(entry["type"], 0) + 1
    listed = ", ".join(f"{kind} x{count}" for kind, count in kinds.items())
    tail = (f"score means are over the {stats['scored']} that did not"
            if stats["scored"] else "no trial was scored")
    return {"type": "trial_errors",
            "detail": f"{stats['errors']} of {stats['n']} trials errored "
                      f"({listed}); {tail}"}


def _fmt_mean(value: float) -> str:
    """One decimal, but an integral mean prints as an integer (`7`, not
    `7.0`) — the same rule scripts/make_badge.py prints its means by."""
    rounded = round(value, 1)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.1f}"


def _fmt_figure(name: str, value: float) -> str:
    """Cost to four decimals, as the cost column prints it; everything else
    (turns, milliseconds, token and error counts) to one."""
    return f"{value:.4f}" if name == "cost_usd" else _fmt_mean(value)


def _fmt_metric(name: str, block: dict | None) -> str:
    """One efficiency cell: `mean / median` of the trials that reported it,
    plus `(n of N)` when some did not. `-` when none did."""
    if not block or not block.get("n"):
        return "-"
    cell = (f"{_fmt_figure(name, block['mean'])} / "
            f"{_fmt_figure(name, block['median'])}")
    if block.get("n_missing"):
        cell += f" ({block['n']} of {block['n'] + block['n_missing']})"
    return cell


def _fmt_delta(name: str, value) -> str:
    if not _is_number(value):
        return "-"
    text = _fmt_figure(name, abs(value))
    if float(text) == 0:
        return "0"
    return ("+" if value > 0 else "-") + text


def _render_efficiency_table(arms: list[dict]) -> list[str]:
    """The efficiency table of one fixture: a row per metric, a column per
    arm (`mean / median`), and, when the arms are `with_skill` and
    `without_skill`, the with-minus-without delta of the mean and the
    median. Rows no arm reported are left out."""
    blocks = {arm["arm"]: arm["stats"]["aggregate"].get("efficiency") or {}
              for arm in arms}
    names = [name for name in EFFICIENCY_NAMES
             if any((blocks[a].get(name) or {}).get("n") for a in blocks)]
    if not names:
        return []
    paired = "with_skill" in blocks and "without_skill" in blocks
    delta = (efficiency_delta(blocks["with_skill"], blocks["without_skill"])
             if paired else {})
    header = "| Metric (mean / median) | " + " | ".join(blocks) + " |"
    rule = "| --- |" + " --- |" * len(blocks)
    if paired:
        header += " Delta mean | Delta median |"
        rule += " --- | --- |"
    lines = ["", "Efficiency per trial (a trial that did not report a metric "
             "is left out and the cell says how many did; delta is "
             "with_skill minus without_skill):" if paired else
             "Efficiency per trial (a trial that did not report a metric is "
             "left out and the cell says how many did):", "", header, rule]
    for name in names:
        row = f"| {name} | " + " | ".join(
            _fmt_metric(name, blocks[a].get(name)) for a in blocks) + " |"
        if paired:
            row += (f" {_fmt_delta(name, delta[name]['delta_mean'])} |"
                    f" {_fmt_delta(name, delta[name]['delta_median'])} |")
        lines.append(row)
    return lines


def _render_trials_report(skill: str, timestamp: str, trials: int,
                          sections: list[dict],
                          harness_version: str | None = None) -> str:
    """report.md for a run with more than one trial, or with nested fixtures.

    One section per fixture, its header carrying `n`. `sections` is a list of
    `{"label", "prompt", "arms"}`, each arm `{"arm", "models_used", "stats"}`
    with `stats` as `aggregate_trials` returns it. The single-fixture,
    single-trial run of a flat fixture does not come through here: it keeps
    `_render_report`'s page, byte for byte.
    """
    lines = [f"# Eval report: {skill}", "",
             f"- Timestamp: {timestamp}",
             f"- Trials per arm: {trials}"]
    for section in sections:
        arms = section["arms"]
        lines += ["",
                  f"## Fixture: {section['label']} (n={trials})", "",
                  f"- Prompt: {section['prompt'].strip()}",
                  _harness_line(harness_version, arms), "",
                  "| Arm | n | Errors | Objective (mean) | Judge overall "
                  "(mean, min to max) | Cost USD (mean / sum) |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for arm in arms:
            stats = arm["stats"]
            block = stats["aggregate"]
            objective_stats = block["objective"]
            if objective_stats and objective_stats["total"]:
                objective_str = (f"{_fmt_mean(objective_stats['mean_passed'])}/"
                                 f"{_fmt_mean(objective_stats['mean_total'])}")
            else:
                objective_str = "-"
            judge_stats = block["judge"]
            if not judge_stats:
                judge_str = "-"
            elif not judge_stats["overall"]:
                judge_str = "error"
            else:
                overall = judge_stats["overall"]
                judge_str = (f"{overall['mean']:.1f} ({overall['min']:.1f} to "
                             f"{overall['max']:.1f}, {overall['n']} judged)")
                if judge_stats["errors"]:
                    judge_str += f"; {judge_stats['errors']} judge error(s)"
            cost = block["cost_usd"]
            cost_str = (f"{cost['mean']:.4f} / {cost['sum']:.4f}"
                        if cost else "-")
            if block["cost_unknown_trials"]:
                cost_str += f"; {block['cost_unknown_trials']} unknown"
            lines.append(f"| {arm['arm']} | {stats['n']} | {stats['errors']} | "
                         f"{objective_str} | {judge_str} | {cost_str} |")

        lines += _render_efficiency_table(arms)
        lines += guidance_violations.render(arms)

        errored = [(arm["arm"], entry) for arm in arms
                   for entry in arm["stats"]["trial_errors"]]
        if errored:
            lines += ["",
                      "Errored trials are counted in n and excluded from "
                      "score means; known costs from all trials are counted:",
                      ""]
            lines += [f"- {arm_name} trial {entry['trial']}: "
                      f"{_error_cell(entry)}" for arm_name, entry in errored]

        check_ids: list = []
        for arm in arms:
            for check in (arm["stats"]["aggregate"]["objective"] or {}).get(
                    "checks", []):
                if check["id"] not in check_ids:
                    check_ids.append(check["id"])
        if check_ids:
            lines += ["",
                      "| Check (passed / scored) | "
                      + " | ".join(arm["arm"] for arm in arms) + " |",
                      "| --- |" + " --- |" * len(arms)]
            for check_id in check_ids:
                cells = []
                for arm in arms:
                    checks = (arm["stats"]["aggregate"]["objective"]
                              or {}).get("checks", [])
                    match = next((c for c in checks if c["id"] == check_id), None)
                    cells.append(f"{match['passed']}/{match['n']}"
                                 if match else "-")
                lines.append(f"| {str(check_id).replace('|', chr(92) + '|')} | "
                             + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _run_arm(arm_name: str, fixture: dict, seed: Path, registries: dict[str, dict],
            args: argparse.Namespace, timestamp: str,
            selection: tuple | None = None, *,
            out_dir: Path | None = None, extra: dict | None = None) -> dict:
    """Materialize a workspace, invoke the agent, score it, write results, clean up.

    ONE TRIAL (#66). A fresh workspace, one agent call, one judge call, one
    summary.json. `out_dir` and `extra` are how `_run_arm_trials` points that
    summary at a trial directory and labels it (`trial`, `fixture`, `n`); a
    caller that passes neither gets the path and the fields this function
    wrote before trials existed.

    `selection` is `select_models()`'s answer, resolved ONCE by main() and
    passed in: the roster is one file describing one run, and re-reading it per
    arm let two arms of the same run disagree if it changed underneath them.
    A selection error is checked and recorded FIRST, before any workspace is
    materialized (mkdtemp/copytree/git init) — a run this arm will never make
    is not worth building one only to shutil.rmtree it straight back out.
    """
    agent_model, roster_judge_model, selection_error = (
        selection if selection is not None else select_models(fixture, args))
    # Read once per run by main() (#202); a caller that built its own
    # Namespace without it records null rather than probing the CLI here.
    harness_version = getattr(args, "harness_version", None)
    permission_mode = _permission_mode(args)
    effort = _effort(args, fixture)
    extra = dict(extra or {})
    if fixture.get("_real_work"):
        extra["guidance_violations"] = guidance_violations.measure(None, None, None)
    if selection_error:
        # A runner-level error, recorded on the arm exactly like an agent
        # failure, so it leaves through main()'s existing exit-2 path instead
        # of running the agent on a model nobody chose. Checked BEFORE
        # materializing anything: a workspace this run will never use (no
        # agent is ever invoked) is not worth an mkdtemp + copytree + a git
        # init/add/commit only to shutil.rmtree it two lines later.
        error = {"type": "model-selection", "detail": selection_error}
        _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                       error, None, None, None, None, extra=extra,
                       harness_version=harness_version,
                       permission_mode=permission_mode, arm_dir=out_dir,
                       effort=effort, agent_model=agent_model)
        return {"arm": arm_name, "error": error, "agent": None,
                "objective_checks": None, "judge": None, "models_used": [], **extra}

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
                       error, None, None, None, None, extra=extra,
                       harness_version=harness_version,
                       permission_mode=permission_mode, arm_dir=out_dir,
                       effort=effort, agent_model=agent_model)
        shutil.rmtree(exc.workspace, ignore_errors=True)
        return {"arm": arm_name, "error": error, "agent": None,
                "objective_checks": None, "judge": None, "models_used": [], **extra}
    try:
        assert_stand_ins_on_path(workspace, agent_env(workspace, fixture.get("env")),
                                 fixture.get("env"))

        arm_config = {
            "name": arm_name,
            "model": agent_model,
            "timeout": args.timeout or fixture.get("timeout_s", 600),
            "env": fixture.get("env"),
            "followups": fixture.get("followups"),
            "permission_mode": permission_mode,
            "effort": effort,
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
                        # which eval.yml commits to the public persistent/eval-results
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

        baseline = guidance_violations.snapshot(workspace) if fixture.get("_real_work") else None
        result = registry_error if registry_error is not None else run_agent(
            workspace, fixture["prompt"], arm_config)
        if fixture.get("_real_work"):
            extra["guidance_violations"] = guidance_violations.measure(
                baseline, workspace, result.get("tool_trace"))

        error = None
        agent_summary = None
        objective_checks = None
        judge_result = None
        raw = result.get("raw")
        tool_trace = result.get("tool_trace")
        # Only a run that produced a result can say what served it; an
        # errored agent call records none (an `agent_error` result's raw
        # object is not trusted to be a complete one).
        agent_models = [] if "error" in result else models_used(raw)
        agent_usage = None if "error" in result else model_usage(raw)
        judge_models: list = []

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
            except objective.ScorerUnavailableError as exc:
                # A scoring dependency is missing on THIS machine: not the
                # agent's failure, so the trial is an error (excluded from
                # every check's denominator, listed in `trial_errors`), never
                # a failed check. The judge is skipped with the objective.
                error = {"type": "scorer_unavailable", "detail": str(exc)}
                _write_summary(args.results_dir, fixture["skill"], arm_name,
                               timestamp, error, agent_summary, None, None, raw,
                               extra=extra, harness_version=harness_version,
                               permission_mode=permission_mode,
                               models=agent_models, arm_dir=out_dir,
                               tool_trace=tool_trace, effort=effort,
                               agent_usage=agent_usage,
                               agent_model=agent_model)
                return {"arm": arm_name, "error": error,
                        "agent": agent_summary, "objective_checks": None,
                        "judge": None, "models_used": agent_models, **extra}
            except objective.FixtureError as exc:
                error = {"type": "invalid_fixture", "detail": str(exc)}
                _write_summary(args.results_dir, fixture["skill"], arm_name,
                               timestamp, error, agent_summary, None, None, raw,
                               extra=extra, harness_version=harness_version,
                               permission_mode=permission_mode,
                               models=agent_models, arm_dir=out_dir,
                               tool_trace=tool_trace, effort=effort,
                               agent_usage=agent_usage,
                               agent_model=agent_model)
                return {"arm": arm_name, "error": error,
                        "agent": agent_summary, "objective_checks": None,
                        "judge": None, "models_used": agent_models, **extra}

            if not args.no_judge:
                diff = _build_judge_diff(workspace)
                judge_cfg = fixture.get("judge", {})
                # Bound before the `with`, and read AFTER the try: a judge
                # CLI call that completed is recorded even when `score`
                # then raises on its answer (#203 round 1).
                judge_results: list = []
                try:
                    with judge.collecting_models() as judge_results:
                        judge_result = judge.score(
                            fixture["judge_rubric"], result.get("transcript") or "",
                            diff, model=roster_judge_model,
                            timeout=judge_cfg.get("timeout_s", 120),
                            weights=judge_cfg.get("weights"),
                            permission_mode=permission_mode,
                        )
                except guidance.GuidanceError:
                    # S1-a-2. A sink's own timeout refusal is a CONFIGURATION
                    # error, not a judge result: recorded as `{"error": ...}`
                    # it would score the arm and exit 0/1 with the rule never
                    # named. Re-raised so main()'s rc-2 contract holds.
                    raise
                except Exception as exc:  # noqa: BLE001 — record, never crash the run
                    judge_result = {"error": str(exc)}
                judge_models = models_used(*judge_results)

        _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                       error, agent_summary, objective_checks, judge_result, raw,
                       extra=extra, harness_version=harness_version,
                       permission_mode=permission_mode,
                       models=agent_models, judge_models=judge_models,
                       arm_dir=out_dir, tool_trace=tool_trace, effort=effort,
                       agent_usage=agent_usage, agent_model=agent_model)

        return {"arm": arm_name, "error": error, "agent": agent_summary,
                "objective_checks": objective_checks, "judge": judge_result,
                "models_used": agent_models, **extra}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _unit_dir(results_dir: Path, skill: str, timestamp: str,
              fixture_name: str | None) -> Path:
    """Where one fixture's arm directories go: the run directory itself for a
    flat fixture (the path every run before #66 wrote), `<run>/<fixture>/`
    for a nested one — so two fixtures of one skill never share an arm
    directory."""
    run_dir = results_dir / skill / timestamp
    return run_dir / fixture_name if fixture_name else run_dir


def _read_summary(arm_dir: Path) -> dict:
    with open(arm_dir / "summary.json", encoding="utf-8") as f:
        return json.load(f)


def _union(summaries: list[dict], key: str) -> list[str]:
    """The sorted, capped union of one model-list field across trials."""
    found = {model for summary in summaries for model in summary.get(key) or []}
    return sorted(found)[:MODELS_USED_MAX]


def _run_arm_trials(arm_name: str, item: dict, registries: dict[str, dict],
                    args: argparse.Namespace, timestamp: str,
                    selection: tuple | None) -> dict:
    """Run `args.trials` trials of one arm of one fixture, and aggregate.

    `item` is one prepared fixture: `{"fixture", "seed", "name"}`, `name`
    being the nested fixture's name or None for a flat one.

    Returns `{"arm", "models_used", "stats", "results"}`: `stats` is
    `aggregate_trials` over the trial summaries AS WRITTEN (read back from
    disk, so the aggregate cannot describe anything a reader of the trial
    files would not find there), and `results` the in-memory `_run_arm`
    returns, which the single-trial report is rendered from.
    """
    fixture = item["fixture"]
    arm_dir = _unit_dir(args.results_dir, fixture["skill"], timestamp,
                        item["name"]) / arm_name
    label = {"fixture": item["name"]} if item["name"] else {}
    results, written = [], []
    if args.trials == 1:
        results.append(_run_arm(arm_name, fixture, item["seed"], registries,
                                args, timestamp, selection, out_dir=arm_dir,
                                extra={**label, "n": 1}))
        written.append(_read_summary(arm_dir))
        stats = aggregate_trials(written, [_trial_tool_errors(arm_dir)])
    else:
        tool_errors = []
        for index in range(1, args.trials + 1):
            trial_dir = arm_dir / f"{TRIAL_DIR_PREFIX}{index}"
            results.append(_run_arm(arm_name, fixture, item["seed"], registries,
                                    args, timestamp, selection,
                                    out_dir=trial_dir,
                                    extra={**label, "trial": index}))
            written.append(_read_summary(trial_dir))
            tool_errors.append(_trial_tool_errors(trial_dir))
        stats = aggregate_trials(written, tool_errors)
        _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                       _trials_error(stats), None, None, None, None,
                       extra={**label, **stats},
                       harness_version=getattr(args, "harness_version", None),
                       permission_mode=_permission_mode(args),
                       models=_union(written, "models_used"),
                       judge_models=_union(written, "judge_models_used"),
                       arm_dir=arm_dir, effort=_effort(args, fixture),
                       agent_usage=sum_model_usage(written),
                       agent_model=_arm_model(written))
    return {"arm": arm_name, "models_used": _union(written, "models_used"),
            "stats": stats, "results": results}


def _write_pre_run_error(args: argparse.Namespace, fixture: dict,
                         error_type: str, detail: str,
                         fixture_name: str | None = None) -> str:
    """Record a fixture-level error as the artifacts a run would have left.

    A pre-run refusal that only printed to stdout left `results/` with
    nothing in it, so the reason the run produced no numbers was visible
    only to whoever watched it happen. The report and one summary.json per
    arm carry the named error instead, in the shape `_render_report` and
    `_write_summary` already use for an arm that failed.

    The harness version is recorded as null here: a pre-run refusal never
    invokes the CLI, so it does not spawn one just to ask its version.

    No trial is attempted, so the summaries carry no `n` (#66): they are the
    ones this function always wrote. A nested fixture's go under its own
    `<run>/<fixture>/` directory and the report names it.
    """
    timestamp = args.run_timestamp
    error = {"type": error_type, "detail": detail}
    arm_names = (["with_skill", "without_skill"] if args.arm == "both"
                 else [args.arm])
    unit_dir = _unit_dir(args.results_dir, fixture["skill"], timestamp,
                         fixture_name)
    for arm_name in arm_names:
        _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                       error, None, None, None, None,
                       extra={"fixture": fixture_name} if fixture_name else None,
                       arm_dir=unit_dir / arm_name)
    title = (f"{fixture['skill']}/{fixture_name}" if fixture_name
             else fixture["skill"])
    report = _render_report(title, fixture.get("prompt", ""),
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
TOOL_TRACE_NAME = "tool_trace.json"
ARM_DIR_FILES = ("summary.json", "raw.json", TOOL_TRACE_NAME)

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
    run history on the public `persistent/eval-results` branch — and `.` wrote into the
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
    harness_version = getattr(args, "harness_version", None)
    permission_mode = _permission_mode(args)
    effort = _effort(args, fixture)
    agent_model = getattr(args, "model", None) or fixture.get("model")
    extra = {}
    agent_summary = raw = tool_trace = None
    agent_models = []
    agent_usage = None
    scratch = Path(tempfile.mkdtemp(
        prefix=f"{ARM_WORKSPACE_PREFIX}{arm['name']}-"))
    try:
        workspace, home = scratch / "ws", scratch / "home"
        config, tmpdir = scratch / "config", scratch / "tmp"
        for path in (workspace, home, config, tmpdir):
            path.mkdir(parents=True)
        if seed.is_dir():
            shutil.copytree(seed, workspace, dirs_exist_ok=True)
        seed_prep.prepare_seed(workspace, fixture)
        seed_error = seed_prep.seed_guard(workspace, fixture)
        if seed_error is not None:
            raise guidance.GuidanceError(seed_error["detail"])
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
        if fixture.get("_real_work"):
            extra["guidance_violations"] = guidance_violations.measure(None, None, None)
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
                           key=ctx["key"], extra=extra,
                           harness_version=harness_version,
                           permission_mode=permission_mode, effort=effort,
                           agent_model=agent_model)
            return {"arm": arm["name"], "mode": arm["mode"], "error": error,
                    "agent": None, "objective_checks": None, "judge": None,
                    "guard": None, "inconclusive": True, "models_used": [],
                    **({"guidance_violations": extra["guidance_violations"]}
                       if "guidance_violations" in extra else {})}

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
                           key=ctx["key"], extra=extra,
                           harness_version=harness_version,
                           permission_mode=permission_mode, effort=effort,
                           agent_model=agent_model)
            return {"arm": arm["name"], "mode": arm["mode"], "error": error,
                    "agent": None, "objective_checks": None, "judge": None,
                    "guard": guard, "inconclusive": True, "models_used": [],
                    **({"guidance_violations": extra["guidance_violations"]}
                       if "guidance_violations" in extra else {})}

        arm_config = {
            "name": arm["name"],
            "model": agent_model,
            "timeout": args.timeout or fixture.get("timeout_s", 600),
            "setting_sources": setting_sources,
            "env_override": env,
            "followups": fixture.get("followups"),
            "permission_mode": permission_mode,
            "effort": effort,
            # A multi-turn arm's transcript lands under `config`, inside this
            # scratch, and goes when the scratch does: never archived.
            "session_scratch": str(scratch),
        }
        baseline = guidance_violations.snapshot(workspace) if fixture.get("_real_work") else None
        result = run_agent(workspace, fixture["prompt"], arm_config)
        if fixture.get("_real_work"):
            extra["guidance_violations"] = guidance_violations.measure(
                baseline, workspace, result.get("tool_trace"))

        error = None
        agent_summary = None
        objective_checks = None
        judge_result = None
        raw = result.get("raw")
        tool_trace = result.get("tool_trace")
        agent_models = [] if "error" in result else models_used(raw)
        agent_usage = None if "error" in result else model_usage(raw)
        judge_models: list = []

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
            try:
                objective_checks = objective.run_checks(
                    scored, str(workspace), str(seed),
                    transcript=result.get("transcript"))
            except objective.ScorerUnavailableError as exc:
                # As in `_run_arm`: a missing scoring dependency on THIS
                # machine is a trial error, not a failed check, and the
                # judge is skipped with the objective.
                error = {"type": "scorer_unavailable", "detail": str(exc)}

            if error is None and not args.no_judge and fixture.get("judge_rubric"):
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
                # Read after the try, as in the skill path (#203 round 1).
                judge_results: list = []
                try:
                    with judge.collecting_models() as judge_results:
                        judge_result = judge.score(
                            fixture["judge_rubric"], result.get("transcript") or "",
                            diff, model=judge_cfg.get("model"),
                            timeout=judge_cfg.get("timeout_s", 120),
                            weights=judge_cfg.get("weights"),
                            permission_mode=permission_mode)
                except guidance.GuidanceError:
                    # S1-a-2. A sink's own timeout refusal is a CONFIGURATION
                    # error, not a judge result: recorded as `{"error": ...}`
                    # it would score the arm and exit 0/1 with the rule never
                    # named. Re-raised so main()'s rc-2 contract holds.
                    raise
                except Exception as exc:  # noqa: BLE001 — record, never crash the run
                    judge_result = {"error": str(exc)}
                judge_models = models_used(*judge_results)

        _write_summary(args.results_dir, None, arm["name"], timestamp, error,
                       agent_summary, objective_checks, judge_result, raw,
                       key=ctx["key"], extra=extra,
                       harness_version=harness_version,
                       permission_mode=permission_mode, models=agent_models,
                       judge_models=judge_models, tool_trace=tool_trace,
                       effort=effort, agent_usage=agent_usage,
                       agent_model=agent_model)
        return {"arm": arm["name"], "mode": arm["mode"], "error": error,
                "agent": agent_summary, "objective_checks": objective_checks,
                "judge": judge_result, "guard": guard, "inconclusive": False,
                "models_used": agent_models,
                **({"guidance_violations": extra["guidance_violations"]}
                   if "guidance_violations" in extra else {})}
    except guidance.GuidanceError:
        if not fixture.get("_real_work"):
            raise
        error = {"type": "guidance_configuration", "detail": "guidance trial setup failed"}
        counts = extra.get("guidance_violations") or guidance_violations.measure(None, None, None)
        _write_summary(args.results_dir, None, arm["name"], timestamp,
                       error, agent_summary, None, None, raw, key=ctx["key"],
                       extra={"subject": "guidance", "section": ctx["section"],
                              "mode": arm["mode"], "bytes": None,
                              "guidance_violations": counts},
                       harness_version=harness_version, permission_mode=permission_mode,
                       models=agent_models, tool_trace=tool_trace,
                       effort=effort, agent_usage=agent_usage,
                       agent_model=agent_model)
        return {"arm": arm["name"], "mode": arm["mode"], "error": error,
                "agent": agent_summary, "objective_checks": None, "judge": None,
                "guard": None, "inconclusive": True, "models_used": [],
                "guidance_violations": counts}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _render_guidance_report(section: str, prompt: str, timestamp: str,
                            delivery: str, arm_bytes: dict,
                            arm_summaries: list[dict],
                            harness_version: str | None = None) -> str:
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
        _harness_line(harness_version, arm_summaries),
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
    lines += guidance_violations.render([
        {"arm": s["arm"], "stats": {"aggregate": {
            "guidance_violations": guidance_violations.aggregate([s])}}}
        for s in arm_summaries])
    return "\n".join(lines) + "\n"


def guidance_results_key(section: str, fixture_name: str | None) -> str:
    """The results/ subtree of a guidance run: `guidance/<section>`, plus the
    fixture's directory name for a `subject: any` fixture run with --section."""
    return f"guidance/{section}" + (f"/{fixture_name}" if fixture_name else "")


def _run_guidance(args: argparse.Namespace, fixture: dict,
                  fixture_name: str | None = None) -> int:
    """`subject: guidance` — the whole run, from section id to exit code.

    `fixture_name` is set for a `subject: any` fixture run with --section: its
    results go under `guidance/<section>/<fixture name>/`, so two real-work
    fixtures run under one section never share a results directory.
    """
    section = fixture.get("section")
    if not isinstance(section, str) or not section:
        print(f"{args.eval_dir / 'fixture.yaml'} has `subject: guidance` but no "
              "(or a non-string) `section:` — the id of a row in "
              "_agent-guidance's agents-md/eval-coverage.yml")
        return 2
    if "/" in section or section in (".", ".."):
        print(f"invalid section id {section!r}: it becomes a results/ path segment")
        return 2

    key = guidance_results_key(section, fixture_name)
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
            # Every guidance arm strips and guards its copy of the seed; the
            # objective-only path scores the workspace the same way.
            seed_prep.prepare_seed(workspace, fixture)
            seed_error = seed_prep.seed_guard(workspace, fixture)
            if seed_error is not None:
                print(f"setup failed: {seed_error['detail']}")
                return 2
            try:
                results = objective.run_checks(fixture, str(workspace), str(seed))
            except objective.ScorerUnavailableError as exc:
                # As the skill path's objective-only: a missing scoring
                # dependency is not a failed check (exit 1), so name it and
                # exit 2 instead of a traceback.
                print(f"scorer_unavailable: {exc}")
                return 2
            except objective.FixtureError as exc:
                # As the skill path's objective-only: a bad fixture value
                # (`strip_seed: "no"`, an oversized seed file) is a named
                # `invalid_fixture` and exit 2, not a traceback and exit 1,
                # the code a failing check returns. `SeedTooLarge` is a
                # `FixtureError`, so one clause covers both.
                print(f"invalid_fixture: {exc}")
                return 2
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
        # Once per run, before any arm (#202), as the skill path does.
        args.harness_version = claude_version()
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
                                     args.delivery, arm_bytes, arm_summaries,
                                     args.harness_version)
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


# ---------------------------------------------------------------------------
# Fixture layout (#66). A skill's fixtures live in ONE of two shapes:
#
#   flat     <skill>/fixture.yaml               one fixture; results under
#            <skill>/seed/                      results/<skill>/<ts>/<arm>/
#
#   nested   <skill>/<fixture-name>/fixture.yaml   several; results under
#            <skill>/<fixture-name>/seed/          results/<skill>/<ts>/<fixture-name>/<arm>/
#
# THE RULE IS POSITIONAL. A fixture directory whose PARENT directory is named
# exactly the fixture's own `skill:` is a nested fixture, named after its own
# directory; any other fixture directory is a flat one and writes the paths
# every run before #66 wrote. `run_eval.py evals/<skill>/<name>` and
# `run_eval.py evals/<skill> --fixture <name>` name the same fixture and write
# the same paths, which is what stops two fixtures of one skill sharing
# `results/<skill>/<ts>/<arm>/`.
#
# The position is read off the path AS NAMED — made absolute and normalized,
# symlinks not followed (`fixture_position`). A fixture is the directory entry
# an operator points at, and two entries of one skill directory are two
# fixtures whatever they link to; following links let two of them resolve to
# one name and one results directory.
#
# What the rule cannot see is intent: a flat fixture kept in a directory whose
# parent happens to carry the skill's own name (`<skill>/<skill>/fixture.yaml`)
# reads as a nested fixture called `<skill>`. `evals/<skill>/fixture.yaml` is
# never that — its parent is `evals`.
#
# NEVER BOTH. A directory holding a `fixture.yaml` is a fixture and may not
# also hold fixture subdirectories (its own `seed/` excepted, whatever the
# seed contains), nor sit directly inside another fixture. The two shapes
# write different trees under the same `results/<skill>/`, so a skill that
# had both would publish runs a reader cannot tell apart by path. Every
# fixture directory an invocation selects is checked both ways before it is
# loaded (`check_fixture_dir`).
# ---------------------------------------------------------------------------

# A nested fixture's name becomes a directory BESIDE report.md, and a flat
# fixture's arm directories sit at that same level — so a fixture may not be
# called what a run-directory file or a skill arm's directory is called.
# `seed` is refused because a flat fixture's own seed directory is skipped by
# name.
RESERVED_FIXTURE_NAMES = (SEED_DIR, "with_skill", "without_skill",
                          "objective-only", *RUN_DIR_FILES)


class FixtureLayoutError(guidance.GuidanceError):
    """The directory named on the command line is not a layout this runner
    can run: no fixture, a flat fixture and nested ones together, a fixture
    name that cannot be a results directory, a `--fixture` naming nothing."""


def _validate_fixture_name(name: str) -> None:
    """`name` is an existing directory's own name, so it is already one path
    segment of a length the filesystem takes; what is left to refuse is the
    characters results/ paths are held to, and the names already taken."""
    if not _ARM_NAME_RE.fullmatch(name):
        raise FixtureLayoutError(
            f"invalid fixture name {name!r}: a nested fixture is named after "
            "its directory and that name becomes a directory under results/, "
            "so it may only use letters, digits, `.`, `_` and `-`")
    # Casefolded: on a filesystem that folds case, `Report.md/` and
    # `report.md` are one name.
    if name.casefold() in RESERVED_FIXTURE_NAMES:
        raise FixtureLayoutError(
            f"invalid fixture name {name!r}: reserved "
            f"({', '.join(RESERVED_FIXTURE_NAMES)}). A nested fixture's "
            "results directory sits beside report.md, where a flat fixture's "
            "arm directories also go, and `seed` is a flat fixture's own seed")


def nested_fixture_names(directory: Path) -> list[str]:
    """The sorted names of `directory`'s immediate subdirectories that hold a
    fixture.yaml. Immediate only: a fixture two levels down is not this
    directory's."""
    if not directory.is_dir():
        return []
    return sorted(child.name for child in directory.iterdir()
                  if child.is_dir() and (child / FIXTURE_FILE).is_file())


def _mixed_layout_error(directory: Path, nested: list[str]) -> FixtureLayoutError:
    return FixtureLayoutError(
        f"{directory} holds a {FIXTURE_FILE} AND fixture subdirectories "
        f"({', '.join(nested)}). A skill directory holds one flat fixture or "
        "nested ones, never both: the two write different trees under the "
        "same results/<skill>/. Move the flat fixture into a subdirectory of "
        "its own, or remove the nested ones")


SUBJECT_ANY = "any"


def apply_runtime_subject(fixture: dict, skill: str | None, section: str | None,
                          arm: str, fixture_path: Path) -> dict:
    """The fixture with its subject named for this run.

    `subject: any` is a real-work fixture that names no treatment of its own
    (Adam, 2026-10-06, Q4: "Subject-agnostic"): `--skill NAME` runs it as a
    skill fixture and `--section ID` as a guidance fixture, so one fixture
    serves every subject instead of being copied once per subject. With
    neither, only `--arm objective-only` can run it: scoring a workspace
    needs no treatment. A fixture that fixes its own subject refuses both
    flags, so a flag never silently changes what a committed fixture means.
    The input is never mutated.
    """
    for flag, value in (("--skill", skill), ("--section", section)):
        if value is not None and not value.strip():
            raise guidance.GuidanceError(f"{flag} must be a nonblank name")
    subject = fixture.get("subject", "skill")
    if subject != SUBJECT_ANY:
        if skill is not None or section is not None:
            raise guidance.GuidanceError(
                f"{fixture_path} fixes its subject ({subject!r}); --skill and "
                f"--section name the subject only for a `subject: "
                f"{SUBJECT_ANY}` fixture")
        return fixture
    if "skill" in fixture or "section" in fixture:
        raise guidance.GuidanceError(
            f"{fixture_path} is `subject: {SUBJECT_ANY}`, so it names no "
            "`skill:` or `section:`; the run names one with --skill or --section")
    if skill is not None and section is not None:
        raise guidance.GuidanceError(
            "pass one of --skill and --section, not both --skill and --section")
    if skill is not None:
        return {**fixture, "subject": "skill", "skill": skill, "_real_work": True}
    if section is not None:
        return {**fixture, "subject": "guidance", "section": section, "_real_work": True}
    if arm != "objective-only":
        raise guidance.GuidanceError(
            f"{fixture_path} is `subject: {SUBJECT_ANY}` and this run names no "
            "subject: pass --skill NAME or --section ID, or score it with "
            "--arm objective-only")
    return fixture


def check_draft(fixture: dict, arm: str, allow_draft: bool, fixture_path: Path) -> None:
    """`draft: true` (#65's key) marks a fixture no human has reviewed yet.

    objective-only still runs it, which is how a draft proves its checks
    execute; an agent arm needs `--allow-draft`, which no workflow passes, so
    a draft is never paid for or published until a person removes the key.
    """
    if "draft" not in fixture:
        return
    if not isinstance(fixture["draft"], bool):
        raise guidance.GuidanceError(
            f"{fixture_path}: `draft:` must be true or false, got {fixture['draft']!r}")
    if fixture["draft"] and arm != "objective-only" and not allow_draft:
        raise guidance.GuidanceError(
            f"{fixture_path} is `draft: true`: a person removes the key after "
            "reviewing that its task text is the real ask and its checks encode "
            "it. Score it with --arm objective-only, or pass --allow-draft for a "
            "local run")


def fixture_position(eval_dir: Path) -> Path:
    """`eval_dir` as named: absolute and normalized (`.`, `..`, a trailing
    slash), symlinks NOT followed. The layout rule reads a fixture's name and
    its parent's off this path."""
    return Path(os.path.abspath(eval_dir))


def check_fixture_dir(eval_dir: Path) -> None:
    """Refuse a fixture directory that is half of a mixed layout: one that
    holds fixture subdirectories of its own (`seed/` excepted), or one that
    sits directly inside another fixture."""
    inner = [name for name in nested_fixture_names(eval_dir) if name != SEED_DIR]
    if inner:
        raise _mixed_layout_error(eval_dir, inner)
    position = fixture_position(eval_dir)
    if (position.parent / FIXTURE_FILE).is_file():
        raise _mixed_layout_error(position.parent, [position.name])


def resolve_fixture_dirs(eval_dir: Path, selected: str | None) -> list[Path]:
    """The fixture directories one invocation runs, in name order, each one
    already checked by `check_fixture_dir`.

    `eval_dir` holding a fixture.yaml is that one fixture — today's shape,
    and the only one `--fixture` does not apply to. Otherwise it is a skill
    directory and every `<name>/fixture.yaml` beneath it is run, or the one
    `--fixture NAME` selects.
    """
    if (eval_dir / FIXTURE_FILE).is_file():
        check_fixture_dir(eval_dir)
        if selected is not None:
            raise FixtureLayoutError(
                f"--fixture {selected!r} selects one of a skill directory's "
                f"nested fixtures, and {eval_dir} is itself a fixture. Drop "
                "the flag, or name the skill directory")
        return [eval_dir]
    nested = nested_fixture_names(eval_dir)
    if not nested:
        raise FixtureLayoutError(
            f"{eval_dir} holds no {FIXTURE_FILE}, and no "
            f"<name>/{FIXTURE_FILE} beneath it")
    for name in nested:
        _validate_fixture_name(name)
        check_fixture_dir(eval_dir / name)
    if selected is None:
        return [eval_dir / name for name in nested]
    if selected not in nested:
        raise FixtureLayoutError(
            f"--fixture {selected!r} names no fixture under {eval_dir} "
            f"(found: {', '.join(nested)})")
    return [eval_dir / selected]


def nested_fixture_name(eval_dir: Path, skill: str) -> str | None:
    """The nested fixture's name, or None for a flat fixture — the positional
    rule above, applied to one fixture directory whose `skill:` is known."""
    position = fixture_position(eval_dir)
    if position.parent.name != skill:
        return None
    _validate_fixture_name(position.name)
    return position.name


def _valid_timestamp(value: str) -> bool:
    """`--timestamp` is a results/ path segment, so it is held to the exact
    shape the wall-clock default produces and must be a real date and time."""
    if not _TIMESTAMP_RE.fullmatch(value):
        return False
    try:
        datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError:
        return False
    return True


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
                             "as the adam-agentskills entry; unknown names and empty "
                             "paths are rejected. Merges by name with "
                             "$SKILLS_EVALS_REGISTRIES (same NAME=PATH,NAME=PATH "
                             "shape; a bare entry there is also taken as "
                             "adam-agentskills), then $AGENTSKILLS_DIR (name kept "
                             "unchanged) for adam-agentskills specifically, then a "
                             "sibling checkout ../<name> next to this repo for any "
                             "name still unresolved")
    parser.add_argument("--model", default=None,
                        help="override the fixture's model for the agent")
    parser.add_argument("--roster", type=Path, default=None,
                        help="override the committed evals/roster.yml model "
                             "roster (tests and deliberate local runs only)")
    parser.add_argument("--permission-mode", default=guidance.DEFAULT_PERMISSION_MODE,
                        choices=list(guidance.PERMISSION_MODES),
                        help="the CLI permission mode every agent arm and "
                             "the judge are launched with (default "
                             f"{guidance.DEFAULT_PERMISSION_MODE}). Recorded "
                             "in every summary.json's `harness` block; "
                             "`bypassPermissions` reproduces runs recorded "
                             "before this option existed, and is refused by "
                             "the CLI when it runs as root")
    parser.add_argument("--effort", default=None,
                        choices=list(guidance.EFFORT_LEVELS),
                        help="the CLI effort level every agent arm is "
                             "launched with, first turn and follow-ups alike; "
                             "overrides the fixture's `effort:`. Without "
                             "either, no `--effort` is passed (the CLI's "
                             "default). Recorded in every summary.json's "
                             "`harness` block; the judge does not take it")
    parser.add_argument("--no-judge", action="store_true", help="skip judge scoring")
    parser.add_argument("--timeout", type=int, default=None,
                        help="override the fixture's agent timeout (seconds); "
                             f"1..{guidance.MAX_TIMEOUT_S}, the same ceiling "
                             "the fixture's own `timeout_s:` is held to")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                        help="root directory for run outputs (summaries + reports)")
    parser.add_argument("--fixture", default=None, metavar="NAME",
                        help="when eval_dir is a skill directory holding "
                             "nested fixtures (<name>/fixture.yaml), run only "
                             "this one; without it, every nested fixture runs")
    parser.add_argument("--skill", default=None, metavar="NAME",
                        help="the skill a `subject: any` fixture runs under "
                             "(a subject-agnostic real-work fixture)")
    parser.add_argument("--section", default=None, metavar="ID",
                        help="the guidance section a `subject: any` fixture "
                             "runs under")
    parser.add_argument("--allow-draft", action="store_true",
                        help="run an agent arm of a `draft: true` fixture "
                             "(local review only; no workflow passes it)")
    parser.add_argument("--trials", type=int, default=1,
                        help="trials per arm, each a fresh workspace, a fresh "
                             "agent call and its own judge call "
                             f"(default 1; 1..{MAX_TRIALS}). Above 1, each "
                             "trial is written under <arm>/trial-<k>/ and "
                             "<arm>/summary.json carries the aggregate")
    parser.add_argument("--timestamp", default=None,
                        help="the run directory's name, as YYYYMMDDTHHMMSSZ, "
                             "instead of the current UTC time — for tests and "
                             "wrappers that need a deterministic path. Refused "
                             "when that run directory already holds one of "
                             "the arms this invocation would write")
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

    # #66. Checked before any fixture is read, like the flag above: both are
    # operator input that decides what gets spent or where it gets written.
    # `type=int` bounds nothing, so `--trials 0`, a negative and an absurd
    # count are refused by name rather than run as zero or as a bill.
    if not 1 <= args.trials <= MAX_TRIALS:
        print(f"configuration error: --trials must be between 1 and "
              f"{MAX_TRIALS}, got {args.trials}. Every trial is a paid agent "
              "call and a paid judge call per arm")
        return 2
    if args.trials > 1 and args.arm == "objective-only":
        print("configuration error: --trials applies to the agent arms. "
              "objective-only scores one workspace with no agent call, so N "
              "trials of it would be N copies of one answer")
        return 2
    if args.timestamp is not None and not _valid_timestamp(args.timestamp):
        print(f"configuration error: --timestamp {args.timestamp!r} is not a "
              "UTC time written as YYYYMMDDTHHMMSSZ (for example "
              "20260716T070000Z). It becomes the run directory's name under "
              "results/")
        return 2
    # ONE timestamp per invocation: every fixture, arm and trial of this run
    # shares one run directory.
    args.run_timestamp = (args.timestamp
                          or datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT))

    try:
        eval_dirs = resolve_fixture_dirs(args.eval_dir, args.fixture)
    except FixtureLayoutError as exc:
        print(f"fixture configuration error: {exc}")
        return 2
    # A fixture found beneath the directory named on the command line, rather
    # than named by it.
    discovered = eval_dirs != [args.eval_dir]

    # EVERY selected fixture is loaded and checked before ANY arm of any of
    # them starts: the first refusal ends the invocation with nothing spent.
    prepared = []
    for eval_dir in eval_dirs:
        fixture = None
        try:
            fixture = load_fixture(eval_dir)
            agnostic = fixture.get("subject") == SUBJECT_ANY
            fixture = apply_runtime_subject(fixture, args.skill, args.section,
                                            args.arm, eval_dir / FIXTURE_FILE)
            check_draft(fixture, args.arm, args.allow_draft,
                        eval_dir / FIXTURE_FILE)
            answer_leak.validate_fixture(fixture, eval_dir / FIXTURE_FILE)
            validate_mapping_keys(fixture, eval_dir / FIXTURE_FILE)
            validate_timeouts(fixture, eval_dir / FIXTURE_FILE)
            validate_followups(fixture, eval_dir / FIXTURE_FILE)
            validate_effort(fixture, eval_dir / FIXTURE_FILE)
            seed_prep.validate_fixture(fixture, eval_dir)
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
                try:
                    name = nested_fixture_name(eval_dir, skill_name)
                except FixtureLayoutError as layout_exc:
                    print(f"fixture configuration error: {layout_exc}")
                    return 2
                print(f"invalid_judge_block: {exc}")
                _write_pre_run_error(args, fixture, "invalid_judge_block", str(exc),
                                     fixture_name=name)
                return 2
            print(f"fixture configuration error: {exc}")
            return 2
        except guidance.GuidanceError as exc:
            print(f"fixture configuration error: {exc}")
            return 2

        # Two subjects: a skill copied into the workspace (the original, and
        # untouched by #97), and the fleet guidance delivered into user memory by
        # the real fleet-memory.sh hook. Everything below this branch is the skill
        # path exactly as it was.
        subject = fixture.get("subject", "skill")
        if subject == "guidance":
            # #66 is the skill subject's: a guidance fixture is run by its own
            # directory, one trial per arm, under the wall clock's timestamp,
            # as before. Refused by name rather than run with a flag that
            # asked for something else quietly ignored.
            if discovered or args.trials > 1 or args.timestamp is not None:
                print(f"configuration error: {eval_dir / FIXTURE_FILE} is a "
                      "guidance fixture. Nested-fixture discovery, --trials "
                      "above 1 and --timestamp apply to skill fixtures only; "
                      "run it by its own directory without them")
                return 2
            try:
                if agnostic:
                    name = fixture_position(eval_dir).name
                    _validate_fixture_name(name)
                return _run_guidance(args, fixture, name if agnostic else None)
            except FixtureLayoutError as exc:
                print(f"fixture configuration error: {exc}")
                return 2
            except guidance.GuidanceError as exc:
                # The sink checks (S1-a-2) raise from inside whichever function
                # was about to spawn. Caught HERE so every one of them lands on
                # the rc-2 configuration contract instead of a traceback.
                print(f"configuration error: {exc}")
                return 2
        if subject == SUBJECT_ANY:
            # Only objective-only reaches here (apply_runtime_subject refused
            # every other arm): no skill, no results path, no judge. A
            # subject-agnostic fixture is named after its own directory.
            try:
                name = fixture_position(eval_dir).name
                _validate_fixture_name(name)
            except FixtureLayoutError as exc:
                print(f"fixture configuration error: {exc}")
                return 2
            prepared.append({"fixture": fixture, "seed": eval_dir / SEED_DIR,
                             "name": name})
            continue
        if subject != "skill":
            print(f"{eval_dir / FIXTURE_FILE} has unknown subject "
                  f"{subject!r} — expected 'skill', 'guidance' or "
                  f"'{SUBJECT_ANY}'")
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
            print(f"{eval_dir / FIXTURE_FILE} is missing required "
                  f"field(s): {', '.join(missing)}")
            return 2
        bad_type = [f for f in required if not isinstance(fixture.get(f), str)]
        if bad_type:
            print(f"{eval_dir / FIXTURE_FILE} field(s) must be strings: " +
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

        # Flat or nested (#66), decided by where the fixture sits and before any
        # results path is built: every path below hangs off this name.
        try:
            if agnostic:
                # Named after its own directory whatever --skill says, so two
                # real-work fixtures run under one skill never share results.
                name = fixture_position(eval_dir).name
                _validate_fixture_name(name)
            else:
                name = nested_fixture_name(eval_dir, fixture["skill"])
        except FixtureLayoutError as exc:
            print(f"fixture configuration error: {exc}")
            return 2
        if discovered and name is None:
            print(f"fixture configuration error: {eval_dir / FIXTURE_FILE} "
                  f"declares `skill: {fixture['skill']}`, but it was found as a "
                  f"nested fixture of {fixture_position(eval_dir).parent.name!r}. A "
                  "skill directory's nested fixtures all carry the directory's "
                  "own name as their `skill:`")
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
            _write_pre_run_error(args, fixture, "invalid_judge_block", detail,
                                 fixture_name=name)
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
            _write_pre_run_error(args, fixture, "judge_mode_unsupported", detail,
                                 fixture_name=name)
            return 2

        prepared.append({"fixture": fixture, "seed": eval_dir / SEED_DIR,
                         "name": name})

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
        # One JSON document about one workspace: a skill directory holding
        # several nested fixtures has no single answer to print.
        if len(prepared) != 1:
            print("configuration error: --arm objective-only scores one "
                  f"fixture, and {args.eval_dir} holds "
                  f"{len(prepared)} ({', '.join(i['name'] for i in prepared)}). "
                  "Pass --fixture NAME")
            return 2
        fixture, seed = prepared[0]["fixture"], prepared[0]["seed"]
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
                    seed_prep.prepare_seed(workspace, fixture)
                    setup_error = (run_setup(workspace, fixture)
                                   or seed_prep.seed_guard(workspace, fixture))
                    if setup_error is not None:
                        print(f"setup failed: {setup_error['detail']}")
                        return 2
                    results = objective.run_checks(fixture, str(workspace),
                                                   str(seed))
        except guidance.GuidanceError as exc:
            # run_setup's and the objective git checks' sink checks land here.
            print(f"configuration error: {exc}")
            return 2
        except objective.ScorerUnavailableError as exc:
            # Not a fixture error and not a failed check: exit 2, named.
            print(f"scorer_unavailable: {exc}")
            if "skill" in fixture:  # a `subject: any` run has no results path
                _write_pre_run_error(args, fixture, "scorer_unavailable", str(exc),
                                     fixture_name=prepared[0]["name"])
            return 2
        except objective.FixtureError as exc:
            # `SeedTooLarge` is a `FixtureError`, so one clause covers both.
            print(f"invalid_fixture: {exc}")
            if "skill" in fixture:  # a `subject: any` run has no results path
                _write_pre_run_error(args, fixture, "invalid_fixture", str(exc),
                                     fixture_name=prepared[0]["name"])
            return 2

        head = ({"skill": fixture["skill"]} if "skill" in fixture
                else {"subject": SUBJECT_ANY, "fixture": prepared[0]["name"]})
        print(json.dumps({**head, "arm": args.arm, "checks": results}, indent=2))
        return 0 if all(r["passed"] for r in results) else 1

    timestamp = args.run_timestamp
    arm_names = ["with_skill", "without_skill"] if args.arm == "both" else [args.arm]
    # The wall clock never names a run directory twice in practice; a
    # `--timestamp` can. Written into again, an arm directory would keep the
    # earlier run's `trial-<k>/` beside this run's aggregate, so the reuse is
    # refused before anything is spent — for the flag only, which leaves the
    # default path as it was.
    if args.timestamp is not None:
        taken = [str(arm_dir) for item in prepared for arm_dir in (
                     _unit_dir(args.results_dir, item["fixture"]["skill"],
                               timestamp, item["name"]) / name
                     for name in arm_names) if arm_dir.exists()]
        if taken:
            print(f"configuration error: --timestamp {timestamp} names a run "
                  f"that already holds {', '.join(taken)}. A run never writes "
                  "over another; pick another timestamp or results directory")
            return 2
    # Every prepared fixture carries the same `skill:` — a leaf is one
    # fixture, and a skill directory's nested ones are held to its name.
    skill = prepared[0]["fixture"]["skill"]
    outcomes = []
    try:
        # Read once per run, before any arm (#202): every arm's summary.json
        # records the same version, and a run whose version could not be
        # read still runs and records null.
        args.harness_version = claude_version()
        for item in prepared:
            # Resolved once per fixture: one trusted-roster read, one model
            # choice, every arm and every trial of that fixture.
            selection = select_models(item["fixture"], args)
            outcomes.append((item, [
                _run_arm_trials(name, item, registries, args, timestamp,
                                selection)
                for name in arm_names]))
    except guidance.GuidanceError as exc:
        # Every subprocess sink `_run_arm` can reach — run_setup, run_agent,
        # _nested_repo_diff, judge.score, the objective git checks — checks
        # its timeout on entry and raises this. Named rc 2, never a
        # traceback and never `Runner-level error in arm(s)`.
        print(f"configuration error: {exc}")
        return 2

    # The page a run has always left, byte for byte, for the run it has
    # always been: one flat fixture, one trial per arm. Anything else — more
    # trials, or a nested fixture — gets one section per fixture with `n` in
    # its header.
    single_trial_flat = (len(outcomes) == 1 and outcomes[0][0]["name"] is None
                         and args.trials == 1)
    if single_trial_flat:
        item, arms = outcomes[0]
        report = _render_report(skill, item["fixture"]["prompt"], timestamp,
                                [arm["results"][0] for arm in arms],
                                args.harness_version)
    else:
        report = _render_trials_report(
            skill, timestamp, args.trials,
            [{"label": item["name"] or skill,
              "prompt": item["fixture"]["prompt"], "arms": arms}
             for item, arms in outcomes],
            args.harness_version)
    report_path = args.results_dir / skill / timestamp / REPORT_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # ANY errored trial is a runner-level error and exit 2, as an errored arm
    # always was: an arm whose mean is over the survivors is not the
    # measurement that was asked for.
    errored_arms = []
    for item, arms in outcomes:
        for arm in arms:
            stats = arm["stats"]
            if not stats["errors"]:
                continue
            label = (f"{item['name']}/{arm['arm']}" if item["name"]
                     else arm["arm"])
            if args.trials > 1:
                label += f" ({stats['errors']} of {stats['n']} trials)"
            errored_arms.append(label)
    if errored_arms:
        print(f"Runner-level error in arm(s): {', '.join(errored_arms)}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
