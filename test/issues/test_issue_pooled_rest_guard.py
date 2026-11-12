#!/usr/bin/env python3
"""In-situ guidance cells pooled across rests, with a current-rest guard
(Adam, 2026-11-07: "Pool + removal guard"; ADR 0014, "Pooled-rest addendum
(2026-11-07)").

Since 2026-11-03 an in-situ cell read only the runs beside the CURRENT rest
of the guidance, so one base.md edit discarded 494 of 498 in-situ arms. The
guidance block's `rest_policy: pooled-with-current-guard` (the default) pools
the pairs beside every rest, each at equal weight, a pair formed within one
rest only; keep decisions read them all, and every decision toward removal
needs the current rest's own evidence (harness/gates.py, module docstring,
IN-SITU GUIDANCE CELLS). `rest_policy: current` is the old rule, kept so the
gate can be switched back (test_issue_557_stratified_verdict.py pins it).

Hermetic and deterministic: canned runs, no network, no clock.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import gates  # noqa: E402
import explorer_data  # noqa: E402
import plan_week  # noqa: E402
from test_issue_70_retirement import FLAT, GAIN, LOSS, TEST_POLICY  # noqa: E402
from test_issue_557_stratified_verdict import CEILING, EXPECT, MAIN, OLD, stratum  # noqa: E402

POOLED = {**TEST_POLICY, "rest_policy": "pooled-with-current-guard", "rest_guard_min_pairs": 6}
CURRENT = {**TEST_POLICY, "rest_policy": "current"}
#: A with arm 0.2 above FLAT's without arm, which has headroom (0.8 < 0.85).
HELP = [(100, 100, 100)] * 40
#: A without arm with nothing left to gain.
TOP = [(100, 100, 100)] * 40
#: Both arms at the floor.
ZERO = [(0, 0, 0)] * 10
OLDER = "rest-older"
NOW = datetime(2026, 11, 7, 12, 0, 0, tzinfo=timezone.utc)


def verdict(runs, policy=POOLED, models=("model-a",), expect=EXPECT):
    return gates.guidance_verdict({"runs": runs}, list(models), "sec", policy, expect)


def cell_of(runs, policy=POOLED):
    return verdict(runs, policy)["cells"][0]


def strat(rest, with_patterns, without_patterns, start=0, **kw):
    """`stratum`'s in-situ runs beside `rest`, with judge figures for up to
    100 runs (the judge is reported, never decides)."""
    judges = [7.0, 7.2] * 50
    return stratum(rest, with_patterns, without_patterns, judges=(judges, judges),
                   start=start, **kw)


class PolicySettingTests(unittest.TestCase):

    def text(self, **guidance):
        base = "".join(f"  {k}: {v}\n" for k, v in TEST_POLICY.items())
        extra = "".join(f"  {k}: {v}\n" for k, v in guidance.items())
        return f"skills:\n{base}guidance:\n{base}{extra}"

    def test_both_keys_default_and_the_committed_file_sets_the_pooled_rule(self):
        parsed = gates.parse_gate_policy(self.text())["guidance"]
        self.assertEqual((parsed["rest_policy"], parsed["rest_guard_min_pairs"]),
                         ("pooled-with-current-guard", 6))
        committed = gates.load_gate_policy()
        self.assertEqual(committed["guidance"]["rest_policy"], "pooled-with-current-guard")
        self.assertEqual(committed["guidance"]["rest_guard_min_pairs"], 6)
        self.assertNotIn("rest_policy", committed["skills"])
        parsed = gates.parse_gate_policy(self.text(rest_policy="current",
                                                   rest_guard_min_pairs=10))["guidance"]
        self.assertEqual((parsed["rest_policy"], parsed["rest_guard_min_pairs"]),
                         ("current", 10))

    def test_an_unknown_rest_policy_fails_and_names_the_choices(self):
        for bad in ("pooled", "Current", "''", "[current]", "1"):
            with self.subTest(bad=bad), self.assertRaises(gates.GatePolicyError) as caught:
                gates.parse_gate_policy(self.text(rest_policy=bad))
            self.assertIn("guidance.rest_policy must be one of current, "
                          "pooled-with-current-guard", str(caught.exception))

    def test_a_bad_guard_size_fails(self):
        for bad in (0, -1, 41, 2.5, "six", "true"):
            with self.subTest(bad=bad), self.assertRaises(gates.GatePolicyError) as caught:
                gates.parse_gate_policy(self.text(rest_guard_min_pairs=bad))
            self.assertIn("rest_guard_min_pairs", str(caught.exception))

    def test_the_skills_block_has_no_rest(self):
        base = "".join(f"  {k}: {v}\n" for k, v in TEST_POLICY.items())
        with self.assertRaises(gates.GatePolicyError) as caught:
            gates.parse_gate_policy(f"skills:\n{base}  rest_policy: current\n")
        self.assertIn("unknown keys", str(caught.exception))

    def test_pool_cells_refuses_an_unknown_rest_policy(self):
        with self.assertRaises(ValueError):
            gates.pool_cells([], "sec", ["model-a"], EXPECT, strata=True, rest_policy="x")


class PoolingTests(unittest.TestCase):

    def test_a_cell_holds_every_rest_under_one_key(self):
        runs = (strat(OLD, FLAT[:4], FLAT[:4]) + strat(MAIN, FLAT[:3], FLAT[:3], start=4)
                + strat(OLD, FLAT[:2], FLAT[:2], model="model-b"))
        cells = gates.pool_cells(runs, "sec", ["model-a", "model-b"], EXPECT, strata=True,
                                 rest_policy="pooled-with-current-guard")
        a, b = cells[("fx", "model-a")], cells[("fx", "model-b")]
        self.assertEqual(sorted(a["strata"]), sorted([MAIN, OLD]))
        self.assertEqual((len(a["with"]), len(a["without"])), (7, 7))
        self.assertEqual(a["key"], {"tested_digest": "t1", "fixture_digest": "f1",
                                    "rest_digest": MAIN})
        self.assertEqual((len(b["with"]), len(b["without"])), (2, 2))

    def test_only_the_rest_digest_is_relaxed(self):
        runs = strat(OLD, FLAT[:4], FLAT[:4])
        runs[0]["tested_digest"] = "t0"        # an older section text
        runs[5]["fixture_digest"] = "f0"       # an older fixture
        runs[6]["fleet_hooks_digest"] = "h1"   # a hooked run
        runs[6]["pair_key"] = f"{OLD}:h1"
        cell = gates.pool_cells(runs, "sec", ["model-a"], EXPECT, strata=True)[("fx", "model-a")]
        self.assertEqual((len(cell["with"]), len(cell["without"])), (3, 2))

    def test_runs_pair_only_within_one_rest(self):
        # A with run beside one rest and a without run beside another share
        # a timestamp: they are not a pair.
        runs = strat(OLD, FLAT[:1], []) + strat(MAIN, [], FLAT[:1])
        cell = cell_of(runs)
        self.assertEqual((cell["pairs"], cell["unpaired"]), (0, 2))
        self.assertEqual(cell_of(strat(MAIN, FLAT[:1], FLAT[:1]))["pairs"], 1)

    def test_every_pair_weighs_the_same(self):
        # Ten pairs gaining 0.4 beside an old rest and two gaining 0 beside
        # main: the delta is the plain mean over the twelve pairs, not a
        # weighting of the two strata.
        runs = strat(OLD, GAIN, LOSS) + strat(MAIN, FLAT[:2], FLAT[:2], start=20)
        cell = cell_of(runs)
        pairs = [(w["numbers"]["run_mean"] - o["numbers"]["run_mean"])
                 for w, o in zip(sorted([r for r in runs if r["role"] == "with"],
                                        key=lambda r: r["timestamp"]),
                                 sorted([r for r in runs if r["role"] == "without"],
                                        key=lambda r: r["timestamp"]))]
        self.assertEqual(cell["pairs"], 12)
        self.assertAlmostEqual(cell["objective"]["delta"], sum(pairs) / len(pairs))
        self.assertEqual((cell["rests"], cell["current_rest_pairs"]), (2, 2))


class KeepTests(unittest.TestCase):

    def test_a_benefit_beside_an_old_rest_keeps_once_the_current_rest_has_its_pairs(self):
        # Adam, 2026-11-07: the pooled keep counts only from the pair at which
        # the current rest has `rest_guard_min_pairs` (6) pairs.
        runs = strat(OLD, GAIN, LOSS) + strat(MAIN, FLAT[:6], FLAT[:6], start=20)
        v = verdict(runs)
        self.assertEqual(v["verdict"], "keep", v["cells"][0]["reason"])
        guard = v["cells"][0]["rest_guard"]
        self.assertLess(guard["pooled_keep_at"], 20)
        self.assertIsNone(guard["current_keep_at"])
        # Under `current` the same runs are insufficient (the 2026-11-03 rule).
        self.assertEqual(verdict(runs, CURRENT)["verdict"], "insufficient")

    def test_an_older_rest_alone_never_keeps(self):
        for current in (0, 2, 5):
            with self.subTest(current=current):
                runs = strat(OLD, GAIN, LOSS) + strat(MAIN, FLAT[:current], FLAT[:current],
                                                      start=20)
                cell = cell_of(runs)
                self.assertEqual(cell["class"], "insufficient", cell["reason"])
                self.assertIsNotNone(cell["rest_guard"]["pooled_keep_at"])
                self.assertEqual(cell["current_rest_pairs"], current)
                self.assertFalse(cell["at_cap"])
                # The pooled keep's p does not count yet either.
                self.assertEqual(cell["keep_tests"][0]["p"], 1.0)

    def test_the_current_rest_keeps_on_its_own(self):
        # Older rests that showed harm cannot stop a section that helps
        # today from keeping: the current-rest keep test needs no older pair.
        runs = strat(OLD, LOSS * 4, FLAT * 2) + strat(MAIN, GAIN, LOSS, start=40)
        cell = cell_of(runs)
        self.assertEqual(cell["class"], "benefit", cell["reason"])
        self.assertIsNotNone(cell["rest_guard"]["current_keep_at"])

    def test_the_two_keep_routes_split_the_keep_level(self):
        # Each route runs at half the cell's keep alpha (Bonferroni) and its
        # p is doubled, so `1 - m x min p` still reads the cell's level.
        runs = strat(OLD, GAIN, LOSS) + strat(MAIN, GAIN, LOSS, start=10)
        cell = cell_of(runs)
        self.assertEqual([t["route"] for t in cell["keep_tests"]],
                         ["objective", "objective-current-rest"])
        current = gates.differences(gates.pair_runs(
            [r for r in runs if r["role"] == "with" and r["pair_key"] == MAIN],
            [r for r in runs if r["role"] == "without" and r["pair_key"] == MAIN])[0])
        wealth = gates.keep_wealth(current)
        self.assertAlmostEqual(cell["keep_tests"][1]["p"], min(1.0, 2 * gates.ville_p(wealth)))
        half = (1 - POOLED["benefit_confidence"]) / 2
        self.assertEqual(cell["rest_guard"]["current_keep_at"],
                         10 + gates.first_crossing(wealth, half))
        # The pooled route's own crossing is at half the level too.
        ds = gates.differences(gates.pair_runs([r for r in runs if r["role"] == "with"],
                                               [r for r in runs if r["role"] == "without"])[0])
        self.assertEqual(cell["rest_guard"]["pooled_keep_at"],
                         gates.first_crossing(gates.keep_wealth(ds), half))


class StaleKeepTests(unittest.TestCase):
    """THE STALE KEEP (the pooled adversarial round 2): a keep the pooled test
    made is not final; the guarded removal deciding later overrides it. A
    keep the current-rest test made stays final, ordered against the
    removal's stopping time as under `current`."""

    def stale(self, current_pairs):
        # Ten pairs gaining 0.4 beside an older rest, then a current rest
        # where the section gains nothing.
        return strat(OLD, GAIN, LOSS) + strat(MAIN, (FLAT * 2)[:current_pairs],
                                              (FLAT * 2)[:current_pairs], start=20)

    def test_a_pooled_keep_is_provisional_until_the_removal_decides(self):
        cell = cell_of(self.stale(20))
        self.assertEqual(cell["class"], "benefit", cell["reason"])
        self.assertIs(cell["rest_guard"]["keep_final"], False)
        self.assertIsNone(cell["rest_guard"]["current_keep_at"])
        self.assertIn("not final", cell["reason"])

    def test_the_guarded_removal_overrides_an_earlier_pooled_keep(self):
        # Thirty current pairs, under the cap, so the override, not the
        # lapse at the cap, ends the keep.
        runs = self.stale(30)
        v = verdict(runs)
        cell = v["cells"][0]
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertFalse(cell["at_cap"])
        self.assertNotEqual(v["verdict"], "keep")
        guard = cell["rest_guard"]
        # The pooled keep came first; the removal decided later, on the
        # guard (pair floor, the current rest's evidence, CLI versions).
        self.assertLess(guard["pooled_keep_at"], cell["remove_decided_at"])
        self.assertIsNotNone(guard["remove_evidence_at"])
        self.assertIs(guard["keep_final"], False)
        # `current` reads only the current rest, which never helped: it
        # removes too.
        self.assertEqual(cell_of(runs, CURRENT)["class"], "no-benefit")

    def test_older_gains_cannot_hold_the_removal_off_for_good(self):
        # Forty pairs gaining 0.4 beside an older rest starve the pooled
        # remove test's bets, so the guarded removal never decides; the
        # current rest's own remove test, in the removal evidence, does
        # (the pooled adversarial round 2's target: removed as `current`
        # removes it).
        runs = strat(OLD, GAIN * 4, LOSS * 4) + strat(MAIN, FLAT * 2, FLAT * 2, start=40)
        cell = cell_of(runs)
        guard = cell["rest_guard"]
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertIsNone(guard["remove_share_at"])
        self.assertIsNone(guard["pooled_remove_at"])
        self.assertIsNotNone(guard["current_remove_at"])
        self.assertLess(guard["pooled_keep_at"], cell["remove_decided_at"])
        self.assertIn("a pooled keep is not final", cell["reason"])
        self.assertEqual(cell_of(runs, CURRENT)["class"], "no-benefit")

    def test_the_override_needs_the_pair_floor(self):
        # The same older gains with five current pairs: the pooled keep has
        # not counted yet and no removal can decide.
        runs = strat(OLD, GAIN * 4, LOSS * 4) + strat(MAIN, FLAT[:5], FLAT[:5], start=40)
        cell = cell_of(runs)
        self.assertEqual(cell["class"], "insufficient", cell["reason"])
        self.assertIsNone(cell["remove_decided_at"])

    def test_a_planner_cell_reads_a_provisional_keep(self):
        self.assertTrue(plan_week.provisional_keep(cell_of(self.stale(20))))
        final = cell_of(strat(OLD, LOSS * 4, FLAT * 2) + strat(MAIN, GAIN, LOSS, start=40))
        self.assertFalse(plan_week.provisional_keep(final))
        self.assertFalse(plan_week.provisional_keep(cell_of(strat(MAIN, GAIN, LOSS), CURRENT)))
        self.assertFalse(plan_week.provisional_keep(None))

    def noisy(self, current_pairs, single_cli=False):
        # Forty older pairs gaining 0.4, then a current rest whose gain
        # swings between +0.4 and -0.3: neither keep test nor the removal
        # decides within its window.
        current = strat(MAIN, [(100, 100, 100), (30, 30, 30)] * 20,
                        [(60, 60, 60)] * 40, start=40)
        current = [r for r in current if r["timestamp"] in
                   {x["timestamp"] for x in current[:current_pairs]}]
        if single_cli:
            for run in current:
                run["cli_versions"] = ["1.0.0 (Claude Code)"]
        return strat(OLD, GAIN * 4, LOSS * 4) + current, current

    def test_a_pooled_keep_lapses_at_the_current_rests_cap(self):
        # Round 3's M1: before the cap the pooled keep stands (and is
        # fired); at the cap no more pairs can test it, so the cell ends on
        # the current rest's own rules, as `current` ends it.
        runs, _ = self.noisy(20)
        cell = cell_of(runs)
        self.assertEqual((cell["class"], cell["at_cap"]), ("benefit", False), cell["reason"])
        self.assertIs(cell["rest_guard"]["keep_final"], False)
        runs, current = self.noisy(40)
        cell = cell_of(runs)
        self.assertTrue(cell["at_cap"])
        self.assertEqual(cell["class"], "no-clear-effect", cell["reason"])
        self.assertIn("lapsed at the current rest's cap", cell["reason"])
        self.assertIsNotNone(cell["rest_guard"]["pooled_keep_at"])
        self.assertEqual(cell_of(current, CURRENT)["class"], "no-clear-effect")

    def test_a_lapsed_keep_on_one_cli_version_is_insufficient_at_the_cap(self):
        # As under `current`: one CLI version beside the current rest cannot
        # propose a removal, so the cell is `insufficient` at its cap (a
        # `cell-at-cap` item), never a silent keep.
        runs, current = self.noisy(40, single_cli=True)
        cell = cell_of(runs)
        self.assertEqual((cell["class"], cell["at_cap"]), ("insufficient", True),
                         cell["reason"])
        self.assertIn("lapsed at the current rest's cap", cell["reason"])
        self.assertEqual(cell["keep_tests"][0]["p"], 1.0)
        # Round 4's m(d): the note reaches the waiting path too, where the
        # removal crossed but one CLI version cannot decide it.
        runs = self.stale(40)
        for run in runs:
            if run["pair_key"] == MAIN:
                run["cli_versions"] = ["1.0.0 (Claude Code)"]
        cell = cell_of(runs)
        self.assertEqual((cell["class"], cell["at_cap"]), ("insufficient", True),
                         cell["reason"])
        self.assertIn("has not held at one pair", cell["reason"])
        self.assertIn("lapsed at the current rest's cap", cell["reason"])
        self.assertEqual(cell_of(current, CURRENT)["class"], "insufficient")

    def test_a_current_keep_after_the_removal_does_not_stand(self):
        # Round 3's m1 (the reviewer's M4): after an older rest's gains,
        # twenty-two current pairs gaining nothing, then eighteen gaining
        # 0.4. The removal decides before the current-rest keep crosses, so
        # the removal stands, as under `current`, and the pooled keep, which
        # came first, does not stand either.
        runs = strat(OLD, GAIN, LOSS) + strat(MAIN, (FLAT * 2)[:22] + (GAIN * 4)[:18],
                                              (FLAT * 2)[:22] + (LOSS * 4)[:18], start=20)
        cell = cell_of(runs)
        guard = cell["rest_guard"]
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertLess(guard["pooled_keep_at"], cell["remove_decided_at"])
        self.assertLess(cell["remove_decided_at"], guard["current_keep_at"])

    def test_a_pooled_keep_crossing_after_the_removal_does_not_stand(self):
        # Round 3's m1 (the reviewer's M3): the removal decides before the
        # pooled keep test crosses at all; the later crossing does not undo
        # it.
        runs = strat(OLD, FLAT[:10], FLAT[:10]) + strat(
            MAIN, (FLAT * 2)[:20] + (GAIN * 4)[:20], (FLAT * 2)[:20] + (LOSS * 4)[:20],
            start=20)
        cell = cell_of(runs)
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertLess(cell["remove_decided_at"], cell["rest_guard"]["pooled_keep_at"])

    def test_a_current_rest_keep_stays_final_against_a_later_removal(self):
        # One older pair, then seven current pairs gaining 0.4 and 33 gaining
        # nothing: the current-rest keep crosses at pair 8, the removal
        # decides at 40, and the earlier keep stands, as under `current`.
        policy = {**POOLED, "benefit_confidence": 0.6}
        runs = strat(OLD, FLAT[:1], FLAT[:1]) + strat(
            MAIN, (GAIN * 4)[:7] + (FLAT * 2)[:33], (LOSS * 4)[:7] + (FLAT * 2)[:33],
            start=20)
        cell = cell_of(runs, policy)
        self.assertEqual(cell["class"], "benefit", cell["reason"])
        guard = cell["rest_guard"]
        self.assertIsNotNone(cell["remove_decided_at"])
        self.assertLessEqual(guard["current_keep_at"], cell["remove_decided_at"])
        self.assertIs(guard["keep_final"], True)

    def test_a_current_rest_keep_at_the_removals_pair_stands(self):
        # Round 4's m(e): a tie keeps (`current_keep <= remove_decided`).
        # One older pair, then forty current pairs gaining 0.08. The
        # removal evidence crosses at pair 35 but the current rest's second
        # CLI version first appears at pair 37, where the current-rest keep
        # also crosses: both at pair 37, and the keep stands.
        current = strat(MAIN, [(88, 88, 88)] * 40, [(80, 80, 80)] * 40, start=20)
        stamps = sorted({r["timestamp"] for r in current})
        for run in current:
            late = stamps.index(run["timestamp"]) >= 35
            run["cli_versions"] = ["1.0.1 (Claude Code)" if late else "1.0.0 (Claude Code)"]
        cell = cell_of(strat(OLD, FLAT[:1], FLAT[:1]) + current)
        guard = cell["rest_guard"]
        self.assertEqual((guard["current_keep_at"], cell["remove_decided_at"]), (37, 37))
        self.assertLess(guard["remove_evidence_at"], 37)
        self.assertEqual(cell["class"], "benefit", cell["reason"])
        self.assertIs(guard["keep_final"], True)

    def test_a_current_rest_keep_is_final(self):
        cell = cell_of(strat(OLD, LOSS * 4, FLAT * 2) + strat(MAIN, GAIN, LOSS, start=40))
        self.assertEqual(cell["class"], "benefit", cell["reason"])
        self.assertIs(cell["rest_guard"]["keep_final"], True)
        self.assertNotIn("not final", cell["reason"])

    def test_current_has_no_keep_final_field(self):
        cell = cell_of(strat(MAIN, GAIN, LOSS), CURRENT)
        self.assertEqual(cell["class"], "benefit")
        self.assertIsNone(cell.get("rest_guard"))


