"""A lost routine fire is planned again within the hour (Adam, 2026-11-03).

The 2026-11-03 03:05 UTC Opus fire of ci-watcher-loops (run id
20261103T030538Z-a4fd19) pushed nothing, and its cell stayed pending for the
planner's fixed two hours until someone noticed. scripts/routine_deadlines.py
now says when a fire of each mode can no longer deliver: the routine prompt's
own stop plus a margin. These tests tie those limits to the prompt text and
pin the planner's use of the eval one.
"""
import re
import sys
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import plan_week  # noqa: E402
import routine_deadlines  # noqa: E402
from test_issue_559_empty_fires import MODEL, NOW, SKILL_FIXTURE, fire, one, stamp  # noqa: E402

PROMPT = ROOT / "docs" / "routine" / "eval-runner-instructions.md"


class DeadlineTests(unittest.TestCase):

    def prompt_limits(self) -> dict:
        """Each mode's stop from the prompt's "Limits:" sentence."""
        text = PROMPT.read_text(encoding="utf-8")
        sentence = re.search(r"Limits: (.*?)\n", text).group(1)
        limits = {}
        for modes, minutes in re.findall(
                r"((?:[a-z-]+(?: and | ))?[a-z-]+) modes? max \d+ nested agent runs"
                r"(?: \([^)]*\))? and stop after (\d+) minutes", sentence):
            for mode in re.split(r" and ", modes):
                limits[mode] = timedelta(minutes=int(minutes))
        return limits

    def test_the_limits_are_the_routine_prompts(self):
        self.assertEqual(self.prompt_limits(), routine_deadlines.MODE_LIMITS)

    def test_each_deadline_is_its_limit_plus_the_margin(self):
        expected = {"eval": 40, "scaffold": 40, "improve": 100,
                    "guidance-improve": 100, "draft": 70}
        self.assertEqual({mode: routine_deadlines.deadline(mode)
                          for mode in routine_deadlines.MODE_LIMITS},
                         {mode: timedelta(minutes=m) for mode, m in expected.items()})

    def test_the_planner_holds_a_cell_for_the_eval_deadline(self):
        self.assertEqual(plan_week.PENDING_WINDOW, routine_deadlines.deadline("eval"))
        # The outage rule still judges a fire at two hours (#583).
        self.assertEqual(plan_week.FIRE_RESULT_WINDOW, timedelta(hours=2))


class LostFireTests(unittest.TestCase):
    """The a4fd19 shape: one fire lost while the routine delivered others."""

    STARTED = NOW - timedelta(minutes=45)

    def doc(self, other_runs):
        def row(fixture, runs):
            return {"fixture": fixture, "model": MODEL, "class": "missing",
                    "runs": {"with": [], "without": []},
                    "newest_on_model": runs[-1] if runs else None,
                    "run_stamps_on_model": runs}
        return {"roster_models": [MODEL], "skills": {
            "writing-adrs": {"cells": [row("bootstrap", [])]},
            "disarm-inherited-reach": {"cells": [row(None, other_runs)]}}}

    def cell(self, doc, fires, now=NOW):
        return one(plan_week.eval_cells(ROOT / "evals", doc, fires, now), SKILL_FIXTURE)

    def test_a_fire_past_its_deadline_is_re_planned_once_another_delivers(self):
        lost = [fire(1, SKILL_FIXTURE, self.STARTED)]
        delivered = self.doc([stamp(self.STARTED + timedelta(minutes=5))])
        self.assertFalse(self.cell(delivered, lost)["pending"])

    def test_before_its_deadline_it_still_holds(self):
        lost = [fire(1, SKILL_FIXTURE, NOW - timedelta(minutes=35))]
        delivered = self.doc([stamp(NOW - timedelta(minutes=30))])
        self.assertTrue(self.cell(delivered, lost)["pending"])

    def test_with_no_delivery_since_it_holds_as_in_an_outage(self):
        lost = [fire(1, SKILL_FIXTURE, self.STARTED)]
        for runs in ([], [stamp(self.STARTED - timedelta(minutes=5))]):
            with self.subTest(runs=runs):
                self.assertTrue(self.cell(self.doc(runs), lost)["pending"])

    def test_a_released_fire_still_counts_only_at_two_hours(self):
        lost = [fire(1, SKILL_FIXTURE, self.STARTED)]
        delivered = self.doc([stamp(self.STARTED + timedelta(minutes=5))])
        self.assertEqual(self.cell(delivered, lost)["empty_fires"], 0)



import json  # noqa: E402
import tempfile  # noqa: E402
import io  # noqa: E402

