"""The first real-work fixtures under evals/real-work/ (the fixtures DESIGN's
"smallest next PR 4"): each is red on its seed and green with its pull
request's fix applied, scored by its pull request's own hidden tests.

Offline: the scorer's network probe is mocked off and nothing is fetched.
The checkers need each seed's npm dependencies installed from the seed's own
lockfile first (`npm ci` in the directory each fixture's `deps:` names; CI's
test job does it), exactly as the browser-testing fixture's tests need theirs.
"""

from __future__ import annotations

import contextlib
import difflib
import hashlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "harness"))
import answer_leak  # noqa: E402
import run_eval  # noqa: E402
import seed_prep  # noqa: E402

REAL_WORK = REPO / "evals" / "real-work"

# Each checker file's git blob id in its pull request's merge commit, read with
# `git ls-tree <merge> <path>`: the overlay is that file, byte for byte.
CHECKER_BLOBS = {
    "cms-platform-693": {
        "e2e/live-url-derive-routable.test.js": "274da0153db0a64b05f25e5ac5e42753c7295a2c"},
    "cms-platform-221": {
        "e2e/check-platform-pin-consistency.test.js": "e0235030215025986b023fdf56045ab4056a1d1b"},
    "_agent-guidance-196": {
        "test/test-dependabot-config-health.js": "76c73b457533ae2b0a7d9d544804468f07b91920"},
}
# Paths a seed must not carry: the agent context the guidance and skill A/B
# withholds, and the subject under evaluation itself (Adam, 2026-10-06: "Strip
# subject + trim").
EVALUATED_PATHS = (".claude", "skills.lock", "agents-md", "skills", ".claude-plugin")
# Files over this size were trimmed unless something needs them: the lockfile
# `deps:` installs from, and AGENTS.md's kept repository-specific section.
TRIM_BYTES = 100 * 1024
KEPT_LARGE = {"package-lock.json", "AGENTS.md"}


