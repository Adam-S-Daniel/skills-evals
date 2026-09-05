#!/usr/bin/env python3
"""Run a skill eval fixture.

Usage:
    python3 harness/run_eval.py evals/<skill> --arm objective-only
    python3 harness/run_eval.py evals/<skill> --arm both [--registry NAME=PATH ...]
        [--roster PATH] [--no-judge]

The model a run uses: `--model` > the fixture's `model:` > the roster > error.

`--arm objective-only` scores a workspace as-is (no agent invocation) — the
pristine seed should FAIL the fixture's checks; a correctly reworked copy
should PASS. `--arm with_skill|without_skill|both` runs the agent under test
(the Claude Code CLI, headless) on a fresh copy of the seed, scores it with
the objective checks and the LLM judge, and writes a summary + report under
`--results-dir` (default `results/`).
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
from scorers import judge, objective  # noqa: E402


def load_fixture(eval_dir: Path) -> dict:
    with open(eval_dir / "fixture.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


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


def _resolve_roster(cli_value: Path | None) -> Path:
    """Model roster: --roster, else $EVAL_ROSTER, else this checkout's roster/.

    The roster is published to the `eval-results` branch as `roster/latest.json`
    (harness/roster.py); CI materializes it before the eval runs and points
    $EVAL_ROSTER at it, which is why the eval invocation itself needs no new
    flag. Whether a missing roster is an error depends on the fixture — see
    select_models(): it is for an unpinned one, and it is not for a pinned one.
    """
    if cli_value:
        return Path(cli_value).expanduser()
    env = os.environ.get("EVAL_ROSTER")
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parent.parent / "roster" / "latest.json"


def read_roster(roster_path: Path | None) -> tuple[dict | None, str | None]:
    """(roster, problem). Never raises, and never returns a half-shaped roster.

    The roster is a JSON file written by another job on another machine and
    read off a public branch. Every one of these shapes was reachable and
    three of them crashed with an AttributeError three frames down: a
    top-level list, `arms` as a list of strings, `judge` as a string, a
    truncated file, an empty file. A named problem is the whole difference
    between a run that says what is wrong and a stack trace in a CI log.
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
            document = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return None, f"model roster at {path.name} is unreadable ({type(exc).__name__})"
    if not isinstance(document, dict):
        return None, f"model roster at {path.name} is not a JSON object"
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


def agent_env(workspace: Path, env_spec: dict | None) -> dict:
    """The environment the agent under test runs in.

    A fixture's `env:` mapping is applied over the harness's own environment,
    with `$WORKSPACE` (and any other `$VAR`) expanded against the workspace
    the arm actually got — a temp dir the fixture cannot know in advance.
    That is what lets a seed put a fake binary on the agent's PATH
    (`PATH: "$WORKSPACE/bin:$PATH"`), the Class B "fake `gh` on the seed
    workspace's PATH" move DESIGN.md prescribes, without the seed carrying an
    absolute path. Values are strings; a non-string is stringified rather
    than rejected, since YAML will happily hand over an int.
    """
    env = dict(os.environ)
    env["WORKSPACE"] = str(workspace)
    for key, value in (env_spec or {}).items():
        env[str(key)] = os.path.expandvars(str(value)).replace("$WORKSPACE", str(workspace))
    return env


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
    `$VAR`) expanded the same way `env:` values are (see `agent_env`), so a
    fixture can write `bash $WORKSPACE/setup.sh` or a bare `bash setup.sh`
    interchangeably.

    Returns `None` when the fixture has no `setup:` (every existing fixture)
    or the command exits 0. Otherwise returns a `{"error": "setup_failed",
    "detail": ...}` dict — the same error-dict convention `run_agent` uses —
    so a failing setup script fails the arm/run with a named error and a
    captured stderr/stdout tail, never a bare traceback out of a check that
    assumed setup had already put its files in place.
    """
    setup_cmd = fixture.get("setup")
    if not setup_cmd:
        return None
    cmd = os.path.expandvars(str(setup_cmd)).replace("$WORKSPACE", str(workspace))
    timeout = fixture.get("setup_timeout_s", 60)
    try:
        result = subprocess.run(["bash", "-c", cmd], cwd=workspace,
                                capture_output=True, text=True, timeout=timeout,
                                env=agent_env(workspace, fixture.get("env")))
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

    cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p", prompt,
           "--output-format", "json", "--permission-mode", "bypassPermissions",
           "--setting-sources", "project"]
    if arm.get("model"):
        cmd += ["--model", arm["model"]]

    timeout = arm.get("timeout", 600)
    try:
        result = subprocess.run(cmd, cwd=workspace, capture_output=True,
                                text=True, timeout=timeout,
                                env=agent_env(workspace, arm.get("env")))
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


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run git in `cwd` with a fixed local identity (don't rely on global
    config). `errors="replace"` — a workspace an agent has been let loose in
    can carry non-UTF-8 bytes git itself doesn't treat as binary (its own
    heuristic only looks for a NUL byte early in the content), and a diff or
    log that embeds them raw must not crash the whole run over it.
    """
    return subprocess.run(
        ["git", "-c", "user.email=skills-evals@local",
         "-c", "user.name=skills-evals harness", *args],
        cwd=cwd, check=True, capture_output=True, text=True, errors="replace",
    )


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
    sections = []
    for d in dirs:
        rel = d.relative_to(workspace)
        log = subprocess.run(
            ["git", "-C", str(d), "log", "--stat", "-p", "-1", "--format=%H %s"],
            capture_output=True, text=True, errors="replace", timeout=10)
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


