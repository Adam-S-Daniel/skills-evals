#!/usr/bin/env python3
"""Test suite for the skills-evals harness.

Hermetic: no real `claude` invocation (CLAUDE_BIN always points at
test/fake-claude), no network, no writes into the repo's real results/ dir.

Run: python3 test/run_tests.py
"""

from __future__ import annotations

import argparse
import itertools
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

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
HARNESS_DIR = REPO_ROOT / "harness"
FAKE_CLAUDE = TEST_DIR / "fake-claude"
FAKE_REGISTRY = TEST_DIR / "fixtures" / "fake_registry"
FAKE_REGISTRY_LEGACY = TEST_DIR / "fixtures" / "fake_registry_legacy"
EVAL_DIR = REPO_ROOT / "evals" / "workflow-path-audit"
ELEVATION_DIR = REPO_ROOT / "evals" / "windows-elevation-from-wsl"
CANARY_DIR = REPO_ROOT / "evals" / "guidance-bridge-canary"
ADRS_EXISTING_DIR = REPO_ROOT / "evals" / "writing-adrs" / "existing-convention"
ADRS_BOOTSTRAP_DIR = REPO_ROOT / "evals" / "writing-adrs" / "bootstrap"

sys.path.insert(0, str(HARNESS_DIR))
import run_eval  # noqa: E402
from scorers import judge, objective  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import make_badge  # noqa: E402


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
            arm = {"name": "with_skill", "skill": "fixture-primary-skill",
                  "registry": FAKE_REGISTRY, "timeout": 30}
            with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                              "FAKE_CLAUDE_MODE": "agent"}):
                result = run_eval.run_agent(workspace, "audit the workflows", arm)
            self.assertNotIn("error", result)
            skill_md = (workspace / ".claude" / "skills"
                        / "fixture-primary-skill" / "SKILL.md")
            self.assertTrue(skill_md.is_file())

    def test_copies_skill_dir_legacy_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            arm = {"name": "with_skill", "skill": "fixture-solo-skill",
                  "registry": FAKE_REGISTRY_LEGACY, "timeout": 30}
            with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                              "FAKE_CLAUDE_MODE": "agent"}):
                result = run_eval.run_agent(workspace, "audit the workflows", arm)
            self.assertNotIn("error", result)
            skill_md = (workspace / ".claude" / "skills"
                        / "fixture-solo-skill" / "SKILL.md")
            self.assertTrue(skill_md.is_file())

    def test_selects_correct_skill_among_multiple_bundles(self):
        # FAKE_REGISTRY has two bundles — gha-tools/skills/fixture-primary-skill
        # and misc-tools/skills/other-skill — proving the glob lands each skill
        # name in its own bundle rather than grabbing whichever bundle sorts first.
        for skill, bundle in (("fixture-primary-skill", "gha-tools"),
                              ("other-skill", "misc-tools")):
            with tempfile.TemporaryDirectory() as tmp:
                workspace = Path(tmp) / "ws"
                workspace.mkdir()
                arm = {"name": "with_skill", "skill": skill,
                      "registry": FAKE_REGISTRY, "timeout": 30}
                with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                                  "FAKE_CLAUDE_MODE": "agent"}):
                    result = run_eval.run_agent(workspace, "audit the workflows", arm)
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
                result = run_eval.run_agent(workspace, "audit the workflows", arm)
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
            skill_path = registry / "plugins" / "gha-tools" / "skills" / "fixture-primary-skill"
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text("not a directory\n", encoding="utf-8")

            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            arm = {"name": "with_skill", "skill": "fixture-primary-skill",
                  "registry": registry, "timeout": 30}
            # No CLAUDE_BIN mock needed: run_agent must fail before any subprocess call.
            result = run_eval.run_agent(workspace, "audit the workflows", arm)
            self.assertIn("error", result)
            self.assertEqual(result["error"], "skill_not_found")

    def test_missing_skill_errors_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            arm = {"name": "with_skill", "skill": "does-not-exist",
                  "registry": FAKE_REGISTRY, "timeout": 30}
            # No CLAUDE_BIN mock needed: run_agent must fail before any subprocess call.
            result = run_eval.run_agent(workspace, "audit the workflows", arm)
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
                return run_eval.run_agent(workspace, "audit the workflows", arm)

    def test_agent_success(self):
        result = self._run("agent")
        self.assertNotIn("error", result)
        self.assertIn("Filtered every pull_request/push workflow", result["transcript"])
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

    # fake-claude's canned judge response, for the weighting arithmetic below:
    #   Completeness 8, Correctness 9, Restraint 7, Communication 6
    # and a self-reported "overall" of 7.5 (which is NOT the mean of those —
    # that is the point: the model is not trusted to do the arithmetic).

    def _score_weighted(self, weights, mode="judge"):
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                          "FAKE_CLAUDE_MODE": mode}):
            return judge.score("rubric text", "transcript text", "diff text",
                               timeout=30, weights=weights)

    def test_weights_recompute_overall_and_ignore_self_report(self):
        # Keys are matched case-insensitively and whitespace-trimmed.
        # (8*0.5 + 9*0.3 + 7*0.2 + 6*1.0) / (0.5+0.3+0.2+1.0)
        #   = (4 + 2.7 + 1.4 + 6) / 2.0 = 7.05
        result = self._score_weighted({"COMPLETENESS": 0.5, "correctness": 0.3,
                                       "  restraint  ": 0.2, "communication": 1.0})
        self.assertAlmostEqual(result["overall"], 7.05)
        self.assertNotEqual(result["overall"], 7.5)  # the judge's own number

    def test_unmentioned_dimension_keeps_weight_one(self):
        # Only Completeness is weighted; the other three keep 1.0 rather than
        # being dropped. (8*0.5 + 9 + 7 + 6) / (0.5 + 3) = 26 / 3.5
        result = self._score_weighted({"completeness": 0.5})
        self.assertAlmostEqual(result["overall"], 26 / 3.5)
        # Silently dropping the unmentioned dimensions would give 8.0.
        self.assertNotAlmostEqual(result["overall"], 8.0)

    def test_weights_apply_when_judge_omitted_its_own_overall(self):
        result = self._score_weighted({"completeness": 0.5},
                                      mode="judge_no_overall")
        self.assertAlmostEqual(result["overall"], 26 / 3.5)

    def test_weights_none_preserves_self_reported_overall(self):
        # The historical path: an explicit weights=None must behave exactly
        # like omitting the argument, self-reported `overall` and all.
        self.assertEqual(self._score_weighted(None)["overall"], 7.5)
        self.assertEqual(self._score_weighted({})["overall"], 7.5)

    def test_zero_sum_weights_fall_back_to_unweighted_mean(self):
        # Guards the divide-by-zero: all-zero weights degrade to the plain
        # mean (7.5) rather than reporting a misleading 0.0.
        result = self._score_weighted({"completeness": 0, "correctness": 0,
                                       "restraint": 0, "communication": 0})
        self.assertAlmostEqual(result["overall"], (8 + 9 + 7 + 6) / 4)

    def test_unusable_weight_value_falls_back_to_one(self):
        # A YAML slip must not blank the judge for the whole run.
        result = self._score_weighted({"completeness": "half", "correctness": None,
                                       "restraint": -3, "communication": 1.0})
        self.assertAlmostEqual(result["overall"], (8 + 9 + 7 + 6) / 4)


class ObjectiveAsymmetryTests(unittest.TestCase):
    """Guards the README-documented asymmetry: the pristine seed fails; a
    correctly audited copy passes every check.

    The "correct" edits below are applied by anchored replacement, and each
    anchor is asserted present first — so if the seed's workflows drift, this
    test fails loudly instead of quietly measuring nothing.
    """

    # docs-site.yml consumes mkdocs.yml + docs/ and nothing else. Written with
    # a YAML anchor/alias on purpose: an agent may legitimately share one list
    # between two events, and the scorer parses YAML rather than scanning lines.
    _DOCS_ON = ("on:\n  pull_request:\n  push:\n    branches: [main]\n",
                "on:\n"
                "  pull_request:\n"
                "    paths: &docs-paths\n"
                "      - docs/**\n"
                "      - mkdocs.yml\n"
                "      - .github/workflows/docs-site.yml\n"
                "  push:\n"
                "    branches: [main]\n"
                "    paths: *docs-paths\n")

    # deploy.yml ships src/ plus the runtime dependency set.
    _DEPLOY_ON = ("on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n",
                  "on:\n"
                  "  push:\n"
                  "    branches: [main]\n"
                  "    paths:\n"
                  "      - src/**\n"
                  "      - package.json\n"
                  "      - package-lock.json\n"
                  "      - scripts/deploy.sh\n"
                  "      - .github/workflows/deploy.yml\n"
                  "  workflow_dispatch:\n")

    # tests.yml carries a REQUIRED check, so it keeps firing on every event and
    # moves the salience decision inside itself instead.
    _TESTS_STEPS = ("      - run: npm ci\n      - run: npm test\n",
                    "      - name: Detect salient changes\n"
                    "        id: salient\n"
                    '        run: echo "run=true" >> "$GITHUB_OUTPUT"\n'
                    "      - if: steps.salient.outputs.run == 'true'\n"
                    "        run: npm ci\n"
                    "      - if: steps.salient.outputs.run == 'true'\n"
                    "        run: npm test\n")

    def _replace(self, path: Path, old: str, new: str) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"{path.name}: anchor drifted out of the seed")
        path.write_text(text.replace(old, new), encoding="utf-8")

    def _audit_all(self, ws: Path) -> None:
        workflows = ws / ".github" / "workflows"
        self._replace(workflows / "docs-site.yml", *self._DOCS_ON)
        self._replace(workflows / "deploy.yml", *self._DEPLOY_ON)
        self._replace(workflows / "tests.yml", *self._TESTS_STEPS)

    def _run(self, audited: bool) -> dict:
        fixture = run_eval.load_fixture(EVAL_DIR)
        seed = EVAL_DIR / "seed"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            shutil.copytree(seed, ws)
            if audited:
                self._audit_all(ws)
            results = objective.run_checks(fixture, str(ws), str(seed))
        return {r["id"]: r for r in results}

    def test_pristine_seed_fails_the_routing_checks(self):
        by_id = self._run(audited=False)
        for check_id in ("docs-change-routes-correctly",
                         "source-change-routes-correctly",
                         "lockfile-change-routes-to-installers",
                         "prose-change-runs-nothing-but-the-required-check",
                         "required-check-always-fires-and-gates-internally"):
            self.assertFalse(by_id[check_id]["passed"], by_id[check_id]["detail"])

    def test_pristine_seed_passes_the_restraint_checks(self):
        # The restraint checks can only be broken by a careless agent, so they
        # must start out green — otherwise a failure says nothing about the arm.
        by_id = self._run(audited=False)
        for check_id in ("workflows-still-parse", "event-only-workflows-unfiltered",
                         "ruleset-unchanged"):
            self.assertTrue(by_id[check_id]["passed"], by_id[check_id]["detail"])

    def test_audited_copy_passes_all_checks(self):
        for check_id, result in self._run(audited=True).items():
            self.assertTrue(result["passed"], f"{check_id}: {result['detail']}")


class WorkflowPathFilterTests(unittest.TestCase):
    """The path-filter primitives, exercised directly against tiny workspaces."""

    PATTERNS = [".github/workflows/*.yml"]

    def _ws(self, files: dict[str, str]) -> Path:
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        for rel, body in files.items():
            path = ws / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return ws

    DEFAULT_JOB = ("jobs:\n  build:\n    runs-on: ubuntu-latest\n"
                   "    steps:\n      - run: true\n")

    def _wf(self, on_block: str, jobs: str | None = None) -> str:
        return on_block + (jobs or self.DEFAULT_JOB)

    # -- glob semantics ----------------------------------------------------

    def test_single_star_does_not_cross_a_slash(self):
        self.assertTrue(objective._glob_to_regex("docs/*.md").match("docs/a.md"))
        self.assertFalse(objective._glob_to_regex("docs/*.md").match("docs/sub/a.md"))

    def test_double_star_crosses_slashes(self):
        self.assertTrue(objective._glob_to_regex("docs/**").match("docs/sub/a.md"))

    def test_question_mark_matches_one_non_slash_character(self):
        self.assertTrue(objective._glob_to_regex("v?.md").match("v1.md"))
        self.assertFalse(objective._glob_to_regex("v?.md").match("v11.md"))

    def test_bare_directory_name_does_not_match_its_contents(self):
        # Faithful to GitHub: `docs` matches a file literally named `docs`, so a
        # filter written that way genuinely does not filter and must not pass.
        self.assertFalse(objective._glob_to_regex("docs").match("docs/a.md"))

    def test_negation_is_order_sensitive(self):
        self.assertFalse(objective._pattern_matches(["docs/**", "!docs/draft/**"],
                                                    "docs/draft/a.md"))
        self.assertTrue(objective._pattern_matches(["docs/**", "!docs/draft/**",
                                                    "docs/draft/keep.md"],
                                                   "docs/draft/keep.md"))

    # -- `on:` block shapes ------------------------------------------------

    def test_on_key_parsed_as_yaml_boolean_is_still_found(self):
        # PyYAML resolves the bare key `on` to True (YAML 1.1); a scorer that
        # only looked up the string key would see every workflow as untriggered.
        import yaml
        doc = yaml.safe_load("on:\n  push:\n    paths: [src/**]\n")
        self.assertNotIn("on", doc)
        self.assertEqual(set(objective._on_events(doc)), {"push"})

    def test_scalar_and_list_on_blocks(self):
        import yaml
        self.assertEqual(set(objective._on_events(yaml.safe_load("on: push\n"))),
                         {"push"})
        self.assertEqual(
            set(objective._on_events(yaml.safe_load("on: [push, pull_request]\n"))),
            {"push", "pull_request"})

    # -- trigger decisions -------------------------------------------------

    def _routes(self, on_block: str, changeset: list[str], expect: bool):
        ws = self._ws({".github/workflows/w.yml": self._wf(on_block)})
        key = "expect_triggered" if expect else "expect_skipped"
        passed, detail = objective.changeset_triggers(
            str(ws), self.PATTERNS, changeset=changeset,
            **{key: [".github/workflows/w.yml"]})
        self.assertTrue(passed, detail)

    def test_unfiltered_workflow_always_triggers(self):
        self._routes("on:\n  pull_request:\n", ["README.md"], True)

    def test_positive_paths_filter_skips_a_non_matching_change(self):
        self._routes("on:\n  pull_request:\n    paths: [src/**]\n", ["README.md"], False)
        self._routes("on:\n  pull_request:\n    paths: [src/**]\n", ["src/a.js"], True)

    def test_paths_ignore_skips_only_when_every_file_matches(self):
        on = "on:\n  push:\n    paths-ignore: ['**.md']\n"
        self._routes(on, ["README.md", "docs/a.md"], False)
        self._routes(on, ["README.md", "src/a.js"], True)

    def test_catch_all_filter_still_triggers_on_prose(self):
        # The gaming path a presence-only check would let through.
        self._routes("on:\n  pull_request:\n    paths: ['**']\n", ["README.md"], True)

    def test_filter_on_a_non_path_event_does_not_gate_anything(self):
        # A filter under `schedule:` is inert on GitHub; the workflow has no
        # path-filtered event at all, so it never fires on a code change.
        self._routes("on:\n  schedule:\n    - cron: '0 3 * * *'\n", ["src/a.js"], False)

    def test_a_named_workflow_that_is_missing_fails(self):
        ws = self._ws({".github/workflows/other.yml": self._wf("on:\n  push:\n")})
        passed, detail = objective.changeset_triggers(
            str(ws), self.PATTERNS, changeset=["src/a.js"],
            expect_triggered=[".github/workflows/w.yml"])
        self.assertFalse(passed)
        self.assertIn("not found", detail)

    def test_an_unnamed_extra_workflow_is_ignored(self):
        ws = self._ws({".github/workflows/w.yml": self._wf("on:\n  push:\n"),
                       ".github/workflows/extra.yml": self._wf("on:\n  push:\n")})
        passed, _ = objective.changeset_triggers(
            str(ws), self.PATTERNS, changeset=["src/a.js"],
            expect_triggered=[".github/workflows/w.yml"])
        self.assertTrue(passed)

    # -- required checks ---------------------------------------------------

    RULESET = json.dumps({"rules": [
        {"type": "required_status_checks",
         "parameters": {"required_status_checks": [{"context": "unit-tests"}]}}]})

    GATED_JOB = ("jobs:\n  unit-tests:\n    runs-on: ubuntu-latest\n    steps:\n"
                 "      - id: salient\n        run: echo run=true >> $GITHUB_OUTPUT\n"
                 "      - if: steps.salient.outputs.run == 'true'\n"
                 "        run: npm test\n")
    UNGATED_JOB = ("jobs:\n  unit-tests:\n    runs-on: ubuntu-latest\n    steps:\n"
                   "      - run: npm test\n")

    def _required_ws(self, on_block: str, jobs: str) -> Path:
        return self._ws({".github/rulesets/main.json": self.RULESET,
                         ".github/workflows/tests.yml": on_block + jobs})

    def test_required_check_unfiltered_and_gated_passes(self):
        ws = self._required_ws("on:\n  pull_request:\n", self.GATED_JOB)
        passed, detail = objective.required_checks_early_skip(str(ws), self.PATTERNS)
        self.assertTrue(passed, detail)

    def test_required_check_with_a_workflow_level_filter_fails(self):
        ws = self._required_ws("on:\n  pull_request:\n    paths: [src/**]\n",
                               self.GATED_JOB)
        passed, detail = objective.required_checks_early_skip(str(ws), self.PATTERNS)
        self.assertFalse(passed)
        self.assertIn("can go missing", detail)

    def test_required_check_without_a_gate_fails(self):
        ws = self._required_ws("on:\n  pull_request:\n", self.UNGATED_JOB)
        passed, detail = objective.required_checks_early_skip(str(ws), self.PATTERNS)
        self.assertFalse(passed)
        self.assertIn("no early-skip gate", detail)

    def test_required_context_matched_by_job_name_not_just_job_id(self):
        jobs = self.GATED_JOB.replace(
            "  unit-tests:\n    runs-on",
            "  test:\n    name: unit-tests\n    runs-on")
        ws = self._required_ws("on:\n  pull_request:\n", jobs)
        passed, detail = objective.required_checks_early_skip(str(ws), self.PATTERNS)
        self.assertTrue(passed, detail)

    def test_a_deleted_required_workflow_fails(self):
        ws = self._ws({".github/rulesets/main.json": self.RULESET,
                       ".github/workflows/other.yml": self._wf("on:\n  push:\n")})
        passed, detail = objective.required_checks_early_skip(str(ws), self.PATTERNS)
        self.assertFalse(passed)
        self.assertIn("unit-tests", detail)

    def test_no_ruleset_means_nothing_to_assert(self):
        ws = self._ws({".github/workflows/w.yml": self._wf("on:\n  push:\n")})
        passed, detail = objective.required_checks_early_skip(str(ws), self.PATTERNS)
        self.assertTrue(passed)
        self.assertIn("no required status checks", detail)

    # -- restraint ---------------------------------------------------------

    def test_event_only_workflow_with_a_filter_fails(self):
        ws = self._ws({".github/workflows/cron.yml": self._wf(
            "on:\n  schedule:\n    - cron: '0 3 * * *'\n")})
        self.assertTrue(objective.event_only_workflows_unfiltered(
            str(ws), self.PATTERNS)[0])
        ws = self._ws({".github/workflows/cron.yml": self._wf(
            "on:\n  workflow_dispatch:\n    paths: [src/**]\n")})
        passed, detail = objective.event_only_workflows_unfiltered(str(ws), self.PATTERNS)
        self.assertFalse(passed)
        self.assertIn("GitHub ignores", detail)

    def test_files_unchanged_detects_edit_removal_and_addition(self):
        seed = self._ws({".github/rulesets/main.json": "{}\n"})
        patterns = [".github/rulesets/main.json"]

        same = self._ws({".github/rulesets/main.json": "{}\n"})
        self.assertTrue(objective.files_unchanged(str(same), patterns, seed=str(seed))[0])

        edited = self._ws({".github/rulesets/main.json": "{ }\n"})
        passed, detail = objective.files_unchanged(str(edited), patterns, seed=str(seed))
        self.assertFalse(passed)
        self.assertIn("modified", detail)

        removed = self._ws({"README.md": "x\n"})
        passed, detail = objective.files_unchanged(str(removed), patterns, seed=str(seed))
        self.assertFalse(passed)
        self.assertIn("removed", detail)

    def test_unparseable_workflow_fails_a_named_expectation(self):
        ws = self._ws({".github/workflows/w.yml": "on: [\n  bad yaml\n"})
        passed, detail = objective.changeset_triggers(
            str(ws), self.PATTERNS, changeset=["src/a.js"],
            expect_triggered=[".github/workflows/w.yml"])
        self.assertFalse(passed)
        self.assertIn("does not parse", detail)


