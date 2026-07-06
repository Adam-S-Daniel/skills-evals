#!/usr/bin/env python3
"""Run a skill eval fixture.

Usage:
    python3 harness/run_eval.py evals/<skill> [--arm objective-only]

Implemented today: fixture loading, workspace materialization from the seed,
and the objective scorer. Agent invocation (running Claude Code on the
workspace, per arm) is a stub with a settled interface — until it is wired,
`--arm objective-only` scores a workspace as-is, which exercises the fixture
and scorers end-to-end (the pristine seed should FAIL the pinning checks; a
correctly pinned copy should PASS).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from scorers import objective  # noqa: E402


def load_fixture(eval_dir: Path) -> dict:
    with open(eval_dir / "fixture.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_agent(workspace: Path, prompt: str, arm: dict) -> str:
    """Run the agent under test on the workspace — STUB.

    Planned: spawn Claude Code non-interactively in `workspace` with `prompt`,
    installing the skill first for the with_skill arm (marketplace or local
    plugins/ path per DESIGN.md). Returns the transcript.
    """
    raise NotImplementedError("agent invocation not wired yet — see DESIGN.md")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_dir", type=Path)
    parser.add_argument("--arm", default="objective-only",
                        choices=["objective-only", "with_skill", "without_skill", "both"])
    parser.add_argument("--workspace", type=Path, default=None,
                        help="objective-only: score this workspace instead of the pristine seed")
    args = parser.parse_args()

    fixture = load_fixture(args.eval_dir)
    seed = args.eval_dir / "seed"

    if args.arm != "objective-only":
        print("Agent arms are not wired yet — run with --arm objective-only.")
        return 2

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


if __name__ == "__main__":
    raise SystemExit(main())
