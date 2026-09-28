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
5. **Permissions:** `pull-requests: write` and `actions: write`, used only by
   the auto path above. **Revised by the adversarial round 1 review on #209
   (F2):** these two scopes live on a separate job, `roster-pr`, never on
   `eval` itself — `eval` is the job that runs the bypass-permissions agent,
   and giving the whole job a PR/workflow-dispatch scope for one late step
   would have handed that scope to the agent too. `roster-pr` runs
   `pull-requests: write, actions: write, issues: write, contents: write`
   (the `contents: write` reason is round 2's revision, immediately below);
   `eval` keeps exactly its pre-#209 scopes
   (`contents: write, id-token: write, issues: write`) and never calls `gh
   pr`/`gh workflow run` at all. `roster-pr` needs `issues: write` too: the
   tracking issue's final wording (a PR number, "merging automatically",
   "could not be turned off") depends on what `roster-pr` did to the PR, so
   it finishes editing the SAME issue the `eval` job's propose step found or
   left with neutral text, rather than splitting one issue's text across two
   writers with no shared view of the outcome. Workflow-level `permissions:`
   is `{}`. `roster-pr` runs on EVERY eval run (`if: !cancelled()`),
   `roster_mode: proposal` included — a stale `roster/proposal` PR's
   auto-merge must come off, or the PR must be closed if the roster no
   longer differs, whether or not this run's propose step reached the auto
   path (F3, below). **Revised again by adversarial round 2 on #209 (S2):**
   `roster-pr` carries `contents: write`, not `contents: read` —
   `enablePullRequestAutoMerge`/an immediate merge both need write access to
   contents even though this job performs no checkout and runs no
   repository code; only `gh` calls happen here. **Revised again by B1
   (round 3 on #209, blocker):** the compute/render/admit/push path — and
   with it `issues: write` — moved off `eval` entirely, onto a third job,
   `roster` (see the Round 3 section below); `eval` keeps only `contents:
   write, id-token: write`, and `roster-pr` now `needs: [roster, eval]`
   rather than `needs: eval` alone.

## Round 2 (adversarial review on #209, spec-roster-mode-r2.md): `roster-pr`
## trusts nothing the `eval` job produced

Round 1 (F2, above) moved the PR/workflow-dispatch scopes off the job that
runs the bypass-permissions agent. It did not go far enough: `roster-pr`
still READ its auto/proposal decision, and the sha it enabled auto-merge
on, from that same job's own outputs — `needs.eval.outputs.*` — which are
just as reachable by a compromised `eval` job as a `pull-requests: write`
scope would have been, through `$GITHUB_OUTPUT` (any earlier step, or a
`BASH_ENV`/shell-startup trick, can append to it) or through the checkout
that step's `git rev-parse HEAD` reads.

**Threat model:** treat EVERYTHING the `eval` job produces — its job
outputs, the commit it pushed to `roster/proposal`, its workspace — as
untrusted. `roster-pr` (no checkout of its own) is the only place trust is
established, and it establishes it from two sources only: GitHub's own API,
and the triggering commit `$GITHUB_SHA` on `main` (`github.sha`, fixed at
dispatch time and never touched by whatever the `eval` job's checkout later
does — the same property that makes a `GITHUB_TOKEN` PR immune to a
`pull_request` re-trigger, reused here as the one thing on the runner a
compromised `eval` job cannot rewrite).

Four checks, all in `roster-pr`, all before `gh pr create/edit/merge --auto`
and the `ci.yml` dispatch:

1. **The decision itself is re-read, not re-used.** `roster_mode` is read
   fresh from `evals/roster-policy.yml` at `$GITHUB_SHA` via the contents
   API (`gh api "repos/$REPO/contents/evals/roster-policy.yml?ref=$GITHUB_SHA"
   --jq .content | base64 -d`, parsed with `yaml.safe_load`; the same
   missing-key/unreadable-file/bad-value fallback rules as the `eval` job's
   own read). The `eval` job's `ROSTER_MODE` output is still read and
   logged, but never used for the decision — a compromised `eval` job
   forging `roster_mode=auto` over `$GITHUB_OUTPUT` while the committed
   policy still says `proposal` (the kill switch) no longer works.
2. **The pushed branch's actual head is re-read from the API**
   (`gh api repos/$REPO/git/ref/heads/roster/proposal --jq .object.sha`,
   40-hex validated) and required to equal `$PUSHED_SHA`. `$PUSHED_SHA`
   itself is still the `eval` job's own claim, so this is what makes that
   claim mean something: the job cannot enable auto-merge on a sha it has
   not independently confirmed IS the branch's current head.
3. **The shape, the content and the commit's own identity are all
   re-verified, not re-trusted (round 3 on #209 added the last of these).**
   `gh api "repos/$REPO/compare/$GITHUB_SHA...$PUSHED_SHA"` must show
   `status == "ahead"`, `ahead_by == 1`, `behind_by == 0`,
   `[.files[].filename] == ["evals/roster.yml"]` with that file's status
   `modified` — mirroring the path-allowlist precedent in
   `dependabot-auto-merge.yml`'s `auto-merge` job (a fixed set of paths a
   bot's own change may touch, checked server-side rather than trusted from
   the bot's own diff) applied here to a single fixed path rather than a
   manifest glob — AND that the one commit's own message and author email
   equal exactly what the propose step commits with
   (`roster: proposed model roster (run <RUN_ID>)`,
   `skills-evals@users.noreply.github.com`). An extra commit riding along on
   the `eval` job's checkout (ahead_by 2), an extra file in the same commit,
   `main` having moved on since this run started (behind_by > 0), or a
   planted commit message/author (round 3 repro `test_B1_hostile_roster_
   content_single_file_is_auto_merged`: a hostile `render_roster_yaml.py`
   in the untrusted workspace rewrites the FILE content while a git
   `commit-msg` hook plants a closing keyword — the file-shape checks alone
   never catch either) each fail this check.
4. **Only on `main`.** `roster-pr`'s own `if:` gains
   `&& github.ref == 'refs/heads/main'` — a dispatch on any other ref never
   has a `$GITHUB_SHA` worth trusting as "the committed policy", so this job
   (and the auto-merge surface it alone holds) never runs for one.

If any of 1–3 fails on a run that would otherwise attempt auto-merge: the
attempt is not made; an open `roster/proposal` PR (from an earlier run) has
its auto-merge disabled the same way every other "did not (re-)enable"
path in decision 4 above does; and the tracking issue's text names which
check failed, in fixed wording per check (never anything read off the
failing API response) — "the pushed branch's head does not match this
run's proposal" for check 2, "the pushed commit did not verify as a single
`evals/roster.yml` change ahead of this run's checkout" for check 3.

**Cancellation window.** A run cancelled after the `eval` job's push but
before `roster-pr` runs can leave an EARLIER run's auto-merge still armed —
cancellation does not itself disable anything. No `test` run lands on the
new head unless something dispatches `ci.yml` on it, and nothing does until
`roster-pr` next runs (the next scheduled or dispatched `eval` run) and
performs checks 1–3 against whatever `$GITHUB_SHA` is current then. This
window is accepted rather than closed: closing it would mean either a
`roster-pr` that runs even when `eval` is cancelled before pushing (nothing
to verify) or a third job whose only purpose is "disable on cancel", for a
window that self-heals on the very next run.

## Round 3 (adversarial review on #209, spec-roster-mode-r3.md): the compute/
## render/admit/push path moves off the agent's own job entirely

Round 1 (F2) moved the PR/workflow-dispatch scopes off the `eval` job; round 2
made `roster-pr` re-verify rather than re-trust what that job produced. Both
left the computation, rendering, admission and push of the proposal itself —
"Refresh the model roster" and "Propose a roster change" — running as later
STEPS in the SAME job as the bypass-permissions agent. That job's runner is
one filesystem: even though the `contents`/`issues` write credential is
step-scoped `env:` and never exists while the agent step runs, anything the
agent could have planted on that runner (a modified `git`, a shell rc file, a
`bash -c` alias) is still there when the later, credentialed step runs. B1's
fix is a third job, `roster`, that computes, renders, admits and pushes the
proposal on a runner the agent never touches at all — before, after or
alongside `eval`, never depending on it.

**The new job boundary.** `roster` (`contents: write`, `id-token: write`,
`issues: write`): its own checkout of `skills-evals` only (none of the four
fixture/registry repositories), its own Node/Claude-CLI/Python setup, its own
WIF mint, then "Refresh the model roster" and "Propose a roster change"
unchanged in substance. It must never `needs: eval` — the whole point is
independence, not sequencing. `eval` keeps its own checkout, its own separate
WIF mint (never shared with `roster`'s — two jobs, two runners, no credential
in common), the fixture run and the badge/commit; `issues: write` came off
it since nothing here writes the tracking issue any more. `eval` DOES
`needs: roster`, in one direction only, so its badge step can commit an
EXHIBIT copy of `roster`'s own computed roster
(`needs.roster.outputs.roster_latest_json`, ADR 0001 decision 3: read by no
decision) without either job reaching into the other's runner; `if:
${{ !cancelled() && !inputs.roster_only }}` keeps a `roster` failure
non-fatal to the eval, exactly as before. `roster-pr` becomes the only job
depending on BOTH (`needs: [roster, eval]`): the only place both an
independent re-verification of what `roster` published (B1.1–B1.3, now read
via `needs.roster.outputs.*`) AND the `eval` job's own outcome
(`needs.eval.result`) are both in reach at once — the tracking issue's eval
sentence, which used to read `steps.eval.outcome` inside the single shared
job, is computed here now instead, since `roster` structurally cannot know
it (see below).

**What "the eval job's outcome" costs.** Because `roster` never depends on
`eval`, its own "same"/frozen-same tracking-issue writes can no longer say
whether the eval succeeded, failed, or didn't run this dispatch — only
whether `roster_only` was set (known synchronously from the event payload,
same as before). The fuller success/failure/unknown sentence — read from
`needs.eval.result`, a fixed GitHub Actions word, never trusted as free text
— lives in `roster-pr` alone now, for the "differs"/"rejected" bodies it
writes. `needs.eval.result == "skipped"` reads unambiguously as "this was a
`roster_only` dispatch" because the `eval` job's own `if:` is now EXACTLY
`!inputs.roster_only` — no other reason skips that job.

**Should-fix 1 (this round): the commit itself, not just its shape, is
verified.** Round 2's check 3 (above) confirmed the pushed commit's file
diff — one file, `evals/roster.yml`, modified. It never confirmed the
commit's own MESSAGE or AUTHOR, so a hostile `scripts/render_roster_yaml.py`
planted in the `roster` job's untrusted-in-principle-but-previously-
unverified workspace, or a `commit-msg` git hook, could ride along inside a
file-shape-clean commit and land arbitrary content — a closing keyword, an
`@mention` — in a pull request `roster-pr` then auto-merges
(`test_B1_hostile_roster_content_single_file_is_auto_merged`, the round-3
adversarial repro this fixes). `verify_publish` in `roster-pr` now also
requires the compare's one commit to carry EXACTLY the message the propose
step commits with (`roster: proposed model roster (run <RUN_ID>)`) and the
bot's own author email (`skills-evals@users.noreply.github.com`); anything
else fails the same way an extra file or a wrong status would. Separately,
`harness/roster.py`'s rendered `summary.md` — the one piece of this run's
own text that legitimately varies, shaped in part by the untrusted census —
is neutralised in place (a zero-width space after `@` and before a `#`-digit
run) the moment it is read, before it can reach any PR or issue body, so a
closing keyword or mention embedded in the SUMMARY TEXT itself (rather than
smuggled via the commit) is defused too.

**B2: a planted future `catalogue_seen.last_seen` can't be used to poison
history.** `_update_catalogue_seen`'s ageing math (`now - seen_at > max_age`)
never ages out an entry whose `last_seen` is in the future — the round-3
repro `test_B2_future_catalogue_seen_never_ages_out` shows one planted at
`2099-12-31` still present after 4+ simulated years. Rather than changing
that ageing math (which only ever runs on data already inside the trusted
`evals/roster.yml`, i.e. already reviewed), `committed_roster_problems` — the
one gate every proposal and every committed file must pass — now also
rejects any `catalogue_seen` entry whose `last_seen` is later than the
document's own `generated_at`. A hostile proposal carrying such an entry is
rejected at admission, before it can ever be pushed or merged.

**Should-fix 2–6 (mutant-proofing and wording), briefly:** the round-3
mutation run found five single-fault gaps in `verify_publish`'s compare
check (dropping `ahead_by == 1`, the filename check, the `modified` status
check, or loosening either to a prefix/inequality) that survived only
because every existing test happened to violate more than one clause at
once; dedicated single-fault tests close each. A failed policy read
combined with a forged `roster_mode: auto` claim from the untrusted job
still had to fall back to `proposal` (it already did; a test now proves it,
fail-closed). The PR lookup's `--jq` filter now also requires
`.head.ref == "roster/proposal"`, not just the same repository, so a
same-repo PR opened from some other branch can never be matched. And three
tracking-issue/PR sentences that used to say "merge it after CI" regardless
of WHY the automatic path didn't run now distinguish: a push that never
succeeded this run ("this run's proposal was not pushed; review before
merging" — never implying this run's content is on the PR), and a
verification failure ("inspect before merging" plus the specific failed
check — never implying the content is safe to just merge).

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
- **A bot merge gets no `test` run on the merge commit itself** (N2,
  adversarial round 1 on #209): the same `GITHUB_TOKEN`-does-not-retrigger
  rule above means `main`'s post-merge sha never gets its own `test` run.
  What actually satisfied the ruleset's required check is the `test` run
  this workflow dispatched on the PR's HEAD (`roster/proposal`'s pushed
  sha), which ran against `main` as it stood at the START of this run — not
  against whatever else may have merged to `main` between this run starting
  and GitHub performing the merge. That gap is the same one any PR merge
  carries between its last CI run and the merge button; `roster_mode: auto`
  does not widen it, it just removes the human who would otherwise notice.
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