class RemovalGuardTests(unittest.TestCase):
    """THE CURRENT-REST GUARD: a no-benefit or harm decision needs at least
    `rest_guard_min_pairs` pairs beside the current rest, spanning
    `min_cli_versions`, and the current rest's share of the pooled test's
    wealth at the retire level on its own."""

    def test_old_rests_alone_never_remove(self):
        cell = cell_of(strat(OLD, FLAT * 2, FLAT * 2))
        self.assertIsNotNone(cell["objective"]["remove_at"])
        self.assertIsNotNone(cell["rest_guard"]["pooled_remove_at"])
        self.assertEqual(cell["class"], "insufficient", cell["reason"])
        self.assertIsNone(cell["remove_decided_at"])
        self.assertIsNone(cell["rest_guard"]["remove_share_at"])

    def test_the_removal_decides_on_the_current_rests_evidence_alone(self):
        # Older pairs that first win and then lose leave the pooled wealth
        # below its level when the current rest's removal evidence reaches
        # its own. Round 3's m5: the removal no longer waits for the pooled
        # wealth (round 1's M10 rule), since the evidence alone carries the
        # level. Four old pairs with no gain, two gaining 0.8, then main's
        # no gain.
        runs = (strat(OLD, FLAT[:4] + [(100, 100, 100)] * 2,
                      FLAT[:4] + [(20, 20, 20)] * 2)
                + strat(MAIN, FLAT * 2, FLAT * 2, start=6))
        cell = cell_of(runs)
        threshold = -gates.math.log(1 - POOLED["retire_confidence"])
        ds = gates.differences(gates.pair_runs([r for r in runs if r["role"] == "with"],
                                               [r for r in runs if r["role"] == "without"])[0])
        wealth = gates.remove_wealth(ds, POOLED["objective_margin"])
        guard = cell["rest_guard"]
        decided = cell["remove_decided_at"]
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertEqual(decided, guard["remove_evidence_at"])
        self.assertLess(wealth[decided - 1], threshold)
        self.assertGreater(guard["pooled_remove_at"], decided)
        self.assertGreaterEqual(guard["remove_evidence_confidence"],
                                POOLED["retire_confidence"])

    def test_the_guard_blocks_a_removal_with_too_few_current_pairs(self):
        # Twenty old pairs and eighteen beside main, all with identical arms:
        # main's share reaches the level on its own, so with a guard of 6
        # pairs the cell is no-benefit; with a guard of 20 it is not yet.
        runs = (strat(OLD, FLAT, FLAT)
                + strat(MAIN, FLAT[:18], FLAT[:18], start=20))
        cell = cell_of(runs)
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertEqual(cell["rest_guard"]["usable_current_rest_pairs"], 18)
        self.assertEqual(cell["current_rest_pairs"], 18)
        self.assertIsNotNone(cell["rest_guard"]["remove_share_at"])
        strict = cell_of(runs, {**POOLED, "rest_guard_min_pairs": 20})
        self.assertEqual(strict["class"], "insufficient", strict["reason"])
        self.assertIn("at least 20 pairs beside the current rest (18 so far)",
                      strict["reason"])
        self.assertFalse(strict["rest_guard"]["met_pairs"])

    def test_the_guard_blocks_a_removal_the_current_rest_contradicts(self):
        # Thirty old pairs with no gain decide the pooled remove test; beside
        # main the section gains 0.2, above the margin. The current rest's
        # share falls, so the cell never shows no benefit.
        runs = (strat(OLD, (FLAT * 2)[:30], (FLAT * 2)[:30])
                + strat(MAIN, HELP[:20], FLAT, start=30))
        cell = cell_of(runs)
        self.assertIsNotNone(cell["objective"]["remove_at"])
        self.assertNotEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertIsNone(cell["remove_decided_at"])
        self.assertIsNone(cell["rest_guard"]["remove_share_at"])
        self.assertLess(cell["rest_guard"]["no_help_confidence"],
                        POOLED["retire_confidence"])

    def test_the_current_rest_needs_two_cli_versions_of_its_own(self):
        runs = strat(OLD, FLAT, FLAT) + strat(MAIN, FLAT, FLAT, start=20)
        for run in runs:
            if run["pair_key"] == MAIN:
                run["cli_versions"] = ["1.0.0 (Claude Code)"]
        cell = cell_of(runs)
        self.assertEqual(cell["class"], "insufficient", cell["reason"])
        self.assertIn("spanning 2 CLI versions (1 so far)", cell["reason"])

    def test_the_harm_test_is_guarded_too(self):
        # Beside an old rest the section cost 0.5; beside main the without
        # arm is at the top and the arms are equal. The pooled harm test
        # crosses, but main shows no harm, so the cell is not no-benefit and
        # its harm does not count as crossed.
        runs = (strat(OLD, LOSS + LOSS, TOP[:20])
                + strat(MAIN, TOP[:3], TOP[:3], start=20))
        cell = cell_of(runs)
        self.assertIsNotNone(cell["rest_guard"]["pooled_harm_at"])
        self.assertIsNone(cell["harm_at"])
        self.assertNotEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertIsNone(cell["harm_decided_at"])

    def test_the_guard_reaches_the_verdict(self):
        runs = strat(OLD, FLAT * 2, FLAT * 2)
        v = verdict(runs)
        self.assertEqual(v["verdict"], "insufficient")
        self.assertNotIn("removal", v)


