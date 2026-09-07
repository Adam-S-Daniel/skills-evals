"""The 601-key census row: 601 ids all in history, the victim with 8000 turns."""
import sys, os
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import run, model, weeks_back, reason_for
TREE=sys.argv[1]
now=datetime.now(timezone.utc); W=weeks_back(4, now)
VICT="claude-sonnet-4-9"
MODELS={"fetched_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"models":[
    model("claude-haiku-5","2025-06-01T00:00:00Z"), model("claude-sonnet-5","2025-06-01T00:00:00Z")]}
keys={VICT:{W[0]:8000}, "claude-sonnet-5":{W[0]:800}}
for i in range(600): keys[f"claude-opus-4-{i:04d}"]={W[0]:3}
CENSUS={"generated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"weeks":W,"counts":keys}
prev={"generated_at":(now-timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),"arms":[],
      "catalogue_seen":[{"id":k,"last_seen":(now-timedelta(days=4)).date().isoformat()} for k in keys]}
r=run(TREE, models=MODELS, census=CENSUS, previous=prev, entry_pct=0)
seen=[e["id"] for e in (r["roster"] or {}).get("catalogue_seen",[])]
low=[i for i in seen if i.startswith("claude-opus-4-")]
print(f"  rc={r['rc']}  |catalogue_seen|={len(seen)}  victim kept={VICT in seen}")
print(f"  low-turn keys kept={len(low)}  dropped={600-len(low)}")
print(f"  claude-sonnet-5: {reason_for(r,'claude-sonnet-5')}")
