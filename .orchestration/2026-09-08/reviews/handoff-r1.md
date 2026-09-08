FOUND — 1 blocker, 2 should-fix, 2 nit

Reviewed at branch `claude/orchestration-handoff` (HEAD `f7a6d62`), diff against
`origin/main` (`7c966ba`): `AGENTS.md` (+5 lines) and `HANDOFF.md` (new, 366
lines). Method: `/code-review` at medium effort applied as a documentation
review, plus my own independent line-by-line cross-check of every number,
date, SHA, issue/PR reference, table, and link — including diffing the two
HANDOFF.md-only commits against each other and, where the worktree itself
holds the ground truth (test file line numbers, the `evals/` fixture census,
`skills-evals` merge-commit SHAs), checking the document's claims against the
actual files rather than only against themselves.

## Findings

### 1. [BLOCKER] Stale "running at the pause" claims contradict the document's own corrected narrative

**Anchors:** HANDOFF.md lines 187–188 ("`#138 3/3 (the third running at the
pause); _agent-guidance#124 2/3 (the second running at the pause)`") and line
298–299 ("`plus the two Opus sessions running at the pause`"), vs. the "In
flight" narrative at lines 108–144.

Section 2's detailed account states both fix rounds were already **done**
before the document was finished, not still running:
- PR #138 (line 118): "Fix 4 LANDED on `b583341` (seven commits, one per
  item, **worker report on the PR**) and was **VERIFIED by the orchestrator
  at 02:33 on 09-08** in a fresh worktree: 825 tests… CI green on the head."
  Nothing here is in progress; the next step is a fresh review round 5
  (line 119), not waiting on a session.
- _agent-guidance PR #124 (lines 136–140): "the orchestrator **VERIFIED**
  `8ec4cb3` **at 03:12** on 09-08… The worker **was interrupted** at 03:27 on
  09-08, inside its mutation battery… **so it posted no report of its own**;
  the thirteen commits… are the record." The worker session ended (was
  killed), it is not "running."

This is not a subtle reading — it's git-provable. The worktree's own history
shows the author caught and fixed exactly this staleness in **one** spot but
missed two others carrying the identical claim:
```
commit f7a6d62 (HEAD) — "docs(handoff): the #123 fix-3 worker was interrupted
before its report; the commits are the record"
-The worker's own report (a PR comment) is the last thing it posts; read it before round 4.
+The worker was interrupted at 03:27 on 09-08, inside its mutation battery, …
```
That fix touched only line 140's text (1 line changed, per `git show f7a6d62
--stat`). Lines 188 and 298–299 still say "running at the pause," unchanged
from the first commit (`69a11b4`, timestamped 03:13:18 UTC — *before* the
03:27 interruption the document later learned about).

**Why it matters for a resuming session:** section 7's resume checklist
(item 4) already gives the *correct* instruction ("re-verify the head… then
launch the next review round"), so a careful resumer who reads the whole file
in order is fine. But the compact "decisions in force" list (§2) and the cost
recap (§4) are exactly the kind of summary a resuming agent skims first, and
both tell it two child sessions are still in flight. Acting on that directly
contradicts §2's own fuller account, risks a wasted `get_session`/
`list_sessions` cycle chasing sessions that no longer exist, and creates
ambiguity about whether the "$1,180 across 88 child sessions" total already
includes the cost of these two sessions (one of which is given an explicit
cost, "$32.99," at line 140) or is exclusive of them.

### 2. [SHOULD-FIX] Cross-repo issue references given as bare text, not links

**Anchors:** HANDOFF.md lines 52 (`agentskills#153`), 53 (`adamdaniel.ai#3536`),
54 (`cms-platform#408`), 56 (`adamdaniel.ai#3538`), repeated at lines 73–74,
161, 176–177.

The account's own standing rule (restated in this session's loaded guidance)
is explicit: "A bare `repo#123` autolinks only inside that repo's own
threads — in chat, another repo's issue, an email or **a doc** it is dead
text, so cross-repo references get the full URL." HANDOFF.md is exactly such
a doc, and it demonstrates the correct form itself elsewhere (e.g. line 12:
`[skills-evals#126](https://github.com/Adam-S-Daniel/skills-evals/issues/126)`),
so the bare instances read as an oversight rather than a deliberate
exception. A reader opening this file outside GitHub's issue/PR UI (which is
the file's whole purpose — it's the offline map to the state) gets inert text
for four distinct external issues and has to reconstruct each URL by hand.

