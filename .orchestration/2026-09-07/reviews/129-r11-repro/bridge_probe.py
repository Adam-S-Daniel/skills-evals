"""Mechanism: which arms survive the cap, and where the turns land."""
import lib, json
W8 = lib.weeks(8)
VICTIM="claude-sonnet-5-20261231"; BRIDGE="claude-sonnet-5"; USED="claude-sonnet-5-20260601"
api=[VICTIM,"claude-sonnet-7","claude-haiku-5"]
models=lib.models(*api)
census=lib.census({USED:{w:519 for w in W8}, "claude-haiku-5":{w:390 for w in W8}})
for nfill in (497,498):
    prev={"arms":[{"id":VICTIM},{"id":BRIDGE},{"id":USED}]+
                 [{"id":f"0filler-{i:04d}"} for i in range(nfill)],
          "catalogue_seen":[]}
    got,warn=lib.warnbox()
    R=lib.roster
    rel=None
    # reproduce compute_roster's internals
    api_ids=[m["id"] for m in R._clean_models(models,warn)]
    counts=R._clean_counts(census["counts"],warn)
    seat=R.alias_map(api_ids)
    ranked=[m for m in R._clean_models(models,warn)]
    snapshots={m["id"]:seat[m["id"]] for m in ranked if m["id"] in seat}
    avail=[m for m in ranked if m["id"] not in snapshots]
    rungs=R.tier_rungs(lib.POLICY)
    avail.sort(key=lambda m: R._rank(m,rungs))
    live_order=[m["id"] for m in avail]
    ew=R.window_weeks(lib.NOW,lib.POLICY["arm_enter_window_weeks"])
    xw=R.window_weeks(lib.NOW,lib.POLICY["arm_exit_window_weeks"])
    wu=set(ew)|set(xw)
    ct={c:sum(n for w,n in bw.items() if w in wu) for c,bw in counts.items()}
    ct={k:v for k,v in ct.items() if v>0}
    rel=R._relevance(api_ids,ct,seat,live_order)
    reported,carried=R._clean_previous_arms(prev,warn,relevant=rel)
    rk=rel.rank(reported)
    print(f"--- fillers={nfill}: |reported|={len(reported)} |carried|={len(carried)}")
    for i in (VICTIM,BRIDGE,USED):
        print(f"     {i:28s} tier={rk[i][0]} turns={-rk[i][1]:6d} fold={rel.fold(i):28s} carried={i in carried}")
    al=R._usage_alias_map(api_ids,list(counts)+carried+list(api_ids),seat,live_order)
    print(f"     alias_map[{USED}] -> {al.get(USED, USED)}")
    print(f"     invariant: census key {USED!r} folds to {rel.fold(USED)!r};"
          f" an entry folding onto it survives = "
          f"{any(rel.fold(c)==rel.fold(USED) for c in carried)}")
