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

    def test_a_skills_retire_is_kept_whatever_its_removal_field_or_cells_say(self):
        # Adam, 2026-11-13: every retire is automatic, so neither a `proposal`
        # field nor a no-clear-effect headroom cell makes the removal stale.
        for entry in (VERDICTS["retire+proposal"],
                      retire("auto", ("no-benefit", "no-clear-effect"))):
            self.assertEqual(self.decide(entry)["action"], "keep")

    def test_retire_pending_with_a_confirmed_automatic_removal_keeps(self):
        # Round 1's M1: finalize demotes all but one confirmed subject per
        # evaluation to retire-pending; that ranks it and says nothing
        # against it, so the removal it already has stays open.
        d = self.decide(pending(retire("auto")))
        self.assertEqual(d["action"], "keep")

    def test_retire_pending_whose_raw_verdict_is_not_an_automatic_retire_withdraws(self):
        for name, entry in (("no raw verdict", {**pending(retire("auto")),
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
                 label_fails=0, repo_labels=(), closed=()):
        self.prs, self.armed, self.stuck, self.fail = list(prs), armed, stuck, fail
        self.issues, self.state, self.closed = list(issues), state, list(closed)
        self.label_fails = label_fails  # how many `--add-label` calls fail first
        self.repo_labels = list(repo_labels)  # the repository's labels
        self.pr_labels = []
        self.head = "c" * 40  # the closed pull request's head commit
        self.closer = rs.LOOP_AUTHOR  # who closed the pull request this pass closes
        self.timeline = []  # its timeline events (R7-3)
        self.unlabel_stuck = False  # a `--remove-label` that exits 0 without landing
        self.calls = []

    def __call__(self, args, stdin=None):
        self.calls.append((list(args), stdin))
        if self.fail and args[:2] == self.fail:
            raise rs.RetireError(f"gh {args[0]} exited 1")
        if "--add-label" in args and self.label_fails:
            self.label_fails -= 1
            raise rs.RetireError(f"gh {args[0]} exited 1")
        if args[:2] == ["api", "--paginate"] and "/timeline?" in args[2]:
            # The arms read (ARMS_JQ) keeps only the enables, as jq would; an
            # entry with no `event` is one already shaped as an arm.
            keep = [e for e in self.timeline
                    if rs.ARMS_JQ not in args or e.get("event", "auto_merge_enabled")
                    == "auto_merge_enabled"]
            return "".join(json.dumps(e) + "\n" for e in keep)
        if args[0] == "api" and "/pulls/" in args[1]:
            return ("true" if self.armed else "false") + "\n"  # the REST armed read
        if args[:2] == ["api", "--paginate"]:
            rows = (self.issues if "/issues?" in args[2] else
                    self.closed if "state=closed" in args[2] else self.prs)
            # A pulls listing never carries `closed_by`: only the issue read does.
            return "".join(json.dumps({k: v for k, v in p.items() if k != "closed_by"}) + "\n"
                           for p in rows)
        if args[:2] == ["pr", "merge"] and "--disable-auto" in args and not self.stuck:
            self.armed = False
        if args[:2] == ["pr", "edit"] and "--add-label" in args:
            self.pr_labels.append(args[-1])
        if args[:2] == ["pr", "edit"] and "--remove-label" in args and not self.unlabel_stuck:
            self.pr_labels = [x for x in self.pr_labels if x != args[-1]]
        if args[:2] == ["label", "create"]:
            self.repo_labels.append(args[2])
        if args[:2] == ["label", "list"]:
            return "".join(f"{x}\n" for x in self.repo_labels)
        if args[:2] == ["pr", "view"] and "state" in args:
            return self.state + "\n"
        if args[:2] == ["pr", "view"] and "labels" in args:
            return "".join(f"{x}\n" for x in self.pr_labels)
        if args[:2] == ["pr", "view"] and "headRefOid" in args:
            return self.head + "\n"
        if args[:2] == ["pr", "view"]:
            return ("MERGE" if self.armed else "") + "\n"
        if args[0] == "api" and "/issues/" in args[1]:
            n = int(args[1].rsplit("/", 1)[1])
            return next((p.get("closed_by") or "" for p in self.closed
                         if p.get("number") == n), self.closer) + "\n"
        return ""

    def writes(self):
        return [a for a, _ in self.calls if not (a[0] == "api" and "-X" not in a)
                and a[:2] not in (["pr", "view"], ["label", "list"])]


def issue(number, subject=SKILL, state="open", author=rs.ISSUE_AUTHOR,
          marker=rs.ISSUE_MARKER):
    key = "section" if marker == rs.GUIDANCE_ISSUE_MARKER else "skill"
    return {"number": number, "body": marker.format(**{key: subject}) + "\nbody",
            "author": author, "state": state}


class WithdrawStaleTests(unittest.TestCase):
    """The thin layer: the calls, in order, with the fake."""

    def test_disarms_labels_files_then_comments_closes_and_deletes_the_branch(self):
        gh = FakeGh()
        gates = doc({SKILL: VERDICTS["keep"]})
        deletes = []
        lines = rs.withdraw_stale(gates, [pr()], "skill", gh,
                                  "https://github.com/Adam-S-Daniel/skills-evals/actions/runs/1",
                                  delete=lambda *a: deletes.append(a))
        self.assertEqual(lines, ["withdrew #41: the verdict is keep, not retire; "
                                 "filed its retirement issue; deleted its branch"])
        # R6-5: the branch goes, leased on the closed pull request's head.
        self.assertEqual(deletes, [(rs.REGISTRY_REPO, f"{rs.BRANCH_PREFIX}{SKILL}", gh.head)])
        repo = rs.REGISTRY_REPO
        self.assertEqual([a[:4] if a[0] == "issue" else a for a in gh.writes()], [
            ["pr", "merge", SKILL_URL, "-R", repo, "--disable-auto"],
            ["pr", "edit", SKILL_URL, "-R", repo, "--add-label", rs.WITHDRAWN_LABEL],
            ["issue", "create", "-R", rs.EVALS_REPO],
            ["pr", "comment", SKILL_URL, "-R", repo, "--body-file", "-"],
            ["pr", "close", SKILL_URL, "-R", repo]])
        self.assertEqual(gh.pr_labels, [rs.WITHDRAWN_LABEL])
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
        # Issue 5 is a closed one the withdrawal path filed: it declines nothing
        # (a closed proposal would, R9-1).
        closed = {**issue(5, state="closed")}
        closed["body"] += f"\n{rs.WITHDRAWAL_STAMP}"
        gh = FakeGh(issues=[closed, issue(9), issue(7)])
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        self.assertEqual([a[:3] for a, _ in gh.calls if a[0] == "issue"],
                         [["issue", "comment", "7"]])
        self.assertTrue(lines[0].endswith(
            "commented on issue #7; could not delete its branch (RetireError)"))
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
        self.assertEqual([a[1] for a in gh.writes()], ["edit", "create", "comment", "close"])

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
                         ["merge", "edit", "comment", rs.GUIDANCE_REPO])
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
            ["pr", "comment", SKILL_URL, "-R", rs.REGISTRY_REPO, "--body-file", "-"]])
        self.assertFalse(gh.armed)
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn(rs.DISARMED_MARKER.format(subject=SKILL), body)
        self.assertTrue(body.rstrip("\n").endswith(rs.AGENT_MARKER))
        self.assertTrue(lines[0].startswith("disarmed #41"))

    def test_a_disarmed_removal_is_not_commented_again(self):
        gh = FakeGh()
        rs.withdraw_stale(self.gates(), [pr()], "skill", gh)
        rs.withdraw_stale(self.gates(), [pr()], "skill", gh)
        self.assertEqual([a[1] for a in gh.writes()], ["merge", "comment"])

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
        self.assertEqual([a[1] for a in gh.writes()],
                         ["merge", "edit", "create", "comment", "close"])

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
                 ("proposal mode", doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal"),
                  False),
                 ("absent", doc({}), False), ("unknown", None, False))
        for name, gates, want in cases:
            with self.subTest(name):
                self.assertIs(rs.refresh_allowed(gates, head, FakeGh())[0], want)

    def test_guidance_heads_read_the_guidance_block(self):
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        self.assertTrue(rs.refresh_allowed(doc(guidance={SECTION: gretire()}), head,
                                           FakeGh())[0])
        self.assertFalse(rs.refresh_allowed(
            doc(guidance={SECTION: VERDICTS["keep"]}), head, FakeGh())[0])
        self.assertFalse(rs.refresh_allowed(doc({SECTION: VERDICTS["retire+auto"]}), head,
                                            FakeGh())[0])

    def test_other_loop_heads_are_always_refreshed(self):
        for head in ("eval-improve/x", "draft-skill/x", "draft-skill-fixtures/x"):
            with self.subTest(head=head):
                self.assertTrue(rs.refresh_allowed(None, head, FakeGh())[0])

    def test_a_removal_head_naming_no_subject_is_not_refreshed(self):
        self.assertFalse(rs.refresh_allowed(doc({}), f"{rs.BRANCH_PREFIX}Bad Name",
                                            FakeGh())[0])

    def test_a_declined_removal_is_not_refreshed(self):
        # R10-4: a closed proposal issue declines the removal, so a decline
        # the withdrawal pass could not finish is never refreshed into a merge.
        head = f"{rs.BRANCH_PREFIX}{SKILL}"
        gates = doc({SKILL: VERDICTS["retire+auto"]})
        for stamp in (rs.PROPOSAL_STAMP, ()):  # a legacy issue declines too
            with self.subTest(stamp=stamp):
                issues = [stamped(900, stamp) if stamp else issue(900, state="closed")]
                ok, why = rs.refresh_allowed(gates, head, FakeGh(issues=issues))
                self.assertFalse(ok)
                self.assertIn("#900 is closed", why)
        for issues in ([stamped(900, rs.PROPOSAL_STAMP, state="open")],
                       [stamped(900, rs.WITHDRAWAL_STAMP)]):
            with self.subTest(issues=issues):
                self.assertTrue(rs.refresh_allowed(gates, head, FakeGh(issues=issues))[0])
        gguidance = doc(guidance={SECTION: gretire()})
        closed = stamped(900, rs.PROPOSAL_STAMP, subject=SECTION,
                         marker=rs.GUIDANCE_ISSUE_MARKER)
        self.assertFalse(rs.refresh_allowed(gguidance, f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}",
                                            FakeGh(issues=[closed]))[0])

    def test_an_unreadable_issue_list_refreshes_no_removal(self):
        def failing(args, stdin=None):
            raise rs.RetireError("gh api exited 1")
        ok, why = rs.refresh_allowed(doc({SKILL: VERDICTS["retire+auto"]}),
                                     f"{rs.BRANCH_PREFIX}{SKILL}", failing)
        self.assertEqual((ok, why), (False, "its retirement issues could not be read"))
        # Another loop head never reads the issues.
        self.assertTrue(rs.refresh_allowed(None, "eval-improve/x", failing)[0])


class RemovalCheckCliTests(unittest.TestCase):
    """refresh_loop_prs.py removal-check, the call the workflow makes."""

    def run_check(self, gates, head, gh=None):
        import refresh_loop_prs as rlp
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "latest.json"
            if gates is not None:
                path.write_text(json.dumps(gates))
            out = io.StringIO()
            from contextlib import redirect_stdout
            with redirect_stdout(out):
                code = rlp.main(["removal-check", "--gates", str(path), "--head", head],
                                gh=gh or FakeGh())
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
        code, out = self.run_check(doc({SKILL: VERDICTS["retire+auto"]}), head,
                                   FakeGh(issues=[stamped(900, rs.PROPOSAL_STAMP)]))
        self.assertEqual(code, 4)
        self.assertIn("reason=its proposal issue #900 is closed, which declines it", out)


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
        self.assertEqual(len(later), 9)  # the review's CLI and bearer (#917) included
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
            # pull-requests: write to disarm, label (creating the label
            # too), comment and close; contents: write for the leased branch
            # delete after the close (R6-5). It never arms.
            self.assertEqual({k: v for k, v in s["with"].items()
                              if k.startswith("permission-")},
                             {"permission-contents": "write",
                              "permission-pull-requests": "write"})
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
        self.assertIn('removal-check --gates "$GATES" --head "$ref" --number "$n"',
                      run["run"])
        self.assertLess(run["run"].index("removal-check"), run["run"].index(" merge --repo"))
        self.assertEqual(run["env"]["GATES"], "${{ runner.temp }}/gates/latest.json")
        download = next(s for s in steps if str(s.get("uses", "")).startswith(
            "actions/download-artifact@"))
        self.assertIs(download["continue-on-error"], True)
        self.assertEqual(download["with"]["name"], "gates")

    def test_the_refresh_push_cannot_recreate_a_deleted_branch(self):
        # R6-11: a withdrawal deletes the branch; a refresh that fetched it
        # before must not push it back. Leased on the fetched head, and the
        # merge sits on that head, so the push is a fast-forward.
        run = next(s for s in self.jobs["refresh"]["steps"]
                   if "refresh_repo" in s.get("run", ""))["run"]
        self.assertIn('push -q --force-with-lease="refs/heads/${ref}:${head}" origin', run)
        self.assertLess(run.index('head="$(git -C "$dir" rev-parse HEAD)"'),
                        run.index("--force-with-lease"))



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
  merge) echo "outcome=${MERGE_OUTCOME:-up-to-date}"; exit 0 ;;
esac
exit 9
"""

FAKE_GIT = """#!/bin/sh
printf 'git %s\\n' "$*" >> "$CALLS"
case "$*" in
  *rev-parse*) echo 0123456789abcdef0123456789abcdef01234567 ;;
  *"merge-base --is-ancestor 0123"*) exit "${ANCESTOR_RC:-0}" ;;
esac
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

    def run_step(self, check_rc, **extra):
        calls, summary = self.tmp / "calls.log", self.tmp / "summary.md"
        for f in (calls, summary):
            f.write_text("")
        env = {"PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
               "HOME": str(self.tmp), "CALLS": str(calls), "CHECK_RC": str(check_rc),
               "GITHUB_STEP_SUMMARY": str(summary), "RUNNER_TEMP": str(self.tmp),
               "GH_TOKEN": "job-token-invented", "REGISTRY_TOKEN": "registry-token-invented",
               "ROSTER_TOKEN": "", "SELF_REPO": "Adam-S-Daniel/skills-evals",
               "SCRIPT": str(self.tmp / "refresh_loop_prs.py"),
               "GATES": str(self.tmp / "gates.json"), **extra}
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

    def test_a_merge_not_on_the_fetched_head_is_never_pushed(self):
        # R7-5: fast-forward only by check, so the lease cannot rewrite
        # history. ANCESTOR_RC answers `merge-base --is-ancestor`.
        proc, calls, summary = self.run_step(0, MERGE_OUTCOME="merged", ANCESTOR_RC="1")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertTrue(any("merge-base --is-ancestor" in c for c in calls), calls)
        self.assertFalse(any(" push " in c for c in calls), calls)
        self.assertIn("does not descend from the fetched head", proc.stdout)

    def test_a_merge_on_the_fetched_head_is_pushed(self):
        # The positive control for the test above.
        proc, calls, summary = self.run_step(0, MERGE_OUTCOME="merged", ANCESTOR_RC="0")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        pushes = [c for c in calls if " push " in c]
        self.assertEqual(len(pushes), 1, calls)
        self.assertIn("--force-with-lease=refs/heads/retire-skill/example-skill:", pushes[0])
        ancestry = next(i for i, c in enumerate(calls) if "merge-base --is-ancestor" in c)
        self.assertLess(ancestry, calls.index(pushes[0]))




# ---------------------------------------------------------------------------
# PR #724 round 3 and PR #740 round 4, kept by round 5's redesign.


def gpr(**kw):
    kw.setdefault("head", f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}")
    kw.setdefault("url", GUIDANCE_URL)
    kw.setdefault("number", 42)
    return pr(**kw)


class BasisTests(unittest.TestCase):
    """Round 3's M2: a removal is judged by the results it was opened on,
    the "**retire** as of <as_of>" its body records."""

    AS_OF = "2026-11-02T10:00:00+00:00"
    STALE = doc({SKILL: VERDICTS["keep"]}, as_of=AS_OF)

    def body(self, stamp):
        return (f"Removes `x`: its retirement verdict in [skills-evals#70](u) is "
                f"**retire** as of {stamp} (every cell shows no benefit).\n")

    def decide(self, body, created_at="2026-11-03T00:00:00Z", gates=None):
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
                self.assertEqual(self.decide(body, created_at=OPENED)["action"], "withdraw")
                self.assertEqual(self.decide(body, created_at=None)["action"], "keep")

    def test_an_unknown_as_of_keeps(self):
        gates = {**self.STALE, "as_of": "not a time"}
        self.assertEqual(self.decide(self.body("2026-11-01T00:00:00Z"), gates=gates)["action"],
                         "keep")

    def test_the_basis_reads_the_first_stamp(self):
        late = "2026-12-02T00:00:00Z"
        self.assertEqual(rs._basis(self.body("2026-11-01T00:00:00Z")
                                   + self.body("2026-12-01T00:00:00Z"), late),
                         rs._moment("2026-11-01T00:00:00Z"))
        self.assertIsNone(rs._basis(None, late))

    def test_the_skill_pr_body_records_a_readable_basis(self):
        gates = {**doc({SKILL: retire()}, as_of=self.AS_OF)}
        body = rs._pr_body(gates, SKILL, {"path": "plugins/p/skills/x", "plugin": "p"},
                           {"plugins/p/plugin.json": ("1.0.0", "1.0.1")}, None)
        self.assertEqual(rs._basis(body, "2026-11-02T10:05:00Z"), rs._moment(self.AS_OF))

    def test_the_guidance_pr_body_records_a_readable_basis(self):
        from unittest import mock
        gates = {**doc(guidance={SECTION: gretire()}, as_of=self.AS_OF)}

        def gh(args, stdin=None):
            return ""

        row = {"file": "agents-md/base.md", "heading": "Example heading"}
        with mock.patch.object(rs, "guidance_row", return_value=row):
            plan = rs.guidance_plan(gates, Path("."), gh, allowed=("auto",))
        self.assertEqual(plan["action"], "guidance-removal")
        self.assertEqual(rs._basis(plan["body"], "2026-11-02T10:05:00Z"),
                         rs._moment(self.AS_OF))

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


class ItemIsolationTests(unittest.TestCase):
    """R4-2's second half: one pull request's failed call does not skip the
    later ones; the pass still fails, with every status line."""

    def test_a_failure_does_not_skip_the_next_item(self):
        second = pr(head=f"{rs.BRANCH_PREFIX}other-skill", number=43,
                    url=f"https://github.com/{rs.REGISTRY_REPO}/pull/43")
        gh = FakeGh(fail=["pr", "close"])
        gates = doc({SKILL: VERDICTS["keep"], "other-skill": VERDICTS["keep"]})
        with self.assertRaises(rs.WithdrawFailed) as ctx:
            rs.withdraw_stale(gates, [pr(), second], "skill", gh)
        self.assertEqual([x.split(":")[0] for x in ctx.exception.lines],
                         ["failed #41", "failed #43"])
        self.assertEqual(len([a for a in gh.writes() if a[:2] == ["pr", "close"]]), 2)

    def test_the_next_item_still_acts(self):
        second = pr(head=f"{rs.BRANCH_PREFIX}other-skill", number=43,
                    url=f"https://github.com/{rs.REGISTRY_REPO}/pull/43")
        calls = {"n": 0}
        gh = FakeGh()
        real = gh.__call__

        def first_disable_sticks(args, stdin=None):
            if "--disable-auto" in args:
                calls["n"] += 1
                if calls["n"] == 1:
                    gh.calls.append((list(args), stdin))
                    return ""  # the read-back still says armed: #41 fails
            return real(args, stdin)

        gates = doc({SKILL: VERDICTS["keep"], "other-skill": VERDICTS["keep"]})
        with self.assertRaises(rs.WithdrawFailed) as ctx:
            rs.withdraw_stale(gates, [pr(), second], "skill", first_disable_sticks)
        self.assertTrue(ctx.exception.lines[0].startswith("failed #41: auto-merge is still"))
        self.assertTrue(ctx.exception.lines[1].startswith("withdrew #43"))
        self.assertEqual(str(ctx.exception), "auto-merge is still enabled on #41")

    def test_main_prints_every_line_then_exits_2(self):
        path = Path(tempfile.mkdtemp()) / "gates.json"
        path.write_text(json.dumps(doc({SKILL: VERDICTS["keep"]})))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            code = rs.main(["--withdraw-stale", "--gates", str(path)], env=AUTO_ENV,
                           gh=FakeGh([pr()], fail=["pr", "close"]), out=out)
        self.assertEqual(code, 2)
        self.assertIn("retire_skill: failed #41: gh pr exited 1", out.getvalue())
        self.assertEqual(err.getvalue().strip(), "retire_skill: gh pr exited 1")
        path.unlink()
        path.parent.rmdir()


class BasisGuardTests(unittest.TestCase):
    """R4-5: a basis later than the pull request itself, or not on the
    loop's own first line, is ignored."""

    STALE = doc({SKILL: VERDICTS["keep"]}, as_of="2026-11-02T10:00:00Z")

    def body(self, stamp):
        return f"Removes `x`: its verdict is **retire** as of {stamp} (reason).\n"

    def test_a_future_basis_falls_back_to_created_at(self):
        item = {**pr(created_at="2026-11-01T00:00:00Z"), "body": self.body("20991231T000000Z")}
        self.assertEqual(rs.withdrawal_decision(item, self.STALE)["action"], "withdraw")
        self.assertIsNone(rs._basis(item["body"], item["created_at"]))
        self.assertIsNone(rs._basis(item["body"], None))
        ok = self.body("2026-10-31T00:00:00Z")
        self.assertIsNotNone(rs._basis(ok, "2026-10-31T00:00:00Z"))  # equal is fine

    def test_only_the_loops_first_line_counts(self):
        quoted = "Notes.\n> " + self.body("2026-12-01T00:00:00Z")
        self.assertIsNone(rs._basis(quoted, "2027-01-01T00:00:00Z"))
        later = "Some text\n" + self.body("2026-12-01T00:00:00Z")
        self.assertIsNone(rs._basis(later, "2027-01-01T00:00:00Z"))
        two = self.body("2026-10-01T00:00:00Z").rstrip("\n") + " " + \
            self.body("2026-12-01T00:00:00Z")
        self.assertEqual(rs._basis(two, "2027-01-01T00:00:00Z"),
                         rs._moment("2026-10-01T00:00:00Z"))


