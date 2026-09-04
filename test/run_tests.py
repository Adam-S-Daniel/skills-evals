#!/usr/bin/env python3
"""Test suite for the skills-evals harness.

Hermetic: no real `claude` invocation (CLAUDE_BIN always points at
test/fake-claude), no network, no writes into the repo's real results/ dir.

Run: python3 test/run_tests.py
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
HARNESS_DIR = REPO_ROOT / "harness"
FAKE_CLAUDE = TEST_DIR / "fake-claude"
FAKE_REGISTRY = TEST_DIR / "fixtures" / "fake_registry"
FAKE_REGISTRY_LEGACY = TEST_DIR / "fixtures" / "fake_registry_legacy"
EVAL_DIR = REPO_ROOT / "evals" / "workflow-path-audit"
ELEVATION_DIR = REPO_ROOT / "evals" / "windows-elevation-from-wsl"
CANARY_DIR = REPO_ROOT / "evals" / "guidance-bridge-canary"

sys.path.insert(0, str(HARNESS_DIR))
import roster  # noqa: E402
import run_eval  # noqa: E402
import timeweeks  # noqa: E402
from scorers import judge, objective  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import make_badge  # noqa: E402
import model_usage_census  # noqa: E402
import refresh_models  # noqa: E402


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


class TestIssue67(unittest.TestCase):
    """Model roster: availability + usage -> arms/judge/preflight (#67).

    Every model id below is TEST FIXTURE data. The policy code under test
    carries none: tiers are inferred from the id's family word, and the family
    words themselves live in evals/roster-policy.yml. `test_no_model_ids_are
    _hardcoded_outside_fixtures` is the guard that keeps it that way.

    `NOW` is frozen so the ISO-week windows and the 7-day cooling-off are
    decidable rather than wall-clock-dependent — the harness-wide "hermetic,
    always" rule (DESIGN.md) applies to time as much as to network.
    """

    NOW = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)
    # 2026-09-04 is ISO week 36; the four- and eight-week windows below run
    # back from it. Spelled out rather than computed, so a bug in the
    # implementation's own week arithmetic cannot hide inside the fixture.
    W = ["2026-W36", "2026-W35", "2026-W34", "2026-W33",
         "2026-W32", "2026-W31", "2026-W30", "2026-W29"]

    POLICY = REPO_ROOT / "evals" / "roster-policy.yml"

    # --- fixture builders -------------------------------------------------

    @staticmethod
    def _model(model_id, created, *, max_input=1_000_000, max_output=128_000):
        return {"id": model_id, "display_name": model_id, "created_at": created,
                "max_input_tokens": max_input, "max_tokens": max_output,
                "capabilities": {"thinking": {"supported": True}}}

    @classmethod
    def _models_doc(cls, extra=None, drop=()):
        """A canned GET /v1/models payload spanning all four tiers.

        claude-fable-5-1 is deliberately 3 days old: it is the newest model in
        its tier but inside the cooling-off window, so it is NOT an arm — which
        is what leaves a tier above the strongest arm for the judge to come
        from.
        """
        models = [
            cls._model("claude-haiku-4-5", "2025-10-01T00:00:00Z", max_input=200_000),
            cls._model("claude-sonnet-4-6", "2025-11-24T00:00:00Z"),
            cls._model("claude-sonnet-5", "2026-02-01T00:00:00Z"),
            cls._model("claude-opus-4-8", "2026-01-15T00:00:00Z"),
            cls._model("claude-opus-5", "2026-04-01T00:00:00Z"),
            cls._model("claude-fable-5-1", "2026-09-01T00:00:00Z"),
        ]
        models = [m for m in models if m["id"] not in drop]
        models += list(extra or [])
        return {"fetched_at": "2026-09-04T11:00:00Z", "models": models}

    @classmethod
    def _census_doc(cls, counts=None, generated_at="2026-09-04T06:00:00Z"):
        if counts is None:
            counts = {
                # last four weeks: 400 / 620 = 64.5%
                "claude-sonnet-5": {w: 100 for w in cls.W[:4]},
                # last four weeks: 200 / 620 = 32.3%
                "claude-opus-5": {w: 50 for w in cls.W[:4]},
                # last four weeks: 20 / 620 = 3.2% — under the 10% entry bar
                "claude-haiku-4-5": {w: 5 for w in cls.W[:4]},
                # all outside the four-week window
                "claude-sonnet-4-6": {cls.W[7]: 100},
            }
        return {"generated_at": generated_at, "weeks": cls.W, "counts": counts}

    @classmethod
    def _policy(cls):
        return roster.load_policy(cls.POLICY)

    #: distinguishes "use the default fixture" from "there is no census at all",
    #: which None cannot do here — the absence IS one of the cases under test.
    DEFAULT = object()

    @classmethod
    def _compute(cls, models=DEFAULT, census=DEFAULT, previous=None):
        return roster.compute_roster(
            models_doc=cls._models_doc() if models is cls.DEFAULT else models,
            census_doc=cls._census_doc() if census is cls.DEFAULT else census,
            policy=cls._policy(), previous=previous, now=cls.NOW)

    @staticmethod
    def _arm_ids(result):
        return [a["id"] for a in result["arms"]]

    @staticmethod
    def _reason(result, model_id):
        return next(a["reason"] for a in result["arms"] if a["id"] == model_id)

    # --- policy: the headline case ---------------------------------------

    def test_canned_models_and_census_give_the_expected_roster(self):
        result = self._compute()

        self.assertEqual(sorted(self._arm_ids(result)),
                         ["claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5"])
        # Usage-qualified arms say so, in words, with the share.
        self.assertIn("64.5%", self._reason(result, "claude-sonnet-5"))
        self.assertIn("4 weeks", self._reason(result, "claude-sonnet-5"))
        # haiku is under the 10% bar and rides in on newest-in-tier instead.
        self.assertIn("newest", self._reason(result, "claude-haiku-4-5"))
        self.assertIn("haiku", self._reason(result, "claude-haiku-4-5"))

        # One tier above the strongest arm (opus) is fable, and the only fable
        # model available is not an arm — so it is the judge.
        self.assertEqual(result["judge"]["id"], "claude-fable-5-1")
        self.assertIn("tier above", result["judge"]["reason"])

        self.assertEqual(result["preflight"]["id"], "claude-haiku-4-5")
        self.assertIn("cheapest", result["preflight"]["reason"])

        self.assertEqual(result["source"]["models_api_at"], "2026-09-04T11:00:00Z")
        self.assertEqual(result["source"]["census_at"], "2026-09-04T06:00:00Z")
        self.assertIsNone(result["source"]["admin_report_at"])
        self.assertIn("generated_at", result)

    def test_judge_is_never_an_arm_model(self):
        # Strip the fable tier: the strongest arm is then opus-5 with nothing
        # above it, so the judge falls back to the strongest AVAILABLE model —
        # which must still not be one of the arms.
        result = self._compute(models=self._models_doc(drop={"claude-fable-5-1"}))
        self.assertNotIn(result["judge"]["id"], self._arm_ids(result))
        self.assertEqual(result["judge"]["id"], "claude-opus-4-8")
        self.assertIn("strongest available", result["judge"]["reason"])

    def test_judge_falls_back_when_every_available_model_is_an_arm(self):
        """The first real run's state: no census published yet, so the arm set
        is newest-per-tier — which on a one-current-model-per-tier catalogue is
        every model there is. A null judge would be a hole in the published
        roster, so the strongest available model is named and the reason says
        plainly that it is also an arm."""
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-haiku-4-5", "2025-10-01T00:00:00Z"),
            self._model("claude-sonnet-5", "2026-02-01T00:00:00Z"),
            self._model("claude-opus-5", "2026-04-01T00:00:00Z"),
            self._model("claude-fable-5-1", "2026-05-01T00:00:00Z"),
        ]}
        result = self._compute(models=models, census=None)
        self.assertEqual(sorted(self._arm_ids(result)),
                         ["claude-fable-5-1", "claude-haiku-4-5",
                          "claude-opus-5", "claude-sonnet-5"])
        self.assertEqual(result["judge"]["id"], "claude-fable-5-1")
        self.assertIn("every available model is currently an arm",
                      result["judge"]["reason"])

    def test_preflight_is_the_cheapest_available_model(self):
        # Drop the whole haiku tier and the cheapest becomes the newest sonnet.
        result = self._compute(models=self._models_doc(drop={"claude-haiku-4-5"}))
        self.assertEqual(result["preflight"]["id"], "claude-sonnet-5")

    # --- the 7-day cooling-off -------------------------------------------

    def test_seven_day_rule_excludes_a_model_created_yesterday(self):
        yesterday = (self.NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        models = self._models_doc(
            extra=[self._model("claude-sonnet-6", yesterday)])
        result = self._compute(models=models)
        self.assertNotIn("claude-sonnet-6", self._arm_ids(result),
                         "a model one day old is inside the fleet's 7-day "
                         "cooling-off and must not enter the arm set on the "
                         "newest-in-tier rule")
        # ... and the tier's previous newest keeps the seat.
        self.assertIn("claude-sonnet-5", self._arm_ids(result))

    def test_a_brand_new_model_still_enters_on_usage(self):
        # The cooling-off gates the newest-in-tier rule only. A model the fleet
        # is demonstrably already using is an arm on the usage rule regardless
        # of age — otherwise the roster would refuse to measure what is in use.
        yesterday = (self.NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        models = self._models_doc(extra=[self._model("claude-sonnet-6", yesterday)])
        census = self._census_doc(counts={
            "claude-sonnet-6": {self.W[0]: 300},
            "claude-sonnet-5": {w: 100 for w in self.W[:4]},
        })
        result = self._compute(models=models, census=census)
        self.assertIn("claude-sonnet-6", self._arm_ids(result))
        self.assertIn("usage", self._reason(result, "claude-sonnet-6"))

    # --- leaving the arm set ---------------------------------------------

    def test_model_missing_from_the_api_is_retired_even_with_high_usage(self):
        previous = {"arms": [{"id": "claude-opus-4-7", "reason": "was an arm"}],
                    "judge": {"id": "claude-fable-5-1", "reason": ""},
                    "preflight": {"id": "claude-haiku-4-5", "reason": ""}}
        census = self._census_doc(counts={
            "claude-opus-4-7": {w: 400 for w in self.W},   # ~66% of everything
            "claude-sonnet-5": {w: 200 for w in self.W},
        })
        result = self._compute(census=census, previous=previous)

        self.assertNotIn("claude-opus-4-7", self._arm_ids(result))
        retired = {r["id"]: r["reason"] for r in result["retired_since_last"]}
        self.assertIn("claude-opus-4-7", retired)
        self.assertIn("Models API", retired["claude-opus-4-7"])

    def test_a_previous_arm_is_held_over_until_it_is_under_two_percent(self):
        previous = {"arms": [{"id": "claude-sonnet-4-6", "reason": "was an arm"},
                             {"id": "claude-opus-4-8", "reason": "was an arm"}],
                    "judge": {"id": "claude-fable-5-1", "reason": ""},
                    "preflight": {"id": "claude-haiku-4-5", "reason": ""}}
        census = self._census_doc(counts={
            "claude-sonnet-5": {w: 100 for w in self.W},           # 800
            # 40/week over 8 weeks = 320/1128 ≈ 28% of the 8-week window but
            # only 160/560 of the 4-week one... keep it simple: sonnet-4-6 sits
            # above 2% over 8 weeks, opus-4-8 below it.
            "claude-sonnet-4-6": {w: 10 for w in self.W},          # 80
            "claude-opus-4-8": {self.W[7]: 2},                     # 2
        })
        result = self._compute(census=census, previous=previous)

        arms = self._arm_ids(result)
        self.assertIn("claude-sonnet-4-6", arms,
                      "a previous arm above the 2% exit bar over 8 weeks stays")
        self.assertIn("held over", self._reason(result, "claude-sonnet-4-6"))
        self.assertNotIn("claude-opus-4-8", arms)
        retired = {r["id"]: r["reason"] for r in result["retired_since_last"]}
        self.assertIn("claude-opus-4-8", retired)
        self.assertIn("2", retired["claude-opus-4-8"])
        self.assertIn("8 weeks", retired["claude-opus-4-8"])

    def test_added_since_last_names_the_new_arms_with_their_reason(self):
        previous = {"arms": [{"id": "claude-sonnet-5", "reason": "was an arm"}],
                    "judge": {"id": "claude-fable-5-1", "reason": ""},
                    "preflight": {"id": "claude-haiku-4-5", "reason": ""}}
        result = self._compute(previous=previous)
        added = {a["id"]: a["reason"] for a in result["added_since_last"]}
        self.assertEqual(sorted(added), ["claude-haiku-4-5", "claude-opus-5"])
        self.assertTrue(all(added.values()), "every entry carries its reason")

    def test_first_run_has_no_previous_roster_and_reports_nothing_retired(self):
        result = self._compute(previous=None)
        self.assertEqual(result["retired_since_last"], [])
        # Everything is new, but with no previous roster there is no "since
        # last" to speak of — an empty added list, not the whole arm set.
        self.assertEqual(result["added_since_last"], [])

    # --- the census fallback ---------------------------------------------

    def test_absent_census_falls_back_to_newest_per_tier_and_says_so(self):
        result = self._compute(census=None)
        self.assertEqual(sorted(self._arm_ids(result)),
                         ["claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5"])
        for arm in result["arms"]:
            self.assertIn("no fresh census", arm["reason"].lower())
        self.assertIsNone(result["source"]["census_at"])

    def test_stale_census_falls_back_the_same_way(self):
        stale = self._census_doc(generated_at="2026-08-01T00:00:00Z")  # 34 days
        result = self._compute(census=stale)
        for arm in result["arms"]:
            self.assertIn("no fresh census", arm["reason"].lower())
        # The usage-only arm set would have been different, which is the whole
        # point of saying so in the file rather than publishing it silently.
        self.assertIn("claude-haiku-4-5", self._arm_ids(result))

    def test_a_census_inside_the_freshness_window_is_used(self):
        fresh = self._census_doc(generated_at="2026-08-25T00:00:00Z")  # 10 days
        result = self._compute(census=fresh)
        self.assertNotIn("no fresh census", self._reason(result, "claude-sonnet-5").lower())

    # --- the census parser, and its privacy guard ------------------------

    def test_census_emits_only_model_week_counts_and_leaks_nothing(self):
        """MANDATORY (#67 guardrail): the census output is public data on a
        public branch. A fixture transcript carrying a project path and prose
        must yield neither — in its VALUES or in its KEYS.

        The hostile `message.model` values below are the review round's
        addition (B1): that field is whatever the routing layer wrote, and it
        was being copied verbatim into a top-level key. TestIssue67Review
        takes each of them apart individually; here they ride along in the one
        test nobody is allowed to delete.
        """
        secret_path = "/home/example/repos/private-client-work"
        secret_text = "the merger closes on Tuesday"
        account_arn = ("arn:aws:bedrock:us-east-1:123456789012:"
                       "application-inference-profile/abcd1234")
        gcp_path = ("projects/example-gcp-project/locations/us-east5/"
                    "publishers/anthropic/models/claude-opus-5")
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects" / "-home-example-repos-private-client-work"
            projects.mkdir(parents=True)
            hostile = [
                {"type": "assistant", "timestamp": "2026-09-03T10:00:02Z",
                 "message": {"role": "assistant", "model": value}}
                for value in (account_arn, gcp_path, secret_path, secret_text,
                              {"id": "claude-opus-5"}, ["claude-opus-5"], 7)
            ]
            entries = [
                {"type": "user", "cwd": secret_path,
                 "sessionId": "11111111-2222-4333-8444-555555555555",
                 "timestamp": "2026-09-03T10:00:00Z",
                 "message": {"role": "user", "content": secret_text}},
                {"type": "assistant", "cwd": secret_path,
                 "sessionId": "11111111-2222-4333-8444-555555555555",
                 "timestamp": "2026-09-03T10:00:01Z",
                 "message": {"role": "assistant", "model": "claude-opus-5",
                             "content": [{"type": "text", "text": secret_text}]}},
                {"type": "assistant", "cwd": secret_path,
                 "sessionId": "11111111-2222-4333-8444-555555555555",
                 "timestamp": "2026-08-27T09:00:00Z",
                 "message": {"role": "assistant", "model": "claude-haiku-4-5",
                             "content": [{"type": "text", "text": secret_text}]}},
            ]
            entries += hostile
            path = projects / "session.jsonl"
            path.write_text("\n".join(json.dumps(e) for e in entries) + "\n",
                            encoding="utf-8")
            # Explicit mtime: the census skips transcripts last written before
            # the window, so a wall-clock mtime would make this test's verdict
            # depend on the year the suite runs in.
            stamp = self.NOW.timestamp()
            os.utime(path, (stamp, stamp))

            counts = model_usage_census.census_counts(
                Path(tmp) / "projects", now=self.NOW, weeks=8)
            self.assertEqual(counts, {"claude-opus-5": {"2026-W36": 1},
                                      "claude-haiku-4-5": {"2026-W35": 1},
                                      model_usage_census.OTHER_KEY: {"2026-W36": 7}})

            document = model_usage_census.build_document(
                Path(tmp) / "projects", now=self.NOW, weeks=8)
            blob = json.dumps(document)
            for key in document["counts"]:
                self.assertTrue(
                    model_usage_census.MODEL_ID_RE.match(key)
                    or key == model_usage_census.OTHER_KEY,
                    f"census published {key!r} as a key on a public branch")
            self.assertNotIn(secret_path, blob)
            self.assertNotIn(secret_text, blob)
            self.assertNotIn("123456789012", blob)
            self.assertNotIn("example-gcp-project", blob)
            self.assertNotIn("private-client-work", blob)
            self.assertNotIn("session.jsonl", blob)
            self.assertNotIn("11111111-2222-4333-8444-555555555555", blob)
            # Keys are exactly the published contract — nothing else rides along.
            self.assertEqual(sorted(document), ["counts", "generated_at", "weeks"])

    def test_census_ignores_entries_outside_the_window_and_without_a_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects" / "-tmp-x"
            projects.mkdir(parents=True)
            entries = [
                # 12 weeks back — outside an 8-week window.
                {"type": "assistant", "timestamp": "2026-06-12T10:00:00Z",
                 "message": {"model": "claude-opus-4-8"}},
                # assistant entry with no model at all
                {"type": "assistant", "timestamp": "2026-09-03T10:00:00Z",
                 "message": {"role": "assistant"}},
                # a summary/system line the loader must not count
                {"type": "summary", "timestamp": "2026-09-03T10:00:00Z",
                 "message": {"model": "claude-opus-5"}},
            ]
            path = projects / "s.jsonl"
            path.write_text("\n".join(json.dumps(e) for e in entries) + "\nnot json\n",
                            encoding="utf-8")
            stamp = self.NOW.timestamp()
            os.utime(path, (stamp, stamp))
            counts = model_usage_census.census_counts(
                Path(tmp) / "projects", now=self.NOW, weeks=8)
            self.assertEqual(counts, {})

    # --- availability refresh --------------------------------------------

    def test_refresh_models_normalizes_the_models_api_payload(self):
        page = {"data": [
            {"id": "claude-opus-5", "display_name": "Claude Opus 5",
             "created_at": "2026-04-01T00:00:00Z", "max_input_tokens": 1000000,
             "max_tokens": 128000, "capabilities": {"thinking": {"supported": True}},
             "type": "model"},
            {"id": "some-other-vendor-model", "display_name": "Other",
             "created_at": "2026-04-01T00:00:00Z", "max_input_tokens": 1,
             "max_tokens": 1, "capabilities": {}, "type": "model"},
        ], "has_more": False}
        doc = refresh_models.build_models_document(
            lambda url, headers: page, now=self.NOW)
        self.assertEqual([m["id"] for m in doc["models"]], ["claude-opus-5"],
                         "only Claude models are written to the roster input")
        model = doc["models"][0]
        for field in ("max_input_tokens", "max_tokens", "capabilities", "created_at"):
            self.assertIn(field, model)
        self.assertEqual(doc["fetched_at"], "2026-09-04T12:00:00Z")

    def test_admin_report_fails_soft_with_a_notice_naming_the_secret(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_ADMIN_KEY", None)
            report, notice = refresh_models.fetch_admin_usage_report(
                now=self.NOW, fetch=None)
        self.assertIsNone(report)
        self.assertTrue(notice.startswith("::notice::"), notice)
        self.assertIn("ANTHROPIC_ADMIN_KEY", notice)

    # --- consumption by the runner ---------------------------------------

    def _fixture_dir(self, tmp, pinned):
        eval_dir = Path(tmp) / "evals" / "a-skill"
        (eval_dir / "seed").mkdir(parents=True)
        (eval_dir / "seed" / "README.md").write_text("seed\n", encoding="utf-8")
        fixture = {"skill": "a-skill", "prompt": "do the thing",
                   "judge_rubric": "grade it", "arms": {"without_skill": {"install": "none"}}}
        if pinned:
            fixture["model"] = "claude-sonnet-4-6"
            fixture["judge"] = {"model": "claude-opus-4-6"}
        (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture), encoding="utf-8")
        return eval_dir

    def _roster_file(self, tmp):
        path = Path(tmp) / "roster" / "latest.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(self._compute()), encoding="utf-8")
        return path

    def _capture_models(self, eval_dir, roster_path, want="models"):
        """Run one arm with the agent and judge stubbed, returning the models
        the runner actually chose."""
        seen = {}

        def fake_run_agent(workspace, prompt, arm):
            seen["agent"] = arm.get("model")
            return {"transcript": "done", "usage": {}, "cost_usd": 0.0,
                    "num_turns": 1, "duration_ms": 1, "raw": {}}

        def fake_score(rubric, transcript, diff, model=None, **kwargs):
            seen["judge"] = model
            return {"dimensions": [], "overall": 1.0}

        args = argparse.Namespace(
            model=None, timeout=30, no_judge=False,
            results_dir=Path(tempfile.mkdtemp()), roster=roster_path)
        self.addCleanup(shutil.rmtree, args.results_dir, ignore_errors=True)
        fixture = run_eval.load_fixture(eval_dir)
        with mock.patch.object(run_eval, "run_agent", fake_run_agent), \
             mock.patch.object(run_eval.judge, "score", fake_score):
            summary = run_eval._run_arm(
                "without_skill", fixture, eval_dir / "seed",
                Path("/nonexistent-registry"), args, "20260904T120000Z")
        return summary if want == "summary" else seen

    def test_runner_takes_the_roster_when_the_fixture_has_no_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=False)
            seen = self._capture_models(eval_dir, self._roster_file(tmp))
        expected = self._compute()
        self.assertEqual(seen["agent"], expected["arms"][0]["id"])
        self.assertEqual(seen["judge"], expected["judge"]["id"])

    def test_runner_takes_the_fixture_pin_when_it_has_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=True)
            seen = self._capture_models(eval_dir, self._roster_file(tmp))
        self.assertEqual(seen["agent"], "claude-sonnet-4-6")
        self.assertEqual(seen["judge"], "claude-opus-4-6")

    def test_runner_survives_a_missing_roster(self):
        """It no longer falls through to the CLI default: an unpinned fixture
        with no usable roster is a RUNNER-level error naming the path it
        looked for (the exit-2 path), while a pinned fixture is unaffected and
        still runs with no roster at all. TestIssue67Review covers both sides
        in detail; this is the regression floor for the change of contract."""
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=False)
            missing = Path(tmp) / "nope.json"
            summary = self._capture_models(eval_dir, missing, want="summary")
        self.assertIsNotNone(summary["error"])
        self.assertIn(str(missing), summary["error"]["detail"])

        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=True)
            seen = self._capture_models(eval_dir, Path(tmp) / "nope.json")
        self.assertEqual(seen["agent"], "claude-sonnet-4-6",
                         "a pinned fixture still runs with no roster at all")

    # --- policy file + the no-hardcoded-ids guard ------------------------

    def test_policy_file_carries_the_thresholds_and_the_adr_placeholder(self):
        raw = self.POLICY.read_text(encoding="utf-8")
        policy = self._policy()
        self.assertEqual(policy["cooling_off_days"], 7)
        self.assertEqual(policy["arm_enter_usage_pct"], 10)
        self.assertEqual(policy["arm_enter_window_weeks"], 4)
        self.assertEqual(policy["arm_exit_usage_pct"], 2)
        self.assertEqual(policy["arm_exit_window_weeks"], 8)
        self.assertEqual(policy["census_max_age_days"], 14)
        self.assertEqual(roster.tier_rungs(policy),
                         [["haiku"], ["sonnet"], ["opus"], ["fable", "mythos"]],
                         "a rung may name peers that rank identically")
        self.assertIn("#73", raw, "roster-policy.yml must point at the ADR "
                                  "sub-issue until the ADR itself exists")

    #: Anything a maintainer marks with this on the SAME LINE is allowed to
    #: carry a model id, and each file gets at most one. The marker is the
    #: whole of the exemption: an unmarked literal is a bug by definition.
    FALLBACK_MARKER = "ROSTER FALLBACK"

    def _model_id_pattern(self):
        """The shape of a model id, with the family words taken FROM THE
        POLICY rather than restated here.

        A literal alternation drifts the moment a rung is added — the guard
        would then stop looking for the very family that was just introduced,
        and go on passing. Deriving it means a new rung is covered the day it
        lands.

        The trailing group is `-<anything lowercase>`, repeated: it catches
        `claude-opus-4-8`, the older `claude-3-opus-20240229` (hence the
        optional numeric segment BEFORE the family word) and the alias shapes
        like `claude-opus-latest` — all of which the previous
        `-(family)-[0-9]` pattern walked straight past.
        """
        families = "|".join(re.escape(w) for w in roster.tier_words(self._policy()))
        return re.compile(rf"claude-(?:[0-9]+-)?(?:{families})(?:-[0-9a-z.]+)+")

    def test_no_model_ids_are_hardcoded_outside_fixtures(self):
        # Fixtures may pin a model; the roster machinery may not, or the whole
        # point of computing the roster from the API is lost the first time a
        # model retires. eval.yml and run_eval.py are in scope because that is
        # where the two surviving literals were: the preflight's hardcoded
        # `--model`, and the runner's fall-through to the CLI default.
        pattern = self._model_id_pattern()
        # Self-check: the pattern must actually match the shapes it claims to.
        for shape in ("claude-opus-4-8", "claude-3-opus-20240229",
                      "claude-opus-latest", "claude-mythos-5-1"):
            self.assertRegex(shape, pattern, "the guard's own pattern is inert")
        for rel in ("harness/roster.py", "harness/timeweeks.py",
                    "harness/run_eval.py", "scripts/refresh_models.py",
                    "scripts/model_usage_census.py", "evals/roster-policy.yml",
                    ".github/workflows/eval.yml"):
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            offenders = [line for line in text.splitlines()
                         if pattern.search(line)
                         and self.FALLBACK_MARKER not in line]
            self.assertEqual(offenders, [], f"{rel} hardcodes a model id")
            marked = [line for line in text.splitlines()
                      if self.FALLBACK_MARKER in line and pattern.search(line)]
            self.assertLessEqual(len(marked), 1,
                                 f"{rel} carries more than one marked fallback "
                                 f"literal; there is only ever one")

    # --- eval.yml -----------------------------------------------------------

    def _eval_workflow(self):
        path = REPO_ROOT / ".github" / "workflows" / "eval.yml"
        return path.read_text(encoding="utf-8"), yaml.safe_load(
            path.read_text(encoding="utf-8"))

    def test_eval_workflow_refreshes_the_roster_before_running_the_eval(self):
        _, doc = self._eval_workflow()
        steps = doc["jobs"]["eval"]["steps"]
        names = [s.get("name", "") for s in steps]
        refresh = next(i for i, n in enumerate(names) if "roster" in n.lower())
        run = next(i for i, n in enumerate(names) if n.startswith("Run the eval"))
        self.assertLess(refresh, run,
                        "the roster has to exist before the eval reads it")
        script = steps[refresh]["run"]
        self.assertIn("GITHUB_STEP_SUMMARY", script,
                      "#67: the computed roster is called out in the job summary")
        self.assertIn("roster.py", script)
        self.assertIn("refresh_models.py", script)

    def test_eval_workflow_commits_the_roster(self):
        _, doc = self._eval_workflow()
        commit = next(s for s in doc["jobs"]["eval"]["steps"]
                      if "git checkout -B eval-results" in (s.get("run") or ""))
        self.assertIn("roster", commit["run"],
                      "roster/ is published on eval-results alongside the badge")

    def test_eval_workflow_keeps_its_security_posture(self):
        raw, doc = self._eval_workflow()
        triggers = doc.get("on", doc.get(True))
        self.assertEqual(sorted(triggers), ["schedule", "workflow_dispatch"],
                         "eval.yml holds a credential and runs the agent under "
                         "bypassPermissions — no pull_request trigger, ever")
        self.assertEqual(doc["permissions"], {"contents": "write", "id-token": "write"})
        for step in doc["jobs"]["eval"]["steps"]:
            script = step.get("run") or ""
            self.assertNotIn("${{", script,
                             f"step {step.get('name')!r} interpolates into a "
                             "run: block; read inputs from $GITHUB_EVENT_PATH")
            uses = step.get("uses")
            if uses:
                self.assertRegex(uses, r"^[\w.\-/]+@[0-9a-f]{40}$",
                                 "every uses: is a bare 40-hex SHA, no comment")
        self.assertNotIn("ANTHROPIC_API_KEY", raw,
                         "auth is WIF-derived; no stored key shape is added")
        # The bare-SHA rule is LEXICAL and yaml.safe_load strips comments, so
        # `uses: owner/repo@<sha> # v4` sailed through the parsed check above
        # (mutation-proven). Re-assert it on the raw text, where the comment
        # still exists. TestIssue67Review carries the same rule; the
        # duplication is deliberate — this is the test nobody may delete.
        for line in raw.splitlines():
            if re.match(r"^\s*(?:-\s+)?uses:", line):
                self.assertRegex(line, r"^\s*(?:-\s+)?uses:\s*\S+@[0-9a-f]{40}\s*$",
                                 "a `uses:` pin carries a trailing comment")
        for step in doc["jobs"]["eval"]["steps"]:
            if (step.get("uses") or "").startswith("actions/checkout@"):
                self.assertIs((step.get("with") or {}).get("persist-credentials"),
                              False, f"checkout step {step.get('name')!r} keeps a "
                                     "GitHub credential on the runner")
        self.assertEqual(doc["concurrency"],
                         {"group": "real-eval", "cancel-in-progress": False},
                         "the badge commit races itself without this lane")


class TestIssue67Review(unittest.TestCase):
    """Review-round fixes on top of #67's roster feature (PR #129, round 1).

    A SIBLING of TestIssue67, not a subclass: it reuses that class's canned
    documents (they are classmethods for exactly this reason) so the two are
    testing one model of the policy, but its own tests run once, not twice.

    Same hermetic rules: frozen `now`, no network, no real `claude`, and
    `example`-shaped stand-ins for anything that would name a real account,
    project or path.
    """

    NOW = TestIssue67.NOW
    W = TestIssue67.W
    POLICY = TestIssue67.POLICY

    @classmethod
    def _models_doc(cls, extra=None, drop=()):
        return TestIssue67._models_doc(extra=extra, drop=drop)

    @classmethod
    def _census_doc(cls, counts=None, generated_at="2026-09-04T06:00:00Z"):
        return TestIssue67._census_doc(counts=counts, generated_at=generated_at)

    @classmethod
    def _policy(cls):
        return TestIssue67._policy()

    @classmethod
    def _compute(cls, models=TestIssue67.DEFAULT, census=TestIssue67.DEFAULT,
                 previous=None):
        return TestIssue67._compute(models=models, census=census, previous=previous)

    _arm_ids = staticmethod(TestIssue67._arm_ids)
    _reason = staticmethod(TestIssue67._reason)

    # --- shared fixture helpers ------------------------------------------

    @staticmethod
    def _write_transcript(path: Path, entries: list, mtime: datetime) -> Path:
        """A JSONL transcript with an EXPLICIT mtime.

        The census skips transcripts whose mtime falls before the window
        (N6), so a fixture that relied on the wall clock for its mtime would
        pass or fail depending on the year the suite is run in. Setting it
        explicitly keeps the hermetic-time rule intact.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(e) for e in entries) + "\n",
                        encoding="utf-8")
        stamp = mtime.timestamp()
        os.utime(path, (stamp, stamp))
        return path

    def _assistant(self, model, when, **extra):
        entry = {"type": "assistant", "timestamp": when,
                 "message": {"role": "assistant", "model": model}}
        entry["message"].update(extra.pop("message_extra", {}))
        entry.update(extra)
        return entry

    # --- B1: the census publishes model-id-shaped keys, or `other` -------

    #: The values a real transcript can carry in `message.model` that are NOT
    #: model ids. Every one of these was found in a real routing setup; each
    #: would have been copied verbatim into a key of a file on a public
    #: branch. `example`-shaped stand-ins only — no real account or project.
    HOSTILE_MODELS = {
        "bedrock_arn": ("arn:aws:bedrock:us-east-1:123456789012:"
                        "application-inference-profile/abcd1234"),
        "vertex_path": ("projects/example-gcp-project/locations/us-east5/"
                        "publishers/anthropic/models/claude-opus-5"),
        "fs_path": "/home/example/repos/example-private-client/model.json",
        "prose": "the model I used for the merger memo",
        # These four ARE lowercase-and-dashes — the exact shape `MODEL_ID_RE`
        # accepts — so a regex weakened in one specific way lets each one
        # straight through as its own published key:
        "dashed_no_family_word": "claude-home-user-secret-client-northrop-merger",
        "dashed_too_long": "claude-" + "x" * 80,
        # only the length-40 cap keeps this one out — it carries a real
        # family word (`opus`) and every dash-token is well under the
        # per-token 20-char sub-cap, so widening the overall cap (e.g. to
        # 2000) is the ONLY thing that would admit it.
        "dashed_long_with_family_word": ("claude-" +
                                         "-".join(["pad12345678"] * 4) + "-opus"),
        # only the `claude` prefix requirement keeps this one out — it is
        # otherwise a well-formed, short, family-word-bearing id shape.
        "family_word_without_claude_prefix": "internal-proxy-opus-route",
    }

    #: The only key this test's transcript can honestly earn — an
    #: independent oracle, not `MODEL_ID_RE` checking itself. Item 7 (#129
    #: review round 2): the old assertion just re-ran the production regex
    #: against its own output, so a mutation weakening the regex (dropping
    #: the anchor, widening the length cap) stayed green — every hostile
    #: value it let through still "matched MODEL_ID_RE" by definition.
    GOOD_KEYS = {"claude-opus-5"}

    def test_census_publishes_only_model_id_shaped_keys(self):
        """B1: `message.model` is attacker-adjacent data — it is whatever the
        routing layer wrote — and it became a top-level KEY of a public file."""
        values = list(self.HOSTILE_MODELS.values()) + [
            {"id": "claude-opus-5", "provider": "example"},   # a dict
            ["claude-opus-5"],                                 # a list
            7,                                                 # an int
            "claude-opus-5",                                   # the honest case
        ]
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            self._write_transcript(
                projects / "-home-example-x" / "s.jsonl",
                [self._assistant(v, "2026-09-03T10:00:00Z") for v in values],
                mtime=self.NOW)
            counts = model_usage_census.census_counts(projects, now=self.NOW, weeks=8)

        for key in counts:
            with self.subTest(key=key):
                self.assertTrue(
                    key in self.GOOD_KEYS or key == model_usage_census.OTHER_KEY,
                    f"census published {key!r} as a key on a public branch")
        non_conforming = len(values) - 1  # every value but the one honest id
        self.assertEqual(counts[model_usage_census.OTHER_KEY]["2026-W36"],
                         non_conforming)
        self.assertEqual(counts["claude-opus-5"]["2026-W36"], 1)

    def test_census_never_stringifies_a_non_string_model(self):
        """`str(some_dict)` is `repr()` — it publishes every value inside."""
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            self._write_transcript(
                projects / "-home-example-x" / "s.jsonl",
                [self._assistant({"id": "claude-opus-5", "api_key": "sk-ant-example"},
                                 "2026-09-03T10:00:00Z")],
                mtime=self.NOW)
            document = model_usage_census.build_document(projects, now=self.NOW, weeks=8)
        blob = json.dumps(document)
        self.assertNotIn("sk-ant-example", blob)
        self.assertNotIn("api_key", blob)
        self.assertEqual(list(document["counts"]), [model_usage_census.OTHER_KEY])

    def test_census_main_prints_nothing_from_under_the_projects_tree(self):
        """The status line is the other public surface: CI logs are public."""
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            out = Path(tmp) / "published" / "usage.json"
            self._write_transcript(
                projects / "-home-example-repos-private-client-work" / "s.jsonl",
                [self._assistant(v, "2026-09-03T10:00:00Z")
                 for v in self.HOSTILE_MODELS.values()],
                mtime=self.NOW)
            argv = ["model_usage_census.py", "--projects", str(projects),
                    "--out", str(out), "--weeks", "8"]
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(sys, "argv", argv), \
                 contextlib.redirect_stdout(stdout), \
                 contextlib.redirect_stderr(stderr):
                rc = model_usage_census.main()
            printed = stdout.getvalue() + stderr.getvalue()
            self.assertEqual(rc, 0, printed)
            self.assertNotIn(str(projects), printed)
            self.assertNotIn("private-client-work", printed)
            for value in self.HOSTILE_MODELS.values():
                self.assertNotIn(value, printed)
            published = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(list(published["counts"]), [model_usage_census.OTHER_KEY])

    # --- S5: one count per API turn, not per JSONL entry -----------------

    def test_census_counts_one_turn_per_message_id(self):
        """A thinking block, a text block and two tool calls arrive as four
        assistant entries sharing one `message.id`. Counting entries inflated
        the numbers the 10%/2% bars are decided on (measured 2.5x)."""
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            entries = [self._assistant("claude-opus-5", "2026-09-03T10:00:0%dZ" % i,
                                       message_extra={"id": "msg_01AAA"})
                       for i in range(4)]
            entries.append(self._assistant("claude-opus-5", "2026-09-03T11:00:00Z",
                                           message_extra={"id": "msg_01BBB"}))
            self._write_transcript(projects / "-x" / "s.jsonl", entries, mtime=self.NOW)
            counts = model_usage_census.census_counts(projects, now=self.NOW, weeks=8)
        self.assertEqual(counts, {"claude-opus-5": {"2026-W36": 2}})

    def test_census_falls_back_to_request_id_then_counts_the_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            entries = [
                {"type": "assistant", "timestamp": "2026-09-03T10:00:00Z",
                 "requestId": "req_1", "message": {"model": "claude-opus-5"}},
                {"type": "assistant", "timestamp": "2026-09-03T10:00:01Z",
                 "requestId": "req_1", "message": {"model": "claude-opus-5"}},
                # No id and no requestId: nothing to dedupe on, so it counts.
                {"type": "assistant", "timestamp": "2026-09-03T10:00:02Z",
                 "message": {"model": "claude-opus-5"}},
            ]
            self._write_transcript(projects / "-x" / "s.jsonl", entries, mtime=self.NOW)
            counts = model_usage_census.census_counts(projects, now=self.NOW, weeks=8)
        self.assertEqual(counts, {"claude-opus-5": {"2026-W36": 2}})

    def test_dedupe_is_per_transcript_not_global(self):
        """Two sessions can legitimately carry the same message id only if one
        is a resumed copy of the other; across unrelated transcripts, ids are
        distinct. Deduping globally would silently drop real turns."""
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            for name in ("a.jsonl", "b.jsonl"):
                self._write_transcript(
                    projects / "-x" / name,
                    [self._assistant("claude-opus-5", "2026-09-03T10:00:00Z",
                                     message_extra={"id": "msg_01SAME"})],
                    mtime=self.NOW)
            counts = model_usage_census.census_counts(projects, now=self.NOW, weeks=8)
        self.assertEqual(counts, {"claude-opus-5": {"2026-W36": 2}})

    # --- N6: transcripts older than the window are not parsed ------------

    def test_census_skips_transcripts_last_written_before_the_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            self._write_transcript(
                projects / "-x" / "old.jsonl",
                [self._assistant("claude-opus-5", "2026-09-03T10:00:00Z")],
                mtime=self.NOW - timedelta(days=365))
            self._write_transcript(
                projects / "-x" / "new.jsonl",
                [self._assistant("claude-sonnet-5", "2026-09-03T10:00:00Z")],
                mtime=self.NOW)
            counts = model_usage_census.census_counts(projects, now=self.NOW, weeks=8)
        self.assertEqual(counts, {"claude-sonnet-5": {"2026-W36": 1}})

    # --- N1: one week-arithmetic implementation, not two -----------------

    def test_roster_and_census_share_one_week_implementation(self):
        self.assertIs(roster.iso_week, timeweeks.iso_week)
        self.assertIs(model_usage_census.iso_week, timeweeks.iso_week)
        self.assertIs(roster.window_weeks, timeweeks.window_weeks)
        self.assertIs(model_usage_census.window_weeks, timeweeks.window_weeks)
        self.assertIs(roster.parse_ts, timeweeks.parse_ts)
    # --- S1: an empty census is not usage evidence -----------------------

    def _empty_census(self, **kwargs):
        return self._census_doc(counts={}, **kwargs)

    def test_a_fresh_but_empty_census_is_not_treated_as_usage_evidence(self):
        """Nobody ran anything, or the publisher wrote a census of nothing —
        either way there is no evidence, and every arm was reading as though
        it had been chosen on usage."""
        result = self._compute(census=self._empty_census())
        self.assertTrue(result["arms"], "the fallback still names an arm set")
        for arm in result["arms"]:
            with self.subTest(arm=arm["id"]):
                self.assertIn("census published but empty over the window",
                              arm["reason"])
        self.assertEqual(result["source"]["census_at"], "2026-09-04T06:00:00Z",
                         "the census WAS published; its provenance is recorded")

    def test_a_census_with_no_weeks_inside_the_window_is_not_evidence(self):
        outside = {"claude-sonnet-5": {"2026-W02": 500}}
        result = self._compute(census=self._census_doc(counts=outside))
        for arm in result["arms"]:
            with self.subTest(arm=arm["id"]):
                self.assertIn("census published but empty over the window",
                              arm["reason"])

    # --- S2: staleness is not evidence of retirement ---------------------

    STALE = "2026-08-14T00:00:00Z"  # 21 days before NOW, past the 14-day window

    def test_a_stale_census_holds_previous_arms_still_in_the_api(self):
        """Measured: a previous arm at 33% usage dropped because the census
        was 21 days old. A stale census says nothing about usage — including
        nothing that would justify retiring anything."""
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        result = self._compute(census=self._census_doc(generated_at=self.STALE),
                               previous=previous)
        self.assertIn("claude-opus-4-8", self._arm_ids(result))
        held = self._reason(result, "claude-opus-4-8")
        self.assertIn("no fresh census", held)
        self.assertIn("no evidence to retire it", held)
        self.assertEqual(result["retired_since_last"], [])

    def test_a_stale_census_still_retires_a_model_that_left_the_api(self):
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        result = self._compute(
            models=self._models_doc(drop=("claude-opus-4-8",)),
            census=self._census_doc(generated_at=self.STALE), previous=previous)
        self.assertNotIn("claude-opus-4-8", self._arm_ids(result))
        self.assertEqual([r["id"] for r in result["retired_since_last"]],
                         ["claude-opus-4-8"])
        self.assertIn("no longer returned by the Models API",
                      result["retired_since_last"][0]["reason"])

    def test_an_empty_census_holds_previous_arms_the_same_way(self):
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        result = self._compute(census=self._empty_census(), previous=previous)
        self.assertIn("claude-opus-4-8", self._arm_ids(result))
        self.assertIn("no evidence to retire it",
                      self._reason(result, "claude-opus-4-8"))

    # --- S16: a future census timestamp is not fresh ---------------------

    def test_a_census_generated_in_the_future_is_not_fresh(self):
        ahead = self._census_doc(generated_at="2026-10-01T00:00:00Z")
        result = self._compute(census=ahead)
        for arm in result["arms"]:
            with self.subTest(arm=arm["id"]):
                self.assertIn("in the future", arm["reason"])
        self.assertIsNone(result["source"]["census_at"])

    # --- S6: the ladder places mythos, and names what it cannot place ----

    def test_mythos_ranks_as_a_peer_of_fable(self):
        rungs = roster.tier_rungs(self._policy())
        self.assertEqual(roster.rung_of("claude-mythos-5-1", rungs),
                         roster.rung_of("claude-fable-5-1", rungs))
        self.assertIsNotNone(roster.rung_of("claude-mythos-5-1", rungs))

    def test_an_unranked_claude_model_is_named_with_its_reason(self):
        extra = [TestIssue67._model("claude-zephyr-1", "2026-01-01T00:00:00Z")]
        result = self._compute(models=self._models_doc(extra=extra))
        self.assertEqual([u["id"] for u in result["unranked"]], ["claude-zephyr-1"])
        self.assertIn("ladder", result["unranked"][0]["reason"])
        self.assertNotIn("claude-zephyr-1", self._arm_ids(result))

    def test_unranked_usage_is_excluded_from_the_share_denominator(self):
        """Measured: 60/week of sonnet computed at 5.7% — under the 10% entry
        bar — against 1000/week of usage on a model the ladder never placed."""
        counts = {"claude-sonnet-5": {w: 60 for w in self.W[:4]},
                  "claude-zephyr-1": {w: 1000 for w in self.W[:4]}}
        result = self._compute(census=self._census_doc(counts=counts))
        self.assertIn("claude-sonnet-5", self._arm_ids(result))
        self.assertIn("100.0% of census usage", self._reason(result, "claude-sonnet-5"))

    # --- S7: what was excluded from the arm set, and why -----------------

    def test_a_model_with_no_created_at_is_excluded_and_says_which(self):
        broken = TestIssue67._model("claude-fable-9", None)
        result = self._compute(models=self._models_doc(
            extra=[broken], drop=("claude-fable-5-1",)))
        entry = next(e for e in result["excluded"] if e["id"] == "claude-fable-9")
        self.assertIn("created_at", entry["reason"])
        self.assertIn("absent", entry["reason"])
        self.assertNotIn("days old", entry["reason"],
                         "'created_at absent' is not 'too new'")

    def test_a_model_inside_the_cooling_off_is_excluded_and_says_so(self):
        result = self._compute()
        entry = next(e for e in result["excluded"] if e["id"] == "claude-fable-5-1")
        self.assertIn("cooling-off", entry["reason"])
        self.assertIn("3 days old", entry["reason"])

    def test_an_unparseable_created_at_reads_as_absent_not_as_new(self):
        broken = TestIssue67._model("claude-fable-9", "last Tuesday")
        result = self._compute(models=self._models_doc(
            extra=[broken], drop=("claude-fable-5-1",)))
        entry = next(e for e in result["excluded"] if e["id"] == "claude-fable-9")
        self.assertIn("unparseable", entry["reason"])

    def test_an_empty_arm_set_is_fatal_and_publishes_nothing(self):
        """An all-inside-cooling-off tier used to yield `arms: []` and exit 0
        — a roster with no arms is not a roster, it is a silent no-op run."""
        fresh_only = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            TestIssue67._model("claude-haiku-9", "2026-09-02T00:00:00Z")]}
        with tempfile.TemporaryDirectory() as tmp:
            models = Path(tmp) / "models.json"
            models.write_text(json.dumps(fresh_only), encoding="utf-8")
            out = Path(tmp) / "roster" / "latest.json"
            argv = ["roster.py", "--models", str(models), "--policy",
                    str(self.POLICY), "--out", str(out)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(sys, "argv", argv), \
                 contextlib.redirect_stdout(stdout), \
                 contextlib.redirect_stderr(stderr):
                rc = roster.main()
            self.assertNotEqual(rc, 0)
            self.assertFalse(out.exists(), "nothing is written when there are no arms")
            self.assertIn("no arms", (stdout.getvalue() + stderr.getvalue()).lower())

    # --- S8: an alias and its dated snapshot are one model ---------------

    SNAPSHOT = "claude-sonnet-5-20260201"

    def _with_snapshot(self):
        return self._models_doc(
            extra=[TestIssue67._model(self.SNAPSHOT, "2026-02-01T00:00:00Z")])

    def test_a_dated_snapshot_takes_no_second_arm_seat(self):
        result = self._compute(models=self._with_snapshot())
        self.assertIn("claude-sonnet-5", self._arm_ids(result))
        self.assertNotIn(self.SNAPSHOT, self._arm_ids(result))
        entry = next(e for e in result["excluded"] if e["id"] == self.SNAPSHOT)
        self.assertIn("claude-sonnet-5", entry["reason"])
        self.assertIn("snapshot", entry["reason"])

    def test_a_dated_id_whose_alias_is_absent_stands_on_its_own(self):
        """Only collapse onto an alias that actually exists — otherwise a
        catalogue that publishes ONLY dated ids would have no arms at all."""
        models = self._models_doc(drop=("claude-sonnet-5",),
                                  extra=[TestIssue67._model(self.SNAPSHOT,
                                                            "2026-02-01T00:00:00Z")])
        result = self._compute(models=models)
        self.assertIn(self.SNAPSHOT, self._arm_ids(result))

    def test_snapshot_usage_counts_towards_its_alias(self):
        counts = {self.SNAPSHOT: {w: 100 for w in self.W[:4]},
                  "claude-haiku-4-5": {w: 100 for w in self.W[:4]}}
        result = self._compute(models=self._with_snapshot(),
                               census=self._census_doc(counts=counts))
        self.assertIn("50.0% of census usage", self._reason(result, "claude-sonnet-5"))

    def test_version_components_sort_numerically_not_lexicographically(self):
        """`claude-x-4-10` supersedes `claude-x-4-9`; a string sort says the
        opposite, and the tie-break decides which model is 'newest in tier'."""
        same_day = "2026-03-01T00:00:00Z"
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            TestIssue67._model("claude-sonnet-4-9", same_day),
            TestIssue67._model("claude-sonnet-4-10", same_day)]}
        rungs = roster.tier_rungs(self._policy())
        ordered = sorted(models["models"], key=lambda m: roster._rank(m, rungs))
        self.assertEqual([m["id"] for m in ordered],
                         ["claude-sonnet-4-9", "claude-sonnet-4-10"])

    # --- S10: the judge says, in a field, whether it is also an arm ------

    def test_judge_carries_a_machine_readable_is_arm_flag(self):
        result = self._compute()
        self.assertIs(result["judge"]["is_arm"], False)
        self.assertNotIn(result["judge"]["id"], self._arm_ids(result))

    def test_judge_is_arm_is_true_when_every_model_is_an_arm(self):
        one_per_tier = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            TestIssue67._model("claude-haiku-4-5", "2025-10-01T00:00:00Z"),
            TestIssue67._model("claude-sonnet-5", "2026-02-01T00:00:00Z")]}
        result = self._compute(models=one_per_tier, census=None)
        self.assertIs(result["judge"]["is_arm"], True)
        self.assertIn(result["judge"]["id"], self._arm_ids(result))

    # --- S12: the three documents come off a public branch ---------------

    def _warned(self, **kwargs):
        """compute_roster with the warnings collected instead of printed."""
        notes: list[str] = []
        kwargs.setdefault("models_doc", self._models_doc())
        kwargs.setdefault("census_doc", self._census_doc())
        kwargs.setdefault("policy", self._policy())
        kwargs.setdefault("previous", None)
        kwargs.setdefault("now", self.NOW)
        result = roster.compute_roster(warn=notes.append, **kwargs)
        return result, notes

    def test_a_model_entry_without_a_string_id_is_skipped_and_named(self):
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            {"display_name": "no id at all", "created_at": "2026-01-01T00:00:00Z"},
            {"id": 5, "created_at": "2026-01-01T00:00:00Z"},
            TestIssue67._model("claude-sonnet-5", "2026-02-01T00:00:00Z"),
            TestIssue67._model("claude-opus-5", "2026-04-01T00:00:00Z"),
            "not even a dict",
        ]}
        result, notes = self._warned(models_doc=models)
        self.assertEqual(self._arm_ids(result), ["claude-sonnet-5", "claude-opus-5"])
        self.assertTrue(notes)
        for note in notes:
            with self.subTest(note=note):
                self.assertNotIn("\n", note, "one line, never a traceback")
                self.assertIn("models", note)

    def test_census_counts_that_are_not_numbers_are_coerced_or_dropped(self):
        counts = {"claude-sonnet-5": {w: "100" for w in self.W[:4]},
                  "claude-opus-5": {w: None for w in self.W[:4]},
                  "claude-haiku-4-5": "not a mapping at all"}
        result, notes = self._warned(census_doc=self._census_doc(counts=counts))
        # "100" coerces; None does not, and neither crashes the run.
        self.assertIn("claude-sonnet-5", self._arm_ids(result))
        self.assertIn("100.0% of census usage", self._reason(result, "claude-sonnet-5"))
        self.assertTrue(any("census" in n for n in notes), notes)
        for note in notes:
            self.assertNotIn("\n", note)

    def test_previous_arms_that_are_not_dicts_with_an_id_are_ignored(self):
        previous = {"arms": ["claude-opus-4-8", {"reason": "no id"}, 7,
                             {"id": "claude-opus-4-8"}]}
        result, notes = self._warned(previous=previous)
        self.assertTrue(any("previous" in n for n in notes), notes)
        # The one well-formed entry is still honoured.
        self.assertEqual([r["id"] for r in result["retired_since_last"]],
                         ["claude-opus-4-8"])

    def test_a_wrong_shaped_previous_document_does_not_raise(self):
        for previous in ({"arms": "claude-opus-5"}, {"arms": None}, {}):
            with self.subTest(previous=previous):
                result, _ = self._warned(previous=previous)
                self.assertEqual(result["retired_since_last"], [])

    # --- N5: an unranked previous arm is not "gone from the API" ---------

    def test_an_unranked_previous_arm_is_retired_for_the_right_reason(self):
        extra = [TestIssue67._model("claude-zephyr-1", "2026-01-01T00:00:00Z")]
        previous = {"arms": [{"id": "claude-zephyr-1", "reason": "was an arm"}]}
        result = self._compute(models=self._models_doc(extra=extra),
                               previous=previous)
        why = next(r["reason"] for r in result["retired_since_last"]
                   if r["id"] == "claude-zephyr-1")
        self.assertNotIn("no longer returned by the Models API", why)
        self.assertIn("ladder", why)

    # --- S9: the summary never claims "no change" it cannot know ---------

    def test_summary_says_there_was_no_previous_roster_on_a_first_run(self):
        text = roster.render_summary(self._compute(previous=None))
        self.assertIn("no previous roster to compare against", text)
        self.assertNotIn("No change to the arm set", text)

    def test_summary_says_no_change_only_when_it_compared_something(self):
        previous = {"arms": [{"id": i} for i in self._arm_ids(self._compute())]}
        text = roster.render_summary(self._compute(previous=previous))
        self.assertIn("No change to the arm set", text)

    def test_summary_says_inputs_unavailable_when_the_previous_was_unreadable(self):
        text = roster.render_summary(self._compute(previous=None),
                                     previous_state="unavailable")
        self.assertIn("roster inputs unavailable", text.lower())
        self.assertNotIn("No change to the arm set", text)

    def test_main_reports_unavailable_when_the_previous_roster_is_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            models = Path(tmp) / "models.json"
            models.write_text(json.dumps(self._models_doc()), encoding="utf-8")
            previous = Path(tmp) / "previous.json"
            previous.write_text("{ this is not json", encoding="utf-8")
            out = Path(tmp) / "roster" / "latest.json"
            argv = ["roster.py", "--models", str(models), "--policy",
                    str(self.POLICY), "--previous", str(previous), "--out", str(out)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(sys, "argv", argv), \
                 contextlib.redirect_stdout(stdout), \
                 contextlib.redirect_stderr(stderr):
                rc = roster.main()
            printed = stdout.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("roster inputs unavailable", printed.lower())
    # --- S13: a half-read catalogue is refused, loudly and without a body ---

    def test_a_models_api_that_never_stops_paging_is_refused(self):
        """The file says it refuses a half-read API because a partial read is
        indistinguishable from a retirement. It then read 20 pages and wrote
        whatever it had."""
        pages = iter(range(10_000))

        def endless(url, headers):
            n = next(pages)
            return {"data": [{"id": f"claude-sonnet-{n}", "created_at":
                              "2026-01-01T00:00:00Z"}],
                    "has_more": True, "last_id": f"claude-sonnet-{n}"}

        with self.assertRaises(RuntimeError) as caught:
            refresh_models.build_models_document(endless, now=self.NOW)
        self.assertIn("truncated", str(caught.exception).lower())

    def test_a_catalogue_that_ends_within_the_bound_is_written(self):
        pages = [
            {"data": [{"id": "claude-sonnet-5", "created_at": "2026-02-01T00:00:00Z"}],
             "has_more": True, "last_id": "claude-sonnet-5"},
            {"data": [{"id": "claude-opus-5", "created_at": "2026-04-01T00:00:00Z"}],
             "has_more": False},
        ]
        served = iter(pages)
        doc = refresh_models.build_models_document(
            lambda url, headers: next(served), now=self.NOW)
        self.assertEqual([m["id"] for m in doc["models"]],
                         ["claude-opus-5", "claude-sonnet-5"])

    def _refresh_main(self, exc):
        """main() with the network call replaced by a raise. (rc, printed)."""
        def boom(url, headers, timeout=30):
            raise exc

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "models.json"
            argv = ["refresh_models.py", "--out", str(out)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(refresh_models, "http_json", boom), \
                 mock.patch.object(refresh_models, "_auth_headers", lambda: {}), \
                 mock.patch.object(sys, "argv", argv), \
                 contextlib.redirect_stdout(stdout), \
                 contextlib.redirect_stderr(stderr):
                rc = refresh_models.main()
            wrote = out.exists()
        return rc, stdout.getvalue() + stderr.getvalue(), wrote

    def test_a_timeout_is_caught_and_named_by_its_class(self):
        """TimeoutError is an OSError, not a URLError — it used to escape the
        except clause entirely and exit through a traceback."""
        rc, printed, wrote = self._refresh_main(TimeoutError("timed out"))
        self.assertEqual(rc, 1)
        self.assertIn("TimeoutError", printed)
        self.assertFalse(wrote)

    def test_a_decoding_error_is_caught_and_named_by_its_class(self):
        exc = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        rc, printed, _ = self._refresh_main(exc)
        self.assertEqual(rc, 1)
        self.assertIn("UnicodeDecodeError", printed)
        self.assertNotIn("invalid start byte", printed)

    def test_an_http_error_reports_the_status_code_and_no_response_body(self):
        body = "the account example-org is over its quota"
        exc = urllib.error.HTTPError(
            "https://example.com/v1/models", 429, "Too Many Requests", {},
            io.BytesIO(body.encode()))
        rc, printed, _ = self._refresh_main(exc)
        self.assertEqual(rc, 1)
        self.assertIn("429", printed)
        self.assertNotIn(body, printed)
        self.assertNotIn("example-org", printed)

    def test_a_missing_credential_still_says_which_variable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "models.json"
            argv = ["refresh_models.py", "--out", str(out)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
                os.environ.pop("ANTHROPIC_API_KEY", None)
                with mock.patch.object(sys, "argv", argv), \
                     contextlib.redirect_stdout(stdout), \
                     contextlib.redirect_stderr(stderr):
                    rc = refresh_models.main()
            printed = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(rc, 1)
        self.assertIn("ANTHROPIC_AUTH_TOKEN", printed)
    # --- S11 / S10: the runner fails closed on an unusable roster --------

    def _fixture_dir(self, tmp, pinned, pin_judge=None):
        eval_dir = Path(tmp) / "evals" / "a-skill"
        (eval_dir / "seed").mkdir(parents=True)
        (eval_dir / "seed" / "README.md").write_text("seed\n", encoding="utf-8")
        fixture = {"skill": "a-skill", "prompt": "do the thing",
                   "judge_rubric": "grade it",
                   "arms": {"without_skill": {"install": "none"}}}
        if pinned:
            fixture["model"] = "claude-sonnet-4-6"
        if pinned or pin_judge:
            fixture["judge"] = {"model": pin_judge or "claude-opus-4-6"}
        (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture), encoding="utf-8")
        return eval_dir

    def _roster_file(self, tmp, document=None, name="latest.json"):
        path = Path(tmp) / "roster" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(document, str):
            path.write_text(document, encoding="utf-8")
        else:
            path.write_text(json.dumps(document if document is not None
                                       else self._compute()), encoding="utf-8")
        return path

    def _run_one_arm(self, eval_dir, roster_path):
        """One arm with the agent and judge stubbed. Returns the arm summary."""
        seen = {}

        def fake_run_agent(workspace, prompt, arm):
            seen["agent"] = arm.get("model")
            return {"transcript": "done", "usage": {}, "cost_usd": 0.0,
                    "num_turns": 1, "duration_ms": 1, "raw": {}}

        def fake_score(rubric, transcript, diff, model=None, **kwargs):
            seen["judge"] = model
            return {"dimensions": [], "overall": 1.0}

        args = argparse.Namespace(
            model=None, timeout=30, no_judge=False,
            results_dir=Path(tempfile.mkdtemp()), roster=roster_path)
        self.addCleanup(shutil.rmtree, args.results_dir, ignore_errors=True)
        fixture = run_eval.load_fixture(eval_dir)
        with mock.patch.object(run_eval, "run_agent", fake_run_agent), \
             mock.patch.object(run_eval.judge, "score", fake_score):
            summary = run_eval._run_arm("without_skill", fixture, eval_dir / "seed",
                                        Path("/nonexistent-registry"), args,
                                        "20260904T120000Z")
        return summary, seen

    def test_an_unpinned_fixture_with_no_roster_is_a_runner_level_error(self):
        """Silently falling back to the CLI's default model published a badge
        for a model nobody chose, and made every week-over-week comparison a
        comparison against a different model."""
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=False)
            missing = Path(tmp) / "roster" / "nope.json"
            summary, seen = self._run_one_arm(eval_dir, missing)
        self.assertIsNotNone(summary["error"], "no pin and no roster must not run")
        self.assertIn(str(missing), summary["error"]["detail"],
                      "the error names the roster path it looked for")
        self.assertNotIn("agent", seen, "the agent is never invoked")

    def test_a_pinned_fixture_runs_with_no_roster_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=True)
            summary, seen = self._run_one_arm(eval_dir, Path(tmp) / "nope.json")
        self.assertIsNone(summary["error"])
        self.assertEqual(seen["agent"], "claude-sonnet-4-6")
        self.assertEqual(seen["judge"], "claude-opus-4-6")

    WRONG_SHAPES = {
        "top level list": '[{"id": "claude-opus-5"}]',
        "arms as strings": '{"arms": ["claude-opus-5"], "judge": {"id": "claude-fable-5-1"}}',
        "judge as a string": '{"arms": [{"id": "claude-opus-5"}], "judge": "claude-fable-5-1"}',
        "arms not a list": '{"arms": "claude-opus-5", "judge": {"id": "claude-fable-5-1"}}',
        "empty arms": '{"arms": [], "judge": {"id": "claude-fable-5-1"}}',
        "truncated": '{"arms": [{"id": "claude-opus-5"}',
        "empty file": "",
    }

    def test_a_wrong_shaped_roster_is_a_named_error_not_an_attributeerror(self):
        for label, raw in self.WRONG_SHAPES.items():
            with self.subTest(shape=label), tempfile.TemporaryDirectory() as tmp:
                eval_dir = self._fixture_dir(tmp, pinned=False)
                path = self._roster_file(tmp, raw)
                summary, seen = self._run_one_arm(eval_dir, path)
                self.assertIsNotNone(summary["error"])
                self.assertIn(str(path), summary["error"]["detail"])
                self.assertNotIn("agent", seen)

    def test_the_runner_refuses_a_roster_judge_that_is_also_an_arm(self):
        """The roster says so in a field precisely so the runner can refuse:
        a model grading its own run is not a judgement."""
        document = {"arms": [{"id": "claude-opus-5", "reason": "x"}],
                    "judge": {"id": "claude-opus-5", "reason": "y", "is_arm": True}}
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=False)
            summary, seen = self._run_one_arm(eval_dir, self._roster_file(tmp, document))
        self.assertIsNotNone(summary["error"])
        self.assertIn("judge", summary["error"]["detail"].lower())
        self.assertNotIn("agent", seen)

    def test_a_fixture_that_pins_its_judge_may_still_use_a_judge_is_arm_roster(self):
        document = {"arms": [{"id": "claude-opus-5", "reason": "x"}],
                    "judge": {"id": "claude-opus-5", "reason": "y", "is_arm": True}}
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=False, pin_judge="claude-fable-5-1")
            summary, seen = self._run_one_arm(eval_dir, self._roster_file(tmp, document))
        self.assertIsNone(summary["error"])
        self.assertEqual(seen["agent"], "claude-opus-5")
        self.assertEqual(seen["judge"], "claude-fable-5-1")

    def test_a_judge_that_merely_appears_in_arms_is_refused_too(self):
        """`is_arm` absent (an older roster) is not permission — membership in
        `arms` is the fact, and the flag is the shortcut."""
        document = {"arms": [{"id": "claude-opus-5", "reason": "x"}],
                    "judge": {"id": "claude-opus-5", "reason": "y"}}
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=False)
            summary, _ = self._run_one_arm(eval_dir, self._roster_file(tmp, document))
        self.assertIsNotNone(summary["error"])

    # --- N3: the roster is read once a run, not once an arm --------------

    def test_the_roster_is_read_once_per_run_not_once_per_arm(self):
        reads = []
        real = run_eval.read_roster

        def counting(path):
            reads.append(path)
            return real(path)

        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = self._fixture_dir(tmp, pinned=False)
            path = self._roster_file(tmp)
            results = Path(tmp) / "results"
            argv = ["run_eval.py", str(eval_dir), "--arm", "both",
                    "--roster", str(path), "--results-dir", str(results)]

            def fake_run_agent(workspace, prompt, arm):
                return {"transcript": "done", "usage": {}, "cost_usd": 0.0,
                        "num_turns": 1, "duration_ms": 1, "raw": {}}

            with mock.patch.object(run_eval, "read_roster", counting), \
                 mock.patch.object(run_eval, "run_agent", fake_run_agent), \
                 mock.patch.object(run_eval.judge, "score",
                                   lambda *a, **k: {"dimensions": [], "overall": 1.0}), \
                 mock.patch.object(sys, "argv", argv), \
                 contextlib.redirect_stdout(io.StringIO()):
                rc = run_eval.main()
        self.assertEqual(rc, 0)
        self.assertEqual(len(reads), 1, f"read {len(reads)} times for 2 arms")
    # --- S3 / S4 / S9 / S15: the roster step in eval.yml ------------------

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"

    def _steps(self):
        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        return doc["jobs"]["eval"]["steps"]

    def _step_named(self, needle):
        return next(s for s in self._steps()
                    if needle.lower() in (s.get("name") or "").lower())

    def test_the_roster_is_refreshed_before_the_preflight_that_consumes_it(self):
        names = [s.get("name", "") for s in self._steps()]
        roster_at = next(i for i, n in enumerate(names) if "roster" in n.lower())
        preflight_at = next(i for i, n in enumerate(names) if "preflight" in n.lower())
        self.assertLess(roster_at, preflight_at,
                        "the preflight takes its model from the roster, so the "
                        "roster has to exist first")

    def test_the_preflight_takes_its_model_from_the_roster(self):
        script = self._step_named("preflight")["run"]
        self.assertIn("roster/latest.json", script,
                      "`preflight` was computed and consumed by nothing")
        self.assertIn('"preflight"', script, "it reads the preflight entry")
        self.assertIn('--model "$model"', script,
                      "the model is a variable the roster fills in, not a literal")
        # Exactly one model id in the whole file, and it carries the marker.
        raw = self.WORKFLOW.read_text(encoding="utf-8")
        pattern = TestIssue67._model_id_pattern(TestIssue67())
        literals = [ln for ln in raw.splitlines() if pattern.search(ln)]
        self.assertEqual(len(literals), 1, literals)
        self.assertIn("ROSTER FALLBACK", literals[0])

    # --- the roster step, actually executed -------------------------------

    def _run_roster_step(self, *, refresh_rc=0, git_shim=None):
        """Run eval.yml's roster step for real, against stubs.

        Hermetic: the two python scripts it calls are replaced by stubs, `git`
        by an optional shim, and there is no network and no credential. What is
        under test is the STEP — its failure handling — not the scripts.
        """
        script = self._step_named("roster")["run"]
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "scripts").mkdir()
        (tmp / "harness").mkdir()
        (tmp / "evals").mkdir()
        (tmp / "evals" / "roster-policy.yml").write_text("tiers: []\n", encoding="utf-8")
        stub_args = ("import sys, json, argparse\n"
                     "p = argparse.ArgumentParser()\n"
                     "for f in ('--models','--policy','--census',"
                     "'--admin-report','--previous','--out'):\n"
                     "    p.add_argument(f)\n"
                     "a = p.parse_args()\n")
        (tmp / "scripts" / "refresh_models.py").write_text(
            stub_args + (
                "print('Models API read failed: HTTP 503', file=sys.stderr)\n"
                "sys.exit(1)\n" if refresh_rc else
                "open(a.out, 'w').write(json.dumps({'models': []}))\n"
                "open(a.admin_report, 'w').write('{}')\n"),
            encoding="utf-8")
        (tmp / "harness" / "roster.py").write_text(
            stub_args + "open(a.out, 'w').write('{}')\n"
                        "print('### Model roster')\n",
            encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        # A real (empty) bare "origin" — actions/checkout always configures
        # one in production, and item 2's fix makes the step's behavior
        # depend on whether `origin` is genuinely reachable vs. genuinely
        # missing the branch. An unconfigured origin used to read the same
        # as "reachable, branch absent" purely by accident of both failing
        # the same commands; that coincidence is gone now that ls-remote's
        # own exit status is checked, so the fixture needs a real remote to
        # stay a genuine first-run case without a git_shim.
        bare_origin = tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare_origin)], check=True)
        subprocess.run(["git", "remote", "add", "origin", str(bare_origin)],
                       cwd=tmp, check=True)

        runner = tmp / "runner"
        runner.mkdir()
        (runner / "anthropic-bearer").write_text("not-a-real-token", encoding="utf-8")
        env = dict(os.environ)
        env.update({"RUNNER_TEMP": str(runner),
                    "GITHUB_ENV": str(tmp / "github_env"),
                    "GITHUB_STEP_SUMMARY": str(tmp / "summary.md")})
        (tmp / "github_env").write_text("", encoding="utf-8")
        (tmp / "summary.md").write_text("", encoding="utf-8")
        if git_shim:
            bindir = tmp / "bin"
            bindir.mkdir()
            shim = bindir / "git"
            shim.write_text(git_shim.replace("{GIT}", shutil.which("git")),
                            encoding="utf-8")
            shim.chmod(0o755)
            env["PATH"] = f"{bindir}:{env['PATH']}"
        # Actions runs a `run:` block as `bash -e {file}`, not `bash -c`
        # (its default shell is `bash --noprofile --norc -eo pipefail {0}`)
        # — a command that fails outside an if/&&/||/! context aborts the
        # whole step there. `bash -c` without `-e` let a step that would
        # actually die partway through read as fully successful here.
        script_file = tmp / "roster_step.sh"
        script_file.write_text(script, encoding="utf-8")
        proc = subprocess.run(["bash", "-e", str(script_file)], cwd=tmp, env=env,
                              capture_output=True, text=True, timeout=120)
        return {
            "rc": proc.returncode,
            "out": proc.stdout + proc.stderr,
            "roster": runner / "roster" / "latest.json",
            "env": (tmp / "github_env").read_text(encoding="utf-8"),
            "summary": (tmp / "summary.md").read_text(encoding="utf-8"),
        }

    def test_the_roster_step_publishes_a_roster_on_the_happy_path(self):
        got = self._run_roster_step()
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertTrue(got["roster"].is_file(), got["out"])
        self.assertIn("EVAL_ROSTER=", got["env"])
        self.assertIn("Model roster", got["summary"])

    def test_a_models_api_failure_does_not_fail_the_eval(self):
        """S4: the roster step sits ahead of the eval and the badge, neither of
        which ever depended on it. A Models API blip must not kill both."""
        got = self._run_roster_step(refresh_rc=1)
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertIn("::warning::", got["out"])
        self.assertFalse(got["roster"].exists(),
                         "no roster is published — never a partial one")
        self.assertNotIn("EVAL_ROSTER=", got["env"])
        self.assertIn("not refreshed", got["summary"].lower())

    #: `fetch` fails, `ls-remote` says the branch is there — a transient
    #: network failure, not a first run. Anything else goes to the real git.
    GIT_SHIM_FETCH_FAILS = '''#!/usr/bin/env bash
for a in "$@"; do
  case "$a" in
    fetch) echo "fatal: unable to access origin" >&2; exit 128 ;;
    ls-remote) printf 'deadbeef\\trefs/heads/eval-results\\n'; exit 0 ;;
  esac
done
exec {GIT} "$@"
'''

    #: `fetch` fails and the branch does not exist either — a genuine first run.
    GIT_SHIM_FIRST_RUN = '''#!/usr/bin/env bash
for a in "$@"; do
  case "$a" in
    fetch) exit 128 ;;
    ls-remote) exit 0 ;;
  esac
done
exec {GIT} "$@"
'''

    def test_a_failed_fetch_is_not_read_as_a_first_run(self):
        """S9: `git fetch || true` conflated a transient failure with a first
        run, and the roster then asserted 'no fresh census (none published)'."""
        got = self._run_roster_step(git_shim=self.GIT_SHIM_FETCH_FAILS)
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertIn("::warning::", got["out"])
        self.assertFalse(got["roster"].exists())
        self.assertNotIn("EVAL_ROSTER=", got["env"])

    def test_a_genuine_first_run_still_computes_a_roster(self):
        got = self._run_roster_step(git_shim=self.GIT_SHIM_FIRST_RUN)
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertTrue(got["roster"].is_file(), got["out"])

    def test_the_admin_usage_report_is_written_outside_the_published_directory(self):
        """S15: it went into the very directory the commit step copies from."""
        script = self._step_named("roster")["run"]
        self.assertNotIn('roster/admin-usage.json', script)
        self.assertIn('"$RUNNER_TEMP/admin-usage.json"', script)
        got = self._run_roster_step()
        published = got["roster"].parent
        self.assertEqual(sorted(p.name for p in published.iterdir()),
                         ["latest.json"],
                         "only the roster itself lives in the copied directory")

    # --- S14: the security header's rules, checked where they live -------

    def test_every_uses_line_is_bare_in_the_RAW_file(self):
        """The parsed-YAML check cannot see this: yaml.safe_load strips the
        comment, so `uses: owner/repo@<sha> # v4` passed it (mutation-proven).
        A trailing version comment is a LEXICAL property of the file, and a
        regex over the raw text is the right tool for a lexical property."""
        bare = re.compile(r"^\s*(?:-\s+)?uses:\s*\S+@[0-9a-f]{40}\s*$")
        raw = self.WORKFLOW.read_text(encoding="utf-8")
        lines = [ln for ln in raw.splitlines() if re.match(r"^\s*(?:-\s+)?uses:", ln)]
        self.assertTrue(lines, "no `uses:` lines found — the check is inert")
        for line in lines:
            with self.subTest(line=line.strip()):
                self.assertRegex(line, bare,
                                 "every `uses:` is a bare 40-hex SHA with no "
                                 "trailing version/date comment")

    def test_every_checkout_disables_persist_credentials(self):
        checkouts = [s for s in self._steps()
                     if (s.get("uses") or "").startswith("actions/checkout@")]
        self.assertTrue(checkouts)
        for step in checkouts:
            with self.subTest(step=step.get("name")):
                self.assertIs((step.get("with") or {}).get("persist-credentials"),
                              False)

    def test_the_concurrency_group_is_still_there(self):
        """Nothing in this round adds or changes it — that is the assertion.
        The badge commit races itself without it."""
        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        self.assertEqual(doc["concurrency"],
                         {"group": "real-eval", "cancel-in-progress": False})

    def test_no_run_block_interpolates_an_actions_expression(self):
        for step in self._steps():
            with self.subTest(step=step.get("name")):
                self.assertNotIn("${{", step.get("run") or "")


