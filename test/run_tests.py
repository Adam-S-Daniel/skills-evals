#!/usr/bin/env python3
"""Test suite for the skills-evals harness.

Hermetic: no real `claude` invocation (CLAUDE_BIN always points at
test/fake-claude), no network, no writes into the repo's real results/ dir.

Run: python3 test/run_tests.py
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import itertools
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
RENAME_DIR = REPO_ROOT / "evals" / "rename-pdfs"

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
            # Item 6 (#129 review round 4): the registry's basename, not its
            # full absolute path — this detail reaches summary.json, which
            # eval.yml commits to the public eval-results branch.
            self.assertIn(FAKE_REGISTRY.name, result["detail"])
            self.assertNotIn(str(FAKE_REGISTRY), result["detail"])
            # Names the plugins/*/skills/<skill> glob pattern that was searched.
            self.assertIn("skills", result["detail"])
            self.assertIn("plugins", result["detail"])

    def test_missing_skill_detail_does_not_leak_the_registry_absolute_path(self):
        """A registry checkout can live anywhere on the runner's disk —
        this proves the leak is closed for a path shape that does not
        happen to be the repo's own committed fixture path."""
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "some-private-runner-directory-name"
            registry.mkdir()
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            arm = {"name": "with_skill", "skill": "does-not-exist",
                  "registry": registry, "timeout": 30}
            result = run_eval.run_agent(workspace, "audit the workflows", arm)
            self.assertIn("error", result)
            self.assertIn(registry.name, result["detail"])
            self.assertNotIn(str(registry), result["detail"])


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
        # The roster's basename, not its full absolute path (item 5, #129
        # review round 3) — this detail reaches summary.json, which
        # eval.yml commits to the public eval-results branch.
        self.assertIn(missing.name, summary["error"]["detail"])
        self.assertNotIn(str(missing), summary["error"]["detail"])

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
        self.assertEqual(policy["min_ranked_turns"], 20)
        self.assertEqual(policy["min_ranked_share"], 0.01)
        self.assertEqual(roster.tier_rungs(policy),
                         [["haiku"], ["sonnet"], ["opus"], ["fable", "mythos"]],
                         "a rung may name peers that rank identically")
        self.assertIn("#73", raw, "roster-policy.yml must point at the ADR "
                                  "sub-issue until the ADR itself exists")
        roster.validate_policy(policy)  # the real policy file must validate

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
        # `$`, unlike `\Z`, matches just before a trailing newline — item 6
        # (#129 review round 3): an otherwise honest id with a trailing
        # newline used to be published as its own (distinct, newline-
        # carrying) key rather than falling to `other`.
        "trailing_newline": "claude-opus-5\n",
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
        self.assertIn("100.0% of rankable census usage", self._reason(result, "claude-sonnet-5"))

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
        self.assertIn("50.0% of rankable census usage", self._reason(result, "claude-sonnet-5"))

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

    def test_census_counts_that_are_not_actual_ints_are_dropped_not_coerced(self):
        """A census cell must be an actual `int` — not a numeral STRING, not
        `None`. (N2, #129 review round 5: `_clean_counts` used to run every
        cell through Python's `int()`, which coerces far more than a real
        JSON number ever needs — see `_clean_counts`'s own comment.) Every
        one of these weeks is dropped, and the run does not crash."""
        counts = {"claude-sonnet-5": {w: "100" for w in self.W[:4]},
                  "claude-opus-5": {w: None for w in self.W[:4]},
                  "claude-haiku-4-5": "not a mapping at all"}
        result, notes = self._warned(census_doc=self._census_doc(counts=counts))
        # Every cell is dropped, so the census reads as empty over the
        # window and every arm falls back to newest-per-tier — NOT to a
        # coerced "100.0%" usage share.
        reason = self._reason(result, "claude-sonnet-5")
        self.assertIn("fell back to newest per tier", reason)
        self.assertNotIn("100.0%", reason)
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
                   "registry": "https://github.com/Adam-S-Daniel/agentskills",
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
        # The roster's basename, not its full absolute path (item 5, #129
        # review round 3): this detail flows into summary.json, which
        # eval.yml commits to the public eval-results branch.
        self.assertIn(missing.name, summary["error"]["detail"],
                      "the error names the roster path it looked for")
        self.assertNotIn(str(missing), summary["error"]["detail"],
                         "the roster's absolute path must not reach a "
                         "public summary.json")
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
                # The roster's basename, not its full absolute path (item
                # 15, #129 review round 2; item 5, round 3): a selection
                # error naming the roster's ABSOLUTE path lands in
                # summary.json, which eval.yml commits to the public
                # eval-results branch. assertIn(path.name, ...) alone has
                # no teeth here — path.name is a substring of the full
                # path too — so the absolute path's absence is asserted
                # explicitly.
                self.assertIn(path.name, summary["error"]["detail"])
                self.assertNotIn(str(path), summary["error"]["detail"])
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
                    "--roster", str(path), "--results-dir", str(results),
                    "--registry", f"agentskills={tmp}"]

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

    def _run_roster_step(self, *, refresh_rc=0, git_shim=None,
                         roster_fail_stderr=None, roster_success_stderr=None):
        """Run eval.yml's roster step for real, against stubs.

        Hermetic: the two python scripts it calls are replaced by stubs, `git`
        by an optional shim, and there is no network and no credential. What is
        under test is the STEP — its failure handling — not the scripts.

        `roster_fail_stderr`, if given, makes the roster.py stub write that
        exact text to stderr and exit 1 (instead of succeeding) — for
        exercising the step's own reason-extraction and step-summary logic
        against a controlled roster.err. `roster_success_stderr`, if given
        (and `roster_fail_stderr` is not), makes the stub write that text to
        stderr but still SUCCEED (exit 0, write --out) — a stale/unreadable
        census or skipped bad rows can print `roster: ` warnings and still
        let the run succeed overall.

        SHARED with TestIssue67Review3 (assigned there rather than
        duplicated — see this file's per-review-round class convention:
        TestIssue67Review2 does the same). Same step, same stub shape; kept
        as one definition so a future change to the step's fixture only
        needs to happen once.
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
        if roster_fail_stderr is not None:
            roster_stub = (stub_args +
                           f"sys.stderr.write({roster_fail_stderr!r})\n"
                           f"sys.exit(1)\n")
        elif roster_success_stderr is not None:
            roster_stub = (stub_args +
                           f"sys.stderr.write({roster_success_stderr!r})\n"
                           "open(a.out, 'w').write('{}')\n"
                           "print('### Model roster')\n")
        else:
            roster_stub = (stub_args + "open(a.out, 'w').write('{}')\n"
                                       "print('### Model roster')\n")
        (tmp / "harness" / "roster.py").write_text(roster_stub, encoding="utf-8")
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
    _roster_file = TestIssue67Review._roster_file
    _write_transcript = staticmethod(TestIssue67Review._write_transcript)
    _assistant = TestIssue67Review._assistant

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
        self.assertTrue(any("not a usable count" in n for n in notes), notes)

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
        self.assertTrue(any("not a usable count" in n for n in notes), notes)

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

    # --- item 8: roster_models() drops malformed arm entries silently, and
    #             the judge-is-arm refusal was checked against an emptied set

    def test_roster_models_returns_a_skipped_count(self):
        arm_ids, judge_id, judge_is_arm, skipped = run_eval.roster_models(
            {"arms": [{"id": "claude-opus-5", "reason": "x"}, "not-a-dict",
                      {"reason": "no id"}],
             "judge": {"id": "claude-fable-5-1"}})
        self.assertEqual(arm_ids, ["claude-opus-5"])
        self.assertEqual(judge_id, "claude-fable-5-1")
        self.assertFalse(judge_is_arm)
        self.assertEqual(skipped, 2)

    def test_a_roster_whose_arms_all_fail_to_parse_is_a_selection_error_even_when_the_agent_is_pinned(self):
        """A fixture pinning `model:` but not `judge.model:` still reads the
        roster (for the judge) — and `{"arms": ["claude-opus-5"], "judge":
        {"id": "claude-opus-5", "is_arm": false}}` used to be ACCEPTED: the
        raw string arm entry is dropped silently, arm_ids comes back empty,
        and the judge-is-arm check (`judge_id in arm_ids`) is then checked
        against that emptied set — even though the roster's own arms list
        plainly names this exact judge id. A roster whose `arms` list is
        non-empty but yields zero usable ids cannot be trusted, regardless
        of whether this run even needed an arm from it."""
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = Path(tmp) / "evals" / "a-skill"
            (eval_dir / "seed").mkdir(parents=True)
            (eval_dir / "seed" / "README.md").write_text("seed\n", encoding="utf-8")
            fixture = {"skill": "a-skill", "prompt": "do the thing",
                      "judge_rubric": "grade it", "model": "claude-sonnet-4-6",
                      "arms": {"without_skill": {"install": "none"}}}
            (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture),
                                                    encoding="utf-8")
            document = {"arms": ["claude-opus-5"],
                       "judge": {"id": "claude-opus-5", "is_arm": False}}
            roster_path = self._roster_file(tmp, document)
            loaded_fixture = run_eval.load_fixture(eval_dir)
            args = argparse.Namespace(model=None, roster=roster_path, no_judge=False)
            agent, judge_model, error = run_eval.select_models(loaded_fixture, args)
        self.assertIsNotNone(error)
        self.assertIn(roster_path.name, error)

    # --- item 10: `compared_to_previous` collapses "unreadable previous"
    #              into "first run" — publish a third state -------------

    def test_previous_state_is_published_and_the_summary_reads_it_off_the_roster(self):
        """The JSON and the Markdown used to disagree by construction: main()
        derived render_summary's `previous_state` argument from
        `previous_problem` itself, while the roster dict only ever recorded
        `compared_to_previous: previous is not None` — collapsing "the
        previous roster was there but unreadable" into the same `False` as
        "there is no previous roster (first run)". Publishing the state in
        the roster means render_summary(roster), with no override, already
        agrees with what actually happened."""
        result = roster.compute_roster(
            models_doc=self._models_doc(), census_doc=self._census_doc(),
            policy=self._policy(), previous=None, now=self.NOW,
            previous_problem="previous.json is present but unreadable (JSONDecodeError)")
        self.assertEqual(result["previous_state"], "unavailable")
        text = roster.render_summary(result)
        self.assertIn("roster inputs unavailable", text.lower())
        self.assertNotIn("No change to the arm set", text)
        self.assertNotIn("First published roster here", text)

    def test_previous_state_distinguishes_none_from_compared(self):
        first_run = roster.compute_roster(
            models_doc=self._models_doc(), census_doc=self._census_doc(),
            policy=self._policy(), previous=None, now=self.NOW)
        self.assertEqual(first_run["previous_state"], "none")
        self.assertFalse(first_run["compared_to_previous"])

        previous = {"arms": [{"id": i} for i in self._arm_ids(self._compute())]}
        compared = roster.compute_roster(
            models_doc=self._models_doc(), census_doc=self._census_doc(),
            policy=self._policy(), previous=previous, now=self.NOW)
        self.assertEqual(compared["previous_state"], "compared")
        self.assertTrue(compared["compared_to_previous"])

    # --- item 11: a fixture pinning neither model nor judge is told only
    #              about the model pin -------------------------------------

    def test_a_fixture_pinning_neither_model_nor_judge_is_told_about_both(self):
        fixture = {"skill": "a-skill", "prompt": "x", "judge_rubric": "y"}
        args = argparse.Namespace(model=None,
                                  roster=Path("/nonexistent/roster.json"),
                                  no_judge=False)
        agent, judge_model, error = run_eval.select_models(fixture, args)
        self.assertIsNotNone(error)
        self.assertIn("model", error)
        self.assertIn("judge model", error)

    # --- item 12: the fixture's own precedence comment still says the old,
    #              fall-through-to-CLI-default contract -------------------

    def test_workflow_path_audit_fixture_describes_the_fail_closed_precedence(self):
        text = (REPO_ROOT / "evals" / "workflow-path-audit" / "fixture.yaml").read_text(
            encoding="utf-8")
        self.assertNotIn("the CLI's own default", text,
                         "select_models() fails closed; nothing falls through "
                         "to a CLI default any more")

    # --- item 13: model_usage_census.py's docstring overstates what `other`
    #              buys — usage_share drops it from BOTH sides -----------

    def test_census_docstring_does_not_overstate_the_other_bucket_contract(self):
        text = (REPO_ROOT / "scripts" / "model_usage_census.py").read_text(
            encoding="utf-8")
        self.assertNotIn("the totals the roster divides by stay truthful", text,
                         "usage_share excludes `other` (and any unranked id) "
                         "from what it divides by entirely — routing its "
                         "counts under `other` keeps this script's own turn "
                         "count honest, it does not feed the roster's share "
                         "math at all")

    # --- item 14: _run_arm materialized the workspace before checking
    #              whether the run can even proceed ------------------------

    def test_run_arm_checks_selection_error_before_materializing_the_workspace(self):
        """A model-selection error means the agent never runs; mkdtemp +
        copytree + a git init/add/commit for a workspace that gets
        `shutil.rmtree`'d one line later was pure waste on every unpinned
        fixture that hits a missing or broken roster."""
        with tempfile.TemporaryDirectory() as tmp:
            eval_dir = Path(tmp) / "evals" / "a-skill"
            (eval_dir / "seed").mkdir(parents=True)
            (eval_dir / "seed" / "README.md").write_text("seed\n", encoding="utf-8")
            fixture_doc = {"skill": "a-skill", "prompt": "do the thing",
                           "judge_rubric": "grade it",
                           "arms": {"without_skill": {"install": "none"}}}
            (eval_dir / "fixture.yaml").write_text(yaml.safe_dump(fixture_doc),
                                                    encoding="utf-8")
            fixture = run_eval.load_fixture(eval_dir)
            results_dir = Path(tempfile.mkdtemp())
            self.addCleanup(shutil.rmtree, results_dir, ignore_errors=True)
            args = argparse.Namespace(model=None, timeout=30, no_judge=False,
                                      results_dir=results_dir,
                                      roster=Path(tmp) / "nope.json")
            with mock.patch.object(run_eval.tempfile, "mkdtemp") as fake_mkdtemp:
                summary = run_eval._run_arm(
                    "without_skill", fixture, eval_dir / "seed",
                    Path("/nonexistent-registry"), args, "20260904T120000Z")
        self.assertIsNotNone(summary["error"])
        fake_mkdtemp.assert_not_called()

    # --- item 16: select_models' docstring says a pinned fixture never
    #              needs the roster — true only when it pins BOTH ----------

    def test_select_models_docstring_says_a_fixture_must_pin_both_to_skip_the_roster(self):
        doc = run_eval.select_models.__doc__
        self.assertNotIn("A PINNED fixture never needs the roster", doc,
                         "a fixture pinning only `model:` (not `judge.model:`) "
                         "still reads the roster for the judge")
        self.assertIn("both", doc.lower())

    # --- item 17: seen_turns resets per transcript, so the SAME file
    #              reachable twice in the walk (a symlink, a hard-linked
    #              copy) double-counts every turn in it -------------------

    def test_a_duplicate_or_symlinked_transcript_is_not_double_counted(self):
        """The same underlying file reachable via two paths must count once.
        This is deliberately NOT the same thing test_dedupe_is_per_transcript
        _not_global guards: that test has two genuinely DIFFERENT files
        (different inodes) that happen to share a message id, and both must
        still count — dedup here is by FILE IDENTITY, never by turn id
        across distinct files."""
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            original = self._write_transcript(
                projects / "-x" / "a.jsonl",
                [self._assistant("claude-opus-5", "2026-09-03T10:00:00Z",
                                 message_extra={"id": "msg_01ONLY"})],
                mtime=self.NOW)
            duplicate = projects / "-x" / "b.jsonl"
            os.link(original, duplicate)
            counts = model_usage_census.census_counts(projects, now=self.NOW, weeks=8)
        self.assertEqual(counts, {"claude-opus-5": {"2026-W36": 1}})

    # --- item 19: eval.yml's two reason extractors disagree (tail vs head),
    #              and grep -v '^roster: ' discards the diagnosis itself ---

    def test_roster_failure_reason_is_the_last_line_not_the_traceback_header(self):
        """`head -n 1` on roster.err — even filtered through `grep -v
        '^roster: '` — picks 'Traceback (most recent call last):' on an
        uncaught exception: the single least useful line a traceback has.
        The last line is the exception message."""
        stderr = ("roster: census.json is present but unreadable (JSONDecodeError)\n"
                  "Traceback (most recent call last):\n"
                  '  File "harness/roster.py", line 1, in <module>\n'
                  "ValueError: something roster.py did not expect\n")
        got = self._run_roster_step(roster_fail_stderr=stderr)
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertIn("::warning::", got["out"])
        self.assertIn("ValueError: something roster.py did not expect",
                      got["out"])
        self.assertNotIn("Traceback (most recent call last):",
                         [ln for ln in got["out"].splitlines()
                          if ln.startswith("::warning::")][0])

    def test_roster_warnings_are_carried_into_the_step_summary(self):
        """The `roster: `-prefixed warn() lines used to be filtered OUT of
        the reason candidates and never appeared anywhere but the raw job
        log — the step summary (the UI surface most people actually read)
        never showed the diagnosis at all on a failure."""
        stderr = ("roster: census.json is present but unreadable (JSONDecodeError)\n"
                  "refusing to publish a roster with no arms: every ranked "
                  "model is excluded\n")
        got = self._run_roster_step(roster_fail_stderr=stderr)
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertIn("census.json is present but unreadable", got["summary"])

    # --- item 20: _version_key uses isdigit(), which int() does not agree
    #              with for every character isdigit() accepts ------------

    def test_version_key_does_not_crash_on_a_non_ascii_digit_token(self):
        """`'²'.isdigit()` (superscript two) is True, but
        `int('²')` raises ValueError — `isdigit()` and `int()` do not
        agree on what counts as a digit."""
        result = roster._version_key("claude-sonnet-²")
        self.assertEqual(result, ((0, 0, "claude"), (0, 0, "sonnet"),
                                  (0, 0, "²")))

    # --- item 21: roster.py imports window_start but never uses it, hidden
    #              behind a line-wide `# noqa: F401` -----------------------

    def test_roster_does_not_import_the_unused_window_start(self):
        """`iso_week` is legitimately unused BY roster.py's own logic — it is
        re-exported so `test_roster_and_census_share_one_week_implementation`
        can check identity with timeweeks.iso_week — but `window_start` has
        no such reason and roster.py never calls it at all."""
        self.assertFalse(hasattr(roster, "window_start"),
                         "window_start is dead weight in roster.py's import")
        self.assertTrue(hasattr(roster, "iso_week"),
                        "iso_week stays: it is deliberately re-exported")

    # --- item 22: roster-policy.yml's comment says a model's tier is "the
    #              first word to appear in its id" — rung_of returns the
    #              LOWEST matching rung, not positional order -------------

    def test_roster_policy_comment_matches_rung_of_lowest_rung_behavior(self):
        text = self.POLICY.read_text(encoding="utf-8")
        self.assertNotIn("the first of these words to appear", text,
                         "rung_of() returns the WEAKEST matching rung, "
                         "walking the ladder top-down — not the first word "
                         "to appear positionally in the id")
        # And the code the comment describes actually does that:
        rungs = roster.tier_rungs(self._policy())
        self.assertEqual(roster.rung_of("claude-opus-haiku-5", rungs),
                         roster.rung_of("claude-haiku-5", rungs),
                         "an id carrying both an opus and a haiku token "
                         "ranks by the weaker rung, regardless of which "
                         "word appears first in the id string")


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
                              "model": "claude-haiku-4-5",
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
        self.assertIn("--registry flag", msg)
        # The resolved absolute PATH must not reach the message (item 6,
        # #129 review round 4's treatment of this same class of detail,
        # applied here too — N6, round 5): only the registry's name and
        # override source.
        self.assertNotIn(str(bad_path), msg)
        self.assertNotIn("does-not-exist-anywhere", msg)

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
            fixture = {"skill": "some-skill", "model": "claude-haiku-4-5",
                      "prompt": "do the thing"}
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
                "model": "claude-haiku-4-5",
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
            fixture = {"skill": "some-skill", "registry": None,
                      "model": "claude-haiku-4-5", "prompt": "do the thing"}
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
                "model": "claude-haiku-4-5",
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
            # Item 6 (#129 review round 4): the registry's NAME and layout,
            # not its resolved absolute path — this detail reaches
            # summary.json, which eval.yml commits to the public
            # eval-results branch.
            expected_path = str((tmp_root / "scratch-registry").resolve())
            self.assertIn("scratch-registry", with_skill_summary["error"]["detail"])
            self.assertNotIn(expected_path, with_skill_summary["error"]["detail"])

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
            # The skill name, not the destination's absolute workspace path
            # (S5, #129 review round 5) — this detail reaches summary.json,
            # which eval.yml commits to the public eval-results branch.
            # Generic wording (N1, #129 review round 6): "already exists"
            # would be false for the NotADirectoryError case below, which
            # shares this same message.
            self.assertIn("could not install some-skill/ into the seed workspace",
                          result["detail"])
            self.assertIn("FileExistsError", result["detail"])
            self.assertNotIn(str(workspace), result["detail"])

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
            # N1 (#129 review round 6): "already exists" is FALSE for this
            # case — `.claude/skills` is a file, not an existing directory
            # — so the detail must not claim it.
            self.assertIn("could not install some-skill/ into the seed workspace",
                          result2["detail"])
            self.assertNotIn("already exists", result2["detail"])
            self.assertIn("NotADirectoryError", result2["detail"])
            self.assertNotIn(str(workspace2), result2["detail"])

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


class TestIssue67Review3(unittest.TestCase):
    """Round 3 fixes for #67, one test per fix. See run_tests.py's
    class-per-review-round convention (TestIssue67Review, TestIssue67Review2)."""

    WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"
    POLICY = REPO_ROOT / "evals" / "roster-policy.yml"

    # --- shared with TestIssue67Review: same step, same stub shape, one
    # definition (item 9, #129 review round 4 — this file's existing
    # per-review-round class convention already does this for
    # TestIssue67Review2; a duplicate copy here just drifted from it once).
    # NOT class inheritance: inheriting TestIssue67Review's TestCase would
    # re-collect and re-run its whole test suite here too.

    def _steps(self):
        doc = yaml.safe_load(self.WORKFLOW.read_text(encoding="utf-8"))
        return doc["jobs"]["eval"]["steps"]

    def _step_named(self, needle):
        return next(s for s in self._steps()
                    if needle.lower() in (s.get("name") or "").lower())

    _run_roster_step = TestIssue67Review._run_roster_step

    # --- item 2: the roster-failure reason extractor must prefer the
    # no-arms headline over an indented per-model detail line ------------

    def test_roster_failure_reason_prefers_the_no_arms_headline_over_a_model_detail_line(self):
        """roster.py's fatal "refusing to publish a roster with no arms" path
        prints the headline FIRST, then one indented "  <id>: <reason>" line
        per excluded/unranked model — production-shaped, built by actually
        running roster.py on a no-arms input (every ranked model inside the
        cooling-off), not hand-written. The old `tail -n 1` extractor picked
        the LAST line — a model's detail, not the headline — and the comment
        claimed otherwise.
        """
        with tempfile.TemporaryDirectory() as tmp:
            models = Path(tmp) / "models.json"
            models.write_text(json.dumps({
                "fetched_at": "2026-09-04T11:00:00Z",
                "models": [TestIssue67._model("claude-haiku-9",
                                              "2026-09-02T00:00:00Z")],
            }), encoding="utf-8")
            out = Path(tmp) / "roster" / "latest.json"
            proc = subprocess.run(
                [sys.executable, str(HARNESS_DIR / "roster.py"),
                 "--models", str(models), "--policy", str(self.POLICY),
                 "--out", str(out)],
                capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("refusing to publish a roster with no arms", proc.stderr)
        self.assertTrue(
            any(ln.startswith("  ") for ln in proc.stderr.splitlines()),
            "fixture must carry at least one indented per-model detail line "
            "— the production shape the old extractor got wrong")

        got = self._run_roster_step(roster_fail_stderr=proc.stderr)
        self.assertEqual(got["rc"], 0, got["out"])
        warning_line = next(ln for ln in got["out"].splitlines()
                            if ln.startswith("::warning::"))
        self.assertIn("refusing to publish a roster with no arms", warning_line)
        self.assertNotIn("claude-haiku-9:", warning_line,
                         "the per-model detail line leaked into the warning "
                         "instead of the headline")
        self.assertIn("refusing to publish a roster with no arms",
                      got["summary"])

    # --- item 7: the roster-warnings <details> block must render on the
    # success path too, not only on failure -----------------------------

    def test_roster_warnings_reach_the_step_summary_on_the_success_path_too(self):
        """A stale/unreadable census or skipped bad rows can print
        `roster: `-prefixed warnings and still let the roster refresh
        succeed overall. The <details> block used to render only in the
        failure branch, so these warnings reached the raw job log but
        never the step summary on a run that otherwise succeeded.
        """
        got = self._run_roster_step(
            roster_success_stderr="roster: census.json is present but "
                                  "unreadable (JSONDecodeError)\n")
        self.assertEqual(got["rc"], 0, got["out"])
        self.assertIn("roster warnings", got["summary"])
        self.assertIn("census.json is present but unreadable", got["summary"])

    # --- item 3: a proxy alias carrying a family word (`claude-sonnet-
    # proxy-route`) is `rung_of()`-ranked but not a catalogue model or a
    # previous arm — its usage must not count as "usage this policy can
    # rank" ------------------------------------------------------------

    def test_proxy_alias_census_holds_previous_arms_not_credits_them(self):
        """A census whose in-window usage is entirely a proxy alias that
        merely carries a family word (not a real catalogue id, measured
        end to end through the real census) used to be read as usable
        evidence — rung_of() ranks it — crediting its usage to nobody's
        numerator while still inflating every real arm's denominator, and
        letting an otherwise-unattributable census retire a previous arm at
        0.0%. This is the same failure round 2 closed for an entirely-
        `other` census (test_census_entirely_unrankable_is_held_not_read_as
        _usable), by a second route.
        """
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        counts = {"claude-sonnet-proxy-route":
                  {w: 500 for w in TestIssue67.W[:4]}}
        result = TestIssue67._compute(
            census=TestIssue67._census_doc(counts=counts), previous=previous)
        self.assertIn("claude-opus-4-8", TestIssue67._arm_ids(result),
                      "a census with no attributable usage is not evidence "
                      "to retire a previous arm")
        reason = TestIssue67._reason(result, "claude-opus-4-8")
        self.assertIn("no evidence to retire it", reason)
        self.assertIn("no usage this policy can rank", reason)
        self.assertEqual(result["retired_since_last"], [])

    def test_real_id_census_still_computes_shares(self):
        """The new attribution filter changes nothing when every census key
        really is a catalogue id — the ordinary case must not regress."""
        rungs = roster.tier_rungs(TestIssue67._policy())
        cleaned = roster._clean_counts(
            {"claude-opus-5": {TestIssue67.W[0]: 250},
             "claude-sonnet-5": {TestIssue67.W[0]: 250}}, lambda _m: None)
        share = roster.usage_share(
            cleaned, "claude-opus-5", TestIssue67.W[:1], rungs,
            api_ids={"claude-opus-5", "claude-sonnet-5"}, previous_arms=set())
        self.assertEqual(share, 50.0)

    def test_mixed_census_computes_share_against_real_ids_only(self):
        """One real id at 60 turns and one alias at 1000 turns: the real
        id's share is computed against real ids only — the alias's usage
        must not inflate the denominator."""
        rungs = roster.tier_rungs(TestIssue67._policy())
        cleaned = roster._clean_counts(
            {"claude-opus-5": {TestIssue67.W[0]: 60},
             "claude-sonnet-proxy-route": {TestIssue67.W[0]: 1000}},
            lambda _m: None)
        share = roster.usage_share(
            cleaned, "claude-opus-5", TestIssue67.W[:1], rungs,
            api_ids={"claude-opus-5"}, previous_arms=set())
        self.assertEqual(share, 100.0,
                         "the alias's 1000 turns must not inflate the "
                         "denominator for a real id's share")

    # --- item 4: _clean_counts bounds a cell above zero, and usage_share
    # stays safe even when a huge value gets past it anyway -------------

    def test_clean_counts_rejects_a_cell_above_the_weekly_turn_ceiling(self):
        """A week cannot hold more turns than roster.MAX_WEEKLY_TURNS. A
        cell of `1e308` (a huge but finite float) or a several-hundred-
        digit JSON integer both pass a bare `int()` cleanly — Python ints
        are arbitrary precision — and used to ride straight into
        usage_share's arithmetic."""
        notes = []
        huge_int = int("9" * 400)
        cleaned = roster._clean_counts(
            {"claude-opus-5": {"2026-W36": 1e308, "2026-W35": huge_int,
                               "2026-W34": 50}}, notes.append)
        self.assertEqual(cleaned, {"claude-opus-5": {"2026-W34": 50}})
        self.assertTrue(any("not a usable count" in n for n in notes), notes)

    def test_usage_share_does_not_overflow_on_a_huge_count(self):
        """usage_share is called directly by other tests on hand-built
        counts that bypass _clean_counts's own upper bound, so it must stay
        safe on its own: `100.0 * mine` converts a huge `mine` to a float
        BEFORE dividing, which either overflows to `inf` (a `1e308`-sized
        int, published as "carries inf% of census usage") or raises
        OverflowError outright (a several-hundred-digit int)."""
        rungs = roster.tier_rungs(TestIssue67._policy())
        huge = int(1e308)
        cleaned = {"claude-opus-5": {TestIssue67.W[0]: huge},
                  "claude-sonnet-5": {TestIssue67.W[0]: huge}}
        share = roster.usage_share(
            cleaned, "claude-opus-5", TestIssue67.W[:1], rungs,
            api_ids={"claude-opus-5", "claude-sonnet-5"}, previous_arms=set())
        self.assertEqual(share, 50.0)

        way_huge = int("9" * 400)
        cleaned = {"claude-opus-5": {TestIssue67.W[0]: way_huge},
                  "claude-sonnet-5": {TestIssue67.W[0]: way_huge}}
        share = roster.usage_share(
            cleaned, "claude-opus-5", TestIssue67.W[:1], rungs,
            api_ids={"claude-opus-5", "claude-sonnet-5"}, previous_arms=set())
        self.assertEqual(share, 50.0)

    # --- item 1: model_usage_census.py must not need PyYAML just to import
    # or to fail an argument, only to actually build a census ---

    def test_missing_pyyaml_is_a_named_exit_2_not_a_traceback(self):
        """model_usage_census.py used to `import roster` (for `tier_words`)
        and build MODEL_ID_RE at IMPORT TIME, so a machine with no PyYAML
        installed died with a bare ImportError before argparse ever ran —
        before even `--help` worked. The roster import is now lazy
        (`_require_model_id_re()`), and main() turns a missing PyYAML into
        one named line on stderr and exit 2, never a traceback.
        """
        import model_usage_census
        saved = {name: sys.modules.get(name) for name in ("yaml", "roster")}
        saved_re = model_usage_census.MODEL_ID_RE
        for name in ("yaml", "roster"):
            sys.modules.pop(name, None)
        sys.modules["yaml"] = None  # the standard "this module is not installed" shim
        model_usage_census.MODEL_ID_RE = None  # force a fresh (failing) resolve
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "usage.json"
                argv = ["model_usage_census.py", "--out", str(out)]
                err = io.StringIO()
                with mock.patch.object(sys, "argv", argv), \
                     contextlib.redirect_stderr(err), \
                     contextlib.redirect_stdout(io.StringIO()):
                    rc = model_usage_census.main()
                self.assertFalse(out.exists())
        finally:
            for name, mod in saved.items():
                if mod is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = mod
            model_usage_census.MODEL_ID_RE = saved_re
        self.assertEqual(rc, 2)
        self.assertIn(model_usage_census.PYYAML_MISSING_MESSAGE, err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())


