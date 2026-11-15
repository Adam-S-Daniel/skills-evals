"""Target arrivals are counted from git history (scripts/target_arrivals.py,
Adam 2026-11-15: never a hand count). Synthetic repositories built in a
temporary directory with fixed commit dates: no network, no clock."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
import target_arrivals as ta  # noqa: E402

AS_OF = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)

REGISTRIES = """\
registries:
  - name: pub
    url: https://github.com/o/pub
    layout: "plugins/*/skills/*/SKILL.md"
    private: false
  - name: priv
    url: https://github.com/o/priv
    layout: "plugins/*/skills/*/SKILL.md"
    private: true
"""

CONFIG = """\
rate_weeks: 4
sources:
  - kind: guidance-section
    repo: o/guide
    path: agents-md/eval-coverage.yml
    parser: eval-coverage
  - kind: git-hook
    repo: o/guide
    path: .agent-checks/local.sh
    parser: repo-local
"""


def _git(root: Path, *args: str, when: str | None = None) -> None:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    if when:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True, env=env)


class Repo:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True)
        _git(root, "init", "-q", "-b", "main")

    def commit(self, when: str, files: dict | None = None, delete: tuple = ()):
        for rel, text in (files or {}).items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for rel in delete:
            (self.root / rel).unlink()
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "--allow-empty", "-m", "c", when=when)


def skill(plugin: str, name: str) -> dict:
    return {f"plugins/{plugin}/skills/{name}/SKILL.md": f"---\nname: {name}\n---\n"}


def coverage(rows: dict) -> dict:
    return {"agents-md/eval-coverage.yml": yaml.safe_dump(
        [{"id": k, "status": v} for k, v in rows.items()])}


class Fixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        (self.tmp / "config.yml").write_text(CONFIG, encoding="utf-8")
        (self.tmp / "registries.yml").write_text(REGISTRIES, encoding="utf-8")
        self.checkouts = self.tmp / "co"
        pub = Repo(self.checkouts / "o__pub")
        pub.commit("2026-09-01T12:00:00Z", {**skill("p", "alpha"), **skill("p", "beta")})
        pub.commit("2026-10-27T12:00:00Z", skill("p", "gamma"))
        pub.commit("2026-11-03T12:00:00Z", delete=("plugins/p/skills/alpha/SKILL.md",))
        pub.commit("2026-11-04T12:00:00Z", {"README.md": "unrelated\n"})
        priv = Repo(self.checkouts / "o__priv")
        priv.commit("2026-09-01T12:00:00Z", skill("q", "secret-one"))
        priv.commit("2026-11-10T12:00:00Z", skill("q", "secret-two"))
        guide = Repo(self.checkouts / "o__guide")
        guide.commit("2026-08-01T12:00:00Z", {"README.md": "x\n"})
        guide.commit("2026-09-01T12:00:00Z", coverage({"one": "covered"}))
        guide.commit("2026-10-28T12:00:00Z", coverage({"one": "covered", "two": "gap",
                                                       "three": "skipped"}))
        guide.commit("2026-11-11T12:00:00Z", {".agent-checks/local.sh": "#!/bin/bash\n"})

    def build(self, usage=None, exempt=frozenset(), checkouts=None):
        weeks, sources = ta.load_sources(self.tmp / "config.yml", self.tmp / "registries.yml")
        return ta.build(sources, weeks, checkouts or self.checkouts, AS_OF, usage, exempt)


class Sources(Fixture):
    def test_skills_come_from_every_registry(self):
        _, sources = ta.load_sources(self.tmp / "config.yml", self.tmp / "registries.yml")
        skills = [(s["repo"], s["private"]) for s in sources if s["kind"] == "skill"]
        self.assertEqual(skills, [("o/pub", False), ("o/priv", True)])
        self.assertEqual(ta.repos(sources), [("o/guide", False), ("o/priv", True), ("o/pub", False)])

    def test_a_parser_its_kind_does_not_take_is_refused(self):
        (self.tmp / "config.yml").write_text(CONFIG.replace("parser: repo-local",
                                                            "parser: eval-coverage"))
        with self.assertRaises(ta.ArrivalsError):
            ta.load_sources(self.tmp / "config.yml", self.tmp / "registries.yml")

    def test_a_repo_private_anywhere_is_private_for_every_source(self):
        (self.tmp / "config.yml").write_text(CONFIG + """\
  - kind: git-hook
    repo: o/priv
    path: .agent-checks/local.sh
    parser: repo-local
