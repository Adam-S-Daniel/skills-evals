#!/usr/bin/env python3
"""Run a skill eval fixture.

Usage:
    python3 harness/run_eval.py evals/<skill> --arm objective-only
    python3 harness/run_eval.py evals/<skill> --arm both [--registry PATH] [--no-judge]

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


REGISTRIES_YML = Path(__file__).parent / "registries.yml"


def _load_registries_config() -> list[dict]:
    """harness/registries.yml: [{name, url, layout}, ...] — this harness's own
    record of registry name/URL/layout, kept in step by hand with agentskills'
    scripts/skills_registries.yml (see test/run_tests.py::TestIssue63) rather
    than importing that file at run time: this harness must resolve using
    only its own checkout plus the registry under test.
    """
    with open(REGISTRIES_YML, encoding="utf-8") as f:
        return yaml.safe_load(f)["registries"]


def _parse_registry_flags(values: list[str] | None) -> dict[str, str]:
    """Repeatable --registry NAME=PATH entries. A bare PATH (no "=") is the
    pre-#63 single-path form and is taken as the agentskills entry, so the
    legacy invocation (`--registry ../agentskills`) keeps working unchanged.
    """
    out: dict[str, str] = {}
    for value in values or []:
        name, sep, path = value.partition("=")
        if sep:
            out[name] = path
        else:
            out["agentskills"] = value
    return out


def _parse_registry_env(value: str | None) -> dict[str, str]:
    """$SKILLS_EVALS_REGISTRIES: the same NAME=PATH shape, comma-separated."""
    out: dict[str, str] = {}
    for item in (value or "").split(","):
        item = item.strip()
        if not item:
            continue
        name, sep, path = item.partition("=")
        if sep:
            out[name] = path
    return out


def resolve_registries(cli_values: list[str] | None, env_value: str | None,
                       base_dir: Path) -> dict[str, dict]:
    """Map every registry named in harness/registries.yml to a local checkout.

    Sources, in order: a --registry NAME=PATH flag (repeatable; a bare PATH
    means agentskills), then $SKILLS_EVALS_REGISTRIES (same shape), then
    $AGENTSKILLS_DIR for the agentskills entry specifically (the harness's
    pre-#63 override), then a sibling-directory default `../<name>` next to
    `base_dir` — the same convention agentskills' own skills_registries.yml
    uses for the registries it doesn't live in.
    """
    overrides = {**_parse_registry_env(env_value), **_parse_registry_flags(cli_values)}
    resolved = {}
    for entry in _load_registries_config():
        name = entry["name"]
        if name in overrides:
            path = Path(overrides[name]).expanduser()
        elif name == "agentskills" and os.environ.get("AGENTSKILLS_DIR"):
            path = Path(os.environ["AGENTSKILLS_DIR"]).expanduser()
        else:
            path = (base_dir / ".." / name).resolve()
        resolved[name] = {"path": path, "layout": entry["layout"], "url": entry["url"]}
    return resolved


def registry_for_url(registries: dict[str, dict], url: str) -> dict:
    """The registries.yml entry (path + layout) whose url matches a fixture's
    `registry:` field. Raises with a message naming harness/registries.yml —
    the file to edit — rather than failing silently or crashing deep inside
    a glob.
    """
    for entry in registries.values():
        if entry["url"].rstrip("/") == url.rstrip("/"):
            return entry
    known = ", ".join(sorted(registries)) or "(none configured)"
    raise ValueError(
        f"unknown registry {url!r} — not listed in harness/registries.yml "
        f"(known registries: {known})")


def _skill_dir_glob(layout: str, skill: str) -> str:
    """Substitute `skill` for the skill-name placeholder in a registries.yml
    `layout` glob (its final path segment, immediately before `SKILL.md`),
    leaving any earlier `*` (a bundle/plugin wildcard) untouched.
    """
    parts = layout.split("/")
    if len(parts) < 2 or parts[-1] != "SKILL.md" or parts[-2] != "*":
        raise ValueError(f"registries.yml layout {layout!r} must end in '*/SKILL.md'")
    parts = parts[:-1]
    parts[-1] = skill
    return "/".join(parts)


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
        # Registry layouts vary (agentskills' plugins/<bundle>/skills/<skill>/,
        # cms-platform's flat skills/<skill>/, adamdaniel.ai's
        # .claude/skills/<skill>/ — see harness/registries.yml). `layout`
        # carries the glob for the registry under test, defaulting to
        # agentskills' shape for callers that predate #63. Sorted so multiple
        # matches pick deterministically.
        layout = arm.get("layout", "plugins/*/skills/*/SKILL.md")
        skill_glob = _skill_dir_glob(layout, skill)
        matches = sorted(p for p in registry.glob(skill_glob) if p.is_dir())
        if not matches:
            pattern = registry / skill_glob
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


def _run_arm(arm_name: str, fixture: dict, seed: Path, registries: dict[str, dict],
            args: argparse.Namespace, timestamp: str) -> dict:
    """Materialize a workspace, invoke the agent, score it, write results, clean up."""
    workspace = Path(tempfile.mkdtemp(prefix=f"skills-evals-{arm_name}-"))
    try:
        shutil.copytree(seed, workspace, dirs_exist_ok=True)
        _git("init", "-q", cwd=workspace)
        _git("add", "-A", cwd=workspace)
        _git("commit", "-q", "-m", "seed", cwd=workspace)

        arm_config = {
            "name": arm_name,
            "model": args.model or fixture.get("model"),
            "timeout": args.timeout or fixture.get("timeout_s", 600),
            "env": fixture.get("env"),
        }
        if arm_name == "with_skill":
            arm_config["skill"] = fixture["skill"]
            entry = registry_for_url(registries, fixture["registry"])
            arm_config["registry"] = entry["path"]
            arm_config["layout"] = entry["layout"]

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
                             "as the agentskills entry; else $SKILLS_EVALS_REGISTRIES "
                             "(same NAME=PATH,NAME=PATH shape), else $AGENTSKILLS_DIR "
                             "for agentskills specifically, else a sibling checkout "
                             "../<name> next to this repo")
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
    registries = resolve_registries(args.registry, os.environ.get("SKILLS_EVALS_REGISTRIES"),
                                    Path(__file__).resolve().parent.parent)

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
