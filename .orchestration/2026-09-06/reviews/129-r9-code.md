NOT CLEAN — all eight brief items (A1, A2, F1, A3, F3, F2, F4, F5) are genuinely fixed with teeth and every named invariant holds, but the A2/F2 fix introduced one new should-fix: `_as_date` (`harness/roster.py:913`) raises an uncaught `OverflowError` on a `last_seen` of `0001-01-01T00:00:00+05:00`, so `roster.py` exits 1 with a full traceback and publishes no roster where both `384396f` and `a390bc9` complete cleanly.

# skills-evals PR #129 — round-9 scoped code review (head `5d1f00a85188d10d37f9ffc56b0c43294ebda516`)

Scope: `384396f..5d1f00a` (9 commits: 8 fix commits plus the merge of `origin/main`
at `8d131bd`, PR #134). Effort: high. All work in `$SP/rev129i-code`, `$SP/rev129i-ref`
and throwaway copies under `/tmp/r9*`; `/home/user/skills-evals` was read-only
throughout (`git show`/`diff`/`log`/`archive` only — HEAD still `527c729`,
`git status --short` empty). `$SP/rev129i-adv` was never entered or written (its only
recent writes are `__pycache__` files at 16:18 from the concurrent adversarial
session, not from me). Nothing posted to GitHub; no session, routine or reminder
created; the real `claude` CLI never invoked; no network.

**Work dirs verified:**

| tree | `harness/roster.py` md5 | `git show <sha>:harness/roster.py \| md5sum` |
|---|---|---|
| `$SP/rev129i-code` (head `5d1f00a`) | `a7bd1c68f1bbb91bdd4f71b1600c3569` | `a7bd1c68f1bbb91bdd4f71b1600c3569` ✓ |
| `$SP/rev129i-ref` (`384396f`) | `1aa5d1d19eac086bd1f0ee90e1ed3452` | `1aa5d1d19eac086bd1f0ee90e1ed3452` ✓ |
| `$SP/rev129h-ref` (`a390bc9`, third point of comparison) | `1349ebd5706eb448081ebc6762cfe77a` | `1349ebd5706eb448081ebc6762cfe77a` ✓ |

`test/run_tests.py` in `$SP/rev129i-ref` is `d4ba2711488af66bccf9d1cec0c8576f` =
`git show 384396f:test/run_tests.py`. Container clock `2026-09-05T15:56Z`,
`iso_week` = `2026-W36`, Python 3.11.

---

## 1. Verifiers

| Command | Exit | Result |
|---|---|---|
| `python3 test/run_tests.py` | **0** | **Ran 520 … OK (skipped=2)** — expected 520 / 2 skipped ✓ |
| `python3 test/test_propagation.py` | **0** | **Ran 164 … OK (skipped=1)** ✓ |
| `python3 harness/run_eval.py evals/workflow-path-audit --arm objective-only` | **1** | stdout **byte-identical** to `origin/main`'s (`$SP/base129i`, `8d131bd`) — 1644 bytes, `diff` clean ✓ |
| `git diff --stat 384396f 5d1f00a -- .github/` | 0 | **EMPTY** ✓ |

All four re-run **after** the whole mutation battery: identical numbers, and the
92-file manifest is byte-identical to the pre-work one (§9).

Files this round touched: `DESIGN.md`, `README.md`, `evals/roster-policy.yml`,
`harness/roster.py`, `test/run_tests.py`, plus what the merge brought in
(`evals/post-failure-comment/*`, `harness/scorers/objective.py`).
`scripts/refresh_models.py` and `scripts/model_usage_census.py` are **unchanged**
(`git diff --stat 384396f 5d1f00a -- scripts/` empty); the `DESIGN.md`/`README.md`
hunks are the merge's post-failure-comment graduation, not roster text. Every other
fixture under `evals/` is unchanged this round.

---

## 2. Per-item verdicts

"Red on `384396f`" = head's `test/run_tests.py` dropped into a copy of
`$SP/rev129i-ref` and `TestIssue67Review8` run there: **14 of the 21 new tests are
RED** (log `$SP/r9.hollow.log`). The 7 that pass are the five A3 regression floors
plus two already-true assertions — the brief exempts a floor for
already-correct code from the red-first half, and each of those pins its **named
mutation** instead. Every mutation was applied to a **scratch copy** under
`/tmp/r9mut/<name>`, the **whole 520-test suite** run, and the copy deleted;
`$SP/rev129i-code` was never modified (§9).

| Item | Verdict | Fix (file:line) | Pin (test/run_tests.py:line) | Red on `384396f`? | Named mutation → result |
|---|---|---|---|---|---|
| **A1** map not composed (BLOCKER) | **FIXED** | `roster.py:341-361` | `:9312`, `:9341`, `:9422`, `:9474` | **RED** (all 4) | `A1_delete_composition` → **RED 4**; `A1_round7_single_wide_map` → **RED 8** |
| **A2** `1-01-01` unreadable `last_seen` | **FIXED** (see finding 1) | `roster.py:897-913`, `:918`, `:1088-1089` | `:9546`, `:9569`, `:9593` | **RED** (all 3) | `A2_strftime_render` → **RED 5** |
| **F1** cap order steerable by the planter | **FIXED** | `roster.py:761-784`, `:1050-1090`, `:1279-1280` | `:9661`, `:9681`, `:9696` | `:9661`/`:9681` **RED**; `:9696` passes (superset already held) | `F1_age_only_order` → **RED 2**; `F1_drop_cap_count_keys_arg` → **RED 2**; `F1_no_id_presort` → **RED 1** |
| **A3** six undefended defences | **5 of 6 pinned; (6) is an equivalent mutant** (finding 2) | see A3 table §5 | `:9736`, `:9760`, `:9781`, `:9802`, `:9824` | all 5 pass (floors) | 5 of 5 → **RED**; item (6) `A2_unparseable_reads_as_now` → **GREEN** |
| **F3** report computed before the cap | **FIXED** | `roster.py:792-894` (returns `(reported, carried)`), `:1266-1268`, `:1576-1577` | `:9868`, `:9893`, `:9916` | `:9868`/`:9916` **RED**; `:9893` passes (count-only already held) | `F3_report_from_capped` → **RED 4** |
| **F2** `last_seen` rendered on the local clock | **FIXED** | `roster.py:913` | `:9944`, `:9959` | **RED** (both) | `F2_no_astimezone` → **RED 2** |
| **F4** `:.17g` float noise | **FIXED** | `roster.py:515-521` | `:9998` | **RED** | `F4_17g_last_rung` → **RED 1**; `F4_round7_unchecked_6g` → **RED 2** (keeps round-7's N3 test red too) |
| **F5** two PEP 8 slips | **FIXED** (cosmetic, no test) | `roster.py:363-364` (two blank lines), `:1266-1268` (continuation at col 55 = the open paren) | — | — | — |

**Sixteen of the seventeen mutations I ran turned the suite red.** The one exception
is A3's item (6), which I verified by hand to be an equivalent mutant rather than a
gap — finding 2.

### The invariants the brief names, verified independently

Own generator, own ownership model, driven through `compute_roster` with the
production alias map captured by wrapping `_usage_alias_map` (never rebuilt) —
`$SP/r9work/props.py`, 400 scenarios × 3 seeds:

| seed | tree | two-hop keys | (i) idempotence violations | (ii) value violations | orphaned turns | (iii) partition failures |
|---|---|---|---|---|---|---|
| 990001 | **head** | 266 | **0** | **0** | **0** | **0** |
| 990001 | `384396f` | 266 | 266 | 266 | 690,300 | 170 |
| 424242 | **head** | 298 | **0** | **0** | **0** | **0** |
| 424242 | `384396f` | 298 | 298 | 298 | 738,200 | 175 |
| 70707 | **head** | 289 | **0** | **0** | **0** | **0** |
| 70707 | `384396f` | 289 | 289 | 289 | 732,000 | 171 |

"Orphaned turns" = attributable ranked turns whose fold is no live model's usage
target *while the family has a live model* — the measurement `sum(shares) <= 100`
cannot make, and the one that names the A1 defect directly. Zero on head over 1,200
random catalogues; 2.16M turns across 516 scenarios on `384396f`.

I also reasoned the composition loop's termination out and it agrees with the
measurement: rule (1)'s keys are live ids whose targets are live bases (never
themselves keys, since a base in the catalogue is its own seat target); rule (3)
fires only when the base is **not** live, so its target is terminal. Maximum chain
length is 2 and no cycle is constructible — the `seen` guard at `:356-360` is
belt-and-braces, not load-bearing.

---

## 3. A1 — the scenario table, through the real CLI with files on disk

Every row driven through `harness/roster.py`'s real CLI the way `eval.yml:368-374`
invokes it (`--models`/`--policy`/`--census`/`--previous`/`--out`), on the
container's real clock. Scripts in `$SP/r9work/`, outside every reviewed tree.

| scenario | **head `5d1f00a`** | `384396f` (the blocker) | `a390bc9` |
|---|---|---|---|
| **organic two-run chain, run 2** (run 1's catalogue lists the bare alias; run 2's is dated-snapshot-only; census under the older dated spelling) | `claude-haiku-4-20260601` **seated, carries 94.3%** ✓ | **NOT SEATED AT ALL** | seated, 94.3% |
| **previous-arm case** (same shape, model already an arm, `claude-haiku-5` newly shipped) | **carries 94.3%**, `retired_since_last` empty ✓ | **RETIRED** — "below the 2% exit bar … (0.0% of rankable census usage)" | carries 94.3% |
| two snapshots, bare alias in `previous.arms` | `-20260601` **99.0%**; `-20260101` not seated | identical | **BOTH at 100.0%** |
| two snapshots, bare alias in `catalogue_seen` | `-20260601` **99.0%**; `-20260101` not seated | identical | **BOTH at 100.0%** |
| round-6 production case | `claude-sonnet-5` **not seated**, retired at **1.96%** | identical | identical |
| zero-usage previous arm | retired at **0.0%** | identical | identical |

Head reproduces `a390bc9`'s correct outcome on the two A1 rows and `384396f`'s
outcome on every row the items do not name. `select_models` on a
production-shaped catalogue (a cooling-off newest model leaving a tier above the
arms) gives `('claude-haiku-4-20260601', 'claude-fable-5-1', None)` with
`judge.is_arm=False` — head matches `a390bc9`; `384396f` returns the weaker
`claude-haiku-5` because the two-hop model was never seated. (On a degenerate
4-model catalogue where *every* model is seated, `select_models` correctly refuses
with the judge-is-arm error on all three trees — a property of that fixture, not
of the fix.)

### The 24-scenario sweep

2 catalogues × 6 censuses × 2 previous rosters, whole published roster compared
field by field with `generated_at` and `models_api_at` dropped, head vs `384396f`
(`$SP/r9work/sweep.py`): **SAME=24, DIFF=0**. The round changed only what it
claimed to.

---

## 4. F1 — the attack table

Catalogue `{claude-sonnet-5, claude-haiku-4-5}`; census `{claude-opus-4-1:
1000/wk × 8 (real, since retired), claude-sonnet-5: 100/wk × 8}`; true share
800/8800 = **9.09%**. `0plant-*` sorts **before** the api ids, `zplant-*` after —
the shipped test only uses the `zplant` direction, so I measured both.

| `previous.catalogue_seen` | **head** real id kept? / published | `384396f` | `a390bc9` |
|---|---|---|---|
| control: the real id alone | **kept** / newest-in-tier | kept | kept |
| 500 LOW-sorting, STALE (round-7 acceptance) | **kept** ✓ | kept | evicted → 100.0% |
| **500 LOW-sorting, dated TODAY** | **kept** ✓ | evicted → **100.0%** | evicted → 100.0% |
| **500 HIGH-sorting, dated TODAY** | **kept** ✓ | evicted → **100.0%** | kept |
| **500 LOW-sorting BARE STRINGS** (migration run) | **kept** ✓ | evicted → **100.0%** | evicted → 100.0% |
| **500 HIGH-sorting BARE STRINGS** | **kept** ✓ | evicted → **100.0%** | kept |
| 500 LOW, TODAY, real entry 169 days old | **kept** ✓ | evicted → **100.0%** | evicted → 100.0% |
| tie: all dated TODAY including the real entry | **kept** ✓ | evicted → **100.0%** | evicted → 100.0% |
| 500 LOW dated `9999-12-31` (clamps to today) | **kept** ✓ | evicted → **100.0%** | evicted → 100.0% |

`catalogue_seen` stays a **superset of the live catalogue** in all nine rows on all
three trees, including the 600-plant case where the plants are dated today AND
named by the census (`:9696`).

With a test-only 0% entry bar so the numerator is visible, head publishes
`carries 9.1%` on the today-dated and bare-string rows where both older heads
publish `carries 100.0%` — the true share, not just the absence of the false one.

The census keys are threaded as a **parameter** (`count_keys=counts.keys()` at
`roster.py:1279-1280`), never a module global: the only module-level names in
`roster.py` are the regexes, the caps, `MAX_WEEKLY_TURNS`, `_LAST_SEEN_FLOOR` and
the census codes — none holds census data. `roster-policy.yml:135-168` now
describes the implemented order ("entries the census names come first, then the
newest by `last_seen`, then the id order as a tie-break") and records that
"eviction here is PERMANENT". `test_the_policy_describes_the_cap_the_code_implements`
(`:8813`) pins **both** clauses — I mutated each independently and each turns the
suite red.

---

## 5. A3 — the mutation table

Every mutation applied to a scratch copy, **full 520-test suite** run, copy deleted.

| # | Defence | Mutation | Result | Caught by |
|---|---|---|---|---|
| 1 | rule (3)'s direction (`roster.py:334`) | `reversed(live_order)` | **RED 2** | `test_the_newest_live_snapshot_claims_the_bare_alias_not_the_oldest` (`:9736`) + the partition test |
| 2 | `named_bases` (`roster.py:771-776`) | `named_bases = set()` | **RED 1** | `test_a_departed_arm_named_by_a_dated_census_key_survives_the_cap` (`:9760`) |
| 3 | dated-arm-with-a-named-base branch (`roster.py:780-781`) | `return False` | **RED 1** | `test_a_dated_departed_arm_whose_base_the_census_names_survives` (`:9781`) |
| 4 | `api_ids=` at the call site (`roster.py:1267`) | drop the argument | **RED 1** | `test_a_live_previous_arm_survives_the_cap_and_is_held_over` (`:9802`) |
| 5 | the cap's deterministic id tie-break (`roster.py:1089`) | drop the `sorted(...)` seed | **RED 1** | `test_the_cap_breaks_a_tie_by_id_not_by_input_order` (`:9824`) |
| 6 | `or now` in the cap sort (`roster.py:1088`) | restore `or now` | **GREEN** | **nobody** — equivalent mutant, see finding 2 |
| — | `count_keys=` at the arms call site | drop the argument | **RED 3** | three round-7/8 tests |

Item (6) is an **equivalent mutant, not a gap**: after A2, `_clean_catalogue_seen`
re-renders every date through `_as_date` before `_update_catalogue_seen` runs, so
`parse_ts` never returns `None` there and the branch is unreachable through the
production entry point. `roster.py:1080-1087` says exactly that, correctly. I
confirmed the floor is nevertheless *right* when reached, by calling
`_update_catalogue_seen` directly with 500 unparseable `1-01-01` entries beside a
real id dated yesterday: head keeps the real id, `384396f` evicts it. The only
thing wrong is the test file's claim about which test pins it — finding 2.

---

## 6. F3, A2, F2, F4 — measured

### F3: the retirement report, computed before the cap

| case (500 fillers + one real departed arm) | **head** | `384396f` | `a390bc9` |
|---|---|---|---|
| A control: real arm alone, ZERO census turns | 1 retired, **REAL present** | present | present |
| **B +500 LOW fillers, ZERO census turns** | 501 retired, **REAL present** ✓ | 500, **ABSENT** | absent |
| C +500 HIGH fillers, ZERO census turns | 501, **REAL present** | present | present |
| D +500 LOW fillers, census NAMES the arm | 501, **REAL present** | present | **absent** |

The uncapped list reaches exactly two readers — `added_since_last` (`:1576`) and the
retirement loop (`:1577`); every attribution, alias-map and hold-over path reads
`carried_arms`, which is still capped at 500 with its count-only warning (`:9916`).

**Is the uncapped report bounded? No — it is linear in the input, and the worker's
cost note is numerically accurate.** Measured through the real CLI:

| planted `arms` | `previous.json` | **head** `latest.json` / stdout | `384396f` |
|---|---|---|---|
| 1,000 | 0.04 MB | 0.10 MB / 0.07 MB | 0.05 / 0.03 MB |
| 100,000 | 4.4 MB | 9.60 MB / 6.40 MB | 0.05 / 0.03 MB |
| **1,000,000** | 44 MB | **96.00 MB / 64.00 MB**, rc 0 in 12.8 s | (capped at 500) |

96 MB and 64 MB are exactly the two numbers `roster.py:838-843` records. Reaching it
needs write access to `eval-results`, and it does not compound. See finding 3 for the
one thing the note does not name.

### A2 and F2

| probe | **head** | `384396f` | `a390bc9` |
|---|---|---|---|
| `last_seen: 0001-01-01` | **published nothing** (dropped, older than the window); no `1-01-01` in the file ✓ | publishes `"1-01-01"` | dropped |
| 500 plants at `0001-01-01` + a real id seen yesterday | **real kept, all 500 dropped**, n_seen=3 ✓ | real **gone**, 498 plants kept | real kept, 500 dropped |
| every published `last_seen` round-trips through `parse_ts` | **0 non-round-tripping** ✓ | `1-01-01` fails | `\r\n…\r\n` and `…-08:00` fail |
| `2026-09-01T23:00:00-08:00` | **`2026-09-02`** ✓ | `2026-09-01` (a day early) | raw, unconverted |
| `2026-09-02T01:00:00+05:00` | **`2026-09-01`** ✓ | `2026-09-02` (a day late) | raw, unconverted |

### F4

The brief's own literal case through `main()` — `mine = 19,999,999`, denominator
exactly `1,000,000,000`, share `1.9999999` (13 filler models, because
`MAX_WEEKLY_TURNS = 10⁷`):

```
head     : below the 2% exit bar for the last 8 weeks (1.9999999% of rankable census usage)
384396f  : below the 2% exit bar for the last 8 weeks (1.9999998999999999% of …)
a390bc9  : below the 2% exit bar for the last 8 weeks (2% of …)          <- round-7's N3 bug
```

The shipped test (`:9998`) uses those same numbers, not the cheaper 7,999,999 /
400,000,000 round 7 shipped. Round 7's N3 test
(`test_the_share_fallback_is_checked_against_the_bar_as_well`) is **still red**
under the `:.6g`-unchecked mutation.

---

## 7. Cross-cutting checks (all clean)

- **Hostile inputs stay count-only.** Round 8's battery re-run (5 hostile arm ids —
  newline + `::error::`, 500 chars, `../../etc/passwd`, NUL,
  `${{ secrets.GITHUB_TOKEN }}` — the same 5 as `catalogue_seen` ids with
  `\r\n`-wrapped dates, a `"garbage"` and a `9999-12-31` `last_seen`, hostile census
  keys, `1e308` cells): rc=0, three count-only warnings, and **none** of `pwned`,
  `::error::`, `secrets.GITHUB_TOKEN`, `etc/passwd`, `garbage`, `9999-12-31`, `\r`,
  `\n` in stdout **or** `latest.json`. Byte-for-byte the same output as `384396f`.
- **Determinism.** Three scenarios (two-hop chain, two-snapshot, 500-plant cap) under
  `PYTHONHASHSEED` ∈ {0, 1, 42, 7919, 12345}: **1 distinct output each** across
  roster JSON *and* rendered Markdown, despite `_usage_alias_map` and
  `_census_relevance` both iterating sets.
- **`test_no_model_ids_are_hardcoded_outside_fixtures` (`:2192`) is green and keeps
  its teeth.** Planted one at a time into a scratch copy and restored: a comment
  carrying a model id in `harness/roster.py` → FAILED; in `evals/roster-policy.yml`
  → FAILED; in `scripts/refresh_models.py` → FAILED; restored → OK.
- `_census_relevance` is a behaviour-preserving extraction of round 7's `_relevant`
  (same four routes, same order), which the 24-scenario sweep and the full suite
  both confirm.

---

## 8. Merge hygiene (`5d1f00a`)

Parents: `d346a5e` (the branch) and `8d131bd` (`origin/main`, PR #134).

- **Symbol sets compared by AST**, never by regex (`$SP/r9work/mergecheck.py`,
  `ast.ClassDef`/`ast.FunctionDef` walk):

  | file | parent1 | parent2 | merge | union | lost from p1 | lost from p2 | invented |
  |---|---|---|---|---|---|---|---|
  | `test/run_tests.py` | 542 | 350 | **636** | 636 | **none** | **none** | none |
  | `harness/scorers/objective.py` | 29 | 45 | **45** | 45 | **none** | **none** | none |

- **`CHECKS` registry**, parsed as an `ast.Dict` (`$SP/r9work/checkscheck.py`):
  parent1 11 keys, parent2 15, merge **15** = the exact union; none lost, none
  invented. `harness/scorers/objective.py` is **byte-identical** to `origin/main`'s
  (`9b58c3d9eca56078c414bba66540a203`), so the merge took that side wholesale.
- **Count arithmetic.** Measured by running each tree's own suite: `384396f` = 411,
  `origin/main` (`8d131bd`) = 305, `git merge-base origin/main 384396f` (`a6c882a`)
  = 217. So 411 + (305 − 217) = 499 post-merge, + the 21 new tests in
  `TestIssue67Review8` = **520** — exactly the observed number, so the merge lost no
  test from either side.
- **`.github/`**: `git diff --stat 384396f 5d1f00a -- .github/` is **empty**, and
  against `origin/main` only `.github/workflows/eval.yml` differs (+247/−3) — the
  three deleted lines are the canary comment, the hardcoded `--model
  claude-haiku-4-5`, and the commit message, all replaced by this PR's own roster
  step. Nothing else under `.github/` moves.
- **Authorship**: every one of the 9 commits in `384396f..5d1f00a` is
  `4205216+Adam-S-Daniel@users.noreply.github.com` ✓.

---

## 9. New findings

Three. None is a repeat of a round-7 or round-8 finding — I checked each against
both reports and say so per item, because this is the last authorized round.

### should-fix

**F-A — `_as_date` crashes the whole roster with an uncaught `OverflowError` on a
year-1 `last_seen` carrying a positive UTC offset. `harness/roster.py:913`. NEW this
round, introduced by the A2/F2 fix; a regression against BOTH `384396f` and
`a390bc9`, neither of which crashes.**

```python
def _as_date(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).date().isoformat()   # :913
```

`parse_ts` keeps whatever offset the entry carried (`timeweeks.py:34`), so
converting a year-1 timestamp with a positive offset to UTC lands before
`datetime.min` and `astimezone` raises. The future clamp at `:986`
(`today if parsed > now else _as_date(parsed)`) covers the year-9999 side; nothing
covers this one. Measured through the real CLI with files on disk
(`$SP/r9work/a_ovf.py`, `ovf3.py`):

```
previous.catalogue_seen = [{"id": "claude-opus-4-1",
                            "last_seen": "0001-01-01T00:00:00+05:00"}]

head 5d1f00a : rc=1   OverflowError: date value out of range   NO ROSTER PUBLISHED
                      + a 10-line traceback carrying the runner's absolute paths
384396f      : rc=0   publishes "1-01-01"   (round 8's A2 defect)
a390bc9      : rc=0   entry dropped as older than the window
```

The window is narrow and I mapped it: `0001-01-01T00:00:00+00:01` crashes,
`0001-01-01T00:00:01+00:00`, `0001-01-01T05:00:00+05:00`, `0001-01-02T00:00:00+05:00`,
plain `0001-01-01` and any negative offset do not. The sibling `census_at` conversion
at `:1384` is **not** affected — it is gated on `CENSUS_PUBLISHED_CODES`, and I
confirmed a year-1 `generated_at` completes at rc=0.

**Why it matters past the narrow window.** This is the input class
`_clean_catalogue_seen` exists for — the module docstring calls `eval-results`
untrusted, and round 8 rated the sibling `1-01-01` case a should-fix from exactly
the same capability. It breaks the contract round 7's N4 established and that
`roster.py:167-179` states in its own words: "this module's docstring promises a
one-line named message about every untrusted input". N4's guard wraps the JSON
*load*; this fires later, during *cleaning*, so the guard cannot reach it.

**Why it is not a blocker.** It fails closed and loud. `eval.yml:376-396` turns a
non-zero rc into `::warning::model roster NOT refreshed: <reason>` and the eval runs
on the fixture pins; `extract_reason` skips the traceback header and every indented
frame, so the step summary gets the clean line `OverflowError: date value out of
range` with no path. The traceback itself still reaches the public Actions job log,
which is the half of N4's rationale that stands.

*Repeat determination:* **not a repeat.** Round 7's N4 is the same class (an
uncaught exception on untrusted `previous.json` escaping as a traceback) but a
different site and exception; round 8's should-fix was the `1-01-01` value, and this
is the defect its fix introduced. It is, however, the **third consecutive round** in
which a change to that one rendering line has introduced a new defect
(round 7 N1 raw `last_seen` → round 8 A2/F2 `1-01-01` + local clock → this).

*Fix, two lines.* Give the conversion the same treatment every other malformed
entry gets — count it and skip it, so the published set stays parseable:

```python
    try:
        return moment.astimezone(timezone.utc).date().isoformat()
    except OverflowError:          # year 1 (or 9999) once the offset is applied
        return None                # caller: skipped += 1; continue
```

with a test through `main()` on `last_seen: "0001-01-01T00:00:00+05:00"` asserting
rc=0 and that the entry is absent — red on head today.

### nits

**F-B — `test/run_tests.py:9728-9730` names a test as the regression floor for A3's
sixth defence, and that test does not catch its mutation. NEW; not a repeat.**

> "and the sixth — the cap sort's `or now`, replaced by a floor under A2 — is pinned
> by `test_five_hundred_year_one_plants_do_not_evict_real_history`."

Measured: restoring `parse_ts(survivors[i]) or now` at `:1088` and leaving everything
else alone leaves the **full suite 520 GREEN**, that test included. What that test is
actually red under is the *render* mutation (`A2_strftime_render`), which is a
different defence. The underlying code is fine — the branch is genuinely unreachable
once `_as_date` normalises every date, so the mutation is an equivalent mutant, and
`roster.py:1080-1087` describes it accurately as "a FLOOR rather than a live one".
The comment in the test file is the only thing that overclaims, and it overclaims in
the direction that matters: it tells the next reader a defence is pinned when nothing
pins it. Fix: reword it to say "equivalent mutant — unreachable because
`_clean_catalogue_seen` re-renders every date first", the way round 8's adversarial
report handled its own three equivalent mutants.

**F-C — F3's cost note is accurate about the sizes but does not name the two
surfaces they land on. `harness/roster.py:838-849`. NEW; not a repeat.**

The note records "a 96MB roster and 64MB of `render_summary` Markdown" — I
reproduced both exactly (§6). What it does not say is where they go:
`eval.yml:380` is `cat "$work/summary.md" | tee -a "$GITHUB_STEP_SUMMARY"`, and
GitHub's step-summary cap is 1 MiB, so 64 MB is discarded with a job error rather
than truncated; and the 96 MB roster is committed to the public `eval-results`
branch by the commit step. Both need write access to `eval-results` to provoke, and
the tradeoff itself is the one the brief prescribed ("take the other remedy round 7
offered") and is argued soundly — a size cap would only move the number at which a
real retirement can be hidden. This is a record-only gap in an otherwise unusually
honest note: two clauses naming the step-summary limit and the committed size would
close it.

### Explicitly checked and clean

- No warning echoes a value from `previous.json` or the census; every new one names a
  count.
- `catalogue_seen` stays a superset of `api_ids` in every scenario, including the
  600-plant and 500-plant ones.
- Published output deterministic across five `PYTHONHASHSEED` values.
- The A1 composition preserves rule (1)'s disjointness (round 7's disjointness test
  still green; 0 partition failures over 1,200 random catalogues).
- 24 ordinary scenarios byte-identical to `384396f`.
- No `__pycache__` left behind; every mutation ran on a scratch copy and the copy was
  deleted.

## What I could not check

- **PR #129's GitHub state and CI.** No network. Everything here is local.
- **A live workflow run.** `eval.yml` was asserted by `git diff` byte-identity and by
  reading the roster step; I did not dispatch it and never invoked the real `claude`.
- **Whether Anthropic's `/v1/models` returns the catalogue rotation A1 needs.** The
  two-run chain needs only shapes `roster-policy.yml:42-52` already documents.
- **F-A's step-summary behaviour on a real runner.** I read `extract_reason`'s
  filtering and traced my captured stderr through it by hand; I could not run
  GitHub's summary writer.
- One environmental note: run inside `/tmp`, the suite reports `skipped=3` rather
  than 2 — the extra skip is `no agentskills checkout at /tmp/agentskills/...`, a
  pre-existing path-relative skip unrelated to this PR. In `$SP/rev129i-code` the
  count is the expected 2.

---

## 10. Tree integrity

`find . -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum | md5sum`,
run in `$SP/rev129i-code`:

| | value |
|---|---|
| **before** any work | `1d727685fd9edbac231af74549eff6c8` (92 files) |
| **after** everything | `1d727685fd9edbac231af74549eff6c8` (92 files) |

The 92-line per-file manifests `diff` clean; `harness/roster.py` is still
`a7bd1c68f1bbb91bdd4f71b1600c3569`. **No mutation was ever applied inside
`$SP/rev129i-code`** — all 17 went to throwaway copies under `/tmp/r9mut/`,
`/tmp/r9guard`, `/tmp/r9pmut*`, each deleted afterwards.
`/home/user/skills-evals` is unmodified (`git status --short` empty, HEAD still
`527c729`). `$SP/rev129i-adv` was never entered or written. No background process is
running (`ps -eo pid,etimes,cmd` clean). Scratch drivers remain under `$SP/r9work/`,
outside every reviewed tree.
