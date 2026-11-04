"""Issue #623: a conflicted loop pull request is brought up to date with its
base by merging the base in and re-resolving the append-only paths both
sides added to (scripts/refresh_loop_prs.py, .github/workflows/loop-pr-refresh.yml)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import refresh_loop_prs as rlp  # noqa: E402

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.com",
    "GIT_AUTHOR_DATE": "2026-10-26T00:00:00Z", "GIT_COMMITTER_DATE": "2026-10-26T00:00:00Z",
}

HEADER = "# Skill impact\n\nRules.\n\n---\n\n"
OLD = "## 2026-10-01 — p/old — edit\n- Outcome: kept.\n\n"
MAIN_ENTRY = "## 2026-11-03 — p/one — create\n- Outcome: pending.\n\n"
PR_ENTRY = "## 2026-11-03 — p/two — create\n- Outcome: pending.\n\n"

UNSCHED = "# reasons\nfixtures:\n  - path: evals/a/x\n    reason: \"r\"\n"
ROW = lambda s: f"  - path: evals/{s}/x\n    reason: \"Isolation pair\"\n"  # noqa: E731

README = "```\nevals/\n  a/\n  real-work/\nharness/\n```\n"


def layout(**plugins) -> str:
    return json.dumps({"plugins": {k: {"defaultEnabled": True, "skills": v}
                                   for k, v in sorted(plugins.items())}}, indent=2) + "\n"


class Resolvers(unittest.TestCase):
    def test_skill_impact_puts_the_pull_requests_entry_on_top(self):
        base = HEADER + OLD
        out = rlp.resolve_skill_impact(base, HEADER + MAIN_ENTRY + OLD, HEADER + PR_ENTRY + OLD)
        self.assertEqual(out, HEADER + PR_ENTRY + MAIN_ENTRY + OLD)

    def test_unscheduled_appends_the_rows_and_keeps_every_reason(self):
        out = rlp.resolve_unscheduled(UNSCHED, UNSCHED + ROW("one"), UNSCHED + ROW("two"))
        self.assertEqual(out, UNSCHED + ROW("one") + ROW("two"))
        rows = yaml.safe_load(out)["fixtures"]
        self.assertEqual([r["path"] for r in rows], ["evals/a/x", "evals/one/x", "evals/two/x"])
        self.assertTrue(all(r["reason"] for r in rows))

    def test_readme_puts_the_layout_entry_above_real_work(self):
        mine = "  two/\n    x/\n"
        theirs = "  one/\n    x/\n"
        main = README.replace("  real-work/", theirs + "  real-work/")
        head = README.replace("  real-work/", mine + "  real-work/")
        out = rlp.resolve_readme(README, main, head)
        self.assertEqual(out, README.replace("  real-work/", theirs + mine + "  real-work/"))

    def test_plugin_layout_takes_both_sides_in_canonical_form(self):
        base = layout(p=["a", "c"], q=["z"])
        out = rlp.resolve_plugin_layout(base, layout(p=["a", "b", "c"], q=["z"]),
                                        layout(p=["a", "c", "d"], q=[]))
        self.assertEqual(out, layout(p=["a", "b", "c", "d"], q=[]))

    def test_a_change_that_is_not_one_inserted_block_is_refused(self):
        cases = {
            "edit": (HEADER + OLD, HEADER + MAIN_ENTRY + OLD, HEADER + OLD.replace("kept", "gone")),
            "two blocks": (HEADER + OLD, HEADER + MAIN_ENTRY + OLD,
                           "x\n" + HEADER + PR_ENTRY + OLD),
            "nothing": (HEADER + OLD, HEADER + MAIN_ENTRY + OLD, HEADER + OLD),
            "already there": (HEADER + OLD, HEADER + PR_ENTRY + OLD, HEADER + PR_ENTRY + OLD),
        }
        for label, (base, main, head) in cases.items():
            with self.subTest(label), self.assertRaises(rlp.Unresolvable):
                rlp.resolve_skill_impact(base, main, head)
        with self.assertRaises(rlp.Unresolvable):
            rlp.resolve_unscheduled(UNSCHED, UNSCHED, UNSCHED + "other: 1\n")
        with self.assertRaises(rlp.Unresolvable):
            rlp.resolve_skill_impact("no rule\n", "no rule\nx\n", "no rule\ny\n")


class Merge(unittest.TestCase):
    """Against a real repository: base and pull request both add to the
    same append-only files from one fork point."""

    def setUp(self):
        self.env = mock.patch.dict(os.environ, GIT_ENV)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        self.run_git("init", "-q", "-b", "main", str(self.repo), cwd=self.tmp)
        self.put({"docs/skill-impact.md": HEADER + OLD, "evals/unscheduled.yml": UNSCHED,
                  "other.txt": "one\n"})
        self.commit("fork")
        self.run_git("checkout", "-q", "-b", "pr")
        self.put({"docs/skill-impact.md": HEADER + PR_ENTRY + OLD,
                  "evals/unscheduled.yml": UNSCHED + ROW("two"), "pr.txt": "new\n"})
        self.commit("pull request")
        self.run_git("checkout", "-q", "main")
        self.put({"docs/skill-impact.md": HEADER + MAIN_ENTRY + OLD,
                  "evals/unscheduled.yml": UNSCHED + ROW("one")})
        self.commit("base")
        self.run_git("checkout", "-q", "pr")

    def run_git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.repo, check=True,
                              capture_output=True, text=True).stdout

    def put(self, files):
        for rel, text in files.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def commit(self, msg):
        self.run_git("add", "-A")
        self.run_git("commit", "-q", "-m", msg)

    def test_both_sides_entries_survive_and_the_head_keeps_its_history(self):
        head = self.run_git("rev-parse", "HEAD").strip()
        self.assertEqual(rlp.main(["merge", "--repo", str(self.repo), "--base", "main"]), 0)
        self.assertEqual((self.repo / "docs/skill-impact.md").read_text(),
                         HEADER + PR_ENTRY + MAIN_ENTRY + OLD)
        self.assertEqual((self.repo / "evals/unscheduled.yml").read_text(),
                         UNSCHED + ROW("one") + ROW("two"))
        self.assertEqual((self.repo / "pr.txt").read_text(), "new\n")
        parents = self.run_git("log", "-1", "--format=%P").split()
        self.assertEqual(parents[0], head, "a merge commit on top, never a rewrite")
        self.assertEqual(self.run_git("status", "--porcelain"), "")
        # A second pass is a no-op.
        self.assertEqual(rlp.merge(self.repo, "main"), "up-to-date")

    def test_a_conflict_outside_the_resolvers_is_aborted_untouched(self):
        self.run_git("checkout", "-q", "main")
        self.put({"other.txt": "main\n"})
        self.commit("base edits other")
        self.run_git("checkout", "-q", "pr")
        self.put({"other.txt": "pr\n"})
        self.commit("pr edits other")
        head = self.run_git("rev-parse", "HEAD").strip()
        self.assertEqual(rlp.main(["merge", "--repo", str(self.repo), "--base", "main"]), 3)
        self.assertEqual(self.run_git("rev-parse", "HEAD").strip(), head)
        self.assertEqual(self.run_git("status", "--porcelain"), "")


class Workflow(unittest.TestCase):
    PATH = REPO_ROOT / ".github/workflows/loop-pr-refresh.yml"

    def test_triggers_permissions_and_no_concurrency(self):
        doc = yaml.safe_load(self.PATH.read_text(encoding="utf-8"))
        on = doc[True] if True in doc else doc["on"]
        self.assertEqual(on["workflow_run"]["workflows"], ["Ingest routine eval results"])
        self.assertNotIn("schedule", on)  # ThreePrGateTests
        self.assertIn("workflow_dispatch", on)
        self.assertNotIn("pull_request", on)
        self.assertNotIn("push", on)
        self.assertEqual(doc["permissions"], {})
        # No workflow group, and none on the refresh: a pending run in a
        # group is cancelled by the next. Only the withdraw job has one
        # (PR #724 round 2's R2-2; test_issue_removal_withdrawal.py).
        self.assertNotIn("concurrency", doc)
        self.assertNotIn("concurrency", doc["jobs"]["refresh"])
        self.assertIs(doc["jobs"]["withdraw"]["concurrency"]["cancel-in-progress"], False)

    def test_no_expression_reaches_a_run_block(self):
        doc = yaml.safe_load(self.PATH.read_text(encoding="utf-8"))
        for job in doc["jobs"].values():
            for step in job["steps"]:
                self.assertNotIn("${{", step.get("run", ""), step.get("name"))

    def test_the_follower_also_runs_after_every_ingest(self):
        doc = yaml.safe_load((REPO_ROOT / ".github/workflows/draft-fixtures-follow.yml")
                             .read_text(encoding="utf-8"))
        on = doc[True] if True in doc else doc["on"]
        self.assertEqual(on["workflow_run"]["workflows"], ["Ingest routine eval results"])


if __name__ == "__main__":
    unittest.main()
