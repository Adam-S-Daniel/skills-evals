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

**The audit's verdict is now advisory on a pull request and fatal on the
schedule.** It was originally fatal on both, on the reasoning that `main` carries
no required status checks so a red check is a loud signal rather than a merge
blocker. What that missed is how long the red lasts. The drift lives in the
claude.ai account store: no commit in this repo caused it and none can clear it,
so for those four days every pull request opened here wore someone else's red. A
check that is red for reasons its reader cannot act on is one people learn to
scroll past — and a gate mentally filed under "always red" has stopped being a
gate, which is the same death as never building it. The change was made while
the gate happened to be green again, which is the right time to make it: the
policy question is about the next episode, not this one.

So the pull-request run prints `WARN freshness-gate [reported-failure]` with the
drifted skills named, and passes. The scheduled run still fails, and `report`
still files the tracking issue — that is the surface where a stale verdict was
always supposed to be answered. What stays fatal EVERYWHERE is liveness: a
`missing`, `stale` or `unreadable` result means the audit is not reaching us at
all, and catching a Routine that quietly stopped firing is this gate's entire
reason to exist. The split is between "the audit told us something bad" and
"the audit is not talking to us" — only the second is this repo's to answer.

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

Residual risk: if the bound session is archived or reclaimed, the binding dies.
The gate catches that — a publisher that stops publishing goes stale within
three days — so it is detected, just not instantly.

Root cause and fix are recorded in
[skills-evals#20](https://github.com/Adam-S-Daniel/skills-evals/issues/20).

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
   older than `account_audit_max_age_days` (3), or reports a failure. A stale
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
   files one tracking issue); the Routine no longer reports itself at all — see
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
   `post-failure-comment` pattern — **unavailable, and now known to be.** A
   Routine created through the MCP meta-tool stores no connectors, so the
   sessions it fires get no `mcp__*` tools, and this environment has no `gh`
   CLI: the fired session has no route to the GitHub API at all. The live
   prompt no longer attempts it and reports `issue: unavailable` instead.
   Nothing else depends on this layer, but the independence once claimed for
   the others was narrower than it looked — 1 and 4 both ride the published
   result, so the publish failure took them both, and only 2, which came from
   the Routine itself, was ever independent of it.
4. **A badge** built from the same result (`--badge`), served from
   `eval-results` exactly like the quality badge, naming the count — published
   in `0a532be6` reading `account skill store: 4 of 8 drifted · 2026-08-14`.

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
