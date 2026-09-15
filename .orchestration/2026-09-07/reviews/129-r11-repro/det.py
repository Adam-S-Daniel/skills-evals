"""Determinism through the CLI across PYTHONHASHSEED, on the B1' rows and the A rows."""
import hashlib, json, sys, os, re
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import run, model, weeks_back

TREE = sys.argv[1]
now = datetime.now(timezone.utc); W = weeks_back(4, now)
MODELS={"fetched_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"models":[
    model("claude-haiku-5","2025-06-01T00:00:00Z"), model("claude-sonnet-5","2025-06-01T00:00:00Z")]}
CENSUS={"generated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"weeks":W,
        "counts":{"claude-haiku-4":{W[0]:8000},"claude-sonnet-5":{W[0]:4000}}}
ARM="claude-haiku-4-20250101"
def prev(f):
    return {"generated_at":(now-timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "arms":[{"id":ARM},{"id":"claude-sonnet-5"}]+[{"id":x} for x in f],
            "catalogue_seen":[]}
ROWS={"B1'-A":[f"0filler-{i:04d}" for i in range(500)],
      "B1'-B":[f"zfiller-{i:04d}" for i in range(500)],
      "B1'-D":[f"claude-haiku-4-000000{i:02d}" for i in range(500)],
      "A-absent":[f"0plant-{i:04d}" for i in range(500)],
      "A-emptycounts":[f"0plant-{i:04d}" for i in range(500)]}
for name,f in ROWS.items():
    census = CENSUS
    omit = False
    if name=="A-absent": census=None; omit=True
    if name=="A-emptycounts":
        census={"generated_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"weeks":W,"counts":{}}
    digs=set()
    for seed in ("0","1","42"):
        r=run(TREE, models=MODELS, census=census, previous=prev(f), entry_pct=0,
              env_extra={"PYTHONHASHSEED":seed}, census_omit=omit)
        ro=r["roster"] or {}
        ro=json.loads(json.dumps(ro))
        for k in ("generated_at",):
            ro.pop(k,None)
        if "source" in ro:
            for k in ("models_api_at","census_at","admin_report_at"): ro["source"].pop(k,None)
        blob=json.dumps(ro,sort_keys=True)+"||"+re.sub(r'\d{4}-\d\d-\d\dT[\d:]+Z','<TS>',r["stdout"])
        digs.add(hashlib.md5(blob.encode()).hexdigest())
    print(f"  {name:16s} distinct outputs over PYTHONHASHSEED 0/1/42 = {len(digs)}  md5={sorted(digs)[0][:12]}")
