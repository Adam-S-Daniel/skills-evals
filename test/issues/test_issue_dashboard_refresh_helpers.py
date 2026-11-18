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


def run_py(name, arg, home=None, extra_env=None):
    """One helper script from dashboard/refresh/, never the test runner: bash
    execs python3 on that one file, so no argv here can name the suite."""
    return subprocess.run(["bash", "-c", 'exec python3 -I "$0" "$1"', str(REFRESH / name), arg],
                          env={**_env(home), **(extra_env or {})},
                          capture_output=True, text=True, timeout=60)


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
        # The fire ledger is not under DASHBOARD_HOME; its own variable is
        # checked in test_routine_fire_ledger_appends_once_per_session.
        for name in [n for n in PY_HELPERS if n != "append_routine_fires.py"]:
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

    def test_missed_run_threshold_follows_build_py_interval(self):
        """The MISSED line fires one hour past build.py's REFRESH_INTERVAL_HOURS,
        not a number of its own: the refresh went from every 12 hours to every
        24 on 2026-11-15, and a hard-coded 13 would flag every run as missed."""
        import re
        every = int(re.search(r"^REFRESH_INTERVAL_HOURS = (\d+)$",
                              (REPO / "dashboard" / "build.py").read_text(), re.M).group(1))
        (self.home / "inputs" / "threads.json").write_text(json.dumps(
            [{"thread_id": "t1", "last_activity_at": "2020-01-01T00:00:00Z"}]))
        (self.home / "inputs" / "owner_messages_read.json").write_text(json.dumps(
            {"read_through": "2020-01-01T00:00:00Z"}))
        (self.home / "watch" / "log.md").write_text(
            "- 2020-01-01T00:00Z 2020-01-01T00:05Z refresh (example): 1 thread\n")
        r = run_sh("refresh.sh", self.home)
        self.assertIn(f"MISSED: the last refresh logged was 2020-01-01T00:00Z, over {every + 1} hours ago", r.stdout)

    def test_refresh_stops_before_the_build_without_the_fire_ledger_or_workflows(self):
        """Scheduled-task cost needs the fire ledger and the fleet worker's firing workflow; without
        either, every figure would read as no value, so refresh.sh stops before build.py, and passes
        --workflows-root to it. The guard runs as its own script here: the steps before it call gh."""
        text = (REFRESH / "refresh.sh").read_text()
        guard = text[text.index("# Scheduled-task cost"):text.index("S=${REFRESH_WORK")]
        self.assertLess(text.index("# Scheduled-task cost"), text.index("dashboard/build.py --results"))
        self.assertIn('--workflows-root "$WORKFLOWS_ROOT"', text)
        ledger = self.home / "fires.jsonl"
        roots = self.home / "roots"
        wf = roots / "_agent-guidance" / ".github" / "workflows"
        wf.mkdir(parents=True)
        def run(env):
            return subprocess.run(["bash", "-c", "set -e\n" + guard + "echo GUARD-PASSED"], env={**_env(self.home), **env},
                                  capture_output=True, text=True, timeout=60)
        r = run({})
        self.assertIn("STOP: ROUTINE_FIRES_LEDGER is unset", r.stdout)
        ledger.write_text("")
        r = run({"ROUTINE_FIRES_LEDGER": str(ledger), "WORKFLOWS_ROOT": str(roots)})
        self.assertIn("STOP: WORKFLOWS_ROOT", r.stdout)
        (wf / "fleet-worker-fire.yml").write_text("on: {}\n")
        r = run({"ROUTINE_FIRES_LEDGER": str(ledger), "WORKFLOWS_ROOT": str(roots)})
        self.assertIn("GUARD-PASSED", r.stdout, r.stdout + r.stderr)

    def test_routine_fire_ledger_appends_once_per_session(self):
        items = [
            {"trigger_id": "trig_a", "name": "Worker", "fired_at": "2026-01-05T10:00:00Z",
             "finished_at": "2026-01-05T10:03:00Z", "status": "ROUTINE_RUN_STATUS_SUCCEEDED",
             "session_id": "session_one", "total_cost_usd": 1.2345678901234},
            {"trigger_id": "trig_b", "session_id": "cse_two", "finished_at": None},
            {"trigger_id": "trig_c", "finished_at": "2026-01-05T11:00:00Z"},
        ]
        ledger = self.home / "spend" / "routine-fires.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            r = run_py("append_routine_fires.py", json.dumps(items), self.home,
                       extra_env={"ROUTINE_FIRES_LEDGER": str(ledger)})
            self.assertEqual(r.returncode, 0, r.stderr)
        rows = [json.loads(l) for l in ledger.read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["session_id"], "cse_one")
        self.assertEqual(rows[0]["total_cost_usd"], 1.2345678901234)
        self.assertIn("already present 1", r.stdout)
        self.assertIn("skipped (no session id or unfinished) 2", r.stdout)
        # Without the ledger path it stops and names it, rather than guess one.
        r = run_py("append_routine_fires.py", json.dumps(items), self.home)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ROUTINE_FIRES_LEDGER", r.stderr)

    def test_owner_ledger_saves_and_keeps_the_chat_cursor(self):
        """read_project_chat pages oldest first, so the next run starts from the
        saved cursor instead of paging the whole chat; a run that passes no
        cursor keeps the saved one."""
        (self.home / "inputs" / "owner_messages.jsonl").write_text("")
        mark = self.home / "inputs" / "owner_messages_read.json"
        item = json.dumps([{"message_id": "cmsg_A1", "sent_at": "2026-01-05T10:00:00Z", "thread_id": None}])
        def run(*args):
            return subprocess.run(["bash", "-c", 'exec python3 -I "$0" "$@"',
                                   str(REFRESH / "append_owner_messages.py"), *args],
                                  env=_env(self.home), capture_output=True, text=True, timeout=60)
        r = run("--read-through", "2026-01-05T11:00:00Z", "--chat-cursor", "c-123", item)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(mark.read_text())["chat_cursor"], "c-123")
        r = run("--read-through", "2026-01-06T11:00:00Z", "[]")
        self.assertEqual(r.returncode, 0, r.stderr)
        saved = json.loads(mark.read_text())
        self.assertEqual((saved["chat_cursor"], saved["read_through"]), ("c-123", "2026-01-06T11:00:00Z"))
        self.assertEqual(len((self.home / "inputs" / "owner_messages.jsonl").read_text().splitlines()), 1)
        r = run("--read-through", "2026-01-06T11:00:00Z", "--chat-cursor", " ", "[]")
        self.assertNotEqual(r.returncode, 0)

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