class ParkingReadsTheCurrentRestTests(unittest.TestCase):
    """Parking, setting aside and the cap can lead toward a removal, so
    pooling must not loosen them: each reads the current rest alone."""

    def test_an_old_ceiling_does_not_park_the_cell(self):
        runs = strat(OLD, TOP[:20], TOP[:20]) + strat(MAIN, FLAT[:3], FLAT[:3], start=20)
        cell = cell_of(runs)
        self.assertNotIn(cell["class"], gates.PARKED_CLASSES, cell["reason"])
        self.assertIsNone(cell["ceiling_at"])
        self.assertAlmostEqual(cell["without_mean"], sum(
            sum(p) / 300 for p in FLAT[:3]) / 3)
        # The same ceiling beside main parks it, as before.
        self.assertEqual(cell_of(strat(MAIN, CEILING, CEILING))["class"], "ceiling")

    def test_an_old_floor_does_not_set_the_cell_aside(self):
        # Forty old pairs at the floor and three beside main: the pooled pass
        # rates (2.4 of 43) are under the floor fraction, the current rest's
        # are not (the pooled adversarial round 1's M4).
        zero = ZERO * 4
        runs = strat(OLD, zero, zero) + strat(MAIN, FLAT[:3], FLAT[:3], start=40)
        cell = cell_of(runs)
        self.assertLessEqual(cell["with"]["pass_rate"], POOLED["floor_fraction"])
        self.assertNotEqual(cell["class"], "cannot-discriminate")
        self.assertEqual(cell_of(strat(MAIN, ZERO, ZERO))["class"], "cannot-discriminate")

    def test_the_no_harm_test_reads_the_current_rest(self):
        # Old pairs gaining 0.4 reject the pooled no-harm test at once; three
        # current pairs losing 0.3 do not reject it (round 1's M5).
        runs = strat(OLD, GAIN, LOSS) + strat(MAIN, LOSS[:3], FLAT[:3], start=10)
        cell = cell_of(runs)
        ds = gates.differences(gates.pair_runs([r for r in runs if r["role"] == "with"],
                                               [r for r in runs if r["role"] == "without"])[0])
        self.assertIsNotNone(gates.first_crossing(
            gates.keep_wealth(ds, None, -POOLED["objective_margin"]),
            1 - POOLED["retire_confidence"]))
        self.assertIsNone(cell["noharm_at"])

    def test_the_cap_is_not_the_pooled_window(self):
        # Forty old pairs fill the old window; three current pairs on two CLI
        # versions must not make the cell no-clear-effect on older-rest data
        # (round 1's M8).
        noisy = [(100, 100, 100), (20, 20, 20)] * 20
        back = [(20, 20, 20), (100, 100, 100)] * 20
        runs = strat(OLD, noisy, back) + strat(MAIN, noisy[:3], back[:3], start=40)
        cell = cell_of(runs)
        self.assertEqual(cell["pairs_used"], 43)
        self.assertFalse(cell["at_cap"])
        self.assertEqual(cell["class"], "insufficient", cell["reason"])

    def test_the_cap_is_the_current_rests(self):
        # 45 old pairs fill only the old rest's window (40); the cell is not
        # at its cap and keeps being fired beside main.
        old = (FLAT * 3)[:45]
        runs = strat(OLD, old, old) + strat(MAIN, FLAT[:2], FLAT[:2], start=45)
        cell = cell_of(runs)
        self.assertEqual((cell["pairs"], cell["pairs_used"], cell["current_rest_pairs"]),
                         (47, 42, 2))
        self.assertFalse(cell["at_cap"])
        self.assertNotEqual(cell["class"], "no-clear-effect")

    def test_no_clear_effect_needs_the_current_rests_cap(self):
        # Neither test crosses on alternating gains and losses; 40 old
        # pairs do not make the cell no-clear-effect, 40 beside main do.
        noisy = [(100, 100, 100), (20, 20, 20)] * 20
        back = [(20, 20, 20), (100, 100, 100)] * 20
        old = cell_of(strat(OLD, noisy, back))
        self.assertEqual(old["class"], "insufficient", old["reason"])
        current = cell_of(strat(MAIN, noisy, back))
        self.assertEqual((current["class"], current["at_cap"]), ("no-clear-effect", True))


