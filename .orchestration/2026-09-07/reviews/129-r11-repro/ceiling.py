"""A's ceiling: uncapped carry, the count-only warning, and the refusal past 10,000."""
import sys, os, json
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import run, model, weeks_back
TREE=sys.argv[1]
now=datetime.now(timezone.utc); W=weeks_back(4, now)
MODELS={"fetched_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"models":[
    model("claude-haiku-5","2025-06-01T00:00:00Z"), model("claude-sonnet-5","2025-06-01T00:00:00Z")]}
EMPTY={"generated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"weeks":W,"counts":{}}
for n in (501, 10000, 10001):
    prev={"generated_at":(now-timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "arms":[{"id":f"0plant-{i:06d}"} for i in range(n)],
          "catalogue_seen":[{"id":f"0seen-{i:06d}","last_seen":now.date().isoformat()} for i in range(n)]}
    r=run(TREE, models=MODELS, census=EMPTY, previous=prev, entry_pct=0)
    seen=len((r["roster"] or {}).get("catalogue_seen",[]))
    warn=[l for l in r["stderr"].splitlines() if "uncapped" in l or "refusing" in l]
    print(f"  n={n:6d} rc={r['rc']}  |catalogue_seen|={seen}")
    for l in warn: print(f"        {l}")
    # check nothing echoes an id
    leak=[l for l in r["stderr"].splitlines() if "0plant-" in l or "0seen-" in l]
    print(f"        ids echoed in stderr: {len(leak)}")
