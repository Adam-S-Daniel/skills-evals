Closes #67.

> **Status (orchestrator, 2026-09-05 22:10 UTC): round 10 (code review plus adversarial, both opus at high, on `e6587f8`; first launched 19:23 and killed by the account's rate limit at 19:42, relaunched 21:08) is NOT CLEAN. Every round-9 item is fixed with teeth and both orchestrator rulings hold. The adversarial half found ONE blocker (the narrowed relevance rule drops a real DATED departed arm whose census usage sits under its bare alias, so 500 filler arms evict it and a false `carries 100.0%` is published where `5d1f00a` publishes the true 33.3%; a regression the fix round had pinned as "the cost"), two should-fix (an empty, absent or padded census hands the cap's order back to the planter-written `last_seen`; route (c2) is dead code and route (a) has no floor) and one nit; the code half found two should-fix (the invariant sentence pinned by no test in either file; route (c2) dead while its docstring and a test comment call it load-bearing). The two-strikes rule fired again (the blocker returns through the brief's own design decision; the floor family for the fourth consecutive round); under Adam's renewed budget that converts into fix round 10, the SECOND of three, dispatched 22:03 to [session_01GaB8jVxurg7Ph4hjEPM38S](https://claude.ai/code/session_01GaB8jVxurg7Ph4hjEPM38S) (Opus 5) with DESIGN DECISION 4 (relevance in three tiers: exact membership; one fold slot per in-window census key; everything else last; in-tier order by census turns, never `last_seen` first; no eviction at all when the census carries no in-window usage). It merges `main` at `d5e06ee` first. Round 11 decides; if it is not clean, fix round 11 is the last of the three. Adam answered "1" on this PR at 17:07 ([comment](https://github.com/Adam-S-Daniel/skills-evals/pull/129#issuecomment-5553410839)); the orchestrator reads that as a fresh budget of three fix rounds, the same unit as his 04:10 authorization, and says so on the [status board](https://github.com/Adam-S-Daniel/skills-evals/issues/126) so he can narrow it.**

## What

Arms pinned `claude-sonnet-5`, judges `claude-opus-4-8`, the preflight `claude-haiku-4-5` — each a literal in its own file, and nothing here noticed when a model shipped or retired. This computes that set instead.

**Availability** — `scripts/refresh_models.py` reads `GET /v1/models` and writes every Claude model with `created_at`, `max_input_tokens`, `max_tokens` and `capabilities`. It uses **the same WIF-derived bearer `eval.yml` already mints** (`ANTHROPIC_AUTH_TOKEN`, exported step-locally); no new credential shape, no stored secret. This is the only network call in the feature.

**Usage** — `scripts/model_usage_census.py` reads Claude Code's local transcripts and emits counts per model id per ISO week for the last 8 weeks. Its output is published on a public branch, so it emits `{model: {week: count}}` and nothing else — no project names, no paths, no prompt or reply text, no session ids, no timestamp finer than a week. It publishes to `eval-results` exactly the way the Tier-3 account audit does, and it is wired into that Routine's live prompt as a best-effort step 6 (`evals/propagation/ROUTINE.md`).

The optional Admin API usage report is **soft**. `ANTHROPIC_ADMIN_KEY` is not provisioned, and its absence prints a `::notice::` naming that exact variable rather than failing the run.

**Policy** — `harness/roster.py` is a pure function over files, thresholds in `evals/roster-policy.yml`:

- an **arm** if it carries >=10% of census usage over 4 weeks, or is the newest model in its tier and past the 7-day cooling-off; a previous arm is held over until it drops under 2% for 8 weeks, and leaves immediately if it disappears from the Models API;
- the **judge** is the most capable available model at least one tier above the strongest arm, never an arm itself;
- the **preflight** is the cheapest available;
- no fresh census (absent, or older than 14 days) → fall back to newest-per-tier and **say so in every arm's reason**.

**No model id appears in `roster.py`, `refresh_models.py`, `model_usage_census.py` or `roster-policy.yml`.** Tier comes from the family word in the model's own id, matched against a ladder that lives in the policy file; `test_no_model_ids_are_hardcoded_outside_fixtures` is the guard. Every roster entry carries its reason in words.

**Consumption** — fixtures' `model:` and `judge.model:` are now overrides. Precedence is `--model` > fixture pin > roster > the CLI's own default. Both existing fixtures keep their pins, with the comment saying why.

**`eval.yml`** gains one small, separate `Refresh the model roster` step and commits `roster/` alongside the badge. The eval step itself is untouched — the roster reaches it through `$EVAL_ROSTER`. Everything lands in `$RUNNER_TEMP`. Previous roster and census come off `eval-results` with `git show`, no checkout. Security posture is unchanged and pinned by a test: schedule + dispatch only, minimal permissions, every `uses:` a bare 40-hex SHA, no `${{ }}` in any `run:` block, push auth still step-local.

## Verifier output

```
$ python3 test/run_tests.py
Ran 122 tests in 3.53s
OK
$ echo $?
0
```

- **Before** (on `main` at `527c729`): 97 tests, exit 0. **After** the first commit: 122. After fix round 6 (`a390bc9`): 328. After fix round 7 (`384396f`, which carries `main` at `a6c882a`): 411, 2 skipped. After fix round 8 (`5d1f00a`, which carries `main` at `8d131bd`, PR #134): 520, 2 skipped. After fix round 9 (`e6587f8`, which carries `main` at `c05d7de`, PR #133): 609, 2 skipped (520 + `main`'s 74 + 15 new).

Covering, red-first, the list in the issue: canned Models API JSON + canned census → the expected arms/judge/preflight with their stated reasons; the 7-day rule; a model missing from the API retired even at 66% usage; the 2%/8-week hysteresis both ways; no census → fallback with the reason saying so; the census privacy guard; the runner taking the roster when the fixture has no `model:` and the pin when it does; the no-hardcoded-ids guard and the `eval.yml` invariants. Fixture transcripts use `example.com`/`example.net`-shaped data only; the suite is hermetic.

## What I could not do

**No dispatch of `eval.yml`.** `eval.yml`'s WIF federation rule pins its `sub` claim to `repo:Adam-S-Daniel/skills-evals:ref:refs/heads/main`, so a dispatch from any other ref gets no bearer and dies at the token-exchange step. **The first real dispatch has to happen on `main` after merge**, and its job summary will carry the computed roster. Expect that first run's summary to read `census none` and every arm's reason to begin "no fresh census (none published)"; the census publishes from the Tier-3 Routine on a durable machine, not from CI.

**Knobs for Adam.** None are required. `ANTHROPIC_ADMIN_KEY` (repository secret) is **optional**: it buys the org-wide Admin API usage report as a second usage signal; without it the run prints a `::notice::` naming it and continues on the census alone. The one manual step outside CI is the Tier-3 Routine's prompt, if the census should flow before the next natural re-read of `ROUTINE.md`.

The ADR recording the policy and its thresholds belongs to #73; `roster-policy.yml` carries a "see ADR (to be written under #73)" placeholder.

## Review rounds (orchestrator notes)

**Round 1** (opus code review at high plus an adversarial opus round, on `dfc8633`, 20:03): NOT CLEAN — 1 blocker (the usage census published any `message.model` value verbatim to a public branch) and 16 distinct should-fix. Fixed across six commits by session_01ChQqSDUctiMBnxyYRU6hKP (Opus 5, which died after pushing) and audited by session_01YJYkyg5HkkayksBcYNUzeG (Sonnet 5), head `f03594f`; verifier 182 tests.

**Round 2** (on `f03594f`, 21:25 to 21:46): NOT CLEAN, no blocker; the round-1 blocker fixed and mutation-verified; 14 of 16 should-fix fixed; two PARTIAL; new should-fix on the all-unrankable census, the fatal preflight, `OverflowError`, the census key allowlist, `roster_models()`; 14 low/nit. Fixed by session_01FKfQmMMCYVU5szmGFd1aSg in 14 commits to `fc5de5c` (22 items).

**Round 3** (on `fc5de5c`, 22:43 to 23:00): NOT CLEAN, no blocker, not a repeat; all eight must-fix items FIXED with teeth; the roster step non-fatal under `bash -e` in five scenarios; eval.yml byte-identical to main. Residual: PyYAML import at census import time; eval.yml's reason extractor; the all-unrankable guard's second route (a proxy alias carrying a family word); unbounded counts; `read_roster`'s path in messages; nits. Verifier 214 tests.

**Reconcile + fix round 3** (session_01G4xaZZJxPf1NjU8eBotDWA, Sonnet 5, 23:02 to 23:39): the first reconcile worker (session_01CLwAUKvUhFB1fZs2H35cVt) stalled on an unanswerable permission prompt for `git commit --amend`; the identity rewrite of the three Opus-authored commits (`b5de547`, `b50d821`, `dfc8633`) was Adam's decision on the status board, and at 15:49 he chose "merge with the commits" (no history rewrite). The replacement worker merged `origin/main` (`af06d0f`, PR #128) in `6895b10` and fixed the eight round-3 items to `d0de00f`. Verifier 282 tests; CI green ([run 33930347756](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33930347756), [run 33930347770](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33930347770)).

**Round 4** (on `d0de00f`, 23:45 to 00:07): NOT CLEAN, no blocker, not a repeat; the merge complete; all eight round-3 items FIXED; eval.yml re-verified. New, all from round 3's `_is_attributable` filter: attribution tests only the alias-folded id (a regression: a 5-turn model "carries 100.0%"); `usage_share`'s docstring vs code on since-retired models; `CENSUS_UNRANKED`'s wrong cause; nits.

**Fix round 4** ([session_01PLKixJErYDbdw4HZJbs5s7](https://claude.ai/code/session_01PLKixJErYDbdw4HZJbs5s7), Sonnet 5, 00:35 to 01:15, $15.56): ten commits `6ec2b08..b743d50`; item 2 by a canonical-id shape route; a `min_ranked_turns` floor. Verifier 296 tests; eval.yml byte-identical to `d0de00f`; CI green ([run 33935434179](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33935434179), [run 33935434171](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33935434171), [run 33935434169](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33935434169)).

**Round 5** (on `b743d50`, 01:32 to 01:56): NOT CLEAN. Nine of ten round-4 items FIXED; item 2 PARTIAL and the shape route unsound (`\d` matches Unicode digits; the legacy `claude-3-5-sonnet-20241022` shape never matches; a plausibly shaped fake is attributed); `previous_arms` never alias-folded (97.09% instead of about 2%); the floor measured over the wrong window and absolute; a hollowed test; nits. Two-strikes ruling: PARTIAL for the first time, one more round; the orchestrator withdrew the shape route in favour of catalogue history (`catalogue_seen`).

**Fix round 5** ([session_01N9sQQ6p6JR2Pq7P9Wvks5R](https://claude.ai/code/session_01N9sQQ6p6JR2Pq7P9Wvks5R), Sonnet 5, 02:28 to 02:58, $10.48): one commit, `a946c9b`. Verifier 307 tests; eval.yml byte-identical to `d0de00f`; CI green ([run 33940402297](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33940402297), [run 33940402330](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33940402330), [run 33940402361](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33940402361)).

**Round 6** (on `a946c9b`, 03:16 to 03:58; sixteen whole-suite mutations, a 26-case hostile-entry matrix, end-to-end `main()` against hostile inputs): NOT CLEAN. Closed with teeth: `_canonical_id_re` gone; `catalogue_seen` published, read back, shape-checked; the legacy-id scenario right; all five proxy aliases unattributable; the per-window absolute floor and the union relative floor; eval.yml byte-identical. **The previous-arm alias miss unchanged in production** (`compute_roster` builds the usage alias map from `api_ids + counts` only; `claude-sonnet-5` still at "carries 97.1%"), the certifying test hollow. New: the relative floor union-only; a planted `catalogue_seen` id retires a real arm and is republished forever with no eviction, TTL or cap; O(n²) dedup; nits. **Two-strikes ruling: PARKED ON ADAM at 04:05**, un-parked 04:10 by Adam's authorization ("I authorize 3 additional rounds for PR 132 and pre-emptively for any (each) additional PR that needs them"). Fix round 6 is the first of this PR's three.

**Fix round 6** ([session_01TYEc6RntpYzvsvutdSBc1f](https://claude.ai/code/session_01TYEc6RntpYzvsvutdSBc1f), Sonnet 5, 04:20 to 05:09, $20.55): fifteen commits `146e528..a390bc9`, one per item (B1: the usage alias map widened to previous arms and `catalogue_seen`; B2: two dead `_is_attributable` clauses deleted; S1: the relative floor per window; S2: `_format_share` escalates past two decimals; S3: `catalogue_seen` entries carry `last_seen`, age out after 180 days, capped at 500, bare strings migrated on read; N1 to N10). Verifier 328 tests; `af06d0f` an ancestor. No CI on `a390bc9` (the branch conflicted with `main` in `test/run_tests.py` since PR #137 landed); the last CI was on `7d735d5` ([run 33945809347](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33945809347), [run 33945809356](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33945809356)).

**Round 7** (scoped code review at high plus an adversarial round, both on `a390bc9`; first launched 05:17 and killed by the account's five-hour rate limit, relaunched 10:55, reports at 11:27 and 11:34): NOT CLEAN, **not a repeat**: every one of the fifteen round-6 items FIXED through the production entry point. The code reviewer reproduced round 6's production case through `roster.py main()` with files on disk: head publishes `claude-sonnet-5` at **1.96%**, `a946c9b` at 97.1%; the pinning test drives `compute_roster` and is red on `a946c9b`. The per-window floor holds; `_format_share` renders 1.999% and 0.04% as themselves; the planted `catalogue_seen` id ages out at 181 days; 100,000 entries in 0.43 s, linear. eval.yml byte-identical to `d0de00f`. New, all introduced by this round's own fixes: **(blocker, adversarial)** the widened usage alias map is also used for a model's own numerator target, so two dated snapshots of one base with the bare alias only in history each collect the other's turns and are published "carries 100.0%" (one carries 0.99%), a zero-usage previous arm is kept, and the extra seat makes the judge an arm so `select_models` refuses every unpinned fixture; reproducible from the harness's own two-run chain; `a946c9b` seated only the newer snapshot at 99.0%. (should-fix) the 500-entry `catalogue_seen` cap evicts by alphabetical id, so 500 low-sorting valid ids delete a real since-retired model from history (a regression), and `roster-policy.yml` describes an order the code does not implement; four of S3's own defences can each be deleted with the suite green; the previous-arms cap can omit a real retirement. Nits: `last_seen` republished verbatim with control characters; `census_at` re-rendered with a `Z` without converting an offset to UTC; the `:.6g` fallback re-prints the bar at 1.9999999; a 100k-deep JSON still tracebacks (pre-existing); "for ONE migration run" enforced by nothing; a plant's retirement outlives the plant. The adversarial reviewer also corrected a premise: the roster step's `refresh()` exports the WIF bearer for `refresh_models.py`, and `roster.py` runs in the same shell, so the bearer is in its environment; `roster.py` never reads the environment and prints only the summary.

**Fix round 7** ([session_01WYfjzWW4YaYLn2eyZs2zhV](https://claude.ai/code/session_01WYfjzWW4YaYLn2eyZs2zhV), Opus 5 with the chunk rule, 11:35 to 12:04, $15.07; the second of Adam's three authorized rounds; the model went up because attribution had failed on reasoning in three consecutive rounds): ten commits `cbdcaa1..384396f`: the merge of `main` (`cbdcaa1`, at `a6c882a`, PR #137; the `test/run_tests.py` conflict resolved by keeping both appended sides), then `0f32c06` (B1, the orchestrator's design decision: a live catalogue id is never re-targeted by the wide usage map; its numerator target comes from the catalogue-only seat map, and the wide map folds only non-catalogue ids and census keys), `67fd22b` (S2: the `catalogue_seen` cap evicts the oldest by `last_seen`), `4e32be5` (S3: the previous-arms cap keeps real retirements over filler), `11b741c` (S1: regression floors for the four `catalogue_seen` defences), `a790273` (N1), `fd0ad0e` (N2), `11d5760` (N3), `bbb618d` (N4), `384396f` (N5 to N8); noreply identity. The worker flagged S1 and N3 for the orchestrator's attention in its closing summary; the round-8 code reviewer read both commits and ruled each flag right (S1's floors cannot be red on a commit where the code is already correct, so the named mutations are the evidence, and all four are red; N3's cheaper fixture exhibits the identical `:.6g` defect and the brief's own 13-model case was also driven through `main()` and renders distinguishably). Verifier re-run by the orchestrator in a fresh worktree of `384396f` at 13:02: `python3 test/run_tests.py` exit 0, 411 tests, 2 skipped (328 before; `main`'s 60 folded in); `python3 test/test_propagation.py` exit 0, 164 (1 skipped); `evals/workflow-path-audit --arm objective-only` exit 1 with per-check outcomes identical to `origin/main`; every other fixture identical per check; input fingerprints unchanged; `main` an ancestor; `.github/` differs from `main` only by this PR's own roster step (round 8 asserted `git diff a390bc9 384396f -- .github/` empty). CI on `384396f`, the first on a current head since 04:55: every check run success or skipped ([run 33964822828](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33964822828), [run 33964822851](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33964822851), [run 33964822822](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33964822822)); combined status pending over zero statuses.

**Round 8** (scoped code review at high, 13:05 to 13:31, plus an adversarial round, 13:04 to 13:45, both opus, on `384396f`; every scenario through `roster.py`'s real CLI with files on disk; hollowness against `a390bc9`; 22 code-review mutations all red; 44 adversarial attacks; a 3,000-scenario differential fuzz): NOT CLEAN. **Round-7 B1 FIXED with teeth**: both two-snapshot cases and the organic two-run chain seat only the newer snapshot at 99.0%; the zero-usage arm retires at 0.0%; `select_models` picks a judge that is not an arm; round 6's production case still publishes 1.96%; numerator disjointness holds over 4,000 random colliding-base catalogues (0 overlaps; 67 on `a390bc9`); the property test is red on `a390bc9` and red under the single-wide-map mutation. All fifteen round-7 items FIXED and killed by their tests; the 24-scenario sweep is byte-identical to `a390bc9`; hostile inputs stay count-only; `.github/` untouched. New: **(blocker, adversarial; introduced by the B1 fix)** the usage alias map is not composed: a census key two hops from a live model (dated id → bare alias → live snapshot) folds once onto the bare alias, which is in `catalogue_seen`, so it lands in the denominator and in no numerator; in the harness's own organic two-run chain a model carrying 94.3% is not seated at all (`a390bc9` seats it), and as a previous arm it is retired with the published sentence "below the 2% exit bar … (0.0% of rankable census usage)"; 12 of 3,000 random catalogues carry orphaned turns (0 on `a390bc9`); the shipped property test asserts only `sum(shares) <= 100` and cannot see turns lost from every numerator. **(should-fix, both reviewers; a repeat of round-7 SF1 at the same severity, reached through the brief's own prescribed remedy)** the `catalogue_seen` cap's new age order is a key the planter controls: 498 entries dated today, or 500 bare strings (the migration path stamps today on each), still evict the real since-retired id and still publish "carries 100.0%" for a true 9.09%, and on the first production run after merge every bare-string entry carries the same date so pure id order decides, round 7's defect verbatim. (should-fix, adversarial; introduced by the N1 fix) `strftime("%Y-%m-%d")` does not zero-pad a year below 1000, so `last_seen: 0001-01-01` is republished as `1-01-01`, which `parse_ts` cannot read and the cap then treats as seen today; 500 such plants evict the real history where `a390bc9` dropped all 500. (should-fix, adversarial; a repeat of round 7's "no regression floor" should-fix on this round's own code) six of round 7's new defences can each be mutated with the suite green, including the B1 acceptance criterion itself (iterating `live_order` in reverse seats the OLDER snapshot at 87.1%). Nits: `last_seen` rendered on the offset's local date, not UTC (the mirror of N2); the previous-arms cap still hides a real retirement for a departed arm with zero census turns (the half of round-7 N-5 the chosen remedy could not reach); `:.17g` publishes 17 digits of float noise; two cosmetic PEP 8 slips. **Two-strikes ruling: fired a third time on this PR (the cap repeat and the regression-floor repeat), converted to Adam's budget: fix round 8 is the third and last authorized round; if round 9 is not clean the PR parks for Adam.**

**Fix round 8** ([session_01RUkR8RdYTmFXC9uRXagPNr](https://claude.ai/code/session_01RUkR8RdYTmFXC9uRXagPNr), Opus 5 with the chunk rule, 13:48 to 14:35, $27.08; the last of Adam's three): nine commits `d92931a..5d1f00a`, one per item: `d92931a` (A1: the usage alias map composed so a two-hop census key is credited), `582d215` (A2: `last_seen` published as a date this module can read back), `55df40e` (F1: the `catalogue_seen` cap ordered by data the previous roster cannot write, census-named entries first), `14773a9` (A3: regression floors for the defences round 7 introduced), `08b147c` (F3: retirements reported before the previous-arms cap, not after), `3858582` (F2: the UTC conversion of `last_seen` pinned), `683b486` (F4: the last share rung rendered with `repr`), `d346a5e` (F3: the uncapped retirement report's cost recorded), and the merge of `main` (`5d1f00a`, at `8d131bd`, PR #134). The worker's closing state: 14 mutations red, the unmutated suite green, the roster deterministic across `PYTHONHASHSEED` values. All noreply identity. Verifier re-run by the orchestrator in a fresh worktree of `5d1f00a` at 15:14: `python3 test/run_tests.py` exit 0, 520 tests, 2 skipped (411 before; `main`'s 88 folded in; 21 new); `python3 test/test_propagation.py` exit 0, 164 (1 skipped); every fixture under `evals/` (including `post-failure-comment`, new on both sides) identical per check to `origin/main`; input fingerprints unchanged; `.github/` unchanged this round (`git diff --stat 384396f..5d1f00a -- .github/` empty; against `main` the diff is this PR's own roster step); `main` (`8d131bd`) an ancestor and the merge clean. CI on `5d1f00a`: every check run success or skipped ([run 33972211179](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33972211179), [run 33972211183](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33972211183), [run 33972211181](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33972211181)); combined status pending over zero statuses.

**Round 9** (scoped code review at high, 15:51 to 16:26, plus an adversarial round, 15:51 to 16:33, both opus, on `5d1f00a`; hollowness against `384396f`; every scenario through `roster.py`'s real CLI with files on disk; 17 code-review mutations, 16 red and the one survivor proved an equivalent mutant by instrumentation; a 3,000-scenario property fuzz with zero violations on head against 516 on `384396f`; the 24-scenario sweep byte-identical to `384396f`; the merge of `main` AST-compared and shown to lose no symbol, test or `CHECKS` key): NOT CLEAN. **Every round-8 item FIXED with teeth**: A1 composed (the organic two-run chain seats `claude-haiku-4-20260601` at 94.3%; the two-hop previous arm carries 94.3% instead of retiring at 0.0%; 0 of 3,000 random catalogues orphan a turn, 12 before); A2 and F2 (`0001-01-01` dropped as older than the window; 500 such plants drop and the real id stays; every published `last_seen` round-trips and is a UTC date); F1 as filed (500 plants dated today, bare strings, high- or low-sorting, all keep the real id; `count_keys` threaded as a parameter; the policy text pinned); A3 (five of six defences pinned; the sixth is an equivalent mutant, unreachable once `_clean_catalogue_seen` re-renders every date); F3 (a zero-turn departed arm is reported retired among 500 fillers; the uncapped report's cost measured at 97 MB / 65 MB for a million planted arms, exactly as the code's note records); F4 (the brief's own case renders `1.99999999%`); F5. New: **(blocker, adversarial; a same-defect REPEAT of round 8's should-fix, at the severity this round's rubric assigns a plant that evicts real history)** `_census_relevance`'s third route decides "census-named" by SPELLING: `SNAPSHOT_SUFFIX` wants eight digits, not a date, so whoever writes `previous.json` and knows one census key (every live model id is one, and all three inputs are public on `eval-results`) mints `claude-sonnet-5-00000000` … `-00000499`, and those 500 plants head the census-named group, evict the real since-retired id and publish "carries 100.0%" for a true 9.09% — permanently (run 2 reads run 1's own published roster and still publishes it); the same route on the previous-arms cap publishes "carries 80.0%" for 8.89%; two properties written this round (`roster.py:1051-1057`, `roster-policy.yml:138-141`: "who survives is decided by data the previous roster does not control") do not hold. Round 6 keyed the cap on the id, round 7 on `last_seen`, round 8 on a predicate over the id — each on something the planter writes. **(should-fix, both reviewers; NEW, introduced by round 8's A2/F2 fix)** `_as_date` raises an uncaught `OverflowError` on a `last_seen` of `0001-01-01T00:00:00+05:00` (any positive offset at the year-1 boundary): `roster.py` exits 1 with a traceback carrying the runner's absolute paths and publishes NO roster, where both `384396f` and `a390bc9` complete; eval.yml turns the non-zero exit into a `::warning::` and the eval runs on the fixture pins, but no roster publishes on any later run until `eval-results` is edited by hand — one `catalogue_seen` entry disables the feature; the fix is two lines (catch, count, skip) and a test through `main()`. **(should-fix, adversarial; a REPEAT of round 8's A3 and round 7's S3 finding, the third consecutive round)** two of this round's own defences have no regression floor: the alias composition's chain length (a `while` → `if` mutation loses a three-hop census key with the suite 520/520 green) and the `carried_arms` cap (`return ids, ids` leaves the suite green, including `test_the_cap_still_bounds_what_is_carried_forward`, whose assertions read the uncapped list). Nits: the test file names a regression floor for A3's sixth defence that nothing pins (an equivalent mutant; reword); F3's cost note omits the two surfaces the sizes land on (GitHub's 1 MiB step-summary cap, crossed at about 16,000 planted arms; the 100 MB push limit, at about a million); a very small share renders as `1e-09%` inside a human-facing reason (pre-existing). **Two-strikes ruling: fired a FOURTH time on this PR (the cap repeat and the regression-floor repeat); Adam's three authorized rounds were spent. PARKED ON ADAM 16:45 to 17:07.**

## What Adam decided

The PR was parked at 16:45 with three options (authorize further fix rounds / merge as-is with the hole recorded / descope the survivor-ordering guarantee), in [this comment](https://github.com/Adam-S-Daniel/skills-evals/pull/129#issuecomment-5553306055). Adam answered "1" at 17:07 ([comment](https://github.com/Adam-S-Daniel/skills-evals/pull/129#issuecomment-5553410839)): further fix rounds. The orchestrator reads that as a fresh budget of three, the same unit as his 04:10 authorization, and records it on the status board so he can narrow it.

**Fix round 9** ([session_01J5iLLj3g4BsQoqAHsHSCup](https://claude.ai/code/session_01J5iLLj3g4BsQoqAHsHSCup), Opus 5 with the chunk rule, 17:27 to 18:28, $24.24; the first of the renewed three): merges `main` (`c05d7de`, PR #133) first; B1 by the orchestrator's design decision — `_census_relevance` decides "census-named" only by exact membership (the entry's id is a census key, or a live catalogue id, or maps to one through the alias map the catalogue and census produce), with no spelling route, and the same rule on the previous-arms cap; the 500-plant scenario of round 9 pinned through `main()` with files on disk on both caps; S1 the `OverflowError` caught, counted and skipped, tested through `main()`; S2 regression floors for the alias composition's chain length (a three-hop key) and the `carried_arms` cap; N1 to N3 (the reworded comment, the two cost surfaces named, no scientific notation in a reason). Nine commits `fc71156..e6587f8`, one per item, noreply identity; the worker's own verifier record follows below. Verifier re-run by the orchestrator in a fresh worktree of `e6587f8` at 18:58: `python3 test/run_tests.py` exit 0, 609 tests, 2 skipped; `python3 test/test_propagation.py` exit 0, 164 (1 skipped); every fixture identical per check to `main` at `c05d7de`; input fingerprints unchanged; `.github/` unchanged since `5d1f00a`; `c05d7de` an ancestor; the branch conflicts with `main` since PR #135 (`f82bd77`). CI on `e6587f8`: every check run success or skipped ([run 33983830565](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33983830565), [run 33983830581](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/33983830581)); combined status pending over zero statuses. The worker's two flagged judgment calls, ruled: keeping the census-derived route (c1) `named_bases` was accepted (a planter cannot add a census key); landing the missed comment as `e9e8c02` instead of amending `1750407` is right.

**Round 10** (scoped code review at high, 21:08 to 21:43, plus an adversarial round, 21:08 to 21:58, both opus, on `e6587f8`; a first attempt at 19:23 was killed by the account's rate limit with no report; hollowness against `5d1f00a`; every scenario through `roster.py`'s real CLI with files on disk; 18 code-review mutations, 15 red; 24 adversarial mutations; an independent 1,200-scenario property from the design decision with 0 violations against 883 on `5d1f00a`; a 72-scenario sweep and a 3,000-scenario differential byte-identical to `5d1f00a` where the caps do not fire; the merge `fc71156` the exact union by AST): NOT CLEAN. **Every round-9 item FIXED with teeth**: B1 as filed (rows A, B, C, the permanence run and the arms cap all keep the real id and publish 9.1% / 8.9% where `5d1f00a` published 100.0% / 80.0%; the A1 chain still 94.3%; the property test red on `5d1f00a`); S1 (the three year-1 stamps → rc 0, the roster published, one count-only warning, no traceback); S2a and S2b (their named mutations red); N1 to N3 (N3 measured end to end: `under 0.000001%` where `5d1f00a` published `4.16667e-07%`). Both orchestrator rulings hold: `named_bases` is built from the census keys and the live catalogue before `previous.json` is read, five planted `previous.json` shapes change nothing, and the mutation that feeds entries into relevance is red; `e9e8c02` is AST-identical to its parent. New: **(blocker, adversarial; a regression against `5d1f00a`, reached through the brief's own design decision)** a DATED departed arm whose census usage is recorded under its UNDATED alias (previous arm `claude-haiku-4-20250101`, census key `claude-haiku-4` with 8,000 turns beside `claude-sonnet-5` with 4,000) is no longer relevant — route (c) maps census key → base, never entry → census key — so 500 `0filler-NNNN` arms evict it from `carried_arms` and head publishes `claude-sonnet-5 carries 100.0%` where `5d1f00a` publishes the true 33.3%; round 8's own 3,000-scenario generator with the caps forced gives 6 scenarios that differ and 11 shares higher on head, 0 lower; 74 of 3,000 scenarios have an id narrowed and 7 of those are load-bearing; the invariant sentence fails in that direction; the fix round had pinned this outcome as "the cost" in `test_a_dated_arm_gets_no_relevance_from_its_own_spelling`. Restoring the spelling route re-opens round 9's blocker (its mutation red 4), so that is not the fix; the reviewer's row D (500 plants folding onto the census key beside the fillers leave 33.3% correct) shows attribution reads the fold set, not which entry produced it. **(should-fix, adversarial; pre-existing on `5d1f00a`; the same family as round 7's S2 and round 8's F1)** with the census absent, `counts: {}`, `counts: []`, or padded with 600 keys carrying only out-of-window turns (the plants named after them), relevance has no signal and the cap orders by the planter-written `last_seen`: 500 plants evict the 8,000-turn victim in run 1 and run 2 publishes `carries 100.0%` for 9.09%, permanently; `census.json` comes off the same `eval-results` branch as `previous.json`, and `git show … || true` leaves it empty before the census has ever run. **(should-fix, both reviewers; a REPEAT — the fourth consecutive round of a defence without a regression floor)** route (c2) of the new predicate is provably dead (c2 implies a, b or c1; 0 fires in 6,000,000 evaluations and 5,000 scenarios; dropping it alone leaves the suite green) while the docstring, `roster-policy.yml` and the test's "Mutation check (manual)" comment call it load-bearing; route (a) has no floor either (dropping it alone is green; (a) and (c2) mask each other). **(should-fix, code)** the invariant sentence is present in both files and pinned by no test: deleting it from `roster-policy.yml` or from the cap's comment leaves 609 green. Nits: three green mutations unreachable by construction (only one documented); one stale docstring word. **Two-strikes ruling: the blocker returns through the brief's own DESIGN DECISION 3 and the floor family returns for the fourth round, so the rule fires again on this PR; under Adam's renewed authorization it converts into fix round 10, the SECOND of three; fix round 11 would be the last.**

**Fix round 10** ([session_01GaB8jVxurg7Ph4hjEPM38S](https://claude.ai/code/session_01GaB8jVxurg7Ph4hjEPM38S), Opus 5 with the chunk rule, dispatched 22:03; the second of the renewed three): merges `main` (`d5e06ee`, PRs #132 and #135) first; B1' by DESIGN DECISION 4 — relevance in three tiers from data the previous roster does not write: tier 1 exact membership (a census key with in-window turns, or a live catalogue id); tier 2 one fold slot per in-window census key that has no tier-1 entry in its fold group (`fold(x)` = the production alias map applied to the id with one trailing eight-digit date suffix stripped; the smallest id wins the slot, and a planter who wins it leaves the key attributable through the plant, so no published share changes); tier 3 everything else, after every tier-1 and tier-2 entry; in-tier order by census turns descending then id, `last_seen` only after both; the invariant "every census key with in-window turns that any entry folds onto keeps at least one entry that folds onto it, and an entry that neither the live catalogue nor the census names, under any spelling, never outranks one that either names" stated and pinned in both files; the blocker's rows, the two fuzz scenarios, round 9's rows and the A1 chain all through `main()`; the property generator rewritten to exercise `arms` and the blocker's shape; the forced-cap differential against `5d1f00a` (expect 0 shares higher). A: a census key with zero in-window turns names nothing; when the census names nothing the caps do not evict (count-only warning; the F3 size ceiling as the only bound). F-1: the sentence pinned in both files. F-2: (c2) deleted with its prose; every remaining predicate clause has a named red mutation or is deleted. N-1: the unreachable mutations documented.

**Round 11** (code review plus adversarial, both opus, on the fix-10 head; hollowness against `e6587f8`): decides. CLEAN merges after a fresh verification and a CI read on the head (the branch will carry `d5e06ee`); NOT CLEAN gets fix round 11, the last of the three, after which the PR parks for Adam.

### Fix round 10 — verifier output (worker)

Seven commits, `5712522..1fa9d3a`, one per item plus a cosmetic tail, all plain pushes on
`claude/skills-evals-67`; `git merge-base --is-ancestor <sha> origin/claude/skills-evals-67`
verified for each.

| Commit | Item |
|---|---|
| `5712522` | merge of `origin/main` (`d5e06ee`, PRs #132 and #135) |
| `5ecab6b` | **B1'** — relevance reads the FOLD SET, not the entry that produced it |
| `30eac91` | **A** — a census that names nothing gives the caps no order, so they do not evict |
| `fd7214a` | **F-1** — the invariant sentence pinned in both files, every copy load-bearing |
| `431069e` | **F-2** — every clause of the relevance machinery has a red mutation, or is gone |
| `d72b868` | **N-1** — an unreachable catch narrowed instead of documented |
| `1fa9d3a` | style — the needless `\'` escapes this round's prose picked up (no behaviour change; every docstring already read correctly at runtime) |

**Suite.** `python3 test/run_tests.py` exit 0 throughout:

- after the merge (baseline): **818 tests, 3 skipped** — the predicted
  609 + (588 − 379). The brief's "2 skipped" was the branch's own count;
  `main` at `d5e06ee` runs 588 with **3** skipped in this container (the
  cross-repo `registries.yml` check plus two pypdf-dependent `TestIssue82`
  cases), and 3 is the union.
- at the end: **836 tests, 3 skipped**, exit 0 (+18 this round, one test
  retired).

`python3 test/test_propagation.py` exit 0, **164 tests, 1 skipped**, after
the merge and at the end.

**Fixtures.** `python3 harness/run_eval.py <fixture> --arm objective-only`
for all **nine** directories under `evals/` (two new on `main` this round),
on the final tree and on a plain export of `origin/main` — identical per
check everywhere. This PR adds no fixture.

```
disarm-inherited-reach     rc=1 IDENTICAL   propagation                rc=2 IDENTICAL
github-actions-sha-pinning rc=1 IDENTICAL   rename-pdfs                rc=1 IDENTICAL
guidance-bridge-canary     rc=2 IDENTICAL   review-bash-ci-reliability rc=1 IDENTICAL
post-failure-comment       rc=1 IDENTICAL   windows-elevation-from-wsl rc=1 IDENTICAL
workflow-path-audit        rc=1 IDENTICAL
```

**The merge.** `objective.py` is `main`'s verbatim (`git diff origin/main`
empty). `run_eval.py` carries both sides — `main`'s `run_setup` with both
call sites and this PR's roster-aware `select_models` — and every top-level
symbol of both (31 = the union, nothing dropped or duplicated by AST).
`test/run_tests.py` carries every class from both sides: 34 ours + 29
theirs = **39 distinct**, none missing, none duplicated. `DESIGN.md` and
`README.md` are the union.

One test needed a one-line change for a real semantic interaction, not a
textual conflict: `main`'s
`SetupHookTests::test_run_arm_short_circuits_before_the_agent_on_a_failing_setup`
calls `_run_arm` with a fixture pinning no model, and this PR's
`select_models` fails closed there, so the model-selection error
short-circuited the arm ahead of the `setup:` the test exists to exercise.
The fixture now pins `model:`, which (with the test's existing
`no_judge=True`) makes `select_models` return without reading a roster.

**`.github/` untouched:** `git diff --stat 5d1f00a..HEAD -- .github/` is
empty.

**`test_no_model_ids_are_hardcoded_outside_fixtures`:** green.

**Deterministic across `PYTHONHASHSEED`:** the B1' rows and the A rows,
through `roster.py`'s CLI at seeds 0, 1 and 42 — byte-identical output at
each (`md5 d3a21faa92f0…` and `0940baeefa50…`, three times each).

#### B1' — DESIGN DECISION 4, measured through `main()` with files on disk

`fold(x)` is the production alias map — built from the live catalogue and
the IN-WINDOW census keys alone — applied to `base(x)`, which strips one
trailing `-DDDDDDDD`. Relevance is three tiers: **tier 1** the id is an
in-window census key or a live catalogue id; **tier 2** one slot per census
key with in-window turns that no tier-1 entry of the list being capped
folds onto, taken by the smallest id in that key's fold group; **tier 3**
everything else, after both. Within a tier: census in-window turns
descending (the group's, for tier 2), then id. `last_seen` is out of the
order entirely, and `_LAST_SEEN_FLOOR` with it.

Every row: catalogue of two live models, census
`{claude-haiku-4: 8000, claude-sonnet-5: 4000}` (true share for
`claude-sonnet-5` = 4000/12000 = **33.3%**), previous arm
`claude-haiku-4-20250101` — a DATED arm whose usage the census records
under its UNDATED alias — and a test-only 0% entry bar. "Pre-fix" is the
post-merge tree `5712522`; "after" is `d72b868`. `5d1f00a` is the
pre-round-9 head the blocker measured the regression against.

| Row | fillers | `5d1f00a` | pre-fix `5712522` | **after** |
|---|---|---|---|---|
| control | none | carries 33.3% | carries 33.3% | **carries 33.3%** |
| A | 500 `0filler-NNNN` | carries 33.3% | **carries 100.0%** | **carries 33.3%** |
| B | 500 `zfiller-NNNN` | carries 33.3% | carries 33.3% | **carries 33.3%** |
| D | 500 `claude-haiku-4-000000NN` | carries 33.3% | carries 33.3% | **carries 33.3%** |
| E | 498 `0filler-NNNN` (under the cap) | carries 33.3% | carries 33.3% | **carries 33.3%** |

Row B is the control that shows the id order alone was what spared the arm
before; row D is the tier-2 slot's own cost — the smallest plant WINS the
slot and the real arm is capped out, and nothing moves, because the plant
folds onto the same census key.

The two worst scenarios the round-10 reviewer found by re-running round 8's
generator with the caps forced, restated with round numbers:

| Scenario | true | `5d1f00a` | pre-fix | **after** |
|---|---|---|---|---|
| api `[claude-haiku-5]`, census `claude-fable-5`, arm `claude-fable-5-20250101` | 2990/10000 = 29.9% | 29.9% | **100.0%** | **29.9%** |
| api `[claude-fable-4-20250101, claude-sonnet-4]`, census `claude-opus-5`, arm `claude-opus-5-20260601` | 493/1000 = 49.3% | 49.3% | **100.0%** | **49.3%** |

**Nothing round 9 won is given back.** All through `main()` on the final
head, published sentence in each:

| Row | outcome |
|---|---|
| R9 A — 500 `claude-sonnet-5-000000NN` | real id kept, `carries 9.1%`, `|catalogue_seen| = 500` |
| R9 B — the same as bare strings | real id kept, `carries 9.1%` |
| R9 C — 500 `claude-sonnet-4-9-000000NN` (the victim's own id) | real id kept, `carries 9.1%` |
| R9 D — 500 `0plant-NNNN` | real id kept, `carries 9.1%` |
| R8 F1-a — 500 `zplant-NNN` dated today | real id kept, `carries 9.1%` |
| R8 F1-b — the same as bare strings | real id kept, `carries 9.1%` |
| permanence — run 2 from run 1's own roster | real id kept in both, run 2 `carries 9.1%` |
| arms cap — 500 `claude-haiku-4-5-000000NN` | `carries 8.9%` (800/9000) |
| A1 organic chain, cap firing | bare alias kept, `claude-haiku-4-20260601: carries 94.3%` |
| three-hop chain, two runs | run 2 `claude-haiku-4-20260601: carries 94.3%` |

Full sentence in the 9.1% rows:
`carries 9.1% of rankable census usage over the last 4 weeks (at or above the 0% entry bar)`.

**The forced-cap differential.** Round 8's `_random_scenario`, 3,000
scenarios, 500 filler arms and 500 filler history entries each, plus the
blocker's own shape (a family the census names bare whose only entry is a
DATED previous arm, deliberately absent from `catalogue_seen` — round 8's
generator never produced it, which is why the reviewer had to add it):

| Candidate vs `5d1f00a` | scenarios differing | shares HIGHER | lower |
|---|---|---|---|
| pre-fix `5712522` | **933 of 3000** | **2028** | 0 |
| **`d72b868`** | **0 of 3000** | **0** | **0** |

The 72-scenario sweep with the caps NOT firing is byte-identical across
`5d1f00a`, the pre-fix head and this one.

**The property test, rewritten.** Its generator now fills
`previous["arms"]` as well as `catalogue_seen` (round 9's left `arms`
empty in every scenario, so the arms cap was never exercised by it),
generates dated spellings of census keys as REAL history and REAL arms as
well as plants, and plants a full cap's worth of ids that sort ahead of
every `claude-` id. It asserts BOTH halves of the invariant: half two
directly (every entry the census names outright survives), half one
through the only consequence that matters (every published share equals
the turns that model really carries, from the generator's own `owner`
map). 3 seeds × 400 = **1,200 scenarios green here, red in all 1,200 on
the post-merge tree**.

#### A — a census that names nothing gives the caps no order

Pre-existing on `5d1f00a`, and reachable with no hostile census at all:
`eval.yml` materializes `census.json` with `git show … || true`, which
leaves an EMPTY file before the census job has ever run. Measured through
`main()` twice over — run 1 with the broken census, run 2 from run 1's own
roster with a healthy one (true share 800/8800 = 9.09%, under the 10% entry
bar):

| Run-1 census | `5d1f00a` / pre-fix: victim survives run 1 | run 2 | **after: survives** | **run 2** |
|---|---|---|---|---|
| absent (`--census` omitted) | no | carries 100.0% | **yes** | **newest model in the sonnet tier** |
| `counts: {}` | no | carries 100.0% | **yes** | **newest model in the sonnet tier** |
| `counts: []` (wrong type) | no | carries 100.0% | **yes** | **newest model in the sonnet tier** |
| padded: 600 keys, every turn out of window | no | carries 100.0% | **yes** | **newest model in the sonnet tier** |
| control: the census names the victim | yes | newest model in the sonnet tier | yes | newest model in the sonnet tier |

The rule, in three parts: a census key with ZERO in-window turns names
nothing; when the census names nothing at all neither cap evicts, with one
count-only warning
(`roster: census carries no in-window usage; catalogue_seen and arms carried uncapped (503 entries)`);
and past `UNCAPPED_CARRY_CEILING` = **10,000 per list** the run refuses to
publish — rc **4**, one named line, counts only, no traceback, nothing
written, so the last good roster stands. The ceiling stops short of both
costs F3 measured: at the ceiling with both lists full, a **1.61 MB**
`roster/latest.json` and a **0.60 MB** step summary in 0.17s, inside
GitHub's 1 MiB summary cap and two orders of magnitude inside its 100 MB
file limit.

**The 601-key row, measured rather than asserted from the design:** a
census naming 601 ids all in history, the victim with 8,000 turns against
600 keys carrying 3 each. All 601 are tier 1, so the turn order inside the
tier is the whole answer — the victim heads it, **497 of the 600** low-turn
keys are kept and **103** dropped, `|catalogue_seen| = 500`.

Five existing tests reached their cap through a `census=None` that now
names nothing; each is given a census that names something the entries in
it do not relate to, because the bound they are about is the one that
applies when the census CAN order the entries. A sixth,
`test_a_live_previous_arm_survives_the_cap_and_is_held_over`, gets a census
the cap can order by but the POLICY cannot rank, which is what keeps its
"no evidence to retire it" assertion measuring what it means to.

#### F-1 — the invariant sentence, pinned

The sentence, verbatim as it now appears in `evals/roster-policy.yml`, over
the `catalogue_seen` cap's sort, and in the docstrings of `_relevance`,
`_clean_previous_arms` and `_update_catalogue_seen`:

> every census key with in-window turns that any entry folds onto keeps at
> least one entry that folds onto it, and an entry that neither the live
> catalogue nor the census names, under any spelling, never outranks one
> that either names

`test_the_invariant_sentence_is_pinned_in_the_policy_and_the_code`
normalises comment markers, whitespace and case (a YAML comment, an
indented Python comment and three docstrings wrap it differently, and the
cap's own comment shouts it), then asserts it appears in the policy prose,
EXACTLY FOUR times in `roster.py`'s source, and in each of the three
`__doc__`s. The count, not a bare `assertIn`, is what makes each copy
load-bearing.

**Deletions run, each red on its own** (`python3 test/run_tests.py TestIssue67Review10`):

| Deleted from | Result |
|---|---|
| `evals/roster-policy.yml` | FAILED (failures=1) |
| the `catalogue_seen` cap comment | FAILED (failures=1) |
| `_relevance.__doc__` | FAILED (failures=1) |
| `_clean_previous_arms.__doc__` | FAILED (failures=1) |
| `_update_catalogue_seen.__doc__` | FAILED (failures=1) |
| policy + cap comment together | FAILED (failures=1) |

A sibling, `test_the_policy_states_what_the_ceiling_does`, pins A's half.
N-2 goes with it: the stale "orders by census relevance FIRST, then by
`last_seen`" docstring now says what the code does.

#### F-2 — every clause, one mutation each

Route (c2) is gone with B1''s rewrite (provably implied by the others; 0
fires in 6,000,000 evaluations). Two more clauses are DELETED for having no
red mutation: `_no_relevance_order` and the `relevant=None` defaults on
both caps (`compute_roster` is the only caller and always has a
`_Relevance`), and the `historical = sorted(...)` pre-sort in
`_update_catalogue_seen`, which made the sort key's own id term redundant.
Four floors were added where a clause was load-bearing but unpinned.

Every mutation, run on the whole suite, with the first test each turns red:

| Mutation | Verdict | First test red |
|---|---|---|
| drop tier-1 route (a), the in-window census key | FAILED (2) | `test_a_census_key_a_tier_one_entry_already_reaches_spends_no_slot` |
| drop tier-1 route (b), the live catalogue id | FAILED (1) | `test_a_live_previous_arm_survives_the_cap_and_is_held_over` |
| drop tier 2 entirely | FAILED (1206) | `test_a_census_key_gets_exactly_one_slot_however_many_fold_onto_it` |
| drop tier 2's `covered` guard | FAILED (1) | `test_a_census_key_a_tier_one_entry_already_reaches_spends_no_slot` |
| tier 2's slot to `max`, not `min` | FAILED (407) | `test_a_census_key_gets_exactly_one_slot_however_many_fold_onto_it` |
| tier 2 to every group member, not one | FAILED (1) | `test_a_census_key_gets_exactly_one_slot_however_many_fold_onto_it` |
| drop `_base`'s `-DDDDDDDD` strip | FAILED (1206) | `test_a_census_key_gets_exactly_one_slot_however_many_fold_onto_it` |
| drop the production map from `fold` | FAILED (1) | `test_the_fold_follows_the_alias_map_not_one_suffix_strip` |
| drop the turns term from the order | FAILED (2) | `test_a_census_naming_more_keys_than_the_cap_keeps_the_biggest` |
| drop the id term from the order | FAILED (3) | `test_a_census_key_a_tier_one_entry_already_reaches_spends_no_slot` |
| drop the `census_is_silent` branch from both caps | FAILED (7) | `test_a_census_that_names_nothing_does_not_evict` |
| match `catalogue_seen` raw, not folded | FAILED (2) | `test_a_census_key_gets_exactly_one_slot_however_many_fold_onto_it` |
| count every census week, not the window | FAILED (1) | `test_a_census_that_names_nothing_does_not_evict` |
| `return ids, carried` → `return ids, ids` | FAILED (2) | `test_the_cap_still_bounds_what_is_carried_forward` |
| drop the live/historical split in the history cap | FAILED (3) | `test_a_census_naming_more_keys_than_the_cap_keeps_the_biggest` |

The stale "Mutation check (manual)" comment in
`test_a_bare_alias_a_live_snapshot_claims_survives_the_cap` named route
(c2); it now names the mutation that IS red there (dropping tier 2).

#### N-1

`_clean_catalogue_seen`'s `except (OverflowError, ValueError, OSError)` is
narrowed to `OverflowError`. `parse_ts` returns an AWARE datetime or None,
`.astimezone` on an aware one can only overflow, and `.date().isoformat()`
raises nothing — so the other two were unreachable. F-2's rule settles which
remedy to take: a defence nothing can reach is deleted, not annotated.
Widening it back leaves all 836 tests green, which is the point; there is
nothing to pin it with. The other two green mutations the pass named are
left alone, as asked, and both were already documented where they live.

#### Two judgment calls, flagged for the orchestrator

1. **A residual cost of decision 4, measured rather than hidden.** The
   invariant holds SUBJECT TO THE CAP: tier 1 plus tier 2 can exceed 500
   when the census names more than that, and then the lowest-turn entries
   go. `test_the_arms_cap_decides_the_attributable_denominator` is now
   built on the smallest case where it happens (500 tier-1 arms with three
   turns each, plus one tier-2 entry holding a 900,000-turn census key's
   only slot, which the cap drops). Filling tier 1 that way costs a planter
   500 entries that are themselves in-window census keys, and planting a
   census key does not remove its own attributability; what it can displace
   is another key's dated stand-in. Raising the cap moves the number, it
   does not remove the case. Stated in the policy and in that test.

2. **One fix beyond the brief's letter, which the property test forced.**
   `_is_attributable` matched `api_ids` and `previous_arms` through the
   alias map and `catalogue_seen` RAW, so a fold-group survivor in the
   HISTORY list conferred no attribution and decision 4's tier-2 guarantee
   ("K stays attributable through the plant") was true only for the arms
   list. `catalogue_seen` is now folded the same way the other two are.
   This grants a planter nothing — an id planted in `catalogue_seen`
   already attributes ITSELF, so planting `X-00000000` now attributes
   exactly what planting `X` always did — and
   `test_a_dated_history_entry_credits_its_undated_census_key` is its
   floor.

#### Two predictions in the brief that did not hold, reported rather than papered over

- "give tier 2 more than one slot per key (or let plants take a slot when a
  tier-1 entry exists) → round 9's rows A/B/C". Measured: neither mutation
  touches those rows. A fold group is the set of ids sharing a base, so its
  minimum is the bare base whenever that is present, and the bare base is
  the tier-1 entry in round 9's shape — the extra slot lands on an entry
  tier 1 already covers. Both mutations ARE red, under the two new F-2
  floors built for exactly them.
- "order a tier by `last_seen` first → the padded row red". It cannot be:
  with the census naming nothing, the padded row never reaches the order at
  all. That mutation is red under
  `test_a_tier_is_ordered_by_census_turns_not_by_last_seen`, which measures
  the same defence where it can fire.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_0177hC15KA5fhjufWz9oJx8a

---
_Generated by [Claude Code](https://claude.ai/code/session_0177hC15KA5fhjufWz9oJx8a)_

---
_Generated by [Claude Code](https://claude.ai/code)_