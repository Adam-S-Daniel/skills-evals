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

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))

import context  # noqa: E402
import fleet_hooks  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
