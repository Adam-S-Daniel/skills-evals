#!/usr/bin/env python3
"""scripts/local_eval.py — the local-exhibit runner (ADR 0002, decision 4).

Every test drives the production entry point, `python3 scripts/local_eval.py`,
as a subprocess, against a CLAUDE_BIN that is a per-test DISPATCHER written
into the test's own mkdtemp: it logs each invocation and hands it to the
repo's fakes — `test/fake-claude-init` for the stream-json init probe,
`test/fake-claude` for `--version` and the agent arms — and answers the judge
itself with scores that differ per call, so a mean is distinguishable from a
min. No real `claude` is run, no credential is read, and the environment each
run gets is built from nothing (HOME, TMPDIR and every path under the test's
own mkdtemp).

Discovered and run by test/run_tests.py; also runnable on its own with
`python3 test/issues/test_issue_local_eval.py`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCAL_EVAL = REPO_ROOT / "scripts" / "local_eval.py"
FAKE_CLAUDE = REPO_ROOT / "test" / "fake-claude"
FAKE_CLAUDE_INIT = REPO_ROOT / "test" / "fake-claude-init"
EVAL_DIR = REPO_ROOT / "evals" / "workflow-path-audit"
GUIDANCE_FIXTURE = REPO_ROOT / "evals" / "guidance" / "_delivery"
SKILL = "workflow-path-audit"
EXHIBIT = "local — not badge input"

HAVE_GIT = shutil.which("git") is not None

DISPATCHER = '''#!{python}
import json, os, sys
LOG = {log!r}
STATE = {state!r}
FAIL_AGENT_CALL = {fail!r}
argv = sys.argv[1:]
if "--version" in argv:
    role = "version"
elif "stream-json" in argv:
    role = "probe"
elif "--setting-sources" in argv:
    role = "agent"
else:
    role = "judge"
path = os.path.join(STATE, role)
n = int(open(path).read()) + 1 if os.path.exists(path) else 1
with open(path, "w") as f:
    f.write(str(n))
record = {{"role": role, "n": n, "argv": argv, "cwd": os.getcwd()}}
if role == "probe":
    record["cwd_entries"] = sorted(os.listdir("."))
    record["env"] = {{k: os.environ[k] for k in ("ANTHROPIC_BASE_URL", "HOME")
                     if k in os.environ}}
with open(LOG, "a") as f:
    f.write(json.dumps(record) + "\\n")
if role == "agent" and n == FAIL_AGENT_CALL:
    sys.stderr.write("simulated agent failure\\n")
    sys.exit(3)
if role == "judge":
    sys.stdin.read()
    base = (6, 8, 9)[(n - 1) % 3]
    dims = [{{"name": "Completeness", "score": base, "rationale": "r"}},
            {{"name": "Salience", "score": base - 1, "rationale": "r"}},
            {{"name": "Restraint", "score": 10 - base, "rationale": "r"}}]
    print(json.dumps({{"result": json.dumps({{"dimensions": dims, "overall": 0}}),
                      "modelUsage": {{"fake-judge-model": {{}}}}}}))
    sys.exit(0)
target = {fake_init!r} if role == "probe" else {fake!r}
os.execv(sys.executable, [sys.executable, target, *argv])
'''


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.name=t",
         "-c", "user.email=t@example.com", *args],
        capture_output=True, text=True, check=True)


def _plant_skill(skills_dir: Path, name: str) -> None:
    (skills_dir / name).mkdir(parents=True)
    (skills_dir / name / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test stand-in.\n---\n",
        encoding="utf-8")


@unittest.skipUnless(HAVE_GIT, "git is required")
class TestLocalEval(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="local-eval-test-")).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = self.root / "home"
        self.home.mkdir()
        (self.root / "tmp").mkdir()
        self.state = self.root / "state"
        self.state.mkdir()
        self.log = self.root / "calls.jsonl"
        self.out = self.root / "out"

    # -- helpers ---------------------------------------------------------

    def _dispatcher(self, fail_agent_call=None) -> Path:
        path = self.root / "claude-dispatch"
        path.write_text(DISPATCHER.format(
            python=sys.executable, log=str(self.log), state=str(self.state),
            fail=fail_agent_call, fake=str(FAKE_CLAUDE),
            fake_init=str(FAKE_CLAUDE_INIT)), encoding="utf-8")
        path.chmod(0o755)
        return path

    def _registry(self) -> Path:
        registry = self.root / "registry"
        _plant_skill(registry / "plugins" / "a-bundle" / "skills", SKILL)
        _git(registry, "init", "-q")
        _git(registry, "add", "-A")
        _git(registry, "commit", "-q", "-m", "registry")
        return registry

    def _env(self, dispatcher: Path, **extra) -> dict:
        path = [str(Path(sys.executable).parent),
                str(Path(shutil.which("git")).parent), "/usr/bin", "/bin"]
        env = {"PATH": os.pathsep.join(dict.fromkeys(path)),
               "HOME": str(self.home), "TMPDIR": str(self.root / "tmp"),
               "LANG": "C.UTF-8", "CLAUDE_BIN": str(dispatcher)}
        env.update(extra)
        return env

    def _run(self, *args, fail_agent_call=None, env_extra=None,
             results_dir=None):
        env = self._env(self._dispatcher(fail_agent_call), **(env_extra or {}))
        out = self.out if results_dir is None else results_dir
        return subprocess.run(
            [sys.executable, str(LOCAL_EVAL), *args, "--results-dir", str(out)],
            capture_output=True, text=True, env=env, cwd=str(self.root),
            timeout=600)

    def _calls(self) -> list:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in
                self.log.read_text(encoding="utf-8").splitlines()]

    def _json(self, name: str) -> dict:
        return json.loads((self.out / name).read_text(encoding="utf-8"))

    def _summaries(self, arm: str, trials: int) -> list:
        found = []
        for k in range(1, trials + 1):
            paths = sorted((self.out / f"t{k}").glob(f"{SKILL}/*/{arm}/summary.json"))
            self.assertEqual(len(paths), 1, f"t{k}/{arm}: {paths}")
            found.append(json.loads(paths[0].read_text(encoding="utf-8")))
        return found

    def _assert_nothing_ran(self, proc):
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(self._calls(), [],
                         "a refusal must happen before any CLI call")

    # -- 1. preflight: the environment -----------------------------------

    def test_refuses_each_credential_or_endpoint_variable(self):
        registry = self._registry()
        for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                     "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL"):
            for value in ("set", ""):
                with self.subTest(name=name, value=value):
                    proc = self._run(str(EVAL_DIR), "--trials", "1",
                                     "--registry", f"adam-agentskills={registry}",
                                     env_extra={name: value})
                    self._assert_nothing_ran(proc)
                    self.assertIn(name, proc.stderr)
                    self.assertFalse(self.out.exists())

    # -- 1. preflight: where results go ----------------------------------

    def test_refuses_a_results_dir_inside_this_checkout(self):
        name = f"local-eval-refusal-{self.root.name}"
        link = self.root / "link"
        link.symlink_to(REPO_ROOT, target_is_directory=True)
        for out in (REPO_ROOT / name, REPO_ROOT / "results" / name,
                    link / name, self.root / "link" / "evals" / ".." / name):
            with self.subTest(out=str(out)):
                self.assertFalse((REPO_ROOT / name).exists())
                proc = self._run(str(EVAL_DIR), "--trials", "1", results_dir=out)
                self._assert_nothing_ran(proc)
                self.assertIn("inside this checkout", proc.stderr)
                self.assertFalse((REPO_ROOT / name).exists())
                self.assertFalse((REPO_ROOT / "results" / name).exists())

    def test_refuses_a_results_dir_inside_another_git_work_tree(self):
        other = self.root / "other-repo"
        other.mkdir()
        _git(other, "init", "-q")
        proc = self._run(str(EVAL_DIR), "--trials", "1",
                         results_dir=other / "nested" / "out")
        self._assert_nothing_ran(proc)
        self.assertIn("git work tree", proc.stderr)
        self.assertFalse((other / "nested").exists())

    def test_refuses_a_results_dir_that_already_holds_files(self):
        self.out.mkdir()
        (self.out / "earlier.txt").write_text("x\n", encoding="utf-8")
        proc = self._run(str(EVAL_DIR), "--trials", "1",
                         "--registry", f"adam-agentskills={self._registry()}")
        self._assert_nothing_ran(proc)
        self.assertIn("already exists", proc.stderr)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         ["earlier.txt"])

    def test_refuses_a_guidance_fixture_and_out_of_range_trials(self):
        for args, message in (((str(GUIDANCE_FIXTURE), "--trials", "1"),
                               "skill fixtures only"),
                              ((str(EVAL_DIR), "--trials", "0"), "--trials"),
                              ((str(EVAL_DIR), "--trials", "21"), "--trials")):
            with self.subTest(args=args):
                proc = self._run(*args)
                self._assert_nothing_ran(proc)
                self.assertIn(message, proc.stderr)
                self.assertFalse(self.out.exists())

    # -- 3. contamination probe ------------------------------------------

    def _assert_contaminated(self, proc, expected_copy):
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        roles = [c["role"] for c in self._calls()]
        self.assertIn("probe", roles)
        self.assertNotIn("agent", roles, "no arm may run after contamination")
        self.assertNotIn("judge", roles)
        manifest = self._json("manifest.json")
        self.assertEqual(manifest["exhibit"], EXHIBIT)
        probe = manifest["contamination_probe"]
        self.assertTrue(probe["skill_under_test_visible"])
        self.assertIn(expected_copy, probe["visible_skills"])
        self.assertEqual(probe["skill_under_test_copies"], [expected_copy])
        self.assertTrue(manifest["status"].startswith("refused"))
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         ["manifest.json"])

    def test_a_user_level_copy_of_the_skill_fails_the_run(self):
        _plant_skill(self.home / ".claude" / "skills", SKILL)
        proc = self._run(str(EVAL_DIR), "--trials", "1",
                         "--registry", f"adam-agentskills={self._registry()}")
        self._assert_contaminated(proc, SKILL)

    def test_a_plugin_copy_of_the_skill_fails_the_run(self):
        install = self.root / "plugin-install"
        _plant_skill(install / "skills", SKILL)
        plugins = self.home / ".claude" / "plugins"
        plugins.mkdir(parents=True)
        (plugins / "installed_plugins.json").write_text(json.dumps(
            {"version": 2, "plugins": {"some-bundle@market": [
                {"scope": "user", "installPath": str(install),
                 "version": "1.0.0"}]}}), encoding="utf-8")
        proc = self._run(str(EVAL_DIR), "--trials", "1",
                         "--registry", f"adam-agentskills={self._registry()}")
        self._assert_contaminated(proc, f"some-bundle:{SKILL}")

    def test_a_skill_whose_name_only_contains_the_skill_under_test_is_not_contamination(self):
        # The near miss: the match is the whole name (bare or after the last
        # `:`), so a longer name sharing a prefix does not stop the run.
        near_miss = f"{SKILL}-extra"
        _plant_skill(self.home / ".claude" / "skills", near_miss)
        proc = self._run(str(EVAL_DIR), "--trials", "1", "--no-judge",
                         "--registry", f"adam-agentskills={self._registry()}")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        probe = self._json("manifest.json")["contamination_probe"]
        self.assertIn(near_miss, probe["visible_skills"])
        self.assertFalse(probe["skill_under_test_visible"])

    # -- 2, 4, 5, 6: a clean run -----------------------------------------

    def test_a_clean_run_records_identity_runs_n_trials_and_aggregates(self):
        registry = self._registry()
        # A RELATIVE registry path, resolved from the caller's cwd (the test
        # root), while run_eval itself runs from the repository root.
        proc = self._run(str(EVAL_DIR), "--registry", "adam-agentskills=registry")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        calls = self._calls()
        roles = [c["role"] for c in calls]
        self.assertEqual(roles.count("probe"), 1)
        self.assertLess(roles.index("probe"), roles.index("agent"),
                        "the probe must run before any arm")
        self.assertEqual(roles.count("agent"), 6, "3 trials x 2 arms")
        self.assertEqual(roles.count("judge"), 6)
        probe_call = calls[roles.index("probe")]
        argv = probe_call["argv"]
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "project")
        self.assertEqual(probe_call["cwd_entries"], [".git"])
        self.assertEqual(probe_call["env"]["HOME"], str(self.home))
        self.assertTrue(probe_call["env"]["ANTHROPIC_BASE_URL"].startswith(
            "http://127.0.0.1:"))

        manifest = self._json("manifest.json")
        self.assertEqual(manifest["exhibit"], EXHIBIT)
        self.assertEqual(manifest["status"], "completed")
        self.assertRegex(manifest["started_at"],
                         r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        version = subprocess.run([sys.executable, str(FAKE_CLAUDE), "--version"],
                                 capture_output=True, text=True).stdout
        self.assertEqual(manifest["harness"]["claude_version"],
                         version.splitlines()[0].strip())
        fixture = yaml.safe_load((EVAL_DIR / "fixture.yaml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["models"]["fixture_pins"],
                         {"model": fixture["model"],
                          "judge_model": fixture["judge"]["model"]})
        self.assertEqual(manifest["models"]["selected"],
                         {"agent": fixture["model"],
                          "judge": fixture["judge"]["model"]})
        head = _git(registry, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(manifest["registry"],
                         {"name": "adam-agentskills", "source": "--registry flag",
                          "sha": head, "dirty": False})
        own = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                             capture_output=True, text=True)
        self.assertEqual(manifest["skills_evals"]["sha"],
                         own.stdout.strip() if own.returncode == 0 else None)
        probe = manifest["contamination_probe"]
        self.assertFalse(probe["skill_under_test_visible"])
        self.assertEqual(probe["setting_sources"], "project")
        self.assertIsInstance(probe["visible_skills"], list)
        self.assertNotIn(SKILL, probe["visible_skills"])
        self.assertEqual([(t["trial"], t["exit_code"]) for t in manifest["trials"]],
                         [(1, 0), (2, 0), (3, 0)])

        # 6: transcripts stay where run_eval wrote them, and are listed.
        raw = sorted(p.relative_to(self.out).as_posix()
                     for p in self.out.rglob("raw.json"))
        self.assertEqual(len(raw), 6)
        self.assertTrue(all(re.match(r"^t[123]/", p) for p in raw), raw)
        self.assertEqual(manifest["transcripts"]["files"], raw)
        self.assertIs(manifest["transcripts"]["local_only"], True)
        self.assertIn("LOCAL-ONLY", manifest["transcripts"]["note"])
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         ["aggregate.json", "manifest.json", "t1", "t2", "t3"])

        # 5: the aggregate, recomputed here from the trial summaries.
        aggregate = self._json("aggregate.json")
        self.assertEqual(aggregate["exhibit"], EXHIBIT)
        self.assertEqual(sorted(aggregate["arms"]), ["with_skill", "without_skill"])
        for arm in ("with_skill", "without_skill"):
            with self.subTest(arm=arm):
                summaries = self._summaries(arm, 3)
                got = aggregate["arms"][arm]
                self.assertEqual((got["n"], got["errors"], got["scored"]), (3, 0, 3))
                overall = [s["judge"]["overall"] for s in summaries]
                self.assertGreater(len(set(overall)), 1,
                                   "the dispatcher must vary the judge per call")
                self.assertEqual(got["judge"]["overall"],
                                 {"n": 3, "mean": sum(overall) / 3,
                                  "min": min(overall), "max": max(overall)})
                completeness = [d["score"] for s in summaries
                                for d in s["judge"]["dimensions"]
                                if d["name"] == "Completeness"]
                self.assertEqual(got["judge"]["dimensions"]["Completeness"]["mean"],
                                 sum(completeness) / 3)
                totals = [sum(c["passed"] for c in s["objective_checks"])
                          for s in summaries]
                self.assertEqual(got["objective"]["total"],
                                 {"n": 3, "mean": sum(totals) / 3,
                                  "min": min(totals), "max": max(totals)})
                for check_id in {c["id"] for c in summaries[0]["objective_checks"]}:
                    passed = sum(c["passed"] for s in summaries
                                 for c in s["objective_checks"] if c["id"] == check_id)
                    self.assertEqual(got["objective"]["checks"][check_id],
                                     {"passed": passed, "n": 3,
                                      "pass_rate": passed / 3})
                costs = [s["agent"]["cost_usd"] for s in summaries]
                self.assertEqual(got["cost_usd"]["sum"], sum(costs))

    # -- 4: a trial that errors ------------------------------------------

    def test_an_errored_trial_is_recorded_counted_and_fails_the_exit_code(self):
        # Agent call 3 is trial 2's with_skill arm (arms run with_skill first).
        proc = self._run(str(EVAL_DIR), "--trials", "3",
                         "--registry", f"adam-agentskills={self._registry()}",
                         fail_agent_call=3)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        manifest = self._json("manifest.json")
        self.assertEqual([t["exit_code"] for t in manifest["trials"]], [0, 2, 0])
        self.assertIn("t2/run_eval.log", manifest["trials"][1]["error"])
        self.assertTrue((self.out / "t2" / "run_eval.log").is_file())
        self.assertEqual(manifest["status"], "completed with errors")
        arms = self._json("aggregate.json")["arms"]
        self.assertEqual((arms["with_skill"]["n"], arms["with_skill"]["errors"],
                          arms["with_skill"]["scored"]), (3, 1, 2))
        self.assertEqual(arms["with_skill"]["error_trials"],
                         [{"trial": 2, "error": "nonzero_exit"}])
        self.assertEqual(arms["with_skill"]["judge"]["overall"]["n"], 2)
        self.assertEqual((arms["without_skill"]["n"],
                          arms["without_skill"]["errors"]), (3, 0))

    # -- 4: pass-through -------------------------------------------------

    def test_arm_and_no_judge_pass_through(self):
        proc = self._run(str(EVAL_DIR), "--trials", "1", "--arm", "without_skill",
                         "--no-judge")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        roles = [c["role"] for c in self._calls()]
        self.assertEqual(roles.count("agent"), 1)
        self.assertNotIn("judge", roles)
        self.assertEqual(list((self.out / "t1" / SKILL).glob("*/with_skill")), [])
        aggregate = self._json("aggregate.json")
        self.assertEqual(sorted(aggregate["arms"]), ["without_skill"])
        self.assertIsNone(aggregate["arms"]["without_skill"]["judge"])
        manifest = self._json("manifest.json")
        self.assertEqual(manifest["invocation"]["arm"], "without_skill")
        self.assertIs(manifest["invocation"]["no_judge"], True)
        self.assertIsNone(manifest["models"]["selected"]["judge"])


if __name__ == "__main__":
    unittest.main()
