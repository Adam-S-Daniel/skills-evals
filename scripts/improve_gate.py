#!/usr/bin/env python3
"""Validate a routine's `claude/eval-improve-<run id>` branch and apply it.

The improvement loop's routine mode (ADR 0005 amendment 1; ADR 0010). The
eval routine runs `scripts/propose_skill_edit.py` and, when its candidate is
ACCEPTED, pushes one branch holding exactly

    eval-improve/<run id>/summary.json   the loop's record (`<ts>.json`)
    eval-improve/<run id>/report.md      its pull-request body (`<ts>.pr-body.md`)
    eval-improve/<run id>/skill.patch    its registry patch (`<ts>.patch`)

and nothing else. It never opens a pull request. The branch is UNTRUSTED
input (a model run wrote it): `.github/workflows/routine-improve-gate.yml`
runs this script from the default branch's checkout, and it reads the branch
only through git plumbing (`git diff --raw`, `git cat-file`), reusing
`ingest_routine_results.py`'s helpers. Nothing from the branch is executed,
imported or checked out; `apply` hands the validated patch to `git apply` in
a registry checkout, as data.

`eval-improve/` is not `eval-results/`: `claude/eval-improve-*` also matches
the results signal's `claude/eval-*` branch filter, and only the two path
filters keep an improve push from starting a results ingest (and a results
push from starting this gate).

What a branch must look like to pass:

  * its name is `claude/eval-improve-<YYYYMMDDTHHMMSSZ>-<6 hex>`;
  * against its merge-base with the default branch it ADDS exactly the three
    files above, regular and non-executable, under its own run id;
  * summary.json is an `accepted` record (schema 1) for the adam-agentskills
    registry at a full commit sha, whose `skill_md` is that registry's
    `plugins/<plugin>/skills/<skill>/SKILL.md` for the record's own skill,
    and the skill has fixtures under `evals/<skill>/` on the default branch;
  * skill.patch is a unified diff of that one path and nothing else, every
    hunk's line counts agreeing with its header;
  * report.md opens with the loop's own title and holds no closing keyword
    or @mention (it becomes a pull-request body in another repository);
  * every file is under its size cap and valid UTF-8 with no control
    characters.

Subcommands (output is `key=value` lines of validated values, for
$GITHUB_OUTPUT):

  resolve  --event-name NAME --event-path PATH
  validate --repo DIR --base REF --source REF --branch NAME
           [--expect-sha SHA] --out DIR
  apply    --staged DIR --tree DIR --skill-md PATH
  prepare  --staged DIR --tree DIR --skill-md PATH --registry-sha SHA
           --run-id ID [--policy FILE]
  pr-body  --staged DIR --run-id ID --sha SHA --branch NAME
           [--mode draft|auto]                          (body on stdout)
  merge-mode --tree DIR --plugin NAME --skill NAME [--policy FILE]   (mode=, mode_reason=)
  fire-check SKILL [--holdout NAME] [--trigger-only | --trim]
                                                        (no output; exit 0 or 1)

`prepare` builds the whole registry change on a clean checkout of
adam-agentskills' default branch tip, holding no credential: the patch
(`apply`), a `PURPOSE.md` stub when the skill has none, the plugin's patch
version raised in both manifests (adam-agentskills ADR 0009), a
`docs/skill-impact.md` entry, the README table regenerated, then a second
commit re-pinning `skills.lock` to the first when the lock covers the
skill (the registry's own `scripts/` do the last two). Those are what the
registry's required checks and AGENTS.md ask of a skill edit. It prints the
merge mode: `evals/improve-policy.yml`'s `improve_merge_mode`, or `draft`
when adam-agentskills' plugin-runtime-review would hold the change
(`auto_refusal`: the skill has its own `hooks/` or `bin/`, or a hook of its
plugin names a path in it), so an auto-merged pull request never waits on
that review. A skill's text is not runtime, whatever its plugin holds.
`merge-mode` prints the same decision (`effective_mode`) for
routine-draft-skill-gate.yml, so one policy file switches every loop gate
that writes adam-agentskills.

A TRIGGER-ONLY record (`"mode": "trigger-only"`, skills-evals#662: only
skill-creator's description loop ran, on the skill's reviewed
`evals/<skill>/trigger-eval-set.json`) has no split, baseline or candidate.
It must name that set, present as a regular file on the default branch
instead of fixtures, and `check_trigger_only` re-verifies its acceptance from
its own counts (a held-out pass-rate gain of at least TRIGGER_ONLY_MIN_GAIN,
no should-not-trigger drop) rather than trusting its status. `apply` then
refuses any change to the SKILL.md body, and `impact_entry` records the
trigger counts. A TRIM record (`"mode": "trim"`, skills-evals#687: only the
description was shortened, to at most TRIM_MAX_CHARS characters, and
measured on every fixture) gets its own key sets; `check_trim` re-derives
its acceptance from its `trim` block's per-fixture counts with the loop's
rule (propose_skill_edit.decide_trim, its constants mirrored here), `apply`
refuses a body change or a resulting description over the cap, `prepare`
also removes the skill's `length-limit` waiver from the registry's
`scripts/skills_waivers.yml` (`remove_length_waiver`; nothing when there is
none), and `impact_entry` records the fixture counts. Any other `mode` value
is rejected.

`fire-check` is the other end: `routine-eval-fire.yml` runs it before the
fire bearer exists, so a skill the loop would refuse never starts a routine
session. It reuses the loop's own resolution (`skill_fixtures`,
`load_fixtures`, `MIN_FIXTURES`) and harness/registries.yml, read-only and
offline. The loop's last step, finding `<skill>/SKILL.md` in the registry
checkout, needs that checkout, which the fire job does not have, so that
step stays the routine's. `--trigger-only` checks a trigger-only fire
instead: an empty holdout, the committed reviewed set the loop's own loader
and `trigger_only_set` accept, any number of fixtures (zero included), and
adam-agentskills as every fixture's registry. `--trim` checks a trim fire:
an empty holdout and the ordinary check's fixtures (at least MIN_FIXTURES,
one registry, adam-agentskills), since a trim is measured on them.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ingest_routine_results as ingest  # noqa: E402
from ingest_routine_results import Rejected  # noqa: E402

BRANCH_RE = re.compile(rf"claude/eval-improve-(?P<run_id>{ingest.RUN_ID})")
BRANCH_SHAPE = "claude/eval-improve-<run id>"
#: The one top-level directory an improve branch adds to.
SOURCE_ROOT = "eval-improve"
#: Every file the branch must add, with its byte cap.
SIZE_CAPS = {"summary.json": 256 * 1024, "report.md": 64 * 1024,
             "skill.patch": 128 * 1024}

#: The only registry a pull request is opened in. ADR 0010 decision 1
#: lets routine arms run only the registries' default branches; this gate
#: further limits the loop's output to the one registry it targets.
REGISTRY_NAME = "adam-agentskills"
REGISTRY_URL = "https://github.com/Adam-S-Daniel/adam-agentskills"
NAME = r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
#: adam-agentskills' layout (harness/registries.yml: plugins/*/skills/*/SKILL.md).
SKILL_MD_RE = re.compile(rf"plugins/(?P<plugin>{NAME})/skills/(?P<skill>{NAME})/SKILL\.md")
NAME_RE = re.compile(NAME)
#: The branch the pull request comes from in adam-agentskills: one per skill,
#: so a second accepted candidate waits until the first has merged (and its
#: branch was deleted) or was closed (ADR 0005, "the idempotency check on an
#: open eval-improve/<skill> branch").
TARGET_BRANCH = "eval-improve/{skill}"

#: The improvement gate's policy: `improve_merge_mode`.
POLICY = Path(__file__).resolve().parent.parent / "evals" / "improve-policy.yml"
MERGE_MODES = ("auto", "draft")
#: A policy that names no mode (Adam, 2026-10-26: accepted improvements merge
#: with no human in the loop).
DEFAULT_MERGE_MODE = "auto"
#: The places adam-agentskills' scripts/plugin_runtime_gate.py reads to
#: decide whether a pull request changes how a plugin runs code: a hook's
#: command names a path after the plugin root, and a skill's own `hooks/` or
#: `bin/` directory is a runtime path. A loop pull request that only adds,
#: edits or removes a skill's text is not one of those, whatever else the
#: plugin holds (Adam, 2026-11-03: text-only loop skill pull requests in
#: plugins with hooks auto-merge; the gate still holds the rest).
SKILL_RUNTIME_DIRS = ("hooks", "bin")
#: Where a plugin's hooks can name a path: its hooks/ JSON, the two
#: manifests (an inline `hooks` value) and its settings file.
HOOK_CONFIG_MAX = 1024 * 1024
#: The registry files `prepare` writes besides the skill's own directory.
IMPACT_FILE = "docs/skill-impact.md"
README = "README.md"
LOCK = "skills.lock"
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json")
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
#: The registry ADR that lets an accepted improvement merge itself.
REGISTRY_ADR = (f"{REGISTRY_URL}/blob/main/docs/decisions/"
                "0021-automated-skill-changes-merge-without-review.md")
#: Who commits in the registry checkout. The App's token pushes the commits;
#: it does not author them.
COMMIT_IDENTITY = ("-c", "user.name=skills-evals improve-gate bot",
                   "-c", "user.email=skills-evals@users.noreply.github.com")
#: The fleet's marker for a GitHub contribution an agent wrote on Adam's
#: behalf (_agent-guidance ADR 0023); the candidate is a Claude Code run's.
AGENT_MARKER = ("<sub>🤖 Written by Claude Code on behalf of "
                "@Adam-S-Daniel</sub>")

#: The repository secrets the pull-request job mints its GitHub App token from
#: (owner decision, Adam: "GitHub App (Recommended)"): the App's client id
#: and its private key in PEM form. Neither name holds one of gitleaks'
#: generic-api-key keywords (ADR 0010 decision 5).
APP_CLIENT_ID_SECRET = "EVAL_IMPROVE_APP_CLIENT_ID"
APP_PEM_SECRET = "EVAL_IMPROVE_APP_PEM"

#: propose_skill_edit.improve()'s record keys (the suite reads them from its
#: AST and checks they stay inside these sets).
RECORD_REQUIRED = ("schema", "skill", "timestamp", "registry", "split",
                   "trials", "status", "reasons", "baseline", "candidate",
                   "description_half", "body_half", "table", "files")
RECORD_ALLOWED = RECORD_REQUIRED + (
    "local_exhibit", "no_judge", "min_gain", "models", "runs", "trigger_set",
    "phase", "exit_code", "decision", "tokens_basis", "heldout_screen",
    "mode", "trigger_only")
#: propose_skill_edit.improve_trigger_only()'s record keys (skills-evals#662):
#: the ones an accepted trigger-only record must carry, and the only others
#: it may (its refusal and decision fields). No split, baseline or
#: candidate: no task fixture was measured.
TRIGGER_MODE = "trigger-only"
TRIGGER_RECORD_REQUIRED = ("schema", "skill", "timestamp", "mode",
                           "local_exhibit", "registry", "models", "trigger_set",
                           "description_half", "trigger_only", "status",
                           "reasons", "files")
TRIGGER_RECORD_ALLOWED = TRIGGER_RECORD_REQUIRED + ("phase", "exit_code", "decision")
#: The held-out trigger pass-rate gain a trigger-only record must show,
#: re-verified from its counts (propose_skill_edit.TRIGGER_ONLY_MIN_GAIN;
#: a test holds the two equal). Adam, 2026-11-03, the #662 decision card.
TRIGGER_ONLY_MIN_GAIN = 0.15
#: A trigger-only record's reviewed query set, under evals/<skill>/
#: (propose_skill_edit.TRIGGER_SET_FILE).
TRIGGER_SET_FILE = "trigger-eval-set.json"
TRIGGER_COUNT_KEYS = ("test_passed", "test_total", "should_not_passed",
                      "should_not_total")
#: propose_skill_edit.improve_trim()'s record keys (skills-evals#687): the
#: ones an accepted trim record must carry, and the only others it may.
TRIM_MODE = "trim"
TRIM_RECORD_REQUIRED = ("schema", "skill", "timestamp", "mode", "local_exhibit",
                        "registry", "models", "trials", "description", "trim",
                        "status", "reasons", "files")
TRIM_RECORD_ALLOWED = TRIM_RECORD_REQUIRED + ("no_judge", "runs", "phase",
                                             "exit_code", "decision")
TRIM_BLOCK_KEYS = ("max_chars", "original_chars", "candidate_chars", "rule",
                   "tolerance_checks", "fixture_drop_checks", "baseline", "candidate")
#: The trim rule, mirrored from propose_skill_edit (TRIM_MAX_CHARS,
#: TRIM_TOLERANCE_CHECKS, TRIM_FIXTURE_DROP_CHECKS, TRIM_RULE; a test holds
#: them equal): adam-agentskills' 400-character description cap, no fewer
#: objective passes summed over every fixture, and at most one lost pass on
#: any one fixture.
TRIM_MAX_CHARS = 400
TRIM_TOLERANCE_CHECKS = 0
TRIM_FIXTURE_DROP_CHECKS = 1
TRIM_RULE = "aggregate-noninferior-per-fixture-drop-1"
#: The registry's waiver file and the waiver a trim retires (adam-agentskills
#: scripts/check_skills.py: a waiver matching no finding fails its build, so
#: the trim's pull request must remove it in the same change).
WAIVERS_FILE = "scripts/skills_waivers.yml"
LENGTH_WAIVER_CLASS = "length-limit"
#: The values a record's `tokens_basis` may take (propose_skill_edit's
#: TOKENS_BASIS and TOKENS_BASIS_LEGACY); a record without one predates it.
TOKENS_BASES = ("model_usage_total", "usage_main_loop")
MAX_RECORD_STRING = 32 * 1024
MAX_RECORD_DEPTH = 10
MAX_RECORD_ITEMS = 512

REPORT_TITLE = "## Proposed `{skill}` SKILL.md edit (validation-gated)"
#: GitHub closes an issue or pull request named after one of these keywords
#: in a merged pull request's body, in any repository; a model-written
#: report must not be able to do that. Matched against the text with its
#: Markdown emphasis, code and link syntax stripped (`closing_text`), so
#: `**Fixes** #1` or `Fixes [#1](...)` cannot hide one; a link's target URL
#: is kept, so `Closes [x](https://github.com/o/r/issues/7)` is caught too.
_KEYWORD = r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b[\s:<]*"
CLOSING_RE = re.compile(
    _KEYWORD + r"(?:(?:[\w.-]+/[\w.-]+)?#\d+"
    r"|https?://github\.com/[^\s/]+/[^\s/]+/(?:issues|pull)/\d+)", re.I)
#: A keyword with an issue or pull request URL anywhere later on its line
#: (a link label can sit between the two). Over-rejects; that is fine.
CLOSING_URL_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b[^\n]*?"
    r"https?://github\.com/[^\s/]+/[^\s/]+/(?:issues|pull)/\d+", re.I)
#: Markdown that can sit between a keyword and its reference.
_MARKDOWN_NOISE = re.compile(r"[*_`~\[\]]")
_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]*)[^)]*\)")
#: An @mention notifies a person. Only a letter or digit right before the @
#: (an email address, an `action@sha` pin) makes it something else;
#: punctuation does not, so this over-rejects rather than miss one.
MENTION_RE = re.compile(r"(?<![A-Za-z0-9])@[A-Za-z0-9][A-Za-z0-9-]*")
HUNK_RE = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?")


# ---------------------------------------------------------------------------
# Content.

def bounded(value, where: str, depth: int = 0) -> None:
    """Any JSON value, within the record's depth, string and size limits
    (larger than a result summary's: a record carries the proposal's diff
    and rationale)."""
    if depth > MAX_RECORD_DEPTH:
        raise Rejected(f"{where}: nested too deep")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if not ingest.is_number(value):
            raise Rejected(f"{where}: not a finite number")
        return
    if isinstance(value, str):
        if len(value) > MAX_RECORD_STRING:
            raise Rejected(f"{where}: string too long")
        return
    if isinstance(value, (list, dict)):
        if len(value) > MAX_RECORD_ITEMS:
            raise Rejected(f"{where}: too many items")
        items = value.items() if isinstance(value, dict) else enumerate(value)
        for key, item in items:
            if isinstance(key, str) and len(key) > 128:
                raise Rejected(f"{where}: key too long")
            bounded(item, where, depth + 1)
        return
    raise Rejected(f"{where}: unexpected JSON type")


def check_record(doc, where: str, repo: str) -> dict:
    mode = doc.get("mode") if isinstance(doc, dict) else None
    if isinstance(doc, dict) and "mode" in doc and mode not in (TRIGGER_MODE, TRIM_MODE):
        raise Rejected(f"{where}: unknown mode")
    trigger, trim = mode == TRIGGER_MODE, mode == TRIM_MODE
    if isinstance(doc, dict) and "trigger_only" in doc and not trigger:
        raise Rejected(f"{where}: a trigger_only block needs mode trigger-only")
    if trigger:
        ingest._object(doc, where, TRIGGER_RECORD_ALLOWED, TRIGGER_RECORD_REQUIRED)
    elif trim:
        ingest._object(doc, where, TRIM_RECORD_ALLOWED, TRIM_RECORD_REQUIRED)
    else:
        ingest._object(doc, where, RECORD_ALLOWED, RECORD_REQUIRED)
    bounded(doc, where)
    if doc["schema"] != 1 or isinstance(doc["schema"], bool):
        raise Rejected(f"{where}: unknown schema")
    if doc["status"] != "accepted":
        raise Rejected(f"{where}: status is not accepted; the routine pushes "
                       "only an accepted candidate")
    if "decision" in doc and doc["decision"] != "accepted":
        raise Rejected(f"{where}: decision is not accepted")
    if "tokens_basis" in doc and doc["tokens_basis"] not in TOKENS_BASES:
        raise Rejected(f"{where}: unknown tokens_basis")
    skill = doc["skill"]
    if not isinstance(skill, str) or not NAME_RE.fullmatch(skill):
        raise Rejected(f"{where}: bad skill name")
    if not isinstance(doc["timestamp"], str) \
            or not ingest.TIMESTAMP_RE.fullmatch(doc["timestamp"]):
        raise Rejected(f"{where}: bad timestamp")
    if not trigger:
        ingest._integer(doc["trials"], f"{where}: trials", 1, ingest.MAX_TRIALS)
    reasons = doc["reasons"]
    if not isinstance(reasons, list) or not reasons \
            or not all(isinstance(r, str) for r in reasons):
        raise Rejected(f"{where}: reasons must be a list of strings")

    registry = doc["registry"]
    keys = ("name", "url", "sha", "skill_md")
    ingest._object(registry, f"{where}: registry", keys, keys)
    if registry["name"] != REGISTRY_NAME or registry["url"] != REGISTRY_URL:
        raise Rejected(f"{where}: registry is not {REGISTRY_NAME}")
    if not isinstance(registry["sha"], str) \
            or not ingest.SHA_RE.fullmatch(registry["sha"]):
        raise Rejected(f"{where}: registry sha is not a 40-hex commit id")
    match = SKILL_MD_RE.fullmatch(registry["skill_md"]) \
        if isinstance(registry["skill_md"], str) else None
    if not match or match.group("skill") != skill \
            or ".." in registry["skill_md"].split("/"):
        raise Rejected(f"{where}: registry skill_md is not this skill's "
                       "SKILL.md")
    found = {"skill": skill, "registry_sha": registry["sha"],
             "skill_md": registry["skill_md"]}

    if trigger:
        check_trigger_only(doc["trigger_only"], where)
        trigger_set = Path(repo) / "evals" / skill / TRIGGER_SET_FILE
        if trigger_set.is_symlink() or not trigger_set.is_file():
            raise Rejected(f"{where}: skill has no reviewed trigger eval set "
                           "under evals/ on the default branch")
        return found
    if trim:
        check_trim(doc, where)
        if not (Path(repo) / "evals" / skill).is_dir():
            raise Rejected(f"{where}: skill has no evals/ directory on the "
                           "default branch")
        return found

    split = doc["split"]
    ingest._object(split, f"{where}: split",
                   ("rotation", "train", "validation", "holdout"),
                   ("rotation", "train", "validation"))
    names = split["train"] if isinstance(split["train"], list) else [None]
    names = names + [split["validation"]] + (
        [split["holdout"]] if "holdout" in split else [])
    if not all(isinstance(n, str) and NAME_RE.fullmatch(n) for n in names):
        raise Rejected(f"{where}: bad fixture name in split")
    held = (doc["baseline"].get(split["validation"])
            if isinstance(doc["baseline"], dict) else None)
    if isinstance(held, dict) and type(held.get("passed")) is int \
            and type(held.get("total")) is int and held["total"] >= 1 \
            and held["passed"] == held["total"]:
        raise Rejected(f"{where}: the held-out fixture passed every check on "
                       "the baseline, so it cannot show the edit carries over "
                       "(propose_skill_edit's held-out screen)")

    if not (Path(repo) / "evals" / skill).is_dir():
        raise Rejected(f"{where}: skill has no evals/ directory on the "
                       "default branch")
    return found


def check_trigger_only(block, where: str) -> None:
    """Re-verify a trigger-only record's acceptance from its own counts
    (propose_skill_edit.decide_trigger_only's rule), so a record whose
    status says accepted while its numbers do not is never applied: the same
    held-out and should-not-trigger totals on both sides, a held-out
    pass-rate gain of at least TRIGGER_ONLY_MIN_GAIN, and no fewer
    should-not-trigger passes. Fixed-text rejections only."""
    where = f"{where}: trigger_only"
    ingest._object(block, where, ("min_gain", "original", "best", "gain"),
                   ("min_gain", "original", "best", "gain"))
    for side in ("original", "best"):
        counts = block[side]
        ingest._object(counts, f"{where}: {side}", TRIGGER_COUNT_KEYS,
                       TRIGGER_COUNT_KEYS)
        for key in TRIGGER_COUNT_KEYS:
            ingest._integer(counts[key], f"{where}: {side}", 0, 10 ** 6)
        if counts["test_passed"] > counts["test_total"] \
                or counts["should_not_passed"] > counts["should_not_total"]:
            raise Rejected(f"{where}: more queries passed than were run")
    original, best = block["original"], block["best"]
    if original["test_total"] < 1 or original["test_total"] != best["test_total"] \
            or original["should_not_total"] != best["should_not_total"]:
        raise Rejected(f"{where}: the original and the best were not measured "
                       "on the same queries")
    total = original["test_total"]
    gain = (best["test_passed"] - original["test_passed"]) / total
    if not ingest.is_number(block["gain"]) or isinstance(block["gain"], bool) \
            or abs(block["gain"] - gain) > 1e-9:
        raise Rejected(f"{where}: gain disagrees with its counts")
    if not ingest.is_number(block["min_gain"]) or isinstance(block["min_gain"], bool):
        raise Rejected(f"{where}: min_gain is not a number")
    if gain < TRIGGER_ONLY_MIN_GAIN and abs(gain - TRIGGER_ONLY_MIN_GAIN) > 1e-12:
        raise Rejected(f"{where}: held-out trigger accuracy rose by less than "
                       "the minimum gain")
    if best["should_not_passed"] < original["should_not_passed"]:
        raise Rejected(f"{where}: fewer should-not-trigger queries passed")


def _count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def check_trim(doc: dict, where: str) -> None:
    """Re-verify a trim record's acceptance from its own `trim` block
    (propose_skill_edit.decide_trim's rule), so a record whose status says
    accepted while its numbers do not is never applied: the rule and its
    constants are this gate's, the candidate's description is non-empty and
    at most TRIM_MAX_CHARS characters (its `candidate_chars` agreeing), the
    original was over the cap, both sides list the same fixtures with
    integer counts and equal totals, the summed passes do not fall by more
    than TRIM_TOLERANCE_CHECKS, and no fixture falls by more than
    TRIM_FIXTURE_DROP_CHECKS. Fixed-text rejections only."""
    block = doc["trim"]
    where = f"{where}: trim"
    ingest._object(block, where, TRIM_BLOCK_KEYS, TRIM_BLOCK_KEYS)
    if block["rule"] != TRIM_RULE or block["max_chars"] != TRIM_MAX_CHARS \
            or block["tolerance_checks"] != TRIM_TOLERANCE_CHECKS \
            or block["fixture_drop_checks"] != TRIM_FIXTURE_DROP_CHECKS \
            or any(isinstance(block[k], bool) for k in
                   ("max_chars", "tolerance_checks", "fixture_drop_checks")):
        raise Rejected(f"{where}: not this gate's trim rule")
    description = doc["description"]
    ingest._object(description, f"{where}: description", ("original", "candidate"),
                   ("original", "candidate"))
    candidate, original = description["candidate"], description["original"]
    if not isinstance(candidate, str) or not isinstance(original, str):
        raise Rejected(f"{where}: description is not two strings")
    if not 1 <= len(candidate) <= TRIM_MAX_CHARS or "\n" in candidate \
            or candidate != " ".join(candidate.split()) \
            or block["candidate_chars"] != len(candidate) \
            or not _count(block["candidate_chars"]):
        raise Rejected(f"{where}: the candidate description is not within the cap")
    if block["original_chars"] != len(original) or not _count(block["original_chars"]) \
            or len(original) <= TRIM_MAX_CHARS:
        raise Rejected(f"{where}: the original description was not over the cap")
    baseline, cand = block["baseline"], block["candidate"]
    if not isinstance(baseline, dict) or not isinstance(cand, dict) or not baseline \
            or set(baseline) != set(cand) \
            or not all(isinstance(n, str) and NAME_RE.fullmatch(n) for n in baseline):
        raise Rejected(f"{where}: the sides do not list the same fixtures")
    for side in (baseline, cand):
        for name, counts in side.items():
            ingest._object(counts, f"{where}: fixture", ("passed", "total"),
                           ("passed", "total"))
            if not _count(counts["passed"]) or not _count(counts["total"]) \
                    or counts["passed"] > counts["total"] or counts["total"] < 1:
                raise Rejected(f"{where}: a fixture's counts are not checks passed of run")
    if any(baseline[n]["total"] != cand[n]["total"] for n in baseline):
        raise Rejected(f"{where}: a fixture ran different checks on the two sides")
    before = sum(c["passed"] for c in baseline.values())
    after = sum(c["passed"] for c in cand.values())
    if after < before - TRIM_TOLERANCE_CHECKS:
        raise Rejected(f"{where}: the candidate passed fewer checks in aggregate")
    if any(baseline[n]["passed"] - cand[n]["passed"] > TRIM_FIXTURE_DROP_CHECKS
           for n in baseline):
        raise Rejected(f"{where}: a fixture lost more checks than the rule allows")


def staged_mode(staged: Path) -> str | None:
    """The staged summary.json's `mode` (None for an ordinary record, or for
    no staged record: an `apply` run by hand on a bare patch). An unreadable
    record is refused rather than read as any mode."""
    path = staged / "summary.json"
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise Rejected("the staged record is unreadable") from None
    mode = doc.get("mode") if isinstance(doc, dict) else None
    return mode if isinstance(mode, str) else None


def is_trigger_record(staged: Path) -> bool:
    """Whether the staged summary.json is a trigger-only record. No staged
    record (an `apply` run by hand on a bare patch) is not one; an
    unreadable one is refused rather than read as either."""
    return staged_mode(staged) == TRIGGER_MODE


def check_patch(text: str, where: str, skill_md: str) -> None:
    """A unified diff of `skill_md` only, as difflib writes it."""
    if not text.endswith("\n"):
        raise Rejected(f"{where}: does not end with a newline")
    lines = text[:-1].split("\n")
    if lines[:2] != [f"--- a/{skill_md}", f"+++ b/{skill_md}"]:
        raise Rejected(f"{where}: must change {skill_md!r} and nothing else")
    i, hunks, changed = check_hunks(lines, 2, where)
    if i < len(lines):
        raise Rejected(f"{where}: line {i + 1} is not a hunk header")
    if not hunks or not changed:
        raise Rejected(f"{where}: changes nothing")


def check_hunks(lines: list, i: int, where: str) -> tuple[int, int, int]:
    """(index of the first line after them, hunks, changed lines) of the
    unified-diff hunks starting at `lines[i]`, every hunk's line counts
    agreeing with its header. Stops at the first line that is not a hunk
    header; scripts/guidance_improve_gate.py reads a multi-file patch with
    it."""
    changed = hunks = 0
    while i < len(lines):
        header = HUNK_RE.fullmatch(lines[i])
        if not header:
            break
        old = int(header.group(2) if header.group(2) is not None else 1)
        new = int(header.group(4) if header.group(4) is not None else 1)
        hunks += 1
        i += 1
        while old or new:
            if i >= len(lines):
                raise Rejected(f"{where}: hunk {hunks} is shorter than its "
                               "header")
            mark = lines[i][:1]
            if mark == " " and old and new:
                old, new = old - 1, new - 1
            elif mark == "-" and old:
                old, changed = old - 1, changed + 1
            elif mark == "+" and new:
                new, changed = new - 1, changed + 1
            else:
                raise Rejected(f"{where}: line {i + 1} does not fit hunk "
                               f"{hunks}")
            i += 1
    return i, hunks, changed


def closing_text(text: str) -> str:
    """`text` with each Markdown link reduced to its label and target, and
    emphasis, code and bracket characters removed."""
    return _MARKDOWN_NOISE.sub("", _LINK.sub(r"\1 \2", text))


def check_report(text: str, where: str, skill: str) -> None:
    if text.split("\n", 1)[0] != REPORT_TITLE.format(skill=skill):
        raise Rejected(f"{where}: does not open with the loop's title for "
                       "this skill")
    check_body_text(text, where)


def check_body_text(text: str, where: str) -> None:
    """Refuse text that would act on GitHub as a pull-request body in
    another repository: a closing keyword before an issue or pull request
    reference, or an @mention."""
    stripped = closing_text(text)
    if CLOSING_RE.search(text) or CLOSING_RE.search(stripped) \
            or CLOSING_URL_RE.search(stripped):
        raise Rejected(f"{where}: has a closing keyword before an issue or "
                       "pull request reference")
    if MENTION_RE.search(text):
        raise Rejected(f"{where}: has an @mention")


# ---------------------------------------------------------------------------
# Subcommands.

def validate(repo: str, base: str, source: str, branch: str,
             expect_sha: str | None, out: Path) -> dict:
    match = BRANCH_RE.fullmatch(branch)
    if not match:
        raise Rejected(f"branch name is not {BRANCH_SHAPE}")
    run_id = match.group("run_id")
    tip = ingest.resolve_commit(repo, source)
    if expect_sha is not None:
        if not ingest.SHA_RE.fullmatch(expect_sha):
            raise Rejected("expected sha is not a 40-hex commit id")
        if tip != expect_sha:
            raise Rejected("the branch moved since the push that triggered "
                           "this run; that newer push triggers its own gate")
    base_sha = ingest.resolve_commit(repo, base)
    merge_base = ingest.git(repo, "merge-base", base_sha, tip).decode().strip()
    if not ingest.SHA_RE.fullmatch(merge_base):
        raise Rejected("the branch shares no history with the default branch")

    prefix = f"{SOURCE_ROOT}/{run_id}/"
    files = {}
    for name, _, oid in ingest.added_files(repo, merge_base, tip):
        if not name.startswith(prefix):
            raise Rejected(f"{name!r}: not under {prefix!r}")
        kind = name[len(prefix):]
        if kind not in SIZE_CAPS:
            raise Rejected(f"{name!r}: not a file an improve branch carries")
        size = int(ingest.git(repo, "cat-file", "-s", oid).decode().strip())
        if size > SIZE_CAPS[kind]:
            raise Rejected(f"{name!r}: {size} bytes is over the {kind} cap")
        data = ingest.git(repo, "cat-file", "blob", oid)
        if len(data) != size:
            raise Rejected(f"{name!r}: size changed while reading")
        files[kind] = (repr(name), data)
    missing = sorted(set(SIZE_CAPS) - set(files))
    if missing:
        raise Rejected(f"{missing}: missing under {prefix!r}")

    where, data = files["summary.json"]
    found = check_record(
        ingest.load_json(ingest.decode_text(data, where), where), where, repo)
    where, data = files["skill.patch"]
    check_patch(ingest.decode_text(data, where), where, found["skill_md"])
    where, data = files["report.md"]
    check_report(ingest.decode_text(data, where), where, found["skill"])

    if out.exists() and any(out.iterdir()):
        raise Rejected("the staging directory is not empty")
    out.mkdir(parents=True, exist_ok=True)
    for kind, (_, data) in files.items():
        (out / kind).write_bytes(data)
    return {"run_id": run_id, "sha": tip, **found,
            "target_branch": TARGET_BRANCH.format(skill=found["skill"])}


def _frontmatter(text: str, where: str) -> dict:
    if not text.startswith("---\n") or "\n---\n" not in text[3:]:
        raise Rejected(f"{where}: has no frontmatter")
    try:
        data = yaml.safe_load(text[4:text.index("\n---\n", 3)])
    except yaml.YAMLError:
        raise Rejected(f"{where}: frontmatter is not YAML") from None
    if not isinstance(data, dict):
        raise Rejected(f"{where}: frontmatter is not a mapping")
    return data


def _body(text: str) -> str:
    """A SKILL.md's text after its frontmatter (`_frontmatter` has already
    found the closing `---`)."""
    return text[text.index("\n---\n", 3) + len("\n---\n"):]


def apply(staged: Path, tree: Path, skill_md: str) -> dict:
    """Apply the staged patch to a registry checkout at `tree`. Only
    `skill_md` may change, and only its frontmatter's `description` may
    change there (propose_skill_edit.set_description's rule: the name is
    fixed, the description is the trigger half's, and nothing else moves).
    For a trigger-only record (skills-evals#662) the body may not change
    either: only the description loop ran, so the description is all it can
    have measured. Nor for a trim record (skills-evals#687), whose resulting
    description must also be at most TRIM_MAX_CHARS characters, read back
    from the patched frontmatter as adam-agentskills' checker reads it."""
    if not SKILL_MD_RE.fullmatch(skill_md) or ".." in skill_md.split("/"):
        raise Rejected("skill_md is not a registry SKILL.md path")
    cursor = tree
    for part in Path(skill_md).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise Rejected(f"{skill_md!r}: the registry path has a symlink")
    target = tree / skill_md
    if not target.is_file():
        raise Rejected(f"{skill_md!r}: not in the registry checkout")
    mode = staged_mode(staged)
    trigger, trim = mode == TRIGGER_MODE, mode == TRIM_MODE
    before_text = target.read_text(encoding="utf-8")
    before = _frontmatter(before_text, skill_md)
    patch = str((staged / "skill.patch").resolve())
    for args in (("apply", "--check", patch), ("apply", patch)):
        # Raw git is fine here (#343): the gate's own registry checkout at a recorded sha, never an agent-touched
        # workspace, so harness/workspace_git.py does not apply.
        result = subprocess.run(["git", "-C", str(tree), *args],
                                capture_output=True, check=False)
        if result.returncode != 0:
            raise Rejected("the patch does not apply to the registry at the "
                           "recorded sha")
    after_text = target.read_text(encoding="utf-8")
    after = _frontmatter(after_text, skill_md)
    if trigger and _body(after_text) != _body(before_text):
        raise Rejected(f"{skill_md!r}: a trigger-only patch changes the body; "
                       "only the description may change")
    if trim and _body(after_text) != _body(before_text):
        raise Rejected(f"{skill_md!r}: a trim patch changes the body; "
                       "only the description may change")
    if trim and (not isinstance(after.get("description"), str)
                 or not 1 <= len(after["description"]) <= TRIM_MAX_CHARS):
        raise Rejected(f"{skill_md!r}: the trimmed description is not within the "
                       f"{TRIM_MAX_CHARS}-character cap")
    if {k: v for k, v in after.items() if k != "description"} \
            != {k: v for k, v in before.items() if k != "description"} \
            or ("description" in after) != ("description" in before):
        raise Rejected(f"{skill_md!r}: the patch changes the frontmatter "
                       "beyond its description")
    changed = ingest.git(str(tree), "status", "--porcelain=v1", "-z").decode()
    if changed.split("\0")[:-1] != [f" M {skill_md}"]:
        raise Rejected("the patch changed more than the one SKILL.md")
    return {"changed": skill_md}


def merge_mode(path: Path = POLICY) -> str:
    """`improve_merge_mode` from the policy file. A missing key is
    DEFAULT_MERGE_MODE; anything unreadable, unknown or malformed is
    `draft`, the mode that merges nothing on its own."""
    try:
        doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError, ValueError):
        return "draft"
    if doc is None:
        doc = {}
    if not isinstance(doc, dict) or set(doc) - {"improve_merge_mode"}:
        return "draft"
    mode = doc.get("improve_merge_mode", DEFAULT_MERGE_MODE)
    return mode if mode in MERGE_MODES else "draft"


def _no_symlink(tree: Path, rel: str) -> Path:
    """`tree / rel`, refusing a symlink anywhere on the path (the file
    itself may be absent)."""
    cursor = tree
    for part in Path(rel).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise Rejected(f"{rel!r}: the registry path has a symlink")
    return cursor


def _manifest(tree: Path, rel: str) -> tuple[str, dict]:
    path = _no_symlink(tree, rel)
    try:
        text = path.read_text(encoding="utf-8")
        doc = json.loads(text)
    except (OSError, UnicodeDecodeError, ValueError):
        raise Rejected(f"cannot read {rel}") from None
    if not isinstance(doc, dict):
        raise Rejected(f"{rel} is not a JSON object")
    return text, doc


def _hook_config_texts(tree: Path, root: str) -> list[str]:
    """The text of every file under `root` a hook can be declared in: hooks/
    JSON files, the manifests and settings.json. Missing files are skipped;
    an unreadable one is a refusal, never a silent pass."""
    rels = [f"{root}/{name}" for name in MANIFESTS + ("settings.json",)]
    hooks = tree / root / "hooks"
    if hooks.is_symlink():
        raise Rejected(f"{root}/hooks is a symlink")
    if hooks.is_dir():
        rels += sorted(p.relative_to(tree).as_posix() for p in hooks.rglob("*.json"))
    texts = []
    for rel in rels:
        path = _no_symlink(tree, rel)
        if not path.is_file():
            continue
        if path.stat().st_size > HOOK_CONFIG_MAX:
            raise Rejected(f"{rel} is too large to read")
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            raise Rejected(f"cannot read {rel}") from None
    return texts


def auto_refusal(tree: Path, plugin: str, skill: str) -> str | None:
    """Why a loop pull request that changes `skill` may not be auto-merged,
    or None: when adam-agentskills' plugin-runtime-review would hold it (its
    ADR 0016), because auto-merge cannot approve that. That is a skill with
    its own `hooks/` or `bin/` directory, or one a hook of its plugin names
    a path in. Any other skill change, in any plugin, is text."""
    if not NAME_RE.fullmatch(skill):
        raise Rejected("skill is not a skill name")
    root = f"plugins/{plugin}"
    for name in SKILL_RUNTIME_DIRS:
        path = tree / root / "skills" / skill / name
        if path.exists() or path.is_symlink():
            return f"the skill has a runtime path ({name}/), which plugin-runtime-review holds"
    needle = f"skills/{skill}/"
    if any(needle in text or text.rstrip().endswith(f"skills/{skill}")
           for text in _hook_config_texts(tree, root)):
        return "a hook of the skill's plugin names a path in the skill, which plugin-runtime-review holds"
    return None


#: SKILL.md frontmatter keys that make a skill run code or widen what it may
#: do without asking. adam-agentskills' plugin-runtime-review does not read
#: frontmatter, but its one-way-door check (adam-agentskills#134, #135)
#: fails an armed loop pull request that sets or changes one, and nothing in
#: the loop would disarm it, so it would hold the one loop slot. An
#: improvement cannot change them (`apply` refuses any frontmatter change
#: but the description); a drafted skill can set them.
RUNTIME_FRONTMATTER = ("hooks", "allowed-tools")


def frontmatter_refusal(before: str | None, after: str) -> str | None:
    """Why a SKILL.md going from `before` (None: a new skill) to `after`
    may not be auto-merged, or None: it adds, changes or removes a
    RUNTIME_FRONTMATTER key. Unreadable frontmatter is a refusal too."""
    try:
        old = _frontmatter(before, "SKILL.md") if before is not None else {}
        new = _frontmatter(after, "SKILL.md")
    except Rejected:
        return "the SKILL.md frontmatter cannot be read, so its runtime keys cannot be checked"
    changed = [k for k in RUNTIME_FRONTMATTER
               if (k in old, old.get(k)) != (k in new, new.get(k))]
    if changed:
        return (f"the SKILL.md frontmatter sets or changes {', '.join(changed)}, which "
                "adam-agentskills' one-way-door check holds for a person")
    return None


def staged_skill_md(staged: Path, plugin: str, skill: str) -> str:
    """The SKILL.md a draft-skill staging directory's new-files patch adds
    (draft_new_skill.validate's `skill.patch`), or Rejected."""
    import draft_new_skill  # noqa: PLC0415 - it imports this module
    prefix = draft_new_skill.skill_prefix(plugin, skill)
    try:
        text = (staged / "skill.patch").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise Rejected("the staged skill.patch cannot be read") from None
    files = draft_new_skill.parse_new_files_patch(text, prefix)
    if "SKILL.md" not in files:
        raise Rejected("the staged skill.patch adds no SKILL.md")
    return files["SKILL.md"].decode("utf-8")


def effective_mode(tree: Path, plugin: str, skill: str, policy: Path = POLICY,
                   skill_md: str | None = None) -> dict:
    """The merge mode for a loop pull request that changes `skill` of
    `plugin` in the registry checkout `tree`: the policy's, lowered to
    `draft` (with the reason) when `auto_refusal` gives one, or, given the
    proposed SKILL.md text `skill_md`, when `frontmatter_refusal` does
    against the tree's current copy (none for a new skill). The one switch for
    every loop gate that writes adam-agentskills: this gate's `prepare` and
    routine-draft-skill-gate.yml's `merge-mode` step (with `--staged`)."""
    if not NAME_RE.fullmatch(plugin):
        raise Rejected("plugin is not a plugin name")
    mode = merge_mode(policy)
    reason = auto_refusal(tree, plugin, skill) if mode == "auto" else None
    if mode == "auto" and reason is None and skill_md is not None:
        current = _no_symlink(tree, f"plugins/{plugin}/skills/{skill}/SKILL.md")
        reason = frontmatter_refusal(
            current.read_text(encoding="utf-8") if current.is_file() else None, skill_md)
    return {"mode": "draft", "mode_reason": reason} if reason \
        else {"mode": mode}


def _bump_versions(tree: Path, plugin: str) -> tuple[str, str]:
    """Raise the plugin's patch version in both manifests (adam-agentskills
    ADR 0009: `claude plugin update` fires on the version string alone, and
    its check_plugin_versions.py fails a content change without one).
    The text is edited in place so the file keeps its formatting."""
    found = {}
    for name in MANIFESTS:
        rel = f"plugins/{plugin}/{name}"
        text, doc = _manifest(tree, rel)
        version = doc.get("version")
        match = VERSION_RE.fullmatch(version) if isinstance(version, str) else None
        if not match:
            raise Rejected(f"{rel}: version is not MAJOR.MINOR.PATCH")
        found[rel] = (text, version, match)
    if len({version for _, version, _ in found.values()}) != 1:
        raise Rejected(f"{plugin}'s two manifests disagree on its version")
    old = next(iter(found.values()))[1]
    major, minor, patch = map(int, next(iter(found.values()))[2].groups())
    new = f"{major}.{minor}.{patch + 1}"
    for rel, (text, _, _) in found.items():
        needle = f'"version": "{old}"'
        if text.count(needle) != 1:
            raise Rejected(f"{rel}: its version is not written once as {needle}")
        (tree / rel).write_text(text.replace(needle, f'"version": "{new}"'),
                                encoding="utf-8")
    return old, new


def _score(metrics) -> str:
    """`passed/total` of one fixture's metrics, or `n/a`."""
    if not isinstance(metrics, dict):
        return "n/a"
    passed, total = metrics.get("passed"), metrics.get("total")
    if type(passed) is not int or type(total) is not int \
            or not 0 <= passed <= total or total < 1:
        return "n/a"
    return f"{passed}/{total}"


def eval_numbers(record: dict) -> str:
    """One line of the record's objective scores, baseline -> candidate, per
    fixture of the split. Every value is a validated fixture name or an
    integer, so nothing the model wrote reaches the registry's text."""
    split = record["split"]
    roles = [("train", n) for n in split["train"]]
    roles.append(("validation", split["validation"]))
    if "holdout" in split:
        roles.append(("holdout", split["holdout"]))
    parts = [f"{role} {name} {_score(record['baseline'].get(name))} -> "
             f"{_score(record['candidate'].get(name))}"
             for role, name in roles]
    return "; ".join(parts)


def trigger_numbers(record: dict) -> str:
    """The Eval line's numbers for a trigger-only record. Every value is a
    validated integer (check_trigger_only), so nothing the model wrote
    reaches the registry's text. The `a/b` pass counts and the run id are
    what adam-agentskills' scripts/check_skill_gates.py accepts as RAN."""
    o, b = record["trigger_only"]["original"], record["trigger_only"]["best"]
    return (f"held-out trigger queries passed, original -> candidate: "
            f"{o['test_passed']}/{o['test_total']} -> "
            f"{b['test_passed']}/{b['test_total']}; should-not-trigger passed: "
            f"{o['should_not_passed']}/{o['should_not_total']} -> "
            f"{b['should_not_passed']}/{b['should_not_total']}")


def trim_numbers(record: dict) -> str:
    """The Eval line's numbers for a trim record: per fixture, objective
    passes baseline -> candidate, then the sum. Every value is a validated
    fixture name or integer (check_trim), so nothing the model wrote reaches
    the registry's text; the `a/b -> c/d` counts and the run id are what
    adam-agentskills' scripts/check_skill_gates.py accepts as RAN."""
    block = record["trim"]
    names = sorted(block["baseline"])
    parts = [f"{n} {_score(block['baseline'][n])} -> {_score(block['candidate'][n])}"
             for n in names]
    before = sum(block["baseline"][n]["passed"] for n in names)
    after = sum(block["candidate"][n]["passed"] for n in names)
    total = sum(block["baseline"][n]["total"] for n in names)
    return "; ".join(parts) + f"; all fixtures {before}/{total} -> {after}/{total}"


def remove_length_waiver(tree: Path, skill_md: str) -> bool:
    """Remove the registry's `length-limit` waiver for `skill_md` from
    WAIVERS_FILE, as text, so every comment and every other entry stays
    byte for byte. True when one was removed; False, with the file left
    alone, when the file or the entry is absent (the cap may have been met
    another way).

    The entry is the list item under `waivers:` whose `klass` is
    LENGTH_WAIVER_CLASS, `registry` REGISTRY_NAME and `path` `skill_md`. An
    item runs from its `  - ` line to the last non-blank, non-comment line
    before the next item at the same indent or the end of the list, so a
    comment above the next item stays with it. The result is loaded again
    and must equal the original with exactly that one entry gone (an empty
    list is written `waivers: []`); anything else, two matching entries
    included, is Rejected."""
    path = _no_symlink(tree, WAIVERS_FILE)
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
        doc = yaml.safe_load(text)
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        raise Rejected(f"{WAIVERS_FILE}: unreadable") from None
    waivers = doc.get("waivers") if isinstance(doc, dict) else None
    if not isinstance(waivers, list):
        raise Rejected(f"{WAIVERS_FILE}: has no waivers list")
    target = {"klass": LENGTH_WAIVER_CLASS, "registry": REGISTRY_NAME, "path": skill_md}
    matches = [i for i, w in enumerate(waivers) if isinstance(w, dict)
               and all(w.get(k) == v for k, v in target.items())]
    if not matches:
        return False
    if len(matches) > 1:
        raise Rejected(f"{WAIVERS_FILE}: more than one length-limit waiver names "
                       "the skill")
    lines = text.splitlines(keepends=True)
    key = next((i for i, line in enumerate(lines) if re.match(r"waivers:\s*(#.*)?$", line)),
               None)
    if key is None:
        raise Rejected(f"{WAIVERS_FILE}: the waivers list is not in block style")
    items, end = [], len(lines)
    for i in range(key + 1, len(lines)):
        line = lines[i]
        if line.startswith("  - "):
            items.append(i)
        elif line.strip() and not line.lstrip().startswith("#") and not line.startswith("   "):
            end = i
            break

    def last_content(start: int, stop: int) -> int:
        last = start
        for j in range(start, stop):
            if lines[j].strip() and not lines[j].lstrip().startswith("#"):
                last = j
        return last + 1

    spans = [(start, last_content(start, items[n + 1] if n + 1 < len(items) else end))
             for n, start in enumerate(items)]
    found = None
    for start, stop in spans:
        try:
            item = yaml.safe_load("".join(lines[start:stop]))
        except yaml.YAMLError:
            continue
        if isinstance(item, list) and len(item) == 1 and item[0] == waivers[matches[0]]:
            if found is not None:
                raise Rejected(f"{WAIVERS_FILE}: the waiver's text is ambiguous")
            found = (start, stop)
    if found is None:
        raise Rejected(f"{WAIVERS_FILE}: the waiver's lines could not be found")
    new_lines = lines[:found[0]] + lines[found[1]:]
    if len(waivers) == 1:
        new_lines[key] = "waivers: []\n"
    new = "".join(new_lines)
    try:
        after = yaml.safe_load(new)
    except yaml.YAMLError:
        raise Rejected(f"{WAIVERS_FILE}: removing the waiver broke the file") from None
    expected = {**doc, "waivers": waivers[:matches[0]] + waivers[matches[0] + 1:]}
    if after != expected:
        raise Rejected(f"{WAIVERS_FILE}: removing the waiver changed more than "
                       "that one entry")
    path.write_text(new, encoding="utf-8")
    return True


def impact_entry(record: dict, plugin: str, run_id: str, versions: tuple,
                 purpose_added: bool, mode: str, waiver_removed: bool = False) -> str:
    stamp = record["timestamp"]
    date = f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}"
    skill = record["skill"]
    added = " and a `PURPOSE.md` stub added" if purpose_added else ""
    outcome = ("auto-merges once required checks pass, with no human review "
               "(ADR 0021, Adam's 2026-10-26 decision)." if mode == "auto"
               else "draft pull request; a person merges or closes it.")
    if record.get("mode") == TRIM_MODE:
        t = record["trim"]
        waiver = (f"; its `length-limit` waiver removed from `{WAIVERS_FILE}`"
                  if waiver_removed else "")
        return (f"## {date} — {plugin}/{skill} — edit\n\n"
                f"- Motivation: skills-evals description trim run `{run_id}`: the "
                f"description was over the {t['max_chars']}-character listing cap, "
                "waived until the improve lane trimmed it "
                "([skills-evals#687](https://github.com/Adam-S-Daniel/skills-evals/issues/687)).\n"
                f"- Change: SKILL.md description shortened from {t['original_chars']} "
                f"to {t['candidate_chars']} characters by the trim loop, body "
                f"unchanged{added}{waiver}; bundle `{plugin}` {versions[0]} -> "
                f"{versions[1]}, by skills-evals' `routine-improve-gate.yml`.\n"
                f"- Eval: run `{run_id}`, objective checks passed on every fixture, "
                f"baseline -> candidate, {record['trials']} trial(s) per fixture in "
                f"the eval routine (a local exhibit, not badge input): "
                f"{trim_numbers(record)}.\n"
                f"- Outcome: {outcome}\n")
    if record.get("mode") == TRIGGER_MODE:
        return (f"## {date} — {plugin}/{skill} — edit\n\n"
                f"- Motivation: skills-evals trigger-only improvement run "
                f"`{run_id}`: the skill rarely triggers, and skill-creator's "
                "description loop found a description that passed more "
                "held-out trigger queries "
                "([skills-evals#662](https://github.com/Adam-S-Daniel/skills-evals/issues/662)).\n"
                f"- Change: SKILL.md description rewritten by the trigger-only "
                f"improvement loop, body unchanged{added}; bundle `{plugin}` "
                f"{versions[0]} -> {versions[1]}, by skills-evals' "
                "`routine-improve-gate.yml`.\n"
                f"- Eval: run `{run_id}`, skill-creator's description loop on "
                f"`evals/{skill}/{TRIGGER_SET_FILE}` in the eval routine (a "
                f"local exhibit, not badge input): {trigger_numbers(record)}.\n"
                f"- Outcome: {outcome}\n")
    return (f"## {date} — {plugin}/{skill} — edit\n\n"
            f"- Motivation: skills-evals improvement run `{run_id}`: train "
            "checks failed, and `scripts/propose_skill_edit.py`'s acceptance "
            "rule accepted its proposed edit "
            "([skills-evals#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71)).\n"
            f"- Change: SKILL.md edited by the improvement loop{added}; bundle "
            f"`{plugin}` {versions[0]} -> {versions[1]}, by skills-evals' "
            "`routine-improve-gate.yml`.\n"
            f"- Eval: objective checks passed, baseline -> candidate, "
            f"{record['trials']} trial(s) per fixture in the eval routine (a "
            f"local exhibit, not badge input): {eval_numbers(record)}.\n"
            f"- Outcome: {outcome}\n")


def insert_entry(text: str, entry: str) -> str:
    """`entry` newest first, right after the header's `---` rule
    (scripts/retire_skill.py writes its removal entries the same way)."""
    lines = text.split("\n")
    try:
        rule = lines.index("---")
    except ValueError:
        raise Rejected(f"{IMPACT_FILE} has no `---` rule to insert after") from None
    head = "\n".join(lines[:rule + 1]).rstrip("\n")
    rest = "\n".join(lines[rule + 1:]).lstrip("\n")
    return f"{head}\n\n{entry}\n{rest}"


PURPOSE_STUB = """# Purpose — {skill}

Maintenance context only; never loaded at inference.

## What it is for

Not written yet. skills-evals' improvement gate added this file when
improvement run `{run_id}` edited `SKILL.md`, because adam-agentskills asks a
touched skill to carry one (AGENTS.md, "Skill changes get recorded"). Replace
it with the incidents and patterns that motivated the skill.

## Eval status

Fixtures live in skills-evals under `evals/{skill}/`; the edit that added
this file is recorded in `docs/skill-impact.md`.
"""


def _registry_script(tree: Path, rel: str) -> None:
    """Refuse unless `rel` is a regular file of the registry checkout. The
    callers then run it there: it is the default branch's copy (the tree is
    its tip), the same code the registry's CI runs, and the step holds no
    credential. Each call spells its argv in full, so the suite's
    fork scan can tell it is not this repository's test runner."""
    script = _no_symlink(tree, rel)
    if not script.is_file():
        raise Rejected(f"{rel}: not in the registry checkout")


def prepare(staged: Path, tree: Path, skill_md: str, registry_sha: str,
            run_id: str, policy: Path = POLICY) -> dict:
    """Build the registry change on `tree`, a clean checkout of the
    registry's default branch tip, as one or two commits; see the module
    docstring. Returns the merge mode, and `mode_reason` when the policy's
    mode was lowered to `draft`."""
    match = SKILL_MD_RE.fullmatch(skill_md)
    if not match or ".." in skill_md.split("/"):
        raise Rejected("skill_md is not a registry SKILL.md path")
    if not ingest.SHA_RE.fullmatch(registry_sha) \
            or not re.fullmatch(ingest.RUN_ID, run_id):
        raise Rejected("prepare takes only validated values")
    plugin, skill = match.group("plugin"), match.group("skill")
    skill_dir = f"plugins/{plugin}/skills/{skill}"
    repo = str(tree)
    if ingest.git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
        raise Rejected("the registry checkout is not clean")
    base = ingest.resolve_commit(repo, "HEAD")
    # The loop measured the skill at registry_sha; the pull request is based
    # on the tip. The skill's whole directory must be unchanged between the
    # two, or what merges is not what was measured.
    if ingest.git(repo, "rev-parse", f"{registry_sha}:{skill_dir}") \
            != ingest.git(repo, "rev-parse", f"HEAD:{skill_dir}"):
        raise Rejected("the skill changed on the registry's default branch "
                       "since it was measured; measure it again")

    decided = effective_mode(tree, plugin, skill, policy)
    mode, reason = decided["mode"], decided.get("mode_reason")

    apply(staged, tree, skill_md)
    record = json.loads((staged / "summary.json").read_text(encoding="utf-8"))
    trim = isinstance(record, dict) and record.get("mode") == TRIM_MODE
    # A trim retires the skill's length-limit waiver in the same change: the
    # registry's checker fails on a waiver that matches no finding.
    waiver_removed = remove_length_waiver(tree, skill_md) if trim else False
    purpose = _no_symlink(tree, f"{skill_dir}/PURPOSE.md")
    purpose_added = not purpose.exists()
    if purpose_added:
        purpose.write_text(PURPOSE_STUB.format(skill=skill, run_id=run_id),
                           encoding="utf-8")
    versions = _bump_versions(tree, plugin)
    impact = _no_symlink(tree, IMPACT_FILE)
    try:
        text = impact.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise Rejected(f"cannot read {IMPACT_FILE}") from None
    impact.write_text(insert_entry(text, impact_entry(
        record, plugin, run_id, versions, purpose_added, mode, waiver_removed)),
        encoding="utf-8")
    _no_symlink(tree, README)
    _registry_script(tree, "scripts/generate_readme_table.py")
    if subprocess.run([sys.executable, "scripts/generate_readme_table.py"],
                      cwd=tree, capture_output=True, check=False).returncode:
        raise Rejected("the registry's README table did not regenerate")
    ingest.git(repo, "add", "-A", "--", skill_dir, IMPACT_FILE, README,
               *(f"plugins/{plugin}/{name}" for name in MANIFESTS),
               *([WAIVERS_FILE] if waiver_removed else []))
    ingest.git(repo, *COMMIT_IDENTITY, "commit", "-q", "-m",
               f"Edit {plugin}/{skill} from improvement run {run_id}\n\n"
               "skills-evals' improvement loop measured the edit and accepted "
               f"it; the bundle version moves {versions[0]} -> {versions[1]} "
               "so `claude plugin update` delivers it.\n\nAgent: claude-code")
    content = ingest.resolve_commit(repo, "HEAD")

    # The lock pins a commit, so it can only name the content commit after
    # that commit exists (adam-agentskills ci.yml, "Check skills.lock still
    # describes the current bundle").
    if (tree / LOCK).exists():
        _no_symlink(tree, LOCK)
        _registry_script(tree, "scripts/generate_skills_lock.py")
        current = subprocess.run(
            [sys.executable, "scripts/generate_skills_lock.py", "--check-current"],
            cwd=tree, capture_output=True, check=False).returncode
        if current == 1:
            if subprocess.run(
                    [sys.executable, "scripts/generate_skills_lock.py", "--repin",
                     "--repo", "."],
                    cwd=tree, capture_output=True, check=False).returncode:
                raise Rejected("the registry's skills.lock did not re-pin")
            ingest.git(repo, "add", "--", LOCK)
            ingest.git(repo, *COMMIT_IDENTITY, "commit", "-q", "-m",
                       "Re-pin skills.lock to the content commit\n\n"
                       f"The edit changed {skill}, so the lock must pin "
                       "the commit that carries it for ephemeral surfaces "
                       "to receive it.\n\nAgent: claude-code")
        elif current != 0:
            raise Rejected("the registry's skills.lock check could not run")

    if ingest.git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all"):
        raise Rejected("the registry's scripts changed files they were not "
                       "asked to")
    allowed = {IMPACT_FILE, README, LOCK,
               *(f"plugins/{plugin}/{name}" for name in MANIFESTS),
               # Only a trim may touch the waiver file, and only to remove
               # its own waiver (remove_length_waiver).
               *([WAIVERS_FILE] if waiver_removed else [])}
    changed = ingest.git(repo, "diff", "--no-renames", "--name-only", "-z",
                         base, "HEAD").decode().split("\0")[:-1]
    stray = [p for p in changed
             if p not in allowed and not p.startswith(f"{skill_dir}/")]
    if stray:
        raise Rejected("the registry change reaches past the skill's "
                       "directory and its bookkeeping files")
    out = {"mode": mode, "base_sha": base, "content_sha": content,
           "commit": ingest.resolve_commit(repo, "HEAD"),
           "version": versions[1]}
    if reason:
        out["mode_reason"] = reason
    return out


def pr_body(staged: Path, run_id: str, sha: str, branch: str,
            mode: str = "draft") -> str:
    report = (staged / "report.md").read_text(encoding="utf-8")
    if mode == "auto":
        review = [
            "This pull request merges itself (merge commit) once "
            "adam-agentskills' required checks pass, with no human review: "
            "Adam decided on 2026-10-26 that accepted improvements merge "
            f"with no human in the loop ([ADR 0021]({REGISTRY_ADR})). It does "
            "not count toward the three human-reviewed loop pull requests of "
            "[skills-evals#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71). "
            "Where the report below says to review before merging, this "
            "paragraph supersedes it."]
    else:
        review = [
            "A person reviews and merges this, or declines it; nothing merges "
            "itself. Merging it counts toward the three human-reviewed loop "
            "pull requests that must merge before any scheduled loop "
            "([skills-evals#71](https://github.com/Adam-S-Daniel/skills-evals/issues/71))."]
    return "\n".join([
        f"From the skills-evals improvement loop, run `{run_id}`: the "
        "eval routine pushed "
        f"[`{branch}`](https://github.com/Adam-S-Daniel/skills-evals/tree/{sha}) "
        f"at `{sha}`, and `routine-improve-gate.yml` validated it without "
        "running it and applied its `skill.patch` here. The gate also added "
        "what the registry asks of a skill edit: the bundle's patch version "
        "in both manifests, a `docs/skill-impact.md` entry, a `PURPOSE.md` "
        "stub if the skill had none, the README table, and a `skills.lock` "
        "re-pin when the lock covers the skill.",
        "",
        *review,
        "",
        "The numbers below are a local exhibit (skills-evals ADR 0010 "
        "decision 3), not badge input.",
        "",
        "Part of https://github.com/Adam-S-Daniel/skills-evals/issues/71.",
        "",
        "---",
        "",
        report.rstrip("\n"),
        "",
        AGENT_MARKER,
        ""])


#: fire-check's refusals: fixed text, so no input value reaches the log.
FIRE_NOT_A_SKILL = ("input 'skill' is not one skill's fixture set: the loop "
                    "finds no nested fixture under evals/<skill>/, or one "
                    "naming another skill or none, or more than one registry")
FIRE_NOT_ROUTINE_REGISTRY = (f"input 'skill' is not an {REGISTRY_NAME} skill "
                             "(harness/registries.yml), the one registry the "
                             "routine checks out")
FIRE_BAD_HOLDOUT = "input 'holdout' names no nested fixture of that skill"
FIRE_TRIGGER_HOLDOUT = "input 'holdout' must be empty in trigger-only mode"
FIRE_NOT_A_SKILL_NAME = "input 'skill' is not a skill name"
FIRE_NO_TRIGGER_SET = ("input 'skill' has no committed regular "
                       "evals/<skill>/trigger-eval-set.json on the default branch")
FIRE_TRIM_HOLDOUT = "input 'holdout' must be empty in trim mode"
FIRE_TRIM_AND_TRIGGER = "a fire is trim or trigger-only, never both"
FIRE_TRIGGER_SET_UNUSABLE = (
    "the skill's trigger-eval-set.json is not a reviewed set the trigger-only "
    "loop accepts (its shape, its per-class minimum, or a split lacking a class)")


def _fire_too_few() -> str:
    import propose_skill_edit as loop  # noqa: PLC0415 — only fire-check needs it
    return (f"input 'skill' has fewer than {loop.MIN_FIXTURES} nested "
            "fixtures, the loop's minimum")


def fire_check_trigger_only(skill: str, holdout: str) -> None:
    """fire-check for a trigger-only fire (skills-evals#662): no holdout, a
    committed regular `evals/<skill>/trigger-eval-set.json` that the loop's
    own loader and `trigger_only_set` accept, and every nested fixture that
    names a registry naming adam-agentskills. Any number of fixtures, zero
    included: the loop measures none."""
    import propose_skill_edit as loop  # noqa: PLC0415 — only fire-check needs it
    run_eval = loop.run_eval
    if holdout:
        raise Rejected(FIRE_TRIGGER_HOLDOUT)
    if not NAME_RE.fullmatch(skill) or skill in (".", ".."):
        raise Rejected(FIRE_NOT_A_SKILL_NAME)
    rel = f"{skill}/{loop.TRIGGER_SET_FILE}"
    path = loop.EVALS_DIR / skill / loop.TRIGGER_SET_FILE
    if (loop.EVALS_DIR / skill).is_symlink() or path.is_symlink() \
            or not path.is_file():
        raise Rejected(FIRE_NO_TRIGGER_SET)
    # Committed, as a regular file: git's index entry, read from the
    # checkout the loop itself reads (the fire job's default branch).
    try:
        entry = ingest.git(str(loop.EVALS_DIR), "ls-files", "-s", "-z", "--", rel)
    except Rejected:
        raise Rejected(FIRE_NO_TRIGGER_SET) from None
    entries = entry.split(b"\0")[:-1]
    if len(entries) != 1 or not entries[0].startswith((b"100644 ", b"100755 ")):
        raise Rejected(FIRE_NO_TRIGGER_SET)
    try:
        loop.trigger_only_set(path)
    except loop.Refusal:
        raise Rejected(FIRE_TRIGGER_SET_UNUSABLE) from None
    registries = run_eval.resolve_registries(None, None, loop.REPO_ROOT)
    for name in run_eval.nested_fixture_names(loop.EVALS_DIR / skill):
        try:
            fixture = run_eval.load_fixture(loop.EVALS_DIR / skill / name)
        except (OSError, yaml.YAMLError, run_eval.guidance.GuidanceError):
            raise Rejected(FIRE_NOT_A_SKILL) from None
        url = fixture.get("registry") if isinstance(fixture, dict) else None
        if url is None:
            continue
        try:
            found = run_eval.registry_for_url(registries, url) \
                if isinstance(url, str) else None
        except ValueError:
            found = None
        if not found or found["name"] != REGISTRY_NAME or found["url"] != REGISTRY_URL:
            raise Rejected(FIRE_NOT_ROUTINE_REGISTRY)


def fire_check(skill: str, holdout: str, trigger_only: bool = False,
               trim: bool = False) -> None:
    """Refuse a skill or holdout the improvement loop would refuse, as far as
    the committed fixtures and harness/registries.yml can tell. With
    `trigger_only`, the trigger-only loop's checks instead
    (`fire_check_trigger_only`). With `trim` (skills-evals#687), the holdout
    must be empty and the fixtures pass the same checks as an ordinary fire:
    the trim loop measures every one of them."""
    if trigger_only and trim:
        raise Rejected(FIRE_TRIM_AND_TRIGGER)
    if trigger_only:
        fire_check_trigger_only(skill, holdout)
        return
    if trim and holdout:
        raise Rejected(FIRE_TRIM_HOLDOUT)
    import propose_skill_edit as loop  # noqa: PLC0415 — only fire-check needs it
    run_eval = loop.run_eval
    try:
        names = loop.skill_fixtures(skill)
        fixtures = loop.load_fixtures(skill, names)
    except (ValueError, loop.Refusal):
        raise Rejected(FIRE_NOT_A_SKILL) from None
    url = next(iter(fixtures.values())).get("registry")
    if not isinstance(url, str):
        raise Rejected(FIRE_NOT_ROUTINE_REGISTRY)
    try:
        entry = run_eval.registry_for_url(
            run_eval.resolve_registries(None, None, loop.REPO_ROOT), url)
    except ValueError:
        raise Rejected(FIRE_NOT_ROUTINE_REGISTRY) from None
    if entry["name"] != REGISTRY_NAME or entry["url"] != REGISTRY_URL:
        raise Rejected(FIRE_NOT_ROUTINE_REGISTRY)
    if len(names) < loop.MIN_FIXTURES:
        raise Rejected(_fire_too_few())
    if holdout and holdout not in names:
        raise Rejected(FIRE_BAD_HOLDOUT)


def resolve(event_name: str, event_path: str) -> dict:
    return ingest.resolve(event_name, event_path, BRANCH_RE, BRANCH_SHAPE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("resolve")
    p.add_argument("--event-name", required=True)
    p.add_argument("--event-path", required=True)
    p = sub.add_parser("validate")
    p.add_argument("--repo", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--expect-sha", default="")
    p.add_argument("--out", required=True, type=Path)
    p = sub.add_parser("apply")
    p.add_argument("--staged", required=True, type=Path)
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--skill-md", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--staged", required=True, type=Path)
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--skill-md", required=True)
    p.add_argument("--registry-sha", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--policy", type=Path, default=POLICY)
    p = sub.add_parser("merge-mode")
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--plugin", required=True)
    p.add_argument("--skill", required=True)
    p.add_argument("--policy", type=Path, default=POLICY)
    p.add_argument("--staged", type=Path, default=None,
                   help="a draft-skill staging directory: the SKILL.md its skill.patch "
                        "adds is checked for runtime frontmatter keys")
    p = sub.add_parser("pr-body")
    p.add_argument("--staged", required=True, type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--mode", choices=MERGE_MODES, default="draft")
    p = sub.add_parser("fire-check")
    p.add_argument("skill")
    p.add_argument("--holdout", default="")
    flags = p.add_mutually_exclusive_group()
    flags.add_argument("--trigger-only", action="store_true")
    flags.add_argument("--trim", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "fire-check":
            fire_check(args.skill, args.holdout, args.trigger_only, args.trim)
            return 0
        if args.command == "resolve":
            result = resolve(args.event_name, args.event_path)
        elif args.command == "validate":
            result = validate(args.repo, args.base, args.source, args.branch,
                              args.expect_sha or None, args.out)
        elif args.command == "apply":
            result = apply(args.staged, args.tree, args.skill_md)
        elif args.command == "merge-mode":
            result = effective_mode(args.tree, args.plugin, args.skill, args.policy,
                                    staged_skill_md(args.staged, args.plugin, args.skill)
                                    if args.staged is not None else None)
        elif args.command == "prepare":
            result = prepare(args.staged, args.tree, args.skill_md,
                             args.registry_sha, args.run_id, args.policy)
        else:
            if not BRANCH_RE.fullmatch(args.branch) \
                    or not ingest.SHA_RE.fullmatch(args.sha) \
                    or BRANCH_RE.fullmatch(args.branch).group("run_id") != args.run_id:
                raise Rejected("pr-body takes only validated values")
            sys.stdout.write(pr_body(args.staged, args.run_id, args.sha,
                                     args.branch, args.mode))
            return 0
    except Rejected as exc:
        message = "".join(c if c.isprintable() else repr(c)[1:-1]
                          for c in str(exc))
        print(f"rejected: {message}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
