#!/usr/bin/env python3
"""Issue #548: one shared rule for a skill's copy on the registries' main.

run_eval.main_copy returns the single copy or refuses with a named
DeliveryError; compute_gates.tested_digest maps every refusal to None.

Hermetic: registry trees in a temporary directory, no network, no clock.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent.parent
ROOT = TEST_DIR.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

import compute_gates  # noqa: E402
import context  # noqa: E402
import delivery  # noqa: E402
import run_eval  # noqa: E402

LAYOUT = "plugins/*/skills/*/SKILL.md"


class MainCopyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def registry(self, name, owner="Owner", skills=(("bundle", "sample"),)):
        path = self.tmp / name
        path.mkdir()
        for bundle, skill in skills:
            skill_md = path / "plugins" / bundle / "skills" / skill / "SKILL.md"
            skill_md.parent.mkdir(parents=True, exist_ok=True)
            skill_md.write_text(f"---\nname: {skill}\ndescription: d\n---\n{name}\n",
                                encoding="utf-8")
        return {"name": name, "path": str(path), "layout": LAYOUT,
                "url": f"https://github.com/{owner}/{name}"}

    @staticmethod
    def registries(*entries):
        return {entry["name"]: entry for entry in entries}

    def code(self, registries, skill, url):
        with self.assertRaises(delivery.DeliveryError) as raised:
            run_eval.main_copy(registries, skill, url)
        return raised.exception.code

    def test_url_returns_the_one_copy(self):
        one = self.registry("one")
        two = self.registry("two")
        identity, bundle, path = run_eval.main_copy(
            self.registries(one, two), "sample", "https://github.com/Owner/two")
        self.assertEqual((identity, bundle), ("Owner/two", "bundle"))
        self.assertEqual(path, Path(two["path"]) / "plugins" / "bundle" / "skills" / "sample")

    def test_no_url_finds_a_unique_copy_across_registries(self):
        one = self.registry("one", skills=())
        two = self.registry("two")
        identity, bundle, _path = run_eval.main_copy(
            self.registries(one, two), "sample", None)
        self.assertEqual((identity, bundle), ("Owner/two", "bundle"))

    def test_case_and_git_suffix_differences_still_match(self):
        one = self.registry("one")
        found = run_eval.main_copy(self.registries(one), "sample",
                                   "HTTPS://GITHUB.COM/OWNER/ONE.git")
        self.assertEqual(found[1], "bundle")

    def test_unknown_url(self):
        one = self.registry("one")
        self.assertEqual(self.code(self.registries(one), "sample",
                                   "https://github.com/Owner/other"),
                         "registry_unknown")

    def test_missing_checkout_for_url(self):
        one = self.registry("one")
        one["path"] = str(self.tmp / "absent")
        self.assertEqual(self.code(self.registries(one), "sample",
                                   one["url"]), "registry_checkout_missing")

    def test_no_copy(self):
        one = self.registry("one", skills=())
        self.assertEqual(self.code(self.registries(one), "sample", None),
                         "main_copy_missing")

    def test_two_bundles_are_ambiguous(self):
        one = self.registry("one", skills=(("a", "sample"), ("b", "sample")))
        with self.assertRaises(delivery.DeliveryError) as raised:
            run_eval.main_copy(self.registries(one), "sample", one["url"])
        self.assertEqual(raised.exception.code, "main_copy_ambiguous")
        self.assertIn("Owner/one:a", str(raised.exception))
        self.assertIn("Owner/one:b", str(raised.exception))

    def test_two_registries_are_ambiguous_without_a_url(self):
        regs = self.registries(self.registry("one"), self.registry("two"))
        self.assertEqual(self.code(regs, "sample", None), "main_copy_ambiguous")

    def test_two_registries_are_not_ambiguous_with_a_url(self):
        regs = self.registries(self.registry("one"), self.registry("two"))
        run_eval.main_copy(regs, "sample", "https://github.com/Owner/one")

    def test_tested_digest_matches_the_tree_digest(self):
        one = self.registry("one")
        path = Path(one["path"]) / "plugins" / "bundle" / "skills" / "sample"
        expected = context._file_digest(delivery._tree_files(path)[0])
        regs = self.registries(one)
        self.assertEqual(compute_gates.tested_digest(regs, "sample", None), expected)
        self.assertEqual(compute_gates.tested_digest(regs, "sample", one["url"]), expected)

    def test_tested_digest_is_none_for_each_refusal(self):
        one = self.registry("one", skills=(("a", "sample"), ("b", "sample")))
        gone = self.registry("gone")
        gone["path"] = str(self.tmp / "absent")
        two = self.registry("two")
        regs = self.registries(one, gone, two)
        for skill, url in (("sample", None),                      # ambiguous
                           ("sample", gone["url"]),               # checkout missing
                           ("sample", "https://github.com/x/y"),  # unknown
                           ("other", one["url"]),                 # no copy
                           ("../bad", None)):                     # invalid name
            with self.subTest(skill=skill, url=url):
                self.assertIsNone(compute_gates.tested_digest(regs, skill, url))


if __name__ == "__main__":
    unittest.main()