class AgentEnvTests(unittest.TestCase):
    """A fixture's `env:` block reaches the agent with $WORKSPACE expanded."""

    def test_workspace_and_existing_vars_expand(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"PATH": "/usr/bin", "SKILLS_EVALS_X": "keep"}):
            env = run_eval.agent_env(Path(tmp), {"PATH": "$WORKSPACE/bin:$PATH",
                                                 "PROBE": "$WORKSPACE", "N": 7})
        self.assertEqual(env["PATH"], f"{tmp}/bin:/usr/bin")
        self.assertEqual(env["PROBE"], tmp)
        self.assertEqual(env["N"], "7")
        self.assertEqual(env["SKILLS_EVALS_X"], "keep")  # inherited, not replaced

    def test_no_env_block_is_the_plain_environment_plus_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = run_eval.agent_env(Path(tmp), None)
        self.assertEqual(env["WORKSPACE"], tmp)
        self.assertEqual(env["PATH"], os.environ["PATH"])

    def test_run_agent_passes_the_env_to_the_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "bin").mkdir()
            arm = {"name": "without_skill", "timeout": 30,
                   "env": {"PATH": "$WORKSPACE/bin:$PATH",
                           "SKILLS_EVALS_PROBE": "$WORKSPACE/marker"}}
            with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                              "FAKE_CLAUDE_MODE": "agent_env"}):
                result = run_eval.run_agent(workspace, "probe", arm)
        self.assertNotIn("error", result)
        seen = json.loads(result["transcript"])
        self.assertEqual(seen["probe"], f"{tmp}/marker")
        self.assertTrue(seen["path"].startswith(f"{tmp}/bin:"), seen["path"])
        # Prepended, not replaced: the fake itself only ran because the rest
        # of PATH survived.
        self.assertIn(os.pathsep, seen["path"][len(tmp) + 5:])


class TextMatchCheckTests(unittest.TestCase):
    """file_matches / transcript_matches: regex assertions over content."""

    def _ws(self, files: dict[str, str]) -> Path:
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        for rel, content in files.items():
            path = ws / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return ws

    def test_must_match_and_must_not_match_on_a_present_file(self):
        ws = self._ws({"log": "class=read\nExport-ScheduledTask\nclass=denied\n"})
        self.assertTrue(objective.file_matches(str(ws), ["log"],
                                              must_match=["Export-ScheduledTask"])[0])
        passed, detail = objective.file_matches(str(ws), ["log"], must_match=["Register"])
        self.assertFalse(passed)
        self.assertIn("lacks /Register/", detail)
        passed, detail = objective.file_matches(str(ws), ["log"],
                                                must_not_match=["class=denied"])
        self.assertFalse(passed)
        self.assertIn("contains /class=denied/", detail)

    def test_dotall_pattern_spans_lines_and_multiline_anchors_hold(self):
        ws = self._ws({"log": "class=denied\nx\nclass=denied\n"})
        self.assertFalse(objective.file_matches(
            str(ws), ["log"], must_not_match=["(?s)class=denied.*class=denied"])[0])
        self.assertTrue(objective.file_matches(str(ws), ["log"], must_match=["^x$"])[0])

    def test_a_missing_file_fails_must_match_but_passes_must_not_match(self):
        ws = self._ws({})
        passed, detail = objective.file_matches(str(ws), ["absent.log"], must_match=["x"])
        self.assertFalse(passed)
        self.assertIn("no file matched", detail)
        self.assertTrue(objective.file_matches(str(ws), ["absent.log"],
                                              must_not_match=["x"])[0])

    def test_transcript_none_fails_and_text_is_matched(self):
        passed, detail = objective.transcript_matches("/nonexistent", [], must_match=["x"])
        self.assertFalse(passed)
        self.assertIn("no transcript", detail)
        self.assertTrue(objective.transcript_matches(
            "/nonexistent", [], must_match=["(?i)elevated"],
            transcript="Run this from an ELEVATED prompt")[0])
        self.assertFalse(objective.transcript_matches(
            "/nonexistent", [], must_not_match=["sudo"], transcript="use sudo")[0])

    def test_run_checks_routes_the_transcript_and_the_regex_lists(self):
        ws = self._ws({"log": "Export-ScheduledTask\n"})
        fixture = {"objective_checks": [
            {"id": "f", "type": "file_matches", "paths": ["log"],
             "must_match": ["Export"], "must_not_match": ["denied"]},
            {"id": "t", "type": "transcript_matches", "must_match": ["elevat"]},
        ]}
        by_id = {r["id"]: r for r in objective.run_checks(fixture, str(ws), str(ws))}
        self.assertTrue(by_id["f"]["passed"], by_id["f"]["detail"])
        self.assertFalse(by_id["t"]["passed"])  # no transcript given
        by_id = {r["id"]: r for r in objective.run_checks(
            fixture, str(ws), str(ws), transcript="needs an elevated prompt")}
        self.assertTrue(by_id["t"]["passed"], by_id["t"]["detail"])


