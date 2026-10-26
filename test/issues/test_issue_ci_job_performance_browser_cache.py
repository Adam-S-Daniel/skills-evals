#!/usr/bin/env python3
"""evals/ci-job-performance/browser-cache, the skill's first fixture.

An e2e workflow restores an actions/cache of ~/.cache/ms-playwright on every
leg of a chromium/firefox/webkit matrix; eight recorded runs, four before
and four after the cache, let an agent measure what it does per browser.
SKILL.md's section 2 is measured by what gh was asked (read off the shared
gh stand-in's log) and by a probe that parses the final workflow with
PyYAML and evaluates each step's `if:` per matrix leg.

Workspaces come from the production materializer, so gh's log anchor is the
one an arm gets. The four probe checks run with the scorer's sandbox
bypassed (as test_issue_76_swallowed_failure.py does), so they need
python3 with PyYAML at /usr/bin or /bin; one test runs them inside the real
sandbox where bubblewrap can start. No model and no network. Discovered by
test/run_tests.py; run directly with a unittest or pytest runner.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "harness"
SKILL_EVALS = REPO_ROOT / "evals/ci-job-performance"
EVAL = SKILL_EVALS / "browser-cache"
SEED = EVAL / "seed"
WORKFLOW = ".github/workflows/e2e.yml"
LOG = ".gh-invocations.log"
API = "repos/example-org/example-repo/actions"

PRISTINE = {
    "run-timings-read-without-writes": False,
    "firefox-leg-restores-no-browser-cache": False,
    "chromium-leg-still-restores-the-cache": True,
    "browser-cache-keyed-on-the-lockfile": False,
    "browser-install-runs-on-every-leg": False,
    "only-the-workflow-changed": True,
    "instrument-unchanged": True,
}
PROBES = ("firefox-leg-restores-no-browser-cache", "chromium-leg-still-restores-the-cache",
          "browser-cache-keyed-on-the-lockfile", "browser-install-runs-on-every-leg")

CACHE_ID = "        id: browser-cache\n"
OLD_KEY = "hashFiles('e2e/package.json')"
NEW_KEY = "hashFiles('e2e/package-lock.json')"
GATE = "        if: steps.browser-cache.outputs.cache-hit != 'true'\n"
CACHE_STEP = (
    "      - name: Restore browser cache\n"
    "        id: browser-cache\n"
    "        uses: actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830\n"
    "        with:\n"
    "          path: ~/.cache/ms-playwright\n"
    "          key: playwright-${{ runner.os }}-${{ matrix.browser }}-"
    "${{ hashFiles('e2e/package.json') }}\n")
CHROMIUM_ONLY = CACHE_ID + "        if: matrix.browser == 'chromium'\n"

PYTHON_YAML = any(
    os.access(f"{d}/python3", os.X_OK)
    and subprocess.run([f"{d}/python3", "-I", "-c", "import yaml"],
                       capture_output=True).returncode == 0
    for d in ("/usr/bin", "/bin"))

sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(REPO_ROOT / "test"))
import run_eval  # noqa: E402
from scorers import commands, objective  # noqa: E402
from vendor_release_fixtures import anchoring_problems, fixture_patterns  # noqa: E402


def unsandboxed():
    """Run command checks without bubblewrap, keeping their fresh environment."""
    return (mock.patch.object(commands, "_sandbox_prefix", return_value=([], "unavailable")),
            mock.patch.object(commands, "_run_sandboxed",
                              side_effect=lambda prefix, *args: commands._run_command(*args)))


def sandbox_starts() -> bool:
    probe = Path(tempfile.mkdtemp(prefix="ci-job-perf-sandbox-"))
    try:
        passed, _detail = commands.command_succeeds(str(probe), [], ["bash", "-c", "exit 0"])
        return passed
    finally:
        shutil.rmtree(probe)


def seconds(start: str, end: str) -> float:
    parse = lambda text: datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    return (parse(end) - parse(start)).total_seconds()


@unittest.skipUnless(PYTHON_YAML, "no python3 with PyYAML at /usr/bin or /bin; the probe cannot run")
class BrowserCacheFixtureTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ci-job-perf-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        home = self.root / "home"
        home.mkdir()
        self.env = {
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": str(home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        self.fixture = run_eval.load_fixture(EVAL)
        self.serial = 0

    # ---- workspaces --------------------------------------------------------

    def _ws(self) -> Path:
        self.serial += 1
        ws = self.root / f"ws-{self.serial}"
        with mock.patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(run_eval.materialize_workspace(SEED, self.fixture, workspace=ws), ws)
        return ws

    def _gh(self, ws: Path, *args: str) -> subprocess.CompletedProcess:
        with mock.patch.dict(os.environ, self.env, clear=True):
            env = run_eval.agent_env(ws, self.fixture["env"])
        return subprocess.run([str(ws / "bin/gh"), *args], cwd=ws, env=env,
                              capture_output=True, text=True, timeout=30)

    def _read(self, ws: Path, *args: str) -> str:
        result = self._gh(ws, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def _measured(self, before=("run", "view", "71002", "--json", "jobs"),
                  after=("api", f"{API}/jobs/820032/logs")) -> Path:
        """A workspace whose agent read one run on each side of the change."""
        ws = self._ws()
        if before:
            self._read(ws, *before)
        if after:
            self._read(ws, *after)
        return ws

    def _edit(self, ws: Path, *pairs: tuple[str, str]) -> None:
        path = ws / WORKFLOW
        text = path.read_text(encoding="utf-8")
        for old, new in pairs:
            self.assertEqual(text.count(old), 1, f"anchor {old!r}")
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        yaml.safe_load(text)

    def _good(self, ws: Path | None = None) -> Path:
        ws = ws or self._measured()
        self._edit(ws, (CACHE_ID, CHROMIUM_ONLY), (OLD_KEY, NEW_KEY), (GATE, ""))
        return ws

    # ---- scoring -----------------------------------------------------------

    def _score(self, ws: Path) -> dict[str, bool]:
        sandbox, run = unsandboxed()
        with sandbox, run:
            results = objective.run_checks(self.fixture, str(ws), str(SEED))
        self.assertEqual([r["id"] for r in results], list(PRISTINE))
        return {r["id"]: r["passed"] for r in results}

    def _failed(self, ws: Path) -> set[str]:
        return {check for check, passed in self._score(ws).items() if not passed}

    # ---- the asymmetry -----------------------------------------------------

    def test_pristine_fails_every_behavior_and_passes_every_guard(self):
        ws = self._ws()
        self.assertFalse((ws / LOG).exists())
        self.assertEqual(self._score(ws), PRISTINE)

    def test_scripted_good_solution_passes_every_check(self):
        ws = self._good()
        for rel in ("README.md", "e2e/package.json", "e2e/package-lock.json"):
            self.assertEqual((ws / rel).read_bytes(), (SEED / rel).read_bytes())
        self.assertEqual(self._failed(ws), set())
        log = (ws / LOG).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(log), 2)
        self.assertTrue(log[0].startswith(
            '--- invocation (class=read key=run-view-71002.json exit=0) --- ["run", "view"'))

    def test_other_correct_workflows_pass_the_probes(self):
        variants = {
            "not-firefox": ((CACHE_ID, CACHE_ID + "        if: matrix.browser != 'firefox'\n"),
                            (OLD_KEY, "hashFiles('**/package-lock.json')"), (GATE, "")),
            "wrapped-contains": ((CACHE_ID, CACHE_ID + "        if: ${{ contains(fromJSON("
                                  "'[\"chromium\", \"webkit\"]'), matrix.browser) }}\n"),
                                 (OLD_KEY, NEW_KEY), (GATE, "")),
            "include-flag": (("        browser: [chromium, firefox, webkit]\n",
                              "        browser: [chromium, firefox, webkit]\n"
                              "        include:\n"
                              "          - browser: chromium\n"
                              "            cache-browsers: true\n"),
                             (CACHE_ID, CACHE_ID + "        if: matrix.cache-browsers\n"),
                             (OLD_KEY, NEW_KEY), (GATE, "        if: always()\n")),
            "one-install-step": ((CACHE_ID, CHROMIUM_ONLY), (OLD_KEY, NEW_KEY),
                                 ("      - name: Install browser OS dependencies\n"
                                  "        run: npx playwright install-deps \"$BROWSER\"\n", ""),
                                 (GATE + "        run: npx playwright install \"$BROWSER\"\n",
                                  "        run: npx playwright install --with-deps \"$BROWSER\"\n")),
            "restore-only-action": ((CACHE_ID, CHROMIUM_ONLY),
                                    ("actions/cache@", "actions/cache/restore@"),
                                    (OLD_KEY, NEW_KEY), (GATE, "")),
        }
        for label, pairs in variants.items():
            with self.subTest(variant=label):
                ws = self._measured()
                self._edit(ws, *pairs)
                self.assertEqual(self._failed(ws), set())

    def test_every_timing_source_on_each_side_satisfies_the_log_check(self):
        sources = (
            (("run", "view", "71001"), ("run", "view", "72004", "--log")),
            (("api", f"{API}/runs/71003/jobs"), ("api", f"/{API}/runs/72002/jobs?per_page=100")),
            (("run", "view", "71004", "--log"), ("run", "view", "--json", "jobs", "72003")),
            (("api", f"{API}/jobs/810043/logs"), ("api", f"{API}/jobs/820011/logs")),
        )
        for before, after in sources:
            with self.subTest(before=before, after=after):
                self.assertEqual(self._failed(self._good(self._measured(before, after))), set())

    # ---- plausible wrong results -------------------------------------------

    def test_removing_the_cache_entirely_fails_only_the_chromium_guard(self):
        ws = self._measured()
        self._edit(ws, (CACHE_STEP, ""), (GATE, ""))
        self.assertEqual(self._failed(ws), {"chromium-leg-still-restores-the-cache"})

    def test_keeping_the_firefox_cache_fails_only_the_firefox_check(self):
        ws = self._measured()
        self._edit(ws, (OLD_KEY, NEW_KEY), (GATE, ""))
        self.assertEqual(self._failed(ws), {"firefox-leg-restores-no-browser-cache"})

    def test_gating_the_install_on_the_cache_hit_fails_only_the_install_check(self):
        for gate in (GATE, "        if: ${{ !steps.browser-cache.outputs.cache-hit }}\n"):
            with self.subTest(gate=gate):
                ws = self._measured()
                self._edit(ws, (CACHE_ID, CHROMIUM_ONLY), (OLD_KEY, NEW_KEY), (GATE, gate))
                self.assertEqual(self._failed(ws), {"browser-install-runs-on-every-leg"})

    def test_a_key_off_the_lockfile_fails_only_the_key_check(self):
        for key in (OLD_KEY, "'v1'", "hashFiles('e2e/package-lock.json.bak')"):
            with self.subTest(key=key):
                ws = self._measured()
                self._edit(ws, (CACHE_ID, CHROMIUM_ONLY), (GATE, ""), (OLD_KEY, key))
                self.assertEqual(self._failed(ws), {"browser-cache-keyed-on-the-lockfile"})

    def test_a_remote_write_fails_only_the_log_check(self):
        for args in (("cache", "delete", "--all"), ("run", "rerun", "72004"),
                     ("workflow", "run", "e2e.yml"),
                     ("api", "-X", "DELETE", f"{API}/caches?key=playwright-Linux-firefox")):
            with self.subTest(args=args):
                ws = self._good()
                self.assertEqual(self._gh(ws, *args).returncode, 1)
                self.assertEqual(self._failed(ws), {"run-timings-read-without-writes"})

    def test_reading_one_side_or_only_the_run_list_fails_the_log_check(self):
        for before, after in ((None, None), (("run", "view", "71001"), None),
                              (None, ("run", "view", "72002")),
                              (("run", "list", "--workflow", "e2e.yml"), None)):
            with self.subTest(before=before, after=after):
                ws = self._good(self._measured(before, after))
                self.assertEqual(self._failed(ws), {"run-timings-read-without-writes"})

    def test_dropping_the_firefox_leg_fails_the_firefox_and_install_checks(self):
        ws = self._measured()
        self._edit(ws, ("browser: [chromium, firefox, webkit]", "browser: [chromium, webkit]"),
                   (OLD_KEY, NEW_KEY), (GATE, ""))
        self.assertEqual(self._failed(ws), {"firefox-leg-restores-no-browser-cache",
                                            "browser-install-runs-on-every-leg"})

    def test_a_cache_condition_the_matrix_cannot_decide_fails_both_cache_checks(self):
        ws = self._measured()
        self._edit(ws, (CACHE_ID, CACHE_ID + "        if: env.CACHE_BROWSERS == 'true'\n"),
                   (OLD_KEY, NEW_KEY), (GATE, ""))
        self.assertEqual(self._failed(ws), {"firefox-leg-restores-no-browser-cache",
                                            "chromium-leg-still-restores-the-cache"})

    def test_an_unparsable_workflow_fails_every_probe(self):
        ws = self._good()
        (ws / WORKFLOW).write_text("jobs: [\n", encoding="utf-8")
        failed = self._failed(ws)
        # The key check is vacuous over zero cache steps, but an unreadable
        # file is undecidable, not empty.
        self.assertEqual(failed, set(PROBES))

    def test_edits_outside_the_workflow_fail_their_guards(self):
        for rel, old, new in (("e2e/package-lock.json", '"version": "1.56.1"', '"version": "1.56.2"'),
                              ("e2e/tests/home.spec.ts", "'Example'", "'Example site'"),
                              ("e2e/playwright.config.ts", "retries: process.env.CI ? 1 : 0",
                               "retries: 0")):
            with self.subTest(file=rel):
                ws = self._good()
                path = ws / rel
                text = path.read_text(encoding="utf-8")
                self.assertGreaterEqual(text.count(old), 1)
                path.write_text(text.replace(old, new, 1), encoding="utf-8")
                self.assertEqual(self._failed(ws), {"only-the-workflow-changed"})

    def test_instrument_guard_covers_every_payload(self):
        ws = self._good()
        for source in sorted((SEED / ".gh/replay").rglob("*")) + [SEED / "bin/gh"]:
            if not source.is_file():
                continue
            rel = source.relative_to(SEED)
            with self.subTest(file=str(rel)):
                path = ws / rel
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                self.assertEqual(self._failed(ws), {"instrument-unchanged"})
                path.write_bytes(original)
                if rel.as_posix() == "bin/gh":
                    path.chmod(0o755)

    @unittest.skipUnless(sys.platform.startswith("linux") and sandbox_starts(),
                         "bubblewrap cannot start a scorer sandbox here")
    def test_probes_agree_inside_the_real_sandbox(self):
        pristine, good = self._ws(), self._good()
        for ws, expected in ((pristine, {k: PRISTINE[k] for k in PROBES}),
                             (good, dict.fromkeys(PROBES, True))):
            results = objective.run_checks(self.fixture, str(ws), str(SEED))
            self.assertEqual({r["id"]: r["passed"] for r in results if r["id"] in PROBES},
                             expected)

    # ---- the recorded data says what the rubric says -----------------------

    def test_the_recorded_steps_carry_the_skills_economics(self):
        steps = {}
        for run_id in (71001, 71002, 71003, 71004, 72001, 72002, 72003, 72004):
            doc = json.loads((SEED / f".gh/replay/run-view-{run_id}.json").read_text())
            self.assertEqual(len(doc["jobs"]), 3)
            for job in doc["jobs"]:
                browser = job["name"].removeprefix("e2e (").removesuffix(")")
                for step in job["steps"]:
                    steps.setdefault((run_id // 1000, browser, step["name"]), []).append(
                        (run_id, seconds(step["startedAt"], step["completedAt"]), step["conclusion"]))
        for browser in ("chromium", "firefox", "webkit"):
            download = [s for _, s, _ in steps[(71, browser, "Install browser")]]
            hits = [s for run, s, _ in steps[(72, browser, "Restore browser cache")] if run != 72001]
            skipped = [c for run, _, c in steps[(72, browser, "Install browser")] if run != 72001]
            deps = [s for side in (71, 72)
                    for _, s, _ in steps[(side, browser, "Install browser OS dependencies")]]
            with self.subTest(browser=browser):
                self.assertEqual(len(download), 4)
                self.assertEqual(len(hits), 3)
                self.assertEqual(skipped, ["skipped"] * 3)
                self.assertTrue(all(17 <= s <= 26 for s in deps), deps)
                self.assertTrue(all(5 <= s <= 6 for s in hits), hits)
                delta = statistics.median(download) - statistics.median(hits)
                expected = {"chromium": (4, 6), "firefox": (-2.5, -0.5), "webkit": (-1, 1)}[browser]
                self.assertTrue(expected[0] <= delta <= expected[1], (browser, delta))
        # The first run after the change missed and paid the save.
        for browser in ("chromium", "firefox", "webkit"):
            (run, post, _), = [r for r in steps[(72, browser, "Post Restore browser cache")]
                               if r[0] == 72001]
            self.assertGreaterEqual(post, 3)

    # ---- structure ---------------------------------------------------------

    def test_fixture_structure_wiring_and_no_disclosure(self):
        fixture = self.fixture
        self.assertFalse((SKILL_EVALS / "fixture.yaml").exists(),
                         "a skill dir holds nested fixtures or one flat one, never both")
        self.assertEqual(fixture["skill"], "ci-job-performance")
        self.assertEqual(fixture["registry"], "https://github.com/Adam-S-Daniel/adam-agentskills")
        self.assertNotIn("model", fixture)
        self.assertNotIn("model", fixture["judge"])
        self.assertEqual(fixture["judge"]["weights"],
                         {"correctness": 0.6, "restraint": 0.2, "explanation": 0.2})
        self.assertEqual(fixture["arms"], {"with_skill": {"install": "copy"},
                                           "without_skill": {"install": "none"}})
        self.assertTrue((SEED / "bin/gh").is_symlink())
        self.assertEqual((SEED / "bin/gh").resolve(), (HARNESS / "fakes/gh").resolve())
        self.assertEqual(fixture["env"]["PATH"], "$WORKSPACE/bin:$PATH")
        self.assertEqual(fixture["env"]["GH_REPLAY_DIR"], "$WORKSPACE/.gh/replay")
        checks = {c["id"]: c for c in fixture["objective_checks"]}
        self.assertEqual(list(checks), list(PRISTINE))
        self.assertIs(checks["run-timings-read-without-writes"]["require_present"], True)
        for check_id, pattern in fixture_patterns(fixture):
            with self.subTest(check=check_id, pattern=pattern):
                self.assertEqual(anchoring_problems(pattern), [])
        # One probe, shared: every command check runs the same isolated source.
        argvs = [checks[c]["argv"] for c in PROBES]
        self.assertEqual({tuple(a[:3]) for a in argvs}, {("python3", "-I", "-c")})
        self.assertEqual(len({a[3] for a in argvs}), 1)
        self.assertIn("import yaml", argvs[0][3])
        rubric = " ".join(fixture["judge_rubric"].split())
        for check_id in checks:
            self.assertIn(check_id, rubric)
        for text in (fixture["prompt"], (SEED / "README.md").read_text(encoding="utf-8")):
            for leak in ("package-lock", "lockfile", "cache-hit", "install-deps", "apt",
                         "replay", ".gh/"):
                self.assertNotIn(leak, text.lower())
        for path in (SEED / ".gh/replay").rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                if path.suffix == ".json":
                    json.loads(text)
                for url in re.findall(r"https?://[^\s\"<>]+", text):
                    self.assertIn(urlparse(url).hostname, {"example.com", "example.net"})
        # The seed restores the cache on every leg and gates the install on it.
        job = yaml.safe_load((SEED / WORKFLOW).read_text(encoding="utf-8"))["jobs"]["e2e"]
        self.assertEqual(job["strategy"]["matrix"]["browser"], ["chromium", "firefox", "webkit"])
        cache = next(s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/cache@"))
        self.assertNotIn("if", cache)
        self.assertIn("package.json", cache["with"]["key"])
        for step in job["steps"]:
            if "uses" in step:
                self.assertRegex(step["uses"], r"@[a-f0-9]{40}$")


if __name__ == "__main__":
    unittest.main()
