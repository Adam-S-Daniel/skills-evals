#!/usr/bin/env python3
"""Planner over-fires of 2026-11-08 (scripts/plan_week.py after DEEP BEFORE
WIDE, #842), each pinned against harness/gates.py's own classification:

  * The sweep's plan job installed PyYAML alone, so compute_gates could not
    read any guidance section's digests (harness/guidance.py needs
    markdown-it-py) and every guidance cell read "pooling key incomplete":
    agent-contribution-markers, kept since 2026-11-07, was fired in the
    focus band about every 40 minutes. `gather` now refuses to plan with
    --guidance and no parser, and the job installs it.
  * A cell whose remove test had crossed but which that test cannot decide
    projected 0 pairs and led every plan: a HIGH cell (its without arm too
    high to show the margin) waits for the `ceiling-unconfirmed` stop, and
    a crossed test on one Claude Code version waits for a second version.
  * A provisional pooled keep was projected on the pooled moments and
    clamped to its cap, so its lapse at the cap read as a near verdict.
    Its routes are now the current rest's own keep test and the removal,
    on the current rest's moments; with neither under the cap it is past it.
  * gates' run utility labeled a provisional keep's runs `after_decision`
    from the pooled crossing; they are `building` until the keep is final.
  * A fire never carries a model whose cell is decided or held, also under
    PAIR_EVERY_FIRE.
  * `pairs_to_verdict` started each test from its PEAK log wealth (Ville's
    p and `reached`), but a test rejects only when its running wealth
    crosses, and betting wealth falls after a peak: a cell that peaked and
    fell read as near a verdict and was never flagged past its cap. gates
    now reports each test's current log wealth, and the planner starts
    there (the peak only for an older document without it).
  * `partly_decided` counted a parked cell (ceiling, ceiling-unconfirmed,
    paused) as settled, though it does not vote on removal, so a subject
    whose only non-open cell was parked was finished first.

Hermetic: canned runs and hand-built cells, `now` passed in, workflows
parsed with PyYAML. No network, clock or sleep.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
import statistics
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ISSUES))

import gates  # noqa: E402
import guidance  # noqa: E402
import plan_week  # noqa: E402
from test_issue_70_retirement import FLAT, FLAT_JUDGE, TEST_POLICY, cell, series  # noqa: E402
# The module, not the class: a TestCase bound to a name here is collected
# again, and the suite's count check (build_suite) then fails.
import test_issue_pooled_rest_guard as pooled_tests  # noqa: E402
from test_issue_pooled_rest_guard import POOLED, cell_of, verdict  # noqa: E402


NOW = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
A, B = "claude-sonnet-5-5", "claude-opus-5-5"
#: Equal arms with a without arm of 0.93 (high: above 1 - 0.15, and above
#: `high_stop_min_without`) and of 0.87 (high, but below it).
HIGH = [(93, 93, 93), (93, 93, 92)] * 20
MID = [(87, 87, 87), (87, 87, 86)] * 20


def planner_cell(gate_cell, *, section=None, skill="s", model=A, **over):
    """A gates cell as `eval_cells_and_outages` hands it to the planner."""
    base = {"skill": "" if section else skill, "section": section,
            "fixture": f"evals/guidance/{section}/a" if section else f"evals/{skill}/a",
            "model": model, "class": gate_cell["class"],
            "verdict": "keep" if gate_cell["class"] == "benefit" else "insufficient",
            "pairs": gate_cell["pairs"], "reason": gate_cell.get("reason"),
            "current_rest_pairs": gate_cell.get("current_rest_pairs"),
            "provisional_keep": plan_week.provisional_keep(gate_cell),
            "at_cap": gate_cell.get("at_cap") is True,
            "objective": gate_cell["objective"], "keep_tests": gate_cell["keep_tests"],
            "keep_family": gate_cell.get("keep_family", 1),
            "bet_prior": gate_cell.get("bet_prior"),
            "d_variance": plan_week.d_variance(gate_cell),
            "without_mean": gate_cell.get("without_mean"),
            "ceiling_at": gate_cell.get("ceiling_at"), "noharm_at": gate_cell.get("noharm_at"),
            "with_runs": gate_cell["pairs"], "without_runs": gate_cell["pairs"],
            "newest": None, "usd_per_fire": None, "empty_fires": 0,
            "with_counted": gate_cell["pairs"], "without_counted": gate_cell["pairs"]}
    if isinstance(gate_cell.get("rest_guard"), dict):
        base["rest_guard"] = gate_cell["rest_guard"]
    base.update(over)
    return base


def plan_ctx(cells, **over):
    base = {"policy": TEST_POLICY, "guidance_policy": POOLED, "reservation": 0.035,
            "overrun": 0.005, "improve_charge": 0.10, "room": 1.0, "points_per_usd": None,
            "model_weights": {A: 0.9, B: 0.1}, "removal_prs": [], "cells": cells,
            "skills": {}, "lessons": []}
    base.update(over)
    return base


def skill_cell(pattern, n, **kw):
    """`classify_cell` of n pairs of equal arms on `pattern`."""
    return cell(series("with", pattern[:n], FLAT_JUDGE * 4, **kw),
                series("without", pattern[:n], FLAT_JUDGE * 4, **kw))


class HighCellTests(unittest.TestCase):
    """harness/gates.py rule 6: a high cell's remove test never decides it."""

    def test_a_crossed_remove_test_on_a_high_cell_is_not_zero_pairs(self):
        gate = skill_cell(HIGH, 19)
        self.assertEqual(gate["class"], "insufficient", gate["reason"])
        self.assertIsNotNone(gate["objective"]["remove_at"])
        projection = plan_week.pairs_to_verdict(planner_cell(gate), plan_ctx([]))
        # The gate stops it at max_runs_high_cell (20): one more pair.
        self.assertEqual(projection["pairs"], TEST_POLICY["max_runs_high_cell"] - 19)
        self.assertEqual(skill_cell(HIGH, 20)["class"], "ceiling-unconfirmed")

    def test_the_projection_counts_down_to_the_ceiling_stop(self):
        for n in (8, 12, 16):
            with self.subTest(pairs=n):
                gate = skill_cell(HIGH, n)
                projection = plan_week.pairs_to_verdict(planner_cell(gate), plan_ctx([]))
                self.assertEqual(projection["remove"], TEST_POLICY["max_runs_high_cell"] - n)

    def test_a_high_cell_below_the_stop_level_is_past_its_cap(self):
        # 0.87: high, but the stop needs 0.90, so only the cap ends it.
        gate = skill_cell(MID, 19)
        self.assertEqual(gate["class"], "insufficient", gate["reason"])
        self.assertIsNotNone(gate["objective"]["remove_at"])
        projection = plan_week.pairs_to_verdict(planner_cell(gate), plan_ctx([]))
        self.assertTrue(math.isinf(projection["remove"]))
        self.assertTrue(projection["past_cap"])

    def test_the_planner_cell_carries_the_high_cell_fields(self):
        gate = skill_cell(HIGH, 19)
        doc = {"roster_models": [A], "guidance": {},
               "skills": {"writing-adrs": {"verdict": "insufficient", "cells": [
                   {**gate, "fixture": "bootstrap", "model": A}]}}}
        with mock.patch.object(plan_week.schedule, "scheduled_fixtures",
                               lambda path, committed: ["evals/writing-adrs/bootstrap"]):
            cells, _outages, _down = plan_week.eval_cells_and_outages(
                ROOT / "evals", doc, [], NOW, "git version 2.50.0")
        (got,) = cells
        self.assertEqual((got["without_mean"], got["noharm_at"], got["ceiling_at"]),
                         (gate["without_mean"], gate["noharm_at"], gate["ceiling_at"]))

    def test_a_high_cell_no_longer_leads_the_near_band(self):
        close = [0.4, 0.0, 0.2, 0.4, 0.0, 0.2, 0.4, 0.0]
        near = {"skill": "close", "section": None, "fixture": "evals/close/a", "model": A,
                "class": "insufficient", "verdict": "insufficient", "with_runs": 8,
                "without_runs": 8, "newest": None, "usd_per_fire": None, "empty_fires": 0,
                "pairs": 8, "keep_family": 1, "bet_prior": None, "d_variance": 0.04,
                "objective": gates.sequence_block(close, 0.15, 0.2, 0.1, None)}
        near["keep_tests"] = [{"route": "objective", "p": near["objective"]["keep_p"]}]
        stuck = planner_cell(skill_cell(HIGH, 10), skill="stuck")
        bands, _work = plan_week.eval_items(plan_ctx([stuck, near]), NOW)
        order = [i["skill"] for i in sorted(bands["near"], key=lambda i: i["order"])]
        self.assertEqual(order, ["close", "stuck"])