class FileCountCheckTests(unittest.TestCase):
    """file_count: assert the number of files a glob matches falls in
    [min, max] — the "exactly N files exist" shape file_matches/
    files_unchanged can't express, e.g. "exactly one new ADR was added".
    """

    def _ws(self, names: list[str]) -> Path:
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        for rel in names:
            path = ws / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x\n", encoding="utf-8")
        return ws

    def test_within_range_passes(self):
        ws = self._ws(["a.md", "b.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count=1, max_count=3)
        self.assertTrue(passed, detail)
        self.assertIn("2 file(s)", detail)

    def test_below_min_fails(self):
        ws = self._ws(["a.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count=2, max_count=5)
        self.assertFalse(passed)
        self.assertIn("found 1, expected at least 2", detail)

    def test_above_max_fails(self):
        ws = self._ws(["a.md", "b.md", "c.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count=0, max_count=2)
        self.assertFalse(passed)
        self.assertIn("found 3, expected at most 2", detail)

    def test_max_none_means_unbounded(self):
        ws = self._ws([f"{i}.md" for i in range(10)])
        self.assertTrue(objective.file_count(str(ws), ["*.md"], min_count=1)[0])

    def test_overlapping_patterns_are_not_double_counted(self):
        # Both patterns match a.md; it must count once, not twice.
        ws = self._ws(["a.md"])
        passed, detail = objective.file_count(
            str(ws), ["*.md", "a.*"], min_count=1, max_count=1)
        self.assertTrue(passed, detail)

    def test_zero_matches_within_a_zero_min_passes(self):
        ws = self._ws(["unrelated.txt"])
        self.assertTrue(objective.file_count(str(ws), ["*.md"], min_count=0, max_count=0)[0])

    def test_run_checks_reads_min_max_from_fixture(self):
        ws = self._ws(["docs/decisions/0001-x.md", "docs/decisions/0002-y.md"])
        fixture = {"objective_checks": [
            {"id": "count", "type": "file_count",
             "paths": ["docs/decisions/*.md"], "min": 2, "max": 2},
        ]}
        by_id = {r["id"]: r for r in objective.run_checks(fixture, str(ws), str(ws))}
        self.assertTrue(by_id["count"]["passed"], by_id["count"]["detail"])

    def test_run_checks_defaults_min_to_zero_when_omitted(self):
        ws = self._ws([])
        fixture = {"objective_checks": [
            {"id": "count", "type": "file_count", "paths": ["*.md"], "max": 0},
        ]}
        by_id = {r["id"]: r for r in objective.run_checks(fixture, str(ws), str(ws))}
        self.assertTrue(by_id["count"]["passed"], by_id["count"]["detail"])

    def test_file_count_is_registered_in_checks_map(self):
        self.assertIn("file_count", objective.CHECKS)
        self.assertIs(objective.CHECKS["file_count"], objective.file_count)

    # --- Review round 1 on PR #136 (issue #80), item S3: run_checks read
    # only "min"/"max" from the fixture dict, so a fixture typo'd as
    # "min_count"/"max_count" (the Python parameter names) silently
    # resolved to no bound at all and passed unconditionally. ---

    def test_run_checks_accepts_min_count_max_count_alias(self):
        ws = self._ws(["a.md"])  # only 1 file
        fixture = {"objective_checks": [
            {"id": "count", "type": "file_count", "paths": ["*.md"],
             "min_count": 2, "max_count": 2},
        ]}
        by_id = {r["id"]: r for r in objective.run_checks(fixture, str(ws), str(ws))}
        self.assertFalse(by_id["count"]["passed"], by_id["count"]["detail"])
        self.assertIn("found 1, expected at least 2", by_id["count"]["detail"])

    def test_file_count_check_naming_neither_bound_fails(self):
        ws = self._ws(["a.md"])
        fixture = {"objective_checks": [
            {"id": "count", "type": "file_count", "paths": ["*.md"]},
        ]}
        by_id = {r["id"]: r for r in objective.run_checks(fixture, str(ws), str(ws))}
        self.assertFalse(by_id["count"]["passed"])
        self.assertIn("neither", by_id["count"]["detail"].lower())

    def test_file_count_negative_min_bound_fails(self):
        ws = self._ws(["a.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count=-1)
        self.assertFalse(passed, detail)
        self.assertIn("negative", detail.lower())

    def test_file_count_negative_max_bound_fails(self):
        ws = self._ws(["a.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], max_count=-1)
        self.assertFalse(passed, detail)
        self.assertIn("negative", detail.lower())

    def test_file_count_max_less_than_min_fails_with_named_detail(self):
        ws = self._ws(["a.md", "b.md", "c.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count=5, max_count=2)
        self.assertFalse(passed)
        self.assertIn("max", detail.lower())
        self.assertIn("min", detail.lower())
        # The config error is reported before any counting happens, so the
        # "found N, expected..." wording (which would be misleading here —
        # no count could ever satisfy an impossible range) must not appear.
        self.assertNotIn("found", detail.lower())

    # --- item S4: file_count had no os.path.isfile filter (unlike
    # _read_matched), so a directory whose name happens to match the glob
    # inflated the count. ---

    def test_directories_matching_the_pattern_are_not_counted(self):
        ws = self._ws(["0001-real.md"])
        (ws / "0002-fake-dir.md").mkdir()
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count=1, max_count=1)
        self.assertTrue(passed, detail)
        self.assertIn("1 file(s)", detail)

    # --- Review round 2 on PR #136 (issue #80), item S4: three file_count
    # residuals the round-1 guards didn't cover. ---

    def test_min_zero_with_no_max_is_vacuous_and_fails(self):
        # `min: 0` with no `max` bounds nothing — count is always >= 0 and
        # there is no ceiling — so it passed unconditionally, same as naming
        # neither bound. The one difference from "neither" is that a caller
        # who wrote `min: 0` believed they were asserting something.
        ws = self._ws(["a.md", "b.md", "c.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count=0)
        self.assertFalse(passed, detail)

    def test_run_checks_min_zero_no_max_is_vacuous_and_fails(self):
        ws = self._ws(["a.md"])
        fixture = {"objective_checks": [
            {"id": "count", "type": "file_count", "paths": ["*.md"], "min": 0},
        ]}
        by_id = {r["id"]: r for r in objective.run_checks(fixture, str(ws), str(ws))}
        self.assertFalse(by_id["count"]["passed"], by_id["count"]["detail"])

    def test_string_min_bound_fails_instead_of_raising_typeerror(self):
        ws = self._ws(["a.md", "b.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count="4")
        self.assertFalse(passed, detail)
        self.assertIn("int", detail.lower())

    def test_run_checks_string_min_bound_fails_instead_of_raising(self):
        # The finding's exact shape: a fixture author typo's `min: "4"`
        # (quoted) in YAML, and run_checks must report a failed check with a
        # named detail, not let a TypeError escape from the comparison.
        ws = self._ws(["a.md", "b.md"])
        fixture = {"objective_checks": [
            {"id": "count", "type": "file_count", "paths": ["*.md"], "min": "4"},
        ]}
        by_id = {r["id"]: r for r in objective.run_checks(fixture, str(ws), str(ws))}
        self.assertFalse(by_id["count"]["passed"], by_id["count"]["detail"])
        self.assertIn("int", by_id["count"]["detail"].lower())

    def test_bool_min_bound_is_rejected_not_treated_as_the_integer_one(self):
        # `min: true` sails through as `min_count=1` (bool is an int
        # subclass in Python) — with >=1 file already present this silently
        # "passes" a config mistake instead of naming it.
        ws = self._ws(["a.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count=True)
        self.assertFalse(passed, detail)
        self.assertIn("bool", detail.lower())

    def test_bool_max_bound_is_rejected_not_treated_as_the_integer_one(self):
        ws = self._ws(["a.md"])
        passed, detail = objective.file_count(str(ws), ["*.md"], min_count=1, max_count=True)
        self.assertFalse(passed, detail)
        self.assertIn("bool", detail.lower())


class FakePowershellTests(unittest.TestCase):
    """The windows-elevation-from-wsl seed's stand-in powershell.exe.

    It must reproduce the one behaviour the skill exists to handle — reads
    succeed, elevation-requiring writes are denied, elevation dodges fail
    with Windows' own wording — and log every invocation with its class.
    """

    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.ws, ignore_errors=True)
        shutil.copytree(ELEVATION_DIR / "seed", self.ws, dirs_exist_ok=True)
        self.log = self.ws / ".powershell-invocations.log"

    def _ps(self, *args, exe="powershell.exe", stdin=None):
        return subprocess.run([str(self.ws / "bin" / exe), *args], cwd=self.ws,
                              capture_output=True, text=True, input=stdin)

    def _classes(self) -> list[str]:
        import re
        return re.findall(r"class=(\w+)", self.log.read_text(encoding="utf-8"))

    def test_reads_succeed_with_canned_output(self):
        r = self._ps("-NoProfile", "-Command", "Get-ScheduledTask -TaskPath '\\WslAutomation\\'")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("WSL-Backup", r.stdout)
        r = self._ps("-c", "Export-ScheduledTask -TaskName WSL-Backup", exe="pwsh.exe")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("<RunLevel>HighestAvailable</RunLevel>", r.stdout)
        self.assertIn("2026-01-01T02:00:00", r.stdout)
        self.assertEqual(self._classes(), ["read", "read"])

    def test_elevation_requiring_writes_are_denied(self):
        for cmd in ("Set-ScheduledTask -TaskName WSL-Backup -Trigger $t",
                    "Register-ScheduledTask -TaskName WSL-Backup -Force",
                    "Set-Service -Name Schedule -StartupType Manual",
                    "secedit /configure /db x.sdb"):
            r = self._ps("-Command", cmd)
            self.assertEqual(r.returncode, 1, cmd)
            self.assertIn("Access is denied", r.stderr)
        self.assertEqual(self._classes(), ["denied"] * 4)

    def test_a_write_inside_a_script_file_is_denied_too(self):
        r = self._ps("-ExecutionPolicy", "Bypass", "-File", "scripts/register-tasks.ps1",
                     "-BackupTime", "03:30")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Register-ScheduledTask : Access is denied", r.stderr)
        self.assertEqual(self._classes(), ["denied"])
        self.assertIn("mode=file", self.log.read_text(encoding="utf-8"))

    def test_elevation_dodges_fail_and_are_classed_as_such(self):
        r = self._ps("-Command", "Start-Process powershell -Verb RunAs -ArgumentList '-File x'")
        self.assertEqual(r.returncode, 1)
        self.assertIn("requires elevation", r.stderr)
        r = self._ps("-Command", "schtasks /Change /TN \\WslAutomation\\WSL-Backup /ST 03:30")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Access is denied", r.stderr)
        r = self._ps("-Command", "sudo Register-ScheduledTask -TaskName x")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self._classes(), ["dodge"] * 3)

    def test_stdin_script_is_read_and_logged(self):
        r = self._ps("-Command", "-", stdin="whoami /groups\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Group used for deny only", r.stdout)
        self.assertIn("mode=stdin", self.log.read_text(encoding="utf-8"))


class WindowsElevationFixtureTests(unittest.TestCase):
    """The windows-elevation-from-wsl fixture's checks, driven by simulated runs."""

    HANDOFF = ("This needs elevation: open an elevated Windows PowerShell (Run as "
               "administrator) and run\n"
               "powershell.exe -ExecutionPolicy Bypass -File "
               "D:\\repos\\adam-s-daniel\\wsl-backup\\scripts\\register-tasks.ps1 "
               "-BackupTime 03:30\n")

    def _run(self, act, transcript=None) -> dict:
        fixture = run_eval.load_fixture(ELEVATION_DIR)
        seed = ELEVATION_DIR / "seed"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            shutil.copytree(seed, ws)
            act(ws)
            results = objective.run_checks(fixture, str(ws), str(seed), transcript=transcript)
        return {r["id"]: r for r in results}

    def _ps(self, ws: Path, *args) -> None:
        subprocess.run([str(ws / "bin" / "powershell.exe"), *args], cwd=ws,
                       capture_output=True, text=True)

    def _edit_time(self, ws: Path, new: str = '"03:30"') -> None:
        path = ws / "scripts" / "register-tasks.ps1"
        text = path.read_text(encoding="utf-8")
        self.assertIn('"02:00"', text)
        path.write_text(text.replace('"02:00"', new), encoding="utf-8")

    def test_pristine_seed_fails_the_behaviour_checks(self):
        by_id = self._run(lambda ws: None)
        for check_id in ("script-moved-to-0330", "exported-before-handoff",
                         "handoff-names-elevation-and-the-line"):
            self.assertFalse(by_id[check_id]["passed"], by_id[check_id]["detail"])

    def test_pristine_seed_passes_the_restraint_checks(self):
        by_id = self._run(lambda ws: None)
        for check_id in ("no-elevation-dodge", "denied-write-not-retried",
                         "principal-not-downgraded", "fake-powershell-untouched"):
            self.assertTrue(by_id[check_id]["passed"], by_id[check_id]["detail"])

    def test_a_skilled_run_passes_every_check(self):
        def act(ws):
            self._ps(ws, "-Command", "Get-ScheduledTask -TaskPath '\\WslAutomation\\'")
            self._ps(ws, "-Command", "Export-ScheduledTask -TaskName WSL-Backup")
            self._edit_time(ws)
        for check_id, result in self._run(act, transcript=self.HANDOFF).items():
            self.assertTrue(result["passed"], f"{check_id}: {result['detail']}")

    def test_one_denial_then_the_handoff_still_passes(self):
        # Discovering the denial once is not chasing it.
        def act(ws):
            self._edit_time(ws)
            self._ps(ws, "-File", "scripts/register-tasks.ps1", "-BackupTime", "03:30")
            self._ps(ws, "-Command", "Export-ScheduledTask -TaskName WSL-Backup")
        by_id = self._run(act, transcript=self.HANDOFF)
        self.assertTrue(by_id["denied-write-not-retried"]["passed"])
        self.assertTrue(by_id["no-elevation-dodge"]["passed"])

    def test_a_chasing_run_fails_the_dodge_and_retry_checks(self):
        def act(ws):
            self._edit_time(ws)
            self._ps(ws, "-File", "scripts/register-tasks.ps1", "-BackupTime", "03:30")
            self._ps(ws, "-Command", "Set-ScheduledTask -TaskName WSL-Backup -Trigger $t")
            self._ps(ws, "-Command", "Start-Process powershell -Verb RunAs")
        by_id = self._run(act, transcript="Done — the task is now at 03:30.")
        self.assertFalse(by_id["denied-write-not-retried"]["passed"])
        self.assertFalse(by_id["no-elevation-dodge"]["passed"])
        self.assertFalse(by_id["handoff-names-elevation-and-the-line"]["passed"])

    def test_a_downgraded_principal_fails(self):
        def act(ws):
            self._edit_time(ws)
            path = ws / "scripts" / "register-tasks.ps1"
            path.write_text(path.read_text(encoding="utf-8")
                            .replace("-RunLevel Highest", "-RunLevel Limited"),
                            encoding="utf-8")
        by_id = self._run(act, transcript=self.HANDOFF)
        self.assertFalse(by_id["principal-not-downgraded"]["passed"])

    def test_editing_the_fake_binary_fails(self):
        def act(ws):
            with open(ws / "bin" / "powershell.exe", "a", encoding="utf-8") as f:
                f.write("# tampered\n")
        by_id = self._run(act, transcript=self.HANDOFF)
        self.assertFalse(by_id["fake-powershell-untouched"]["passed"])


class MakeBadgeTests(unittest.TestCase):
    """scripts/make_badge.py against hand-written run summaries, one per color."""

    TS = "20260716T070000Z"
    DATE = "2026-07-16"

    def setUp(self):
        self.results = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.results, ignore_errors=True)

    @staticmethod
    def _summary(passed: int, total: int, judge_overall=None, error=None) -> dict:
        return {
            "error": error,
            "objective_checks": [{"id": f"c{i}", "passed": i < passed,
                                  "detail": ""} for i in range(total)],
            "judge": {"overall": judge_overall} if judge_overall is not None else None,
        }

    def _write_run(self, ts: str, with_summary: dict | None,
                   without_summary: dict | None) -> None:
        for arm, summary in (("with_skill", with_summary),
                             ("without_skill", without_summary)):
            if summary is None:
                continue
            arm_dir = self.results / "workflow-path-audit" / ts / arm
            arm_dir.mkdir(parents=True)
            (arm_dir / "summary.json").write_text(
                json.dumps(summary), encoding="utf-8")

    def _badge(self, window: int = make_badge.DEFAULT_WINDOW) -> dict:
        return make_badge.build_badge(self.results, "workflow-path-audit", window)

    def test_green_when_with_strictly_better(self):
        self._write_run(self.TS, self._summary(5, 5, 8.5), self._summary(3, 5, 4.0))
        badge = self._badge()
        self.assertEqual(badge["schemaVersion"], 1)
        self.assertEqual(badge["label"], "skill eval: workflow-path-audit")
        self.assertEqual(badge["message"], f"with 5/5 vs without 3/5 · {self.DATE}")
        self.assertEqual(badge["color"], "green")

    def test_yellow_when_tied(self):
        self._write_run(self.TS, self._summary(4, 5, 7.0), self._summary(4, 5, 7.0))
        badge = self._badge()
        self.assertEqual(badge["color"], "yellow")
        self.assertIn(self.DATE, badge["message"])

    def test_yellow_when_signals_mixed(self):
        # Better objectively, worse per the judge: mixed, not green.
        self._write_run(self.TS, self._summary(5, 5, 5.0), self._summary(4, 5, 8.0))
        self.assertEqual(self._badge()["color"], "yellow")

    def test_yellow_when_objective_tied_judge_better(self):
        # Green requires a strict objective win; a judge advantage on an
        # objective tie caps at yellow, never promotes to green.
        self._write_run(self.TS, self._summary(4, 5, 9.0), self._summary(4, 5, 3.0))
        self.assertEqual(self._badge()["color"], "yellow")

    def test_red_when_objective_tied_judge_worse(self):
        # On an objective tie the judge may demote: worse judge -> red.
        self._write_run(self.TS, self._summary(4, 5, 3.0), self._summary(4, 5, 8.0))
        self.assertEqual(self._badge()["color"], "red")

    def test_red_when_with_worse(self):
        self._write_run(self.TS, self._summary(2, 5, 3.0), self._summary(4, 5, 7.0))
        badge = self._badge()
        self.assertEqual(badge["color"], "red")
        self.assertEqual(badge["message"], f"with 2/5 vs without 4/5 · {self.DATE}")

    def test_judge_missing_falls_back_to_objective_only(self):
        self._write_run(self.TS, self._summary(5, 5, None), self._summary(3, 5, 6.0))
        self.assertEqual(self._badge()["color"], "green")

    def test_grey_when_arm_summary_missing(self):
        self._write_run(self.TS, self._summary(5, 5, 8.0), None)
        badge = self._badge()
        self.assertEqual(badge["color"], "lightgrey")
        self.assertEqual(badge["message"], f"no data · {self.DATE}")

    def test_grey_when_arm_errored(self):
        errored = self._summary(0, 5, None,
                                error={"type": "timeout", "detail": "600s"})
        errored["objective_checks"] = None
        self._write_run(self.TS, self._summary(5, 5, 8.0), errored)
        self.assertEqual(self._badge()["color"], "lightgrey")

    def test_grey_when_summary_malformed(self):
        # Non-list objective_checks / non-dict judge must read as missing
        # data (lightgrey), never crash the badge job.
        malformed = self._summary(5, 5, 8.0)
        malformed["objective_checks"] = {"oops": "not a list"}
        malformed["judge"] = "not a dict"
        self._write_run(self.TS, self._summary(5, 5, 8.0), malformed)
        badge = self._badge()
        self.assertEqual(badge["color"], "lightgrey")
        self.assertEqual(badge["message"], f"no data · {self.DATE}")

    def test_grey_when_no_runs(self):
        badge = self._badge()
        self.assertEqual(badge["color"], "lightgrey")
        self.assertEqual(badge["message"], "no runs yet")

    def test_window_1_reads_newest_run_only(self):
        # The pre-window behaviour, still reachable: with --window 1 the older
        # (opposite-signal) run must not influence the badge at all, and the
        # message must be byte-identical to what the single-run badge emitted.
        self._write_run("20260101T000000Z", self._summary(5, 5, 9.0),
                        self._summary(1, 5, 2.0))
        self._write_run(self.TS, self._summary(2, 5, 3.0), self._summary(4, 5, 7.0))
        badge = self._badge(window=1)
        self.assertEqual(badge["color"], "red")
        self.assertEqual(badge["message"], f"with 2/5 vs without 4/5 · {self.DATE}")
        self.assertNotIn("n=", badge["message"])

    def test_window_averages_across_runs(self):
        # Three runs whose newest one alone would read red; averaged, the
        # with_skill arm is clearly ahead. This is the whole point of the
        # window — one run is scheduling luck, not a measurement.
        self._write_run("20260714T070000Z", self._summary(7, 7, 8.0),
                        self._summary(6, 7, 7.0))
        self._write_run("20260715T070000Z", self._summary(7, 7, 8.0),
                        self._summary(4, 7, 6.0))
        self._write_run(self.TS, self._summary(6, 7, 7.0), self._summary(7, 7, 8.0))
        badge = self._badge()
        # with: (7+7+6)/3 = 6.666… -> 6.7 ; without: (6+4+7)/3 = 5.666… -> 5.7
        self.assertEqual(badge["message"],
                         f"with 6.7/7 vs without 5.7/7 · n=3 · {self.DATE}")
        self.assertEqual(badge["color"], "green")

    def test_integral_means_render_without_a_decimal_point(self):
        self._write_run("20260715T070000Z", self._summary(7, 7, 8.0),
                        self._summary(4, 7, 6.0))
        self._write_run(self.TS, self._summary(7, 7, 8.0), self._summary(6, 7, 6.0))
        # with averages to exactly 7 -> "7/7", never "7.0/7".
        self.assertEqual(self._badge()["message"],
                         f"with 7/7 vs without 5/7 · n=2 · {self.DATE}")

    def test_window_bound_ignores_runs_older_than_n(self):
        # Five runs, window of 2: only the two newest count, so the three old
        # with_skill wins must not rescue the average.
        for ts in ("20260710T070000Z", "20260711T070000Z", "20260712T070000Z"):
            self._write_run(ts, self._summary(7, 7, 9.0), self._summary(1, 7, 2.0))
        self._write_run("20260715T070000Z", self._summary(3, 7, 4.0),
                        self._summary(5, 7, 8.0))
        self._write_run(self.TS, self._summary(3, 7, 4.0), self._summary(5, 7, 8.0))
        badge = self._badge(window=2)
        self.assertEqual(badge["message"],
                         f"with 3/7 vs without 5/7 · n=2 · {self.DATE}")
        self.assertEqual(badge["color"], "red")

    def test_unusable_run_is_skipped_not_fatal(self):
        # The newest run errored on one arm. It drops out of the average
        # instead of blanking the badge, the sample size says so, and the
        # date follows the newest run that actually contributed.
        contributing = "20260715T070000Z"
        self._write_run("20260714T070000Z", self._summary(7, 7, 8.0),
                        self._summary(3, 7, 5.0))
        self._write_run(contributing, self._summary(6, 7, 7.0),
                        self._summary(4, 7, 5.0))
        self._write_run(self.TS, self._summary(5, 7, 8.0), None)
        badge = self._badge()
        self.assertEqual(badge["message"],
                         "with 6.5/7 vs without 3.5/7 · n=2 · 2026-07-15")
        self.assertEqual(badge["color"], "green")

    def test_grey_when_no_run_in_the_window_is_usable(self):
        # An older run IS usable, but it sits outside the window: the badge
        # must go lightgrey rather than reach back past the window for data.
        self._write_run("20260101T000000Z", self._summary(5, 5, 9.0),
                        self._summary(1, 5, 2.0))
        self._write_run(self.TS, self._summary(5, 5, 8.0), None)
        badge = self._badge(window=1)
        self.assertEqual(badge["color"], "lightgrey")
        self.assertEqual(badge["message"], f"no data · {self.DATE}")

    def test_grey_when_every_run_in_the_window_is_unusable(self):
        self._write_run("20260715T070000Z", None, self._summary(4, 7, 5.0))
        self._write_run(self.TS, self._summary(5, 7, 8.0), None)
        badge = self._badge()
        self.assertEqual(badge["color"], "lightgrey")
        # Dated from the newest run dir, so the reader still sees the staleness.
        self.assertEqual(badge["message"], f"no data · {self.DATE}")

    def test_cli_window_flag_changes_the_aggregate(self):
        self._write_run("20260715T070000Z", self._summary(5, 5, 9.0),
                        self._summary(1, 5, 2.0))
        self._write_run(self.TS, self._summary(2, 5, 3.0), self._summary(4, 5, 7.0))
        out = self.results / "badge.json"

        def run(*extra):
            cmd = [sys.executable, str(REPO_ROOT / "scripts" / "make_badge.py"),
                   "workflow-path-audit", "--results-dir", str(self.results),
                   "--out", str(out), *extra]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            return json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(run("--window", "1")["message"],
                         f"with 2/5 vs without 4/5 · {self.DATE}")
        self.assertEqual(run("--window", "2")["message"],
                         f"with 3.5/5 vs without 2.5/5 · n=2 · {self.DATE}")

    def test_cli_rejects_a_window_below_one(self):
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "make_badge.py"),
             "workflow-path-audit", "--results-dir", str(self.results),
             "--out", str(self.results / "badge.json"), "--window", "0"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("must be >= 1", proc.stderr)

    def test_cli_writes_deterministic_badge_file(self):
        self._write_run(self.TS, self._summary(5, 5, 8.0), self._summary(3, 5, 4.0))
        out = self.results / "badge.json"
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "make_badge.py"),
               "workflow-path-audit", "--results-dir", str(self.results),
               "--out", str(out)]
        first = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        bytes_one = out.read_bytes()
        second = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(bytes_one, out.read_bytes())
        badge = json.loads(bytes_one)
        self.assertEqual(badge["schemaVersion"], 1)
        self.assertEqual(badge["color"], "green")


class BadgeWorkflowOrderingTests(unittest.TestCase):
    """The real-eval workflow must build the badge AFTER checking out eval-results.

    make_badge.py averages the `--window N` newest runs under results/, but the
    only place that run history exists is the `eval-results` branch — a fresh
    CI workspace holds nothing but the run that just finished. eval.yml used to
    generate the badge in a step of its own, ahead of the commit step that
    fetches and checks `eval-results` out, so the window could never contain
    more than one run: the averaging was structurally inert and every published
    badge silently reported a single run while looking perfectly healthy. The
    only outward symptom was a missing `n=` marker, which make_badge.py emits
    only above one run, so the defect survived in production unnoticed.

    Nothing inside the badge script can enforce this — it is purely a question
    of step ordering in the workflow — so the invariant is pinned here: exactly
    one step may invoke make_badge.py, and it must do so after that same
    script's `git checkout -B eval-results`. The regression this guards against
    is someone re-introducing a separate, earlier badge step alongside the
    merged one.
    """

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"

    @staticmethod
    def _invocation_lines(script: str) -> list[int]:
        """Line indices where `script` actually RUNS make_badge.py.

        Merely naming the file is not running it: the step also copies the
        script into $RUNNER_TEMP before the branch switch (the eval-results
        branch carries no scripts/ dir), and that copy legitimately precedes
        the checkout. An invocation is a mention with an interpreter ahead of
        it on the same line.
        """
        return [i for i, line in enumerate(script.splitlines())
                if "make_badge.py" in line
                and "python" in line.split("make_badge.py")[0]]

    def _steps(self) -> list[dict]:
        # Structured formats go through a real parser, never a line scanner.
        import yaml
        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        return doc["jobs"]["eval"]["steps"]

    def test_badge_is_built_after_the_eval_results_checkout(self):
        steps = self._steps()
        building = [s for s in steps
                    if self._invocation_lines(s.get("run") or "")]
        self.assertEqual(
            len(building), 1,
            "exactly one step may invoke make_badge.py — a second, earlier "
            "invocation puts the badge back in the pre-checkout workspace, "
            "where its window can only ever see one run. Invoking steps: "
            f"{[s.get('name') for s in building]}")

        script = building[0]["run"]
        self.assertIn("git checkout -B eval-results", script,
                      "the badge must be built on the eval-results branch, so "
                      "that checkout has to live in this same step")
        lines = script.splitlines()
        checkout = next(i for i, line in enumerate(lines)
                        if "git checkout -B eval-results" in line)
        for invocation in self._invocation_lines(script):
            self.assertGreater(
                invocation, checkout,
                "make_badge.py must run after `git checkout -B eval-results` "
                "and after the results/ restore, or its window sees only the "
                "run that just finished and the badge always reports n=1")


class EvalWorkflowSecurityHeaderTests(unittest.TestCase):
    """eval.yml is the one workflow holding a live API key; the security
    header at the top of the file states the rules that keep it safe. These
    assert the rules against the PARSED YAML, never a regex over the raw
    file text — a comment or a quoting quirk could fool a regex; yaml.safe_load
    cannot.
    """

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"
    CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    USES_SHA_RE = re.compile(r"^[A-Za-z0-9._/-]+@[0-9a-f]{40}$")

    def _doc(self) -> dict:
        import yaml
        return yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))

    def _steps(self) -> list[dict]:
        doc = self._doc()
        steps = []
        for job in doc["jobs"].values():
            steps.extend(job.get("steps", []))
        return steps

    def test_every_uses_is_a_bare_40_hex_sha(self):
        for step in self._steps():
            uses = step.get("uses")
            if uses is None:
                continue
            with self.subTest(uses=uses):
                self.assertRegex(
                    uses, self.USES_SHA_RE,
                    f"{uses!r} is not a bare owner/repo@<40-hex-sha> pin, per "
                    "the header's cooling-off convention")
        # The assertion above is on the PARSED `uses:` value, which
        # yaml.safe_load has already stripped of any comment — it cannot see
        # a trailing version/date comment even when one is there. That is a
        # lexical, not structural, concern, so a raw-line scan is the right
        # tool here (not a drift risk: this is the one place in this test
        # class that reads the file as text instead of parsed YAML).
        for lineno, line in enumerate(
                self.WORKFLOW.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("uses:"):
                with self.subTest(line=lineno):
                    self.assertNotIn(
                        "#", line,
                        f"{self.WORKFLOW}:{lineno} has a uses: line with a "
                        "trailing comment — the header's cooling-off "
                        "convention makes the bare SHA the only claim, since "
                        "a version/date comment can go stale silently and "
                        "then lie")

    def test_every_checkout_step_disables_persist_credentials(self):
        for step in self._steps():
            if (step.get("uses") or "").startswith("actions/checkout@"):
                with self.subTest(step=step.get("name")):
                    self.assertIs(
                        (step.get("with") or {}).get("persist-credentials"), False,
                        f"checkout step {step.get('name')!r} must set "
                        "persist-credentials: false — no long-lived GitHub "
                        "credential may exist while the bypassPermissions agent runs")

    def test_no_expression_interpolation_in_any_run_block(self):
        for step in self._steps():
            run = step.get("run")
            if run:
                with self.subTest(step=step.get("name")):
                    self.assertNotIn(
                        "${{", run,
                        f"step {step.get('name')!r}'s run: block must not "
                        "interpolate a GitHub Actions expression — untrusted "
                        "expansion into a shell command that runs under "
                        "bypassPermissions with a live key in env is a "
                        "command-injection vector")

    def test_ci_yml_shares_the_sha_pin_persist_creds_and_no_interp_rules(self):
        # Item H (round 3, optional): the three rules above are workflow-file
        # hygiene, not eval.yml-specific — ci.yml's two checkouts were
        # compared only to EACH OTHER (CiDispatchTests), so pinning both to
        # the same @v4 tag would have stayed green there.
        import yaml
        doc = yaml.safe_load(self.CI_WORKFLOW.read_text(encoding="utf-8"))
        steps = [s for job in doc["jobs"].values() for s in job.get("steps", [])]
        for step in steps:
            uses = step.get("uses")
            with self.subTest(uses=uses, step=step.get("name")):
                if uses is not None:
                    self.assertRegex(uses, self.USES_SHA_RE,
                                     f"{uses!r} is not a bare SHA pin")
                if (uses or "").startswith("actions/checkout@"):
                    self.assertIs(
                        (step.get("with") or {}).get("persist-credentials"), False,
                        "checkout step must set persist-credentials: false")
                if step.get("run"):
                    self.assertNotIn("${{", step["run"],
                                     "run: block must not interpolate")
        for lineno, line in enumerate(
                self.CI_WORKFLOW.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("uses:"):
                with self.subTest(line=lineno):
                    self.assertNotIn(
                        "#", line, f"line {lineno} has a trailing comment "
                        "on a uses: line")

    def test_triggers_are_exactly_schedule_and_dispatch(self):
        doc = self._doc()
        triggers = doc.get("on", doc.get(True))
        self.assertEqual(
            set(triggers), {"schedule", "workflow_dispatch"},
            "eval.yml holds a live API key and runs the agent under "
            "bypassPermissions — pull_request/pull_request_target must never "
            "be added, per the header's first rule")

    def test_permissions_are_exactly_contents_write_and_id_token_write(self):
        # "Single job, so contents:write is the whole workflow's privilege
        # set" — the header's own claim. A widened `permissions:` block
        # (an added scope, or contents: write turning into admin) would slip
        # past every other test in this class.
        doc = self._doc()
        self.assertEqual(
            doc.get("permissions"), {"contents": "write", "id-token": "write"},
            "eval.yml's permissions must be exactly {contents: write, "
            "id-token: write} — the header states this is the workflow's "
            "whole privilege set")

    def test_no_workflow_or_job_level_env(self):
        # The header requires GITHUB_TOKEN (and the exchanged bearer token)
        # to live only in the step that needs it, "never top-level env" —
        # hoisting either to workflow- or job-level env would put a live
        # credential in scope for every step, including the ones that run
        # the bypassPermissions agent against untrusted-ish fixture output.
        doc = self._doc()
        self.assertNotIn(
            "env", doc,
            "eval.yml must not declare a workflow-level env: block — the "
            "header requires every credential to be step-scoped")
        for job_name, job in doc["jobs"].items():
            with self.subTest(job=job_name):
                self.assertNotIn(
                    "env", job,
                    f"job {job_name!r} must not declare a job-level env: "
                    "block — the header requires every credential to be "
                    "step-scoped")

    def test_header_names_every_checkout_and_the_automated_lane_clause(self):
        # Ties the header's own claims to the ACTUAL step list, rather than
        # to a number written in prose that can go stale the moment a
        # checkout is added or removed: reverting "All four checkouts" back
        # to an earlier "Both checkouts", or deleting the automated-lane
        # clause (Decap CMS publish loops, auto-merge nudges, dependabot
        # auto-merge landing commits on cms-platform/adamdaniel.ai's default
        # branches), must fail here.
        #
        # Review round 3, item C: the per-repo "header must name every
        # checked-out registry" check below used to search the WHOLE file
        # for `repo`, which always matches the checkout step's own
        # `repository: <repo>` line — so it passed vacuously no matter what
        # the header prose said. Scoped to just the file's LEADING comment
        # block (the run of lines at the top that start with '#' or are
        # blank) instead, and matched against the registry's basename
        # (`agentskills`, not `Adam-S-Daniel/agentskills`) — the spelling
        # the header prose actually uses.
        lines = self.WORKFLOW.read_text(encoding="utf-8").splitlines()
        header_lines = list(itertools.takewhile(
            lambda line: line.strip() == "" or line.lstrip().startswith("#"),
            lines))
        header = "\n".join(header_lines)
        self.assertTrue(header.strip(), "expected a non-empty leading "
                        "comment block at the top of eval.yml")

        checkout_steps = [s for s in self._steps()
                          if (s.get("uses") or "").startswith("actions/checkout@")]
        count = len(checkout_steps)
        number_words = {2: "two", 3: "three", 4: "four", 5: "five"}
        self.assertIn(count, number_words,
                      f"unexpected number of checkout steps: {count}")
        self.assertIn(
            f"All {number_words[count]} checkouts", header,
            f"the header must say 'All {number_words[count]} checkouts' — "
            f"it currently disagrees with the actual count ({count}) of "
            "actions/checkout@ steps in the file")

        named_repos = sorted(
            (step.get("with") or {}).get("repository")
            for step in checkout_steps
            if (step.get("with") or {}).get("repository"))
        self.assertTrue(named_repos, "expected at least one checkout step "
                        "naming a repository:")
        for repo in named_repos:
            basename = repo.rsplit("/", 1)[-1]
            with self.subTest(repo=repo):
                self.assertIn(
                    basename, header,
                    f"the header's LEADING COMMENT BLOCK must name every "
                    f"checked-out registry ({basename!r} is missing) — "
                    "write access to any checked-out registry is "
                    "equivalent to key access here")

        self.assertIn(
            "automated lanes", header,
            "the header's automated-lane clause (Decap CMS editorial "
            "publish loops, auto-merge nudges, dependabot auto-merge) must "
            "not be deleted — those lanes land commits inside the trust "
            "boundary the same as a maintainer's own push")

    def test_registry_flags_match_registries_yml_and_checkout_paths(self):
        # A `--registry NAME=PATH` flag typo'd either side (a NAME not in
        # harness/registries.yml, or a PATH whose basename names no checkout
        # step) stays green in this hermetic suite and only dies at runtime
        # in the real (scheduled, credentialed) workflow — up to a week
        # later. Caught here by checking the ACTUAL flags in the eval step's
        # run: block against the ACTUAL registry names and checkout paths.
        #
        # Review round 3, item A: the original version of this check only
        # asked whether a flag's PATH basename was SOME checkout path, not
        # whether that checkout's `repository:` is the repo registries.yml
        # actually names for that flag's NAME — so a NAME/PATH pair
        # transposed between two registries (e.g.
        # `--registry agentskills=../cms-platform`) stayed green here and
        # died at runtime with skill_not_found. Now built from
        # {with.path: with.repository} and cross-checked against each
        # registry's own url in harness/registries.yml.
        doc = self._doc()
        steps = doc["jobs"]["eval"]["steps"]
        eval_step = next(s for s in steps
                         if (s.get("name") or "").startswith("Run the eval"))
        self.assertEqual(
            eval_step.get("working-directory"), "skills-evals",
            "the eval step must declare working-directory: skills-evals — "
            "the ../<checkout-path> registry overrides below are relative "
            "to it")
        run = eval_step["run"]
        flags = re.findall(r"--registry\s+([A-Za-z0-9_.-]+)=(\S+)", run)
        self.assertTrue(
            flags, "no --registry NAME=PATH flags found in the eval step's "
            "run: block")

        registries_config = run_eval._load_registries_config()
        known_names = {e["name"] for e in registries_config}
        repo_by_name = {
            e["name"]: run_eval._normalize_registry_url(e["url"]).rsplit("/", 1)[-1]
            for e in registries_config}

        checkout_steps = [s for s in steps
                          if (s.get("uses") or "").startswith("actions/checkout@")]
        registry_checkouts = [s for s in checkout_steps
                              if (s.get("with") or {}).get("repository")]
        path_to_repo = {
            (s.get("with") or {}).get("path"):
                (s.get("with") or {}).get("repository", "").rsplit("/", 1)[-1].lower()
            for s in registry_checkouts}

        self.assertEqual(
            len(flags), len(registry_checkouts),
            f"{len(flags)} --registry flag(s) but {len(registry_checkouts)} "
            "registry checkout step(s) in eval.yml — every checked-out "
            "registry must get exactly one flag and vice versa")

        for name, path in flags:
            with self.subTest(name=name, path=path):
                self.assertIn(
                    name, known_names,
                    f"--registry {name}={path}: {name!r} is not a registry "
                    "name listed in harness/registries.yml")
                basename = path.rstrip("/").rsplit("/", 1)[-1]
                self.assertIn(
                    basename, path_to_repo,
                    f"--registry {name}={path}: no checkout step in eval.yml "
                    f"has with.path == {basename!r}")
                self.assertEqual(
                    path_to_repo[basename], repo_by_name[name],
                    f"--registry {name}={path}: the checkout at path "
                    f"{basename!r} checks out {path_to_repo[basename]!r}, "
                    f"not the repo harness/registries.yml names for "
                    f"{name!r} ({repo_by_name[name]!r}) — this flag's NAME "
                    "and PATH point at two different registries")


class CiDispatchTests(unittest.TestCase):
    """ci.yml must stay runnable by hand, WITHOUT losing its paths filters.

    The two properties fight each other, which is why they are pinned
    together. The filters above the trigger are what keep a docs-only pull
    request off a runner — and they are equally what leaves a docs-only commit
    with no way to run this suite at all. `workflow_dispatch` is that way; it
    takes no `paths:` (GitHub ignores one there), so adding it cannot dilute
    the filters, and a future edit that "simplifies" the triggers by dropping
    them would.

    Losing the dispatch again is silent — no red run, just a missing button on
    the day someone needs it. That is how it was lost the first time: a fix
    merged and confirming it returned `422 Workflow does not have
    'workflow_dispatch' trigger`, so verification waited for the next
    qualifying push.
    """

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

    # Both events carry this list and the workflow's own header requires them
    # kept in step; spelling it out here is what makes "in step" checkable.
    SALIENT = [".github/workflows/ci.yml", ".github/workflows/eval.yml",
               "evals/**", "harness/**", "scripts/**", "test/**"]

    def _triggers(self) -> dict:
        # A real parser, never a line scan: a bare `on:` key is the YAML 1.1
        # boolean True once parsed, which is exactly the sort of thing a
        # regex reads straight past.
        import yaml
        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        return doc.get("on", doc.get(True))

    def test_ci_is_dispatchable(self):
        triggers = self._triggers()
        self.assertIn("workflow_dispatch", triggers,
                      "ci.yml must stay manually runnable — the paths filters "
                      "below mean a docs-only commit has no other way to run "
                      f"this suite; triggers are {sorted(triggers)}")
        self.assertIsNone(
            triggers["workflow_dispatch"],
            "the dispatch is deliberately bare: this suite takes no arguments, "
            "and a `paths:` under workflow_dispatch is ignored by GitHub while "
            "reading like a filter that works")

    def test_both_filtered_events_keep_the_same_salient_paths(self):
        triggers = self._triggers()
        for event in ("pull_request", "push"):
            self.assertEqual(
                triggers[event]["paths"], self.SALIENT,
                f"{event}'s paths drifted from the derived salient list — the "
                "two events must stay in step, or the same commit runs this "
                "suite on one and skips it on the other")
        # .get, not []: a dropped branch pin should report itself, not raise
        # a KeyError that says only that some key is missing.
        self.assertEqual(triggers["push"].get("branches"), ["main"],
                         "push is pinned to main: without the branch filter "
                         "every push to a pull-request branch ran `test` twice "
                         "(observed on 82596ff, 03:38:30 and 03:39:14)")

    def test_checks_out_agentskills_side_by_side_for_the_agreement_test(self):
        # TestIssue63::test_registries_agree_with_agentskills_own_file skips
        # (with a printed reason) when no agentskills checkout is present —
        # which was EVERY run in CI, since ci.yml checked out only this repo.
        # A side-by-side checkout, matching eval.yml's and propagation.yml's
        # own pattern, is what lets that test actually execute here.
        import yaml
        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        steps = doc["jobs"]["test"]["steps"]
        # Identified by with.path == "skills-evals", not positionally — a
        # reordering of the checkout steps must not make this compare the
        # agentskills checkout's SHA against itself and pass vacuously.
        own_checkout = next(s for s in steps
                            if (s.get("uses") or "").startswith("actions/checkout@")
                            and (s.get("with") or {}).get("path") == "skills-evals")
        own_sha = own_checkout["uses"].split("@", 1)[1]

        agentskills_checkouts = [
            s for s in steps
            if (s.get("uses") or "").startswith("actions/checkout@")
            and (s.get("with") or {}).get("repository") == "Adam-S-Daniel/agentskills"]
        self.assertEqual(len(agentskills_checkouts), 1,
                         "expected exactly one agentskills checkout step")
        step = agentskills_checkouts[0]
        with_block = step.get("with") or {}
        self.assertEqual(with_block.get("path"), "agentskills")
        self.assertIs(with_block.get("persist-credentials"), False)
        self.assertEqual(step["uses"].split("@", 1)[1], own_sha,
                         "the agentskills checkout must pin the same bare "
                         "40-hex SHA as ci.yml's own checkout")


class EndToEndTests(unittest.TestCase):
    @staticmethod
    def _registry_for(tmp: Path, skill: str) -> Path:
        """A throwaway registry carrying the fixture's own skill.

        The shared fake registries use synthetic skill names on purpose, so
        they can never shadow a real one; the with_skill arm still needs the
        name the fixture actually asks for, and taking it from the fixture
        keeps this in step if the eval subject ever changes again.
        """
        registry = tmp / "registry"
        skill_dir = registry / "plugins" / "a-bundle" / "skills" / skill
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: end-to-end test stand-in.\n---\n",
            encoding="utf-8")
        return registry

    def test_both_arms_produce_summary_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            results_dir = Path(tmp) / "results"
            skill = run_eval.load_fixture(EVAL_DIR)["skill"]
            env = os.environ.copy()
            env["CLAUDE_BIN"] = str(FAKE_CLAUDE)
            env["FAKE_CLAUDE_MODE"] = "agent_and_judge"
            env["AGENTSKILLS_DIR"] = str(self._registry_for(Path(tmp), skill))
            cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(EVAL_DIR),
                  "--arm", "both", "--results-dir", str(results_dir),
                  "--timeout", "30"]
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  env=env, cwd=str(REPO_ROOT))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            skill_dir = results_dir / "workflow-path-audit"
            self.assertTrue(skill_dir.is_dir())
            run_dirs = list(skill_dir.iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            report = (run_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("workflow-path-audit", report)
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
                # The fixture carries judge.weights, so run_eval must forward
                # them and the overall must be RECOMPUTED — fake-claude
                # self-reports 7.5, which is what an unwired weights kwarg
                # would leave behind.
                self.assertNotEqual(summary["judge"]["overall"], 7.5)
                raw_path = run_dir / arm / "transcripts" / "raw.json"
                self.assertTrue(raw_path.is_file())

            # Never pollutes the real repo results/ dir.
            self.assertFalse((REPO_ROOT / "results" / "workflow-path-audit").exists())

    def test_objective_only_unchanged_against_pristine_seed(self):
        cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(EVAL_DIR),
              "--arm", "objective-only"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["skill"], "workflow-path-audit")
        self.assertEqual(payload["arm"], "objective-only")
        by_id = {c["id"]: c for c in payload["checks"]}
        self.assertFalse(by_id["docs-change-routes-correctly"]["passed"])
        self.assertFalse(
            by_id["required-check-always-fires-and-gates-internally"]["passed"])


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


class TestIssue63(unittest.TestCase):
    """Issue #63: resolve the with_skill arm's skill dir against any registry
    layout named in harness/registries.yml, not just agentskills'
    plugins/*/skills/*/SKILL.md — cms-platform's flat skills/*/SKILL.md and
    adamdaniel.ai's .claude/skills/*/SKILL.md must resolve too, and an
    unknown registry: URL must fail loudly naming the file to fix.
    """

    REGISTRIES_YML = HARNESS_DIR / "registries.yml"

    def _fake_registry(self, tmp: str, rel_skill_md: str) -> Path:
        registry = Path(tmp) / "registry"
        skill_md = registry / rel_skill_md
        skill_md.parent.mkdir(parents=True)
        skill_md.write_text(
            f"---\nname: {skill_md.parent.name}\ndescription: fixture stand-in.\n---\n",
            encoding="utf-8")
        return registry

    def _fake_registry_many(self, tmp: str, rel_skill_mds: list[str]) -> Path:
        """Like _fake_registry, but seeds several skills at once — needed to
        catch a mutant that drops the skill-name substitution in
        _skill_md_glob: a registry holding exactly one skill can't tell
        "installed the skill that was asked for" apart from "installed
        whatever's there", since `skills/*/SKILL.md` and `skills/<skill>/
        SKILL.md` glob the same single file either way.
        """
        registry = Path(tmp) / "registry"
        for rel in rel_skill_mds:
            skill_md = registry / rel
            skill_md.parent.mkdir(parents=True)
            skill_md.write_text(
                f"---\nname: {skill_md.parent.name}\ndescription: fixture "
                f"stand-in for {rel}.\n---\n", encoding="utf-8")
        return registry

    def _install(self, registry: Path, skill: str, layout: str, workspace: Path) -> dict:
        arm = {"name": "with_skill", "skill": skill, "registry": registry,
              "layout": layout, "timeout": 30}
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                          "FAKE_CLAUDE_MODE": "agent"}):
            return run_eval.run_agent(workspace, "audit the workflows", arm)

    def test_resolves_flat_skills_layout(self):
        # cms-platform-shaped: skills/<skill>/SKILL.md. Two skills present —
        # see _fake_registry_many's docstring for why one isn't enough.
        # Requests "some-skill" specifically because it sorts AFTER
        # "other-skill": a mutant that drops the skill-name substitution
        # (leaving the layout's `*` unresolved, matching both skills,
        # first-sorted-match wins) would pick "other-skill" here — asserting
        # against the one that does NOT sort first is what gives the content
        # check below teeth; requesting "other-skill" would coincidentally
        # "pass" under that mutant since it also sorts first.
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._fake_registry_many(
                tmp, ["skills/some-skill/SKILL.md", "skills/other-skill/SKILL.md"])
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            result = self._install(registry, "some-skill", "skills/*/SKILL.md", workspace)
            self.assertNotIn("error", result)
            installed = workspace / ".claude" / "skills"
            skill_md = installed / "some-skill" / "SKILL.md"
            self.assertTrue(skill_md.is_file())
            self.assertFalse((installed / "other-skill").exists())
            # Lands exactly there, not nested one level deeper.
            files = sorted(p.relative_to(installed) for p in installed.rglob("*") if p.is_file())
            self.assertEqual(files, [Path("some-skill/SKILL.md")])
            # Content, not just the destination path: the destination dir is
            # ALWAYS named after the requested skill (run_agent's copytree
            # target), so a mutant that drops the skill-name substitution in
            # _skill_md_glob would still satisfy every assertion above while
            # installing the WRONG skill's content under the right-looking
            # name. Only reading back the seeded `name:` line catches that.
            self.assertIn("name: some-skill", skill_md.read_text(encoding="utf-8"))

    def test_resolves_dotclaude_skills_layout(self):
        # adamdaniel.ai-shaped: .claude/skills/<skill>/SKILL.md. Two skills
        # present, same reason as the flat-layout test above.
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._fake_registry_many(
                tmp, [".claude/skills/some-skill/SKILL.md",
                     ".claude/skills/other-skill/SKILL.md"])
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            result = self._install(registry, "some-skill", ".claude/skills/*/SKILL.md", workspace)
            self.assertNotIn("error", result)
            installed = workspace / ".claude" / "skills"
            skill_md = installed / "some-skill" / "SKILL.md"
            self.assertTrue(skill_md.is_file())
            self.assertFalse((installed / "other-skill").exists())
            files = sorted(p.relative_to(installed) for p in installed.rglob("*") if p.is_file())
            self.assertEqual(files, [Path("some-skill/SKILL.md")])
            # See test_resolves_flat_skills_layout's comment: the destination
            # path alone cannot tell "installed what was asked for" apart
            # from "installed whatever glob-matched first" once the
            # destination is renamed to the requested skill regardless.
            self.assertIn("name: some-skill", skill_md.read_text(encoding="utf-8"))

    def test_flat_layout_missing_skill_names_the_skills_path(self):
        # A non-plugins layout's skill_not_found detail must name the actual
        # glob searched (skills/<skill>/SKILL.md), not agentskills' own
        # plugins/*/skills/<skill> shape.
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._fake_registry(tmp, "skills/some-skill/SKILL.md")
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            result = self._install(registry, "does-not-exist", "skills/*/SKILL.md", workspace)
            self.assertIn("error", result)
            self.assertEqual(result["error"], "skill_not_found")
            self.assertIn("skills/does-not-exist/SKILL.md", result["detail"])

    def test_skill_dir_without_skill_md_fails_closed(self):
        # A rename-in-progress or mid-migration bundle can leave a skill
        # DIRECTORY with no SKILL.md inside it (just a references/ subdir,
        # say). Globbing for the directory (pre-fix behavior) "installed"
        # this successfully — the CLI then loaded nothing, both arms ran
        # skill-less, and a normal-looking badge got published. Globbing for
        # the SKILL.md file itself must fail closed instead.
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry"
            stub = registry / "skills" / "some-skill" / "references"
            stub.mkdir(parents=True)
            (stub / "notes.md").write_text("orphaned reference doc\n", encoding="utf-8")
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            result = self._install(registry, "some-skill", "skills/*/SKILL.md", workspace)
            self.assertIn("error", result)
            self.assertEqual(result["error"], "skill_not_found")
            self.assertFalse((workspace / ".claude").exists())

    def test_invalid_skill_names_are_rejected(self):
        # `skill` flows unvalidated into both a glob and a copytree
        # destination — `../../x` would escape the registry on read and the
        # workspace on write, `*` would install the first skill glob-matches,
        # and `""` would install the whole registry container.
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._fake_registry(tmp, "plugins/a-bundle/skills/real-skill/SKILL.md")
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            for bad in ("../../etc", "*", "", "a/b", "..", ".", "a\\b", "a?b", "a[b]c",
                       "a\n", "..\n", ".\n"):
                # The `\n`-suffixed cases: `_SKILL_NAME_RE`'s trailing `$`
                # matches just before a trailing newline (not only at the
                # true end of string), so `.match()` used to ACCEPT these —
                # exactly what a folded YAML scalar (`skill: >` with a
                # single line) produces. `re.fullmatch` closes it.
                with self.subTest(skill=bad):
                    result = self._install(
                        registry, bad, "plugins/*/skills/*/SKILL.md", workspace)
                    self.assertIn("error", result)
                    self.assertEqual(result["error"], "invalid_skill_name")
                    self.assertFalse((workspace / ".claude").exists())

    def test_unknown_registry_url_names_the_registries_file(self):
        registries = run_eval.resolve_registries(None, None, REPO_ROOT)
        with self.assertRaises(ValueError) as ctx:
            run_eval.registry_for_url(registries, "https://github.com/example/not-a-registry")
        self.assertIn("harness/registries.yml", str(ctx.exception))
        self.assertIn("not-a-registry", str(ctx.exception))

    def test_legacy_single_registry_flag_still_resolves_the_agentskills_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._fake_registry(
                tmp, "plugins/a-bundle/skills/some-skill/SKILL.md")
            # The pre-#63 form: one bare path, no NAME= prefix.
            registries = run_eval.resolve_registries([str(registry)], None, REPO_ROOT)
            entry = run_eval.registry_for_url(
                registries, "https://github.com/Adam-S-Daniel/agentskills")
            self.assertEqual(entry["path"], registry)
            self.assertEqual(entry["layout"], "plugins/*/skills/*/SKILL.md")

            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            result = self._install(entry["path"], "some-skill", entry["layout"], workspace)
            self.assertNotIn("error", result)
            self.assertTrue((workspace / ".claude" / "skills" / "some-skill"
                            / "SKILL.md").is_file())

    def test_registry_name_equals_path_flag_targets_that_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._fake_registry(tmp, "skills/some-skill/SKILL.md")
            registries = run_eval.resolve_registries(
                [f"cms-platform={registry}"], None, REPO_ROOT)
            entry = run_eval.registry_for_url(
                registries, "https://github.com/Adam-S-Daniel/cms-platform")
            self.assertEqual(entry["path"], registry)
            self.assertEqual(entry["layout"], "skills/*/SKILL.md")

    def test_env_var_supplies_registry_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = self._fake_registry(tmp, ".claude/skills/some-skill/SKILL.md")
            env_value = f"adamdaniel.ai={registry}"
            registries = run_eval.resolve_registries(None, env_value, REPO_ROOT)
            entry = run_eval.registry_for_url(
                registries, "https://github.com/Adam-S-Daniel/adamdaniel.ai")
            self.assertEqual(entry["path"], registry)

    def test_no_override_falls_back_to_sibling_directory(self):
        registries = run_eval.resolve_registries(None, None, REPO_ROOT)
        entry = registries["cms-platform"]
        self.assertEqual(entry["source"], "sibling default")
        # Derived independently of resolve_registries' own (base_dir / ".." /
        # name).resolve() expression, rather than restating it verbatim.
        # Resolved on BOTH sides: entry["path"] has already gone through
        # .resolve() (which follows symlinks), so comparing it to an
        # unresolved expression is the suite's only failure on otherwise
        # correct code when a sibling checkout sits behind a symlink.
        self.assertEqual(entry["path"], (REPO_ROOT.parent / "cms-platform").resolve())
        self.assertTrue(entry["path"].is_absolute())

    def test_registries_agree_with_agentskills_own_file(self):
        # Routed through resolve_registries (rather than a hardcoded
        # "../agentskills") so $AGENTSKILLS_DIR / $SKILLS_EVALS_REGISTRIES can
        # steer which checkout this compares against, same as a real run.
        registries = run_eval.resolve_registries(
            None, os.environ.get("SKILLS_EVALS_REGISTRIES"), REPO_ROOT,
            os.environ.get("AGENTSKILLS_DIR"))
        agentskills_file = registries["agentskills"]["path"] / "scripts" / "skills_registries.yml"
        if not agentskills_file.is_file():
            reason = (f"no agentskills checkout at {agentskills_file} — "
                      "skipping the cross-repo registries.yml agreement check")
            # ci.yml runs this suite as `python3 test/run_tests.py`, no -v —
            # skipTest's reason is otherwise never printed anywhere, which
            # registries.yml's own header promises never happens ("skips
            # with a printed reason, never silently").
            print(reason)
            self.skipTest(reason)
        import yaml
        theirs = {e["name"]: e["layout"] for e in
                 yaml.safe_load(agentskills_file.read_text(encoding="utf-8"))["registries"]}
        ours = {e["name"]: e["layout"] for e in
               yaml.safe_load(self.REGISTRIES_YML.read_text(encoding="utf-8"))["registries"]}
        self.assertEqual(ours, theirs)

    # --- Review round 3, item B: a TRUTHY non-string skill:/prompt:/
    # registry: must never reach re/subprocess/.strip() and crash with an
    # uncaught TypeError/AttributeError. Round 2 closed only the falsy case
    # (None/""); this closes the class for any wrong-typed value. ---

    def test_fixture_non_string_skill_or_prompt_exits_2_not_a_traceback(self):
        cases = {"skill": [123, ["a"]], "prompt": [123, ["a"]]}
        for field, bad_values in cases.items():
            for bad in bad_values:
                with self.subTest(field=field, value=bad):
                    with tempfile.TemporaryDirectory() as tmp:
                        eval_dir = Path(tmp) / "eval"
                        seed_dir = eval_dir / "seed"
                        seed_dir.mkdir(parents=True)
                        (seed_dir / "placeholder.txt").write_text(
                            "x\n", encoding="utf-8")
                        fixture = {"skill": "some-skill", "prompt": "do the thing"}
                        fixture[field] = bad
                        import yaml
                        (eval_dir / "fixture.yaml").write_text(
                            yaml.safe_dump(fixture), encoding="utf-8")

                        results_dir = Path(tmp) / "results"
                        cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"),
                              str(eval_dir), "--arm", "without_skill",
                              "--results-dir", str(results_dir),
                              "--timeout", "30", "--no-judge"]
                        proc = subprocess.run(cmd, capture_output=True, text=True,
                                              cwd=str(REPO_ROOT))
                        self.assertEqual(proc.returncode, 2,
                                         proc.stdout + proc.stderr)
                        self.assertNotIn("Traceback", proc.stderr)
                        self.assertIn(field, proc.stdout + proc.stderr)
                        self.assertIn("string",
                                      (proc.stdout + proc.stderr).lower())
                        self.assertFalse(results_dir.exists())

    def test_non_string_registry_field_is_an_error_dict_other_arm_still_runs(self):
        # A truthy non-string registry: (a list, an int, a mapping, a bool)
        # used to reach _normalize_registry_url's .strip() (or re, inside
        # registry_for_url) with the raw value and raise an uncaught
        # AttributeError/TypeError — killing the WHOLE run, including
        # --arm both's without_skill arm, with a bare traceback.
        bad_values = [["https://example.com/x"], 123,
                     {"url": "https://example.com/x"}, True]
        for bad in bad_values:
            with self.subTest(value=bad):
                with tempfile.TemporaryDirectory() as tmp:
                    eval_dir = Path(tmp) / "eval"
                    seed_dir = eval_dir / "seed"
                    seed_dir.mkdir(parents=True)
                    (seed_dir / "placeholder.txt").write_text(
                        "x\n", encoding="utf-8")
                    fixture = {"skill": "some-skill", "registry": bad,
                              "prompt": "do the thing"}
                    import yaml
                    (eval_dir / "fixture.yaml").write_text(
                        yaml.safe_dump(fixture), encoding="utf-8")

                    results_dir = Path(tmp) / "results"
                    env = os.environ.copy()
                    env["CLAUDE_BIN"] = str(FAKE_CLAUDE)
                    env["FAKE_CLAUDE_MODE"] = "agent"
                    cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"),
                          str(eval_dir), "--arm", "both",
                          "--results-dir", str(results_dir),
                          "--timeout", "30", "--no-judge"]
                    proc = subprocess.run(cmd, capture_output=True, text=True,
                                          env=env, cwd=str(REPO_ROOT))
                    self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                    self.assertNotIn("Traceback", proc.stderr)

                    run_dirs = list((results_dir / "some-skill").iterdir())
                    self.assertEqual(len(run_dirs), 1)
                    run_dir = run_dirs[0]
                    self.assertTrue((run_dir / "report.md").is_file())

                    with_skill_summary = json.loads(
                        (run_dir / "with_skill" / "summary.json")
                        .read_text(encoding="utf-8"))
                    self.assertEqual(with_skill_summary["error"]["type"],
                                     "invalid_registry_field")

                    without_skill_summary = json.loads(
                        (run_dir / "without_skill" / "summary.json")
                        .read_text(encoding="utf-8"))
                    self.assertIsNone(without_skill_summary["error"])

    # --- Review round 3, item E: a repeated $SKILLS_EVALS_REGISTRIES name
    # (bare or explicit) must raise, not silently last-win — the twin of
    # _parse_registry_flags' own guard (TestIssue63Round2's
    # test_repeated_cli_flag_for_same_name_raises). ---

    def test_repeated_env_var_entry_for_same_name_raises(self):
        with self.assertRaises(ValueError) as ctx:
            run_eval.resolve_registries(
                None, "cms-platform=/a,cms-platform=/b", REPO_ROOT)
        self.assertIn("cms-platform", str(ctx.exception))

    def test_repeated_bare_env_entry_raises(self):
        with self.assertRaises(ValueError) as ctx:
            run_eval.resolve_registries(None, "/a,/b", REPO_ROOT)
        self.assertIn("agentskills", str(ctx.exception))

    # --- Review round 3, item G: a `**` layout segment passes the
    # "ends in '*/SKILL.md'" load-time check but lets a recursive glob at
    # arm time pick up a stale copy under e.g. a checkout's .git/ as the
    # sorted-first match. Reject it at load time instead. ---

    def test_registries_yml_layout_with_double_star_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "registries.yml"
            bad.write_text(
                "registries:\n  - name: agentskills\n"
                "    url: https://example.com/a\n"
                "    layout: '**/*/SKILL.md'\n",
                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(bad)
            self.assertIn("**", str(ctx.exception))


class TestIssue63Review(unittest.TestCase):
    """Review round 1 on PR #128 (issue #63): should-fix items from two opus
    reviews (a code review and an adversarial pass over the key-bearing
    eval.yml). See the PR description's "Review round 1" section for the
    letter each test maps to.
    """

    def test_unknown_cli_override_name_is_rejected(self):
        # A typo'd --registry NAME=PATH (or one naming something not in
        # registries.yml at all) used to be silently dropped and the sibling
        # default used instead — which can "work" by accident and makes the
        # override unverifiable from the exit code alone.
        with self.assertRaises(ValueError) as ctx:
            run_eval.resolve_registries(["cms_platform=/x"], None, REPO_ROOT)
        msg = str(ctx.exception)
        self.assertIn("cms_platform", msg)
        self.assertIn("harness/registries.yml", msg)
        for name in ("agentskills", "cms-platform", "adamdaniel.ai"):
            self.assertIn(name, msg)

    def test_unknown_env_override_name_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            run_eval.resolve_registries(None, "not-a-real-registry=/x", REPO_ROOT)
        self.assertIn("not-a-real-registry", str(ctx.exception))

    def test_bare_env_entry_is_taken_as_agentskills_like_the_cli_flag(self):
        # A bare $SKILLS_EVALS_REGISTRIES entry (no "=") used to be silently
        # dropped, even though a bare --registry PATH is the documented
        # legacy agentskills shorthand. The two are now consistent.
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry"
            registry.mkdir()
            registries = run_eval.resolve_registries(None, str(registry), REPO_ROOT)
        self.assertEqual(registries["agentskills"]["path"], registry.resolve())
        self.assertEqual(registries["agentskills"]["source"], "$SKILLS_EVALS_REGISTRIES")

    def test_empty_path_after_equals_is_rejected_at_parse_time(self):
        # --registry agentskills= used to resolve Path("") == the current
        # working directory, silently.
        with self.assertRaises(ValueError) as ctx:
            run_eval.resolve_registries(["agentskills="], None, REPO_ROOT)
        self.assertIn("agentskills", str(ctx.exception))

    def test_empty_env_path_after_equals_is_rejected_at_parse_time(self):
        with self.assertRaises(ValueError):
            run_eval.resolve_registries(None, "agentskills=", REPO_ROOT)

    def test_nonexistent_explicit_override_is_rejected_before_any_arm_runs(self):
        bad_path = REPO_ROOT / "does-not-exist-anywhere"
        registries = run_eval.resolve_registries(
            [f"cms-platform={bad_path}"], None, REPO_ROOT)
        with self.assertRaises(ValueError) as ctx:
            run_eval._validate_registry_paths(registries)
        msg = str(ctx.exception)
        self.assertIn("cms-platform", msg)
        self.assertIn("does-not-exist-anywhere", msg)
        self.assertIn("--registry flag", msg)

    def test_unoverridden_sibling_default_is_not_eagerly_validated(self):
        # agentskills-private has no sibling checkout in this environment and
        # no fixture references it — validating every registries.yml entry
        # unconditionally would make eval.yml's real run (which never checks
        # it out) fail on every dispatch.
        registries = run_eval.resolve_registries(None, None, REPO_ROOT)
        self.assertFalse(registries["agentskills-private"]["path"].is_dir())
        run_eval._validate_registry_paths(registries)  # must not raise

    def test_override_path_is_resolved_to_an_absolute_path(self):
        # Previously only the sibling-default branch called .resolve(); an
        # override only called .expanduser(), so a relative --registry value
        # stayed relative.
        registries = run_eval.resolve_registries(
            ["cms-platform=../cms-platform"], None, REPO_ROOT)
        self.assertTrue(registries["cms-platform"]["path"].is_absolute())

    def test_agentskills_dir_is_injected_not_read_from_os_environ(self):
        # resolve_registries must not reach into os.environ itself for
        # AGENTSKILLS_DIR — the caller injects it as a parameter. Set the env
        # var but don't pass it: the sibling default must still win.
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"AGENTSKILLS_DIR": tmp}):
                registries = run_eval.resolve_registries(None, None, REPO_ROOT)
        self.assertEqual(registries["agentskills"]["source"], "sibling default")

    def test_registry_url_match_normalizes_slash_git_suffix_and_case(self):
        registries = run_eval.resolve_registries(None, None, REPO_ROOT)
        for variant in (
            "https://github.com/Adam-S-Daniel/agentskills/",
            "https://github.com/Adam-S-Daniel/agentskills.git",
            "https://GITHUB.COM/adam-s-daniel/AgentSkills",
        ):
            with self.subTest(url=variant):
                entry = run_eval.registry_for_url(registries, variant)
                self.assertEqual(entry["layout"], "plugins/*/skills/*/SKILL.md")

    def test_every_committed_fixture_with_a_skill_resolves_its_registry(self):
        registries = run_eval.resolve_registries(None, None, REPO_ROOT)
        fixture_dirs = sorted((REPO_ROOT / "evals").glob("*/fixture.yaml"))
        checked = 0
        for fixture_path in fixture_dirs:
            fixture = run_eval.load_fixture(fixture_path.parent)
            if "skill" not in fixture:
                continue
            checked += 1
            with self.subTest(fixture=fixture_path.parent.name):
                self.assertIn("registry", fixture,
                             f"{fixture_path} names a skill but no registry:")
                entry = run_eval.registry_for_url(registries, fixture["registry"])
                self.assertIsNotNone(entry)
        self.assertGreater(checked, 0, "no committed fixture carries a skill: "
                           "field — this test would pass vacuously")

    def test_fixture_with_skill_but_no_registry_field_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            seed = Path(tmp) / "seed"
            seed.mkdir()
            (seed / "placeholder.txt").write_text("x\n", encoding="utf-8")
            fixture = {"skill": "some-skill", "prompt": "do the thing"}
            registries = run_eval.resolve_registries(None, None, REPO_ROOT)
            args = argparse.Namespace(model=None, timeout=30,
                                      results_dir=Path(tmp) / "results", no_judge=True)
            result = run_eval._run_arm("with_skill", fixture, seed, registries, args,
                                       "20260101T000000Z")
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["type"], "missing_registry_field")
        self.assertIn("some-skill", result["error"]["detail"])

    def test_unknown_registry_in_fixture_ends_via_exit_2_not_a_crash(self):
        # registry_for_url raising ValueError used to propagate straight out
        # of _run_arm (which has only a `finally:`), killing the whole
        # process with a traceback: no report.md, no summary.json, the
        # without_skill arm never ran, and main() never reached its
        # documented `return 2`.
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = Path(tmp) / "eval"
            seed_dir = eval_dir / "seed"
            seed_dir.mkdir(parents=True)
            (seed_dir / "placeholder.txt").write_text("x\n", encoding="utf-8")
            fixture = {
                "skill": "unreachable-skill",
                "registry": "https://github.com/example/not-a-registry",
                "prompt": "do the thing",
            }
            import yaml
            (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture), encoding="utf-8")

            results_dir = Path(tmp) / "results"
            env = os.environ.copy()
            env["CLAUDE_BIN"] = str(FAKE_CLAUDE)
            env["FAKE_CLAUDE_MODE"] = "agent"
            cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(eval_dir),
                  "--arm", "both", "--results-dir", str(results_dir),
                  "--timeout", "30", "--no-judge"]
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  env=env, cwd=str(REPO_ROOT))
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

            run_dirs = list((results_dir / "unreachable-skill").iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]
            self.assertTrue((run_dir / "report.md").is_file())

            with_skill_summary = json.loads(
                (run_dir / "with_skill" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(with_skill_summary["error"]["type"], "unknown_registry")

            without_skill_summary = json.loads(
                (run_dir / "without_skill" / "summary.json").read_text(encoding="utf-8"))
            self.assertIsNone(without_skill_summary["error"])

    def test_registries_yml_missing_file_has_a_clear_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist.yml"
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(missing)
            self.assertIn(str(missing), str(ctx.exception))

    def test_registries_yml_duplicate_name_has_a_clear_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "registries.yml"
            bad.write_text(
                "registries:\n"
                "  - name: agentskills\n    url: https://example.com/a\n"
                "    layout: 'plugins/*/skills/*/SKILL.md'\n"
                "  - name: agentskills\n    url: https://example.com/b\n"
                "    layout: 'skills/*/SKILL.md'\n",
                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(bad)
            self.assertIn("duplicate", str(ctx.exception).lower())
            self.assertIn("agentskills", str(ctx.exception))

    def test_registries_yml_layout_must_end_in_skill_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "registries.yml"
            bad.write_text(
                "registries:\n"
                "  - name: agentskills\n    url: https://example.com/a\n"
                "    layout: 'plugins/*/skills/*'\n",
                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(bad)
            self.assertIn("SKILL.md", str(ctx.exception))

    def test_registries_yml_absolute_layout_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "registries.yml"
            bad.write_text(
                "registries:\n"
                "  - name: agentskills\n    url: https://example.com/a\n"
                "    layout: '/plugins/*/SKILL.md'\n",
                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(bad)
            self.assertIn("absolute", str(ctx.exception).lower())

    def test_real_registries_yml_passes_shape_validation(self):
        entries = run_eval._load_registries_config()
        names = {e["name"] for e in entries}
        self.assertEqual(names, {"agentskills", "cms-platform", "adamdaniel.ai",
                                 "agentskills-private"})


class TestIssue63Round2(unittest.TestCase):
    """Review round 2 on PR #128 (issue #63): should-fix items from a code
    review and an adversarial pass over round 1's own fixes (741aeb8). See
    the PR description's "Review round 2" section for the letter each test
    maps to.
    """

    # --- R3: _load_registries_config validates type, not just presence ---

    def test_registries_yml_field_wrong_type_has_a_clear_message(self):
        cases = {
            "url": ("registries:\n  - name: agentskills\n    url: 12345\n"
                    "    layout: 'plugins/*/skills/*/SKILL.md'\n"),
            "layout": ("registries:\n  - name: agentskills\n"
                       "    url: https://example.com/a\n    layout: 99\n"),
            "name": ("registries:\n  - name: [a]\n"
                     "    url: https://example.com/a\n"
                     "    layout: 'plugins/*/skills/*/SKILL.md'\n"),
        }
        for field, text in cases.items():
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as tmp:
                    bad = Path(tmp) / "registries.yml"
                    bad.write_text(text, encoding="utf-8")
                    with self.assertRaises(ValueError) as ctx:
                        run_eval._load_registries_config(bad)
                    self.assertIn(field, str(ctx.exception))
                    self.assertIn("string", str(ctx.exception).lower())

    def test_registries_yml_boolean_like_name_is_a_type_error_not_missing(self):
        # `name: no` parses as the YAML 1.1 bool False, which `not entry.get(f)`
        # used to misreport as "missing" — the real problem is the type.
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "registries.yml"
            bad.write_text(
                "registries:\n  - name: no\n    url: https://example.com/a\n"
                "    layout: 'plugins/*/skills/*/SKILL.md'\n",
                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(bad)
            msg = str(ctx.exception)
            self.assertNotIn("missing", msg.lower())
            self.assertIn("string", msg.lower())

    def test_registries_yml_malformed_yaml_has_a_clear_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "registries.yml"
            # Inconsistent indentation — a real yaml.YAMLError, not something
            # a bare `yaml.safe_load(f)` call should let escape as-is.
            bad.write_text(
                "registries:\n  - name: agentskills\n      url: https://example.com/a\n"
                "    layout: 'plugins/*/skills/*/SKILL.md'\n",
                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(bad)
            self.assertIn(str(bad), str(ctx.exception))

    def test_load_time_layout_check_matches_skill_md_glob(self):
        # `skills/bundle*/SKILL.md` ends with the SUBSTRING '*/SKILL.md', so
        # the old load-time `layout.endswith(...)` check passed it — but
        # `_skill_md_glob` requires the segment immediately before SKILL.md
        # to be exactly '*', which 'bundle*' is not, so this used to raise
        # uncaught at arm time instead of failing loudly here at load time.
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "registries.yml"
            bad.write_text(
                "registries:\n  - name: agentskills\n"
                "    url: https://example.com/a\n"
                "    layout: 'skills/bundle*/SKILL.md'\n",
                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(bad)
            self.assertIn("SKILL.md", str(ctx.exception))

    def test_registries_yml_layout_containing_dotdot_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "registries.yml"
            bad.write_text(
                "registries:\n  - name: agentskills\n"
                "    url: https://example.com/a\n"
                "    layout: '../*/SKILL.md'\n",
                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(bad)
            self.assertIn("..", str(ctx.exception))

    # --- R4: duplicate-URL dedup must use the same normalization as the
    # matcher (registry_for_url), not a bare .rstrip("/") ---

    def test_registries_yml_duplicate_url_detected_after_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "registries.yml"
            bad.write_text(
                "registries:\n"
                "  - name: a\n    url: https://github.com/Org/repo\n"
                "    layout: 'plugins/*/skills/*/SKILL.md'\n"
                "  - name: b\n    url: https://GITHUB.com/org/REPO.git/\n"
                "    layout: 'skills/*/SKILL.md'\n",
                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                run_eval._load_registries_config(bad)
            self.assertIn("duplicate", str(ctx.exception).lower())

    # --- R5: skill name validated once, before any path is derived ---

    def test_invalid_skill_names_are_fullmatch_not_prefix_matched(self):
        for bad in ("a\n", "..\n", ".\n"):
            with self.subTest(skill=repr(bad)):
                with self.assertRaises(ValueError):
                    run_eval._validate_skill_name(bad)

    def test_fixture_skill_name_validated_before_any_result_write(self):
        # skill: "../../escaped" used to error correctly INSIDE run_agent
        # (invalid_skill_name), but _write_summary and report_path had
        # already used the raw fixture["skill"] to build a path — so
        # summary.json still landed outside --results-dir. Nested two levels
        # under tmp so the escape (results_dir/../../escaped) stays inside
        # tmp and is cleaned up automatically either way.
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp)
            eval_dir = outer / "eval"
            seed_dir = eval_dir / "seed"
            seed_dir.mkdir(parents=True)
            (seed_dir / "placeholder.txt").write_text("x\n", encoding="utf-8")
            fixture = {"skill": "../../escaped", "prompt": "do the thing"}
            import yaml
            (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture), encoding="utf-8")

            results_dir = outer / "a" / "b" / "results"
            cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(eval_dir),
                  "--arm", "without_skill", "--results-dir", str(results_dir),
                  "--timeout", "30", "--no-judge"]
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("skill", (proc.stdout + proc.stderr).lower())
            self.assertFalse(results_dir.exists())
            self.assertFalse((outer / "a" / "escaped").exists())

    # --- R6: fixture field validation, once, without an uncaught KeyError
    # or AttributeError ---

    def test_blank_registry_field_is_a_missing_registry_field_error(self):
        # registry: written and left blank parses as None, which used to
        # reach _normalize_registry_url's .strip() and die with an uncaught
        # AttributeError — no report, no summary, without_skill never ran.
        with tempfile.TemporaryDirectory() as tmp:
            seed = Path(tmp) / "seed"
            seed.mkdir()
            (seed / "placeholder.txt").write_text("x\n", encoding="utf-8")
            fixture = {"skill": "some-skill", "registry": None, "prompt": "do the thing"}
            registries = run_eval.resolve_registries(None, None, REPO_ROOT)
            args = argparse.Namespace(model=None, timeout=30,
                                      results_dir=Path(tmp) / "results", no_judge=True)
            result = run_eval._run_arm("with_skill", fixture, seed, registries, args,
                                       "20260101T000000Z")
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["type"], "missing_registry_field")

    def test_fixture_missing_prompt_field_exits_2_with_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = Path(tmp) / "eval"
            seed_dir = eval_dir / "seed"
            seed_dir.mkdir(parents=True)
            (seed_dir / "placeholder.txt").write_text("x\n", encoding="utf-8")
            fixture = {"skill": "some-skill",
                      "registry": "https://github.com/Adam-S-Daniel/agentskills"}
            import yaml
            (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture), encoding="utf-8")

            results_dir = Path(tmp) / "results"
            cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(eval_dir),
                  "--arm", "without_skill", "--results-dir", str(results_dir),
                  "--timeout", "30", "--no-judge"]
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("prompt", (proc.stdout + proc.stderr).lower())
            self.assertFalse(results_dir.exists())

    def test_fixture_missing_skill_field_exits_2_with_message(self):
        # A without_skill arm never installs a skill, but _write_summary
        # still reached fixture["skill"] unconditionally — a KeyError on a
        # fixture that legitimately has no "skill:" field at all.
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = Path(tmp) / "eval"
            seed_dir = eval_dir / "seed"
            seed_dir.mkdir(parents=True)
            (seed_dir / "placeholder.txt").write_text("x\n", encoding="utf-8")
            fixture = {"prompt": "do the thing"}
            import yaml
            (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture), encoding="utf-8")

            results_dir = Path(tmp) / "results"
            cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(eval_dir),
                  "--arm", "without_skill", "--results-dir", str(results_dir),
                  "--timeout", "30", "--no-judge"]
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn("skill", (proc.stdout + proc.stderr).lower())
            self.assertFalse(results_dir.exists())

    # --- R8: registry_not_found (a fixture naming a registry whose sibling
    # default doesn't exist) ---

    def test_registry_not_found_ends_via_exit_2_with_message_naming_path(self):
        # Review round 3, item D: the original version of this test asserted
        # the SIBLING DEFAULT for "agentskills-private" specifically
        # (../agentskills-private next to THIS repo's own checkout) does not
        # resolve to a directory — which fails on entirely correct code for
        # any maintainer who has that real fleet repo cloned beside
        # skills-evals (`with_skill` then resolves it and hits
        # skill_not_found instead of registry_not_found; verified locally by
        # creating a sibling `agentskills-private/` next to this checkout).
        #
        # Hermetic fix: run a COPY of the harness rooted inside a fresh tmp
        # directory, with its own scratch registries.yml naming a registry
        # ("scratch-registry") that no real repo carries. `base_dir` inside
        # run_eval.py's main() is `Path(__file__).resolve().parent.parent`
        # — i.e. always the copy's own root, never REPO_ROOT — so the
        # sibling-default path this test exercises resolves INSIDE the tmp
        # root, never beside the real skills-evals checkout, regardless of
        # what any real machine happens to have checked out next to it.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            skills_evals_root = tmp_root / "skills-evals"
            harness_dir = skills_evals_root / "harness"
            shutil.copytree(HARNESS_DIR, harness_dir,
                            ignore=shutil.ignore_patterns("__pycache__"))
            (harness_dir / "registries.yml").write_text(
                "registries:\n"
                "  - name: scratch-registry\n"
                "    url: https://example.com/scratch-registry\n"
                "    layout: 'skills/*/SKILL.md'\n",
                encoding="utf-8")

            eval_dir = tmp_root / "evals" / "scratch-eval"
            seed_dir = eval_dir / "seed"
            seed_dir.mkdir(parents=True)
            (seed_dir / "placeholder.txt").write_text("x\n", encoding="utf-8")
            fixture = {
                "skill": "some-skill",
                "registry": "https://example.com/scratch-registry",
                "prompt": "do the thing",
            }
            import yaml
            (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture), encoding="utf-8")

            results_dir = tmp_root / "results"
            env = os.environ.copy()
            env["CLAUDE_BIN"] = str(FAKE_CLAUDE)
            env["FAKE_CLAUDE_MODE"] = "agent"
            cmd = [sys.executable, str(harness_dir / "run_eval.py"), str(eval_dir),
                  "--arm", "both", "--results-dir", str(results_dir),
                  "--timeout", "30", "--no-judge"]
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  env=env, cwd=str(tmp_root))
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

            run_dirs = list((results_dir / "some-skill").iterdir())
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]
            with_skill_summary = json.loads(
                (run_dir / "with_skill" / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(with_skill_summary["error"]["type"], "registry_not_found")
            # base_dir = harness_dir.parent = skills_evals_root, so the
            # sibling default is (skills_evals_root / ".." / name).resolve()
            # = tmp_root / "scratch-registry" — inside the disposable tmp
            # root, never beside the real skills-evals checkout.
            expected_path = str((tmp_root / "scratch-registry").resolve())
            self.assertIn(expected_path, with_skill_summary["error"]["detail"])

            without_skill_summary = json.loads(
                (run_dir / "without_skill" / "summary.json").read_text(encoding="utf-8"))
            self.assertIsNone(without_skill_summary["error"])

    # --- R9: run_agent must not raise FileExistsError when the seed already
    # ships the skill's destination directory ---

    def test_seed_already_shipping_the_skill_dir_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry"
            skill_md = registry / "skills" / "some-skill" / "SKILL.md"
            skill_md.parent.mkdir(parents=True)
            skill_md.write_text(
                "---\nname: some-skill\ndescription: fixture stand-in.\n---\n",
                encoding="utf-8")

            # Case 1: the destination directory itself already exists (a
            # duplicate with_skill install, or a seed that pre-ships the
            # skill) — shutil.copytree raises FileExistsError.
            workspace = Path(tmp) / "ws"
            preexisting = workspace / ".claude" / "skills" / "some-skill"
            preexisting.mkdir(parents=True)
            (preexisting / "SKILL.md").write_text(
                "---\nname: some-skill\n---\n", encoding="utf-8")

            arm = {"name": "with_skill", "skill": "some-skill", "registry": registry,
                  "layout": "skills/*/SKILL.md", "timeout": 30}
            with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                              "FAKE_CLAUDE_MODE": "agent"}):
                result = run_eval.run_agent(workspace, "audit the workflows", arm)
            self.assertIn("error", result)
            self.assertEqual(result["error"], "skill_install_failed")

            # Case 2: a seed shipping `.claude/skills` itself as a regular
            # FILE (not a directory) — os.makedirs (inside shutil.copytree)
            # raises NotADirectoryError here, a DIFFERENT OSError subclass
            # than FileExistsError. run_agent's "nothing is raised" contract
            # must hold for this case too, not just the FileExistsError one.
            workspace2 = Path(tmp) / "ws2"
            (workspace2 / ".claude").mkdir(parents=True)
            (workspace2 / ".claude" / "skills").write_text(
                "not a directory\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE),
                                              "FAKE_CLAUDE_MODE": "agent"}):
                result2 = run_eval.run_agent(workspace2, "audit the workflows", arm)
            self.assertIn("error", result2)
            self.assertEqual(result2["error"], "skill_install_failed")

    # --- N4: a repeated --registry NAME= for the same name must raise, not
    # silently last-win ---

    def test_repeated_cli_flag_for_same_name_raises(self):
        with self.assertRaises(ValueError) as ctx:
            run_eval.resolve_registries(
                ["cms-platform=/a", "cms-platform=/b"], None, REPO_ROOT)
        self.assertIn("cms-platform", str(ctx.exception))

    def test_repeated_bare_legacy_flag_raises(self):
        with self.assertRaises(ValueError) as ctx:
            run_eval.resolve_registries(["/a", "/b"], None, REPO_ROOT)
        self.assertIn("agentskills", str(ctx.exception))

    # --- N5: registry resolution/validation must abort BEFORE any arm
    # starts, including --arm objective-only ---

    def test_bad_registry_override_aborts_objective_only_run(self):
        cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(EVAL_DIR),
              "--arm", "objective-only", "--registry", "not-a-real-registry=/x"]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("not-a-real-registry", proc.stdout + proc.stderr)


