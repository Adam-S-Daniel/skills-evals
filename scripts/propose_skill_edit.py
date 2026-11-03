#!/usr/bin/env python3
"""Propose one SKILL.md edit, measure it against held-out fixtures, keep the record.

Part of https://github.com/Adam-S-Daniel/skills-evals/issues/71 (the smallest
slice) and https://github.com/Adam-S-Daniel/skills-evals/issues/232. The
decision record is docs/decisions/0005-improvement-loop-reuses-skill-creator.md.

    python3 scripts/propose_skill_edit.py <skill> \\
        --registry adam-agentskills=PATH [--ref REF] [--trials 3] \\
        [--rotation K] [--min-gain .10] [--holdout FIXTURE] \\
        [--trigger-eval-set FILE] [--skill-creator DIR] [--num-workers 1] \\
        [--results-dir DIR] [--no-judge] [--dry-run]
    python3 scripts/propose_skill_edit.py <skill> --trigger-only \\
        --trigger-eval-set evals/<skill>/trigger-eval-set.json \\
        --registry adam-agentskills=PATH [--ref REF] [--skill-creator DIR] \\
        [--results-dir DIR] [--dry-run]
    python3 scripts/propose_skill_edit.py <skill> --trim-description \\
        --registry adam-agentskills=PATH [--ref REF] [--trials 3] \\
        [--results-dir DIR] [--dry-run]

WHAT IT DOES, in order:

 1. Refuses (exit 2, "needs more fixtures") a skill with fewer than three
    nested fixtures under `evals/<skill>/`: one held-out fixture beside one
    train fixture is a coin toss, not a split.
 2. Splits them deterministically: the fixtures in name order, validation is
    the one at index `rotation % n`, train is the rest. `rotation` defaults to
    the number of records already written for this skill, so consecutive
    runs hold out a different fixture. `--holdout` removes one fixed fixture
    from both train and the rotating validation population on every run.
 3. Builds two scratch registries from `git archive <ref>` of the local
    registry checkout: no `.git`, so nothing in them has a push path.
 4. HELD-OUT FIRST, then BASELINE: `scripts/local_eval.py evals/<skill>
    --arm with_skill --trials N --fixture <name>` against the first scratch
    copy, one fixture per call, so each is measured once. The rotating
    validation fixture is measured before any other. One that passes every
    objective check in every trial (`saturated`) can only show a regression,
    never that an edit carries over to a task the proposer did not see, so it
    is refused and the next fixture in rotation order is measured as the
    validation instead; a candidate whose fixture-derived trigger set would
    be unusable is passed over unmeasured. When every candidate passes
    everything, or the chosen one errors, the run stops here, before any
    train fixture is measured. Then the train fixtures and the fixed
    holdout are measured.
 4b. EARLY STOP: a baseline train objective that leaves less than `--min-gain`
    to gain, with a judge mean that cannot make it up (missing, or within
    `--min-gain` of 10), is rejected here with a "no train headroom" record,
    before any trigger, proposal or candidate call; add harder fixtures.
 5. TRIGGER HALF, from Anthropic's skill-creator plugin: its
    `scripts/run_loop.py` description-optimization loop (stratified 60/40
    train/held-out split of a should/should-not-trigger query set, 3 runs per
    query, best description picked by HELD-OUT score). The validation
    fixture's prompt and the fixed holdout's prompt are never in that set,
    and a query appears in it once. A fixture-derived set whose train or
    held-out split (by skill-creator's own split arithmetic) lacks a
    should-trigger or should-not-trigger query is refused before any model
    call, with a `trigger-set-unusable` record; a reviewed
    `--trigger-eval-set` is run anyway and its split problems recorded.
    A reviewed set lives beside the skill's fixtures as
    `evals/<skill>/trigger-eval-set.json` (writing-adrs ships one) and is
    passed explicitly; it must be a JSON list of exactly
    `{query: string, should_trigger: boolean}` objects.
    `--num-workers` must be 1 (the default): skill-creator's parallel
    workers share one project directory and undercount triggers.
    Scratch project settings disable the archived registry plugins that
    provide the skill, leaving the operator's login available.
 6. BODY HALF: one proposal call (roster judge model, no tools) returning
    `{rationale, unified_diff}` for SKILL.md's body, fed the train fixtures'
    failed checks and transcripts. A diff naming any other file, or touching
    the frontmatter, is rejected before anything else runs.
 7. CANDIDATE: both halves applied to the second scratch copy and measured
    through the same local_eval invocation.
 8. ACCEPT only if validation held (objective pass rate not lower; judge mean
    not lower by more than 0.5) AND train improved (objective pass rate
    higher by at least `--min-gain` (default .10), or equal with judge mean
    higher by at least ten times that gain). A fixed holdout must not regress
    on either score. This is a conservative heuristic, not a significance test.
    TOKENS (ADR 0005 amendment 2) sit beside that quality rule: each fixture's
    tokens are the mean per trial of the four token counts summed over every
    model in the CLI's `modelUsage` (subagents, sidechains and compaction
    included; ADR 0005's 2026-10-07 addendum), summed over the measured
    fixtures. Baseline and candidate must be measured on the same basis
    (`tokens_basis`). A fixture without token data on either side makes the
    run inconclusive (rejected), never a pass. A candidate that costs more
    tokens than the baseline (`TOKEN_INCREASE_TOLERANCE`, 0: any rise)
    without a quality gain is not accepted; a gain at a higher cost is
    accepted and the rise recorded in the reasons.
 9. Writes `<results>/improvements/<skill>/<ts>.json` always, `<ts>.patch`
    whenever a candidate existed, and `<ts>.pr-body.md` on accept. Nothing is
    pushed and no pull request is opened: a human reads the record first.

`--dry-run` prints the plan and makes no model call and no write.

TRIGGER-ONLY MODE (`--trigger-only`; skills-evals#662, Adam 2026-11-03:
"New fire mode runs only skill-creator's description loop"). For a rarely
used skill whose task fixtures leave no headroom, or that has few or none:
steps 1-4b and 6-8 are skipped and only step 5 runs, on the reviewed
`--trigger-eval-set` (required; `--holdout`, `--rotation`, `--no-judge`,
`--trials` and `--min-gain` are refused, since nothing would read them).
The set must hold at least `TRIGGER_ONLY_MIN_CLASS` distinct queries of each
class with both classes in both splits, or the run is refused. The registry
is the fixtures' (all must agree) or, with none, adam-agentskills; the loop's
model is the first fixture's arm model or the roster's default. ACCEPT only
when skill-creator's best description differs from the original (its
`history[0]`), the held-out pass rate rose by at least
`TRIGGER_ONLY_MIN_GAIN` on the same held-out queries, and no fewer
should-not-trigger queries (train and held-out) passed. The record
(`mode: trigger-only`, a `trigger_only` block of both entries' counts) and the
files are written where step 9 writes them; scripts/improve_gate.py checks
the counts again before any pull request.

DESCRIPTION TRIM MODE (`--trim-description`; skills-evals#687). A fixed
chore, not an improvement: adam-agentskills caps a skill's description at
TRIM_MAX_CHARS (400) characters for the session's skill listing, and an
eval-protected skill over the cap carries a `length-limit` waiver until this
mode shortens it. Steps 2, 4b, 5 and 6 are replaced: `--holdout`,
`--rotation`, `--min-gain`, `--no-judge`, `--trigger-eval-set`,
`--skill-creator` and `--trigger-only` are refused, since nothing would read them (the judge never
runs: the rule reads objective checks only). The skill needs at least
MIN_FIXTURES nested fixtures, as step 1. A description already within the
cap is rejected with no model call ("already within the cap"). Otherwise ONE
proposal call (the roster's judge model, no tools, `Runner.propose`) asks for
a replacement of at most TRIM_MAX_CHARS characters that keeps every trigger
phrase and situation and every "not for" or "use X instead" boundary, as the
reply `{"description": "..."}` and nothing else (`parse_trim_reply`). A reply
of any other shape, with a line break, empty or over the cap after
whitespace is collapsed, or equal to the current description is an
`invalid-proposal` record (exit 1), never measured. The candidate changes
only the description (`set_description`); baseline and candidate are then
measured on EVERY fixture of the skill with the same `local_eval` call as
step 7 (`with_skill`, `--trials`, no judge). ACCEPT (`decide_trim`) only
when no fixture errored, every fixture ran the same checks on both sides,
the candidate's objective passes summed over all fixtures and trials are at
least the baseline's (TRIM_TOLERANCE_CHECKS, 0), and no single fixture lost
more than TRIM_FIXTURE_DROP_CHECKS (1) of its passes. Aggregate
non-inferiority rather than per-fixture strictness: with three trials a
fixture's summed checks move by one on noise alone, and strict per-fixture
equality on all of a skill's fixtures would reject most faithful trims for a
flake; the per-fixture bound still refuses a trim that loses a fixture's
behavior and buys it back elsewhere. The record (`mode: trim`, a `trim` block
of both sides' per-fixture counts) and the files are written where step 9
writes them; scripts/improve_gate.py re-derives the decision from the counts
before any pull request, and removes the skill's `length-limit` waiver in
the same registry change.

EVERY MODEL CALL GOES THROUGH A `Runner` (the three methods below), so the
tests drive the whole pipeline offline with a fake. This is a LOCAL exhibit
under ADR 0002 decision 4: it runs under the operator's own login, its numbers
are not badge input, and it never runs in CI.

Exit codes: 0 accepted, 1 rejected (or nothing to measure), 2 refused or
errored before a decision could be taken.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import difflib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_DIR = REPO_ROOT / "harness"
EVALS_DIR = REPO_ROOT / "evals"
LOCAL_EVAL = REPO_ROOT / "scripts" / "local_eval.py"

sys.path.insert(0, str(HARNESS_DIR))
from cli_json import normalize_cli_result  # noqa: E402
import run_eval  # noqa: E402
import local_eval  # noqa: E402

MIN_FIXTURES = 3
DEFAULT_TRIALS = 3
DEFAULT_MIN_GAIN = 0.10
#: The judge may drop by at most this much on validation (#71 step 3).
JUDGE_TOLERANCE = 0.5
#: How much more total tokens a candidate may cost than the baseline, as a
#: fraction of the baseline, before it "costs more tokens". ADR 0005's
#: Token-aware acceptance addendum (2026-10-06) records "Keep as built":
#: quality first, tokens veto a candidate with no quality gain; any
#: increase counts.
TOKEN_INCREASE_TOLERANCE = 0.0
#: What a fixture's `tokens` measure, recorded as `tokens_basis` in every
#: record and every fixture's metrics. Since ADR 0005's 2026-10-07 addendum
#: ("Switch to total (Recommended)"): the four counts summed over every
#: model in `modelUsage`, so subagent, sidechain and compaction tokens
#: count. Metrics without a basis predate it and measured
#: `TOKENS_BASIS_LEGACY`: the main loop's `usage` alone.
TOKENS_BASIS = "model_usage_total"
TOKENS_BASIS_LEGACY = "usage_main_loop"
#: The four `usage` counts that make up the main loop's tokens (all of them,
#: cache reads and writes included; a trial missing any one is unknown).
#: Recorded as `main_loop_tokens`; no rule reads them.
TOKEN_USAGE_METRICS = ("input_tokens", "output_tokens",
                       "cache_creation_input_tokens", "cache_read_input_tokens")
#: skill-creator's own hard limit on a description (improve_description.py).
DESCRIPTION_MAX_CHARS = 1024
#: How much of one failing trial's final reply the proposal prompt carries.
TRANSCRIPT_EXCERPT_CHARS = 4000
#: The arm whose numbers a SKILL.md edit can move.
ARM = "with_skill"
#: skill-creator's held-out fraction, passed as run_loop's --holdout.
TRIGGER_HOLDOUT = 0.4
#: Trigger-only mode (skills-evals#662; Adam, 2026-11-03, "Build a
#: trigger-only improve fire"): the reviewed query set's file name under
#: evals/<skill>/, the held-out pass-rate gain the best description must
#: show over the original, and the fewest queries of each class the set may
#: hold (8 per class leaves skill-creator's 0.4 split at least 3 of each class
#: held out, 6 in all, so one query is never the whole margin).
TRIGGER_SET_FILE = "trigger-eval-set.json"
TRIGGER_ONLY_MIN_GAIN = 0.15
TRIGGER_ONLY_MIN_CLASS = 8
#: Description trim mode (skills-evals#687): adam-agentskills' description
#: cap (its scripts/skills_registries.yml `max_lengths`, which
#: scripts/check_skills.py measures as `len()` of the parsed value), the
#: summed objective passes the candidate may lose over all fixtures and
#: trials (0: no worse in aggregate), and the most one fixture may lose (1:
#: one check's noise across three trials). scripts/improve_gate.py mirrors
#: all three, and a test holds them equal.
TRIM_MAX_CHARS = 400
TRIM_TOLERANCE_CHECKS = 0
TRIM_FIXTURE_DROP_CHECKS = 1
#: The acceptance rule a trim record names (`trim.rule`), so a gate built for
#: another rule refuses the record rather than misread it.
TRIM_RULE = "aggregate-noninferior-per-fixture-drop-1"
#: Parallel `claude -p` calls in skill-creator's trigger eval: exactly one.
#: run_eval.py plants every worker's command file (`<skill>-skill-<uuid>`) in
#: the ONE project directory run_loop.py finds from its cwd, and counts a hit
#: only when the model picks that worker's own copy, so with N > 1 the model
#: sees N identical skills and a real trigger often scores as a miss. A
#: 2026-10-06 A/B on three writing-adrs positives: 7/9 triggers serial, 0/9
#: with 4 workers, 7/9 serial again. run_loop.py passes no per-worker
#: directory, so the only fix that leaves skill-creator unmodified is serial.
DEFAULT_NUM_WORKERS = 1
NUM_WORKERS_REFUSAL = (
    "--num-workers must be 1: skill-creator's parallel workers share one "
    "project directory, each sees every other worker's identical command file, "
    "and a trigger counts only when the model picks its own copy, so N > 1 "
    "undercounts triggers (ADR 0005, serial trigger eval addendum)")
#: What a trigger-loop usage record says about money: nothing is reported.
TRIGGER_COST_NOTE = ("skill-creator reports no tokens or cost: run_eval.py "
                     "stops reading each stream-json CLI call once it has a "
                     "verdict, and improve_description.py asks for text output")

EXIT_ACCEPTED, EXIT_REJECTED, EXIT_REFUSED = 0, 1, 2

#: Where skill-creator lives when nothing names it: the installed bundle that
#: `claude plugin install skill-creator@claude-plugins-official` records.
SKILL_CREATOR_PLUGIN_KEY = "skill-creator@claude-plugins-official"
SKILL_CREATOR_SUBDIR = Path("skills") / "skill-creator"


class Refusal(Exception):
    """Configuration or measurement problem: exit 2, no decision taken."""


class InvalidProposal(Exception):
    """The proposal broke a constraint; it is recorded and never measured."""


def check_launch_environment() -> None:
    """Refuse credential and provider settings before any model subprocess starts."""
    refused = local_eval.refused_env_names(os.environ)
    if refused:
        raise Refusal("refusing to run with " + ", ".join(refused) +
                      " set; unset them and use the interactive login")
    proxies = local_eval.proxy_userinfo_names(os.environ)
    if proxies:
        raise Refusal("refusing proxy URLs that embed credentials: " +
                      ", ".join(proxies))


@contextmanager
def guarded_environment():
    """A private launcher guards explicit and PATH-based CLI calls alike."""
    check_launch_environment()
    env = local_eval.child_environment(os.environ)
    with tempfile.TemporaryDirectory(prefix="skill-edit-guard-") as directory:
        guard_dir = Path(directory)
        try:
            local_eval.install_guard_launcher(guard_dir, environ=env)
        except local_eval.Refused as exc:
            raise Refusal(str(exc)) from exc
        try:
            yield env
        finally:
            # skill-creator can swallow an unsuccessful CLI launch and emit
            # valid JSON. The launcher's record takes precedence over it.
            refusals = local_eval.guard_refusals(guard_dir)
            if refusals:
                raise Refusal("launch-time settings guard refused: " +
                              str(refusals[0].get("message")))


# ---------------------------------------------------------------------------
# The runner: every step that can spend model budget, and nothing else.
# ---------------------------------------------------------------------------

class Runner:
    """The real thing. Tests substitute a fake with the same three methods."""

    def run_eval(self, argv: list[str]) -> int:
        """Run the guarded local exhibit wrapper; 2 means refusal."""
        return subprocess.run([sys.executable, str(LOCAL_EVAL), *argv],
                              check=False).returncode

    def run_description_loop(self, argv: list[str], *, cwd: Path,
                             skill_creator: Path) -> dict:
        """skill-creator's `scripts/run_loop.py` with `argv`, run from
        `cwd` (its `find_project_root` writes a command file under the
        nearest `.claude/`, so `cwd` must be a scratch project), and its JSON
        stdout parsed. A `skill-creator` link to the plugin is planted in `cwd`."""
        # Run through a link to the plugin planted in the scratch project, so
        # the script path is a literal: the test suite's fork scan
        # (test_every_suite_forking_test_in_this_repo_stands_down_in_a_child)
        # can then prove this spawn is skill-creator and not the suite, which
        # it cannot for `-m` or a computed path. PYTHONPATH carries
        # skill-creator's `scripts` package, so its imports resolve as under
        # its documented `python -m scripts.run_loop`.
        with guarded_environment() as env:
            # Only this trusted plugin's import directory is carried.
            env["PYTHONPATH"] = str(skill_creator)
            link = Path(cwd) / "skill-creator"
            if not link.exists():
                link.symlink_to(skill_creator, target_is_directory=True)
            try:
                proc = subprocess.run([sys.executable, "skill-creator/scripts/run_loop.py", *argv],
                                      cwd=cwd, env=env, capture_output=True, text=True,
                                      check=False)
            except OSError as exc:
                raise Refusal(f"skill-creator run_loop could not run: {type(exc).__name__}") from exc
        if proc.returncode != 0:
            raise Refusal(f"skill-creator run_loop exited {proc.returncode}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise Refusal(f"skill-creator run_loop printed no JSON ({exc})") from exc

    #: The last proposal call's numbers (#572 part 1, 2026-11-02): calls,
    #: usd, input_tokens and output_tokens, copied by name from the CLI's
    #: JSON and type-checked, so no reply text or session id is ever kept.
    #: None until a call printed all four. The caller writes it to
    #: `$RESULTS/proposal-<ts>.json` for scripts/improve_cost.py.
    last_usage: dict | None = None

    def propose(self, prompt: str, model: str) -> str:
        """One headless call, no tools, prompt on stdin; the reply text."""
        self.last_usage = None
        try:
            with guarded_environment() as env:
                cmd = [env["CLAUDE_BIN"], "-p", "--output-format", "json",
                       "--permission-mode", "default", "--tools", "", "--model", model,
                       # The judge's isolation: no settings source, no MCP
                       # connector, no transcript (auto-memory is off in env).
                       *run_eval.judge.JUDGE_ISOLATION_FLAGS]
                proc = subprocess.run(cmd, input=prompt, capture_output=True,
                                      text=True, env=env, timeout=600, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Refusal(f"proposal call could not run: {type(exc).__name__}") from exc
        if proc.returncode != 0:
            raise Refusal(f"proposal call exited {proc.returncode}")
        try:
            result = normalize_cli_result(json.loads(proc.stdout))
            self.last_usage = proposal_usage(result)
            return result.get("result", "")
        except (ValueError, AttributeError) as exc:
            raise Refusal("proposal call printed no JSON result") from exc


def proposal_usage(result: dict) -> dict | None:
    """{calls, usd, input_tokens, output_tokens} of one `claude -p` result,
    numbers only, or None when any is missing or not a bounded number
    (scripts/improve_cost.py's bounds). Built field by field: the CLI object
    also carries the reply and a session id, which must never be written."""
    usage = result.get("usage") if isinstance(result, dict) else None
    usd = result.get("total_cost_usd") if isinstance(result, dict) else None
    tokens = [usage.get(name) if isinstance(usage, dict) else None
              for name in ("input_tokens", "output_tokens")]
    if isinstance(usd, bool) or not isinstance(usd, (int, float)) \
            or not math.isfinite(usd) or not 0 <= usd <= 1000:
        return None
    if any(isinstance(t, bool) or not isinstance(t, int) or not 0 <= t <= 10 ** 9
           for t in tokens):
        return None
    return {"calls": 1, "usd": usd, "input_tokens": tokens[0],
            "output_tokens": tokens[1]}


def write_proposal_usage(results: Path, ts: str, runner) -> None:
    """`<results>/proposal-<ts>.json` from `runner.last_usage`, when the
    runner kept one (test fakes need not). Beside runs/, never under it:
    local_eval requires each runs/<label>/ destination to be empty."""
    usage = getattr(runner, "last_usage", None)
    if isinstance(usage, dict):
        # Called from a `finally`: a failed write must never replace the
        # loop's own outcome or Refusal (#572 review, 2026-11-02). The cost
        # record then reads the proposal as null, the safe direction.
        try:
            (results / f"proposal-{ts}.json").write_text(
                json.dumps(usage) + "\n", encoding="utf-8")
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Fixtures, split, registry
# ---------------------------------------------------------------------------

def skill_fixtures(skill: str) -> list[str]:
    """The nested fixture names under `evals/<skill>/`, sorted."""
    run_eval._validate_skill_name(skill)
    return run_eval.nested_fixture_names(EVALS_DIR / skill)


def split_fixtures(fixtures: list[str], rotation: int,
                   holdout: str | None = None) -> tuple[list[str], str]:
    """(train, validation): validation is `sorted(fixtures)[rotation % n]`."""
    if len(fixtures) < MIN_FIXTURES:
        raise Refusal(f"needs more fixtures: {len(fixtures)} found, "
                      f"{MIN_FIXTURES} required (one held out, the rest trained on)")
    if holdout is not None and holdout not in fixtures:
        raise Refusal(f"--holdout {holdout!r} is not a nested fixture of this skill")
    ordered = sorted(f for f in fixtures if f != holdout)
    validation = ordered[rotation % len(ordered)]
    return [f for f in ordered if f != validation], validation


def validation_order(fixtures: list[str], rotation: int,
                     holdout: str | None = None) -> list[str]:
    """Every validation candidate, in the order the held-out screen tries
    them: `split_fixtures`'s pick first, then the rest in rotation order."""
    ordered = sorted(f for f in fixtures if f != holdout)
    return [ordered[(rotation + i) % len(ordered)] for i in range(len(ordered))]


def saturated(metrics: dict) -> bool:
    """Every objective check passed in every trial. Pure. Such a held-out
    fixture can catch a regression but can never show that an edit carries
    over to a task the proposer did not see (skills-evals ADR 0005's
    held-out screen addendum). The judge is not consulted: "passes every
    check" is the rule, and `decide` still guards the judge. An errored or
    unscored fixture is not saturated."""
    total = metrics.get("total")
    return (not metrics.get("error") and bool(total)
            and metrics.get("passed") == total)


def default_rotation(records_dir: Path) -> int:
    """How many records this skill already has: each run holds out the next
    fixture, and the same results directory always gives the same answer."""
    return len(list(records_dir.glob("*.json"))) if records_dir.is_dir() else 0


def load_fixtures(skill: str, names: list[str]) -> dict:
    out = {}
    for name in names:
        try:
            fixture = run_eval.load_fixture(EVALS_DIR / skill / name)
        except (OSError, yaml.YAMLError, run_eval.guidance.GuidanceError) as exc:
            raise Refusal(f"fixture {name!r} is unreadable: {exc}") from exc
        if fixture.get("skill") != skill:
            raise Refusal(f"fixture {name!r} names skill {fixture.get('skill')!r}, "
                          f"not {skill!r}")
        out[name] = fixture
    registries = {f.get("registry") for f in out.values()}
    if len(registries) != 1:
        raise Refusal("the fixtures name more than one registry; one scratch "
                      "registry cannot serve them all")
    return out


def resolve_registry(url: str, flags: list[str] | None) -> dict:
    """The registries.yml entry for `url`, with its local checkout."""
    resolved = run_eval.resolve_registries(
        flags, os.environ.get("SKILLS_EVALS_REGISTRIES"), REPO_ROOT,
        os.environ.get("AGENTSKILLS_DIR"))
    entry = run_eval.registry_for_url(resolved, url)
    if not (entry["path"] / ".git").exists():
        raise Refusal(f"registry {entry['name']!r} has no git checkout at "
                      f"{entry['source']}; pass --registry {entry['name']}=PATH")
    return entry


def resolve_ref(checkout: Path, ref: str) -> str:
    # Raw git is fine here (#343): the operator's registry checkout, never an agent-touched
    # workspace, so harness/workspace_git.py does not apply.
    proc = subprocess.run(["git", "-C", str(checkout), "rev-parse", "--verify",
                           "--quiet", f"{ref}^{{commit}}"],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise Refusal(f"ref {ref!r} does not resolve to a commit in the registry checkout")
    return proc.stdout.strip()


def archive_registry(checkout: Path, sha: str, dest: Path) -> Path:
    """`git archive <sha>` of the checkout, extracted into `dest`. The copy
    carries no `.git`, so there is no remote and no push path in it."""
    # Raw git is fine here (#343): the operator's registry checkout, never an agent-touched
    # workspace, so harness/workspace_git.py does not apply.
    proc = subprocess.run(["git", "-C", str(checkout), "archive", "--format=tar", sha],
                          capture_output=True, check=False)
    if proc.returncode != 0:
        raise Refusal("git archive of the registry failed")
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
        tar.extractall(dest, filter="data")
    return dest


def find_skill_dir(registry_root: Path, layout: str, skill: str) -> Path:
    matches = sorted(registry_root.glob(run_eval._skill_md_glob(layout, skill)))
    if len(matches) != 1:
        raise Refusal(f"expected exactly one {skill}/SKILL.md in the registry, "
                      f"found {len(matches)}")
    return matches[0].parent


def skill_provider_plugins(registry_root: Path, skill: str) -> list[str]:
    """Local marketplace plugins providing `skill`, using archived manifests.

    Default skills/ and declared additional skill paths are additive. Remote
    marketplace sources cannot be inspected in this archive and are skipped.
    Every local path is confined to the archive; no installed plugin runs.
    """
    def read_manifest(path: Path) -> dict:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise Refusal(f"unreadable plugin manifest {path.name}") from exc
        if not isinstance(value, dict):
            raise Refusal(f"plugin manifest {path.name} must be an object")
        return value

    def local_path(base: Path, value: str) -> Path:
        if not isinstance(value, str) or (value != "." and not value.startswith("./")):
            raise Refusal("local plugin paths must be . or start with ./")
        path = (base / value).resolve()
        if not path.is_relative_to(registry_root.resolve()):
            raise Refusal("local plugin path escapes the archived registry")
        return path

    marketplace_path = registry_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.exists():
        return []  # No marketplace means no fully-qualified installed key.
    marketplace = read_manifest(marketplace_path)
    market_name, plugins = marketplace.get("name"), marketplace.get("plugins")
    if not isinstance(market_name, str) or not market_name or not isinstance(plugins, list):
        raise Refusal("marketplace manifest needs a name and plugins list")
    providers = set()
    for entry in plugins:
        if not isinstance(entry, dict):
            raise Refusal("marketplace plugin entry must be an object")
        source = entry.get("source")
        if isinstance(source, dict):
            continue  # Federated sources are never fetched by this loop.
        root = local_path(registry_root, source)
        manifest_path = root / ".claude-plugin" / "plugin.json"
        manifest = read_manifest(manifest_path) if manifest_path.exists() else {}
        name = entry.get("name")  # Installed keys use the marketplace entry.
        if not isinstance(name, str) or not name:
            raise Refusal("marketplace plugin entry needs a name")
        paths = []
        for declaration in (manifest.get("skills", []), entry.get("skills", [])):
            if isinstance(declaration, str):
                declaration = [declaration]
            if not isinstance(declaration, list):
                raise Refusal("plugin skills must be a path or list of paths")
            for declared in declaration:
                path = local_path(root, declared)
                if not path.is_relative_to(root):
                    raise Refusal("skill path escapes its plugin root")
                paths.append(path)
        defaults = ([] if root == registry_root.resolve() and entry.get("skills")
                    else [root / "skills"])
        for path in defaults + paths:
            candidates = ([path / "SKILL.md"] if (path / "SKILL.md").is_file()
                          else sorted(path.glob("*/SKILL.md")))
            for candidate in candidates:
                if not candidate.resolve().is_relative_to(root):
                    raise Refusal("skill path escapes its plugin root")
                try:
                    provided_name = frontmatter_data(candidate.read_text(encoding="utf-8")).get(
                        "name", candidate.parent.name)
                except (OSError, yaml.YAMLError, InvalidProposal) as exc:
                    raise Refusal("unreadable plugin skill frontmatter") from exc
                if provided_name == skill:
                    providers.add(f"{name}@{market_name}")
    return sorted(providers)


def find_skill_creator(cli_value: Path | None) -> tuple[Path, str | None]:
    """(skill-creator's skill directory, its installed commit or None).

    `--skill-creator`, else `$SKILL_CREATOR_DIR`, else the installed bundle
    recorded in `~/.claude/plugins/installed_plugins.json`."""
    candidates: list[tuple[Path, str | None]] = []
    explicit = cli_value or (Path(os.environ["SKILL_CREATOR_DIR"])
                             if os.environ.get("SKILL_CREATOR_DIR") else None)
    if explicit:
        candidates.append((Path(explicit).expanduser(), None))
    else:
        record = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
        try:
            installs = json.loads(record.read_text(encoding="utf-8"))
            for entry in installs.get("plugins", {}).get(SKILL_CREATOR_PLUGIN_KEY, []):
                candidates.append((Path(entry["installPath"]) / SKILL_CREATOR_SUBDIR,
                                   entry.get("gitCommitSha")))
        except (OSError, ValueError, AttributeError, KeyError, TypeError):
            pass
    for path, sha in candidates:
        if (path / "scripts" / "run_loop.py").is_file():
            return path.resolve(), sha
    raise Refusal("skill-creator not found: install the plugin "
                  f"({SKILL_CREATOR_PLUGIN_KEY}) or pass --skill-creator DIR "
                  "(the directory holding scripts/run_loop.py)")


def arm_model(fixture: dict, no_judge: bool = True) -> str:
    """The model run_eval itself will pick for this fixture's agent."""
    ns = argparse.Namespace(model=None, roster=None, no_judge=no_judge)
    model, _, problem = run_eval.select_models(fixture, ns)
    if problem:
        raise Refusal(f"{problem}; configure a judge or pass --no-judge")
    mode = (fixture.get("judge") or {}).get("mode", "absolute")
    normalized = mode.strip().casefold() if isinstance(mode, str) else mode
    if not no_judge and normalized not in (None, "", "absolute"):
        raise Refusal(f"cannot drive judge mode {mode!r}; pass --no-judge")
    return model


def proposal_model() -> str:
    """The committed roster's judge: a model that is not an arm."""
    roster, problem = run_eval.read_roster(run_eval._resolve_roster(None))
    if problem:
        raise Refusal(problem)
    _, judge_id, _, _ = run_eval.roster_models(roster)
    if not judge_id:
        raise Refusal("the roster names no judge model for the proposal call")
    return judge_id


# ---------------------------------------------------------------------------
# Trigger half: skill-creator's description loop
# ---------------------------------------------------------------------------

def load_trigger_eval_set(path: Path) -> list[dict]:
    """A reviewed `--trigger-eval-set` file, refused unless it is exactly
    skill-creator's shape: a JSON list of `{query, should_trigger}` objects
    with a non-empty string query and a JSON boolean label. The label is
    never coerced: `"false"` would otherwise read as a should-trigger query."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise Refusal(f"--trigger-eval-set {path.name}: unreadable: "
                      f"{type(exc).__name__}") from exc
    return parse_trigger_eval_set(data, path.name)


def parse_trigger_eval_set(data: bytes, name: str) -> list[dict]:
    """`load_trigger_eval_set`'s check on bytes already read, so a caller
    holding a git blob (scripts/fixture_pr_gate.py) needs no temp file."""
    try:
        items = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refusal(f"--trigger-eval-set {name}: unreadable: "
                      f"{type(exc).__name__}") from exc
    if not isinstance(items, list):
        raise Refusal(f"--trigger-eval-set {name}: must be a JSON list")
    for index, item in enumerate(items):
        if (not isinstance(item, dict)
                or set(item) != {"query", "should_trigger"}
                or not isinstance(item["query"], str) or not item["query"].strip()
                or not isinstance(item["should_trigger"], bool)):
            raise Refusal(f"--trigger-eval-set {name}: item {index} must be "
                          "exactly {query: non-empty string, should_trigger: boolean}")
    return items


def normalize_trigger_items(items: list[dict],
                            held_out: frozenset | set = frozenset()) -> list[dict]:
    """skill-creator's `[{query, should_trigger}]` as the loop runs it: each
    query's whitespace collapsed, a query in `held_out` dropped, and a query
    kept once (the first label wins). skill-creator separates train from
    held-out results by query text, so a duplicate would put one query on
    both sides. `trigger_eval_set` and the trigger-only mode (and
    improve_gate's fire-check) share it, so all three count the same set."""
    clean, seen = [], set()
    for item in items:
        query = " ".join(str(item.get("query", "")).split())
        if query and query not in held_out and query not in seen:
            seen.add(query)
            clean.append({"query": query, "should_trigger": bool(item.get("should_trigger"))})
    return clean


#: Trigger-only mode's refusal of a reviewed set too small or lopsided to
#: measure a description by. Fixed text: it never quotes the file.
TRIGGER_ONLY_SET_REFUSAL = (
    f"trigger-only mode needs a reviewed trigger eval set with at least "
    f"{TRIGGER_ONLY_MIN_CLASS} distinct should-trigger and "
    f"{TRIGGER_ONLY_MIN_CLASS} distinct should-not-trigger queries, and both "
    "classes in both of skill-creator's splits")


def trigger_only_set(path: Path) -> tuple[list[dict], dict]:
    """(the normalized set, its split counts) of a reviewed set for
    trigger-only mode (skills-evals#662), or Refusal. No fixture prompt is
    held out: there is no validation fixture, and the description loop's own
    held-out split decides. Each class needs TRIGGER_ONLY_MIN_CLASS distinct
    queries, so the 0.4 split holds out at least three of each and one query
    is never the whole TRIGGER_ONLY_MIN_GAIN margin."""
    items = normalize_trigger_items(load_trigger_eval_set(path))
    counts = trigger_split_counts(items)
    positives = sum(1 for item in items if item["should_trigger"])
    if min(positives, len(items) - positives) < TRIGGER_ONLY_MIN_CLASS \
            or trigger_set_problems(counts):
        raise Refusal(TRIGGER_ONLY_SET_REFUSAL)
    return items, counts


def trigger_eval_set(skill: str, fixtures: dict, train: list[str],
                     validation: str, override: Path | None,
                     holdout: str | None = None) -> tuple[list[dict], str]:
    """skill-creator's `[{query, should_trigger}]` and where it came from.

    Default: the train fixtures' prompts should trigger; every OTHER skill's
    fixture prompts should not. `--trigger-eval-set` replaces it. Either way
    the validation fixture's prompt is dropped, so the description loop never
    trains on the fixture that decides acceptance. A query appears once (the
    first label wins): skill-creator separates train from held-out results by
    query text, so a duplicate would put one query on both sides."""
    held_out = {" ".join(str(fixtures[n].get("prompt", "")).split())
                for n in [validation] + ([holdout] if holdout else [])}
    if override:
        items = load_trigger_eval_set(override)
        source = f"file:{override.name}"
    else:
        items = [{"query": fixtures[name]["prompt"], "should_trigger": True}
                 for name in train]
        for path in sorted(EVALS_DIR.rglob(run_eval.FIXTURE_FILE)):
            other = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if (isinstance(other, dict) and other.get("skill")
                    and other.get("skill") != skill
                    and other.get("subject", "skill") == "skill"
                    and isinstance(other.get("prompt"), str)):
                items.append({"query": other["prompt"], "should_trigger": False})
        source = "fixtures"
    clean = normalize_trigger_items(items, held_out)
    if override and (not any(i["should_trigger"] for i in clean)
                     or all(i["should_trigger"] for i in clean)):
        raise Refusal("the trigger eval set needs at least one should-trigger "
                      "and one should-not-trigger query")
    return clean, source


def trigger_split_counts(eval_set: list[dict],
                         holdout: float = TRIGGER_HOLDOUT) -> dict:
    """How many queries of each class skill-creator's `split_eval_set` puts
    in train and in held-out. Its split is stratified: per class it holds out
    `max(1, int(n * holdout))` of the shuffled queries, so the counts (not
    which queries) follow from the class sizes alone."""
    counts = {"train": {}, "held_out": {}}
    for label, wanted in (("should_trigger", True), ("should_not_trigger", False)):
        n = sum(1 for item in eval_set if item["should_trigger"] is wanted)
        held = min(n, max(1, int(n * holdout)))
        counts["train"][label] = n - held
        counts["held_out"][label] = held
    return counts


def trigger_set_problems(counts: dict) -> list[str]:
    """Each split that lacks a class. A train split without a should-trigger
    query lets the loop "pass" by never triggering, and a held-out split
    without one cannot notice a description that stopped triggering."""
    problems = []
    for split, name in (("train", "train"), ("held_out", "held-out")):
        for label in ("should_trigger", "should_not_trigger"):
            if not counts[split][label]:
                problems.append(f"{name} split has no {label.replace('_', '-')} query")
    return problems


def description_loop_argv(eval_set_path: Path, skill_dir: Path, model: str,
                          out_dir: Path,
                          num_workers: int = DEFAULT_NUM_WORKERS) -> list[str]:
    """skill-creator's documented invocation (SKILL.md "Description
    Optimization", step 3), with its defaults spelled out so the record says
    what ran, its browser report switched off, and one worker instead of its
    default 10 (see DEFAULT_NUM_WORKERS)."""
    return ["--eval-set", str(eval_set_path), "--skill-path", str(skill_dir),
            "--model", model, "--max-iterations", "5", "--runs-per-query", "3",
            "--holdout", str(TRIGGER_HOLDOUT), "--num-workers", str(num_workers),
            "--report", "none", "--results-dir", str(out_dir)]


def trigger_loop_usage(loop: dict, out_dir: Path) -> dict:
    """The trigger loop's model calls, counted from what skill-creator left:
    each history entry's per-query `runs` (one `claude -p` each), one
    proposer call between consecutive iterations, and one more per improve
    log that records a length rewrite. Tokens and cost are not reported."""
    history = loop.get("history")
    eval_calls = None
    if isinstance(history, list) and history:
        eval_calls = 0
        for entry in history:
            entry = entry if isinstance(entry, dict) else {}
            for result in (entry.get("train_results") or []) + (entry.get("test_results") or []):
                runs = result.get("runs") if isinstance(result, dict) else None
                if isinstance(runs, int) and not isinstance(runs, bool):
                    eval_calls += runs
    iterations = loop.get("iterations_run")
    description_calls = (iterations - 1 if isinstance(iterations, int)
                         and not isinstance(iterations, bool) and iterations > 0 else None)
    rewrite_calls = 0
    for log in sorted(out_dir.glob("*/logs/improve_iter_*.json")):
        try:
            entry = json.loads(log.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(entry, dict) and "rewrite_prompt" in entry:
            rewrite_calls += 1
    total = (eval_calls + description_calls + rewrite_calls
             if eval_calls is not None and description_calls is not None else None)
    return {"counted_from": "skill-creator loop history and improve logs",
            "eval_calls": eval_calls, "description_calls": description_calls,
            "rewrite_calls": rewrite_calls, "total_calls": total,
            "tokens": None, "cost_usd": None, "cost_note": TRIGGER_COST_NOTE}


# ---------------------------------------------------------------------------
# SKILL.md editing
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str, str]:
    """(frontmatter block including both `---` lines, body)."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise InvalidProposal("SKILL.md has no frontmatter")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "".join(lines[:index + 1]), "".join(lines[index + 1:])
    raise InvalidProposal("SKILL.md frontmatter is not closed")


def frontmatter_data(text: str) -> dict:
    block, _ = split_frontmatter(text)
    inner = block.split("\n", 1)[1].rsplit("---", 1)[0]
    data = yaml.safe_load(inner)
    if not isinstance(data, dict):
        raise InvalidProposal("SKILL.md frontmatter is not a mapping")
    return data


def set_description(text: str, description: str) -> str:
    """`text` with only the frontmatter's `description:` value replaced.
    Written plain when YAML reads it back unchanged, else double-quoted."""
    if not description or len(description) > DESCRIPTION_MAX_CHARS:
        raise InvalidProposal(f"description must be 1..{DESCRIPTION_MAX_CHARS} characters")
    if any(unicodedata.category(char) == "Cc" and char not in "\t\n\r"
           for char in description):
        raise InvalidProposal("description contains a control character")
    block, body = split_frontmatter(text)
    lines = block.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.startswith("description:")), None)
    if start is None:
        raise InvalidProposal("SKILL.md frontmatter has no description")
    end = start + 1
    while end < len(lines) - 1 and lines[end][:1] in (" ", "\t"):
        end += 1
    flat = " ".join(description.split())
    rendered = None
    for candidate in (f"description: {flat}\n",
                      f"description: {json.dumps(flat, ensure_ascii=False)}\n"):
        try:
            if yaml.safe_load(candidate) == {"description": flat}:
                rendered = candidate
                break
        except yaml.YAMLError:
            continue
    if rendered is None:
        raise InvalidProposal("description cannot be rendered as YAML")
    new = "".join(lines[:start]) + rendered + "".join(lines[end:]) + body
    before, after = frontmatter_data(text), frontmatter_data(new)
    if after.get("description") != flat or {k: v for k, v in after.items() if k != "description"} \
            != {k: v for k, v in before.items() if k != "description"}:
        raise InvalidProposal("rewriting the description changed another frontmatter key")
    return new


def check_diff_targets(diff: str) -> None:
    """Every file header in `diff` must be `a/SKILL.md` / `b/SKILL.md`."""
    headers = 0
    for line in diff.splitlines():
        if line.startswith(("--- ", "+++ ")):
            path = line[4:].split("\t", 1)[0].strip()
            if path not in ("a/SKILL.md", "b/SKILL.md"):
                raise InvalidProposal(f"diff touches {path!r}; only SKILL.md may change")
            headers += 1
        elif line.startswith("diff --git ") and line.split()[2:] != ["a/SKILL.md", "b/SKILL.md"]:
            raise InvalidProposal(f"diff touches {line[11:]!r}; only SKILL.md may change")
        elif line.startswith(("rename ", "copy ", "new file", "deleted file",
                              "Binary files", "GIT binary patch", "old mode", "new mode")):
            raise InvalidProposal(f"diff carries a {line.split()[0]!r} header; "
                                  "only an in-place SKILL.md text edit is allowed")
    if headers == 0:
        raise InvalidProposal("diff has no file headers")


def apply_body_diff(text: str, diff: str, scratch: Path) -> str:
    """`text` (a SKILL.md) with `diff` applied, refusing any change to the
    frontmatter. The diff is applied by `git apply` in an empty scratch
    directory that git cannot mistake for part of a repository."""
    if not diff.strip():
        return text
    check_diff_targets(diff)
    work = scratch / "apply"
    work.mkdir(parents=True)
    (work / "SKILL.md").write_text(text, encoding="utf-8")
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(scratch))
    # Raw git is fine here (#343): a fresh scratch directory with no .git, behind a ceiling, never an agent-touched
    # workspace, so harness/workspace_git.py does not apply.
    proc = subprocess.run(["git", "apply", "-p1", "--recount", "--whitespace=nowarn", "-"],
                          cwd=work, input=diff if diff.endswith("\n") else diff + "\n",
                          capture_output=True, text=True, env=env, check=False)
    if proc.returncode != 0:
        # Git's first stderr line says why (e.g. "error: patch failed: SKILL.md:12"), which the record keeps.
        reason = (proc.stderr.strip().splitlines() or [""])[0].strip()[:200]
        raise InvalidProposal("diff does not apply to SKILL.md" + (f": {reason}" if reason else ""))
    unexpected = sorted(p.name for p in work.iterdir() if p.name != "SKILL.md")
    if unexpected:
        raise InvalidProposal(f"diff created {unexpected}; only SKILL.md may change")
    new = (work / "SKILL.md").read_text(encoding="utf-8")
    if split_frontmatter(new)[0] != split_frontmatter(text)[0]:
        raise InvalidProposal("diff touches the frontmatter: the name stays, and "
                              "the description is the trigger half's to change")
    return new


def registry_patch(old: str, new: str, rel_path: str) -> str:
    """A `git apply`-able patch against the registry, rooted at its top."""
    return "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}"))


# ---------------------------------------------------------------------------
# Body half: the proposal call
# ---------------------------------------------------------------------------

PROPOSAL_CONSTRAINTS = """\
Constraints (skills-evals#71):
- Change SKILL.md only. No other file, no new payload file, no rename.
- Leave the frontmatter (the --- block) byte for byte: the name is fixed, and
  the description is the trigger and is tuned separately.
- Fix the failures below by generalizing the instruction that would have
  prevented them; do not quote the fixture, its file names or its answers.
- Prefer the smallest edit that would plausibly fix the failures."""


def run_paths(results: Path, label: str, skill: str, ts: str) -> Path:
    """One empty local_eval destination for this skill, phase and timestamp."""
    return results / "runs" / label / skill / ts


def baseline_dir(results: Path, skill: str, ts: str, fixture: str) -> Path:
    """The baseline is measured one fixture per local_eval call, held-out
    first; each call gets its own empty destination under the baseline's."""
    return run_paths(results, "baseline", skill, ts) / fixture


def trial_arm_dir(run_dir: Path, trial: int, skill: str, ts: str,
                  fixture: str) -> Path:
    return run_dir / f"t{trial}" / skill / ts / fixture / ARM


def failure_evidence(run_dir: Path, skill: str, ts: str,
                     fixture: str, trials: int) -> list[dict]:
    """Each trial's failed checks and the tail of its final reply."""
    evidence = []
    for k in range(1, trials + 1):
        trial = trial_arm_dir(run_dir, k, skill, ts, fixture)
        try:
            summary = json.loads((trial / "summary.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        failed = [{"id": c.get("id"), "detail": c.get("detail")}
                  for c in summary.get("objective_checks") or [] if not c.get("passed")]
        if not failed:
            continue
        reply = ""
        try:
            raw = json.loads((trial / "transcripts" / "raw.json").read_text(encoding="utf-8"))
            reply = str(raw.get("result", "")) if isinstance(raw, dict) else ""
        except (OSError, ValueError):
            pass
        evidence.append({"trial": k, "failed_checks": failed,
                         "reply_tail": reply[-TRANSCRIPT_EXCERPT_CHARS:]})
    return evidence


def proposal_prompt(skill: str, skill_md: str, purpose: str | None,
                    evidence: dict[str, list[dict]], fixtures: dict) -> str:
    parts = [f"You are improving the agent skill `{skill}`. Its SKILL.md is "
             "measured by fixtures; with the skill installed, an agent still "
             "fails the checks below on the TRAINING fixtures.", "",
             PROPOSAL_CONSTRAINTS, ""]
    if purpose:
        parts += ["<purpose>", purpose.strip(), "</purpose>", ""]
    parts += ["<skill_md>", skill_md, "</skill_md>", ""]
    for name, items in evidence.items():
        parts += [f"<fixture name={json.dumps(name)}>",
                  f"Prompt: {fixtures[name].get('prompt', '').strip()}",
                  json.dumps(items, indent=2), "</fixture>", ""]
    parts += ['Answer with ONE JSON object and nothing else: {"rationale": '
              '"<why this edit fixes the failures>", "unified_diff": "<a unified '
              'diff with headers --- a/SKILL.md and +++ b/SKILL.md, or an empty '
              'string if no body edit is warranted>"}']
    return "\n".join(parts)


def parse_proposal(reply: str) -> dict:
    """`{rationale, unified_diff}` out of the reply: the first JSON object in
    it, tolerating a code fence around it."""
    start = reply.find("{")
    decoder = json.JSONDecoder()
    while start != -1:
        try:
            value, _ = decoder.raw_decode(reply, start)
        except json.JSONDecodeError:
            start = reply.find("{", start + 1)
            continue
        if (isinstance(value, dict) and isinstance(value.get("rationale"), str)
                and isinstance(value.get("unified_diff"), str)):
            return value
        start = reply.find("{", start + 1)
    raise InvalidProposal("proposal is not a {rationale, unified_diff} JSON object")


# ---------------------------------------------------------------------------
# Measurement and decision
# ---------------------------------------------------------------------------

def run_eval_argv(skill: str, registry_name: str, registry_root: Path,
                  results: Path, ts: str, trials: int, no_judge: bool,
                  read_deny: Path | None = None,
                  fixture: str | None = None) -> list[str]:
    """local_eval's argv. `read_deny` is this pipeline's results root: the
    candidate's arms must not read the baseline run or the proposed patch.
    `fixture` runs that one nested fixture only."""
    argv = [str(EVALS_DIR / skill), "--arm", ARM, "--trials", str(trials),
            "--registry", f"{registry_name}={registry_root}",
            "--results-dir", str(results), "--timestamp", ts]
    if read_deny is not None:
        argv += ["--read-deny", str(read_deny)]
    if fixture is not None:
        argv += ["--fixture", fixture]
    return argv + (["--no-judge"] if no_judge else [])


def fixture_metrics(run_dir: Path, skill: str, ts: str,
                    fixture: str, trials: int) -> dict:
    """Reduce every local_eval trial; a missing trial stays inconclusive."""
    summaries = []
    for k in range(1, trials + 1):
        path = trial_arm_dir(run_dir, k, skill, ts, fixture) / "summary.json"
        try:
            summary = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(summary, dict):
                raise ValueError("summary is not an object")
        except (OSError, ValueError):
            summary = {"error": {"type": "missing_summary"}}
        if summary.get("error") and not isinstance(summary["error"], dict):
            summary["error"] = {"type": "trial_error"}
        summaries.append(summary)
    stats = run_eval.aggregate_trials(summaries)
    objective = stats["aggregate"]["objective"] or {}
    judge_stats = stats["aggregate"]["judge"] or {}
    judge = judge_stats.get("overall") or {}
    error = next((s["error"].get("type") or "trial_error"
                  for s in summaries if s.get("error")), None)
    if not error and judge_stats.get("errors"):
        error = "judge_error"
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = None  # Injected offline runners may only write trial summaries.
    trial_entries = manifest.get("trials") if isinstance(manifest, dict) else None
    if not error and isinstance(trial_entries, list) and any(
            not isinstance(item, dict) or item.get("exit_code") != 0
            for item in trial_entries):
        error = "trial_exit"
    return {"error": error,
            "passed": objective.get("passed"), "total": objective.get("total"),
            "judge_mean": judge.get("mean"), "n": stats.get("n"),
            "tokens": mean_total_tokens(summaries),
            "tokens_basis": TOKENS_BASIS,
            "main_loop_tokens": mean_tokens(stats["aggregate"]["efficiency"]),
            "model_tokens": model_mean_tokens(stats["aggregate"]["model_tokens"]),
            "cross_model": stats["aggregate"]["cross_model"]}


def model_mean_tokens(per_model: dict) -> dict:
    """Per model id, the mean per trial of each of its four token counts
    (`run_eval.MODEL_TOKEN_FIELDS`), from an `aggregate.model_tokens` block.
    A count is None when any trial lacks it, as in `mean_tokens`. Recorded
    beside `tokens`; no acceptance rule reads it."""
    out = {}
    for model, counts in per_model.items():
        out[model] = {}
        for name, _ in run_eval.MODEL_TOKEN_FIELDS:
            block = counts.get(name) or {}
            out[model][name] = (block["mean"] if block.get("n")
                                and not block.get("n_missing")
                                and valid_tokens(block.get("mean")) else None)
    return out


def mean_total_tokens(summaries: list[dict]) -> float | None:
    """The mean per trial of `run_eval.model_usage_total`: every model's four
    counts from the trial's `model_tokens`. None when any trial's accounting
    is missing or incomplete (an entry dropped, the models truncated, a count
    missing or invalid): the same "missing token data" `decide` already
    treats as inconclusive, never a partial sum."""
    totals = []
    for summary in summaries:
        block = summary.get("cross_model")
        complete = isinstance(block, dict) and block.get("complete") is True
        total = run_eval.model_usage_total(summary.get("model_tokens"), complete)
        if total is None:
            return None
        totals.append(total)
    return sum(totals) / len(totals) if totals else None


def tokens_basis(metrics) -> str:
    """One fixture's `tokens_basis`; metrics written before the field
    measured the main loop's `usage` alone."""
    basis = metrics.get("tokens_basis") if isinstance(metrics, dict) else None
    return basis if isinstance(basis, str) else TOKENS_BASIS_LEGACY


def valid_tokens(value) -> bool:
    """A usable token figure: a finite number, never negative."""
    return run_eval._is_number(value) and value >= 0


def mean_tokens(efficiency: dict) -> float | None:
    """Mean total tokens of one trial (the four `TOKEN_USAGE_METRICS`
    summed), from an `aggregate.efficiency` block. None when any trial lacks
    any of the four: a partial sum is a silent undercount, and a missing
    figure is never zero."""
    total = 0
    for name in TOKEN_USAGE_METRICS:
        block = efficiency.get(name) or {}
        mean = block.get("mean")
        if (not block.get("n") or block.get("n_missing")
                or not valid_tokens(mean)):
            return None
        total += block["mean"]
    return total


def group_metrics(per_fixture: dict, names: list[str]) -> dict:
    rows = [per_fixture.get(n, {"error": "missing fixture"}) for n in names]
    errors = [n for n, r in zip(names, rows) if r.get("error") or not r.get("total")]
    passed = sum(r.get("passed") or 0 for r in rows)
    total = sum(r.get("total") or 0 for r in rows)
    judged = [r["judge_mean"] for r in rows if run_eval._is_number(r.get("judge_mean"))]
    return {"errors": errors, "passed": passed, "total": total,
            "pass_rate": passed / total if total else None,
            "judge_mean": (sum(judged) / len(judged)
                           if judged and len(judged) == len(rows) else None)}


def no_headroom(b_train: dict, min_gain: float = DEFAULT_MIN_GAIN) -> str | None:
    """Why no candidate could be accepted on this baseline, or None. Pure.

    `decide` needs a train objective gain of `min_gain`, or at an equal
    objective a judge gain of ten times it. A baseline whose objective leaves
    less than `min_gain` to gain, and whose judge mean leaves less than that
    on its ten-point scale, cannot be beaten, so measuring a proposal is
    wasted. Errored or unscored train fixtures are left to `decide`'s
    inconclusive path."""
    rate = b_train["pass_rate"]
    if b_train["errors"] or rate is None:
        return None

    def below(gap: float) -> bool:
        return gap < min_gain and not math.isclose(
            gap, min_gain, rel_tol=0, abs_tol=1e-12)

    judge = b_train["judge_mean"]
    if below(1 - rate) and (judge is None or below((10 - judge) / 10)):
        return (f"no train headroom: baseline objective {rate:.3f} leaves less "
                f"than the minimum gain {min_gain:g}, and the judge cannot "
                "make it up; add harder fixtures instead")
    return None


def decide(baseline: dict, candidate: dict, train: list[str],
           validation: str, min_gain: float = DEFAULT_MIN_GAIN,
           holdout: str | None = None,
           judge_required: bool | set[str] = False) -> tuple[bool, list[str]]:
    """(accepted, reasons). Pure: reads the two per-fixture metric maps.

    ADR 0005 amendment 2: quality (objective and judge, below) is judged
    beside tokens. Token data missing for any measured fixture on either side
    is inconclusive, never a pass. A candidate that costs more tokens than the
    baseline (`TOKEN_INCREASE_TOLERANCE`) without a quality gain is not
    accepted; quality gain here is the train gain of `min_gain`, which
    acceptance has always required, so a rise in tokens is accepted only
    alongside one and is recorded in the reasons. Tokens measured on
    different bases (`tokens_basis`) on the two sides are inconclusive."""
    reasons = []
    b_train, c_train = group_metrics(baseline, train), group_metrics(candidate, train)
    b_val, c_val = group_metrics(baseline, [validation]), group_metrics(candidate, [validation])
    errored = sorted(set(b_train["errors"] + c_train["errors"]
                         + b_val["errors"] + c_val["errors"]))
    if errored:
        return False, [f"inconclusive: errored or unscored fixtures {errored}"]
    measured = train + [validation] + ([holdout] if holdout else [])
    required = (set(measured) if judge_required is True
                else set(judge_required) if judge_required else set())
    required.update(n for n in measured
                    if run_eval._is_number(baseline.get(n, {}).get("judge_mean")))
    missing_judge = [n for n in measured if n in required and any(
        not run_eval._is_number(metrics.get(n, {}).get("judge_mean"))
        for metrics in (baseline, candidate))]
    if missing_judge:
        return False, [f"inconclusive: missing expected judge scores {missing_judge}"]

    bases = sorted({tokens_basis(metrics.get(n)) for metrics in (baseline, candidate)
                    for n in measured})
    if len(bases) > 1:
        return False, [f"inconclusive: token bases differ {bases}; baseline "
                       "and candidate must be measured the same way"]
    unknown = [f"{side} {n}" for side, metrics in (("baseline", baseline),
                                                   ("candidate", candidate))
               for n in measured
               if not valid_tokens(metrics.get(n, {}).get("tokens"))]
    if unknown:
        return False, [f"inconclusive: missing token data for {unknown}"]
    b_tokens = sum(baseline[n]["tokens"] for n in measured)
    c_tokens = sum(candidate[n]["tokens"] for n in measured)
    limit = b_tokens * (1 + TOKEN_INCREASE_TOLERANCE)
    costs_more = c_tokens > limit and not math.isclose(c_tokens, limit, rel_tol=1e-9)

    held = c_val["pass_rate"] >= b_val["pass_rate"]
    if not held:
        reasons.append(f"validation objective fell {b_val['pass_rate']:.3f} -> "
                       f"{c_val['pass_rate']:.3f}")
    if b_val["judge_mean"] is not None and c_val["judge_mean"] is not None \
            and c_val["judge_mean"] < b_val["judge_mean"] - JUDGE_TOLERANCE:
        held = False
        reasons.append(f"validation judge fell more than {JUDGE_TOLERANCE}: "
                       f"{b_val['judge_mean']:.2f} -> {c_val['judge_mean']:.2f}")

    if holdout:
        b_fixed = group_metrics(baseline, [holdout])
        c_fixed = group_metrics(candidate, [holdout])
        if b_fixed["errors"] or c_fixed["errors"]:
            return False, [f"inconclusive: errored or unscored holdout {holdout!r}"]
        if c_fixed["pass_rate"] < b_fixed["pass_rate"]:
            held = False
            reasons.append("holdout objective regressed")
        if b_fixed["judge_mean"] is not None and c_fixed["judge_mean"] is not None \
                and c_fixed["judge_mean"] < b_fixed["judge_mean"]:
            held = False
            reasons.append("holdout judge regressed (zero tolerance)")

    def meets_gain(gain: float) -> bool:
        return gain > 0 and (gain >= min_gain or math.isclose(
            gain, min_gain, rel_tol=0, abs_tol=1e-12))

    improved = meets_gain(c_train["pass_rate"] - b_train["pass_rate"])
    if c_train["pass_rate"] == b_train["pass_rate"] \
            and b_train["judge_mean"] is not None and c_train["judge_mean"] is not None:
        improved = meets_gain((c_train["judge_mean"] - b_train["judge_mean"]) / 10)
    if not improved:
        reasons.append(f"train did not meet minimum gain {min_gain:g}: "
                       f"objective {b_train['pass_rate']:.3f} -> "
                       f"{c_train['pass_rate']:.3f}")
    reasons.append(f"tokens {b_tokens:g} -> {c_tokens:g} per trial over "
                   f"{', '.join(measured)}")
    if costs_more and not improved:
        reasons.append("candidate costs more tokens without a quality gain")
    elif costs_more and held:
        reasons.append("candidate costs more tokens; accepted only because "
                       "train gained at least the minimum")
    if held and improved:
        reasons.append("validation held and train improved")
    return held and improved, reasons


def table(baseline: dict, candidate: dict | None, train: list[str],
          validation: str, holdout: str | None = None) -> str:
    def cell(m: dict | None) -> tuple[str, str]:
        if not m:
            return "-", "-"
        if m.get("error") or not m.get("total"):
            return f"error ({m.get('error')})", "-"
        judge = m.get("judge_mean")
        return (f"{m['passed']}/{m['total']}",
                f"{judge:.2f}" if run_eval._is_number(judge) else "-")
    lines = ["| Fixture | Split | Baseline objective | Candidate objective "
             "| Baseline judge | Candidate judge |", "|---|---|---|---|---|---|"]
    for name in train + [validation] + ([holdout] if holdout else []):
        b_obj, b_judge = cell(baseline.get(name))
        c_obj, c_judge = cell((candidate or {}).get(name))
        split = "holdout" if name == holdout else "validation" if name == validation else "train"
        lines.append(f"| {name} | {split} | {b_obj} | {c_obj} | {b_judge} | {c_judge} |")
    return "\n".join(lines)


def pr_body(record: dict, rows: str) -> str:
    d, b = record["description_half"], record["body_half"]
    lines = [f"## Proposed `{record['skill']}` SKILL.md edit (validation-gated)", "",
             "Produced by skills-evals `scripts/propose_skill_edit.py` "
             "([#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71)). "
             "A local exhibit (skills-evals ADR 0002, decision 4): measured under "
             "the operator's own login, not badge input. Review before merging; "
             "nothing here merges itself.", "",
             f"- Registry: `{record['registry']['name']}` at `{record['registry']['sha']}`",
             f"- Split: train {', '.join(record['split']['train'])}; "
             f"validation {record['split']['validation']} "
             f"(rotation {record['split']['rotation']})",
             f"- Fixed holdout: {record['split'].get('holdout') or 'none'}; "
             f"minimum train gain: {record['min_gain']:g} (normalized 0..1)",
             f"- Trials per fixture: {record['trials']}, arm `{ARM}`, "
             f"agent model `{record['models']['arm']}`", "",
             "### Train / validation", "", rows, "",
             f"Decision: {'; '.join(record['reasons'])}.", ""]
    if d.get("changed"):
        lines += ["### Description (skill-creator `scripts/run_loop.py`)", "",
                  f"Held-out trigger score {d.get('best_test_score')}, train "
                  f"{d.get('best_train_score')}, query set from {d.get('eval_set_source')}.", "",
                  f"Before: {d['original']}", "", f"After: {d['best']}", ""]
    if b.get("unified_diff"):
        lines += ["### Body edit", "", b.get("rationale", ""), ""]
    lines += ["The patch is `" + record["files"]["patch"] + "`; apply it with "
              "`git apply` at the registry root."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------

def default_results_dir() -> Path:
    """Outside the repository: `$XDG_STATE_HOME/skills-evals`, else
    `~/.local/state/skills-evals`."""
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "skills-evals"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("skill")
    parser.add_argument("--registry", action="append", default=None,
                        help="registry checkout, NAME=PATH (as run_eval.py)")
    parser.add_argument("--ref", default="HEAD",
                        help="registry commit to archive (default HEAD)")
    parser.add_argument("--trials", type=int, default=None,
                        help=f"trials per fixture (default {DEFAULT_TRIALS})")
    parser.add_argument("--rotation", type=int, default=None,
                        help="validation fixture index (default: records so far)")
    parser.add_argument("--min-gain", type=float, default=None,
                        help="minimum train gain on 0..1 scale (default .10; "
                             "objective rate or judge mean / 10 when objective is flat)")
    parser.add_argument("--holdout", default=None,
                        help="fixed nested fixture, never trained on; must not regress")
    parser.add_argument("--trigger-eval-set", type=Path, default=None,
                        help="skill-creator query set JSON (default: from fixtures)")
    parser.add_argument("--skill-creator", type=Path, default=None,
                        help="skill-creator's skill directory (holds scripts/run_loop.py)")
    parser.add_argument("--num-workers", type=int, default=DEFAULT_NUM_WORKERS,
                        help="parallel CLI calls in skill-creator's trigger eval; "
                             "only 1 is accepted (parallel workers undercount triggers)")
    parser.add_argument("--results-dir", type=Path, default=None)
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan; no model call, no write")
    parser.add_argument("--trigger-only", action="store_true",
                        help="run only skill-creator's description loop on "
                             "--trigger-eval-set (skills-evals#662)")
    parser.add_argument("--trim-description", action="store_true",
                        help=f"shorten the description to at most {TRIM_MAX_CHARS} "
                             "characters, accepted on fixture non-inferiority "
                             "(skills-evals#687)")
    args = parser.parse_args(argv)
    if args.trim_description:
        # Each of these would be silently ignored: no fixture is held out,
        # rotated or judged, the gain is not read, and no description loop runs.
        for name, value in (("--holdout", args.holdout), ("--rotation", args.rotation),
                            ("--min-gain", args.min_gain),
                            ("--no-judge", args.no_judge or None),
                            ("--trigger-eval-set", args.trigger_eval_set),
                            ("--skill-creator", args.skill_creator),
                            ("--trigger-only", args.trigger_only or None)):
            if value is not None:
                parser.error(f"--trim-description does not take {name}")
    if args.trigger_only:
        # Each of these would be silently ignored: no fixture is split,
        # measured, judged or trained on, and the gain is fixed.
        if args.trigger_eval_set is None:
            parser.error("--trigger-only needs --trigger-eval-set")
        for name, value in (("--holdout", args.holdout), ("--rotation", args.rotation),
                            ("--no-judge", args.no_judge or None),
                            ("--trials", args.trials), ("--min-gain", args.min_gain)):
            if value is not None:
                parser.error(f"--trigger-only does not take {name}")
    if args.trials is None:
        args.trials = DEFAULT_TRIALS
    if args.min_gain is None:
        args.min_gain = DEFAULT_MIN_GAIN
    if not 1 <= args.trials <= run_eval.MAX_TRIALS:
        parser.error(f"--trials must be 1..{run_eval.MAX_TRIALS}")
    if args.rotation is not None and args.rotation < 0:
        parser.error("--rotation must be >= 0")
    if args.num_workers != 1:
        parser.error(NUM_WORKERS_REFUSAL)
    if not math.isfinite(args.min_gain) or not 0 < args.min_gain <= 1:
        parser.error("--min-gain must be finite and greater than 0, at most 1")
    return args


def plan(args: argparse.Namespace) -> dict:
    """Everything decided before any model call. Reads, never writes."""
    skill = args.skill
    try:
        names = skill_fixtures(skill)
    except ValueError as exc:
        raise Refusal(str(exc)) from exc
    results = (args.results_dir or default_results_dir()).expanduser().resolve()
    records_dir = results / "improvements" / skill
    rotation = args.rotation if args.rotation is not None else default_rotation(records_dir)
    train, validation = split_fixtures(names, rotation, args.holdout)
    fixtures = load_fixtures(skill, names)
    if args.holdout:
        fixed_prompt = " ".join(str(fixtures[args.holdout].get("prompt", "")).split())
        if any(" ".join(str(fixtures[n].get("prompt", "")).split()) == fixed_prompt
               for n in train):
            raise Refusal("fixed --holdout needs a prompt distinct from every train fixture")
    models = {name: arm_model(fixture, args.no_judge) for name, fixture in fixtures.items()}
    url = next(iter(fixtures.values())).get("registry")
    try:
        registry = resolve_registry(url, args.registry)
    except ValueError as exc:
        raise Refusal(str(exc)) from exc
    sha = resolve_ref(registry["path"], args.ref)
    skill_creator, sc_sha = find_skill_creator(args.skill_creator)
    p = {"skill": skill, "results": results, "records_dir": records_dir,
         "rotation": rotation, "holdout": args.holdout, "min_gain": args.min_gain,
         "fixtures": fixtures, "registry": registry, "sha": sha,
         "skill_creator": skill_creator, "skill_creator_sha": sc_sha,
         "validation_order": validation_order(names, rotation, args.holdout),
         "trigger_eval_set_override": args.trigger_eval_set,
         "arm_model": models[train[0]],
         "proposal_model": proposal_model()}
    set_split(p, train, validation)
    return p


def set_split(p: dict, train: list[str], validation: str) -> None:
    """Point the plan at one split, with the trigger set that split implies:
    the validation fixture's prompt never enters it. Reads, never writes."""
    eval_set, source = trigger_eval_set(p["skill"], p["fixtures"], train, validation,
                                        p["trigger_eval_set_override"], p["holdout"])
    split_counts = trigger_split_counts(eval_set)
    p.update(train=train, validation=validation, eval_set=eval_set,
             eval_set_source=source, trigger_split=split_counts,
             trigger_problems=trigger_set_problems(split_counts))


def print_plan(p: dict, args: argparse.Namespace) -> None:
    n = len(p["fixtures"])
    per_run = n * args.trials * (1 if args.no_judge else 2)
    print(json.dumps({
        "skill": p["skill"], "rotation": p["rotation"], "train": p["train"],
        "validation": p["validation"],
        "validation_order": p["validation_order"],
        "holdout": p["holdout"], "min_gain": p["min_gain"],
        "registry": {"name": p["registry"]["name"], "sha": p["sha"]},
        "skill_creator": str(p["skill_creator"]),
        "trigger_eval_set": {"source": p["eval_set_source"], "size": len(p["eval_set"]),
                             "split": p["trigger_split"],
                             "problems": p["trigger_problems"]},
        "num_workers": args.num_workers,
        "models": {"arm": p["arm_model"], "proposal": p["proposal_model"]},
        "results_dir": str(p["results"]),
        "model_calls": {
            "run_eval_baseline": per_run, "run_eval_candidate": per_run,
            # 5 iterations x 3 runs per query, plus up to two proposer calls
            # (one more when a description overruns 1024 characters) for
            # each of the 4 improvements between them.
            "skill_creator_loop_at_most": 5 * 3 * len(p["eval_set"]) + 2 * 4,
            "proposal": 1},
    }, indent=2))


def improve(args: argparse.Namespace, runner: Runner, now: datetime) -> int:
    p = plan(args)
    unusable = trigger_set_unusable(p)
    if args.dry_run:
        print_plan(p, args)
        if unusable:
            print(f"trigger-set-unusable: {unusable}", file=sys.stderr)
            return EXIT_REFUSED
        return EXIT_ACCEPTED
    skill, results, registry = p["skill"], p["results"], p["registry"]
    ts = now.astimezone(timezone.utc).strftime(run_eval.TIMESTAMP_FORMAT)
    # Improvement records persist here; each local_eval call receives its
    # own absent or empty directory beneath runs/.
    try:
        for path in (results, p["records_dir"],
                     results / "trigger" / skill):
            local_eval.check_results_dir(path, require_empty=False)
        local_eval.check_results_dir(results / "trigger" / skill / ts)
    except local_eval.Refused as exc:
        raise Refusal(str(exc)) from exc
    names = p["train"] + [p["validation"]] + ([p["holdout"]] if p["holdout"] else [])
    p["records_dir"].mkdir(parents=True, exist_ok=True)
    stem = p["records_dir"] / ts
    if stem.with_suffix(".json").exists():
        raise Refusal(f"a record for {ts} already exists")

    scratch = Path(tempfile.mkdtemp(prefix="propose-skill-edit-"))
    try:
        base_root = archive_registry(registry["path"], p["sha"], scratch / "baseline")
        cand_root = archive_registry(registry["path"], p["sha"], scratch / "candidate")
        base_skill = find_skill_dir(base_root, registry["layout"], skill)
        cand_skill = find_skill_dir(cand_root, registry["layout"], skill)
        rel_path = base_skill.relative_to(base_root).as_posix() + "/SKILL.md"
        original = (base_skill / "SKILL.md").read_text(encoding="utf-8")
        disabled_plugins = skill_provider_plugins(base_root, skill)

        record = {
            "schema": 1, "skill": skill, "timestamp": ts,
            "local_exhibit": "skills-evals ADR 0002 decision 4: operator login, not badge input",
            "registry": {"name": registry["name"], "url": registry["url"],
                         "sha": p["sha"], "skill_md": rel_path},
            "split": {"rotation": p["rotation"], "train": p["train"],
                      "validation": p["validation"]},
            "trials": args.trials, "no_judge": args.no_judge,
            "min_gain": args.min_gain,
            "models": {"arm": p["arm_model"], "proposal": p["proposal_model"]},
            "baseline": None, "candidate": None, "tokens_basis": TOKENS_BASIS,
            "runs": {"baseline": str(run_paths(results, "baseline", skill, ts))},
            "files": {},
        }
        if p["holdout"]:
            record["split"]["holdout"] = p["holdout"]
        record["trigger_set"] = {"source": p["eval_set_source"],
                                 "size": len(p["eval_set"]),
                                 "split": p["trigger_split"],
                                 "problems": p["trigger_problems"]}
        if unusable:
            record.update(status="trigger-set-unusable", phase="trigger-set",
                          exit_code=EXIT_REFUSED, reasons=[unusable])
            write_record(stem, record)
            print(f"refused: trigger-set-unusable: {unusable}; record: "
                  f"{stem.with_suffix('.json')}", file=sys.stderr)
            return EXIT_REFUSED
        if p["trigger_problems"]:
            print("warning: reviewed trigger eval set: " + "; ".join(p["trigger_problems"]),
                  file=sys.stderr)

        try:
            check_launch_environment()
        except Refusal as exc:
            return record_refusal(stem, record, "preflight", exc)

        # Held-out first: the validation fixture is measured before any train
        # fixture, and one that already passes every check is swapped for the
        # next in rotation order, so no train, trigger, proposal or candidate
        # tokens go to a run whose held-out test cannot tell anything.
        baseline: dict = {}
        record["baseline"] = baseline
        record["heldout_screen"] = screen = []

        def measure(name: str) -> int:
            out = baseline_dir(results, skill, ts, name)
            rc = runner.run_eval(run_eval_argv(skill, registry["name"], base_root,
                                               out, ts, args.trials, args.no_judge,
                                               read_deny=results, fixture=name))
            baseline[name] = fixture_metrics(out, skill, ts, name, args.trials)
            return rc

        def refuse_baseline(rc: int) -> int:
            record.update(status="refused", phase="baseline", exit_code=rc,
                          reasons=[f"local_eval exited {rc} during baseline"])
            write_record(stem, record)
            print(f"refused: local_eval baseline exited {rc}; record: "
                  f"{stem.with_suffix('.json')}", file=sys.stderr)
            return EXIT_REFUSED

        validation = None
        for name in p["validation_order"]:
            train = [n for n in p["train"] + [p["validation"]] if n != name]
            if name != p["validation"]:
                trial = dict(p)
                set_split(trial, sorted(train), name)
                if trigger_set_unusable(trial):
                    screen.append({"fixture": name, "measured": False,
                                   "skipped": "trigger set unusable"})
                    continue
            rc = measure(name)
            if rc not in (EXIT_ACCEPTED, EXIT_REJECTED):
                return refuse_baseline(rc)
            full = saturated(baseline[name])
            screen.append({"fixture": name, "measured": True,
                           "passed": baseline[name]["passed"],
                           "total": baseline[name]["total"], "saturated": full})
            if not full:
                validation = name
                break
        if validation is None:
            reason = ("no held-out headroom: every validation candidate passes "
                      "every check on the baseline, so no held-out test could "
                      "show an edit carries over; add harder fixtures instead")
            record.update(status="rejected", phase="held-out", reasons=[reason])
            write_record(stem, record)
            print(f"rejected before proposal: {reason}")
            return EXIT_REJECTED
        if validation != p["validation"]:
            set_split(p, sorted(n for n in p["train"] + [p["validation"]]
                                if n != validation), validation)
            record["split"].update(train=p["train"], validation=validation)
            record["trigger_set"] = {"source": p["eval_set_source"],
                                     "size": len(p["eval_set"]),
                                     "split": p["trigger_split"],
                                     "problems": p["trigger_problems"]}
        if baseline[validation]["error"]:
            reason = (f"inconclusive: held-out fixture {validation!r} errored on "
                      f"the baseline ({baseline[validation]['error']})")
            record.update(status="rejected", phase="held-out", reasons=[reason])
            write_record(stem, record)
            print(f"rejected before proposal: {reason}")
            return EXIT_REJECTED

        for name in names:
            if name not in baseline:
                rc = measure(name)
                if rc not in (EXIT_ACCEPTED, EXIT_REJECTED):
                    return refuse_baseline(rc)
        names = p["train"] + [p["validation"]] + ([p["holdout"]] if p["holdout"] else [])
        record["baseline"] = baseline = {n: baseline[n] for n in names}

        # Stop before any trigger, proposal or candidate call when the
        # baseline leaves no room for the gain `decide` requires.
        stuck = no_headroom(group_metrics(baseline, p["train"]), args.min_gain)
        if stuck:
            record.update(status="rejected", phase="baseline", reasons=[stuck])
            write_record(stem, record)
            print(f"rejected before proposal: {stuck}")
            return EXIT_REJECTED

        # Trigger half: skill-creator's loop, untouched.
        trigger_dir = results / "trigger" / skill / ts
        try:
            loop = run_trigger_loop(runner, p, scratch, trigger_dir, base_skill,
                                    disabled_plugins, args.num_workers)
        except Refusal as exc:
            return record_refusal(stem, record, "trigger", exc)
        raw_best = str(loop.get("best_description") or "")
        record["description_half"] = description_half(
            p, loop, trigger_dir, original, disabled_plugins, args.num_workers)

        # Body half: one proposal call, validated before anything is measured.
        evidence = {n: failure_evidence(baseline_dir(results, skill, ts, n),
                                        skill, ts, n, args.trials)
                    for n in p["train"]}
        evidence = {n: e for n, e in evidence.items() if e}
        record["body_half"] = {"model": p["proposal_model"], "rationale": None,
                               "unified_diff": "", "error": None}
        candidate_text = original
        try:
            if evidence:
                purpose_path = base_skill / "PURPOSE.md"
                purpose = (purpose_path.read_text(encoding="utf-8")
                           if purpose_path.is_file() else None)
                try:
                    reply = runner.propose(
                        proposal_prompt(skill, original, purpose, evidence, p["fixtures"]),
                        p["proposal_model"])
                finally:
                    write_proposal_usage(results, ts, runner)
                proposal = parse_proposal(reply)
                record["body_half"].update(rationale=proposal["rationale"],
                                           unified_diff=proposal["unified_diff"])
                candidate_text = apply_body_diff(original, proposal["unified_diff"], scratch)
            else:
                record["body_half"]["error"] = "no failed train check to learn from"
            if record["description_half"]["changed"]:
                candidate_text = set_description(candidate_text, raw_best)
        except InvalidProposal as exc:
            record.update(status="invalid-proposal", reasons=[str(exc)])
            write_record(stem, record)
            print(f"rejected before measurement: {exc}")
            return EXIT_REJECTED
        except Refusal as exc:
            return record_refusal(stem, record, "proposal", exc)

        if candidate_text == original:
            record.update(status="no-candidate",
                          reasons=["neither half produced a change"])
            write_record(stem, record)
            print("no candidate: neither half produced a change")
            return EXIT_REJECTED

        patch = registry_patch(original, candidate_text, rel_path)
        stem.with_suffix(".patch").write_text(patch, encoding="utf-8")
        record["files"]["patch"] = str(stem.with_suffix(".patch"))
        (cand_skill / "SKILL.md").write_text(candidate_text, encoding="utf-8")

        record["runs"]["candidate"] = str(run_paths(results, "candidate", skill, ts))
        rc = runner.run_eval(run_eval_argv(skill, registry["name"], cand_root,
                                           run_paths(results, "candidate", skill, ts),
                                           ts, args.trials, args.no_judge,
                                           read_deny=results))
        if rc not in (EXIT_ACCEPTED, EXIT_REJECTED):
            record.update(status="refused", phase="candidate", exit_code=rc,
                          reasons=[f"local_eval exited {rc} during candidate"])
            write_record(stem, record)
            print(f"refused: local_eval candidate exited {rc}; record: "
                  f"{stem.with_suffix('.json')}", file=sys.stderr)
            return EXIT_REFUSED
        candidate = {n: fixture_metrics(run_paths(results, "candidate", skill, ts),
                                        skill, ts, n, args.trials) for n in names}
        record["candidate"] = candidate

        accepted, reasons = decide(baseline, candidate, p["train"], p["validation"],
                                    args.min_gain, p["holdout"],
                                    {n for n in names if not args.no_judge
                                     and p["fixtures"][n].get("judge_rubric")})
        record.update(status="accepted" if accepted else "rejected", reasons=reasons)
        rows = table(baseline, candidate, p["train"], p["validation"], p["holdout"])
        record["table"] = rows
        if accepted:
            body_path = stem.with_name(stem.name + ".pr-body.md")
            record["files"]["pr_body"] = str(body_path)
            body_path.write_text(pr_body(record, rows), encoding="utf-8")
        write_record(stem, record)
        print(rows)
        print(f"{record['status']}: {'; '.join(reasons)}")
        print(f"record: {stem.with_suffix('.json')}")
        return EXIT_ACCEPTED if accepted else EXIT_REJECTED
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def trigger_set_unusable(p: dict) -> str | None:
    """Why a fixture-derived trigger set must not run, or None. A reviewed
    `--trigger-eval-set` is the operator's call and only warns."""
    if p["eval_set_source"] != "fixtures" or not p["trigger_problems"]:
        return None
    return ("; ".join(p["trigger_problems"]) + f" (skill-creator --holdout "
            f"{TRIGGER_HOLDOUT} of {len(p['eval_set'])} fixture-derived "
            "queries); the trigger loop would pass without "
            "measuring triggering. Pass a reviewed --trigger-eval-set with at "
            "least two distinct should-trigger and two should-not-trigger queries")


def run_trigger_loop(runner, p: dict, scratch: Path, trigger_dir: Path,
                     skill_dir: Path, disabled_plugins: list[str],
                     num_workers: int) -> dict:
    """skill-creator's description loop on `p["eval_set"]`, run from a
    scratch project whose settings disable `disabled_plugins`, and its
    output saved as `<trigger_dir>/loop.json`. Shared by `improve` and
    `improve_trigger_only`; a Refusal is the caller's to record."""
    trigger_dir.mkdir(parents=True, exist_ok=True)
    eval_set_path = trigger_dir / "eval-set.json"
    eval_set_path.write_text(json.dumps(p["eval_set"], indent=2), encoding="utf-8")
    project = scratch / "trigger-project"
    (project / ".claude").mkdir(parents=True)
    (project / ".claude" / "settings.json").write_text(json.dumps({
        "enabledPlugins": {name: False for name in disabled_plugins}}, indent=2),
        encoding="utf-8")
    loop = runner.run_description_loop(
        description_loop_argv(eval_set_path, skill_dir, p["arm_model"],
                              trigger_dir, num_workers),
        cwd=project, skill_creator=p["skill_creator"])
    (trigger_dir / "loop.json").write_text(json.dumps(loop, indent=2), encoding="utf-8")
    return loop


def description_half(p: dict, loop: dict, trigger_dir: Path, original: str,
                     disabled_plugins: list[str], num_workers: int) -> dict:
    """The record's `description_half`: what the loop ran on and found."""
    original_description = frontmatter_data(original).get("description", "")
    best = " ".join(str(loop.get("best_description") or "").split())
    return {
        "from": "skill-creator scripts/run_loop.py",
        "skill_creator": {"path": str(p["skill_creator"]),
                          "commit": p["skill_creator_sha"]},
        "eval_set_source": p["eval_set_source"], "eval_set_size": len(p["eval_set"]),
        "disabled_plugins": disabled_plugins,
        "original": original_description, "best": best,
        "best_test_score": loop.get("best_test_score"),
        "best_train_score": loop.get("best_train_score"),
        "iterations": loop.get("iterations_run"),
        "num_workers": num_workers,
        "usage": trigger_loop_usage(loop, trigger_dir),
        "changed": bool(best) and best != " ".join(str(original_description).split()),
        "loop_output": str(trigger_dir / "loop.json")}


# ---------------------------------------------------------------------------
# Trigger-only mode (skills-evals#662)
# ---------------------------------------------------------------------------

#: Where a skill with no fixture is looked up: the one registry the routine
#: checks out (improve_gate.REGISTRY_URL).
TRIGGER_ONLY_DEFAULT_REGISTRY = "https://github.com/Adam-S-Daniel/adam-agentskills"
#: Fixed text for a loop output trigger-only mode cannot read.
TRIGGER_LOOP_MALFORMED = ("skill-creator's loop output is malformed: it needs a "
                          "history whose first entry is the original "
                          "description, an entry for best_description, and "
                          "held-out counts and per-query results of the shape "
                          "run_loop.py writes")
#: The numbers trigger-only mode keeps of one history entry.
TRIGGER_COUNT_KEYS = ("test_passed", "test_total", "should_not_passed",
                      "should_not_total")


def _count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def trigger_entry_numbers(entry) -> dict:
    """{test_passed, test_total, should_not_passed, should_not_total} of one
    skill-creator history entry, or Refusal. Held-out is `test_*`; the
    should-not-trigger counts span train and held-out results together, so
    a description that "wins" by triggering on everything shows the drop."""
    if not isinstance(entry, dict):
        raise Refusal(TRIGGER_LOOP_MALFORMED)
    passed, total = entry.get("test_passed"), entry.get("test_total")
    train, test = entry.get("train_results"), entry.get("test_results")
    if not (_count(passed) and _count(total) and passed <= total
            and isinstance(train, list) and isinstance(test, list)):
        raise Refusal(TRIGGER_LOOP_MALFORMED)
    should_not = []
    for result in train + test:
        if not (isinstance(result, dict) and isinstance(result.get("should_trigger"), bool)
                and isinstance(result.get("pass"), bool)):
            raise Refusal(TRIGGER_LOOP_MALFORMED)
        if result["should_trigger"] is False:
            should_not.append(result["pass"])
    return {"test_passed": passed, "test_total": total,
            "should_not_passed": sum(should_not), "should_not_total": len(should_not)}


def meets_trigger_gain(gain: float) -> bool:
    """The held-out pass-rate gain reaches TRIGGER_ONLY_MIN_GAIN. Compared
    at full precision with a tolerance far below one query, so 3/20 - 0/20
    counts as 0.15 although the float is not exact."""
    return gain >= TRIGGER_ONLY_MIN_GAIN or math.isclose(
        gain, TRIGGER_ONLY_MIN_GAIN, rel_tol=0, abs_tol=1e-12)


def decide_trigger_only(loop) -> tuple[bool, list[str], dict, str]:
    """(accepted, reasons, the record's `trigger_only` block, raw best
    description) from skill-creator's loop output, or Refusal on a shape it
    cannot read. Pure.

    history[0] is the ORIGINAL description (run_loop.py measures it first);
    the best is the first history entry whose `description` equals
    `best_description`. Accepted only when the best differs from the
    original, both were measured on the same held-out queries, the held-out
    pass rate rose by at least TRIGGER_ONLY_MIN_GAIN, and no
    should-not-trigger query that passed before fails now (Adam,
    2026-11-03, the #662 decision card)."""
    history = loop.get("history") if isinstance(loop, dict) else None
    raw_best = loop.get("best_description") if isinstance(loop, dict) else None
    if not isinstance(history, list) or not history \
            or not isinstance(raw_best, str) or not raw_best.strip():
        raise Refusal(TRIGGER_LOOP_MALFORMED)
    first = history[0]
    best_entry = next((entry for entry in history if isinstance(entry, dict)
                       and entry.get("description") == raw_best), None)
    if best_entry is None or not isinstance(first, dict) \
            or not isinstance(first.get("description"), str):
        raise Refusal(TRIGGER_LOOP_MALFORMED)
    original, best = trigger_entry_numbers(first), trigger_entry_numbers(best_entry)
    if original["test_total"] < 1 or original["test_total"] != best["test_total"] \
            or original["should_not_total"] != best["should_not_total"]:
        raise Refusal(TRIGGER_LOOP_MALFORMED)
    total = original["test_total"]
    gain = (best["test_passed"] - original["test_passed"]) / total
    block = {"min_gain": TRIGGER_ONLY_MIN_GAIN, "original": original,
             "best": best, "gain": gain}
    reasons = [
        f"held-out trigger queries passed {original['test_passed']}/{total} -> "
        f"{best['test_passed']}/{total} (gain {gain:.3f}, minimum "
        f"{TRIGGER_ONLY_MIN_GAIN:g})",
        f"should-not-trigger queries passed {original['should_not_passed']}/"
        f"{original['should_not_total']} -> {best['should_not_passed']}/"
        f"{best['should_not_total']}"]
    accepted = True
    if " ".join(raw_best.split()) == " ".join(first["description"].split()):
        accepted = False
        reasons.append("the best description is the original")
    if not meets_trigger_gain(gain):
        accepted = False
        reasons.append("held-out trigger accuracy did not rise by the minimum gain")
    if best["should_not_passed"] < original["should_not_passed"]:
        accepted = False
        reasons.append("fewer should-not-trigger queries passed")
    if accepted:
        reasons.append("held-out trigger accuracy rose by at least the minimum "
                       "with no should-not-trigger drop")
    return accepted, reasons, block, raw_best


def trigger_only_plan(args: argparse.Namespace) -> dict:
    """Everything trigger-only mode decides before any model call. Reads,
    never writes. The skill may have no fixture at all: its registry is then
    adam-agentskills, and its arm model the roster's default for a fixture
    with no pin."""
    skill = args.skill
    try:
        names = skill_fixtures(skill)
    except ValueError as exc:
        raise Refusal(str(exc)) from exc
    eval_set, split_counts = trigger_only_set(args.trigger_eval_set)
    fixtures = load_fixtures(skill, names) if names else {}
    url = (next(iter(fixtures.values())).get("registry") if fixtures
           else TRIGGER_ONLY_DEFAULT_REGISTRY)
    try:
        registry = resolve_registry(url, args.registry)
    except ValueError as exc:
        raise Refusal(str(exc)) from exc
    sha = resolve_ref(registry["path"], args.ref)
    skill_creator, sc_sha = find_skill_creator(args.skill_creator)
    results = (args.results_dir or default_results_dir()).expanduser().resolve()
    # The model the normal path would run its arms and trigger loop on: the
    # first fixture's (by name), or the roster's default with no fixture.
    model = arm_model(fixtures[names[0]] if fixtures else {}, True)
    return {"skill": skill, "results": results,
            "records_dir": results / "improvements" / skill,
            "registry": registry, "sha": sha, "skill_creator": skill_creator,
            "skill_creator_sha": sc_sha, "arm_model": model,
            "eval_set": eval_set, "trigger_split": split_counts,
            "trigger_problems": trigger_set_problems(split_counts),
            "eval_set_source": f"file:{args.trigger_eval_set.name}",
            "fixture_count": len(names)}


def trigger_only_pr_body(record: dict) -> str:
    """The pull-request body of an accepted trigger-only run. It opens with
    the loop's own title (improve_gate.REPORT_TITLE) and holds no closing
    keyword and no mention: it becomes a body in adam-agentskills."""
    d, t = record["description_half"], record["trigger_only"]
    o, b = t["original"], t["best"]
    return "\n".join([
        f"## Proposed `{record['skill']}` SKILL.md edit (validation-gated)", "",
        "Produced by skills-evals `scripts/propose_skill_edit.py --trigger-only` "
        "([#662](https://github.com/Adam-S-Daniel/skills-evals/issues/662)): a "
        "trigger-only run. Only skill-creator's description loop "
        "(`scripts/run_loop.py`) ran, on the skill's reviewed trigger eval "
        "set; the SKILL.md body is unchanged and no task fixture was measured. "
        "A local exhibit (skills-evals ADR 0002, decision 4), not badge input.", "",
        f"- Registry: `{record['registry']['name']}` at `{record['registry']['sha']}`",
        f"- Query set: {record['trigger_set']['source']}, "
        f"{record['trigger_set']['size']} queries; trigger model "
        f"`{record['models']['arm']}`", "",
        "### Description", "",
        f"Before: {d['original']}", "", f"After: {d['best']}", "",
        "### Trigger accuracy", "",
        f"- Held-out queries passed: {o['test_passed']}/{o['test_total']} -> "
        f"{b['test_passed']}/{b['test_total']} (gain {t['gain']:.3f})",
        f"- Should-not-trigger queries passed (train and held-out): "
        f"{o['should_not_passed']}/{o['should_not_total']} -> "
        f"{b['should_not_passed']}/{b['should_not_total']}", "",
        f"Acceptance rule: the held-out pass rate must rise by at least "
        f"{t['min_gain']:g} and no fewer should-not-trigger queries may pass. "
        f"Decision: {'; '.join(record['reasons'])}.", "",
        "The patch is `" + record["files"]["patch"] + "`; apply it with "
        "`git apply` at the registry root."]) + "\n"


def improve_trigger_only(args: argparse.Namespace, runner: Runner, now: datetime) -> int:
    """Trigger-only mode: only skill-creator's description loop, accepted
    by `decide_trigger_only`. See the module docstring."""
    p = trigger_only_plan(args)
    if args.dry_run:
        print(json.dumps({
            "skill": p["skill"], "mode": "trigger-only",
            "fixtures": p["fixture_count"],
            "registry": {"name": p["registry"]["name"], "sha": p["sha"]},
            "skill_creator": str(p["skill_creator"]),
            "trigger_eval_set": {"source": p["eval_set_source"],
                                 "size": len(p["eval_set"]),
                                 "split": p["trigger_split"],
                                 "problems": p["trigger_problems"]},
            "min_gain": TRIGGER_ONLY_MIN_GAIN,
            "num_workers": args.num_workers,
            "models": {"arm": p["arm_model"]},
            "results_dir": str(p["results"]),
            "model_calls": {"skill_creator_loop_at_most":
                            5 * 3 * len(p["eval_set"]) + 2 * 4},
        }, indent=2))
        return EXIT_ACCEPTED
    skill, results, registry = p["skill"], p["results"], p["registry"]
    ts = now.astimezone(timezone.utc).strftime(run_eval.TIMESTAMP_FORMAT)
    try:
        for path in (results, p["records_dir"], results / "trigger" / skill):
            local_eval.check_results_dir(path, require_empty=False)
        local_eval.check_results_dir(results / "trigger" / skill / ts)
    except local_eval.Refused as exc:
        raise Refusal(str(exc)) from exc
    p["records_dir"].mkdir(parents=True, exist_ok=True)
    stem = p["records_dir"] / ts
    if stem.with_suffix(".json").exists():
        raise Refusal(f"a record for {ts} already exists")

    scratch = Path(tempfile.mkdtemp(prefix="propose-skill-edit-"))
    try:
        base_root = archive_registry(registry["path"], p["sha"], scratch / "baseline")
        base_skill = find_skill_dir(base_root, registry["layout"], skill)
        rel_path = base_skill.relative_to(base_root).as_posix() + "/SKILL.md"
        original = (base_skill / "SKILL.md").read_text(encoding="utf-8")
        disabled_plugins = skill_provider_plugins(base_root, skill)
        record = {
            "schema": 1, "skill": skill, "timestamp": ts, "mode": "trigger-only",
            "local_exhibit": "skills-evals ADR 0002 decision 4: operator login, not badge input",
            "registry": {"name": registry["name"], "url": registry["url"],
                         "sha": p["sha"], "skill_md": rel_path},
            "models": {"arm": p["arm_model"]},
            "trigger_set": {"source": p["eval_set_source"], "size": len(p["eval_set"]),
                            "split": p["trigger_split"],
                            "problems": p["trigger_problems"]},
            "files": {},
        }
        try:
            check_launch_environment()
        except Refusal as exc:
            return record_refusal(stem, record, "preflight", exc)
        trigger_dir = results / "trigger" / skill / ts
        try:
            loop = run_trigger_loop(runner, p, scratch, trigger_dir, base_skill,
                                    disabled_plugins, args.num_workers)
            if not isinstance(loop, dict):
                raise Refusal(TRIGGER_LOOP_MALFORMED)
        except Refusal as exc:
            return record_refusal(stem, record, "trigger", exc)
        record["description_half"] = description_half(
            p, loop, trigger_dir, original, disabled_plugins, args.num_workers)
        try:
            accepted, reasons, block, raw_best = decide_trigger_only(loop)
        except Refusal as exc:
            return record_refusal(stem, record, "decision", exc)
        record["trigger_only"] = block
        try:
            candidate = set_description(original, raw_best)
        except InvalidProposal as exc:
            accepted = False
            reasons = reasons + [f"the best description cannot be written: {exc}"]
            candidate = original
        if candidate != original:
            stem.with_suffix(".patch").write_text(
                registry_patch(original, candidate, rel_path), encoding="utf-8")
            record["files"]["patch"] = str(stem.with_suffix(".patch"))
        elif accepted:
            accepted = False
            reasons = reasons + ["the best description leaves SKILL.md unchanged"]
        record.update(status="accepted" if accepted else "rejected", reasons=reasons)
        if accepted:
            body_path = stem.with_name(stem.name + ".pr-body.md")
            record["files"]["pr_body"] = str(body_path)
            body_path.write_text(trigger_only_pr_body(record), encoding="utf-8")
        write_record(stem, record)
        print(f"{record['status']}: {'; '.join(reasons)}")
        print(f"record: {stem.with_suffix('.json')}")
        return EXIT_ACCEPTED if accepted else EXIT_REJECTED
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Description trim mode (skills-evals#687)
# ---------------------------------------------------------------------------

#: The trim reply's one key: `{"description": "..."}` and nothing else.
TRIM_REPLY_KEYS = ("description",)
#: Fixed texts for a reply the trim refuses to measure. None quotes the
#: reply: the record keeps the model's text only as the candidate, and only
#: once it passed every check.
TRIM_REPLY_MALFORMED = ('the trim reply is not exactly one JSON object '
                        '{"description": "<text>"}')
TRIM_REPLY_NEWLINE = "the trimmed description contains a line break"
TRIM_REPLY_LENGTH = (f"the trimmed description must be 1..{TRIM_MAX_CHARS} "
                     "characters after whitespace is collapsed")
TRIM_REPLY_UNCHANGED = "the trimmed description is the current description"
TRIM_ALREADY_SHORT = "already within the cap"

TRIM_CONSTRAINTS = f"""\
Constraints (skills-evals#687):
- Return ONE replacement for the description in the frontmatter below, at
  most {TRIM_MAX_CHARS} characters, on one line, plain text: no Markdown, no
  quotes around it, no line breaks.
- Keep every trigger phrase and every situation in which the skill should
  be used, so it is chosen as often as before.
- Keep every boundary: each "not for ...", "use X instead" or "skip when"
  statement, so it is not chosen where it was not before.
- Remove repetition, examples that restate a trigger, and filler first.
- Do not invent a trigger, a boundary or a capability the skill does not
  have. Change nothing but the description."""


def trim_prompt(skill: str, skill_md: str, description: str) -> str:
    """The one proposal call of trim mode. The whole SKILL.md goes in so the
    model can tell which phrases name real situations; the reply shape is
    fixed and parsed by `parse_trim_reply`."""
    flat = " ".join(str(description).split())
    return "\n".join([
        f"You are shortening the description of the agent skill `{skill}`. A "
        f"session lists every skill's description, and this one is "
        f"{len(flat)} characters, over the {TRIM_MAX_CHARS}-character cap, so "
        "the listing truncates or drops it.", "",
        TRIM_CONSTRAINTS, "",
        "<current_description>", flat, "</current_description>", "",
        "<skill_md>", skill_md, "</skill_md>", "",
        'Answer with ONE JSON object and nothing else: {"description": '
        f'"<the replacement, at most {TRIM_MAX_CHARS} characters>"}}'])


def parse_trim_reply(reply: str, original: str) -> str:
    """The replacement description out of `reply`, whitespace collapsed, or
    InvalidProposal with fixed text. Strict: the reply, stripped and with at
    most one surrounding code fence removed, must parse as exactly one JSON
    object whose only key is `description`, a string with no line break,
    1..TRIM_MAX_CHARS characters after whitespace is collapsed, and not equal
    to `original` (collapsed the same way). Pure."""
    text = reply.strip() if isinstance(reply, str) else ""
    if text.startswith("```") and text.endswith("```") and len(text) >= 6:
        inner = text[3:-3]
        first, _, rest = inner.partition("\n")
        text = (rest if first.strip() in ("", "json") else inner).strip()
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        raise InvalidProposal(TRIM_REPLY_MALFORMED) from None
    if not isinstance(value, dict) or tuple(value) != TRIM_REPLY_KEYS \
            or not isinstance(value["description"], str):
        raise InvalidProposal(TRIM_REPLY_MALFORMED)
    raw = value["description"]
    if "\n" in raw or "\r" in raw:
        raise InvalidProposal(TRIM_REPLY_NEWLINE)
    flat = " ".join(raw.split())
    if not 1 <= len(flat) <= TRIM_MAX_CHARS:
        raise InvalidProposal(TRIM_REPLY_LENGTH)
    if flat == " ".join(str(original).split()):
        raise InvalidProposal(TRIM_REPLY_UNCHANGED)
    return flat


def trim_counts(metrics: dict) -> dict:
    """{passed, total} of one fixture's `fixture_metrics`, as the record's
    `trim` block keeps them (None where the run produced no number)."""
    return {"passed": metrics.get("passed"), "total": metrics.get("total")}


def decide_trim(baseline: dict, candidate: dict, names: list[str]) -> tuple[bool, list[str]]:
    """(accepted, reasons) for a trimmed description, from each side's
    `fixture_metrics` per fixture in `names`. Pure. The rule (module
    docstring, DESCRIPTION TRIM MODE; TRIM_RULE): no fixture errored on
    either side, each fixture ran the same number of checks (at least one)
    on both, the candidate's passes summed over every fixture are at least
    the baseline's minus TRIM_TOLERANCE_CHECKS, and no fixture lost more than
    TRIM_FIXTURE_DROP_CHECKS passes. scripts/improve_gate.check_trim applies
    the same rule to the record's counts."""
    reasons = []
    for name in names:
        for side, metrics in (("baseline", baseline.get(name)), ("candidate", candidate.get(name))):
            if not isinstance(metrics, dict) or metrics.get("error"):
                kind = metrics.get("error") if isinstance(metrics, dict) else "missing"
                reasons.append(f"inconclusive: fixture {name!r} errored on the {side} ({kind})")
    if reasons:
        return False, reasons
    for name in names:
        b, c = baseline[name], candidate[name]
        if not all(isinstance(v, int) and not isinstance(v, bool)
                   for v in (b["passed"], b["total"], c["passed"], c["total"])) \
                or b["total"] < 1 or b["total"] != c["total"]:
            reasons.append(f"inconclusive: fixture {name!r} did not run the same "
                           "checks on both sides")
    if reasons:
        return False, reasons
    before = sum(baseline[n]["passed"] for n in names)
    after = sum(candidate[n]["passed"] for n in names)
    total = sum(baseline[n]["total"] for n in names)
    reasons.append(f"objective checks passed over all fixtures {before}/{total} -> "
                   f"{after}/{total}")
    accepted = True
    if after < before - TRIM_TOLERANCE_CHECKS:
        accepted = False
        reasons.append("the trimmed description passed fewer checks in aggregate")
    for name in names:
        drop = baseline[name]["passed"] - candidate[name]["passed"]
        if drop > TRIM_FIXTURE_DROP_CHECKS:
            accepted = False
            reasons.append(f"fixture {name!r} lost {drop} checks, more than "
                           f"{TRIM_FIXTURE_DROP_CHECKS}")
    if accepted:
        reasons.append("no worse in aggregate, and no fixture lost more than "
                       f"{TRIM_FIXTURE_DROP_CHECKS} check(s)")
    return accepted, reasons


def trim_plan(args: argparse.Namespace) -> dict:
    """Everything trim mode decides before any model call. Reads, never
    writes. The fixtures, their one registry and the arm model are resolved
    as `plan` resolves them; at least MIN_FIXTURES are required."""
    skill = args.skill
    try:
        names = skill_fixtures(skill)
    except ValueError as exc:
        raise Refusal(str(exc)) from exc
    if len(names) < MIN_FIXTURES:
        raise Refusal(f"needs more fixtures: {len(names)} found, {MIN_FIXTURES} "
                      "required for a trim to be measured on")
    fixtures = load_fixtures(skill, names)
    url = next(iter(fixtures.values())).get("registry")
    try:
        registry = resolve_registry(url, args.registry)
    except ValueError as exc:
        raise Refusal(str(exc)) from exc
    sha = resolve_ref(registry["path"], args.ref)
    results = (args.results_dir or default_results_dir()).expanduser().resolve()
    return {"skill": skill, "results": results,
            "records_dir": results / "improvements" / skill,
            "names": names, "fixtures": fixtures, "registry": registry, "sha": sha,
            "arm_model": arm_model(fixtures[names[0]], True),
            "proposal_model": proposal_model()}


def trim_pr_body(record: dict) -> str:
    """The pull-request body of an accepted trim. It opens with the loop's
    own title (improve_gate.REPORT_TITLE) and holds no closing keyword and no
    mention: it becomes a body in adam-agentskills."""
    t, d = record["trim"], record["description"]
    rows = ["| Fixture | Baseline | Candidate |", "|---|---|---|"]
    for name in sorted(t["baseline"]):
        b, c = t["baseline"][name], t["candidate"][name]
        rows.append(f"| `{name}` | {b['passed']}/{b['total']} | {c['passed']}/{c['total']} |")
    return "\n".join([
        f"## Proposed `{record['skill']}` SKILL.md edit (validation-gated)", "",
        "Produced by skills-evals `scripts/propose_skill_edit.py --trim-description` "
        "([#687](https://github.com/Adam-S-Daniel/skills-evals/issues/687)): the "
        f"description was over adam-agentskills' {t['max_chars']}-character listing "
        "cap, so its `length-limit` waiver is removed here too. Only the "
        "description changed; the body is unchanged. A local exhibit "
        "(skills-evals ADR 0002, decision 4), not badge input.", "",
        f"- Registry: `{record['registry']['name']}` at `{record['registry']['sha']}`",
        f"- Length: {t['original_chars']} -> {t['candidate_chars']} characters",
        f"- Measured: every fixture, {record['trials']} trial(s) each, `with_skill` "
        f"arm on `{record['models']['arm']}`, no judge; proposal model "
        f"`{record['models']['proposal']}`", "",
        "### Description", "",
        f"Before: {d['original']}", "", f"After: {d['candidate']}", "",
        "### Objective checks passed", "", *rows, "",
        "Acceptance rule: the candidate passes at least as many checks as the "
        "baseline summed over every fixture, and no fixture loses more than "
        f"{TRIM_FIXTURE_DROP_CHECKS}. Decision: {'; '.join(record['reasons'])}.", "",
        "The patch is `" + record["files"]["patch"] + "`; apply it with "
        "`git apply` at the registry root."]) + "\n"


def improve_trim(args: argparse.Namespace, runner: Runner, now: datetime) -> int:
    """Description trim mode: one proposal call for a shorter description,
    accepted by `decide_trim` on every fixture. See the module docstring."""
    p = trim_plan(args)
    if args.dry_run:
        n = len(p["names"])
        print(json.dumps({
            "skill": p["skill"], "mode": "trim", "fixtures": p["names"],
            "registry": {"name": p["registry"]["name"], "sha": p["sha"]},
            "max_chars": TRIM_MAX_CHARS, "rule": TRIM_RULE, "trials": args.trials,
            "models": {"arm": p["arm_model"], "proposal": p["proposal_model"]},
            "results_dir": str(p["results"]),
            "model_calls": {"proposal": 1, "run_eval_baseline": n * args.trials,
                            "run_eval_candidate": n * args.trials},
        }, indent=2))
        return EXIT_ACCEPTED
    skill, results, registry, names = p["skill"], p["results"], p["registry"], p["names"]
    ts = now.astimezone(timezone.utc).strftime(run_eval.TIMESTAMP_FORMAT)
    try:
        for path in (results, p["records_dir"]):
            local_eval.check_results_dir(path, require_empty=False)
    except local_eval.Refused as exc:
        raise Refusal(str(exc)) from exc
    p["records_dir"].mkdir(parents=True, exist_ok=True)
    stem = p["records_dir"] / ts
    if stem.with_suffix(".json").exists():
        raise Refusal(f"a record for {ts} already exists")

    scratch = Path(tempfile.mkdtemp(prefix="propose-skill-edit-"))
    try:
        base_root = archive_registry(registry["path"], p["sha"], scratch / "baseline")
        cand_root = archive_registry(registry["path"], p["sha"], scratch / "candidate")
        base_skill = find_skill_dir(base_root, registry["layout"], skill)
        cand_skill = find_skill_dir(cand_root, registry["layout"], skill)
        rel_path = base_skill.relative_to(base_root).as_posix() + "/SKILL.md"
        original = (base_skill / "SKILL.md").read_text(encoding="utf-8")
        try:
            current = frontmatter_data(original).get("description")
        except InvalidProposal as exc:
            raise Refusal(f"the registry's SKILL.md cannot be read: {exc}") from exc
        if not isinstance(current, str) or not current.strip():
            raise Refusal("the registry's SKILL.md has no description to trim")
        record = {
            "schema": 1, "skill": skill, "timestamp": ts, "mode": "trim",
            "local_exhibit": "skills-evals ADR 0002 decision 4: operator login, not badge input",
            "registry": {"name": registry["name"], "url": registry["url"],
                         "sha": p["sha"], "skill_md": rel_path},
            "models": {"arm": p["arm_model"], "proposal": p["proposal_model"]},
            "trials": args.trials, "no_judge": True,
            "description": {"original": current, "candidate": None},
            "trim": {"max_chars": TRIM_MAX_CHARS, "original_chars": len(current),
                     "candidate_chars": None, "rule": TRIM_RULE,
                     "tolerance_checks": TRIM_TOLERANCE_CHECKS,
                     "fixture_drop_checks": TRIM_FIXTURE_DROP_CHECKS,
                     "baseline": {}, "candidate": {}},
            "files": {},
        }
        if len(current) <= TRIM_MAX_CHARS:
            record.update(status="rejected", phase="trim", reasons=[TRIM_ALREADY_SHORT])
            write_record(stem, record)
            print(f"rejected: {TRIM_ALREADY_SHORT}")
            return EXIT_REJECTED
        try:
            check_launch_environment()
        except Refusal as exc:
            return record_refusal(stem, record, "preflight", exc)

        try:
            try:
                reply = runner.propose(trim_prompt(skill, original, current),
                                       p["proposal_model"])
            finally:
                write_proposal_usage(results, ts, runner)
            trimmed = parse_trim_reply(reply, current)
            candidate_text = set_description(original, trimmed)
        except InvalidProposal as exc:
            record.update(status="invalid-proposal", reasons=[str(exc)])
            write_record(stem, record)
            print(f"rejected before measurement: {exc}")
            return EXIT_REJECTED
        except Refusal as exc:
            return record_refusal(stem, record, "proposal", exc)
        record["description"]["candidate"] = trimmed
        record["trim"]["candidate_chars"] = len(trimmed)
        stem.with_suffix(".patch").write_text(
            registry_patch(original, candidate_text, rel_path), encoding="utf-8")
        record["files"]["patch"] = str(stem.with_suffix(".patch"))
        (cand_skill / "SKILL.md").write_text(candidate_text, encoding="utf-8")

        # Both sides on every fixture, through the call `improve` measures its
        # candidate with; the judge never runs (the rule reads objective checks).
        record["runs"] = {}
        sides = {}
        for side, root in (("baseline", base_root), ("candidate", cand_root)):
            out = run_paths(results, side, skill, ts)
            record["runs"][side] = str(out)
            rc = runner.run_eval(run_eval_argv(skill, registry["name"], root, out, ts,
                                               args.trials, True, read_deny=results))
            if rc not in (EXIT_ACCEPTED, EXIT_REJECTED):
                record.update(status="refused", phase=side, exit_code=rc,
                              reasons=[f"local_eval exited {rc} during {side}"])
                write_record(stem, record)
                print(f"refused: local_eval {side} exited {rc}; record: "
                      f"{stem.with_suffix('.json')}", file=sys.stderr)
                return EXIT_REFUSED
            sides[side] = {n: fixture_metrics(out, skill, ts, n, args.trials) for n in names}
            record["trim"][side] = {n: trim_counts(m) for n, m in sides[side].items()}

        accepted, reasons = decide_trim(sides["baseline"], sides["candidate"], names)
        record.update(status="accepted" if accepted else "rejected", reasons=reasons)
        if accepted:
            body_path = stem.with_name(stem.name + ".pr-body.md")
            record["files"]["pr_body"] = str(body_path)
            body_path.write_text(trim_pr_body(record), encoding="utf-8")
        write_record(stem, record)
        print(f"{record['status']}: {'; '.join(reasons)}")
        print(f"record: {stem.with_suffix('.json')}")
        return EXIT_ACCEPTED if accepted else EXIT_REJECTED
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def record_refusal(stem: Path, record: dict, phase: str, exc: Refusal) -> int:
    record.update(status="refused", phase=phase, exit_code=EXIT_REFUSED,
                  reasons=[str(exc)])
    write_record(stem, record)
    print(f"refused during {phase}: {exc}; record: {stem.with_suffix('.json')}",
          file=sys.stderr)
    return EXIT_REFUSED


def write_record(stem: Path, record: dict) -> None:
    record["decision"] = {"invalid-proposal": "rejected",
                          "trigger-set-unusable": "refused"}.get(
                              record["status"], record["status"])
    record["files"]["record"] = str(stem.with_suffix(".json"))
    stem.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n",
                                         encoding="utf-8")


def main(argv: list[str] | None = None, runner: Runner | None = None,
         now: datetime | None = None) -> int:
    args = parse_args(argv)
    try:
        pipeline = (improve_trim if args.trim_description
                    else improve_trigger_only if args.trigger_only else improve)
        return pipeline(args, runner or Runner(), now or datetime.now(timezone.utc))
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