class CliVersionTests(unittest.TestCase):

    def test_a_crossed_remove_test_on_one_cli_version_has_no_projection(self):
        gate = skill_cell([(80, 80, 80), (80, 80, 79)] * 20, 20, cli="1.0.0 (Claude Code)")
        self.assertEqual(gate["class"], "insufficient", gate["reason"])
        self.assertIsNotNone(gate["objective"]["remove_at"])
        projection = plan_week.pairs_to_verdict(planner_cell(gate), plan_ctx([]))
        self.assertEqual(projection["blocked"], plan_week.BLOCKED_CLI_VERSIONS)
        self.assertTrue(math.isinf(projection["remove"]))
        self.assertFalse(projection["past_cap"])
        stamp = plan_week.depth_order(planner_cell(gate), plan_ctx([]), 0.1, set())
        self.assertTrue(math.isinf(stamp[2]))

    def test_the_same_cell_on_two_versions_decides(self):
        gate = skill_cell([(80, 80, 80), (80, 80, 79)] * 20, 20)
        self.assertEqual(gate["class"], "no-benefit", gate["reason"])


class ProvisionalKeepTests(unittest.TestCase):
    """THE STALE KEEP: a pooled keep is final only on the current rest's own
    keep test; a removal on the current rest's evidence overrides it."""

    def projection(self, gate):
        cell_ = planner_cell(gate, section="sec")
        self.assertTrue(cell_["provisional_keep"])
        return plan_week.pairs_to_verdict(cell_, plan_ctx([]))

    def test_a_provisional_keep_with_only_the_lapse_left_is_past_its_cap(self):
        runs, _current = pooled_tests.StaleKeepTests().noisy(20)
        projection = self.projection(cell_of(runs))
        self.assertGreater(projection["keep"], projection["remaining"])
        self.assertGreater(projection["remove"], projection["remaining"])
        self.assertTrue(projection["past_cap"])

    def test_the_removal_that_overrides_it_is_projected_on_the_current_rest(self):
        stale = pooled_tests.StaleKeepTests()
        for n, decides in ((14, 22), (20, 22)):
            with self.subTest(current_pairs=n):
                projection = self.projection(cell_of(stale.stale(n)))
                self.assertFalse(projection["past_cap"])
                # The gate overrides the keep at 22 current pairs.
                self.assertLessEqual(abs(projection["pairs"] - (decides - n)), 1.0)
                self.assertTrue(math.isinf(projection["keep"]))

    def test_the_spent_pooled_crossing_moves_nothing(self):
        gate = cell_of(pooled_tests.StaleKeepTests().stale(20))
        base = self.projection(gate)
        richer = {**gate, "objective": {**gate["objective"], "delta": 0.9}}
        self.assertEqual(self.projection(richer)["pairs"], base["pairs"])

    def test_a_reported_route_p_reaches_the_full_keep_alpha(self):
        # gates doubles each route's p and runs it at half the alpha, so a
        # reported p at the cell's keep alpha is a rejected route.
        gate = cell_of(pooled_tests.StaleKeepTests().stale(20))
        alpha = 1 - POOLED["benefit_confidence"]
        cell_ = planner_cell(gate, section="sec", provisional_keep=False, keep_tests=[
            {"route": "objective", "p": 1.0},
            {"route": "objective-current-rest", "p": alpha}])
        self.assertEqual(plan_week.pairs_to_verdict(cell_, plan_ctx([]))["keep"], 0.0)


