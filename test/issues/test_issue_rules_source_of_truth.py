#!/usr/bin/env python3
"""The rules' source of truth: evals/*-policy.yml, rendered by
scripts/build_rules.py into docs/rules.md and docs/rules.json, and enforced
by scripts/check_rule_restatements.py.

What is pinned here:

  * build_rules: the committed page and JSON are current (`--check` exits 0);
    `--check` fails on a scratch copy whose YAML changed and passes once
    rebuilt; every numeric gate, removal, scope and hook key is in the JSON
    with its source; an invalid policy is refused, not rendered;
  * check_rule_restatements: the real tree is clean; a wrong value planted in
    code (`name: value`, `NAME = value`, `policy.get("name", value)`) and in
    prose (confidence, pair cap, margin, one-use value, weeks) fails with
    file:line, the rule and found vs current; the right values pass; a
    retired name or phrase fails whatever its number; test/, ADR bodies,
    seeds and the source YAMLs are skipped; bad arguments exit 2;
  * ci.yml's suite runs both on shard 1 behind the salient gate, and the
    workflows-table row names rules-consistency.yml.

Run with: python3 -m pytest test/issues/test_issue_rules_source_of_truth.py -q
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

import build_rules  # noqa: E402
import check_rule_restatements as checker  # noqa: E402

RULES = json.loads((ROOT / "docs" / "rules.json").read_text(encoding="utf-8"))
POLICY_FILES = ("gate-policy.yml", "removal-policy.yml", "scope-policy.yml", "hook-policy.yml",
                "usage-unknown.yml", "stakes.yml")


def run(main, *argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


def value(rule_id: str):
    return RULES["rules"][rule_id]["value"]


class ScratchTree:
    """A throwaway root with the policy YAMLs and the generated docs."""

    def __init__(self, case: unittest.TestCase):
        self.dir = tempfile.TemporaryDirectory()
        case.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)
        (self.root / "evals").mkdir()
        (self.root / "docs").mkdir()
        for name in POLICY_FILES:
            shutil.copy(ROOT / "evals" / name, self.root / "evals" / name)
        for name in ("rules.md", "rules.json"):
            shutil.copy(ROOT / "docs" / name, self.root / "docs" / name)

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class BuildRulesTests(unittest.TestCase):

    def test_the_committed_page_and_json_are_current(self):
        code, _, err = run(build_rules.main, "--check")
        self.assertEqual(code, 0, err)

    def test_check_fails_when_a_yaml_changes_and_passes_once_rebuilt(self):
        tree = ScratchTree(self)
        path = tree.root / "evals" / "gate-policy.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("  max_runs_per_cell: 20\n", text)
        path.write_text(text.replace("  max_runs_per_cell: 20\n", "  max_runs_per_cell: 30\n"),
                        encoding="utf-8")
        code, _, err = run(build_rules.main, "--check", "--root", str(tree.root))
        self.assertEqual(code, 1)
        self.assertIn("stale", err)
        self.assertEqual(run(build_rules.main, "--root", str(tree.root))[0], 0)
        self.assertEqual(run(build_rules.main, "--check", "--root", str(tree.root))[0], 0)
        rebuilt = json.loads((tree.root / "docs" / "rules.json").read_text(encoding="utf-8"))
        self.assertEqual(rebuilt["rules"]["gate-policy.yml#skills.max_runs_per_cell"]["value"], 30)
        self.assertIn("at most 30 ", (tree.root / "docs" / "rules.md").read_text(encoding="utf-8"))

    def test_an_invalid_policy_is_refused_not_rendered(self):
        tree = ScratchTree(self)
        path = tree.root / "evals" / "removal-policy.yml"
        path.write_text(path.read_text(encoding="utf-8").replace("floor_weeks: 8", "floor_weeks: 0"),
                        encoding="utf-8")
        before = (tree.root / "docs" / "rules.md").read_text(encoding="utf-8")
        code, _, err = run(build_rules.main, "--root", str(tree.root))
        self.assertEqual(code, 1)
        self.assertIn("floor_weeks", err)
        self.assertEqual((tree.root / "docs" / "rules.md").read_text(encoding="utf-8"), before)

    def test_every_numeric_policy_key_is_in_the_json_with_its_source(self):
        for name in ("gate-policy.yml", "removal-policy.yml", "scope-policy.yml", "hook-policy.yml"):
            doc = yaml.safe_load((ROOT / "evals" / name).read_text(encoding="utf-8"))
            blocks = {"skills": doc["skills"], "guidance": doc["guidance"]} \
                if name == "gate-policy.yml" else {None: doc}
            for block, keys in blocks.items():
                for key, got in keys.items():
                    if isinstance(got, dict):
                        continue
                    rule_id = f"{name}#{block + '.' if block else ''}{key}"
                    with self.subTest(rule=rule_id):
                        self.assertEqual(RULES["rules"][rule_id]["value"], got)
                        self.assertEqual(RULES["rules"][rule_id]["source"], f"evals/{name}")

    def test_the_page_says_it_is_generated_and_links_its_keys(self):
        page = (ROOT / "docs" / "rules.md").read_text(encoding="utf-8")
        self.assertIn("Generated by scripts/build_rules.py", page)
        self.assertIn("../evals/gate-policy.yml#L", page)
        self.assertIn("No rule removes a hook check", page)
        self.assertIn("base-md-merge-window.yml", page)


class CheckerTests(unittest.TestCase):

    def check(self, *roots, extra=()):
        return run(checker.main, "--rules", str(ROOT / "docs" / "rules.json"),
                   *[a for r in roots for a in ("--root", str(r))], *extra)

    def test_the_real_tree_is_clean(self):
        code, out, err = self.check(ROOT)
        self.assertEqual(code, 0, out + err)

    def test_a_wrong_value_in_code_fails_and_the_right_one_passes(self):
        retire = value("gate-policy.yml#skills.retire_confidence")
        margin = value("gate-policy.yml#skills.objective_margin")
        cases = {
            "conf.yml": f"retire_confidence: {retire + 0.05:g}\n",
            "rule.py": f"HIGH_STOP_MIN_WITHOUT = {value('gate-policy.yml#skills.high_stop_min_without') - 0.05:g}\n",
            "get.py": f'm = policy.get("objective_margin", {margin + 0.1:g})\n',
            "fallback.js": f"const at = policy.retire_confidence ?? {retire - 0.1:g};\n",
            "weeks.py": f"RECHECK_AFTER = timedelta(weeks={value('gate-policy.yml#skills.recheck_weeks') + 1})\n",
            # Key then a parenthesized value, the docs' most common shape.
            "paren.md": f"Keep at `benefit_confidence` ({value('gate-policy.yml#skills.benefit_confidence') - 0.1:g}).\n",
            "guard.md": f"`rest_guard_min_pairs` ({value('gate-policy.yml#guidance.rest_guard_min_pairs') + 3}) pairs.\n",
            "legacy.md": f"HIGH_STOP_MIN_WITHOUT ({value('gate-policy.yml#skills.high_stop_min_without') - 0.05:g}; round 3).\n",
            "cap.md": f"`max_runs_per_cell` ({value('gate-policy.yml#skills.max_runs_per_cell') + 20})\n",
            "or.py": f'level = policy.get("retire_confidence") or {retire + 0.05:g}\n',
            "typed.py": f"MAX_LOOP_PAUSES: int = {value('gate-policy.yml#skills.max_removal_pauses') + 2}\n",
            "default.py": f"DEFAULT_RETIRE_CONFIDENCE = {retire - 0.2:g}\n",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                tree = ScratchTree(self)
                tree.write(f"src/{name}", "# fine\n" + text)
                code, out, _ = self.check(tree.root)
                self.assertEqual(code, 1, name)
                self.assertIn(f"src/{name}:2:", out)
                self.assertIn("found", out)
                self.assertIn("current", out)
        tree = ScratchTree(self)
        tree.write("src/ok.py", f"retire_confidence = {retire:g}\nmargin = policy.get("
                                f'"objective_margin", {margin})\n')
        self.assertEqual(self.check(tree.root)[0], 0)

    def test_a_wrong_value_in_prose_fails_and_the_right_one_passes(self):
        keep = round(value("gate-policy.yml#skills.benefit_confidence") * 100)
        cap = value("gate-policy.yml#skills.max_runs_per_cell")
        margin_points = round(value("gate-policy.yml#skills.objective_margin") * 100)
        use = value("removal-policy.yml#value_per_use_usd")
        recheck = value("gate-policy.yml#skills.recheck_weeks")
        wrong = {
            "confidence": f"A subject is kept at {keep + 5}% confidence that it helps.\n",
            "cap": f"A cell is capped at {cap + 20} pairs.\n",
            "margin": f"No benefit means a gain under the {margin_points + 5}-point margin.\n",
            "use": f"Remove it once its cost passes ${use + 5:g}, the value of one use.\n",
            "weeks": f"A decided subject is re-checked after {recheck + 4} weeks.\n",
            "paired runs": f"A cell with {cap + 20} paired runs with neither test crossed has no clear effect.\n",
            "cap of": f"Each cell stops at the cap of {cap + 20}.\n",
            "fraction": f"Remove it at {value('gate-policy.yml#skills.retire_confidence') - 0.05:g} confidence that it does not help.\n",
        }
        for what, text in wrong.items():
            with self.subTest(what=what):
                tree = ScratchTree(self)
                tree.write("README.md", "# Title\n\n" + text)
                code, out, _ = self.check(tree.root)
                self.assertEqual(code, 1, what)
                self.assertIn("README.md:3:", out)
        tree = ScratchTree(self)
        tree.write("README.md", (
            f"A subject is kept at {keep}% confidence that it helps. A cell is capped at "
            f"{cap} pairs. No benefit means a gain under the {margin_points}-point margin.\n"
            f"Remove it once its cost passes ${use:g}, the value of one use.\n"
            f"A decided subject is re-checked after {recheck} weeks.\n"
            f"A cell with {cap} paired runs with neither test crossed has no clear effect.\n"
            f"Each cell stops at the cap of {cap}.\n"
            f"Remove it at {value('gate-policy.yml#skills.retire_confidence'):g} confidence that it "
            "does not help.\n"))
        tree.write("src/ok.py", (
            f'level = policy.get("retire_confidence") or '
            f'{value("gate-policy.yml#skills.retire_confidence"):g}\n'
            f'MAX_LOOP_PAUSES: int = {value("gate-policy.yml#skills.max_removal_pauses")}\n'
            f'# `max_runs_per_cell` ({cap}); `max_runs_per_cell` (2026-11-03) is a date.\n'))
        code, out, err = self.check(tree.root)
        self.assertEqual(code, 0, out + err)

    def test_a_retired_rule_fails_whatever_its_number(self):
        for text in ("ZERO_USE_MIN_SESSIONS = 7\n",
                     'HOOK_POLICY_DEFAULTS = {"window_weeks": 8}\n',
                     "Evals pause after 500 sessions of zero use.\n"):
            with self.subTest(text=text):
                tree = ScratchTree(self)
                tree.write("notes.md", text)
                self.assertEqual(self.check(tree.root)[0], 1)

    def test_skipped_paths_are_not_read(self):
        tree = ScratchTree(self)
        bad = "retire_confidence: 0.5\n"
        for rel in ("test/x.yml", "tests/x.yml", "results/x.yml", "routine-results/x.yml",
                    "node_modules/p/x.yml", "docs/decisions/0001-old.md", "tool/index.html",
                    "explorer/dist/x.js", "evals/some-skill/seed/x.yml", "vendor/x.yml",
                    ".claude/worktrees/w/x.yml"):
            tree.write(rel, bad)
        self.assertEqual(self.check(tree.root)[0], 0)
        tree.write("starter/x.yml", bad)
        self.assertEqual(self.check(tree.root, extra=("--exclude", "starter/*"))[0], 0)
        self.assertEqual(self.check(tree.root)[0], 1)

    def test_the_source_yamls_themselves_are_not_restatements(self):
        tree = ScratchTree(self)
        path = tree.root / "evals" / "gate-policy.yml"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "retire_confidence: 0.90", "retire_confidence: 0.95"), encoding="utf-8")
        self.assertEqual(self.check(tree.root)[0], 0)

    def test_bad_arguments_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(run(checker.main, "--rules", str(Path(d) / "none.json"),
                                 "--root", d)[0], 2)
            self.assertEqual(run(checker.main, "--rules", str(ROOT / "docs" / "rules.json"),
                                 "--root", str(Path(d) / "missing"))[0], 2)


class WiringTests(unittest.TestCase):

    def test_ci_runs_both_on_one_shard_behind_the_salient_gate(self):
        doc = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
        steps = {s.get("name"): s for s in doc["jobs"]["suite"]["steps"]}
        for name, command in (
                ("Rules page matches the policy YAMLs", "python3 scripts/build_rules.py --check"),
                ("No rule restatement disagrees with docs/rules.json",
                 "python3 scripts/check_rule_restatements.py --rules docs/rules.json --root .")):
            with self.subTest(step=name):
                self.assertEqual(steps[name]["run"].strip(), command)
                self.assertEqual(steps[name]["if"],
                                 "steps.salient.outputs.run == 'true' && matrix.shard == 1")
        self.assertIn("docs/**", doc[True]["push"]["paths"])

    def test_the_fleet_workflow_is_scheduled_read_only_and_names_no_repo(self):
        path = ROOT / ".github" / "workflows" / "rules-consistency.yml"
        text = path.read_text(encoding="utf-8")
        doc = yaml.safe_load(text)
        self.assertEqual(set(doc[True]), {"schedule", "workflow_dispatch"})
        self.assertEqual(doc["permissions"], {"contents": "read", "issues": "write"})
        self.assertEqual(doc["concurrency"], {"group": "rules-consistency",
                                              "cancel-in-progress": False})
        # Each repository is checked alone, with its own excludes.
        self.assertNotIn("--exclude \"$", text)
        for step in doc["jobs"]["check"]["steps"]:
            self.assertNotIn("${{", step.get("run", ""), step.get("name"))
        # The repositories come from evals/rules-consistency.yml alone.
        self.assertNotIn("Adam-S-Daniel/", text)
        config = yaml.safe_load((ROOT / "evals" / "rules-consistency.yml").read_text(encoding="utf-8"))
        names = [row["repo"] for row in config["repos"]]
        self.assertTrue(names)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("Rule restatements disagree with docs/rules.md", text)
        self.assertIn("--label agent-ready", text)
        table = (ROOT / "docs" / "workflows.md").read_text(encoding="utf-8")
        self.assertIn("| `rules-consistency.yml` |", table)

    def test_agents_md_points_at_the_rules(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("docs/rules.md", agents)
        self.assertIn("check_rule_restatements.py", agents)


if __name__ == "__main__":
    unittest.main()