class NoStuckCellTests(unittest.TestCase):
    """The pooled adversarial round 1's blocker: a pooled harm or no-benefit
    crossing the older rests made alone held a cell `insufficient` at the
    current rest's cap for good. A full current window that shows benefit or
    a ceiling now ends as it would under `current`."""

    def test_older_harm_then_a_current_benefit_keeps_at_the_cap(self):
        runs = strat(OLD, (LOSS * 4)[:40], (FLAT * 2)) + strat(MAIN, HELP, FLAT * 2, start=40)
        cell = cell_of(runs)
        self.assertIsNotNone(cell["rest_guard"]["pooled_harm_at"])
        self.assertTrue(cell["at_cap"])
        self.assertEqual(cell["class"], "benefit", cell["reason"])
        self.assertEqual(cell_of(runs, CURRENT)["class"], "benefit")

    def test_older_no_benefit_then_a_current_benefit_keeps_at_the_cap(self):
        runs = strat(OLD, FLAT * 2, FLAT * 2) + strat(MAIN, HELP, FLAT * 2, start=40)
        cell = cell_of(runs)
        self.assertIsNotNone(cell["rest_guard"]["pooled_remove_at"])
        self.assertEqual(cell["class"], "benefit", cell["reason"])

    def test_older_harm_then_a_current_ceiling_parks(self):
        runs = strat(OLD, (LOSS * 4)[:40], TOP) + strat(MAIN, TOP, TOP, start=40)
        cell = cell_of(runs)
        self.assertIsNotNone(cell["rest_guard"]["pooled_harm_at"])
        self.assertTrue(cell["at_cap"])
        self.assertEqual(cell["class"], "ceiling", cell["reason"])
        self.assertEqual(cell_of(runs, CURRENT)["class"], "ceiling")

    def test_a_paused_ceiling_reads_the_current_rests_harm(self):
        # `_shows_ceiling` reads the current rest's harm evidence (round 4's
        # M3), not the pooled harm crossing older rests made.
        runs = strat(OLD, (LOSS * 4)[:40], TOP) + strat(MAIN, TOP, TOP, start=40)
        expect = {"fx": {**EXPECT["fx"], "scope_paused": "ceiling"}}
        v = verdict(runs, expect=expect)
        self.assertEqual((v["cells"][0]["class"], v["cells"][0]["class_before_pause"],
                          v["verdict"]), ("paused", "ceiling", "ceiling"))
        guard = {**cell_of(runs)["rest_guard"]}
        paused = {"class": "paused", "scope_paused": "ceiling", "class_before_pause": "ceiling",
                  "rest_guard": guard, "harm_at": 1}
        self.assertTrue(gates._shows_ceiling(paused))
        self.assertFalse(gates._shows_ceiling({**paused, "rest_guard": {
            **guard, "harm_evidence_at": 3}}))


