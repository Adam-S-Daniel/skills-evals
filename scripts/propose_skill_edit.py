#!/usr/bin/env python3
"""Propose one SKILL.md edit, measure it against held-out fixtures, keep the record.

Part of https://github.com/Adam-S-Daniel/skills-evals/issues/71 (the smallest
slice) and https://github.com/Adam-S-Daniel/skills-evals/issues/232. The
decision record is docs/decisions/0005-improvement-loop-reuses-skill-creator.md.

    python3 scripts/propose_skill_edit.py <skill> \\
        --registry adam-agentskills=PATH [--ref REF] [--trials 3] \\
        [--rotation K] [--min-gain .10] [--holdout FIXTURE] \\
        [--trigger-eval-set FILE] [--skill-creator DIR] \\
        [--results-dir DIR] [--no-judge] [--dry-run]

WHAT IT DOES, in order:

 1. Refuses (exit 2, "needs more fixtures") a skill with fewer than three
    nested fixtures under `evals/<skill>/`: one held-out fixture beside one
    train fixture is a coin toss, not a split.
 2. Splits them deterministically: the fixtures in name order, validation is
    the one at index `rotation % n`, train is the rest. `rotation` defaults to
    the number of records already written for this skill, so consecutive
    runs hold out a different fixture. `--holdout` removes one fixed fixture
    from both train and the rotating validation population on every run.
 3. Builds two scratch registries from `git archive <ref>` of the local
    registry checkout: no `.git`, so nothing in them has a push path.
 4. BASELINE: `harness/run_eval.py evals/<skill> --arm with_skill --trials N`
    against the first scratch copy.
 5. TRIGGER HALF, from Anthropic's skill-creator plugin: its
    `scripts/run_loop.py` description-optimization loop (stratified 60/40
    train/held-out split of a should/should-not-trigger query set, 3 runs per
    query, best description picked by HELD-OUT score). The validation
    fixture's prompt and the fixed holdout's prompt are never in that set.
    Scratch project settings disable the archived registry plugins that
    provide the skill, leaving the operator's login available.
 6. BODY HALF: one proposal call (roster judge model, no tools) returning
    `{rationale, unified_diff}` for SKILL.md's body, fed the train fixtures'
    failed checks and transcripts. A diff naming any other file, or touching
    the frontmatter, is rejected before anything else runs.
 7. CANDIDATE: both halves applied to the second scratch copy and measured
    with the same run_eval invocation.
 8. ACCEPT only if validation held (objective pass rate not lower; judge mean
    not lower by more than 0.5) AND train improved (objective pass rate
    higher by at least `--min-gain` (default .10), or equal with judge mean
    higher by at least ten times that gain). A fixed holdout must not regress
    on either score. This is a conservative heuristic, not a significance test.
 9. Writes `<results>/improvements/<skill>/<ts>.json` always, `<ts>.patch`
    whenever a candidate existed, and `<ts>.pr-body.md` on accept. Nothing is
    pushed and no pull request is opened: a human reads the record first.

`--dry-run` prints the plan and makes no model call and no write.

EVERY MODEL CALL GOES THROUGH A `Runner` (the three methods below), so the
tests drive the whole pipeline offline with a fake. This is a LOCAL exhibit
under ADR 0002 decision 4: it runs under the operator's own login, its numbers
are not badge input, and it never runs in CI.

Exit codes: 0 accepted, 1 rejected (or nothing to measure), 2 refused or
errored before a decision could be taken.
"""

from __future__ import annotations

import argparse
import difflib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_DIR = REPO_ROOT / "harness"
EVALS_DIR = REPO_ROOT / "evals"
RUN_EVAL = HARNESS_DIR / "run_eval.py"

sys.path.insert(0, str(HARNESS_DIR))
from cli_json import normalize_cli_result  # noqa: E402
import run_eval  # noqa: E402

MIN_FIXTURES = 3
DEFAULT_TRIALS = 3
DEFAULT_MIN_GAIN = 0.10
#: The judge may drop by at most this much on validation (#71 step 3).
JUDGE_TOLERANCE = 0.5
#: skill-creator's own hard limit on a description (improve_description.py).
DESCRIPTION_MAX_CHARS = 1024
#: How much of one failing trial's final reply the proposal prompt carries.
TRANSCRIPT_EXCERPT_CHARS = 4000
#: The arm whose numbers a SKILL.md edit can move.
ARM = "with_skill"

EXIT_ACCEPTED, EXIT_REJECTED, EXIT_REFUSED = 0, 1, 2

#: Where skill-creator lives when nothing names it: the installed bundle that
#: `claude plugin install skill-creator@claude-plugins-official` records.
SKILL_CREATOR_PLUGIN_KEY = "skill-creator@claude-plugins-official"
SKILL_CREATOR_SUBDIR = Path("skills") / "skill-creator"


class Refusal(Exception):
    """Configuration or measurement problem: exit 2, no decision taken."""


class InvalidProposal(Exception):
    """The proposal broke a constraint; it is recorded and never measured."""


# ---------------------------------------------------------------------------
# The runner: every step that can spend model budget, and nothing else.
# ---------------------------------------------------------------------------

