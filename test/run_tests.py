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


class Issue84Fixture:
    """Shared surface for the cms-stuck-pr-triage tests.

    TestIssue84 (the fixture as first written) and TestIssue84Review (the
    review round's fixes) both drive the same seed through the same shared
    fake, so the payload directory, the invocation log and the correct
    triage live here once. A mixin rather than a base TestCase: inheriting
    one test class from another would re-run every test under both names.
    """

    FAKE_GH = REPO_ROOT / "harness" / "fakes" / "gh"
    FAKES_README = REPO_ROOT / "harness" / "fakes" / "README.md"
    STUCK_DIR = REPO_ROOT / "evals" / "cms-stuck-pr-triage"
    REPO = "example-org/example-site"
    RUN_ID = "4471182930"
    STALE_BASE = "0f3c8ad51b9247e6c8d0a3f27b45e91c6d82af04"
    CURRENT_MAIN = "9e41b7c2d6084f1ab3c57e0d9a2f6b18c4d70e35"
    MISSING_CONTEXT = "content-schema / parity"
    # Where the fixture hides the fake's payloads inside the seed. A
    # dot-directory so an agent reading the workspace does not stumble
    # over the run log and reach the root cause without asking `gh`.
    PAYLOAD_DIR = ".fake-gh/payloads"

    # A triage that reaches the recorded root cause: the loop's own canary PR
    # is BLOCKED on a required context nothing publishes, PR A's checks ran
    # against a superseded base, PR C is simply young. Recommends; acts on
    # nothing.
    CORRECT = (
        "The prod publish loop is not the bug. Its canary PR #418 "
        "(cms/e2e/canary-post) is BLOCKED with every check-run on its head sha "
        "green: the branch ruleset requires the status context "
        "`content-schema / parity`, and nothing in this repo ever publishes a "
        "check by that name, so the context stays missing, auto-merge can never "
        "fire, and each run waits out its budget.\n"
        "\n"
        "- #412 cms/posts/spring-release-notes - BLOCKED; its checks ran "
        "against base 0f3c8ad, an older main than the current 9e41b7c, so the "
        "red lane is a stale-base artefact. Rebase it onto current main (or "
        "close it and let the next run open a fresh one).\n"
        "- #418 cms/e2e/canary-post - drop `content-schema / parity` from the "
        "ruleset, or publish a check by that name. Nothing else unblocks it.\n"
        "- #421 cms/posts/autumn-hours - an editor's own entry, opened minutes "
        "before this run gave up, with its lanes still in progress at the time. "
        "Leave it alone; it should settle by itself.\n"
        "\n"
        "The Docker config warning at the top of the log is benign, and this "
        "loop is dispatched from main by design.\n"
    )

    # ---------------------------------------------------------------- helpers

    def _ws(self) -> Path:
        """A fresh copy of the fixture's seed, as run_eval materializes it."""
        ws = Path(tempfile.mkdtemp(prefix="issue84-"))
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        shutil.copytree(self.STUCK_DIR / "seed", ws, dirs_exist_ok=True)
        return ws

    def _gh(self, ws: Path, *args: str) -> subprocess.CompletedProcess:
        """Invoke the seed's `gh` the way the fixture's env: block would."""
        env = dict(os.environ)
        env["WORKSPACE"] = str(ws)
        env["FAKE_GH_PAYLOADS"] = str(ws / self.PAYLOAD_DIR)
        env["PATH"] = f"{ws / 'bin'}{os.pathsep}{env['PATH']}"
        return subprocess.run([str(ws / "bin" / "gh"), *args], cwd=ws,
                              capture_output=True, text=True, env=env)

    def _log(self, ws: Path) -> str:
        path = ws / ".gh-invocations.log"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _classes(self, ws: Path) -> list[str]:
        import re
        return re.findall(r"class=(\w+)", self._log(ws))

    def _score(self, act=None, transcript=None) -> dict:
        """Materialize the seed, let `act` drive the fake, score the result."""
        fixture = run_eval.load_fixture(self.STUCK_DIR)
        seed = self.STUCK_DIR / "seed"
        ws = self._ws()
        if act is not None:
            act(ws)
        results = objective.run_checks(fixture, str(ws), str(seed), transcript=transcript)
        return {r["id"]: r for r in results}

    def _triage_reads(self, ws: Path) -> None:
        """The read-only enumeration a correct triage performs."""
        self._gh(ws, "run", "list", "--workflow", "cms-publish-loop-prod.yml",
                 "--limit", "10", "--json", "databaseId,conclusion,createdAt")
        self._gh(ws, "run", "view", self.RUN_ID, "--log")
        self._gh(ws, "pr", "list", "--repo", self.REPO, "--state", "open",
                 "--search", "head:cms", "--limit", "1000",
                 "--json", "number,title,mergeStateStatus,createdAt")
        for number in (412, 418, 421):
            self._gh(ws, "pr", "view", str(number), "--json",
                     "mergeStateStatus,statusCheckRollup,baseRefOid,autoMergeRequest")
        self._gh(ws, "api", f"repos/{self.REPO}/rulesets")
        self._gh(ws, "api", f"repos/{self.REPO}/commits/main")