# ---------------------------------------------------------------------------
# PR #740 round 5: a loop withdrawal is a pause, not a decision.

sys.path.insert(0, str(ROOT / "test" / "issues"))
import test_issue_70_retire as t70  # noqa: E402

SHA_A, SHA_B = "a" * 40, "b" * 40


def closed_pr(number=8, labels=(rs.AGENT_LABEL, rs.WITHDRAWN_LABEL), author=rs.LOOP_AUTHOR,
              merged=False, head=f"{rs.BRANCH_PREFIX}{t70.SKILL}", closed_by=rs.LOOP_AUTHOR,
              **extra):
    """One record as CLOSED_JQ shapes it, with the `closed_by` login
    `with_closer` adds (the fakes answer the issue read from it)."""
    return {"number": number, "head": head, "labels": list(labels), "author": author,
            "merged": merged, "closed_by": closed_by,
            "url": f"https://github.com/{rs.REGISTRY_REPO}/pull/{number}", **extra}


class LoopWithdrawnTests(unittest.TestCase):
    """Only a closed, unmerged removal the loop opened and labeled
    `loop-withdrawn` decides nothing; anything else closed decides."""

    def test_a_loop_withdrawn_closed_pr_does_not_decide(self):
        self.assertTrue(rs.loop_withdrawn(closed_pr()))
        self.assertEqual(rs.deciding([closed_pr()]), ([], [closed_pr()]))

    def test_a_person_closed_pr_still_decides(self):
        # No label: a person closed it.
        p = closed_pr(labels=(rs.AGENT_LABEL,))
        self.assertFalse(rs.loop_withdrawn(p))
        self.assertEqual(rs.deciding([p]), ([p], []))

    def test_a_loop_pr_whose_label_a_person_removed_still_decides(self):
        # The conservative reading: a person took the pause away.
        p = closed_pr(labels=())
        self.assertEqual(rs.deciding([p, closed_pr(9)]), ([p], [closed_pr(9)]))

    def test_merged_foreign_or_unreadable_records_decide(self):
        for p in (closed_pr(merged=True), closed_pr(merged=None),
                  closed_pr(author="Adam-S-Daniel"), closed_pr(author=None),
                  {k: v for k, v in closed_pr().items() if k != "labels"},
                  closed_pr(labels="loop-withdrawn")):
            with self.subTest(p=p):
                self.assertFalse(rs.loop_withdrawn(p))
                self.assertEqual(rs.deciding([p])[0], [p])

    def test_a_labeled_pr_a_person_closed_decides(self):
        # R6-1, R6-3: the label alone is not a pause; the loop must have
        # closed it. An unknown closer decides too.
        for closer in ("a-person", "Adam-S-Daniel", None, "", 7):
            with self.subTest(closer=closer):
                p = closed_pr(closed_by=closer)
                self.assertFalse(rs.loop_withdrawn(p))
                self.assertEqual(rs.deciding([p]), ([p], []))

    def test_with_closer_reads_who_closed_each_candidate(self):
        gh = FakeGh(closed=[closed_pr(8), closed_pr(9, closed_by="a-person"),
                            closed_pr(10, merged=True), closed_pr(11, author="a-person")])
        got = rs.with_closer(gh, rs.REGISTRY_REPO, [
            {k: v for k, v in p.items() if k != "closed_by"} for p in gh.closed])
        self.assertEqual([p["closed_by"] for p in got], [rs.LOOP_AUTHOR, "a-person", None, None])
        # Only the two that could be a pause are read, by issue number.
        self.assertEqual([a for a, _ in gh.calls], [
            ["api", f"repos/{rs.REGISTRY_REPO}/issues/8", "--jq", '.closed_by.login // ""'],
            ["api", f"repos/{rs.REGISTRY_REPO}/issues/9", "--jq", '.closed_by.login // ""']])

    def test_with_closer_ignores_a_closer_in_the_listing_and_an_unreadable_one_decides(self):
        def fails(args, stdin=None):
            raise rs.RetireError("gh api exited 1")
        got = rs.with_closer(fails, rs.REGISTRY_REPO, [closed_pr()])
        self.assertIsNone(got[0]["closed_by"])
        self.assertEqual(rs.deciding(got)[0], got)

    def test_the_closed_listings_read_what_deciding_needs(self):
        for fn, subject in ((rs.closed_removal_prs, t70.SKILL),
                            (rs.guidance_closed_removal_prs, SECTION)):
            with self.subTest(fn=fn.__name__):
                gh = FakeGh()
                fn(gh, subject)
                jq = gh.calls[0][0][-1]
                for field in ("labels: [.labels[].name]", "author: .user.login",
                              "merged: (.merged_at != null)"):
                    self.assertIn(field, jq)

    def test_the_label_text_and_color(self):
        self.assertRegex(rs.WITHDRAWN_LABEL_COLOR, r"^[0-9A-Fa-f]{6}$")
        self.assertEqual(rs.WITHDRAWN_LABEL, "loop-withdrawn")
        self.assertLessEqual(len(rs.WITHDRAWN_LABEL_DESCRIPTION), 100)  # GitHub's limit


class ReopenAfterWithdrawalTests(t70.Base):
    """The retirement job opens a fresh removal for a subject whose last
    removal the loop withdrew, with a plain push (R6-5: the withdrawal
    deleted the branch)."""

    def run_auto(self, closed, *extra):
        fake = t70.FakeGitHub(closed=closed)
        argv = ["--gates", str(self.write_gates(t70.gates_doc("auto"))),
                "--registry", f"adam-agentskills={self.registry}", "--allow-mode", "auto",
                *extra]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            code = rs.main(argv, env=t70.AUTO_ENV, gh=fake.gh, push=fake.push,
                           review=t70.passing_review, out=out)
        return code, out.getvalue(), err.getvalue(), fake

    def test_a_withdrawn_removal_is_opened_again(self):
        code, out, err, fake = self.run_auto([closed_pr(), closed_pr(9)])
        self.assertEqual(code, 0, err)
        self.assertIn("opened", out)
        self.assertEqual([b for _, b in fake.pushes], [f"{rs.BRANCH_PREFIX}{t70.SKILL}"])
        self.assertTrue(any(a[:2] == ["pr", "create"] for a in fake.writes()))

    def test_a_person_closed_one_beside_it_still_decides(self):
        for other in (closed_pr(9, labels=(rs.AGENT_LABEL,)),
                      closed_pr(9, closed_by="a-person")):
            with self.subTest(other=other):
                code, out, err, fake = self.run_auto([closed_pr(), other])
                self.assertEqual(code, 0, err)
                self.assertIn("already decided", out)
                self.assertIn("/pull/9", out)
                self.assertEqual((fake.pushes, fake.writes()), ([], []))

    def test_the_dry_run_names_a_plain_push(self):
        code, out, err, _ = self.run_auto([closed_pr()], "--dry-run")
        self.assertEqual(code, 0, err)
        plan = json.loads(out)
        self.assertNotIn("replaces", plan)
        branch = f"{rs.BRANCH_PREFIX}{t70.SKILL}"
        self.assertIn(["git", "ls-remote", "origin", f"refs/heads/{branch}"], plan["would_run"])
        self.assertIn(["git", "push", "origin", f"HEAD:refs/heads/{branch}"], plan["would_run"])
        self.assertFalse(any("force" in x for a in plan["would_run"] for x in a))

    def test_the_guidance_plan_reopens_a_withdrawn_section(self):
        from unittest import mock
        gates = doc(guidance={SECTION: gretire()})
        row = {"file": "agents-md/base.md", "heading": "Example heading"}
        withdrawn = closed_pr(head=f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}")
        for closed, want in (([withdrawn], "guidance-removal"),
                             ([{**withdrawn, "labels": [rs.AGENT_LABEL]}], "none"),
                             ([{**withdrawn, "closed_by": "a-person"}], "none")):
            with self.subTest(want=want, closed=closed):
                gh = FakeGh(closed=closed)
                with mock.patch.object(rs, "guidance_row", return_value=row):
                    plan = rs.guidance_plan(gates, Path("."), gh, allowed=("auto",))
                self.assertEqual(plan["action"], want)
                self.assertNotIn("replaces", plan)


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=Example",
                           "-c", "user.email=example@example.com",
                           "-c", "commit.gpgsign=false", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


class BranchFixture(unittest.TestCase):
    """A real (local, bare) remote holding a withdrawn removal's branch, and
    a work tree whose HEAD is a fresh removal."""

    BRANCH = f"{rs.BRANCH_PREFIX}{SKILL}"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(self.tmp)], check=False))
        self.remote = self.tmp / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        self.work = self.tmp / "work"
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.work)], check=True)
        _git(self.work, "remote", "add", "origin", str(self.remote))
        _git(self.work, "commit", "-q", "--allow-empty", "-m", "base")
        _git(self.work, "push", "-q", "origin", "main")
        # The withdrawn removal's branch, still on the remote.
        _git(self.work, "checkout", "-q", "-b", "old")
        _git(self.work, "commit", "-q", "--allow-empty", "-m", "withdrawn removal")
        self.old = _git(self.work, "rev-parse", "HEAD")
        _git(self.work, "push", "-q", "origin", f"HEAD:refs/heads/{self.BRANCH}")
        # The fresh removal, on main.
        _git(self.work, "checkout", "-q", "-b", "fresh", "main")
        _git(self.work, "commit", "-q", "--allow-empty", "-m", "fresh removal")
        self.fresh = _git(self.work, "rev-parse", "HEAD")

    def remote_head(self):
        out = subprocess.run(["git", "-C", str(self.remote), "rev-parse", "--verify", "-q",
                              f"refs/heads/{self.BRANCH}"], capture_output=True, text=True)
        return out.stdout.strip() or None

    def delete(self, sha):
        rs.default_delete_branch(rs.REGISTRY_REPO, self.BRANCH, sha, "token",
                                 url=str(self.remote))


class BranchTests(BranchFixture):
    """default_push and default_delete_branch against a real (local, bare)
    remote (R6-5, R6-11): the withdrawal deletes the branch only while it
    still points at the closed pull request's head; a removal never pushes
    over a branch that exists, and nothing forces."""

    def test_the_withdrawal_deletes_the_branch_at_its_head(self):
        self.delete(self.old)
        self.assertIsNone(self.remote_head())

    def test_a_branch_someone_pushed_to_since_is_kept(self):
        with self.assertRaises(rs.RetireError):
            self.delete(SHA_B)
        self.assertEqual(self.remote_head(), self.old)

    def test_a_delete_needs_a_token_and_a_sha(self):
        for token, sha in ((None, self.old), ("token", "main"), ("token", None)):
            with self.subTest(token=token, sha=sha), self.assertRaises(rs.RetireError):
                rs.default_delete_branch(rs.REGISTRY_REPO, self.BRANCH, sha, token,
                                         url=str(self.remote))
        self.assertEqual(self.remote_head(), self.old)

    def test_the_reopen_never_pushes_over_a_branch_that_exists(self):
        # A failed delete left it: a person's job, never a forced push.
        with self.assertRaises(rs.RetireError) as ctx:
            rs.default_push(self.work, self.BRANCH, "token")
        self.assertIn("already exists", str(ctx.exception))
        self.assertEqual(self.remote_head(), self.old)

    def test_a_deleted_branch_is_pushed_plainly(self):
        self.delete(self.old)
        rs.default_push(self.work, self.BRANCH, "token")
        self.assertEqual(self.remote_head(), self.fresh)

    def test_no_forced_push_is_left_in_the_source(self):
        import ast
        src = (ROOT / "scripts" / "retire_skill.py").read_text()
        for name in ("replace_lease", "_push"):
            self.assertFalse(hasattr(rs, name), name)
        lease = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.JoinedStr)
                 and any(isinstance(v, ast.Constant) and "--force-with-lease" in v.value
                         for v in n.values)]
        # One lease, on the delete (and its dry-run lines: the withdrawal's
        # and the reopen's retried delete, R7-2).
        self.assertEqual(len(lease), 3)


class WithdrawnLabelTests(unittest.TestCase):
    """The label goes on before anything records or closes the withdrawal;
    without it the pull request stays open, since a closed one without the
    label would decide its subject."""

    STALE = staticmethod(lambda: doc({SKILL: VERDICTS["keep"]}))

    def test_a_missing_label_is_created_and_the_add_retried(self):
        gh = FakeGh(label_fails=1)
        lines = rs.withdraw_stale(self.STALE(), [pr()], "skill", gh)
        repo = rs.REGISTRY_REPO
        add = ["pr", "edit", SKILL_URL, "-R", repo, "--add-label", rs.WITHDRAWN_LABEL]
        self.assertEqual(gh.writes()[:4], [
            ["pr", "merge", SKILL_URL, "-R", repo, "--disable-auto"], add,
            ["label", "create", rs.WITHDRAWN_LABEL, "-R", repo, "--color",
             rs.WITHDRAWN_LABEL_COLOR, "--description", rs.WITHDRAWN_LABEL_DESCRIPTION,
             "--force"], add])
        self.assertTrue(lines[0].startswith("withdrew #41"))
        self.assertIn(["pr", "close", SKILL_URL, "-R", repo], gh.writes())

    def test_the_guidance_label_is_created_in_agent_guidance(self):
        gh = FakeGh(label_fails=1)
        rs.withdraw_stale(doc(guidance={SECTION: VERDICTS["keep"]}), [gpr()], "guidance", gh)
        create = [a for a in gh.writes() if a[:2] == ["label", "create"]]
        self.assertEqual(create[0][3:5], ["-R", rs.GUIDANCE_REPO])

    def assertLeftOpen(self, gh, ctx):
        self.assertFalse(any(a[:2] in (["pr", "close"], ["pr", "comment"]) or a[0] == "issue"
                             for a in gh.writes()))
        self.assertFalse(gh.armed)  # disarmed, open, for the next pass
        self.assertEqual(ctx.exception.lines, [
            f"failed #41: could not add the {rs.WITHDRAWN_LABEL} label, so it is left open"])

    def test_a_label_that_still_fails_leaves_the_pull_request_open(self):
        for kw in ({"label_fails": 2}, {"label_fails": 2, "fail": ["label", "create"]}):
            with self.subTest(**kw):
                gh = FakeGh(**kw)
                with self.assertRaises(rs.WithdrawFailed) as ctx:
                    rs.withdraw_stale(self.STALE(), [pr()], "skill", gh)
                self.assertLeftOpen(gh, ctx)
                self.assertEqual(len([a for a in gh.writes() if "--add-label" in a]), 2)

    def test_a_failure_with_the_label_present_creates_nothing(self):
        gh = FakeGh(label_fails=1, repo_labels=(rs.WITHDRAWN_LABEL,))
        with self.assertRaises(rs.WithdrawFailed) as ctx:
            rs.withdraw_stale(self.STALE(), [pr()], "skill", gh)
        self.assertFalse(any(a[:2] == ["label", "create"] for a in gh.writes()))
        self.assertLeftOpen(gh, ctx)

    def test_an_unreadable_label_list_creates_nothing(self):
        gh = FakeGh(label_fails=1, fail=["label", "list"])
        with self.assertRaises(rs.WithdrawFailed) as ctx:
            rs.withdraw_stale(self.STALE(), [pr()], "skill", gh)
        self.assertFalse(any(a[:2] == ["label", "create"] for a in gh.writes()))
        self.assertLeftOpen(gh, ctx)

    def test_the_list_is_searched_by_the_exact_name(self):
        gh = FakeGh(label_fails=1, repo_labels=(f"{rs.WITHDRAWN_LABEL}-old",))
        rs.withdraw_stale(self.STALE(), [pr()], "skill", gh)
        self.assertTrue(any(a[:2] == ["label", "create"] for a in gh.writes()))

    def test_the_comment_and_issue_say_it_is_a_pause(self):
        gh = FakeGh()
        rs.withdraw_stale(self.STALE(), [pr()], "skill", gh)
        for prefix in (["pr", "comment"], ["issue", "create"]):
            body = next(s for a, s in gh.calls if a[:2] == prefix)
            self.assertIn(f"`{rs.WITHDRAWN_LABEL}`", body)
            self.assertIn("fresh removal pull request", body)
            self.assertNotIn("opens no removal for it again", body)


class IssueBeforeCloseTests(unittest.TestCase):
    """R5-4: the retirement issue is filed (or commented on) before the pull
    request is commented on and closed, so a failure leaves it open."""

    def test_a_failed_issue_leaves_the_pull_request_open(self):
        for fail, issues in ((["issue", "create"], ()), (["issue", "comment"], (issue(7),))):
            with self.subTest(fail=fail):
                gh = FakeGh(fail=fail, issues=issues)
                with self.assertRaises(rs.WithdrawFailed):
                    rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
                self.assertFalse(any(a[:2] in (["pr", "close"], ["pr", "comment"])
                                     for a in gh.writes()))

    def test_a_failed_issue_lookup_leaves_the_pull_request_open(self):
        gh = FakeGh()
        real = gh.__call__

        def lookup_fails(args, stdin=None):
            if args[:2] == ["api", "--paginate"] and "/issues?" in args[2]:
                gh.calls.append((list(args), stdin))
                return "{not json\n"
            return real(args, stdin)

        with self.assertRaises(rs.WithdrawFailed) as ctx:
            rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", lookup_fails)
        # R9-1: the listing is read first for the decline, and its failure is
        # this item's alone, named by type.
        self.assertEqual(ctx.exception.lines, [
            "failed #41: its retirement issues could not be read (JSONDecodeError), so it "
            "is left as it is"])
        self.assertFalse(any(a[:2] in (["pr", "close"], ["pr", "comment"])
                             for a in gh.writes()))

    def test_the_next_pass_withdraws_it(self):
        gh = FakeGh(fail=["issue", "create"])
        with self.assertRaises(rs.WithdrawFailed):
            rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", gh)
        gh.fail = None
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}),
                                  [pr(labels=(rs.AGENT_LABEL, rs.WITHDRAWN_LABEL))],
                                  "skill", gh)
        self.assertTrue(lines[0].startswith("withdrew #41"))
        self.assertEqual(len([a for a in gh.writes() if a[:2] == ["pr", "close"]]), 1)


class GenericIsolationTests(unittest.TestCase):
    """R5-4: any exception, not only RetireError, is one item's failure; its
    text is never printed, only its type."""

    def test_a_value_error_does_not_skip_the_next_item(self):
        second = pr(head=f"{rs.BRANCH_PREFIX}other-skill", number=43,
                    url=f"https://github.com/{rs.REGISTRY_REPO}/pull/43")
        gh = FakeGh()
        real = gh.__call__

        def first_raises(args, stdin=None):
            if args[:2] == ["pr", "view"] and "/pull/41" in args[2]:
                raise ValueError("secret response text")
            return real(args, stdin)

        gates = doc({SKILL: VERDICTS["keep"], "other-skill": VERDICTS["keep"]})
        with self.assertRaises(rs.WithdrawFailed) as ctx:
            rs.withdraw_stale(gates, [pr(), second], "skill", first_raises)
        self.assertEqual(ctx.exception.lines[0], "failed #41: ValueError")
        self.assertTrue(ctx.exception.lines[1].startswith("withdrew #43"))
        self.assertNotIn("secret", str(ctx.exception))

    def test_main_prints_every_line_and_exits_2(self):
        path = Path(tempfile.mkdtemp()) / "gates.json"
        self.addCleanup(lambda: (path.unlink(), path.parent.rmdir()))
        path.write_text(json.dumps(doc({SKILL: VERDICTS["keep"]})))
        gh = FakeGh([pr()])
        real = gh.__call__

        def raises(args, stdin=None):
            if args[:2] == ["pr", "view"]:
                raise KeyError("secret")
            return real(args, stdin)

        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            code = rs.main(["--withdraw-stale", "--gates", str(path)], env=AUTO_ENV,
                           gh=raises, out=out)
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "retire_skill: failed #41: KeyError\n")
        self.assertNotIn("secret", err.getvalue())


class KeepNeedsNoTokenTests(unittest.TestCase):
    """R5-5: a pass that only keeps makes no call with the App token."""

    def test_a_keep_only_pass_exits_0_without_the_token(self):
        path = Path(tempfile.mkdtemp()) / "gates.json"
        self.addCleanup(lambda: (path.unlink(), path.parent.rmdir()))
        # (A labeled one whose verdict supports it is a partial withdrawal,
        # R6-2, so it is not a keep: PartialWithdrawalTests.)
        for labels, gates in (
                ((rs.AGENT_LABEL,), doc({SKILL: VERDICTS["retire+auto"]})),
                ((rs.AGENT_LABEL,), doc({"other-skill": VERDICTS["keep"]})),
                ((rs.AGENT_LABEL, rs.WITHDRAWN_LABEL), doc({"other-skill": VERDICTS["keep"]}))):
            with self.subTest(labels=labels, gates=list(gates["skills"])):
                path.write_text(json.dumps(gates))

                def no_token(args, stdin=None):
                    raise rs.RetireError(f"no {rs.REGISTRY_TOKEN_ENV}")

                out = io.StringIO()
                code = rs.main(["--withdraw-stale", "--gates", str(path)],
                               env=SCHEDULE, gh=FakeGh([pr(labels=labels)]),
                               registry_gh=no_token, out=out)
                self.assertEqual(code, 0)
                self.assertIn("kept #41", out.getvalue())


class RemovedMachineryTests(unittest.TestCase):
    """Round 5's redesign removed the incomplete state, the re-arm and its
    label, and the planner import: incomplete data is stale again."""

    def test_a_roster_add_withdraws_and_nothing_re_arms(self):
        cells = retire()["cells"] + [{"fixture": f, "model": "model-c", "class": "missing",
                                      "reason": "no run on this model"}
                                     for f in ("fx-a", "fx-b")]
        entry = {"reason": "", "cells": cells, **gates_mod._verdict(cells, True)}
        self.assertEqual(entry["verdict"], "insufficient")
        self.assertEqual(rs.removal_support(doc(), entry)[0], "stale")
        self.assertEqual(rs.withdrawal_decision(pr(), doc({SKILL: entry}))["action"], "withdraw")
        for name in ("rearm", "DISARMED_LABEL", "LOOP_COMMIT_EMAILS", "plan_week"):
            self.assertFalse(hasattr(rs, name), name)

    def test_a_section_with_an_unfinished_alone_pair_is_stale(self):
        entry = gretire()
        entry["alone"] = {"verdict": "insufficient",
                          "cells": [cell("fx-a", "model-a", "missing")]}
        self.assertEqual(rs.removal_support(doc(), entry, "guidance")[0], "stale")
        self.assertEqual(rs.removal_support(doc(), entry)[0], "supported")


