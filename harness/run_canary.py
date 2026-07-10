#!/usr/bin/env python3
"""Run the guidance-bridge canary against the real Claude Code CLI.

Verifies that the fleet's guidance-bridge pattern — a CLAUDE.md containing an
`@AGENTS.md` import line — still gets expanded by Claude Code's memory loader,
by probing each layout in evals/guidance-bridge-canary/layouts/ for a
per-layout magic token and checking whether it shows up in a tool-free reply.

This needs real API access (it spawns the real `claude` CLI, not a stub), so
it is run on demand or on a schedule like real eval runs — it is NOT part of
the hermetic test suite (test/run_tests.py exercises this runner against
test/fake-claude only) and is NOT run in CI.

Usage:
    python3 harness/run_canary.py evals/guidance-bridge-canary
    python3 harness/run_canary.py evals/guidance-bridge-canary --subagent \
      [--model M] [--timeout N] [--results-dir results]

Exit codes: 0 all layouts behaved as expected; 1 an expectation mismatch (see
per-layout diagnostics printed to stdout); 2 a runner-level error (CLI
invocation failed for at least one leg).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_fixture(eval_dir: Path) -> dict:
    with open(eval_dir / "fixture.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def claude_version() -> str:
    """Record the CLI version under test; "unknown" if it can't be determined."""
    try:
        result = subprocess.run(
            [os.environ.get("CLAUDE_BIN", "claude"), "--version"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: BLE001 — record "unknown", never crash the run
        pass
    return "unknown"


def run_leg(workspace: Path, prompt: str, disallowed_tools: str, *,
           model: str | None, timeout: int) -> dict:
    """Invoke the CLI once against a seeded workspace.

    Mirrors run_eval.run_agent's error-dict pattern: callers must check
    `"error" in result` rather than relying on exceptions. Success dicts carry
    "reply" (the agent's final text, possibly empty).
    """
    # Unlike run_eval, no --permission-mode bypassPermissions: the probe must
    # not use tools at all (read tools are explicitly disallowed), so the
    # default deny-without-a-prompter headless behavior is the safer choice —
    # and bypassPermissions is refused outright when running as root.
    cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p", prompt,
          "--output-format", "json",
          "--setting-sources", "project", "--disallowedTools", disallowed_tools]
    if model:
        cmd += ["--model", model]

    try:
        result = subprocess.run(cmd, cwd=workspace, capture_output=True,
                                text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "detail": f"agent timed out after {timeout}s"}

    if result.returncode != 0:
        return {"error": "nonzero_exit",
                "detail": result.stderr.strip() or result.stdout.strip(),
                "returncode": result.returncode}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"error": "invalid_json", "detail": f"{result.stdout[:500]!r}: {e}"}

    if data.get("is_error"):
        return {"error": "agent_error", "detail": data.get("result", ""), "raw": data}

    return {"reply": data.get("result") or ""}


def _build_legs(fixture: dict, eval_dir: Path, use_subagent: bool) -> list[dict]:
    """One leg per layout, plus an optional bridge-subagent leg."""
    layouts_dir = eval_dir / "layouts"
    legs = [
        {
            "name": layout["name"],
            "expect": layout["expect"],
            "token": layout["token"],
            "prompt": fixture["prompt"],
            "disallowed_tools": fixture["disallowed_tools"],
            "layout_dir": layouts_dir / layout["name"],
        }
        for layout in fixture["layouts"]
    ]
    if use_subagent:
        bridge = next(layout for layout in fixture["layouts"] if layout["name"] == "bridge")
        # Catches regressions in subagent memory passing: same bridge layout
        # and token, but the probe itself launches a Task subagent.
        legs.append({
            "name": "bridge-subagent",
            "expect": bridge["expect"],
            "token": bridge["token"],
            "prompt": fixture["subagent_prompt"],
            "disallowed_tools": fixture["subagent_disallowed_tools"],
            "layout_dir": layouts_dir / "bridge",
        })
    return legs


