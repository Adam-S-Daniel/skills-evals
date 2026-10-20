#!/usr/bin/env python3
"""Keep automated evals inside their share of the weekly allowance (#68).

Adam's standing decision (2026-10-10,
https://github.com/Adam-S-Daniel/skills-evals/issues/68#issuecomment-6097945979):
all automated evals stay within 30% of the Claude subscription's weekly
allowance. `evals/budget.yml` holds the numbers (read by harness/budget.py);
this script is the layer that runs BEFORE any spend:

  check  routine-eval-fire.yml runs it before the fire step, in every mode,
         and a refusal stops the fire. A fire may go only when
         spent + pending + one run's reservation <= weekly_cap.
  fits   prints how many more fires fit now; scripts/plan_scheduled_evals.py
         calls `fires_that_fit` itself so the weekly sweep plans only those.

What counts, over the last seven days (rolling, so every allowance week stays
under the cap wherever the account's own week starts):

  * spent: every ingested routine run on `persistent/eval-results`
    (`routine-results/<run id>/`, scripts/ingest_routine_results.py) whose
    run id's timestamp falls in the window, each charged its measured
    `usage.meter_delta.windows.seven_day.delta` plus `per_run_overrun` (the
    meter is read as a call begins, so the last call is outside the delta),
    or `per_run_cap + per_run_overrun` when there is no measured delta (null,
    a window reset, a run of one agent call, an unreadable summary). Every
    summary of one run_eval invocation carries the same run-level block, so
    an invocation is counted once however many summaries it wrote.
  * pending: successful runs of routine-eval-fire.yml in the window that
    have no ingested results yet, each reserved at `per_run_cap +
    per_run_overrun`. A fire whose routine never pushed (a failed session, a
    scaffold or improve run, which never land in routine-results/) stays
    reserved for seven days: conservative by design.

The meter is account-wide, so Adam's own use during a run is counted as eval
spend: an overcount, the safe direction.

The results branch is bot-written and untrusted (AGENTS.md, "Automation vs
branch protection"): files are read as data, never executed; a symlink, an
oversize file or a summary that does not parse is charged the full
reservation rather than trusted. Output is numbers only. The GitHub API call
is isolated in `count_successful_fires`, so tests pass the count in; an API
error refuses the fire (fail closed) and prints only the status code. Tests
pass `now` in too: nothing here reads the clock except `main`.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))

import budget as budget_file  # noqa: E402

#: The routine run id the fire workflow generates (routine-eval-fire.yml's
#: validate step), and the directory ingest names after it.
RUN_ID_RE = re.compile(r"(?P<stamp>[0-9]{8}T[0-9]{6}Z)-[0-9a-f]{6}")
DEST_ROOT = "routine-results"
WINDOW = timedelta(days=7)
#: ingest_routine_results.SIZE_CAPS["summary.json"]: a bigger file was never
#: ingested by that validator, so it is not read here either.
SUMMARY_MAX_BYTES = 64 * 1024
FIRE_WORKFLOW = "routine-eval-fire.yml"
#: Float noise, not spend: the meter's readings carry six decimals
#: (run_eval._meter_delta rounds to them), so a sum within this of the cap is
#: an exact fit. 0.3 - 0.2 is 0.0999... in floats.
EPSILON = 1e-9
REFUSAL = ("::error::the weekly eval allowance cap would be exceeded by this "
           "fire; nothing was fired (evals/budget.yml, #68)")


class GuardError(Exception):
    """The guard could not tell what has been spent. Its message is fixed
    text and, for an API failure, a status code: never a response body."""


def _parse_stamp(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def _summary_paths(run_dir: Path) -> list[Path]:
    return sorted(path for path in run_dir.rglob("summary.json"))


def _invocation_cost(usage, limits: dict) -> float:
    """One run_eval invocation's charge from its run-level `usage` block."""
    reserve = budget_file.run_reservation(limits)
    delta = usage.get("meter_delta") if isinstance(usage, dict) else None
    windows = delta.get("windows") if isinstance(delta, dict) else None
    week = windows.get("seven_day") if isinstance(windows, dict) else None
    moved = week.get("delta") if isinstance(week, dict) else None
    if isinstance(moved, bool) or not isinstance(moved, (int, float)) \
            or not math.isfinite(moved) or week.get("window_reset") is not False:
        return reserve
    # A meter that went down in a window that did not reset spent nothing
    # measurable; the overrun is still charged.
    return max(0.0, float(moved)) + limits["per_run_overrun"]


def run_cost(run_dir: Path, limits: dict) -> float:
    """What one ingested routine run is charged: the sum over its run_eval
    invocations (one run-level block each, however many summaries carry it),
    or the full reservation when nothing in it can be read."""
    reserve = budget_file.run_reservation(limits)
    blocks = {}
    for path in _summary_paths(run_dir):
        try:
            if path.is_symlink() or path.stat().st_size > SUMMARY_MAX_BYTES:
                return reserve
            summary = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError, RecursionError):
            return reserve
        usage = summary.get("usage") if isinstance(summary, dict) else None
        if not isinstance(usage, dict):
            # A summary from before #370 says nothing of its spend.
            return reserve
        level = {key: value for key, value in usage.items() if key != "measured"}
        blocks[json.dumps(level, sort_keys=True)] = usage
    if not blocks:
        return reserve
    return sum(_invocation_cost(usage, limits) for usage in blocks.values())