# ---------------------------------------------------------------------------
# PR #740 round 6.

class LabelReadBackTests(unittest.TestCase):
    """R6-4: the label is read back before anything records or closes the
    withdrawal; an add that exited 0 without landing leaves it open."""

    def noop_label(self, gh):
        real = gh.__call__

        def call(args, stdin=None):
            if "--add-label" in args:
                gh.calls.append((list(args), stdin))
                return ""
            return real(args, stdin)
        return call

    def test_a_label_that_did_not_land_leaves_the_pull_request_open(self):
        gh = FakeGh()
        with self.assertRaises(rs.WithdrawFailed) as ctx:
            rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill",
                              self.noop_label(gh), delete=lambda *a: None)
        self.assertEqual(ctx.exception.lines, [
            f"failed #41: the {rs.WITHDRAWN_LABEL} label is not on #41 after adding it, "
            "so it is left open"])
        self.assertFalse(any(a[:2] in (["pr", "close"], ["pr", "comment"]) or a[0] == "issue"
                             for a in gh.writes()))
        self.assertIn(["pr", "view", SKILL_URL, "-R", rs.REGISTRY_REPO, "--json", "labels",
                       "--jq", ".labels[].name"], [a for a, _ in gh.calls])

    def test_an_unreadable_label_read_back_leaves_it_open(self):
        gh = FakeGh()
        real = gh.__call__

        def call(args, stdin=None):
            if args[:2] == ["pr", "view"] and "labels" in args:
                raise rs.RetireError("gh pr exited 1")
            return real(args, stdin)

        with self.assertRaises(rs.WithdrawFailed):
            rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr()], "skill", call)
        self.assertFalse(any(a[:2] == ["pr", "close"] for a in gh.writes()))


class BranchDeleteActTests(unittest.TestCase):
    """R6-5: after the close, the branch is deleted, leased on the closed
    pull request's head; a failed delete is best effort, named by type."""

    STALE = staticmethod(lambda: doc({SKILL: VERDICTS["keep"]}))

    def test_the_delete_follows_the_close(self):
        gh = FakeGh()
        order = []
        real = gh.__call__

        def call(args, stdin=None):
            if args[:2] == ["pr", "close"]:
                order.append("close")
            return real(args, stdin)

        rs.withdraw_stale(self.STALE(), [pr()], "skill", call,
                          delete=lambda *a: order.append(("delete",) + a))
        self.assertEqual(order, ["close", ("delete", rs.REGISTRY_REPO,
                                           f"{rs.BRANCH_PREFIX}{SKILL}", gh.head)])

    def test_the_guidance_branch_is_deleted_in_agent_guidance(self):
        deletes = []
        rs.withdraw_stale(doc(guidance={SECTION: VERDICTS["keep"]}), [gpr()], "guidance",
                          FakeGh(), delete=lambda *a: deletes.append(a))
        self.assertEqual(deletes[0][:2], (rs.GUIDANCE_REPO,
                                          f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"))

    def test_a_failed_delete_keeps_the_pause_and_names_only_its_type(self):
        for exc in (rs.RetireError("git push exited 1"), ValueError("secret response")):
            with self.subTest(exc=type(exc).__name__):
                def fails(*a, exc=exc):
                    raise exc
                gh = FakeGh()
                lines = rs.withdraw_stale(self.STALE(), [pr()], "skill", gh, delete=fails)
                self.assertEqual(lines, [
                    "withdrew #41: the verdict is keep, not retire; filed its retirement "
                    f"issue; could not delete its branch ({type(exc).__name__})"])
                self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO], gh.writes())

    def test_a_head_that_is_not_a_sha_deletes_nothing(self):
        gh = FakeGh()
        gh.head = "main"
        deletes = []
        lines = rs.withdraw_stale(self.STALE(), [pr()], "skill", gh,
                                  delete=lambda *a: deletes.append(a))
        self.assertEqual(deletes, [])
        self.assertTrue(lines[0].endswith("could not delete its branch (RetireError)"))

    def test_main_passes_its_delete_through(self):
        path = Path(tempfile.mkdtemp()) / "gates.json"
        self.addCleanup(lambda: (path.unlink(), path.parent.rmdir()))
        path.write_text(json.dumps(self.STALE()))
        deletes, out = [], io.StringIO()
        code = rs.main(["--withdraw-stale", "--gates", str(path)], env=AUTO_ENV,
                       gh=FakeGh([pr()]), delete=lambda *a: deletes.append(a), out=out)
        self.assertEqual(code, 0)
        self.assertEqual(len(deletes), 1)
        self.assertIn("deleted its branch", out.getvalue())

    def test_the_dry_run_names_the_leased_delete(self):
        item = {"action": "withdraw", "subject": SKILL, "url": SKILL_URL}
        branch = f"{rs.BRANCH_PREFIX}{SKILL}"
        self.assertIn(["git", "push", f"--force-with-lease=refs/heads/{branch}:<its head>",
                       f"https://github.com/{rs.REGISTRY_REPO}.git", f":refs/heads/{branch}"],
                      rs.would_run("skill", item))

    def test_the_comment_tells_a_person_to_restore_the_branch(self):
        gh = FakeGh()
        rs.withdraw_stale(self.STALE(), [pr()], "skill", gh)
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn("restore the branch from the pull request page, then reopen", body)
        self.assertNotIn("branch is kept", body)


#: The timeline event the loop's own disarm leaves (R7-3).
LOOP_DISABLE = {"event": "auto_merge_disabled", "actor": rs.LOOP_AUTHOR, "body": ""}


class PartialWithdrawalTests(unittest.TestCase):
    """R6-2: in auto mode, an open loop removal whose verdict supports it
    but which is labeled `loop-withdrawn` or disarmed is a withdrawal that
    stopped part way, and is finished as a pause."""

    LABELED = (rs.AGENT_LABEL, rs.WITHDRAWN_LABEL)

    def test_a_labeled_supported_removal_is_withdrawn_in_auto_mode(self):
        d = rs.withdrawal_decision(pr(labels=self.LABELED), doc({SKILL: VERDICTS["retire+auto"]}))
        self.assertEqual((d["action"], d["partial"]), ("withdraw", "labeled"))
        gh = FakeGh(armed=False)
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["retire+auto"]}),
                                  [pr(labels=self.LABELED)], "skill", gh,
                                  delete=lambda *a: None)
        self.assertTrue(lines[0].startswith("withdrew #41: a withdrawal stopped part way"))
        self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO], gh.writes())
        body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn("stopped part way", body)

    def test_a_disarmed_supported_removal_is_withdrawn_in_auto_mode(self):
        gates = doc({SKILL: VERDICTS["retire+auto"]})
        d = rs.withdrawal_decision({**pr(), "armed": False}, gates)
        self.assertEqual((d["action"], d["partial"]), ("withdraw", "disarmed"))
        gh = FakeGh(armed=False)
        gh.timeline = [LOOP_DISABLE]
        rs.withdraw_stale(gates, [{**pr(), "armed": False}], "skill", gh)
        self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO], gh.writes())

    def test_one_armed_after_all_is_kept_with_no_write(self):
        gh = FakeGh(armed=True)
        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["retire+auto"]}),
                                  [{**pr(), "armed": False}], "skill", gh)
        self.assertEqual(lines, ["kept #41: its auto-merge is on after all"])
        self.assertEqual(gh.writes(), [])

    def test_an_armed_unknown_or_newly_opened_one_is_kept(self):
        gates = doc({SKILL: VERDICTS["retire+auto"]}, as_of="20261101T000000Z")
        for record in (pr(), {**pr(), "armed": True}, {**pr(), "armed": None},
                       {**pr(created_at="2026-11-01T00:00:01Z"), "armed": False},
                       {**pr(created_at="2026-11-01T00:00:00Z"), "armed": False},
                       {**pr(created_at=None), "armed": False}):
            with self.subTest(record=record):
                self.assertEqual(rs.withdrawal_decision(record, gates)["action"], "keep")

    def test_proposal_mode_keeps_todays_disarm(self):
        for record in (pr(labels=self.LABELED), {**pr(), "armed": False}):
            with self.subTest(record=record):
                d = rs.withdrawal_decision(record, doc({SKILL: VERDICTS["retire+auto"]},
                                                       mode="proposal"))
                self.assertEqual(d["action"], "disarm")

    def test_unknown_verdicts_never_finish_a_partial_withdrawal(self):
        d = rs.withdrawal_decision(pr(labels=self.LABELED), doc({"other": VERDICTS["keep"]}))
        self.assertEqual(d["action"], "keep")

    def test_the_guidance_target_too(self):
        g = {**gpr(), "labels": list(self.LABELED)}
        d = rs.withdrawal_decision(g, doc(guidance={SECTION: gretire()}), "guidance")
        self.assertEqual((d["action"], d["partial"]), ("withdraw", "labeled"))

    def test_the_listing_reads_auto_merge(self):
        gh = FakeGh()
        rs.removal_prs(gh, "skill")
        self.assertIn("armed: (.auto_merge != null)", gh.calls[0][0][-1])


class PauseCapTests(t70.Base):
    """R6-6: after MAX_LOOP_PAUSES loop pauses the retirement job files or
    updates the proposal issue instead of opening another removal."""

    def test_the_cap_is_three(self):
        self.assertEqual(rs.MAX_LOOP_PAUSES, 3)

    def run_auto(self, closed):
        fake = t70.FakeGitHub(closed=closed)
        code, out, err, fake = t70.Base.run_main(
            self, t70.gates_doc("auto"), "--allow-mode", "auto", "--allow-mode", "proposal",
            env=t70.AUTO_ENV, fake=fake)
        return code, out, err, fake

    def test_three_pauses_file_the_proposal_issue(self):
        code, out, err, fake = self.run_auto([closed_pr(n) for n in (7, 8, 9)])
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.pushes, [])
        self.assertFalse(any(a[:2] == ["pr", "create"] for a in fake.writes()))
        create = [(a, s) for a, s in fake.calls if a[:2] == ["issue", "create"]]
        self.assertEqual(len(create), 1)
        self.assertIn("already withdrawn 3 automatic removal pull requests", create[0][1])
        self.assertIn("auto lowered to proposal", err)

    def test_two_pauses_still_open_a_removal(self):
        code, out, err, fake = self.run_auto([closed_pr(n) for n in (8, 9)])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1)

    def test_a_guidance_section_is_capped_too(self):
        from unittest import mock
        gates = doc(guidance={SECTION: gretire()})
        row = {"file": "agents-md/base.md", "heading": "Example heading"}
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        for count, want in ((2, "guidance-removal"), (3, "create-issue"), (4, "create-issue")):
            with self.subTest(count=count):
                gh = FakeGh(closed=[closed_pr(n, head=head) for n in range(count)])
                with mock.patch.object(rs, "guidance_row", return_value=row):
                    plan = rs.guidance_plan(gates, Path("."), gh,
                                            allowed=("auto", "proposal"))
                self.assertEqual(plan["action"], want)
                if want == "create-issue":
                    self.assertIn(f"withdrawn {count} automatic", plan["body"])


class WithdrawalIssueModeTests(unittest.TestCase):
    """R6-7: the retirement issue says what closing it means in each mode."""

    ITEM = {"subject": SKILL, "url": SKILL_URL, "verdict": "keep", "reason": "r", "why": "w"}

    def test_auto_mode_says_closing_the_issue_declines_nothing(self):
        note = rs.withdrawal_issue(self.ITEM, doc({}), "skill", FakeGh(), None)["comment"]
        self.assertIn("closing this issue declines nothing until the loop has paused 3", note)
        self.assertIn("close the removal pull request yourself", note)
        self.assertNotIn("Otherwise close this issue", note)

    def test_proposal_mode_keeps_the_existing_text(self):
        note = rs.withdrawal_issue(self.ITEM, doc({}, mode="proposal"), "skill", FakeGh(),
                                   None)["comment"]
        self.assertIn("Otherwise close this issue", note)
        self.assertNotIn("declines nothing", note)

    def test_the_guidance_mode_is_its_own(self):
        gates = {**doc({}, mode="proposal"), "guidance": {},
                 "guidance_retirement_mode": "auto"}
        note = rs.withdrawal_issue(self.ITEM, gates, "guidance", FakeGh(), None)["comment"]
        self.assertIn("declines nothing", note)

# ---------------------------------------------------------------------------
# PR #740 round 7.


class CloserAfterCloseTests(unittest.TestCase):
    """R7-1: after its close, the pass reads `closed_by` again. Only the
    loop's own close is a pause; anyone else's decides, keeps the branch and
    gets a correction on the pull request and the retirement issue."""

    STALE = staticmethod(lambda: doc({SKILL: VERDICTS["keep"]}))

    def run_pass(self, closer, issues=(issue(77),), target="skill"):
        gh = FakeGh(issues=issues)
        gh.closer = closer
        deletes = []
        gates = self.STALE() if target == "skill" else doc(guidance={SECTION: VERDICTS["keep"]})
        lines = rs.withdraw_stale(gates, [pr() if target == "skill" else gpr()], target, gh,
                                  delete=lambda *a: deletes.append(a))
        return lines, deletes, gh

    def test_a_person_close_during_the_withdrawal_decides_and_keeps_the_branch(self):
        for closer in ("a-person", rs.ISSUE_AUTHOR, ""):
            with self.subTest(closer=closer):
                lines, deletes, gh = self.run_pass(closer)
                self.assertEqual(deletes, [])
                self.assertTrue(lines[0].startswith("decided #41: someone other than the loop "
                                                    "closed it, so it decides (not a pause)"),
                                lines)
                self.assertIn("corrected its comment; corrected issue #77; kept its branch",
                              lines[0])
                notes = [(a, x) for a, x in gh.calls
                         if x and rs.DECIDED_MARKER.format(subject=SKILL) in x]
                self.assertEqual([a[:3] for a, _ in notes],
                                 [["pr", "comment", SKILL_URL], ["issue", "comment", "77"]])
                self.assertIn("decided", notes[0][1])
                self.assertIn("branch is kept", notes[0][1])
                self.assertFalse(any(a[:3] == ["pr", "view", SKILL_URL] and "headRefOid" in a
                                     for a, _ in gh.calls))

    def test_the_loops_own_close_deletes_the_branch(self):
        lines, deletes, gh = self.run_pass(rs.LOOP_AUTHOR)
        self.assertEqual(len(deletes), 1)
        self.assertTrue(lines[0].startswith("withdrew #41"))
        self.assertFalse(any(x and rs.DECIDED_MARKER.format(subject=SKILL) in x
                             for _, x in gh.calls))

    def test_the_closer_is_read_after_the_close(self):
        lines, deletes, gh = self.run_pass(rs.LOOP_AUTHOR)
        args = [a for a, _ in gh.calls]
        close = args.index(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO])
        read = args.index(["api", f"repos/{rs.REGISTRY_REPO}/issues/41", "--jq",
                           '.closed_by.login // ""'])
        self.assertLess(close, read)

    def test_an_unreadable_closer_keeps_the_branch(self):
        gh = FakeGh()

        def flaky(args, stdin=None):
            if args[0] == "api" and args[1].endswith("/issues/41"):
                raise rs.RetireError("gh api exited 1")
            return gh(args, stdin)

        deletes = []
        lines = rs.withdraw_stale(self.STALE(), [pr()], "skill", flaky,
                                  delete=lambda *a: deletes.append(a))
        self.assertEqual(deletes, [])
        self.assertTrue(lines[0].startswith("withdrew #41"))
        self.assertIn("could not read who closed it, so its branch is kept", lines[0])

    def test_no_open_issue_still_corrects_the_pull_request(self):
        lines, deletes, gh = self.run_pass("a-person", issues=())
        self.assertIn("corrected its comment; could not correct its retirement issue",
                      lines[0])

    def test_the_guidance_pass_too(self):
        lines, deletes, gh = self.run_pass(
            "a-person", issues=(issue(78, subject=SECTION, marker=rs.GUIDANCE_ISSUE_MARKER),),
            target="guidance")
        self.assertEqual(deletes, [])
        self.assertTrue(lines[0].startswith("decided #42"))
        self.assertIn(["api", f"repos/{rs.GUIDANCE_REPO}/issues/42", "--jq",
                       '.closed_by.login // ""'], [a for a, _ in gh.calls])
        self.assertIn("corrected issue #78", lines[0])


class NullCloserTests(unittest.TestCase):
    """R7-6: GitHub returns a null `closed_by` for some closes; such a close
    is not the loop's, so it decides."""

    def test_a_null_closer_decides(self):
        gh = FakeGh(closed=[closed_pr(8, closed_by=""), closed_pr(9)])
        got = rs.closed_removal_prs(gh, t70.SKILL)
        self.assertEqual([p["closed_by"] for p in got], [None, rs.LOOP_AUTHOR])
        decided, paused = rs.deciding(got)
        self.assertEqual([p["number"] for p in decided], [8])
        self.assertEqual([p["number"] for p in paused], [9])

    def test_a_null_closer_stops_the_reopen(self):
        gh = FakeGh(closed=[closed_pr(8, closed_by="", head=f"{rs.GUIDANCE_BRANCH_PREFIX}"
                                                         f"{SECTION}")])
        plan = rs.guidance_plan(doc(guidance={SECTION: gretire()}), Path("."), gh,
                                allowed=("auto",))
        self.assertEqual(plan["action"], "none")
        self.assertIn("already decided", plan["reason"])


class FailedDeleteRetryTests(BranchFixture):
    """R7-2: a branch a withdrawal failed to delete is deleted at the next
    removal, leased on its tip, when that tip is a paused removal's head;
    any other branch is still refused."""

    def test_a_leftover_at_a_paused_head_is_deleted_then_pushed_plainly(self):
        rs.default_push(self.work, self.BRANCH, "token", [SHA_A, self.old])
        self.assertEqual(self.remote_head(), self.fresh)

    def test_a_branch_at_any_other_commit_is_refused(self):
        for heads in ((), [SHA_A], [self.fresh]):
            with self.subTest(heads=heads), self.assertRaises(rs.RetireError) as ctx:
                rs.default_push(self.work, self.BRANCH, "token", heads)
            self.assertIn("already exists", str(ctx.exception))
            self.assertEqual(self.remote_head(), self.old)

    def test_a_branch_already_gone_counts_as_deleted(self):
        self.delete(self.old)
        self.delete(self.old)  # "remote ref does not exist": not a failure
        self.assertIsNone(self.remote_head())

    def test_a_lost_lease_still_fails(self):
        self.delete(self.old)
        _git(self.work, "push", "-q", "origin", f"{self.fresh}:refs/heads/{self.BRANCH}")
        with self.assertRaises(rs.RetireError):
            self.delete(self.old)
        self.assertEqual(self.remote_head(), self.fresh)


class PausedHeadsPlanTests(t70.Base):
    """R7-2: the plan hands the paused removals' heads to the push."""

    def run_auto(self, closed, *extra):
        return ReopenAfterWithdrawalTests.run_auto(self, closed, *extra)

    def test_the_paused_heads_reach_the_push(self):
        code, out, err, fake = self.run_auto([closed_pr(8, sha=SHA_B),
                                              closed_pr(9, sha=SHA_A)])
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.paused_heads, [SHA_A, SHA_B])

    def test_a_head_that_is_not_a_sha_is_dropped(self):
        code, out, err, fake = self.run_auto([closed_pr(8, sha="main"), closed_pr(9)])
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.paused_heads, [])

    def test_the_dry_run_names_the_retried_delete(self):
        code, out, err, _ = self.run_auto([closed_pr(8, sha=SHA_A)], "--dry-run")
        self.assertEqual(code, 0, err)
        plan = json.loads(out)
        self.assertEqual(plan["paused_heads"], [SHA_A])
        branch = f"{rs.BRANCH_PREFIX}{t70.SKILL}"
        self.assertIn(["git", "push", f"--force-with-lease=refs/heads/{branch}:<its tip, if "
                       "one of paused_heads>", "origin", f":refs/heads/{branch}"],
                      plan["would_run"])

    def test_the_guidance_plan_passes_them_too(self):
        from unittest import mock
        withdrawn = closed_pr(head=f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}", sha=SHA_A)
        with mock.patch.object(rs, "guidance_row", return_value={
                "file": "agents-md/base.md", "heading": "Example heading"}):
            plan = rs.guidance_plan(doc(guidance={SECTION: gretire()}), Path("."),
                                    FakeGh(closed=[withdrawn]), allowed=("auto",))
        self.assertEqual(plan["paused_heads"], [SHA_A])

    def test_the_closed_listing_reads_the_head_commit(self):
        self.assertIn("sha: .head.sha", rs.CLOSED_JQ)

    def test_the_comment_and_issue_say_the_branch_will_be_deleted(self):
        item = {"subject": SKILL, "url": SKILL_URL, "verdict": "keep", "reason": "r",
                "why": "w", "removal": None, "removal_reason": None}
        comment = rs.withdrawal_comment(item, doc({}), None)
        note = rs.withdrawal_issue(item, doc({}), "skill", FakeGh(), None)["comment"]
        for text in (comment, note):
            self.assertIn("will be", text)
            self.assertNotIn("branch is deleted", text)
            self.assertNotIn("branch deleted", text)
        self.assertIn("retries it before it pushes", comment)


