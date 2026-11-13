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
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "harness"))

import guidance_improve_gate as gate  # noqa: E402
import guidance_merge_window as gmw  # noqa: E402
import plan_week  # noqa: E402
import retire_skill as rs  # noqa: E402
from ingest_routine_results import Rejected  # noqa: E402

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "guidance-merge-window.yml"
# The bounds _agent-guidance ships (ADR 0039, 2026-11-13 addendum): Monday
# noon to 2 PM US Eastern. 2026-11-09 is a Monday in EST (UTC-5).
BOUNDS = "timezone: America/New_York\nweekday: 1\nstart: \"12:00\"\nend: \"14:00\"\n"
OPEN = datetime(2026, 11, 9, 17, 0, tzinfo=timezone.utc)       # a Monday, noon EST
LAST = datetime(2026, 11, 9, 18, 59, 59, tzinfo=timezone.utc)
CLOSED = datetime(2026, 11, 9, 19, 0, tzinfo=timezone.utc)
TUESDAY = datetime(2026, 11, 10, 17, 30, tzinfo=timezone.utc)
#: A Monday in EST and one in EDT (UTC midnight): a UTC cron must sit inside both.
MONDAYS = (datetime(2026, 11, 9, tzinfo=timezone.utc), datetime(2026, 6, 15, tzinfo=timezone.utc))


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
        self.assertEqual(gmw.parse_window(BOUNDS),
                         {"timezone": ZoneInfo("America/New_York"), "weekday": 1,
                          "start": "12:00", "end": "14:00"})

    def test_anything_else_is_refused(self):
        z = "timezone: UTC\n"
        for text in ("", "- a\n", z + "weekday: 1\nstart: '17:00'\n",
                     "weekday: 1\nstart: '17:00'\nend: '19:00'\n",
                     BOUNDS + "tz: UTC\n",
                     "timezone: Eastern\nweekday: 1\nstart: '17:00'\nend: '19:00'\n",
                     "timezone: ../../etc/passwd\nweekday: 1\nstart: '17:00'\nend: '19:00'\n",
                     "timezone: 5\nweekday: 1\nstart: '17:00'\nend: '19:00'\n",
                     z + "weekday: 0\nstart: '17:00'\nend: '19:00'\n",
                     z + "weekday: 8\nstart: '17:00'\nend: '19:00'\n",
                     z + "weekday: true\nstart: '17:00'\nend: '19:00'\n",
                     z + "weekday: 1\nstart: 17:00\nend: '19:00'\n",
                     z + "weekday: 1\nstart: '19:00'\nend: '17:00'\n",
                     z + "weekday: 1\nstart: '17:00'\nend: '24:00'\n", "weekday: [1\n"):
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
        plus2 = timezone(timedelta(hours=2))
        self.assertTrue(gmw.in_window(datetime(2026, 11, 9, 19, 30, tzinfo=plus2), self.W))
        self.assertFalse(gmw.in_window(datetime(2026, 11, 9, 17, 30, tzinfo=plus2), self.W))

    def test_a_naive_instant_is_refused(self):
        with self.assertRaises(gmw.WindowError):
            gmw.in_window(datetime(2026, 11, 9, 17, 30), self.W)

    def test_next_start(self):
        self.assertEqual(gmw.next_start(OPEN, self.W), datetime(2026, 11, 16, 17, 0, tzinfo=timezone.utc))
        self.assertEqual(gmw.next_start(OPEN.replace(hour=9), self.W), OPEN)

    def test_daylight_saving_time_moves_the_utc_instants(self):
        # 2026-06-15 is a Monday in EDT (UTC-4): noon ET is 16:00 UTC.
        summer = datetime(2026, 6, 15, 16, 0, tzinfo=timezone.utc)
        self.assertFalse(gmw.in_window(summer - timedelta(seconds=1), self.W))
        self.assertTrue(gmw.in_window(summer, self.W))
        self.assertTrue(gmw.in_window(summer.replace(hour=17, minute=59), self.W))
        self.assertFalse(gmw.in_window(summer.replace(hour=18), self.W))
        self.assertEqual(gmw.window_end(summer, self.W), summer.replace(hour=18))
        self.assertEqual(gmw.window_end(OPEN, self.W), OPEN.replace(hour=19))
        # Across the clock changes (2026-11-01 back, 2027-03-14 forward).
        self.assertEqual(gmw.next_start(datetime(2026, 10, 27, tzinfo=timezone.utc), self.W),
                         datetime(2026, 11, 2, 17, 0, tzinfo=timezone.utc))
        self.assertEqual(gmw.next_start(datetime(2027, 3, 9, tzinfo=timezone.utc), self.W),
                         datetime(2027, 3, 15, 16, 0, tzinfo=timezone.utc))

    def test_the_weekday_is_the_zones_not_utcs(self):
        late = gmw.parse_window("timezone: America/New_York\nweekday: 1\nstart: '18:00'\nend: '21:00'\n")
        self.assertTrue(gmw.in_window(datetime(2026, 11, 10, 1, 0, tzinfo=timezone.utc), late))
        self.assertFalse(gmw.in_window(datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc), late))

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

    def test_the_arming_margin(self):
        # Arming stops ARM_MARGIN before the end, so the merge lands while
        # the eval pause still holds.
        margin_start = CLOSED - gmw.ARM_MARGIN
        self.assertEqual(self.arm(FakeGh([queued(5)]), margin_start), ["#5: armed"])
        gh = FakeGh([queued(5)])
        self.assertIn("nothing armed", self.arm(gh, margin_start + timedelta(seconds=1))[0])
        self.assertEqual(gh.calls, [])
        self.assertIn("nothing armed", self.arm(FakeGh([queued(5)]), LAST)[0])
        self.assertFalse(gmw.window_open(tree_with(BOUNDS, self), LAST))
        self.assertTrue(gmw.window_open(tree_with(BOUNDS, self), margin_start))

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
        self.assertIn("Monday noon to 2 PM US Eastern", queued_body)
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

    def test_triggers_are_the_monday_window_schedule_the_ingest_backstop_and_dispatch(self):
        self.assertEqual(set(self.on), {"schedule", "workflow_run", "workflow_dispatch"})
        ingest = yaml.safe_load((REPO_ROOT / ".github" / "workflows"
                                 / "routine-eval-ingest.yml").read_text(encoding="utf-8"))
        self.assertEqual(self.on["workflow_run"],
                         {"workflows": [ingest["name"]], "types": ["completed"]})
        w = gmw.parse_window(BOUNDS)
        for entry in self.on["schedule"]:
            minute, hour, dom, month, dow = entry["cron"].split()
            self.assertEqual((dom, month, dow), ("*", "*", str(w["weekday"])), entry)
            # Cron is UTC: inside the window in winter (EST) and summer (EDT).
            for monday in MONDAYS:
                when = monday.replace(hour=int(hour), minute=int(minute))
                self.assertTrue(gmw.arming_open(when, w), (entry, monday))

    def test_skill_coverage_has_a_pass_inside_the_window(self):
        doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "skill-coverage.yml")
                             .read_text(encoding="utf-8"))
        on = doc.get("on", doc.get(True))
        w = gmw.parse_window(BOUNDS)
        inside = []
        for entry in on["schedule"]:
            minute, hour, dom, month, dow = entry["cron"].split()
            if dow == str(w["weekday"]):
                inside.append(all(gmw.arming_open(
                    m.replace(hour=int(hour), minute=int(minute)), w) for m in MONDAYS))
        self.assertEqual(inside, [True])

    def test_runs_are_serialized_never_cancelled(self):
        # Ingest runs arrive minutes apart inside the window; a later run must
        # wait for an earlier one rather than list a pull request it already
        # armed and merged. Not a required check, so a queue is safe.
        self.assertEqual(self.doc["concurrency"],
                         {"group": "guidance-merge-window", "cancel-in-progress": False})

    def test_no_job_concurrency_no_path_filter_and_no_write_permission_of_its_own(self):
        self.assertEqual(self.doc["permissions"], {})
        for job in self.doc["jobs"].values():
            self.assertNotIn("concurrency", job)
            self.assertEqual(job["permissions"], {"contents": "read"})

    def test_it_never_names_the_improve_loop_strings_the_schedule_ban_scans_for(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("eval-improve", text)
        self.assertNotIn("trig_", text)

    def test_a_backstop_run_outside_the_window_stops_before_the_token(self):
        steps = self.doc["jobs"]["arm"]["steps"]
        window = next(s for s in steps if s.get("id") == "window")
        self.assertIn("window_open", window["run"])
        self.assertLess(steps.index(window),
                        min(i for i, s in enumerate(steps) if s.get("id") == "guidance-token"))
        gate = "steps.window.outputs.open == 'true'"
        for step in (next(s for s in steps if s.get("id") == "guidance-token"),
                     next(s for s in steps if "arm-queued" in s.get("run", ""))):
            self.assertIn("github.event_name != 'workflow_run' || " + gate, step["if"])

    def test_no_run_block_reads_an_event_payload(self):
        for step in self.doc["jobs"]["arm"]["steps"]:
            self.assertNotIn("github.event.", step.get("run", ""), step.get("name"))

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


class EvalPauseTests(unittest.TestCase):
    """The eval pause (Adam, 2026-11-13): no eval run starts inside the
    window. One source: the same bounds file the merge window reads."""

    def cli(self, bounds, now):
        out = io.StringIO()
        rc = gmw.main(["eval-pause", "--tree", str(tree_with(bounds, self)), "--now", now.isoformat()],
                      env={}, out=out)
        return rc, out.getvalue()

    def test_inside_the_window_it_is_paused_until_the_end(self):
        paused, message = gmw.eval_pause(tree_with(BOUNDS, self), OPEN)
        self.assertTrue(paused)
        self.assertIn("2026-11-09T19:00:00+00:00", message)
        self.assertTrue(gmw.eval_pause(tree_with(BOUNDS, self), LAST)[0])

    def test_outside_the_window_evals_may_start(self):
        for when in (CLOSED, OPEN - timedelta(seconds=1), TUESDAY):
            with self.subTest(when=when):
                self.assertFalse(gmw.eval_pause(tree_with(BOUNDS, self), when)[0])

    def test_summer_pause_is_16_to_18_utc(self):
        tree = tree_with(BOUNDS, self)
        self.assertFalse(gmw.eval_pause(tree, datetime(2026, 6, 15, 15, 59, tzinfo=timezone.utc))[0])
        paused, message = gmw.eval_pause(tree, datetime(2026, 6, 15, 16, 0, tzinfo=timezone.utc))
        self.assertTrue(paused)
        self.assertIn("2026-06-15T18:00:00+00:00", message)

    def test_cli_exit_codes(self):
        self.assertEqual(self.cli(BOUNDS, OPEN)[0], gmw.PAUSED_EXIT)
        self.assertEqual(gmw.PAUSED_EXIT, 3)
        self.assertEqual(self.cli(BOUNDS, CLOSED)[0], 0)

    def test_cli_unreadable_bounds_fail_closed_with_exit_1(self):
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(self.cli(None, CLOSED)[0], 1)
            self.assertEqual(self.cli("weekday: 1\nstart: '17:00'\nend: '19:00'\n", CLOSED)[0], 1)
        self.assertIn("fail closed", err.getvalue())

    def test_cli_needs_no_token(self):
        # eval-pause reads nothing but the bounds; arm-queued's token rule
        # (no token, nothing armed, exit 0) must not swallow it.
        self.assertEqual(self.cli(BOUNDS, OPEN)[0], 3)


class PlanPauseTests(unittest.TestCase):
    """plan_week.py: a sweep inside the window plans no fire."""

    def plan(self):
        return {"fires": [{"slot": 1}], "matrix": {"include": [{"slot": 1}]}, "work": [{"kind": "x"}],
                "room": 0.5}

    def test_inside_the_window_no_fire_is_planned_and_the_rest_stands(self):
        out = plan_week.hold_for_eval_pause(self.plan(), tree_with(BOUNDS, self), OPEN)
        self.assertEqual(out["fires"], [])
        self.assertEqual(out["matrix"], {"include": []})
        self.assertEqual(out["work"], [{"kind": "x"}])
        self.assertIn("evals paused", out["paused"])
        lines = plan_week.summary_lines({**out, "skills": {}})
        self.assertTrue(lines[0].startswith("### Weekly plan: 0 fire(s)"))
        self.assertTrue(lines[2].startswith("Eval pause: evals paused"), lines[:4])

    def test_outside_the_window_the_plan_is_untouched(self):
        self.assertEqual(plan_week.hold_for_eval_pause(self.plan(), tree_with(BOUNDS, self), CLOSED),
                         self.plan())

    def test_unreadable_bounds_plan_no_fire(self):
        out = plan_week.hold_for_eval_pause(self.plan(), tree_with(None, self), CLOSED)
        self.assertEqual(out["fires"], [])
        self.assertIn("cannot be read", out["paused"])

    def test_no_checkout_skips_the_check(self):
        self.assertEqual(plan_week.hold_for_eval_pause(self.plan(), None, OPEN), self.plan())

    def test_the_sweep_passes_the_checkout(self):
        doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "routine-eval-weekly.yml")
                             .read_text(encoding="utf-8"))
        run = next(st["run"] for st in doc["jobs"]["plan"]["steps"] if st.get("id") == "plan")
        self.assertIn('--guidance "$GITHUB_WORKSPACE/agent-guidance"', run)


