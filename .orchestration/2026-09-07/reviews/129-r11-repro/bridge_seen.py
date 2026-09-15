"""Same bridge, but living in catalogue_seen — and the dated census key is a
catalogue_seen entry too, so it is TIER 1 and 'covers' the fold group."""
import sys, os
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import run, model, weeks_back, reason_for

TREE = sys.argv[1]
now = datetime.now(timezone.utc)
W = weeks_back(8, now)
VICTIM="claude-sonnet-5-20261231"; BRIDGE="claude-sonnet-5"; USED="claude-sonnet-5-20260601"
MODELS={"fetched_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"models":[
    model(VICTIM,"2024-01-01T00:00:00Z"), model("claude-sonnet-7","2025-01-01T00:00:00Z"),
    model("claude-haiku-5","2024-01-01T00:00:00Z")]}
CENSUS={"generated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"weeks":W,
        "counts":{USED:{w:519 for w in W}, "claude-haiku-5":{w:390 for w in W}}}
old=(now-timedelta(days=30)).date().isoformat(); new=(now-timedelta(days=1)).date().isoformat()
for n in (0, 100, 496, 497, 498, 500):
    prev={"generated_at":(now-timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "arms":[{"id":VICTIM}],
          "catalogue_seen":[{"id":BRIDGE,"last_seen":old},{"id":USED,"last_seen":old}]+
                           [{"id":f"0plant-{i:04d}","last_seen":new} for i in range(n)]}
    r=run(TREE, models=MODELS, census=CENSUS, previous=prev)
    seen=[e["id"] for e in (r["roster"] or {}).get("catalogue_seen",[])]
    ret={t["id"]:t["reason"] for t in (r["roster"] or {}).get("retired_since_last",[])}
    print(f"  plants={n:4d} rc={r['rc']}  bridge kept={BRIDGE in seen}  |seen|={len(seen)}")
    print(f"        {VICTIM}: {reason_for(r,VICTIM) or 'RETIRED: '+ret.get(VICTIM,'?')}")