class PartialDisarmActorTests(unittest.TestCase):
    """R7-3: a disarmed removal is a withdrawal that stopped part way only
    when the loop's own App turned auto-merge off last, and the proposal
    switch never commented on it."""

    GATES = staticmethod(lambda: doc({SKILL: VERDICTS["retire+auto"]}))

    def run_pass(self, timeline):
        gh = FakeGh(armed=False)
        gh.timeline = list(timeline)
        lines = rs.withdraw_stale(self.GATES(), [{**pr(), "armed": False}], "skill", gh,
                                  delete=lambda *a: None)
        return lines, gh

    @staticmethod
    def disable(actor):
        return {"event": "auto_merge_disabled", "actor": actor, "body": ""}

    @staticmethod
    def comment(actor, body):
        return {"event": "commented", "actor": actor, "body": body}

    def test_only_the_loops_latest_disable_finishes_it(self):
        person, loop = self.disable("a-person"), self.disable(rs.LOOP_AUTHOR)
        for timeline, finished in (([loop], True), ([person, loop], True),
                                   ([person], False), ([loop, person], False),
                                   ([], False), ([self.disable("")], False)):
            with self.subTest(timeline=timeline):
                lines, gh = self.run_pass(timeline)
                closed = ["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO] in gh.writes()
                self.assertEqual(closed, finished, lines)
                if not finished:
                    self.assertEqual(gh.writes(), [])
                    self.assertTrue(lines[0].startswith("kept #41"), lines)

    def test_a_removal_the_proposal_switch_disarmed_is_left_alone(self):
        marker = rs.DISARMED_MARKER.format(subject=SKILL)
        loop = self.disable(rs.LOOP_AUTHOR)
        lines, gh = self.run_pass([loop, self.comment(rs.LOOP_AUTHOR, f"{marker}\nbody")])
        self.assertEqual(gh.writes(), [])
        self.assertEqual(lines, ["kept #41: the proposal switch turned its auto-merge off"])
        # A person quoting the marker does not make it the switch's.
        lines, gh = self.run_pass([loop, self.comment("a-person", marker)])
        self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO], gh.writes())
        # The marker of another subject does not either.
        lines, gh = self.run_pass([loop, self.comment(
            rs.LOOP_AUTHOR, rs.DISARMED_MARKER.format(subject="other-skill"))])
        self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO], gh.writes())

    def test_an_unreadable_timeline_is_left_alone(self):
        gh = FakeGh(armed=False)

        def flaky(args, stdin=None):
            if "/timeline?" in " ".join(args):
                raise rs.RetireError("gh api exited 1")
            return gh(args, stdin)

        lines = rs.withdraw_stale(self.GATES(), [{**pr(), "armed": False}], "skill", flaky)
        self.assertEqual(lines, ["kept #41: who turned its auto-merge off cannot be read"])
        self.assertEqual(gh.writes(), [])

    def test_the_timeline_is_read_on_every_page(self):
        lines, gh = self.run_pass([self.disable(rs.LOOP_AUTHOR)])
        read = next(a for a, _ in gh.calls if "/timeline?" in " ".join(a))
        self.assertEqual(read[:3], ["api", "--paginate",
                                    f"repos/{rs.REGISTRY_REPO}/issues/41/timeline?per_page=100"])
        self.assertIn('select(.event == "auto_merge_disabled"', read[-1])

    def test_a_labeled_partial_needs_no_timeline(self):
        gh = FakeGh(armed=False)
        rs.withdraw_stale(self.GATES(), [pr(labels=(rs.AGENT_LABEL, rs.WITHDRAWN_LABEL))],
                          "skill", gh, delete=lambda *a: None)
        self.assertFalse(any("/timeline?" in " ".join(a) for a, _ in gh.calls))
        self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO], gh.writes())

    def test_the_dry_run_names_the_timeline_read(self):
        item = {"action": "withdraw", "subject": SKILL, "url": SKILL_URL, "partial": "disarmed"}
        self.assertIn(rs.withdraw_commands("skill", SKILL_URL)["timeline"],
                      rs.would_run("skill", item))
        self.assertNotIn(rs.withdraw_commands("skill", SKILL_URL)["timeline"],
                         rs.would_run("skill", {**item, "partial": "labeled"}))


class CapNoticeTests(t70.Base):
    """R7-4: the first time the pause cap reaches an open retirement issue,
    the job comments there (a body edit does not notify); a new issue
    mentions the owner in its body; the cap marker keeps it to once."""

    PAUSES = staticmethod(lambda: [closed_pr(n) for n in (7, 8, 9)])

    def run_cap(self, issue_body):
        open_issue = {"number": 77, "body": rs.ISSUE_MARKER.format(skill=t70.SKILL) + "\nx",
                      "author": rs.ISSUE_AUTHOR, "state": "open"}

        class Fake(t70.FakeGitHub):
            def gh(self, args, stdin=None):
                if args[0] == "api" and args[1] == f"repos/{rs.EVALS_REPO}/issues/77":
                    self.calls.append((list(args), stdin))
                    return issue_body + "\n"
                return super().gh(args, stdin)

        fake = Fake(closed=self.PAUSES(), issues=[open_issue])
        return t70.Base.run_main(self, t70.gates_doc("auto"), "--allow-mode", "auto",
                                 "--allow-mode", "proposal", env=t70.AUTO_ENV, fake=fake)

    def test_the_first_cap_comments_on_the_open_issue(self):
        code, out, err, fake = self.run_cap("old body")
        self.assertEqual(code, 0, err)
        comments = [(a, s) for a, s in fake.calls if a[:3] == ["issue", "comment", "77"]]
        self.assertEqual(len(comments), 1)
        self.assertIn(f"@{rs.NOTICE_OWNER}", comments[0][1])
        self.assertIn("stopped opening removals", comments[0][1])
        self.assertIn("close this issue", comments[0][1])
        edit = next(s for a, s in fake.calls if a[:3] == ["issue", "edit", "77"])
        self.assertIn(rs.CAP_MARKER.format(subject=t70.SKILL), edit)
        self.assertIn("commented that the loop stopped opening removals", out)

    def test_a_later_cap_does_not_comment_again(self):
        code, out, err, fake = self.run_cap(rs.CAP_MARKER.format(subject=t70.SKILL))
        self.assertEqual(code, 0, err)
        self.assertFalse(any(a[:2] == ["issue", "comment"] for a, _ in fake.calls))
        self.assertTrue(any(a[:3] == ["issue", "edit", "77"] for a, _ in fake.calls))

    def test_a_new_issue_mentions_the_owner_in_its_body(self):
        fake = t70.FakeGitHub(closed=self.PAUSES())
        code, out, err, fake = t70.Base.run_main(
            self, t70.gates_doc("auto"), "--allow-mode", "auto", "--allow-mode", "proposal",
            env=t70.AUTO_ENV, fake=fake)
        self.assertEqual(code, 0, err)
        body = next(s for a, s in fake.calls if a[:2] == ["issue", "create"])
        self.assertIn(f"@{rs.NOTICE_OWNER}", body)
        self.assertIn(rs.CAP_MARKER.format(subject=t70.SKILL), body)
        self.assertFalse(any(a[:2] == ["issue", "comment"] for a, _ in fake.calls))

    def test_the_dry_run_names_the_comment(self):
        # R8-4: the comment comes before the body edit that records the marker.
        action = {"action": "update-issue", "issue": 77, "cap_comment": "c"}
        self.assertEqual([c[:3] for c in rs.commands(action)],
                         [["gh", "issue", "comment"], ["gh", "issue", "edit"]])
        self.assertEqual(rs.commands(action)[0],
                         ["gh", "issue", "comment", "77", "-R", rs.EVALS_REPO,
                          "--body-file", "-"])
        self.assertEqual(rs.guidance_commands(action), rs.commands(action))
        self.assertEqual(len(rs.commands({**action, "cap_comment": None})), 1)

    def test_a_guidance_section_gets_the_comment_too(self):
        from unittest import mock
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        gh = FakeGh(closed=[closed_pr(n, head=head) for n in range(3)],
                    issues=[issue(78, subject=SECTION, marker=rs.GUIDANCE_ISSUE_MARKER)])
        with mock.patch.object(rs, "guidance_row", return_value={
                "file": "agents-md/base.md", "heading": "Example heading"}):
            plan = rs.guidance_plan(doc(guidance={SECTION: gretire()}), Path("."), gh,
                                    allowed=("auto", "proposal"))
        self.assertEqual((plan["action"], plan["issue"]), ("update-issue", 78))
        self.assertIn(f"@{rs.NOTICE_OWNER}", plan["cap_comment"])
        self.assertIn(rs.CAP_MARKER.format(subject=SECTION), plan["body"])
        out = rs.guidance_execute(plan, None, gh, None, {})
        self.assertIn(["issue", "comment", "78", "-R", rs.EVALS_REPO, "--body-file", "-"],
                      [a for a, _ in gh.calls])
        self.assertIn("commented that the loop stopped", out)

    def test_a_closed_issue_decides_at_the_cap_as_the_text_says(self):
        closed_issue = {"number": 77, "body": rs.ISSUE_MARKER.format(skill=t70.SKILL),
                        "author": rs.ISSUE_AUTHOR, "state": "closed"}
        fake = t70.FakeGitHub(closed=self.PAUSES(), issues=[closed_issue])
        code, out, err, fake = t70.Base.run_main(
            self, t70.gates_doc("auto"), "--allow-mode", "auto", "--allow-mode", "proposal",
            env=t70.AUTO_ENV, fake=fake)
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        note = rs.withdrawal_issue({"subject": SKILL, "url": SKILL_URL, "verdict": "keep",
                                    "reason": "r", "why": "w"}, doc({}), "skill", FakeGh(),
                                   None)["comment"]
        self.assertIn("a closed issue declines the removal", note)
        self.assertNotIn("Closing this issue declines nothing while", note)


class RoundSevenDocTests(unittest.TestCase):
    """R7-5: the docs say what the code does."""

    def test_the_refresh_is_described_as_fast_forward_only_and_leased(self):
        wf = (ROOT / ".github/workflows/loop-pr-refresh.yml").read_text()
        header = wf.split("\non:", 1)[0]
        self.assertNotIn("never a force-push", header)
        self.assertIn("fast-forward only", header)
        agents = (ROOT / "docs" / "workflows.md").read_text(encoding="utf-8")
        row = next(line for line in agents.splitlines()
                   if line.startswith("| `loop-pr-refresh.yml`"))
        self.assertIn("(fast-forward only, leased)", row)
        self.assertNotIn("never a force-push", row)
        self.assertIn("contents: write", row)
        self.assertIn("delete a withdrawn PR's branch", row)

    def test_agents_md_fits_codex(self):
        self.assertLessEqual(len((ROOT / "AGENTS.md").read_bytes()), 32768)

    def test_agents_md_points_at_the_workflow_table(self):
        # The table moved to docs/workflows.md for headroom under Codex's cut.
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("[`docs/workflows.md`](docs/workflows.md)", agents)
        self.assertNotIn("| Workflow | Triggers |", agents)

    def test_local_agent_check_refuses_an_agents_md_codex_would_truncate(self):
        # ci.yml's suite skips a docs-only change, so the size limit is held
        # by .agent-checks/local.sh, which runs on every pull request.
        script = ROOT / ".agent-checks" / "local.sh"
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
                   "GIT_CONFIG_NOSYSTEM": "1"}

            def git(*args):
                subprocess.run(["git", "-C", tmp, *args], check=True, env=env,
                               capture_output=True)

            git("init", "-q")
            results = {}
            for size in (32768, 32769):
                Path(tmp, "AGENTS.md").write_bytes(b"x" * (size - 1) + b"\n")
                git("add", "AGENTS.md")
                git("-c", "user.name=t", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", "commit", "-q", "-m", str(size))
                for paths in (b"AGENTS.md\0", b"README.md\0"):
                    proc = subprocess.run(
                        ["bash", str(script), "pull_request"], cwd=tmp,
                        input=paths, capture_output=True, check=False,
                        env={**env, "AGENT_CHECKS_REV": "HEAD"})
                    results[(size, paths)] = proc.returncode
        self.assertEqual(results[(32768, b"AGENTS.md\0")], 0)
        self.assertEqual(results[(32769, b"AGENTS.md\0")], 1)
        self.assertEqual(results[(32769, b"README.md\0")], 0)

    def test_how_it_works_no_longer_overclaims(self):
        text = " ".join((ROOT / "docs" / "how-it-works.md").read_text().split())
        self.assertNotIn("is still arming is never caught", text)
        self.assertIn("Turning auto-merge off by hand is therefore a hold", text)


# ---------------------------------------------------------------------------
# PR #751 round 8.


class ClosedProposalIssueTests(t70.Base):
    """R8-1: in `auto` mode a closed retirement issue the proposal path filed
    declines the removal, on every path that files one while the mode is
    `auto`; one the withdrawal path filed declines nothing until the cap."""

    def run_gates(self, gates, issues=(), *extra):
        fake = t70.FakeGitHub(issues=list(issues))
        return t70.Base.run_main(self, gates, *extra, env=t70.AUTO_ENV, fake=fake)

    def run_auto(self, issues):
        return self.run_gates(t70.gates_doc("auto"), issues, "--allow-mode", "auto",
                        "--allow-mode", "proposal")

    def filed(self, gates, *extra):
        """The body the proposal path files for `gates`."""
        code, out, err, fake = self.run_gates(gates, (), *extra)
        self.assertEqual(code, 0, err)
        return next(s for a, s in fake.calls if a[:2] == ["issue", "create"])

    def assertDeclined(self, body):
        code, out, err, fake = self.run_auto([t70.issue(900, body, state="closed")])
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        self.assertIn("#900", out)
        self.assertEqual((fake.pushes, fake.writes()), ([], []))

    def test_the_proposal_path_stamps_the_issue_it_files(self):
        body = self.filed(t70.gates_doc("proposal"))
        self.assertIn(rs.PROPOSAL_STAMP, body)
        self.assertNotIn(rs.WITHDRAWAL_STAMP, body)
        self.assertEqual(rs.issue_origin(body), "proposal")

    def test_a_verdict_that_once_allowed_only_a_proposal_now_opens_the_removal(self):
        # Path (a) is gone (Adam, 2026-11-13: every retire is automatic): a
        # `removal: proposal` verdict in auto mode opens the removal, so no
        # proposal issue is filed to close.
        verdicts = t70.gates_doc("auto")["skills"]
        verdicts[t70.SKILL] = {**verdicts[t70.SKILL], "removal": "proposal",
                               "removal_reason": "one cell with headroom"}
        code, out, err, fake = self.run_gates(t70.gates_doc("auto", verdicts), (),
                                              "--allow-mode", "auto", "--allow-mode",
                                              "proposal")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1, out)
        self.assertFalse([a for a, _ in fake.calls if a[:2] == ["issue", "create"]
                          and "Retire skill" in " ".join(a)])

    def test_a_day_without_a_token_then_one_with_it(self):
        # Path (b): --fallback-to-proposal files the issue; the token returns.
        body = self.filed(t70.gates_doc("auto"), "--fallback-to-proposal")
        self.assertIn(rs.NO_CREDENTIAL, body)
        self.assertDeclined(body)

    def test_a_proposal_period_then_the_switch_to_auto(self):
        # Path (c): filed in proposal mode, closed, then the mode is auto.
        self.assertDeclined(self.filed(t70.gates_doc("proposal")))

    def test_an_issue_without_a_stamp_predates_them_and_declines(self):
        self.assertDeclined(rs.ISSUE_MARKER.format(skill=t70.SKILL) + "\nold body")

    def test_a_closed_issue_the_withdrawal_filed_declines_nothing(self):
        item = {"subject": t70.SKILL, "url": SKILL_URL, "verdict": "keep", "reason": "r",
                "why": "w"}
        body = rs.withdrawal_issue(item, doc({}), "skill", FakeGh(), None)["body"]
        self.assertIn(rs.WITHDRAWAL_STAMP, body)
        self.assertNotIn(rs.PROPOSAL_STAMP, body)
        code, out, err, fake = self.run_auto([t70.issue(900, body, state="closed")])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1, out)

    def test_a_closed_proposal_declines_beside_an_open_withdrawal_issue(self):
        item = {"subject": t70.SKILL, "url": SKILL_URL, "verdict": "keep", "reason": "r",
                "why": "w"}
        withdrawn = rs.withdrawal_issue(item, doc({}), "skill", FakeGh(), None)["body"]
        proposal = self.filed(t70.gates_doc("proposal"))
        code, out, err, fake = self.run_auto([t70.issue(900, proposal, state="closed"),
                                              t70.issue(901, withdrawn)])
        self.assertEqual(code, 0, err)
        self.assertIn("#900", out)
        self.assertEqual(fake.pushes, [])

    def test_an_open_proposal_issue_does_not_decline(self):
        code, out, err, fake = self.run_auto([t70.issue(
            900, self.filed(t70.gates_doc("proposal")))])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1, out)

    def test_another_authors_closed_issue_declines_nothing(self):
        body = self.filed(t70.gates_doc("proposal"))
        code, out, err, fake = self.run_auto([t70.issue(900, body, author="someone",
                                                        state="closed")])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1, out)

    def test_withdrawal_comments_keep_the_proposal_stamp(self):
        # The proposal issue is open when a removal is withdrawn: it gets a
        # comment (saying closing it declines), never a body edit, so it is
        # still the proposal once a person closes it.
        proposal = self.filed(t70.gates_doc("proposal"))
        gh = FakeGh(issues=[{"number": 900, "body": proposal, "author": rs.ISSUE_AUTHOR,
                             "state": "open"}])
        rs.withdraw_stale(doc({SKILL: VERDICTS["keep"]}), [pr(head=f"{rs.BRANCH_PREFIX}"
                                                              f"{t70.SKILL}")],
                          "skill", gh, delete=lambda *a: None)
        issue_writes = [(a, s) for a, s in gh.calls if a[0] == "issue"
                        and "900" in a]
        self.assertEqual([a[:2] for a, _ in issue_writes], [["issue", "comment"]])
        self.assertIn("closing it declines the removal", issue_writes[0][1])
        self.assertNotIn("declines nothing", issue_writes[0][1])
        self.assertDeclined(proposal)

    def test_a_withdrawal_issue_says_closing_it_declines_nothing(self):
        item = {"subject": t70.SKILL, "url": SKILL_URL, "verdict": "keep", "reason": "r",
                "why": "w"}
        withdrawn = rs.withdrawal_issue(item, doc({}), "skill", FakeGh(), None)["body"]
        gh = FakeGh(issues=[{"number": 900, "body": withdrawn, "author": rs.ISSUE_AUTHOR,
                             "state": "open"}])
        note = rs.withdrawal_issue(item, doc({}), "skill", gh, None)["comment"]
        self.assertIn("declines nothing until the loop has paused", note)

    def test_a_guidance_section_is_declined_the_same_way(self):
        from unittest import mock
        gates = doc(guidance={SECTION: gretire()})
        filed = rs.guidance_plan(doc(guidance={SECTION: gretire()}, mode="proposal"), None,
                                 FakeGh(), allowed=("proposal",))
        self.assertEqual(filed["action"], "create-issue")
        self.assertIn(rs.PROPOSAL_STAMP, filed["body"])
        item = {"subject": SECTION, "url": GUIDANCE_URL, "verdict": "keep", "reason": "r",
                "why": "w"}
        withdrawn = rs.withdrawal_issue(item, gates, "guidance", FakeGh(), None)["body"]
        self.assertIn(rs.WITHDRAWAL_STAMP, withdrawn)
        legacy = rs.GUIDANCE_ISSUE_MARKER.format(section=SECTION)
        row = {"file": "agents-md/base.md", "heading": "Example heading"}
        for body, want in ((filed["body"], "none"), (legacy, "none"),
                           (withdrawn, "guidance-removal")):
            with self.subTest(want=want, body=body[:60]):
                gh = FakeGh(issues=[{"number": 900, "body": body, "state": "closed",
                                     "author": rs.ISSUE_AUTHOR}])
                with mock.patch.object(rs, "guidance_row", return_value=row):
                    plan = rs.guidance_plan(gates, Path("."), gh, allowed=("auto",))
                self.assertEqual(plan["action"], want)
                if want == "none":
                    self.assertIn("#900", plan["reason"])

    def test_a_shorten_issue_is_not_stamped_as_a_proposal(self):
        self.assertEqual(rs.issue_origin(rs.SHORTEN_ISSUE_MARKER.format(section=SECTION)),
                         "legacy")
        plan = rs.guidance_plan(doc(guidance={SECTION: {**gretire(), "verdict":
                                                        "shorten-or-merge"}}),
                                None, FakeGh())
        self.assertEqual(plan["action"], "create-issue")
        self.assertIn(rs.SHORTEN_ISSUE_MARKER.format(section=SECTION), plan["body"])
        self.assertNotIn(rs.PROPOSAL_STAMP, plan["body"])


