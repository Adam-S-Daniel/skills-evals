#!/usr/bin/env python3
"""Act on a `retire` verdict (#70, part 2): file or update an issue, or open
an auto-merging removal pull request in adam-agentskills.

  retire_skill.py --gates FILE --registry adam-agentskills=PATH
                  [--registry NAME=PATH ...] [--dry-run]
                  [--allow-mode proposal|auto ...] [--usage FILE]

`--gates` is scripts/compute_gates.py's output. A skill acts only when its
verdict there is `retire`, and this script re-checks what that verdict
means before acting: every (fixture, roster model) cell of the cells'
fixtures crossed with the gates file's roster models present exactly once,
every one `no-benefit`, `no-clear-effect`, `cannot-discriminate` or parked
(`gates.PARKED_CLASSES`: `ceiling`, `ceiling-unconfirmed`, or `paused` for
a fixture the eval scope pass paused), and at least one `no-benefit` or
`no-clear-effect`
(a cell with headroom; harness/gates.py, THE VERDICT). Any field of the
wrong type is a refusal, never a crash or a pass.
compute_gates lets one skill retire per evaluation; two `retire` verdicts
here are refused, never a pick.

THE MODE is the gates file's `retirement_mode` (from evals/gate-policy.yml;
anything but `auto` is `proposal`). Every `retire` verdict's removal is
automatic (Adam, 2026-11-13: "I want removals to occur without requiring my
intervention/approval"; harness/gates.py, THE VERDICT), so the verdict's
`removal` and the cells are no longer re-derived into a proposal. In `auto`
mode a removal that cannot be opened mechanically goes to one of two places
(the removal path's `effective_mode`, as scripts/improve_gate.py lowers an
improvement to a draft):

  * the OWNER, as a `proposal` issue, when removing the skill would wait on
    adam-agentskills' plugin-runtime-review, which auto-merge cannot approve
    (adam-agentskills ADR 0016 and 0021, decision 4: owner approval is a
    standing rule there): improve_gate.py's `auto_refusal`, a skill with its
    own `hooks/` or `bin/` or one a hook of its plugin names a path in;
  * the FLEET WORKER, as an `agent` issue (below), for a reason an agent can
    fix: the skill's one copy is in a public registry other than
    adam-agentskills (cms-platform, adamdaniel.ai), adam-agentskills' mechanical
    path refuses (the skill is its plugin's last, the layout file does not
    list it, a `scripts/skills_waivers.yml` waiver, or a test a tracked source
    elsewhere cites by name), or the caller has no write credential for
    adam-agentskills this run (`--fallback-to-proposal` without `--allow-mode
    auto`: the scheduled workflow passes it when the GitHub App token, or the
    adversarial review's Anthropic bearer (skills-evals#917), was not minted).

A basename found 0 or 2+ times, a copy in adam-agentskills-private (never a
target) or an unsafe path stays a refusal (exit 2); with
`--fallback-to-proposal` an unlocated skill still gets the proposal issue.

  * `proposal`: an issue in skills-evals, found by a marker comment in its
    body (`ISSUE_MARKER`) on an issue `github-actions[bot]` opened, is
    created or its body updated, stamped `PROPOSAL_STAMP`. One issue per
    skill, ever: an open one is updated, and a closed one means the skill is
    already decided, so nothing is filed again. A human removes. An issue
    anyone else wrote is ignored, whatever it quotes.
  * `agent` (`AGENT_STAMP`, `agent_issue_body`): the same one issue per
    skill (same `ISSUE_MARKER`), its body naming the registry
    (`Adam-S-Daniel/<registry>`), the skill's path in it, why the bot could
    not open the pull request, and that the fleet worker removes it with a
    `retire-skill/<skill>` pull request that closes the issue. The label
    `agent-ready` is added through `gh` (REST) unless the issue carries
    `agent-working`, `agent-blocked` or `on-hold`. An open
    proposal-stamped issue that now qualifies is rewritten in place and
    labeled; a closed agent-stamped issue decides the skill, as a closed
    proposal does.
  * `auto` (Adam, 2026-10-25; docs/decisions/0014 and adam-agentskills ADR
    0021): a branch `retire-skill/<skill>` is prepared in the
    adam-agentskills checkout; it is pushed (and the push verified with
    `git merge-base --is-ancestor`), a ready pull request is opened, labeled
    `agent-authored`, reviewed by a fresh-context agent
    (scripts/removal_review.py, skills-evals#917: the section and its
    `Adversarial-review: pass|block <run url>` line are written into the
    body and read back), and only on a pass is auto-merge (merge commit,
    `--match-head-commit`) enabled and read back; a block leaves it open and
    unarmed, and the removal notice says it waits for Adam. No human review,
    so the branch must pass the registry's required checks on its own. Its first commit deletes
    `plugins/<plugin>/skills/<skill>/`, raises the plugin's MAJOR version in
    both manifests (adam-agentskills ADR 0009 requires a raise; removing a
    skill breaks every consumer that calls it, which the registry has bumped
    as major before, `adam-coding-local` 1.1.0 -> 2.0.0 for `sync-skills`),
    adds a `docs/skill-impact.md` entry, drops the skill from
    `scripts/plugin_layout.json` (the ADR 0013
    layout its tests pin) and regenerates the README skill table with the
    registry's own `scripts/generate_readme_table.py`. When `skills.lock`
    locks the plugin, a second commit re-pins it to the first with the
    registry's `scripts/generate_skills_lock.py --repin`, and
    `--check-current` must then pass (the order that script documents:
    content, commit, re-pin, commit). The two registry scripts run with a
    scrubbed environment (no token reaches them), from the checkout's
    default branch, which the registry's own CI already runs. Registry
    writes use the token in `REGISTRY_TOKEN` (the App's), never `GH_TOKEN`
    (this repository's, for the issue path).

`--allow-mode` lists the modes the caller has wired (default: `proposal`
only, the safe one; auto must be named). A gates file in a mode not allowed
exits 2 rather than doing nothing quietly, unless `--fallback-to-proposal`
lowers auto to proposal.

AUTO MODE OPENS NOTHING (exit 0, nothing written) while any loop pull
request is open in adam-agentskills (head `eval-improve/`, `draft-skill/` or
`retire-skill/`; the slot routine-improve-gate.yml's `registry-pr` job
checks): all three write the bundle version, `docs/skill-impact.md` and
`skills.lock`, so a second would conflict once the first merged
(adam-agentskills ADR 0021, decision 5). Nor while a closed pull request
from `retire-skill/<skill>` decides it: one merged, or closed unmerged by a
person, decides the skill, as a closed issue decides a proposal. Nor
while a closed retirement issue the proposal path filed (`PROPOSAL_STAMP`,
or an issue with no stamp, which predates the stamps) stands, whatever
else is open (R8-1): auto mode files that issue too, when a verdict allows
only a proposal or no token reached the run, and a person who closed it
declined the removal; any close does, whatever its reason
(`state_reason` is not read). A closed issue the withdrawal path filed
(`WITHDRAWAL_STAMP`) decides nothing until the pause cap: while auto mode is
lowered to a proposal short of the cap, such an issue does not count as
already decided either, and a fresh proposal issue is filed for a person to
decline (R9-5; in `proposal` mode, or at the cap, any closed issue decides:
the lowered path counts the subject's loop pauses too, R10-3). At the cap
the cap comment is posted once per subject (R11-1): on the open retirement
issue, when none of the subject's issues carries `CAP_MARKER` yet, even
beside a closed issue; from then on a closed issue decides with no comment,
and so does one with no issue open, which gets none. A pass lowered to a
proposal at the cap (a skill's removal is paused three times)
writes the cap note into the issue body it rewrites, and posts the comment
itself when it is still owed (R12-1), so no path erases `CAP_MARKER` and
the comment is posted once whichever pass reaches the cap first.
A proposal issue that is open when a removal opens gets a comment linking it
(`open_proposal_note`): closing the issue still declines that removal, since
the withdrawal pass closes it (R9-1, below), unless a person armed it
strictly after the close (round 13: the latest person action wins); a
removal that has merged is reverted, not declined. One the
loop withdrew (opened by `LOOP_AUTHOR`, labeled `loop-withdrawn` AND closed
by `LOOP_AUTHOR`, read from the issue's `closed_by`) decides nothing: the
withdrawal deleted its branch, so the next removal is a plain push, and a
branch that still exists is refused, never replaced. After
`MAX_LOOP_PAUSES` (3) such pauses the skill's proposal issue is filed or
updated instead of another removal.

REFUSALS (exit 2, nothing written):

  * any run that is not `--dry-run` outside the scheduled workflow
    (`GITHUB_EVENT_NAME` must be `schedule`): never from a dispatch, a pull
    request or a terminal;
  * in auto mode, any run that is not `--dry-run` outside GitHub Actions
    (`GITHUB_ACTIONS` must be `true`) on the default branch (`GITHUB_REF`
    must be `refs/heads/main`);
  * in auto mode, a shallow adam-agentskills checkout (the lock re-pin and
    its check read the commit the lock pins, which a shallow clone lacks) or
    a skill whose removal that registry's `plugin-runtime-review` gate would
    hold for the owner although its plugin runs no code (a `hooks/` or
    `bin/` directory in the skill, or another plugin's hook naming a path
    inside it; the owner's proposal issue is filed instead). A skill that
    is its plugin's last (the lock generator refuses an empty plugin), a
    `scripts/plugin_layout.json` that does not list the skill under its
    plugin, a skill `scripts/skills_waivers.yml` waives a finding under (the
    waiver goes stale with it and `check_skills.py` exits 1), or a skill
    defining a test that a tracked source elsewhere cites by name (the
    registry's citation test would fail on the dangling name) take the
    agent route instead of a refusal (`AgentFixable`);
  * in auto mode, a skill whose basename is not found exactly once across
    every `--registry` checkout given, or whose one copy is not a real
    directory (`plugins/<plugin>/skills/<skill>/` of adam-agentskills, or
    a copy in cms-platform or adamdaniel.ai for the agent route): none of
    `plugins/`, the plugin, its `skills/`, the skill, its manifests or
    `docs/skill-impact.md` may be a symlink or resolve outside the
    checkout.

Only adam-agentskills is ever written by this script. The private registry,
adam-agentskills-private, is never a target (adam-agentskills ADR 0021,
decision 7): the scheduled job does not check it out, so a skill there has
no tested digest and never reaches `retire`, and a `--registry` copy found
anywhere but adam-agentskills is refused in auto mode.

`--dry-run` reads (the gates file, the checkouts, and open pull requests or
issues through `gh`), writes nothing, and prints the plan as JSON: the
action, the issue or pull request text, and the commands it would run.

Every GitHub call goes through one of two functions, `gh(args, stdin)` (the
`gh` CLI with `GH_TOKEN`: reads, and skills-evals issues) and
`registry_gh(args, stdin)` (with `REGISTRY_TOKEN`: adam-agentskills
writes), and every push through `push(checkout, branch)`, all injectable,
so tests need no network. An error from `gh` is reported by its exit code
only, never its output. Deterministic: no clock; the skill-impact date is
`--date` (the workflow passes the run's UTC date), else the gates file's
`as_of`.

`--usage` is the published `usage/weekly-local.json`; the issue body names
the skill's invocations over the four weeks ending at the gates file's
`as_of` (harness/skill_usage.weight), or says `unknown` when there is no
fresh census. For a `retire` verdict it informs the human and changes no
decision; the `unused` reason (below) is decided from it.

THE `unused` REASON (Adam, 2026-11-12). With no skill at a `retire` verdict (a
`retire` verdict always has priority: at most one removal per run), a skill
nobody uses is removed once the context its description cost passes the value
of one use. `evals/removal-policy.yml` holds the numbers and
`harness/removal_policy.py` the rule (`unused_removal`): not exempt
(`evals/usage-unknown.yml`), reaching the cloud surface (a local-only skill is
never removed on usage), zero uses over the policy's `floor_weeks`, every
surface it reaches counted back to the floor's start, and sessions x d x R / P
summed over the surfaces at least V. Candidates are the skills of
adam-agentskills' `scripts/plugin_layout.json` (surfaces as
`eval_scope._surfaces`, d from the skill's SKILL.md), ranked by accrued cost,
then name; a candidate refused by the checks below, or already decided by a
closed pull request, a declining issue, a held issue or the pause cap, gives
way to the next. The chosen one goes through the same `plan` tail as a
`retire` verdict (loop slot, closed-pull-request, declined, held, runtime-gate
and registry refusals, adversarial review, auto-merge), in `auto` mode with
`auto` allowed only: the reason is never lowered to an issue, so proposal
mode, no credential or no `--usage` opens nothing (exit 0). Its pull request
body starts "Removes `<path>`: it is **unused** as of <as_of> (" (the basis
line `BASIS_RE` reads), states the figures and gives the restore command,
`python3 scripts/restore_skill.py <skill>`; the skill-impact entry and title
say `unused`. `--withdraw-stale --usage` judges such a pull request by use,
not by a verdict (`unused_checker`): kept while the skill stays unused,
withdrawn once it is used in the floor window or exempt, kept when the census
is missing or stale.

The gate guards against honest mistakes, not forged results (Adam,
2026-10-26): anyone who can write the results can also remove a skill.

GUIDANCE SECTIONS (`--target guidance`, skills-evals#124; the functions
named `guidance_*` below, kept apart from the skill path). The gates file's
`guidance` block and `guidance_retirement_mode` decide, read the same way:

  * a `retire` verdict, re-checked as a skill's is, and its section-alone
    pair too (`guidance_proposal_only`: an alone pair with no cell, or with
    a cell that has not decided files nothing and removes nothing, 2026-11-13:
    the evidence is incomplete and the scheduler runs the alone arm; the
    gates report such a section `insufficient`): in `proposal` mode an
    issue in skills-evals (`GUIDANCE_ISSUE_MARKER`); in `auto` mode (Adam:
    removal is automatic, 2026-10-10, and its pull requests auto-merge,
    2026-10-25) a branch `retire-guidance/<section>` in the
    `--guidance PATH` checkout of _agent-guidance that removes the
    section's extent from its file (the whole file for a sections/*.md file
    with no other `##`; for base.md, re-copied to the repository's own
    `.claude/hooks/fleet-guidance.md` payload), deletes its
    `agents-md/eval-coverage.yml` row,
    rewrites the manifest's bytes (`check-guidance-coverage.js
    --write-bytes`), adds a typed `remove` entry to
    `docs/guidance-impact.md` whose `Eval:` line names the fixtures, the
    pooled run count (`n=`) and the policy, and regenerates `AGENTS.md`
    exactly as that repository's own instructions say: managed output with
    its trailing newlines stripped, then everything from the `## Repo-
    specific additions` heading LINE (never the first occurrence of the
    substring, which the managed header quotes); pushed, opened, labeled
    `agent-authored` and armed to auto-merge (merge commit, matched to the
    removal head, read back), one at a time (`retire-guidance/` heads),
    and then a removal notice filed here (#557: an `agent-authored` issue,
    `GUIDANCE_NOTICE_MARKER`, that mentions Adam, links the removal pull
    request and says how to reverse it: close it, or press Revert once it
    has merged). The explorer lists every removed section from the impact
    file's `remove` entries (scripts/explorer_data.py `removed_sections`).
    These writes to _agent-guidance go through `registry_gh` and the push
    with `REGISTRY_TOKEN`, as the skill path's do; the issues stay on `gh`.
    With `--fallback-to-proposal`, `auto` mode without `auto` allowed (no
    token reached the run) files nothing (an infrastructure failure is not
    the owner's decision, 2026-11-13) and exits 1 with a fixed message, so
    the scheduled-run health audit flags the run;
  * a `shorten-or-merge` verdict (the section helps only alone): an issue in
    skills-evals (`SHORTEN_ISSUE_MARKER`) in either mode, never a removal.

One action per evaluation: a `retire` first, else the first
`shorten-or-merge` section by name. As a closed `retire-skill/<skill>` pull
request decides a skill, a closed `retire-guidance/<section>` one decides a
section: no removal is opened for it again, unless the loop withdrew it
(`loop-withdrawn`), as for skills.

WITHDRAWAL (`--withdraw-stale`, with or without `--target guidance`; ADR
0014, the known limit round 8 recorded). It runs before each scheduled pass
and after every ingest (loop-pr-refresh.yml's `withdraw` job, ahead of its
refresh). It lists the target repository's open pull requests and, for
each the loop opened (head `retire-skill/` or `retire-guidance/`, the
`agent-authored` label, and `LOOP_AUTHOR` as author) that is not labeled
`on-hold`, re-reads its subject's verdict (`removal_support`). A verdict
that no longer supports an automatic removal (not `retire`, or a `retire`
lowered to a proposal; a `retire-pending` whose `raw_verdict` is `retire`
still supports it, since `finalize` only ranks it behind another subject)
withdraws it, in this order:

  1. auto-merge is turned off and read back;
  2. the label `loop-withdrawn` is added and read back;
  3. the subject's retirement issue here (the proposal path's marker) is
     filed, stamped `WITHDRAWAL_STAMP`, or the oldest open one gets a
     comment (its body, and any `PROPOSAL_STAMP` in it, is kept);
  4. a comment gives the new verdict, why and the override;
  5. the pull request is closed, and who closed it is read back (R7-1):
     `gh pr close` exits 0 on one someone else closed first, so a closer
     other than `LOOP_AUTHOR` (or none GitHub records) decides the subject,
     a correction (`DECIDED_MARKER`) is posted on the pull request and the
     retirement issue, and the branch is kept, as it is when the closer
     cannot be read;
  6. only after the loop's own close, its branch is deleted, leased on the
     closed pull request's head, so a commit pushed since keeps it (best
     effort: a failure is named by its error's type and the pause stands,
     and the next removal's push retries the delete when the branch still
     points at a paused removal's head, R7-2);
  7. any open removal notice (#557) for the subject is closed as not
     planned and then commented on, best effort.

DECLINE (R9-1). Before any of that, each open loop removal's subject has its
retirement issues read (`declined_decision`): when `declined` finds a closed
proposal issue (proposal-stamped, or legacy), a person declined the removal
while it was open, which the retirement job never reads while a loop pull
request is open. That pull request is a `decline`, whatever its verdict and
in either mode (a `keep`, a `disarm` and a `withdraw` alike): auto-merge is
turned off and read back, `loop-withdrawn` is taken off if a withdrawal that
stopped part way left it on, and read back (R10-1; a label that stays on
fails the item and the pull request is left open), a comment
(`DECLINED_MARKER`) cites the closed issue, and the pull request is closed
as a decision, with no `loop-withdrawn` label, so the closed removal decides
the subject: no removal is opened for it again, even if the issue is
reopened, and its branch is kept, since no later removal pushes to it. No
new retirement issue is filed (one saying that closing it declines nothing
would be wrong); then, best effort, the closed issue gets a comment and
stays closed, and any open removal notice is closed as in step 7. An
unreadable issue list fails that pull request's item (exit 2) and writes
nothing to it. A removal under a person's arm (below) made strictly after
the issue's close is not declined.

A PERSON'S ARM IN FORCE (round 12, `persons_arm`): the one exception to
every action above and below. A removal pull request that is armed for
auto-merge now, and whose latest `auto_merge_enabled` timeline event (by
`created_at`) is a person's, belongs to that person. A person is a
`User` account other than `LOOP_AUTHOR` and `GHOST` (round 13): a `Bot`
(any App or bot, github-actions[bot] included), a deleted account, or an
actor with no type or no login is not. The loop does not disarm it (the
`proposal` switch), withdraw it (a stale verdict) or finish it as a
stopped withdrawal; it logs `left #N for a person: armed by a person`, and
`refresh_allowed` lets loop-pr-refresh.yml bring it up to date, so it can
still merge. To stop it, a person turns its auto-merge off or closes it.
For those actions, nothing is compared with when the loop last disarmed:
who armed it, and that it is armed now, decide. The one comparison (round
13, the latest person action wins) is with a decline: when a closed
proposal or legacy issue declines the subject, the arm wins only when its
`created_at` is strictly later than the issue's `closed_at` (the latest
close, when several decline); a tie, or a time missing or unparseable on
either side, and the removal is declined. A removal that is not armed (the
loop's own disarm included), one a non-person armed last, an unreadable
timeline, no event, or a time missing or unparseable on any
`auto_merge_enabled` event is not a person's arm in force, and gets the
action above or below, so unknown data still leans toward disarming or
declining.

A failure at steps 1 to 5 leaves the pull request open for the next pass.
In `auto` mode an open removal whose verdict still supports it but which
carries `loop-withdrawn` is such a withdrawal that stopped part way, and is
finished the same way (R6-2). So is one whose auto-merge the listing shows
off (one opened before the verdicts' results), but only when its timeline
says the loop turned it off (R7-3, `loop_disarm_hold`): the latest
`auto_merge_disabled` event is `LOOP_AUTHOR`'s and no `DISARMED_MARKER`
comment of the loop's follows it (R8-2), read by `created_at`, a
same-second marker counting as following it (R9-2). A person's disarm is
a hold, and so is the proposal switch's, which comments that marker after
it disarms; if that comment failed, the next `proposal` pass that finds the loop's
disarm with no marker after it posts it (R8-3). The gap left: if the mode
is switched to `auto` before any `proposal` pass posts it, the removal is
finished as a pause. A loop withdrawal is a
pause, not a decision: a closed removal the loop opened, labeled and
closed itself decides nothing, so once the verdict supports an automatic
removal again the retirement job opens a fresh one; a person who removes
the label, or closes a removal themselves, decides the subject.

Only verdicts newer than the results a pull request was opened on judge
it: its body's first line, "Removes ... is
**retire** as of <as_of> (", names them (a basis later than its own
`created_at` is ignored); with none, one whose `created_at` is later than
the document's `as_of`, or with either time unknown, is kept. The override
is a person's: remove `agent-authored`, restore the branch from the pull
request page, then reopen and merge by hand; a pull request without the
label is not the loop's. While the target's mode is
`proposal` (the one switch), a removal still supported is only disarmed,
left open and commented once, unless a person's arm is in force (above).
Unknown data never withdraws: a missing or
unreadable gates document (or no guidance block) withdraws nothing and
exits 0 with a status naming no subject, and a subject the document does
not list, whose verdict raised in compute_gates.py (`VERDICT_RAISED`) or
whose `retire` fails the re-check is kept. `withdrawal_decision` is the
pure decision; the pull request writes go through `registry_gh` (the App
token in `REGISTRY_TOKEN`) and the issues through `gh`, in GitHub Actions on
main only, and a missing token with something to withdraw exits 2. One
pull request's failure does not stop the others: every status line is
printed and the pass exits 2 at the end.
`refresh_allowed` is the same verdict read for loop-pr-refresh.yml, which
brings a removal up to date only while it would still be kept, and only
while no closed proposal issue declines it (R10-4: an unreadable issue list
refreshes nothing), so a decline the withdrawal pass could not finish is
not merged by a refresh. Given the pull request's number
(`removal-check --number`), it also refreshes one under a person's arm in
force, whatever its verdict or mode, since the withdrawal pass leaves that
one to the person (round 12), unless a closed proposal issue declines it
and the arm is not strictly later than that close, or the issue list
cannot be read (round 13).
"""

from __future__ import annotations

import argparse
import ast
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

import compute_gates  # noqa: E402
import gates  # noqa: E402
import guidance_merge_window  # noqa: E402
import delivery  # noqa: E402
import guidance  # noqa: E402
import skill_usage  # noqa: E402
import removal_policy  # noqa: E402
import eval_scope  # noqa: E402
import improve_gate  # noqa: E402
import removal_review  # noqa: E402
import loop_door_check  # noqa: E402

TARGET = "adam-agentskills"
REGISTRY_REPO = "Adam-S-Daniel/adam-agentskills"
EVALS_REPO = "Adam-S-Daniel/skills-evals"
BRANCH_PREFIX = "retire-skill/"
#: Every loop pull request's head in adam-agentskills: improvement, new
#: skill, removal. One open at a time across all three (ADR 0021,
#: decision 5; routine-improve-gate.yml's registry-pr job checks the same).
LOOP_PREFIXES = ("eval-improve/", "draft-skill/", BRANCH_PREFIX)
#: The fleet label and marker for a contribution an agent made on Adam's
#: behalf (_agent-guidance ADR 0023), as the improvement gate writes them.
AGENT_LABEL = "agent-authored"
AGENT_MARKER = improve_gate.AGENT_MARKER
AGENT_TRAILER = "Agent: claude-code"
REGISTRY_ADR = improve_gate.REGISTRY_ADR
#: The environment variable holding the adam-agentskills write token (the
#: skills-evals GitHub App's installation token, minted by the workflow).
REGISTRY_TOKEN_ENV = "REGISTRY_TOKEN"
PR_URL_RE = re.compile(rf"https://github\.com/{re.escape(REGISTRY_REPO)}/pull/(\d+)")
#: What a guidance run with no credential prints and fails with: fixed, and
#: naming no identity.
GUIDANCE_NO_CREDENTIAL_FAILURE = ("no credential for the guidance removal reached this run, "
                                  "so nothing was filed or removed; the run fails so the "
                                  "scheduled-run health audit flags it")
#: The cell classes a `retire` verdict may hold, and those with headroom,
#: of which it needs one (harness/gates.py, THE VERDICT).
RETIRE_CELL_CLASSES = ("no-benefit", "no-clear-effect", "cannot-discriminate",
                       *sorted(gates.PARKED_CLASSES))
HEADROOM_CLASSES = ("no-benefit", "no-clear-effect")
NO_CREDENTIAL = ("no write credential for adam-agentskills, or no credential for the "
                 "adversarial review, reached this run (a token was not minted)")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ISSUE_MARKER = "<!-- skills-evals:retire-skill:{skill} -->"
