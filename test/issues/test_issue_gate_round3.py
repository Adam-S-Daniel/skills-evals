#!/usr/bin/env python3
"""PR 649's third adversarial round on the betting gate (2026-11-03).

Each class pins one finding of
/mnt/project-files/reports/pr649-adversarial-round3.md:

  * C1: a fixture the eval scope pass paused keeps its cells in the verdict,
    parked as `paused` (a keep it earned still keeps), so its subject's other
    cells cannot remove the subject automatically, for skills and guidance;
  * M2: a high cell stops at `max_runs_high_cell` pairs only once the
    no-harm test has rejected and its without arm is at least
    HIGH_STOP_MIN_WITHOUT; otherwise it is fired on to the cap;
  * M3: the keep is ordered against the removal's stopping time, and an
    undecided cell at the cap is a `cell-at-cap` work item;
  * M4: gates sets `at_cap` at exactly `max_runs_per_cell` pairs, and it
    reaches the planner;
  * the minors: one PARKED_CLASSES, the `high or ceiling_at` branch, the
    explorer's voting cells and no re-check of a decided cell at the cap.

Hermetic and deterministic: canned runs, temporary directories, no network,
no clock.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

ISSUES = Path(__file__).resolve().parent
ROOT = ISSUES.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ISSUES))

import compute_gates  # noqa: E402
import eval_scope  # noqa: E402
import explorer_data  # noqa: E402
import gates  # noqa: E402
import plan_week  # noqa: E402
import retire_skill  # noqa: E402
from test_issue_70_retirement import CLIS, POLICY, arm_run, cell, trial  # noqa: E402

CAP = POLICY["max_runs_per_cell"]
MODELS = ["model-a", "model-b"]


def pairs(fixture, n, without, with_, *, start=0, model="model-a", cli=None,
          skill="demo", in_situ=False):
    """`n` fires of one cell, each a without and a with run of one trial
    (`without` and `with_` checks passed of 100, ints or functions of the
    fire's index). CLI versions alternate unless `cli` (a function of the
    index) says otherwise. `in_situ` makes them a guidance section's in-situ
    pair beside the rest `rest`."""
    out = []
    for r in range(start, start + n):
        version = cli(r) if cli else None
        for role, passed in (("without", without), ("with", with_)):
            run = arm_run(role, [trial(passed(r) if callable(passed) else passed, 100, r)], r,
                          fixture=fixture, model=model, cli=version, skill=skill,
                          pair="rest" if in_situ else "p")
            if in_situ:
                run["pair"] = "in_situ"
                run["path"] = f"{run['path']}#in_situ"
            out.append(run)
    return out


def classify(n, with_, without, *, family=1, cli=None):
    """One cell of `n` fires, classified on the committed policy."""
    runs = pairs(None, n, without, with_, cli=cli)
    return cell([r for r in runs if r["role"] == "with"],
                [r for r in runs if r["role"] == "without"], policy=POLICY, family=family)


def expect(*fixtures, paused=(), rule="ceiling", rest=False):
    out = {}
    for name in fixtures:
        out[name] = {"fixture_digest": "f1", "tested_digest": "t1"}
        if rest:
            out[name]["rest_digest"] = "rest"
        if name in paused:
            out[name]["scope_paused"] = rule
    return out


class ScopePauseTests(unittest.TestCase):
    """C1: the reviewer's repro_scope_drop.py. Fixture a helps (without
    80/100, with 100/100), fixture b is flat (50 vs 50), two roster models,
    40 pairs each, CLI versions alternating. Dropping a paused a's cells
    turned `keep` into `retire` with `removal: auto`."""

    @staticmethod
    def runs(a_pairs=40, in_situ=False, skill="demo"):
        out = []
        for i, model in enumerate(MODELS):
            out += pairs("a", a_pairs, 80, 100, start=1000 * i, model=model,
                         skill=skill, in_situ=in_situ)
            out += pairs("b", 40, 50, 50, start=1000 * i + 200, model=model,
                         skill=skill, in_situ=in_situ)
        return out

    def skill_verdict(self, runs, expected):
        return gates.retirement({"runs": runs}, MODELS, "demo", POLICY, expected)

    def guidance_verdict(self, runs, expected):
        return gates.guidance_verdict({"runs": runs}, MODELS, "sec", POLICY, expected)

    def test_the_repro_kept_with_both_fixtures(self):
        v = self.skill_verdict(self.runs(), expect("a", "b"))
        self.assertEqual(v["verdict"], "keep")
        self.assertEqual([c["class"] for c in v["cells"]],
                         ["benefit", "benefit", "no-benefit", "no-benefit"])

    def test_a_paused_fixture_keeps_the_keep_it_earned(self):
        for verdict, runs, expected in (
                (self.skill_verdict, self.runs(), expect("a", "b", paused="a")),
                (self.guidance_verdict, self.runs(in_situ=True, skill="sec"),
                 expect("a", "b", paused="a", rest=True))):
            v = verdict(runs, expected)
            self.assertEqual(v["verdict"], "keep", v["reason"])
            a = [c for c in v["cells"] if c["fixture"] == "a"]
            self.assertEqual([c["class"] for c in a], ["benefit", "benefit"])
            self.assertEqual({c["scope_paused"] for c in a}, {"ceiling"})

    def test_a_paused_fixture_never_frees_an_auto_removal(self):
        # Paused after 3 pairs, before its keep: its cells are parked, not
        # dropped, so b's two no-benefit cells can only propose.
        for verdict, runs, expected in (
                (self.skill_verdict, self.runs(3), expect("a", "b", paused="a")),
                (self.guidance_verdict, self.runs(3, in_situ=True, skill="sec"),
                 expect("a", "b", paused="a", rest=True))):
            v = verdict(runs, expected)
            self.assertEqual((v["verdict"], v["removal"]), ("retire", "proposal"),
                             v["reason"])
            self.assertIn("paused by the eval scope pass", v["removal_reason"])
            a = [c for c in v["cells"] if c["fixture"] == "a"]
            self.assertEqual([(c["class"], c["class_before_pause"]) for c in a],
                             [("paused", "insufficient")] * 2)
            self.assertFalse(retire_skill.cells_allow_auto(v))
            self.assertIsNotNone(retire_skill.proposal_only({**v, "removal": "auto"}))
            gates_doc = {"skills": {"demo": v}, "roster_models": MODELS}
            self.assertEqual(retire_skill.retiring(gates_doc), "demo")
        # The same runs with a's cells dropped, as before the fix, would
        # have been automatic: the parking is what stops it.
        dropped = self.skill_verdict(self.runs(3), expect("b"))
        self.assertEqual(dropped["removal"], "auto")

    def test_a_subject_whose_every_cell_is_paused(self):
        runs = pairs("a", 3, 95, 95) + pairs("a", 3, 95, 95, model="model-b")
        ceiling = self.skill_verdict(runs, expect("a", paused="a"))
        self.assertEqual(ceiling["verdict"], "ceiling")
        for rule in ("zero-use", "floor"):
            v = self.skill_verdict(runs, expect("a", paused="a", rule=rule))
            self.assertEqual(v["verdict"], "insufficient", rule)
            self.assertNotIn("removal", v)
        # A cell of a paused fixture with no run is parked, not missing.
        v = self.skill_verdict(pairs("a", 3, 95, 95), expect("a", paused="a"))
        self.assertEqual([c["class"] for c in v["cells"]], ["paused", "paused"])
        self.assertEqual(v["cells"][1]["class_before_pause"], "missing")


class ScopePauseFilesTests(unittest.TestCase):
    """C1: compute_gates reads the pauses eval_scope records."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="round3-"))
        self.addCleanup(shutil.rmtree, self.root)
        self.evals = self.root / "evals"
        for name in ("a", "b", "c"):
            fixture = self.evals / "demo" / name
            fixture.mkdir(parents=True)
            (fixture / "fixture.yaml").write_text("skill: demo\n", encoding="utf-8")
        section = self.evals / "guidance" / "sec" / "fx"
        section.mkdir(parents=True)
        (section / "fixture.yaml").write_text("subject: guidance\nsection: sec\n",
                                              encoding="utf-8")
        (self.evals / "scope-auto.yml").write_text(
            "rows:\n"
            "  - path: evals/demo/a\n    rule: \"ceiling\"\n"
            "  - path: evals/guidance/sec/fx\n    rule: \"ceiling\"\n", encoding="utf-8")
        (self.evals / "unscheduled.yml").write_text(
            "fixtures:\n"
            "  - path: evals/demo/a\n"
            "    reason: \"Auto scope (ceiling), 2026-11-03: the without arm passed.\"\n"
            "  - path: evals/demo/b\n"
            "    reason: \"Auto scope (zero-use), 2026-11-03: no recorded use.\"\n"
            "  - path: evals/demo/c\n    reason: \"Held by hand.\"\n", encoding="utf-8")

    def test_the_prefix_and_file_are_eval_scopes(self):
        self.assertEqual(compute_gates.SCOPE_PAUSE_PREFIX, eval_scope.AUTO_PREFIX)
        self.assertEqual("evals/" + compute_gates.SCOPE_AUTO_FILE, eval_scope.SCOPE_AUTO)

    def test_paused_fixtures_are_kept_and_marked(self):
        self.assertEqual(compute_gates.scope_paused(self.evals),
                         {"evals/demo/a": "ceiling", "evals/demo/b": "zero-use",
                          "evals/guidance/sec/fx": "ceiling"})
        got = compute_gates.expected_content(self.evals, "demo", {}, keep_paused=True)
        self.assertEqual({k: v.get("scope_paused") for k, v in got.items()},
                         {"a": "ceiling", "b": "zero-use"})
        # The improve loop's callers still leave paused fixtures out, and a
        # row the scope pass did not write still drops its fixture.
        self.assertEqual(compute_gates.expected_content(self.evals, "demo", {}), {})
        got = compute_gates.expected_guidance(self.evals, "sec", None)
        self.assertEqual(got["fx"]["scope_paused"], "ceiling")

    def test_a_malformed_scope_file_raises(self):
        (self.evals / "scope-auto.yml").write_text("rows: [1, 2]\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            compute_gates.scope_paused(self.evals)


class HighStopTests(unittest.TestCase):
    """M2: the 20-pair stop on a sample mean hid harm and parked helpful
    cells."""

    def test_a_harm_at_a_high_without_arm_is_fired_on_and_found(self):
        # Without 95, with 85 (D = -0.10): the reviewer's 92%-hidden shape.
        stopped = classify(20, 85, 95)
        self.assertEqual(stopped["class"], "insufficient", stopped["reason"])
        self.assertIsNone(stopped["noharm_at"])
        found = classify(40, 85, 95)
        self.assertEqual((found["class"], found["harm_decided_at"]), ("no-benefit", 29),
                         found["reason"])

    def test_a_high_cell_under_the_slack_is_fired_on_and_keeps(self):
        # Without 88, with 100 (D = +0.12), a family of 4: the no-harm test
        # rejects at pair 11, but 0.88 is under HIGH_STOP_MIN_WITHOUT.
        early = classify(20, 100, 88, family=4)
        self.assertEqual(early["class"], "insufficient", early["reason"])
        self.assertEqual(early["noharm_at"], 11)
        self.assertEqual(classify(40, 100, 88, family=4)["class"], "benefit")

    def test_the_clean_case_still_stops_at_twenty(self):
        top = classify(20, 96, 96)
        self.assertEqual(top["class"], "ceiling-unconfirmed", top["reason"])
        self.assertEqual(classify(19, 96, 96)["class"], "insufficient")

    def test_a_high_cell_the_stop_did_not_take_ends_on_the_cap_rule(self):
        # Without 88, with 84: no test decides, the remove test does not
        # decide a high cell, and at the cap it has no clear effect.
        self.assertEqual(classify(CAP - 1, 84, 88)["class"], "insufficient")
        capped = classify(CAP, 84, 88)
        self.assertEqual(capped["class"], "no-clear-effect", capped["reason"])
        self.assertIsNotNone(capped["remove_decided_at"])
        one = classify(CAP, 84, 88, cli=lambda r: CLIS[0])
        self.assertEqual((one["class"], one["at_cap"]), ("insufficient", True))

    def test_a_crossed_ceiling_keeps_a_cell_off_the_remove_test(self):
        # Round 3's surviving mutation [14]: the ceiling test crossed at pair
        # 18, then the without arm fell to a sample mean of 0.818. The cell
        # is still high (on the bound), so the remove test does not decide it.
        got = classify(22, lambda r: 90 if r < 18 else 0, lambda r: 100 if r < 18 else 0)
        self.assertEqual(got["ceiling_at"], 18)
        self.assertLess(got["without_mean"], 1 - POLICY["objective_margin"])
        self.assertIsNotNone(got["remove_decided_at"])
        self.assertEqual(got["class"], "insufficient", got["reason"])


class OrderTests(unittest.TestCase):
    """M3: repro_order_stuck.py. 18 flat pairs on one CLI version cross the
    remove test, which never decides; then the subject helps (with 90,
    without 50) on a second version and the keep test crosses at pair 25."""

    def test_a_keep_after_an_undecided_remove_crossing_keeps(self):
        version = lambda r: CLIS[r >= 18]  # noqa: E731
        for n in (28, CAP):
            got = classify(n, lambda r: 50 if r < 18 else 90, 50, cli=version)
            self.assertEqual((got["objective"]["keep_at"], got["objective"]["remove_at"],
                              got["remove_decided_at"]), (25, 18, None))
            self.assertEqual(got["class"], "benefit", got["reason"])

    def test_a_decided_removal_before_the_keep_still_removes(self):
        # The same remove crossing on alternating versions decides at 18, so
        # a later keep crossing does not outrank it.
        got = classify(CAP, lambda r: 50 if r < 18 else 90, 50)
        self.assertEqual(got["remove_decided_at"], 18)
        self.assertEqual(got["class"], "no-benefit", got["reason"])


class AtCapTests(unittest.TestCase):
    """M4 and M3: `at_cap` at exactly `max_runs_per_cell` pairs, and the
    planner's work item for an undecided cell there."""

    ONE = staticmethod(lambda r: CLIS[0])

    def test_at_cap_is_set_at_the_cap_and_not_before(self):
        short = classify(CAP - 1, 50, 50, cli=self.ONE)
        capped = classify(CAP, 50, 50, cli=self.ONE)
        self.assertEqual((short["class"], short["at_cap"]), ("insufficient", False))
        self.assertEqual((capped["class"], capped["at_cap"]), ("insufficient", True))
        self.assertIs(classify(CAP + 3, 50, 50, cli=self.ONE)["at_cap"], True)

    def test_a_capped_cell_reaches_the_planner_as_a_work_item_not_a_fire(self):
        from test_issue_559_empty_fires import MODEL, NOW, SKILL_FIXTURE, one
        from test_issue_closed_loop_planner import ctx
        skill, fixture = SKILL_FIXTURE.split("/")[1:]
        for n, at_cap in ((CAP - 1, False), (CAP, True)):
            runs = pairs(fixture, n, 50, 50, model=MODEL, cli=self.ONE, skill=skill)
            verdict = gates.retirement({"runs": runs}, [MODEL], skill, POLICY,
                                       expect(fixture))
            doc = {"roster_models": [MODEL], "skills": {skill: verdict}}
            got = one(plan_week.eval_cells(ROOT / "evals", doc, [], NOW), SKILL_FIXTURE)
            self.assertEqual((got["class"], got["at_cap"]), ("insufficient", at_cap))
            plan = plan_week.build_plan(ctx(cells=[got], room=1.0), NOW)
            fired = [(f["fixture"], f["model"]) for f in plan["fires"]]
            items = [w for w in plan["work"] if w["kind"] == "cell-at-cap"]
            if at_cap:
                self.assertEqual(fired, [])
                self.assertEqual(items, [{"kind": "cell-at-cap", "change_type": None,
                                          "skill": skill, "fixture": SKILL_FIXTURE,
                                          "model": MODEL, "route": "issue",
                                          "reason": got["reason"]}])
                self.assertIn("has not been at its level", items[0]["reason"])
            else:
                self.assertEqual(fired, [(SKILL_FIXTURE, MODEL)])
                self.assertEqual(items, [])

    def test_a_kept_subject_and_a_guidance_cell_at_the_cap(self):
        from test_issue_closed_loop_planner import NOW, cell as pcell, ctx
        frozen = {**pcell("evals/a", "heavy", "insufficient", runs=CAP), "at_cap": True,
                  "pairs": CAP, "reason": "why"}
        kept = plan_week.build_plan(ctx(cells=[{**frozen, "verdict": "keep"}], room=1.0), NOW)
        self.assertEqual([w for w in kept["work"] if w["kind"] == "cell-at-cap"], [])
        section = {**frozen, "skill": "", "section": "sec"}
        work = plan_week.build_plan(ctx(cells=[section], room=1.0), NOW)["work"]
        self.assertIn({"kind": "cell-at-cap", "change_type": None, "skill": "",
                       "fixture": "evals/a", "model": "heavy", "route": "issue",
                       "reason": "why", "section": "sec"}, work)

    def test_a_decided_cell_at_the_cap_is_not_rechecked(self):
        # Round 3's m5: its frozen window cannot take another pair.
        from test_issue_closed_loop_planner import NOW, cell as pcell, ctx
        old = (NOW - timedelta(days=120)).strftime("%Y%m%dT%H%M%SZ")
        for cls in ("no-clear-effect", "benefit", "no-benefit"):
            due = pcell("evals/a", "heavy", cls, runs=CAP, newest=old)
            plan = plan_week.build_plan(ctx(cells=[due], room=1.0), NOW)
            self.assertEqual([f["band"] for f in plan["fires"]], ["recheck"], cls)
            plan = plan_week.build_plan(ctx(cells=[{**due, "at_cap": True}], room=1.0), NOW)
            self.assertEqual(plan["fires"], [], cls)


class SharedClassesTests(unittest.TestCase):
    """The minors: one list of parked classes, read the same everywhere."""

    def test_parked_classes_agree(self):
        self.assertEqual(set(plan_week.PARKED_CLASSES), set(gates.PARKED_CLASSES))
        self.assertEqual(gates.PARKED_CLASSES, {"ceiling", "ceiling-unconfirmed", "paused"})
        self.assertTrue(set(gates.PARKED_CLASSES) <= set(retire_skill.RETIRE_CELL_CLASSES))

    def test_no_parked_cell_votes_on_the_explorer(self):
        def c(cls, no_help):
            return {"class": cls, "objective": {"no_help_confidence": no_help},
                    "keep_tests": [{"route": "objective", "p": 0.5}]}
        for cls in sorted(gates.PARKED_CLASSES):
            got = explorer_data.subject_confidence(
                {"cells": [c("no-benefit", 0.95), c(cls, 0.1)]})
            self.assertEqual(got["no_help"], 0.95, cls)
        got = explorer_data.subject_confidence({"cells": [c("no-clear-effect", 0.4),
                                                          c("no-benefit", 0.95)]})
        self.assertEqual(got["no_help"], 0.4)


if __name__ == "__main__":
    unittest.main()
