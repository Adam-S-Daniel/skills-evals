"""The eval routine session's measured cost per fire (Adam, 2026-11-24:
"Make this measured cost thing automated and dynamic"): dashboard/build.py
writes spend/weekly.json `eval_routine` from the fire ledger, the schema and
ingest gate accept it, the allowance guard charges it once per run priced
from its own calls (falling back to `per_run_overrun`, and saying so), the
loop status estimate adds it, and the forecast takes its dollars as
`fire_overhead_usd`. Invented data only; `now` is passed in everywhere."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import allowance_guard as guard  # noqa: E402
import explorer_public  # noqa: E402
import forecast_catch_up as fc  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import loop_status  # noqa: E402
import test_issue_usage_weights as weights  # noqa: E402

spec = importlib.util.spec_from_file_location("dashboard_build_routine", ROOT / "dashboard" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

NOW = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)
SCHEMA = json.loads((ROOT / "explorer" / "schema.json").read_text(encoding="utf-8"))
RUNNER, OTHER = "trig_runner", "trig_other"


def iso(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def fire(trigger, days_ago, usd, model="model-a", n=[0]):
    n[0] += 1
    at = NOW - timedelta(days=days_ago)
    return {"trigger_id": trigger, "name": "x", "fired_at": iso(at),
            "finished_at": iso(at + timedelta(minutes=5)), "status": "success",
            "session_id": f"cse_{n[0]}", "total_cost_usd": usd, "last_served_model": model}


def spend_doc(routine=None, **extra):
    doc = {"schema": 1, "generated_at": iso(NOW), "weeks": [],
           "loop_jobs": {"as_of": iso(NOW), "points_per_week": 2.0, "usd_per_week": 20.0}}
    if routine is not None:
        doc["eval_routine"] = routine
    doc.update(extra)
    return doc


def routine_block(points=0.04, usd=0.5, fires=6, as_of=NOW - timedelta(hours=2)):
    return {"as_of": iso(as_of), "points_per_fire": points, "usd_per_fire": usd, "fires": fires}


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.inputs, self.config = self.tmp / "inputs", self.tmp / "config"
        write_json(self.inputs / "triggers.json",
                   {RUNNER: {"enabled": True, "name": "Eval runner"},
                    OTHER: {"enabled": True, "cron_expression": "0 9 * * *", "name": "Fleet worker"}})
        write_json(self.config / "routines.json", [])
        self.workflows = self.tmp / "workflows"
        self.workflows.mkdir()
        self.ledger = self.tmp / "routine-fires.jsonl"

    def ledger_rows(self, *rows):
        self.ledger.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def block(self):
        return build.eval_routine(self.inputs, self.config, str(self.workflows), NOW, str(self.ledger))

    def test_the_block_is_the_median_eval_runner_fire_of_the_last_14_days(self):
        self.ledger_rows(fire(RUNNER, 1, 0.30), fire(RUNNER, 3, 0.40), fire(RUNNER, 13, 0.90),
                         fire(RUNNER, 15, 9.0),  # outside the window
                         fire(OTHER, 1, 5.0))    # another task
        got = self.block()
        rate = build.legacy_usd_per_point()
        self.assertEqual(got["as_of"], iso(NOW))
        self.assertEqual(got["fires"], 3)
        self.assertAlmostEqual(got["usd_per_fire"], 0.40)
        self.assertAlmostEqual(got["points_per_fire"], 0.40 / rate)

    def test_a_fire_on_an_older_model_is_left_out(self):
        self.ledger_rows(fire(RUNNER, 5, 2.0, model="model-old"), fire(RUNNER, 1, 0.30),
                         fire(RUNNER, 2, 0.50))
        self.assertEqual(self.block()["fires"], 2)
        self.assertAlmostEqual(self.block()["usd_per_fire"], 0.40)

    def test_no_fire_in_the_window_or_no_ledger_leaves_the_block_out(self):
        self.ledger_rows(fire(RUNNER, 20, 0.30), fire(OTHER, 1, 5.0))
        self.assertIsNone(self.block())
        self.assertIsNone(build.eval_routine(self.inputs, self.config, str(self.workflows), NOW, None))

    def test_the_block_passes_the_schema_and_the_ingest_gate(self):
        self.ledger_rows(fire(RUNNER, 1, 0.30))
        doc = spend_doc(self.block())
        jsonschema.validate(doc, SCHEMA["$defs"]["spend_file"],
                            cls=jsonschema.validators.validator_for(SCHEMA))
        ingest.check_spend(doc, json.dumps(doc), "built")


class SchemaAndIngestTests(unittest.TestCase):
    def errors(self, doc):
        v = jsonschema.validators.validator_for(SCHEMA)(SCHEMA["$defs"]["spend_file"])
        return list(v.iter_errors(doc))

    def test_schema_refuses_a_bad_block(self):
        self.assertEqual(self.errors(spend_doc(routine_block())), [])
        for bad in ({**routine_block(), "fires": 0}, {**routine_block(), "points_per_fire": -1},
                    {**routine_block(), "task": "x"}, {"as_of": iso(NOW), "fires": 1}):
            self.assertTrue(self.errors(spend_doc(bad)), bad)

    def test_ingest_refuses_another_key_in_it(self):
        doc = spend_doc({**routine_block(), "session_id": "cse_x"})
        with self.assertRaises(ingest.Rejected):
            ingest.check_spend(doc, json.dumps(doc), "bad")

    def test_the_public_export_never_copies_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_json(Path(tmp) / "spend" / "weekly.json",
                       spend_doc(routine_block(), weeks=[{"week": "2026-11-23", "eval_runs": 1}]))
            got = explorer_public.build_spend(Path(tmp), True)
        self.assertIsNotNone(got)
        self.assertNotIn("eval_routine", json.dumps(got))


class GuardTests(weights.TmpCase):
    """A run priced from its own calls is charged its routine session once."""

    run_dir = weights.GuardChargeTests.run_dir
    summary = weights.GuardChargeTests.summary
    usage = weights.GuardChargeTests.usage
    LIMITS = {**weights.LIMITS, "legacy_usd_per_point": weights.RATE}

    def state(self):
        return guard.account(self.tmp, self.LIMITS, weights.NOW, (0, 0),
                             since=weights.NOW - guard.WINDOW)

    def put(self, routine):
        write_json(self.tmp / "spend" / "weekly.json",
                   spend_doc(routine, generated_at=iso(weights.NOW)))

    def own_points(self):
        return weights.points(weights.block())["points"] / 100

    def test_a_priced_run_is_charged_the_measured_routine_session_once(self):
        run = self.run_dir()
        self.summary(run, "k/20261019T100000Z/with_skill/trial-1", self.usage(weights.block()))
        self.summary(run, "j/20261019T101000Z/with_skill/trial-1",
                     self.usage(weights.block(), started="2026-10-19T10:10:00Z"))
        self.put(routine_block(points=0.04, as_of=weights.NOW - timedelta(hours=1)))
        st = self.state()
        # Two invocations in one run (one fire): the session is charged once.
        self.assertAlmostEqual(st["spent"], 2 * self.own_points() + 0.0004, places=12)
        self.assertAlmostEqual(st["eval_routine_per_fire"], 0.0004)
        self.assertIn("measured: median of 6", st["eval_routine_source"])
        self.assertIn("0.04 points for its routine session", guard.describe(st))

    def test_a_missing_or_stale_block_falls_back_to_per_run_overrun_and_says_so(self):
        run = self.run_dir()
        self.summary(run, "k/20261019T100000Z/with_skill/trial-1", self.usage(weights.block()))
        overrun = self.LIMITS["per_run_overrun"]
        cases = {"is missing": None,
                 "more than 3 days ago": routine_block(as_of=weights.NOW - timedelta(days=3, seconds=1)),
                 "is malformed": routine_block(fires=0),
                 "ahead of the clock": routine_block(as_of=weights.NOW + timedelta(hours=2))}
        for words, routine in cases.items():
            with self.subTest(words):
                self.put(routine)
                st = self.state()
                self.assertAlmostEqual(st["spent"], self.own_points() + overrun, places=12)
                self.assertIn("per_run_overrun, as a fallback", st["eval_routine_source"])
                self.assertIn(words, st["eval_routine_source"])
                self.assertIn("as a fallback", guard.describe(st))

    def test_a_run_charged_by_its_meter_delta_gets_no_second_session_charge(self):
        # Its per_run_overrun already covers the routine session.
        run = self.run_dir()
        self.summary(run, "k/20261019T100000Z/with_skill/trial-1",
                     self.usage({"calls": 1, "models": None, "cost_usd": None}))
        self.put(routine_block(points=0.04))
        st = self.state()
        self.assertAlmostEqual(st["spent"], 0.30 + self.LIMITS["per_run_overrun"], places=12)


class LoopStatusTests(unittest.TestCase):
    def test_the_estimate_adds_the_session_to_each_priced_run(self):
        since = guard.window_start(NOW)
        runs = [Path("a"), Path("b")]
        priced = {runs[0]: {"points": 0.06}, runs[1]: None}
        state = {"loop_reserve": 0.0, "improve_matched_cost": 0.0, guard.ROUTINE_CHARGE: 0.0004}
        limits = {"per_run_overrun": 0.0005, "legacy_usd_per_point": 12.35}
        with unittest.mock.patch.object(guard, "ingested_runs", return_value=runs), \
                unittest.mock.patch.object(guard, "run_points", side_effect=lambda r, *_: priced[r]), \
                unittest.mock.patch.object(guard, "run_cost", return_value=0.0015):
            spend = loop_status.estimated_spend(Path("."), limits, NOW, since, state)
        # The unpriced run's run_cost already holds its session charge.
        self.assertAlmostEqual(spend["evals"], 0.0006 + 0.0004 + 0.0015)

    def test_the_forecast_reruns_every_15_minutes_by_default(self):
        captured = {}
        with unittest.mock.patch.object(loop_status, "collect",
                                        side_effect=lambda a, now: captured.update(a=a) or {}), \
                unittest.mock.patch("sys.stdout"):
            loop_status.main(["collect", "--work", "w"], now=NOW)
        self.assertEqual(captured["a"].forecast_every_minutes, 15)


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree = Path(self._tmp.name)

    def resolve(self, given=None):
        assumptions, sources = dict(given or {}), {}
        fc.fire_overhead(self.tree, NOW, assumptions, sources)
        return assumptions, sources

    def test_the_measured_fire_overrides_the_default(self):
        write_json(self.tree / "spend" / "weekly.json", spend_doc(routine_block(usd=0.37)))
        assumptions, sources = self.resolve()
        self.assertEqual(assumptions["fire_overhead_usd"], 0.37)
        self.assertIn("spend/weekly.json eval_routine", sources["fire_overhead_usd"])

    def test_without_it_the_default_stays_and_is_named_as_the_fallback(self):
        assumptions, sources = self.resolve()
        self.assertNotIn("fire_overhead_usd", assumptions)
        self.assertTrue(sources["fire_overhead_usd"].startswith(
            f"fallback {fc.ASSUMPTION_KEYS['fire_overhead_usd'][0]}"))

    def test_a_given_value_wins(self):
        write_json(self.tree / "spend" / "weekly.json", spend_doc(routine_block(usd=0.37)))
        assumptions, sources = self.resolve({"fire_overhead_usd": 1.0})
        self.assertEqual(assumptions["fire_overhead_usd"], 1.0)
        self.assertNotIn("fire_overhead_usd", sources)


if __name__ == "__main__":
    unittest.main()
