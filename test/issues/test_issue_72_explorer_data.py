#!/usr/bin/env python3
"""skills-evals#72: scripts/explorer_data.py and .github/workflows/explorer-data.yml.

The explorer document is public, so the tests pin what it must carry (the
contract's shape, the paired-run counts, the guidance modes, the alerts) and,
above all, what it must never carry: a private registry's skill, a skill with
no census row, a session id or a digest.

Hermetic: a small synthetic results tree of invented data, no network, no
clock.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import shutil
import unittest
from unittest import mock
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import explorer_data  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "explorer-data.yml"
SHA_A, SHA_B = "a" * 40, "b" * 40
AS_OF = "2026-10-31T21:00:00Z"
SESSION = "cse_" + "x" * 24  # invented; must never reach the document
DIGEST = "d" * 64
GUIDANCE_DIGESTS = {"section": DIGEST, "rest": "e" * 64}

ROSTER = {"arms": [{"id": "model-a", "reason": "invented reason a"}],
          "judge": {"id": "model-j", "reason": "invented judge reason"}}


def census(public_skills, private_names=()):
    return {"include_private_names": False, "problems": [],
            "publication": {"as_of": "2026-10-31T14:00:00Z"},
            "registries": [
                {"name": "pub", "private": False, "names_withheld": False,
                 "counts": {"covered": len(public_skills), "skipped": 1, "gap": 0,
                            "total": len(public_skills) + 1},
                 "skills": [{"skill": s, "bundle": "bundle-one", "status": "covered",
                             "reason": None, "fixtures": 1} for s in public_skills]
                 + [{"skill": "skipped-skill", "bundle": None, "status": "skipped",
                     "reason": "invented skip reason", "fixtures": 0}]},
                {"name": "priv", "private": True, "names_withheld": True,
                 "counts": {"covered": 1, "skipped": 0, "gap": 0, "total": 1},
                 "skills": [{"skill": s, "status": "covered"} for s in private_names]}]}


class Tree:
    """A results tree on disk, built one arm at a time."""

    def __init__(self, test: unittest.TestCase):
        tmp = tempfile.TemporaryDirectory(prefix="explorer-")
        test.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.tree = self.root / "tree"
        self.evals = self.root / "evals"
        self.evals.mkdir()
        self.roster = self.root / "roster.yml"
        self.roster.write_text(yaml.safe_dump(ROSTER))
        self.policy = self.root / "policy.yml"
        self.policy.write_text((ROOT / "evals" / "gate-policy.yml").read_text(encoding="utf-8"))
        self.write_json("coverage/latest.json", census(["alpha", "beta", "gamma"]))

    def write_json(self, rel, doc):
        path = self.tree / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc), encoding="utf-8")

    @staticmethod
    def trial(passed, total, judge, cost, error=None):
        return {"error": error, "agent": {"cost_usd": cost},
                "objective_checks": [{"id": f"c{i}", "passed": i < passed} for i in range(total)],
                "judge": ({"overall": judge, "dimensions": []} if judge is not None
                          else {"status": "skipped"}),
                "harness": {"version": "2.1.300 (Claude Code)"},
                "cross_model": {"model": "model-a"}}

    def skill_arm(self, skill, stamp, arm, trials, fixture=None):
        base = self.tree / "results" / skill / stamp
        arm_dir = base / (f"{fixture}/{arm}" if fixture else arm)
        arm_dir.mkdir(parents=True, exist_ok=True)
        (base / "report.md").write_text("report\n")
        for k, t in enumerate(trials, 1):
            (arm_dir / f"trial-{k}").mkdir(exist_ok=True)
            (arm_dir / f"trial-{k}" / "summary.json").write_text(json.dumps(
                {"skill": skill, **t}))
        (arm_dir / "summary.json").write_text(json.dumps({
            "skill": skill, "n": len(trials), "errors": sum(1 for t in trials if t["error"]),
            "aggregate": {}, "run": {"id": stamp, "session_id": SESSION,
                                     "harness_commit": "f" * 40},
            "harness": {"version": "2.1.300 (Claude Code)"},
            "cross_model": {"model": "model-a"}}))

    def pair(self, skill, stamp, with_trials, without_trials, fixture=None):
        self.skill_arm(skill, stamp, "with_skill", with_trials, fixture)
        self.skill_arm(skill, stamp, "without_skill", without_trials, fixture)

    def guidance_arm(self, section, stamp, arm, mode, passed, total=4):
        run_dir = self.tree / "results" / "guidance" / section / stamp
        (run_dir / arm).mkdir(parents=True, exist_ok=True)
        (run_dir / "report.md").write_text("report\n")
        (run_dir / arm / "summary.json").write_text(json.dumps({
            "subject": "guidance", "section": section, "mode": mode, "arm": arm,
            "error": None, "agent": {"cost_usd": 0.5},
            "objective_checks": [{"id": f"c{i}", "passed": i < passed} for i in range(total)],
            "judge": {"overall": 8.0, "dimensions": []},
            "harness": {"version": "2.1.301 (Claude Code)"},
            "cross_model": {"model": "model-a"},
            "run": {"id": stamp, "session_id": SESSION},
            "fixture_name": "fx", "fixture_digest": DIGEST,
            "guidance_digests": GUIDANCE_DIGESTS, "judge_conditional": False}))

    def build(self, manifest=None, issues=None):
        return explorer_data.build(
            self.tree, self.roster, self.policy, self.evals, AS_OF, SHA_A, SHA_B,
            manifest=manifest or [], issues=issues)


MANIFEST = [
    {"id": "sec-one", "heading": "Section one", "bytes": 100, "status": "covered"},
    {"id": "sec-two", "heading": "Section two", "bytes": 200, "status": "skipped",
     "reason": "invented reason"}]


class ShapeAndMathTests(unittest.TestCase):

    def setUp(self):
        self.t = Tree(self)
        # alpha: 3 trials each arm; one trial per arm has no judge figure.
        self.t.pair("alpha", "20261030T100000Z",
                    [Tree.trial(4, 5, 8.0, 0.25), Tree.trial(5, 5, 9.0, 0.25),
                     Tree.trial(3, 5, None, 0.5)],
                    [Tree.trial(1, 5, 4.0, 0.125), Tree.trial(2, 5, 5.0, 0.125),
                     Tree.trial(0, 5, None, 0.25)])
        self.t.pair("alpha", "20261029T100000Z", [Tree.trial(5, 5, 8.0, 0.25)],
                    [Tree.trial(0, 5, 3.0, 0.25)], fixture="fx-one")
        # beta: a with arm only, so no paired run.
        self.t.skill_arm("beta", "20261030T110000Z", "with_skill", [Tree.trial(5, 5, 8.0, 0.1)])
        self.doc = self.t.build()

    def skill(self, name):
        return next(s for s in self.doc["skills"] if s["name"] == name)

    def test_top_level_keys_and_types(self):
        d = self.doc
        # No `broken_unknown`: #544's alert is retired (#559).
        self.assertEqual(sorted(d), ["alerts", "context_drift_unknown",
                                     "coverage", "fires_without_results",
                                     "fixture_queue", "generated_at",
                                     "guidance", "lessons", "newest_run", "policy", "removed_skills",
                                     "roster", "schema_version",
                                     "skills", "source", "usage"])
        self.assertIsNone(d["usage"])
        # No evals/scheduled.yml, so no fixture is in the #545 scope, nor in
        # #555's: no fire file either, so the summary is unknown.
        self.assertIsNone(d["fires_without_results"])
        # No --fixture-queue report: unknown, not an empty queue.
        self.assertIsNone(d["fixture_queue"])
        # No --lessons directory: unknown, not an empty list.
        self.assertIsNone(d["lessons"])
        self.assertEqual(d["context_drift_unknown"], 0)
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["generated_at"], AS_OF)
        self.assertEqual(d["newest_run"], "2026-10-30T10:00:00Z")
        self.assertEqual(d["source"], {"repository": "Adam-S-Daniel/skills-evals",
                                       "repository_commit": SHA_A, "results_commit": SHA_B})
        self.assertEqual(d["roster"], {"arms": [{"model": "model-a", "reason": "invented reason a"}],
                                       "judge": {"model": "model-j",
                                                 "reason": "invented judge reason"}})
        self.assertEqual(d["policy"], {"benefit_confidence": 0.80, "retire_confidence": 0.90,
                                       "min_cli_versions": 2, "objective_margin": 0.15,
                                       "max_runs_per_cell": 40})
        self.assertIsInstance(d["skills"], list)
        self.assertIsInstance(d["guidance"]["sections"], list)
        self.assertIsInstance(d["alerts"], list)
        self.assertEqual(d["coverage"], {"as_of": "2026-10-31T14:00:00Z", "covered": 3,
                                         "skipped": 1, "gap": 0, "total": 4})
        for s in d["skills"]:
            self.assertEqual(sorted(s), ["bundle", "confidence", "copies", "current_text_runs",
                                         "description", "name",
                                         "next_test", "registry", "runs", "skip_reason",
                                         "stakes", "status", "usage", "verdict",
                                         "verdict_reason"])
            # No evals/stakes.yml row: normal.
            self.assertEqual(s["stakes"], {"level": "normal"})
            # No usage census in the tree: unknown, not zero. No schedule: no test.
            self.assertIsNone(s["usage"])
            self.assertIsNone(s["copies"])
            self.assertEqual(s["next_test"], {"position": None, "band": None, "due": None,
                                              "scheduled": False})

    def test_with_and_without_are_paired_and_counted(self):
        runs = self.skill("alpha")["runs"]
        self.assertEqual([r["at"] for r in runs],
                         ["2026-10-30T10:00:00Z", "2026-10-29T10:00:00Z"])
        run = runs[0]
        self.assertEqual(run["fixture"], None)
        self.assertEqual(run["model"], "model-a")
        self.assertEqual(run["cli_version"], "2.1.300")
        self.assertEqual(run["with"], {"trials": 3, "checks_passed": 12, "checks_total": 15,
                                       "judge_mean": 8.5, "cost_usd": 1.0})
        self.assertEqual(run["without"], {"trials": 3, "checks_passed": 3, "checks_total": 15,
                                          "judge_mean": 4.5, "cost_usd": 0.5})
        self.assertEqual(run["report_url"],
                         "https://github.com/Adam-S-Daniel/skills-evals/blob/persistent/"
                         "eval-results/results/alpha/20261030T100000Z/report.md")
        self.assertEqual(runs[1]["fixture"], "fx-one")

    def test_the_description_comes_from_the_registry_skill_md(self):
        reg = self.t.root / "reg"
        md = reg / "plugins" / "bundle-one" / "skills" / "alpha" / "SKILL.md"
        md.parent.mkdir(parents=True)
        md.write_text("---\nname: alpha\ndescription: >-\n  Do the alpha thing\n  with @scope/pkg.\n"
                      "  Use when asked.\n---\nbody\n", encoding="utf-8")
        nested = reg / "plugins" / "bundle-one" / "skills" / "beta" / "SKILL.md"
        nested.parent.mkdir(parents=True)
        nested.write_text("no front matter\n", encoding="utf-8")
        doc = explorer_data.build(self.t.tree, self.t.roster, self.t.policy, self.t.evals, AS_OF,
                                  SHA_A, SHA_B, registries={"pub": {"path": reg}}, manifest=[])
        by = {s["name"]: s for s in doc["skills"]}
        self.assertEqual(by["alpha"]["description"],
                         "Do the alpha thing with scope/pkg. Use when asked.")
        self.assertIsNone(by["beta"]["description"])
        self.assertIsNone(by["gamma"]["description"])
        explorer_data.finish(doc)  # the dropped @ keeps the safety net quiet
        self.assertIsNone(explorer_data.skill_description({"pub": {"path": reg}}, "pub", ".."))
        self.assertIsNone(explorer_data.skill_description(None, "pub", "alpha"))

    def test_stakes_rows_reach_the_document(self):
        (self.t.evals / "alpha").mkdir(parents=True, exist_ok=True)
        (self.t.evals / "stakes.yml").write_text(
            "skills:\n  - {skill: alpha, stakes: high, reason: invented reason}\n",
            encoding="utf-8")
        by = {s["name"]: s for s in self.t.build()["skills"]}
        self.assertEqual(by["alpha"]["stakes"], {"level": "high", "reason": "invented reason",
                                                 "covered_by": None})
        self.assertEqual(by["beta"]["stakes"], {"level": "normal"})

    def test_an_unpaired_run_is_not_listed(self):
        self.assertEqual(self.skill("beta")["runs"], [])
        self.assertEqual(self.skill("gamma")["runs"], [])

    def test_census_fields_ride_along(self):
        s = self.skill("alpha")
        self.assertEqual((s["registry"], s["bundle"], s["status"], s["skip_reason"]),
                         ("pub", "bundle-one", "covered", None))
        skipped = self.skill("skipped-skill")
        self.assertEqual((skipped["status"], skipped["skip_reason"], skipped["verdict"]),
                         ("skipped", "invented skip reason", None))

    def test_errored_and_infrastructure_trials_do_not_count(self):
        t = Tree(self)
        t.pair("alpha", "20261030T100000Z",
               [Tree.trial(5, 5, 8.0, 0.25), Tree.trial(0, 5, None, 0.25,
                                                         error={"type": "timeout"})],
               [Tree.trial(1, 5, 4.0, 0.125), Tree.trial(1, 5, 4.0, 0.125)])
        run = next(s for s in t.build()["skills"] if s["name"] == "alpha")["runs"][0]
        self.assertEqual(run["with"]["trials"], 1)
        self.assertEqual(run["with"]["checks_total"], 5)
        # An arm with no counted trial drops the whole pair.
        t2 = Tree(self)
        t2.pair("alpha", "20261030T100000Z", [Tree.trial(0, 5, None, 0.1, error={"type": "timeout"})],
                [Tree.trial(1, 5, 4.0, 0.125)])
        self.assertEqual(next(s for s in t2.build()["skills"] if s["name"] == "alpha")["runs"], [])

    def test_the_document_serializes_with_full_precision_and_no_nan(self):
        text = explorer_data.finish(self.doc)
        self.assertEqual(json.loads(text), self.doc)
        self.assertTrue(text.endswith("}\n"))
        self.assertEqual(text, json.dumps(self.doc, indent=1, sort_keys=True,
                                          allow_nan=False) + "\n")


class PrivacyTests(unittest.TestCase):

    def test_a_private_registry_skill_with_runs_is_excluded(self):
        t = Tree(self)
        t.write_json("coverage/latest.json", census(["alpha"], private_names=["secret-skill"]))
        for name in ("alpha", "secret-skill"):
            t.pair(name, "20261030T100000Z", [Tree.trial(5, 5, 8.0, 0.1)],
                   [Tree.trial(1, 5, 4.0, 0.1)])
        doc = t.build()
        names = [s["name"] for s in doc["skills"]]
        self.assertIn("alpha", names)
        self.assertNotIn("secret-skill", names)
        self.assertNotIn("secret-skill", explorer_data.finish(doc))
        self.assertEqual(doc["coverage"]["total"], 2)  # the private registry is not counted

    def test_a_skill_with_runs_but_no_census_row_is_dropped(self):
        t = Tree(self)
        t.pair("retired-skill", "20261030T100000Z", [Tree.trial(5, 5, 8.0, 0.1)],
               [Tree.trial(1, 5, 4.0, 0.1)])
        self.assertNotIn("retired-skill", explorer_data.finish(t.build()))

    def test_no_session_id_or_digest_reaches_the_document(self):
        t = Tree(self)
        t.pair("alpha", "20261030T100000Z", [Tree.trial(5, 5, 8.0, 0.1)],
               [Tree.trial(1, 5, 4.0, 0.1)])
        t.guidance_arm("sec-one", "20261030T120000Z", "with_guidance_full", "full", 4)
        text = explorer_data.finish(t.build(manifest=MANIFEST))
        for forbidden in ("cse_", "session", "harness_commit", DIGEST, "e" * 64, "f" * 40):
            self.assertNotIn(forbidden, text)

    def test_the_safety_net_refuses_what_the_contract_forbids(self):
        base = {"a": "fine https://github.com/Adam-S-Daniel/skills-evals/blob/x@y"}
        explorer_data.finish(base)  # an '@' inside a URL is allowed
        for label, value in (("session id", SESSION), ("session_", "session_01abc"),
                             ("e-mail", "someone@example.com"), ("digest", DIGEST),
                             ("uppercase digest", DIGEST.upper())):
            with self.subTest(label), self.assertRaises(explorer_data.Refused):
                explorer_data.finish({"a": value})
        with self.assertRaises(ValueError):
            explorer_data.finish({"a": float("nan")})

    def test_the_cli_exits_2_and_writes_nothing_when_the_safety_net_trips(self):
        t = Tree(self)
        t.write_json("regressions/latest.json", {"rows": [
            {"subject": "skill", "id": "alpha", "fixture": "fx", "model": "model-a",
             "verdict": "regressed", "reason": f"saw {SESSION} in a log"}]})
        out = t.root / "out" / "latest.json"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = explorer_data.main([
                "--results-tree", str(t.tree), "--roster", str(t.roster),
                "--policy", str(t.policy), "--evals-dir", str(t.evals), "--as-of", AS_OF,
                "--repository-commit", SHA_A, "--results-commit", SHA_B, "--out", str(out)])
        self.assertEqual(code, 2)
        self.assertIn("refusing to publish", err.getvalue())
        self.assertFalse(out.exists())

    def test_the_cli_writes_the_document_and_checks_the_commits(self):
        t = Tree(self)
        out = t.root / "out" / "latest.json"
        args = ["--results-tree", str(t.tree), "--roster", str(t.roster),
                "--policy", str(t.policy), "--evals-dir", str(t.evals), "--as-of", AS_OF,
                "--results-commit", SHA_B, "--out", str(out)]
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(explorer_data.main([*args, "--repository-commit", "main"]), 2)
        self.assertEqual(explorer_data.main([*args, "--repository-commit", SHA_A]), 0)
        self.assertEqual(json.loads(out.read_text())["schema_version"], 1)


class RemovedSectionsTests(unittest.TestCase):
    """#557 (Adam, 2026-11-02): the page lists every removed section with its
    date and a link to its removal pull request, whose Revert button
    restores it."""

    def test_remove_entries_are_listed_newest_first(self):
        root = Path(tempfile.mkdtemp(prefix="removed-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "docs").mkdir()
        (root / "docs" / "guidance-impact.md").write_text(
            "# Guidance impact\n\n## Entry format\n\ntext\n\n"
            "## 2026-11-20 — bravo — remove\n- Motivation: m\n\n"
            "## 2026-11-18 — alpha — add\n- Motivation: m\n\n"
            "## 2026-11-10 — charlie — remove\n- Motivation: m\n", encoding="utf-8")
        removed = explorer_data.removed_sections(root)
        self.assertEqual([(r["id"], r["date"]) for r in removed],
                         [("bravo", "2026-11-20"), ("charlie", "2026-11-10")])
        self.assertEqual(removed[0]["reverse_url"],
                         "https://github.com/Adam-S-Daniel/_agent-guidance/pulls"
                         "?q=is%3Apr+head%3Aretire-guidance%2Fbravo")

    def test_removed_skills_come_from_the_registrys_impact_file(self):
        root = Path(tempfile.mkdtemp(prefix="removed-skills-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "docs").mkdir()
        (root / "docs" / "skill-impact.md").write_text(
            "# Skill impact\n\n## 2026-11-21 — adam-coding-anywhere/example-skill — remove\n\n"
            "- Motivation: m\n\n## 2026-11-19 — adam-coding-anywhere/other — edit\n\n- m\n",
            encoding="utf-8")
        removed = explorer_data.removed_skills({"adam-agentskills": {"path": root}})
        self.assertEqual([(r["name"], r["plugin"], r["date"]) for r in removed],
                         [("example-skill", "adam-coding-anywhere", "2026-11-21")])
        self.assertIn("head%3Aretire-skill%2Fexample-skill", removed[0]["reverse_url"])
        self.assertEqual(explorer_data.removed_skills({}), [])
        self.assertEqual(explorer_data.removed_skills({"other-registry": {"path": root}}), [])

    def _skill_urls(self, body: str) -> dict:
        root = Path(tempfile.mkdtemp(prefix="removed-skills-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "docs").mkdir()
        (root / "docs" / "skill-impact.md").write_text(
            "# Skill impact\n\n## 2026-11-21 — plug-one/gamma-skill — remove\n\n" + body +
            "\n## 2026-11-19 — plug-one/other — edit\n\n- See PR #999.\n", encoding="utf-8")
        return {r["name"]: r["reverse_url"]
                for r in explorer_data.removed_skills({"adam-agentskills": {"path": root}})}

    def _section_urls(self, body: str) -> dict:
        root = Path(tempfile.mkdtemp(prefix="removed-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "docs").mkdir()
        (root / "docs" / "guidance-impact.md").write_text(
            "# Guidance impact\n\n## 2026-11-20 — delta-section — remove\n" + body +
            "\n## 2026-11-18 — alpha — add\n- See PR #999.\n", encoding="utf-8")
        return {r["id"]: r["reverse_url"] for r in explorer_data.removed_sections(root)}

    def test_a_linked_pull_request_beats_an_issue_link(self):
        urls = self._skill_urls(
            "- Motivation: [issue #23](https://github.com/Adam-S-Daniel/adam-agentskills/issues/23)"
            " step 2\n- Change: skill deleted ([#34](https://github.com/Adam-S-Daniel/"
            "adam-agentskills/pull/34))\n")
        self.assertEqual(urls["gamma-skill"],
                         "https://github.com/Adam-S-Daniel/adam-agentskills/pull/34")

    def test_a_bare_pr_number_names_the_guidance_pull_request(self):
        urls = self._section_urls(
            "- Change: removed the section and its eval-coverage.yml row (PR #213).\n")
        self.assertEqual(urls["delta-section"],
                         "https://github.com/Adam-S-Daniel/_agent-guidance/pull/213")
        self.assertEqual(self._skill_urls("- Change: gone (PR #7).\n")["gamma-skill"],
                         "https://github.com/Adam-S-Daniel/adam-agentskills/pull/7")

    def test_the_first_pull_request_in_body_order_wins(self):
        urls = self._skill_urls(
            "- Change: see PR #5, then https://github.com/Adam-S-Daniel/adam-agentskills/pull/6\n")
        self.assertEqual(urls["gamma-skill"],
                         "https://github.com/Adam-S-Daniel/adam-agentskills/pull/5")

    def test_an_issue_link_only_falls_back_to_the_search(self):
        urls = self._skill_urls(
            "- Motivation: https://github.com/Adam-S-Daniel/adam-agentskills/issues/23\n")
        self.assertIn("pulls?q=is%3Apr+head%3Aretire-skill%2Fgamma-skill", urls["gamma-skill"])
        urls = self._section_urls(
            "- Motivation: [#9](https://github.com/Adam-S-Daniel/_agent-guidance/issues/9)\n")
        self.assertIn("pulls?q=is%3Apr+head%3Aretire-guidance%2Fdelta-section",
                      urls["delta-section"])

    def test_no_link_falls_back_and_the_next_entry_is_not_read(self):
        # The following entry names PR #999; it must not leak into this one.
        self.assertIn("head%3Aretire-skill%2Fgamma-skill",
                      self._skill_urls("- Motivation: m\n")["gamma-skill"])
        self.assertIn("head%3Aretire-guidance%2Fdelta-section",
                      self._section_urls("- Motivation: m\n")["delta-section"])

    def test_no_checkout_or_file_lists_nothing(self):
        self.assertEqual(explorer_data.removed_sections(None), [])
        self.assertEqual(explorer_data.removed_sections(Path("/nonexistent-dir")), [])


class GuidanceTests(unittest.TestCase):

    def setUp(self):
        self.t = Tree(self)
        stamp = "20261030T120000Z"
        for arm, mode, passed in (("with_guidance_full", "full", 4),
                                  ("without_guidance_full_minus_section",
                                   "full-minus-section", 2),
                                  ("with_guidance_section", "section", 3),
                                  ("without_guidance", "none", 1)):
            self.t.guidance_arm("sec-one", stamp, arm, mode, passed)
        self.doc = self.t.build(manifest=MANIFEST)

    def test_modes_follow_the_arm_names(self):
        one, two = self.doc["guidance"]["sections"]
        self.assertEqual((one["id"], one["heading"], one["bytes"], one["status"]),
                         ("sec-one", "Section one", 100, "covered"))
        self.assertEqual((two["status"], two["skip_reason"], two["runs"]),
                         ("skipped", "invented reason", []))
        run = one["runs"][0]
        self.assertEqual(sorted(run["modes"]), ["full", "full_minus_section", "none", "section"])
        passed = {mode: m["checks_passed"] for mode, m in run["modes"].items()}
        self.assertEqual(passed, {"full": 4, "full_minus_section": 2, "section": 3, "none": 1})
        self.assertEqual(run["modes"]["full"], {"trials": 1, "checks_passed": 4,
                                                "checks_total": 4, "judge_mean": 8.0,
                                                "cost_usd": 0.5})
        self.assertEqual((run["fixture"], run["model"], run["cli_version"], run["at"]),
                         ("fx", "model-a", "2.1.301", "2026-10-30T12:00:00Z"))
        self.assertIn("/guidance/sec-one/20261030T120000Z/report.md", run["report_url"])
        for key in ("verdict", "verdict_reason", "alone_verdict"):
            self.assertIn(key, one)

    def test_a_missing_mode_is_absent(self):
        t = Tree(self)
        t.guidance_arm("sec-one", "20261030T120000Z", "with_guidance_full", "full", 4)
        run = t.build(manifest=MANIFEST)["guidance"]["sections"][0]["runs"][0]
        self.assertEqual(list(run["modes"]), ["full"])


def cell(n_with, n_without):
    return {"runs": {"with": [{"run": i} for i in range(n_with)],
                     "without": [{"run": i} for i in range(n_without)]}}


class CurrentTextRunsTests(unittest.TestCase):
    """`current_text_runs` counts with-arm runs only: they are the runs on the
    subject's current text (without-arm runs pool across text changes)."""

    def build_with(self, gates_doc):
        t = Tree(self)
        gates_doc = {"policy": {"benefit_confidence": 0.85, "retire_confidence": 0.95,
                                "min_cli_versions": 2, "objective_margin": 0.05},
                     **gates_doc}
        with mock.patch.object(explorer_data.compute_gates, "compute", return_value=gates_doc):
            return t.build(manifest=MANIFEST)

    def test_a_skill_counts_with_arm_runs_only(self):
        doc = self.build_with({"skills": {"alpha": {"verdict": "retain", "cells": [
            cell(1, 2), cell(1, 1)]}}, "guidance": {}})
        alpha = next(s for s in doc["skills"] if s["name"] == "alpha")
        self.assertEqual(alpha["current_text_runs"], 2)

    def test_a_skill_with_no_verdict_or_no_with_key_reports_zero(self):
        doc = self.build_with({"skills": {"beta": {"verdict": "insufficient", "cells": [
            {"runs": {"without": [{"run": 0}]}}, {"runs": {}}]}}, "guidance": {}})
        counts = {s["name"]: s["current_text_runs"] for s in doc["skills"]}
        self.assertEqual(counts, {"alpha": 0, "beta": 0, "gamma": 0,
                                  "skipped-skill": 0})

    def test_a_guidance_section_counts_in_situ_and_alone_cells(self):
        doc = self.build_with({"skills": {}, "guidance": {"sec-one": {
            "verdict": "retain", "cells": [cell(2, 5)],
            "alone": {"verdict": "retain", "cells": [cell(1, 4), cell(1, 0)]}}}})
        counts = {s["id"]: s["current_text_runs"] for s in doc["guidance"]["sections"]}
        self.assertEqual(counts, {"sec-one": 4, "sec-two": 0})