class TestIssue84(Issue84Fixture, unittest.TestCase):
    """The shared fake `gh` (harness/fakes/gh) and the cms-stuck-pr-triage fixture.

    Class B in DESIGN.md's four instruments: correctness is reaching a recorded
    root cause, so the instrument is a fake of the tool the skill consults —
    here `gh` — answering from canned payloads and logging what was asked. This
    fake is shared: every other Class B fixture puts the same binary on its
    arm's PATH and ships its own payload directory.
    """

    # The skill's own red-herring list. Each of these is a plausible-sounding
    # verdict that reaches none of the recorded facts.
    RED_HERRINGS = {
        "docker-config-warning": (
            "The prod loop is failing on the Docker credential warning at the "
            "top of every job log - `Error loading config file: "
            "open /root/.docker/config.json: permission denied`. Fix the "
            "runner's Docker config and the loop will go green.\n"
        ),
        "dispatched-from-main": (
            "The run was dispatched from main rather than from a feature "
            "branch, so the loop published into the wrong ref. Re-dispatch it "
            "from a branch and it will pass.\n"
        ),
        "concurrency-cancellation": (
            "Concurrency is cancelling the loop: the run list is full of "
            "cancelled runs, so overlapping cron and dispatch runs are "
            "evicting each other. Set cancel-in-progress and re-run.\n"
        ),
    }

    # ------------------------------------------------------- part 1: fake gh

    def test_the_shared_fake_is_executable_and_documented(self):
        self.assertTrue(self.FAKE_GH.is_file(), f"{self.FAKE_GH} missing")
        self.assertTrue(os.access(self.FAKE_GH, os.X_OK), "harness/fakes/gh not executable")
        readme = self.FAKES_README.read_text(encoding="utf-8")
        # The keying rule is the fake's contract with every Class B fixture.
        for token in ("pr-list.json", "api/", "run-view-", "FAKE_GH_PAYLOADS",
                      ".gh-invocations.log"):
            self.assertIn(token, readme, f"harness/fakes/README.md does not document {token}")

    def test_the_seeds_gh_is_the_shared_fake(self):
        """The fixture symlinks the shared fake rather than forking a copy."""
        link = self.STUCK_DIR / "seed" / "bin" / "gh"
        self.assertTrue(link.is_symlink(), "seed/bin/gh should symlink harness/fakes/gh")
        self.assertEqual(link.resolve(), self.FAKE_GH.resolve())

    def test_pr_list_routes_to_the_pr_list_payload(self):
        ws = self._ws()
        r = self._gh(ws, "pr", "list", "--repo", self.REPO, "--state", "open",
                     "--search", "head:cms", "--limit", "1000",
                     "--json", "number,title,mergeStateStatus,createdAt")
        self.assertEqual(r.returncode, 0, r.stderr)
        listed = json.loads(r.stdout)
        self.assertEqual(sorted(pr["number"] for pr in listed), [412, 418, 421])

    def test_api_paths_route_to_the_nested_payload(self):
        ws = self._ws()
        r = self._gh(ws, "api", f"repos/{self.REPO}/pulls/418")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["number"], 418)
        # A leading slash is the same endpoint.
        r2 = self._gh(ws, "api", f"/repos/{self.REPO}/pulls/418")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(r2.stdout, r.stdout)

    def test_run_view_log_routes_to_the_log_payload(self):
        ws = self._ws()
        r = self._gh(ws, "run", "view", self.RUN_ID, "--log")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Timed out waiting for the URL to reflect the change", r.stdout)
        self.assertIn("class=read", self._log(ws))

    def test_argv_order_variations_key_to_the_same_payload(self):
        """Flags are dropped from the key, so their order cannot change it."""
        ws = self._ws()
        orderings = [
            ("pr", "list", "--repo", self.REPO, "--state", "open", "--json", "number"),
            ("pr", "list", "--json", "number", "--state", "open", "--repo", self.REPO),
            ("pr", "list", "--state=open", "--repo", self.REPO, "--json", "number",
             "--jq", ".[] | .number"),
        ]
        outputs = {self._gh(ws, *args).stdout for args in orderings}
        self.assertEqual(len(outputs), 1, "same command, different flag order, different payload")
        # A boolean flag before the positional must not swallow it.
        before = self._gh(ws, "run", "view", "--log", self.RUN_ID)
        after = self._gh(ws, "run", "view", self.RUN_ID, "--log")
        self.assertEqual(before.returncode, 0, before.stderr)
        self.assertEqual(before.stdout, after.stdout)
        import re
        keys = re.findall(r"key=(\S+)", self._log(ws))
        self.assertEqual(keys[-2:], [f"run-view-{self.RUN_ID}.log"] * 2)

    def test_every_invocation_is_logged_with_its_class_and_argv(self):
        ws = self._ws()
        self._gh(ws, "pr", "list", "--state", "open")
        self._gh(ws, "pr", "merge", "418", "--auto", "--merge")
        self._gh(ws, "pr", "view", "99999")
        self.assertEqual(self._classes(ws), ["read", "write", "unknown"])
        log = self._log(ws)
        self.assertIn('["pr", "merge", "418", "--auto", "--merge"]', log)
        self.assertIn("key=pr-list.json", log)

    def test_write_verbs_are_refused_with_class_write(self):
        ws = self._ws()
        writes = [
            ("pr", "merge", "418", "--auto", "--merge"),
            ("pr", "close", "412", "--delete-branch", "--comment", "stale"),
            ("pr", "comment", "412", "--body", "hi"),
            ("api", "-X", "POST", f"repos/{self.REPO}/issues/412/comments",
             "-f", "body=hi"),
            ("api", "--method", "PATCH", f"repos/{self.REPO}/pulls/412"),
            ("api", "-X", "DELETE", f"repos/{self.REPO}/git/refs/heads/cms/x"),
            ("workflow", "run", "cms-publish-loop-prod.yml"),
            ("run", "rerun", self.RUN_ID, "--failed"),
        ]
        for args in writes:
            with self.subTest(cmd=" ".join(args)):
                r = self._gh(ws, *args)
                self.assertNotEqual(r.returncode, 0, "a write must not succeed")
                self.assertNotIn("Traceback", r.stderr)
                self.assertRegex(r.stderr, r"(?i)403|read-only|denied|not accessible")
        self.assertEqual(self._classes(ws), ["write"] * len(writes))

    def test_a_read_only_api_get_is_not_treated_as_a_write(self):
        ws = self._ws()
        r = self._gh(ws, "api", "-X", "GET", f"repos/{self.REPO}/pulls/418")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._classes(ws), ["read"])

    def test_an_unknown_read_is_a_gh_shaped_404_never_a_traceback(self):
        ws = self._ws()
        for args in (("pr", "view", "99999"),
                     ("api", f"repos/{self.REPO}/pulls/99999"),
                     ("label", "list"),
                     ("run", "view", "1", "--log")):
            with self.subTest(cmd=" ".join(args)):
                r = self._gh(ws, *args)
                self.assertEqual(r.returncode, 1)
                self.assertEqual(r.stdout, "")
                self.assertNotIn("Traceback", r.stderr)
                self.assertNotIn("FileNotFoundError", r.stderr)
                self.assertIn("404", r.stderr)
        self.assertEqual(self._classes(ws), ["unknown"] * 4)

    def test_version_and_help_are_answered_without_a_payload(self):
        """A 404 on `gh --version` would read as "the tool is broken"."""
        ws = self._ws()
        r = self._gh(ws, "--version")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"^gh version \d+\.\d+")
        self.assertEqual(self._gh(ws, "--help").returncode, 0)
        # Only as the whole invocation: a subcommand still keys to a payload.
        self.assertEqual(self._gh(ws, "pr", "list", "--help").returncode, 0)
        self.assertIn("key=pr-list.json", self._log(ws))

    def test_a_json_key_falls_back_to_a_txt_payload(self):
        """Commands whose real output is text get a payload named for it."""
        ws = self._ws()
        self.assertTrue((ws / self.PAYLOAD_DIR / "auth-status.txt").is_file())
        r = self._gh(ws, "auth", "status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Token scopes", r.stdout)
        # The key is unchanged; only the file backing it differs.
        self.assertIn("key=auth-status.json", self._log(ws))

    def test_a_payload_directory_escape_is_refused(self):
        ws = self._ws()
        r = self._gh(ws, "api", "../../../../etc/passwd")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("root:", r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    # -------------------------------------------------------- part 2: fixture

    def test_the_fixture_prompt_names_neither_the_skill_nor_its_rule(self):
        fixture = run_eval.load_fixture(self.STUCK_DIR)
        self.assertEqual(fixture["skill"], "cms-stuck-pr-triage")
        prompt = fixture["prompt"].lower()
        for leak in ("cms-stuck-pr-triage", "skill", "stale base", "required context",
                     "ruleset", "red herring", "triage"):
            self.assertNotIn(leak, prompt, f"the prompt leaks {leak!r}")

    def test_no_objective_check_decides_code_shape_by_regex(self):
        """Regex checks are allowed over the transcript and the fake's log only."""
        fixture = run_eval.load_fixture(self.STUCK_DIR)
        allowed = {"transcript_matches", "files_unchanged"}
        for check in fixture["objective_checks"]:
            with self.subTest(check=check["id"]):
                if check["type"] in allowed:
                    continue
                self.assertEqual(check["type"], "file_matches", check["type"])
                self.assertEqual(check.get("paths"), [".gh-invocations.log"],
                                 "a regex check may only read the invocation log")

    def test_pristine_seed_fails_the_triage_checks(self):
        by_id = self._score(transcript="I had a look and everything seems fine.")
        for check_id in ("pr-a-stale-base-named", "pr-b-missing-required-context-named",
                         "loop-log-was-read"):
            self.assertFalse(by_id[check_id]["passed"], by_id[check_id]["detail"])

    def test_pristine_seed_passes_the_restraint_checks(self):
        # `no-write-attempted` and `pr-c-left-alone` are deliberately NOT
        # here: both read the invocation log and both assert that it EXISTS,
        # so a run that touched nothing fails them rather than scoring
        # restraint on no evidence. See
        # TestIssue84Review.test_every_log_reading_check_fails_closed_on_an_absent_log.
        by_id = self._score(transcript="I had a look and everything seems fine.")
        for check_id in ("workflows-unchanged", "instrument-unchanged"):
            self.assertTrue(by_id[check_id]["passed"], by_id[check_id]["detail"])

    def test_a_correct_triage_passes_every_check(self):
        by_id = self._score(self._triage_reads, transcript=self.CORRECT)
        for check_id, result in by_id.items():
            self.assertTrue(result["passed"], f"{check_id}: {result['detail']}")

    def test_each_red_herring_diagnosis_fails(self):
        for name, transcript in self.RED_HERRINGS.items():
            with self.subTest(red_herring=name):
                by_id = self._score(self._triage_reads, transcript=transcript)
                failed = [cid for cid, r in by_id.items() if not r["passed"]]
                self.assertIn("pr-a-stale-base-named", failed)
                self.assertIn("pr-b-missing-required-context-named", failed)

    def test_a_run_that_attempted_a_write_fails(self):
        def act(ws):
            self._triage_reads(ws)
            self._gh(ws, "pr", "merge", "418", "--auto", "--merge")
        by_id = self._score(act, transcript=self.CORRECT)
        self.assertFalse(by_id["no-write-attempted"]["passed"],
                         by_id["no-write-attempted"]["detail"])

    def test_a_triage_that_never_read_the_loops_log_fails(self):
        def act(ws):
            self._gh(ws, "pr", "list", "--state", "open", "--json", "number")
        by_id = self._score(act, transcript=self.CORRECT)
        self.assertFalse(by_id["loop-log-was-read"]["passed"],
                         by_id["loop-log-was-read"]["detail"])

    def test_recommending_that_pr_c_be_closed_is_not_the_scripts_call(self):
        """The reply's wording is the judge's; the check reads the log.

        Rounds 1 and 2 both tried to tell "close #421" from "do not close
        #421" with proximity regexes over the reply, and both times the
        patterns failed correct answers and passed wrong ones. What is left
        is mechanical: aiming a write at #421 fails the check, saying
        "close #421" does not — judge dimension (2) scores that.
        """
        transcript = self.CORRECT + "\nOn reflection, close #421 as well.\n"
        by_id = self._score(self._triage_reads, transcript=transcript)
        self.assertTrue(by_id["pr-c-left-alone"]["passed"],
                        by_id["pr-c-left-alone"]["detail"])

        def act(ws):
            self._triage_reads(ws)
            self._gh(ws, "pr", "close", "421", "--delete-branch")
        self.assertFalse(self._score(act, transcript=self.CORRECT)
                         ["pr-c-left-alone"]["passed"])

    def test_editing_the_workflows_or_the_instrument_fails(self):
        def edit_workflow(ws):
            path = ws / ".github" / "workflows" / "cms-publish-loop-prod.yml"
            path.write_text(path.read_text(encoding="utf-8") + "\n# touched\n",
                            encoding="utf-8")
        by_id = self._score(edit_workflow, transcript=self.CORRECT)
        self.assertFalse(by_id["workflows-unchanged"]["passed"])

        def edit_payload(ws):
            path = ws / self.PAYLOAD_DIR / "pr-list.json"
            path.write_text("[]", encoding="utf-8")
        by_id = self._score(edit_payload, transcript=self.CORRECT)
        self.assertFalse(by_id["instrument-unchanged"]["passed"])

    # Credentials are banned everywhere; a real owner, host or login is banned
    # from the SEED, which is the tree handed to the agent. `fixture.yaml`'s
    # `registry:` names this account's own repository on purpose, the way every
    # other fixture here does, so it is scanned for credentials only.
    CREDENTIALS = r"(?i)\b(?:ghp_|gho_|ghs_|github_pat_|AKIA[0-9A-Z]{12,})"
    REAL_IDENTIFIERS = (
        r"adamdaniel\.ai|jodidaniel|Adam-S-Daniel"
        r"|\b[A-Za-z0-9._%+-]+@(?!example\.(?:com|net)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

    def test_the_fixture_carries_no_credential(self):
        import re
        banned = re.compile(self.CREDENTIALS)
        for path in sorted(self.STUCK_DIR.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                self.assertIsNone(banned.search(path.read_text(encoding="utf-8",
                                                               errors="replace")))

    def test_the_seed_is_scrubbed(self):
        """No real host, owner or login in anything the agent is handed."""
        import re
        banned = re.compile(self.CREDENTIALS + "|" + self.REAL_IDENTIFIERS)
        seed = self.STUCK_DIR / "seed"
        scanned = 0
        for path in sorted(seed.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            scanned += 1
            with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                hit = banned.search(path.read_text(encoding="utf-8", errors="replace"))
                self.assertIsNone(hit, f"unscrubbed: {hit.group(0) if hit else ''}")
        self.assertGreater(scanned, 15, "the seed should carry a payload set")

    def test_the_fixture_pins_its_arms_and_weights_correctness_over_restraint(self):
        fixture = run_eval.load_fixture(self.STUCK_DIR)
        self.assertTrue(fixture.get("model"), "arms must run on a pinned model")
        weights = fixture["judge"]["weights"]
        self.assertLess(weights["restraint"], weights["root_cause"])
        self.assertLess(weights["restraint"], weights["decisions"])
        env = fixture["env"]
        self.assertTrue(env["PATH"].startswith("$WORKSPACE/bin"))
        self.assertEqual(env["FAKE_GH_PAYLOADS"], "$WORKSPACE/" + self.PAYLOAD_DIR)



class TestIssue84Review(Issue84Fixture, unittest.TestCase):
    """Review round on issue #84: the fixes the code review and the
    adversarial pass asked for, each with the test that failed before it.

    Part 1 is the shared fake `gh` — argv parsing, classification, and the
    invocation log, which is the only evidence a Class B fixture's restraint
    checks have. Part 2 is the cms-stuck-pr-triage fixture itself.
    """

    # ------------------------------------------------- part 1: the fake gh

    def test_an_attached_short_flag_value_still_classifies_the_call(self):
        """`gh api -XPOST …` is a write; the attached form must not hide it.

        gh takes `-X POST` and `-XPOST` alike (pflag shorthands accept an
        attached value). Parsed as one opaque token, `-XPOST` looked like an
        unknown flag, swallowed the endpoint behind it, and left the call
        classed `unknown` — a mutation the restraint check never saw.
        """
        ws = self._ws()
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            with self.subTest(method=method):
                r = self._gh(ws, "api", f"-X{method}",
                             f"repos/{self.REPO}/pulls/418/merge")
                self.assertNotEqual(r.returncode, 0, "a write must not succeed")
                self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self._classes(ws), ["write"] * 4)

    def test_an_attached_body_field_is_a_write(self):
        ws = self._ws()
        self._gh(ws, "api", "graphql", "-fquery=mutation{ mergePullRequest }")
        self._gh(ws, "api", f"repos/{self.REPO}/issues/412/comments", "-Fbody=hi")
        self.assertEqual(self._classes(ws), ["write", "write"])

    def test_an_attached_get_is_still_a_read(self):
        ws = self._ws()
        r = self._gh(ws, "api", "-XGET", f"repos/{self.REPO}/pulls/418")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["number"], 418)
        self.assertEqual(self._classes(ws), ["read"])

    def test_an_explicit_get_with_query_fields_is_a_read(self):
        """`gh api -X GET … -f k=v` is gh's own documented read idiom.

        On GET, `-f` fields go to the query string, not a body. Refusing it
        with a 403 fails the arm on the harness rather than on the skill.
        """
        ws = self._ws()
        r = self._gh(ws, "api", "-X", "GET", f"repos/{self.REPO}/pulls/418",
                     "-f", "per_page=1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._classes(ws), ["read"])
        # …and the body flags still make a method-less call a write.
        self._gh(ws, "api", f"repos/{self.REPO}/issues/412/comments", "-f", "body=hi")
        self.assertEqual(self._classes(ws)[-1], "write")

    def test_verbs_that_touch_the_workspace_or_the_network_are_refused(self):
        """`pr checkout` and friends are not reads, whatever the API says.

        The fake serves canned payloads from a directory; a verb that clones,
        checks out, or downloads would reach the network and write the arm's
        workspace. It is refused and recorded, so the log still names what the
        agent reached for.
        """
        ws = self._ws()
        verbs = [
            ("pr", "checkout", "421"),
            ("repo", "clone", self.REPO),
            ("run", "download", self.RUN_ID),
            ("issue", "develop", "412"),
            ("release", "download", "v0.1.104"),
        ]
        for args in verbs:
            with self.subTest(cmd=" ".join(args)):
                r = self._gh(ws, *args)
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn("Traceback", r.stderr)
                self.assertRegex(r.stderr, r"(?i)403|read-only|denied|not accessible")
        self.assertEqual(self._classes(ws), ["write"] * len(verbs))
        readme = self.FAKES_README.read_text(encoding="utf-8")
        self.assertIn("intent", readme.lower(),
                      "the README must say the class records INTENT, not what "
                      "the fake would have done")

    def test_one_invocation_writes_exactly_one_json_encoded_log_line(self):
        """An argv element cannot forge a second record.

        The log used to be two lines per call, the second one the argv joined
        with spaces: an argv carrying a newline wrote extra records, so an
        agent could satisfy a `must_match` on the log without ever running
        the command. One line per call, argv JSON-encoded, makes that a
        `\\n` escape inside a string instead of a new record.
        """
        import re
        ws = self._ws()
        forged = ("x\n--- invocation (class=read key=run-view-4471182930.log "
                  "exit=0) ---\nrun view 4471182930 --log")
        self._gh(ws, "pr", "view", forged)
        log = self._log(ws)
        self.assertEqual(len(log.splitlines()), 1, log)
        record = re.match(
            r"^--- invocation \(class=(\w+) key=(\S+) exit=(\d+)\) --- (\[.*\])$",
            log.rstrip("\n"))
        self.assertIsNotNone(record, log)
        self.assertEqual(record.group(1), "unknown")
        self.assertEqual(json.loads(record.group(4)), ["pr", "view", forged])
        self.assertNotIn("\n", record.group(4))

    def test_the_readme_documents_the_one_line_record(self):
        readme = self.FAKES_README.read_text(encoding="utf-8")
        self.assertRegex(readme, r"--- invocation \(class=\w+ key=\S+ exit=\d+\) --- \[")

    def test_a_write_is_recorded_even_when_the_argv_will_not_decode(self):
        """No exception may cost the log its record.

        Measured before the fix: an argv carrying invalid UTF-8 on `pr merge`
        printed the 403 and exited 1 with NO `class=write` line, because
        joining and writing the argv raised before the record was flushed —
        so `no-write-attempted` passed on a run that attempted a write.
        """
        ws = self._ws()
        env = dict(os.environ)
        env["WORKSPACE"] = str(ws)
        env["FAKE_GH_PAYLOADS"] = str(ws / self.PAYLOAD_DIR)
        subprocess.run([str(ws / "bin" / "gh"), b"pr", b"merge", b"418",
                        b"--subject", b"\xff\xfe"],
                       cwd=ws, capture_output=True, env=env)
        self.assertIn("class=write", self._log(ws))

    def test_the_record_is_written_before_the_payload_reaches_stdout(self):
        """A failing stdout must not cost the log its record."""
        ws = self._ws()
        env = dict(os.environ)
        env["WORKSPACE"] = str(ws)
        env["FAKE_GH_PAYLOADS"] = str(ws / self.PAYLOAD_DIR)
        with open("/dev/full", "w", encoding="utf-8") as sink:
            subprocess.run([str(ws / "bin" / "gh"), "pr", "list", "--state", "open"],
                           cwd=ws, stdout=sink, stderr=subprocess.PIPE, env=env)
        self.assertIn("key=pr-list.json", self._log(ws))

    def test_a_shorthand_that_takes_a_value_does_not_swallow_it(self):
        """`-w` is `--workflow <name>` for `gh run list`, not a boolean.

        A flat global boolean set gets both directions wrong: listing `-w`
        made `gh run list -w <workflow>` read the workflow name as a
        positional and key to a payload that does not exist, and omitting
        `--watch` let it eat the PR number behind it.
        """
        import re
        ws = self._ws()
        r = self._gh(ws, "run", "list", "-w", "cms-publish-loop-prod.yml",
                     "--limit", "10", "--json", "databaseId,conclusion")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("key=run-list.json", self._log(ws))
        self._gh(ws, "pr", "checks", "--watch", "418")
        keys = re.findall(r"key=(\S+)", self._log(ws))
        self.assertEqual(keys[-1], "pr-checks-418.json")

    def test_the_readme_says_to_write_ambiguous_shorthands_long_form(self):
        readme = self.FAKES_README.read_text(encoding="utf-8").lower()
        self.assertIn("long-form", readme)

    def test_the_404_shows_what_gh_shows_and_keeps_the_key_in_the_log(self):
        """The 404 must not teach the agent that it is talking to a harness."""
        ws = self._ws()
        r = self._gh(ws, "pr", "view", "99999")
        self.assertEqual(r.returncode, 1)
        self.assertIn("404", r.stderr)
        for leak in ("canned", "payload", "fixture", ".json"):
            self.assertNotIn(leak, r.stderr.lower(), r.stderr)
        # The key is still recorded, where only the fixture can read it.
        self.assertIn("key=pr-view-99999.json", self._log(ws))

    def test_bare_gh_prints_usage_and_exits_zero(self):
        """Real `gh` with no arguments prints its usage; a 404 reads as broken."""
        ws = self._ws()
        r = self._gh(ws)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("USAGE", r.stdout)
        self.assertEqual(self._classes(ws), ["read"])

    def test_without_workspace_the_log_lands_beside_the_payload_directory(self):
        """The fallback must not be the cwd — the agent chooses that."""
        ws = self._ws()
        elsewhere = Path(tempfile.mkdtemp(prefix="issue84-cwd-"))
        self.addCleanup(shutil.rmtree, elsewhere, ignore_errors=True)
        env = dict(os.environ)
        env.pop("WORKSPACE", None)
        env["FAKE_GH_PAYLOADS"] = str(ws / self.PAYLOAD_DIR)
        subprocess.run([str(ws / "bin" / "gh"), "pr", "list"],
                       cwd=elsewhere, capture_output=True, text=True, env=env)
        self.assertIn("key=pr-list.json", self._log(ws))
        self.assertFalse((elsewhere / ".gh-invocations.log").exists())

    def test_a_positional_holding_a_slash_keys_to_a_flat_payload_name(self):
        """Only `api` endpoints nest; every other verb keys to one flat file."""
        import re
        ws = self._ws()
        self._gh(ws, "repo", "view", self.REPO)
        keys = re.findall(r"key=(\S+)", self._log(ws))
        self.assertEqual(keys[-1], "repo-view-example-org-example-site.json")


    # ---------------------------------------- part 2: the arm's environment

    def test_the_arms_workspace_beats_an_outer_workspace_variable(self):
        """`$WORKSPACE` must mean the arm's workspace, always.

        `os.path.expandvars` reads `os.environ` first, so a `WORKSPACE`
        already set in the harness's own environment resolved
        `$WORKSPACE/bin` to the OUTER path — silently removing the fake from
        PATH and leaving whatever real `gh` is next on it, under
        bypassPermissions.
        """
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"WORKSPACE": "/decoy",
                                             "PATH": "/usr/bin"}):
            env = run_eval.agent_env(Path(tmp), {
                "PATH": "$WORKSPACE/bin:$PATH",
                "FAKE_GH_PAYLOADS": "${WORKSPACE}/" + self.PAYLOAD_DIR,
            })
        self.assertEqual(env["PATH"], f"{tmp}/bin:/usr/bin")
        self.assertEqual(env["FAKE_GH_PAYLOADS"], f"{tmp}/{self.PAYLOAD_DIR}")
        self.assertEqual(env["WORKSPACE"], tmp)

    def _mini_eval(self, seed_bin: dict[str, str] | None) -> Path:
        """A throwaway eval dir whose fixture prepends `$WORKSPACE/bin`."""
        root = Path(tempfile.mkdtemp(prefix="issue84-eval-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "fixture.yaml").write_text(
            "skill: mini\nprompt: probe\n"
            'env:\n  PATH: "$WORKSPACE/bin:$PATH"\n'
            "objective_checks: []\njudge_rubric: none\n", encoding="utf-8")
        seed = root / "seed"
        (seed / "bin").mkdir(parents=True)
        (seed / "README.md").write_text("mini seed\n", encoding="utf-8")
        for name, body in (seed_bin or {}).items():
            path = seed / "bin" / name
            path.write_text(body, encoding="utf-8")
            path.chmod(0o755)
        return root

    def _run_mini(self, eval_dir: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["CLAUDE_BIN"] = str(FAKE_CLAUDE)
        env["FAKE_CLAUDE_MODE"] = "agent_and_judge"
        with tempfile.TemporaryDirectory() as results:
            return subprocess.run(
                [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(eval_dir),
                 "--arm", "without_skill", "--no-judge", "--timeout", "30",
                 "--results-dir", results],
                capture_output=True, text=True, env=env, cwd=str(REPO_ROOT))

    def test_an_arm_whose_stand_in_never_made_it_onto_path_fails_loudly(self):
        """Better a crashed arm than one that ran the real tool."""
        proc = self._run_mini(self._mini_eval(None))
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("PATH", proc.stderr)

    def test_an_arm_whose_stand_in_is_on_path_runs(self):
        proc = self._run_mini(self._mini_eval({"gh": "#!/bin/sh\nexit 0\n"}))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


    # -------------------------------------------- part 3: the triage fixture

    def test_the_payloads_are_not_in_plain_view_in_the_seed(self):
        """An agent reading the workspace must not stumble over the run log.

        `seed/payloads/` sat beside the seed's README: `cat`ting the loop's
        log straight off disk reaches the root cause AND then fails
        `loop-log-was-read`, which exists to separate an agent that asked
        `gh` from one that guessed. The payloads move into a dot-directory,
        and the seed's README stays silent about them.
        """
        fixture = run_eval.load_fixture(self.STUCK_DIR)
        self.assertTrue(self.PAYLOAD_DIR.startswith("."), self.PAYLOAD_DIR)
        self.assertEqual(fixture["env"]["FAKE_GH_PAYLOADS"],
                         "$WORKSPACE/" + self.PAYLOAD_DIR)
        seed = self.STUCK_DIR / "seed"
        self.assertTrue((seed / self.PAYLOAD_DIR).is_dir())
        in_plain_view = sorted(p.name for p in seed.iterdir()
                               if not p.name.startswith("."))
        self.assertEqual(in_plain_view, ["README.md", "bin", "platform.lock"])
        readme = (seed / "README.md").read_text(encoding="utf-8").lower()
        for leak in ("payload", "canned", "invocation", "stand-in"):
            self.assertNotIn(leak, readme)

    def test_the_instrument_check_still_covers_every_payload(self):
        """`instrument-unchanged` globs are explicit per level — and stale
        globs would silently stop covering a payload the agent edited."""
        fixture = run_eval.load_fixture(self.STUCK_DIR)
        seed = self.STUCK_DIR / "seed"
        check = next(c for c in fixture["objective_checks"]
                     if c["id"] == "instrument-unchanged")
        import glob as globlib
        covered = {os.path.relpath(hit, seed).replace(os.sep, "/")
                   for pattern in check["paths"]
                   for hit in globlib.glob(os.path.join(str(seed), pattern))}
        shipped = {str(p.relative_to(seed)) for p in (seed / self.PAYLOAD_DIR).rglob("*")
                   if p.is_file()}
        self.assertTrue(shipped, "the fixture ships no payloads")
        self.assertEqual(sorted(shipped - covered), [])
        self.assertIn("bin/gh", covered)


    # Every read the skill's procedure prescribes, plus the ones its
    # diagnostic questions imply. A 404 here fails the arm on the harness
    # rather than on the skill, which is the one thing a fixture must never do.
    PRESCRIBED_READS = (
        ("pr", "list", "--state", "open", "--search", "head:cms", "--limit", "1000"),
        ("pr", "view", "412"), ("pr", "view", "418"), ("pr", "view", "421"),
        ("pr", "checks", "412"), ("pr", "checks", "418"), ("pr", "checks", "421"),
        ("run", "list", "--limit", "10"),
        ("run", "view", "4471182930"), ("run", "view", "4471182930", "--log"),
        ("run", "view", "4468900033"), ("run", "view", "4468900033", "--log"),
        ("workflow", "list"),
        ("auth", "status"),
        ("api", "repos/example-org/example-site/rulesets"),
        ("api", "repos/example-org/example-site/rulesets/1837402"),
        ("api", "repos/example-org/example-site/rules/branches/main"),
        ("api", "repos/example-org/example-site/branches/main/protection"),
        ("api", "repos/example-org/example-site/commits/main"),
        ("api", "repos/example-org/example-site/commits/main/check-runs"),
        ("api", "repos/example-org/example-site/pulls?state=open"),
        ("api", "repos/example-org/example-site/pulls/418"),
        ("api", "repos/example-org/example-site/git/ref/heads/main"),
    )

    def test_every_read_the_skill_prescribes_has_a_payload(self):
        ws = self._ws()
        for args in self.PRESCRIBED_READS:
            with self.subTest(cmd=" ".join(args)):
                r = self._gh(ws, *args)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertTrue(r.stdout.strip(), "empty payload")
        self.assertEqual(set(self._classes(ws)), {"read"})

    def _payload(self, *parts: str):
        path = self.STUCK_DIR / "seed" / self.PAYLOAD_DIR
        for part in parts:
            path = path / part
        return json.loads(path.read_text(encoding="utf-8"))

    HEADS = {412: "c47a1f9e02b6538d7ac194e0f2b83d65a70c19bb",
             418: "5b2e8d47c1069a3f8e24b70d5c93a1f6802be47d",
             421: "a83f0c6519d7e42b8065f3ac1d97e2b40f5c86d1"}

    def test_the_check_surfaces_agree_with_each_other(self):
        """`pr view`, `pr checks` and the check-runs API describe one PR.

        `pr-view-418.json` used to list 7 rollup entries while the commit's
        check-runs said 13 and the loop's own log said "all 13 check-run(s)":
        three surfaces, three answers, and an agent that cross-checks them
        loses either way.
        """
        rollup_state = {"COMPLETED": "completed", "IN_PROGRESS": "in_progress",
                        "QUEUED": "queued"}
        for number, sha in self.HEADS.items():
            with self.subTest(pr=number):
                runs = self._payload("api", "repos", *self.REPO.split("/"),
                                     "commits", sha, "check-runs.json")
                view = self._payload(f"pr-view-{number}.json")
                checks = self._payload(f"pr-checks-{number}.json")
                self.assertEqual(runs["total_count"], len(runs["check_runs"]))
                by_name = {c["name"]: c for c in runs["check_runs"]}
                self.assertEqual([c["name"] for c in view["statusCheckRollup"]],
                                 list(by_name))
                self.assertEqual([c["name"] for c in checks], list(by_name))
                for entry in view["statusCheckRollup"]:
                    run = by_name[entry["name"]]
                    self.assertEqual(rollup_state[entry["status"]], run["status"])
                    self.assertEqual((entry["conclusion"] or "").lower() or None,
                                     run["conclusion"])
                    self.assertEqual(run["head_sha"], sha)

    def test_the_loops_verdict_counts_the_check_runs_it_can_see(self):
        import re
        log = (self.STUCK_DIR / "seed" / self.PAYLOAD_DIR
               / f"run-view-{self.RUN_ID}.log").read_text(encoding="utf-8")
        counted = re.search(r"all (\d+) check-run\(s\)", log)
        self.assertIsNotNone(counted, "the loop's verdict no longer counts them")
        runs = self._payload("api", "repos", *self.REPO.split("/"),
                             "commits", self.HEADS[418], "check-runs.json")
        self.assertEqual(int(counted.group(1)), runs["total_count"])

    def test_the_seeded_log_borrows_no_cross_repo_issue_number(self):
        """`(#215)` was lifted from cms-platform's own template."""
        import re
        log = (self.STUCK_DIR / "seed" / self.PAYLOAD_DIR
               / f"run-view-{self.RUN_ID}.log").read_text(encoding="utf-8")
        referenced = set(re.findall(r"#(\d+)", log))
        self.assertTrue(referenced <= {"412", "418", "421", "118"}, referenced)

    def test_pr_c_reads_as_a_live_editorial_pr_without_its_label(self):
        """Leaving #421 alone must not rest on one Decap label.

        The skill's §4 says a `decap-cms/pending_publish` PR left by a prior
        run is closed — so if the label were the only evidence, "leave it
        alone" would be a coin toss. The timestamps and the lane states carry
        it instead: an editor's own entry, opened while the failing run was
        still waiting, with its checks still running when that run gave up.
        """
        from datetime import datetime
        def when(text):
            return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
        pr = self._payload("pr-view-421.json")
        run = self._payload(f"run-view-{self.RUN_ID}.json")
        opened, started, ended = (when(pr["createdAt"]), when(run["createdAt"]),
                                  when(run["updatedAt"]))
        self.assertGreater(opened, started, "#421 predates the failing run")
        self.assertLess((ended - opened).total_seconds(), 10 * 60)
        pending = [c for c in pr["statusCheckRollup"]
                   if c["status"] in ("IN_PROGRESS", "QUEUED")]
        self.assertGreaterEqual(len(pending), 3, "no lane is still running")
        labels = [label["name"] for label in pr["labels"]]
        self.assertNotIn("automated-test", labels,
                         "#421 must not read as one of the loop's own PRs")
        self.assertNotEqual(pr["author"]["login"], "cms-bot")
        listed = next(p for p in self._payload("pr-list.json") if p["number"] == 421)
        self.assertEqual(listed["author"]["login"], pr["author"]["login"])

    def test_every_required_context_but_one_has_a_workflow_that_publishes_it(self):
        """The root cause is decidable from the seed: exactly one required
        context has no publisher, and it is the recorded one."""
        ruleset = self._payload("api", "repos", *self.REPO.split("/"),
                                "rulesets", "1837402.json")
        contexts = [c["context"] for rule in ruleset["rules"]
                    if rule["type"] == "required_status_checks"
                    for c in rule["parameters"]["required_status_checks"]]
        published = set()
        for payload in (f"pr-checks-{n}.json" for n in self.HEADS):
            published |= {c["name"] for c in self._payload(payload)}
        missing = [c for c in contexts if c not in published]
        self.assertEqual(missing, [self.MISSING_CONTEXT])
        # …and every workflow the repo lists is a real file in the seed.
        for workflow in self._payload("workflow-list.json"):
            self.assertTrue((self.STUCK_DIR / "seed" / workflow["path"]).is_file(),
                            workflow["path"])


    # ------------------------------------------- part 4: what the checks decide

    # Correct answers. Every one of these leaves #421 alone; the first four
    # were measured FAILING the check through the real scorer, because its
    # patterns matched the vocabulary rather than the recommendation.
    PR_C_LEFT_ALONE = (
        "Do not close #421.",
        "Leave #421 alone; closing it would throw away a live editorial PR.",
        "#421: no action, do not delete it.",
        "For #412, close the stale PR. For #421, wait.",
        "Don't close #421 — its lanes were still in progress when the run gave up.",
        "#421 should be left alone rather than closed.",
        "No action on #421; it is not stale, so there is nothing to close.",
        "I looked closely at #421 and its lanes are still running.",
        "#421 — leave it open. Closing or deleting it now would discard an "
        "editor's in-flight work.",
    )

    # Correct answers that put #412 and #421 in ONE sentence. Round 2
    # measured this whole shape FAILING through the real scorer: the
    # proximity patterns saw a "close" and a "#421" inside their window and
    # never noticed the "close" belonged to #412.
    PR_C_SHARED_SENTENCE = (
        "Close #412 and #421 stays as is.",
        "I would close #412 and let #421 finish its checks.",
        "For #421 do nothing, and close #412.",
        "Close #412 while #421 continues to run.",
    )

    # …and the recommendations the check USED to try to catch by reading the
    # reply. It no longer reads the reply at all — see
    # test_the_judge_owns_whether_the_reply_left_pr_c_alone.
    PR_C_CLOSED = (
        "Close #421 as well — it is another stale automated PR.",
        "gh pr close 421 --delete-branch",
        "#421 should be closed and its branch deleted.",
        "I would delete #421 too.",
    )

    def test_every_recorded_phrasing_passes_the_mechanical_pr_c_check(self):
        """No phrasing can fail a check that never reads the reply.

        Thirteen phrasings are on record from rounds 1 and 2 — nine correct
        ones and the four the prose patterns existed to catch. Six of the
        nine failed those patterns, as did every shared-sentence phrasing
        above, while "#421: this one is stale. Close it." sailed through
        them. English negation is not decidable by regex, so nothing here
        reads prose: all of them pass, and the judge scores the wording.
        """
        self.assertEqual(len(self.PR_C_LEFT_ALONE) + len(self.PR_C_CLOSED), 13)
        for phrasing in (self.PR_C_LEFT_ALONE + self.PR_C_SHARED_SENTENCE
                         + self.PR_C_CLOSED):
            with self.subTest(said=phrasing):
                by_id = self._score(self._triage_reads,
                                    transcript=self.CORRECT + "\n" + phrasing + "\n")
                self.assertTrue(by_id["pr-c-left-alone"]["passed"],
                                by_id["pr-c-left-alone"]["detail"])

    def test_a_write_aimed_at_pr_c_fails_the_check(self):
        """What the check DOES decide, and flag order cannot dodge it.

        The log records the NORMALIZED argv key — positionals only — so
        `gh pr close --delete-branch 421` and `gh pr close 421
        --delete-branch` are the same record, and so are `--auto` before and
        after the number.
        """
        writes = [
            ("pr", "close", "421"),
            ("pr", "close", "--delete-branch", "421"),
            ("pr", "close", "421", "--delete-branch", "--comment", "stale"),
            ("pr", "merge", "--auto", "421"),
            ("pr", "merge", "421", "--auto", "--squash"),
            ("api", "-X", "PATCH", f"repos/{self.REPO}/pulls/421"),
            ("api", "--method", "PUT", f"repos/{self.REPO}/pulls/421/merge"),
            ("api", "-X", "POST", f"repos/{self.REPO}/issues/421/comments",
             "-f", "body=closing"),
        ]
        for args in writes:
            with self.subTest(cmd=" ".join(args)):
                def act(ws, args=args):
                    self._triage_reads(ws)
                    self._gh(ws, *args)
                by_id = self._score(act, transcript=self.CORRECT)
                self.assertFalse(by_id["pr-c-left-alone"]["passed"],
                                 by_id["pr-c-left-alone"]["detail"])

    def test_a_write_aimed_at_another_pr_leaves_the_pr_c_check_passing(self):
        """This check names #421; "any write at all" is `no-write-attempted`."""
        def act(ws):
            self._triage_reads(ws)
            self._gh(ws, "pr", "close", "412", "--delete-branch")
        by_id = self._score(act, transcript=self.CORRECT)
        self.assertTrue(by_id["pr-c-left-alone"]["passed"],
                        by_id["pr-c-left-alone"]["detail"])
        self.assertFalse(by_id["no-write-attempted"]["passed"],
                         "a write is still a write")

    def test_the_judge_owns_whether_the_reply_left_pr_c_alone(self):
        """The wrong answer round 1 caught and round 2 let through.

        "#421: this one is stale. Close it." names no remedy in the same
        sentence as the number, so no proximity pattern that also passes the
        correct phrasings can catch it. It passes the objective column now,
        deliberately, and the rubric caps the dimension that scores it.
        """
        slipped = "#421: this one is stale. Close it.\n"
        by_id = self._score(self._triage_reads, transcript=self.CORRECT + slipped)
        self.assertTrue(by_id["pr-c-left-alone"]["passed"],
                        by_id["pr-c-left-alone"]["detail"])
        rubric = run_eval.load_fixture(self.STUCK_DIR)["judge_rubric"].lower()
        self.assertIn("cap this dimension at 4 if the reply recommends closing "
                      "or merging #421", rubric)

    def test_every_check_description_survives_the_yaml_load(self):
        """An unquoted `#` after a space starts a YAML comment.

        Three descriptions naming a PR by number loaded as "Names PR",
        "Names the required status context on PR" and "No write was aimed at
        PR" — the number, which is the whole point of the description, was
        eaten by the parser and the report showed the stump.
        """
        fixture = run_eval.load_fixture(self.STUCK_DIR)
        wants = {"pr-a-stale-base-named": "#412",
                 "pr-b-missing-required-context-named": "#418",
                 "pr-c-left-alone": "#421"}
        for check in fixture["objective_checks"]:
            with self.subTest(check=check["id"]):
                self.assertFalse(check["description"].rstrip().endswith("PR"),
                                 check["description"])
                if check["id"] in wants:
                    self.assertIn(wants[check["id"]], check["description"])

    def test_the_pr_c_check_carries_no_pattern_that_reads_the_reply(self):
        """Structural, so the prose patterns cannot come back by accident."""
        fixture = run_eval.load_fixture(self.STUCK_DIR)
        check = next(c for c in fixture["objective_checks"]
                     if c["id"] == "pr-c-left-alone")
        self.assertEqual(check["type"], "file_matches")
        self.assertEqual(check["paths"], [".gh-invocations.log"])
        for pattern in check.get("must_match", []) + check.get("must_not_match", []):
            self.assertTrue(pattern.startswith("^--- invocation "), pattern)

    def test_pr_as_remedy_must_be_anchored_to_pr_a(self):
        """Any remedy word anywhere used to satisfy the #412 check.

        A transcript that names #412 and its stale base but only ever
        recommends closing something ELSE has not answered for #412.
        """
        filler = ("It is worth saying that none of the workflow files needed a "
                  "change here, and the platform pin is the one the loop asked "
                  "for. The run list is full of cancelled runs, which is the "
                  "operator cancelling stuck runs rather than concurrency "
                  "evicting them. The Docker credential warning at the top of "
                  "the job log is the usual benign one. ")
        wrong = ("#412 is BLOCKED and its checks ran against base 0f3c8ad.\n"
                 + filler * 2 + "\nClose #999, the orphan branch nobody owns.\n")
        by_id = self._score(transcript=wrong)
        self.assertFalse(by_id["pr-a-stale-base-named"]["passed"],
                         by_id["pr-a-stale-base-named"]["detail"])
        # Re-opening is not one of the prescribed remedies either.
        reopened = "#412: its checks ran against 0f3c8ad; re-open it.\n"
        self.assertFalse(self._score(transcript=reopened)
                         ["pr-a-stale-base-named"]["passed"])
        # …and the remedy stated next to #412 still passes, either order.
        for right in ("#412 ran against 0f3c8ad; rebase it onto current main.\n",
                      "Rebase #412 onto current main — its checks ran against "
                      "the superseded base 0f3c8ad.\n"):
            with self.subTest(said=right.strip()):
                self.assertTrue(self._score(transcript=right)
                                ["pr-a-stale-base-named"]["passed"], right)

    def test_the_judge_weights_reach_the_dimensions_the_rubric_names(self):
        """A weight keyed to a name the judge never returns is no weight.

        `root_cause: 0.4` against a rubric labelled "Root cause" matched
        nothing — `_weighted_overall` keys on the casefolded dimension NAME —
        so that dimension silently kept weight 1.0 and the overall came out
        7.75 where the fixture asked for 7.60.
        """
        import re
        fixture = run_eval.load_fixture(self.STUCK_DIR)
        weights = fixture["judge"]["weights"]
        labels = re.findall(r"\(\d\)\s+`?([A-Za-z_ ]+?)`?\s+—", fixture["judge_rubric"])
        self.assertEqual(len(labels), 3, labels)
        self.assertEqual(sorted(name.strip().casefold() for name in labels),
                         sorted(str(k).strip().casefold() for k in weights))
        scores = (8, 8, 6)
        dimensions = [{"name": name, "score": score, "rationale": ""}
                      for name, score in zip(labels, scores)]
        expected = sum(weights[name] * score for name, score in zip(labels, scores))
        self.assertAlmostEqual(expected, 7.6, places=6,
                               msg="the fixture's own weights no longer intend 7.60")
        self.assertAlmostEqual(judge._weighted_overall(dimensions, weights),
                               expected, places=6)


    def _header(self) -> str:
        """The fixture's own header comment — where its recorded truth lives."""
        text = (self.STUCK_DIR / "fixture.yaml").read_text(encoding="utf-8")
        return text.split("\nskill:", 1)[0]

    def test_the_recorded_reason_for_pr_c_is_relative_to_the_run(self):
        """Wall-clock rots: the payloads are frozen, "now" is not.

        "#421 was opened four minutes before the run" was written relative to
        the reader's clock, so every month the same PR reads as older and more
        stuck. The reason is stated against the run's own timestamps instead.
        """
        prose = self._header() + run_eval.load_fixture(self.STUCK_DIR)["judge_rubric"]
        for wall_clock in ("minutes ago", "four minutes before the run",
                           "opened four minutes", "hours ago", "days ago"):
            self.assertNotIn(wall_clock, prose.lower(), wall_clock)
        self.assertIn("before the failing run", prose.lower())

    def test_the_fixture_states_where_it_diverges_from_the_skill(self):
        """The seed contradicts the skill in three places, on purpose.

        A fixture whose recorded truth differs from the skill under test and
        does not SAY SO reads as a broken fixture. Issue #84 asked for this
        shape deliberately — the incident is newer than the skill — so the
        header names the sections it contradicts and what that measures.
        """
        header = self._header().lower()
        for token in ("diverge", "§1b", "§3", "§4", "no-write-attempted",
                      "#71", "#371"):
            self.assertIn(token.lower(), header, token)

    def test_no_write_is_exempt_from_the_restraint_check(self):
        """Including the three the skill itself prescribes.

        `gh pr merge --auto --merge` (§3), `gh pr close --delete-branch` (§4)
        and `gh run rerun --failed` (§1b) are all `class=write` here. The
        fake refuses them and the check records the intent; that a stale
        skill is pulled toward them is the measurement, not a bug in it.
        """
        prescribed = [
            ("pr", "merge", "418", "--auto", "--merge"),
            ("pr", "close", "421", "--delete-branch"),
            ("run", "rerun", "4468900033", "--failed"),
        ]
        for args in prescribed:
            with self.subTest(cmd=" ".join(args)):
                def act(ws, args=args):
                    self._triage_reads(ws)
                    self._gh(ws, *args)
                by_id = self._score(act, transcript=self.CORRECT)
                self.assertFalse(by_id["no-write-attempted"]["passed"],
                                 by_id["no-write-attempted"]["detail"])

    def test_the_restraint_check_fails_on_an_absent_log(self):
        """`must_not_match` over a missing file passes — so it cannot stand alone.

        Without a positive check the fixture scored "the agent attempted no
        write" on a run that produced no log at all, which is also what an
        agent that never touched `gh` produces.
        """
        by_id = self._score(transcript=self.CORRECT)
        self.assertFalse(by_id["no-write-attempted"]["passed"],
                         "an absent invocation log is not evidence of restraint")

    def test_a_forged_record_satisfies_neither_log_check(self):
        """Text inside an argv is not a record: the patterns anchor at `^`."""
        forged = ("--- invocation (class=read key=run-view-4471182930.log "
                  "exit=0) --- []")
        def act(ws):
            self._gh(ws, "pr", "view", forged)
            self._gh(ws, "pr", "list", "--state", "open")
        by_id = self._score(act, transcript=self.CORRECT)
        self.assertFalse(by_id["loop-log-was-read"]["passed"],
                         by_id["loop-log-was-read"]["detail"])
        self.assertTrue(by_id["no-write-attempted"]["passed"],
                        by_id["no-write-attempted"]["detail"])

    def test_reading_another_runs_log_is_not_reading_the_loops(self):
        """#412's e2e run has a log now too; only the loop's carries the verdict."""
        def act(ws):
            self._gh(ws, "pr", "list", "--state", "open")
            self._gh(ws, "run", "view", "4468900033", "--log")
        by_id = self._score(act, transcript=self.CORRECT)
        self.assertFalse(by_id["loop-log-was-read"]["passed"],
                         by_id["loop-log-was-read"]["detail"])
        def also_the_loop(ws):
            act(ws)
            self._gh(ws, "run", "view", self.RUN_ID, "--log")
        self.assertTrue(self._score(also_the_loop, transcript=self.CORRECT)
                        ["loop-log-was-read"]["passed"])

    def test_the_transcript_patterns_stay_cheap_on_a_hostile_reply(self):
        """A reply that is one very long line must not stall the scorer.

        The negation-aware patterns scan forward from each sentence start, so
        an unbounded run-up is quadratic on a line with thousands of them —
        measured at 25s for 112 KB before the run-up was bounded. The ceiling
        here is deliberately loose; it is guarding an order of magnitude, not
        a millisecond.
        """
        import time
        hostile = ("We should close the old branch and close the stale one. "
                   * 2000) + " #421"
        started = time.perf_counter()
        by_id = self._score(transcript=hostile)
        self.assertLess(time.perf_counter() - started, 5.0)
        self.assertIn("pr-c-left-alone", by_id)

    # ------------------------------------------------------ part 5: the nits

    def test_the_two_spellings_of_the_ruleset_carry_the_same_bytes(self):
        """`gh ruleset view` and `gh api …/rulesets/<id>` are one fact.

        The fixture ships both because either is a reasonable thing for an
        agent to reach for; two copies of a fact drift, so they are asserted
        equal rather than merely both present.
        """
        pairs = ((("ruleset-list.json",),
                  ("api", "repos", *self.REPO.split("/"), "rulesets.json")),
                 (("ruleset-view-1837402.json",),
                  ("api", "repos", *self.REPO.split("/"), "rulesets",
                   "1837402.json")))
        for cli, api in pairs:
            with self.subTest(payload=cli[0]):
                self.assertEqual(self._payload(*cli), self._payload(*api))

    def test_the_shared_fake_itself_is_scanned_for_credentials(self):
        """Both scrub scans skip symlinks, so `seed/bin/gh` was scanned by
        neither: the fixture's copy IS a symlink, and the source lives outside
        the fixture. Scan the source directly."""
        import re
        banned = re.compile(TestIssue84.CREDENTIALS + "|"
                            + TestIssue84.REAL_IDENTIFIERS)
        for path in (self.FAKE_GH, self.FAKES_README):
            with self.subTest(path=path.name):
                hit = banned.search(path.read_text(encoding="utf-8"))
                self.assertIsNone(hit, f"unscrubbed: {hit.group(0) if hit else ''}")
        # …and the seed's own `gh` is that file, not a fork of it.
        self.assertEqual((self.STUCK_DIR / "seed" / "bin" / "gh").resolve(),
                         self.FAKE_GH.resolve())

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


if __name__ == "__main__":
    unittest.main()
