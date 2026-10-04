#!/usr/bin/env python3
"""Run one skill fixture N times on this workstation: a LOCAL EXHIBIT.

ADR 0002 (docs/decisions/0002-runs-bill-the-api-org-not-the-subscription.md)
decision 4 keeps ad-hoc runs available "locally by the account holder under
their own `/login`", with the results "a local exhibit, not badge input". This
script is the safe way to make one. It drives the unmodified single-run
interface, `harness/run_eval.py <fixture> --arm <arm>`, once per trial; it does
not change how a run is scored.

Usage:

    python3 scripts/local_eval.py evals/<skill> --results-dir ~/evals-local/<name>
        [--trials 3] [--arm both|with_skill|without_skill] [--no-judge]
        [--registry NAME=PATH ...]

What it does, in order, and what it refuses (exit 2, nothing run):

1. Refuses when `CLAUDE_CODE_OAUTH_TOKEN` or any variable whose name begins
   `ANTHROPIC_` is SET in the environment (empty counts). `ANTHROPIC_API_KEY`
   and `ANTHROPIC_AUTH_TOKEN` bill API dollars, `CLAUDE_CODE_OAUTH_TOKEN` is a
   `setup-token` credential that must never sit in an arm's environment
   (`run_eval.agent_env` forwards every `ANTHROPIC_*`/`CLAUDE_*` name), and
   every other `ANTHROPIC_*` name re-routes, authenticates or re-models the
   CLI; a run under `/login` needs none of them.
2. Refuses a `--results-dir` that resolves (symlinks followed) inside this
   checkout, or inside any other git work tree or `.git` directory, or that
   already holds files:
   `results/` is not gitignored, so summaries written there would ride into a
   pull request.
3. Refuses a fixture that is not a skill fixture, whose `env:` block names a
   refused variable (run_eval applies that block last, so it would hand the
   variable back to every arm), whose models cannot be selected, or whose
   registry checkout is missing.
4. Records the harness identity in `<out>/manifest.json`: `claude --version`,
   the fixture's pinned models and the models `run_eval.select_models` picks,
   the UTC start time, and the git SHA (plus a dirty flag) of this checkout
   and of the registry checkout the fixture's `registry:` resolves to.
5. Contamination probe. Reads the CLI's `system/init` event
   (`harness/propagation/init_probe.py`; no model turn, the API endpoint is
   black-holed) in an EMPTY git repository, created under the same temp
   parent and name prefix `run_eval.materialize_workspace` uses for an arm,
   with the arms' own environment (`run_eval.agent_env`, the API endpoint
   overridden) and `--setting-sources project`. If the skill under
   test is already visible there — bare (`<skill>`) or namespaced
   (`<bundle>:<skill>`) — the run FAILS (exit 2) before any arm: a user-level
   copy would contaminate the without_skill arm. The visible skill list is
   recorded in the manifest either way.
6. Runs `--trials` trials (default 3). Trial k is
   `run_eval.py <fixture> --arm <arm> --results-dir <out>/t<k>` with every
   `--registry` passed through (relative paths resolved from YOUR cwd) and
   `--no-judge` when given; its output is kept in `<out>/t<k>/run_eval.log`.
   A trial that exits non-zero (2 is run_eval's runner error) is recorded in
   the manifest and counted in the aggregate's `errors`; it is never dropped.
7. Writes `<out>/aggregate.json`: per arm, `n` (trials), `errors`, per-check
   pass counts and `pass_rate`, the objective total's mean/min/max, the
   judge's `overall` and per-dimension mean/min/max when judged, and the
   agent cost's mean and sum. Errored arm-trials are excluded from every
   statistic and counted in `errors`.

Exit codes: 0 every trial ran clean; 1 at least one trial or arm errored (the
aggregate and manifest are still written); 2 refused before any trial ran.

What it never does: write inside the repository, touch the
`persistent/eval-results` branch, push, or copy a transcript. Each trial's
`transcripts/raw.json` stays where run_eval wrote it, under `<out>/t<k>/`; it
carries host paths and is LOCAL-ONLY, and the manifest lists those files and
says so.

Limits a reader must know:

- The judge is not isolated like the arms. `harness/scorers/judge.py`
  (`_run_judge_cli`) runs the CLI with no `--setting-sources`, no `env=` and
  no `cwd=`, so locally it loads this account's user settings, user memory
  and plugins, and the project memory of this checkout (run_eval runs from
  the repo root here, as in CI). Local judge scores may therefore not be
  comparable with CI's.
- The probe measures which SKILLS an empty workspace sees. It does not
  measure user memory, hooks or MCP servers, and it does not include the
  fixture's seed.
- On a workstation a `bypassPermissions` arm inherits the real `HOME`, where
  the account's own credentials live (ADR 0002, decision 4).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_DIR = REPO_ROOT / "harness"
RUN_EVAL = HARNESS_DIR / "run_eval.py"

sys.path.insert(0, str(HARNESS_DIR))
import guidance  # noqa: E402
import run_eval  # noqa: E402
from propagation import init_probe  # noqa: E402

EXHIBIT = "local — not badge input"

#: Refused when present in the environment at all. A PREFIX for the
#: `ANTHROPIC_` family (the CLI's credential, endpoint, header and model
#: overrides all live there, and new members arrive with CLI releases), and
#: the one `CLAUDE_` name that is a credential.
REFUSED_ENV_PREFIXES = ("ANTHROPIC_",)
REFUSED_ENV_NAMES = ("CLAUDE_CODE_OAUTH_TOKEN",)

ARMS = ("both", "with_skill", "without_skill")
MAX_TRIALS = 20

EXIT_OK = 0
EXIT_TRIAL_ERROR = 1
EXIT_REFUSED = 2

TRANSCRIPTS_NOTE = (
    "LOCAL-ONLY. Each raw.json is the CLI's full JSON result for one arm and "
    "carries host paths (workspace, HOME). This wrapper never copies them; do "
    "not commit, publish or attach them.")


class Refused(Exception):
    """A preflight refusal: printed, exit 2, no trial run."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def refused_env_names(environ) -> list[str]:
    """Every name in `environ` this wrapper refuses to run under."""
    return sorted(name for name in environ
                  if name in REFUSED_ENV_NAMES
                  or name.startswith(REFUSED_ENV_PREFIXES))