class AlertTests(unittest.TestCase):

    GATES = {"skills": {"alpha": {"verdict": "retire", "reason": "no benefit in any cell"},
                        "hidden": {"verdict": "retire", "reason": "x"},
                        "beta": {"verdict": "retain", "reason": "y"}},
             "guidance": {"sec-one": {"verdict": "retire", "reason": "flat"}}}
    ROWS = {"rows": [
        {"subject": "skill", "id": "alpha", "fixture": "fx", "model": "model-a",
         "verdict": "regressed", "reason": "the pass rate fell"},
        {"subject": "guidance", "id": "sec-one", "fixture": "fx", "model": "model-b",
         "verdict": "lost-delta", "reason": "the gap closed"},
        {"subject": "skill", "id": "beta", "verdict": "improved", "reason": "up"},
        {"subject": "skill", "id": "stable-one", "verdict": "stable"},
        {"subject": "skill", "id": "hidden", "verdict": "regressed", "reason": "private"}]}

    def alerts(self, issues=None):
        return explorer_data.build_alerts(self.GATES, self.ROWS, issues or {},
                                          {"alpha", "beta"}, {"sec-one"})

    def test_retire_verdicts_and_regression_rows_become_alerts(self):
        alerts = self.alerts()
        by = {(a["kind"], a["subject"], a["name"]): a for a in alerts}
        self.assertEqual(set(by), {("retire", "skill", "alpha"), ("retire", "guidance", "sec-one"),
                                   ("regression", "skill", "alpha"),
                                   ("regression", "guidance", "sec-one")})
        self.assertIn("no benefit in any cell", by[("retire", "skill", "alpha")]["text"])
        regression = by[("regression", "guidance", "sec-one")]
        self.assertEqual(regression["model"], "model-b")
        self.assertIn("lost-delta", regression["text"])
        self.assertTrue(all(a["url"] is None for a in alerts))

    def test_alerts_about_unlisted_subjects_are_dropped(self):
        self.assertFalse([a for a in self.alerts() if a["name"] == "hidden"])

    def test_issue_urls_fill_the_regression_alerts_only(self):
        url = "https://github.com/Adam-S-Daniel/skills-evals/issues/7"
        guidance_url = "https://github.com/Adam-S-Daniel/skills-evals/issues/8"
        alerts = self.alerts({"skills-evals:regression:alpha": url,
                              "skills-evals:regression:guidance:sec-one": guidance_url,
                              "skills-evals:regression:beta": "https://example.com/not-github"})
        urls = {(a["kind"], a["subject"]): a["url"] for a in alerts}
        self.assertEqual(urls[("regression", "skill")], url)
        self.assertEqual(urls[("regression", "guidance")], guidance_url)
        self.assertIsNone(urls[("retire", "skill")])

    def test_markers_are_read_from_issue_bodies(self):
        listing = [
            {"url": "https://github.com/o/r/issues/1",
             "body": "text\n<!-- skills-evals:regression:alpha -->"},
            {"url": "https://github.com/o/r/issues/2",
             "body": "<!-- skills-evals:regression:guidance:sec-one -->"},
            {"url": "https://github.com/o/r/issues/3", "body": None}, "junk"]
        self.assertEqual(explorer_data.issue_markers(listing), {
            "skills-evals:regression:alpha": "https://github.com/o/r/issues/1",
            "skills-evals:regression:guidance:sec-one": "https://github.com/o/r/issues/2"})

    def test_regression_rows_in_the_tree_reach_the_document(self):
        t = Tree(self)
        t.pair("alpha", "20261030T100000Z", [Tree.trial(5, 5, 8.0, 0.1)],
               [Tree.trial(1, 5, 4.0, 0.1)])
        t.write_json("regressions/latest.json", self.ROWS)
        url = "https://github.com/Adam-S-Daniel/skills-evals/issues/7"
        doc = t.build(issues={"skills-evals:regression:alpha": url})
        found = [a for a in doc["alerts"] if a["kind"] == "regression"]
        self.assertEqual([(a["name"], a["url"]) for a in found], [("alpha", url)])


