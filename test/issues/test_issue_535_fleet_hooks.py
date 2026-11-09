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
import regression  # noqa: E402
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
# A stand-in guard shaped like the real one: `python3 -c` on the event,
# exit 2 on `--no-verify`.
GUARD = b"""#!/usr/bin/env bash
command -v python3 >/dev/null 2>&1 || exit 0
python3 -c '
import json, sys
event = json.load(sys.stdin)
if "--no-verify" in str((event.get("tool_input") or {}).get("command") or ""):
    sys.stderr.write("agent-checks-guard: refused\\n")
    sys.exit(2)
'
rc=$?
[ "$rc" -eq 2 ] && exit 2
exit 0
"""
TEMPLATES = {
    "agent-checks": RUNNER,
    "agent-checks-guard.sh": GUARD,
    "dated-phrasing.js": b"// stand-in\n",
    "dated-phrasing-allowlist.txt": b"# fleet allowlist\n",
    "dated-phrasing/package.json": b'{"name": "x", "dependencies": {"markdown-it": "15.0.3"}}\n',
    "dated-phrasing/package-lock.json": b'{"lockfileVersion": 3}\n',
}
EXECUTABLE = {"agent-checks", "agent-checks-guard.sh"}
# What the sync delivers into a consumer, by template name.
SHIPPED = {fleet_hooks.CONSUMER_PATHS[name]: raw for name, raw in TEMPLATES.items()}
REAL_NPM_CI = fleet_hooks._npm_ci


def fake_npm_ci(directory):
    """`fleet_hooks._npm_ci` without the network: what `npm ci` leaves."""
    module = Path(directory) / "node_modules" / "markdown-it"
    module.mkdir(parents=True)
    (module / "package.json").write_text('{"name": "markdown-it", "version": "15.0.3"}')


class HookBase(Base):
    """`Base` with a fleet-owned consumer whose context revision ships the
    set the pinned guidance revision's template holds."""

    def setUp(self):
        super().setUp()
        templates = {f"templates/agent-checks/{name}": raw for name, raw in TEMPLATES.items()}
        templates["templates/agent-checks/agent-checks.yml"] = b"name: agent-checks\n"
        self.guidance_sha = self.commit(self.guidance, templates)
        for name in EXECUTABLE:
            os.chmod(self.guidance / "templates/agent-checks" / name, 0o755)
        self.guidance_sha = self.commit(self.guidance, {})
        self.git(self.guidance, "update-ref", "refs/remotes/origin/main", self.guidance_sha)
        self.revision = self.ship(SHIPPED)
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

    def ship(self, files):
        """A consumer commit with `files`, the set's two scripts executable."""
        revision = self.commit(self.consumer, files)
        for name in EXECUTABLE:
            path = self.consumer / fleet_hooks.CONSUMER_PATHS[name]
            if path.exists():
                path.chmod(0o755)
        return self.commit(self.consumer, {})

    def prepare(self, role, plan, seed=None, fixture=None):
        # Base.prepare's own, with the unlock registered before anything can
        # raise, so a read-only set never outlives a failed prepare.
        scratch = Path(tempfile.mkdtemp(prefix=f"{run_eval.ARM_WORKSPACE_PREFIX}test-"))
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        self.addCleanup(fleet_hooks.unlock, scratch / fleet_hooks.DIRNAME)
        self.addCleanup(run_eval.workspace_git.release, scratch / "ws")
        workspace, env, delivered = run_eval._prepare_in_place(
            role, fixture or {}, seed or self.seed(), plan, scratch)
        return scratch, workspace, env, delivered

    def freeze(self, guidance_subject=False):
        return fleet_hooks.freeze(self.frozen(), self.repositories,
                                  guidance_subject=guidance_subject)