class RunUtilityTests(unittest.TestCase):

    @staticmethod
    def classes(runs):
        out = Counter()
        for row in verdict(runs)["run_utility"]:
            out[row["class"]] += row["runs"]
        return dict(out)

    def test_a_provisional_keeps_runs_are_building(self):
        runs = pooled_tests.StaleKeepTests().stale(20)
        self.assertIs(cell_of(runs)["rest_guard"]["keep_final"], False)
        self.assertEqual(self.classes(runs), {"building": 2 * 30})

    def test_a_pooled_keep_decides_where_it_became_final(self):
        from test_issue_pooled_rest_guard import GAIN, LOSS, MAIN, OLD, strat
        runs = strat(OLD, GAIN, LOSS) + strat(MAIN, GAIN, LOSS, start=20)
        gate = cell_of(runs)
        guard = gate["rest_guard"]
        self.assertIs(guard["keep_final"], True)
        self.assertGreater(guard["current_keep_at"], gate["decided_at"])
        self.assertEqual(self.classes(runs),
                         {"decisive": 2 * guard["current_keep_at"],
                          "after_decision": 2 * (gate["pairs"] - guard["current_keep_at"])})


class PairFireTests(unittest.TestCase):

    @staticmethod
    def leg(model, fixture="evals/x/a"):
        return {"mode": "eval", "arms": "both", "fixture": fixture, "model": model,
                "skill": "x", "holdout": "", "cost": 0.05, "band": "near", "order": ()}

    def test_every_fire_never_adds_a_decided_or_held_cell(self):
        base = {"fixture": "evals/x/a", "model": B, "class": "insufficient",
                "verdict": "insufficient", "schedulable": True, "empty_fires": 0}
        held = {"decided": {"class": "no-benefit"}, "parked": {"class": "ceiling-unconfirmed"},
                "at cap": {"at_cap": True}, "unschedulable": {"schedulable": False},
                "stakes none": {"stakes": "none"}, "broken": {"empty_fires": 2},
                "kept subject": {"verdict": "keep"}}
        for label, over in held.items():
            with self.subTest(other=label):
                cells = {("evals/x/a", B): {**base, **over}}
                self.assertEqual(plan_week.pair_every_fire([self.leg(A)], [A, B], cells),
                                 [self.leg(A)])
        self.assertEqual(plan_week.pair_every_fire([self.leg(A)], [A, B], {}), [self.leg(A)])
        # The control: an open sibling, pending or not yet due, is added.
        for over in ({}, {"pending": True}):
            cells = {("evals/x/a", B): {**base, **over}}
            (leg,) = plan_week.pair_every_fire([self.leg(A)], [A, B], cells)
            self.assertEqual(leg["model"], f"{A},{B}")

    def test_the_planner_never_pairs_a_decided_sibling(self):
        open_cell = {"skill": "x", "section": None, "fixture": "evals/x/a", "model": A,
                     "class": "insufficient", "verdict": "insufficient", "with_runs": 1,
                     "without_runs": 1, "newest": None, "usd_per_fire": None,
                     "empty_fires": 0}
        decided = {**open_cell, "model": B, "class": "no-benefit", "with_runs": 18,
                   "without_runs": 18}
        for every in (False, True):
            with self.subTest(pair_every_fire=every), \
                    mock.patch.object(plan_week, "PAIR_EVERY_FIRE", every):
                plan = plan_week.build_plan(plan_ctx([open_cell, decided],
                                                     roster_models=[A, B]), NOW, 10)
                self.assertEqual([f["model"] for f in plan["fires"]
                                  if f["fixture"] == "evals/x/a"], [A])
        # The control: two open cells make one pair fire.
        plan = plan_week.build_plan(plan_ctx([open_cell, {**open_cell, "model": B}],
                                             roster_models=[A, B]), NOW, 10)
        self.assertEqual([f["model"] for f in plan["fires"]], [f"{A},{B}"])


