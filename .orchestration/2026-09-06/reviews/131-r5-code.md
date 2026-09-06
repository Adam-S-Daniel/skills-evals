NOT CLEAN — one blocker: the round-3 transcript the brief named by name still ALL-PASSES recruiter-reply, because step (5)'s exemption is implemented as "the sentence is not a contiguous seed run" rather than as the decision's own "composed with its own words", so a sentence carrying not one word of the agent's is scored as the agent's writing and supplies `cites-both-facts`; plus one should-fix (a fence line's info string is deleted whole, so parking avoid-list words on it switches the ban off and the reply ALL-PASSES).

# skills-evals PR #131 — round-5 code review

Head `2b1bda75aeae9eec86424520f8f3805babcb7fd5`. Round-4 head `f01c1e6`.
Reviewed against `$SP/briefs/81-fix4.md` (read in full), round 4's two
reports, and `/home/user/agentskills/plugins/adam/skills/adam-writing-style/
SKILL.md` (read in full; every calibration example is a blockquote, which is
why "formatting cannot decide authorship" is load-bearing here).

Everything below was measured in `$SP/rev131e-code` (verified export:
`objective.py` `77614b42…`, `judge.py` `70b84474…`, `run_tests.py`
`c8f15628…`), against `$SP/rev131e-ref` (`f01c1e6`, `judge.py` `0efb60f8…`,
`run_tests.py` `7b129c35…`) and `$SP/mainx` (`8d131bd`, `objective.py`
`9b58c3d9…` and `run_tests.py` `05beb976…`, both byte-equal to
`git show 8d131bd:<path>`). **No file in `$SP/rev131e-code` was modified**:
every mutation, the hollowness drop-in and the one feasibility patch ran in
throwaway copies at the same directory depth (`$SP/r5mut{,2,3}`,
`$SP/r5hollow`, `$SP/r5fence`), all deleted. `/home/user/skills-evals`
read-only (`git show/diff/log`; `git status --short` empty, HEAD still
`527c729`). No network, no real `claude`, nothing posted to GitHub, no
sessions/routines/reminders. `$SP/rev131e-adv` never entered.

---

## 1. Verifiers

| Verifier | Expected | Measured |
|---|---|---|
| `python3 test/run_tests.py` | 461, 2 skipped, exit 0 | **461, OK (skipped=2), exit 0** |
| `python3 test/test_propagation.py` | 164, 1 skipped | **164, OK (skipped=1), exit 0** |
| `run_eval.py …/proposal-bio --arm objective-only` | exit 1, 3 of 3 failing | **exit 1, 3/3 failing** |
| `run_eval.py …/recruiter-reply --arm objective-only` | exit 1, 4 of 4 | **exit 1, 4/4** |
| `run_eval.py …/self-appraisal-opening --arm objective-only` | exit 1, 3 of 3 | **exit 1, 3/3** |
| the three, head vs `f01c1e6` | identical | **stdout byte-identical, all three** |

**The arithmetic, counted per tree rather than asserted** (`ast`, one test
method count per class):

- `$SP/rev131e-ref` (`f01c1e6`) alone: **345** = 217 shared base + 128 `TestIssue81`.
- `$SP/mainx` (`8d131bd`) alone: **305** = the same 217 + 88 `TestIssue86`.
- head: **461** = 217 + 156 `TestIssue81` + 88 `TestIssue86`. So 345 + 88 + 28 = 461,
  and 305 + 156 = 461. Both readings agree; the merge commit's own
  "217 + 88 + 128 = 433" plus this round's 28 lands on the same number.
- `TestIssue81` grew by exactly **28 added, 2 changed, 0 removed**.

The two skips are `pypdf not installed` in main's `TestIssue82`. The
avoid-list drift test is not skipped.

---

## 2. The merge (`afb5353`), audited with `ast` — never a regex

| Claim | Verdict |
|---|---|
| `CHECKS` registry is the exact union of both parents | **YES.** ref 11 ∪ main 15 = head 15; lost from ref `[]`, lost from main `[]`, invented `[]` |
| `_CHECK_ALLOWED_KEYS` carries every key these three fixtures use | **YES.** `transcript_matches: {must_match, must_not_match, strip_seed}`; an unknown-key audit over all 9 `fixture.yaml`s (`set(check) - _CHECK_META_KEYS - allowed`) reports **0 violations** |
| each #81 fixture loads through `run_checks` with no ValueError | **YES** — 4, 3 and 3 checks respectively; every `type` resolves in `CHECKS` |
| no function or class lost from either side | **YES from main** (`objective`, `judge`, `run_eval`: none lost). From ref, `objective` loses `_normalise`/`_unquote` and `judge` loses `_unwrap_block`/`_wrap_width` — all four **replaced by name** this round (`_key`, `_dequote`, `_strip_wrapper`, and `wrapping.unwrap_block`/`wrapping.wrap_width`, which `judge` re-aliases at `judge.py:461-462`). New: `FixtureError`, `SeedTooLarge`, `_sentences`, `_strip_table_pipes`, `_is_seed_material` |
| every test class from both sides kept | **YES** — 23 classes on each side, 24 in head, the union; `TestIssue86`'s 88 methods and `TestIssue81`'s all present |
| DESIGN.md and README.md are the union | **YES.** `git diff 8d131bd 2b1bda7 -- DESIGN.md` adds only the Class-C `judge:` paragraph; `git diff f01c1e6 2b1bda7 -- DESIGN.md` adds only main's `post-failure-comment` graduation. README the same both ways (branch's tree lines + `judge:` section on one side, main's `post-failure-comment` tree lines on the other) |
| every other fixture scores identically | **YES** — §7 |

---

## 3. The DESIGN DECISION as implemented

Read in this order, as instructed: `strip_seed_material`'s docstring
(`objective.py:878-937`), the README statement
(`evals/adam-writing-style/README.md:106-180`), then the code.

| Step | Verdict | Pin |
|---|---|---|
| (1) invisibles fold, incl. U+2062/U+034F/U+FE0F/U+180E | **YES** | `objective.py:652-654`, `judge.py:450-452` (identical patterns, asserted by test) |
| (2) wrapper only comes off; a comment / attributed tag / attribute text stays | **YES** | `_WRAPPER_TAGS` `objective.py:626-629`, `_strip_wrapper` `:707-726` |
| (3) hard wraps undone by the judge's own helper, table pipes to spaces | **YES** — one shared module `harness/scorers/wrapping.py`, imported by both | `wrapping.py:113-136`, `objective.py:973`, `_strip_table_pipes` `:728-730` |
| (4) split into sentences at `.!?;`+space and at a list/table line break | **YES** | `_SENTENCE_SPLIT_RE` `objective.py:660`, `_sentences` `:701-704` |
| (5) a ≥24-char contiguous run **or** a whole seed sentence (≥12) is the seed's; a composed sentence stays | **PARTIAL — see finding 1.** The two positive halves are exactly as written (`_is_seed_material` `:794-823`, floors `:597`/`:605`). The *negative* half is implemented as "the sentence's whole key is not a contiguous run", which is **wider** than the decision's "composed … **with its own words**" and than the docstring's "joined by **its own** connective" | `objective.py:994-999`, `:1011-1024` |
| (6) both `must_match` and `must_not_match` score the residue | **YES** — one `text` string reaches `_text_matches` | `objective.py:1122-1127` |
| no whole-reply fallback | **YES**, and now pinned (§5) | `objective.py:1031` |
| opt-in per check, real boolean | **YES** | `objective.py:1833-1841` |

---

## 4. Per item

Hollowness = head's `test/run_tests.py` dropped into a copy of
`$SP/rev131e-ref` (`f01c1e6`), `TestIssue81` only. **Main's classes reported
separately:** `TestIssue86`'s 88 tests cannot run there at all (main is not
merged into `f01c1e6`), so they are excluded from every hollowness verdict
below; the whole `TestIssue81` run on that tree is 156 tests, 142 failures +
10 errors, and **21 of the 28 added / 2 changed tests are red there**.
Mutation column: 34 mutations, each applied to a fresh copy of head, whole
suite run. **32 red, 2 green** (both listed as nits).