class TestIssue67Review4(unittest.TestCase):
    """Round 4 fixes for #67, one test per fix. See run_tests.py's
    class-per-review-round convention (TestIssue67Review, TestIssue67Review2,
    TestIssue67Review3) — a SIBLING of TestIssue67, reusing its canned
    documents rather than subclassing."""

    NOW = TestIssue67.NOW
    W = TestIssue67.W
    POLICY = TestIssue67.POLICY

    @classmethod
    def _policy(cls):
        return TestIssue67._policy()

    @classmethod
    def _compute(cls, models=TestIssue67.DEFAULT, census=TestIssue67.DEFAULT,
                 previous=None):
        return TestIssue67._compute(models=models, census=census, previous=previous)

    _arm_ids = staticmethod(TestIssue67._arm_ids)
    _reason = staticmethod(TestIssue67._reason)
    _model = staticmethod(TestIssue67._model)

    # --- item 1: `_is_attributable` must attribute a candidate whose RAW
    # (unfolded) spelling is itself an api id, or whose folded spelling
    # matches an api id folded through the SAME alias map — not only a
    # candidate whose folded spelling is a bare (unfolded) api id. -------

    def test_dated_only_catalogue_with_usage_under_the_undated_alias_is_attributed(self):
        """(a) The Models API publishes only the dated snapshot id; the
        census recorded most usage under that exact id but a handful of
        turns under the bare (undated) alias — a shape roster-policy.yml
        and alias_map's own docstring call legitimate. The OLD
        `_is_attributable` folded the DATED candidate onto its undated
        alias and found neither spelling in `api_ids` (the alias itself
        is not a catalogue id), so all 2000 of its turns read as
        unattributable and the census read as CENSUS_UNRANKED. Measured
        against fc5de5c the same input gave 100% for this model; this is
        the regression floor.
        """
        models_solo = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-sonnet-4-9-20260101", "2026-06-01T00:00:00Z"),
        ]}
        counts_solo = {"claude-sonnet-4-9-20260101": {w: 500 for w in self.W[:4]},
                       "claude-sonnet-4-9": {self.W[0]: 4}}

        rungs = roster.tier_rungs(self._policy())
        cleaned = roster._clean_counts(counts_solo, lambda _m: None)
        aliases = roster.alias_map(["claude-sonnet-4-9-20260101"] + list(cleaned))
        raw_total, ranked_total = roster._in_window_totals(
            cleaned, set(self.W[:4]), rungs, aliases=aliases,
            api_ids={"claude-sonnet-4-9-20260101"}, previous_arms=set())
        self.assertEqual(raw_total, 2004)
        self.assertEqual(ranked_total, 2004,
                         "the dated id's own 2000 turns must count as "
                         "ranked, attributable usage")

        # A second, ordinary model in the mix (its own id published and
        # attributed with no aliasing involved at all) is what turns the
        # dated model's own combined 2004 turns into a measured SHARE
        # rather than the trivial 100% of a one-model universe.
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-sonnet-4-9-20260101", "2026-06-01T00:00:00Z"),
            self._model("claude-haiku-4-9", "2026-06-01T00:00:00Z"),
        ]}
        counts = dict(counts_solo, **{"claude-haiku-4-9": {self.W[0]: 4}})
        census = TestIssue67._census_doc(counts=counts)

        result = self._compute(models=models, census=census, previous=None)
        self.assertIn("claude-sonnet-4-9-20260101", self._arm_ids(result))
        reason = self._reason(result, "claude-sonnet-4-9-20260101")
        self.assertIn("99.8%", reason)
        self.assertNotIn("no fresh census", reason.lower())

    def test_mixed_dated_and_undated_ids_do_not_give_a_false_100_percent(self):
        """(b) A mixed catalogue: one family published dated-only while its
        census usage is recorded under the undated alias (the same shape as
        (a)), alongside a second family whose census key matches its api id
        exactly. Under the old code the first family's usage was excluded
        (unattributable) while the second's was not, so the second family's
        tiny usage read as ALL the rankable census."""
        rungs = roster.tier_rungs(self._policy())
        counts_raw = {"claude-sonnet-4-9": {self.W[0]: 100000},
                      "claude-haiku-4-9-20251001": {self.W[0]: 5}}
        cleaned = roster._clean_counts(counts_raw, lambda _m: None)
        api_ids = {"claude-sonnet-4-9-20260101", "claude-haiku-4-9-20251001"}
        aliases = roster.alias_map(list(api_ids) + list(cleaned))
        share = roster.usage_share(
            cleaned, "claude-haiku-4-9-20251001", self.W[:1], rungs,
            aliases, api_ids=api_ids, previous_arms=set())
        self.assertLess(share, 1.0,
                        "sonnet's 100000 turns under its undated alias must "
                        "count toward the denominator; haiku's 5 turns must "
                        "not read as the entire rankable census")

    def test_a_heavily_used_dated_previous_arm_is_not_retired_at_zero_percent(self):
        """(b), continued: end to end through compute_roster. A previous
        arm published only under a dated id, whose census usage is
        recorded under its undated alias, carries real usage and must not
        be retired at a false 0.0% — nor should it lose its seat to a
        newer same-tier model it is genuinely outperforming."""
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-sonnet-4-9-20260101", "2026-01-01T00:00:00Z"),
            self._model("claude-sonnet-4-10-20260201", "2026-02-01T00:00:00Z"),
            self._model("claude-haiku-4-9-20251001", "2025-10-01T00:00:00Z"),
        ]}
        counts = {"claude-sonnet-4-9": {self.W[0]: 100000},
                  "claude-haiku-4-9-20251001": {self.W[0]: 5}}
        census = TestIssue67._census_doc(counts=counts)
        previous = {"arms": [{"id": "claude-sonnet-4-9-20260101",
                              "reason": "was an arm"}]}
        result = self._compute(models=models, census=census, previous=previous)
        retired = {r["id"]: r["reason"] for r in result["retired_since_last"]}
        self.assertNotIn("claude-sonnet-4-9-20260101", retired,
                         f"a model carrying ~100000 turns under its own "
                         f"alias must not be retired: {retired}")
        # S3 (#129 review round 5): this test passed even before item 1's
        # fix existed, rescued by the `min_ranked_turns` floor's "no
        # evidence to retire it" bailout rather than by a genuine usage
        # measurement — the floor's own reason names "floor", never
        # "rankable census usage". Pin the ARM's actual reason so a
        # regression that breaks the real attribution path but leaves the
        # floor rescuing it by coincidence still shows red here.
        reason = self._reason(result, "claude-sonnet-4-9-20260101")
        self.assertIn("rankable census usage", reason)
        self.assertNotIn("floor", reason)

    def test_proxy_and_implausible_aliases_stay_unattributable(self):
        """Every shape a proxy/routing layer — or a plausible-looking fake
        version that was never a real catalogue id — can carry: `rung_of()`
        ranks all of these (a recognised family word is present), yet none
        is a real catalogue id or a previous arm under any spelling, and
        none was ever in `catalogue_seen` either (it is built only from
        real Models API responses). Regression floor for round 3's
        proxy-alias fix, and for round 5's withdrawal of the canonical-
        shape route: the last three entries are exactly the three holes
        that route shipped with (see `_is_attributable`'s docstring) —
        a Unicode decimal digit in the version segment, a plausible but
        entirely invented version number, and a region-suffixed alias.
        (Consolidates what were two near-duplicate tests, N7 — one for a
        bare `api_ids`/`previous_arms` and one adding `previous_arms`; both
        asserted the identical `ranked_total == 0` outcome.)
        """
        rungs = roster.tier_rungs(self._policy())
        for alias in ("proxy-router-claude-sonnet-4-5", "claude-sonnet-proxy-route",
                      "claude-sonnet-9-9", "claude-opus-٤", "claude-opus-4-eu"):
            cleaned = roster._clean_counts(
                {alias: {self.W[0]: 500}}, lambda _m: None)
            api_ids = {"claude-opus-4-8"}
            previous_arms = {"claude-opus-4-8"}
            aliases = roster.alias_map(list(api_ids) + list(cleaned))
            raw_total, ranked_total = roster._in_window_totals(
                cleaned, set(self.W[:1]), rungs, aliases=aliases,
                api_ids=api_ids, previous_arms=previous_arms)
            self.assertEqual(ranked_total, 0, alias)

    # --- item 1 (design decision, #129 review round 5): a since-retired
    # real model id must still count in the usage denominator — attribution
    # by catalogue HISTORY (`catalogue_seen`), not id SHAPE. A proxy alias
    # must not gain a seat just because it carries a family word. ---------

    def test_a_since_retired_real_model_still_counts_via_catalogue_seen(self):
        """`claude-opus-4-8` leaves the Models API and was never a previous
        arm. Its 1000-turns/week usage is real work that happened, and
        DESIGN.md's own property says it belongs in the denominator. Round
        4 attributed it by id SHAPE (`_canonical_id_re`, withdrawn in round
        5 for the reasons in `_is_attributable`'s docstring); the
        replacement is catalogue HISTORY — a previous run's published
        roster recorded seeing `claude-opus-4-8` in the Models API, so it
        rides in `catalogue_seen` this run even with no census usage of its
        own and no seat. Without either mechanism, item 1 alone still
        excludes it (neither a bare/folded api id nor a previous arm),
        starving the denominator down to `claude-sonnet-4-6`'s own usage
        and inflating its measured share from ~5.66% (correctly below the
        10% entry bar) to a false 100%, seating it as a paid arm on no real
        evidence.
        """
        rungs = roster.tier_rungs(self._policy())
        counts = {"claude-sonnet-4-6": {w: 60 for w in self.W},
                  "claude-opus-4-8": {w: 1000 for w in self.W}}
        cleaned = roster._clean_counts(counts, lambda _m: None)
        api_ids = {"claude-sonnet-4-6"}  # opus-4-8 dropped from the catalogue
        catalogue_seen = {"claude-sonnet-4-6", "claude-opus-4-8"}
        aliases = roster.alias_map(list(api_ids) + list(cleaned))
        share = roster.usage_share(
            cleaned, "claude-sonnet-4-6", self.W[:4], rungs, aliases,
            api_ids=api_ids, previous_arms=set(), catalogue_seen=catalogue_seen)
        self.assertAlmostEqual(share, 100 * 240 / 4240, places=6)
        self.assertLess(share, 10.0,
                        "below the 10% entry bar — opus-4-8's usage must "
                        "still be in the denominator")

        # End to end: `claude-sonnet-5` (the DEFAULT fixture's newer sonnet)
        # stays in the catalogue so `claude-sonnet-4-6` is NOT the newest in
        # its tier — its only possible route to a seat is the usage share
        # above, which must legitimately fail, so the assertion below is
        # unconditional (N5, #129 review round 5 — the round 4 version of
        # this test only checked the reason's wording IF the model ended up
        # seated, which a regression could dodge simply by also breaking
        # the newest-in-tier fallback in a way that happened to keep this
        # model out of `arms`).
        models = TestIssue67._models_doc(drop={"claude-opus-4-8"})
        census = TestIssue67._census_doc(counts=counts)
        previous = {"arms": [], "catalogue_seen": ["claude-opus-4-8"]}
        result = self._compute(models=models, census=census, previous=previous)
        self.assertNotIn("claude-sonnet-4-6", self._arm_ids(result),
                         "opus-4-8's usage must count in the denominator, "
                         "keeping sonnet-4-6's share below the entry bar "
                         "rather than seating it at a false 100%")

    # --- item 3: CENSUS_UNRANKED's published reason must name the
    # unattributable cause too, not only "the tier ladder cannot place" ---

    def test_census_unranked_reason_names_the_unattributable_cause_too(self):
        """For a census whose only in-window usage is a proxy alias, the
        ladder DID place it (`rung_of` ranks it) — `_is_attributable`
        excludes it, a different fact entirely. The old CENSUS_UNRANKED
        wording named only `other` and 'an id the tier ladder cannot
        place', which is false for this case and does not name the real
        cause."""
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        counts = {"claude-sonnet-proxy-route": {w: 500 for w in self.W[:4]}}
        result = self._compute(census=TestIssue67._census_doc(counts=counts),
                               previous=previous)
        reason = self._reason(result, "claude-opus-4-8")
        self.assertIn("no evidence to retire it", reason)
        self.assertIn("neither the Models API nor the previous roster "
                      "attributes", reason)

    # --- item 4 (nit): every share-percentage reason must say "of
    # rankable census usage" — the denominator is ranked, attributable
    # usage, not literally everything the census recorded -----------------

    def test_share_reasons_say_rankable_census_usage_not_census_usage(self):
        result = self._compute()
        entry_reason = self._reason(result, "claude-sonnet-5")
        self.assertIn("of rankable census usage", entry_reason)
        self.assertNotIn("% of census usage", entry_reason)

        previous = {"arms": [{"id": "claude-sonnet-4-6", "reason": "was an arm"},
                             {"id": "claude-opus-4-8", "reason": "was an arm"}],
                    "judge": {"id": "claude-fable-5-1", "reason": ""},
                    "preflight": {"id": "claude-haiku-4-5", "reason": ""}}
        census = TestIssue67._census_doc(counts={
            "claude-sonnet-5": {w: 100 for w in self.W},
            "claude-sonnet-4-6": {w: 10 for w in self.W},
            "claude-opus-4-8": {self.W[7]: 2},
        })
        result2 = self._compute(census=census, previous=previous)
        held_reason = self._reason(result2, "claude-sonnet-4-6")
        self.assertIn("of rankable census usage", held_reason)
        self.assertNotIn("% of census usage", held_reason)

        retired = {r["id"]: r["reason"] for r in result2["retired_since_last"]}
        self.assertIn("rankable census usage", retired["claude-opus-4-8"])

    def test_a_tiny_ranked_count_dominated_by_other_does_not_retire_a_previous_arm(self):
        """Item 4 (nit): the census can hold a handful of genuinely-ranked,
        attributable turns swamped by literally everything else being
        `other` (a fleet almost entirely routed through Bedrock/Vertex, say,
        with one stray direct-API turn). `ranked_total > 0` alone used to
        read as CENSUS_FRESH; below the `min_ranked_turns` floor it must
        fall back the same way an entirely-unranked census does, so a
        previous arm with no counted usage of its own is held, not retired
        at a false 0.0%.
        """
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        counts = {"other": {w: 100000 for w in self.W},
                  "claude-haiku-4-5": {self.W[0]: 1}}
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(census=census, previous=previous)
        self.assertIn("claude-opus-4-8", self._arm_ids(result))
        reason = self._reason(result, "claude-opus-4-8")
        self.assertIn("no evidence to retire it", reason)
        self.assertEqual(result["retired_since_last"], [])

    # --- item 5 (nit): a previous roster's `arms` ids must be shape-checked,
    # not merely typed-checked — render_summary interpolates them verbatim
    # into Markdown that eval.yml `tee`s to stdout, where GitHub parses
    # `::` workflow commands. ----------------------------------------------

    def test_previous_arm_ids_are_shape_checked_before_they_reach_the_summary(self):
        """`_clean_previous_arms` validated the SHAPE of the `arms` entry (a
        dict with a non-empty string `id`) but not the id's CONTENT. An id
        carrying a newline and an `::error::` line reached the published
        roster's `retired_since_last` (no current model matches it, and it
        is not in api_ids either) and, from there, render_summary's
        Markdown verbatim — which eval.yml prints to stdout.
        """
        hostile_id = "claude-sonnet-4-5\n::error::pwned::"
        previous = {"arms": [{"id": hostile_id, "reason": "was an arm"}]}
        result = self._compute(previous=previous)
        retired_ids = [r["id"] for r in result["retired_since_last"]]
        self.assertNotIn(hostile_id, retired_ids)
        summary = roster.render_summary(result)
        self.assertNotIn("::error::", summary)
        self.assertNotIn(hostile_id, summary)

    # --- item 7 (nit): _clean_counts must reject JSON booleans, and its
    # bad-cell warning must cover more than "not a number" -----------------

    def test_clean_counts_rejects_json_booleans(self):
        """`bool` is an `int` subclass in Python — `int(True)` is `1`,
        `int(False)` is `0` — so a census cell holding the JSON literal
        `true`/`false` silently coerced into a real count instead of being
        rejected as the wrong shape."""
        notes = []
        cleaned = roster._clean_counts(
            {"claude-opus-5": {"2026-W36": True, "2026-W35": False,
                               "2026-W34": 50}}, notes.append)
        self.assertEqual(cleaned, {"claude-opus-5": {"2026-W34": 50}})
        self.assertTrue(any("not a usable count" in n for n in notes), notes)

    def test_clean_counts_bad_cell_warning_covers_more_than_not_a_number(self):
        """The bad-cell warning said "not a number", but a negative count
        and a count above MAX_WEEKLY_TURNS both ARE numbers — they are
        rejected for being out of range, not for failing to parse as a
        number at all. "not a usable count" covers every rejection reason
        (non-numeric, boolean, negative, out of range) accurately."""
        notes = []
        roster._clean_counts({"claude-opus-5": {"2026-W36": -5}}, notes.append)
        self.assertTrue(any("not a usable count" in n for n in notes), notes)
        self.assertFalse(any("not a number" in n for n in notes), notes)

    # --- item 10: model_usage_census.py's lazy PyYAML import has a test for
    # main()'s own `--out` guard, but not for `--help` — the case the
    # laziness exists to fix in the first place ---------------------------

    def test_census_help_succeeds_with_pyyaml_unimportable(self):
        """`_require_model_id_re()` is called only when actually building a
        census; `--help` is handled by argparse inside `parser.parse_args()`
        and exits before that call is ever reached. A machine with no
        PyYAML installed at all must still get `--help` — this is the case
        the lazy import exists to fix, and it had no test of its own."""
        saved = {name: sys.modules.get(name) for name in ("yaml", "roster")}
        saved_re = model_usage_census.MODEL_ID_RE
        for name in ("yaml", "roster"):
            sys.modules.pop(name, None)
        sys.modules["yaml"] = None
        model_usage_census.MODEL_ID_RE = None
        try:
            argv = ["model_usage_census.py", "--help"]
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch.object(sys, "argv", argv), \
                 contextlib.redirect_stdout(out), \
                 contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    model_usage_census.main()
        finally:
            for name, mod in saved.items():
                if mod is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = mod
            model_usage_census.MODEL_ID_RE = saved_re
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("usage:", out.getvalue().lower())
        self.assertNotIn("Traceback", err.getvalue())


