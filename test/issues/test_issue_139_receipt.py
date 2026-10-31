"""#139: every guidance arm proves its delivery from its OWN session's
receipt, the `instructions` entry the CLI writes into a persisted transcript.

Measured on CLI 2.1.316 with a scratch CLAUDE_CONFIG_DIR and a stub API
endpoint (no credential): the entry lists each loaded memory file's absolute
path, its type (`User`, `Project`) and its content with HTML comments
removed and whitespace stripped; `--no-session-persistence` writes no
transcript at all, and a session that loads no memory file writes no entry.
test/fake-claude writes the same entry. No network, no real `claude`.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(TEST_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gates  # noqa: E402
import guidance  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import run_eval  # noqa: E402
import test_issue_97 as t97  # noqa: E402
from arm_test_env import install_arm_test_environment  # noqa: E402

FAKE_CLAUDE = TEST_DIR / "fake-claude"


@install_arm_test_environment
def setUpModule() -> None:
    t97.setUpModule()


def tearDownModule() -> None:
    t97.tearDownModule()


class ReceiptVerdictTests(unittest.TestCase):
    """`guidance.receipt_verdict`, pure but for resolving paths."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="receipt-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.config, self.ws = self.root / "config", self.root / "ws"
        self.config.mkdir()
        self.ws.mkdir()
        self.roots = {"config": self.config, "ws": self.ws}

    def verdict(self, files, token="TOK-1", forbidden=("DECOY-2",), memory_type="User"):
        return guidance.receipt_verdict(
            files, roots=self.roots, delivered=self.config / "CLAUDE.md",
            memory_type=memory_type, token=token, forbidden=forbidden)

    def user(self, content="guidance\nThe magic word is TOK-1."):
        return {"path": str(self.config / "CLAUDE.md"), "type": "User", "content": content}

    def test_the_delivered_file_with_its_token_is_ok_and_recorded_relative(self):
        got = self.verdict([self.user(), {"path": str(self.ws / "CLAUDE.md"),
                                          "type": "Project", "content": "seed"}])
        self.assertTrue(got["ok"], got)
        self.assertEqual([f["path"] for f in got["files"]], ["config/CLAUDE.md", "ws/CLAUDE.md"])
        self.assertNotIn(str(self.root), json.dumps(got))
        self.assertEqual(got["files"][1]["bytes"], 4)

    def test_no_entry_is_delivery_unproven(self):
        got = self.verdict(None)
        self.assertEqual((got["ok"], got["reason"]), (False, "delivery_unproven"))

    def test_the_delivered_file_without_its_token_is_unproven(self):
        got = self.verdict([self.user("guidance only")])
        self.assertEqual(got["reason"], "delivery_unproven")

    def test_the_delivered_file_as_the_wrong_type_is_unproven(self):
        got = self.verdict([dict(self.user(), type="Project")])
        self.assertEqual(got["reason"], "delivery_unproven")

    def test_a_file_outside_the_scratch_is_contamination_without_its_path(self):
        outside = self.root.parent / "real-home" / ".claude" / "CLAUDE.md"
        got = self.verdict([self.user(), {"path": str(outside), "type": "User",
                                          "content": "the real guidance"}])
        self.assertEqual(got["reason"], "receipt_contaminated")
        self.assertEqual(got["files"][1]["path"], guidance.OUTSIDE)
        self.assertNotIn("real-home", json.dumps(got))

    def test_a_dotdot_path_is_judged_by_where_it_lands(self):
        sneaky = str(self.config) + "/../../elsewhere/CLAUDE.md"
        got = self.verdict([self.user(), {"path": sneaky, "type": "Project", "content": "x"}])
        self.assertEqual(got["reason"], "receipt_contaminated")

    def test_a_second_user_file_is_contamination(self):
        got = self.verdict([self.user(), {"path": str(self.config / "rules" / "x.md"),
                                          "type": "User", "content": "x"}])
        self.assertEqual(got["reason"], "receipt_contaminated")
        self.assertIn("config/rules/x.md", got["detail"])

    def test_a_forbidden_token_anywhere_is_contamination(self):
        got = self.verdict([self.user(), {"path": str(self.ws / "CLAUDE.md"),
                                          "type": "Project",
                                          "content": "The magic word is DECOY-2."}])
        self.assertEqual(got["reason"], "receipt_contaminated")

    def test_managed_policy_memory_is_recorded_not_contamination(self):
        got = self.verdict([self.user(), {"path": "/etc/claude-code/CLAUDE.md",
                                          "type": "Managed", "content": "policy"}])
        self.assertTrue(got["ok"], got)
        self.assertEqual(got["files"][1]["path"], guidance.MANAGED)

    def test_an_in_place_arm_needs_no_token(self):
        got = self.verdict([self.user("deployed guidance")], token=None, forbidden=())
        self.assertTrue(got["ok"], got)

    def test_every_verdict_ingests(self):
        cases = [self.verdict([self.user()]), self.verdict(None),
                 self.verdict([self.user(), {"path": "/x/CLAUDE.md", "type": "User",
                                             "content": "x"}])]
        for got in cases:
            with self.subTest(reason=got["reason"]):
                ingest.check_receipt(got, "summary")

    def test_ingest_refuses_an_absolute_path_or_a_lying_reason(self):
        good = self.verdict([self.user()])
        for bad in (dict(good, files=[dict(good["files"][0], path="/home/x/CLAUDE.md")]),
                    dict(good, files=[dict(good["files"][0], path="config/../x")]),
                    dict(good, reason="delivery_unproven"),
                    dict(good, extra=1)):
            with self.subTest(bad=bad), self.assertRaises(ingest.Rejected):
                ingest.check_receipt(bad, "summary")

    def test_ingest_constants_match_the_harness(self):
        self.assertEqual(ingest.RECEIPT_FILES_MAX, guidance.RECEIPT_FILES_MAX)
        self.assertEqual(set(ingest.RECEIPT_REASONS) - {None}, set(run_eval.RECEIPT_ERRORS))
        self.assertIn("receipt", ingest.SUMMARY_ALLOWED)
        for reason in run_eval.RECEIPT_ERRORS:
            self.assertIn(reason, gates.INFRASTRUCTURE_ERRORS)


