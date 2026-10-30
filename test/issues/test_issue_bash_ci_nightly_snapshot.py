#!/usr/bin/env python3
"""evals/review-bash-ci-reliability/nightly-snapshot (SKILL.md items 5, 6, 7).

The seed's scripts/publish-snapshot.sh commits a rebuilt snapshot in CI. It
leaves commit signing to the runner's global git config, hides a missing
dasel behind `|| echo unknown`, and captures `grep -c` under `set -euo
pipefail`, which exits 1 on a night with nothing to commit. The behavior and
restraint checks run the final script through `repo_tests` in a throwaway git
repository the hidden probe builds. Written as the unseen fixture that
adam-agentskills#87 (an edit to items 5, 6 and 7) is re-checked on.

What is pinned here:

  * the pristine seed FAILS the three behavior checks and PASSES every
    restraint check;
  * a hand-written good fix passes every check, and each partial or wrong
    fix fails the checks it should;
  * the fixture's shape: no model pin, the shared context block, correctness
    weighted above restraint, line-anchored patterns, a probe the seed does
    not carry.

Scoring runs `objective.run_checks` in process with the bubblewrap sandbox
replaced by a direct run, as test_issue_bash_ci_drift_report_capture.py does,
so these tests need bash, git and the coreutils but no sandbox. One test
scores the pristine seed through `run_eval.py` and the real sandbox, and skips
where the sandbox cannot start.
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

REPO = Path(__file__).resolve().parent.parent.parent
HARNESS = REPO / "harness"
SKILL_DIR = REPO / "evals" / "review-bash-ci-reliability"
FIXTURE_DIR = SKILL_DIR / "nightly-snapshot"
SEED = FIXTURE_DIR / "seed"
SCRIPT = Path("scripts") / "publish-snapshot.sh"

sys.path.insert(0, str(HARNESS))
import run_eval  # noqa: E402
from scorers import commands, objective  # noqa: E402

# Every check in fixture order, with what the untouched seed scores.
EXPECTED_PRISTINE = {
    "workflow-yaml-parses": True,
    "workflow-file-present": True,
    "signing-on-runner": False,
    "no-change-night": False,
    "missing-tool-not-silent": False,
    "new-data-still-committed": True,
    "build-failure-still-fails": True,
    "data-untouched": True,
}
BEHAVIOR = {k for k, v in EXPECTED_PRISTINE.items() if not v}

SEED_VERSION = ("version=$(dasel -f manifest.toml '.package.version' 2>/dev/null "
                "|| echo unknown)\n")
GOOD_VERSION = ('command -v dasel >/dev/null || { echo "ERROR: dasel is required '
                'but not installed" >&2; exit 1; }\n'
                "version=$(dasel -f manifest.toml '.package.version')\n")
SEED_EMAIL = 'git config user.email "snapshot-bot@example.com"\n'
GOOD_EMAIL = SEED_EMAIL + "git config commit.gpgsign false\n"
SEED_CHANGED = "changed=$(git status --porcelain -- snapshot/ | grep -c .)\n"
GOOD_CHANGED = "changed=$(git status --porcelain -- snapshot/ | wc -l)\n"

TOOLS = ("bash", "git", "grep", "sed", "sort", "tail", "cp", "cat", "rm", "mkdir",
         "mktemp", "tr", "head", "wc")
HAVE_TOOLS = all(any(os.access(f"{d}/{t}", os.X_OK) for d in ("/usr/bin", "/bin"))
                 for t in TOOLS)
needs_tools = unittest.skipUnless(
    HAVE_TOOLS, "a tool the probe runs is not at /usr/bin or /bin")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError(f"{path.name}: expected one {old!r}, found {text.count(old)}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def sandbox_starts() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        _, detail = commands.command_succeeds(tmp, [], argv=["bash", "-c", "true"])
    return not detail.startswith("scorer_sandbox_unavailable")


class NightlySnapshot(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="bash-ci-snapshot-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.fixture = run_eval.load_fixture(FIXTURE_DIR)

    def ws(self) -> Path:
        ws = self.tmp / f"ws-{len(list(self.tmp.iterdir()))}"
        shutil.copytree(SEED, ws)
        return ws

    def fixed(self, *, version=True, signing=True, changed=True) -> Path:
        ws = self.ws()
        if version:
            replace_once(ws / SCRIPT, SEED_VERSION, GOOD_VERSION)
        if signing:
            replace_once(ws / SCRIPT, SEED_EMAIL, GOOD_EMAIL)
        if changed:
            replace_once(ws / SCRIPT, SEED_CHANGED, GOOD_CHANGED)
        return ws

    def score(self, ws: Path) -> dict[str, bool]:
        with mock.patch.object(commands, "_sandbox_prefix", return_value=([], "unavailable")), \
                mock.patch.object(commands, "_run_sandboxed",
                                  side_effect=lambda prefix, *a: commands._run_command(*a)):
            rows = objective.run_checks(self.fixture, str(ws), str(SEED))
        return {row["id"]: row["passed"] for row in rows}

    def failed(self, ws: Path) -> set[str]:
        return {k for k, v in self.score(ws).items() if not v}

    # ---- the pristine seed and the good fix ----------------------------------

    @needs_tools
    def test_pristine_seed_fails_behavior_and_passes_restraint(self):
        results = self.score(self.ws())
        self.assertEqual(list(results), list(EXPECTED_PRISTINE))
        self.assertEqual(results, EXPECTED_PRISTINE)

    @needs_tools
    def test_good_fix_passes_every_check(self):
        self.assertEqual(self.failed(self.fixed()), set())

    @needs_tools
    def test_reading_the_version_with_plain_bash_also_passes(self):
        ws = self.fixed(version=False)
        replace_once(ws / SCRIPT, SEED_VERSION,
                     "version=$(sed -n 's/^version = \"\\(.*\\)\"$/\\1/p' manifest.toml)\n"
                     '[[ -n "$version" ]] || { echo "ERROR: no version" >&2; exit 1; }\n')
        self.assertEqual(self.failed(ws), set())

    @needs_tools
    def test_signing_disabled_per_commit_also_passes(self):
        ws = self.fixed(signing=False)
        replace_once(ws / SCRIPT, 'git commit -q -m', 'git -c commit.gpgsign=false commit -q -m')
        self.assertEqual(self.failed(ws), set())

    # ---- partial and wrong fixes ---------------------------------------------

    @needs_tools
    def test_each_unfixed_item_fails_its_own_check(self):
        cases = {"version": "missing-tool-not-silent", "signing": "signing-on-runner",
                 "changed": "no-change-night"}
        for left, check in cases.items():
            with self.subTest(left_unfixed=left):
                self.assertEqual(self.failed(self.fixed(**{left: False})), {check})

    @needs_tools
    def test_installing_dasel_but_keeping_the_fallback_fails(self):
        # The workflow may install the tool, but the `|| echo unknown` still
        # turns its absence into a green `snapshot unknown`.
        ws = self.fixed(version=False)
        self.assertEqual(self.failed(ws), {"missing-tool-not-silent"})

    @needs_tools
    def test_swallowing_the_build_failure_fails_restraint(self):
        ws = self.fixed()
        replace_once(ws / SCRIPT, "bash scripts/build-snapshot.sh\n",
                     "bash scripts/build-snapshot.sh || true\n")
        self.assertEqual(self.failed(ws), {"build-failure-still-fails"})

    @needs_tools
    def test_dropping_the_push_fails_restraint(self):
        ws = self.fixed()
        replace_once(ws / SCRIPT, "git push -q origin HEAD\n", "")
        # The missing-tool case fails before committing, so it still passes.
        self.assertEqual(self.failed(ws), {"signing-on-runner", "new-data-still-committed"})

    @needs_tools
    def test_editing_the_data_fails_restraint(self):
        ws = self.fixed()
        with (ws / "data" / "east.csv").open("a", encoding="utf-8") as fh:
            fh.write("east,2026-10-09,1\n")
        # The committed snapshot no longer matches the data, so a quiet night
        # has something to commit too.
        self.assertEqual(self.failed(ws), {"data-untouched", "no-change-night"})

    @needs_tools
    def test_deleting_the_workflow_fails_its_presence_check(self):
        ws = self.fixed()
        (ws / ".github" / "workflows" / "snapshot.yml").unlink()
        self.assertEqual(self.failed(ws), {"workflow-file-present"})

    # ---- the real sandbox, where it can start ---------------------------------

    def test_pristine_seed_through_run_eval_and_the_real_sandbox(self):
        if not sandbox_starts():
            self.skipTest("the scorer sandbox cannot start on this machine")
        home = self.tmp / "home"
        home.mkdir()
        env = {"PATH": os.defpath, "HOME": str(home), "TMPDIR": str(self.tmp),
               "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
        proc = subprocess.run(
            [sys.executable, str(HARNESS / "run_eval.py"), str(FIXTURE_DIR),
             "--arm", "objective-only", "--results-dir", str(self.tmp / "results")],
            capture_output=True, text=True, env=env, cwd=str(REPO), timeout=300)
        payload = json.loads(proc.stdout)
        self.assertEqual({c["id"]: c["passed"] for c in payload["checks"]},
                         EXPECTED_PRISTINE)
        self.assertEqual(proc.returncode, 1)

    # ---- the fixture's shape ---------------------------------------------------

    def test_contract(self):
        fx = self.fixture
        self.assertEqual(fx["skill"], "review-bash-ci-reliability")
        self.assertEqual(fx["registry"], "https://github.com/Adam-S-Daniel/adam-agentskills")
        self.assertNotIn("model", fx)
        self.assertNotIn("model", fx["judge"])
        self.assertNotIn("draft", fx)
        weights = fx["judge"]["weights"]
        self.assertAlmostEqual(sum(weights.values()), 1.0)
        self.assertGreater(weights["correctness"], weights["restraint"])
        self.assertEqual({k: v["install"] for k, v in fx["arms"].items()},
                         {"with_skill": "copy", "without_skill": "none"})
        sibling = run_eval.load_fixture(SKILL_DIR / "release-pipeline")
        self.assertEqual(fx["context"], sibling["context"])
        self.assertEqual(fx["prompt"], sibling["prompt"])
        self.assertEqual([c["id"] for c in fx["objective_checks"]], list(EXPECTED_PRISTINE))

    def test_rubric_caps_on_every_behavior_check(self):
        rubric = " ".join(self.fixture["judge_rubric"].split())
        for check_id in BEHAVIOR:
            self.assertIn(check_id, rubric)

    def test_file_patterns_are_line_anchored_and_need_their_file(self):
        for check in self.fixture["objective_checks"]:
            if check["type"] != "file_matches":
                continue
            self.assertIs(check.get("require_present"), True, check["id"])
            for pattern in check.get("must_match", []) + check.get("must_not_match", []):
                self.assertTrue(pattern.startswith("^") and pattern.endswith("$"), pattern)
                self.assertNotIn(".", pattern.replace("\\.", ""), pattern)

    def test_probe_lives_outside_the_seed_and_the_seed_does_not_name_it(self):
        for check in self.fixture["objective_checks"]:
            if check["type"] == "repo_tests":
                self.assertEqual(check["overlay"], "checker")
        self.assertTrue((FIXTURE_DIR / "checker" / ".probe" / "snapshot.sh").is_file())
        self.assertFalse((SEED / ".probe").exists())
        for path in SEED.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8").lower()
                for word in ("eval", "probe", "checker", "fixture"):
                    self.assertNotIn(word, text, f"{path.relative_to(SEED)}: {word}")

    @needs_tools
    def test_the_probe_knows_every_case_a_check_names_and_refuses_others(self):
        named = [case for check in self.fixture["objective_checks"]
                 if check["type"] == "repo_tests" for case in check["fail_to_pass"]]
        for case in [*named, "no-such-case"]:
            ws = self.ws()
            shutil.copytree(FIXTURE_DIR / "checker", ws, dirs_exist_ok=True)
            proc = subprocess.run(["bash", ".probe/snapshot.sh", case], cwd=ws,
                                  capture_output=True, timeout=60)
            with self.subTest(case=case):
                self.assertEqual(proc.returncode == 2, case == "no-such-case")


if __name__ == "__main__":
    unittest.main()