class LauncherWiringTests(unittest.TestCase):
    """Every automated eval launcher asks eval-pause before it runs anything,
    from a credential-free sparse checkout of the one bounds file."""

    def steps(self, workflow, job):
        doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8"))
        return doc["jobs"][job]["steps"]

    def check(self, steps, gate_id, later):
        co = next(i for i, st in enumerate(steps) if st.get("with", {}).get("path") == "guidance-window")
        self.assertEqual(steps[co]["with"]["repository"], "Adam-S-Daniel/_agent-guidance")
        self.assertEqual(steps[co]["with"]["sparse-checkout"], gmw.WINDOW_REL)
        self.assertIs(steps[co]["with"]["persist-credentials"], False)
        gate = next(i for i, st in enumerate(steps) if st.get("id") == gate_id)
        self.assertLess(co, gate)
        run = steps[gate]["run"]
        self.assertLess(run.index("guidance_merge_window.py eval-pause"), run.index(later))
        self.assertIn('"$rc" -eq 3', run)
        self.assertIn('exit "$rc"', run)

    def test_the_routine_fire_workflow_checks_before_the_allowance_guard(self):
        steps = self.steps("routine-eval-fire.yml", next(iter(yaml.safe_load(
            (REPO_ROOT / ".github" / "workflows" / "routine-eval-fire.yml").read_text(encoding="utf-8"))["jobs"])))
        self.check(steps, "allowance", "allowance_guard.py check")
        run = next(st["run"] for st in steps if st.get("id") == "allowance")
        pause = run[:run.index("allowance_guard.py check")]
        self.assertIn('echo "refused=true" >> "$GITHUB_OUTPUT"', pause)

    def test_the_api_lane_plans_nothing_inside_the_window(self):
        steps = self.steps("eval.yml", "plan")
        self.check(steps, "plan", "plan_scheduled_evals.py")
        run = next(st["run"] for st in steps if st.get("id") == "plan")
        self.assertIn("count=0", run[:run.index("plan_scheduled_evals.py")])
        self.assertIn('echo "guidance_sha=$sha"', run[:run.index("eval-pause")])

    def test_every_api_lane_leg_reads_the_commit_the_plan_judged(self):
        doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "eval.yml").read_text(encoding="utf-8"))
        self.assertEqual(doc["jobs"]["plan"]["outputs"]["guidance_sha"],
                         "${{ steps.plan.outputs.guidance_sha }}")
        legs = [st for st in doc["jobs"]["eval"]["steps"]
                if st.get("with", {}).get("repository") == "Adam-S-Daniel/_agent-guidance"]
        self.assertEqual(len(legs), 1)
        self.assertEqual(legs[0]["with"]["ref"], "${{ needs.plan.outputs.guidance_sha }}")
        self.assertIn("plan", doc["jobs"]["eval"]["needs"])


if __name__ == "__main__":
    unittest.main()
