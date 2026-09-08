NOT CLEAN — the previous-arm alias attribution miss is NOT fixed in production: `compute_roster` builds the usage alias map from `api_ids + counts` only, so `previous_arms_folded` never folds a since-retired dated arm and the roster still publishes `claude-sonnet-5` at "carries 97.1% of rankable census usage" instead of ~1.96%; the test that "pins" it builds a different alias map and passes verbatim on b743d50.

# skills-evals PR #129 — round-6 code review (head `a946c9b`)

Scope: what round-5 (`b743d50..a946c9b`) changed, plus the attribution design as a
whole. Effort: high. All work in `$SP/rev129f-code` (tree verified `md5`-equal to
`a946c9b` for all five touched files before and after every mutation).
`/home/user/skills-evals` was read-only throughout (`git show/log/diff` only).

## 1. Verifiers

| Command | Exit | Count |
|---|---|---|
| `python3 test/run_tests.py` | **0** | **307** tests, OK (b743d50 baseline: 296) |
| `python3 test/test_propagation.py` | **0** | **164** tests, OK (skipped=1) |

Re-run after the last mutation was restored: same numbers, and
`md5sum -c` on `harness/roster.py`, `harness/run_eval.py`,
`evals/roster-policy.yml`, `test/run_tests.py`, `DESIGN.md` all `OK`.
`__pycache__` was purged before and after every mutation (the round-4 stale-`.pyc`
trap). No background processes were started; `ps` shows none left.

## 2. `.github/workflows/eval.yml`

`git -C /home/user/skills-evals diff d0de00f a946c9b -- .github/workflows/eval.yml`
is **EMPTY** (0 bytes). So is `b743d50..a946c9b` for the same path, and so is
`git diff --stat b743d50 a946c9b -- .github/` (nothing under `.github/` moved at
all). The workflow still does `git show origin/eval-results:roster/latest.json >
"$work/previous.json"` (eval.yml:353) and passes `--previous` (eval.yml:368-374), so
`catalogue_seen` genuinely round-trips in CI without a workflow change.

## 3. Per-item verdicts

Every mutation below was applied to the working tree, the named test class(es) run,
and the tree restored from a pristine copy immediately afterwards (verified by
`md5sum -c`). "307 green" means the mutation left the **whole** suite passing.

### The design decision (catalogue_seen replaces `_canonical_id_re`)

| Sub-requirement | Status | Evidence | Mutation |
|---|---|---|---|
| `_canonical_id_re` gone with its tests | **FIXED** | function deleted; only three prose references remain (`roster.py:262`, `run_tests.py:5308,5527,5534`) explaining the withdrawal. `import math` also dropped and no `math.` use remains. Removed tests: `test_a_proxy_alias_does_not_gain_a_seat_from_the_canonical_shape_check`, `test_a_since_retired_real_model_still_counts_in_the_denominator`, `test_proxy_alias_with_family_word_stays_unattributable` | n/a (deletion) |
| `catalogue_seen` written into the published roster JSON | **FIXED** | `roster.py:1046`; end-to-end `main()` run publishes it (§5 below) | publish `[]` → `TestIssue67Review5.test_catalogue_seen_round_trips_through_the_published_roster` **red** |
| read back from `previous.json` | **FIXED** | `_clean_catalogue_seen` `roster.py:574-601`, consumed at `roster.py:779` | as above |
| deduplicated + sorted | **FIXED** | `sorted(set(api_ids) \| set(...))` `roster.py:779`; `_clean_catalogue_seen` also de-dupes (`roster.py:594`). Measured: a `previous.json` listing `claude-opus-4-8` twice publishes it once, sorted | covered by the same test's `assertEqual(result["catalogue_seen"], sorted(set(...)))` |
| each id shape-checked with the previous-arm rule, count-only warning | **FIXED** | `roster.py:593` uses `PREVIOUS_ARM_ID_RE`; warning at `roster.py:598-600` names only a count | drop the `PREVIOUS_ARM_ID_RE.match` → round-trip test **red** |
| `_is_attributable` covers the five routes | **PARTIAL** (see blocker B1) | `roster.py:287-291` — all five clauses are present in the source | per-clause results below |
| legacy-id scenario → 9.68%, no seat | **FIXED** | measured §4 A | drop the `catalogue_seen` clause → `TestIssue67Review5.test_legacy_shaped_previously_seen_model_is_attributed_via_catalogue_seen` + `TestIssue67Review4.test_a_since_retired_real_model_still_counts_via_catalogue_seen` **red** |
| empty `catalogue_seen` (first-run) documented | **FIXED** | measured §4 B; `TestIssue67Review5:5572`; documented in `_is_attributable`'s FIRST-RUN CAVEAT, `usage_share`'s docstring, DESIGN.md property 5, `roster-policy.yml` | make an empty `catalogue_seen` fail open → that test + `test_proxy_and_implausible_aliases_stay_unattributable` **red** |
| previous-arm alias scenario → ~2.0% not 97.09% | **MISSING end-to-end** | measured §4 C: `compute_roster` still yields **97.0874%** | see B1 |
| proxies unattributable, `retired: []` | **FIXED** | measured §4 D — all five, seat and retirement both | `_is_attributable → True` → 4 failures incl. `test_proxy_and_implausible_aliases_stay_unattributable` |
| "item 1's api-id spellings must be load-bearing in their own tests" | **MISSING (half)** | dropping `candidate in api_ids` → **307 green**; dropping `folded in api_ids` → **307 green**. Only the folded set is pinned | see B2 |

