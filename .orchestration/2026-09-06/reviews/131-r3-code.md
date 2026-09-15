NOT CLEAN — the global quote-stripper silently narrows an existing unrelated fixture (windows-elevation-from-wsl now fails a fenced command handoff), and "quoted material satisfies checks" is PARTIAL again: a contentless reply plus a quoted seed still passes every objective check on all three fixtures under 4-space indented code blocks, lazy-continuation blockquotes and HTML `<blockquote>`/`<details>`/`<pre>`.

# skills-evals PR #131 — round-3 code review

Head `a74b52625c1813cfce416ee6a602d6c6cf8c2210`. Scope: what fix round 2
(`c3da3d3..a74b526`, ten commits) changed, and whether the four round-2
PARTIAL items are closed. Reviewed against
`/home/user/agentskills/plugins/adam/skills/adam-writing-style/SKILL.md`
(read in full) and the brief at `$SP/briefs/81-fix2.md`.

Everything below was measured in a throwaway extraction of `a74b526`
(`$SP/rev131c-code`). `/home/user/skills-evals` was read-only throughout
(`git show`/`log`/`diff`/`archive` only). Every mutation was applied in the
extraction and restored from `git show a74b526:<path>`; the tree was
diffed against a fresh extraction afterwards and is byte-identical except
for `__pycache__`. No network, no real `claude` binary, no background
processes, nothing posted to GitHub.

## 1. Verifiers

| Verifier | Result |
|---|---|
| `python3 test/run_tests.py` | **exit 0, 262 tests, 0 skipped** (226 on c3da3d3, 157 on main af06d0f) |
| `python3 test/test_propagation.py` | **exit 0, 164 tests, 1 skipped** |
| `run_eval.py evals/adam-writing-style/proposal-bio --arm objective-only` | **exit 1** (3 checks, all "no transcript") |
| `run_eval.py .../recruiter-reply --arm objective-only` | **exit 1** (4 checks) |
| `run_eval.py .../self-appraisal-opening --arm objective-only` | **exit 1** (3 checks) |

The avoid-list drift test is **not** skipped here: `resolve_registries`
finds `/home/user/agentskills` as the sibling checkout, so
`test_avoid_list_covers_every_term_the_skill_lists` ran against the real
SKILL.md rather than skipping (the 1 skip is in `test_propagation.py`, not
this suite).

## 2. The four round-2 PARTIAL items

**(a) Quoted material satisfying checks — PARTIAL (again).**
FIXED for every shape the brief named and for several it did not:
`>` at 0–3 spaces of indent, ` ``` ` and `~~~` fences with or without an
info string, nested `> >`, a fence inside a blockquote, and a blockquote
inside a list item are all stripped, and a quoted seed in any of those
shapes no longer supplies `cites-both-facts` on any fixture.
PARTIAL because the same round-1 exploit — quoted seed material plus a
contentless filler paragraph — **still passes every objective check on all
three fixtures** under quoting shapes the scanner cannot see:

| Shape | proposal-bio | recruiter-reply | self-appraisal-opening |
|---|---|---|---|
| 4-space indented code block | ALL PASS (both positions) | ALL PASS (quote last) | ALL PASS (both) |
| blockquote w/ lazy continuation | ALL PASS (both) | ALL PASS (quote last) | fails `cites-both-facts` |
| HTML `<blockquote>` / `<details>` / `<pre>` | ALL PASS (both) | ALL PASS (quote last) | ALL PASS (both) |
| verbatim paste, no quote marker | ALL PASS | ALL PASS (quote last) | ALL PASS |
| unterminated ` ``` ` fence | ALL PASS (quote first) | fails | ALL PASS (quote first) |

Reproduction: `harness/scorers/objective.py:419-420` — the pre-pass knows
exactly two block types. The verbatim case is out of reach of any lexical
pre-pass and bounds what this design can deliver; the other three carry an
explicit "this is quoted" marker and are the ones that should close.

**(b) The blockquote switching off `no-avoid-list-words` — FIXED for the
named case, with a residual.** A wholly blockquoted / fenced / indented
buzzword reply now fails `no-avoid-list-words` on all three fixtures
(`objective.py:455`, the whole-reply fallback), and
`test_a_wholly_quoted_draft_cannot_switch_the_avoid_list_off` goes red when
the fallback is reverted to `return residue` (9 failures). Residual,
measured: add a one-line unquoted preamble and the ban is vacuous again —
`"Here is the draft:" + <blockquoted buzzword reply>` passes
`no-avoid-list-words`. In that shape every `must_match` check also fails, so
the fixture verdict is still FAIL and no bad draft is scored as good; but a
ban reporting PASS over a deliverable full of buzzwords is the same defect
in a smaller costume. See should-fix S-1 for the two-line fix that closes
this and the wholly-quoted `must_match` hole together.

