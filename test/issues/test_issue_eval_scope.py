#!/usr/bin/env python3
"""Adam, 2026-11-03: the eval scope pass (scripts/eval_scope.py).

What is pinned here:

  * ceiling, floor, zero-use and resume, each on synthetic explorer and usage
    documents and a throwaway git repository whose commit times are fixed
    (no network, no wall clock: `--now` is always passed);
  * the exclusions: `stakes: high` subjects, `draft: true` fixtures and every
    unscheduled.yml row the pass did not write;
  * `apply` pauses and resumes the three files and leaves the rest of them
    byte for byte, refuses a stale plan, and a round trip restores the
    schedule;
  * the committed evals/scope-auto.yml has its shape, and no row's path is
    still scheduled;
  * .github/workflows/eval-scope.yml, parsed with PyYAML, has its triggers
    (workflow_run, schedule, dispatch; no push or pull_request),
    `permissions: {}` at the top, no `${{` in any `run:`, no concurrency
    group, and its pins locked.

Run with: python3 -m pytest test/issues/test_issue_eval_scope.py -q
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test"))

import eval_scope  # noqa: E402
import skill_usage  # noqa: E402
from lockfile_pins import lock_problem  # noqa: E402

WORKFLOW = ROOT / ".github/workflows/eval-scope.yml"
NOW = "2026-11-03T14:00:00Z"
NOW_DT = datetime(2026, 11, 3, 14, 0, tzinfo=timezone.utc)
COMMITTED = "2026-10-01T12:00:00Z"
AFTER = "2026-10-20T12:00:00Z"
BEFORE = "2026-09-20T12:00:00Z"


# --- builders ------------------------------------------------------------


def git(root: Path, *args: str, when: str = COMMITTED) -> None:
    env = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    subprocess.run(["git", "-C", str(root), *args], check=True, env=env,
                   capture_output=True)


def write(root: Path, rel: str, text: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


SCHEDULED_HEAD = "# schedule header comment\nfixtures:\n"
UNSCHEDULED_HEAD = "# unscheduled header comment\nfixtures:\n"
HUMAN_ROW = ('  - path: evals/human-skill\n'
             '    reason: "Scope decision 2026-11-03: a person decided."\n')


def make_repo(tmp: str, scheduled: list[str], *, draft: tuple = (), high_skills: tuple = (),
              high_sections: tuple = (), unscheduled: str = HUMAN_ROW) -> Path:
    root = Path(tmp)
    git(root, "init", "-q")
    for path in scheduled:
        write(root, f"{path}/fixture.yaml",
              "draft: true\n" if path in draft else "draft: false\n")
        write(root, f"{path}/seed/a.txt", "seed\n")
    write(root, "evals/human-skill/fixture.yaml", "draft: false\n")
    write(root, "evals/scheduled.yml", SCHEDULED_HEAD + "".join(
        f'  - path: {p}\n    readiness: "ready {p}"\n' for p in scheduled))
    write(root, "evals/unscheduled.yml", UNSCHEDULED_HEAD + unscheduled)
    write(root, "evals/scope-auto.yml", eval_scope.render_scope_auto([]))
    stakes = ""
    if high_skills or high_sections:
        stakes = "skills:\n" + "".join(
            f"  - skill: {s}\n    stakes: high\n    reason: irreversible\n" for s in high_skills)
        if high_sections:
            stakes += "sections:\n" + "".join(
                f"  - section: {s}\n    stakes: high\n    reason: irreversible\n"
                for s in high_sections)
        for s in high_skills:
            write(root, f"evals/{s}/fixture.yaml", "draft: false\n")
        for s in high_sections:
            write(root, f"evals/guidance/{s}/fixture.yaml", "draft: false\n")
    write(root, "evals/stakes.yml", stakes or "skills: []\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return root


def arm(passed: int, total: int = 10, judge: float | None = None) -> dict:
    out = {"checks_passed": passed, "checks_total": total, "cost_usd": 0.1, "trials": 1}
    if judge is not None:
        out["judge_mean"] = judge
    return out


def skill_run(fixture: str | None, with_arm: dict, without_arm: dict, at: str = AFTER) -> dict:
    return {"at": at, "fixture": fixture, "with": with_arm, "without": without_arm}


def guidance_run(fixture: str, full: dict, minus: dict, at: str = AFTER) -> dict:
    return {"at": at, "fixture": fixture,
            "modes": {"full": full, "full_minus_section": minus}}


def explorer(skills: dict | None = None, sections: dict | None = None) -> dict:
    return {"skills": [{"name": n, "runs": r} for n, r in (skills or {}).items()],
            "guidance": {"sections": [{"id": n, "runs": r} for n, r in (sections or {}).items()]}}


def usage_doc(used: dict | None = None, *, cloud: bool = True, local: int = 300,
              cloud_sessions: int = 300) -> dict:
    """A fresh census counted from long before the 8-week window, with
    `local` full-listing local sessions and (when `cloud`) `cloud_sessions`
    cloud sessions in the window: 600 by default, over the 500 a zero needs."""
    floor = NOW_DT - timedelta(weeks=20)
    rows = [skill_usage.row("2026-W44", "skill", name, count, 1)
            for name, count in (used or {}).items()]
    rows.append(skill_usage.listing_row("2026-W44", "full", local))
    rows.append(skill_usage.listing_row("2026-W44", "truncated", 700))
    if cloud:
        rows.append(skill_usage.listing_row("2026-W44", "full", cloud_sessions,
                                            skill_usage.SURFACE_CLOUD))
    doc = skill_usage.document(
        rows, NOW_DT, floor, sessions_scanned=1,
        cloud_guidance={"from": floor, "records_scanned": 1, "listing_recorded": True}
        if cloud else None,
        skill_keys=sorted({"alpha", "beta", "zzz", *(used or {})}))
    if cloud:
        skill_usage.add_rows(doc, [], skill_usage.digest_source(
            floor, NOW_DT, 0, surface=skill_usage.SURFACE_CLOUD))
    return doc


def plan_for(root: Path, exp: dict, usage=None, plugins: dict | None = None) -> dict:
    return eval_scope.build_plan(root, exp, usage, plugins or {}, NOW_DT)


def four(fixture, with_arm, without_arm, count=4):
    return [skill_run(fixture, with_arm, without_arm) for _ in range(count)]


# --- rules ---------------------------------------------------------------


class CeilingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_repo(self._tmp.name, ["evals/alpha/one", "evals/alpha/two"])

    def paused(self, runs, fixture="one"):
        plan = plan_for(self.root, explorer({"alpha": runs}))
        return [(p["path"], p["rule"]) for p in plan["pause"]]

    def test_four_runs_with_the_without_arm_at_the_ceiling_pause_the_fixture(self):
        self.assertEqual(self.paused(four("one", arm(10), arm(9))),
                         [("evals/alpha/one", "ceiling")])

    def test_the_threshold_is_the_share_of_checks_passed(self):
        # 0.80 stays; 0.85 pauses.
        self.assertEqual(self.paused(four("one", arm(10), arm(8))), [])
        self.assertEqual(self.paused(four("one", arm(20), arm(17, 20))),
                         [("evals/alpha/one", "ceiling")])

    def test_three_runs_are_not_enough(self):
        self.assertEqual(self.paused(four("one", arm(10), arm(10), count=3)), [])

    def test_runs_before_the_fixtures_last_commit_do_not_count(self):
        runs = four("one", arm(10), arm(10), count=3) + [
            skill_run("one", arm(10), arm(10), at=BEFORE)]
        self.assertEqual(self.paused(runs), [])

    def test_a_low_judge_score_keeps_it(self):
        runs = four("one", arm(10), arm(10, judge=8.0))
        self.assertEqual(self.paused(runs), [])
        runs = four("one", arm(10), arm(10, judge=8.5))
        self.assertEqual(self.paused(runs), [("evals/alpha/one", "ceiling")])

    def test_only_the_named_fixtures_runs_count(self):
        self.assertEqual(self.paused(four("two", arm(10), arm(10))),
                         [("evals/alpha/two", "ceiling")])

    def test_a_skill_with_one_fixture_has_null_fixture_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, ["evals/solo"])
            plan = plan_for(root, explorer({"solo": four(None, arm(10), arm(10))}))
            self.assertEqual([p["path"] for p in plan["pause"]], ["evals/solo"])

    def test_the_plan_records_what_resume_needs(self):
        item = plan_for(self.root, explorer({"alpha": four("one", arm(10), arm(10))}))["pause"][0]
        self.assertEqual(item["fixture_digest"],
                         eval_scope.fixture_digest(self.root / "evals/alpha/one"))
        self.assertEqual(item["readiness"], "ready evals/alpha/one")
        self.assertEqual(item["since"], "2026-11-03")
        self.assertEqual(item["kind"], "skill")


class FloorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_repo(self._tmp.name, ["evals/alpha/one"])

    def paused(self, with_arm, without_arm, count=4):
        plan = plan_for(self.root, explorer({"alpha": four("one", with_arm, without_arm, count)}))
        return [(p["path"], p["rule"]) for p in plan["pause"]]

    def test_both_arms_at_the_floor_pause(self):
        self.assertEqual(self.paused(arm(1), arm(0)), [("evals/alpha/one", "floor")])

    def test_a_with_arm_above_the_floor_keeps_it(self):
        self.assertEqual(self.paused(arm(2), arm(0)), [])

    def test_a_without_arm_above_the_floor_keeps_it(self):
        self.assertEqual(self.paused(arm(0), arm(2)), [])

    def test_runs_missing_an_arm_do_not_count(self):
        runs = [{"at": AFTER, "fixture": "one", "with": arm(0), "without": None}] * 4
        plan = plan_for(self.root, explorer({"alpha": runs}))
        self.assertEqual(plan["pause"], [])


class GuidanceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_repo(self._tmp.name, ["evals/guidance/sec/fx"])

    def plan(self, full, minus):
        runs = [guidance_run("fx", full, minus) for _ in range(4)]
        return plan_for(self.root, explorer(sections={"sec": runs}))

    def test_the_full_minus_section_arm_is_the_ceiling_arm(self):
        item = self.plan(arm(0), arm(10, judge=9.9))["pause"][0]
        self.assertEqual((item["path"], item["rule"], item["kind"]),
                         ("evals/guidance/sec/fx", "ceiling", "guidance"))

    def test_the_full_arm_alone_at_the_ceiling_does_not_pause(self):
        self.assertEqual(self.plan(arm(10), arm(5))["pause"], [])

    def test_floor_reads_full_and_full_minus_section(self):
        self.assertEqual(self.plan(arm(0), arm(1))["pause"][0]["rule"], "floor")

    def test_zero_use_never_applies_to_guidance(self):
        plan = plan_for(self.root, explorer(), usage_doc())
        self.assertEqual(plan["pause"], [])


ROSTER = {"arms": [{"model": "opus"}, {"model": "sonnet"}]}


def on(model: str, runs: list[dict]) -> list[dict]:
    return [{**r, "model": model} for r in runs]


class PerModelAndKeepTests(unittest.TestCase):
    """The ceiling and floor read each roster model's cell on its own, and a
    kept (or nearly kept) subject is never paused (adversarial round 3 on
    #649: C1 and M1)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_repo(self._tmp.name, ["evals/alpha/one", "evals/guidance/sec/fx"])

    def exp(self, opus, sonnet, **entry):
        doc = explorer({"alpha": on("opus", opus) + on("sonnet", sonnet)})
        doc["roster"] = ROSTER
        doc["skills"][0].update(entry)
        return doc

    def paused(self, exp):
        return [p["path"] for p in plan_for(self.root, exp)["pause"]]

    def test_a_pooled_ceiling_with_one_model_below_it_does_not_pause(self):
        # Pooled without share is 0.875, but sonnet's own cell is 0.75.
        self.assertEqual(self.paused(self.exp(four("one", arm(10), arm(10)),
                                              four("one", arm(10), arm(7)) + four(
                                                  "one", arm(10), arm(8)))), [])

    def test_every_model_at_the_ceiling_pauses(self):
        self.assertEqual(self.paused(self.exp(four("one", arm(10), arm(10)),
                                              four("one", arm(10), arm(9)))),
                         ["evals/alpha/one"])

    def test_a_roster_model_without_enough_runs_does_not_pause(self):
        self.assertEqual(self.paused(self.exp(four("one", arm(10), arm(10)),
                                              four("one", arm(10), arm(10), count=3))), [])

    def test_a_kept_subject_is_never_paused(self):
        at = (four("one", arm(10), arm(10)), four("one", arm(10), arm(10)))
        self.assertEqual(self.paused(self.exp(*at, verdict="keep")), [])
        self.assertEqual(self.paused(self.exp(*at, confidence={"helps": 0.6})), [])
        self.assertEqual(self.paused(self.exp(*at, confidence={"helps": 0.4})),
                         ["evals/alpha/one"])

    def paused_then(self, exp):
        eval_scope.apply_plan(self.root, plan_for(self.root, self.exp(
            four("one", arm(10), arm(10)), four("one", arm(10), arm(10)))))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "pause", when=COMMITTED)
        return [(r["path"], r["rule"]) for r in plan_for(self.root, exp)["resume"]]

    def test_a_pause_resumes_when_the_subject_is_kept(self):
        at = (four("one", arm(10), arm(10)), four("one", arm(10), arm(10)))
        self.assertEqual(self.paused_then(self.exp(*at)), [])
        plan = plan_for(self.root, self.exp(*at, verdict="keep"))
        self.assertEqual([(r["path"], r["rule"]) for r in plan["resume"]],
                         [("evals/alpha/one", "ceiling")])

    def test_a_pooled_pause_resumes_when_one_model_has_room(self):
        # The live case: a pause the pooled rule made, read per model.
        self.assertEqual(self.paused_then(self.exp(four("one", arm(10), arm(10)),
                                                   four("one", arm(10), arm(7)))),
                         [("evals/alpha/one", "ceiling")])

    def test_a_guidance_cell_with_room_is_not_paused(self):
        runs = (on("opus", [guidance_run("fx", arm(10), arm(10, judge=9.0))] * 4)
                + on("sonnet", [guidance_run("fx", arm(10), arm(6, judge=9.0))] * 4))
        doc = explorer(sections={"sec": runs})
        doc["roster"] = ROSTER
        self.assertEqual(self.paused(doc), [])


class ZeroUseTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_repo(self._tmp.name, ["evals/alpha/one", "evals/alpha/two", "evals/beta"])

    def paused(self, usage, plugins=None):
        plan = plan_for(self.root, explorer(), usage, plugins)
        return sorted(p["path"] for p in plan["pause"] if p["rule"] == "zero-use")

    def test_an_unused_skill_pauses_all_its_fixtures(self):
        self.assertEqual(self.paused(usage_doc({"beta": 3})),
                         ["evals/alpha/one", "evals/alpha/two"])

    def test_a_skill_with_unknown_use_is_not_paused(self):
        write(self.root, "evals/usage-unknown.yml",
              'skills:\n  - skill: alpha\n    reason: "listed by name only"\n')
        self.assertEqual(self.paused(usage_doc({"beta": 3})), [])

    def test_a_usage_unknown_row_needs_a_reason(self):
        write(self.root, "evals/usage-unknown.yml", "skills:\n  - skill: alpha\n")
        with self.assertRaises(eval_scope.ScopeError):
            self.paused(usage_doc({"beta": 3}))

    def test_a_used_skill_is_kept(self):
        self.assertEqual(self.paused(usage_doc({"alpha": 1, "beta": 1})), [])

    def test_no_usage_document_means_unknown_and_nothing_happens(self):
        self.assertEqual(self.paused(None), [])

    def test_a_stale_usage_document_means_unknown(self):
        doc = usage_doc()
        doc["generated_at"] = "2026-10-01T00:00:00Z"
        self.assertEqual(self.paused(doc), [])

    def test_exposure_does_not_matter_for_the_pause(self):
        """2026-11-13, Adam: no evals before a first recorded use. Little or
        unknown exposure (5 local sessions, a local-only skill without a
        cloud source) still pauses when every source it needs is current."""
        self.assertEqual(self.paused(usage_doc({"beta": 3}, local=5, cloud_sessions=5)),
                         ["evals/alpha/one", "evals/alpha/two"])
        for doc in (usage_doc({"beta": 3}, cloud=False, local=5),
                    usage_doc({"beta": 3}, cloud=False, local=0)):
            self.assertEqual(self.paused(doc, {"alpha": "adam-coding-local"}),
                             ["evals/alpha/one", "evals/alpha/two"])
        self.assertEqual(self.paused(usage_doc({"beta": 3}), {"alpha": "adam-coding-local"}),
                         ["evals/alpha/one", "evals/alpha/two"])

    def test_a_missing_cloud_source_for_a_cloud_skill_is_unknown_not_zero(self):
        """UNKNOWN IS NOT ZERO: no cloud source reads 0 there, so a skill that
        reaches the cloud is not paused (no plugin layout means both surfaces)."""
        for plugins in (None, {"alpha": "adam-agentskills"}):
            self.assertEqual(self.paused(usage_doc({"beta": 3}, cloud=False, local=500), plugins), [])

    def test_a_skill_the_census_does_not_track_is_not_paused(self):
        doc = usage_doc({"beta": 3})
        for source in doc["sources"]:
            if "skill_keys" in source:
                source["skill_keys"] = ["beta"]
        self.assertEqual(self.paused(doc), [])

    def test_the_why_names_no_recorded_use(self):
        plan = plan_for(self.root, explorer(), usage_doc({"beta": 3}))
        why = next(p["why"] for p in plan["pause"] if p["rule"] == "zero-use")
        self.assertEqual(why, "no recorded use in real work in the last 8 weeks; "
                              "its evals resume on its first recorded use")


