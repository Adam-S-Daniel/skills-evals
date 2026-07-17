#!/usr/bin/env python3
"""Test suite for the skills-evals harness.

Hermetic: no real `claude` invocation (CLAUDE_BIN always points at
test/fake-claude), no network, no writes into the repo's real results/ dir.

Run: python3 test/run_tests.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
HARNESS_DIR = REPO_ROOT / "harness"
FAKE_CLAUDE = TEST_DIR / "fake-claude"
FAKE_REGISTRY = TEST_DIR / "fixtures" / "fake_registry"
FAKE_REGISTRY_LEGACY = TEST_DIR / "fixtures" / "fake_registry_legacy"
EVAL_DIR = REPO_ROOT / "evals" / "pin-actions-to-sha"
CANARY_DIR = REPO_ROOT / "evals" / "guidance-bridge-canary"

sys.path.insert(0, str(HARNESS_DIR))
import run_eval  # noqa: E402
from scorers import judge, objective  # noqa: E402


def _fake_sha(seed: int) -> str:
    """A 40-hex-char string — valid per objective.SHA_RE, not a real commit."""
    return f"{seed:040x}"


class WithSkillInstallTests(unittest.TestCase):
    """Skill-dir resolution must work against both registry layouts:
    plugins/<bundle>/skills/<skill>/ where a bundle holds several skills
    (FAKE_REGISTRY), and the legacy plugins/<skill>/skills/<skill>/ where the
    plugin dir is named after its one skill (FAKE_REGISTRY_LEGACY).
    """

    def test_copies_skill_dir_bundle_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            arm = {"name": "with_skill", "skill": "pin-actions-to-sha",
                  "registry": FAKE_REGISTRY, "timeout": 30}
            with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                              "FAKE_CLAUDE_MODE": "agent"}):
                result = run_eval.run_agent(workspace, "pin things", arm)
            self.assertNotIn("error", result)
            skill_md = workspace / ".claude" / "skills" / "pin-actions-to-sha" / "SKILL.md"
            self.assertTrue(skill_md.is_file())

    def test_copies_skill_dir_legacy_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            arm = {"name": "with_skill", "skill": "pin-actions-to-sha",
                  "registry": FAKE_REGISTRY_LEGACY, "timeout": 30}
            with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                              "FAKE_CLAUDE_MODE": "agent"}):
                result = run_eval.run_agent(workspace, "pin things", arm)
            self.assertNotIn("error", result)
            skill_md = workspace / ".claude" / "skills" / "pin-actions-to-sha" / "SKILL.md"
            self.assertTrue(skill_md.is_file())

    def test_selects_correct_skill_among_multiple_bundles(self):
        # FAKE_REGISTRY has two bundles — gha-tools/skills/pin-actions-to-sha and
        # misc-tools/skills/other-skill — proving the glob lands each skill name
        # in its own bundle rather than grabbing whichever bundle sorts first.
        for skill, bundle in (("pin-actions-to-sha", "gha-tools"),
                              ("other-skill", "misc-tools")):
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp) / "ws"
                workspace.mkdir()
                arm = {"name": "with_skill", "skill": skill,
                      "registry": FAKE_REGISTRY, "timeout": 30}
                with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                                  "FAKE_CLAUDE_MODE": "agent"}):
                    result = run_eval.run_agent(workspace, "pin things", arm)
                self.assertNotIn("error", result)
                skill_md = workspace / ".claude" / "skills" / skill / "SKILL.md"
                self.assertTrue(skill_md.is_file())
                self.assertIn(bundle, skill_md.read_text(encoding="utf-8"))

    def test_multiple_matches_pick_first_sorted(self):
        # Not a registry state that should ever occur (a skill name should be
        # unique across bundles), but resolution must be deterministic if it
        # ever did rather than depending on filesystem enumeration order.
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry"
            for bundle in ("zzz-bundle", "aaa-bundle"):
                skill_dir = registry / "plugins" / bundle / "skills" / "dup-skill"
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(f"from {bundle}\n", encoding="utf-8")

            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            arm = {"name": "with_skill", "skill": "dup-skill",
                  "registry": registry, "timeout": 30}
            with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                              "FAKE_CLAUDE_MODE": "agent"}):
                result = run_eval.run_agent(workspace, "pin things", arm)
            self.assertNotIn("error", result)
            content = (workspace / ".claude" / "skills" / "dup-skill" / "SKILL.md").read_text(
                encoding="utf-8")
            # "aaa-bundle" sorts before "zzz-bundle" lexicographically.
            self.assertEqual(content, "from aaa-bundle\n")

    def test_stray_file_at_match_path_errors_cleanly(self):
        # A plain file sitting where a skill dir would be (not a real registry
        # state, but not impossible either) must not reach shutil.copytree and
        # crash — it should be filtered out just like a non-existent path.
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry"
            skill_path = registry / "plugins" / "gha-tools" / "skills" / "pin-actions-to-sha"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text("not a directory\n", encoding="utf-8")

            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            arm = {"name": "with_skill", "skill": "pin-actions-to-sha",
                  "registry": registry, "timeout": 30}
            # No CLAUDE_BIN mock needed: run_agent must fail before any subprocess call.
            result = run_eval.run_agent(workspace, "pin things", arm)
            self.assertIn("error", result)
            self.assertEqual(result["error"], "skill_not_found")

    def test_missing_skill_errors_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            arm = {"name": "with_skill", "skill": "does-not-exist",
                  "registry": FAKE_REGISTRY, "timeout": 30}
            # No CLAUDE_BIN mock needed: run_agent must fail before any subprocess call.
            result = run_eval.run_agent(workspace, "pin things", arm)
            self.assertIn("error", result)
            self.assertIn("does-not-exist", result["detail"])
            self.assertIn(str(FAKE_REGISTRY), result["detail"])
            # Names the plugins/*/skills/<skill> glob pattern that was searched.
            self.assertIn("skills", result["detail"])
            self.assertIn("plugins", result["detail"])


class RunAgentModesTests(unittest.TestCase):
    def _run(self, mode, timeout=30, sleep=None):
        env = {"CLAUDE_BIN": str(FAKE_CLAUDE), "FAKE_CLAUDE_MODE": mode}
        if sleep is not None:
            env["FAKE_CLAUDE_SLEEP"] = str(sleep)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            arm = {"name": "without_skill", "timeout": timeout}
            with mock.patch.dict(os.environ, env):
                return run_eval.run_agent(workspace, "pin things", arm)

    def test_agent_success(self):
        result = self._run("agent")
        self.assertNotIn("error", result)
        self.assertIn("Pinned all GitHub Actions", result["transcript"])
        self.assertEqual(result["num_turns"], 3)
        self.assertEqual(result["cost_usd"], 0.04)
        self.assertIn("usage", result)
        self.assertIn("raw", result)

    def test_agent_error_mode(self):
        result = self._run("agent_error")
        self.assertEqual(result.get("error"), "agent_error")
        self.assertIn("detail", result)
        self.assertIn("raw", result)

    def test_nonzero_exit(self):
        result = self._run("error")
        self.assertEqual(result.get("error"), "nonzero_exit")
        self.assertEqual(result.get("returncode"), 1)
        self.assertIn("simulated CLI failure", result["detail"])

    def test_timeout(self):
        # Short harness timeout + a longer fake sleep forces subprocess.TimeoutExpired
        # quickly rather than actually waiting out a multi-second sleep.
        result = self._run("timeout", timeout=0.3, sleep=2)
        self.assertEqual(result.get("error"), "timeout")


class JudgeScoreTests(unittest.TestCase):
    def _score(self, mode):
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                          "FAKE_CLAUDE_MODE": mode}):
            return judge.score("rubric text", "transcript text", "diff text", timeout=30)

    def test_plain_json(self):
        result = self._score("judge")
        self.assertEqual(result["overall"], 7.5)
        self.assertEqual(len(result["dimensions"]), 4)
        self.assertEqual(result["dimensions"][0]["name"], "Completeness")

    def test_fenced_json(self):
        result = self._score("judge_fenced")
        self.assertEqual(result["overall"], 7.5)
        self.assertEqual(len(result["dimensions"]), 4)

    def test_missing_overall_computes_mean(self):
        result = self._score("judge_no_overall")
        scores = [d["score"] for d in result["dimensions"]]
        self.assertAlmostEqual(result["overall"], sum(scores) / len(scores))

    def test_cli_failure_raises(self):
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                          "FAKE_CLAUDE_MODE": "error"}):
            with self.assertRaises(RuntimeError):
                judge.score("rubric", "transcript", "diff", timeout=30)


class ObjectiveAsymmetryTests(unittest.TestCase):
    """Guards the README-documented asymmetry: pristine seed fails; pinned copy passes."""

    _REPLACEMENTS = {
        "actions/checkout@v4": f"actions/checkout@{_fake_sha(1)} # v4.3.1",
        "actions/setup-node@v4": f"actions/setup-node@{_fake_sha(2)} # v4.0.3",
        "actions/setup-python@v5": f"actions/setup-python@{_fake_sha(3)} # v5.1.1",
        "softprops/action-gh-release@v2": f"softprops/action-gh-release@{_fake_sha(4)} # v2.0.8",
    }

    def _pin_all(self, ws: Path) -> None:
        for path in (ws / ".github" / "workflows").glob("*.y*ml"):
            text = path.read_text(encoding="utf-8")
            for old, new in self._REPLACEMENTS.items():
                text = text.replace(f"uses: {old}", f"uses: {new}")
            path.write_text(text, encoding="utf-8")

    def test_pristine_seed_fails_pinning_check(self):
        fixture = run_eval.load_fixture(EVAL_DIR)
        seed = EVAL_DIR / "seed"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            shutil.copytree(seed, ws)
            results = objective.run_checks(fixture, str(ws), str(seed))
        by_id = {r["id"]: r for r in results}
        self.assertFalse(by_id["all-actions-sha-pinned"]["passed"])

    def test_pinned_copy_passes_all_checks(self):
        fixture = run_eval.load_fixture(EVAL_DIR)
        seed = EVAL_DIR / "seed"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            shutil.copytree(seed, ws)
            self._pin_all(ws)
            results = objective.run_checks(fixture, str(ws), str(seed))
        for r in results:
            self.assertTrue(r["passed"], r["detail"])


class PinnedShaTagCheckTests(unittest.TestCase):
    """pinned_shas_match_tags: parsing/matching logic exercised with injected
    ls-remote data — the network path itself is opt-in (--net-checks) and never
    runs in this hermetic suite.
    """

    SHA = _fake_sha(0xA1)
    OTHER = _fake_sha(0xB2)

    def _ws(self, uses_lines: list[str]) -> Path:
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        wf = ws / ".github" / "workflows"
        wf.mkdir(parents=True)
        body = "jobs:\n  x:\n    steps:\n" + "".join(
            f"      - uses: {u}\n" for u in uses_lines)
        (wf / "ci.yml").write_text(body, encoding="utf-8")
        return ws

    PATTERNS = [".github/workflows/*.yml"]

    def test_skipped_without_network(self):
        ws = self._ws([f"actions/checkout@{self.SHA} # v6.0.0"])
        passed, detail = objective.pinned_shas_match_tags(str(ws), self.PATTERNS)
        self.assertTrue(passed)
        self.assertIn("skipped", detail)
        self.assertIn("1 pinned ref(s) unverified", detail)

    def test_no_pinned_refs_vacuous_pass(self):
        ws = self._ws(["actions/checkout@v4"])  # unpinned: nothing to verify
        passed, detail = objective.pinned_shas_match_tags(
            str(ws), self.PATTERNS,
            ls_remote=lambda url, ver: (self.fail("must not be called"), None))
        self.assertTrue(passed)
        self.assertIn("no SHA-pinned remote refs", detail)

    def test_lightweight_tag_match(self):
        ws = self._ws([f"actions/checkout@{self.SHA} # v6.0.0 (2025-11-20)"])
        refs = {"refs/tags/v6.0.0": self.SHA}
        passed, detail = objective.pinned_shas_match_tags(
            str(ws), self.PATTERNS, ls_remote=lambda url, ver: (refs, None))
        self.assertTrue(passed, detail)
        self.assertIn("1 verified, 0 mismatched, 0 unverifiable", detail)

    def test_annotated_tag_peel_match(self):
        # Annotated tag: the ref names a tag object; the commit is on the peel.
        ws = self._ws([f"actions/setup-python@{self.SHA} # v6.1.0"])
        refs = {"refs/tags/v6.1.0": self.OTHER,
                "refs/tags/v6.1.0^{}": self.SHA}
        passed, detail = objective.pinned_shas_match_tags(
            str(ws), self.PATTERNS, ls_remote=lambda url, ver: (refs, None))
        self.assertTrue(passed, detail)

    def test_bare_version_comment_matches_v_prefixed_tag(self):
        ws = self._ws([f"actions/checkout@{self.SHA} # 6.0.0"])
        refs = {"refs/tags/v6.0.0": self.SHA}
        passed, detail = objective.pinned_shas_match_tags(
            str(ws), self.PATTERNS, ls_remote=lambda url, ver: (refs, None))
        self.assertTrue(passed, detail)

    def test_mismatch_fails(self):
        ws = self._ws([f"actions/checkout@{self.SHA} # v6.0.0"])
        refs = {"refs/tags/v6.0.0": self.OTHER,
                "refs/tags/v6.0.0^{}": self.OTHER}
        passed, detail = objective.pinned_shas_match_tags(
            str(ws), self.PATTERNS, ls_remote=lambda url, ver: (refs, None))
        self.assertFalse(passed)
        self.assertIn("1 mismatched", detail)
        self.assertIn("ci.yml", detail)

    def test_claimed_tag_missing_upstream_fails(self):
        # Wildcard hit a sibling tag but not the claimed one: the claim is wrong.
        ws = self._ws([f"actions/checkout@{self.SHA} # v6.0.0"])
        refs = {"refs/tags/v6.0.1": self.SHA}
        passed, detail = objective.pinned_shas_match_tags(
            str(ws), self.PATTERNS, ls_remote=lambda url, ver: (refs, None))
        self.assertFalse(passed)
        self.assertIn("1 mismatched", detail)

    def test_ls_remote_failure_is_unverifiable_not_failure(self):
        ws = self._ws([
            f"actions/checkout@{self.SHA} # v6.0.0",
            f"actions/setup-node@{self.OTHER} # v6.0.0",
        ])
        def flaky(url, ver):
            if "setup-node" in url:
                return None, "could not resolve host"
            return {"refs/tags/v6.0.0": self.SHA}, None
        passed, detail = objective.pinned_shas_match_tags(
            str(ws), self.PATTERNS, ls_remote=flaky)
        self.assertTrue(passed, detail)
        self.assertIn("1 verified, 0 mismatched, 1 unverifiable", detail)
        self.assertIn("could not resolve host", detail)

    def test_repo_url_strips_action_subpath(self):
        ws = self._ws([f"github/codeql-action/init@{self.SHA} # v3.28.0"])
        seen = []
        def capture(url, ver):
            seen.append((url, ver))
            return {"refs/tags/v3.28.0": self.SHA}, None
        passed, _ = objective.pinned_shas_match_tags(
            str(ws), self.PATTERNS, ls_remote=capture)
        self.assertTrue(passed)
        self.assertEqual(seen, [("https://github.com/github/codeql-action", "v3.28.0")])

    def test_run_checks_stays_hermetic_by_default(self):
        # The real fixture now carries the network-dependent check; without
        # allow_network it must report as skipped-pass, never touch the network.
        fixture = run_eval.load_fixture(EVAL_DIR)
        ws = self._ws([f"actions/checkout@{self.SHA} # v6.0.0"])
        results = objective.run_checks(fixture, str(ws), str(EVAL_DIR / "seed"))
        by_id = {r["id"]: r for r in results}
        self.assertIn("pinned-shas-match-tags", by_id)
        self.assertTrue(by_id["pinned-shas-match-tags"]["passed"])
        self.assertIn("skipped", by_id["pinned-shas-match-tags"]["detail"])


class EndToEndTests(unittest.TestCase):
    def test_both_arms_produce_summary_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            results_dir = Path(tmp) / "results"
            env = os.environ.copy()
            env["CLAUDE_BIN"] = str(FAKE_CLAUDE)
            env["FAKE_CLAUDE_MODE"] = "agent_and_judge"
            env["AGENTSKILLS_DIR"] = str(FAKE_REGISTRY)
            cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(EVAL_DIR),
                  "--arm", "both", "--results-dir", str(results_dir),
                  "--timeout", "30"]
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  env=env, cwd=str(REPO_ROOT))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            skill_dir = results_dir / "pin-actions-to-sha"
            self.assertTrue(skill_dir.is_dir())
            run_dirs = list(skill_dir.iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            report = (run_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("pin-actions-to-sha", report)
            self.assertIn("with_skill", report)
            self.assertIn("without_skill", report)

            for arm in ("with_skill", "without_skill"):
                summary_path = run_dir / arm / "summary.json"
                self.assertTrue(summary_path.is_file())
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                self.assertIsNone(summary["error"])
                self.assertIsNotNone(summary["agent"])
                self.assertIsNotNone(summary["objective_checks"])
                self.assertIsNotNone(summary["judge"])
                self.assertNotIn("error", summary["judge"])
                raw_path = run_dir / arm / "transcripts" / "raw.json"
                self.assertTrue(raw_path.is_file())

            # Never pollutes the real repo results/ dir.
            self.assertFalse((REPO_ROOT / "results" / "pin-actions-to-sha").exists())

    def test_objective_only_unchanged_against_pristine_seed(self):
        cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(EVAL_DIR),
              "--arm", "objective-only"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["skill"], "pin-actions-to-sha")
        self.assertEqual(payload["arm"], "objective-only")
        by_id = {c["id"]: c for c in payload["checks"]}
        self.assertFalse(by_id["all-actions-sha-pinned"]["passed"])


class CanaryTests(unittest.TestCase):
    """harness/run_canary.py exercised against test/fake-claude's canary_* modes."""

    def _run(self, mode, extra_args=None):
        results_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, results_dir, ignore_errors=True)
        env = os.environ.copy()
        env["CLAUDE_BIN"] = str(FAKE_CLAUDE)
        env["FAKE_CLAUDE_MODE"] = mode
        cmd = [sys.executable, str(HARNESS_DIR / "run_canary.py"), str(CANARY_DIR),
              "--results-dir", str(results_dir), "--timeout", "30"]
        if extra_args:
            cmd += extra_args
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              env=env, cwd=str(REPO_ROOT))
        return proc, results_dir

    def _summary(self, results_dir):
        fixture_dir = results_dir / "guidance-bridge-canary"
        run_dirs = list(fixture_dir.iterdir())
        self.assertEqual(len(run_dirs), 1)
        run_dir = run_dirs[0]
        report = (run_dir / "report.md").read_text(encoding="utf-8")
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        return report, summary

    def test_canary_loader(self):
        proc, results_dir = self._run("canary_loader")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS bridge", proc.stdout)
        self.assertIn("PASS no-bridge", proc.stdout)
        self.assertIn("PASS fence", proc.stdout)
        report, summary = self._summary(results_dir)
        self.assertIn("fake-claude 0.0.0 (hermetic test stub)", report)
        self.assertEqual(len(summary["legs"]), 3)
        self.assertTrue(all(leg["passed"] for leg in summary["legs"]))

    def test_canary_blind(self):
        proc, results_dir = self._run("canary_blind")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("FAIL bridge", proc.stdout)
        self.assertIn("FLUMMOX-7291", proc.stdout)
        self.assertIn("visible", proc.stdout)
        self.assertIn("PASS no-bridge", proc.stdout)
        self.assertIn("PASS fence", proc.stdout)

    def test_canary_forager(self):
        proc, results_dir = self._run("canary_forager")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("FAIL no-bridge", proc.stdout)
        self.assertIn("FAIL fence", proc.stdout)
        self.assertIn("PASS bridge", proc.stdout)

    def test_runner_level_error(self):
        proc, results_dir = self._run("error")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("nonzero_exit", proc.stdout)

    def test_canary_loader_with_subagent(self):
        proc, results_dir = self._run("canary_loader", extra_args=["--subagent"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        _, summary = self._summary(results_dir)
        self.assertEqual(len(summary["legs"]), 4)
        names = {leg["name"] for leg in summary["legs"]}
        self.assertIn("bridge-subagent", names)
        self.assertTrue(all(leg["passed"] for leg in summary["legs"]))


if __name__ == "__main__":
    unittest.main()