class TestIssue67Review5(unittest.TestCase):
    """Round 5 fixes for #67 (PR #129 review round 5), one test per item.
    See run_tests.py's class-per-review-round convention (TestIssue67Review,
    TestIssue67Review2, TestIssue67Review3, TestIssue67Review4) — a SIBLING
    of TestIssue67, reusing its canned documents rather than subclassing."""

    NOW = TestIssue67.NOW
    W = TestIssue67.W
    POLICY = TestIssue67.POLICY

    @classmethod
    def _policy(cls):
        return TestIssue67._policy()

    @classmethod
    def _compute(cls, models=TestIssue67.DEFAULT, census=TestIssue67.DEFAULT,
                 previous=None):
        return TestIssue67._compute(models=models, census=census, previous=previous)

    _arm_ids = staticmethod(TestIssue67._arm_ids)
    _reason = staticmethod(TestIssue67._reason)
    _model = staticmethod(TestIssue67._model)

    # --- design decision: catalogue_seen replaces _canonical_id_re -------

    def test_legacy_shaped_previously_seen_model_is_attributed_via_catalogue_seen(self):
        """A pre-#67 legacy-shaped id (family word AFTER a leading numeric
        segment, e.g. a `claude-3-...` id) that has since left the Models
        API is attributable when this harness's own history says it was
        once in the catalogue — `catalogue_seen`, not id SHAPE. The
        withdrawn `_canonical_id_re` never matched this shape at all (its
        pattern required the family word immediately after `claude-`), so
        this legacy model would have been starved out of the denominator
        even under round 4's code; `catalogue_seen` fixes it a different
        way — by evidence, not shape.
        """
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-sonnet-4-6", "2025-01-01T00:00:00Z"),
            self._model("claude-sonnet-5-0", "2026-06-01T00:00:00Z"),
            self._model("claude-opus-4-2", "2026-01-01T00:00:00Z"),
        ]}
        legacy_id = "claude-3-opus-20240229"
        previous = {"arms": [], "catalogue_seen": [legacy_id]}
        counts = {legacy_id: {w: 112 for w in self.W[:4]},
                  "claude-sonnet-4-6": {w: 12 for w in self.W[:4]}}
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(models=models, census=census, previous=previous)
        self.assertNotIn("claude-sonnet-4-6", self._arm_ids(result),
                         "sonnet-4-6 is not newest (sonnet-5-0 is) and its "
                         "real ~9.68% share must not seat it")

        rungs = roster.tier_rungs(self._policy())
        cleaned = roster._clean_counts(counts, lambda _m: None)
        api_ids = {m["id"] for m in models["models"]}
        aliases = roster.alias_map(list(api_ids) + list(cleaned))
        share = roster.usage_share(
            cleaned, "claude-sonnet-4-6", self.W[:4], rungs, aliases,
            api_ids=api_ids, previous_arms=set(),
            catalogue_seen={legacy_id} | api_ids)
        self.assertAlmostEqual(share, 100 * 48 / 496, places=2)
        self.assertAlmostEqual(share, 9.68, places=2)

        # Mutation check (manual, not automated): deleting the
        # `catalogue_seen` clause from `_is_attributable` drops the legacy
        # id's 448 turns from the denominator, leaving sonnet-4-6 at a
        # false 48/48 = 100.0% and seating it — turning the `assertNotIn`
        # above red.

    def test_legacy_shaped_model_with_no_catalogue_history_documents_the_first_run_caveat(self):
        """Same scenario, but `catalogue_seen` starts EMPTY — the
        documented first-run caveat: with no history yet, a model retired
        before this harness's first run is unattributable, and its usage
        silently drops from the denominator. This is expected, current
        behavior, not a bug — see `_is_attributable`'s docstring and
        DESIGN.md's roster properties."""
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-sonnet-4-6", "2025-01-01T00:00:00Z"),
            self._model("claude-sonnet-5-0", "2026-06-01T00:00:00Z"),
            self._model("claude-opus-4-2", "2026-01-01T00:00:00Z"),
        ]}
        legacy_id = "claude-3-opus-20240229"
        previous = {"arms": [], "catalogue_seen": []}
        counts = {legacy_id: {w: 112 for w in self.W[:4]},
                  "claude-sonnet-4-6": {w: 12 for w in self.W[:4]}}
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(models=models, census=census, previous=previous)
        self.assertIn("claude-sonnet-4-6", self._arm_ids(result))
        self.assertIn("100.0%", self._reason(result, "claude-sonnet-4-6"))

    def test_previous_arm_alias_usage_counts_via_widened_alias_map(self):
        """B1 (#129 review round 6): a previous arm published under a
        DATED id that has since left the Models API, whose real usage the
        census records under its UNDATED alias, must still count in the
        denominator. `aliases = alias_map(api_ids + list(counts))` never
        saw the dated id at all — it is neither an api id nor a census
        key, only its undated alias is (and only that alias is in
        `counts`) — so `alias_map` had no dated/undated PAIR to fold at
        all, and `previous_arms_folded` (built by running `previous_arms`
        through that same, blind `aliases` map) stayed identical to
        `previous_arms`, never matching the undated candidate. Measured
        through `compute_roster` on a946c9b: `claude-sonnet-5` reads
        "carries 97.1% of rankable census usage" off a denominator of 103
        instead of the real 5103. (The previous round's test built its own
        alias map with `previous_arms` already added to the ids list,
        which is exactly this fix — so it exercised the fixed formula
        without ever calling the buggy `compute_roster` code path, and
        passed on the buggy commit too.)
        """
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-sonnet-5", "2026-02-01T00:00:00Z"),
            self._model("claude-haiku-4-5", "2025-10-01T00:00:00Z"),
            self._model("claude-opus-5", "2026-04-01T00:00:00Z"),
        ]}
        counts = {
            "claude-sonnet-4-9": {self.W[0]: 5000},  # previous arm's usage, undated alias
            "claude-sonnet-5": {self.W[0]: 100},
            "claude-haiku-4-5": {self.W[0]: 3},
        }
        census = TestIssue67._census_doc(counts=counts)
        previous = {"arms": [{"id": "claude-sonnet-4-9-20260101",
                              "reason": "was an arm"}]}
        result = self._compute(models=models, census=census, previous=previous)

        for arm in result["arms"]:
            self.assertNotIn("carries 97", arm["reason"], arm)
        self.assertIn("claude-sonnet-5", self._arm_ids(result))
        reason = self._reason(result, "claude-sonnet-5")
        self.assertIn("newest", reason)
        self.assertNotIn("carries", reason)

        # Reproduces `compute_roster`'s OWN widened alias-map formula (not
        # a hand-picked ids list) only to pin the exact measured share and
        # totals the reason text above implies.
        rungs = roster.tier_rungs(self._policy())
        api_ids = {m["id"] for m in models["models"]}
        cleaned = roster._clean_counts(counts, lambda _m: None)
        previous_arms = {"claude-sonnet-4-9-20260101"}
        catalogue_seen = set(api_ids)
        aliases = roster.alias_map(
            list(api_ids) + list(cleaned) + list(previous_arms) + list(catalogue_seen))
        raw_total, ranked_total = roster._in_window_totals(
            cleaned, set(self.W[:1]), rungs, aliases=aliases,
            api_ids=api_ids, previous_arms=previous_arms,
            catalogue_seen=catalogue_seen)
        self.assertEqual(raw_total, 5103)
        self.assertEqual(ranked_total, 5103)
        share = roster.usage_share(
            cleaned, "claude-sonnet-5", self.W[:1], rungs, aliases,
            api_ids=api_ids, previous_arms=previous_arms,
            catalogue_seen=catalogue_seen)
        self.assertGreater(share, 1.9)
        self.assertLess(share, 2.0)
        # Mutation check (manual): reverting `compute_roster`'s `aliases`
        # line to `alias_map(api_ids + list(counts))` (dropping
        # `previous_arms`/`catalogue_seen` from the ids fed to
        # `alias_map`) turns every assertion above red again — the
        # denominator collapses back to 103 and `claude-sonnet-5` reads
        # "carries 97.09%" instead of the newest-in-tier reason.

    def test_catalogue_seen_round_trips_through_the_published_roster(self):
        """`catalogue_seen` is the union of api ids seen this run and
        whatever the previous roster already accumulated, sorted and
        deduplicated, and it is shape-checked before being read back —
        the same `_clean_previous_arms`-style treatment as `arms`,
        including the count-only warning on a hostile entry."""
        models = TestIssue67._models_doc()
        result = self._compute(models=models, previous=None)
        api_ids = {m["id"] for m in models["models"]}
        seen_ids = [e["id"] for e in result["catalogue_seen"]]
        self.assertEqual(set(seen_ids), api_ids)
        self.assertEqual(seen_ids, sorted(seen_ids))
        for entry in result["catalogue_seen"]:
            self.assertIn("last_seen", entry)

        hostile = "claude-sonnet-4-5\n::error::pwned::"
        previous = {"arms": [], "catalogue_seen": result["catalogue_seen"] +
                   [hostile, 123, None]}
        warnings = []
        roster.compute_roster(
            models_doc=models, census_doc=None, policy=self._policy(),
            previous=previous, now=self.NOW, warn=warnings.append)
        self.assertTrue(
            any("catalogue_seen" in w and "skipped" in w for w in warnings),
            warnings)
        for w in warnings:
            self.assertNotIn(hostile, w)

        result2 = self._compute(models=models, previous=previous)
        # `catalogue_seen` itself never reaches render_summary's Markdown
        # (N2, #129 review round 6) — its safety property is the round
        # trip above (published, read back, re-published), not a summary
        # check, which would pass here whether or not the hostile entry
        # were sanitized.
        self.assertNotIn(hostile, [e["id"] for e in result2["catalogue_seen"]])

    # --- S1: the min_ranked_turns floor must apply PER WINDOW, not only
    # over the 8-week union -------------------------------------------------

    def test_min_ranked_turns_floor_applies_to_the_enter_window_on_its_own(self):
        """30 ranked turns in weeks 5-8 (outside the 4-week enter window)
        clear the union floor, while the enter window itself carries a
        single turn — that one turn used to compute a 100.0% entry share
        and seat `claude-sonnet-4-6` (not the newest in its tier; the
        DEFAULT fixture's `claude-sonnet-5` is), on evidence of a single
        turn.
        """
        counts = {
            "claude-sonnet-4-6": {self.W[0]: 1},                     # enter window: 1 turn
            "claude-opus-5": {w: 6 for w in self.W[4:8]},             # weeks 5-8: 24 turns
        }
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(census=census, previous=None)
        self.assertNotIn("claude-sonnet-4-6", self._arm_ids(result),
                         "one turn inside a 4-turn-total enter window must "
                         "not clear the 20-turn floor just because weeks "
                         "5-8 do")
        # Mutation check (manual): gating the entry share check on the
        # union's `usable` alone (reverting `enter_usable` back to
        # `usable`) seats claude-sonnet-4-6 at "100.0%" here — red.

    # --- S2: an absolute floor alone is not enough; a RELATIVE guard too ---

    def test_min_ranked_share_holds_a_previous_arm_at_the_absolute_floor(self):
        """`other` dominates the window (100000 turns/week for 8 weeks) with
        exactly `min_ranked_turns` (20) genuinely ranked turns on a
        DIFFERENT model — the absolute floor alone reads this as usable
        evidence and retires `claude-opus-4-8` (no counted usage of its
        own) at a literal 0.0% against 800,020 raw turns. The relative
        floor (`min_ranked_share`) must hold it instead."""
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        counts = {"other": {w: 100000 for w in self.W},
                  "claude-haiku-4-5": {self.W[0]: 20}}
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(census=census, previous=previous)
        self.assertIn("claude-opus-4-8", self._arm_ids(result))
        reason = self._reason(result, "claude-opus-4-8")
        self.assertIn("no evidence to retire it", reason)
        self.assertEqual(result["retired_since_last"], [])

    def test_min_ranked_share_does_not_hold_a_genuinely_ranked_census(self):
        """A census that is genuinely ranked over a meaningful share of the
        raw window total must not be held back by the new relative guard —
        retirement proceeds normally."""
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        counts = {"claude-sonnet-5": {w: 100 for w in self.W}}
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(census=census, previous=previous)
        self.assertNotIn("claude-opus-4-8", self._arm_ids(result))
        retired = {r["id"]: r["reason"] for r in result["retired_since_last"]}
        self.assertIn("claude-opus-4-8", retired)
        self.assertIn("exit bar", retired["claude-opus-4-8"])

    # --- S4: a models.json entry's id must be shape-checked too -----------

    def test_malformed_model_id_in_the_models_document_is_dropped_with_a_warning(self):
        """A models.json entry carrying a hostile id (a newline and an
        `::error::` line) must not reach `unranked`/`excluded` — and from
        there render_summary's Markdown, which eval.yml prints to stdout
        — or `catalogue_seen` (checked separately below: `catalogue_seen`
        never itself reaches render_summary's Markdown, so a summary
        check would not exercise its own sanitization — N2, #129 review
        round 6)."""
        hostile = "claude-opus-4\n::error::pwned::"
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-haiku-4-5", "2025-10-01T00:00:00Z"),
            self._model(hostile, "2026-01-01T00:00:00Z"),
        ]}
        warnings = []
        result = roster.compute_roster(
            models_doc=models, census_doc=None, policy=self._policy(),
            previous=None, now=self.NOW, warn=warnings.append)
        self.assertTrue(any("malformed model-id-shaped" in w for w in warnings), warnings)
        self.assertNotIn(hostile, [e["id"] for e in result["catalogue_seen"]])
        for entries in (result["arms"], result["unranked"], result["excluded"]):
            self.assertNotIn(hostile, [e["id"] for e in entries])
        summary = roster.render_summary(result)
        self.assertNotIn("::error::", summary)
        self.assertNotIn(hostile, summary)

    # --- S6: the `\Z` anchor in PREVIOUS_ARM_ID_RE, pinned ------------------

    def test_previous_arm_id_re_rejects_a_trailing_newline(self):
        """`$` also matches just before a trailing newline; `\\Z` does not.
        Reverting the anchor to `$` would let `claude-opus-4\\n` through as
        a "well-formed" id."""
        self.assertIsNone(roster.PREVIOUS_ARM_ID_RE.match("claude-opus-4\n"))
        self.assertIsNotNone(roster.PREVIOUS_ARM_ID_RE.match("claude-opus-4"))

    # --- N1: a rounded share must not contradict its own bar ---------------

    def test_retirement_reason_uses_two_decimals_when_one_would_touch_the_bar(self):
        """A previous arm at a true 1.96% exit-window share rounds to
        "2.0%" at one decimal — "below the 2% exit bar (2.0%)" reads as
        self-contradictory. Two decimals only when the tie actually
        happens."""
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        counts = {"claude-opus-4-8": {self.W[0]: 98},
                  "claude-sonnet-5": {self.W[0]: 4902}}
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(census=census, previous=previous)
        retired = {r["id"]: r["reason"] for r in result["retired_since_last"]}
        self.assertIn("claude-opus-4-8", retired)
        self.assertIn("1.96%", retired["claude-opus-4-8"])
        self.assertNotIn("2.0%", retired["claude-opus-4-8"])

    def test_retirement_reason_escalates_past_two_decimals_when_needed(self):
        """S2 (#129 review round 6): two decimals is not always enough to
        stop touching the bar (1.9999% still rounds to "2.00%" at two
        decimals), and a genuinely tiny nonzero share (0.04%, 0.004%)
        must not render as the misleading "0.0%" — about a model that
        DID carry turns, not one with none. `_format_share` escalates
        through 1/2/3/4/6 decimals until the text differs from the bar
        and, for a nonzero value, does not read as "0.0...0"."""
        cases = [
            (1999, 98001, "1.999%", "2.0%"),
            (19999, 980001, "1.9999%", "2.00%"),
            (4, 9996, "0.04%", "0.0%"),
            (40, 999960, "0.004%", "0.00%"),
        ]
        for opus, sonnet, expect, forbid in cases:
            with self.subTest(opus=opus, sonnet=sonnet):
                previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
                counts = {"claude-opus-4-8": {self.W[0]: opus},
                         "claude-sonnet-5": {self.W[0]: sonnet}}
                census = TestIssue67._census_doc(counts=counts)
                result = self._compute(census=census, previous=previous)
                retired = {r["id"]: r["reason"] for r in result["retired_since_last"]}
                self.assertIn("claude-opus-4-8", retired)
                self.assertIn(expect, retired["claude-opus-4-8"])
                self.assertNotIn(forbid, retired["claude-opus-4-8"])
        # Mutation check (manual): reverting `_format_share` to stop after
        # two decimals renders 1.9999% as "2.00%" (touches the bar) and
        # 0.004% as "0.00%" (reads as no usage) — turning the
        # corresponding subTest red.

    def test_at_or_above_reasons_are_not_escalated(self):
        """A model at EXACTLY its bar in the "at or above" direction is
        not self-contradictory ("carries 10.0% ... at or above the 10%
        entry bar" is correct at a true 10.0%) — `_format_share` must not
        escalate past one decimal there."""
        self.assertEqual(roster._format_share(10.0, 10), "10.0")
        self.assertEqual(roster._format_share(2.0, 2), "2.0")

    # --- N2: _clean_counts must require an actual int, not a coercible
    # string/float --------------------------------------------------------

    def test_clean_counts_requires_actual_ints_not_coercible_strings_or_floats(self):
        """`1.9` (a float) silently truncated to `1`; `"5"` (a JSON string)
        parsed as `5`; `"5_0"` parsed as `50` (Python's `int()` honors the
        digit-group underscore numeric-literal syntax inside a string);
        `"٥"` (an Arabic-Indic digit) parsed as `5` (`int()` accepts
        non-ASCII Unicode decimal digits). None of these is a value
        `json.load` ever hands back for a JSON number."""
        notes = []
        cleaned = roster._clean_counts(
            {"claude-opus-5": {"2026-W36": 1.9, "2026-W35": "5",
                               "2026-W34": "5_0", "2026-W33": "٥",
                               "2026-W32": 50}}, notes.append)
        self.assertEqual(cleaned, {"claude-opus-5": {"2026-W32": 50}})
        self.assertTrue(any("not a usable count" in n for n in notes), notes)

    # --- N4: min_ranked_turns/min_ranked_share validated with the other
    # thresholds -------------------------------------------------------------

    def test_roster_policy_is_the_single_source_of_thresholds(self):
        base = dict(self._policy())
        for key in ("min_ranked_turns", "min_ranked_share", "cooling_off_days",
                   "arm_enter_usage_pct", "arm_exit_window_weeks"):
            for bad, label in ((None, "missing"), ("20", "string"),
                              (-5, "negative"), (None, "None")):
                policy = dict(base)
                if label == "missing":
                    del policy[key]
                else:
                    policy[key] = bad
                with self.subTest(key=key, bad=label):
                    with self.assertRaises(ValueError) as ctx:
                        roster.validate_policy(policy)
                    self.assertIn(key, str(ctx.exception))
        # min_ranked_share also has an upper bound: a share above 1 (100%)
        # is not a fraction.
        policy = dict(base)
        policy["min_ranked_share"] = 1.5
        with self.assertRaises(ValueError) as ctx:
            roster.validate_policy(policy)
        self.assertIn("min_ranked_share", str(ctx.exception))
        # The real policy file must itself validate cleanly.
        roster.validate_policy(base)

    def test_validate_policy_requires_a_well_formed_tiers_ladder(self):
        """N6 (#129 review round 6): `validate_policy` checked numeric
        thresholds only — a policy missing `tiers` (or with a malformed
        one) sailed through and KeyErrored deep inside `tier_rungs`
        instead of failing loudly, by name, at the same point every other
        bad threshold does."""
        base = dict(self._policy())
        for bad, label in (
            (None, "missing"), ([], "empty list"), ("sonnet", "not a list"),
            ([""], "empty string rung"), ([[]], "empty peer list"),
            ([["sonnet", 5]], "non-string peer"), ([123], "non-string rung"),
        ):
            policy = dict(base)
            if label == "missing":
                del policy["tiers"]
            else:
                policy["tiers"] = bad
            with self.subTest(bad=label):
                with self.assertRaises(ValueError) as ctx:
                    roster.validate_policy(policy)
                self.assertIn("tiers", str(ctx.exception))
        # The real policy file's tiers must validate cleanly.
        roster.validate_policy(base)
        # Mutation check (manual): removing the `tiers` check from
        # `validate_policy` turns every subTest above red — `tiers`
        # sails through unvalidated and `tier_rungs` KeyErrors instead
        # (for the "missing" case) or misbehaves silently.