**Per-clause mutation teeth for `_is_attributable` (roster.py:287-291), whole suite:**

| Clause dropped | Result |
|---|---|
| `candidate in api_ids` | **307 green — no test** |
| `folded in api_ids` | **307 green — no test** |
| `folded in (api_ids_folded or ())` | 2 red (`test_dated_only_catalogue_with_usage_under_the_undated_alias_is_attributed`, `test_mixed_dated_and_undated_ids_do_not_give_a_false_100_percent`) |
| `candidate in previous_arms or folded in previous_arms` | **307 green — no test** |
| `candidate/folded in previous_arms_folded` | 1 red (`test_previous_arm_alias_usage_counts_via_previous_arms_folded` — a unit test, see B1) |
| `candidate/folded in catalogue_seen` | 2 red |
| whole function → `return True` | 5 red |

### S1 – S6 and N1 – N7

| Item | Status | Code | Pinning test | Mutation → red |
|---|---|---|---|---|
| **S1** per-window `min_ranked_turns` | **FIXED** (enter side) | `roster.py:800-811` | `TestIssue67Review5.test_min_ranked_turns_floor_applies_to_the_enter_window_on_its_own` (:5656) | `enter_usable = usable` → **red** (and the roster then seats `claude-sonnet-4-6` at "100.0%", §4 E) |
| S1 exit side | untested | `roster.py:811`, branch `roster.py:864-875` | none | `exit_usable = usable` → **307 green**. Unreachable with the shipped policy (exit window ⊇ enter, so `exit_ranked_total == ranked_total`); the code comment says so. Nit N-e |
| **S2** relative `min_ranked_share` | **FIXED for the 8-week union; NOT applied per window** | `roster.py:725-733`; policy `roster-policy.yml:99-107` | `test_min_ranked_share_holds_a_previous_arm_at_the_absolute_floor` (:5680), `..._does_not_hold_a_genuinely_ranked_census` (:5697) | disable the check → **red**; force it always → 13 red. But the same defect reproduces at the enter window (should-fix SF1, §4 F) |
| **S3** strengthen the heavily-used-arm test | **FIXED** | `run_tests.py:5257-5266` (`assertIn("rankable census usage")`, `assertNotIn("floor")`) | `TestIssue67Review4.test_a_heavily_used_dated_previous_arm_is_not_retired_at_zero_percent` (:5238) | revert to pre-item-1 attribution (drop `api_ids_folded` + `previous_arms_folded`) → **red** (it was green under that mutation before the strengthening) |
| **S4** `_clean_models` shape-checks ids | **FIXED** | `roster.py:437-441, 447-449` | `test_malformed_model_id_in_the_models_document_is_dropped_with_a_warning` (:5712) | `elif False:` → **red** |
| **S5** `skill_install_failed` path | **FIXED** (path gone); wording now false for one branch | `run_eval.py:552-554` | `TestIssue63Round2.test_seed_already_shipping_the_skill_dir_is_a_clean_error` (:4844) | restore the old `{skill_dest} … {exc}` → **red**. See nit N-a |
| **S6** `\Z` anchor pinned | **FIXED** | `roster.py:186` | `test_previous_arm_id_re_rejects_a_trailing_newline` (:5736) | `\Z` → `$` → **red**. `MODEL_ID_RE`'s own `\Z` stays pinned by the round-3 `HOSTILE_MODELS["trailing_newline"]` case |
| **N1** two decimals at the bar | **PARTIAL** | `_format_share` `roster.py:301-307` | `test_retirement_reason_uses_two_decimals_when_one_would_touch_the_bar` (:5745) | always-`.1f` → **red**. But a true **1.999%** still renders "below the 2% exit bar (**2.00%**)" — SF2 |
| **N2** `_clean_counts` int-only | **FIXED** | `roster.py:498-508` | `test_clean_counts_requires_actual_ints…` (:5763) + rewritten `TestIssue67Review.test_census_counts_that_are_not_actual_ints_are_dropped_not_coerced` (:2752) | restore `int(n)` coercion → **2 red** |
| **N3** dead `elif not usable:` retirement branch | **FIXED — removed** (they chose removal; comment `roster.py:1002-1011` says why) | `roster.py:1002-1012` | n/a | re-inserted the branch as an `AssertionError` tripwire: **307 green, never fired** — confirms it was genuinely unreachable |
| **N4** validate the new thresholds | **FIXED** | `_THRESHOLD_CHECKS` `roster.py:82-91`, `validate_policy` `roster.py:96-105`, called `roster.py:1123-1128` | `test_roster_policy_is_the_single_source_of_thresholds` (:5781) + `test_policy_file_carries_the_thresholds_and_the_adr_placeholder` (:2149) now asserts `20`/`0.01` and calls `validate_policy` | drop both keys from `_THRESHOLD_CHECKS` → **9 subtest failures** |
| **N5** unconditional assertion | **FIXED** | `run_tests.py:5340-5344` — the `if … in self._arm_ids(result):` is gone, replaced by `assertNotIn(…)` | `test_a_since_retired_real_model_still_counts_via_catalogue_seen` (:5304) | drop the `catalogue_seen` clause → **red** |
| **N6** registry message drops the path | **FIXED** | `run_eval.py:284-286`; `entry["source"]` is only ever one of `--registry flag` / `$SKILLS_EVALS_REGISTRIES` / `$AGENTSKILLS_DIR` / `sibling default`, so no path can leak | `TestIssue63Review.test_nonexistent_explicit_override_is_rejected_before_any_arm_runs` (:4381) now `assertNotIn(str(bad_path), msg)` | restore the path → **red** |
| **N7** `1e308` comment + duplicate proxy tests | **FIXED** | comment `roster.py:379-388`; verified empirically: one `1e308` cell → `inf`, two → `nan`. `test_a_proxy_alias_does_not_gain_a_seat_from_the_canonical_shape_check` deleted; the survivor now covers **five** aliases (`run_tests.py:5270-5294`) | `_is_attributable → True` → **red** |

