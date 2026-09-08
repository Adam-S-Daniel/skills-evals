# PR #138 fix round 2 — worker report (two PR comments, 20:28 and 20:29 UTC 2026-09-07)

<!-- comment 5575354303 2026-09-07T20:28:02Z https://github.com/Adam-S-Daniel/skills-evals/pull/138#issuecomment-5575354303 -->

## Fix round 2 — verifier output (worker), part 1 of 2

> Posted as a comment, not appended to the PR description, deliberately: the description is already ~30 KB of the orchestrator's own status prose, and editing it means re-emitting all of it verbatim in one call. A comment carries the same numbers and cannot clobber or corrupt an earlier section. Nothing in the description is deleted.

Worker [session_019ciz5F5NQjSgwu9ZpHhgsr](https://claude.ai/code/session_019ciz5F5NQjSgwu9ZpHhgsr) (Opus 5), `CLAUDE_CODE_EFFORT_LEVEL=xhigh`. Fourteen commits, one per item, plus one merge of `main`; all noreply identity, plain pushes, no amend/rebase/force-push. **Not merged.**

**Environment.** `markdown-it-py==4.2.0`; `_agent-guidance` `main` at **`5f13def4288442a44f28473836819a29bd490944`** as the sibling `../_agent-guidance`; `agentskills` at `cd5ad3e` as `../agentskills` (without the latter `TestIssue63::test_registries_agree_with_agentskills_own_file` skips and the count reads 3 skipped, not 2). Every suite run and every probe with `HOME` and `$SKILLS_EVALS_USER_MEMORY` pointed at a throwaway directory; no real `claude` and no real `gh` was run. `md5sum /root/.claude/CLAUDE.md` is **`935c291f2efb1ff55a463bccfde55e6a`** before the first command of this session and after the last.

**Baseline on `c5ea933`, with that environment: `Ran 685 tests … OK (skipped=2)`, exit 0; `python3 test/test_propagation.py` → `Ran 164 tests … OK (skipped=1)`, exit 0.** Exactly the counts the brief predicted. (The very first baseline read 3 skipped because this container had no `../agentskills` sibling; cloning it, as `ci.yml` does, brought it to 2.)

**STEP 0.** At the start of the round `origin/main` was still `d5e06ee` — so, in the brief's own words, there was nothing to merge. It advanced to **`7c966ba`** (PR #136) mid-round and the PR went `dirty`, so the same rule was applied then instead: see *Second merge of `main`* in part 2.

### Commits

| Item | Commit | What it is |
|---|---|---|
| S1 | `ea2b770` | `MAX_TIMEOUT_S`, an upper bound in the same predicate, anchored to eval.yml by a parsed test |
| N1 (adv) + N4 (code) | `26491bd` | neither rejection branch echoes the dispatched value |
| N2 (adv) | `fd2bcff` | the A6 sentence names `WORKSPACE` and the fixture `env:` overlay |
| N3 (adv) | `47e01fa` | the residual paragraph names both reasons, not only ambiguity |
| N4 (adv) | `778f325` | the contamination check runs in both directions |
| N5 (adv) | `9f5772b` | a `-k` that selects nothing is exit 2 |
| N6 (adv) | `dd2d7c4` | the empty-module failure names the module and says it defines no tests |
| N7 (adv) | `d8f298f` | a targeted run is covered by the user-memory guard too |
| S-A | `5cec429` | the guard prompt asks for EVERY magic word |
| S-B | `f69a2d8` | the suite-forking pin stands down in a child |
| N1 (code) | `89039e1` | the A2 timeout rows run in a bounded child |
| N2 (code) | `6a1ff2b` | the nested-fixture glob made falsifiable |
| N3 (code) | `feb49a4` | a NUL in the dispatch value refused before the substitution |
| N5 (code) | `c27994a` | what can and cannot police the runner's own exit code |
| — | `a6d165d` | Merge `origin/main` (`7c966ba`, PR #136) |

Every one verified with `git merge-base --is-ancestor <sha> origin/claude/skills-evals-97`: **15 of 15 ANCESTOR OK**, head `a6d165d` equal to the remote. `git log --format='%ae %ce' c5ea933..HEAD --not origin/main`: all 15 authored *and* committed by `4205216+Adam-S-Daniel@users.noreply.github.com`. (The unscoped `c5ea933..HEAD` range also contains main's own PR #136 commits, five of them `noreply@anthropic.com` plus one GitHub merge committer; they arrived with the merge and are not from this round.)

### Suites

```
$ python3 test/run_tests.py                 exit 0   Ran 788 tests   OK (skipped=2)
$ python3 test/test_propagation.py          exit 0   Ran 164 tests   OK (skipped=1)
$ python3 test/run_tests.py -k TestIssue97  exit 0   NARROWED RUN: -k selected 102 of 788
$ python3 test/run_tests.py -k NoSuchThingAtAll      rc=2
    FAILED: -k 'NoSuchThingAtAll' selected 0 of 788 tests. A pattern that
    matches nothing is a typo, not a clean run: an empty measurement is not a
    passing one.
```

685 at `c5ea933` → **703** after the fourteen item commits → **788** after the merge. Arithmetic: 703 + (673 on main at `7c966ba` − 588 on main at `d5e06ee`) = 788. Measured 788.

### S1 — the timeout ceiling

`MAX_TIMEOUT_S = 45 * 60`, checked in the same predicate as the lower bound (`0 < value <= MAX_TIMEOUT_S`), with `test_the_timeout_ceiling_is_the_workflow_job_budget` parsing `.github/workflows/eval.yml` with `yaml.safe_load`, reading the eval job's `timeout-minutes`, and asserting the constant equals it × 60. Every row driven through the real CLI entry point:

| knob | 2 200 000 | 1e9 | 2701 | 2700 | 600 |
|---|---|---|---|---|---|
| `timeout_s` | rc 2 | rc 2 | rc 2 | rc 0 | rc 0 |
| `setup_timeout_s` | rc 2 | rc 2 | rc 2 | rc 0 | rc 0 |
| `guard.timeout_s` | rc 2 | rc 2 | rc 2 | rc 0 | rc 0 |
| `judge.timeout_s` | rc 2 | rc 2 | rc 2 | rc 0 | rc 0 |

Every rc-2 row's first output line is the named message, e.g.

```
fixture configuration error: /tmp/s1row-u7fpql3w/eval/fixture.yaml:
`guard.timeout_s` must be a positive number of seconds no greater than 2700
(eval.yml gives the eval job that many), got 2200000. …
```

and each asserts no `Traceback`, no `OverflowError`, and — via `$FAKE_CLAUDE_ARGV_LOG` — **zero CLI invocations**: the check runs at fixture load, before any subject branch.

**Mutation (drop the upper bound, keep everything else): `Ran 3 tests in 301.925s / FAILED (failures=12)`, exit 1.** All twelve rejected rows red; two of them (`guard.timeout_s` at 2 200 000 and at 1e9) on the bare `OverflowError: timeout is too large` the reviewer measured, the other ten on the new outer bound. The ten lower-bound rows (`null`, `"abc"`, `0`, `-1` across the four knobs) are unchanged and still rc 2 with `positive number` in the message.

### N1 (adversarial) = N4 (code) — the second rejection branch

`echo "…names no committed fixture: $fixture"` → `echo "…names no committed fixture"`, and the comment block above the gate now says both branches obey the rule and why naming the value buys nothing. The existing echo pin covered the shape branch only; it now drives **both** through the real `run:` block with a marker that appears nowhere in the committed tree. Red on `c5ea933`:

```
AssertionError: 'uniquely-identifiable-payload' unexpectedly found in
"eval.yml: dispatch input 'fixture' names no committed fixture:
evals/uniquely-identifiable-payload\nCommitted fixtures:\n …" :
the no such fixture branch echoed the dispatched value back into a public log
```

The `case` character class, the here-string, the `find` and the step order (validate → mint → preflight) are untouched.

### N2 (adversarial) — the A6 sentence

New sentence, verbatim (line-folded as the pin reads it):

> a GUIDANCE arm's agent gets an ALLOWLIST built from nothing (harness/guidance.py's `agent_env`): PATH, LANG, LC_ALL, SHELL, USER, NODE_PATH, plus the HOME, TMPDIR, CLAUDE_CONFIG_DIR and WORKSPACE the harness sets and every ANTHROPIC_\* variable, and on top of all of that the fixture's own `env:` block, which may add any name except those three isolation variables (HOME, TMPDIR, CLAUDE_CONFIG_DIR are refused by name, because the block is applied after they are set, so a fixture allowed to name one could point an arm at the real config dir). The two GitHub tokens above are NOT in that set.

The pin no longer restates the list — it derives it from the measured environment (every name `guidance.agent_env` returns, bar the `ANTHROPIC_*` family the header names as a family, must appear in the header), so the next name added there cannot be omitted the same way. Measured against a 93-name hostile parent: `agent_env` returns 11 names, `WORKSPACE` among them; with a fixture `env:` block it returns 12, the extra one `$WORKSPACE`-expanded. Red on `c5ea933`:

```
AssertionError: 'WORKSPACE' not found in '…' : WORKSPACE is in the guidance
arm's environment (measured through guidance.agent_env) and the header does
not name it
AssertionError: '`env:` block' not found in '…' : the header must say the
fixture's own `env:` block is applied on top of the allowlist
```

### N3 (adversarial) + S-A — the residual paragraph

The paragraph in `harness/guidance.py`, verbatim after both commits (README and DESIGN carry the same two clauses in their own wording):

> THE RESIDUAL the guard does NOT settle: a control arm that reads its own scratch memory AND an ambient one in addition — a real `~/.claude/CLAUDE.md` alongside the delivered decoy — is prevented by the per-arm HOME and CLAUDE_CONFIG_DIR isolation rather than by the guard. TWO reasons, and the one this paragraph used to give is the narrower: a probe asked for the magic words when its context carries two may report either, **and a contaminating source that carries no token of its own is invisible to a token guard at all.** Measured, both of these score clean: an ambient file carrying a STALE token (no current run's token is in the reply, so there is nothing to catch) and the real base.md, which carries no token whatsoever. Only a real dispatch settles it.
>
> The two-word case is the DECOY'S OWN DOING, and is why GUARD_PROMPT asks for every magic word rather than "the magic word": before the decoy a contaminated control carried exactly one magic word — the treatment token — and had to report it, and the decoy gave that token somewhere to hide. A one-word answer from a contaminated control is the case the plural prompt exists for.

Both clauses are pinned by their operative words — the first in `guidance.py`, the second in all three places. Red on `c5ea933`:

```
AssertionError: 'a contaminating source that carries no token of its own is
invisible to a token guard at all' not found in '…'
```

### N4 (adversarial) — the guard is two-sided in both directions

`forbidden_token: str | None` → `forbidden_tokens: tuple[str, ...]`, and each arm's set is *every token this run minted that was not delivered to it* — one expression, symmetric by construction. That needs the decoys before any arm runs, so they are minted once in the run's `ctx` (one per `none` arm) instead of inside the arm that gets one.

`run_guard`'s docstring, verbatim:

> `token` is the token THIS arm was delivered — the run's magic token for a treatment arm, its own decoy for the control. `forbidden_tokens` is every OTHER token the run minted: the treatment token for a control arm, and the control's decoy for a treatment arm.
>
> BOTH directions, because contamination has two. The loud one is a control arm reached by the guidance. The quiet one is a treatment arm that reads the CONTROL's scratch user memory — the same per-arm isolation failure seen from the other side, and just as fatal to the pair, because the two arms are then not measuring two different contexts. Only the control was given a forbidden token, so the quiet one scored clean: measured, a treatment arm whose probe reported both the treatment token and the control's decoy exited 0 with every check passing.

`new_decoy_token`'s, verbatim:

> The control is delivered this, and only this, through the same hook — so its probe reporting the decoy proves the arm reads ITS OWN scratch user memory, and its probe reporting the TREATMENT token proves it was contaminated. **EVERY arm's guard is two-sided for that reason, not only the control's: the decoy is also the forbidden token a TREATMENT arm must not report, which is how a treatment arm reading the control's scratch memory is caught rather than scored.**

and the module docstring's guard paragraph now opens "Every arm's guard is TWO-SIDED: it reports the token it was delivered, and it reports no token it was not." `_guard_error`'s `guard_contaminated` detail, README and DESIGN name both directions.

Rows through `main()` with an ambient file carrying the control's decoy: the treatment arm is rc 2, `guard_contaminated`, `observed` true, `contaminated` true, `objective_checks` null, and the control in the same run is untouched (`contaminated` false). Red on `c5ea933`:

```
AssertionError: 0 != 2 : a treatment arm whose probe reported the control's
decoy must be INCONCLUSIVE, never scored (stdout: '')
```

The paired row pins the other side (a treatment arm reading only its own payload is still clean, `contaminated` false, decoy absent from its reply), so a guard that condemned every arm would not satisfy the first. The control arm's existing rows are unchanged.

*(continued in part 2)*

---
_Generated by [Claude Code](https://claude.ai/code)_

<!-- comment 5575361687 2026-09-07T20:29:00Z https://github.com/Adam-S-Daniel/skills-evals/pull/138#issuecomment-5575361687 -->

## Fix round 2 — verifier output (worker), part 2 of 2

*(continues [part 1](https://github.com/Adam-S-Daniel/skills-evals/pull/138#issuecomment-5575354303))*

### N5, N6, N7 — the runner

**N5.** `-k` selecting zero tests is exit 2 with the pattern named. Measured on `c5ea933`: `NARROWED RUN: -k selected 0 of 691 tests …` / `Ran 0 tests in 0.000s` / `OK` / `rc=0`. On the new head: `rc=2` with the message quoted under *Suites* in part 1. `-k TestIssue97` still narrows (102 of 788, exit 0). The four inline lines of the S2 guard become `memory_guard()` so the new exit path passes through it rather than returning around it. Red with the check removed: `AssertionError: 0 != 2 : NARROWED RUN: -k selected 0 of 692 tests …`.

**N6.** The planted-empty-module failure now names the module and says it defines no test. Measured on `c5ea933` with `test/issues/test_issue_zz_empty.py` containing only `VALUE = 1`:

```
AssertionError: Items in the first set but not the second: 'test_issue_zz_empty'
: build_suite() must carry at least one test from EVERY test_issue_*.py module
under /home/user/skills-evals/test/issues; missing: ['test_issue_zz_empty']
```

which sends the reader to `build_suite()` when the fault is in their own file. The new assertion is driven against a SCRATCH discovery dir (`build_suite()` takes it as an optional parameter for that), so nothing is planted in the repo and a concurrent run cannot see it; `sys.path` and `sys.modules` are restored. Red with the old wording: `AssertionError: 'defines no test' not found in "build_suite() must carry at least one test from EVERY …"`.

**N7.** The S2 snapshot moves above the targeted-run branch and that branch returns through `memory_guard()`. The probe is a `TestCase` injected into the module for the duration (a targeted run addresses this module's own classes and nothing else) and writes only the throwaway `$SKILLS_EVALS_USER_MEMORY` path. Red with the return moved back around the guard: `AssertionError: 0 != 1 : a targeted run that changed the watched user-memory file must exit 1 even though its test passed`. The paired row pins that a targeted run touching nothing still exits 0.

### S-A — the plural guard prompt

`GUARD_PROMPT`, and the same text in both canary fixtures:

> If your context contains any magic words, reply with every one of them and nothing else. If it contains none, reply with exactly NO-MAGIC-WORD. Do not use any tools.

`test/fake-claude` gains `guidance_probe_literal`, which answers the question it was ASKED — every magic word when the prompt asks for every one of them, otherwise the first it finds — keyed off a `PLURAL_MARKER` constant that the suite reads back out of the fake with `ast` and asserts `GUARD_PROMPT` still carries. The honest every-word `guidance_probe` and all its rows are unchanged.

Rows through `main()` with a contaminated control (an ambient file carrying the treatment token) and that probe: **rc 2, `guard_contaminated`**, `contaminated` true, no score. The paired row pins that a clean control under the same probe still scores (rc 0). **Mutation — revert the prompt wording alone, keeping the fake and everything else:**

```
AssertionError: 0 != 2 : a contaminated control must never score clean,
whatever arity its probe answers with (stdout: '')
AssertionError: 'If y[…]ins any magic words, reply with every one of t[…]ols.'
!= 'If y[…]ins a magic word, reply with that magic word a[…]ols.'
AssertionError: 'every one of them' not found in 'If your context contains a
magic word, reply with that magic word and nothing else. …'
```

i.e. the end-to-end row, the canary-prompt equality pin and the marker pin all go red together.

**The canary prompt diff against `origin/main`** — the whole of this PR's `evals/` diff:

```
$ git diff --stat origin/main..HEAD -- evals/
 evals/guidance-bridge-canary/fixture.yaml |   6 +-
 evals/guidance/_delivery/fixture.yaml     | 105 ++++++++++++++++++++++++++++++
 2 files changed, 108 insertions(+), 3 deletions(-)

$ git diff origin/main..HEAD -- evals/guidance-bridge-canary/
 prompt: >
-  If your context contains a magic word, reply with that magic word and
-  nothing else. If it does not, reply with exactly NO-MAGIC-WORD. Do not use
-  any tools.
+  If your context contains any magic words, reply with every one of them and
+  nothing else. If it contains none, reply with exactly NO-MAGIC-WORD. Do not
+  use any tools.
```

`evals/guidance/_delivery/fixture.yaml` is new on this branch and carries the same wording. The bridge canary's separate `subagent_prompt` is deliberately untouched: it probes a SUBAGENT's context, which carries one token per layout, and it is not pinned to `GUARD_PROMPT`. Nothing else under `evals/` differs from `origin/main`, and `git diff --name-only c5ea933 c27994a -- evals/` names **no `seed/` path** (0 of them).

### S-B — the suite-forking pin

`test_dash_k_on_the_command_line_still_reaches_the_discovered_subtree` is the **only** test in `test/run_tests.py` that shells out to the whole suite; the four in `test/issues/test_issue_97.py` (`test_planted_issue_module_is_discovered_and_fails_the_runner`, `test_removing_the_planted_module_puts_the_runner_back_to_zero`, `test_the_run_wide_user_memory_guard_fails_a_run_that_writes_the_file`, `test_an_ordinary_run_leaves_the_watched_file_alone`, all via `_run_suite`) already call `_skip_in_child()`. Enumerated by AST, not by eye.

**Measurement**, in a scratch copy of the repo (no `.git`, so no inherited remote) with the S3 defect reverted — `select_tests` returns everything, `-k` narrowing broken — running that one test alone:

| | peak concurrent `run_tests.py` processes | parent |
|---|---|---|
| guarded (this commit) | **2** | returns in 30.2 s, FAILS correctly (the child ran 788 tests, not 1) |
| unguarded (`c5ea933`) | **8 and still climbing** | never returns; killed by a 150 s bound |

The unguarded counts over time, one sample per second: 1 → 2 at 2 s → 3 at 20 s → 4 at 40 s → 5 at 61 s → 6 at 83 s → 7 at 105 s → 8 at 128 s. The runaway tree was killed by pid afterwards and the scratch copy removed; `ps` confirmed 0 remaining.

A new AST pin keeps it that way: `test/run_tests.py` is **parsed** (never scanned as text), every function that both names `run_tests.py` and calls `subprocess.run` must call `self._skip_in_child()`, and the assertion refuses to pass over an empty set. Red without the guard:

```
AssertionError: False is not true :
test_dash_k_on_the_command_line_still_reaches_the_discovered_subtree
(line 10169) spawns the whole suite but never calls self._skip_in_child(),
so nothing bounds it when it IS the child: it forks again, and again
```

N5's new test is the same hazard one class down — it calls `main()` in process, so a broken `-k` would make it run the whole suite from inside the suite — so it now asserts its sentinel pattern selects zero *before* calling `main()`, turning that case into a plain red too. That is what made the S-B measurement above possible.

### N1, N2, N3, N5 (code half)

**N1.** Every timeout row now goes through the real CLI entry point in a child with a 30 s outer bound (`_run_main_subprocess`; the S1 rows take the same path). With `validate_timeouts` disabled entirely the battery returns **`Ran 2 tests in 210.746s / FAILED (failures=11)`**, seven of them on the outer bound's own message, where in-process it did not return at all.

**N2.** The `evals/**/fixture.yaml` sweep moves into one shared helper and a second test plants a nested skill fixture in its own mkdtemp copy. Mutation to `*`:

```
AssertionError: PosixPath('/tmp/nested-fixture-l8fyadln/evals/family/nested/
fixture.yaml') not found in [PosixPath('/tmp/nested-fixture-l8fyadln/evals/
top/fixture.yaml')] : the sweep must reach a fixture nested below the top
level of evals/
```

Worth recording: the merge of `main` brought two genuinely nested skill fixtures onto the committed tree (`evals/writing-adrs/{bootstrap,existing-convention}`), and the committed half is **still** not red under that mutation — it asserts only `checked > 0`, which a single-level glob satisfies. The scratch half remains the only thing that falsifies the spelling.

**N3.** A `jq -e` test on the event file, before any substitution and before the `case` guard, refuses a NUL with a named message and no value echoed. Measured on `c5ea933` through the same `run:` block, all four rows accepted:

```
AssertionError: 0 != 1 : leading: a NUL anywhere in the dispatch value must fail the step
AssertionError: 0 != 1 : trailing: …
AssertionError: 0 != 1 : embedded, collapsing to a committed name: …
AssertionError: 'NUL byte' not found in "eval.yml: dispatch input 'fixture'
names no committed fixture: evals/nope … bash: line 7: warning: command
substitution: ignored null byte in input"
```

The accepted rows are unchanged, asserted in the same test. The `case` character class, the here-string, the `find` and the step order are untouched.

**N5.** One comment beside `status = 0 if result.wasSuccessful() else 1` saying nothing inside the runner can police that line and naming the two child-rc pins that can, with a test requiring both names to still be defined (`test_issue_97.py` parsed with `ast`) and the sentence to still be in `main()`. Red with the comment removed.

### Second merge of `main`, inside this round

`origin/main` advanced from `d5e06ee` to **`7c966ba`** (PR #136: the `writing-adrs` fixtures, the `file_count` objective check, ~1800 lines of new tests) while this round was running, and the PR went `dirty`. Merged as its own commit (`a6d165d`), and checked rather than trusted.

One conflict, resolved as the **union**: README.md's `evals/` tree, where main's `writing-adrs/` rows and this branch's `disarm-inherited-reach/` rows land at the same append point. Both kept.

`test/run_tests.py` auto-merged and was verified by **AST**, not by reading the diff:

| | ours | theirs | merged | missing (ours) | missing (theirs) | invented |
|---|---|---|---|---|---|---|
| classes | 32 | 32 | 35 | none | none | none |
| top-level functions | 13 | 5 | 13 | none | none | none |
| test methods | 603 | 673 | 688 | none | none | none |

This branch's runner machinery survives intact: `memory_guard`, `build_suite`'s `discovery_dir` parameter, `_skip_in_child`, `_fixture_dirs`, `_uncovered_message`, `CHILD_RC_PINS`, the zero-selection branch, the `NARROWED RUN` lines. `ci.yml` carries both sides — main's `README.md`/`DESIGN.md` paths entries and this branch's `_agent-guidance` checkout and `markdown-it-py` pin. Count arithmetic: 703 + (673 − 588) = **788**, measured 788.

### Rule 19 and the workflow guardrails

Every fixture under `evals/` scored with `--arm objective-only` on this head and on a plain export of `origin/main` (`7c966ba`), compared per check (id, type, passed, and the detail string with `/tmp/…` names normalized):

| fixture | rc main | rc head | identical |
|---|---|---|---|
| `disarm-inherited-reach` | 1 | 1 | YES |
| `github-actions-sha-pinning` | 1 | 1 | YES |
| `guidance-bridge-canary` | 2 | 2 | YES |
| `post-failure-comment` | 1 | 1 | YES |
| `propagation` | 2 | 2 | YES |
| `rename-pdfs` | 1 | 1 | YES |
| `review-bash-ci-reliability` | 1 | 1 | YES |
| `windows-elevation-from-wsl` | 1 | 1 | YES |
| `workflow-path-audit` | 1 | 1 | YES |
| `writing-adrs/bootstrap` | 1 | 1 | YES |
| `writing-adrs/existing-convention` | 1 | 1 | YES |
| `guidance/_delivery` | absent | **2** | new on the branch |

**11 identical, 0 differing.** The guidance canary's objective-only run exits **2**, per N-f: *"evals/guidance/_delivery/fixture.yaml declares no top-level `objective_checks:` — objective-only has nothing to score. A guidance fixture's checks are per arm; run it with `--arm both` (or a named arm) instead."*

All six workflows parsed with `yaml.safe_load`:

```
6 workflows parsed with yaml.safe_load
26 run: blocks, 0 containing `${{`
25 uses: refs, all bare 40-hex SHAs except the cms-platform carve-out:
  scheduled-run-health.yml:audit -> Adam-S-Daniel/cms-platform/.github/workflows/scheduled-run-health.yml@v0.1.87
violations: 0
```

That one tag ref is the fleet's documented carve-out (a ref into this account's own `cms-platform` stays on its release tag), pre-existing and untouched here.

```
$ git diff --stat origin/main..HEAD -- .github/
 .github/workflows/ci.yml   |  16 +++-
 .github/workflows/eval.yml | 195 +++++++++++++++++++++++++++++++++++++++-----
```

`eval.yml` and `ci.yml` only.

### Recorded, deliberately not changed

- The `_agent-guidance` manifest's `file:` is not constrained to the checkout: a `file: ../x.md` row is read and its content reaches `results/`. Inside the trust boundary the header already states.
- `deliver()`'s timeout kills the direct `bash` child but not its descendants; the real hook spawns nothing long-lived.
- The control arm now carries the hook's marker wrapper around the decoy paragraph (documented).
- `NODE_PATH` is the one loader-influencing name in `PASSTHROUGH` — deliberate, and pinned.
- The new `_agent-guidance` checkouts carry no `ref:` pin; the three registry checkouts already there follow the same convention.
- `dependabot-auto-merge.yml`'s checkouts lack `persist-credentials: false` (pre-existing, untouched).
- `aa03ac0` (`noreply@anthropic.com`) is an ancestor of `origin/main`, not this branch's commit.
- N2 (code): even after the merge brought nested skill fixtures onto the committed tree, the committed half of that test stays green under the `*` mutation — it asserts only `checked > 0`. Left as is; the scratch half is what falsifies the spelling, and it cannot go vacuous when main's fixture layout changes.

### Not done, and why

- **No real dispatch, and no real `claude` or `gh` was run** — the brief forbids both, and `eval.yml`'s WIF rule pins `sub` to `main`, so the first real run still happens after merge.
- **The skill arm still inherits the runner's ambient environment.** A6's sentence says so (and now says what the guidance arm gets instead); re-pointing it at the allowlist is the separate PR already on the board.
- **The verifier output is in these two comments rather than appended to the PR description**, for the reason given at the top of part 1.
- **Not merged**, per the brief.

---
_Generated by [Claude Code](https://claude.ai/code)_

