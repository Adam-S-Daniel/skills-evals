"""Issue #78's hermetic Class C unknowns-pass fixture proofs."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "evals/finding-unknowns"
SEED = EVAL / "seed"
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
import run_eval  # noqa: E402
from scorers import judge, objective  # noqa: E402
import eval_coverage  # noqa: E402

CHECK_IDS = ("cites-export-module", "cites-acceptance-test",
             "cites-design-decision", "source-unchanged")


class TestIssue78(unittest.TestCase):
    def setUp(self):
        self.fixture = run_eval.load_fixture(EVAL)
        self.root = Path(tempfile.mkdtemp(prefix="issue-78-")).resolve()
        self.addCleanup(self._clean)
        # These are metadata-free copies of seed/, not clones or worktrees.
        self.workspace = self._copy_seed("workspace")
        self.strong = (EVAL / "references/strong.md").read_text(encoding="utf-8")
        self.shallow = (EVAL / "references/shallow.md").read_text(encoding="utf-8")

    def _clean(self):
        self.assertEqual(self.root.parent, Path(tempfile.gettempdir()).resolve())
        self.assertTrue(self.root.name.startswith("issue-78-"))
        shutil.rmtree(self.root)

    def _copy_seed(self, name):
        destination = self.root / name
        self.assertFalse(destination.exists())
        shutil.copytree(SEED, destination)
        self.assertFalse((destination / ".git").exists())
        return destination

    def _score(self, reply, workspace=None):
        checks = objective.run_checks(self.fixture, str(workspace or self.workspace),
                                      str(SEED), transcript=reply)
        self.assertEqual(tuple(c["id"] for c in checks), CHECK_IDS)
        return {c["id"]: c["passed"] for c in checks}

    def _fails_only(self, check_id, reply, workspace=None):
        scores = self._score(reply, workspace)
        self.assertEqual({key for key, passed in scores.items() if not passed},
                         {check_id}, scores)

    def test_pristine_behavior_fails_and_source_restraint_passes(self):
        self.assertEqual(self._score(None), dict(zip(CHECK_IDS,
                                                     (False, False, False, True))))

    def test_strong_reference_passes_and_shallow_one_misses_a_behavior(self):
        self.assertEqual(self._score(self.strong), dict.fromkeys(CHECK_IDS, True))
        self._fails_only("cites-design-decision", self.shallow)

    def test_path_mentions_do_not_claim_semantic_correctness(self):
        wrong = ("export/table.py requires loading the full dataset; "
                 "test/test_export.py says empty exports must be blank; "
                 "docs/adr/0001-bounded-exports.md requires a blocking dump.")
        self.assertEqual(self._score(wrong), dict.fromkeys(CHECK_IDS, True))
        self.assertIn("invented meaning", self.fixture["judge_rubric"])

    def test_paraphrase_and_formatting_do_not_change_objective_score(self):
        variants = (
            "Read export/table.py, test/test_export.py, and "
            "docs/adr/0001-bounded-exports.md before choosing a direction.",
            "| Export | `export/table.py` |\n| Test | `test/test_export.py` |\n"
            "| Decision | `docs/adr/0001-bounded-exports.md` |",
            "Read ./export/table.py, ./test/test_export.py, and "
            "./docs/adr/0001-bounded-exports.md.",
        )
        for reply in variants:
            with self.subTest(reply=reply):
                self.assertEqual(self._score(reply), dict.fromkeys(CHECK_IDS, True))

    def test_each_path_check_has_one_isolated_mutation(self):
        for path, check_id in (
            ("export/table.py", "cites-export-module"),
            ("test/test_export.py", "cites-acceptance-test"),
            ("docs/adr/0001-bounded-exports.md", "cites-design-decision"),
        ):
            with self.subTest(check=check_id):
                reply = self.strong.replace(path, "a local file", 1)
                self.assertNotIn(path, reply)
                self._fails_only(check_id, reply)

    def test_source_mutation_fails_only_restraint_and_restores(self):
        source = self.workspace / "src/service.py"
        original = source.read_bytes()
        source.write_bytes(original + b"\n# changed\n")
        self._fails_only("source-unchanged", self.strong)
        source.write_bytes(original)
        self.assertEqual(self._score(self.strong), dict.fromkeys(CHECK_IDS, True))

    def test_source_additions_and_deletions_are_detected(self):
        def add_nested(ws):
            (ws / "src/newdir").mkdir()
            (ws / "src/newdir/new.py").write_text("pass\n")

        for name, mutate in (
            ("new src file", lambda ws: (ws / "src/new.py").write_text("pass\n")),
            ("new export file", lambda ws: (ws / "export/new.py").write_text("pass\n")),
            ("edited export file", lambda ws: (ws / "export/table.py").write_text("pass\n")),
            ("new nested source", add_nested),
            ("deleted source", lambda ws: (ws / "src/service.py").unlink()),
        ):
            with self.subTest(name=name):
                workspace = self._copy_seed(name.replace(" ", "-"))
                mutate(workspace)
                self._fails_only("source-unchanged", self.strong, workspace)

    def test_bytecode_caches_from_the_seed_test_are_not_source_changes(self):
        env = {key: value for key, value in os.environ.items()
               if key not in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX")}
        env["PYTHONPATH"] = str(self.workspace)
        run = subprocess.run([sys.executable, "test/test_export.py", "-q"],
                             cwd=self.workspace, env=env, capture_output=True,
                             text=True, timeout=15)
        self.assertEqual(run.returncode, 1, run.stderr)  # the seed test is red
        for directory in ("src", "export"):
            caches = list((self.workspace / directory / "__pycache__").glob("*.pyc"))
            self.assertTrue(caches, f"{directory}/__pycache__ was not created")
        self.assertEqual(self._score(self.strong), dict.fromkeys(CHECK_IDS, True))

    def test_citation_boundaries(self):
        cases = (
            ("export/table.py", "/tmp/ws/export/table.py", True),
            ("export/table.py", "a/export/table.py", True),  # nested path: accepted
            ("export/table.py", "export/table.py:12", True),
            ("export/table.py", "my_export/table.py", False),
            ("export/table.py", "export/table.pyc", False),
            ("test/test_export.py", "/tmp/ws/test/test_export.py", True),
            ("test/test_export.py", "my_test/test_export.py", False),
            ("test/test_export.py", "test/test_export.py:7", True),
            ("test/test_export.py", "test/test_export.pyc", False),
            ("docs/adr/0001-bounded-exports.md", "/tmp/ws/docs/adr/0001-bounded-exports.md", True),
            ("docs/adr/0001-bounded-exports.md", "my_docs/adr/0001-bounded-exports.md", False),
            ("docs/adr/0001-bounded-exports.md", "docs/adr/0001-bounded-exports.md:3", True),
            ("docs/adr/0001-bounded-exports.md", "docs/adr/0001-bounded-exports.mdx", False),
        )
        ids = {"export/table.py": "cites-export-module",
               "test/test_export.py": "cites-acceptance-test",
               "docs/adr/0001-bounded-exports.md": "cites-design-decision"}
        for path, written, expected in cases:
            with self.subTest(written=written):
                reply = self.strong.replace(path, "a local file")
                self.assertNotIn(path, reply)
                reply += f"\nSee {written}.\n"
                self.assertEqual(self._score(reply)[ids[path]], expected)

    def test_seed_test_fails_then_minimal_fix_passes_in_scratch(self):
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(self.workspace)
        command = [sys.executable, "test/test_export.py", "-q"]
        failed = subprocess.run(command, cwd=self.workspace, env=env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertIn("FAIL: test_empty_export_keeps_header", failed.stderr)
        target = self.workspace / "src/service.py"
        before = target.read_text(encoding="utf-8")
        self.assertIn('return "text/csv; charset=utf-8", iter(())', before)
        target.write_text(before.replace('return "text/csv; charset=utf-8", iter(())',
                                         'return export_response(())', 1), encoding="utf-8")
        passed = subprocess.run(command, cwd=self.workspace, env=env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertIn("Ran 1 test", passed.stderr)

    def test_references_stay_outside_materialized_workspace(self):
        root = self.root / "materialized"
        root.mkdir()
        with mock.patch.dict(os.environ, {"HOME": str(root),
                                          "GIT_CONFIG_GLOBAL": os.devnull,
                                          "GIT_CONFIG_NOSYSTEM": "1"}), \
             mock.patch.object(run_eval.tempfile, "mkdtemp",
                               return_value=str(root / "workspace")):
            workspace = run_eval.materialize_workspace(SEED, self.fixture)
        self.assertEqual(workspace, root / "workspace")
        self.assertFalse((workspace / "references").exists())
        self.assertFalse((workspace / "fixture.yaml").exists())
        remotes = subprocess.run(["git", "remote", "-v"], cwd=workspace,
                                 capture_output=True, text=True, timeout=15)
        self.assertEqual(remotes.returncode, 0, remotes.stderr)
        self.assertEqual(remotes.stdout, "")

    def test_pairwise_references_and_roster_are_registered(self):
        self.assertEqual(run_eval.resolve_fixture_dirs(EVAL, None), [EVAL])
        self.assertEqual(self.fixture["skill"], "finding-unknowns")
        self.assertNotIn("model", self.fixture)
        self.assertNotIn("model", self.fixture["judge"])
        self.assertEqual(self.fixture["judge"]["mode"], "pairwise")
        self.assertNotIn("weights", self.fixture["judge"])
        references = judge.load_references(EVAL, self.fixture["judge"])
        self.assertEqual([r["name"] for r in references], ["strong", "shallow"])
        self.assertEqual([r["text"] for r in references],
                         [self.strong, self.shallow])
        prompt = judge._build_pairwise_prompt(
            self.fixture["judge_rubric"],
            [{"label": "A", "text": self.strong},
             {"label": "B", "text": self.shallow},
             {"label": "C", "text": "candidate"}], nonce="fixednonce")
        self.assertEqual(prompt.count('<draft id='), 4)  # instruction plus three drafts
        self.assertIn("empty export", prompt)
        self.assertIn("Rank the drafts", prompt)
        args = argparse.Namespace(model=None, no_judge=False,
                                  roster=ROOT / "evals/roster.yml")
        agent_model, judge_model, error = run_eval.select_models(self.fixture, args)
        self.assertIsNone(error)
        self.assertTrue(agent_model)
        self.assertTrue(judge_model)
        self.assertNotEqual(agent_model, judge_model)

    def test_coverage_census_discovers_fixture_from_registry_metadata(self):
        catalog = yaml.safe_load((ROOT / "harness/registries.yml").read_text())
        resolved = {entry["name"]: entry for entry in catalog["registries"]}
        counts = eval_coverage.count_fixtures(ROOT / "evals", resolved)
        self.assertEqual(counts[("adam-agentskills", "finding-unknowns")], 1)


if __name__ == "__main__":
    unittest.main()