## 4. Measured rosters

All from `harness/roster.py` at `a946c9b`, `now = 2026-09-04T12:00:00Z`, the repo's
own `evals/roster-policy.yml`, `W = 2026-W36 … 2026-W29`.

### A. Legacy-id scenario — previous `catalogue_seen` includes `claude-3-opus-20240229`

Catalogue `{claude-sonnet-4-6 (not newest), claude-sonnet-5-0, claude-opus-4-2}`;
census `{claude-3-opus-20240229: 112/wk × 4, claude-sonnet-4-6: 12/wk × 4}`.

```
arms:
  - claude-sonnet-5-0: newest model in the sonnet tier, 95 days old (past the 7-day cooling-off)
  - claude-opus-4-2:   newest model in the opus tier, 246 days old (past the 7-day cooling-off)
judge: claude-sonnet-4-6 (is_arm=False)   preflight: claude-sonnet-5-0
retired_since_last: []
added_since_last:   [claude-sonnet-5-0, claude-opus-4-2]
catalogue_seen: [claude-3-opus-20240229, claude-opus-4-2, claude-sonnet-4-6, claude-sonnet-5-0]
MEASURED claude-sonnet-4-6 enter-window share = 9.6774%   (48/496)   -> NO SEAT   ✔ (brief: 9.68%)
enter-window raw=496 ranked=496
```

