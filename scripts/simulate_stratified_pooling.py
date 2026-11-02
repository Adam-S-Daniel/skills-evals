#!/usr/bin/env python3
"""Seeded simulation of stratified in-situ guidance pooling (skills-evals#546).

Two error rates, each checked after EVERY run (no fixed looks), using the
real bounds in harness/gates.py:

RETIRE (false removals). The section helps by exactly the margin beside
main's rest-of-guidance (delta = objective_margin, the hardest true "keep"),
while older rests show delta <= 0 and already hold many runs. A removal is
wrongly confirmed when BOTH the main-rest stratum's own confidence sequence
and the precision-weighted combined one have their `retire_confidence`
upper end under the margin (the intersection test the issue requires). The
target is 2.5% one-sided (`retire_confidence` 0.95 is two-sided). The two
halves are also reported alone: the combined bound alone is what #546's
review found unsafe.

KEEP (false keeps). No stratum has any effect (delta = 0 everywhere), 2 to 4
strata, one near the ceiling, per-check Bernoulli outcomes at one trial per
run. A keep is wrongly confirmed when the combined `benefit_confidence`
lower end is above 0, or a check is confidently better (Holm over the
stratified per-check figures, at `check_confidence`). The target is 7.5%
one-sided (85% two-sided).

TOLERANCE. A scenario passes when its estimate is at or under the target
plus 0.5 percentage points (the anytime boundary is approximate, since each
stratum's moderated variance and weight are re-estimated at every look),
and the report prints the 95% Wilson interval beside it.

THE PRIOR. `run_priors` pools the run-to-run variance over every guidance
section's runs, and on 2026-11-02 those were 48 runs with no group of two,
so the prior was the fallback and the next few runs will measure it. The
default here is that worst case: no history (`--history-groups 0`), the
prior re-measured at every look over the cell's own (stratum, arm) groups.
Measured on a few runs it is noisy and can reach the 1e-4 floor, which
broke both targets, today's single-stratum rule included; so the guidance
prior keeps a conservative fallback, 0.25 (the largest variance of a figure
from 0 to 1), until it has `GUIDANCE_PRIOR_MIN_DF` degrees of freedom
(`--min-prior-df`, `--fallback`). `--history-groups N` adds N past groups
of `HISTORY_RUNS` runs at the scenario's pass rates; `--cell-prior` drops
them.

KEEP ROUTES. Today's rule keeps on either route, the objective delta or a
Holm-confident check, each at 85%, so its false-keep rate is up to the sum
of the two. Each route is held to the target; the union is reported beside
today's single-stratum rule on the same runs, so a stratified change is
judged against the rule it replaces. The judge is not simulated: it can only add a requirement to a
removal and a route to a keep that has its own sequence.

THE CONFIRMATION'S PRIOR is measured on the main-rest stratum's own two arms
(same guard): a prior pooled with lower-variance strata (old rests at the
ceiling beside a mid-range main rest) made it anti-conservative (#546
review round 1, now a scenario here).

KNOWN LIMITS (#546 review round 2), for whoever wires this into a verdict:
  * the keep side is not shown safe when the shared prior is pooled from
    OTHER cells at the ceiling: a reviewer's probe with such a history gave
    stratified false keeps of 34-46% against 22-25% for one pooled stratum;
  * the main-rest half relies on the classifier's ceiling, floor and
    cannot-discriminate rules, which this simulation does not apply: a
    0/1 stratum with both arms constant meets the df guard and falls to the
    1e-4 floor (1 check at 0.97/0.92 retired 30% of the time without them);
  * a keep is the union of its routes, gated here per route, and the judge
    route is not simulated; each pass is judged on the point estimate.

    python3 scripts/simulate_stratified_pooling.py [--reps 20000] [--seed 546] [--jobs N]
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from harness import gates  # noqa: E402

POLICY = gates.load_gate_policy()["guidance"]
TOLERANCE = 0.005
HISTORY_GROUPS = 40
HISTORY_RUNS = 3

#: name, checks per trial, main-rest (p_with, p_without), old strata
#: [(p_with, p_without, runs per arm)], new main-rest runs per arm.
RETIRE = [
    ("3 checks, two old rests", 3, (0.75, 0.70), [(0.70, 0.70, 10), (0.60, 0.70, 10)], 40),
    ("1 check, two old rests", 1, (0.75, 0.70), [(0.70, 0.70, 10), (0.60, 0.70, 10)], 40),
    ("3 checks, four old rests x20", 3, (0.75, 0.70),
     [(0.70, 0.70, 20), (0.60, 0.70, 20), (0.65, 0.70, 20), (0.70, 0.75, 20)], 40),
    ("3 checks, near ceiling", 3, (0.92, 0.87), [(0.87, 0.87, 10), (0.80, 0.87, 10)], 40),
    ("5 checks, no old rest", 5, (0.75, 0.70), [], 60),
    # Round 1: old rests near the ceiling (low variance) beside a mid-range
    # main rest, so a pooled prior is far too small for the main rest.
    ("1 check, old rests at the ceiling", 1, (0.55, 0.50),
     [(0.97, 0.97, 30), (0.95, 0.97, 30)], 60),
    ("3 checks, old rests at the ceiling", 3, (0.55, 0.50),
     [(0.97, 0.97, 30), (0.95, 0.97, 30)], 60),
    ("3 checks, unequal old rests 4x40, main above margin", 3, (0.76, 0.70),
     [(0.70, 0.70, 40), (0.60, 0.70, 40), (0.65, 0.70, 40), (0.70, 0.75, 40)], 60),
]

#: Power, not error: the section truly does nothing beside main's rest
#: (delta 0), as RETIRE otherwise. Reported, never failed: the price of
#: confirming at main's rest is runs.
POWER = [
    ("3 checks, two old rests", 3, (0.70, 0.70), [(0.70, 0.70, 10), (0.60, 0.70, 10)], 60),
    ("1 check, two old rests", 1, (0.70, 0.70), [(0.70, 0.70, 10), (0.60, 0.70, 10)], 60),
]

#: name, checks per trial, strata [p] (with == without), total runs.
KEEP = [
    ("2 strata, one near ceiling", 3, [0.60, 0.95], 40),
    ("3 strata, one near ceiling", 3, [0.50, 0.75, 0.95], 40),
    ("4 strata, one near ceiling", 3, [0.40, 0.60, 0.80, 0.95], 40),
    ("3 strata, 1 check", 1, [0.50, 0.75, 0.95], 40),
    ("2 strata, ceiling beside mid-range", 3, [0.97, 0.55], 60),
    ("3 strata, 1 check, ceiling beside mid-range", 1, [0.97, 0.97, 0.55], 60),
]


def _run(rng, p: float, checks: int) -> list:
    """One arm of one run: one trial, `checks` Bernoulli check outcomes."""
    return [rng.random() < p for _ in range(checks)]


def _history(rng, ps: list, checks: int) -> tuple:
    """(run-mean groups, per-check-rate groups) of a past evaluation."""
    means, rates = [], []
    for g in range(HISTORY_GROUPS):
        p = ps[g % len(ps)]
        runs = [_run(rng, p, checks) for _ in range(HISTORY_RUNS)]
        means.append([_mean(r) for r in runs])
        rates.extend([float(r[c]) for r in runs] for c in range(checks))
    return means, rates


CELL_PRIOR = False
MIN_DF = 1
FALLBACK = gates.FALLBACK_PRIOR_VARIANCE


def _prior(history: list, cell: list) -> float:
    return gates.pooled_variance(cell if CELL_PRIOR else history + cell, MIN_DF, FALLBACK)


def _mean(values):
    return sum(values) / len(values)


def retire_rep(args) -> tuple:
    """(intersection, combined only, main only) retire for one rep, and the
    main-rest runs per arm the intersection first retired at (None if
    never)."""
    seed, checks, main, old, horizon = args
    rng = random.Random(seed)
    history = _history(rng, [p for q in old for p in q[:2]] + list(main), checks)[0]
    margin, level, strength = (POLICY["objective_margin"], POLICY["retire_confidence"],
                               POLICY["prior_strength"])
    strata = []
    for pw, po, n in old:
        strata.append(([_mean(_run(rng, pw, checks)) for _ in range(n)],
                       [_mean(_run(rng, po, checks)) for _ in range(n)]))
    mw, mo = [], []
    hit, first = [False, False, False], None
    for look in range(1, horizon + 1):
        mw.append(_mean(_run(rng, main[0], checks)))
        mo.append(_mean(_run(rng, main[1], checks)))
        groups = [g for s in strata for g in s] + [mw, mo]
        prior = _prior(history, groups)
        all_strata = strata + [(mw, mo)]
        combined = gates.stratified_sequence(all_strata, level, prior, strength)[1] < margin
        # The confirmation's prior is its own stratum's (#546 round 1): a
        # prior pooled with lower-variance strata made it anti-conservative.
        own_prior = gates.pooled_variance([mw, mo], gates.GUIDANCE_PRIOR_MIN_DF,
                                          gates.GUIDANCE_FALLBACK_PRIOR_VARIANCE)
        own = gates.confidence_sequence(mw, mo, level, own_prior, strength)[1] < margin
        if combined and own and first is None:
            first = look
        hit[0] |= combined and own
        hit[1] |= combined
        hit[2] |= own
        if all(hit):
            break
    return tuple(hit) + (first,)


def keep_rep(args) -> tuple:
    """(objective route, check route, union, today's union on the same
    runs pooled as one stratum) false keep for one rep."""
    seed, checks, ps, total = args
    rng = random.Random(seed)
    history, check_history = _history(rng, ps, checks)
    hit = [False, False, False, False]
    level, check_level, strength = (POLICY["benefit_confidence"],
                                    POLICY["check_confidence"], POLICY["prior_strength"])
    runs = [([], []) for _ in ps]  # per stratum: (with runs, without runs) of check lists
    for _ in range(total):
        s = rng.randrange(len(ps))
        runs[s][0].append(_run(rng, ps[s], checks))
        runs[s][1].append(_run(rng, ps[s], checks))
        used = [r for r in runs if r[0] and r[1]]
        for strata, at in ((used, 0), ([(sum((w for w, _ in used), []),
                                         sum((o for _, o in used), []))], 2)):
            means = [([_mean(x) for x in w], [_mean(x) for x in o]) for w, o in strata]
            prior = _prior(history, [g for m in means for g in m])
            objective = gates.stratified_sequence(means, level, prior, strength)[0] > 0
            per_check = [({str(c): [float(x[c]) for x in w] for c in range(checks)},
                          {str(c): [float(x[c]) for x in o] for c in range(checks)})
                         for w, o in strata]
            check_prior = _prior(check_history, [v for w, o in per_check
                                                 for d in (w, o) for v in d.values()])
            check = bool(gates.stratified_confident_checks(
                per_check, check_level, {str(c): check_prior for c in range(checks)},
                strength))
            if at == 0:
                hit[0] |= objective
                hit[1] |= check
                hit[2] |= objective or check
            else:
                hit[3] |= objective or check
    return tuple(hit)


def _init(cell_prior: bool, history_groups: int, min_df: int, fallback: float) -> None:
    global CELL_PRIOR, HISTORY_GROUPS, MIN_DF, FALLBACK
    CELL_PRIOR, HISTORY_GROUPS, MIN_DF, FALLBACK = (cell_prior, history_groups, min_df,
                                                    fallback)


def _seeds(seed: int, kind: int, scenario: int, reps: int) -> list:
    """One seed per rep, fixed by (seed, kind, scenario)."""
    rng = random.Random(f"{seed}:{kind}:{scenario}")
    return [rng.getrandbits(63) for _ in range(reps)]


class _Serial:
    """A pool of one, in this process (`--jobs 1`)."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def map(self, fn, items, chunksize=1):  # noqa: ARG002 - the pool's signature
        return map(fn, items)


