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
import os
import subprocess
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


def gretire(removal="auto", alone=("no-benefit", "no-benefit")):
    """A section's `retire` (`retire`) with its section-alone pair; the
    default pair is finished, so the retire is not held to a proposal
    (#738, gates.alone_unfinished)."""
    return {**retire(removal),
            "alone": {"verdict": "retire", "cells": [cell("fx-a", m, c)
                                                     for m, c in zip(MODELS, alone)]}}


VERDICTS = {
    "keep": {"verdict": "keep", "reason": "a cell shows benefit", "cells": []},
    "insufficient": {"verdict": "insufficient", "reason": "a cell is insufficient or missing",
                     "cells": []},
    "retire+auto": retire("auto"),
    "retire+proposal": retire("proposal"),
}


def doc(block=None, guidance=None, as_of="20261101T000000Z", mode="auto"):
    out = {"schema_version": 1, "as_of": as_of, "roster_models": MODELS,
           "retirement_mode": mode, "skills": block if block is not None else {}}
    if guidance is not None:
        out["guidance"] = guidance
        out["guidance_retirement_mode"] = mode
    return out


#: Before every `doc()` as_of below: these verdicts may judge the pull request.
OPENED = "2026-10-31T00:00:00Z"


def pr(head=f"{rs.BRANCH_PREFIX}{SKILL}", labels=(rs.AGENT_LABEL,), number=41, url=SKILL_URL,
       author=rs.LOOP_AUTHOR, created_at=OPENED):
    out = {"number": number, "head": head, "url": url,
           "labels": None if labels is None else list(labels), "author": author}
    if created_at is not None:
        out["created_at"] = created_at
    return out


def pending(entry, raw="retire"):
    """`entry` as compute_gates.finalize leaves a confirmed subject another
    one outranked: verdict retire-pending, raw_verdict kept."""
    return {**entry, "verdict": "retire-pending", "raw_verdict": raw,
            "reason": "no benefit is confirmed, but only one skill retires per "
                      "evaluation and other-skill has more runs"}


class DecisionTests(unittest.TestCase):
    """withdrawal_decision: one call per verdict shape, no I/O."""

    def decide(self, verdict=None, *, present=True, gates=..., mode="auto", **kw):
        if gates is ...:
            gates = doc({SKILL: verdict} if present else {"other-skill": VERDICTS["keep"]},
                        mode=mode)
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

    def test_retire_pending_with_a_confirmed_automatic_removal_keeps(self):
        # Round 1's M1: finalize demotes all but one confirmed subject per
        # evaluation to retire-pending; that ranks it and says nothing
        # against it, so the removal it already has stays open.
        d = self.decide(pending(retire("auto")))
        self.assertEqual(d["action"], "keep")

    def test_retire_pending_whose_raw_verdict_is_not_an_automatic_retire_withdraws(self):
        for name, entry in (("raw retire, proposal removal", pending(retire("proposal"))),
                            ("raw retire, cells allow a proposal only",
                             pending(retire("auto", ("no-benefit", "no-clear-effect")))),
                            ("no raw verdict", {**pending(retire("auto")),
                                                "raw_verdict": None}),
                            ("raw keep", pending(retire("auto"), raw="keep"))):
            with self.subTest(name):
                d = self.decide(entry)
                self.assertEqual((d["action"], d["verdict"]), ("withdraw", "retire-pending"))

    def test_retire_pending_from_finalize_keeps_the_outranked_removal(self):
        # The sequence round 1 simulated, through compute_gates.finalize: B
        # confirms with more runs, A is demoted, and A's open PR stays.
        def confirmed(runs):
            return {**retire("auto"), "runs_used": [f"r{i}" for i in range(runs)]}
        block = {SKILL: confirmed(10), "other-skill": confirmed(12)}
        compute_gates.finalize(block)
        self.assertEqual(block[SKILL]["verdict"], "retire-pending")
        self.assertEqual(rs.withdrawal_decision(pr(), doc(block))["action"], "keep")

    def test_a_subject_missing_from_the_verdicts_withdraws_nothing(self):
        # Round 1's minor 1: absent from a readable document is unknown data.
        d = self.decide(present=False)
        self.assertEqual(d["action"], "keep")
        self.assertIn("does not list", d["why"])

    def test_an_empty_or_partial_block_withdraws_nothing(self):
        prs = [pr(), pr(head=f"{rs.BRANCH_PREFIX}beta-skill", number=2,
                        url=f"https://github.com/{rs.REGISTRY_REPO}/pull/2")]
        for block in ({}, {"other-skill": VERDICTS["keep"]}):
            with self.subTest(block=block):
                self.assertEqual([i["action"] for i in rs.withdraw_plan(doc(block), prs,
                                                                         "skill")],
                                 ["keep", "keep"])

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
        self.assertEqual(self.decide(pending(broken))["action"], "keep")

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

    def test_a_pull_request_the_loop_app_did_not_open_is_left_alone(self):
        # Round 1's minor 3: every agent-authored pull request carries the
        # label, so a hand-opened removal (a person or an agent acting on a
        # proposal issue) is told apart by its author.
        for author in ("Adam-S-Daniel", "github-actions[bot]", "skills-evals-roster[bot]",
                       None, ""):
            with self.subTest(author=author):
                d = self.decide(VERDICTS["retire+proposal"], author=author)
                self.assertEqual(d["action"], "ignore")

    def test_the_loop_author_is_the_eval_improve_apps_bot(self):
        self.assertEqual(rs.LOOP_AUTHOR, "skills-evals-improve[bot]")

    def test_a_pull_request_reopened_without_the_label_is_left_alone(self):
        # Round 1's M4: the documented override. A person removes
        # agent-authored, then reopens and merges; no pass touches it.
        for verdict in ("keep", "insufficient", "retire+proposal"):
            with self.subTest(verdict=verdict):
                self.assertEqual(self.decide(VERDICTS[verdict], labels=())["action"],
                                 "ignore")
        self.assertEqual(self.decide(VERDICTS["keep"], labels=())["action"], "ignore")

    def test_a_head_that_names_no_subject_withdraws_nothing(self):
        d = self.decide(VERDICTS["keep"], head=f"{rs.BRANCH_PREFIX}Bad Name")
        self.assertEqual(d["action"], "keep")
        # Even when the document lists that name with a stale verdict: the
        # head never names a subject, so nothing reaches the comment.
        bad = "Bad Name"
        d = rs.withdrawal_decision(pr(head=f"{rs.BRANCH_PREFIX}{bad}"),
                                   doc({bad: VERDICTS["keep"]}))
        self.assertEqual(d, {"action": "keep", "why": "its head names no subject"})

    def test_the_verdict_compute_gates_writes_on_a_raise_carries_the_prefix(self):
        self.assertEqual(compute_gates.VERDICT_RAISED, "the verdict raised ")


class CreatedAfterTests(unittest.TestCase):
    """PR #724 round 2's R2-1: a pass on older verdicts never withdraws a
    removal pull request opened after them (the gates' `as_of`)."""

    GATES = doc({SKILL: VERDICTS["insufficient"]}, as_of="20261101T080000Z")

    def decide(self, created_at, gates=None):
        return rs.withdrawal_decision(pr(created_at=created_at), gates or self.GATES)

    def test_a_pull_request_opened_after_the_verdicts_is_kept(self):
        d = self.decide("2026-11-01T08:19:00Z")
        self.assertEqual(d["action"], "keep")
        self.assertIn("opened after", d["why"])

    def test_one_second_after_is_kept_and_at_or_before_is_withdrawn(self):
        self.assertEqual(self.decide("2026-11-01T08:00:01Z")["action"], "keep")
        self.assertEqual(self.decide("2026-11-01T08:00:00Z")["action"], "withdraw")
        self.assertEqual(self.decide("2026-11-01T07:59:59Z")["action"], "withdraw")

    def test_an_offset_is_honored(self):
        # 09:10+01:00 is 08:10Z: after as_of. 08:50+01:00 is 07:50Z: before.
        self.assertEqual(self.decide("2026-11-01T09:10:00+01:00")["action"], "keep")
        self.assertEqual(self.decide("2026-11-01T08:50:00+01:00")["action"], "withdraw")

    def test_a_missing_or_unparseable_time_withdraws_nothing(self):
        for value in (None, "", "yesterday", 1730448000, "2026-11-01 07:00:00",
                      "2026-11-01T07:00:00", "2026-13-01T07:00:00Z"):
            with self.subTest(created_at=value):
                d = self.decide(value)
                self.assertEqual(d["action"], "keep")
                self.assertIn("unknown", d["why"])
        for as_of in (None, "", "2026-11-01", "20261301T000000Z"):
            with self.subTest(as_of=as_of):
                gates = {**self.GATES, "as_of": as_of}
                self.assertEqual(self.decide("2026-10-01T00:00:00Z", gates)["action"], "keep")

    def test_the_decision_is_pure(self):
        item, gates = pr(created_at="2026-11-01T08:19:00Z"), json.loads(json.dumps(self.GATES))
        before = (json.dumps(item, sort_keys=True), json.dumps(gates, sort_keys=True))
        rs.withdrawal_decision(item, gates)
        self.assertEqual(before, (json.dumps(item, sort_keys=True),
                                  json.dumps(gates, sort_keys=True)))

    def test_the_older_pass_leaves_the_newer_removal_open(self):
        gh = FakeGh()
        lines = rs.withdraw_stale(self.GATES, [pr(created_at="2026-11-01T08:19:00Z")],
                                  "skill", gh)
        self.assertEqual(gh.writes(), [])
        self.assertTrue(lines[0].startswith("kept #41"))


