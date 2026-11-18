#!/usr/bin/env python3
"""Append the owner's own messages to inputs/owner_messages.jsonl (a ledger).

usage: append_owner_messages.py --read-through <ISO time> [--chat-cursor <cursor>] '<json list>' | @<file>

Each item: {message_id, sent_at, thread_id}; thread_id is null for the project
chat. Ids and times only, never message text. Ids already in the ledger are
skipped, so passing the same window twice is harmless.

--read-through is the time up to which every thread active since the last
read (list_threads `since` = the previous read_through) and the project chat
were read. It is written to inputs/owner_messages_read.json, and refresh.sh
stops when it lags the newest thread activity by more than 24 hours. The
ledger stopped on 2026-11-04 and nothing noticed until the 2026-11-12 UX
review (C6), because a quiet ledger looks the same as a quiet owner; the
read-through time tells the two apart.

--chat-cursor is the read_project_chat cursor that fetched the chat's last page
this run. read_project_chat pages oldest first, so without it every run paged
the whole chat (20 pages, about 370k characters on 2026-11-18) to reach a few
new messages; the next run starts from the saved cursor instead. Left out, the
saved cursor is kept.
"""
import datetime
import json
import re
import sys

import os
H = os.environ.get("DASHBOARD_HOME") or sys.exit("DASHBOARD_HOME is not set: export it as the private dashboard folder (config/, inputs/, ds/, watch/) and run again.")
H = os.path.abspath(H)
LEDGER = os.path.join(H, "inputs/owner_messages.jsonl")
MARK = os.path.join(H, "inputs/owner_messages_read.json")
ID = re.compile(r"^cmsg_[A-Za-z0-9]+$")


def iso(s):
    t = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError(f"time without zone: {s}")
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv):
    cursor = None
    if len(argv) == 5 and argv[2] == "--chat-cursor":
        cursor, argv = argv[3], argv[:2] + argv[4:]
        if not cursor.strip():
            sys.exit("--chat-cursor is empty")
    if len(argv) != 3 or argv[0] != "--read-through":
        sys.exit(__doc__)
    through = iso(argv[1])
    raw = argv[2]
    items = json.load(open(raw[1:])) if raw.startswith("@") else json.loads(raw)
    seen = set()
    for line in open(LEDGER):
        if line.strip():
            seen.add(json.loads(line)["message_id"])
    new = []
    for it in items:
        mid, tid = it["message_id"], it.get("thread_id")
        if not ID.match(mid) or (tid is not None and not ID.match(tid)):
            sys.exit(f"bad id in {it!r}")
        if mid in seen:
            continue
        seen.add(mid)
        new.append({"v": 1, "message_id": mid, "sent_at": iso(it["sent_at"]), "thread_id": tid})
    new.sort(key=lambda r: r["sent_at"])
    with open(LEDGER, "a") as f:
        for r in new:
            f.write(json.dumps(r) + "\n")
    newest = max([r["sent_at"] for r in new], default=None)
    if cursor is None:
        try:
            cursor = json.load(open(MARK)).get("chat_cursor")
        except (OSError, ValueError):
            cursor = None
    mark = {"read_through": through,
            "written_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if cursor:
        mark["chat_cursor"] = cursor
    json.dump(mark, open(MARK, "w"))
    print(f"appended {len(new)} of {len(items)}; newest {newest}; read through {through}")


if __name__ == "__main__":
    main(sys.argv[1:])
