#!/usr/bin/env python3
"""Rebuild $DASHBOARD_HOME/inputs/threads.json from list_threads results in
this session's transcripts, so no agent retypes the listing.

usage: threads_from_transcripts.py --since <ISO time> [--root <dir>]

Reads every *.jsonl under --root (default ~/.claude/projects: the main
session's transcript and its subagents'), takes each list_threads result whose
call was made at or after --since with no `since` or `state` filter, and keeps
the newest row per thread. It refuses to write unless it holds as many threads
as the listing's own `total`, so a run that skipped a page stops instead of
writing a short file.

Why: on 2026-11-18 a Haiku worker held all 238 threads but would not retype
about 50 KB into a file, and the Opus session did it instead.
"""
import datetime
import glob
import json
import os
import sys

H = os.environ.get("DASHBOARD_HOME") or sys.exit("DASHBOARD_HOME is not set: export it as the private dashboard folder (config/, inputs/, ds/, watch/) and run again.")
H = os.path.abspath(H)
OUT = os.path.join(H, "inputs/threads.json")
FIELDS = ("thread_id", "title", "state", "last_activity_at", "resolved", "session_id")


def ts(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def payload(content):
    """The JSON object inside a tool result, whatever envelope text surrounds it."""
    texts = [content] if isinstance(content, str) else [b.get("text", "") for b in content or [] if isinstance(b, dict)]
    dec = json.JSONDecoder()
    for text in texts:
        i = text.find("{")
        while i != -1:
            try:
                obj, _ = dec.raw_decode(text, i)
            except ValueError:
                i = text.find("{", i + 1)
                continue
            if isinstance(obj, dict) and "sessions" in obj:
                return obj
            i = text.find("{", i + 1)
    return None


def pages(root, since):
    for path in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
        calls = {}
        with open(path, errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                content = (d.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use" and str(b.get("name", "")).endswith("list_threads"):
                        calls[b.get("id")] = (b.get("input") or {}, d.get("timestamp"))
                    elif b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                        args, at = calls[b["tool_use_id"]]
                        if not at or ts(at) < since or args.get("since") or args.get("state"):
                            continue
                        obj = payload(b.get("content"))
                        if obj is not None:
                            yield at, obj


def main(argv):
    if len(argv) not in (2, 4) or argv[0] != "--since" or (len(argv) == 4 and argv[2] != "--root"):
        sys.exit(__doc__)
    since = ts(argv[1])
    root = argv[3] if len(argv) == 4 else os.path.expanduser("~/.claude/projects")
    rows, total = {}, None
    for at, obj in sorted(pages(root, since), key=lambda p: p[0]):
        if isinstance(obj.get("total"), int):
            total = obj["total"]
        for s in obj.get("sessions") or []:
            if isinstance(s, dict) and s.get("thread_id"):
                rows[s["thread_id"]] = {k: s.get(k) for k in FIELDS}
    if total is None:
        sys.exit(f"STOP: no unfiltered list_threads result since {argv[1]} in {root}. Call list_threads (no since or state filter, every page) and run again.")
    if len(rows) < total:
        sys.exit(f"STOP: list_threads results hold {len(rows)} threads but the listing says {total}. Fetch every page (follow next_cursor) and run again.")
    out = sorted(rows.values(), key=lambda r: r["last_activity_at"] or "", reverse=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, OUT)
    print(f"wrote {len(out)} threads (listing total {total})")


if __name__ == "__main__":
    main(sys.argv[1:])