class TestIssue67Review6(unittest.TestCase):
    """Round 6 fixes for #67 (PR #129 review round 6), one test per fix.
    See run_tests.py's class-per-review-round convention — a SIBLING of
    TestIssue67, reusing its canned documents rather than subclassing."""

    NOW = TestIssue67.NOW
    W = TestIssue67.W
    POLICY = TestIssue67.POLICY

    @classmethod
    def _policy(cls):
        return TestIssue67._policy()

    @classmethod
    def _compute(cls, models=TestIssue67.DEFAULT, census=TestIssue67.DEFAULT,
                 previous=None):
        return TestIssue67._compute(models=models, census=census, previous=previous)

    _arm_ids = staticmethod(TestIssue67._arm_ids)
    _reason = staticmethod(TestIssue67._reason)
    _model = staticmethod(TestIssue67._model)

    # --- B2: `_is_attributable` has exactly three routes left after round
    # 6 dropped `candidate in api_ids`/`folded in api_ids` and the plain
    # `candidate in previous_arms`/`folded in previous_arms` clauses as
    # provably dead. One isolated regression floor per surviving route,
    # all built on the same legacy-shaped dated/undated pair, and each
    # scenario's previous roster's `catalogue_seen` deliberately excludes
    # the id under test so the OTHER routes cannot rescue it by accident.

    DATED = "claude-3-5-sonnet-20241022"
    UNDATED = "claude-3-5-sonnet"

    def test_route_folded_in_api_ids_folded(self):
        """The catalogue publishes ONLY the dated snapshot id; the census
        records its usage under the bare undated alias. Neither
        `previous_arms` nor `catalogue_seen` names either spelling — the
        only possible route is `folded in api_ids_folded`."""
        models = {"fetched_at": "2026-09-04T11:00:00Z",
                 "models": [self._model(self.DATED, "2026-01-01T00:00:00Z")]}
        counts = {self.UNDATED: {self.W[0]: 500}}
        census = TestIssue67._census_doc(counts=counts)
        previous = {"arms": [], "catalogue_seen": []}
        result = self._compute(models=models, census=census, previous=previous)
        reason = self._reason(result, self.DATED)
        self.assertIn("carries", reason)
        self.assertIn("100.0%", reason)
        self.assertNotIn(self.UNDATED, self._seen_ids(result))
        # Mutation check (manual): deleting `folded in (api_ids_folded or
        # ())` from `_is_attributable` makes the 500 turns under
        # `claude-3-5-sonnet` unattributable (neither remaining route
        # names it), so the window carries zero rankable usage and
        # `claude-3-5-sonnet-20241022` falls back to "no fresh census
        # ...; fell back to newest per tier" — turning both assertions
        # above red.

    def test_route_previous_arms_folded(self):
        """A previous arm published under the dated id, since retired
        from the Models API; the census records its usage under the bare
        undated alias. `catalogue_seen` names neither spelling — the only
        possible route is `previous_arms_folded`."""
        models = TestIssue67._models_doc(drop={
            "claude-sonnet-4-6", "claude-sonnet-5", "claude-opus-4-8",
            "claude-opus-5", "claude-fable-5-1"})  # haiku only
        counts = {self.UNDATED: {self.W[0]: 500},
                 "claude-haiku-4-5": {self.W[0]: 25}}
        census = TestIssue67._census_doc(counts=counts)
        previous = {"arms": [{"id": self.DATED, "reason": "was an arm"}],
                    "catalogue_seen": []}
        result = self._compute(models=models, census=census, previous=previous)
        reason = self._reason(result, "claude-haiku-4-5")
        self.assertIn("newest", reason)
        self.assertNotIn("carries", reason)
        self.assertNotIn(self.UNDATED, self._seen_ids(result))
        self.assertNotIn(self.DATED, self._seen_ids(result))
        # Mutation check (manual): deleting `candidate in
        # previous_arms_folded or folded in previous_arms_folded` makes
        # the 500 turns unattributable, shrinking the denominator to
        # haiku's own 25 turns (still above min_ranked_turns, so the
        # census still reads as usable rather than merely falling back)
        # and inflating its share to a false 100% — its reason becomes
        # "carries 100.0%..." instead of the newest-in-tier one, turning
        # both assertions above red.

    def test_route_catalogue_seen(self):
        """Both the dated and undated spellings have left the Models API
        and neither was ever a previous arm; only the UNDATED spelling
        was ever recorded in `catalogue_seen` history. Usage is recorded
        under the DATED spelling, so only the FOLDED form matches
        `catalogue_seen` — the only possible route."""
        models = TestIssue67._models_doc(drop={
            "claude-sonnet-4-6", "claude-sonnet-5", "claude-opus-4-8",
            "claude-opus-5", "claude-fable-5-1"})  # haiku only
        counts = {self.DATED: {self.W[0]: 500},
                 "claude-haiku-4-5": {self.W[0]: 25}}
        census = TestIssue67._census_doc(counts=counts)
        previous = {"arms": [], "catalogue_seen": [self.UNDATED]}
        result = self._compute(models=models, census=census, previous=previous)
        reason = self._reason(result, "claude-haiku-4-5")
        self.assertIn("newest", reason)
        self.assertNotIn("carries", reason)
        # Mutation check (manual): deleting `candidate in catalogue_seen
        # or folded in catalogue_seen` makes the 500 turns unattributable
        # (neither of the other two routes names the dated id or its
        # fold), shrinking the denominator to haiku's own 5 turns and
        # inflating its share to a false 100% — turning both assertions
        # above red.

    def test_catalogue_seen_is_always_a_superset_of_this_runs_api_ids(self):
        """`catalogue_seen = set(api_ids) | previous.catalogue_seen`
        (compute_roster) — every id this run's Models API returned is in
        `catalogue_seen` by construction, which is also why a bare
        `candidate in api_ids`/`folded in api_ids` check added nothing
        `catalogue_seen` didn't already cover."""
        models = TestIssue67._models_doc()
        result = self._compute(models=models, previous=None)
        api_ids = {m["id"] for m in models["models"]}
        self.assertLessEqual(api_ids, self._seen_ids(result))

    def test_two_dead_clauses_stay_deleted(self):
        """Regression floor for the deletion itself, not just for the
        routes that remain: `_is_attributable`'s EXECUTABLE body (the
        `return` statement, not its prose docstring, which names the
        deleted clauses on purpose to explain why they're gone) must not
        contain the bare, unfolded `candidate in api_ids`/`candidate in
        previous_arms` checks — both provably subsumed by their `_folded`
        siblings."""
        import inspect
        src = inspect.getsource(roster._is_attributable)
        body = src.rsplit('"""', 1)[-1]
        self.assertNotIn("candidate in api_ids", body)
        self.assertNotIn("candidate in previous_arms or", body)

    # --- S1: the relative min_ranked_share floor must apply PER WINDOW,
    # not only over the 8-week union -----------------------------------

    def test_min_ranked_share_floor_applies_to_the_enter_window_on_its_own(self):
        """`other` dominates weeks 1-4 (the enter window) while a real
        model's usage sits in weeks 5-8 (inside the union, outside the
        enter window) — together they clear the UNION's relative floor
        (100,025 of 4,100,025), but the enter window's OWN 25 ranked
        turns against 4,000,025 raw ones fail its own relative floor.
        Before this fix, only the ABSOLUTE per-window floor existed
        (round 5), and 25 >= 20 cleared it — computing a false 100.0%
        entry share for `claude-sonnet-4-6`, which is not the newest in
        its tier (`claude-sonnet-5` is, in the DEFAULT fixture)."""
        counts = {
            "other": {w: 1_000_000 for w in self.W[:4]},
            "claude-sonnet-4-6": {self.W[0]: 25},
            "claude-opus-5": {w: 25_000 for w in self.W[4:8]},
        }
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(census=census, previous=None)
        self.assertNotIn("claude-sonnet-4-6", self._arm_ids(result),
                         "25 ranked turns against 4,000,025 raw ones in "
                         "the enter window must not clear the relative "
                         "floor just because weeks 5-8 do")
        # Mutation check (manual): dropping the
        # `enter_ranked_total >= policy["min_ranked_share"] *
        # enter_raw_total` clause from `enter_usable` (reverting to the
        # absolute-only check) seats claude-sonnet-4-6 at "carries
        # 100.0%" here — red.

    # --- N5 / S1: the exit-side per-window gate is unreachable under the
    # SHIPPED policy (arm_exit_window_weeks >= arm_enter_window_weeks
    # makes the exit window the union); a test-only policy with a
    # shorter exit window makes it reachable and pins both branches of
    # the widened floor note. ------------------------------------------

    @staticmethod
    def _short_exit_policy():
        policy = dict(TestIssue67Review6._policy())
        policy["arm_exit_window_weeks"] = 2
        return policy

    def test_exit_side_floor_note_names_the_absolute_floor(self):
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        counts = {"claude-sonnet-5": {self.W[2]: 30, self.W[3]: 30}}
        census = TestIssue67._census_doc(counts=counts)
        result = roster.compute_roster(
            models_doc=TestIssue67._models_doc(), census_doc=census,
            policy=self._short_exit_policy(), previous=previous, now=self.NOW)
        self.assertIn("claude-opus-4-8", self._arm_ids(result))
        reason = self._reason(result, "claude-opus-4-8")
        self.assertIn("no evidence to retire it", reason)
        self.assertIn("0 turn(s)", reason)
        self.assertIn("turn floor", reason)
        self.assertNotIn("relative floor", reason)

    def test_exit_side_floor_note_names_the_relative_floor(self):
        previous = {"arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}]}
        counts = {
            "other": {self.W[0]: 1500, self.W[1]: 1500},
            "claude-opus-4-8": {self.W[0]: 13, self.W[1]: 12},
            "claude-sonnet-5": {self.W[2]: 250, self.W[3]: 250},
        }
        census = TestIssue67._census_doc(counts=counts)
        result = roster.compute_roster(
            models_doc=TestIssue67._models_doc(), census_doc=census,
            policy=self._short_exit_policy(), previous=previous, now=self.NOW)
        self.assertIn("claude-opus-4-8", self._arm_ids(result))
        reason = self._reason(result, "claude-opus-4-8")
        self.assertIn("no evidence to retire it", reason)
        self.assertIn("relative floor for this window", reason)
        self.assertNotIn("turn floor", reason)
        # Mutation check (manual, both tests above): reverting
        # `exit_usable` to its pre-S1 absolute-only definition, or
        # deleting the `elif not exit_usable:` branch outright, turns
        # these red — the first because the relative-cause test's 25
        # exit-window turns clear the absolute floor alone (`exit_usable`
        # would read True, giving opus-4-8 a "held over ... still X%"
        # reason via the usage_share branch instead), the second because
        # opus-4-8 would fall through to the "below the exit bar" branch
        # and be retired instead of held.

    # --- S3: catalogue_seen needs an age, a cap, and a migration path for
    # the bare-string shape it used to publish ---------------------------

    @staticmethod
    def _seen_ids(result):
        return {e["id"] for e in result["catalogue_seen"]}

    def test_catalogue_seen_migrates_the_bare_string_shape(self):
        """The shape `catalogue_seen` used to publish (a bare list of id
        strings) must still be READABLE for one migration run: no crash,
        no shape warning, and the ids come through into this run's
        (now dict-shaped) output."""
        models = TestIssue67._models_doc()
        previous = {"arms": [], "catalogue_seen": ["claude-opus-4-7"]}
        warnings = []
        result = roster.compute_roster(
            models_doc=models, census_doc=None, policy=self._policy(),
            previous=previous, now=self.NOW, warn=warnings.append)
        self.assertIn("claude-opus-4-7", self._seen_ids(result))
        for entry in result["catalogue_seen"]:
            self.assertIn("id", entry)
            self.assertIn("last_seen", entry)
        self.assertFalse(
            [w for w in warnings if "catalogue_seen" in w and "skipped" in w],
            warnings)

    def test_catalogue_seen_entry_ages_out_and_stops_diluting_a_held_over_arm(self):
        """S3 (#129 review round 6): a valid-shaped id planted directly in
        `catalogue_seen` with a stale `last_seen` — never actually
        returned by the Models API, so nothing ever refreshes it — must
        drop out of `catalogue_seen` once it is older than
        `catalogue_seen_max_age_days`. Before this fix, catalogue_seen had
        no age at all: the plant stayed attributable forever, and its
        fabricated usage diluted a real held-over arm's measured share
        from 100% to a false 0.1%, retiring it on no real evidence.
        """
        stale = (self.NOW - timedelta(days=181)).strftime("%Y-%m-%d")
        previous = {
            "arms": [{"id": "claude-opus-4-8", "reason": "was an arm"}],
            "catalogue_seen": [{"id": "claude-sonnet-9-9", "last_seen": stale}],
        }
        # opus-4-8's own 96 turns alone are 100% of the rankable window;
        # with the plant credited too (95904 more, under a different
        # model) they dilute to exactly 96/96000 = 0.1%.
        counts = {"claude-sonnet-9-9": {w: 11988 for w in self.W},
                 "claude-opus-4-8": {w: 12 for w in self.W}}
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(census=census, previous=previous)
        self.assertNotIn("claude-sonnet-9-9", self._seen_ids(result),
                         "a plant never returned by the Models API, aged "
                         "past the policy window, must not survive into "
                         "this run's catalogue_seen")
        # Once excluded, the plant's own huge (fabricated) volume still
        # shows up in the RAW window total (attribution-blind), which now
        # also trips S1's relative floor — a second, independent reason
        # the real arm is held rather than retired on manufactured
        # evidence, whichever text names it.
        self.assertIn("claude-opus-4-8", self._arm_ids(result))
        reason = self._reason(result, "claude-opus-4-8")
        self.assertIn("no evidence to retire it", reason)
        # "0.1%" legitimately appears here now (N7, #129 review round 6):
        # it's the RAW-vs-ranked ratio S1's relative floor reports (96 of
        # 96000 raw turns are rankable), not the old per-model DILUTED
        # share this test guards against — that specific phrasing is what
        # must stay absent.
        self.assertNotIn("still 0.1%", reason)
        self.assertNotIn("claude-opus-4-8",
                         {r["id"] for r in result["retired_since_last"]})
        # Mutation check (manual): skipping the age-eviction step in
        # `_update_catalogue_seen` (treat every previously-seen id as
        # kept regardless of `last_seen`) keeps `claude-sonnet-9-9`
        # attributable, diluting opus-4-8's exit-window share to a false
        # 0.1% and RETIRING it (not merely leaving it unheld) — the
        # `assertNotIn("claude-sonnet-9-9", ...)` above goes red directly,
        # and opus-4-8 no longer appears in `arms` at all.

    def test_real_since_retired_model_stays_attributable_within_the_age_window(self):
        """The normal case S3 must not break: an id genuinely seen
        recently (well within `catalogue_seen_max_age_days`) stays
        attributable, dict-shaped `last_seen` and all."""
        recent = (self.NOW - timedelta(days=10)).strftime("%Y-%m-%d")
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-sonnet-4-6", "2025-01-01T00:00:00Z"),
            self._model("claude-sonnet-5-0", "2026-06-01T00:00:00Z"),
        ]}
        previous = {"arms": [],
                   "catalogue_seen": [{"id": "claude-opus-4-8", "last_seen": recent}]}
        counts = {"claude-opus-4-8": {w: 1000 for w in self.W},
                 "claude-sonnet-4-6": {w: 60 for w in self.W}}
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(models=models, census=census, previous=previous)
        self.assertNotIn("claude-sonnet-4-6", self._arm_ids(result),
                         "claude-opus-4-8's usage must still count in the "
                         "denominator, keeping sonnet-4-6's share below "
                         "the entry bar")
        self.assertIn("claude-opus-4-8", self._seen_ids(result))

    def test_three_chained_runs_drop_the_plant_after_its_age(self):
        """The plant is republished by the harness as its own output on
        every later run — reverting it on the branch does not remove it
        — until it ages out on its own. Simulates three chained runs,
        each feeding the previous run's own `catalogue_seen` output
        forward, `now` advancing between them; the plant is never
        returned by the Models API in any of the three runs, so nothing
        ever refreshes it."""
        models = TestIssue67._models_doc(drop={"claude-opus-4-8"})
        plant = "claude-sonnet-9-9"
        previous = {"arms": [], "catalogue_seen": [plant]}  # migrates: last_seen = run 1's date
        now = self.NOW
        for run in range(3):
            result = roster.compute_roster(
                models_doc=models, census_doc=None, policy=self._policy(),
                previous=previous, now=now)
            if run < 2:
                self.assertIn(plant, self._seen_ids(result),
                             f"run {run}: still within the age window")
            previous = result
            now = now + timedelta(days=100)  # 3 runs span 200 days > 180-day policy
        self.assertNotIn(plant, self._seen_ids(result),
                         "the plant must not survive past its age even "
                         "though every run kept republishing it forward")

    def test_catalogue_seen_caps_length_with_a_count_only_warning(self):
        """N3, merged into S3's rewrite: `catalogue_seen` accepts at most
        500 entries (sorted head kept), past which the warning names only
        the count — not one dropped id, which would be a value from an
        untrusted branch reaching a log."""
        previous = {"arms": [], "catalogue_seen": sorted(
            f"claude-sonnet-{i}-9" for i in range(600))}
        warnings = []
        result = roster.compute_roster(
            models_doc=TestIssue67._models_doc(), census_doc=None,
            policy=self._policy(), previous=previous, now=self.NOW,
            warn=warnings.append)
        self.assertLessEqual(len(result["catalogue_seen"]), 500)
        api_ids = {m["id"] for m in TestIssue67._models_doc()["models"]}
        self.assertLessEqual(api_ids, self._seen_ids(result),
                             "the cap must never evict this run's own live ids")
        self.assertTrue(any("cap" in w or "500" in w for w in warnings), warnings)
        for w in warnings:
            self.assertNotIn("claude-sonnet-599-9", w)

    # --- N3: `_clean_previous_arms` dedup must be O(1)-membership and
    # cap its accepted list the same way catalogue_seen does -------------

    def test_previous_arms_caps_length_with_a_count_only_warning(self):
        """`_clean_previous_arms` dedup used `entry not in ids` over a
        growing list — O(n^2) — and had no cap at all. A set for
        membership plus a 500-entry cap (sorted head, count-only
        warning) matches the treatment `catalogue_seen` already got."""
        previous = {"arms": [{"id": f"claude-sonnet-{i}-9", "reason": "x"}
                             for i in range(600)]}
        warnings = []
        result = roster.compute_roster(
            models_doc=TestIssue67._models_doc(), census_doc=None,
            policy=self._policy(), previous=previous, now=self.NOW,
            warn=warnings.append)
        retired_ids = {r["id"] for r in result["retired_since_last"]}
        self.assertLessEqual(len(retired_ids), 500)
        self.assertTrue(any("cap" in w or "500" in w for w in warnings), warnings)
        for w in warnings:
            self.assertNotIn("claude-sonnet-599-9", w)

    # --- N7: the policy's own relative-floor percentage must not round
    # to "0%" via `:.0f` -------------------------------------------------

    def test_census_unranked_relative_floor_reason_does_not_round_the_bar_to_zero(self):
        """`f"{100 * policy['min_ranked_share']:.0f}%"` rendered a 0.5%
        policy floor as "0%" — self-contradictory next to a measured
        share that IS under 0.5% but reads as "under the 0% floor".
        `:g` for the policy bar, and the S2 escalating formatter for the
        measured share."""
        policy = dict(self._policy())
        policy["min_ranked_share"] = 0.005
        _, note, code = roster._census_verdict(
            {"generated_at": self.NOW.strftime("%Y-%m-%dT%H:%M:%SZ")},
            raw_total=100000, ranked_total=499, policy=policy, now=self.NOW)
        self.assertEqual(code, roster.CENSUS_UNRANKED)
        self.assertIn("0.5% relative", note)
        self.assertNotIn("0% relative", note)
        self.assertIn("0.499%", note)
        # Mutation check (manual): reverting the bar's format spec to
        # `:.0f` renders "0% relative floor" — red.

    # --- N8: source.census_at must publish the PARSED timestamp,
    # re-rendered, not the raw string ------------------------------------

    def test_census_at_publishes_the_parsed_timestamp_not_the_raw_string(self):
        """`parse_ts` strips a census `generated_at` before comparing it
        against `now`, but `source.census_at` used to publish the RAW
        string verbatim — a trailing newline or `\\r` would reach
        `latest.json`, summary.md, and eval.yml's stdout as a literal
        control character."""
        census = TestIssue67._census_doc(generated_at="2026-09-03T00:00:00Z\n")
        result = self._compute(census=census, previous=None)
        self.assertEqual(result["source"]["census_at"], "2026-09-03T00:00:00Z")
        summary = roster.render_summary(result)
        self.assertNotIn("\n\n·", summary)
        self.assertNotIn("Z\n`", summary)
        # Mutation check (manual): reverting `census_at_published` to
        # `(census_doc or {}).get("generated_at")` (the raw string)
        # republishes the trailing newline — the assertEqual above
        # turns red.

    # --- N9: SNAPSHOT_SUFFIX must anchor at the true end of string -------

    def test_snapshot_suffix_rejects_a_trailing_control_character(self):
        """`$` matches just before a trailing newline as well as at the
        true end of string; `\\Z` does not."""
        self.assertIsNone(roster.SNAPSHOT_SUFFIX.match("claude-sonnet-4-5-20260101\n"))
        match = roster.SNAPSHOT_SUFFIX.match("claude-sonnet-4-5-20260101")
        self.assertIsNotNone(match)
        self.assertEqual(match.group("base"), "claude-sonnet-4-5")

    def test_snapshot_suffix_anchor_end_to_end_through_compute_roster(self):
        """A census key `claude-sonnet-4-5-20260101\\n` folded onto
        `claude-sonnet-4-5` under the old `$`-anchored regex, inflating
        its measured share from a real 50.0% to a false ~99.9%."""
        models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model("claude-sonnet-4-5", "2026-01-01T00:00:00Z"),
            self._model("claude-haiku-4-5", "2025-10-01T00:00:00Z"),
        ]}
        counts = {"claude-sonnet-4-5-20260101\n": {self.W[0]: 9800},
                 "claude-sonnet-4-5": {self.W[0]: 100},
                 "claude-haiku-4-5": {self.W[0]: 100}}
        census = TestIssue67._census_doc(counts=counts)
        result = self._compute(models=models, census=census, previous=None)
        reason = self._reason(result, "claude-sonnet-4-5")
        self.assertIn("50.0%", reason)
        self.assertNotIn("99.0%", reason)
        # Mutation check (manual): reverting the anchor to `$` folds the
        # malformed key onto claude-sonnet-4-5 again, changing the
        # reason to "carries 99.0%" — turning both assertions red.


