"""Offline consumer-bump fixture proofs for issue 93."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "evals/platform-release-and-bump"
SEED = EVAL / "seed"
TAG_SHA = "e76901db4beaa3d2e4ad88b7f554cfe89fffc20b"
sys.path.insert(0, str(ROOT / "harness"))
from scorers.objective import run_checks  # noqa: E402
from run_eval import load_fixture, select_models, check_fixture_dir  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts"))
from eval_coverage import count_fixtures  # noqa: E402


def bumped(workspace: Path) -> None:
    for relative in ("platform.lock", "Gemfile", "Gemfile.lock"):
        path = workspace / relative
        path.write_text(path.read_text().replace("v0.1.103", "v0.1.104"), encoding="utf-8")
    lock = workspace / "Gemfile.lock"
    lock.write_text(lock.read_text().replace("1" * 40, TAG_SHA), encoding="utf-8")
    for path in (workspace / ".github/workflows").glob("*.yml"):
        path.write_text(path.read_text().replace("v0.1.103", "v0.1.104"), encoding="utf-8")
    action = workspace / ".github/actions/local/action.yml"
    action.write_text(action.read_text().replace("v0.1.103", "v0.1.104"), encoding="utf-8")
    (workspace / ".github/workflows/old-preview-cleanup.yml").unlink()
    canonical = workspace / ".cms-platform/examples/site/.github/workflows/cms-delete-published-preview.yml"
    new_caller = workspace / ".github/workflows/cms-delete-published-preview.yml"
    new_caller.write_text(canonical.read_text().replace("v0.1.103", "v0.1.104"), encoding="utf-8")


@unittest.skipUnless(shutil.which("node"), "Node is required for the fixed platform verifier")
class ConsumerBumpFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = yaml.safe_load((EVAL / "fixture.yaml").read_text())

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="issue-93-")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "site"
        # The copy contains only fixture files, no inherited Git metadata or remote.
        shutil.copytree(SEED, self.workspace)

    def score(self) -> dict[str, bool]:
        result = run_checks(self.fixture, str(self.workspace), str(SEED), "Consumer bumped; verifier exit 0.")
        return {check["id"]: check["passed"] for check in result}

    def assert_failed(self, *ids: str) -> None:
        score = self.score()
        self.assertEqual({name for name, passed in score.items() if not passed}, set(ids), score)

    def test_fixture_registration_and_tag_provenance(self) -> None:
        self.assertEqual(self.fixture["skill"], "platform-release-and-bump")
        self.assertEqual(self.fixture["registry"], "https://github.com/Adam-S-Daniel/cms-platform")
        self.assertEqual(set(self.fixture["arms"]), {"with_skill", "without_skill"})
        self.assertEqual((SEED / "PLATFORM_REF").read_text(), f"tag: v0.1.104\ncommit: {TAG_SHA}\n")
        self.assertEqual(hashlib.sha256((SEED / ".cms-platform/scripts/verify-consumer-pins.sh").read_bytes()).hexdigest(),
                         "3e49a4659837d64fb9cd7ce102ed394e55098d8dc39d41e99707da55f1883a41")
        self.assertEqual(len(list((SEED / ".cms-platform/examples/site/.github/workflows").glob("*.yml"))), 12)
        self.assertEqual(load_fixture(EVAL), self.fixture)
        check_fixture_dir(EVAL)
        self.assertEqual(count_fixtures(EVAL, {"cms-platform": {"name": "cms-platform",
                         "url": self.fixture["registry"]}}),
                         {("cms-platform", "platform-release-and-bump"): 1})
        selected, judge, problem = select_models(self.fixture, argparse.Namespace(
            model=None, no_judge=False, roster=ROOT / "evals/roster.yml"))
        self.assertIsNone(problem)
        self.assertEqual(selected, self.fixture["model"])
        self.assertIsInstance(judge, str)
        self.assertNotIn("model", self.fixture["judge"])
        for pattern, count, expected in (
            (".cms-platform/scripts/*", 3, "b67a3a5ba04abd181acf83b8b47376cd17efc0659de62cb06264e18ffdddfa15"),
            (".cms-platform/examples/site/.github/workflows/*.yml", 12, "7d329ce631494e59fec5411144b63d46dc98d167ddc29646c94bf39a6b8f9448"),
            (".cms-platform/e2e/node_modules/yaml/dist/**/*.js", 74, "f534ad9c5d4639c8ec3aca1b27ff95fdf9efc1ed9b9eac039069333538e7f060"),
        ):
            files = sorted(path for path in SEED.glob(pattern) if path.is_file())
            self.assertEqual(len(files), count)
            manifest = "".join(path.relative_to(SEED).as_posix() + " " +
                               hashlib.sha256(path.read_bytes()).hexdigest() + "\n" for path in files)
            self.assertEqual(hashlib.sha256(manifest.encode()).hexdigest(), expected)

    def test_pristine_fails_every_behavior_check_and_passes_restraint(self) -> None:
        self.assert_failed("canonical-verifier", "refs-on-release", "resolved-revision", "added-caller", "retired-caller")

    def test_complete_bump_passes_all_checks(self) -> None:
        bumped(self.workspace)
        self.assertTrue(all(self.score().values()))

    def test_plausible_pin_only_bump_fails_set_parity(self) -> None:
        bumped(self.workspace)
        (self.workspace / ".github/workflows/cms-delete-published-preview.yml").unlink()
        self.assert_failed("canonical-verifier", "refs-on-release", "added-caller")

    def test_each_behavior_check_has_a_negative_control(self) -> None:
        bumped(self.workspace)
        mutations = {
            "canonical-verifier": lambda: (self.workspace / ".github/workflows/deploy-preview.yml").write_text(
                (self.workspace / ".github/workflows/deploy-preview.yml").read_text().replace("AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}", "AWS_ROLE_ARN: ${{ secrets.OTHER_ROLE_ARN }}")),
            "refs-on-release": lambda: (self.workspace / ".github/actions/local/action.yml").write_text(
                (self.workspace / ".github/actions/local/action.yml").read_text().replace("@v0.1.104", "@v0.1.103")),
            "resolved-revision": lambda: (self.workspace / "Gemfile.lock").write_text(
                (self.workspace / "Gemfile.lock").read_text().replace(TAG_SHA, "1" * 40)),
            "added-caller": lambda: (self.workspace / ".github/workflows/cms-delete-published-preview.yml").unlink(),
            "retired-caller": lambda: (self.workspace / ".github/workflows/old-preview-cleanup.yml").write_text("name: obsolete\n"),
        }
        failures = {
            "canonical-verifier": {"canonical-verifier"},
            "refs-on-release": {"refs-on-release"},
            "resolved-revision": {"resolved-revision"},
            "added-caller": {"canonical-verifier", "refs-on-release", "added-caller"},
            "retired-caller": {"canonical-verifier", "retired-caller"},
        }
        for expected, mutate in mutations.items():
            with self.subTest(check=expected):
                mutate()
                score = self.score()
                self.assertEqual({name for name, passed in score.items() if not passed}, failures[expected], score)
                # Restore from a freshly built good workspace; exact failing set
                # overlaps where the mandatory verifier sees the same defect.
                shutil.rmtree(self.workspace)
                shutil.copytree(SEED, self.workspace)
                bumped(self.workspace)
                self.assertTrue(all(self.score().values()))

    def test_instrument_and_restraint_mutations(self) -> None:
        bumped(self.workspace)
        cases = (
            ("no-pin-comments", ".github/workflows/deploy-preview.yml", lambda t: t.replace("@v0.1.104", "@v0.1.104 # v0.1.104", 1)),
            ("no-gh-write", ".gh-invocations.log", lambda t: t + '--- invocation (class=write key=workflow-run exit=1 argv=["workflow","run"])\n'),
            ("verifier-digest", ".cms-platform/scripts/verify-consumer-pins.sh", lambda t: t + "\n# tampered\n"),
            ("instrument-unchanged", "PLATFORM_REF", lambda t: t + "other: changed\n"),
        )
        for expected, relative, change in cases:
            with self.subTest(check=expected):
                path = self.workspace / relative
                before = path.read_text()
                path.write_text(change(before))
                score = self.score()
                expected_failures = ({"verifier-digest", "instrument-unchanged"}
                                     if expected == "verifier-digest" else {expected})
                self.assertEqual({name for name, passed in score.items() if not passed}, expected_failures, score)
                path.write_text(before)
                self.assertTrue(all(self.score().values()))

    def test_lock_revision_belongs_to_the_platform_source_block(self) -> None:
        bumped(self.workspace)
        lock = self.workspace / "Gemfile.lock"
        text = lock.read_text()
        lock.write_text(text.replace(TAG_SHA, "1" * 40) +
                        "\nGIT\n  remote: https://github.com/example-org/other-gem\n"
                        f"  revision: {TAG_SHA}\n  tag: v0.1.104\n")
        self.assert_failed("resolved-revision")
        lock.write_text(text.replace("  revision: " + TAG_SHA + "\n  tag: v0.1.104",
                                     "    tag: v0.1.104\n  revision: " + TAG_SHA))
        self.assertTrue(all(self.score().values()))
        lock.write_text(text.replace("remote: https://github.com/Adam-S-Daniel/cms-platform",
                                     "remote: https://github.com/Adam-S-Daniel/cms-platform.git"))
        self.assertTrue(all(self.score().values()))
        lock.write_text(text + "\nGIT\n  remote: https://github.com/Adam-S-Daniel/cms-platform\n"
                        "  revision: " + "1" * 40 + "\n  tag: v0.1.104\n")
        self.assert_failed("resolved-revision")
        lock.write_text(text.replace("  revision: " + TAG_SHA + "\n", ""))
        self.assert_failed("resolved-revision")

    def test_missing_gem_file_is_detected_even_when_verifier_allows_it(self) -> None:
        bumped(self.workspace)
        (self.workspace / "Gemfile").unlink()
        self.assert_failed("gem-files-present")

    def test_missing_or_modified_instrument_fails_closed(self) -> None:
        bumped(self.workspace)
        for relative in (".cms-platform/scripts/stale-platform-refs.js",
                         ".gh/replay/release-view-v0.1.104.json"):
            with self.subTest(path=relative):
                path = self.workspace / relative
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                self.assertFalse(self.score()["instrument-unchanged"])
                path.unlink()
                self.assertFalse(self.score()["instrument-unchanged"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(original)
                self.assertTrue(all(self.score().values()))

    def test_malformed_consumer_yaml_fails_the_verifier(self) -> None:
        bumped(self.workspace)
        caller = self.workspace / ".github/workflows/deploy-preview.yml"
        caller.write_text(caller.read_text() + "\nnot: [closed\n")
        self.assertFalse(self.score()["canonical-verifier"])

    def test_release_reads_use_the_local_command_replay(self) -> None:
        anchor = self.workspace / ".git/workspace-root"
        anchor.parent.mkdir()
        anchor.write_text(str(self.workspace) + "\n")
        environment = {
            "PATH": os.environ["PATH"],
            "HOME": self.temp.name,
            "GH_REPLAY_DIR": str(self.workspace / ".gh/replay"),
            "GH_REPO": "example-org/example-site",
            "GH_TOKEN": "",
            "GITHUB_TOKEN": "",
        }
        commands = (
            ("release", "view", "v0.1.104"),
            ("api", "repos/Adam-S-Daniel/cms-platform/git/ref/tags/v0.1.104"),
            ("api", "repos/Adam-S-Daniel/cms-platform/git/refs/tags/v0.1.104"),
        )
        for command in commands:
            result = subprocess.run([str(self.workspace / "bin/gh"), *command],
                                    cwd=self.workspace, env=environment,
                                    input="", capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(TAG_SHA, result.stdout)
        log = (self.workspace / ".gh-invocations.log").read_text()
        self.assertEqual(log.count("class=read"), 3)
        self.assertNotIn("class=write", log)
        self.assertTrue(self.score()["no-gh-write"])

    def test_parser_runtime_and_payload_additions_fail_closed(self) -> None:
        bumped(self.workspace)
        paths = (
            ".cms-platform/e2e/node_modules/yaml/dist/schema/core/extra.js",
            ".cms-platform/scripts/node_modules/yaml/index.js",
            ".cms-platform/examples/site/.github/workflows/extra.yml",
            ".gh/replay/api/repos/Adam-S-Daniel/cms-platform/git/ref/tags/other.json",
        )
        for relative in paths:
            with self.subTest(path=relative):
                path = self.workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("module.exports = {}\n")
                self.assertFalse(self.score()["instrument-unchanged"])
                path.unlink()
                if "scripts/node_modules" in relative:
                    shutil.rmtree(self.workspace / ".cms-platform/scripts/node_modules")
                self.assertTrue(all(self.score().values()))


if __name__ == "__main__":
    unittest.main()