| Item | Verdict | Pin (file:line) | Hollowness vs `f01c1e6` | Mutation → result | Killed by its own test? |
|---|---|---|---|---|---|
| **B1** re-selected seed passes everything | **MOSTLY FIXED — one named input still ALL-PASSES (finding 1)** | `objective.py:794-823`, `:994-1024` | `test_a_repasted_seed_cites_nothing_however_it_is_re_broken` RED (72 subtests), `test_each_half_of_the_provenance_rule_is_load_bearing` RED | delete the seed-sentence rule → RED(1); delete the contiguous-run rule → RED(48); delete the unwrap → RED(73); delete the paste-run rule → RED(197); remove the marked-quote floor relief → RED(16) | Yes for the 8 shapes it tests; **no** for the round-3 transcript, which no test carries |
| **B2** genuine hard-wrapped bio deleted | **FIXED** | `objective.py:967-999` (sentence unit, after the shared unwrap) | `test_a_bio_wrapped_where_the_seed_wraps_keeps_its_own_words` RED, `test_the_verdict_is_the_same_at_every_wrap_column` RED | delete the unwrap → RED(73) | Yes |
| **B3** `_wrap_width` eats a model-shaped sign-off | **FIXED** | `wrapping.py:22-33`, `:49-88`; `judge.py:461-462` | `test_a_model_shaped_draft_keeps_its_sign_off` RED, +4 more | `WRAP_EVIDENCE_LINES=1` → RED(1); drop the `MIN_WRAP_COLUMN` fallback → RED(4); width=longest → RED(1) | Yes — and `2b1bda7` exists precisely because the first two were not *independently* load-bearing |
| **S1** tag/comment carrying words deletes a line | **FIXED** | `objective.py:626-629`, `:707-726` | `test_a_tag_carrying_words_is_the_agents_writing` RED, `test_a_tag_inside_a_line_does_not_shorten_it_onto_a_seed_line` RED | widen the tag set to `<[^<>]*>` → RED(4); remove the bare-tag strip → RED(7) | Yes |
| **S2** her `From:` header greets her | **FIXED** | `objective.py:689-698` (no tag strip in the key) | `test_her_own_email_never_greets_her` RED | reinstate an HTML-tag strip inside `_key` → RED(1) | Yes |
| **S3** indentation defeats the unwrap | **FIXED** | `_QUOTE_MARKER_RE` `objective.py:612` | `test_an_indented_deliverable_is_still_the_deliverable` RED | back to `^ {0,3}> ?` → RED(2) | Yes |
| **S4** battery cannot fail on B1; fallback unpinned; stale docstring | **FIXED** (docstring corrected at `run_tests.py:4091-4102`) | `run_tests.py:4519-4557` (`_repaste`), `:4606-4618` | `test_a_wholly_quoted_seed_cites_nothing` green on ref *correctly* (the code was already right there); it has teeth: killed by B1-d | **restore the whole-reply fallback → RED(35)**, incl. that test — the round-4 gap is closed | Yes |
| **N1** four invisibles | **FIXED** | `objective.py:652-654` | `test_an_invisible_character_hides_nothing` RED (both directions, per codepoint) | narrow `_INVISIBLE_RE` → RED(8) | Yes |
| **N2** `strip_seed` truthiness | **FIXED** | `objective.py:1833-1839`, `FixtureError` `:669` | `test_strip_seed_has_to_be_a_real_boolean` RED | `isinstance` check → `False` → RED(6) | Yes |
| **N3** `deploy-scaffold` across a hyphen wrap | **FIXED** | `self-appraisal-opening/fixture.yaml:144` (`\bdeploy\s*-\s*scaffold\b`) | `test_the_verdict_is_the_same_at_every_wrap_column` RED | pattern back to `\bdeploy-scaffold\b` → RED(1) | Yes |
| **N4** silent report-cell cut | **FIXED** | `run_eval.py:519` | `test_a_truncated_report_cell_says_so` RED | drop the `…` → RED(1) | Yes |
| **N5** seven scan gaps + four by-name | **FIXED (all seven)** | `_SECRET_RE` `run_tests.py:3422-3437`, `_IBAN_RE` `:3442`, `_IPV6_RE` `:3452`, `_BARE_HOST_RE` `:3390` | the three scan tests are green on ref only because the patterns live in `run_tests.py` itself, which I copied over — untestable that way; mutations are the evidence | drop `_BARE_HOST_RE` from the walk → RED(1); drop the by-name token alternatives → RED(8); drop `_IBAN_RE` → RED(1); drop the JWT alternative → RED(1); break `_IPV6_RE` → RED(5) | Yes |
| **N6** three-intervening-words record | **FIXED** | `self-appraisal-opening/fixture.yaml:94-103` | n/a (comment) | none — correctly, a recorded bound has nothing to pin | n/a |
| **N7** 1 MiB cap | **FIXED** | `_SEED_READ_CAP` `objective.py:687`, `SeedTooLarge` `:673`, raise `:772-777` | `test_a_seed_file_over_the_read_cap_is_refused_by_name` RED | make the raise unreachable → RED(1) | Yes |
| **rule 19** opt-in stays opt-in | **FIXED** | `objective.py:1833-1841` | `test_a_real_boolean_still_works_both_ways` RED | remove the gate → RED(2), incl. the WSL fenced-handoff test | Yes |
| **table pipes** (`639c345`) | **FIXED** | `objective.py:728-730`, `:984-991` | `test_a_table_leaves_no_pipes_behind_in_the_residue` RED | stop stripping pipes → RED(1) | Yes |

