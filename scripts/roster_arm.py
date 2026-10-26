#!/usr/bin/env python3
"""Is MODEL the `id` of an arm in the committed model roster? (#68, #372 U4)

    roster_arm.py MODEL [--roster PATH]     exit 0: an arm; exit 1: not one
    roster_arm.py --resolve FIXTURE [--roster PATH]
                                            print the model a fire of FIXTURE runs

`routine-eval-fire.yml` runs this in its validation step, before the fire
bearer exists, so a `model` input the sweep could not run never starts a
routine session. The roster is `evals/roster.yml` in the checkout (the default
branch's copy, trusted because `main` is pull-request-only; ADR 0001), read
with the harness's own reader and arm extraction, so this agrees with what
`run_eval.select_models` would accept for `--model`: a parsed `arms[].id`,
never a substring of the file. The judge and the preflight model are not arms.

A refusal prints one fixed line to stderr and never the input: the workflow's
log is public. MODEL is always the first argument and is read literally, never
as an option: `-h` is a model that is not an arm. `--roster` points at another
file for tests.

`--resolve FIXTURE` (#70, rounds 7 and 8) prints the model a fixture runs
when none is named, as run_eval resolves it: the fixture's `model:` pin,
else the roster's first arm; exit 1 with a fixed line when there is neither.
routine-eval-weekly.yml passes it as the fire's `model`, which eval mode
requires, so the fire's title names the model it ran
(scripts/compute_gates.py); scripts/plan_scheduled_evals.py --validate
checks it is an arm first. `--resolve` is never a model: an arm id starts
with a letter or digit, and the workflow checks that shape first.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))

import run_eval  # noqa: E402

REFUSAL = "input 'model' is not an arm of the committed evals/roster.yml"
NO_MODEL = "the fixture pins no model and the committed evals/roster.yml has no arm"
REPO_ROOT = Path(__file__).resolve().parent.parent


def is_arm(model: str, roster_path: Path) -> bool:
    roster, problem = run_eval.read_roster(roster_path)
    if problem:
        return False
    arm_ids, _judge, _is_arm, _skipped = run_eval.roster_models(roster)
    return model in arm_ids


def resolve(fixture: str, roster_path: Path, root: Path = REPO_ROOT) -> str | None:
    """The fixture's `model:` pin, else the roster's first arm, else None.
    `fixture` is a committed `evals/...` path, relative to `root`."""
    try:
        doc = yaml.safe_load((root / fixture / run_eval.FIXTURE_FILE)
                             .read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
        doc = None
    pin = doc.get("model") if isinstance(doc, dict) else None
    if isinstance(pin, str) and pin:
        return pin
    roster, problem = run_eval.read_roster(roster_path)
    if problem:
        return None
    arm_ids = run_eval.roster_models(roster)[0]
    return arm_ids[0] if arm_ids else None


def main(argv: list[str] | None = None) -> int:
    # No option parser: one would read a MODEL of `-h` as a request for help
    # and exit 0, which the workflow takes for "an arm". The first argument is
    # the model, whatever it looks like; any other argument list is refused.
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--resolve"] and len(argv) in (2, 4) \
            and (len(argv) == 2 or argv[2] == "--roster"):
        model = resolve(argv[1], Path(argv[3]) if len(argv) == 4 else run_eval.TRUSTED_ROSTER)
        if model is None:
            print(NO_MODEL, file=sys.stderr)
            return 1
        print(model)
        return 0
    if len(argv) == 1:
        roster_path = run_eval.TRUSTED_ROSTER
    elif len(argv) == 3 and argv[1] == "--roster":
        roster_path = Path(argv[2])
    else:
        print(REFUSAL, file=sys.stderr)
        return 1
    if is_arm(argv[0], roster_path):
        return 0
    print(REFUSAL, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
