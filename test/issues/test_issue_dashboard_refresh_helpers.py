"""dashboard/refresh/: the refresh helpers read and write only under DASHBOARD_HOME.

The helpers moved here from the owner's private project folder so the procedure
is version-controlled; the owner's data stays private. Invented data only.
Deterministic: no network, no wall-clock assertions.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REFRESH = REPO / "dashboard" / "refresh"
PY_HELPERS = ["append_owner_messages.py", "append_session_costs.py", "append_routine_fires.py", "collect_runs.py"]
SH_HELPERS = ["refresh.sh", "half_built.sh", "loop_prs.sh", "mark_published.sh"]


def _env(home):
    env = {k: v for k, v in os.environ.items() if k != "DASHBOARD_HOME"}
    if home is not None:
        env["DASHBOARD_HOME"] = str(home)
    return env


def run_py(name, arg, home=None):
    """One helper script from dashboard/refresh/, never the test runner: bash
    execs python3 on that one file, so no argv here can name the suite."""
    return subprocess.run(["bash", "-c", 'exec python3 -I "$0" "$1"', str(REFRESH / name), arg],
                          env=_env(home), capture_output=True, text=True, timeout=60)


def run_sh(name, home=None):
    return subprocess.run(["bash", str(REFRESH / name), "{}", "{}"], env=_env(home),
                          capture_output=True, text=True, timeout=60)


class RefreshHelpers(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        for d in ("config", "inputs", "ds", "watch"):
            (self.home / d).mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_every_helper_stops_without_dashboard_home(self):
        for name in PY_HELPERS:
            r = run_py(name, "[]")
            self.assertNotEqual(r.returncode, 0, name)
            self.assertIn("DASHBOARD_HOME", r.stderr + r.stdout, name)
        for name in SH_HELPERS:
            r = run_sh(name)
            self.assertNotEqual(r.returncode, 0, name)
            self.assertIn("DASHBOARD_HOME", r.stderr + r.stdout, name)

    def test_no_helper_names_a_private_path(self):
        for f in sorted(p for p in REFRESH.iterdir() if p.is_file()):
            text = f.read_text()
            for bad in ("/mnt/", "/home/user", "project-files"):
                self.assertNotIn(bad, text, f.name)

    def test_routine_fire_ledger_appends_once_per_session(self):
        items = [
            {"trigger_id": "trig_a", "name": "Worker", "fired_at": "2026-01-05T10:00:00Z",
             "finished_at": "2026-01-05T10:03:00Z", "status": "ROUTINE_RUN_STATUS_SUCCEEDED",
             "session_id": "session_one", "total_cost_usd": 1.2345678901234},
            {"trigger_id": "trig_b", "session_id": "cse_two", "finished_at": None},
            {"trigger_id": "trig_c", "finished_at": "2026-01-05T11:00:00Z"},
        ]
        for _ in range(2):
            r = run_py("append_routine_fires.py", json.dumps(items), self.home)
            self.assertEqual(r.returncode, 0, r.stderr)
        rows = [json.loads(l) for l in (self.home / "watch" / "routine-fires.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["session_id"], "cse_one")
        self.assertEqual(rows[0]["total_cost_usd"], 1.2345678901234)
        self.assertIn("already present 1", r.stdout)
        self.assertIn("skipped (no session id or unfinished) 2", r.stdout)

    def test_session_cost_ledger_writes_under_dashboard_home(self):
        item = [{"thread_id": "thread-0001", "session_id": "session_abc", "cost_usd": 2.5}]
        r = run_py("append_session_costs.py", json.dumps(item), self.home)
        self.assertEqual(r.returncode, 0, r.stderr)
        row = json.loads((self.home / "inputs" / "session_costs.jsonl").read_text())
        self.assertEqual((row["session_id"], row["cost_usd"], row["source"]), ("cse_abc", 2.5, "refresh"))

    def test_collect_runs_needs_its_repo_list_in_site_json(self):
        (self.home / "config" / "site.json").write_text("{}")
        r = run_py("collect_runs.py", "[]", self.home)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("run_console_repos", r.stderr)

    def test_the_task_prompt_points_at_the_readme_not_at_steps(self):
        text = (REPO / "dashboard" / "tasks" / "refresh.md").read_text()
        self.assertIn('`dashboard/README.md` "Refresh"', text)
        self.assertIn("DASHBOARD_HOME", text)
        readme = (REPO / "dashboard" / "README.md").read_text()
        for name in PY_HELPERS + SH_HELPERS:
            self.assertIn(name, readme, f"README's Refresh steps never run {name}")


if __name__ == "__main__":
    unittest.main()
