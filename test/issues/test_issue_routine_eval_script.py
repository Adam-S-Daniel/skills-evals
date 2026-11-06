"""scripts/routine_eval.py does the eval runner routine's EVAL STEPS.

An eval fire cost the routine session ten or more model calls, about eight
of them mechanical, and a read of the whole 31 KB instructions file. The
steps now live in scripts/routine_eval.py, which the session runs once. These
tests pin what it does, with no network and no real run: payload checks
(including a two-model `models` list), the harness pins read from eval.yml,
the run_eval.py commands it builds for each kind of fixture, its time limits,
and the commit it pushes, against scratch git repositories whose `origin` is
a local bare repository. run_eval.py itself is a fake that writes summaries.
"""

from __future__ import annotations

import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import routine_eval  # noqa: E402

INSTRUCTIONS = ROOT / "docs" / "routine" / "eval-runner-instructions.md"
RUN_ID = "20261106T120000Z-a1b2c3"
MODEL_A = "claude-opus-5-5"
MODEL_B = "claude-sonnet-5-5"
MARKER = "INJECTED-MARKER-7f3e"
PRIVATE_URL = "https://github.com/Adam-S-Daniel/adam-agentskills-private"
REVISION = "0123456789abcdef0123456789abcdef01234567"

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.com",
    "GIT_AUTHOR_DATE": "2026-11-06T00:00:00Z", "GIT_COMMITTER_DATE": "2026-11-06T00:00:00Z",
    "GIT_CONFIG_COUNT": "2",
    "GIT_CONFIG_KEY_0": "gc.auto", "GIT_CONFIG_VALUE_0": "0",
    "GIT_CONFIG_KEY_1": "maintenance.auto", "GIT_CONFIG_VALUE_1": "false",
}

SKILL = "skill-a"
FIXTURES = {
    # An isolation skill fixture.
    "evals/skill-a/basic": {"skill": SKILL, "prompt": "x",
                            "registry": "https://github.com/Adam-S-Daniel/adam-agentskills"},
    # An in-place skill fixture: a top-level `context` mapping.
    "evals/skill-b/deployed": {"skill": "skill-b", "prompt": "x",
                               "registry": "https://github.com/Adam-S-Daniel/cms-platform",
                               "context": {"repository": "Adam-S-Daniel/adamdaniel.ai",
                                           "revision": REVISION}},
    # A pairwise-judged skill fixture.
    "evals/skill-c/paired": {"skill": "skill-c", "prompt": "x",
                             "registry": "https://github.com/Adam-S-Daniel/adam-agentskills",
                             "judge": {"mode": "pairwise"}},
    # A guidance fixture with the usual four arms.
    "evals/guidance/sec-a/one": {"subject": "guidance", "section": "sec-a", "prompt": "x",
                                 "arms": {"with_guidance_section": {"mode": "section"},
                                          "without_guidance": {"mode": "none"},
                                          "with_guidance_full": {"mode": "full"},
                                          "with_guidance_full_minus_section":
                                              {"mode": "full-minus-section"}}},
    # A skill from the private registry.
    "evals/priv-skill/one": {"skill": "priv-skill", "prompt": "x", "registry": PRIVATE_URL},
}


def payload(**overrides) -> dict:
    doc = {"mode": "eval", "run_id": RUN_ID, "fixture": "evals/skill-a/basic",
           "arms": "both", "trials": 1}
    doc.update(overrides)
    return {k: v for k, v in doc.items() if v is not None}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class FakeClock:
    """A monotonic clock and a UTC wall clock that move together, only when
    told to."""

    def __init__(self):
        self.t = 5000.0
        self.wall = datetime(2026, 11, 6, 12, 0, 0, 250000, tzinfo=timezone.utc)
        self.sleeps = []

    def monotonic(self) -> float:
        return self.t

    def now(self) -> datetime:
        return self.wall

    def advance(self, seconds: float) -> None:
        self.t += seconds
        self.wall += timedelta(seconds=seconds)

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.advance(seconds)