def _write_summary(results_dir: Path, skill: str, arm_name: str, timestamp: str,
                   error: dict | None, agent: dict | None,
                   objective_checks: list | None, judge_result: dict | None,
                   raw: dict | None) -> None:
    arm_dir = results_dir / skill / timestamp / arm_name
    arm_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "skill": skill,
        "arm": arm_name,
        "timestamp": timestamp,
        "error": error,
        "agent": agent,
        "objective_checks": objective_checks,
        "judge": judge_result,
    }
    with open(arm_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    if raw is not None:
        transcripts_dir = arm_dir / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        with open(transcripts_dir / "raw.json", "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)


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
        # Error details can carry multiline stderr or `|`s — keep the table intact.
        err_str = " ".join(f"{err['type']}: {err['detail']}".split()).replace("|", "\\|")[:200] if err else ""

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

    workspace = Path(tempfile.mkdtemp(prefix=f"skills-evals-{arm_name}-"))
    try:
        shutil.copytree(seed, workspace, dirs_exist_ok=True)

        # run_setup BEFORE the bookkeeping commit — a fixture's `setup:`
        # script (e.g. disarm-inherited-reach's) builds real git repositories
        # in the workspace and then deletes its own machinery (setup.sh, any
        # template dir) as its last step. Committing first and running setup
        # second used to let that machinery survive into the "seed" commit
        # even though it no longer existed on disk: `git status --short` in
        # the agent's own workspace showed it as a spurious deletion, and
        # `git show HEAD:setup.sh` returned its content intact — both
        # readable by the agent under test. A `setup:` script that writes
        # into `.git/info/exclude` (again, disarm-inherited-reach's) still
        # works in this order: `git init` on a `.git` directory that already
        # has one (created by `mkdir -p` before the repo itself exists)
        # initializes normally and leaves unrelated existing files alone —
        # verified directly, not assumed.
        setup_result = run_setup(workspace, fixture)
        if setup_result is not None:
            error = {"type": setup_result["error"], "detail": setup_result.get("detail", "")}
            _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                           error, None, None, None, None)
            return {"arm": arm_name, "error": error, "agent": None,
                    "objective_checks": None, "judge": None}

        _git("init", "-q", cwd=workspace)
        _git("add", "-A", cwd=workspace)
        _git("commit", "-q", "-m", "seed", cwd=workspace)

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
            objective_checks = objective.run_checks(
                fixture, str(workspace), str(seed), transcript=result.get("transcript"))

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
                except Exception as exc:  # noqa: BLE001 — record, never crash the run
                    judge_result = {"error": str(exc)}

        _write_summary(args.results_dir, fixture["skill"], arm_name, timestamp,
                       error, agent_summary, objective_checks, judge_result, raw)

        return {"arm": arm_name, "error": error, "agent": agent_summary,
                "objective_checks": objective_checks, "judge": judge_result}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_dir", type=Path)
    parser.add_argument("--arm", default="objective-only",
                        choices=["objective-only", "with_skill", "without_skill", "both"])
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
                        help="model roster JSON (harness/roster.py); REQUIRED when "
                             "the fixture pins no model. Else $EVAL_ROSTER, else "
                             "roster/latest.json in this checkout")
    parser.add_argument("--no-judge", action="store_true", help="skip judge scoring")
    parser.add_argument("--timeout", type=int, default=None,
                        help="override the fixture's agent timeout (seconds)")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                        help="root directory for run outputs (summaries + reports)")
    args = parser.parse_args()

    fixture = load_fixture(args.eval_dir)
    seed = args.eval_dir / "seed"

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

    if args.arm != "objective-only":
        try:
            _validate_skill_name(fixture["skill"])
        except ValueError as exc:
            print(f"invalid fixture: {exc}")
            return 2

    if args.arm == "objective-only":
        if args.workspace:
            # An explicitly given workspace is scored as-is — the caller's
            # own responsibility to have already run any `setup:` themselves
            # (or to be scoring a hand-built workspace that never needed it).
            workspace = args.workspace
            results = objective.run_checks(fixture, str(workspace), str(seed))
        else:
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp) / "ws"
                shutil.copytree(seed, workspace)
                setup_error = run_setup(workspace, fixture)
                if setup_error is not None:
                    print(f"setup failed: {setup_error['detail']}")
                    return 2
                results = objective.run_checks(fixture, str(workspace), str(seed))

        print(json.dumps({"skill": fixture["skill"], "arm": args.arm,
                          "checks": results}, indent=2))
        return 0 if all(r["passed"] for r in results) else 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arm_names = ["with_skill", "without_skill"] if args.arm == "both" else [args.arm]

    # Resolved once: one roster read, one model choice, both arms.
    selection = select_models(fixture, args)
    arm_summaries = [_run_arm(name, fixture, seed, registries, args, timestamp,
                              selection)
                     for name in arm_names]

    report = _render_report(fixture["skill"], fixture["prompt"], timestamp, arm_summaries)
    report_path = args.results_dir / fixture["skill"] / timestamp / "report.md"
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