#: Which path filed a retirement issue (R8-1), stamped in its body beside
#: the subject's marker when it is created (or, for the proposal path,
#: rewritten): the proposal path (`_issue_body`, `guidance_issue_action`)
#: or the withdrawal path (`withdrawal_issue`). In `auto` mode a closed
#: issue the proposal path filed declines the removal; one the withdrawal
#: path filed declines nothing until the pause cap. An issue with neither
#: stamp predates them and is read as a proposal (`issue_origin`).
PROPOSAL_STAMP = "<!-- skills-evals:retirement-issue:proposal -->"
WITHDRAWAL_STAMP = "<!-- skills-evals:retirement-issue:withdrawal -->"
#: The third path (Adam, 2026-11-13: removals happen without his approval): an
#: issue an agent acts on, for a removal the bot cannot open mechanically
#: (`agent_issue_body`). A closed one decides the skill like a closed proposal.
AGENT_STAMP = "<!-- skills-evals:retirement-issue:agent -->"
#: The label that hands the issue to the fleet worker, unless the issue
#: already carries one of AGENT_BLOCKING_LABELS (a worker is on it, it is
#: stuck, or the owner paused it).
AGENT_READY_LABEL = "agent-ready"
AGENT_BLOCKING_LABELS = ("agent-working", "agent-blocked", "on-hold")
#: Public registries other than adam-agentskills whose skills the agent route
#: may name. adam-agentskills-private is never one (ADR 0021, decision 7).
AGENT_REGISTRIES = ("Adam-S-Daniel/cms-platform", "Adam-S-Daniel/adamdaniel.ai")
AGENT_WORKER_DOC = ("Adam-S-Daniel/_agent-guidance docs/reference/agent-issue-worker.md, "
                    '"Skill removal issues"')
IMPACT_FILE = "docs/skill-impact.md"
#: Who a removal notice mentions, so GitHub notifies him (#557).
NOTICE_OWNER = "Adam-S-Daniel"
LAYOUT_FILE = "scripts/plugin_layout.json"
README_FILE = "README.md"
LOCK_FILE = "skills.lock"
README_GENERATOR = "scripts/generate_readme_table.py"
LOCK_GENERATOR = "scripts/generate_skills_lock.py"
WAIVERS_FILE = "scripts/skills_waivers.yml"
#: adam-agentskills' append-only ledger of every shipped name, which its
#: one-way-door check reads (adam-agentskills#133).
SHIPPED_LEDGER = "scripts/shipped_names.json"
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json")
ADR = ("https://github.com/Adam-S-Daniel/skills-evals/blob/main/docs/decisions/"
       "0014-removal-pull-requests-merge-without-review.md")
COMMIT_NAME = "github-actions[bot]"
ISSUE_AUTHOR = "github-actions[bot]"
DEFAULT_REF = "refs/heads/main"
COMMIT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
SKILL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
# A fixture directory or a roster model id: no space, `|` or newline, so a
# value can never break the evidence table or mention anyone.
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@\[\]/-]{0,127}$")


class RetireError(Exception):
    """A refusal: nothing is written."""


def default_gh(args: list, stdin: str | None = None, token: str | None = None) -> str:
    """Run `gh` and return its stdout; its output is never echoed on failure,
    since an API error body can carry data a public log must not. `token`,
    when given, replaces GH_TOKEN for this call only."""
    env = {**os.environ, "GH_TOKEN": token} if token else None
    proc = subprocess.run(["gh", *args], input=stdin, capture_output=True,
                          text=True, check=False, env=env)
    if proc.returncode != 0:
        raise RetireError(f"gh {args[0]} exited {proc.returncode}")
    return proc.stdout


def _auth_env(token: str) -> dict:
    """git's environment with `token` as an HTTP header for github.com, set
    through GIT_CONFIG_* so it never appears in an argv or .git/config."""
    header = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return {**os.environ, "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {header}",
            "GIT_TERMINAL_PROMPT": "0"}


def branch_exists(checkout: Path, branch: str, env=None, remote: str = "origin") -> str:
    """`branch`'s tip on `remote` (the checkout's origin by default; a URL
    works too) as `git ls-remote` gives it, or "" when the branch does not
    exist; RetireError when it cannot be read."""
    proc = subprocess.run(["git", "-C", str(checkout), "ls-remote", remote,
                           f"refs/heads/{branch}"], capture_output=True, text=True,
                          check=False, env=env)
    if proc.returncode != 0:
        raise RetireError(f"git ls-remote exited {proc.returncode}")
    fields = proc.stdout.split()
    return fields[0] if fields else ""


def default_push(checkout: Path, branch: str, token: str | None = None,
                 paused_heads=()) -> None:
    """Push HEAD to a new `branch`, then prove it landed: a refused commit can
    still leave `git push` reporting success, so the pushed ref is fetched
    back and HEAD must be its ancestor (the fleet's push rule). A branch
    that already exists is RetireError, never replaced (PR #740 round 6's
    R6-5), with one exception (round 7's R7-2): a branch whose tip is one of
    `paused_heads`, the head commits of the closed removals the loop paused
    (the caller passes them only when every closed removal from this branch
    is such a pause), is what a withdrawal's failed delete left behind. Its
    delete is retried, leased on that tip as the withdrawal leases it, and
    then the push is plain. Any other branch is a person's to restore or
    delete, and nothing here ever forces a push over a commit."""
    if not token:
        raise RetireError(f"no {REGISTRY_TOKEN_ENV} to push with")
    env = _auth_env(token)
    tip = branch_exists(checkout, branch, env)
    if tip and tip in paused_heads:
        url = _git(checkout, "remote", "get-url", "origin").strip()
        default_delete_branch("", branch, tip, token, url=url)
        tip = branch_exists(checkout, branch, env)
    if tip:
        raise RetireError(f"{branch} already exists, so a removal is not pushed over it; "
                          "a person restores its pull request or deletes the branch")
    for args in (["push", "origin", f"HEAD:refs/heads/{branch}"],
                 ["fetch", "-q", "--no-tags", "origin",
                  f"+refs/heads/{branch}:refs/remotes/origin/{branch}"],
                 ["merge-base", "--is-ancestor", "HEAD", f"refs/remotes/origin/{branch}"]):
        proc = subprocess.run(["git", "-C", str(checkout), *args], capture_output=True,
                              text=True, check=False, env=env)
        if proc.returncode != 0:
            raise RetireError(f"git {args[0]} exited {proc.returncode}"
                              + (": the pushed branch does not hold the removal commit"
                                 if args[0] == "merge-base" else ""))


def default_delete_branch(repo: str, branch: str, sha: str, token: str | None = None,
                          url: str | None = None) -> None:
    """Delete a withdrawn removal's `branch` (R6-5, R6-11) only while it
    still points at `sha`, the closed pull request's head: `git push
    --force-with-lease=refs/heads/<branch>:<sha> <url> :refs/heads/<branch>`
    from an empty repository. The server applies the delete only if the ref
    still holds `sha` (receive-pack checks the old value under its ref
    lock), so a commit anyone pushed since keeps the branch. `url` defaults
    to the repository on github.com, authenticated with `token` through
    `_auth_env`. A refused delete whose branch is gone (a person or an
    earlier pass deleted it: "remote ref does not exist", R7-2) counts as
    deleted; whether it is gone is read with `git ls-remote`, not from the
    error text."""
    if not token:
        raise RetireError(f"no {REGISTRY_TOKEN_ENV} to delete a branch with")
    if not SHA_RE.fullmatch(sha or ""):
        raise RetireError("the closed pull request's head is not a commit sha")
    env = _auth_env(token)
    with tempfile.TemporaryDirectory(prefix="trusted-git-") as tmp:
        for args in (["init", "-q", tmp],
                     ["-C", tmp, "push", f"--force-with-lease=refs/heads/{branch}:{sha}",
                      url or f"https://github.com/{repo}.git", f":refs/heads/{branch}"]):
            proc = subprocess.run(["git", *args], capture_output=True, text=True,
                                  check=False, env=env)
            if proc.returncode != 0 and args[0] == "-C" \
                    and not branch_exists(Path(tmp), branch, env, args[-2]):
                return
            if proc.returncode != 0:
                raise RetireError(f"git {args[0] if args[0] != '-C' else args[2]} exited "
                                  f"{proc.returncode}")


def _git(checkout: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(checkout), *args],
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RetireError(f"git {args[0]} exited {proc.returncode}")
    return proc.stdout


def check_event(env, events=("schedule",)) -> None:
    """Only the named events write: the schedule acts on a verdict, and
    withdrawal (`WITHDRAW_EVENTS`) also runs after every ingest."""
    if env.get("GITHUB_EVENT_NAME") not in events:
        raise RetireError("refusing: only the scheduled workflow acts on a retire "
                          f"verdict (GITHUB_EVENT_NAME is {env.get('GITHUB_EVENT_NAME')!r})")


def check_auto_env(env) -> None:
    if env.get("GITHUB_ACTIONS") != "true" or env.get("GITHUB_REF") != DEFAULT_REF:
        raise RetireError("refusing: auto mode acts only in GitHub Actions on "
                          f"{DEFAULT_REF} (GITHUB_ACTIONS is "
                          f"{env.get('GITHUB_ACTIONS')!r}, GITHUB_REF is "
                          f"{env.get('GITHUB_REF')!r})")


def _names(value) -> bool:
    """A non-empty list of distinct NAME_RE strings."""
    return (isinstance(value, list) and bool(value)
            and all(isinstance(v, str) and NAME_RE.fullmatch(v) for v in value)
            and len(set(value)) == len(value))


