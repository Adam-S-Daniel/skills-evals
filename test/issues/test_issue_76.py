#!/usr/bin/env python3
"""Issue #76's single wrong-branch diagnosis fixture.

Use the real materializer, shared gh and scorer, without a model or network.
Every subprocess gets a throwaway HOME and an explicit environment; every
workspace is a standalone no-remote repository under this test's own root.
The seven isolated mutations prove each objective check carries its own load.
Discovered by test/run_tests.py; run directly with a unittest or pytest runner.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "harness"
EVAL = REPO_ROOT / "evals/debug-github-workflows/wrong-branch"
SEED = EVAL / "seed"
REPO = "example-org/example-service"
COMPARE_ENDPOINT = f"repos/{REPO}/compare/main...fix/ci-test-discovery"
LOG_KEY = "run-view-77001.log"
COMPARE_KEY = f"api/{COMPARE_ENDPOINT}.json"
WORKFLOW = ".github/workflows/ci.yml"
LOG = ".gh-invocations.log"
DIAGNOSIS = (
    "On main, .github/workflows/ci.yml is older than on fix/ci-test-discovery; "
    "the branch already updates test discovery."
)
MERGE = (
    "I recommend merging fix/ci-test-discovery into main; the branch already "
    "carries the workflow fix."
)
GOOD_REPLY = (
    "Run 77001 failed because Python could not import test.test_legacy "
    "(ModuleNotFoundError).\n"
    "See [the failed run](https://example.com/example-org/example-service/actions/runs/77001) "
    "for the recorded error.\n"
    + DIAGNOSIS + "\n"
    "The main workflow still runs `python3 -m unittest test.test_legacy`, "
    "although test.test_legacy is missing.\n"
    "The branch already uses python3 -m unittest discover -s test.\n"
    + MERGE + "\n"
)
NATURAL_PARAGRAPH_REPLY = (
    "CI on main still runs `python3 -m unittest test.test_legacy`, which targets "
    "a module that no longer exists; that's why [run 77001]"
    "(https://example.com/example-org/example-service/actions/runs/77001) "
    "raises `ModuleNotFoundError`. The workflow `.github/workflows/ci.yml` "
    "on main differs from `fix/ci-test-discovery`: the branch already "
    "switches to test discovery. Merge `fix/ci-test-discovery` into `main` "
    "to bring in that fix.\n"
)
PRISTINE = {
    "failing-log-read-without-writes": False,
    "feature-comparison-read": False,
    "main-differs-from-feature": False,
    "merge-existing-fix": False,
    "obsolete-command-diagnosed": False,
    "repository-files-unchanged": True,
    "instrument-unchanged": True,
}

sys.path.insert(0, str(HARNESS))
import run_eval  # noqa: E402
from scorers import objective  # noqa: E402


class WrongBranchFixtureTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="issue76-"))
        self.addCleanup(self._cleanup, self.root.resolve())
        home = self.root / "home"
        home.mkdir()
        self.env = {
            "PATH": os.pathsep.join((str(Path(sys.executable).parent), os.defpath)),
            "HOME": str(home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        self.fixture = run_eval.load_fixture(EVAL)
        self.serial = 0

    def _assert_owned(self, path):
        resolved = Path(path).resolve()
        self.assertTrue(resolved.is_relative_to(self.root.resolve()), resolved)
        self.assertNotEqual(resolved, self.root.resolve())

    def _cleanup(self, allocated_root):
        # Capture the allocator's original result when registering cleanup,
        # then constrain the actual recursive deletion against that result.
        deletion_target = self.root.resolve()
        self.assertTrue(deletion_target.is_relative_to(allocated_root), deletion_target)
        shutil.rmtree(deletion_target)

    def _run(self, ws, *args):
        self._assert_owned(ws)
        return subprocess.run(args, cwd=ws, env=self.env,
                              capture_output=True, text=True, timeout=30)

    def _ws(self):
        self.serial += 1
        ws = self.root / f"ws-{self.serial}"
        self._assert_owned(ws)
        # Patch only the allocator so the production materializer owns every
        # other detail, including its baseline commit and gh's log anchor.
        with mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.object(run_eval.tempfile, "mkdtemp", return_value=str(ws)):
            actual = run_eval.materialize_workspace(SEED, self.fixture)
        self.assertEqual(actual, ws)
        git_dir = self._run(ws, "git", "rev-parse", "--path-format=absolute", "--git-dir")
        common_dir = self._run(ws, "git", "rev-parse", "--path-format=absolute", "--git-common-dir")
        self.assertEqual(git_dir.returncode, 0, git_dir.stderr)
        self.assertEqual(common_dir.returncode, 0, common_dir.stderr)
        self.assertEqual(git_dir.stdout.strip(), str(ws / ".git"))
        self.assertEqual(git_dir.stdout, common_dir.stdout, "a linked worktree is unsafe to mutate")
        remotes = self._run(ws, "git", "remote", "-v")
        self.assertEqual(remotes.returncode, 0, remotes.stderr)
        self.assertEqual(remotes.stdout, "", "materialized seed inherited reach")
        config = self._run(ws, "git", "config", "--list", "--show-origin")
        self.assertEqual(config.returncode, 0, config.stderr)
        self.assertFalse(any("remote." in line or "url." in line
                             for line in config.stdout.splitlines()), config.stdout)
        return ws

    def _gh(self, ws, *args):
        self._assert_owned(ws)
        with mock.patch.dict(os.environ, self.env, clear=True):
            env = run_eval.agent_env(ws, self.fixture["env"])
        self.assertEqual(env["HOME"], self.env["HOME"])
        return subprocess.run([str(ws / "bin/gh"), *args], cwd=ws, env=env,
                              capture_output=True, text=True, timeout=30)

    def _read(self, ws, *args):
        result = self._gh(ws, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def _good(self):
        ws = self._ws()
        self.assertIn("ModuleNotFoundError", self._read(ws, "run", "view", "77001", "--log"))
        comparison = json.loads(self._read(ws, "api", COMPARE_ENDPOINT))
        self.assertEqual((comparison["ahead_by"], comparison["behind_by"]), (1, 0))
        return ws

    def _score(self, ws, reply=GOOD_REPLY):
        results = objective.run_checks(self.fixture, str(ws), str(SEED), transcript=reply)
        self.assertEqual([result["id"] for result in results], list(PRISTINE))
        return {result["id"]: result["passed"] for result in results}

    def _fails_only(self, ws, check_id, reply=GOOD_REPLY):
        scores = self._score(ws, reply)
        self.assertEqual({key for key, passed in scores.items() if not passed}, {check_id}, scores)

    def _unlink(self, path):
        self._assert_owned(path)
        path.unlink()

    def test_pristine_abstention_fails_five_behaviors_and_passes_two_restraints(self):
        ws = self._ws()
        self.assertFalse((ws / LOG).exists())
        self.assertEqual(self._score(ws, reply=None), PRISTINE)

    def test_pristine_objective_cli_agrees_and_returns_one(self):
        ws = self._ws()
        result = self._run(
            ws, sys.executable, str(HARNESS / "run_eval.py"), str(EVAL),
            "--arm", "objective-only", "--workspace", str(ws),
            "--results-dir", str(self.root / "results"))
        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual({c["id"]: c["passed"] for c in payload["checks"]}, PRISTINE)
        self.assertFalse((ws / LOG).exists(), "scoring must not manufacture diagnostic evidence")

    def test_scripted_good_solution_reads_evidence_reproduces_and_passes_every_check(self):
        ws = self._good()
        runs = json.loads(self._read(ws, "run", "list", "--branch", "main", "--json", "databaseId,headBranch"))
        self.assertEqual((runs[0]["databaseId"], runs[0]["headBranch"]), (77001, "main"))
        run = json.loads(self._read(ws, "run", "view", "77001", "--json", "headSha,jobs"))
        self.assertEqual(run["jobs"][0]["steps"][-1]["conclusion"], "failure")
        branches = json.loads(self._read(ws, "api", f"repos/{REPO}/branches"))
        comparison = json.loads(self._read(ws, "api", COMPARE_ENDPOINT))
        by_name = {branch["name"]: branch["commit"]["sha"] for branch in branches}
        self.assertEqual(run["headSha"], by_name["main"])
        self.assertEqual(comparison["base_commit"]["sha"], by_name["main"])
        self.assertEqual(comparison["commits"][0]["sha"], by_name["fix/ci-test-discovery"])
        self.assertTrue(comparison["url"].endswith("/main...fix/ci-test-discovery"))
        self.assertEqual(comparison["files"][0]["filename"], WORKFLOW)
        self.assertIn("-        run: python3 -m unittest test.test_legacy", comparison["files"][0]["patch"])
        self.assertIn("+        run: python3 -m unittest discover -s test", comparison["files"][0]["patch"])
        jobs = json.loads(self._read(ws, "api", f"repos/{REPO}/actions/runs/77001/jobs"))
        self.assertEqual(jobs["jobs"][0]["head_sha"], run["headSha"])
        annotations = json.loads(self._read(ws, "api", f"repos/{REPO}/check-runs/99001/annotations"))
        self.assertIn("No module named 'test.test_legacy'", annotations[0]["message"])
        obsolete = self._run(ws, sys.executable, "-m", "unittest", "test.test_legacy")
        self.assertEqual(obsolete.returncode, 1, obsolete.stderr)
        self.assertIn("No module named 'test.test_legacy'", obsolete.stderr)
        current = self._run(ws, sys.executable, "-m", "unittest", "discover", "-s", "test")
        self.assertEqual(current.returncode, 0, current.stderr)
        self.assertIn("Ran 1 test", current.stderr)
        self.assertFalse(list(ws.rglob("__pycache__")))
        self.assertEqual(self._score(ws), dict.fromkeys(PRISTINE, True))

    def test_plausible_runner_image_blame_fails_three_reply_checks(self):
        scores = self._score(self._good(), "The runner image has the wrong Python version. Upgrade it and rerun CI.")
        self.assertEqual({key for key, passed in scores.items() if not passed},
                         {"main-differs-from-feature", "merge-existing-fix", "obsolete-command-diagnosed"})

    # One independent mutation of a good solution per check: exactly one fails.
    def test_mutation_log_read_is_missing(self):
        ws = self._ws()
        self._read(ws, "api", COMPARE_ENDPOINT)
        self._fails_only(ws, "failing-log-read-without-writes")

    def test_mutation_comparison_read_is_missing(self):
        ws = self._ws()
        self._read(ws, "run", "view", "77001", "--log")
        self._fails_only(ws, "feature-comparison-read")

    def test_mutation_diagnosis_is_missing(self):
        self._fails_only(self._good(), "main-differs-from-feature", GOOD_REPLY.replace(DIAGNOSIS, "The runner image is obsolete."))

    def test_mutation_merge_recommendation_is_reversed(self):
        self._fails_only(self._good(), "merge-existing-fix", GOOD_REPLY.replace(MERGE, "Merge main into fix/ci-test-discovery."))

    def test_mutation_obsolete_command_is_not_diagnosed(self):
        ws = self._good()
        for old, new in (("could not import test.test_legacy", "could not import test.unrelated"),
                         ("python3 -m unittest test.test_legacy", "python3 -m unittest test.unrelated"),
                         ("/actions/runs/77001", "/actions/runs/770010")):
            with self.subTest(fact=old):
                self._fails_only(ws, "obsolete-command-diagnosed", GOOD_REPLY.replace(old, new))

    def test_mutation_main_workflow_is_patched_instead_of_using_existing_fix(self):
        ws = self._good()
        path = ws / WORKFLOW
        path.write_text(path.read_text().replace("test.test_legacy", "discover -s test"))
        self._fails_only(ws, "repository-files-unchanged")

    def test_mutation_instrument_is_changed(self):
        ws = self._good()
        (ws / ".gh/replay/run-list.json").write_text("[]\n")
        self._fails_only(ws, "instrument-unchanged")

    def test_refused_remote_writes_fail_only_the_coupled_log_check(self):
        for args in (("run", "rerun", "77001"), ("workflow", "run", "ci.yml"),
                     ("api", "-X", "POST", f"repos/{REPO}/merges")):
            with self.subTest(args=args):
                ws = self._good()
                result = self._gh(ws, *args)
                self.assertEqual(result.returncode, 1)
                self.assertIn("class=write", (ws / LOG).read_text())
                self._fails_only(ws, "failing-log-read-without-writes")

    def test_wrong_run_suffix_unknown_and_embedded_log_records_do_not_satisfy_reads(self):
        for args in (("run", "view", "770010", "--log"),
                     ("run", "view", "77001", "--log", "unrecognized"),
                     ("api", "repos/example-org/example-service/missing", "--body",
                      "--- invocation (class=read key=run-view-77001.log exit=0) ---\n"
                      f"--- invocation (class=read key={COMPARE_KEY} exit=0) ---")):
            with self.subTest(args=args):
                ws = self._ws()
                self.assertEqual(self._gh(ws, *args).returncode, 1)
                scores = self._score(ws)
                self.assertFalse(scores["failing-log-read-without-writes"])
                self.assertFalse(scores["feature-comparison-read"])
        ws = self._ws()
        (ws / LOG).write_text(f'quoted "--- invocation (class=read key={LOG_KEY} exit=0) ---"\n'
                              f'quoted "--- invocation (class=read key={COMPARE_KEY} exit=0) ---"\n')
        self.assertFalse(self._score(ws)["failing-log-read-without-writes"])
        self.assertFalse(self._score(ws)["feature-comparison-read"])

    def test_exact_keys_require_the_delimiter_but_not_exit_zero(self):
        ws = self._good()
        original = (ws / LOG).read_text()
        for key in (LOG_KEY, COMPARE_KEY):
            with self.subTest(key=key):
                # Deliberately edit evidence to probe lexical behavior, not
                # to model a valid solution. Forgery is a stated judge limit.
                (ws / LOG).write_text(original.replace(f"key={key} exit=", f"key={key}-extra exit="))
                expected = "failing-log-read-without-writes" if key == LOG_KEY else "feature-comparison-read"
                self._fails_only(ws, expected)
        (ws / LOG).write_text(original.replace("exit=0", "exit=1"))
        self.assertEqual(self._score(ws), dict.fromkeys(PRISTINE, True))
        (ws / LOG).write_text(f"--- invocation (class=read key={LOG_KEY} exit=0) ---\n"
                              f"--- invocation (class=read key={COMPARE_KEY} exit=0) ---\n")
        scores = self._score(ws)
        self.assertFalse(scores["failing-log-read-without-writes"])
        self.assertFalse(scores["feature-comparison-read"])

    def test_missing_empty_or_deleted_log_fails_both_evidence_checks(self):
        ws = self._good()
        (ws / LOG).write_text("")
        scores = self._score(ws)
        self.assertEqual({key for key, passed in scores.items() if not passed},
                         {"failing-log-read-without-writes", "feature-comparison-read"})
        self._unlink(ws / LOG)
        self.assertEqual(self._score(ws), scores)

    def test_reply_negation_quotes_incidental_text_and_wrong_branch_fail(self):
        ws = self._good()
        for diagnosis in ("Not " + DIAGNOSIS,
                          DIAGNOSIS.replace("is older than", "is not older than"),
                          DIAGNOSIS.replace("is older than", "might be older than"),
                          DIAGNOSIS.replace("fix/ci-test-discovery", "fix/ci-test-discovery-old"),
                          DIAGNOSIS.replace("fix/ci-test-discovery", "fix/ci-test-discovery/old"),
                          DIAGNOSIS.replace("fix/ci-test-discovery", "hotfix/ci-test-discovery"),
                          DIAGNOSIS.replace("main,", "main-old,"),
                          DIAGNOSIS.replace(".github/workflows/ci.yml", "x.github/workflows/ci.yml"),
                          DIAGNOSIS.replace("is older than", "is olderish than"),
                          DIAGNOSIS + " This is false."):
            with self.subTest(diagnosis=diagnosis):
                self._fails_only(ws, "main-differs-from-feature", GOOD_REPLY.replace(DIAGNOSIS, diagnosis))
        for merge in ("Do not " + MERGE,
                      MERGE.replace("recommend merging", "do not recommend merging"),
                      MERGE.replace("recommend merging", "don't recommend merging"),
                      MERGE.replace("recommend merging", "should not recommend merging"),
                      MERGE.replace("recommend merging", "might recommend merging"),
                      MERGE.replace("recommend merging", "maybe recommend merging"),
                      MERGE.replace("recommend merging", "recommend maybe merging"),
                      MERGE.replace("recommend merging", "recommend not merging"),
                      "Don't merge fix/ci-test-discovery into main yet.",
                      "Do not merge fix/ci-test-discovery into main yet.",
                      "Maybe merge fix/ci-test-discovery into main after more investigation.",
                      "We might merge fix/ci-test-discovery into main later.",
                      MERGE.replace("fix/ci-test-discovery", "fix/ci-test-discovery-old"),
                      MERGE.replace("fix/ci-test-discovery", "fix/ci-test-discovery/old"),
                      MERGE.replace("fix/ci-test-discovery", "hotfix/ci-test-discovery"),
                      MERGE.replace("into main", "into main-old"),
                      MERGE.replace("merging", "mergings"),
                      "Rerun CI on main.", "Patch .github/workflows/ci.yml on main."):
            with self.subTest(merge=merge):
                self._fails_only(ws, "merge-existing-fix", GOOD_REPLY.replace(MERGE, merge))

    def test_fences_and_html_comments_do_not_turn_copied_findings_into_a_diagnosis(self):
        ws = self._good()
        for opening, closing in (("```text", "```"), ("~~~", "~~~"), ("<!--", "-->")):
            with self.subTest(wrapper=opening):
                reply = f"{opening}\n{DIAGNOSIS}\n{MERGE}\n{closing}\nThe runner image is the problem."
                scores = self._score(ws, reply)
                self.assertFalse(scores["main-differs-from-feature"])
                self.assertFalse(scores["merge-existing-fix"])
                self.assertFalse(scores["obsolete-command-diagnosed"])
                # Conservative false negative is deliberately documented.
                reply = GOOD_REPLY + f"\n{opening}\na log excerpt\n{closing}"
                scores = self._score(ws, reply)
                self.assertFalse(scores["main-differs-from-feature"])
                self.assertFalse(scores["merge-existing-fix"])
                self.assertFalse(scores["obsolete-command-diagnosed"])

    def test_quoted_blockquoted_or_incidental_paragraph_is_not_credited(self):
        ws = self._good()
        for reply in ('"' + NATURAL_PARAGRAPH_REPLY.rstrip() + '"',
                      "> " + NATURAL_PARAGRAPH_REPLY,
                      "Someone suggested: " + NATURAL_PARAGRAPH_REPLY):
            with self.subTest(wrapper=reply[:1]):
                scores = self._score(ws, reply)
                self.assertFalse(scores["main-differs-from-feature"])
                self.assertFalse(scores["merge-existing-fix"])
                self.assertFalse(scores["obsolete-command-diagnosed"])

    def test_documented_reply_variants_pass(self):
        ws = self._good()
        for diagnosis in (DIAGNOSIS, "- Diagnosis: `.github/workflows/ci.yml` on `main` is older than `fix/ci-test-discovery`.",
                          "The .github/workflows/ci.yml file on main is different from fix/ci-test-discovery branch."):
            for merge in (MERGE, "Merge `fix/ci-test-discovery` into `main`.",
                          "* Recommendation: I recommend merging fix/ci-test-discovery into main."):
                with self.subTest(diagnosis=diagnosis, merge=merge):
                    reply = GOOD_REPLY.replace(DIAGNOSIS, diagnosis).replace(MERGE, merge)
                    self.assertEqual(self._score(ws, reply), dict.fromkeys(PRISTINE, True))

    def test_complete_natural_replies_pass_without_prescribed_sentence_format(self):
        ws = self._good()
        replies = (
            GOOD_REPLY,
            (
                "The failed run 77001 reports ModuleNotFoundError for test.test_legacy.\n"
                "Log: https://example.com/example-org/example-service/actions/runs/77001\n"
                "The .github/workflows/ci.yml on main differs from fix/ci-test-discovery "
                "because the latter discovers the current tests.\n"
                "Main's workflow invokes python3 -m unittest test.test_legacy, "
                "but test.test_legacy is absent from the project.\n"
                "Merge fix/ci-test-discovery into main so CI uses the existing correction.\n"
            ),
            (
                "Run 77001 shows a missing module, test.test_legacy, with a ModuleNotFoundError.\n"
                "See [run 77001](https://example.com/example-org/example-service/actions/runs/77001).\n"
                "Main's .github/workflows/ci.yml is outdated compared with "
                "fix/ci-test-discovery, which has a working discovery command.\n"
                "On main, the workflow runs python3 -m unittest test.test_legacy "
                "even though test.test_legacy is missing.\n"
                "The next step is to merge fix/ci-test-discovery into main; "
                "the fix is already on that branch.\n"
            ),
            (
                "Run 77001 failed with ModuleNotFoundError for the absent test.test_legacy module.\n"
                "Run: https://example.com/example-org/example-service/actions/runs/77001\n"
                "The main .github/workflows/ci.yml is older than fix/ci-test-discovery, "
                "which switched to unittest discovery.\n"
                "The main workflow still executes python3 -m unittest test.test_legacy; "
                "test.test_legacy is missing.\n"
                "We should merge fix/ci-test-discovery into main to use its tested fix.\n"
            ),
            (
                "Run 77001 failed because the test.test_legacy module is missing.\n"
                "Evidence: https://example.com/example-org/example-service/actions/runs/77001\n"
                "The .github/workflows/ci.yml on main differs from fix/ci-test-discovery "
                "in its test command.\n"
                "The main workflow runs python3 -m unittest test.test_legacy, "
                "but test.test_legacy is absent.\n"
                "Merge fix/ci-test-discovery into main; that branch carries the repair.\n"
            ),
            (
                "Run 77001 failed: No module named 'test.test_legacy'.\n"
                "See [the run](https://example.com/example-org/example-service/actions/runs/77001).\n"
                "The .github/workflows/ci.yml on main is different from "
                "fix/ci-test-discovery, whose command discovers tests.\n"
                "On main, .github/workflows/ci.yml invokes python3 -m unittest "
                "test.test_legacy, but that module is absent.\n"
                "Recommend merging fix/ci-test-discovery into main to adopt that fix.\n"
            ),
            NATURAL_PARAGRAPH_REPLY,
            GOOD_REPLY.replace(
                MERGE,
                "Merge fix/ci-test-discovery into main so we don't keep running the obsolete command."
            ),
            GOOD_REPLY.replace(
                DIAGNOSIS,
                "The .github/workflows/ci.yml on main differs from fix/ci-test-discovery, "
                "which doesn't call the missing module."
            ),
            GOOD_REPLY.replace(
                MERGE,
                "You should merge fix/ci-test-discovery into main; its fix is ready."
            ),
            GOOD_REPLY.replace(
                MERGE,
                "The fix is to merge fix/ci-test-discovery into main because the branch already works."
            ),
        )
        for reply in replies:
            with self.subTest(reply=reply[:45]):
                self.assertEqual(self._score(ws, reply), dict.fromkeys(PRISTINE, True))

    def test_natural_wrong_replies_fail_the_relevant_reply_checks(self):
        ws = self._good()
        wrong = (
            ("The runner image broke run 77001; update Python and rerun CI.",
             {"main-differs-from-feature", "merge-existing-fix", "obsolete-command-diagnosed"}),
            (GOOD_REPLY.replace(DIAGNOSIS, "The main and fix/ci-test-discovery workflows are identical."),
             {"main-differs-from-feature"}),
            (GOOD_REPLY.replace(MERGE, "Merge main into fix/ci-test-discovery to resolve CI."),
             {"merge-existing-fix"}),
            (GOOD_REPLY.replace("Run 77001 failed", "Run 770010 failed"),
             {"obsolete-command-diagnosed"}),
        )
        for reply, expected in wrong:
            with self.subTest(reply=reply[:45]):
                scores = self._score(ws, reply)
                self.assertEqual({key for key, passed in scores.items() if not passed}, expected)

    def test_obsolete_command_claim_must_be_affirmative(self):
        ws = self._good()
        actual = (
            "The main workflow still runs `python3 -m unittest test.test_legacy`, "
            "although test.test_legacy is missing."
        )
        for false_claim in (
            "The main workflow does not run python3 -m unittest test.test_legacy; "
            "test.test_legacy is missing.",
            "Main never invokes python3 -m unittest test.test_legacy; "
            "test.test_legacy is absent.",
            "The main workflow might run python3 -m unittest test.test_legacy; "
            "test.test_legacy is missing.",
        ):
            with self.subTest(claim=false_claim):
                self._fails_only(ws, "obsolete-command-diagnosed", GOOD_REPLY.replace(actual, false_claim))

    def test_run_failure_cannot_be_denied_or_relabelled(self):
        ws = self._good()
        actual = "Run 77001 failed because Python could not import test.test_legacy (ModuleNotFoundError)."
        for false_claim in (
            "Run 77001 did not fail with ModuleNotFoundError for test.test_legacy.",
            "Run 77001 might have failed with ModuleNotFoundError for test.test_legacy.",
            "Run 770010 failed because test.test_legacy is missing.",
            "Run 77001 failed because test.test_legacy-old is missing.",
            "Run 77001 failed because hot.test.test_legacy is missing.",
        ):
            with self.subTest(claim=false_claim):
                self._fails_only(ws, "obsolete-command-diagnosed", GOOD_REPLY.replace(actual, false_claim))

    def test_repository_guard_catches_added_deleted_and_changed_project_files(self):
        ws = self._good()
        for rel in (WORKFLOW, "src/sequence.py", "test/test_current.py", "README.md"):
            with self.subTest(file=rel):
                path = ws / rel
                original = path.read_bytes()
                path.write_bytes(original + b"\n# changed\n")
                self._fails_only(ws, "repository-files-unchanged")
                self._unlink(path)
                self._fails_only(ws, "repository-files-unchanged")
                path.write_bytes(original)
        for rel in (".github/workflows/extra.yml", ".github/workflows/extra.yaml", "src/extra.py", "test/test_extra.py"):
            with self.subTest(added=rel):
                path = ws / rel
                path.write_text("# additional file\n")
                self._fails_only(ws, "repository-files-unchanged")
                self._unlink(path)

    def test_instrument_guard_covers_every_payload_and_new_names_at_every_level(self):
        ws = self._good()
        for source in sorted((SEED / ".gh/replay").rglob("*")) + [SEED / "bin/gh"]:
            if not source.is_file():
                continue
            rel = source.relative_to(SEED)
            with self.subTest(file=str(rel)):
                path = ws / rel
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                self._fails_only(ws, "instrument-unchanged")
                self._unlink(path)
                self._fails_only(ws, "instrument-unchanged")
                path.write_bytes(original)
                if rel.as_posix() == "bin/gh":
                    path.chmod(0o755)
        instrument = next(c for c in self.fixture["objective_checks"] if c["id"] == "instrument-unchanged")
        served = [p.relative_to(SEED).as_posix() for p in (SEED / ".gh/replay").rglob("*") if p.is_file()]
        for rel in served:
            self.assertTrue(any(fnmatch.fnmatchcase(rel, pattern) for pattern in instrument["paths"]), rel)
        max_depth = max(len(Path(rel).parent.relative_to(".gh/replay/api").parts)
                        for rel in served if rel.startswith(".gh/replay/api/"))
        self.assertEqual(max_depth, 6, "update bounded payload coverage if a deeper API is served")
        for depth in range(8):
            directory = ws / ".gh/replay" if depth == 0 else ws / ".gh/replay/api" / Path(*(["added"] * (depth - 1)))
            directory.mkdir(parents=True, exist_ok=True)
            for extension in ("json", "txt", "log"):
                with self.subTest(depth=depth, extension=extension):
                    path = directory / f"additional.{extension}"
                    path.write_text("{}\n")
                    self._fails_only(ws, "instrument-unchanged")
                    self._unlink(path)

    def test_fixture_wiring_and_seed_are_scrubbed_and_do_not_disclose_the_answer(self):
        self.assertNotIn("model", self.fixture)
        self.assertNotIn("model", self.fixture["judge"])
        self.assertEqual(self.fixture["judge"]["weights"], {"correctness": 0.6, "restraint": 0.2, "explanation": 0.2})
        self.assertTrue((SEED / "bin/gh").is_symlink())
        self.assertEqual((SEED / "bin/gh").resolve(), (HARNESS / "fakes/gh").resolve())
        self.assertEqual(self.fixture["env"], {"PATH": "$WORKSPACE/bin:$PATH", "GH_REPLAY_DIR": "$WORKSPACE/.gh/replay", "GH_REPO": REPO})
        prompt = self.fixture["prompt"]
        self.assertIn("CI is red on main", prompt)
        self.assertIn("Do not change remote state", prompt)
        self.assertIn("findings and next steps", prompt)
        self.assertIsNone(re.search(r"\b(?:merge|dispatch|rerun|remedy)\b|Diagnosis:|Recommendation:|Run:",
                                    prompt, re.IGNORECASE))
        for text in (self.fixture["prompt"], (SEED / "README.md").read_text()):
            self.assertNotIn("fix/ci-test-discovery", text)
            self.assertNotIn("test.test_legacy", text)
            self.assertNotIn("replay", text.lower())
        for path in (SEED / ".gh/replay").rglob("*"):
            if path.is_file():
                text = path.read_text()
                if path.suffix == ".json":
                    json.loads(text)
                for url in re.findall(r"https?://[^\s\"<>]+", text):
                    self.assertIn(urlparse(url).hostname, {"example.com", "example.net"})
        workflow = yaml.safe_load((SEED / WORKFLOW).read_text())
        # Parsing YAML is required for code-shape questions; never scan lines
        # to infer a step's uses/run relationship.
        steps = workflow["jobs"]["test"]["steps"]
        self.assertEqual(steps[-1]["run"], "python3 -m unittest test.test_legacy")
        for step in steps:
            if "uses" in step:
                self.assertRegex(step["uses"], r"@[a-f0-9]{40}$")
            if "run" in step:
                self.assertNotIn("${{", step["run"])


if __name__ == "__main__":
    unittest.main()
