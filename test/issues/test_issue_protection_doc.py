#!/usr/bin/env python3
"""scripts/protection_doc.py: the eval-protection subset a private registry's CI
builds from its own results tree (it must match the explorer subset that
_agent-guidance's eval-protected.js reads, without the skills ever reaching
the public explorer, #81).

Hermetic: invented skills, a tiny results tree, fixtures and registry checkouts
in a temp directory, and no network or clock.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compute_gates  # noqa: E402
import context  # noqa: E402
import delivery  # noqa: E402
import protection_doc  # noqa: E402
import run_eval  # noqa: E402
import test_issue_70_retirement as t70  # noqa: E402  (its results-tree builders)

AS_OF = "2026-12-31T00:00:00Z"
PRIVATE, PUBLIC = "adam-agentskills-private", "adam-agentskills"


class ProtectionDocTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="protection-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.tree = self.tmp / "tree"
        self.roster = self.tmp / "roster.yml"
        self.roster.write_text("arms:\n  - id: model-a\n", encoding="utf-8")
        self.evals = self.tmp / "repo" / "evals"
        self.private = self.tmp / "private"
        self.public = self.tmp / "public"
        for skill, checkout in (("privone", self.private), ("privtwo", self.private),
                                ("pubone", self.public)):
            fixture = self.evals / skill
            fixture.mkdir(parents=True)
            (fixture / "fixture.yaml").write_text(f"skill: {skill}\nprompt: p\n",
                                                  encoding="utf-8")
            path = checkout / "plugins" / "bundle" / "skills" / skill / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text(f"---\nname: {skill}\ndescription: d\n---\nbody\n",
                            encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.evals.parent, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.evals.parent, check=True)

    def digest_of(self, checkout, skill):
        path = checkout / "plugins" / "bundle" / "skills" / skill
        return context._file_digest(delivery._tree_files(path)[0])

    def write_runs(self, skill, checkout, *, tested=None, count=3):
        t70.write_arm_runs(self.tree, skill, "model-a", t70.FLAT[:count],
                           t70.FLAT_JUDGE[:count], checks=False,
                           tested=tested or self.digest_of(checkout, skill),
                           fdig=run_eval.fixture_digest(self.evals / skill))

    def run_cli(self, name="out.json", registries=(f"{PRIVATE}=private",)):
        out = self.tmp / name
        args = ["--results-tree", str(self.tree), "--roster", str(self.roster),
                "--policy", str(ROOT / "evals" / "gate-policy.yml"),
                "--evals-dir", str(self.evals), "--as-of", AS_OF, "--out", str(out)]
        for value in registries:
            label, _, rel = value.partition("=")
            args += ["--registry", f"{label}={self.tmp / rel}"]
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = protection_doc.main(args)
        self.assertEqual(code, 0)
        return out, json.loads(out.read_text(encoding="utf-8")), stdout.getvalue()

    def by_name(self, doc):
        return {s["name"]: s for s in doc["skills"]}

    def test_run_on_current_text_counts_and_old_digest_does_not(self):
        self.write_runs("privone", self.private)
        self.write_runs("privtwo", self.private, tested="0" * 64)
        _, doc, _ = self.run_cli()
        skills = self.by_name(doc)
        self.assertGreater(skills["privone"]["current_text_runs"], 0)
        self.assertEqual(skills["privtwo"]["current_text_runs"], 0)
        self.assertEqual(skills["privone"]["registry"], PRIVATE)

    def test_skill_outside_the_given_registries_is_omitted(self):
        self.write_runs("privone", self.private)
        self.write_runs("pubone", self.public)
        _, doc, _ = self.run_cli()
        self.assertNotIn("pubone", self.by_name(doc))
        _, both, _ = self.run_cli("both.json",
                                  (f"{PRIVATE}=private", f"{PUBLIC}=public"))
        self.assertEqual(self.by_name(both)["pubone"]["registry"], PUBLIC)

    def test_empty_tree_gives_no_skills_and_a_count_line(self):
        _, doc, printed = self.run_cli()
        self.assertEqual(doc, {"schema_version": 1, "skills": [],
                               "guidance": {"sections": []}})
        self.assertEqual(printed, "protection_doc: 0 skills\n")

    def test_skill_with_no_runs_in_the_tree_is_insufficient_with_zero(self):
        self.write_runs("privone", self.private)
        with mock.patch.object(compute_gates, "compute", return_value={
                "skills": {"privtwo": {"verdict": "insufficient", "cells": []}}}):
            out = protection_doc.build(self.tree, self.roster, self.tmp / "p.yml",
                                       self.evals, AS_OF,
                                       compute_gates.flag_registries(
                                           [f"{PRIVATE}={self.private}"]))
        self.assertEqual(out["skills"], [{"name": "privtwo", "registry": PRIVATE,
                                          "verdict": "insufficient",
                                          "current_text_runs": 0}])

    def test_output_shape_is_sorted_and_deterministic(self):
        self.write_runs("privtwo", self.private)
        self.write_runs("privone", self.private)
        first, doc, printed = self.run_cli("a.json")
        second, _, _ = self.run_cli("b.json")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual([s["name"] for s in doc["skills"]], ["privone", "privtwo"])
        self.assertEqual(set(doc["skills"][0]),
                         {"name", "registry", "verdict", "current_text_runs"})
        self.assertTrue(first.read_text(encoding="utf-8").endswith("}\n"))
        self.assertEqual(printed, "protection_doc: 2 skills\n")


if __name__ == "__main__":
    unittest.main()
