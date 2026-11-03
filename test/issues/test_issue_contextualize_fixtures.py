#!/usr/bin/env python3
"""Drafted skill fixtures reach a verdict (adversarial gap review,
2026-11-03, item 2).

The draft loop writes isolation pairs with no `context:`, whose runs never
pool. `scripts/contextualize_fixtures.py` gives each one listed in
evals/unscheduled.yml with the draft loop's reason a measured context and
moves it to evals/scheduled.yml. Pinned here, offline and with a fake
measurer (the real one reads Git checkouts):

  * only the draft loop's isolation rows with no context are candidates;
  * the context repository is the skill's override, else its siblings'
    most common one, else its bundle's default;
  * a skill not on main yet, or a context that cannot be proven, is skipped
    and left listed;
  * each budget is the larger arm plus 25%, rounded up;
  * the written fixture, unscheduled.yml and scheduled.yml read back with
    nothing else changed, and the schedule's promoted-row rules hold.

example.com and example-org only.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

import contextualize_fixtures as cf  # noqa: E402
import draft_new_skill  # noqa: E402
import plan_scheduled_evals as planner  # noqa: E402
import scaffold_real_work as scaffold  # noqa: E402

SHA = "a" * 40
GUIDANCE = "b" * 40
REASON = draft_new_skill.ISOLATION_REASON


class FakeMeasure:
    def __init__(self, bundles, refuse=()):
        self.bundles = bundles
        self.refuse = set(refuse)
        self.calls = []

    def bundle(self, skill, url):
        if skill not in self.bundles:
            raise cf.Skip(f"{skill} is not on its registry's main (main_copy_missing)")
        return self.bundles[skill]

    def __call__(self, fixture_dir, repository):
        self.calls.append((fixture_dir.name, repository))
        if repository in self.refuse:
            raise cf.Skip(f"guidance unproven at {repository}")
        return {"repository": repository, "revision": SHA, "guidance_revision": GUIDANCE,
                "budget": cf.budgets({"guidance_bytes": 100, "skill_catalog_bytes": 10,
                                      "skill_payload_bytes": 1000},
                                     {"guidance_bytes": 100, "skill_catalog_bytes": 13,
                                      "skill_payload_bytes": 1201}),
                "action": "added"}


class ContextualizeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="contextualize-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        fixture = ("# A drafted fixture.\nskill: {skill}\n"
                   "registry: https://github.com/Adam-S-Daniel/adam-agentskills\n"
                   "prompt: Tidy https://example.com/a.\n")
        for skill, name in (("new-skill", "one"), ("new-skill", "two"),
                            ("local-skill", "one"), ("unmerged-skill", "one"),
                            ("known-skill", "drafted")):
            self.write(f"evals/{skill}/{name}/fixture.yaml", fixture.format(skill=skill))
        self.write("evals/known-skill/reviewed/fixture.yaml",
                   fixture.format(skill="known-skill")
                   + "context:\n  repository: example-org/home\n  revision: " + SHA
                   + "\n  guidance_revision: " + GUIDANCE + "\n  budget:\n"
                   "    guidance_bytes: 1\n    skill_catalog_bytes: 1\n"
                   "    skill_payload_bytes: 1\n")
        self.write("evals/other/fixture.yaml", fixture.format(skill="other"))
        rows = [("evals/new-skill/one", REASON), ("evals/new-skill/two", REASON),
                ("evals/local-skill/one", REASON), ("evals/unmerged-skill/one", REASON),
                ("evals/known-skill/drafted", REASON),
                ("evals/other", "Deliberately out: a reason of its own.")]
        self.write("evals/unscheduled.yml", "# Header kept.\nfixtures:\n" + "".join(
            f'  - path: {p}\n    reason: "{r}"\n' for p, r in rows))
        self.write("evals/scheduled.yml",
                   'fixtures:\n  - path: evals/known-skill/reviewed\n    readiness: "Reviewed."\n')
        self.measure = FakeMeasure({"new-skill": "adam-coding-anywhere",
                                    "local-skill": "adam-non-coding-local",
                                    "known-skill": "adam-coding-anywhere"})

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def load(self, rel):
        return yaml.safe_load((self.root / rel).read_text(encoding="utf-8"))

    def test_only_the_draft_loops_isolation_rows_are_candidates(self):
        self.assertEqual(cf.candidates(self.root), [
            "evals/new-skill/one", "evals/new-skill/two", "evals/local-skill/one",
            "evals/unmerged-skill/one", "evals/known-skill/drafted"])

    def test_the_repository_is_override_then_siblings_then_bundle(self):
        self.assertEqual(cf.choose_repository(self.root, "evals/red-ci-adamdaniel-ai/x",
                                              "red-ci-adamdaniel-ai", "adam-coding-anywhere"),
                         "Adam-S-Daniel/adamdaniel.ai")
        self.assertEqual(cf.choose_repository(self.root, "evals/known-skill/drafted",
                                              "known-skill", "adam-coding-anywhere"),
                         "example-org/home")
        self.assertEqual(cf.choose_repository(self.root, "evals/local-skill/one",
                                              "local-skill", "adam-non-coding-local"),
                         "Adam-S-Daniel/wsl-automation")
        with self.assertRaises(cf.Skip):
            cf.choose_repository(self.root, "evals/x/y", "x", "some-other-bundle")

    def test_budgets_take_the_larger_arm_plus_a_quarter_rounded_up(self):
        self.assertEqual(cf.budgets({"guidance_bytes": 100, "skill_catalog_bytes": 10,
                                     "skill_payload_bytes": 1000},
                                    {"guidance_bytes": 99, "skill_catalog_bytes": 13,
                                     "skill_payload_bytes": 1201}),
                         {"guidance_bytes": 125, "skill_catalog_bytes": 17,
                          "skill_payload_bytes": 1502})

    def test_a_dry_run_writes_nothing(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*.yaml")}
        before.update({p: p.read_bytes() for p in self.root.rglob("*.yml")})
        done, _ = cf.contextualize(self.root, self.measure, "2026-11-03", apply=False)
        self.assertEqual(len(done), 4)
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_apply_contextualizes_and_schedules_and_skips_the_unmerged(self):
        unscheduled_before = self.load("evals/unscheduled.yml")
        done, skipped = cf.contextualize(self.root, self.measure, "2026-11-03", apply=True)
        self.assertEqual([p for p, _ in done], [
            "evals/new-skill/one", "evals/new-skill/two", "evals/local-skill/one",
            "evals/known-skill/drafted"])
        self.assertEqual([p for p, _ in skipped], ["evals/unmerged-skill/one"])
        self.assertIn("main_copy_missing", skipped[0][1])
        # Each fixture gains exactly its context.
        fixture = self.load("evals/local-skill/one/fixture.yaml")
        self.assertEqual(fixture["context"], {
            "repository": "Adam-S-Daniel/wsl-automation", "revision": SHA,
            "guidance_revision": GUIDANCE,
            "budget": {"guidance_bytes": 125, "skill_catalog_bytes": 17,
                       "skill_payload_bytes": 1502}})
        self.assertEqual(self.load("evals/known-skill/drafted/fixture.yaml")["context"]
                         ["repository"], "example-org/home")
        self.assertTrue((self.root / "evals/new-skill/one/fixture.yaml").read_text(
            encoding="utf-8").startswith("# A drafted fixture.\n"))
        # Unscheduled keeps its header and the other rows.
        text = (self.root / "evals/unscheduled.yml").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Header kept.\n"))
        self.assertEqual([r["path"] for r in self.load("evals/unscheduled.yml")["fixtures"]],
                         ["evals/unmerged-skill/one", "evals/other"])
        self.assertEqual(len(unscheduled_before["fixtures"]), 6)
        # Scheduled gains promoted rows the planner loads.
        rows = self.load("evals/scheduled.yml")["fixtures"]
        self.assertEqual([r["path"] for r in rows][1:], [p for p, _ in done])
        for row in rows[1:]:
            self.assertTrue(row["readiness"].startswith(scaffold.PROMOTED_NOTE))
        env = {"GIT_AUTHOR_NAME": "Example", "GIT_AUTHOR_EMAIL": "dev@example.com",
               "GIT_COMMITTER_NAME": "Example", "GIT_COMMITTER_EMAIL": "dev@example.com",
               "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
               "PATH": os.environ["PATH"]}
        for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "x"]):
            subprocess.run(["git", *args], cwd=self.root, check=True, env=env,
                           capture_output=True)
        committed = planner.committed_fixtures(self.root)
        planner.scheduled_fixtures(self.root / "evals/scheduled.yml", committed)
        # A second run finds nothing left but the unmerged skill.
        self.assertEqual(cf.candidates(self.root), ["evals/unmerged-skill/one"])

    def test_an_unproven_context_is_skipped_and_left_listed(self):
        measure = FakeMeasure(self.measure.bundles, refuse={"Adam-S-Daniel/wsl-automation"})
        done, skipped = cf.contextualize(self.root, measure, "2026-11-03", apply=True)
        self.assertIn("evals/local-skill/one", [p for p, _ in skipped])
        self.assertNotIn("context", self.load("evals/local-skill/one/fixture.yaml"))
        self.assertIn("evals/local-skill/one",
                      [r["path"] for r in self.load("evals/unscheduled.yml")["fixtures"]])

    def test_a_fixture_that_already_has_a_context_is_refused(self):
        target = self.root / "evals/new-skill/one/fixture.yaml"
        metadata = self.measure(target.parent, "example-org/home")
        cf.write_context(target, metadata, "2026-11-03")
        with self.assertRaises(scaffold.ScaffoldError):
            cf.write_context(target, metadata, "2026-11-03")

    def test_every_bundle_the_draft_loop_writes_to_has_a_default(self):
        self.assertEqual(set(cf.CONTEXT_FOR_PLUGIN), set(draft_new_skill.PLUGINS))


if __name__ == "__main__":
    unittest.main()
