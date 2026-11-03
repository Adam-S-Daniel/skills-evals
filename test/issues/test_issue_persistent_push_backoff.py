#!/usr/bin/env python3
"""The workflows that publish to the busy `persistent/eval-results` branch.

Routine ingests push to that branch every minute or two, so three
back-to-back attempts can all lose the race (regression-publish run
41673151659: "Could not publish regressions/latest.json after 3 attempts").
Each retry loop makes six attempts and sleeps with exponential backoff plus
jitter before every retry, never before the first attempt. Every attempt
still fetches fresh, rebuilds and commits; there is no rebase or force-push.

Hermetic: reads the workflow files only.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
SLEEP = "sleep $(( (1 << attempt) + RANDOM % 5 ))"
LOOPS = {
    "explorer-data.yml": "for attempt in 1 2 3 4 5 6; do",
    "routine-eval-ingest.yml": "for attempt in 1 2 3 4 5 6; do",
    "routine-eval-weekly.yml": "for attempt in 1 2 3 4 5 6; do",
    "skill-coverage.yml": "for attempt in 1 2 3 4 5 6; do",
}


def _scripts(name):
    doc = yaml.safe_load((WORKFLOWS / name).read_text())
    return [step["run"] for job in doc["jobs"].values()
            for step in job.get("steps", []) if "for attempt in" in step.get("run", "")]


class PersistentPushBackoffTests(unittest.TestCase):
    def test_each_loop_has_six_attempts_and_backs_off_between_them(self):
        for name, header in LOOPS.items():
            with self.subTest(workflow=name):
                scripts = _scripts(name)
                self.assertEqual(len(scripts), 1)
                script = scripts[0]
                self.assertIn(header, script)
                self.assertNotIn("1 2 3;", script)
                self.assertIn("6 attempts", script)
                self.assertNotIn("3 attempts", script)
                self.assertEqual(script.count(SLEEP), 1)
                lines = script.splitlines()
                sleep_at = next(i for i, l in enumerate(lines) if SLEEP in l)
                # The sleep is guarded so the first attempt never waits.
                self.assertIn('[ "$attempt" -gt 1 ]', lines[sleep_at - 1])
                # The wait comes before the fresh fetch of the same attempt.
                fetch_at = next(i for i, l in enumerate(lines) if re.search(r"\bgit .*fetch\b", l))
                self.assertLess(sleep_at, fetch_at)

    def test_every_attempt_still_fetches_fresh_and_never_forces(self):
        for name in LOOPS:
            with self.subTest(workflow=name):
                script = _scripts(name)[0]
                self.assertRegex(script, r"\bgit .*fetch\b")
                self.assertNotRegex(script, r"push .*(--force|--rebase| -f )|git rebase|\+HEAD")

    def test_job_timeout_covers_the_worst_case_wait(self):
        # Waits sum to 2+4+8+16+32 plus 5 jitters of up to 4s: under 90s.
        for name in LOOPS:
            with self.subTest(workflow=name):
                doc = yaml.safe_load((WORKFLOWS / name).read_text())
                for job in doc["jobs"].values():
                    if any("for attempt in" in s.get("run", "") for s in job.get("steps", [])):
                        self.assertGreaterEqual(job["timeout-minutes"], 10)


if __name__ == "__main__":
    unittest.main()