def qcell(skill, fixture, cls, newest=None, verdict=None, section=None, runs=1):
    return {"skill": "" if section else skill, "section": section, "fixture": fixture,
            "model": "model-a", "class": cls, "verdict": verdict, "with_runs": runs,
            "without_runs": runs, "newest": newest, "usd_per_fire": None,
            "usd_per_arm_trial": None, "empty_fires": 0}


class NotSchedulableTests(unittest.TestCase):
    """A held scheduled cell is no queue entry; a public one is an alert, a
    private one is never named."""
    NOW = explorer_data.plan_week._stamp_time("20261101T000000Z")

    def held(self, skill, reason):
        return {**qcell(skill, f"evals/{skill}/x", "missing"), "schedulable": False,
                "hold_reason": reason}

    def test_the_queue_skips_held_cells(self):
        cells = [self.held("iso", "no context"), qcell("ok", "evals/ok/x", "missing")]
        q = explorer_data.test_queue(cells, {"model-a": 1.0}, self.NOW)
        self.assertEqual(set(q), {("skill", "ok")})

    def test_a_public_held_cell_is_an_alert_and_a_private_one_is_not(self):
        gates_doc = {"skills": {}}
        cells = [self.held("iso", "no context"), self.held("pin", "null pin"),
                 self.held("hidden", "private, paused"), qcell("ok", "evals/ok/x", "missing")]
        alerts = explorer_data.build_alerts(gates_doc, None, {}, {"iso", "pin", "ok"}, set(),
                                            cells)
        got = {(a["kind"], a["name"], a["model"], a["fixture"], a["reason"]) for a in alerts}
        self.assertEqual(got, {("not-schedulable", "iso", "model-a", "evals/iso/x", "no context"),
                               ("not-schedulable", "pin", "model-a", "evals/pin/x", "null pin")})
        # Even when the private skill is listed, its cell raises nothing.
        alerts = explorer_data.build_alerts(gates_doc, None, {}, {"hidden"}, set(), cells)
        self.assertEqual(alerts, [])


