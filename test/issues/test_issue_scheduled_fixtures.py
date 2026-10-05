#!/usr/bin/env python3
"""ADR 0007: reviewed schedules, isolated legs, and per-fixture badges.

Parse workflow structure with PyYAML and execute selection scripts offline.
The caller must use the PID namespace and sentinel required by AGENTS.md.
"""
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/eval.yml"
EXPECTED = ["evals/workflow-path-audit", "evals/embeddable-tool-pages",
            "evals/review-bash-ci-reliability",
            "evals/skills-doctor/bucketed-account-store"]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


planner = module("scheduled_plan", ROOT / "scripts/plan_scheduled_evals.py")
badge = module("scheduled_badge", ROOT / "scripts/make_badge.py")


def doc():
    return yaml.safe_load(WORKFLOW.read_text())


def step(job, name):
    return next(s for s in doc()["jobs"][job]["steps"] if s["name"] == name)


class TestScheduledFixtures(unittest.TestCase):
    def test_schedule_plan_matches_exact_reviewed_list(self):
        committed = planner.committed_fixtures(ROOT)
        paths = planner.scheduled_fixtures(ROOT / "evals/scheduled.yml", committed)
        self.assertEqual(paths, EXPECTED)
        actual = planner.plan(ROOT, "schedule", {"inputs": {"fixture": "evals/nope"}})
        self.assertEqual(actual, {"include": [
            {"fixture": p, "eval_key": p[len("evals/"):], "slot": i}
            for i, p in enumerate(EXPECTED)]})
        plan_step = step("plan", "Plan reviewed fixtures")
        self.assertEqual(plan_step["run"], "python3 scripts/plan_scheduled_evals.py")
        self.assertEqual(doc()["jobs"]["plan"]["outputs"],
                         {"matrix": "${{ steps.plan.outputs.matrix }}"})

    def test_dispatch_defaults_and_explicit_fixture_are_unchanged(self):
        trigger = doc().get("on", doc().get(True))
        self.assertEqual(trigger["schedule"], [{"cron": "0 7 * * 2"}])
        self.assertEqual(trigger["workflow_dispatch"]["inputs"]["fixture"]["default"], EXPECTED[0])
        events = [{}, {"inputs": {}}, {"inputs": {"fixture": ""}},
                  {"inputs": {"fixture": None}}]
        for event in events:
            self.assertEqual(planner.plan(ROOT, "workflow_dispatch", event),
                             {"include": [{"fixture": EXPECTED[0],
                                           "eval_key": "workflow-path-audit", "slot": 0}]})
        for path in EXPECTED:
            self.assertEqual(planner.plan(ROOT, "workflow_dispatch", {"inputs": {"fixture": path}})["include"],
                             [{"fixture": path, "eval_key": path[6:], "slot": 0}])

    def test_dispatch_rejects_invalid_types_nul_and_paths(self):
        for value in [False, True, 0, 123, [], {}, "\0" + EXPECTED[0],
                      EXPECTED[0] + "\n", "evals/../evals/workflow-path-audit", "evals/nope"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                planner.plan(ROOT, "workflow_dispatch", {"inputs": {"fixture": value}})
        for inputs in [False, 0, [], "fixture"]:
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                planner.plan(ROOT, "workflow_dispatch", {"inputs": inputs})
        with self.assertRaises(ValueError):
            planner.plan(ROOT, "pull_request", {})

    def test_schema_rejects_unreviewed_shapes_duplicate_keys_and_notes(self):
        good = {"path": EXPECTED[0], "readiness": "Local smoke: with 8 vs without 7."}
        bad = [None, [], {}, {"fixtures": []}, {"fixtures": [good], "extra": 1},
               {"fixtures": {}}, {"fixtures": [None]}, {"fixtures": [{"path": EXPECTED[0]}]},
               {"fixtures": [dict(good, extra=1)]}, {"fixtures": [good, good]},
               {"fixtures": [good] * 257}]
        bad += [{"fixtures": [dict(good, readiness=n)]}
                for n in [None, 3, "", "  ", "line\nline", "line\rline", "\0", "\u2028"]]
        bad += [{"fixtures": [dict(good, path=p)]}
                for p in [None, "evals/nope", EXPECTED[0] + "\n"]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schedule.yml"
            for document in bad:
                path.write_text(yaml.safe_dump(document))
                with self.subTest(document=document), self.assertRaises(ValueError):
                    planner.scheduled_fixtures(path, EXPECTED)
            for text in ["fixtures: []\nfixtures: []\n", "fixtures:\n  - path: evals/workflow-path-audit\n    path: evals/workflow-path-audit\n    readiness: smoke\n", "fixtures: [unclosed-private-marker"]:
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    planner.scheduled_fixtures(path, EXPECTED)
            path.write_text(yaml.safe_dump({"fixtures": [good]}))
            self.assertEqual(planner.scheduled_fixtures(path, EXPECTED), [EXPECTED[0]])

    def test_schema_entrypoint_sanitizes_malformed_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            subprocess.run(["git", "init", "-q", str(base)], check=True)
            (base / "evals").mkdir()
            (base / "evals/scheduled.yml").write_text("fixtures: [private-source-marker")
            (base / "scripts").mkdir()
            shutil.copyfile(ROOT / "scripts/plan_scheduled_evals.py",
                            base / "scripts/plan_scheduled_evals.py")
            result = subprocess.run(["python3", "scripts/plan_scheduled_evals.py"],
                                    cwd=base, env=dict(os.environ, GITHUB_EVENT_NAME="schedule", GITHUB_EVENT_PATH="", GITHUB_OUTPUT=str(base / "out")),
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "::error::Invalid eval plan or committed fixture selection\n")
            self.assertNotIn("private-source-marker", result.stdout + result.stderr)

    def test_committed_set_refuses_untracked_fixture_directories(self):
        tracked = planner.committed_fixtures(ROOT)
        self.assertTrue(set(EXPECTED) <= set(tracked))
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            subprocess.run(["git", "init", "-q", str(base)], check=True)
            tracked_path = base / "evals/tracked/fixture.yaml"
            tracked_path.parent.mkdir(parents=True)
            tracked_path.write_text("skill: tracked\n")
            subprocess.run(["git", "-C", str(base), "add", "evals/tracked/fixture.yaml"], check=True)
            untracked = base / "evals/untracked/fixture.yaml"
            untracked.parent.mkdir(parents=True)
            untracked.write_text("skill: untracked\n")
            self.assertEqual(planner.committed_fixtures(base), ["evals/tracked"])
            with self.assertRaises(ValueError):
                planner.validate_fixture("evals/untracked", planner.committed_fixtures(base))
            with self.assertRaises(ValueError):
                planner.validate_fixture("evals", ["evals"])

    def test_each_matrix_leg_selects_before_its_own_exchange(self):
        jobs = doc()["jobs"]
        for name, parallel in [("eval", 2), ("publish", 1)]:
            self.assertEqual(jobs[name]["strategy"], {"fail-fast": False, "max-parallel": parallel,
                             "matrix": "${{ fromJSON(needs.plan.outputs.matrix) }}"})
        steps = jobs["eval"]["steps"]
        select = next(i for i, s in enumerate(steps) if s.get("id") == "select-fixture")
        exchange = next(i for i, s in enumerate(steps) if s["name"].startswith("Mint OIDC"))
        self.assertLess(select, exchange)
        self.assertEqual(sum(s["name"].startswith("Mint OIDC") for s in steps), 1)
        selection = steps[select]
        self.assertEqual(selection["env"]["SCHEDULE_FIXTURE"], "${{ github.event_name == 'schedule' && matrix.fixture || '' }}")
        for path in EXPECTED:
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                event = base / "event.json"
                event.write_text(json.dumps({"inputs": {"fixture": "evals/nope"}}))
                env = dict(os.environ, SCHEDULE_FIXTURE=path, MATRIX_KEY=path[6:], MATRIX_SLOT="0", GITHUB_EVENT_PATH=str(event), GITHUB_OUTPUT=str(base / "out"), RUNNER_TEMP=tmp)
                result = subprocess.run(["bash", "-c", selection["run"]], cwd=ROOT, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((base / "eval-fixture").read_text(), path)
                env["MATRIX_KEY"] = "wrong-fixture"
                result = subprocess.run(["bash", "-c", selection["run"]], cwd=ROOT, env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)

    def test_permissions_credentials_and_roster_jobs_do_not_widen(self):
        workflow = doc()
        self.assertEqual(workflow["permissions"], {})
        expected = {"plan": {"contents": "read"},
                    "eval": {"contents": "read", "id-token": "write"},
                    "publish": {"contents": "write"},
                    "roster": {"contents": "read", "id-token": "write", "issues": "write"},
                    "disarm": {"contents": "read", "pull-requests": "write"},
                    "roster-pr": {"contents": "read", "pull-requests": "write", "issues": "write"},
                    "roster-wait": {"contents": "read", "pull-requests": "write"}}
        self.assertEqual({name: job["permissions"] for name, job in workflow["jobs"].items()}, expected)
        secrets = []
        for name, job in workflow["jobs"].items():
            self.assertNotIn("env", job)
            if name in ("roster", "disarm", "roster-pr", "roster-wait"):
                self.assertNotIn("strategy", job)
            for s in job["steps"]:
                self.assertNotIn("${{", s.get("run", ""))
                secrets += [(name, key, value) for key, value in {**s.get("env", {}), **s.get("with", {})}.items() if "secrets." in str(value)]
                if "uses" in s:
                    ref = s["uses"].rsplit("@", 1)[-1]
                    self.assertEqual(len(ref), 40)
                    self.assertTrue(all(char in "0123456789abcdef" for char in ref))
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0][0], "roster-pr")

    def test_artifacts_are_isolated_success_only_with_separate_diagnostics(self):
        payload = step("eval", "Upload eval results")
        download = step("publish", "Download eval results")
        diagnostic = step("eval", "Upload eval diagnostics")
        expected = "eval-results-payload-${{ matrix.slot }}-${{ github.run_attempt }}"
        self.assertEqual(payload["with"]["name"], expected)
        self.assertEqual(download["with"]["name"], expected)
        self.assertEqual(payload["if"], "${{ success() }}")
        self.assertEqual(payload["with"]["if-no-files-found"], "error")
        self.assertEqual(diagnostic["if"], "${{ failure() && !cancelled() }}")
        self.assertEqual(diagnostic["with"]["name"], "eval-results-diagnostics-${{ matrix.slot }}-${{ github.run_attempt }}")
        keys = [entry["eval_key"] for entry in planner.plan(ROOT, "schedule", {})["include"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertNotIn("outputs", doc()["jobs"]["eval"])

    def test_publisher_revalidates_fixture_key_before_matching_download(self):
        steps = doc()["jobs"]["publish"]["steps"]
        validation = step("publish", "Validate the publishing fixture and key")
        self.assertLess(steps.index(validation), steps.index(step("publish", "Download eval results")))
        self.assertEqual(validation["env"], {"FIXTURE": "${{ matrix.fixture }}", "EVAL_KEY": "${{ matrix.eval_key }}", "SLOT": "${{ matrix.slot }}"})
        for path in EXPECTED:
            with tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "output"
                env = dict(os.environ, FIXTURE=path, EVAL_KEY=path[6:], SLOT="0", GITHUB_OUTPUT=str(output))
                result = subprocess.run(["bash", "-c", validation["run"]], cwd=ROOT, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(output.read_text(), "eval_key=" + path[6:] + "\n")
                for key, slot in [("wrong", "0"), (path[6:], "256"), (path[6:], "-1"), (path[6:], "x")]:
                    env.update(EVAL_KEY=key, SLOT=slot)
                    result = subprocess.run(["bash", "-c", validation["run"]], cwd=ROOT, env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)

    def test_successful_siblings_publish_and_missing_payload_is_reported(self):
        gate = doc()["jobs"]["publish"]["if"]
        self.assertIn("needs.eval.result == 'success' || needs.eval.result == 'failure'", gate)
        self.assertIn("!cancelled()", gate)
        self.assertIn("needs.plan.result == 'success'", gate)
        self.assertIn("needs.roster-wait.outputs.cleared == 'true'", gate)
        download = step("publish", "Download eval results")
        self.assertTrue(download["continue-on-error"])
        report = step("publish", "Report a missing success payload")
        self.assertEqual(report["if"], "${{ steps.download.outcome == 'failure' }}")
        commit = step("publish", "Build the badge over the run window, commit, and push")
        self.assertEqual(commit["if"], "${{ steps.download.outcome == 'success' }}")
        for aggregate, rc in [("failure", 0), ("success", 1)]:
            with tempfile.TemporaryDirectory() as tmp:
                summary = Path(tmp) / "summary"
                result = subprocess.run(["bash", "-c", report["run"]], env=dict(os.environ, EVAL_RESULT=aggregate, GITHUB_STEP_SUMMARY=str(summary)), capture_output=True, text=True)
                self.assertEqual(result.returncode, rc)
                self.assertIn("publishing is skipped", summary.read_text())

    def test_fixture_badge_uses_accumulated_history_and_validated_key(self):
        commit = step("publish", "Build the badge over the run window, commit, and push")
        self.assertEqual(commit["env"]["EVAL_KEY"], "${{ steps.fixture.outputs.eval_key }}")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            workspace = base / "workspace"
            scripts = workspace / "scripts"
            scripts.mkdir(parents=True)
            shutil.copyfile(ROOT / "scripts/make_badge.py", scripts / "make_badge.py")
            history = base / "history"
            history.mkdir()
            runner = base / "runner"
            runner.mkdir()
            key = "skills-doctor/bucketed-account-store"
            for tree, stamp, scores in [(history, "20260927T070000Z", (3, 3)),
                                        (workspace / "results", "20261004T070000Z", (5, 3))]:
                for arm, passed in zip(("with_skill", "without_skill"), scores):
                    directory = tree / "skills-doctor" / stamp / "bucketed-account-store" / arm
                    directory.mkdir(parents=True)
                    (directory / "summary.json").write_text(json.dumps({
                        "objective_checks": [{"passed": i < passed} for i in range(5)]}))
            fake_bin = base / "bin"
            fake_bin.mkdir()
            claude_calls = base / "claude-calls"
            refusal = fake_bin / "claude"
            refusal.write_text('#!/bin/sh\nprintf "called\\n" >> "$CLAUDE_CALLS"\nexit 97\n')
            refusal.chmod(0o755)
            git = fake_bin / "git"
            git.write_text("""#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import sys
args = sys.argv[1:]
with open(os.environ["GIT_CALLS"], "a") as output:
    output.write(json.dumps(args) + "\\n")
if args[:2] == ["checkout", "-B"]:
    shutil.copytree(os.environ["HISTORY_TREE"], "results", dirs_exist_ok=True)
if args == ["diff", "--cached", "--quiet"]:
    raise SystemExit(1)
""")
            git.chmod(0o755)
            calls_path = base / "git-calls"
            env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ["PATH"],
                       HISTORY_TREE=str(history), GIT_CALLS=str(calls_path),
                       CLAUDE_CALLS=str(claude_calls),
                       EVAL_KEY=key, GITHUB_TOKEN="offline-fixture", ROSTER_LATEST_JSON="",
                       RUNNER_TEMP=str(runner), GITHUB_STEP_SUMMARY=str(base / "summary"))
            result = subprocess.run(["bash", "-c", commit["run"]], cwd=workspace,
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            actual = json.loads((workspace / "badges" / (key + ".json")).read_text())
            self.assertEqual(actual["message"], "with 4/5 vs without 3/5 · n=2 · 2026-10-04")
            self.assertEqual(actual["color"], "green")
            calls = [json.loads(line) for line in calls_path.read_text().splitlines()]
            self.assertIn(["commit", "-m", "eval: " + key + " run + badge + roster [skip ci]"], calls)
            pushes = [args for args in calls if "push" in args]
            self.assertEqual(len(pushes), 1)
            self.assertEqual(pushes[0][-3:], ["push", "origin", "persistent/eval-results"])
            self.assertFalse((workspace / ".git").exists())
            self.assertFalse(claude_calls.exists() and claude_calls.read_text())

    def test_timeout_covers_every_scheduled_fixture_with_default_budgets(self):
        budget = doc()["jobs"]["eval"]["timeout-minutes"] * 60
        fixtures = planner.scheduled_fixtures(ROOT / "evals/scheduled.yml", planner.committed_fixtures(ROOT))
        self.assertEqual(len(fixtures), 4)
        for path in fixtures:
            fixture = yaml.safe_load((ROOT / path / "fixture.yaml").read_text())
            arms = fixture.get("arms") or {"with_skill": {}, "without_skill": {}}
            per_arm = fixture.get("setup_timeout_s", 60) + fixture.get("timeout_s", 600) + (fixture.get("judge") or {}).get("timeout_s", 120)
            # WIF preflight can retry once, with two 120 s attempts. Leave
            # room for checkout, dependency install, and summary overhead.
            self.assertLess(len(arms) * per_arm + 2 * 120, budget * .75, path)

    def test_nested_fixture_badge_reads_only_its_own_runs_and_preserves_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = Path(tmp)
            key = "skills-doctor/bucketed-account-store"
            for stamp, fixture, scores in [("20261004T070000Z", "bucketed-account-store", (5, 3)),
                                            ("20260927T070000Z", "bucketed-account-store", (3, 3)),
                                            ("20261005T070000Z", "other-fixture", (0, 5))]:
                for arm, passed in zip(("with_skill", "without_skill"), scores):
                    directory = results / "skills-doctor" / stamp / fixture / arm
                    directory.mkdir(parents=True)
                    (directory / "summary.json").write_text(json.dumps({"objective_checks": [{"passed": i < passed} for i in range(5)]}))
            result = badge.build_badge(results, key, window=2)
            self.assertEqual(result["color"], "green")
            self.assertEqual(result["message"], "with 4/5 vs without 3/5 · n=2 · 2026-10-04")
            self.assertEqual(result["label"], "skill eval: " + key)
            latest = badge.build_badge(results, key, window=1)
            self.assertEqual(latest["message"], "with 5/5 vs without 3/5 · 2026-10-04")
            flat = results / "workflow-path-audit/20261004T070000Z"
            for arm, passed in [("with_skill", True), ("without_skill", False)]:
                (flat / arm).mkdir(parents=True)
                (flat / arm / "summary.json").write_text(json.dumps({"objective_checks": [{"passed": passed}]}))
            self.assertEqual(badge.build_badge(results, "workflow-path-audit")["color"], "green")
            summary = results / "skills-doctor/20261004T070000Z/bucketed-account-store/with_skill/summary.json"
            summary.write_text(json.dumps({"local_exhibit": True}))
            with self.assertRaises(SystemExit):
                badge.build_badge(results, key)


if __name__ == "__main__":
    unittest.main()
