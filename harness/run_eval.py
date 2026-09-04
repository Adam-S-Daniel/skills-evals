#!/usr/bin/env python3
"""Run a skill eval fixture.

Usage:
    python3 harness/run_eval.py evals/<skill> --arm objective-only
    python3 harness/run_eval.py evals/<skill> --arm both [--registry PATH]
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


def _resolve_registry(cli_value: Path | None) -> Path:
    """agentskills checkout: --registry, else $AGENTSKILLS_DIR, else ~/repos/agentskills."""
    if cli_value:
        return Path(cli_value).expanduser()
    env = os.environ.get("AGENTSKILLS_DIR")
    if env:
        return Path(env).expanduser()
    return Path.home() / "repos" / "agentskills"


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
    if not path.is_file() or path.stat().st_size == 0:
        return None, f"no model roster at {path}"
    try:
        with open(path, encoding="utf-8") as f:
            document = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return None, f"model roster at {path} is unreadable ({type(exc).__name__})"
    if not isinstance(document, dict):
        return None, f"model roster at {path} is not a JSON object"
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
    the normal exit-2 path. A PINNED fixture never needs the roster and is
    unaffected: it still runs with no roster at all.

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


def run_agent(workspace: Path, prompt: str, arm: dict) -> dict:
    """Run the agent under test (the Claude Code CLI, headless) on the workspace.

    `arm` carries: name ("with_skill"/"without_skill"), skill + registry (Path,
    only for with_skill), optional model, optional timeout (default 600s),
    optional env (the fixture's `env:` mapping, see agent_env).

    This replaces the old `-> str` transcript stub with a richer dict. Success
    dicts have no "error" key and carry transcript/usage/cost_usd/num_turns/
    duration_ms/raw. Error dicts always have an "error" key — one of
    "skill_not_found", "timeout", "nonzero_exit", "invalid_json",
    "agent_error" — plus a "detail". Callers MUST check `"error" in result`
    rather than relying on exceptions; only skill installation and process
    invocation failures are turned into error dicts here, nothing is raised.
    """
    if arm["name"] == "with_skill":
        skill = arm["skill"]
        registry = arm["registry"]
        # The registry lays out skills as plugins/<bundle>/skills/<skill>/SKILL.md.
        # Historically <bundle> == <skill> (one skill per plugin); it's moving to
        # bundles that group several skills under one plugin dir, so <bundle> !=
        # <skill> in general. Glob for it rather than hardcoding the bundle name,
        # so both layouts resolve. Sorted so multiple matches pick deterministically.
        matches = sorted(p for p in (registry / "plugins").glob(f"*/skills/{skill}")
                         if p.is_dir())
        if not matches:
            pattern = registry / "plugins" / "*" / "skills" / skill
            return {"error": "skill_not_found",
                    "detail": f"no skill dir matched {pattern}"}
        skill_src = matches[0]
        shutil.copytree(skill_src, workspace / ".claude" / "skills" / skill)

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
    """Run git in `cwd` with a fixed local identity (don't rely on global config)."""
    return subprocess.run(
        ["git", "-c", "user.email=skills-evals@local",
         "-c", "user.name=skills-evals harness", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    )


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


def _run_arm(arm_name: str, fixture: dict, seed: Path, registry: Path,
            args: argparse.Namespace, timestamp: str,
            selection: tuple | None = None) -> dict:
    """Materialize a workspace, invoke the agent, score it, write results, clean up.

    `selection` is `select_models()`'s answer, resolved ONCE by main() and
    passed in: the roster is one file describing one run, and re-reading it per
    arm let two arms of the same run disagree if it changed underneath them.
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
        _git("init", "-q", cwd=workspace)
        _git("add", "-A", cwd=workspace)
        _git("commit", "-q", "-m", "seed", cwd=workspace)

        arm_config = {
            "name": arm_name,
            "model": agent_model,
            "timeout": args.timeout or fixture.get("timeout_s", 600),
            "env": fixture.get("env"),
        }
        if arm_name == "with_skill":
            arm_config["skill"] = fixture["skill"]
            arm_config["registry"] = registry

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
            objective_checks = objective.run_checks(
                fixture, str(workspace), str(seed), transcript=result.get("transcript"))

            if not args.no_judge:
                _git("add", "-A", cwd=workspace)
                diff = _git("diff", "--cached", "--", ".", ":!.claude", cwd=workspace).stdout
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
    parser.add_argument("--registry", type=Path, default=None,
                        help="agentskills checkout path (with_skill arm); "
                             "else $AGENTSKILLS_DIR, else ~/repos/agentskills")
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

    if args.arm == "objective-only":
        if args.workspace:
            workspace = args.workspace
            results = objective.run_checks(fixture, str(workspace), str(seed))
        else:
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp) / "ws"
                shutil.copytree(seed, workspace)
                results = objective.run_checks(fixture, str(workspace), str(seed))

        print(json.dumps({"skill": fixture["skill"], "arm": args.arm,
                          "checks": results}, indent=2))
        return 0 if all(r["passed"] for r in results) else 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arm_names = ["with_skill", "without_skill"] if args.arm == "both" else [args.arm]
    registry = _resolve_registry(args.registry)

    # Resolved once: one roster read, one model choice, both arms.
    selection = select_models(fixture, args)
    arm_summaries = [_run_arm(name, fixture, seed, registry, args, timestamp,
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