class GuidanceParserTests(unittest.TestCase):

    def test_planning_with_guidance_and_no_parser_is_refused(self):
        def missing():
            raise guidance.GuidanceError("no markdown-it-py")
        with mock.patch.object(guidance, "_markdown_it", missing):
            with self.assertRaises(plan_week.PlanError) as ctx:
                plan_week.require_guidance_parser(Path(tempfile.mkdtemp()))
            self.assertIn("markdown-it-py", str(ctx.exception))
            plan_week.require_guidance_parser(None)
        plan_week.require_guidance_parser(Path(tempfile.mkdtemp()))

    def test_gather_checks_the_parser_first(self):
        def missing():
            raise guidance.GuidanceError("no markdown-it-py")
        args = mock.Mock(guidance=Path(tempfile.mkdtemp()))
        with mock.patch.object(guidance, "_markdown_it", missing), \
                mock.patch("compute_gates.compute") as compute:
            with self.assertRaises(plan_week.PlanError):
                plan_week.gather(args, NOW)
        compute.assert_not_called()

    def test_the_headroom_check_refuses_without_the_parser(self):
        def missing():
            raise guidance.GuidanceError("no markdown-it-py")
        with mock.patch.object(guidance, "_markdown_it", missing), \
                mock.patch("compute_gates.compute") as compute:
            with self.assertRaises(plan_week.PlanError):
                plan_week.guidance_headroom("example-section", Path(tempfile.mkdtemp()),
                                            Path(tempfile.mkdtemp()),
                                            Path(tempfile.mkdtemp()), "2026-11-08T00:00:00Z")
        compute.assert_not_called()

    def test_the_fire_job_installs_the_parser_before_the_headroom_check(self):
        doc = yaml.safe_load((ROOT / ".github" / "workflows" / "routine-eval-fire.yml")
                             .read_text(encoding="utf-8"))
        runs = [str(s.get("run") or "") for job in doc["jobs"].values()
                for s in job.get("steps", [])]
        at = next(i for i, r in enumerate(runs) if "plan_week.py guidance-headroom" in r)
        installs = " ".join(r for r in runs[:at] if "pip install" in r).split()
        self.assertIn("markdown-it-py==4.2.0", installs)

    def test_the_plan_job_installs_the_parser_before_planning(self):
        doc = yaml.safe_load((ROOT / ".github" / "workflows" / "routine-eval-weekly.yml")
                             .read_text(encoding="utf-8"))
        steps = doc["jobs"]["plan"]["steps"]
        runs = [str(s.get("run") or "") for s in steps]
        plan_at = next(i for i, r in enumerate(runs) if "scripts/plan_week.py plan" in r)
        installs = [i for i, r in enumerate(runs[:plan_at]) if "pip install" in r]
        self.assertTrue(installs)
        self.assertIn("markdown-it-py==4.2.0", " ".join(runs[i] for i in installs).split())
        self.assertIn("--guidance", runs[plan_at])