**Per-item measurements through the production entry point**
(`objective.run_checks(fixture, workspace, seed, transcript=…)` on the
committed fixtures and seeds; `--workspace` exercised separately in §7):

- **B1**, seed perturbations, bare and under a filler, all three fixtures
  (42 cells): exact paste, re-wrapped at 55, **re-broken at sentence
  boundaries**, selected sentences on one line, trailing `!` per line,
  Markdown table, one U+2062 per line — **every cell fails at least one
  check, and every one fails `cites-both-facts`**. Round 4 measured
  `selected sentences` / `trailing !` / `table` / `invisibles` ALL-PASSing
  or passing `cites`. The round-4 adversarial four-line paste fails 3 of 4
  in all four containers (`>`, unmarked, fenced, `<blockquote>`); round 4's
  proposal-bio and self-appraisal ALL-PASS inputs now fail
  `cites-both-facts`. **The one exception is round 3's own transcript —
  finding 1.**
- **B2**: the 72-wrapped in-voice bio ALL-PASSES on head and loses **0** of
  its own lines (`f01c1e6`: fails `cites-both-facts`, loses
  `deployment pipeline behind eleven state agency websites, and ran the`
  and the line under it). Width sweep 38→100 on all three committed
  references: **one verdict (ALLPASS) at all 63 columns**, and **0 columns
  lose a line of the reference's own** — on `f01c1e6`, 14 columns lose one
  in proposal-bio and 8 in self-appraisal.
- **B3**: `judge._normalize_draft_text(UNWRAPPED_CANDIDATE)` ends
  `"Thanks,\nAdam Daniel"` on head, `"Thanks, Adam Daniel"` (joined) on
  `f01c1e6`. Through `judge.blind_order(…, trial 0)`, recruiter-reply, the
  three drafts' normalised line lengths: head `[8,91,178,197,7,11]`,
  `[10,150,189,194,13,11]`, `[8,260,110,7,11]` — **all three end
  `…,7,11` with last line `Adam Daniel`**; on `f01c1e6` the agent's is
  `[8,260,110,19]`, last line `Thanks, Adam Daniel`, the odd one out. The
  hyperlinked and hard-wrapped drafts keep the sign-offs they were written
  with on both trees.
