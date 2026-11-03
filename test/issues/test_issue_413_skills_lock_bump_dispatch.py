"""_agent-guidance#413: skills-lock-bump.yml is dispatched from here when
adam-agentskills' main has changed (scripts/skills_lock_bump_due.sh,
.github/workflows/skills-lock-bump-dispatch.yml)."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "skills_lock_bump_due.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "skills-lock-bump-dispatch.yml"

NOW = int(datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc).timestamp())


def at(hours_ago: float) -> str:
    t = datetime.fromtimestamp(NOW - hours_ago * 3600, tz=timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def run(created: list[str], committed: str, status: str = "completed") -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        runs = Path(tmp) / "runs.json"
        runs.write_text(json.dumps({"workflow_runs": [
            {"created_at": c, "status": status if i == 0 else "completed"}
            for i, c in enumerate(created)]}))
        p = subprocess.run(["bash", str(SCRIPT), str(runs), committed, str(NOW)],
                           capture_output=True, text=True, check=False)
        return p.returncode, p.stdout.strip()


class DueTests(unittest.TestCase):
    def test_a_change_after_both_runs_is_due(self):
        self.assertEqual(run([at(5), at(10)], at(1)), (0, "due"))

    def test_a_change_between_the_runs_is_due_once_more_for_the_sweep(self):
        self.assertEqual(run([at(2), at(10)], at(5)), (0, "due"))

    def test_two_runs_after_the_change_stop_it(self):
        code, out = run([at(2), at(4)], at(5))
        self.assertEqual(code, 0)
        self.assertIn("two runs have started", out)

    def test_a_recent_run_holds_it_back(self):
        code, out = run([at(0.25), at(10)], at(1))
        self.assertIn("less than 30 minutes", out)

    def test_an_active_run_holds_it_back(self):
        code, out = run([at(2), at(10)], at(1), status="in_progress")
        self.assertIn("queued or in progress", out)

    def test_no_runs_at_all_is_due(self):
        self.assertEqual(run([], at(1)), (0, "due"))

    def test_malformed_input_exits_2(self):
        self.assertEqual(run([at(5)], "not-a-time")[0], 2)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.on = self.doc[True] if True in self.doc else self.doc["on"]

    def test_triggers(self):
        self.assertEqual(self.on["workflow_run"]["workflows"], ["Ingest routine eval results"])
        self.assertIn("workflow_dispatch", self.on)
        for t in ("schedule", "push", "pull_request", "pull_request_target"):
            self.assertNotIn(t, self.on)

    def test_permissions_and_no_concurrency(self):
        self.assertEqual(self.doc["permissions"], {})
        self.assertNotIn("concurrency", self.doc)
        job = self.doc["jobs"]["dispatch"]
        self.assertEqual(job["permissions"], {"contents": "read"})
        self.assertNotIn("concurrency", job)

    def test_the_token_is_scoped_to_one_repository_and_contents_only(self):
        steps = self.doc["jobs"]["dispatch"]["steps"]
        mint = [s for s in steps if "create-github-app-token" in s.get("uses", "")]
        self.assertEqual(len(mint), 1)
        w = mint[0]["with"]
        self.assertEqual(w["repositories"], "_agent-guidance")
        self.assertEqual({k for k in w if k.startswith("permission-")}, {"permission-contents"})
        self.assertTrue(mint[0]["continue-on-error"])

    def test_no_expression_reaches_a_run_block(self):
        for step in self.doc["jobs"]["dispatch"]["steps"]:
            self.assertNotIn("${{", step.get("run", ""))


if __name__ == "__main__":
    unittest.main()