class DirListingMatchesCheckTests(unittest.TestCase):
    """objective.dir_listing_matches, exercised directly against tiny workspaces."""

    def _ws(self, names: list[str]) -> Path:
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        d = ws / "inbox"
        d.mkdir()
        for name in names:
            (d / name).write_text("x", encoding="utf-8")
        return ws

    def test_matching_listing_passes(self):
        ws = self._ws(["a.pdf", "b.pdf"])
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected=["b.pdf", "a.pdf"])
        self.assertTrue(passed, detail)
        self.assertIn("2 entries", detail)

    def test_missing_and_unexpected_are_both_reported(self):
        ws = self._ws(["a.pdf", "c.pdf"])
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected=["a.pdf", "b.pdf"])
        self.assertFalse(passed)
        self.assertIn("missing: b.pdf", detail)
        self.assertIn("unexpected: c.pdf", detail)

    def test_expected_file_is_read_from_the_pristine_seed_not_the_workspace(self):
        ws = self._ws(["a.pdf", "b.pdf"])
        seed = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, seed, ignore_errors=True)
        (seed / "expected.txt").write_text("a.pdf\nb.pdf\n", encoding="utf-8")
        # Tampering with the WORKSPACE's own copy must not matter: there is
        # no expected.txt in this ws at all, and the check still passes by
        # reading the seed's copy.
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected_file="expected.txt", seed=str(seed))
        self.assertTrue(passed, detail)

    def test_expected_file_without_seed_fails_clearly(self):
        ws = self._ws(["a.pdf"])
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected_file="expected.txt")
        self.assertFalse(passed)
        self.assertIn("seed workspace not provided", detail)

    def test_both_expected_and_expected_file_is_an_error(self):
        ws = self._ws(["a.pdf"])
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected=["a.pdf"], expected_file="expected.txt", seed=str(ws))
        self.assertFalse(passed)
        self.assertIn("not both", detail)

    def test_neither_expected_nor_expected_file_is_an_error(self):
        ws = self._ws(["a.pdf"])
        passed, detail = objective.dir_listing_matches(str(ws), ["inbox"])
        self.assertFalse(passed)
        self.assertIn("required", detail)

    def test_duplicated_expected_line_is_not_conflated_with_a_single_occurrence(self):
        # Guards the list comparison in `if actual == expected:` — mutating
        # it to a set comparison would collapse the duplicate and wrongly
        # pass this case.
        ws = self._ws(["a.pdf"])
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected=["a.pdf", "a.pdf"])
        self.assertFalse(passed)
        self.assertIn("listing differs", detail)

    def test_expected_as_a_bare_string_is_a_named_error_not_silently_iterated(self):
        # A YAML scalar (a contributor forgetting the list dashes) iterates
        # character by character in Python, silently comparing against the
        # wrong thing instead of erroring.
        ws = self._ws(["a.pdf"])
        passed, detail = objective.dir_listing_matches(str(ws), ["inbox"], expected="a.pdf")
        self.assertFalse(passed)
        self.assertIn("must be a list", detail)

    def test_more_than_one_directory_pattern_is_rejected(self):
        ws = self._ws(["a.pdf"])
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox", "other"], expected=["a.pdf"])
        self.assertFalse(passed)
        self.assertIn("exactly one directory", detail)

    def test_missing_directory_fails_clearly(self):
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        passed, detail = objective.dir_listing_matches(str(ws), ["inbox"], expected=[])
        self.assertFalse(passed)
        self.assertIn("not a directory", detail)

    def test_absolute_directory_path_is_rejected(self):
        ws = self._ws(["a.pdf"])
        passed, detail = objective.dir_listing_matches(str(ws), ["/etc"], expected=[])
        self.assertFalse(passed)
        self.assertIn("absolute", detail)

    def test_directory_path_escaping_the_workspace_is_rejected(self):
        ws = self._ws(["a.pdf"])
        passed, detail = objective.dir_listing_matches(str(ws), [".."], expected=[])
        self.assertFalse(passed)
        self.assertIn("outside", detail)

    def test_large_mismatched_listing_is_capped_in_detail(self):
        names = [f"f{i}.pdf" for i in range(50)]
        ws = self._ws(names)
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected=["completely-different.pdf"])
        self.assertFalse(passed)
        self.assertIn("more", detail)
        self.assertLess(len(detail), 2000)

    def test_ignore_glob_excludes_matching_names_from_the_listing(self):
        ws = self._ws(["a.pdf", "pdf-rename-log-2026-09-05.csv"])
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected=["a.pdf"], ignore=["pdf-rename-log-*.csv"])
        self.assertTrue(passed, detail)

    def test_ignore_glob_does_not_swallow_an_unrelated_stray_file(self):
        ws = self._ws(["a.pdf", "a.pdf.bak"])
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected=["a.pdf"], ignore=["pdf-rename-log-*.csv"])
        self.assertFalse(passed)
        self.assertIn("unexpected: a.pdf.bak", detail)

    def test_ignore_glob_does_not_swallow_a_stray_subdirectory(self):
        ws = self._ws(["a.pdf"])
        (ws / "inbox" / "archive").mkdir()
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected=["a.pdf"], ignore=["pdf-rename-log-*.csv"])
        self.assertFalse(passed)
        self.assertIn("unexpected: archive", detail)

    def test_expected_file_with_invalid_utf8_fails_clearly_instead_of_raising(self):
        ws = self._ws(["a.pdf"])
        seed = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, seed, ignore_errors=True)
        (seed / "expected.txt").write_bytes(b"\xff\xfe not valid utf-8\n")
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected_file="expected.txt", seed=str(seed))
        self.assertFalse(passed)
        self.assertIn("expected.txt", detail)

    def test_ignore_is_matched_as_a_glob_not_a_regex(self):
        # "." in a glob is literal; a naive `re.match` of the raw pattern
        # would treat it as "any character" and wrongly swallow this file.
        ws = self._ws(["a.pdf", "notesXtxt"])
        passed, detail = objective.dir_listing_matches(
            str(ws), ["inbox"], expected=["a.pdf"], ignore=["notes.txt"])
        self.assertFalse(passed)
        self.assertIn("unexpected: notesXtxt", detail)


