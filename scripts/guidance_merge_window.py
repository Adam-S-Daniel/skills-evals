#!/usr/bin/env python3
"""The weekly merge window for _agent-guidance's fleet guidance (ADR 0017).

Every merge of `agents-md/base.md` or `agents-md/sections/**` restarts the
eval evidence of every guidance section, so the owner batched automated
merges of those files into one window a week (2026-11-07). The bounds are
written once, in _agent-guidance's `scripts/base-md-merge-window.yml`
(timezone, weekday, start, end: wall-clock times in an IANA zone, so the
window's UTC instants move with daylight saving time). This module reads
that file from a checkout of _agent-guidance and never holds a copy of the
bounds.

The same window is the EVAL PAUSE (Adam, 2026-11-13: "evals pause from 12
to 2 on Mondays"; ADR 0017's addendum): no eval run starts inside it, so no
run reads guidance that is half merged. `eval-pause` answers "may an eval
run start now?" for every automated launcher: routine-eval-fire.yml (every
mode, before the allowance guard), eval.yml (the API lane's plan job) and
plan_week.py (a sweep inside the window plans no fire). A run already going
when the window opens is left to finish: it checked out the guidance once,
at its start, before any merge in the window could land.

Three callers use the merge half:

  * `guidance_improve_gate.open-pr`: outside the window the improvement pull
    request is opened ready but NOT armed for auto-merge (queued).
  * `retire_skill.py --target guidance`: outside the window no removal pull
    request is opened at all; a removal is armed the moment it is opened, and
    the withdrawal logic reads an unarmed one as a person's hold, so it
    is never opened unarmed.
  * `arm-queued` (guidance-merge-window.yml, Monday inside the window): arms
    auto-merge on the queued improvement pull requests.

Every failure to read the bounds means CLOSED: a missing, unreadable or
malformed file never arms anything. A person may merge any time; this
module only decides what automation does.

  guidance_merge_window.py arm-queued --tree DIR [--now ISO]
      env GUIDANCE_TOKEN: the App token for _agent-guidance
  guidance_merge_window.py eval-pause --tree DIR [--now ISO]

arm-queued: exit 0 when it ran (including "window closed, nothing armed");
1 on a failure it names (the exit code only, never an API body).
eval-pause: exit 0 when an eval run may start; 3 inside the window (paused;
stdout names the window's end); 1 when the bounds cannot be read, which a
launcher treats as paused (fail closed) and reports as a failure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: Where the bounds live, relative to a checkout of _agent-guidance.
WINDOW_REL = "scripts/base-md-merge-window.yml"
GUIDANCE_REPO = "Adam-S-Daniel/_agent-guidance"
QUEUED_PREFIX = "eval-guidance-improve/"
TOKEN_ENV = "GUIDANCE_TOKEN"
KEYS = ("timezone", "weekday", "start", "end")
#: Automation arms auto-merge only while at least this much of the window is
#: left, so the merge (after _agent-guidance's required checks) lands before
#: the window, and with it the eval pause, ends. Arming bounds when automation
#: may arm, never when GitHub merges; this margin is what keeps the two close.
ARM_MARGIN = timedelta(minutes=30)
#: eval-pause exit code inside the window (the allowance guard's refusal code).
PAUSED_EXIT = 3
HHMM = re.compile(r"([01]\d|2[0-3]):([0-5]\d)")


class WindowError(Exception):
    """The bounds could not be read or are not valid."""


def _minutes(hhmm: str) -> int:
    m = HHMM.fullmatch(hhmm)
    return int(m.group(1)) * 60 + int(m.group(2))


def parse_window(text: str) -> dict:
    """Strict parse: exactly timezone (an IANA zone name), weekday (1 to 7),
    start and end ("HH:MM", end later than start). Anything else raises
    WindowError. The parsed `timezone` is a ZoneInfo."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        raise WindowError("the window file is not YAML") from None
    if not isinstance(doc, dict) or set(doc) != set(KEYS):
        raise WindowError("the window file must hold exactly timezone, weekday, start and end")
    zone = doc["timezone"]
    if not isinstance(zone, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_+-]*(/[A-Za-z0-9_+-]+)*", zone):
        raise WindowError("timezone must be an IANA zone name such as America/New_York")
    try:
        zone = ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise WindowError("timezone is not a known IANA zone") from None
    wd = doc["weekday"]
    if isinstance(wd, bool) or not isinstance(wd, int) or not 1 <= wd <= 7:
        raise WindowError("weekday must be an integer 1 to 7")
    for key in ("start", "end"):
        if not isinstance(doc[key], str) or not HHMM.fullmatch(doc[key]):
            raise WindowError(f'{key} must be a "HH:MM" string')
    if _minutes(doc["start"]) >= _minutes(doc["end"]):
        raise WindowError("end must be later than start")
    return {"timezone": zone, "weekday": wd, "start": doc["start"], "end": doc["end"]}


def load_window(tree: Path) -> dict:
    try:
        text = (Path(tree) / WINDOW_REL).read_text(encoding="utf-8")
    except OSError:
        raise WindowError(f"{WINDOW_REL} is not readable in the _agent-guidance checkout") from None
    return parse_window(text)


def in_window(now: datetime, window: dict) -> bool:
    """Half open: `start` is inside, `end` is not, in the window's zone.
    `now` must be aware."""
    if now.tzinfo is None:
        raise WindowError("now must carry a timezone")
    local = now.astimezone(window["timezone"])
    minute = local.hour * 60 + local.minute
    return (local.isoweekday() == window["weekday"]
            and _minutes(window["start"]) <= minute < _minutes(window["end"]))