class Runner:
    """The real thing. Tests substitute a fake with the same three methods."""

    def run_eval(self, argv: list[str]) -> int:
        """`harness/run_eval.py` with `argv`; its exit code (0 pass, 1 a
        check failed, 2 configuration error)."""
        return subprocess.run([sys.executable, str(RUN_EVAL), *argv],
                              check=False).returncode

    def run_description_loop(self, argv: list[str], *, cwd: Path,
                             skill_creator: Path) -> dict:
        """skill-creator's `scripts/run_loop.py` with `argv`, run from
        `cwd` (its `find_project_root` writes a command file under the
        nearest `.claude/`, so `cwd` must be a scratch project), and its JSON
        stdout parsed. A `skill-creator` link to the plugin is planted in `cwd`."""
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            p for p in (str(skill_creator), env.get("PYTHONPATH", "")) if p)
        # Run through a link to the plugin planted in the scratch project, so
        # the script path is a literal: the test suite's fork scan
        # (test_every_suite_forking_test_in_this_repo_stands_down_in_a_child)
        # can then prove this spawn is skill-creator and not the suite, which
        # it cannot for `-m` or a computed path. PYTHONPATH carries
        # skill-creator's `scripts` package, so its imports resolve as under
        # its documented `python -m scripts.run_loop`.
        link = Path(cwd) / "skill-creator"
        if not link.exists():
            link.symlink_to(skill_creator, target_is_directory=True)
        proc = subprocess.run([sys.executable, "skill-creator/scripts/run_loop.py", *argv],
                              cwd=cwd, env=env, capture_output=True, text=True,
                              check=False)
        if proc.returncode != 0:
            raise Refusal(f"skill-creator run_loop exited {proc.returncode}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise Refusal(f"skill-creator run_loop printed no JSON ({exc})") from exc

    def propose(self, prompt: str, model: str) -> str:
        """One headless call, no tools, prompt on stdin; the reply text."""
        cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p",
               "--output-format", "json", "--permission-mode", "default",
               "--tools", "", "--model", model]
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        try:
            proc = subprocess.run(cmd, input=prompt, capture_output=True,
                                  text=True, env=env, timeout=600, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Refusal(f"proposal call could not run: {type(exc).__name__}") from exc
        if proc.returncode != 0:
            raise Refusal(f"proposal call exited {proc.returncode}")
        try:
            return normalize_cli_result(json.loads(proc.stdout)).get("result", "")
        except (ValueError, AttributeError) as exc:
            raise Refusal("proposal call printed no JSON result") from exc


# ---------------------------------------------------------------------------
# Fixtures, split, registry
# ---------------------------------------------------------------------------

def skill_fixtures(skill: str) -> list[str]:
    """The nested fixture names under `evals/<skill>/`, sorted."""
    run_eval._validate_skill_name(skill)
    return run_eval.nested_fixture_names(EVALS_DIR / skill)


def split_fixtures(fixtures: list[str], rotation: int,
                   holdout: str | None = None) -> tuple[list[str], str]:
    """(train, validation): validation is `sorted(fixtures)[rotation % n]`."""
    if len(fixtures) < MIN_FIXTURES:
        raise Refusal(f"needs more fixtures: {len(fixtures)} found, "
                      f"{MIN_FIXTURES} required (one held out, the rest trained on)")
    if holdout is not None and holdout not in fixtures:
        raise Refusal(f"--holdout {holdout!r} is not a nested fixture of this skill")
    ordered = sorted(f for f in fixtures if f != holdout)
    validation = ordered[rotation % len(ordered)]
    return [f for f in ordered if f != validation], validation


def default_rotation(records_dir: Path) -> int:
    """How many records this skill already has: each run holds out the next
    fixture, and the same results directory always gives the same answer."""
    return len(list(records_dir.glob("*.json"))) if records_dir.is_dir() else 0


def load_fixtures(skill: str, names: list[str]) -> dict:
    out = {}
    for name in names:
        try:
            fixture = run_eval.load_fixture(EVALS_DIR / skill / name)
        except (OSError, yaml.YAMLError, run_eval.guidance.GuidanceError) as exc:
            raise Refusal(f"fixture {name!r} is unreadable: {exc}") from exc
        if fixture.get("skill") != skill:
            raise Refusal(f"fixture {name!r} names skill {fixture.get('skill')!r}, "
                          f"not {skill!r}")
        out[name] = fixture
    registries = {f.get("registry") for f in out.values()}
    if len(registries) != 1:
        raise Refusal("the fixtures name more than one registry; one scratch "
                      "registry cannot serve them all")
    return out


def resolve_registry(url: str, flags: list[str] | None) -> dict:
    """The registries.yml entry for `url`, with its local checkout."""
    resolved = run_eval.resolve_registries(
        flags, os.environ.get("SKILLS_EVALS_REGISTRIES"), REPO_ROOT,
        os.environ.get("AGENTSKILLS_DIR"))
    entry = run_eval.registry_for_url(resolved, url)
    if not (entry["path"] / ".git").exists():
        raise Refusal(f"registry {entry['name']!r} has no git checkout at "
                      f"{entry['source']}; pass --registry {entry['name']}=PATH")
    return entry


def resolve_ref(checkout: Path, ref: str) -> str:
    proc = subprocess.run(["git", "-C", str(checkout), "rev-parse", "--verify",
                           "--quiet", f"{ref}^{{commit}}"],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise Refusal(f"ref {ref!r} does not resolve to a commit in the registry checkout")
    return proc.stdout.strip()


def archive_registry(checkout: Path, sha: str, dest: Path) -> Path:
    """`git archive <sha>` of the checkout, extracted into `dest`. The copy
    carries no `.git`, so there is no remote and no push path in it."""
    proc = subprocess.run(["git", "-C", str(checkout), "archive", "--format=tar", sha],
                          capture_output=True, check=False)
    if proc.returncode != 0:
        raise Refusal("git archive of the registry failed")
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        tar.extractall(dest, filter="data")
    return dest


def find_skill_dir(registry_root: Path, layout: str, skill: str) -> Path:
    matches = sorted(registry_root.glob(run_eval._skill_md_glob(layout, skill)))
    if len(matches) != 1:
        raise Refusal(f"expected exactly one {skill}/SKILL.md in the registry, "
                      f"found {len(matches)}")
    return matches[0].parent


def skill_provider_plugins(registry_root: Path, skill: str) -> list[str]:
    """Local marketplace plugins providing `skill`, using archived manifests.

    Default skills/ and declared additional skill paths are additive. Remote
    marketplace sources cannot be inspected in this archive and are skipped.
    Every local path is confined to the archive; no installed plugin runs.
    """
    def read_manifest(path: Path) -> dict:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise Refusal(f"unreadable plugin manifest {path.name}") from exc
        if not isinstance(value, dict):
            raise Refusal(f"plugin manifest {path.name} must be an object")
        return value

    def local_path(base: Path, value: str) -> Path:
        if not isinstance(value, str) or (value != "." and not value.startswith("./")):
            raise Refusal("local plugin paths must be . or start with ./")
        path = (base / value).resolve()
        if not path.is_relative_to(registry_root.resolve()):
            raise Refusal("local plugin path escapes the archived registry")
        return path

    marketplace_path = registry_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.exists():
        return []  # No marketplace means no fully-qualified installed key.
    marketplace = read_manifest(marketplace_path)
    market_name, plugins = marketplace.get("name"), marketplace.get("plugins")
    if not isinstance(market_name, str) or not market_name or not isinstance(plugins, list):
        raise Refusal("marketplace manifest needs a name and plugins list")
    providers = set()
    for entry in plugins:
        if not isinstance(entry, dict):
            raise Refusal("marketplace plugin entry must be an object")
        source = entry.get("source")
        if isinstance(source, dict):
            continue  # Federated sources are never fetched by this loop.
        root = local_path(registry_root, source)
        manifest_path = root / ".claude-plugin" / "plugin.json"
        manifest = read_manifest(manifest_path) if manifest_path.exists() else {}
        name = entry.get("name")  # Installed keys use the marketplace entry.
        if not isinstance(name, str) or not name:
            raise Refusal("marketplace plugin entry needs a name")
        paths = []
        for declaration in (manifest.get("skills", []), entry.get("skills", [])):
            if isinstance(declaration, str):
                declaration = [declaration]
            if not isinstance(declaration, list):
                raise Refusal("plugin skills must be a path or list of paths")
            for declared in declaration:
                path = local_path(root, declared)
                if not path.is_relative_to(root):
                    raise Refusal("skill path escapes its plugin root")
                paths.append(path)
        defaults = ([] if root == registry_root.resolve() and entry.get("skills")
                    else [root / "skills"])
        for path in defaults + paths:
            candidates = ([path / "SKILL.md"] if (path / "SKILL.md").is_file()
                          else sorted(path.glob("*/SKILL.md")))
            for candidate in candidates:
                if not candidate.resolve().is_relative_to(root):
                    raise Refusal("skill path escapes its plugin root")
                try:
                    provided_name = frontmatter_data(candidate.read_text(encoding="utf-8")).get(
                        "name", candidate.parent.name)
                except (OSError, yaml.YAMLError, InvalidProposal) as exc:
                    raise Refusal("unreadable plugin skill frontmatter") from exc
                if provided_name == skill:
                    providers.add(f"{name}@{market_name}")
    return sorted(providers)


def find_skill_creator(cli_value: Path | None) -> tuple[Path, str | None]:
    """(skill-creator's skill directory, its installed commit or None).

    `--skill-creator`, else `$SKILL_CREATOR_DIR`, else the installed bundle
    recorded in `~/.claude/plugins/installed_plugins.json`."""
    candidates: list[tuple[Path, str | None]] = []
    explicit = cli_value or (Path(os.environ["SKILL_CREATOR_DIR"])
                             if os.environ.get("SKILL_CREATOR_DIR") else None)
    if explicit:
        candidates.append((Path(explicit).expanduser(), None))
    else:
        record = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
        try:
            installs = json.loads(record.read_text(encoding="utf-8"))
            for entry in installs.get("plugins", {}).get(SKILL_CREATOR_PLUGIN_KEY, []):
                candidates.append((Path(entry["installPath"]) / SKILL_CREATOR_SUBDIR,
                                   entry.get("gitCommitSha")))
        except (OSError, ValueError, AttributeError, KeyError, TypeError):
            pass
    for path, sha in candidates:
        if (path / "scripts" / "run_loop.py").is_file():
            return path.resolve(), sha
    raise Refusal("skill-creator not found: install the plugin "
                  f"({SKILL_CREATOR_PLUGIN_KEY}) or pass --skill-creator DIR "
                  "(the directory holding scripts/run_loop.py)")


def arm_model(fixture: dict, no_judge: bool = True) -> str:
    """The model run_eval itself will pick for this fixture's agent."""
    ns = argparse.Namespace(model=None, roster=None, no_judge=no_judge)
    model, _, problem = run_eval.select_models(fixture, ns)
    if problem:
        raise Refusal(f"{problem}; configure a judge or pass --no-judge")
    mode = (fixture.get("judge") or {}).get("mode", "absolute")
    normalized = mode.strip().casefold() if isinstance(mode, str) else mode
    if not no_judge and normalized not in (None, "", "absolute"):
        raise Refusal(f"cannot drive judge mode {mode!r}; pass --no-judge")
    return model


def proposal_model() -> str:
    """The committed roster's judge: a model that is not an arm."""
    roster, problem = run_eval.read_roster(run_eval._resolve_roster(None))
    if problem:
        raise Refusal(problem)
    _, judge_id, _, _ = run_eval.roster_models(roster)
    if not judge_id:
        raise Refusal("the roster names no judge model for the proposal call")
    return judge_id


# ---------------------------------------------------------------------------
# Trigger half: skill-creator's description loop
# ---------------------------------------------------------------------------

def trigger_eval_set(skill: str, fixtures: dict, train: list[str],
                     validation: str, override: Path | None,
                     holdout: str | None = None) -> tuple[list[dict], str]:
    """skill-creator's `[{query, should_trigger}]` and where it came from.

    Default: the train fixtures' prompts should trigger; every OTHER skill's
    fixture prompts should not. `--trigger-eval-set` replaces it. Either way
    the validation fixture's prompt is dropped, so the description loop never
    trains on the fixture that decides acceptance."""
    held_out = {" ".join(str(fixtures[n].get("prompt", "")).split())
                for n in [validation] + ([holdout] if holdout else [])}
    if override:
        items = json.loads(override.read_text(encoding="utf-8"))
        source = f"file:{override.name}"
    else:
        items = [{"query": fixtures[name]["prompt"], "should_trigger": True}
                 for name in train]
        for path in sorted(EVALS_DIR.rglob(run_eval.FIXTURE_FILE)):
            other = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if (isinstance(other, dict) and other.get("skill")
                    and other.get("skill") != skill
                    and other.get("subject", "skill") == "skill"
                    and isinstance(other.get("prompt"), str)):
                items.append({"query": other["prompt"], "should_trigger": False})
        source = "fixtures"
    clean = []
    for item in items:
        query = " ".join(str(item.get("query", "")).split())
        if query and query not in held_out:
            clean.append({"query": query, "should_trigger": bool(item.get("should_trigger"))})
    if not any(i["should_trigger"] for i in clean) or all(i["should_trigger"] for i in clean):
        raise Refusal("the trigger eval set needs at least one should-trigger "
                      "and one should-not-trigger query")
    return clean, source


def description_loop_argv(eval_set_path: Path, skill_dir: Path, model: str,
                          out_dir: Path) -> list[str]:
    """skill-creator's documented invocation (SKILL.md "Description
    Optimization", step 3), with its defaults spelled out so the record says
    what ran, and its browser report switched off."""
    return ["--eval-set", str(eval_set_path), "--skill-path", str(skill_dir),
            "--model", model, "--max-iterations", "5", "--runs-per-query", "3",
            "--holdout", "0.4", "--report", "none", "--results-dir", str(out_dir)]


# ---------------------------------------------------------------------------
# SKILL.md editing
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str, str]:
    """(frontmatter block including both `---` lines, body)."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise InvalidProposal("SKILL.md has no frontmatter")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[:index + 1]), "".join(lines[index + 1:])
    raise InvalidProposal("SKILL.md frontmatter is not closed")


def frontmatter_data(text: str) -> dict:
    block, _ = split_frontmatter(text)
    inner = block.split("\n", 1)[1].rsplit("---", 1)[0]
    data = yaml.safe_load(inner)
    if not isinstance(data, dict):
        raise InvalidProposal("SKILL.md frontmatter is not a mapping")
    return data


def set_description(text: str, description: str) -> str:
    """`text` with only the frontmatter's `description:` value replaced.
    Written plain when YAML reads it back unchanged, else double-quoted."""
    if not description or len(description) > DESCRIPTION_MAX_CHARS:
        raise InvalidProposal(f"description must be 1..{DESCRIPTION_MAX_CHARS} characters")
    if any(unicodedata.category(char) == "Cc" and char not in "\t\n\r"
           for char in description):
        raise InvalidProposal("description contains a control character")
    block, body = split_frontmatter(text)
    lines = block.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.startswith("description:")), None)
    if start is None:
        raise InvalidProposal("SKILL.md frontmatter has no description")
    end = start + 1
    while end < len(lines) - 1 and lines[end][:1] in (" ", "\t"):
        end += 1
    flat = " ".join(description.split())
    rendered = None
    for candidate in (f"description: {flat}\n",
                      f"description: {json.dumps(flat, ensure_ascii=False)}\n"):
        try:
            if yaml.safe_load(candidate) == {"description": flat}:
                rendered = candidate
                break
        except yaml.YAMLError:
            continue
    if rendered is None:
        raise InvalidProposal("description cannot be rendered as YAML")
    new = "".join(lines[:start]) + rendered + "".join(lines[end:]) + body
    before, after = frontmatter_data(text), frontmatter_data(new)
    if after.get("description") != flat or {k: v for k, v in after.items() if k != "description"} \
            != {k: v for k, v in before.items() if k != "description"}:
        raise InvalidProposal("rewriting the description changed another frontmatter key")
    return new


def check_diff_targets(diff: str) -> None:
    """Every file header in `diff` must be `a/SKILL.md` / `b/SKILL.md`."""
    headers = 0
    for line in diff.splitlines():
        if line.startswith(("--- ", "+++ ")):
            path = line[4:].split("\t", 1)[0].strip()
            if path not in ("a/SKILL.md", "b/SKILL.md"):
                raise InvalidProposal(f"diff touches {path!r}; only SKILL.md may change")
            headers += 1
        elif line.startswith("diff --git ") and line.split()[2:] != ["a/SKILL.md", "b/SKILL.md"]:
            raise InvalidProposal(f"diff touches {line[11:]!r}; only SKILL.md may change")
        elif line.startswith(("rename ", "copy ", "new file", "deleted file",
                              "Binary files", "GIT binary patch", "old mode", "new mode")):
            raise InvalidProposal(f"diff carries a {line.split()[0]!r} header; "
                                  "only an in-place SKILL.md text edit is allowed")
    if headers == 0:
        raise InvalidProposal("diff has no file headers")


def apply_body_diff(text: str, diff: str, scratch: Path) -> str:
    """`text` (a SKILL.md) with `diff` applied, refusing any change to the
    frontmatter. The diff is applied by `git apply` in an empty scratch
    directory that git cannot mistake for part of a repository."""
    if not diff.strip():
        return text
    check_diff_targets(diff)
    work = scratch / "apply"
    work.mkdir(parents=True)
    (work / "SKILL.md").write_text(text, encoding="utf-8")
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(scratch))
    proc = subprocess.run(["git", "apply", "-p1", "--whitespace=nowarn", "-"],
                          cwd=work, input=diff if diff.endswith("\n") else diff + "\n",
                          capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0:
        raise InvalidProposal("diff does not apply to SKILL.md")
    unexpected = sorted(p.name for p in work.iterdir() if p.name != "SKILL.md")
    if unexpected:
        raise InvalidProposal(f"diff created {unexpected}; only SKILL.md may change")
    new = (work / "SKILL.md").read_text(encoding="utf-8")
    if split_frontmatter(new)[0] != split_frontmatter(text)[0]:
        raise InvalidProposal("diff touches the frontmatter: the name stays, and "
                              "the description is the trigger half's to change")
    return new


def registry_patch(old: str, new: str, rel_path: str) -> str:
    """A `git apply`-able patch against the registry, rooted at its top."""
    return "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}"))


# ---------------------------------------------------------------------------
# Body half: the proposal call
# ---------------------------------------------------------------------------

PROPOSAL_CONSTRAINTS = """\
Constraints (skills-evals#71):
- Change SKILL.md only. No other file, no new payload file, no rename.
- Leave the frontmatter (the --- block) byte for byte: the name is fixed, and
  the description is the trigger and is tuned separately.
- Fix the failures below by generalizing the instruction that would have
  prevented them; do not quote the fixture, its file names or its answers.
- Prefer the smallest edit that would plausibly fix the failures."""


def run_paths(results: Path, label: str, skill: str, ts: str, fixture: str) -> Path:
    return results / "runs" / label / skill / ts / fixture / ARM


def failure_evidence(arm_dir: Path) -> list[dict]:
    """Each trial's failed checks and the tail of its final reply."""
    trial_dirs = sorted(arm_dir.glob(f"{run_eval.TRIAL_DIR_PREFIX}*")) or [arm_dir]
    evidence = []
    for trial in trial_dirs:
        try:
            summary = json.loads((trial / "summary.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        failed = [{"id": c.get("id"), "detail": c.get("detail")}
                  for c in summary.get("objective_checks") or [] if not c.get("passed")]
        if not failed:
            continue
        reply = ""
        try:
            raw = json.loads((trial / "transcripts" / "raw.json").read_text(encoding="utf-8"))
            reply = str(raw.get("result", "")) if isinstance(raw, dict) else ""
        except (OSError, ValueError):
            pass
        evidence.append({"trial": trial.name, "failed_checks": failed,
                         "reply_tail": reply[-TRANSCRIPT_EXCERPT_CHARS:]})
    return evidence


def proposal_prompt(skill: str, skill_md: str, purpose: str | None,
                    evidence: dict[str, list[dict]], fixtures: dict) -> str:
    parts = [f"You are improving the agent skill `{skill}`. Its SKILL.md is "
             "measured by fixtures; with the skill installed, an agent still "
             "fails the checks below on the TRAINING fixtures.", "",
             PROPOSAL_CONSTRAINTS, ""]
    if purpose:
        parts += ["<purpose>", purpose.strip(), "</purpose>", ""]
    parts += ["<skill_md>", skill_md, "</skill_md>", ""]
    for name, items in evidence.items():
        parts += [f"<fixture name={json.dumps(name)}>",
                  f"Prompt: {fixtures[name].get('prompt', '').strip()}",
                  json.dumps(items, indent=2), "</fixture>", ""]
    parts += ['Answer with ONE JSON object and nothing else: {"rationale": '
              '"<why this edit fixes the failures>", "unified_diff": "<a unified '
              'diff with headers --- a/SKILL.md and +++ b/SKILL.md, or an empty '
              'string if no body edit is warranted>"}']
    return "\n".join(parts)


def parse_proposal(reply: str) -> dict:
    """`{rationale, unified_diff}` out of the reply: the first JSON object in
    it, tolerating a code fence around it."""
    start = reply.find("{")
    decoder = json.JSONDecoder()
    while start != -1:
        try:
            value, _ = decoder.raw_decode(reply, start)
        except json.JSONDecodeError:
            start = reply.find("{", start + 1)
            continue
        if (isinstance(value, dict) and isinstance(value.get("rationale"), str)
                and isinstance(value.get("unified_diff"), str)):
            return value
        start = reply.find("{", start + 1)
    raise InvalidProposal("proposal is not a {rationale, unified_diff} JSON object")


# ---------------------------------------------------------------------------
# Measurement and decision
# ---------------------------------------------------------------------------

def run_eval_argv(skill: str, registry_name: str, registry_root: Path,
                  results: Path, ts: str, trials: int, no_judge: bool) -> list[str]:
    argv = [str(EVALS_DIR / skill), "--arm", ARM, "--trials", str(trials),
            "--registry", f"{registry_name}={registry_root}",
            "--results-dir", str(results), "--timestamp", ts]
    return argv + (["--no-judge"] if no_judge else [])


def fixture_metrics(arm_dir: Path) -> dict:
    """One fixture's arm summary reduced to what the decision reads."""
    try:
        summary = json.loads((arm_dir / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"error": "no summary.json"}
    stats = summary if "aggregate" in summary else run_eval.aggregate_trials([summary])
    objective = stats["aggregate"]["objective"] or {}
    judge = (stats["aggregate"]["judge"] or {}).get("overall") or {}
    error = summary.get("error")
    return {"error": (error or {}).get("type") if error else None,
            "passed": objective.get("passed"), "total": objective.get("total"),
            "judge_mean": judge.get("mean"), "n": stats.get("n")}


def group_metrics(per_fixture: dict, names: list[str]) -> dict:
    rows = [per_fixture.get(n, {"error": "missing fixture"}) for n in names]
    errors = [n for n, r in zip(names, rows) if r.get("error") or not r.get("total")]
    passed = sum(r.get("passed") or 0 for r in rows)
    total = sum(r.get("total") or 0 for r in rows)
    judged = [r["judge_mean"] for r in rows if run_eval._is_number(r.get("judge_mean"))]
    return {"errors": errors, "passed": passed, "total": total,
            "pass_rate": passed / total if total else None,
            "judge_mean": (sum(judged) / len(judged)
                           if judged and len(judged) == len(rows) else None)}


def decide(baseline: dict, candidate: dict, train: list[str],
           validation: str, min_gain: float = DEFAULT_MIN_GAIN,
           holdout: str | None = None,
           judge_required: bool | set[str] = False) -> tuple[bool, list[str]]:
    """(accepted, reasons). Pure: reads the two per-fixture metric maps."""
    reasons = []
    b_train, c_train = group_metrics(baseline, train), group_metrics(candidate, train)
    b_val, c_val = group_metrics(baseline, [validation]), group_metrics(candidate, [validation])
    errored = sorted(set(b_train["errors"] + c_train["errors"]
                         + b_val["errors"] + c_val["errors"]))
    if errored:
        return False, [f"inconclusive: errored or unscored fixtures {errored}"]
    measured = train + [validation] + ([holdout] if holdout else [])
    required = (set(measured) if judge_required is True
                else set(judge_required) if judge_required else set())
    required.update(n for n in measured
                    if run_eval._is_number(baseline.get(n, {}).get("judge_mean")))
    missing_judge = [n for n in measured if n in required and any(
        not run_eval._is_number(metrics.get(n, {}).get("judge_mean"))
        for metrics in (baseline, candidate))]
    if missing_judge:
        return False, [f"inconclusive: missing expected judge scores {missing_judge}"]

    held = c_val["pass_rate"] >= b_val["pass_rate"]
    if not held:
        reasons.append(f"validation objective fell {b_val['pass_rate']:.3f} -> "
                       f"{c_val['pass_rate']:.3f}")
    if b_val["judge_mean"] is not None and c_val["judge_mean"] is not None \
            and c_val["judge_mean"] < b_val["judge_mean"] - JUDGE_TOLERANCE:
        held = False
        reasons.append(f"validation judge fell more than {JUDGE_TOLERANCE}: "
                       f"{b_val['judge_mean']:.2f} -> {c_val['judge_mean']:.2f}")

    if holdout:
        b_fixed = group_metrics(baseline, [holdout])
        c_fixed = group_metrics(candidate, [holdout])
        if b_fixed["errors"] or c_fixed["errors"]:
            return False, [f"inconclusive: errored or unscored holdout {holdout!r}"]
        if c_fixed["pass_rate"] < b_fixed["pass_rate"]:
            held = False
            reasons.append("holdout objective regressed")
        if b_fixed["judge_mean"] is not None and c_fixed["judge_mean"] is not None \
                and c_fixed["judge_mean"] < b_fixed["judge_mean"]:
            held = False
            reasons.append("holdout judge regressed (zero tolerance)")

    def meets_gain(gain: float) -> bool:
        return gain > 0 and (gain >= min_gain or math.isclose(
            gain, min_gain, rel_tol=0, abs_tol=1e-12))

    improved = meets_gain(c_train["pass_rate"] - b_train["pass_rate"])
    if c_train["pass_rate"] == b_train["pass_rate"] \
            and b_train["judge_mean"] is not None and c_train["judge_mean"] is not None:
        improved = meets_gain((c_train["judge_mean"] - b_train["judge_mean"]) / 10)
    if not improved:
        reasons.append(f"train did not meet minimum gain {min_gain:g}: "
                       f"objective {b_train['pass_rate']:.3f} -> "
                       f"{c_train['pass_rate']:.3f}")
    if held and improved:
        reasons.append("validation held and train improved")
    return held and improved, reasons


def table(baseline: dict, candidate: dict | None, train: list[str],
          validation: str, holdout: str | None = None) -> str:
    def cell(m: dict | None) -> tuple[str, str]:
        if not m:
            return "-", "-"
        if m.get("error") or not m.get("total"):
            return f"error ({m.get('error')})", "-"
        judge = m.get("judge_mean")
        return (f"{m['passed']}/{m['total']}",
                f"{judge:.2f}" if run_eval._is_number(judge) else "-")
    lines = ["| Fixture | Split | Baseline objective | Candidate objective "
             "| Baseline judge | Candidate judge |", "|---|---|---|---|---|---|"]
    for name in train + [validation] + ([holdout] if holdout else []):
        b_obj, b_judge = cell(baseline.get(name))
        c_obj, c_judge = cell((candidate or {}).get(name))
        split = "holdout" if name == holdout else "validation" if name == validation else "train"
        lines.append(f"| {name} | {split} | {b_obj} | {c_obj} | {b_judge} | {c_judge} |")
    return "\n".join(lines)


def pr_body(record: dict, rows: str) -> str:
    d, b = record["description_half"], record["body_half"]
    lines = [f"## Proposed `{record['skill']}` SKILL.md edit (validation-gated)", "",
             "Produced by skills-evals `scripts/propose_skill_edit.py` "
             "([#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71)). "
             "A local exhibit (skills-evals ADR 0002, decision 4): measured under "
             "the operator's own login, not badge input. Review before merging; "
             "nothing here merges itself.", "",
             f"- Registry: `{record['registry']['name']}` at `{record['registry']['sha']}`",
             f"- Split: train {', '.join(record['split']['train'])}; "
             f"validation {record['split']['validation']} "
             f"(rotation {record['split']['rotation']})",
             f"- Fixed holdout: {record['split'].get('holdout') or 'none'}; "
             f"minimum train gain: {record['min_gain']:g} (normalized 0..1)",
             f"- Trials per fixture: {record['trials']}, arm `{ARM}`, "
             f"agent model `{record['models']['arm']}`", "",
             "### Train / validation", "", rows, "",
             f"Decision: {'; '.join(record['reasons'])}.", ""]
    if d.get("changed"):
        lines += ["### Description (skill-creator `scripts/run_loop.py`)", "",
                  f"Held-out trigger score {d.get('best_test_score')}, train "
                  f"{d.get('best_train_score')}, query set from {d.get('eval_set_source')}.", "",
                  f"Before: {d['original']}", "", f"After: {d['best']}", ""]
    if b.get("unified_diff"):
        lines += ["### Body edit", "", b.get("rationale", ""), ""]
    lines += ["The patch is `" + record["files"]["patch"] + "`; apply it with "
              "`git apply` at the registry root."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------

def default_results_dir() -> Path:
    """Outside the repository: `$XDG_STATE_HOME/skills-evals`, else
    `~/.local/state/skills-evals`."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "skills-evals"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("skill")
    parser.add_argument("--registry", action="append", default=None,
                        help="registry checkout, NAME=PATH (as run_eval.py)")
    parser.add_argument("--ref", default="HEAD",
                        help="registry commit to archive (default HEAD)")
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    parser.add_argument("--rotation", type=int, default=None,
                        help="validation fixture index (default: records so far)")
    parser.add_argument("--min-gain", type=float, default=DEFAULT_MIN_GAIN,
                        help="minimum train gain on 0..1 scale (default .10; "
                             "objective rate or judge mean / 10 when objective is flat)")
    parser.add_argument("--holdout", default=None,
                        help="fixed nested fixture, never trained on; must not regress")
    parser.add_argument("--trigger-eval-set", type=Path, default=None,
                        help="skill-creator query set JSON (default: from fixtures)")
    parser.add_argument("--skill-creator", type=Path, default=None,
                        help="skill-creator's skill directory (holds scripts/run_loop.py)")
    parser.add_argument("--results-dir", type=Path, default=None)
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan; no model call, no write")
    args = parser.parse_args(argv)
    if not 1 <= args.trials <= run_eval.MAX_TRIALS:
        parser.error(f"--trials must be 1..{run_eval.MAX_TRIALS}")
    if args.rotation is not None and args.rotation < 0:
        parser.error("--rotation must be >= 0")
    if not math.isfinite(args.min_gain) or not 0 < args.min_gain <= 1:
        parser.error("--min-gain must be finite and greater than 0, at most 1")
    return args


def plan(args: argparse.Namespace) -> dict:
    """Everything decided before any model call. Reads, never writes."""
    skill = args.skill
    try:
        names = skill_fixtures(skill)
    except ValueError as exc:
        raise Refusal(str(exc)) from exc
    results = (args.results_dir or default_results_dir()).expanduser().resolve()
    records_dir = results / "improvements" / skill
    rotation = args.rotation if args.rotation is not None else default_rotation(records_dir)
    train, validation = split_fixtures(names, rotation, args.holdout)
    fixtures = load_fixtures(skill, names)
    if args.holdout:
        fixed_prompt = " ".join(str(fixtures[args.holdout].get("prompt", "")).split())
        if any(" ".join(str(fixtures[n].get("prompt", "")).split()) == fixed_prompt
               for n in train):
            raise Refusal("fixed --holdout needs a prompt distinct from every train fixture")
    models = {name: arm_model(fixture, args.no_judge) for name, fixture in fixtures.items()}
    url = next(iter(fixtures.values())).get("registry")
    try:
        registry = resolve_registry(url, args.registry)
    except ValueError as exc:
        raise Refusal(str(exc)) from exc
    sha = resolve_ref(registry["path"], args.ref)
    skill_creator, sc_sha = find_skill_creator(args.skill_creator)
    eval_set, source = trigger_eval_set(skill, fixtures, train, validation,
                                        args.trigger_eval_set, args.holdout)
    return {"skill": skill, "results": results, "records_dir": records_dir,
            "rotation": rotation, "train": train, "validation": validation,
            "holdout": args.holdout, "min_gain": args.min_gain,
            "fixtures": fixtures, "registry": registry, "sha": sha,
            "skill_creator": skill_creator, "skill_creator_sha": sc_sha,
            "eval_set": eval_set, "eval_set_source": source,
            "arm_model": models[train[0]],
            "proposal_model": proposal_model()}


def print_plan(p: dict, args: argparse.Namespace) -> None:
    n = len(p["fixtures"])
    per_run = n * args.trials * (1 if args.no_judge else 2)
    print(json.dumps({
        "skill": p["skill"], "rotation": p["rotation"], "train": p["train"],
        "validation": p["validation"],
        "holdout": p["holdout"], "min_gain": p["min_gain"],
        "registry": {"name": p["registry"]["name"], "sha": p["sha"]},
        "skill_creator": str(p["skill_creator"]),
        "trigger_eval_set": {"source": p["eval_set_source"], "size": len(p["eval_set"])},
        "models": {"arm": p["arm_model"], "proposal": p["proposal_model"]},
        "results_dir": str(p["results"]),
        "model_calls": {
            "run_eval_baseline": per_run, "run_eval_candidate": per_run,
            # 5 iterations x 3 runs per query, plus up to two proposer calls
            # (one more when a description overruns 1024 characters) for
            # each of the 4 improvements between them.
            "skill_creator_loop_at_most": 5 * 3 * len(p["eval_set"]) + 2 * 4,
            "proposal": 1},
    }, indent=2))


def improve(args: argparse.Namespace, runner: Runner, now: datetime) -> int:
    p = plan(args)
    if args.dry_run:
        print_plan(p, args)
        return EXIT_ACCEPTED
    skill, results, registry = p["skill"], p["results"], p["registry"]
    ts = now.astimezone(timezone.utc).strftime(run_eval.TIMESTAMP_FORMAT)
    names = p["train"] + [p["validation"]] + ([p["holdout"]] if p["holdout"] else [])
    p["records_dir"].mkdir(parents=True, exist_ok=True)
    stem = p["records_dir"] / ts
    if stem.with_suffix(".json").exists():
        raise Refusal(f"a record for {ts} already exists")

    scratch = Path(tempfile.mkdtemp(prefix="propose-skill-edit-"))
    try:
        base_root = archive_registry(registry["path"], p["sha"], scratch / "baseline")
        cand_root = archive_registry(registry["path"], p["sha"], scratch / "candidate")
        base_skill = find_skill_dir(base_root, registry["layout"], skill)
        cand_skill = find_skill_dir(cand_root, registry["layout"], skill)
        rel_path = base_skill.relative_to(base_root).as_posix() + "/SKILL.md"
        original = (base_skill / "SKILL.md").read_text(encoding="utf-8")
        disabled_plugins = skill_provider_plugins(base_root, skill)

        rc = runner.run_eval(run_eval_argv(skill, registry["name"], base_root,
                                           results / "runs" / "baseline", ts,
                                           args.trials, args.no_judge))
        if rc not in (0, 1):
            raise Refusal(f"baseline run_eval exited {rc}")
        baseline = {n: fixture_metrics(run_paths(results, "baseline", skill, ts, n))
                    for n in names}

        record = {
            "schema": 1, "skill": skill, "timestamp": ts,
            "local_exhibit": "skills-evals ADR 0002 decision 4: operator login, not badge input",
            "registry": {"name": registry["name"], "url": registry["url"],
                         "sha": p["sha"], "skill_md": rel_path},
            "split": {"rotation": p["rotation"], "train": p["train"],
                      "validation": p["validation"]},
            "trials": args.trials, "no_judge": args.no_judge,
            "min_gain": args.min_gain,
            "models": {"arm": p["arm_model"], "proposal": p["proposal_model"]},
            "baseline": baseline, "candidate": None,
            "runs": {"baseline": str(results / "runs" / "baseline" / skill / ts)},
            "files": {},
        }
        if p["holdout"]:
            record["split"]["holdout"] = p["holdout"]

        # Trigger half: skill-creator's loop, untouched.
        trigger_dir = results / "trigger" / skill / ts
        trigger_dir.mkdir(parents=True, exist_ok=True)
        eval_set_path = trigger_dir / "eval-set.json"
        eval_set_path.write_text(json.dumps(p["eval_set"], indent=2), encoding="utf-8")
        project = scratch / "trigger-project"
        (project / ".claude").mkdir(parents=True)
        (project / ".claude" / "settings.json").write_text(json.dumps({
            "enabledPlugins": {name: False for name in disabled_plugins}}, indent=2),
            encoding="utf-8")
        loop = runner.run_description_loop(
            description_loop_argv(eval_set_path, base_skill, p["arm_model"], trigger_dir),
            cwd=project, skill_creator=p["skill_creator"])
        (trigger_dir / "loop.json").write_text(json.dumps(loop, indent=2), encoding="utf-8")
        original_description = frontmatter_data(original).get("description", "")
        raw_best = str(loop.get("best_description") or "")
        best = " ".join(raw_best.split())
        record["description_half"] = {
            "from": "skill-creator scripts/run_loop.py",
            "skill_creator": {"path": str(p["skill_creator"]),
                              "commit": p["skill_creator_sha"]},
            "eval_set_source": p["eval_set_source"], "eval_set_size": len(p["eval_set"]),
            "disabled_plugins": disabled_plugins,
            "original": original_description, "best": best,
            "best_test_score": loop.get("best_test_score"),
            "best_train_score": loop.get("best_train_score"),
            "iterations": loop.get("iterations_run"),
            "changed": bool(best) and best != " ".join(str(original_description).split()),
            "loop_output": str(trigger_dir / "loop.json")}

        # Body half: one proposal call, validated before anything is measured.
        evidence = {n: failure_evidence(run_paths(results, "baseline", skill, ts, n))
                    for n in p["train"]}
        evidence = {n: e for n, e in evidence.items() if e}
        record["body_half"] = {"model": p["proposal_model"], "rationale": None,
                               "unified_diff": "", "error": None}
        candidate_text = original
        try:
            if evidence:
                purpose_path = base_skill / "PURPOSE.md"
                purpose = (purpose_path.read_text(encoding="utf-8")
                           if purpose_path.is_file() else None)
                proposal = parse_proposal(runner.propose(
                    proposal_prompt(skill, original, purpose, evidence, p["fixtures"]),
                    p["proposal_model"]))
                record["body_half"].update(rationale=proposal["rationale"],
                                           unified_diff=proposal["unified_diff"])
                candidate_text = apply_body_diff(original, proposal["unified_diff"], scratch)
            else:
                record["body_half"]["error"] = "no failed train check to learn from"
            if record["description_half"]["changed"]:
                candidate_text = set_description(candidate_text, raw_best)
        except InvalidProposal as exc:
            record.update(status="invalid-proposal", reasons=[str(exc)])
            write_record(stem, record)
            print(f"rejected before measurement: {exc}")
            return EXIT_REJECTED

        if candidate_text == original:
            record.update(status="no-candidate",
                          reasons=["neither half produced a change"])
            write_record(stem, record)
            print("no candidate: neither half produced a change")
            return EXIT_REJECTED

        patch = registry_patch(original, candidate_text, rel_path)
        stem.with_suffix(".patch").write_text(patch, encoding="utf-8")
        record["files"]["patch"] = str(stem.with_suffix(".patch"))
        (cand_skill / "SKILL.md").write_text(candidate_text, encoding="utf-8")

        rc = runner.run_eval(run_eval_argv(skill, registry["name"], cand_root,
                                           results / "runs" / "candidate", ts,
                                           args.trials, args.no_judge))
        if rc not in (0, 1):
            raise Refusal(f"candidate run_eval exited {rc}")
        candidate = {n: fixture_metrics(run_paths(results, "candidate", skill, ts, n))
                     for n in names}
        record["candidate"] = candidate
        record["runs"]["candidate"] = str(results / "runs" / "candidate" / skill / ts)

        accepted, reasons = decide(baseline, candidate, p["train"], p["validation"],
                                    args.min_gain, p["holdout"],
                                    {n for n in names if not args.no_judge
                                     and p["fixtures"][n].get("judge_rubric")})
        record.update(status="accepted" if accepted else "rejected", reasons=reasons)
        rows = table(baseline, candidate, p["train"], p["validation"], p["holdout"])
        record["table"] = rows
        if accepted:
            body_path = stem.with_name(stem.name + ".pr-body.md")
            record["files"]["pr_body"] = str(body_path)
            body_path.write_text(pr_body(record, rows), encoding="utf-8")
        write_record(stem, record)
        print(rows)
        print(f"{record['status']}: {'; '.join(reasons)}")
        print(f"record: {stem.with_suffix('.json')}")
        return EXIT_ACCEPTED if accepted else EXIT_REJECTED
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def write_record(stem: Path, record: dict) -> None:
    record["files"]["record"] = str(stem.with_suffix(".json"))
    stem.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n",
                                         encoding="utf-8")


def main(argv: list[str] | None = None, runner: Runner | None = None,
         now: datetime | None = None) -> int:
    args = parse_args(argv)
    try:
        return improve(args, runner or Runner(), now or datetime.now(timezone.utc))
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
