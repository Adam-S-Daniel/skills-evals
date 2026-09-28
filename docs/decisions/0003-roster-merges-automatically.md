# ADR 0003: The roster proposal merges automatically, behind `roster_mode`

- **Status:** accepted (2026-09-28)
- **Issue:** none filed; Adam's decision of 2026-09-28. Settings-as-code
  follow-up for the "Allow GitHub Actions to create and approve pull
  requests" repo setting this depends on:
  [repo-settings#51](https://github.com/Adam-S-Daniel/repo-settings/issues/51)
  (another session).
- **Deciders:** Adam, directly — this amends
  [ADR 0001](0001-roster-trusted-on-main.md)'s human-merge decision rather
  than following from any measurement in this repo.

## Context

[ADR 0001](0001-roster-trusted-on-main.md) decided that a computed roster is
a proposal, not the running set: the "Propose a roster change" step in
`.github/workflows/eval.yml` pushes a differing proposal to the bot-owned
branch `roster/proposal` and files one tracking issue, and — in its own
words — "a human opens the PR from a valid branch and merges it after CI."
That decision's Consequences section is explicit that this is deliberate:
"This is the fleet's sanctioned bot-write path — a branch and a PR a human
merges — not `PR + auto-merge` and not a bypass actor."

The fleet guidance repeats the same rule in general form (`AGENTS.md`,
"Automation vs branch protection"): "PR + auto-merge is not a sanctioned
bot-write path for fleet repos." Adam's decision here is to use it anyway,
for this one workflow, behind a flag — he considers a ruleset bypass actor
(the alternative ADR 0001 priced at 6–15 points and rejected) a semantic
workaround around the same protection PR + auto-merge is meant to route
around, not a materially different guarantee: both let a bot's own commit
reach `main` with no human reading it first, unless a human is the one
merging. `PR + auto-merge` is the cheaper way to get the property he
actually wants (a required, green `test` check on the exact commit that
lands) without asking for a `repo-settings` bypass-actor change.

Facts measured on this repo before this decision: the `main` ruleset
requires a PR with 0 approvals, merge commits only, and the required status
check context `test` (the `test` job in `.github/workflows/ci.yml`); the
repo's `allow_auto_merge` is `true`; `ci.yml` has a bare `workflow_dispatch:`
trigger and no concurrency group; a PR opened with `GITHUB_TOKEN` does not
fire `pull_request` workflows, so nothing dispatches `ci.yml` on
`roster/proposal` unless this workflow does it itself, and a `GITHUB_TOKEN`
`workflow_dispatch` does create a run whose `test` check lands on the head
sha and satisfies the ruleset. Adam enabled "Allow GitHub Actions to create
and approve pull requests" on this repo for this change.

## Decision

1. **`roster_mode` in `evals/roster-policy.yml`** (`auto` or `proposal`)
   selects the behavior. Set to `auto` here. A missing key, or any value
   other than the two, is `proposal` — silently for a missing key, with a
   fixed `::warning::` for a present, wrong value. `harness/roster.py` never
   reads this key; it is machinery for the "Propose a roster change" step
   alone, read from the trusted `main` checkout.
2. **`auto` changes only what happens to an already-valid, already-pushed
   proposal, and only on a clean run.** The render + admission checks, the
   `roster/proposal` branch push, and the tracking issue are unchanged.
   Auto-merging is attempted only after the branch push succeeds AND this
   run's vendor-default probe was clean (`defaults_failed` = 0 and
   `defaults_mismatched` = 0, [ADR 0002](0002-roster-follows-vendor-defaults.md)'s
   freeze). A probe failure or mismatch, or a rejected proposal, keeps
   today's behavior exactly — issue filed, human decides — and the issue
   says why the automatic merge did not run.
3. **The auto path:** find or open a pull request from `roster/proposal`
   onto `main`; dispatch `ci.yml` on that branch so its `test` job reports on
   the pushed sha (nothing else would, per the Context section above); enable
   `gh pr merge --auto --merge --match-head-commit <pushed sha>` on it. Any
   of those `gh` calls failing is a fixed `::warning::`, never a failed job —
   the roster and its branch already exist either way — and the tracking
   issue then says a human must open or merge the PR, the same as
   `roster_mode: proposal`. A "same" run under `roster_mode: auto` closes an
   open `roster/proposal` PR alongside the tracking issue, for the same
   reason it closes the issue: the roster no longer differs.
4. **Auto-merge is turned OFF on every run that does not (re-)enable it,
   whenever a pull request is open.** `--match-head-commit` is checked only
   when auto-merge is *enabled*, not at merge time — so a PR an earlier
   clean run opened would otherwise keep auto-merge across a later push it
   never approved (a probe going dirty, `roster_mode` switching back to
   `proposal`, or a mid-attempt `gh` failure). On every one of those paths —
   including a proposal REJECTED before the branch was even touched — an
   open PR from `roster/proposal` has `gh pr merge --disable-auto` run on
   it, wrapped the same way (`::warning::`, never a failed job), and the
   tracking issue says whose merge was turned off and why.
5. **Permissions:** `eval.yml`'s `permissions:` gains `pull-requests: write`
   and `actions: write`, used only by the auto path above.

## Consequences

- **The untrusted census can now move which tiers are on the roster with no
  human reading the diff first**, when the probe is clean. `test` still
  gates shape (the committed-roster contract, admission, the harness's own
  suite) but not the reviewer judgment ADR 0001 reserved. This is the
  decision's whole cost, and Adam took it knowingly rather than as an
  oversight.
- **A bot merge on `main` does not trigger `push`-triggered workflows** the
  way a human's merge commit does, for the same reason a `GITHUB_TOKEN`-
  opened PR does not fire `pull_request` workflows: `GITHUB_TOKEN` actions
  do not re-trigger `on:` events by design, to prevent runaway recursion.
  Nothing in this repo currently depends on a `push`-to-`main` trigger for
  roster changes, so this is recorded rather than mitigated.
- **The toggle also lets Actions approve pull requests generally**, not only
  merge them, on this repo — a side effect of the one GitHub setting this
  depends on. Harmless at the ruleset's 0 required approvals: there is
  nothing to approve away.
- **Switching back is one edit.** Setting `roster_mode: proposal` in
  `evals/roster-policy.yml` restores ADR 0001's human-merge flow exactly;
  no code path is deleted, so the switch is reversible without a revert.
- **Managing "Allow GitHub Actions to create and approve pull requests" as
  code**, rather than by hand in repo settings, is out of scope here and
  tracked on [repo-settings#51](https://github.com/Adam-S-Daniel/repo-settings/issues/51).

## How to switch back

Set `roster_mode: proposal` in `evals/roster-policy.yml` and merge that one-
line change. The next differing proposal is pushed to `roster/proposal` and
filed as a tracking issue exactly as before this ADR; nothing else changes.
