#!/usr/bin/env python3
"""The eval runner routine's EVAL STEPS, done mechanically (ADR 0010).

An eval fire used to cost the routine session ten or more model calls, most
of them mechanical (installing the pins, reading fixture.yaml, fetching the
sibling checkouts, running harness/run_eval.py, committing and pushing), and
a read of every mode's instructions. docs/routine/eval-runner-instructions.md
now has the session write the fire text, unchanged, to a file and run

    python3 scripts/routine_eval.py --payload <file>

from the skills-evals checkout at the instructions' own commit. This script
then does what the EVAL STEPS paragraph used to ask of the session:

1. Checks the payload strictly, and prints REFUSED on anything else: only
   mode (absent or "eval"), fixture (a committed fixture under evals/), arms
   (both, with, without, bare, in-situ), trials (1 to 3), run_id, and either
   one "model" or a "models" list of exactly two distinct roster ids. The
   payload is untrusted: no refusal echoes it.
2. Installs the harness pins exactly as .github/workflows/eval.yml's `eval`
   job installs them (read from that file with a YAML parser, so the two
   cannot drift), with `python3 -m pip install --user`.
3. Reads the fixture's fixture.yaml with yaml.safe_load. A top-level
   `context` mapping means --pairing in_place, after every sibling checkout
   is made full history with a current origin/main; `judge.mode: pairwise`
   means --no-judge; a guidance fixture gets --guidance and a skill fixture
   one --registry per harness/registries.yml entry it may read (the three
   public registries, and adam-agentskills-private only for a fixture whose
   `registry` is that repository), each detached at a fetched origin/main.
   arms bare is --pairing isolation --arm without_skill with no sibling
   fetch; in-situ is --arm in-situ.
4. Runs harness/run_eval.py once per model, in sequence (never both at
   once; see _wait_for_a_new_second), never retrying,
   into eval-results/<run id>/, with the run context flags and never
   --asserted-quiet. The nested-agent limit is 6 agent runs per model. Each
   run is stopped 40 minutes after its own start (RUN_STOP_S), and the k-th,
   counted from 0, starts only while the fire is younger than 40 minutes
   times k + 1 (`start_limit_s`), so a fire ends within 40 minutes per model
   plus setup.
5. Commits only the summary.json, report.md and transcripts/tool_trace.json
   files under eval-results/<run id>/ (never transcripts/raw.json) to
   claude/eval-<run id>, in skills-evals or, for the private registry, in
   the adam-agentskills-private checkout from its default branch; pushes it
   and verifies it with `git merge-base --is-ancestor`. Nothing is pushed
   when no summary.json was written.
6. Prints a compact report ending in `RESULT: ok|error|refused`.

Exit code 0 is ok, 1 an error, 2 a refusal. Every command is an argument
list; nothing from the payload reaches a shell.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parent

RUN_ID_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}")
MODEL_RE = re.compile(r"claude-[a-z0-9][a-z0-9.-]{0,62}")
FIXTURE_RE = re.compile(r"[A-Za-z0-9/_.-]{1,256}")
#: The payload's arms and what run_eval.py's --arm is for each.
ARMS = {"both": "both", "with": "with_skill", "without": "without_skill",
        "bare": "without_skill", "in-situ": "in-situ"}
PAYLOAD_KEYS = frozenset({"mode", "fixture", "arms", "trials", "run_id", "model", "models"})
REQUIRED_KEYS = ("fixture", "arms", "trials", "run_id")
MAX_TRIALS = 3
MAX_PAYLOAD_BYTES = 16 * 1024

#: The instructions' "Limits:" for eval mode, per model.
MAX_AGENT_RUNS_PER_MODEL = 6
#: Each run_eval.py command is stopped this long after its own start:
#: routine_deadlines.MODE_LIMITS["eval"], which is per model.
RUN_STOP_S = 40 * 60
#: A git command that talks to a remote, in the commit and push step.
NETWORK_TIMEOUT_S = 120
LOCAL_TIMEOUT_S = 60

EVAL_WORKFLOW = Path(".github/workflows/eval.yml")
EVAL_JOB = "eval"
PIN_STEP = "Install harness dependencies"
PIN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9][A-Za-z0-9.]*")
REGISTRIES_FILE = Path("harness/registries.yml")
RUN_EVAL = "harness/run_eval.py"
RESULTS_ROOT = "eval-results"

PUBLIC_REGISTRIES = ("adam-agentskills", "cms-platform", "adamdaniel.ai")
PRIVATE_REGISTRY = "adam-agentskills-private"
PRIVATE_REGISTRY_URL = "https://github.com/Adam-S-Daniel/adam-agentskills-private"
GUIDANCE_CHECKOUT = "_agent-guidance"
#: The routine's cloned repositories beside skills-evals (the RULES list).
SIBLINGS = ("_agent-guidance", "adam-agentskills", "adam-agentskills-private",
            "cms-platform", "adamdaniel.ai", "wsl-automation", "repo-settings")
REPOSITORY = {"skills-evals": "Adam-S-Daniel/skills-evals",
              PRIVATE_REGISTRY: "Adam-S-Daniel/adam-agentskills-private"}
BRANCH_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}")
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
TRIAL_DIR_RE = re.compile(r"trial-[0-9]+")
GUARD_TAIL_LINES = 12
LINE_CAP = 300


class Refused(Exception):
    """The payload asks for something an eval fire may not."""


class Failed(Exception):
    """A step failed; `tail` is the failing command's last output lines."""

    def __init__(self, reason: str, tail: list[str] | None = None):
        super().__init__(reason)
        self.tail = tail or []


