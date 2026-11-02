#!/usr/bin/env python3
"""Plan the week's routine fires: which cells to measure and which skills to
improve, by priority band, inside the weekly allowance (G5, G6).

    plan_week.py plan --results-tree DIR --as-of TIME [--registry NAME=PATH ...]
                      [--guidance DIR] [--evidence FILE] [--lessons DIR]
                      [--max-fires 30] [--out FILE]
    plan_week.py validate-fire        (the matrix leg's env; exit 0 or 1)
    plan_week.py wait-slot [--max-wait SECONDS]
    plan_week.py watchdog --mode wait|check [--max-wait SECONDS]

The rules are the thresholds design's (eval-loop thresholds, version 2,
2026-10-25), A (eligibility), C (stopping) and D (bands); B (acceptance)
stays in scripts/propose_skill_edit.py.

WHAT IS MEASURED. Eval fires are cells, (fixture, roster arm model), of the
reviewed fixtures in evals/scheduled.yml only (ADR 0008): every fire is one
routine-eval-fire.yml dispatch in eval mode with that `model`, both arms, one
trial. A cell's evidence is scripts/compute_gates.py's verdict document,
computed here over the results tree, so the cells are pooled exactly as the
retirement verdict pools them.

GUIDANCE FIXTURES (#124). A scheduled `evals/guidance/<section>/<name>`
fixture (`subject: guidance`) is a cell like any other, fired in eval mode
on its path, but it names a section, not a skill: its evidence is the
section's in-situ cells in the verdict document's `guidance` half
(results/guidance/<section>/..., classified by arm `mode`), and its cell
carries `section` and an empty `skill`. Skill-only logic skips it: the
removal-PR safety band, skill improve eligibility and skill usage weight.
The section's expected extent needs `--guidance`, an _agent-guidance
checkout; without one every guidance cell that has runs stays insufficient
and there are no guidance improve candidates. A guidance section is an
improve CANDIDATE (see IMPROVE ELIGIBILITY), ranked with the skills, and an
eligible one is a `guidance-improve` fire (routine-eval-fire.yml's
guidance-improve mode, ADR 0005's routine guidance improve mode addendum).

THE BANDS (rule D), in order:

  1. safety: every cell of a skill with an open removal pull request in
     adam-agentskills (`retire-skill/<skill>`), no cap, counted first. The
     doc's second safety item, a touch check of an open registry pull
     request's head, is not planned: routine arms run only the registries'
     default branches (ADR 0010 decision 1).
  2. missing evidence, at least 30%: cells with no run on their model,
     cheaper model first, then heaviest model usage (usage/latest.json on the results branch;
     equal weights without it).
  3. near a decision, at least 20%: insufficient cells, fewest runs first,
     then the cheaper model (every run can decide a cell: harness/gates.py
     checks a confidence sequence after each one).
  Bands 2 and 3 skip every cell of a skill or guidance section whose
  verdict is already `keep` (one confident benefit decides it; band 5
  re-checks it), and order the cheaper model first within a tie (Adam,
  2026-10-31: Sonnet first, Opus only while that has not settled it).
  EMPTY FIRES (#559). A cell bound for band 2, 3 or 5 with
  BROKEN_AFTER_FIRES (2) empty fires becomes a `fixture-broken` work item
  and enters no band. An empty fire is a successful non-bare eval fire for
  the cell that started after the cell's newest run of any role or digest
  on its model (gates' `newest_on_model`; any fire when it has none), at
  least FIRE_RESULT_WINDOW (2 hours) ago, within RETRY_AFTER (14 days, so a
  broken cell is retried once its fires age out) and not before
  EMPTY_FIRES_SINCE (fires under the delivery before main's copy say
  nothing). OUTAGES (2026-11-01: six fixtures fired, none produced
  anything). Each fire is classified once: young (under FIRE_RESULT_WINDOW
  old), delivered (a run of the cell is stamped within FIRE_RESULT_WINDOW
  of its start, gates' `run_stamps_on_model`) or empty, so a later retry
  never changes an old fire's state. Every classified fire of every cell is
  grouped into sweeps (`fire_sweeps`: starts at most OUTAGE_GAP, 60
  minutes, apart, at most OUTAGE_SPAN, 2 hours, from the sweep's first). A
  sweep with no delivered and no young fire whose empty fires cover at
  least OUTAGE_CELLS (3) distinct cells is an outage: a cell's earliest
  empty fire in one, at most OUTAGE_EXCUSES (1) within RETRY_AFTER, is
  excused (`outage_fires`), and any further one counts, so fixtures broken
  together still go fixture-broken, one fire later. A sweep with a young
  fire is undecided and counts nothing yet. A sweep narrower than three
  cells cannot be told from broken fixtures, so it counts. Each outage
  sweep of the last 24 hours is a `routine-outage` work item (no fixture
  names). A refused run counts: the fire workflow succeeds once the fire
  API accepts, so fixture-broken means "no run after two fires", whatever
  the cause. A cell whose verdict document lacks `newest_on_model` or
  `run_stamps_on_model` counts none and joins no sweep (fail safe). Safety
  cells are exempt. Every band, safety included, skips a cell with a
  PENDING fire: one younger than FIRE_RESULT_WINDOW, successful or still
  running, with no run on the cell since it started.
  4. improvements, at least 20%: improve fires for eligible skills and
     guidance-improve fires for eligible guidance sections, highest
     potential value first: value = use x headroom / cost, ties by name.
       use: a skill's usage weight (harness/skill_usage.py, `skill_weights`:
         invocations over 4 weeks); a guidance section's is the census's
         transcript sessions scanned scaled to 28 days by its window
         (`skill_usage.session_rate`), since every session loads the
         guidance. Unknown (no, stale or unreadable census) is neutral, the
         median known skill weight, never zero; a known 0 stays 0.
       headroom: 1 - the pooled with-arm pass rate over the train fixtures
         (a guidance section's: its in-situ `full` arm). Unknown headroom
         gives no value, ranked last, never a guessed 0.
       cost: allowance points, IMPROVE_TRIALS x the sum over the subject's
         fixtures of that fixture's mean `fire_cost` across its cells with a
         known cost. With none known, the median of the known estimates
         across candidates, else the improve charge (neutral, like use).
     Each ranking row records whether use and cost were known.
     IMPROVE CAP (#572, 2026-11-02): before allocation the band is walked
     in allocate's own order, and an item goes only when
     `allowance_guard.improve_cap` allows it with the earlier kept items
     counted, exactly the test the guard applies to each fire (Adam's 0.20
     share of weekly_cap for the account week, at least one fire of each
     kind). Cut items count as unplanned. The share above is of one sweep's
     room; this one is of the whole week's cap, and binds every dispatcher.
  5. re-checks: decided cells whose newest run is over 8 weeks old (4
     weeks for a high-stakes subject).
  STAKES (evals/stakes.yml, scripts/stakes.py; Adam, 2026-11-01): within
  bands 2, 3 and 5 a high-stakes subject's cells go first, before the
  band's own order; a `none` subject (a named check enforces it) plans no
  eval fire at all. Every other subject is `normal`.
  6. bare baselines (ADR 0012, bare baseline addendum; Adam, 2026-10-27:
     "one time per model per version of model"): one fire with `arms:
     bare`, `BARE_TRIALS` trials, per (scheduled fixture that runs in place,
     roster model) that has never had one, heaviest model first, with no
     minimum share, so only room the other bands leave. Done means a bare
     run ingested for that cell (the verdict document's `bare_runs`) or a
     bare fire for it that succeeded or is still running (its run title);
     a refused or failed fire is not done. A new roster model id gets its
     own; nothing is repeated on a clock.

Each band first gets its minimum share of the room left after safety;
what is left then goes to the bands in order. Within a band ties break on
cost, cheapest first, and the plan stops at `--max-fires`. A fire is
reserved at its historical cost: its cell's mean agent `cost_usd` per run
(summed over both arms) converted to allowance points by the ratio the
measured routine runs show (points per dollar), between `per_run_overrun`
and one full reservation; one full reservation when either is unknown. A
bare fire runs ONE arm, so it is reserved at its cell's mean agent cost per
arm trial times `BARE_TRIALS`, clamped the same way. An
improve or guidance-improve fire is reserved at
`allowance_guard.improve_charge`. The room is
`allowance_guard.room`. The per-fire guard still checks every fire at its
full reservation before it spends anything; this plan only orders them.

IMPROVE ELIGIBILITY (rule A), per skill with fixtures under evals/<skill>/:

  1. at least `MIN_IMPROVE_FIXTURES` (4) fixtures, all naming
     adam-agentskills (the one registry the routine checks out); the first
     by name is the fixed holdout, passed as `holdout` so the proposer never
     sees it. Fewer fixtures with train headroom is a `needs-fixtures` work
     item instead, ranked by headroom.
  2. train headroom: 1 - the pooled with-arm pass rate over the other
     fixtures is at least `MIN_GAIN` (propose_skill_edit's default gain). A
     skill below it (one that already passes at least 90% of its checks) can
     not be improved by an edit, so it becomes a `needs-harder-fixtures` work
     item instead: the next step is a fixture it fails. Retiring skills and
     skills outside adam-agentskills get none.
  3. a target: some train check fails in at least 25% of at least 6 scored
     with-arm trials, at least twice, and has passed at least once in some
     arm. Infrastructure trials are not evidence (gates.trial_record).
  4. not owned by retirement: its verdict is not `retire` or
     `retire-pending`.
  5. not paused (rule C, `pause`): no open improve pull request
     (`eval-improve/<skill>` in adam-agentskills), no attempt in flight, no
     open issue or pull request labeled `on-hold` whose title names the
     skill, no cooldown. Outcomes come from scripts/improve_outcomes.py.

  The same ranking covers every guidance section with fixtures (not
  `_delivery`, the canary), found by scripts/propose_guidance_edit.py's own
  listing (fixtures declaring the `full` ablation arm). A section is
  eligible with at least `MIN_IMPROVE_FIXTURES` such fixtures (the last in
  name order is the holdout, as the proposer picks it), train headroom of at
  least `MIN_GAIN` over its pooled in-situ `full` arm runs, and a guidance
  verdict (the verdict document's `guidance` half) that is not `retire` or
  `retire-pending`, an `eval-coverage.yml` row that is not `skipped` (the
  proposer refuses one), and not paused: `pause` keyed by section over the
  guidance-improve outcomes (scripts/improve_outcomes.py, mode
  `guidance-improve`) and the `eval-guidance-improve/<section>` pull
  requests in _agent-guidance, plus the guidance lane (`guidance_lane`): no
  guidance-loop pull request (`eval-guidance-improve/*`,
  `retire-guidance/*`) open there and no guidance-improve attempt in flight,
  since every guidance edit writes AGENTS.md and docs/guidance-impact.md and
  a second would conflict. Its content change, for the three-rejection stop,
  is the _agent-guidance history of its row's file. It has no target rule
  (the proposer proposes before it measures). An eligible section is an
  improve-band fire, `mode: guidance-improve`, its `section`, the proposer's
  holdout as `holdout` (the fixture key, guidance/<section>/<name>), reserved
  at the improve charge; at most ONE per plan, the highest value (the lane
  rule again). The work item `guidance-improve` (change type
  `guidance-edit`, routed to a local run of the proposer) remains only for
  an eligible section whose id the fire workflow's `section` pattern
  (^[a-z0-9][a-z0-9-]{0,63}$) refuses. One with fewer fixtures and headroom
  gets `needs-fixtures`, one without headroom `needs-harder-fixtures`, each
  carrying its `section`.

STOPPING (rule C): a rejection (every no-branch outcome, conservatively, and
an accepted candidate whose pull request closed unmerged) starts a 14-day
cooldown; three in a row stop the skill until its content (the registry
checkout's git history for its directory), a fixture (this repository's
history under evals/<skill>/) or the roster (evals/roster.yml) changes after
the third, or 90 days pass. A failed fire job is infrastructure: it is
retried at most twice, then the skill waits 14 days. After a merged
improvement nothing is attempted until a with-arm run of the new content
lands (the gates pool only runs of the content on main).

WORK ITEMS are not fires: `needs-fixtures`, `needs-harder-fixtures` and
`fixture-broken` (change type `fixture`), `routine-outage` (change type
None: the routine failed, not a subject; see EMPTY FIRES),
`guidance-improve` (change type `guidance-edit`; only for a section id the
fire workflow refuses, see above), and `agent-check` items
read from `--lessons` (lesson proposals
of kind `agent-check`, adam-agentskills-private lessons/proposals/**.json),
which go to the fleet worker as agent-ready issues (Adam, 2026-10-26: git
hooks are the first choice whenever possible, so they lead the work list).
Every item carries `change_type`: `skill-edit` for an improve fire,
`guidance-edit` for a guidance-improve fire, `fixture`, `agent-check`,
`trigger`, or None for `routine-outage`.

THE TRIGGER LANE (usage tracking, 2026-10-26: about 55 skill calls in 8
weeks over about 72,000 model turns, so most skills almost never trigger).
Every adam-agentskills skill whose usage weight is fresh (known) and at most
`TRIGGER_MAX_WEIGHT` gets a work item: `trigger-optimize` (change type
`trigger`) when it has a reviewed evals/<skill>/trigger-eval-set.json, or
`needs-trigger-set` (change type `fixture`) to write one. Neither is a
fire: improve mode's payload cannot ask for description optimization with
that set, so a trigger item is routed "needs routine prompt change"
(docs/how-it-works.md, "The trigger lane"). Trigger items sit just before
the improve work items. Skills whose SKILL.md is mostly checklist or rules
sections (`hook_candidate`) are listed as `hook_candidates` and in the
summary, since a git hook may serve them better.

OUTPUT. `--out` gets the whole plan as JSON, including `improve_ranking`
(every candidate, skill or guidance section, by value, highest first and
unknown last, with its use, headroom, cost, whether use and cost were known,
and eligibility) and `guidance` (a per-section status like `skills`); each
fire entry carries its `value` (null for an eval fire; the matrix legs do
not). `--ranking-out` gets the ranking alone (public-safe: skill names and
section ids), which the weekly workflow uploads as the `improve-ranking`
artifact. $GITHUB_OUTPUT gets `matrix=`
(the fires, improve and guidance-improve fires last so a long improve run
never holds up the evals behind it; every leg carries `section`, empty but
for a guidance-improve leg) and `count=`. The log and job summary carry numbers and
public skill names only: agent-check items are counted, never quoted.

FIRE CHECK. `guidance-headroom SECTION` is routine-eval-fire.yml's check
before a guidance-improve fire: the same rule A headroom over the same
pooled in-situ `full` runs (`guidance_contexts`), so a fire dispatched by
hand cannot start what the plan would never pick. Exit 1 when the train
headroom is known and under `MIN_GAIN` (the section already passes at least
90% of its checks; it needs harder fixtures), 0 otherwise. Unknown headroom
passes: the guidance proposer measures before it decides, and the rule is
about sections already at the ceiling. Unlike the skill proposer it has no
early stop after a baseline (it interleaves baseline and candidate), so
without this check such a fire spends its whole run before rejecting
(2026-10-28: "anything-you-name-gets-its-link" at 72/72, run
20261028T213124Z-65c174). The log names the section and the numbers only.

EVIDENCE. `--evidence FILE` reads the GitHub evidence from a recorded JSON
file ({fire_runs, improve_branches, registry_prs, on_hold}, and optionally
guidance_branches, guidance_prs and guidance_on_hold, empty when absent);
without it the evidence is fetched with GH_TOKEN (scripts/improve_outcomes.py's
reader), _agent-guidance's pull requests and on-hold issues included.
Every read failure stops the plan (fail closed); the message is fixed text
and a status code.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import urllib.parse

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO_ROOT / "harness"))

import allowance_guard as guard  # noqa: E402
import improve_outcomes as outcomes_mod  # noqa: E402
import plan_scheduled_evals as schedule  # noqa: E402
import stakes as stakes_mod  # noqa: E402

REGISTRY_URL = "https://github.com/Adam-S-Daniel/adam-agentskills"
#: A skill here is private (Adam, 2026-10-31): its results come from the
#: private repository's own results branch and stay out of every public
#: output, so it gets cells (fires) but no improve candidate, ranking row,
#: status or work item, each of which would publish its pass rate.
PRIVATE_REGISTRY_URL = "https://github.com/Adam-S-Daniel/adam-agentskills-private"
REGISTRY_REPO = "Adam-S-Daniel/adam-agentskills"
SELF_REPO = "Adam-S-Daniel/skills-evals"
GUIDANCE_REPO = "Adam-S-Daniel/_agent-guidance"
#: Guidance-loop heads in _agent-guidance: improvements (this plan's fires,
#: scripts/guidance_improve_gate.py) and removals (scripts/retire_skill.py).
GUIDANCE_IMPROVE_PREFIX = "eval-guidance-improve/"
GUIDANCE_REMOVAL_PREFIX = "retire-guidance/"
#: The fire modes that run the improvement loop (held IMPROVE_FLIGHT).
IMPROVE_MODES = ("improve", "guidance-improve")
MIN_IMPROVE_FIXTURES = 4
MIN_GAIN = 0.10
TARGET_FAIL_RATE = 0.25
TARGET_MIN_TRIALS = 6
TARGET_MIN_FAILS = 2
COOLDOWN = timedelta(days=14)
STOP_AFTER_REJECTIONS = 3
STOP_FOR = timedelta(days=90)
INFRA_RETRIES = 2
RECHECK_AFTER = timedelta(weeks=8)
#: A decided high-stakes subject is re-checked this soon (evals/stakes.yml).
RECHECK_AFTER_HIGH = timedelta(weeks=4)
BROKEN_AFTER_FIRES = 2
#: A successful eval fire this old with no run on its cell produced nothing.
FIRE_RESULT_WINDOW = timedelta(hours=2)
#: Only empty fires this recent count, so a fixture-broken cell is retried
#: once its fires age out instead of staying broken for good (#559).
RETRY_AFTER = timedelta(days=14)
#: Empty fires before this are not counted. Runs test main's copy of a skill
#: from #559 on, which adds refusals (registry_checkout_dirty, ...) and
#: clears others, so fires made under the old delivery say nothing about
#: whether the cell can produce a run now; the first sweep after the change
#: judges only fires made under it.
EMPTY_FIRES_SINCE = datetime(2026, 11, 3, tzinfo=timezone.utc)
#: Fires whose starts chain at most this far apart are one sweep.
#: explorer_data's FIRE_SWEEP_GAP is this constant and its sweeps come from
#: fire_sweeps too, but it groups only fires without results and has no
#: span cap, so its sweeps can differ from the planner's.
OUTAGE_GAP = timedelta(minutes=60)
#: The planner's sweeps end this long after their first start, so a planner
#: firing every hour cannot chain a week of fires into one sweep that one
#: delivered fire would clear of every outage.
OUTAGE_SPAN = timedelta(hours=2)
#: A sweep with no delivered fire whose empty fires span at least this many
#: distinct (fixture, model) cells is a routine outage, not broken fixtures:
#: one bad cell or two cannot explain it, and counting it would bench healthy
#: cells for RETRY_AFTER. A narrower sweep cannot be told from broken
#: fixtures, so it counts.
OUTAGE_CELLS = 3
#: Outage fires excused per cell within RETRY_AFTER, its earliest. The
#: backstop: a fixture empty in sweep after sweep still reaches
#: BROKEN_AFTER_FIRES, one fire later, even when every sweep looks like an
#: outage because several broken fixtures fail together.
OUTAGE_EXCUSES = 1
#: A `routine-outage` work item is listed for an outage sweep this recent.
OUTAGE_REPORT_WINDOW = timedelta(hours=24)
SHARES = (("missing", 0.30), ("near", 0.20), ("improve", 0.20))
BANDS = ("safety", "missing", "near", "improve", "recheck", "bare")
IMPROVE_TRIALS = 3
#: Where an eligible guidance section's improvement runs when the fire
#: workflow's `section` pattern refuses its id.
GUIDANCE_IMPROVE_ROUTE = ("local run: scripts/propose_guidance_edit.py (the fire "
                          "workflow's section pattern refuses this id)")
#: A guidance fixture key, relative to evals/ (the proposer's listing).
GUIDANCE_FIXTURE_RE = re.compile(r"guidance/[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
                                 r"(?:/[A-Za-z0-9][A-Za-z0-9._-]{0,127})?")
#: The window `use` is counted over: skill_usage.weight's four weeks.
USE_WINDOW_DAYS = 28
#: Trials of a bare fire's one arm (routine-eval-weekly.yml sends them).
BARE_TRIALS = 3
#: wait-slot: at most this many fires in flight, each counted in flight this
#: long after it started (an eval run takes 4 to 12 minutes, an improve run
#: a few hours), polled once a minute.
MAX_IN_FLIGHT = 3
EVAL_FLIGHT = timedelta(minutes=20)
IMPROVE_FLIGHT = timedelta(hours=3)
POLL_SECONDS = 60
#: watchdog (routine-eval-watchdog.yml): re-plan this long after the last
#: sweep when nothing else has started one, and this long after a fire's
#: hold ends, so the guard's own clock is past it. A fire that never pushes
#: results wakes no ingest, so without this nothing re-plans when its hold
#: frees the room (2026-11-01: a 15:55 UTC fire stalled the evals 16:11 to
#: 18:33 UTC). `check` mode, the schedule's, uses the newest finished
#: sweep's end as the anchor and never sleeps.
WATCHDOG_IDLE = timedelta(minutes=50)
WATCHDOG_MARGIN = timedelta(minutes=2)
WATCHDOG_MAX_WAIT = 3300
WEEKLY_WORKFLOW = "routine-eval-weekly.yml"
WATCHDOG_WORKFLOW = "routine-eval-watchdog.yml"
LESSON_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
#: The trigger lane: a skill whose fresh usage weight (invocations over
#: skill_usage.weight's four weeks) is at most this rarely triggers at all.
TRIGGER_MAX_WEIGHT = 1
TRIGGER_SET = "trigger-eval-set.json"
#: What the routine would need before a trigger item can be fired (see
#: docs/how-it-works.md, "The trigger lane").
TRIGGER_ROUTE = "needs routine prompt change"
#: A hook candidate: at least this share of its SKILL.md body's non-blank
#: lines sits under a heading naming a checklist, rules or checks.
HOOK_RULE_SHARE = 0.5
HOOK_HEADING_RE = re.compile(r"\b(?:checklist|rules|checks)\b", re.IGNORECASE)
MARKDOWN_HEADING_RE = re.compile(r"(#{1,6})\s+(.*)")
STAMP = "%Y%m%dT%H%M%SZ"


class PlanError(Exception):
    """The plan could not be made. Fixed text, never evidence content."""


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp_time(stamp) -> datetime | None:
    try:
        return datetime.strptime(stamp, STAMP).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Rule C: is a skill paused?

def pause(skill: str, records: list, prs: list, on_hold: list, now: datetime,
          changed_at: datetime | None, remeasured_after, key: str = "skill") -> str | None:
    """Why `skill` may not be attempted now, or None. `records` are
    improve_outcomes records, `prs` {skill, state, created_at, closed_at,
    merged_at} of `eval-improve/<skill>` pull requests, `on_hold` the titles
    of open `on-hold` issues and pull requests, `changed_at` the newest
    change to its content, fixtures or the roster, and `remeasured_after` a
    function of a time: whether a with-arm run of the skill landed after
    it. A guidance section passes `key="section"`: its records and its
    `eval-guidance-improve/<section>` pull requests carry `section`."""
    mine = [r for r in records if r[key] == skill]
    own_prs = sorted((p for p in prs if p[key] == skill),
                     key=lambda p: p["created_at"] or "")
    if any(p["state"] == "open" for p in own_prs):
        return "an improve pull request is open"
    token = re.compile(rf"(?<![A-Za-z0-9._-]){re.escape(skill)}(?![A-Za-z0-9._-])")
    if any(isinstance(t, str) and token.search(t) for t in on_hold):
        return "an open on-hold issue or pull request names it"
    if any(r["outcome"] == "pending" for r in mine):
        return "an attempt is in flight"
    failed = 0
    for record in reversed(mine):
        if record["outcome"] != "fire-failed":
            break
        failed += 1
    if failed > INFRA_RETRIES:
        last = outcomes_mod.parse_time(mine[-1]["at"])
        if now - last < COOLDOWN:
            return f"its fire failed {failed} times in a row; retrying after a cooldown"
    # Measured outcomes, in order: a rejection, or an acceptance and what its
    # pull request became.
    measured = []
    for record in mine:
        at = outcomes_mod.parse_time(record["at"])
        if record["outcome"] == "rejected":
            measured.append(("rejected", at))
        elif record["outcome"] == "accepted":
            pr = next((p for p in own_prs if outcomes_mod.parse_time(p["created_at"])
                       and outcomes_mod.parse_time(p["created_at"]) >= at), None)
            if pr is None:
                measured.append(("awaiting-pr", at))
            elif pr["merged_at"]:
                measured.append(("merged", outcomes_mod.parse_time(pr["merged_at"])))
            else:
                measured.append(("rejected", outcomes_mod.parse_time(pr["closed_at"]) or at))
    if not measured:
        return None
    kind, at = measured[-1]
    if kind == "awaiting-pr":
        return "an accepted candidate has no registry pull request yet"
    if kind == "merged":
        if not remeasured_after(at):
            return "an improvement merged; waiting for the with arm to be re-measured"
        return None
    streak = 0
    for kind, _ in reversed(measured):
        if kind != "rejected":
            break
        streak += 1
    if streak >= STOP_AFTER_REJECTIONS:
        if not (changed_at and changed_at > at) and now - at < STOP_FOR:
            return (f"{streak} rejections in a row; stopped until its content, a "
                    "fixture or the roster changes, or 90 days pass")
        return None
    if now - at < COOLDOWN:
        return "cooling down after a rejection"
    return None


def guidance_lane(section: str, records: list, prs: list, removals: list) -> str | None:
    """Why no guidance-improve fire may go for `section` because of ANOTHER
    section, or None: every guidance edit writes AGENTS.md and
    docs/guidance-impact.md in _agent-guidance, so a second open pull
    request would conflict once the first merged (the gate opens nothing
    while one is open). `records` are guidance-improve outcome records, `prs`
    the `eval-guidance-improve/<section>` pull requests, `removals` the
    sections with an open `retire-guidance/` pull request."""
    if any(p["state"] == "open" and p["section"] != section for p in prs) \
            or any(r != section for r in removals):
        return "another guidance-loop pull request is open in _agent-guidance"
    if any(r["outcome"] == "pending" and r["section"] != section for r in records):
        return "another guidance-improve attempt is in flight"
    if section in removals:
        return "a removal pull request for it is open in _agent-guidance"
    return None


# ---------------------------------------------------------------------------
# Rule A's evidence: train headroom and targets, from pooled with-arm trials.

def train_evidence(cells: dict, train: list) -> dict:
    """{pass_rate, headroom, with_trials, targets} over the train fixtures'
    cells. `cells` is gates.pool_cells' output: {(fixture, model): {"with":
    runs, "without": runs}}, each run with `trials` (gates.trial_record) and
    `timestamp`."""
    passed = total = 0
    by_check: dict = {}
    with_trials = 0
    for (fixture, _model), pool in cells.items():
        if fixture not in train:
            continue
        for role in ("with", "without"):
            for run in pool[role]:
                for trial in run["trials"]:
                    if not trial.get("scored") or trial.get("infrastructure") \
                            or not trial.get("checks"):
                        continue
                    for check, ok in trial["checks"].items():
                        entry = by_check.setdefault((fixture, check),
                                                    {"n": 0, "fails": 0, "passed_any": False})
                        entry["passed_any"] |= bool(ok)
                        if role == "with":
                            entry["n"] += 1
                            entry["fails"] += 0 if ok else 1
                    if role == "with":
                        with_trials += 1
                        passed += sum(1 for ok in trial["checks"].values() if ok)
                        total += len(trial["checks"])
    rate = passed / total if total else None
    targets = sorted(f"{fixture or '-'}:{check}" for (fixture, check), e in by_check.items()
                     if e["n"] >= TARGET_MIN_TRIALS and e["fails"] >= TARGET_MIN_FAILS
                     and e["fails"] / e["n"] >= TARGET_FAIL_RATE and e["passed_any"])
    return {"pass_rate": rate, "headroom": None if rate is None else 1 - rate,
            "with_trials": with_trials, "targets": targets}


def with_run_after(cells: dict, moment: datetime) -> bool:
    """Whether any pooled with-arm run of these cells is stamped after `moment`."""
    return any((_stamp_time(run["timestamp"]) or moment) > moment
               for pool in cells.values() for run in pool["with"])


# ---------------------------------------------------------------------------
# Rule D: the bands.

def fire_cost(cell: dict, ctx: dict) -> float:
    """A cell's fire at its historical cost (module docstring)."""
    reserve, ratio = ctx["reservation"], ctx.get("points_per_usd")
    usd = cell.get("usd_per_fire")
    if not ratio or usd is None:
        return reserve
    return min(reserve, max(ctx["overrun"], usd * ratio))


