#!/usr/bin/env python3
"""A seeded simulation of the in-situ guidance gate's `rest_policy` (ADR
0014, "Pooled-rest addendum (2026-11-07)"; harness/gates.py, IN-SITU
GUIDANCE CELLS). Deterministic: a fixed seed, no network, no clock.

  simulate_rest_guard.py [--sims N] [--seed S]

It runs harness/gates.py's own cell classifier (`_classify`) on synthetic
pairs and reports two things.

DRIFT (the false-removal rate). A section that helps by `--effect` (default
exactly the margin, 0.15) beside the CURRENT rest, after `--old-pairs`
(default 40, a full window) pairs beside an older rest that already covered
its content, so the older pairs show no gain (D about 0). Pairs beside the
current rest arrive one at a time up to the cap. A removal is false. It is
reported for:

  * `current`: only the current rest's pairs (the 2026-11-03 rule);
  * `pooled-with-current-guard`: the committed rule;
  * `pooled, no guard`: the pooled tests deciding alone (what the guard
    exists to stop);
  * `pooled, light guard`: a rejected design, the pooled remove test plus
    `rest_guard_min_pairs` current pairs and a current-only keep test at the
    margin that has not rejected (no contradiction on the current rest's
    own bound).

The target is at most 1 - `retire_confidence` (0.10).

AT THE CAP (`at_cap`, CAP_CASES). How cells end once the current rest's
window is full, under `current` and the committed rule: the share that
keep, that are removed, that end `no-clear-effect` (a proposed removal),
and that are STUCK (`insufficient` at the cap, which
no more runs can move; the pooled adversarial round 1's blocker). The cases
are a section that helps today after older rests that showed no gain or
harm, and a STALE KEEP: one that helped beside an older rest and no longer
does. A pooled keep is not final (the pooled adversarial rounds 2 and 3):
a removal on the current rest's evidence overrides it, and it lapses at the
current rest's cap, so the stale keep is removed or proposed.
For the committed rule it also reports the share of cells that held a
pooled keep alone at some pair, and the current-rest pairs fired for them
meanwhile (the planner fires such a cell until the current rest's own keep
crosses, the removal decides, or the window is full): the cost of the
override, in re-checks per kept cell.

NO BENEFIT (the cost). A section that does not help beside any rest: how
many pairs beside the current rest each policy needs to remove it (median
and the share removed within the cap), after 0, 20 and 40 older pairs.

THE OUTCOMES. Each arm of each pair is one run with `CHECKS` (10) objective
checks, each passed with probability `p` (the without arm's `--base`, 0.55,
and the with arm's that plus the effect), so a run mean is a binomial
proportion and D = with - without lies in [-1, 1]. Each pair is on one of
two CLI versions, alternately. Bets are neutral (no learned prior).

In this regime (a without arm far from the ceiling and the floor) a cell's
class can only move toward `no-benefit` at the remove test's stopping time,
which only grows with more pairs, and a keep that can still be overridden
is fired until the cap, so classifying once at the cap equals checking
after every pair; the script classifies once at the cap. The
display bounds (`betting_bound`), which no decision reads, are skipped to
keep it fast.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))

import gates  # noqa: E402

CHECKS = 10
CLIS = ("1.0.0 (Claude Code)", "1.0.1 (Claude Code)")
OLD, CURRENT = "rest-old", "rest-current"


def _run(mean: float, stamp: int, rest: str, role: str) -> dict:
    passed = round(mean * CHECKS)
    return {"timestamp": f"{stamp:06d}", "path": f"sim/{stamp:06d}/{role}",
            "pair_key": rest, "cli_versions": [CLIS[stamp % 2]],
            "numbers": {"run_mean": mean, "passed": passed, "total": CHECKS,
                        "scored_trials": 1, "judge_mean": None, "judge_conditional": False}}


def _arm(rng: random.Random, p: float) -> float:
    p = min(max(p, 0.0), 1.0)
    return sum(rng.random() < p for _ in range(CHECKS)) / CHECKS


def make_pairs(rng, n_old, n_current, base, old_effect, effect):
    pairs, keys = [], []
    for i in range(n_old + n_current):
        rest = OLD if i < n_old else CURRENT
        gain = old_effect if i < n_old else effect
        pairs.append((_run(_arm(rng, base + gain), i, rest, "with"),
                      _run(_arm(rng, base), i, rest, "without")))
        keys.append(rest)
    return pairs, keys


def guarded(pairs, keys, policy):
    """(class, current pairs at the removal or None) under the committed rule.
    Every removal is a decided remove or harm test (`remove_decided_at`,
    which since round 3's m5 also covers a removal over a pooled keep, or
    `harm_decided_at`), whichever came first."""
    cell = gates._classify(pairs, policy, 1, None,
                           {"keys": keys, "current": CURRENT,
                            "min_pairs": policy["rest_guard_min_pairs"]})
    at = min([n for n in (cell.get("remove_decided_at"), cell.get("harm_decided_at"))
              if n is not None], default=None) if cell["class"] == "no-benefit" else None
    return cell["class"], (sum(k == CURRENT for k in keys[:at]) if at else None)


def current_only(pairs, keys, policy):
    mine = [p for p, k in zip(pairs, keys) if k == CURRENT]
    cell = gates._classify(mine, policy, 1, None)
    at = cell.get("remove_decided_at") if cell["class"] == "no-benefit" else None
    return cell["class"], at


def _versions_ok(pairs, n, need):
    return len({v for pair in pairs[:n] for r in pair for v in r["cli_versions"]}) >= need


def unguarded(pairs, keys, policy, light=False):
    """Whether the pooled remove test decides (keep not first) with no guard,
    or with the LIGHT guard: `rest_guard_min_pairs` current pairs and a
    current-only keep test at the margin that has not rejected."""
    margin = policy["objective_margin"]
    alpha = 1 - policy["retire_confidence"]
    threshold = -math.log(alpha)
    ds = gates.differences(pairs)
    keep_at = gates.first_crossing(gates.keep_wealth(ds), (1 - policy["benefit_confidence"]))
    wealth = gates.remove_wealth(ds, margin)
    seen = 0
    for i, w in enumerate(wealth):
        seen += keys[i] == CURRENT
        if w < threshold or not _versions_ok(pairs, i + 1, policy["min_cli_versions"]):
            continue
        if light:
            current = [d for d, k in zip(ds[:i + 1], keys[:i + 1]) if k == CURRENT]
            if seen < policy["rest_guard_min_pairs"] or gates.first_crossing(
                    gates.keep_wealth(current, None, margin), alpha) is not None:
                continue
        return keep_at is None or keep_at > i + 1
    return False


def drift(rng, sims, policy, n_old, effect, base):
    cap = policy["max_runs_per_cell"]
    counts = {"current": 0, "pooled-with-current-guard": 0, "pooled, no guard": 0,
              "pooled, light guard": 0}
    for _ in range(sims):
        pairs, keys = make_pairs(rng, n_old, cap, base, 0.0, effect)
        counts["current"] += current_only(pairs, keys, policy)[0] == "no-benefit"
        counts["pooled-with-current-guard"] += guarded(pairs, keys, policy)[0] == "no-benefit"
        counts["pooled, no guard"] += unguarded(pairs, keys, policy)
        counts["pooled, light guard"] += unguarded(pairs, keys, policy, light=True)
    return {k: v / sims for k, v in counts.items()}


def at_cap(rng, sims, policy, n_old, old_effect, effect, base):
    """{policy: {"benefit", "no-benefit", "stuck"}}: the share of cells that
    end each way once the current rest's window is full. `stuck` is a cell
    still `insufficient` at its cap, which no more runs beside the current
    rest can move (the pooled adversarial round 1's blocker)."""
    cap = policy["max_runs_per_cell"]
    out = {"current": [], "pooled-with-current-guard": []}
    for _ in range(sims):
        pairs, keys = make_pairs(rng, n_old, cap, base, old_effect, effect)
        mine = [p for p, k in zip(pairs, keys) if k == CURRENT]
        out["current"].append(gates._classify(mine, policy, 1, None))
        out["pooled-with-current-guard"].append(gates._classify(
            pairs, policy, 1, None, {"keys": keys, "current": CURRENT,
                                     "min_pairs": policy["rest_guard_min_pairs"]}))
    extra = [provisional_fires(c, policy, n_old) for c in out["pooled-with-current-guard"]]
    got = {name: {"benefit": sum(c["class"] == "benefit" for c in cells) / sims,
                  "no-benefit": sum(c["class"] == "no-benefit" for c in cells) / sims,
                  "no-clear-effect": sum(c["class"] == "no-clear-effect" for c in cells) / sims,
                  "stuck": sum(c["class"] == "insufficient" and c["at_cap"]
                               for c in cells) / sims}
           for name, cells in out.items()}
    held = [n for n in extra if n is not None]
    got["pooled-with-current-guard"].update(
        # Round 3's M1: a pooled keep never stands at the cap (it lapses).
        kept_provisionally=sum(c["class"] == "benefit" and c["at_cap"]
                               and (c["rest_guard"] or {}).get("keep_final") is False
                               for c in out["pooled-with-current-guard"]) / sims,
        provisional=len(held) / sims,
        fires_while_provisional=statistics.mean(held) if held else 0.0)
    return got


def provisional_fires(cell, policy, n_old):
    """The current-rest pairs a cell is fired for while its keep is the
    pooled one alone (THE STALE KEEP: the planner fires it until the
    current rest's own keep crosses, the guarded removal decides, or the
    window is full), or None when it never holds a pooled keep alone. The
    older pairs come first, so pair n is current pair n - n_old."""
    guard = cell["rest_guard"]
    if guard is None or guard["pooled_keep_at"] is None:
        return None
    start = max(guard["pooled_keep_at"], n_old + policy["rest_guard_min_pairs"])
    current = guard["current_keep_at"]
    if current is not None and current <= start:
        return None  # the current-rest keep came first: final from the start
    removed = cell.get("remove_decided_at")
    if removed is not None and removed <= start:
        return None  # the removal decided first: never kept
    end = min(n for n in (current, removed, n_old + policy["max_runs_per_cell"])
              if n is not None)
    return end - start


#: (label, older pairs, older gain, current gain) for `at_cap`.
CAP_CASES = (
    ("helps today by 0.25, older rest no gain", 40, 0.0, 0.25),
    ("helps today by 0.25, older rest harmed 0.20", 40, -0.20, 0.25),
    ("helps today by the margin, older rest no gain", 40, 0.0, 0.15),
    # The override's own false removal: a pooled keep stands from the older
    # gains, and the section still helps by exactly the margin today.
    ("helps today by the margin, older rest gained 0.30", 40, 0.30, 0.15),
    ("no gain today, older rest gained 0.30 (stale keep)", 40, 0.30, 0.0),
    ("gains 0.05 today, older rest gained 0.30 (stale keep)", 40, 0.30, 0.05),
    # Round 4's M2: one rest, where the pooled rule is the `current` rule.
    ("helps today by 0.10, one rest", 0, 0.0, 0.10),
    # Round 4's M3: harm at a high without arm (above 1 - margin, where
    # only the harm test can remove) after older gains, and its false
    # removal at the harm test's null (no gain today) there.
    ("costs 0.30 today, without arm 0.90, older rest gained 0.10", 40, 0.10, -0.30, 0.90),
    ("no gain today (the harm null), without arm 0.90, older rest gained 0.10", 40, 0.10,
     0.0, 0.90),
)


def no_benefit(rng, sims, policy, n_old, base):
    cap = policy["max_runs_per_cell"]
    out = {"current": [], "pooled-with-current-guard": []}
    for _ in range(sims):
        pairs, keys = make_pairs(rng, n_old, cap, base, 0.0, 0.0)
        out["current"].append(current_only(pairs, keys, policy)[1])
        out["pooled-with-current-guard"].append(guarded(pairs, keys, policy)[1])
    return {k: {"removed": sum(v is not None for v in vs) / sims,
                "median_current_pairs": (statistics.median([v for v in vs if v is not None])
                                         if any(v is not None for v in vs) else None)}
            for k, vs in out.items()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sims", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--old-pairs", type=int, default=40)
    parser.add_argument("--effect", type=float, default=None,
                        help="the current rest's gain (default: the margin)")
    parser.add_argument("--base", type=float, default=0.55)
    args = parser.parse_args(argv)
    policy = gates.load_gate_policy()["guidance"]
    gates.betting_bound = lambda *a, **k: 0.0  # display only; no decision reads it
    effect = policy["objective_margin"] if args.effect is None else args.effect
    rng = random.Random(args.seed)
    target = 1 - policy["retire_confidence"]
    print(f"seed {args.seed}, {args.sims} simulations per row, margin "
          f"{policy['objective_margin']}, retire level {policy['retire_confidence']}, "
          f"guard {policy['rest_guard_min_pairs']} pairs")
    print(f"\nDRIFT: {args.old_pairs} older pairs with no gain, then up to "
          f"{policy['max_runs_per_cell']} current pairs gaining {effect}")
    for name, rate in drift(rng, args.sims, policy, args.old_pairs, effect, args.base).items():
        print(f"  false removal, {name:28s} {rate:.4f}"
              f"{'' if rate <= target else '  ABOVE ' + format(target, '.2f')}")
    print("\nAT THE CURRENT REST'S CAP: share keeping, removed, and stuck insufficient")
    for label, n_old, old_effect, gain, *base in CAP_CASES:
        sims = max(1, args.sims // 4)
        print(f"  {label} ({n_old} older pairs)")
        for name, got in at_cap(rng, sims, policy, n_old, old_effect, gain,
                                base[0] if base else args.base).items():
            print(f"    {name:28s} benefit {got['benefit']:.3f}, no-benefit "
                  f"{got['no-benefit']:.3f}, no-clear-effect {got['no-clear-effect']:.3f}, "
                  f"stuck {got['stuck']:.3f}"
                  + (f"; a pooled keep alone {got['provisional']:.3f}, fired "
                     f"{got['fires_while_provisional']:.1f} current pairs meanwhile"
                     if "provisional" in got else ""))
    print("\nNO BENEFIT: current pairs needed to remove (median), share removed in the cap")
    for n_old in (0, 20, 40):
        sims = max(1, args.sims // 4)
        for name, got in no_benefit(rng, sims, policy, n_old, args.base).items():
            print(f"  {n_old:2d} older pairs, {name:28s} median "
                  f"{got['median_current_pairs']}, removed {got['removed']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