class RoundFourTests(unittest.TestCase):
    """The pooled adversarial round 4: a cell with one rest is a `current`
    cell (M2), and the harm test decides on the current rest's evidence
    (M3)."""

    def test_a_cell_with_one_rest_classifies_as_current(self):
        # A differential over random cells beside the current rest alone:
        # the pooled rule gives the same cell, field for field, as
        # `current`, apart from the pooled fields it adds.
        import simulate_rest_guard as sim
        policy = gates.load_gate_policy()["guidance"]
        rng = sim.random.Random(20261107)
        extra = {"rest_policy", "current_rest_pairs", "rests", "rest_guard"}
        for i in range(60):
            effect = rng.choice((0.0, 0.05, 0.10, 0.15, 0.25, -0.1))
            n = rng.choice((5, 12, 25, 40))
            pairs, keys = sim.make_pairs(rng, 0, n, rng.choice((0.4, 0.55, 0.8)), 0.0, effect)
            with self.subTest(i=i, effect=effect, n=n):
                pooled = gates._classify(pairs, policy, 1, None,
                                         {"keys": keys, "current": sim.CURRENT,
                                          "min_pairs": policy["rest_guard_min_pairs"]})
                current = gates._classify(pairs, policy, 1, None)
                self.assertIsNone(pooled["rest_guard"])
                self.assertEqual({k: v for k, v in pooled.items() if k not in extra}, current)

    def test_older_pairs_with_no_run_mean_leave_one_rest(self):
        # The round 5 review's m2: older pairs with no objective figure add
        # nothing to pool, so the cell is still a one-rest `current` cell.
        import simulate_rest_guard as sim
        policy = gates.load_gate_policy()["guidance"]
        rng = sim.random.Random(11)
        extra = {"rest_policy", "current_rest_pairs", "rests", "rest_guard"}
        for i in range(40):
            pairs, keys = sim.make_pairs(rng, 5, rng.choice((12, 25, 40)), 0.55, 0.0,
                                         rng.choice((0.0, 0.10, 0.25)))
            for w, _o in pairs[:5]:
                w["numbers"]["run_mean"] = None
            with self.subTest(i=i):
                pooled = gates._classify(pairs, policy, 1, None,
                                         {"keys": keys, "current": sim.CURRENT,
                                          "min_pairs": policy["rest_guard_min_pairs"]})
                current = gates._classify(pairs[5:], policy, 1, None)
                self.assertIsNone(pooled["rest_guard"])
                self.assertEqual(pooled["class"], current["class"])
                self.assertEqual(pooled["objective"], current["objective"])
                self.assertEqual(pooled["keep_tests"], current["keep_tests"])

    def test_harm_today_is_removed_after_older_gains(self):
        # Forty older pairs gaining 0.4, then a current rest where the
        # section costs 0.35 from a without arm at 0.95: `current` removes
        # it on the harm test at pair 10; the pooled harm bets stay near 0,
        # so before round 4 it never did. Its harm evidence decides.
        current = strat(MAIN, [(60, 60, 60)] * 20, [(95, 95, 95)] * 20, start=40)
        cell = cell_of(strat(OLD, [(100, 100, 100)] * 40, [(60, 60, 60)] * 40) + current)
        guard = cell["rest_guard"]
        self.assertEqual(cell["class"], "no-benefit", cell["reason"])
        self.assertIn("harm test decided", cell["reason"])
        self.assertIsNone(guard["pooled_harm_at"])
        self.assertEqual(cell["harm_decided_at"], guard["harm_evidence_at"])
        self.assertGreaterEqual(guard["harm_evidence_confidence"],
                                POOLED["retire_confidence"])
        self.assertEqual(cell_of(current, CURRENT)["class"], "no-benefit")

    def test_harm_awaiting_a_second_cli_version_names_the_harm_evidence(self):
        # The round 4 review's minor 4: the harm decision reads the harm
        # evidence, so its awaiting reason says so.
        current = strat(MAIN, [(60, 60, 60)] * 20, [(95, 95, 95)] * 20, start=10)
        for run in current:
            run["cli_versions"] = ["1.0.0 (Claude Code)"]
        cell = cell_of(strat(OLD, [(80, 80, 80)] * 10, [(80, 80, 80)] * 10) + current)
        self.assertEqual(cell["class"], "insufficient", cell["reason"])
        self.assertIn(f"harm on the numbers (at pair {cell['rest_guard']['harm_evidence_at']} "
                      "the current rest's harm evidence reached its level)", cell["reason"])

    def test_the_harm_evidence_needs_the_pair_floor(self):
        current = strat(MAIN, [(60, 60, 60)] * 5, [(95, 95, 95)] * 5, start=40)
        cell = cell_of(strat(OLD, [(100, 100, 100)] * 40, [(60, 60, 60)] * 40) + current)
        self.assertIsNone(cell["harm_decided_at"])
        self.assertNotEqual(cell["class"], "no-benefit")


    def test_a_scope_pause_parks_a_provisional_keep(self):
        # The round 4 review's minor 2: a paused fixture gets no current-rest
        # runs, so a provisional pooled keep can never be confirmed; it is
        # parked like any other undecided cell. A final keep stays a keep.
        paused = {k: {**v, "scope_paused": "no-use"} for k, v in EXPECT.items()}
        out = verdict(StaleKeepTests().stale(20), expect=paused)
        cell = out["cells"][0]
        self.assertEqual((cell["class"], cell["class_before_pause"]), ("paused", "benefit"))
        self.assertNotEqual(out["verdict"], "keep")
        # The round 5 review's m1: its pooled route is no keep evidence.
        self.assertEqual([t["p"] for t in cell["keep_tests"]], [1.0, 1.0])
        self.assertEqual(explorer_data.subject_confidence(out)["helps"], 0.0)
        final = verdict(strat(OLD, LOSS * 4, FLAT * 2) + strat(MAIN, GAIN, LOSS, start=40),
                        expect=paused)
        self.assertTrue(final["cells"][0]["rest_guard"]["keep_final"])
        self.assertEqual((final["cells"][0]["class"], final["verdict"]), ("benefit", "keep"))


