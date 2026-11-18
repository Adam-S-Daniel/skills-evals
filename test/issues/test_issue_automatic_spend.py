"""The automatic spend breakdown (scripts/automatic_spend.py) builds its
inventory from sources: trigger dumps, workflow files and register-tasks.ps1.
Synthetic inputs only: no network, no clock."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import automatic_spend as aus  # noqa: E402

NOW = datetime(2026, 11, 15, 18, tzinfo=timezone.utc)
CONFIG = {
    "categories": [
        {"id": "dash", "label": "Dashboard", "match": ["dashboard"]},
        {"id": "fleet", "label": "Fleet", "match": ["fleet"]},
        {"id": "evals", "label": "Evals", "match": ["eval runner", "eval\\.yml$"]},
    ],
    "fired_by": {"^fleet worker$": {"workflow": "ag/fire.yml", "cadence_hours": 6}},
    "eval_cap_triggers": ["eval runner"],
    "eval_api_workflows": ["se/eval.yml"],
}


class Cron(unittest.TestCase):
    def test_rates(self):
        self.assertAlmostEqual(aus.cron_fires_per_week("CRON_TZ=America/New_York 29 7,19 * * *"), 14)
        self.assertAlmostEqual(aus.cron_fires_per_week("0 9 * * 1"), 1)
        self.assertAlmostEqual(aus.cron_fires_per_week("41 */3 * * *"), 56)
        self.assertAlmostEqual(aus.cron_fires_per_week("20 0 * * 0,1,3-6"), 6)
        # Twice a year.
        self.assertAlmostEqual(aus.cron_fires_per_week("17 14 22 2,8 *"), 2 / 52)

    def test_cadence_keeps_the_rarest_lines_that_fit(self):
        lines = ["20 0 * * 2", "20 0 * * 0,1,3-6", "20 12 * * *", "20 6,18 * * *",
                 "20 3,9,15,21 * * *"]
        self.assertAlmostEqual(aus.cadence_fires_per_week(lines, 6), 28)
        self.assertAlmostEqual(aus.cadence_fires_per_week(lines, 3), 56)
        self.assertAlmostEqual(aus.cadence_fires_per_week(lines, 168), 1)

    def test_rejects_a_malformed_line(self):
        with self.assertRaises(ValueError):
            aus.cron_fires_per_week("* * *")


class Breakdown(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        wf = self.tmp / "wf"
        for repo, name, text in [
            ("ag", "fire.yml", "name: Fire\non:\n  schedule:\n"
             + "".join(f"    - cron: '{c}'\n" for c in
                       ["20 0 * * 2", "20 0 * * 0,1,3-6", "20 12 * * *", "20 6,18 * * *",
                        "20 3,9,15,21 * * *"])
             + "jobs: {}\n# FLEET_WORKER_FIRE_BEARER\n"),
            ("se", "eval.yml", "name: Eval\non: [workflow_dispatch, workflow_run]\n"
             "# api.anthropic.com/v1/oauth/token\n"),
            ("se", "manual.yml", "name: Manual\non: workflow_dispatch\n# ANTHROPIC_API_KEY\n"),
            ("se", "lint.yml", "name: Lint\non: [push, pull_request]\n"),
            ("cms", "media.yml", "name: Media\non:\n  schedule:\n    - cron: '0 1 * * 1'\n"
             "env:\n  K: ${{ secrets.ANTHROPIC_API_KEY }}\n"),
        ]:
            d = wf / repo / ".github" / "workflows"
            d.mkdir(parents=True, exist_ok=True)
            (d / name).write_text(text, encoding="utf-8")
        self.workflows = aus.scan_workflows(wf)
        self.triggers = {
            "trig_dash": {"name": "Dashboard refresh", "cron_expression": "29 7,19 * * *",
                          "enabled": True, "last_run": {"session_id": "cse_1"}},
            "trig_fw": {"name": "Fleet worker", "cron_expression": "", "enabled": True,
                        "last_run": {"session_id": "cse_3"}},
            "trig_eval": {"name": "Eval runner", "cron_expression": "", "enabled": True,
                          "last_run": {"session_id": "cse_5"}},
            "trig_new": {"name": "Article lift", "cron_expression": "", "enabled": True,
                         "last_run": None},
            "trig_off": {"name": "Old dashboard", "cron_expression": "* * * * *",
                         "enabled": False},
        }
        self.fires = [
            {"trigger_id": "trig_dash", "session_id": "cse_1", "total_cost_usd": 4.0,
             "fired_at": "2026-11-15T12:29:00Z"},
            {"trigger_id": "trig_dash", "session_id": "cse_2", "total_cost_usd": 6.0,
             "fired_at": "2026-11-14T12:29:00Z"},
            {"trigger_id": "trig_fw", "session_id": "cse_3", "total_cost_usd": 2.0,
             "fired_at": "2026-11-15T06:50:00Z"},
            {"trigger_id": "trig_eval", "session_id": "cse_5", "total_cost_usd": 0.1,
             "fired_at": "2026-11-12T02:22:00Z"},
        ]

    def run_breakdown(self, boxy=()):
        return aus.breakdown(CONFIG, self.triggers, self.fires, self.workflows, list(boxy),
                             NOW, 14)

    def job(self, doc, name):
        return next(j for j in doc["jobs"] if j["name"] == name)

    def test_manual_only_workflows_are_left_out(self):
        self.assertNotIn("Manual", [w["name"] for w in self.workflows])

    def test_rates_costs_and_lanes(self):
        doc = self.run_breakdown()
        dash = self.job(doc, "Dashboard refresh")
        self.assertEqual((dash["fires_per_week"], dash["usd_per_fire"], dash["usd_per_week"]),
                         (14, 5.0, 70.0))
        fw = self.job(doc, "Fleet worker")
        self.assertAlmostEqual(fw["usd_per_week"], 56.0)  # 28 fires at $2
        self.assertEqual(self.job(doc, "Eval runner")["lane"], "eval_cap")
        self.assertEqual(self.job(doc, "Article lift")["fires_per_week"], 0.0)
        self.assertNotIn("Old dashboard", [j["name"] for j in doc["jobs"]])
        # The firing workflow carries no cost of its own: the task does.
        self.assertEqual(self.job(doc, "Fire")["lane"], "fires_scheduled_task")
        self.assertEqual(self.job(doc, "Eval")["lane"], "eval_cap")
        self.assertEqual(self.job(doc, "Lint")["lane"], "actions_only")
        self.assertEqual(self.job(doc, "Media")["lane"], "api")
        self.assertEqual(doc["unmeasured"], ["Media"])
        self.assertAlmostEqual(doc["meter_usd_per_week"], 126.0)
        by_id = {c["id"]: c for c in doc["categories"]}
        self.assertAlmostEqual(by_id["dash"]["meter_usd_per_week"], 70.0)
        self.assertEqual(by_id["evals"]["meter_usd_per_week"], 0.0)
        self.assertIn("other", by_id)

    def test_boxy_task_that_runs_claude_is_meter_and_unmeasured(self):
        doc = self.run_breakdown([{"name": "Memory Curation", "fires_per_week": 1.0,
                                   "runs_claude": True, "scripts": []},
                                  {"name": "Task Health Publish", "fires_per_week": 7.0,
                                   "runs_claude": False, "scripts": []}])
        self.assertEqual(self.job(doc, "Memory Curation")["lane"], "meter")
        self.assertIn("Memory Curation", doc["unmeasured"])
        self.assertEqual(self.job(doc, "Task Health Publish")["usd_per_week"], 0.0)


class CurrentModel(unittest.TestCase):
    """Costs come only from fires on the task's current model (Adam, 2026-11-15)."""

    ROWS = [
        {"session_id": "a", "fired_at": "2026-11-12T02:00:00Z", "total_cost_usd": 10.0,
         "last_served_model": "claude-fable-5-2"},
        {"session_id": "b", "fired_at": "2026-11-14T02:00:00Z", "total_cost_usd": 2.0,
         "last_served_model": "claude-sonnet-5-5"},
        {"session_id": "c", "fired_at": "2026-11-15T02:00:00Z", "total_cost_usd": 1.0,
         "last_served_model": "claude-sonnet-5-5"},
    ]

    def test_drops_fires_on_an_earlier_model(self):
        trig = {"model": "claude-sonnet-5-5", "updated_at": "2026-11-13T00:00:00Z"}
        self.assertEqual(aus.current_model_costs(self.ROWS, trig),
                         ("claude-sonnet-5-5", [2.0, 1.0], 1, False))

    def test_a_set_model_with_no_fire_since_the_edit_has_no_cost(self):
        trig = {"derived_state": {"model": "claude-haiku-5-5"},
                "updated_at": "2026-11-15T12:00:00Z"}
        self.assertEqual(aus.current_model_costs(self.ROWS, trig),
                         ("claude-haiku-5-5", [], 3, False))

    def test_a_page_model_the_fires_ignore_is_flagged(self):
        trig = {"model": "claude-haiku-5-5", "updated_at": "2026-11-13T00:00:00Z"}
        self.assertEqual(aus.current_model_costs(self.ROWS, trig),
                         ("claude-sonnet-5-5", [2.0, 1.0], 1, True))

    def test_odd_times_neither_crash_nor_decide_the_model(self):
        rows = self.ROWS + [
            {"session_id": "d", "fired_at": None, "total_cost_usd": 9.0,
             "last_served_model": "claude-opus-5-5"},
            {"session_id": "e", "fired_at": "2026-11-15T03:00:00", "total_cost_usd": None,
             "last_served_model": "claude-sonnet-5-5"},
        ]
        trig = {"model": "claude-sonnet-5-5", "updated_at": 1763000000}
        self.assertEqual(aus.current_model_costs(rows, trig),
                         ("claude-sonnet-5-5", [2.0, 1.0], 2, False))

    def test_a_fire_at_the_edit_counts_as_since(self):
        trig = {"model": "claude-haiku-5-5", "updated_at": "2026-11-15T02:00:00Z"}
        self.assertEqual(aus.current_model_costs(self.ROWS, trig)[0], "claude-sonnet-5-5")

    def test_no_set_model_uses_the_newest_fire(self):
        self.assertEqual(aus.current_model_costs(self.ROWS, {"model": ""})[:3],
                         ("claude-sonnet-5-5", [2.0, 1.0], 1))


