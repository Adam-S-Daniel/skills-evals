"""The allowance guard reserves the loop's own automatic jobs out of the cap
(Adam, 2026-11-15): the producer (dashboard/build.py `loop_jobs`), the schema
and ingest gate, and the guard's reduced cap and refusals. The planner's use
of the reduced cap is tested in test_issue_batch_fit_budget.py. Invented data
only; `now` is passed in everywhere."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness"))
import allowance_guard as guard  # noqa: E402
import explorer_public  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402

spec = importlib.util.spec_from_file_location("dashboard_build_reserve", ROOT / "dashboard" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

NOW = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)
LIMITS = {"weekly_cap": 0.25, "per_run_cap": 0.01, "per_run_overrun": 0.005,
          "stop_when_account_above": 0.80, "points_per_usd": 0.0015}
SCHEMA = json.loads((ROOT / "explorer" / "schema.json").read_text(encoding="utf-8"))


def iso(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def spend_doc(points=2.1, as_of=NOW - timedelta(hours=2), **extra) -> dict:
    doc = {"schema": 1, "generated_at": iso(NOW), "weeks": [],
           "loop_jobs": {"as_of": iso(as_of), "points_per_week": points, "usd_per_week": 14.0}}
    doc.update(extra)
    return doc


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.inputs, self.config = self.tmp / "inputs", self.tmp / "config"
        write_json(self.inputs / "triggers.json",
                   {"t1": {"enabled": True, "cron_expression": "0 9 * * *"}})
        write_json(self.config / "routines.json",
                   [{"name": "Dashboard refresh", "source": {"kind": "trigger", "id": "t1"}}])
        self.ledger = self.tmp / "routine-fires.jsonl"
        row = {"trigger_id": "t1", "name": "Dashboard refresh", "fired_at": "2026-11-15T09:00:00Z",
               "finished_at": "2026-11-15T09:30:00Z", "status": "success",
               "session_id": "cse_a", "total_cost_usd": 2.0, "last_served_model": "model-a"}
        self.ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")

    def test_loop_jobs_is_the_measured_meter_use_in_points(self):
        got = build.loop_jobs(self.inputs, self.config, None, NOW, str(self.ledger))
        # One daily fire at $2 is $14 a week; 0.0015 of the allowance per dollar is 2.1 points.
        self.assertEqual(got["as_of"], iso(NOW))
        self.assertAlmostEqual(got["usd_per_week"], 14.0)
        self.assertAlmostEqual(got["points_per_week"], 2.1)

    def test_without_a_ledger_there_is_no_block(self):
        self.assertIsNone(build.loop_jobs(self.inputs, self.config, None, NOW, None))
        self.assertIsNone(build.loop_jobs(self.inputs, self.config, None, NOW,
                                          str(self.tmp / "missing.jsonl")))

    def test_the_block_passes_the_schema_and_the_ingest_gate(self):
        import jsonschema
        doc = spend_doc()
        doc["loop_jobs"] = build.loop_jobs(self.inputs, self.config, None, NOW, str(self.ledger))
        jsonschema.validate(doc, SCHEMA["$defs"]["spend_file"],
                            cls=jsonschema.validators.validator_for(SCHEMA))
        ingest.check_spend(doc, json.dumps(doc), "built")


class SchemaAndIngestTests(unittest.TestCase):
    def validator(self):
        import jsonschema
        return jsonschema.validators.validator_for(SCHEMA)(SCHEMA["$defs"]["spend_file"])

    def test_schema_accepts_the_block_and_the_file_without_it(self):
        v = self.validator()
        self.assertEqual(list(v.iter_errors(spend_doc())), [])
        doc = spend_doc()
        del doc["loop_jobs"]
        self.assertEqual(list(v.iter_errors(doc)), [])

    def test_schema_refuses_a_bad_block(self):
        v = self.validator()
        for bad in ({"as_of": "yesterday", "points_per_week": 1, "usd_per_week": 1},
                    {"as_of": iso(NOW), "points_per_week": -1, "usd_per_week": 1},
                    {"as_of": iso(NOW), "points_per_week": 1},
                    {"as_of": iso(NOW), "points_per_week": 1, "usd_per_week": 1, "task": "x"}):
            self.assertTrue(list(v.iter_errors(spend_doc(loop_jobs=bad))), bad)

    def test_ingest_accepts_the_block_and_refuses_another_key_in_it(self):
        doc = spend_doc()
        ingest.check_spend(doc, json.dumps(doc), "ok")
        doc["loop_jobs"]["extra"] = 1
        with self.assertRaises(ingest.Rejected):
            ingest.check_spend(doc, json.dumps(doc), "bad")

    def test_the_public_export_never_copies_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = spend_doc(weeks=[{"week": "2026-11-09", "eval_runs": 1}])
            write_json(Path(tmp) / "spend" / "weekly.json", doc)
            got = explorer_public.build_spend(Path(tmp), True)
        self.assertIsNotNone(got)
        self.assertNotIn("loop_jobs", json.dumps(got))


@pytest.mark.real_loop_reserve
class GuardReserveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree = Path(self._tmp.name)

    def state(self):
        return guard.account(self.tree, LIMITS, NOW, (0, 0), since=NOW - guard.WINDOW)

    def put(self, doc):
        write_json(self.tree / "spend" / "weekly.json", doc)

    def test_the_cap_is_the_configured_cap_less_the_reserve(self):
        self.put(spend_doc(points=2.1))
        st = self.state()
        self.assertAlmostEqual(st["cap"], 0.25 - 0.021)
        self.assertEqual(st["cap_configured"], 0.25)
        self.assertAlmostEqual(st["loop_reserve"], 0.021)
        self.assertIn("25.0 configured less 2.1 reserved", guard.describe(st))
        self.assertIn("cap 22.9", guard.describe(st))

    def test_a_reserve_above_the_cap_floors_it_at_zero(self):
        self.put(spend_doc(points=40))
        self.assertEqual(self.state()["cap"], 0.0)

    def test_the_improve_share_follows_the_reduced_cap(self):
        self.put(spend_doc(points=5))
        st = self.state()
        st["improve_charge"] = 0.01
        allowed, _, _ = guard.improve_numbers(st, "improve")
        self.assertEqual(allowed, 4)  # floor(0.20 * 0.20 / 0.01), not 5 of the full cap

    def assertRefused(self, *words):
        with self.assertRaises(guard.GuardError) as caught:
            self.state()
        text = str(caught.exception)
        for word in ("spend/weekly.json", "dashboard/README.md", *words):
            self.assertIn(word, text)

    def test_a_missing_file_refuses_and_says_how_to_fix_it(self):
        self.assertRefused("missing")

    def test_a_file_without_the_block_refuses(self):
        doc = spend_doc()
        del doc["loop_jobs"]
        self.put(doc)
        self.assertRefused("no loop_jobs")

    def test_a_stale_block_refuses(self):
        self.put(spend_doc(as_of=NOW - timedelta(days=3, seconds=1)))
        self.assertRefused("stale")
        self.put(spend_doc(as_of=NOW - timedelta(days=3)))
        self.assertAlmostEqual(self.state()["loop_reserve"], 0.021)

    def test_an_unreadable_or_malformed_block_refuses(self):
        (self.tree / "spend").mkdir()
        (self.tree / "spend" / "weekly.json").write_text("{", encoding="utf-8")
        self.assertRefused("not readable")
        for points in (-1, "2", None, True):
            self.put(spend_doc(points=points))
            self.assertRefused("points_per_week")


if __name__ == "__main__":
    unittest.main()
