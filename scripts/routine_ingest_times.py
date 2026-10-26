#!/usr/bin/env python3
"""Print `--ingest-times` for scripts/compute_gates.py (#70): a JSON object
mapping each `routine-results/<run id>` in a checkout of
`persistent/eval-results` to its FIRST ingest: {"commit": the commit that
first added a file under it, "time": that commit's committer time in UTC
(`YYYY-MM-DDTHH:MM:SSZ`, whatever offset Git prints), "files":
{every path, relative to the run id directory, that commit added: its full
Git blob id in that commit}}.

  routine_ingest_times.py RESULTS_CHECKOUT [--committer EMAIL]

Only commits on the first-parent chain of the checked-out branch, walked in
parent order (never by committer date), whose committer email is the
ingest identity (`INGEST_COMMITTER`, what routine-eval-ingest.yml commits
as; `--committer` names another) can be a run's first ingest (#70, round
6). A side branch merged in, with a backdated committer date, or a commit by
anyone else, is not read. The committer email is not authentication (any
pusher can set it); it narrows the history read, and compute_gates'
re-verification of each run's MAC is what binds a run to the routine.
A file added under a run id by any later commit is not in `files`, and
compute_gates does not read it (round 4: a later push into an ingested run
must not change, or disqualify, what that run says). The blob ids let
compute_gates refuse a file edited in place since (round 5, B2). The
scheduled workflow runs this on its results checkout, which must be a full
clone: a shallow one may not reach a run's first ingest, so it is refused.
The Git reads are `harness_repo.IS_SHALLOW` and `harness_repo.INGEST_LOG`
(`git log --first-parent --topo-order --diff-filter=A --reverse --raw`),
through harness_repo's hardened sink: a fixed git binary, no hooks,
fsmonitor, attributes file, system or global configuration, diff driver,
text conversion or signature check. A directory name that is not a run id
is left out; compute_gates refuses such a run on its own. Exit 2 when a read
fails, its output is not the expected shape, or the checkout is shallow.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))

import harness_repo  # noqa: E402

PREFIX = "routine-results/"
#: compute_gates.RUN_ID_RE: what routine-eval-fire.yml names a run.
RUN_ID_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}")
#: The committer email routine-eval-ingest.yml's commit step sets.
INGEST_COMMITTER = "skills-evals@users.noreply.github.com"
#: A full Git object id, SHA-1 or SHA-256.
OID_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


def utc_time(value: str) -> str | None:
    """Git's strict ISO 8601 committer time (`%cI`) as one canonical UTC
    form, `YYYY-MM-DDTHH:MM:SSZ`, or None when it is not one: Git spells
    the zero offset `+00:00` in some versions and `Z` in others."""
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ingest_times(checkout: Path, committer: str = INGEST_COMMITTER) -> dict | None:
    """{run id: {"commit", "time", "files": {path: blob id}}}, each run id's
    first ingest by `committer` (module docstring), or None when a read
    fails, its output is not the expected shape, or the checkout is
    shallow."""
    if harness_repo._git_out(*harness_repo.IS_SHALLOW, cwd=checkout) != "false":
        return None
    out = harness_repo._git_out(*harness_repo.INGEST_LOG, cwd=checkout)
    if out is None:
        return None
    # Commits come oldest first, each as "\x01<sha> <time> <email>" and then, per
    # added file, ":<old mode> <new mode> <old id> <new id> A" and its path,
    # NUL-separated (git puts a newline before the first raw line).
    times, current, raw = {}, None, None
    for token in out.split("\0"):
        token = token.lstrip("\n")
        if raw is not None:
            path, meta, raw = token, raw, None
            fields = meta[1:].split(" ")
            if len(fields) != 5 or not OID_RE.fullmatch(fields[3]) or current is None:
                return None
            if not path.startswith(PREFIX) or current[2] != committer:
                continue
            run_id, _, rest = path[len(PREFIX):].partition("/")
            if not RUN_ID_RE.fullmatch(run_id) or not rest:
                continue
            first = times.setdefault(run_id, {"commit": current[0], "time": current[1],
                                              "files": {}})
            if first["commit"] == current[0]:
                first["files"][rest] = fields[3]
        elif token.startswith("\x01"):
            current = tuple(token[1:].split(" ", 2))
            if len(current) != 3 or utc_time(current[1]) is None:
                return None
            current = (current[0], utc_time(current[1]), current[2])
        elif token.startswith(":"):
            raw = token
        elif token:
            return None
    return times


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    committer = INGEST_COMMITTER
    if len(args) == 3 and args[1] == "--committer" and args[2]:
        args, committer = args[:1], args[2]
    if len(args) != 1:
        print("usage: routine_ingest_times.py RESULTS_CHECKOUT [--committer EMAIL]",
              file=sys.stderr)
        return 2
    times = ingest_times(Path(args[0]), committer)
    if times is None:
        print("routine_ingest_times: the results checkout's log could not be read",
              file=sys.stderr)
        return 2
    print(json.dumps(times, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
