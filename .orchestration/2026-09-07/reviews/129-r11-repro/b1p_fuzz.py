"""The two round-10 fuzz scenarios (29.9% and 49.3%)."""
import json, re, sys, os
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import run, model, weeks_back, reason_for

TREE = sys.argv[1]
now = datetime.now(timezone.utc)
W = weeks_back(4, now)
FILL = [f"0filler-{i:04d}" for i in range(500)]

def scen(name, api, counts, arm, victim, fillers):
    models = {"fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "models": [model(i, "2025-06-01T00:00:00Z") for i in api]}
    census = {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "weeks": W,
              "counts": {k: {W[0]: v} for k, v in counts.items()}}
    prev = {"generated_at": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "arms": [{"id": arm}, {"id": victim}] + [{"id": f} for f in fillers],
            "catalogue_seen": []}
    r = run(TREE, models=models, census=census, previous=prev, entry_pct=0)
    reason = reason_for(r, victim) or "(absent)"
    m = re.search(r"carries ([\d.]+%)", reason)
    print(f"{name}: rc={r['rc']} {victim} -> carries {m.group(1) if m else reason[:80]}")

scen("scenario 1321 (true 29.9%)",
     ["claude-haiku-5"],
     {"claude-haiku-5": 2990, "claude-fable-5": 7010},
     "claude-fable-5-20250101", "claude-haiku-5", FILL)
scen("scenario 930  (true 49.3%)",
     ["claude-fable-4-20250101", "claude-sonnet-4"],
     {"claude-fable-4-20250101": 493, "claude-opus-5": 507},
     "claude-opus-5-20260601", "claude-fable-4-20250101", FILL)