class QueueConfidenceUsageTests(unittest.TestCase):
    """The page's order (next test first), its confidence line and its
    real-use count (Adam, 2026-11-01)."""

    NOW = explorer_data.plan_week._stamp_time("20261101T000000Z")

    def test_queue_follows_the_planner_bands_then_the_recheck_date(self):
        cells = [qcell("near", "evals/near", "insufficient", newest="20261030T000000Z", runs=2),
                 qcell("miss", "evals/miss", "missing"),
                 qcell("", "evals/guidance/sec/fx", "insufficient", runs=1,
                       newest="20261030T000000Z", section="sec"),
                 qcell("kept", "evals/kept", "benefit", newest="20261025T000000Z",
                       verdict="keep"),
                 qcell("open", "evals/open", "insufficient", newest="20261025T000000Z",
                       verdict="keep")]
        q = explorer_data.test_queue(cells, {"model-a": 1.0}, self.NOW)
        self.assertEqual(q[("skill", "miss")]["position"], 1)
        self.assertEqual(q[("skill", "miss")]["band"], "missing")
        # A guidance cell is never near: its section is focused, after near.
        self.assertEqual(q[("skill", "near")]["position"], 2)
        self.assertEqual(q[("guidance", "sec")], {"position": 3, "band": "focus",
                                                  "due": None, "scheduled": True})
        # Kept: no fire now, a re-check eight weeks after the newest run.
        self.assertEqual(q[("skill", "kept")], {"position": None, "band": None,
                                                "due": "2026-12-20T00:00:00Z",
                                                "scheduled": True})
        self.assertEqual(q[("skill", "open")]["due"], "2026-12-20T00:00:00Z")

    def test_renumber_counts_only_listed_subjects(self):
        rows = [{"next_test": {"position": 5}}, {"next_test": {"position": None}},
                {"next_test": {"position": 2}}]
        explorer_data.renumber(rows)
        self.assertEqual([r["next_test"]["position"] for r in rows], [2, None, 1])

    def test_confidence_is_the_family_keep_level_and_the_weakest_no_help(self):
        # 2026-11-03: `helps` is the subject's keep level, 1 - m x the
        # smallest objective keep p (the judge does not vote, so its levels
        # are not read); `no_help` the weakest no-help level over the cells
        # that vote on removal.
        verdict = {"keep_family": 2, "cells": [
            {"objective": {"helps_confidence": 0.4, "no_help_confidence": 0.7},
             "keep_tests": [{"route": "objective", "p": 0.6}],
             "judge": {"helps_confidence": 0.9, "no_help_confidence": 0.1}},
            {"objective": {"helps_confidence": 0.95, "no_help_confidence": 0.3},
             "keep_tests": [{"route": "objective", "p": 0.05}]}]}
        got = explorer_data.subject_confidence(verdict)
        self.assertEqual((got["helps"], got["no_help"]), (0.9, 0.3))
        # A family of one, or none recorded, is m = 1.
        self.assertEqual(explorer_data.subject_confidence(
            {**verdict, "keep_family": None})["helps"], 0.95)
        # A ceiling or broken cell does not vote, so it does not lower no_help.
        verdict["cells"].append({"class": "ceiling", "objective": {"no_help_confidence": 0.0}})
        verdict["cells"].append({"class": "cannot-discriminate"})
        self.assertEqual(explorer_data.subject_confidence(verdict)["no_help"], 0.3)
        # A voting cell with no figure blocks a no-help claim; no figure at all is None.
        verdict["cells"].append({"class": "missing"})
        self.assertEqual(explorer_data.subject_confidence(verdict)["no_help"], 0.0)
        empty = {k: None for k in ("helps", "no_help", "keep_pairs", "no_help_pairs",
                                   "max_pairs", "keep_family")}
        self.assertEqual(explorer_data.subject_confidence({"cells": [{"class": "missing"}]}), empty)
        self.assertEqual(explorer_data.subject_confidence({}), empty)

    def test_confidence_carries_the_pair_counts_behind_each_level(self):
        verdict = {"keep_family": 2, "cells": [
            {"objective": {"no_help_confidence": 0.7, "pairs": 11},
             "keep_tests": [{"route": "objective", "p": 0.6}]},
            {"objective": {"no_help_confidence": 0.3, "pairs": 6},
             "keep_tests": [{"route": "objective", "p": 0.05}]}]}
        got = explorer_data.subject_confidence(verdict)
        # keep comes from the second cell (smallest p), remove from the second
        # (lowest level), and the busiest cell is the first.
        self.assertEqual((got["keep_pairs"], got["no_help_pairs"], got["max_pairs"],
                          got["keep_family"]), (6, 6, 11, 2))
        verdict["cells"][1]["objective"]["pairs"] = "6"
        got = explorer_data.subject_confidence(verdict)
        self.assertEqual((got["keep_pairs"], got["no_help_pairs"], got["max_pairs"]),
                         (None, None, 11))

    def test_usage_counts_listed_skills_and_names_its_window(self):
        t = Tree(self)
        t.pair("alpha", "20261030T100000Z", [Tree.trial(5, 5, 8.0, 0.25)],
               [Tree.trial(1, 5, 4.0, 0.25)])
        rows = [{"week": w, "kind": "skill", "name": n, "repo": None, "surface": "local",
                 "invocations": k, "sessions": 1, "blocked": None, "overridden": None,
                 "outcome": None}
                for w, n, k in (("2026-10-19", "alpha", 2), ("2026-10-26", "alpha", 3),
                                ("2026-10-26", "other", 7))]
        t.write_json("usage/weekly-local.json", {
            "generated_at": "2026-10-31T16:00:00Z", "schema": 1, "rows": rows,
            "sources": [{"surface": "local", "scope": "transcripts",
                         "from": "2026-10-19T00:00:00Z", "to": "2026-10-31T16:00:00Z",
                         "sessions_scanned": 40}]})
        doc = t.build()
        by = {s["name"]: s for s in doc["skills"]}
        self.assertEqual(by["alpha"]["usage"], {"invocations": 5})
        self.assertEqual(by["beta"]["usage"], {"invocations": 0})
        self.assertEqual(doc["usage"], {"from": "2026-10-19T00:00:00Z",
                                        "to": "2026-10-31T16:00:00Z",
                                        "sessions_scanned": 40, "surface": "local"})
        explorer_data.finish(doc)