def bare_cost(cell: dict | None, ctx: dict) -> float:
    """A bare fire's reservation: one arm, BARE_TRIALS trials, at its cell's
    mean agent cost per arm trial (module docstring)."""
    reserve, ratio = ctx["reservation"], ctx.get("points_per_usd")
    usd = (cell or {}).get("usd_per_arm_trial")
    if not ratio or usd is None:
        return reserve
    return min(reserve, max(ctx["overrun"], usd * BARE_TRIALS * ratio))


def bare_items(ctx: dict) -> list:
    """Band 6's fires: one per ctx["bare"] entry, {fixture, model, skill},
    the in-place cells with no bare run yet."""
    weights = ctx["model_weights"]
    cells = {(c["fixture"], c["model"]): c for c in ctx["cells"]}
    items = []
    for entry in ctx.get("bare", []):
        weight = weights.get(entry["model"], 0.0)
        items.append({"mode": "eval", "arms": "bare", "fixture": entry["fixture"],
                      "model": entry["model"], "skill": entry["skill"], "holdout": "",
                      "cost": bare_cost(cells.get((entry["fixture"], entry["model"])), ctx),
                      "change_type": None, "weight": weight, "band": "bare",
                      "order": (-weight,)})
    return items


def model_costs(cells: list) -> dict:
    """Each roster model's median agent cost per arm trial over the cells
    that know one; a model with none known is absent (ordered last)."""
    known: dict = {}
    for cell in cells:
        if cell.get("usd_per_arm_trial") is not None:
            known.setdefault(cell["model"], []).append(cell["usd_per_arm_trial"])
    return {m: statistics.median(v) for m, v in known.items()}


