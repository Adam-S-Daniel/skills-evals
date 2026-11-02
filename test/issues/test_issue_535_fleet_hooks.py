#!/usr/bin/env python3
"""#535: the fleet hook runner in arms that stand for the real setup.

ADR 0012's fleet hooks addendum. An in-place arm of a `fleet_hooks: true`
fixture gets the hook set its context deployed (harness/fleet_hooks.py):
frozen from _agent-guidance's `templates/agent-checks/` at the guidance
revision the context loads, proven against the context repository's own
`.githooks/agent-checks`, written read-only into the arm's scratch.

Every repository is a disposable Git repository (test_issue_adr0012_delivery's
`Base`), the template files are small stand-ins, and the npm install is
stubbed: no network, no model, no clock. Run inside a PID namespace.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))

import compute_gates  # noqa: E402
import context  # noqa: E402
import fleet_hooks  # noqa: E402
import gates  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import run_eval  # noqa: E402
from test_issue_adr0012_delivery import Base, GUIDANCE_REPO, PRIMARY  # noqa: E402

FLEET_CONSUMER = "Adam-S-Daniel/consumer"
# A stand-in runner with the real one's contract: an event argument, a
# refusal on a staged `.env`, and the repository's own `.agent-checks/local.sh`
# as a child. It logs each call into the repository's Git directory.
RUNNER = b"""#!/usr/bin/env bash
printf '%s %s\\n' "$1" "${2:-}" >> "$(git rev-parse --git-dir)/runner.log"
top=$(git rev-parse --show-toplevel)
if [ -f "$top/.agent-checks/local.sh" ]; then
  (cd "$top" && bash .agent-checks/local.sh "$1") || exit 1
fi
if [ "$1" = pre-commit ] && git diff --cached --name-only | grep -qx .env; then
  echo "agent-checks: .env: looks like a secret" >&2
  exit 1
fi
exit 0
"""
TEMPLATES = {
    "agent-checks": RUNNER,
    "agent-checks-guard.sh": b"#!/usr/bin/env bash\nexit 0\n",
    "agent-checks.yml": b"name: agent-checks\n",
    "dated-phrasing.js": b"// stand-in\n",
    "dated-phrasing-allowlist.txt": b"# fleet allowlist\n",
    "dated-phrasing/package.json": b'{"name": "x", "dependencies": {"markdown-it": "15.0.3"}}\n',
    "dated-phrasing/package-lock.json": b'{"lockfileVersion": 3}\n',
}
EXECUTABLE = {"agent-checks", "agent-checks-guard.sh"}
REAL_NPM_CI = fleet_hooks._npm_ci


def fake_npm_ci(directory):
    """`fleet_hooks._npm_ci` without the network: what `npm ci` leaves."""
    module = Path(directory) / "node_modules" / "markdown-it"
    module.mkdir(parents=True)
    (module / "package.json").write_text('{"name": "markdown-it", "version": "15.0.3"}')


class HookBase(Base):
    """`Base` with a fleet-owned consumer whose context revision ships the
    runner the pinned guidance revision's template holds."""

    def setUp(self):
        super().setUp()
        templates = {f"templates/agent-checks/{name}": raw for name, raw in TEMPLATES.items()}
        self.guidance_sha = self.commit(self.guidance, templates)
        for name in EXECUTABLE:
            os.chmod(self.guidance / "templates/agent-checks" / name, 0o755)
        self.guidance_sha = self.commit(self.guidance, {})
        self.git(self.guidance, "update-ref", "refs/remotes/origin/main", self.guidance_sha)
        self.revision = self.commit(self.consumer, {".githooks/agent-checks": RUNNER})
        self.repositories = {FLEET_CONSUMER: self.consumer, PRIMARY: self.registry,
                             GUIDANCE_REPO: self.guidance}
        self.metadata = {**self.metadata, "repository": FLEET_CONSUMER,
                         "revision": self.revision, "guidance_revision": self.guidance_sha}
        patcher = mock.patch.object(fleet_hooks, "_npm_ci", fake_npm_ci)
        patcher.start()
        self.addCleanup(patcher.stop)

    def plan(self, skill="sample", section=None, hooks=True, **extra):
        fixture = {"context": self.metadata, "fleet_hooks": hooks}
        if section is None:
            fixture["skill"] = skill
            return run_eval._in_place_plan(fixture, self.args(**extra), self.registries, "skill")
        fixture["section"] = section
        return run_eval._in_place_plan(fixture, self.args(**extra), {}, "guidance")

    def prepare(self, role, plan, seed=None, fixture=None):
        scratch, workspace, env, delivered = super().prepare(role, plan, seed, fixture)
        self.addCleanup(fleet_hooks.unlock, scratch / fleet_hooks.DIRNAME)
        return scratch, workspace, env, delivered

    def freeze(self, guidance_subject=False):
        return fleet_hooks.freeze(self.frozen(), self.repositories,
                                  guidance_subject=guidance_subject)