class LoopMembership(unittest.TestCase):
    CONFIG = {
        "categories": [
            {"id": "fleet", "label": "Fleet", "match": ["fleet", "security"], "in_loop": True},
            {"id": "personal", "label": "Personal", "match": ["brief"], "in_loop": False},
        ],
        "outside_loop": ["security alert triage"],
        "inside_loop": ["special brief"],
        "other_in_loop": False,
    }

    def test_category_default_and_overrides(self):
        m = lambda name, cat: aus.loop_membership(name, cat, self.CONFIG)  # noqa: E731
        self.assertIs(m("Fleet worker", "fleet"), True)
        self.assertIs(m("Daily security alert triage", "fleet"), False)
        self.assertIs(m("Morning brief", "personal"), False)
        self.assertIs(m("A special brief", "personal"), True)
        self.assertIs(m("Site build", "other"), False)
        self.assertIsNone(aus.loop_membership("Site build", "other", {"categories": []}))

    def test_breakdown_splits_meter_spend(self):
        triggers = {
            "t1": {"name": "Fleet worker", "cron_expression": "0 0 * * 1", "enabled": True},
            "t2": {"name": "Daily security alert triage", "cron_expression": "0 0 * * 1",
                   "enabled": True},
        }
        triggers["t1"].update(model="claude-haiku-5-5", updated_at="2026-11-10T00:00:00Z")
        fires = [{"trigger_id": "t1", "session_id": "a", "total_cost_usd": 3.0,
                  "fired_at": "2026-11-12T00:00:00Z", "last_served_model": "claude-opus-5-5"},
                 {"trigger_id": "t1", "session_id": "c", "total_cost_usd": 8.0,
                  "fired_at": "2026-11-01T00:00:00Z", "last_served_model": "claude-fable-5-2"},
                 {"trigger_id": "t2", "session_id": "b", "total_cost_usd": 2.0}]
        doc = aus.breakdown(self.CONFIG, triggers, fires, [], [], NOW, 14)
        self.assertAlmostEqual(doc["loop_meter_usd_per_week"], 3.0)
        self.assertAlmostEqual(doc["outside_loop_meter_usd_per_week"], 2.0)
        self.assertEqual(doc["loop_unassigned"], [])
        fw = next(j for j in doc["jobs"] if j["name"] == "Fleet worker")
        self.assertEqual((fw["model"], fw["cost_fires_other_model"], fw["model_mismatch"]),
                         ("claude-opus-5-5", 1, True))
        fleet = next(c for c in doc["categories"] if c["id"] == "fleet")
        self.assertAlmostEqual(fleet["outside_loop_meter_usd_per_week"], 2.0)