class FreezeTests(HookBase):
    def test_a_skill_fixtures_set_is_what_the_context_shipped(self):
        hooks = self.freeze()
        self.assertEqual(dict(hooks.files), TEMPLATES)
        self.assertEqual({name for name, mode in hooks.modes.items() if mode == "100755"},
                         EXECUTABLE)
        self.assertEqual(hooks.revision, self.revision)

    def test_a_guidance_fixtures_set_is_the_template_at_the_loaded_revision(self):
        hooks = self.freeze(guidance_subject=True)
        self.assertEqual(dict(hooks.files), TEMPLATES)
        self.assertEqual(hooks.revision, self.guidance_sha)
        self.assertEqual(hooks.digest, self.freeze().digest)

    def test_only_dated_phrasing_or_only_the_guard_differing_is_the_contexts(self):
        # The runner is the same blob in both; the rest of the set is not.
        template = self.freeze(guidance_subject=True)
        for name, raw in (("dated-phrasing.js", b"// older pass\n"),
                          ("agent-checks-guard.sh", GUARD + b"# older guard\n")):
            with self.subTest(name=name):
                self.metadata["revision"] = self.ship({fleet_hooks.CONSUMER_PATHS[name]: raw})
                hooks = self.freeze()
                self.assertEqual(hooks.files[name], raw)
                self.assertEqual(hooks.files["agent-checks"], template.files["agent-checks"])
                self.assertNotEqual(hooks.digest, template.digest)
                self.metadata["revision"] = self.ship(SHIPPED)

    def test_a_context_lagging_a_runner_only_template_commit_is_accepted(self):
        self.guidance_sha = self.commit(self.guidance, {
            "templates/agent-checks/agent-checks": RUNNER + b"# newer runner\n"})
        self.git(self.guidance, "update-ref", "refs/remotes/origin/main", self.guidance_sha)
        self.metadata["revision"] = self.ship({"touch": b"x\n"})
        self.metadata["guidance_revision"] = self.guidance_sha
        self.assertEqual(self.freeze().files["agent-checks"], RUNNER)

    def test_a_context_without_the_guard_is_unproven(self):
        self.git(self.consumer, "rm", "-q", ".claude/hooks/agent-checks-guard.sh")
        self.metadata["revision"] = self.commit(self.consumer, {})
        self.refused("fleet_hooks_unproven", self.freeze)

    def test_the_digest_is_stable_and_covers_bytes_modes_and_paths(self):
        hooks = self.freeze()
        self.assertRegex(hooks.digest, r"\A[0-9a-f]{64}\Z")
        self.assertEqual(hooks.digest, self.freeze().digest)
        name = "dated-phrasing.js"
        variants = [
            ({**hooks.files, name: b"// changed\n"}, hooks.modes),
            (hooks.files, {**hooks.modes, name: "100755"}),
            ({**{k: v for k, v in hooks.files.items() if k != name}, "dated.js": hooks.files[name]},
             {**{k: v for k, v in hooks.modes.items() if k != name}, "dated.js": "100644"}),
        ]
        for files, modes in variants:
            self.assertNotEqual(fleet_hooks._digest(files, modes), hooks.digest)
        # The injected configuration is part of it too.
        for function, changed in (
                ("include_text", lambda real: lambda d: real(d) + "# more\n"),
                ("agent_env", lambda real: lambda d: {**real(d), "AGENT_CHECKS_LOG": "on"}),
                ("guard_hooks", lambda real: lambda d: {**real(d), "Stop": []})):
            with self.subTest(function=function), mock.patch.object(
                    fleet_hooks, function, changed(getattr(fleet_hooks, function))):
                self.assertNotEqual(fleet_hooks._digest(hooks.files, hooks.modes), hooks.digest)

    def test_a_working_tree_edit_is_not_an_input(self):
        (self.guidance / "templates/agent-checks/agent-checks").write_bytes(b"#!/bin/sh\nexit 1\n")
        (self.consumer / ".githooks/agent-checks").write_bytes(b"#!/bin/sh\nexit 1\n")
        self.assertEqual(self.freeze().files["agent-checks"], RUNNER)

    def test_a_context_without_the_runner_is_unproven(self):
        self.git(self.consumer, "rm", "-q", ".githooks/agent-checks")
        self.metadata["revision"] = self.commit(self.consumer, {})
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

    def test_an_agent_guidance_context_takes_the_guard_its_settings_register(self):
        # The sync skips _agent-guidance itself: it has `.githooks/` but its
        # guard is the template file its own `.claude/settings.json` names.
        own = {path: raw for path, raw in SHIPPED.items() if not path.startswith(".claude/")}
        revision = self.commit(self.guidance, own)
        for name in EXECUTABLE - {"agent-checks-guard.sh"}:
            (self.guidance / fleet_hooks.CONSUMER_PATHS[name]).chmod(0o755)
        revision = self.commit(self.guidance, {})
        frozen = self.frozen()
        manifest = dict(frozen.manifest, repository=GUIDANCE_REPO, revision=revision)
        own_context = context.FrozenContext(manifest, frozen.skills, frozen.guidance, frozen.digest)
        hooks = fleet_hooks.freeze(own_context, self.repositories, guidance_subject=False)
        self.assertEqual(dict(hooks.files), TEMPLATES)
        self.assertEqual(hooks.revision, revision)
        # Only _agent-guidance reads the template path: a consumer without
        # its `.claude/hooks/` copy is still unproven.
        self.git(self.consumer, "rm", "-q", ".claude/hooks/agent-checks-guard.sh")
        self.commit(self.consumer, {"templates/agent-checks/agent-checks-guard.sh": GUARD})
        self.metadata["revision"] = self.commit(self.consumer, {})
        self.refused("fleet_hooks_unproven", self.freeze)

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
        # The consumer ships another dated-phrasing pass: a guidance plan
        # takes the template at the loaded guidance revision, a skill plan
        # what the consumer shipped.
        self.metadata["revision"] = self.ship({".githooks/dated-phrasing.js": b"// consumer\n"})
        plan = self.plan(section="python")
        scratch, *_ = self.prepare("with", plan)
        self.assertEqual(self.hook_files(scratch)["agent-checks"][0], RUNNER)
        self.assertEqual(plan["fleet_hooks"].files["dated-phrasing.js"],
                         TEMPLATES["dated-phrasing.js"])
        self.assertEqual(self.plan()["fleet_hooks"].files["dated-phrasing.js"], b"// consumer\n")

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
        link = directory / "link"
        changes = {
            "file mode": lambda: runner.chmod(0o777),
            "bytes": lambda: runner.write_bytes(b"x"),
            "new file": lambda: (directory / "extra").write_bytes(b""),
            "new empty directory": lambda: (directory / "empty").mkdir(),
            "new symlink": lambda: link.symlink_to("a"),
            "symlink target": lambda: (link.unlink(), link.symlink_to("b")),
            "root mode": lambda: directory.chmod(0o700),
        }
        for what, change in changes.items():
            with self.subTest(change=what):
                previous = fleet_hooks.tree_digest(directory)
                change()
                self.assertNotEqual(fleet_hooks.tree_digest(directory), previous)

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

    def test_the_hook_command_runs_no_path_lookup_outside_the_sandbox(self):
        # Outside the sandbox PATH is the agent's: a stand-in for anything
        # the command could run before its namespace check never runs.
        _, workspace, env = self.arm()
        marks, stand_ins = self.root / "marks", self.root / "stand-ins"
        marks.mkdir()
        stand_ins.mkdir()
        for name in ("cat", "readlink", "bash", "sh"):
            (stand_ins / name).write_text(f"#!/bin/sh\ntouch {marks / name}\nexit 0\n")
            (stand_ins / name).chmod(0o755)
        planted = dict(env, PATH=f"{stand_ins}:{env['PATH']}")
        self.stage_secret(workspace, env)
        done = subprocess.run(["/usr/bin/git", "-c", "user.name=a", "-c", "user.email=a@example.com",
                               "commit", "-q", "-m", "outside"], cwd=workspace, env=planted,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(sorted(p.name for p in marks.iterdir()), [])
        self.assertEqual(self.runner_log(workspace), "")

    def test_an_empty_or_missing_receipt_runs_nothing_inside_the_sandbox(self):
        # An empty line reads as an empty id; an empty file, or none, fails the read.
        for receipt in ("\n", "", None):
            with self.subTest(receipt=receipt):
                scratch, workspace, env = self.arm()
                directory = scratch / fleet_hooks.DIRNAME
                fleet_hooks.unlock(directory)
                if receipt is None:
                    (directory / fleet_hooks.RECEIPT).unlink()
                else:
                    (directory / fleet_hooks.RECEIPT).write_text(receipt)
                self.stage_secret(workspace, env)
                done = self.git_in(workspace, env, "commit", "-q", "-m", "secret")
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(self.runner_log(workspace), "")

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
    def plan(self, *args, **kwargs):
        self.last_plan = super().plan(*args, **kwargs)
        return self.last_plan

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
                "command": f"cd {directory} && exec /usr/bin/env -i PATH=/usr/bin:/bin "
                           f"HOME={directory} PYTHONSAFEPATH=1 PYTHONNOUSERSITE=1 LC_ALL=C "
                           f"/usr/bin/bash {directory}/.githooks/agent-checks-guard.sh"}]}]})
        self.assertNotIn("hooks", run_eval.arm_sandbox_settings(workspace=workspace))
        self.assertTrue(os.access(directory / ".githooks/agent-checks", os.R_OK))
        self.assertFalse(os.access(directory / ".githooks/agent-checks", os.W_OK))
        modules = Path(plan_modules := self.last_plan["fleet_hooks_modules"])
        hooked = run_eval.arm_sandbox_settings(workspace=workspace, fleet_hooks_dir=directory,
                                               fleet_hooks_modules=modules)
        self.assertIn(str(modules), hooked["sandbox"]["filesystem"]["denyWrite"])
        self.assertIn(f"Edit(/{plan_modules}/**)", hooked["permissions"]["deny"])
        self.assertFalse(os.access(modules / "node_modules", os.W_OK))

    def test_the_guard_runs_nothing_the_agent_planted(self):
        # A Claude Code hook runs outside the sandbox, in the workspace, with
        # the CLI's environment: a module in the cwd, an interpreter first on
        # PATH and a .pth in HOME's user site-packages are all the agent's.
        scratch, workspace, env, _ = self.prepare("with", self.plan())
        command = fleet_hooks.guard_hooks(scratch / fleet_hooks.DIRNAME)["PreToolUse"][0][
            "hooks"][0]["command"]
        marks = self.root / "marks"
        marks.mkdir()
        (workspace / "json.py").write_text(f"open({str(marks / 'json')!r}, 'w')\n")
        stand_ins = workspace / "bin"
        stand_ins.mkdir()
        for name, real in (("python3", "/usr/bin/python3"), ("bash", "/usr/bin/bash")):
            (stand_ins / name).write_text(f"#!/bin/sh\ntouch {marks / name}\nexec {real} \"$@\"\n")
            (stand_ins / name).chmod(0o755)
        # The user site-packages /usr/bin/python3 reads under the arm's HOME
        # (this interpreter's version; the suite runs on the system Python).
        site = (Path(env["HOME"]) / ".local" / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages")
        Path(site).mkdir(parents=True)
        (Path(site) / "planted.pth").write_text(f"import os; open({str(marks / 'pth')!r}, 'w')\n")
        attack = dict(env, PATH=f"{stand_ins}:{env['PATH']}", PYTHONPATH=str(workspace))
        for text, expected in (("git status", 0), ("git commit --no-verify -m x", 2)):
            event = json.dumps({"tool_name": "Bash", "tool_input": {"command": text}})
            result = subprocess.run(["/bin/sh", "-c", command], cwd=workspace, env=attack,
                                    input=event, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, expected, result.stderr)
        self.assertEqual(sorted(p.name for p in marks.iterdir()), [])


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
elif mode == "tamper" or (mode == "tamper_later" and "--resume" in argv):
    directory = Path(os.environ["AGENT_CHECKS_DATED_PHRASING_MODULES"]).parents[2]
    os.chmod(directory, 0o755)
    (directory / "planted").write_text("x")
cfg = os.environ.get("CLAUDE_CONFIG_DIR")
if cfg and "--no-session-persistence" not in argv and (Path(cfg) / "CLAUDE.md").is_file():
    # A guidance arm's receipt (#139), as test_issue_adr0012_delivery's recorder writes it.
    import re
    project = Path(cfg, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(os.getcwd())))
    project.mkdir(parents=True, exist_ok=True)
    with open(project / "s1.jsonl", "a") as fh:
        fh.write(json.dumps({{"type": "attachment", "attachment": {{"type": "instructions",
            "files": [{{"path": str(Path(cfg) / "CLAUDE.md"), "type": "User",
                        "content": (Path(cfg) / "CLAUDE.md").read_text()}}]}}}}) + "\\n")
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
        # The run's own TMPDIR, so what it leaves behind is its own.
        self.tmp = self.root / "tmp"
        self.tmp.mkdir()

    def run_main(self, mode, arm="both", hooks=True, subject="skill", followups=None,
                 pairing="in_place"):
        name = "sample" if subject == "skill" else "guidance-fixture"
        directory = self.root / "evals" / name
        (directory / "seed").mkdir(parents=True, exist_ok=True)
        (directory / "seed" / "README.md").write_text("x\n", encoding="utf-8")
        body = {"prompt": "do it", "model": "claude-test-model", "fleet_hooks": hooks,
                "env": {"REC_LOG": str(self.log), "HOOK_MODE": mode},
                "objective_checks": [{"id": "seed-kept", "description": "d",
                                      "type": "files_unchanged", "paths": ["README.md"]}],
                "context": self.metadata, **({"followups": followups} if followups else {})}
        flags = ["--registry", f"adam-agentskills={self.registry}"]
        if subject == "skill":
            body.update(skill="sample",
                        registry="https://github.com/Adam-S-Daniel/adam-agentskills")
        else:
            body.update(subject="guidance", section="bravo", objective_checks=[])
            flags = ["--guidance", str(self.root / "missing-live-guidance")]
        (directory / "fixture.yaml").write_text(yaml.safe_dump(body), encoding="utf-8")
        env = dict(self.env, SKILLS_EVALS_REGISTRIES=self.registry_env,
                   CLAUDE_CODE_REMOTE_SESSION_ID="session_test", TMPDIR=str(self.tmp))
        repos = [f"--context-repo={k}={v}" for k, v in self.repositories.items()]
        proc = subprocess.run(
            [sys.executable, "harness/run_eval.py", str(directory), *flags,
             "--results-dir", str(self.root / "results"),
             "--timeout", "60", "--no-judge", "--arm", arm, "--pairing", pairing,
             "--timestamp", self.TS, *repos],
            capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=600)
        # Every arm's scratch, its read-only set included, and the plan's
        # read-only markdown-it install are gone once the run ends.
        self.assertEqual(sorted(p.relative_to(self.tmp).as_posix()
                                for p in self.tmp.rglob("*fleet-hooks*")), [])
        return proc

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def summary(self, arm, key="sample"):
        return json.loads((self.root / "results" / key / self.TS / arm / "summary.json")
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

    def test_a_write_in_a_later_turn_fails_the_arm_after_that_turn(self):
        proc = self.run_main("tamper_later", arm="with_skill", followups=["again", "more"])
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        error = self.summary("with_skill")["error"]
        self.assertEqual(error["type"], "agent_wrote_agent_config")
        self.assertIn("follow-up 1 of 2", error["detail"])
        self.assertEqual(len(self.calls()), 2, "no turn runs after the write")

    def test_isolation_and_bare_arms_of_a_hooked_fixture_get_no_hooks(self):
        proc = self.run_main("commit", pairing="isolation")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self.calls()
        self.assertEqual(len(calls), 2)
        for call in calls:
            self.assertEqual(call["env"], {})
            self.assertIsNone(call["hooks"])
            self.assertEqual(call["inside"][0], 0, call)


@unittest.skipUnless(sandbox_available(), "bubblewrap with a network namespace is not available")
class GuidanceEndToEndTests(MainRun):
    """The in-place guidance pair (`full`/`full-minus-section`) is hooked."""

    def test_the_agent_commits_through_the_frozen_runner_inside_its_sandbox(self):
        proc = self.run_main("commit", subject="guidance")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        calls = self.calls()
        self.assertEqual(len(calls), 2)
        for call in calls:
            self.assertIn("agent-checks: .env", call["inside"][1])
            self.assertNotEqual(call["inside"][0], 0, call)
            self.assertEqual(call["outside"][0], 0, call)
            directory = call["env"]["GIT_CONFIG_VALUE_0"].rsplit("/", 1)[0]
            self.assertIn(directory, call["deny_write"])
            self.assertEqual(call["hooks"], fleet_hooks.guard_hooks(directory))
        for arm in ("with_guidance", "without_guidance"):
            self.assertEqual(self.summary(arm, "guidance/bravo")["context"]["fleet_hooks_digest"],
                             self.freeze(guidance_subject=True).digest)

    def test_a_write_into_the_frozen_set_fails_the_arm(self):
        proc = self.run_main("tamper", subject="guidance", arm="with_guidance")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        error = self.summary("with_guidance", "guidance/bravo")["error"]
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
        for value in ("sha256:" + "0" * 64, None):
            with self.subTest(value=value):
                bad = json.loads(path.read_bytes())
                bad["context"]["fleet_hooks_digest"] = value
                with self.assertRaises(ingest.Rejected):
                    ingest.check_summary(bad, path.name, ingest.parse_result_path(
                        path.relative_to(self.root / "results").as_posix()))

    def test_compute_gates_skips_a_present_but_null_digest(self):
        proc = self.run_main("none")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        path = self.root / "results" / "sample" / self.TS / "with_skill" / "summary.json"
        doc = json.loads(path.read_bytes())
        doc["context"]["fleet_hooks_digest"] = None
        path.write_text(json.dumps(doc), encoding="utf-8")
        index = compute_gates.build_index(self.root, self.root / "evals", "99991231T235959Z")
        self.assertEqual(index["skipped"], {"malformed arm summary": 1})
        self.assertEqual([run["role"] for run in index["runs"]], ["without"])

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


class GuidanceRowPoolingTests(unittest.TestCase):
    """compute_gates' guidance rows take the hook digest too (defensive:
    only isolation guidance runs pool today, and they are never hooked).
    Synthetic summaries from test_issue_124's ComputeGuidanceTests."""

    def setUp(self):
        from test_issue_124_guidance_gates import ComputeGuidanceTests
        self.helper = ComputeGuidanceTests("test_flat_runs_of_both_pairs_retire_the_section")
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)

    def index(self):
        return compute_gates.build_index(self.helper.tree, self.helper.evals, "20261231T000000Z")

    def test_hooked_and_unhooked_guidance_rows_never_pool(self):
        digest = "c" * 64
        for r, hooks in ((0, True), (1, False)):
            over = {"context": {"fleet_hooks_digest": digest}} if hooks else {}
            for arm in ("with_guidance_full", "with_guidance_full_minus_section"):
                self.helper.arm(r, arm, {"with_guidance_full": "full"}.get(arm, "full-minus-section"),
                                80, 7.0, **over)
        index = self.index()
        self.assertEqual(index["skipped"], {})
        runs = {(run["fleet_hooks_digest"] is not None, run["role"]): run
                for run in index["guidance_runs"]}
        rest = self.helper.digests["rest"]
        for role in ("with", "without"):
            plain, hooked = runs[(False, role)], runs[(True, role)]
            self.assertEqual((plain["pair_key"], plain["arm_context_digest"]), (rest, rest))
            self.assertEqual((hooked["pair_key"], hooked["arm_context_digest"]),
                             (f"{rest}:{digest}", f"{rest}:{digest}"))
        self.assertEqual(gates._joint_context([runs[(True, "with")]], [runs[(False, "without")]],
                                              ["model-a"]), (None, None, None))
        self.assertEqual(gates._joint_context([runs[(True, "with")]], [runs[(True, "without")]],
                                              ["model-a"])[2], f"{rest}:{digest}")

    def test_a_present_but_null_digest_is_malformed(self):
        self.helper.arm(0, "with_guidance_full", "full", 80, 7.0,
                        context={"fleet_hooks_digest": None})
        self.assertEqual(self.index()["skipped"], {"no guidance pooling key": 1})