#: Paired differences whose keep wealth peaks at about 1.11 (below the keep
#: threshold, log 1/0.2 = 1.61) after four pairs and falls to about 0.15.
PEAKED = [0.5] * 4 + [-0.5] * 2 + [0.2] * 2
#: The mirror for the remove test: its wealth peaks, then falls.
PEAKED_REMOVE = [-0.5] * 4 + [0.6] * 3


def betting_cell(ds, *, current=True, **over):
    """A skill cell over `ds`, as the planner receives it from gates; with
    `current` False, an older verdict document with no current log wealth."""
    block = gates.sequence_block(ds, TEST_POLICY["objective_margin"],
                                 1 - TEST_POLICY["benefit_confidence"],
                                 1 - TEST_POLICY["retire_confidence"], None)
    route = {"route": "objective", "p": block["keep_p"],
             "log_wealth": block["keep_log_wealth"]}
    if not current:
        block = {k: v for k, v in block.items() if not k.endswith("_log_wealth")}
        route.pop("log_wealth")
    base = {"skill": "s", "section": None, "fixture": "evals/s/a", "model": A,
            "class": "insufficient", "verdict": "insufficient", "pairs": len(ds),
            "objective": block, "keep_tests": [route], "keep_family": 1,
            "bet_prior": None, "d_variance": statistics.variance(ds)}
    base.update(over)
    return base