def _at(day: date, hhmm: str, window: dict) -> datetime:
    """The UTC instant of wall-clock `hhmm` on `day` in the window's zone."""
    h, m = divmod(_minutes(hhmm), 60)
    return datetime(day.year, day.month, day.day, h, m,
                    tzinfo=window["timezone"]).astimezone(timezone.utc)


def next_start(now: datetime, window: dict) -> datetime:
    today = now.astimezone(window["timezone"]).date()
    for days in range(8):
        day = today + timedelta(days=days)
        start = _at(day, window["start"], window)
        if day.isoweekday() == window["weekday"] and start > now:
            return start
    raise WindowError("no window start found")  # unreachable


def window_end(now: datetime, window: dict) -> datetime:
    """The end of the window `now` is inside (call only when it is)."""
    return _at(now.astimezone(window["timezone"]).date(), window["end"], window)


def arming_open(now: datetime, window: dict) -> bool:
    """Inside the window with at least ARM_MARGIN of it left."""
    return in_window(now, window) and now + ARM_MARGIN <= window_end(now, window)


def window_open(tree: Path, now: datetime | None = None) -> bool:
    """True only when the bounds read cleanly and `now` (default: the clock,
    read here and nowhere else) is inside with ARM_MARGIN left (arming_open).
    Any failure is False."""
    try:
        return arming_open(now or datetime.now(timezone.utc), load_window(tree))
    except WindowError:
        return False


QUEUED_JQ = (".[] | select(.head.ref | startswith(\"" + QUEUED_PREFIX + "\")) | "
             "{number, sha: .head.sha, draft, armed: (.auto_merge != null), "
             "author: .user.login, labels: [.labels[].name]}")


def eval_pause(tree: Path, now: datetime | None = None) -> tuple[bool, str]:
    """(paused, message) for an eval launcher. Raises WindowError when the
    bounds cannot be read: the caller fails closed."""
    window = load_window(tree)
    when = now or datetime.now(timezone.utc)
    if in_window(when, window):
        return True, ("evals paused: inside the weekly guidance merge window until "
                      f"{window_end(when, window).isoformat()}")
    return False, f"evals may start; next pause starts {next_start(when, window).isoformat()}"


def arm_queued(gh, tree: Path, now: datetime | None = None) -> list[str]:
    """Arm auto-merge (merge commit, matched to the head) on each queued
    improvement pull request, only inside the window. Returns what it did,
    one line each, with pull request numbers and no content."""
    import retire_skill  # noqa: PLC0415 - shared constants, imported lazily
    try:
        window = load_window(tree)
    except WindowError as exc:
        return [f"window unreadable ({exc}); nothing armed"]
    when = now or datetime.now(timezone.utc)
    if not arming_open(when, window):
        return [f"window closed (or under {int(ARM_MARGIN.total_seconds() // 60)} minutes left); "
                f"next start {next_start(when, window).isoformat()}; nothing armed"]
    listing = gh(["api", "--paginate", f"repos/{GUIDANCE_REPO}/pulls?state=open&per_page=100",
                  "--jq", QUEUED_JQ])
    done = []
    for line in listing.splitlines():
        pr = json.loads(line)
        number = pr["number"]
        if pr["author"] != retire_skill.LOOP_AUTHOR or retire_skill.AGENT_LABEL not in pr["labels"]:
            done.append(f"#{number}: not the loop's; left alone")
        elif retire_skill.ON_HOLD_LABEL in pr["labels"]:
            done.append(f"#{number}: on hold; left alone")
        elif pr["draft"]:
            done.append(f"#{number}: a draft (draft mode); left alone")
        elif pr["armed"]:
            done.append(f"#{number}: already armed")
        else:
            gh(["pr", "merge", str(number), "-R", GUIDANCE_REPO, "--auto", "--merge",
                "--match-head-commit", pr["sha"]])
            method = gh(["pr", "view", str(number), "-R", GUIDANCE_REPO, "--json",
                         "autoMergeRequest", "--jq",
                         '.autoMergeRequest.mergeMethod // ""']).strip()
            if method != "MERGE":
                raise retire_skill.RetireError(f"auto-merge (merge commit) is not enabled on #{number}")
            done.append(f"#{number}: armed")
    return done or ["no queued pull request"]


def main(argv: list[str] | None = None, *, env=None, gh=None, out=sys.stdout) -> int:
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("arm-queued")
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--now", default=None, help="ISO instant (tests); default the clock")
    p = sub.add_parser("eval-pause")
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--now", default=None, help="ISO instant (tests); default the clock")
    args = parser.parse_args(argv)
    if args.command == "eval-pause":
        try:
            now = datetime.fromisoformat(args.now) if args.now else None
            paused, message = eval_pause(args.tree, now)
        except (WindowError, ValueError) as exc:
            print(f"guidance_merge_window: eval-pause: {exc}; no eval may start (fail closed)",
                  file=sys.stderr)
            return 1
        out.write(message + "\n")
        return PAUSED_EXIT if paused else 0
    import retire_skill  # noqa: PLC0415
    token = env.get(TOKEN_ENV) or None
    if token is None:
        out.write("no write credential for _agent-guidance; nothing armed\n")
        return 0
    gh = gh or (lambda a, stdin=None: retire_skill.default_gh(a, stdin, token))
    now = datetime.fromisoformat(args.now) if args.now else None
    try:
        for line in arm_queued(gh, args.tree, now):
            out.write(line + "\n")
    except (retire_skill.RetireError, ValueError, KeyError) as exc:
        print(f"guidance_merge_window: {type(exc).__name__}: {exc if isinstance(exc, retire_skill.RetireError) else 'unexpected listing'}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