class ExclusionTests(unittest.TestCase):
    def test_high_stakes_draft_and_human_rows_are_never_touched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(
                tmp, ["evals/hi/one", "evals/dr/one", "evals/guidance/hg/fx", "evals/ok/one"],
                draft=("evals/dr/one",), high_skills=("hi",), high_sections=("hg",))
            exp = explorer(
                {"hi": four("one", arm(10), arm(10)), "dr": four("one", arm(10), arm(10)),
                 "ok": four("one", arm(10), arm(10))},
                {"hg": [guidance_run("fx", arm(10), arm(10)) for _ in range(4)]})
            plan = plan_for(root, exp, usage_doc())
            self.assertEqual([p["path"] for p in plan["pause"]], ["evals/ok/one"])
            # Ceiling and floor skip a high-stakes subject; zero use does not
            # (below), and a draft is skipped by every rule.
            self.assertNotIn("evals/dr/one", [p["path"] for p in plan["pause"]])

    def test_zero_use_pauses_a_high_stakes_skill_but_not_a_draft(self):
        """2026-11-13: the high-stakes exemption is for ceiling and floor only."""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, ["evals/hi/one", "evals/dr/one"],
                             draft=("evals/dr/one",), high_skills=("hi",))
            doc = usage_doc({"zzz": 1}, cloud=False, local=5)
            for source in doc["sources"]:
                if "skill_keys" in source:
                    source["skill_keys"] = sorted({*source["skill_keys"], "hi", "dr"})
            plan = plan_for(root, explorer(), doc,
                            {"hi": "adam-coding-local", "dr": "adam-coding-local"})
            self.assertEqual([(p["path"], p["rule"]) for p in plan["pause"]],
                             [("evals/hi/one", "zero-use")])

    def test_an_unscheduled_row_the_pass_did_not_write_survives_apply_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, ["evals/alpha/one"])
            exp = explorer({"alpha": four("one", arm(10), arm(10))})
            eval_scope.apply_plan(root, plan_for(root, exp))
            text = (root / "evals/unscheduled.yml").read_text()
            self.assertIn(HUMAN_ROW, text)
            self.assertIn("Auto scope (ceiling), 2026-11-03:", text)
            write(root, "evals/alpha/one/seed/a.txt", "changed\n")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "edit", when=BEFORE)
            plan = plan_for(root, explorer())
            eval_scope.apply_plan(root, plan)
            self.assertIn(HUMAN_ROW, (root / "evals/unscheduled.yml").read_text())