**(c) The run_eval.py mismatch documented but not enforced — FIXED.**
`harness/run_eval.py:712-726`. A `judge.mode: pairwise` fixture with the
judge on exits **2** with `judge_mode_unsupported`, before any arm runs, and
writes `report.md` + one `summary.json` per arm carrying that named error.
Measured, `--arm both`: exit 2, three artifacts, no `raw.json`, no `7.5`
anywhere. Removing the guard turns
`test_a_pairwise_fixture_with_the_judge_on_exits_2` red.

**(d) The fiction-marker test's hardcoded denominator — FIXED.**
`test/run_tests.py:2591-2599` derives `FIXTURES` from
`STYLE_DIR.glob("*/fixture.yaml")`, `_fixture_names()` does the same for any
root, and the marker/credential scans walk the whole style directory
including its own README. Planting a fourth fixture directory with its
markers stripped is caught: reverting `_fixture_names` to the 3-tuple turns
`test_the_marker_scan_reaches_a_fixture_this_file_does_not_name` red.

## 3. Per-item table (brief `81-fix2.md`)

Every mutation below was applied to the extracted tree, the named test(s)
run, then the file restored from `git show a74b526:<path>` and the tests
re-run green. "RED" means the mutation made them fail.

| # | Item | Status | Where | Pinning test | Mutation → result |
|---|---|---|---|---|---|
| B1 | Ban not switchable off by a wholly quoted reply | FIXED (residual, S-1) | `objective.py:455` | `test_a_wholly_quoted_draft_cannot_switch_the_avoid_list_off` | `return residue` → RED (9) |
| 1 | Structural quote stripper, 47 anchors gone | **PARTIAL** | `objective.py:419-455,506` | `test_quoted_material_never_supplies_what_a_check_looks_for` | bypass stripper → RED (16); `^ {0,3}>`→`^>` → RED (5); fence RE disabled → RED (6) |
| 2 | Untested anchors + nonce-forgery guard | FIXED | `judge.py:525` | `test_pairwise_rejects_a_draft_carrying_the_nonce`, 10×3 `QUOTED_CASES` | `if nonce in text:`→`if False:` → RED (1) |
| 3 | `judge_mode_unsupported`, exit 2, artifacts | FIXED (S-2, S-3) | `run_eval.py:712-726` | `test_a_pairwise_fixture_with_the_judge_on_exits_2` | guard → `if False:` → RED (1) |
| 4 | Fixture list read off disk | FIXED | `run_tests.py:2591,2600` | `test_the_marker_scan_reaches_a_fixture_this_file_does_not_name` | `_fixture_names` → 3-tuple → RED (1) |
| 5 | Structure-preserving unwrap | FIXED (S-4) | `judge.py:430-453,456-506` | `..._leaves_a_bulleted_draft_bulleted`, `..._sign_off_on_its_own_line`, `..._normalises_like_its_unwrapped_twin` | join-everything → RED (2); never-join → RED (4) |
| 6 | Six references contract | FIXED | all six `references/*.md` | `test_every_reference_is_written_in_a_voice_that_contracts` | de-contract one → RED (1) |
| 7a | Hedge anchor accepts `,;:` | FIXED | `recruiter-reply/fixture.yaml:134` | `test_a_hedge_joined_by_ordinary_punctuation_still_counts` | drop `,;:` → RED (4) |
| 7b | Marker out of `seed/`, stripped from candidate | FIXED | fixture headers + `judge.py:483` | `..._prose_outside_the_seed_is_marked...`, `..._agent_workspace_built_from_a_seed...`, `..._candidate_that_echoes_the_marker...` | marker into a seed → RED (2); stop stripping on candidate → RED (1) |
| 7c | `their`/`they` out of the subject list | FIXED | `proposal-bio/fixture.yaml:100` | `test_a_their_belonging_to_someone_else_is_not_a_third_person_subject` | put `their` back → RED (1) |
| 7d | #97 named and linked | FIXED | `judge.py:754`, `README.md:151`, `evals/.../README.md` | `test_the_run_eval_gap_names_the_issue_that_owns_it` | drop the link → RED (1) |
| 7 | `run_agent` argv/OSError gap handed to #97 | FIXED | `evals/adam-writing-style/README.md:46-52` | `test_the_readme_hands_run_agents_argv_gap_to_the_same_issue` | (doc-only; test asserts `run_agent`+`OSError`+`argv`) |
| 8 | Shuffle folded per fixture | FIXED (N-2) | `judge.py:304-329` | `test_pairwise_trial_zero_order_is_pinned_per_fixture`, `..._moves_with_the_fixture_directory` | drop `scope` → RED (5) |
| 9 | `_SECRET_RE` widened | FIXED | `run_tests.py:3234-3239` | `test_the_credential_scan_catches_the_shapes_it_missed` | revert to `\b` form → RED (5) |
| 10 | Invisible-character drafts | FIXED (N-7) | `judge.py:427,365` | `test_a_draft_of_invisible_characters_is_not_a_draft`, `..._do_not_hide_a_duplicate_draft` | drop `_INVISIBLE_RE` → RED (6); emptiness on `.strip()` → RED (5) |
| 11 | Lone surrogate → RuntimeError | FIXED | `judge.py:150-157` | `test_a_lone_surrogate_in_the_prompt_is_a_runtimeerror` | catch a different exception → RED (1) |
| 12 | N a whole number of cycles | FIXED | 3 fixture headers + `evals/.../README.md:8-13` | `test_the_recommended_trial_count_is_a_whole_number_of_cycles` | "N >= 5" → RED (1) |
| 13 | `_PHONE_RE` widened | FIXED | `run_tests.py:3245-3248` | `test_the_phone_scan_catches_the_shapes_it_missed` | revert to separated-only → RED (2) |
| 14 | One opening window, honestly described | FIXED | `recruiter-reply/fixture.yaml:98-103,108,134` | `test_both_opening_checks_use_the_same_window` | `{0,3}`→`{0,5}` on one → RED (2) |
| 15 | Range tested before `isfinite` | FIXED | `judge.py:675` | `test_pairwise_rejects_a_score_too_large_to_be_a_float` | restore `math.isfinite` first → RED (1, `OverflowError`) |
| 16 | Twinned label raises | FIXED | `judge.py:640-652` | `test_pairwise_rejects_two_dimension_entries_for_one_draft` | duplicate check → `if False:` → RED (1) |
| 17 | `Sections 504 and 508` either order | FIXED | `proposal-bio/fixture.yaml:122` | `test_the_named_standard_is_cited_in_either_order` | restore adjacency → RED (1) |
| 18 | A real argv invariant | FIXED | `run_tests.py:3496-3505` | `test_judge_prompt_travels_on_stdin_not_argv` | prompt back into argv → RED (1) |
| 19 | Candidate-triggered errors named | FIXED | `judge.py:34,521,526` + `score_pairwise` docstring | `test_a_draft_that_cannot_be_rendered_is_a_named_rejection` | rename the class → RED (1) |

