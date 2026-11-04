#!/usr/bin/env python3
"""The fixture queue, tracked and alerted on (Adam, 2026-11-03: "Make sure
the proper functioning and cost and benefits/impacts/instances of requesting
harder fixtures, creating them from real fleet work when possible and
putting those to use is tracked, acted on when broken, and included in the
dashboard").

scripts/fixture_queue.py `report` follows each request issue to the pull
requests that name it and the fixtures that carry its URL in `origin:`, with
their runs and cost; `alerts` files `half-built-or-broken` issues from its
findings. Pinned here: the report's shape and numbers (null when unknown,
never a guess), the three findings and their thresholds, the alert filing
rules, and that the report passes explorer_data's public-document gate.

Hermetic: throwaway Git repositories with fixed commit dates, a synthetic
results tree, `now` passed in, `gh` faked. example.com and invented names.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))

import explorer_data  # noqa: E402
import fixture_queue as fq  # noqa: E402
import retire_skill  # noqa: E402
import work_item_issues  # noqa: E402
from test_issue_72_explorer_data import Tree  # noqa: E402

NOW = datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc)
BOT = {"login": "github-actions[bot]"}
REQ = "https://github.com/Adam-S-Daniel/skills-evals/issues/"
RUN_ID = "4100000001-1"


def iso(day, hour=12):
    return f"2026-11-{day:02d}T{hour:02d}:00:00Z"


def request(number, kind="needs-harder-fixtures", key="writing-adrs", state="open",
            opened=1, closed=None, **over):
    return {"number": number, "state": state, "user": BOT,
            "created_at": iso(opened), "closed_at": iso(closed) if closed else None,
            "body": f"<!-- skills-evals:{kind}:{key} -->\nKind: {kind}\n\ntext\n", **over}


def pull(number, refs, state="open", opened=10, merged=None, auto=False, lane=True):
    return {"number": number, "state": state, "created_at": iso(opened),
            "merged_at": iso(merged) if merged else None,
            "auto_merge": {"merge_method": "merge"} if auto else None,
            "user": {"login": "Adam-S-Daniel" if lane else "someone"},
            "labels": [{"name": "agent-authored"}] if lane else [],
            "body": f"Adds a fixture.\n\nRefs {REQ}{refs}\n"}


def origin(kind="invented", source=None, issue=1):
    src = "null" if source is None else source
    return f"origin:\n  kind: {kind}\n  source: {src}\n  request: {REQ}{issue}\n"


class Repo:
    """A skills-evals checkout with fixtures committed on fixed dates."""

    def __init__(self, test):
        tmp = tempfile.TemporaryDirectory(prefix="fq-repo-")
        test.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.git("init", "-q", "-b", "main")

    def git(self, *args, date=None):
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(["git", "-C", str(self.root), *args], check=True,
                       capture_output=True, env=env)

    def add(self, rel, text, day):
        path = self.root / rel / "fixture.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"add {rel}", date=iso(day))


SKILL = "skill: writing-adrs\nregistry: https://github.com/Adam-S-Daniel/adam-agentskills\n"


class World:
    """The repository, the results tree and the API listings of one test."""

    def __init__(self, test):
        self.repo = Repo(test)
        self.tree = Tree(test)

    def routine_pair(self, run_id, skill, fixture, stamp, with_passed, without_passed):
        # Tree writes under results/; move the run under routine-results/<id>.
        self.tree.pair(skill, stamp, [Tree.trial(with_passed, 4, 8.0, 0.25)],
                       [Tree.trial(without_passed, 4, 4.0, 0.25)], fixture=fixture)
        src = self.tree.tree / "results" / skill / stamp
        dest = self.tree.tree / "routine-results" / run_id / skill / stamp
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)

    def estimate(self, run_id, usd, points):
        self.tree.write_json(f"routine-results/{run_id}/cost_estimate.json",
                             {"schema_version": 1, "run_id": run_id, "usd": usd,
                              "points": points})

    def report(self, issues, pulls, now=NOW):
        runs, by_run = fq.fixture_runs(self.tree.tree, self.repo.root / "evals",
                                       now.strftime("%Y%m%dT%H%M%SZ"))
        return fq.build_report(issues, pulls, fq.origin_fixtures(self.repo.root), runs,
                               by_run, self.tree.tree, now)


class ReportTests(unittest.TestCase):

    def setUp(self):
        self.w = World(self)
        r = self.w.repo
        r.add("evals/writing-adrs/old", SKILL, 1)  # no origin: not in the queue
        r.add("evals/writing-adrs/harder", SKILL + origin(
            "real-work", "https://github.com/jodidaniel/example-site/pull/12", 1), 2)
        r.add("evals/writing-adrs/invented-one", SKILL + origin(issue=2), 18)  # 2 days
        r.add("evals/writing-adrs/never-ran", SKILL + origin(issue=2), 3)
        r.add("evals/writing-adrs/bad-origin", SKILL + origin("scraped"), 3)
        r.add("evals/guidance/example-section/fx", "subject: guidance\n" + origin(issue=3), 19)
        self.w.routine_pair(RUN_ID, "writing-adrs", "harder", "20261105T100000Z", 3, 1)
        self.w.estimate(RUN_ID, 1.5, 0.25)
        self.issues = [
            request(1, closed=8, state="closed"),
            request(2, kind="needs-fixtures", opened=5),          # open PR: not stale
            request(3, kind="needs-fixtures", key="guidance/example-section", opened=2),
            request(4, kind="needs-trigger-set", key="quiet-skill", opened=18),
            request(5, user={"login": "someone"}),                # not the bot's
            {**request(6), "pull_request": {}},                    # a pull request
            {**request(7), "body": "no marker"},
        ]
        self.pulls = [
            pull(101, 1, state="closed", opened=6, merged=7),
            pull(102, 2, opened=10),                     # lane, open 10 days, no auto: stuck
            pull(103, 2, opened=19),                     # lane, under 2 days
            pull(104, 2, opened=10, auto=True),          # armed
            pull(105, 2, opened=10, lane=False),         # not the lane
            pull(106, 99, opened=10),                    # names no request
        ]
        self.report = self.w.report(self.issues, self.pulls)

    def test_shape(self):
        rep = self.report
        self.assertEqual(sorted(rep), ["findings", "fixtures", "generated_at", "requests",
                                       "schema", "totals"])
        self.assertEqual((rep["schema"], rep["generated_at"]), (1, "2026-11-20T12:00:00Z"))
        self.assertEqual([r["issue"] for r in rep["requests"]], [1, 2, 3, 4])
        first = rep["requests"][0]
        self.assertEqual(first, {"issue": 1, "kind": "needs-harder-fixtures",
                                 "subject": "writing-adrs", "state": "closed",
                                 "opened_at": iso(1), "closed_at": iso(8),
                                 "prs": [{"number": 101, "state": "merged",
                                          "merged_at": iso(7), "auto_merge": False}]})
        self.assertEqual([p["number"] for p in rep["requests"][1]["prs"]],
                         [102, 103, 104, 105])
        self.assertTrue(rep["requests"][1]["prs"][2]["auto_merge"])
        self.assertEqual(rep["requests"][2]["subject"], "guidance/example-section")

    def test_fixtures_runs_pass_rates_and_cost(self):
        by = {f["path"]: f for f in self.report["fixtures"]}
        self.assertEqual(sorted(by), ["evals/guidance/example-section/fx",
                                      "evals/writing-adrs/harder",
                                      "evals/writing-adrs/invented-one",
                                      "evals/writing-adrs/never-ran"])
        harder = by["evals/writing-adrs/harder"]
        self.assertEqual(harder, {
            "path": "evals/writing-adrs/harder", "subject": "writing-adrs",
            "origin_kind": "real-work",
            "source": "https://github.com/jodidaniel/example-site/pull/12",
            "request": f"{REQ}1", "added_at": iso(2), "runs": 1,
            "with_pass_rate": 0.75, "without_pass_rate": 0.25,
            "cost_points": 0.25, "cost_usd": 1.5})
        never = by["evals/writing-adrs/never-ran"]
        self.assertEqual((never["runs"], never["with_pass_rate"], never["cost_usd"],
                          never["source"]), (0, None, 0, None))
        self.assertEqual(by["evals/guidance/example-section/fx"]["subject"],
                         "guidance/example-section")
        self.assertEqual(self.report["totals"], {
            "requests_open": 3, "requests_closed": 1, "prs_merged": 1,
            "fixtures_real_work": 1, "fixtures_invented": 3, "fixture_runs": 1,
            "cost_points": 0.25, "cost_usd": 1.5})

    def test_findings_and_thresholds(self):
        ids = [f["finding_id"] for f in self.report["findings"]]
        self.assertEqual(ids, [
            "skills-evals/fixture-queue-stale-request-3",
            "skills-evals/fixture-queue-stuck-pr-102",
            "skills-evals/fixture-queue-unused-fixture-writing-adrs-never-ran"])
        by = {f["finding_id"]: f for f in self.report["findings"]}
        self.assertEqual(by["skills-evals/fixture-queue-stale-request-3"], {
            "finding_id": "skills-evals/fixture-queue-stale-request-3", "kind": "idle",
            "severity": "medium", "subject": "guidance/example-section",
            "url": f"{REQ}3"})
        self.assertEqual(by["skills-evals/fixture-queue-stuck-pr-102"]["url"],
                         "https://github.com/Adam-S-Daniel/skills-evals/pull/102")
        self.assertEqual(
            by["skills-evals/fixture-queue-unused-fixture-writing-adrs-never-ran"]["url"],
            "https://github.com/Adam-S-Daniel/skills-evals/tree/main/evals/writing-adrs/never-ran")
        # Every finding passes the alert job's own check.
        for item in self.report["findings"]:
            fq.checked(item)

    def test_thresholds_are_inclusive_and_not_crossed_earlier(self):
        # On day 5, request 3 is 3 days old and the fixture added on day 3 is
        # 2 days old: neither has crossed its threshold. On day 9 the request
        # is exactly 7 days old, which counts.
        early = self.w.report(self.issues, self.pulls,
                              now=datetime(2026, 11, 5, 12, tzinfo=timezone.utc))
        ids = [f["finding_id"] for f in early["findings"]]
        self.assertNotIn("skills-evals/fixture-queue-stale-request-3", ids)
        self.assertNotIn("skills-evals/fixture-queue-unused-fixture-writing-adrs-never-ran",
                         ids)
        exact = self.w.report(self.issues, self.pulls,
                              now=datetime(2026, 11, 9, 12, tzinfo=timezone.utc))
        self.assertIn("skills-evals/fixture-queue-stale-request-3",
                      [f["finding_id"] for f in exact["findings"]])

    def test_a_merged_pr_quiets_a_stale_request(self):
        pulls = [*self.pulls, pull(107, 3, state="closed", opened=4, merged=5)]
        ids = [f["finding_id"] for f in self.w.report(self.issues, pulls)["findings"]]
        self.assertNotIn("skills-evals/fixture-queue-stale-request-3", ids)
        # A closed, unmerged one does not.
        pulls = [*self.pulls, pull(107, 3, state="closed", opened=4)]
        ids = [f["finding_id"] for f in self.w.report(self.issues, pulls)["findings"]]
        self.assertIn("skills-evals/fixture-queue-stale-request-3", ids)

    def test_unknown_cost_is_null_never_a_guess(self):
        # No estimate file for the run: unknown.
        (self.w.tree.tree / "routine-results" / RUN_ID / "cost_estimate.json").unlink()
        rep = self.w.report(self.issues, self.pulls)
        harder = next(f for f in rep["fixtures"] if f["path"] == "evals/writing-adrs/harder")
        self.assertEqual((harder["cost_usd"], harder["cost_points"]), (None, None))
        self.assertEqual((rep["totals"]["cost_usd"], rep["totals"]["cost_points"]), (None, None))
        # An estimate without points: dollars known, points not.
        self.w.estimate(RUN_ID, 2.0, None)
        harder = next(f for f in self.w.report(self.issues, self.pulls)["fixtures"]
                      if f["path"] == "evals/writing-adrs/harder")
        self.assertEqual((harder["cost_usd"], harder["cost_points"]), (2.0, None))

    def test_a_run_shared_with_another_fixture_has_unknown_cost(self):
        self.w.routine_pair(RUN_ID, "writing-adrs", "invented-one", "20261106T100000Z", 4, 0)
        rep = self.w.report(self.issues, self.pulls)
        by = {f["path"]: f for f in rep["fixtures"]}
        for path in ("evals/writing-adrs/harder", "evals/writing-adrs/invented-one"):
            with self.subTest(path=path):
                self.assertEqual(by[path]["runs"], 1)
                self.assertIsNone(by[path]["cost_usd"])

    def test_a_run_outside_routine_results_has_unknown_cost(self):
        self.w.tree.pair("writing-adrs", "20261107T100000Z", [Tree.trial(4, 4, 8.0, 0.25)],
                         [Tree.trial(0, 4, 4.0, 0.25)], fixture="invented-one")
        by = {f["path"]: f for f in self.w.report(self.issues, self.pulls)["fixtures"]}
        self.assertEqual((by["evals/writing-adrs/invented-one"]["runs"],
                          by["evals/writing-adrs/invented-one"]["with_pass_rate"],
                          by["evals/writing-adrs/invented-one"]["cost_usd"]), (1, 1.0, None))

    def test_the_report_passes_the_public_document_gate(self):
        doc = self.w.tree.build()
        doc["fixture_queue"] = self.report
        text = explorer_data.finish(doc)
        self.assertNotIn("text", json.dumps(self.report))  # no issue body
        self.assertNotIn("Adds a fixture", text)            # no pull request body

    def test_the_cli_writes_the_report(self):
        files = self.w.tree.root
        (files / "issues.json").write_text(json.dumps([self.issues[:3], self.issues[3:]]))
        (files / "pulls.json").write_text(json.dumps(self.pulls))
        out = files / "out" / "queue.json"
        args = ["report", "--issues", str(files / "issues.json"),
                "--pulls", str(files / "pulls.json"), "--repo", str(self.w.repo.root),
                "--results-tree", str(self.w.tree.tree), "--now", "2026-11-20T12:00:00Z",
                "--out", str(out)]
        import contextlib
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(fq.main(args), 0)
        self.assertEqual(json.loads(out.read_text()), self.report)
        self.assertEqual(stdout.getvalue(),
                         "fixture queue: 3 open request(s), 4 fixture(s) with an origin, "
                         "3 finding(s)\n")
        (files / "pulls.json").write_text("{")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(fq.main(args[:-1] + [str(files / "other.json")]), 2)
        self.assertFalse((files / "other.json").exists())


class FakeGh:
    def __init__(self, issues, labels=("half-built-or-broken",)):
        self.issues, self.labels, self.calls = issues, set(labels), []

    def __call__(self, args, stdin=None, token=None):
        self.calls.append((args, stdin))
        if args[0] == "api" and "/labels" in args[2]:
            return "\n".join(sorted(self.labels))
        if args[0] == "api":
            return "\n".join(json.dumps({"labels": [], **i, "author": retire_skill.ISSUE_AUTHOR})
                             for i in self.issues)
        if args[:2] == ["label", "create"]:
            self.labels.add(args[2])
        return ""


STALE = fq.finding("stale-request", 3, "guidance/example-section", f"{REQ}3")
STUCK = fq.finding("stuck-pr", 102, "writing-adrs",
                   "https://github.com/Adam-S-Daniel/skills-evals/pull/102")
UNUSED = fq.finding("unused-fixture", "writing-adrs-never-ran", "writing-adrs",
                    "https://github.com/Adam-S-Daniel/skills-evals/tree/main/"
                    "evals/writing-adrs/never-ran")


def alert_issue(number, finding_id, state="open", labels=()):
    return {"number": number, "state": state, "labels": list(labels),
            "body": f"Kind: idle\nSeverity: medium\nFinding-ID: {finding_id}\n"
                    f"<!-- skills-evals:fixture-queue:{finding_id} -->\n\ntext\n"}


class AlertTests(unittest.TestCase):

    def run_alerts(self, findings, issues, *extra, gh=None):
        report = {"schema": 1, "generated_at": "2026-11-20T12:00:00Z", "requests": [],
                  "fixtures": [], "totals": {}, "findings": findings}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            gh, out = gh or FakeGh(issues), io.StringIO()
            import contextlib
            with contextlib.redirect_stderr(io.StringIO()):
                code = fq.main(["alerts", "--report", str(path), *extra], gh=gh, out=out)
        return code, gh.calls, out.getvalue()

    @staticmethod
    def writes(calls):
        return [args[:3] if args[1] in ("reopen", "close", "comment") else args[:2]
                for args, _ in calls if args[0] == "issue"]

    def test_each_new_finding_opens_one_issue_in_the_audits_format(self):
        code, calls, out = self.run_alerts([STALE, STUCK, UNUSED], [],
                                           "--run-url", "https://example.com/run/1")
        self.assertEqual(code, 0)
        creates = [(a, b) for a, b in calls if a[:2] == ["issue", "create"]]
        self.assertEqual(len(creates), 3)
        titles = sorted(a[a.index("--title") + 1] for a, _ in creates)
        self.assertEqual(titles, [
            "Fixture queue: fixture evals/writing-adrs/never-ran has no runs 3 days after it "
            "landed",
            "Fixture queue: pull request #102 open 2+ days without auto-merge",
            "Fixture queue: request #3 has no PR after 7 days"])
        for args, body in creates:
            with self.subTest(title=args[args.index("--title") + 1]):
                self.assertEqual(args[args.index("--label") + 1], "half-built-or-broken")
                lines = body.splitlines()
                self.assertRegex(lines[0], r"^Kind: (broken|idle)$")
                self.assertRegex(lines[1], r"^Severity: (high|medium|low)$")
                fid = lines[2].removeprefix("Finding-ID: ")
                self.assertEqual(lines[3], f"<!-- skills-evals:fixture-queue:{fid} -->")
                self.assertIn("Recommendation: fix", body)
                self.assertIn("https://example.com/run/1", body)
                self.assertIn("2026-11-20T12:00:00Z", body)
        self.assertEqual(out.count("create-issue: "), 3)

    def test_an_open_issue_stands_and_a_cleared_one_closes(self):
        open_one = alert_issue(7, STALE["finding_id"])
        code, calls, _ = self.run_alerts([STALE], [open_one])
        self.assertEqual((code, self.writes(calls)), (0, []))
        code, calls, _ = self.run_alerts([], [open_one])
        self.assertEqual(self.writes(calls), [["issue", "comment", "7"], ["issue", "close", "7"]])
        # The owner's hold keeps it open.
        held = alert_issue(7, STALE["finding_id"], labels=["on-hold"])
        self.assertEqual(self.writes(self.run_alerts([], [held])[1]), [])
        # Another marker kind is not this script's.
        other = {**open_one, "body": "<!-- skills-evals:needs-fixtures:writing-adrs -->\n"}
        self.assertEqual(self.writes(self.run_alerts([], [other])[1]), [])

    def test_a_finding_that_comes_back_reopens_its_issue(self):
        closed = alert_issue(8, STUCK["finding_id"], state="closed")
        code, calls, _ = self.run_alerts([STUCK], [closed])
        self.assertEqual((code, self.writes(calls)),
                         (0, [["issue", "reopen", "8"], ["issue", "comment", "8"]]))

    def test_the_label_is_created_when_missing_and_never_edited(self):
        gh = FakeGh([], labels=())
        code, calls, _ = self.run_alerts([STALE], [], gh=gh)
        self.assertEqual(code, 0)
        self.assertEqual([a[:3] for a, _ in calls if a[0] == "label"],
                         [["label", "create", "half-built-or-broken"]])
        # Present: nothing created; nothing to create: no label call at all.
        code, calls, _ = self.run_alerts([STALE], [])
        self.assertFalse([a for a, _ in calls if a[0] == "label"])
        code, calls, _ = self.run_alerts([], [alert_issue(7, STALE["finding_id"])],
                                         gh=FakeGh([alert_issue(7, STALE["finding_id"])],
                                                   labels=()))
        self.assertFalse([a for a, _ in calls if a[0] == "label" or "/labels" in a[2]])

    def test_a_malformed_finding_files_nothing(self):
        bad = [
            {**STALE, "finding_id": "skills-evals/fixture-queue-stale-request-x"},
            {**STALE, "url": f"{REQ}4"},
            {**STALE, "url": "https://example.com/issues/3"},
            {**STUCK, "severity": "low"},
            {**UNUSED, "url": UNUSED["url"].replace("never-ran", "other")},
            {**UNUSED, "subject": "a b"},
            {**STALE, "extra": 1},
        ]
        for item in bad:
            with self.subTest(item=item):
                code, calls, _ = self.run_alerts([STUCK, item], [alert_issue(7, "x")])
                self.assertEqual((code, self.writes(calls)), (2, []))
        code, calls, _ = self.run_alerts([STALE], [])
        self.assertEqual(code, 0)

    def test_an_unreadable_report_closes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            gh = FakeGh([alert_issue(7, STALE["finding_id"])])
            import contextlib
            with contextlib.redirect_stderr(io.StringIO()):
                code = fq.main(["alerts", "--report", str(Path(tmp) / "absent.json")],
                               gh=gh, out=io.StringIO())
        self.assertEqual((code, self.writes(gh.calls)), (2, []))

    def test_a_dry_run_writes_nothing(self):
        code, calls, out = self.run_alerts([STALE], [], "--dry-run")
        self.assertEqual((code, self.writes(calls)), (0, []))
        self.assertEqual(json.loads(out)["actions"][0]["action"], "create-issue")

    def test_one_failed_call_does_not_stop_the_others(self):
        class Failing(FakeGh):
            def __call__(self, args, stdin=None, token=None):
                if args[:2] == ["issue", "create"] and "#102" in args[args.index("--title") + 1]:
                    self.calls.append((args, stdin))
                    raise retire_skill.RetireError("gh issue exited 1")
                return super().__call__(args, stdin, token)

        code, calls, out = self.run_alerts([STALE, STUCK], [], gh=Failing([]))
        self.assertEqual(code, 1)
        self.assertEqual(out.count("create-issue: "), 1)

    def test_the_issue_listing_is_shared_with_the_request_issues(self):
        self.assertIs(fq.work_item_issues.fetch_issues, work_item_issues.fetch_issues)


class WorkflowTests(unittest.TestCase):
    """explorer-data.yml's fixture queue steps and job, parsed with PyYAML."""

    @classmethod
    def setUpClass(cls):
        import yaml
        cls.wf = yaml.safe_load((ROOT / ".github/workflows/explorer-data.yml")
                                .read_text(encoding="utf-8"))
        cls.build = cls.wf["jobs"]["build"]
        cls.steps = {s.get("name"): s for s in cls.build["steps"]}

    def test_the_listing_holds_the_token_and_cannot_fail_the_job(self):
        step = self.steps["List the fixture requests and their pull requests"]
        self.assertIs(step["continue-on-error"], True)
        self.assertEqual(step["env"], {"GH_TOKEN": "${{ github.token }}"})
        run = step["run"]
        self.assertNotIn("${{", run)
        self.assertNotIn("set -e", run)
        self.assertEqual(run.strip().splitlines()[-1], "exit 0")
        self.assertIn("issues?state=all&labels=agent-ready", run)
        self.assertIn("pulls?state=all", run)
        printing = [line.strip() for line in run.splitlines()
                    if line.strip().split(" ", 1)[0] in ("echo", "cat", "printf", "jq")]
        self.assertEqual(printing, ['echo "fixture queue listings unavailable (exit $rc)"'])

    def test_the_report_runs_without_a_token_before_the_build(self):
        step = self.steps["Build the fixture queue report"]
        self.assertNotIn("env", step)
        self.assertEqual(step["id"], "queue")
        self.assertIn("scripts/fixture_queue.py report", step["run"])
        self.assertIn('--now "$(date -u +%Y-%m-%dT%H:%M:%SZ)"', step["run"])
        names = list(self.steps)
        self.assertLess(names.index("List the fixture requests and their pull requests"),
                        names.index("Build the fixture queue report"))
        self.assertLess(names.index("Build the fixture queue report"),
                        names.index("Build the explorer data"))
        self.assertIn('--fixture-queue "$RUNNER_TEMP/fixture-queue/fixture-queue.json"',
                      self.steps["Build the explorer data"]["run"])
        self.assertEqual(self.build["outputs"]["queue"], "${{ steps.queue.outputs.queue }}")

    def test_publish_ignores_only_the_moving_clocks(self):
        push = next(s for s in self.wf["jobs"]["publish"]["steps"]
                    if s["name"].startswith("Commit to"))["run"]
        # Schema 2: the activity listing's window moves with every build too.
        self.assertIn("strip='del(.generated_at, .source.results_commit, "
                      ".fixture_queue.generated_at, .activity.fetched_at, .activity.since)'", push)

    def test_the_alerts_job_writes_issues_only_from_a_built_report(self):
        job = self.wf["jobs"]["queue-alerts"]
        self.assertEqual(job["needs"], "build")
        self.assertEqual(job["if"], "needs.build.outputs.queue == 'true'")
        self.assertEqual(job["permissions"], {"contents": "read", "issues": "write"})
        self.assertNotIn("concurrency", job)
        writers = [name for name, j in self.wf["jobs"].items()
                   if (j.get("permissions") or {}).get("issues") == "write"]
        self.assertEqual(writers, ["queue-alerts"])
        checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@"))
        self.assertIs(checkout["with"]["persist-credentials"], False)
        run = next(s for s in job["steps"] if "fixture_queue.py alerts" in s.get("run", ""))
        self.assertNotRegex(run["run"], r"\$\{\{")
        self.assertEqual(run["env"]["GH_TOKEN"], "${{ github.token }}")


class DocsTests(unittest.TestCase):

    def test_the_workflow_table_and_the_docs_name_the_queue(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        row = next(line for line in agents.splitlines()
                   if line.startswith("  | `explorer-data.yml`"))
        for text in ("fixture_queue.py", "queue-alerts", "`pull-requests: read`",
                     "half-built-or-broken", "`issues: write`"):
            self.assertIn(text, row)
        supply = next(line for line in agents.splitlines()
                      if line.startswith("  | `routine-fixture-supply.yml`"))
        self.assertIn("paused", supply)
        self.assertIn("skills-evals#656", supply)
        docs = (ROOT / "docs" / "how-it-works.md").read_text(encoding="utf-8")
        for text in ("### Fixture requests", "`origin:`", "scripts/fixture_queue.py",
                     "fixture-queue-stale-request", "paused"):
            self.assertIn(text, docs)


if __name__ == "__main__":
    unittest.main()
