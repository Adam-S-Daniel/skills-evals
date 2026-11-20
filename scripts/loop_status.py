#!/usr/bin/env python3
"""The loop's guard, pace, spend and forecast as one JSON status document.

Adam, 2026-11-20: "Give me observability on the loop guards, pace, usage".
His AI Usage dashboard (Adam-S-Daniel/ai-usage-dashboard) runs a collector on
the owner's machine every 5 minutes with no model involved; it runs `collect` and shows the
document this prints. Every figure is the guard's or the forecast's own
number, computed by their code, never recomputed here:

  * guard: `allowance_guard.live_state`, exactly what `check` and `fits`
    read (fires counted live from the GitHub API), and the verdict `check`
    gives an eval fire: open, refresh (one fire to bring a reading), pace
    probe, pace hold, 5-hour stop, or cap full.
  * pace: the account's weekly reading against the pace line
    (`stop_when_account_above` times the share of the week gone), through
    `allowance_guard.ahead_of_pace`. The guard reads the newest snapshot
    in ingested eval results, which can be hours old; the collector's own
    reading (`--week-used`, `--week-at`, `--week-resets`, at most
    `LIVE_MAX_AGE` old) is minutes old, so the page shows both and says
    which the guard used.
  * loop spend: approximate points (percent of the weekly allowance) the
    loop has committed since the account's weekly reset: eval runs spent
    and pending (the guard's `committed`), plus the loop's own scheduled
    jobs (`loop_reserve`, spend/weekly.json `loop_jobs`), against the
    configured cap. Project threads are development, not loop spend: no
    figure here counts them.
  * forecast: `forecast_catch_up.py`'s catch-up weeks and dates and keep-up
    per week, read from its output document. `collect` runs it at most every
    `--forecast-every-minutes` from the newest `gates` artifact of
    loop-pr-refresh.yml, the results branch and the account's meter history.
    Its per-task rows need the scheduled tasks' fire ledger, which only the
    daily dashboard refresh holds, so they are listed only when the
    forecast's input carries them.

Usage:
  python3 scripts/loop_status.py status --results-tree <checkout> [--forecast f.json]
      [--week-used 76 --week-at <ISO> --week-resets <ISO>]
  python3 scripts/loop_status.py collect --work <dir> [--meter-history <csv>]
      [--week-used ... --week-at ... --week-resets ...]

`collect` keeps its own checkouts under `--work` (the results branch and
_agent-guidance, both shallow) and reads them as data. It needs `git`, and
`gh` logged in for the gates artifact and, when GH_TOKEN is unset, the token
the guard counts fires with. The token is never printed. Output is numbers,
times and fixed text only; an error is a fixed message, never a body.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import allowance_guard as guard  # noqa: E402
import budget as budget_file  # noqa: E402
import cache_ttl  # noqa: E402

SCHEMA = 1
REPO = "Adam-S-Daniel/skills-evals"
RESULTS_BRANCH = "persistent/eval-results"
GATES_WORKFLOW = "loop-pr-refresh.yml"
GATES_ARTIFACT = "gates"
GUIDANCE_REPO = "https://github.com/Adam-S-Daniel/_agent-guidance"
#: The collector's reading is used for the live pace only while it is this
#: fresh; an older one says too little about the account now.
LIVE_MAX_AGE = timedelta(hours=1)
#: How long a subprocess (git, gh) may take before `collect` gives up on it.
STEP_TIMEOUT = 120


def iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str | None) -> datetime | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def points(fraction) -> float | None:
    return None if fraction is None else fraction * 100


def next_reset(now: datetime) -> datetime:
    """The account's next scheduled weekly reset after `now`."""
    weeks = (now - guard.ACCOUNT_WEEK_RESET) // guard.WINDOW + 1
    return guard.ACCOUNT_WEEK_RESET + weeks * guard.WINDOW