class FreezeTests(HookBase):
    def test_the_set_is_every_template_file_at_the_loaded_guidance_revision(self):
        hooks = self.freeze()
        self.assertEqual(dict(hooks.files), TEMPLATES)
        self.assertEqual({name for name, mode in hooks.modes.items() if mode == "100755"},
                         EXECUTABLE)
        self.assertEqual(hooks.revision, self.guidance_sha)

    def test_the_digest_is_stable_and_covers_bytes_modes_and_paths(self):
        hooks = self.freeze()
        self.assertRegex(hooks.digest, r"\A[0-9a-f]{64}\Z")
        self.assertEqual(hooks.digest, self.freeze().digest)
        variants = [
            ({**hooks.files, "dated-phrasing.js": b"// changed\n"}, hooks.modes),
            (hooks.files, {**hooks.modes, "agent-checks.yml": "100755"}),
            ({**{k: v for k, v in hooks.files.items() if k != "agent-checks.yml"},
              "agent-checks.yaml": hooks.files["agent-checks.yml"]},
             {**{k: v for k, v in hooks.modes.items() if k != "agent-checks.yml"},
              "agent-checks.yaml": "100644"}),
        ]
        for files, modes in variants:
            self.assertNotEqual(fleet_hooks._digest(files, modes), hooks.digest)

    def test_a_working_tree_edit_is_not_an_input(self):
        (self.guidance / "templates/agent-checks/agent-checks").write_bytes(b"#!/bin/sh\nexit 1\n")
        (self.consumer / ".githooks/agent-checks").write_bytes(b"#!/bin/sh\nexit 1\n")
        self.assertEqual(self.freeze().files["agent-checks"], RUNNER)

    def test_a_context_without_the_runner_is_unproven(self):
        self.git(self.consumer, "rm", "-q", ".githooks/agent-checks")
        self.metadata["revision"] = self.commit(self.consumer, {})
        self.refused("fleet_hooks_unproven", self.freeze)

    def test_a_context_whose_runner_differs_is_unproven(self):
        self.metadata["revision"] = self.commit(self.consumer, {
            ".githooks/agent-checks": RUNNER + b"# local edit\n"})
        self.refused("fleet_hooks_unproven", self.freeze)

    def test_a_guidance_fixture_takes_the_template_itself(self):
        self.metadata["revision"] = self.commit(self.consumer, {
            ".githooks/agent-checks": b"#!/bin/sh\n# older runner\n"})
        self.assertEqual(self.freeze(guidance_subject=True).files["agent-checks"], RUNNER)

    def test_a_guidance_revision_without_the_template_is_unproven(self):
        self.git(self.guidance, "rm", "-q", "templates/agent-checks/agent-checks-guard.sh")
        self.guidance_sha = self.commit(self.guidance, {})
        self.git(self.guidance, "update-ref", "refs/remotes/origin/main", self.guidance_sha)
        self.metadata["revision"] = self.commit(self.consumer, {"touch": b"x\n"})
        self.metadata["guidance_revision"] = self.guidance_sha
        self.refused("fleet_hooks_unproven", lambda: self.freeze(guidance_subject=True))

    def test_a_non_fleet_context_is_unproven(self):
        frozen = self.frozen()
        manifest = dict(frozen.manifest, repository="example/consumer")
        other = context.FrozenContext(manifest, frozen.skills, frozen.guidance, frozen.digest)
        self.refused("fleet_hooks_unproven", lambda: fleet_hooks.freeze(
            other, {**self.repositories, "example/consumer": self.consumer},
            guidance_subject=False))

    def test_the_plan_refuses_before_any_arm(self):
        self.git(self.consumer, "rm", "-q", ".githooks/agent-checks")
        self.metadata["revision"] = self.commit(self.consumer, {})
        self.refused("fleet_hooks_unproven", self.plan)

    def test_an_unhooked_plan_has_no_hook_set(self):
        self.assertNotIn("fleet_hooks", self.plan(hooks=False))

    def test_a_failed_npm_install_is_named(self):
        def fail(directory):
            raise context.ContextError("fleet_hooks_install_failed", "npm ci exited 1")
        with mock.patch.object(fleet_hooks, "_npm_ci", fail):
            self.refused("fleet_hooks_install_failed", self.plan)
        with mock.patch.object(fleet_hooks, "_npm_ci", lambda directory: None):
            self.refused("fleet_hooks_install_failed", self.plan)

    def test_npm_ci_runs_from_the_frozen_lockfile_without_scripts(self):
        calls = []

        def run(argv, **kwargs):
            calls.append((argv, kwargs["cwd"], sorted(p.name for p in Path(kwargs["cwd"]).iterdir())))
            fake_npm_ci(kwargs["cwd"])
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        hooks = self.freeze()
        with mock.patch.object(fleet_hooks, "_npm_ci", REAL_NPM_CI), \
                mock.patch.object(fleet_hooks.subprocess, "run", run):
            modules = fleet_hooks.install_modules(hooks)
        self.assertEqual(calls[0][0], ["npm", "ci", "--ignore-scripts", "--no-audit",
                                       "--no-fund", "--loglevel=error"])
        self.assertEqual(calls[0][2], ["package-lock.json", "package.json"])
        self.assertEqual((modules / "package-lock.json").read_bytes(),
                         TEMPLATES["dated-phrasing/package-lock.json"])

    def test_a_hooked_fixture_may_not_set_git_config_in_its_env(self):
        for key in ("GIT_CONFIG_COUNT", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_PARAMETERS"):
            with self.subTest(key=key):
                raw = f"prompt: p\nfleet_hooks: true\nenv:\n  {key}: '0'\n".encode()
                self.refused("fleet_hooks_git_config_env",
                             lambda: context.load_fixture_yaml(raw, "fixture.yaml"))
        # Unhooked, the key is the fixture's own business, as before.
        context.load_fixture_yaml(b"prompt: p\nfleet_hooks: false\nenv:\n  GIT_CONFIG_COUNT: '0'\n",
                                  "fixture.yaml")


class MaterializeTests(HookBase):
    def hook_files(self, scratch):
        root = scratch / fleet_hooks.DIRNAME / fleet_hooks.HOOKS_SUBDIR
        return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mode & 0o777)
                for p in sorted(root.rglob("*")) if p.is_file()}

    def test_each_arm_gets_the_set_read_only_outside_ws_and_tmp(self):
        plan = self.plan()
        scratch, workspace, env, _ = self.prepare("with", plan)
        directory = scratch / fleet_hooks.DIRNAME
        self.assertEqual(directory.parent, workspace.parent)
        self.assertNotIn(directory, (Path(env["TMPDIR"]), workspace))
        files = self.hook_files(scratch)
        for name, raw in TEMPLATES.items():
            self.assertEqual(files[name], (raw, 0o555 if name in EXECUTABLE else 0o444))
        self.assertIn("dated-phrasing/node_modules/markdown-it/package.json", files)
        for current, dirs, names in os.walk(directory):
            self.assertEqual(Path(current).stat().st_mode & 0o777, 0o555, current)
            for name in names:
                self.assertEqual(Path(current, name).stat().st_mode & 0o222, 0, name)
        with self.assertRaises(PermissionError):
            (directory / fleet_hooks.HOOKS_SUBDIR / "agent-checks").write_bytes(b"x")
        with self.assertRaises(PermissionError):
            (directory / "new-file").write_bytes(b"x")
        self.assertEqual((directory / fleet_hooks.RECEIPT).read_text().strip(),
                         os.readlink("/proc/self/ns/net"))

    def test_both_arms_of_a_pair_get_identical_sets_and_one_digest(self):
        plan = self.plan()
        with_scratch, *_ = self.prepare("with", plan)
        without_scratch, *_ = self.prepare("without", plan)
        self.assertEqual(self.hook_files(with_scratch), self.hook_files(without_scratch))
        # One plan, one frozen set: its digest is the same for the second plan
        # of the same context, which is what pools trials and runs together.
        self.assertEqual(plan["fleet_hooks"].digest, self.plan()["fleet_hooks"].digest)

    def test_a_guidance_pair_gets_the_set_too(self):
        plan = self.plan(section="python")
        scratch, *_ = self.prepare("with", plan)
        self.assertEqual(self.hook_files(scratch)["agent-checks"][0], RUNNER)

    def test_an_unhooked_arm_gets_nothing(self):
        scratch, *_ = self.prepare("with", self.plan(hooks=False))
        self.assertFalse((scratch / fleet_hooks.DIRNAME).exists())

    def test_the_tree_digest_sees_a_change_in_bytes_mode_or_entries(self):
        scratch, *_ = self.prepare("with", self.plan())
        directory = scratch / fleet_hooks.DIRNAME
        before = fleet_hooks.tree_digest(directory)
        self.assertEqual(before, fleet_hooks.tree_digest(directory))
        fleet_hooks.unlock(directory)
        runner = directory / fleet_hooks.HOOKS_SUBDIR / "agent-checks"
        for change in (lambda: runner.chmod(0o777), lambda: runner.write_bytes(b"x"),
                       lambda: (directory / "extra").write_bytes(b"")):
            change()
            self.assertNotEqual(fleet_hooks.tree_digest(directory), before)

    def test_unlock_lets_the_scratch_go(self):
        scratch = Path(tempfile.mkdtemp(prefix="fleet-hooks-test-"))
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        fleet_hooks.materialize(self.freeze(), scratch / fleet_hooks.DIRNAME,
                                fleet_hooks.install_modules(self.freeze()))
        fleet_hooks.unlock(scratch / fleet_hooks.DIRNAME)
        shutil.rmtree(scratch)
        self.assertFalse(scratch.exists())


