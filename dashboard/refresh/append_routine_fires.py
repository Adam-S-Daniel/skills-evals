#!/usr/bin/env python3
"""Append scheduled-task fires to $DASHBOARD_HOME/watch/routine-fires.jsonl, one line per fire,
deduplicated by session id (a ledger: append, never rewrite).

usage: append_routine_fires.py '<json list>'   (or @file)
Each item: {trigger_id, name, fired_at, finished_at, status, session_id,
total_cost_usd, session_usage_cost_usd, last_served_model}. Missing keys
become null. An item without a session_id, or without finished_at (the fire
is still running), is skipped and counted, so the next refresh picks it up.

Why: list_triggers shows only each task's last_run, and list_sessions does
not list trigger-fired sessions, so a fire's session id is lost once the next
fire replaces it. acsi-kit's plan model needs per-fire cost history
(thread "Gather per-fire costs for routine plan model", 2026-11-13).
"""
import json, sys, datetime

import os
H = os.environ.get("DASHBOARD_HOME") or sys.exit("DASHBOARD_HOME is not set: export it as the private dashboard folder (config/, inputs/, ds/, watch/) and run again.")
PATH = os.path.join(H, "watch/routine-fires.jsonl")
FIELDS = ["trigger_id", "name", "fired_at", "finished_at", "status", "session_id",
          "total_cost_usd", "session_usage_cost_usd", "last_served_model"]


def norm(sid):
    sid = sid or ""
    return "cse_" + sid[len("session_"):] if sid.startswith("session_") else sid


def main(arg, path=PATH):
    items = json.load(open(arg[1:])) if arg.startswith("@") else json.loads(arg)
    seen = set()
    try:
        with open(path) as f:
            for line in f:
                if line.strip():
                    seen.add(json.loads(line)["session_id"])
    except FileNotFoundError:
        pass
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = dup = skipped = 0
    with open(path, "a") as f:
        for it in items:
            row = {"v": 1, "at": at}
            for k in FIELDS:
                row[k] = it.get(k)
            row["session_id"] = norm(row["session_id"])
            if not row["session_id"] or not row["finished_at"]:
                skipped += 1
                continue
            if row["session_id"] in seen:
                dup += 1
                continue
            seen.add(row["session_id"])
            f.write(json.dumps(row) + "\n")
            added += 1
    print(f"appended {added}, already present {dup}, skipped (no session id or unfinished) {skipped}")


if __name__ == "__main__":
    main(sys.argv[1])