@dataclass(frozen=True)
class Payload:
    fixture: str
    arms: str
    trials: int
    run_id: str
    #: (None,) for the roster default, else one or two model ids in order.
    models: tuple


@dataclass(frozen=True)
class Fixture:
    path: str
    guidance: bool
    in_place: bool
    pairwise: bool
    private: bool
    #: Agent arms one run_eval.py command starts per trial.
    arm_count: int


@dataclass
class Run:
    model: str | None
    argv: list
    code: int | None = None
    started: bool = False
    wall_s: float = 0.0
    summaries: list = field(default_factory=list)
    log: Path | None = None
    #: How old the fire may be when this run starts (`start_limit_s`).
    start_limit_s: int = 0


def start_limit_s(index: int) -> int:
    """How old the fire may be when its `index`-th run_eval.py command
    (counted from 0) starts: one RUN_STOP_S for each run up to and including
    it, so a run that starts never ends past RUN_STOP_S per model."""
    return RUN_STOP_S * (index + 1)


# ---------------------------------------------------------------------------
# The payload.

def _unique_object(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError("duplicate key")
        seen[key] = value
    return seen


def _no_constant(_name):
    raise ValueError("non-finite number")


def load_payload(path: Path) -> Payload:
    try:
        raw = path.read_bytes()
    except OSError:
        raise Failed("the payload file cannot be read") from None
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise Refused(f"the payload is over {MAX_PAYLOAD_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
        doc = json.loads(text, object_pairs_hook=_unique_object,
                         parse_constant=_no_constant)
    except (UnicodeDecodeError, ValueError):
        raise Refused("the payload is not one JSON object with unique keys") from None
    return validate_payload(doc)


def validate_payload(doc) -> Payload:
    """The EVAL mode payload rule, strictly. Refusals are fixed text naming
    only this script's own key names, never a value the payload sent."""
    if not isinstance(doc, dict):
        raise Refused("the payload is not a JSON object")
    if "mode" in doc and doc["mode"] != "eval":
        raise Refused('"mode" is not "eval": this script runs eval mode only')
    if set(doc) - PAYLOAD_KEYS:
        raise Refused("the payload has a key an eval payload may not carry")
    for key in REQUIRED_KEYS:
        if key not in doc:
            raise Refused(f'the payload has no "{key}"')
    fixture = doc["fixture"]
    if not (isinstance(fixture, str) and FIXTURE_RE.fullmatch(fixture)
            and fixture.startswith("evals/")
            and all(part not in ("", ".", "..") for part in fixture.split("/"))):
        raise Refused('"fixture" is not a fixture path under evals/')
    arms = doc["arms"]
    if not isinstance(arms, str) or arms not in ARMS:
        raise Refused('"arms" is not one of ' + ", ".join(ARMS))
    trials = doc["trials"]
    if type(trials) is not int or not 1 <= trials <= MAX_TRIALS:
        raise Refused(f'"trials" is not an integer from 1 to {MAX_TRIALS}')
    run_id = doc["run_id"]
    if not (isinstance(run_id, str) and RUN_ID_RE.fullmatch(run_id)):
        raise Refused('"run_id" does not match ' + RUN_ID_RE.pattern)
    if "model" in doc and "models" in doc:
        raise Refused('the payload has both "model" and "models"')
    if "model" in doc:
        models = (_model(doc["model"], '"model"'),)
    elif "models" in doc:
        listed = doc["models"]
        if not isinstance(listed, list) or len(listed) != 2:
            raise Refused('"models" is not a list of exactly two model ids')
        models = tuple(_model(m, '"models"') for m in listed)
        if models[0] == models[1]:
            raise Refused('"models" names one model twice')
    else:
        models = (None,)
    return Payload(fixture, arms, trials, run_id, models)


def _model(value, where: str) -> str:
    if not (isinstance(value, str) and MODEL_RE.fullmatch(value)):
        raise Refused(f"{where} holds a value that does not match {MODEL_RE.pattern}")
    return value


# ---------------------------------------------------------------------------
# The fixture and the checkout's own files.

def _importable_scripts() -> None:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))


