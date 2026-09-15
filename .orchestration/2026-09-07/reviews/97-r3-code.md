FOUND — 0 blocker, 0 should-fix, 5 nit

Round-3 code review (one-way-door half) — PR [#138](https://github.com/Adam-S-Daniel/skills-evals/pull/138),
issue [#97](https://github.com/Adam-S-Daniel/skills-evals/issues/97), head
`a6d165dd50090b3a6e90fe5439497bd270ee9267`, round-2 head `c5ea933`, base `origin/main` = `7c966ba`.

**Every round-2 item (S1, N1-adv/N4-code, N2-adv, N3-adv, N4-adv, N5-adv, N6-adv, N7-adv, S-A,
S-B, N1-code, N2-code, N3-code, N5-code) landed and survives a revert-the-fix mutation.** Every
round-1 item I re-measured (B1, B0/S1, S2, S3, S4, S5, A3, A4, A5, A6) still holds under its own
mutation. The merge `a6d165d` of `main` `7c966ba` is an **exact union** — nothing missing from
either parent, nothing invented beyond this round's own 7 new runner tests and 12 new
`TestIssue97` tests. Rule 19 holds: 11 fixtures identical per check to main, `guidance/_delivery`
exits 2. The key-bearing workflow's gate was **executed under bash against 43 inputs** and nothing
was minted or exported before any rejection; the two round-2 gate holes (the leading NUL and the
echoed value) are both closed and both were red on `c5ea933` through the same executed `run:` block.

The five nits are all new or newly-stale; none is a repeat of a round-1 or round-2 item at the
same severity with the same fix. Two of them arrive through the brief's own prescribed remedies
and are noted as such.

---

## 0. Safety ledger and tree integrity

| | Before first command | After last command |
|---|---|---|
| `/root/.claude/CLAUDE.md` (the real one) | **`935c291f2efb1ff55a463bccfde55e6a`** | **`935c291f2efb1ff55a463bccfde55e6a`** — unchanged |

Its mtime is still `Sep 6 01:56`. Every suite run, every probe and every mutation ran with
`HOME=$SP/r3w97-home` and `SKILLS_EVALS_USER_MEMORY=$SP/r3w97-home/usermem.md`. `markdown-it-py`
4.2.0 was reached with `PYTHONPATH=/root/.local/lib/python3.11/site-packages`, never by pointing
`HOME` at the real one. Nothing was written under `/root/.claude`.

**No code path under test resolves a path under the real HOME — measured, not asserted.** I
instrumented `guidance.deliver`, `guidance.agent_env` and `guidance._refuse_real_config_dir` in a
throwaway copy and ran the whole 788-test suite through it (`rc=0`, `Ran 788 tests in 192.384s`,
`OK (skipped=2)`):

```
instrumented calls: agent_env 1020, deliver 765, _refuse_real_config_dir 560
distinct (fn, arg, path) tuples: 2270
path roots: {'tmp': 2270}          NOT under /tmp: 0        under /root: 0
```

**Work-dir integrity.** All nine named md5s verified at start **and** at end, all identical to the
brief:

```
47c7268b23f402405f898f197d227c00  harness/guidance.py
40a08f8a22cda74be4d76cb9351da2d0  harness/run_eval.py
842bf963db0000f2ff9a8d1f964f791b  test/run_tests.py
fe241884fe83389f7e38fc8b774b42bf  test/issues/test_issue_97.py
5e2ccf934b89a62d7b8dcc8749f19c75  .github/workflows/eval.yml
aa540eb0a52779a08f40dc19cbee1acd  .github/workflows/ci.yml
6863402fa23ca1b69f6340f817734b3f  test/fake-claude
cc70a869e850f02912ac010e3d400241  evals/guidance/_delivery/fixture.yaml
e8d70f0a7ebda25e6927f357454b6640  evals/guidance-bridge-canary/fixture.yaml
```

`diff -rq $SP/rev97c-code <(fresh git archive a6d165d)` → **BYTE-IDENTICAL** after cleanup.

**`test/issues/` before and after a full run — the claim, measured.**

| | contents |
|---|---|
| before | `test_issue_97.py` |
| after a full 788-test run | `test_issue_97.py`, `__pycache__/` holding `test_issue_97.cpython-311.pyc`, **`test_issue_zz_discovery_probe.cpython-311.pyc`**, **`test_issue_zz_memory_probe.cpython-311.pyc`** |

So the claim is **true only of N6's new test**, which is exactly what the worker's report claims
for it ("driven against a SCRATCH discovery dir … so nothing is planted in the repo"). The four
round-1 suite-forking pins still write `test_issue_zz_discovery_probe.py` and
`test_issue_zz_memory_probe.py` into the repo's own `test/issues/` and remove them again —
inherent, since they must spawn the real runner over the real discovery dir — and only the `.pyc`
byproduct survives. Both `.pyc` and `__pycache__/` are gitignored. I removed all four
`__pycache__` directories; the tree is byte-identical to the archive.

`rev97c-ref`, `mainx5`, `_agent-guidance` and `agentskills`: **0 files modified**. All mutations
ran in `$SP/r3mut97-*` copies (no `.git`, so no inherited remote), now deleted. I entered none of
the other reviewers' directories (`rev97c-adv`, `r3adv97-*`, `se-97-v3`, `rev129*`, `rev124*`).

**Processes.** Zero `python3` processes alive at the end (`ps -eo pid,comm | awk '$3=="python3"'`
→ empty). The one fork bomb I created deliberately (the S-B unguarded measurement) was killed by
process group; `survivors after kill: 0`. I observed but did not touch the adversarial reviewer's
own `r3adv97-work/fork` process tree.

---

## 1. Verifiers

| Verifier | Exit | Result | Skips |
|---|---|---|---|
| `python3 test/run_tests.py` (first run) | — (`OK`) | **Ran 788 tests** in 198.7 s | 2 |
| `python3 test/run_tests.py` (final run, rc captured) | **0** | **Ran 788 tests** in 195.5 s, `OK (skipped=2)` | 2 |
| `python3 test/run_tests.py` (instrumented copy, §0) | **0** | **Ran 788 tests** in 192.4 s | 2 |
| `python3 test/test_propagation.py` | **0** | **Ran 164 tests** in 4.5 s, `OK (skipped=1)` | 1 |
| `python3 test/run_tests.py -k TestIssue97` | **0** | `NARROWED RUN: -k selected 102 of 788`; **Ran 102 tests** in 142.3 s, `OK` | 0 |
| `python3 test/run_tests.py -k NoSuchThingAtAll` | **2** | `FAILED: -k 'NoSuchThingAtAll' selected 0 of 788 tests. A pattern that matches nothing is a typo, not a clean run: an empty measurement is not a passing one.` | — |

Every number matches the brief's expectation exactly (788/2, 164/1, 102 of 788, rc 2). Both skips
are `pypdf not installed` (isolated: `-k pdf` → `skipped 'pypdf not installed'`); the
`_agent-guidance` sibling at `3d972b4` and the `agentskills` sibling are both present, so the 11
real-hook tests and `TestIssue63::test_registries_agree_with_agentskills_own_file` all ran — hence
2, not 3.

---

## 2. Per-item certification

Mutations ran in throwaway copies under `$SP/r3mut97-*`, driven through the production entry point
(`python3 test/run_tests.py -k <name>`, or the full suite where noted).

| Item | Landed? | Red-first on `c5ea933` | Mutation | Verdict |
|---|---|---|---|---|
| **S1** timeout ceiling | yes | **RED** — 3 tests, `AttributeError: module 'run_eval' has no attribute 'MAX_TIMEOUT_S'` | drop the upper bound → `Ran 3 tests in 302.9s / FAILED (failures=12)`; **all 12 ceiling rows red**, lower-bound and accepted rows untouched | **PASS** |
| **N1-adv / N4-code** no echo | yes | **RED** — `'uniquely-identifiable-payload' unexpectedly found in "…names no committed fixture: evals/uniquely-identifiable-payload…"` | restore `: $fixture` → **1 red** (`branch='no such fixture'`) | **PASS** |
| **N2-adv** A6 header | yes | **RED** (round 2 measured; re-proved by mutation) | add a new name to `agent_env` not in the header → **1 red**, `'NEWLY_ADDED_ALLOWLIST_NAME' … the header does not name it` | **PASS** |
| **N3-adv** residual reasons | yes | **RED** — `'a contaminating source that carries no token of its own is invisible to a token guard at all' not found in …` | drop the clause → **1 red** | **PASS** (see nit N3) |
| **N4-adv** symmetric guard | yes | **RED** — `0 != 2 : a treatment arm whose probe reported the control's decoy must be INCONCLUSIVE, never scored` | revert to control-only forbidden token → **1 red**; the paired clean-treatment row stays green | **PASS** |
| **N5-adv** `-k` zero → 2 | yes | **RED** — `0 != 2 : NARROWED RUN: -k selected 0 of 692 tests` | `if False:` on the zero branch → **1 red** | **PASS** |
| **N6-adv** empty module named | yes | **ERROR** — `TypeError: build_suite() takes 0 positional arguments but 1 was given` | restore the old wording → **1 red**, `'test_issue_zz_empty' not found in 'build_suite() must carry at least one test from EVERY …'` | **PASS** |
| **N7-adv** targeted run guarded | yes | **RED** — `0 != 1 : a targeted run that changed the watched user-memory file must exit 1 even though its test passed` | move the snapshot back below the branch → **1 red**; the paired clean row stays green | **PASS** |
| **S-A** plural guard prompt | yes | **RED** — `0 != 2 : a contaminated control must never score clean, whatever arity its probe answers with`, and `'every one of them' not found in 'If your context contains a magic word…'` | revert the wording alone → **red in 3 places** (end-to-end row, `test_the_guard_prompt_asks_for_every_magic_word`, `test_the_guard_probe_is_the_canary_probe`) | **PASS** |
| **S-B** suite-forking pin | yes | **RED** — `test_dash_k_… (line 9989) spawns the whole suite but never calls self._skip_in_child()` | drop the guard → **1 red**; break the detector's anchor → `[] is not true : … must not be able to pass vacuously` | **PASS** |
| **N1-code** bounded child | yes | (same rows as S1) | disable the bound's premise → the battery **returns red in 302.9 s** instead of hanging; 10 of 12 reds are the outer bound's own message | **PASS** |
| **N2-code** nested glob | yes | **green on ref** (fix travels with the class) | `**` → `*` → scratch half **red**, committed half **green** | **LANDED, teeth in the scratch half only** — see nit N2 |
| **N3-code** NUL refused | yes | **RED** — 4 subtests, `0 != 1 : leading / trailing / embedded: a NUL anywhere in the dispatch value must fail the step` | delete the `jq -e` block → **4 red** | **PASS** |
| **N5-code** exit-code comment | yes | **RED** — `False is not true : main() must say, beside 'status = 0 if …'` | (a) delete the sentence → **1 red**; (b) rename one `CHILD_RC_PINS` target → **1 red** | **PASS** |
| **merge `a6d165d`** (main `7c966ba`, PR #136) | yes | n/a | AST + file-set union, §6 | **EXACT UNION** |

### S1 — the ceiling, measured through the production entry point

`MAX_TIMEOUT_S = 45 * 60` = 2700, checked in the **same predicate** as the lower bound
(`harness/run_eval.py:105`): `and 0 < value <= MAX_TIMEOUT_S`. The anchoring test parses the
workflow — `yaml.safe_load(EVAL_WORKFLOW…)["jobs"]["eval"]["timeout-minutes"] * 60` — i.e. the
**`eval` job by name**, and it does fail when that job's number changes: mutating
`timeout-minutes: 45` → `30` gives `AssertionError: 2700 != 1800 : harness/run_eval.py's
MAX_TIMEOUT_S must equal eval.yml's 'timeout-minutes' x 60 for the eval job`.

I drove all four knobs × 16 values through `python3 harness/run_eval.py …` in a child, with
`$FAKE_CLAUDE_ARGV_LOG` set (64 rows):

| value | `timeout_s` | `setup_timeout_s` | `guard.timeout_s` | `judge.timeout_s` |
|---|---|---|---|---|
| `null`, `""`, `"600"`, `true`, `false`, `-1`, `0`, `.inf`, `.nan`, `[3]`, `{a:1}` | rc 2, 0 CLI | rc 2, 0 CLI | rc 2, 0 CLI | rc 2, 0 CLI |
| **2200000**, **1e9**, **2701** | rc 2, 0 CLI | rc 2, 0 CLI | rc 2, 0 CLI | rc 2, 0 CLI |
| **2700**, **600** | rc 0, 1 CLI | rc 0, 1 CLI | rc 0, 1 CLI | rc 0, 1 CLI |

**Zero `Traceback`, zero `OverflowError` across all 64 rows; zero CLI invocations on every
rejected row** (the validator runs at fixture load, before any subject branch). Sample:

```
fixture configuration error: /tmp/s1row-…/eval/fixture.yaml: `guard.timeout_s` must be a
positive number of seconds no greater than 2700 (eval.yml gives the eval job that many), got
2200000. …
```

**Every `.get(<timeout>…)` in `run_eval.py` and `guidance.py`, enumerated:**

| Read | Fixture-settable? | Validated? |
|---|---|---|
| `:455 fixture.get("setup_timeout_s", 60)` | yes | **yes** (`TIMEOUT_KNOBS[1]`) |
| `:816 / :1158 args.timeout or fixture.get("timeout_s", 600)` | yes | **yes** (`TIMEOUT_KNOBS[0]`) — *unless `--timeout` supplies it, see nit N1* |
| `:534 arm.get("timeout", 600)` | only via the two lines above | **inherits** their validation |
| `:891 / :1203 judge_cfg.get("timeout_s", 120)` | yes | **yes** (`TIMEOUT_KNOBS[3]`) |
| `:1142 (fixture.get("guard") or {}).get("timeout_s", 300)` | yes | **yes** (`TIMEOUT_KNOBS[2]`) |
| `:632 timeout=10`, `run_canary.py:48 timeout=30` | no — literals | n/a |
| `guidance.py:482 deliver(timeout=120)` default, `:597 run_guard(timeout=…)` | fed only from `TIMEOUT_KNOBS[2]` | **inherits** |
| `--timeout` CLI flag (`argparse type=int`, no bound) | operator | **NO** — nit N1 |

### N4-adv — the guard is symmetric by construction

`harness/run_eval.py:1093`:

```python
forbidden = tuple(other for other in (ctx["token"], *ctx["decoys"].values())
                  if other != arm_token)
```

Every token the run minted that was not delivered to this arm — the treatment token for a control,
the control's decoy for a treatment arm. The decoys are minted in the run `ctx` **before any arm
runs**: measured by AST, the `ctx` assignment (with `"decoys": {arm["name"]: guidance.new_decoy_token()
for arm in arms if arm["mode"] == "none"}`) is at line **1322** and the `_run_guidance_arm` list
comprehension at line **1338**. `run_guard` (`guidance.py:636`) sets
`contaminated = any(other in reply for other in forbidden_tokens if other)`.

Rows through `main()`: a treatment arm whose probe reports the control's decoy → **rc 2**,
`error.type == "guard_contaminated"`, `guard.contaminated` true, `objective_checks` null; the
paired row (treatment reading only its own payload) → **rc 0**, `contaminated` false, decoy absent
from the reply; the control's round-1 rows unchanged (green on head, red under the A4 revert).

### S-A — the plural prompt

```
GUARD_PROMPT = 'If your context contains any magic words, reply with every one of them and
nothing else. If it contains none, reply with exactly NO-MAGIC-WORD. Do not use any tools.'
```

Both canary fixtures carry the same text (`evals/guidance-bridge-canary/fixture.yaml` and
`evals/guidance/_delivery/fixture.yaml`, both parsed with `yaml.safe_load`), and the bridge
canary's separate `subagent_prompt` is **byte-untouched** (still singular) — confirmed from the
diff hunk, which changes only the `prompt:` scalar.

`test/fake-claude` gains `guidance_probe_literal`, which returns every magic word only when the
`-p` prompt (whitespace-folded) carries `PLURAL_MARKER = "every one of them"`, else `found[:1]`.
The suite reads that constant back out of the fake with `ast`
(`_fake_claude_plural_marker`, asserting exactly one such assignment) and requires `GUARD_PROMPT`
to still carry it. Under the literal probe: a contaminated control → **rc 2 `guard_contaminated`**,
`contaminated` true, no score; a clean control → **rc 0**, `observed` true.

**Does the honest `guidance_probe` still cover the round-1 rows?** Yes — measured from the
`c5ea933 → a6d165d` diff of `test/fake-claude`, the change is purely additive: `guidance_probe`
and `guidance_blind` behave identically (the new `found[:1]` line is gated on
`MODE == "guidance_probe_literal"`), the mode tuple simply gained a third member, and the seven
tests that use `guidance_probe` — including round-1's
`test_a_contaminated_control_arm_is_inconclusive_and_exits_2` — are green on head and red under
the A4 revert.

### S-B — the fork bomb, bounded

By AST (my own scan, independent of the committed pin), functions that both name `run_tests.py`
and spawn a subprocess:

| file | function | forks via | calls `_skip_in_child()` |
|---|---|---|---|
| `test/run_tests.py` | `test_dash_k_on_the_command_line_still_reaches_the_discovered_subtree` (:12058) | direct | **yes** |
| `test/issues/test_issue_97.py` | `test_planted_issue_module_is_discovered_and_fails_the_runner` (:238) | `_run_suite` | **yes** |
| " | `test_removing_the_planted_module_puts_the_runner_back_to_zero` (:258) | `_run_suite` | **yes** |
| " | `test_the_run_wide_user_memory_guard_fails_a_run_that_writes_the_file` (:1419) | `_run_suite` | **yes** |
| " | `test_an_ordinary_run_leaves_the_watched_file_alone` (:1446) | `_run_suite` | **yes** |

That is the **only** one in `test/run_tests.py` and exactly the **four** in `test_issue_97.py`.
The committed pin parses the file with `ast` (never a regex) and `assertTrue(forking, …)` refuses
an empty set — measured red when the anchor is broken.

**The process measurement**, in a throwaway copy of the head tree with the S3 defect reverted
(`select_tests` returns everything, `-k` narrowing broken), running that one test alone as a
targeted run, sampled once a second, hard 60 s bound, killed by process group:

| | peak concurrent `run_tests.py` | growth | parent |
|---|---|---|---|
| **guarded** (this head) | **2** | 1 → 2 at 1.0 s, flat | **returns in 33.3 s**, rc 1, correctly failing (`Ran 788 tests` in the child, `1 != 0`) |
| **unguarded** (guard removed) | **4 and climbing** | 1 → 2 at 1.0 s → 3 at 23.2 s → 4 at 45.4 s | **never returns**; bound hit, process group killed |

`survivors after kill: 0` in both runs; the global `run_tests.py` count returned to 0 afterwards.
Consistent with the worker's 8-at-150 s extrapolation (~22 s per level here).

N5's own test is the same hazard one class down and it asserts its sentinel selects zero
**before** calling `main()` — verified in the source and exercised: on the ref that assertion is
what turns a broken `-k` into `0 != 2` rather than a recursion.

### N6 — sys.path / sys.modules restored, measured

Ran `test_a_discovered_module_that_defines_no_tests_is_named_in_the_failure` in isolation with
before/after snapshots:

```
test ok: True
sys.path identical: True        sys.path added: []
sys.modules leaked: []          'test_issue_zz_empty' in sys.modules: False
```

Nothing was planted in the repo (the scratch dir is an `mkdtemp`).

### N5-adv — the zero-selection exit really goes through `memory_guard()`

By AST, `main()` has exactly **3** `return` statements and **all three** are
`memory_guard(memory, before, …)` — the targeted branch (:12174), the zero-selection branch
(:12189, `memory_guard(memory, before, 2)`) and the ordinary path (:12208).

---

## 3. Hollowness — every NEW test on head, run on a throwaway copy of `c5ea933`

Spliced, not read. Two splices, because the two files need different treatment.

### 3a. `test/issues/test_issue_97.py` — 12 new methods (plus `test/fake-claude`)

Head's `test_issue_97.py` and `test/fake-claude` dropped onto the ref tree, run through the
**production entry point** (`python3 test/run_tests.py -v -k …`, never `python3 <file>`, which
would be a hollow verifier — the module has no `if __name__ == "__main__"`):

**Ran 12 tests → FAILED (failures=12, errors=3), rc 1 — 10 of 12 red.**

| new test | on ref | reason |
|---|---|---|
| `test_the_timeout_ceiling_is_the_workflow_job_budget` | **ERROR** | `AttributeError: module 'run_eval' has no attribute 'MAX_TIMEOUT_S'` |
| `test_a_timeout_above_the_job_budget_is_a_named_configuration_error` | **ERROR** | same |
| `test_a_timeout_at_or_below_the_job_budget_still_runs_the_arm` | **ERROR** | same |
| `test_neither_rejection_branch_echoes_the_dispatched_value` | **FAIL** | `'uniquely-identifiable-payload' unexpectedly found in "…names no committed fixture: evals/uniquely-identifiable-payload…"` |
| `test_a_nul_byte_in_the_dispatch_value_is_refused_before_substitution` | **FAIL** ×4 | `0 != 1 : leading / trailing / embedded…: a NUL anywhere in the dispatch value must fail the step` |
| `test_the_guard_prompt_asks_for_every_magic_word` | **FAIL** | `'every one of them' not found in 'If your context contains a magic word…'` |
| `test_a_contaminated_control_is_caught_by_a_prompt_obeying_probe` | **FAIL** | `0 != 2 : a contaminated control must never score clean, whatever arity its probe answers with` |
| `test_a_treatment_arm_that_reports_the_controls_decoy_is_contaminated` | **FAIL** | `0 != 2 : … must be INCONCLUSIVE, never scored` |
| `test_the_residual_paragraph_names_both_reasons_the_guard_cannot_settle` | **FAIL** | `'a contaminating source that carries no token of its own is invisible to a token guard at all' not found` |
| `test_all_three_residual_paragraphs_say_why_the_prompt_is_plural` | **FAIL** ×3 | `'the plural prompt exists for' not found` in `guidance.py`, `README.md`, `DESIGN.md` |
| `test_a_clean_control_still_scores_under_a_prompt_obeying_probe` | **ok** | the paired other-side floor the brief required; teeth = the S-A revert (red on the contaminated row, green here) |
| `test_an_uncontaminated_treatment_arm_reports_only_its_own_token` | **ok** | the paired other-side floor; teeth = the N4-adv revert |

The three ERRORs are the case the brief anticipated (the feature is simply absent on the ref).
The two greens are the deliberate "so a fix that condemned every arm would not satisfy the first"
rows — regression floors over already-correct code, each with a named mutation proved red above.

### 3b. `test/run_tests.py` — 7 new methods

A whole-class splice would carry the fixes with the tests (round 2 hit the same problem), so I
spliced **only the new methods** plus the class members they need that are not themselves the fix,
left ref's own `test_dash_k_…` untouched, and added `import io` / `import contextlib` (plumbing
ref lacks). **Ran 7 tests → FAILED (failures=4, errors=1), rc 1 — 5 of 7 red.**

| new test | on ref | reason |
|---|---|---|
| `test_a_dash_k_that_selects_nothing_is_exit_2_and_names_the_pattern` | **FAIL** | `0 != 2 : NARROWED RUN: -k selected 0 of 692 tests — an OK from this run is not a full-suite pass.` |
| `test_a_discovered_module_that_defines_no_tests_is_named_in_the_failure` | **ERROR** | `TypeError: build_suite() takes 0 positional arguments but 1 was given` (`discovery_dir` is this round's module-level fix) |
| `test_a_targeted_run_is_covered_by_the_user_memory_guard_too` | **FAIL** | `0 != 1 : a targeted run that changed the watched user-memory file must exit 1 even though its test passed` |
| `test_every_suite_forking_test_in_this_file_stands_down_in_a_child` | **FAIL** | `test_dash_k_on_the_command_line_still_reaches_the_discovered_subtree (line 9989) spawns the whole suite but never calls self._skip_in_child()` — i.e. it really detects ref's unguarded test |
| `test_the_runner_says_what_can_and_cannot_police_its_own_exit_code` | **FAIL** | `False is not true : main() must say, beside 'status = 0 if result.wasSuccessful() else 1', …` |
| `test_a_targeted_run_that_touches_nothing_still_exits_0` | **ok** | paired other-side floor; teeth = the N7 revert |
| `test_the_fixture_sweep_reaches_a_nested_skill_fixture` | **ok** | its fix **is** a class member (`_fixture_dirs`'s `**`), so it travels with the test; teeth = the `**`→`*` mutation, measured red |

---

## 4. Rule 19 / identity per check

Every committed fixture scored with `--arm objective-only` on head and on `$SP/mainx5`
(`origin/main` = `7c966ba`), `--results-dir` outside both trees, stdout **and** stderr **and** exit
code compared after normalising `/tmp/...` paths. Real per-check JSON, not just an error line
(1.2–3.8 KB of `{"id", "passed", "detail"}` per fixture).

| Fixture | rc main | rc head | per-check |
|---|---|---|---|
| `evals/disarm-inherited-reach` | 1 | 1 | **identical** |
| `evals/github-actions-sha-pinning` | 1 | 1 | **identical** |
| `evals/guidance-bridge-canary` | 2 | 2 | **identical** |
| `evals/post-failure-comment` | 1 | 1 | **identical** |
| `evals/propagation` | 2 | 2 | **identical** |
| `evals/rename-pdfs` | 1 | 1 | **identical** |
| `evals/review-bash-ci-reliability` | 1 | 1 | **identical** |
| `evals/windows-elevation-from-wsl` | 1 | 1 | **identical** |
| `evals/workflow-path-audit` | 1 | 1 | **identical** |
| **`evals/writing-adrs/bootstrap`** | 1 | 1 | **identical** |
| **`evals/writing-adrs/existing-convention`** | 1 | 1 | **identical** |
| `evals/guidance/_delivery` | — | **2** | new on the branch; N-f message, not `{"checks": []}` |

**11 identical, 0 differing** — the worker's claim reproduces exactly, both nested `writing-adrs/*`
fixtures included.

`git diff --stat origin/main..a6d165d -- evals/` is **two files**: the canary's `prompt:` (6 lines,
the S-A wording and nothing else — the `subagent_prompt` hunk is absent from the diff) and the new
`evals/guidance/_delivery/fixture.yaml`. This round's own commits
(`git diff --name-only c5ea933..c27994a -- evals/`) touch **only the two fixture prompts** and
**no `seed/` path**.

---

## 5. Round-1 and round-2 regression — one measurement each

| Round-1/2 item | Measurement on this head | Result |
|---|---|---|
| **B1** dispatch gate | delete the `case` block → `test_the_validation_step_*` **3 red**; and in my own executed-gate run all four multi-line rows are rc 1 with nothing written | **HOLDS** |
| **B0/S1** no real HOME path | 2,270 distinct instrumented `(fn, arg, path)` tuples across the full 788-test suite, **100 % rooted at `/tmp`**, 0 under `/root`; real `CLAUDE.md` md5 unchanged | **HOLDS** |
| **S2** run-wide memory snapshot | `if True: return status` in `memory_guard` → **2 red** (`…guard_fails_a_run_that_writes_the_file` and the new targeted-run pin) | **HOLDS** |
| **S3** discovery + argv | `if False and discovery_dir.is_dir():` → full suite **686 tests, 3 red, rc 1** (down from 788) | **HOLDS** |
| **S4** `PASSTHROUGH` exact | append `GITHUB_TOKEN` → **2 red** (`…committed_six` and the A6 header pin) | **HOLDS** |
| **S5** no pipe into grep | restore `printf … \| grep -Fxq` → **20/20 trials red**, `1 != 0 : a committed fixture must still be accepted when the committed list is 118826 bytes; the step failed CLOSED` | **HOLDS** |
| **A3** `delivery_failed` | `if False:` on the delivery check → **2 red** | **HOLDS** |
| **A4** decoy / two-sided control | `decoy = None` → **1 red** (`test_a_contaminated_control_arm_is_inconclusive_and_exits_2`) | **HOLDS** |
| **A5** `arms:` shapes | restore `fixture.get("arms") or DEFAULT_GUIDANCE_ARMS` → **2 tests / 6 subtests red**; the absent-key floor stays green | **HOLDS** |
| **A6** header per subject | add a name to `agent_env` not in the header → **1 red** (and the header now names `WORKSPACE` and the fixture `env:` overlay verbatim) | **HOLDS** |

No round-1 or round-2 item regressed.

---

## 6. The merge `a6d165d` — an exact union

Parents, measured: `a6d165d parents=c27994a 7c966ba`. So **"ours" is `c27994a`** (the pre-merge
branch tip), not the round-2 head `c5ea933`; the worker's numbers are stated against that parent
and reproduce **exactly**.

`test/run_tests.py`, by AST:

| | ours (`c27994a`) | theirs (main `7c966ba`) | merged (`a6d165d`) | missing from ours | missing from theirs | invented |
|---|---|---|---|---|---|---|
| classes (`ast.walk`) | 32 | 32 | **35** | none | none | none |
| top-level functions | 13 | 5 | **13** | none | none | none |
| test methods | 603 | 673 | **688** | none | none | none |

(Top-level-only class counts are 30 / 32 / 33; the two extra on head are the `_MemoryGuardProbe`
and `_MemoryQuietProbe` classes defined inside N7's own test bodies. Against `c5ea933` instead of
`c27994a` the ours column reads 30 / 12 / 594 — same verdict either way.)

The other files, by AST name set (classes + functions + upper-case module constants):

| file | ours | theirs | head | missing-ours | missing-theirs | invented |
|---|---|---|---|---|---|---|
| `harness/run_eval.py` | 42 | 27 | 42 | none | none | none |
| `harness/scorers/objective.py` | 83 | 85 | 85 | none | none | none |
| `harness/scorers/judge.py` | 5 | 5 | 5 | none | none | none |
| `harness/run_canary.py` | 9 | 9 | 9 | none | none | none |
| `scripts/make_badge.py` | 18 | 13 | 18 | none | none | none |
| `harness/guidance.py` | 34 | (absent) | 34 | none | — | none |
| `test/issues/test_issue_97.py` | 174 | (absent) | 174 | none | — | none |

**File-set union:** 0 files present on either parent and absent from head; 0 files on head absent
from both parents.

- **`harness/scorers/objective.py` is byte-identical to main** (`726ef62a…` both sides), so main's
  `file_count` check and every `CHECKS` entry survive untouched. `harness/scorers/judge.py` is
  byte-identical across all three trees.
- **`run_setup` and `agent_env` in `harness/run_eval.py` are byte-identical to main's**, compared
  by AST source segment.
- **The 85 tests main gained with PR #136** (`d5e06ee` → `7c966ba`, 588 → 673): named by AST diff,
  **0 missing from head**, and main lost nothing in that range. They are `FileCountCheckTests`
  (24), `LinkTargetsExistCheckTests` (17), `TestIssue80` (41), `CiDispatchTests` (3).
- **README's `evals/` tree carries both sides**: `writing-adrs/` at :50 (main's) and
  `disarm-inherited-reach/` at :47 (this branch's), plus `guidance/` at :62. Exactly **one** line
  present on main is absent from head — `  run_tests.py … (hermetic, no real claude)` — and that
  line was *extended* on head (a `;` plus a continuation documenting `test/issues/`), not dropped.
  **DESIGN.md: 0 lines present on main and missing from head.**
- **`ci.yml` carries both sides**, verified by diffing against each parent: main's `README.md` and
  `DESIGN.md` entries in **both** the `pull_request` and `push` `paths:` filters (plus the
  `CiDispatchTests` rationale comment), **and** this branch's `_agent-guidance` side-by-side
  checkout (`persist-credentials: false`, same pin) and `pip install pyyaml markdown-it-py==4.2.0`.

The five files head differs from `c27994a` are exactly the five main touched in #136
(`ci.yml`, `DESIGN.md`, `README.md`, `objective.py`, `run_tests.py`).

**Authors.** All 15 commits in `c5ea933..a6d165d --not origin/main` are authored **and** committed
as `4205216+Adam-S-Daniel@users.noreply.github.com`.

---

## 7. The one-way-door read

`git diff --name-only origin/main..a6d165d -- .github/` → **`ci.yml` and `eval.yml` only**
(+16 / +195).

Every workflow parsed with `yaml.safe_load` and re-scanned as text:

| Rule | Result |
|---|---|
| Every `uses:` a bare 40-hex SHA | **25 `uses:` across 6 workflows; 24 pass.** The one exception is `scheduled-run-health.yml:jobs.audit` -> `Adam-S-Daniel/cms-platform/.github/workflows/scheduled-run-health.yml@v0.1.87` — the documented `cms-platform` release-tag carve-out, pre-existing and outside this PR's diff |
| No trailing version comment on any `uses:` | **PASS** — zero, on all 25 |
| Zero `${{ }}` inside any `run:` block | **PASS** — 26 `run:` blocks, zero. `eval.yml`'s only live `${{ }}` is `GITHUB_TOKEN: ${{ github.token }}` in step 13's own `env:`; the other two occurrences are comment prose |
| `eval.yml` triggers | **PASS** — exactly `schedule` + `workflow_dispatch`; no `pull_request`, no `pull_request_target` |
| `permissions` minimal and unchanged from main | **PASS** — `{contents: write, id-token: write}` on head **and** on main; no job-level `permissions` |
| `concurrency` | **PASS** — workflow-level `{group: real-eval, cancel-in-progress: false}`, identical to main; **no `concurrency` on any job**, and none at all in `ci.yml`, the workflow that publishes the required PR context |
| All checkouts `persist-credentials: false` and pinned | **PASS** — 5 in `eval.yml`, 3 in `ci.yml`, all on `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| New `_agent-guidance` checkout | **PASS** — `persist-credentials: false`, same pin, `path: _agent-guidance`, in both workflows |
| Push auth step-local | **PASS** — `GITHUB_TOKEN` appears in exactly one step's `env:` (step 13, the badge commit) and is used only inside that step's `run:` |
| Validation **before** the OIDC/token exchange | **PASS, by parsed step index** — step **9** "Select and validate the fixture to run", step **10** "Mint OIDC token and exchange for Anthropic access token", step **11** "WIF auth preflight" |
| NUL check before the substitution and before the `case` guard | **PASS** — by execution, see below |
| `inputs.fixture` never interpolated | **PASS** — it appears only inside two `jq` programs reading `$GITHUB_EVENT_PATH` as data |

The whole `c5ea933 -> a6d165d` diff of `eval.yml` is **three hunks and nothing else**: the A6 header
sentence (N2-adv), the `jq -e` NUL block (N3-code) and dropping `: $fixture` (N1-adv/N4-code). The
`case` character class, the here-string `grep -Fxq -- "$fixture" <<<"$committed"`, the `find`, and
the step order are byte-unchanged.

### The executed gate — step 9's `run:` block under bash, 43 inputs

Synthetic tree: three top-level committed fixtures, two **nested** committed fixtures
(`evals/writing-adrs/{bootstrap,existing-convention}`), `evals/guidance/_delivery`, one existing
directory with no `fixture.yaml`, and one directory whose `fixture.yaml` is a **symlink**. NUL is
written below as the two-character escape `\0`; every case used a real NUL byte.

| Input | rc | `eval-fixture` | `eval-key` | value echoed? | rejected by |
|---|---|---|---|---|---|
| `evals/workflow-path-audit` | **0** | the value | `workflow-path-audit` | — | accepted |
| **`evals/writing-adrs/bootstrap`** (nested) | **0** | the value | `writing-adrs/bootstrap` | — | accepted |
| `evals/guidance/_delivery` | **0** | the value | `guidance/_delivery` | — | accepted |
| `evals/symlinked` (symlinked `fixture.yaml`) | **0** | the value | `symlinked` | — | accepted (documented N-i behaviour) |
| no `inputs` key / `inputs` without `fixture` / JSON `null` / `""` | **0** | default | `workflow-path-audit` | — | schedule default |
| `..`, `/etc/passwd`, `../../etc/passwd`, trailing slash, `evals/…/fixture.yaml`, `evals/uncommitted-dir`, charset-clean marker | **1** | **not written** | **not written** | **no** (278 B, constant) | no committed fixture |
| **100 KB alnum**, **100 KB marker-prefixed** | **1** | **not written** | **not written** | **no** (278 B — the same length as the short row) | no committed fixture |
| JSON `7`, JSON `true` | **1** | **not written** | **not written** | no | no committed fixture |
| multi-line (2nd line committed), multi-line + `$(id)`, `*`, `[`, leading/inner/trailing space, Cyrillic-а homoglyph, marker+space, JSON object, JSON array, JSON array of one committed string | **1** | **not written** | **not written** | no (74 B) | **charset (`case`) guard** |
| **`\0` leading**, **`\0` trailing**, **`\0` embedded**, **`\0` embedded collapsing to a committed name**, **`\0` + marker** | **1** | **not written** | **not written** | no (55 B) | **NUL guard** (`contains a NUL byte`) |
| malformed JSON, `inputs` a string, `inputs` a list, top-level array | **5** | **not written** | **not written** | no | `jq` under `set -e` — fails closed |
| empty event file / `GITHUB_EVENT_PATH` unset / pointing nowhere | **0** | default | `workflow-path-audit` | — | schedule default |

**Nothing was minted or exported before any rejection: on every rejecting row both output files
were absent** (`REJECTED-BUT-WROTE-OUTPUT: []`).

**Ordering, proved by execution rather than by reading:** a value that is *both* NUL-bearing and
charset-violating (`\0` + `*`) gives the **NUL** message on head and the **charset** message on
`c5ea933` — so the NUL check really does run before the substitution and before the `case` guard.

**Both round-2 gate holes, red-first through the same executed block:**

| input | on `c5ea933` | on `a6d165d` |
|---|---|---|
| `\0evals/workflow-path-audit` | **rc 0** — accepted as that fixture, **both outputs written**, 210 B of output | **rc 1**, `eval.yml: dispatch input 'fixture' contains a NUL byte`, nothing written |
| `evals/<marker>` | rc 1, **marker echoed**, 319 B | rc 1, **marker absent**, 278 B |
| `<marker>` + 100 KB | rc 1, **marker echoed — 100,313 B into a public log** | rc 1, **marker absent, 278 B** |

---

## 8. Findings

### Blockers
**None.**

### Should-fix
**None.**

### Nits

**N1 — the new ceiling is a *fixture* ceiling, and `--timeout` still walks past it into the bare
traceback S1 was raised to close.**
`harness/run_eval.py:534` (`arm.get("timeout", 600)`), fed by `:816` / `:1158`
(`args.timeout or fixture.get("timeout_s", 600)`), and `:1422` (`--timeout`, `argparse type=int`,
no bound).

Reproducing input, on this head, through the real CLI entry point:

```
$ CLAUDE_BIN=test/fake-claude python3 harness/run_eval.py evals/workflow-path-audit \
      --arm without_skill --timeout 2200000 --no-judge --results-dir /tmp/x
rc=1
    fd_event_list = self._selector.poll(timeout)
OverflowError: timeout is too large
```

Identical at `--timeout 1000000000`; `--timeout 600` is rc 0. That is the exact rc-1 / empty
stdout / bare `OverflowError` shape S1 closed for the four fixture knobs, still reachable through
the same `arm.get("timeout", 600)` read because `--timeout` overrides the fixture value *after*
`validate_timeouts` has run.

Why a nit and not more: it needs an operator to type an absurd flag, it is not reachable from
fixture content, and **`eval.yml` passes no `--timeout`** — I read the run step out of the parsed
YAML: `python3 harness/run_eval.py "$fixture" --arm both --guidance … --registry …`. Round 2's own
enumeration listed the flag as "operator, `argparse type=int`, n/a", so it was seen and
deliberately scoped out.

**Does it return through the brief's own remedy?** Partly. The traceback pre-dates this round, but
the *message* S1 added now says `must be a positive number of seconds no greater than 2700
(eval.yml gives the eval job that many)` — which reads as a harness-wide ceiling, and the flag does
not honour it. **REPEAT?** No: not a round-1 or round-2 item, and not at the same severity.
*Fix:* a bound in the argparse `type=` (or run `args.timeout` through the same predicate) plus one
clause in the flag's `help`.

---

**N2 — the docstring the brief asked for is now factually false, and the merge has made the
committed half free to falsify.**
`test/run_tests.py`, `TestIssue63Review.test_every_committed_fixture_with_a_skill_resolves_its_registry`.

Its docstring says: *"On the committed tree the only NESTED fixture is `evals/guidance/_delivery`,
which carries no `skill:` and is filtered out — so `*` and `**` score identically here."* Measured
on this head:

```
glob '*'   dirs: 9   with skill: 7
glob '**'  dirs: 12  with skill: 9
nested-only WITH skill: evals/writing-adrs/bootstrap, evals/writing-adrs/existing-convention
```

So `*` and `**` do **not** score identically on the committed tree any more — the merge brought
two nested *skill* fixtures in — and the sentence is wrong. The committed half nevertheless stays
green under the `**`→`*` mutation (measured: scratch half red, committed half green) purely because
it asserts `checked > 0`. The worker recorded the "still green" half in the PR report but left the
docstring's factual claim standing.

**Returns through the brief's own prescribed remedy?** Yes — the brief said *"say so in the test's
docstring"*, and that sentence is the one the merge invalidated. **REPEAT?** No (the round-2 nit
N2 was "unfalsifiable on the committed tree"; that is now closed by the scratch half, and this is
a different, newly-created problem). *Fix, one line:* assert `checked` equals the `**` count (9
today) rather than `> 0` — which now genuinely falsifies the spelling on the committed half too —
and delete the stale sentence.

---

**N3 — N3-adv's clause landed in `harness/guidance.py` only; DESIGN.md still gives the narrower
reason the nit was raised about.**
`DESIGN.md:470-471` — *"because a probe asked for the magic words with two in context may report
either"* — is verbatim the incompleteness N3-adv identified in the docstring, and it is still the
only reason DESIGN gives. `README.md:195-196` gives no reason at all. Only `guidance.py:53-59`
carries both, and `test_the_residual_paragraph_names_both_reasons_the_guard_cannot_settle` pins it
in that one place; the three-way pin
(`test_all_three_residual_paragraphs_say_why_the_prompt_is_plural`) covers the *S-A* clause, not
this one.

The brief scoped N3 to the docstring in as many words (*"Pin the clause's operative words in the
existing docstring-words test if there is one; otherwise no test (docstring only)"*), so the worker
complied exactly. Recorded because the three copies now disagree and DESIGN is the one a reader
reaches for. **REPEAT?** No. *Fix:* one clause in DESIGN's sentence, and extend the existing
three-way pin to require it.

---

**N4 — a failure message that dumps 174 names, in the test whose own comment explains why not to.**
`test/run_tests.py`,
`TestTheRunnerItself.test_the_runner_says_what_can_and_cannot_police_its_own_exit_code`.

Two lines above, the test says *"assertTrue, not assertIn: assertIn's default message would dump
this whole 10k-line file into the failure"* — then uses `self.assertIn(name, defined, …)` over
`defined`, the set of every function name in `test_issue_97.py`. Measured (mutation: rename one
`CHILD_RC_PINS` target): the failure prints the custom message **after** all 174 names.
**REPEAT?** No. *Fix:* `assertTrue(name in defined, …)`, same as the line above it.

---

**N5 — the S-B detector's blind spot, recorded because it fails safe.**
`test/run_tests.py`,
`TestTheRunnerItself.test_every_suite_forking_test_in_this_file_stands_down_in_a_child`.

It recognises a suite-forking function by an `ast.Constant` equal to `"run_tests.py"` inside it. A
function that builds the same path from a module constant is invisible to it — measured: rewriting
the spawn as `TEST_DIR / RUNNER_NAME` leaves `forking == []`. The test's own vacuity guard turns
that into a red rather than a silent pass:

```
AssertionError: [] is not true : no function in test/run_tests.py spawns the suite —
this assertion must not be able to pass vacuously
```

so the failure mode is loud, not quiet. **REPEAT?** No. *Fix (optional):* also treat a call to a
helper that itself forks as forking, or match on `TEST_DIR` usage; the vacuity guard already makes
this safe enough to leave.

### Record-only (measured, no change requested)

- **The four round-1 suite-forking pins still write into the repo's own `test/issues/`**
  (`test_issue_zz_discovery_probe.py`, `test_issue_zz_memory_probe.py`) and remove them; after a
  full run only their `.pyc` remains under `test/issues/__pycache__`, which `.gitignore` covers.
  Inherent — those pins must spawn the real runner over the real discovery dir — and it is why
  "run the suite serially per checkout" is a standing instruction. N6's new test is the pattern
  that avoids it (`build_suite(discovery_dir=…)` against an `mkdtemp`), and plants nothing.
- **Malformed `GITHUB_EVENT_PATH` payloads fail closed** at rc 5 (jq under `set -e`) with nothing
  minted, though without an `eval.yml:`-prefixed message. GitHub writes that file, so it is not
  attacker-reachable.
- **`test_the_runner_says_what_can_and_cannot_police_its_own_exit_code`'s first assertion is a
  text `in` over the runner's source.** That is a comment-string pin, not a claim about code
  shape, so it is outside the "parse an AST, never a regex" rule; the half that *is* a code-shape
  claim (the two pin names still being defined) is parsed with `ast`.
- **The worker's merge table reproduces exactly** when "ours" is read as the merge's first parent
  `c27994a` rather than the round-2 head `c5ea933`; §6 gives both readings.
- **`EXTRA_PASSTHROUGH = ()`** is an empty extension point on `agent_env`'s allowlist; a name added
  there would be measured by the A6 pin (which derives its required list from the live
  `guidance.agent_env`), so it cannot be omitted from the header silently.

---

## 9. What I could not measure

- **No real dispatch.** Everything about the OIDC exchange, the WIF preflight and the real `claude`
  CLI is inference from the parsed workflow plus the validation step's `run:` block executed
  locally. The ordering guarantee is proven by parsed step index **and** by execution; that the
  *exchange step itself* behaves as documented is not.
- **Real-model probe behaviour.** S-A's residual severity still depends on how often a real model
  answers with one word when two are in context. I measured the harness's response to both
  arities through the production prompt; I could not measure the model.
- **The `_agent-guidance` sibling is pinned at `3d972b4`** in this container; a manifest change
  upstream would move the 28-row extent identity, and I could not test against another revision.
- **The M4 mutation's per-row breakdown came from a re-run**, because my first pass piped the
  output through `tail -40`. The re-run (`Ran 1 test in 300.6s / FAILED (failures=12)`) names all
  12 rows — 4 knobs x {2200000, 1e9, 2701} — and I report that, not the truncated first log.
- **Two concurrent full-suite runs in one checkout** would race over the planted probe modules
  above. I did not run that race deliberately; I ran serially per checkout throughout.
