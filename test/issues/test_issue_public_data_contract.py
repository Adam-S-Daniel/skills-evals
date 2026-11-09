#!/usr/bin/env python3
"""explorer/latest.json as the single public data contract (schema_version 1:
the new sections only add fields, so the live page keeps reading it).

scripts/explorer_public.py builds the new sections (`evals`, `hooks`,
`lesson_funnel`, `activity`, `spend`) from public inputs only, and
scripts/explorer_data.py `finish` and `validate` (explorer/schema.json) are
the last gates. These tests pin each section, the privacy folding of
non-public repositories, the spend flag both ways, the schema and every new
refusal, plus the workflow steps that feed them.

Hermetic: invented data (example-owner style names, fictional repositories
under the fleet owners' names, example.com), no network, no clock.
"""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))

import eval_facts  # noqa: E402
import explorer_data  # noqa: E402
import explorer_public as pub  # noqa: E402
from test_issue_72_explorer_data import AS_OF, SHA_A, SHA_B, Tree  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "explorer-data.yml"
NOW = datetime(2026, 10, 31, 21, 0, tzinfo=timezone.utc)
PUBLIC = frozenset({"Adam-S-Daniel/open-one", "Adam-S-Daniel/open-two", "jodidaniel/open-three",
                    "Adam-S-Daniel/skills-evals"})
POLICY = dict(pub.HOOK_POLICY_DEFAULTS)

_spec = importlib.util.spec_from_file_location("dashboard_build_contract", ROOT / "dashboard" / "build.py")
dashboard_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dashboard_build)


def write(path: Path, doc) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
    return path


def summary(arm, passed, total, model="model-a", **extra):
    return {"arm": arm, "n": 3, "cross_model": {"model": model},
            "aggregate": {"objective": {"mean_passed": passed, "mean_total": total},
                          "cost_usd": {"sum": 0.5}},
            "harness": {"version": "2.1.300 (Claude Code)"},
            "usage": {"meter_delta": {"windows": {"seven_day": {"delta": 0.01, "to": 0.4}}}},
            **extra}


def routine_pair(tree: Path, run: str, skill: str, with_passed, without_passed, total=4,
                 model="model-a"):
    base = tree / "routine-results" / run / skill / "20261030T100000Z"
    write(base / "report.md", "report\n")
    write(base / "with_skill" / "summary.json", summary("with_skill", with_passed, total, model))
    write(base / "without_skill" / "summary.json", summary("without_skill", without_passed, total, model))


def routine_bare(tree: Path, run: str, skill: str, passed, total=4):
    base = tree / "routine-results" / run / skill / "20261030T110000Z"
    write(base / "report.md", "report\n")
    write(base / "without_skill" / "summary.json", summary("without_skill", passed, total))


def hook_row(week, name, repo, invocations, blocked, overridden=None, surface="local"):
    return {"week": week, "kind": "hook", "name": name, "repo": repo, "surface": surface,
            "invocations": invocations, "sessions": None, "blocked": blocked,
            "overridden": overridden, "outcome": None, "runner": None}


def usage_file(rows, generated="2026-10-31T12:00:00Z"):
    return {"schema": 1, "generated_at": generated, "sources": [], "rows": rows}


RUNNER = """#!/usr/bin/env bash
note_ran() { :; }
problem() { local id=$1; note_ran "$id"; }
lesson_checks="lesson-alpha lesson-beta"
check_paths() {
  note_ran rules-dir
  note_ran secret-file
  problem runner-error "not a check"
}
run_local() { note_ran repo-local; }
for id in $lesson_checks; do note_ran "$id"; done
"""


class EvalFactsTests(unittest.TestCase):
    """The page's calcs, ported: same numbers, nothing rounded."""

    ROWS = [
        {"skill": "alpha", "fixture": "alpha", "model": "m1", "gain": 1, "with_share": 0.75,
         "without_share": 0.5, "fired_at": "2026-10-30T10:00:00Z", "run_id": "r2",
         "with_skill": 3, "without_skill": 2, "checks": 4},
        {"skill": "alpha", "fixture": "alpha", "model": "m1", "gain": -1, "with_share": 0.25,
         "without_share": 0.5, "fired_at": "2026-10-29T10:00:00Z", "run_id": "r1",
         "with_skill": 1, "without_skill": 2, "checks": 4},
        {"skill": "beta", "fixture": "beta/fx", "model": "m2", "gain": 0, "with_share": None,
         "without_share": None, "fired_at": "2026-10-28T10:00:00Z", "run_id": "r0",
         "with_skill": 0, "without_skill": 0, "checks": 0},
        {"skill": "guidance/sec-one", "fixture": "guidance/sec-one/fx", "model": "m1", "gain": 2,
         "with_share": 1.0, "without_share": 0.5, "fired_at": "2026-10-30T11:00:00Z",
         "run_id": "r3", "with_skill": 4, "without_skill": 2, "checks": 4}]

    def test_skill_vs_no_skill_leaves_guidance_out_and_adds_a_null_share_as_zero(self):
        out = eval_facts.skill_vs_no_skill(self.ROWS)
        self.assertEqual([r["model"] for r in out], ["All", "m1", "m2"])
        every = out[0]
        self.assertEqual((every["runs"], every["helped"], every["tied"], every["hurt"]), (3, 1, 1, 1))
        self.assertEqual(every["with_avg"], (0.75 + 0.25 + 0) / 3)
        self.assertEqual(every["lift"], ((0.75 + 0.25) - (0.5 + 0.5)) / 3)

    def test_latest_summary_counts_each_test_once(self):
        self.assertEqual(eval_facts.latest_summary(self.ROWS),
                         {"tests": 2, "helped": 1, "tied": 1, "hurt": 0})

    def test_latest_per_test_keeps_the_newest_run_including_guidance(self):
        out = eval_facts.latest_per_test(self.ROWS)
        self.assertEqual(sorted(r["run_id"] for r in out), ["r0", "r2", "r3"])
        self.assertEqual(set(out[0]), set(eval_facts.LATEST_KEYS))

    def test_bare_summary(self):
        bare = [{"model": "m1", "bare_share": 0.9, "with_share": 0.8, "without_share": 0.5},
                {"model": "m1", "bare_share": 0.4, "with_share": 0.8, "without_share": 0.6},
                {"model": "m1", "bare_share": 0.4, "with_share": None, "without_share": 0.6}]
        out = eval_facts.bare_summary(bare)
        self.assertEqual(out[0], {"model": "All", "pairs": 2, "bare": 0.65, "without": 0.55,
                                  "with": 0.8, "setup_lift": (1.1 - 1.3) / 2,
                                  "skill_lift": (1.6 - 1.1) / 2, "bare_won": 1})

    def test_the_dashboard_builds_its_runs_from_the_shared_module(self):
        t = Tree(self)
        routine_pair(t.tree, "20261030T100000Z-aaaaaa", "alpha", 3, 2)
        routine_bare(t.tree, "20261030T110000Z-bbbbbb", "alpha", 1)
        write(t.tree / "routine-results" / "not-a-run" / "x" / "report.md", "x\n")
        shared = eval_facts.scored_runs(str(t.tree), "https://example.com/r/")
        self.assertEqual(dashboard_build.eval_rows(str(t.tree), "https://example.com/r/"), shared)
        self.assertIs(dashboard_build.scored_runs, eval_facts.scored_runs)
        self.assertEqual(len(shared[0]), 1)
        self.assertEqual(len(shared[1]), 1)