Item 19 note: `CandidateRejected` is a `ValueError` subclass and
`run_eval.py:604` still records it as an undifferentiated judge error — but
`run_eval` never reaches `score_pairwise` (item 3's guard refuses first), so
there is no behavioural gap today. The brief allowed "distinguish **or**
document"; both were done.

Item 4 note: `test_the_fixture_list_is_read_off_the_disk` asserts
`FIXTURES == _fixture_names()`, which cannot fail while `FIXTURES` is
derived — hardcoding it back to today's three names leaves that test green
(N-3). The teeth are in the planted-fourth-fixture test, which is red under
mutation, so the item itself is closed.

## 4. The stripper, in full

`objective.strip_quoted` (`harness/scorers/objective.py:423-455`) is a
**line-based scanner**, not a parser and not token-based. One pass over
`splitlines()` with a single `fence` state variable: a line matching
`^ {0,3}(` ``` `|~~~)` opens a fence and is dropped, every line thereafter
is dropped until a line whose stripped content is all the same fence
character and at least as long; outside a fence, a line matching
`^ {0,3}>` is dropped and everything else is kept. If the kept text is
empty or whitespace, the **whole original reply** is returned.

That means it knows exactly two of CommonMark's block types, and nothing
about HTML blocks, indented code blocks, or lazy continuation. This is the
`AGENTS.md` "parse a real parser for the language in play" rule playing out
exactly as predicted: the three block types the hand-rolled scanner cannot
see are the three that still let quoted material satisfy a check.

Measured, per shape. Column A: the in-voice reference **plus** a quoted copy
of the whole seed appended — a genuine draft that also quotes — must still
pass every check. Column B: a contentless filler that satisfies every check
**except** the facts, plus the quoted seed — must still fail.

| Quoting shape | Stripped? | A: genuine draft + quote | B: contentless + quote |
|---|---|---|---|
| `>` blockquote | yes | ALL PASS (3/3 fixtures) | fails `cites-both-facts` (3/3) |
| `>` blockquote, 1–3 space indent | yes | ALL PASS | fails (3/3) |
| ` ``` ` fence | yes | ALL PASS | fails (3/3) |
| ` ```markdown ` (info string) | yes | ALL PASS | fails (3/3) |
| `~~~` fence, with/without info | yes | ALL PASS | fails (3/3) |
| unterminated ` ``` ` fence | to EOF → residue empty → **fallback scores the whole reply** | ALL PASS | **ALL PASS** on proposal-bio + self-appraisal (quote first) |
| indented code block (4 spaces) | **no** | ALL PASS | **ALL PASS** on all three |
| blockquote, lazy continuation | only the marked line | ALL PASS | **ALL PASS** on proposal-bio + recruiter-reply |
| nested `> >` | yes | ALL PASS | fails (3/3) |
| fence inside a blockquote | yes | ALL PASS | fails (3/3) |
| blockquote inside a list item | yes | ALL PASS | fails (3/3) |
| HTML `<blockquote>` | **no** | ALL PASS | **ALL PASS** on all three |
| HTML `<details>` | **no** | ALL PASS | **ALL PASS** on all three |
| HTML `<pre>` | **no** | ALL PASS | **ALL PASS** on all three |
| seed reproduced verbatim, no marker | **not strippable** | ALL PASS | **ALL PASS** on all three |

