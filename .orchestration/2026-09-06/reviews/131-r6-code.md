NOT CLEAN — one blocker: a paste of the seed with one contentless connective inserted every fifth word — zero substantive words of the agent's — ALL-PASSES all three fixtures including `cites-both-facts`, so the round-2 (a) defect class is back on a new input one mechanical parameter away from the committed `flat-and-joined` shape the battery expects to fail; plus one should-fix (nine `Mn` combining marks switch the avoid-list ban off) and one on the recorded justification for R = 6.

# skills-evals PR #131 — round-6 scoped CODE review

Head `04f40b5197b77338fc6aa5e41e927960d8782184`. Round-5 head `2b1bda7`.
Reviewed against `$SP/briefs/81-fix5.md` (read in full), `$SP/reviews/131-r5-code.md`,
`$SP/reviews/131-r5-adv.md`, `$SP/reviews/131-r4-code.md`, and
`/home/user/agentskills/plugins/adam/skills/adam-writing-style/SKILL.md`
(read in full — the Avoid list, core moves 3 and 8, all five calibration
examples).

Measured in `$SP/rev131c-code` against `$SP/rev131c-ref` (`2b1bda7`) and
`$SP/mainx3` (`f82bd77`). **Tree integrity**: at start the five named files
matched `git -C /home/user/skills-evals show 04f40b5:<path> | md5sum`
exactly (`objective.py b2b70578…`, `wrapping.py 82a7082e…`, `judge.py
1f74ab50…`, `run_tests.py 37992ba5…`, `recruiter-reply/fixture.yaml
aff2abcf…`). Every mutation ran in a throwaway copy (`$SP/r6mut`,
`$SP/r6mx`, `$SP/r6n1`, all deleted). One write did land inside the work
dir and I removed it: my own `run_eval.py --arm objective-only` on a
throwaway fixture wrote the harness's default `results/` tree there
(untracked). After removal the whole work dir is **byte-identical to a
fresh `git archive 04f40b5`** (`diff -rq` clean).
`/home/user/skills-evals` read-only throughout (`git show/archive/diff/log/
merge-tree`); `git status --short` empty, HEAD still `527c729`. No network,
no real `claude`, nothing posted to GitHub, no sessions/routines/reminders,
no background processes. `$SP/rev131c-adv` never entered.

---

## 1. Verifiers — both environments

Constructed env: `env -i PATH=/usr/bin:/bin:/usr/local/bin HOME=$SP/r6work/fakehome LANG=C.UTF-8`.
Ambient env: my own shell with `SP` and `GH_TOKEN=decoy-not-a-credential` exported.

| Verifier | Expected | Ambient (+decoys) | Constructed (`env -i`) |
|---|---|---|---|
| `python3 test/run_tests.py` | 663, 2 skipped, exit 0 | **663, OK (skipped=2), exit 0** | **663, OK (skipped=2), exit 0** |
| `python3 test/test_propagation.py` | 164, 1 skipped | **164, OK (skipped=1), exit 0** | **164, OK (skipped=1), exit 0** |
| `recruiter-reply --arm objective-only` | exit 1, 4/4 "no transcript" | **exit 1, 4/4 "no transcript"** | same |
| `proposal-bio --arm objective-only` | exit 1, 3/3 | **exit 1, 3/3** | same |
| `self-appraisal-opening --arm objective-only` | exit 1, 3/3 | **exit 1, 3/3** | same |