def live_reading(used_pct, at: datetime | None, resets: datetime | None,
                 now: datetime) -> dict | None:
    """The collector's weekly reading as {used, at, elapsed}, or None when it
    is missing, out of range, older than `LIVE_MAX_AGE`, ahead of the clock,
    or its reset is past or more than a week out."""
    if used_pct is None or at is None or resets is None:
        return None
    if not 0 <= used_pct <= 100:
        return None
    if not now - LIVE_MAX_AGE <= at <= now + guard.PACE_CLOCK_SKEW:
        return None
    left = (resets - now).total_seconds()
    if left <= 0 or (resets - at) > guard.WINDOW:
        return None
    elapsed = min(1.0, max(0.0, 1 - left / guard.WINDOW.total_seconds()))
    return {"used": used_pct / 100, "at": at, "elapsed": elapsed}


def verdict(state: dict) -> tuple[str, str]:
    """What the guard does with an eval fire now, as (code, why)."""
    if state.get("session_hold"):
        return "session_hold", "The 5-hour window is at or above its stop: no fire goes."
    if state.get("pace_hold"):
        if state.get("pace_probe"):
            return "pace_probe", ("No recent account reading: one eval fire may go as the pace "
                                  "probe, to bring one.")
        if state.get("account_used") is None:
            return "pace_hold", ("No recent account reading, and a probe is not due yet: "
                                 "no fire goes.")
        return "pace_hold", "The account is ahead of its weekly pace line: no fire goes."
    fits = guard.fits(state)
    if fits >= 1:
        return "open", f"{fits} more eval fire(s) fit under the cap now."
    if guard.refresh(state):
        return "refresh", "The cap is full, but one eval fire may go to bring a newer reading."
    return "cap_full", "The loop's share of the week is used: no fire goes."


def pace_block(reading: dict | None, limits: dict, source: str) -> dict | None:
    if reading is None:
        return None
    stop = limits["stop_when_account_above"]
    line = stop * reading["elapsed"]
    return {"source": source, "used_pct": points(reading["used"]), "at": iso(reading["at"]),
            "elapsed_pct": points(reading["elapsed"]), "line_pct": points(line),
            "stop_pct": points(stop),
            "ahead": guard.ahead_of_pace(reading["used"], reading["elapsed"], limits),
            "under_line_points": points(line - reading["used"])}


def forecast_block(doc) -> dict | None:
    """The forecast figures the page shows, from forecast_catch_up.py's
    output; None for a document without them."""
    if not isinstance(doc, dict):
        return None
    try:
        scenario = doc["scenarios"]["plan_cap_only"]
        inputs = doc["inputs"]
        low, high = inputs["usd_per_point"]
        mid = (low + high) / 2
        keep_up_usd = doc["keep_up_usd_per_week"]
        capacity = doc["capacity_usd_per_week"]["plan_central"]
    except (KeyError, TypeError, ValueError):
        return None
    def weeks(key):
        value = scenario.get(key)
        return None if not isinstance(value, (int, float)) or value == float("inf") else value
    tasks = [{"task": t.get("task"), "in_loop": t.get("in_loop"), "model": t.get("model"),
              "fires_per_week": t.get("fires_per_week"), "points_per_week": t.get("points_per_week")}
             for t in inputs.get("scheduled_tasks") or [] if isinstance(t, dict)]
    return {
        "as_of": doc.get("as_of"),
        "open_subjects": len(doc.get("subjects") or []),
        "backlog_points": doc.get("backlog_points_central"),
        "catch_up_weeks": {k: weeks(f"weeks_{k}") for k in ("central", "fast", "slow")},
        "catch_up_date": {k: scenario.get(f"done_{k}") for k in ("central", "fast", "slow")},
        "keep_up_points_per_week": keep_up_usd / mid if mid else None,
        "capacity_points_per_week": capacity / mid if mid else None,
        "eval_cap_points_per_week": inputs.get("weekly_cap_points"),
        "loop_jobs_points_per_week": inputs.get("loop_jobs_points_per_week"),
        "non_eval_points_per_week": (inputs.get("assumptions") or {}).get("non_eval_points_per_week"),
        "pace_hold_modeled": bool((inputs.get("assumptions") or {}).get("pace_hold")),
        "tasks": tasks,
    }