import retire_skill  # noqa: E402
import work_item_issues  # noqa: E402

BROKEN = {"kind": "fixture-broken", "change_type": "fixture", "skill": "ci-watcher-loops",
          "fixture": "evals/ci-watcher-loops", "model": "claude-opus-5-5", "route": "issue"}
OUTAGE = {"kind": "routine-outage", "change_type": None, "route": "issue",
          "sweep_start": "2026-11-01T05:43:40Z", "fires": 6}


class FakeGh:
    def __init__(self, issues):
        self.issues, self.calls = issues, []

    def __call__(self, args, stdin=None, token=None):
        self.calls.append((args, stdin))
        if args[0] == "api":
            return "\n".join(json.dumps({**i, "author": i.get("author", retire_skill.ISSUE_AUTHOR)})
                             for i in self.issues)
        return ""


class WorkItemIssueTests(unittest.TestCase):
    """The second loss files the issue; nobody has to read a step summary."""

    def run_main(self, items, issues, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            gh, out = FakeGh(issues), io.StringIO()
            code = work_item_issues.main(["--items", str(path), *extra], gh=gh, out=out)
        return code, gh.calls, out.getvalue()

    def writes(self, calls):
        return [args[:2] for args, _ in calls if args[0] == "issue"]

    def test_a_broken_cell_and_an_outage_each_open_one_issue(self):
        code, calls, _ = self.run_main({"routine_down": True, "work": [BROKEN, OUTAGE]}, [],
                                       "--run-url", "https://example.com/run/1")
        self.assertEqual(code, 0)
        self.assertEqual(self.writes(calls), [["issue", "create"], ["issue", "create"]])
        bodies = [stdin for args, stdin in calls if args[:2] == ["issue", "create"]]
        self.assertIn("<!-- skills-evals:fixture-broken:evals/ci-watcher-loops:"
                      "claude-opus-5-5 -->", bodies[0])
        self.assertIn("<!-- skills-evals:routine-outage:2026-11-01T05:43:40Z -->", bodies[1])

    def test_an_open_issue_is_not_filed_twice(self):
        body = "<!-- skills-evals:fixture-broken:evals/ci-watcher-loops:claude-opus-5-5 -->\n"
        code, calls, _ = self.run_main({"routine_down": False, "work": [BROKEN]},
                                       [{"number": 7, "state": "open", "body": body}])
        self.assertEqual((code, self.writes(calls)), (0, []))

    def test_a_recovered_cell_closes_its_issue(self):
        body = "<!-- skills-evals:fixture-broken:evals/ci-watcher-loops:claude-opus-5-5 -->\n"
        code, calls, _ = self.run_main({"routine_down": False, "work": []},
                                       [{"number": 7, "state": "open", "body": body}])
        self.assertEqual((code, self.writes(calls)),
                         (0, [["issue", "comment"], ["issue", "close"]]))

    def test_an_outage_issue_stays_open_while_the_routine_is_down(self):
        body = "<!-- skills-evals:routine-outage:2026-11-01T05:43:40Z -->\n"
        issue = [{"number": 8, "state": "open", "body": body}]
        self.assertEqual(self.writes(self.run_main({"routine_down": True, "work": []}, issue)[1]), [])
        self.assertEqual(self.writes(self.run_main({"routine_down": False, "work": []}, issue)[1]),
                         [["issue", "comment"], ["issue", "close"]])

    def test_other_authors_and_other_work_items_are_ignored(self):
        body = "<!-- skills-evals:fixture-broken:evals/ci-watcher-loops:claude-opus-5-5 -->\n"
        code, calls, _ = self.run_main(
            {"routine_down": False, "work": [{"kind": "needs-trigger-set"}]},
            [{"number": 9, "state": "open", "body": body, "author": "someone"}])
        self.assertEqual((code, self.writes(calls)), (0, []))

    def test_a_malformed_item_writes_nothing(self):
        for bad in ({**BROKEN, "fixture": "../etc"}, {**BROKEN, "model": "x y"},
                    {**OUTAGE, "sweep_start": "soon"}):
            with self.subTest(bad=bad):
                code, calls, _ = self.run_main({"routine_down": False, "work": [bad]}, [])
                self.assertEqual((code, self.writes(calls)), (2, []))

    def test_a_dry_run_writes_nothing(self):
        code, calls, out = self.run_main({"routine_down": False, "work": [BROKEN]}, [],
                                         "--dry-run")
        self.assertEqual((code, self.writes(calls)), (0, []))
        self.assertEqual(json.loads(out)["actions"][0]["action"], "create-issue")


if __name__ == "__main__":
    unittest.main()