class CurrentReproducesTheOldRuleTests(unittest.TestCase):
    """`current` reads the runs beside the current rest and nothing else, and
    adds no field: its verdict on runs beside several rests is the verdict
    on the current rest's runs alone."""

    SCENARIOS = {
        "older flat, current flat": strat(OLD, FLAT, FLAT)
        + strat(MAIN, FLAT, FLAT, start=20),
        "older gain, current short": strat(OLD, GAIN, LOSS)
        + strat(MAIN, FLAT[:2], FLAT[:2], start=20),
        "two older rests": strat(OLDER, FLAT[:5], FLAT[:5])
        + strat(OLD, GAIN, LOSS, start=5) + strat(MAIN, GAIN, LOSS, start=30),
        "older ceiling": strat(OLD, TOP[:20], TOP[:20])
        + strat(MAIN, CEILING, CEILING, start=20),
    }

    def test_current_ignores_every_older_rest(self):
        for name, runs in self.SCENARIOS.items():
            with self.subTest(name):
                alone = [r for r in runs if r["pair_key"] == MAIN]
                got, want = verdict(runs, CURRENT), verdict(alone, CURRENT)
                for key in ("verdict", "reason", "removal"):
                    self.assertEqual(got.get(key), want.get(key))
                for a, b in zip(got["cells"], want["cells"]):
                    self.assertEqual({k: a.get(k) for k in ("class", "reason", "pairs",
                                                            "objective", "at_cap")},
                                     {k: b.get(k) for k in ("class", "reason", "pairs",
                                                            "objective", "at_cap")})
                    for field in ("rest_policy", "current_rest_pairs", "rests", "rest_guard"):
                        self.assertNotIn(field, a)

    def test_a_policy_without_the_key_is_pooled(self):
        # The default, for a policy built in code as for one read from YAML.
        runs = strat(OLD, GAIN, LOSS) + strat(MAIN, FLAT[:6], FLAT[:6], start=20)
        cell = cell_of(runs, TEST_POLICY)
        self.assertEqual(cell["class"], "benefit")
        self.assertIn("rest_guard", cell)