def status(tree: Path, limits: dict, now: datetime, state: dict | None,
           error: str | None = None, live: dict | None = None,
           forecast_doc=None, forecast_error: str | None = None) -> dict:
    """The status document. `state` is `allowance_guard.live_state`'s result
    (None with `error` when the guard could not read the spend: it refuses
    every fire then, and so does the page)."""
    since = guard.window_start(now)
    session_limit = budget_file.session_limit(limits, now)
    doc = {
        "schema": SCHEMA, "computed_at": iso(now),
        "week": {"window_start": iso(since), "resets_at": iso(next_reset(now))},
        "session": {"plan": limits.get(budget_file.PLAN_KEY),
                    "stop_pct": points(session_limit),
                    "hold": bool(state and state.get("session_hold"))},
        "guard": None, "pace": None, "guard_pace": None, "loop": None,
        "forecast": forecast_block(forecast_doc), "forecast_error": forecast_error,
    }
    if state is None:
        doc["guard"] = {"ok": False, "verdict": "error", "why": error or "the guard could not run",
                        "fits": 0}
    else:
        code, why = verdict(state)
        doc["guard"] = {"ok": True, "verdict": code, "why": why, "fits": guard.fits(state),
                        "pace_hold": bool(state.get("pace_hold")),
                        "pace_probe": bool(state.get("pace_probe")),
                        "session_hold": bool(state.get("session_hold"))}
        found = guard.newest_snapshot(guard.ingested_runs(tree, now, since))
        if state.get("account_used") is not None:
            doc["guard_pace"] = pace_block(
                {"used": state["account_used"], "at": found[0] if found else None,
                 "elapsed": state["week_elapsed"]}, limits, "guard")
        committed = state["committed"]
        doc["loop"] = {
            "eval_spent_points": points(state["spent"]),
            "eval_pending_points": points(state["pending"]),
            "eval_committed_points": points(committed),
            "loop_jobs_points": points(state.get("loop_reserve", 0.0)),
            "used_points": points(committed + state.get("loop_reserve", 0.0)),
            "cap_points": points(state.get("cap_configured", state["cap"])),
            "eval_cap_points": points(state["cap"]),
            "room_points": points(guard.room(state)),
            "eval_runs": state["runs"], "fires": state["fires"],
        }
    doc["pace"] = pace_block(live, limits, "live") or doc["guard_pace"]
    return doc


# --- collect: the checkouts and the forecast, then `status` -----------------

def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> str:
    """Run a step; raise RuntimeError naming only the program on failure."""
    try:
        out = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                             timeout=STEP_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError(f"{cmd[0]} {cmd[1]} did not finish") from None
    if out.returncode != 0:
        raise RuntimeError(f"{cmd[0]} {cmd[1]} failed ({out.returncode})")
    return out.stdout


def stale(marker: Path, every: timedelta, now: datetime) -> bool:
    try:
        made = datetime.fromtimestamp(marker.stat().st_mtime, timezone.utc)
    except OSError:
        return True
    return now - made >= every


def shallow(dest: Path, url: str, branch: str, every: timedelta, now: datetime) -> None:
    """A shallow checkout of `branch` at `dest`, refreshed when older than `every`."""
    marker = dest / ".git" / "loop-status-fetched"
    if not (dest / ".git").is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        run(["git", "clone", "-q", "--depth", "1", "--single-branch", "--branch", branch,
             url, str(dest)])
    elif stale(marker, every, now):
        run(["git", "fetch", "-q", "--depth", "1", "origin", branch], cwd=dest)
        run(["git", "reset", "-q", "--hard", "FETCH_HEAD"], cwd=dest)
    else:
        return
    marker.touch()