def _yaml():
    try:
        import yaml  # noqa: PLC0415 - reported as a step failure, not a crash
    except ImportError:
        raise Failed("PyYAML is not importable, so eval.yml and fixture.yaml "
                     "cannot be read") from None
    return yaml


def load_fixture(checkout: Path, payload: Payload) -> Fixture:
    """The facts the run_eval.py command depends on, from a committed
    fixture.yaml read with yaml.safe_load; a fixture that is not committed,
    or arms the fixture cannot take, are refused."""
    _importable_scripts()
    import plan_scheduled_evals  # noqa: PLC0415 - the fire workflow's own check

    try:
        committed = plan_scheduled_evals.committed_fixtures(checkout)
        plan_scheduled_evals.validate_fixture(payload.fixture, committed)
    except ValueError:
        raise Refused('"fixture" names no committed fixture on this checkout') from None
    except (OSError, subprocess.CalledProcessError):
        raise Failed("git cannot list this checkout's committed fixtures") from None
    yaml = _yaml()
    try:
        doc = yaml.safe_load((checkout / payload.fixture / "fixture.yaml")
                             .read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        raise Failed("the fixture's fixture.yaml cannot be read as YAML") from None
    if not isinstance(doc, dict):
        raise Failed("the fixture's fixture.yaml is not a mapping")
    guidance = doc.get("subject", "skill") == "guidance"
    judge = doc.get("judge")
    mode = judge.get("mode") if isinstance(judge, dict) else None
    pairwise = isinstance(mode, str) and mode.strip().casefold() == "pairwise"
    if payload.arms == "in-situ" and not guidance:
        raise Refused('"arms" is in-situ but the fixture is not a guidance fixture')
    if payload.arms == "both" and guidance:
        # Every arm the fixture declares, or run_eval.py's default pair.
        declared = doc.get("arms")
        arm_count = len(declared) if isinstance(declared, dict) and declared else 2
    elif payload.arms in ("both", "in-situ"):
        arm_count = 2
    else:
        arm_count = 1
    fixture = Fixture(path=payload.fixture, guidance=guidance,
                      in_place=isinstance(doc.get("context"), dict),
                      pairwise=pairwise,
                      private=doc.get("registry") == PRIVATE_REGISTRY_URL,
                      arm_count=arm_count)
    runs = fixture.arm_count * payload.trials
    if runs > MAX_AGENT_RUNS_PER_MODEL:
        raise Refused(f"the fire would start {runs} agent runs per model, over the "
                      f"limit of {MAX_AGENT_RUNS_PER_MODEL}")
    return fixture


def harness_pins(checkout: Path) -> list[str]:
    """The pip pins eval.yml's `eval` job installs in its `Install harness
    dependencies` step, parsed from the workflow with a YAML parser."""
    yaml = _yaml()
    try:
        doc = yaml.safe_load((checkout / EVAL_WORKFLOW).read_text(encoding="utf-8"))
        steps = doc["jobs"][EVAL_JOB]["steps"]
        [step] = [s for s in steps if isinstance(s, dict) and s.get("name") == PIN_STEP]
        argv = shlex.split(step["run"])
    except (OSError, UnicodeDecodeError, yaml.YAMLError, KeyError, TypeError, ValueError):
        raise Failed(f"cannot read the harness pins from {EVAL_WORKFLOW}") from None
    if argv[:2] != ["pip", "install"] or len(argv) < 3 \
            or not all(PIN_RE.fullmatch(pin) for pin in argv[2:]):
        raise Failed(f"{EVAL_WORKFLOW}'s harness pins are not one `pip install` "
                     "of exact pins")
    return argv[2:]


def registry_names(checkout: Path, fixture: Fixture) -> list[str]:
    """harness/registries.yml's names, in its order, limited to the ones an
    eval fire may read."""
    yaml = _yaml()
    try:
        doc = yaml.safe_load((checkout / REGISTRIES_FILE).read_text(encoding="utf-8"))
        names = [entry["name"] for entry in doc["registries"]]
    except (OSError, UnicodeDecodeError, yaml.YAMLError, KeyError, TypeError):
        raise Failed(f"cannot read {REGISTRIES_FILE}") from None
    allowed = set(PUBLIC_REGISTRIES) | ({PRIVATE_REGISTRY} if fixture.private else set())
    return [name for name in names if name in allowed]


# ---------------------------------------------------------------------------
# Commands.

class Runner:
    """Starts the commands; tests substitute a fake with the same methods."""

    def run(self, argv: list[str], *, cwd: Path | None = None,
            timeout: float | None = None) -> tuple[int | None, str]:
        """(exit code or None on a timeout, combined output)."""
        try:
            done = subprocess.run(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            return None, _text(exc.output)
        except OSError as exc:
            return 127, type(exc).__name__
        return done.returncode, _text(done.stdout)

    def run_eval(self, argv: list[str], *, cwd: Path, timeout: float,
                 log: Path) -> int | None:
        """run_eval.py in its own session, output to `log`; at `timeout` the
        whole group is stopped (SIGTERM, then SIGKILL) and None returned."""
        with open(log, "ab") as sink:
            try:
                proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                        stdout=sink, stderr=subprocess.STDOUT,
                                        start_new_session=True)
            except OSError as exc:
                sink.write(f"cannot start run_eval.py: {type(exc).__name__}\n".encode())
                return 127
            try:
                return proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _importable_scripts()
                # The reviewed group stop: it refuses an unsafe pid itself.
                from probe_model_defaults import _stop  # noqa: PLC0415
                _stop(proc)
                return None


def _text(data) -> str:
    if data is None:
        return ""
    return data.decode("utf-8", "replace") if isinstance(data, bytes) else data


_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/@\s]+@")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def tail_lines(text: str, count: int = GUARD_TAIL_LINES) -> list[str]:
    """The last `count` non-empty lines, each without control characters or
    URL userinfo and cut at LINE_CAP characters."""
    lines = [_USERINFO.sub(r"\1<redacted>@", _CONTROL.sub("", line)).strip()
             for line in text.splitlines()]
    return [line[:LINE_CAP] for line in lines if line][-count:]


