"""B1' rows: control, A, B, D, E — the dated departed arm whose census usage
is recorded under the UNDATED alias."""
import json, sys, os
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import run, model, weeks_back, reason_for

TREE = sys.argv[1]
now = datetime.now(timezone.utc)
W = weeks_back(4, now)

MODELS = {"fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
          "models": [model("claude-haiku-5", "2025-06-01T00:00:00Z"),
                     model("claude-sonnet-5", "2025-06-01T00:00:00Z")]}
CENSUS = {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
          "weeks": W,
          "counts": {"claude-haiku-4": {W[0]: 8000},
                     "claude-sonnet-5": {W[0]: 4000}}}
ARM = "claude-haiku-4-20250101"
def prev(fillers):
    arms = [{"id": ARM}, {"id": "claude-sonnet-5"}]
    arms += [{"id": f} for f in fillers]
    return {"generated_at": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "arms": arms, "catalogue_seen": []}

ROWS = {
  "control": [],
  "A":  [f"0filler-{i:04d}" for i in range(500)],
  "B":  [f"zfiller-{i:04d}" for i in range(500)],
  "D":  [f"claude-haiku-4-000000{i:02d}" for i in range(500)],
  "E":  [f"0filler-{i:04d}" for i in range(498)],
}
for name, fillers in ROWS.items():
    r = run(TREE, models=MODELS, census=CENSUS, previous=prev(fillers), entry_pct=0)
    reason = reason_for(r, "claude-sonnet-5")
    carried = None
    if r["roster"]:
        carried = len(r["roster"].get("catalogue_seen", []))
    share = "??"
    if reason:
        import re
        m = re.search(r"carries ([\d.]+%)", reason)
        share = m.group(1) if m else reason[:70]
    print(f"{name:8s} rc={r['rc']} claude-sonnet-5: carries {share}   |arms|={len(fillers)+2}")
    if r["rc"] not in (0,):
        print("   stderr:", r["stderr"][:400])