BWRAP = "/usr/bin/bwrap"
# The arm's sandbox as far as a hook can tell: another network namespace.
# Claude Code's Linux sandbox is bubblewrap with its own network namespace.
SANDBOX = [BWRAP, "--dev-bind", "/", "/", "--unshare-net", "--"]
GIT = ["git", "-c", "user.name=Agent", "-c", "user.email=agent@example.com"]


def sandbox_available() -> bool:
    try:
        return subprocess.run([*SANDBOX, "/usr/bin/true"], capture_output=True,
                              timeout=30).returncode == 0
    except OSError:
        return False


@unittest.skipUnless(sandbox_available(), "bubblewrap with a network namespace is not available")
class InjectionTests(HookBase):
    """The hooks reach the agent's Git, inside the sandbox, and nothing else."""

    def arm(self, plan=None):
        scratch, workspace, env, _ = self.prepare("with", plan or self.plan())
        return scratch, workspace, env

    def git_in(self, workspace, env, *args, sandboxed=True):
        return subprocess.run([*(SANDBOX if sandboxed else []), *GIT, *args], cwd=workspace,
                              env=env, capture_output=True, text=True, timeout=60)

    def runner_log(self, repo):
        log = Path(repo) / ".git" / "runner.log"
        return log.read_text() if log.exists() else ""

    def stage_secret(self, workspace, env):
        (workspace / ".env").write_text("TOKEN=x\n")
        self.assertEqual(self.git_in(workspace, env, "add", ".env", sandboxed=False).returncode, 0)

    def test_an_agent_commit_inside_the_sandbox_fires_the_frozen_runner(self):
        _, workspace, env = self.arm()
        self.assertFalse((workspace / ".githooks").exists(), "the seed carries no runner")
        self.stage_secret(workspace, env)
        refused = self.git_in(workspace, env, "commit", "-q", "-m", "secret")
        self.assertNotEqual(refused.returncode, 0, refused.stderr)
        self.assertIn("agent-checks: .env", refused.stderr)
        self.assertEqual(self.runner_log(workspace), "pre-commit \n")
        # The repository's own checks run too, inside the sandbox.
        self.git_in(workspace, env, "reset", "-q", sandboxed=False)
        (workspace / ".env").unlink()
        (workspace / ".agent-checks").mkdir()
        (workspace / ".agent-checks" / "local.sh").write_text(
            'touch "$(git rev-parse --git-dir)/local-ran"\n')
        self.git_in(workspace, env, "add", ".agent-checks", sandboxed=False)
        done = self.git_in(workspace, env, "commit", "-q", "-m", "checks")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((workspace / ".git" / "local-ran").exists())

    def test_pre_push_gets_the_remote_and_url(self):
        _, workspace, env = self.arm()
        bare = self.root / "bare.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True, env=self.env)
        pushed = self.git_in(workspace, env, "push", "-q", str(bare), "HEAD:refs/heads/topic")
        self.assertEqual(pushed.returncode, 0, pushed.stderr)
        self.assertEqual(self.runner_log(workspace), f"pre-push {bare}\n")

    def test_a_commit_from_outside_the_sandbox_runs_nothing(self):
        # A Claude Code hook runs outside the sandbox with the agent's
        # environment: the receipt keeps it from running local.sh.
        _, workspace, env = self.arm()
        (workspace / ".agent-checks").mkdir()
        (workspace / ".agent-checks" / "local.sh").write_text(
            'touch "$(git rev-parse --git-dir)/local-ran"\n')
        self.stage_secret(workspace, env)
        done = self.git_in(workspace, env, "commit", "-q", "-m", "outside", sandboxed=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.runner_log(workspace), "")
        self.assertFalse((workspace / ".git" / "local-ran").exists())

    def test_a_nested_repository_with_a_foreign_remote_fires_nothing(self):
        _, workspace, env = self.arm()
        nested = workspace / "vendor" / "lib"
        nested.mkdir(parents=True)
        self.git_in(nested, env, "init", "-q", sandboxed=False)
        self.git_in(nested, env, "remote", "add", "origin", "https://github.com/example/lib.git",
                    sandboxed=False)
        self.stage_secret(nested, env)
        done = self.git_in(nested, env, "commit", "-q", "-m", "nested")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.runner_log(nested), "")

    def test_negative_control_without_the_injected_config_nothing_fires(self):
        # The first test's commit with the GIT_CONFIG_* keys taken out: the
        # same frozen files and origin, and the runner never runs, so that
        # test fails without the injection.
        _, workspace, env = self.arm()
        bare = {k: v for k, v in env.items() if not k.startswith("GIT_CONFIG")}
        self.stage_secret(workspace, bare)
        done = self.git_in(workspace, bare, "commit", "-q", "-m", "secret")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.runner_log(workspace), "")

    def test_the_agent_environment_carries_the_include_and_runner_settings(self):
        scratch, workspace, env = self.arm()
        directory = scratch / fleet_hooks.DIRNAME
        self.assertEqual(env["GIT_CONFIG_COUNT"], "9")
        keys = {env[f"GIT_CONFIG_KEY_{i}"] for i in range(9)}
        self.assertIn("includeIf.hasconfig:remote.*.url:https://github.com/Adam-S-Daniel/**.path",
                      keys)
        self.assertIn("includeIf.hasconfig:remote.*.url:git@github.com:jodidaniel/**.path", keys)
        self.assertEqual({env[f"GIT_CONFIG_VALUE_{i}"] for i in range(9)},
                         {str(directory / fleet_hooks.INCLUDE)})
        self.assertFalse(any("hooksPath" in env[f"GIT_CONFIG_KEY_{i}"] for i in range(9)))
        self.assertEqual(env["AGENT_CHECKS_LOG"], "off")
        self.assertEqual(env["AGENT_CHECKS_DATED_PHRASING_MODULES"],
                         str(directory / ".githooks/dated-phrasing/node_modules"))
        self.assertEqual(self.git_in(workspace, env, "remote", "get-url", "origin",
                                     sandboxed=False).stdout.strip(),
                         f"https://github.com/{FLEET_CONSUMER}.git")

    def test_harness_git_runs_no_hook_even_with_the_keys_in_its_own_environment(self):
        _, workspace, env = self.arm()
        # An include whose hook fires anywhere, so only the env decides.
        include = self.root / "loud.inc"
        include.write_text('[hook "loud"]\n\tevent = pre-commit\n'
                           '\tcommand = "touch \\"$(git rev-parse --git-dir)/loud\\""\n')
        keys = {k: (str(include) if k.startswith("GIT_CONFIG_VALUE") else v)
                for k, v in env.items() if k.startswith("GIT_CONFIG")}
        with mock.patch.dict(os.environ, keys):
            # The control: plain Git with this environment fires it.
            control = self.root / "control"
            subprocess.run(["git", "init", "-q", str(control)], check=True)
            subprocess.run(["git", "-C", str(control), "remote", "add", "origin",
                            f"https://github.com/{FLEET_CONSUMER}.git"], check=True)
            subprocess.run([*GIT, "-C", str(control), "commit", "-q", "--allow-empty", "-m", "c"],
                           check=True)
            self.assertTrue((control / ".git" / "loud").exists())
            run_eval.workspace_git.run("commit", "-q", "--allow-empty", "-m", "harness",
                                       cwd=workspace, check=True)
            self.assertFalse(list(Path(tempfile.gettempdir()).glob("trusted-git-*/**/loud")))
            self.assertFalse((workspace / ".git" / "loud").exists())
            self.assertFalse(any(k.startswith("GIT_CONFIG_") and k not in (
                "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL") for k in run_eval.workspace_git._env(
                    self.root)))
            frozen = context._Git(FLEET_CONSUMER, self.repositories)
            self.assertNotIn("GIT_CONFIG_COUNT", frozen.env)
            self.assertEqual((frozen.env["GIT_CONFIG_GLOBAL"], frozen.env["GIT_CONFIG_NOSYSTEM"]),
                             ("/dev/null", "1"))
            import harness_repo
            self.assertNotIn("GIT_CONFIG_COUNT", harness_repo._env())
            self.assertEqual((harness_repo._env()["GIT_CONFIG_GLOBAL"],
                              harness_repo._env()["GIT_CONFIG_NOSYSTEM"]), ("/dev/null", "1"))

    def test_a_seed_with_its_own_origin_is_refused(self):
        seed = self.seed()
        fixture = {"setup": "git init -q && git remote add origin https://github.com/example/x.git"}
        plan = self.plan()
        self.refused("fleet_hooks_origin_exists", lambda: self.prepare("with", plan, seed, fixture))