class DisarmMarkerOrderTests(unittest.TestCase):
    """R8-2: only a DISARMED_MARKER comment after the latest disable holds a
    disarmed removal; one from an earlier, since re-armed disarm does not."""

    run_pass = PartialDisarmActorTests.run_pass
    GATES = staticmethod(lambda: doc({SKILL: VERDICTS["retire+auto"]}))

    def test_a_marker_before_the_latest_disable_does_not_hold(self):
        d, c = PartialDisarmActorTests.disable, PartialDisarmActorTests.comment
        marker = rs.DISARMED_MARKER.format(subject=SKILL)
        loop = d(rs.LOOP_AUTHOR)
        for timeline, finished in (([loop, c(rs.LOOP_AUTHOR, marker), loop], True),
                                   ([c(rs.LOOP_AUTHOR, marker), loop], True),
                                   ([loop, c(rs.LOOP_AUTHOR, marker)], False),
                                   ([loop, c(rs.LOOP_AUTHOR, marker), loop,
                                     c(rs.LOOP_AUTHOR, marker)], False)):
            with self.subTest(timeline=timeline):
                lines, gh = self.run_pass(timeline)
                closed = ["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO] in gh.writes()
                self.assertEqual(closed, finished, lines)


class MissingDisarmCommentTests(unittest.TestCase):
    """R8-3: a `proposal` pass that finds the loop's disarm with no marker
    after it (the switch's comment failed) posts the marker."""

    GATES = staticmethod(lambda: doc({SKILL: VERDICTS["retire+auto"]}))

    def run_pass(self, timeline, fail_timeline=False):
        gh = FakeGh(armed=False)
        gh.timeline = list(timeline)

        def flaky(args, stdin=None):
            if fail_timeline and "/timeline?" in " ".join(args):
                raise rs.RetireError("gh api exited 1")
            return gh(args, stdin)

        lines = rs.withdraw_stale(doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal"),
                                  [{**pr(), "armed": False}], "skill", flaky)
        return lines, gh

    def comments(self, gh):
        return [s for a, s in gh.calls if a[:2] == ["pr", "comment"]]

    def test_the_missing_marker_is_posted(self):
        lines, gh = self.run_pass([PartialDisarmActorTests.disable(rs.LOOP_AUTHOR)])
        self.assertEqual(len(self.comments(gh)), 1, lines)
        self.assertIn(rs.DISARMED_MARKER.format(subject=SKILL), self.comments(gh)[0])
        self.assertEqual([a[:2] for a in gh.writes()], [["pr", "comment"]])
        self.assertIn("posted the comment an earlier pass could not", lines[0])

    def test_no_comment_when_the_marker_is_there_or_a_person_disarmed(self):
        d, c = PartialDisarmActorTests.disable, PartialDisarmActorTests.comment
        marker = rs.DISARMED_MARKER.format(subject=SKILL)
        for timeline in ([d(rs.LOOP_AUTHOR), c(rs.LOOP_AUTHOR, marker)],
                         [d("a-person")], [], [d(rs.LOOP_AUTHOR), d("a-person")]):
            with self.subTest(timeline=timeline):
                lines, gh = self.run_pass(timeline)
                self.assertEqual(gh.writes(), [], lines)
                self.assertTrue(lines[0].startswith("left #41 open and disarmed"), lines)

    def test_an_unreadable_timeline_posts_nothing(self):
        lines, gh = self.run_pass([PartialDisarmActorTests.disable(rs.LOOP_AUTHOR)],
                                  fail_timeline=True)
        self.assertEqual(gh.writes(), [], lines)

    def test_after_the_comment_an_auto_pass_keeps_it(self):
        lines, gh = self.run_pass([PartialDisarmActorTests.disable(rs.LOOP_AUTHOR)])
        posted = PartialDisarmActorTests.comment(rs.LOOP_AUTHOR, self.comments(gh)[0])
        lines, gh = PartialDisarmActorTests.run_pass(
            self, [PartialDisarmActorTests.disable(rs.LOOP_AUTHOR), posted])
        self.assertEqual(gh.writes(), [])
        self.assertEqual(lines, ["kept #41: the proposal switch turned its auto-merge off"])

    def test_the_dry_run_names_the_timeline_read(self):
        item = {"action": "disarm", "subject": SKILL, "url": SKILL_URL}
        self.assertIn(rs.withdraw_commands("skill", SKILL_URL)["timeline"],
                      rs.would_run("skill", item))


class CapCommentFirstTests(t70.Base):
    """R8-4: the cap's comment is posted before the body edit that records
    CAP_MARKER, so a failed comment is retried on the next run."""

    PAUSES = staticmethod(lambda: [closed_pr(n) for n in (7, 8, 9)])

    def run_failing(self):
        open_issue = {"number": 77, "body": rs.ISSUE_MARKER.format(skill=t70.SKILL) + "\nx",
                      "author": rs.ISSUE_AUTHOR, "state": "open"}

        class Fake(t70.FakeGitHub):
            def gh(self, args, stdin=None):
                if args[0] == "api" and args[1] == f"repos/{rs.EVALS_REPO}/issues/77":
                    self.calls.append((list(args), stdin))
                    return "old body\n"
                if args[:2] == ["issue", "comment"]:
                    self.calls.append((list(args), stdin))
                    raise rs.RetireError("gh issue exited 1")
                return super().gh(args, stdin)

        fake = Fake(closed=self.PAUSES(), issues=[open_issue])
        return t70.Base.run_main(self, t70.gates_doc("auto"), "--allow-mode", "auto",
                                 "--allow-mode", "proposal", env=t70.AUTO_ENV, fake=fake)

    def test_a_failed_comment_leaves_the_body_without_the_marker(self):
        code, out, err, fake = self.run_failing()
        self.assertEqual(code, 2)
        self.assertTrue(any(a[:2] == ["issue", "comment"] for a, _ in fake.calls))
        self.assertFalse(any(a[:2] == ["issue", "edit"] for a, _ in fake.calls))

    def test_the_guidance_comment_comes_first_too(self):
        from unittest import mock
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        gh = FakeGh(closed=[closed_pr(n, head=head) for n in range(3)],
                    issues=[issue(78, subject=SECTION, marker=rs.GUIDANCE_ISSUE_MARKER)])
        with mock.patch.object(rs, "guidance_row", return_value={
                "file": "agents-md/base.md", "heading": "Example heading"}):
            plan = rs.guidance_plan(doc(guidance={SECTION: gretire()}), Path("."), gh,
                                    allowed=("auto", "proposal"))
        self.assertTrue(plan.get("cap_comment"))

        def failing(args, stdin=None):
            gh.calls.append((list(args), stdin))
            if args[:2] == ["issue", "comment"]:
                raise rs.RetireError("gh issue exited 1")
            return ""

        gh.calls = []
        with self.assertRaises(rs.RetireError):
            rs.guidance_execute(plan, None, failing, None, {})
        self.assertEqual([a[:2] for a, _ in gh.calls], [["issue", "comment"]])


class HeldGuidanceRemovalTests(unittest.TestCase):
    """R8-5: a guidance removal a person holds open is a no-op for the act
    step, as for a skill, never exit 2."""

    def test_an_open_guidance_removal_makes_the_pass_wait(self):
        held = {"number": 42, "head": f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}",
                "url": GUIDANCE_URL}
        gh = FakeGh(prs=[held])
        plan = rs.guidance_plan(doc(guidance={SECTION: gretire()}), Path("."), gh,
                                allowed=("auto",))
        self.assertEqual(plan["action"], "none")
        self.assertIn(GUIDANCE_URL, plan["reason"])
        self.assertEqual(rs.guidance_execute(plan, None, gh, None, {}), plan["reason"])
        self.assertEqual(gh.writes(), [])


class RetriedDeleteReReadTests(BranchFixture):
    """R8-6 (mutant 8): a retried delete that "succeeds" but leaves the
    branch still refuses the push; the tip is read again after it."""

    def test_a_branch_the_delete_left_is_still_refused(self):
        from unittest import mock
        with mock.patch.object(rs, "default_delete_branch", lambda *a, **k: None), \
                self.assertRaises(rs.RetireError) as ctx:
            rs.default_push(self.work, self.BRANCH, "token", [self.old])
        self.assertIn("already exists", str(ctx.exception))
        self.assertEqual(self.remote_head(), self.old)


@unittest.skipUnless(__import__("shutil").which("jq"), "jq is not installed")
class TimelineFilterTests(unittest.TestCase):
    """R8-6 (mutant 18): TIMELINE_JQ itself, through real jq, and a fake
    that answers the timeline read by applying the filter the code passes."""

    RAW = [{"event": "labeled", "actor": {"login": "a-person"}},
           {"event": "auto_merge_disabled", "actor": {"login": rs.LOOP_AUTHOR},
            "created_at": "2026-11-01T10:00:00Z"},
           {"event": "commented", "actor": {"login": rs.LOOP_AUTHOR},
            "body": rs.DISARMED_MARKER.format(subject=SKILL) + "\nbody",
            "created_at": "2026-11-01T10:00:00Z"},
           {"event": "auto_merge_enabled", "actor": {"login": "a-person"}},
           {"event": "auto_merge_disabled", "actor": None}]

    @staticmethod
    def jq(filter_, raw):
        return subprocess.run(["jq", "-c", filter_], input=json.dumps(raw),
                              capture_output=True, text=True, check=True).stdout

    def test_the_filter_keeps_disables_and_comments_in_order(self):
        rows = [json.loads(x) for x in self.jq(rs.TIMELINE_JQ, self.RAW).splitlines()]
        self.assertEqual(rows, [
            {"event": "auto_merge_disabled", "actor": rs.LOOP_AUTHOR, "body": "",
             "created_at": "2026-11-01T10:00:00Z"},
            {"event": "commented", "actor": rs.LOOP_AUTHOR,
             "body": rs.DISARMED_MARKER.format(subject=SKILL) + "\nbody",
             "created_at": "2026-11-01T10:00:00Z"},
            {"event": "auto_merge_disabled", "actor": "", "body": "", "created_at": ""}])

    def test_the_switchs_marker_holds_through_the_real_filter(self):
        gh = FakeGh(armed=False)
        raw = self.RAW[1:3]

        def jq_gh(args, stdin=None):
            if args[:2] == ["api", "--paginate"] and "/timeline?" in args[2]:
                gh.calls.append((list(args), stdin))
                return self.jq(args[args.index("--jq") + 1], raw)
            return gh(args, stdin)

        lines = rs.withdraw_stale(PartialDisarmActorTests.GATES(),
                                  [{**pr(), "armed": False}], "skill", jq_gh,
                                  delete=lambda *a: None)
        self.assertEqual(lines, ["kept #41: the proposal switch turned its auto-merge off"])
        self.assertEqual(gh.writes(), [])


class GuidancePushHeadsTests(unittest.TestCase):
    """R8-6 (mutant 21): the guidance removal hands its paused heads to the
    push, so a withdrawal's leftover branch is retried there too."""

    def test_guidance_execute_passes_the_paused_heads(self):
        from unittest import mock
        withdrawn = closed_pr(head=f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}", sha=SHA_A)
        with mock.patch.object(rs, "guidance_row", return_value={
                "file": "agents-md/base.md", "heading": "Example heading"}):
            plan = rs.guidance_plan(doc(guidance={SECTION: gretire()}), Path("."),
                                    FakeGh(closed=[withdrawn]), run_url=t70.RUN_URL,
                                    allowed=("auto",))
        pushed = []
        with mock.patch.object(rs, "guidance_prepare_branch", lambda *a: None), \
                mock.patch.object(rs, "_git", lambda *a: SHA_B + "\n"):
            with self.assertRaises(rs.RetireError):  # FakeGh prints no pull request URL
                rs.guidance_execute(plan, Path("."), FakeGh(),
                                    lambda c, b, heads=(): pushed.append((b, list(heads))),
                                    AUTO_ENV, window_open=lambda tree: True,
                                    review=t70.passing_review)
        self.assertEqual(pushed, [(f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}", [SHA_A])])



class RoundEightDocTests(unittest.TestCase):
    """R8-7: the module docstring and how-it-works say what the code does."""

    def test_the_docstring_names_r7_1_r7_3_and_the_stamps(self):
        doc_ = " ".join(rs.__doc__.split())
        self.assertIn("who closed it is read back (R7-1)", doc_)
        self.assertIn("only after the loop's own close, its branch is deleted", doc_)
        self.assertIn("`loop_disarm_hold`", doc_)
        self.assertIn("no `DISARMED_MARKER` comment of the loop's follows it (R8-2)", doc_)
        self.assertIn("`PROPOSAL_STAMP`", doc_)
        self.assertIn("`WITHDRAWAL_STAMP`", doc_)
        self.assertNotIn("6. its branch is deleted, leased", doc_)

    def test_how_it_works_qualifies_the_closed_issue_for_auto_mode(self):
        text = " ".join((ROOT / "docs" / "how-it-works.md").read_text().split())
        self.assertIn("the skill is not proposed again. In `auto` mode no removal is "
                      "opened for it either", text)
        self.assertIn("closing a retirement issue the withdrawal filed declines nothing", text)
        self.assertNotIn("closing the retirement issue declines nothing until the cap", text)
        self.assertNotIn("the App never left the `proposal` switch's disarm", text)


def arm(actor, when, type_=None):
    """One ARMS_JQ row: an `auto_merge_enabled` event's actor, its account
    type (`account_type` unless given) and its time."""
    return {"actor": actor, "type": account_type(actor) if type_ is None else type_,
            "created_at": when}


def stamped(number, stamp, subject=SKILL, state="closed", marker=rs.ISSUE_MARKER):
    """A bot retirement issue whose body carries `stamp` (or several)."""
    out = issue(number, subject=subject, state=state, marker=marker)
    out["body"] += "\n" + "\n".join(stamp if isinstance(stamp, tuple) else (stamp,))
    return out


class DeclinedWhileOpenTests(unittest.TestCase):
    """R9-1: a person who closes the proposal issue while the loop's removal
    is open declines it: `--withdraw-stale` turns its auto-merge off and
    closes it as a decision (no `loop-withdrawn` label, branch kept), never
    keeps it to merge and never files a withdrawal issue saying closing it
    declines nothing."""

    def run_pass(self, gates, issues, prs=None, target="skill", armed=True):
        gh = FakeGh(issues=issues, armed=armed)
        deletes = []
        lines = rs.withdraw_stale(gates, prs if prs is not None else [pr()], target, gh,
                                  delete=lambda *a: deletes.append(a))
        return lines, gh, deletes

    def assertDeclinedPass(self, lines, gh, deletes, url=SKILL_URL, repo=rs.REGISTRY_REPO,
                           number="900"):
        self.assertTrue(lines[0].startswith("declined #"), lines)
        self.assertIn(f"proposal issue #{number}", lines[0])
        self.assertEqual([a[:3] if a[0] == "issue" else a for a in gh.writes()], [
            ["pr", "merge", url, "-R", repo, "--disable-auto"],
            ["pr", "comment", url, "-R", repo, "--body-file", "-"],
            ["pr", "close", url, "-R", repo],
            ["issue", "comment", number]])
        self.assertEqual(gh.pr_labels, [])
        self.assertEqual(deletes, [])
        self.assertFalse(gh.armed)
        self.assertFalse(any(a[:2] == ["issue", "create"] for a, _ in gh.calls))
        for a, body in gh.calls:
            if a[:2] in (["pr", "comment"], ["issue", "comment"]):
                self.assertNotIn("declines nothing", body)
                self.assertNotIn("reopen", a)

    def test_a_supported_armed_removal_is_closed_as_a_decision(self):
        for stamp in (rs.PROPOSAL_STAMP, ()):  # a legacy issue declines too
            with self.subTest(stamp=stamp):
                issues = [stamped(900, stamp) if stamp else issue(900, state="closed")]
                lines, gh, deletes = self.run_pass(doc({SKILL: VERDICTS["retire+auto"]}),
                                                   issues)
                self.assertDeclinedPass(lines, gh, deletes)
                body = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
                self.assertIn(rs.DECLINED_MARKER.format(subject=SKILL), body)
                self.assertIn(f"{rs.EVALS_REPO}/issues/900", body)
                self.assertIn("not a pause", body)

    def test_without_the_closed_proposal_it_is_kept(self):
        for issues in ([], [stamped(900, rs.PROPOSAL_STAMP, state="open")],
                       [stamped(900, rs.WITHDRAWAL_STAMP)],
                       [{**stamped(900, rs.PROPOSAL_STAMP), "author": "a-person"}]):
            with self.subTest(issues=issues):
                lines, gh, _ = self.run_pass(doc({SKILL: VERDICTS["retire+auto"]}), issues)
                self.assertEqual(lines, ["kept #41: the verdict is still retire with an "
                                         "automatic removal"])
                self.assertEqual(gh.writes(), [])

    def test_a_stale_removal_files_no_declines_nothing_issue(self):
        lines, gh, deletes = self.run_pass(doc({SKILL: VERDICTS["keep"]}),
                                           [stamped(900, rs.PROPOSAL_STAMP)])
        self.assertDeclinedPass(lines, gh, deletes)

    def test_the_proposal_switch_closes_it_too(self):
        lines, gh, deletes = self.run_pass(doc({SKILL: VERDICTS["retire+auto"]},
                                               mode="proposal"),
                                           [stamped(900, rs.PROPOSAL_STAMP)])
        self.assertDeclinedPass(lines, gh, deletes)

    def test_a_removal_already_disarmed_is_closed_without_a_disable(self):
        lines, gh, _ = self.run_pass(doc({SKILL: VERDICTS["retire+auto"]}),
                                     [stamped(900, rs.PROPOSAL_STAMP)],
                                     prs=[{**pr(), "armed": False}], armed=False)
        self.assertTrue(lines[0].startswith("declined #41"), lines)
        self.assertEqual([a[:2] for a in gh.writes()], [
            ["pr", "comment"], ["pr", "close"], ["issue", "comment"]])
        self.assertFalse(any("/timeline?" in " ".join(a) for a, _ in gh.calls))

    def test_a_guidance_section_is_declined_the_same_way(self):
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        lines, gh, deletes = self.run_pass(
            doc(guidance={SECTION: gretire()}),
            [stamped(900, rs.PROPOSAL_STAMP, subject=SECTION,
                     marker=rs.GUIDANCE_ISSUE_MARKER)],
            prs=[pr(head=head, number=42, url=GUIDANCE_URL)], target="guidance")
        self.assertDeclinedPass(lines, gh, deletes, url=GUIDANCE_URL, repo=rs.GUIDANCE_REPO)
        # A skill's closed proposal of the same name declines no section.
        lines, gh, _ = self.run_pass(
            doc(guidance={SECTION: gretire()}),
            [stamped(900, rs.PROPOSAL_STAMP, subject=SECTION)],
            prs=[pr(head=head, number=42, url=GUIDANCE_URL)], target="guidance")
        self.assertTrue(lines[0].startswith("kept #42"), lines)

    def test_the_open_removal_notice_is_closed(self):
        notice = {"number": 77, "body": rs.SKILL_NOTICE_MARKER.format(skill=SKILL),
                  "author": rs.ISSUE_AUTHOR, "state": "open"}
        lines, gh, _ = self.run_pass(doc({SKILL: VERDICTS["retire+auto"]}),
                                     [stamped(900, rs.PROPOSAL_STAMP), notice])
        self.assertIn(["issue", "close", "77", "-R", rs.EVALS_REPO, "--reason", "not planned"],
                      gh.writes())
        self.assertIn("closed its removal notice #77", lines[0])
        note = next(s for a, s in gh.calls if a[:3] == ["issue", "comment", "77"])
        self.assertIn("proposal issue #900 is closed", note)

    def test_an_on_hold_removal_is_still_left_alone(self):
        lines, gh, _ = self.run_pass(doc({SKILL: VERDICTS["retire+auto"]}),
                                     [stamped(900, rs.PROPOSAL_STAMP)],
                                     prs=[pr(labels=(rs.AGENT_LABEL, rs.ON_HOLD_LABEL))])
        self.assertEqual(lines, ["no open removal pull request to withdraw"])
        self.assertEqual(gh.writes(), [])

    def test_the_closed_removal_then_decides_the_subject(self):
        # Closed by the loop without the label, it decides even if the issue
        # is reopened later.
        record = closed_pr(41, labels=(rs.AGENT_LABEL,))
        self.assertEqual(rs.deciding([record]), ([record], []))

    def test_the_dry_run_lists_the_decline_and_its_writes(self):
        gh = FakeGh(prs=[pr()], issues=[stamped(900, rs.PROPOSAL_STAMP)])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gates.json"
            path.write_text(json.dumps(doc({SKILL: VERDICTS["retire+auto"]})))
            out = io.StringIO()
            code = rs.main(["--gates", str(path), "--withdraw-stale", "--dry-run"],
                           env={}, gh=gh, out=out)
        self.assertEqual(code, 0)
        plan = json.loads(out.getvalue())
        self.assertEqual([(i["action"], i["declined"]) for i in plan["withdraw"]],
                         [("decline", 900)])
        self.assertIn(["gh", "pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO],
                      plan["would_run"])
        self.assertEqual(gh.writes(), [])

    def test_the_sequence_round_9_found(self):
        # The proposal issue is open when the verdict firms and the removal
        # opens; the person closes it; the next pass declines the removal,
        # and the retirement job opens nothing after it.
        gates = doc({SKILL: VERDICTS["retire+auto"]})
        lines, _, _ = self.run_pass(gates, [stamped(900, rs.PROPOSAL_STAMP, state="open")])
        self.assertTrue(lines[0].startswith("kept #41"), lines)
        lines, _, _ = self.run_pass(gates, [stamped(900, rs.PROPOSAL_STAMP)])
        self.assertTrue(lines[0].startswith("declined #41"), lines)



class OpenProposalNoteTests(t70.Base):
    """R9-1: when a removal opens while the subject's proposal issue is
    open, that issue (whose body says no removal is opened) gets a comment
    saying closing it still declines the removal; a withdrawal issue does
    not, and a failed comment never fails the opened removal."""

    def run_auto(self, issues, fake_cls=t70.FakeGitHub):
        fake = fake_cls(issues=list(issues))
        return t70.Base.run_main(self, t70.gates_doc("auto"), "--allow-mode", "auto",
                                 "--allow-mode", "proposal", env=t70.AUTO_ENV, fake=fake)

    def proposal(self, number, state="open"):
        body = f"{rs.ISSUE_MARKER.format(skill=t70.SKILL)}\n{rs.PROPOSAL_STAMP}\nbody"
        return t70.issue(number, body, state=state)

    def test_the_open_proposal_is_told(self):
        code, out, err, fake = self.run_auto([self.proposal(900)])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1)
        notes = [(a, s) for a, s in fake.calls if a[:3] == ["issue", "comment", "900"]]
        self.assertEqual(len(notes), 1, fake.calls)
        self.assertIn("Closing this issue still declines it", notes[0][1])
        self.assertIn("pull/999", notes[0][1])
        self.assertIn("commented on its open proposal issue #900", out)
        # It follows the removal notice.
        kinds = [a[:2] for a in fake.writes() if a[0] == "issue"]
        self.assertEqual(kinds, [["issue", "create"], ["issue", "comment"]])

    def assertNoNote(self, issues):
        code, out, err, fake = self.run_auto(issues)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1)
        self.assertFalse(any(a[:2] == ["issue", "comment"] for a in fake.writes()))
        self.assertTrue(out.strip().endswith("filed the removal notice"), out)

    def test_no_issue_gets_no_note(self):
        self.assertNoNote([])

    def test_a_withdrawal_issue_gets_no_note(self):
        item = {"subject": t70.SKILL, "url": SKILL_URL, "verdict": "keep", "reason": "r",
                "why": "w"}
        withdrawn = rs.withdrawal_issue(item, doc({}), "skill", FakeGh(), None)["body"]
        self.assertNoNote([t70.issue(901, withdrawn)])

    def test_a_failed_note_does_not_fail_the_removal(self):
        class Fake(t70.FakeGitHub):
            def gh(self, args, stdin=None):
                if args[:2] == ["issue", "comment"]:
                    self.calls.append((list(args), stdin))
                    raise rs.RetireError("gh issue exited 1")
                return super().gh(args, stdin)

        code, out, err, fake = self.run_auto([self.proposal(900)], Fake)
        self.assertEqual(code, 0, err)
        self.assertIn("#900 (failed)", out)

    def test_the_guidance_removal_tells_its_proposal_too(self):
        found = {"open": [900, 901], "closed": [], "proposals": [900]}
        calls = []
        tail = rs.open_proposal_note(lambda a, s=None: calls.append((a, s)), found, SECTION,
                                     GUIDANCE_URL, "guidance")
        self.assertEqual([a[:3] for a, _ in calls], [["issue", "comment", "900"]])
        self.assertIn("guidance removal pull request", calls[0][1])
        self.assertIn("#900", tail)

class DisarmMarkerTieTests(unittest.TestCase):
    """R9-2: a DISARMED_MARKER created in the same second as the latest
    disable holds, whichever the timeline lists first; time, not position,
    decides when both times are known."""

    run_pass = PartialDisarmActorTests.run_pass
    GATES = staticmethod(lambda: doc({SKILL: VERDICTS["retire+auto"]}))

    @staticmethod
    def at(event, when):
        return {**event, "created_at": when}

    def test_a_same_second_marker_listed_first_still_holds(self):
        d, c = PartialDisarmActorTests.disable, PartialDisarmActorTests.comment
        marker = rs.DISARMED_MARKER.format(subject=SKILL)
        tick = "2026-11-01T10:00:00Z"
        for timeline in ([self.at(c(rs.LOOP_AUTHOR, marker), tick),
                          self.at(d(rs.LOOP_AUTHOR), tick)],
                         [self.at(d(rs.LOOP_AUTHOR), tick),
                          self.at(c(rs.LOOP_AUTHOR, marker), tick)]):
            with self.subTest(timeline=timeline):
                lines, gh = self.run_pass(timeline)
                self.assertEqual(lines, ["kept #41: the proposal switch turned its "
                                         "auto-merge off"])
                self.assertEqual(gh.writes(), [])

    def test_a_marker_from_an_earlier_second_does_not_hold(self):
        d, c = PartialDisarmActorTests.disable, PartialDisarmActorTests.comment
        marker = rs.DISARMED_MARKER.format(subject=SKILL)
        lines, gh = self.run_pass([self.at(c(rs.LOOP_AUTHOR, marker), "2026-11-01T09:59:59Z"),
                                   self.at(d(rs.LOOP_AUTHOR), "2026-11-01T10:00:00Z")])
        self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO], gh.writes())

    def test_a_later_marker_holds_and_a_missing_time_falls_back_to_order(self):
        d, c = PartialDisarmActorTests.disable, PartialDisarmActorTests.comment
        marker = rs.DISARMED_MARKER.format(subject=SKILL)
        for timeline, held in (
                ([self.at(d(rs.LOOP_AUTHOR), "2026-11-01T10:00:00Z"),
                  self.at(c(rs.LOOP_AUTHOR, marker), "2026-11-01T10:00:01Z")], True),
                ([self.at(d(rs.LOOP_AUTHOR), ""),
                  self.at(c(rs.LOOP_AUTHOR, marker), "2026-11-01T10:00:00Z")], True),
                ([self.at(c(rs.LOOP_AUTHOR, marker), "2026-11-01T10:00:00Z"),
                  self.at(d(rs.LOOP_AUTHOR), "")], False)):
            with self.subTest(timeline=timeline):
                lines, gh = self.run_pass(timeline)
                self.assertEqual(gh.writes() == [], held, lines)

    def test_the_filter_reads_each_events_time(self):
        self.assertIn("created_at: (.created_at // \"\")", rs.TIMELINE_JQ)


