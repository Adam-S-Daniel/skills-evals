#!/usr/bin/env python3
"""#577: charge improve fires their measured cost.

`scripts/allowance_guard.py` reads `improve-costs/<run id>.json` from the
results tree (#572 part 1) and, for each improve or guidance-improve fire:

  * matches it one-to-one, oldest first, to the record of its mode and
    target whose run id's stamp falls within -2/+30 minutes of the fire's
    `run_started_at`, and charges the record's measured dollars at
    `points_per_usd` instead of `improve_charge`; unmatched fires keep that
    rule;
  * recomputes `IMPROVE_FIRE_UNITS` from the records' dollar measures (the
    75th percentile once at least 6 records measured something, the largest
    before that), flagging brackets whose busy/span ratio is low.

Two recording gaps from the #572 review ride along: a failed `claude -p`
proposal call records `{calls: 1, usd: null}`, and the proposal's cache
tokens are left out on purpose (its `usd` already includes them).

Hermetic: records are fixture JSON in a temp tree; `now` is passed in.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent.parent
ROOT = TEST_DIR.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))

import allowance_guard as guard  # noqa: E402
import improve_cost  # noqa: E402
import propose_skill_edit as pse  # noqa: E402

NOW = datetime(2026, 11, 12, 12, 0, 0, tzinfo=timezone.utc)
START = datetime(2026, 11, 10, 8, 0, 0, tzinfo=timezone.utc)
LIMITS = {"weekly_cap": 0.25, "per_run_cap": 0.01, "per_run_overrun": 0.0005,
          "stop_when_account_above": 0.80, "points_per_usd": 0.0015}
SINCE = datetime(2026, 11, 9, 17, 0, 0, tzinfo=timezone.utc)


def stamp(at: datetime, suffix: str = "a1b2c3") -> str:
    return at.strftime("%Y%m%dT%H%M%SZ") + "-" + suffix


def record(run_id: str, mode: str = "improve", target: str = "demo-skill", *,
           agent: float = 2.0, judge: float = 0.0, guard_usd: float = 0.0,
           proposal: float | None = 0.25, trigger_calls=None, busy=900.0,
           span=900.0, delta=0.0, stage: str = "candidate") -> dict:
    """One valid cost record as `improve_cost.summarize` writes it."""
    base = datetime.strptime(run_id[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)

    def at(when: datetime) -> str:
        return when.strftime("%Y-%m-%dT%H:%M:%S.000000Z")

    trials = 0 if stage == "none" else 2
    measured = stage != "none"
    doc = {
        "schema_version": 1, "run_id": run_id, "mode": mode, "target": target,
        "exit_code": 0 if stage == "candidate" else 1,
        "outcome": "accepted" if stage == "candidate" else "rejected",
        "stage_reached": stage, "trial_summaries": trials, "agent_calls": trials,
        "judge_calls": 0, "agent_usd": agent, "judge_usd": judge, "guard_usd": guard_usd,
        "usd_unpriced_trials": 0,
        "sides": {"baseline": {"trials": trials // 2, "usd": (agent + judge + guard_usd) / 2},
                  "candidate": {"trials": trials // 2, "usd": (agent + judge + guard_usd) / 2}},
        "proposal": None if proposal is None else
        {"calls": 1, "usd": proposal, "input_tokens": 2, "output_tokens": 10},
        "trigger_calls": trigger_calls,
        "models": {"arm": "claude-sonnet-5-5", "proposal": None},
        "busy_seconds": busy if measured else None,
        "span_seconds": span if measured else None,
        "snapshots": 4 if measured else 0, "omitted": 0,
        "first": None, "last": None,
        "delta": delta if measured else None,
        "delta_reason": "measured" if measured else "fewer_than_two_snapshots",
        "ended_at": at(base + timedelta(minutes=40)),
    }
    if measured:
        doc["first"] = {"at": at(base + timedelta(minutes=10)), "utilization": 0.2,
                        "resets_at": 1794848400}
        doc["last"] = {"at": at(base + timedelta(minutes=25)), "utilization": 0.2 + delta,
                       "resets_at": 1794848400}
    return doc


def fire(started: datetime = START, mode: str = "improve", target: str = "demo-skill") -> dict:
    return {"mode": mode, "target": target, "started": started}


class TreeCase(unittest.TestCase):

    def setUp(self):
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree, ignore_errors=True)

    def put(self, doc: dict, name: str | None = None) -> Path:
        path = self.tree / "improve-costs" / f"{name or doc['run_id']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        return path

    def account(self, fires, limits=None, **kwargs):
        started = [f["started"] for f in fires]
        return guard.account(self.tree, limits or LIMITS, NOW,
                             (len(fires), 0), (len(fires), 0), since=SINCE,
                             improve_started=started, improve_fires=fires, **kwargs)


class FixtureTests(TreeCase):

    def test_the_fixture_records_meet_the_schema(self):
        for doc in (record(stamp(START)), record(stamp(START), stage="none"),
                    record(stamp(START), proposal=None, trigger_calls=60)):
            improve_cost.check_record(doc)


class MatchingTests(TreeCase):

    def test_a_matched_fire_is_charged_its_measured_dollars(self):
        doc = record(stamp(START + timedelta(seconds=5)), agent=2.0, judge=0.5,
                     guard_usd=0.25, proposal=0.25)
        self.put(doc)
        state = self.account([fire()])
        # 3.0 dollars at 0.0015 points per dollar, full precision.
        self.assertAlmostEqual(state["spent"], 3.0 * 0.0015, places=15)
        self.assertEqual(state["improve_matched"], 1)
        self.assertEqual(state["pending"], 0.0)
        self.assertEqual(state["improve_fires"], 1)
        self.assertIn("1 matched to a cost record", guard.describe(state))

    def test_an_unmatched_fire_keeps_the_improve_charge(self):
        state = self.account([fire()])
        self.assertEqual(state["improve_matched"], 0)
        self.assertAlmostEqual(state["pending"], state["improve_charge"], places=15)
        self.assertEqual(state["spent"], 0.0)

    def test_the_window_is_two_minutes_before_to_thirty_after(self):
        cases = [(-120, True), (-121, False), (0, True), (1800, True), (1801, False)]
        for offset, expected in cases:
            with self.subTest(offset=offset):
                shutil.rmtree(self.tree / "improve-costs", ignore_errors=True)
                self.put(record(stamp(START + timedelta(seconds=offset))))
                self.assertEqual(self.account([fire()])["improve_matched"],
                                 1 if expected else 0)

    def test_mode_and_target_must_agree(self):
        self.put(record(stamp(START), mode="improve", target="demo-skill"))
        for other in (fire(mode="guidance-improve", target="demo-skill"),
                      fire(mode="improve", target="other-skill")):
            with self.subTest(fire=other):
                self.assertEqual(self.account([other])["improve_matched"], 0)

    def test_matching_is_one_to_one_oldest_first(self):
        self.put(record(stamp(START + timedelta(minutes=1))))
        older, newer = fire(START), fire(START + timedelta(minutes=5))
        state = self.account([newer, older])
        self.assertEqual(state["improve_matched"], 1)
        # The older fire took the record, the newer one is charged the unit.
        self.assertAlmostEqual(state["pending"], state["improve_charge"], places=15)
        self.assertEqual(state["improve_started_unmatched"], [newer["started"]])

    def test_two_records_match_two_fires_each_once(self):
        first = record(stamp(START + timedelta(seconds=3), "aaaaaa"), agent=1.0, proposal=0.0)
        second = record(stamp(START + timedelta(minutes=6), "bbbbbb"), agent=3.0, proposal=0.0)
        self.put(first)
        self.put(second)
        state = self.account([fire(START), fire(START + timedelta(minutes=5))])
        self.assertEqual(state["improve_matched"], 2)
        self.assertAlmostEqual(state["spent"], 4.0 * 0.0015, places=15)
        self.assertEqual(state["pending"], 0.0)

    def test_a_record_with_no_trial_is_a_matched_fire_that_cost_nothing(self):
        self.put(record(stamp(START), stage="none", agent=0, proposal=None))
        state = self.account([fire()])
        self.assertEqual(state["improve_matched"], 1)
        self.assertEqual(state["spent"], 0.0)

    def test_an_incomplete_dollar_measure_without_a_clean_bracket_keeps_the_unit_charge(self):
        # 60 trigger-loop calls report no cost: the dollars are a floor only.
        self.put(record(stamp(START), trigger_calls=60, busy=100.0, span=900.0))
        state = self.account([fire()])
        self.assertEqual(state["improve_matched"], 1)
        self.assertAlmostEqual(state["spent"], state["improve_charge"], places=15)
        self.assertEqual(state["pending"], 0.0)

    def test_an_incomplete_measure_with_a_clean_bracket_takes_the_larger_of_dollars_and_delta(self):
        for delta, expected in ((0.02, 0.02), (0.0, 2.25 * 0.0015)):
            with self.subTest(delta=delta):
                shutil.rmtree(self.tree / "improve-costs", ignore_errors=True)
                self.put(record(stamp(START), trigger_calls=60, busy=800.0,
                                span=900.0, delta=delta))
                self.assertAlmostEqual(self.account([fire()])["spent"], expected, places=15)

    def test_a_failed_proposal_call_makes_the_measure_incomplete(self):
        doc = record(stamp(START), busy=100.0, span=900.0)
        doc["proposal"] = {"calls": 1, "usd": None, "input_tokens": None,
                           "output_tokens": None}
        improve_cost.check_record(doc)
        self.put(doc)
        state = self.account([fire()])
        self.assertAlmostEqual(state["spent"], state["improve_charge"], places=15)

    def test_no_dollar_rate_means_no_matching(self):
        self.put(record(stamp(START)))
        limits = {k: v for k, v in LIMITS.items() if k != "points_per_usd"}
        state = self.account([fire()], limits)
        self.assertEqual(state["improve_matched"], 0)

    def test_untrusted_files_are_ignored(self):
        good = record(stamp(START))
        self.put(good, name="not-a-run-id")
        bad = copy.deepcopy(good)
        bad["agent_usd"] = -1
        self.put(bad)
        self.assertEqual(self.account([fire()])["improve_matched"], 0)
        shutil.rmtree(self.tree / "improve-costs")
        path = self.put(good)
        path.write_text(path.read_text() + " " * 5000, encoding="utf-8")  # oversize
        self.assertEqual(self.account([fire()])["improve_matched"], 0)
        path.unlink()
        target = self.tree / "elsewhere.json"
        target.write_text(json.dumps(good), encoding="utf-8")
        path.symlink_to(target)
        self.assertEqual(self.account([fire()])["improve_matched"], 0)
        path.unlink()
        path.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.account([fire()])["improve_matched"], 0)

    def test_fire_details_must_agree_with_the_count(self):
        with self.assertRaises(guard.GuardError):
            guard.account(self.tree, LIMITS, NOW, (2, 0), (2, 0), since=SINCE,
                          improve_started=[START], improve_fires=[fire()])


class ReadingBoundTests(TreeCase):
    """A matched fire counts in the reading bound like an eval run: inside
    the reading when it finished before it, charged in full after it."""

    def run_dir(self, at: datetime, week: float = 0.30):
        run = self.tree / "routine-results" / stamp(at.replace(hour=1), "ffffff")
        path = run / "k" / "20261110T010000Z" / "with_skill" / "summary.json"
        path.parent.mkdir(parents=True)
        resets = int((NOW + timedelta(days=2)).timestamp())
        shot = {"at": at.strftime("%Y-%m-%dT%H:%M:%S.123Z"), "at_source": "cli_message",
                "info": {"unifiedWindows": {"seven_day": {"utilization": week,
                                                          "resetsAt": resets}}}}
        path.write_text(json.dumps({"arm": "x", "usage": {
            "started_at": "2026-11-10T01:00:00Z", "ended_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "meter_delta": None,
            "measured": {"scope": "trial", "meter": {"snapshots": [shot], "omitted": 0}}}}),
            encoding="utf-8")

    def baseline(self):
        """The bound with no improve fire at all."""
        return guard.account(self.tree, LIMITS, NOW, (0, 0), (0, 0), since=SINCE)["bound"]

    def test_a_matched_fire_after_the_reading_adds_its_cost_to_the_bound(self):
        reading = NOW - timedelta(hours=1)
        self.run_dir(reading)
        self.put(record(stamp(NOW - timedelta(minutes=30)), agent=2.0, proposal=0.0))
        state = self.account([fire(NOW - timedelta(minutes=31))])
        self.assertEqual(state["improve_covered"], 0)
        self.assertAlmostEqual(state["bound"], self.baseline() + 2.0 * 0.0015, places=12)

    def test_a_matched_fire_before_the_reading_is_already_inside_it(self):
        reading = NOW - timedelta(hours=1)
        self.run_dir(reading)
        started = reading - guard.IMPROVE_MAX_RUN - timedelta(minutes=5)
        self.put(record(stamp(started + timedelta(seconds=10)), agent=2.0, proposal=0.0))
        state = self.account([fire(started)])
        self.assertEqual(state["improve_matched"], 1)
        # Not added to the bound (the reading holds it) and not held again.
        self.assertAlmostEqual(state["bound"], self.baseline(), places=12)
        self.assertAlmostEqual(state["eval_inside"], 2.0 * 0.0015, places=12)


class MainWiringTests(TreeCase):

    def test_main_matches_with_the_fire_details(self):
        self.put(record(stamp(START)))
        budget_file = self.tree / "budget.yml"
        budget_file.write_text(
            "weekly_cap: 0.25\nper_run_cap: 0.01\nper_run_overrun: 0.0005\n"
            "stop_when_account_above: 0.80\npoints_per_usd: 0.0015\n", encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = guard.main(["check", "--results-tree", str(self.tree), "--budget",
                               str(budget_file), "--mode", "improve"], now=NOW,
                              fire_count=lambda now: (1, 0),
                              improve_count=lambda now: (1, 0),
                              improve_starts=lambda now: [START],
                              improve_details=lambda now: [fire()])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("1 matched to a cost record", out.getvalue())

    def test_the_live_fetch_names_each_fire_by_mode_and_target(self):
        runs = [
            {"id": 7, "display_title": "Fire eval routine: improve demo-skill",
             "run_started_at": "2026-11-10T08:00:00Z", "status": "completed",
             "conclusion": "success"},
            {"id": 8, "display_title": "Fire eval routine: guidance-improve some-section",
             "run_started_at": "2026-11-10T09:00:00Z", "status": "completed",
             "conclusion": "success"},
            {"id": 9, "display_title": "Fire eval routine: improve failed-skill",
             "run_started_at": "2026-11-10T10:00:00Z", "status": "completed",
             "conclusion": "failure"},
        ]
        details = guard.improve_details(runs, NOW, SINCE)
        self.assertEqual(details, [
            {"mode": "improve", "target": "demo-skill",
             "started": datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc)},
            {"mode": "guidance-improve", "target": "some-section",
             "started": datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)}])


# The five records on persistent/eval-results (2026-11-13) that measured
# anything: agent + judge + guard + proposal dollars, in run-id order, and the
# mean dollars of the 1122 priced ingested eval runs.
REAL_FIRE_DOLLARS = [
    5.723102399999999 + 1.3598100000000002 + 2.6758805 + 0.70939225,
    2.4127806 + 0 + 0 + 0.19781225000000002,
    5.0551632 + 0.9036359 + 1.7553433000000005 + 0.4204358,
    2.4883146000000003 + 0.12502580000000002,
    2.8653758999999996 + 0.16012579999999998,
]
REAL_EVAL_RUN_DOLLARS = 0.8574372249019607


class UnitsTests(TreeCase):

    def records(self, dollars):
        return [record(stamp(START + timedelta(hours=i), f"{i:06x}"), agent=usd,
                       proposal=0.0) for i, usd in enumerate(dollars)]

    def test_fewer_than_six_measured_records_use_the_largest(self):
        result = guard.recompute_improve_units(self.records([3.0, 9.0, 6.0]), 1.5)
        self.assertEqual(result["basis"], "maximum")
        self.assertEqual(result["measured"], 3)
        self.assertAlmostEqual(result["units"], 9.0 / 1.5, places=12)

    def test_six_or_more_use_the_75th_percentile(self):
        result = guard.recompute_improve_units(
            self.records([1.0, 2.0, 3.0, 4.0, 5.0, 10.0]), 1.0)
        self.assertEqual(result["basis"], "75th percentile")
        # Linear interpolation: rank 0.75 * 5 = 3.75 between 4.0 and 5.0.
        self.assertAlmostEqual(result["units"], 4.75, places=12)

    def test_records_with_no_trial_are_not_measurements(self):
        records = self.records([3.0, 9.0, 6.0, 4.0, 5.0, 7.0])
        records += [record(stamp(START + timedelta(days=1, minutes=i), f"{i:06x}"),
                           stage="none", agent=0, proposal=None, trigger_calls=60)
                    for i in range(12)]
        result = guard.recompute_improve_units(records, 1.0)
        self.assertEqual(result["measured"], 6)
        self.assertEqual(result["records"], 18)
        self.assertAlmostEqual(result["units"], 6.75, places=12)

    def test_a_low_busy_over_span_bracket_is_flagged(self):
        records = self.records([3.0, 9.0])
        records[1]["busy_seconds"] = 100.0
        result = guard.recompute_improve_units(records, 1.0)
        self.assertEqual(result["contaminated"], [records[1]["run_id"]])
        clean = guard.recompute_improve_units(self.records([3.0]), 1.0)
        self.assertEqual(clean["contaminated"], [])

    def test_the_committed_units_are_the_recomputed_ones(self):
        records = self.records(REAL_FIRE_DOLLARS)
        result = guard.recompute_improve_units(records, REAL_EVAL_RUN_DOLLARS)
        self.assertEqual(result["basis"], "maximum")
        self.assertAlmostEqual(guard.IMPROVE_FIRE_UNITS, result["units"], places=12)

    def test_the_eval_run_mean_reads_priced_invocations_only(self):
        for name, usd in (("20261105T100000Z-aaaaaa", 1.0), ("20261105T110000Z-bbbbbb", 3.0),
                          ("20261105T120000Z-cccccc", None)):
            path = self.tree / "routine-results" / name / "k" / "s" / "summary.json"
            path.parent.mkdir(parents=True)
            usage = {"started_at": "2026-11-05T10:00:00Z", "meter_delta": None}
            if usd is not None:
                usage["cost_estimate"] = {"usd": usd}
            path.write_text(json.dumps({"usage": usage}), encoding="utf-8")
        self.assertEqual(guard.eval_run_dollars(self.tree), 2.0)
        self.assertIsNone(guard.eval_run_dollars(self.tree / "nowhere"))

    def test_the_units_command_prints_the_computation(self):
        for doc in self.records([3.0, 9.0]):
            self.put(doc)
        path = self.tree / "routine-results" / "20261105T100000Z-aaaaaa" / "k" / "s" / "summary.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"usage": {"cost_estimate": {"usd": 1.5},
                                              "meter_delta": None}}), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = guard.main(["units", "--results-tree", str(self.tree)], now=NOW)
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("maximum", text)
        self.assertIn("6.0 units", text)


class ProposalGapTests(unittest.TestCase):
    """The two recording gaps from the #572 review (2026-11-02)."""

    def run_propose(self, side_effect=None, proc=None):
        @contextlib.contextmanager
        def env():
            yield {"CLAUDE_BIN": "claude"}

        runner = pse.Runner()
        with mock.patch.object(pse, "guarded_environment", env), \
                mock.patch.object(pse.subprocess, "run", side_effect=side_effect,
                                  return_value=proc):
            try:
                runner.propose("prompt", "claude-x")
            except pse.Refusal:
                pass
        return runner

    UNPRICED = {"calls": 1, "usd": None, "input_tokens": None, "output_tokens": None}

    def test_a_timed_out_call_is_recorded_as_one_unpriced_call(self):
        runner = self.run_propose(side_effect=subprocess.TimeoutExpired("claude", 600))
        self.assertEqual(runner.last_usage, self.UNPRICED)

    def test_a_nonzero_exit_and_unreadable_output_are_recorded_too(self):
        for proc in (subprocess.CompletedProcess([], 1, "", "boom"),
                     subprocess.CompletedProcess([], 0, "not json", ""),
                     subprocess.CompletedProcess([], 0, json.dumps({"result": "x"}), "")):
            with self.subTest(returncode=proc.returncode, out=proc.stdout):
                self.assertEqual(self.run_propose(proc=proc).last_usage, self.UNPRICED)

    def test_a_call_that_never_started_is_not_recorded(self):
        runner = self.run_propose(side_effect=FileNotFoundError("claude"))
        self.assertIsNone(runner.last_usage)

    def test_the_cache_tokens_are_not_kept_and_the_dollars_stay(self):
        reply = {"result": "x", "total_cost_usd": 0.5,
                 "usage": {"input_tokens": 3, "output_tokens": 4,
                           "cache_read_input_tokens": 99,
                           "cache_creation_input_tokens": 98}}
        usage = pse.proposal_usage(reply)
        self.assertEqual(usage, {"calls": 1, "usd": 0.5, "input_tokens": 3,
                                 "output_tokens": 4})

    def test_the_unpriced_record_is_read_and_checked(self):
        results = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, results)
        (results / "proposal-20261102T120005Z.json").write_text(
            json.dumps(self.UNPRICED), encoding="utf-8")
        self.assertEqual(improve_cost.read_proposal(results), self.UNPRICED)
        doc = record(stamp(START), proposal=None)
        doc["proposal"] = dict(self.UNPRICED)
        improve_cost.check_record(doc)
        doc["proposal"]["usd"] = "x"
        with self.assertRaises(improve_cost.Invalid):
            improve_cost.check_record(doc)


if __name__ == "__main__":
    unittest.main()
