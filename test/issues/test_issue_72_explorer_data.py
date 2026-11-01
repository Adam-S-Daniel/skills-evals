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
        self.assertEqual(sorted(d), ["alerts", "coverage", "generated_at", "guidance",
                                     "newest_run", "policy", "roster", "schema_version",
                                     "skills", "source"])
        self.assertEqual(d["schema_version"], 1)
        self.assertEqual(d["generated_at"], AS_OF)
        self.assertEqual(d["newest_run"], "2026-10-30T10:00:00Z")
        self.assertEqual(d["source"], {"repository": "Adam-S-Daniel/skills-evals",
                                       "repository_commit": SHA_A, "results_commit": SHA_B})
        self.assertEqual(d["roster"], {"arms": [{"model": "model-a", "reason": "invented reason a"}],
                                       "judge": {"model": "model-j",
                                                 "reason": "invented judge reason"}})
        self.assertEqual(d["policy"], {"benefit_confidence": 0.85, "retire_confidence": 0.95,
                                       "min_cli_versions": 2, "objective_margin": 0.05})
        self.assertIsInstance(d["skills"], list)
        self.assertIsInstance(d["guidance"]["sections"], list)
        self.assertIsInstance(d["alerts"], list)
        self.assertEqual(d["coverage"], {"as_of": "2026-10-31T14:00:00Z", "covered": 3,
                                         "skipped": 1, "gap": 0, "total": 4})
        for s in d["skills"]:
            self.assertEqual(sorted(s), sorted([
                "bundle", "description", "name", "registry", "runs", "skip_reason",
                "status", "verdict", "verdict_reason", "current_text_runs"]))

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
        self.assertEqual(build["permissions"], {"contents": "read", "issues": "read"})
        self.assertEqual(publish["permissions"], {"contents": "write"})
        self.assertEqual(sorted(self.doc["jobs"]), ["build", "publish"])
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