- **S1**: `<span title="…leverage…">`, `<img alt="…synergy…">`,
  `<!-- we can leverage this -->` and `<div class="x">…</div>` each make
  `no-avoid-list-words` **fire** on head (three of the four ALL-PASSED on
  `f01c1e6`); the mid-line `I<leverage synergy robust> was looking…` line
  fires too and `leverage` is in the residue (ALL-PASSED on `f01c1e6`).
  Bare `<blockquote>` / `</details>` / `<pre>` / `<p>` / `<br>` /
  `</code>` are still dropped as delimiters.
- **S2**: `seed/inbox/cold-email.md` pasted in 6 shapes × {alone, +filler}
  = **12 cells, `greets-the-recruiter-by-name` False in all 12**; on
  `f01c1e6` 5 of those 12 were True.
- **S3**: the committed in-voice reply plain / indented 1,2,3 / tab / `>` +
  two spaces / inside a list item / indented fence in a list — **8 of 8
  ALL-PASS** (7 of 8 failed `opens-with-a-hedge` on `f01c1e6`).
- **N1**: per codepoint (U+2062, U+034F, U+FE0F, U+180E + the five earlier),
  the ban fires through it **and** provenance still matches through it — 9
  of 9 both ways on head; on `f01c1e6` the four new ones hid the ban and
  all nine broke provenance.
- **N4**: end to end. A `mode: pairwise` fixture → exit **2**, `report.md`
  cell ends `…wires the call site o…`, and both `summary.json`s carry the
  full 354-character detail.
- **N5**: JWT, IBAN, IPv6 literal, `github_pat_`, `xoxp-`, bare PEM body
  line, **and the bare real domain** (`northgatebell.com/contact`, caught
  by `_BARE_HOST_RE`) — 7 of 7 caught on head, 1 of 7 on `f01c1e6` (and
  that one only by the phone regex). `ghs_`, `gho_`, `sk-proj-`, `AIza…`
  all match `_SECRET_RE` by name.
- **N7**: a seed file at exactly 1 MiB reads whole; one byte over raises
  `SeedTooLarge` naming the file and the cap. On `f01c1e6` it truncated
  silently.

---

## 5. Shape grid — round 4's grids re-run through the real scorer, plus the sentence-grain cases

**A** = the fixture's own committed `in-voice` reference (marker stripped)
beside the quoted whole seed → must ALL-PASS. **B** = a contentless filler
that greets/hedges/registers correctly and carries neither fact → must fail
at least one. Both orders. 23 shapes × 3 fixtures × 2 columns × 2 orders =
**276 cells.**

| Shape | quote AFTER the draft (A / B) | quote BEFORE the draft (A / B) |
|---|---|---|
| `>` at 0 / 1 / 2 / 3 spaces | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| nested `> >` | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| NBSP before `>` | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| ZWSP before `>` | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| ``` fence — no info / `markdown` / trailing space | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| `~~~` / `~~~text` / `~~~~` | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| unterminated ``` fence | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| **4-space indented block** | ALLPASS ×3 / fails `cites` ×3 | **recruiter-reply fails `opens-with-a-hedge`**; bio + appraisal ALLPASS / fails `cites` ×3 |
| lazy continuation | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| fence inside a blockquote | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| blockquote inside a list item | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| HTML `<blockquote>` / `<details>`+`<summary>` / `<pre>` | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |
| **verbatim paste, no marker** | ALLPASS ×3 / fails `cites` ×3 | **recruiter-reply fails `opens-with-a-hedge`**; bio + appraisal ALLPASS / fails `cites` ×3 |
| CRLF `>` quote | ALLPASS ×3 / fails `cites` ×3 | ALLPASS ×3 / fails `cites` ×3 |

**Column A: 136 of 138 ALLPASS. Column B: 0 of 138 ALLPASS.** Round 4 had 4
column-A misses in 120 cells; two of those four (unterminated fence, lazy
continuation) are now clean and two remain — both are the same documented
mechanism (an *unmarked* whole-seed paste above the reply leaves `# Brief`,
`Hi Adam,` and `# Current commitments`, all under the floors and each in
its own paragraph so no run can anchor them, occupying the four-line
opening window). `evals/adam-writing-style/README.md:176-180` states exactly
this limit. Nit N-a below.

**The 21-shape battery and round 3/4's named exploits, re-measured** (19
rows; every one through `run_checks` on the real fixtures):