### B. Same scenario with an EMPTY `catalogue_seen` (documented first-run behaviour)

```
arms:
  - claude-sonnet-4-6: carries 100.0% of rankable census usage over the last 4 weeks (at or above the 10% entry bar)
  - claude-sonnet-5-0: newest model in the sonnet tier, 95 days old …
  - claude-opus-4-2:   newest model in the opus tier, 246 days old …
judge: claude-opus-4-2 (is_arm=TRUE)    preflight: claude-sonnet-5-0
retired_since_last: []
catalogue_seen: [claude-opus-4-2, claude-sonnet-4-6, claude-sonnet-5-0]
MEASURED share = 100.0000%   enter-window raw=496 ranked=48   -> SEATED (fourth paid arm, and the judge is now also an arm)
```
Identical with `previous=None`. This is the documented caveat; it is stated in
`_is_attributable`, `usage_share`, DESIGN.md property 5 and `roster-policy.yml`.
Worth noting out loud: the caveat also bites on the **first run after this PR
merges**, because the `previous.json` already on `eval-results` has no
`catalogue_seen` key — none of the four doc sites mentions that case (nit N-d).

### C. Previous-arm alias scenario — **the blocker**

Previous arm `claude-sonnet-4-9-20260101` (dated, since gone from the API); its
usage recorded under the undated alias `claude-sonnet-4-9`. Catalogue
`{claude-sonnet-5, claude-haiku-4-5, claude-opus-5}`; census
`{claude-sonnet-4-9: 5000, claude-sonnet-5: 100, claude-haiku-4-5: 3}` in W36.

```
arms:
  - claude-haiku-4-5: newest model in the haiku tier, 338 days old …
  - claude-sonnet-5:  carries 97.1% of rankable census usage over the last 4 weeks (at or above the 10% entry bar)   <-- WRONG
  - claude-opus-5:    newest model in the opus tier, 156 days old …
judge: claude-opus-5 (is_arm=TRUE)      preflight: claude-haiku-4-5
retired_since_last: [{"id":"claude-sonnet-4-9-20260101","reason":"no longer returned by the Models API"}]
catalogue_seen: [claude-haiku-4-5, claude-opus-5, claude-sonnet-4-9-20260101, claude-sonnet-5]
MEASURED claude-sonnet-5 enter-window share = 97.0874%    enter-window raw=5103 ranked=103
```

Expected ~1.96%. The 5000 real turns are still dropped. Diagnosis and fix in B1.

### D. Proxies (`api_ids={claude-opus-4-8}`, `previous_arms={claude-opus-4-8}`, `catalogue_seen={claude-opus-4-8}`)

| alias | `rung_of` | raw | ranked | end-to-end at 100000 turns/wk × 8 |
|---|---|---|---|---|
| `proxy-router-claude-sonnet-4-5` | 1 | 500 | **0** | seated=False, `retired: []`, `claude-opus-4-8` kept |
| `claude-sonnet-proxy-route` | 1 | 500 | **0** | idem |
| `claude-sonnet-9-9` | 1 | 500 | **0** | idem |
| `claude-opus-٤` | 2 | 500 | **0** | idem |
| `claude-opus-4-eu` | 2 | 500 | **0** | idem |

All five: unattributable, no seat, `retired_since_last: []`, no warning leaked. ✔

### E. S1 floor — before / after

Census `{claude-sonnet-4-6: 1 turn in W36, claude-opus-5: 6/wk × W32–W29}` (24
ranked turns in weeks 5-8; union ranked total 25 ≥ 20, enter-window total 1).

