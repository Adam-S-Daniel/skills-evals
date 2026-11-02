#!/usr/bin/env python3
"""Seeded simulation of stratified in-situ guidance pooling (skills-evals#546).

Two error rates, each checked after EVERY run (no fixed looks), using the
real bounds in harness/gates.py:

RETIRE (false removals). harness/gates.py's rule for an in-situ guidance
cell (Adam, 2026-11-02; #557): pooled over every version of the rest of
the guidance, remove when the stratified `retire_confidence` (0.90) upper
end is under `objective_margin` (0.15), after the pooled ceiling, floor and
cannot-discriminate rules; no separate confirmation step. In a GATED
scenario the section helps by exactly the margin beside every version of
the rest, so a removal is false; the target is 5% one-sided (0.90 is
two-sided). DRIFT scenarios (helps beside main's rest, not beside older
ones) are reported: the pooled rule decides on the average over versions,
by that decision. (#546 and the first #557 design gated an intersection
with a main-rest confirmation at 0.05 / 95%; the run counts on #557 showed
it could not be reached.)

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

KNOWN LIMITS:
  * the keep side needs a PER-CELL prior (harness/gates.py `cell_priors`,
    which is this simulation's default, no history): with a prior pooled
    from other cells at the ceiling a reviewer's probe gave stratified false
    keeps of 34-46%;
  * a 0/1 stratum with both arms constant meets the df guard and falls to
    the 1e-4 floor, so the ceiling and floor rules are what keep the edge
    scenarios safe;
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

M = POLICY["objective_margin"]
#: name, checks per trial, main-rest (p_with, p_without), old strata
#: [(p_with, p_without, runs per arm)], new main-rest runs per arm, gated.
#: GATED scenarios: the section helps by exactly the margin beside EVERY
#: version of the rest, so a removal is a false removal. The others are
#: DRIFT: it helps by the margin beside main's rest but not beside older
#: rests; the pooled rule (Adam, 2026-11-02, no confirmation step) removes
#: on the average over versions, so these are reported, not gated.
RETIRE = [
    ("3 checks, one rest", 3, (0.70 + M, 0.70), [], 60, True),
    ("1 check, one rest", 1, (0.50 + M, 0.50), [], 60, True),
    ("3 checks, three rests", 3, (0.70 + M, 0.70),
     [(0.60 + M, 0.60, 10), (0.75 + M, 0.75, 10)], 40, True),
    ("1 check, rests near the ceiling", 1, (0.75 + M, 0.75),
     [(0.97, 0.97 - M, 30), (0.95, 0.95 - M, 30)], 60, True),
    ("1 check, just under the ceiling", 1, (0.89, 0.89 - M), [], 60, True),
    ("1 check, just over the floor", 1, (0.12 + M, 0.12), [], 60, True),
    ("DRIFT 3 checks, two old rests at delta <= 0", 3, (0.70 + M, 0.70),
     [(0.70, 0.70, 10), (0.60, 0.70, 10)], 40, False),
    ("DRIFT 3 checks, four old rests x20", 3, (0.70 + M, 0.70),
     [(0.70, 0.70, 20), (0.60, 0.70, 20), (0.65, 0.70, 20), (0.70, 0.75, 20)], 40, False),
]

#: Power, not error: the section truly does nothing (delta 0 in every
#: rest). Reported, never failed: how many runs a removal costs.
POWER = [
    ("3 checks x 1 trial, two old rests", 3, (0.70, 0.70),
     [(0.70, 0.70, 10), (0.60, 0.60, 10)], 60),
    ("1 check x 1 trial, one rest", 1, (0.70, 0.70), [], 100),
    ("3 checks x 3 trials, one rest", 9, (0.70, 0.70), [], 40),
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
    """(pooled rule, main rest alone) retire for one rep, and the main-rest
    runs per arm the pooled rule first retired at (None if never). The
    pooled rule is harness/gates.py's for an in-situ guidance cell: the
    stratified `retire_confidence` upper end under the margin, with the
    pooled ceiling, floor and cannot-discriminate rules first."""
    seed, checks, main, old, horizon = args[:5]
    rng = random.Random(seed)
    history = _history(rng, [p for q in old for p in q[:2]] + list(main), checks)[0]
    margin, level, strength = (POLICY["objective_margin"], POLICY["retire_confidence"],
                               POLICY["prior_strength"])
    old_runs = [([_run(rng, pw, checks) for _ in range(n)],
                 [_run(rng, po, checks) for _ in range(n)]) for pw, po, n in old]
    strata = [([_mean(t) for t in w], [_mean(t) for t in o]) for w, o in old_runs]
    mw, mo, cw, co = [], [], [], []
    hit, first = [False, False], None
    for look in range(1, horizon + 1):
        cw.append(_run(rng, main[0], checks))
        co.append(_run(rng, main[1], checks))
        mw.append(_mean(cw[-1]))
        mo.append(_mean(co[-1]))
        groups = [g for s in strata for g in s] + [mw, mo]
        prior = _prior(history, groups)
        pooled = gates.stratified_sequence(strata + [(mw, mo)], level, prior,
                                           strength)[1] < margin
        every_w = cw + [t for w, _ in old_runs for t in w]
        every_o = co + [t for _, o in old_runs for t in o]
        rates = (_mean([_mean(t) for t in every_w]), _mean([_mean(t) for t in every_o]))
        blocked = (all(r >= POLICY["ceiling_fraction"] for r in rates)
                   or all(r <= POLICY["floor_fraction"] for r in rates)
                   or any(not any(t[c] for t in every_w + every_o) for c in range(checks)))
        own_prior = gates.pooled_variance([mw, mo], gates.GUIDANCE_PRIOR_MIN_DF,
                                          gates.GUIDANCE_FALLBACK_PRIOR_VARIANCE)
        own = gates.confidence_sequence(mw, mo, level, own_prior, strength)[1] < margin
        if pooled and not blocked and first is None:
            first = look
        hit[0] |= pooled and not blocked
        hit[1] |= own
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
        target = (1 - POLICY["retire_confidence"]) / 2
        print(f"RETIRE: false removals at margin {M}, {POLICY['retire_confidence']:.0%}, "
              f"target <= {target:.1%} (+{TOLERANCE:.1%} tolerance), "
              f"{args.reps} reps, seed {args.seed}")
        for i, (name, checks, main_p, old, horizon, gated) in enumerate(RETIRE):
            seeds = _seeds(args.seed, 1, i, args.reps)
            hits = list(pool.map(retire_rep, [(int(s), checks, main_p, old, horizon)
                                              for s in seeds], chunksize=200))
            pooled, own = (sum(h[j] for h in hits) for j in range(2))
            lo, hi = wilson(pooled, args.reps)
            passed = pooled / args.reps <= target + TOLERANCE
            if gated:
                ok &= passed
            mark = ("PASS" if passed else "FAIL") if gated else "INFO"
            print(f"  {mark} {name}: pooled rule {pooled / args.reps:.2%} "
                  f"[{lo:.2%}, {hi:.2%}]; main rest alone {own / args.reps:.2%}")
        print("POWER: true no-benefit at main's rest (reported, not gated)")
        for i, (name, checks, main_p, old, horizon) in enumerate(POWER):
            seeds = _seeds(args.seed, 3, i, args.reps)
            hits = list(pool.map(retire_rep, [(int(s), checks, main_p, old, horizon)
                                              for s in seeds], chunksize=200))
            firsts = sorted(h[2] for h in hits if h[2] is not None)
            median = firsts[len(firsts) // 2] if firsts else None
            print(f"  {name}: retired within {horizon} main-rest runs per arm in "
                  f"{len(firsts) / args.reps:.1%} (median runs {median})")
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
