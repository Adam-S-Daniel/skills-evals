NOT CLEAN — the S4 wrap-column fix introduces a new blinding tell (a model-shaped draft's two-line sign-off is collapsed while both hard-wrapped references keep theirs, so the agent's draft is the odd one out in every recruiter-reply trial), the deletion of the whole-reply fallback is killed by no test, and a line is dropped as "seed material" on a normalisation that has deleted content from it — so a crafted line carrying avoid-list words is removed whole and all four recruiter-reply checks pass.

# skills-evals PR #131 — round-4 code review

Head `f01c1e6fe3ff762ec5581e1cd6ab4eae57ea5cbc` (merge of `85ea6af` with
`origin/main` at `a6c882a`). Round-3 head `a74b526`. Reviewed against the
fix brief `$SP/briefs/81-fix3.md`, round 3's two reports, and
`/home/user/agentskills/plugins/adam/skills/adam-writing-style/SKILL.md`
(read in full; every calibration example is a blockquote).

Everything below was measured in `$SP/rev131d-code` (a verified plain
export of `f01c1e6`, `objective.py` md5 `480d8fe5…`), against
`$SP/rev131d-ref` (`a74b526`, md5 `f87589d5…`) and `$SP/base131d`
(`origin/main` `a6c882a`). **No file in `$SP/rev131d-code` was modified**:
every mutation ran in a throwaway copy at the same directory depth
(`$SP/mut-work-tree`, deleted after each run), so the tree md5 is unchanged
(§10). `/home/user/skills-evals` read-only throughout (`git
show/diff/log/archive`; `git status --short` empty, HEAD still `527c729`).
No network, no real `claude`, nothing posted to GitHub, no sessions or
routines. Two live python processes remain in this container
(`…/rev131d-mut/harness/run_eval.py`, and a `test/run_tests.py`) — they
belong to the **adversarial** reviewer's tree, not to me; I started none
and killed none.

## 1. Verifiers

| Verifier | Expected | Measured |
|---|---|---|
| `python3 test/run_tests.py` | 345, 2 skipped, exit 0 | **345 tests, OK (skipped=2), exit 0** |
| `python3 test/test_propagation.py` | 164, 1 skipped | **164 tests, OK (skipped=1), exit 0** |
| `run_eval.py evals/adam-writing-style/recruiter-reply --arm objective-only` | exit 1 | **exit 1**, 4 checks, all "no transcript" |
| `run_eval.py …/proposal-bio --arm objective-only` | exit 1 | **exit 1**, 3 checks |
| `run_eval.py …/self-appraisal-opening --arm objective-only` | exit 1 | **exit 1**, 3 checks |

The two skips are `pypdf not installed` in `TestIssue82` (main's
rename-pdfs tests). The avoid-list drift tests are **not** skipped — a
third skip would have appeared if `_skill_md()` had returned None.
345 = 262 (a74b526) + 23 new branch tests + 60 from main's merge.

## 2. The DESIGN DECISION, clause by clause