```
BEFORE (enter_usable = usable):
  arms: haiku-4-5(newest), claude-sonnet-4-6: "carries 100.0% of rankable census usage over the last 4 weeks
        (at or above the 10% entry bar)", sonnet-5(newest), opus-5(newest)      <-- 4th arm on ONE turn
AFTER  (a946c9b):
  arms: claude-haiku-4-5(newest), claude-sonnet-5(newest), claude-opus-5(newest)   <-- sonnet-4-6 NOT seated ✔
  retired: []   judge: claude-fable-5-1 (is_arm=False)   preflight: claude-haiku-4-5
```
The 30-turn variant (`opus-5` 8/8/7/7 across W32–W29) behaves identically.

### F. S2 floor — before / after, and the residual gap

`{other: 100000/wk × 8, claude-haiku-4-5: 20 turns in W36}` — 800,020 raw.

```
BEFORE (no min_ranked_share):
  retired_since_last: [{"id":"claude-opus-4-8",
     "reason":"below the 2% exit bar for the last 8 weeks (0.0% of rankable census usage)"}]   <-- retired on 20 turns
AFTER (a946c9b):
  arms include claude-opus-4-8: "held over from the previous roster: census published but only 20 of
     800020 raw turns over the window are rankable, attributable usage (0.00% — under the 1% relative
     floor), too little to be evidence of anything, so there is no evidence to retire it"
  retired_since_last: []    ✔
S2b (genuinely ranked, {claude-sonnet-5: 100/wk × 8}):
  retired_since_last: [{"id":"claude-opus-4-8","reason":"below the 2% exit bar for the last 8 weeks
     (0.0% of rankable census usage)"}]   <-- retirement still proceeds ✔
```

**Residual (SF1).** The relative floor is applied to the 8-week union only, never
per window. Census
`{other: 1,000,000/wk × W36–W33, claude-sonnet-4-6: 25 turns in W36, claude-opus-5: 25,000/wk × W32–W29}`:

```
union  raw=4,100,025  ranked=100,025  ratio=2.44%   -> passes both floors, usable=True
enter  raw=4,000,025  ranked=25       ratio=0.0006% -> NEVER CHECKED (only the 20-turn absolute floor is)
arms:
  - claude-haiku-4-5: newest model in the haiku tier …
  - claude-sonnet-4-6: carries 100.0% of rankable census usage over the last 4 weeks (at or above the 10% entry bar)
  - claude-sonnet-5:  newest model in the sonnet tier …
  - claude-opus-5:    newest model in the opus tier …
```
`claude-sonnet-4-6` — not the newest in its tier — is seated as a fourth paid arm on
25 turns out of 4,000,025 in that window. That is S2's own defect, one window over.

### G. End-to-end `main()` against hostile inputs

`models.json` carrying `{"id": "claude-opus-4\n::error::pwned::"}` and `{"id": 123}`;
`census.json` with a `"5"` string cell; `previous.json` with
`catalogue_seen: ["claude-opus-4-8", "claude-sonnet-4-5\n::error::x::", 7, null, "claude-opus-4-8"]`.
`rc=0`. stderr: four count-only lines, no value quoted. Published `latest.json`
carries `"catalogue_seen": [claude-fable-5-1, claude-haiku-4-5, claude-opus-4-8,
claude-opus-5, claude-sonnet-5]` — hostile entries dropped, duplicate collapsed,
sorted. **No raw control character anywhere in `latest.json`; no `::error::`, no
absolute path in either `latest.json` or the rendered `summary.md`.**

## 5. Findings

### BLOCKER

**B1 — `previous_arms_folded` is inert for the scenario it was added for; the
alias attribution miss survives. `harness/roster.py:762` (with :349, :627, :288-291).**

`compute_roster` builds the USAGE alias map as

```python
seat_aliases = alias_map(api_ids)                    # roster.py:761
aliases      = alias_map(api_ids + list(counts))     # roster.py:762
```