class ProposalSwitchDecisionTests(unittest.TestCase):
    """Round 1's minor 2: `retirement_mode: proposal` disarms every armed
    loop removal; a stale one is still withdrawn."""

    def test_a_supported_removal_is_disarmed_in_proposal_mode(self):
        for entry in (VERDICTS["retire+auto"], pending(retire("auto"))):
            with self.subTest(verdict=entry["verdict"]):
                d = rs.withdrawal_decision(pr(), doc({SKILL: entry}, mode="proposal"))
                self.assertEqual(d["action"], "disarm")
                self.assertIn("proposal", d["why"])

    def test_unknown_data_is_disarmed_not_withdrawn_in_proposal_mode(self):
        d = rs.withdrawal_decision(pr(), doc({}, mode="proposal"))
        self.assertEqual(d["action"], "disarm")

    def test_a_stale_removal_is_still_withdrawn_in_proposal_mode(self):
        d = rs.withdrawal_decision(pr(), doc({SKILL: VERDICTS["keep"]}, mode="proposal"))
        self.assertEqual(d["action"], "withdraw")

    def test_the_guidance_switch_is_its_own(self):
        gates = {**doc(guidance={SECTION: gretire()}),
                 "retirement_mode": "auto", "guidance_retirement_mode": "proposal"}
        gpr = pr(head=f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}", url=GUIDANCE_URL)
        self.assertEqual(rs.withdrawal_decision(gpr, gates, "guidance")["action"], "disarm")
        gates["guidance_retirement_mode"] = "auto"
        self.assertEqual(rs.withdrawal_decision(gpr, gates, "guidance")["action"], "keep")


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
                entry = gretire() if name == "retire+auto" else VERDICTS[name]
                self.assertEqual(self.decide({SECTION: entry})["action"], action)
        self.assertEqual(self.decide({"other": VERDICTS["keep"]})["action"], "keep")
        self.assertEqual(self.decide({SECTION: pending(gretire())})["action"], "keep")

    def test_no_guidance_block_withdraws_nothing(self):
        self.assertEqual(self.decide(None)["action"], "keep")

    def test_a_skill_branch_is_not_a_guidance_loop_pull_request(self):
        d = self.decide({SECTION: VERDICTS["keep"]}, head=f"{rs.BRANCH_PREFIX}{SECTION}")
        self.assertEqual(d["action"], "ignore")


class OneLineTests(unittest.TestCase):
    """Round 1's minor 5 (mutant M15): every verdict text is flattened."""

    def test_whitespace_is_flattened(self):
        self.assertEqual(rs._one_line("a cell\n  shows\tbenefit "), "a cell shows benefit")
        self.assertEqual(rs._one_line(None), "")

    def test_the_comment_quotes_the_reason_on_one_line(self):
        gh = FakeGh()
        entry = {**VERDICTS["keep"], "reason": "a cell\nshows\n\n  benefit"}
        rs.withdraw_stale(doc({SKILL: entry}), [pr()], "skill", gh)
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn("**keep**: a cell shows benefit.", body)


class FakeGh:
    """Answers the open pull request and issue listings, the state read and
    the auto-merge read-back; records every call. `armed` is the
    read-back's state, turned off by `--disable-auto` unless `stuck`."""

    def __init__(self, prs=(), armed=True, stuck=False, fail=None, issues=(), state="OPEN",
                 head="a" * 40, arms=True):
        self.prs, self.armed, self.stuck, self.fail = list(prs), armed, stuck, fail
        self.issues, self.state, self.head, self.arms = list(issues), state, head, arms
        self.calls = []

    def __call__(self, args, stdin=None):
        self.calls.append((list(args), stdin))
        if self.fail and args[:2] == self.fail:
            raise rs.RetireError(f"gh {args[0]} exited 1")
        if args[:2] == ["api", "--paginate"]:
            rows = self.issues if "/issues?" in args[2] else self.prs
            return "".join(json.dumps(p) + "\n" for p in rows)
        if args[:2] == ["pr", "merge"] and "--disable-auto" in args and not self.stuck:
            self.armed = False
        if args[:2] == ["pr", "merge"] and "--auto" in args and self.arms:
            self.armed = True
        if args[:2] == ["pr", "view"] and "headRefOid" in args:
            return self.head + "\n"
        if args[:2] == ["pr", "view"] and "state" in args:
            return self.state + "\n"
        if args[:2] == ["pr", "view"]:
            return ("MERGE" if self.armed else "") + "\n"
        return ""

    def writes(self):
        return [a for a, _ in self.calls if a[:2] != ["api", "--paginate"]
                and a[:2] != ["pr", "view"]]


def issue(number, subject=SKILL, state="open", author=rs.ISSUE_AUTHOR,
          marker=rs.ISSUE_MARKER):
    key = "section" if marker == rs.GUIDANCE_ISSUE_MARKER else "skill"
    return {"number": number, "body": marker.format(**{key: subject}) + "\nbody",
            "author": author, "state": state}


