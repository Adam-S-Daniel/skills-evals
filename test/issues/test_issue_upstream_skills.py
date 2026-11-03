"""Upstream skills are background, never subjects (Adam, 2026-11-03).

The self-improvement loop never evaluates, improves, trims, retires or drafts
a skill made by Anthropic (the claude.ai account skills and Claude Code's
bundled ones), and the draft loop never creates a skill that duplicates one.
`harness/upstream_skills.yml` lists the names; these tests hold the rule:
no fixture, no schedule entry and no registry names an upstream skill or an
Anthropic repository, and the draft loop's guards and its `upstream-covered`
decision behave. See docs/decisions/0005-improvement-loop-reuses-skill-creator.md.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent
ROOT = TEST_DIR.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(TEST_DIR))

import draft_new_skill as dns  # noqa: E402
import test_issue_draft_new_skill as helpers  # noqa: E402
import upstream_skills  # noqa: E402

LISTS = upstream_skills.load()
UPSTREAM = LISTS["anthropic_account"] | LISTS["claude_code_bundled"]


class UpstreamList(unittest.TestCase):
    def test_the_file_loads_and_both_groups_are_filled(self):
        self.assertEqual(set(LISTS), {"anthropic_account", "claude_code_bundled"})
        self.assertIn("pdf", LISTS["anthropic_account"])
        self.assertIn("loop", LISTS["claude_code_bundled"])

    def test_upstream_source(self):
        self.assertEqual(upstream_skills.upstream_source("anthropic-skills:pdf"),
                         "anthropic_account")
        self.assertEqual(upstream_skills.upstream_source("loop"), "claude_code_bundled")
        self.assertEqual(upstream_skills.upstream_source("deep-research"),
                         "anthropic_account")
        self.assertIsNone(upstream_skills.upstream_source("writing-adrs"))

    def test_load_rejects_a_malformed_file(self):
        good = {"schema": 1, "anthropic_account": ["a", "b"],
                "claude_code_bundled": ["c"]}
        bad = {"schema": {**good, "schema": 2}, "extra": {**good, "extra": []},
               "unsorted": {**good, "anthropic_account": ["b", "a"]},
               "repeat": {**good, "anthropic_account": ["a", "a"]},
               "name": {**good, "claude_code_bundled": ["Bad_Name"]},
               "missing": {"schema": 1, "anthropic_account": []}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "u.yml"
            path.write_text(yaml.safe_dump(good), encoding="utf-8")
            self.assertEqual(upstream_skills.load(path)["anthropic_account"],
                             frozenset({"a", "b"}))
            for label, doc in bad.items():
                with self.subTest(label):
                    path.write_text(yaml.safe_dump(doc), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        upstream_skills.load(path)


class LoopNeverTouchesUpstream(unittest.TestCase):
    def test_no_fixture_is_for_an_upstream_skill(self):
        seen = 0
        for path in sorted((ROOT / "evals").rglob("fixture.yaml")):
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            skill = doc.get("skill") if isinstance(doc, dict) else None
            if skill is None:
                continue
            seen += 1
            self.assertNotIn(upstream_skills.upstream_source(str(skill), LISTS), {
                "anthropic_account", "claude_code_bundled"}, str(path))
        self.assertGreater(seen, 10)

    def test_no_registry_is_anthropics_or_the_account_store(self):
        doc = yaml.safe_load((ROOT / "harness" / "registries.yml").read_text("utf-8"))
        self.assertTrue(doc["registries"])
        for row in doc["registries"]:
            for key in ("url", "path"):
                value = str(row.get(key, ""))
                self.assertNotIn("anthropics/", value, row["name"])
                self.assertNotIn("skills/synced", value, row["name"])

    def test_no_schedule_entry_names_an_upstream_skill(self):
        for name in ("scheduled.yml", "unscheduled.yml"):
            doc = yaml.safe_load((ROOT / "evals" / name).read_text("utf-8"))
            self.assertTrue(doc["fixtures"], name)
            for row in doc["fixtures"]:
                parts = Path(row["path"]).parts
                self.assertEqual(parts[0], "evals", row["path"])
                self.assertNotIn(parts[1], UPSTREAM, f"{name}: {row['path']}")


class DraftLoopGuards(helpers.Case):
    def setUp(self):
        super().setUp()
        self.lessons = self.tmp / "lessons"
        self.registry = self.tmp / "registry"
        self.registry.mkdir()
        self.evals = self.tmp / "evals"
        self.evals.mkdir()
        self.drafted = self.write(self.tmp / "drafted.txt", "")

    def select(self) -> dict:
        code, out, err = helpers.run_main(
            "select", "--lessons", str(self.lessons), "--registry",
            f"adam-agentskills={self.registry}", "--evals", str(self.evals),
            "--drafted", str(self.drafted))
        self.assertEqual(code, 0, err)
        return helpers.outputs(out)

    def test_select_skips_an_upstream_subject(self):
        self.write(self.lessons / "proposals/2026-10-26/pdf__new-skill.json",
                   helpers.proposal(subject="pdf", evidence_count=9))
        self.assertEqual(self.select()["count"], "0")
        mine = "proposals/2026-10-26/lint-before-push__new-skill.json"
        self.write(self.lessons / mine, helpers.proposal(evidence_count=1))
        self.assertEqual(self.select()["proposal"], mine)

    def test_upstream_covered_is_final(self):
        self.assertEqual(dns.eligibility("a", {"a": {"upstream-covered"}}, {"a"}),
                         (False, False))

    def run_covered(self, name="pdf", reason="The pdf skill already does this."):
        p = self.write(self.tmp / "payload.json", helpers.payload_doc())
        return helpers.run_main("upstream-covered", "--payload", str(p), "--skill",
                                name, "--reason", reason, "--results",
                                str(self.tmp / "results"))

    def test_upstream_covered_writes_a_record_the_check_accepts(self):
        for name, source in (("pdf", "anthropic_account"), ("loop", "claude_code_bundled"),
                             ("brand-new-upstream", "live")):
            with self.subTest(name):
                shutil.rmtree(self.tmp / "results", ignore_errors=True)
                code, out, err = self.run_covered(name)
                self.assertEqual(code, 0, err)
                root = self.tmp / "results" / "draft-skill" / helpers.RUN_ID
                self.assertEqual(sorted(p.name for p in root.iterdir()),
                                 ["report.md", "summary.json"])
                record = json.loads((root / "summary.json").read_text())
                self.assertEqual(record["decision"], "upstream-covered")
                self.assertEqual(record["upstream"], {"name": name, "source": source})
                self.assertEqual(dns.check_record(record, helpers.RUN_ID), record)
                self.assertTrue((root / "report.md").read_text().startswith(
                    f"# Upstream covered: {helpers.SUBJECT}\n"))

    def test_upstream_covered_refuses_bad_input(self):
        for label, kwargs in {"name": {"name": "Not A Name"},
                              "blank": {"reason": "  "},
                              "mention": {"reason": "ask @someone"}}.items():
            with self.subTest(label):
                shutil.rmtree(self.tmp / "results", ignore_errors=True)
                code, _, _ = self.run_covered(**kwargs)
                self.assertEqual(code, 2)
                self.assertFalse((self.tmp / "results").exists())

    def test_check_record_refuses_a_malformed_upstream_record(self):
        self.assertEqual(self.run_covered()[0], 0)
        path = self.tmp / "results" / "draft-skill" / helpers.RUN_ID / "summary.json"
        good = json.loads(path.read_text())
        for label, change in {"source": {"upstream": {"name": "pdf", "source": "x"}},
                              "extra": {"extra": 1}}.items():
            with self.subTest(label):
                with self.assertRaises(dns.Rejected):
                    dns.check_record({**good, **change}, helpers.RUN_ID)


class MeasureGuard(helpers.Case):
    def test_measure_rejects_an_upstream_subject_without_running_anything(self):
        registry = self.tmp / "registry"
        self.write(registry / f"plugins/{helpers.PLUGIN}/skills/other/SKILL.md",
                   "---\nname: other\ndescription: x\n---\n")
        self.write(registry / "README.md", "# Registry\n")
        helpers.git(registry, "init", "-q", "-b", "main")
        helpers.git(registry, "add", "-A")
        helpers.git(registry, "commit", "-q", "-m", "registry")
        sha = helpers.git(registry, "rev-parse", "HEAD")
        staging = self.tmp / "staging"
        for rel, data in helpers.skill_files().items():
            self.write(staging / "skill" / rel, data)
        for name, files in helpers.fixture_files().items():
            for rel, data in files.items():
                self.write(staging / "fixtures" / name / rel, data)
        self.write(staging / "plugin", helpers.PLUGIN + "\n")
        self.write(staging / "triage.json", {"mechanical": False, "reason": "A judgment."})
        p = self.write(self.tmp / "payload.json", helpers.payload_doc())
        # The subject is not in the shipped list, so stand it in for one.
        lists = {"anthropic_account": frozenset({helpers.SUBJECT}),
                 "claude_code_bundled": frozenset()}
        runner = helpers.FakeRunner(helpers.table())
        with mock.patch.object(upstream_skills, "load", return_value=lists):
            code, _, err = helpers.run_main(
                "measure", "--staging", str(staging), "--registry",
                f"adam-agentskills={registry}", "--ref", sha, "--payload", str(p),
                "--trials", "1", "--results", str(self.tmp / "results"), runner=runner)
        self.assertEqual(code, 1, err)
        self.assertEqual(runner.calls, [])
        record = json.loads((self.tmp / "results" / "draft-skill" / helpers.RUN_ID
                             / "summary.json").read_text())
        self.assertEqual(record["decision"], "rejected")
        self.assertEqual(record["reasons"], [dns.UPSTREAM_REFUSAL])


class GateValidates(helpers.Case):
    """validate's record check accepts an upstream-covered branch and refuses
    extra files; an accepted record for an upstream subject is rejected.
    Borrows the branch-building helpers without inheriting (and so rerunning)
    the draft-loop suite's own validate tests."""

    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "evals-repo"
        self.repo.mkdir()
        helpers.git(self.repo, "init", "-q", "-b", "main")
        self.write(self.repo / "README.md", "base\n")
        helpers.git(self.repo, "add", "-A")
        helpers.git(self.repo, "commit", "-q", "-m", "base")
        self.registry = self.tmp / "agentskills"
        (self.registry / "plugins" / helpers.PLUGIN / "skills").mkdir(parents=True)

    accepted_files = helpers.Validate.accepted_files
    branch = helpers.Validate.branch
    validate = helpers.Validate.validate
    assert_rejected = helpers.Validate.assert_rejected

    def covered_files(self) -> dict[str, bytes]:
        prefix = f"draft-skill/{helpers.RUN_ID}/"
        record = {"schema": 1, "run_id": helpers.RUN_ID,
                  "decision": "upstream-covered", "subject": helpers.SUBJECT,
                  "evidence_count": 3, "proposal": helpers.payload_doc()["proposal"],
                  "upstream": {"name": "pdf", "source": "anthropic_account"},
                  "reason": "The pdf skill already does this."}
        report = dns.upstream_report(helpers.SUBJECT, 3, "pdf", record["reason"])
        return {prefix + "summary.json": json.dumps(record).encode(),
                prefix + "report.md": report.encode()}

    def test_an_upstream_covered_branch_is_staged(self):
        self.branch(self.covered_files())
        code, out, err = self.validate(registry=False)
        self.assertEqual(code, 0, err)
        self.assertEqual(out["decision"], "upstream-covered")

    def test_an_upstream_covered_branch_with_a_patch_is_rejected(self):
        files = self.covered_files()
        files[f"draft-skill/{helpers.RUN_ID}/skill.patch"] = b"x\n"
        self.assert_rejected(files, registry=False)

    def test_an_accepted_record_for_an_upstream_subject_is_rejected(self):
        files = self.accepted_files()
        renamed = {}
        for path, data in files.items():
            renamed[path.replace(helpers.SUBJECT, "pdf")] = (
                data.decode().replace(helpers.SUBJECT, "pdf").encode())
        self.branch(renamed)
        code, _, err = self.validate()
        self.assertEqual(code, 1, err)
        self.assertIn("duplicates an Anthropic", err)


if __name__ == "__main__":
    unittest.main()