Column A is clean everywhere: the pre-pass never breaks a genuine draft
that also quotes. Column B is where item 1 is still open.

**The whole-reply fallback.** With the residue empty or whitespace-only the
entire reply is scored. Both directions measured:

- The ban holds — this is the fallback's purpose and it works (B1 above).
- `must_match` is satisfied by the quote. A reply that is **only** a `>`
  quote of the seed passes `cites-both-facts` on all three fixtures and
  `greets-the-recruiter-by-name` on recruiter-reply. It does not reach
  ALL PASS on any fixture, because the register check
  (`opens-with-a-hedge` / `bio-is-third-person` /
  `appraisal-is-first-person`) still fails on the seed's own text — so
  no fixture can be passed by pure quotation, but the ambition "quoted
  material never supplies what a check looks for" is not met in this case
  either, and the docstring at `objective.py:433-438` explains the ban half
  of the fallback without mentioning this half.

## 5. The exit-2 guard, measured

`run_eval.py:712-726` plus `_write_pre_run_error` at `:616-639`. Behaviour
against `recruiter-reply` with a rewritten `judge:` block, `--arm
without_skill`, `CLAUDE_BIN=test/fake-claude`:

| `judge:` block | exit | named error | artifacts | judge score in them |
|---|---|---|---|---|
| `mode: pairwise` | 2 | yes | report.md + summary.json | none |
| `mode: Pairwise` / `PAIRWISE` / `' pairwise '` | 2 | yes | same | none |
| `mode: Absolute` (capital A) | 2 | yes | same | none (over-refusal, N-5) |
| `mode: absolute` / `mode: null` / no `judge:` key | 0 | — | + `raw.json` | 7.5, as before |
| nested `judge.config.mode: pairwise` | 0 | — | + `raw.json` | 7.5 |
| `judge:` is a **list** | **1** | **no — uncaught `AttributeError`** | **none** | — |
| `judge:` is a **string** | **1** | **no — uncaught `AttributeError`** | **none** | — |

Spelling cannot bypass the guard: it is a whitelist (`not in (None, "",
"absolute")`), so every misspelling of `pairwise` — and every misspelling of
`absolute` — is refused rather than silently mis-scored. `judge.config.mode`
is not a bypass either; that fixture declares no `judge.mode` at all, so
"absolute" is the correct reading of it. The two real problems are the
non-dict crash (S-3, a **regression**: on `c3da3d3` both spellings ran to
exit 0 with artifacts, the malformed block being recorded as a judge error
by the `except` at `run_eval.py:604`) and the traversal write (S-2).

`run_eval.py`'s 56 added lines are **only** the guard and its wiring: 52
added source lines, zero deletions, split between `_write_pre_run_error`
(`:616-639`, 24 lines including its docstring) and the guard block
(`:697-726`, 28 lines including its comment). Nothing else in the file
changed.

### Other-fixture comparison (base `af06d0f` vs head `a74b526`)

Every other fixture under `evals/`, `--arm objective-only`, per-check
outcome **and** detail string compared:

| Fixture | base | head | per-check outcomes |
|---|---|---|---|
| `guidance-bridge-canary` | exit 2 | exit 2 | identical stdout ("missing required field(s): skill") |
| `propagation` | exit 2 | exit 2 | identical stdout |
| `windows-elevation-from-wsl` | exit 1 | exit 1 | 7 checks, identical |
| `workflow-path-audit` | exit 1 | exit 1 | 8 checks, identical |

Also run through the agent arm with `fake-claude` (`--arm without_skill`,
mode `agent_and_judge`): both runnable fixtures exit 0 on base and head with
identical objective outcomes and identical judge overalls
(`7.624999999999999` and `7.5555555555555545`). The guard does not fire for
them — neither declares a `judge.mode`.

**But that comparison is blind to the one real cross-fixture change**, because
the canned transcript contains no quoted material. See blocker B-1.

## 6. The judge

**Absolute mode vs main (`af06d0f`).** `_build_prompt` output is
byte-identical (sha256 `c04dd2a7e18f…`), and `score()`'s parsed result is
identical across all six combinations of `{judge, judge_fenced,
judge_no_overall}` × `{no weights, weights}`, including the weighted
recomputation. Two deliberate differences, both from round 1 rather than
round 2 and both tested: the prompt now travels on **stdin** rather than in
argv (`test_judge_prompt_travels_on_stdin_not_argv`; that test's assertion
is now a real invariant, item 18), and a missing CLI is a `RuntimeError`
rather than a bare `FileNotFoundError`. Round 2 adds only the
`UnicodeEncodeError` translation, which cannot fire on a surrogate-free
prompt. Absolute mode is unchanged where it matters.

**Blind, after the structure-preserving unwrap.** Measured by normalising
each committed reference and a model-shaped (one-line-per-paragraph) draft
and comparing line-length distributions:

| Fixture | in-voice ref | generic ref | model-shaped draft |
|---|---|---|---|
| proposal-bio | `[393]` | `[319]` | `[348]` |
| self-appraisal-opening | `[540]` | `[456]` | `[352]` |
| recruiter-reply | `[8, 91, 178, 197, 7, 11]` | `[10, 150, 189, 194, 13, 11]` | `[8, 260, 110, 7, 11]` |

Every paragraph collapses to exactly one line in every draft; the
recruiter-reply differences are paragraph counts (content), not wrap
artifacts. No line-shape tell survives — **for these six references**. It is
fragile in one measurable way (S-4).

**Nonce forgery** — tested (`test_pairwise_rejects_a_draft_carrying_the_nonce`);
`if nonce in text:` → `if False:` turns it red. The closing-fence half is
tested too, and both now raise the named `CandidateRejected`.

**Per-fixture shuffle** — `_cycle_offset(identities, scope)`; dropping
`scope` turns five tests red. Two of the three fixtures still walk the cycle
in lockstep (N-2).

**Whole-cycle recommendation** — all three fixture headers and the fixtures'
README say "N >= 6 … and a multiple of 6" and say why; the test computes
`math.factorial(3)` rather than hardcoding 6.

**Surrogate / huge score / twinned labels / blame**, all measured directly
against `fake-claude`: `10**400` → `ValueError` "off the 0-10 scale" (not
`OverflowError`); NaN and 11 → the same `ValueError`; `{"A": …, "a": …}` →
`ValueError` "scored draft 'A' twice"; a lone surrogate in the candidate →
`RuntimeError` "could not encode its prompt"; a `</draft>` in the candidate
→ `CandidateRejected` (and `isinstance(…, ValueError)` is still True, so no
existing caller changes behaviour); sloppy lower-case labels still parse.

## 7. References, read as prose against SKILL.md

All six carry the `<!-- fictional -->` marker, all six are stripped before
the judge sees them, and all six now contract.

| Reference | words | contractions | em dashes | passes its fixture's checks |
|---|---|---|---|---|
| proposal-bio / in-voice | 60 | `hadn't` | 1 | 3/3 |
| proposal-bio / generic | 44 | `he's` | 0 | fails avoid-list + facts |
| recruiter-reply / in-voice | 93 | `I'm, isn't, wouldn't, that's, I'd, I'm` | 3 | 4/4 |
| recruiter-reply / generic | 99 | `I've, isn't, I'd, I'm` | 1 | fails avoid-list, hedge, facts |
| self-appraisal / in-voice | 93 | `isn't` | 1 | 3/3 |
| self-appraisal / generic | 60 | `I've` | 0 | fails avoid-list + facts |

