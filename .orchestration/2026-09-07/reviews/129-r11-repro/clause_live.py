"""Can `candidate in catalogue_seen_folded` fire ALONE (C27), and can
`n > 0` inside _Relevance.__init__ ever drop a key (C1)?"""
import lib, json
R = lib.roster
orig = R._is_attributable
stats = {"c27_alone": 0, "c27_true": 0, "calls": 0}
def patched(candidate, folded, api_ids, api_ids_folded, pa, paf, cs, csf):
    stats["calls"] += 1
    if api_ids is None: return True
    a = folded in (api_ids_folded or ())
    b = candidate in paf or folded in paf
    c1 = candidate in csf
    c2 = folded in csf
    if c1: stats["c27_true"] += 1
    if c1 and not (a or b or c2): stats["c27_alone"] += 1
    return a or b or c1 or c2
R._is_attributable = patched

origrel = R._Relevance.__init__
drops = {"n": 0}
def relinit(self, api_ids, count_turns, seat_aliases, live_order):
    d = dict(count_turns)
    drops["n"] += sum(1 for k, v in d.items() if not (isinstance(k, str) and v > 0))
    origrel(self, api_ids, count_turns, seat_aliases, live_order)
R._Relevance.__init__ = relinit

scen = json.load(open("scenarios.json"))
FA=[{"id": f"0filler-{i:04d}", "reason":"x"} for i in range(500)]
FS=[{"id": f"0plant-{i:04d}", "last_seen":"2026-09-04"} for i in range(500)]
for s in scen:
    for prev in (s["previous"],
                 {"arms": s["previous"]["arms"]+FA,
                  "catalogue_seen": s["previous"]["catalogue_seen"]+FS}):
        try: lib.run(s["models"], s["census"], prev)
        except Exception: pass
print(f"_is_attributable calls: {stats['calls']}")
print(f"  `candidate in catalogue_seen_folded` TRUE       : {stats['c27_true']}")
print(f"  `candidate in catalogue_seen_folded` TRUE ALONE : {stats['c27_alone']}")
print(f"_Relevance.__init__ keys dropped by `isinstance(k,str) and n>0`: {drops['n']}")
