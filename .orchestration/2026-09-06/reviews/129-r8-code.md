NOT CLEAN — all fifteen brief items (B1, S1a–d, S2, S3, N1–N8) are genuinely FIXED through the production entry point, but the S2 fix only ROTATED the `catalogue_seen` cap's eviction key: 498 planted entries dated today (or 500 bare strings, which the migration path dates today for free) still delete a real since-retired id and still publish a false "carries 100.0%" for a model carrying 9.09% — round-7 SF1's exact consequence, exact fixture, exact numbers, at the same should-fix severity.

# skills-evals PR #129 — round-8 scoped code review (head `384396f221d8802f0480f06ebece143a31f0ce6d`)

Scope: the fix round `a390bc9..384396f` (10 commits: a merge of `origin/main` plus one
per item). Effort: high. All work in `$SP/rev129h-code`; `/home/user/skills-evals` was
read-only throughout (`git show`/`diff`/`log`/`archive`/`merge-base` only, HEAD still
`527c729`, `git status --short` empty). `$SP/rev129h-adv` untouched (mtime `13:02:44`,
before this session began). Nothing posted to GitHub; no session, routine or reminder
created; the real `claude` CLI never invoked; no network.

**Work dirs verified this time** (round 7 had to rebuild both):

| tree | `harness/roster.py` md5 | `git show <sha>:harness/roster.py \| md5sum` |
|---|---|---|
| `$SP/rev129h-code` (head `384396f`) | `1aa5d1d19eac086bd1f0ee90e1ed3452` | `1aa5d1d19eac086bd1f0ee90e1ed3452` ✓ |
| `$SP/rev129h-ref` (`a390bc9`) | `1349ebd5706eb448081ebc6762cfe77a` | `1349ebd5706eb448081ebc6762cfe77a` ✓ |

`test/run_tests.py` in `$SP/rev129h-ref` is `c2c5e30c0cc992e18257bf9c6effbdaa` =
`git show a390bc9:test/run_tests.py`. I also built `$SP/r8ref946` (`git archive a946c9b`)
for the B1 comparison and md5-verified `roster.py`, `run_eval.py` and `roster-policy.yml`
against `git show a946c9b:<path>`.

---

## 1. Verifiers

| Command | Exit | Result |
|---|---|---|
| `python3 test/run_tests.py` | **0** | **Ran 411 tests … OK (skipped=2)** — expected 411, 2 skipped ✓ |
| `python3 test/test_propagation.py` | **0** | **Ran 164 tests … OK (skipped=1)** ✓ |
| `python3 harness/run_eval.py evals/workflow-path-audit --arm objective-only` | **1** | 8 checks, 5 fail / 3 pass — **stdout byte-identical to `origin/main`** (`diff` clean) |
| `git -C /home/user/skills-evals diff --stat a390bc9 384396f -- .github/` | 0 | **EMPTY** — the round did not touch `.github/` ✓ |

Per-check comparison against `$SP/base129h` (`git archive origin/main`, `a6c882a`): the
two JSON documents are byte-identical, so all 8 `(id, passed, detail)` triples match —
`docs-change-routes-correctly` F, `source-change-routes-correctly` F,
`lockfile-change-routes-to-installers` F,
`prose-change-runs-nothing-but-the-required-check` F,
`required-check-always-fires-and-gates-internally` F, `workflows-still-parse` T,
`event-only-workflows-unfiltered` T, `ruleset-unchanged` T.

**Count arithmetic checks out.** `a390bc9` = 328, `origin/main` = 217,
`git merge-base origin/main a390bc9` (`af06d0f`) = 157. 328 + (217 − 157) = 388 post-merge,
+ 23 new tests in `TestIssue67Review7` = **411**. Exactly the observed number, so the merge
lost no class from either side.

Re-run after the whole mutation battery: identical numbers, and the 87-file manifest is
byte-identical to the pre-work one (§8).

---

## 2. B1 — the design as implemented, and every scenario through `main()`

**The design, in two sentences from the code** (`harness/roster.py:261-323`,
`_usage_alias_map`, called at `:1155-1157`):