Against the skill: the in-voice recruiter reply greets by first name (move
1), opens on "Sorry for the slow reply" (move 2), pastes REQ-4417 and March
2027 verbatim (move 3), uses em dashes at real joints and not in every
sentence (move 4, and not dash-soup), and signs off `Thanks,` / full name
(move 6) — while the generic one opens "Dear Dana" and closes "Best
regards," both of which move 6 explicitly rejects, and reaches for "circle
back". The in-voice bio is third person with employer-and-dates, "Section
508" spelled the way the skill's spelling list demands, and certifications
listed plainly at the end (move 8); the generic one is résumé-headline
language ("seasoned", "proven track record", "passionate") plus "deep
expertise in" and "robust" — the anti-patterns section and the avoid list.
The in-voice self-appraisal is first person, narrative, credits a coworker
and names next quarter (move 9); the generic one is "leveraged", "robust",
"strategic initiatives", "cross-functionally", "positioning the team".

No surface tell separates the two sides: contraction counts are 1/6/1
against 1/4/1, lengths do not order consistently (recruiter in-voice is
*shorter* than its generic twin), exclamation marks are zero everywhere, and
the marker is stripped from all six and from the candidate. The em-dash
counts do favour in-voice (1/3/1 vs 0/1/0), but em dashes are rubric
dimension (2) in every fixture, so a judge using them is applying the
rubric, not reading a tell. The 60-word in-voice bio against a 44-word
generic one is likewise the rubric's own "roughly sixty words is the
budget".

The generic ones are competent-but-generic, as intended: each is a plausible
piece of writing that a reader would accept and that fails the register on
its own terms.

## 8. Fixtures

- **Prompts unchanged** by round 2 (`yaml.safe_load` comparison
  `c3da3d3` → `a74b526`: identical on all three) and pinned in
  `run_tests.py:2606-2617`. None of them names a rule — they name a task
  ("declining but leaving the door open"), not a move, an avoid-list term
  or a register.
- **Every check is `transcript_matches`** — 10 of 10 across the three
  fixtures, pinned by `test_every_objective_check_is_a_transcript_check`.
- **No regex decides code shape.** The fixtures' patterns are lexical over
  prose, which is the Class C instrument. The one place structure is decided
  by a hand-rolled scanner is `strip_quoted` over Markdown blocks — see
  section 4 and blocker B-2.
- **Credential / phone / URL scan.** Widened patterns verified directly:
  `AWS_SECRET_ACCESS_KEY=`, `GITHUB_TOKEN=ghp_…`, `DJANGO_SECRET_KEY=`,
  `Authorization: Bearer`, `Authorization: Basic`, `api_key:`, `password =`
  and a PEM header all hit; "the secrets-remediation backlog", "secret
  sauce", "tokenize the string" and "a credential is needed" do not.
  `5558675309`, `+44 20 7946 0958` and all three separated forms hit;
  `2019–2024`, `REQ-4417`, `HRLS-2026-014`, `NIST 800-53`, `1998–2005` and
  the harness's own `20260905T034732Z` timestamps do not. Both mutations
  (reverting either regex) turn the corresponding test red, and the scan
  walking the README rather than the three fixture dirs is separately
  planted and tested.
- **Fiction marker**: zero occurrences anywhere under any `seed/`, present
  on all six references and on the fixtures' README, and recorded for each
  seed in the `fixture.yaml` header (the file beside `seed/` that is never
  copied). The workspace built the way `_run_arm` builds it carries none.
- **Domains**: `example.com` / `example.net` only; the host check rejects
  `notexample.com` and `example.com.attacker.test`, and the only exempted
  links are `github.com/Adam-S-Daniel/*`.

## 9. Findings

### Blockers

**B-1. The global quote-stripper silently narrows an existing, unrelated
fixture.** `harness/scorers/objective.py:506` applies `strip_quoted` to
*every* fixture's `transcript_matches`, and
`evals/windows-elevation-from-wsl/fixture.yaml:104-109`
(`handoff-names-elevation-and-the-line`) asks for the exact command line
back. An agent that hands over a command the way agents hand over commands —
in a fenced block — now fails it:

```
The change needs an elevated PowerShell prompt … Run this from an elevated prompt:

```powershell
pwsh -File C:\tools\register-tasks.ps1 -Time 03:30
```
```
→ head: `(False, "transcript lacks /(?i)register-tasks\.ps1/")`; base
(`af06d0f` and `c3da3d3`): `True`.
Nothing catches it: `WindowsElevationFixtureTests.HANDOFF`
(`test/run_tests.py:747-752`) puts the command in bare prose, so all 262
tests stay green while a shipped eval's measurement moves in the
false-negative direction. `objective.py:499-502` documents the consequence
("a fixture that wants an exact command line back must ask for it in prose
too") without acting on it, and no fixture was updated.
*Fix*: make the pre-pass opt-in per check — a `strip_quotes: true` key on
the check (or on the fixture), set on the ten #81 checks and left off
elsewhere — plus a regression test that fences the handoff command and
asserts `handoff-names-elevation-and-the-line` still passes. Two lines in
`run_checks` and one in each #81 check.

**B-2. Round-2 PARTIAL item (a) is PARTIAL again: quoted material still
satisfies checks.** `harness/scorers/objective.py:419-455`. The measurement
is in section 4: quoted seed + a contentless filler ALL-PASSES every
objective check on all three fixtures under 4-space indented code blocks,
under HTML `<blockquote>`/`<details>`/`<pre>`, and (on two fixtures) under
lazy-continuation blockquotes, plus on two fixtures via an unterminated
fence reaching the whole-reply fallback. Reproduce with the harness in this
review or directly:
`objective.transcript_matches('.', [], must_match=[r'\bREQ-4417\b'],
transcript="    REQ-4417 is the requisition.\n\nHere is the text you asked
for.")` → `(True, …)`.
*Fix*: extend the scanner to the three marker-carrying shapes — indented
code blocks (four spaces or a tab, after a blank line and not inside a list
item), HTML blocks (`<blockquote>`, `<pre>`, `<details>` … their closers),
and lazy continuation (a `>` block continues across unmarked non-blank lines
until a blank one) — or hand the job to a real CommonMark parser if a
dependency is acceptable. Then say plainly in the docstring and the fixtures'
README that a verbatim paste with **no** quote marker is indistinguishable
from the agent's own words and is the judge's problem, rather than implying
the pre-pass covers "what a model actually writes".

### Should-fix

**S-1. Bans and requirements should not be scored against the same text.**
`harness/scorers/objective.py:506` runs both `must_match` and
`must_not_match` over the residue. Two measured consequences, opposite in
direction: `"Here is the draft:" + <blockquoted buzzword reply>` passes
`no-avoid-list-words` (the ban made vacuous by quoting the thing being
scored — B1's residual), and the same shape with a *good* reply fails all
three `must_match` checks on recruiter-reply (a legitimate deliverable
presented as a blockquote or a fence, which is exactly what SKILL.md's
calibration examples look like, is now scored as if the deliverable were
absent — and on `c3da3d3` a fenced deliverable passed). Both close with one
change: score `must_not_match` against the **whole transcript** always and
`must_match` against the residue (falling back to the whole reply when the
residue is empty, as today). Verified safe for these fixtures: no
avoid-list term appears in any `seed/`, so scoring the ban over quoted
seed material cannot produce a false failure here.

**S-2. The new pre-run error writer escapes `--results-dir`.**
`harness/run_eval.py:616-639` builds `results_dir / fixture["skill"] / …`
and runs at `:724`, *before* `_validate_skill_name` at `:742`. Measured: a
fixture with `skill: ../../ESCAPED` and `judge.mode: pairwise` writes
`results/ESCAPED/<ts>/report.md` two directories above the `--results-dir`
it was given; the same fixture with `mode: absolute` correctly refuses
without writing, and `c3da3d3` wrote nothing. The comment at `:670-682`
warns about exactly this hazard for the arm loop.
*Fix*: move the `_validate_skill_name` call above the judge-mode guard (it
is already unconditional for non-objective-only arms), or call it inside
`_write_pre_run_error` before building the path.

**S-3. A non-dict `judge:` block is now an uncaught `AttributeError`.**
`harness/run_eval.py:712` — `(fixture.get("judge") or {}).get("mode", …)`
raises on a list or a string. Measured: exit 1, traceback, **no artifacts**;
on `c3da3d3` the same fixtures ran to exit 0 with the malformed block
recorded as a judge error by the `except` at `:604`. That is the failure
mode this commit's own docstring says it exists to prevent ("a pre-run
refusal that only printed to stdout left `results/` with nothing in it").
*Fix*: `judge_cfg = fixture.get("judge") or {}`; if it is not a `dict`,
take the same `_write_pre_run_error` path with a named
`invalid_judge_block` error. One test per shape.

**S-4. The unwrap's wrap column is the draft's own longest line, so one long
line disables it.** `harness/scorers/judge.py:491`. Adding a single 153-char
URL to `recruiter-reply/references/in-voice.md` changes its normalised
shape from `[8, 91, 178, 197, 7, 11]` (paragraphs joined) to
`[8, 70, 20, 71, 68, 37, 72, 72, 51, 7, 11, 153]` — every hard-wrapped line
break survives, and the line-shape tell that `_normalize_draft_text` exists
to remove comes straight back beside two drafts that do not have it. This is
not hypothetical for this skill: SKILL.md core move 3 tells the writer to
"Hyperlink the page you're talking about", and its own calibration examples
carry URLs. `test_pairwise_prompt_gives_every_draft_the_same_line_shape`
cannot see it — it only ever runs the committed references and one fixed
candidate.
*Fix*: compute `width` **per block** and ignore each block's last line (a
URL on its own line is then its own block and stops inflating the column),
or use a robust statistic over non-final lines. Add a case with a long line
to the shape test.

### Nits

**N-1.** `run_eval.py:508` truncates the error detail to 200 characters, so
the artifact's `report.md` for a refused pairwise run carries
`judge_mode_unsupported: … before #81, so scoring this fixture here wou` —
neither `#97`, its URL, nor `--no-judge` survives. `summary.json` has the
full detail and stdout has it too, and the test only asserts `#97` in
stdout. Front-load the actionable half of `detail` (re-run with
`--no-judge`; the wiring is #97 <url>) so the truncated table still points
somewhere.

**N-2.** Item 8 asked for "three different orders"; two of the three
fixtures still produce the identical trial-0 order and walk the cycle in
step (`proposal-bio` and `recruiter-reply`: `[in-voice, agent, generic]` at
trial 0 and identical at trials 1 and 2). The test asserts only "more than
one distinct order", and `run_tests.py:4293-4300` explains why — three draws
from six permutations collide 56% of the time and a hash tuned until they
did not would be fitted to today's directory names. I agree with that
reasoning, and it is fully neutralised by item 12: with N a multiple of 6
every draft sits in every slot equally often regardless of the offset. Worth
the orchestrator knowing the letter of the nit was not met.

**N-3.** `test_the_fixture_list_is_read_off_the_disk` cannot fail today:
hardcoding `FIXTURES` back to the three names on disk leaves it green
(measured). It only bites once a fourth fixture exists. The planted-fourth
test carries the real invariant, so this is cosmetic.

**N-4.** `evals/adam-writing-style/self-appraisal-opening/fixture.yaml:8-9`
was left with `# The` alone on a line by round 2's insertion — the same
ragged rewrap that commit `a74b526` fixed in `recruiter-reply` and missed
here.

**N-5.** `judge.mode: Absolute` (capital A) is refused with
`judge_mode_unsupported: fixture asks for judge mode 'Absolute', which
run_eval.py cannot drive yet`. Failing closed is right; the message is
misleading — it can drive that mode, it just does not recognise the
spelling. Say so, or casefold before comparing (`judge.score()` is
case-sensitive in the same way, so casefolding would need to happen in both).

**N-6.** `evals/adam-writing-style/README.md:88-96` says the anchors missed
"a fenced code block and a blockquote indented one to three spaces — legal
Markdown, and what a model actually writes", implying the pre-pass now
covers what a model writes. Three shapes a model also writes are still
uncovered (B-2). Either fix B-2 or say what remains.

**N-7.** `judge.py:427`'s `_INVISIBLE_RE` covers the shapes the brief named
(BOM, ZWSP/bidi range, U+2060, NUL) but not non-whitespace invisibles: a
draft of only U+2800 BRAILLE PATTERN BLANK or U+3164 HANGUL FILLER is still
accepted and ranked. Marginal.

## 10. What I could not check, and why

- **Whether the three prompts are the issue's sentences.** No network, so I
  could only confirm they are unchanged by round 2 and match the constants
  pinned in `run_tests.py:2606-2617`; I could not open
  `Adam-S-Daniel/skills-evals#81` to compare.
- **CI on `a74b526`.** Reported green by the brief; I did not query GitHub
  (no posting, and the review is offline).
- **Any real `claude` run.** Everything judge-side was measured through
  `test/fake-claude`, so the pairwise prompt's effect on a real judge —
  whether the blinding actually holds against a model rather than against a
  line-length metric — is unmeasured here and stays a live-run question.
- **The eval's real behaviour under either arm.** These fixtures cannot be
  scored end to end until #97 wires `score_fixture`; the guard is the
  correct interim, but it also means nobody has seen the objective column
  against a real transcript.
- **Line numbers** are from the `a74b526` tree as extracted; they are stable
  because nothing in the working tree was left modified.