class EvalsSectionTests(unittest.TestCase):

    def setUp(self):
        self.t = Tree(self)  # census: alpha, beta, gamma are public
        routine_pair(self.t.tree, "20261030T100000Z-aaaaaa", "alpha", 3, 2)
        routine_pair(self.t.tree, "20261030T120000Z-cccccc", "secret-skill", 4, 0)
        routine_bare(self.t.tree, "20261030T110000Z-bbbbbb", "alpha", 1)
        routine_bare(self.t.tree, "20261030T130000Z-dddddd", "secret-skill", 4)

    def test_only_listed_subjects_reach_the_rows_and_the_summaries(self):
        evals = self.t.build()["evals"]
        self.assertEqual([r["skill"] for r in evals["runs"]], ["alpha"])
        self.assertEqual([r["skill"] for r in evals["bare_runs"]], ["alpha"])
        self.assertEqual(evals["summary"][0]["runs"], 1)
        self.assertEqual(evals["latest_summary"], {"tests": 1, "helped": 1, "tied": 0, "hurt": 0})
        self.assertNotIn("secret-skill", json.dumps(evals))
        self.assertEqual(set(evals["runs"][0]), set(pub.RUN_KEYS))
        self.assertTrue(evals["runs"][0]["report_url"].startswith(
            "https://github.com/Adam-S-Daniel/skills-evals/blob/persistent/eval-results/"
            "routine-results/"))

    def test_the_meter_readings_follow_the_spend_flag(self):
        on = explorer_data.build(self.t.tree, self.t.roster, self.t.policy, self.t.evals, AS_OF,
                                 SHA_A, SHA_B, spend=True)["evals"]["runs"][0]
        off = self.t.build()["evals"]["runs"][0]
        self.assertEqual((on["meter_points"], on["account_week_after"]), (1.0, 40.0))
        self.assertEqual((off["meter_points"], off["account_week_after"]), (None, None))
        self.assertEqual(off["cost_usd"], on["cost_usd"])


class HookCatalogTests(unittest.TestCase):

    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_the_catalog_is_parsed_from_the_runner_not_scanned(self):
        write(self.root / "agent-checks" / "agent-checks", RUNNER)
        names = [c["name"] for c in pub.fleet_checks(self.root / "agent-checks")]
        # Literal note_ran ids and the lesson list; `$id` expansions, the
        # runner's own error ids and repo-local (listed per repository) are not.
        self.assertEqual(names, ["lesson-alpha", "lesson-beta", "rules-dir", "secret-file"])
        entry = pub.fleet_checks(self.root / "agent-checks")[0]
        self.assertEqual(entry, {"name": "lesson-alpha", "where": "fleet", "repo": None,
                                 "source_url": pub.RUNNER_URL})

    def test_a_comment_or_string_naming_note_ran_is_not_a_check(self):
        write(self.root / "c" / "agent-checks",
              '# note_ran fake-one\necho "note_ran fake-two"\nnote_ran real-one\n')
        self.assertEqual([c["name"] for c in pub.fleet_checks(self.root / "c")], ["real-one"])

    def test_no_runner_or_bad_bash_is_unknown(self):
        self.assertIsNone(pub.fleet_checks(None))
        self.assertIsNone(pub.fleet_checks(self.root / "missing"))
        write(self.root / "bad" / "agent-checks", "if then fi (\n")
        self.assertIsNone(pub.fleet_checks(self.root / "bad"))

    def test_repo_checks_need_a_public_repository_and_a_local_file(self):
        write(self.root / "one" / ".agent-checks" / "local.sh", "true\n")
        write(self.root / "hidden" / ".agent-checks" / "local.sh", "true\n")
        (self.root / "two").mkdir()
        repos = {"Adam-S-Daniel/open-one": self.root / "one",
                 "Adam-S-Daniel/open-two": self.root / "two",
                 "Adam-S-Daniel/hidden-repo": self.root / "hidden"}
        self.assertEqual(pub.repo_checks(repos, PUBLIC), [{
            "name": "repo-local", "where": "repo", "repo": "Adam-S-Daniel/open-one",
            "source_url": "https://github.com/Adam-S-Daniel/open-one/blob/HEAD/.agent-checks/local.sh"}])
        self.assertEqual(pub.repo_checks(repos, None), [])