class ShippedConfig(unittest.TestCase):
    def test_every_category_says_whether_it_is_in_the_loop(self):
        import yaml
        cfg = yaml.safe_load((ROOT / "evals" / "automatic-spend.yml").read_text(encoding="utf-8"))
        for c in cfg["categories"]:
            self.assertIsInstance(c.get("in_loop"), bool, c["id"])
        self.assertIsInstance(cfg.get("other_in_loop"), bool)

    def test_the_split_fleet_worker_is_marked_and_rated(self):
        # _agent-guidance ADR 0046: the loop worker is in the loop, daily; the
        # maintenance fleet worker is outside it, every 6 hours.
        import yaml
        cfg = yaml.safe_load((ROOT / "evals" / "automatic-spend.yml").read_text(encoding="utf-8"))
        for name, inside, hours in (("Loop worker", True, 24), ("Fleet worker", False, 6)):
            cat = aus.categorize(name, cfg["categories"])
            self.assertIs(aus.loop_membership(name, cat, cfg), inside, name)
            spec = next(v for k, v in cfg["fired_by"].items() if re.search(k, name, re.I))
            self.assertEqual((spec["workflow"], spec["cadence_hours"]),
                             ("_agent-guidance/fleet-worker-fire.yml", hours), name)


class BoxyTasks(unittest.TestCase):
    def test_register_tasks_parameters_and_claude_scripts(self):
        root = Path(tempfile.mkdtemp())
        (root / "scripts").mkdir()
        (root / "scripts" / "register-tasks.ps1").write_text(
            ".PARAMETER MemoryCurationTime\n    Time of day the weekly (Monday) trigger fires.\n"
            ".PARAMETER TaskHealthTime\n    Time of day the daily trigger fires.\n"
            "param(\n"
            "    [string]$MemoryCurationTaskName = 'Memory Curation',\n"
            "    [string]$MemoryCurationTime = '13:47',\n"
            "    [string]$TaskHealthTaskName = 'Task Health Publish',\n"
            "    [string]$TaskHealthTime = '23:47',\n"
            "    [string]$KeeperTaskName = 'Session Keeper',\n"
            "    [int]$KeeperIntervalMinutes = 5\n)\n", encoding="utf-8")
        (root / "scripts" / "run-memory-curation.sh").write_text(
            'timeout 60 "$claude_bin" -p "$prompt" --model sonnet\n', encoding="utf-8")
        (root / "scripts" / "publish-task-health.sh").write_text("echo ok\n", encoding="utf-8")
        tasks = {t["name"]: t for t in aus.scan_boxy_tasks(root)}
        self.assertEqual((tasks["Memory Curation"]["fires_per_week"],
                          tasks["Memory Curation"]["runs_claude"]), (1.0, True))
        self.assertEqual((tasks["Task Health Publish"]["fires_per_week"],
                          tasks["Task Health Publish"]["runs_claude"]), (7.0, False))
        self.assertEqual(tasks["Session Keeper"]["fires_per_week"], 2016)


class Cli(unittest.TestCase):
    def test_writes_a_document_from_a_dashboard_style_dump(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "t.json").write_text(json.dumps(
            {"trig_dash": {"cron_expression": "0 9 * * 1", "enabled": True}}), encoding="utf-8")
        (tmp / "r.json").write_text(json.dumps(
            [{"name": "Dashboard refresh", "source": {"kind": "trigger", "id": "trig_dash"}}]),
            encoding="utf-8")
        (tmp / "f.jsonl").write_text(json.dumps(
            {"trigger_id": "trig_dash", "session_id": "s", "total_cost_usd": 3.0}) + "\n",
            encoding="utf-8")
        out = tmp / "out.json"
        aus.main(["--triggers", str(tmp / "t.json"), "--routines", str(tmp / "r.json"),
                  "--fires", str(tmp / "f.jsonl"), "--as-of", "2026-11-15T18:00:00Z",
                  "--out-json", str(out)])
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["jobs"][0]["name"], "Dashboard refresh")
        self.assertAlmostEqual(doc["meter_usd_per_week"], 3.0)


if __name__ == "__main__":
    unittest.main()