class Steps:
    """One fire's commands, against its clock and deadline."""

    def __init__(self, runner, checkout: Path, siblings: Path, logs: Path,
                 clock, start: float):
        self.runner, self.checkout, self.siblings = runner, checkout, siblings
        self.logs, self.clock, self.start = logs, clock, start
        self.fetched: set[Path] = set()
        self.notes: list[str] = []

    def setup_left(self) -> float:
        """The time left to the first run's start limit: setup that runs
        past it leaves the first model no run."""
        return max(1.0, start_limit_s(0) - (self.clock() - self.start))

    def cmd(self, argv: list[str], what: str, *, cwd: Path | None = None,
            timeout: float | None = None) -> str:
        code, out = self.runner.run(argv, cwd=cwd,
                                    timeout=self.setup_left() if timeout is None else timeout)
        with open(self.logs / "setup.log", "a", encoding="utf-8") as log:
            log.write(f"$ {shlex.join(argv)}\n{out}\n")
        if code != 0:
            why = "timed out" if code is None else f"exited {code}"
            raise Failed(f"{what} {why}", tail_lines(out, 8))
        return out

    def git(self, repo: Path, *args: str, what: str, timeout: float | None = None) -> str:
        return self.cmd(["git", "-C", str(repo), *args], what, timeout=timeout)

    def install_pins(self, python: str) -> list[str]:
        pins = harness_pins(self.checkout)
        self.cmd([python, "-m", "pip", "install", "--user", *pins],
                 "installing the harness pins", cwd=self.checkout)
        return pins

    def clone(self, name: str) -> Path | None:
        path = self.siblings / name
        return path if (path / ".git").exists() else None

    def fetch_main(self, repo: Path) -> None:
        if repo not in self.fetched:
            self.git(repo, "fetch", "origin", "main", what=f"git fetch in {repo.name}")
            self.fetched.add(repo)

    def unshallow_siblings(self) -> None:
        """Every sibling checkout full history with a current origin/main:
        the harness reads each context repository at a pinned revision from
        the clone of its name beside skills-evals."""
        for name in SIBLINGS:
            repo = self.clone(name)
            if repo is None:
                continue
            shallow = self.git(repo, "rev-parse", "--is-shallow-repository",
                               what=f"git rev-parse in {name}").strip()
            if shallow == "true":
                self.git(repo, "fetch", "--unshallow", "origin",
                         what=f"git fetch --unshallow in {name}")
            self.fetch_main(repo)

    def detach_registries(self, names: list[str]) -> list[tuple[str, Path]]:
        """Each registry clone the run reads, detached at a fetched
        origin/main; a clone that is not there is noted and left out."""
        found = []
        for name in names:
            repo = self.clone(name)
            if repo is None:
                self.notes.append(f"registry clone {name} is not checked out")
                continue
            self.fetch_main(repo)
            self.git(repo, "checkout", "--quiet", "--detach", "origin/main",
                     what=f"git checkout --detach origin/main in {name}")
            found.append((name, repo))
        return found