class SandboxSettingsTests(HookBase):
    def test_the_dir_is_write_denied_and_the_guard_is_the_arms_pre_tool_use_hook(self):
        scratch, workspace, _, _ = self.prepare("with", self.plan())
        directory = scratch / fleet_hooks.DIRNAME
        settings = run_eval.arm_sandbox_settings(workspace=workspace, fleet_hooks_dir=directory)
        self.assertIn(str(directory), settings["sandbox"]["filesystem"]["denyWrite"])
        for rule in (f"Edit(/{directory})", f"Edit(/{directory}/**)"):
            self.assertIn(rule, settings["permissions"]["deny"])
        self.assertEqual(settings["hooks"], {"PreToolUse": [{
            "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit", "hooks": [{
                "type": "command", "timeout": 10,
                "command": f"bash {directory}/.githooks/agent-checks-guard.sh"}]}]})
        self.assertNotIn("hooks", run_eval.arm_sandbox_settings(workspace=workspace))
        self.assertTrue(os.access(directory / ".githooks/agent-checks", os.R_OK))
        self.assertFalse(os.access(directory / ".githooks/agent-checks", os.W_OK))


# A `claude` that records what a hooked arm receives and acts in its cwd:
# `commit` stages a secret and commits it inside a sandbox and outside one;
# `tamper` writes into the frozen hook set from outside the sandbox.
AGENT = f"""#!{sys.executable}
import json, os, subprocess, sys
from pathlib import Path
argv = sys.argv[1:]
if argv == ["--version"]:
    print("2.1.293 (Claude Code)")
    sys.exit(0)
settings = json.loads(argv[argv.index("--settings") + 1])
rec = {{"env": {{k: v for k, v in os.environ.items() if k.startswith(("GIT_CONFIG", "AGENT_CHECKS"))}},
        "hooks": settings.get("hooks"), "deny_write": settings["sandbox"]["filesystem"]["denyWrite"],
        "deny": settings["permissions"]["deny"]}}
git = {GIT!r}
mode = os.environ.get("HOOK_MODE")
if mode == "commit":
    Path(".env").write_text("TOKEN=x\\n")
    subprocess.run(git + ["add", ".env"], check=True)
    inside = subprocess.run({SANDBOX!r} + git + ["commit", "-q", "-m", "x"], capture_output=True, text=True)
    outside = subprocess.run(git + ["commit", "-q", "-m", "x"], capture_output=True, text=True)
    rec["inside"] = [inside.returncode, inside.stderr]
    rec["outside"] = [outside.returncode, outside.stderr]
elif mode == "tamper":
    directory = Path(os.environ["AGENT_CHECKS_DATED_PHRASING_MODULES"]).parents[2]
    os.chmod(directory, 0o755)
    (directory / "planted").write_text("x")
with open(os.environ["REC_LOG"], "a") as fh:
    fh.write(json.dumps(rec) + "\\n")
print(json.dumps({{"type": "result", "is_error": False, "result": "done", "total_cost_usd": 0,
                  "usage": {{}}, "num_turns": 1, "duration_ms": 1, "session_id": "s1",
                  "modelUsage": {{}}}}))
"""
# `npm` on PATH for the harness's own process: what `npm ci` leaves.
FAKE_NPM = """#!/bin/sh
[ "$1" = ci ] || exit 64
mkdir -p node_modules/markdown-it && printf '{"name":"markdown-it"}' > node_modules/markdown-it/package.json
"""


