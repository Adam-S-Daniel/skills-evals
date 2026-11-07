"""ADR 0017: fleet guidance merges by automation are batched into one weekly
window. Pins scripts/guidance_merge_window.py, the two openers' behavior
outside the window, and guidance-merge-window.yml (parsed with a YAML
parser). No network, no wall clock: every instant is passed in."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "harness"))

import guidance_improve_gate as gate  # noqa: E402
import guidance_merge_window as gmw  # noqa: E402
import retire_skill as rs  # noqa: E402
from ingest_routine_results import Rejected  # noqa: E402

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "guidance-merge-window.yml"
# The bounds _agent-guidance ships (ADR 0039): Monday 17:00 to 19:00 UTC.
BOUNDS = "weekday: 1\nstart: \"17:00\"\nend: \"19:00\"\n"
OPEN = datetime(2026, 11, 9, 17, 0, tzinfo=timezone.utc)       # a Monday
LAST = datetime(2026, 11, 9, 18, 59, 59, tzinfo=timezone.utc)
CLOSED = datetime(2026, 11, 9, 19, 0, tzinfo=timezone.utc)
TUESDAY = datetime(2026, 11, 10, 17, 30, tzinfo=timezone.utc)


def tree_with(bounds: str | None, test: unittest.TestCase) -> Path:
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    root = Path(tmp.name)
    if bounds is not None:
        (root / gmw.WINDOW_REL).parent.mkdir(parents=True)
        (root / gmw.WINDOW_REL).write_text(bounds, encoding="utf-8")
    return root


class ParseTests(unittest.TestCase):
    def test_the_shipped_shape_parses(self):
        self.assertEqual(gmw.parse_window(BOUNDS), {"weekday": 1, "start": "17:00", "end": "19:00"})

    def test_anything_else_is_refused(self):
        for text in ("", "- a\n", "weekday: 1\nstart: '17:00'\n",
                     BOUNDS + "tz: UTC\n", "weekday: 0\nstart: '17:00'\nend: '19:00'\n",
                     "weekday: 8\nstart: '17:00'\nend: '19:00'\n",
                     "weekday: true\nstart: '17:00'\nend: '19:00'\n",
                     "weekday: 1\nstart: 17:00\nend: '19:00'\n",
                     "weekday: 1\nstart: '19:00'\nend: '17:00'\n",
                     "weekday: 1\nstart: '17:00'\nend: '24:00'\n", "weekday: [1\n"):
            with self.subTest(text=text), self.assertRaises(gmw.WindowError):
                gmw.parse_window(text)


class WindowTests(unittest.TestCase):
    W = gmw.parse_window(BOUNDS)

    def test_half_open_on_the_window_day(self):
        self.assertTrue(gmw.in_window(OPEN, self.W))
        self.assertTrue(gmw.in_window(LAST, self.W))
        self.assertFalse(gmw.in_window(CLOSED, self.W))
        self.assertFalse(gmw.in_window(OPEN.replace(hour=16, minute=59), self.W))
        self.assertFalse(gmw.in_window(TUESDAY, self.W))

    def test_a_non_utc_instant_is_converted(self):
        from datetime import timedelta
        plus2 = timezone(timedelta(hours=2))
        self.assertTrue(gmw.in_window(datetime(2026, 11, 9, 19, 30, tzinfo=plus2), self.W))
        self.assertFalse(gmw.in_window(datetime(2026, 11, 9, 17, 30, tzinfo=plus2), self.W))

    def test_a_naive_instant_is_refused(self):
        with self.assertRaises(gmw.WindowError):
            gmw.in_window(datetime(2026, 11, 9, 17, 30), self.W)

    def test_next_start(self):
        self.assertEqual(gmw.next_start(OPEN, self.W), datetime(2026, 11, 16, 17, 0, tzinfo=timezone.utc))
        self.assertEqual(gmw.next_start(OPEN.replace(hour=9), self.W), OPEN)

    def test_window_open_fails_closed(self):
        self.assertTrue(gmw.window_open(tree_with(BOUNDS, self), OPEN))
        self.assertFalse(gmw.window_open(tree_with(BOUNDS, self), CLOSED))
        self.assertFalse(gmw.window_open(tree_with(None, self), OPEN), "missing file")
        self.assertFalse(gmw.window_open(tree_with("junk: 1\n", self), OPEN), "malformed file")


class FakeGh:
    def __init__(self, prs=(), method="MERGE"):
        self.prs, self.method, self.calls = list(prs), method, []

    def __call__(self, args, stdin=None):
        self.calls.append(list(args))
        if args[0] == "api":
            return "".join(json.dumps(p) + "\n" for p in self.prs)
        if args[:2] == ["pr", "view"]:
            return self.method + "\n"
        return ""


def queued(number, **over):
    pr = {"number": number, "sha": "a" * 40, "draft": False, "armed": False,
          "author": rs.LOOP_AUTHOR, "labels": [rs.AGENT_LABEL]}
    pr.update(over)
    return pr


class ArmQueuedTests(unittest.TestCase):
    def arm(self, gh, now=OPEN, bounds=BOUNDS):
        return gmw.arm_queued(gh, tree_with(bounds, self), now)

    def test_outside_the_window_nothing_is_listed_or_armed(self):
        gh = FakeGh([queued(5)])
        out = self.arm(gh, CLOSED)
        self.assertEqual(gh.calls, [])
        self.assertIn("window closed", out[0])
        self.assertIn("2026-11-16T17:00:00+00:00", out[0])

    def test_an_unreadable_window_arms_nothing(self):
        gh = FakeGh([queued(5)])
        out = self.arm(gh, OPEN, bounds="nope: 1\n")
        self.assertEqual(gh.calls, [])
        self.assertIn("nothing armed", out[0])

    def test_inside_the_window_a_queued_pull_request_is_armed_on_its_head(self):
        gh = FakeGh([queued(5)])
        out = self.arm(gh)
        self.assertEqual(out, ["#5: armed"])
        merge = next(c for c in gh.calls if c[:2] == ["pr", "merge"])
        self.assertEqual(merge, ["pr", "merge", "5", "-R", gmw.GUIDANCE_REPO, "--auto",
                                 "--merge", "--match-head-commit", "a" * 40])
        self.assertFalse(any("--squash" in c or "--admin" in c for c in gh.calls))

    def test_the_last_second_of_the_window_still_arms(self):
        self.assertEqual(self.arm(FakeGh([queued(5)]), LAST), ["#5: armed"])

    def test_pull_requests_that_are_not_the_loops_or_are_held_are_left_alone(self):
        gh = FakeGh([queued(1, author="someone"), queued(2, labels=[]),
                     queued(3, labels=[rs.AGENT_LABEL, rs.ON_HOLD_LABEL]),
                     queued(4, draft=True), queued(6, armed=True)])
        out = self.arm(gh)
        self.assertFalse(any(c[:2] == ["pr", "merge"] for c in gh.calls))
        self.assertEqual([line.split(":")[0] for line in out], [f"#{n}" for n in (1, 2, 3, 4, 6)])

    def test_auto_merge_that_did_not_take_is_an_error(self):
        with self.assertRaises(rs.RetireError):
            self.arm(FakeGh([queued(5)], method=""))

    def test_the_listing_selects_only_the_improvement_heads(self):
        gh = FakeGh()
        self.arm(gh)
        jq = gh.calls[0][gh.calls[0].index("--jq") + 1]
        self.assertIn(gmw.QUEUED_PREFIX, jq)
        self.assertEqual(gmw.QUEUED_PREFIX, gate.TARGET_PREFIX)
        self.assertNotIn("retire-guidance", jq)

    def test_main_without_a_token_arms_nothing(self):
        out = io.StringIO()
        rc = gmw.main(["arm-queued", "--tree", str(tree_with(BOUNDS, self))], env={}, out=out)
        self.assertEqual(rc, 0)
        self.assertIn("nothing armed", out.getvalue())


class OpenerTests(unittest.TestCase):
    """The improvement gate queues; the retirement pass waits."""

    def open_pr(self, arm):
        gh = FakeGh()
        gh.calls.clear()
        outputs = {"api": "", "pr create": f"https://github.com/{gate.GUIDANCE_REPO}/pull/41\n"}

        def run(args, stdin=None):
            gh.calls.append(list(args))
            if args[:2] == ["pr", "create"]:
                return outputs["pr create"]
            if args[:2] == ["pr", "view"]:
                return "MERGE\n"
            return ""
        pushed = []
        out = gate.open_pr("t", run, pushed.append, section="example", run_id="1",
                           base="main", commit="3" * 40, mode="auto", body="b", arm=arm)
        return out, gh.calls

    def test_outside_the_window_the_pull_request_is_ready_labeled_and_unarmed(self):
        out, calls = self.open_pr(arm=False)
        self.assertEqual(out["queued"], "true")
        self.assertTrue(out["opened"])
        create = next(c for c in calls if c[:2] == ["pr", "create"])
        self.assertNotIn("--draft", create)
        self.assertTrue(any("labels[]=agent-authored" in c for c in calls))
        self.assertFalse(any(c[:2] == ["pr", "merge"] for c in calls))

    def test_inside_the_window_it_is_armed_as_before(self):
        out, calls = self.open_pr(arm=True)
        self.assertNotIn("queued", out)
        self.assertTrue(any(c[:2] == ["pr", "merge"] for c in calls))

    def test_the_body_says_it_is_queued_only_when_it_is(self):
        staged = tree_with(None, self)
        (staged / "report.md").write_text("report\n", encoding="utf-8")
        queued_body = gate.pr_body(staged, "1", "b" * 40, "claude/x", "auto", True)
        self.assertIn("queued", queued_body)
        self.assertIn("Monday 17:00 to 19:00 UTC", queued_body)
        self.assertNotIn("queued", gate.pr_body(staged, "1", "b" * 40, "claude/x", "auto", False))
        self.assertNotIn("queued", gate.pr_body(staged, "1", "b" * 40, "claude/x", "draft", True)
                         .replace("not queued", ""))

    def test_a_removal_is_not_opened_outside_the_window(self):
        action = {"action": "guidance-removal", "section": "example"}
        gh = FakeGh()
        with mock.patch.object(rs, "guidance_prepare_branch") as prepare:
            out = rs.guidance_execute(action, Path("."), gh, None, {}, window_open=lambda t: False)
            self.assertEqual(out, rs.WINDOW_CLOSED)
            prepare.assert_not_called()
        self.assertEqual(gh.calls, [])

    def test_a_removal_with_no_checkout_waits_too(self):
        action = {"action": "guidance-removal", "section": "example"}
        self.assertEqual(rs.guidance_execute(action, None, FakeGh(), None, {}), rs.WINDOW_CLOSED)

    def test_the_real_check_is_the_default(self):
        action = {"action": "guidance-removal", "section": "example"}
        # No window file in the checkout: closed, so nothing is written.
        self.assertEqual(rs.guidance_execute(action, tree_with(None, self), FakeGh(), None, {}),
                         rs.WINDOW_CLOSED)


class WorkflowTests(unittest.TestCase):
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    on = doc.get("on", doc.get(True))

    def test_triggers_are_the_monday_window_schedule_and_dispatch(self):
        self.assertEqual(set(self.on), {"schedule", "workflow_dispatch"})
        w = gmw.parse_window(BOUNDS)
        for entry in self.on["schedule"]:
            minute, hour, dom, month, dow = entry["cron"].split()
            self.assertEqual((dom, month, dow), ("*", "*", str(w["weekday"])), entry)
            when = datetime(2026, 11, 9, int(hour), int(minute), tzinfo=timezone.utc)
            self.assertTrue(gmw.in_window(when, w), entry)

    def test_skill_coverage_has_a_pass_inside_the_window(self):
        doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "skill-coverage.yml")
                             .read_text(encoding="utf-8"))
        on = doc.get("on", doc.get(True))
        w = gmw.parse_window(BOUNDS)
        inside = []
        for entry in on["schedule"]:
            minute, hour, dom, month, dow = entry["cron"].split()
            if dow == str(w["weekday"]):
                inside.append(gmw.in_window(
                    datetime(2026, 11, 9, int(hour), int(minute), tzinfo=timezone.utc), w))
        self.assertEqual(inside, [True])

    def test_no_concurrency_no_path_filter_and_no_write_permission_of_its_own(self):
        self.assertNotIn("concurrency", self.doc)
        self.assertEqual(self.doc["permissions"], {})
        for job in self.doc["jobs"].values():
            self.assertNotIn("concurrency", job)
            self.assertEqual(job["permissions"], {"contents": "read"})

    def test_it_never_names_the_improve_loop_strings_the_schedule_ban_scans_for(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("eval-improve", text)
        self.assertNotIn("trig_", text)

    def test_the_token_reaches_exactly_the_arming_step(self):
        steps = self.doc["jobs"]["arm"]["steps"]
        holders = [s["name"] for s in steps if "steps.guidance-token.outputs.token" in json.dumps(s.get("env", {}))]
        self.assertEqual(holders, ["Arm the queued pull requests, inside the window only"])
        mint = next(s for s in steps if s.get("id") == "guidance-token")
        self.assertTrue(mint["continue-on-error"])
        self.assertEqual(mint["with"]["repositories"], "_agent-guidance")

    def test_it_reads_the_bounds_from_agent_guidance_and_keeps_no_copy(self):
        steps = self.doc["jobs"]["arm"]["steps"]
        co = next(s for s in steps if s.get("with", {}).get("repository") == "Adam-S-Daniel/_agent-guidance")
        self.assertEqual(co["with"]["sparse-checkout"], gmw.WINDOW_REL)
        self.assertIs(co["with"]["persist-credentials"], False)
        self.assertFalse((REPO_ROOT / "evals" / "base-md-merge-window.yml").exists())

    def test_the_gate_workflow_reports_a_queued_pull_request(self):
        gate_doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows"
                                   / "routine-guidance-improve-gate.yml").read_text(encoding="utf-8"))
        run = next(s["run"] for s in gate_doc["jobs"]["guidance-pr"]["steps"]
                   if s.get("name") == "Open the pull request in _agent-guidance")
        self.assertIn("queued", run)


if __name__ == "__main__":
    unittest.main()
