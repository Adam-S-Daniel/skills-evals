"""Allowance points from token counts by type (2026-11-20).

Eval runs are charged estimated weekly-allowance points, not dollars at a flat
rate: `evals/usage-weights.lock` pins the vendored `usage_weights` package and
its weight table, `harness/allowance_points.py` reads the lock (checking every
file's sha256) and prices a run's token counts, and the guard, the in-run
stop and the ingest check read that estimate.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR))

import test_issue_68_allowance_guard as base  # noqa: E402

import allowance_points as ap  # noqa: E402

budget, guard, run_eval, ingest = base.budget, base.guard, base.run_eval, base.ingest
LIMITS, NOW = base.LIMITS, base.NOW
REPO = Path(__file__).resolve().parents[2]
LOCK = REPO / "evals" / "usage-weights.lock"
RATE = 12.35

SONNET = "claude-sonnet-5-5"
TOKENS = {"input_tokens": 1_000_000, "output_tokens": 100_000,
          "cache_read_input_tokens": 500_000,
          "cache_creation_input_tokens": 200_000, "cost_usd": 1.0}


def block(model=SONNET, calls=1, **counts) -> dict:
    return {"calls": calls, "models": {model: {**TOKENS, **counts}}}


def points(*blocks, rate=None) -> dict:
    return ap.estimate_blocks([{"agent": b} for b in blocks], rate)


def mimic_vendor(tmp: Path) -> tuple[Path, Path]:
    """A copy of the vendored package and the lock, to damage."""
    vendor = tmp / "vendor"
    shutil.copytree(REPO / "vendor" / "usage_weights", vendor / "usage_weights",
                    ignore=shutil.ignore_patterns("__pycache__"))
    lock = tmp / "usage-weights.lock"
    shutil.copy(LOCK, lock)
    return lock, vendor


class TmpCase(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class LockTests(TmpCase):

    def test_the_committed_lock_matches_every_vendored_file(self):
        lock = ap.read_lock()
        self.assertEqual(lock["table"], "2026-11-20")
        self.assertIn("usage_weights/data/weights/2026-11-20.json", lock["files"])
        self.assertEqual(ap.table()["id"], lock["table"])

    def test_the_committed_lock_pins_the_source_repository_commit(self):
        lock = ap.read_lock()
        self.assertEqual(lock["repo"], "Adam-S-Daniel/claude-plan-usage-estimator")
        self.assertRegex(lock["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(lock["tag"], "v0.1.0")

    def test_a_short_commit_or_a_bare_repo_name_is_refused(self):
        for old, new, named in (
                ("commit: 990850e87b7ea19276dbeea631aaad9eba9f54e8", "commit: 990850e",
                 "`commit`"),
                ("repo: Adam-S-Daniel/claude-plan-usage-estimator",
                 "repo: claude-plan-usage-estimator", "`repo`")):
            with self.subTest(named=named):
                lock, vendor = mimic_vendor(self.tmp / named.strip("`"))
                text = lock.read_text(encoding="utf-8")
                self.assertIn(old, text)
                lock.write_text(text.replace(old, new), encoding="utf-8")
                with self.assertRaisesRegex(ap.LockError, named):
                    ap.read_lock(lock, vendor)

    def test_a_changed_byte_is_refused_naming_the_file(self):
        lock, vendor = mimic_vendor(self.tmp)
        self.assertEqual(ap.read_lock(lock, vendor)["table"], "2026-11-20")
        target = vendor / "usage_weights" / "estimate.py"
        data = bytearray(target.read_bytes())
        data[0] ^= 1
        target.write_bytes(bytes(data))
        with self.assertRaises(ap.LockError) as caught:
            ap.read_lock(lock, vendor)
        self.assertIn("usage_weights/estimate.py", str(caught.exception))

    def test_a_missing_lock_is_refused(self):
        _, vendor = mimic_vendor(self.tmp)
        with self.assertRaises(ap.LockError):
            ap.read_lock(self.tmp / "absent.lock", vendor)

    def test_a_lock_without_a_table_is_refused(self):
        lock, vendor = mimic_vendor(self.tmp)
        lines = [line for line in lock.read_text(encoding="utf-8").splitlines()
                 if not line.startswith("table:")]
        lock.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ap.LockError, "keys"):
            ap.read_lock(lock, vendor)

    def test_a_vendored_file_the_lock_does_not_name_is_refused(self):
        lock, vendor = mimic_vendor(self.tmp)
        (vendor / "usage_weights" / "extra.py").write_text("x = 1\n", encoding="utf-8")
        with self.assertRaises(ap.LockError) as caught:
            ap.read_lock(lock, vendor)
        self.assertIn("usage_weights/extra.py", str(caught.exception))

    def test_a_locked_file_that_is_missing_is_refused(self):
        lock, vendor = mimic_vendor(self.tmp)
        (vendor / "usage_weights" / "meter.py").unlink()
        with self.assertRaises(ap.LockError) as caught:
            ap.read_lock(lock, vendor)
        self.assertIn("usage_weights/meter.py", str(caught.exception))


class RoleRecordsTests(unittest.TestCase):

    def test_one_model_applies_the_cache_write_split_and_keeps_the_remainder(self):
        found = ap.role_records({**block(), "cache_creation": {
            "ephemeral_5m_input_tokens": 50_000,
            "ephemeral_1h_input_tokens": 120_000}})
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["model"], SONNET)
        self.assertEqual(found[0]["tokens"], {
            "input": 1_000_000, "output": 100_000, "cache_read": 500_000,
            "cache_write": 30_000, "cache_write_5m": 50_000,
            "cache_write_1h": 120_000})

    def test_a_split_larger_than_the_total_is_not_applied(self):
        found = ap.role_records({**block(), "cache_creation": {
            "ephemeral_5m_input_tokens": 150_000,
            "ephemeral_1h_input_tokens": 120_000}})
        self.assertEqual(found[0]["tokens"]["cache_write"], 200_000)
        self.assertNotIn("cache_write_5m", found[0]["tokens"])

    def test_two_models_leave_the_cache_writes_unsplit(self):
        two = {"calls": 2, "models": {
            SONNET: dict(TOKENS), "claude-haiku-5-5": dict(TOKENS)},
            "cache_creation": {"ephemeral_5m_input_tokens": 50_000,
                               "ephemeral_1h_input_tokens": 120_000}}
        found = ap.role_records(two)
        self.assertEqual(len(found), 2)
        for record in found:
            self.assertEqual(record["tokens"]["cache_write"], 200_000)
            self.assertNotIn("cache_write_5m", record["tokens"])

    def test_a_null_token_count_makes_the_role_unknown(self):
        self.assertIsNone(ap.role_records(block(output_tokens=None)))
        self.assertIsNone(ap.role_records(block(cache_creation_input_tokens=None)))
        self.assertIsNone(ap.role_records({"calls": 1, "models": None}))

    def test_a_role_with_no_calls_has_no_records(self):
        self.assertEqual(ap.role_records(block(calls=0)), [])
        self.assertEqual(ap.role_records({"calls": 0, "models": {}}), [])


class EstimateTests(unittest.TestCase):

    def test_tokens_are_priced_with_the_locked_table(self):
        weights = ap.table()["meters"]["all_models"]["models"][SONNET]
        got = points(block(input_tokens=1_000_000, output_tokens=0,
                           cache_read_input_tokens=0,
                           cache_creation_input_tokens=0))
        self.assertAlmostEqual(got["points"], weights["input"]["point"], places=9)
        self.assertEqual((got["roles_from_tokens"], got["legacy_roles"],
                          got["unpriced_roles"], got["complete"]), (1, 0, 0, True))

    def test_low_and_high_bracket_the_points(self):
        got = points(block())
        self.assertLessEqual(got["low"], got["points"])
        self.assertLessEqual(got["points"], got["high"])
        self.assertLess(got["low"], got["high"])

    def test_a_role_without_models_is_priced_from_its_dollars_at_the_legacy_rate(self):
        priced = {"calls": 1, "models": None, "cost_usd": 6.175}
        got = points(priced, rate=RATE)
        self.assertAlmostEqual(got["points"], 6.175 / RATE, places=12)
        self.assertAlmostEqual(got["low"], got["points"], places=12)
        self.assertAlmostEqual(got["high"], got["points"], places=12)
        self.assertEqual((got["legacy_roles"], got["legacy_usd"], got["complete"],
                          got["roles_from_tokens"], got["unpriced_roles"]),
                         (1, 6.175, False, 0, 0))

    def test_without_a_rate_such_a_role_is_unpriced(self):
        got = points({"calls": 1, "models": None, "cost_usd": 6.175})
        self.assertEqual((got["unpriced_roles"], got["legacy_roles"], got["points"],
                          got["complete"]), (1, 0, 0.0, False))

    def test_a_role_with_neither_tokens_nor_dollars_is_unpriced_even_with_a_rate(self):
        got = points({"calls": 1, "models": None, "cost_usd": None}, rate=RATE)
        self.assertEqual((got["unpriced_roles"], got["legacy_roles"]), (1, 0))

    def test_a_model_the_table_does_not_price_is_charged_its_own_dollars(self):
        got = points(block(model="claude-opus-4-8", cost_usd=2.47), rate=RATE)
        self.assertAlmostEqual(got["points"], 2.47 / RATE, places=12)
        self.assertEqual((got["legacy_roles"], got["roles_from_tokens"],
                          got["complete"]), (1, 1, False))

    def test_an_unpriced_model_without_a_rate_is_unpriced(self):
        got = points(block(model="claude-opus-4-8", cost_usd=2.47))
        self.assertEqual((got["unpriced_roles"], got["points"]), (1, 0.0))

    def test_a_role_that_made_no_call_adds_nothing(self):
        got = points(block(calls=0))
        self.assertEqual((got["points"], got["roles_from_tokens"],
                          got["unpriced_roles"], got["complete"]), (0.0, 0, 0, True))

    def test_the_fable_meter_counts_only_fable_records(self):
        fable = block(model="claude-fable-5-2")
        both = points(fable, block())
        only_sonnet = points(block())
        self.assertEqual(only_sonnet["fable"]["points"], 0.0)
        self.assertGreater(both["fable"]["points"], 0.0)
        self.assertAlmostEqual(both["fable"]["points"],
                               points(fable)["fable"]["points"], places=12)

    def test_blocks_add_without_rounding(self):
        one, two = points(block()), points(block(output_tokens=7))
        both = points(block(), block(output_tokens=7))
        self.assertAlmostEqual(both["points"], one["points"] + two["points"], places=12)


def telemetry_usage(role_blocks, budget_limits) -> dict:
    run_eval._TELEMETRY.begin(base.flags())
    run_eval._TELEMETRY.budget = dict(budget_limits)
    run_eval._TELEMETRY.role_blocks = list(role_blocks)
    return run_eval._TELEMETRY._run_level()


def every_points_figure(estimate: dict) -> dict:
    """The estimate's points figures by name (the Fable meter's included)."""
    return {"points": estimate["points"], "low": estimate["low"], "high": estimate["high"],
            **{f"fable.{k}": v for k, v in estimate["fable"].items()}}


class ScaleTests(unittest.TestCase):

    MIXED = [{"agent": block(), "judge": {"calls": 1, "models": None, "cost_usd": 3.0}}]

    def test_scale_multiplies_every_points_figure_and_nothing_else(self):
        plain = ap.estimate_blocks(self.MIXED, RATE)
        self.assertEqual(plain["legacy_roles"], 1)
        for scale in (2, 10, 0.5):
            with self.subTest(scale=scale):
                scaled = ap.estimate_blocks(self.MIXED, RATE, scale=scale)
                before, after = every_points_figure(plain), every_points_figure(scaled)
                self.assertGreater(before["points"], 0)
                for name, value in before.items():
                    self.assertAlmostEqual(after[name], value * scale, places=9, msg=name)
                for key in ("table", "roles_from_tokens", "legacy_roles", "legacy_usd",
                            "unpriced_roles", "complete"):
                    self.assertEqual(scaled[key], plain[key], key)

    def test_scale_one_leaves_the_ultra_numbers_exactly_as_they_were(self):
        self.assertEqual(ap.estimate_blocks(self.MIXED, RATE, scale=1),
                         ap.estimate_blocks(self.MIXED, RATE))

    def test_the_legacy_priced_part_is_scaled(self):
        dollars = [{"agent": {"calls": 1, "models": None, "cost_usd": 3.0}}]
        self.assertAlmostEqual(ap.estimate_blocks(dollars, RATE, scale=2)["points"],
                               2 * 3.0 / RATE, places=12)

    def test_a_session_estimate_takes_the_scale_too(self):
        models = block()["models"]
        self.assertAlmostEqual(ap.estimate_session(models, 1.0, RATE, scale=2)["points"],
                               2 * ap.estimate_session(models, 1.0, RATE)["points"], places=9)

    def test_a_bad_scale_is_refused(self):
        for scale in (0, -1, float("inf"), float("nan"), None, True, "2"):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                ap.estimate_blocks(self.MIXED, RATE, scale=scale)


class ReadingRangeTests(unittest.TestCase):

    def test_a_cli_reading_truncates_and_an_endpoint_reading_rounds(self):
        self.assertEqual(ap.reading_range(63, ap.CLI), (63.0, 64.0))
        self.assertEqual(ap.reading_range(63, ap.USAGE_ENDPOINT), (62.5, 63.5))

    def test_a_delta_is_the_later_range_less_the_earlier_one(self):
        self.assertEqual(ap.delta_range(63, 64, ap.CLI), (0.0, 2.0))
        self.assertEqual(ap.delta_range(63, 63, ap.CLI), (-1.0, 1.0))
        self.assertEqual(ap.delta_range(63, 66, ap.USAGE_ENDPOINT), (2.0, 4.0))

    def test_an_unknown_reader_is_refused(self):
        with self.assertRaises(ValueError):
            ap.reading_range(63, "guess")


class BudgetKeyTests(unittest.TestCase):

    def parse(self, rate) -> dict:
        return budget.parse_budget(base.VALID_BUDGET + f"legacy_usd_per_point: {rate}\n")

    def test_the_rate_is_dollars_per_point_with_no_upper_bound(self):
        for rate in (0.5, 12.35, 250, 1e9):
            with self.subTest(rate=rate):
                self.assertEqual(self.parse(rate)["legacy_usd_per_point"], float(rate))

    def test_the_rate_is_optional(self):
        self.assertNotIn("legacy_usd_per_point", budget.parse_budget(base.VALID_BUDGET))

    def test_a_bad_rate_is_refused_without_echoing_it(self):
        for name, rate in {"zero": "0", "negative": "-12.377", "bool": "true",
                           "nan": ".nan", "infinite": ".inf", "string": "'12.377'"}.items():
            with self.subTest(case=name):
                with self.assertRaises(budget.BudgetError) as caught:
                    self.parse(rate)
                self.assertIn("legacy_usd_per_point", str(caught.exception))
                self.assertNotIn("377", str(caught.exception))

    def test_points_per_usd_is_an_unknown_key(self):
        with self.assertRaisesRegex(budget.BudgetError, "unknown keys.*points_per_usd"):
            budget.parse_budget(base.VALID_BUDGET + "points_per_usd: 0.0015\n")

    def test_the_committed_budget_sets_the_rate(self):
        loaded = budget.load_budget()
        self.assertEqual(loaded["legacy_usd_per_point"], RATE)
        self.assertNotIn("points_per_usd", loaded)


class GuardChargeTests(TmpCase):

    def run_dir(self, suffix="a1b2c3") -> Path:
        path = self.tmp / "routine-results" / f"20261019T100000Z-{suffix}"
        path.mkdir(parents=True)
        return path

    def summary(self, run: Path, rel: str, usage: dict) -> None:
        path = run / rel / "summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"arm": "x", "usage": usage}), encoding="utf-8")

    def usage(self, agent, *, scope="trial", started="2026-10-19T10:00:00Z", delta=0.30):
        usage = base.usage_block(delta, started=started)
        usage["measured"].update(scope=scope, agent=agent)
        return usage

    def spent(self, limits=None) -> float:
        return guard.account(self.tmp, limits or {**LIMITS, "legacy_usd_per_point": RATE},
                             NOW, (0, 0), since=NOW - guard.WINDOW)["spent"]

    def test_token_bearing_trial_blocks_are_charged_their_points_not_a_larger_delta(self):
        run = self.run_dir()
        self.summary(run, "k/20261019T100000Z/with_skill/trial-1", self.usage(block()))
        # Measured cost (Adam, 2026-11-25) plus the routine session at its
        # per_run_overrun fallback (no eval_routine block in the tree).
        expected = points(block())["points"] / 100 + LIMITS["per_run_overrun"]
        self.assertLess(expected, 0.30 + LIMITS["per_run_overrun"])
        self.assertAlmostEqual(self.spent(), expected, places=12)

    def test_a_max5x_budget_is_charged_twice_the_ultra_estimate(self):
        run = self.run_dir()
        self.summary(run, "k/20261019T100000Z/with_skill/trial-1", self.usage(block()))
        ultra = {**LIMITS, "legacy_usd_per_point": RATE, "allowance_scale": 1}
        max5x = {**ultra, "allowance_scale": budget.ALLOWANCE_SCALE["max5x"]}
        overrun = LIMITS["per_run_overrun"]
        self.assertAlmostEqual(self.spent(max5x) - overrun, 2 * (self.spent(ultra) - overrun),
                               places=12)
        self.assertAlmostEqual(self.spent(ultra), points(block())["points"] / 100 + overrun,
                               places=12)

    def test_an_arm_scope_block_is_not_counted_twice(self):
        run = self.run_dir()
        self.summary(run, "k/20261019T100000Z/with_skill/trial-1", self.usage(block()))
        self.summary(run, "k/20261019T100000Z/with_skill", self.usage(
            block(), scope="arm"))
        expected = points(block())["points"] / 100 + LIMITS["per_run_overrun"]
        self.assertAlmostEqual(self.spent(), expected, places=12)

    def test_an_unpriced_role_falls_back_to_the_meter_delta(self):
        run = self.run_dir()
        self.summary(run, "k/20261019T100000Z/with_skill/trial-1", self.usage(
            {"calls": 1, "models": None, "cost_usd": None}, delta=0.02))
        self.assertAlmostEqual(self.spent(), 0.02 + LIMITS["per_run_overrun"], places=12)

    def test_a_dollars_only_role_is_charged_at_the_legacy_rate(self):
        run = self.run_dir()
        self.summary(run, "k/20261019T100000Z/with_skill/trial-1", self.usage(
            {"calls": 1, "models": None, "cost_usd": 3.0}))
        self.assertAlmostEqual(self.spent(), 3.0 / RATE / 100 + LIMITS["per_run_overrun"],
                               places=12)


class IngestCheckTests(unittest.TestCase):

    def estimate(self) -> dict:
        usage = telemetry_usage([{"agent": block()}, {"judge": block(
            model="claude-fable-5-2")}], {**LIMITS, "legacy_usd_per_point": RATE})
        return json.loads(json.dumps(usage["allowance_estimate"]))

    def check(self, estimate) -> None:
        ingest.check_allowance_estimate(estimate, "usage")

    def test_run_evals_own_output_is_accepted(self):
        estimate = self.estimate()
        self.assertGreater(estimate["points"], 0)
        self.check(estimate)

    def test_points_outside_low_to_high_are_rejected(self):
        for name, change in {"above high": {"points": 1000.0 - 1e-9, "high": 1.0},
                             "below low": {"low": 999.0}}.items():
            with self.subTest(case=name):
                with self.assertRaises(ingest.Rejected):
                    self.check({**self.estimate(), **change})

    def test_a_fable_range_that_does_not_hold_is_rejected(self):
        estimate = self.estimate()
        estimate["fable"] = {**estimate["fable"], "points": estimate["fable"]["high"] + 1}
        with self.assertRaises(ingest.Rejected):
            self.check(estimate)

    def test_a_wrong_complete_is_rejected(self):
        estimate = self.estimate()
        self.assertTrue(estimate["complete"])
        with self.assertRaisesRegex(ingest.Rejected, "complete"):
            self.check({**estimate, "complete": False})
        with self.assertRaisesRegex(ingest.Rejected, "complete"):
            self.check({**estimate, "legacy_roles": 1})

    def test_an_extra_or_missing_key_is_rejected(self):
        estimate = self.estimate()
        with self.assertRaisesRegex(ingest.Rejected, "unexpected keys"):
            self.check({**estimate, "extra": 1})
        del estimate["table"]
        with self.assertRaisesRegex(ingest.Rejected, "missing keys"):
            self.check(estimate)

    def test_a_negative_or_non_integer_count_is_rejected(self):
        for change in ({"unpriced_roles": -1}, {"legacy_roles": 1.5},
                       {"legacy_usd": -1.0}, {"table": "../x"}):
            with self.subTest(change=change):
                with self.assertRaises(ingest.Rejected):
                    self.check({**self.estimate(), **change})


class RunEvalTests(unittest.TestCase):

    def setUp(self):
        self.addCleanup(run_eval._TELEMETRY.begin)

    def test_the_run_stops_at_per_run_cap_on_its_own_estimate(self):
        cap = LIMITS["per_run_cap"]
        stop = run_eval.budget_stop_reading([(0.28, 1), (0.28, 1)], LIMITS, own=cap)
        self.assertEqual(stop, {"reason": "per_run_cap", "utilization": 0.28,
                                "moved": cap, "limit": cap})
        self.assertIsNone(run_eval.budget_stop_reading(
            [(0.28, 1), (0.28, 1)], LIMITS, own=cap - 1e-4))

    def test_the_own_estimate_overrides_a_meter_tick(self):
        self.assertIsNone(run_eval.budget_stop_reading(
            [(0.28, 1), (0.40, 1)], LIMITS, own=0.001))

    def test_the_usage_block_carries_the_allowance_estimate(self):
        usage = telemetry_usage([{"agent": block()}], {**LIMITS, "legacy_usd_per_point": RATE})
        self.assertEqual(usage["allowance_estimate"], points(block(), rate=RATE))

    def test_a_run_with_an_unpriced_role_falls_back_to_the_meter(self):
        run_eval._TELEMETRY.begin(base.flags())
        run_eval._TELEMETRY.budget = dict(LIMITS)
        run_eval._TELEMETRY.role_blocks = [
            {"agent": {"calls": 1, "models": None, "cost_usd": 0.5}}]
        now = datetime(2026, 10, 12, 17, 0, tzinfo=timezone.utc)
        run_eval._TELEMETRY.record("judge", [{
            "started": now, "ended": now, "outcome": "ok",
            "events": [{"at": None, "info": base.meter(week)}
                       for week in (0.70, 0.74)]}])
        self.assertEqual(run_eval._TELEMETRY.budget_stop()["reason"], "per_run_cap")

    def test_the_report_has_the_estimated_allowance_line(self):
        run_eval._TELEMETRY.begin(base.flags())
        run_eval._TELEMETRY.budget = {**LIMITS, "legacy_usd_per_point": RATE}
        run_eval._TELEMETRY.role_blocks = [{"agent": block()}]
        lines = run_eval._TELEMETRY.report_lines(None)
        found = [line for line in lines if line.startswith("- Estimated allowance")]
        self.assertEqual(len(found), 1)
        estimate = points(block(), rate=RATE)
        self.assertIn(f"{estimate['points']:.2f} points of the weekly meter", found[0])
        self.assertIn("weight table 2026-11-20", found[0])
        self.assertNotIn("without token counts", found[0])

    def test_the_report_line_names_a_role_priced_from_dollars(self):
        run_eval._TELEMETRY.begin(base.flags())
        run_eval._TELEMETRY.budget = {**LIMITS, "legacy_usd_per_point": RATE}
        run_eval._TELEMETRY.role_blocks = [
            {"agent": {"calls": 1, "models": None, "cost_usd": 2.0}}]
        line = [l for l in run_eval._TELEMETRY.report_lines(None)
                if l.startswith("- Estimated allowance")][0]
        self.assertIn("1 role total(s) without token counts priced from $2.00", line)


if __name__ == "__main__":
    unittest.main()