# --- apply and resume ----------------------------------------------------


class RemovedTests(unittest.TestCase):
    """2026-11-13, Adam: a skill removed from its registry stops being
    evaluated with no approval, and its fixtures are kept."""

    LAYOUTS = {"adam-agentskills": "plugins/*/skills/*/SKILL.md",
               "cms-platform": "skills/*/SKILL.md"}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.root = self.repo("repo", ["evals/alpha/one", "evals/alpha/two", "evals/beta"])
        self.cms = base / "cms"
        write(self.cms, "skills/beta/SKILL.md", "---\nname: beta\n---\n")
        write(self.cms, "skills/other/SKILL.md", "---\nname: other\n---\n")
        self.exp = explorer()
        self.exp["skills"] = [{"name": "alpha", "registry": "cms-platform", "runs": []},
                              {"name": "beta", "registry": "cms-platform", "runs": []}]

    def repo(self, name, scheduled, **kwargs):
        path = Path(self._tmp.name) / name
        path.mkdir()
        return make_repo(str(path), scheduled, **kwargs)

    def plan(self, checkouts=None, exp=None):
        return eval_scope.build_plan(self.root, exp or self.exp, None, {}, NOW_DT,
                                     {"cms-platform": self.cms} if checkouts is None else checkouts,
                                     self.LAYOUTS)

    def removed(self, plan):
        return sorted(p["path"] for p in plan["pause"] if p["rule"] == "removed")

    def test_a_skill_confirmed_gone_from_its_registry_is_paused_and_its_fixtures_kept(self):
        plan = self.plan()
        self.assertEqual(self.removed(plan), ["evals/alpha/one", "evals/alpha/two"])
        eval_scope.apply_plan(self.root, plan)
        self.assertTrue((self.root / "evals/alpha/one/fixture.yaml").is_file())
        self.assertEqual([r["path"] for r in eval_scope.read_rows(
            self.root, "evals/scheduled.yml", "fixtures")], ["evals/beta"])
        reasons = {r["path"]: r["reason"] for r in eval_scope.read_rows(
            self.root, "evals/unscheduled.yml", "fixtures")}
        self.assertTrue(reasons["evals/alpha/one"].startswith("Auto scope (removed), 2026-11-03: "))

    def test_it_applies_at_high_stakes(self):
        root = self.repo("hs", ["evals/alpha/one"], high_skills=("alpha",))
        plan = eval_scope.build_plan(root, self.exp, None, {}, NOW_DT,
                                     {"cms-platform": self.cms}, self.LAYOUTS)
        self.assertEqual(self.removed(plan), ["evals/alpha/one"])

    def test_unknown_does_nothing(self):
        # No checkout at all, a checkout that is not a directory, an empty
        # (or sparse) checkout, an entry with no registry, an unknown layout.
        empty = Path(self._tmp.name) / "empty"
        empty.mkdir()
        for checkouts in ({}, {"cms-platform": Path(self._tmp.name) / "nope"},
                          {"cms-platform": empty}):
            self.assertEqual(self.removed(self.plan(checkouts)), [], checkouts)
        no_registry = {"skills": [{"name": "alpha", "runs": []}]}
        self.assertEqual(self.removed(self.plan(exp=no_registry)), [])
        plan = eval_scope.build_plan(self.root, self.exp, None, {}, NOW_DT,
                                     {"cms-platform": self.cms}, {})
        self.assertEqual(self.removed(plan), [])

    def test_a_skill_present_in_its_registry_or_another_visible_one_is_kept(self):
        write(self.cms, "skills/alpha/SKILL.md", "---\nname: alpha\n---\n")
        self.assertEqual(self.removed(self.plan()), [])
        (self.cms / "skills/alpha/SKILL.md").unlink()
        other = Path(self._tmp.name) / "agentskills"
        write(other, "plugins/p/skills/alpha/SKILL.md", "---\nname: alpha\n---\n")
        self.assertEqual(self.removed(self.plan({"cms-platform": self.cms,
                                                 "adam-agentskills": other})), [])

    def test_it_resumes_when_the_skill_reappears_and_stays_when_unknown(self):
        eval_scope.apply_plan(self.root, self.plan())
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "pause")
        self.assertEqual(self.plan()["resume"], [])
        self.assertEqual(self.plan({})["resume"], [])
        write(self.cms, "skills/alpha/SKILL.md", "---\nname: alpha\n---\n")
        plan = self.plan()
        self.assertEqual(sorted((r["path"], r["rule"]) for r in plan["resume"]),
                         [("evals/alpha/one", "removed"), ("evals/alpha/two", "removed")])
        eval_scope.apply_plan(self.root, plan)
        self.assertEqual(eval_scope.read_rows(self.root, "evals/scope-auto.yml", "rows"), [])
        self.assertIn("evals/alpha/one", [r["path"] for r in eval_scope.read_rows(
            self.root, "evals/scheduled.yml", "fixtures")])

    def test_guidance_fixtures_are_never_removed_by_this_rule(self):
        root = self.repo("g", ["evals/guidance/alpha/fx"])
        plan = eval_scope.build_plan(root, self.exp, None, {}, NOW_DT,
                                     {"cms-platform": self.cms}, self.LAYOUTS)
        self.assertEqual(self.removed(plan), [])

    def test_the_command_line_takes_registry_checkouts(self):
        out = Path(self._tmp.name) / "plan.json"
        exp = Path(self._tmp.name) / "exp.json"
        exp.write_text(json.dumps(self.exp), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            code = eval_scope.main(["plan", "--repo-root", str(self.root), "--explorer", str(exp),
                                    "--registry", f"cms-platform={self.cms}", "--now", NOW,
                                    "--out", str(out)])
        self.assertEqual(code, 0)
        self.assertEqual(self.removed(json.loads(out.read_text())),
                         ["evals/alpha/one", "evals/alpha/two"])


class ApplyAndResumeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.paths = ["evals/alpha/one", "evals/alpha/two", "evals/guidance/sec/fx"]
        self.root = make_repo(self._tmp.name, self.paths)
        self.exp = explorer({"alpha": four("one", arm(10), arm(10))},
                            {"sec": [guidance_run("fx", arm(10), arm(10, judge=9.0))
                                     for _ in range(4)]})
        self.before = {f: (self.root / f).read_text() for f in
                       ("evals/scheduled.yml", "evals/unscheduled.yml")}

    def rows(self, rel, key):
        return eval_scope.read_rows(self.root, rel, key)

    def test_apply_pauses_all_three_files(self):
        eval_scope.apply_plan(self.root, plan_for(self.root, self.exp))
        self.assertEqual([r["path"] for r in self.rows("evals/scheduled.yml", "fixtures")],
                         ["evals/alpha/two"])
        auto = self.rows("evals/scope-auto.yml", "rows")
        self.assertEqual([(r["path"], r["rule"], r["since"]) for r in auto],
                         [("evals/alpha/one", "ceiling", "2026-11-03"),
                          ("evals/guidance/sec/fx", "ceiling", "2026-11-03")])
        self.assertEqual(auto[0]["readiness"], "ready evals/alpha/one")
        unsched = {r["path"]: r["reason"] for r in self.rows("evals/unscheduled.yml", "fixtures")}
        self.assertTrue(unsched["evals/alpha/one"].startswith("Auto scope (ceiling), 2026-11-03: "))
        # A guidance fixture gets no unscheduled row.
        self.assertNotIn("evals/guidance/sec/fx", unsched)
        # Headers and the human row are untouched.
        self.assertTrue((self.root / "evals/scheduled.yml").read_text().startswith(SCHEDULED_HEAD))
        self.assertTrue((self.root / "evals/unscheduled.yml").read_text().startswith(
            self.before["evals/unscheduled.yml"]))

    def test_resume_on_a_content_change_restores_everything(self):
        eval_scope.apply_plan(self.root, plan_for(self.root, self.exp))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "pause", when=COMMITTED)
        # Unchanged content: nothing to resume, and the paused fixtures stay paused.
        self.assertEqual(plan_for(self.root, explorer())["resume"], [])
        write(self.root, "evals/alpha/one/seed/a.txt", "a new seed\n")
        write(self.root, "evals/guidance/sec/fx/seed/b.txt", "new\n")
        plan = plan_for(self.root, explorer())
        self.assertEqual(sorted((r["path"], r["rule"]) for r in plan["resume"]),
                         [("evals/alpha/one", "ceiling"), ("evals/guidance/sec/fx", "ceiling")])
        eval_scope.apply_plan(self.root, plan)
        self.assertEqual(self.rows("evals/scope-auto.yml", "rows"), [])
        self.assertEqual(sorted(r["path"] for r in self.rows("evals/scheduled.yml", "fixtures")),
                         sorted(self.paths))
        restored = {r["path"]: r["readiness"] for r in self.rows("evals/scheduled.yml", "fixtures")}
        self.assertEqual(restored["evals/alpha/one"], "ready evals/alpha/one")
        self.assertEqual((self.root / "evals/unscheduled.yml").read_text(),
                         self.before["evals/unscheduled.yml"])

    def test_zero_use_resumes_when_the_skill_is_used_and_stays_when_unknown(self):
        eval_scope.apply_plan(self.root, plan_for(self.root, explorer(), usage_doc({"zzz": 1})))
        self.assertEqual(sorted(r["rule"] for r in self.rows("evals/scope-auto.yml", "rows")),
                         ["zero-use", "zero-use"])
        self.assertEqual(plan_for(self.root, explorer(), None)["resume"], [])
        plan = plan_for(self.root, explorer(), usage_doc({"alpha": 2}))
        self.assertEqual(sorted(r["path"] for r in plan["resume"]),
                         ["evals/alpha/one", "evals/alpha/two"])
        eval_scope.apply_plan(self.root, plan)
        self.assertEqual([r["path"] for r in self.rows("evals/scope-auto.yml", "rows")], [])
        self.assertIn("evals/alpha/two",
                      [r["path"] for r in self.rows("evals/scheduled.yml", "fixtures")])

    def test_zero_use_resumes_when_the_skill_is_listed_as_unknown_use(self):
        eval_scope.apply_plan(self.root, plan_for(self.root, explorer(), usage_doc({"zzz": 1})))
        write(self.root, "evals/usage-unknown.yml",
              'skills:\n  - skill: alpha\n    reason: "listed by name only"\n')
        plan = plan_for(self.root, explorer(), usage_doc({"zzz": 1}))
        self.assertEqual(sorted(r["path"] for r in plan["resume"]),
                         ["evals/alpha/one", "evals/alpha/two"])
        self.assertIn("listed by name only", plan["resume"][0]["why"])
        self.assertEqual(plan["pause"], [])

    def test_a_stale_plan_is_refused(self):
        plan = plan_for(self.root, self.exp)
        write(self.root, "evals/alpha/one/seed/a.txt", "moved on\n")
        with self.assertRaises(eval_scope.ScopeError):
            eval_scope.apply_plan(self.root, plan)
        self.assertEqual((self.root / "evals/scheduled.yml").read_text(),
                         self.before["evals/scheduled.yml"])

    def test_a_pass_never_resumes_a_row_it_did_not_write(self):
        plan = {"schema": 1, "now": NOW, "pause": [], "resume": [
            {"path": "evals/human-skill", "kind": "skill", "subject": "human-skill",
             "rule": "ceiling", "why": "x"}]}
        with self.assertRaises(eval_scope.ScopeError):
            eval_scope.apply_plan(self.root, plan)

    def test_the_summary_lists_each_change_with_its_reason(self):
        text = eval_scope.summary(plan_for(self.root, self.exp))
        self.assertEqual(len(text.strip().splitlines()), 2)
        self.assertIn("Pause `evals/alpha/one` (ceiling): the without arm passed 1.00", text)

    def test_the_command_line_plans_applies_and_summarizes(self):
        out = Path(self._tmp.name).parent / f"{Path(self._tmp.name).name}-plan.json"
        self.addCleanup(lambda: out.unlink(missing_ok=True))
        ex = Path(self._tmp.name).parent / f"{Path(self._tmp.name).name}-explorer.json"
        self.addCleanup(lambda: ex.unlink(missing_ok=True))
        ex.write_text(json.dumps(self.exp), encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = eval_scope.main(["plan", "--repo-root", str(self.root), "--explorer", str(ex),
                                    "--now", NOW, "--out", str(out)])
        self.assertEqual((code, buf.getvalue()), (0, "count=2\n"))
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(eval_scope.main(["summary", "--plan", str(out)]), 0)
        self.assertIn("Pause `evals/guidance/sec/fx`", buf.getvalue())
        self.assertEqual(eval_scope.main(["apply", "--plan", str(out), "--repo-root",
                                          str(self.root)]), 0)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(eval_scope.main(["plan", "--repo-root", str(self.root), "--explorer",
                                              str(ex), "--now", "nonsense", "--out", str(out)]), 1)


# --- the committed state -------------------------------------------------


class CommittedScopeAutoTests(unittest.TestCase):
    """The loader test: the committed file has its shape and agrees with the
    schedule."""

    ROW_FIELDS = {"path", "rule", "since", "fixture_digest", "readiness"}

    def test_shape_and_agreement_with_the_other_files(self):
        doc = yaml.safe_load((ROOT / "evals/scope-auto.yml").read_text(encoding="utf-8"))
        self.assertEqual(set(doc), {"rows"})
        rows = doc["rows"]
        self.assertIsInstance(rows, list)
        scheduled = {r["path"] for r in eval_scope.read_rows(ROOT, "evals/scheduled.yml", "fixtures")}
        unscheduled = {r["path"]: r["reason"]
                       for r in eval_scope.read_rows(ROOT, "evals/unscheduled.yml", "fixtures")}
        seen = set()
        for row in rows:
            self.assertEqual(set(row), self.ROW_FIELDS)
            self.assertIn(row["rule"], eval_scope.RULES)
            self.assertRegex(str(row["since"]), r"\A\d{4}-\d{2}-\d{2}\Z")
            self.assertRegex(row["fixture_digest"], r"\A[0-9a-f]{64}\Z")
            self.assertTrue(row["readiness"].strip() and "\n" not in row["readiness"])
            self.assertTrue((ROOT / row["path"]).is_dir(), row["path"])
            self.assertNotIn(row["path"], seen)
            seen.add(row["path"])
            self.assertNotIn(row["path"], scheduled)
            if not row["path"].startswith("evals/guidance/"):
                self.assertTrue(unscheduled[row["path"]].startswith(
                    f"Auto scope ({row['rule']}), "), row["path"])

    def test_a_synthetic_bad_file_would_fail_the_agreement(self):
        # The loader's own check, run on a tree where a paused path is
        # scheduled: apply_plan refuses to leave that state.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_repo(tmp, ["evals/alpha/one"])
            eval_scope.apply_plan(root, plan_for(
                root, explorer({"alpha": four("one", arm(10), arm(10))})))
            scheduled = {r["path"] for r in eval_scope.read_rows(root, "evals/scheduled.yml", "fixtures")}
            auto = {r["path"] for r in eval_scope.read_rows(root, "evals/scope-auto.yml", "rows")}
            self.assertFalse(scheduled & auto)


# --- the workflow --------------------------------------------------------


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.on = cls.doc.get("on", cls.doc.get(True))

    def test_triggers(self):
        self.assertEqual(set(self.on), {"workflow_run", "schedule", "workflow_dispatch"})
        self.assertNotIn("push", self.on)
        self.assertNotIn("pull_request", self.on)
        self.assertNotIn("pull_request_target", self.on)
        run = self.on["workflow_run"]
        self.assertEqual(run["types"], ["completed"])
        ingest = yaml.safe_load(
            (ROOT / ".github/workflows/routine-eval-ingest.yml").read_text(encoding="utf-8"))
        self.assertEqual(run["workflows"], [ingest["name"]])
        self.assertEqual(len(self.on["schedule"]), 1)
        # Success only, on the default branch.
        cond = self.doc["jobs"]["plan"]["if"]
        self.assertIn("workflow_run.conclusion == 'success'", cond)
        self.assertIn("default_branch", cond)

    def test_permissions_are_empty_at_the_top_and_least_below(self):
        self.assertEqual(self.doc["permissions"], {})
        self.assertEqual(self.doc["jobs"]["plan"]["permissions"], {"contents": "read"})
        self.assertEqual(self.doc["jobs"]["propose"]["permissions"],
                         {"contents": "read", "pull-requests": "read"})

    def test_no_concurrency_group_anywhere(self):
        self.assertNotIn("concurrency", self.doc)
        for job in self.doc["jobs"].values():
            self.assertNotIn("concurrency", job)

    def test_no_expression_in_any_run_block(self):
        blocks = [step["run"] for job in self.doc["jobs"].values()
                  for step in job["steps"] if "run" in step]
        self.assertTrue(blocks)
        for body in blocks:
            self.assertNotIn("${{", body)

    def test_no_checkout_keeps_credentials_and_main_has_full_history(self):
        for job in self.doc["jobs"].values():
            for step in job["steps"]:
                if str(step.get("uses", "")).startswith("actions/checkout"):
                    self.assertIs(step["with"]["persist-credentials"], False)
        first = self.doc["jobs"]["plan"]["steps"][0]
        self.assertEqual(first["with"]["fetch-depth"], 0)

    def test_every_action_is_locked(self):
        uses = [step["uses"] for job in self.doc["jobs"].values()
                for step in job["steps"] if "uses" in step]
        self.assertTrue(uses)
        for pinned in uses:
            self.assertIsNone(lock_problem(pinned, WORKFLOW), pinned)

    def test_the_mint_step_degrades_and_the_pr_is_armed_with_a_merge_commit(self):
        steps = self.doc["jobs"]["propose"]["steps"]
        mint = next(s for s in steps if s.get("id") == "app-token")
        self.assertIs(mint["continue-on-error"], True)
        body = next(s["run"] for s in steps if "gh pr create" in s.get("run", "")
                    or "pr create" in s.get("run", ""))
        self.assertIn("--auto --merge --match-head-commit", body)
        self.assertNotIn("--draft", body)
        self.assertIn("## TLDR", body)
        self.assertIn("<sub>🤖 Written by Claude Code on behalf of @Adam-S-Daniel</sub>", body)
        self.assertRegex(body, r'branch="eval-scope/\$\{RUN_ID\}"')
        names = [s.get("name", "") for s in steps]
        scope_i = names.index("Apply the plan and check its scope")
        self.assertLess(scope_i, names.index("Mint the roster App token"),
                        "the scope check must run before the App token is minted")
        scope = steps[scope_i]["run"]
        self.assertIn('startswith("eval-scope/")', scope)
        self.assertIn("evals/scheduled.yml|evals/unscheduled.yml|evals/scope-auto.yml", scope)
        self.assertNotIn("app_token", scope)

    def test_the_removed_rule_sees_all_three_public_registries(self):
        steps = self.doc["jobs"]["plan"]["steps"]
        repos = {s["with"]["repository"]: s["with"] for s in steps
                 if str(s.get("uses", "")).startswith("actions/checkout")
                 and "repository" in s.get("with", {})}
        for name in ("adam-agentskills", "cms-platform", "adamdaniel.ai"):
            self.assertIn(f"Adam-S-Daniel/{name}", repos)
        layouts = {r["name"]: r["layout"]
                   for r in yaml.safe_load((ROOT / "harness/registries.yml").read_text())["registries"]}
        run = next(s["run"] for s in steps if s.get("id") == "plan")
        for name, path in (("adam-agentskills", "registry-agentskills"), ("cms-platform", "registry-cms"),
                           ("adamdaniel.ai", "registry-site")):
            self.assertIn(f'--registry "{name}=$GITHUB_WORKSPACE/ctx/{path}"', run)
            sparse = repos[f"Adam-S-Daniel/{name}"]
            # Sparse and read-only, and the sparse pattern is the layout.
            self.assertEqual(sparse["path"], f"ctx/{path}")
            self.assertIs(sparse["persist-credentials"], False)
            self.assertEqual(sparse["sparse-checkout"], "/" + layouts[name])

    def test_the_agents_md_row_exists(self):
        text = (ROOT / "docs" / "workflows.md").read_text(encoding="utf-8")
        row = next(line for line in text.splitlines() if line.startswith("| `eval-scope.yml`"))
        for needle in ("workflow_run", "schedule", "dispatch", "no path filter"):
            self.assertIn(needle, row)

    def test_the_lockfile_lists_the_workflow(self):
        lock = yaml.safe_load((ROOT / ".github/workflows/actions.lock").read_text(encoding="utf-8"))
        self.assertIn(".github/workflows/eval-scope.yml", lock["workflows"])

    def test_the_script_never_reads_yaml_by_regex(self):
        # The one lexical split (entry boundaries) is checked against yaml.
        src = (ROOT / "scripts/eval_scope.py").read_text(encoding="utf-8")
        self.assertNotIn("import re\n", src)
        self.assertIsNone(re.search(r"^from re import", src, re.M))


if __name__ == "__main__":
    unittest.main()