class HookUseTests(unittest.TestCase):

    def setUp(self):
        self.t = Tree(self)
        write(self.t.root / "ac" / "agent-checks", RUNNER)

    def hooks(self, local_rows, ci_rows=(), public=PUBLIC, policy=None):
        write(self.t.tree / "usage" / "weekly-local.json", usage_file(list(local_rows)))
        write(self.t.tree / "usage" / "weekly-ci.json", usage_file(list(ci_rows)))
        return pub.build_hooks(self.t.tree, NOW, self.t.root / "ac", {}, public,
                               policy or POLICY)

    def check(self, hooks, name, repo=None):
        return next(c for c in hooks["checks"] if c["name"] == name and c["repo"] == repo)

    def test_use_is_summed_per_week_surface_and_repository(self):
        h = self.hooks([hook_row("2026-10-26", "rules-dir", "Adam-S-Daniel/open-one", 5, 1),
                        hook_row("2026-10-26", "rules-dir", "Adam-S-Daniel/open-one", 2, 0),
                        hook_row("2026-10-26", "all", None, 9, 1)],
                       [hook_row("2026-10-26", "agent-checks", "Adam-S-Daniel/open-two", 4, 1, 1,
                                 surface="ci")])
        self.assertEqual(self.check(h, "rules-dir")["use"], [
            {"week": "2026-10-26", "surface": "local", "repo": "Adam-S-Daniel/open-one",
             "invocations": 7, "blocked": 1, "overridden": None}])
        self.assertEqual(h["totals"]["local"][0]["invocations"], 9)
        self.assertEqual(h["totals"]["ci"][0]["repo"], "Adam-S-Daniel/open-two")
        self.assertEqual(h["unlisted"], 0)

    def test_non_public_repositories_fold_into_one_bucket_hidden_below_three(self):
        rows = [hook_row("2026-10-26", "rules-dir", "Adam-S-Daniel/hidden-a", 1, 0),
                hook_row("2026-10-26", "rules-dir", "jodidaniel/hidden-b", 1, 0),
                hook_row("2026-10-26", "rules-dir", "other", 1, 0),
                hook_row("2026-10-26", "repo-local", "Adam-S-Daniel/hidden-a", 1, 0)]
        h = self.hooks(rows)
        self.assertFalse(h["private_repos_shown"])
        self.assertEqual(self.check(h, "rules-dir")["use"], [])
        self.assertNotIn(("repo-local", pub.PRIVATE_BUCKET),
                         {(c["name"], c["repo"]) for c in h["checks"]})
        self.assertNotIn("hidden", json.dumps(h))
        # A third distinct named non-public repository shows the bucket; the
        # producers' own `other` fold never counts toward it.
        h = self.hooks(rows + [hook_row("2026-10-26", "rules-dir", "Adam-S-Daniel/hidden-c", 1, 0)])
        self.assertTrue(h["private_repos_shown"])
        self.assertEqual(self.check(h, "rules-dir")["use"][0],
                         {"week": "2026-10-26", "surface": "local", "repo": pub.PRIVATE_BUCKET,
                          "invocations": 4, "blocked": 0, "overridden": None})
        self.assertIn(("repo-local", pub.PRIVATE_BUCKET), {(c["name"], c["repo"]) for c in h["checks"]})
        self.assertNotIn("hidden", json.dumps(h))

    def test_without_a_visibility_list_no_repository_is_named(self):
        h = self.hooks([hook_row("2026-10-26", "rules-dir", "Adam-S-Daniel/open-one", 1, 0)],
                       public=None)
        self.assertNotIn("open-one", json.dumps(h))

    def test_verdicts_follow_the_policy(self):
        # Measured overrides (a local row that counts them).
        local = [hook_row("2026-10-26", "secret-file", "Adam-S-Daniel/open-one", 10, 10, 1),
                 hook_row("2026-10-26", "lesson-alpha", "Adam-S-Daniel/open-one", 10, 4, 2),
                 # Blocks with no override count anywhere.
                 hook_row("2026-10-26", "lesson-beta", None, 10, 3),
                 # Outside the 8-week window: its block does not count.
                 hook_row("2026-08-24", "rules-dir", None, 10, 9, 0)]
        h = self.hooks(local)
        secret = self.check(h, "secret-file")
        self.assertEqual((secret["verdict"], secret["overrides_measured"]), ("earning", True))
        self.assertEqual(secret["window_totals"]["override_rate"], 0.1)
        self.assertEqual(self.check(h, "lesson-alpha")["verdict"], "overridden-often")
        beta = self.check(h, "lesson-beta")
        self.assertEqual((beta["verdict"], beta["overrides_measured"]), ("earning", False))
        self.assertEqual(beta["verdict_reason"], "blocked in 8 weeks; no source counts its overrides")
        self.assertIsNone(beta["window_totals"]["override_rate"])
        self.assertEqual(self.check(h, "rules-dir")["verdict"], "never-ran")
        self.assertEqual(h["window"], {"weeks": 8, "from": "2026-09-07", "to": "2026-10-31"})
        stricter = self.hooks(local, policy={**POLICY, "max_override_rate": 0.05})
        self.assertEqual(self.check(stricter, "secret-file")["verdict"], "overridden-often")

    def test_the_ci_files_overridden_is_not_an_override_count(self):
        # The CI file repeats `blocked` as `overridden`; read as a rate it would
        # call every blocking check overridden-often.
        ci = [hook_row("2026-10-26", "secret-file", "Adam-S-Daniel/open-one", 0, 4, 4, "ci"),
              hook_row("2026-10-26", "agent-checks", "Adam-S-Daniel/open-one", 9, 3, 3, "ci")]
        h = self.hooks([], ci)
        secret = self.check(h, "secret-file")
        self.assertEqual((secret["verdict"], secret["overrides_measured"]), ("earning", False))
        self.assertIsNone(secret["use"][0]["overridden"])
        # The per-check CI row says which check refused, not how often it
        # ran: published as unknown, never as a count below the blocks.
        self.assertIsNone(secret["use"][0]["invocations"])
        self.assertIsNone(secret["window_totals"]["invocations"])
        self.assertEqual(secret["window_totals"]["blocked"], 4)
        self.assertEqual(h["totals"]["ci"], [
            {"week": "2026-10-26", "surface": "ci", "repo": "Adam-S-Daniel/open-one",
             "invocations": 9, "blocked": 3, "overridden": None}])

    def test_a_zero_or_null_per_check_ci_count_is_unknown_not_zero(self):
        # What the CI producer writes today (0) and what it may write (null).
        for runs in (0, None):
            h = self.hooks([], [hook_row("2026-10-26", "secret-file", "Adam-S-Daniel/open-one",
                                         runs, 4, 4, "ci")])
            secret = self.check(h, "secret-file")
            self.assertIsNone(secret["use"][0]["invocations"])
            self.assertIsNone(secret["window_totals"]["invocations"])
            self.assertEqual(secret["verdict"], "earning")

    def test_a_local_row_beside_unknown_ci_runs_keeps_its_own_count(self):
        h = self.hooks([hook_row("2026-10-26", "secret-file", None, 30, 0)],
                       [hook_row("2026-10-26", "secret-file", "Adam-S-Daniel/open-one", 0, 4, 4, "ci")])
        totals = self.check(h, "secret-file")["window_totals"]
        self.assertEqual((totals["invocations"], totals["invocations_counted"]), (None, 30))

    def test_a_check_that_ran_and_never_blocked_says_how_often(self):
        h = self.hooks([hook_row("2026-10-26", "rules-dir", None, 33, 0),
                        hook_row("2026-10-19", "rules-dir", None, 7, 0)])
        c = self.check(h, "rules-dir")
        self.assertEqual((c["verdict"], c["verdict_reason"]),
                         ("never-blocked", "ran 40 times in 8 weeks, blocked none"))
        self.assertEqual(c["window_totals"]["invocations"], 40)
        one = self.hooks([hook_row("2026-10-26", "rules-dir", None, 1, 0)])
        self.assertEqual(self.check(one, "rules-dir")["verdict_reason"],
                         "ran 1 time in 8 weeks, blocked none")

    def test_a_check_with_no_counted_runs_and_no_block_never_ran(self):
        h = self.hooks([hook_row("2026-10-26", "secret-file", None, 5, 1)])
        c = self.check(h, "rules-dir")
        self.assertEqual(c["verdict"], "never-ran")
        self.assertIn("no recorded runs in 8 weeks", c["verdict_reason"])

    def test_uncounted_runs_with_no_block_say_so(self):
        h = self.hooks([], [hook_row("2026-10-26", "rules-dir", "Adam-S-Daniel/open-one", None, 0, 0, "ci")])
        c = self.check(h, "rules-dir")
        self.assertEqual((c["verdict"], c["verdict_reason"]),
                         ("never-blocked", "runs not counted; no block in 8 weeks"))

    def test_no_usage_file_is_unknown_and_an_unknown_name_is_only_counted(self):
        h = pub.build_hooks(self.t.tree, NOW, self.t.root / "ac", {}, PUBLIC, POLICY)
        self.assertIsNone(self.check(h, "rules-dir")["use"])
        self.assertIsNone(h["totals"])
        h = self.hooks([hook_row("2026-10-26", "mystery-check", None, 1, 1)])
        self.assertEqual(h["unlisted"], 1)
        self.assertNotIn("mystery", json.dumps(h))
        self.assertIsNone(pub.build_hooks(self.t.tree / "none", NOW, None, {}, PUBLIC, POLICY))

    def test_the_policy_file_is_held_to_its_keys_and_types(self):
        committed = pub.load_policy(ROOT / "evals" / "hook-policy.yml", pub.HOOK_POLICY_DEFAULTS)
        self.assertEqual(committed, {"window_weeks": 8, "max_override_rate": 0.2,
                                     "min_private_repos": 3})
        for text in ("surprise: 1\n", "window_weeks: eight\n", "max_override_rate: true\n"):
            path = write(self.t.root / "p.yml", text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                pub.load_policy(path, pub.HOOK_POLICY_DEFAULTS)


class LessonFunnelTests(unittest.TestCase):

    def setUp(self):
        self.t = Tree(self)
        self.funnel = write(self.t.root / "funnel.json", {
            "hook_proposals": [
                {"number": 1, "state": "closed", "state_reason": "completed",
                 "labels": [{"name": "hook-proposal"}]},
                {"number": 2, "state": "closed", "state_reason": "not_planned",
                 "labels": [{"name": "hook-proposal"}]},
                {"number": 3, "state": "open", "labels": [{"name": "hook-proposal"}]},
                {"number": 4, "state": "closed", "state_reason": "completed", "labels": []},
                {"number": 5, "state": "closed", "labels": [{"name": "hook-proposal"}],
                 "pull_request": True}],
            "lesson_check_prs": [
                {"head": "agent/lesson-check-one", "number": 10, "state": "closed", "merged": True},
                {"head": "agent/lesson-check-two", "number": 11, "state": "closed", "merged": False},
                {"head": "feature/other", "number": 12, "state": "closed", "merged": True}]})
        self.issues = write(self.t.root / "issues.json", {
            "memory": [
                {"repo": "Adam-S-Daniel/open-one", "number": 20, "state": "closed",
                 "state_reason": "completed", "created_at": "2026-10-20T10:00:00Z",
                 "title": "Memory promotion 2026-10-20: 3 facts for AGENTS.md", "private": False},
                {"repo": "Adam-S-Daniel/open-one", "number": 21, "state": "closed",
                 "state_reason": "completed", "created_at": "2026-10-21T10:00:00Z",
                 "title": "Memory promotion 2026-10-21: 1 agent-checks", "private": False},
                {"repo": "Adam-S-Daniel/hidden-a", "number": 22, "state": "closed",
                 "state_reason": "completed", "created_at": "2026-10-21T10:00:00Z",
                 "title": "Memory promotion 2026-10-21: 2 facts for AGENTS.md", "private": True}],
            "proposals": [self.proposal(30, "tool-alpha", "closed", "completed"),
                          self.proposal(31, "tool-beta", "closed", "not_planned"),
                          self.proposal(32, "tool-gamma", "closed", None)]})
        self.drafts = {"tool-alpha": {"number": 40, "state": "merged", "url": "x"},
                       "tool-delta": {"number": 41, "state": "open", "url": "y"}}

    @staticmethod
    def proposal(number, name, state, reason):
        return {"number": number, "state": state, "state_reason": reason,
                "created_at": "2026-10-22T10:00:00Z", "author_association": "OWNER",
                "user": {"login": "Adam-S-Daniel"}, "labels": [{"name": "skill-proposal"}],
                "body": f"Skill name: `{name}`\n"}

    def build(self, funnel=True, issues=True, drafts=True):
        return pub.build_lesson_funnel(self.funnel if funnel else None,
                                       self.issues if issues else None,
                                       self.drafts if drafts else None,
                                       explorer_data.memory_issue, explorer_data.proposal_issue)

    def test_each_source_counts_by_its_outcome(self):
        f = self.build()
        by = f["by_source"]
        self.assertEqual({k: v for k, v in by["hook-proposal"].items() if v},
                         {"check": 1, "nothing": 1, "open": 1})
        self.assertEqual({k: v for k, v in by["lesson-check"].items() if v}, {"check": 1, "nothing": 1})
        # The private repository's memory issue is not counted.
        self.assertEqual({k: v for k, v in by["memory"].items() if v}, {"guidance": 1, "check": 1})
        self.assertEqual({k: v for k, v in by["draft-skill"].items() if v}, {"skill": 1, "open": 1})
        # tool-alpha is counted once, by its draft; a reasonless close is unknown.
        self.assertEqual({k: v for k, v in by["skill-proposal"].items() if v},
                         {"nothing": 1, "unknown": 1})
        self.assertEqual((f["check"], f["skill"], f["guidance"], f["nothing"], f["open"], f["unknown"]),
                         (3, 1, 1, 3, 2, 1))
        self.assertEqual(f["sources_missing"], [])

    def test_a_missing_source_is_named_and_none_at_all_is_unknown(self):
        self.assertEqual(self.build(funnel=False)["sources_missing"], ["hook-proposal", "lesson-check"])
        self.assertIsNone(self.build(funnel=False, issues=False, drafts=False))


class ActivityTests(unittest.TestCase):

    def setUp(self):
        self.t = Tree(self)

    def activity(self, doc, public=PUBLIC):
        path = write(self.t.root / "activity.json", doc)
        return pub.build_activity(path, public, NOW, NOW)

    @staticmethod
    def doc(**extra):
        return {"fetched_at": "2026-10-31T20:00:00Z",
                "pulls": [{"repo": "Adam-S-Daniel/open-one", "number": 7, "title": "Fix @someone's bug",
                           "state": "closed", "created_at": "2026-10-25T10:00:00Z",
                           "updated_at": "2026-10-26T10:00:00Z", "closed_at": "2026-10-26T10:00:00Z",
                           "merged_at": "2026-10-26T10:00:00Z", "body": "never published"},
                          {"repo": "Adam-S-Daniel/open-one", "number": 8, "title": "Old merge",
                           "state": "closed", "merged_at": "2026-10-01T10:00:00Z"},
                          {"repo": "Adam-S-Daniel/open-one", "number": 9, "title": "Closed unmerged",
                           "state": "closed", "merged_at": None},
                          {"repo": "jodidaniel/open-three", "number": 3,
                           "title": "See cmsg_01AbCdEfGh for context", "state": "open"},
                          {"repo": "Adam-S-Daniel/hidden-a", "number": 1, "title": "Hidden work",
                           "state": "open"}],
                "issues": [{"repo": "Adam-S-Daniel/open-two", "number": 4, "title": "Open issue",
                            "state": "open", "created_at": "2026-09-01T10:00:00Z"},
                           {"repo": "Adam-S-Daniel/hidden-a", "number": 2, "title": "Hidden issue",
                            "state": "open"}],
                "runs": [{"repo": "Adam-S-Daniel/open-two", "id": 1234, "workflow": "CI",
                          "title": "Merge pull request #4", "event": "push", "status": "completed",
                          "conclusion": "success", "created_at": "2026-10-30T10:00:00Z",
                          "updated_at": "2026-10-30T10:05:00Z"},
                         {"repo": "Adam-S-Daniel/open-two", "id": 1233, "workflow": "CI",
                          "title": "old", "status": "completed", "conclusion": "success",
                          "created_at": "2026-10-10T10:00:00Z"},
                         {"repo": "Adam-S-Daniel/skills-evals", "id": 1235,
                          "path": ".github/workflows/explorer-data.yml",
                          "workflow": "Publish explorer data", "title": "Publish explorer data",
                          "status": "completed", "conclusion": "success",
                          "created_at": "2026-10-30T11:00:00Z"},
                         {"repo": "Adam-S-Daniel/skills-evals", "id": 1236,
                          "path": ".github/workflows/ci.yml", "workflow": "CI", "title": "CI",
                          "status": "completed", "conclusion": "success",
                          "created_at": "2026-10-30T09:00:00Z"},
                         {"repo": "Adam-S-Daniel/hidden-a", "id": 99, "workflow": "CI",
                          "title": "Hidden run", "status": "completed",
                          "created_at": "2026-10-30T10:00:00Z"}], **extra}

    def test_only_public_repositories_and_the_window_are_kept(self):
        a = self.activity(self.doc())
        self.assertEqual([(p["number"], p["state"]) for p in a["pulls"]], [(7, "merged"), (3, "open")])
        self.assertEqual([i["number"] for i in a["issues"]], [4])
        # explorer-data.yml's own run is left out; another workflow here stays.
        self.assertEqual([r["run_id"] for r in a["runs"]], [1234, 1236])
        self.assertNotIn("path", a["runs"][0])
        self.assertEqual(a["since"], "2026-10-17T20:00:00Z")
        self.assertEqual(a["repos"], sorted(PUBLIC))
        text = json.dumps(a)
        for leak in ("hidden", "Hidden", "never published", "body", "@", "cmsg_"):
            self.assertNotIn(leak, text)

    def test_titles_are_cleaned_and_urls_built(self):
        a = self.activity(self.doc())
        pull = a["pulls"][0]
        self.assertEqual(pull["title"], "Fix someone's bug")
        self.assertEqual(pull["url"], "https://github.com/Adam-S-Daniel/open-one/pull/7")
        self.assertIsNone(a["pulls"][1]["title"])  # it carried a message id
        self.assertEqual(set(pull), set(pub.PR_KEYS))
        self.assertEqual(a["runs"][0]["url"], "https://github.com/Adam-S-Daniel/open-two/actions/runs/1234")
        self.assertEqual(set(a["runs"][0]), set(pub.RUN_ACTIVITY_KEYS))

    def test_unknown_inputs_are_null_never_empty(self):
        self.assertIsNone(self.activity(self.doc(), public=None))
        self.assertIsNone(pub.build_activity(None, PUBLIC, NOW, NOW))
        self.assertIsNone(self.activity({"fetched_at": "2026-10-31T20:00:00Z", "pulls": []}))
        self.assertIsNone(self.activity(self.doc(fetched_at="2026-10-29T10:00:00Z")))  # stale
        self.assertIsNone(self.activity(self.doc(fetched_at="2026-11-01T10:00:00Z")))  # future

    def test_the_visibility_list_keeps_only_public_fleet_repositories(self):
        path = write(self.t.root / "repos.json", {"repos": [
            {"full_name": "Adam-S-Daniel/open-one", "private": False},
            {"full_name": "Adam-S-Daniel/hidden-a", "private": True},
            {"full_name": "jodidaniel/open-three", "private": False},
            {"full_name": "someone-else/open", "private": False},
            {"full_name": "Adam-S-Daniel/no-flag"}]})
        self.assertEqual(pub.load_public_repos(path),
                         frozenset({"Adam-S-Daniel/open-one", "jodidaniel/open-three"}))
        self.assertIsNone(pub.load_public_repos(write(self.t.root / "bad.json", "[")))
        self.assertIsNone(pub.load_public_repos(None))


class SpendTests(unittest.TestCase):

    FILE = {"schema": 1, "generated_at": "2026-10-31T12:00:00Z", "plan": "Max 20x",
            "weeks": [{"week": "2026-10-19", "eval_runs": 12, "plan_meter_points": 30.5,
                       "api_usd": 4.25, "thread_spend_usd": 18.123456789, "cost_per_verdict": None,
                       "sessions": [{"session": "invented", "usd": 1}], "thread_id": "thread-0001"},
                      {"week": "2026-10-26", "eval_runs": 3, "plan_meter_points": 1,
                       "api_usd": 0, "thread_spend_usd": 2, "cost_per_verdict": 1.5, "plan": "Pro"},
                      {"week": "2026-10-12", "eval_runs": -1, "api_usd": 1},
                      {"week": "not-a-week", "eval_runs": 1}]}

    def setUp(self):
        self.t = Tree(self)
        write(self.t.tree / "spend" / "weekly.json", self.FILE)

    def test_weekly_totals_only_when_included(self):
        spend = pub.build_spend(self.t.tree, True)
        self.assertEqual(spend["generated_at"], "2026-10-31T12:00:00Z")
        self.assertEqual(spend["weeks"], [
            {"week": "2026-10-26", "eval_runs": 3, "plan_meter_points": 1, "api_usd": 0,
             "thread_spend_usd": 2, "cost_per_verdict": 1.5, "plan": "Pro"},
            {"week": "2026-10-19", "eval_runs": 12, "plan_meter_points": 30.5, "api_usd": 4.25,
             "thread_spend_usd": 18.123456789, "cost_per_verdict": None, "plan": "Max 20x"}])
        self.assertNotIn("invented", json.dumps(spend))
        self.assertNotIn("thread-0001", json.dumps(spend))

    def test_excluded_or_missing_is_null(self):
        self.assertIsNone(pub.build_spend(self.t.tree, False))
        self.assertIsNone(pub.build_spend(self.t.tree / "elsewhere", True))
        write(self.t.tree / "spend" / "weekly.json", {**self.FILE, "schema": 2})
        self.assertIsNone(pub.build_spend(self.t.tree, True))

    def test_the_flag_reaches_the_document_both_ways(self):
        on = explorer_data.build(self.t.tree, self.t.roster, self.t.policy, self.t.evals, AS_OF,
                                 SHA_A, SHA_B, spend=True)
        self.assertEqual(len(on["spend"]["weeks"]), 2)
        self.assertIsNone(self.t.build()["spend"])
        explorer_data.finish(on)
        explorer_data.validate(on)

    def test_the_committed_export_policy_includes_spend(self):
        self.assertTrue(pub.include_spend(ROOT / "evals" / "public-export.yml"))
        off = write(self.t.root / "export.yml", "include_spend: false\n")
        self.assertFalse(pub.include_spend(off))
        self.assertFalse(pub.include_spend(None))


class FullDocumentTests(unittest.TestCase):
    """Every section at once, through `finish` and the schema."""

    def setUp(self):
        self.t = Tree(self)
        t = self.t
        routine_pair(t.tree, "20261030T100000Z-aaaaaa", "alpha", 3, 2)
        routine_bare(t.tree, "20261030T110000Z-bbbbbb", "alpha", 1)
        write(t.root / "ac" / "agent-checks", RUNNER)
        write(t.tree / "usage" / "weekly-ci.json", usage_file(
            [hook_row("2026-10-26", "agent-checks", "Adam-S-Daniel/open-one", 3, 1, 1, "ci")]))
        write(t.tree / "spend" / "weekly.json", SpendTests.FILE)
        self.activity = write(t.root / "activity.json", ActivityTests.doc())
        self.repos = write(t.root / "repos.json", {"repos": [
            {"full_name": r, "private": False} for r in sorted(PUBLIC)]})

    def build(self):
        return explorer_data.build(
            self.t.tree, self.t.roster, self.t.policy, self.t.evals, AS_OF, SHA_A, SHA_B,
            visible_repos=PUBLIC, activity=self.activity, agent_checks_dir=self.t.root / "ac",
            spend=True, wall_clock=datetime(2026, 10, 31, 21, 0, tzinfo=timezone.utc))

    def test_the_document_validates_and_passes_finish(self):
        doc = self.build()
        for key in ("evals", "hooks", "activity", "spend"):
            self.assertIsNotNone(doc[key], key)
        explorer_data.finish(doc, PUBLIC)
        explorer_data.validate(doc)

    def test_the_schema_is_draft_2020_12_and_names_version_1(self):
        import jsonschema
        schema = json.loads(explorer_data.SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        jsonschema.Draft202012Validator.check_schema(schema)
        self.assertEqual(schema["properties"]["schema_version"], {"const": explorer_data.SCHEMA_VERSION})
        self.assertEqual(sorted(schema["required"]), sorted(self.build()))
        self.assertIn("spend_file", schema["$defs"])

    def test_the_schema_refuses_a_document_off_the_contract(self):
        doc = self.build()
        for name, change in (
                ("an extra top-level key", lambda d: d.update(surprise=1)),
                ("another schema version", lambda d: d.update(schema_version=2)),
                ("an extra eval run field", lambda d: d["evals"]["runs"][0].update(session="x")),
                ("a bad verdict", lambda d: d["hooks"]["checks"][0].update(verdict="maybe")),
                ("an activity row with a body", lambda d: d["activity"]["issues"][0].update(body="x")),
                ("a missing section", lambda d: d.pop("spend"))):
            bad = copy.deepcopy(doc)
            change(bad)
            with self.subTest(name), self.assertRaises(explorer_data.Refused):
                explorer_data.validate(bad)

    def test_finish_refuses_ids_private_repositories_and_extra_fields(self):
        doc = self.build()
        cases = (
            ("a message id", lambda d: d["activity"]["pulls"][0].update(title="cmsg_01ABCDEFGH")),
            ("a trigger id", lambda d: d["activity"]["runs"][0].update(title="trig_01ABCDEFGH")),
            ("a thread id", lambda d: d["activity"]["issues"][0].update(title="thread_9a8B7c6D")),
            ("a private repository in activity",
             lambda d: d["activity"]["issues"][0].update(repo="Adam-S-Daniel/hidden-a",
                                                         url="https://github.com/Adam-S-Daniel/hidden-a/issues/4")),
            ("a hand-made activity URL",
             lambda d: d["activity"]["runs"][0].update(url="https://example.com/run")),
            ("a private repository in hooks",
             lambda d: d["hooks"]["totals"]["ci"][0].update(repo="Adam-S-Daniel/hidden-a")),
            ("the bucket below its minimum",
             lambda d: d["hooks"]["totals"]["ci"][0].update(repo=pub.PRIVATE_BUCKET)),
            ("a per-session spend row",
             lambda d: d["spend"]["weeks"][0].update(sessions=[])),
            ("an extra eval field", lambda d: d["evals"]["runs"][0].update(transcript="x")),
            ("a long hex in an eval row",
             lambda d: d["evals"]["runs"][0].update(cli="0123456789abcdef")),
            ("a non-count in the funnel", lambda d: d.update(lesson_funnel={
                **dict.fromkeys(pub.OUTCOMES, 0), "check": "many", "by_source": {},
                "sources_missing": []})))
        for name, change in cases:
            bad = copy.deepcopy(doc)
            change(bad)
            with self.subTest(name), self.assertRaises(explorer_data.Refused):
                explorer_data.finish(bad, PUBLIC)
        # Without the visibility list, activity is refused outright.
        with self.assertRaises(explorer_data.Refused):
            explorer_data.finish(doc)

    def test_a_field_name_is_not_an_id(self):
        # `thread_spend_usd` is a key, not a thread id.
        self.assertIsNone(pub.FORBIDDEN_ID_RE.search('"thread_spend_usd": 2'))
        self.assertIsNotNone(pub.FORBIDDEN_ID_RE.search("thread_9a8B7c6D"))
        self.assertIsNone(pub.safe_text("ok session_01ABCDEFGH"))
        self.assertIsNone(pub.safe_text("sha 0123456789abcdef0"))
        self.assertEqual(pub.safe_text("  ping  @someone \n now "), "ping someone now")

    def test_the_cli_validates_and_writes(self):
        t = self.t
        out = t.root / "out" / "latest.json"
        funnel = write(t.root / "funnel.json", {"hook_proposals": [], "lesson_check_prs": []})
        args = ["--results-tree", str(t.tree), "--roster", str(t.roster), "--policy", str(t.policy),
                "--evals-dir", str(t.evals), "--as-of", AS_OF, "--repository-commit", SHA_A,
                "--results-commit", SHA_B, "--agent-checks", str(t.root / "ac"),
                "--public-repos", str(self.repos), "--lesson-funnel", str(funnel),
                "--out", str(out)]
        self.assertEqual(explorer_data.main(args), 0)
        doc = json.loads(out.read_text())
        self.assertEqual(doc["schema_version"], 1)
        self.assertEqual(doc["lesson_funnel"]["sources_missing"],
                         ["draft-skill", "memory", "skill-proposal"])
        # No --activity file: unknown, not empty.
        self.assertIsNone(doc["activity"])
        off = write(t.root / "export.yml", "include_spend: false\n")
        self.assertEqual(explorer_data.main([*args, "--export-policy", str(off)]), 0)
        self.assertIsNone(json.loads(out.read_text())["spend"])
        broken = write(t.root / "hooks.yml", "window_weeks: soon\n")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(explorer_data.main([*args, "--hook-policy", str(broken)]), 2)

    def test_the_cli_refuses_when_the_schema_does_not_validate(self):
        t = self.t
        out = t.root / "out2" / "latest.json"
        args = ["--results-tree", str(t.tree), "--roster", str(t.roster), "--policy", str(t.policy),
                "--evals-dir", str(t.evals), "--as-of", AS_OF, "--repository-commit", SHA_A,
                "--results-commit", SHA_B, "--out", str(out)]
        bad = write(t.root / "schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema",
                                             "type": "object", "required": ["not-there"]})
        err = io.StringIO()
        original = explorer_data.SCHEMA_PATH
        explorer_data.SCHEMA_PATH = bad
        try:
            with contextlib.redirect_stderr(err):
                self.assertEqual(explorer_data.main(args), 2)
        finally:
            explorer_data.SCHEMA_PATH = original
        self.assertIn("does not match explorer/schema.json", err.getvalue())
        self.assertFalse(out.exists())


class WorkflowTests(unittest.TestCase):

    NEW_STEPS = {"List the public repositories": "public repositories unavailable (exit $rc)",
                 "List recent activity in the public repositories": "activity unavailable (exit $rc)",
                 "List the lesson outcomes": "lesson outcomes unavailable (exit $rc)"}

    def setUp(self):
        self.wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.steps = {s["name"]: s for s in self.wf["jobs"]["build"]["steps"]}

    def test_the_new_listings_are_soft_hold_the_token_alone_and_print_fixed_lines(self):
        for name, line in self.NEW_STEPS.items():
            step = self.steps[name]
            with self.subTest(name):
                self.assertTrue(step["continue-on-error"])
                self.assertEqual(step["env"], {"GH_TOKEN": "${{ github.token }}"})
                self.assertIn(f'echo "{line}"', step["run"])
                self.assertTrue(step["run"].rstrip().endswith("exit 0"))
                self.assertNotIn("${{", step["run"])
        build = self.steps["Build the explorer data"]
        self.assertNotIn("env", build)
        for flag in ("--agent-checks", "--hook-policy evals/hook-policy.yml",
                     "--export-policy evals/public-export.yml", '"${public[@]}"'):
            self.assertIn(flag, build["run"])
        self.assertIn("for name in public-repos activity lesson-funnel", build["run"])

    def test_only_public_repositories_are_listed_for_activity(self):
        run = self.steps["List recent activity in the public repositories"]["run"]
        self.assertIn("select(.private == false)", run)
        self.assertNotIn(".body", run)
        # The run's path is read so explorer_data.py can leave out this
        # workflow's own runs.
        self.assertIn("{repo: $repo, id, path, workflow: .name", run)
        publish = next(s for s in self.wf["jobs"]["publish"]["steps"]
                       if s["name"].startswith("Commit to"))["run"]
        self.assertIn(".activity.fetched_at, .activity.since)'", publish)
        listing = self.steps["List the public repositories"]["run"]
        self.assertIn("for owner in Adam-S-Daniel jodidaniel", listing)

    def test_the_install_carries_the_schema_and_parser_pins(self):
        install = self.steps["Install the offline verdict dependency"]["run"].split()
        pins = dict(p.split("==") for p in install if "==" in p)
        setup = (ROOT / "scripts" / "dev_setup.sh").read_text(encoding="utf-8")
        for name in ("jsonschema", "tree-sitter", "tree-sitter-bash", "pyyaml"):
            with self.subTest(name):
                self.assertIn(f"  {name}=={pins[name]}\n", setup)

    def test_the_agents_md_row_names_the_new_inputs(self):
        agents = (ROOT / "docs" / "workflows.md").read_text(encoding="utf-8")
        row = next(line for line in agents.splitlines() if line.startswith("| `explorer-data.yml`"))
        for word in ("schema.json", "activity", "hook-policy.yml", "public-export.yml",
                     "lesson_funnel", "private repos"):
            self.assertIn(word, row)


if __name__ == "__main__":
    unittest.main()