| Guardrail | Verdict |
|---|---|
| every other fixture under `evals/` identical **per check** to `$SP/mainx3` | **YES** — 8 fixtures run in both trees, stdout diff empty after normalising the tempdir path only |
| `windows-elevation-from-wsl`, four seed-carrying transcripts (README in a `> ` block, in a fence, verbatim, alone) | **identical per check to `$SP/mainx3`** on all four; `handoff-names-elevation-and-the-line` passes in every shape, both trees (rule 19 holds) |
| `git diff --stat f82bd77 04f40b5 -- .github/` | **empty** |
| `git diff --stat 2b1bda7 04f40b5 -- '…/seed' '…/references'` | **empty** — seeds and all six references byte-unchanged |
| the three prompts vs `2b1bda7` | **byte-identical** (see below) |
| `git log --format='%ae %ce' 2b1bda7..04f40b5` | **all noreply** — author `4205216+Adam-S-Daniel@users.noreply.github.com`, committer that or `noreply@github.com` |
| `git merge-base --is-ancestor f82bd77 04f40b5` | **true** |
| pairwise judge still unwired in `run_eval` (#97) | **YES** — `run_eval.py:956-982` still refuses `mode: pairwise` and names #97 |

The three prompts at head, quoted:

```
recruiter-reply:        Reply to this recruiter's cold email in my voice, declining but leaving
                        the door open
proposal-bio:           Write my 60-word bio for this proposal
self-appraisal-opening: Draft the opening paragraph of my self-appraisal for this quarter from
                        these notes.
```

---

## 2. Per item

Hollowness column: *ref* = head's own tests/batteries measured against
`2b1bda7`'s scorer; *floor* = already correct on the ref, so the test is a
regression floor pinned by its mutation instead. Every mutation ran the
FULL suite (663) in a throwaway copy.

| Item | Verdict | Pin (file:line) | Hollowness | Mutation → red |
|---|---|---|---|---|
| **DD3 / B-1** coverage rule | **implemented as the brief wrote it**, and the named inputs close — but see finding 1 | `objective.py:1138`, `:1169`, `:1382-1407`, `:1409-1455` | **RED on ref**: 22 of the 29 paste shapes PASS `cites-both-facts` on `2b1bda7`, 0 at head; the round-3 transcript is ALL-PASS on the ref | M1 drop rule (c) → 8 failures, paste rows only (`test_every_paste_shape_fails_cites_both_facts`, `test_the_round_3_transcript_cites_nothing`, `test_a_bio_that_only_restates_the_note_is_the_notes`); M2 `C=1.0` → 10; M4 drop the container strip → 9 (link/image/footnote rows) |
| **DD3 genuine battery** (16 drafts + 189 wrap cells) | **ALL-PASS, reproduced** | `run_tests.py:7401`, `:5053` | **floor** — 16/16 all-pass on the ref too | M3 `R=3` → **63** failures across the genuine and register rows |
| **S-1** wrap column is a lower bound | **closed** | `wrapping.py:88-131` | **RED on ref** | M16 (ref `wrapping.py` verbatim) → `test_a_two_line_paragraph_draft_is_not_separable_by_line_shape`, `test_a_ragged_draft_is_not_separable_by_line_shape` red; M10 (longest-line fallback only) → the two-line test red |
| **S-2** bare tag leaves a gap, ban reads both sides | **closed** | `objective.py:1067-1078`, `:1268`, `:1900-1913`, `_text_matches_any:1783` | **RED on ref** (ref substitutes `""`, `objective.py:724` there) | M5 space-reading only → `test_a_wrapper_tag_splitting_a_banned_word_still_fires`, `test_both_tag_readings_are_load_bearing` red; M6 empty-reading only → `test_a_wrapper_tag_mid_word_cannot_switch_the_ban_off` + the same pair red. **The brief's own `tag_gap`-default mutation (M7) is a NO-OP** — suite stays 663/OK — because `transcript_matches` passes both gaps explicitly and the default now only reaches `_seed_index`; the worker's replacement (`_TAG_READINGS` + an in-process mutation test) is the load-bearing one, and both halves of it are red |
| **S-3** fold by Unicode category | **closed for `Cf` + the six fillers**; residual on 9 `Mn` — finding 2 | `invisibles.py:56-85`, `objective.py:1105` | **RED on ref** | M8 (back to the 9-char enumeration) → `test_the_fold_covers_every_invisible_category`, `test_no_format_control_hides_a_banned_term`, `test_no_format_control_defeats_provenance`, `test_an_invisible_character_hides_nothing`, `test_the_fold_in_transcript_matches_protects_the_wsl_handoff` red |
| **S-4** three documents state the ceiling | **closed and pinned** | `recruiter-reply/fixture.yaml:66-108`, `README.md:161-195`, `objective.py:1409-1455`, `:1600-1625` | **RED on ref** (the false "in whatever shape" claim is present there) | M15b (drop "diluted with enough of the agent's own words" from one header) → `test_the_headers_state_the_rule_the_scorer_applies` red; M15c (drop "re-ordering someone else's words is not writing" from the README) → `test_the_readme_states_the_same_limits` red. **M15d (gut the `_is_seed_material` docstring's rule (c) clause) stays GREEN** — the docstrings are unpinned; the brief scoped the pin to the header and the README, so this is in-scope, recorded as nit N-b |
| **S-5** fence info string is scored | **closed** | `objective.py:1280-1299` | **RED on ref** (`objective.py:950` there blanks the whole line) | M9 (return `""` from `_fence_payload`) → `test_avoid_list_words_on_a_fence_line_still_fire` red; a plain ` ``` ` line is still a delimiter (`_fence_payload("```") == ("", True)`) |
| **N-1** fixture errors exit 2 | **closed** | `run_eval.py:1004-1035`, `:797-814` | **RED on ref** | M12 (remove the objective-only `except`) → `test_a_non_boolean_strip_seed_exits_2_with_a_named_line` red |
| **N-5** the two brief-named transcripts pinned as constants | **closed** | `run_tests.py:7150-7173` | covered by the DD3 hollowness above | — |
| **N-6** `unwrap_indices([])` | **closed** | `wrapping.py:150-157` | **RED on ref** | M11 / M16 → `test_unwrapping_no_lines_yields_no_groups` red |
| **N-b(i)** the fold in `transcript_matches` | **closed** | `objective.py:1894`, test `run_tests.py:5582` | **RED on ref** (unpinned there) | M13 (drop the fold from `transcript_matches`) → `test_the_fold_in_transcript_matches_protects_the_wsl_handoff` red |
| **N-b(ii)** seed files kept apart | **closed** | `objective.py:1320-1381`, test `run_tests.py:5626` | **RED on ref** (unpinned there) | M14 (join every seed file into one whole) → `test_a_run_cannot_span_two_seed_files` red |

Measured directly, not only through the suite:

- **S-1 through the production path** (`judge.blind_order` → `judge._build_pairwise_prompt`, recruiter-reply trial 0, drafts parsed back out of the built prompt): the two-line-paragraph hyperlinked draft is **10 lines / 0 surviving wraps**, exactly like both references (10/0) — not separable by line shape. `hyperlinked` 8/0, ragged 58/69/49 **6/0**, ragged 55/66/30 **6/0**. Every one keeps `Thanks,\nAdam Daniel` on two lines. The regression floor: **486 cells** (6 committed references × columns 40–120), **0** with a surviving wrap.
- **S-2**: all eight wrapper tags × three shapes (`x<tag>leverage`, `lever<tag>age`, `lever</tag>age`) — **24 of 24 fail `no-avoid-list-words` and nothing else**. `<blockquote>`, `</details>`, `<pre>`, `</blockquote>`, `<br>` alone are still delimiters under **both** readings.
- **S-3**: `objective._fold_invisibles is judge._fold_invisibles is invisibles.fold` → **True**. A loop over `sys.maxunicode`: **163 `Cf` + 1,950 `Mn` = 2,113** code points; all 163 `Cf` and all six `ZERO_WIDTH_OTHERS` fillers (U+115F, U+1160, U+3164, U+FFA0, U+2800, U+0000) fold out of `leverage`; `fold("café") == "café"` and `"a café in town"` keeps three words. **9 `Mn` do not** — finding 2.
- **S-5**: the five fence variants (opening info string, closing info string, indented, `~~~~`, a whole sentence on the fence) — **all five fail `no-avoid-list-words`**; `_fence_payload("```py") == ("py", True)`.
- **N-1 through the real CLI** on a throwaway fixture copy with `strip_seed: "no"`: `invalid_fixture: check 'no-avoid-list-words': strip_seed must be a boolean, not 'no' …`, **exit 2, no traceback**. `SeedTooLarge` cannot fire on the objective-only path (no transcript ⇒ no index is ever built), which the code says at `run_eval.py:1005-1011`; it is driven through `run_eval._run_arm` with the agent stubbed (`test_an_oversized_seed_file_is_an_arm_error_not_a_crash`) and I confirmed that path is the only one where it can escape.

---

## 3. DESIGN DECISION 3

### 3a. The rule as implemented — is it the brief's rule?

**Yes, clause for clause.** After the invisible fold, the wrapper strip
(blockquote markers, list markers, footnote definition markers, link/image
containers, bare wrapper tags, table pipes), the fence-payload split, the
wrap reconstruction and the sentence split:

- `_seed_index` (`objective.py:1320`) reads each seed file separately, joins
  its wrapper-stripped lines with a space, and stores (i) the file's
  sentence keys, (ii) the file's whole key, (iii) **every window of
  `_SEED_COVERAGE_RUN` consecutive words** — per file, so no run spans a
  file boundary.
- `_seed_coverage` (`:1382`) marks every word of a sentence that lies inside
  some R-window of the sentence that occurs in the index, and returns
  marked/total; **0.0 when the sentence is shorter than R words**.
- `_is_seed_material` (`:1409`) is (a) whole-sentence key ∨ (b) contiguous
  run ∨ (c) `len(key) >= run_floor` **and** `coverage >= _SEED_COVERAGE`.
  The at-least-one-run condition is implicit and correct: coverage is 0
  unless a window matched, and `_SEED_COVERAGE = 0.75 > 0`.
- The 24-character floor (`_SEED_MATERIAL_FLOOR`) gates (c) as the brief
  asked; inside a marked quotation the floors are nil, as before.
- Containers: `_LINK_RE` keeps `[text]`/`![alt]` and drops the destination,
  `_FOOTNOTE_MARKER_RE` drops a line-leading `[^n]:` — both narrow, neither
  spanning a line, exactly as the brief scoped them.
- Interaction with (a)/(b): `_is_contiguous_seed_material` (`:1456`) is
  factored out so `seed_coverage_report` can say which sentences (c) could
  *newly* claim. The run-swallow rule is unchanged; note that the `seed`
  flag it reads is computed with floors **0**, so (c) can mark a short
  sentence as seed for the purpose of the run, while `above` (the real
  floors) is what licenses the drop. No genuine draft in either battery is
  affected by that asymmetry — I probed for one and could not build it.

`R = _SEED_COVERAGE_RUN = 6` (`objective.py:1138`), `C = _SEED_COVERAGE =
0.75` (`:1169`), both module constants with the measurement beside them, as
the brief required.

### 3b. Both batteries, reproduced through the real scorer

Driven through `objective.run_checks` on `run_eval.load_fixture` over the
real fixtures and the real seeds (my own driver, not the suite).

**GENUINE — 16 drafts, all ALL-PASS. Confirms the PR body.**

| draft | fixture | newly-claimable max cov | raw max cov | verdict |
|---|---|---|---|---|
| a-table-the-agent-wrote | recruiter-reply | 0.0000 | 0.0000 | ALL-PASS |
| abbreviations | recruiter-reply | 0.0000 | 0.0000 | ALL-PASS |
| bio-hard-wrapped-60/68/72/80 | proposal-bio | 0.5833 | 0.5833 | ALL-PASS (×4) |
| close-paraphrase | recruiter-reply | **0.5909** | 0.5909 | ALL-PASS |
| decimals-and-a-url | recruiter-reply | 0.0000 | 0.0000 | ALL-PASS |
| ellipsis-and-initials | recruiter-reply | 0.0000 | 0.0000 | ALL-PASS |
| employer-and-title | recruiter-reply | 0.0000 | 0.0000 | ALL-PASS |
| her-hedge-as-my-opener | recruiter-reply | 0.4800 | 0.4800 | ALL-PASS |
| one-sentence-per-line | self-appraisal-opening | 0.0000 | 0.0000 | ALL-PASS |
| plain-certifications-line | proposal-bio | 0.5833 | 0.5833 | ALL-PASS |
| quotes-her-question | recruiter-reply | 0.3810 | 0.3810 | ALL-PASS |
| repo-path | recruiter-reply | 0.0000 | 0.0000 | ALL-PASS |
| stock-phrase-end-to-end | recruiter-reply | 0.0000 | **1.0000** | ALL-PASS |

Wrap loop: **189 cells** (3 in-voice references × columns 38–100), **0
failures**; highest newly-claimable coverage in the loop 0.5128
(`in-voice/proposal-bio@38`).

**PASTE — 29 shapes, every one fails `cites-both-facts`. Confirms the PR body.**

| shape | recruiter-reply | proposal-bio | self-appraisal-opening |
|---|---|---|---|
| round-3-transcript | 1.0000 fail (+`opens-with-a-hedge`) | — | — |
| round-4-four-line-quote | 1.0000 fail (+greeting, +hedge) | — | — |
| flat-and-joined | 1.0000 fail | **0.9324** fail | 1.0000 fail |
| full-stop-space-deleted | 1.0000 fail | 1.0000 fail | 1.0000 fail |
| she-wrote-prefixed | 1.0000 fail | 1.0000 fail | 1.0000 fail |
| two-clauses-joined | 1.0000 fail | **0.9259** fail | 0.9583 fail |
| footnote-definition | 1.0000 fail | 1.0000 fail | 1.0000 fail |
| markdown-link | 1.0000 fail | 1.0000 fail | 1.0000 fail |
| markdown-image | 1.0000 fail | 1.0000 fail | 1.0000 fail |
| sub-floor-bullets | 1.0000 fail | 0.0000 fail (+`bio-is-third-person`) | 0.0000 fail |
| mid-word-invisibles | 1.0000 fail | 1.0000 fail | 1.0000 fail |

29 shapes, 0 pass `cites-both-facts`. Rule (c) alone reaches exactly
`flat-and-joined` and `two-clauses-joined` — I re-ran the worker's own
in-process mutation (`_SEED_COVERAGE = 1.01`) and got the same two, on
recruiter-reply, with no genuine draft changing verdict.

### 3c. The margins, measured by me

| quantity | measured | vs C = 0.75 | ≥ 0.1? |
|---|---|---|---|
| genuine ceiling, newly claimable (16 drafts + 189 cells) | **0.5909** (`close-paraphrase`) | margin **0.1591** | **yes** |
| paste floor, excl. `sub-floor-bullets` | **0.9259** (`two-clauses-joined` / proposal-bio) | margin **0.1759** | **yes** |

Both match the PR body to the digit. `sub-floor-bullets` really is 0 by
construction on two fixtures (three-word fragments, none as long as R) and
is caught by the floor and the run-swallow rule, so excluding it from the
*floor* population is right; it still fails `cites-both-facts` everywhere,
which the other test asserts.

**Is "newly claimable" the right denominator?** Yes, and I checked both
alternatives:

- The **raw** genuine maximum is **1.0000** — `Not interested in
  management-track roles.` inside `stock-phrase-end-to-end`, a whole seed
  sentence rule (a) has always owned. A raw denominator makes the margin
  rule unsatisfiable at any C ≤ 1, so it would be a worse number, not a
  more honest one. It changes no verdict: the operative property is the
  ALL-PASS battery, which is measured on the drafts as they are, and the
  constant's comment (`objective.py:1171-1177`) states the choice.
- Dropping the **24-character floor filter** from the ceiling measurement
  changes nothing: the newly-claimable maximum is still **0.5909**. So the
  measured ceiling is not an artefact of either filter.

### 3d. The round-5 battery, re-run

Every shape the task names, measured on the real fixtures at head:

| input | required | measured |
|---|---|---|
| round-3 transcript, verbatim (U+2014) | fail `cites-both-facts`, and hedge | **fails `cites-both-facts` and `opens-with-a-hedge`**; residue is exactly `On Tue, 1 Sep 2026, Dana Whitcombe wrote: My own note:` |
| round-4 four-line `> ` paste | fail | **fails greeting, hedge and `cites-both-facts`** |
| seed flat, `". "` → `" and "`, + register line | fail | **fails on all three fixtures** |
| space after every full stop deleted | fail | **fails on all three** |
| `She wrote: ` prefixed | fail | **fails on all three** |
| two clauses joined by a connective | fail | **fails on all three** |
| footnote / link / image containers | fail | **fails on all three, all three shapes** |
| sub-floor bullets beside a 110-char line | fail | **fails on all three** |
| one mid-word invisible from each of the seven classes | fail | **fails on all three** |

The one carried exception, which head records itself
(`run_tests.py:7449-7457`): the round-3 transcript still **passes**
`greets-the-recruiter-by-name`, because the residue's `Dana Whitcombe
wrote:` attribution line is not in any seed file and is therefore the
agent's own writing under the rule. Filed as nit N-a — it is a greeting-
pattern width question, not a provenance leak, and the fixture still fails.

### 3e. The R = 6 deviation, and the probe it invites

**Is the recorded reason measured and true? No — it is measured at a C the
tree does not use.** `objective.py:1148-1154` records "the committed
in-voice references … lost `cites-both-facts` at 126 of the 189
wrap-column cells at four and 63 at five." Measured by me, at the
committed **C = 0.75**:

| R | in-voice references losing `cites-both-facts` (of 189) | genuine battery failures |
|---|---|---|
| 4 | **63** (all `self-appraisal-opening`) | 1 (`plain-certifications-line`) |
| 5 | **0** | 0 |
| 6 | 0 | 0 |
| 7 | 0 | 0 |

The recorded 126/63 reproduce **exactly at C = 0.60** — the brief's
*starting* value — where R=4 loses `proposal-bio` (63) + `self-appraisal`
(63) = 126 and R=5 loses `proposal-bio` (63). So the numbers are real
measurements of a configuration the tree does not ship. The second recorded
reason ("six is the shortest run at which the seed's longest FACT phrases …
cannot be a run on their own") is also satisfied at five: the longest such
phrase in the recruiter seed is `Northgate Bell Talent Group`, four words.

**What does justify 6 over 5 at the shipped C** is the margin, which the
comment does not use for this: at R = 5 the genuine newly-claimable ceiling
jumps to **0.9167** (`in-voice/self-appraisal-opening` at column 38)
against a paste floor of 0.9259 — a margin of 0.009, far inside the 0.1
rule. So the constant is right and the recorded reason for it is wrong.
Filed as finding 3.

**The probe R = 6 invites — and it passes.** Take the committed paste
shape `flat-and-joined` (the register line plus the whole seed flattened,
with `" and "` where every `". "` was), which **fails `cites-both-facts` on
all three fixtures**, and change one parameter: insert the same connective
every **fifth word** instead of at every full stop. Zero substantive words
of the agent's; the inserted token is the single word `and`; 56 insertions
in 281 seed words = **16.6 % of tokens**.

| paste | recruiter-reply | proposal-bio | self-appraisal-opening |
|---|---|---|---|
| `flat-and-joined` (committed shape) | fail `cites-both-facts` | fail | fail |
| the same seed, `and` inserted every 5th word | **ALL-PASS** | **ALL-PASS** | **ALL-PASS** |

The fact-bearing sentence measures **coverage 0.000**: `The engagement is
contracted and through March 2027.` — eight words, and every 6-window in it
contains the inserted `and`, so nothing is marked at all. Both facts are in
the residue; `REQ-4417` and `March 2027` both survive.

Per the task's own criterion this is the round-2 (a) defect returning, at
blocker severity. Finding 1 states it, with its repeat status and the
structural reason no constant fixes it.

### 3f. Hollowness of the batteries

| population | on `2b1bda7` (ref) | at head |
|---|---|---|
| 29 paste shapes | **22 PASS `cites-both-facts`** (the defect) | 0 pass |
| round-3 transcript | **ALL-PASS** | fails `cites-both-facts` + hedge |
| round-4 paste | already failing | already failing |
| 16 genuine drafts | 16 all-pass | 16 all-pass (**regression floor**, pinned by M3: `R=3` → 63 failures) |
| 189 wrap cells | 0 failures | 0 failures (**regression floor**, same pin) |

---

## 4. The merge `615b2fb`, audited with `ast`

| Claim | Verdict |
|---|---|
| no top-level function lost from `2b1bda7` or from `f82bd77`, in `objective.py` or `run_tests.py` | **none lost either side** (head: 77 top-level fns in `objective.py`, 29 test classes) |
| no class or test method lost from either side | **none lost either side** |
| `CHECKS` is the exact union | **YES** — ref 15 ∪ main 24 = head **24**, `head == ref | main` exactly, ref-only `[]`, main-only 9 (`git_ref_unchanged`, `git_remote_url_is`, `git_worktree_list_matches`, `no_git_config_names_path`, `reaper_avoided_paths`, `reaper_ran_in_standalone_repo`, `pin_comment_absent`, `pins_match_reference`, `platform_refs_on_tag`) |
| `main`'s six git-state check types present | **YES** — seven of them, all listed above |
| `strip_seed` in `_CHECK_ALLOWED_KEYS` | **YES** — `transcript_matches: {must_match, must_not_match, strip_seed}` |
| both fixtures load / every fixture loads | **YES** — all 9 fixture dirs load through `run_eval.load_fixture`; unknown check types **0**, unknown constraint keys **0**, across all 61 checks |
| README and DESIGN are the union | **YES** — 0 lines lost from either parent in `README.md`; `DESIGN.md` loses 10 ref lines but they are re-flowed prose in the candidate list, and **no backticked fixture/skill name is lost from either parent** |

**What the textual merge with `d5e06ee` must reconcile.** `git merge-tree
f82bd77 04f40b5 d5e06ee` (read-only): three files are "changed in both" —
`DESIGN.md`, `README.md`, `test/run_tests.py` — but only **one conflict
hunk** exists, and it is in `test/run_tests.py`: the import block, where
this branch adds `import copy` (for `TestIssue81`'s fixture deep-copies) and
`d5e06ee` does not. `DESIGN.md` and `README.md` auto-merge. PR #132's own
additions arrive cleanly: `BASH_CI_DIR = REPO_ROOT / "evals" /
"review-bash-ci-reliability"` beside the other eval-directory constants, and
`TestIssue74` (plus `_iter_regex_tokens` and friends) appended. So: keep
`import copy`, take both sides' constants and both sides' classes. The task's
statement that the conflict is `test/run_tests.py` only is correct.

---

## 5. New findings

### BLOCKER

**1. A paste of the seed with one contentless connective every fifth word —
zero substantive words of the agent's — ALL-PASSES all three fixtures,
including `cites-both-facts`.**
`harness/scorers/objective.py:1382-1407` (`_seed_coverage`) with `:1138`
(`_SEED_COVERAGE_RUN = 6`).

Reproduction, through `objective.run_checks` on the committed fixtures and
seeds. Construction is the committed `flat-and-joined` shape with one
parameter changed:

```python
register = "Hi Dana,\n\nSorry — here is the text you asked for.\n"      # the battery's own line
flat     = " ".join(seed_text("recruiter-reply").split())
words    = flat.split()
body     = " ".join(w + (" and" if (i+1) % 5 == 0 else "")
                    for i, w in enumerate(words))                       # 56 insertions / 281 words
paste    = register + "\n" + body + "\n"
```
```
recruiter-reply         ALL-PASS   (no-avoid-list-words, greets-the-recruiter-by-name,
                                    opens-with-a-hedge, cites-both-facts)
proposal-bio            ALL-PASS
self-appraisal-opening  ALL-PASS
```
against the shape it is one parameter away from, which the suite already
asserts must fail:
```
flat-and-joined   recruiter-reply / proposal-bio / self-appraisal-opening   fail: cites-both-facts
```

**Why it gets through.** Coverage marks a word only when an **unbroken**
run of R = 6 sentence-words containing it occurs in a seed file. One
inserted token every five words means *no* 6-window is clean, so coverage
collapses to **0.000** — not to 5/6 — on every sentence, including the
fact-bearing `The engagement is contracted and through March 2027.` Rules
(a) and (b) miss for the same reason they always did. 16.6 % of the tokens
are one repeated function word; the agent has written nothing.

**It is structural, not a constant that needs tuning.** I swept R:

| R | genuine newly-claimable ceiling | splice-every-5 fact sentence |
|---|---|---|
| 4 | 0.9167 | 0.500 |
| 5 | 0.9167 | 0.000 |
| 6 | 0.5909 | 0.000 |
| 7 | 0.5909 | 0.000 |

There is no (R, C) pair that keeps the 16-draft + 189-cell genuine battery
and catches an every-(R−1) splice: at R = 6 and R = 5 the coverage is 0 at
any C, and at R = 4 the coverage is 0.5 while the genuine ceiling is 0.5909.
A coverage rule with a fixed run length is defeated by inserting one word
every R−1 words, and the cost of the attack **falls** as R rises — so the
R = 6 choice made the escape cheaper than R = 4 would have, which is the
one place the unmeasured justification for R (finding 3) actually bites.

**What IS recorded, in fairness.** All three fixture headers and the README
do state a dilution ceiling: "a paste diluted with enough of the agent's own
words *in the same sentence* survives by design"
(`recruiter-reply/fixture.yaml:96-99`, `README.md:174-178`). What is not
recorded, and what a reader of those documents plus `C = 0.75` would predict
wrongly, is the **size** of "enough": the documents imply that more than a
quarter of a sentence's words must be the agent's, when in fact one
contentless word per five drives the measured coverage to zero rather than
to 0.83. And the ceiling is stated as a *dilution* limit, which suggests
some contribution by the agent; here the contribution is a single repeated
conjunction.

**Severity and repeat status: BLOCKER, and a REPEAT of the defect class —
round-2 item (a), round-3 adv B-1(a), round-4 adv B-1, round-5 B-1 (code
and adv), all blocker, all "a transcript made of nothing but the seed's own
words satisfies `cites-both-facts`". It is a REPEAT of the class and the
severity, on a NEW input: the round-3 transcript itself, the input every
brief since round 3 named, is now correctly caught, as are all 29 committed
shapes. Same recommended fix direction as rounds 4 and 5 (decide provenance
below the whole-sentence grain), now with the added measurement that the
grain chosen — an unbroken R-word window — is itself breakable at 1/R
cost.** Two candidate directions that do not need a new instrument: score
coverage over the sentence's words that appear in the seed *at all* (a bag
test) in addition to the run test; or count runs down to 2–3 words but weight
them, so a stream of 5-word runs cannot read as composition. Either is a
decision, not a patch, which is why this parks for the owner.

*What is emphatically not wrong here*: the worker implemented the brief's
design decision exactly, the two constants are supported by the batteries it
built, and the 29 committed shapes and the round-3 transcript all close. The
defect is in the shape of the rule the brief specified, for the fifth round
running.

### SHOULD-FIX

**2. Nine `Mn` combining marks switch the avoid-list ban off inside a
banned word, in a draft that otherwise ALL-PASSES — while `objective.py` and
`invisibles.py` both say "every `Cf` and every `Mn` code point goes".**
`harness/scorers/invisibles.py:79-85` (`fold`: NFKC **first**, then drop
`Cf`/`Mn`) and `objective.py:1099-1105`.

Measured over all 1,950 `Mn` code points through `objective.run_checks` on
recruiter-reply:

```
U+0301 U+0307 U+030C U+030F U+0311 U+0323 U+0327 U+0331 U+0341
  → "We would rather not lever<mark>age a move now."  ALL-PASS (4/4)
  → invisibles.fold("leveŕage") == "leveŕage"
```
NFKC **composes** each of these onto the preceding `r`, producing a
precomposed letter that is no longer `Mn`, so step 2 cannot drop it and
`\bleverage\b` no longer matches. The other 1,941 `Mn` do not compose onto
`r` and are dropped correctly, and every one of the 163 `Cf` and all six
fillers folds.

The tests are honest about the mechanism — `_zero_width_code_points()`
(`run_tests.py:4513-4525`) deliberately excludes `Mn` from the per-draft
loops and says why, and `test_the_fold_covers_every_invisible_category`
only asserts that a mark **standing alone** folds to nothing. So this is a
documented consequence rather than a broken claim in the test. But the
module prose in two places says the category "goes", the recorded ceiling
names only *Cyrillic homoglyphs* and only for **provenance**, and a
measurable `no-avoid-list-words` bypass is exactly what round-5 S-3 was
filed for.

*Fix, and it is the pattern S-2 already established.* Add a second reading
for `must_not_match` only: fold, then NFD-decompose and drop `Mn` again, and
forbid a banned pattern in either reading — `_text_matches_any` already
takes a list. `café` keeps its accent in the reading that `must_match` uses.
Cheap, consistent, and one test (the same `sys.maxunicode` loop, extended
to `Mn`) pins it.

**Repeat status: NEW.** Round-5 adv S-3 was the enumeration, which is gone;
this is a residual of its fix. Not a repeat of any round-3/4/5 finding.

**3. The recorded justification for `R = 6` — the deciding constant — is a
measurement of a configuration the tree does not ship.**
`harness/scorers/objective.py:1148-1154`.

Measured above (§3e): at the committed `C = 0.75` the in-voice references
lose `cites-both-facts` at **63** of 189 cells at R = 4 and **0** at R = 5,
not 126 and 63. The recorded figures reproduce exactly at `C = 0.60`, the
brief's starting value. The comment's second reason ("six is the shortest
value at which the seed's own longest FACT phrases … cannot be a run on
their own") is satisfied at five as well — the longest is four words.

The constant is nonetheless **right**, for a reason the comment does not
give: at R = 5 the genuine newly-claimable ceiling is 0.9167 against a paste
floor of 0.9259, a margin of 0.009 against the 0.1 rule. The fix is to
correct the two sentences and add the margin figures; nothing in the code
moves. It matters because these prose measurements beside a calibration
constant are what a future round will read instead of re-measuring, and
`test_the_coverage_constants_are_named_with_their_margins`
(`run_tests.py:7599`) pins only `0.59`, `0.93` and `margins stay at 0.1 or
better` — the 126/63 figures are unpinned.

**Repeat status: NEW in its particulars**, but the same *class* as round-5
S-4 ("documents assert properties measured false"), which is why it is
should-fix rather than nit.

### NITS

**N-a (record-only).** The round-3 transcript still passes
`greets-the-recruiter-by-name`: the residue is `On Tue, 1 Sep 2026, Dana
Whitcombe wrote: My own note:`, and the attribution line appears in no seed
file, so it is the agent's under the rule. Head records this deliberately
(`run_tests.py:7449-7457`) and it is a greeting-pattern width question, not
a provenance leak; `cites-both-facts` and `opens-with-a-hedge` both fail, so
the fixture fails. New at head only because round-5's blocker masked it.

**N-b (record-only).** The `_is_seed_material` / `strip_seed_material`
docstrings are **not** pinned: gutting rule (c)'s clause out of
`_is_seed_material`'s docstring leaves the suite at 663/OK (M15d). The
brief scoped S-4's pin to the recruiter header and the README paragraph, so
this is in scope; recorded because those docstrings now carry the ceiling
statement too.

**N-c (record-only, pre-existing).** Six of the 24 `CHECKS` types have no
`_CHECK_ALLOWED_KEYS` entry (`event_only_workflows_unfiltered`,
`no_event_interpolation_in_run`, `non_remote_refs_unchanged`,
`pin_comment_absent`, `required_checks_early_skip`, `yaml_parses`). All six
take no constraint keys (`non_remote_refs_unchanged`'s `seed` is injected by
`run_checks` explicitly), and an audit over all 61 checks in all 9 fixtures
reports zero dropped keys — so nothing is weakened today. Pre-existing on
`main`, not this PR's; recorded because the guard's own docstring says the
validation runs "for every type".

**N-d (record-only).** `_provenance_paragraphs` computes the `seed` flag
with floors of **0** (`objective.py:1753`), so rule (c) can mark a
sub-floor sentence as the seed's for the run-swallow rule while `above`
(the real floors) is what licenses the drop. I could not construct a
genuine draft that loses anything to it, and re-measuring the ceiling with
the 24-character filter removed gives the same 0.5909, so it is an
observation rather than a finding.

---

## 6. What I could not check

- **Anything about a real judge.** No network and no real `claude`, so every
  judge measurement is structural — `blind_order` → `_build_pairwise_prompt`
  over the committed references. Whether a model would rank finding 1's
  paste last is unmeasured; that nothing scores it today is measured, and
  the judge is still unwired (#97).
- **CI on `04f40b5`.** Not queried — offline review.
- **`SeedTooLarge` through the real CLI.** Structurally unreachable on the
  objective-only path (no transcript ⇒ no index); verified through
  `run_eval._run_arm` with the agent stubbed, which is the only site where
  it can escape.
- Line numbers are from `$SP/rev131c-code` as exported; the tree was never
  modified.

## 7. Tree integrity

`find . -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum | md5sum`

- **before** (five named files verified against `git show 04f40b5:<path>`,
  all OK; whole-tree digest not taken until after the stray `results/` was
  removed)
- **after**: `4822413b5afdbad4e1e9d00a2a295f5e`, and `diff -rq
  --exclude=__pycache__` against a fresh `git archive 04f40b5` is **empty**
  — no tracked file in the work dir was modified at any point.

The one write that landed inside the work dir was an untracked `results/`
directory (`results/adam-writing-style/20260905T225714Z/{report.md,
objective-only/summary.json}`) produced by my own `run_eval.py` CLI run
using the harness's default `--results-dir`; I deleted it and re-verified.
All mutation copies (`$SP/r6mut`, `$SP/r6mx`, `$SP/r6n1`) deleted. Nothing
written under `/root/.claude` or any real HOME path.
