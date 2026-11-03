#!/usr/bin/env python3
"""ADR 0014's known limit (round 8): an open automatic removal pull request
is withdrawn once its subject's verdict no longer supports it.

scripts/retire_skill.py --withdraw-stale lists the target repository's open
pull requests and, for each the loop opened (`retire-skill/` or
`retire-guidance/` head AND the `agent-authored` label, not `on-hold`),
re-reads the subject's verdict. Anything but `retire` with an automatic
removal turns auto-merge off, comments the new verdict and closes the pull
request (branch kept). Unknown data never withdraws.

Hermetic: hand-written gates documents with invented names, a fake `gh`;
no network, no clock, no sleeps.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

import compute_gates  # noqa: E402
import retire_skill as rs  # noqa: E402

MODELS = ["model-a", "model-b"]
SCHEDULE = {"GITHUB_EVENT_NAME": "schedule"}
AUTO_ENV = {**SCHEDULE, "GITHUB_ACTIONS": "true", "GITHUB_REF": "refs/heads/main"}
SKILL = "example-skill"
SECTION = "example-section"
SKILL_URL = f"https://github.com/{rs.REGISTRY_REPO}/pull/41"
GUIDANCE_URL = f"https://github.com/{rs.GUIDANCE_REPO}/pull/42"


def cell(fixture, model, cls="no-benefit"):
    return {"fixture": fixture, "model": model, "class": cls,
            "with": {"runs": 20}, "without": {"runs": 20}}


def retire(removal="auto", classes=("no-benefit", "no-benefit")):
    """A `retire` verdict over two fixtures; `classes` sets fixture b's cells."""
    cells = [cell("fx-a", m) for m in MODELS] + [
        cell("fx-b", m, c) for m, c in zip(MODELS, classes)]
    return {"verdict": "retire", "reason": "every cell shows no benefit",
            "removal": removal, "removal_reason": "invented removal reason",
            "cells": cells}


VERDICTS = {
    "keep": {"verdict": "keep", "reason": "a cell shows benefit", "cells": []},
    "insufficient": {"verdict": "insufficient", "reason": "a cell is insufficient or missing",
                     "cells": []},
    "retire+auto": retire("auto"),
    "retire+proposal": retire("proposal"),
}


def doc(block=None, guidance=None, as_of="20261101T000000Z"):
    out = {"schema_version": 1, "as_of": as_of, "roster_models": MODELS,
           "retirement_mode": "proposal", "skills": block if block is not None else {}}
    if guidance is not None:
        out["guidance"] = guidance
    return out


def pr(head=f"{rs.BRANCH_PREFIX}{SKILL}", labels=(rs.AGENT_LABEL,), number=41, url=SKILL_URL):
    return {"number": number, "head": head, "url": url,
            "labels": None if labels is None else list(labels)}