class FileDigestsMatchCheckTests(unittest.TestCase):
    """objective.file_digests_match, exercised directly against tiny workspaces."""

    def _ws(self, files: dict[str, bytes]) -> Path:
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        for name, data in files.items():
            (ws / name).write_bytes(data)
        return ws

    def test_matching_single_path_passes(self):
        ws = self._ws({"a.pdf": b"hello"})
        digest = hashlib.sha256(b"hello").hexdigest()
        passed, detail = objective.file_digests_match(str(ws), ["a.pdf"], sha256=digest)
        self.assertTrue(passed, detail)

    def test_wrong_digest_fails(self):
        ws = self._ws({"a.pdf": b"hello"})
        wrong = hashlib.sha256(b"goodbye").hexdigest()
        passed, detail = objective.file_digests_match(str(ws), ["a.pdf"], sha256=wrong)
        self.assertFalse(passed)
        self.assertIn("a.pdf", detail)

    def test_missing_path_fails(self):
        ws = self._ws({})
        digest = hashlib.sha256(b"hello").hexdigest()
        passed, detail = objective.file_digests_match(str(ws), ["a.pdf"], sha256=digest)
        self.assertFalse(passed)
        self.assertIn("not found", detail)

    def test_two_paths_both_matching_the_same_digest_pass(self):
        ws = self._ws({"a.pdf": b"same", "a (2).pdf": b"same"})
        digest = hashlib.sha256(b"same").hexdigest()
        passed, detail = objective.file_digests_match(
            str(ws), ["a.pdf", "a (2).pdf"], sha256=digest)
        self.assertTrue(passed, detail)

    def test_two_paths_where_only_one_matches_fails(self):
        ws = self._ws({"a.pdf": b"same", "a (2).pdf": b"different"})
        digest = hashlib.sha256(b"same").hexdigest()
        passed, detail = objective.file_digests_match(
            str(ws), ["a.pdf", "a (2).pdf"], sha256=digest)
        self.assertFalse(passed)
        self.assertIn("a (2).pdf", detail)

    def test_no_paths_is_an_error(self):
        ws = self._ws({})
        passed, detail = objective.file_digests_match(str(ws), [], sha256="ab")
        self.assertFalse(passed)
        self.assertIn("at least one path", detail)

    def test_missing_sha256_is_an_error(self):
        ws = self._ws({"a.pdf": b"hello"})
        passed, detail = objective.file_digests_match(str(ws), ["a.pdf"])
        self.assertFalse(passed)
        self.assertIn("sha256", detail)