def _run_leg(leg: dict, model: str | None, timeout: int) -> dict:
    """Materialize a fresh workspace from the leg's layout, probe it, clean up."""
    workspace = Path(tempfile.mkdtemp(prefix=f"guidance-bridge-canary-{leg['name']}-"))
    try:
        shutil.copytree(leg["layout_dir"], workspace, dirs_exist_ok=True)
        result = run_leg(workspace, leg["prompt"], leg["disallowed_tools"],
                         model=model, timeout=timeout)

        if "error" in result:
            return {"name": leg["name"], "expect": leg["expect"], "token": leg["token"],
                    "visible": None, "passed": False, "reply": "",
                    "error": {"type": result["error"], "detail": result.get("detail", "")}}

        reply = result["reply"]
        visible = leg["token"] in reply
        passed = visible == (leg["expect"] == "visible")
        return {"name": leg["name"], "expect": leg["expect"], "token": leg["token"],
                "visible": visible, "passed": passed, "reply": reply, "error": None}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _failure_hint(leg: dict) -> str:
    name = leg["name"]
    if name == "bridge":
        return ("import bridge may have regressed in this CLI version — check the "
                "upstream import-regression history and anthropics/claude-code#6235; "
                "see README \"Guidance-bridge canary\".")
    if name == "bridge-subagent":
        return "subagent memory passing may have regressed (as reported upstream Feb-May 2026)."
    hint = ("either the probe's tool controls broke or native AGENTS.md support shipped "
           "(anthropics/claude-code#6235) — a signal to simplify the fleet, not a failure "
           "of it")
    if name == "fence":
        hint += "; for fence specifically: fenced-import expansion behavior changed."
    else:
        hint += "."
    return hint


def _print_leg(leg: dict) -> None:
    if leg["error"]:
        print(f"ERROR {leg['name']}: {leg['error']['type']}: {leg['error']['detail']}")
        return
    status = "visible" if leg["visible"] else "invisible"
    if leg["passed"]:
        print(f"PASS {leg['name']} (expected {leg['expect']}, token {status})")
    else:
        print(f"FAIL {leg['name']} (token {leg['token']}, expected {leg['expect']}, "
             f"got {status}): {_failure_hint(leg)}")


def _render_report(name: str, version: str, model: str | None, timestamp: str,
                   legs: list[dict]) -> str:
    lines = [
        f"# Guidance-bridge canary report: {name}",
        "",
        f"- Claude CLI version: {version}",
        f"- Model: {model or '(CLI default)'}",
        f"- Timestamp: {timestamp}",
        "",
        "| Leg | Expectation | Token visible | Result |",
        "| --- | --- | --- | --- |",
    ]
    for leg in legs:
        if leg["error"]:
            visible_str = "-"
            result_str = f"ERROR: {leg['error']['type']}"
        else:
            visible_str = "yes" if leg["visible"] else "no"
            result_str = "PASS" if leg["passed"] else "FAIL"
        lines.append(f"| {leg['name']} | {leg['expect']} | {visible_str} | {result_str} |")

    lines += ["", "## Replies", ""]
    for leg in legs:
        reply = (leg.get("reply") or "")[:500]
        lines.append(f"### {leg['name']}")
        lines.append("")
        lines.append(f"> {reply}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_dir", type=Path)
    parser.add_argument("--subagent", action="store_true",
                        help="also run the bridge-subagent leg (Task-launched subagent)")
    parser.add_argument("--model", default=None, help="override the model for all legs")
    parser.add_argument("--timeout", type=int, default=600,
                        help="per-leg CLI timeout in seconds (default 600)")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                        help="root directory for run outputs (summary + report)")
    args = parser.parse_args()

    fixture = load_fixture(args.eval_dir)
    version = claude_version()
    legs = _build_legs(fixture, args.eval_dir, args.subagent)
    results = [_run_leg(leg, args.model, args.timeout) for leg in legs]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = args.results_dir / fixture["name"] / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)

    report = _render_report(fixture["name"], version, args.model, timestamp, results)
    with open(report_dir / "report.md", "w", encoding="utf-8") as f:
        f.write(report)

    summary = {
        "name": fixture["name"],
        "timestamp": timestamp,
        "claude_version": version,
        "legs": [{k: leg[k] for k in
                 ("name", "expect", "token", "visible", "passed", "error", "reply")}
                for leg in results],
    }
    with open(report_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    for leg in results:
        _print_leg(leg)

    if any(leg["error"] for leg in results):
        return 2
    if any(not leg["passed"] for leg in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
