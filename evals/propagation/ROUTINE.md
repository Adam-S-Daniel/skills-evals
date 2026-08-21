# Tier 3 — the account-store Routine

`harness/run_account_audit.py` is built, tested and **verified against the real
claude.ai account store** (see below for what it found). Its *transport* — the
scheduled cloud session that runs the audit and publishes the result — now works
end to end. `eval-results` carries commit `0a532be6`:
`propagation/account/latest.json` (1705 bytes), its timestamped copy
`20260814T141714Z.json`, `badges/account-store.json`, and the bootstrap marker
`propagation/.bootstrapped`. The Routine is `trig_01MpUvqeffteExy1gkWT8yBi`,
cron `0 5 * * *` (daily, 05:00 UTC), fired into a session that carries this repo
in its authorized set. The freshness gate is **armed**, not waiting.

It read red for a while, and that was the design working rather than a fault in
it: the account store was genuinely drifted (8 checked, 4 drifted), so the gate
returned `reported-failure`. A gate that stayed green against a known-bad store
would have been the failure. **That episode is over** — the audit published at
`2026-08-18T22:01:13Z` reads `pass`, 10 checked, 0 findings, so agentskills#59
is repaired and the gate now returns `fresh`.

The red ran from 2026-08-14 to 2026-08-18, and writing the duration down matters,
because the duration is what changed the design.

**The audit's verdict is advisory on every event EXCEPT the schedule.** It was
originally fatal on all of them, on the reasoning that `main` carries no required
status checks so a red check is a loud signal rather than a merge blocker. What
that missed is how long the red lasts. The drift lives in the claude.ai account
store: no commit in this repo caused it and none can clear it, so for those four
days every pull request opened here wore someone else's red. A check that is red
for reasons its reader cannot act on is one people learn to scroll past — and a
gate mentally filed under "always red" has stopped being a gate, which is the
same death as never building it. The change was made while the gate happened to
be green again, which is the right time to make it: the policy question is about
the next episode, not this one.

The first cut of that change named `pull_request` as the *one* advisory event and
left every other trigger fatal, which kept the same problem on the other half of
the traffic. **A push to `main` is a worse surface for this red than a pull
request, not a better one:** the merge has already happened, so the check blocks
nothing, and it still names no change anyone could make. Measured 2026-08-21 —
runs `32444343915` and `32445416856` were both post-merge pushes that failed on
`FAIL freshness-gate [reported-failure]`, and `scheduled-run-health.yml` then
reported both into issue #33 as failing runs. One account drift, two CI-fault
reports, no repair. The condition is now written the other way round — advisory
by default, subtracted on `schedule` alone — so a trigger added later (a
dispatch, a merge group) arrives on the side that blocks nothing, and making one
fatal is a deliberate line in a diff.

So every non-scheduled run prints `WARN freshness-gate [reported-failure]` with
the drifted skills named, and passes. The scheduled run still fails, and `report`
still files the tracking issue — that is the surface where a stale verdict was
always supposed to be answered, and the only one that acts on it. What stays
fatal EVERYWHERE is liveness: a `missing`, `stale` or `unreadable` result means
the audit is not reaching us at all, and catching a Routine that quietly stopped
firing is this gate's entire reason to exist. That is guaranteed by
`ADVISORY_STATUSES` in `harness/run_propagation.py`, which names
`reported-failure` and nothing else — not by which events pass the flag, so no
future trigger can downgrade a dead Routine. The split is between "the audit told
us something bad" and "the audit is not talking to us" — only the second is this
repo's to answer.

Getting there took a redesign of the transport: the measurement worked on the
first fire, and the last hop did not.

This file was written as a specification rather than a record on the grounds
that a probe nobody can prove works is worse than a gap somebody can read. It is
a record now, end to end — the audit runs on a Routine-fired surface, the result
reaches `eval-results`, and the gate reads it.

## Why a Routine and not a workflow