class FixtureQueueFieldTests(unittest.TestCase):
    """Adam, 2026-11-03: the fixture queue's report (scripts/fixture_queue.py)
    is in the document as `fixture_queue`, carried as is, or None."""

    REPORT = {"schema": 1, "generated_at": "2026-11-01T00:00:00Z",
              "requests": [{"issue": 3, "kind": "needs-fixtures", "subject": "alpha",
                            "state": "open", "opened_at": "2026-10-20T00:00:00Z",
                            "closed_at": None, "prs": []}],
              "fixtures": [], "findings": [],
              "totals": {"requests_open": 1, "requests_closed": 0, "prs_merged": 0,
                         "fixtures_real_work": 0, "fixtures_invented": 0,
                         "fixture_runs": 0, "cost_points": 0, "cost_usd": 0}}

    def test_loaded_or_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.json"
            self.assertIsNone(explorer_data.load_fixture_queue(None))
            self.assertIsNone(explorer_data.load_fixture_queue(path))
            for bad in ("{", "[]", json.dumps({**self.REPORT, "schema": 2}),
                        json.dumps({**self.REPORT, "totals": []}),
                        json.dumps({k: v for k, v in self.REPORT.items() if k != "fixtures"})):
                path.write_text(bad, encoding="utf-8")
                with self.subTest(bad=bad[:30]):
                    self.assertIsNone(explorer_data.load_fixture_queue(path))
            path.write_text(json.dumps(self.REPORT), encoding="utf-8")
            self.assertEqual(explorer_data.load_fixture_queue(path), self.REPORT)

    def test_carried_into_the_document_and_through_the_gate(self):
        t = Tree(self)
        doc = explorer_data.build(t.tree, t.roster, t.policy, t.evals, AS_OF, SHA_A, SHA_B,
                                  manifest=[], fixture_queue=self.REPORT)
        self.assertEqual(doc["fixture_queue"], self.REPORT)
        explorer_data.finish(doc)
        # The gate still applies inside it.
        leak = {**self.REPORT, "requests": [{**self.REPORT["requests"][0],
                                             "subject": "someone@example.com"}]}
        with self.assertRaises(explorer_data.Refused):
            explorer_data.finish({**doc, "fixture_queue": leak})

    def test_the_cli_passes_the_file(self):
        t = Tree(self)
        queue, out = t.root / "queue.json", t.root / "out.json"
        queue.write_text(json.dumps(self.REPORT), encoding="utf-8")
        code = explorer_data.main([
            "--results-tree", str(t.tree), "--roster", str(t.roster),
            "--policy", str(t.policy), "--evals-dir", str(t.evals), "--as-of", AS_OF,
            "--repository-commit", SHA_A, "--results-commit", SHA_B,
            "--fixture-queue", str(queue), "--out", str(out)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.read_text())["fixture_queue"], self.REPORT)