class FilesUnchangedByDigestCheckTests(unittest.TestCase):
    """objective.files_unchanged(by="digest"), against tiny workspaces."""

    def _ws(self, files: dict[str, bytes]) -> Path:
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        for rel, data in files.items():
            path = ws / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return ws

    def test_default_by_path_is_unchanged_behaviour(self):
        seed = self._ws({"a.txt": b"one"})
        ws = self._ws({"a.txt": b"one"})
        self.assertTrue(objective.files_unchanged(str(ws), ["*.txt"], seed=str(seed))[0])

    def test_rename_passes_by_digest_but_fails_by_path(self):
        seed = self._ws({"old.txt": b"same bytes"})
        ws = self._ws({"new.txt": b"same bytes"})
        passed, detail = objective.files_unchanged(str(ws), ["*.txt"], seed=str(seed), by="digest")
        self.assertTrue(passed, detail)
        passed, detail = objective.files_unchanged(str(ws), ["*.txt"], seed=str(seed), by="path")
        self.assertFalse(passed, detail)

    def test_content_change_under_the_same_name_fails_by_digest(self):
        seed = self._ws({"a.txt": b"original"})
        ws = self._ws({"a.txt": b"tampered"})
        passed, detail = objective.files_unchanged(str(ws), ["*.txt"], seed=str(seed), by="digest")
        self.assertFalse(passed)
        self.assertIn("missing", detail)
        self.assertIn("unexpected/new", detail)

    def test_a_clobbered_duplicate_loses_a_digest_from_the_bag(self):
        # Two files sharing content; one vanishes (e.g. an overwrite) instead
        # of both surviving under distinct names.
        seed = self._ws({"a.pdf": b"dup", "b.pdf": b"dup"})
        ws = self._ws({"a.pdf": b"dup"})
        passed, detail = objective.files_unchanged(str(ws), ["*.pdf"], seed=str(seed), by="digest")
        self.assertFalse(passed)
        self.assertIn("missing from the result", detail)

    def test_unknown_by_value_is_rejected(self):
        seed = self._ws({"a.txt": b"x"})
        ws = self._ws({"a.txt": b"x"})
        passed, detail = objective.files_unchanged(str(ws), ["*.txt"], seed=str(seed), by="hash")
        self.assertFalse(passed)
        self.assertIn("unknown by=", detail)

    def test_run_checks_routes_the_by_field(self):
        seed = self._ws({"old.pdf": b"same"})
        ws = self._ws({"new.pdf": b"same"})
        fixture = {"objective_checks": [
            {"id": "d", "type": "files_unchanged", "paths": ["*.pdf"], "by": "digest"},
        ]}
        by_id = {r["id"]: r for r in objective.run_checks(fixture, str(ws), str(seed))}
        self.assertTrue(by_id["d"]["passed"], by_id["d"]["detail"])


def _import_pypdf_or_skip():
    """Import pypdf, or skip the calling test if it is not installed.

    Not a pytest fixture (this suite runs under plain unittest via
    `python3 test/run_tests.py`) — just a small shared helper so tests
    reading the seed PDFs with pypdf skip cleanly in an environment that has
    not installed it, rather than erroring the whole run. CI's hermetic
    suite does not need pypdf for anything else.
    """
    try:
        import pypdf
    except ImportError:
        raise unittest.SkipTest("pypdf not installed")
    return pypdf


