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

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
record = {{"role": role, "n": n, "argv": argv, "cwd": os.getcwd(),
          "env_names": sorted(os.environ),
          "secret_env": sorted(k for k in os.environ
                               if k.startswith("ANTHROPIC_")
                               or k == "CLAUDE_CODE_OAUTH_TOKEN")}}
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


SHIM = '''#!{python}
import json, os, sys
with open({log!r}, "a") as f:
    f.write(json.dumps({{"tool": {tool!r}, "argv": sys.argv[1:]}}) + "\\n")
real = {real!r}
if real:
    os.execv(real, [real, *sys.argv[1:]])
sys.stderr.write("shim: {tool} is not available in this test\\n")
sys.exit(97)
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
        self.root = Path(tempfile.mkdtemp(
            prefix="local-eval-test-", dir=self._temp_base())).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = self.root / "home"
        self.home.mkdir()
        (self.root / "tmp").mkdir()
        self.state = self.root / "state"
        self.state.mkdir()
        self.log = self.root / "calls.jsonl"
        self.out = self.root / "out"

    @staticmethod
    def _temp_base():
        """A temp parent with no `.git` entry in it or above it: the runner
        refuses a results dir under one, and a shared or dotfile-managed temp
        dir can have one (an empty `.git` in /tmp is enough)."""
        for base in (tempfile.gettempdir(), "/dev/shm"):
            path = Path(base).resolve()
            if path.is_dir() and not any((p / ".git").exists()
                                         for p in (path, *path.parents)):
                return str(path)
        raise unittest.SkipTest("no temp directory outside a git repository")

    # -- helpers ---------------------------------------------------------

    def _dispatcher(self, fail_agent_call=None) -> Path:
        path = self.root / "claude-dispatch"
        path.write_text(DISPATCHER.format(
            python=sys.executable, log=str(self.log), state=str(self.state),
            fail=fail_agent_call, fake=str(FAKE_CLAUDE),
            fake_init=str(FAKE_CLAUDE_INIT)), encoding="utf-8")
        path.chmod(0o755)
        return path

    def _registry(self, skill: str = SKILL) -> Path:
        registry = self.root / "registry"
        _plant_skill(registry / "plugins" / "a-bundle" / "skills", skill)
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

    def test_refuses_a_fixture_whose_env_block_names_a_refused_variable(self):
        # run_eval.agent_env applies a fixture's `env:` block LAST, over its
        # allowlist, so this is the one way a refused name could still reach
        # an arm after the caller's own environment passed the check.
        registry = self._registry()
        for name in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
                     "CLAUDE_CODE_USE_BEDROCK", "AWS_BEARER_TOKEN_BEDROCK",
                     "GOOGLE_APPLICATION_CREDENTIALS", "CLAUDE_CONFIG_DIR"):
            with self.subTest(name=name):
                eval_dir = self.root / f"fixture-{name}"
                shutil.copytree(EVAL_DIR, eval_dir)
                fixture_path = eval_dir / "fixture.yaml"
                fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
                fixture["env"] = {name: "example-value", "HARMLESS": "1"}
                fixture_path.write_text(yaml.safe_dump(fixture), encoding="utf-8")
                proc = self._run(str(eval_dir), "--trials", "1",
                                 "--registry", f"adam-agentskills={registry}")
                self._assert_nothing_ran(proc)
                self.assertIn(name, proc.stderr)
                self.assertIn("env:", proc.stderr)
                self.assertNotIn("example-value", proc.stderr)
                self.assertFalse(self.out.exists())

    def test_no_child_process_receives_a_refused_variable(self):
        # The only ANTHROPIC_ name any child may see is the probe's own
        # black-holed endpoint; the version call, every arm and every judge
        # call see none, and nothing ever sees the OAuth token name.
        proc = self._run(str(EVAL_DIR), "--trials", "1",
                         "--registry", f"adam-agentskills={self._registry()}")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self._calls()
        self.assertEqual({c["role"] for c in calls},
                         {"version", "probe", "agent", "judge"})
        for call in calls:
            with self.subTest(role=call["role"], n=call["n"]):
                expected = (["ANTHROPIC_BASE_URL"] if call["role"] == "probe"
                            else [])
                self.assertEqual(call["secret_env"], expected)

    # -- 1. preflight: where results go ----------------------------------

    def test_refuses_a_results_dir_inside_this_checkout(self):
        name = f"local-eval-refusal-{self.root.name}"
        link = self.root / "link"
        link.symlink_to(REPO_ROOT, target_is_directory=True)
        dangling = self.root / "dangling"
        dangling.symlink_to(REPO_ROOT / name)
        for out in (REPO_ROOT / name, REPO_ROOT / "results" / name,
                    link / name, self.root / "link" / "evals" / ".." / name,
                    dangling):
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

    def test_refuses_a_results_dir_inside_a_git_directory(self):
        other = self.root / "other-repo"
        other.mkdir()
        _git(other, "init", "-q")
        proc = self._run(str(EVAL_DIR), "--trials", "1",
                         results_dir=other / ".git" / "nested" / "out")
        self._assert_nothing_ran(proc)
        self.assertIn("git", proc.stderr)
        self.assertFalse((other / ".git" / "nested").exists())

    def test_the_checkout_guard_stands_without_a_git_work_tree(self):
        # In a checkout with no .git (an archive export) the work-tree probe
        # cannot fire, so the path comparison alone must refuse. Patch
        # REPO_ROOT to a non-repository and call the guard in-process.
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        self.addCleanup(sys.path.remove, str(REPO_ROOT / "scripts"))
        import local_eval
        fake_root = self.root / "archive-export"
        (fake_root / "results").mkdir(parents=True)
        link = self.root / "into-archive"
        link.symlink_to(fake_root, target_is_directory=True)
        with mock.patch.object(local_eval, "REPO_ROOT", fake_root):
            for out in (fake_root / "results" / "x", link / "results" / "x",
                        fake_root / "evals" / ".." / "x"):
                with self.subTest(out=str(out)):
                    with self.assertRaises(local_eval.Refused) as ctx:
                        local_eval.check_results_dir(out)
                    self.assertIn("inside this checkout", str(ctx.exception))
            outside = self.root / "elsewhere" / "x"
            self.assertEqual(local_eval.check_results_dir(outside), outside)

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
        self.assertIn(EXHIBIT, proc.stdout, "the console summary is labeled too")

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
        self.assertEqual(manifest["fixtures"][0]["models"]["fixture_pins"],
                         {"model": fixture["model"],
                          "judge_model": fixture["judge"]["model"]})
        self.assertEqual(manifest["fixtures"][0]["models"]["selected"],
                         {"agent": fixture["model"],
                          "judge": fixture["judge"]["model"]})
        head = _git(registry, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(manifest["fixtures"][0]["registry"],
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
        self.assertIsNone(manifest["fixtures"][0]["models"]["selected"]["judge"])

    # -- 3, 5: never publishes; argv lists; no shell ---------------------

    def _shim_dir(self) -> tuple[Path, Path]:
        """A directory of `gh` and `git` shims that log each call (to the
        returned log) and then run the real git, or fail for gh."""
        shims = self.root / "shims"
        shims.mkdir()
        log = self.root / "shim-calls.jsonl"
        for tool, real in (("gh", None), ("git", shutil.which("git"))):
            shim = shims / tool
            shim.write_text(SHIM.format(python=sys.executable, log=str(log),
                                        tool=tool, real=real), encoding="utf-8")
            shim.chmod(0o755)
        return shims, log

    @staticmethod
    def _tree_snapshot() -> dict:
        """{path: mtime_ns} for every file in this checkout outside .git and
        bytecode caches, so a created OR rewritten file shows."""
        snapshot = {}
        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for name in files:
                path = os.path.join(root, name)
                snapshot[path] = os.lstat(path).st_mtime_ns
        return snapshot

    @staticmethod
    def _git_subcommand(argv: list) -> str | None:
        args, i = list(argv), 0
        while i < len(args):
            if args[i] in ("-C", "-c"):
                i += 2
            elif args[i].startswith("-"):
                i += 1
            else:
                return args[i]
        return None

    def test_a_run_never_calls_gh_or_pushes_and_writes_only_to_the_results_dir(self):
        shims, log = self._shim_dir()
        path = os.pathsep.join([str(shims), self._env(self._dispatcher())["PATH"]])
        before = self._tree_snapshot()
        proc = self._run(str(EVAL_DIR), "--trials", "1", "--no-judge",
                         "--registry", f"adam-agentskills={self._registry()}",
                         env_extra={"PATH": path})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = [json.loads(line) for line in
                 log.read_text(encoding="utf-8").splitlines()]
        self.assertTrue(any(c["tool"] == "git" for c in calls),
                        "the shim must be on the path the run really used")
        self.assertEqual([c for c in calls if c["tool"] == "gh"], [])
        subcommands = {self._git_subcommand(c["argv"]) for c in calls
                       if c["tool"] == "git"}
        self.assertEqual(subcommands & {"push", "fetch", "pull", "remote",
                                        "send-pack", "checkout", "switch"},
                         set())
        self.assertEqual(self._tree_snapshot(), before,
                         "the repository must be untouched by a run")

    def test_the_wrapper_builds_every_subprocess_as_an_argv_list(self):
        # A shape check, so it parses the module (an AST, not a regex).
        source = (REPO_ROOT / "scripts" / "local_eval.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        list_names = {t.id for node in ast.walk(tree)
                      if isinstance(node, ast.Assign)
                      and isinstance(node.value, ast.List)
                      for t in node.targets if isinstance(t, ast.Name)}
        spawned = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = ast.unparse(node.func)
            self.assertNotIn(func, ("os.system", "os.popen", "os.spawnl",
                                    "os.execl"), func)
            if func.split(".")[0] != "subprocess":
                continue
            spawned += 1
            first = node.args[0] if node.args else None
            self.assertTrue(
                isinstance(first, ast.List)
                or (isinstance(first, ast.Name) and first.id in list_names),
                f"line {node.lineno}: {func} must take an argv list")
            for kw in node.keywords:
                if kw.arg == "shell":
                    self.fail(f"line {node.lineno}: {func} passes shell=")
        self.assertGreaterEqual(spawned, 2)
        # Nothing here may name a publishing command, in an argv or anywhere
        # else a string can be built (docstrings excluded).
        docstrings = {id(n.value) for n in ast.walk(tree)
                      if isinstance(n, ast.Expr)
                      and isinstance(n.value, ast.Constant)}
        words = {n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and id(n) not in docstrings}
        self.assertEqual(words & {"gh", "push", "workflow", "dispatch"}, set())

    # -- 1: provider selection and credentials, by rule ------------------

    def test_refuses_any_provider_selection_or_credential_variable(self):
        names = ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
                 "CLAUDE_CODE_USE_FOUNDRY", "AWS_BEARER_TOKEN_BEDROCK",
                 "AWS_ACCESS_KEY_ID", "AWS_PROFILE",
                 "GOOGLE_APPLICATION_CREDENTIALS", "GCLOUD_PROJECT",
                 "CLOUDSDK_CORE_PROJECT", "AZURE_CLIENT_ID",
                 "CLAUDE_CONFIG_DIR", "ACME_API_KEY", "acme_auth_token",
                 "ACME_ACCESS_KEY", "ACME_SECRET", "ACME_BEARER")
        for name in names:
            with self.subTest(name=name):
                proc = self._run(str(EVAL_DIR), "--trials", "1",
                                 env_extra={name: "sentinel-value-1234"})
                self._assert_nothing_ran(proc)
                self.assertIn(name, proc.stderr)
                self.assertNotIn("sentinel-value-1234", proc.stderr)
                self.assertFalse(self.out.exists())

    def test_an_unlisted_variable_never_reaches_any_child(self):
        # The refusal list cannot name every variable; the children's
        # environment is an allow-list built here, so this one (on no refusal
        # list) must not appear for the version call, the probe, an arm or
        # the judge.
        allowed = {"PATH", "HOME", "LANG", "LANGUAGE", "TERM", "TMPDIR", "TZ",
                   "CLAUDE_BIN", "SKILLS_EVALS_REGISTRIES", "AGENTSKILLS_DIR"}
        proc = self._run(str(EVAL_DIR), "--trials", "1",
                         "--registry", f"adam-agentskills={self._registry()}",
                         env_extra={"SOME_UNLISTED_VAR": "1",
                                    "CLAUDECODE": "1", "LC_ALL": "C.UTF-8"})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self._calls()
        self.assertEqual({c["role"] for c in calls},
                         {"version", "probe", "agent", "judge"})
        for call in calls:
            with self.subTest(role=call["role"], n=call["n"]):
                for name in ("SOME_UNLISTED_VAR", "CLAUDECODE"):
                    self.assertNotIn(name, call["env_names"])
                if call["role"] in ("version", "judge"):
                    # these inherit the wrapper's whole environment
                    extra = {n for n in call["env_names"]
                             if n not in allowed and not n.startswith("LC_")}
                    self.assertEqual(extra, set())

    # -- 1b: settings files the judge loads ------------------------------

    def _settings(self, content, name="settings.json", home=None):
        directory = (home or self.home) / ".claude"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(
            content if isinstance(content, str) else json.dumps(content),
            encoding="utf-8")

    def test_refuses_a_settings_file_naming_a_credential_source(self):
        cases = (
            ("settings.json", {"apiKeyHelper": "sentinel-helper"}, "apiKeyHelper"),
            ("settings.json", {"awsAuthRefresh": "sentinel-helper"}, "awsAuthRefresh"),
            ("settings.local.json", {"awsCredentialExport": "sentinel-helper"},
             "awsCredentialExport"),
            ("settings.json", {"env": {"ANTHROPIC_API_KEY": "sentinel-helper"}},
             "env.ANTHROPIC_API_KEY"),
            ("settings.json", {"env": {"AWS_ACCESS_KEY_ID": "sentinel-helper"}},
             "env.AWS_ACCESS_KEY_ID"),
            ("settings.json", {"env": {"CLAUDE_CODE_USE_VERTEX": "sentinel-helper"}},
             "env.CLAUDE_CODE_USE_VERTEX"),
            ("settings.json", "{not json sentinel-helper", "not valid JSON"),
            ("settings.json", ["sentinel-helper"], "not a JSON object"))
        for name, content, expected in cases:
            with self.subTest(name=name, expected=expected):
                self._settings(content, name)
                proc = self._run(str(EVAL_DIR), "--trials", "1")
                self._assert_nothing_ran(proc)
                self.assertIn(str(self.home / ".claude" / name), proc.stderr)
                self.assertIn(expected, proc.stderr)
                self.assertNotIn("sentinel-helper", proc.stderr)
                self.assertFalse(self.out.exists())
                (self.home / ".claude" / name).unlink()

    def test_a_settings_file_without_a_credential_source_does_not_stop_the_run(self):
        self._settings({"theme": "dark", "env": {"EXAMPLE_FLAG": "1"},
                        "permissions": {"allow": ["Bash(ls:*)"]}})
        proc = self._run(str(EVAL_DIR), "--trials", "1", "--no-judge",
                         "--registry", f"adam-agentskills={self._registry()}")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_the_settings_check_covers_this_checkout_and_managed_policy(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        self.addCleanup(sys.path.remove, str(REPO_ROOT / "scripts"))
        import local_eval
        fake_repo, managed = self.root / "fake-repo", self.root / "managed"
        (fake_repo / ".claude").mkdir(parents=True)
        (managed / "dropins").mkdir(parents=True)
        home = self.root / "settings-home"
        home.mkdir()
        cases = (
            (fake_repo / ".claude" / "settings.json", {"apiKeyHelper": "x"}),
            (fake_repo / ".claude" / "settings.local.json", {"awsAuthRefresh": "x"}),
            (managed / "managed-settings.json", {"apiKeyHelper": "x"}),
            (managed / "dropins" / "10-extra.json",
             {"env": {"AZURE_CLIENT_SECRET": "x"}}))
        with mock.patch.object(local_eval, "REPO_ROOT", fake_repo), \
                mock.patch.object(local_eval, "MANAGED_SETTINGS_FILES",
                                  (managed / "managed-settings.json",)), \
                mock.patch.object(local_eval, "MANAGED_SETTINGS_DROPINS",
                                  (managed / "dropins",)):
            local_eval.check_user_settings(home)  # nothing there: passes
            for path, content in cases:
                with self.subTest(path=str(path)):
                    path.write_text(json.dumps(content), encoding="utf-8")
                    with self.assertRaises(local_eval.Refused) as ctx:
                        local_eval.check_user_settings(home)
                    self.assertIn(str(path), str(ctx.exception))
                    path.unlink()

    # -- 2: git cannot answer, or a .git sits above ----------------------

    def test_a_git_that_cannot_answer_is_a_refusal_not_no_repository(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        self.addCleanup(sys.path.remove, str(REPO_ROOT / "scripts"))
        import local_eval
        probe = self.root / "plain"
        probe.mkdir()
        for stderr in ("fatal: detected dubious ownership in repository at '/x'\n",
                       "fatal: cannot use bare repository '/x' "
                       "(safe.bareRepository is 'explicit')\n"):
            with self.subTest(stderr=stderr):
                failed = subprocess.CompletedProcess([], 128, "", stderr)
                with mock.patch.object(local_eval, "_git", return_value=failed):
                    with self.assertRaises(local_eval.Refused) as ctx:
                        local_eval.check_results_dir(probe / "out")
                self.assertIn("refused to say", str(ctx.exception))
        with mock.patch.object(local_eval, "_git", side_effect=OSError("no git")):
            with self.assertRaises(local_eval.Refused):
                local_eval.check_results_dir(probe / "out")
        # and the genuine "not a repository" answer still lets it through
        self.assertEqual(local_eval.check_results_dir(probe / "out"),
                         probe / "out")

    def test_a_git_entry_in_a_parent_refuses_without_asking_git(self):
        # An empty .git directory is not a repository to git ("not a git
        # repository"), so only the git-independent parent walk can refuse.
        tree = self.root / "looks-like-a-repo"
        (tree / ".git").mkdir(parents=True)
        proc = self._run(str(EVAL_DIR), "--trials", "1",
                         results_dir=tree / "deeper" / "out")
        self._assert_nothing_ran(proc)
        self.assertIn("holds a git repository", proc.stderr)
        self.assertFalse((tree / "deeper").exists())

    # -- N1: a local trial tree is not badge input -----------------------

    def _make_badge(self, name, results_dir):
        badge = self.root / "badge.json"
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "make_badge.py"), name,
             "--results-dir", str(results_dir), "--out", str(badge)],
            capture_output=True, text=True, env=self._env(self._dispatcher()),
            cwd=str(self.root), timeout=120)
        return proc, badge

    def test_local_trial_summaries_are_stamped_and_refused_as_badge_input(self):
        for eval_dir, skill in ((EVAL_DIR, SKILL),
                                (REPO_ROOT / "evals" / "writing-adrs" / "bootstrap",
                                 "writing-adrs")):
            with self.subTest(skill=skill):
                if self.out.exists():
                    shutil.rmtree(self.out)
                shutil.rmtree(self.root / "registry", ignore_errors=True)
                registry = self._registry(skill)
                proc = self._run(str(eval_dir), "--trials", "1", "--no-judge",
                                 "--registry", f"adam-agentskills={registry}")
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                summaries = sorted(self.out.rglob("summary.json"))
                self.assertEqual(len(summaries), 2)
                for path in summaries:
                    self.assertIs(json.loads(path.read_text(
                        encoding="utf-8"))["local_exhibit"], True, str(path))
                badge_proc, badge = self._make_badge(skill, self.out / "t1")
                self.assertNotEqual(badge_proc.returncode, 0)
                self.assertIn("local exhibit", badge_proc.stderr)
                self.assertFalse(badge.exists())

    def test_an_unstamped_summary_is_still_badge_input(self):
        registry = self._registry()
        proc = self._run(str(EVAL_DIR), "--trials", "1", "--no-judge",
                         "--registry", f"adam-agentskills={registry}")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for path in self.out.rglob("summary.json"):
            summary = json.loads(path.read_text(encoding="utf-8"))
            del summary["local_exhibit"]  # what a published summary looks like
            path.write_text(json.dumps(summary), encoding="utf-8")
        badge_proc, badge = self._make_badge(SKILL, self.out / "t1")
        self.assertEqual(badge_proc.returncode, 0, badge_proc.stderr)
        self.assertTrue(badge.is_file())
        self.assertIn(f"skill eval: {SKILL}",
                      json.loads(badge.read_text(encoding="utf-8"))["label"])

    # -- nested fixtures (run_eval's #66 layout) -------------------------

    def _assert_clean(self, proc, trials, fixtures):
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        aggregate = self._json("aggregate.json")
        self.assertEqual(sorted(aggregate["fixtures"]), sorted(fixtures))
        for name, entry in aggregate["fixtures"].items():
            for arm, got in entry["arms"].items():
                with self.subTest(fixture=name, arm=arm):
                    self.assertEqual((got["n"], got["errors"], got["scored"]),
                                     (trials, 0, trials))
        return aggregate

    def test_a_flat_fixture_runs_clean_under_the_fixtures_key(self):
        proc = self._run(str(EVAL_DIR), "--trials", "2", "--no-judge",
                         "--registry", f"adam-agentskills={self._registry()}")
        aggregate = self._assert_clean(proc, 2, ["(flat)"])
        self.assertEqual(aggregate["arms"], aggregate["fixtures"]["(flat)"]["arms"])

    def test_a_nested_fixture_named_by_its_own_directory_runs_clean(self):
        nested = REPO_ROOT / "evals" / "writing-adrs" / "bootstrap"
        proc = self._run(str(nested), "--trials", "2", "--no-judge",
                         "--registry",
                         f"adam-agentskills={self._registry('writing-adrs')}")
        aggregate = self._assert_clean(proc, 2, ["bootstrap"])
        self.assertEqual(sorted(aggregate["arms"]), ["with_skill", "without_skill"])
        self.assertEqual(
            len(list(self.out.glob("t*/writing-adrs/*/bootstrap/*/summary.json"))), 4)

    def test_a_skill_directory_of_nested_fixtures_runs_all_of_them(self):
        skill_dir = REPO_ROOT / "evals" / "writing-adrs"
        registry = self._registry("writing-adrs")
        proc = self._run(str(skill_dir), "--trials", "2", "--no-judge",
                         "--registry", f"adam-agentskills={registry}")
        aggregate = self._assert_clean(
            proc, 2, ["bootstrap", "existing-convention", "supersede"])
        self.assertNotIn("arms", aggregate, "several fixtures: no single `arms`")
        self.assertEqual(
            [f["name"] for f in self._json("manifest.json")["fixtures"]],
            ["bootstrap", "existing-convention", "supersede"])

    def test_fixture_selects_one_nested_fixture_of_a_skill_directory(self):
        skill_dir = REPO_ROOT / "evals" / "writing-adrs"
        proc = self._run(str(skill_dir), "--fixture", "supersede", "--trials", "1",
                         "--no-judge", "--registry",
                         f"adam-agentskills={self._registry('writing-adrs')}")
        self._assert_clean(proc, 1, ["supersede"])


if __name__ == "__main__":
    unittest.main()