| exploit | head |
|---|---|
| **R3 B-1(a) round-3's own 7-line transcript, verbatim** | **ALLPASS (4/4)** ← finding 1 |
| R3 B-1(b) fenced / `>` / `~~~` / unterminated buzzwords | fails `no-avoid-list-words` (all four) |
| R3 S-1 preamble + blockquoted buzzwords | fails `no-avoid-list-words`, `opens-with-a-hedge` |
| brief B2 indented `REQ-4417` line | fails 3 of 4 |
| R4 adv B-1 four-line paste (`>` / unmarked / fenced / `<blockquote>`) | fails 3 of 4 in every container |
| R4 adv B-2 72-wrapped genuine bio | **ALLPASS** (correct) |
| R4 adv S-1 `<span title=…>` / `<img alt=…>` / `<!-- … -->` | ban fires on all three |
| R4 code 3(a) mid-line `I<leverage synergy robust>` | ban fires |
| R4 S-5 reference blockquoted / fenced / stray ``` | ALLPASS (correct) |
| R4 S-7 `9 minutes, down from 26` | ALLPASS (correct) |
| R4 S-8 `Adam has led … I/O` | fails `appraisal-is-first-person` (correct) |
| R4 N-1 `March\n2027` across a wrap | ALLPASS (correct) |

**The sentence-grain cases the task asked for, added:**

| case | recruiter-reply | proposal-bio | self-appraisal |
|---|---|---|---|
| paste re-broken at **sentence boundaries** (bare) | fails hedge + `cites` | fails third-person + `cites` | fails first-person + `cites` |
| the same under a filler | fails `cites` | fails `cites` | fails `cites` |
| seed sentences **reordered whole** (order shuffled) | fails hedge + `cites` | fails third-person + `cites` | fails first-person + `cites` |
| seed sentences **spliced** (middle clause dropped) | fails hedge + `cites` | fails third-person + `cites` | fails first-person + `cites` |
| **stitched fragments** (fragments < 24 chars, interleaved), bare | fails hedge only | fails third-person only | fails first-person only |
| **stitched fragments + the suite's own register filler** | **ALLPASS** | **ALLPASS** | **ALLPASS** |
| the same, `>`-quoted, and via a `--workspace` surface | **ALLPASS** | **ALLPASS** | **ALLPASS** |

Also measured clean on head, 15 shapes × 3 fixtures: the committed
reference presented plain, blockquoted, fenced, in `<blockquote>` and as a
Markdown table — **ALL-PASS in every one**; and a genuine reply preceded by
`---`, `***`, `<hr>`, a heading, or wrapped as a bullet list, a numbered
list, a table, CRLF, or with a trailing HTML comment — **ALL-PASS in all
10**.

---

## 6. The "stitched fragments" shape — where it is recorded, what it is, and whether anything floors it

**Where the worker recorded it.** Three places, all with the same sentence,
and none of them calls it unresolved:

- `harness/scorers/objective.py:915-918` (the `strip_seed_material`
  docstring): "A sentence the agent COMPOSED from the seed's phrases — two
  seed runs joined by **its own** connective, a seed clause inside its own
  sentence — carries a word ordering the seed does not have and is the
  agent's writing, so it stays and is scored."
- `evals/adam-writing-style/README.md:166-169`, under "**What it does not
  do**": the same wording, prefaced by "**That is the point, not a leak.**"
- `evals/adam-writing-style/proposal-bio/fixture.yaml:33-35` and
  `self-appraisal-opening/fixture.yaml:28-30`: the same sentence again.
- Commit `7dbb4e8`'s message: "Consequences that are the point rather than
  side effects: a sentence the agent composed out of seed phrases carries a
  word order the seed does not have and stays."

**Not recorded anywhere:** `recruiter-reply/fixture.yaml` — the one fixture
where it reaches a full ALL-PASS — carries no such note; a
`grep -rniE 'unfixable|not closed|still passes|remains open|cannot close'`
over `evals/`, `harness/` and `test/` finds nothing about it; and no test
carries the round-3 transcript. What `recruiter-reply/fixture.yaml:147-152`
does say about `cites-both-facts` is *"a line the agent merely echoed is not
the agent being specific. A SENTENCE the agent built around the ID is, and
still counts — the sentence is not one of her lines."* For the shape below
that reads as coverage and is not.

**What the shape is, exactly, measured.** Two distinct things share the
name, and they are not equally interesting:

1. **The degenerate one** — fragments each under 24 characters, interleaved
   into new sentences. It ALL-PASSES all three fixtures with a one-sentence
   register filler (table above), residue = 100 % of the material. But the
   residue reads as word salad (`# Brief Dana Whitcombe's am not taking the
   role. recruits in a small commitments are in reply itself…`); no model
   emits it, and a pairwise judge would rank it last. **A curiosity, not a
   threat.**
2. **The one that matters — clause splicing, which is what round 3's own
   transcript is.** Its middle sentence is
   `I am filling a Staff Platform Engineer role for a client of ours —
   requisition REQ-4417 — and the client would like to start interviews
   inside the next two weeks.` Measured: **not one word in it is absent
   from the seed**; both halves are independently seed material
   (`_is_seed_material(…, 24, 12)` True for each); the whole is not a
   contiguous run, so it is kept and it supplies `REQ-4417`. Across the
   whole transcript only **two** words (`note`, `wrote`) appear nowhere in
   the seed, and 20 of its 58 word-4-grams are novel — all 20 inside the
   `On Tue, 1 Sep 2026, Dana Whitcombe wrote:` attribution line, which is
   what every mail client writes for you.

**Is the record honest?** *Partly.* It is accurate about the mechanism and
it is in four places. Three things are missing, and they are the load-bearing
three:

- The prose describes a **narrower** rule than the code implements. "Two
  seed runs joined by **its own** connective" does not describe the
  sentence above, whose connective (`— and`) is the seed's too and which
  contains no word of the agent's at all. A reader who checks the code
  against the docstring finds the docstring's rule; the code's rule is "the
  whole key is not a contiguous run", which is strictly wider.
- The **consequence** is unstated. Nowhere does any document say that a
  reply of this shape passes every recruiter-reply check including
  `cites-both-facts`, which all three fixture headers call the thing under
  test.
- It is **not framed as unresolved.** "That is the point, not a leak" is
  the opposite framing, and the fixture where it bites carries neither the
  note nor a correction to the comment that contradicts it.

**Does the judge or another check floor it?** **No — nothing does today.**
No other objective check fails (all four pass). The pairwise judge would in
principle rank it last — it is the recruiter's own email quoted back, and
rubric dimension (2) scores register — but `run_eval.py:766-781` refuses a
`mode: pairwise` fixture outright (#97), so the judge column has never
scored anything on any of these three fixtures, and the objective column is
the only instrument that runs. BRIEF.md's "no quoting of her email or my
notes" is prose to the agent, not a check.

**"Unfixable" is stronger than what is measured.** A proportion floor — the
direction round-4 adv B-1 suggested — separates them cleanly. Seed-word
coverage by runs of ≥ 4 words, measured on head:

| sentence | coverage |
|---|---|
| round-3 sentence 1 | 16/22 = **73 %** |
| round-3 sentence 2 | 29/29 = **100 %** |
| round-3 sentence 3 | 7/10 = **70 %** |
| the suite's own genuine "own words" draft (`run_tests.py:4877-4884`) | 6/35 = **17 %** |
| in-voice reference, its three long sentences | **0 %, 37 %, 0 %** |

Any floor between 40 % and 70 % keeps every genuine sentence and drops all
three of round 3's. I file that as a direction, not a demand — but it means
the honest record would say "not closed", not "unfixable".

---

## 7. Rule 19 — the harness change is opt-in per check

**By reading the code:** `run_checks` injects `seed` into a
`transcript_matches` call only inside `if strip_seed:`
(`objective.py:1840-1841`), and `strip_seed` is popped from `kwargs` and
type-checked first (`:1833-1839`). `transcript_matches` runs the pre-pass
only `if seed is not None` (`objective.py:1123-1124`). YAML-parsed across
all 9 `fixture.yaml`s: **exactly 10 `strip_seed` keys, all `True`, all on
the three #81 fixtures** (4/4, 3/3, 3/3); `post-failure-comment` 0/12,
`rename-pdfs` 0/8, `windows-elevation-from-wsl` 0/7, `workflow-path-audit`
0/8, the other two have no checks.

**Plain `--arm objective-only`, head vs `$SP/mainx` (`8d131bd`), stdout compared byte for byte:**

| Fixture | mainx | head | stdout |
|---|---|---|---|
| `guidance-bridge-canary` | exit 2 | exit 2 | **identical** |
| `post-failure-comment` | exit 1 | exit 1 | **identical** (12 checks) |
| `propagation` | exit 2 | exit 2 | **identical** |
| `rename-pdfs` | exit 1 | exit 1 | **identical** (8 checks) |
| `windows-elevation-from-wsl` | exit 1 | exit 1 | **identical** (7 checks) |
| `workflow-path-audit` | exit 1 | exit 1 | **identical** (8 checks) |

Same six under `--arm objective-only --workspace <its own seed>` — the
workspace surface — for the three that have one: **identical**.

**Transcripts that carry seed text**, which is where a leaked pre-pass would
show: each of the six fixtures scored through `run_checks` with its own
seed's sentences as the transcript, in four shapes (verbatim, `>`-quoted,
fenced under a reply, joined onto one line) — **24 cells, head and mainx
identical in all 24**, per check.

Plus the brief's named regression, both directions:
`windows-elevation-from-wsl`'s `handoff-names-elevation-and-the-line`
scored through `run_checks` on a ```` ```powershell ```` fenced handoff and
on bare prose: **True on mainx, True on head** (and True on `f01c1e6`).