class DecisionTests(unittest.TestCase):
    """withdrawal_decision: one call per verdict shape, no I/O."""

    def decide(self, verdict=None, *, present=True, gates=..., **kw):
        if gates is ...:
            gates = doc({SKILL: verdict} if present else {"other-skill": VERDICTS["keep"]})
        return rs.withdrawal_decision(pr(**kw), gates)

    def test_keep_withdraws(self):
        d = self.decide(VERDICTS["keep"])
        self.assertEqual(d["action"], "withdraw")
        self.assertEqual((d["subject"], d["verdict"]), (SKILL, "keep"))

    def test_insufficient_withdraws(self):
        d = self.decide(VERDICTS["insufficient"])
        self.assertEqual((d["action"], d["verdict"]), ("withdraw", "insufficient"))

    def test_retire_with_an_automatic_removal_keeps(self):
        self.assertEqual(self.decide(VERDICTS["retire+auto"])["action"], "keep")

    def test_retire_with_a_proposal_removal_withdraws(self):
        d = self.decide(VERDICTS["retire+proposal"])
        self.assertEqual((d["action"], d["verdict"], d["removal"]),
                         ("withdraw", "retire", "proposal"))

    def test_retire_auto_whose_cells_allow_only_a_proposal_withdraws(self):
        # The field says auto, but a no-clear-effect headroom cell makes it a
        # proposal (retire_skill.proposal_only): it should not be auto-merging.
        d = self.decide(retire("auto", ("no-benefit", "no-clear-effect")))
        self.assertEqual(d["action"], "withdraw")

    def test_retire_pending_withdraws(self):
        d = self.decide({**retire("auto"), "verdict": "retire-pending",
                         "reason": "only one skill retires per evaluation"})
        self.assertEqual((d["action"], d["verdict"]), ("withdraw", "retire-pending"))

    def test_a_subject_missing_from_the_verdicts_withdraws(self):
        d = self.decide(present=False)
        self.assertEqual((d["action"], d["verdict"]), ("withdraw", None))

    def test_a_missing_document_withdraws_nothing(self):
        self.assertEqual(self.decide(gates=None)["action"], "keep")
        self.assertEqual(self.decide(gates={"schema_version": 1})["action"], "keep")

    def test_a_verdict_that_could_not_be_computed_withdraws_nothing(self):
        raised = {"verdict": "insufficient", "cells": [], "runs_used": [],
                  "reason": f"{compute_gates.VERDICT_RAISED}ZeroDivisionError"}
        for entry in (raised, "insufficient", {"reason": "no verdict field"},
                      {"verdict": "keep"}):
            with self.subTest(entry=entry):
                self.assertEqual(self.decide(entry)["action"], "keep")

    def test_a_malformed_retire_withdraws_nothing(self):
        broken = retire("proposal")
        broken["cells"] = broken["cells"][:-1]  # no longer the cross product
        self.assertEqual(self.decide(broken)["action"], "keep")

    def test_on_hold_is_left_alone(self):
        d = self.decide(VERDICTS["keep"], labels=(rs.AGENT_LABEL, "on-hold"))
        self.assertEqual(d["action"], "ignore")

    def test_non_loop_pull_requests_are_left_alone(self):
        for kw in ({"labels": ()},
                   {"labels": ("documentation",)},
                   {"head": f"someone/{SKILL}"},
                   {"head": f"eval-improve/{SKILL}"},
                   {"head": f"{rs.GUIDANCE_BRANCH_PREFIX}{SKILL}"},
                   {"head": None}, {"labels": None}):
            with self.subTest(**{k: str(v) for k, v in kw.items()}):
                self.assertEqual(self.decide(VERDICTS["keep"], **kw)["action"], "ignore")

    def test_a_head_that_names_no_subject_withdraws_nothing(self):
        d = self.decide(VERDICTS["keep"], head=f"{rs.BRANCH_PREFIX}Bad Name")
        self.assertEqual(d["action"], "keep")

    def test_the_verdict_compute_gates_writes_on_a_raise_carries_the_prefix(self):
        self.assertEqual(compute_gates.VERDICT_RAISED, "the verdict raised ")


class GuidanceDecisionTests(unittest.TestCase):
    def decide(self, guidance, **kw):
        kw.setdefault("head", f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}")
        kw.setdefault("url", GUIDANCE_URL)
        return rs.withdrawal_decision(pr(**kw), doc(guidance=guidance), "guidance")

    def test_each_verdict_shape(self):
        want = {"keep": "withdraw", "insufficient": "withdraw", "retire+auto": "keep",
                "retire+proposal": "withdraw"}
        for name, action in want.items():
            with self.subTest(verdict=name):
                self.assertEqual(self.decide({SECTION: VERDICTS[name]})["action"], action)
        self.assertEqual(self.decide({"other": VERDICTS["keep"]})["action"], "withdraw")

    def test_no_guidance_block_withdraws_nothing(self):
        self.assertEqual(self.decide(None)["action"], "keep")

    def test_a_skill_branch_is_not_a_guidance_loop_pull_request(self):
        d = self.decide({SECTION: VERDICTS["keep"]}, head=f"{rs.BRANCH_PREFIX}{SECTION}")
        self.assertEqual(d["action"], "ignore")


class FakeGh:
    """Answers the open pull request listing and the auto-merge read-back;
    records every call. `armed` is the read-back's state, turned off by
    `--disable-auto` unless `stuck`."""

    def __init__(self, prs=(), armed=True, stuck=False, fail=None):
        self.prs, self.armed, self.stuck, self.fail = list(prs), armed, stuck, fail
        self.calls = []

    def __call__(self, args, stdin=None):
        self.calls.append((list(args), stdin))
        if self.fail and args[:2] == self.fail:
            raise rs.RetireError(f"gh {args[0]} exited 1")
        if args[:2] == ["api", "--paginate"]:
            return "".join(json.dumps(p) + "\n" for p in self.prs)
        if args[:2] == ["pr", "merge"] and "--disable-auto" in args and not self.stuck:
            self.armed = False
        if args[:2] == ["pr", "view"]:
            return ("MERGE" if self.armed else "") + "\n"
        return ""

    def writes(self):
        return [a for a, _ in self.calls if a[:2] != ["api", "--paginate"]
                and a[:2] != ["pr", "view"]]