> A live catalogue id's usage target comes from **`seat_aliases`** — the catalogue-only
> map — so two ids the seat map keeps distinct always have distinct targets and therefore
> disjoint numerators; only ids that are *not* in the catalogue (a departed previous arm,
> a `catalogue_seen` history entry, a census key naming neither) are folded by the
> **wide** map `alias_map(api_ids + counts + previous_arms + catalogue_seen)`.
> The single exception is rule (3): a bare alias that is **not itself** in the catalogue
> while dated snapshots of it are, is claimed by the **newest** live snapshot (last write
> wins over `live_order`, the run's own weakest-and-oldest-first capability order), which
> is the same model that holds the seat — so a census key is attributed to at most one
> live id and the map stays a function.

All scenarios driven through `harness/roster.py`'s real CLI with files on disk, exactly
as `.github/workflows/eval.yml:367-374` invokes it (`--models`/`--policy`/`--census`/
`--previous`/`--out`), on the container's real clock (`2026-09-05T13:07Z`, `2026-W36`).
Scripts in `$SP/r8work/`, outside every reviewed tree.

### 2a. Round 6's production case — still 1.96%, not 97.1%

Fixture (`$SP/r8work/sA.py`): catalogue `claude-haiku-4-5`, `claude-sonnet-5`,
`claude-sonnet-5-1`, `claude-opus-5`; `previous.arms` = `[claude-sonnet-4-9-20260101,
claude-sonnet-5]` (the first departed from the API); census W36 =
`{claude-sonnet-4-9: 5000, claude-sonnet-5: 100, claude-haiku-4-5: 3}` (5000 turns under
the *undated* alias beside 103 ranked turns).

| tree | `claude-sonnet-5`'s published sentence |
|---|---|
| **head `384396f`** | `below the 2% exit bar for the last 8 weeks (**1.96%** of rankable census usage)` — **not seated** |
| `a390bc9` | identical — `1.96%`, not seated |
| `a946c9b` | `carries **97.1%** … (at or above the 10% entry bar)` — **seated as a fourth arm** |

Round-6 B1's outcome is intact and unmoved by this round's rewrite. ✓

### 2b. The round-7 two-snapshot cases

Fixture (`$SP/r8work/sB2.py`): catalogue `claude-haiku-4-5`, `claude-sonnet-5`,
`claude-opus-5-20260101`, `claude-opus-5-20260601`; **no bare-alias census key**; census
`{claude-opus-5-20260601: 1000×4 weeks, claude-opus-5-20260101: 10×4}` — 4000 of 4040
enter-window turns on the newer snapshot, 40 (0.99%) on the older.

| scenario | head `384396f` | `a390bc9` (the defect) | `a946c9b` |
|---|---|---|---|
| bare alias in **`previous.arms`** only | `-20260601` **99.0%**, seated; `-20260101` NOT an arm, is the judge | **BOTH** at `carries 100.0%` | `-20260601` **99.0%** only |
| bare alias in **`previous.catalogue_seen`** only | `-20260601` **99.0%**; `-20260101` NOT an arm | **BOTH** at `100.0%` | **99.0%** only |
| **organic chain**, run 2 (run 1's catalogue lists the bare alias, run 1's own published roster is run 2's `previous`) | `-20260601` **99.0%**; `-20260101` NOT an arm | **BOTH** at `100.0%` | **99.0%** only |
| (run 1 of that chain, for reference) | `claude-opus-5` `carries 100.0%` — correct, it is the only opus in the catalogue | same | same |

**Head reproduces `a946c9b`'s outcome exactly** — the newer snapshot carries the usage at
99.0%, the older is not seated. No DESIGN.md deviation was needed and none was taken;
`_usage_alias_map`'s docstring rule (3) is the mechanism. "Never both at 100.0%" holds in
all three. ✓

I also ran the *variant where the bare alias IS a census key* (`$SP/r8work/sB.py`): head
gives `-20260601` 99.0% / `-20260101` 0.99%, while **`a946c9b` publishes both at 100.0%**
there — so on that shape head is strictly better than the round-6 head as well.

Rule (3) is **order-independent** (`$SP/r8work/sOrder.py`): with all usage on the bare
alias, swapping the two snapshots' order in `models.json` and equalising their
`created_at` still yields `carrier=['claude-opus-5-20260601']` in all four combinations.

### 2c. The zero-usage previous arm — retired at 0.0%

Previous arm `claude-opus-5-20260101` with **literally no census turns**, bare alias in
`previous.catalogue_seen`:

| tree | outcome |
|---|---|
| **head** | `RETIRED claude-opus-5-20260101 \| below the 2% exit bar for the last 8 weeks (**0.0%** of rankable census usage)` ✓ |
| `a390bc9` | **kept**, `carries 100.0%`; `retired_since_last` empty |
| `a946c9b` | retired at `0.0%` |

### 2d. The resulting roster through `run_eval.select_models`

Driven through `harness/run_eval.py::select_models` on the `latest.json` each run actually
published (`$SP/r8work/sD.py`):

| scenario | head `384396f` | `a390bc9` |
|---|---|---|
| all four B1 scenarios | `arms=[haiku-4-5, sonnet-5, opus-5-20260601]`, `judge=claude-opus-5-20260101`, `is_arm=False` → **`('claude-haiku-4-5', 'claude-opus-5-20260101', None)`** | `arms=[…, -20260101, -20260601]`, `judge.is_arm=True` → **`(None, None, 'the model roster … names a judge that is also an arm …')`** |

Every unpinned fixture runs again. ✓

### 2e. The property test

`TestIssue67Review7.test_usage_numerators_are_disjoint_across_distinct_seat_ids`
(`test/run_tests.py:7199`).

- **Drives `compute_roster`.** Four catalogues via `self._compute(...)` →
  `roster.compute_roster(models_doc, census_doc, policy, previous, now)` with a test-only
  0% entry bar so every available model publishes its measured share in words; it then
  parses the shares out of the published reasons and asserts they sum ≤ 100 + half a
  last-digit unit per arm. No hand-built alias map anywhere in it.
- **Red on `a390bc9`**: head's `test/run_tests.py` dropped into a copy of `$SP/rev129h-ref`
  → both subtests (`catalogue=0`, `catalogue=1`) **FAIL**.
- **Mutation** (restore the single wide-map target, `aliases = alias_map(api_ids +
  list(counts) + previous_arms + list(catalogue_seen))`) → **RED**, 7 failures across
  6 tests, this one included (catalogue 0's two snapshots report 100.0% each — 200% of one
  denominator).

**B1 verdict: FIXED** — `harness/roster.py:261-323` (`_usage_alias_map`), wired at
`:1155-1157` after `available` is ordered.

---

## 3. Per-item verdicts

"Hollow?" = head's own `test/run_tests.py` dropped into a copy of `$SP/rev129h-ref`
(`a390bc9`) and run: **19 of the 23 new tests are RED there** (18 failures + 1 error);
5 pass, all five by design — see the note under S1. Every mutation was applied to a
**scratch copy** (`$SP/r8mut*`, deleted afterwards), the **whole 411-test suite** run, and
the copy discarded; `$SP/rev129h-code` itself was never modified (§8).

| Item | Verdict | Fix (file:line) | Test (file:line) | Red on `a390bc9`? | Mutation → red |
|---|---|---|---|---|---|
| **B1** two live snapshots merged | **FIXED** | `roster.py:261-323`, `:1155-1157` | `:7093`, `:7106`, `:7118`, `:7140`, `:7162`, `:7199` | **RED** (all 6) | `B1_single_wide_map` → **RED**, 7 red incl. all six |
| **S1a** future-`last_seen` clamp | **FIXED** (floor added) | `roster.py:866-867` | `:7391` | passes (floor for correct code) | `S1a_no_future_clamp` (`= parsed.strftime(...)`) → **RED** 1; round-7's literal `= entry["last_seen"]` → **RED** 2 |
| **S1b** unparseable-`last_seen` skip | **FIXED** (floor added) | `roster.py:857-860` | `:7412` | passes | round-7's `parse_ts(...) or now` → **RED** 1; the worker's own named mutation (drop the `continue`) → **RED** 1 |
| **S1c** id shape check on the dict shape | **FIXED** (floor added) | `roster.py:853` | `:7437` | passes | `S1c_dict_id_unchecked` → **RED** 1 |
| **S1d** cap's live-id exemption | **FIXED** (floor added) | `roster.py:926`, `:942-943` | `:7464` | passes | round-7's literal `kept = sorted(survivors)[:CAP]` → **RED 3** (green at `a390bc9`); `live = []` → **RED 6**; `newest-first, no live split` → **RED 1** (this test alone) |
| **S2** `catalogue_seen` cap order + policy text | **FIXED as specified** (see finding 1) | `roster.py:940-943`; `evals/roster-policy.yml:138-146` | `:7270`, `:7289`, `:7311` | **RED** (all 3) | `S2_cap_by_id_sort` → **RED** 2; `S2_policy_says_id_sort` → **RED** 1 |
| **S3** previous-arms cap keeps real retirements | **FIXED for the census-named case; PARTIAL for a zero-usage arm** (finding 3) | `roster.py:779-794` | `:7329`, `:7355` | `:7329` **RED**; `:7355` passes (bound unchanged) | `S3_arms_cap_by_id_sort` → **RED** 1 |
| **N1** `last_seen` republished raw | **FIXED** (see finding 2 for a residual) | `roster.py:866-867` | `:7490` | **RED** | `N1_raw_last_seen` → **RED** 1 |
| **N2** `census_at` not converted to UTC | **FIXED** | `roster.py:1224-1226` | `:7511` | **RED** | `N2_no_astimezone` → **RED** 1 |
| **N3** `:.6g` fallback vs the bar | **FIXED** | `roster.py:452-471` | `:7524` | **RED** | `N3_unchecked_6g` → **RED** 1 |
| **N4** `RecursionError` traceback | **FIXED** | `roster.py:171-182` | `:7556` | **ERROR** (the RecursionError propagates) | `N4_narrow_except` → **RED** 1 |
| **N5** "for ONE migration run" | **FIXED** | `roster.py:807-820` | `:7592` | **RED** | `N5_one_migration_run` → **RED** 1 |
| **N6** ageing does not undo a retirement | **FIXED** | `DESIGN.md:383-391`; `roster.py:895-903` | `:7601` | **RED** | `N6_design_text` → **RED** 1; `N6_docstring` → **RED** 1 |
| **N7** module docstring: no env, no stray stdout | **FIXED** | `roster.py:46-55` | `:7613` | **RED** | `N7_no_env_rule` → **RED** 1 |
| **N8** dedup comment names the real bound | **FIXED** | `roster.py:726-736` | `:7626` | **RED** | `N8_no_dedup_note` → **RED** 1 |

**Every mutation I ran turned the suite red. None left it green.** Full battery:
`$SP/r8work/mutate.py` (15), `mutate2.py` (5 round-7-literal ones), `mutate_n6.py` (2).

### The four S1 defences, measured end to end

The brief's acceptance for each defence is the named mutation, not redness on `a390bc9`
— the code was already correct there, which is the whole point of a regression floor.
Round 7 measured all four mutations leaving the suite at **328/328 green**; on head each
is caught, and by exactly one new test apiece except where noted:

```
r7_clamp_literal          RED  test_a_future_dated_last_seen_is_clamped_and_still_ages_out (+ the N1 test)
r7_unparseable_or_now     RED  test_an_unparseable_last_seen_is_skipped_not_kept_forever
S1c_dict_id_unchecked     RED  test_a_hostile_id_in_the_dict_shape_is_skipped_too
r7_cap_sorted_by_id       RED  test_the_cap_never_evicts_a_live_id_even_for_lower_sorting_plants (+2)
```

The (d) test does plant ids that sort **before** the api ids (`a0000-000`…`a0000-599`,
`'a' < 'c'`) and it is the **only** test red under `cap_newest_first_no_live_split` — so it
has teeth against both the id-order and the age-order forms of the mutation.

### S2 and S3, measured end to end

**S2 acceptance (`$SP/r8work/sEvict.py`)** — catalogue `{claude-sonnet-5,
claude-haiku-4-5}`, census `{claude-opus-4-1: 1000/wk × 8 (real, since retired),
claude-sonnet-5: 100/wk × 8}`, true share 800/8800 = 9.09%:

| `previous.catalogue_seen` | head `384396f` | `a390bc9` |
|---|---|---|
| control: the real id alone | kept; `newest model in the sonnet tier` | kept; same |
| **500 `0plant-…` (low-sorting), STALE, real id seen a day ago** | **kept** ✓ (the brief's acceptance) | **evicted** → `carries 100.0%` |
| 500 plants `last_seen` = TODAY, real id 100 days old | **evicted** → `carries 100.0%` ✗ (**finding 1**) | kept |
| 500 **bare-string** plants, real id 100 days old | **evicted** → `carries 100.0%` ✗ (**finding 1**) | kept |

The policy comment (`evals/roster-policy.yml:138-146`) now says "the entries dropped are
the oldest by `last_seen` first, tie-broken by id — NOT the alphabetically-last ids", which
**does** describe the implemented order; `test_the_policy_describes_the_cap_the_code_
implements` (`:7311`) pins it and is red when the old wording returns.

**S3 acceptance (`$SP/r8work/sArms.py`)** — a real departed previous arm plus 500
`0arm-…` fillers:

| case | head | `a390bc9` |
|---|---|---|
| control, real arm alone | reported retired ✓ | ✓ |
| **+500 filler, census NAMES the real arm** | **reported retired ✓** (the brief's acceptance) | **not reported** |
| +500 filler, real arm has **zero** census turns | **not reported** ✗ (**finding 3**) | not reported |

**N3 acceptance, the brief's literal numbers** (`$SP/r8work/sN3.py`, through `main()`:
`mine = 19,999,999`, denominator exactly `1,000,000,000`, share `1.9999999`; 13 filler
models are needed because `MAX_WEEKLY_TURNS = 10⁷`):

```
head    : below the 2% exit bar for the last 8 weeks (1.9999998999999999% of rankable census usage)
a390bc9 : below the 2% exit bar for the last 8 weeks (2% of rankable census usage)
```

Renders distinguishably from the bar. ✓ (See finding 4 on the 17-digit rendering.)

**N4 acceptance, through the real CLI as a subprocess** (`$SP/r8work/n4/`, a 100 000-deep
`previous.json`):

```
head    : rc=0   stderr = 1 line: "roster: previous.json is present but unreadable (RecursionError)"   Traceback count: 0
a390bc9 : rc=1   stderr = 23 lines beginning "Traceback (most recent call last):" with the absolute roster.py path
```

### Cross-cutting checks (all clean)

- **Determinism.** The new `_usage_alias_map` iterates a `set` at step (1), so I ran the
  two-snapshot suite under `PYTHONHASHSEED` ∈ {0, 1, 42, 7919, 12345}: all five outputs
  md5-identical (`514d4243172dfc9336c8eca17c9e0c5a`).
- **No collateral regression.** 24 ordinary scenarios (2 catalogues × 6 censuses ×
  2 previous rosters), whole published roster compared field by field with `generated_at`
  and `models_api_at` dropped: **SAME=24, DIFF=0** against `a390bc9`
  (`$SP/r8work/sSweep.py`).
- **Warnings are count-only.** A `previous.json` carrying 5 hostile arm ids (newline +
  `::error::`, 500 chars, `../../etc/passwd`, NUL, `${{ secrets.GITHUB_TOKEN }}`), the same
  5 as `catalogue_seen` ids with `\r\n`-wrapped dates, a `"garbage"` and a `9999-12-31`
  `last_seen`, plus hostile census keys and `1e308` cells, through `main()`: rc=0, three
  count-only warnings, and **none** of `pwned`, `::error::`, `secrets.GITHUB_TOKEN`,
  `etc/passwd`, `garbage`, `9999-12-31`, `\r`, `\n` appears in stdout **or** in the
  published `latest.json`. `census_at` published `2026-09-02T19:00:00Z` for a
  `+05:00` input (N2 working), `catalogue_seen` entries all `2026-09-05` (N1 working,
  future value clamped).

---

## 4. The worker's own flags — S1 (`11b741c`) and N3 (`11d5760`)

I do not have the worker's closing message, so I read both commits' messages and diffs.

### S1 — `11b741c` "test: a regression floor for four undefended catalogue_seen checks"

**What it flags**, in its own last paragraph:

> "Unlike the other items in this round these are floors for code that is already correct,
> so they are green before the change as well as after it."

That is a declared **deviation from the brief's "red first" rule** ("a failing test per
item that FAILS on `a390bc9`"). The same sentence is repeated in the test file as a
block comment at `test/run_tests.py:7377-7381`, so it is disclosed in the code as well as
in the commit.

**My ruling: the flag is right, and raising it was the correct call.** S1 asked for
regression floors under four *existing, correct* defences. A test that pins correct code
cannot fail on the commit where the code is already correct; demanding redness on
`a390bc9` would only be satisfiable by a test that was really pinning something else. The
brief's own S1 text says so implicitly — it specifies the evidence as "red under the
**named mutation**", and names all four mutations. I verified each of those four named
mutations against the *full* 411-test suite and each is red, caught by its own new test
(and by `test_the_cap_never_evicts_a_live_id_even_for_lower_sorting_plants` alone for the
subtlest form of (d)). Round 7 measured all four leaving the suite at 328 green, so the
floors are new and load-bearing. The commit body also lists the four mutations and their
consequences accurately — I reproduced each. No overclaim anywhere in it.

One detail the flag does **not** mention and I checked: (d)'s plants must sort *before*
the api ids or the test is inert. They do (`a0000-*` vs `claude-*`), and the test is the
sole detector of the age-ordered form of the mutation.

### N3 — `11d5760` "roster: check _format_share's fallback against the bar too"

The commit message flags nothing explicitly; the flag must be about a **deviation from the
brief's prescribed test input**. The brief said "Test through `compute_roster`
(mine=19,999,999 of 1,000,000,000)". The shipped test
(`test/run_tests.py:7524`) uses **7,999,999 of 400,000,000** = 1.99999975% and says so.

**My ruling: the deviation is right, and it does not weaken the test.** `MAX_WEEKLY_TURNS
= 10⁷` (`roster.py:628`), so a 1,000,000,000 denominator over an 8-week window needs
≥ 100 full cells, i.e. **13 ranked, attributable models** — a fixture more than twice the
canned catalogue's size, built solely to hit a round number. Both pairs exhibit the
identical defect: `f"{1.9999999:.6g}"` and `f"{1.99999975:.6g}"` are **both** exactly
`"2"`. I nonetheless built the brief's literal 13-model case and drove it through
`main()` with files on disk (§3, N3 acceptance) — head renders
`1.9999998999999999%`, `a390bc9` renders `2%`. So the brief's own acceptance criterion is
met on head even though the shipped test uses a cheaper equivalent.

Two things about the N3 diff I checked that the worker did not flag, and both are fine:
`"17g"` now appears **both** as the last rung of the checked ladder and as the unchecked
`return` at `:471`, which makes that `return` unreachable for any `value` that is neither
`0.0` nor exactly equal to `bar` (`:.17g` round-trips, so `float(text) == value`); and
`under=False` still short-circuits to `:.1f` at `:459`, so nothing on the "at or above"
side moved. See finding 4 for the one cosmetic consequence.

---

## 5. `.github/workflows/eval.yml`

`git -C /home/user/skills-evals diff --stat a390bc9 384396f -- .github/` → **empty**;
`git diff a390bc9 384396f -- .github/workflows/eval.yml` → **0 bytes**. The round's
diff is `DESIGN.md`, `README.md`, `evals/roster-policy.yml`, `harness/roster.py`,
`test/run_tests.py`, plus the files the `origin/main` merge brought in
(`evals/rename-pdfs/*`, `harness/scorers/objective.py`). The guardrail holds. ✓

N7 was handled the only way it could be without touching the file: the *rule* is written
into `roster.py`'s module docstring (`:46-55`) and pinned by
`test_the_module_docstring_forbids_the_environment_and_stray_stdout` (`:7613`), which also
asserts `os.environ` appears nowhere in the module body — I confirmed the module never
imports `os` at all.

---

## 6. No model id hard-coded outside fixtures

`TestIssue67.test_no_model_ids_are_hardcoded_outside_fixtures` (`test/run_tests.py:2192`)
is **green** on head and **still has teeth**. Planted into a scratch copy, one at a time,
each restored:

| planted line | into | result |
|---|---|---|
| `# planted claude-opus-4-8 for the guard` | `harness/roster.py` | **FAILED (failures=1)** |
| `# planted claude-sonnet-5-1 for the guard` | `evals/roster-policy.yml` | **FAILED (failures=1)** |

The guard's own self-check (`assertRegex` over four id shapes) is intact, and its scan list
still covers all seven non-test files including `.github/workflows/eval.yml`.

---

## 7. New findings

Four new items. Two of them I judge **REPEATS** and say so explicitly, because this is the
last round of budget after this one.

### should-fix

**F1 — the `catalogue_seen` cap's new age order is bypassed by dating the plants today, so
500 planted entries still delete genuine history and still publish a false "carries
100.0%". `harness/roster.py:940-943`. REPEAT of round-7 SF1 at the SAME severity
(same consequence, same fixture, same numbers); different mechanism.**

```python
    historical = sorted(i for i in survivors if i not in api_id_set)
    historical.sort(key=lambda i: parse_ts(survivors[i]) or now, reverse=True)
    room = max(0, CATALOGUE_SEEN_CAP - len(live))
    kept = live + historical[:room]        # newest-first head — but the planter picks the dates
```

The planter controls `last_seen`. Future values are clamped to *today* (`:866`), and
today is `>=` any genuine historical entry's date by construction — a since-retired model's
`last_seen` is the last date a run actually saw it in the API, necessarily in the past.
So the eviction key the fix chose is a key the attacker maxes out for free. Worse, the
**bare-string migration path** (`:848-851`) stamps `last_seen = today` on every bare
string, so the cheapest possible plant — a flat list of ids — is automatically dated
optimally with no effort at all.

Measured end to end through the CLI (`$SP/r8work/sEvict.py`), the *identical* fixture and
the *identical* numbers round 7 used for SF1:

```
CONTROL (history holds only the real since-retired id)
  n_seen=3    real id kept? True
  arm claude-sonnet-5 | newest model in the sonnet tier, 216 days old (past the 7-day cooling-off)

ATTACK A (+500 plants, last_seen = TODAY; real id last_seen = 100 days ago)
  stderr: roster: catalogue_seen: dropped 3 entry/entries past the 500-entry cap
  n_seen=500  real id kept? FALSE
  arm claude-sonnet-5 | carries 100.0% of rankable census usage over the last 4 weeks
                        (at or above the 10% entry bar)     <-- true share is 800/8800 = 9.09%

ATTACK B (+500 BARE-STRING plants — the migration path dates them today for me)
  stderr: roster: previous roster: migrated 500 `catalogue_seen` entry/entries from the bare-string shape
          roster: catalogue_seen: dropped 3 entry/entries past the 500-entry cap
  n_seen=500  real id kept? FALSE      ... same false 100.0%
```

Threshold measured: **498** plants suffice against a 2-model catalogue
(`room = 500 − len(live)`); ~490 against today's real catalogue. The loss is permanent —
once evicted the id is gone from the next run's `previous.json` too, so reverting the plant
does not restore it (the same "ageing out is not a repair" property N6 just wrote down for
retirements, applying here to history itself, and nothing says so).

What the fix *did* close is real and I want to be exact about it: the low-sorting-stale
attack now fails on head and succeeds on `a390bc9`, and the reverse holds for the
today-dated one. The key rotated; the primitive did not.

**Repeat determination.** Round-7 SF1's headline named the mechanism ("evicts by
ALPHABETICAL id") and its measured impact was *verbatim* what I measured above — "real
since-retired id kept? FALSE … carries 100.0% … true share is 800/8800 = 9.09%". At the
level round 7 stated the impact, and at round 7's severity (should-fix), **this is the same
finding, still open.**

**In fairness to the worker, this is at least as much a brief gap.** The brief's S2
prescribed this exact remedy in these exact words — "Evict the OLDEST by `last_seen` (keep
newest first; tie-break by id)" — and named exactly two acceptance tests, "a recent
historical entry outlives 500 stale ones" and "500 plants sorting before the real history
do not evict it". **Both pass.** The worker implemented what it was told, documented it
accurately, and pinned it. Nothing in the brief asked about plants dated today.

*Candidate fix, measured.* Order the historical slice by **relevance** first — keep ids the
census names ahead of ids only the previous roster asserts — which is the identical shape
`_clean_previous_arms` already implements for its own cap at `:779-794`, so the idea is
already in the file and the two caps would agree. Probed on a scratch copy (a two-line
sort plus threading `counts.keys()` through, as `_clean_previous_arms` does): **all four
attack variants blocked** (real id kept in every one) and the suite stays **411 green**.
The asymmetry as shipped — S3's cap sorts by relevance, S2's by a value the planter
controls, against the same attack — is the part that reads as unfinished.

### nits

**F2 — `catalogue_seen[].last_seen` is rendered from the LOCAL wall clock of an
offset-aware timestamp, not UTC: the defect N2 fixed for `census_at`, in the sibling commit
one before it. `harness/roster.py:866-867`.** New site, not a repeat of a specific
round-6/7 finding — but the third consecutive appearance of this class (round 6 N8 raw
`census_at` → round 7 N1 raw `last_seen` + N2 `census_at` timezone → this).

```python
by_id[entry["id"]] = (today if parsed > now else parsed.strftime("%Y-%m-%d"))
```

`parse_ts` preserves the offset (`harness/timeweeks.py:34`), so `strftime("%Y-%m-%d")`
prints the local date. Measured through `main()` (`$SP/r8work/sN1tz.py`):

```
in "2026-09-01T23:00:00-08:00"  (= 2026-09-02T07:00Z)  -> published last_seen "2026-09-01"   one day early
in "2026-09-02T01:00:00+05:00"  (= 2026-09-01T20:00Z)  -> published last_seen "2026-09-02"   one day late
```

Cost is one day on the 180-day age window and on F1's newest-first cap order. Needs a
hand-written or third-party `previous.json` — which is exactly the input class this
function exists for. One word, the same word `:1225` uses:
`parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")`.

**F3 — the previous-arms cap still omits a REAL retirement when the census does not name
the departed arm. `harness/roster.py:779-794`. REPEAT of round-7 nit N-5 at the same (nit)
severity, half-fixed.** Measured (`$SP/r8work/sArms.py`): a real previous arm that has left
the Models API and has **zero** census turns, beside 500 `0arm-…` fillers, is absent from
`retired_since_last` (`REAL reported retired=False`), against `True` on the unpadded
control. `_relevant` (`:783-788`) admits an id only if the catalogue lists it or the census
names it (either spelling), which by construction cannot cover an arm with no usage — the
precise case the S3 test at `:7329` avoids by giving the arm 8,000 turns. The brief offered
**two** remedies and the worker took the one that leaves this open; the other — "compute the
retirement report before capping" — closes it. Round 7 flagged N-5 "rather than counted
against the worker" because the brief had prescribed the alphabetical head; the same
allowance applies here.

**F4 — `:.17g` publishes 17 digits of float noise where `repr` would publish the input.
`harness/roster.py:452`, `:471`.** The brief's own N3 case renders
`(1.9999998999999999% of rankable census usage)` for a share of `1.9999999`. `repr(value)`
is the *shortest* round-tripping decimal form — `'1.9999999'` — so it satisfies
`float(text) != bar` just as reliably while reading like a number. Reachable only inside a
~5 × 10⁻⁷ window around a bar, so cosmetic; non-blocking, and the current code is correct.

**F5 — two cosmetic PEP 8 slips, nothing in the repo catches them.** One blank line where
two belong between `_usage_alias_map` and `_is_attributable` (`roster.py:323-325`), and the
continuation of the `_clean_previous_arms` call is one column short of its opening paren
(`roster.py:1109-1110`). There is no linter config in the tree (no `ruff`/`flake8`/
`pyproject`), so neither is caught by anything. Purely cosmetic.

### Explicitly checked and clean

- No warning echoes a hostile value; every new one names a count (§3 cross-cutting).
- `catalogue_seen` stays a superset of `api_ids` in every scenario, including the
  600-plant and 500-plant ones, pinned at `:7464`.
- Published output is deterministic across five `PYTHONHASHSEED` values despite
  `_usage_alias_map` iterating a set.
- `_usage_alias_map` rule (3) is independent of `models.json` order and of equal
  `created_at` values.
- 24 ordinary scenarios byte-identical to `a390bc9`; the round changed only what it
  claimed to.
- `example.com`/`example.net` appear only under `evals/` fixtures.
- No `__pycache__` left behind; every mutation ran on a scratch copy and the copy was
  deleted.

## What I could not check

- **PR #129's GitHub state and CI.** No network. Everything here is local, from
  `$SP/rev129h-code` and read-only `git` against `/home/user/skills-evals`.
- **A live workflow run.** `eval.yml` was asserted by `git diff` byte-identity only;
  I did not dispatch it and never invoked the real `claude` binary.
- **F1 against the real catalogue's size.** I measured with a 2-model catalogue, so 498
  plants suffice; a larger live catalogue needs `500 − len(live)`, still ~490 today.
- **The candidate fix for F1 as a shippable patch.** My probe threaded the census keys
  through a module global for expedience; a real fix would add a `count_keys` parameter to
  `_update_catalogue_seen`, exactly as `_clean_previous_arms` already has.

---

## 8. Tree integrity

`find . -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum | md5sum`,
run in `$SP/rev129h-code`:

| | value |
|---|---|
| **before** any work | `2aad1af619af49f4a721d1bb38cbd8cc` (87 files) |
| **after** everything | `2aad1af619af49f4a721d1bb38cbd8cc` (87 files) |

The 87-line per-file manifests `diff` clean, and `diff -r --brief` against a pristine
pre-work copy reports nothing. **No mutation was ever applied inside `$SP/rev129h-code`** —
all 22 went to throwaway copies (`$SP/r8mut`, `r8mut2`, `r8mut6`, `r8fix`, `r8guard`), each
deleted afterwards. `/home/user/skills-evals` is unmodified (`git status --short` empty,
HEAD still `527c729`); `$SP/rev129h-adv` was never opened or written. No background process
is running (`ps -eo pid,etimes,cmd` clean). Scratch inputs and drivers remain under
`$SP/r8work/` and `$SP/r8ref946/`, outside every reviewed tree.