def fetch_gates(work: Path) -> Path:
    """The newest successful loop-pr-refresh run's verdict document, downloaded
    into a new empty directory (it is data from a bot-written artifact)."""
    listed = run(["gh", "run", "list", "-R", REPO, "-w", GATES_WORKFLOW, "-s", "success",
                  "-L", "1", "--json", "databaseId", "--jq", ".[0].databaseId"])
    run_id = listed.strip()
    if not run_id.isdigit():
        raise RuntimeError("no successful loop-pr-refresh run")
    fresh = work / "gates-new"
    if fresh.exists():
        shutil.rmtree(fresh)
    fresh.mkdir()
    run(["gh", "run", "download", run_id, "-R", REPO, "-n", GATES_ARTIFACT, "-D", str(fresh)])
    found = fresh / "latest.json"
    if found.is_symlink() or not found.is_file():
        raise RuntimeError("the gates artifact has no latest.json")
    target = work / "gates"
    if target.exists():
        shutil.rmtree(target)
    fresh.rename(target)
    return target / "latest.json"


def loop_jobs_input(tree: Path, out: Path) -> Path | None:
    """forecast_catch_up.py's `--automatic-spend` input carrying only the loop
    jobs' weekly points (spend/weekly.json `loop_jobs`), so the forecast takes
    them out of the eval cap as the guard does; None without them. With no
    categories, the meter history's measured non-eval total is all of it."""
    try:
        jobs = json.loads((tree / guard.LOOP_RESERVE_FILE).read_text(encoding="utf-8"))["loop_jobs"]
        value = float(jobs["points_per_week"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    out.write_text(json.dumps({"as_of": jobs.get("as_of"), "categories": [], "jobs": [],
                               "unmeasured": [], "loop_meter_points_per_week": value}),
                   encoding="utf-8")
    return out


def run_forecast(work: Path, tree: Path, meter_history: Path | None, now: datetime) -> Path:
    import forecast_catch_up  # noqa: PLC0415 - only collect needs it (and PyYAML)
    gates = fetch_gates(work)
    guidance = work / "agent-guidance"
    shallow(guidance, GUIDANCE_REPO, "main", timedelta(0), now)
    out = work / "forecast.json"
    tmp = work / "forecast.tmp.json"
    argv = ["--gates", str(gates), "--results-tree", str(tree), "--as-of", iso(now),
            "--guidance", str(guidance), "--set", f"start={iso(now)}", "--out-json", str(tmp)]
    jobs = loop_jobs_input(tree, work / "loop-jobs.json")
    if jobs:
        argv += ["--automatic-spend", str(jobs)]
    if meter_history and meter_history.is_file():
        argv += ["--meter-history", str(meter_history)]
    # Its summary lines go to stderr: stdout carries only the status document.
    try:
        with contextlib.redirect_stdout(sys.stderr):
            code = forecast_catch_up.main(argv)
    except SystemExit as exc:
        code = exc.code
    if code not in (0, None) or not tmp.is_file():
        raise RuntimeError("forecast_catch_up.py failed")
    doc = json.loads(tmp.read_text(encoding="utf-8"))
    doc["as_of"] = iso(now)
    out.write_text(json.dumps(doc), encoding="utf-8")
    tmp.unlink()
    return out


def collect(args, now: datetime) -> dict:
    work = args.work
    work.mkdir(parents=True, exist_ok=True)
    tree = work / "eval-results"
    limits = budget_file.load_budget(args.budget)
    shallow(tree, f"https://github.com/{REPO}", RESULTS_BRANCH,
            timedelta(minutes=args.results_every_minutes), now)
    forecast_path, forecast_error = work / "forecast.json", None
    if stale(forecast_path, timedelta(minutes=args.forecast_every_minutes), now):
        try:
            run_forecast(work, tree, args.meter_history, now)
        except (RuntimeError, OSError, ValueError, KeyError, ImportError) as exc:
            # Keep the previous forecast; say it is not fresh.
            forecast_error = f"forecast not refreshed: {exc}"
    env_token = os.environ.get("GH_TOKEN")
    if not env_token:
        os.environ["GH_TOKEN"] = run(["gh", "auth", "token"]).strip()
    os.environ.setdefault("GITHUB_REPOSITORY", REPO)
    doc = status_from_tree(tree, limits, now, args, forecast_path, forecast_error)
    doc["cache_ttl"] = cache_ttl_block(args.claude_settings, args.claude_projects)
    return doc


def cache_ttl_block(settings: Path | None = None, projects: Path | None = None) -> dict:
    """The `cache_ttl` section: the locked table's verdict, the result of
    applying it to `settings` (only with a path) and the observed cache writes
    under `projects` (only with a path). An error is a fixed message."""
    try:
        doc = cache_ttl.locked_weights()
        verdict = cache_ttl.subscription_ttl(doc)[0]
        block = {"table": doc.get("id"), "subscription_ttl": verdict,
                 "per_model": {m: v["ttl"] for m, v in
                               cache_ttl.model_verdicts(doc).items()},
                 "settings": "skipped", "verify": None}
    except (ValueError, OSError, ImportError):
        return {"table": None, "subscription_ttl": "5m", "per_model": {},
                "settings": "error", "verify": None,
                "error": "the weight table could not be read"}
    if settings is not None:
        try:
            block["settings"] = cache_ttl.apply_settings(settings, verdict)
        except (ValueError, OSError):
            block["settings"] = "error"
    if projects is not None:
        try:
            block["verify"] = cache_ttl.verify(projects, weights_doc=doc)
        except (ValueError, OSError):
            block["verify"] = {"ok": False, "reason": "the transcripts could not be read"}
    return block


def status_from_tree(tree: Path, limits: dict, now: datetime, args, forecast_path,
                     forecast_error=None, **stand_ins) -> dict:
    try:
        state, error = guard.live_state(tree, limits, now, **stand_ins), None
    except guard.GuardError as exc:
        state, error = None, f"the guard refuses every fire: {exc}"
    live = live_reading(args.week_used, parse_iso(args.week_at), parse_iso(args.week_resets), now)
    try:
        forecast_doc = json.loads(Path(forecast_path).read_text(encoding="utf-8")) \
            if forecast_path else None
    except (OSError, ValueError):
        forecast_doc = None
    return status(tree, limits, now, state, error, live, forecast_doc, forecast_error)


def main(argv: list[str] | None = None, now: datetime | None = None, **stand_ins) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("command", choices=("status", "collect"))
    p.add_argument("--results-tree", type=Path, help="status: a checkout of persistent/eval-results")
    p.add_argument("--work", type=Path, help="collect: the folder its checkouts and forecast live in")
    p.add_argument("--budget", type=Path, default=None)
    p.add_argument("--forecast", type=Path, default=None,
                   help="status: forecast_catch_up.py output to show")
    p.add_argument("--meter-history", type=Path, default=None,
                   help="collect: the meter history CSV forecast_catch_up.py measures non-eval use from")
    p.add_argument("--week-used", type=float, default=None,
                   help="the collector's weekly reading, in percent")
    p.add_argument("--week-at", default=None, help="when it was read (ISO)")
    p.add_argument("--week-resets", default=None, help="when that week resets (ISO)")
    p.add_argument("--results-every-minutes", type=float, default=10)
    p.add_argument("--forecast-every-minutes", type=float, default=60)
    p.add_argument("--claude-settings", type=Path, default=None,
                   help="collect: a Claude Code settings.json to set subagentPromptCacheTtl in")
    p.add_argument("--claude-projects", type=Path, default=None,
                   help="collect: ~/.claude/projects, to tally observed cache writes from")
    p.add_argument("--now", default=None, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    now = now or parse_iso(args.now) or datetime.now(timezone.utc)
    try:
        if args.command == "collect":
            if not args.work:
                p.error("collect needs --work")
            doc = collect(args, now)
        else:
            if not args.results_tree:
                p.error("status needs --results-tree")
            limits = budget_file.load_budget(args.budget)
            doc = status_from_tree(args.results_tree, limits, now, args, args.forecast,
                                   **stand_ins)
    except (RuntimeError, budget_file.BudgetError) as exc:
        print(f"loop status: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(doc, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