class WithdrawStaleTests(unittest.TestCase):
    """The thin layer: the calls, in order, with the fake."""

    def test_disarms_then_comments_then_closes_keeping_the_branch(self):
        gh = FakeGh()
        gates = doc({SKILL: VERDICTS["keep"]})
        lines = rs.withdraw_stale(gates, [pr()], "skill", gh,
                                  "https://github.com/Adam-S-Daniel/skills-evals/actions/runs/1")
        self.assertEqual(lines, ["withdrew #41: the verdict is keep, not retire; "
                                 "filed its retirement issue"])
        repo = rs.REGISTRY_REPO
        self.assertEqual(gh.writes()[:3], [
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

    def test_the_comment_documents_the_override_that_works(self):
        # Round 1's M4: reopening alone is withdrawn again; the override is
        # to remove agent-authored first.
        gh = FakeGh()
        rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn(f"remove the `{rs.AGENT_LABEL}` label first", body)
        self.assertIn("reopen", body)

    def test_a_withdrawal_files_the_subjects_retirement_issue(self):
        gh = FakeGh(issues=[issue(9, "other-skill"),
                            issue(8, author="Adam-S-Daniel")])
        rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh,
                          "https://github.com/Adam-S-Daniel/skills-evals/actions/runs/1")
        create = [(a, s) for a, s in gh.calls if a[:2] == ["issue", "create"]]
        self.assertEqual(len(create), 1)
        args, body = create[0]
        self.assertEqual(args[:4], ["issue", "create", "-R", rs.EVALS_REPO])
        self.assertIn(rs.ISSUE_MARKER.format(skill=SKILL), body)
        self.assertIn(SKILL_URL, body)
        self.assertIn("the verdict is keep, not retire", body)
        self.assertIn("actions/runs/1", body)
        self.assertIn(f"remove the `{rs.AGENT_LABEL}` label first", body)
        # The proposal path finds it again by its marker and author.
        self.assertIn(rs.ISSUE_MARKER.format(skill=SKILL), body.splitlines()[0])

    def test_a_withdrawal_comments_on_the_oldest_open_retirement_issue(self):
        # R2-6: a comment, never an edit, so the proposal's evidence stays;
        # mutant N04: the oldest open issue, not the newest.
        gh = FakeGh(issues=[issue(5, state="closed"), issue(9), issue(7)])
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        self.assertEqual([a[:3] for a, _ in gh.calls if a[0] == "issue"],
                         [["issue", "comment", "7"]])
        self.assertTrue(lines[0].endswith("commented on issue #7"))
        body = next(s for a, s in gh.calls if a[:2] == ["issue", "comment"])
        self.assertIn(SKILL_URL, body)
        self.assertIn("the verdict is keep, not retire", body)

    def test_withdrawal_issue_picks_the_oldest_open_issue(self):
        gh = FakeGh(issues=[issue(12), issue(4), issue(30), issue(2, state="closed")])
        item = {"subject": SKILL, "url": SKILL_URL, "verdict": "keep", "reason": "r",
                "why": "w"}
        out = rs.withdrawal_issue(item, doc({}), "skill", gh, None)
        self.assertEqual((out["action"], out["issue"]), ("update-issue", 4))

    def test_the_issue_goes_through_the_jobs_token_not_the_app_token(self):
        app, job = FakeGh(), FakeGh()
        rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", app, gh=job)
        self.assertFalse(any(a[0] == "issue" for a, _ in app.calls))
        self.assertTrue(any(a[:2] == ["issue", "create"] for a, _ in job.calls))
        self.assertFalse(any(a[0] == "pr" for a, _ in job.calls))

    def test_a_guidance_withdrawal_files_the_sections_issue(self):
        gh = FakeGh(issues=[issue(3, SECTION, marker=rs.GUIDANCE_ISSUE_MARKER)])
        gpr = pr(head=f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}", number=42, url=GUIDANCE_URL)
        rs.withdraw_stale(doc(guidance={SECTION: VERDICTS["insufficient"]}), [gpr],
                          "guidance", gh)
        self.assertFalse(any(a[:2] == ["issue", "edit"] for a, _ in gh.calls))
        comment = [(a, s) for a, s in gh.calls if a[:2] == ["issue", "comment"]]
        self.assertEqual(comment[0][0][2], "3")
        self.assertIn(GUIDANCE_URL, comment[0][1])

    def test_a_new_retirement_issue_still_carries_its_marker_in_the_body(self):
        gh = FakeGh()
        rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        body = next(s for a, s in gh.calls if a[:2] == ["issue", "create"])
        self.assertTrue(body.startswith(rs.ISSUE_MARKER.format(skill=SKILL) + "\n"))

    def test_the_open_removal_notice_is_commented_on_and_closed(self):
        # R2-3: the #557 notice no longer says a removal is in flight.
        notice = {"number": 6, "body": rs.SKILL_NOTICE_MARKER.format(skill=SKILL) + "\nx",
                  "author": rs.ISSUE_AUTHOR, "state": "open"}
        other = {**notice, "number": 8,
                 "body": rs.SKILL_NOTICE_MARKER.format(skill="other-skill")}
        gh = FakeGh(issues=[notice, other, {**notice, "number": 3, "state": "closed"},
                            {**notice, "number": 11, "author": "Adam-S-Daniel"}])
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        self.assertEqual([a for a in gh.writes() if a[0] == "issue"], [
            ["issue", "create", "-R", rs.EVALS_REPO, "--title",
             f"Retire skill {SKILL}: automatic removal withdrawn (#70)", "--body-file", "-"],
            ["issue", "close", "6", "-R", rs.EVALS_REPO, "--reason", "not planned"],
            ["issue", "comment", "6", "-R", rs.EVALS_REPO, "--body-file", "-"]])
        body = next(s for a, s in gh.calls if a[:3] == ["issue", "comment", "6"])
        self.assertIn("Removal withdrawn", body)
        self.assertIn(SKILL_URL, body)
        self.assertTrue(body.rstrip("\n").endswith(rs.AGENT_MARKER.strip()))
        self.assertTrue(lines[0].endswith("closed its removal notice #6"))

    def test_the_guidance_notice_is_closed_too(self):
        notice = {"number": 6, "body": rs.GUIDANCE_NOTICE_MARKER.format(section=SECTION),
                  "author": rs.ISSUE_AUTHOR, "state": "open"}
        gh = FakeGh(issues=[notice])
        gpr = pr(head=f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}", number=42, url=GUIDANCE_URL)
        rs.withdraw_stale(doc(guidance={SECTION: VERDICTS["insufficient"]}), [gpr],
                          "guidance", gh)
        self.assertIn(["issue", "close", "6", "-R", rs.EVALS_REPO, "--reason", "not planned"],
                      gh.writes())

    def test_a_failed_notice_close_does_not_stop_the_withdrawal(self):
        notice = {"number": 6, "body": rs.SKILL_NOTICE_MARKER.format(skill=SKILL),
                  "author": rs.ISSUE_AUTHOR, "state": "open"}
        gh = FakeGh(issues=[notice], fail=["issue", "close"])
        second = pr(head=f"{rs.BRANCH_PREFIX}other-skill", number=43,
                    url=f"https://github.com/{rs.REGISTRY_REPO}/pull/43")
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["keep"], "other-skill": VERDICTS["keep"]}),
                                  [pr(), second], "skill", gh)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith("could not close its removal notice"))
        self.assertTrue(lines[1].startswith("withdrew #43"))
        closes = [a for a in gh.writes() if a[:2] == ["pr", "close"]]
        self.assertEqual(len(closes), 2)

    def test_a_pull_request_no_longer_open_is_skipped(self):
        gh = FakeGh(state="CLOSED")
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        self.assertEqual(gh.writes(), [])
        self.assertEqual(lines, ["skipped #41: it is no longer open"])

    def test_an_unarmed_pull_request_is_commented_and_closed_without_a_disable(self):
        gh = FakeGh(armed=False)
        rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        self.assertEqual([a[1] for a in gh.writes()], ["comment", "close", "create"])

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

    def test_a_reopened_pull_request_without_the_label_gets_no_write(self):
        gh = FakeGh()
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["insufficient"]}), [pr(labels=())],
                                  "skill", gh)
        self.assertEqual((gh.calls, lines),
                         ([], ["no open removal pull request to withdraw"]))

    def test_a_withdrawal_with_a_foreign_url_is_refused(self):
        gh = FakeGh()
        bad = pr(url=f"https://github.com/{rs.GUIDANCE_REPO}/pull/41")
        for gates in (doc({SKILL: VERDICTS["keep"]}),
                      doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal")):
            with self.assertRaises(rs.RetireError):
                rs.withdraw_stale(gates, [bad], "skill", gh)
        self.assertEqual(gh.writes(), [])

    def test_the_guidance_pass_writes_to_agent_guidance(self):
        gh = FakeGh()
        gpr = pr(head=f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}", number=42, url=GUIDANCE_URL)
        rs.withdraw_stale(doc(guidance={SECTION: VERDICTS["insufficient"]}), [gpr],
                          "guidance", gh)
        prw = [a for a in gh.writes() if a[0] == "pr"]
        self.assertEqual([a[-1] if a[1] == "close" else a[1] for a in prw],
                         ["merge", "comment", rs.GUIDANCE_REPO])
        self.assertTrue(all(rs.GUIDANCE_REPO in a for a in prw))


class DisarmTests(unittest.TestCase):
    """Round 1's minor 2: the proposal switch disarms, leaves the pull
    request open and comments once."""

    def gates(self):
        return doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal")

    def test_an_armed_removal_is_disarmed_left_open_and_commented(self):
        gh = FakeGh()
        lines = rs.withdraw_stale(self.gates(), [pr()], "skill", gh)
        self.assertEqual(gh.writes(), [
            ["pr", "merge", SKILL_URL, "-R", rs.REGISTRY_REPO, "--disable-auto"],
            ["pr", "edit", SKILL_URL, "-R", rs.REGISTRY_REPO, "--add-label",
             rs.DISARMED_LABEL],
            ["pr", "comment", SKILL_URL, "-R", rs.REGISTRY_REPO, "--body-file", "-"]])
        self.assertFalse(gh.armed)
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn(rs.DISARMED_MARKER.format(subject=SKILL), body)
        self.assertTrue(body.rstrip("\n").endswith(rs.AGENT_MARKER))
        self.assertTrue(lines[0].startswith("disarmed #41"))

    def test_a_disarmed_removal_is_not_commented_again(self):
        gh = FakeGh()
        rs.withdraw_stale(self.gates(), [pr()], "skill", gh)
        rs.withdraw_stale(self.gates(), [pr(labels=(rs.AGENT_LABEL, rs.DISARMED_LABEL))],
                          "skill", gh)
        self.assertEqual([a[1] for a in gh.writes()], ["merge", "edit", "comment"])

    def test_a_disarm_that_does_not_hold_refuses(self):
        gh = FakeGh(stuck=True)
        with self.assertRaises(rs.RetireError):
            rs.withdraw_stale(self.gates(), [pr()], "skill", gh)
        self.assertEqual([a[1] for a in gh.writes()], ["merge"])


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
        self.assertEqual([a[1] for a in gh.writes()], ["merge", "comment", "close", "create"])

    def test_the_listing_reads_the_author(self):
        _, _, _, gh = self.run_main(doc({SKILL: VERDICTS["keep"]}))
        jq = next(a for a, _ in gh.calls if a[0] == "api" and "/pulls?" in a[2])[-1]
        self.assertIn("author: .user.login", jq)
        self.assertIn("created_at: .created_at", jq)

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

    def test_the_schedule_and_an_ingest_act_and_a_dispatch_does_not(self):
        for event, want in (("schedule", 0), ("workflow_run", 0),
                            ("workflow_dispatch", 2), ("push", 2), (None, 2)):
            with self.subTest(event=event):
                env = {**AUTO_ENV, "GITHUB_EVENT_NAME": event}
                code, _, _, gh = self.run_main(doc({SKILL: VERDICTS["keep"]}), env=env)
                self.assertEqual(code, want)
                if want:
                    self.assertEqual(gh.calls, [])

    def test_the_act_path_still_needs_the_schedule(self):
        path = self.tmp / "gates.json"
        path.write_text(json.dumps(doc({SKILL: VERDICTS["keep"]})))
        err = io.StringIO()
        with redirect_stderr(err):
            code = rs.main(["--gates", str(path)], env={**AUTO_ENV,
                           "GITHUB_EVENT_NAME": "workflow_run"}, gh=FakeGh(), out=io.StringIO())
        self.assertEqual(code, 2)
        self.assertIn("refusing", err.getvalue())

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
        self.assertIn(["gh", "pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO],
                      plan["would_run"])

    def test_a_failed_call_exits_2_with_its_exit_code_only(self):
        gh = FakeGh([pr()], fail=["pr", "close"])
        code, _, err, _ = self.run_main(doc({SKILL: VERDICTS["keep"]}), gh=gh)
        self.assertEqual(code, 2)
        self.assertEqual(err.strip(), "retire_skill: gh pr exited 1")


class RefreshAllowedTests(unittest.TestCase):
    """Round 1's M2: loop-pr-refresh.yml brings a removal up to date only
    while the withdrawal would keep it in auto mode."""

    def test_only_a_supported_removal_in_auto_mode_is_refreshed(self):
        head = f"{rs.BRANCH_PREFIX}{SKILL}"
        cases = (("retire+auto", doc({SKILL: VERDICTS["retire+auto"]}), True),
                 ("retire-pending", doc({SKILL: pending(retire("auto"))}), True),
                 ("keep", doc({SKILL: VERDICTS["keep"]}), False),
                 ("insufficient", doc({SKILL: VERDICTS["insufficient"]}), False),
                 ("retire+proposal", doc({SKILL: VERDICTS["retire+proposal"]}), False),
                 ("proposal mode", doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal"),
                  False),
                 ("absent", doc({}), False), ("unknown", None, False))
        for name, gates, want in cases:
            with self.subTest(name):
                self.assertIs(rs.refresh_allowed(gates, head)[0], want)

    def test_guidance_heads_read_the_guidance_block(self):
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        self.assertTrue(rs.refresh_allowed(doc(guidance={SECTION: gretire()}), head)[0])
        self.assertFalse(rs.refresh_allowed(
            doc(guidance={SECTION: VERDICTS["keep"]}), head)[0])
        self.assertFalse(rs.refresh_allowed(doc({SECTION: VERDICTS["retire+auto"]}), head)[0])

    def test_other_loop_heads_are_always_refreshed(self):
        for head in ("eval-improve/x", "draft-skill/x", "draft-skill-fixtures/x"):
            with self.subTest(head=head):
                self.assertTrue(rs.refresh_allowed(None, head)[0])

    def test_a_removal_head_naming_no_subject_is_not_refreshed(self):
        self.assertFalse(rs.refresh_allowed(doc({}), f"{rs.BRANCH_PREFIX}Bad Name")[0])


class RemovalCheckCliTests(unittest.TestCase):
    """refresh_loop_prs.py removal-check, the call the workflow makes."""

    def run_check(self, gates, head):
        import refresh_loop_prs as rlp
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "latest.json"
            if gates is not None:
                path.write_text(json.dumps(gates))
            out = io.StringIO()
            from contextlib import redirect_stdout
            with redirect_stdout(out):
                code = rlp.main(["removal-check", "--gates", str(path), "--head", head])
        return code, out.getvalue()

    def test_exit_codes(self):
        head = f"{rs.BRANCH_PREFIX}{SKILL}"
        self.assertEqual(self.run_check(doc({SKILL: VERDICTS["retire+auto"]}), head)[0], 0)
        code, out = self.run_check(doc({SKILL: VERDICTS["keep"]}), head)
        self.assertEqual(code, 4)
        self.assertIn("outcome=skip", out)
        self.assertIn("reason=the verdict is keep, not retire", out)
        self.assertEqual(self.run_check(None, head)[0], 4)
        self.assertEqual(self.run_check(None, "eval-improve/x")[0], 0)


class GuidanceDecidedTests(unittest.TestCase):
    """A withdrawn (closed) retire-guidance/ pull request decides its section,
    as a closed retire-skill/ one decides a skill: no removal reopens it."""

    def gates(self):
        cells = [{"fixture": "fx", "model": m, "class": "no-benefit"} for m in MODELS] + [
            {"fixture": "fy", "model": m, "class": "no-benefit"} for m in MODELS]
        return {**doc(), "guidance_retirement_mode": "auto",
                "guidance": {SECTION: {"verdict": "retire", "removal": "auto",
                                       "reason": "every cell shows no benefit",
                                       "cells": cells,
                                       # A finished section-alone pair, so the
                                       # retire is not held to a proposal
                                       # (#738, gates.alone_unfinished).
                                       "alone": {"verdict": "retire", "cells": cells}}}}

    def plan(self, closed_head):
        closed = {"number": 42, "head": closed_head, "url": GUIDANCE_URL}

        def gh(args, stdin=None):
            if "state=closed" in args[2]:
                return json.dumps(closed) + "\n"
            return ""

        return rs.guidance_plan(self.gates(), None, gh, allowed=("proposal", "auto"))

    def test_a_closed_removal_pull_request_decides_the_section(self):
        plan = self.plan(f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}")
        self.assertEqual(plan["action"], "none")
        self.assertIn("already decided", plan["reason"])

    def test_a_closed_pull_request_from_another_head_does_not(self):
        # Round 1's minor 5 (mutant M14): the API's head= filter is not
        # trusted alone; `retire-guidance/<section>-extra` is another section.
        with self.assertRaises(rs.RetireError) as ctx:
            self.plan(f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}-extra")
        self.assertIn("checkout", str(ctx.exception))


def _steps_after(steps, name):
    i = next(i for i, s in enumerate(steps) if s.get("name") == name)
    return steps[i + 1:]


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

    def test_each_pass_withdraws_in_its_own_step_before_it_acts(self):
        names = [s.get("name") for s in self.steps]
        for withdraw_name, act_name, token, guidance in (
                ("Withdraw stale skill removal pull requests",
                 "Act on the skill retirement verdict", "app-token", False),
                ("Withdraw stale guidance removal pull requests",
                 "Act on the guidance retirement verdict", "guidance-token", True)):
            withdraw, act = self.step(withdraw_name), self.step(act_name)
            with self.subTest(step=withdraw_name):
                self.assertLess(names.index(withdraw_name), names.index(act_name))
                (wcmd,), (acmd,) = self.commands(withdraw), self.commands(act)
                self.assertIn("--withdraw-stale", wcmd)
                self.assertNotIn("--withdraw-stale", acmd)
                self.assertNotIn("--dry-run", wcmd)
                self.assertIn('--gates "$RUNNER_TEMP/gates/latest.json"', wcmd)
                self.assertEqual("--target guidance" in wcmd, guidance)
                self.assertEqual("--target guidance" in acmd, guidance)
                for step in (withdraw, act):
                    self.assertTrue(step["run"].lstrip().startswith("set -euo pipefail"))
                    self.assertNotIn("continue-on-error", step)
                    self.assertEqual(step["env"], {
                        "GH_TOKEN": "${{ github.token }}",
                        "REGISTRY_TOKEN": f"${{{{ steps.{token}.outputs.token }}}}"})

    def test_a_failed_step_never_skips_a_later_pass(self):
        # Round 1's M3: every step after the verdicts runs unless the run was
        # cancelled, so a failed skill withdrawal still lets the skill act
        # step and both guidance steps run; the failed step still fails the job.
        later = _steps_after(self.steps, "Upload the verdicts")
        self.assertEqual(len(later), 7)
        for step in later:
            with self.subTest(step=step.get("name")):
                cond = step.get("if", "")
                self.assertTrue(cond.startswith("${{ !cancelled() && "), cond)
                self.assertIn("steps.verdicts.outcome == 'success'", cond)
                self.assertNotIn("failure()", cond)
                self.assertNotIn("always()", cond)
        for mint in ("app-token", "guidance-token"):
            step = next(s for s in later if s.get("id") == mint)
            self.assertIn("steps.credential.outputs.present == 'true'", step["if"])
        self.assertEqual(self.step("Compute the retirement verdicts")["id"], "verdicts")


class RefreshWorkflowTests(unittest.TestCase):
    """loop-pr-refresh.yml: the withdrawal after every ingest (round 1's M2)."""

    def setUp(self):
        self.doc = yaml.safe_load((ROOT / ".github/workflows/loop-pr-refresh.yml").read_text())
        self.jobs = self.doc["jobs"]

    def test_the_withdrawal_runs_after_every_ingest_before_the_refresh(self):
        on = self.doc[True] if True in self.doc else self.doc["on"]
        self.assertEqual(on["workflow_run"], {"workflows": ["Ingest routine eval results"],
                                              "types": ["completed"]})
        self.assertEqual(self.jobs["refresh"]["needs"], "withdraw")
        self.assertIn("!cancelled()", self.jobs["refresh"]["if"])

    def test_one_withdrawal_pass_at_a_time(self):
        # R2-2: the withdraw job alone has a group, never cancelling a pass
        # in progress; the workflow and the refresh have none (#623).
        self.assertNotIn("concurrency", self.doc)
        self.assertNotIn("concurrency", self.jobs["refresh"])
        self.assertEqual(self.jobs["withdraw"]["concurrency"],
                         {"group": "loop-pr-refresh-withdraw", "cancel-in-progress": False})
        # Not shared with the scheduled retirement job (its pending pass
        # would be cancelled) and not a group any other workflow uses.
        groups = []
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            if path.name == "loop-pr-refresh.yml":
                continue
            wf = yaml.safe_load(path.read_text())
            for node in [wf, *(wf.get("jobs") or {}).values()]:
                c = node.get("concurrency") if isinstance(node, dict) else None
                groups.append(c.get("group") if isinstance(c, dict) else c)
        self.assertNotIn("loop-pr-refresh-withdraw", groups)

    def test_the_workflow_has_no_duplicate_keys(self):
        # GitHub refuses a duplicated key; PyYAML would keep the last one and
        # hide, say, a second `concurrency` on a job.
        class Strict(yaml.SafeLoader):
            pass

        def mapping(loader, node, deep=False):
            keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
            dupes = {k for k in keys if keys.count(k) > 1}
            if dupes:
                raise AssertionError(f"duplicate keys {sorted(map(str, dupes))} "
                                     f"at line {node.start_mark.line + 1}")
            return yaml.SafeLoader.construct_mapping(loader, node, deep)

        Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
        yaml.load((ROOT / ".github/workflows/loop-pr-refresh.yml").read_text(), Loader=Strict)

    def test_each_withdrawal_pass_is_its_own_step_and_runs_unless_cancelled(self):
        steps = self.jobs["withdraw"]["steps"]
        withdraws = [s for s in steps if "--withdraw-stale" in s.get("run", "")]
        self.assertEqual([("--target guidance" in s["run"]) for s in withdraws],
                         [False, True])
        for step in _steps_after(steps, "Upload the verdicts"):
            with self.subTest(step=step.get("name")):
                self.assertTrue(step["if"].startswith("${{ !cancelled() && "))
                self.assertIn("steps.verdicts.outcome == 'success'", step["if"])
                self.assertIn("github.event_name == 'workflow_run'", step["if"])
        tokens = {s["id"]: s for s in steps if s.get("id") in ("app-token", "guidance-token")}
        self.assertEqual(tokens["app-token"]["with"]["repositories"], "adam-agentskills")
        self.assertEqual(tokens["guidance-token"]["with"]["repositories"], "_agent-guidance")
        for s in tokens.values():
            self.assertIs(s["continue-on-error"], True)
            # contents: write for the re-arm alone (R2-5), as the retirement
            # job's token arms a removal; nothing else.
            self.assertEqual({k: v for k, v in s["with"].items()
                              if k.startswith("permission-")},
                             {"permission-pull-requests": "write",
                              "permission-contents": "write"})
        for s, token in zip(withdraws, ("app-token", "guidance-token")):
            self.assertEqual(s["env"]["REGISTRY_TOKEN"],
                             f"${{{{ steps.{token}.outputs.token }}}}")
            self.assertEqual(s["env"]["GH_TOKEN"], "${{ github.token }}")
        self.assertEqual(self.jobs["withdraw"]["permissions"],
                         {"contents": "read", "issues": "write"})

    def test_the_verdicts_are_computed_as_the_retirement_job_computes_them(self):
        compute = next(s for s in self.jobs["withdraw"]["steps"]
                       if "scripts/compute_gates.py" in s.get("run", ""))
        coverage = yaml.safe_load((ROOT / ".github/workflows/skill-coverage.yml").read_text())
        theirs = next(s for s in coverage["jobs"]["retirement"]["steps"]
                      if "scripts/compute_gates.py" in s.get("run", ""))
        self.assertEqual(compute["run"], theirs["run"])

    def test_the_refresh_checks_every_removal_head_before_merging(self):
        steps = self.jobs["refresh"]["steps"]
        run = next(s for s in steps if "refresh_repo" in s.get("run", ""))
        self.assertIn("retire-skill/*|retire-guidance/*)", run["run"])
        self.assertIn('removal-check --gates "$GATES" --head "$ref"', run["run"])
        self.assertLess(run["run"].index("removal-check"), run["run"].index(" merge --repo"))
        self.assertEqual(run["env"]["GATES"], "${{ runner.temp }}/gates/latest.json")
        download = next(s for s in steps if str(s.get("uses", "")).startswith(
            "actions/download-artifact@"))
        self.assertIs(download["continue-on-error"], True)
        self.assertEqual(download["with"]["name"], "gates")



FAKE_GH = """#!/bin/sh
# The open pull request listing, then `.mergeable` (false: a conflict).
printf 'gh %s\\n' "$*" >> "$CALLS"
case "$2" in
  *'/pulls?state=open'*)
    printf '[{"number": 41, "head": {"ref": "retire-skill/example-skill", "repo": {"full_name": "Adam-S-Daniel/adam-agentskills"}}, "base": {"ref": "main"}}]\\n' ;;
  */pulls/41) echo false ;;
esac
"""

FAKE_PYTHON = """#!/bin/sh
# `python3 "$SCRIPT" <subcommand> ...`: removal-check exits $CHECK_RC.
printf 'python3 %s\\n' "$2" >> "$CALLS"
case "$2" in
  removal-check) echo "reason=invented"; exit "$CHECK_RC" ;;
  merge) echo "outcome=up-to-date"; exit 0 ;;
esac
exit 9
"""

FAKE_GIT = """#!/bin/sh
printf 'git %s\\n' "$*" >> "$CALLS"
case "$*" in *rev-parse*) echo 0123456789abcdef0123456789abcdef01234567 ;; esac
exit 0
"""


class RefreshGateExecutionTests(unittest.TestCase):
    """R2-8 (mutant N12): the refresh step's shell gate on `removal-check`
    is executed, not read. The step's `run:` block comes from the parsed
    workflow and runs under bash with fake `gh`, `git` and `python3` on
    PATH: no network, no clock."""

    def setUp(self):
        wf = yaml.safe_load((ROOT / ".github/workflows/loop-pr-refresh.yml").read_text())
        self.run_block = next(s["run"] for s in wf["jobs"]["refresh"]["steps"]
                              if "refresh_repo" in s.get("run", ""))
        self.tmp = Path(tempfile.mkdtemp())
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for name, text in (("gh", FAKE_GH), ("python3", FAKE_PYTHON), ("git", FAKE_GIT)):
            (self.bin / name).write_text(text)
            (self.bin / name).chmod(0o755)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def run_step(self, check_rc):
        calls, summary = self.tmp / "calls.log", self.tmp / "summary.md"
        for f in (calls, summary):
            f.write_text("")
        env = {"PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
               "HOME": str(self.tmp), "CALLS": str(calls), "CHECK_RC": str(check_rc),
               "GITHUB_STEP_SUMMARY": str(summary), "RUNNER_TEMP": str(self.tmp),
               "GH_TOKEN": "job-token-invented", "REGISTRY_TOKEN": "registry-token-invented",
               "ROSTER_TOKEN": "", "SELF_REPO": "Adam-S-Daniel/skills-evals",
               "SCRIPT": str(self.tmp / "refresh_loop_prs.py"),
               "GATES": str(self.tmp / "gates.json")}
        proc = subprocess.run(["bash", "-c", self.run_block], env=env, capture_output=True,
                              text=True, timeout=60, check=False)
        return proc, calls.read_text().splitlines(), summary.read_text()

    def test_a_removal_check_failure_skips_the_merge(self):
        proc, calls, summary = self.run_step(4)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("python3 removal-check", calls)
        self.assertNotIn("python3 merge", calls)
        self.assertFalse(any(c.startswith("git ") for c in calls), calls)
        self.assertFalse(any(c.endswith("/pulls/41 --jq .mergeable") for c in calls), calls)
        self.assertIn("removal not refreshed", summary)

    def test_a_supported_removal_is_merged(self):
        # The positive control: the same harness reaches the merge, so the
        # test above fails if the gate stops gating.
        proc, calls, summary = self.run_step(0)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([c for c in calls if c.startswith("python3 ")],
                         ["python3 removal-check", "python3 merge"])
        self.assertIn("already up to date", summary)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# PR #724 round 3.

#: A roster model the gates have no run on yet: every cell on it is
#: `missing` (harness/gates.py `retirement`, "no run on this model").
NEW_MODEL = "model-c"


def roster_added(entry):
    """`entry` (a `retire` over MODELS) after a roster model is added: its
    cells plus a `missing` cell per fixture on NEW_MODEL, and the verdict
    harness/gates.py `_verdict` gives those cells."""
    cells = entry["cells"] + [{"fixture": f, "model": NEW_MODEL, "class": "missing",
                               "reason": "no run on this model"} for f in ("fx-a", "fx-b")]
    out = {k: v for k, v in entry.items() if k not in ("removal", "removal_reason")}
    return {**out, **gates_mod._verdict(cells, True), "cells": cells}


import gates as gates_mod  # noqa: E402


def unfinished_alone(removal="proposal", alone_cells=None):
    """A section `retire` whose section-alone pair is unfinished, as
    harness/gates.py `guidance_verdict` writes it (removal `proposal` with
    ALONE_UNFINISHED_REASON), or as an older document said it (`auto`)."""
    entry = gretire()
    entry["alone"] = {"verdict": "insufficient",
                      "cells": alone_cells if alone_cells is not None
                      else [cell("fx-a", m) for m in MODELS]
                      + [cell("fx-a", NEW_MODEL, "missing")]}
    if removal == "proposal":
        entry.update(removal="proposal", removal_reason=gates_mod.ALONE_UNFINISHED_REASON)
    return entry


def gpr(**kw):
    kw.setdefault("head", f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}")
    kw.setdefault("url", GUIDANCE_URL)
    kw.setdefault("number", 42)
    return pr(**kw)


class IncompleteDataTests(unittest.TestCase):
    """Round 3's M1: undecided data never withdraws. An `insufficient`
    verdict over a `missing` or `insufficient` cell, or a section `retire`
    lowered only by its unfinished alone pair, is `incomplete`: disarmed in
    both modes, never refreshed."""

    def test_the_roster_fixture_is_what_the_gates_compute(self):
        entry = roster_added(retire())
        self.assertEqual(entry["verdict"], "insufficient")
        self.assertIn("missing", {c["class"] for c in entry["cells"]})
        self.assertNotIn("removal", entry)

    def test_a_roster_model_added_disarms_open_skill_and_guidance_removals(self):
        # The sim-equivalent of sim_r3_8: both pull requests are disarmed,
        # labeled and commented, and neither is closed or withdrawn.
        for mode in ("auto", "proposal"):
            with self.subTest(mode=mode):
                gates = doc({SKILL: roster_added(retire())},
                            guidance={SECTION: roster_added(gretire())}, mode=mode)
                for target, item, url, repo in (
                        ("skill", pr(), SKILL_URL, rs.REGISTRY_REPO),
                        ("guidance", gpr(), GUIDANCE_URL, rs.GUIDANCE_REPO)):
                    d = rs.withdrawal_decision(item, gates, target)
                    self.assertEqual((d["action"], d["cause"]), ("disarm", "incomplete"))
                    self.assertIn("missing", d["why"])
                    self.assertFalse(rs.refresh_allowed(gates, item["head"])[0])
                    gh = FakeGh()
                    lines = rs.withdraw_stale(gates, [item], target, gh)
                    self.assertEqual(gh.writes(), [
                        ["pr", "merge", url, "-R", repo, "--disable-auto"],
                        ["pr", "edit", url, "-R", repo, "--add-label", rs.DISARMED_LABEL],
                        ["pr", "comment", url, "-R", repo, "--body-file", "-"]])
                    self.assertFalse(gh.armed)
                    self.assertTrue(lines[0].startswith(f"disarmed #{item['number']}"))

    def test_an_insufficient_cell_is_incomplete_too(self):
        entry = {"verdict": "insufficient", "reason": "a cell is insufficient or missing",
                 "cells": [cell("fx-a", "model-a", "insufficient"), cell("fx-b", "model-a")]}
        self.assertEqual(rs.removal_support(doc(), entry)[0], "incomplete")
        self.assertEqual(rs.withdrawal_decision(pr(), doc({SKILL: entry}))["action"],
                         "disarm")

    def test_an_insufficient_verdict_with_no_unfinished_cell_is_stale(self):
        for cells in ([], [cell("fx-a", "model-a", "paused")],
                      [cell("fx-a", "model-a", "cannot-discriminate")]):
            with self.subTest(cells=cells):
                entry = {"verdict": "insufficient", "reason": "no fixture on main",
                         "cells": cells}
                self.assertEqual(rs.removal_support(doc(), entry)[0], "stale")

    def test_only_an_insufficient_verdict_reads_its_cells(self):
        # harness/gates.py `_verdict` makes any verdict over a missing or
        # insufficient cell `insufficient` (unless one shows benefit), so
        # another verdict beside one is not read as incomplete.
        for verdict in ("cannot-discriminate", "ceiling", "shorten-or-merge"):
            with self.subTest(verdict=verdict):
                entry = {"verdict": verdict, "reason": "invented",
                         "cells": [cell("fx-a", NEW_MODEL, "missing"),
                                   cell("fx-b", "model-a", "insufficient")]}
                self.assertEqual(rs.removal_support(doc(), entry)[0], "stale")

    def test_a_decided_verdict_beside_a_missing_cell_is_not_incomplete(self):
        entry = {"verdict": "keep", "reason": "a cell shows benefit",
                 "cells": [cell("fx-a", "model-a", "benefit"),
                           cell("fx-a", NEW_MODEL, "missing")]}
        self.assertEqual(rs.withdrawal_decision(pr(), doc({SKILL: entry}))["action"],
                         "withdraw")

    def test_malformed_cells_are_unknown(self):
        entry = {"verdict": "insufficient", "reason": "x", "cells": {"class": "missing"}}
        self.assertEqual(rs.removal_support(doc(), entry)[0], "unknown")
        self.assertEqual(rs.withdrawal_decision(pr(), doc({SKILL: entry}))["action"], "keep")

    def test_an_unfinished_alone_pair_disarms_in_both_modes(self):
        cases = {"alone cell missing": unfinished_alone(),
                 "removal still auto": unfinished_alone("auto"),
                 "no alone cell yet": unfinished_alone(alone_cells=[]),
                 "alone cell insufficient": unfinished_alone(
                     alone_cells=[cell("fx-a", m, "insufficient") for m in MODELS])}
        for name, entry in cases.items():
            for mode in ("auto", "proposal"):
                with self.subTest(name, mode=mode):
                    gates = doc(guidance={SECTION: entry}, mode=mode)
                    state, why = rs.removal_support(gates, entry, "guidance")
                    self.assertEqual((state, why),
                                     ("incomplete", gates_mod.ALONE_UNFINISHED_REASON))
                    d = rs.withdrawal_decision(gpr(), gates, "guidance")
                    self.assertEqual((d["action"], d["cause"]), ("disarm", "incomplete"))
                    self.assertFalse(rs.refresh_allowed(gates, gpr()["head"])[0])

    def test_the_guidance_target_rechecks_the_alone_pair(self):
        # Round 3's side note: a document saying `auto` over an unfinished
        # alone pair is not trusted; the skill target has no alone pair.
        entry = unfinished_alone("auto")
        gates = doc(guidance={SECTION: entry})
        self.assertEqual(rs.removal_support(gates, entry, "skill")[0], "supported")
        self.assertEqual(rs.removal_support(gates, entry, "guidance")[0], "incomplete")
        self.assertNotEqual(rs.refresh_allowed(gates, gpr()["head"]),
                            (True, "the verdict is still retire with an automatic removal"))

    def test_a_finished_alone_pair_is_supported(self):
        gates = doc(guidance={SECTION: gretire()})
        self.assertEqual(rs.removal_support(gates, gretire(), "guidance")[0], "supported")
        self.assertEqual(rs.withdrawal_decision(gpr(), gates, "guidance")["action"], "keep")
        self.assertTrue(rs.refresh_allowed(gates, gpr()["head"])[0])

    def test_a_retire_lowered_for_another_reason_too_is_stale(self):
        # Only a retire whose ONE lowering is the alone pair is incomplete:
        # cells that allow only a proposal stay stale, whatever the reason.
        for entry in ({**unfinished_alone(), "cells": retire(
                          classes=("no-benefit", "no-clear-effect"))["cells"]},
                      {**unfinished_alone(), "cells": retire(
                          classes=("no-benefit", "ceiling"))["cells"]}):
            with self.subTest(classes=sorted({c["class"] for c in entry["cells"]})):
                gates = doc(guidance={SECTION: entry})
                self.assertEqual(rs.removal_support(gates, entry, "guidance")[0], "stale")
                self.assertEqual(rs.withdrawal_decision(gpr(), gates, "guidance")["action"],
                                 "withdraw")
        other = {**gretire("proposal"), "removal_reason": "invented removal reason"}
        self.assertEqual(rs.removal_support(doc(), other, "guidance")[0], "stale")

    def test_a_skill_with_the_alone_reason_is_stale(self):
        # The alone pair is a section's only; a skill's proposal is stale.
        entry = {**retire("proposal"), "removal_reason": gates_mod.ALONE_UNFINISHED_REASON}
        self.assertEqual(rs.removal_support(doc(), entry)[0], "stale")

    def test_the_incomplete_disarm_comment(self):
        gh = FakeGh()
        rs.withdraw_stale(doc({SKILL: roster_added(retire())}), [pr()], "skill", gh)
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn(rs.DISARMED_MARKER.format(subject=SKILL), body)
        self.assertIn("not complete yet", body)
        self.assertIn(rs.DISARMED_LABEL, body)
        self.assertNotIn("is `proposal`", body)
        self.assertTrue(body.rstrip("\n").endswith(rs.AGENT_MARKER.strip()))
        gh = FakeGh()
        rs.withdraw_stale(doc({SKILL: retire()}, mode="proposal"), [pr()], "skill", gh)
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn("is `proposal`", body)

    def test_an_unarmed_incomplete_removal_gets_no_write(self):
        # Auto-merge already off (a person, or an earlier pass): no label,
        # so a person's choice is never turned into a re-arm.
        gh = FakeGh(armed=False)
        lines = rs.withdraw_stale(doc({SKILL: roster_added(retire())}), [pr()], "skill", gh)
        self.assertEqual(gh.writes(), [])
        self.assertTrue(lines[0].startswith("left #41 open and disarmed"))

    def test_incomplete_never_withdraws_whatever_the_times(self):
        gates = doc({SKILL: roster_added(retire())}, as_of="20261201T000000Z")
        for kw in ({}, {"created_at": None}, {"created_at": "2020-01-01T00:00:00Z"}):
            with self.subTest(**kw):
                self.assertEqual(rs.withdrawal_decision(pr(**kw), gates)["action"], "disarm")


class RearmTests(unittest.TestCase):
    """R2-5: a removal the loop disarmed (DISARMED_LABEL) is armed again in
    `auto` mode once its verdict supports it; one a person disarmed is not."""

    LABELS = (rs.AGENT_LABEL, rs.DISARMED_LABEL)

    def test_the_decision(self):
        auto, proposal = doc({SKILL: retire()}), doc({SKILL: retire()}, mode="proposal")
        cases = ((pr(labels=self.LABELS), auto, "rearm"),
                 (pr(), auto, "keep"),
                 (pr(labels=(*self.LABELS, rs.ON_HOLD_LABEL)), auto, "ignore"),
                 (pr(labels=self.LABELS), proposal, "disarm"),
                 (pr(labels=self.LABELS), doc({SKILL: roster_added(retire())}), "disarm"),
                 (pr(labels=self.LABELS), doc({SKILL: VERDICTS["keep"]}), "withdraw"),
                 (pr(labels=self.LABELS), doc({}), "keep"),
                 (pr(labels=self.LABELS), doc({SKILL: pending(retire())}), "rearm"))
        for item, gates, want in cases:
            with self.subTest(labels=item["labels"], want=want):
                self.assertEqual(rs.withdrawal_decision(item, gates)["action"], want)
        gates = doc(guidance={SECTION: gretire()})
        self.assertEqual(rs.withdrawal_decision(gpr(labels=self.LABELS), gates,
                                                "guidance")["action"], "rearm")
        gates = doc(guidance={SECTION: unfinished_alone()})
        self.assertEqual(rs.withdrawal_decision(gpr(labels=self.LABELS), gates,
                                                "guidance")["action"], "disarm")

    def test_rearms_with_the_retirement_jobs_command_then_unlabels_and_comments(self):
        gh = FakeGh(armed=False, head="b" * 40)
        lines = rs.withdraw_stale(doc({SKILL: retire()}), [pr(labels=self.LABELS)],
                                  "skill", gh)
        repo = rs.REGISTRY_REPO
        self.assertEqual(gh.writes(), [
            ["pr", "merge", SKILL_URL, "-R", repo, "--auto", "--merge",
             "--match-head-commit", "b" * 40],
            ["pr", "edit", SKILL_URL, "-R", repo, "--remove-label", rs.DISARMED_LABEL],
            ["pr", "comment", SKILL_URL, "-R", repo, "--body-file", "-"]])
        self.assertTrue(gh.armed)
        self.assertTrue(lines[0].startswith("re-armed #41"))
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn(rs.REARMED_MARKER.format(subject=SKILL), body)
        self.assertIn("turned back on", body)
        self.assertTrue(body.rstrip("\n").endswith(
            "<sub>🤖 Written by Claude Code on behalf of @Adam-S-Daniel</sub>"))
        self.assertFalse(any(a[0] == "issue" for a, _ in gh.calls))

    def test_the_arm_is_the_command_execute_uses(self):
        action = {"action": "removal", "branch": "retire-skill/x", "path": "p", "versions": {},
                  "skill": "x", "title": "t", "notice": {"title": "n"}}
        armed = next(c for c in rs.commands(action) if c[1:3] == ["pr", "merge"])
        c = rs.withdraw_commands("skill", SKILL_URL)
        self.assertEqual(c["arm"][3:-1], armed[4:-1])
        self.assertEqual(c["arm"][3:-1], ["-R", rs.REGISTRY_REPO, "--auto", "--merge",
                                          "--match-head-commit"])
        self.assertEqual(c["arm"][:2], ["pr", "merge"])

    def test_the_guidance_pass_rearms_in_agent_guidance(self):
        gh = FakeGh(armed=False)
        rs.withdraw_stale(doc(guidance={SECTION: gretire()}), [gpr(labels=self.LABELS)],
                          "guidance", gh)
        self.assertEqual([a[1] for a in gh.writes()], ["merge", "edit", "comment"])
        self.assertTrue(all(rs.GUIDANCE_REPO in a for a in gh.writes()))

    def test_a_rearm_with_a_foreign_url_is_refused(self):
        gh = FakeGh(armed=False)
        bad = pr(labels=self.LABELS, url=f"https://github.com/{rs.GUIDANCE_REPO}/pull/41")
        with self.assertRaises(rs.RetireError):
            rs.withdraw_stale(doc({SKILL: retire()}), [bad], "skill", gh)
        self.assertEqual(gh.writes(), [])

    def test_already_armed_only_loses_the_label(self):
        gh = FakeGh(armed=True)
        lines = rs.withdraw_stale(doc({SKILL: retire()}), [pr(labels=self.LABELS)],
                                  "skill", gh)
        self.assertEqual(gh.writes(), [["pr", "edit", SKILL_URL, "-R", rs.REGISTRY_REPO,
                                        "--remove-label", rs.DISARMED_LABEL]])
        self.assertTrue(lines[0].startswith("unlabeled #41"))

    def test_a_person_disarmed_removal_stays_off(self):
        gh = FakeGh(armed=False)
        lines = rs.withdraw_stale(doc({SKILL: retire()}), [pr()], "skill", gh)
        self.assertEqual(gh.writes(), [])
        self.assertTrue(lines[0].startswith("kept #41"))

    def test_an_arm_that_does_not_hold_refuses_and_keeps_the_label(self):
        gh = FakeGh(armed=False, arms=False)
        with self.assertRaises(rs.RetireError):
            rs.withdraw_stale(doc({SKILL: retire()}), [pr(labels=self.LABELS)], "skill", gh)
        self.assertEqual([a[1] for a in gh.writes()], ["merge"])

    def test_an_unreadable_head_refuses_before_arming(self):
        for head in ("", "not-a-sha", "A" * 40):
            with self.subTest(head=head):
                gh = FakeGh(armed=False, head=head)
                with self.assertRaises(rs.RetireError):
                    rs.withdraw_stale(doc({SKILL: retire()}), [pr(labels=self.LABELS)],
                                      "skill", gh)
                self.assertEqual(gh.writes(), [])

    def test_a_closed_pull_request_is_not_rearmed(self):
        gh = FakeGh(armed=False, state="CLOSED")
        rs.withdraw_stale(doc({SKILL: retire()}), [pr(labels=self.LABELS)], "skill", gh)
        self.assertEqual(gh.writes(), [])

    def test_disarm_then_rearm_round_trip(self):
        # Data incomplete, then complete again: off with the label, then on
        # without it.
        gh = FakeGh()
        rs.withdraw_stale(doc({SKILL: roster_added(retire())}), [pr()], "skill", gh)
        self.assertFalse(gh.armed)
        labels = [a[-1] for a in gh.writes() if "--add-label" in a]
        self.assertEqual(labels, [rs.DISARMED_LABEL])
        rs.withdraw_stale(doc({SKILL: retire()}), [pr(labels=(rs.AGENT_LABEL, *labels))],
                          "skill", gh)
        self.assertTrue(gh.armed)

    def test_dry_run_and_the_environment_check(self):
        gh = FakeGh([pr(labels=self.LABELS)])
        path = Path(tempfile.mkdtemp()) / "gates.json"
        path.write_text(json.dumps(doc({SKILL: retire()})))
        out = io.StringIO()
        self.assertEqual(rs.main(["--withdraw-stale", "--gates", str(path), "--dry-run"],
                                 env={}, gh=gh, out=out), 0)
        plan = json.loads(out.getvalue())
        self.assertEqual([i["action"] for i in plan["withdraw"]], ["rearm"])
        c = rs.withdraw_commands("skill", SKILL_URL)
        self.assertEqual(plan["would_run"], [["gh", *x] for x in (
            c["state"], c["view"], c["head"], c["arm"], c["view"], c["unlabel"],
            c["comment"])])
        self.assertEqual(gh.writes(), [])
        err = io.StringIO()
        with redirect_stderr(err):
            code = rs.main(["--withdraw-stale", "--gates", str(path)], env=SCHEDULE, gh=gh,
                           out=io.StringIO())
        self.assertEqual(code, 2)
        self.assertEqual(gh.writes(), [])
        path.unlink()
        path.parent.rmdir()

    def test_dry_run_lists_the_disarm_label(self):
        c = rs.withdraw_commands("skill", SKILL_URL)
        item = {"action": "disarm", "url": SKILL_URL}
        self.assertIn(c["label"], rs.would_run("skill", item))
        self.assertEqual(c["label"][-2:], ["--add-label", rs.DISARMED_LABEL])


class BasisTests(unittest.TestCase):
    """Round 3's M2: a removal is judged by the results it was opened on,
    the "**retire** as of <as_of>" its body records."""

    AS_OF = "2026-11-02T10:00:00+00:00"
    STALE = doc({SKILL: VERDICTS["keep"]}, as_of=AS_OF)

    def body(self, stamp):
        return (f"Removes `x`: its retirement verdict in [skills-evals#70](u) is "
                f"**retire** as of {stamp} (every cell shows no benefit).\n")

    def decide(self, body, created_at=OPENED, gates=None):
        item = pr(created_at=created_at)
        if body is not None:
            item["body"] = body
        return rs.withdrawal_decision(item, gates or self.STALE)

    def test_a_basis_newer_than_the_verdicts_is_kept(self):
        d = self.decide(self.body("2026-11-02T10:00:01+00:00"))
        self.assertEqual(d["action"], "keep")
        self.assertIn("newer results", d["why"])

    def test_a_pr_opened_late_on_older_results_is_withdrawn(self):
        # Case (a): the ingest committed results after the PR's basis but
        # before the PR opened; created_at alone would have kept it.
        d = self.decide(self.body("2026-11-02T09:00:00+00:00"),
                        created_at="2026-11-02T11:00:00Z")
        self.assertEqual(d["action"], "withdraw")

    def test_the_same_results_withdraw(self):
        # Case (b): a main-side input made the verdict stale while the
        # results tip stayed where it was.
        d = self.decide(self.body(self.AS_OF), created_at="2026-11-02T11:00:00Z")
        self.assertEqual(d["action"], "withdraw")
        d = self.decide(self.body("20261102T100000Z"), created_at="2026-11-02T11:00:00Z")
        self.assertEqual(d["action"], "withdraw")

    def test_no_parseable_basis_falls_back_to_created_at(self):
        for body in (None, "", "no stamp here", self.body("yesterday"),
                     self.body("2026-13-40T00:00:00Z")):
            with self.subTest(body=body):
                self.assertEqual(self.decide(body, created_at="2026-11-02T11:00:00Z")["action"],
                                 "keep")
                self.assertEqual(self.decide(body)["action"], "withdraw")
                self.assertEqual(self.decide(body, created_at=None)["action"], "keep")

    def test_an_unknown_as_of_keeps(self):
        gates = {**self.STALE, "as_of": "not a time"}
        self.assertEqual(self.decide(self.body("2026-11-01T00:00:00Z"), gates=gates)["action"],
                         "keep")

    def test_the_basis_reads_the_first_stamp(self):
        self.assertEqual(rs._basis(self.body("2026-11-01T00:00:00Z")
                                   + self.body("2026-12-01T00:00:00Z")),
                         rs._moment("2026-11-01T00:00:00Z"))
        self.assertIsNone(rs._basis(None))

    def test_the_skill_pr_body_records_a_readable_basis(self):
        gates = {**doc({SKILL: retire()}, as_of=self.AS_OF)}
        body = rs._pr_body(gates, SKILL, {"path": "plugins/p/skills/x", "plugin": "p"},
                           {"plugins/p/plugin.json": ("1.0.0", "1.0.1")}, None)
        self.assertEqual(rs._basis(body), rs._moment(self.AS_OF))

    def test_the_guidance_pr_body_records_a_readable_basis(self):
        from unittest import mock
        gates = {**doc(guidance={SECTION: gretire()}, as_of=self.AS_OF)}

        def gh(args, stdin=None):
            return ""

        row = {"file": "agents-md/base.md", "heading": "Example heading"}
        with mock.patch.object(rs, "guidance_row", return_value=row):
            plan = rs.guidance_plan(gates, Path("."), gh, allowed=("auto",))
        self.assertEqual(plan["action"], "guidance-removal")
        self.assertEqual(rs._basis(plan["body"]), rs._moment(self.AS_OF))

    def test_the_listing_reads_the_body(self):
        gh = FakeGh()
        rs.removal_prs(gh, "skill")
        jq = gh.calls[0][0][-1]
        self.assertIn('body: (.body // "")', jq)
        self.assertIn("created_at: .created_at", jq)


class NoticeOrderTests(unittest.TestCase):
    """Round 3's m2: a removal notice is closed before its comment, so a
    failure never leaves an open notice whose comment says it is closed."""

    NOTICE = {"number": 6, "body": rs.SKILL_NOTICE_MARKER.format(skill=SKILL),
              "author": rs.ISSUE_AUTHOR, "state": "open"}

    def test_a_failed_comment_leaves_the_notice_closed_and_says_so(self):
        gh = FakeGh(issues=[self.NOTICE], fail=["issue", "comment"])
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        writes = [a[:3] for a in gh.writes() if a[0] == "issue"]
        self.assertEqual(writes, [["issue", "create", "-R"], ["issue", "close", "6"],
                                  ["issue", "comment", "6"]])
        self.assertTrue(lines[0].endswith("closed its removal notice #6 (no comment)"))

    def test_a_failed_close_posts_no_comment(self):
        gh = FakeGh(issues=[self.NOTICE], fail=["issue", "close"])
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        self.assertFalse(any(a[:3] == ["issue", "comment", "6"] for a in gh.writes()))
        self.assertTrue(lines[0].endswith("could not close its removal notice"))


class RetirementIssueCommentTests(unittest.TestCase):
    """Round 3's m4 (mutant R15): the comment on an open retirement issue is
    the note alone, never the filing body with its marker."""

    def test_the_comment_carries_no_marker_and_not_the_body(self):
        gh = FakeGh(issues=[issue(7)])
        rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        body = next(s for a, s in gh.calls if a[:3] == ["issue", "comment", "7"])
        self.assertNotIn(rs.ISSUE_MARKER.format(skill=SKILL), body)
        self.assertNotIn("<!-- skills-evals:", body)
        self.assertIn(SKILL_URL, body)

    def test_the_guidance_comment_carries_no_marker(self):
        gh = FakeGh(issues=[issue(3, SECTION, marker=rs.GUIDANCE_ISSUE_MARKER)])
        rs.withdraw_stale(doc(guidance={SECTION: VERDICTS["keep"]}), [gpr()], "guidance", gh)
        body = next(s for a, s in gh.calls if a[:3] == ["issue", "comment", "3"])
        self.assertNotIn(rs.GUIDANCE_ISSUE_MARKER.format(section=SECTION), body)
