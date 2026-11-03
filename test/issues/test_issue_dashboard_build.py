"""dashboard/build.py: every snapshot dataset comes from a read or the owner's config.

Invented data only (example-owner, thread-000N). Deterministic: every build
passes --now.
"""
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DASH = REPO / "dashboard"
spec = importlib.util.spec_from_file_location("dashboard_build", DASH / "build.py")
build = importlib.util.module_from_spec(spec)
sys.modules["dashboard_build"] = build
spec.loader.exec_module(build)

NOW = datetime(2026, 1, 6, 13, 0, tzinfo=timezone.utc)
SITE = {"thread_url": "https://claude.ai/code/project/p?thread=", "thread_titles": {}}


def summary(arm, passed, total, **extra):
    return {"arm": arm, "n": 3, "models_used": ["claude-sonnet-9-9"],
            "aggregate": {"objective": {"mean_passed": passed, "mean_total": total}, "cost_usd": {"sum": 1.0}},
            **extra}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def make_results(tmp_path):
    """A results branch with one paired run, one bare run, one guidance run and one usage file."""
    er = tmp_path / "results"
    paired = er / "routine-results" / "20260105T120000Z-aaaaaa" / "writing-adrs" / "ts"
    write(paired / "with_skill" / "summary.json", summary("with_skill", 9, 10))
    write(paired / "without_skill" / "summary.json", summary("without_skill", 6, 10))
    (paired / "report.md").write_text("report")
    bare = er / "routine-results" / "20260105T130000Z-bbbbbb" / "writing-adrs" / "ts"
    write(bare / "without_skill" / "summary.json", summary("without_skill", 5, 10))
    (bare / "report.md").write_text("report")
    guide = er / "routine-results" / "20260105T140000Z-cccccc" / "guidance" / "links" / "ts"
    one = {"objective_checks": [{"passed": True}, {"passed": False}], "models_used": ["claude-opus-9-9"],
           "section": "links", "fixture_name": "handoff"}
    write(guide / "with_guidance_full" / "summary.json", {"arm": "with_guidance_full", **one})
    write(guide / "with_guidance_full_minus_section" / "summary.json",
          {"arm": "with_guidance_full_minus_section", **one,
           "objective_checks": [{"passed": False}, {"passed": False}]})
    (guide / "report.md").write_text("report")
    write(er / "usage" / "weekly-local.json", {
        "schema": 1, "generated_at": "2026-01-05T00:00:00Z",
        "sources": [{"surface": "local", "scope": "transcripts", "from": "a", "to": "b", "sessions_scanned": 4},
                    {"surface": "local", "scope": "hooks", "from": "a", "to": "b", "runs_scanned": 9},
                    {"surface": "cloud", "scope": "guidance-records", "from": "a", "to": "b", "records_scanned": 3}],
        "rows": [{"week": "2026-01-05", "kind": "hook", "name": "all", "invocations": 7},
                 {"week": "2026-01-05", "kind": "skill", "name": "writing-adrs", "invocations": 2}]})
    return er




def routine(**kw):
    return {"name": "R", "what": "w", "schedule": "s", "note": "", "link": None, **kw}


class DashboardBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.results = make_results(self.tmp)

    def test_eval_rows_pairs_bare_and_guidance(self):
        rows, bare = build.eval_rows(str(self.results), "https://example.com/r/")
        by_skill = {r["skill"]: r for r in rows}
        self.assertEqual((by_skill["writing-adrs"]["with_skill"], by_skill["writing-adrs"]["gain"]), (9, 3))
        self.assertEqual((by_skill["guidance/links"]["with_skill"], by_skill["guidance/links"]["without_skill"]), (1, 0))
        self.assertEqual(by_skill["guidance/links"]["fixture"], "guidance/links/handoff")
        self.assertEqual([b["bare"] for b in bare], [5])
        # The bare run sits beside the newest paired run of the same test and model.
        self.assertEqual((bare[0]["with_share"], bare[0]["without_share"]), (0.9, 0.6))
        self.assertTrue(by_skill["writing-adrs"]["report_url"].startswith("https://example.com/r/routine-results/"))

    def test_empty_results_get_placeholder_rows(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        rows, bare = build.eval_rows(str(empty), "x/")
        self.assertEqual(([r["run_id"] for r in rows], [r["run_id"] for r in bare]), (["none"], ["none"]))
        rows, sources, digests = build.usage(str(empty))
        self.assertEqual((rows[0]["kind"], sources[0]["file"], digests[0]["digest"]),
                         ("none", "none", "none"))

    def test_usage_keeps_the_weekly_total_apart(self):
        rows, sources, _digests = build.usage(str(self.results))
        self.assertEqual({r["kind"] for r in rows}, {"hook_all", "skill"})

    def test_usage_sources_carry_each_producers_read_count_and_unit(self):
        _, sources, _ = build.usage(str(self.results))
        self.assertEqual([(s["scanned"], s["scanned_unit"]) for s in sources], [(4, "sessions"), (9, "git hook runs"), (3, "cloud sessions")])
        self.assertEqual(len({s["key"] for s in sources}), 3)

    def test_skill_digest_rows_go_to_their_own_dataset_and_leave_the_totals_alone(self):
        """#562: a skill-digest row is a second view of the same uses."""
        before, _, _ = build.usage(str(self.results))
        path = self.results / "usage" / "weekly-local.json"
        doc = json.loads(path.read_text())
        doc["rows"].append({"week": "2026-01-05", "kind": "skill-digest", "name": "writing-adrs",
                            "repo": "example-owner/r", "surface": "local", "invocations": 2,
                            "sessions": 1, "digest": "abcdef012345"})
        doc["sources"].append({"surface": "local", "scope": "skill-records", "from": "a", "to": "b",
                               "events_scanned": 2})
        write(path, doc)
        rows, sources, digests = build.usage(str(self.results))
        self.assertEqual(rows, before)
        self.assertEqual([(d["name"], d["digest"], d["invocations"]) for d in digests],
                         [("writing-adrs", "abcdef012345", 2)])
        self.assertEqual((sources[-1]["scanned"], sources[-1]["scanned_unit"]), (2, "skill uses"))
        self.assertEqual(len({s["key"] for s in sources}), len(sources))

    def test_usage_refuses_an_unknown_schema(self):
        write(self.tmp / "u" / "usage" / "weekly-x.json", {"schema": 2})
        with self.assertRaises(SystemExit):
            build.usage(str(self.tmp / "u"))

    def test_threads_say_waiting_on_you_and_take_title_overrides(self):
        site = {**SITE, "thread_titles": {"t2": "Renamed"}}
        rows = build.threads([
            {"thread_id": "t1", "title": "A", "state": "blocked", "last_activity_at": "2026-01-05T00:00:00Z"},
            {"thread_id": "t2", "title": "B", "state": "done", "last_activity_at": "2026-01-06T00:00:00Z"}], site)
        self.assertEqual([r["title"] for r in rows], ["Renamed", "A"])
        self.assertEqual(rows[1]["state"], "Waiting on you")
        self.assertEqual(rows[1]["link"], SITE["thread_url"] + "t1")

    def test_threads_carry_their_session_and_branch_so_prs_can_name_them(self):
        rows = build.threads([
            {"thread_id": "t1", "title": "A", "state": "working", "session_id": "cse_01Abc"},
            {"thread_id": "t2", "title": "B", "state": "done"}], SITE, {"01Abc": "claude/project-thread-abc123"})
        by = {r["title"]: r for r in rows}
        self.assertEqual((by["A"]["session"], by["A"]["branch"]), ("01Abc", "claude/project-thread-abc123"))
        self.assertEqual((by["B"]["session"], by["B"]["branch"]), ("", ""))

    def test_routine_health_comes_from_the_last_run(self):
        trig = {"kind": "trigger", "id": "t"}
        cases = [
            (routine(source=trig), {"t": {"last_run": {"status": "ROUTINE_RUN_STATUS_FAILED", "fired_at": "2026-01-06T12:00:00Z"}}}, {}, "Failing", "Failed"),
            (routine(source=trig, expect_every_hours=1), {"t": {"last_run": {"status": "ROUTINE_RUN_STATUS_SUCCEEDED", "fired_at": "2026-01-06T09:00:00Z"}}}, {}, "Late", "Succeeded"),
            (routine(source=trig, expect_every_hours=1), {"t": {"last_run": {"status": "ROUTINE_RUN_STATUS_SUCCEEDED", "fired_at": "2026-01-06T12:30:00Z"}}}, {}, "OK", "Succeeded"),
            (routine(source=trig), {"t": {"enabled": False}}, {}, "Paused", None),
            (routine(source=trig, expect_every_hours=168), {"t": {"next_run_at": "2026-01-13T18:00:00Z"}}, {}, "Not run yet", None),
            (routine(source=trig, expect_every_hours=1), {"t": {"next_run_at": "2026-01-06T00:00:00Z"}}, {}, "Late", None),
            (routine(source={"kind": "none"}, retired=True), {}, {}, "Retired", "Idle"),
            (routine(source={"kind": "workflow", "repo": "o/r", "workflow": "w.yml"}), {},
             {"o/r:w.yml": [{"created_at": "2026-01-05T00:00:00Z", "status": "completed", "conclusion": "success"},
                            {"created_at": "2026-01-06T00:00:00Z", "status": "completed", "conclusion": "cancelled"}]},
             "Check", "Cancelled"),
        ]
        for cfg, triggers, runs, health, result in cases:
            with self.subTest(health=health):
                row = build.routines([cfg], triggers, runs, NOW)[0]
                self.assertEqual((row["health"], row["last_result"]), (health, result))

    def test_a_workflow_turned_off_in_github_reads_as_paused(self):
        wf = routine(source={"kind": "workflow", "repo": "o/r", "workflow": "w.yml"})
        runs = {"o/r:w.yml": [{"created_at": "2026-01-06T00:00:00Z", "status": "completed", "conclusion": "success"}]}
        for state, health in [("disabled_manually", "Paused"), ("disabled_inactivity", "Paused"), ("active", "OK")]:
            with self.subTest(state=state):
                row = build.routines([wf], {}, runs, NOW, {"o/r:w.yml": state})[0]
                self.assertEqual(row["health"], health)
        self.assertEqual(build.routines([wf], {}, runs, NOW)[0]["health"], "OK")

    def test_get_trigger_output_is_accepted_whole(self):
        full = {"t": {"trigger": {"enabled": True, "next_run_at": "2026-01-06T14:00:00.5Z",
                                  "last_run": {"status": "ROUTINE_RUN_STATUS_PENDING", "fired_at": "2026-01-06T12:59:00.1Z"}}}}
        row = build.routines([routine(source={"kind": "trigger", "id": "t"})], full, {}, NOW)[0]
        self.assertEqual((row["last_result"], row["last_run"], row["next_run"]),
                         ("Running", "2026-01-06T12:59:00Z", "2026-01-06T14:00:00Z"))

    def test_next_cron(self):
        for expr, want in [("0 7 * * 2", "2026-01-13T07:00:00Z"),  # NOW is Tuesday 13:00, so next Tuesday
                           ("53 6 * * *", "2026-01-07T06:53:00Z"),
                           ("20 * * * *", "2026-01-06T13:20:00Z"),
                           ("0 7 1 * *", None)]:  # day-of-month schedules are not computed
            with self.subTest(expr=expr):
                self.assertEqual(build.next_cron(expr, NOW), want)

    def test_checkins_keep_this_projects_pending_one_shots(self):
        rows = build.checkins([
            {"id": "a", "name": "Later", "run_once_at": "2026-01-07T00:00:00Z", "hearth_channel_id": "c1"},
            {"id": "b", "name": "Past", "run_once_at": "2026-01-05T00:00:00Z", "hearth_channel_id": "c1"},
            {"id": "c", "name": "Other project", "run_once_at": "2026-01-07T00:00:00Z", "hearth_channel_id": "c2"},
        ], "c1", NOW)
        self.assertEqual([r["id"] for r in rows], ["a"])
        self.assertEqual(build.checkins([], "c1", NOW)[0]["id"], "none")

    def test_waiting_collects_every_source_and_drops_what_is_done(self):
        snap = {"cleanup": [
            {"id": "C1", "status": "Not started", "waiting_on_you": "Needs the laptop", "waiting_since": "2026-01-02T00:00:00Z"},
            {"id": "C2", "status": "Done", "waiting_on_you": "Needs the laptop"},
            {"id": "C3", "status": "Not started", "waiting_on_you": "Needs the laptop", "waiting_since": "2026-01-01T00:00:00Z"}],
            "waiting_manual": [{"item": "Merged already", "link": "https://github.com/example-owner/r/pull/1"},
                               {"item": "Still open", "link": "https://github.com/example-owner/r/pull/2"}]}
        needs = [{"title": "Decide", "html_url": "https://github.com/example-owner/r/pull/3", "state": "open",
                  "repository_url": "https://api.github.com/repos/example-owner/r", "labels": [{"name": "needs-owner"}]},
                 {"title": "Held", "html_url": "https://github.com/example-owner/r/issues/4", "state": "open",
                  "repository_url": "https://api.github.com/repos/example-owner/r", "labels": [{"name": "on-hold"}]}]
        reviews = [{"repo": "example-owner/r", "name": "PR", "environment": "env", "head_sha": "new", "job_url": "https://example.com/new"},
                   {"repo": "example-owner/r", "name": "PR", "environment": "env", "head_sha": "old", "job_url": "https://example.com/old"}]
        threads = [{"thread_id": "t1", "title": "Blocked one", "state": "blocked"},
                   {"thread_id": "t2", "title": "Resolved", "state": "blocked", "resolved": True}]
        rows = build.waiting(snap, needs, reviews, {"example-owner/r": ["new"]}, threads,
                             {"https://github.com/example-owner/r/pull/1": "merged"}, SITE)
        self.assertEqual([r["item"] for r in rows],
                         ["Decide", "Approve the env review for PR", "Blocked one", "Cleanup items C1, C3", "Still open"])
        self.assertEqual(rows[0]["where"], "example-owner/r")
        self.assertEqual(rows[1]["link"], "https://example.com/new")
        self.assertEqual(rows[3]["since"], "2026-01-01T00:00:00Z")
        self.assertTrue(all(r["id"] for r in rows))

    def test_waiting_has_a_placeholder_when_nothing_waits(self):
        rows = build.waiting({"cleanup": []}, [], [], {}, [], {}, SITE)
        self.assertEqual([(r["id"], r["item"]) for r in rows], [("none", "Nothing waiting on you")])

    def test_loop_stage_status_follows_its_gaps(self):
        cfg = {"home_thread_id": "t0", "grid": [],
               "stages": [{"order": "1", "kind": "k", "stage": "a", "what": "w", "gaps": ["G1", "G2"]},
                          {"order": "2", "kind": "k", "stage": "b", "what": "w", "gaps": ["G1"]},
                          {"order": "3", "kind": "k", "stage": "c", "what": "w", "gaps": [], "override": "Off"}],
               "lanes": [{"lane": "L", "thread": "T", "thread_id": "t1", "does": "d", "latest": "x"}]}
        status = {"gaps": [{"gap": "G1", "title": "x", "status": "done", "pr": "https://example.com/1"},
                           {"gap": "G2", "title": "y", "status": "open"}]}
        stages, grid, lanes, gaps = build.loop(cfg, status, SITE)
        self.assertEqual([s["status"] for s in stages], ["In progress", "Done", "Off"])
        self.assertEqual((stages[1]["link"], stages[2]["link"]), ("https://example.com/1", SITE["thread_url"] + "t0"))
        self.assertEqual(lanes[0]["link"], SITE["thread_url"] + "t1")

    def test_roster_and_budget_are_read_from_the_repo(self):
        rows = build.roster({"why": {}, "dropped": [
            {"id": "claude-gone-1", "model": "Gone 1", "role": "Tested", "status": "Dropped"}]})
        roles = [r["role"] for r in rows]
        self.assertEqual((roles.count("Judge"), roles.count("Quick check")), (1, 1))
        self.assertIn("Tested", roles)
        self.assertEqual(rows[-1]["id"], "claude-gone-1")
        self.assertEqual(build.model_name("claude-sonnet-5-5"), "Sonnet 5.5")
        self.assertEqual([r["setting"] for r in build.budget()], build.BUDGET_KEYS)

    def test_example_config_builds_every_dataset_the_page_defines(self):
        out = self.tmp / "ds"
        build.main(["--results", str(self.results), "--inputs", str(DASH / "inputs.example"),
                    "--config", str(DASH / "config.example"), "--out", str(out), "--now", NOW.isoformat()])
        built = {p.stem for p in out.glob("*.json")}
        defined = json.loads((DASH / "page" / "datasets.json").read_text())
        self.assertEqual(built, {k for k, v in defined.items() if v["source"]["kind"] == "file"})
        for name in built:
            self.assertTrue(json.loads((out / f"{name}.json").read_text()), name)
        waiting = json.loads((out / "waiting.json").read_text())
        self.assertNotIn("Paused idea", [r["item"] for r in waiting])  # labeled on-hold

    def test_run_stream_maps_states_windows_dedupes_and_sorts(self):
        def wf(url, at, status="completed", conclusion="success", end=None):
            return {"repo": "o/skills-evals", "workflow": "ci.yml", "event": "push", "status": status,
                    "conclusion": conclusion, "created_at": at, "updated_at": end or at, "html_url": url,
                    "display_title": "T " + url}
        cases = [("queued", None, "Queued"), ("waiting", None, "Queued"), ("in_progress", None, "Running"),
                 ("completed", "success", "Succeeded"), ("completed", "failure", "Failed"),
                 ("completed", "timed_out", "Failed"), ("completed", "cancelled", "Cancelled"),
                 ("completed", "skipped", "Skipped"), ("completed", "action_required", "Needs approval"),
                 ("completed", "stale", "Stale")]
        for status, conclusion, want in cases:
            with self.subTest(status=status, conclusion=conclusion):
                row = build.run_stream({"workflow_runs": [wf("u", "2026-01-06T12:00:00Z", status, conclusion)]}, NOW)[0]
                self.assertEqual(row["state"], want)
        dump = {
            "workflow_runs": [
                wf("old", "2025-12-30T12:59:59Z"),  # just outside 7 days
                wf("edge", "2025-12-30T13:00:00Z"),
                wf("new", "2026-01-06T12:00:00Z", end="2026-01-06T12:02:05Z"),
                wf("new", "2026-01-06T12:00:00Z"),  # duplicate
                wf("live", "2026-01-06T12:30:00Z", "in_progress", None),
            ],
            "routine_runs": [
                {"trigger_id": "t1", "name": "Nightly", "fired_at": "2026-01-06T09:00:00Z",
                 "finished_at": "2026-01-06T09:10:30Z", "status": "ROUTINE_RUN_STATUS_FAILED"},
                {"trigger_id": "t1", "name": "Nightly", "fired_at": "2026-01-06T09:00:00Z",
                 "finished_at": None, "status": "ROUTINE_RUN_STATUS_RUNNING"},
                {"trigger_id": "t2", "name": "Sweep", "fired_at": "2026-01-06T12:45:00Z",
                 "finished_at": "2026-01-06T12:50:00Z", "status": "ROUTINE_RUN_STATUS_PENDING"},
                {"trigger_id": "t3", "name": "Odd", "fired_at": "2026-01-06T08:00:00Z",
                 "finished_at": None, "status": "ROUTINE_RUN_STATUS_SUCCEEDED"},
            ],
        }
        rows = build.run_stream(dump, NOW)
        self.assertEqual([r["key"] for r in rows],
                         ["t2@2026-01-06T12:45:00Z", "live", "new", "t1@2026-01-06T09:00:00Z",
                          "t3@2026-01-06T08:00:00Z", "edge"])
        by = {r["key"]: r for r in rows}
        self.assertEqual(by["new"]["duration_s"], 125)
        self.assertEqual((by["new"]["source"], by["new"]["name"], by["new"]["kind"]),
                         ("skills-evals", "ci.yml", "workflow"))
        self.assertIsNone(by["live"]["duration_s"])
        r = by["t1@2026-01-06T09:00:00Z"]
        self.assertEqual((r["state"], r["duration_s"], r["kind"], r["source"], r["title"]),
                         ("Failed", 630, "routine", "scheduled task", "Nightly"))
        self.assertEqual(r["link"], "https://claude.ai/scheduled-task/t1")
        pending = by["t2@2026-01-06T12:45:00Z"]
        self.assertEqual((pending["state"], pending["duration_s"]), ("Running", None))

    def test_run_stream_caps_rows_and_has_a_placeholder(self):
        runs = [{"repo": "o/r", "workflow": "w", "status": "queued", "created_at": "2026-01-06T12:00:00Z",
                 "html_url": f"u{i}"} for i in range(600)]
        self.assertEqual(len(build.run_stream({"workflow_runs": runs}, NOW)), 500)
        # An older failure past the cap is still listed: the cap trims only runs that went fine.
        failed = {"repo": "o/r", "workflow": "w", "status": "completed", "conclusion": "failure",
                  "created_at": "2026-01-01T12:00:00Z", "updated_at": "2026-01-01T12:01:00Z", "html_url": "old-fail"}
        rows = build.run_stream({"workflow_runs": runs + [failed]}, NOW)
        self.assertEqual(len(rows), 501)
        self.assertEqual(rows[-1]["key"], "old-fail")
        for dump in ({}, {"workflow_runs": [dict(runs[0], created_at="2025-01-01T00:00:00Z")]}):
            rows = build.run_stream(dump, NOW)
            self.assertEqual([r["key"] for r in rows], ["none"])

    # --- Cost and benefit ---------------------------------------------------------

    def cb_now(self):
        return datetime(2026, 11, 5, 13, 0, tzinfo=timezone.utc)  # a Thursday, in the week of 2026-11-02

    def cb_starts(self):
        return build.week_starts(build.COST_START, self.cb_now())

    def sample(self, at, cost, session="cse_s1", created="2026-10-25T17:00:00Z", updated=None, **kw):
        return {"v": 1, "at": at, "source": "refresh", "thread_id": "cmsg_thread0001", "session_id": session,
                "created_at": created, "updated_at": updated or at, "cost_usd": cost, "output_tokens": 1,
                "error": None, **kw}

    def test_weeks_start_monday_17_utc_and_run_through_the_week_holding_now(self):
        starts = self.cb_starts()
        self.assertEqual([s.date().isoformat() for s in starts], ["2026-10-19", "2026-10-26", "2026-11-02"])
        self.assertEqual(build.week_of(datetime(2026, 10, 26, 16, 59, tzinfo=timezone.utc), starts), 0)
        self.assertEqual(build.week_of(datetime(2026, 10, 26, 17, 0, tzinfo=timezone.utc), starts), 1)
        self.assertEqual(build.week_starts(build.COST_START, datetime(2026, 10, 1, tzinfo=timezone.utc)), [])

    def test_session_spend_between_two_samples_splits_at_the_week_boundary(self):
        # $10 rose over 48 hours; 24 of them fall before Monday 2026-10-26 17:00.
        samples = [self.sample("2026-10-25T17:00:00Z", 0), self.sample("2026-10-27T17:00:00Z", 10),
                   self.sample("2026-10-28T00:00:00Z", None)]
        usd, estimated = build.session_spend(samples, self.cb_starts())
        self.assertEqual((usd[0], usd[1]), (5, 5))
        self.assertEqual(estimated, set())
        # A cost that falls back between samples adds nothing.
        usd, _ = build.session_spend([self.sample("2026-10-27T00:00:00Z", 0), self.sample("2026-10-28T00:00:00Z", 0)],
                                     self.cb_starts())
        self.assertEqual(usd, {})

    def test_a_single_backfill_sample_is_spread_from_creation_and_marked_estimated(self):
        s = self.sample("2026-10-28T00:00:00Z", 8, created="2026-10-25T17:00:00Z", updated="2026-10-27T17:00:00Z",
                        source="backfill")
        usd, estimated = build.session_spend([s], self.cb_starts())
        self.assertEqual((usd[0], usd[1], estimated), (4, 4, {0, 1}))
        # An empty span puts it all at that instant.
        s = self.sample("2026-10-28T00:00:00Z", 3, created="2026-10-27T00:00:00Z", updated="2026-10-27T00:00:00Z")
        self.assertEqual(build.session_spend([s], self.cb_starts())[0], {1: 3})

    def plan_row(self, at, cost, after=None, points=None):
        return {"run_id": "r" + at, "fired_at": at, "cost_usd": cost, "meter_points": points, "account_week_after": after}

    def test_points_per_usd_is_the_account_reading_over_all_spend_of_complete_weeks(self):
        starts = self.cb_starts()
        rows = [self.plan_row("2026-10-20T10:00:00Z", 5, after=20), self.plan_row("2026-10-22T10:00:00Z", 5, after=30),
                self.plan_row("2026-11-03T10:00:00Z", 50, after=90)]  # the current week is not complete
        rate, basis, weeks = build.points_per_usd(rows, {0: 20, 2: 999}, starts, self.cb_now())
        self.assertEqual((rate, weeks), (1.0, 1))  # the week's largest reading, 30, over $20 + $10
        self.assertIn("upper bound", basis)
        rate, basis, weeks = build.points_per_usd([self.plan_row("2026-10-27T10:00:00Z", 5)], {}, starts, self.cb_now())
        self.assertEqual((rate, weeks), (build.DEFAULT_POINTS_PER_USD, 0))
        self.assertEqual(build.DEFAULT_POINTS_PER_USD, 0.07)
        self.assertIn("default", basis)

    def test_loop_changes_parse_each_prefix_and_ignore_unmerged_prs(self):
        def pr(n, ref, merged="2026-10-27T10:00:00Z"):
            return {"repo": "example-owner/r", "number": n, "url": "https://example.com/" + str(n), "head_ref": ref,
                    "title": "t", "state": "closed", "merged_at": merged}
        got = build.loop_changes([
            pr(1, "eval-improve/writing-adrs"), pr(2, "draft-skill/new-one"), pr(3, "retire-skill/old-one"),
            pr(4, "eval-guidance-improve/links/extra"), pr(5, "retire-guidance/handoff"),
            pr(6, "eval-improve/unmerged", merged=None), pr(7, "feature/other"), pr(1, "eval-improve/writing-adrs")])
        self.assertEqual([(c["kind"], c["subject"]) for c in got],
                         [("edit", "writing-adrs"), ("new skill", "new-one"), ("removal", "old-one"),
                          ("guidance edit", "links"), ("guidance removal", "handoff")])

    def cb(self, **kw):
        args = dict(er=str(self.tmp / "no-results"), plan_rows=[], usage_rows=[], decisions=[], samples=[],
                    owner_msgs=[], prs=[], explorer={}, now=self.cb_now())
        args.update(kw)
        return build.cost_benefit(*args.values())

    def test_real_work_reach_counts_uses_in_weeks_after_a_change_merged(self):
        pr = {"repo": "example-owner/r", "number": 1, "url": "u", "head_ref": "eval-improve/writing-adrs",
              "title": "t", "state": "closed", "merged_at": "2026-10-27T10:00:00Z"}
        gpr = dict(pr, number=2, head_ref="eval-guidance-improve/links", merged_at="2026-10-20T10:00:00Z")
        usage = [{"week": "2026-10-19", "kind": "skill", "name": "writing-adrs", "invocations": 4},
                 {"week": "2026-10-26", "kind": "skill", "name": "writing-adrs", "invocations": 3},
                 {"week": "2026-11-02", "kind": "skill", "name": "writing-adrs", "invocations": 2},
                 {"week": "2026-10-26", "kind": "guidance", "name": "full", "invocations": 0, "sessions": 5},
                 {"week": "2026-11-02", "kind": "skill", "name": "other-skill", "invocations": 9}]
        weeks, summary = self.cb(prs=[pr, gpr], usage_rows=usage)
        by = {w["week"]: w for w in weeks}
        # The skill change merged in week 2 does not count week 1's uses; the guidance change counts its sessions.
        self.assertEqual([by[k]["real_work_reach"] for k in ("2026-10-19", "2026-10-26", "2026-11-02")], [0, 8, 2])
        self.assertEqual([by[k]["changes"] for k in ("2026-10-19", "2026-10-26", "2026-11-02")], [1, 1, 0])
        sm = {r["key"]: r for r in summary}
        self.assertEqual(sm["bar_changes"]["value"], 2)
        self.assertEqual(sm["real_work_reach"]["value"], 8)  # the latest complete week is 2026-10-26
        self.assertEqual(sm["decision_yield"]["value"], "2 of 0")

    def test_owner_messages_dedupe_and_decisions_fall_in_their_week(self):
        msgs = [{"message_id": "cmsg_m1", "sent_at": "2026-10-26T16:59:00Z"},
                {"message_id": "cmsg_m1", "sent_at": "2026-10-26T16:59:00Z"},
                {"message_id": "cmsg_m2", "sent_at": "2026-10-26T17:00:00Z"}]
        decisions = [{"date": "2026-10-25"}, {"date": "2026-10-26"}, {"date": "2026-10-27"}]
        weeks, _ = self.cb(owner_msgs=msgs, decisions=decisions)
        self.assertEqual([(w["owner_messages"], w["decisions"]) for w in weeks], [(1, 1), (1, 2), (0, 0)])
        path = self.tmp / "m.jsonl"
        path.write_text(json.dumps(msgs[0]) + "\nnot json\n\n" + json.dumps(dict(msgs[2], v=2)) + "\n")
        self.assertEqual(len(build.load_jsonl(str(path))), 1)
        self.assertEqual(build.load_jsonl(str(self.tmp / "missing.jsonl")), [])

    def test_build_cost_points_api_dollars_and_verdicts_reach_the_week_rows(self):
        write(self.tmp / "res" / "results" / "run" / "with_skill" / "summary.json",
              summary("with_skill", 9, 10, usage={"started_at": "2026-10-21T10:00:00Z",
                                                  "reasons": {"meter": build.API_BILLED}}))
        write(self.tmp / "res" / "results" / "run" / "other" / "summary.json",
              summary("with_skill", 9, 10, usage={"started_at": "2026-10-21T10:00:00Z", "reasons": {}}))
        self.assertIn(build.API_BILLED, (REPO / "harness" / "run_eval.py").read_text())
        explorer = {"skills": [{"verdict": "keep"}, {"verdict": "insufficient"}, {"verdict": None}],
                    "guidance": {"sections": [{"verdict": "retire"}]}}
        plan = [self.plan_row("2026-10-21T10:00:00Z", 10, after=10, points=2)]
        samples = [self.sample("2026-10-25T17:00:00Z", 0), self.sample("2026-10-26T17:00:00Z", 10)]
        weeks, summary_rows = self.cb(er=str(self.tmp / "res"), plan_rows=plan, samples=samples, explorer=explorer)
        w = weeks[0]
        rate = 10 / (10 + 10)  # reading 10 over thread $10 + plan-run $10 in the one complete week with a reading
        self.assertEqual((w["api_usd"], w["build_usd"], w["build_estimated"]), (1.0, 10.0, False))
        self.assertEqual((w["run_count"], w["run_meter_points"], w["run_points_est"]), (1, 2, 10 * rate))
        self.assertEqual((w["build_points"], w["total_points"]), (10 * rate, 10 * rate + 10 * rate + 1.0 * rate))
        self.assertEqual([x["verdicts"] for x in weeks], [None, None, 2])
        sm = {r["key"]: r for r in summary_rows}
        self.assertEqual(sm["points_per_usd"]["value"], rate)
        self.assertEqual(sm["cost_per_verdict"]["value"], round((10 + 10 + 1.0) / 2, 2))

    def test_the_bars_follow_the_week_and_the_date(self):
        def bars(now, **kw):
            _, rows = self.cb(now=now, **kw)
            return {r["key"]: r for r in rows}
        sm = bars(self.cb_now())
        self.assertEqual((sm["bar_changes"]["status"], sm["bar_build"]["status"]), ("Not met", "Met"))
        self.assertIn("Due 2026-12-15", sm["bar_build"]["note"])
        self.assertNotIn("bar_verdict", sm)
        prs = [{"repo": "o/r", "number": n, "url": "u", "head_ref": f"eval-improve/s{n}", "title": "t",
                "state": "closed", "merged_at": "2026-10-20T10:00:00Z"} for n in (1, 2, 3)]
        usage = [{"week": "2026-10-19", "kind": "skill", "name": f"s{n}", "invocations": 1} for n in (1, 2, 3)]
        late = datetime(2026, 12, 16, 0, 0, tzinfo=timezone.utc)
        sm = bars(late, prs=prs, usage_rows=usage)
        self.assertEqual((sm["bar_changes"]["status"], sm["bar_verdict"]["value"]), ("Met", "Met: keep the eval system"))
        hot = [self.sample("2026-12-10T00:00:00Z", 100000, created="2026-12-10T00:00:00Z")]
        ppu_rows = [self.plan_row("2026-10-20T10:00:00Z", 1, after=50)]
        sm = bars(late, prs=prs, usage_rows=usage, samples=hot, plan_rows=ppu_rows)
        self.assertEqual((sm["bar_build"]["status"], sm["bar_verdict"]["value"]),
                         ("Not met", "Missed: cut back to guidance-only evals"))

    def test_cost_benefit_placeholder_before_the_first_week(self):
        weeks, summary_rows = self.cb(now=datetime(2026, 10, 1, tzinfo=timezone.utc))
        self.assertEqual([w["week"] for w in weeks], ["none"])
        self.assertTrue(summary_rows)

    def hb_item(self, n, state="open", created="2026-10-20T12:00:00Z", closed=None, **kw):
        row = {"repo": "Adam-S-Daniel/example-repo", "number": n, "url": f"https://example.com/{n}", "title": f"T{n}",
               "state": state, "created_at": created, "closed_at": closed, "kind": "partial", "severity": "low",
               "finding_id": f"demo-{n}"}
        row.update(kw)
        return row

    HB_NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)

    def test_half_built_missing_dump_is_not_checked(self):
        issues, summary = build.half_built({}, self.HB_NOW)
        self.assertEqual([r["key"] for r in issues], ["none"])
        self.assertEqual((summary[0]["status"], summary[0]["open"], summary[0]["checked_at"]), ("not-checked", 0, None))
        _, via_build = build.half_built(build.load(str(self.tmp / "absent.json"), {}), self.HB_NOW)
        self.assertEqual(via_build[0]["status"], "not-checked")

    def test_half_built_empty_dump_is_clear(self):
        dump = {"checked_at": "2026-11-03T10:00:00Z", "total_count": 0, "incomplete": False, "items": []}
        issues, summary = build.half_built(dump, self.HB_NOW)
        self.assertEqual([r["key"] for r in issues], ["none"])
        self.assertEqual((summary[0]["status"], summary[0]["checked_at"]), ("clear", "2026-11-03T10:00:00Z"))
        self.assertIs(summary[0]["incomplete"], False)

    def test_half_built_counts_sorts_and_drops_old_closed_items(self):
        items = [
            self.hb_item(1, severity="low", created="2026-10-01T12:00:00Z"),
            self.hb_item(2, severity="high", kind="broken", created="2026-10-30T12:00:00Z"),
            self.hb_item(3, severity="high", kind="idle", created="2026-10-25T12:00:00Z"),
            self.hb_item(4, severity="medium", kind="implied-only"),
            self.hb_item(5, state="closed", severity="high", closed="2026-10-30T12:00:00Z"),
            self.hb_item(6, state="closed", closed="2026-10-26T11:59:00Z"),
            self.hb_item(7, state="closed", closed=None)]
        dump = {"checked_at": "2026-11-03T10:00:00Z", "incomplete": True, "items": items}
        issues, summary = build.half_built(dump, self.HB_NOW)
        self.assertEqual([r["number"] for r in issues], [3, 2, 4, 1, 5])
        self.assertEqual(issues[0]["key"], "Adam-S-Daniel/example-repo#3")
        self.assertEqual((issues[0]["opened"], issues[0]["age_days"], issues[0]["closed_at"]), ("2026-10-25", 9, None))
        self.assertEqual(issues[-1]["closed_at"], "2026-10-30T12:00:00Z")
        self.assertEqual({k: v for k, v in summary[0].items() if k != "key"},
                         {"open": 4, "high": 2, "broken": 1, "partial": 1, "implied_only": 1, "idle": 1,
                          "needs_owner": 0, "fixed_7d": 1,
                          "checked_at": "2026-11-03T10:00:00Z", "incomplete": True, "status": "attention"})

    def test_half_built_puts_high_first_then_what_needs_the_owner(self):
        dump = {"checked_at": "2026-11-03T10:00:00Z", "items": [
            self.hb_item(1, severity="medium", created="2026-10-01T12:00:00Z"),
            self.hb_item(2, severity="low", labels=["half-built-or-broken", "needs-owner"]),
            self.hb_item(3, severity="high"),
            self.hb_item(4, severity="medium", labels=["needs-owner"], created="2026-10-30T12:00:00Z")]}
        issues, summary = build.half_built(dump, self.HB_NOW)
        self.assertEqual([r["number"] for r in issues], [3, 4, 2, 1])
        self.assertEqual([r["needs_owner"] for r in issues], ["", "needs you", "needs you", ""])
        self.assertEqual(summary[0]["needs_owner"], 2)

    def test_half_built_unknown_kind_and_severity(self):
        dump = {"checked_at": "2026-11-03T10:00:00Z", "items": [
            self.hb_item(1, kind=None, severity=None), self.hb_item(2, severity="low")]}
        issues, summary = build.half_built(dump, self.HB_NOW)
        self.assertEqual([(r["number"], r["kind"], r["severity"]) for r in issues],
                         [(2, "partial", "low"), (1, "unknown", "unknown")])
        self.assertEqual((summary[0]["open"], summary[0]["high"]), (2, 0))

    def test_the_page_draws_the_half_built_banner_from_both_datasets(self):
        page = (DASH / "page" / "index.html").read_text()
        for name in ("half_built_issues", "half_built_summary"):
            self.assertIn(f'data-source="{name}"', page)
        self.assertIn("Half-built and broken features", page)
        self.assertLess(page.index("card-halfbuilt"), page.index("tile-routines"))
        self.assertIn("half_built_issues: 'key'", page)

    FQ_NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)

    def fq_queue(self, **kw):
        queue = {
            "schema": 1, "generated_at": "2026-11-03T10:00:00Z",
            "requests": [
                {"issue": 11, "kind": "needs-fixtures", "subject": "demo-new", "state": "open",
                 "opened_at": "2026-11-02T12:00:00Z", "closed_at": None, "prs": []},
                {"issue": 12, "kind": "needs-harder-fixtures", "subject": "demo-old", "state": "open",
                 "opened_at": "2026-10-30T00:00:00Z", "closed_at": None,
                 "prs": [{"number": 40, "state": "closed", "merged_at": None, "auto_merge": False},
                         {"number": 44, "state": "merged", "merged_at": "2026-11-01T00:00:00Z", "auto_merge": True}]},
                {"issue": 13, "kind": "needs-trigger-set", "subject": "demo-done", "state": "closed",
                 "opened_at": "2026-10-01T00:00:00Z", "closed_at": "2026-10-05T00:00:00Z", "prs": []},
            ],
            "fixtures": [
                {"path": "evals/demo-old/a", "subject": "demo-old", "origin_kind": "real-work", "request": 12,
                 "runs": 4, "cost_usd": 1.25},
                {"path": "evals/demo-old/b", "subject": "demo-old", "origin_kind": "invented", "request": 12,
                 "runs": 2, "cost_usd": 0.5},
                {"path": "evals/other/c", "subject": "other", "origin_kind": "invented", "request": 99,
                 "runs": 7, "cost_usd": 9.0},
            ],
            "totals": {"requests_open": 2, "requests_closed": 1, "prs_merged": 1, "fixtures_real_work": 1,
                       "fixtures_invented": 2, "fixture_runs": 13, "cost_points": 3, "cost_usd": 10.75},
            "findings": [],
        }
        queue.update(kw)
        return {"fixture_queue": queue}

    def test_fixture_queue_null_or_absent_is_not_reported(self):
        for explorer in ({}, {"fixture_queue": None}, {"schema": 1}):
            rows, summary = build.fixture_queue(explorer, self.FQ_NOW)
            self.assertEqual([r["key"] for r in rows], ["none"])
            self.assertEqual((summary[0]["key"], summary[0]["status"], summary[0]["findings"]), ("all", "not-reported", 0))
            self.assertIsNone(summary[0]["requests_open"])

    def test_fixture_queue_rows_fold_in_prs_and_fixtures_and_sort_open_oldest_first(self):
        rows, summary = build.fixture_queue(self.fq_queue(), self.FQ_NOW)
        self.assertEqual([r["key"] for r in rows], ["12", "11", "13"])
        old = rows[0]
        self.assertEqual((old["kind"], old["subject"], old["state"], old["opened"]), ("harder fixtures", "demo-old", "open", "2026-10-30"))
        self.assertEqual(old["age_days"], 4.5)  # full precision; the page rounds
        self.assertEqual((old["prs"], old["pr_url"], old["merged"]), (2, "https://github.com/Adam-S-Daniel/skills-evals/pull/44", True))
        self.assertEqual((old["fixtures"], old["real_work"], old["runs"], old["cost_usd"]), (2, 1, 6, 1.75))
        self.assertEqual(old["issue_url"], "https://github.com/Adam-S-Daniel/skills-evals/issues/12")
        new = rows[1]
        self.assertEqual((new["kind"], new["prs"], new["pr_url"], new["merged"], new["fixtures"]), ("new fixtures", 0, "", False, 0))
        done = rows[2]
        self.assertEqual((done["kind"], done["state"], done["age_days"], done["closed_at"]), ("trigger set", "closed", None, "2026-10-05T00:00:00Z"))
        self.assertEqual({k: v for k, v in summary[0].items() if k != "key"},
                         {"requests_open": 2, "requests_closed": 1, "prs_merged": 1, "fixtures_real_work": 1,
                          "fixtures_invented": 2, "fixture_runs": 13, "cost_points": 3, "cost_usd": 10.75,
                          "findings": 0, "findings_high": 0, "status": "ok", "generated_at": "2026-11-03T10:00:00Z"})

    def test_fixture_queue_any_finding_needs_attention(self):
        findings = [{"finding_id": "demo-1", "kind": "stuck-pr", "severity": "high", "subject": "demo-old", "url": "https://example.com/1"},
                    {"finding_id": "demo-2", "kind": "stale-request", "severity": "low", "subject": "demo-new", "url": "https://example.com/2"}]
        _, summary = build.fixture_queue(self.fq_queue(findings=findings), self.FQ_NOW)
        self.assertEqual((summary[0]["status"], summary[0]["findings"], summary[0]["findings_high"]), ("attention", 2, 1))

    def test_fixture_queue_with_no_requests_is_ok_with_a_placeholder(self):
        rows, summary = build.fixture_queue(self.fq_queue(requests=[], fixtures=[]), self.FQ_NOW)
        self.assertEqual([r["key"] for r in rows], ["none"])
        self.assertEqual(summary[0]["status"], "ok")

    def test_the_page_draws_the_fixture_requests_panel(self):
        page = (DASH / "page" / "index.html").read_text()
        for name in ("fixture_requests", "fixture_queue_summary"):
            self.assertIn(f'data-source="{name}"', page)
        self.assertIn("Fixture requests", page)
        self.assertIn("fixture_requests: 'key'", page)
        self.assertLess(page.index('id="loop"'), page.index("card-fixture-requests"))
        self.assertLess(page.index("card-fixture-requests"), page.index('id="impact"'))

    def test_red_runs_list_links_public_runs_and_drops_bad_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            er = Path(tmp)
            write(er / "usage" / "weekly-ci.json", {"schema": 1, "rows": [], "red_runs": [
                {"week": "2026-10-19", "repo": "private", "created_at": None, "conclusion": None, "url": None},
                {"week": "2026-10-26", "repo": "example-owner/widgets", "created_at": "2026-10-27T08:00:00Z",
                 "conclusion": "failure", "url": "https://github.com/example-owner/widgets/actions/runs/9100002"},
                {"week": "2026-10-26", "repo": "example-owner/widgets", "created_at": "2026-10-28T08:00:00Z",
                 "conclusion": "timed_out", "url": "https://example.com/not-a-run"},
                "not a dict"]})
            rows = build.ci_red_runs(str(er))
        self.assertEqual([(r["week"], r["created_at"]) for r in rows],
                         [("2026-10-26", "2026-10-28T08:00:00Z"), ("2026-10-26", "2026-10-27T08:00:00Z"), ("2026-10-19", None)])
        self.assertIsNone(rows[0]["url"])
        self.assertEqual(rows[1]["url"], "https://github.com/example-owner/widgets/actions/runs/9100002")
        self.assertEqual(len({r["key"] for r in rows}), 3)

    def test_red_runs_placeholder_without_the_file_or_the_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([r["key"] for r in build.ci_red_runs(tmp)], ["none"])
            write(Path(tmp) / "usage" / "weekly-ci.json", {"schema": 1, "rows": []})
            self.assertEqual([r["key"] for r in build.ci_red_runs(tmp)], ["none"])

    def test_the_page_shows_red_in_ci_by_repo_by_week_and_lists_the_runs(self):
        page = (DASH / "page" / "index.html").read_text()
        for table in ("tbl-impact-repos", "tbl-impact-weeks"):
            head = page[page.index(f'id="{table}"'):]
            head = head[:head.index("</thead>")]
            self.assertIn('data-field="overridden">Red in CI', head)
        self.assertIn('data-source="ci_red_runs"', page)
        self.assertIn("ci_red_runs: 'key'", page)
        self.assertIn("overridden: usageSum(rs, 'overridden') }));", page)

    def test_the_page_names_no_owner(self):
        page = (DASH / "page" / "index.html").read_text()
        defined = json.loads((DASH / "page" / "datasets.json").read_text())
        words = json.dumps({k: [v.get("title"), v.get("description")] for k, v in defined.items()})
        self.assertIn("Waiting on you", page)
        for text in (page, words):
            for name in ("Waiting on Adam", "Adam's", "Adam "):
                self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