""")
        _, sources = ta.load_sources(self.tmp / "config.yml", self.tmp / "registries.yml")
        self.assertTrue(all(s["private"] for s in sources if s["repo"] == "o/priv"))

    def test_the_committed_config_loads(self):
        weeks, sources = ta.load_sources(ROOT / "evals" / "target-sources.yml")
        self.assertGreaterEqual(weeks, 1)
        self.assertEqual({s["kind"] for s in sources}, set(ta.KINDS))


class Counting(Fixture):
    def test_baseline_is_not_counted_and_changes_are(self):
        doc = self.build()
        public = [(i["kind"], i["event"], i["name"]) for i in doc["items"] if i["repo"] == "o/pub"]
        self.assertEqual(public, [("skill", "added", "gamma"), ("skill", "removed", "alpha")])
        sections = [(i["event"], i["name"]) for i in doc["items"] if i["kind"] == "guidance-section"]
        self.assertEqual(sections, [("added", "three"), ("added", "two")])

    def test_a_private_registry_is_counted_without_names(self):
        doc = self.build()
        private = [i for i in doc["items"] if i["repo"] is None]
        self.assertEqual([(i["event"], i["name"], i["week"]) for i in private],
                         [("added", None, "2026-11-09")])
        self.assertNotIn("secret", json.dumps(doc))

    def test_a_repo_local_file_appearing_is_an_addition(self):
        hooks = [i for i in self.build()["items"] if i["kind"] == "git-hook"]
        self.assertEqual([(i["name"], i["week"]) for i in hooks],
                         [("repo-local:o/guide", "2026-11-09")])

    def test_weekly_rows_sum_by_kind(self):
        rows = {(r["week"], r["kind"]): r for r in self.build()["weeks"]}
        self.assertEqual(rows[("2026-11-09", "skill")]["added"], 1)
        self.assertEqual(rows[("2026-11-02", "skill")]["removed"], 1)
        self.assertEqual(rows[("2026-10-26", "guidance-section")]["added"], 2)


class Eligibility(Fixture):
    def test_sections_are_eligible_unless_skipped(self):
        found = {i["name"]: i["eligible"] for i in self.build()["items"]
                 if i["kind"] == "guidance-section"}
        self.assertEqual(found, {"two": True, "three": False})

    def test_skill_eligibility_is_first_recorded_use_or_exempt(self):
        with mock.patch("skill_usage.has_recorded_use", return_value=None) as used:
            doc = self.build(usage={"stand-in": True}, exempt=frozenset({"gamma"}))
        gamma = next(i for i in doc["items"] if i["name"] == "gamma")
        self.assertIs(gamma["eligible"], True)
        unknown = next(i for i in doc["items"] if i["kind"] == "skill" and i["repo"] is None)
        self.assertIsNone(unknown["eligible"])
        used.assert_called_once()

    def test_a_skill_since_removed_is_not_eligible(self):
        judge = ta.skill_eligibility({("o/pub", "skill"): frozenset({"beta"})}, None, AS_OF, {},
                                     frozenset({"alpha"}))
        self.assertIs(judge("o/pub", "alpha"), False)


class Rates(Fixture):
    def test_rates_over_the_window_ending_at_as_of(self):
        rates = self.build()["rates"]
        sections = rates["guidance-section"]
        self.assertTrue(sections["complete"])
        self.assertEqual((sections["weeks"], sections["added"]), (4, 2))
        self.assertAlmostEqual(sections["added_per_week"], 0.5)
        self.assertAlmostEqual(sections["eligible_share"], 0.5)

    def test_a_missing_source_makes_its_kind_unknown_not_zero(self):
        import shutil
        shutil.rmtree(self.checkouts / "o__priv")
        doc = self.build()
        self.assertFalse(doc["rates"]["skill"]["complete"])
        self.assertIsNone(doc["rates"]["skill"]["added_per_week"])
        self.assertIn("unreadable", [s["status"] for s in doc["sources"]])
        self.assertTrue(doc["rates"]["guidance-section"]["complete"])

    def test_a_shallow_clone_is_unreadable(self):
        shallow = self.tmp / "shallow"
        shallow.mkdir()
        for name in ("o__pub", "o__priv", "o__guide"):
            subprocess.run(["git", "clone", "-q", "--depth", "1",
                            f"file://{self.checkouts / name}", str(shallow / name)],
                           check=True, capture_output=True)
        doc = self.build(checkouts=shallow)
        self.assertEqual({s["status"] for s in doc["sources"]}, {"unreadable"})

    def test_the_window_starts_no_earlier_than_the_newest_baseline(self):
        hooks = self.build()["rates"]["git-hook"]
        # o/guide's first commit (2026-08-01) is the repo-local baseline,
        # older than the window, so the window keeps its four weeks.
        self.assertEqual((hooks["weeks"], hooks["added"]), (4, 1))

    def test_the_window_is_cut_to_a_late_baseline(self):
        import shutil
        shutil.rmtree(self.checkouts / "o__priv")
        priv = Repo(self.checkouts / "o__priv")
        priv.commit("2026-11-01T12:00:00Z", skill("q", "late"))
        skills = self.build()["rates"]["skill"]
        # o/priv began on 2026-11-01 12:00, two weeks before as-of; o/pub's
        # removal of alpha (2026-11-03) is the one change inside that cut.
        self.assertEqual((skills["from"], skills["weeks"]), ("2026-11-01T12:00:00Z", 2))
        self.assertEqual((skills["added"], skills["removed"]), (0, 1))
        self.assertAlmostEqual(skills["removed_per_week"], 0.5)

    def test_a_cut_window_under_a_week_is_no_rate(self):
        import shutil
        shutil.rmtree(self.checkouts / "o__priv")
        Repo(self.checkouts / "o__priv").commit("2026-11-12T12:00:00Z", skill("q", "late"))
        skills = self.build()["rates"]["skill"]
        self.assertIsNone(skills["added_per_week"])

    def test_skill_rates_count_public_and_private(self):
        skills = self.build()["rates"]["skill"]
        # gamma (2026-10-27) and the private addition (2026-11-10) added,
        # alpha (2026-11-03) removed, all inside the four weeks.
        self.assertEqual((skills["added"], skills["removed"], skills["weeks"]), (2, 1, 4))

    def test_a_failed_blob_fetch_is_unreadable_not_a_deletion(self):
        partial = self.tmp / "partial"
        partial.mkdir()
        for name in ("o__pub", "o__priv", "o__guide"):
            _git(self.checkouts / name, "config", "uploadpack.allowFilter", "true")
            subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
                            f"file://{self.checkouts / name}", str(partial / name)],
                           check=True, capture_output=True)
        _git(partial / "o__guide", "remote", "set-url", "origin", f"file://{self.tmp}/gone")
        doc = self.build(checkouts=partial)
        status = {(s["repo"], s["parser"]): s["status"] for s in doc["sources"]}
        self.assertEqual(status[("o/guide", "eval-coverage")], "unreadable")
        # Presence comes from trees, so repo-local and skills still read.
        self.assertEqual(status[("o/guide", "repo-local")], "ok")
        self.assertTrue(doc["rates"]["skill"]["complete"])
        self.assertFalse(doc["rates"]["guidance-section"]["complete"])


@unittest.skipUnless(__import__("importlib").util.find_spec("tree_sitter_bash"),
                     "tree-sitter-bash is not installed")
class AgentChecksParser(unittest.TestCase):
    def test_check_ids_come_from_the_bash_parse(self):
        import explorer_public
        source = textwrap.dedent("""\
            note_ran pr-tldr
            lesson_checks="one-a two-b"
            # note_ran commented-out
            note_ran "$dynamic"
        """).encode()
        self.assertEqual(explorer_public.fleet_check_ids(source), {"pr-tldr", "one-a", "two-b"})


class Workflow(unittest.TestCase):
    def setUp(self):
        self.doc = yaml.safe_load((ROOT / ".github" / "workflows" / "target-arrivals.yml")
                                  .read_text(encoding="utf-8"))

    def test_only_publish_writes(self):
        jobs = self.doc["jobs"]
        self.assertEqual(jobs["build"]["permissions"], {"contents": "read"})
        self.assertEqual(jobs["publish"]["permissions"], {"contents": "write"})
        self.assertEqual(self.doc["permissions"], {})

    def test_the_private_token_reaches_one_step(self):
        steps = [s for s in self.doc["jobs"]["build"]["steps"]
                 if "private-token.outputs.token" in json.dumps(s)]
        self.assertEqual([s["name"] for s in steps],
                         ["Clone the source repositories (full history, no blobs)"])

    def test_no_event_value_reaches_a_run_block(self):
        for job in self.doc["jobs"].values():
            for step in job["steps"]:
                self.assertNotIn("${{", step.get("run", ""))


if __name__ == "__main__":
    unittest.main()
