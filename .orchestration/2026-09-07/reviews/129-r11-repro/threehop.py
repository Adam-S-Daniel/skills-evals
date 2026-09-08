"""The SHIPPED three-hop floor's own scenario, with the previous-arms cap
made to fire by N filler arms.  Everything else verbatim from
test_a_three_hop_census_key_still_reaches_the_live_snapshot."""
import sys, os, re
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import run, model, weeks_back, reason_for

TREE = sys.argv[1]
now = datetime.now(timezone.utc)
W = weeks_back(4, now)
KEY="claude-haiku-4-20250101-20260101"; MID="claude-haiku-4-20250101"
BASE="claude-haiku-4"; LIVE="claude-haiku-4-20260601"; NEXT="claude-haiku-5"

MODELS={"fetched_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"models":[
    model(LIVE,"2026-06-01T00:00:00Z"), model(NEXT,"2026-07-01T00:00:00Z"),
    model("claude-sonnet-5","2026-02-01T00:00:00Z"),
    model("claude-opus-5","2026-04-01T00:00:00Z")]}
CENSUS={"generated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"weeks":W,
        "counts":{KEY:{W[0]:5000},"claude-sonnet-5":{W[0]:300}}}
for n in (0, 497, 498, 500):
    prev={"generated_at":(now-timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "arms":[{"id":BASE,"reason":"was an arm"}]+
                 [{"id":f"0filler-{i:04d}"} for i in range(n)],
          "catalogue_seen":[{"id":MID,"last_seen":(now-timedelta(days=3)).date().isoformat()}]}
    r=run(TREE, models=MODELS, census=CENSUS, previous=prev)
    ids=[a["id"] for a in (r["roster"] or {}).get("arms",[])]
    print(f"  fillers={n:4d} rc={r['rc']}  {LIVE} seated={LIVE in ids}  reason={reason_for(r,LIVE)}")