def load_gates(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise RetireError(f"cannot read the gates file ({type(exc).__name__})") from None
    if not isinstance(doc, dict) or doc.get("schema_version") != 1 \
            or not isinstance(doc.get("skills"), dict) \
            or not _names(doc.get("roster_models")) \
            or not isinstance(doc.get("as_of"), str) \
            or not re.fullmatch(r"\d{8}T\d{6}Z", doc["as_of"]):
        raise RetireError("the gates file is not compute_gates.py schema 1")
    return doc


def mode_of(gates: dict) -> str:
    return "auto" if gates.get("retirement_mode") == "auto" else "proposal"


def retiring(gates: dict) -> str | None:
    """The one skill whose verdict is `retire`, re-checked; None when none.
    RetireError for two, or for a `retire` the cells do not support."""
    names = sorted(n for n, v in gates["skills"].items()
                   if isinstance(v, dict) and v.get("verdict") == "retire")
    if not names:
        return None
    if len(names) > 1:
        raise RetireError(f"{len(names)} skills have a retire verdict; compute_gates "
                          "allows one per evaluation")
    skill, verdict = names[0], gates["skills"][names[0]]
    if not SKILL_RE.fullmatch(skill):
        raise RetireError("the retiring skill's name is not a skill basename")
    if not isinstance(verdict.get("reason"), str):
        raise RetireError(f"{skill}: a retire verdict whose reason is not text")
    cells = verdict.get("cells")
    roster = gates["roster_models"]
    if not isinstance(cells, list) or not cells or not _names(roster):
        raise RetireError(f"{skill}: a retire verdict with no cell")
    for c in cells:
        if not isinstance(c, dict) or c.get("class") not in RETIRE_CELL_CLASSES:
            raise RetireError(f"{skill}: a retire verdict with a cell that is not "
                              f"{', '.join(RETIRE_CELL_CLASSES)}")
        fixture = c.get("fixture")
        if not (fixture is None or isinstance(fixture, str) and NAME_RE.fullmatch(fixture)) \
                or not isinstance(c.get("model"), str):
            raise RetireError(f"{skill}: a retire verdict with a malformed cell")
    if not any(c["class"] in HEADROOM_CLASSES for c in cells):
        raise RetireError(f"{skill}: a retire verdict with no cell with headroom")
    pairs = [(c["fixture"], c["model"]) for c in cells]
    fixtures = {f for f, _ in pairs}
    want = {(f, m) for f in fixtures for m in roster}
    if len(set(pairs)) != len(pairs) or set(pairs) != want:
        raise RetireError(f"{skill}: the retire verdict's cells are not each fixture "
                          "crossed with each roster model exactly once (the cross product)")
    return skill


def locate(registries: dict, skill: str) -> dict:
    """{"plugin", "path"} of the one copy of `skill`, in adam-agentskills;
    RetireError otherwise."""
    if TARGET not in registries:
        raise RetireError(f"no {TARGET} checkout was given (--registry {TARGET}=PATH)")
    try:
        matches = delivery._registry_matches(registries, None, skill)
    except delivery.DeliveryError:
        raise RetireError(f"{skill}: a copy escapes its checkout") from None
    root = Path(registries[TARGET]["path"])
    dirs = sorted(p for p in root.glob(f"plugins/*/skills/{skill}") if p.exists()
                  or p.is_symlink())
    if len(matches) != 1 or len(dirs) != 1:
        raise RetireError(f"{skill}: basename found {len(matches)} time(s) across the "
                          f"registries given, not exactly once")
    identity, plugin, directory = matches[0]
    if directory != dirs[0] or not directory.is_relative_to(root):
        raise RetireError(f"{skill}: its one copy is not in {TARGET}")
    if directory.is_symlink():
        raise RetireError(f"{skill}: its copy is a symlink")
    if not directory.is_dir():
        raise RetireError(f"{skill}: its copy is not a real directory")
    rel = directory.relative_to(root).as_posix()
    if rel != f"plugins/{plugin}/skills/{skill}":
        raise RetireError(f"{skill}: unexpected location {rel}")
    contained(root, ["plugins", f"plugins/{plugin}", f"plugins/{plugin}/skills", rel])
    return {"plugin": plugin, "path": rel}


class AgentFixable(RetireError):
    """A refusal the bot cannot clear mechanically but an agent can (the
    agent route files an `agent-ready` issue instead of exiting 2)."""


def locate_anywhere(registries: dict, skill: str) -> dict:
    """`locate`'s answer for a skill in adam-agentskills, with `registry`
    (`REGISTRY_REPO`); or {"plugin", "path", "registry"} of its one copy in
    another PUBLIC registry (AGENT_REGISTRIES), which the bot never writes.
    RetireError for a basename found 0 or 2+ times, a copy in any other
    registry (adam-agentskills-private is never a target), or an unsafe path."""
    if TARGET not in registries:
        raise RetireError(f"no {TARGET} checkout was given (--registry {TARGET}=PATH)")
    try:
        matches = delivery._registry_matches(registries, None, skill)
    except delivery.DeliveryError:
        raise RetireError(f"{skill}: a copy escapes its checkout") from None
    if len(matches) == 1 and matches[0][0] != REGISTRY_REPO:
        identity, plugin, directory = matches[0]
        if identity not in AGENT_REGISTRIES:
            raise RetireError(f"{skill}: its one copy is in {identity}, which is not a "
                              f"registry a removal may name")
        roots = [Path(e["path"]) for e in registries.values()
                 if directory.is_relative_to(Path(e["path"]))]
        if len(roots) != 1:
            raise RetireError(f"{skill}: its copy is in no single checkout")
        root = roots[0]
        rel = directory.relative_to(root)
        contained(root, ["/".join(rel.parts[:i]) for i in range(1, len(rel.parts) + 1)])
        if not directory.is_dir():
            raise RetireError(f"{skill}: its copy is not a real directory")
        return {"plugin": plugin, "path": rel.as_posix(), "registry": identity}
    return {**locate(registries, skill), "registry": REGISTRY_REPO}


def contained(root: Path, rels) -> None:
    """RetireError unless each of `rels` under `root` is no symlink and
    resolves inside `root`, so no write follows a link out of the checkout."""
    base = root.resolve()
    for rel in rels:
        path = root / rel
        if path.is_symlink() or not path.resolve().is_relative_to(base):
            raise RetireError(f"{rel} is a symlink or resolves outside the {TARGET} "
                              "checkout")


def _json_lines(text: str) -> list:
    out = []
    for line in text.splitlines():
        if line.strip():
            item = json.loads(line)
            if isinstance(item, dict):
                out.append(item)
    return out


def open_loop_prs(gh) -> list:
    """Open adam-agentskills pull requests whose head is any loop's."""
    text = gh(["api", "--paginate",
               f"repos/{REGISTRY_REPO}/pulls?state=open&per_page=100",
               "--jq", ".[] | {number: .number, head: .head.ref, url: .html_url}"])
    return [p for p in _json_lines(text)
            if isinstance(p.get("head"), str) and p["head"].startswith(LOOP_PREFIXES)]


#: The label a withdrawal puts on a removal pull request before it closes it
#: (ADR 0014): a closed removal carrying it, opened by LOOP_AUTHOR, was
#: paused by the loop, not declined by a person, so it decides nothing.
WITHDRAWN_LABEL = "loop-withdrawn"
#: How a pass creates WITHDRAWN_LABEL in a repository that lacks it (`gh label
#: create --force`, through the App token: pull-requests: write may create a
#: label, POST /repos/{owner}/{repo}/labels). GitHub caps a description at 100
#: characters.
WITHDRAWN_LABEL_COLOR = "BFD4F2"
WITHDRAWN_LABEL_DESCRIPTION = ("Eval loop closed this removal PR because the verdict moved; it "
                               "may open a fresh one")
#: The closed listing's fields: who opened it, its labels, whether it
#: merged and its head commit (`sha`, which a reopen's retried delete is
#: leased on, R7-2). Who closed it is not in the listing; `with_closer`
#: reads it.
CLOSED_JQ = (".[] | {number: .number, head: .head.ref, url: .html_url, "
             "labels: [.labels[].name], author: .user.login, "
             "merged: (.merged_at != null), sha: .head.sha}")
SHA_RE = re.compile(r"[0-9a-f]{40}")
#: How many loop-paused removals a subject may have before the retirement
#: job stops opening removals for it and files (or updates) its proposal
#: issue instead, so a verdict near its threshold cannot open and withdraw
#: removal pull requests without bound (PR #740 round 6's R6-6).
MAX_LOOP_PAUSES = 3


def loop_withdrawn(pr: dict) -> bool:
    """A closed, unmerged removal the loop withdrew: LOOP_AUTHOR opened it,
    it carries WITHDRAWN_LABEL, AND LOOP_AUTHOR closed it (`closed_by`,
    which `with_closer` reads from the issue; R6-1, R6-3). It decides
    nothing. Anything else closed decides its subject: merged, closed by a
    person (labeled or not), one whose closer is unknown, or one whose
    label a person removed (the conservative reading)."""
    labels = pr.get("labels")
    return pr.get("merged") is False and pr.get("author") == LOOP_AUTHOR \
        and isinstance(labels, list) and WITHDRAWN_LABEL in labels \
        and pr.get("closed_by") == LOOP_AUTHOR


def deciding(closed: list) -> tuple:
    """(the closed pull requests that decide the subject, those the loop
    paused)."""
    decided, paused = [], []
    for p in closed:
        (paused if loop_withdrawn(p) else decided).append(p)
    return decided, paused


def read_closer(gh, repo: str, n: int) -> str | None:
    """Who closed issue or pull request `n` (`GET repos/{repo}/issues/{n}`'s
    `closed_by` login): "" when GitHub records no closer, None when it
    cannot be read."""
    try:
        return gh(["api", f"repos/{repo}/issues/{n}", "--jq",
                   '.closed_by.login // ""']).strip()
    except Exception:  # noqa: BLE001 - unknown closer
        return None


def with_closer(gh, repo: str, closed: list) -> list:
    """`closed` with each record's `closed_by` login, read from `GET
    repos/{repo}/issues/{n}` for the records that could be a loop pause (the
    listing does not carry it). An unreadable one, or one GitHub records no
    closer for (a null `closed_by`, R7-6), is None, which decides."""
    for p in closed:
        p["closed_by"] = None
        n = p.get("number")
        if p.get("merged") is not False or p.get("author") != LOOP_AUTHOR \
                or type(n) is not int:
            continue
        p["closed_by"] = read_closer(gh, repo, n) or None
    return closed


def closed_removal_prs(gh, skill: str) -> list:
    """Closed adam-agentskills pull requests from `retire-skill/<skill>`,
    with the fields `deciding` reads."""
    owner = REGISTRY_REPO.split("/")[0]
    text = gh(["api", "--paginate",
               f"repos/{REGISTRY_REPO}/pulls?state=closed&per_page=100"
               f"&head={owner}:{BRANCH_PREFIX}{skill}",
               "--jq", CLOSED_JQ])
    return with_closer(gh, REGISTRY_REPO, [
        p for p in _json_lines(text) if p.get("head") == f"{BRANCH_PREFIX}{skill}"])


def runtime_refusal(checkout: Path, plugin: str, skill: str) -> str | None:
    """improve_gate.py's `auto_refusal`: why removing `skill` would wait on
    plugin-runtime-review, or None."""
    try:
        return improve_gate.auto_refusal(checkout, plugin, skill)
    except improve_gate.Rejected as exc:
        raise RetireError(str(exc)) from None


def issue_origin(body: str) -> str:
    """Which path filed a retirement issue, from its body's stamp (R8-1):
    "proposal", "agent", "withdrawal", or "legacy" for one with neither stamp, which
    predates them. A legacy issue counts as a proposal: before the stamps
    the committed mode was `proposal`, in which closing the issue declined,
    so reading it as declined keeps that meaning, and the error it risks is
    a removal not opened (a person can still remove by hand), never one
    opened against a person's decline."""
    if AGENT_STAMP in body:
        return "agent"
    if PROPOSAL_STAMP in body:
        return "proposal"
    if WITHDRAWAL_STAMP in body:
        return "withdrawal"
    return "legacy"


def existing_issues(gh, skill: str) -> dict:
    """{"open": [...], "closed": [...], "proposals": [...], "capped": [...]}: the numbers,
    ascending, of every issue, in any state, that github-actions[bot] opened
    with this skill's marker, and of those the ones the withdrawal path did
    not file (`issue_origin`). An issue anyone else opened is ignored,
    whatever it quotes."""
    return guidance_issues(gh, ISSUE_MARKER.format(skill=skill))


def _figure(block, field):
    if not isinstance(block, dict) or not isinstance(block.get(field), (int, float)):
        return "n/a"
    return f"{block[field]:.3f}"


def evidence(gates: dict, skill: str) -> str:
    """A Markdown table of the verdict's cells."""
    rows = ["| Fixture | Model | Runs with | Runs without | Objective upper | "
            "Judge upper |", "|---|---|---|---|---|---|"]
    for cell in gates["skills"][skill]["cells"]:
        arms = [cell.get(a) if isinstance(cell.get(a), dict) else {}
                for a in ("with", "without")]
        rows.append(f"| {cell.get('fixture') or '(flat)'} | {cell.get('model')} | "
                    f"{arms[0].get('runs', 'n/a')} | {arms[1].get('runs', 'n/a')} | "
                    f"{_figure(cell.get('objective'), 'retire_upper')} | "
                    f"{_figure(cell.get('judge'), 'retire_upper')} |")
    return "\n".join(rows)


def _date(as_of: str) -> str:
    return f"{as_of[0:4]}-{as_of[4:6]}-{as_of[6:8]}"


def _runs(cells) -> int:
    return sum(c[arm]["runs"] for c in cells for arm in ("with", "without")
               if isinstance(c.get(arm), dict) and type(c[arm].get("runs")) is int)


def impact_entry(gates: dict, skill: str, plugin: str, run_url: str | None,
                 versions: tuple, date: str | None = None) -> str:
    """The registry's entry format (docs/skill-impact.md, "Entry format"):
    the date the removal is opened, one line each, links in full since the
    file lives in another repository."""
    cells = gates["skills"][skill]["cells"]
    fixtures = sorted({c.get("fixture") or "(flat)" for c in cells})
    paths = [f"evals/{skill}" if f == "(flat)" else f"evals/{skill}/{f}" for f in fixtures]
    where = f"workflow run {run_url}" if run_url else "its scheduled workflow"
    return (f"## {date or _date(gates['as_of'])} — {plugin}/{skill} — remove\n\n"
            f"- Motivation: the retirement verdict is `retire` "
            f"([skills-evals#70](https://github.com/{EVALS_REPO}/issues/70)): every cell "
            f"({len(fixtures)} fixture(s) x {len(gates['roster_models'])} roster model(s)) "
            f"shows no benefit at the retire confidence level.\n"
            f"- Change: `plugins/{plugin}/skills/{skill}/` removed, the skill dropped from "
            f"`{LAYOUT_FILE}` and the README table, bundle `{plugin}` {versions[0]} -> "
            f"{versions[1]} (a removal is a breaking change), by skills-evals' "
            f"`scripts/retire_skill.py` ({where}).\n"
            f"- Eval: n={_runs(cells)} pooled arm runs (with vs without the skill) as of "
            f"{gates['as_of']}, fixtures {', '.join(paths)}, "
            f"policy evals/gate-policy.yml; per-cell bounds in the pull request.\n"
            f"- Outcome: pending merge; auto-merges once required checks pass, with no "
            f"human review ([ADR 0021]({REGISTRY_ADR})).\n")


def insert_entry(text: str, entry: str) -> str:
    """`entry` newest first: right after the header's `---` rule."""
    lines = text.split("\n")
    try:
        rule = lines.index("---")
    except ValueError:
        raise RetireError(f"{IMPACT_FILE} has no `---` rule to insert after") from None
    head = "\n".join(lines[:rule + 1]).rstrip("\n")
    rest = "\n".join(lines[rule + 1:]).lstrip("\n")
    return f"{head}\n\n{entry}\n{rest}"


def bump(version: str) -> str:
    """The next MAJOR version: a removal breaks every consumer that calls the
    skill. check_plugin_versions.py asks only that it rise; the registry
    bumped major for its last skill removal (sync-skills, 1.1.0 -> 2.0.0)."""
    match = VERSION_RE.fullmatch(version) if isinstance(version, str) else None
    if not match:
        raise RetireError("a plugin version is not MAJOR.MINOR.PATCH")
    return f"{int(match.group(1)) + 1}.0.0"


def manifest_versions(checkout: Path, plugin: str) -> dict:
    """{manifest path: (old, new)}; both manifests must agree."""
    out = {}
    contained(checkout, [f"plugins/{plugin}/.claude-plugin",
                         *(f"plugins/{plugin}/{name}" for name in MANIFESTS), "docs",
                         IMPACT_FILE])
    for name in MANIFESTS:
        rel = f"plugins/{plugin}/{name}"
        try:
            doc = json.loads((checkout / rel).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            raise RetireError(f"cannot read {rel}") from None
        version = doc.get("version") if isinstance(doc, dict) else None
        out[rel] = (version, bump(version))
    if len({old for old, _ in out.values()}) != 1:
        raise RetireError(f"{plugin}'s two manifests disagree on its version")
    return out


def usage_line(usage: dict | None, skill: str, as_of: str) -> str:
    """One line on how often `skill` was invoked lately, for the human who
    decides; `unknown` when there is no fresh usage census at `as_of`."""
    now = datetime.strptime(as_of, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    count = skill_usage.weight(usage, skill, now)
    if count is None:
        return "Recent use: unknown (no fresh usage census)."
    return (f"Recent use: {count} local invocation(s) in the four weeks to {as_of} "
            "(usage/weekly-local.json).")


def layout_without(checkout: Path, plugin: str, skill: str) -> str:
    """`scripts/plugin_layout.json`'s text with `skill` dropped from
    `plugin`, in the registry's canonical form (json.dumps, indent 2, one
    trailing newline). RetireError unless the file lists the skill under the
    plugin, or when the skill is the plugin's last."""
    contained(checkout, ["scripts", LAYOUT_FILE])
    try:
        doc = json.loads((checkout / LAYOUT_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise RetireError(f"cannot read {LAYOUT_FILE}") from None
    plugins = doc.get("plugins") if isinstance(doc, dict) else None
    entry = plugins.get(plugin) if isinstance(plugins, dict) else None
    skills = entry.get("skills") if isinstance(entry, dict) else None
    if not isinstance(skills, list) or skills.count(skill) != 1:
        raise RetireError(f"{LAYOUT_FILE} does not list {skill} once under {plugin}")
    if len(skills) == 1:
        raise RetireError(f"{skill} is {plugin}'s last skill; emptying a plugin is a "
                          "registry decision, not a retirement")
    entry["skills"] = [s for s in skills if s != skill]
    return json.dumps(doc, indent=2) + "\n"


def lock_relevant(checkout: Path, plugin: str) -> bool:
    """Whether `skills.lock` locks `plugin`, so removing one of its skills
    makes the lock stale (adam-agentskills CI's `--check-current`)."""
    contained(checkout, [LOCK_FILE])
    path = checkout / LOCK_FILE
    if not path.exists():
        return False
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise RetireError(f"cannot read {LOCK_FILE}") from None
    bundles = doc.get("bundles") if isinstance(doc, dict) else None
    skills = doc.get("skills") if isinstance(doc, dict) else None
    if not isinstance(bundles, list) or not isinstance(skills, dict):
        raise RetireError(f"{LOCK_FILE} has no bundles list or skills map")
    return plugin in bundles or any(isinstance(k, str) and k.startswith(f"{plugin}/")
                                    for k in skills)


def check_registry(checkout: Path, location: dict, skill: str) -> None:
    """The auto-mode preconditions on the checkout itself; RetireError
    otherwise. Read-only, so a dry run refuses the same way."""
    if _git(checkout, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise RetireError(f"the {TARGET} checkout is shallow; the lock re-pin needs "
                          "full history (fetch-depth: 0)")
    plugin = location["plugin"]
    skills_dir = checkout / "plugins" / plugin / "skills"
    others = [p for p in skills_dir.iterdir() if p.name != skill
              and (p.is_dir() or p.is_symlink())]
    if not others:
        raise AgentFixable(f"{skill} is {plugin}'s last skill; emptying a plugin is a "
                           "registry decision, not a retirement")
    try:
        layout_without(checkout, plugin, skill)
    except RetireError as exc:
        if "does not list" in str(exc):
            raise AgentFixable(str(exc)) from None
        raise
    contained(checkout, [README_FILE, README_GENERATOR, LOCK_GENERATOR])
    for rel in (README_FILE, README_GENERATOR):
        if not (checkout / rel).is_file():
            raise RetireError(f"{TARGET} has no {rel}")
    if lock_relevant(checkout, plugin) and not (checkout / LOCK_GENERATOR).is_file():
        raise RetireError(f"{TARGET} has no {LOCK_GENERATOR}")
    runtime_gated(checkout, location["path"], skill)
    waived_paths(checkout, location["path"], skill)
    dangling_citations(checkout, location["path"], skill)


TEST_NAME_RE = re.compile(r"\btest_[a-z0-9_]+")


def _defined_tests(checkout: Path, rels) -> set:
    """Function names (parsed, never grepped) and module stems of `rels`."""
    names = set()
    for rel in rels:
        if not rel.endswith(".py"):
            continue
        names.add(Path(rel).stem)
        try:
            tree = ast.parse((checkout / rel).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
            raise RetireError(f"cannot parse {rel}") from None
        names |= {node.name for node in ast.walk(tree)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return {n for n in names if n.startswith("test_")}


def dangling_citations(checkout: Path, path: str, skill: str) -> None:
    """AgentFixable when a tracked source outside the skill cites, by name, a
    test that only the skill defines. adam-agentskills'
    test_every_test_this_repo_cites_by_name_exists scans every tracked
    non-test `*.py` and `*.sh` for `test_...` tokens and fails on one no
    tracked module defines, so removing the skill would turn that citation
    into a failing required check. Rewording someone's comment is not a
    removal's job; an agent does that."""
    inside = _git(checkout, "ls-files", "-z", "--", path).split("\0")
    gone = _defined_tests(checkout, [r for r in inside if r])
    if not gone:
        return
    outside = [r for r in _git(checkout, "ls-files", "-z", "--", "*.py", "*.sh")
               .split("\0") if r and not (r == path or r.startswith(f"{path}/"))]
    gone -= _defined_tests(checkout, outside)
    for rel in outside:
        if Path(rel).name.startswith("test_"):
            continue
        try:
            text = (checkout / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise RetireError(f"cannot read {rel}") from None
        cited = sorted(set(TEST_NAME_RE.findall(text)) & gone)
        if cited:
            raise AgentFixable(f"{rel} cites {cited[0]}, a test only {skill} defines; "
                               "removing the skill leaves that citation dangling, which "
                               f"{TARGET}' test_every_test_this_repo_cites_by_name_exists "
                               "fails on")


def waived_paths(checkout: Path, path: str, skill: str) -> None:
    """AgentFixable when `scripts/skills_waivers.yml` waives a finding inside
    the skill: that waiver matches nothing once the skill is gone, and
    check_skills.py reports a `stale-waiver` and exits 1, so the pull request
    could never merge. Removing the waiver with the skill means editing a
    commented YAML file, which this does not do; an agent does that. The
    file is parsed, never grepped — its comments name skills
    and would read as waivers."""
    contained(checkout, [WAIVERS_FILE])
    file = checkout / WAIVERS_FILE
    if not file.exists():
        return
    try:
        doc = yaml.safe_load(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        raise RetireError(f"cannot read {WAIVERS_FILE}") from None
    waivers = (doc or {}).get("waivers") if isinstance(doc, dict) else None
    if waivers is None:
        waivers = []
    if not isinstance(waivers, list):
        raise RetireError(f"{WAIVERS_FILE}: waivers is not a list")
    for waiver in waivers:
        where = waiver.get("path") if isinstance(waiver, dict) else None
        if isinstance(where, str) and (where == path or where.startswith(f"{path}/")):
            raise AgentFixable(f"{WAIVERS_FILE} waives a finding under {skill}; that "
                               "waiver goes stale when the skill does and check_skills.py "
                               "would exit 1, so the waiver is retired with the skill")


def runtime_gated(checkout: Path, path: str, skill: str) -> None:
    """RetireError when deleting this skill would be a plugin RUNTIME change
    in adam-agentskills' sense (its ADR 0016 gate): a `hooks/` or `bin/`
    directory inside the skill, or a hook naming a path inside it. Such a
    pull request waits on the `plugin-runtime-review` environment for the
    owner's approval, which auto-merge cannot supply, so the branch would sit
    open forever and hold the one removal slot. No skill ships either today;
    this refuses the day one does, rather than wedging the queue."""
    for name in ("hooks", "bin"):
        if (checkout / path / name).exists():
            raise RetireError(f"{skill} ships a {name}/ directory, so removing it is a "
                              "plugin runtime change: adam-agentskills' "
                              "plugin-runtime-review gate holds such a pull request for "
                              "the owner, and auto-merge cannot approve it")
    needle = f"skills/{skill}/"
    for config in sorted(checkout.glob("plugins/*/hooks/*.json")) + [
            checkout / f"plugins/{p}/{m}" for p in
            sorted(d.name for d in (checkout / "plugins").iterdir() if d.is_dir())
            for m in MANIFESTS]:
        if config.is_symlink() or not config.is_file():
            continue
        try:
            text = config.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise RetireError(f"cannot read {config.relative_to(checkout).as_posix()}") \
                from None
        if needle in text:
            raise RetireError(
                f"{config.relative_to(checkout).as_posix()} names a path inside {skill}, "
                "so removing it is a plugin runtime change: adam-agentskills' "
                "plugin-runtime-review gate holds such a pull request for the owner, and "
                "auto-merge cannot approve it")


def run_registry_script(checkout: Path, script: str, *args: str) -> None:
    """Run one of the registry's own scripts in its checkout, with a scrubbed
    environment: no token or other secret from this workflow reaches it, and
    no bytecode is written into the checkout. Reported by exit code only."""
    contained(checkout, ["scripts", script])
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8",
           "HOME": os.environ.get("HOME", "/nonexistent"),
           "PYTHONDONTWRITEBYTECODE": "1"}
    # Each target is spelled literally at its call so the suite's spawn audit
    # (run_tests.py, S-B-a-2) can prove it is not the test runner.
    if script == README_GENERATOR:
        proc = subprocess.run([sys.executable, "scripts/generate_readme_table.py", *args],
                              cwd=str(checkout), env=env, capture_output=True, text=True,
                              check=False)
    elif script == LOCK_GENERATOR:
        proc = subprocess.run([sys.executable, "scripts/generate_skills_lock.py", *args],
                              cwd=str(checkout), env=env, capture_output=True, text=True,
                              check=False)
    else:
        raise RetireError(f"{script} is not a registry script this tool runs")
    if proc.returncode != 0:
        raise RetireError(" ".join([script, *args, "exited", str(proc.returncode)]))


def _issue_body(gates, skill, location, problem, run_url, usage=None,
                mode_reason=None) -> str:
    where = (f"`{location['path']}` in {REGISTRY_REPO}" if location
             else f"not located: {problem}")
    run = f"\nWorkflow run: {run_url}\n" if run_url else ""
    why = (f"`evals/gate-policy.yml` sets `retirement_mode: auto`, but {mode_reason}, "
           "so no removal pull request is opened and a human removes it"
           if mode_reason else
           "`evals/gate-policy.yml` sets `retirement_mode: proposal`, so a human "
           "removes it")
    return (f"{ISSUE_MARKER.format(skill=skill)}\n{PROPOSAL_STAMP}\n"
            f"The retirement verdict for `{skill}` is **retire** as of "
            f"{gates['as_of']}: {gates['skills'][skill].get('reason')}.\n\n"
            f"{usage_line(usage, skill, gates['as_of'])}\n\n"
            f"{why}. Copy: {where}.\n\n{evidence(gates, skill)}\n{run}\n"
            "Filed by scripts/retire_skill.py on the scheduled workflow (#70).\n")


def agent_issue_body(gates, skill, agent, run_url, usage=None) -> str:
    """The agent route's issue (Adam, 2026-11-13): the proposal body's verdict
    line and table, the registry and path, why the bot did not open the
    removal itself, and who removes it."""
    run = f"\nWorkflow run: {run_url}\n" if run_url else ""
    return (f"{ISSUE_MARKER.format(skill=skill)}\n{AGENT_STAMP}\n"
            f"The retirement verdict for `{skill}` is **retire** as of "
            f"{gates['as_of']}: {gates['skills'][skill].get('reason')}.\n\n"
            f"{usage_line(usage, skill, gates['as_of'])}\n\n"
            f"Registry: `{agent['registry']}`, path `{agent['path']}`. The bot did not "
            f"open the removal pull request itself: {agent['reason']}.\n\n"
            f"{evidence(gates, skill)}\n{run}\n"
            f"The fleet worker removes it ({AGENT_WORKER_DOC}): a pull request from "
            f"branch `{BRANCH_PREFIX}{skill}` in that repository that closes this "
            "issue.\n\n"
            "Filed by scripts/retire_skill.py on the scheduled workflow (#70).\n")


def _pr_body(gates, skill, location, versions, run_url, repin=False) -> str:
    bumps = "\n".join(f"- `{p}`: {old} -> {new}" for p, (old, new) in versions.items())
    lock = (f" A second commit re-pins `{LOCK_FILE}` to the removal commit."
            if repin else "")
    run = f"\nWorkflow run: {run_url}\n" if run_url else ""
    return (f"Removes `{location['path']}`: its retirement verdict in "
            f"[skills-evals#70](https://github.com/{EVALS_REPO}/issues/70) is "
            f"**retire** as of {gates['as_of']} "
            f"({gates['skills'][skill].get('reason')}).\n\n{evidence(gates, skill)}\n\n"
            f"Version bumps:\n{bumps}\n\nAdds a `{IMPACT_FILE}` entry, drops the skill "
            f"from `{LAYOUT_FILE}` and regenerates the `{README_FILE}` skill table."
            f"{lock}\n\n"
            f"This pull request auto-merges (merge commit) once required checks pass, "
            f"with no human review, by Adam's 2026-10-25 decision "
            f"([skills-evals ADR 0014]({ADR}); [ADR 0021]({REGISTRY_ADR})). To decline "
            f"the removal, close it: a closed `{BRANCH_PREFIX}{skill}` pull request means "
            f"the skill is decided, and none is opened again.\n"
            f"{run}\nOpened by skills-evals' scripts/retire_skill.py on its scheduled "
            f"workflow.\n\n{AGENT_MARKER}\n")


def guidance_proposal_only(verdict: dict) -> str | None:
    """Why a guidance section's `retire` verdict allows only a proposal, or
    None. Every `retire` removal is automatic (Adam, 2026-11-13), but the
    section-alone pair is re-checked here rather than trusted from the
    verdict's `removal` field: an unfinished alone pair (harness/gates.py
    `alone_unfinished`: no alone cell, or one that has not decided) could
    still turn the verdict into shorten-or-merge, so the removal waits
    (`guidance_plan` files nothing)."""
    alone = verdict.get("alone")
    if alone is not None and not isinstance(alone, dict):
        return "the verdict's alone block is malformed"
    if gates.alone_unfinished((alone or {}).get("cells")):
        return gates.ALONE_UNFINISHED_REASON
    return None


def _lowered(mode_reason: str, allowed) -> str:
    """`proposal`, the mode auto falls back to; RetireError when the caller
    has not allowed it either."""
    if "proposal" not in allowed:
        raise RetireError(f"retirement_mode auto falls back to proposal ({mode_reason}), "
                          f"which this caller has not wired (allowed: {', '.join(allowed)})")
    return "proposal"


def paused_reason(count: int) -> str:
    """Why a subject the loop has paused MAX_LOOP_PAUSES times or more gets
    its proposal issue rather than another removal (R6-6)."""
    return (f"the loop has already withdrawn {count} automatic removal pull requests for "
            f"it (at most {MAX_LOOP_PAUSES} before a person decides, so a verdict near its "
            "threshold cannot open and withdraw removals without end)")


#: In the body of a retirement issue the pause cap has reached, so the
#: comment that tells a person is posted once (R7-4).
CAP_MARKER = "<!-- skills-evals:pause-cap:{subject} -->"
#: What every CAP_MARKER starts with. A retirement issue carries only its own
#: subject's, so `guidance_issues` reads this prefix in the issues it lists.
CAP_PREFIX = CAP_MARKER.split("{", 1)[0]


def cap_note(subject: str, count: int) -> str:
    """What the retirement issue says once the pause cap is reached, and the
    one comment that announces it (a comment notifies; a body edit does
    not). The way back is a person's: nothing lowers the count."""
    return (f"{CAP_MARKER.format(subject=subject)}\n@{NOTICE_OWNER}: the loop has withdrawn "
            f"{count} automatic removal pull requests for `{subject}`, so it has stopped "
            f"opening removals for it (at most {MAX_LOOP_PAUSES}). This issue is now the "
            "proposal, and a person decides. Nothing lowers the count, so the loop does not "
            "resume on its own. To remove the subject, take over the last withdrawn removal: "
            f"remove its `{AGENT_LABEL}` label, restore its branch from the pull request page, "
            "reopen it and merge it by hand (or remove the subject by hand). To decline, "
            f"close this issue. Rule: [ADR 0014]({ADR}).\n")


def cap_notice(action: dict, gh, subject: str, count: int) -> dict:
    """`action` (the proposal issue the cap falls back to) with `cap_note`
    in its body and, the first time the cap reaches an open issue (its body
    lacks CAP_MARKER), `cap_comment` to post on it. A new issue mentions the
    owner in its body, which notifies; a closed one already decided. Every
    path that writes a retirement issue at the cap goes through here, the
    pass lowered to a proposal included (R12-1): a body rewritten without
    the note would erase CAP_MARKER, and the next pass would post the
    comment again."""
    if action["action"] not in ("create-issue", "update-issue"):
        return action
    note = cap_note(subject, count)
    action = {**action, "body": f"{action['body']}\n{note}"}
    if action["action"] == "update-issue":
        old = gh(["api", f"repos/{EVALS_REPO}/issues/{action['issue']}", "--jq",
                  '.body // ""'])
        if CAP_MARKER.format(subject=subject) not in old:  # posted once (R7-4)
            action["cap_comment"] = f"{note}\n{AGENT_MARKER}\n"
    return action


def cap_owed(found: dict) -> bool:
    """Whether the pause cap's one comment is still owed (R11-1): an open
    retirement issue exists and none of the subject's issues, open or
    closed, records the comment (`capped`). Then the open issue gets it,
    even beside a closed issue, so the owner learns the loop stopped."""
    return bool(found["open"]) and not found["capped"]


def capped_decided(found: dict, mode: str, key: str, subject: str, count: int) -> dict:
    """At the pause cap, the `none` action for a subject a closed retirement
    issue decides (R10-3), once no cap comment is owed (`cap_owed`, R11-1):
    the comment is already on one of its issues, or no issue is open. So the
    comment is posted at most once per subject, and a subject with no open
    issue is decided with none."""
    number = found["closed"][0]
    return {"action": "none", "mode": mode, key: subject, "issue": number,
            "reason": f"{subject} is already decided: the loop has withdrawn {count} "
                      f"removals for it and its retirement issue #{number} is closed, which "
                      "at the pause cap declines it, so nothing is filed or commented"}


def paused_heads(paused: list) -> list:
    """The head commits of the loop's paused removals, for `default_push`'s
    retried delete (R7-2)."""
    return sorted({p["sha"] for p in paused
                   if isinstance(p.get("sha"), str) and SHA_RE.fullmatch(p["sha"])})


def declined(found: dict, subject: str, mode: str, key: str) -> dict | None:
    """In `auto` mode, the `none` action when a closed retirement issue the
    proposal path filed (or one predating the stamps) declines the removal
    (R8-1), whatever else is open: a person closed the proposal. Any close
    declines, whatever its reason (`state_reason` is not read: "completed"
    and "not planned" alike). A closed issue the withdrawal path filed
    declines nothing until the pause cap. `found` is `guidance_issues`'s
    result; None when nothing declines. `closed_at` is the latest close time
    of the declining issues, or None when any of them is missing or
    unparseable; a person's arm in force wins over the decline only when it
    is strictly later than that time (round 13, `persons_arm`), so with None
    the decline wins."""
    closed = [n for n in found["closed"] if n in found["proposals"]]
    if not closed:
        return None
    times = [found.get("closed_at", {}).get(n) for n in closed]
    moments = [_moment(t) for t in times]
    latest = None if any(m is None for m in moments) else \
        times[moments.index(max(moments))]
    # Name the issue with the latest close (the one `closed_at` is); keep
    # the first when any close time is missing or unparseable.
    named = closed[0] if latest is None else closed[moments.index(max(moments))]
    return {"action": "none", "mode": mode, key: subject, "issue": named,
            "closed_at": latest,
            "reason": f"{subject} is already decided: its proposal issue #{named} is "
                      "closed, which declines the removal, so none is opened"}


def deciding_issues(found: dict, withdrawn_decides: bool, paused: int = 0) -> list:
    """The closed retirement issues that decide a subject on the proposal
    path. Every closed one, unless `withdrawn_decides` is False (R9-5: `auto`
    mode lowered to a proposal) and the subject's loop pauses are short of
    the cap (`paused` < MAX_LOOP_PAUSES, R10-3), when one the withdrawal path
    filed (`WITHDRAWAL_STAMP`) does not: a person closed it after being told
    that closing it declines nothing, so a fresh proposal issue is filed for
    them to decide on. At the cap any closed issue decides (R10-3): the loop
    has stopped opening removals, so a close is read as a decline whatever
    its stamp. An open issue this lowered path rewrites at the cap keeps
    the cap note (`cap_notice`, R12-1)."""
    if withdrawn_decides or paused >= MAX_LOOP_PAUSES:
        return found["closed"]
    return [n for n in found["closed"] if n in found["proposals"]]


def _skill_issue(gates, registries, gh, skill, mode_reason, run_url, usage,
                 withdrawn_decides=True, paused=0, agent=None) -> dict:
    """The proposal path's action: create or update the skill's issue, or
    nothing when a closed one already decided it (`deciding_issues`).
    With `agent` ({registry, path, reason}) it is the agent route's: the
    agent body and stamp, and the `agent-ready` label unless the issue
    already carries one of AGENT_BLOCKING_LABELS. An open proposal-stamped
    issue is rewritten in place; an open held one is left alone."""
    try:
        location, problem = locate(registries, skill), None
    except RetireError as exc:
        location, problem = None, str(exc)
    issues = existing_issues(gh, skill)
    lowered = {"mode_reason": mode_reason} if mode_reason else {}
    decided = deciding_issues(issues, withdrawn_decides, paused)
    if not issues["open"] and decided:
        return {"action": "none", "mode": "proposal", "skill": skill, **lowered,
                "issue": decided[0],
                "reason": f"{skill} is already decided: issue "
                          f"#{decided[0]} is closed, so none is filed again"}
    number = issues["open"][0] if issues["open"] else None
    if agent:
        held = [n for n in issues.get("held", []) if n in issues["open"]]
        if held:
            return {"action": "none", "mode": "agent", "skill": skill, "issue": held[0],
                    "reason": f"{skill}'s removal is held for a person: issue #{held[0]} "
                              "is open, so no agent issue is filed over it"}
        carried = issues.get("labels", {}).get(number, [])
        return {"action": "update-issue" if number else "create-issue", "mode": "agent",
                "skill": skill, "issue": number, "agent_reason": agent["reason"],
                "label": None if any(n in AGENT_BLOCKING_LABELS for n in carried)
                else AGENT_READY_LABEL,
                "title": f"Retire skill {skill}: no benefit on every roster model (#70)",
                "body": agent_issue_body(gates, skill, agent, run_url, usage)}
    return {"action": "update-issue" if number else "create-issue", "mode": "proposal",
            "skill": skill, "issue": number, **lowered,
            "title": f"Retire skill {skill}: no benefit on every roster model (#70)",
            "body": _issue_body(gates, skill, location, problem, run_url, usage, mode_reason)}


def plan(gates: dict, registries: dict, gh, run_url: str | None = None,
         allowed=("proposal",), usage: dict | None = None, fallback: bool = False,
         date: str | None = None, unused_loader=None) -> dict:
    """What to do, read-only. RetireError for a refusal.

    With no `retire` verdict, and `unused_loader` (returns the removal policy
    and the exempt skills, see `unused_inputs`), an unused skill may be
    removed instead (`unused_plan`); a `retire` verdict always has priority."""
    skill = retiring(gates)
    mode = mode_of(gates)
    if skill is None:
        if unused_loader is not None:
            return unused_plan(gates, registries, gh, run_url, allowed, usage, date,
                               unused_loader)
        return {"action": "none", "mode": mode, "reason": "no skill has a retire verdict"}
    mode_reason = None
    agent = None
    if mode == "auto" and "auto" not in allowed and fallback:
        mode_reason = NO_CREDENTIAL
        mode = _lowered(mode_reason, allowed)
        # No registry write credential: an auto-eligible skill goes to the
        # fleet worker, a runtime-review one to the owner, one the bot cannot
        # find exactly once stays the proposal it was.
        try:
            where = locate_anywhere(registries, skill)
        except RetireError:
            where = None
        if where is not None:
            runtime = runtime_refusal(Path(registries[TARGET]["path"]), where["plugin"],
                                      skill) if where["registry"] == REGISTRY_REPO else None
            if runtime:
                mode_reason = runtime
            else:
                agent = {**where, "reason": NO_CREDENTIAL}
    if mode not in allowed:
        raise RetireError(f"retirement_mode is {mode}, which this caller has not wired "
                          f"(allowed: {', '.join(allowed)})")
    if mode == "auto":
        where = locate_anywhere(registries, skill)
        checkout = Path(registries[TARGET]["path"])
        if where["registry"] != REGISTRY_REPO:
            # Its one copy is in a registry the bot never writes: an agent can.
            agent = {**where, "reason": f"its one copy is in {where['registry']}, a "
                     f"registry this bot has no credential to write ({TARGET} is the "
                     "only one)"}
            mode = _lowered(agent["reason"], allowed)
        else:
            location = {"plugin": where["plugin"], "path": where["path"]}
            mode_reason = runtime_refusal(checkout, location["plugin"], skill)
            if mode_reason:
                mode = _lowered(mode_reason, allowed)
    if mode == "proposal":
        # R10-3: lowered from `auto`, the pause cap still decides, so the
        # subject's loop pauses are counted here too.
        lowered_from_auto = mode_of(gates) == "auto"
        paused = 0
        if lowered_from_auto:
            declined_prs, paused_prs = deciding(closed_removal_prs(gh, skill))
            paused = len(paused_prs)
            if agent and declined_prs:
                # The auto path's "already decided": a person closed this
                # skill's removal, so no agent issue overrides the decline.
                return {"action": "none", "mode": mode, "skill": skill,
                        "reason": f"{skill} is already decided: removal pull request "
                                  f"{declined_prs[0].get('url')} is closed, so none "
                                  "is opened again"}
            mine = [p for p in open_loop_prs(gh)
                    if p.get("head") == f"{BRANCH_PREFIX}{skill}"] if agent else []
            if mine:
                return {"action": "none", "mode": mode, "skill": skill,
                        "reason": f"{skill}'s removal pull request {mine[0].get('url')} "
                                  "is already open, so no agent issue is filed beside it"}
        if paused >= MAX_LOOP_PAUSES:
            agent = None  # the loop stopped: a person decides (the cap note)
        action = _skill_issue(gates, registries, gh, skill, mode_reason, run_url, usage,
                              withdrawn_decides=not lowered_from_auto, paused=paused,
                              agent=agent)
        # R12-1: at the cap the rewritten body keeps CAP_MARKER, so the cap
        # comment is posted once whichever pass reaches the cap first.
        return cap_notice(action, gh, skill, paused) if paused >= MAX_LOOP_PAUSES else action
    return _removal_action(gates, registries, gh, skill, mode, location, checkout, run_url,
                           usage, allowed, date)


def _removal_action(gates: dict, registries: dict, gh, skill: str, mode: str, location: dict,
                    checkout: Path, run_url: str | None, usage: dict | None, allowed,
                    date: str | None, unused: dict | None = None) -> dict:
    """The auto path of `plan` for one skill, past the mode and runtime
    checks: the loop-slot, closed-pull-request, declined, held and pause-cap
    refusals, then the removal action. `unused` (an `unused_removal` answer)
    makes it an `unused` removal: its figures, not a verdict's cells, fill
    the texts, and a refusal that concerns only this skill carries
    `candidate_decided` so the caller may try the next candidate."""
    skip = {"candidate_decided": True} if unused else {}
    prs = open_loop_prs(gh)
    if prs:
        return {"action": "none", "mode": mode, "skill": skill,
                "reason": "a loop pull request is already open in "
                          f"{REGISTRY_REPO}, so this removal waits for it: "
                          + ", ".join(str(p.get("url")) for p in prs)}
    closed, paused = deciding(closed_removal_prs(gh, skill))
    if closed:
        return {"action": "none", "mode": mode, "skill": skill,
                "reason": f"{skill} is already decided: removal pull request "
                          f"{closed[0].get('url')} is closed, so none is opened again", **skip}
    issues = existing_issues(gh, skill)
    decline = declined(issues, skill, mode, "skill")
    if decline:
        return {**decline, **skip}
    held = [n for n in issues.get("held", []) if n in issues["open"]]
    if held:
        return {"action": "none", "mode": mode, "skill": skill, "issue": held[0],
                "reason": f"{skill}'s removal is held for a person: issue #{held[0]} "
                          "is open, so no removal is reviewed or opened again", **skip}
    working = [n for n in issues.get("agent", []) if n in issues["open"]]
    if working:
        # The fleet worker owns this removal through its issue: a second pull
        # request here would leave that issue open after the merge, and a
        # loop withdrawal of it could read to the worker as a decline.
        return {"action": "none", "mode": mode, "skill": skill, "issue": working[0],
                "reason": f"the fleet worker holds {skill}'s removal: issue #{working[0]} "
                          "is open, so this run opens no pull request beside it", **skip}
    capped = len(paused) >= MAX_LOOP_PAUSES
    if capped and unused:
        # The cap files a retirement issue from a verdict's cells; an unused
        # skill has none, so the loop simply stops opening its removal.
        return {"action": "none", "mode": mode, "skill": skill, **skip,
                "reason": f"{skill}'s removal was paused {len(paused)} times by the loop, "
                          "so no unused removal is opened again"}
    if capped and not cap_owed(issues):  # R11-1: else the open issue gets it first
        if issues["closed"]:
            return capped_decided(issues, mode, "skill", skill, len(paused))
    if capped:
        mode_reason = paused_reason(len(paused))
        _lowered(mode_reason, allowed)
        return cap_notice(_skill_issue(gates, registries, gh, skill, mode_reason, run_url,
                                       usage), gh, skill, len(paused))
    versions = manifest_versions(checkout, location["plugin"])
    try:
        check_registry(checkout, location, skill)
    except AgentFixable as exc:
        if unused:
            raise
        # An agent can clear it (a waiver, a citing source, the layout, the
        # plugin's last skill): the fleet worker removes it, not a person.
        return _skill_issue(gates, registries, gh, skill, None, run_url, usage,
                            withdrawn_decides=False, paused=len(paused),
                            agent={"registry": REGISTRY_REPO, "path": location["path"],
                                   "reason": str(exc)})
    repin = lock_relevant(checkout, location["plugin"])
    if unused:
        as_of = gates["as_of"]
        entry = unused_impact_entry(skill, location["plugin"], run_url,
                                    next(iter(versions.values())), unused, as_of, date)
        return {"action": "removal", "mode": mode, "skill": skill, **location,
                "removal_reason": "unused", "unused": unused,
                "branch": f"{BRANCH_PREFIX}{skill}", "versions": versions,
                "paused_heads": paused_heads(paused),
                "impact_entry": entry, "repin": repin,
                "notice": unused_notice(skill, location, run_url, unused, as_of),
                "held_issue": issues["open"][0] if issues["open"] else None,
                "held_title": f"Retire skill {skill}: held for a person (unused)",
                "held_body": _unused_issue_body(skill, location, run_url, unused, as_of)
                + f"\n{HELD_MARKER}\n{HELD_SLOT}\n",
                "run_url": run_url,
                "verdict": f"unused as of {as_of}: {unused['why']}",
                "title": f"Remove {location['plugin']}/{skill}: unused "
                         "(skills-evals removal policy)",
                "body": _unused_pr_body(skill, location, versions, run_url, repin, unused,
                                        as_of)}
    entry = impact_entry(gates, skill, location["plugin"], run_url,
                         next(iter(versions.values())), date)
    return {"action": "removal", "mode": mode, "skill": skill, **location,
            "branch": f"{BRANCH_PREFIX}{skill}", "versions": versions,
            "paused_heads": paused_heads(paused),
            "impact_entry": entry, "repin": repin,
            "notice": skill_notice(gates, skill, location, run_url),
            "held_issue": issues["open"][0] if issues["open"] else None,
            "held_title": f"Retire skill {skill}: held for a person (#70)",
            "held_body": _issue_body(gates, skill, location, None, run_url, usage,
                                     HELD_REASON) + f"\n{HELD_MARKER}\n{HELD_SLOT}\n",
            "run_url": run_url,
            "verdict": (f"retire as of {gates['as_of']}: "
                        f"{gates['skills'][skill].get('reason')}"),
            "title": f"Remove {location['plugin']}/{skill}: no benefit (skills-evals#70)",
            "body": _pr_body(gates, skill, location, versions, run_url, repin)}


# ---------------------------------------------------------------------------
# The `unused` reason (Adam, 2026-11-12): a skill nobody uses is removed once
# the context its description cost passes the value of one use
# (evals/removal-policy.yml, harness/removal_policy.py). It opens the same
# `retire-skill/<skill>` pull request as a `retire` verdict, through the same
# refusals, adversarial review and auto-merge, but only in `auto` mode with
# `auto` allowed, never lowered to an issue, and never beside a `retire`
# verdict, which has priority: at most one removal per run.

REMOVAL_POLICY_FILE = REPO_ROOT / "evals" / "removal-policy.yml"
RESTORE_COMMAND = "python3 scripts/restore_skill.py {skill}"


def unused_inputs() -> tuple:
    """(the removal policy, the exempt skills) from this repository's
    evals/removal-policy.yml and evals/usage-unknown.yml; RetireError when
    either cannot be read."""
    try:
        policy = removal_policy.load(REMOVAL_POLICY_FILE)
        exempt = set(eval_scope.usage_unknown(REPO_ROOT))
    except (removal_policy.PolicyError, eval_scope.ScopeError) as exc:
        raise RetireError(f"the unused-removal inputs cannot be read: {exc}") from None
    return policy, exempt


def _as_of_moment(as_of: str) -> datetime:
    return datetime.strptime(as_of, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def unused_candidates(gates: dict, registries: dict, usage, policy: dict,
                      exempt) -> list:
    """Every skill of adam-agentskills' `scripts/plugin_layout.json` whose
    `unused_removal` says remove, most accrued cost first, then by name.
    Surfaces come from `eval_scope._surfaces` (the same local-only plugins as
    the scope pass), d from the skill's SKILL.md. A skill whose copy cannot be
    located exactly once, or whose SKILL.md has no readable frontmatter, is
    not a candidate. [] when there is no checkout, layout or fresh census."""
    if TARGET not in registries or usage is None:
        return []
    checkout = Path(registries[TARGET]["path"])
    layout = checkout / LAYOUT_FILE
    if not layout.is_file() or layout.is_symlink():
        return []
    try:
        plugins = eval_scope._skill_plugins(layout)
    except eval_scope.ScopeError:
        return []
    now = _as_of_moment(gates["as_of"])
    found = []
    for skill in sorted(plugins):
        if not SKILL_RE.fullmatch(skill):
            continue
        try:
            location = locate(registries, skill)
            contained(checkout, [f"{location['path']}/SKILL.md"])
            d = removal_policy.description_tokens(
                (checkout / location["path"] / "SKILL.md").read_text(encoding="utf-8"))
        except (RetireError, removal_policy.PolicyError, OSError, UnicodeDecodeError):
            continue
        decision = removal_policy.unused_removal(
            policy, usage, skill, eval_scope._surfaces(skill, plugins), d, now, exempt)
        if decision["remove"]:
            found.append({**decision, "location": location})
    return sorted(found, key=lambda c: (-c["accrued_usd"], c["skill"]))


def unused_plan(gates: dict, registries: dict, gh, run_url: str | None, allowed,
                usage, date: str | None, loader) -> dict:
    """The plan when no skill has a `retire` verdict: remove the unused
    skill with the most accrued cost, or nothing. Nothing is raised for a
    missing census, checkout or credential (a run with no verdict used to do
    nothing, and still does); a policy file that cannot be read, a shallow
    checkout, or any refusal `plan` makes for a removal is raised."""
    mode = mode_of(gates)
    none = {"action": "none", "mode": mode, "reason": "no skill has a retire verdict"}
    if mode != "auto" or "auto" not in allowed or usage is None or TARGET not in registries:
        return none
    policy, exempt = loader()
    candidates = unused_candidates(gates, registries, usage, policy, exempt)
    if not candidates:
        return {**none, "reason": "no skill has a retire verdict, and none is unused enough "
                                  "to remove (evals/removal-policy.yml)"}
    checkout = Path(registries[TARGET]["path"])
    if _git(checkout, "rev-parse", "--is-shallow-repository").strip() != "false":
        raise RetireError(f"the {TARGET} checkout is shallow; the lock re-pin needs "
                          "full history (fetch-depth: 0)")
    skipped = []
    for candidate in candidates:
        skill, location = candidate["skill"], candidate["location"]
        try:
            held = runtime_refusal(checkout, location["plugin"], skill)
            if held is None:
                check_registry(checkout, location, skill)
        except RetireError as exc:
            held = str(exc)
        if held:
            skipped.append(f"{skill}: {held}")
            continue
        action = _removal_action(gates, registries, gh, skill, mode, location, checkout,
                                 run_url, usage, allowed, date, unused=candidate)
        if action.get("candidate_decided"):
            skipped.append(f"{skill}: {action['reason']}")
            continue
        return action
    return {**none, "reason": "no skill has a retire verdict; "
                              f"{len(candidates)} unused skill(s), none removable now: "
                              + "; ".join(skipped)}


def _unused_figures(unused: dict) -> str:
    """The numbers behind an unused removal, as Markdown lines."""
    lines = [f"- Floor window: the {unused['floor_weeks']} ISO weeks from "
             f"{unused['window_start']} (the census counts every surface the skill "
             "reaches back to it)."]
    for surface in unused["surfaces"]:
        lines.append(f"- {surface}: {unused['exposure'].get(surface, 0)} full-listing "
                     f"session(s) in the window; N* = V x P / (d x R) = "
                     f"{unused['threshold'][surface]:.0f} sessions alone would reach V.")
    lines += [f"- Uses in the window: {unused['uses']}.",
              f"- d (description tokens, ceil(bytes / 4) of the frontmatter name and "
              f"description): {unused['d']}.",
              f"- Accrued description cost: ${unused['accrued_usd']:.2f}, against "
              f"V = ${unused['value_usd']:g} for one use "
              "(`evals/removal-policy.yml`)."]
    return "\n".join(lines)


def _unused_pr_body(skill, location, versions, run_url, repin, unused, as_of) -> str:
    bumps = "\n".join(f"- `{p}`: {old} -> {new}" for p, (old, new) in versions.items())
    lock = (f" A second commit re-pins `{LOCK_FILE}` to the removal commit."
            if repin else "")
    run = f"\nWorkflow run: {run_url}\n" if run_url else ""
    return (f"Removes `{location['path']}`: it is **unused** as of {as_of} "
            f"({unused['why']}).\n\n{_unused_figures(unused)}\n\n"
            f"Restore it, if it is wanted after all: in an adam-agentskills checkout, on a "
            f"fresh branch from main, run `{RESTORE_COMMAND.format(skill=skill)}`. It "
            "restores the directory from the removal commit's parent, bumps the plugin's "
            "MINOR version and adds a `restore` entry to "
            f"`{IMPACT_FILE}`.\n\n"
            f"Version bumps:\n{bumps}\n\nAdds a `{IMPACT_FILE}` entry, drops the skill "
            f"from `{LAYOUT_FILE}` and regenerates the `{README_FILE}` skill table."
            f"{lock}\n\n"
            f"This pull request auto-merges (merge commit) once required checks pass, "
            f"with no human review, by Adam's 2026-10-25 decision "
            f"([skills-evals ADR 0014]({ADR}); [ADR 0021]({REGISTRY_ADR})) and his "
            "2026-11-12 decision to remove unused skills. To decline the removal, close "
            f"it: a closed `{BRANCH_PREFIX}{skill}` pull request means the skill is "
            f"decided, and none is opened again.\n"
            f"{run}\nOpened by skills-evals' scripts/retire_skill.py on its scheduled "
            f"workflow.\n\n{AGENT_MARKER}\n")


def unused_impact_entry(skill: str, plugin: str, run_url: str | None, versions: tuple,
                        unused: dict, as_of: str, date: str | None = None) -> str:
    """`impact_entry` for the `unused` reason: the same entry format, with
    the census figures where a verdict's cells would be."""
    where = f"workflow run {run_url}" if run_url else "its scheduled workflow"
    sessions = ", ".join(f"{s} {unused['exposure'].get(s, 0)}" for s in unused["surfaces"])
    return (f"## {date or _date(as_of)} — {plugin}/{skill} — remove\n\n"
            f"- Motivation: reason `unused`: no recorded use in the last "
            f"{unused['floor_weeks']} weeks, and its description has cost "
            f"${unused['accrued_usd']:.2f} of context, at least the "
            f"${unused['value_usd']:g} one use is worth (skills-evals "
            "`evals/removal-policy.yml`).\n"
            f"- Change: `plugins/{plugin}/skills/{skill}/` removed, the skill dropped from "
            f"`{LAYOUT_FILE}` and the README table, bundle `{plugin}` {versions[0]} -> "
            f"{versions[1]} (a removal is a breaking change), by skills-evals' "
            f"`scripts/retire_skill.py` ({where}). Restore with "
            f"`{RESTORE_COMMAND.format(skill=skill)}`.\n"
            f"- Eval: none; usage census as of {as_of}, full-listing sessions in the "
            f"window: {sessions}, uses 0.\n"
            f"- Outcome: pending merge; auto-merges once required checks pass, with no "
            f"human review ([ADR 0021]({REGISTRY_ADR})).\n")


def unused_notice(skill: str, location: dict, run_url: str | None, unused: dict,
                  as_of: str) -> dict:
    """`skill_notice` for the `unused` reason."""
    marker = SKILL_NOTICE_MARKER.format(skill=skill)
    return {"marker": marker,
            "title": f"Skill {location['plugin']}/{skill} is being removed as unused",
            "body": (f"{marker}\n@{NOTICE_OWNER}: the skill `{location['plugin']}/{skill}` "
                     f"is being removed from adam-agentskills as **unused** as of {as_of}: "
                     f"{unused['why']}.\n\n{_unused_figures(unused)}\n\n"
                     "Removal pull request: {removal_pr} (auto-merges once its checks "
                     "pass).\n\n**To reverse it:** before it merges, close that pull "
                     "request. After it merges, run "
                     f"`{RESTORE_COMMAND.format(skill=skill)}` in an adam-agentskills "
                     "checkout on a fresh branch from main (it restores the directory from "
                     "the removal commit's parent, bumps MINOR and adds a `restore` entry), "
                     "or press **Revert** on the merged pull request."
                     + (f"\n\nWorkflow run: {run_url}" if run_url else "")
                     + "\n\nFiled by scripts/retire_skill.py on the scheduled workflow."
                       "\n\n" + AGENT_MARKER + "\n")}


def _unused_issue_body(skill, location, run_url, unused, as_of) -> str:
    """The proposal-path issue a held unused removal is recorded on."""
    run = f"\nWorkflow run: {run_url}\n" if run_url else ""
    return (f"{ISSUE_MARKER.format(skill=skill)}\n{PROPOSAL_STAMP}\n"
            f"`{skill}` is **unused** as of {as_of}: {unused['why']}.\n\n"
            f"{_unused_figures(unused)}\n\nCopy: `{location['path']}` in {REGISTRY_REPO}.\n"
            f"{run}\nFiled by scripts/retire_skill.py on the scheduled workflow.\n")


#: The issue that tells Adam a skill is being removed and how to reverse it
#: (#557; Adam, 2026-11-02, as for guidance sections). `{removal_pr}` is
#: filled once the pull request exists.
SKILL_NOTICE_MARKER = "<!-- skills-evals:removed-skill:{skill} -->"


def skill_notice(gates: dict, skill: str, location: dict, run_url: str | None) -> dict:
    """The removal notice (#557): an issue here that mentions the owner,
    links the removal pull request and says how to reverse it."""
    verdict = gates["skills"][skill]
    marker = SKILL_NOTICE_MARKER.format(skill=skill)
    return {"marker": marker,
            "title": f"Skill {location['plugin']}/{skill} is being removed automatically (#557)",
            "body": (f"{marker}\n@{NOTICE_OWNER}: the skill `{location['plugin']}/{skill}` "
                     f"is being removed from adam-agentskills: its verdict is **retire** as of "
                     f"{gates['as_of']} ({verdict.get('reason')}). The rule is 90% confidence "
                     "that it does not improve results by 0.15 or more, on every cell with "
                     "room to show it (`evals/gate-policy.yml` `skills:`).\n\n"
                     "Removal pull request: {removal_pr} (auto-merges once its checks "
                     "pass).\n\n**To reverse it:** before it merges, close that pull "
                     "request. After it merges, open it and press **Revert**: GitHub opens "
                     "a pull request that restores the skill, its layout and README rows "
                     "and the bundle version; merge that. The removal is recorded as a "
                     f"`remove` entry in adam-agentskills' `{IMPACT_FILE}` and on the "
                     "explorer's list of removed skills.\n\n"
                     + evidence(gates, skill)
                     + (f"\n\nWorkflow run: {run_url}" if run_url else "")
                     + "\n\nFiled by scripts/retire_skill.py on the scheduled workflow."
                       "\n\n" + AGENT_MARKER + "\n")}


def record_shipped(checkout: Path, name: str) -> list:
    """Add `<plugin>/<skill>` to adam-agentskills' append-only ledger of
    shipped names (`SHIPPED_LEDGER`, adam-agentskills#133) when it is not
    listed yet, in that file's own form (sorted lists, two-space JSON, one
    trailing newline). The paths to stage: none when the registry has no
    ledger or already lists the name."""
    path = checkout / SHIPPED_LEDGER
    if not path.exists():
        return []
    contained(checkout, ["scripts", SHIPPED_LEDGER])
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise RetireError(f"cannot read {SHIPPED_LEDGER}") from None
    if not isinstance(doc, dict) or not isinstance(doc.get("skills"), list) \
            or not all(isinstance(n, str) for n in doc["skills"]):
        raise RetireError(f"{SHIPPED_LEDGER} has no list of skills")
    if name in doc["skills"]:
        return []
    doc["skills"] = sorted([*doc["skills"], name])
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return [SHIPPED_LEDGER]


def prepare_branch(checkout: Path, action: dict) -> None:
    """The removal commit, and the lock re-pin when the plugin is locked, on
    a new branch of `checkout`, which must be clean."""
    if _git(checkout, "status", "--porcelain"):
        raise RetireError(f"the {TARGET} checkout has uncommitted changes")
    contained(checkout, ["plugins", f"plugins/{action['plugin']}",
                         f"plugins/{action['plugin']}/skills", action["path"],
                         f"plugins/{action['plugin']}/.claude-plugin", *action["versions"],
                         "docs", IMPACT_FILE])
    check_registry(checkout, action, action["skill"])
    layout = layout_without(checkout, action["plugin"], action["skill"])
    _git(checkout, "checkout", "-b", action["branch"])
    _git(checkout, "rm", "-r", "-q", "--", action["path"])
    for rel, (old, new) in action["versions"].items():
        path = checkout / rel
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or doc.get("version") != old:
            raise RetireError(f"{rel} changed under the plan")
        text = path.read_text(encoding="utf-8")
        needle = f'"version": "{old}"'
        if text.count(needle) != 1:
            raise RetireError(f"{rel}: its version is not written once as {needle}")
        path.write_text(text.replace(needle, f'"version": "{new}"'), encoding="utf-8")
    impact = checkout / IMPACT_FILE
    try:
        text = impact.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise RetireError(f"cannot read {IMPACT_FILE}") from None
    impact.write_text(insert_entry(text, action["impact_entry"]), encoding="utf-8")
    (checkout / LAYOUT_FILE).write_text(layout, encoding="utf-8")
    ledger = record_shipped(checkout, f"{action['plugin']}/{action['skill']}")
    run_registry_script(checkout, README_GENERATOR)
    _git(checkout, "add", "--", IMPACT_FILE, LAYOUT_FILE, README_FILE, *action["versions"],
         *ledger)
    if action.get("removal_reason") == "unused":
        _commit(checkout,
                f"Remove {action['plugin']}/{action['skill']}: unused\n\n"
                "skills-evals' removal policy found no use of the skill, and its description "
                "has cost more context than one use is worth.")
    else:
        _commit(checkout,
                f"Remove {action['plugin']}/{action['skill']}: no benefit on every roster model\n\n"
                "skills-evals#70's scheduled retirement found no benefit in every cell at "
                "the retire confidence level.")
    if action.get("repin"):
        run_registry_script(checkout, LOCK_GENERATOR, "--repin")
        run_registry_script(checkout, LOCK_GENERATOR, "--check-current")
        _git(checkout, "add", "--", LOCK_FILE)
        _commit(checkout, f"Re-pin skills.lock after removing {action['plugin']}/"
                          f"{action['skill']}\n\n"
                          "The lock pinned a commit that still has the skill, so its "
                          "--check-current would fail; it now pins the removal commit.")
    if _git(checkout, "status", "--porcelain"):
        raise RetireError(f"the {TARGET} checkout has changes the removal did not commit")


def _commit(checkout: Path, message: str) -> None:
    """A commit by the bot identity, with the fleet's agent trailer (as the
    improvement gate's commits carry it)."""
    _git(checkout, "-c", f"user.name={COMMIT_NAME}", "-c", f"user.email={COMMIT_EMAIL}",
         "commit", "-q", "-m", f"{message}\n\n{AGENT_TRAILER}")


def commands(action: dict) -> list:
    """The writes `execute` makes, for a dry run."""
    kind = action["action"]
    if kind == "create-issue":
        return [["gh", "issue", "create", "-R", EVALS_REPO, "--title", action["title"],
                 *(["--label", action["label"]] if action.get("label") else []),
                 "--body-file", "-"]]
    if kind == "update-issue":
        return [*_cap_commands(action), ["gh", "issue", "edit", str(action["issue"]), "-R",
                                         EVALS_REPO, "--body-file", "-"],
                *([["gh", "api", "-X", "POST",
                    f"repos/{EVALS_REPO}/issues/{action['issue']}/labels",
                    "-f", f"labels[]={action['label']}"]] if action.get("label") else [])]
    if kind == "removal":
        return [["git", "checkout", "-b", action["branch"]],
                ["git", "rm", "-r", "--", action["path"]],
                *[["edit", rel, f"version {old} -> {new}"]
                  for rel, (old, new) in action["versions"].items()],
                ["edit", IMPACT_FILE, "insert the entry"],
                ["edit", LAYOUT_FILE, f"drop {action['skill']}"],
                ["python3", README_GENERATOR],
                ["git", "commit"],
                *([["python3", LOCK_GENERATOR, "--repin"],
                   ["python3", LOCK_GENERATOR, "--check-current"],
                   ["git", "commit"]] if action.get("repin") else []),
                REVIEW_COMMAND,
                DOOR_COMMAND,
                *_push_commands(action),
                ["git", "merge-base", "--is-ancestor", "HEAD",
                 f"refs/remotes/origin/{action['branch']}"],
                ["gh", "pr", "create", "-R", REGISTRY_REPO, "--base", "main",
                 "--head", action["branch"], "--title", action["title"], "--body-file", "-"],
                ["gh", "api", "-X", "POST",
                 f"repos/{REGISTRY_REPO}/issues/<new pull request number>/labels",
                 "-f", f"labels[]={AGENT_LABEL}"],
                *review_commands(REGISTRY_REPO),
                ["gh", "pr", "merge", "<new pull request url>", "-R", REGISTRY_REPO,
                 "--auto", "--merge", "--match-head-commit", "<removal head sha>"],
                ["gh", "pr", "view", "<new pull request url>", "-R", REGISTRY_REPO,
                 "--json", "autoMergeRequest"],
                ["gh", "issue", "create", "-R", EVALS_REPO, "--title",
                 action["notice"]["title"], "--label", AGENT_LABEL, "--body-file", "-"]]
    return []


def _cap_commands(action: dict) -> list:
    """The dry run's line for the one comment the pause cap posts (R7-4),
    made before the body edit that records CAP_MARKER (R8-4): if the comment
    fails, the body still lacks the marker, so the next run posts it."""
    if not action.get("cap_comment"):
        return []
    return [["gh", "issue", "comment", str(action["issue"]), "-R", EVALS_REPO,
             "--body-file", "-"]]


def _push_commands(action: dict) -> list:
    """The dry run's push lines: the branch must not exist yet (`default_push`
    refuses one that does, unless its tip is a paused removal's head, whose
    delete it retries first, R7-2), then a plain push."""
    branch = action["branch"]
    retry = ([["git", "push", f"--force-with-lease=refs/heads/{branch}:<its tip, if one "
               "of paused_heads>", "origin", f":refs/heads/{branch}"]]
             if action.get("paused_heads") else [])
    return [["git", "ls-remote", "origin", f"refs/heads/{branch}"], *retry,
            ["git", "push", "origin", f"HEAD:refs/heads/{branch}"]]


def _cap_comment(action: dict, gh) -> str:
    """Post the pause cap's one comment (R7-4); the status line's tail."""
    if not action.get("cap_comment"):
        return ""
    gh(_cap_commands(action)[0][1:], action["cap_comment"])
    return ", and commented that the loop stopped opening removals"


def open_proposal_note(gh, found: dict, subject: str, url: str, target: str) -> str:
    """Comment, best effort, on each open proposal issue of a subject whose
    removal `url` has just opened (R9-1): its body says no removal pull
    request is opened, and closing it still declines this one. The status
    line's tail."""
    kind = "removal" if target == "skill" else "guidance removal"
    note = (f"The automatic {kind} pull request {url} is now open for `{subject}` and "
            "auto-merges once its checks pass: the reason this issue gave for only proposing "
            "the removal no longer holds. Closing this issue still declines it: the next "
            "withdrawal pass (before each daily run and after every ingest) turns its "
            "auto-merge off and closes it as a decision, if it has not merged by then. "
            f"{LATEST_WINS} To stop it at once, close the pull request yourself. Rule: "
            f"[ADR 0014]({ADR}).\n\n{AGENT_MARKER}\n")
    done = []
    for number in [n for n in found["open"] if n in found["proposals"]]:
        try:
            gh(["issue", "comment", str(number), "-R", EVALS_REPO, "--body-file", "-"], note)
            done.append(f"#{number}")
        except Exception:  # noqa: BLE001 - its text may quote a response
            done.append(f"#{number} (failed)")
    return f", and commented on its open proposal issue {', '.join(done)}" if done else ""


def _proposal_note(gh, marker: str, subject: str, url: str, target: str) -> str:
    """`open_proposal_note` after a fresh read of the subject's issues
    (`guidance_issues` with `marker`); an unreadable list is named, never
    raised: the removal has opened."""
    try:
        found = guidance_issues(gh, marker)
    except Exception:  # noqa: BLE001
        return ", and could not read its proposal issue"
    return open_proposal_note(gh, found, subject, url, target)


# ---------------------------------------------------------------------------
# The adversarial review (skills-evals#917; scripts/removal_review.py). Both
# removal paths review the prepared branch before the push, open the pull
# request with the review's section in its body, read the body back, and arm
# auto-merge only on a `Adversarial-review: pass <run url>` line. A guidance
# removal the review does not pass is opened unarmed, which the withdrawal
# pass reads as a person's hold, and the removal notice says it waits for
# Adam. A skill removal is held before the push instead (`_hold`, below).

#: The line a block puts in the removal notice in place of "auto-merges".
BLOCKED_NOTE = ("**The adversarial review blocked this removal**, so auto-merge is off "
                "and the pull request waits for you: its `## Adversarial review` section "
                "lists the findings. Merge it by hand to accept the removal, or close it "
                "to decline.\n\n")


def review_commands(repo: str) -> list:
    """The dry run's lines after the pull request opens: the body's
    read-back. Auto-merge follows only on a pass."""
    return [["gh", "pr", "view", "<new pull request url>", "-R", repo, "--json", "body"],
            ["only on Adversarial-review: pass"]]


#: The dry run's line for the review, which runs on the prepared branch
#: before the push, so the body is opened with its section.
REVIEW_COMMAND = ["claude", "-p", "--model", removal_review.MODEL, "--tools",
                  removal_review.TOOLS, "<one fresh reviewer per round, until the stop rule>"]


#: The dry run's line for adam-agentskills' one-way-door check, run on the
#: prepared branch after a passing review and before the push.
DOOR_COMMAND = ["python3", "<base>:" + loop_door_check.CHECK, "--base", "<base>", "--head",
                "<removal head sha>", "<as the loop pull request; only a pass is pushed>"]

# adam-agentskills#134: the registry's required `pytest` job fails a
# `retire-skill/` pull request that carries an `Adversarial-review: block`
# line, or steps outside ADR 0021, and a red loop pull request holds the
# loop's one slot. So a removal the review does not pass, or that the
# registry's own check (run here from its default branch) would fail, is
# never pushed: the skill's proposal issue says why and waits for a person.
# While it is open no removal is reviewed or opened again (`plan`); closing
# it declines the removal, as closing any proposal issue does.
HELD_MARKER = "<!-- skills-evals:retirement-held -->"
HELD_SLOT = "<!-- skills-evals:retirement-held-details -->"
HELD_REASON = ("a check run before the push held the removal (the adversarial review, "
               "or adam-agentskills' one-way-door check; details below)")
HELD_HOW = ("**To remove it anyway:** remove it by hand on a branch outside `retire-skill/` "
            "in adam-agentskills, then close this issue. **To keep it:** close this "
            "issue, which declines the removal. While this issue is open, no removal "
            "is reviewed or opened again.")


def held_details(result: dict | None, errors: list, run_url: str) -> str:
    """The issue's details: the review's section, or the door check's
    messages in a fence (paths and names only, flattened and capped)."""
    if result is not None:
        return removal_review.section(result, run_url) + "\n" + HELD_HOW
    return ("## One-way-door check\n\nadam-agentskills' "
            "`scripts/check_one_way_doors.py` (adam-agentskills#134) would fail the "
            "removal pull request:\n\n" + loop_door_check.fenced(errors)
            + "\n\n" + HELD_HOW)


def _hold(gh, action: dict, details: str, why: str) -> str:
    """Record the held removal on the skill's proposal issue; nothing is pushed."""
    body = action["held_body"].replace(HELD_SLOT, details)
    if action.get("held_issue"):
        gh(["issue", "edit", str(action["held_issue"]), "-R", EVALS_REPO,
            "--body-file", "-"], body)
        return (f"held the removal of {action['skill']}: {why}; updated issue "
                f"#{action['held_issue']}, nothing pushed")
    gh(["issue", "create", "-R", EVALS_REPO, "--title", action["held_title"],
        "--label", AGENT_LABEL, "--body-file", "-"], body)
    return f"held the removal of {action['skill']}: {why}; filed an issue, nothing pushed"


def door_errors(doors, checkout: Path, base: str, head: str, branch: str,
                body: str) -> list:
    """adam-agentskills' own check on the prepared branch, as the loop pull
    request; RetireError (nothing pushed) when it cannot run."""
    try:
        return doors(checkout, base, head, branch, body)
    except loop_door_check.DoorError as exc:
        raise RetireError(f"the one-way-door check could not run: {exc}") from None


def reviewer(review, env):
    """`review`, or the real one once a reviewer can run (a RetireError
    before anything is written when it cannot)."""
    if review is not None:
        return review
    try:
        removal_review.check_ready(env)
    except removal_review.ReviewError as exc:
        raise RetireError(str(exc)) from exc

    def run(subject, checkout, base, verdict, dirs):
        return removal_review.review(subject, checkout, base, verdict, dirs,
                                     lambda text: removal_review.claude_round(text, dirs, env))
    return run


def check_review_url(action: dict) -> None:
    """The review's line links the run, so a removal needs its URL."""
    url = action.get("run_url") or ""
    if not removal_review.LINE_RE.fullmatch(f"{removal_review.LINE_PREFIX} pass {url}"):
        raise RetireError("no workflow run URL for the adversarial review's line")


def run_review(action: dict, review, subject: dict, checkout: Path, base: str,
               dirs: dict) -> dict:
    """Review the prepared branch before anything is pushed, and return the
    result with the pull request body that carries its section, so the
    registry's first CI run already reads the `Adversarial-review:` line
    (adam-agentskills#133 reads the body from the API). A review that
    raises is a block."""
    try:
        result = review(subject, checkout, base, action["verdict"], dirs)
    except Exception as exc:  # noqa: BLE001 - its text may quote model output
        result = {"outcome": "block", "rounds": [], "findings": [],
                  "why": f"the review failed ({type(exc).__name__})"}
    body = removal_review.with_section(action["body"],
                                       removal_review.section(result, action["run_url"]))
    return {**result, "body": body}


def review_passed(result: dict, url: str, repo: str, registry_gh) -> bool:
    """The opened pull request's body, read back, carries exactly one
    `Adversarial-review:` line and it is a pass, and the review passed."""
    read = registry_gh(["pr", "view", url, "-R", repo, "--json", "body", "--jq", ".body"])
    return result["outcome"] == "pass" and removal_review.has_pass(read)


def blocked_notice(notice: dict) -> dict:
    """The removal notice for a removal the review blocked."""
    marker, _, rest = notice["body"].partition("\n")
    rest = rest.replace("(auto-merges once its checks pass)",
                        "(not armed: the adversarial review blocked it)")
    return {**notice, "title": "Blocked: " + notice["title"],
            "body": f"{marker}\n{BLOCKED_NOTE}{rest}"}


def _file_notice(gh, notice: dict, url: str) -> None:
    gh(["issue", "create", "-R", EVALS_REPO, "--title", notice["title"],
        "--label", AGENT_LABEL, "--body-file", "-"],
       notice["body"].replace("{removal_pr}", url))


def execute(action: dict, registries: dict, gh, push, env, registry_gh=None,
            review=None, doors=None) -> str:
    """Make the plan's writes: skills-evals issues through `gh`,
    adam-agentskills writes through `registry_gh` (default `gh`). A removal
    is pushed only after `review` (default: removal_review's) passes and
    `doors` (default: adam-agentskills' own check) finds nothing."""
    registry_gh = registry_gh or gh
    doors = doors or loop_door_check.check
    kind = action["action"]
    if kind == "none":
        return action["reason"]
    if kind == "create-issue":
        gh(commands(action)[0][1:], action["body"])
        return f"filed an issue for {action['skill']}"
    if kind == "update-issue":
        commented = _cap_comment(action, gh)  # R8-4: before the edit that records it
        edit = [c for c in commands(action) if c[:3] == ["gh", "issue", "edit"]][0]
        gh(edit[1:], action["body"])
        if action.get("label"):
            gh(["api", "-X", "POST", f"repos/{EVALS_REPO}/issues/{action['issue']}/labels",
                "-f", f"labels[]={action['label']}"])
        return f"updated issue #{action['issue']} for {action['skill']}" + commented
    check_auto_env(env)
    check_review_url(action)
    review = reviewer(review, env)
    checkout = Path(registries[TARGET]["path"])
    base = _git(checkout, "rev-parse", "HEAD").strip()
    prepare_branch(checkout, action)
    head = _git(checkout, "rev-parse", "HEAD").strip()
    subject = {"target": "skill", "name": action["skill"], "path": action["path"],
               "plugin": action["plugin"]}
    dirs = {**{name: Path(r["path"]) for name, r in registries.items()},
            "skills-evals": REPO_ROOT}
    result = run_review(action, review, subject, checkout, base, dirs)
    if result["outcome"] != "pass":
        return _hold(gh, action, held_details(result, [], action["run_url"]),
                     f"the adversarial review did not pass ({result['why']})")
    errors = door_errors(doors, checkout, base, head, action["branch"], result["body"])
    if errors:
        return _hold(gh, action, held_details(None, errors, action["run_url"]),
                     "adam-agentskills' one-way-door check would fail it")
    push(checkout, action["branch"], action.get("paused_heads") or [])
    url = registry_gh(["pr", "create", "-R", REGISTRY_REPO, "--base", "main",
                       "--head", action["branch"], "--title", action["title"],
                       "--body-file", "-"], result["body"]).strip()
    match = PR_URL_RE.fullmatch(url)
    if not match:
        raise RetireError("creating the pull request printed no pull request URL")
    # Labeled before auto-merge: a pull request that could not be marked as
    # the loop's stays open for a person instead of merging.
    registry_gh(["api", "-X", "POST", f"repos/{REGISTRY_REPO}/issues/{match.group(1)}/labels",
                 "-f", f"labels[]={AGENT_LABEL}"])
    if not review_passed(result, url, REGISTRY_REPO, registry_gh):
        _file_notice(gh, blocked_notice(action["notice"]), url)
        return (f"opened {url} unarmed: the adversarial review did not pass "
                f"({result['why']}); filed the removal notice")
    registry_gh(["pr", "merge", url, "-R", REGISTRY_REPO, "--auto", "--merge",
                 "--match-head-commit", head])
    method = registry_gh(["pr", "view", url, "-R", REGISTRY_REPO, "--json",
                          "autoMergeRequest", "--jq",
                          '.autoMergeRequest.mergeMethod // ""']).strip()
    if method != "MERGE":
        raise RetireError(f"auto-merge (merge commit) is not enabled on {url}")
    # The notice goes out once the removal is armed, through the job's own
    # token (skills-evals issues), never the registry one (#557).
    _file_notice(gh, action["notice"], url)
    # R9-1: an open proposal issue said no removal is opened (existing_issues).
    told = _proposal_note(gh, ISSUE_MARKER.format(skill=action["skill"]), action["skill"],
                          url, "skill")
    return f"opened {url} with auto-merge, and filed the removal notice" + told


# ---------------------------------------------------------------------------
# Guidance sections (skills-evals#124): `--target guidance`. Kept apart from
# the skill path above; the two share only the gh/push plumbing, the issue
# lookup's shape and `insert_entry`'s neighbor `_date`.

GUIDANCE_REPO = "Adam-S-Daniel/_agent-guidance"
GUIDANCE_BRANCH_PREFIX = "retire-guidance/"
GUIDANCE_ISSUE_MARKER = "<!-- skills-evals:retire-guidance:{section} -->"
SHORTEN_ISSUE_MARKER = "<!-- skills-evals:shorten-guidance:{section} -->"
#: The issue that tells Adam a section is being removed and how to reverse
#: it (#557; Adam, 2026-11-02: "notify and track removals so I can always
#: decide to reverse something"). `{removal_pr}` is filled once the pull
#: request exists.
GUIDANCE_NOTICE_MARKER = "<!-- skills-evals:removed-guidance:{section} -->"
GUIDANCE_NOTICE_OWNER = NOTICE_OWNER
GUIDANCE_MANIFEST = "agents-md/eval-coverage.yml"
GUIDANCE_IMPACT = "docs/guidance-impact.md"
GUIDANCE_AGENTS = "AGENTS.md"
#: _agent-guidance's own fleet-memory payload: a hand-made byte copy of
#: base.md that nothing syncs (its scripts/check-fleet-guidance-mirror.js).
GUIDANCE_PAYLOAD = ".claude/hooks/fleet-guidance.md"
#: _agent-guidance's generated contributor rules and the script that builds
#: them; an older _agent-guidance has neither, and then nothing is run.
GUIDANCE_CONTRIBUTOR_SCRIPT = "scripts/build-contributor-rules.js"
GUIDANCE_CONTRIBUTOR_RULES = ".github/fleet-contributor-rules.md"
#: The heading LINE AGENTS.md is split on, never a substring of a line: the
#: managed block's own first line quotes it (_agent-guidance AGENTS.md).
REPO_SPECIFIC_LINE = "## Repo-specific additions"
DATED_HEADING_RE = re.compile(r"^\d{4}-\d{2}-\d{2} — ")


def guidance_mode(gates: dict) -> str:
    return "auto" if gates.get("guidance_retirement_mode") == "auto" else "proposal"


def guidance_block(gates: dict) -> dict:
    block = gates.get("guidance")
    if not isinstance(block, dict):
        raise RetireError("the gates file has no guidance block (a policy without "
                          "guidance:, or a compute_gates.py from before #124)")
    return block


def guidance_retiring(gates: dict) -> str | None:
    """The one section whose verdict is `retire`, re-checked exactly as a
    skill's is (`retiring`, over the guidance block)."""
    return retiring({**gates, "skills": guidance_block(gates)})


def guidance_shortening(gates: dict) -> list:
    """Sections whose verdict is `shorten-or-merge`, by name."""
    names = sorted(n for n, v in guidance_block(gates).items()
                   if isinstance(v, dict) and v.get("verdict") == "shorten-or-merge")
    for name in names:
        if not SKILL_RE.fullmatch(name):
            raise RetireError("a shorten-or-merge section's name is not a section id")
    return names


def guidance_open_prs(gh) -> list:
    text = gh(["api", "--paginate",
               f"repos/{GUIDANCE_REPO}/pulls?state=open&per_page=100",
               "--jq", ".[] | {number: .number, head: .head.ref, url: .html_url}"])
    return [p for p in _json_lines(text)
            if isinstance(p.get("head"), str) and p["head"].startswith(GUIDANCE_BRANCH_PREFIX)]


def guidance_closed_removal_prs(gh, section: str) -> list:
    """Closed _agent-guidance pull requests from `retire-guidance/<section>`,
    with the fields `deciding` reads: merged or closed by a person, the
    section is decided, as for a skill; one the loop withdrew is not."""
    owner = GUIDANCE_REPO.split("/")[0]
    text = gh(["api", "--paginate",
               f"repos/{GUIDANCE_REPO}/pulls?state=closed&per_page=100"
               f"&head={owner}:{GUIDANCE_BRANCH_PREFIX}{section}",
               "--jq", CLOSED_JQ])
    return with_closer(gh, GUIDANCE_REPO, [
        p for p in _json_lines(text)
        if p.get("head") == f"{GUIDANCE_BRANCH_PREFIX}{section}"])


def guidance_issues(gh, marker: str) -> dict:
    """As `existing_issues`, for any marker, plus `capped`: the issues
    whose body records the pause cap's comment (`CAP_MARKER`, R11-1), and
    `closed_at`: each closed issue's close time as the API gives it (""
    when it gives none), which a decline compares with a person's arm
    (round 13, `persons_arm`). The close reason (`state_reason`) is not
    read: any close declines."""
    text = gh(["api", "--paginate",
               f"repos/{EVALS_REPO}/issues?state=all&per_page=100",
               "--jq", ".[] | select(.pull_request == null) | "
                       "{number: .number, body: (.body // \"\"), "
                       "author: .user.login, state: .state, "
                       "closed_at: (.closed_at // \"\"), "
                       "labels: [(.labels // [])[] | .name]}"])
    found = {"open": [], "closed": [], "proposals": [], "capped": [], "held": [], "agent": []}
    closed_at = {}
    labels = {}
    for item in _json_lines(text):
        if item.get("author") != ISSUE_AUTHOR or not isinstance(item.get("body"), str) \
                or marker not in item["body"]:
            continue
        number, state = item.get("number"), item.get("state")
        if type(number) is not int or number < 1 or state not in ("open", "closed"):
            raise RetireError("an issue record from the API is malformed")
        found[state].append(number)
        names = item.get("labels")
        labels[number] = [n for n in names if isinstance(n, str)] \
            if isinstance(names, list) else []
        if state == "closed":
            closed_at[number] = item.get("closed_at")
        if issue_origin(item["body"]) != "withdrawal":
            found["proposals"].append(number)
        if CAP_PREFIX in item["body"]:
            found["capped"].append(number)
        if HELD_MARKER in item["body"]:
            found["held"].append(number)
        if issue_origin(item["body"]) == "agent":
            found["agent"].append(number)
    return {**{state: sorted(numbers) for state, numbers in found.items()},
            "closed_at": closed_at, "labels": labels}


def guidance_evidence(verdict: dict) -> str:
    """The in-situ cells, then the alone cells for contrast."""
    tables = []
    for title, cells in (("Whole guidance with vs without the section (decides)",
                          verdict.get("cells")),
                         ("The section alone vs no guidance (contrast)",
                          (verdict.get("alone") or {}).get("cells"))):
        rows = [f"{title}:", "", "| Fixture | Model | Class | Runs with | Runs without | "
                "Objective upper | Judge upper |", "|---|---|---|---|---|---|---|"]
        for cell in cells if isinstance(cells, list) else []:
            if not isinstance(cell, dict):
                continue
            arms = [cell.get(a) if isinstance(cell.get(a), dict) else {}
                    for a in ("with", "without")]
            fixture, model, cls = (cell.get(k) for k in ("fixture", "model", "class"))
            rows.append(f"| {fixture if isinstance(fixture, str) and NAME_RE.fullmatch(fixture) else 'n/a'} "
                        f"| {model if isinstance(model, str) and NAME_RE.fullmatch(model) else 'n/a'} "
                        f"| {cls if isinstance(cls, str) and NAME_RE.fullmatch(cls) else 'n/a'} "
                        f"| {arms[0].get('runs', 'n/a')} | {arms[1].get('runs', 'n/a')} | "
                        f"{_figure(cell.get('objective'), 'retire_upper')} | "
                        f"{_figure(cell.get('judge'), 'retire_upper')} |")
        tables.append("\n".join(rows))
    return "\n\n".join(tables)


def guidance_row(checkout: Path, section: str) -> dict:
    """The section's manifest row in `checkout`, every path it touches
    checked to be no symlink and inside the checkout."""
    try:
        rows = guidance.load_manifest(checkout)
        row = guidance.find_row(rows, section, checkout)
    except guidance.GuidanceError:
        raise RetireError(f"{section}: no readable manifest row in the "
                          "_agent-guidance checkout") from None
    rel = row["file"]
    if rel != "agents-md/base.md" and not re.fullmatch(r"agents-md/sections/[a-z0-9-]+\.md", rel):
        raise RetireError(f"{section}: its file {rel!r} is neither base.md nor a sections file")
    contained(checkout, ["agents-md", "agents-md/sections", rel, GUIDANCE_MANIFEST, "docs",
                         GUIDANCE_IMPACT, GUIDANCE_AGENTS, "scripts", ".claude",
                         ".claude/hooks", GUIDANCE_PAYLOAD])
    return row


def _read_exact(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write_exact(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def guidance_without_section(text: str, heading: str) -> str | None:
    """`text` with the `##` extent named `heading` removed (harness/guidance.py
    `h2_extents`, the arithmetic check-guidance-coverage.js uses), or None
    when it was the file's only `##`, so the file goes."""
    spans = guidance.h2_extents(text)
    hits = [s for s in spans if s["heading"] == heading]
    if len(hits) != 1:
        raise RetireError(f"heading {heading!r} is not in its file exactly once")
    if len(spans) == 1:
        return None
    return text[:hits[0]["start"]] + text[hits[0]["end"]:]


def manifest_without_row(text: str, section: str) -> str:
    """The manifest with `section`'s row deleted, comments and layout kept:
    the row's lines are found on the composed YAML tree (its sequence item's
    start, to the next item's start or the end), never by a line scan."""
    try:
        doc = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        raise RetireError(f"{GUIDANCE_MANIFEST} is not valid YAML") from None
    if not isinstance(doc, yaml.SequenceNode):
        raise RetireError(f"{GUIDANCE_MANIFEST} is not a YAML list")
    items = doc.value
    hits = [i for i, node in enumerate(items) if isinstance(node, yaml.MappingNode)
            and any(k.value == "id" and isinstance(v, yaml.ScalarNode) and v.value == section
                    for k, v in node.value)]
    if len(hits) != 1:
        raise RetireError(f"{section}: not exactly one manifest row")
    lines = text.splitlines(keepends=True)
    start = items[hits[0]].start_mark.line
    end = items[hits[0] + 1].start_mark.line if hits[0] + 1 < len(items) else len(lines)
    return "".join(lines[:start] + lines[end:])


def guidance_impact_entry(gates: dict, section: str, run_url: str | None) -> str:
    """A typed `remove` entry whose Eval: line is a real result for
    check-guidance-touch.js: the fixtures, the pooled run count as `n=` and
    the policy."""
    verdict = guidance_block(gates)[section]
    cells = verdict["cells"]
    fixtures = sorted({c.get("fixture") or "(flat)" for c in cells})
    runs = _runs(cells)
    where = f"workflow run {run_url}" if run_url else "the scheduled workflow"
    return (f"## {_date(gates['as_of'])} — {section} — remove\n"
            f"- Motivation: skills-evals#124's retirement verdict is `retire`: the whole "
            f"guidance with and without the section shows no benefit in every cell "
            f"({len(fixtures)} fixture(s) x {len(gates['roster_models'])} roster model(s)) "
            f"at the retire confidence level.\n"
            f"- Change: removed the section and its eval-coverage.yml row, by "
            f"skills-evals' scheduled retirement ({where}).\n"
            f"- Eval: n={runs} pooled arm runs (full vs full-minus-section) as of "
            f"{gates['as_of']}, fixtures "
            f"{', '.join(f'evals/guidance/{section}/{f}' for f in fixtures)}, policy "
            f"evals/gate-policy.yml guidance:.\n"
            f"- Outcome: auto-merges once required checks pass, with no human review "
            f"(Adam, 2026-10-10 and 2026-10-25).\n")


def guidance_insert_entry(text: str, entry: str) -> str:
    """`entry` newest first: before the first dated `##` entry (after the
    file's header and its `## Entry format`), or at the end when none."""
    for span in guidance.h2_extents(text):
        if DATED_HEADING_RE.match(span["heading"]):
            return text[:span["start"]] + entry + "\n" + text[span["start"]:]
    return text.rstrip("\n") + "\n\n" + entry


def regenerate_agents_md(checkout: Path, managed: str) -> None:
    """AGENTS.md rebuilt as _agent-guidance's own AGENTS.md says: `managed`
    (build-agents-md.sh's stdout) with its trailing newlines stripped, a
    newline, then the file from its `## Repo-specific additions` heading
    LINE on, trailing newlines stripped, and one closing newline."""
    path = checkout / GUIDANCE_AGENTS
    lines = _read_exact(path).split("\n")
    marks = [i for i, line in enumerate(lines) if line.rstrip("\r") == REPO_SPECIFIC_LINE]
    if len(marks) != 1:
        raise RetireError(f"{GUIDANCE_AGENTS} has {len(marks)} `{REPO_SPECIFIC_LINE}` "
                          "heading lines, not exactly one")
    tail = "\n".join(lines[marks[0]:]).rstrip("\n")
    _write_exact(path, managed.rstrip("\n") + "\n" + tail + "\n")


def _node_deps(checkout: Path) -> None:
    """_agent-guidance's node scripts need its locked `yaml` and `markdown-it`,
    and the workflow's checkout has no node_modules: install them, scripts
    off, when the checkout has a lockfile and they are not there yet."""
    if (checkout / "package-lock.json").is_file() \
            and not (checkout / "node_modules" / "yaml").is_dir():
        _run(checkout, "npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund")


#: The only variables _agent-guidance's build scripts and `npm ci` see: the
#: job's environment holds the App token and the review credential, and
#: none of it is theirs to read.
_BUILD_ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")


def _build_env() -> dict:
    return {k: os.environ[k] for k in _BUILD_ENV_KEYS if k in os.environ}


def _run(checkout: Path, *args: str) -> str:
    proc = subprocess.run(list(args), cwd=checkout, capture_output=True, text=True,
                          check=False, env=_build_env())
    if proc.returncode != 0:
        raise RetireError(f"{' '.join(args[:2])} exited {proc.returncode}")
    return proc.stdout


def guidance_issue_action(gates, section, kind, run_url, mode_reason=None) -> dict:
    """Create or update the section's issue (`kind` retire or shorten), or
    nothing when a closed one already decided it."""
    verdict = guidance_block(gates)[section]
    marker = (GUIDANCE_ISSUE_MARKER if kind == "retire" else SHORTEN_ISSUE_MARKER).format(
        section=section)
    return {"marker": marker, "section": section, "kind": kind,
            "title": (f"Retire guidance section {section}: no marginal benefit on every "
                      "roster model (#124)" if kind == "retire" else
                      f"Shorten or merge guidance section {section}: it helps only alone "
                      "(#124)"),
            "body": (f"{marker}\n" + (f"{PROPOSAL_STAMP}\n" if kind == "retire" else "")
                     + f"The guidance verdict for `{section}` is "
                     f"**{verdict.get('verdict')}** as of {gates['as_of']}: "
                     f"{verdict.get('reason')}.\n\n"
                     + ((f"`evals/gate-policy.yml` sets `guidance: retirement_mode: auto`, "
                         f"but {mode_reason}, so no removal pull request is opened and a "
                         "human removes it from _agent-guidance.\n\n" if mode_reason else
                         "`evals/gate-policy.yml` sets `guidance: retirement_mode: proposal`, "
                         "so a human removes it from _agent-guidance.\n\n")
                        if kind == "retire" else "Nothing is removed: the section teaches the behavior, and the "
                        "rest of the guidance already covers it. Shorten it or merge it into "
                        "the section that covers it.\n\n")
                     + guidance_evidence(verdict)
                     + (f"\n\nWorkflow run: {run_url}" if run_url else "")
                     + "\n\nFiled by scripts/retire_skill.py --target guidance on the "
                       "scheduled workflow (#124).\n")}


def _guidance_issue(gates, section, kind, mode, mode_reason, gh, run_url,
                    withdrawn_decides=True, paused=0) -> dict:
    """The issue path's action for a section: create or update its issue,
    or nothing when a closed one already decided it (`deciding_issues`)."""
    issue = guidance_issue_action(gates, section, kind, run_url, mode_reason)
    lowered = {"mode_reason": mode_reason} if mode_reason else {}
    found = guidance_issues(gh, issue["marker"])
    decided = deciding_issues(found, withdrawn_decides, paused)
    if not found["open"] and decided:
        return {"action": "none", "mode": mode, "section": section, **lowered,
                "issue": decided[0],
                "reason": f"{section} is already decided: issue "
                          f"#{decided[0]} is closed, so none is filed again"}
    number = found["open"][0] if found["open"] else None
    return {"action": "update-issue" if number else "create-issue", "mode": mode,
            "section": section, "issue": number, **lowered, "title": issue["title"],
            "body": issue["body"]}


def guidance_plan(gates: dict, checkout: Path | None, gh, run_url: str | None = None,
                  allowed=("proposal",), fallback: bool = False) -> dict:
    """What to do for guidance, read-only. RetireError for a refusal."""
    mode = guidance_mode(gates)
    mode_reason = None
    section = guidance_retiring(gates)
    if section is None:
        shortening = guidance_shortening(gates)
        if not shortening:
            return {"action": "none", "mode": mode,
                    "reason": "no guidance section has a retire or shorten-or-merge verdict"}
        section, kind = shortening[0], "shorten"
    else:
        kind = "retire"
        if mode == "auto" and guidance_proposal_only(guidance_block(gates)[section]):
            # Evidence is incomplete, not a call for the owner (2026-11-13):
            # file nothing; the scheduler runs the alone arm. harness/gates.py
            # already reports such a section `insufficient`, so this guards a
            # verdict document that predates that.
            return {"action": "none", "mode": mode, "section": section,
                    "reason": f"{section}'s removal waits: "
                              + guidance_proposal_only(guidance_block(gates)[section])}
        if mode == "auto" and "auto" not in allowed and fallback:
            # An infrastructure failure, not a decision for the owner: file
            # nothing and fail the run, so the scheduled-run health audit
            # flags it (`main` exits 1 on `failure`).
            return {"action": "none", "mode": mode, "section": section,
                    "failure": GUIDANCE_NO_CREDENTIAL_FAILURE,
                    "reason": GUIDANCE_NO_CREDENTIAL_FAILURE}
        if mode not in allowed:
            raise RetireError(f"guidance_retirement_mode is {mode}, which this caller has "
                              f"not wired (allowed: {', '.join(allowed)})")
    if kind == "shorten" or mode == "proposal":
        # No guidance retire is lowered from `auto` any more (2026-11-13: an
        # unfinished alone pair or no credential files nothing for the
        # owner), so the pause cap and the withdrawal stamp concern only
        # the auto path below.
        return _guidance_issue(gates, section, kind, mode, mode_reason, gh, run_url)
    prs = guidance_open_prs(gh)
    if prs:
        # R8-5: as for a skill, an open removal (one a person holds by
        # turning its auto-merge off included) makes this pass wait, never fail.
        return {"action": "none", "mode": mode, "section": section,
                "reason": "a guidance removal pull request is already open in "
                          f"{GUIDANCE_REPO}, so this removal waits for it: "
                          + ", ".join(str(p.get("url")) for p in prs)}
    closed, paused = deciding(guidance_closed_removal_prs(gh, section))
    if closed:
        return {"action": "none", "mode": mode, "section": section,
                "reason": f"{section} is already decided: removal pull request "
                          f"{closed[0].get('url')} is closed, so none is opened again"}
    issues = guidance_issues(gh, GUIDANCE_ISSUE_MARKER.format(section=section))
    decline = declined(issues, section, mode, "section")
    if decline:
        return decline
    capped = len(paused) >= MAX_LOOP_PAUSES
    if capped and not cap_owed(issues):  # R11-1: else the open issue gets it first
        if issues["closed"]:
            return capped_decided(issues, mode, "section", section, len(paused))
    if capped:
        mode_reason = paused_reason(len(paused))
        _lowered(mode_reason, allowed)
        return cap_notice(_guidance_issue(gates, section, kind, "proposal", mode_reason, gh,
                                          run_url), gh, section, len(paused))
    if checkout is None:
        raise RetireError("no _agent-guidance checkout was given (--guidance PATH)")
    row = guidance_row(checkout, section)
    verdict = guidance_block(gates)[section]
    return {"action": "guidance-removal", "mode": mode, "section": section,
            "notice": guidance_notice(gates, section, row, run_url),
            "run_url": run_url,
            "verdict": f"retire as of {gates['as_of']}: {verdict.get('reason')}",
            "file": row["file"], "heading": row["heading"],
            "branch": f"{GUIDANCE_BRANCH_PREFIX}{section}",
            "paused_heads": paused_heads(paused),
            "impact_entry": guidance_impact_entry(gates, section, run_url),
            "title": f"Remove guidance section {section}: no marginal benefit "
                     "(skills-evals#124)",
            "body": (f"Removes the `## {row['heading']}` section of `{row['file']}` "
                     f"and its `{GUIDANCE_MANIFEST}` row: its verdict in "
                     f"[skills-evals#124](https://github.com/{EVALS_REPO}/issues/124) is "
                     f"**retire** as of {gates['as_of']} ({verdict.get('reason')}).\n\n"
                     f"{guidance_evidence(verdict)}\n\nAdds a `{GUIDANCE_IMPACT}` `remove` "
                     f"entry and regenerates `{GUIDANCE_AGENTS}`.\n\nThis pull request "
                     "auto-merges once required checks pass, with no human review "
                     "(Adam, 2026-10-10 and 2026-10-25)."
                     + (f"\n\nWorkflow run: {run_url}" if run_url else "")
                     + "\n\nOpened by skills-evals' scripts/retire_skill.py --target "
                       "guidance on its scheduled workflow.\n\n" + AGENT_MARKER + "\n")}


def guidance_notice(gates: dict, section: str, row: dict, run_url: str | None) -> dict:
    """The removal notice (#557): an issue in skills-evals that mentions the
    owner, links the removal pull request (`{removal_pr}`) and says how to
    reverse it in one click."""
    verdict = guidance_block(gates)[section]
    marker = GUIDANCE_NOTICE_MARKER.format(section=section)
    return {"marker": marker,
            "title": f"Guidance section {section} is being removed automatically (#557)",
            "body": (f"{marker}\n@{GUIDANCE_NOTICE_OWNER}: the guidance section `{section}` "
                     f"(`## {row['heading']}` in `{row['file']}`) is being removed: its "
                     f"verdict is **retire** as of {gates['as_of']} ({verdict.get('reason')}). "
                     "The rule is 90% confidence that it does not improve results by 0.15 "
                     "or more beside the current rest of the guidance, on every cell with "
                     "room to show it (`evals/gate-policy.yml` `guidance:`).\n\n"
                     "Removal pull request: {removal_pr} (auto-merges once its checks "
                     "pass).\n\n**To reverse it:** before it merges, close that pull "
                     "request. After it merges, open it and press **Revert**: GitHub opens "
                     "a pull request that restores the section, its coverage row and the "
                     "regenerated files; merge that. The removal is recorded as a `remove` "
                     f"entry in `{GUIDANCE_IMPACT}` and on the explorer's list of removed "
                     "sections.\n\n"
                     + guidance_evidence(verdict)
                     + (f"\n\nWorkflow run: {run_url}" if run_url else "")
                     + "\n\nFiled by scripts/retire_skill.py --target guidance on the "
                       "scheduled workflow.\n\n" + AGENT_MARKER + "\n")}


def guidance_prepare_branch(checkout: Path, action: dict) -> None:
    """The removal commit on a new branch of `checkout`, which must be
    clean: the section, its row, the bytes, the impact entry, AGENTS.md."""
    if _git(checkout, "status", "--porcelain"):
        raise RetireError("the _agent-guidance checkout has uncommitted changes")
    row = guidance_row(checkout, action["section"])
    if row["file"] != action["file"] or row["heading"] != action["heading"]:
        raise RetireError("the manifest row changed under the plan")
    _git(checkout, "checkout", "-q", "-b", action["branch"])
    source = checkout / row["file"]
    remaining = guidance_without_section(_read_exact(source), row["heading"])
    if remaining is None:
        _git(checkout, "rm", "-q", "--", row["file"])
    else:
        _write_exact(source, remaining)
        if row["file"] == "agents-md/base.md":
            (checkout / GUIDANCE_PAYLOAD).write_bytes(source.read_bytes())
    manifest = checkout / GUIDANCE_MANIFEST
    _write_exact(manifest, manifest_without_row(_read_exact(manifest), action["section"]))
    _node_deps(checkout)
    _run(checkout, "node", "scripts/check-guidance-coverage.js", "--write-bytes")
    impact = checkout / GUIDANCE_IMPACT
    _write_exact(impact, guidance_insert_entry(_read_exact(impact), action["impact_entry"]))
    regenerate_agents_md(checkout, _run(checkout, "bash", "scripts/build-agents-md.sh"))
    rules = (checkout / GUIDANCE_CONTRIBUTOR_SCRIPT).is_file()
    if rules:
        _run(checkout, "node", GUIDANCE_CONTRIBUTOR_SCRIPT, "--write")
    _git(checkout, "add", "-A", "--", "agents-md", GUIDANCE_IMPACT, GUIDANCE_AGENTS,
         GUIDANCE_PAYLOAD, *([GUIDANCE_CONTRIBUTOR_RULES] if rules else []))
    _git(checkout, "-c", f"user.name={COMMIT_NAME}", "-c", f"user.email={COMMIT_EMAIL}",
         "commit", "-q", "-m",
         f"Remove guidance section {action['section']}: no marginal benefit\n\n"
         "skills-evals#124's scheduled retirement found no benefit of the whole "
         "guidance with the section over it without, in every cell at the retire confidence level."
         f"\n\n{AGENT_TRAILER}")


def guidance_commands(action: dict) -> list:
    """The writes `guidance_execute` makes, for a dry run."""
    kind = action["action"]
    if kind == "create-issue":
        return [["gh", "issue", "create", "-R", EVALS_REPO, "--title", action["title"],
                 "--body-file", "-"]]
    if kind == "update-issue":
        return [*_cap_commands(action), ["gh", "issue", "edit", str(action["issue"]), "-R",
                                         EVALS_REPO, "--body-file", "-"]]
    if kind == "guidance-removal":
        return [["git", "checkout", "-b", action["branch"]],
                ["edit", action["file"], f"remove ## {action['heading']}"],
                *([["copy", "agents-md/base.md", GUIDANCE_PAYLOAD]]
                  if action["file"] == "agents-md/base.md" else []),
                ["edit", GUIDANCE_MANIFEST, f"delete row {action['section']}"],
                ["npm", "ci", "--ignore-scripts", "(when node_modules is missing)"],
                ["node", "scripts/check-guidance-coverage.js", "--write-bytes"],
                ["edit", GUIDANCE_IMPACT, "insert the remove entry"],
                ["bash", "scripts/build-agents-md.sh", "> AGENTS.md (managed half)"],
                ["node", GUIDANCE_CONTRIBUTOR_SCRIPT, "--write",
                 "(when _agent-guidance has the script)"],
                ["git", "commit"],
                REVIEW_COMMAND,
                *_push_commands(action),
                ["git", "merge-base", "--is-ancestor", "HEAD",
                 f"refs/remotes/origin/{action['branch']}"],
                ["gh", "pr", "create", "-R", GUIDANCE_REPO, "--base", "main",
                 "--head", action["branch"], "--title", action["title"], "--body-file", "-"],
                ["gh", "api", "-X", "POST",
                 f"repos/{GUIDANCE_REPO}/issues/<new pull request number>/labels",
                 "-f", f"labels[]={AGENT_LABEL}"],
                *review_commands(GUIDANCE_REPO),
                ["gh", "pr", "merge", "<new pull request url>", "-R", GUIDANCE_REPO,
                 "--auto", "--merge", "--match-head-commit", "<removal head sha>"],
                ["gh", "pr", "view", "<new pull request url>", "-R", GUIDANCE_REPO,
                 "--json", "autoMergeRequest"],
                ["gh", "issue", "create", "-R", EVALS_REPO, "--title",
                 action["notice"]["title"], "--label", AGENT_LABEL, "--body-file", "-"]]
    return []


GUIDANCE_PR_URL_RE = re.compile(rf"https://github\.com/{re.escape(GUIDANCE_REPO)}/pull/(\d+)")


#: Said when a removal waits for the weekly guidance merge window (ADR 0017).
WINDOW_CLOSED = ("no removal pull request is opened: the weekly guidance merge window "
                 "(_agent-guidance ADR 0039) is closed; the schedule's Monday pass inside "
                 "it opens it")


def guidance_execute(action: dict, checkout: Path | None, gh, push, env,
                     registry_gh=None, window_open=None, review=None) -> str:
    """Make the plan's writes: skills-evals issues through `gh`,
    _agent-guidance writes through `registry_gh` (default `gh`). A removal
    pull request is opened only while the weekly merge window is open
    (`window_open(checkout)`, default guidance_merge_window.window_open): it
    is armed the moment it opens, and an unarmed one reads as a person's
    hold, so outside the window it is not opened at all."""
    registry_gh = registry_gh or gh
    window_open = window_open or guidance_merge_window.window_open
    kind = action["action"]
    if kind == "none":
        return action["reason"]
    if kind in ("create-issue", "update-issue"):
        commented = _cap_comment(action, gh)  # R8-4: before the edit that records it
        gh(guidance_commands(action)[-1][1:], action["body"])
        return (f"filed an issue for {action['section']}" if kind == "create-issue"
                else f"updated issue #{action['issue']} for {action['section']}" + commented)
    if checkout is None or not window_open(checkout):
        return WINDOW_CLOSED
    check_auto_env(env)
    check_review_url(action)
    review = reviewer(review, env)
    base = _git(checkout, "rev-parse", "HEAD").strip()
    guidance_prepare_branch(checkout, action)
    head = _git(checkout, "rev-parse", "HEAD").strip()
    subject = {"target": "guidance", "name": action["section"], "path": action["file"],
               "heading": action["heading"]}
    dirs = {"_agent-guidance": Path(checkout), "skills-evals": REPO_ROOT}
    result = run_review(action, review, subject, Path(checkout), base, dirs)
    push(checkout, action["branch"], action.get("paused_heads") or [])
    url = registry_gh(["pr", "create", "-R", GUIDANCE_REPO, "--base", "main",
                       "--head", action["branch"], "--title", action["title"],
                       "--body-file", "-"], result["body"]).strip()
    match = GUIDANCE_PR_URL_RE.fullmatch(url)
    if not match:
        raise RetireError("creating the pull request printed no pull request URL")
    # Labeled before auto-merge, as the skill path does: a pull request that
    # could not be marked as the loop's stays open for a person.
    registry_gh(["api", "-X", "POST", f"repos/{GUIDANCE_REPO}/issues/{match.group(1)}/labels",
                 "-f", f"labels[]={AGENT_LABEL}"])
    if not review_passed(result, url, GUIDANCE_REPO, registry_gh):
        _file_notice(gh, blocked_notice(action["notice"]), url)
        return (f"opened {url} unarmed: the adversarial review did not pass "
                f"({result['why']}); filed the removal notice")
    registry_gh(["pr", "merge", url, "-R", GUIDANCE_REPO, "--auto", "--merge",
                 "--match-head-commit", head])
    method = registry_gh(["pr", "view", url, "-R", GUIDANCE_REPO, "--json",
                          "autoMergeRequest", "--jq",
                          '.autoMergeRequest.mergeMethod // ""']).strip()
    if method != "MERGE":
        raise RetireError(f"auto-merge (merge commit) is not enabled on {url}")
    # The notice goes out once the removal is armed, through the job's own
    # token (skills-evals issues), never the _agent-guidance one.
    _file_notice(gh, action["notice"], url)
    told = _proposal_note(gh, GUIDANCE_ISSUE_MARKER.format(section=action["section"]),
                          action["section"], url, "guidance")
    return f"opened {url} with auto-merge, and filed the removal notice" + told


# ---------------------------------------------------------------------------
# Withdrawal (ADR 0014, round 8's known limit): `--withdraw-stale`. An open
# removal pull request the loop made is armed to auto-merge on the verdict it
# was opened on. When a later verdict no longer supports it (more runs moved
# the subject to keep or insufficient, or its removal fell to a proposal),
# the pull request is disarmed, labeled `loop-withdrawn`, recorded in the
# subject's proposal issue, told why and closed: a pause, not a decision, so
# a later `retire` opens a fresh removal. While the target's mode is `proposal` (the
# owner's switch), a removal the verdict still supports is only disarmed.
# `withdrawal_decision` decides, with no I/O; `withdraw_stale` does the calls.

#: The label the owner puts on work he has paused; a held pull request is
#: never touched (the fleet's on-hold rule).
ON_HOLD_LABEL = "on-hold"
#: The login every loop removal pull request is opened under: the
#: eval-improve GitHub App's bot (secrets EVAL_IMPROVE_APP_CLIENT_ID and
#: EVAL_IMPROVE_APP_PEM; skill-coverage.yml mints its token for both
#: adam-agentskills and _agent-guidance). Its `draft-skill/` and
#: `eval-improve/` pull requests in adam-agentskills carry this login. A
#: pull request opened by anyone else (a person, or an agent acting on a
#: proposal issue) is not the loop's, whatever its head or labels.
LOOP_AUTHOR = "skills-evals-improve[bot]"
WITHDRAWN_MARKER = "<!-- skills-evals:withdrawn-removal:{subject} -->"
DISARMED_MARKER = "<!-- skills-evals:disarmed-removal:{subject} -->"
#: The basis a removal pull request's body records on its first line
#: (`_pr_body`, `_unused_pr_body` and `guidance_plan`): "Removes ... is
#: **retire** (or **unused**) as of <the gates document's as_of> (". Matched
#: from the body's start only.
BASIS_RE = re.compile(r"Removes [^\n]*? is \*\*(?:retire|unused)\*\* as of (\S+) \(")
#: The first line of an `unused` removal (`_unused_pr_body`): the same shape
#: with `unused` for `retire`. Only this line marks the pull request as an
#: unused removal, so `withdrawal_decision` judges it by use, not by a verdict.
UNUSED_BASIS_RE = re.compile(r"Removes [^\n]*? is \*\*unused\*\* as of (\S+) \(")
#: The events that may withdraw: the daily retirement job and the pass after
#: every ingest (loop-pr-refresh.yml). Withdrawal only disarms, labels,
#: closes and files an issue; it never arms or opens anything.
WITHDRAW_EVENTS = ("schedule", "workflow_run")
#: Per target: the repository, the loop's head prefix, the gates document's
#: verdict block, and how its mode is read.
WITHDRAW_TARGETS = {
    "skill": {"repo": REGISTRY_REPO, "prefix": BRANCH_PREFIX, "block": "skills",
              "url_re": PR_URL_RE, "mode": mode_of},
    "guidance": {"repo": GUIDANCE_REPO, "prefix": GUIDANCE_BRANCH_PREFIX,
                 "block": "guidance", "url_re": GUIDANCE_PR_URL_RE, "mode": guidance_mode},
}


def _one_line(value) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


#: GitHub's `created_at` (UTC, `Z`) and the gates document's `as_of`.
_ISO_RE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)")


def _moment(value):
    """`value` (an `as_of` stamp, `YYYYMMDDTHHMMSSZ`, or an ISO 8601 time
    with its offset) as an aware datetime, or None when it is missing or
    unparseable."""
    if not isinstance(value, str):
        return None
    try:
        if re.fullmatch(r"\d{8}T\d{6}Z", value):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if _ISO_RE.fullmatch(value):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return None


def removal_support(gates: dict, entry, target: str = "skill") -> tuple:
    """Whether a verdict entry still supports an automatic removal:
    `("supported", why)`, `("unknown", why)` or `("stale", why)`.

    Supported is a `retire` (every skill's is automatic; for a section
    `guidance_proposal_only` must be None, which `guidance_plan` lowers by, so
    an unfinished alone pair is stale too). A `retire-pending` whose `raw_verdict` is
    `retire` counts as that `retire`: compute_gates' `finalize` demotes all
    but one confirmed subject per evaluation, which ranks them and says
    nothing against this one (round 1's M1). Unknown is a verdict that
    raised in compute_gates.py or a `retire` that fails the re-check."""
    if not isinstance(entry, dict) or not isinstance(entry.get("verdict"), str) \
            or not isinstance(entry.get("reason"), str) \
            or entry["reason"].startswith(compute_gates.VERDICT_RAISED):
        return "unknown", "the subject's verdict could not be computed"
    verdict = entry["verdict"]
    if verdict == "retire-pending" and entry.get("raw_verdict") == "retire":
        verdict = "retire"
    if verdict != "retire":
        return "stale", f"the verdict is {entry['verdict']}, not retire"
    try:
        retiring({**gates, "skills": {"subject": {**entry, "verdict": "retire"}}})
    except RetireError:
        return "unknown", "the subject's retire verdict is malformed"
    lowered = guidance_proposal_only(entry) if target == "guidance" else None
    if lowered is not None:
        return "stale", lowered
    return "supported", "the verdict is still retire with an automatic removal"


def _basis(body, created_at=None):
    """The `as_of` a removal pull request's body says it was opened on, as
    an aware datetime, or None. Only the loop's own opening line counts:
    the body's first line, "Removes ... is **retire** as of <as_of> (" (the
    first stamp on it), so a quote or a later line cannot supply one. A
    basis later than the pull request's `created_at` is None too: no pull
    request is opened on results newer than itself."""
    match = BASIS_RE.match(body) if isinstance(body, str) else None
    basis = _moment(match.group(1)) if match else None
    opened = _moment(created_at)
    if basis is None or opened is None or basis > opened:
        return None
    return basis


def withdrawal_decision(pr: dict, gates: dict | None, target: str = "skill",
                        unused_check=None) -> dict:
    """What to do with one open pull request, from the gates document alone.

    `{"action": "ignore" | "keep" | "disarm" | "withdraw", "why": text, ...}`:
    `ignore` for a pull request the loop did not make (head prefix, the
    `agent-authored` label and `LOOP_AUTHOR` as its author all required)
    or one held `on-hold`; `withdraw` when its subject's verdict no longer
    supports an automatic removal (`removal_support` "stale"), with the
    verdict fields the comment quotes; otherwise `disarm` while the
    target's mode is `proposal` (the one switch), else `keep`. Unknown data
    never withdraws: `gates` None, no verdict block, a subject the block
    does not list (an empty or partial block), a malformed entry or a
    verdict that raised all keep (or only disarm, in proposal mode).

    A pull request is withdrawn only by verdicts newer than the results it
    was opened on: the `as_of` its body's first line records (BASIS_RE)
    must not be later than the gates document's. A body with no parseable
    basis, or one later than its `created_at`, falls back to its
    `created_at` (PR #724 round 2's R2-1): one created after the gates
    document's `as_of` is kept, as it is when either time is missing or
    unparseable. A pass that started on older results can otherwise close
    a removal the retirement job has just opened on newer ones."""
    spec = WITHDRAW_TARGETS[target]
    head, labels = pr.get("head"), pr.get("labels")
    if not isinstance(head, str) or not head.startswith(spec["prefix"]) \
            or not isinstance(labels, list) or AGENT_LABEL not in labels \
            or pr.get("author") != LOOP_AUTHOR:
        return {"action": "ignore", "why": "not a removal pull request the loop opened"}
    if ON_HOLD_LABEL in labels:
        return {"action": "ignore", "why": f"labeled {ON_HOLD_LABEL}"}
    subject = head[len(spec["prefix"]):]
    if not SKILL_RE.fullmatch(subject):
        return {"action": "keep", "why": "its head names no subject"}
    if not isinstance(gates, dict) or not isinstance(gates.get(spec["block"]), dict):
        return {"action": "keep", "subject": subject, "why": "the verdicts are unknown"}
    block = gates[spec["block"]]
    unused_pr = (target == "skill" and isinstance(pr.get("body"), str)
                 and UNUSED_BASIS_RE.match(pr["body"]) is not None)
    if unused_pr:
        # An `unused` removal has no verdict: it is judged by use (`unused_check`).
        state, why = (unused_check(subject) if unused_check is not None
                      else ("unknown", "no usage census was given"))
    elif subject not in block:
        state, why = "unknown", "the verdicts document does not list the subject"
    else:
        state, why = removal_support(gates, block[subject], target)
    if state == "stale":
        judged = _moment(gates.get("as_of"))
        basis = _basis(pr.get("body"), pr.get("created_at"))
        if basis is not None and judged is not None:
            if basis > judged:
                return {"action": "keep", "subject": subject,
                        "why": "it was opened on newer results than these verdicts"}
        else:
            opened = _moment(pr.get("created_at"))
            if opened is None or judged is None:
                return {"action": "keep", "subject": subject,
                        "why": "its basis, its creation time or the verdicts' as_of "
                               "is unknown"}
            if opened > judged:
                return {"action": "keep", "subject": subject,
                        "why": "it was opened after the results these verdicts stand on"}
        if unused_pr:
            return {"action": "withdraw", "subject": subject, "verdict": "no longer unused",
                    "removal": None, "reason": why, "removal_reason": "", "why": why,
                    "unused": True}
        entry = block[subject]
        return {"action": "withdraw", "subject": subject, "verdict": entry["verdict"],
                "removal": entry.get("removal") if isinstance(entry.get("removal"), str)
                else None,
                "reason": _one_line(entry["reason"]),
                "removal_reason": _one_line(entry.get("removal_reason")), "why": why}
    if spec["mode"](gates) != "auto":
        return {"action": "disarm", "subject": subject,
                "why": f"the {spec['block']} retirement_mode is proposal ({why})"}
    partial = partial_withdrawal(pr, gates) if state == "supported" else None
    if partial is not None:
        entry = block[subject] if not unused_pr else {
            "verdict": "unused", "reason": why}
        return {"action": "withdraw", "subject": subject, "partial": partial,
                "verdict": entry["verdict"],
                "removal": entry.get("removal") if isinstance(entry.get("removal"), str)
                else None,
                "reason": _one_line(entry["reason"]),
                "removal_reason": _one_line(entry.get("removal_reason")),
                "why": f"a withdrawal stopped part way ({PARTIAL_WHY[partial]}), so it is "
                       "finished as a pause; the next daily run opens a fresh, armed removal"}
    return {"action": "keep", "subject": subject, "why": why}


#: R6-2: why an open loop removal whose verdict still supports it is a
#: withdrawal that stopped part way. `_act` re-reads auto-merge for
#: `disarmed` and keeps the pull request if it is armed after all.
PARTIAL_WHY = {"labeled": f"it carries the `{WITHDRAWN_LABEL}` label",
               "disarmed": "its auto-merge is off"}


def partial_withdrawal(pr: dict, gates: dict) -> str | None:
    """In `auto` mode, whether an open loop removal whose verdict supports it
    may be a withdrawal that stopped part way (R6-2): it carries
    WITHDRAWN_LABEL (`labeled`), or the listing says its auto-merge is off
    (`disarmed`, only for one opened before the results these verdicts stand
    on). A `disarmed` one is a candidate only: `_act` reads auto-merge again
    and its timeline (`loop_disarm_hold`), and keeps it unless the loop's
    own withdrawal turned auto-merge off (R7-3). Anything else, unknown data
    included, is None: the pull request is kept."""
    labels = pr.get("labels") or []
    if WITHDRAWN_LABEL in labels:
        return "labeled"
    opened, judged = _moment(pr.get("created_at")), _moment(gates.get("as_of"))
    if pr.get("armed") is False and opened is not None and judged is not None \
            and opened < judged:
        return "disarmed"
    return None


OVERRIDE = ("To remove the subject anyway, take it over from the loop: remove the "
            f"`{AGENT_LABEL}` label first (a pull request without it is not the loop's, so "
            "no later pass touches it), then restore the branch from the pull request page, "
            "then reopen it and merge it by hand.")

#: What every issue- and pull-request-facing text says about a person's arm
#: and a closed proposal issue (round 13, `persons_arm`).
LATEST_WINS = ("The latest person action wins: if a person (a user account, not a bot or "
               "an App) turns the removal pull request's auto-merge on strictly after the "
               "proposal issue is closed, the loop leaves that removal to them and it can "
               "merge; a close after a person's arm, in the same second as it, or with either "
               "time unknown declines it. The close takes effect at the next withdrawal "
               "pass, if the removal has not merged by then.")


def withdrawal_comment(decision: dict, gates: dict, run_url: str | None) -> str:
    """The comment a withdrawn pull request gets: the new verdict, why, and
    how a person overrides it."""
    subject = decision["subject"]
    removal = f", removal `{decision['removal']}`" if decision.get("removal") else ""
    now = (f"The current verdict for `{subject}` as of {gates['as_of']} is "
           f"**{decision['verdict']}**{removal}: {decision['reason']}"
           + (f" ({decision['removal_reason']})" if decision.get("removal_reason") else "")
           + f". Why this withdraws the removal: {decision['why']}.")
    if decision.get("unused"):
        now = (f"The skill `{subject}` as of {gates['as_of']}: {decision['reason']}. "
               f"Why this withdraws the removal: {decision['why']}.")
    lead = ("A withdrawal of this removal stopped part way, and this finishes it as a "
            "pause." if decision.get("partial") else
            "This removal pull request was opened because the skill was unused, and it "
            "no longer is." if decision.get("unused") else
            "This removal pull request was opened on a `retire` verdict with an automatic "
            "removal, and the subject no longer has one.")
    return (f"{WITHDRAWN_MARKER.format(subject=subject)}\n"
            f"**Withdrawn automatically.** {lead}\n\n{now}\n\n"
            "Auto-merge is turned off and the pull request is closed; then its branch will be "
            "deleted while it still points at this pull request's head (if that delete fails, "
            "the next removal for the subject retries it before it pushes). The "
            f"`{WITHDRAWN_LABEL}` label marks this as a pause, not a decision: if the "
            "verdict supports an automatic removal again, the loop opens a fresh removal "
            f"pull request (after {MAX_LOOP_PAUSES} pauses it files the proposal issue "
            "instead). To decline the removal for good, remove the "
            f"`{WITHDRAWN_LABEL}` label; a closed removal without it, or one a person "
            "closed, decides the subject. The subject's retirement issue in skills-evals "
            f"records this withdrawal. {OVERRIDE} Rule: [ADR 0014]({ADR})."
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\n" + AGENT_MARKER + "\n")


def disarm_comment(decision: dict, run_url: str | None) -> str:
    """The one comment a removal disarmed by the `proposal` switch gets."""
    return (f"{DISARMED_MARKER.format(subject=decision['subject'])}\n"
            "**Auto-merge turned off.** The retirement mode in "
            "`evals/gate-policy.yml` is `proposal`, so no removal merges without a "
            f"person: {decision['why']}. This pull request stays open; merge it by hand "
            "to remove the subject, or close it to decline. Remove the "
            f"`{AGENT_LABEL}` label before merging by hand, so no later pass touches it. "
            f"Rule: [ADR 0014]({ADR})."
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\n" + AGENT_MARKER + "\n")


def removal_prs(gh, target: str) -> list:
    """The target repository's open pull requests, each with its number,
    head branch, URL, labels, author login, `created_at` (R2-1), body (its
    basis) and whether auto-merge is on (`armed`, R6-2's partial withdrawal),
    read through the job's token.
    Whether auto-merge is armed is read later, per pull request, by
    `withdraw_stale` (`gh pr view`)."""
    repo = WITHDRAW_TARGETS[target]["repo"]
    text = gh(["api", "--paginate", f"repos/{repo}/pulls?state=open&per_page=100",
               "--jq", ".[] | {number: .number, head: .head.ref, url: .html_url, "
                       "labels: [.labels[].name], author: .user.login, "
                       "created_at: .created_at, body: (.body // \"\"), "
                       "armed: (.auto_merge != null)}"])
    return _json_lines(text)


def withdraw_commands(target: str, url: str) -> dict:
    """The calls one withdrawal or disarm makes: (state) the pull request
    must still be open; (merge) auto-merge off, then (view) read back;
    (label) WITHDRAWN_LABEL on, after (labels) the repository's labels show
    it missing and (create_label) creates it, then (pr_labels) read back;
    (comment); (close); (head) the closed pull request's head commit, which
    the branch delete is leased on. Every one of them also reads (arms) who
    turned auto-merge on (`persons_arm`); `refresh_allowed` pairs that with
    (armed), the REST read of whether it is armed now. A decline also takes
    (unlabel) WITHDRAWN_LABEL off."""
    repo = WITHDRAW_TARGETS[target]["repo"]
    return {"state": ["pr", "view", url, "-R", repo, "--json", "state", "--jq", ".state"],
            "merge": ["pr", "merge", url, "-R", repo, "--disable-auto"],
            "view": ["pr", "view", url, "-R", repo, "--json", "autoMergeRequest", "--jq",
                     '.autoMergeRequest.mergeMethod // ""'],
            "label": ["pr", "edit", url, "-R", repo, "--add-label", WITHDRAWN_LABEL],
            "labels": ["label", "list", "-R", repo, "--search", WITHDRAWN_LABEL,
                       "--json", "name", "--jq", ".[].name"],
            "create_label": ["label", "create", WITHDRAWN_LABEL, "-R", repo, "--color",
                             WITHDRAWN_LABEL_COLOR, "--description",
                             WITHDRAWN_LABEL_DESCRIPTION, "--force"],
            "pr_labels": ["pr", "view", url, "-R", repo, "--json", "labels", "--jq",
                          ".labels[].name"],
            "unlabel": ["pr", "edit", url, "-R", repo, "--remove-label", WITHDRAWN_LABEL],
            "comment": ["pr", "comment", url, "-R", repo, "--body-file", "-"],
            "close": ["pr", "close", url, "-R", repo],
            "head": ["pr", "view", url, "-R", repo, "--json", "headRefOid", "--jq",
                     ".headRefOid"],
            "timeline": ["api", "--paginate",
                         f"repos/{repo}/issues/{_number(url)}/timeline?per_page=100",
                         "--jq", TIMELINE_JQ],
            "arms": ["api", "--paginate",
                     f"repos/{repo}/issues/{_number(url)}/timeline?per_page=100",
                     "--jq", ARMS_JQ],
            "armed": ["api", f"repos/{repo}/pulls/{_number(url)}", "--jq",
                      ".auto_merge != null"],
            "closer": ["api", f"repos/{repo}/issues/{_number(url)}", "--jq",
                       '.closed_by.login // ""']}


def _number(url: str) -> str:
    """The pull request number a URL ends in."""
    return url.rstrip("/").rsplit("/", 1)[-1]


#: The timeline events `loop_disarm_hold` reads: who turned auto-merge off,
#: and the loop's comments (the proposal switch's DISARMED_MARKER), each with
#: its `created_at` (R9-2: the order is decided by time, not position).
TIMELINE_JQ = ('.[] | select(.event == "auto_merge_disabled" or .event == "commented") '
               '| {event: .event, actor: (.actor.login // ""), body: (.body // ""), '
               'created_at: (.created_at // "")}')


#: The timeline events `persons_arm` reads: who turned auto-merge on, what
#: kind of account that is (round 13: only a `User` is a person), and when.
ARMS_JQ = ('.[] | select(.event == "auto_merge_enabled") '
           '| {actor: (.actor.login // ""), type: (.actor.type // ""), '
           'created_at: (.created_at // "")}')

#: The login GitHub shows for a deleted account: its type is `User`, but no
#: person stands behind it now, so its arm is not a person's (round 13).
GHOST = "ghost"


#: The status line of a removal the loop leaves to a person (round 12).
PERSONS_ARM = "armed by a person"


def _a_persons(event: dict) -> bool:
    """Whether an `auto_merge_enabled` event (ARMS_JQ's row) is a human's
    (round 13): its actor's type is `User` and its login is neither the
    loop's (LOOP_AUTHOR) nor GHOST. A `Bot` (any App's or bot's arm,
    github-actions[bot] included), an `Organization`, a missing type, a
    missing login or a deleted account is not a person."""
    return (event.get("type") == "User" and isinstance(event.get("actor"), str)
            and event["actor"] not in ("", LOOP_AUTHOR, GHOST))


def persons_arm(registry_gh, c: dict, armed: bool, decline: dict | None = None) -> bool:
    """Whether a person's arm is in force on a removal pull request (round
    12's single rule): it is armed now (`armed`, read by the caller) AND the
    latest `auto_merge_enabled` event on its timeline (`c["arms"]`, by
    `created_at`) is a person's (`_a_persons`: a `User` other than
    LOOP_AUTHOR, round 13). Such a removal is that person's: the withdrawal
    pass does not disarm it (the `proposal` switch) or withdraw it (a stale
    verdict, or a withdrawal that stopped part way), and `refresh_allowed`
    lets it be refreshed. For those, the arm's time is compared with
    nothing else. The one comparison (round 13, "the latest person action
    wins"): when a closed proposal or legacy issue declines the subject
    (`decline`, `declined`'s result), the arm wins only when its
    `created_at` is strictly later than the decline's `closed_at`; a tie,
    or either time missing or unparseable, and the decline wins. False for
    anything not known to be a person's arm in force: not armed (the loop's
    own disarm included), an unreadable timeline, no event, a non-person's
    arm last, or a time missing or unparseable on any `auto_merge_enabled`
    event (then which arm is the latest is unknown). Two arms in the same
    second count as a person's only when every one of them is."""
    if not armed:
        return False
    closed = None
    if decline is not None:
        closed = _moment(decline.get("closed_at"))
        if closed is None:
            return False
    try:
        events = _json_lines(registry_gh(c["arms"]))
    except Exception:  # noqa: BLE001 - not known to be a person's arm
        return False
    moments = [_moment(e.get("created_at")) for e in events]
    if not events or any(m is None for m in moments):
        return False
    latest = max(moments)
    if closed is not None and latest <= closed:
        return False
    return all(_a_persons(e) for e, m in zip(events, moments) if m == latest)


def loop_disarm_hold(registry_gh, c: dict, subject: str) -> str | None:
    """Why a `disarmed` candidate (R6-2) is kept, or None when it is a
    withdrawal that stopped part way (R7-3): the latest
    `auto_merge_disabled` event on its timeline (`GET
    repos/{r}/issues/{n}/timeline`, every page, oldest first) must be
    LOOP_AUTHOR's, and the loop must not have commented DISARMED_MARKER on
    it after that event (R8-2: a marker from an earlier disarm, which a
    person re-armed since, says nothing about this one). "After" is read
    from `created_at` (R9-2): a marker created in the same second as the
    disable counts as after it, whatever order the timeline lists the two
    in, since the switch disarms and comments within a few calls; only when
    either time is missing or unparseable does the timeline's order decide.
    A person's disarm is a hold, and the proposal switch, which disarms
    with the loop's App too, leaves that comment right after its disarm
    (or, if posting it failed, the next `proposal` pass does, R8-3), so
    neither is finished as a pause. An unreadable timeline, or one with no
    such event, keeps it."""
    try:
        events = _json_lines(registry_gh(c["timeline"]))
    except Exception:  # noqa: BLE001 - unknown: leave it alone
        return "who turned its auto-merge off cannot be read"
    disabled = [i for i, e in enumerate(events) if e.get("event") == "auto_merge_disabled"]
    if not disabled or events[disabled[-1]].get("actor") != LOOP_AUTHOR:
        return "someone other than the loop turned its auto-merge off (a hold, not a withdrawal)"
    last = disabled[-1]
    when = _moment(events[last].get("created_at"))

    def after(i: int, e: dict) -> bool:
        made = _moment(e.get("created_at"))
        if when is None or made is None:
            return i > last
        return made >= when  # a same-second tie holds (R9-2)

    marker = DISARMED_MARKER.format(subject=subject)
    if any(e.get("event") == "commented" and e.get("actor") == LOOP_AUTHOR
           and isinstance(e.get("body"), str) and marker in e["body"] and after(i, e)
           for i, e in enumerate(events)):
        return "the proposal switch turned its auto-merge off"
    return None


def would_run(target: str, item: dict) -> list:
    """The dry run's list of the writes for one planned item."""
    c = withdraw_commands(target, item["url"])
    if item["action"] == "withdraw":
        branch = f"{WITHDRAW_TARGETS[target]['prefix']}{item['subject']}"
        hold = [c["timeline"]] if item.get("partial") == "disarmed" else []
        return [c["state"], c["view"], c["arms"], *hold, c["merge"], c["view"], c["label"],
                c["pr_labels"],
                ["issue", "create-or-comment", "-R", EVALS_REPO,
                 "<the subject's retirement issue>"],
                c["comment"], c["close"], c["closer"], c["head"],
                ["git", "push", f"--force-with-lease=refs/heads/{branch}:<its head>",
                 f"https://github.com/{WITHDRAW_TARGETS[target]['repo']}.git",
                 f":refs/heads/{branch}"],
                ["issue", "close", "<the subject's open removal notice>", "-R", EVALS_REPO,
                 "--reason", "not planned"],
                ["issue", "comment", "<the subject's open removal notice>", "-R", EVALS_REPO,
                 "--body-file", "-"]]
    if item["action"] == "decline":
        return [c["state"], c["view"], c["arms"], c["merge"], c["view"], c["pr_labels"],
                c["unlabel"], c["pr_labels"], c["comment"], c["close"],
                ["issue", "comment", str(item["declined"]), "-R", EVALS_REPO,
                 "--body-file", "-"],
                ["issue", "close", "<the subject's open removal notice>", "-R", EVALS_REPO,
                 "--reason", "not planned"],
                ["issue", "comment", "<the subject's open removal notice>", "-R", EVALS_REPO,
                 "--body-file", "-"]]
    if item["action"] == "disarm":
        # Armed: who armed it (`persons_arm`); already off: the timeline, for
        # the switch's comment (R8-3).
        return [c["state"], c["view"], c["arms"], c["timeline"], c["merge"], c["view"],
                c["comment"]]
    return []


def declined_decision(decision: dict, gates: dict, target: str, gh, seen: dict) -> dict:
    """`decision` turned into `decline` when the subject's retirement issues
    (read through `gh`, once per subject: `seen`) decline its removal
    (`declined`, R9-1): a person closed the proposal issue while this
    removal was open, which the retirement job's `plan` never reads while a
    loop pull request is open. A decline is a person's decision, so it
    overrides `keep`, `disarm` and `withdraw` alike, in either mode: the
    loop closes the removal as a decision rather than keeping it to merge
    or filing a withdrawal issue that would say closing it declines
    nothing. An unreadable issue list makes the item `unreadable`, which
    `_act` fails (the pull request is left as it is and the pass exits 2).
    `_act` leaves a removal under a person's arm (`persons_arm`) alone
    instead of declining it only when that arm is strictly later than the
    issue's close (`closed_at`, round 13): the latest person action wins."""
    subject = decision.get("subject")
    if not isinstance(subject, str) or not isinstance(gates, dict):
        return decision
    if subject not in seen:
        try:
            found = retirement_issues(gh, subject, target)[1]
            seen[subject] = declined(found, subject,
                                     WITHDRAW_TARGETS[target]["mode"](gates), "subject")
        except Exception as exc:  # noqa: BLE001 - its text may quote a response
            why = str(exc) if isinstance(exc, RetireError) else type(exc).__name__
            seen[subject] = {"unreadable": f"its retirement issues could not be read ({why}), "
                                           "so it is left as it is"}
    decline = seen[subject]
    if decline is None:
        return decision
    if "unreadable" in decline:
        return {"action": "unreadable", "subject": subject, "why": decline["unreadable"]}
    return {"action": "decline", "subject": subject, "declined": decline["issue"],
            "closed_at": decline.get("closed_at"),
            "why": f"its proposal issue #{decline['issue']} in skills-evals is closed, "
                   "which declines the removal"}


def withdraw_plan(gates: dict | None, prs: list, target: str, gh=None,
                  unused_check=None) -> list:
    """Each listed pull request's decision, with its number and URL; a
    `withdraw`, `disarm` or `decline` whose URL is not the target
    repository's pull request is refused rather than acted on. With `gh`,
    a subject a closed proposal issue declines is a `decline`
    (`declined_decision`, R9-1)."""
    spec = WITHDRAW_TARGETS[target]
    out, seen = [], {}
    for pr in prs:
        decision = withdrawal_decision(pr, gates, target, unused_check)
        if decision["action"] == "ignore":
            continue
        if gh is not None:
            decision = declined_decision(decision, gates, target, gh, seen)
        url, number = pr.get("url"), pr.get("number")
        match = spec["url_re"].fullmatch(url) if isinstance(url, str) else None
        if decision["action"] in ("withdraw", "disarm", "decline", "unreadable") and (
                not match or type(number) is not int or match.group(1) != str(number)):
            raise RetireError("an open pull request record from the API is malformed")
        out.append({**decision, "number": number, "url": url})
    return out


def retirement_issues(gh, subject: str, target: str) -> tuple:
    """(the marker, `{"open": [...], "closed": [...]}`) of the subject's
    retirement issues, the proposal path's."""
    if target == "skill":
        return ISSUE_MARKER.format(skill=subject), existing_issues(gh, subject)
    marker = GUIDANCE_ISSUE_MARKER.format(section=subject)
    return marker, guidance_issues(gh, marker)


def withdrawal_issue(item: dict, gates: dict, target: str, gh, run_url: str | None) -> dict:
    """The subject's retirement proposal issue, filed or commented on to
    record the withdrawal (round 1's M4): the issue `--fallback-to-proposal`
    and proposal mode use (same marker, same author), so a withdrawn subject
    is never decided in silence. The oldest open one gets `comment` as a
    comment, its body (the proposal's evidence, and its PROPOSAL_STAMP)
    left as it is (R2-6); otherwise one is filed with `body`, stamped
    WITHDRAWAL_STAMP (R8-1)."""
    subject = item["subject"]
    marker, found = retirement_issues(gh, subject, target)
    number = found["open"][0] if found["open"] else None
    if target == "skill":
        title = f"Retire skill {subject}: automatic removal withdrawn (#70)"
    else:
        title = f"Retire guidance section {subject}: automatic removal withdrawn (#124)"
    auto = WITHDRAW_TARGETS[target]["mode"](gates) == "auto"
    if auto and number in found["proposals"]:
        # R8-1: this issue is the proposal path's, so closing it declines.
        decline = ("This issue is the subject's proposal, so closing it declines the "
                   "removal: while it is closed the loop opens no removal for the subject. "
                   f"{LATEST_WINS} {OVERRIDE}")
    elif auto:
        # R6-7: in auto mode the retirement job reads this issue only once
        # the pause cap is reached (R7-4), so until then closing it declines
        # nothing.
        decline = ("While the retirement mode is `auto`, closing this issue declines nothing "
                   f"until the loop has paused {MAX_LOOP_PAUSES} removals for the subject. "
                   "To decline the removal before then, close the removal pull request "
                   "yourself (a fresh one, when the loop opens it), or remove the "
                   f"`{WITHDRAWN_LABEL}` label from that closed one: a removal a person "
                   f"closed, or one without the label, decides the subject. After "
                   f"{MAX_LOOP_PAUSES} pauses the loop stops opening removals and this issue "
                   "becomes the proposal: the loop comments here, and from then on a closed "
                   f"issue declines the removal (one already closed then declines it too). "
                   f"{OVERRIDE}")
    else:
        decline = ("To decline the removal for good, remove the "
                   f"`{WITHDRAWN_LABEL}` label from that closed pull request. {OVERRIDE} "
                   "Otherwise close this issue.")
    note = (f"The automatic removal pull request {item['url']} was withdrawn "
            f"(turned off, labeled `{WITHDRAWN_LABEL}` and closed; its branch will be "
            "deleted) "
            f"on the verdicts as of {gates['as_of']}: "
            + (f"the skill is no longer unused: {item['reason']}. Why: {item['why']}."
               if item.get("unused") else
               f"the verdict is now **{item['verdict']}**: {item['reason']}. "
               f"Why: {item['why']}.")
            + "\n\nA withdrawal is a pause, not a decision: if the "
            + ("skill is unused again" if item.get("unused") else
               "verdict supports an automatic removal again")
            + f", the loop opens a fresh removal pull request. {decline}"
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\nFiled by scripts/retire_skill.py --withdraw-stale (ADR 0014).\n\n"
            + AGENT_MARKER + "\n")
    return {"action": "update-issue" if number else "create-issue", "issue": number,
            "title": title, "body": f"{marker}\n{WITHDRAWAL_STAMP}\n{note}",
            "comment": note}


def close_removal_notices(item: dict, gates: dict, target: str, gh,
                          run_url: str | None) -> list:
    """Close (not planned), then comment on, every open removal notice
    (#557) for the withdrawn subject, so none is left saying a removal is in
    flight (R2-3); the numbers closed, each `#n`, or `#n (no comment)` when
    only its comment failed. Closing first means a failure never leaves an
    open notice whose comment says it is closed."""
    subject = item["subject"]
    if target == "skill":
        marker = SKILL_NOTICE_MARKER.format(skill=subject)
    else:
        marker = GUIDANCE_NOTICE_MARKER.format(section=subject)
    if item["action"] == "decline":
        why = (f"was closed (turned off first) because its proposal issue "
               f"#{item['declined']} is closed, which declines the removal. Nothing is "
               "being removed, so this notice is closed")
    else:
        why = (f"was withdrawn (turned off and closed) on the verdicts as of "
               f"{gates['as_of']}: the verdict is now **{item['verdict']}**. Nothing is "
               "being removed, so this notice is closed; the subject's retirement issue "
               "records the withdrawal")
    note = (f"**Removal withdrawn.** The automatic removal pull request {item['url']} for "
            f"`{subject}` {why}. Rule: [ADR 0014]({ADR})."
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\n" + AGENT_MARKER + "\n")
    closed = []
    for number in guidance_issues(gh, marker)["open"]:
        gh(["issue", "close", str(number), "-R", EVALS_REPO, "--reason", "not planned"])
        try:
            gh(["issue", "comment", str(number), "-R", EVALS_REPO, "--body-file", "-"], note)
        except Exception:  # noqa: BLE001 - the notice is closed; say so, no detail
            closed.append(f"#{number} (no comment)")
        else:
            closed.append(f"#{number}")
    return closed


def add_withdrawn_label(c: dict, registry_gh) -> None:
    """WITHDRAWN_LABEL on a pull request about to be withdrawn. Only when
    the add failed AND the repository's labels (read back) lack it is the
    label created and the add tried once more; RetireError when it is still
    not on, so the pull request is not closed (closed without the label, it
    would decide its subject). No error detail is kept."""
    try:
        registry_gh(c["label"])
        return
    except Exception:  # noqa: BLE001 - read the labels before creating one
        pass
    failed = RetireError(f"could not add the {WITHDRAWN_LABEL} label, so it is left open")
    try:
        names = [n.strip() for n in registry_gh(c["labels"]).split("\n")]
    except Exception:  # noqa: BLE001 - not known to be missing: create nothing
        raise failed from None
    if WITHDRAWN_LABEL in names:
        raise failed
    try:
        registry_gh(c["create_label"])
    except Exception:  # noqa: BLE001 - another pass may have created it
        pass
    try:
        registry_gh(c["label"])
    except Exception:  # noqa: BLE001
        raise failed from None


class WithdrawFailed(RetireError):
    """At least one pull request's calls failed; `lines` holds every item's
    status line, the failed ones included, so a failure never hides the
    others."""

    def __init__(self, message: str, lines: list):
        super().__init__(message)
        self.lines = lines


def _act(item: dict, gates: dict, target: str, registry_gh, gh, run_url, delete) -> str:
    """One planned item's calls; its status line. A `keep` makes none. A
    withdrawal records itself (label, read back, then the retirement issue)
    before it comments and closes, so any failure before the close leaves
    the pull request open for the next pass; then it deletes the branch,
    best effort. A `disarmed` partial withdrawal (R6-2) found armed is
    kept. A `withdraw` or `disarm` under a person's arm (`persons_arm`,
    round 12) is left for that person, with no write; so is a `decline`,
    but only when that arm is strictly later than the declining issue's
    close (round 13: the latest person action wins)."""
    n = item["number"]
    if item["action"] == "keep":
        return f"kept #{n}: {item['why']}"
    if item["action"] == "unreadable":
        raise RetireError(item["why"])
    c = withdraw_commands(target, item["url"])
    if registry_gh(c["state"]).strip() != "OPEN":
        return f"skipped #{n}: it is no longer open"
    armed = bool(registry_gh(c["view"]).strip())
    decline = item if item["action"] == "decline" else None
    if persons_arm(registry_gh, c, armed, decline):
        return f"left #{n} for a person: {PERSONS_ARM}"
    if item.get("partial") == "disarmed" and armed:
        return f"kept #{n}: its auto-merge is on after all"
    if item.get("partial") == "disarmed":
        hold = loop_disarm_hold(registry_gh, c, item["subject"])
        if hold:
            return f"kept #{n}: {hold}"
    if armed:
        registry_gh(c["merge"])
        if registry_gh(c["view"]).strip():
            raise RetireError(f"auto-merge is still enabled on #{n}")
    if item["action"] == "decline":
        return _decline(item, gates, target, registry_gh, gh, run_url, c)
    if item["action"] == "disarm":
        if armed:
            registry_gh(c["comment"], disarm_comment(item, run_url))
            return f"disarmed #{n}: {item['why']}"
        # R8-3: the loop's own disarm with no marker after it is this switch's
        # disarm whose comment failed; post it now, so an `auto` pass reads
        # it as the switch's hold, not as a withdrawal stopped part way.
        if loop_disarm_hold(registry_gh, c, item["subject"]) is None:
            registry_gh(c["comment"], disarm_comment(item, run_url))
            return (f"left #{n} open and disarmed, and posted the comment an earlier pass "
                    f"could not: {item['why']}")
        return f"left #{n} open and disarmed: {item['why']}"
    add_withdrawn_label(c, registry_gh)
    # R6-4: read the label back; an add that exited 0 without landing would
    # make the close below a person-like decision.
    if WITHDRAWN_LABEL not in [x.strip() for x in registry_gh(c["pr_labels"]).split("\n")]:
        raise RetireError(f"the {WITHDRAWN_LABEL} label is not on #{n} after adding it, "
                          "so it is left open")
    issue = withdrawal_issue(item, gates, target, gh, run_url)
    if issue["action"] == "update-issue":
        gh(["issue", "comment", str(issue["issue"]), "-R", EVALS_REPO, "--body-file", "-"],
           issue["comment"])
        filed = f"commented on issue #{issue['issue']}"
    else:
        gh(["issue", "create", "-R", EVALS_REPO, "--title", issue["title"],
            "--body-file", "-"], issue["body"])
        filed = "filed its retirement issue"
    registry_gh(c["comment"], withdrawal_comment(item, gates, run_url))
    registry_gh(c["close"])
    # R7-1: `gh pr close` exits 0 on a pull request someone else closed
    # first. Only the loop's own close is a pause; any other closer decides,
    # and that branch is not the loop's to delete. An unreadable closer keeps
    # the branch too; if the close was the loop's, the next removal's push
    # retries the delete (R7-2).
    closer = read_closer(registry_gh, WITHDRAW_TARGETS[target]["repo"], n)
    decided = closer is not None and closer != LOOP_AUTHOR
    if decided:
        filed += "; " + correct_decided(item, target, registry_gh, gh, c)
    elif closer is None:
        filed += "; could not read who closed it, so its branch is kept"
    else:
        # R6-5, R6-11: no branch outlives its pull request. Best effort: the
        # pause has happened; a branch left behind (a lease that lost, say)
        # is named by its error's type alone, and the next removal for the
        # subject retries the delete before it pushes (R7-2).
        branch = f"{WITHDRAW_TARGETS[target]['prefix']}{item['subject']}"
        try:
            sha = registry_gh(c["head"]).strip()
            if not SHA_RE.fullmatch(sha):
                raise RetireError("no head commit")
            delete(WITHDRAW_TARGETS[target]["repo"], branch, sha)
        except Exception as exc:  # noqa: BLE001 - its text may quote a response
            filed += f"; could not delete its branch ({type(exc).__name__})"
        else:
            filed += "; deleted its branch"
    # Best effort: the withdrawal has happened; a notice left open is
    # named in the status line, never a failed pass.
    try:
        closed = close_removal_notices(item, gates, target, gh, run_url)
    except Exception:  # noqa: BLE001
        filed += "; could not close its removal notice"
    else:
        if closed:
            filed += "; closed its removal notice " + ", ".join(closed)
    if decided:
        return (f"decided #{n}: someone other than the loop closed it, so it decides (not "
                f"a pause); {filed}")
    return f"withdrew #{n}: {item['why']}; {filed}"


DECLINED_MARKER = "<!-- skills-evals:declined-removal:{subject} -->"


def declined_comment(item: dict, target: str, run_url: str | None) -> str:
    """What a removal closed because its subject is declined says (R9-1)."""
    kind = "removal" if target == "skill" else "guidance removal"
    return (f"{DECLINED_MARKER.format(subject=item['subject'])}\n**Closed: the subject is "
            f"declined.** The proposal issue for `{item['subject']}`, "
            f"https://github.com/{EVALS_REPO}/issues/{item['declined']}, was closed while "
            f"this automatic {kind} pull request was open, and a closed proposal issue "
            "declines the removal, whatever its close reason. So auto-merge is turned off "
            "and this pull request is closed as a decision, not a pause: it carries no "
            f"`{WITHDRAWN_LABEL}` label and its branch is kept. This closed pull request now "
            "decides the subject: the loop opens no removal for it again, and reopening the "
            f"issue does not resume it. {LATEST_WINS} No person's arm on this pull request "
            f"is known to be later than the latest close. {OVERRIDE} Rule: [ADR 0014]({ADR})."
            + (f"\n\nWorkflow run: {run_url}" if run_url else "")
            + "\n\n" + AGENT_MARKER + "\n")


def _decline(item: dict, gates: dict, target: str, registry_gh, gh, run_url,
             c: dict) -> str:
    """Close a removal whose subject a closed proposal issue declines
    (R9-1), its auto-merge already off and read back: WITHDRAWN_LABEL off
    and read back (R10-1: a withdrawal that stopped part way left it on, and
    closed with it the removal would read as a pause), comment, close, then,
    best effort, a comment on the closed issue (which stays closed) and the
    subject's removal notices closed. No label and no new issue: the
    subject is declined, not paused, and the closed removal decides it. A
    label that cannot be taken off fails the item, and the pull request is
    left open."""
    n = item["number"]
    if WITHDRAWN_LABEL in [x.strip() for x in registry_gh(c["pr_labels"]).split("\n")]:
        try:
            registry_gh(c["unlabel"])
        except Exception:  # noqa: BLE001 - its text may quote a response
            raise RetireError(f"could not remove the {WITHDRAWN_LABEL} label from #{n}, so "
                              "it is left open") from None
        if WITHDRAWN_LABEL in [x.strip() for x in registry_gh(c["pr_labels"]).split("\n")]:
            raise RetireError(f"the {WITHDRAWN_LABEL} label is still on #{n} after removing "
                              "it, so it is left open")
    comment = declined_comment(item, target, run_url)
    registry_gh(c["comment"], comment)
    registry_gh(c["close"])
    done = []
    try:
        gh(["issue", "comment", str(item["declined"]), "-R", EVALS_REPO, "--body-file", "-"],
           f"The automatic {'removal' if target == 'skill' else 'guidance removal'} pull "
           f"request {item['url']} for `{item['subject']}` was still open when this issue "
           "was closed. A closed proposal issue declines the removal, whatever its close "
           "reason, so the loop turned its auto-merge off and closed it as a decision (no "
           f"`{WITHDRAWN_LABEL}` label, branch kept). That closed pull request now decides "
           "the subject: nothing is removed, and reopening this issue does not resume the "
           f"loop. {LATEST_WINS} No person's arm on that pull request is known to be later than "
           "the latest close. To remove the subject anyway, take that pull request over (remove "
           f"its `{AGENT_LABEL}` label, then reopen and merge it by hand). Rule: "
           f"[ADR 0014]({ADR})."
           + (f"\n\nWorkflow run: {run_url}" if run_url else "")
           + "\n\n" + AGENT_MARKER + "\n")
        done.append(f"commented on issue #{item['declined']}")
    except Exception:  # noqa: BLE001 - its text may quote a response
        done.append(f"could not comment on issue #{item['declined']}")
    try:
        closed = close_removal_notices(item, gates, target, gh, run_url)
    except Exception:  # noqa: BLE001
        done.append("could not close its removal notice")
    else:
        if closed:
            done.append("closed its removal notice " + ", ".join(closed))
    return (f"declined #{n}: {item['why']}; closed it as a decision and kept its branch; "
            + "; ".join(done))


DECIDED_MARKER = "<!-- skills-evals:closed-by-another:{subject} -->"


def decided_note(item: dict, target: str) -> str:
    """The correction for a withdrawal someone else's close overtook (R7-1):
    the comment and issue note already sent call it a pause."""
    kind = "removal" if target == "skill" else "guidance removal"
    return (f"{DECIDED_MARKER.format(subject=item['subject'])}\n**Correction.** Someone "
            f"other than the loop closed the automatic {kind} pull request {item['url']} "
            "while the loop was withdrawing it (or GitHub records no closer), so it counts as "
            f"a person's decision, not a pause: the subject `{item['subject']}` is decided, and the loop opens no fresh "
            "removal for it. The earlier note that called it a pause is wrong, and its branch "
            f"is kept. Rule: [ADR 0014]({ADR}).\n\n{AGENT_MARKER}\n")


def correct_decided(item: dict, target: str, registry_gh, gh, c: dict) -> str:
    """Post `decided_note` on the pull request and the subject's open
    retirement issue, best effort; the status line's tail."""
    note, done = decided_note(item, target), []
    try:
        registry_gh(c["comment"], note)
        done.append("corrected its comment")
    except Exception:  # noqa: BLE001 - its text may quote a response
        done.append("could not correct its comment")
    try:
        number = retirement_issues(gh, item["subject"], target)[1]["open"][0]
        gh(["issue", "comment", str(number), "-R", EVALS_REPO, "--body-file", "-"], note)
        done.append(f"corrected issue #{number}")
    except Exception:  # noqa: BLE001
        done.append("could not correct its retirement issue")
    return "; ".join(done) + "; kept its branch"


def _no_delete(repo, branch, sha):
    raise RetireError("no branch delete is wired")


def withdraw_stale(gates: dict | None, prs: list, target: str, registry_gh,
                   run_url: str | None = None, gh=None, delete=None,
                   items: list | None = None) -> list:
    """Withdraw every stale loop removal pull request among `prs` (the
    listing `removal_prs` read), and disarm every one the `proposal` switch
    holds; the status lines. Pull request writes go through `registry_gh`;
    the retirement issue and the removal notice through `gh` (the job's
    token; default `registry_gh`). One item's failure of any kind does not
    stop the others: WithdrawFailed at the end, with every status line (a
    RetireError's text, or only the type of any other exception, since its
    text may quote a response). A malformed listing still refuses before
    any write. `delete(repo, branch, sha)` deletes a withdrawn removal's
    branch under a lease on its head (`default_delete_branch`); without
    one, every delete is reported as not made. `items` is `withdraw_plan`'s
    result when the caller has it already (default: read here, with the
    subjects' retirement issues through `gh`)."""
    gh = gh or registry_gh
    delete = delete or _no_delete
    lines, errors = [], []
    if items is None:
        items = withdraw_plan(gates, prs, target, gh)
    for item in items:
        try:
            lines.append(_act(item, gates, target, registry_gh, gh, run_url, delete))
        except Exception as exc:  # noqa: BLE001 - isolate each pull request
            why = str(exc) if isinstance(exc, RetireError) else type(exc).__name__
            errors.append(why)
            lines.append(f"failed #{item['number']}: {why}")
    if errors:
        raise WithdrawFailed("; ".join(errors), lines)
    return lines or ["no open removal pull request to withdraw"]


def unused_checker(gates: dict, usage_path) -> "callable":
    """The `unused_check` of `withdrawal_decision`: `subject -> (state, why)`
    for an open `unused` removal. Stale when the skill was used in the
    policy's `floor_weeks` window (read as of the gates document's `as_of`)
    or has become exempt (evals/usage-unknown.yml); supported while the
    census is fresh and still shows no use; unknown (kept) when the census,
    the policy or the exempt list cannot be read, or the census is stale.
    The threshold itself is not re-derived here: the withdrawal passes have no
    registry checkout for a skill's description size, and exposure only
    grows while the skill stays unused."""
    def check(subject: str) -> tuple:
        try:
            policy, exempt = unused_inputs()
        except RetireError:
            return "unknown", "the removal policy or the exempt list could not be read"
        if subject in exempt:
            return "stale", "the skill is now listed in evals/usage-unknown.yml (exempt)"
        usage = skill_usage.load(usage_path) if usage_path is not None else None
        now = _moment(gates.get("as_of"))
        if usage is None or now is None or not skill_usage.is_fresh(usage, now):
            return "unknown", "there is no fresh usage census"
        uses = skill_usage.weight(usage, subject, now, policy["floor_weeks"])
        if uses is None:
            return "unknown", "there is no fresh usage census"
        if uses > 0:
            return "stale", (f"the skill has been used ({uses} use(s) in the last "
                             f"{policy['floor_weeks']} weeks)")
        return "supported", "the skill still has no recorded use in the census window"
    return check


def withdraw_main(args, env, gh, registry_gh, run_url, out, delete=None) -> int:
    """`--withdraw-stale`: unknown verdicts withdraw nothing and exit 0 with a
    status that names no subject; a refusal or a failed call exits 2."""
    try:
        gates = load_gates(args.gates)
    except RetireError:
        gates = None
    if gates is not None and args.target == "guidance" \
            and not isinstance(gates.get("guidance"), dict):
        gates = None
    if gates is None:
        out.write("retire_skill: withdrew nothing: the verdicts document is missing "
                  "or unreadable\n")
        return 0
    prs = removal_prs(gh, args.target)
    check = unused_checker(gates, args.usage) if args.target == "skill" else None
    items = withdraw_plan(gates, prs, args.target, gh, check)
    if args.dry_run:
        out.write(json.dumps({"dry_run": True, "withdraw": items, "would_run": [
            ["gh", *c] for i in items for c in would_run(args.target, i)]},
            indent=2, sort_keys=True) + "\n")
        return 0
    if any(i["action"] in ("withdraw", "disarm", "decline") for i in items):
        check_auto_env(env)
    try:
        lines = withdraw_stale(gates, prs, args.target, registry_gh, run_url, gh, delete,
                               items)
    except WithdrawFailed as exc:
        for line in exc.lines:
            out.write(f"retire_skill: {line}\n")
        raise
    for line in lines:
        out.write(f"retire_skill: {line}\n")
    return 0


def refresh_allowed(gates: dict | None, head: str, gh, number: int | None = None) -> tuple:
    """Whether loop-pr-refresh.yml may bring a pull request from `head` up to
    date (round 1's M2): `(True, why)` for a head that is not a removal's;
    for a `retire-skill/` or `retire-guidance/` head, only while its
    subject's verdict still supports an automatic removal AND the target's
    mode is `auto` AND no closed proposal issue declines it (R10-4: its
    retirement issues are read through `gh`, as the withdrawal pass reads
    them, so a decline that pass could not finish is not undone by a
    refresh). Anything else, unknown data or an unreadable issue list
    included, is `(False, why)`, so a refresh never re-runs the checks of a
    removal that should not merge. The one exception (round 12): given its
    pull request `number`, a removal under a person's arm in force
    (`persons_arm`, armed now as read through `gh`) is `(True, ...)`
    whatever its verdict or mode, since the withdrawal pass leaves it to
    that person and it must still be able to merge. Its retirement issues
    are read for it too, and the same comparison as the withdrawal pass's
    applies (round 13, the latest person action wins): when a closed
    proposal issue declines the subject, the arm wins only when it is
    strictly later than that close, so a later close, a tie or a missing
    time refuses, and so does an unreadable issue list. An unreadable arm is
    not a person's, so the refusal stands."""
    for target, spec in WITHDRAW_TARGETS.items():
        if not head.startswith(spec["prefix"]):
            continue
        subject = head[len(spec["prefix"]):]
        if not SKILL_RE.fullmatch(subject):
            return False, "its head names no subject"
        ok, why = _refresh_verdict(gates, gh, target, spec, subject)
        if not ok and type(number) is int and number > 0:
            c = withdraw_commands(target, f"https://github.com/{spec['repo']}/pull/{number}")
            try:
                armed = gh(c["armed"]).strip() == "true"
            except Exception:  # noqa: BLE001 - not known to be armed
                armed = False
            if armed:
                try:
                    decline = declined(retirement_issues(gh, subject, target)[1], subject,
                                       "auto", "subject")
                except Exception:  # noqa: BLE001 - its text may quote a response
                    return False, "its retirement issues could not be read"
                if persons_arm(gh, c, armed, decline):
                    return True, f"{PERSONS_ARM}, so the loop leaves it to that person ({why})"
                if decline is not None and persons_arm(gh, c, armed):
                    return False, (f"its proposal issue #{decline['issue']} was closed no "
                                   "earlier than a person armed it (or either time is "
                                   "unknown), which declines it")
        return ok, why
    return True, "not a removal pull request"


def _refresh_verdict(gates, gh, target, spec, subject) -> tuple:
    """`refresh_allowed`'s answer from the verdict, the mode and the
    subject's retirement issues alone."""
    if not isinstance(gates, dict) or not isinstance(gates.get(spec["block"]), dict):
        return False, "the verdicts are unknown"
    if subject not in gates[spec["block"]]:
        return False, "the verdicts document does not list the subject"
    state, why = removal_support(gates, gates[spec["block"]][subject], target)
    if state != "supported":
        return False, why
    if spec["mode"](gates) != "auto":
        return False, f"the {spec['block']} retirement_mode is proposal"
    try:
        decline = declined(retirement_issues(gh, subject, target)[1], subject, "auto",
                           "subject")
    except Exception:  # noqa: BLE001 - its text may quote a response
        return False, "its retirement issues could not be read"
    if decline:
        return False, f"its proposal issue #{decline['issue']} is closed, which declines it"
    return True, why


def main(argv: list | None = None, *, env=None, gh=default_gh, push=None,
         registry_gh=None, delete=None, review=None, doors=None,
         out=sys.stdout) -> int:
    env = os.environ if env is None else env
    token = env.get(REGISTRY_TOKEN_ENV) or None
    if push is None:
        def push(checkout, branch, heads=()):
            default_push(checkout, branch, token, heads)
    if delete is None and gh is not default_gh:
        def delete(repo, branch, sha):  # an injected gh (a test's fake): no network
            raise RetireError("no branch delete is wired beside an injected gh")
    elif delete is None:
        def delete(repo, branch, sha):
            default_delete_branch(repo, branch, sha, token)
    if registry_gh is None and gh is not default_gh:
        registry_gh = gh  # an injected gh (a test's fake) answers both
    elif registry_gh is None:
        def registry_gh(args, stdin=None):
            if not token:
                raise RetireError(f"no {REGISTRY_TOKEN_ENV} for an adam-agentskills write")
            return default_gh(args, stdin, token)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gates", required=True, type=Path)
    parser.add_argument("--registry", action="append", metavar="NAME=PATH")
    parser.add_argument("--allow-mode", action="append", choices=("auto", "proposal"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fallback-to-proposal", action="store_true",
                        help="this caller has no write credential for the target repository: a "
                             "gates file in auto mode files the issue instead of exiting 2")
    parser.add_argument("--date", metavar="YYYY-MM-DD",
                        help="the skill-impact entry's date (default: the gates file's "
                             "as_of date)")
    parser.add_argument("--target", choices=("skill", "guidance"), default="skill",
                        help="act on the skills' verdicts (default) or the guidance "
                             "sections' (#124)")
    parser.add_argument("--guidance", type=Path, metavar="PATH",
                        help="the _agent-guidance checkout a guidance removal edits")
    parser.add_argument("--usage", type=Path, default=None,
                        help="usage/weekly-local.json, for the issue's recent-use line")
    parser.add_argument("--withdraw-stale", action="store_true",
                        help="only withdraw the target's open removal pull requests whose "
                             "subject's verdict no longer supports them, and disarm the "
                             "rest while the mode is proposal (ADR 0014)")
    args = parser.parse_args(argv)
    run_url = None
    if env.get("GITHUB_RUN_ID") and env.get("GITHUB_REPOSITORY") == EVALS_REPO \
            and env["GITHUB_RUN_ID"].isdigit():
        run_url = (f"https://github.com/{EVALS_REPO}/actions/runs/{env['GITHUB_RUN_ID']}")
    try:
        if not args.dry_run:
            check_event(env, WITHDRAW_EVENTS if args.withdraw_stale else ("schedule",))
        if args.withdraw_stale:
            return withdraw_main(args, env, gh, registry_gh, run_url, out, delete)
        if args.date is not None and not DATE_RE.fullmatch(args.date):
            raise RetireError("--date is not YYYY-MM-DD")
        gates = load_gates(args.gates)
        registries = compute_gates.flag_registries(args.registry)
        allowed = tuple(args.allow_mode or ("proposal",))
        if args.target == "guidance":
            if not args.dry_run and guidance_mode(gates) == "auto" and "auto" in allowed:
                check_auto_env(env)
            action = guidance_plan(gates, args.guidance, gh, run_url, allowed,
                                   fallback=args.fallback_to_proposal)
            if args.dry_run:
                out.write(json.dumps({"dry_run": True, **action,
                                      "would_run": guidance_commands(action)},
                                     indent=2, sort_keys=True) + "\n")
                return 0
            if action.get("mode_reason"):
                print(f"retire_skill: auto lowered to proposal: {action['mode_reason']}",
                      file=sys.stderr)
            out.write(guidance_execute(action, args.guidance, gh, push, env,
                                       registry_gh, review=review) + "\n")
            if action.get("failure"):
                print(f"retire_skill: {action['failure']}", file=sys.stderr)
                return 1
            return 0
        if not args.dry_run and mode_of(gates) == "auto" and "auto" in allowed:
            check_auto_env(env)
        usage = skill_usage.load(args.usage) if args.usage is not None else None
        action = plan(gates, registries, gh, run_url, allowed, usage,
                      fallback=args.fallback_to_proposal, date=args.date,
                      unused_loader=unused_inputs)
        if args.dry_run:
            out.write(json.dumps({"dry_run": True, **action,
                                  "would_run": commands(action)},
                                 indent=2, sort_keys=True) + "\n")
            return 0
        if action.get("mode_reason"):
            print(f"retire_skill: auto lowered to proposal: {action['mode_reason']}",
                  file=sys.stderr)
        out.write(execute(action, registries, gh, push, env, registry_gh,
                          review=review, doors=doors) + "\n")
    except (RetireError, ValueError) as exc:
        print(f"retire_skill: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