def run_eval_argv(python: str, payload: Payload, fixture: Fixture, model: str | None,
                  guidance: Path | None, registries: list[tuple[str, Path]]) -> list[str]:
    """One run_eval.py command, run from the skills-evals root."""
    argv = [python, RUN_EVAL, fixture.path, "--arm", ARMS[payload.arms],
            "--trials", str(payload.trials)]
    if fixture.guidance:
        argv += ["--guidance", str(guidance)]
    else:
        for name, repo in registries:
            argv += ["--registry", f"{name}={repo}"]
    if payload.arms == "bare":
        argv += ["--pairing", "isolation"]
    elif fixture.in_place:
        argv += ["--pairing", "in_place"]
    if model is not None:
        argv += ["--model", model]
    if fixture.pairwise:
        argv.append("--no-judge")
    argv += ["--results-dir", f"{RESULTS_ROOT}/{payload.run_id}",
             "--run-billing", "subscription", "--run-runner", "routine",
             "--run-location", "cloud", "--run-id", payload.run_id]
    return argv


# ---------------------------------------------------------------------------
# Results.

def summary_paths(results: Path) -> set[Path]:
    found = set()
    for top, dirs, files in os.walk(results, followlinks=False):
        found |= {Path(top) / name for name in files
                  if name == "summary.json" and (Path(top) / name).is_file()
                  and not (Path(top) / name).is_symlink()}
    return found


def result_files(results: Path) -> tuple[list[str], int]:
    """(the files to commit, relative to `results`, sorted; how many were
    left out). Only regular files the ingest accepts: summary.json,
    report.md and transcripts/tool_trace.json. transcripts/raw.json can
    hold credentials and is never committed."""
    keep, left_out = [], 0
    for top, dirs, files in os.walk(results, followlinks=False):
        for name in files:
            path = Path(top) / name
            rel = path.relative_to(results)
            wanted = (name in ("summary.json", "report.md")
                      or (name == "tool_trace.json" and rel.parent.name == "transcripts"))
            if wanted and path.is_file() and not path.is_symlink():
                keep.append(rel.as_posix())
            else:
                left_out += 1
    return sorted(keep), left_out


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _count(value) -> bool:
    return type(value) is int and value >= 0


def arm_result(doc: dict) -> str:
    """One arm's pass/fail as counts: never a check's text."""
    arm = doc.get("arm")
    name = arm if isinstance(arm, str) and NAME_RE.fullmatch(arm) else "arm"
    aggregate = doc.get("aggregate")
    if isinstance(aggregate, dict):
        objective = aggregate.get("objective")
        errors = doc.get("errors")
        extra = f", {errors} errored" if _count(errors) and errors else ""
        if isinstance(objective, dict) and all(
                _count(objective.get(k)) for k in ("passed", "total", "n")):
            return (f"{name} {objective['passed']}/{objective['total']} checks over "
                    f"{objective['n']} scored trial(s){extra}")
        return f"{name} no scored trial{extra}"
    error = doc.get("error")
    if error:
        kind = error.get("type") if isinstance(error, dict) else None
        kind = kind if isinstance(kind, str) and NAME_RE.fullmatch(kind) else "error"
        return f"{name} error ({kind})"
    checks = doc.get("objective_checks")
    checks = checks if isinstance(checks, list) else []
    passed = sum(1 for c in checks if isinstance(c, dict) and c.get("passed") is True)
    verdict = "pass" if checks and passed == len(checks) else "fail"
    return f"{name} {verdict} ({passed}/{len(checks)} checks)"