---

## 8. Seeds, prompts, references, hygiene

- `git diff --stat f01c1e6 2b1bda7 -- evals/adam-writing-style/*/seed` —
  **empty**. Seeds byte-identical; no item required otherwise.
- `git diff --stat f01c1e6 2b1bda7 -- evals/adam-writing-style/*/references`
  — **empty**. The six reference samples are unchanged.
- **The three prompts, quoted in full, `yaml.safe_load`-compared and
  byte-identical to `f01c1e6`.** None names a rule, the skill, the avoid
  list or a reference sample:
  - proposal-bio: `Write my 60-word bio for this proposal`
  - recruiter-reply: `Reply to this recruiter's cold email in my voice, declining but leaving the door open`
  - self-appraisal-opening: `Draft the opening paragraph of my self-appraisal for this quarter from these notes.`
- Nothing under any `seed/` names a rule, the skill, the avoid list, a
  register term or a reference:
  `grep -rniE 'adam-writing-style|SKILL\.md|avoid.?list|buzzword|core move|leverage|synerg|em.?dash|third person|first person|hedge|register|in-voice|generic\.md|reference'`
  over the seven seed files → **zero hits**. `fictional` appears in **no**
  file under any `seed/`.
- **All ten checks are `transcript_matches`.** Every pattern is lexical
  over prose; **no check decides code shape by regex**. The Markdown
  regexes live only in the pre-pass and no longer decide anything on their
  own — a markup misread can only fail to drop text that provenance already
  proved is the seed's, so it errs toward keeping the agent's writing.
