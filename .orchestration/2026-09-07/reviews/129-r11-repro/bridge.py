"""Does evicting the bare-alias BRIDGE entry retire a real live previous arm?

api:      claude-sonnet-5-20261231 (live dated snapshot; bare alias NOT live)
          claude-sonnet-7          (newer sonnet, so the victim is not `newest in tier`)
          claude-haiku-5
census:   claude-sonnet-5-20260601 = 4153   (usage under ANOTHER dated snapshot)
          claude-haiku-5           = 3125
previous arms: the victim (live), the bare alias `claude-sonnet-5` (the BRIDGE),
          claude-sonnet-5-20260601, + N fillers.
"""
import json, re, sys, os
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import run, model, weeks_back, reason_for

TREE = sys.argv[1]
now = datetime.now(timezone.utc)
W = weeks_back(8, now)
VICTIM = "claude-sonnet-5-20261231"
BRIDGE = "claude-sonnet-5"
USED   = "claude-sonnet-5-20260601"

MODELS = {"fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "models": [
    model(VICTIM, "2024-01-01T00:00:00Z"),
    model("claude-sonnet-7", "2025-01-01T00:00:00Z"),
    model("claude-haiku-5", "2024-01-01T00:00:00Z")]}
CENSUS = {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "weeks": W,
          "counts": {USED: {w: 4153 // 8 for w in W},
                     "claude-haiku-5": {w: 3125 // 8 for w in W}}}

for nfill in (0, 100, 497, 498, 500):
    fillers = [f"0filler-{i:04d}" for i in range(nfill)]
    prev = {"generated_at": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "arms": [{"id": VICTIM}, {"id": BRIDGE}, {"id": USED}] +
                    [{"id": f} for f in fillers],
            "catalogue_seen": []}
    r = run(TREE, models=MODELS, census=CENSUS, previous=prev)
    seated = [a["id"] for a in r["roster"]["arms"]] if r["roster"] else []
    ret = {t["id"]: t["reason"] for t in (r["roster"] or {}).get("retired_since_last", [])}
    vr = reason_for(r, VICTIM)
    print(f"fillers={nfill:4d} rc={r['rc']}  victim seated={VICTIM in seated}")
    print(f"      victim: {vr}")
    if VICTIM in ret:
        print(f"      RETIRED: {ret[VICTIM]}")