`alias_map(ids)` maps `<base>-YYYYMMDD → <base>` only when **both** spellings are in
`ids`. In the target scenario the previous arm's dated id is in neither `api_ids`
(it left the API) nor `counts` (usage is recorded undated), so it is not a key of
`aliases`, so `previous_arms_folded = _fold_set(previous_arms_set, aliases)`
(`roster.py:349`, `:627`) equals `previous_arms` — and the new clause
`candidate in previous_arms_folded or folded in previous_arms_folded`
(`roster.py:290`) can never match. `catalogue_seen` does not rescue it either: it
holds the **dated** id, and it is never folded.

Reproduction (`compute_roster`, no hand-built helpers) is §4 C above:
`claude-sonnet-5` is published with `"carries 97.1% of rankable census usage over
the last 4 weeks (at or above the 10% entry bar)"` — the brief's stated failure
number, unchanged — instead of ~1.96%. `enter-window raw=5103 ranked=103`: the
5000 turns are still outside the denominator.

The test that is supposed to pin this,
`TestIssue67Review5.test_previous_arm_alias_usage_counts_via_previous_arms_folded`
(`test/run_tests.py:5593`), builds a **different** alias map than production does:

```python
aliases = roster.alias_map(list(api_ids) + list(previous_arms) + list(cleaned))
```

Note `list(previous_arms)` — production never adds that. Measured side by side:
with the test's map the share is `1.9596%`; with
`alias_map(api_ids + list(counts))` — what `compute_roster` actually passes — it is
`97.0874%`. The test is also **hollow by the brief's own definition**: I ran its
body verbatim against `b743d50`'s `roster.py` (round 4, `_canonical_id_re` still
present) and it returns `1.9596%` and passes there too, so it does not distinguish
the round-5 code from the code it replaced.

`previous_arms_folded` is not 100% dead — it fires when the dated previous arm is
*also* a census key or an api id (measured: 1.9569% vs 100.0% with the route
removed) — but that is not the case the design decision named, and it is not the
case the 5000-turn / 97.09% measurement came from.

*Fix.* Resolve `previous_arms` and `catalogue_seen` **before** the alias maps and
widen the usage map (the seating map must stay narrow — `seat_aliases` is
deliberately catalogue-only):

```python
previous_arms  = _clean_previous_arms(previous, warn)
catalogue_seen = sorted(set(api_ids) | set(_clean_catalogue_seen(previous, warn)))
seat_aliases = alias_map(api_ids)
aliases      = alias_map(api_ids + list(counts) + previous_arms + catalogue_seen)
```

I applied exactly this to a scratch copy: the whole suite stays **307 green**, and
the §4 C roster changes to `claude-sonnet-5: "newest model in the sonnet tier"`
with a measured share of **1.9596%** (`raw=5103 ranked=5103`). The pinning test then
needs to go through `compute_roster` (or at minimum use
`alias_map(api_ids + list(counts))`), or it will keep passing regardless.

**B2 — the brief's "item 1's api-id spellings must be load-bearing in their own
tests" is not met, and a whole attribution route is unpinned. `harness/roster.py:287-291`.**

Whole-suite mutations, one clause at a time:

- drop `candidate in api_ids` → **307 green**
- drop `folded in api_ids` → **307 green**
- drop `candidate in previous_arms or folded in previous_arms` → **307 green**