| Clause | Verdict | Pin |
|---|---|---|
| `strip_quoted` withdrawn | YES — no reference anywhere in the tree (`grep -rn strip_quoted` = 0 hits); AST symbol diff confirms it is the only function lost in the merge | `objective.py` (absent) |
| `strip_seed_material(transcript, seed_dir)` | YES, signature `strip_seed_material(text, seed)` | `objective.py:729` |
| Decides by PROVENANCE: normalised seed lines ≥ 24 chars **plus** the normalised whole-seed text | YES; `_SEED_LINE_FLOOR = 24`; whole text = each file's lines joined by a space, files joined by `\n` | `objective.py:586`, `637-671` |
| A transcript line goes only if its normalised form **is** a seed line **or is** a ≥24-char substring of the seed text | YES | `objective.py:769-772` (`is_seed_line`) |
| Fenced or HTML-wrapped blocks go only when **wholly** seed text | YES (`all(is_seed_text(i) for i in body)`); blockquote RUNS are treated the same way — an extension beyond the letter of the decision, but conservative: a run is dropped only when every non-blank line in it is seed text | `objective.py:783-786`, `_wrapped_blocks` `:672-708`, `_quote_runs` `:711-726` |
| Kept lines lose leading quote markers and fence delimiter lines | YES (`content = [_unquote(line) …]`, delimiters unioned into `drop`) | `objective.py:766`, `787-790` |
| BOTH `must_match` and `must_not_match` score over the residue | YES — one `text` string reaches `_text_matches` | `objective.py:850-854` |
| Whole-reply fallback deleted | YES in the code; **not pinned by any test** — see finding 2 | `objective.py:791` |
| Opt-in per check with `strip_seed: true`, on all ten #81 checks and no other fixture | YES — YAML-parsed across `evals/**/fixture.yaml` (8 fixtures): exactly 10 keys, all on the three #81 fixtures, `windows-elevation-from-wsl` has none | three `fixture.yaml`s; `run_tests.py:4323`, `:4330` |
| `run_checks` passes `seed` only when the key is set | YES | `objective.py:904-909` |

Docstring accuracy: `strip_seed_material`'s docstring (`:729-763`) and the
fixtures' README (`evals/adam-writing-style/README.md:87-137`) both state
the design and both documented limits. Two limits they do **not** state are
findings 3 and 4.

## 3. Quoting shape × fixture, through the real scorer

`objective.run_checks(fixture, seed, seed, transcript=…)` with the real
fixtures and seeds. **A** = the fixture's own committed `in-voice`
reference (marker stripped) plus the quoted whole seed → must pass every
check. **B** = a contentless filler that greets/hedges/registers correctly
but carries neither fact, plus the quoted whole seed → must fail at least
one. Both orders measured (draft first, then quote; and quote first).
**120 cells.**

