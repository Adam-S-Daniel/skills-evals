#!/usr/bin/env python3
"""Re-pin drifted in-place fixtures whose evidence is not in use.

`scripts/repin_drifted_fixtures.py` moves a fixture's `context.revision` and
`guidance_revision` to its context repository's HEAD when the explorer's
`context-drift` alert fires and the fixture's runs at its current pin are
free (`explorer_data.drift_evidence`). Pinned here, offline, with a fake
measurer (the real one reads Git checkouts):

  * only the two revision lines and one comment line change, and the file
    reads back YAML-equal otherwise;
  * a repeated re-pin replaces the comment rather than stacking it;
  * a measurement the committed budget cannot hold is not re-pinned and is
    listed as over budget;
  * a skipped measurement is reported, never re-pinned;
  * a dry run writes nothing.

example.com and example-org only.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

import contextualize_fixtures as cf  # noqa: E402
import repin_drifted_fixtures as rp  # noqa: E402
import scaffold_real_work as scaffold  # noqa: E402

OLD, OLD_GUIDANCE = "a" * 40, "b" * 40
NEW, NEW_GUIDANCE = "c" * 40, "d" * 40
BUDGET = {"guidance_bytes": 125, "skill_catalog_bytes": 20, "skill_payload_bytes": 1500}
TEXT = f"""# A fixture with its own comments.
skill: some-skill
registry: https://example.com/registry
prompt: Tidy https://example.com/a.

# In-place context (ADR 0012), added on 2026-11-03 by scripts/contextualize_fixtures.py:
context:
  repository: example-org/home
  revision: {OLD}
  guidance_revision: {OLD_GUIDANCE}
  budget:
    guidance_bytes: 125
    skill_catalog_bytes: 20
    skill_payload_bytes: 1500
judge:
  revision: {OLD}
"""


class FakeMeasure:
    def __init__(self, measured, skip=()):
        self.measured = measured
        self.skip = set(skip)

    def __call__(self, fixture_dir, repository):
        if fixture_dir.name in self.skip:
            raise cf.Skip("no checkout")
        return {"repository": repository, "revision": NEW, "guidance_revision": NEW_GUIDANCE,
                "budget": {k: v * 5 // 4 + 1 for k, v in self.measured.items()},
                "measured": self.measured, "action": "added"}


class RepinTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="repin-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        for name in ("fits", "over", "skipped"):
            self.write(f"evals/some-skill/{name}/fixture.yaml", TEXT)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def entry(self, name):
        return {"fixture": f"evals/some-skill/{name}", "skill": "some-skill",
                "context": yaml.safe_load(TEXT)["context"]}

    def read(self, name):
        return (self.root / f"evals/some-skill/{name}/fixture.yaml").read_text(encoding="utf-8")

    def measure(self, **kw):
        return FakeMeasure({"guidance_bytes": 100, "skill_catalog_bytes": 16,
                            "skill_payload_bytes": 1200, **kw}, skip=("skipped",))

    def test_only_the_two_revisions_and_the_comment_change(self):
        done, over, skipped = rp.repin(self.root, self.measure(), [self.entry("fits")],
                                       "2026-11-14", apply=True)
        self.assertEqual(([p for p, _ in done], over, skipped), (["evals/some-skill/fits"], [], []))
        after = self.read("fits")
        expected = yaml.safe_load(TEXT)
        expected["context"]["revision"] = NEW
        expected["context"]["guidance_revision"] = NEW_GUIDANCE
        self.assertEqual(yaml.safe_load(after), expected)
        self.assertEqual(after.splitlines(), (
            TEXT.replace(OLD_GUIDANCE, NEW_GUIDANCE).replace(
                f"context:\n  repository: example-org/home\n  revision: {OLD}",
                f"{rp.comment('2026-11-14')}\ncontext:\n  repository: example-org/home\n"
                f"  revision: {NEW}")
            .replace(f"judge:\n  revision: {NEW}", f"judge:\n  revision: {OLD}")).splitlines())

    def test_a_second_re_pin_replaces_the_comment(self):
        target = self.root / "evals/some-skill/fits/fixture.yaml"
        rp.write_repin(target, {"revision": NEW, "guidance_revision": NEW_GUIDANCE}, "2026-11-14")
        rp.write_repin(target, {"revision": OLD, "guidance_revision": OLD_GUIDANCE}, "2026-11-21")
        text = target.read_text(encoding="utf-8")
        self.assertEqual(text.count(rp.COMMENT_PREFIX), 1)
        self.assertIn(rp.comment("2026-11-21") + "\ncontext:\n", text)
        self.assertEqual(yaml.safe_load(text), yaml.safe_load(TEXT))

    def test_a_measurement_over_the_committed_budget_is_listed_and_not_written(self):
        done, over, _ = rp.repin(self.root, self.measure(skill_payload_bytes=1501),
                                 [self.entry("over")], "2026-11-14", apply=True)
        self.assertEqual((done, over), ([], ["evals/some-skill/over"]))
        self.assertEqual(self.read("over"), TEXT)

    def test_a_measurement_exactly_at_the_budget_fits(self):
        done, over, _ = rp.repin(self.root, self.measure(skill_payload_bytes=1500),
                                 [self.entry("fits")], "2026-11-14", apply=False)
        self.assertEqual((len(done), over), (1, []))

    def test_a_skipped_measurement_is_reported_and_not_written(self):
        done, over, skipped = rp.repin(self.root, self.measure(), [self.entry("skipped")],
                                       "2026-11-14", apply=True)
        self.assertEqual((done, over, skipped),
                         ([], [], [("evals/some-skill/skipped", "no checkout")]))
        self.assertEqual(self.read("skipped"), TEXT)

    def test_a_dry_run_writes_nothing(self):
        done, _, _ = rp.repin(self.root, self.measure(), [self.entry("fits")],
                              "2026-11-14", apply=False)
        self.assertEqual(len(done), 1)
        self.assertEqual(self.read("fits"), TEXT)

    def test_a_fixture_without_one_context_block_raises(self):
        self.write("evals/some-skill/fits/fixture.yaml", "skill: some-skill\n")
        with self.assertRaises(scaffold.ScaffoldError):
            rp.write_repin(self.root / "evals/some-skill/fits/fixture.yaml",
                           {"revision": NEW, "guidance_revision": NEW_GUIDANCE}, "2026-11-14")

    def test_bad_arguments_exit_two(self):
        self.assertEqual(rp.main(["--results-tree", str(self.root), "--as-of", "nonsense"]), 2)


if __name__ == "__main__":
    unittest.main()
