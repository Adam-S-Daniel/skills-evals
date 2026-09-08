"""Scenario 2908 at several filler counts, through compute_roster."""
import lib, json, sys
scen = json.load(open("scenarios.json"))
s = scen[2908]
for nfill in (0, 100, 498, 499, 500, 501):
    FILL_ARMS = [{"id": f"0filler-{i:04d}", "reason": "x"} for i in range(nfill)]
    FILL_SEEN = [{"id": f"0plant-{i:04d}", "last_seen": "2026-09-04"} for i in range(nfill)]
    prev = {"arms": s["previous"]["arms"] + FILL_ARMS,
            "catalogue_seen": s["previous"]["catalogue_seen"] + FILL_SEEN}
    r, w = lib.run(s["models"], s["census"], prev)
    arms = {a["id"]: a["reason"][:60] for a in r["arms"]}
    print(f"  fillers={nfill:4d}  claude-sonnet-5-20261231: {arms.get('claude-sonnet-5-20261231','ABSENT')}")