class MainRun(HookBase):
    """run_eval's main() on a hooked in-place skill pair, with AGENT as the
    CLI and FAKE_NPM as npm."""
    TS = "20261102T000000Z"

    def setUp(self):
        super().setUp()
        agent = self.root / "agent"
        agent.write_text(AGENT, encoding="utf-8")
        agent.chmod(0o755)
        npm = self.bin / "npm"
        npm.write_text(FAKE_NPM)
        npm.chmod(0o755)
        self.env["CLAUDE_BIN"] = str(agent)
        registries = self.root / "registries"
        self.registry_env = ",".join(f"{name}={registries / name}" for name in (
            "cms-platform", "adamdaniel.ai", "adam-agentskills-private"))
        for name in ("cms-platform", "adamdaniel.ai", "adam-agentskills-private"):
            (registries / name).mkdir(parents=True)

    def run_main(self, mode, arm="both", hooks=True):
        directory = self.root / "evals" / "sample"
        (directory / "seed").mkdir(parents=True, exist_ok=True)
        (directory / "seed" / "README.md").write_text("x\n", encoding="utf-8")
        (directory / "fixture.yaml").write_text(yaml.safe_dump({
            "skill": "sample", "registry": "https://github.com/Adam-S-Daniel/adam-agentskills",
            "prompt": "do it", "model": "claude-test-model", "fleet_hooks": hooks,
            "env": {"REC_LOG": str(self.log), "HOOK_MODE": mode},
            "objective_checks": [{"id": "seed-kept", "description": "d",
                                  "type": "files_unchanged", "paths": ["README.md"]}],
            "context": self.metadata}), encoding="utf-8")
        env = dict(self.env, SKILLS_EVALS_REGISTRIES=self.registry_env,
                   CLAUDE_CODE_REMOTE_SESSION_ID="session_test")
        repos = [f"--context-repo={k}={v}" for k, v in self.repositories.items()]
        return subprocess.run(
            [sys.executable, "harness/run_eval.py", str(directory), "--registry",
             f"adam-agentskills={self.registry}", "--results-dir", str(self.root / "results"),
             "--timeout", "60", "--no-judge", "--arm", arm, "--pairing", "in_place",
             "--timestamp", self.TS, *repos],
            capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=600)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def summary(self, arm):
        return json.loads((self.root / "results" / "sample" / self.TS / arm / "summary.json")
                          .read_bytes())