def judge_state(docs: list[dict], turned_off: bool) -> str:
    if turned_off:
        return "turned off (pairwise fixture, --no-judge)"
    blocks = []
    for doc in docs:
        aggregate = doc.get("aggregate")
        blocks.append(aggregate.get("judge") if isinstance(aggregate, dict)
                      else doc.get("judge"))
    if any(isinstance(b, dict) and b.get("status") != "skipped" for b in blocks):
        return "ran"
    if any(isinstance(b, dict) and b.get("status") == "skipped" for b in blocks):
        return "skipped by the harness"
    return "no judge result"


def arm_docs(paths: list[Path]) -> list[dict]:
    """The arm-level summaries among `paths` (not a trial-<k> one)."""
    docs = []
    for path in sorted(paths):
        if TRIAL_DIR_RE.fullmatch(path.parent.name):
            continue
        doc = _read_json(path)
        if isinstance(doc, dict):
            docs.append(doc)
    return docs


# ---------------------------------------------------------------------------
# The branch.

def publish(steps: Steps, repo: Path, base: str, results: Path, run_id: str,
            files: list[str]) -> str:
    """Commit exactly `files` under eval-results/<run id>/ on a new branch
    claude/eval-<run id> from `base`, in a worktree of `repo`, push it and
    verify it on the remote. Returns the pushed commit."""
    branch = f"claude/eval-{run_id}"
    base_sha = steps.git(repo, "rev-parse", "--verify", f"{base}^{{commit}}",
                         what="git rev-parse of the base", timeout=LOCAL_TIMEOUT_S).strip()
    work = Path(tempfile.mkdtemp(prefix="skills-evals-routine-")) / "branch"
    steps.git(repo, "worktree", "add", "--quiet", "-b", branch, str(work), base_sha,
              what="git worktree add", timeout=LOCAL_TIMEOUT_S)
    try:
        paths = [f"{RESULTS_ROOT}/{run_id}/{rel}" for rel in files]
        try:
            for rel, path in zip(files, paths):
                (work / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(results / rel, work / path)
        except OSError as exc:
            raise Failed(f"cannot copy the results into the branch: {type(exc).__name__}") from None
        steps.git(work, "add", "--", *paths, what="git add", timeout=LOCAL_TIMEOUT_S)
        staged = steps.git(work, "diff", "--cached", "--name-only", "-z",
                           what="git diff --cached", timeout=LOCAL_TIMEOUT_S)
        if sorted(name for name in staged.split("\0") if name) != sorted(paths):
            raise Failed("the staged files are not exactly the results")
        steps.git(work, "commit", "--quiet", "-m", f"Eval results {run_id}",
                  what="git commit", timeout=LOCAL_TIMEOUT_S)
        sha = steps.git(work, "rev-parse", "HEAD", what="git rev-parse",
                        timeout=LOCAL_TIMEOUT_S).strip()
        if sha == base_sha:
            raise Failed("git commit made no commit")
        steps.git(work, "push", "--quiet", "origin", f"{sha}:refs/heads/{branch}",
                  what="git push", timeout=NETWORK_TIMEOUT_S)
        steps.git(work, "fetch", "--quiet", "origin",
                  f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
                  what="git fetch of the pushed branch", timeout=NETWORK_TIMEOUT_S)
        steps.git(work, "merge-base", "--is-ancestor", sha, f"refs/remotes/origin/{branch}",
                  what="git merge-base --is-ancestor", timeout=LOCAL_TIMEOUT_S)
        return sha
    finally:
        steps.runner.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                          str(work)], timeout=LOCAL_TIMEOUT_S)