| Shape | quote AFTER the draft (A / B) | quote BEFORE the draft (A / B) |
|---|---|---|
| `>` at 0 spaces | PASS ×3 / fails `cites-both-facts` ×3 | PASS ×3 / fails `cites` ×3 |
| `>` at 1 space | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| `>` at 2 spaces | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| `>` at 3 spaces | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| ``` fence, no info | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| ```markdown (info string) | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| `~~~` fence, no info | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| `~~~text` (info string) | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| unterminated ``` fence | PASS ×3 / fails `cites` ×3 | **recruiter-reply A fails `opens-with-a-hedge`**; other 2 PASS / fails `cites` ×3 |
| 4-space indented block | PASS ×3 / fails `cites` ×3 | **recruiter-reply A fails `opens-with-a-hedge`**; other 2 PASS / fails `cites` ×3 |
| lazy continuation | PASS ×3 / fails `cites` ×3 | **recruiter-reply A fails `opens-with-a-hedge`**; other 2 PASS / fails `cites` ×3 |
| nested `> >` | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| fence inside a blockquote | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| blockquote inside a list item | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| HTML `<blockquote>` | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| HTML `<details>` (+`<summary>`) | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| HTML `<pre>` | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| verbatim paste, no marker | PASS ×3 / fails `cites` ×3 | **recruiter-reply A fails `opens-with-a-hedge`**; other 2 PASS / fails `cites` ×3 |
| CRLF (`>` quote, `\r\n`) | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |
| NBSP before `>` | PASS ×3 / fails `cites` ×3 | PASS ×3 / fails `cites` ×3 |

**116 of 120 cells correct.** Column B never all-passes anywhere — round-3
code B-2 and round-3 adv S-6 are closed. The four exceptions are all
column A (a genuine draft scored as failing) and all the same mechanism:
the four **unmarked** shapes leave the seed's short lines behind, and when
the paste sits above the reply those leftovers occupy the four-line opening
window. This is documented in the test file
(`run_tests.py:4226-4233`) as the length floor's known limit; finding 3
is the half of it that is not documented and that fires in the
false-**positive** direction.

The brief's named extra cases, all three fixtures:

| Case | Result |
|---|---|
| a good deliverable presented **entirely** as a blockquote | **ALL PASS** ×3 |
| the same after a one-line preamble (`Here is the draft:`) | **ALL PASS** ×3 |
| the same inside a ``` fence (with and without a preamble) | **ALL PASS** ×3 |
| a plain reply with one stray unbalanced ``` line at line 3 | **ALL PASS** ×3 |
| `Here is the draft:` + a **blockquoted** buzzword reply | fails `no-avoid-list-words` ×3 (and the register + facts checks) |
| the same fenced | fails `no-avoid-list-words` ×3 |
| a seed line shorter than 24 chars reused in the agent's prose (`"Hi Adam,"`) | not stripped — present in the residue; all 4 checks pass |
| a fact restated in the agent's own sentence (REQ-4417 / Section 508 / deploy-scaffold) **beside a full `>` quote of the seed** | **ALL PASS** ×3 |
| a reply that is nothing but the quoted seed | residue is `''`; fails 3/4 (recruiter-reply), 2/3 (bio), 2/3 (appraisal) |

Round-3 adv B-1(a) — a wholly quoted reply ALL-PASSing — is closed:
measured `a74b526` fails only the register check; head fails the greeting,
the hedge **and** the facts.

## 4. Per item

Mutations were run against the **whole** suite in a fresh copy; "red (n)"
is the failure count. Hollowness column: head's `test/run_tests.py` dropped
into a copy of `a74b526`, running the named test.

| Item | Verdict | Pin (file:line) | Hollowness vs `a74b526` | Mutation → result |
|---|---|---|---|---|
| **B1** WSL fixture not narrowed | **FIXED** | opt-in `objective.py:908`; `run_tests.py:4344` (`…fenced_handoff…`), `:4330` (`…no_other_fixture…`) | fenced-handoff test RED on ref (`transcript lacks /register-tasks\.ps1/`); the no-other-fixture test is green on ref (trivially — no fixture there has the key) | `if check.get("strip_seed")` → `if True` → red (1); `strip_seed: true` added to the WSL fixture → red (2) |
| | | Fenced ```powershell handoff through `run_checks` **and** `transcript_matches`: **origin/main True, head True, a74b526 False** | | |
| **B2** quoted material satisfies checks | **FIXED** | `objective.py:729-791` | `test_quoted_seed_material_is_not_the_agents_writing` RED on ref (24 subtest failures) | disable the pre-pass → red (92) |
| **S1** bans vs requirements over one residue | **FIXED** | `objective.py:850-854`; `run_tests.py:4249` (`…deliverable_the_agent_chose_to_format…`), `:4032` (avoid list) | RED on ref (2 failures: `greets`, `cites` on a blockquoted good reply) | covered by the B2 mutation |
| **S2** `_validate_skill_name` before the writer | **FIXED** | `run_eval.py:698-711` | RED on ref (`'judge_mode_unsupported' unexpectedly found`) | delete the moved call → red (2). Measured end-to-end: `skill: ../../ESCAPED` + `mode: pairwise`, `--arm both` and `--arm objective-only` → exit 2, **zero files written anywhere**; on `a74b526` the same fixture wrote `$W/ESCAPED/<ts>/report.md` + two `summary.json` two directories above `--results-dir` |
| **S3** non-dict `judge:` | **FIXED** | `run_eval.py:719-728` | RED on ref (4 failures) | restore `(fixture.get("judge") or {}).get(...)` → red (4). Measured: `judge:` as a **list** and as a **string**, both arms → exit **2**, `invalid_judge_block` named in stdout, `report.md` + per-arm `summary.json` written under `--results-dir` (`{"error": {"type": "invalid_judge_block", …}}`); on `a74b526` all four combinations were exit 1 + traceback + no artifacts |
| **S4** wrap column | **FIXED for the named case, NEW REGRESSION** | `judge.py:485-509` (`_wrap_width`) | (test modified, not added) | `median(non_final)` → `max(...)` → red (1). `_HYPERLINKED_DRAFT`: a74b526 `[8,63,27,203,20,7,11]` (wrap survived) → head `[8,91,224,7,11]`, sign-off intact. **But see finding 1** |
| **S5** permutation buckets | **FIXED** | `judge.py:342` (`/v2/`); `run_tests.py:5056`, `:5080` | (tests modified) | drop `/v2/` → red (6). Measured `offset % 6`: head `""`=5, recruiter=3, bio=1, appraisal=2 (four distinct); `a74b526` recruiter=4, bio=4 — identical trial-0 order and identical agent-slot sequence `[1,2,0,0,1,2]` |
| **S6a** `CandidateRejected` | **FIXED** | `run_tests.py:5276` `assertIsNot`, + judge-side `assertNotIsInstance` | (test modified) | `CandidateRejected = ValueError` → red (1) |
| **S6b** `_BULLETED_DRAFT` guard load-bearing | **FIXED** | `run_tests.py:4667-4676` (`_BULLETED_DRAFT`) (the line before the first bullet is now 70 chars) | (fixture constant modified) | `_LIST_ITEM_RE = (?!x)x` → red (1) |
| **S7** 26/min either order | **FIXED** | `self-appraisal-opening/fixture.yaml:123` | RED on ref | restore the lookahead → red (2). "cut the median pipeline run to 9 minutes, down from 26" → head True, ref False; forward order still True |
| **S8** first-person marker | **FIXED** | `self-appraisal-opening/fixture.yaml:101-103` | both tests RED on ref | verb-adjacency restored → red (1); bare `\bI\b` restored → red (1). "Adam has led … I/O …" and "Adam again led … I am told" → head **False** (caught), ref True; a genuine first-person draft still True |
| **N1** truncated detail | **FIXED** | `run_eval.py:754-765` | RED on ref | pad the front of `detail` → red (3). `report.md` cell at 200 chars: head carries `--no-judge`, `#97` and the issue URL; `a74b526` carries none of the three |
| **N2** fixture-list test | **FIXED** | `run_tests.py:4585-4607` (plants a fourth fixture) | (test rewritten) | hardcode `_fixture_names` → red (2) |
| **N3** ragged `# The` comment | **FIXED** | `self-appraisal-opening/fixture.yaml:8-12` rewrapped | n/a (cosmetic) | none — correctly, a rewrap has nothing to pin |
| **N4** `mode: Absolute` | **FIXED** | `run_eval.py:749-751` and `judge.py:220-221`, `judge.py:832-833` (all three sites casefold) | RED on ref | drop the run_eval casefold → red (1) |
| **N5** README rewritten for provenance | **FIXED** | `evals/adam-writing-style/README.md:87-137` | n/a (doc) | none. States the mechanism, the opt-in and both intended limits; no "known failure mode: the agent formats its own reply" note is needed (none of the 120 cells fails that way) |
| **N6** invisibles + `\s+` | **FIXED** | `objective.py:609`, `:850`; avoid patterns use `\s+` | RED on ref (18 subtest failures) | narrow `_INVISIBLE_RE` → red (3); remove the fold → red (9); hard-code one space in a pattern → red (1). `lever­age`, `deep​ dive`, `deep  dive`, `rob⠀ust` → all **caught** on head, all **missed** on ref |
| **N7** two-word facts across a wrap | **FIXED** | `recruiter-reply/fixture.yaml:157`, `proposal-bio/fixture.yaml:140` | RED on ref (3 failures) | `[^.]{0,80}` → `[^.\n]*` → red (1) each. `Section\n508` and `March\n2027` → head True, ref False |
| **N8** `+=` and bulleted twin | **FIXED (perf half unpinned)** | `judge.py:461-482` | (tests modified) | refuse to join a continuation → red (2). Restoring the quadratic `+=` leaves the suite **green** — deliberate and correct: a timing assertion would be non-deterministic. Worth one sentence in the report, not a change |
| **N9** scan gaps | **FIXED** | `run_tests.py:3375` (`www.`), `:3394-3404` (`ghp_`, `xoxb-`, `AKIA`, `sk-ant-`, `access[_-]?key`, `CERTIFICATE`), `:3414-3419` (`+44 (0)20 …`, `+44207946…`) | the two scan tests are green on ref **only because the patterns live in `run_tests.py` itself**, which I copied over — so hollowness is untestable that way; the mutations below are the evidence | bare-token alternatives removed → red (5); `access[_-]?key` removed → red (2); `CERTIFICATE` removed → red (1); two phone shapes removed → red (3); bare `www.` removed from `_URL_RE` → red (1) |
| **N10** `bio-is-third-person` passing direction | **FIXED** | `proposal-bio/fixture.yaml:36-45` and `:99-110` | `test_commentary_can_supply_a_check_as_well_as_break_one` RED on ref | covered by the fixture-header assertions in that test |