class ReadInstructionFilesTests(unittest.TestCase):
    def setUp(self):
        self.projects = Path(tempfile.mkdtemp(prefix="receipt-projects-"))
        self.addCleanup(shutil.rmtree, self.projects, ignore_errors=True)

    def write(self, lines, session="s1", project="-ws"):
        path = self.projects / project / f"{session}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")

    def test_the_first_instructions_entry_is_read_past_torn_lines(self):
        entry = {"type": "attachment", "attachment": {"type": "instructions",
                 "files": [{"path": "/c/CLAUDE.md", "type": "User", "content": "a"}, "junk"]}}
        later = {"type": "attachment", "attachment": {"type": "instructions", "files": []}}
        self.write(['{"type": "user"', '"instructions" not json', json.dumps(entry),
                    json.dumps(later)])
        self.assertEqual(guidance.read_instruction_files(self.projects, "s1"),
                         [{"path": "/c/CLAUDE.md", "type": "User", "content": "a"}])

    def test_no_transcript_or_no_entry_is_none(self):
        self.write([json.dumps({"type": "user"})])
        self.assertIsNone(guidance.read_instruction_files(self.projects, "s1"))
        self.assertIsNone(guidance.read_instruction_files(self.projects, "other"))
        self.assertIsNone(guidance.read_instruction_files(None, "s1"))

    def test_a_session_id_cannot_walk_out(self):
        for bad in ("../s1", "a/b", ".hidden", "", None, 7):
            with self.subTest(bad=bad):
                self.assertIsNone(guidance.read_instruction_files(self.projects, bad))