class CurrentWealthTests(unittest.TestCase):
    """The projection starts from each test's current log wealth, not its
    peak: only a running crossing rejects."""

    def test_gates_reports_the_current_log_wealth_beside_the_peak(self):
        margin = TEST_POLICY["objective_margin"]
        keep = gates.keep_wealth(PEAKED)
        remove = gates.remove_wealth(PEAKED_REMOVE, margin)
        self.assertLess(keep[-1], max(keep))
        self.assertLess(remove[-1], max(remove))
        kept = gates.sequence_block(PEAKED, margin, 0.2, 0.1)
        self.assertAlmostEqual(kept["keep_log_wealth"], keep[-1], places=12)
        self.assertAlmostEqual(kept["keep_p"], math.exp(-max(keep)), places=12)
        removed = gates.sequence_block(PEAKED_REMOVE, margin, 0.2, 0.1)
        self.assertAlmostEqual(removed["no_help_log_wealth"], remove[-1], places=12)
        self.assertAlmostEqual(removed["no_help_confidence"],
                               1 - math.exp(-max(remove)), places=12)

    def test_a_classified_cell_carries_its_routes_current_log_wealth(self):
        gate = skill_cell(FLAT, 8)
        self.assertEqual([set(t) for t in gate["keep_tests"]],
                         [{"route", "p", "log_wealth"}])
        self.assertAlmostEqual(gate["keep_tests"][0]["log_wealth"],
                               gate["objective"]["keep_log_wealth"], places=12)
        for key in ("keep_log_wealth", "no_help_log_wealth"):
            self.assertTrue(plan_week._real(gate["objective"][key]), key)

    def test_a_pooled_cell_carries_its_removal_evidences_current_log_wealth(self):
        gate = cell_of(pooled_tests.StaleKeepTests().stale(20))
        guard = gate["rest_guard"]
        now = guard["remove_evidence_log_wealth"]
        self.assertTrue(plan_week._real(now))
        # Never above the peak the level was read from.
        self.assertLessEqual(now, -math.log(1 - guard["remove_evidence_confidence"]) + 1e-9)
        self.assertEqual([t["route"] for t in gate["keep_tests"]],
                         ["objective", "objective-current-rest"])
        for route in gate["keep_tests"]:
            if route["log_wealth"] is not None:
                # On its doubled p's scale: never above log 1/p.
                self.assertLessEqual(route["log_wealth"], -math.log(route["p"]) + 1e-9)
        self.assertIsNotNone(gate["keep_tests"][1]["log_wealth"])

    def test_a_cell_that_peaked_and_fell_is_projected_further(self):
        peak = plan_week.pairs_to_verdict(betting_cell(PEAKED, current=False), plan_ctx([]))
        now = plan_week.pairs_to_verdict(betting_cell(PEAKED), plan_ctx([]))
        self.assertGreater(now["keep"], peak["keep"] + 10)
        # The same for the remove test.
        peak = plan_week.pairs_to_verdict(betting_cell(PEAKED_REMOVE, current=False),
                                          plan_ctx([]))
        now = plan_week.pairs_to_verdict(betting_cell(PEAKED_REMOVE), plan_ctx([]))
        self.assertGreater(now["remove"], peak["remove"])

    def test_it_is_past_its_cap_when_the_gap_exceeds_the_pairs_left(self):
        # 25 pairs held leaves 15 under the cap of 40: the peak reads about
        # 9 pairs away, the current wealth about 27.
        peak = plan_week.pairs_to_verdict(betting_cell(PEAKED, current=False, pairs=25),
                                          plan_ctx([]))
        now = plan_week.pairs_to_verdict(betting_cell(PEAKED, pairs=25), plan_ctx([]))
        self.assertEqual(now["remaining"], 15)
        self.assertLess(peak["pairs"], 15)
        self.assertFalse(peak["past_cap"])
        self.assertGreater(now["pairs"], 15)
        self.assertTrue(now["past_cap"])

    def test_a_crossed_peak_still_counts_as_crossed(self):
        # A rejection is final: a keep route whose peak crossed projects 0
        # however far its wealth fell since.
        cell_ = betting_cell(PEAKED, keep_tests=[
            {"route": "objective", "p": 0.1, "log_wealth": -1.0}])
        self.assertEqual(plan_week.pairs_to_verdict(cell_, plan_ctx([]))["keep"], 0.0)


class ParkedCellTests(unittest.TestCase):
    """A parked cell does not vote on removal, so it settles nothing."""

    def plain(self, fixture, cls, skill="s"):
        return {"skill": skill, "section": None, "fixture": f"evals/{skill}/{fixture}",
                "model": A, "class": cls}

    def test_a_parked_cell_beside_open_ones_is_not_partly_decided(self):
        for parked in plan_week.PARKED_CLASSES:
            with self.subTest(parked=parked):
                cells = [self.plain("a", parked), self.plain("b", "insufficient"),
                         self.plain("c", "missing")]
                self.assertEqual(plan_week.partly_decided(cells), set())

    def test_a_settled_cell_still_counts_beside_a_parked_one(self):
        cells = [self.plain("a", "ceiling"), self.plain("b", "no-benefit"),
                 self.plain("c", "insufficient")]
        self.assertEqual(plan_week.partly_decided(cells), {("skill", "s")})

    def test_a_parked_provisional_keep_is_not_open_either(self):
        cells = [{**self.plain("a", "paused"), "provisional_keep": True},
                 self.plain("b", "no-benefit")]
        self.assertEqual(plan_week.partly_decided(cells), set())


if __name__ == "__main__":
    unittest.main()
