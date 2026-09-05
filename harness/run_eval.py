#!/usr/bin/env python3
"""Run an eval fixture.

Usage:
    python3 harness/run_eval.py evals/<skill> --arm objective-only
    python3 harness/run_eval.py evals/<skill> --arm both [--registry NAME=PATH ...] [--no-judge]
    python3 harness/run_eval.py evals/guidance/<id> --arm both [--guidance PATH]

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
        resolved[name] = {"path": path, "layout": entry["layout"], "url": entry["url"],
                          "source": source}
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
                f"registry {name!r} ({entry['source']}) resolves to "
                f"{entry['path']}, which is not a directory")


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
            pattern = registry / skill_md_glob
            return {"error": "skill_not_found",
                    "detail": f"no SKILL.md matched {pattern}"}
        skill_src = matches[0]
        skill_dest = workspace / ".claude" / "skills" / skill
        try:
            shutil.copytree(skill_src, skill_dest)
        except OSError as exc:
            # FileExistsError (the destination dir already exists) and
            # NotADirectoryError (a seed shipping .claude/skills itself as a
            # regular FILE, so os.makedirs can't create skill_dest under it)
            # both land here — both are a seed/workspace layout problem, not
            # something to raise out of run_agent's "nothing is raised" contract.
            return {"error": "skill_install_failed",
                    "detail": f"{skill_dest} already exists in the seed: {exc}"}

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

    timeout = arm.get("timeout", 600)
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
            args: argparse.Namespace, timestamp: str) -> dict:
    """Materialize a workspace, invoke the agent, score it, write results, clean up."""
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
            "model": args.model or fixture.get("model"),
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
                        registry_error = {
                            "error": "registry_not_found",
                            "detail": f"registry {fixture['registry']!r} resolves "
                                      f"to {entry['path']}, which is not a "
                                      "directory"}
                    else:
                        arm_config["skill"] = fixture["skill"]
                        arm_config["registry"] = entry["path"]
                        arm_config["layout"] = entry["layout"]

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
                        model=judge_cfg.get("model"),
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

# The placeholder a guidance fixture writes where the run's magic token goes.
# The token is fresh per run, so a fixture cannot name it; `transcript_matches`
# patterns (and any other check string) get it substituted in at score time.
TOKEN_PLACEHOLDER = "$MAGIC_TOKEN"


def _validate_arm_entry(name: str, entry: dict) -> dict:
    if not isinstance(name, str) or not _ARM_NAME_RE.fullmatch(name):
        raise guidance.GuidanceError(
            f"invalid arm name {name!r}: arm names become directory names "
            "under results/, so they must be a single path segment")
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
        declared = fixture.get("arms") or DEFAULT_GUIDANCE_ARMS
        if not isinstance(declared, dict) or not declared:
            raise guidance.GuidanceError(
                "`arms:` must be a mapping of arm name -> {mode: ...}")
    arms = [_validate_arm_entry(name, entry) for name, entry in declared.items()]
    if arm_flag in ("both", "all"):
        return arms
    for arm in arms:
        if arm["name"] == arm_flag:
            return [arm]
    raise guidance.GuidanceError(
        f"--arm {arm_flag!r} names no arm in this fixture (declared: "
        f"{', '.join(a['name'] for a in arms)}; or `both` for all of them)")


def substitute_token(value, token: str):
    """Replace the fixture's `$MAGIC_TOKEN` placeholder with this run's token,
    recursively, in a copy — the fixture dict itself is never mutated."""
    if isinstance(value, str):
        return value.replace(TOKEN_PLACEHOLDER, token)
    if isinstance(value, list):
        return [substitute_token(item, token) for item in value]
    if isinstance(value, dict):
        return {key: substitute_token(item, token) for key, item in value.items()}
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
    expectation = "the magic word" if guard["expected"] else "no magic word"
    observed = "saw it" if guard["observed"] else "did not see it"
    return {"type": "guard_miss",
            "detail": f"delivery guard expected {expectation}, the probe "
                      f"{observed} — this arm was not delivered what its mode "
                      "says (or something else already had been); no score is "
                      "written for it"}


def _run_guidance_arm(arm: dict, fixture: dict, seed: Path, ctx: dict,
                      args: argparse.Namespace, timestamp: str) -> dict:
    """Materialize a scratch dir, deliver, guard, invoke, score, clean up."""
    scratch = Path(tempfile.mkdtemp(prefix=f"skills-evals-{arm['name']}-"))
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
        payload = guidance.assemble(ctx["guidance_dir"], ctx["row"], arm["mode"],
                                    token=ctx["token"])
        info = guidance.deliver(
            ctx["guidance_dir"], scratch=scratch, home=home, payload=payload,
            dest_dir=config if delivery == "user" else workspace)
        env = guidance.agent_env(workspace=workspace, home=home, tmpdir=tmpdir,
                                 config_dir=config, env_spec=fixture.get("env"))
        setting_sources = guidance.SETTING_SOURCES[delivery]
        # The guard's preflight model: the fixture's own `model:` pin when it
        # has one, else the CLI's default. When the model roster (#67) lands,
        # its `preflight` entry — the cheapest model that can answer a
        # tool-free probe — is what this line consults instead.
        preflight_model = args.model or fixture.get("model")
        guard = guidance.run_guard(
            workspace=workspace, token=ctx["token"],
            expected=guidance.guard_expectation(arm["mode"]), env=env,
            setting_sources=setting_sources, model=preflight_model,
            timeout=(fixture.get("guard") or {}).get("timeout_s", 300))

        extra = {"subject": "guidance", "section": ctx["section"],
                 "mode": arm["mode"], "bytes": info["bytes"],
                 "delivery": delivery, "guard": guard,
                 "hook_verdict": info["verdict"]}

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
            scored["objective_checks"] = substitute_token(checks, ctx["token"])
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
           "token": guidance.new_token()}

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
    with open(report_dir / "report.md", "w", encoding="utf-8") as f:
        f.write(report)

    inconclusive = [s for s in arm_summaries if s["inconclusive"]]
    for s in inconclusive:
        guard = s["guard"]
        print(f"INCONCLUSIVE {s['arm']} (mode {s['mode']}): guard expected "
              f"{guard['expected']}, observed {guard['observed']} — "
              f"{s['error']['detail']}")
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
    parser.add_argument("--no-judge", action="store_true", help="skip judge scoring")
    parser.add_argument("--timeout", type=int, default=None,
                        help="override the fixture's agent timeout (seconds)")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                        help="root directory for run outputs (summaries + reports)")
    args = parser.parse_args()

    fixture = load_fixture(args.eval_dir)
    seed = args.eval_dir / "seed"

    # Two subjects: a skill copied into the workspace (the original, and
    # untouched by #97), and the fleet guidance delivered into user memory by
    # the real fleet-memory.sh hook. Everything below this branch is the skill
    # path exactly as it was.
    subject = fixture.get("subject", "skill")
    if subject == "guidance":
        return _run_guidance(args, fixture)
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
    arm_summaries = [_run_arm(name, fixture, seed, registries, args, timestamp)
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