A GitHub runner has no signed-in claude.ai account, so `~/.claude/skills/synced/`
does not exist there. This is a **surface** constraint, not a credential one:
the audit reads files and spends nothing. Only a session that *is* a
signed-in surface can observe the account store, which is what a cloud session
spawned by a Routine is.

That is now measured rather than argued: the fired sessions found the store
where an interactive session finds it and returned the same counts. What the
premise did not cover is whether such a session may then *push* — see below.

## How it was created

The call that made the current Routine, kept as the recipe if it is ever lost:

```
create_trigger(
  name  = "skills-evals: account-store propagation audit (authorized)",
  cron_expression = "0 5 * * *",          # daily, 05:00 UTC
  persistent_session_id = "<a session carrying skills-evals as a source>",
  prompt = <the standalone prompt below, since rewritten>,
)
```

The first Routine (`trig_0148Zfwf9ZvxRUFuHygJ2dPU`) took
`create_new_session_on_fire = true` and `notifications = {push, email}`
instead. It measured correctly on all three of its runs and published none of
them; it was deleted and replaced by the call above. Why, and what that cost,
is the next section.

## Why it fires into a bound session

Each of the first Routine's three runs on 2026-08-14 measured correctly —
`account audit: 8 checked, 4 drifted, exit 1`, identical to an interactive
session on this account — and then failed at the last hop with:

```
Adam-S-Daniel/skills-evals is not in this session's authorized repository set
```

That is the CCR proxy's per-session repository scope, not a GitHub rejection. A
Routine-fired session is minted without this repo in its authorized set, so the
push is refused before it ever reaches GitHub: the repo's own permissions and
branch protection are not involved, and `eval-results` being unprotected is
irrelevant to it. Misread as a GitHub 403 it sends the next person to repo
settings, where they will find nothing wrong and conclude the report was
mistaken.

The mechanism was isolated rather than inferred. A session created with
`skills-evals` as an explicit `sources` entry pushed a probe branch on the first
try, where three Routine-fired sessions had all failed — same repo, same
account, same environment, the attached sources the only difference. Those
sessions also carry no `mcp__*` tools at all (visible in the Routine's stored
`session_context.allowed_tools`), so they could neither reach the GitHub API to
work around it nor call `add_repo` to put the repo into their own set.

Binding the Routine to a session that already carries the repo fixes it, and
costs two things worth stating plainly:

- **No cold boot.** `create_new_session_on_fire` was chosen deliberately: a
  Routine bound to a persistent session audits that session's warm state rather
  than a fresh one. That reasoning is sound for Tier 2, where what a surface
  assembles at boot *is* the measurement. It is weak for Tier 3 — the account
  store is external state synced from claude.ai, not something a session
  accumulates, so a warm session reads the same store a cold one would.
- **No notifications.** The API rejects `notifications` on a persistent-session
  Routine, so layer 2 is gone. It was the only layer reaching a human while
  publishing was broken. What replaces it is layer 1, which is machine-readable
  and is the one this file already calls the layer that matters — better, but a
  trade rather than a free win.

Residual risk, as originally written: *if the bound session is archived or
reclaimed, the binding dies.* That happened on 2026-08-19, and the wording above
was wrong in the way that mattered — **the binding does not die, it silently
degrades**, which is strictly harder to see. See the next section.

