#!/usr/bin/env python3
"""Is MODEL the `id` of an arm in the committed model roster? (#68, #372 U4)

    roster_arm.py MODEL [--roster PATH]     exit 0: an arm; exit 1: not one

`routine-eval-fire.yml` runs this in its validation step, before the fire
bearer exists, so a `model` input the sweep could not run never starts a
routine session. The roster is `evals/roster.yml` in the checkout (the default
branch's copy, trusted because `main` is pull-request-only; ADR 0001), read
with the harness's own reader and arm extraction, so this agrees with what
`run_eval.select_models` would accept for `--model`: a parsed `arms[].id`,
never a substring of the file. The judge and the preflight model are not arms.

A refusal prints one fixed line to stderr and never the input: the workflow's
log is public. `--roster` points at another file for tests.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))

import run_eval  # noqa: E402

REFUSAL = "input 'model' is not an arm of the committed evals/roster.yml"


def is_arm(model: str, roster_path: Path) -> bool:
    roster, problem = run_eval.read_roster(roster_path)
    if problem:
        return False
    arm_ids, _judge, _is_arm, _skipped = run_eval.roster_models(roster)
    return model in arm_ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("model")
    parser.add_argument("--roster", type=Path, default=run_eval.TRUSTED_ROSTER)
    args = parser.parse_args(argv)
    if is_arm(args.model, args.roster):
        return 0
    print(REFUSAL, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