if __name__ == "__main__":
    unittest.main()


class HostGuardTests(HookBase):
    """Host conditions a hooked plan refuses before any arm is paid for (#605)."""

    def managed(self, content, name="managed-settings.json"):
        path = Path(self.enterContext(tempfile.TemporaryDirectory())) / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_managed_hooks_off_is_refused_naming_file_and_key(self):
        for key, value in (("disableAllHooks", True), ("allowManagedHooksOnly", True),
                           ("disableAllHooks", "yes")):
            path = self.managed(json.dumps({key: value}))
            reason = run_eval.managed_hooks_refusal(files=[path], dropins=[])
            self.assertIn(str(path), reason)
            self.assertIn(key, reason)
            self.assertNotIn("yes", reason)

    def test_managed_hooks_left_on_missing_files_and_other_keys_are_fine(self):
        path = self.managed(json.dumps({"disableAllHooks": False, "model": "x"}))
        missing = path.parent / "absent.json"
        self.assertIsNone(run_eval.managed_hooks_refusal(files=[path, missing], dropins=[]))

    def test_an_unreadable_or_non_object_managed_file_is_a_refusal(self):
        for content in ("{not json", "[]"):
            path = self.managed(content)
            self.assertIn(str(path), run_eval.managed_hooks_refusal(files=[path], dropins=[]))

    def test_a_dropin_is_read_too(self):
        path = self.managed(json.dumps({"allowManagedHooksOnly": True}), "10-x.json")
        self.assertIn("allowManagedHooksOnly",
                      run_eval.managed_hooks_refusal(files=[], dropins=[path.parent]))

    def test_plan_refuses_managed_hooks_off_only_for_a_hooked_fixture(self):
        path = self.managed(json.dumps({"disableAllHooks": True}))
        with mock.patch.object(run_eval, "MANAGED_SETTINGS_FILES", (path,)), \
                mock.patch.object(run_eval, "MANAGED_SETTINGS_DROPINS", ()):
            with self.assertRaises(run_eval.delivery.DeliveryError) as raised:
                self.plan()
            self.assertEqual(raised.exception.code, "fleet_hooks_managed_hooks_off")
            self.assertNotIn("fleet_hooks", self.plan(hooks=False))

    def test_plan_refuses_a_host_without_the_guards_python(self):
        with mock.patch.object(fleet_hooks, "GUARD_PYTHON_PATHS", ("/nonexistent/python3",)):
            with self.assertRaises(run_eval.delivery.DeliveryError) as raised:
                self.plan()
            self.assertEqual(raised.exception.code, "fleet_hooks_no_python")
            self.assertNotIn("fleet_hooks", self.plan(hooks=False))

    def test_plan_refuses_a_host_without_a_netns_id(self):
        with mock.patch.object(fleet_hooks.os, "readlink", side_effect=OSError("no")):
            with self.assertRaises(context.ContextError) as raised:
                self.plan()
            self.assertEqual(raised.exception.code, "fleet_hooks_no_receipt")