def ingested_runs(tree: Path, now: datetime) -> list[Path]:
    """The run directories under `<tree>/routine-results/` whose run id's
    timestamp is in the seven days up to `now` (a later one, from a clock
    ahead of this one, counts too: the safe direction)."""
    root = tree / DEST_ROOT
    if not root.is_dir():
        return []
    since = now - WINDOW
    found = []
    for run_dir in sorted(root.iterdir()):
        match = RUN_ID_RE.fullmatch(run_dir.name)
        if match is None or run_dir.is_symlink() or not run_dir.is_dir():
            continue
        try:
            stamp = _parse_stamp(match.group("stamp"))
        except ValueError:
            continue
        if stamp >= since:
            found.append(run_dir)
    return found


def account(tree: Path, limits: dict, now: datetime, fires: int) -> dict:
    """{spent, pending, runs, fires, reservation, cap} for the seven days up
    to `now`, given `fires`, the successful fires in that window."""
    if isinstance(fires, bool) or not isinstance(fires, int) or fires < 0:
        raise GuardError("fire count is not a non-negative integer")
    runs = ingested_runs(tree, now)
    reserve = budget_file.run_reservation(limits)
    spent = sum(run_cost(run_dir, limits) for run_dir in runs)
    pending = max(0, fires - len(runs)) * reserve
    return {"spent": spent, "pending": pending, "runs": len(runs),
            "fires": fires, "reservation": reserve, "cap": limits["weekly_cap"]}


def fits(state: dict) -> int:
    """How many more fires, each reserved in full, fit under the cap: the
    largest n with spent + pending + n * reservation <= cap (within
    EPSILON)."""
    room = state["cap"] - state["spent"] - state["pending"] + EPSILON
    if room < state["reservation"]:
        return 0
    # Counted by comparison, not trusted from a float quotient alone.
    count = int(room // state["reservation"])
    while (count + 1) * state["reservation"] <= room:
        count += 1
    while count and count * state["reservation"] > room:
        count -= 1
    return count


def count_successful_fires(repo: str, since: datetime, token: str,
                           api: str = "https://api.github.com",
                           opener=urllib.request.urlopen) -> int:
    """Successful runs of routine-eval-fire.yml created at or after `since`:
    the one network call, isolated so tests never make it. Any failure is a
    GuardError carrying at most the HTTP status code."""
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", repo or ""):
        raise GuardError("repository name is missing or malformed")
    query = urllib.parse.urlencode({
        "created": ">=" + since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "success", "per_page": "1"})
    request = urllib.request.Request(
        f"{api}/repos/{repo}/actions/workflows/{FIRE_WORKFLOW}/runs?{query}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with opener(request, timeout=30) as response:
            status = getattr(response, "status", 200)
            body = response.read(1024 * 1024)
    except urllib.error.HTTPError as exc:
        raise GuardError(f"the workflow runs API answered {exc.code}") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise GuardError("the workflow runs API could not be reached") from None
    if status != 200:
        raise GuardError(f"the workflow runs API answered {status}")
    try:
        total = json.loads(body).get("total_count")
    except (ValueError, AttributeError, UnicodeDecodeError):
        raise GuardError("the workflow runs API answered 200 with an unreadable body") from None
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise GuardError("the workflow runs API answered 200 with an unreadable body")
    return total


def fires_that_fit(tree: Path, limits: dict, now: datetime, fires: int) -> int:
    """`fits` of the accounting for `now`: the weekly planner's cap."""
    return fits(account(tree, limits, now, fires))


def describe(state: dict) -> str:
    """One non-identifying line, in points (percent of the weekly allowance)."""
    def points(value):
        return f"{value * 100:.1f}"
    return (f"weekly eval allowance: spent {points(state['spent'])} points over "
            f"{state['runs']} ingested run(s), pending {points(state['pending'])} "
            f"points over {max(0, state['fires'] - state['runs'])} fire(s) without "
            f"results, this run reserves {points(state['reservation'])}, cap "
            f"{points(state['cap'])} (last 7 days)")


def check(state: dict) -> bool:
    """Whether one more fire, reserved in full, stays within the cap."""
    return fits(state) >= 1


def _live_fires(now: datetime) -> int:
    return count_successful_fires(
        os.environ.get("GITHUB_REPOSITORY", ""), now - WINDOW,
        os.environ.get("GH_TOKEN", ""),
        api=os.environ.get("GITHUB_API_URL") or "https://api.github.com")


def main(argv: list[str] | None = None, now: datetime | None = None,
         fire_count=None) -> int:
    """`fire_count`, a function of `now`, stands in for the API in tests."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("check", "fits"))
    parser.add_argument("--results-tree", type=Path, required=True,
                        help="a checkout of persistent/eval-results")
    parser.add_argument("--budget", type=Path, default=None,
                        help="the budget file (default: evals/budget.yml)")
    args = parser.parse_args(argv)
    now = now or datetime.now(timezone.utc)
    try:
        limits = budget_file.load_budget(args.budget)
        state = account(args.results_tree, limits, now,
                        (fire_count or _live_fires)(now))
    except (GuardError, budget_file.BudgetError) as exc:
        # Fail closed: an unknown spend is never read as room to spend.
        print(f"::error::allowance guard: {exc}; refusing")
        return 1
    line = describe(state)
    print(line)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write(f"### Weekly allowance guard\n\n- {line}\n")
    if args.command == "fits":
        print(f"fires={fits(state)}")
        return 0
    if not check(state):
        print(REFUSAL)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