class RoundNineGapTests(t70.Base):
    """R9-3: the two mutants round 9's mutation run left alive."""

    def run_auto(self, issues, closed=()):
        fake = t70.FakeGitHub(issues=list(issues), closed=list(closed))
        return t70.Base.run_main(self, t70.gates_doc("auto"), "--allow-mode", "auto",
                                 "--allow-mode", "proposal", env=t70.AUTO_ENV, fake=fake)

    def test_both_stamps_read_as_a_proposal(self):
        # M1: the proposal stamp wins, so pasting the withdrawal stamp into a
        # closed proposal does not unblock a removal.
        both = f"{rs.ISSUE_MARKER.format(skill=t70.SKILL)}\n{rs.WITHDRAWAL_STAMP}\n" \
               f"{rs.PROPOSAL_STAMP}\nbody"
        self.assertEqual(rs.issue_origin(both), "proposal")
        code, out, err, fake = self.run_auto([t70.issue(900, both, state="closed")])
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        self.assertIn("#900", out)
        self.assertEqual((fake.pushes, fake.writes()), ([], []))

    def test_a_decline_holds_after_a_pause(self):
        # M7: a closed proposal beside a removal the loop paused still declines.
        body = f"{rs.ISSUE_MARKER.format(skill=t70.SKILL)}\n{rs.PROPOSAL_STAMP}\nbody"
        code, out, err, fake = self.run_auto([t70.issue(900, body, state="closed")],
                                             closed=[closed_pr(8)])
        self.assertEqual(code, 0, err)
        self.assertIn("its proposal issue #900 is closed", out)
        self.assertEqual((fake.pushes, fake.writes()), ([], []))

    def test_a_guidance_decline_holds_after_a_pause_too(self):
        from unittest import mock
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        gh = FakeGh(closed=[closed_pr(8, head=head)],
                    issues=[stamped(900, rs.PROPOSAL_STAMP, subject=SECTION,
                                    marker=rs.GUIDANCE_ISSUE_MARKER)])
        with mock.patch.object(rs, "guidance_row", return_value={
                "file": "agents-md/base.md", "heading": "Example heading"}):
            plan = rs.guidance_plan(doc(guidance={SECTION: gretire()}), Path("."), gh,
                                    allowed=("auto",))
        self.assertEqual((plan["action"], plan.get("issue")), ("none", 900))


class ClosedWithdrawalIssueProposalTests(t70.Base):
    """R9-5: in `auto` mode lowered to a proposal (short of the cap), a closed
    issue the withdrawal path filed decides nothing, so a fresh proposal
    issue is filed for a person to decline; a closed proposal still decides,
    and so does a closed withdrawal issue in `proposal` mode or at the cap."""

    def withdrawn(self, subject=t70.SKILL, target="skill"):
        item = {"subject": subject, "url": SKILL_URL, "verdict": "keep", "reason": "r",
                "why": "w"}
        return rs.withdrawal_issue(item, doc({}), target, FakeGh(), None)["body"]

    def run_gates(self, mode, issues):
        # `auto` lowered by a missing write token (2026-11-13: no verdict is
        # lowered any more), which files the agent route's issue.
        fake = t70.FakeGitHub(issues=list(issues))
        return t70.Base.run_main(self, t70.gates_doc(mode), "--allow-mode", "proposal",
                                 "--fallback-to-proposal", env=t70.AUTO_ENV, fake=fake)

    def test_a_lowered_pass_files_a_fresh_issue(self):
        code, out, err, fake = self.run_gates("auto", [t70.issue(900, self.withdrawn(),
                                                                 state="closed")])
        self.assertEqual(code, 0, err)
        self.assertNotIn("already decided", out)
        create = [s for a, s in fake.calls if a[:2] == ["issue", "create"]]
        self.assertEqual(len(create), 1, out)
        self.assertIn(rs.AGENT_STAMP, create[0])
        self.assertIn(rs.NO_CREDENTIAL, create[0])

    def test_a_closed_proposal_still_decides(self):
        body = f"{rs.ISSUE_MARKER.format(skill=t70.SKILL)}\n{rs.PROPOSAL_STAMP}\nbody"
        code, out, err, fake = self.run_gates("auto", [t70.issue(900, body, state="closed")])
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        self.assertEqual(fake.writes(), [])

    def test_proposal_mode_still_reads_any_closed_issue_as_decided(self):
        code, out, err, fake = self.run_gates("proposal", [t70.issue(900, self.withdrawn(),
                                                                     state="closed")])
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        self.assertEqual(fake.writes(), [])

    def test_at_the_cap_a_closed_withdrawal_issue_decides(self):
        fake = t70.FakeGitHub(closed=[closed_pr(n) for n in (7, 8, 9)],
                              issues=[t70.issue(900, self.withdrawn(), state="closed")])
        code, out, err, fake = t70.Base.run_main(
            self, t70.gates_doc("auto"), "--allow-mode", "auto", "--allow-mode", "proposal",
            env=t70.AUTO_ENV, fake=fake)
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        self.assertEqual((fake.pushes, fake.writes()), ([], []))

    def test_a_guidance_section_in_proposal_mode_is_decided_by_a_closed_issue(self):
        # No guidance retire is lowered from auto any more (2026-11-13), so a
        # closed withdrawal issue decides in proposal mode like any close.
        gates = doc(guidance={SECTION: gretire()}, mode="proposal")
        closed = stamped(900, rs.WITHDRAWAL_STAMP, subject=SECTION,
                         marker=rs.GUIDANCE_ISSUE_MARKER)
        plan = rs.guidance_plan(gates, None, FakeGh(issues=[closed]),
                                allowed=("auto", "proposal"))
        self.assertEqual((plan["action"], plan["issue"]), ("none", 900))


class RoundTenTests(t70.Base):
    """PR #751 round 10: R10-1 (a decline takes `loop-withdrawn` off first),
    R10-2 (any close declines; the comments say reopening does not resume;
    its re-arm comparison became round 12's single rule), R10-3 (the pause cap
    decides on the lowered path too, and no cap comment for a decided
    subject) and R10-6 (the tests mutants 10, 11, 22 and 27 survived)."""

    GATES = staticmethod(lambda: doc({SKILL: VERDICTS["retire+auto"]}))

    def decline_pass(self, gh, prs=None):
        return rs.withdraw_stale(self.GATES(), prs or [pr()], "skill", gh,
                                 delete=lambda *a: None)

    # R10-1 ---------------------------------------------------------------
    def test_a_labeled_removal_loses_the_label_before_it_is_closed(self):
        gh = FakeGh(issues=[stamped(900, rs.PROPOSAL_STAMP)])
        gh.pr_labels = [rs.AGENT_LABEL, rs.WITHDRAWN_LABEL]
        lines = self.decline_pass(gh, [pr(labels=(rs.AGENT_LABEL, rs.WITHDRAWN_LABEL))])
        self.assertTrue(lines[0].startswith("declined #41"), lines)
        writes = [a[:2] if a[0] == "issue" else a for a in gh.writes()]
        repo = rs.REGISTRY_REPO
        self.assertEqual(writes, [
            ["pr", "merge", SKILL_URL, "-R", repo, "--disable-auto"],
            ["pr", "edit", SKILL_URL, "-R", repo, "--remove-label", rs.WITHDRAWN_LABEL],
            ["pr", "comment", SKILL_URL, "-R", repo, "--body-file", "-"],
            ["pr", "close", SKILL_URL, "-R", repo],
            ["issue", "comment"]])
        self.assertEqual(gh.pr_labels, [rs.AGENT_LABEL])
        # So the closed removal decides the subject, as the comment says.
        record = closed_pr(41, labels=gh.pr_labels)
        self.assertFalse(rs.loop_withdrawn(record))
        self.assertEqual(rs.deciding([record]), ([record], []))

    def test_a_label_that_will_not_come_off_leaves_it_open(self):
        for fail, stuck in ((["pr", "edit"], False), (None, True)):
            with self.subTest(fail=fail, stuck=stuck):
                gh = FakeGh(issues=[stamped(900, rs.PROPOSAL_STAMP)], fail=fail)
                gh.pr_labels = [rs.AGENT_LABEL, rs.WITHDRAWN_LABEL]
                gh.unlabel_stuck = stuck
                with self.assertRaises(rs.WithdrawFailed) as ctx:
                    self.decline_pass(gh, [pr(labels=(rs.AGENT_LABEL, rs.WITHDRAWN_LABEL))])
                self.assertIn(rs.WITHDRAWN_LABEL, ctx.exception.lines[0])
                self.assertFalse(any(a[:2] in (["pr", "close"], ["pr", "comment"])
                                     for a in gh.writes()), gh.writes())

    def test_an_unlabeled_decline_makes_no_label_write(self):
        gh = FakeGh(issues=[stamped(900, rs.PROPOSAL_STAMP)])
        self.decline_pass(gh)
        self.assertFalse(any(a[:2] == ["pr", "edit"] for a in gh.writes()))

    # R10-2 ---------------------------------------------------------------
    CLOSED_AT = "2026-11-02T10:00:00Z"

    def rearm_pass(self, arms, closed_at=CLOSED_AT, fail_arms=False):
        gh = FakeGh(issues=[{**stamped(900, rs.PROPOSAL_STAMP), "closed_at": closed_at}])
        gh.timeline = arms
        if fail_arms:
            base = gh

            def gh(args, stdin=None):  # noqa: F811
                if "/timeline?" in " ".join(args):
                    base.calls.append((list(args), stdin))
                    raise rs.RetireError("gh api exited 1")
                return base(args, stdin)
            gh.writes, gh.calls = base.writes, base.calls
        lines = rs.withdraw_stale(self.GATES(), [{**pr(), "armed": True}], "skill", gh,
                                  delete=lambda *a: None)
        return lines, gh

    def test_a_persons_arm_after_the_close_is_left_not_declined(self):
        # Round 13: the latest person action wins, so only an arm strictly
        # later than the close is left (round 12 left one made before the
        # close, or in the same second, too: RoundThirteenTests has those).
        for when in ("2026-11-02T10:00:01Z", "2026-11-03T00:00:00Z"):
            with self.subTest(when=when):
                lines, gh = self.rearm_pass([arm(rs.LOOP_AUTHOR, "2026-11-01T09:00:00Z"),
                                             arm("a-person", when)])
                self.assertEqual(lines, ["left #41 for a person: armed by a person"])
                self.assertEqual(gh.writes(), [])
                self.assertTrue(gh.armed)

    def test_anything_short_of_a_persons_arm_in_force_still_declines(self):
        cases = {
            "the loop armed last": [arm("a-person", "2026-11-02T11:00:00Z"),
                                    arm(rs.LOOP_AUTHOR, "2026-11-02T12:00:00Z")],
            "no arm event": [],
            "arm time unknown": [arm("a-person", "")],
            "an earlier arm's time unknown": [arm(rs.LOOP_AUTHOR, ""),
                                              arm("a-person", "2026-11-02T11:00:00Z")],
            "a tie with the loop's arm": [arm("a-person", "2026-11-02T11:00:00Z"),
                                          arm(rs.LOOP_AUTHOR, "2026-11-02T11:00:00Z")],
            "no actor": [arm("", "2026-11-02T11:00:00Z")],
            "a person's arm before the close": [arm("a-person", "2026-11-02T09:59:59Z")],
            "a person's arm in the close's second": [arm("a-person", self.CLOSED_AT)],
            "a bot's arm after the close": [arm("a-helper[bot]", "2026-11-02T11:00:00Z")],
        }
        for name, arms in cases.items():
            with self.subTest(name):
                lines, gh = self.rearm_pass(arms)
                self.assertTrue(lines[0].startswith("declined #41"), lines)
                self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO], gh.writes())
        lines, gh = self.rearm_pass([], fail_arms=True)
        self.assertTrue(lines[0].startswith("declined #41"), lines)

    def test_the_arms_filter_keeps_only_enables_through_real_jq(self):
        raw = [{"event": "auto_merge_disabled", "actor": {"login": rs.LOOP_AUTHOR},
                "created_at": "2026-11-01T10:00:00Z"},
               {"event": "auto_merge_enabled", "actor": {"login": "a-person"},
                "created_at": "2026-11-02T10:00:00Z"},
               {"event": "auto_merge_enabled", "actor": None}]
        rows = [json.loads(x) for x in TimelineFilterTests.jq(rs.ARMS_JQ, raw).splitlines()]
        self.assertEqual(rows, [{"actor": "a-person", "type": "", "created_at":
                                 "2026-11-02T10:00:00Z"},
                                {"actor": "", "type": "", "created_at": ""}])

    def test_the_close_time_is_read_and_carried(self):
        # Round 13 brought back what round 12 dropped: the listing reads
        # `closed_at` and a decline carries it, for `persons_arm`. The
        # item's own decision is still not carried.
        gh = FakeGh(issues=[{**stamped(900, rs.PROPOSAL_STAMP), "closed_at": self.CLOSED_AT}])
        found = rs.existing_issues(gh, SKILL)
        self.assertIn("closed_at: (.closed_at // \"\")", gh.calls[0][0][-1])
        self.assertEqual(found["closed_at"], {900: self.CLOSED_AT})
        self.assertEqual(rs.declined(found, SKILL, "auto", "skill")["closed_at"],
                         self.CLOSED_AT)
        item = rs.withdraw_plan(self.GATES(), [pr()], "skill", gh)[0]
        self.assertEqual((item["action"], item["closed_at"]), ("decline", self.CLOSED_AT))
        self.assertNotIn("otherwise", item)

    def test_any_close_declines_whatever_its_reason(self):
        for reason in ("completed", "not_planned", None):
            with self.subTest(reason=reason):
                gh = FakeGh(issues=[{**stamped(900, rs.PROPOSAL_STAMP),
                                     "state_reason": reason}])
                self.assertTrue(self.decline_pass(gh)[0].startswith("declined #41"))

    def test_the_comments_say_reopening_does_not_resume(self):
        gh = FakeGh(issues=[stamped(900, rs.PROPOSAL_STAMP)])
        self.decline_pass(gh)
        pr_comment = " ".join(next(s for a, s in gh.calls if a[:2] == ["pr", "comment"]).split())
        issue_comment = " ".join(next(s for a, s in gh.calls
                                      if a[:2] == ["issue", "comment"]).split())
        self.assertIn("reopening the issue does not resume it", pr_comment)
        self.assertNotIn("while that issue is closed", pr_comment)
        self.assertIn("whatever its close reason", pr_comment)
        self.assertIn("reopening this issue does not resume the loop", issue_comment)

    # R10-3 ---------------------------------------------------------------
    def withdrawn_body(self):
        item = {"subject": t70.SKILL, "url": SKILL_URL, "verdict": "keep", "reason": "r",
                "why": "w"}
        return rs.withdrawal_issue(item, doc({}), "skill", FakeGh(), None)["body"]

    def run_capped(self, issues, removal="auto"):
        verdicts = t70.gates_doc("auto")["skills"]
        verdicts[t70.SKILL] = {**verdicts[t70.SKILL], "removal": removal,
                               "removal_reason": "a parked cell"}
        fake = t70.FakeGitHub(closed=[closed_pr(n) for n in (7, 8, 9)], issues=list(issues))
        return t70.Base.run_main(self, t70.gates_doc("auto", verdicts), "--allow-mode",
                                 "auto", "--allow-mode", "proposal", env=t70.AUTO_ENV,
                                 fake=fake)

    def test_at_the_cap_a_lowered_verdict_files_nothing(self):
        capped = self.withdrawn_body() + rs.cap_note(t70.SKILL, 3)
        code, out, err, fake = self.run_capped([t70.issue(900, capped, state="closed")],
                                               removal="proposal")
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        self.assertEqual((fake.pushes, fake.writes()), ([], []))

    def test_short_of_the_cap_a_lowered_verdict_still_files_a_fresh_issue(self):
        verdicts = t70.gates_doc("auto")["skills"]
        verdicts[t70.SKILL] = {**verdicts[t70.SKILL], "removal": "proposal",
                               "removal_reason": "a parked cell"}
        fake = t70.FakeGitHub(closed=[closed_pr(n) for n in (7, 8)],
                              issues=[t70.issue(900, self.withdrawn_body(), state="closed")])
        code, out, err, fake = t70.Base.run_main(
            self, t70.gates_doc("auto", verdicts), "--allow-mode", "auto", "--allow-mode",
            "proposal", env=t70.AUTO_ENV, fake=fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(len([a for a in fake.writes() if a[:2] == ["issue", "create"]]), 1)

    def test_no_cap_comment_for_a_subject_already_declined(self):
        capped = self.withdrawn_body() + rs.cap_note(t70.SKILL, 3)
        code, out, err, fake = self.run_capped([t70.issue(900, capped, state="closed"),
                                                t70.issue(901, self.withdrawn_body())])
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        self.assertIn("#900 is closed", out)
        self.assertEqual((fake.pushes, fake.writes()), ([], []))

    def test_the_guidance_cap_decides_on_both_paths(self):
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        paused = [closed_pr(n, head=head) for n in (7, 8, 9)]
        closed = stamped(900, rs.WITHDRAWAL_STAMP, subject=SECTION,
                         marker=rs.GUIDANCE_ISSUE_MARKER)
        # R11-1: beside the closed issue, the open one gets the cap comment
        # once; with the comment recorded on it, the closed issue decides.
        opened = stamped(901, rs.WITHDRAWAL_STAMP, subject=SECTION,
                         marker=rs.GUIDANCE_ISSUE_MARKER, state="open")
        auto = rs.guidance_plan(doc(guidance={SECTION: gretire()}), None,
                                FakeGh(issues=[closed, opened], closed=paused),
                                allowed=("auto", "proposal"))
        self.assertEqual((auto["action"], auto["issue"]), ("update-issue", 901))
        self.assertIn(f"@{rs.NOTICE_OWNER}", auto["cap_comment"])
        opened = {**opened, "body": opened["body"] + "\n" + rs.cap_note(SECTION, 3)}
        auto = rs.guidance_plan(doc(guidance={SECTION: gretire()}), None,
                                FakeGh(issues=[closed, opened], closed=paused),
                                allowed=("auto", "proposal"))
        self.assertEqual((auto["action"], auto["issue"]), ("none", 900))
        self.assertNotIn("cap_comment", auto)

    # R10-6 ---------------------------------------------------------------
    def test_mutant_10_a_decline_with_another_repositorys_url_is_refused(self):
        bad = {**pr(), "url": "https://github.com/Other/repo/pull/41"}
        with self.assertRaises(rs.RetireError):
            rs.withdraw_plan(self.GATES(), [bad], "skill",
                             FakeGh(issues=[stamped(900, rs.PROPOSAL_STAMP)]))

        def failing(args, stdin=None):
            raise rs.RetireError("gh api exited 1")
        with self.assertRaises(rs.RetireError):  # an unreadable item too
            rs.withdraw_plan(self.GATES(), [bad], "skill", failing)

    def test_mutant_11_a_decline_only_pass_outside_actions_refuses(self):
        gh = FakeGh(prs=[{**pr(), "armed": True}], issues=[stamped(900, rs.PROPOSAL_STAMP)])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gates.json"
            path.write_text(json.dumps(self.GATES()))
            err = io.StringIO()
            with redirect_stderr(err):
                code = rs.main(["--gates", str(path), "--withdraw-stale"], env=SCHEDULE,
                               gh=gh, out=io.StringIO())
        self.assertEqual(code, 2)
        self.assertIn("auto mode acts only in GitHub Actions", err.getvalue())
        self.assertEqual(gh.writes(), [])

    def test_mutant_22_the_guidance_removal_notes_its_open_proposal(self):
        from unittest import mock
        base = FakeGh(issues=[stamped(900, rs.PROPOSAL_STAMP, subject=SECTION,
                                      marker=rs.GUIDANCE_ISSUE_MARKER, state="open")])

        edited = {}

        def gh(args, stdin=None):
            if args[:2] == ["pr", "create"]:
                base.calls.append((list(args), stdin))
                edited["body"] = stdin  # opened with the review's section (#917)
                return GUIDANCE_URL + "\n"
            if args[:2] == ["pr", "view"] and "body" in args:
                return edited.get("body", "") + "\n"
            return base(args, stdin)

        action = {"action": "guidance-removal", "section": SECTION,
                  "branch": f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}", "title": "t",
                  "body": "b", "notice": {"title": "n", "body": "{removal_pr}"},
                  "run_url": t70.RUN_URL, "verdict": "retire", "file": "agents-md/base.md",
                  "heading": "Example heading"}
        with mock.patch.object(rs, "guidance_prepare_branch"), \
                mock.patch.object(rs, "_git", return_value="a" * 40 + "\n"):
            out = rs.guidance_execute(action, Path("."), gh, lambda *a: None, AUTO_ENV, gh,
                                       window_open=lambda tree: True,
                                       review=t70.passing_review)
        self.assertIn("commented on its open proposal issue #900", out)
        note = next(s for a, s in base.calls if a[:3] == ["issue", "comment", "900"])
        self.assertIn("guidance removal pull request", note)

    def test_mutant_27_an_unreadable_issue_list_is_named_not_raised(self):
        def failing(args, stdin=None):
            raise rs.RetireError("gh api exited 1")
        self.assertEqual(rs._proposal_note(failing, "m", SKILL, SKILL_URL, "skill"),
                         ", and could not read its proposal issue")


