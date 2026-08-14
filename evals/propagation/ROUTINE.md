# Tier 3 — the account-store Routine

`harness/run_account_audit.py` is built, tested and **verified against the real
claude.ai account store** (see below for what it found). Its *transport* — the
scheduled cloud session that runs the audit and publishes the result — now
exists too: Routine `trig_0148Zfwf9ZvxRUFuHygJ2dPU`,
`skills-evals: account-store propagation audit`, cron `0 5 * * *` (daily,
05:00 UTC), a fresh session per fire, push and email notifications on. It
**has not fired yet** — first scheduled fire 2026-08-15T05:04Z — so nothing is
published to `eval-results` and the freshness gate is still in its
`not-yet-bootstrapped` (passing) state.

This file was written as a specification rather than a record on the grounds
that a probe nobody can prove works is worse than a gap somebody can read. That
caution was right and is only half discharged: creating the Routine proves it is
scheduled, not that a fired session can clone, audit and push. The first run is
what turns the rest of this file into a record.

## Why a Routine and not a workflow

A GitHub runner has no signed-in claude.ai account, so `~/.claude/skills/synced/`
does not exist there. This is a **surface** constraint, not a credential one:
the audit reads files and spends nothing. Only a session that *is* a
signed-in surface can observe the account store, which is what a cloud session
spawned by a Routine is.

## How it was created

The call that made it, kept as the recipe if it is ever lost:

```
create_trigger(
  name  = "skills-evals: account-store propagation audit",
  cron_expression = "0 5 * * *",          # daily, 05:00 UTC
  create_new_session_on_fire = true,       # a COLD boot every time is the point
  notifications = {push: true, email: true},
  prompt = <the standalone prompt below>,
)
```

`create_new_session_on_fire` matters: a Routine bound to a persistent session
would audit that session's warm state instead of a fresh boot, which is the
thing worth measuring.

## The prompt (fresh-session mode — assume no prior context)

Abridged: the live prompt also carries the known-state baseline from the manual
run below, so a fired session can tell "unchanged" from "new", and the standing
instruction that this Routine only measures — repairing a drifted account copy
is agentskills#59 and needs a browser.

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

## How a human learns that this went red — four layers, three unconditional

1. **The next pull request goes red.** `harness/run_propagation.py`'s freshness
   gate runs on every pull request (`propagation.yml`, job `gate`), reads
   `eval-results:propagation/account/latest.json`, and fails when it is missing,
   older than `account_audit_max_age_days` (3), or reports a failure. This is
   the layer that matters, because it catches the failure mode nothing else
   does: a Routine that **stops firing at all**. It is implemented and tested
   (`FreshnessGateTests`), and the `gate` job carries no event filter, so it
   runs on `propagation.yml`'s daily schedule as well — a dead Routine surfaces
   within a day rather than whenever someone next opens a pull request. That
   schedule and this gate cover different failures and neither subsumes the
   other: only the gate sees a Routine that stopped firing, and only the Tier-2
   arms see a delivery channel that broke with no commit here — their one
   unpinned input is the agentskills registry at `main`. Both report themselves
   rather than trusting anyone to read the Actions tab: the workflow files one
   tracking issue (job `report`), the Routine its push/email notifications —
   plus, when it can reach the API, the marker-tagged issue of layer 3.
2. **Routine `notifications: {push: true, email: true}`** — the only channel
   that reaches someone who never opens GitHub.
3. **One marker-tagged issue**, edited in place (step 5), following the fleet's
   `post-failure-comment` pattern — **best effort, and it may never fire.** A
   Routine created through the MCP meta-tool stores no connectors, so the
   sessions it fires get no `mcp__github__*` tools, and this environment has no
   `gh` CLI: the fired session probably has no route to the GitHub API at all.
   The prompt tells it to skip the issue in that case and report
   `issue: unavailable` rather than improvise one. Nothing else depends on this
   layer — 1, 2 and 4 all ride the published result (the gate reads it over
   plain git, the notification comes from the Routine itself, the badge is
   written from the same JSON), and none of them touches the GitHub API.
4. **A badge** built from the same result (`--badge`), served from
   `eval-results` exactly like the quality badge, naming the count
   (`account skill store: 4 of 8 drifted`).

### The bootstrap fix

Until the first successful run commits `propagation/.bootstrapped`, an absent
`latest.json` is reported as `not-yet-bootstrapped` and the gate **passes**.
Without that, this gate reds every pull request from the day it merges and gets
disabled inside a week — the same death as never building it. Once the marker
exists, a vanished `latest.json` is a hard failure.

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