class TestIssue67Review2(unittest.TestCase):
    """Review-round-2 fixes on top of #67's roster feature (PR #129, round 2).

    A SIBLING of TestIssue67 and TestIssue67Review — same reasons: reuse the
    canned documents, run its own tests once. Same hermetic rules apply.
    """

    NOW = TestIssue67.NOW
    W = TestIssue67.W
    POLICY = TestIssue67.POLICY

    @classmethod
    def _models_doc(cls, extra=None, drop=()):
        return TestIssue67._models_doc(extra=extra, drop=drop)

    @classmethod
    def _census_doc(cls, counts=None, generated_at="2026-09-04T06:00:00Z"):
        return TestIssue67._census_doc(counts=counts, generated_at=generated_at)

    @classmethod
    def _policy(cls):
        return TestIssue67._policy()

    @classmethod
    def _compute(cls, models=TestIssue67.DEFAULT, census=TestIssue67.DEFAULT,
                 previous=None):
        return TestIssue67._compute(models=models, census=census, previous=previous)

    _arm_ids = staticmethod(TestIssue67._arm_ids)
    _reason = staticmethod(TestIssue67._reason)

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"

    def _steps(self):
        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        return doc["jobs"]["eval"]["steps"]

    def _step_named(self, needle):
        return next(s for s in self._steps()
                    if needle.lower() in (s.get("name") or "").lower())

    #: The roster step, actually executed against stubs — same harness as
    #: TestIssue67Review, reused rather than duplicated.
    _run_roster_step = TestIssue67Review._run_roster_step

    # --- item 1: usage_share's denominator excludes `other`/unranked, and
    #             _census_verdict must agree, not read RAW counts -----------

    def test_census_entirely_unrankable_is_held_not_read_as_usable(self):
        """A census whose in-window usage is entirely `other` (e.g. every
        turn routed through Bedrock/Vertex/a proxy) has raw usage but a ZERO
        ranked denominator. `usage_share` already excludes `other` from that
        denominator; `_census_verdict` used to check raw counts instead, so
        it called this census usable and let previous arms fall under the
        exit bar at 0.0% — retiring them on no measurable evidence, exactly
        the failure the stale-census hold-over path exists to prevent."""
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        counts = {model_usage_census.OTHER_KEY:
                  {w: 500 for w in self.W[:4]}}
        result = self._compute(census=self._census_doc(counts=counts),
                               previous=previous)
        self.assertIn("claude-opus-4-8", self._arm_ids(result),
                      "an unrankable-only census is not evidence to retire "
                      "a previous arm")
        reason = self._reason(result, "claude-opus-4-8")
        self.assertIn("no evidence to retire it", reason)
        self.assertIn("no usage this policy can rank", reason)
        self.assertEqual(result["retired_since_last"], [])

    def test_census_verdict_distinguishes_unranked_only_from_truly_empty(self):
        """The existing 'empty over the window' message is for a census that
        recorded NOTHING; a census that recorded usage none of which the
        ladder can rank is a different fact and gets its own words."""
        raw_total, ranked_total = roster._in_window_totals(
            {model_usage_census.OTHER_KEY: {self.W[0]: 500}},
            set(self.W[:4]), roster.tier_rungs(self._policy()))
        self.assertEqual(raw_total, 500)
        self.assertEqual(ranked_total, 0)
        _, note, code = roster._census_verdict(
            self._census_doc(counts={model_usage_census.OTHER_KEY:
                                     {self.W[0]: 500}}),
            raw_total, ranked_total, self._policy(), self.NOW)
        self.assertEqual(code, "unranked")
        self.assertIn("no usage this policy can rank", note)

        empty_raw, empty_ranked = roster._in_window_totals(
            {}, set(self.W[:4]), roster.tier_rungs(self._policy()))
        _, empty_note, empty_code = roster._census_verdict(
            self._census_doc(counts={}), empty_raw, empty_ranked,
            self._policy(), self.NOW)
        self.assertEqual(empty_code, "empty")
        self.assertIn("empty over the window", empty_note)

    # --- item 2: `git ls-remote | grep -q` discards ls-remote's own exit
    #             status under `pipefail` -----------------------------------

    #: Both `fetch` AND `ls-remote` fail — a correlated outage (DNS, proxy,
    #: GitHub down), not a first run. `grep -q` on ls-remote's empty stdout
    #: exits 1 (no match); under `pipefail` that becomes the PIPELINE's exit
    #: status, discarding ls-remote's own 128 — so `if ... | grep -q ...`
    #: reads false and the step falls through as though the branch never
    #: existed.
    GIT_SHIM_BOTH_FAIL = '''#!/usr/bin/env bash
for a in "$@"; do
  case "$a" in
    fetch) echo "fatal: unable to access origin" >&2; exit 128 ;;
    ls-remote) echo "fatal: unable to access origin" >&2; exit 128 ;;
  esac
done
exec {GIT} "$@"
'''

    def test_a_correlated_outage_is_not_read_as_a_first_run(self):
        got = self._run_roster_step(git_shim=self.GIT_SHIM_BOTH_FAIL)
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertIn("::warning::", got["out"])
        self.assertFalse(got["roster"].exists(),
                         "no roster is published on a correlated outage")
        self.assertNotIn("EVAL_ROSTER=", got["env"])

    # --- item 3: `has_more: true` must never exit the paging loop via a
    #             plain `break` — every such exit is a truncated catalogue --

    def test_a_stuck_cursor_is_refused_not_silently_truncated(self):
        """`has_more: true` with the SAME `last_id` every page — exactly what
        MAX_PAGES exists to catch. The `next_after == after` break used to
        fire after the SECOND identical page, exiting with rc 0 long before
        MAX_PAGES and defeating the bound entirely."""
        page = {"data": [{"id": "claude-sonnet-5",
                          "created_at": "2026-01-01T00:00:00Z"}],
                "has_more": True, "last_id": "claude-sonnet-5"}
        with self.assertRaises(RuntimeError) as caught:
            refresh_models.build_models_document(lambda url, headers: page,
                                                  now=self.NOW)
        self.assertIn("truncated", str(caught.exception).lower())

    def test_has_more_with_no_usable_cursor_is_refused(self):
        """`has_more: true`, no `last_id`, and no entry in `data` carries an
        `id` either — there is nothing to page from, but the old code read
        that as "done" rather than "cannot continue"."""
        page = {"data": [{"created_at": "2026-01-01T00:00:00Z"}],
                "has_more": True}
        with self.assertRaises(RuntimeError) as caught:
            refresh_models.build_models_document(lambda url, headers: page,
                                                  now=self.NOW)
        self.assertIn("truncated", str(caught.exception).lower())

    def test_an_empty_page_that_still_claims_more_is_refused(self):
        """A real page, then `{"data": [], "has_more": true}` — the API says
        there is more, but the empty page carries no cursor to reach it.
        `not entries` used to break the loop silently regardless of
        `has_more`, publishing everything read so far as the whole
        catalogue."""
        pages = iter([
            {"data": [{"id": "claude-sonnet-5",
                      "created_at": "2026-01-01T00:00:00Z"}],
             "has_more": True, "last_id": "claude-sonnet-5"},
            {"data": [], "has_more": True},
        ])
        with self.assertRaises(RuntimeError) as caught:
            refresh_models.build_models_document(
                lambda url, headers: next(pages), now=self.NOW)
        self.assertIn("truncated", str(caught.exception).lower())

    # --- item 4a: the preflight pick applies the cooling-off, not just
    #              "newest in the lowest rung" ----------------------------

    def test_preflight_prefers_a_model_past_cooling_off_over_a_newer_one_inside_it(self):
        """A day-old cheapest-tier model is exactly the kind an old or
        narrowly-scoped bearer may not yet be entitled to invoke — and the
        preflight step this feeds is FATAL to the whole job. When an older,
        already-cooled-off model exists in the same (cheapest) tier, that is
        the one to canary with, not the newest arrival."""
        yesterday = (self.NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        models = self._models_doc(extra=[TestIssue67._model("claude-haiku-5", yesterday)])
        result = self._compute(models=models)
        self.assertEqual(result["preflight"]["id"], "claude-haiku-4-5")
        self.assertIn("cooling-off", result["preflight"]["reason"])

    def test_preflight_falls_back_to_newest_when_nothing_in_tier_has_cooled_off(self):
        """The tier's only model is brand new — there is nothing older to
        prefer, so the newest (still within cooling-off) is the only pick,
        and the reason says so rather than silently pretending otherwise."""
        yesterday = (self.NOW - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            TestIssue67._model("claude-haiku-9", yesterday),
            TestIssue67._model("claude-opus-5", "2026-04-01T00:00:00Z")]}
        result = self._compute(models=models, census=None)
        self.assertEqual(result["preflight"]["id"], "claude-haiku-9")
        self.assertIn("within the", result["preflight"]["reason"])
        self.assertIn("cooling-off", result["preflight"]["reason"])

    # --- item 4b: eval.yml retries the preflight once with the fallback --

    def _run_preflight_step(self, *, roster_doc, claude_shim):
        """Run eval.yml's WIF auth preflight step for real, against a fake
        `claude` on PATH. No network, no real credential."""
        script = self._step_named("preflight")["run"]
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        runner = tmp / "runner"
        runner.mkdir()
        (runner / "anthropic-bearer").write_text("not-a-real-token", encoding="utf-8")
        if roster_doc is not None:
            (runner / "roster").mkdir()
            (runner / "roster" / "latest.json").write_text(
                json.dumps(roster_doc), encoding="utf-8")
        bindir = tmp / "bin"
        bindir.mkdir()
        fake = bindir / "claude"
        fake.write_text(claude_shim, encoding="utf-8")
        fake.chmod(0o755)
        env = dict(os.environ)
        env["RUNNER_TEMP"] = str(runner)
        env["PATH"] = f"{bindir}:{env['PATH']}"
        script_file = tmp / "preflight_step.sh"
        script_file.write_text(script, encoding="utf-8")
        proc = subprocess.run(["bash", "-e", str(script_file)], cwd=tmp, env=env,
                              capture_output=True, text=True, timeout=60)
        return {"rc": proc.returncode, "out": proc.stdout + proc.stderr}

    #: Fails when invoked with `--model claude-opus-5` (the roster's pick),
    #: succeeds on anything else (the ROSTER FALLBACK literal).
    CLAUDE_SHIM_FAILS_ON_ROSTER_MODEL = '''#!/usr/bin/env bash
model=""
prev=""
for a in "$@"; do
  if [ "$prev" = "--model" ]; then model="$a"; fi
  prev="$a"
done
if [ "$model" = "claude-opus-5" ]; then
  echo "not entitled to invoke claude-opus-5" >&2
  exit 1
fi
echo '{"result":"ok"}'
exit 0
'''

    CLAUDE_SHIM_ALWAYS_FAILS = '''#!/usr/bin/env bash
echo "nope" >&2
exit 1
'''

    def test_preflight_retries_once_with_the_fallback_on_failure(self):
        roster = {"preflight": {"id": "claude-opus-5", "reason": "x"}}
        got = self._run_preflight_step(
            roster_doc=roster, claude_shim=self.CLAUDE_SHIM_FAILS_ON_ROSTER_MODEL)
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertIn("::warning::", got["out"])
        self.assertIn("claude-opus-5", got["out"])
        self.assertIn("preflight model: claude-opus-5", got["out"])
        self.assertIn("preflight model: claude-haiku-4-5", got["out"],
                      "retried with the fallback")

    def test_preflight_fails_the_job_when_the_fallback_also_fails(self):
        roster = {"preflight": {"id": "claude-opus-5", "reason": "x"}}
        got = self._run_preflight_step(
            roster_doc=roster, claude_shim=self.CLAUDE_SHIM_ALWAYS_FAILS)
        self.assertNotEqual(got["rc"], 0)

    def test_preflight_does_not_retry_when_the_roster_model_already_succeeds(self):
        always_ok = '''#!/usr/bin/env bash
echo '{"result":"ok"}'
exit 0
'''
        roster = {"preflight": {"id": "claude-opus-5", "reason": "x"}}
        got = self._run_preflight_step(roster_doc=roster, claude_shim=always_ok)
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertNotIn("::warning::", got["out"])
        self.assertEqual(got["out"].count("preflight model:"), 1,
                         "no retry when the first attempt already succeeded")

    # --- item 5: `_clean_counts` misses OverflowError, non-finite floats,
    #             and negative counts ---------------------------------------

    def test_clean_counts_rejects_infinite_and_nan_cells(self):
        """`int(float('inf'))` raises OverflowError, which `except
        (TypeError, ValueError)` does not catch — a census cell of `1e400`
        (JSON overflows it to inf) or the literal `Infinity` used to exit by
        an uncaught traceback instead of being skipped as a bad cell."""
        notes = []
        cleaned = roster._clean_counts(
            {"claude-opus-5": {"2026-W36": float("inf"),
                               "2026-W35": float("-inf"),
                               "2026-W34": float("nan"),
                               "2026-W33": 50}}, notes.append)
        self.assertEqual(cleaned, {"claude-opus-5": {"2026-W33": 50}})
        self.assertTrue(any("number" in n for n in notes), notes)

    def test_main_does_not_crash_on_a_non_finite_census_count(self):
        """End-to-end: Python's `json` module accepts the bare `Infinity`
        literal by default (it is what `1e400` also decodes to). This used
        to reach `int()` unguarded and exit by traceback; eval.yml's
        extractor then printed the traceback's first line as the reason."""
        with tempfile.TemporaryDirectory() as tmp:
            models = Path(tmp) / "models.json"
            models.write_text(json.dumps(self._models_doc()), encoding="utf-8")
            census = Path(tmp) / "census.json"
            census.write_text(
                '{"generated_at": "2026-09-04T06:00:00Z", "weeks": %s, '
                '"counts": {"claude-sonnet-5": {"2026-W36": Infinity}}}'
                % json.dumps(self.W), encoding="utf-8")
            out = Path(tmp) / "roster" / "latest.json"
            argv = ["roster.py", "--models", str(models), "--policy",
                    str(self.POLICY), "--census", str(census), "--out", str(out)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(sys, "argv", argv), \
                 contextlib.redirect_stdout(stdout), \
                 contextlib.redirect_stderr(stderr):
                rc = roster.main()
            printed = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(rc, 0, printed)
        self.assertNotIn("Traceback", printed)

    def test_negative_counts_are_rejected_as_bad_cells(self):
        """A `-99` cell was accepted at face value — `int(-99)` does not
        raise — and fed straight into usage_share's totals, once producing
        a nonsensical 'carries 10000.0% of census usage'."""
        notes = []
        cleaned = roster._clean_counts(
            {"claude-opus-5": {"2026-W36": -99, "2026-W35": 50}}, notes.append)
        self.assertEqual(cleaned, {"claude-opus-5": {"2026-W35": 50}})
        self.assertTrue(any("number" in n for n in notes), notes)

    def test_a_cancelling_pair_does_not_net_to_a_smaller_share(self):
        """A `+100`/`-100` pair on the same model used to sum straight into
        usage_share's totals and net to zero usage — including a zero
        DENOMINATOR when that pair was the census's only entry, which the
        old `_census_verdict` (checking raw, un-rejected counts) read as
        usable."""
        notes = []
        cleaned = roster._clean_counts(
            {"claude-opus-5": {self.W[0]: 100, self.W[1]: -100},
             "claude-sonnet-5": {w: 100 for w in self.W[:4]}}, notes.append)
        rungs = roster.tier_rungs(self._policy())
        share = roster.usage_share(cleaned, "claude-opus-5", self.W[:4], rungs)
        self.assertEqual(share, 20.0,
                         "the -100 cell is rejected, not summed: opus-5 "
                         "keeps its 100 turns against a 500-turn ranked total")

    # --- item 6: an unreadable (present, but corrupt) census must not read
    #             the same as "none published" ----------------------------

    def test_main_reports_census_unreadable_and_it_reaches_the_arm_reasons(self):
        """`read_json` already distinguishes absent from present-but-
        unreadable; main() printed the distinction to stderr and then threw
        it away, passing `census_doc=None` either way — so a census
        truncated mid-write said 'no fresh census (none published)', a
        different (and wrong) fact."""
        with tempfile.TemporaryDirectory() as tmp:
            models = Path(tmp) / "models.json"
            models.write_text(json.dumps(self._models_doc()), encoding="utf-8")
            census = Path(tmp) / "census.json"
            census.write_text('{"generated_at": "2026-09-04T06:00:00Z", "wee',
                              encoding="utf-8")
            out = Path(tmp) / "roster" / "latest.json"
            argv = ["roster.py", "--models", str(models), "--policy",
                    str(self.POLICY), "--census", str(census), "--out", str(out)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with mock.patch.object(sys, "argv", argv), \
                 contextlib.redirect_stdout(stdout), \
                 contextlib.redirect_stderr(stderr):
                rc = roster.main()
            printed = stdout.getvalue() + stderr.getvalue()
            self.assertEqual(rc, 0, printed)
            self.assertIn("unreadable", printed.lower())
            published = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(published["arms"])
        for arm in published["arms"]:
            with self.subTest(arm=arm["id"]):
                self.assertIn("unreadable", arm["reason"].lower())
                self.assertNotIn("none published", arm["reason"].lower())

    def test_census_verdict_code_distinguishes_unreadable_from_absent(self):
        _, note, code = roster._census_verdict(
            None, 0, 0, self._policy(), self.NOW,
            census_problem="latest.json is present but unreadable (JSONDecodeError)")
        self.assertEqual(code, "unreadable")
        self.assertIn("JSONDecodeError", note)
        _, _, absent_code = roster._census_verdict(None, 0, 0, self._policy(), self.NOW)
        self.assertEqual(absent_code, "absent")


if __name__ == "__main__":
    unittest.main()
