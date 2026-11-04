"""The site freshness watcher: scripts/site_freshness.py and site-freshness.yml.

Deterministic: every time is injected, gh and curl are fakes, and workflows are
parsed with PyYAML, never a line scan. No network, no sleeps, no wall clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test"))
import site_freshness as sf  # noqa: E402
from lockfile_pins import lock_problem  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "site-freshness.yml"
NOW = datetime(2026, 11, 4, 12, 0, 0, tzinfo=timezone.utc)
SHA_A = "a" * 40
SHA_B = "b" * 40


def ago(**kw) -> datetime:
    return NOW - timedelta(**kw)


def iso(when: datetime) -> str:
    return sf.stamp(when)


class DesignTests(unittest.TestCase):
    def test_same_commit_is_fresh_even_when_old(self):
        c = sf.design_check(SHA_A, SHA_A, ago(days=3), None, NOW)
        self.assertTrue(c.ok)

    def test_site_ahead_or_identical_is_fresh(self):
        for relation in ("ahead", "identical"):
            self.assertTrue(sf.design_check(SHA_A, SHA_B, ago(days=3), relation, NOW).ok, relation)

    def test_behind_for_under_two_hours_is_fresh(self):
        c = sf.design_check(SHA_A, SHA_B, ago(hours=1, minutes=59), "behind", NOW)
        self.assertTrue(c.ok)
        self.assertIn("inside the limit", c.detail)

    def test_behind_exactly_two_hours_is_fresh_and_past_it_is_stale(self):
        self.assertTrue(sf.design_check(SHA_A, SHA_B, ago(hours=2), "behind", NOW).ok)
        c = sf.design_check(SHA_A, SHA_B, ago(hours=2, seconds=1), "behind", NOW)
        self.assertFalse(c.ok)
        self.assertIn("bbbbbbb", c.detail)

    def test_diverged_or_unknown_relation_uses_the_age_rule(self):
        for relation in ("diverged", None):
            self.assertFalse(sf.design_check(SHA_A, SHA_B, ago(hours=5), relation, NOW).ok)
            self.assertTrue(sf.design_check(SHA_A, SHA_B, ago(minutes=5), relation, NOW).ok)

    def test_unreadable_inputs_fail(self):
        self.assertFalse(sf.design_check(None, SHA_B, ago(hours=9), None, NOW).ok)
        self.assertFalse(sf.design_check(SHA_A, None, None, None, NOW).ok)

    def test_links_travel_with_the_check(self):
        c = sf.design_check(SHA_A, SHA_B, ago(hours=5), "behind", NOW, ["https://example.com/p"])
        self.assertEqual(c.links, ["https://example.com/p"])


class DataTests(unittest.TestCase):
    def test_fresh_stale_and_boundary(self):
        self.assertTrue(sf.data_check(iso(ago(hours=1)), NOW).ok)
        self.assertTrue(sf.data_check(iso(ago(hours=30)), NOW).ok)
        c = sf.data_check(iso(ago(hours=30, seconds=1)), NOW)
        self.assertFalse(c.ok)
        self.assertIn("30.0 hours", c.detail)

    def test_missing_or_garbled_generated_at_fails(self):
        for value in (None, "", "yesterday"):
            self.assertFalse(sf.data_check(value, NOW).ok, value)

    def test_offset_times_are_normalized(self):
        self.assertTrue(sf.data_check("2026-11-04T07:00:00-05:00", NOW).ok)


class PageTests(unittest.TestCase):
    def test_all_drew_passes(self):
        self.assertTrue(sf.page_check({"https://example.com/a": sf.PAGE_OK}).ok)

    def test_any_failure_fails_and_names_the_url_and_reason(self):
        c = sf.page_check({"https://example.com/a": sf.PAGE_OK,
                           "https://example.com/b": "http 404"})
        self.assertFalse(c.ok)
        self.assertIn("https://example.com/b did not draw (http 404)", c.detail)
        self.assertNotIn("example.com/a did not", c.detail)

    def test_no_result_fails(self):
        self.assertFalse(sf.page_check({}, ["https://example.com/a"]).ok)


class FixPlanTests(unittest.TestCase):
    def test_behind_pr_is_updated(self):
        plan = sf.plan_fixes(True, [{"number": 7, "state": "BEHIND"}], True)
        self.assertEqual(plan, [{"action": "update-branch", "number": 7}])

    def test_conflicted_blocked_or_clean_prs_are_left_alone(self):
        for state in ("DIRTY", "BLOCKED", "CLEAN", "UNSTABLE", "UNKNOWN", None):
            self.assertEqual(sf.plan_fixes(False, [{"number": 7, "state": state}], True), [], state)

    def test_stale_design_with_nothing_in_flight_dispatches(self):
        self.assertEqual(sf.plan_fixes(False, [], False), [{"action": "dispatch-site-sync"}])

    def test_no_dispatch_when_fresh_or_branch_exists_or_unknown(self):
        self.assertEqual(sf.plan_fixes(True, [], False), [])
        self.assertEqual(sf.plan_fixes(False, [], True), [])
        self.assertEqual(sf.plan_fixes(False, [], None), [])

    def test_no_dispatch_while_a_pr_is_open(self):
        self.assertEqual(sf.plan_fixes(False, [{"number": 7, "state": "BLOCKED"}], False), [])


def bad(name="data"):
    return [sf.Check(name, False, "stale")]


def issue(opened_ago, comments=()):
    return {"number": 9, "created_at": iso(NOW - opened_ago), "comments": list(comments)}


def comment(body, when_ago):
    return {"body": body, "created_at": iso(NOW - when_ago)}


class IssuePlanTests(unittest.TestCase):
    def test_all_fresh_without_an_issue_does_nothing(self):
        self.assertEqual(sf.plan_issue([], None, NOW, True),
                         {"action": "none", "fire": False, "config_comment": False})

    def test_all_fresh_closes_an_open_issue(self):
        self.assertEqual(sf.plan_issue([], issue(timedelta(hours=9)), NOW, True)["action"], "close")

    def test_failing_without_an_issue_creates_and_never_fires(self):
        plan = sf.plan_issue(bad(), None, NOW, True)
        self.assertEqual((plan["action"], plan["fire"]), ("create", False))

    def test_young_issue_updates_without_firing(self):
        plan = sf.plan_issue(bad(), issue(timedelta(minutes=59)), NOW, True)
        self.assertEqual((plan["action"], plan["fire"]), ("update", False))
        plan = sf.plan_issue(bad(), issue(timedelta(hours=1)), NOW, True)
        self.assertFalse(plan["fire"])

    def test_old_issue_fires(self):
        plan = sf.plan_issue(bad(), issue(timedelta(hours=1, seconds=1)), NOW, True)
        self.assertEqual((plan["action"], plan["fire"]), ("update", True))

    def test_recent_fire_marker_suppresses_a_fire(self):
        marker = sf.fire_marker(ago(hours=5), "200")
        plan = sf.plan_issue(bad(), issue(timedelta(days=1), [comment(marker, timedelta(hours=5))]),
                             NOW, True)
        self.assertFalse(plan["fire"])

    def test_old_fire_marker_allows_a_fire(self):
        marker = sf.fire_marker(ago(hours=7), "200")
        plan = sf.plan_issue(bad(), issue(timedelta(days=1), [comment(marker, timedelta(hours=6))]),
                             NOW, True)
        self.assertTrue(plan["fire"])

    def test_a_failed_fire_still_counts_as_an_attempt(self):
        marker = sf.fire_marker(ago(hours=1), "000")
        plan = sf.plan_issue(bad(), issue(timedelta(days=1), [comment(marker, timedelta(hours=1))]),
                             NOW, True)
        self.assertFalse(plan["fire"])

    def test_other_comments_are_not_fire_markers(self):
        plan = sf.plan_issue(bad(), issue(timedelta(days=1),
                                          [comment("fire it please", timedelta(minutes=1))]),
                             NOW, True)
        self.assertTrue(plan["fire"])

    def test_unconfigured_routine_comments_once(self):
        old = issue(timedelta(days=1))
        plan = sf.plan_issue(bad(), old, NOW, False)
        self.assertEqual((plan["fire"], plan["config_comment"]), (False, True))
        said = issue(timedelta(days=1), [comment(sf.CONFIG_MARKER, timedelta(hours=3))])
        plan = sf.plan_issue(bad(), said, NOW, False)
        self.assertEqual((plan["fire"], plan["config_comment"]), (False, False))


class IssueTextTests(unittest.TestCase):
    def setUp(self):
        self.failing = [sf.Check("design", False, "behind abc1234", ["https://example.com/p"]),
                        sf.Check("page", False, "did not draw", [])]

    def test_body_has_the_audit_header_lines_first(self):
        body = sf.issue_body(self.failing, ["dispatch site-sync.yml: requested"], NOW,
                             "https://example.com/run/1")
        lines = body.splitlines()
        self.assertEqual(lines[:4], ["Kind: broken", "Severity: high",
                                     "Finding-ID: skills-evals/site-freshness", sf.ISSUE_MARKER])
        self.assertIn("- **design**: behind abc1234 (<https://example.com/p>)", lines)
        self.assertIn("- dispatch site-sync.yml: requested", lines)
        self.assertIn("Workflow run: https://example.com/run/1", lines)

    def test_fire_text_names_the_issue_and_is_bounded(self):
        text = sf.fire_text("https://example.com/issues/9", self.failing)
        self.assertTrue(text.startswith("Site freshness issue: https://example.com/issues/9"))
        self.assertIn("- design: behind abc1234", text)
        huge = [sf.Check("data", False, "x" * 100_000)]
        self.assertLessEqual(len(sf.fire_text("https://example.com/issues/9", huge)), 65_536)

    def test_fire_marker_records_only_time_and_status(self):
        self.assertEqual(sf.fire_marker(NOW, "200"),
                         "<!-- skills-evals:site-freshness-fire at=2026-11-04T12:00:00Z status=200 -->")


class FakeGh:
    def __init__(self, fail=()):
        self.calls = []
        self.fail = set(fail)

    def __call__(self, args, token=None):
        self.calls.append(args)
        if args[:2] in [list(f) for f in self.fail]:
            raise sf.GhError(args, 1)
        return "https://github.com/Adam-S-Daniel/skills-evals/issues/42\n"


class ApplyTests(unittest.TestCase):
    def apply(self, plan, issue_row=None, gh=None):
        gh = gh or FakeGh()
        url = sf.apply_issue_plan(gh, plan, bad(), [], issue_row, NOW, None)
        return gh, url

    def test_create_makes_the_label_then_the_issue(self):
        gh, url = self.apply({"action": "create", "fire": False, "config_comment": False})
        self.assertEqual([c[:2] for c in gh.calls], [["label", "create"], ["issue", "create"]])
        create = gh.calls[1]
        self.assertEqual(create[create.index("--title") + 1], sf.ISSUE_TITLE)
        self.assertEqual(create[create.index("--label") + 1], "half-built-or-broken")
        self.assertTrue(url.endswith("/issues/42"))

    def test_an_existing_label_does_not_stop_the_create(self):
        gh, url = self.apply({"action": "create", "fire": False, "config_comment": False},
                             gh=FakeGh(fail=[("label", "create")]))
        self.assertEqual(gh.calls[-1][:2], ["issue", "create"])
        self.assertIsNotNone(url)

    def test_update_edits_the_body(self):
        gh, url = self.apply({"action": "update", "fire": False, "config_comment": False},
                             {"number": 9})
        self.assertEqual(gh.calls[0][:3], ["issue", "edit", "9"])
        self.assertTrue(url.endswith("/issues/9"))

    def test_close_comments_and_closes_with_the_marker(self):
        gh, _ = self.apply({"action": "close", "fire": False, "config_comment": False}, {"number": 9})
        close = gh.calls[0]
        self.assertEqual(close[:3], ["issue", "close", "9"])
        self.assertIn("on behalf of @Adam-S-Daniel", close[close.index("--comment") + 1])

    def test_config_comment_carries_its_marker(self):
        gh, _ = self.apply({"action": "update", "fire": False, "config_comment": True}, {"number": 9})
        comment_call = gh.calls[-1]
        self.assertEqual(comment_call[:3], ["issue", "comment", "9"])
        self.assertIn(sf.CONFIG_MARKER, comment_call[comment_call.index("--body") + 1])


class ParseTests(unittest.TestCase):
    def test_provenance_commit(self):
        text = f"repo: Adam-S-Daniel/skills-evals\nref: main\ncommit: {SHA_A}\nsource_committed_at: x\n"
        self.assertEqual(sf.provenance_commit(text), SHA_A)
        self.assertIsNone(sf.provenance_commit("commit: short\n"))
        self.assertIsNone(sf.provenance_commit(None))

    def test_generated_at(self):
        self.assertEqual(sf.generated_at('{"generated_at": "2026-11-04T00:00:00Z"}'),
                         "2026-11-04T00:00:00Z")
        for text in (None, "not json", "[]", '{"generated_at": 5}', "{}"):
            self.assertIsNone(sf.generated_at(text), text)

    def test_newest_page_commit_reads_the_committer_time(self):
        rows = [{"sha": SHA_B, "commit": {"committer": {"date": "2026-11-04T10:00:00Z"}}}]
        with mock.patch.object(sf, "gh", return_value=json.dumps(rows)):
            sha, when = sf.newest_page_commit(None)
        self.assertEqual((sha, when), (SHA_B, datetime(2026, 11, 4, 10, tzinfo=timezone.utc)))
        with mock.patch.object(sf, "gh", return_value="[]"):
            self.assertEqual(sf.newest_page_commit(None), (None, None))

    def test_a_missing_branch_is_distinguished_from_an_unreadable_one(self):
        def raising(missing):
            def fake(args, token=None):
                if "pulls?" in args[1]:
                    return "[]"
                raise sf.GhError(args, 1, missing=missing)
            return fake
        with mock.patch.object(sf, "gh", raising(True)):
            self.assertEqual(sf.sync_state("example/site", None), ([], False))
        with mock.patch.object(sf, "gh", raising(False)):
            self.assertEqual(sf.sync_state("example/site", None), ([], None))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.steps = [s for j in self.doc["jobs"].values() for s in j["steps"]]

    def test_triggers(self):
        on = self.doc.get("on", self.doc.get(True))
        self.assertEqual(set(on), {"schedule", "workflow_run", "workflow_dispatch"})
        self.assertEqual(on["workflow_run"], {"workflows": ["Site sync"], "types": ["completed"]})
        cron = on["schedule"][0]["cron"]
        minute, rest = cron.split(" ", 1)
        self.assertEqual(rest, "* * * *")
        self.assertEqual(int(minute) % 2, 1, "an odd minute, off the hour")

    def test_site_sync_is_named_by_the_workflow_it_watches(self):
        name = yaml.safe_load((ROOT / ".github/workflows/site-sync.yml").read_text())["name"]
        self.assertEqual(name, "Site sync")

    def test_permissions_are_minimal(self):
        self.assertEqual(self.doc["permissions"],
                         {"contents": "read", "issues": "write", "actions": "write"})
        for job in self.doc["jobs"].values():
            self.assertNotIn("permissions", job)

    def test_concurrency_never_cancels_a_running_issue_write(self):
        self.assertIs(self.doc["concurrency"]["cancel-in-progress"], False)

    def test_bearer_reaches_only_the_fire_step_via_env(self):
        holders = [s for s in self.steps if "SITE_FRESHNESS_FIRE_BEARER" in json.dumps(s)]
        self.assertEqual(len(holders), 2, "the presence check and the fire step")
        fire = [s for s in self.steps if s.get("name") == "Fire the Sonnet routine"][0]
        self.assertEqual(fire["env"]["FIRE_BEARER"], "${{ secrets.SITE_FRESHNESS_FIRE_BEARER }}")
        self.assertEqual(fire["env"]["ROUTINE_ID"], "${{ vars.SITE_FRESHNESS_ROUTINE_ID || 'trig_01Nu9F7UQ8aUWq4q2QsXHQhK' }}")
        for step in holders:
            self.assertNotIn("secrets.SITE_FRESHNESS_FIRE_BEARER", step.get("run", ""))
            self.assertNotIn("secrets.SITE_FRESHNESS_FIRE_BEARER", json.dumps(step.get("with", {})))
        # Not in workflow- or job-level env either.
        self.assertNotIn("SITE_FRESHNESS_FIRE_BEARER", json.dumps(self.doc.get("env", {})))
        self.assertNotIn("SITE_FRESHNESS_FIRE_BEARER", json.dumps(
            {k: v for j in self.doc["jobs"].values() for k, v in j.items() if k != "steps"}))

    def test_presence_check_passes_a_boolean_only(self):
        check = [s for s in self.steps if s.get("id") == "credential"][0]
        self.assertIn("!= ''", check["env"]["HAVE_ROUTINE"])
        self.assertNotIn("FIRE_BEARER", check["run"])

    def test_no_expression_inside_run_blocks(self):
        for step in self.steps:
            self.assertNotIn("${{", step.get("run", ""), step.get("name"))

    def test_app_token_mint_is_soft_and_scoped(self):
        mint = [s for s in self.steps if s.get("id") == "mint"][0]
        self.assertIs(mint["continue-on-error"], True)
        self.assertEqual(mint["with"]["repositories"], "adamdaniel.ai")
        self.assertEqual(mint["with"]["owner"], "Adam-S-Daniel")

    def test_site_repo_none_skips_every_step_after_the_decision(self):
        self.assertEqual(self.doc["env"]["SITE_REPO"],
                         "${{ vars.SITE_REPO || 'Adam-S-Daniel/adamdaniel.ai' }}")
        decide = [s for s in self.steps if s.get("id") == "site"][0]
        self.assertIn('[ "$SITE_REPO" = none ]', decide["run"])
        for step in self.steps:
            if step is not decide:
                self.assertIn("steps.site.outputs.skip != 'true'", step["if"], step.get("name"))

    def test_fire_only_when_the_issue_step_asked(self):
        fire = [s for s in self.steps if s.get("name") == "Fire the Sonnet routine"][0]
        self.assertIn("steps.issue.outputs.fire == 'true'", fire["if"])
        self.assertEqual(self.steps[-1], fire)

    def test_every_uses_is_locked(self):
        for step in self.steps:
            if "uses" in step:
                self.assertIsNone(lock_problem(step["uses"], WORKFLOW), step["uses"])

    def test_checkout_does_not_persist_credentials(self):
        checkout = [s for s in self.steps if str(s.get("uses", "")).startswith("actions/checkout@")]
        self.assertEqual(len(checkout), 1)
        self.assertIs(checkout[0]["with"]["persist-credentials"], False)

    def test_playwright_is_pinned_exactly(self):
        install = [s for s in self.steps if s.get("name") == "Install Playwright and Chromium"][0]
        self.assertRegex(install["run"], r"playwright==\d+\.\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