def blob_id(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def seed_files(seed: Path):
    for directory, dirnames, filenames in os.walk(seed):
        dirnames[:] = [d for d in dirnames if d != "node_modules"]
        for name in filenames:
            yield Path(directory) / name


class RealWorkFixtureTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("scorers.commands._network_prefix", return_value=[])
        patcher.start()
        self.addCleanup(patcher.stop)

    def fixtures(self):
        names = sorted(p.name for p in REAL_WORK.iterdir() if (p / "fixture.yaml").is_file())
        self.assertEqual(names, sorted(CHECKER_BLOBS))
        for name in names:
            yield name, REAL_WORK / name, run_eval.load_fixture(REAL_WORK / name)

    def test_each_fixture_loads_as_a_subject_agnostic_draft(self):
        for name, directory, fixture in self.fixtures():
            with self.subTest(fixture=name):
                path = directory / "fixture.yaml"
                self.assertEqual(fixture["subject"], "any")
                self.assertIs(fixture["draft"], True)
                self.assertIs(fixture["strip_agent_context"], True)
                self.assertNotIn("skill", fixture)
                self.assertNotIn("section", fixture)
                run_eval.apply_runtime_subject(fixture, None, None, "objective-only", path)
                answer_leak.validate_fixture(fixture, path)
                seed_prep.validate_fixture(fixture, directory)
                [check] = fixture["objective_checks"]
                self.assertEqual((check["type"], check["overlay"]), ("repo_tests", "checker"))

    def test_each_checker_is_the_pull_requests_own_test_file(self):
        for name, directory, _ in self.fixtures():
            with self.subTest(fixture=name):
                checker = directory / "checker"
                found = {p.relative_to(checker).as_posix(): blob_id(p)
                         for p in checker.rglob("*") if p.is_file()}
                self.assertEqual(found, CHECKER_BLOBS[name])

    def test_each_seed_is_stripped_and_trimmed(self):
        for name, directory, _ in self.fixtures():
            seed = directory / "seed"
            with self.subTest(fixture=name):
                self.assertEqual(seed_prep.agent_context_violations(seed), [])
                for evaluated in EVALUATED_PATHS:
                    self.assertFalse(os.path.lexists(seed / evaluated), evaluated)
                large = [p.relative_to(seed).as_posix() for p in seed_files(seed)
                         if p.stat().st_size > TRIM_BYTES and p.name not in KEPT_LARGE]
                self.assertEqual(large, [])

    def test_ci_installs_exactly_the_fixtures_dependencies(self):
        workflow = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml")
                                  .read_text(encoding="utf-8"))
        [step] = [s for s in workflow["jobs"]["test"]["steps"]
                  if s.get("name") == "Install real-work fixture dependencies"]
        self.assertEqual(step["working-directory"], "skills-evals/evals/real-work")
        self.assertEqual(step["if"], "steps.salient.outputs.run == 'true'")
        [loop] = [line.strip() for line in step["run"].splitlines()
                  if line.strip().startswith("for dir in ")]
        words = shlex.split(loop.removesuffix("; do"))
        installed = words[3:]
        wanted = sorted(f"{name}/seed" + ("" if entry["dir"] == "." else f"/{entry['dir']}")
                        for name, _, fixture in self.fixtures()
                        for entry in fixture["deps"])
        self.assertEqual(installed, wanted)
        self.assertIn("npm ci --ignore-scripts --no-audit --no-fund", step["run"])

    def test_cms_seeds_keep_only_the_checkers_own_spec(self):
        # Adam, 2026-10-06: "Trim other e2e specs". The e2e helpers and
        # configs stay; of the specs, only the one the checker overlays.
        for name, directory, _ in self.fixtures():
            e2e = directory / "seed" / "e2e"
            if not e2e.is_dir():
                continue
            with self.subTest(fixture=name):
                specs = sorted(p.name for p in e2e.iterdir()
                               if p.name.endswith((".spec.js", ".test.js", ".spec.js-snapshots")))
                self.assertEqual(specs, [Path(path).name for path in CHECKER_BLOBS[name]])

    def test_no_task_text_quotes_the_merged_diff(self):
        # The answer is every line the pull request added: its fix
        # (solution.patch) and its test file's additions over the seed's copy.
        # Runs inside a declared interface string, or already in the issue
        # before the fix began (issue_before_fix:), are not leaks.
        for name, directory, fixture in self.fixtures():
            with self.subTest(fixture=name):
                added = answer_leak.added_lines(
                    (directory / "solution.patch").read_text(encoding="utf-8"))
                for rel in CHECKER_BLOBS[name]:
                    before = directory / "seed" / rel
                    old = (before.read_text(encoding="utf-8").splitlines()
                           if before.exists() else [])
                    new = (directory / "checker" / rel).read_text(encoding="utf-8").splitlines()
                    added += [line[1:] for line in difflib.unified_diff(old, new, lineterm="", n=0)
                              if line.startswith("+") and not line.startswith("+++")]
                self.assertGreater(len(added), 10)
                preexisting = answer_leak.preexisting_text(fixture, directory)
                self.assertTrue(preexisting.strip(), "each fixture snapshots its issue")
                self.assertEqual(answer_leak.leaked_runs(
                    fixture["prompt"], "\n".join(added),
                    fixture.get("interface_strings", ()), preexisting), [])

    def workspace(self, directory: Path, fixture: dict, fixed: bool) -> Path:
        """The seed as the agent would get it, its dependencies already
        installed (symlinked from the seed), and for `fixed` the pull
        request's own fix applied."""
        seed = directory / "seed"
        for entry in fixture["deps"]:
            modules = seed / entry["dir"] / "node_modules"
            self.assertTrue(modules.is_dir(),
                            f"Install {modules.parent} with npm ci before running the suite")
        owned = tempfile.TemporaryDirectory(prefix="real-work-")
        self.addCleanup(owned.cleanup)
        workspace = Path(owned.name) / "ws"
        shutil.copytree(seed, workspace, ignore=shutil.ignore_patterns("node_modules"))
        for entry in fixture["deps"]:
            (workspace / entry["dir"] / "node_modules").symlink_to(
                seed / entry["dir"] / "node_modules", target_is_directory=True)
        seed_prep.prepare_seed(workspace, fixture)
        self.assertIsNone(seed_prep.seed_guard(workspace, fixture))
        if fixed:
            subprocess.run(["git", "apply", "--whitespace=nowarn",
                            str(directory / "solution.patch")],
                           cwd=workspace, check=True, timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return workspace

    def objective_only(self, directory: Path, workspace: Path):
        out = io.StringIO()
        argv = ["run_eval.py", str(directory), "--arm", "objective-only",
                "--workspace", str(workspace)]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
            code = run_eval.main()
        return code, out.getvalue()

    def test_each_fixture_is_red_on_its_seed_and_green_with_the_fix(self):
        for name, directory, fixture in self.fixtures():
            [check] = fixture["objective_checks"]
            f2p = len(check["fail_to_pass"])
            p2p = len(check.get("pass_to_pass") or [])
            for fixed, code_wanted, detail in (
                    (False, 1, f"fail_to_pass=0/{f2p} pass_to_pass={p2p}/{p2p}"),
                    (True, 0, f"fail_to_pass={f2p}/{f2p} pass_to_pass={p2p}/{p2p}")):
                with self.subTest(fixture=name, fixed=fixed):
                    code, out = self.objective_only(
                        directory, self.workspace(directory, fixture, fixed))
                    self.assertEqual(code, code_wanted, out)
                    report = json.loads(out)
                    self.assertEqual(report["subject"], "any")
                    self.assertIn(detail, report["checks"][0]["detail"])


if __name__ == "__main__":
    unittest.main()