Two of the 23 new tests are green on `a74b526` for benign reasons and are
**guards, not fix-provers**: `test_a_genuine_draft_beside_the_quoted_seed_still_passes`
(column A was already clean on `a74b526`) and
`test_no_other_fixture_asks_for_the_seed_pre_pass` (no fixture there
carried the key). Both have real teeth under mutation.

## 5. Rule 19 — the harness change is opt-in per check

Every other fixture under `evals/`, `--arm objective-only`, `origin/main`
(`a6c882a`) vs head, full stdout compared byte for byte:

| Fixture | main | head | stdout |
|---|---|---|---|
| `guidance-bridge-canary` | exit 2 | exit 2 | **identical** |
| `propagation` | exit 2 | exit 2 | **identical** |
| `rename-pdfs` | exit 1 | exit 1 | **identical** |
| `windows-elevation-from-wsl` | exit 1 | exit 1 | **identical** (7 checks) |
| `workflow-path-audit` | exit 1 | exit 1 | **identical** (8 checks) |

Plus the fenced-handoff transcript scored through both `run_checks` and
`transcript_matches` on `windows-elevation-from-wsl`: **True on
`origin/main`, True on head, False on `a74b526`** — B1 is closed and
verified against the tree the round-3 review said it regressed from.

## 6. Seeds, prompts, checks

