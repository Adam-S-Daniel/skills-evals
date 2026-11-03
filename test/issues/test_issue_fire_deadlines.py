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
    """`gh` over a fixed issue list and label set; `label create` adds to
    the set unless `fail_create` (then, with `race`, another run made it)."""

    def __init__(self, issues, labels=None, fail_create=False, race=False):
        self.issues, self.calls = issues, []
        self.labels = set(work_item_issues.LABELS if labels is None else labels)
        self.fail_create, self.race = fail_create, race

    def __call__(self, args, stdin=None, token=None):
        self.calls.append((args, stdin))
        if args[0] == "api" and "/labels" in args[2]:
            return "\n".join(sorted(self.labels))
        if args[0] == "api":
            return "\n".join(json.dumps({**i, "author": i.get("author", retire_skill.ISSUE_AUTHOR)})
                             for i in self.issues)
        if args[:2] == ["label", "create"]:
            if self.fail_create:
                if self.race:
                    self.labels.add(args[2])
                raise retire_skill.RetireError("gh label exited 1")
            self.labels.add(args[2])
        return ""


class WorkItemIssueTests(unittest.TestCase):
    """The second loss files the issue; nobody has to read a step summary."""

    def run_main(self, items, issues, *extra, gh=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            gh, out = gh or FakeGh(issues), io.StringIO()
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
            {"routine_down": False, "work": [{"kind": "agent-check"}]},
            [{"number": 9, "state": "open", "body": body, "author": "someone"}])
        self.assertEqual((code, self.writes(calls)), (0, []))

    def test_a_malformed_item_writes_nothing(self):
        for bad in ({**BROKEN, "fixture": "../etc"}, {**BROKEN, "model": "x y"},
                    {**OUTAGE, "sweep_start": "soon"}):
            with self.subTest(bad=bad):
                code, calls, _ = self.run_main({"routine_down": False, "work": [bad]}, [])
                self.assertEqual((code, self.writes(calls)), (2, []))

    def test_fixture_needs_open_agent_ready_issues(self):
        # skills-evals#659: the plan's issue-routed fixture needs reach a queue.
        harder = {"kind": "needs-harder-fixtures", "change_type": "fixture",
                  "skill": "writing-adrs", "fixtures": 5, "headroom": 0.04, "route": "issue"}
        more = {"kind": "needs-fixtures", "change_type": "fixture", "skill": "",
                "section": "example-section", "fixtures": 2, "headroom": 0.3,
                "value": None, "route": "issue"}
        code, calls, _ = self.run_main({"routine_down": False, "work": [harder, more]}, [])
        self.assertEqual(code, 0)
        creates = [(args, stdin) for args, stdin in calls if args[:2] == ["issue", "create"]]
        self.assertEqual(len(creates), 2)
        for args, _ in creates:
            self.assertEqual(args[args.index("--label") + 1], "agent-ready")
        bodies = {stdin.splitlines()[0]: stdin for _, stdin in creates}
        self.assertIn("<!-- skills-evals:needs-harder-fixtures:writing-adrs -->", bodies)
        self.assertIn("<!-- skills-evals:needs-fixtures:guidance/example-section -->", bodies)
        self.assertIn("0.04", bodies["<!-- skills-evals:needs-harder-fixtures:writing-adrs -->"])
        self.assertIn("`Refs`", bodies["<!-- skills-evals:needs-fixtures:guidance/example-section -->"])
        # Lost-fire issues stay unlabeled.
        code, calls, _ = self.run_main({"routine_down": False, "work": [BROKEN]}, [])
        self.assertNotIn("--label", next(a for a, _ in calls if a[:2] == ["issue", "create"]))

    def test_a_fixture_need_closes_only_when_the_plan_judged_its_subject(self):
        body = "<!-- skills-evals:needs-harder-fixtures:writing-adrs -->\n"
        issue = [{"number": 11, "state": "open", "body": body}]
        # Not judged (an input the plan lacked): the queue keeps the issue.
        for items in ({"routine_down": False, "work": []},
                      {"routine_down": False, "work": [], "subjects": {"skills": ["other"]}}):
            with self.subTest(items=items):
                self.assertEqual(self.writes(self.run_main(items, issue)[1]), [])
        judged = {"routine_down": False, "work": [], "subjects": {"skills": ["writing-adrs"]}}
        self.assertEqual(self.writes(self.run_main(judged, issue)[1]),
                         [["issue", "comment"], ["issue", "close"]])
        gbody = "<!-- skills-evals:needs-fixtures:guidance/example-section -->\n"
        gjudged = {"routine_down": False, "work": [],
                   "subjects": {"skills": [], "guidance": ["example-section"]}}
        self.assertEqual(
            self.writes(self.run_main(gjudged, [{"number": 12, "state": "open", "body": gbody}])[1]),
            [["issue", "comment"], ["issue", "close"]])

    def test_a_malformed_fixture_need_writes_nothing(self):
        good = {"kind": "needs-fixtures", "skill": "writing-adrs", "fixtures": 2}
        for bad in ({**good, "skill": "../x"}, {**good, "fixtures": "2"},
                    {**good, "section": "example-section"}, {**good, "skill": ""},
                    {"kind": "needs-fixtures", "skill": "", "section": "Bad_Id", "fixtures": 1}):
            with self.subTest(bad=bad):
                code, calls, _ = self.run_main({"routine_down": False, "work": [bad]}, [])
                self.assertEqual((code, self.writes(calls)), (2, []))
        code, _, _ = self.run_main({"routine_down": False, "work": [], "subjects": {"skills": "x"}}, [])
        self.assertEqual(code, 2)

    def test_the_sweep_extracts_every_issue_kind_and_the_measured_subjects(self):
        # The workflow's own jq filter, run on a plan-shaped document.
        import shutil
        import subprocess
        import yaml
        jq = shutil.which("jq")
        if jq is None:
            self.skipTest("jq is not installed")
        doc = yaml.safe_load((ROOT / ".github/workflows/routine-eval-weekly.yml")
                             .read_text(encoding="utf-8"))
        step = next(s for s in doc["jobs"]["plan"]["steps"]
                    if s.get("name") == "Extract the issue-routed work items")
        program = step["run"].split("jq '", 1)[1].split("' \\", 1)[0]
        plan = {"routine_down": False,
                "skills": {"writing-adrs": {"headroom": 0.04}, "unmeasured": {"headroom": None}},
                "guidance": {"example-section": {"headroom": 0.3}},
                "triggers": {"quiet": {"eligible": True}, "busy": {"eligible": False}},
                "work": [{"kind": k} for k in ("fixture-broken", "routine-outage",
                                                "needs-fixtures", "needs-harder-fixtures",
                                                "needs-trigger-set", "agent-check")]}
        out = json.loads(subprocess.run([jq, program], input=json.dumps(plan), text=True,
                                        capture_output=True, check=True).stdout)
        self.assertEqual([w["kind"] for w in out["work"]],
                         ["fixture-broken", "routine-outage", "needs-fixtures",
                          "needs-harder-fixtures", "needs-trigger-set"])
        self.assertEqual(out["subjects"], {"skills": ["writing-adrs"],
                                           "guidance": ["example-section"],
                                           "triggers": ["busy", "quiet"]})
        # A plan from before the trigger lane's status map judged no trigger.
        del plan["triggers"]
        out = json.loads(subprocess.run([jq, program], input=json.dumps(plan), text=True,
                                        capture_output=True, check=True).stdout)
        self.assertEqual(out["subjects"]["triggers"], [])

    def test_a_trigger_set_need_opens_an_agent_ready_issue(self):
        # skills-evals#662: the fleet worker writes the set; the gate merges it.
        need = {"kind": "needs-trigger-set", "change_type": "fixture", "route": "issue",
                "skill": "writing-adrs", "weight": 0,
                "trigger_set": "evals/writing-adrs/trigger-eval-set.json",
                "hook_candidate": False}
        code, calls, _ = self.run_main({"routine_down": False, "work": [need]}, [])
        self.assertEqual(code, 0)
        [(args, body)] = [(a, b) for a, b in calls if a[:2] == ["issue", "create"]]
        self.assertEqual(args[args.index("--label") + 1], "agent-ready")
        self.assertEqual(args[args.index("--title") + 1],
                         "Needs a trigger eval set: skill writing-adrs")
        self.assertEqual(body.splitlines()[0],
                         "<!-- skills-evals:needs-trigger-set:writing-adrs -->")
        for text in ("`evals/writing-adrs/trigger-eval-set.json`", "`query`",
                     "`should_trigger`", "at least 8 should-trigger and 8 should-not-trigger",
                     "near misses", "SKILL.md", "`Refs`", "trigger-only improve run"):
            self.assertIn(text, body)
        for bad in ({**need, "skill": "../x"}, {**need, "skill": ""}, {**need, "skill": 3}):
            with self.subTest(bad=bad):
                code, calls, _ = self.run_main({"routine_down": False, "work": [bad]}, [])
                self.assertEqual((code, self.writes(calls)), (2, []))

    def test_a_trigger_set_need_closes_only_when_its_skill_was_judged(self):
        body = "<!-- skills-evals:needs-trigger-set:writing-adrs -->\n"
        issue = [{"number": 13, "state": "open", "body": body}]
        # Measured headroom is not a trigger-lane judgment.
        for subjects in (None, {"skills": ["writing-adrs"]}, {"triggers": ["other"]}):
            items = {"routine_down": False, "work": []}
            if subjects is not None:
                items["subjects"] = subjects
            with self.subTest(subjects=subjects):
                self.assertEqual(self.writes(self.run_main(items, issue)[1]), [])
        judged = {"routine_down": False, "work": [], "subjects": {"triggers": ["writing-adrs"]}}
        self.assertEqual(self.writes(self.run_main(judged, issue)[1]),
                         [["issue", "comment"], ["issue", "close"]])
        code, _, _ = self.run_main({"routine_down": False, "work": [],
                                    "subjects": {"triggers": "x"}}, [])
        self.assertEqual(code, 2)

    HARDER = {"kind": "needs-harder-fixtures", "change_type": "fixture",
              "skill": "writing-adrs", "fixtures": 5, "headroom": 0.03, "route": "issue"}
    TRIGGER = {"kind": "needs-trigger-set", "change_type": "fixture", "route": "issue",
               "skill": "quiet-skill", "weight": 0}

    def test_a_request_carries_its_kind_label_and_header_lines(self):
        # Adam, 2026-11-03: the dashboard reads kind, subject and reason
        # without parsing prose.
        more = {"kind": "needs-fixtures", "skill": "", "section": "example-section",
                "fixtures": 2, "headroom": 0.3}
        code, calls, _ = self.run_main(
            {"routine_down": False, "work": [self.HARDER, more, self.TRIGGER]}, [])
        self.assertEqual(code, 0)
        creates = {stdin.splitlines()[0]: (args, stdin) for args, stdin in calls
                   if args[:2] == ["issue", "create"]}
        expected = {
            "<!-- skills-evals:needs-harder-fixtures:writing-adrs -->": (
                "needs-harder-fixtures", "writing-adrs", "train headroom 0.03, 5 fixture(s)"),
            "<!-- skills-evals:needs-fixtures:guidance/example-section -->": (
                "needs-fixtures", "guidance/example-section", "train headroom 0.30, 2 fixture(s)"),
            "<!-- skills-evals:needs-trigger-set:quiet-skill -->": (
                "needs-trigger-set", "quiet-skill", "usage weight 0, no trigger set"),
        }
        self.assertEqual(set(creates), set(expected))
        for line, (kind, subject, reason) in expected.items():
            args, body = creates[line]
            with self.subTest(kind=kind):
                labels = [args[i + 1] for i, a in enumerate(args) if a == "--label"]
                self.assertEqual(labels, ["agent-ready", kind])
                self.assertEqual(body.splitlines()[1:4],
                                 [f"Kind: {kind}", f"Subject: {subject}", f"Reason: {reason}"])
        self.assertIn("Reason: usage weight unknown, no trigger set", self.run_main(
            {"routine_down": False, "work": [{**self.TRIGGER, "weight": None}]}, [])[1][-1][1])

    def test_a_fixture_request_asks_for_real_fleet_work_and_an_origin(self):
        code, calls, _ = self.run_main({"routine_down": False, "work": [self.HARDER]}, [])
        body = next(stdin for args, stdin in calls if args[:2] == ["issue", "create"])
        for text in ("real fleet work", "merged pull requests", "both owners",
                     "Adam-S-Daniel and jodidaniel", "invented names, data and hosts",
                     "`example.com`", "Never copy private content verbatim",
                     "When no real case fits, write an invented task",
                     "top-level `origin:` mapping (required",
                     "kind: real-work", "source: https://github.com/<owner>/<repo>/pull/<N>",
                     "request: https://github.com/Adam-S-Daniel/skills-evals/issues/"):
            self.assertIn(text, body)
        # A trigger set is queries, not a rebuilt task: no origin asked.
        code, calls, _ = self.run_main({"routine_down": False, "work": [self.TRIGGER]}, [])
        body = next(stdin for args, stdin in calls if args[:2] == ["issue", "create"])
        self.assertNotIn("origin", body)

    def test_missing_labels_are_created_and_existing_ones_never_edited(self):
        gh = FakeGh([], labels={"agent-ready", "needs-fixtures"})
        code, calls, _ = self.run_main({"routine_down": False, "work": [self.HARDER]}, [],
                                       gh=gh)
        self.assertEqual(code, 0)
        created = [args[2] for args, _ in calls if args[:2] == ["label", "create"]]
        self.assertEqual(created, ["needs-harder-fixtures"])
        self.assertFalse([args for args, _ in calls if args[:2] == ["label", "edit"]
                          or "--force" in args])
        order = [args[:2] for args, _ in calls if args[0] in ("label", "issue")]
        self.assertEqual(order, [["label", "create"], ["issue", "create"]])
        # Present already: nothing is created.
        code, calls, _ = self.run_main({"routine_down": False, "work": [self.HARDER]}, [])
        self.assertFalse([a for a, _ in calls if a[:2] == ["label", "create"]])
        # Lost-fire items use no label, so no label is listed or created.
        code, calls, _ = self.run_main({"routine_down": False, "work": [BROKEN]}, [],
                                       gh=FakeGh([], labels=set()))
        self.assertFalse([a for a, _ in calls if a[0] == "label" or "/labels" in a[-3]])

    def test_a_label_another_run_created_is_fine_and_a_missing_one_stops_the_run(self):
        gh = FakeGh([], labels={"agent-ready"}, fail_create=True, race=True)
        code, calls, _ = self.run_main({"routine_down": False, "work": [self.HARDER]}, [],
                                       gh=gh)
        self.assertEqual((code, self.writes(calls)), (0, [["issue", "create"]]))
        gh = FakeGh([], labels={"agent-ready"}, fail_create=True)
        code, calls, _ = self.run_main({"routine_down": False, "work": [self.HARDER]}, [],
                                       gh=gh)
        self.assertEqual((code, self.writes(calls)), (1, []))

    def test_an_open_request_without_its_kind_label_gets_it_once(self):
        body = "<!-- skills-evals:needs-harder-fixtures:writing-adrs -->\n"
        items = {"routine_down": False, "work": [self.HARDER]}
        unlabeled = [{"number": 21, "state": "open", "body": body, "labels": ["agent-ready"]}]
        code, calls, _ = self.run_main(items, unlabeled)
        self.assertEqual(code, 0)
        self.assertEqual([a for a, _ in calls if a[0] == "issue"],
                         [["issue", "edit", "21", "-R", work_item_issues.EVALS_REPO,
                           "--add-label", "needs-harder-fixtures"]])
        labeled = [{**unlabeled[0], "labels": ["agent-ready", "needs-harder-fixtures"]}]
        self.assertEqual(self.writes(self.run_main(items, labeled)[1]), [])
        # Unknown labels (no list in the record) and lost-fire issues: no edit.
        self.assertEqual(self.writes(self.run_main(items, [{**unlabeled[0], "labels": None}])[1]),
                         [])
        bbody = "<!-- skills-evals:fixture-broken:evals/ci-watcher-loops:claude-opus-5-5 -->\n"
        self.assertEqual(self.writes(self.run_main(
            {"routine_down": False, "work": [BROKEN]},
            [{"number": 22, "state": "open", "body": bbody, "labels": []}])[1]), [])
        # An issue being closed is not relabeled first.
        judged = {"routine_down": False, "work": [], "subjects": {"skills": ["writing-adrs"]}}
        self.assertEqual(self.writes(self.run_main(judged, unlabeled)[1]),
                         [["issue", "comment"], ["issue", "close"]])

    def test_the_issue_listing_asks_for_labels(self):
        gh = FakeGh([{"number": 3, "state": "open", "body": "x", "labels": ["a"]}])
        found = work_item_issues.fetch_issues(gh)
        self.assertEqual(found, [{"number": 3, "body": "x", "state": "open", "labels": ["a"]}])
        self.assertIn("labels: [.labels[]?.name]", gh.calls[0][0][-1])

    def test_a_dry_run_writes_nothing(self):
        code, calls, out = self.run_main({"routine_down": False, "work": [BROKEN]}, [],
                                         "--dry-run")
        self.assertEqual((code, self.writes(calls)), (0, []))
        self.assertEqual(json.loads(out)["actions"][0]["action"], "create-issue")


if __name__ == "__main__":
    unittest.main()