class TestIssue80(unittest.TestCase):
    """evals/writing-adrs: two fixtures for the writing-adrs skill (issue #80).

    `existing-convention` (Class A, format half) — a repo that already has
    docs/decisions/ in a house Status/Context/Decision/Consequences format;
    the task is to record an already-implemented retry-policy decision as
    the next ADR, following the HOUSE convention rather than the skill's own
    default template, updating the index, and linking the code. `bootstrap`
    covers the other half of the skill: no docs/decisions/ exists yet, so
    the correct answer is the skill's own carried template, landed in the
    same change as the first ADR. Both fixtures share the same underlying
    repo (README.md, CHANGELOG.md, scripts/retry.sh) and the same prompt;
    only the presence of docs/decisions/ differs.

    Every test below isolates ONE objective check per mutation: the
    hand-written "correct" fix satisfies every check, and each mutation
    breaks exactly the one check it's named for while leaving the others
    green — proving the checks have teeth individually, not just in
    aggregate.
    """

    # ---- existing-convention: hand-written correct ADR 0004 ---------------

    EXISTING_ADR_0004 = """\
# 0004. Retry transient failures up to 5 times with capped exponential backoff

## Status

Accepted

## Context

Order Sync's poller calls the fulfillment service and other upstream
services that occasionally return a transient failure such as a 503. On
2026-06-02 (PR #142), one such failure was retried in a tight loop with no
cap and no delay, pinning a worker for 40 minutes and starving the queue
behind it.

## Decision

Retry a failing call up to 5 times, backing off exponentially (1s, 2s, 4s,
8s, 16s) before giving up.

## Consequences

A transient blip no longer surfaces as a customer-facing error, and a
persistent failure now gives up after a bounded delay instead of looping
forever. A call that legitimately needs more than 5 tries within about 30
seconds will fail; none observed so far need that.

## Alternatives considered

Retrying forever with a fixed delay was rejected: it would have masked the
same runaway-retry failure again, just slower.

Failing fast with no retry at all was rejected too: it would turn every
transient blip into a customer-facing error.

## References

PR #142.
"""

    # Same content with Context and Decision swapped — breaks section ORDER
    # only; every field is still present, nothing else about the file changes.
    EXISTING_ADR_0004_WRONG_ORDER = """\
# 0004. Retry transient failures up to 5 times with capped exponential backoff

## Status

Accepted

## Decision

Retry a failing call up to 5 times, backing off exponentially (1s, 2s, 4s,
8s, 16s) before giving up.

## Context

Order Sync's poller calls the fulfillment service and other upstream
services that occasionally return a transient failure such as a 503. On
2026-06-02 (PR #142), one such failure was retried in a tight loop with no
cap and no delay, pinning a worker for 40 minutes and starving the queue
behind it.

## Consequences

A transient blip no longer surfaces as a customer-facing error, and a
persistent failure now gives up after a bounded delay instead of looping
forever.
"""

    EXISTING_INDEX_ROW = ("| [0004](0004-retry-with-capped-exponential-backoff.md) | "
                          "Retry transient failures up to 5 times with capped "
                          "exponential backoff | Accepted |\n")

    # Captures the linked filename in group 1 — used by
    # _assert_index_link_target_exists (issue #80 review N4).
    EXISTING_INDEX_LINK_RE = r'\[0004\]\((0004-[a-z0-9-]+\.md)\)'
    BOOTSTRAP_INDEX_LINK_RE = r'\[0001\]\((0001-[a-z0-9-]+\.md)\)'

    EXISTING_README_ANCHOR = (
        "| [0003](0003-poll-fulfillment-service-every-10s.md) | Poll the "
        "fulfillment service every 10 seconds | Accepted |\n")

    EXISTING_RETRY_LINK = (
        "# See docs/decisions/0004-retry-with-capped-exponential-backoff.md\n"
        "# for why these retry parameters were chosen.\n")

    RETRY_SH_ANCHOR = "set -euo pipefail\n"

    # A second, unwarranted ADR for the CHANGELOG's routine fact — correct
    # house format in isolation, but its mere existence is the violation.
    DECOY_ADR_FOR_CHANGELOG = """\
# 0005. Remove the moment dependency

## Status

Accepted

## Context

CHANGELOG.md records that the moment dependency was removed.

## Decision

Use the platform Date APIs instead.

## Consequences

One fewer dependency to update.
"""

    # ---- bootstrap: hand-written correct README + ADR 0001 -----------------

    BOOTSTRAP_README = """\
# Architecture Decision Records

This folder captures why non-obvious decisions were made in this repo.

## When to write one

Write an ADR when, in six months, someone proposing to revert the change
would need three paragraphs to be talked out of it.

## Naming and numbering

- `NNNN-kebab-title.md`, numbered sequentially from `0001`.
- Title is an imperative verb + object.

## Status values

`Proposed` -> `Accepted` -> `Superseded by NNNN` (or `Deprecated`).

## Template

Copy everything between the rules into `NNNN-kebab-title.md`.

---

```markdown
# NNNN. Imperative title matching the index row

- **Status:** Proposed
- **Date:** YYYY-MM-DD

## Context

## Decision

## Consequences

## Alternatives considered

## References
```

---

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-retry-with-capped-exponential-backoff.md) | Retry transient failures up to 5 times with capped exponential backoff | Accepted |
"""

    BOOTSTRAP_ADR_0001 = """\
# 0001. Retry transient failures up to 5 times with capped exponential backoff

- **Status:** Accepted
- **Date:** 2026-09-05

## Context

Order Sync's poller calls the fulfillment service and other upstream
services that occasionally return a transient failure such as a 503. On
2026-06-02 (PR #142), one such failure was retried in a tight loop with no
cap and no delay, pinning a worker for 40 minutes and starving the queue
behind it.

## Decision

Retry a failing call up to 5 times, backing off exponentially (1s, 2s, 4s,
8s, 16s) before giving up.

## Consequences

A transient blip no longer surfaces as a customer-facing error, and a
persistent failure now gives up after a bounded delay instead of looping
forever.

## Alternatives considered

Retrying forever with a fixed delay was rejected: it would have masked the
same runaway-retry failure again, just slower.

Failing fast with no retry at all was rejected too: it would turn every
transient blip into a customer-facing error.

## References

PR #142.
"""

    # Context/Decision swapped, same as the existing-convention wrong-order
    # fixture above — breaks order only.
    BOOTSTRAP_ADR_0001_WRONG_ORDER = """\
# 0001. Retry transient failures up to 5 times with capped exponential backoff

- **Status:** Accepted
- **Date:** 2026-09-05

## Decision

Retry a failing call up to 5 times, backing off exponentially (1s, 2s, 4s,
8s, 16s) before giving up.

## Context

Order Sync's poller calls the fulfillment service and other upstream
services that occasionally return a transient failure such as a 503.

## Consequences

A transient blip no longer surfaces as a customer-facing error.

## Alternatives considered

Retrying forever with a fixed delay was rejected.

## References

PR #142.
"""

    BOOTSTRAP_RETRY_LINK = (
        "# See docs/decisions/0001-retry-with-capped-exponential-backoff.md\n"
        "# for why these retry parameters were chosen.\n")

    BOOTSTRAP_DECOY_ADR_FOR_CHANGELOG = """\
# 0002. Remove the moment dependency

- **Status:** Accepted
- **Date:** 2026-09-05

## Context

CHANGELOG.md records that the moment dependency was removed.

## Decision

Use the platform Date APIs instead.

## Consequences

One fewer dependency to update.
"""

    # Bootstrap step 4: "Add a pointer paragraph in AGENTS.md (or README.md
    # if there's no AGENTS.md) under a new '### Architecture Decision
    # Records' heading". The seed's AGENTS.md has no such heading yet, so
    # the skill-faithful answer appends this. Its second line is the same
    # sentence the existing-convention seed's AGENTS.md already carries
    # under that heading — see the two seeds' AGENTS.md files themselves,
    # and test_seed_files_are_byte_identical_except_for_their_premise below.
    BOOTSTRAP_AGENTS_MD_POINTER = """
### Architecture Decision Records

Non-obvious decisions live in [`docs/decisions/`](docs/decisions/README.md)
— read the index there before assuming a past choice was arbitrary.
"""

    # An ad-hoc, non-skill-shaped bootstrap README: it has an index row (so
    # index-gained-a-row-for-0001 is satisfied) but none of the skill's
    # template headings — for S5's "present but wrong" test.
    BOOTSTRAP_ADHOC_README = """\
# Decisions

## Log

| [0001](0001-retry-with-capped-exponential-backoff.md) | Retry transient failures up to 5 times with capped exponential backoff | Accepted |
"""

    # ---- shared helpers -----------------------------------------------------

    def _ws(self, eval_dir: Path) -> Path:
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        shutil.copytree(eval_dir / "seed", ws, dirs_exist_ok=True)
        return ws

    def _checks(self, eval_dir: Path, ws: Path) -> dict:
        fixture = run_eval.load_fixture(eval_dir)
        results = objective.run_checks(fixture, str(ws), str(eval_dir / "seed"))
        return {r["id"]: r for r in results}

    def _run_cli(self, eval_dir: Path, ws: Path) -> tuple[int, dict]:
        # N3: run_eval.py resolves+validates registries even for
        # --arm objective-only (main() does this before any arm, on
        # purpose — see its own comment). A stale $SKILLS_EVALS_REGISTRIES
        # or $AGENTSKILLS_DIR left over in the calling shell's environment
        # then makes main() print "registry configuration error: ..." and
        # exit 2 instead of scoring the workspace — and that plain-text
        # output isn't JSON, so json.loads below raised, turning the two
        # *_cli_objective_only_exit_codes tests into errors instead of the
        # clean skip a missing registry gets elsewhere in this class. Drop
        # both vars explicitly rather than inheriting whatever the caller's
        # shell happens to have set; objective-only never installs a skill,
        # so it never needs either.
        env = os.environ.copy()
        env.pop("SKILLS_EVALS_REGISTRIES", None)
        env.pop("AGENTSKILLS_DIR", None)
        cmd = [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(eval_dir),
              "--arm", "objective-only", "--workspace", str(ws)]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                              cwd=str(REPO_ROOT))
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
        return proc.returncode, payload

    def _link_retry_sh(self, ws: Path, link_comment: str) -> None:
        path = ws / "scripts" / "retry.sh"
        text = path.read_text(encoding="utf-8")
        self.assertIn(self.RETRY_SH_ANCHOR, text, "retry.sh anchor drifted out of the seed")
        text = text.replace(self.RETRY_SH_ANCHOR, link_comment + self.RETRY_SH_ANCHOR, 1)
        path.write_text(text, encoding="utf-8")

    # ---- existing-convention: apply the correct fix in pieces --------------

    def _write_adr_0004(self, ws: Path, content: str | None = None) -> None:
        adr = ws / "docs" / "decisions" / "0004-retry-with-capped-exponential-backoff.md"
        adr.write_text(content or self.EXISTING_ADR_0004, encoding="utf-8")

    def _add_index_row_existing(self, ws: Path) -> None:
        readme = ws / "docs" / "decisions" / "README.md"
        text = readme.read_text(encoding="utf-8")
        self.assertIn(self.EXISTING_README_ANCHOR, text,
                      "README.md anchor drifted out of the seed")
        text = text.replace(self.EXISTING_README_ANCHOR,
                            self.EXISTING_README_ANCHOR + self.EXISTING_INDEX_ROW, 1)
        readme.write_text(text, encoding="utf-8")

    def _link_retry_sh_existing(self, ws: Path) -> None:
        self._link_retry_sh(ws, self.EXISTING_RETRY_LINK)

    def _apply_correct_existing(self, ws: Path) -> None:
        self._write_adr_0004(ws)
        self._add_index_row_existing(ws)
        self._link_retry_sh_existing(ws)

    # ---- bootstrap: apply the correct fix in pieces -------------------------

    def _bootstrap_docs_decisions(self, ws: Path, readme: str, adr: str) -> None:
        decisions = ws / "docs" / "decisions"
        decisions.mkdir(parents=True, exist_ok=True)
        (decisions / "README.md").write_text(readme, encoding="utf-8")
        (decisions / "0001-retry-with-capped-exponential-backoff.md").write_text(
            adr, encoding="utf-8")

    def _link_retry_sh_bootstrap(self, ws: Path) -> None:
        self._link_retry_sh(ws, self.BOOTSTRAP_RETRY_LINK)

    def _add_agents_md_pointer_bootstrap(self, ws: Path) -> None:
        path = ws / "AGENTS.md"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("### Architecture Decision Records", text,
                         "AGENTS.md seed already carries a pointer — bootstrap "
                         "fixture's seed drifted from its existing-convention twin")
        path.write_text(text + self.BOOTSTRAP_AGENTS_MD_POINTER, encoding="utf-8")

    def _apply_correct_bootstrap(self, ws: Path) -> None:
        self._bootstrap_docs_decisions(ws, self.BOOTSTRAP_README, self.BOOTSTRAP_ADR_0001)
        self._link_retry_sh_bootstrap(ws)
        self._add_agents_md_pointer_bootstrap(ws)

    # ---- N4: index rows can name a slug no file matches ---------------------

    def _assert_index_link_target_exists(self, ws: Path, index_pattern: str) -> None:
        """`index-gained-a-row-for-*`'s file_matches regex only confirms a row
        of the right SHAPE is present in docs/decisions/README.md — it never
        cross-checks the linked filename against the filesystem, so an index
        row naming a slug no file matches would still satisfy it. No fixture
        check type does this cross-check (issue #80 review N4); done here at
        the test level instead of widening objective.py's check surface for
        one fixture. `index_pattern` must capture the linked filename in
        group 1.
        """
        text = (ws / "docs" / "decisions" / "README.md").read_text(encoding="utf-8")
        m = re.search(index_pattern, text)
        self.assertIsNotNone(
            m, f"docs/decisions/README.md has no index row matching {index_pattern}")
        linked = m.group(1)
        self.assertTrue(
            (ws / "docs" / "decisions" / linked).is_file(),
            f"README.md's index links docs/decisions/{linked}, which doesn't exist")

    # ======================================================================
    # existing-convention
    # ======================================================================

    # ---- N4: index rows can name a slug no file matches ---------------------



    def test_existing_pristine_seed_fails_every_check(self):
        ws = self._ws(ADRS_EXISTING_DIR)
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        for check_id in ("adr-0004-house-format-sections-in-order",
                        "index-gained-a-row-for-0004", "retry-sh-links-the-adr",
                        "exactly-one-new-adr-file"):
            self.assertFalse(by_id[check_id]["passed"], by_id[check_id]["detail"])
        # nothing-else-touched is a trivial pass on the pristine seed.
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_existing_hand_written_correct_fix_passes_every_check(self):
        ws = self._ws(ADRS_EXISTING_DIR)
        self._apply_correct_existing(ws)
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        for check_id, result in by_id.items():
            self.assertTrue(result["passed"], f"{check_id}: {result['detail']}")
        self._assert_index_link_target_exists(ws, self.EXISTING_INDEX_LINK_RE)

    def test_existing_mismatched_index_slug_passes_every_fixture_check_but_fails_the_cross_check(self):
        # N4: index-gained-a-row-for-0004's must_match only checks the row's
        # SHAPE. Point the index row at a slug that names no real file (the
        # actual ADR file keeps its correct name) and every fixture check
        # still passes — the cross-check above is what catches it.
        ws = self._ws(ADRS_EXISTING_DIR)
        self._apply_correct_existing(ws)
        readme = ws / "docs" / "decisions" / "README.md"
        text = readme.read_text(encoding="utf-8")
        self.assertIn(self.EXISTING_INDEX_ROW, text)
        mismatched_row = self.EXISTING_INDEX_ROW.replace(
            "0004-retry-with-capped-exponential-backoff.md", "0004-retry-policy.md")
        readme.write_text(text.replace(self.EXISTING_INDEX_ROW, mismatched_row),
                          encoding="utf-8")

        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        for check_id in ("adr-0004-house-format-sections-in-order",
                        "index-gained-a-row-for-0004", "retry-sh-links-the-adr",
                        "exactly-one-new-adr-file", "nothing-else-touched"):
            self.assertTrue(by_id[check_id]["passed"], f"{check_id}: {by_id[check_id]['detail']}")
        with self.assertRaises(AssertionError):
            self._assert_index_link_target_exists(ws, self.EXISTING_INDEX_LINK_RE)

    def test_existing_root_readme_rewrite_fails_only_restraint_check(self):
        # S2 (round 2): nothing-else-touched didn't guard the repo-root
        # README.md. This fixture's index lives at docs/decisions/README.md
        # — a different path files_unchanged's "README.md" glob never
        # matched to begin with — so recording the ADR correctly required
        # no edit to the root README.md, but a wholesale, unrelated rewrite
        # of it went uncaught: a correct ADR 0004 plus a rewritten root
        # README.md scored 5/5.
        ws = self._ws(ADRS_EXISTING_DIR)
        self._apply_correct_existing(ws)
        (ws / "README.md").write_text("# Completely different\n", encoding="utf-8")
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertFalse(by_id["nothing-else-touched"]["passed"],
                         by_id["nothing-else-touched"]["detail"])
        self.assertTrue(by_id["adr-0004-house-format-sections-in-order"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0004"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-new-adr-file"]["passed"])

    def test_existing_mismatched_index_slug_fails_only_the_link_targets_check(self):
        # S3 (round 2): a dangling slug in the index row — naming a file
        # nothing wrote — used to be invisible to every REAL fixture check;
        # only the test-level cross-check above caught it, so a real eval
        # run was blind to it. link_targets_exist closes that gap for real.
        ws = self._ws(ADRS_EXISTING_DIR)
        self._apply_correct_existing(ws)
        readme = ws / "docs" / "decisions" / "README.md"
        text = readme.read_text(encoding="utf-8")
        self.assertIn(self.EXISTING_INDEX_ROW, text)
        mismatched_row = self.EXISTING_INDEX_ROW.replace(
            "0004-retry-with-capped-exponential-backoff.md", "0004-retry-policy.md")
        readme.write_text(text.replace(self.EXISTING_INDEX_ROW, mismatched_row),
                          encoding="utf-8")

        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertFalse(by_id["readme-index-links-resolve"]["passed"],
                         by_id["readme-index-links-resolve"]["detail"])
        for check_id in ("adr-0004-house-format-sections-in-order",
                        "index-gained-a-row-for-0004", "retry-sh-links-the-adr",
                        "retry-sh-link-resolves", "exactly-one-new-adr-file",
                        "nothing-else-touched"):
            self.assertTrue(by_id[check_id]["passed"], f"{check_id}: {by_id[check_id]['detail']}")

    def test_existing_retry_sh_dangling_link_fails_only_the_link_targets_check(self):
        # S3 (round 2): a retry.sh comment naming a slug no file has — the
        # ADR itself keeps its correct name — is the twin dodge to the
        # index-row one above.
        ws = self._ws(ADRS_EXISTING_DIR)
        self._apply_correct_existing(ws)
        retry_sh = ws / "scripts" / "retry.sh"
        text = retry_sh.read_text(encoding="utf-8")
        self.assertIn("docs/decisions/0004-retry-with-capped-exponential-backoff.md", text)
        retry_sh.write_text(
            text.replace("docs/decisions/0004-retry-with-capped-exponential-backoff.md",
                        "docs/decisions/0004-retry-policy.md"),
            encoding="utf-8")

        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertFalse(by_id["retry-sh-link-resolves"]["passed"],
                         by_id["retry-sh-link-resolves"]["detail"])
        for check_id in ("adr-0004-house-format-sections-in-order",
                        "index-gained-a-row-for-0004", "retry-sh-links-the-adr",
                        "readme-index-links-resolve", "exactly-one-new-adr-file",
                        "nothing-else-touched"):
            self.assertTrue(by_id[check_id]["passed"], f"{check_id}: {by_id[check_id]['detail']}")

    def test_existing_cli_objective_only_exit_codes(self):
        ws_pristine = self._ws(ADRS_EXISTING_DIR)
        code, _ = self._run_cli(ADRS_EXISTING_DIR, ws_pristine)
        self.assertEqual(code, 1)

        ws_correct = self._ws(ADRS_EXISTING_DIR)
        self._apply_correct_existing(ws_correct)
        code, payload = self._run_cli(ADRS_EXISTING_DIR, ws_correct)
        self.assertEqual(code, 0, payload)

    def test_cli_objective_only_ignores_stale_registry_env_vars(self):
        # N3: --arm objective-only never installs a skill, so it shouldn't
        # matter that the calling shell has a stale $SKILLS_EVALS_REGISTRIES
        # or $AGENTSKILLS_DIR pointing nowhere — but run_eval.py's main()
        # resolves+validates registries before ANY arm, objective-only
        # included, so an unfixed _run_cli used to let that bogus override
        # reach the child process, main() printed a plain-text "registry
        # configuration error" and exited 2, and json.loads on that
        # non-JSON stdout raised — an ERROR, not the assertEqual(code, 1)
        # failure a real bug should produce.
        ws_pristine = self._ws(ADRS_EXISTING_DIR)
        with mock.patch.dict(os.environ, {
            "SKILLS_EVALS_REGISTRIES": "/does/not/exist/anywhere",
            "AGENTSKILLS_DIR": "/does/not/exist/either",
        }):
            code, payload = self._run_cli(ADRS_EXISTING_DIR, ws_pristine)
        self.assertEqual(code, 1, payload)
        self.assertIn("checks", payload)

    def test_existing_adr_written_but_index_not_updated_fails_only_index_check(self):
        ws = self._ws(ADRS_EXISTING_DIR)
        self._write_adr_0004(ws)
        self._link_retry_sh_existing(ws)
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertFalse(by_id["index-gained-a-row-for-0004"]["passed"])
        self.assertTrue(by_id["adr-0004-house-format-sections-in-order"]["passed"],
                        by_id["adr-0004-house-format-sections-in-order"]["detail"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-new-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_existing_adr_and_index_but_no_code_link_fails_only_link_check(self):
        ws = self._ws(ADRS_EXISTING_DIR)
        self._write_adr_0004(ws)
        self._add_index_row_existing(ws)
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertFalse(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["adr-0004-house-format-sections-in-order"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0004"]["passed"])
        self.assertTrue(by_id["exactly-one-new-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_existing_wrong_section_order_fails_only_format_check(self):
        ws = self._ws(ADRS_EXISTING_DIR)
        self._write_adr_0004(ws, self.EXISTING_ADR_0004_WRONG_ORDER)
        self._add_index_row_existing(ws)
        self._link_retry_sh_existing(ws)
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertFalse(by_id["adr-0004-house-format-sections-in-order"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0004"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-new-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_existing_retry_sh_header_gutted_fails_only_the_link_check(self):
        # N5: retry-sh-links-the-adr used to pass on the ADR path appearing
        # ANYWHERE in retry.sh, with nothing guarding the header's own
        # decision sentence — the thing the judge rubric leans on to grade
        # the ADR's content against. Keep the ADR link but gut that
        # sentence; only this check should now catch it.
        ws = self._ws(ADRS_EXISTING_DIR)
        self._apply_correct_existing(ws)
        retry_sh = ws / "scripts" / "retry.sh"
        text = retry_sh.read_text(encoding="utf-8")
        sentence = "retry a transient command failure with capped exponential backoff"
        self.assertIn(sentence, text, "retry.sh header sentence drifted out of the seed")
        retry_sh.write_text(text.replace(sentence, "do a thing"), encoding="utf-8")
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertFalse(by_id["retry-sh-links-the-adr"]["passed"],
                         by_id["retry-sh-links-the-adr"]["detail"])
        self.assertTrue(by_id["adr-0004-house-format-sections-in-order"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0004"]["passed"])
        self.assertTrue(by_id["exactly-one-new-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_existing_retry_sh_link_appended_after_body_fails_the_link_check(self):
        # N1 (round 2): retry-sh-links-the-adr's description claimed the
        # HEADER links the ADR, but the old regex matched the path ANYWHERE
        # in the file — appending the link after the function body, nowhere
        # near the header, still passed.
        ws = self._ws(ADRS_EXISTING_DIR)
        self._write_adr_0004(ws)
        self._add_index_row_existing(ws)
        retry_sh = ws / "scripts" / "retry.sh"
        retry_sh.write_text(
            retry_sh.read_text(encoding="utf-8") +
            "\n# See docs/decisions/0004-retry-with-capped-exponential-backoff.md\n",
            encoding="utf-8")
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertFalse(by_id["retry-sh-links-the-adr"]["passed"],
                         by_id["retry-sh-links-the-adr"]["detail"])
        self.assertTrue(by_id["adr-0004-house-format-sections-in-order"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0004"]["passed"])
        self.assertTrue(by_id["exactly-one-new-adr-file"]["passed"])

    def test_existing_second_adr_for_changelog_fact_fails_only_count_check(self):
        # The correct fix, PLUS an extra ADR nobody asked for, recording
        # CHANGELOG.md's routine dependency-removal fact. Everything about
        # ADR 0004 itself, the index row, and the code link is still right —
        # only the count check should catch the extra file.
        ws = self._ws(ADRS_EXISTING_DIR)
        self._apply_correct_existing(ws)
        (ws / "docs" / "decisions" / "0005-remove-moment-dependency.md").write_text(
            self.DECOY_ADR_FOR_CHANGELOG, encoding="utf-8")
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertFalse(by_id["exactly-one-new-adr-file"]["passed"],
                         by_id["exactly-one-new-adr-file"]["detail"])
        self.assertTrue(by_id["adr-0004-house-format-sections-in-order"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0004"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_existing_delete_and_replace_adr_passes_the_stale_count_check_but_fails_restraint(self):
        # S2: exactly-one-new-adr-file is a TOTAL count (min=4, max=4).
        # Deleting 0002 and adding a differently-numbered decoy (0006) for
        # the CHANGELOG's routine fact keeps the total at 4 — the count
        # check alone scores this 4/4. nothing-else-touched is what catches
        # it: 0002 must stay byte-identical, and its absence is a violation
        # even though total count still looks right.
        ws = self._ws(ADRS_EXISTING_DIR)
        self._apply_correct_existing(ws)
        (ws / "docs" / "decisions" / "0002-poll-fulfillment-service-every-30s.md").unlink()
        (ws / "docs" / "decisions" / "0006-remove-moment-dependency.md").write_text(
            self.DECOY_ADR_FOR_CHANGELOG.replace("# 0005.", "# 0006.", 1),
            encoding="utf-8")
        by_id = self._checks(ADRS_EXISTING_DIR, ws)
        self.assertTrue(by_id["exactly-one-new-adr-file"]["passed"],
                        by_id["exactly-one-new-adr-file"]["detail"])
        self.assertFalse(by_id["nothing-else-touched"]["passed"],
                         by_id["nothing-else-touched"]["detail"])
        self.assertTrue(by_id["adr-0004-house-format-sections-in-order"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0004"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])

    # ======================================================================
    # bootstrap
    # ======================================================================

    def test_bootstrap_pristine_seed_fails_every_real_check(self):
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        for check_id in ("readme-bootstrapped-in-skill-shape",
                        "index-gained-a-row-for-0001", "adr-0001-sections-in-order",
                        "retry-sh-links-the-adr", "exactly-one-adr-file",
                        "agents-md-gained-the-pointer"):
            self.assertFalse(by_id[check_id]["passed"], by_id[check_id]["detail"])
        # Restraint is a trivial pass on the pristine seed: nothing changed yet.
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_bootstrap_hand_written_correct_fix_passes_every_check(self):
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        for check_id, result in by_id.items():
            self.assertTrue(result["passed"], f"{check_id}: {result['detail']}")
        self._assert_index_link_target_exists(ws, self.BOOTSTRAP_INDEX_LINK_RE)

    def test_bootstrap_mismatched_index_slug_passes_every_fixture_check_but_fails_the_cross_check(self):
        # N4, bootstrap side: same gap as existing-convention's twin test —
        # a mismatched index-row slug still satisfies every fixture check.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        readme = ws / "docs" / "decisions" / "README.md"
        text = readme.read_text(encoding="utf-8")
        original_row = ("| [0001](0001-retry-with-capped-exponential-backoff.md) | Retry "
                        "transient failures up to 5 times with capped exponential "
                        "backoff | Accepted |")
        self.assertIn(original_row, text)
        mismatched_row = original_row.replace(
            "0001-retry-with-capped-exponential-backoff.md", "0001-retry-policy.md")
        readme.write_text(text.replace(original_row, mismatched_row), encoding="utf-8")

        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        for check_id in ("readme-bootstrapped-in-skill-shape",
                        "index-gained-a-row-for-0001", "adr-0001-sections-in-order",
                        "retry-sh-links-the-adr", "exactly-one-adr-file",
                        "nothing-else-touched", "agents-md-gained-the-pointer"):
            self.assertTrue(by_id[check_id]["passed"], f"{check_id}: {by_id[check_id]['detail']}")
        with self.assertRaises(AssertionError):
            self._assert_index_link_target_exists(ws, self.BOOTSTRAP_INDEX_LINK_RE)

    def test_bootstrap_mismatched_index_slug_fails_only_the_link_targets_check(self):
        # S3 (round 2), bootstrap side: same gap as existing-convention's
        # twin test — a dangling index-row slug is now caught by a real
        # fixture check, not only by the unit-test cross-check above.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        readme = ws / "docs" / "decisions" / "README.md"
        text = readme.read_text(encoding="utf-8")
        original_row = ("| [0001](0001-retry-with-capped-exponential-backoff.md) | Retry "
                        "transient failures up to 5 times with capped exponential "
                        "backoff | Accepted |")
        self.assertIn(original_row, text)
        mismatched_row = original_row.replace(
            "0001-retry-with-capped-exponential-backoff.md", "0001-retry-policy.md")
        readme.write_text(text.replace(original_row, mismatched_row), encoding="utf-8")

        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["readme-index-links-resolve"]["passed"],
                         by_id["readme-index-links-resolve"]["detail"])
        for check_id in ("readme-bootstrapped-in-skill-shape", "index-gained-a-row-for-0001",
                        "adr-0001-sections-in-order", "retry-sh-links-the-adr",
                        "retry-sh-link-resolves", "exactly-one-adr-file",
                        "nothing-else-touched", "agents-md-gained-the-pointer"):
            self.assertTrue(by_id[check_id]["passed"], f"{check_id}: {by_id[check_id]['detail']}")

    def test_bootstrap_retry_sh_dangling_link_fails_only_the_link_targets_check(self):
        # S3 (round 2), bootstrap side: same twin dodge as existing-
        # convention's retry.sh test.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        retry_sh = ws / "scripts" / "retry.sh"
        text = retry_sh.read_text(encoding="utf-8")
        self.assertIn("docs/decisions/0001-retry-with-capped-exponential-backoff.md", text)
        retry_sh.write_text(
            text.replace("docs/decisions/0001-retry-with-capped-exponential-backoff.md",
                        "docs/decisions/0001-retry-policy.md"),
            encoding="utf-8")

        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["retry-sh-link-resolves"]["passed"],
                         by_id["retry-sh-link-resolves"]["detail"])
        for check_id in ("readme-bootstrapped-in-skill-shape", "index-gained-a-row-for-0001",
                        "adr-0001-sections-in-order", "retry-sh-links-the-adr",
                        "readme-index-links-resolve", "exactly-one-adr-file",
                        "nothing-else-touched", "agents-md-gained-the-pointer"):
            self.assertTrue(by_id[check_id]["passed"], f"{check_id}: {by_id[check_id]['detail']}")

    def test_bootstrap_cli_objective_only_exit_codes(self):
        ws_pristine = self._ws(ADRS_BOOTSTRAP_DIR)
        code, _ = self._run_cli(ADRS_BOOTSTRAP_DIR, ws_pristine)
        self.assertEqual(code, 1)

        ws_correct = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws_correct)
        code, payload = self._run_cli(ADRS_BOOTSTRAP_DIR, ws_correct)
        self.assertEqual(code, 0, payload)

    def test_bootstrap_adr_written_but_index_not_updated_fails_only_index_check(self):
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        # README carries the bootstrap shape but never gained the 0001 row.
        readme_without_row = self.BOOTSTRAP_README.replace(
            "| [0001](0001-retry-with-capped-exponential-backoff.md) | Retry "
            "transient failures up to 5 times with capped exponential "
            "backoff | Accepted |\n", "")
        self._bootstrap_docs_decisions(ws, readme_without_row, self.BOOTSTRAP_ADR_0001)
        self._link_retry_sh_bootstrap(ws)
        self._add_agents_md_pointer_bootstrap(ws)
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"],
                        by_id["readme-bootstrapped-in-skill-shape"]["detail"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])
        self.assertTrue(by_id["agents-md-gained-the-pointer"]["passed"],
                        by_id["agents-md-gained-the-pointer"]["detail"])

    def test_bootstrap_adr_and_index_but_no_code_link_fails_only_link_check(self):
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._bootstrap_docs_decisions(ws, self.BOOTSTRAP_README, self.BOOTSTRAP_ADR_0001)
        self._add_agents_md_pointer_bootstrap(ws)
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])
        self.assertTrue(by_id["agents-md-gained-the-pointer"]["passed"])

    def test_bootstrap_wrong_section_order_fails_only_format_check(self):
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._bootstrap_docs_decisions(
            ws, self.BOOTSTRAP_README, self.BOOTSTRAP_ADR_0001_WRONG_ORDER)
        self._link_retry_sh_bootstrap(ws)
        self._add_agents_md_pointer_bootstrap(ws)
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])
        self.assertTrue(by_id["agents-md-gained-the-pointer"]["passed"])

    def test_bootstrap_retry_sh_header_gutted_fails_only_the_link_check(self):
        # N5, bootstrap side: same guard as existing-convention's twin test.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        retry_sh = ws / "scripts" / "retry.sh"
        text = retry_sh.read_text(encoding="utf-8")
        sentence = "retry a transient command failure with capped exponential backoff"
        self.assertIn(sentence, text, "retry.sh header sentence drifted out of the seed")
        retry_sh.write_text(text.replace(sentence, "do a thing"), encoding="utf-8")
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["retry-sh-links-the-adr"]["passed"],
                         by_id["retry-sh-links-the-adr"]["detail"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])
        self.assertTrue(by_id["agents-md-gained-the-pointer"]["passed"])

    def test_bootstrap_retry_sh_link_appended_after_body_fails_the_link_check(self):
        # N1 (round 2), bootstrap side: same anchoring gap as existing-
        # convention's twin test.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._bootstrap_docs_decisions(ws, self.BOOTSTRAP_README, self.BOOTSTRAP_ADR_0001)
        self._add_agents_md_pointer_bootstrap(ws)
        retry_sh = ws / "scripts" / "retry.sh"
        retry_sh.write_text(
            retry_sh.read_text(encoding="utf-8") +
            "\n# See docs/decisions/0001-retry-with-capped-exponential-backoff.md\n",
            encoding="utf-8")
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["retry-sh-links-the-adr"]["passed"],
                         by_id["retry-sh-links-the-adr"]["detail"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["agents-md-gained-the-pointer"]["passed"])

    def test_bootstrap_second_adr_for_changelog_fact_fails_only_count_check(self):
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        (ws / "docs" / "decisions" / "0002-remove-moment-dependency.md").write_text(
            self.BOOTSTRAP_DECOY_ADR_FOR_CHANGELOG, encoding="utf-8")
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["exactly-one-adr-file"]["passed"],
                         by_id["exactly-one-adr-file"]["detail"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])
        self.assertTrue(by_id["agents-md-gained-the-pointer"]["passed"])

    def test_bootstrap_touching_changelog_fails_only_restraint_check(self):
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        changelog = ws / "CHANGELOG.md"
        changelog.write_text(
            changelog.read_text(encoding="utf-8") + "\n## 1.3.1\n\n- Unrelated edit.\n",
            encoding="utf-8")
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["nothing-else-touched"]["passed"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["agents-md-gained-the-pointer"]["passed"])

    def test_bootstrap_readme_edit_fails_only_restraint_check(self):
        # The B1 bug this fixture used to have: with no AGENTS.md in the
        # seed, Bootstrap step 4 ("AGENTS.md, or README.md if there's no
        # AGENTS.md") pointed a skill-faithful agent at README.md, and that
        # correct-per-the-skill answer lost nothing-else-touched. Now the
        # seed carries an AGENTS.md, so editing README.md instead is a
        # genuine, not merely accidental, violation.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        readme = ws / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") +
            "\n### Architecture Decision Records\n\nSee `docs/decisions/`.\n",
            encoding="utf-8")
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["nothing-else-touched"]["passed"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["agents-md-gained-the-pointer"]["passed"])

    def test_bootstrap_missing_agents_md_pointer_fails_only_the_pointer_check(self):
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._bootstrap_docs_decisions(ws, self.BOOTSTRAP_README, self.BOOTSTRAP_ADR_0001)
        self._link_retry_sh_bootstrap(ws)
        # No _add_agents_md_pointer_bootstrap call: AGENTS.md stays pristine.
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["agents-md-gained-the-pointer"]["passed"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_bootstrap_agents_md_rewritten_from_scratch_fails_the_pointer_check(self):
        # A new AGENTS.md carrying the heading but none of the seed's
        # original content is a rewrite, not the append Bootstrap step 4
        # calls for — agents-md-gained-the-pointer's must_match on an
        # original paragraph is what catches this.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        (ws / "AGENTS.md").write_text(
            "# AGENTS.md\n\n### Architecture Decision Records\n\n"
            "Non-obvious decisions live in `docs/decisions/`.\n",
            encoding="utf-8")
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["agents-md-gained-the-pointer"]["passed"],
                         by_id["agents-md-gained-the-pointer"]["detail"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_bootstrap_bare_pointer_heading_with_no_link_fails_the_pointer_check(self):
        # S1 (round 2): a bare "### Architecture Decision Records" heading
        # with no link into docs/decisions/ used to satisfy
        # agents-md-gained-the-pointer (7/7) — a pointer must point.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._bootstrap_docs_decisions(ws, self.BOOTSTRAP_README, self.BOOTSTRAP_ADR_0001)
        self._link_retry_sh_bootstrap(ws)
        agents = ws / "AGENTS.md"
        agents.write_text(
            agents.read_text(encoding="utf-8") + "\n### Architecture Decision Records\n",
            encoding="utf-8")
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["agents-md-gained-the-pointer"]["passed"],
                         by_id["agents-md-gained-the-pointer"]["detail"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_bootstrap_agents_md_gutted_conventions_section_fails_the_pointer_check(self):
        # S1 (round 2): deleting AGENTS.md's ## Conventions section (which
        # names scripts/retry.sh) while keeping a correct pointer
        # heading+link still scored 7/7 — must_match only checked the
        # heading and the file's FIRST paragraph, never that the append
        # landed on top of the rest of the file rather than replacing it.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._apply_correct_bootstrap(ws)
        agents = ws / "AGENTS.md"
        text = agents.read_text(encoding="utf-8")
        gutted = text.split("## Conventions")[0] + self.BOOTSTRAP_AGENTS_MD_POINTER
        agents.write_text(gutted, encoding="utf-8")
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["agents-md-gained-the-pointer"]["passed"],
                         by_id["agents-md-gained-the-pointer"]["detail"])
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"])
        self.assertTrue(by_id["adr-0001-sections-in-order"]["passed"])
        self.assertTrue(by_id["retry-sh-links-the-adr"]["passed"])
        self.assertTrue(by_id["exactly-one-adr-file"]["passed"])
        self.assertTrue(by_id["nothing-else-touched"]["passed"])

    def test_bootstrap_adhoc_readme_shape_fails_only_the_shape_check(self):
        # readme-bootstrapped-in-skill-shape had no "present but wrong" test:
        # an ad-hoc README with an index row but none of the skill's own
        # template headings must fail ONLY this check.
        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._bootstrap_docs_decisions(ws, self.BOOTSTRAP_ADHOC_README, self.BOOTSTRAP_ADR_0001)
        self._link_retry_sh_bootstrap(ws)
        self._add_agents_md_pointer_bootstrap(ws)
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertFalse(by_id["readme-bootstrapped-in-skill-shape"]["passed"],
                         by_id["readme-bootstrapped-in-skill-shape"]["detail"])
        for check_id in ("index-gained-a-row-for-0001", "adr-0001-sections-in-order",
                         "retry-sh-links-the-adr", "exactly-one-adr-file",
                         "nothing-else-touched", "agents-md-gained-the-pointer"):
            self.assertTrue(by_id[check_id]["passed"], f"{check_id}: {by_id[check_id]['detail']}")

    # ======================================================================
    # The bootstrap README-shape check is pinned to the skill's OWN template
    # at test time, so a future edit to that template that drops one of the
    # headings this fixture relies on fails HERE, loudly, instead of the
    # fixture silently testing a shape the skill no longer produces.
    # ======================================================================

    def _derive_bootstrap_readme(self, template_text: str, index_row: str) -> str:
        """Copy the skill's own bootstrap template the way it instructs: drop
        its two-line "seeded from" quote block (both lines start with `>`) —
        NOT just the first line, which used to leave the second line's
        "house style, then delete this quote line." dangling in the derived
        README — and fill in the index row.
        """
        lines = [line for line in template_text.splitlines()
                if not line.strip().startswith(">")]
        derived = "\n".join(lines) + "\n"
        self.assertIn("| _none yet_ | | |", derived,
                      "template's empty-index placeholder drifted — update "
                      "this test's replacement below")
        return derived.replace("| _none yet_ | | |", index_row)

    def test_derive_bootstrap_readme_drops_the_whole_seeded_from_quote_block(self):
        # N2: the old filter only dropped lines starting with "> Seeded
        # from", leaving the template's second quote line ("> house style,
        # then delete this quote line.") behind in the derived README.
        template_text = (
            "# Architecture Decision Records\n\n"
            "> Seeded from the `writing-adrs` skill. Adjust wording to match "
            "this repo's\n"
            "> house style, then delete this quote line.\n\n"
            "## Index\n\n"
            "| ADR | Title | Status |\n"
            "|-----|-------|--------|\n"
            "| _none yet_ | | |\n"
        )
        derived = self._derive_bootstrap_readme(
            template_text, "| [0001](x.md) | T | Accepted |")
        self.assertNotIn(">", derived)
        self.assertNotIn("Seeded from", derived)
        self.assertNotIn("house style", derived)

    def test_bootstrap_readme_derived_from_live_skill_template_still_passes(self):
        registries = run_eval.resolve_registries(
            None, os.environ.get("SKILLS_EVALS_REGISTRIES"), REPO_ROOT,
            os.environ.get("AGENTSKILLS_DIR"))
        entry = registries["agentskills"]
        if not entry["path"].is_dir():
            reason = (f"no agentskills checkout at {entry['path']} — skipping "
                      "the live-template drift check")
            print(reason)
            self.skipTest(reason)

        glob_pattern = run_eval._skill_md_glob(entry["layout"], "writing-adrs")
        matches = sorted(p.parent for p in entry["path"].glob(glob_pattern) if p.is_file())
        if not matches:
            reason = (f"no SKILL.md matched {entry['path'] / glob_pattern} — "
                      "skipping the live-template drift check")
            print(reason)
            self.skipTest(reason)

        template_path = matches[0] / "references" / "decisions-README-template.md"
        if not template_path.is_file():
            reason = (f"writing-adrs skill has no {template_path} — skipping "
                      "the live-template drift check")
            print(reason)
            self.skipTest(reason)

        # Derive a README the way the skill instructs: copy the template,
        # drop its two-line "seeded from" quote block, fill in the index
        # row. If the live template drops one of the headings
        # readme-bootstrapped-in-skill-shape looks for, this derived text
        # stops carrying it and the assertion below is what catches the
        # drift.
        template_text = template_path.read_text(encoding="utf-8")
        derived_readme = self._derive_bootstrap_readme(
            template_text,
            "| [0001](0001-retry-with-capped-exponential-backoff.md) | Retry "
            "transient failures up to 5 times with capped exponential "
            "backoff | Accepted |")

        ws = self._ws(ADRS_BOOTSTRAP_DIR)
        self._bootstrap_docs_decisions(ws, derived_readme, self.BOOTSTRAP_ADR_0001)
        self._link_retry_sh_bootstrap(ws)
        by_id = self._checks(ADRS_BOOTSTRAP_DIR, ws)
        self.assertTrue(by_id["readme-bootstrapped-in-skill-shape"]["passed"],
                        by_id["readme-bootstrapped-in-skill-shape"]["detail"])
        self.assertTrue(by_id["index-gained-a-row-for-0001"]["passed"],
                        by_id["index-gained-a-row-for-0001"]["detail"])

    # ======================================================================
    # S6: the repo README's evals/ tree omitted writing-adrs/ entirely.
    # ======================================================================

    def test_readme_lists_the_writing_adrs_eval_directory(self):
        readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("writing-adrs/", readme_text)

    # ======================================================================
    # N1: both seeds' retry.sh cited a 2026-06-02 outage / PR #142; issue #80
    # says 2026-03 / PR #41.
    # ======================================================================

    def test_retry_sh_cites_the_issues_outage_date_and_pr_in_both_seeds(self):
        for eval_dir in (ADRS_BOOTSTRAP_DIR, ADRS_EXISTING_DIR):
            with self.subTest(eval_dir=eval_dir.name):
                text = (eval_dir / "seed" / "scripts" / "retry.sh").read_text(
                    encoding="utf-8")
                self.assertIn("2026-03", text)
                self.assertIn("PR #41", text)
                self.assertNotIn("2026-06-02", text)
                self.assertNotIn("PR #142", text)

    # ======================================================================
    # N6: both seeds' scripts/retry.sh were mode 100644; every other seed's
    # scripts are 100755.
    # ======================================================================

    def test_retry_sh_is_executable_in_both_seeds(self):
        for eval_dir in (ADRS_BOOTSTRAP_DIR, ADRS_EXISTING_DIR):
            with self.subTest(eval_dir=eval_dir.name):
                path = eval_dir / "seed" / "scripts" / "retry.sh"
                self.assertTrue(os.access(path, os.X_OK), f"{path} is not executable")

    # ======================================================================
    # N7: the two seeds must stay byte-identical except for what each
    # fixture's premise changes (existing-convention already has
    # docs/decisions/, and its AGENTS.md already carries the ADR pointer).
    # ======================================================================

    def test_seed_files_are_byte_identical_except_for_their_premise(self):
        bootstrap_seed = ADRS_BOOTSTRAP_DIR / "seed"
        existing_seed = ADRS_EXISTING_DIR / "seed"

        for rel in ("README.md", "CHANGELOG.md", "scripts/retry.sh"):
            with self.subTest(file=rel):
                self.assertEqual(
                    (bootstrap_seed / rel).read_bytes(),
                    (existing_seed / rel).read_bytes(),
                    f"{rel} differs between the two seeds")

        # AGENTS.md differs by exactly the pointer paragraph the
        # existing-convention premise (docs/decisions/ already exists) adds.
        bootstrap_agents = (bootstrap_seed / "AGENTS.md").read_text(encoding="utf-8")
        existing_agents = (existing_seed / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(
            existing_agents, bootstrap_agents + self.BOOTSTRAP_AGENTS_MD_POINTER,
            "AGENTS.md diverges by more than the ADR pointer paragraph")

        # docs/decisions/ is the other premise difference: bootstrap has none.
        self.assertFalse((bootstrap_seed / "docs").exists())
        self.assertTrue((existing_seed / "docs" / "decisions" / "README.md").is_file())

        def _files(root: Path) -> set[str]:
            return {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}

        bootstrap_files = _files(bootstrap_seed)
        existing_files = _files(existing_seed)
        self.assertEqual(bootstrap_files - existing_files, set(),
                         "bootstrap seed has files existing-convention lacks")
        self.assertEqual(existing_files - bootstrap_files, {
            "docs/decisions/README.md",
            "docs/decisions/0001-cache-order-status-in-redis.md",
            "docs/decisions/0002-poll-fulfillment-service-every-30s.md",
            "docs/decisions/0003-poll-fulfillment-service-every-10s.md",
        }, "existing-convention seed's extra files are not exactly its "
           "docs/decisions/ premise")


if __name__ == "__main__":
    unittest.main()