- `git diff --stat a74b526 f01c1e6 -- evals/adam-writing-style/*/seed` is
  **empty** — the seeds are byte-identical, and no item required otherwise.
- The three `prompt:` strings, `judge_rubric:`, `model:` and the whole
  `judge:` block are **identical** to `a74b526` (`yaml.safe_load`
  comparison, all three fixtures).
- Nothing under any `seed/` names a rule, the skill, or the fiction marker:
  a case-insensitive scan for `adam-writing-style|fictional|avoid.list|core
  move|SKILL\.md|leverage|em dash|hedge|third person|first person|buzzword|
  register` over `evals/adam-writing-style/*/seed/` returns **zero hits**.
- **All ten checks are `transcript_matches`** (YAML-parsed); every pattern
  is lexical over prose. **No check decides code shape by regex.**
- The hand-rolled Markdown regexes now live only in the pre-pass, and they
  no longer *decide* anything: a markup misread can only fail to drop a
  block that provenance already proved is seed text, so it errs toward
  keeping the agent's writing. That is the right way round, and it answers
  round-3's AGENTS.md "parse an AST, never a regex" objection.

## 7. Merge hygiene

- `git diff --stat origin/main..f01c1e6 -- .github/` — **empty**.
- `git log --format='%ae' a74b526..f01c1e6` — one address,
  `4205216+Adam-S-Daniel@users.noreply.github.com`.