def private_base(steps: Steps, repo: Path) -> str:
    """adam-agentskills-private's default branch, freshly fetched."""
    code, out = steps.runner.run(["git", "-C", str(repo), "symbolic-ref", "--quiet",
                                  "--short", "refs/remotes/origin/HEAD"],
                                 timeout=LOCAL_TIMEOUT_S)
    name = out.strip()[len("origin/"):] if code == 0 and out.strip().startswith("origin/") else ""
    if not name:
        listing = steps.git(repo, "ls-remote", "--symref", "origin", "HEAD",
                            what="git ls-remote in adam-agentskills-private",
                            timeout=NETWORK_TIMEOUT_S)
        match = re.search(r"^ref: refs/heads/(\S+)\tHEAD$", listing, re.M)
        name = match.group(1) if match else ""
    if not BRANCH_NAME_RE.fullmatch(name) or ".." in name:
        raise Failed("cannot tell adam-agentskills-private's default branch")
    steps.git(repo, "fetch", "--quiet", "origin",
              f"+refs/heads/{name}:refs/remotes/origin/{name}",
              what="git fetch in adam-agentskills-private", timeout=NETWORK_TIMEOUT_S)
    return f"refs/remotes/origin/{name}"


# ---------------------------------------------------------------------------
# The fire.

def _wait_for_a_new_second(after: datetime, wall, sleep) -> None:
    """run_eval.py names its run directory by the UTC second it reads after
    its imports, and one fire's commands share one results directory: a
    second command starts in a later second than the first one ended.

    That is also why the two never run at once. run_eval.py writes into an
    existing run directory without refusing, and its imports take about half
    a second on a cold bytecode cache, so two commands started a new second
    apart named the same directory in 10 of 20 timed trials (2026-11-06) and
    would overwrite each other's summaries."""
    mark = after.replace(microsecond=0)
    while wall().replace(microsecond=0) <= mark:
        sleep(0.05)


def fire(args, runner, clock, wall, sleep, python, err) -> tuple[list[str], str]:
    """Every step after the payload check. Returns (report lines, result)."""
    start = clock()
    lines: list[str] = []
    try:
        payload = load_payload(args.payload)
        checkout = args.checkout.resolve()
        siblings = (args.siblings or checkout.parent).resolve()
        fixture = load_fixture(checkout, payload)
    except Refused as exc:
        return [f"REFUSED: {exc}"], "refused"
    except Failed as exc:
        return [f"error: {exc}", *(f"  {line}" for line in exc.tail)], "error"

    lines += [f"fixture: {fixture.path}", f"arms: {payload.arms}",
              f"trials: {payload.trials}",
              "pairing: " + ("in_place" if fixture.in_place and payload.arms != "bare"
                             else "isolation")]
    logs = Path(tempfile.mkdtemp(prefix="skills-evals-routine-"))
    steps = Steps(runner, checkout, siblings, logs, clock, start)
    results = checkout / RESULTS_ROOT / payload.run_id
    runs = [Run(model=m, argv=[], start_limit_s=start_limit_s(index))
            for index, m in enumerate(payload.models)]
    errors: list[str] = []
    pushed = "none"
    try:
        private = steps.clone(PRIVATE_REGISTRY) if fixture.private else None
        if fixture.private and private is None:
            raise Failed("adam-agentskills-private is not cloned; a private skill's "
                         "results may go nowhere else")
        guidance = steps.clone(GUIDANCE_CHECKOUT) if fixture.guidance else None
        if fixture.guidance and guidance is None:
            raise Failed("the _agent-guidance checkout is missing")
        if results.exists() or results.is_symlink():
            raise Failed(f"{RESULTS_ROOT}/{payload.run_id}/ already exists; "
                         "a fire writes a fresh one")
        print("routine_eval: installing the harness pins", file=err, flush=True)
        steps.install_pins(python)
        if fixture.in_place and payload.arms != "bare":
            print("routine_eval: fetching the sibling checkouts", file=err, flush=True)
            steps.unshallow_siblings()
        registries = ([] if fixture.guidance
                      else steps.detach_registries(registry_names(checkout, fixture)))
        ended = None
        for index, run in enumerate(runs):
            run.argv = run_eval_argv(python, payload, fixture, run.model, guidance,
                                     registries)
            if clock() - start >= run.start_limit_s:
                continue
            if ended is not None:
                _wait_for_a_new_second(ended, wall, sleep)
            print(f"routine_eval: running run_eval.py ({run.model or 'roster default'})",
                  file=err, flush=True)
            before = summary_paths(results)
            run.log = logs / f"run-eval-{index + 1}.log"
            run.started = True
            began = clock()
            run.code = runner.run_eval(run.argv, cwd=checkout, timeout=RUN_STOP_S,
                                       log=run.log)
            run.wall_s = clock() - began
            ended = wall()
            run.summaries = sorted(summary_paths(results) - before)
        files, left_out = result_files(results) if results.is_dir() else ([], 0)
        if not any(Path(rel).name == "summary.json" for rel in files):
            raise Failed("the harness wrote no summary.json, so nothing was pushed")
        print("routine_eval: committing and pushing the results", file=err, flush=True)
        if private is not None:
            repo, base, where = private, private_base(steps, private), REPOSITORY[PRIVATE_REGISTRY]
        else:
            repo, base, where = checkout, "HEAD", REPOSITORY["skills-evals"]
        sha = publish(steps, repo, base, results, payload.run_id, files)
        pushed = (f"claude/eval-{payload.run_id} in {where} at {sha}, {len(files)} file(s)"
                  + (f", {left_out} other file(s) left out" if left_out else ""))
    except Failed as exc:
        errors.append(str(exc))
        errors += [f"  {line}" for line in exc.tail]

    for run in runs:
        lines += run_lines(run, fixture)
    if pushed != "none":
        # Pushed and verified, and the report has read its summaries: the
        # files left out (raw.json) stay unpushed by design, and an untracked
        # results tree would only draw the session's stop hook into an extra
        # turn about uncommitted files.
        shutil.rmtree(results, ignore_errors=True)
    lines += [f"note: {note}" for note in steps.notes]
    lines.append(f"branch pushed: {pushed}")
    lines += [f"error: {line}" if not line.startswith("  ") else line for line in errors]
    lines.append(f"wall time: {clock() - start:.0f}s")
    ok = (not errors and all(run.started and run.code == 0 for run in runs))
    return lines, "ok" if ok else "error"