- `git diff --stat 8d131bd 2b1bda7 -- .github/` — **empty**.
- `git log --format='%ae %ce' f01c1e6..2b1bda7` — every author and every
  committer is `4205216+Adam-S-Daniel@users.noreply.github.com`, with the
  single exception of GitHub's own `noreply@github.com` as *committer* on
  `8d131bd`, main's own merge commit.

---

## 9. New findings

### BLOCKER

**1. Round 3's own transcript — the input the brief named as B1's
acceptance criterion — still ALL-PASSES `recruiter-reply`, because step
(5)'s exemption is implemented more widely than the decision (and the
docstring) describe it: a sentence with ZERO words of the agent's own is
scored as the agent's writing and supplies `cites-both-facts`.**
`harness/scorers/objective.py:994-999` (the `seed` / `above` flags) and
`:1011-1024` (the run rule), with `:794-823` (`_is_seed_material`).

Measured through `run_checks` on the committed fixture and seed, transcript
pasted in verbatim as a string constant:

```
> On Tue, 1 Sep 2026, Dana Whitcombe wrote:
> Hi Adam, I think your background lines up well with what they are after.
> I am filling a Staff Platform Engineer role for a client of ours —
> requisition REQ-4417 — and the client would like to start interviews
> inside the next two weeks.
>
> My own note: the engagement is contracted through March 2027.
```
```
PASS no-avoid-list-words   PASS greets-the-recruiter-by-name
PASS opens-with-a-hedge    PASS cites-both-facts          ALL PASS
```

The residue is the whole transcript, unquoted and unwrapped: **nothing is
stripped**. Two words in it (`note`, `wrote`) appear nowhere in the seed.
Its middle sentence contains **no** word the seed does not have, and both
of its halves are independently seed material — it survives only because
the *whole* key is not one contiguous run.

The brief is explicit that this must close: B1's criterion is "round 3's own
seven-line transcript still ALL-PASSES unchanged" as the defect, and S4
requires "the round-3 transcript pasted in VERBATIM as a string constant"
as a test. **Neither exists:** `REPASTE_SHAPES`'s `seven-line-quote`
(`run_tests.py:4521`, `:4543-4546`) is `textwrap.wrap` of the seed's own
sentences **in order**, so it varies the line breaks and nothing else. No
test in the tree re-orders or splices seed clauses.

Why I call it a defect in the implementation and not only in the decision:
step (5) grants the exemption to "a sentence the agent composed from seed
phrases **with its own words** (two seed runs joined by **the agent's**
connective…)", and `objective.py:915-918` repeats that wording. The code
grants it to any sentence whose whole key is not a contiguous run —
including one that is 100 % the seed's words joined by the seed's own
connective. A rule that required at least one word outside the covering
runs, or a coverage floor (§6: 70-100 % for round 3's three sentences,
0-37 % for every genuine sentence measured), closes the named input while
keeping every genuine one.

**Severity.** Blocker, and a **REPEAT** — round-2 item (a), round-3 B-1(a),
round-4 adv B-1, now round 5: same defect, same severity, and the same fix
direction (match seed material below the whole-sentence grain) that round-4
adv recommended. `cites-both-facts` is what all three fixture headers call
"the skill's specificity move, which is the thing under test", and it is
satisfiable by material with no authorship. This is not a synthetic
adversarial input: it is a transcript round 3 measured from a real run.
Nothing else floors it (§6).

*Everything else B1 asked for did land* — 42 perturbation cells and 276 grid
cells are correct, and round 4's four ALL-PASSING transformations are all
closed. This is one named input, but it is the one the brief named.

### SHOULD-FIX

**2. A fence delimiter line's INFO STRING is deleted whole, so avoid-list
words parked on it switch the ban off and the reply ALL-PASSES.**
`harness/scorers/objective.py:950-951` — `payload.append("" if (only_wrapper
or _FENCE_RE.match(line) or _TABLE_RULE_RE.match(line)) else body)`.
`_FENCE_RE` (`:613`) matches the *prefix*; the whole line, info string
included, is then blanked.

Measured, `recruiter-reply`, through `run_checks`:

```
Hi Dana,

Sorry for the slow reply. REQ-4417 is not for me; my engagement runs to March 2027.

Thanks,
Adam Daniel

```we can leverage this synergy
x
```
```
→ **ALL PASS**, `no-avoid-list-words` included; `leverage` is not in the
residue. Five variants all ALL-PASS: the info string on the opening fence,
on the closing fence, on an indented fence, on `~~~~`, and a whole sentence
parked there (`I kept it free of leverage, synergy and robust, and I did not
circle back.`). Same shape ALL-PASSES `self-appraisal-opening`.

This is the exact invariant the design decision states — "nothing the agent
wrote outside a bare wrapper tag is ever removed" — and the exact argument
S1 used for attribute text: a `<span title="…">`'s attribute value is the
agent's, and so is a fence's info string, which is the agent's choice of
language label. It is **not a regression this round** (identical on
`f01c1e6`), and neither round-3 nor round-4 measured it, so it is not a
repeat of a named finding — but it is the same defect *class* as round-3
B-1(b) (blocker) and round-4 adv S-1 (should-fix), which is why I file it
at should-fix rather than nit.