class WorkflowTests(unittest.TestCase):

    def setUp(self):
        self.doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.on = self.doc.get("on", self.doc.get(True))

    def test_triggers(self):
        self.assertEqual(sorted(self.on), ["schedule", "workflow_dispatch", "workflow_run"])
        run = self.on["workflow_run"]
        self.assertEqual(run["types"], ["completed"])
        ingest = yaml.safe_load((ROOT / ".github/workflows/routine-eval-ingest.yml")
                                .read_text(encoding="utf-8"))
        self.assertEqual(run["workflows"], [ingest["name"]])
        self.assertEqual(len(self.on["schedule"]), 1)

    def test_permissions_are_minimal(self):
        self.assertEqual(self.doc["permissions"], {})
        build, publish = self.doc["jobs"]["build"], self.doc["jobs"]["publish"]
        # #555: `actions: read` lists the fire runs for `fires_without_results`.
        # The fixture queue (2026-11-03): `pull-requests: read` lists the pull
        # requests, and `queue-alerts` alone writes issues.
        self.assertEqual(build["permissions"], {"actions": "read", "contents": "read",
                                                "issues": "read", "pull-requests": "read"})
        self.assertEqual(publish["permissions"], {"contents": "write"})
        self.assertEqual(sorted(self.doc["jobs"]), ["build", "publish", "queue-alerts"])
        self.assertEqual(self.doc["jobs"]["queue-alerts"]["permissions"],
                         {"contents": "read", "issues": "write"})
        self.assertEqual(publish["needs"], "build")

    def test_nothing_from_the_event_is_interpolated_into_a_run_block(self):
        for name, job in self.doc["jobs"].items():
            for step in job["steps"]:
                for text in (step.get("run") or "",):
                    with self.subTest(job=name, step=step.get("name")):
                        self.assertNotRegex(text, r"\$\{\{\s*(github\.event|inputs)\b")

    def test_it_publishes_only_to_the_results_branch(self):
        steps = self.doc["jobs"]["publish"]["steps"]
        push = next(s for s in steps if s["name"].startswith("Commit to"))["run"]
        self.assertIn("HEAD:refs/heads/persistent/eval-results", push)
        self.assertNotRegex(push, r"origin\s+(HEAD:)?(refs/heads/)?main\b")
        self.assertIn("merge-base --is-ancestor", push)

    def test_every_action_is_locked_and_listed_for_this_workflow(self):
        sys.path.insert(0, str(ROOT / "test"))
        import lockfile_pins
        locked = yaml.safe_load(lockfile_pins.LOCKFILE.read_text(encoding="utf-8"))
        listed = set(locked["workflows"][".github/workflows/explorer-data.yml"])
        used = {s["uses"] for job in self.doc["jobs"].values() for s in job["steps"]
                if "uses" in s}
        self.assertEqual(used, listed)
        for uses in used:
            self.assertIsNone(lockfile_pins.lock_problem(uses, "explorer-data.yml"))

    def test_ci_runs_the_suite_when_the_workflow_changes(self):
        ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
        path = ".github/workflows/explorer-data.yml"
        self.assertIn(path, ci["on"]["push"]["paths"])
        salient = next(s for s in ci["jobs"]["suite"]["steps"] if s.get("id") == "salient")
        self.assertIn(path, salient["env"]["SALIENT_PATHS"].splitlines())


if __name__ == "__main__":
    unittest.main()