class PlannerTests(unittest.TestCase):
    """A cell whose pooled test leans to removal but whose current rest has
    too few pairs is fired: it is `insufficient`, not at its cap and not
    blocking, so it needs runs beside the current rest."""

    def planner_cell(self, gate_cell):
        return {"skill": "", "section": "sec", "fixture": "evals/guidance/sec/fx",
                "model": "model-a", "class": gate_cell["class"], "verdict": "insufficient",
                "in_situ_verdict": "insufficient", "with_runs": 40, "without_runs": 40,
                "newest": None, "usd_per_fire": None, "empty_fires": 0,
                "objective": gate_cell["objective"], "judge": None, "judge_carried": False,
                "reason": gate_cell["reason"], "with_counted": 40, "without_counted": 40,
                "pairs": gate_cell["pairs"], "at_cap": gate_cell["at_cap"],
                "current_rest_pairs": gate_cell["current_rest_pairs"]}

    def test_a_pooled_lean_without_current_pairs_is_fired(self):
        gate_cell = cell_of(strat(OLD, FLAT * 2, FLAT * 2))
        cell = self.planner_cell(gate_cell)
        self.assertEqual((cell["class"], cell["at_cap"]), ("insufficient", False))
        self.assertTrue(plan_week._produces_item(cell))
        self.assertFalse(plan_week._blocking(cell))
        ctx = {"cells": [cell], "model_weights": {"model-a": 1.0}, "removal_prs": [],
               "guidance_policy": POOLED, "policy": TEST_POLICY, "reservation": 1.0,
               "overrun": 1.0, "points_per_usd": None, "lessons": [], "skills": {}}
        focus, _ = plan_week.guidance_focus(ctx)
        self.assertEqual([f["section"] for f in focus], ["sec"])
        self.assertTrue(plan_week.leans_to_removal(cell, ctx))
        self.assertEqual(plan_week.fire_arms(cell, ctx), "both")

    def test_retire_progress_reads_the_removal_evidence(self):
        # Round 3's m3: a pooled cell's progress toward removal is the level
        # its removal evidence reached, what decides it, not the pooled
        # remove test's. Forty older pairs gaining 0.4 hold the pooled level
        # at 0 while the current rest's evidence passes the retire level.
        runs = strat(OLD, GAIN * 4, LOSS * 4) + strat(MAIN, FLAT * 2, FLAT * 2, start=40)
        gate_cell = cell_of(runs)
        cell = {**self.planner_cell(gate_cell), "rest_guard": gate_cell["rest_guard"]}
        level = POOLED["retire_confidence"]
        self.assertLess(gate_cell["objective"]["no_help_confidence"], 0.5)
        self.assertEqual(plan_week.retire_progress(cell, level),
                         gate_cell["rest_guard"]["remove_evidence_confidence"] / level)
        self.assertGreaterEqual(plan_week.retire_progress(cell, level), 1.0)
        # A cell without a guard (skills, `current`) reads its objective.
        plain = cell_of(strat(MAIN, FLAT * 2, FLAT * 2), CURRENT)
        self.assertEqual(plan_week.retire_progress({"objective": plain["objective"]}, level),
                         plain["objective"]["no_help_confidence"] / level)

    def test_the_explorer_reads_the_keep_routes_and_the_removal_evidence(self):
        # Round 3's m4: `helps` takes the best keep route, the current-rest
        # one included, and `no_help` a pooled cell's removal evidence.
        kept = verdict(strat(OLD, LOSS * 4, FLAT * 2) + strat(MAIN, GAIN, LOSS, start=40))
        cell = kept["cells"][0]
        best = min(t["p"] for t in cell["keep_tests"])
        self.assertLess(best, cell["keep_tests"][0]["p"])
        got = explorer_data.subject_confidence(kept)
        self.assertAlmostEqual(got["helps"], max(0.0, 1 - best))
        # Round 4's m(b): its pace counts the current rest's pairs.
        self.assertEqual(got["keep_pairs"], cell["rest_guard"]["usable_current_rest_pairs"])
        self.assertEqual(got["keep_pairs"], got["cells"][0]["pairs"])
        self.assertNotEqual(cell["current_rest_pairs"], cell["objective"]["pairs"])
        removed = verdict(strat(OLD, GAIN * 4, LOSS * 4) + strat(MAIN, FLAT * 2, FLAT * 2,
                                                                start=40))
        got = explorer_data.subject_confidence(removed)
        # Round 4's m(a): the overridden pooled keep reports no keep level.
        self.assertEqual(removed["cells"][0]["keep_tests"][0]["p"], 1.0)
        self.assertEqual(got["no_help_pairs"], 40)
        self.assertEqual(got["no_help"],
                         removed["cells"][0]["rest_guard"]["remove_evidence_confidence"])
        self.assertGreater(got["no_help"],
                           removed["cells"][0]["objective"]["no_help_confidence"])
        # The round 4 review's minor 3: the gain chart shows the current
        # rest's own figures, not the pooled block (here +20 points pooled,
        # 0 today).
        row = got["cells"][0]
        current = removed["cells"][0]["rest_guard"]["current_objective"]
        self.assertEqual((row["pairs"], row["gain"]), (40, 0.0))
        self.assertEqual(row["low"], round(current["benefit_lower"] * 100, 1) + 0.0)
        self.assertEqual(row["high"], round(current["retire_upper"] * 100, 1) + 0.0)
        self.assertNotEqual(row["gain"],
                            round(removed["cells"][0]["objective"]["delta"] * 100, 1))

    def test_the_explorer_charts_only_current_rest_figures(self):
        # The round 5 review's m3 and m4: a pooled cell with no current-rest
        # figure gives no chart row (never the pooled block), a malformed
        # guard gives none either, and the row's pairs and the pace both
        # count the usable current-rest pairs.
        removed = verdict(strat(OLD, GAIN * 4, LOSS * 4) + strat(MAIN, FLAT * 2, FLAT * 2,
                                                                start=40))
        cell = removed["cells"][0]
        self.assertIsNotNone(explorer_data.confidence_cell(cell))
        for guard in ({**cell["rest_guard"], "current_objective": None},
                      {**cell["rest_guard"], "current_objective": "bad"}, "bad"):
            with self.subTest(guard=str(guard)[:20]):
                self.assertIsNone(explorer_data.confidence_cell({**cell, "rest_guard": guard}))
        guard = {**cell["rest_guard"], "usable_current_rest_pairs": 30,
                 "current_objective": {**cell["rest_guard"]["current_objective"],
                                       "pairs": 30}}
        got = explorer_data.subject_confidence({**removed, "cells": [{**cell,
                                                                     "rest_guard": guard}]})
        self.assertNotEqual(cell["current_rest_pairs"], 30)
        self.assertEqual((got["cells"][0]["pairs"], got["max_pairs"], got["no_help_pairs"]),
                         (30, 30, 30))

    def test_the_cost_to_a_verdict_counts_the_current_rests_pairs(self):
        cell = self.planner_cell(cell_of(strat(OLD, FLAT * 2, FLAT * 2)))
        self.assertEqual(plan_week.subject_cost([cell], {"model-a": 1.0}, 10.0, cap=40), 10.0)

    def ctx(self, cells):
        return {"cells": cells, "model_weights": {"model-a": 1.0}, "removal_prs": [],
                "guidance_policy": POOLED, "policy": TEST_POLICY, "reservation": 1.0,
                "overrun": 1.0, "points_per_usd": None, "lessons": [], "skills": {},
                "batch": None}

    def kept_cell(self, gate_cell):
        cell = self.planner_cell(gate_cell)
        cell.update(verdict="keep", in_situ_verdict="keep",
                    provisional_keep=plan_week.provisional_keep(gate_cell),
                    rest_guard=gate_cell.get("rest_guard"),
                    keep_tests=gate_cell.get("keep_tests"))
        return cell

    def bands_of(self, cells):
        bands, _work = plan_week.eval_items(self.ctx(cells), NOW)
        return {band: [(i["fixture"], i["model"]) for i in items]
                for band, items in bands.items() if items}

    def test_a_pooled_keep_is_fired_until_the_current_window_is_full(self):
        # The round 2 override needs current-rest pairs, so a provisional
        # keep is fired (no re-check due) while its window has room.
        cell = self.kept_cell(cell_of(StaleKeepTests().stale(20)))
        self.assertTrue(cell["provisional_keep"])
        # Round 4's M1: as an undecided cell, in the focus band.
        self.assertEqual(self.bands_of([cell]), {"focus": [(cell["fixture"], "model-a")]})
        # At the cap the window is frozen: no fire.
        self.assertEqual(self.bands_of([{**cell, "at_cap": True}]), {})

    def test_the_plans_cells_carry_the_provisional_keep(self):
        # eval_cells_and_outages, on the committed evals/ and a gates
        # document whose one cell keeps on a pooled keep alone.
        section = "anything-you-name-gets-its-link"
        fixture = f"evals/guidance/{section}/handoff"
        real = plan_week.schedule.scheduled_fixtures

        def scheduled(path, committed):
            return [f for f in real(path, committed) if f != fixture] + [fixture]

        for gate, want in ((cell_of(StaleKeepTests().stale(20)), True),
                           (cell_of(strat(MAIN, GAIN, LOSS)), False)):
            doc = {"roster_models": ["model-a"], "skills": {}, "guidance": {section: {
                "verdict": "keep",
                "cells": [{**gate, "fixture": "handoff", "model": "model-a"}]}}}
            with self.subTest(want=want), \
                    mock.patch.object(plan_week.schedule, "scheduled_fixtures", scheduled):
                cells, _, _ = plan_week.eval_cells_and_outages(ROOT / "evals", doc, [], NOW)
                mine = [c for c in cells if c["fixture"] == fixture]
                self.assertEqual([(c["class"], c["provisional_keep"]) for c in mine],
                                 [("benefit", want)])

    # A full focus band needs more focus sections than the standing 2.
    @mock.patch.object(plan_week, "GUIDANCE_FOCUS_SECTIONS", 40)
    def test_a_pooled_keep_is_fired_with_a_full_focus_band(self):
        # Round 4's M1: in the recheck band, which has no share, sixty
        # undecided sections filling the focus band starved the provisional
        # keep, so it never lapsed and its section's `keep` held. Now its
        # section stays eligible for the focus (`verdict_open`) and its cell
        # is fired there.
        provisional = self.kept_cell(cell_of(StaleKeepTests().stale(20)))
        others = []
        for i in range(60):
            other = self.planner_cell(cell_of(strat(MAIN, FLAT[:3], FLAT[:3])))
            other.update({"section": f"s{i:02d}", "fixture": f"evals/guidance/s{i:02d}/fx",
                          "verdict": None, "in_situ_verdict": None, "objective": None,
                          "class": "missing"})
            others.append(other)
        ctx = self.ctx([provisional] + others)
        self.assertTrue(plan_week.verdict_open([provisional]))
        self.assertIn("sec", [f["section"] for f in plan_week.guidance_focus(ctx)[0]])
        bands, _ = plan_week.eval_items(ctx, NOW)
        self.assertGreaterEqual(len(bands["focus"]), 20)
        chosen = plan_week.allocate(bands, 20.0, 20)
        self.assertEqual(len(chosen), 20)
        self.assertIn((provisional["fixture"], "focus"),
                      [(c["fixture"], c["band"]) for c in chosen])

    def test_a_pooled_keep_is_fired_while_a_batch_leaves_its_section_out(self):
        # The round 4 review's M1: once a batch is active, focus and
        # guidance-rest take only member cells, and a section a blocking
        # sibling (insufficient at the cap) keeps out of the batch would
        # strand its provisional keep. A provisional keep is exempt.
        provisional = self.kept_cell(cell_of(StaleKeepTests().stale(20)))
        blocked = self.planner_cell(cell_of(strat(MAIN, FLAT[:3], FLAT[:3])))
        blocked.update({"fixture": "evals/guidance/sec/fx2", "verdict": "keep",
                        "in_situ_verdict": "keep", "at_cap": True, "class": "insufficient"})
        self.assertTrue(plan_week._blocking(blocked))
        ctx = self.ctx([provisional, blocked])
        self.assertEqual(plan_week.batch_subjects(ctx)[("guidance", "sec")]["status"], "blocked")
        ctx["batch"] = {"record": {"members": [{"kind": "guidance", "subject": "other"}]}}
        bands, _ = plan_week.eval_items(ctx, NOW)
        fired = [(i["fixture"], band) for band, items in bands.items() for i in items]
        self.assertIn((provisional["fixture"], "guidance-rest"), fired)
        # A non-provisional undecided cell of a non-member section stays out.
        undecided = {**provisional, "provisional_keep": False, "verdict": None,
                     "in_situ_verdict": None, "class": "insufficient", "at_cap": False}
        ctx = self.ctx([undecided, blocked])
        ctx["batch"] = {"record": {"members": [{"kind": "guidance", "subject": "other"}]}}
        bands, _ = plan_week.eval_items(ctx, NOW)
        self.assertEqual([i for items in bands.values() for i in items], [])

    def test_a_section_with_a_final_keep_is_not_open(self):
        provisional = self.kept_cell(cell_of(StaleKeepTests().stale(20)))
        final = self.kept_cell(cell_of(strat(OLD, LOSS * 4, FLAT * 2)
                                       + strat(MAIN, GAIN, LOSS, start=40)))
        self.assertFalse(plan_week.verdict_open([provisional, final]))
        self.assertFalse(plan_week.verdict_open([final]))
        self.assertTrue(plan_week.verdict_open([{**final, "verdict": None,
                                                 "class": "insufficient"}]))

    def test_keep_progress_reads_the_best_final_keep_route(self):
        # Round 4's m(c): a pooled cell's keep progress is 1 - the smallest
        # p over its keep routes; a provisional keep's pooled route does not
        # count.
        level = POOLED["benefit_confidence"]
        final = self.kept_cell(cell_of(strat(OLD, LOSS * 4, FLAT * 2)
                                       + strat(MAIN, GAIN, LOSS, start=40)))
        best = min(t["p"] for t in final["keep_tests"])
        self.assertAlmostEqual(plan_week.keep_progress(final, level), (1 - best) / level)
        gate = cell_of(StaleKeepTests().stale(20))
        provisional = self.kept_cell(gate)
        current_route = [t["p"] for t in gate["keep_tests"]
                         if t["route"] == "objective-current-rest"]
        self.assertAlmostEqual(plan_week.keep_progress(provisional, level),
                               max(0.0, 1 - current_route[0]) / level)
        self.assertLess(plan_week.keep_progress(provisional, level), 1.0)

    def test_a_final_keep_is_not_fired_before_its_recheck(self):
        gate = cell_of(strat(OLD, LOSS * 4, FLAT * 2) + strat(MAIN, GAIN, LOSS, start=40))
        cell = self.kept_cell(gate)
        self.assertFalse(cell["provisional_keep"])
        self.assertEqual(self.bands_of([cell]), {})

    def test_a_final_keep_on_another_cell_stops_the_provisional_fires(self):
        provisional = self.kept_cell(cell_of(StaleKeepTests().stale(20)))
        final = self.kept_cell(cell_of(strat(OLD, LOSS * 4, FLAT * 2)
                                       + strat(MAIN, GAIN, LOSS, start=40)))
        final.update(model="model-b", fixture="evals/guidance/sec/fx2")
        self.assertEqual(self.bands_of([provisional, final]), {})

    def test_the_rest_policy_of_a_verdict_document(self):
        self.assertEqual(plan_week.rest_policy_of({}), "current")
        self.assertEqual(plan_week.rest_policy_of({"guidance_policy": POOLED}),
                         "pooled-with-current-guard")
        self.assertEqual(plan_week.rest_policy_of({"guidance_policy": CURRENT}), "current")