@unittest.skipUnless(sandbox_available(), "bubblewrap with a network namespace is not available")
class EndToEndTests(MainRun):
    def test_the_agent_commits_through_the_frozen_runner_inside_its_sandbox(self):
        proc = self.run_main("commit")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self.calls()
        self.assertEqual(len(calls), 2)
        for call in calls:
            self.assertNotEqual(call["inside"][0], 0, call)
            self.assertIn("agent-checks: .env", call["inside"][1])
            self.assertEqual(call["outside"][0], 0, call)
            directory = call["env"]["GIT_CONFIG_VALUE_0"].rsplit("/", 1)[0]
            self.assertIn(directory, call["deny_write"])
            self.assertIn(f"Edit(/{directory}/**)", call["deny"])
            self.assertEqual(call["hooks"], fleet_hooks.guard_hooks(directory))
            self.assertEqual(call["env"]["AGENT_CHECKS_LOG"], "off")
        self.assertEqual(calls[0]["hooks"]["PreToolUse"][0]["matcher"],
                         calls[1]["hooks"]["PreToolUse"][0]["matcher"])

    def test_an_unhooked_fixture_gets_no_hooks(self):
        proc = self.run_main("commit", hooks=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for call in self.calls():
            self.assertEqual(call["env"], {})
            self.assertIsNone(call["hooks"])
            self.assertEqual(call["inside"][0], 0, call)

    def test_a_write_into_the_frozen_set_fails_the_arm(self):
        proc = self.run_main("tamper", arm="with_skill")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        error = self.summary("with_skill")["error"]
        self.assertEqual(error["type"], "agent_wrote_agent_config")
        self.assertIn(fleet_hooks.DIRNAME, error["detail"])


class PoolingTests(MainRun):
    """The hook-set digest is recorded, ingested and pooled on (#535)."""

    def runs(self, hooks_first=True):
        stamps = {True: "20261102T000000Z", False: "20261102T010000Z"}
        for hooks in (True, False):
            self.TS = stamps[hooks]
            proc = self.run_main("none", hooks=hooks)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.TS = stamps[True]
        index = compute_gates.build_index(self.root, self.root / "evals", "99991231T235959Z")
        self.assertEqual(index["skipped"], {})
        by = {}
        for run in index["runs"]:
            by[(run["timestamp"] == stamps[True], run["role"])] = run
        return by

    def test_both_arms_record_the_plan_digest_and_ingest(self):
        proc = self.run_main("none")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        digests = set()
        for arm in ("with_skill", "without_skill"):
            path = self.root / "results" / "sample" / self.TS / arm / "summary.json"
            doc = json.loads(path.read_bytes())
            ingest.check_summary(doc, path.name, ingest.parse_result_path(
                path.relative_to(self.root / "results").as_posix()))
            digests.add(doc["context"]["fleet_hooks_digest"])
        self.assertEqual(digests, {self.freeze().digest})
        bad = json.loads(path.read_bytes())
        bad["context"]["fleet_hooks_digest"] = "sha256:" + "0" * 64
        with self.assertRaises(ingest.Rejected):
            ingest.check_summary(bad, path.name, ingest.parse_result_path(
                path.relative_to(self.root / "results").as_posix()))

    def test_an_unhooked_summary_has_no_digest(self):
        proc = self.run_main("none", hooks=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("fleet_hooks_digest", self.summary("with_skill")["context"])

    def test_runs_differing_only_in_hook_delivery_never_pool(self):
        by = self.runs()
        digest = self.freeze().digest
        for role in ("with", "without"):
            hooked, plain = by[(True, role)], by[(False, role)]
            self.assertEqual(hooked["fleet_hooks_digest"], digest)
            self.assertIsNone(plain["fleet_hooks_digest"])
            # The unhooked keys are exactly what they were before the hooks.
            summary = json.loads((self.root / plain["path"] / f"{role}_skill" / "summary.json")
                                 .read_bytes())
            self.assertEqual(plain["pair_key"], f"{summary['arm_context']['others_digest']}:"
                                                f"{summary['context']['guidance']['digest']}")
            self.assertEqual(plain["arm_context_digest"],
                             f"{summary['arm_context']['skills_digest']}:"
                             f"{summary['arm_context']['guidance_digest']}")
            self.assertEqual((hooked["pair_key"], hooked["arm_context_digest"]),
                             (f"{plain['pair_key']}:{digest}",
                              f"{plain['arm_context_digest']}:{digest}"))
        model = by[(True, "with")]["model"]
        # Each kind alone is a cell; one arm of each is no pair at all.
        self.assertEqual(gates._joint_context([by[(True, "with")]], [by[(False, "without")]],
                                              [model]), (None, None, None))
        self.assertEqual(gates._joint_context([by[(False, "with")]], [by[(True, "without")]],
                                              [model]), (None, None, None))
        with_ctx, without_ctx, pair = gates._joint_context(
            [by[(True, "with")], by[(False, "with")]],
            [by[(True, "without")], by[(False, "without")]], [model])
        self.assertIn(pair, (by[(True, "with")]["pair_key"], by[(False, "with")]["pair_key"]))


class GuidanceReasonTests(unittest.TestCase):
    """Item 10: the alone pair never runs the hooks, so a hooked in-situ
    retire that helps alone names them as a possible cover."""

    def verdict(self, hooked):
        from test_issue_124_guidance_gates import EXPECT, pair_runs
        from test_issue_70_retirement import FLAT, FLAT_JUDGE, GAIN, TEST_POLICY
        in_situ = pair_runs("in_situ", FLAT, FLAT)
        for run in in_situ:
            run["fleet_hooks_digest"] = "a" * 64 if hooked else None
        runs = in_situ + pair_runs("alone", GAIN * 2, FLAT, ([8.0] * 20, FLAT_JUDGE))
        return gates.guidance_verdict({"runs": runs}, ["model-a"], "sec", TEST_POLICY, EXPECT)

    def test_the_reason_names_the_fleet_hooks_only_for_hooked_runs(self):
        hooked, plain = self.verdict(True), self.verdict(False)
        self.assertEqual((hooked["verdict"], plain["verdict"]),
                         ("shorten-or-merge", "shorten-or-merge"))
        self.assertTrue(hooked["reason"].endswith(
            "the rest of the guidance or the fleet hooks cover it"), hooked["reason"])
        self.assertTrue(plain["reason"].endswith("the rest of the guidance covers it"),
                        plain["reason"])


if __name__ == "__main__":
    unittest.main()