class WithdrawStaleTests(unittest.TestCase):
    """The thin layer: the calls, in order, with the fake."""

    def test_disarms_then_comments_then_closes_keeping_the_branch(self):
        gh = FakeGh()
        gates = doc({SKILL: VERDICTS["keep"]})
        lines = rs.withdraw_stale(gates, [pr()], "skill", gh,
                                  "https://github.com/Adam-S-Daniel/skills-evals/actions/runs/1")
        self.assertEqual(lines, ["withdrew #41: the verdict is keep, not retire"])
        repo = rs.REGISTRY_REPO
        self.assertEqual(gh.writes(), [
            ["pr", "merge", SKILL_URL, "-R", repo, "--disable-auto"],
            ["pr", "comment", SKILL_URL, "-R", repo, "--body-file", "-"],
            ["pr", "close", SKILL_URL, "-R", repo]])
        self.assertFalse(any("--delete-branch" in a for a, _ in gh.calls))
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn("**keep**", body)
        self.assertIn("a cell shows benefit", body)
        self.assertIn("20261101T000000Z", body)
        self.assertIn(rs.WITHDRAWN_MARKER.format(subject=SKILL), body)
        self.assertTrue(body.rstrip("\n").endswith(
            "<sub>🤖 Written by Claude Code on behalf of @Adam-S-Daniel</sub>"))
        self.assertFalse(gh.armed)

    def test_a_missing_subject_comment_says_there_is_no_verdict(self):
        gh = FakeGh()
        rs.withdraw_stale(doc({}), [pr()], "skill", gh)
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn("has no verdict", body)

    def test_an_unarmed_pull_request_is_commented_and_closed_without_a_disable(self):
        gh = FakeGh(armed=False)
        rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        self.assertEqual([a[1] for a in gh.writes()], ["comment", "close"])

    def test_auto_merge_still_on_after_the_disable_refuses_before_closing(self):
        gh = FakeGh(stuck=True)
        with self.assertRaises(rs.RetireError):
            rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        self.assertEqual([a[1] for a in gh.writes()], ["merge"])

    def test_kept_and_ignored_pull_requests_get_no_write(self):
        gh = FakeGh()
        prs = [pr(), pr(head="eval-improve/x", number=7,
                        url=f"https://github.com/{rs.REGISTRY_REPO}/pull/7"),
               pr(labels=(rs.AGENT_LABEL, "on-hold"))]
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["retire+auto"]}), prs, "skill", gh)
        self.assertEqual(gh.writes(), [])
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("kept #41"))

    def test_a_withdrawal_with_a_foreign_url_is_refused(self):
        gh = FakeGh()
        bad = pr(url=f"https://github.com/{rs.GUIDANCE_REPO}/pull/41")
        with self.assertRaises(rs.RetireError):
            rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [bad], "skill", gh)
        self.assertEqual(gh.writes(), [])

    def test_the_guidance_pass_writes_to_agent_guidance(self):
        gh = FakeGh()
        gpr = pr(head=f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}", number=42, url=GUIDANCE_URL)
        rs.withdraw_stale(doc(guidance={SECTION: VERDICTS["insufficient"]}), [gpr],
                          "guidance", gh)
        self.assertEqual([a[-1] if a[1] == "close" else a[1] for a in gh.writes()],
                         ["merge", "comment", rs.GUIDANCE_REPO])
        self.assertTrue(all(rs.GUIDANCE_REPO in a for a in gh.writes()))


class MainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        for p in self.tmp.iterdir():
            p.unlink()
        self.tmp.rmdir()

    def run_main(self, gates, *extra, env=AUTO_ENV, gh=None):
        path = self.tmp / "gates.json"
        if gates is not None:
            path.write_text(gates if isinstance(gates, str) else json.dumps(gates))
        gh = gh or FakeGh([pr()])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            code = rs.main(["--withdraw-stale", "--gates", str(path), *extra], env=env,
                           gh=gh, out=out)
        return code, out.getvalue(), err.getvalue(), gh

    def test_withdraws_a_stale_pull_request(self):
        code, out, _, gh = self.run_main(doc({SKILL: VERDICTS["keep"]}))
        self.assertEqual(code, 0)
        self.assertIn("withdrew #41", out)
        self.assertEqual([a[1] for a in gh.writes()], ["merge", "comment", "close"])

    def test_a_missing_or_unreadable_document_withdraws_nothing_and_exits_0(self):
        for gates in (None, "{not json", json.dumps({"schema_version": 2})):
            with self.subTest(gates=gates):
                code, out, _, gh = self.run_main(gates)
                self.assertEqual(code, 0)
                self.assertEqual(gh.calls, [])
                self.assertIn("withdrew nothing", out)
                self.assertNotIn(SKILL, out)

    def test_a_guidance_pass_without_a_guidance_block_withdraws_nothing(self):
        code, out, _, gh = self.run_main(doc({SKILL: VERDICTS["keep"]}), "--target",
                                         "guidance")
        self.assertEqual((code, gh.calls), (0, []))
        self.assertIn("withdrew nothing", out)

    def test_only_the_schedule_acts(self):
        code, _, err, gh = self.run_main(doc({SKILL: VERDICTS["keep"]}),
                                         env={"GITHUB_EVENT_NAME": "workflow_dispatch"})
        self.assertEqual(code, 2)
        self.assertEqual(gh.calls, [])

    def test_writes_only_in_github_actions_on_main(self):
        code, _, err, gh = self.run_main(doc({SKILL: VERDICTS["keep"]}), env=SCHEDULE)
        self.assertEqual(code, 2)
        self.assertEqual(gh.writes(), [])
        self.assertIn("refusing", err)

    def test_nothing_stale_needs_no_actions_environment(self):
        code, out, _, gh = self.run_main(doc({SKILL: VERDICTS["retire+auto"]}), env=SCHEDULE)
        self.assertEqual((code, gh.writes()), (0, []))
        self.assertIn("kept #41", out)

    def test_dry_run_prints_the_plan_and_writes_nothing(self):
        code, out, _, gh = self.run_main(doc({SKILL: VERDICTS["keep"]}), "--dry-run", env={})
        self.assertEqual((code, gh.writes()), (0, []))
        plan = json.loads(out)
        self.assertEqual([i["action"] for i in plan["withdraw"]], ["withdraw"])
        self.assertEqual(plan["would_run"][-1], ["gh", "pr", "close", SKILL_URL, "-R",
                                                 rs.REGISTRY_REPO])

    def test_a_failed_call_exits_2_with_its_exit_code_only(self):
        gh = FakeGh([pr()], fail=["pr", "close"])
        code, _, err, _ = self.run_main(doc({SKILL: VERDICTS["keep"]}), gh=gh)
        self.assertEqual(code, 2)
        self.assertEqual(err.strip(), "retire_skill: gh pr exited 1")


class GuidanceDecidedTests(unittest.TestCase):
    """A withdrawn (closed) retire-guidance/ pull request decides its section,
    as a closed retire-skill/ one decides a skill: no removal reopens it."""

    def test_a_closed_removal_pull_request_decides_the_section(self):
        cells = [{"fixture": "fx", "model": m, "class": "no-benefit"} for m in MODELS] + [
            {"fixture": "fy", "model": m, "class": "no-benefit"} for m in MODELS]
        gates = {**doc(), "guidance_retirement_mode": "auto",
                 "guidance": {SECTION: {"verdict": "retire", "removal": "auto",
                                        "reason": "every cell shows no benefit",
                                        "cells": cells}}}
        closed = {"number": 42, "head": f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}",
                  "url": GUIDANCE_URL}

        def gh(args, stdin=None):
            if "state=closed" in args[2]:
                return json.dumps(closed) + "\n"
            return ""

        plan = rs.guidance_plan(gates, None, gh, allowed=("proposal", "auto"))
        self.assertEqual(plan["action"], "none")
        self.assertIn("already decided", plan["reason"])


class WorkflowTests(unittest.TestCase):
    """skill-coverage.yml's retirement job, read with a YAML parser."""

    def setUp(self):
        doc_ = yaml.safe_load((ROOT / ".github/workflows/skill-coverage.yml").read_text())
        self.steps = doc_["jobs"]["retirement"]["steps"]

    def step(self, name):
        return next(s for s in self.steps if s.get("name") == name)

    def commands(self, step):
        """The run block's retire_skill.py invocations, continuation lines joined."""
        joined = step["run"].replace("\\\n", " ")
        return [" ".join(line.split()) for line in joined.splitlines()
                if "scripts/retire_skill.py" in line]

    def test_each_pass_withdraws_before_it_acts(self):
        for name, token, guidance in (
                ("Act on the skill retirement verdict", "app-token", False),
                ("Act on the guidance retirement verdict", "guidance-token", True)):
            step = self.step(name)
            cmds = self.commands(step)
            with self.subTest(step=name):
                self.assertEqual(len(cmds), 2)
                withdraw, act = cmds
                self.assertIn("--withdraw-stale", withdraw)
                self.assertNotIn("--withdraw-stale", act)
                self.assertNotIn("--dry-run", withdraw)
                self.assertIn('--gates "$RUNNER_TEMP/gates/latest.json"', withdraw)
                self.assertEqual("--target guidance" in withdraw, guidance)
                self.assertEqual("--target guidance" in act, guidance)
                self.assertTrue(step["run"].lstrip().startswith("set -euo pipefail"))
                self.assertEqual(step["env"], {
                    "GH_TOKEN": "${{ github.token }}",
                    "REGISTRY_TOKEN": f"${{{{ steps.{token}.outputs.token }}}}"})


if __name__ == "__main__":
    unittest.main()
