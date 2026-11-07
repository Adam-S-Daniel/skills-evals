#!/usr/bin/env python3
"""scripts/explorer_data.py PRIVATE MODE (`--subjects private`, 2026-11-04).

A private registry's dashboard reads the same schema as the public document,
built from the private registry's own checkout and run inside that private
repository. These tests pin that private subjects appear only in this mode,
that the public mode's output does not move, and the mode's refusals.

Hermetic: invented skill names and data, no network, no clock.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))

import explorer_data  # noqa: E402
import plan_week  # noqa: E402
from test_issue_72_explorer_data import AS_OF, SHA_A, SHA_B, Tree  # noqa: E402
from test_issue_public_data_contract import routine_pair  # noqa: E402

PRIVATE_NAME = "adam-agentskills-private"
PRIVATE_SKILLS = ("hidden-one", "hidden-two")
PUBLIC_REGISTRY = "adam-agentskills"


class PrivateModeTests(unittest.TestCase):

    def setUp(self):
        self.t = Tree(self)
        # A private registry checkout in its registries.yml layout.
        self.registry = self.t.root / "private-registry"
        for name in PRIVATE_SKILLS:
            skill = self.registry / "plugins" / "bundle-p" / "skills" / name / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(f"---\nname: {name}\ndescription: invented\n---\n", encoding="utf-8")
        # A public registry checkout, for the refusal.
        self.public_registry = self.t.root / "public-registry"
        (self.public_registry / "plugins" / "b" / "skills" / "alpha").mkdir(parents=True)
        (self.public_registry / "plugins" / "b" / "skills" / "alpha" / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: invented\n---\n", encoding="utf-8")
        # One fixture for a private skill, so plan_week.private_skills sees it.
        fixture = self.t.evals / "hidden-one" / "fx-p" / "fixture.yaml"
        fixture.parent.mkdir(parents=True)
        fixture.write_text(yaml.safe_dump({"skill": "hidden-one",
                                           "registry": plan_week.PRIVATE_REGISTRY_URL}),
                           encoding="utf-8")
        # Paired runs: one public skill (in the census), one private one.
        good, bad = [Tree.trial(5, 5, 8.0, 0.25)], [Tree.trial(1, 5, 4.0, 0.25)]
        self.t.pair("alpha", "20261030T100000Z", good, bad)
        self.t.pair("hidden-one", "20261030T110000Z", good, bad, fixture="fx-p")
        # A routine run, the shape `evals` (scripts/eval_facts.py) scores.
        routine_pair(self.t.tree, "20261030T120000Z-abc123", "hidden-one", 4, 2)

    def args(self, out: Path, *extra) -> list:
        return ["--results-tree", str(self.t.tree), "--roster", str(self.t.roster),
                "--policy", str(self.t.policy), "--evals-dir", str(self.t.evals),
                "--as-of", AS_OF, "--repository-commit", SHA_A, "--results-commit", SHA_B,
                "--out", str(out), *extra]

    def private_args(self, out: Path, *extra) -> list:
        return self.args(out, "--subjects", "private",
                         "--registry", f"{PRIVATE_NAME}={self.registry}",
                         "--source-repository", "Adam-S-Daniel/adam-agentskills-private", *extra)

    def run_main(self, argv) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = explorer_data.main(argv)
        return code, err.getvalue()

    def test_private_subjects_appear_only_in_private_mode(self):
        public_out = self.t.root / "out" / "latest.json"
        self.assertEqual(self.run_main(self.args(public_out)), (0, ""))
        public_text = public_out.read_text(encoding="utf-8")
        for name in PRIVATE_SKILLS:
            self.assertNotIn(name, public_text)

        private_out = self.t.root / "out" / "private.json"
        self.assertEqual(self.run_main(self.private_args(private_out)), (0, ""))
        doc = json.loads(private_out.read_text(encoding="utf-8"))
        self.assertEqual([s["name"] for s in doc["skills"]], list(PRIVATE_SKILLS))
        self.assertEqual({s["registry"] for s in doc["skills"]}, {PRIVATE_NAME})
        hidden = doc["skills"][0]
        self.assertEqual(hidden["status"], "covered")
        self.assertTrue(hidden["runs"])
        self.assertEqual(doc["skills"][1]["status"], "gap")
        # Not subtracted as a private skill, so its scored run is in `evals`.
        self.assertEqual({r["skill"] for r in doc["evals"]["runs"]}, {"hidden-one"})
        self.assertEqual({k: doc["coverage"][k] for k in ("covered", "gap", "skipped", "total")},
                         {"covered": 1, "gap": 1, "skipped": 0, "total": 2})
        self.assertIsNone(doc["coverage"]["as_of"])
        self.assertEqual(doc["source"]["repository"], "Adam-S-Daniel/adam-agentskills-private")
        for key in ("hooks", "activity", "lessons", "lesson_funnel", "fixture_queue",
                    "fires_without_results", "spend"):
            self.assertIsNone(doc[key], key)
        # The public census's skills are not subjects here.
        self.assertNotIn("alpha", {s["name"] for s in doc["skills"]})

    def test_private_mode_needs_no_coverage_census(self):
        (self.t.tree / "coverage" / "latest.json").unlink()
        out = self.t.root / "out" / "private.json"
        self.assertEqual(self.run_main(self.private_args(out)), (0, ""))
        code, _err = self.run_main(self.args(self.t.root / "out" / "latest.json"))
        self.assertEqual(code, 2)

    def test_the_public_output_is_byte_identical_with_or_without_the_default_flags(self):
        plain = self.t.root / "a" / "latest.json"
        explicit = self.t.root / "b" / "latest.json"
        self.assertEqual(self.run_main(self.args(plain)), (0, ""))
        self.assertEqual(self.run_main(self.args(
            explicit, "--subjects", "public",
            "--source-repository", explorer_data.DEFAULT_SOURCE_REPOSITORY)), (0, ""))
        self.assertEqual(plain.read_bytes(), explicit.read_bytes())
        # And it is the document build() makes with no private-mode argument.
        doc = explorer_data.build(self.t.tree, self.t.roster, self.t.policy, self.t.evals,
                                  AS_OF, SHA_A, SHA_B)
        self.assertEqual(json.loads(plain.read_text(encoding="utf-8"))["skills"],
                         json.loads(explorer_data.finish(doc))["skills"])
        self.assertEqual(doc["source"]["repository"], "Adam-S-Daniel/skills-evals")

    def test_private_mode_refuses_the_public_file_name(self):
        out = self.t.root / "out" / "latest.json"
        code, err = self.run_main(self.private_args(out))
        self.assertEqual(code, 2)
        self.assertIn("latest.json", err)
        self.assertFalse(out.exists())

    def test_private_mode_refuses_without_a_private_registry(self):
        out = self.t.root / "out" / "private.json"
        cases = {
            "no registry": self.args(out, "--subjects", "private"),
            "a public registry": self.args(
                out, "--subjects", "private",
                "--registry", f"{PUBLIC_REGISTRY}={self.public_registry}"),
            "a private and a public registry": self.args(
                out, "--subjects", "private",
                "--registry", f"{PRIVATE_NAME}={self.registry}",
                "--registry", f"{PUBLIC_REGISTRY}={self.public_registry}"),
            "a missing checkout": self.args(
                out, "--subjects", "private",
                "--registry", f"{PRIVATE_NAME}={self.t.root / 'not-there'}"),
        }
        for label, argv in cases.items():
            with self.subTest(label):
                code, err = self.run_main(argv)
                self.assertEqual(code, 2)
                self.assertIn("--subjects private", err)
                self.assertFalse(out.exists())

    def test_private_mode_refuses_public_only_inputs(self):
        out = self.t.root / "out" / "private.json"
        stub = self.t.root / "stub.json"
        stub.write_text("{}", encoding="utf-8")
        for flag in explorer_data.PUBLIC_ONLY_FLAGS:
            option = "--" + flag.replace("_", "-")
            value = f"owner/repo={self.t.root}" if flag == "context_repo" else str(stub)
            with self.subTest(option):
                code, err = self.run_main(self.private_args(out, option, value))
                self.assertEqual(code, 2)
                self.assertIn(option, err)
                self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