class RunAgentPersistenceTests(unittest.TestCase):
    """`instructions_receipt` persists the session only on a scratch profile."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="receipt-agent-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.ws, self.config, self.home = (self.root / n for n in ("ws", "config", "home"))
        for path in (self.ws, self.config, self.home):
            path.mkdir()
        (self.config / "CLAUDE.md").write_text("The magic word is TOK-1.\n", encoding="utf-8")
        self.log = self.root / "argv.jsonl"
        patcher = mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                               "XDG_STATE_HOME": str(self.root / "state")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def arm(self, **extra):
        env = {"PATH": os.environ["PATH"], "HOME": str(self.home),
               "CLAUDE_CONFIG_DIR": str(self.config), "FAKE_CLAUDE_ARGV_LOG": str(self.log)}
        return {"name": "with_guidance", "timeout": 60, "setting_sources": "user,project",
                "env_override": env, "session_scratch": str(self.root), **extra}

    def argv(self):
        return [json.loads(line)["argv"] for line in self.log.read_text().splitlines()]

    def test_a_receipt_arm_persists_and_returns_what_its_session_loaded(self):
        out = run_eval.run_agent(self.ws, "do it", self.arm(instructions_receipt=True))
        self.assertNotIn("error", out, out)
        (argv,) = self.argv()
        self.assertNotIn("--no-session-persistence", argv)
        self.assertEqual(out["instructions"], [{
            "path": str(self.config / "CLAUDE.md"), "type": "User",
            "content": "The magic word is TOK-1."}])
        self.assertNotIn("instructions", json.dumps(out["raw"]))

    def test_any_other_arm_keeps_no_persistence_and_has_no_receipt(self):
        out = run_eval.run_agent(self.ws, "do it", self.arm())
        self.assertNotIn("error", out, out)
        (argv,) = self.argv()
        self.assertIn("--no-session-persistence", argv)
        self.assertNotIn("instructions", out)
        self.assertFalse((self.config / "projects").exists())


class GuidanceRunReceiptTests(unittest.TestCase):
    """A whole guidance run through main(), the fake CLI and the real hook."""

    TOKEN, DECOY = t97.TestIssue97.TOKEN, t97.TestIssue97.DECOY
    _guidance_fixture = t97.TestIssue97._guidance_fixture
    _run_main = t97.TestIssue97._run_main
    _summary = t97.TestIssue97._summary
    _only_run_dir = staticmethod(t97.TestIssue97._only_run_dir)
    _checkout = t97.TestIssue97._checkout
    _skip_without_real_hook = t97.TestIssue97._skip_without_real_hook

    def run_pair(self, env=None, **overrides):
        tmp = Path(tempfile.mkdtemp(prefix="receipt-run-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        self._skip_without_real_hook(root)
        log = tmp / "argv.jsonl"
        eval_dir = self._guidance_fixture(tmp, env={
            "FAKE_CLAUDE_MODE": "guidance_probe", "FAKE_CLAUDE_ARGV_LOG": str(log),
            **(env or {})}, **overrides)
        results = tmp / "results"
        rc, out = self._run_main([eval_dir, "--arm", "both", "--guidance", root,
                                  "--results-dir", results, "--no-judge"])
        calls = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
        return rc, out, results, calls

    def summaries(self, results):
        return {arm: self._summary(results, "guidance/alpha", arm)
                for arm in ("with_guidance", "without_guidance")}

    def test_both_arms_carry_a_passing_receipt_and_still_score(self):
        rc, out, results, _ = self.run_pair()
        self.assertEqual(rc, 0, out)
        for arm, doc in self.summaries(results).items():
            with self.subTest(arm=arm):
                self.assertTrue(doc["receipt"]["ok"], doc["receipt"])
                self.assertIn({"path": "config/CLAUDE.md", "memory_type": "User"},
                              [{k: f[k] for k in ("path", "memory_type")}
                               for f in doc["receipt"]["files"]])
                self.assertIsNotNone(doc["objective_checks"])
                path = self._only_run_dir(results, "guidance/alpha") / arm / "summary.json"
                ingest.check_summary(doc, "summary", ingest.parse_result_path(
                    path.relative_to(results).as_posix()))
        self.assertIn("receipt ok", out + (self._only_run_dir(
            results, "guidance/alpha") / "report.md").read_text(encoding="utf-8"))

    def test_an_arm_whose_session_wrote_no_entry_is_inconclusive(self):
        rc, out, results, _ = self.run_pair({"FAKE_CLAUDE_NO_INSTRUCTIONS": "1"})
        self.assertEqual(rc, 2, out)
        for arm, doc in self.summaries(results).items():
            with self.subTest(arm=arm):
                self.assertEqual(doc["error"]["type"], "delivery_unproven")
                self.assertIsNone(doc["objective_checks"])
                self.assertIsNone(doc["judge"])
        self.assertIn("INCONCLUSIVE with_guidance (mode section): receipt", out)

    def test_memory_from_outside_the_scratch_is_contamination(self):
        extra = json.dumps([{"path": "/nonexistent-home/.claude/CLAUDE.md",
                             "type": "User", "content": "ambient guidance"}])
        rc, out, results, _ = self.run_pair({"FAKE_CLAUDE_EXTRA_INSTRUCTIONS": extra})
        self.assertEqual(rc, 2, out)
        for doc in self.summaries(results).values():
            self.assertEqual(doc["error"]["type"], "receipt_contaminated")
            self.assertNotIn("nonexistent-home", json.dumps(doc))

    def test_guard_proof_receipt_skips_the_paid_probe(self):
        rc, out, results, calls = self.run_pair(guard={"proof": "receipt"})
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(calls), 2, "one agent call per arm and no probe")
        for doc in self.summaries(results).values():
            self.assertEqual(doc["guard"], {"ok": True, "skipped": "receipt"})
            self.assertTrue(doc["receipt"]["ok"])
        _, _, _, probed = self.run_pair()
        self.assertEqual(len(probed), 4, "the default still probes each arm")

    def test_an_unknown_guard_proof_is_a_configuration_error(self):
        rc, out, _, calls = self.run_pair(guard={"proof": "vibes"})
        self.assertEqual(rc, 2, out)
        self.assertIn("guard.proof", out)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
