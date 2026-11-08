#!/usr/bin/env python3
"""Every trial of one arm hands the CLI the same first request.

The CLI's first request embeds its working directory (system prompt, sandbox
rules, session paths) and the workspace's recent commits. A workspace from a
fresh `mkdtemp` and a seed commit dated by the clock made each trial's
request differ, so trials 2..N rewrote the prompt cache trial 1 had just
written instead of reading it. These tests pin what makes them the same:

  * one workspace path per arm, created fresh for each trial
    (`run_eval._trial_slot_dir`), still unique to the run, so concurrent runs
    and the other arm get their own;
  * the harness's seed commits dated once per run (`workspace_git.COMMIT_DATE`);
  * the results directory and, for a multi-turn arm, the session archive made
    before trial 1, since the read rules list only directories that exist.

Hermetic: every CLI call reaches a recording stand-in that hands it to
test/fake-claude; no sleeps, network or clock reads in the tests.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
HARNESS_DIR = REPO_ROOT / "harness"
FAKE_CLAUDE = TEST_DIR / "fake-claude"

sys.path.insert(0, str(HARNESS_DIR))
import run_eval  # noqa: E402
import workspace_git  # noqa: E402

SKILL = "cache-skill"
TS = "20260716T070000Z"
TEST_PATH = os.pathsep.join(dict.fromkeys(
    (str(Path(sys.executable).parent), "/usr/local/bin", "/usr/bin", "/bin")))

# Records every agent call (argv, cwd, the whole environment, the workspace's
# HEAD and its files) to calls.jsonl beside it, then answers as the fake's
# `agent` mode. Its first agent call writes marker.txt into the workspace, so
# a later trial that saw it would be reusing content, not only a path. A call
# that persists its session leaves a transcript where the real CLI would
# (`$HOME/.claude/projects/<cwd, munged>/`), which the harness archives.
RECORDING_CLI = '''\
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAKE = (HERE / "fake").read_text(encoding="utf-8").strip()
if "--version" in sys.argv:
    os.execv(FAKE, [FAKE] + sys.argv[1:])
git_env = {"PATH": "/usr/bin:/bin", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "HOME": os.environ.get("HOME", "/")}
head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, env=git_env).stdout.strip()
log = HERE / "calls.jsonl"
first = not log.exists()
with open(log, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(),
                             "env": dict(os.environ), "head": head,
                             "files": sorted(os.listdir("."))}) + "\\n")
if first:
    Path("marker.txt").write_text("trial one\\n", encoding="utf-8")
if "--no-session-persistence" not in sys.argv:
    name = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(os.getcwd()))
    session = Path(os.environ["HOME"]) / ".claude" / "projects" / name
    session.mkdir(parents=True, exist_ok=True)
    (session / "fake-session.jsonl").write_text("{}\\n", encoding="utf-8")
os.environ["FAKE_CLAUDE_MODE"] = "agent"
os.execv(FAKE, [FAKE] + sys.argv[1:])
'''


class _Run:
    """One `run_eval.py` invocation's scratch: a recording CLI, a fixture, a
    registry, and the child's whole environment."""

    def __init__(self, root: Path, shared_tmp: Path, **fixture_extra):
        self.root = root
        root.mkdir(parents=True)
        self.cli = root / "cli"
        self.cli.mkdir()
        (self.cli / "fake").write_text(str(FAKE_CLAUDE), encoding="utf-8")
        claude = self.cli / "claude"
        claude.write_text(f"#!{sys.executable}\n{RECORDING_CLI}", encoding="utf-8")
        claude.chmod(0o755)
        self.fixture = root / "evals" / SKILL
        (self.fixture / "seed").mkdir(parents=True)
        (self.fixture / "seed" / "README.md").write_text("# seed\n", encoding="utf-8")
        doc = {"skill": SKILL, "registry": "https://github.com/Adam-S-Daniel/adam-agentskills",
               "model": "fake-agent-model", "judge": {"model": "fake-judge-model"},
               "prompt": "Do the task.", "judge_rubric": "Score it.",
               "objective_checks": [{"id": "readme-kept", "type": "file_count",
                                     "paths": ["README.md"], "min": 1}]}
        doc.update(fixture_extra)
        (self.fixture / "fixture.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
        skill_dir = root / "registry" / "plugins" / "b" / "skills" / SKILL
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {SKILL}\ndescription: stand-in.\n---\n", encoding="utf-8")
        home = root / "home"
        # The profile the CLI creates on its first start on any machine; a
        # missing one would appear between trials only because of this test.
        (home / ".claude").mkdir(parents=True)
        (root / "mountinfo").write_text("", encoding="utf-8")
        self.results = root / "results"
        self.env = {"PATH": TEST_PATH, run_eval.MOUNTINFO_ENV: str(root / "mountinfo"),
                    "HOME": str(home), "TMPDIR": str(shared_tmp), "LANG": "C.UTF-8",
                    "PYTHONDONTWRITEBYTECODE": "1", "CLAUDE_BIN": str(claude),
                    "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "maintenance.auto",
                    "GIT_CONFIG_VALUE_0": "false"}

    def argv(self, arm: str, trials: int) -> list[str]:
        return [sys.executable, str(HARNESS_DIR / "run_eval.py"), str(self.fixture),
                "--results-dir", str(self.results), "--timeout", "60",
                "--arm", arm, "--trials", str(trials), "--no-judge",
                "--timestamp", TS, "--registry",
                f"adam-agentskills={self.root / 'registry'}"]

    def start(self, arm: str, trials: int = 2) -> subprocess.Popen:
        return subprocess.Popen(self.argv(arm, trials), env=self.env, cwd=str(REPO_ROOT),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def calls(self) -> list[dict]:
        log = self.cli / "calls.jsonl"
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]


class TestTrialsOfOneArmShareTheFirstRequest(unittest.TestCase):

    def setUp(self):
        # Short and outside this clone's parent: the arm's read rules deny the
        # clone's parent, and long paths push the settings past their cap.
        self.tmp = Path(tempfile.mkdtemp(prefix="trial-cache-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.shared_tmp = self.tmp / "t"
        self.shared_tmp.mkdir()

    def _finish(self, proc: subprocess.Popen) -> None:
        output, _ = proc.communicate(timeout=600)
        self.assertEqual(proc.returncode, 0, output)

    def _assert_same_first_request(self, first: dict, second: dict) -> None:
        self.assertEqual(first["cwd"], second["cwd"])
        self.assertEqual(first["argv"], second["argv"])
        self.assertEqual(first["env"], second["env"])
        self.assertEqual(first["head"], second["head"])
        self.assertRegex(first["head"], r"^[0-9a-f]{40}$")

    def test_two_trials_get_the_same_cwd_env_argv_and_seed_commit(self):
        run = _Run(self.tmp / "a", self.shared_tmp)
        self._finish(run.start("without_skill"))
        first, second = run.calls()
        self._assert_same_first_request(first, second)
        # Same path, fresh content: trial 1's marker is not in trial 2.
        self.assertEqual(first["files"], second["files"])
        self.assertNotIn("marker.txt", second["files"])
        self.assertEqual(Path(first["cwd"]).parent, self.shared_tmp)
        self.assertFalse(Path(first["cwd"]).exists())

    def test_a_multi_turn_arms_trials_start_with_the_same_request(self):
        # The session archive is denied once it exists; trial 1's archiving
        # created it, so trial 2's rules used to name a path trial 1's lacked.
        run = _Run(self.tmp / "a", self.shared_tmp, followups=["And then?"])
        self._finish(run.start("without_skill"))
        calls = run.calls()
        self.assertEqual(len(calls), 4)
        self.assertNotIn("--no-session-persistence", calls[0]["argv"])
        self._assert_same_first_request(calls[0], calls[2])

    def test_a_session_the_last_trial_left_behind_costs_the_reuse(self):
        # The archive cannot be made (a file holds its name), so trial 1's
        # transcript stays in the profile, where trial 2 could read it under
        # the same path: trial 2 gets a fresh path instead.
        run = _Run(self.tmp / "a", self.shared_tmp, followups=["And then?"])
        archive = Path(run.env["HOME"]) / ".local" / "state" / "skills-evals"
        archive.mkdir(parents=True)
        (archive / "sessions").write_text("not a directory\n", encoding="utf-8")
        self._finish(run.start("without_skill"))
        calls = run.calls()
        self.assertEqual(len(calls), 4)
        self.assertNotEqual(calls[0]["cwd"], calls[2]["cwd"])
        left = (Path(run.env["HOME"]) / ".claude" / "projects"
                / run_eval._munged_project_name(Path(calls[0]["cwd"])))
        self.assertTrue(left.is_dir(), left)

    def test_concurrent_runs_and_the_two_arms_get_distinct_paths(self):
        runs = [_Run(self.tmp / name, self.shared_tmp) for name in ("a", "b")]
        procs = [run.start("both") for run in runs]
        for proc in procs:
            self._finish(proc)
        paths = []
        for run in runs:
            # `--arm both` runs with_skill's trials, then without_skill's.
            # Only cwd, env and HEAD: the sandbox's denyRead also lists the
            # other run's harness directories that exist at that moment
            # (`_harness_temp_rules`), which no fix here may drop.
            with_1, with_2, without_1, without_2 = run.calls()
            for first, second in ((with_1, with_2), (without_1, without_2)):
                for key in ("cwd", "env", "head"):
                    self.assertEqual(first[key], second[key], key)
            self.assertNotEqual(with_1["cwd"], without_1["cwd"])
            paths += [with_1["cwd"], without_1["cwd"]]
        self.assertEqual(len(set(paths)), 4, paths)
        for path in paths:
            self.assertEqual(Path(path).parent, self.shared_tmp)
            self.assertTrue(Path(path).name.startswith(run_eval.WORKSPACE_PREFIX))


class TestTrialSlotDir(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="trial-slot-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        patcher = mock.patch.object(run_eval.tempfile, "tempdir", str(self.tmp))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_slot_recreates_the_first_trials_name_empty(self):
        slot: dict = {}
        first = run_eval._trial_slot_dir(slot, _fresh)
        (first / "left.txt").write_text("x\n", encoding="utf-8")
        shutil.rmtree(first)
        second = run_eval._trial_slot_dir(slot, _fresh)
        self.assertEqual(first, second)
        self.assertEqual(list(second.iterdir()), [])
        self.assertEqual(second.stat().st_mode & 0o777, 0o700 & ~_umask())

    def test_anything_left_at_the_name_gets_a_fresh_name_instead(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        for leftover in ("directory", "symlink"):
            with self.subTest(leftover=leftover):
                slot: dict = {}
                first = run_eval._trial_slot_dir(slot, _fresh)
                if leftover == "symlink":
                    first.rmdir()
                    first.symlink_to(outside)
                second = run_eval._trial_slot_dir(slot, _fresh)
                self.assertNotEqual(first, second)
                self.assertEqual(slot["path"], str(second))
                self.assertEqual(list(outside.iterdir()), [])

    def test_a_stale_session_costs_the_reuse(self):
        slot: dict = {}
        first = run_eval._trial_slot_dir(slot, _fresh)
        first.rmdir()
        second = run_eval._trial_slot_dir(slot, _fresh, lambda path: path == first)
        self.assertNotEqual(first, second)

    def test_no_slot_is_a_fresh_name_every_time(self):
        first = run_eval._trial_slot_dir(None, _fresh)
        first.rmdir()
        self.assertNotEqual(first, run_eval._trial_slot_dir(None, _fresh))

    def test_session_left_behind_reads_the_arms_profile(self):
        home = self.tmp / "home"
        workspace = self.tmp / "workspace-x"
        with mock.patch.dict(os.environ, {"HOME": str(home), "PATH": "/usr/bin:/bin"},
                             clear=True):
            self.assertFalse(run_eval._session_left_behind(workspace, None))
            (home / ".claude" / "projects"
             / run_eval._munged_project_name(workspace)).mkdir(parents=True)
            self.assertTrue(run_eval._session_left_behind(workspace, None))

    def test_an_in_place_arms_scratch_is_reused_the_same_way(self):
        plan = {"_pair_config": self.tmp / "pair" / "config"}
        slot: dict = {}
        first = run_eval._in_place_scratch(plan, slot)
        self.assertTrue(first.name.startswith(f"{run_eval.ARM_WORKSPACE_PREFIX}arm-"))
        shutil.rmtree(first)
        self.assertEqual(run_eval._in_place_scratch(plan, slot), first)


class TestSeedCommitIsDatedOncePerRun(unittest.TestCase):

    def test_two_workspaces_of_one_seed_have_the_same_commit(self):
        tmp = Path(tempfile.mkdtemp(prefix="seed-date-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        seed = tmp / "seed"
        seed.mkdir()
        (seed / "README.md").write_text("# seed\n", encoding="utf-8")
        heads = []
        # A date no clock reads today, so a commit dated by the clock fails.
        with mock.patch.object(workspace_git, "COMMIT_DATE", "1700000000 +0000"), \
                mock.patch.object(run_eval.tempfile, "tempdir", str(tmp)):
            for _ in range(2):
                workspace = run_eval.materialize_workspace(seed)
                try:
                    shown = workspace_git.run("log", "-1", "--format=%H %at %ct",
                                              cwd=workspace, check=True).stdout.split()
                finally:
                    workspace_git.release(workspace)
                    shutil.rmtree(workspace, ignore_errors=True)
                heads.append(shown)
        self.assertEqual(heads[0], heads[1])
        self.assertEqual(heads[0][1:], ["1700000000", "1700000000"])


def _fresh() -> str:
    return tempfile.mkdtemp(prefix=run_eval.WORKSPACE_PREFIX)


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


if __name__ == "__main__":
    unittest.main()