def run_lines(run: Run, fixture: Fixture) -> list[str]:
    label = f"run {run.model or 'roster default'}"
    if not run.started:
        if run.argv:
            return [f"{label}: not started (past the {run.start_limit_s // 60}-minute limit)"]
        return [f"{label}: not started"]
    exit_text = (f"stopped at the {RUN_STOP_S // 60}-minute hard stop"
                 if run.code is None else f"exit {run.code}")
    docs = arm_docs(run.summaries)
    arms = ", ".join(arm_result(doc) for doc in docs) or "no arm summary"
    lines = [f"{label}: {exit_text}, wall {run.wall_s:.0f}s, judge "
             f"{judge_state(docs, fixture.pairwise)}; {arms}"]
    if run.code != 0 and run.log is not None:
        if fixture.private:
            lines.append(f"  guard text withheld for a private skill; log: {run.log}")
        else:
            try:
                text = run.log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            lines.append(f"  guard text (log: {run.log}):")
            lines += [f"    {line}" for line in tail_lines(text)]
    return lines


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Run one eval-mode routine fire.")
    parser.add_argument("--payload", type=Path, required=True,
                        help="a file holding the fire text, unchanged")
    parser.add_argument("--checkout", type=Path, default=REPO_ROOT,
                        help="the skills-evals checkout (default: this script's)")
    parser.add_argument("--siblings", type=Path, default=None,
                        help="the directory holding the other cloned repositories "
                             "(default: the checkout's parent)")
    return parser.parse_args(argv)


def main(argv=None, *, runner=None, clock=time.monotonic,
         wall=lambda: datetime.now(timezone.utc), sleep=time.sleep,
         python=sys.executable, out=None, err=None) -> int:
    args = parse_args(argv)
    try:
        lines, result = fire(args, runner or Runner(), clock, wall, sleep, python,
                             err or sys.stderr)
    except Exception as exc:  # noqa: BLE001 - the report must still end in RESULT
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        lines = [f"error: routine_eval.py stopped on {type(exc).__name__} at "
                 f"{Path(frame.filename).name}:{frame.lineno}"]
        result = "error"
    stream = out or sys.stdout
    for line in [*lines, f"RESULT: {result}"]:
        print(line, file=stream)
    stream.flush()
    return {"ok": 0, "error": 1, "refused": 2}[result]


if __name__ == "__main__":
    raise SystemExit(main())