Root cause and fix are recorded in
[skills-evals#20](https://github.com/Adam-S-Daniel/skills-evals/issues/20).

### The binding degrades silently — it does not die (2026-08-19, #47)

The residual risk above was real and it fired within five days. What it got
wrong is the failure *shape*, and the shape is the whole diagnostic problem.

The bound session was reclaimed some time after its last successful publish at
`2026-08-18T22:01:13Z`. The Routine did **not** stop, and it did **not** disable
itself. At `2026-08-19T05:10:06Z` a replacement session was minted and the
trigger was re-pointed at it one second later (`updated_at 05:10:07`). The
Routine then fired on the 19th, the 20th and the 21st, measured correctly every
time, and published nothing — because the replacement session is exactly the
kind of session #20 is about.

Read from the outside, nothing looks wrong. The trigger is `enabled: true`, has
a `persistent_session_id`, has a recent `last_fired_at`, and carries no
`ended_reason`. Compare a sibling Routine in the same account whose session went
away and which reads `ended_reason: auto_disabled_session_gone` — *that* is the
visible form of this failure, and it is the form this file anticipated. The
invisible form is a live trigger bound to a live session that cannot push.

**The one field that tells them apart is `session_context.sources`.** A session
that can publish carries the repo explicitly; the auto-minted replacement had no
`sources` key at all:

| | publishes | does not publish |
|---|---|---|
| `session_context.sources` | `[{git_repository: …/skills-evals}]` | **absent** |
| `origin` | `claude_code_mcp_seed` (or a user session) | `scheduled_trigger` |
| `tags` | — | `config:routine-lineage-none` |

So the 30-second diagnosis, when the gate next reports `stale`, is:

1. `list_triggers` → read the Routine's `persistent_session_id`.
2. `get_session` on that id → read `session_context.sources`.
3. No `sources` → the binding has been silently re-minted. Nothing is broken in
   the repo, in branch protection, or in the audit; re-bind and move on.

That third cause now belongs in the `stale` message's list alongside the two it
already names ("the Routine has stopped firing, or its result is no longer
reaching `eval-results`"). It is neither: the Routine is firing *and* the result
is not reaching us, because the publisher was replaced underneath it.

The repair is the same recipe as before — create a session with `skills-evals`
as an explicit source, bind a new Routine to it, delete the old one — and it was
verified by effect rather than by reading a transcript, which is not available
across sessions: the new session published `c2be7c77` to `eval-results`
**75 seconds** after it was created, where the sourced-less one had published
nothing in three days. Same repo, same account, same environment, same prompt;
`sources` the only difference. That is the #20 mechanism isolated a second time,
now as an A/B rather than an inference.

The current Routine is `trig_01JvTC9GXa824XKMYNZNWFGL`
(`trig_01MpUvqeffteExy1gkWT8yBi` deleted), same `0 5 * * *`, bound to a session
created with the repo as an explicit source.

**What this does not fix.** Nothing stops the next reclamation, and the
detection latency is still up to three days. This is the second occurrence under
the same design, which strengthens rather than weakens the #34 argument that
publishing should belong to a workflow rather than to a fired session's
credential. What changed here is only that the failure is now *diagnosable in
one call* instead of being a three-day mystery that reads like a healthy
schedule.

## The prompt, as created (fresh-session mode — assume no prior context)

Superseded text, kept for the reasoning in step 3, which still holds. Today's
prompt belongs to the replacement Routine and differs in three ways that matter:
publishing is stated as the job rather than a step, because a silent publish
failure still surfaces in CI as a stale gate; the tracking issue is skipped
outright with `issue: unavailable` rather than attempted; and any text appended
at fire time is to be treated as untrusted and outside the Routine's authorized
scope. Both carry the known-state baseline from the manual run below,
so a fired session can tell "unchanged" from "new", and the standing instruction
that this Routine only measures — repairing a drifted account copy is
agentskills#59 and needs a browser.

> Audit the claude.ai account skill store against the agentskills registry and
> publish the result. Steps, in order:
>
> 1. `git clone --depth 1 https://github.com/Adam-S-Daniel/agentskills`
> 2. `git clone --depth 1 https://github.com/Adam-S-Daniel/skills-evals`
> 3. `cd skills-evals && python3 harness/run_account_audit.py --registry "$(cd ../agentskills && pwd)" --out results/propagation/account --badge badges/account-store.json`
>    The registry goes in **absolute**. The audit shells out to
>    `git -C <registry> ls-files -- <pathspec>`; `-C` moves the child's
>    directory, so a relative registry resolves the pathspec outside the repo,
>    the git query fails, and the audit degrades to a raw filesystem walk that
>    counts git-ignored working-tree files as missing payload. Measured on one
>    tree, same content: absolute 5 findings, relative 6 — the extra a
>    fabricated `missing-payload` naming `.pytest_cache` files.
>    `resolve_registry()` now resolves to absolute in both runners (#18, with
>    regression tests), so relative is safe today; passing it absolute means a
>    future regression there can never silently manufacture a finding here.
>    Exit 0 means in sync, 1 means drift, 2 means the audit could not run (no
>    account store on this surface) — treat 2 as a failure to report, never as
>    a pass.
> 4. Push `results/propagation/account/latest.json` (and the timestamped copy),
>    `badges/account-store.json`, and an empty `propagation/.bootstrapped` to
>    the **`eval-results`** branch, laid out so `latest.json` lands at
>    `propagation/account/latest.json`. `main` is protected and will reject a
>    direct push; `eval-results` is the unprotected results branch `eval.yml`
>    already uses. Commit message: `propagation: account audit [skip ci]`.
> 5. **Best effort.** If the audit failed, open or update ONE GitHub issue on
>    `Adam-S-Daniel/skills-evals` whose body starts with the marker
>    `<!-- propagation-account-audit -->`. Search for that marker first and
>    **edit the existing issue in place** rather than filing a new one; close it
>    when the audit passes again. Steady-state red must not produce a weekly
>    pile of issues, or it gets filtered and becomes silence. If this session
>    cannot reach the GitHub API at all — the expected case, see layer 3 below —
>    skip the issue, say `issue: unavailable` in the status line, and do **not**
>    invent a workaround that writes issue-shaped content into the results
>    branch. Step 4 has already published by then, which is why it runs first.
> 6. Print one non-identifying status line: the counts, plus whether step 5 ran
>    (`issue: updated` / `issue: unavailable`). **Never print skill
>    descriptions, file contents, account identifiers or paths under `$HOME`** —
>    this repo is public and so are its logs.

## How a human learns that this went red — four layers, two of them live

Four by design; two delivering. Layers 1 and 4 ride the published result and it
now arrives; layer 2 was traded away for the binding that publishes it, and
layer 3 needs an API the fired session has not got.

1. **The next pull request goes red.** `harness/run_propagation.py`'s freshness
   gate runs on every pull request (`propagation.yml`, job `gate`), reads
   `eval-results:propagation/account/latest.json`, and fails when it is missing,
   older than `account_audit_max_age_days` (3), or — on the scheduled run only,
   per the policy above — reports a failure. A stale
   verdict names both causes it cannot tell apart — the Routine stopped firing,
   or its result stopped reaching `eval-results`; 2026-08-14 was the second, and
   blaming the first sends the reader to a schedule that is healthy. This is
   the layer that matters, because it catches the failure mode nothing else
   does: a Routine that **stops firing at all**. It is implemented and tested
   (`FreshnessGateTests`), and the `gate` job carries no event filter, so it
   runs on `propagation.yml`'s daily schedule as well — a dead Routine surfaces
   within a day rather than whenever someone next opens a pull request. That
   schedule and this gate cover different failures and neither subsumes the
   other: only the gate sees a Routine that stopped firing, and only the Tier-2
   arms see a delivery channel that broke with no commit here — their one
   unpinned input is the agentskills registry at `main`. The workflow reports
   itself rather than trusting anyone to read the Actions tab (job `report`
   files one tracking issue, and closes it again on the first green scheduled
   run, so an open issue means "broken now" rather than "broke once"); the
   Routine no longer reports itself at all — see
   layer 2 — which makes this gate the whole of the watch on it. **Armed as of
   `0a532be6`:** the bootstrap marker is published, so it enforces instead of
   passing on absent data, and it currently returns `reported-failure` — the
   account store's real state, not a fault in the probe.
2. **Routine `notifications: {push: true, email: true}`** — **gone.** The API
   rejects `notifications` on a Routine bound to a persistent session, and that
   binding is what makes publishing work at all. This was the only channel
   reaching someone who never opens GitHub, and while publishing was broken it
   was the only channel of any kind; layer 1 replaces it with something a gate
   can consume, which is the better half of the trade but not a free one.
3. **One marker-tagged issue**, edited in place (step 5), following the fleet's
   `post-failure-comment` pattern — **unavailable, and now known to be.** The
   sessions this Routine fires carry no `mcp__*` tools, and this environment
   has no `gh` CLI: the fired session has no route to the GitHub API at all.
   That much is measured, in `session_context.allowed_tools` — see the
   subsection below, which also separates it from the *reason* it was long
   attributed to, a Routine created through the MCP meta-tool storing no
   connectors. The live prompt no longer attempts the issue and reports
   `issue: unavailable` instead. Nothing else depends on this layer, but the
   independence once claimed for the others was narrower than it looked — 1
   and 4 both ride the published result, so the publish failure took them
   both, and only 2, which came from the Routine itself, was ever independent
   of it.
4. **A badge** built from the same result (`--badge`), served from
   `eval-results` exactly like the quality badge, naming the count — published
   in `0a532be6` reading `account skill store: 4 of 8 drifted · 2026-08-14`.

### Can a Routine carry a connector? Tested 2026-08-20 — refused a layer earlier

Layer 3 was dead by inference before it was dead by measurement, and the two
are not the same claim. What was measured was the *symptom* — no `mcp__*`
tools in a fired session. The *cause* written next to it — that the Routine
stores no connectors, and that one created **with** a connector would fire
sessions that carry `mcp__github__*` — was a reasonable reading of
`session_context.allowed_tools`, never a test. [#34][i34] proposed the test.
It was run on 2026-08-20 and stopped at step 1, one layer earlier than the
issue anticipated. Recorded here so the next person does not re-derive it.

**The risk #34 named first did not apply.** The issue's cheap pre-check was
whether MCP GitHub tools count as a *connector* in the claude.ai sense at all,
as opposed to a session-injected toolset — because `create_trigger`'s contract
says a CCR session can only narrow the connector set it already holds, never
widen it. They do count, and the creating session does hold one:
`ListConnectors` returns `github-mcp` with `installState: connected`,
`connected: true`, `enabledInChat: true`. This is the org connector, distinct
from the session-provisioned `mcp__github__` server, which does not appear in
`ListConnectors` at all — the two-connector split the fleet `AGENTS.md`
already documents. So the experiment was not blocked by the thing expected to
block it.

**It was blocked by the parameter itself.** `create_trigger` refuses
`connectors` outright, for this organization:

```
create_trigger: the connectors parameter is not available for this organization.
Omit the connectors parameter.
```

**That is an org gate on the parameter, not a name that failed to resolve.**
The call was made twice — once with `connectors: ["github-mcp"]` and once with
`connectors: []` — and returned the **identical** error both times. The tool
contract documents `[]` as "store no connectors", i.e. a request that resolves
no names at all, so a refusal of `[]` cannot be a resolution failure and is
not the documented narrowing either: narrowing an empty set is a no-op.
Neither call persisted anything. `list_triggers` afterwards showed no new
Routine, and the live Tier-3 Routine `trig_01MpUvqeffteExy1gkWT8yBi` was
untouched — still enabled, still cron `0 5 * * *`.

**Corroborating, and worth recording on its own — but count the sample
carefully.** Every Routine exposes its tool surface at
`job_config.ccr.session_context.allowed_tools`, and that surface is uniform.
Of the **first 100** returned by `list_triggers(limit=100,
include_completed=true)` on 2026-08-20, **100 of 100** carry the identical
20-entry list below, and **zero** carry any `mcp__*` entry — the live Tier-3
Routine `trig_01MpUvqeffteExy1gkWT8yBi` among them.

```
preset:default, Task, Bash, Glob, Grep, Read, Edit, MultiEdit, Write,
NotebookEdit, WebFetch, TodoWrite, WebSearch, BashOutput, KillBash, Skill,
Tmux, Monitor, SendUserFile, REPL
```

That is a **sample, not a census**, and is deliberately described as one: the
response came back `has_more: true` carrying a `next_cursor`, and 100 is the
tool's documented maximum `limit`, so the account holds **at least** 100
Routines and the remainder were not read. The right claim is "100 examined,
zero with any `mcp__*` tool", never "all of them".

**The default `list_triggers` view is misleading for exactly this question,
which is a finding in its own right.** Called with no arguments it returns
**three** entries here, and an earlier draft of this section reported "all
three of this account's Routines" on that basis. Three is not the account's
Routine count; it is what survives the tool's default `include_completed:
false`, which by its own contract hides one-shot Routines that have already
fired — and this account generates those constantly (`send_later` reminders,
one-shot session handoffs). A census taken from the default view is wrong by
more than an order of magnitude while looking complete, because nothing in the
response says anything is missing. Pass `include_completed: true`, read
`has_more`/`next_cursor`, and state which of the two you did.

So layer 3's operative claim — the fired session has no route to the GitHub
API at all — is confirmed directly for the live Tier-3 Routine, holds for 99
further Routines besides, and is confirmed independently of the connectors
question.

**What was NOT established, stated plainly.** The downstream hypothesis —
*would* a connector-carrying Routine fire sessions that carry
`mcp__github__*`? — is **untested and, from this account, currently
untestable**. It is not a measured "no". No Routine created here can carry a
connector grant at all, so the hypothesis was never reached, and nothing above
disproves it. The one thing that would change that is the org gate lifting: if
`create_trigger` ever accepts `connectors`, run #34's step 2 as written — a
throwaway Routine with a near-future `run_once_at` whose prompt reports only
its own tool surface, then delete it — and replace this paragraph with the
result. Until then, treat the split #34 wanted as blocked upstream of this
repo, not as refuted.

### A second route the issue does not consider — UNTESTED design, two blockers

#34 assumes the only path from a fired session to CI is a GitHub API call,
which is what makes a connector load-bearing. It is not the only path: **a git
push is a separate credential path from the API**, and the fired session has
published to `eval-results` under its own credential — that is how publishing
works at all since the binding fix above. A workflow triggered on that push,

```yaml
on:
  push:
    branches: [eval-results]
```

would in principle let CI own the badge, the marker issue and the gate with
**no** connector, **no** `mcp__*` tool and **no** `gh` CLI in the fired
session, recovering most of what #34's split wanted while the Routine keeps
only the ~10 lines it alone can execute.

**First, correct the premise it rests on.** An earlier draft of this section
said the fired session "already pushes to `eval-results` successfully today",
in the present tense, as established fact. It is not true as of writing.
Measured 2026-08-20: the Routine's `last_fired_at` is `2026-08-20T05:09:02Z`,
but `origin/eval-results` is still at `190e4a1`, committed `2026-08-18
22:01:36 +0000`, whose `propagation/account/latest.json` reads
`"generated_at": "2026-08-18T22:01:13Z"`. The timestamped copies run
`20260814T141714Z` → `20260818T220113Z` with no `20260819*` and no
`20260820*` file, so the most recent firing published **nothing** — 31.1 h
between the last artifact and the last fire — and the daily `0 5 * * *` slot
on 08-19 falls inside the same gap. What is true is the weaker, past-tense
claim: that credential *has* pushed here, which is why the route is worth
recording at all.

**That gap is the exact silent failure this repo's freshness gate exists to
catch, and it should be named rather than stepped over.** A Routine that fires
and publishes nothing is invisible from every other angle: its run reports to
nobody, and layers 1 and 4 both ride the published result, so they go quiet
together — the narrow independence noted under layer 3 above. Only
`account_store.freshness_verdict` sees it, and its `stale` message already
names the two causes it cannot tell apart — "the Routine has stopped firing,
or its result is no longer reaching `eval-results`" — which is the second
again, as on 2026-08-14. It has not gone red yet only because the gap is still
inside the limit: `account_audit_max_age_days` is 3 and the last result is
dated `2026-08-18T22:01:13Z`, so the gate turns red after
`2026-08-21T22:01:13Z` unless a publish lands first. Whatever the design
sketched above is worth, it would be built on a credential path that is not
currently delivering — establish that it delivers before building on it.

That gap is tracked as [#47][i47], with the evidence and the deadline, so it
does not live only in this paragraph: a note in a design document expires
quietly, and this one has a date on it.

It has not been tried. Two things stand between it and working, and the first
is not a risk to check but a certainty to design around.

**Blocker 1 — the commit message this file mandates suppresses the trigger.**
Step 4 above fixes the publish message as `propagation: account audit
[skip ci]`; the live Routine prompt repeats it verbatim; and every publish on
the branch carries it. Measured 2026-08-20 by parsing `git log` over all 52
commits on `origin/eval-results`: **20** are publishes — 8 from this Routine
(`propagation: account audit`) and **12** from `eval.yml`'s badge step, which
is one publisher under two names, 6 as `eval: workflow-path-audit run + badge`
(the message hard-coded at `.github/workflows/eval.yml:246` today) and 6 as
`eval: pin-actions-to-sha run + badge`, the same step before `29c6e95`
retargeted the fixture. **20 of 20** carry a CI-skip token, so blocker 1 holds
over the whole set and not just the part of it that was counted.

The remaining **32** are not publishes, and *inherited history* describes 31 of
them rather than all: `git merge-base --is-ancestor <sha> origin/main` over all
52 puts **31 on `main`** — the pre-results-branch history and its merges — and
**21 on `eval-results` only**. The 32nd non-publish, `42bb36b` ("Stop
mirroring source onto the results branch"), is a hand-made branch-hygiene
commit that never existed on `main`. Ancestry and publisher are separate
questions and this file previously conflated them: **all 20 publishes are in
the eval-results-only set**, so no publish has ever been an ancestor of `main`,
and an earlier draft of this paragraph put six of them (`bd3dabd`, `99eab53`,
`2dcf4d5`, `0335166`, `dad38ea`, `0feedfb`) into a residue it called inherited
`main` history — a claim that something does not exist, made about six commits
that do.

`[skip ci]` is GitHub's documented instruction to **not create a workflow
run** for a `push` or `pull_request` event, so the workflow above would not
fire on a single one of the Routine's publishes. Nothing about that is
conditional — and it is no longer only documented behaviour. It was measured
here on 2026-08-20, by accident, on the commit that corrected this very
paragraph.

Commit `e4c291b` carries a skip token in its message *body* — not as an
instruction but as a quotation, inside a sentence about the token — and GitHub
suppressed every workflow run for it. Each earlier push to this branch created
three runs (`CI`, `Propagation`, and the PR-title lint); `e4c291b` created
**zero**, twenty-five minutes after the push, while the pull request went on
reporting `mergeable_state: clean`. The token does not have to sit on the
subject line, and it does not have to be meant.

That is the entire failure mode in one commit: nothing red, nothing slow,
nothing logged, and a pull request that looked ready to merge with no run
behind it. What is still *not* observable here is the `eval-results` case
specifically — no workflow in this repo listens on a push to that branch
(parsed 2026-08-20: of five workflows, two declare `push` and both pin
`branches: [main]`), so the absence of *that* particular run cannot be
measured. The mechanism, though, is now witnessed rather than cited.

**So, for anyone editing this file: never put a literal skip token in a commit
message.** Name it in prose ("a CI-skip token"), and check before pushing —
`git log -1 --format=%B | grep -icE '\[(skip ci|ci skip|no ci)\]'` must print
`0`. The one place the literal belongs is step 4's mandated publish message,
where it is doing its job.

Removing the token is a real cost, not a typo fix. `[skip ci]` is what stops a
results-branch publish feeding CI back into itself, and both publishers lean
on it — this Routine and `eval.yml`'s badge commit. Drop it and the push route
opens, but so does every future `eval-results` push into whatever else ever
listens there, including the publish loop's own output. The narrower move is
to leave the message alone and trigger on something `[skip ci]` does not gate
— a `schedule`, a `repository_dispatch`, or simply reading the branch from an
already-running job — which is probably where this goes if it is picked up.
Whichever is chosen, choose it: do not read this section as one precondition
away from shippable.

**Blocker 2 — the push must actually raise a `push` event.** Even with the
message settled, a push made by *that session's* credential has to create a
workflow run rather than being suppressed; pushes from some automation
identities do not. `eval.yml`'s own publish is the case in reverse — it pushes
with `GITHUB_TOKEN`, which GitHub documents as not creating workflow runs at
all — so the two publishers would not necessarily behave alike here. This one
is genuinely untested and needs a live push to settle.

Blocker 1 is locked by an assertion:
`PublishMessageAndPushTriggerTests` in `test/test_propagation.py` parses the
workflow set and step 4's mandated message, and fails if a listener on a push
to `eval-results` is ever added while that message still carries a CI-skip
token. "Listener" there covers the unfiltered spellings too — `on: push` and
`on: [push]` both mean every push on every branch, and both parse to a scalar
or a list under the YAML 1.1 boolean-`True` key rather than to a mapping, so a
mapping-only reader misses precisely the shapes with no `branches:` filter to
inspect. The detector reads `.yaml` as well as `.yml`, since GitHub honours
both and a file that is never opened leaves no trace. Blocker 2 is not lockable
from here.

[i34]: https://github.com/Adam-S-Daniel/skills-evals/issues/34
[i47]: https://github.com/Adam-S-Daniel/skills-evals/issues/47

### The bootstrap fix

Until the first successful run commits `propagation/.bootstrapped`, an absent
`latest.json` is reported as `not-yet-bootstrapped` and the gate **passes**.
Without that, this gate reds every pull request from the day it merges and gets
disabled inside a week — the same death as never building it. Once the marker
exists, a vanished `latest.json` is a hard failure.

That carve-out has now expired: `propagation/.bootstrapped` was published in
`0a532be6`, so from here an absent or stale `latest.json` is a hard failure. It
earned its keep in the window it covered — the transport was broken for the
first three runs, and no pull request was red-flagged on data that had never
arrived.

## What the audit found when it was run for real (2026-08-14, this account)

```
FAIL adam-writing-style [content-drift]: SKILL.md; account updatedAt=2026-05-11
FAIL adam-writing-style [unparseable-frontmatter]: frontmatter is not valid YAML:
     mapping values are not allowed here, line 2, column 246
FAIL fastmail    [content-drift]: SKILL.md; account updatedAt=2026-05-11
FAIL ocr-pdfs    [content-drift]: SKILL.md; account updatedAt=2026-04-21
FAIL rename-pdfs [content-drift]: SKILL.md, scripts/extract_pdf_context.py;
     account updatedAt=2026-05-11
FAIL account-audit: 8 registry-owned skill(s) checked, 9 not owned here, 5 finding(s)
exit 1
```

Four of eight registry-owned account copies have drifted, the oldest by nearly
four months. `adam-writing-style`'s account copy is the sharpest case: its
frontmatter raises a YAML error on an unquoted `: `, so that copy is
**delivered and invisible** — present in the store, registered as a command,
and unable to enter the model's skill list. Nothing else in this programme
catches that, which is why the frontmatter parse is an assertion and not a
comment.

Two findings the issue predicted that did **not** reproduce here:

- **Missing payload files.** All eight account copies carry every git-tracked
  file of their registry counterpart. `missing-payload` ships anyway (it is
  four lines on top of the file walk the content digest already does) but it is
  not evidence of a live incident — if it stays clean on the laptop too, close
  that one as not-reproduced rather than leaving it live and unfalsifiable.
- **Description drift.** All eight descriptions of record currently match the
  registry's. The assertion is kept because it is the one with behavioural
  teeth — only the description gates invocation, so a stale one is a skill that
  silently stops triggering — but it is not firing today.

The CRLF false-positive rate was also smaller than assumed: normalisation is
what keeps the four genuine drifts distinguishable, not what rescues the check
from being ~100% noise.