class ArmsGh(FakeGh):
    """FakeGh whose timeline holds raw events and answers each timeline read
    with what its filter keeps, as the real jq would: ARMS_JQ the
    `auto_merge_enabled` events, TIMELINE_JQ the disables and comments."""

    def __call__(self, args, stdin=None):
        if args[:2] == ["api", "--paginate"] and "/timeline?" in args[2]:
            self.calls.append((list(args), stdin))
            if rs.ARMS_JQ in args:
                rows = [{"actor": e.get("actor", ""), "type": e.get("type", ""),
                         "created_at": e.get("created_at", "")}
                        for e in self.timeline if e.get("event") == "auto_merge_enabled"]
            else:
                rows = [{"event": e["event"], "actor": e.get("actor", ""),
                         "body": e.get("body", ""), "created_at": e.get("created_at", "")}
                        for e in self.timeline
                        if e.get("event") in ("auto_merge_disabled", "commented")]
            return "".join(json.dumps(r) + "\n" for r in rows)
        return super().__call__(args, stdin)


def account_type(actor):
    """The account type GitHub gives `actor`: an App's `[bot]` login is a
    `Bot`, no login has none, anyone else here is a `User` (round 13)."""
    return "" if not actor else "Bot" if actor.endswith("[bot]") else "User"


def event(kind, actor, when, body="", type_=None):
    return {"event": kind, "actor": actor, "created_at": when, "body": body,
            "type": account_type(actor) if type_ is None else type_}


class RoundElevenTests(t70.Base):
    """PR #751 round 11 (skills-evals#758): R11-1 (the cap comment is posted
    once on the open issue, even beside a closed one), R11-2 and R11-3 (a
    person's re-arm, now round 12's single rule: these tests were rewritten
    for it) and R11-4 (mutants 15 and 25)."""

    CLOSED_AT = "2026-11-02T10:00:00Z"
    LOOP_ARM = event("auto_merge_enabled", rs.LOOP_AUTHOR, "2026-11-01T08:00:00Z")
    LOOP_OFF = event("auto_merge_disabled", rs.LOOP_AUTHOR, "2026-11-02T09:00:00Z")
    REARM = event("auto_merge_enabled", "a-person", "2026-11-02T10:00:01Z")

    # R11-1 ---------------------------------------------------------------
    withdrawn_body = RoundTenTests.withdrawn_body

    def run_capped(self, issues, bodies):
        class Fake(t70.FakeGitHub):
            def gh(self, args, stdin=None):
                if args[0] == "api" and args[1].startswith(f"repos/{rs.EVALS_REPO}/issues/") \
                        and args[1].rsplit("/", 1)[1] in bodies:
                    self.calls.append((list(args), stdin))
                    return bodies[args[1].rsplit("/", 1)[1]] + "\n"
                return super().gh(args, stdin)

        fake = Fake(closed=[closed_pr(n) for n in (7, 8, 9)], issues=list(issues))
        return t70.Base.run_main(self, t70.gates_doc("auto"), "--allow-mode", "auto",
                                 "--allow-mode", "proposal", env=t70.AUTO_ENV, fake=fake)

    def test_the_cap_comment_reaches_the_open_issue_beside_a_closed_one(self):
        # The person closed #900 before the cap, when it declined nothing;
        # #901 is the next withdrawal's issue.
        open_body = self.withdrawn_body()
        code, out, err, fake = self.run_capped(
            [t70.issue(900, self.withdrawn_body(), state="closed"), t70.issue(901, open_body)],
            {"901": open_body})
        self.assertEqual(code, 0, err)
        comments = [s for a, s in fake.calls if a[:3] == ["issue", "comment", "901"]]
        self.assertEqual(len(comments), 1, out)
        self.assertIn(f"@{rs.NOTICE_OWNER}", comments[0])
        self.assertIn("stopped opening removals", comments[0])
        edit = next(s for a, s in fake.calls if a[:3] == ["issue", "edit", "901"])
        self.assertIn(rs.CAP_MARKER.format(subject=t70.SKILL), edit)
        self.assertEqual(fake.pushes, [])

    def test_once_the_comment_is_out_the_closed_issue_decides_with_no_write(self):
        capped = self.withdrawn_body() + rs.cap_note(t70.SKILL, 3)
        code, out, err, fake = self.run_capped(
            [t70.issue(900, self.withdrawn_body(), state="closed"), t70.issue(901, capped)],
            {"901": capped})
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        self.assertIn("#900 is closed", out)
        self.assertEqual((fake.pushes, fake.writes()), ([], []))

    def test_with_no_open_issue_nothing_is_posted(self):
        code, out, err, fake = self.run_capped(
            [t70.issue(900, self.withdrawn_body(), state="closed")], {})
        self.assertEqual(code, 0, err)
        self.assertIn("already decided", out)
        self.assertEqual((fake.pushes, fake.writes()), ([], []))

    def test_cap_owed_reads_every_issue_of_the_subject(self):
        self.assertTrue(rs.cap_owed({"open": [901], "closed": [900], "capped": []}))
        self.assertFalse(rs.cap_owed({"open": [901], "closed": [900], "capped": [900]}))
        self.assertFalse(rs.cap_owed({"open": [901], "closed": [], "capped": [901]}))
        self.assertFalse(rs.cap_owed({"open": [], "closed": [900], "capped": []}))
        gh = FakeGh(issues=[{**stamped(900, rs.WITHDRAWAL_STAMP),
                             "body": stamped(900, rs.WITHDRAWAL_STAMP)["body"]
                             + rs.cap_note(SKILL, 3)},
                            stamped(901, rs.WITHDRAWAL_STAMP, state="open")])
        self.assertEqual(rs.existing_issues(gh, SKILL)["capped"], [900])

    def test_the_docs_no_longer_say_the_person_was_asked_before(self):
        src = Path(rs.__file__).read_text()
        self.assertNotIn("asks the person again", src)
        self.assertNotIn("since the cap\n    comment told the person", src)

    # R11-2 ---------------------------------------------------------------
    def pass_with(self, gates, timeline, closed_issue, armed=True):
        issues = [{**stamped(900, rs.PROPOSAL_STAMP), "closed_at": self.CLOSED_AT}] \
            if closed_issue else []
        gh = ArmsGh(issues=issues, armed=armed)
        gh.timeline = list(timeline)
        lines = rs.withdraw_stale(gates, [{**pr(), "armed": armed}], "skill", gh,
                                  delete=lambda *a: None)
        return lines, gh

    LEFT = ["left #41 for a person: armed by a person"]

    def assertLeftEitherWay(self, gates, timeline):
        # Round 12 (was R11-2's "the same as without the issue"): a person's
        # arm in force is left alone with or without a closed issue.
        for closed_issue in (True, False):
            lines, gh = self.pass_with(gates, timeline, closed_issue)
            self.assertEqual(lines, self.LEFT, closed_issue)
            self.assertEqual(gh.writes(), [])
            self.assertTrue(gh.armed)

    def test_a_stale_verdict_leaves_a_persons_arm(self):
        self.assertLeftEitherWay(doc({SKILL: VERDICTS["keep"]}), [self.LOOP_ARM, self.REARM])

    def test_the_proposal_switch_leaves_a_persons_arm(self):
        # Re-armed with no disable of the loop's in between: still a person's
        # arm in force (R11-3's `switch_rearm` disarmed this one).
        gates = doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal")
        self.assertLeftEitherWay(gates, [self.LOOP_ARM, self.REARM])

    def test_a_supported_one_in_auto_mode_has_no_write_either_way(self):
        gates = doc({SKILL: VERDICTS["retire+auto"]})
        lines, gh = self.pass_with(gates, [self.LOOP_ARM, self.REARM], True)
        self.assertEqual(lines, self.LEFT)
        lines, bare = self.pass_with(gates, [self.LOOP_ARM, self.REARM], False)
        self.assertTrue(lines[0].startswith("kept #41"), lines)
        self.assertEqual((gh.writes(), bare.writes()), ([], []))

    # R11-3 ---------------------------------------------------------------
    PROPOSAL = staticmethod(lambda: doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal"))

    def test_a_persons_rearm_after_the_switch_is_left_armed(self):
        lines, gh = self.pass_with(self.PROPOSAL(), [self.LOOP_ARM, self.LOOP_OFF,
                                                     self.REARM], False)
        self.assertEqual(lines, self.LEFT)
        self.assertEqual(gh.writes(), [])
        self.assertTrue(gh.armed)
        # The same, with the person's own hold and re-arm in between (R12-2:
        # `switch_rearm` disarmed this one).
        lines, gh = self.pass_with(self.PROPOSAL(), [
            self.LOOP_ARM, self.LOOP_OFF,
            event("auto_merge_enabled", "a-person", "2026-11-02T09:30:00Z"),
            event("auto_merge_disabled", "a-person", "2026-11-02T09:40:00Z"),
            self.REARM], False)
        self.assertEqual((lines, gh.writes()), (self.LEFT, []))

    def test_anything_short_of_a_persons_arm_in_force_is_disarmed(self):
        # Round 12 (was "short of a later person's re-arm"): only who armed it
        # last counts, so "no loop disable", "re-armed before the loop's
        # disable", "same second" and "disable time unknown" left this list.
        cases = {
            "the loop's own arm only": [self.LOOP_ARM],
            "the loop armed last": [self.LOOP_OFF, self.REARM,
                                    event("auto_merge_enabled", rs.LOOP_AUTHOR,
                                          "2026-11-02T11:00:00Z")],
            "arm time unknown": [self.LOOP_OFF, {**self.REARM, "created_at": ""}],
            "a tie with the loop's arm": [self.REARM, {**self.LOOP_ARM,
                                                       "created_at": self.REARM["created_at"]}],
            "no arm event": [self.LOOP_OFF],
        }
        for name, timeline in cases.items():
            with self.subTest(name):
                lines, gh = self.pass_with(self.PROPOSAL(), timeline, False)
                self.assertTrue(lines[0].startswith("disarmed #41"), lines)
                self.assertFalse(gh.armed)

    def test_an_unreadable_timeline_is_disarmed(self):
        gh = ArmsGh()

        def flaky(args, stdin=None):
            if "/timeline?" in " ".join(args):
                raise rs.RetireError("gh api exited 1")
            return gh(args, stdin)

        lines = rs.withdraw_stale(self.PROPOSAL(), [{**pr(), "armed": True}], "skill", flaky)
        self.assertTrue(lines[0].startswith("disarmed #41"), lines)

    def test_a_stale_verdict_in_proposal_mode_withdraws_only_the_loops_arm(self):
        gates = doc({SKILL: VERDICTS["keep"]}, mode="proposal")
        lines, gh = self.pass_with(gates, [self.LOOP_ARM, self.LOOP_OFF, self.REARM], False)
        self.assertEqual(lines, self.LEFT)
        lines, gh = self.pass_with(gates, [self.LOOP_ARM], False)
        self.assertTrue(lines[0].startswith("withdrew #41"), lines)

    def test_the_dry_run_names_both_timeline_reads(self):
        c = rs.withdraw_commands("skill", SKILL_URL)
        listing = rs.would_run("skill", {"action": "disarm", "subject": SKILL,
                                         "url": SKILL_URL})
        self.assertLess(listing.index(c["timeline"]), listing.index(c["merge"]))
        self.assertLess(listing.index(c["arms"]), listing.index(c["merge"]))

    def test_the_docs_say_a_hand_rearm_lasts(self):
        text = " ".join((ROOT / "docs" / "how-it-works.md").read_text().split())
        self.assertIn("that is a person's arm in force (above), which the switch leaves "
                      "armed", text)

    # R11-4 ---------------------------------------------------------------
    def test_mutant_15_a_rearm_then_a_hold_is_declined(self):
        # A person re-armed after the close, then turned auto-merge off again:
        # unarmed, the re-arm is not read and the close declines it.
        lines, gh = self.pass_with(doc({SKILL: VERDICTS["retire+auto"]}), [
            self.LOOP_ARM, self.REARM,
            event("auto_merge_disabled", "a-person", "2026-11-02T10:00:05Z")], True,
            armed=False)
        self.assertTrue(lines[0].startswith("declined #41"), lines)
        self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO], gh.writes())
        self.assertFalse(any(rs.ARMS_JQ in a for a, _ in gh.calls))

    def test_mutant_25_the_decline_dry_run_names_the_unlabel_and_its_read_back(self):
        c = rs.withdraw_commands("skill", SKILL_URL)
        listing = rs.would_run("skill", {"action": "decline", "subject": SKILL,
                                         "url": SKILL_URL, "declined": 900})
        self.assertEqual(listing[:10], [c["state"], c["view"], c["arms"], c["merge"],
                                        c["view"], c["pr_labels"], c["unlabel"],
                                        c["pr_labels"], c["comment"], c["close"]])
        self.assertIn("--remove-label", c["unlabel"])


class IssueStoreGitHub(t70.FakeGitHub):
    """t70's fake whose skills-evals issues keep the bodies `issue edit`
    writes, and whose body read (`cap_notice`) returns them, so one pass's
    writes are what the next pass reads (R12-1)."""

    def _issue(self, n):
        return next(i for i in self.issues if i["number"] == int(n))

    def gh(self, args, stdin=None):
        if args[:2] == ["issue", "edit"]:
            self.calls.append((list(args), stdin))
            self._issue(args[2])["body"] = stdin
            return ""
        if args[0] == "api" and args[1].startswith(f"repos/{rs.EVALS_REPO}/issues/"):
            self.calls.append((list(args), stdin))
            return self._issue(args[1].rsplit("/", 1)[1])["body"] + "\n"
        return super().gh(args, stdin)