class HookDigestGroupingTests(unittest.TestCase):
    """The bet prior's history cells and regression windows start afresh when
    the hook digest moves, though the fixture digest did not (#605)."""

    def runs(self, hooks_digest):
        from test_issue_69_regression import run
        out = []
        for day, passed in enumerate((4, 3), start=1):
            record = run("a", "with", day, passed)
            if hooks_digest:
                record["fleet_hooks_digest"] = hooks_digest
            out.append(record)
        return out

    def test_the_bet_prior_history_groups_by_hook_digest(self):
        # The variance priors are gone (2026-11-03); the learned bet prior's
        # within-cell variance is what #605 now applies to.
        from test_issue_69_regression import run

        def fire(day, passed, hooks):
            pair = [run("a", role, day, p) for role, p in (("with", passed), ("without", 2))]
            for record in pair:
                if hooks:
                    record["fleet_hooks_digest"] = hooks
            return pair
        together = gates.paired_history(fire(1, 4, None) + fire(2, 3, None))
        self.assertEqual(len({p["cell"] for p in together}), 1)
        apart = gates.paired_history(fire(1, 4, None) + fire(2, 3, "h" * 64))
        self.assertEqual(len(apart), 2)
        self.assertEqual(len({p["cell"] for p in apart}), 2)

    def test_regression_keeps_the_newest_runs_fixture_and_hook_digest(self):
        from test_issue_69_regression import POLICY, series
        old = series("a", [4, 4, 4], first=1)
        new = series("a", [2, 2, 2], first=4)
        for record in new:
            record["fleet_hooks_digest"] = "h" * 64
        row = regression._row("skill", "a", None, "model", None, old + new,
                              POLICY)
        self.assertEqual(len(row["windows"]["previous"]) + len(row["windows"]["current"]), 3)
        self.assertEqual(row["verdict"], "insufficient")