def recheck_after(cell: dict) -> timedelta:
    """How long after its newest run a decided cell is re-checked: sooner
    for a high-stakes subject (evals/stakes.yml)."""
    return RECHECK_AFTER_HIGH if cell.get("stakes") == "high" else RECHECK_AFTER


def eval_items(ctx: dict, now: datetime) -> tuple:
    """(fires by band, work items) for the eval cells. A subject (skill or
    guidance section) already kept plans no missing or near fire: one
    confident benefit keeps it, so more runs cannot change the verdict
    until its re-check. Within a band the cheaper model goes first (Adam,
    2026-10-31: Sonnet first, Opus only while the cheaper runs have not
    settled it), then the heavier-used model.

    A cell bound for the missing, near or recheck band with at least
    BROKEN_AFTER_FIRES `empty_fires` is a `fixture-broken` work item
    instead and enters no band: a refusal that keeps recurring (an upstream
    edit can cause one at any time) would otherwise re-fire it on every
    sweep. A safety cell is exempt, since a removal pull request must keep
    its evidence slot. A `pending` cell, whose last fire may still land a
    run, plans no fire in any band, safety included. Each of ctx["outages"]
    whose first start is within OUTAGE_REPORT_WINDOW is a `routine-outage`
    work item, listed first."""
    weights = ctx["model_weights"]
    costs = model_costs(ctx["cells"])
    removal = {s for s in ctx["removal_prs"]}
    bands = {band: [] for band in BANDS}
    work = []
    for cell in ctx["cells"]:
        if not cell.get("schedulable", True):
            continue  # an isolation, null-pin or private cell enters no band, safety included
        stakes = cell.get("stakes", "normal")
        if stakes == "none":
            continue  # a check enforces it; evals/stakes.yml names the check
        # High stakes go first in every band but safety.
        rank = 0 if stakes == "high" else 1
        item = {"mode": "eval", "arms": "both", "fixture": cell["fixture"], "model": cell["model"],
                "skill": cell["skill"], "holdout": "", "cost": fire_cost(cell, ctx),
                "change_type": None, "weight": weights.get(cell["model"], 0.0)}
        price = costs.get(cell["model"], math.inf)
        least = min(cell["with_runs"], cell["without_runs"])
        newest = _stamp_time(cell["newest"])
        kept = cell.get("verdict") == "keep"
        due = newest is not None and now - newest >= recheck_after(cell)
        if not cell.get("section") and cell["skill"] in removal:
            band, order = "safety", ()
        elif kept and cell["class"] in ("missing", "insufficient"):
            # More runs cannot change a keep, but its re-check still comes
            # due, or a kept subject with an unsettled cell would never be
            # tested again.
            band, order = ("recheck", (rank, newest.timestamp())) if due else (None, None)
        elif cell["class"] == "missing":
            band, order = "missing", (rank, price, -item["weight"])
        elif cell["class"] == "insufficient":
            band, order = "near", (rank, least, price, -item["weight"])
        elif due:
            band, order = "recheck", (rank, newest.timestamp())
        else:
            band, order = None, None
        if band is None:
            continue
        if band != "safety" and cell.get("empty_fires", 0) >= BROKEN_AFTER_FIRES:
            broken = {"kind": "fixture-broken", "change_type": "fixture",
                      "skill": cell["skill"], "fixture": cell["fixture"],
                      "model": cell["model"], "route": "issue"}
            if cell.get("section"):
                broken["section"] = cell["section"]
            work.append(broken)
        elif not cell.get("pending"):
            bands[band].append({**item, "band": band, "order": order})
    # No fixture names: an outage is the routine's, not any fixture's, and
    # the step summary counts work items by kind.
    outages = [{"kind": "routine-outage", "change_type": None, "route": "issue",
                "sweep_start": _iso(sweep["start"]), "fires": sweep["fires"]}
               for sweep in ctx.get("outages", [])
               if now - sweep["start"] <= OUTAGE_REPORT_WINDOW]
    return bands, outages + work