def _git_env() -> dict:
    """The caller's environment without GIT_* overrides, so `git -C <dir>`
    answers about <dir> and not about a GIT_DIR the caller exported."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True,
                          text=True, env=_git_env(), timeout=60)


def git_identity(path: Path) -> dict:
    """{"sha", "dirty"} of the checkout at `path`; both null when it is not a
    git checkout (an extracted archive, say)."""
    head = _git(path, "rev-parse", "HEAD")
    if head.returncode != 0:
        return {"sha": None, "dirty": None}
    status = _git(path, "status", "--porcelain")
    return {"sha": head.stdout.strip(),
            "dirty": bool(status.stdout.strip()) if status.returncode == 0 else None}


def check_results_dir(out: Path) -> Path:
    """The resolved results dir, or Refused."""
    resolved = out.expanduser().resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise Refused(
            f"--results-dir resolves inside this checkout ({REPO_ROOT}); "
            "results/ is not gitignored, so summaries would ride into a pull "
            "request. Pick a directory outside every repository.")
    existing = resolved
    while not existing.exists():
        existing = existing.parent
    if existing.is_dir():
        # --absolute-git-dir answers inside a work tree, inside a .git
        # directory and in a bare repository alike; --show-toplevel does not.
        repo = _git(existing, "rev-parse", "--absolute-git-dir")
        if repo.returncode == 0:
            raise Refused(
                f"--results-dir resolves inside the git work tree or git "
                f"directory {repo.stdout.strip()}; pick a directory outside "
                "every repository.")
    if resolved.exists() and (not resolved.is_dir() or any(resolved.iterdir())):
        raise Refused(
            f"--results-dir {resolved} already exists and is not an empty "
            "directory; trials from two runs must not mix.")
    return resolved


def _absolute_registry_flags(values: list[str] | None) -> list[str]:
    """--registry NAME=PATH flags with PATH made absolute from the CALLER's
    cwd: run_eval runs from the repo root, where a relative path would name a
    different directory."""
    try:
        parsed = run_eval._parse_registry_flags(values)
    except ValueError as exc:
        raise Refused(f"registry configuration error: {exc}") from exc
    return [f"{name}={Path(path).expanduser().resolve()}"
            for name, path in parsed.items()]


def load_skill_fixture(eval_dir: Path) -> dict:
    try:
        fixture = run_eval.load_fixture(eval_dir)
        run_eval.validate_mapping_keys(fixture, eval_dir / "fixture.yaml")
        run_eval.validate_timeouts(fixture, eval_dir / "fixture.yaml")
    except (OSError, guidance.GuidanceError) as exc:
        raise Refused(f"fixture configuration error: {exc}") from exc
    subject = fixture.get("subject", "skill")
    if subject != "skill":
        raise Refused(f"{eval_dir} is a {subject!r} fixture; this wrapper runs "
                      "skill fixtures only")
    for key in ("skill", "prompt"):
        if not isinstance(fixture.get(key), str) or not fixture[key]:
            raise Refused(f"{eval_dir / 'fixture.yaml'}: `{key}:` must be a "
                          "non-empty string")
    try:
        run_eval._validate_skill_name(fixture["skill"])
    except ValueError as exc:
        raise Refused(f"invalid fixture: {exc}") from exc
    # run_eval.agent_env applies the fixture's `env:` block LAST, so a fixture
    # naming one of the refused variables would hand it back to every arm.
    env_block = fixture.get("env")
    named = refused_env_names([str(k) for k in env_block]
                              if isinstance(env_block, dict) else [])
    if named:
        raise Refused(f"{eval_dir / 'fixture.yaml'}: `env:` names "
                      f"{', '.join(named)}, which this wrapper refuses to put "
                      "in an arm's environment")
    return fixture


def resolve_fixture_registry(fixture: dict, registry_flags: list[str],
                             needed: bool) -> dict | None:
    """The registries.yml entry the fixture's `registry:` names, resolved the
    way run_eval resolves it, or None when no arm installs the skill."""
    try:
        registries = run_eval.resolve_registries(
            registry_flags, os.environ.get("SKILLS_EVALS_REGISTRIES"),
            REPO_ROOT, os.environ.get("AGENTSKILLS_DIR"))
        run_eval._validate_registry_paths(registries)
    except ValueError as exc:
        raise Refused(f"registry configuration error: {exc}") from exc
    if not needed:
        return None
    url = fixture.get("registry")
    if not isinstance(url, str) or not url:
        raise Refused("the fixture has no `registry:` string")
    try:
        entry = run_eval.registry_for_url(registries, url)
    except ValueError as exc:
        raise Refused(f"registry configuration error: {exc}") from exc
    if not entry["path"].is_dir():
        raise Refused(f"registry {entry['name']!r} ({entry['source']}) has no "
                      "checkout; pass --registry "
                      f"{entry['name']}=PATH")
    return entry


def select_models(fixture: dict, no_judge: bool) -> dict:
    agent, judge_model, problem = run_eval.select_models(
        fixture, argparse.Namespace(model=None, roster=None, no_judge=no_judge))
    if problem:
        raise Refused(f"model selection: {problem}")
    return {"agent": agent, "judge": None if no_judge else judge_model}


def visible_copies(skills: list, skill: str) -> list[str]:
    """Entries of the init event's `skills` that ARE `skill`: the bare name,
    or any `<namespace>:<skill>`."""
    return [s for s in skills
            if isinstance(s, str) and s.rsplit(":", 1)[-1] == skill]


def contamination_probe(fixture: dict) -> dict:
    """What an arm's session sees before the seed: the skill list of an empty
    workspace under the arms' own environment and `--setting-sources
    project`. Raises init_probe.ProbeError when the CLI cannot be observed."""
    workspace = Path(tempfile.mkdtemp(prefix=run_eval.WORKSPACE_PREFIX))
    try:
        run_eval._git("init", "-q", cwd=workspace)
        env = run_eval.agent_env(workspace, fixture.get("env"))
        env["ANTHROPIC_BASE_URL"] = init_probe.BLACKHOLE_BASE_URL
        facts = init_probe.probe(
            cwd=workspace, home=Path(env.get("HOME") or Path.home()),
            tmpdir=Path(env.get("TMPDIR") or tempfile.gettempdir()),
            env_extra=env, extra_argv=("--setting-sources", "project"),
            allow_scope_flags=True)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    copies = visible_copies(facts.skills, fixture["skill"])
    return {
        "setting_sources": "project",
        "workspace": "empty git repository, same temp parent and prefix as an arm's",
        "claude_code_version": facts.version,
        "api_key_source": facts.init.get("apiKeySource"),
        "visible_skills": facts.skills,
        "plugins": [p.get("name") for p in facts.plugins if isinstance(p, dict)],
        "skill_under_test_copies": copies,
        "skill_under_test_visible": bool(copies),
    }


# ---------------------------------------------------------------------------
# aggregation


def _stats(values: list) -> dict | None:
    if not values:
        return None
    return {"n": len(values), "mean": sum(values) / len(values),
            "min": min(values), "max": max(values)}


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def read_arm_summary(trial_dir: Path, skill: str, arm: str):
    """(summary, None) or (None, problem) for one arm of one trial."""
    paths = sorted(trial_dir.glob(f"{skill}/*/{arm}/summary.json"))
    if len(paths) != 1:
        return None, f"expected one {arm}/summary.json, found {len(paths)}"
    try:
        summary = json.loads(paths[0].read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"unreadable summary.json ({type(exc).__name__})"
    if not isinstance(summary, dict):
        return None, "summary.json is not a mapping"
    return summary, None


def aggregate_arm(records: list) -> dict:
    """`records`: [(trial k, summary or None, problem or None)] for one arm."""
    error_trials, scored = [], []
    for k, summary, problem in records:
        if summary is None:
            error_trials.append({"trial": k, "error": problem})
        elif summary.get("error"):
            err = summary["error"]
            error_trials.append({"trial": k, "error": err.get("type")
                                 if isinstance(err, dict) else str(err)})
        else:
            scored.append(summary)

    checks: dict = {}
    totals, check_counts = [], set()
    overall, dims, costs = [], {}, []
    judge_errors = judged = 0
    models, judge_models = set(), set()
    for summary in scored:
        results = summary.get("objective_checks")
        if isinstance(results, list):
            check_counts.add(len(results))
            totals.append(sum(1 for c in results
                              if isinstance(c, dict) and c.get("passed") is True))
            for c in results:
                if not isinstance(c, dict):
                    continue
                entry = checks.setdefault(str(c.get("id")), {"passed": 0, "n": 0})
                entry["n"] += 1
                entry["passed"] += 1 if c.get("passed") is True else 0
        jd = summary.get("judge")
        if isinstance(jd, dict):
            if _number(jd.get("overall")):
                judged += 1
                overall.append(jd["overall"])
                for d in jd.get("dimensions") or []:
                    if isinstance(d, dict) and _number(d.get("score")):
                        dims.setdefault(str(d.get("name")), []).append(d["score"])
            elif "error" in jd:
                judge_errors += 1
        cost = (summary.get("agent") or {}).get("cost_usd")
        if _number(cost):
            costs.append(cost)
        models.update(m for m in summary.get("models_used") or []
                      if isinstance(m, str))
        judge_models.update(m for m in summary.get("judge_models_used") or []
                            if isinstance(m, str))
    for entry in checks.values():
        entry["pass_rate"] = entry["passed"] / entry["n"]

    return {
        "n": len(records),
        "errors": len(error_trials),
        "error_trials": error_trials,
        "scored": len(scored),
        "objective": {
            "checks": dict(sorted(checks.items())),
            "total": _stats(totals),
            "checks_per_trial": sorted(check_counts),
        },
        "judge": None if not (judged or judge_errors) else {
            "overall": _stats(overall),
            "dimensions": {name: _stats(v) for name, v in sorted(dims.items())},
            "errors": judge_errors,
        },
        "cost_usd": None if not costs else {
            "n": len(costs), "mean": sum(costs) / len(costs), "sum": sum(costs)},
        "models_used": sorted(models),
        "judge_models_used": sorted(judge_models),
    }


def arm_names(arm: str) -> list[str]:
    return ["with_skill", "without_skill"] if arm == "both" else [arm]


def build_aggregate(out: Path, skill: str, arms: list[str], trials: int) -> dict:
    per_arm = {}
    for arm in arms:
        records = []
        for k in range(1, trials + 1):
            summary, problem = read_arm_summary(out / f"t{k}", skill, arm)
            records.append((k, summary, problem))
        per_arm[arm] = aggregate_arm(records)
    return {"exhibit": EXHIBIT, "skill": skill, "trials": trials, "arms": per_arm}


def transcript_files(out: Path) -> list[str]:
    return sorted(p.relative_to(out).as_posix()
                  for p in out.glob("t*/**/transcripts/raw.json"))


# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: dict) -> None:
    staged = path.with_name(path.name + ".partial")
    staged.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    staged.replace(path)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="scripts/local_eval.py",
        description=__doc__.split("\n\n", 1)[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("eval_dir", type=Path, help="a skill fixture, evals/<skill>")
    parser.add_argument("--results-dir", type=Path, required=True,
                        help="where trials, aggregate.json and manifest.json "
                             "go; outside every repository, empty or absent")
    parser.add_argument("--trials", type=int, default=3,
                        help=f"number of trials, 1..{MAX_TRIALS} (default 3)")
    parser.add_argument("--arm", default="both", choices=ARMS,
                        help="passed to run_eval.py (default both)")
    parser.add_argument("--no-judge", action="store_true",
                        help="passed to run_eval.py")
    parser.add_argument("--registry", action="append", default=None,
                        help="passed to run_eval.py, repeatable: NAME=PATH")
    args = parser.parse_args(argv)
    if not 1 <= args.trials <= MAX_TRIALS:
        parser.error(f"--trials must be 1..{MAX_TRIALS}, got {args.trials}")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        refused = refused_env_names(os.environ)
        if refused:
            raise Refused(
                "refusing to run with " + ", ".join(refused) + " set: a local "
                "exhibit runs under your own /login, and these bill API "
                "dollars, re-route the CLI, or put a credential in reach of "
                "the arms. Unset them (e.g. `env -u NAME ...`) and re-run.")
        out = check_results_dir(args.results_dir)
        eval_dir = args.eval_dir.expanduser().resolve()
        fixture = load_skill_fixture(eval_dir)
        registry_flags = _absolute_registry_flags(args.registry)
        arms = arm_names(args.arm)
        registry = resolve_fixture_registry(fixture, registry_flags,
                                            needed="with_skill" in arms)
        models = select_models(fixture, args.no_judge)
    except Refused as exc:
        print(f"local_eval: {exc}", file=sys.stderr)
        return EXIT_REFUSED

    skill = fixture["skill"]
    judge_cfg = fixture.get("judge") if isinstance(fixture.get("judge"), dict) else {}
    manifest = {
        "exhibit": EXHIBIT,
        "status": "running",
        "started_at": _utc_now(),
        "fixture": (eval_dir.relative_to(REPO_ROOT).as_posix()
                    if REPO_ROOT in eval_dir.parents else str(eval_dir)),
        "skill": skill,
        "invocation": {"trials": args.trials, "arm": args.arm,
                       "no_judge": args.no_judge,
                       "registries": [f.split("=", 1)[0] for f in registry_flags]},
        "harness": {"claude_version": run_eval.claude_version()},
        "models": {"fixture_pins": {"model": fixture.get("model"),
                                    "judge_model": (judge_cfg or {}).get("model")},
                   "selected": models},
        "skills_evals": git_identity(REPO_ROOT),
        "registry": None if registry is None else {
            "name": registry["name"], "source": registry["source"],
            **git_identity(registry["path"])},
        "contamination_probe": None,
        "trials": [],
        "transcripts": {"local_only": True, "note": TRANSCRIPTS_NOTE, "files": []},
        "publishing": "none: this wrapper writes only under the results dir, "
                      "never inside a repository, never to "
                      "persistent/eval-results, and never pushes",
    }
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    _write_json(manifest_path, manifest)

    try:
        probe = contamination_probe(fixture)
    except (init_probe.ProbeError, guidance.GuidanceError, OSError,
            subprocess.SubprocessError) as exc:
        manifest["status"] = "refused: the contamination probe could not observe the CLI"
        manifest["contamination_probe"] = {"error": str(exc)}
        _write_json(manifest_path, manifest)
        print(f"local_eval: contamination probe failed, nothing run: {exc}",
              file=sys.stderr)
        return EXIT_REFUSED
    manifest["contamination_probe"] = probe
    if probe["skill_under_test_visible"]:
        manifest["status"] = "refused: the skill under test is already visible"
        _write_json(manifest_path, manifest)
        print(f"local_eval: {skill!r} is already visible to an empty workspace "
              f"under --setting-sources project, as "
              f"{', '.join(probe['skill_under_test_copies'])}: the without_skill "
              "arm would be contaminated. Nothing run; see "
              f"{manifest_path}.", file=sys.stderr)
        return EXIT_REFUSED
    _write_json(manifest_path, manifest)

    for k in range(1, args.trials + 1):
        trial_dir = out / f"t{k}"
        trial_dir.mkdir()
        cmd = [sys.executable, str(RUN_EVAL), str(eval_dir), "--arm", args.arm,
               "--results-dir", str(trial_dir)]
        for flag in registry_flags:
            cmd += ["--registry", flag]
        if args.no_judge:
            cmd.append("--no-judge")
        print(f"local_eval: trial {k}/{args.trials}", flush=True)
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True,
                              text=True)
        (trial_dir / "run_eval.log").write_text(
            (proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
        sys.stdout.write(proc.stdout or "")
        sys.stderr.write(proc.stderr or "")
        manifest["trials"].append({
            "trial": k, "results_dir": f"t{k}", "exit_code": proc.returncode,
            "error": None if proc.returncode == 0
            else f"run_eval.py exited {proc.returncode}; see t{k}/run_eval.log"})
        _write_json(manifest_path, manifest)

    aggregate = build_aggregate(out, skill, arms, args.trials)
    _write_json(out / "aggregate.json", aggregate)

    errored = (any(t["exit_code"] != 0 for t in manifest["trials"])
               or any(a["errors"] for a in aggregate["arms"].values()))
    manifest["status"] = "completed with errors" if errored else "completed"
    manifest["finished_at"] = _utc_now()
    manifest["transcripts"]["files"] = transcript_files(out)
    _write_json(manifest_path, manifest)
    for arm, stats in aggregate["arms"].items():
        total = stats["objective"]["total"]
        judge_overall = (stats["judge"] or {}).get("overall")
        print(f"local_eval: {arm}: n={stats['n']} errors={stats['errors']} "
              f"objective mean={total['mean'] if total else '-'} "
              f"judge mean={judge_overall['mean'] if judge_overall else '-'}")
    print(f"local_eval: wrote {out / 'aggregate.json'} and {manifest_path} "
          f"({EXHIBIT})")
    return EXIT_TRIAL_ERROR if errored else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
