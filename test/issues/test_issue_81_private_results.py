"""#81: private-skill evals keep their results in adam-agentskills-private.

The routine pushes a private skill's results to that repository, whose own
ingest writes its `persistent/eval-results`. Here: the overlay that adds
those runs to the workspace tree the planner and the allowance guard read,
the two workflows that run it, and the planner keeping a private skill out
of every output that would publish its pass rate.

Offline: files and workflow YAML only, no network, no model.
Run with: python3 -m pytest test/issues/test_issue_81_private_results.py -q
"""
from __future__ import annotations

from datetime import datetime, timezone
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))

import overlay_private_results as overlay  # noqa: E402

RUN_A = "20261031T220000Z-abcdef"
RUN_B = "20261031T230000Z-012345"
PRIVATE_REPO = "adam-agentskills-private"


def write_run(tree: Path, run_id: str, body: str = "{}") -> Path:
    path = tree / "routine-results" / run_id / "rename-pdfs" / "20261031T220000Z" / "with_skill"
    path.mkdir(parents=True)
    (path / "summary.json").write_text(body, encoding="utf-8")
    return path


class Overlay(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.private = self.tmp / "private"
        self.tree = self.tmp / "tree"
        self.private.mkdir()
        self.tree.mkdir()

    def test_copies_every_private_run_beside_the_public_ones(self):
        write_run(self.tree, RUN_A)
        write_run(self.private, RUN_B, '{"n": 1}')
        self.assertEqual(overlay.overlay(self.private, self.tree), 1)
        copied = self.tree / "routine-results" / RUN_B / "rename-pdfs" / "20261031T220000Z" \
            / "with_skill" / "summary.json"
        self.assertEqual(copied.read_text(encoding="utf-8"), '{"n": 1}')
        self.assertTrue((self.tree / "routine-results" / RUN_A).is_dir())

    def test_no_private_runs_adds_nothing(self):
        self.assertEqual(overlay.overlay(self.private, self.tree), 0)
        self.assertFalse((self.tree / "routine-results").exists())

    def test_a_run_id_in_both_trees_is_refused_and_nothing_is_copied(self):
        write_run(self.tree, RUN_A, "public")
        write_run(self.private, RUN_A, "private")
        write_run(self.private, RUN_B)
        with self.assertRaises(overlay.OverlayError):
            overlay.overlay(self.private, self.tree)
        self.assertFalse((self.tree / "routine-results" / RUN_B).exists())

    def test_a_name_that_is_not_a_run_id_is_refused(self):
        (self.private / "routine-results" / "not-a-run").mkdir(parents=True)
        with self.assertRaises(overlay.OverlayError):
            overlay.overlay(self.private, self.tree)

    def test_a_symlink_inside_a_run_is_refused(self):
        path = write_run(self.private, RUN_B)
        os.symlink("/etc/passwd", path / "tool_trace.json")
        with self.assertRaises(overlay.OverlayError):
            overlay.overlay(self.private, self.tree)
        self.assertFalse((self.tree / "routine-results" / RUN_B).exists())

    def test_the_cli_logs_a_count_and_fails_closed_without_naming_contents(self):
        write_run(self.private, RUN_B, "secret-ish")
        argv = ["--private", str(self.private), "--tree", str(self.tree)]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(overlay.main(argv), 0)
        self.assertIn("1 run(s) added", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(overlay.main(argv), 1)
        self.assertNotIn(RUN_B, out.getvalue())
        self.assertNotIn("secret-ish", out.getvalue())


def steps(workflow: str, job: str) -> list:
    doc = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text(encoding="utf-8"))
    return doc["jobs"][job]["steps"]


def index(all_steps: list, name: str) -> int:
    return next(i for i, s in enumerate(all_steps) if s.get("name") == name)


class Workflows(unittest.TestCase):
    CASES = (("routine-eval-weekly.yml", "plan",
              "Plan the week's fires by band within the weekly allowance"),
             ("routine-eval-fire.yml", None, "Check the weekly allowance"))

    def job_steps(self, workflow, job):
        if job is None:
            doc = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text(encoding="utf-8"))
            job = next(j for j, body in doc["jobs"].items()
                       if any(s.get("name") == "Check the weekly allowance"
                              for s in body.get("steps", [])))
        return steps(workflow, job)

    def test_the_overlay_runs_before_its_reader_on_the_public_tree(self):
        for workflow, job, reader in self.CASES:
            with self.subTest(workflow=workflow):
                all_steps = self.job_steps(workflow, job)
                add = index(all_steps, "Add the private runs to the results tree")
                self.assertLess(index(all_steps, "Check out persistent/eval-results (the ingested runs)"),
                                add)
                self.assertLess(add, index(all_steps, reader))
                self.assertEqual(all_steps[add]["run"].split(),
                                 ["python3", "scripts/overlay_private_results.py", "--private",
                                  "private-eval-results", "--tree", "eval-results-branch"])

    def test_the_token_is_read_only_and_scoped_to_the_private_repository(self):
        for workflow, job, _ in self.CASES:
            with self.subTest(workflow=workflow):
                all_steps = self.job_steps(workflow, job)
                mint = all_steps[index(all_steps, "Mint the read-only token for the private "
                                       + ("registry" if job else "results"))]
                self.assertEqual(mint["with"]["repositories"], PRIVATE_REPO)
                self.assertEqual(mint["with"]["permission-contents"], "read")
                for step in all_steps:
                    uses = step.get("with", {})
                    if uses.get("repository") == f"Adam-S-Daniel/{PRIVATE_REPO}":
                        self.assertIs(uses["persist-credentials"], False)

    def test_nothing_from_the_private_tree_is_uploaded(self):
        for workflow, job, _ in self.CASES:
            with self.subTest(workflow=workflow):
                for step in self.job_steps(workflow, job):
                    if "upload-artifact" in str(step.get("uses", "")):
                        self.assertNotIn("private", str(step["with"]["path"]))


class PlannerKeepsPrivateSkillsOutOfPublicOutputs(unittest.TestCase):
    def test_a_private_skill_gets_no_improve_context(self):
        import plan_week
        with tempfile.TemporaryDirectory() as tree:
            out = plan_week.skill_contexts(
                ROOT / "evals", Path(tree), "20261031T235959Z", {},
                {"roster_models": ["claude-sonnet-5-5"], "skills": {}},
                [], [], [], datetime(2026, 10, 31, 23, 59, tzinfo=timezone.utc))
        self.assertNotIn("adam-writing-style", out)
        self.assertIn("rename-pdfs", out)

    def test_its_fixtures_are_still_scheduled_cells(self):
        rows = yaml.safe_load((ROOT / "evals/scheduled.yml").read_text(encoding="utf-8"))["fixtures"]
        paths = {row["path"] for row in rows}
        for name in ("proposal-bio", "recruiter-reply", "self-appraisal-opening"):
            self.assertIn(f"evals/adam-writing-style/{name}", paths)


if __name__ == "__main__":
    unittest.main()