def neutral_weights(raw: dict) -> dict:
    """Each skill's usage weight, an unknown one (None) given the median of
    the known positive weights, or 1.0 when there is none: neutral, never
    zero. A known 0 (a fresh census that never saw the skill) stays 0."""
    known = sorted(w for w in raw.values() if w is not None and w > 0)
    neutral = known[len(known) // 2] if known else 1.0
    return {skill: neutral if w is None else w for skill, w in raw.items()}


def value_of(use, headroom, cost) -> float | None:
    """The potential value of an improvement: expected uses over the usage
    window times train headroom, per allowance point spent. None when any
    factor is unknown (headroom) or the cost is not positive: never a guess
    of 0."""
    if use is None or headroom is None or cost is None or cost <= 0:
        return None
    return use * headroom / cost


def cost_estimate(ctx: dict, subject: str, name: str) -> float | None:
    """What an improve run on a subject costs, in allowance points:
    IMPROVE_TRIALS times the sum over its fixtures of that fixture's mean
    `fire_cost` across its cells with a known cost. A fixture with no known
    cell adds nothing. None when no fixture has a known cost (or the
    points-per-dollar ratio is unknown)."""
    if not ctx.get("points_per_usd"):
        return None
    per_fixture: dict = {}
    for c in ctx.get("cells", []):
        mine = c.get("section") == name if subject == "guidance" \
            else not c.get("section") and c["skill"] == name
        if mine and c.get("usd_per_fire") is not None:
            per_fixture.setdefault(c["fixture"], []).append(fire_cost(c, ctx))
    if not per_fixture:
        return None
    return IMPROVE_TRIALS * sum(sum(v) / len(v) for v in per_fixture.values())


def improve_items(ctx: dict, now: datetime) -> tuple:
    """(improve fires, work items, per-skill status, per-section guidance
    status, improve ranking). Candidates, skills and guidance sections, are
    ranked by value = use x headroom / cost (module docstring, THE BANDS
    item 4); improve fires and guidance work items follow that order, and
    needs-fixtures and needs-harder-fixtures items stay ordered by skill
    usage weight, heaviest first (`neutral_weights` of ctx["skill_weights"]),
    then train headroom."""
    raw = ctx.get("skill_weights") or {}
    weights = neutral_weights({name: raw.get(name) for name in ctx["skills"]})
    # The neutral use of anything unknown: the median `neutral_weights` gives
    # an unknown skill, from the skills alone.
    neutral = neutral_weights({**{n: raw.get(n) for n in ctx["skills"]}, "": None})[""]
    fires, work, status = [], [], {}
    candidates = []
    for name, skill in sorted(ctx["skills"].items()):
        evidence = skill["evidence"]
        headroom = evidence["headroom"]
        reasons = []
        if not skill["registry_ok"]:
            reasons.append("its fixtures do not all name adam-agentskills")
        if headroom is None or headroom < MIN_GAIN:
            reasons.append("no train headroom")
            if (headroom is not None and skill["registry_ok"]
                    and skill["verdict"] not in ("retire", "retire-pending")):
                work.append({"kind": "needs-harder-fixtures", "change_type": "fixture",
                             "skill": name, "fixtures": skill["fixtures"],
                             "headroom": headroom, "route": "issue"})
        if skill["fixtures"] < MIN_IMPROVE_FIXTURES:
            if not reasons:
                work.append({"kind": "needs-fixtures", "change_type": "fixture",
                             "skill": name, "fixtures": skill["fixtures"],
                             "headroom": headroom, "route": "issue"})
            reasons.append(f"{skill['fixtures']} fixture(s), under {MIN_IMPROVE_FIXTURES}")
        if not evidence["targets"]:
            reasons.append("no failing check to target")
        if skill["verdict"] in ("retire", "retire-pending"):
            reasons.append(f"owned by retirement ({skill['verdict']})")
        if not reasons and skill["pause"]:
            reasons.append(skill["pause"])
        status[name] = {"eligible": not reasons, "reasons": reasons, "headroom": headroom,
                        "fixtures": skill["fixtures"], "targets": len(evidence["targets"])}
        candidates.append({"subject": "skill", "name": name, "use": weights.get(name, neutral),
                           "use_known": raw.get(name) is not None, "headroom": headroom,
                           "cost": cost_estimate(ctx, "skill", name),
                           "eligible": not reasons, "reasons": reasons,
                           "fixtures": skill["fixtures"], "holdout": skill["holdout"]})
    guidance_use = ctx.get("guidance_use")
    gstatus, gitems = {}, []
    for section, info in sorted((ctx.get("guidance") or {}).items()):
        headroom = info["evidence"]["headroom"]
        reasons = []
        if headroom is None or headroom < MIN_GAIN:
            reasons.append("no train headroom")
        if info["fixtures"] < MIN_IMPROVE_FIXTURES:
            reasons.append(f"{info['fixtures']} fixture(s), under {MIN_IMPROVE_FIXTURES}")
        if info["verdict"] in ("retire", "retire-pending"):
            reasons.append(f"owned by retirement ({info['verdict']})")
        if info.get("row_ok") is False:
            reasons.append("its eval-coverage.yml row is skipped or missing")
        if not reasons and info.get("pause"):
            reasons.append(info["pause"])
        gstatus[section] = {"eligible": not reasons, "reasons": reasons, "headroom": headroom,
                            "fixtures": info["fixtures"]}
        candidates.append({"subject": "guidance", "name": section,
                           "use": neutral if guidance_use is None else guidance_use,
                           "use_known": guidance_use is not None, "headroom": headroom,
                           "cost": cost_estimate(ctx, "guidance", section),
                           "eligible": not reasons, "reasons": reasons})
        gitems.append((section, info, headroom, reasons))
    known = sorted(c["cost"] for c in candidates if c["cost"] is not None)
    fallback = (known[len(known) // 2] if len(known) % 2
                else (known[len(known) // 2 - 1] + known[len(known) // 2]) / 2) \
        if known else ctx["improve_charge"]
    ranking = []
    for c in candidates:
        cost = fallback if c["cost"] is None else c["cost"]
        ranking.append({"subject": c["subject"], "name": c["name"],
                        "value": value_of(c["use"], c["headroom"], cost), "use": c["use"],
                        "use_known": c["use_known"], "headroom": c["headroom"], "cost": cost,
                        "cost_known": c["cost"] is not None, "eligible": c["eligible"],
                        "reasons": c["reasons"]})
    ranking.sort(key=lambda r: (r["value"] is None, -(r["value"] or 0.0), r["name"]))
    value = {(r["subject"], r["name"]): r["value"] for r in ranking}
    for c in candidates:
        if c["subject"] == "skill" and c["eligible"]:
            v = value[("skill", c["name"])]
            fires.append({"mode": "improve", "arms": "", "fixture": "", "model": "",
                          "skill": c["name"], "holdout": c["holdout"],
                          "cost": ctx["improve_charge"], "change_type": "skill-edit",
                          "band": "improve", "value": v,
                          "order": (v is None, -(v or 0.0), c["name"])})
    work.sort(key=lambda w: (-weights.get(w["skill"], 1.0), -(w["headroom"] or 0.0), w["skill"]))
    # An eligible section is a guidance-improve fire, at most one per plan
    # (`guidance_lane`: a second open guidance edit would conflict), the
    # highest value first; a work item only when the fire workflow's section
    # pattern refuses its id.
    guidance_work, fired = [], None
    for section, info, headroom, reasons in sorted(
            gitems, key=lambda g: (value[("guidance", g[0])] is None,
                                   -(value[("guidance", g[0])] or 0.0), g[0])):
        v = value[("guidance", section)]
        if not reasons and not outcomes_mod.SECTION_RE.fullmatch(section):
            guidance_work.append({
                "kind": "guidance-improve", "change_type": "guidance-edit",
                "section": section, "fixtures": info["fixtures"], "headroom": headroom,
                "value": v, "route": GUIDANCE_IMPROVE_ROUTE})
        elif not reasons and fired is not None:
            gstatus[section]["deferred"] = (f"one guidance-improve fire per plan; "
                                            f"{fired} ranks higher")
        elif not reasons:
            fired = section
            fires.append({"mode": "guidance-improve", "arms": "", "fixture": "", "model": "",
                          "skill": "", "section": section,
                          "holdout": info.get("holdout_fixture", ""),
                          "cost": ctx["improve_charge"], "change_type": "guidance-edit",
                          "band": "improve", "value": v,
                          "order": (v is None, -(v or 0.0), section)})
        elif headroom is not None and info["verdict"] not in ("retire", "retire-pending") \
                and (headroom < MIN_GAIN or info["fixtures"] < MIN_IMPROVE_FIXTURES):
            # A paused section, or one whose manifest row is skipped, needs
            # no fixture work; its reason is in `gstatus`.
            kind = "needs-harder-fixtures" if headroom < MIN_GAIN else "needs-fixtures"
            guidance_work.append({
                "kind": kind, "change_type": "fixture", "skill": "", "section": section,
                "fixtures": info["fixtures"], "headroom": headroom, "value": v,
                "route": "issue"})
    guidance_work.sort(key=lambda w: (w["value"] is None, -(w["value"] or 0.0), w["section"]))
    return fires, work + guidance_work, status, gstatus, ranking


def hook_candidate(text: str) -> bool:
    """Whether a SKILL.md is mostly mechanical rules, so a git hook may
    serve better than a skill (Adam, 2026-10-26: hooks first). A cheap
    heuristic: at least HOOK_RULE_SHARE of the body's non-blank lines
    (frontmatter left out, fenced code counted) sit under a heading whose
    text has the word checklist, rules or checks, down to the next heading
    of the same or a higher level."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        ends = [i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"]
        lines = lines[ends[0] + 1:] if ends else lines
    total = under = 0
    fence, level = False, None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            fence = not fence
        heading = None if fence else MARKDOWN_HEADING_RE.fullmatch(stripped)
        if heading:
            depth = len(heading.group(1))
            if level is not None and depth <= level:
                level = None
            if level is None and HOOK_HEADING_RE.search(heading.group(2)):
                level = depth
            continue
        if stripped:
            total += 1
            under += level is not None
    return bool(total) and under / total >= HOOK_RULE_SHARE


def trigger_items(ctx: dict) -> tuple:
    """(work items, hook candidates) for the trigger lane. A skill of
    ctx["triggers"] (every adam-agentskills skill) whose usage weight is
    known, so fresh, and at most TRIGGER_MAX_WEIGHT gets a `trigger` item
    when evals/<skill>/trigger-eval-set.json exists, routed TRIGGER_ROUTE
    because no fire can ask for description optimization yet, or else a
    `fixture` item to write that set. An unknown weight is neutral: no
    item. A skill owned by retirement gets none. Least used first."""
    weights = ctx.get("skill_weights") or {}
    work = []
    for name, info in sorted(ctx.get("triggers", {}).items()):
        weight = weights.get(name)
        if weight is None or weight > TRIGGER_MAX_WEIGHT \
                or ctx["skills"].get(name, {}).get("verdict") in ("retire", "retire-pending"):
            continue
        path = f"evals/{name}/{TRIGGER_SET}"
        if info["trigger_set"]:
            item = {"kind": "trigger-optimize", "change_type": "trigger",
                    "route": TRIGGER_ROUTE}
        else:
            item = {"kind": "needs-trigger-set", "change_type": "fixture", "route": "issue"}
        work.append({**item, "skill": name, "weight": weight, "trigger_set": path,
                     "hook_candidate": info["hook_candidate"]})
    work.sort(key=lambda w: (w["weight"], w["skill"]))
    hooks = sorted(name for name, info in ctx.get("triggers", {}).items()
                   if info["hook_candidate"])
    return work, hooks


def lesson_items(lessons: list) -> list:
    """Agent-check work items from lesson proposals, most evidence first."""
    items = []
    for lesson in lessons:
        if not isinstance(lesson, dict) or lesson.get("kind") != "agent-check" \
                or lesson.get("schema_version") != 1:
            continue
        ident, count = lesson.get("id"), lesson.get("evidence_count")
        if not isinstance(ident, str) or not LESSON_ID_RE.fullmatch(ident) \
                or isinstance(count, bool) or not isinstance(count, int) or count < 1 \
                or not isinstance(lesson.get("subject"), str):
            continue
        items.append({"kind": "agent-check", "change_type": "agent-check", "id": ident,
                      "subject": lesson["subject"], "evidence_count": count,
                      "route": "fleet worker, agent-ready issue (.githooks/agent-checks)"})
    return sorted(items, key=lambda i: (-i["evidence_count"], i["id"]))


def allocate(bands: dict, room: float, max_fires: int) -> list:
    """The fires that fit `room` points: safety first, then each band up to
    its minimum share of what is left, then the rest in band order."""
    for band in bands.values():
        band.sort(key=lambda i: (*i["order"], i["cost"], i["fixture"], i["model"], i["skill"]))
    chosen = []

    def take(item):
        chosen.append(item)
        bands[item["band"]].remove(item)

    for item in list(bands["safety"]):
        if len(chosen) < max_fires:
            take(item)
    left = room - sum(i["cost"] for i in chosen)
    after_safety = max(0.0, left)
    for band, share in SHARES:
        allowance = share * after_safety
        for item in list(bands[band]):
            if len(chosen) >= max_fires:
                break
            if item["cost"] <= allowance + guard.EPSILON and item["cost"] <= left + guard.EPSILON:
                take(item)
                allowance -= item["cost"]
                left -= item["cost"]
    for band in BANDS[1:]:
        for item in list(bands[band]):
            if len(chosen) >= max_fires:
                break
            if item["cost"] <= left + guard.EPSILON:
                take(item)
                left -= item["cost"]
    return chosen


def improve_capped(items: list, improve_state: dict | None) -> tuple:
    """(kept, cut) of the improve band's `items` under the improve cap
    (#572): walked in allocate's own order with a copy of the guard's counts,
    each item kept only when `allowance_guard.improve_cap` allows it with the
    earlier kept items counted, the test the guard applies to each fire in
    turn. With no `improve_state` (a hand-built ctx, the explorer) there is
    no cap."""
    if improve_state is None:
        return list(items), []
    state = {**improve_state,
             "improve_by_kind": dict(improve_state.get("improve_by_kind") or {})}
    kept, cut = [], []
    for item in sorted(items, key=lambda i: (*i["order"], i["cost"], i["fixture"],
                                             i["model"], i["skill"])):
        if guard.improve_cap(state, item["mode"]):
            state["improve_by_kind"][item["mode"]] = \
                state["improve_by_kind"].get(item["mode"], 0) + 1
            kept.append(item)
        else:
            cut.append(item)
    return kept, cut


def build_plan(ctx: dict, now: datetime, max_fires: int = 30) -> dict:
    """The plan for `ctx` (see `gather`), as of `now`. Pure."""
    bands, work = eval_items(ctx, now)
    improve, needs, status, guidance_status, ranking = improve_items(ctx, now)
    triggers, hooks = trigger_items(ctx)
    improve_state = ctx.get("improve_state")
    improve, capped = improve_capped(improve, improve_state)
    bands["improve"].extend(improve)
    bands["bare"].extend(bare_items(ctx))
    chosen = allocate(bands, ctx["room"], max_fires)
    if not chosen and ctx.get("refresh"):
        # The guard's one refresh fire (allowance_guard.refresh): only an
        # ingested eval run brings a newer account reading, and without one
        # the stale holds refuse every fire until the weekly reset (2026-11-01,
        # the loop sat idle from 06:26 to 10:30 UTC with room left). The first
        # eval fire in band order, at most one reservation.
        evals = {band: [i for i in items if i["mode"] == "eval"]
                 for band, items in bands.items()}
        chosen = allocate(evals, ctx["reservation"], 1)
        for item in chosen:
            bands[item["band"]].remove(item)
    # Improve fires last: a long improve run in flight never holds up evals.
    chosen.sort(key=lambda i: i["mode"] in IMPROVE_MODES)
    fires = [{"slot": slot, "band": i["band"], "mode": i["mode"], "arms": i["arms"],
              "fixture": i["fixture"],
              "eval_key": i["fixture"][len("evals/"):] if i["fixture"] else "",
              "model": i["model"], "skill": i["skill"], "section": i.get("section") or "",
              "holdout": i["holdout"],
              "change_type": i["change_type"] or "measure", "cost": i["cost"],
              "value": i.get("value")}
             for slot, i in enumerate(chosen)]
    return {"schema_version": 1, "generated_at": _iso(now), "room": ctx["room"],
            "reservation": ctx["reservation"], "improve_charge": ctx["improve_charge"],
            "points_per_usd": ctx.get("points_per_usd"), "fires": fires,
            "unplanned": {band: len(items) + (len(capped) if band == "improve" else 0)
                          for band, items in bands.items()},
            # Whether one more fire of each kind passed the improve cap
            # before this plan (#572); None without a cap.
            "improve_allowed": None if improve_state is None else
            {mode: guard.improve_cap(improve_state, mode) for mode in IMPROVE_MODES},
            # Hook items first, trigger items just before improve's.
            "work": lesson_items(ctx.get("lessons", [])) + triggers + needs + work,
            "skills": status, "guidance": guidance_status, "improve_ranking": ranking,
            "hook_candidates": hooks, "real_work": ctx.get("real_work", []),
            # An eval leg sends no skill and no section, and only a
            # guidance-improve leg a section: the fire workflow refuses them
            # in any other mode.
            "matrix": {"include": [{**{k: f[k] for k in ("slot", "band", "mode", "arms",
                                                         "fixture", "eval_key", "model",
                                                         "holdout")},
                                    "skill": f["skill"] if f["mode"] == "improve" else "",
                                    "section": f["section"] if f["mode"] == "guidance-improve"
                                    else ""}
                                   for f in fires]}}


# ---------------------------------------------------------------------------
# Gathering the context. Everything below reads files, git or GitHub.

def _git_time(cwd: Path, *paths: str) -> datetime | None:
    """The newest commit time touching `paths` in the checkout at `cwd`."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", *paths], cwd=cwd,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return outcomes_mod.parse_time(out)


def _registry_time(registries: dict, skill: str) -> datetime | None:
    """The newest commit to the skill's directory in the adam-agentskills
    checkout, or None without one."""
    entry = registries.get("adam-agentskills")
    if not entry:
        return None
    root = Path(entry["path"])
    dirs = sorted(str(d.relative_to(root)) for d in root.glob(f"plugins/*/skills/{skill}")
                  if d.is_dir())
    return _git_time(root, *dirs) if dirs else None


def model_weights(tree: Path, models: list) -> dict:
    """Each roster model's share of the census counts (usage/latest.json:
    {model: {iso week: count}}), equal shares without a usable census."""
    try:
        doc = json.loads((tree / "usage" / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        doc = None
    counts = {}
    for model in models:
        weeks = doc.get(model) if isinstance(doc, dict) else None
        counts[model] = sum(v for v in weeks.values() if isinstance(v, int)
                            and not isinstance(v, bool) and v > 0) \
            if isinstance(weeks, dict) else 0
    total = sum(counts.values())
    if not total:
        return {model: 1 / len(models) for model in models} if models else {}
    return {model: count / total for model, count in counts.items()}


def points_per_usd(tree: Path, gates_doc: dict, limits: dict) -> float | None:
    """Measured allowance points per agent dollar over the ingested routine
    runs that have both a measured delta and a known cost."""
    usd: dict = {}
    for verdict in gates_doc["skills"].values():
        for cell in verdict.get("cells", []):
            for runs in cell.get("runs", {}).values():
                for run in runs:
                    parts = str(run.get("path", "")).split("/")
                    if parts[0] == guard.DEST_ROOT and len(parts) > 1 \
                            and isinstance(run.get("cost_usd"), (int, float)):
                        usd[parts[1]] = usd.get(parts[1], 0.0) + run["cost_usd"]
    points = spent = 0.0
    for run_id, dollars in sorted(usd.items()):
        cost = guard.measured_cost(tree / guard.DEST_ROOT / run_id, limits)
        if cost is not None and dollars > 0:
            points += cost
            spent += dollars
    return points / spent if spent and points else None


def _fixture_subject(evals_dir: Path, fixture: str) -> tuple:
    """("skill", skill name) for a skill fixture, or ("guidance", section id)
    for a guidance-section fixture, `evals/guidance/<section>/<name>` with
    `subject: guidance` and that `section:` (compute_gates.expected_guidance)."""
    import yaml
    doc = yaml.safe_load((evals_dir.parent / fixture / "fixture.yaml").read_text(encoding="utf-8"))
    doc = doc if isinstance(doc, dict) else {}
    parts = fixture.split("/")
    if doc.get("subject") == "guidance":
        section = doc.get("section")
        if len(parts) != 4 or parts[1] != "guidance" or not isinstance(section, str) \
                or parts[2] != section or section.startswith("_"):
            raise PlanError("a scheduled guidance fixture is not under its section")
        return "guidance", section
    if doc.get("subject") == "any":
        return "any", None  # a real-work row: no skill cell, the skill planner skips it
    skill = doc.get("skill")
    if not isinstance(skill, str):
        raise PlanError("a scheduled fixture names no skill")
    return "skill", skill


HOLD_PRIVATE = "private, paused"


def fixture_hold_reason(directory: Path) -> str | None:
    """Why the planner refuses to schedule the fixture in `directory`, or
    None when it may be. Adam, 2026-11-02: an isolation pair never pools
    (harness/gates.py pool_cells needs a tested digest and an arm context), so
    a skill fixture with no `context:` mapping ("no context") or a null
    `guidance_revision` pin ("null pin") is held, and a private-registry
    fixture ("private, paused") waits for a private context. A guidance or
    real-work fixture runs in situ and needs no context."""
    import yaml  # noqa: PLC0415
    try:
        doc = yaml.safe_load((directory / "fixture.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        doc = None
    doc = doc if isinstance(doc, dict) else {}
    if doc.get("registry") == PRIVATE_REGISTRY_URL:
        return HOLD_PRIVATE
    if doc.get("subject") in ("guidance", "any"):
        return None
    if not isinstance(doc.get("context"), dict):
        return "no context"
    if doc["context"].get("guidance_revision") is None:
        return "null pin"
    return None


def real_work_rows(evals_dir: Path) -> list:
    """The scheduled `subject: any` fixtures: real-work rows the skill planner
    does not plan."""
    committed = schedule.committed_fixtures(evals_dir.parent)
    scheduled = schedule.scheduled_fixtures(evals_dir / "scheduled.yml", committed)
    return [f for f in scheduled if _fixture_subject(evals_dir, f)[0] == "any"
            and fixture_hold_reason(evals_dir.parent / f) != HOLD_PRIVATE]


def fire_sweeps(starts, gap: timedelta = OUTAGE_GAP, span: timedelta | None = None) -> list:
    """Group fire start times into sweeps: sorted, and a start at most `gap`
    (inclusive) after the previous start joins its sweep, else opens a new
    one. With `span`, a start more than `span` after the sweep's first start
    opens a new one too; with None a chain of starts each within `gap` is one
    sweep however long it runs, the grouping explorer_data (#573) uses."""
    sweeps: list = []
    for start in sorted(starts):
        if sweeps and start - sweeps[-1][-1] <= gap \
                and (span is None or start - sweeps[-1][0] <= span):
            sweeps[-1].append(start)
        else:
            sweeps.append([start])
    return sweeps


def _landed_runs(cell: dict | None) -> list | None:
    """The start-of-run times of every run of the cell on its model, any role
    or digest (gates' `run_stamps_on_model`), or None when unknown: the key
    is absent (a verdict document from before it), not a list, or holds an
    unreadable stamp. A cell the verdict document does not list has none."""
    if cell is None:
        return []
    raw = cell.get("run_stamps_on_model")
    if not isinstance(raw, list):
        return None
    times = [_stamp_time(stamp) for stamp in raw]
    return None if None in times else times


def eval_cells(evals_dir: Path, gates_doc: dict, fire_runs: list, now: datetime) -> list:
    """The cells of `eval_cells_and_outages`."""
    return eval_cells_and_outages(evals_dir, gates_doc, fire_runs, now)[0]


def eval_cells_and_outages(evals_dir: Path, gates_doc: dict, fire_runs: list,
                           now: datetime) -> tuple:
    """(cells, outage sweeps). One cell per scheduled fixture x roster model,
    with its gates class, run counts, newest run, mean cost per run,
    `empty_fires`, `outage_fires`, `pending`, and `schedulable` with its
    `hold_reason` (fixture_hold_reason). A held cell stays in the list for
    the cost statistics; `eval_items` plans none of it. A `subject: any` row
    makes no cell (`real_work_rows` lists it). Each outage sweep is
    {"start", "fires"}: its first start and how many fires it holds.

    A cell is UNKNOWN when its gates cell lacks `newest_on_model` or
    `run_stamps_on_model` (a verdict document from before them) or either
    holds an unreadable stamp. It counts 0 for both fire counts, fails safe,
    never fixture-broken on a guess, and its fires take no part in any
    sweep. A cell the verdict document does not list has no run at all: it
    is known, with no bound.

    FIRE STATES. Every successful non-bare eval fire on a known cell that
    started at or after EMPTY_FIRES_SINCE and within RETRY_AFTER +
    OUTAGE_SPAN, and every successful or still running one younger than
    FIRE_RESULT_WINDOW, is exactly one of: young (younger than
    FIRE_RESULT_WINDOW), delivered (the cell has a run stamped inside
    [start, start + FIRE_RESULT_WINDOW]) or empty. The state never changes
    once the fire is old enough: a later retry's run falls outside an
    earlier fire's window. Grouping looks back OUTAGE_SPAN past RETRY_AFTER
    so a candidate near that edge keeps the sweep it was judged in.

    SWEEPS group every classified fire of every known cell (fire_sweeps,
    OUTAGE_GAP, capped at OUTAGE_SPAN). A sweep with a young fire is
    UNDECIDED. One with no delivered fire whose empty fires cover at least
    OUTAGE_CELLS distinct cells is an OUTAGE: a routine outage empties every
    fire at once and says nothing about any one fixture. A narrower sweep
    cannot be told from broken fixtures, so it counts.

      * `empty_fires`: the cell's candidates, empty fires that started after
        gates' `newest_on_model` (no bound when it is None: no run on its
        model) and within RETRY_AFTER, that are counted: outside any
        outage, or inside one past the cell's OUTAGE_EXCUSES. The bound is
        the newest run of ANY role or digest on that model, not the pooled
        newest: a fire that landed a run that does not pool still produced
        something.
      * `outage_fires`: the candidates excused as an outage's, at most
        OUTAGE_EXCUSES per cell, its earliest. The backstop: a cell empty in
        outage after outage still reaches BROKEN_AFTER_FIRES, one fire
        later, so broken fixtures that fail together are not retried
        forever. A candidate in an UNDECIDED sweep is in neither count
        until the sweep is decided.
      * `pending`: a successful or still running non-bare eval fire that
        started after the bound and less than FIRE_RESULT_WINDOW ago, so
        its run may still land. On an unknown cell any such fire is
        pending: holding a cell for at most FIRE_RESULT_WINDOW is cheaper
        than a second fire.
    A refused run counts as empty: routine-eval-fire.yml concludes `success`
    once the fire API accepts, so fixture-broken means "no run after n
    fires", whatever the cause."""
    committed = schedule.committed_fixtures(evals_dir.parent)
    scheduled = schedule.scheduled_fixtures(evals_dir / "scheduled.yml", committed)
    finished: dict = {}
    young: dict = {}
    for run in fire_runs:
        title = outcomes_mod.parse_title(run.get("display_title"))
        started = outcomes_mod.parse_time(run.get("run_started_at") or run.get("created_at"))
        # A bare fire runs one arm, never the cell's pair: neither empty nor pending.
        if not (title and title["mode"] == "eval" and not title["bare"] and title["model"]
                and started):
            continue
        key = (title["target"], title["model"])
        running = run.get("status") not in (None, "completed")
        if now - started < FIRE_RESULT_WINDOW:
            if running or run.get("conclusion") == "success":
                young.setdefault(key, []).append(started)
        elif run.get("conclusion") == "success" \
                and now - started <= RETRY_AFTER + OUTAGE_SPAN \
                and started >= EMPTY_FIRES_SINCE:
            finished.setdefault(key, []).append(started)
    table = stakes_mod.load(evals_dir / "stakes.yml", evals_dir)
    cells = []
    fires: list = []  # (start, state, cell index) of every classified fire
    candidates: list = []  # per cell, its candidates' starts, earliest first
    for fixture in scheduled:
        subject, ident = _fixture_subject(evals_dir, fixture)
        if subject == "any":
            continue  # a real-work row is not a skill cell
        hold = fixture_hold_reason(evals_dir.parent / fixture)
        parts = fixture.split("/")
        if subject == "guidance":
            # Pooled by section (results/guidance/<id>/...), in-situ cells.
            skill, section, name = "", ident, parts[3]
            verdict = (gates_doc.get("guidance") or {}).get(section, {})
        else:
            skill, section = ident, None
            name = parts[2] if len(parts) == 3 else None
            verdict = gates_doc["skills"].get(skill, {})
        for model in gates_doc["roster_models"]:
            cell = next((c for c in verdict.get("cells", [])
                         if c.get("fixture") == name and c.get("model") == model), None)
            runs = cell.get("runs", {}) if cell else {}
            entries = [r for role in ("with", "without") for r in runs.get(role, [])]
            stamps = sorted({r["timestamp"] for r in entries})
            cost = cell.get("cost_usd") if cell else None
            arm_trials = sum(r.get("scored_trials") or 0 for r in entries)
            newest = stamps[-1] if stamps else None
            cls = cell["class"] if cell else "missing"
            raw = cell.get("newest_on_model") if cell else None
            bound = _stamp_time(raw)
            landed = _landed_runs(cell)
            # An unreadable stamp is as unknown as an absent key.
            known = landed is not None and (cell is None or (
                "newest_on_model" in cell and (raw is None or bound is not None)))
            waiting = [t for t in young.get((fixture, model), [])
                       if not known or bound is None or t > bound]
            mine: list = []
            if known:
                index = len(cells)
                for t in young.get((fixture, model), []):
                    fires.append((t, "young", index))
                for t in finished.get((fixture, model), []):
                    if any(t <= r <= t + FIRE_RESULT_WINDOW for r in landed):
                        fires.append((t, "delivered", index))
                        continue
                    fires.append((t, "empty", index))
                    if (bound is None or t > bound) and now - t <= RETRY_AFTER:
                        mine.append(t)
            candidates.append(sorted(mine))
            cells.append({
                "skill": skill, "section": section, "fixture": fixture, "model": model,
                "class": cls, "verdict": verdict.get("verdict"),
                "schedulable": hold is None, "hold_reason": hold,
                "stakes": stakes_mod.level_of(table, subject, ident),
                "with_runs": len(runs.get("with", [])),
                "without_runs": len(runs.get("without", [])), "newest": newest,
                "usd_per_fire": cost / len(stamps) if cost is not None and stamps else None,
                "usd_per_arm_trial": cost / arm_trials if cost is not None and arm_trials
                else None,
                "empty_fires": 0, "outage_fires": 0, "pending": bool(waiting)})
    # Second pass, once every fire is classified: judge each sweep, then
    # count each cell's candidates against its sweep's judgement.
    sweeps = fire_sweeps({t for t, _, _ in fires}, OUTAGE_GAP, OUTAGE_SPAN)
    sweep_of = {t: i for i, sweep in enumerate(sweeps) for t in sweep}
    members: list = [[] for _ in sweeps]
    for t, state, index in fires:
        members[sweep_of[t]].append((state, index))
    judged = []
    for group in members:
        states = {state for state, _ in group}
        empty_cells = {index for state, index in group if state == "empty"}
        if "young" in states:
            judged.append("undecided")
        elif "delivered" not in states and len(empty_cells) >= OUTAGE_CELLS:
            judged.append("outage")
        else:
            judged.append("counted")
    for out, times in zip(cells, candidates):
        for t in times:  # earliest first, so the excuse goes to the earliest
            if judged[sweep_of[t]] == "undecided":
                continue
            if judged[sweep_of[t]] == "outage" and out["outage_fires"] < OUTAGE_EXCUSES:
                out["outage_fires"] += 1
            else:
                out["empty_fires"] += 1
    outages = [{"start": sweep[0], "fires": len(members[i])}
               for i, sweep in enumerate(sweeps) if judged[i] == "outage"]
    return cells, outages


def bare_cells(evals_dir: Path, gates_doc: dict, fire_runs: list) -> list:
    """{fixture, model, skill} for each (scheduled skill fixture that runs in
    place, roster model) with no bare run yet (module docstring, band 6):
    none in the verdict document's `bare_runs` and no bare fire for it that
    succeeded or is still running. A guidance fixture has none: its arms are
    its own."""
    committed = schedule.committed_fixtures(evals_dir.parent)
    scheduled = schedule.scheduled_fixtures(evals_dir / "scheduled.yml", committed)
    done = {(run.get("skill"), run.get("fixture"), run.get("model"))
            for run in gates_doc.get("bare_runs", []) if isinstance(run, dict)}
    fired = set()
    for run in fire_runs:
        title = outcomes_mod.parse_title(run.get("display_title")) \
            if isinstance(run, dict) else None
        if title and title["bare"] and title["model"] \
                and (run.get("conclusion") == "success"
                     or run.get("status") not in (None, "completed")):
            fired.add((title["target"], title["model"]))
    out = []
    for fixture in scheduled:
        subject, skill = _fixture_subject(evals_dir, fixture)
        if subject != "skill" or not schedule.declares_context(evals_dir.parent / fixture):
            continue
        parts = fixture.split("/")
        name = parts[2] if len(parts) == 3 else None
        for model in gates_doc["roster_models"]:
            if (skill, name, model) not in done and (fixture, model) not in fired:
                out.append({"fixture": fixture, "model": model, "skill": skill})
    return out


def skill_contexts(evals_dir: Path, tree: Path, as_of: str, registries: dict,
                   gates_doc: dict, records: list, prs: list, on_hold: list,
                   now: datetime) -> dict:
    """Per skill with fixtures under evals/: what rule A and C need."""
    import compute_gates
    import gates
    import yaml
    index = compute_gates.build_index(tree, evals_dir, as_of)
    models = gates_doc["roster_models"]
    roster_changed = _git_time(evals_dir.parent, "evals/roster.yml")
    out = {}
    for directory in sorted(p for p in evals_dir.iterdir() if p.is_dir()):
        if directory.name == "guidance":
            # Guidance sections, not a skill: no improve loop, no usage weight.
            continue
        expected = compute_gates.expected_content(evals_dir, directory.name, registries)
        if not expected:
            continue
        urls, names = set(), sorted(expected)
        for name in names:
            try:
                doc = yaml.safe_load((directory / name / "fixture.yaml").read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, yaml.YAMLError):
                doc = None
            urls.add(doc.get("registry") if isinstance(doc, dict) else None)
            if not isinstance(doc, dict) or doc.get("skill") != directory.name:
                urls.add(None)
        if PRIVATE_REGISTRY_URL in urls:
            continue
        skill = directory.name
        cells = gates.pool_cells(index["runs"], skill, models, expected)
        holdout = names[0] if len(names) >= MIN_IMPROVE_FIXTURES else ""
        train = [n for n in names if n != holdout]
        changes = [t for t in (roster_changed,
                               _git_time(evals_dir.parent, f"evals/{skill}"),
                               _registry_time(registries, skill)) if t]
        out[skill] = {
            "fixtures": len(names), "holdout": holdout,
            "registry_ok": urls == {REGISTRY_URL},
            "verdict": gates_doc["skills"].get(skill, {}).get("verdict", "insufficient"),
            "evidence": train_evidence(cells, train),
            "pause": pause(skill, records, prs, on_hold, now,
                           max(changes) if changes else None,
                           lambda moment, cells=cells: with_run_after(cells, moment))}
    return out


def guidance_contexts(evals_dir: Path, tree: Path, as_of: str, gates_doc: dict,
                      guidance_dir: Path | None, records: list = (), prs: list = (),
                      removals: list = (), on_hold: list = (),
                      now: datetime | None = None) -> dict:
    """Per guidance section with fixtures that declare the `full` ablation
    arm (scripts/propose_guidance_edit.py's own listing): what improve
    eligibility needs, {fixtures, holdout, holdout_fixture, verdict,
    evidence, row_ok, pause}. The holdout is the last fixture in name order,
    as the proposer picks it, and only when there are MIN_IMPROVE_FIXTURES:
    `holdout` its directory name (the cells' key), `holdout_fixture` its key
    relative to evals/ (what the fire sends). The evidence is
    `train_evidence` over the other fixtures' pooled in-situ `full` arm
    runs; `row_ok` whether the proposer's `load_row` accepts the section's
    manifest row; `pause` rule C (`pause` keyed by section, then
    `guidance_lane`) over the guidance-improve `records`, the
    `eval-guidance-improve/` `prs` and the open `removals`. {} without
    `guidance_dir` (a section's extent, hence its cells, needs the
    checkout)."""
    root = evals_dir / "guidance"
    if guidance_dir is None or not root.is_dir() or root.is_symlink():
        return {}
    import compute_gates
    import gates
    import propose_guidance_edit as proposer
    index = compute_gates.build_index(tree, evals_dir, as_of)
    runs = [r for r in index["guidance_runs"] if r.get("pair") == "in_situ"]
    now = now or datetime.now(timezone.utc)
    roster_changed = _git_time(evals_dir.parent, "evals/roster.yml")
    out = {}
    for directory in sorted(p for p in root.iterdir()
                            if p.is_dir() and not p.is_symlink() and not p.name.startswith("_")):
        section = directory.name
        try:
            found = proposer.fixture_layout_discover(evals_dir, section)
        except proposer.Refusal:
            raise PlanError("a guidance fixture is unreadable") from None
        if not found:
            continue
        names = [Path(f).name for f in found]
        enough = len(names) >= MIN_IMPROVE_FIXTURES
        holdout = names[-1] if enough else ""
        cells = gates.pool_cells(runs, section, gates_doc["roster_models"],
                                 compute_gates.expected_guidance(evals_dir, section,
                                                                 guidance_dir))
        try:
            row = proposer.load_row(guidance_dir, section)
        except proposer.Refusal:
            row = None
        changes = [t for t in (roster_changed,
                               _git_time(evals_dir.parent, f"evals/guidance/{section}"),
                               _git_time(guidance_dir, row["file"]) if row else None) if t]
        out[section] = {
            "fixtures": len(found), "holdout": holdout,
            "holdout_fixture": found[-1] if enough else "",
            "verdict": (gates_doc.get("guidance") or {}).get(section, {}).get(
                "verdict", "insufficient"),
            "evidence": train_evidence(cells, [n for n in names if n != holdout]),
            "row_ok": row is not None,
            "pause": pause(section, list(records), list(prs), list(on_hold), now,
                           max(changes) if changes else None,
                           lambda moment, cells=cells: with_run_after(cells, moment),
                           key="section")
            or guidance_lane(section, list(records), list(prs), list(removals))}
    return out


def fetch_evidence(token: str, now: datetime) -> dict:
    """The GitHub evidence, read live (fail closed)."""
    get = outcomes_mod.github_get
    since = now - STOP_FOR - timedelta(days=30)
    fire_runs = outcomes_mod.fetch_fire_runs(SELF_REPO, token, since)
    branches = outcomes_mod.fetch_improve_branches(SELF_REPO, token)
    guidance_branches = outcomes_mod.fetch_improve_branches(SELF_REPO, token,
                                                            mode="guidance-improve")

    def pulls_of(repo: str) -> list:
        pulls = []
        for page in range(1, outcomes_mod.MAX_PAGES + 1):
            rows = get(f"/repos/{repo}/pulls?state=all&per_page=100&page={page}", token)
            if not isinstance(rows, list):
                raise outcomes_mod.EvidenceError("the pulls API answered without a list")
            pulls.extend(rows)
            if len(rows) < 100:
                break
        return pulls

    def on_hold_of(repo: str) -> list:
        rows = get(f"/repos/{repo}/issues?state=open&labels=on-hold&per_page=100", token)
        if not isinstance(rows, list):
            raise outcomes_mod.EvidenceError("the issues API answered without a list")
        return [r.get("title") for r in rows if isinstance(r, dict)]
    own = on_hold_of(SELF_REPO)
    return {"fire_runs": fire_runs, "improve_branches": branches,
            "registry_prs": pulls_of(REGISTRY_REPO),
            "on_hold": own + on_hold_of(REGISTRY_REPO),
            "guidance_branches": guidance_branches,
            "guidance_prs": pulls_of(GUIDANCE_REPO),
            "guidance_on_hold": own + on_hold_of(GUIDANCE_REPO)}


def registry_prs(rows: list) -> tuple:
    """(improve PRs as {skill, state, created_at, closed_at, merged_at},
    skills with an open removal PR) from the pulls API's rows."""
    improve, removal = [], set()
    for row in rows:
        head = (row.get("head") or {}).get("ref") if isinstance(row, dict) else None
        if not isinstance(head, str):
            continue
        for prefix in ("eval-improve/", "retire-skill/"):
            skill = head[len(prefix):] if head.startswith(prefix) else None
            if skill is None or not outcomes_mod.SKILL_RE.fullmatch(skill):
                continue
            if prefix == "retire-skill/":
                if row.get("state") == "open":
                    removal.add(skill)
            else:
                improve.append({"skill": skill, "state": row.get("state"),
                                "created_at": row.get("created_at"),
                                "closed_at": row.get("closed_at"),
                                "merged_at": row.get("merged_at")})
    return improve, sorted(removal)


def guidance_prs(rows: list) -> tuple:
    """(guidance improve PRs as {section, state, created_at, closed_at,
    merged_at}, sections with an open removal PR) from _agent-guidance's
    pulls API rows: `eval-guidance-improve/<section>` and
    `retire-guidance/<section>` heads."""
    improve, removal = [], set()
    for row in rows:
        head = (row.get("head") or {}).get("ref") if isinstance(row, dict) else None
        if not isinstance(head, str):
            continue
        for prefix in (GUIDANCE_IMPROVE_PREFIX, GUIDANCE_REMOVAL_PREFIX):
            section = head[len(prefix):] if head.startswith(prefix) else None
            if section is None or not outcomes_mod.SECTION_RE.fullmatch(section):
                continue
            if prefix == GUIDANCE_REMOVAL_PREFIX:
                if row.get("state") == "open":
                    removal.add(section)
            else:
                improve.append({"section": section, "state": row.get("state"),
                                "created_at": row.get("created_at"),
                                "closed_at": row.get("closed_at"),
                                "merged_at": row.get("merged_at")})
    return improve, sorted(removal)


def read_lessons(directory: Path | None) -> list:
    if directory is None:
        return []
    lessons = []
    for path in sorted(directory.rglob("*.json")):
        try:
            if path.is_symlink() or path.stat().st_size > 64 * 1024:
                continue
            lessons.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, UnicodeDecodeError, RecursionError):
            continue
    return lessons


def private_skills(evals_dir: Path) -> frozenset:
    """The skills with a fixture in the private registry (`registry:` is
    PRIVATE_REGISTRY_URL). The public census never counts them, so their
    usage weight is unknown, not 0."""
    import yaml  # noqa: PLC0415
    out = set()
    for path in sorted(evals_dir.rglob("fixture.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        if (isinstance(doc, dict) and isinstance(doc.get("skill"), str)
                and doc.get("registry") == PRIVATE_REGISTRY_URL):
            out.add(doc["skill"])
    return frozenset(out)


def skill_weights(tree: Path, skills: list, now: datetime,
                  private: frozenset = frozenset()) -> dict:
    """{skill: weight or None} from harness/skill_usage.py (skills-evals#420)
    over usage/weekly-local.json on the results branch: invocations over the
    last four weeks, 0 for a fresh census that never saw the skill, None
    when unknown (stale or absent). A skill in `private` is always None: the
    public census counts it under `other`, so a 0 would be false. Until that
    module is on main every weight is unknown, which `neutral_weights` makes
    neutral."""
    try:
        import skill_usage  # noqa: PLC0415 - optional until #420 merges
    except ImportError:
        return {skill: None for skill in skills}
    try:
        doc = skill_usage.load(tree / "usage" / "weekly-local.json")
    except (OSError, ValueError):
        doc = None
    out = {}
    for skill in skills:
        if skill in private:
            out[skill] = None
            continue
        try:
            value = skill_usage.weight(doc, skill, now) if doc is not None else None
        except (TypeError, ValueError, KeyError):
            value = None
        out[skill] = value if isinstance(value, (int, float)) and not isinstance(value, bool) \
            and value >= 0 else None
    return out


def guidance_use(tree: Path, now: datetime) -> float | None:
    """The expected uses of every guidance section over USE_WINDOW_DAYS: all
    of it loads in every session, so the census's transcript sessions
    scanned, scaled to that window (skill_usage.session_rate). None when
    unknown (stale, absent or unreadable census), which the ranking makes
    neutral."""
    try:
        import skill_usage  # noqa: PLC0415 - optional, as in skill_weights
        value = skill_usage.session_rate(skill_usage.load(tree / "usage" / "weekly-local.json"),
                                         now, USE_WINDOW_DAYS)
    except (ImportError, OSError, ValueError, TypeError, KeyError, AttributeError):
        return None
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) \
        and value >= 0 else None


def trigger_contexts(evals_dir: Path, registries: dict) -> dict:
    """{skill: {"trigger_set", "hook_candidate"}} for every skill of the
    adam-agentskills checkout (`plugins/*/skills/<skill>/SKILL.md`, the one
    registry the routine improves); {} without one."""
    entry = registries.get("adam-agentskills")
    if not entry:
        return {}
    out = {}
    for path in sorted(Path(entry["path"]).glob("plugins/*/skills/*/SKILL.md")):
        name = path.parent.name
        if not outcomes_mod.SKILL_RE.fullmatch(name) or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        found = evals_dir / name / TRIGGER_SET
        out[name] = {"trigger_set": found.is_file() and not found.is_symlink(),
                     "hook_candidate": hook_candidate(text)}
    return out


def gather(args, now: datetime) -> dict:
    import compute_gates
    evals_dir = args.evals_dir
    registries = compute_gates.flag_registries(args.registry)
    limits = guard.budget_file.load_budget(args.budget)
    gates_doc = compute_gates.compute(args.results_tree, evals_dir / "roster.yml",
                                      evals_dir / "gate-policy.yml", evals_dir,
                                      compute_gates.parse_as_of(args.as_of), registries,
                                      args.guidance)
    if args.evidence is not None:
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    else:
        evidence = fetch_evidence(os.environ.get("GH_TOKEN", ""), now)
    records = outcomes_mod.outcomes(evidence["fire_runs"], evidence["improve_branches"], now)
    prs, removal = registry_prs(evidence["registry_prs"])
    grecords = outcomes_mod.outcomes(evidence["fire_runs"],
                                     evidence.get("guidance_branches", []), now,
                                     mode="guidance-improve")
    gprs, gremoval = guidance_prs(evidence.get("guidance_prs", []))
    since = guard.window_start(now)
    # No own run: every not-completed improve fire counts (#572).
    by_kind, in_flight = guard.improve_kind_counts(evidence["fire_runs"], now, since)
    state = guard.account(args.results_tree, limits, now,
                          _fire_pair(evidence["fire_runs"], now, since),
                          guard.improve_counts(evidence["fire_runs"], now, since),
                          since,
                          improve_started=guard.improve_starts(evidence["fire_runs"], now, since),
                          eval_started=guard.eval_fire_starts(evidence["fire_runs"], now, since),
                          improve_by_kind=by_kind, improve_in_flight=in_flight)
    print(guard.describe(state))
    skills = skill_contexts(evals_dir, args.results_tree,
                            compute_gates.parse_as_of(args.as_of), registries,
                            gates_doc, records, prs, evidence["on_hold"], now)
    triggers = trigger_contexts(evals_dir, registries)
    cells, outages = eval_cells_and_outages(evals_dir, gates_doc, evidence["fire_runs"], now)
    held = sum(1 for c in cells if c["hold_reason"] == HOLD_PRIVATE)
    if held:
        print(f"{held} private cells held")  # a count only: no name in the log
    return {"policy": gates_doc["policy"], "reservation": state["reservation"],
            "overrun": limits["per_run_overrun"], "improve_charge": state["improve_charge"],
            "room": guard.room(state),
            # What allowance_guard.improve_cap reads, for build_plan's walk.
            "improve_state": {key: state[key] for key in (
                "cap", "improve_charge", "improve_by_kind", "improve_in_flight")},
            # One eval fire may go only to bring a newer reading.
            "refresh": guard.fits(state) < 1 and guard.refresh(state),
            "points_per_usd": points_per_usd(args.results_tree, gates_doc, limits),
            "model_weights": model_weights(args.results_tree, gates_doc["roster_models"]),
            "removal_prs": removal,
            "cells": cells, "outages": outages, "real_work": real_work_rows(evals_dir),
            "bare": bare_cells(evals_dir, gates_doc, evidence["fire_runs"]),
            "skills": skills,
            "guidance": guidance_contexts(evals_dir, args.results_tree,
                                          compute_gates.parse_as_of(args.as_of), gates_doc,
                                          args.guidance, grecords, gprs, gremoval,
                                          evidence.get("guidance_on_hold", []), now),
            "guidance_use": guidance_use(args.results_tree, now),
            "triggers": triggers,
            "skill_weights": skill_weights(args.results_tree, sorted(set(skills) | set(triggers)),
                                           now, private_skills(evals_dir)),
            "lessons": read_lessons(args.lessons)}


def _fire_pair(runs: list, now: datetime, since: datetime | None = None) -> tuple:
    """(successful fires since `since`, default the last week; in the guard's
    hold) from the rows."""
    times = [outcomes_mod.parse_time(r.get("run_started_at") or r.get("created_at"))
             for r in runs if isinstance(r, dict) and r.get("conclusion") == "success"]
    times = [t for t in times if t is not None]
    since = since or now - guard.WINDOW
    return (sum(1 for t in times if t >= since),
            sum(1 for t in times if t >= now - guard.PENDING_FULL_HOLD))


def summary_lines(plan: dict) -> list:
    """Public-safe lines: counts, bands, public skill and fixture names."""
    lines = [f"### Weekly plan: {len(plan['fires'])} fire(s), room "
             f"{plan['room'] * 100:.1f} points", ""]
    for fire in plan["fires"]:
        target = fire["fixture"] or (f"{fire['skill'] or fire.get('section', '')} "
                                     f"(holdout {fire['holdout']})")
        mode = fire["mode"] + (" bare" if fire.get("arms") == "bare" else "")
        lines.append(f"- {fire['band']}: {mode} {target} {fire['model']}".rstrip()
                     + f", {fire['cost'] * 100:.2f} points")
    kinds: dict = {}
    for item in plan["work"]:
        kinds[item["kind"]] = kinds.get(item["kind"], 0) + 1
    lines.append("")
    if plan.get("real_work"):
        lines.append("Real-work row, not planned by the skill planner: "
                     + ", ".join(plan["real_work"]))
    lines.append("Work items: " + (", ".join(f"{k} {v}" for k, v in sorted(kinds.items()))
                                   or "none"))
    eligible = sorted(s for s, v in plan["skills"].items() if v["eligible"])
    lines.append("Improve-eligible skills: " + (", ".join(eligible) or "none"))
    lines.append("Hook candidates (mostly checklist or rules sections): "
                 + (", ".join(plan.get("hook_candidates", [])) or "none"))
    lines += ["", "Improve ranking (value = use × headroom ÷ cost)", ""]
    ranking = plan.get("improve_ranking", [])[:10]
    for row in ranking:
        value = "unknown" if row["value"] is None else f"{row['value']:.3g}"
        headroom = "unknown" if row["headroom"] is None else f"{row['headroom']:.2f}"
        end = ", eligible" if row["eligible"] else f": {row['reasons'][0]}"
        lines.append(f"- {row['subject']} {row['name']}: value {value} (use {row['use']:.1f}, "
                     f"headroom {headroom}, cost {row['cost'] * 100:.2f} points){end}")
    if not ranking:
        lines.append("- none")
    return lines


# ---------------------------------------------------------------------------
# The dispatch legs.

def validate_fire(env: dict, root: Path = REPO_ROOT) -> None:
    """Refuse a matrix leg that is not a fire this repository would plan:
    eval mode on a scheduled, committed fixture and a roster arm, its arms
    both, or bare on a fixture that runs in place; improve mode on a skill
    improve_gate.py fire-check accepts, with a holdout and no arms;
    guidance-improve mode on a section guidance_improve_gate.py fire-check
    accepts, with its holdout fixture key and no arms. Only a
    guidance-improve leg carries a section."""
    import guidance_improve_gate
    import improve_gate
    import roster_arm
    mode = env.get("MODE", "")
    fixture, key, model = env.get("FIXTURE", ""), env.get("EVAL_KEY", ""), env.get("MODEL", "")
    skill, holdout = env.get("SKILL", ""), env.get("HOLDOUT", "")
    section = env.get("SECTION", "")
    arms = env.get("ARMS", "")
    if section and mode != "guidance-improve":
        raise PlanError("only a guidance-improve leg carries a section")
    if mode == "eval":
        committed = schedule.committed_fixtures(root)
        scheduled = schedule.scheduled_fixtures(root / "evals" / "scheduled.yml", committed)
        if fixture not in scheduled or schedule.validate_fixture(fixture, committed) != key \
                or skill or holdout or arms not in ("both", "bare") \
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", model) \
                or not roster_arm.is_arm(model, root / "evals" / "roster.yml"):
            raise PlanError("the eval leg is not a scheduled fixture on a roster arm")
        if arms == "bare" and not schedule.declares_context(root / fixture):
            raise PlanError("the bare leg's fixture does not run in place")
        if arms == "both" and fixture_hold_reason(root / fixture) is not None:
            raise PlanError("the eval leg's fixture is held, not schedulable")
    elif mode == "improve":
        if fixture or key or model or arms or not outcomes_mod.SKILL_RE.fullmatch(skill) \
                or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", holdout):
            raise PlanError("the improve leg is malformed")
        try:
            improve_gate.fire_check(skill, holdout)
        except improve_gate.Rejected:
            raise PlanError("the improve leg is refused by the fixture check") from None
    elif mode == "guidance-improve":
        if fixture or key or model or arms or skill \
                or not outcomes_mod.SECTION_RE.fullmatch(section) \
                or not GUIDANCE_FIXTURE_RE.fullmatch(holdout):
            raise PlanError("the guidance-improve leg is malformed")
        try:
            guidance_improve_gate.fire_check(section, holdout, evals_dir=root / "evals")
        except guidance_improve_gate.Rejected:
            raise PlanError("the guidance-improve leg is refused by the fixture check") from None
    else:
        raise PlanError("the leg's mode is not eval, improve or guidance-improve")


def in_flight(runs: list, now: datetime) -> int:
    """Fire runs still running, or started within their mode's flight time."""
    count = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        started = outcomes_mod.parse_time(run.get("run_started_at") or run.get("created_at"))
        if run.get("status") not in (None, "completed"):
            count += 1
            continue
        if started is None or run.get("conclusion") != "success":
            continue
        title = outcomes_mod.parse_title(run.get("display_title"))
        flight = IMPROVE_FLIGHT if title and title["mode"] in IMPROVE_MODES else EVAL_FLIGHT
        if now - started < flight:
            count += 1
    return count


def wait_slot(fetch, max_wait: int, clock=lambda: datetime.now(timezone.utc),
              sleep=time.sleep) -> bool:
    """Poll until fewer than MAX_IN_FLIGHT fires are in flight; False after
    `max_wait` seconds. `fetch(since)` returns the fire runs."""
    waited = 0
    while True:
        now = clock()
        if in_flight(fetch(now - IMPROVE_FLIGHT), now) < MAX_IN_FLIGHT:
            return True
        if waited + POLL_SECONDS > max_wait:
            return False
        sleep(POLL_SECONDS)
        waited += POLL_SECONDS


def watchdog_due(anchor: datetime, fire_runs: list) -> datetime:
    """When to re-plan after a sweep at `anchor`: WATCHDOG_IDLE after it, or
    earlier, WATCHDOG_MARGIN after the first guard hold (a successful fire's
    PENDING_FULL_HOLD) that was still running at `anchor` ends."""
    due = anchor + WATCHDOG_IDLE
    for run in fire_runs:
        if not isinstance(run, dict) or run.get("conclusion") != "success":
            continue
        started = outcomes_mod.parse_time(run.get("run_started_at") or run.get("created_at"))
        if started is None:
            continue
        ends = started + guard.PENDING_FULL_HOLD
        if ends > anchor:
            due = min(due, ends + WATCHDOG_MARGIN)
    return due


def watchdog_decide(sweeps: list, fire_runs: list, now: datetime,
                    anchor: datetime | None = None) -> tuple:
    """("dispatch" | "wait" | "stand-down", due or None).

    With `anchor` (wait mode, armed at a sweep's end): any sweep created after
    it stands this watchdog down, since that sweep arms its own. Without
    (check mode): any sweep not finished stands it down, and the anchor is the
    newest finished sweep's end; no sweep at all is due now."""
    rows = [r for r in sweeps if isinstance(r, dict)]
    if anchor is not None:
        for run in rows:
            created = outcomes_mod.parse_time(run.get("created_at"))
            if created is None or created > anchor:
                return "stand-down", None
    else:
        if any(r.get("status") != "completed" for r in rows):
            return "stand-down", None
        ends = [outcomes_mod.parse_time(r.get("updated_at")) for r in rows]
        ends = [t for t in ends if t is not None]
        if not ends:
            return "dispatch", now
        anchor = max(ends)
    due = watchdog_due(anchor, fire_runs)
    return ("dispatch" if now >= due else "wait"), due


def fetch_runs(workflow: str, token: str, query: dict, get=outcomes_mod.github_get) -> list:
    """One page (newest first, 100) of `workflow`'s runs matching `query`."""
    doc = get(f"/repos/{SELF_REPO}/actions/workflows/{workflow}/runs?"
              + urllib.parse.urlencode({**query, "per_page": "100"}), token)
    found = doc.get("workflow_runs") if isinstance(doc, dict) else None
    if not isinstance(found, list):
        raise outcomes_mod.EvidenceError("the workflow runs API answered without a run list")
    return found


def watchdog(mode: str, fetch_sweeps, fetch_fires, timers_alive, max_wait: int,
             clock=lambda: datetime.now(timezone.utc), sleep=time.sleep) -> tuple:
    """Run the watchdog: (dispatch?, reason). `wait` mode anchors at its own
    start and sleeps until due (at most `max_wait` seconds in all); `check`
    mode decides once and stands down while a wait-mode watchdog is alive.
    `fetch_sweeps(since)` and `fetch_fires(since)` return runs created at or
    after `since`; `timers_alive()` is whether a wait-mode run is in
    progress."""
    start = clock()
    if mode == "check":
        if timers_alive():
            return False, "a waiting watchdog is armed"
        anchor = None
        sweeps = fetch_sweeps(start - timedelta(days=1))
    else:
        anchor = start
    while True:
        now = clock()
        if anchor is not None:
            sweeps = fetch_sweeps(anchor)
        since = (anchor or now) - guard.PENDING_FULL_HOLD - WATCHDOG_IDLE
        action, due = watchdog_decide(sweeps, fetch_fires(since), now, anchor)
        if action == "stand-down":
            return False, "a newer sweep is queued or running"
        if action == "dispatch":
            return True, f"re-plan due {_iso(due)}"
        if mode == "check":
            return False, f"next re-plan due {_iso(due)}"
        left = max_wait - (now - start).total_seconds()
        if left <= 0:
            return False, f"waited {max_wait}s; re-plan due {_iso(due)}"
        sleep(max(1, min((due - now).total_seconds(), left)))


def guidance_headroom(section: str, tree: Path, evals_dir: Path, guidance_dir: Path,
                      as_of: str) -> tuple:
    """(ok, message) for the fire check (module docstring, FIRE CHECK)."""
    import compute_gates
    gates_doc = compute_gates.compute(tree, evals_dir / "roster.yml",
                                      evals_dir / "gate-policy.yml", evals_dir,
                                      compute_gates.parse_as_of(as_of), {}, guidance_dir)
    info = guidance_contexts(evals_dir, tree, compute_gates.parse_as_of(as_of), gates_doc,
                             guidance_dir).get(section)
    headroom = info["evidence"]["headroom"] if info else None
    if headroom is None:
        return True, f"section {section}: train headroom unknown; the proposer measures it"
    if headroom < MIN_GAIN:
        return False, (f"section {section}: train headroom {headroom:.3f} is under the "
                       f"minimum gain {MIN_GAIN:g}; it needs harder fixtures, not an "
                       "improve run")
    return True, f"section {section}: train headroom {headroom:.3f}"


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--results-tree", type=Path, required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--registry", action="append", metavar="NAME=PATH")
    p.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    p.add_argument("--guidance", type=Path, default=None,
                   help="an _agent-guidance checkout: the guidance sections' content")
    p.add_argument("--budget", type=Path, default=None)
    p.add_argument("--evidence", type=Path, default=None)
    p.add_argument("--lessons", type=Path, default=None)
    p.add_argument("--max-fires", type=int, default=30)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--ranking-out", type=Path, default=None,
                   help="the improve ranking alone (public-safe), as JSON")
    sub.add_parser("validate-fire")
    p = sub.add_parser("guidance-headroom")
    p.add_argument("section")
    p.add_argument("--results-tree", type=Path, required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--guidance", type=Path, required=True)
    p.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    p = sub.add_parser("wait-slot")
    p.add_argument("--max-wait", type=int, default=1500)
    p = sub.add_parser("watchdog")
    p.add_argument("--mode", choices=("wait", "check"), required=True)
    p.add_argument("--max-wait", type=int, default=WATCHDOG_MAX_WAIT)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-fire":
            validate_fire(dict(os.environ))
            return 0
        if args.command == "guidance-headroom":
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.section):
                raise PlanError("the section id is malformed")
            ok, message = guidance_headroom(args.section, args.results_tree, args.evals_dir,
                                            args.guidance, args.as_of)
            print(message if ok else f"::error::{message}")
            return 0 if ok else 1
        if args.command == "wait-slot":
            token = os.environ.get("GH_TOKEN", "")
            ok = wait_slot(lambda since: outcomes_mod.fetch_fire_runs(SELF_REPO, token, since),
                           args.max_wait)
            if not ok:
                print(f"::error::{MAX_IN_FLIGHT} or more fires stayed in flight; not dispatching")
            return 0 if ok else 1
        if args.command == "watchdog":
            token = os.environ.get("GH_TOKEN", "")
            stamp = lambda moment: ">=" + moment.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
            go, reason = watchdog(
                args.mode,
                lambda since: fetch_runs(WEEKLY_WORKFLOW, token, {"created": stamp(since)}),
                lambda since: outcomes_mod.fetch_fire_runs(SELF_REPO, token, since),
                lambda: bool(fetch_runs(WATCHDOG_WORKFLOW, token,
                                        {"event": "workflow_dispatch",
                                         "status": "in_progress"})),
                args.max_wait)
            print(f"watchdog: {reason}")
            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
                    out.write(f"dispatch={'true' if go else 'false'}\n")
            return 0
        if not 1 <= args.max_fires <= 30:
            raise PlanError("the fire cap must be 1 to 30")
        now = datetime.now(timezone.utc)
        plan = build_plan(gather(args, now), now, args.max_fires)
    except (PlanError, outcomes_mod.EvidenceError, guard.GuardError,
            guard.budget_file.BudgetError) as exc:
        print(f"::error::weekly plan: {exc}")
        return 1
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError):
        # Never echo evidence content or exception bodies into the public log.
        print("::error::weekly plan: the plan could not be made")
        return 1
    lines = summary_lines(plan)
    print("\n".join(lines))
    if args.out is not None:
        args.out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.ranking_out is not None:
        args.ranking_out.write_text(json.dumps(
            {"schema_version": 1, "generated_at": plan["generated_at"],
             "improve_ranking": plan["improve_ranking"]}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write("matrix=" + json.dumps(plan["matrix"], separators=(",", ":")) + "\n")
            out.write(f"count={len(plan['fires'])}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