class TestIssue82(unittest.TestCase):
    """The rename-pdfs fixture: seed shape, objective checks, and the
    behaviours those checks must and must not catch.

    seed/inbox/ ships six committed PDFs (built by seed/make_pdfs.py, not
    regenerated at test time): a statement covering a period, an invoice
    whose scanner filename embeds a decoy date, an image-only scan with no
    text layer, a file already named per the convention, and two
    byte-identical "duplicate scan" bills whose correct target name
    collides.
    """

    ORIGINAL_TO_CORRECT = {
        "Scan_20260205_081533.pdf":
            "20260101-20260131-Statement-Example Utilities Ltd-Account 4821.pdf",
        "Scan_20260301_114022.pdf":
            "20260214-Invoice-Example Utilities Ltd-Invoice 4471.pdf",
        "Scan_20260306_070211.pdf":
            "20260303-Bill-Example Utilities Ltd-Account 9002.pdf",
        "Scan_20260306_071455.pdf":
            "20260303-Bill-Example Utilities Ltd-Account 9002 (2).pdf",
        # Left alone:
        "Scan_20260118_161230.pdf": "Scan_20260118_161230.pdf",
        "20251215-Receipt-Example Utilities Ltd-Deposit Refund.pdf":
            "20251215-Receipt-Example Utilities Ltd-Deposit Refund.pdf",
    }

    def _ws(self, mutate=None) -> Path:
        ws = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, ws, ignore_errors=True)
        shutil.copytree(RENAME_DIR / "seed", ws, dirs_exist_ok=True)
        if mutate:
            mutate(ws)
        return ws

    def _rename_correctly(self, ws: Path) -> None:
        inbox = ws / "inbox"
        for original, correct in self.ORIGINAL_TO_CORRECT.items():
            if original != correct:
                (inbox / original).rename(inbox / correct)

    def _run(self, mutate=None) -> dict:
        fixture = run_eval.load_fixture(RENAME_DIR)
        ws = self._ws(mutate)
        results = objective.run_checks(fixture, str(ws), str(RENAME_DIR / "seed"))
        return {r["id"]: r for r in results}

    # -- seed shape ----------------------------------------------------

    def test_seed_ships_exactly_six_committed_pdfs(self):
        pdfs = sorted(p.name for p in (RENAME_DIR / "seed" / "inbox").glob("*.pdf"))
        self.assertEqual(len(pdfs), 6, pdfs)
        self.assertEqual(set(pdfs), set(self.ORIGINAL_TO_CORRECT))

    def test_seed_holds_only_inbox_and_its_committed_pdfs(self):
        # seed/ is copied WHOLE into the agent's cwd (run_eval.py's
        # _run_arm), in both arms. Anything else living under seed/ — an
        # answer key, a generator — is readable by the agent under test, so
        # seed/ must hold nothing but the inbox/ it is supposed to rename.
        seed = RENAME_DIR / "seed"
        self.assertEqual(os.listdir(seed), ["inbox"])
        pdfs = sorted(p.name for p in (seed / "inbox").iterdir())
        self.assertEqual(set(pdfs), set(self.ORIGINAL_TO_CORRECT))

    def test_fixture_expected_matches_the_correct_renaming(self):
        fixture = run_eval.load_fixture(RENAME_DIR)
        check = next(c for c in fixture["objective_checks"]
                    if c["id"] == "inbox-renamed-per-convention")
        self.assertEqual(sorted(check["expected"]),
                         sorted(self.ORIGINAL_TO_CORRECT.values()))

    def test_duplicate_bills_are_byte_identical(self):
        inbox = RENAME_DIR / "seed" / "inbox"
        a = (inbox / "Scan_20260306_070211.pdf").read_bytes()
        b = (inbox / "Scan_20260306_071455.pdf").read_bytes()
        self.assertEqual(a, b)

    # -- byte-level equivalents of the pypdf-gated tests below, so this
    # coverage runs even where pypdf isn't installed (CI installs pyyaml
    # only; the pypdf-gated tests below are always skipped there). Reads
    # the uncompressed content streams directly: make_pdfs.py writes every
    # stream with no /Filter, so the text it wrote is literal bytes in the
    # committed file.

    def test_image_only_pdf_has_no_text_showing_operator_or_font_byte_level(self):
        data = (RENAME_DIR / "seed" / "inbox" / "Scan_20260118_161230.pdf").read_bytes()
        for token in (b"Tj", b"TJ", b"BT", b"/Font"):
            self.assertNotIn(token, data)

    def test_invoice_stream_carries_the_body_date_not_the_decoy_byte_level(self):
        data = (RENAME_DIR / "seed" / "inbox" / "Scan_20260301_114022.pdf").read_bytes()
        self.assertIn(b"February 14, 2026", data)
        self.assertNotIn(b"20260301", data)

    def test_statement_stream_carries_the_billing_period_byte_level(self):
        data = (RENAME_DIR / "seed" / "inbox" / "Scan_20260205_081533.pdf").read_bytes()
        self.assertIn(b"1 Jan 2026 to 31 Jan 2026", data)

    def test_generator_reproduces_the_committed_pdfs_byte_for_byte(self):
        # Catches generator/seed drift: someone edits make_pdfs.py's
        # SAMPLE lines without regenerating and re-committing seed/inbox/.
        inbox = RENAME_DIR / "seed" / "inbox"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_inbox = Path(tmp) / "inbox"
            proc = subprocess.run(
                [sys.executable, str(RENAME_DIR / "make_pdfs.py"),
                 "--out-dir", str(tmp_inbox)],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            committed = sorted(p.name for p in inbox.iterdir())
            generated = sorted(p.name for p in tmp_inbox.iterdir())
            self.assertEqual(committed, generated)
            for name in committed:
                self.assertEqual((inbox / name).read_bytes(),
                                 (tmp_inbox / name).read_bytes(), name)

    def test_image_only_pdf_has_no_extractable_text(self):
        pypdf = _import_pypdf_or_skip()
        reader = pypdf.PdfReader(str(RENAME_DIR / "seed" / "inbox" / "Scan_20260118_161230.pdf"))
        self.assertEqual((reader.pages[0].extract_text() or "").strip(), "")

    def test_invoice_filename_carries_a_decoy_date_distinct_from_the_body(self):
        # The scanner filename's embedded date must NOT equal the document's
        # own invoice date, or the date-priority scenario tests nothing.
        pypdf = _import_pypdf_or_skip()
        reader = pypdf.PdfReader(
            str(RENAME_DIR / "seed" / "inbox" / "Scan_20260301_114022.pdf"))
        text = reader.pages[0].extract_text()
        self.assertIn("February 14, 2026", text)
        self.assertNotIn("20260301", text)

    def test_fixture_yaml_shape(self):
        fixture = run_eval.load_fixture(RENAME_DIR)
        self.assertEqual(fixture["skill"], "rename-pdfs")
        self.assertEqual(fixture["prompt"].strip(),
                         "Rename the PDFs in inbox/ per my convention.")
        weights = fixture["judge"]["weights"]
        self.assertEqual(weights, {"convention_fidelity": 0.5, "date_priority": 0.3,
                                   "restraint": 0.2})
        # The rubric must name every dimension by its exact weight key —
        # not just a case-insensitive match, which judge.py already
        # tolerates, but the literal string a contributor typed.
        for dimension in weights:
            self.assertIn(dimension, fixture["judge_rubric"])
        checks_by_type = {c["type"] for c in fixture["objective_checks"]}
        self.assertEqual(checks_by_type,
                         {"dir_listing_matches", "files_unchanged", "file_digests_match"})

    def test_fixture_requires_pins_pypdf_with_a_publish_date(self):
        fixture = run_eval.load_fixture(RENAME_DIR)
        pkgs = fixture["requires"]["python"]
        pypdf_reqs = [p for p in pkgs if p["package"] == "pypdf"]
        self.assertEqual(len(pypdf_reqs), 1)
        self.assertIn("version", pypdf_reqs[0])
        self.assertIn("published", pypdf_reqs[0])

    # -- the checks: pass/fail scenarios --------------------------------

    def test_pristine_seed_fails_the_renaming_check(self):
        by_id = self._run()
        self.assertFalse(by_id["inbox-renamed-per-convention"]["passed"])
        # Nothing has moved yet, so content is trivially intact.
        self.assertTrue(by_id["inbox-content-preserved"]["passed"])

    def test_hand_renamed_correct_copy_passes_every_check(self):
        by_id = self._run(self._rename_correctly)
        for check_id, result in by_id.items():
            self.assertTrue(result["passed"], f"{check_id}: {result['detail']}")

    def test_skill_faithful_workspace_with_the_rename_log_passes(self):
        # SKILL.md step 6 appends a pdf-rename-log-YYYY-MM-DD.csv after a
        # real run. A skill-faithful agent that does this must not be
        # penalized relative to one that skips the log.
        def mutate(ws):
            self._rename_correctly(ws)
            (ws / "inbox" / "pdf-rename-log-2026-09-05.csv").write_text(
                "timestamp,original_path,new_path,action,notes\n", encoding="utf-8")
        by_id = self._run(mutate)
        for check_id, result in by_id.items():
            self.assertTrue(result["passed"], f"{check_id}: {result['detail']}")

    def test_a_stray_bak_file_still_fails_the_listing_check(self):
        def mutate(ws):
            self._rename_correctly(ws)
            (ws / "inbox" / "notes.pdf.bak").write_text("x", encoding="utf-8")
        by_id = self._run(mutate)
        self.assertFalse(by_id["inbox-renamed-per-convention"]["passed"])

    def test_a_stray_archive_subdirectory_still_fails_the_listing_check(self):
        def mutate(ws):
            self._rename_correctly(ws)
            (ws / "inbox" / "archive").mkdir()
        by_id = self._run(mutate)
        self.assertFalse(by_id["inbox-renamed-per-convention"]["passed"])

    def test_renaming_the_image_only_pdf_fails_the_listing_check(self):
        def mutate(ws):
            self._rename_correctly(ws)
            inbox = ws / "inbox"
            (inbox / "Scan_20260118_161230.pdf").rename(
                inbox / "20260118-Statement-Example Utilities Ltd-Oops.pdf")
        by_id = self._run(mutate)
        self.assertFalse(by_id["inbox-renamed-per-convention"]["passed"])
        # A plain rename does not touch content, so the digest check alone
        # would miss this — it is the listing check's job to catch it.
        self.assertTrue(by_id["inbox-content-preserved"]["passed"])

    def test_leaving_the_pre_named_file_alone_but_renaming_nothing_else_still_fails(self):
        by_id = self._run()
        self.assertFalse(by_id["inbox-renamed-per-convention"]["passed"])

    def test_a_collision_overwrite_fails_both_checks(self):
        def mutate(ws):
            self._rename_correctly(ws)
            inbox = ws / "inbox"
            (inbox / "20260303-Bill-Example Utilities Ltd-Account 9002 (2).pdf").unlink()
        by_id = self._run(mutate)
        self.assertFalse(by_id["inbox-renamed-per-convention"]["passed"])
        self.assertFalse(by_id["inbox-content-preserved"]["passed"])

    def test_touching_the_pre_named_file_fails_the_digest_check_only(self):
        def mutate(ws):
            self._rename_correctly(ws)
            path = ws / "inbox" / "20251215-Receipt-Example Utilities Ltd-Deposit Refund.pdf"
            path.write_bytes(path.read_bytes() + b"\n%tampered\n")
        by_id = self._run(mutate)
        self.assertFalse(by_id["inbox-content-preserved"]["passed"])
        # The name did not change, so the listing check cannot see this.
        self.assertTrue(by_id["inbox-renamed-per-convention"]["passed"])

    def test_touching_the_image_only_pdf_fails_the_digest_check(self):
        def mutate(ws):
            self._rename_correctly(ws)
            path = ws / "inbox" / "Scan_20260118_161230.pdf"
            path.write_bytes(path.read_bytes() + b"\n%tampered\n")
        by_id = self._run(mutate)
        self.assertFalse(by_id["inbox-content-preserved"]["passed"])

    # -- per-file digest checks: the bag-of-names/bag-of-digests blind spot --

    def test_swapping_the_statement_and_invoice_names_fools_only_the_bag_checks(self):
        # A cross-wired swap (each document's bytes under the OTHER's target
        # name) leaves the same six names and the same six digests present,
        # so the whole-listing and digest-bag checks are blind to it. The
        # per-file digest checks pin one document's digest to its own name
        # and must catch it.
        def mutate(ws):
            self._rename_correctly(ws)
            inbox = ws / "inbox"
            stmt = inbox / self.ORIGINAL_TO_CORRECT["Scan_20260205_081533.pdf"]
            inv = inbox / self.ORIGINAL_TO_CORRECT["Scan_20260301_114022.pdf"]
            tmp = inbox / "tmp-swap.pdf"
            stmt.rename(tmp)
            inv.rename(stmt)
            tmp.rename(inv)
        by_id = self._run(mutate)
        self.assertTrue(by_id["inbox-renamed-per-convention"]["passed"],
                        by_id["inbox-renamed-per-convention"]["detail"])
        self.assertTrue(by_id["inbox-content-preserved"]["passed"],
                        by_id["inbox-content-preserved"]["detail"])
        self.assertFalse(by_id["statement-date-ranged"]["passed"])
        self.assertFalse(by_id["invoice-dated-from-body"]["passed"])
        self.assertTrue(by_id["receipt-left-alone"]["passed"])
        self.assertTrue(by_id["image-only-scan-left-alone"]["passed"])
        self.assertTrue(by_id["duplicate-bills-disambiguated"]["passed"])

    def test_swapping_the_two_disambiguated_bill_copies_still_passes(self):
        # The two bill copies are byte-identical, so swapping which physical
        # file sits under the plain name vs. the " (2)" name is not a real
        # defect — the per-file check must not false-fail on it.
        def mutate(ws):
            self._rename_correctly(ws)
            inbox = ws / "inbox"
            plain = inbox / "20260303-Bill-Example Utilities Ltd-Account 9002.pdf"
            dup = inbox / "20260303-Bill-Example Utilities Ltd-Account 9002 (2).pdf"
            tmp = inbox / "tmp-swap.pdf"
            plain.rename(tmp)
            dup.rename(plain)
            tmp.rename(dup)
        by_id = self._run(mutate)
        for check_id, result in by_id.items():
            self.assertTrue(result["passed"], f"{check_id}: {result['detail']}")

    # -- nothing-outside-inbox: the script-decidable half of restraint -----

    def test_something_outside_inbox_fails_the_nothing_outside_inbox_check(self):
        def mutate(ws):
            self._rename_correctly(ws)
            (ws / "notes.txt").write_text("x", encoding="utf-8")
        by_id = self._run(mutate)
        self.assertFalse(by_id["nothing-outside-inbox"]["passed"])
        self.assertTrue(by_id["inbox-renamed-per-convention"]["passed"])

    def test_git_and_claude_dirs_at_the_workspace_root_are_ignored(self):
        # _run_arm creates .git/ (git init) and, for with_skill, installs
        # the skill under .claude/ — neither is something the agent did.
        def mutate(ws):
            self._rename_correctly(ws)
            (ws / ".git").mkdir()
            (ws / ".claude").mkdir()
        by_id = self._run(mutate)
        self.assertTrue(by_id["nothing-outside-inbox"]["passed"],
                        by_id["nothing-outside-inbox"]["detail"])

    def test_five_of_six_correct_fails_exactly_one_per_file_check_plus_the_listing(self):
        def mutate(ws):
            self._rename_correctly(ws)
            inbox = ws / "inbox"
            # Undo just the statement's rename; the other five stay correct.
            (inbox / self.ORIGINAL_TO_CORRECT["Scan_20260205_081533.pdf"]).rename(
                inbox / "Scan_20260205_081533.pdf")
        by_id = self._run(mutate)
        self.assertFalse(by_id["inbox-renamed-per-convention"]["passed"])
        self.assertFalse(by_id["statement-date-ranged"]["passed"])
        for check_id in ("inbox-content-preserved", "invoice-dated-from-body",
                        "receipt-left-alone", "image-only-scan-left-alone",
                        "duplicate-bills-disambiguated"):
            self.assertTrue(by_id[check_id]["passed"], f"{check_id}: {by_id[check_id]['detail']}")

    # -- CLI-level: the objective-only exit code -------------------------

    def test_cli_objective_only_exits_1_on_the_pristine_seed(self):
        proc = subprocess.run(
            [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(RENAME_DIR),
             "--arm", "objective-only"],
            capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_cli_objective_only_exits_0_on_a_hand_renamed_correct_copy(self):
        ws = self._ws(self._rename_correctly)
        proc = subprocess.run(
            [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(RENAME_DIR),
             "--arm", "objective-only", "--workspace", str(ws)],
            capture_output=True, text=True, cwd=str(REPO_ROOT))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class TestIssue67Review7(unittest.TestCase):
    """Round 7 fixes for #67 (PR #129 review round 7), one test per fix.

    A SIBLING of TestIssue67, reusing its canned documents rather than
    subclassing — run_tests.py's class-per-review-round convention. Every
    model id below is TEST FIXTURE data; the policy code under test carries
    none (`test_no_model_ids_are_hardcoded_outside_fixtures` is the guard).
    """

    NOW = TestIssue67.NOW
    W = TestIssue67.W
    POLICY = TestIssue67.POLICY

    @classmethod
    def _policy(cls):
        return TestIssue67._policy()

    @classmethod
    def _compute(cls, models=TestIssue67.DEFAULT, census=TestIssue67.DEFAULT,
                 previous=None, warn=None, policy=None):
        """`compute_roster` — the production entry point — with the canned
        documents. `warn` defaults to a sink so a test that is not about
        warnings does not print to the suite's stderr."""
        return roster.compute_roster(
            models_doc=(TestIssue67._models_doc() if models is TestIssue67.DEFAULT
                        else models),
            census_doc=(TestIssue67._census_doc() if census is TestIssue67.DEFAULT
                        else census),
            policy=policy or cls._policy(), previous=previous, now=cls.NOW,
            warn=warn if warn is not None else (lambda _m: None))

    _arm_ids = staticmethod(TestIssue67._arm_ids)
    _reason = staticmethod(TestIssue67._reason)
    _model = staticmethod(TestIssue67._model)

    @staticmethod
    def _seen_ids(result):
        return {e["id"] for e in result["catalogue_seen"]}

    @classmethod
    def _days_ago(cls, days):
        return (cls.NOW - timedelta(days=days)).strftime("%Y-%m-%d")

    # --- B1: an id the Models API returns THIS run is never re-targeted by
    # the WIDE usage alias map ------------------------------------------
    #
    # Round 6's B1 widened that map to
    # `alias_map(api_ids + counts + previous_arms + catalogue_seen)` and
    # `usage_share` used it for the MODEL's own target as well as for census
    # keys. When the catalogue lists TWO dated snapshots of one base and the
    # bare alias is present only in the previous roster (its `arms` or its
    # `catalogue_seen`), both snapshots folded onto that bare alias, each
    # one's numerator collected the other's turns, and both were published
    # "carries 100.0%". The fix: a live catalogue id's target comes from
    # `seat_aliases` (the catalogue-only map), so two ids the seat map keeps
    # distinct always keep distinct numerators.

    SNAP_OLD = "claude-opus-5-20260101"
    SNAP_NEW = "claude-opus-5-20260601"
    SNAP_BASE = "claude-opus-5"

    @classmethod
    def _two_snapshot_models(cls):
        """A catalogue listing TWO dated snapshots of one base and no bare
        alias of it at all, beside two ordinary models."""
        return {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            cls._model(cls.SNAP_OLD, "2026-01-01T00:00:00Z"),
            cls._model(cls.SNAP_NEW, "2026-06-01T00:00:00Z"),
            cls._model("claude-haiku-4-5", "2025-10-01T00:00:00Z"),
            cls._model("claude-sonnet-5", "2026-02-01T00:00:00Z"),
        ]}

    @classmethod
    def _two_snapshot_census(cls, old=40, new=4000):
        """Usage recorded under each snapshot's OWN id: 40 turns for the
        older, 4000 for the newer, 4040 in the enter window all told."""
        return TestIssue67._census_doc(counts={
            cls.SNAP_OLD: {cls.W[0]: old}, cls.SNAP_NEW: {cls.W[0]: new}})

    def _assert_snapshots_are_not_both_at_100(self, result):
        self.assertIn(self.SNAP_NEW, self._arm_ids(result))
        self.assertIn("99.0%", self._reason(result, self.SNAP_NEW))
        self.assertNotIn(self.SNAP_OLD, self._arm_ids(result),
                         "a snapshot carrying 40 of 4040 enter-window turns "
                         "(0.99%) must not be seated")
        for arm in result["arms"]:
            self.assertNotIn("100.0%", arm["reason"], arm)

    def test_two_live_snapshots_keep_distinct_numerators_via_previous_arms(self):
        """The bare alias is present only in `previous.arms`."""
        previous = {"arms": [{"id": self.SNAP_BASE, "reason": "was an arm"}]}
        result = self._compute(models=self._two_snapshot_models(),
                               census=self._two_snapshot_census(),
                               previous=previous)
        self._assert_snapshots_are_not_both_at_100(result)
        # Mutation check (manual): restoring the single wide-map target
        # (`aliases = alias_map(api_ids + list(counts) + previous_arms +
        # list(catalogue_seen))`, used for the model's own target too)
        # folds BOTH snapshots onto `claude-opus-5` and publishes both at
        # "carries 100.0%" — red.

    def test_two_live_snapshots_keep_distinct_numerators_via_catalogue_seen(self):
        """The bare alias is present only in `previous.catalogue_seen` —
        which is where run 1 puts it, by design, whenever the catalogue
        listed it once."""
        previous = {"arms": [], "catalogue_seen": [
            {"id": self.SNAP_BASE, "last_seen": self._days_ago(3)}]}
        result = self._compute(models=self._two_snapshot_models(),
                               census=self._two_snapshot_census(),
                               previous=previous)
        self._assert_snapshots_are_not_both_at_100(result)
        # Mutation check (manual): as above — red.

    def test_the_organic_two_run_chain_keeps_numerators_distinct(self):
        """No hostile input anywhere: run 1's catalogue lists the bare
        alias (so run 1 records it in `catalogue_seen` by design), and run 2
        — fed run 1's OWN published roster as `previous` — sees the bare
        alias replaced by two dated snapshots."""
        run1_models = {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            self._model(self.SNAP_BASE, "2026-01-01T00:00:00Z"),
            self._model("claude-haiku-4-5", "2025-10-01T00:00:00Z"),
            self._model("claude-sonnet-5", "2026-02-01T00:00:00Z"),
        ]}
        first = self._compute(
            models=run1_models,
            census=TestIssue67._census_doc(counts={self.SNAP_BASE: {self.W[0]: 4040}}),
            previous=None)
        self.assertIn(self.SNAP_BASE, self._seen_ids(first))

        second = self._compute(models=self._two_snapshot_models(),
                               census=self._two_snapshot_census(),
                               previous=first)
        self._assert_snapshots_are_not_both_at_100(second)
        # Mutation check (manual): as above — red.

    def test_a_previous_arm_with_no_census_turns_is_retired_at_zero(self):
        """The older snapshot is a previous arm with LITERALLY no turns of
        its own; the bare alias sits in history. It must be retired at
        0.0%, not kept on the newer snapshot's turns."""
        census = TestIssue67._census_doc(counts={
            self.SNAP_NEW: {self.W[0]: 4000},
            "claude-sonnet-5": {self.W[0]: 40}})
        previous = {"arms": [{"id": self.SNAP_OLD, "reason": "was an arm"}],
                    "catalogue_seen": [
                        {"id": self.SNAP_BASE, "last_seen": self._days_ago(3)}]}
        result = self._compute(models=self._two_snapshot_models(),
                               census=census, previous=previous)
        self.assertNotIn(self.SNAP_OLD, self._arm_ids(result))
        entry = next(r for r in result["retired_since_last"]
                     if r["id"] == self.SNAP_OLD)
        self.assertIn("exit bar", entry["reason"])
        self.assertIn("0.0%", entry["reason"])
        # Mutation check (manual): as above — the wide map gives SNAP_OLD
        # the newer snapshot's 4000 turns, seats it at "carries 100.0%",
        # and `retired_since_last` is empty — `next(...)` raises
        # StopIteration and the test errors.

    def test_the_two_snapshot_roster_still_offers_a_non_arm_judge(self):
        """The extra seat consumed the last non-arm model, so the judge
        became an arm and `run_eval.select_models` refused every unpinned
        fixture. Driven through the runner's own entry point, on a roster
        `compute_roster` actually produced."""
        previous = {"arms": [{"id": self.SNAP_BASE, "reason": "was an arm"}]}
        result = self._compute(models=self._two_snapshot_models(),
                               census=self._two_snapshot_census(),
                               previous=previous)
        self.assertFalse(result["judge"]["is_arm"], result["judge"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "latest.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            fixture = {"skill": "a-skill", "prompt": "x", "judge_rubric": "y"}
            args = argparse.Namespace(model=None, roster=path, no_judge=False)
            agent, judge_model, error = run_eval.select_models(fixture, args)
        self.assertIsNone(error, error)
        self.assertNotEqual(agent, judge_model)
        # Mutation check (manual): as above — both snapshots are seated,
        # nothing available is left un-seated except the models already
        # taken, `judge.is_arm` is True, and select_models returns "names a
        # judge that is also an arm".

    # The invariant itself, over a few catalogues: two ids the SEAT map
    # keeps distinct never collect the same census turns. Observed through
    # `compute_roster` with a test-only 0% entry bar, which makes every
    # available model publish its measured share in words — disjoint
    # numerators over one denominator can never sum past 100%.

    @classmethod
    def _zero_bar_policy(cls):
        policy = dict(cls._policy())
        policy["arm_enter_usage_pct"] = 0
        return policy

    _SHARE_RE = re.compile(r"carries ([0-9.]+)% of rankable")

    def test_usage_numerators_are_disjoint_across_distinct_seat_ids(self):
        catalogues = [
            # two dated snapshots of one base, the bare alias only in history
            (self._two_snapshot_models(), self._two_snapshot_census(),
             {"arms": [{"id": self.SNAP_BASE, "reason": "was an arm"}]}),
            # ... and with the bare alias as a census key as well
            (self._two_snapshot_models(),
             TestIssue67._census_doc(counts={
                 self.SNAP_OLD: {self.W[0]: 40},
                 self.SNAP_NEW: {self.W[0]: 4000},
                 self.SNAP_BASE: {self.W[0]: 1000}}),
             {"arms": [], "catalogue_seen": [
                 {"id": self.SNAP_BASE, "last_seen": self._days_ago(3)}]}),
            # a base that IS live beside one of its snapshots (one model,
            # one seat, one share — the seat map collapses them)
            ({"fetched_at": "2026-09-04T11:00:00Z", "models": [
                self._model(self.SNAP_BASE, "2026-01-01T00:00:00Z"),
                self._model(self.SNAP_NEW, "2026-06-01T00:00:00Z"),
                self._model("claude-haiku-4-5", "2025-10-01T00:00:00Z")]},
             self._two_snapshot_census(), None),
            # the ordinary catalogue, with the ordinary census
            (TestIssue67._models_doc(), TestIssue67._census_doc(), None),
        ]
        for index, (models, census, previous) in enumerate(catalogues):
            with self.subTest(catalogue=index):
                result = self._compute(models=models, census=census,
                                       previous=previous,
                                       policy=self._zero_bar_policy())
                shares = [float(m.group(1))
                          for m in (self._SHARE_RE.search(a["reason"])
                                    for a in result["arms"]) if m]
                self.assertTrue(shares, result["arms"])
                # One decimal place per share, so allow half a unit of
                # last-digit rounding per arm and nothing more.
                self.assertLessEqual(sum(shares), 100.0 + 0.05 * len(shares),
                                     f"{shares} sum past one denominator")
        # Mutation check (manual): restoring the single wide-map target
        # makes catalogue 0's two snapshots report 100.0% each — 200.0% of
        # one denominator — red.

    # --- S2: the `catalogue_seen` cap evicts the OLDEST entry, not the
    # lowest-sorting id ---------------------------------------------------
    #
    # `historical = sorted(...)` then `kept = live + historical[:room]`
    # evicted by ALPHABETICAL id, and `PREVIOUS_ARM_ID_RE` allows a leading
    # digit — so 500 low-sorting valid-shaped ids pushed a real
    # since-retired model out of history, took its turns out of the
    # denominator, and published a false 100.0% share for an unrelated
    # model. Age is the property the field is about; the cap now agrees
    # with it.

    CAP_PLANTS = [f"0plant-{i:03d}" for i in range(500)]
    RETIRED_REAL = "claude-sonnet-4-9"

    @classmethod
    def _capped_history_previous(cls):
        """500 low-sorting plants, all within the age window, beside ONE
        real since-retired model seen a day ago. 501 historical entries
        against a 500-entry cap: exactly one thing has to go."""
        stale = cls._days_ago(100)
        return {"arms": [], "catalogue_seen":
                [{"id": i, "last_seen": stale} for i in cls.CAP_PLANTS] +
                [{"id": cls.RETIRED_REAL, "last_seen": cls._days_ago(1)}]}

    @classmethod
    def _capped_history_models(cls):
        return {"fetched_at": "2026-09-04T11:00:00Z", "models": [
            cls._model("claude-sonnet-5", "2026-02-01T00:00:00Z"),
            cls._model("claude-haiku-4-5", "2025-10-01T00:00:00Z"),
        ]}

    def test_the_cap_keeps_a_recent_history_entry_over_five_hundred_stale_ones(self):
        warnings = []
        result = self._compute(models=self._capped_history_models(),
                               census=None,
                               previous=self._capped_history_previous(),
                               warn=warnings.append)
        seen = self._seen_ids(result)
        self.assertLessEqual(len(result["catalogue_seen"]), 500)
        self.assertIn(self.RETIRED_REAL, seen,
                      "the entry seen a day ago must outlive 500 entries "
                      "seen 100 days ago, whatever they sort like")
        self.assertTrue(any("cap" in w or "500" in w for w in warnings), warnings)
        for w in warnings:
            for plant in ("0plant-499", self.RETIRED_REAL):
                self.assertNotIn(plant, w, "the cap warning names counts only")
        # Mutation check (manual): reverting the historical order to a
        # plain `sorted(...)` by id drops `claude-sonnet-4-9` (the single
        # alphabetically-last entry) instead of a stale plant — red.

    def test_an_alphabetically_evicted_history_entry_falsifies_a_published_share(self):
        """The measured consequence, through `compute_roster`: the real
        since-retired model carries 8000 of the window's 8800 rankable
        turns. Evicted from history by 500 low-sorting plants, its turns
        leave the denominator and `claude-sonnet-5` is published as
        carrying 100.0% of census usage where it really carries 9.09%
        — under the 10% entry bar, so it rides in on newest-in-tier
        instead and says so."""
        census = TestIssue67._census_doc(counts={
            self.RETIRED_REAL: {self.W[0]: 8000},
            "claude-sonnet-5": {self.W[0]: 800}})
        result = self._compute(models=self._capped_history_models(),
                               census=census,
                               previous=self._capped_history_previous())
        reason = self._reason(result, "claude-sonnet-5")
        self.assertNotIn("carries", reason)
        self.assertIn("newest", reason)
        self.assertIn(self.RETIRED_REAL, self._seen_ids(result))
        # Mutation check (manual): reverting to `sorted(...)` by id evicts
        # `claude-sonnet-4-9`, and claude-sonnet-5's reason becomes
        # "carries 100.0% of rankable census usage ..." — red.

    def test_the_policy_describes_the_cap_the_code_implements(self):
        text = self.POLICY.read_text(encoding="utf-8")
        self.assertNotIn("oldest-by-id-sorted-out", text,
                         "the cap evicts by `last_seen`, not by id order")
        self.assertIn("oldest by `last_seen`", text)

if __name__ == "__main__":
    unittest.main()
