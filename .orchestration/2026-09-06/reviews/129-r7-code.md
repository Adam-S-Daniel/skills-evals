NOT CLEAN — every one of the fifteen round-6 items is genuinely fixed through the production entry point (the 97.1% attribution now publishes 1.96%), but S3/N3's new 500-entry `catalogue_seen` cap evicts by ALPHABETICAL id, so 500 low-sorting planted ids delete a real since-retired model from history and flip a published reason to a false "carries 100.0%" — a should-fix regression `a946c9b` does not have.

# skills-evals PR #129 — round-7 scoped code review (head `a390bc95c5cb9d710e6ea0dffab69514194f19fc`)

Scope: the fix round `a946c9b..a390bc9` (15 commits, one per item). Effort: high.
All work in `$SP/rev129g-code`; `/home/user/skills-evals` was read-only throughout
(`git show`/`diff`/`log`/`archive` only). Nothing posted to GitHub; no session,
routine or reminder created; the real `claude` CLI was never invoked; no network.

**Work-dir correction, up front.** `$SP/rev129g-ref` is **not** an export of
`a946c9b` — its 79-file tree md5 is `be2711dfc87637b0c46a4210fd58c5d5`, byte-identical
to `$SP/rev129g-code` (head). Six of the eight files I needed differ from `a946c9b`
(`harness/roster.py` `1349ebd5…` vs `a946c9b`'s `56794b9d…`). I built my own export,
`$SP/r7ref` (`git archive a946c9b`, tree md5 `4a2498277eb7fb81f925515c5afa70a2`, all
six key files md5-verified against `git show a946c9b:<path>`), and every "on a946c9b"
measurement below comes from that. Whoever prepares round 8's work dir should redo
the ref export.

---

## 1. Verifiers

| Command | Exit | Count |
|---|---|---|
| `python3 test/run_tests.py` | **0** | **Ran 328 tests … OK** (expected 328) |
| `python3 test/test_propagation.py` | **0** | **Ran 164 tests … OK (skipped=1)** |
| `python3 harness/run_eval.py evals/workflow-path-audit --arm objective-only` | **1** | 8 checks, 5 fail / 3 pass |

Re-run after the last mutation was restored: identical numbers, and the 79-file
manifest is byte-identical to the pre-work one (§7).

The eval's per-check outcomes are **identical to `af06d0f`** — I exported `af06d0f`
(`$SP/r7base_af`) and ran the same command there, then compared `(id, passed, detail)`
triples: 8/8 `SAME`, `IDENTICAL per-check outcomes: True`.

| check | head | af06d0f |
|---|---|---|
| `docs-change-routes-correctly` | False | False |
| `source-change-routes-correctly` | False | False |
| `lockfile-change-routes-to-installers` | False | False |
| `prose-change-runs-nothing-but-the-required-check` | False | False |
| `required-check-always-fires-and-gates-internally` | False | False |
| `workflows-still-parse` | True | True |
| `event-only-workflows-unfiltered` | True | True |
| `ruleset-unchanged` | True | True |

---

## 2. THE FIRST JOB — the production reproduction (B1)

Driven through `harness/roster.py`'s real CLI, exactly as `.github/workflows/eval.yml`
line 372-378 calls it:

```
python3 harness/roster.py --models <work>/models.json --policy evals/roster-policy.yml \
        --census <work>/census.json --previous <work>/previous.json --out <pub>/latest.json
```

`main()` reads the real clock; the container clock is `2026-09-05T10:58Z`, so
`iso_week(now)` = `2026-W36` and the enter/exit windows are the same weeks round 6
used. Files on disk (`$SP/r7work/b1c`):

- **`models.json`** — `claude-haiku-4-5`, `claude-sonnet-5`, `claude-sonnet-5-1`,
  `claude-opus-5`. The previous arm's dated id is **not** in the catalogue.
- **`previous.json`** — `arms: [claude-sonnet-4-9-20260101, claude-sonnet-5]`
  (the first published under a dated id that has left the API),
  `catalogue_seen` in the bare-string shape a pre-S3 roster publishes.
- **`census.json`** — W36: `{claude-sonnet-4-9: 5000, claude-sonnet-5: 100,
  claude-haiku-4-5: 3}` — the retired arm's 5000 turns recorded under the
  **undated** alias, beside 103 ranked turns for the other two.

**Read off the published `latest.json` with my own eyes:**

| tree | `claude-sonnet-5`'s published sentence |
|---|---|
| **`a390bc9` (head)** | `below the 2% exit bar for the last 8 weeks (**1.96%** of rankable census usage)` — **not seated** |
| **`a946c9b`** | `carries **97.1%** of rankable census usage over the last 4 weeks (at or above the 10% entry bar)` — **seated as a fourth paid arm** |

The plain three-model variant (`$SP/r7work/b1`) shows the same thing from the other
side: on head `claude-sonnet-5`'s reason becomes `newest model in the sonnet tier,
157 days old (past the 7-day cooling-off)` and no `carries 97…` appears anywhere in
the roster; on `a946c9b` it is `carries 97.1% …`. Head's stderr on that run is the
single count-only line `roster: previous roster: migrated 4 'catalogue_seen'
entry/entries from the bare-string shape`; `a946c9b`'s is empty.

**The pinning test.**
`TestIssue67Review5.test_previous_arm_alias_usage_counts_via_widened_alias_map`
(`test/run_tests.py:5600`).

- **Red on `a946c9b`.** Head's `test/run_tests.py` dropped into `$SP/r7ref`
  (`$SP/r7hollow`), then
  `python3 test/run_tests.py TestIssue67Review5.test_previous_arm_alias_usage_counts_via_widened_alias_map`
  → `FAILED (failures=1)`, exit 1. It fails on its **first** assertion:
  `AssertionError: 'carries 97' unexpectedly found in 'carries 97.1% of rankable
  census usage over the last 4 weeks (at or above the 10% entry bar)'`.
- **It drives `compute_roster`, not a hand-built alias map.** That first
  assertion — and the three that follow it (`claude-sonnet-5` is an arm, its reason
  contains `newest`, and contains no `carries`) — all read `result` from
  `TestIssue67._compute` → `roster.compute_roster(models_doc, census_doc, policy,
  previous, now)` (`test/run_tests.py:1746-1751`), with the repo's own
  `evals/roster-policy.yml`. The alias-map block that follows sits **after** those
  assertions, is labelled as reproducing `compute_roster`'s own widened formula only
  to pin the exact `raw=5103 / ranked=5103` and `1.9 < share < 2.0`, and is not what
  makes the test red. Round 5's `list(previous_arms)` cheat is gone.
- **Mutation red.** Reverting `harness/roster.py:974` to
  `aliases = alias_map(api_ids + list(counts))` → `FAILED (failures=1)` on that test.

---

## 3. Per-item verdicts

Every mutation was applied to `$SP/rev129g-code`, the named tests (or the whole suite)
run, and the tree restored from `$SP/r7pristine` and md5-verified afterwards.
"hollow?" = head's own test file run against `$SP/r7ref` (`a946c9b`).

| Item | Verdict | Fix (file:line) | Pinning test (file:line) | Hollowness on `a946c9b` | Mutation → red |
|---|---|---|---|---|---|
| **B1** previous-arm alias miss | **FIXED** | `harness/roster.py:974` (`aliases = alias_map(api_ids + list(counts) + previous_arms + list(catalogue_seen))`; `previous_arms`/`catalogue_seen` resolved at `:940`/`:951` before the maps) | `test/run_tests.py:5600` | **RED** (fails on the `compute_roster` assertion) | revert the `aliases` line → 1 red |
| **B2** dead clauses + route floors | **FIXED** | `harness/roster.py:343-346` (two clauses deleted; docstring `:250-322` states why the three remaining routes are the whole set) | `:5962` / `:5985` / `:6013` / `:6037` / `:6048` | 4 of 5 RED; `test_route_folded_in_api_ids_folded` errors on the new shape — the routes themselves exist at `a946c9b`, so their value is the mutation floor below | drop `folded in api_ids_folded` → **5 red** incl. `test_route_folded_in_api_ids_folded`; drop `previous_arms_folded` → **2 red** incl. `test_route_previous_arms_folded`; drop `catalogue_seen` → **4 red** incl. `test_route_catalogue_seen`; **re-add both dead clauses** → `test_two_dead_clauses_stay_deleted` red |
| **S1** relative floor per window | **FIXED** | `harness/roster.py:1021-1024` (raw totals now kept from both `_in_window_totals` calls); exit-side note widened `:1085-1119` | `:6065` (enter), `:6104`/`:6118` (exit-side notes) | **RED** | drop both per-window share gates → 2 red; drop the enter one only → 1 red |
| **S2** `_format_share` escalation | **FIXED** | `harness/roster.py:355-378`; `under=True` at exactly the 3 "below/under" call sites (`:911`, `:1116`, `:1261`), default at the 2 "at or above" ones (`:1067`, `:1127`) | `:5801` (extended), `:5816`, `:5846` | **RED** (13 failures across Review5) | revert to round 5 → 6 red; drop the nonzero-not-"0.0" half → 2 red; escalate in the at-or-above direction too → 1 red |
| **S3** `catalogue_seen` age/cap/migrate | **FIXED** (see new finding 1) | `_clean_catalogue_seen` `:678-735`, `_update_catalogue_seen` `:737-782`, `CATALOGUE_SEEN_CAP` `:675`, policy key `evals/roster-policy.yml:144`, DESIGN.md `:353-379` | `:6151`, `:6170`, `:6220`, `:6241`, `:6266` | **RED** (all five) | no age eviction → 2 red; no cap → 1 red; no bare-string migration → 6 red; refresh every entry (not just live api ids) → 2 red |
| **N1** `skill_install_failed` wording | **FIXED** | `harness/run_eval.py:556-557` | `:4844` (covers **both** `FileExistsError` and `NotADirectoryError`) | **RED** | restore `"already exists"` → 1 red |
| **N2** docstring / README / comments / vacuous asserts | **FIXED** | module docstring `harness/roster.py:29-37`; `_clean_models` comment `:502-506`; `_clean_catalogue_seen` comment `:693-696`; `README.md:337-344` (now **eight** causes — I counted `_census_verdict`'s branches: unreadable, absent, future, stale, empty, ranked==0, absolute floor, relative floor = 8) | the two vacuous `assertNotIn(…, summary)` pairs are gone / re-aimed (`test/run_tests.py:5770`) | n/a (docs) | covered by `no_catseen_shape`-style mutations under S3 |
| **N3** O(n²) dedup + cap | **FIXED** (see new findings 4 and 5) | `_clean_previous_arms` `:648-666` (set dedup + `PREVIOUS_ARMS_CAP` `:621`); `catalogue_seen` capped at `:772-780` | `:6266`, `:6289` | **RED** (both) | remove the arms cap → 1 red; remove the catalogue cap → 1 red |
| **N4** migration case in the four caveat sites | **FIXED** | `_is_attributable` `harness/roster.py:334-339`, `usage_share` `:409-413`, `DESIGN.md:353-358`, `evals/roster-policy.yml:56-58` — all four name the migration case, and all four also name S3's second (shape) migration | n/a (docs) | n/a | n/a |
| **N5** unreachable exit-side branch | **FIXED — "make it reachable and pin it", and it says which** | `harness/roster.py:1085-1119`; the comment states plainly that the branch is unreachable under the shipped policy and that `TestIssue67Review6` reaches it with a test-only short-exit policy | `:6104` (absolute floor), `:6118` (relative floor) | absolute-floor test PASSES on `a946c9b` (that branch text predates this round); relative-floor test **RED** | revert the per-window relative gate → the relative-floor test red |
| **N6** `validate_policy` checks `tiers` | **FIXED** | `harness/roster.py:136-140`, helper `_valid_tier_rung` `:106-113` | `:5900` (7 subtests) | **RED** (7 failures) | delete the `tiers` block → 7 red |
| **N7** `:.0f` policy share | **FIXED** | `harness/roster.py:909-913` (`{bar:g}` + `_format_share(pct, bar, under=True)`) | `:6310` | **RED** | revert to `:.2f`/`:.0f` → 1 red |
| **N8** raw `census_at` | **FIXED** (see new finding 3) | `harness/roster.py:1039-1042` | `:6331` | **RED** | publish the raw `generated_at` → 1 red |
| **N9** `SNAPSHOT_SUFFIX` anchor | **FIXED** | `harness/roster.py:75` (`\Z`) | `:6350`, `:6358` | **RED** (both) | `\Z` → `$` → 2 red |
| **N10** split literal | **FIXED** | `test/run_tests.py:5552`, `:5591` — `claude-3-opus-20240229` written plainly, no `+`-concatenation anywhere in the file | n/a | n/a | n/a |

### End-to-end measurements behind the table

**S1** (`$SP/r7work/s1`, the round-6 adversarial census verbatim: `other` at
100,000/wk across the four enter weeks, `claude-sonnet-4-5` at 20 turns in W36,
`claude-opus-4-1` at 1,000,000/wk across the four exit-only weeks — **enter window
raw = 400,020, ranked = 20**):

```
a946c9b : arm claude-sonnet-4-5 | carries 100.0% of rankable census usage over the last 4 weeks
          (at or above the 10% entry bar)          <-- a NON-newest model, seated on 20 turns
a390bc9 : claude-sonnet-4-5 is NOT an arm; arms are the three newest-per-tier models only
```

**S2** (`$SP/r7work/s2`, six censuses through the CLI; the model is a held-over
previous arm so the measured share reaches a published surface):

| true share | `a390bc9` | `a946c9b` |
|---|---|---|
| 1.999 % | `(1.999% of rankable census usage)` | `(2.00% …)` |
| 1.9999 % | `(1.9999% …)` | `(2.00% …)` |
| 0.04 % | `(0.04% …)` | `(0.0% …)` |
| 0.004 % | `(0.004% …)` | `(0.0% …)` |
| exactly 2.00 %, "at or above" direction | `still 2.0% … (at or above the 2% exit bar)` | `still 2.00% …` |
| genuinely 0 | `(0.0% …)` | `(0.0% …)` |

**S3 — the planted-id attack** (`$SP/r7work/s3`, round-6 adversarial finding 2
verbatim: catalogue `{claude-sonnet-4-6 (previous arm, not newest), claude-sonnet-5-0,
claude-opus-4-2}`, census `claude-sonnet-9-9` at 10,000/wk × 8 and
`claude-sonnet-4-6` at 12/wk × 8):

```
CONTROL (clean previous.json), head : retired []  — sonnet-4-6 held over
a946c9b, plant present              : retired [claude-sonnet-4-6 'below the 2% exit bar … (0.1% …)']
                                      catalogue_seen carries claude-sonnet-9-9, forever
a390bc9 run 1 (bare-string plant)   : retired [claude-sonnet-4-6 … (0.1% …)]   <-- same on day 0
a390bc9 chained runs 2 and 3 (previous = the harness's own prior output, attacker does nothing):
      plant entry stays {'id': 'claude-sonnet-9-9', 'last_seen': '2026-09-05'} — NEVER refreshed
a390bc9 with last_seen back-dated 179 days : plant present=True,  retired [claude-sonnet-4-6 …]
a390bc9 with last_seen back-dated 181 days : plant present=False, retired []   <-- arm no longer retired
      stderr: roster: catalogue_seen: dropped 1 entry/entries older than the 180-day window
```

Round 3's own regression-floor id behaves the same way (`$SP/r7work/s3p`,
`proxy-router-claude-sonnet-4-5` at 500/wk × 8, `claude-sonnet-4-5` a previous arm):
clean → `retired []`; fresh plant → `retired [claude-sonnet-4-5 … 0.0% …]`;
plant at 181 days → dropped, `retired []`. The floor is restored on its own.

**S3/N3 — the cap and the cost** (`$SP/r7work/s3cap`, 100,000 entries, end to end
through the CLI):

| input | `a390bc9` | `a946c9b` |
|---|---|---|
| 100,000-entry `catalogue_seen` (dict shape) | **0.43 s**, published 500 entries, 41,639 B, warning `dropped 99503 entry/entries past the 500-entry cap` | — |
| 100,000-entry `catalogue_seen` (bare strings) | **0.34 s**, 500 entries, 41,639 B, migration + cap warnings | **35.02 s**, 100,003 entries, **2,690,676 B**, `warns: []` |
| 100,000-entry `previous.arms` | **0.15 s**, warning `dropped 99500 'arms' entry/entries past the 500-entry cap` | — |

Scaling of `_clean_catalogue_seen` + `_update_catalogue_seen` on head, doubling n:
10k 0.016 s → 20k 0.032 s (1.97×) → 40k 0.065 s (2.05×) → 80k 0.142 s (2.18×) →
160k 0.304 s (2.14×). **Linear, not quadratic.**

**N7 / N8 / N9 end to end** (`$SP/r7work/nits`):

| probe | `a390bc9` | `a946c9b` |
|---|---|---|
| policy `min_ranked_share: 0.005`, census 40 of 100,040 | `(0.04% — under the **0.5%** relative floor)` | `(0.04% — under the **0%** relative floor)` |
| census `generated_at` = `"2026-09-03T00:00:00Z\n"` | `"census_at": "2026-09-03T00:00:00Z"`; summary line intact | `"census_at": "2026-09-03T00:00:00Z\n"`; the summary line is split across two lines mid-sentence |
| census key `claude-sonnet-4-5-20260101\n` at 9800 beside 100 + 100 | `carries **50.0%**` | `carries **99.0%**` |

**Behavioural regression sweep, head vs `a946c9b`.** 14 ordinary scenarios (7 censuses
× 2 catalogues: default / other-heavy / stale / empty / future-dated / dated-snapshot /
exactly-at-the-bar), full published roster compared field by field with
`generated_at` dropped and `catalogue_seen` normalised to a sorted id list.
**12 SAME, 2 DIFF, and both DIFFs are the intended S2 change**: `carries 10.00%` →
`carries 10.0%` at exactly the entry bar in the "at or above" direction. Nothing else
moved.

---

## 4. `.github/workflows/eval.yml`

`git -C /home/user/skills-evals diff d0de00f a390bc9 -- .github/workflows/eval.yml`
→ **0 bytes**, `--stat` empty. `git diff --stat a946c9b a390bc9 -- .github/` → **0 bytes**.
`git diff --name-only a946c9b a390bc9` is exactly six files, none under `.github/`.

Re-asserted independently by `yaml.safe_load` parse (never grep):

| Assertion | Result |
|---|---|
| triggers are `schedule` + `workflow_dispatch` only | **PASS** — parsed `on:` keys = `['schedule', 'workflow_dispatch']` |
| permissions minimal | **PASS** — top-level `{contents: write, id-token: write}`; the single `eval` job declares `None` of its own |
| no `concurrency` on the publishing job | **PASS** — the `eval` job has no `concurrency` block. (There is a *workflow-level* `{group: real-eval, cancel-in-progress: false}`. That is the pre-existing design and is safe here: this workflow has no `pull_request` trigger at all, so it publishes no required status context on a PR head — the fleet rule's whole subject.) |
| every `uses:` a bare 40-hex sha | **PASS** — 7 `uses:`, all matching `^[^@]+@[0-9a-f]{40}$`, none carrying a trailing `#` comment: `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (×4), `actions/setup-node@820762786026740c76f36085b0efc47a31fe5020`, `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97`, `actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |
| no `${{` inside any `run:` | **PASS** — 7 `run:` blocks, 0 offenders |
| the roster step is non-fatal | **PASS** — step 9 `Refresh the model roster`; its `refresh` shell function's failure is branched on (`if refresh; then … else … ::warning::model roster NOT refreshed …`), never propagated, and no `continue-on-error` key is needed |
| push auth is step-local | **PASS** — no top-level `env`, no job-level `env`; `GITHUB_TOKEN` appears in exactly one step, index 12 *"Build the badge over the run window, commit, and push"* |

---

## 5. No model id hard-coded outside fixtures

`TestIssue67.test_no_model_ids_are_hardcoded_outside_fixtures`
(`test/run_tests.py:2190`) is green on head and **still has teeth**. I planted a
commented-out model id into four of the seven files it scans, one at a time, and
restored each time:

| planted into | line | result |
|---|---|---|
| `harness/roster.py` | `# planted claude-opus-4-8 for the guard` | **FAILED (failures=1)** |
| `scripts/refresh_models.py` | `# planted claude-sonnet-5-1 for the guard` | **FAILED (failures=1)** |
| `evals/roster-policy.yml` | `# planted claude-haiku-4-5 for the guard` | **FAILED (failures=1)** |
| `.github/workflows/eval.yml` (in the scratch copy only) | `# planted claude-mythos-5-1 for the guard` | **FAILED (failures=1)** |

N10's plainly-written `claude-3-opus-20240229` is not a dodge: the guard's scan list is
the seven non-test files, and `test/run_tests.py` is not among them.

---

## 6. New findings

**None of these is a repeat of a round-5 or round-6 finding.** Every round-6 blocker,
should-fix and nit is fixed and measured above; the two-strikes rule is not triggered
by anything here. Findings 1-5 are in code written *this round*; finding 2 is the same
*defect class* as round-6's N8 (which is itself fixed) recurring in the new S3 code, and
I say so explicitly below.

### should-fix

**SF1 — the new `catalogue_seen` cap evicts by ALPHABETICAL id, giving an
`eval-results` writer a primitive to DELETE genuine history. `harness/roster.py:772-780`.**

```python
    live       = sorted(i for i in survivors if i in api_id_set)
    historical = sorted(i for i in survivors if i not in api_id_set)
    room       = max(0, CATALOGUE_SEEN_CAP - len(live))
    kept       = live + historical[:room]        # alphabetical head, not newest-first
```

`PREVIOUS_ARM_ID_RE` accepts `^[A-Za-z0-9]`, so `a0000`…`a0499` are valid-shaped and
sort below every `claude-*`. Measured end to end through the CLI (`$SP/r7work/evict`;
catalogue `{claude-sonnet-5, claude-haiku-4-5}`, census
`{claude-opus-4-1: 1000/wk × 8 (a real, since-retired model), claude-sonnet-5: 100/wk × 8}`,
`previous.catalogue_seen` = the real id plus 500 filler ids):

```
CONTROL (history holds only the real id)
  len(catalogue_seen)=3   real since-retired id kept? True
  arm claude-sonnet-5 | newest model in the sonnet tier, 247 days old (past the 7-day cooling-off)

ATTACK (+500 low-sorting filler ids)
  stderr: roster: catalogue_seen: dropped 3 entry/entries past the 500-entry cap
  len(catalogue_seen)=500 real since-retired id kept? FALSE
  arm claude-sonnet-5 | carries 100.0% of rankable census usage over the last 4 weeks
                        (at or above the 10% entry bar)      <-- true share is 800/8800 = 9.09%
```

The 8,000 real turns leave the denominator because the id they belong to was evicted
from history, and the harness publishes a false 100.0%. In a catalogue where the
beneficiary is *not* already newest-in-tier this seats an extra paid arm, and in the
mirror case it retires a held-over arm.

**This is a regression, not a pre-existing defect.** The same input against `a946c9b`
(bare-string shape) does nothing at all: `len=503, real id kept? True`, and
`claude-sonnet-5`'s reason stays `newest model in the sonnet tier`. There was no cap to
exploit before. It is should-fix rather than blocker because it needs `eval-results`
write — the same access round 6 already granted the plant primitive — and because it
self-heals after `catalogue_seen_max_age_days`. But S3 exists precisely to bound what an
untrusted list can do, and its cap hands back a new capability pointing the other way.

*Fix.* Evict the **oldest by `last_seen`** rather than the alphabetical head:
`historical = sorted(survivors_not_live, key=lambda i: (survivors[i], i), reverse=True)`
before the `[:room]` slice. One line, and it makes the cap agree with the age rule
already beside it. A test in the shape of `test_catalogue_seen_caps_length_with_a_count_only_warning`
that asserts a genuinely-recent historical entry outlives 500 stale ones would pin it.

### nits

**N-1 — `last_seen` is republished VERBATIM, including embedded control characters: N8's
own defect class, in the S3 code written to fix it. `harness/roster.py:719-723`.**

`_clean_catalogue_seen` validates with `parse_ts(entry["last_seen"])` — which does
`str(value).strip()` before parsing — but then stores `entry["last_seen"]`, the
**unstripped original**. Measured end to end (`$SP/r7work/ls`, ten hostile `last_seen`
values through `main()`); the published `roster/latest.json` carries:

```
{'id': 'claude-opus-4-1', 'last_seen': '2026-09-01\n'}
{'id': 'claude-opus-4-3', 'last_seen': '2026-09-01T00:00:00Z\r\n'}
{'id': 'claude-opus-4-8', 'last_seen': '\n2026-09-01'}
{'id': 'claude-opus-4-2', 'last_seen': '  2026-09-01  '}
```

Impact is bounded — `json.dump` escapes them, and `catalogue_seen` genuinely does not
reach `render_summary`'s Markdown (N2 established that) — so there is no `::`
workflow-command surface. But it is the one field on the roster that is *not*
normalised where every sibling now is, and the value round-trips off an untrusted
branch into the harness's own output. `::error::`-bearing and NUL-bearing values are
correctly rejected (`skipped 2 … entry/entries`), and a `3000-01-01` value is correctly
clamped to today. *Fix:* store `parsed.strftime("%Y-%m-%d")`, one line, at `:723`.

**N-2 — N8's re-render silently misstates a non-UTC census timestamp.
`harness/roster.py:1041`.** `parse_ts` preserves the offset rather than converting to
UTC, so `strftime("%Y-%m-%dT%H:%M:%SZ")` prints the wall clock and appends a `Z` that
is not true. Measured:

```
input  generated_at = "2026-09-03T00:00:00+05:00"   (i.e. 2026-09-02T19:00:00Z)
a390bc9 publishes    "2026-09-03T00:00:00Z"    <-- five hours out, and it LOOKS canonical
a946c9b published    "2026-09-03T00:00:00+05:00"   (raw, but correct)
```

`scripts/model_usage_census.py:249` writes `%Y-%m-%dT%H:%M:%SZ`, so this only bites on
a hand-edited or third-party census — which is exactly the input class this code path
exists for. *Fix:* `census_at_parsed.astimezone(timezone.utc).strftime(...)`.

**N-3 — the future-`last_seen` clamp has no regression floor.
`harness/roster.py:723`.** `_clean_catalogue_seen`'s docstring calls it out as a
defence ("a single future-dated plant cannot buy itself unlimited immunity from the
age check"), and it is genuinely load-bearing — with the clamp removed, a plant dated
`3000-01-01` is republished as `3000-01-01` and can never age out — but removing it
leaves the suite at **Ran 328 … OK**. Measured both ways above.

**N-4 — the O(1) set dedup has no regression floor either.
`harness/roster.py:655-657`.** Reverting `if entry["id"] not in seen:` to
`if entry["id"] not in ids:` leaves **328 green**, while the same 100,000-entry
`previous.arms` input goes from **0.13 s to 44.40 s** end to end. The 500-entry cap
does not protect it: the cap is applied *after* the dedup loop has already walked every
entry. N3 asked for the set and got it; only the cap and its warning were pinned.

**N-5 — `_clean_previous_arms`'s cap can silently suppress a real retirement report.
`harness/roster.py:663-667`.** Same alphabetical-head shape as SF1. Measured:
a previous roster whose `arms` holds one real arm that has left the catalogue plus 500
low-sorting filler ids publishes `retired_since_last` with 500 filler entries and
**omits the real one** (`real arm claude-opus-4-1 reported retired? False`), against
`True` on the unpadded control. Flagged rather than counted against the worker: the
brief prescribed "500 entries, **sorted head**, count-only warning" in so many words,
so this is the specified behaviour.

**N-6 — "for ONE migration run" is not enforced.
`harness/roster.py:680-683`, `:714-718`.** The docstring says the bare-string shape is
accepted "for ONE migration run", but nothing bounds it: any `previous.json` carrying
bare strings gets `last_seen` = today, on every run, forever. Since the harness only
ever writes the dict shape, a bare string after this merges can only be hand-written —
which grants no capability a re-planted dict entry doesn't already have. It is the
wording that is wrong, not the code.

### Explicitly checked and clean

- Every new warning names a **count only** — no id, no `last_seen` value, no path —
  across the hostile `catalogue_seen`, hostile `arms`, cap and age paths.
- The cap never evicts a live api id: `set(api_ids) <= {e["id"] for e in
  result["catalogue_seen"]}` held in every scenario above, including the 100,000-entry
  and the 500-filler ones, and is pinned at `test/run_tests.py:6037`.
- Published output is deterministic despite `catalogue_seen` becoming a `set`
  internally: `alias_map` iterates `sorted(known)` and `_update_catalogue_seen` returns
  `sorted(kept)`, so no `PYTHONHASHSEED` dependence.
- `_format_share`'s `under=True` is used at exactly the three "below/under" call sites
  and nowhere else — I read all five.
- README's "eight distinct ways" matches `_census_verdict`'s eight non-usable returns
  exactly (I counted the branches).
- All four first-run-caveat sites carry both the migration case and S3's second
  (shape) migration.
- No `__pycache__` was left behind before or after any measurement (the round-4 stale
  `.pyc` trap); every mutation restored and md5-verified.

## What I could not check

- **PR #129's GitHub state** — no network. Nothing here comes from the PR page, its
  checks or CI; everything is local, from `$SP/rev129g-code` and read-only `git`
  against `/home/user/skills-evals`.
- **A live workflow run.** `eval.yml` was asserted by parse and by byte-identity to
  `d0de00f`; I did not dispatch it and never invoked the real `claude` binary.
- **`catalogue_seen` at n = 10⁶.** Measured to 160,000 (0.304 s) and 100,000 end to end
  (0.43 s); the linear fit is from five doublings, not a 10⁶ run.
- **SF1's exploitability against the *real* catalogue's size.** I measured with a
  3-model catalogue, so 500 filler ids suffice; a larger live catalogue needs
  `500 - len(live)` of them, which is still ~490 today.

---

## 7. Tree integrity

`find . -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum | md5sum`,
run in `$SP/rev129g-code`:

| | value |
|---|---|
| **before** any work | `be2711dfc87637b0c46a4210fd58c5d5` |
| **after** all 20 mutations + 4 plants, restored | `be2711dfc87637b0c46a4210fd58c5d5` |

The 79-line per-file manifest `diff`s clean, and each of the nine files I touched or
read closely is md5-equal to `git show a390bc9:<path>`. `/home/user/skills-evals` is
unmodified (`git status --short` empty, HEAD still `527c729`). No background process
was started and `ps -eo pid,etimes,cmd` shows none left. Scratch probes
(`$SP/r7probe`, `$SP/r7probe2`) were removed.