class RoundTwelveTests(t70.Base):
    """PR #759 round 12 (skills-evals#758): one rule for a person's arm
    (R12-2 to R12-5): a removal armed now whose latest `auto_merge_enabled`
    event is someone's other than LOOP_AUTHOR is left for that person by
    every action and refreshed; anything else falls back to the action. And
    R12-1: a pass lowered to a proposal at the cap keeps CAP_MARKER, so the
    cap comment is posted once."""

    LOOP_ARM = event("auto_merge_enabled", rs.LOOP_AUTHOR, "2026-11-01T08:00:00Z")
    LOOP_OFF = event("auto_merge_disabled", rs.LOOP_AUTHOR, "2026-11-02T09:00:00Z")
    ARM = event("auto_merge_enabled", "a-person", "2026-11-02T10:00:00Z")
    LEFT = ["left #41 for a person: armed by a person"]
    HEAD = f"{rs.BRANCH_PREFIX}{SKILL}"

    #: (name, gates, a closed proposal issue, labels, what the pass does
    #: without a person's arm)
    ACTIONS = (
        ("decline", lambda: doc({SKILL: VERDICTS["retire+auto"]}), True, (rs.AGENT_LABEL,),
         "declined #41"),
        ("stale verdict", lambda: doc({SKILL: VERDICTS["keep"]}), False, (rs.AGENT_LABEL,),
         "withdrew #41"),
        ("stale verdict, issue closed", lambda: doc({SKILL: VERDICTS["keep"]}), True,
         (rs.AGENT_LABEL,), "declined #41"),
        ("proposal switch", lambda: doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal"),
         False, (rs.AGENT_LABEL,), "disarmed #41"),
        ("stopped withdrawal", lambda: doc({SKILL: VERDICTS["retire+auto"]}), False,
         (rs.AGENT_LABEL, rs.WITHDRAWN_LABEL), "withdrew #41"),
    )

    #: Before ARM: a person's arm after the close wins over it (round 13).
    CLOSED_AT = "2026-11-02T09:30:00Z"

    def one_pass(self, gates, timeline, closed_issue, labels=(rs.AGENT_LABEL,), armed=True,
                 gh=None):
        closed = {**stamped(900, rs.PROPOSAL_STAMP), "closed_at": self.CLOSED_AT}
        gh = gh or ArmsGh(issues=[closed] if closed_issue else [], armed=armed)
        gh.timeline = list(timeline)
        gh.pr_labels = list(labels)
        lines = rs.withdraw_stale(gates, [{**pr(labels=labels), "armed": armed}], "skill", gh,
                                  delete=lambda *a: None)
        return lines, gh

    def test_a_persons_arm_is_left_by_every_action(self):
        for name, gates, closed_issue, labels, _ in self.ACTIONS:
            for timeline in ([self.LOOP_ARM, self.ARM],
                             [self.LOOP_ARM, self.LOOP_OFF, self.ARM],
                             [self.LOOP_ARM, event("auto_merge_disabled", "a-person",
                                                   "2026-11-02T09:00:00Z"), self.ARM]):
                with self.subTest(name, timeline=len(timeline)):
                    lines, gh = self.one_pass(gates(), timeline, closed_issue, labels)
                    self.assertEqual(lines, self.LEFT)
                    self.assertEqual(gh.writes(), [])
                    self.assertTrue(gh.armed)

    def test_the_loops_arm_falls_back_to_the_action(self):
        for name, gates, closed_issue, labels, want in self.ACTIONS:
            for timeline in ([self.LOOP_ARM], [self.ARM, {**self.LOOP_ARM,
                                                          "created_at": "2026-11-03T00:00:00Z"}]):
                with self.subTest(name, timeline=timeline):
                    lines, gh = self.one_pass(gates(), timeline, closed_issue, labels)
                    self.assertTrue(lines[0].startswith(want), lines)
                    self.assertFalse(gh.armed)

    def test_an_unreadable_timeline_falls_back_to_the_action(self):
        for name, gates, closed_issue, labels, want in self.ACTIONS:
            with self.subTest(name):
                base = ArmsGh(issues=[stamped(900, rs.PROPOSAL_STAMP)] if closed_issue else [])
                base.timeline, base.pr_labels = [self.LOOP_ARM, self.ARM], list(labels)

                def flaky(args, stdin=None):
                    if rs.ARMS_JQ in args:
                        raise rs.RetireError("gh api exited 1")
                    return base(args, stdin)

                lines = rs.withdraw_stale(gates(), [{**pr(labels=labels), "armed": True}],
                                          "skill", flaky, delete=lambda *a: None)
                self.assertTrue(lines[0].startswith(want), lines)
                self.assertFalse(base.armed)

    def test_an_unarmed_removal_is_never_a_persons(self):
        # A person armed it, then the loop's own disarm turned it off: not
        # armed, so not overridden, and who armed it is not even read.
        timeline = [self.LOOP_ARM, self.ARM, event("auto_merge_disabled", rs.LOOP_AUTHOR,
                                                   "2026-11-02T11:00:00Z")]
        lines, gh = self.one_pass(doc({SKILL: VERDICTS["retire+auto"]}), timeline, True,
                                  armed=False)
        self.assertTrue(lines[0].startswith("declined #41"), lines)
        self.assertFalse(any(rs.ARMS_JQ in a for a, _ in gh.calls))
        c = rs.withdraw_commands("skill", SKILL_URL)
        self.assertFalse(rs.persons_arm(gh, c, False))
        self.assertTrue(rs.persons_arm(gh, c, True))
        gh.armed = False
        ok, why = rs.refresh_allowed(doc({SKILL: VERDICTS["retire+auto"]}), self.HEAD, gh, 41)
        self.assertEqual((ok, why), (False, "its proposal issue #900 is closed, which "
                                            "declines it"))

    def test_the_latest_arm_is_read_by_time_not_by_position(self):
        c = rs.withdraw_commands("skill", SKILL_URL)
        late = {**self.LOOP_ARM, "created_at": "2026-11-02T11:00:00Z"}
        for timeline, want in (([self.ARM, {**self.LOOP_ARM}], True),
                               ([late, self.ARM], False)):
            with self.subTest(timeline=timeline):
                gh = ArmsGh()
                gh.timeline = timeline
                self.assertIs(rs.persons_arm(gh, c, True), want)

    def test_the_status_line_and_the_dry_run(self):
        self.assertEqual(rs.PERSONS_ARM, "armed by a person")
        c = rs.withdraw_commands("skill", SKILL_URL)
        for action in ("withdraw", "disarm", "decline"):
            listing = rs.would_run("skill", {"action": action, "subject": SKILL,
                                             "url": SKILL_URL, "declined": 900, "why": "w"})
            self.assertLess(listing.index(c["arms"]), listing.index(c["merge"]), action)

    # Refresh -------------------------------------------------------------
    def refresh(self, gates, timeline=None, issues=(), number=41, armed=True,
                head=None, gh=None):
        gh = gh or ArmsGh(issues=list(issues), armed=armed)
        gh.timeline = list(timeline if timeline is not None else [self.LOOP_ARM, self.ARM])
        return rs.refresh_allowed(gates, head or self.HEAD, gh, number), gh

    def test_refresh_allows_a_persons_arm_whatever_else_says_no(self):
        cases = {
            "stale verdict": (doc({SKILL: VERDICTS["keep"]}), ()),
            "proposal mode": (doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal"), ()),
            "closed proposal issue": (doc({SKILL: VERDICTS["retire+auto"]}),
                                      [{**stamped(900, rs.PROPOSAL_STAMP),
                                        "closed_at": self.CLOSED_AT}]),
            "verdicts unknown": (None, ()),
        }
        for name, (gates, issues) in cases.items():
            with self.subTest(name):
                (ok, why), gh = self.refresh(gates, issues=issues)
                self.assertTrue(ok, why)
                self.assertTrue(why.startswith("armed by a person"), why)
                self.assertIn(["api", f"repos/{rs.REGISTRY_REPO}/pulls/41", "--jq",
                               ".auto_merge != null"], [a for a, _ in gh.calls])
                # Without the number, the refusal stands.
                (ok, _), gh = self.refresh(gates, issues=issues, number=None)
                self.assertFalse(ok)
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        (ok, why), gh = self.refresh(doc(guidance={SECTION: VERDICTS["keep"]}), head=head)
        self.assertTrue(ok, why)
        self.assertIn(["api", f"repos/{rs.GUIDANCE_REPO}/pulls/41", "--jq",
                       ".auto_merge != null"], [a for a, _ in gh.calls])

    def test_refresh_refuses_anything_short_of_a_persons_arm(self):
        gates = doc({SKILL: VERDICTS["keep"]})
        for name, kwargs in {
                "the loop's arm": {"timeline": [self.LOOP_ARM]},
                "not armed": {"armed": False},
                "arm time unknown": {"timeline": [{**self.ARM, "created_at": ""}]},
                "no arm": {"timeline": []},
                "no number": {"number": None},
                "a bad number": {"number": 0}}.items():
            with self.subTest(name):
                (ok, why), _ = self.refresh(gates, **kwargs)
                self.assertEqual((ok, why), (False, "the verdict is keep, not retire"))
        for jq in (rs.ARMS_JQ, ".auto_merge != null"):
            with self.subTest(unreadable=jq):
                base = ArmsGh()
                base.timeline = [self.LOOP_ARM, self.ARM]

                def flaky(args, stdin=None):
                    if jq in args:
                        raise rs.RetireError("gh api exited 1")
                    return base(args, stdin)

                self.assertFalse(rs.refresh_allowed(gates, self.HEAD, flaky, 41)[0])
        # A supported removal is refreshed without reading who armed it.
        (ok, _), gh = self.refresh(doc({SKILL: VERDICTS["retire+auto"]}))
        self.assertTrue(ok)
        self.assertFalse(any(rs.ARMS_JQ in a for a, _ in gh.calls))

    def test_removal_check_passes_the_number(self):
        import refresh_loop_prs as rlp
        from contextlib import redirect_stdout
        gh = ArmsGh()
        gh.timeline = [self.LOOP_ARM, self.ARM]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "latest.json"
            path.write_text(json.dumps(doc({SKILL: VERDICTS["keep"]})))
            for extra, want in (([], 4), (["--number", "41"], 0)):
                out = io.StringIO()
                with redirect_stdout(out):
                    code = rlp.main(["removal-check", "--gates", str(path), "--head",
                                     self.HEAD, *extra], gh=gh)
                self.assertEqual(code, want, out.getvalue())
        self.assertIn("reason=armed by a person", out.getvalue())

    def test_round_elevens_comparisons_are_gone(self):
        # Round 13 brought one comparison back (the decline's `closed_at`,
        # inside `persons_arm`); round 11's two functions stay gone.
        src = Path(rs.__file__).read_text()
        for gone in ("def person_rearm", "def switch_rearm", '"otherwise"'):
            self.assertNotIn(gone, src)

    # R12-1 ---------------------------------------------------------------
    def test_a_lowered_pass_at_the_cap_keeps_the_marker_and_the_comment_is_once(self):
        withdrawn = RoundTenTests.withdrawn_body(self)
        fake = IssueStoreGitHub(closed=[closed_pr(n) for n in (7, 8, 9)],
                                issues=[t70.issue(900, withdrawn, state="closed"),
                                        t70.issue(901, withdrawn)])
        auto = ("--allow-mode", "auto", "--allow-mode", "proposal")
        lowered = ("--allow-mode", "proposal", "--fallback-to-proposal")
        marker = rs.CAP_MARKER.format(subject=t70.SKILL)
        for extra in (auto, lowered, auto, lowered, auto):
            code, out, err, _ = t70.Base.run_main(self, t70.gates_doc("auto"), *extra,
                                                  env=t70.AUTO_ENV, fake=fake)
            self.assertEqual(code, 0, err)
            self.assertIn(marker, fake._issue(901)["body"], (extra, out))
        caps = [s for a, s in fake.calls
                if a[:2] == ["issue", "comment"] and marker in (s or "")]
        self.assertEqual(len(caps), 1)
        self.assertEqual(fake.pushes, [])

    def test_the_lowered_path_posts_the_comment_when_it_is_first(self):
        withdrawn = RoundTenTests.withdrawn_body(self)
        fake = IssueStoreGitHub(closed=[closed_pr(n) for n in (7, 8, 9)],
                                issues=[t70.issue(901, withdrawn)])
        lowered = ("--allow-mode", "proposal", "--fallback-to-proposal")
        auto = ("--allow-mode", "auto", "--allow-mode", "proposal")
        for extra in (lowered, lowered, auto):
            code, out, err, _ = t70.Base.run_main(self, t70.gates_doc("auto"), *extra,
                                                  env=t70.AUTO_ENV, fake=fake)
            self.assertEqual(code, 0, err)
        marker = rs.CAP_MARKER.format(subject=t70.SKILL)
        caps = [s for a, s in fake.calls
                if a[:2] == ["issue", "comment"] and marker in (s or "")]
        self.assertEqual(len(caps), 1)
        self.assertIn(f"@{rs.NOTICE_OWNER}", caps[0])


class RoundThirteenTests(t70.Base):
    """PR #759 round 13: R13-1 (the latest person action wins: a person's
    arm in force wins over a closed proposal issue only when it is strictly
    later than the close, in the withdrawal pass and the refresh alike),
    R13-2 (a person's arm is a `User`'s: no bot, App, deleted account or
    untyped actor) and R13-3 (round 13's surviving mutants 11 and 13)."""

    LOOP_ARM = event("auto_merge_enabled", rs.LOOP_AUTHOR, "2026-11-04T08:00:00Z")
    ARM = event("auto_merge_enabled", "a-person", "2026-11-04T10:00:00Z")
    BEFORE, AFTER = "2026-11-04T09:00:00Z", "2026-11-04T12:00:00Z"
    LEFT = ["left #41 for a person: armed by a person"]
    HEAD = f"{rs.BRANCH_PREFIX}{SKILL}"
    #: (name, the issue's close time, whether the person's arm wins)
    ORDERS = (("arm, then close", AFTER, False),
              ("close, then arm", BEFORE, True),
              ("a tie", ARM["created_at"], False),
              ("no close time", None, False),
              ("an empty close time", "", False),
              ("an unparseable close time", "yesterday", False))

    @staticmethod
    def closed_issue(closed_at, number=900, stamp=rs.PROPOSAL_STAMP):
        out = stamped(number, stamp) if stamp else issue(number, state="closed")
        return out if closed_at is None else {**out, "closed_at": closed_at}

    def one_pass(self, gates, timeline, issues, armed=True):
        gh = ArmsGh(issues=list(issues), armed=armed)
        gh.timeline = list(timeline)
        gh.pr_labels = [rs.AGENT_LABEL]
        lines = rs.withdraw_stale(gates, [{**pr(), "armed": armed}], "skill", gh,
                                  delete=lambda *a: None)
        return lines, gh

    def refresh(self, gates, timeline, issues, armed=True, head=None):
        gh = ArmsGh(issues=list(issues), armed=armed)
        gh.timeline = list(timeline)
        return rs.refresh_allowed(gates, head or self.HEAD, gh, 41), gh

    # R13-1: the withdrawal pass -----------------------------------------
    def test_the_latest_person_action_wins_over_a_close(self):
        for gates in (doc({SKILL: VERDICTS["retire+auto"]}),
                      doc({SKILL: VERDICTS["keep"]}),
                      doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal")):
            for stamp in (rs.PROPOSAL_STAMP, None):  # a proposal issue, a legacy one
                for name, closed_at, wins in self.ORDERS:
                    with self.subTest(name, mode=gates["retirement_mode"],
                                      verdict=gates["skills"][SKILL]["verdict"],
                                      legacy=stamp is None):
                        lines, gh = self.one_pass(gates, [self.LOOP_ARM, self.ARM],
                                                  [self.closed_issue(closed_at, stamp=stamp)])
                        if wins:
                            self.assertEqual(lines, self.LEFT)
                            self.assertEqual(gh.writes(), [])
                            self.assertTrue(gh.armed)
                        else:
                            self.assertTrue(lines[0].startswith("declined #41"), lines)
                            self.assertIn(["pr", "close", SKILL_URL, "-R", rs.REGISTRY_REPO],
                                          gh.writes())
                            self.assertFalse(gh.armed)

    def test_the_latest_of_several_closes_is_compared(self):
        issues = [self.closed_issue(self.BEFORE), self.closed_issue(self.AFTER, number=901)]
        lines, _ = self.one_pass(doc({SKILL: VERDICTS["retire+auto"]}),
                                 [self.LOOP_ARM, self.ARM], issues)
        self.assertTrue(lines[0].startswith("declined #41"), lines)
        found = rs.existing_issues(ArmsGh(issues=issues), SKILL)
        self.assertEqual(rs.declined(found, SKILL, "auto", "skill")["closed_at"], self.AFTER)
        # One close time unknown: the decline wins whatever the other says.
        found["closed_at"][901] = ""
        self.assertIsNone(rs.declined(found, SKILL, "auto", "skill")["closed_at"])

    def test_the_decline_names_the_issue_with_the_latest_close(self):
        # #900 closed at 09:00, #901 at 12:00, a person's arm at 10:00.
        issues = [self.closed_issue("2026-11-04T09:00:00Z"),
                  self.closed_issue("2026-11-04T12:00:00Z", number=901)]
        found = rs.existing_issues(ArmsGh(issues=issues), SKILL)
        decline = rs.declined(found, SKILL, "auto", "skill")
        self.assertEqual(decline["issue"], 901)
        self.assertIn("#901", decline["reason"])
        lines, _ = self.one_pass(doc({SKILL: VERDICTS["retire+auto"]}),
                                 [self.LOOP_ARM, self.ARM], issues)
        self.assertTrue(lines[0].startswith("declined #41"), lines)
        self.assertIn("#901", lines[0])
        self.assertNotIn("#900", lines[0])
        # A close time unknown: the first issue is still the one named.
        found["closed_at"][901] = ""
        self.assertEqual(rs.declined(found, SKILL, "auto", "skill")["issue"], 900)

    def test_the_switch_and_a_stale_verdict_keep_the_plain_rule(self):
        # No decline: a person's arm in force is left, whenever it was made.
        # A closed issue the withdrawal path filed declines nothing, so its
        # close time is not compared either.
        withdrawn = self.closed_issue(self.AFTER, stamp=rs.WITHDRAWAL_STAMP)
        for gates in (doc({SKILL: VERDICTS["keep"]}),
                      doc({SKILL: VERDICTS["retire+auto"]}, mode="proposal")):
            for issues in ([], [withdrawn]):
                with self.subTest(mode=gates["retirement_mode"], issues=len(issues)):
                    lines, gh = self.one_pass(gates, [self.LOOP_ARM, self.ARM], issues)
                    self.assertEqual((lines, gh.writes()), (self.LEFT, []))

    def test_persons_arm_compares_only_with_a_decline(self):
        c = rs.withdraw_commands("skill", SKILL_URL)
        gh = ArmsGh()
        gh.timeline = [self.LOOP_ARM, self.ARM]
        self.assertTrue(rs.persons_arm(gh, c, True))
        self.assertTrue(rs.persons_arm(gh, c, True, {"closed_at": self.BEFORE}))
        for closed_at in (self.AFTER, self.ARM["created_at"], None, "", "yesterday"):
            with self.subTest(closed_at=closed_at):
                self.assertFalse(rs.persons_arm(gh, c, True, {"closed_at": closed_at}))
        self.assertFalse(rs.persons_arm(gh, c, True, {}))
        self.assertFalse(rs.persons_arm(gh, c, False, {"closed_at": self.BEFORE}))

    # R13-1: the refresh --------------------------------------------------
    def test_the_refresh_applies_the_same_comparison(self):
        for gates in (doc({SKILL: VERDICTS["retire+auto"]}), doc({SKILL: VERDICTS["keep"]})):
            for name, closed_at, wins in self.ORDERS:
                with self.subTest(name, verdict=gates["skills"][SKILL]["verdict"]):
                    (ok, why), _ = self.refresh(gates, [self.LOOP_ARM, self.ARM],
                                                [self.closed_issue(closed_at)])
                    self.assertIs(ok, wins, why)
                    if wins:
                        self.assertTrue(why.startswith("armed by a person"), why)
                    else:
                        self.assertEqual(why, "its proposal issue #900 was closed no earlier "
                                              "than a person armed it (or either time is "
                                              "unknown), which declines it")

    def test_the_refresh_refuses_a_persons_arm_when_the_issues_cannot_be_read(self):
        base = ArmsGh()
        base.timeline = [self.LOOP_ARM, self.ARM]

        def flaky(args, stdin=None):
            if "/issues?" in " ".join(args):
                raise rs.RetireError("gh api exited 1")
            return base(args, stdin)

        gates = doc({SKILL: VERDICTS["keep"]})
        self.assertEqual(rs.refresh_allowed(gates, self.HEAD, flaky, 41),
                         (False, "its retirement issues could not be read"))
        # Not armed: the issues are not read for it, and the verdict's
        # refusal stands as it is.
        base.armed = False
        self.assertEqual(rs.refresh_allowed(gates, self.HEAD, flaky, 41),
                         (False, "the verdict is keep, not retire"))

    # R13-2 ---------------------------------------------------------------
    NOT_PEOPLE = {
        "github-actions[bot]": ("github-actions[bot]", "Bot"),
        "another App": ("a-helper[bot]", "Bot"),
        "the loop under a new slug": ("skills-evals-improve-v2[bot]", "Bot"),
        "the loop's login typed as a User": (rs.LOOP_AUTHOR, "User"),
        "a deleted account": (rs.GHOST, "User"),
        "an organization": ("an-org", "Organization"),
        "no type": ("a-person", ""),
        "no login": ("", "User"),
    }

    def test_only_a_users_arm_is_a_persons(self):
        c = rs.withdraw_commands("skill", SKILL_URL)
        for name, (actor, type_) in self.NOT_PEOPLE.items():
            timeline = [self.LOOP_ARM, event("auto_merge_enabled", actor,
                                             self.ARM["created_at"], type_=type_)]
            with self.subTest(name):
                gh = ArmsGh()
                gh.timeline = timeline
                self.assertFalse(rs.persons_arm(gh, c, True))
                lines, gh = self.one_pass(doc({SKILL: VERDICTS["keep"]}), timeline, [])
                self.assertTrue(lines[0].startswith("withdrew #41"), lines)
                lines, gh = self.one_pass(doc({SKILL: VERDICTS["retire+auto"]},
                                              mode="proposal"), timeline, [])
                self.assertTrue(lines[0].startswith("disarmed #41"), lines)
                (ok, why), _ = self.refresh(doc({SKILL: VERDICTS["keep"]}), timeline, [])
                self.assertEqual((ok, why), (False, "the verdict is keep, not retire"))
        gh = ArmsGh()
        gh.timeline = [self.LOOP_ARM, self.ARM]
        self.assertEqual(self.ARM["type"], "User")
        self.assertTrue(rs.persons_arm(gh, c, True))
        # A User's and a bot's arm in the same second: not known to be a person's.
        gh.timeline = [self.ARM, event("auto_merge_enabled", "a-helper[bot]",
                                       self.ARM["created_at"])]
        self.assertFalse(rs.persons_arm(gh, c, True))

    def test_the_arms_filter_reads_the_actors_type_through_real_jq(self):
        raw = [{"event": "auto_merge_enabled",
                "actor": {"login": "a-person", "type": "User"},
                "created_at": "2026-11-04T10:00:00Z"},
               {"event": "auto_merge_enabled",
                "actor": {"login": "a-helper[bot]", "type": "Bot"},
                "created_at": "2026-11-04T11:00:00Z"},
               {"event": "auto_merge_enabled", "actor": None}]
        rows = [json.loads(x) for x in TimelineFilterTests.jq(rs.ARMS_JQ, raw).splitlines()]
        self.assertEqual(rows, [
            {"actor": "a-person", "type": "User", "created_at": "2026-11-04T10:00:00Z"},
            {"actor": "a-helper[bot]", "type": "Bot", "created_at": "2026-11-04T11:00:00Z"},
            {"actor": "", "type": "", "created_at": ""}])

    def test_the_issue_listing_reads_the_close_time_through_real_jq(self):
        gh = ArmsGh()
        rs.existing_issues(gh, SKILL)
        jq = gh.calls[0][0][gh.calls[0][0].index("--jq") + 1]
        raw = [{"number": 900, "body": "b", "user": {"login": rs.ISSUE_AUTHOR},
                "state": "closed", "closed_at": self.AFTER},
               {"number": 901, "body": "b", "user": {"login": rs.ISSUE_AUTHOR},
                "state": "open", "closed_at": None}]
        rows = [json.loads(x) for x in TimelineFilterTests.jq(jq, raw).splitlines()]
        self.assertEqual([r["closed_at"] for r in rows], [self.AFTER, ""])

    # Texts ---------------------------------------------------------------
    def test_every_issue_facing_text_states_the_rule(self):
        rule = " ".join(rs.LATEST_WINS.split())
        self.assertIn("strictly after the proposal issue is closed", rule)
        self.assertIn("in the same second as it, or with either time unknown declines it",
                      rule)
        self.assertIn("not a bot or an App", rule)
        gh = FakeGh()
        rs.open_proposal_note(gh, {"open": [900], "proposals": [900]}, SKILL, SKILL_URL,
                              "skill")
        note = next(s for a, s in gh.calls if a[:2] == ["issue", "comment"])
        self.assertIn("Closing this issue still declines it", note)
        item = {"subject": SKILL, "url": SKILL_URL, "verdict": "keep", "reason": "r",
                "why": "w", "declined": 900}
        withdrawal = rs.withdrawal_issue(item, doc({}), "skill",
                                         FakeGh(issues=[stamped(900, rs.PROPOSAL_STAMP,
                                                                state="open")]), None)
        lines, gh = self.one_pass(doc({SKILL: VERDICTS["retire+auto"]}),
                                  [self.LOOP_ARM, self.ARM], [self.closed_issue(self.AFTER)])
        comments = [s for a, s in gh.calls if a[:2] in (["pr", "comment"],
                                                         ["issue", "comment"])]
        self.assertEqual(len(comments), 2)
        for text in (note, withdrawal["comment"], rs.declined_comment(item, "skill", None),
                     *comments):
            self.assertIn(rule, " ".join(text.split()))
        for text in comments:
            self.assertIn("No person's arm on th", text)

    def test_the_docs_state_the_rule(self):
        how = " ".join((ROOT / "docs" / "how-it-works.md").read_text().split())
        adr = " ".join((ROOT / "docs" / "decisions" /
                        "0014-removal-pull-requests-merge-without-review.md").read_text().split())
        for text in (how, adr):
            self.assertIn("the latest person action wins", text.lower())
            self.assertIn("strictly later than the issue's `closed_at`", text)
            self.assertIn("`User`", text)
        self.assertIn("**Round 13", adr)

    # R13-3 ---------------------------------------------------------------
    def test_mutant_13_a_head_with_no_subject_is_refused_under_a_persons_arm(self):
        for head in (f"{rs.BRANCH_PREFIX}Not-A-Skill", f"{rs.BRANCH_PREFIX}",
                     f"{rs.GUIDANCE_BRANCH_PREFIX}a/b"):
            with self.subTest(head=head):
                (ok, why), _ = self.refresh(doc({SKILL: VERDICTS["keep"]}),
                                            [self.LOOP_ARM, self.ARM], [], head=head)
                self.assertEqual((ok, why), (False, "its head names no subject"))

    def test_mutant_11_a_shorten_never_counts_pauses_or_gets_the_cap_note(self):
        head = f"{rs.GUIDANCE_BRANCH_PREFIX}{SECTION}"
        paused = [closed_pr(n, head=head) for n in (7, 8, 9)]
        gates = doc(guidance={SECTION: {**gretire(), "verdict": "shorten-or-merge"}})
        self.assertEqual(gates["guidance_retirement_mode"], "auto")
        gh = FakeGh(closed=paused)
        action = rs.guidance_plan(gates, None, gh, allowed=("auto", "proposal"))
        self.assertEqual(action["action"], "create-issue")
        self.assertNotIn(rs.CAP_PREFIX, action["body"])
        self.assertFalse(any("state=closed" in " ".join(a) for a, _ in gh.calls))


import gates as gates_mod  # noqa: E402


if __name__ == "__main__":
    unittest.main()