class SimulationTests(unittest.TestCase):
    """scripts/simulate_rest_guard.py, seeded, on fewer simulations than the
    addendum's: the committed rule keeps a section that helps by exactly the
    margin beside the current rest under the 10% false-removal target, and
    the pooled tests without the guard do not."""

    def test_the_guard_holds_the_false_removal_rate(self):
        import simulate_rest_guard as sim
        policy = gates.load_gate_policy()["guidance"]
        rates = sim.drift(sim.random.Random(20261107), 200, policy, 40,
                          policy["objective_margin"], 0.55)
        target = 1 - policy["retire_confidence"]
        self.assertLessEqual(rates["pooled-with-current-guard"], target)
        self.assertLessEqual(rates["current"], target)
        self.assertGreater(rates["pooled, no guard"], target)
        self.assertGreater(rates["pooled, light guard"], target)

    def test_a_stale_keep_is_removed_and_a_margin_keep_is_not(self):
        # The pooled adversarial round 2: older gains of 0.30, then a current
        # rest with no gain (removed about as often as under `current`) or
        # one that helps by exactly the margin (removed under the level).
        import simulate_rest_guard as sim
        # The simulation was calibrated at the 40-pair cap the policy had
        # before 2026-11-12 (Adam cut it to 20); pin the cap it assumes.
        policy = {**gates.load_gate_policy()["guidance"], "max_runs_per_cell": 40}
        stale = sim.at_cap(sim.random.Random(20261107), 60, policy, 40, 0.30, 0.0, 0.55)
        self.assertGreaterEqual(stale["pooled-with-current-guard"]["no-benefit"], 0.8)
        margin = sim.at_cap(sim.random.Random(20261107), 60, policy, 40, 0.30,
                            policy["objective_margin"], 0.55)
        self.assertLessEqual(margin["pooled-with-current-guard"]["no-benefit"],
                             1 - policy["retire_confidence"])
        # Round 3's M1: none keeps on a pooled keep at the cap.
        for got in (stale, margin):
            self.assertEqual(got["pooled-with-current-guard"]["kept_provisionally"], 0.0)

    def test_no_cell_is_stuck_at_the_current_rests_cap(self):
        # Round 1's blocker: older-rest harm or no gain, a current rest that
        # helps by 0.25: every cell keeps at its cap, none stays insufficient.
        import simulate_rest_guard as sim
        policy = gates.load_gate_policy()["guidance"]
        for old_effect in (0.0, -0.2):
            with self.subTest(old_effect=old_effect):
                got = sim.at_cap(sim.random.Random(20261107), 60, policy, 40, old_effect,
                                 0.25, 0.55)["pooled-with-current-guard"]
                self.assertEqual((got["stuck"], got["no-benefit"]), (0.0, 0.0))
                self.assertGreaterEqual(got["benefit"], 0.95)


if __name__ == "__main__":
    unittest.main()