The mechanical reason is that `catalogue_seen = set(api_ids) | previous`
(`roster.py:779`) is a **superset of `api_ids`**, so inside `compute_roster` both
api-id spellings — and, in steady state, the previous-arms route as well (a seat
can only come from `available`, which comes from `api_ids`, so a previous arm was in
some earlier run's `catalogue_seen`) — are subsumed by the new clause. That is
harmless for behaviour, but it means round 3's `previous_arms` route and round 4's
item-1 `api_ids` route now have **no regression floor at all**: the next round can
delete either and the suite stays green.

*Fix.* Either add the legacy-shaped dated/undated pair the brief asked for, driven
through `compute_roster` with a `catalogue_seen` that deliberately does **not**
contain the id under test (so the api/previous-arm clauses are the only route), or
state in the code that `catalogue_seen ⊇ api_ids` makes the first two clauses
redundant-by-construction and keep them only for the direct-call contract — with a
test asserting that redundancy rather than leaving it undiscovered.

### SHOULD-FIX

**SF1 — the relative floor is union-only, so S2's defect reproduces at the enter
window and seats a false arm. `harness/roster.py:810-811` vs `:725-733`.**

S1 applied `min_ranked_turns` per window; `min_ranked_share` was not. Reproduction
in §4 F: 25 ranked turns against 4,000,025 raw in the enter window (0.0006%) seat
`claude-sonnet-4-6` — not the newest in its tier — at `"carries 100.0% of rankable
census usage over the last 4 weeks"`. Each arm is a paid run.

*Fix.* Compute `enter_raw_total`/`exit_raw_total` alongside the ranked totals (the
`_in_window_totals` calls already return them and both are discarded into `_`) and
extend the gates:

```python
enter_usable = (usable and enter_ranked_total >= policy["min_ranked_turns"]
                and enter_ranked_total >= policy["min_ranked_share"] * enter_raw_total)
exit_usable  = (usable and exit_ranked_total  >= policy["min_ranked_turns"]
                and exit_ranked_total  >= policy["min_ranked_share"] * exit_raw_total)
```
and widen the exit-side `floor_note` (`roster.py:864-873`) to say which floor it
was. Test with the §4 F census.

**SF2 — N1 is only half-fixed: a true 1.999% still renders "below the 2% exit bar
(2.00%)". `harness/roster.py:301-307`.**

`_format_share` escalates to two decimals only when the one-decimal rendering equals
the bar; at two decimals the same collision recurs. Measured directly and
end-to-end (census `{claude-opus-4-8: 1999, claude-sonnet-5: 98001}` in W36):

```
_format_share(1.96,   2) -> '1.96'
_format_share(1.999,  2) -> '2.00'      <-- still reads as the bar
_format_share(1.9999, 2) -> '2.00'
retired reason: "below the 2% exit bar for the last 8 weeks (2.00% of rankable census usage)"
```

*Fix.* Escalate until the rendering actually differs from the bar rather than
stopping at two:

```python
def _format_share(value: float, bar: float) -> str:
    for places in (1, 2, 3, 4, 6):
        text = f"{value:.{places}f}"
        if float(text) != bar:
            return text
    return f"{value:.6g}"
```
Add `1.999` to `test_retirement_reason_uses_two_decimals_when_one_would_touch_the_bar`.

### NITS

**N-a — the new `skill_install_failed` detail is false for one of the two exception
classes it covers. `harness/run_eval.py:552-554`.** The `except OSError` block
catches `FileExistsError` *and* `NotADirectoryError` (a seed shipping
`.claude/skills` as a regular file), but the new prose says `"{skill}/ already
exists in the seed workspace"` in both cases. Reproduced in a runner-shaped layout:

```
case1 (FileExistsError):    'some-skill/ already exists in the seed workspace (FileExistsError)'
case2 (NotADirectoryError): 'some-skill/ already exists in the seed workspace (NotADirectoryError)'   <-- false; some-skill/ does not exist
```
The old message quoted `{exc}` and was accurate; the test at `run_tests.py:4891-4894`
now pins the false wording. Suggest
`f"could not install {skill}/ into the seed workspace ({type(exc).__name__})"` —
true for both branches, still leaks no path. (The brief prescribed the current
string, so this is a wording call for the orchestrator, not a worker miss.)

**N-b — `roster.py`'s module docstring enumerates the published JSON and omits
`catalogue_seen`. `harness/roster.py:26-31`.** The docstring is the only exhaustive
description of the output shape; a new published field belongs in it. (README:337
also still enumerates only "absent, stale, future-dated or empty" as the census
fallback causes — now four short of the eight `_census_verdict` documents; the
first two of those omissions predate round 5, the relative floor is new.)

**N-c — `_clean_catalogue_seen`'s dedup is O(n²) on an unbounded, monotonically
growing list. `harness/roster.py:594`.** `if entry not in ids` over a list.
Measured on the shipped code: n=10,000 → 0.36 s, n=30,000 → 3.06 s (n=100,000 would
be ~34 s). `catalogue_seen` is the one field designed to accumulate forever and it
has no cap, and it is read off a public branch — which is the same threat model the
shape check exists for. Use a `set` for membership and cap the list (a few hundred
is generous for the whole Anthropic catalogue's history).

**N-d — the first-run caveat's four doc sites don't mention the migration case.**
`_is_attributable`, `usage_share`, DESIGN.md property 5 and `roster-policy.yml` all
say "a genuine first run, or a previous roster that could not be read". The first
real run after this merges hits the caveat for a third reason: the `previous.json`
already on `eval-results` predates the field. One clause each.

**N-e — the exit-window floor branch is unreachable with the shipped policy and
untested. `harness/roster.py:811`, branch `:864-875`.** `exit_usable = usable`
leaves all 307 green. The code comment already says it is a no-op today
("exit >= enter weeks … nothing guarantees that relation"), which is a fair reason to
keep it, but the new reason string it prints has never been executed by anything.

**N-f — `_format_share` renders two decimals at the bar in the "at or above"
direction too.** A model at exactly 10% now reads `"carries 10.00% … (at or above
the 10% entry bar)"` (measured against the repo's own fixture shape). Not wrong,
just inconsistent with every other reason's one decimal — the rule could apply only
to the "below/under" comparisons that motivated it.

**N-g — `validate_policy` covers only the numeric thresholds.** `tiers` is still
unvalidated, so a policy missing it KeyErrors inside `tier_rungs` as a traceback
rather than the named `ValueError` `validate_policy` exists to give. `roster.py:96`.

**N-h — `f"{100 * policy['min_ranked_share']:.0f}%"` (`roster.py:730`) would render
a 0.005 policy as "0%".** And `pct:.2f` renders 20/800,020 as "0.00%", which reads
as literally zero. Cosmetic, in a published reason.

### Explicitly checked and clean

- No absolute path reaches `latest.json`, `summary.md` or stderr on the hostile
  end-to-end run (§4 G); `entry["source"]` in the new registry message is a fixed
  literal, never a path.
- No raw control character survives into the published JSON or Markdown; every new
  warning names a count only.
- No new `scripts/` change (diffstat is exactly the five files).
- `math` import removed and unused; no leftover `_canonical_id_re` code path.
- Behaviour diff base→head over six scenarios (default / no-census / snapshot /
  other-heavy / float-cell / exact-bar) shows only the two intended changes: N1's
  `10.0%`→`10.00%` at the exact bar, and N2 dropping the `1.9` and `"5"` cells with
  a `skipped 2 weekly count(s)` warning. Nothing else moved.
- `read_roster` / `roster_models` / `select_models` in `run_eval.py` ignore
  `catalogue_seen`; the new field cannot destabilise the runner.

## 6. Is attribution sound?

**No.** The round-5 design decision closes the two holes it was written for —
`catalogue_seen` correctly attributes a since-retired legacy model (§4 A, 9.68%,
no seat) and correctly refuses all five proxy/implausible aliases (§4 D) — and
`_canonical_id_re` is gone cleanly. But the **third** defect the brief named, the
previous-arm alias losing 5000 real turns and publishing 97.09%, is **unchanged in
production**: §4 C reproduces it verbatim through `compute_roster`, and the test
that certifies it fixed passes on the code it replaced. Under the two-strikes rule
this is an attribution miss in this round, so the PR parks.

Two things make it worth a single further round rather than a rewrite: the fix is
four lines at `roster.py:761-762` (measured: 307 green, and the scenario resolves to
1.9596%), and B2's missing regression floors are test-only work in the same file.

## 7. What I could not check

- **PR #129's GitHub state** — no network, so nothing from the PR page, its checks,
  or CI conclusions. Everything above is from the local tree at `a946c9b` and
  read-only `git` against `/home/user/skills-evals`.
- **The workflow's runtime behaviour** — I confirmed `eval.yml` is byte-identical to
  `d0de00f` and read the roster step's `git show … > previous.json` / `--previous`
  wiring, but I did not execute the step (prior rounds did; nothing in it changed).
- **The real `claude` binary** was never invoked (per the brief); `run_agent` was
  exercised only up to the copytree failure with `CLAUDE_BIN` pointed at a
  nonexistent path.
- **Long-horizon `catalogue_seen` accumulation** in a real deployment — N-c is a
  measured cost curve, not an observed incident.