- AST symbol comparison across the merge (`ast.parse`, never a regex):
  `test/run_tests.py` 19 classes (branch) + 22 (main) → **23 in the merge,
  none lost, none invented, zero test methods lost** (408 methods).
  `objective.py` `CHECKS` keys: 9 (branch) ∪ 11 (main) → **11 in the merge,
  none lost**. Top-level functions: none lost from either side in
  `run_eval.py` or `judge.py`; `objective.py` loses exactly one,
  `strip_quoted`, which the design decision withdraws by name.
- The branch touched exactly 8 files; `DESIGN.md` and `README.md` moved on
  the **main** side only.

## 8. New findings

### BLOCKER

**1. The `_wrap_width` fix reintroduces a line-shape tell, in the mirror
direction: a model-shaped draft loses its two-line sign-off while both
hard-wrapped references keep theirs.** `harness/scorers/judge.py:485-509`.

`_wrap_width` pools every **non-final** line length across the draft and
takes the median. A model's reply is one long line per paragraph — the
shape `run_tests.py:3690-3694` and `_normalize_draft_text`'s own docstring say
it has — so its **only** multi-line block is the sign-off, and the sole
sample is that block's first line. The median is then 7 (`"Thanks,"`),
`len("Thanks,") + 1 + len("Adam") = 12 > 7` reads as a wrap, and the
sign-off is joined. The docstring at `:494-504` claims pooling prevents
exactly this ("Pooling the whole draft keeps the sign-off's lines far under
the column the prose was wrapped at") — true only for a draft that *has*
wrapped prose.

Measured through the production entry point (`judge.blind_order` →
`judge._build_pairwise_prompt`, recruiter-reply, trial 0, the harness's own
`UNWRAPPED_CANDIDATE`):

```
head      draft A [8, 91, 178, 197, 7, 11]   last line 'Adam Daniel'
          draft B [10, 150, 189, 194, 13, 11] last line 'Adam Daniel'
          draft C [8, 260, 110, 19]           last line 'Thanks, Adam Daniel'   <- the agent's
a74b526   draft A [10, 150, 189, 194, 13, 11] last line 'Adam Daniel'
          draft B [8, 91, 178, 197, 7, 11]    last line 'Adam Daniel'
          draft C [8, 260, 110, 7, 11]        last line 'Adam Daniel'
```

The agent's draft is the only one of three whose sign-off is one line, on
every trial, deterministically — the references never change. This is the
tell `_normalize_draft_text` exists to remove, it lands on a scored rubric
dimension (recruiter-reply's dimension (2) names "a plain sign-off"), and
the fixture's whole instrument is a blind pairwise ranking.

Nothing in the suite can see it. `_assert_one_line_shape`
(`run_tests.py:3729-3743`) only asserts that no non-final line **exceeds**
40 characters — joining two short lines passes it. The sign-off assertions
(`run_tests.py:3793-3798` on `_HYPERLINKED_DRAFT`, `:4701-4703` on
`_SIGNED_OFF_DRAFT` (`:4694-4699`)) both use **hard-wrapped** drafts, where the median is
~65 and the sign-off survives.

*Fix*: exclude a block from the width sample when it contributes no
evidence of wrapping — e.g. sample only from blocks of three or more lines,
or require the width to be at least, say, 40 (`DELIBERATE_LINE` already
encodes that judgment for the tests), or fall back to the longest line when
the pooled sample is smaller than the shortest plausible wrap column.
*Test*: assert `judge._normalize_draft_text(UNWRAPPED_CANDIDATE)
.endswith("Thanks,\nAdam Daniel")` — red on head, green on `a74b526` and
under any of the fixes above.

**Not a repeat.** It is new in this round, introduced by the S4 fix.

### SHOULD-FIX

**2. Deleting the whole-reply fallback — a load-bearing clause of the
design decision and the direct fix for round-3 adversarial B-1 — is killed
by no test.** `harness/scorers/objective.py:791`.

Putting the fallback back (`residue = "\n".join(…); return residue if
residue.strip() else text`) leaves the suite at **345 tests, OK, exit 0**,
while re-opening the defect:

| Transcript | head | head + fallback |
|---|---|---|
| whole seed as a `>` quote, recruiter-reply | fails greets, hedge, **cites** | fails hedge only |
| whole seed in a ``` fence, recruiter-reply | fails greets, hedge, **cites** | fails hedge only |
| whole seed quoted, proposal-bio | fails third-person, **cites** | fails third-person only |
| whole seed quoted, self-appraisal | fails first-person, **cites** | fails first-person only |

`cites-both-facts` is what the recruiter-reply header calls "the skill's
specificity move, which is the thing under test", and it comes back for a
reply containing zero words of the agent's own.

The gap is structural: every quoted-seed test appends
`_CONTENTLESS_FILLER` (`run_tests.py:4178-4180`), so the residue is never
empty and the deleted branch is never reached. `test_a_wholly_quoted_draft
_cannot_switch_the_avoid_list_off` (`:4032`) does not cover it either — its
drafts are buzzwords, which are not seed text and so are never stripped in
the first place; its docstring at `:4033-4036` still describes the deleted
fallback ("when stripping the quoted material leaves nothing at all the
whole reply is scored"), which is now false.

*Fix*: one test — score a transcript that is **only** the quoted seed and
assert `cites-both-facts` fails on all three fixtures — plus correct that
docstring.
**Partial repeat**: the defect it protects is round-3 adversarial B-1
(rated blocker). The fix is present and correct; what is missing is the
test, so I file it at should-fix.

**3. A line is dropped as "seed material" on a normalisation that has
deleted content from it, so text that is not in the seed disappears from
scoring — and one shape of that hands a check to the seed.**
`harness/scorers/objective.py:618-635` (`_normalise`), used both to build
the index and to decide `drop`, while `strip_seed_material` removes the
**original** line (`:791`).

`_normalise` substitutes `_HTML_TAG_RE = <[^<>]*>` → `" "` and strips a
leading list marker. Whatever sat inside those is invisible to the
provenance decision but present in the line that gets deleted.

(a) **Ban evasion, measured.** Recruiter-reply, all four checks:

```
Hi Dana,

Sorry for the slow reply. REQ-4417 is not for me; my engagement runs to March 2027.

Your name came up while I<leverage synergy robust> was looking for platform engineers with

Thanks,
Adam Daniel
```
→ **ALL PASS**, `no-avoid-list-words` included; `"leverage" in residue` is
False. The line normalises to a verbatim seed sentence once the angle
brackets are deleted, so the whole raw line — buzzwords and all — is
removed before the ban runs. The control (`We can leverage that.` on its
own line) correctly fails.

(b) **The greeting handed back to the recruiter, measured.** The same
regex turns `From: Dana Whitcombe <dana.whitcombe@example.com>` (49
characters) into `from: dana whitcombe` (20) — under the 24-char floor — so
her own `From:` header survives an unmarked paste. With the paste **above**
the reply it lands in the four-line opening window:

| paste shape (cold-email above a reply that greets nobody) | `greets-the-recruiter-by-name` |
|---|---|
| 4-space indented block | **True** |
| verbatim, no marker | **True** |
| unterminated ``` fence | **True** |
| lazy continuation | **True** |
| `>` blockquote | False (correct) |
| HTML `<pre>` | False (correct) |

Causal, measured: narrowing `_HTML_TAG_RE` to a tag-shaped pattern flips
that cell to False. This is the exact claim `recruiter-reply/fixture.yaml`
makes at `:88-92` — "her signature is seed material, so it is not part of
the text this pattern sees" — and it is false for four of the shapes the
brief lists. It is also the mechanism behind the four column-A misses in
§3: those same leftovers push a genuine draft's hedge out of its window.

*Fix*: decide provenance on a normalisation that removes only **wrapper**
(quote markers, a leading list marker, whitespace, case) and never
arbitrary inline content; if the HTML-tag strip is wanted for the block
rule, apply it there and require, for a line-level drop, that the
tag-stripped remainder be empty or itself seed text. Narrowing
`_HTML_TAG_RE` fixes (b) but not (a) on its own.
**Partial repeat**: same class as round-3 code B-2 / adv S-6 ("quoted
material satisfies a check"), which were blockers. The innocent shape is
now down to one check out of four, so I file it at should-fix; the crafted
shape (a) is a fresh full ALL-PASS and is what earns the severity.

**4. The ≥24-character substring rule deletes the agent's own lines when a
hard wrap makes one coincide with the seed's phrasing.**
`harness/scorers/objective.py:769-772`.

Measured on the fixtures' **own committed `in-voice` references**,
re-wrapped at 40 columns and scored:

| Fixture | lines deleted from the agent's own draft |
|---|---|
| `proposal-bio` | `pipeline behind eleven state agency`, `AWS Solutions Architect – Professional` |
| `self-appraisal-opening` | `over the secrets-remediation backlog in` |
| `recruiter-reply` | none |

And without any wrapping at all: a bio that follows SKILL.md core move 8
("Plain certifications listing at the end") loses the whole line —
`Certifications: AWS Solutions Architect – Professional, CISSP.` is a
verbatim ≥24-char run of the seed's own certifications bullet and is
removed from the residue.

No current check reads certifications or those clauses, so nothing fails
today; the mechanism is latent and directional against the arm that follows
the skill. The README's "What it does not do" (`:129-137`) documents only
the opposite direction (a fact restated in the agent's own sentence still
counts) and the short-line floor.
*Fix*: at minimum, state this in the README and in one fixture header;
better, require a line-level substring hit to align to a seed line boundary
rather than to any window of the joined text. **Not a repeat** — new.

### NITS

**N-a.** `_seed_index` reads only the first 1 MiB of each seed file
(`objective.py:656`). The cap exists for the binary sniff, but it also
silently truncates the index for a text seed larger than that. The three
#81 seeds are ~1 KB, so it is theoretical; a comment would settle it.

**N-b.** N8's performance half is not test-pinned (restoring the quadratic
`+=` leaves the suite green). That is correct — a timing assertion would be
non-deterministic, which AGENTS.md forbids — and it is worth saying out
loud rather than leaving as an apparent gap.

**N-c.** `_unquote` strips a leading `>` from every transcript line
unconditionally, including one where `>` is prose ("> 60 words is the
cap"). No current pattern is affected; it is a one-line docstring note.

## 9. What I could not check

- **Anything about a real judge.** No network and the real `claude` is off
  limits, so every judge measurement is structural (prompt text, shuffle,
  normalisation) against `test/fake-claude`. Whether a real model reads the
  sign-off tell in finding 1 is unmeasured; the tell itself is measured.
- **The eval end to end.** `run_eval` refuses a pairwise fixture before any
  arm runs (#97, https://github.com/Adam-S-Daniel/skills-evals/issues/97),
  so the objective column has still never been scored against a real
  transcript.
- **CI on `f01c1e6`.** Not queried — offline review, nothing posted.
- **Line numbers** are from `$SP/rev131d-code` as exported; the tree was
  never modified, so they are stable.

## 10. Tree integrity

`$SP/rev131d-code`, `find . -type f -not -path '*/__pycache__/*' -print0 |
sort -z | xargs -0 md5sum | md5sum`:

- **before:** `48e625390db5eb0b1897783075033430`
- **after:**  `48e625390db5eb0b1897783075033430`

No mutation was ever applied inside it (all 26 mutations ran in
`$SP/mut-work-tree`, a same-depth copy deleted after each run).
`/home/user/skills-evals`: `git status --short` empty, HEAD still
`527c7294cfdca393cbcf9ce47e3eede0835d36dc`. `/home/user/agentskills`
read-only. `$SP/rev131d-adv` never entered.
