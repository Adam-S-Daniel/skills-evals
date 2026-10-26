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
  * pending: successful runs of routine-eval-fire.yml in the window (less
    sentinel runs, which send nothing; #70, round 8) that
    have no ingested results yet. One younger than `PENDING_FULL_HOLD` (24
    hours) is reserved at `per_run_cap + per_run_overrun`; an older one is
    charged `per_run_overrun` only for the rest of the week. A routine run
    finishes within minutes (healthy runs take 4-12), so a fire with no
    results a day later failed (or is a scaffold or improve run, which never
    lands in routine-results/), and the in-run stops (`per_run_cap`,
    `stop_when_account_above` in harness/run_eval.py) still bound what it
    could have spent. An ingested run is matched to a fire by its run id's
    timestamp (the fire workflow stamps it at fire time), so a run from the
    last 24 hours frees one recent fire; runs older than that free old fires.

Pace room (Adam, 2026-10-25: "The percentage of weekly should allow for more
usage if I'm approaching end of week and under pace"): the allowance the
account has not used is released as its week ends. The newest account meter
snapshot in those ingested summaries (`usage.measured.meter.snapshots`) gives
the seven-day utilization and when that window resets; the room is
`max(0, stop_when_account_above - utilization)` times the share of the week
gone, less pending (fires still without results, whose spend the snapshot may
not show yet, so every fire shrinks the room until its results are ingested),
and a fire fits when it fits under the larger of that and the fixed cap left.
So the cap is a floor, early in a week the pace room is near nothing,
and the in-run `stop_when_account_above` stop still bounds every run. A
snapshot more than `PACE_MAX_AGE` old, ahead of the clock, with a reset
already past or more than a week out, or with a value out of range gives no
pace room: the fixed cap alone, the safe direction.

The meter is account-wide, so Adam's own use during a run is counted as eval
spend: an overcount, the safe direction.

The results branch is bot-written and untrusted (AGENTS.md, "Automation vs
branch protection"): files are read as data, never executed; a symlink, an
oversize file or a summary that does not parse is charged the full
reservation rather than trusted. Output is numbers only. The GitHub API call
is isolated in `count_successful_fires` (called once per age bound), so tests
pass the counts in; an API
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
#: A fire without results younger than this is held at the full reservation;
#: an older one failed, and is charged per_run_overrun only.
PENDING_FULL_HOLD = timedelta(hours=24)
#: ingest_routine_results.SIZE_CAPS["summary.json"]: a bigger file was never
#: ingested by that validator, so it is not read here either.
SUMMARY_MAX_BYTES = 64 * 1024
FIRE_WORKFLOW = "routine-eval-fire.yml"
#: A sentinel run's title (routine-eval-fire.yml's `run-name`; `mode` is a
#: choice input, so only a sentinel dispatch renders it). A sentinel sends
#: nothing to the routine and spends nothing, so it is no pending fire
#: (#70, round 8).
SENTINEL_TITLE_PREFIX = "Fire eval routine: mode=sentinel "
#: Runs read per page, and pages read at most, to find the sentinels; runs
#: past them are counted as fires, the safe direction.
PAGE_SIZE = 100
MAX_PAGES = 10
#: Float noise, not spend: the meter's readings carry six decimals
#: (run_eval._meter_delta rounds to them), so a sum within this of the cap is
#: an exact fit. 0.3 - 0.2 is 0.0999... in floats.
EPSILON = 1e-9
#: A meter snapshot older than this says too little of the account now to
#: release room on; one more than PACE_CLOCK_SKEW ahead of `now` is not read.
PACE_MAX_AGE = timedelta(hours=12)
PACE_CLOCK_SKEW = timedelta(minutes=5)
REFUSAL = ("::error::the weekly eval allowance cap would be exceeded by this "
           "fire; nothing was fired (evals/budget.yml, #68)")


class GuardError(Exception):
    """The guard could not tell what has been spent. Its message is fixed
    text and, for an API failure, a status code: never a response body."""


def _parse_stamp(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def _summary_paths(run_dir: Path) -> list[Path]:
    return sorted(path for path in run_dir.rglob("summary.json"))


def _load_summary(path: Path):
    """The parsed summary, or None for a symlink, an oversize file or one
    that does not parse: data that is not trusted."""
    try:
        if path.is_symlink() or path.stat().st_size > SUMMARY_MAX_BYTES:
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        return None


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
        summary = _load_summary(path)
        if summary is None:
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


def _snapshot_time(snapshot):
    """A snapshot's `at` as an aware datetime, or None."""
    at = snapshot.get("at") if isinstance(snapshot, dict) else None
    if not isinstance(at, str):
        return None
    try:
        stamp = datetime.fromisoformat(at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo is not None else None


def newest_snapshot(runs: list[Path]):
    """`(at, snapshot)` for the account meter snapshot with the newest `at`
    in the runs' summaries, or None. A snapshot without a readable `at`, and
    a summary `run_cost` would not trust, are skipped."""
    newest = None
    for run_dir in runs:
        for path in _summary_paths(run_dir):
            summary = _load_summary(path)
            usage = summary.get("usage") if isinstance(summary, dict) else None
            measured = usage.get("measured") if isinstance(usage, dict) else None
            reading = measured.get("meter") if isinstance(measured, dict) else None
            snapshots = reading.get("snapshots") if isinstance(reading, dict) else None
            if not isinstance(snapshots, list):
                continue
            for snapshot in snapshots:
                at = _snapshot_time(snapshot)
                if at is not None and (newest is None or at > newest[0]):
                    newest = (at, snapshot)
    return newest


def _number(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) \
        and math.isfinite(value)


def pace(runs: list[Path], limits: dict, now: datetime):
    """`(pace_room, utilization, week_elapsed)` from the newest snapshot, or
    `(0.0, None, None)` when there is none usable: the allowance below
    `stop_when_account_above` the account has not used, scaled by the share
    of its week gone."""
    found = newest_snapshot(runs)
    if found is None:
        return 0.0, None, None
    at, snapshot = found
    if not now - PACE_MAX_AGE <= at <= now + PACE_CLOCK_SKEW:
        return 0.0, None, None
    info = snapshot.get("info")
    windows = info.get("unifiedWindows") if isinstance(info, dict) else None
    week = windows.get("seven_day") if isinstance(windows, dict) else None
    used = week.get("utilization") if isinstance(week, dict) else None
    resets = week.get("resetsAt") if isinstance(week, dict) else None
    if not _number(used) or not 0 <= used <= 1 or not _number(resets):
        return 0.0, None, None
    left = resets - now.timestamp()
    if left <= 0 or resets - at.timestamp() > WINDOW.total_seconds():
        return 0.0, None, None
    elapsed = min(1.0, max(0.0, 1 - left / WINDOW.total_seconds()))
    room = max(0.0, limits["stop_when_account_above"] - used) * elapsed
    return room, float(used), elapsed


def account(tree: Path, limits: dict, now: datetime,
            fires: tuple[int, int]) -> dict:
    """{spent, pending, runs, fires, recent, reservation, cap, pace_room,
    account_used, week_elapsed} for the seven days up to `now`, given
    `fires`, a pair: the successful fires of the last seven days and of the
    last `PENDING_FULL_HOLD`. An ingested run is matched to a fire by its run
    id's timestamp (the fire workflow stamps it at fire time), so a run from
    the last `PENDING_FULL_HOLD` frees one recent fire and runs older than
    that free old fires; the unresulted recent fires are held in full and the
    rest are charged `per_run_overrun`. `pace_room` is `pace` of the same runs'
    newest meter snapshot; `account_used` and `week_elapsed` are None when
    there is no usable one."""
    try:
        fires_7d, fires_24h = fires
    except (TypeError, ValueError):
        raise GuardError("fire counts are not a pair") from None
    for count in (fires_7d, fires_24h):
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise GuardError("fire count is not a non-negative integer")
    runs = ingested_runs(tree, now)
    reserve = budget_file.run_reservation(limits)
    spent = sum(run_cost(run_dir, limits) for run_dir in runs)
    unresulted = max(0, fires_7d - len(runs))
    # A run id stamped after `now` (a clock ahead) counts as recent too, as
    # in ingested_runs. More recent runs than recent fires (a manual run)
    # leave no recent fire unresulted, never a negative count.
    held_since = now - PENDING_FULL_HOLD
    recent_runs = sum(
        1 for run_dir in runs
        if _parse_stamp(RUN_ID_RE.fullmatch(run_dir.name).group("stamp"))
        >= held_since)
    recent = max(0, min(fires_24h - recent_runs, unresulted))
    pending = recent * reserve + (unresulted - recent) * limits["per_run_overrun"]
    room, used, elapsed = pace(runs, limits, now)
    return {"spent": spent, "pending": pending, "runs": len(runs),
            "fires": fires_7d, "recent": recent, "reservation": reserve,
            "cap": limits["weekly_cap"], "pace_room": room,
            "account_used": used, "week_elapsed": elapsed}


def fits(state: dict) -> int:
    """How many more fires, each reserved in full, fit: the largest n with
    n * reservation <= max(cap - spent - pending, pace_room - pending)
    (within EPSILON). The fixed cap left is a floor; late in an under-pace
    week the pace room can exceed it (Adam, 2026-10-25). Pending comes off
    both: the snapshot behind the pace room may predate those fires, and
    without it every fire would fit until the next snapshot is ingested."""
    room = max(state["cap"] - state["spent"],
               state.get("pace_room", 0.0)) - state["pending"] + EPSILON
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
    """Successful runs of routine-eval-fire.yml created at or after `since`,
    less the sentinel runs among them (`SENTINEL_TITLE_PREFIX`): the one
    network call, paged, isolated so tests never make it. The count is the
    API's `total_count` less the sentinels found in at most `MAX_PAGES`
    pages, so a run not read counts as a fire (the safe direction). Any
    failure is a GuardError carrying at most the HTTP status code."""
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", repo or ""):
        raise GuardError("repository name is missing or malformed")
    total, sentinels, seen = None, set(), 0
    for page in range(1, MAX_PAGES + 1):
        query = urllib.parse.urlencode({
            "created": ">=" + since.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "success", "per_page": str(PAGE_SIZE), "page": str(page)})
        request = urllib.request.Request(
            f"{api}/repos/{repo}/actions/workflows/{FIRE_WORKFLOW}/runs?{query}",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with opener(request, timeout=30) as response:
                status = getattr(response, "status", 200)
                body = response.read(4 * 1024 * 1024)
        except urllib.error.HTTPError as exc:
            raise GuardError(f"the workflow runs API answered {exc.code}") from None
        except (urllib.error.URLError, OSError, ValueError):
            raise GuardError("the workflow runs API could not be reached") from None
        if status != 200:
            raise GuardError(f"the workflow runs API answered {status}")
        try:
            doc = json.loads(body)
            count, runs = doc.get("total_count"), doc.get("workflow_runs")
        except (ValueError, AttributeError, UnicodeDecodeError):
            raise GuardError("the workflow runs API answered 200 with an unreadable body") from None
        if isinstance(count, bool) or not isinstance(count, int) or count < 0 \
                or not isinstance(runs, list) \
                or not all(isinstance(r, dict) and isinstance(r.get("display_title"), str)
                           and isinstance(r.get("id"), int) for r in runs):
            raise GuardError("the workflow runs API answered 200 with an unreadable body")
        # The first page's total: a run created since only adds to later
        # pages' totals, never to what is charged.
        total = count if total is None else total
        seen += len(runs)
        # By id: a run created mid-read shifts the pages, so one can be read twice.
        sentinels |= {r["id"] for r in runs
                      if r["display_title"].startswith(SENTINEL_TITLE_PREFIX)}
        if len(runs) < PAGE_SIZE or seen >= total:
            break
    return max(0, total - len(sentinels))


def fires_that_fit(tree: Path, limits: dict, now: datetime,
                   fires: tuple[int, int]) -> int:
    """`fits` of the accounting for `now`: the weekly planner's cap. `fires`
    is `account`'s pair."""
    return fits(account(tree, limits, now, fires))


def describe(state: dict) -> str:
    """One non-identifying line, in points (percent of the weekly allowance)."""
    def points(value):
        return f"{value * 100:.1f}"
    line = (f"weekly eval allowance: spent {points(state['spent'])} points over "
            f"{state['runs']} ingested run(s), pending {points(state['pending'])} "
            f"points over {max(0, state['fires'] - state['runs'])} fire(s) without "
            f"results ({state['recent']} from the last 24h held in full), this run reserves {points(state['reservation'])}, cap "
            f"{points(state['cap'])} (last 7 days)")
    used = state.get("account_used")
    if state.get("pace_room", 0.0) > 0 or used is not None:
        return (f"{line}; account at {points(used or 0.0)}% with "
                f"{points(state.get('week_elapsed') or 0.0)}% of its week gone, "
                f"so pace allows {points(state.get('pace_room', 0.0))} points before pending fires")
    return f"{line}; no recent account reading, so no pace room"


def check(state: dict) -> bool:
    """Whether one more fire, reserved in full, stays within the cap."""
    return fits(state) >= 1


def _live_fires(now: datetime) -> tuple[int, int]:
    """(successful fires in the last seven days, in the last 24 hours)."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    api = os.environ.get("GITHUB_API_URL") or "https://api.github.com"
    return (count_successful_fires(repo, now - WINDOW, token, api=api),
            count_successful_fires(repo, now - PENDING_FULL_HOLD, token, api=api))


def main(argv: list[str] | None = None, now: datetime | None = None,
         fire_count=None) -> int:
    """`fire_count`, a function of `now` returning `(fires_7d, fires_24h)`,
    stands in for the API in tests."""
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