class FakeRunner:
    """Records every command. Git runs for real (`real_git`) or answers with
    canned output; pip is recorded; run_eval.py writes what the harness would
    write for its --arm, unless `writes` is False."""

    def __init__(self, clock: FakeClock, *, real_git=False, shallow=(), codes=None,
                 seconds=None, writes=True, fail=None, setup_seconds=0.0):
        self.clock, self.real_git, self.shallow = clock, real_git, set(shallow)
        self.codes, self.seconds = codes or {}, seconds or {}
        self.writes, self.fail, self.setup_seconds = writes, fail, setup_seconds
        self.calls: list[list[str]] = []
        self.evals: list[tuple[list[str], float]] = []

    def run(self, argv, *, cwd=None, timeout=None):
        self.calls.append(list(argv))
        if argv[0] != "git":
            self.clock.advance(self.setup_seconds)
            return 0, "Successfully installed\n"
        if self.fail is not None and self.fail(argv):
            return 1, "fatal: refused by the fake remote\n"
        if self.real_git:
            done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                                  timeout=timeout, check=False)
            return done.returncode, done.stdout + done.stderr
        if "--is-shallow-repository" in argv:
            return 0, "true\n" if Path(argv[2]).name in self.shallow else "false\n"
        return 0, ""

    def run_eval(self, argv, *, cwd, timeout, log):
        self.evals.append((list(argv), timeout))
        model = argv[argv.index("--model") + 1] if "--model" in argv else None
        stamp = self.clock.now().strftime("%Y%m%dT%H%M%SZ")
        self.clock.advance(self.seconds.get(model, 60.0))
        code = self.codes.get(model, 0)
        log.write_text("starting\nconfiguration error: the fake harness refused\n"
                       if code else "done\n", encoding="utf-8")
        if not self.writes:
            return code
        results = Path(cwd) / argv[argv.index("--results-dir") + 1]
        fixture = argv[2]
        key = FIXTURES[fixture].get("skill", "guidance")
        arm = argv[argv.index("--arm") + 1]
        arms = {"both": ["with_skill", "without_skill"],
                "in-situ": ["with_guidance_full", "with_guidance_full_minus_section"]}.get(arm, [arm])
        run_dir = results / key / stamp
        for name in arms:
            arm_dir = run_dir / name
            (arm_dir / "transcripts").mkdir(parents=True, exist_ok=True)
            summary = {"arm": name, "timestamp": stamp, "error": None,
                       "objective_checks": [{"id": "secret-check-text", "passed": True},
                                            {"id": "second", "passed": name == "with_skill"}],
                       "judge": {"status": "skipped", "reason": "objective-decided"},
                       "models_used": [model or MODEL_A]}
            (arm_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            (arm_dir / "transcripts" / "tool_trace.json").write_text("[]\n", encoding="utf-8")
            (arm_dir / "transcripts" / "raw.json").write_text(
                '{"token": "do-not-commit"}\n', encoding="utf-8")
        (run_dir / "report.md").write_text("# report\n", encoding="utf-8")
        (run_dir / "notes.txt").write_text("stray\n", encoding="utf-8")
        return code


class CheckoutCase(unittest.TestCase):
    """A scratch skills-evals checkout holding FIXTURES, eval.yml and
    registries.yml, committed, with sibling clones beside it."""

    #: Siblings made real clones of a local bare `origin` (else a bare `.git`
    #: directory, enough for canned git).
    REAL = False
    SIBLINGS = ("_agent-guidance", "adam-agentskills", "cms-platform", "adamdaniel.ai",
                "adam-agentskills-private", "wsl-automation", "repo-settings")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        env = mock.patch.dict(os.environ, GIT_ENV)
        env.start()
        self.addCleanup(env.stop)
        files = {".github/workflows/eval.yml":
                     (ROOT / ".github/workflows/eval.yml").read_bytes(),
                 "harness/registries.yml": (ROOT / "harness/registries.yml").read_bytes()}
        for path, doc in FIXTURES.items():
            files[f"{path}/fixture.yaml"] = yaml.safe_dump(doc).encode()
        self.checkout = self.repo("skills-evals", files)
        for name in self.SIBLINGS:
            if self.REAL:
                self.repo(name, {"README.md": f"{name}\n".encode()})
            else:
                (self.tmp / name / ".git").mkdir(parents=True)
        self.clock = FakeClock()
        self.payload_file = self.tmp / "payload.json"

    def repo(self, name: str, files: dict) -> Path:
        """A clone at tmp/<name> of a bare remote whose main holds `files`."""
        seed = self.tmp / "seed" / name
        seed.mkdir(parents=True)
        git(seed, "init", "-q", "-b", "main")
        for rel, data in files.items():
            (seed / rel).parent.mkdir(parents=True, exist_ok=True)
            (seed / rel).write_bytes(data)
        git(seed, "add", "-A")
        git(seed, "commit", "-q", "-m", "main")
        bare = self.tmp / "remotes" / f"{name}.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(bare)], check=True)
        dest = self.tmp / name
        subprocess.run(["git", "clone", "-q", str(bare), str(dest)], check=True)
        return dest

    def fire(self, doc, runner=None, **runner_args):
        text = doc if isinstance(doc, str) else json.dumps(doc)
        self.payload_file.write_text(text, encoding="utf-8")
        self.runner = runner or FakeRunner(self.clock, real_git=self.REAL, **runner_args)
        out, err = io.StringIO(), io.StringIO()
        code = routine_eval.main(["--payload", str(self.payload_file),
                                  "--checkout", str(self.checkout)],
                                 runner=self.runner, clock=self.clock.monotonic,
                                 wall=self.clock.now, sleep=self.clock.sleep,
                                 python="python3", out=out, err=err)
        self.report = out.getvalue()
        return code

    def sibling(self, name: str) -> str:
        return str(self.tmp / name)

    def eval_argv(self, index=0) -> list[str]:
        return self.runner.evals[index][0]

    def git_calls(self) -> list[list[str]]:
        return [c[1:] for c in self.runner.calls if c[0] == "git"]

    def tail(self, fixture: str, model_flags=(), pairing=(), judge=(), arm="both",
             trials=1, flags=()) -> list[str]:
        return ["python3", "harness/run_eval.py", fixture, "--arm", arm,
                "--trials", str(trials), *flags, *pairing, *model_flags, *judge,
                "--results-dir", f"eval-results/{RUN_ID}",
                "--run-billing", "subscription", "--run-runner", "routine",
                "--run-location", "cloud", "--run-id", RUN_ID]

    def public_registry_flags(self) -> list[str]:
        out = []
        for name in ("adam-agentskills", "cms-platform", "adamdaniel.ai"):
            out += ["--registry", f"{name}={self.sibling(name)}"]
        return out


class PayloadTests(unittest.TestCase):

    def test_the_minimal_payload_runs_the_roster_default_once(self):
        got = routine_eval.validate_payload(payload(mode=None))
        self.assertEqual(got, routine_eval.Payload("evals/skill-a/basic", "both", 1, RUN_ID,
                                                   (None,)))

    def test_one_model_or_two(self):
        self.assertEqual(routine_eval.validate_payload(payload(model=MODEL_A)).models,
                         (MODEL_A,))
        longest = "claude-" + "a" * 63
        self.assertEqual(routine_eval.validate_payload(payload(model=longest)).models,
                         (longest,))
        self.assertEqual(routine_eval.validate_payload(payload(models=[MODEL_B, MODEL_A])).models,
                         (MODEL_B, MODEL_A))

    def test_every_arm_and_trial_count_the_rule_allows(self):
        for arms in ("both", "with", "without", "bare", "in-situ"):
            for trials in (1, 2, 3):
                with self.subTest(arms=arms, trials=trials):
                    got = routine_eval.validate_payload(payload(arms=arms, trials=trials))
                    self.assertEqual((got.arms, got.trials), (arms, trials))

    def test_anything_else_is_refused(self):
        cases = {
            "not an object": [payload()],
            "another mode": payload(mode="improve"),
            "an empty mode": payload(mode=""),
            "a null mode": {**payload(), "mode": None},
            "an extra key": payload(extra=1),
            "a scaffold key": payload(candidate="a__b__1"),
            "no fixture": payload(fixture=None),
            "no arms": payload(arms=None),
            "no trials": payload(trials=None),
            "no run id": payload(run_id=None),
            "fixture outside evals": payload(fixture="harness/x"),
            "fixture with ..": payload(fixture="evals/../x"),
            "fixture with //": payload(fixture="evals//x"),
            "fixture with a space": payload(fixture="evals/a b"),
            "fixture not a string": payload(fixture=["evals/x"]),
            "unknown arms": payload(arms="all"),
            "arms not a string": payload(arms=1),
            "trials 0": payload(trials=0),
            "trials 4": payload(trials=4),
            "trials a string": payload(trials="1"),
            "trials a bool": payload(trials=True),
            "trials a float": payload(trials=1.0),
            "run id shape": payload(run_id="20261106T120000Z-ABC123"),
            "run id newline": payload(run_id=RUN_ID + "\n"),
            "model shape": payload(model="Claude-opus"),
            "model leading dash": payload(model="claude--x"),
            "model too long": payload(model="claude-" + "a" * 64),
            "model not a string": payload() | {"model": 3},
            "both model keys": payload(model=MODEL_A, models=[MODEL_A, MODEL_B]),
            "one of models": payload(models=[MODEL_A]),
            "three models": payload(models=[MODEL_A, MODEL_B, "claude-haiku-5-5"]),
            "the same model twice": payload(models=[MODEL_A, MODEL_A]),
            "models not a list": payload(models=MODEL_A),
            "a bad model in models": payload(models=[MODEL_A, "gpt-x"]),
        }
        for label, doc in cases.items():
            with self.subTest(label), self.assertRaises(routine_eval.Refused):
                routine_eval.validate_payload(doc)

    def test_the_payload_file_is_one_json_object_with_unique_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            good = json.dumps(payload())
            for label, data in {
                    "duplicate key": good[:-1].encode() + b', "trials": 2}',
                    "NaN": good.replace('"trials": 1', '"trials": NaN').encode(),
                    "not UTF-8": b'{"fixture": "\xff"}',
                    "two values": (good + good).encode(),
                    "oversized": good[:-1].encode() + b', "x": "' + b"a" * 20000 + b'"}'}.items():
                path.write_bytes(data)
                with self.subTest(label), self.assertRaises(routine_eval.Refused):
                    routine_eval.load_payload(path)
            path.write_text(good + "\n", encoding="utf-8")
            self.assertEqual(routine_eval.load_payload(path).run_id, RUN_ID)

    def test_no_refusal_echoes_the_payload(self):
        for doc in (payload(fixture=f"evals/{MARKER} x"), payload(arms=MARKER),
                    payload(model=MARKER), payload(**{MARKER: 1}), payload(mode=MARKER),
                    payload(models=[MODEL_A, MARKER]), payload(run_id=MARKER)):
            with self.subTest(doc=doc), self.assertRaises(routine_eval.Refused) as caught:
                routine_eval.validate_payload(doc)
            self.assertNotIn(MARKER, str(caught.exception))

    def test_the_rule_is_the_instructions_rule(self):
        text = INSTRUCTIONS.read_text(encoding="utf-8")
        eval_line = next(line for line in text.splitlines() if line.startswith("- EVAL mode"))
        self.assertIn(f"^{routine_eval.RUN_ID_RE.pattern}$", eval_line)
        self.assertIn(f"^{routine_eval.MODEL_RE.pattern}$", eval_line)
        self.assertIn("|".join(routine_eval.ARMS), eval_line)
        self.assertIn(f"trials 1-{routine_eval.MAX_TRIALS}", eval_line)
        self.assertIn('"models": a list of exactly two distinct model ids', eval_line)


class PinsTests(unittest.TestCase):

    def steps_named(self, doc, name):
        return {job: step for job, body in doc["jobs"].items()
                for step in body.get("steps", []) if step.get("name") == name}

    def test_the_pins_are_the_ones_eval_yml_installs_for_the_harness(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/eval.yml").read_text(encoding="utf-8"))
        steps = self.steps_named(doc, routine_eval.PIN_STEP)
        self.assertIn(routine_eval.EVAL_JOB, steps)
        pins = routine_eval.harness_pins(ROOT)
        for job, step in steps.items():
            with self.subTest(job=job):
                self.assertEqual(shlex.split(step["run"]), ["pip", "install", *pins])
        self.assertTrue(any(pin.startswith("pyyaml==") for pin in pins))
        self.assertTrue(all("==" in pin for pin in pins))

    def test_the_pins_are_read_from_the_file_not_kept_here(self):
        doc = yaml.safe_load((ROOT / ".github/workflows/eval.yml").read_text(encoding="utf-8"))
        step = self.steps_named(doc, routine_eval.PIN_STEP)[routine_eval.EVAL_JOB]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / routine_eval.EVAL_WORKFLOW
            target.parent.mkdir(parents=True)
            step["run"] = "pip install pyyaml==9.9.9 other-package==1.0"
            target.write_text(yaml.safe_dump(doc), encoding="utf-8")
            self.assertEqual(routine_eval.harness_pins(Path(tmp)),
                             ["pyyaml==9.9.9", "other-package==1.0"])
            for run in ("pip install pyyaml", "pip install pyyaml==1 && rm -rf x",
                        "python3 -m pip install pyyaml==1", "pip install"):
                step["run"] = run
                target.write_text(yaml.safe_dump(doc), encoding="utf-8")
                with self.subTest(run=run), self.assertRaises(routine_eval.Failed):
                    routine_eval.harness_pins(Path(tmp))

    def test_the_private_registry_is_registries_ymls(self):
        doc = yaml.safe_load((ROOT / "harness/registries.yml").read_text(encoding="utf-8"))
        entries = {e["name"]: e for e in doc["registries"]}
        self.assertEqual(entries[routine_eval.PRIVATE_REGISTRY]["url"],
                         routine_eval.PRIVATE_REGISTRY_URL)
        self.assertIs(entries[routine_eval.PRIVATE_REGISTRY]["private"], True)
        for name in routine_eval.PUBLIC_REGISTRIES:
            self.assertIs(entries[name]["private"], False)

    def test_the_siblings_are_the_rules_repositories(self):
        text = INSTRUCTIONS.read_text(encoding="utf-8")
        listed = text.split("default branches of the cloned repos (", 1)[1].split(")", 1)[0]
        repos = [name.strip() for name in listed.split(",")]
        self.assertEqual(repos[0], "skills-evals")
        self.assertEqual(tuple(repos[1:]), routine_eval.SIBLINGS)


class CommandTests(CheckoutCase):
    """The commands each kind of fire builds, with canned git."""

    def test_an_isolation_skill_fixture(self):
        self.assertEqual(self.fire(payload(), writes=False), 1)
        pins = routine_eval.harness_pins(self.checkout)
        self.assertEqual(self.runner.calls[0],
                         ["python3", "-m", "pip", "install", "--user", *pins])
        expected_git = []
        for name in ("adam-agentskills", "cms-platform", "adamdaniel.ai"):
            expected_git += [["-C", self.sibling(name), "fetch", "origin", "main"],
                             ["-C", self.sibling(name), "checkout", "--quiet", "--detach",
                              "origin/main"]]
        self.assertEqual(self.git_calls(), expected_git)
        self.assertEqual(self.eval_argv(),
                         self.tail("evals/skill-a/basic", flags=self.public_registry_flags()))
        self.assertEqual(len(self.runner.evals), 1)
        for flag in ("--pairing", "--model", "--no-judge", "--judge", "--asserted-quiet"):
            self.assertNotIn(flag, self.eval_argv())
        self.assertIn("pairing: isolation", self.report)
        self.assertIn("harness wrote no summary.json", self.report)
        self.assertTrue(self.report.endswith("RESULT: error\n"))

    def test_an_in_place_skill_fixture_unshallows_every_sibling_first(self):
        self.fire(payload(fixture="evals/skill-b/deployed"), writes=False,
                  shallow={"adamdaniel.ai", "repo-settings"})
        expected = []
        for name in routine_eval.SIBLINGS:
            expected.append(["-C", self.sibling(name), "rev-parse", "--is-shallow-repository"])
            if name in ("adamdaniel.ai", "repo-settings"):
                expected.append(["-C", self.sibling(name), "fetch", "--unshallow", "origin"])
            expected.append(["-C", self.sibling(name), "fetch", "origin", "main"])
        for name in ("adam-agentskills", "cms-platform", "adamdaniel.ai"):
            expected.append(["-C", self.sibling(name), "checkout", "--quiet", "--detach",
                             "origin/main"])
        self.assertEqual(self.git_calls(), expected)
        self.assertEqual(self.eval_argv(),
                         self.tail("evals/skill-b/deployed", flags=self.public_registry_flags(),
                                   pairing=["--pairing", "in_place"]))
        self.assertIn("pairing: in_place", self.report)

    def test_a_missing_sibling_is_skipped_and_a_missing_registry_noted(self):
        shutil.rmtree(self.tmp / "wsl-automation")
        shutil.rmtree(self.tmp / "cms-platform")
        self.fire(payload(fixture="evals/skill-b/deployed"), writes=False)
        touched = {Path(call[1]).name for call in self.git_calls()}
        self.assertNotIn("wsl-automation", touched)
        self.assertNotIn("cms-platform", touched)
        self.assertEqual([self.eval_argv()[i + 1] for i, a in enumerate(self.eval_argv())
                          if a == "--registry"],
                         [f"adam-agentskills={self.sibling('adam-agentskills')}",
                          f"adamdaniel.ai={self.sibling('adamdaniel.ai')}"])
        self.assertIn("note: registry clone cms-platform is not checked out", self.report)

    def test_bare_is_one_isolation_without_arm_and_no_sibling_fetch(self):
        self.fire(payload(fixture="evals/skill-b/deployed", arms="bare", trials=3),
                  writes=False, shallow={"adamdaniel.ai"})
        calls = self.git_calls()
        self.assertFalse([c for c in calls if "--unshallow" in c or "rev-parse" in c])
        self.assertEqual(len([c for c in calls if c[2:] == ["fetch", "origin", "main"]]), 3)
        self.assertEqual(self.eval_argv(),
                         self.tail("evals/skill-b/deployed", arm="without_skill", trials=3,
                                   flags=self.public_registry_flags(),
                                   pairing=["--pairing", "isolation"]))
        self.assertIn("pairing: isolation", self.report)

    def test_with_and_without_name_the_skill_arms(self):
        for arms, arm in (("with", "with_skill"), ("without", "without_skill")):
            with self.subTest(arms=arms):
                shutil.rmtree(self.checkout / "eval-results", ignore_errors=True)
                self.fire(payload(arms=arms), writes=False)
                argv = self.eval_argv()
                self.assertEqual(argv[argv.index("--arm") + 1], arm)

    def test_a_guidance_fixture_gets_guidance_and_no_registry(self):
        for arms in ("both", "in-situ"):
            with self.subTest(arms=arms):
                shutil.rmtree(self.checkout / "eval-results", ignore_errors=True)
                self.fire(payload(fixture="evals/guidance/sec-a/one", arms=arms), writes=False)
                self.assertEqual(self.git_calls(), [])
                self.assertEqual(self.eval_argv(),
                                 self.tail("evals/guidance/sec-a/one", arm=arms,
                                           flags=["--guidance",
                                                  self.sibling("_agent-guidance")]))

    def test_a_guidance_fixture_without_its_checkout_runs_nothing(self):
        shutil.rmtree(self.tmp / "_agent-guidance")
        self.assertEqual(self.fire(payload(fixture="evals/guidance/sec-a/one"), writes=False), 1)
        self.assertEqual((self.runner.calls, self.runner.evals), ([], []))
        self.assertIn("_agent-guidance checkout is missing", self.report)

    def test_a_pairwise_fixture_turns_the_judge_off(self):
        self.fire(payload(fixture="evals/skill-c/paired"))
        self.assertEqual(self.eval_argv(),
                         self.tail("evals/skill-c/paired", flags=self.public_registry_flags(),
                                   judge=["--no-judge"]))
        self.assertIn("judge turned off", self.report)

    def test_the_private_registry_only_for_its_own_fixture(self):
        self.fire(payload(fixture="evals/priv-skill/one"), writes=False)
        flags = self.public_registry_flags() + [
            "--registry", f"adam-agentskills-private={self.sibling('adam-agentskills-private')}"]
        self.assertEqual(self.eval_argv(), self.tail("evals/priv-skill/one", flags=flags))
        self.assertIn(["-C", self.sibling("adam-agentskills-private"), "checkout", "--quiet",
                       "--detach", "origin/main"], self.git_calls())
        shutil.rmtree(self.checkout / "eval-results", ignore_errors=True)
        self.fire(payload(), writes=False)
        self.assertNotIn("adam-agentskills-private", " ".join(self.eval_argv()))

    def test_one_model(self):
        self.fire(payload(model=MODEL_A), writes=False)
        self.assertEqual(self.eval_argv(),
                         self.tail("evals/skill-a/basic", flags=self.public_registry_flags(),
                                   model_flags=["--model", MODEL_A]))
        self.assertIn(f"run {MODEL_A}: exit 0", self.report)

    def test_two_models_run_in_order_into_one_results_directory(self):
        self.fire(payload(models=[MODEL_B, MODEL_A], trials=3), writes=False)
        self.assertEqual([argv for argv, _ in self.runner.evals],
                         [self.tail("evals/skill-a/basic", trials=3,
                                    flags=self.public_registry_flags(),
                                    model_flags=["--model", model])
                          for model in (MODEL_B, MODEL_A)])
        # Pins, fetches and detaches happen once, not per model.
        self.assertEqual(len([c for c in self.runner.calls if c[0] != "git"]), 1)
        self.assertEqual(len(self.git_calls()), 6)
        self.assertLess(self.report.index(f"run {MODEL_B}"), self.report.index(f"run {MODEL_A}"))

    def test_no_model_is_the_roster_default(self):
        self.fire(payload(), writes=False)
        self.assertIn("run roster default: exit 0", self.report)

    def test_a_failed_run_is_not_retried_and_the_next_model_still_runs(self):
        self.fire(payload(models=[MODEL_A, MODEL_B]), writes=False, codes={MODEL_A: 2})
        self.assertEqual(len(self.runner.evals), 2)
        self.assertIn("configuration error: the fake harness refused", self.report)

    def test_a_failed_git_step_runs_nothing(self):
        self.assertEqual(self.fire(payload(), writes=False,
                                   fail=lambda argv: "checkout" in argv), 1)
        self.assertEqual(self.runner.evals, [])
        self.assertIn("error: git checkout --detach origin/main in adam-agentskills exited 1",
                      self.report)
        self.assertIn("fatal: refused by the fake remote", self.report)

    def test_refusals_run_nothing(self):
        (self.checkout / "evals/untracked/one").mkdir(parents=True)
        (self.checkout / "evals/untracked/one/fixture.yaml").write_text("skill: x\n")
        cases = {
            "not committed": payload(fixture="evals/untracked/one"),
            "no such fixture": payload(fixture="evals/none/here"),
            "in-situ on a skill fixture": payload(arms="in-situ"),
            "over the agent-run limit": payload(fixture="evals/guidance/sec-a/one", trials=2),
            "improve mode": {"run_id": RUN_ID, "mode": "improve", "skill": "x", "trials": 1,
                             "holdout": None},
        }
        for label, doc in cases.items():
            with self.subTest(label):
                self.assertEqual(self.fire(doc), 2)
                self.assertEqual((self.runner.calls, self.runner.evals), ([], []))
                self.assertTrue(self.report.startswith("REFUSED: "))
                self.assertTrue(self.report.endswith("RESULT: refused\n"))

    def test_six_agent_runs_per_model_is_the_limit(self):
        self.assertNotEqual(self.fire(payload(trials=3, models=[MODEL_A, MODEL_B]),
                                      writes=False), 2)
        self.assertEqual(len(self.runner.evals), 2)

    def test_an_existing_results_directory_runs_nothing(self):
        (self.checkout / "eval-results" / RUN_ID).mkdir(parents=True)
        self.assertEqual(self.fire(payload()), 1)
        self.assertEqual(self.runner.evals, [])
        self.assertIn("already exists", self.report)


class TimeLimitTests(CheckoutCase):

    def test_each_run_gets_the_time_left_to_the_hard_stop(self):
        self.fire(payload(models=[MODEL_A, MODEL_B]), writes=False, setup_seconds=90,
                  seconds={MODEL_A: 600, MODEL_B: 60})
        first, second = [timeout for _, timeout in self.runner.evals]
        self.assertEqual(first, routine_eval.HARD_STOP_S - 90)
        # Less the wait for a new UTC second between the two runs (under 1 s).
        self.assertAlmostEqual(second, routine_eval.HARD_STOP_S - 90 - 600, delta=1.0)
        self.assertLess(second, routine_eval.HARD_STOP_S - 90 - 600)

    def test_no_run_starts_after_the_soft_limit(self):
        code = self.fire(payload(models=[MODEL_A, MODEL_B]), writes=True,
                         seconds={MODEL_A: routine_eval.SOFT_LIMIT_S + 1})
        self.assertEqual(code, 1)
        self.assertEqual(len(self.runner.evals), 1)
        self.assertIn(f"run {MODEL_B}: not started (past the 30-minute limit)", self.report)
        self.assertTrue(self.report.endswith("RESULT: error\n"))

    def test_a_run_stopped_at_the_hard_stop_is_reported(self):
        class Stopped(FakeRunner):
            def run_eval(self, argv, *, cwd, timeout, log):
                super().run_eval(argv, cwd=cwd, timeout=timeout, log=log)
                return None

        runner = Stopped(self.clock, writes=False)
        self.assertEqual(self.fire(payload(), runner=runner), 1)
        self.assertIn("stopped at the 40-minute hard stop", self.report)

    def test_a_second_run_starts_in_a_later_utc_second(self):
        self.fire(payload(models=[MODEL_A, MODEL_B]), writes=True,
                  seconds={MODEL_A: 0.0, MODEL_B: 0.0})
        self.assertTrue(self.clock.sleeps)
        stamps = sorted(p.name for p in (self.checkout / "eval-results" / RUN_ID / SKILL).iterdir())
        self.assertEqual(len(stamps), 2)

    def test_the_limits_are_the_instructions(self):
        text = INSTRUCTIONS.read_text(encoding="utf-8")
        limits = text.split("Limits: ", 1)[1]
        self.assertTrue(limits.startswith(
            f"eval and scaffold modes max {routine_eval.MAX_AGENT_RUNS_PER_MODEL} nested "
            "agent runs"))
        self.assertIn(f"after {routine_eval.SOFT_LIMIT_S // 60} minutes and stops one at "
                      f"{routine_eval.HARD_STOP_S // 60})", limits)


class PublishTests(CheckoutCase):
    """The commit and push, against local bare remotes."""

    REAL = True
    SIBLINGS = ("adam-agentskills", "cms-platform", "adamdaniel.ai", "adam-agentskills-private")

    def remote_files(self, name: str, branch: str) -> list[str]:
        bare = self.tmp / "remotes" / f"{name}.git"
        return git(bare, "ls-tree", "-r", "--name-only", branch).splitlines()

    def remote_branches(self, name: str) -> list[str]:
        bare = self.tmp / "remotes" / f"{name}.git"
        return git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()

    def expected(self, stamps, arms=("with_skill", "without_skill")) -> list[str]:
        out = []
        for stamp in stamps:
            base = f"eval-results/{RUN_ID}/{SKILL}/{stamp}"
            out.append(f"{base}/report.md")
            for arm in arms:
                out += [f"{base}/{arm}/summary.json", f"{base}/{arm}/transcripts/tool_trace.json"]
        return out

    def test_the_results_are_pushed_without_raw_json_or_strays(self):
        self.assertEqual(self.fire(payload(model=MODEL_A)), 0, self.report)
        branch = f"claude/eval-{RUN_ID}"
        self.assertIn(branch, self.remote_branches("skills-evals"))
        files = self.remote_files("skills-evals", branch)
        main = self.remote_files("skills-evals", "main")
        self.assertEqual(sorted(set(files) - set(main)), sorted(self.expected(["20261106T120000Z"])))
        self.assertFalse([f for f in files if f.endswith("raw.json") or f.endswith("notes.txt")])
        bare = self.tmp / "remotes" / "skills-evals.git"
        self.assertEqual(git(bare, "rev-parse", f"{branch}^"), git(bare, "rev-parse", "main"))
        sha = git(bare, "rev-parse", branch)
        lines = self.report.splitlines()
        self.assertEqual(lines[:4], ["fixture: evals/skill-a/basic", "arms: both", "trials: 1",
                                     "pairing: isolation"])
        self.assertEqual(lines[4], f"run {MODEL_A}: exit 0, wall 60s, judge skipped by the "
                                   "harness; with_skill pass (2/2 checks), without_skill fail "
                                   "(1/2 checks)")
        self.assertIn(f"branch pushed: {branch} in Adam-S-Daniel/skills-evals at {sha}, "
                      "5 file(s), 3 other file(s) left out", self.report)
        self.assertEqual(lines[-1], "RESULT: ok")
        self.assertNotIn("secret-check-text", self.report)
        self.assertNotIn(branch, self.remote_branches("adam-agentskills-private"))
        # The registries were detached at origin/main.
        self.assertEqual(git(self.tmp / "adam-agentskills", "rev-parse", "HEAD"),
                         git(self.tmp / "adam-agentskills", "rev-parse", "origin/main"))
        self.assertEqual(git(self.tmp / "adam-agentskills", "branch", "--show-current"), "")

    def test_two_models_share_one_branch(self):
        self.assertEqual(self.fire(payload(models=[MODEL_A, MODEL_B])), 0, self.report)
        files = self.remote_files("skills-evals", f"claude/eval-{RUN_ID}")
        # The second run starts in the UTC second after the first one ended.
        self.assertEqual(sorted(f for f in files if f.startswith("eval-results/")),
                         sorted(self.expected(["20261106T120000Z", "20261106T120101Z"])))
        self.assertEqual(len(self.remote_branches("skills-evals")), 2)

    def test_a_private_skill_goes_to_the_private_repository_only(self):
        self.assertEqual(self.fire(payload(fixture="evals/priv-skill/one")), 0, self.report)
        branch = f"claude/eval-{RUN_ID}"
        self.assertEqual(self.remote_branches("skills-evals"), ["main"])
        self.assertIn(branch, self.remote_branches("adam-agentskills-private"))
        files = self.remote_files("adam-agentskills-private", branch)
        stamp = "20261106T120000Z"
        self.assertIn(f"eval-results/{RUN_ID}/priv-skill/{stamp}/with_skill/summary.json", files)
        self.assertFalse([f for f in files if f.endswith("raw.json")])
        self.assertIn(f"in Adam-S-Daniel/adam-agentskills-private at", self.report)

    def test_a_private_skill_without_its_clone_runs_and_pushes_nothing(self):
        shutil.rmtree(self.tmp / "adam-agentskills-private")
        self.assertEqual(self.fire(payload(fixture="evals/priv-skill/one")), 1)
        self.assertEqual((self.runner.calls, self.runner.evals), ([], []))
        self.assertEqual(self.remote_branches("skills-evals"), ["main"])
        self.assertIn("adam-agentskills-private is not cloned", self.report)

    def test_a_private_skills_guard_text_is_withheld(self):
        self.assertEqual(self.fire(payload(fixture="evals/priv-skill/one"), writes=False,
                                   codes={None: 2}), 1)
        self.assertIn("guard text withheld for a private skill", self.report)
        self.assertNotIn("the fake harness refused", self.report)

    def test_no_summary_pushes_nothing_and_reports_the_guard_text(self):
        self.assertEqual(self.fire(payload(), writes=False, codes={None: 2}), 1)
        self.assertEqual(self.remote_branches("skills-evals"), ["main"])
        self.assertIn("run roster default: exit 2", self.report)
        self.assertIn("    configuration error: the fake harness refused", self.report)
        self.assertIn("branch pushed: none", self.report)

    def test_an_errored_run_with_summaries_is_still_pushed(self):
        self.assertEqual(self.fire(payload(), codes={None: 2}), 1)
        self.assertIn(f"claude/eval-{RUN_ID}", self.remote_branches("skills-evals"))
        self.assertTrue(self.report.endswith("RESULT: error\n"))

    def test_a_refused_push_is_an_error(self):
        self.assertEqual(self.fire(payload(), fail=lambda argv: "push" in argv), 1)
        self.assertEqual(self.remote_branches("skills-evals"), ["main"])
        self.assertIn("error: git push exited 1", self.report)
        self.assertIn("branch pushed: none", self.report)


class CommitFilterTests(unittest.TestCase):

    def test_only_what_the_ingest_accepts_is_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ["k/t/report.md", "k/t/with_skill/summary.json",
                     "k/t/with_skill/transcripts/tool_trace.json",
                     "k/t/with_skill/transcripts/raw.json",
                     "k/t/with_skill/trial-1/summary.json",
                     "k/t/with_skill/trial-1/transcripts/raw.json",
                     "k/t/with_skill/trial-1/transcripts/tool_trace.json",
                     "k/t/with_skill/tool_trace.json", "k/t/notes.txt"]
            for name in names:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text("{}\n", encoding="utf-8")
            (root / "k/t/link").mkdir()
            (root / "k/t/link/summary.json").symlink_to(root / "k/t/with_skill/summary.json")
            keep, left_out = routine_eval.result_files(root)
        self.assertEqual(keep, sorted(["k/t/report.md", "k/t/with_skill/summary.json",
                                       "k/t/with_skill/transcripts/tool_trace.json",
                                       "k/t/with_skill/trial-1/summary.json",
                                       "k/t/with_skill/trial-1/transcripts/tool_trace.json"]))
        self.assertEqual(left_out, 5)


class ReportTests(unittest.TestCase):

    def test_arm_results_are_counts_never_check_text(self):
        single = {"arm": "with_skill", "error": None,
                  "objective_checks": [{"id": MARKER, "passed": True, "detail": MARKER}]}
        self.assertEqual(routine_eval.arm_result(single), "with_skill pass (1/1 checks)")
        errored = {"arm": "without_skill", "error": {"type": "timeout", "detail": MARKER}}
        self.assertEqual(routine_eval.arm_result(errored), "without_skill error (timeout)")
        trials = {"arm": "with_skill", "errors": 1,
                  "aggregate": {"objective": {"n": 2, "passed": 5, "total": 8}}}
        self.assertEqual(routine_eval.arm_result(trials),
                         "with_skill 5/8 checks over 2 scored trial(s), 1 errored")
        odd = {"arm": f"{MARKER} x", "error": {"type": f"{MARKER} y"}}
        self.assertNotIn(MARKER, routine_eval.arm_result(odd))

    def test_judge_states(self):
        ran = {"judge": {"overall": 7.0}}
        skipped = {"judge": {"status": "skipped", "reason": "objective-decided"}}
        self.assertEqual(routine_eval.judge_state([ran, skipped], False), "ran")
        self.assertEqual(routine_eval.judge_state([skipped], False), "skipped by the harness")
        self.assertEqual(routine_eval.judge_state([{"judge": None}], False), "no judge result")
        self.assertEqual(routine_eval.judge_state([ran], True),
                         "turned off (pairwise fixture, --no-judge)")
        self.assertEqual(routine_eval.judge_state(
            [{"aggregate": {"judge": {"status": "skipped"}}}], False), "skipped by the harness")

    def test_printed_output_never_carries_url_userinfo_or_control_characters(self):
        lines = routine_eval.tail_lines(
            "fatal: https://user:tok3n@example.com/x.git refused\x1b[31m\n\n")
        self.assertEqual(lines, ["fatal: https://<redacted>@example.com/x.git refused[31m"])


class RunnerTests(unittest.TestCase):

    def test_a_run_past_its_timeout_is_stopped_by_the_reviewed_group_stop(self):
        proc = mock.MagicMock(pid=424242)
        proc.wait.side_effect = subprocess.TimeoutExpired("run_eval", 1)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(routine_eval.subprocess, "Popen", return_value=proc) as popen, \
                mock.patch("probe_model_defaults._stop") as stop, \
                mock.patch("os.killpg") as killpg, mock.patch("os.kill") as kill:
            code = routine_eval.Runner().run_eval(["python3", "harness/run_eval.py"],
                                                  cwd=Path(tmp), timeout=5,
                                                  log=Path(tmp) / "log")
        self.assertIsNone(code)
        stop.assert_called_once_with(proc)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        killpg.assert_not_called()
        kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