def wilson(k: int, n: int) -> tuple:
    z = 1.959963984540054
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reps", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=546)
    parser.add_argument("--jobs", type=int, default=None)
    parser.add_argument("--history-groups", type=int, default=0,
                        help="groups in the prior's history (0: none)")
    parser.add_argument("--min-prior-df", type=int, default=gates.GUIDANCE_PRIOR_MIN_DF,
                        help="degrees of freedom the prior needs before it "
                             "replaces the fallback")
    parser.add_argument("--fallback", type=float, default=gates.GUIDANCE_FALLBACK_PRIOR_VARIANCE,
                        help="the prior variance below --min-prior-df")
    parser.add_argument("--cell-prior", action="store_true",
                        help="measure the prior from the cell's own runs only")
    args = parser.parse_args(argv)
    _init(args.cell_prior, args.history_groups, args.min_prior_df, args.fallback)
    ok = True
    with (_Serial() if args.jobs == 1 else ProcessPoolExecutor(
            args.jobs, initializer=_init,
            initargs=(CELL_PRIOR, HISTORY_GROUPS, MIN_DF, FALLBACK))) as pool:
        print(f"RETIRE: false removals, target <= 2.5% (+{TOLERANCE:.1%} tolerance), "
              f"{args.reps} reps, seed {args.seed}")
        for i, (name, checks, main_p, old, horizon) in enumerate(RETIRE):
            seeds = _seeds(args.seed, 1, i, args.reps)
            hits = list(pool.map(retire_rep, [(int(s), checks, main_p, old, horizon)
                                              for s in seeds], chunksize=200))
            both, comb, own = (sum(h[j] for h in hits) for j in range(3))
            lo, hi = wilson(both, args.reps)
            passed = both / args.reps <= 0.025 + TOLERANCE
            ok &= passed
            print(f"  {'PASS' if passed else 'FAIL'} {name}: intersection "
                  f"{both / args.reps:.2%} [{lo:.2%}, {hi:.2%}]; combined alone "
                  f"{comb / args.reps:.2%}; main rest alone {own / args.reps:.2%}")
        print("POWER: true no-benefit at main's rest (reported, not gated)")
        for i, (name, checks, main_p, old, horizon) in enumerate(POWER):
            seeds = _seeds(args.seed, 3, i, args.reps)
            hits = list(pool.map(retire_rep, [(int(s), checks, main_p, old, horizon)
                                              for s in seeds], chunksize=200))
            firsts = sorted(h[3] for h in hits if h[3] is not None)
            median = firsts[len(firsts) // 2] if firsts else None
            print(f"  {name}: retired within {horizon} main-rest runs per arm in "
                  f"{len(firsts) / args.reps:.1%} (median runs {median}); main rest "
                  f"alone {sum(h[2] for h in hits) / args.reps:.1%}, combined alone "
                  f"{sum(h[1] for h in hits) / args.reps:.1%}")
        print(f"KEEP: false keeps, target <= 7.5% (+{TOLERANCE:.1%} tolerance)")
        for i, (name, checks, ps, total) in enumerate(KEEP):
            seeds = _seeds(args.seed, 2, i, args.reps)
            hits = list(pool.map(keep_rep, [(int(s), checks, ps, total) for s in seeds],
                                 chunksize=200))
            obj, chk, union, today = (sum(h[j] for h in hits) for j in range(4))
            passed = max(obj, chk) / args.reps <= 0.075 + TOLERANCE
            ok &= passed
            lo, hi = wilson(max(obj, chk), args.reps)
            print(f"  {'PASS' if passed else 'FAIL'} {name}: objective {obj / args.reps:.2%}, "
                  f"check {chk / args.reps:.2%} (worse route's interval [{lo:.2%}, "
                  f"{hi:.2%}]); either {union / args.reps:.2%} vs today's single "
                  f"stratum {today / args.reps:.2%}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