### 3. [SHOULD-FIX] AGENTS.md's one pointer reference is unlinked

**Anchor:** AGENTS.md line 76: "`The live operational state is the status
board, skills-evals#126.`"

This is the single most load-bearing reference in the five-line addition —
the thing a resuming session is told to treat as authoritative — and it is
plain text, not a link. HANDOFF.md links the identical reference correctly at
its own line 12. This is the specific pattern the account's guidance calls
out by name under "what you cite as already done" / "what you are waiting
on": a named noun without its URL. Not a blocker because the actual link is
one click away (via the adjacent `[HANDOFF.md](HANDOFF.md)` link, which then
links #126 correctly), but it's the one place in this diff where the account's
own "anything you name gets its link" rule is violated for the reference that
matters most.

### 4. [NIT] "1.5-day pause" does not match the "40-hour pause" computed from the same timestamps

**Anchors:** HANDOFF.md line 194 ("`00:50 09-06: a 1.5-day pause (resumed
17:10 09-07)`") vs. line 301 ("`a 40-hour pause excluded`").

From the timestamps given, 2026-09-06 00:50 to 2026-09-07 17:10 is 40h20m
(≈1.68 days), not 1.5 days (36h) — an ~11% gap. The "40-hour pause" phrasing
in §4 is the more accurate figure and matches the stated endpoints; the
"1.5-day" description in the decisions list undercounts. Low practical
impact since the exact start/end timestamps are given directly and a reader
can recompute, but the two descriptions of the same event should agree.

### 5. [NIT] One verification claim in the merged-PR table lacks attribution

**Anchor:** HANDOFF.md line 89, Note column for `_agent-guidance#121`:
"`post-merge sync.yml green`".

Every other verification claim in this document is careful to name who
checked and when ("VERIFIED by the orchestrator at 02:33 on 09-08…"). This
one note is a bare assertion with no timestamp or actor, standing out as the
one unattributed "verified" claim in an otherwise consistently
well-attributed document. The table's own preamble (lines 82–85) covers the
general procedure, so this is minor, but worth tightening to match the
document's own evidentiary standard (stated explicitly at line 7: "nothing is
reconstructed from memory").

## Checks performed and passed cleanly (for context on review depth)

- The "69 sub-issues" total: recomputed from the six epic rows independently
  (4 + 9 + 22 + 6 + 7 + 21 = 69) — matches exactly, including both "(21)"
  fixture-count parentheticals (#74–#94 and #100–#120).
- "Stopped by decision 8" §62 exclusion list (`#75, #76, #78, #79, #83, #87
  to #94`, 13 issues) is exactly the complement of the 8 issues from that
  epic's range that do have PRs (merged: #74,#77,#80,#82,#85,#86; parked:
  #81,#84) against the full #74–#94 range (21) — 21 − 8 = 13, matches.
  This is a genuinely precise piece of bookkeeping.
- All seven skills-evals merge-commit SHAs in the "Merged and verified" table
  (`af06d0f`, `a6c882a`, `8d131bd`, `c05d7de`, `f82bd77`, `d5e06ee`, `7c966ba`)
  exist in this worktree's history, in chronological order, each with a
  matching PR number and a monotonically increasing test count (157 → 217 →
  305 → 379 → 475 → 588 → 673) — all verified directly against `git log`.
  "`main` of skills-evals is `7c966ba`" (line 99) matches `origin/main` here.
  (The `_agent-guidance` SHAs and its stated `main` tip could not be checked —
  that repo isn't in this worktree and there is no network access.)
  "the eleven skill fixtures" (line 118) is exactly the number of
  `fixture.yaml` files under `evals/` in this worktree (`find . -name
  fixture.yaml` → 11), once `evals/propagation/fixture.yaml` — easy to
  overlook since `propagation`'s own tests are run via a separate named
  command — is counted too.
- The "#136 round 7's nit" citation (`test/run_tests.py:4308-4309`, line 348)
  points at the exact N-b nested-join comment lines it describes.
- Budget bookkeeping ("Adam's decisions in force" #2) cross-checks cleanly
  against every PR it names: #132/#134/#136/_agent-guidance#122 all appear as
  merged; #130/#131 as parked with "budget spent"; #138/_agent-guidance#124
  match their in-flight fix-round descriptions exactly ("the last of Adam's
  three authorized rounds" = 3/3; "the second of three" = 2/3).
- Harness-lane round-count range ("4 to 12 rounds," line 307-308) is bounded
  exactly by the two harness PRs with explicit round counts: #138 at 4
  rounds (lower bound) and #129 at 12 rounds (upper bound).
- Cost arithmetic: $2,000 + $1,180 ≈ "about $3,200"; $2,378 / 0.93 ≈ $2,557 ≈
  "about $2,560"; $5,500+$1,700=$7,200 and $9,400+$2,900=$12,300 match the
  stated combined estimate exactly; 55+33=88 matches the session split.
- All three markdown tables have matching column counts on every row (no
  malformed table structure); no unbalanced brackets/parens/backticks
  document-wide; no placeholder text (`<<PENDING`, `TODO`, `TBD`, etc.)
  anywhere in either file; every markdown link's URL matches its label's
  issue/PR number and repo.
- The AGENTS.md diff hunk touches only lines below the `## Repo-specific
  additions` marker (confirmed via `git diff origin/main..HEAD -- AGENTS.md`)
  — nothing above the marker is touched.
- Sensitive-data scan: the only email address in either file is the
  permitted noreply identity `4205216+Adam-S-Daniel@users.noreply.github.com`
  (line 225); no token-shaped strings; the one `/root/...` path (line 245) is
  a generic container-sandbox path describing the review procedure, not a
  path that discloses anything private. One adjacent observation, not a
  finding against this diff's own text: decision 3 (lines 189–190) references
  "no history rewrite of real-address commits," i.e. it records that a past
  decision *accepted* a real email address remaining somewhere in this
  account's git history rather than rewriting it out — the diff itself does
  not print that address anywhere, so it doesn't violate the "nothing
  sensitive" check on this text, but it's worth being aware the underlying
  exposure was a deliberate, already-made call and not something this review
  is newly surfacing.
- Structural completeness: all six requested newcomer sections are present
  and findable under numbered H2 headings 1–7 (what the programme is; where
  it stands, with an explicit "Parked on Adam… exact action" table; how it's
  run, including a "Verifying a head" how-to-verify subsection; and a
  numbered resume checklist).

## What I could not check

- No network access, and instructed not to run `claude` or `gh`: every
  GitHub-hosted fact (the actual current body of `skills-evals#126`, the
  three "park comment" permalinks, whether PRs #129/#130/#131/#138 and
  `_agent-guidance` PR #124 are still open with the states described, the
  claimed merge-conflict shapes in #130/#131, the `_agent-guidance` repo's
  SHAs `5b371e3`/`3d972b4`/`5f13def`/`8ec4cb3`/`df01967` and its stated main
  tip) is unverified against GitHub and rests on the document's own say-so.
- `_agent-guidance` is not checked out alongside this worktree, so none of
  its file/line claims (test counts 1166/1256/1716/1584, gate outputs,
  `.github/` unchanged-since claims) could be checked against real content.
- I did not run this repo's test suite (`test/run_tests.py`,
  `test_propagation.py`) to confirm the specific counts attributed to `main`
  or to PR #138 / `_agent-guidance` PR #124's branches — those branches
  aren't present in this worktree, and running the full suite (which needs
  pip installs and sibling-repo checkouts per lines 273–280) is outside a
  read-only documentation review.
- Cost figures ($2,000 orchestrator spend, $27/round, $30–$50/$3–$15 per fix
  round, etc.) are plausible and internally consistent with each other but
  are not independently auditable from any ledger in this diff.
- Whether "1.5-day" was meant loosely enough to cover 40 hours is a judgment
  call I could not resolve beyond flagging the arithmetic (finding 4).