*Fix, verified feasible.* Keep the text after the delimiter run as payload:

```python
fence = _FENCE_RE.match(line)
if fence:
    info = _dequote(line).strip()[len(fence.group(1)):].strip()
    payload.append(info)
else:
    payload.append("" if (only_wrapper or _TABLE_RULE_RE.match(line)) else body)
```
Measured in a scratch copy: the headline case flips to
`fails no-avoid-list-words`, the suite stays at **461, OK, exit 0**, and the
contentless column of the 276-cell grid still never ALL-PASSES.
*Test*: the five variants above, plus a ```` ```markdown ```` info string
still leaving a paste stripped.

### NITS

**N-a.** Two of 138 column-A cells still miss: an **unmarked** whole-seed
paste **above** a genuine `recruiter-reply` leaves `# Brief`, `Hi Adam,`
and `# Current commitments` — each in its own paragraph, each under both
floors, so no run can anchor them — in the four-line opening window, and
`opens-with-a-hedge` fails a genuine draft. Down from 4 of 120 in round 4,
documented at `evals/adam-writing-style/README.md:176-180`, and both
BRIEF.md files forbid the paste. Record-only.

**N-b.** Two of my 34 mutations left the suite green, i.e. two asserted
properties are unpinned (round 4 counted nine):
  - `objective.py:1122` — removing the invisible fold from
    `transcript_matches` itself is invisible to the suite, because
    `strip_seed_material` folds again at `:937` and every #81 check sets
    `strip_seed`. The only other `transcript_matches` in the repo
    (`windows-elevation-from-wsl`'s handoff, `must_match` only) would then
    false-*fail* on a ZWSP; measured, the fold does protect it today. One
    test on that fixture would pin it.
  - `objective.py:789` — `_seed_index`'s docstring claims "the files are
    kept APART, so a run can never span a boundary that was never adjacent
    to begin with"; joining every file into one whole leaves the suite
    green. Narrow (an agent's sentence would have to straddle the junction
    of two seed files), but it is an asserted invariant with no test.

**N-c.** `_strip_wrapper` still removes a leading `>` from prose that uses
it as a comparison ("> 60 words is the cap" → "60 words is the cap"),
measured. No pattern is affected; round-4 N-c, still a one-line docstring
note.

**N-d.** The brief's B2 asked that "the certifications line survives in the
residue"; it does not (`Certifications: AWS Solutions Architect –
Professional, CISSP.` is a whole seed sentence and is dropped, on head and
on `f01c1e6`). The worker **deviated deliberately and said so** in three
places — `README.md:171-175`, `objective.py:928-934`, and
`run_tests.py:4483-4491`'s own comment — and pinned the weaker claim that
survives (`test_a_certifications_line_costs_the_bio_nothing`: the bio
ALL-PASSES anyway, and a *composed* certifications sentence is kept). I
measured the cost as stated: nothing any check looks for is only in that
line. Recording it because it is a deviation from a written acceptance
criterion, not because I think it is wrong.

**N-e.** `run_eval.py` still refuses every `mode: pairwise` fixture (#97),
so the objective column of all three fixtures has never been scored against
a real transcript end to end, and the judge column has never run at all.
Pre-existing, tracked, and the reason finding 1 has no backstop.

---

## 10. What I could not check

- **Anything about a real judge.** No network, real `claude` off limits, so
  every judge measurement is structural (`_normalize_draft_text`,
  `blind_order`, the built prompt) against the committed references.
  Whether a real model *would* rank finding 1's transcript last is
  unmeasured; that it is not scored at all today is measured.
- **CI on `2b1bda7`.** Not queried — offline review, nothing posted.
- **Line numbers** are from `$SP/rev131e-code` as exported; the tree was
  never modified, so they are stable.

## 11. Tree integrity and processes

`find . -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum | md5sum`:

| Tree | before | after |
|---|---|---|
| `$SP/rev131e-code` | `64cdd6befb97bfd41df73deb0a404d63` | **`64cdd6befb97bfd41df73deb0a404d63`** |
| `$SP/rev131e-ref` | `48e625390db5eb0b1897783075033430` | `48e625390db5eb0b1897783075033430` |
| `$SP/mainx` | — | `af0b092455ad4fe8338146256bac6576` |

All 34 mutations, the hollowness drop-in and the fence feasibility patch ran
in same-depth throwaway copies (`$SP/r5mut`, `$SP/r5mut2`, `$SP/r5mut3`,
`$SP/r5hollow`, `$SP/r5fence`), every one deleted. `/home/user/skills-evals`:
`git status --short` empty, HEAD still `527c729`. `/home/user/agentskills`
read-only. `$SP/rev131e-adv` never entered.

Every background process I started has exited (`ps` shows none). Two
`bash` waiters remain in the container (PIDs 20197, 23508, ~4.4 h old,
polling `pgrep -f mutate2.py` and reading
`tasks/b9upr7gpp.output`) — they are **not mine**; round 4's code review
reported the same pair. They only read, so they wrote into no tree of
mine; I left them alone. Worth knowing that they blocked on *my*
`mutate2.py` because the process name matched theirs.
