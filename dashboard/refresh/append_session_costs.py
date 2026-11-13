#!/usr/bin/env python3
"""Append get_session samples to $DASHBOARD_HOME/inputs/session_costs.jsonl.

usage: append_session_costs.py '<json list>'
Each item: {thread_id, session_id (cse_ or session_), created_at, updated_at,
environment_kind, device, cost_usd, output_tokens, error}. Missing keys become null.
"""
import json, sys, datetime

import os
H = os.environ.get("DASHBOARD_HOME") or sys.exit("DASHBOARD_HOME is not set: export it as the private dashboard folder (config/, inputs/, ds/, watch/) and run again.")
H = os.path.abspath(H)
PATH = os.path.join(H, "inputs/session_costs.jsonl")
FIELDS = ["thread_id", "session_id", "created_at", "updated_at", "environment_kind",
          "device", "cost_usd", "output_tokens", "error"]
at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
items = json.loads(sys.argv[1])
with open(PATH, "a") as f:
    for it in items:
        row = {"v": 1, "at": at, "source": "refresh"}
        for k in FIELDS:
            row[k] = it.get(k)
        sid = row["session_id"] or ""
        if sid.startswith("session_"):
            row["session_id"] = "cse_" + sid[len("session_"):]
        f.write(json.dumps(row) + "\n")
print("appended", len(items))
