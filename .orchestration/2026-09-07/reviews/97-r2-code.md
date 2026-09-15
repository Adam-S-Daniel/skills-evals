FOUND — 0 blocker, 2 should-fix, 6 nit

Round-2 code review (one-way-door half) — PR [#138](https://github.com/Adam-S-Daniel/skills-evals/pull/138),
issue [#97](https://github.com/Adam-S-Daniel/skills-evals/issues/97), head `c5ea933b8f0b6c9cab94bf97365b84e3770aa727`,
base `origin/main` = `d5e06ee`, round-1 head `34ab8fc`.

Every round-1 item (B1, B0/S1, S2, S3, S4, S5, A2, A3, A4, A5, A6, N-a..N-i) **landed and
survives a revert-the-fix mutation**, except the two noted below where the mutation cannot
go red today and I say why. The two merges of main are an exact union with nothing dropped.
Rule 19 holds. The key-bearing workflow's gate was executed under bash against 43 hostile
inputs and **nothing was minted or exported before any rejection**.

The two should-fix items are both *new*, and both arrive **through the brief's own prescribed
remedies** — not through a worker error, and neither is a repeat of a round-1 item.

---

## 0. Safety ledger and tree integrity

| | Before first command | After last command |
|---|---|---|
| `/root/.claude/CLAUDE.md` (the real one) | `935c291f2efb1ff55a463bccfde55e6a` | **`935c291f2efb1ff55a463bccfde55e6a`** — unchanged |
| `$SP/r2w97-home/.claude/CLAUDE.md` (throwaway stand-in) | `9060e351f5bbba2453ebc47353cd380b` | **`9060e351f5bbba2453ebc47353cd380b`** — unchanged |

Every suite run and every mutation ran with `HOME=$SP/r2w97-home`. Both files were
fingerprinted around each of the destructive mutations (B0, S2, S3c) individually as well;
all four readings unchanged. Nothing was ever written under `/root/.claude`. No code path
under test resolved a path under the real HOME (measured — §5, B0/S1).

**Work-dir integrity.** Named md5s verified at start **and** at end, all six identical to
the brief:

```
95c4bb22ee084a3dc974df968f920285  harness/guidance.py
9497375d0d37a57549ff072f31b0a865  harness/run_eval.py
cd5d4f8eb1348765074f04cd2f831bd4  test/run_tests.py
87b7e5bcb35e36b332537eab29600b22  test/issues/test_issue_97.py
95f4d9ea942cb10e6e74b8fe46d8441e  .github/workflows/eval.yml
f40ae7e1aeef5359ffd9be45e2977ada  .github/workflows/ci.yml
```

`diff -rq $SP/rev97b-code <fresh git archive c5ea933>` → **BYTE-IDENTICAL**. The artefacts the
suite creates were cleaned: seven `__pycache__` directories (two holding
`test_issue_zz_discovery_probe` / `test_issue_zz_memory_probe` `.pyc` files), `results/`, and
the planted probe modules (the suite removes the `.py` files itself; only the `.pyc` survived).
`rev97b-ref`, `mainx4`, `_agent-guidance` and `agentskills`: **0 files modified**. All mutations
ran in `$SP/r2mut97-*` copies, now deleted. I entered none of the other reviewers' directories.

**Processes.** All mine are dead, verified by `ps`. I killed one fork bomb of my own making
(finding **S-B** — the S3b mutation) and one hung `fake-claude` guard probe left by the A2
mutation (finding **A2** — that hang *is* the measurement). I left the sibling sessions'
`r2adv97-*` and `r2mut129-*` processes alone.

---

## 1. Verifiers

| Verifier | Exit | Result | Skips (every reason) |
|---|---|---|---|
| `python3 test/run_tests.py` (start of session) | **0** | **Ran 685 tests**, 141 s | 2 — `pypdf not installed` ×2 |
| `python3 test/run_tests.py` (end of session, clean tree) | **0** | **Ran 685 tests**, 144 s | 2 — same |
| `python3 test/run_tests.py -v` | 0 | **Ran 685 tests** | 2 |
| `python3 test/run_tests.py -q` | 0 | **Ran 685 tests** | 2 |
| `python3 test/run_tests.py --failfast` | 0 | **Ran 685 tests** | 2 |
| `python3 test/test_propagation.py` | **0** | **Ran 164 tests** | 1 |
| `python3 test/run_tests.py` with `SKILLS_EVALS_SUITE_CHILD=1` | 0 | Ran 685 tests, 38 s | 6 (+4 forking pins) |

`grep -c TestIssue97` on the `-v` output = **91** (round 1: 0). The 2 skips are `pypdf`, not
guidance — the `_agent-guidance` sibling at `3d972b4` is present so all 11 real-hook tests ran;
`agentskills` is present so `TestIssue63…agentskills_own_file` ran too (hence 2, not 3).

---

## 2. Per-item certification

Mutations ran the **full 685-test suite** in a throwaway copy. Where a mutation ran in
`SKILLS_EVALS_SUITE_CHILD=1` mode, the four suite-forking pins skip, which removes the
collateral reds they otherwise contribute (they each spawn a full child suite that also
carries the mutation) — B0, S2 and S3c were re-run **without** child mode for exactly that
reason, and those rows say so.

| Item | Landed? | Red-first on `34ab8fc` | Mutation | Verdict |
|---|---|---|---|---|
| **B1** dispatch gate | yes | **RED** — `0 != 1 : 'evals/workflow-path-audit\ne...' must fail the step` (all 4 multi-line rows exit 0 on ref) | delete the `case` block → all 4 multi-line rows rc 0, whole 2-line string reaches **both** outputs; suite **2 red** | **PASS** |
| **B0/S1** no real HOME to a writer | yes | floor (`_refuse_real_config_dir` pre-existed; pure-fn pin green on ref — correct) | delete the call → `test_delivery_refuses_the_real_config_dir` **red (3 failures)**, real file **and** stand-in **byte-unchanged**; full suite non-child rc 1 | **PASS** |
| **S2** run-wide memory snapshot | yes | **RED** — `Lists differ: [] != ['SKILLS_EVALS_USER_MEMORY']`; both guard tests FAIL on ref | delete `after != before` (non-child) → rc 1, **1 red**, both memory files unchanged | **PASS** |
| **S3** discovery + argv | yes | **RED** — on ref `-v`/`--failfast` run **379** and exit 0; `-k <t>` runs **0 tests** and prints OK; spliced class → 1 FAIL + 5 ERROR | disable discovery → rc 1, **2 red**, 594 tests (round 1: 0 red, exit 0); `status=0` → 7 red on screen but rc 0 (nit N5) | **PASS** (see N5, S-B) |
| **S4** `PASSTHROUGH` pinned exactly | yes | floor (green on ref — correct) | `+GITHUB_TOKEN` → **2 red**, two independent pins (`…committed_six` and the A6 header test) | **PASS** |
| **S5** no pipe into grep | yes | **RED** — 19 failures, "failed CLOSED on a valid fixture" at 118,826 B | restore the pipe → **1 red** | **PASS** |
| **A2** timeout validation | yes | **RED** — all 10 subtests ERROR on ref | remove `validate_timeouts` → the suite **HANGS** (guard probe alive 498 s, `timeout=None`) | **PASS** |
| **A3** `delivery_failed` | yes | **RED** — both tests ERROR on ref | `if False:` → **2 red** | **PASS** |
| **A4** two-sided control guard | yes | **RED** — 25 `AttributeError … new_decoy_token` on ref | A4a `mode != "none"` → **7 red**; A4b no decoy → **3 red**; A4c no `forbidden_token` → **1 red** | **PASS**, see **S-A** |
| **A5** `arms:` shapes | yes | **RED** (absent-key floor green on ref — correct) | restore the `or` → **2 red** | **PASS** |
| **A6** header per subject | yes | **RED** — `True is not false : the header still claims the WIF token is 'the only credential in reach'` | restore the old sentence → **1 red** | **PASS** |
| **N-a** empty payload refused | yes | **RED** (FAIL on ref) | `if False:` → **2 red** | **PASS** |
| **N-b** extent docstring unit clause | yes | **RED** (FAIL on ref) | — (string pin; the ref FAIL is its teeth) | **PASS** |
| **N-c** budget comments + generalised test | yes | green on ref *because the ref has no 5-arm defaults fixture*; red-first shown with a planted one: `4500 not less than 2025.0` | restore the stale comment → **1 red** | **PASS** |
| **N-d** quoted rejection listing | yes | **RED** (FAIL on ref) | `printf '  %s\n' $committed` → **1 red** | **PASS** |
| **N-e** `evals/**/fixture.yaml` | yes | green on ref | `*/fixture.yaml` → **0 red** — unfalsifiable today, see nit **N2** | **LANDED, no teeth today** |
| **N-f** objective-only exits 2 | yes | **RED** (ERROR on ref) | `if False:` → **1 red** | **PASS** |
| **N-g** lazy `markdown_it` | yes | **RED** (FAIL on ref) | eager import → **1 red** | **PASS** |
| **N-h** `env:` isolation refusal | yes | **RED** — `AttributeError … ISOLATION_NAMES` on ref | `if False:` → **1 red** | **PASS** |
| **N-i** "present in this checkout" | yes | **RED** (FAIL on ref) | reword the header sentence → **1 red** (my first anchor hit a *different* copy of the phrase; corrected — see nit) | **PASS** |
| **merge `eb7d174`** (main `f82bd77`, PR #135) | yes | n/a | AST union, see §6 | **EXACT UNION** |
| **merge `c5ea933`** (main `d5e06ee`, PR #132) | yes | n/a | AST union, see §6 | **EXACT UNION** |

### A2 — the timeout-knob enumeration the brief asked for

The worker's PR report and its own session summary disagree ("`setup_timeout_s` and
`judge.timeout_s` were included" vs "A2 timeout holes flagged for next round"). **The report is
right and the session summary is stale.** Every timeout read in `run_eval.py`, `guidance.py`
and `run_canary.py`, enumerated:

| Read | Fixture-settable? | In `TIMEOUT_KNOBS`? |
|---|---|---|
| `run_eval.py:435 fixture.get("setup_timeout_s", 60)` | yes | **yes** |
| `run_eval.py:796 / :1129 fixture.get("timeout_s", 600)` → `:514 arm.get("timeout", 600)` | yes | **yes** |
| `run_eval.py:871 / :1174 judge_cfg.get("timeout_s", 120)` | yes | **yes** |
| `run_eval.py:1113 (fixture.get("guard") or {}).get("timeout_s", 300)` | yes | **yes** |
| `guidance.py:456 deliver(..., timeout=120)` | **no** — never passed a fixture value | n/a |
| `run_canary.py:48 timeout=30`, `run_eval.py:612 timeout=10` | no — literals | n/a |
| `--timeout` CLI flag | operator, `argparse type=int` | n/a |

**32 rows measured through `main()`** (4 knobs × {null, `"abc"`, `true`, `0`, `-1`, `.inf`,
`.nan`, `3`}): every hostile value → **rc 2** with `` `<knob>` must be a positive number of
seconds `` and no traceback; `3` → normal behaviour. No hole remains.

### A4 — what the two-sided guard proves, measured

Driven through `main()` with hostile probe CLIs (`$CLAUDE_BIN` = a fake that reads
`--setting-sources`, the config dir and cwd):

| Scenario | rc | CLI calls | Message |
|---|---|---|---|
| honest probe, honest hook | **0** | 4 | — |
| probe never echoes | **2** | 2 | both arms INCONCLUSIVE, `observed False` |
| control blind to its **decoy** (treatments fine) | **2** | 3 | control INCONCLUSIVE — *round 1 scored this clean* |
| control reports the **treatment token** (plural answer) | **2** | 3 | "reported the **TREATMENT** token in a control arm" |
| control reports the treatment token (**singular** answer) | **0** | 4 | **scores clean — see S-A** |
| sabotaged hook (`fleet-guidance: current`, writes nothing, exits 0) | **2** | **0** | `delivery_failed`, block **ABSENT** |
| hook writes the block but exits 1 | **2** | **0** | `delivery_failed`, hook exited 1 |

`new_decoy_token()` is a separate function from `new_token()` (both call `_random_token()`;
the docstring says why it is not an alias). `test/fake-claude` reports **every** magic word
(`MAGIC_RE.findall`), deliberately. The control arm's delivered memory is 179 bytes:

```
<!-- BEGIN FLEET GUIDANCE (managed by _agent-guidance) — DO NOT EDIT -->
<!-- fleet-guidance-version: 5b6bac40 -->

The magic word is HBPKGIMM-0830.
<!-- END FLEET GUIDANCE -->
```

### A6 — both `agent_env`s, measured under `env -i` with a poisoned environment

| variable | SKILL arm | GUIDANCE arm |
|---|---|---|
| `ACTIONS_ID_TOKEN_REQUEST_TOKEN` / `_URL` | **present** | absent |
| `ACTIONS_RUNTIME_TOKEN` | **present** | absent |
| `GITHUB_TOKEN`, `AWS_SECRET_ACCESS_KEY`, `SSH_AUTH_SOCK` | **present** | absent |
| `ANTHROPIC_AUTH_TOKEN` | present | present |

Guidance env is exactly `{ANTHROPIC_AUTH_TOKEN, CLAUDE_CONFIG_DIR, HOME, LANG, PATH, SHELL,
TMPDIR, USER, WORKSPACE}`. The header names all three GitHub runner variables **and** all six
`PASSTHROUGH` names. `run_eval.agent_env` is **byte-identical to main's** — correctly *not*
re-pointed (the owed follow-up).

---

## 3. Hollowness (head's new tests spliced onto a throwaway copy of `34ab8fc`)

34 new `TestIssue97` methods, run through `python3 -m unittest` on the ref tree with head's
`test/issues/test_issue_97.py` + `test/fake-claude` dropped in (the module has **no**
`if __name__ == "__main__"` block, so `python3 <file>` would be a hollow verifier — I used the
runner, not the file):

**Ran 34 tests → FAILED (failures=34, errors=26)** — 29 of 34 red, 5 green.

The **errors** (not failures) are the ones whose feature is simply absent on the ref, exactly
as the brief anticipated: 25 × `AttributeError … new_decoy_token`, 1 × `AttributeError …
ISOLATION_NAMES`, plus the A2 rows. The **failures** carry real diagnostics, e.g.
`1 != 0 : a committed fixture must still be accepted when the committed list is 118826 bytes;
the step failed CLOSED` (S5) and `True is not false : the header still claims the WIF token is
'the only credential in reach'` (A6).

The 5 green ones are **regression floors over already-correct code**, each of which is instead
pinned by a named mutation (all four verified red above):

| Green on ref | Why that is correct | Its mutation |
|---|---|---|
| `test_refuse_real_config_dir_rejects_both_of_its_arguments` | the pure function pre-existed | B0 → red |
| `test_passthrough_is_exactly_the_committed_six` | S4 is a pin, not a behaviour change | S4 → red |
| `test_an_absent_arms_key_still_takes_the_default_pair` | absent already defaulted; the red-first half is the *empty* case | A5 → red |
| `test_a_lone_cr_file_never_reaches_the_line_arithmetic` | pins the measured fact that `read_text` normalises first | N-a → red |
| `test_every_guidance_fixture_fits_inside_the_workflow_job_timeout` | the ref carries no 5-arm defaults fixture | N-c → red; and red on head with one planted |

I re-measured the lone-CR claim myself: `b"# T\r\r## Security\r\rbody\r"` reads back as
`"# T\n\n## Security\n\nbody\n"` and `h2_extents` returns one correct extent — the comment is
accurate and the arithmetic is untouched, as `check-guidance-coverage.js:95` requires.

**`TestTheRunnerItself`** (6 new tests, which live *in* `test/run_tests.py`, so a plain splice
would carry the fix with them): I spliced the class alone onto the **ref's** runner →
**1 FAIL + 5 ERROR** (`NameError: parse_argv is not defined`; the surviving one fails with
`'test_issue_97' not found in '… Ran 0 tests … OK'`).

---

## 4. Rule 19 / identity per check

Every committed fixture, `--arm objective-only`, head vs `$SP/mainx4` (`d5e06ee`), stdout
diffed after normalising `/tmp/...` paths:

| Fixture | head | main | stdout |
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
| `evals/guidance/_delivery` (head only) | **2** | — | N-f message, not `{"checks": []}` |

**With and without `--guidance $SP/_agent-guidance`**, all ten fixtures: same exit code,
**identical** stdout. Seeds untouched since `34ab8fc` (`git diff --stat 34ab8fc..c5ea933 --
'evals/*/seed' 'evals/**/seed'` empty); the only `evals/` change vs main is the new canary
fixture; the canary's prompt is byte-identical to `34ab8fc`'s.

---

## 5. B0/S1 — the suite-wide sweep

I instrumented `deliver`, `agent_env` and `_refuse_real_config_dir` in a scratch copy to log
every path argument, and ran the whole 685-test suite:

- **92 instrumented calls**: 34 `_refuse_real_config_dir`, 29 `deliver`, 29 `agent_env`.
  (`_refuse` > `deliver` because five calls are the *pure-function* assertions the brief asked
  for — the "assert on `_refuse_real_config_dir` directly" half landed too.)
- **256 distinct `(fn, arg, path)` tuples. Every single one rooted at `/tmp`.**
  Zero under the real HOME (`/root`), zero even under my throwaway home.
- Targeted proof: with `_refuse_real_config_dir(dest_dir, home)` deleted,
  `test_delivery_refuses_the_real_config_dir` fails on `assertFalse((scratch/"CLAUDE.md").exists())`
  and **both** `/root/.claude/CLAUDE.md` and the stand-in are byte-unchanged. The test now
  resolves against its own `_stand_in_home()` temp dir through a patched
  `guidance.os.path.expanduser`, so the round-1 incident **cannot recur through this mutation**.

---

## 6. The two merges of main

AST comparison of top-level classes / functions / module constants, `branch(34ab8fc)` ∪
`main(d5e06ee)` vs `head`:

| File | missing from head | new in head |
|---|---|---|
| `harness/run_eval.py` | **none** | `validate_timeouts`, `TIMEOUT_KNOBS`, `DECOY_PLACEHOLDER` |
| `harness/scorers/objective.py` | **none** | **none** — file is byte-identical to main |
| `test/run_tests.py` | **none** | `TestTheRunnerItself`, `flatten_suite`, `parse_argv`, `select_tests`, `user_memory_path`, `user_memory_fingerprint`, `USER_MEMORY_ENV` |

`objective.py` `CHECKS`: 24 on main, **the same 24** on head, PR #135's six git-state types
included. `run_setup` (PR #135) is **byte-identical** to main's; so is `agent_env`. `main()`
differs, as expected. README/DESIGN: **0** lines present on main and missing from head in
DESIGN.md; **1** in README.md, and that line was *extended* (a `;` plus a continuation
documenting `test/issues/`), not dropped. Lines present on the branch and not on head are all
prose the fix round deliberately rewrote (the A4 decoy paragraphs). Both merges are the exact
union.

Authors, `34ab8fc..c5ea933`: 50 commits authored **and** committed as
`4205216+Adam-S-Daniel@users.noreply.github.com`; 2 with GitHub's own merge committer; 1
(`aa03ac0`, `noreply@anthropic.com`) which `git merge-base --is-ancestor aa03ac0 d5e06ee`
confirms is an **ancestor of `origin/main`** — it arrived with the PR #132 merge and is not
this PR's commit (nit N6).

---

## 7. The one-way-door read

`git diff --name-only d5e06ee..c5ea933 -- .github/` → **`eval.yml` and `ci.yml` only**
(+164 / +16).

Parsed every workflow with `yaml.safe_load` and re-scanned the raw text:

| Rule | Result |
|---|---|
| Every `uses:` a bare 40-hex SHA | **25 `uses:`; 24 pass.** The one exception is `scheduled-run-health.yml:41` → `Adam-S-Daniel/cms-platform/.github/workflows/scheduled-run-health.yml@v0.1.87` — the documented `cms-platform` release-tag carve-out, **pre-existing and outside this PR's diff** |
| No trailing version comment on any `uses:` | **PASS** — zero |
| Zero `${{ }}` inside any `run:` block | **PASS** — 26 `run:` blocks, zero |
| `eval.yml` triggers | **PASS** — exactly `schedule` (`0 7 * * 1`) + `workflow_dispatch`; no `pull_request` |
| `permissions` unchanged from main | **PASS** — `{contents: write, id-token: write}` on both; no job-level `permissions` |
| `concurrency` unchanged | **PASS** — `{group: real-eval, cancel-in-progress: false}` on both; **no `concurrency` on any job publishing a required context** (`ci.yml`, the `pull_request` one, has none at all) |
| All checkouts `persist-credentials: false` | **PASS** — 5 in `eval.yml`, 3 in `ci.yml`, all on the same pin `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| New `_agent-guidance` checkout pinned + no credentials | **PASS** — same pin, `persist-credentials: false`, `path: _agent-guidance` |
| Push auth step-local | **PASS** — `GITHUB_TOKEN` appears in exactly one step's `env:` (step 13, the badge commit) and in that step's own `run:` |
| Validation **before** the token exchange | **PASS, by parsed step index** — step **9** "Select and validate the fixture to run"; step **10** "Mint OIDC token and exchange"; step **11** "WIF auth preflight" |
| Nothing between validation and the eval step writes `$RUNNER_TEMP/eval-fixture` | **PASS** — written only in step 9; read in steps 12 and 13 |
| `case` guard textually before any `grep` | **PASS** — verified in the `run:` block extracted from the parsed YAML |

### The executed gate — `run:` block of step 9, under bash, 43 inputs

Synthetic tree: three committed fixtures, one existing dir **without** a `fixture.yaml`, one
untracked dir **with** one, and one dir whose `fixture.yaml` is a **symlink**.

| Input | rc | `eval-fixture` | `eval-key` | rejected by |
|---|---|---|---|---|
| `evals/workflow-path-audit` | 0 | the value | `workflow-path-audit` | — accepted |
| `evals/guidance/_delivery` | 0 | the value | `guidance/_delivery` | — accepted |
| `""` (empty) / no `inputs` key / JSON `null` / `"\n"` | 0 | default | `workflow-path-audit` | — falls to the schedule default |
| `..`, `/etc/passwd`, `../../etc/passwd`, `./evals/…`, `evals//…`, `evals/../evals/…`, `evals`, `evals/workflow-path-audit/`, `evals/workflow-path-audit/fixture.yaml` | **1** | **not written** | **not written** | no committed fixture |
| `"a\nevals/…"`, `"evals/…\n$(id)"`, `"/etc/passwd\nevals/…"`, `"evals/…\nevals/guidance/_delivery"` | **1** | **not written** | **not written** | **charset (`case`) guard** |
| space (leading/inner/trailing), tab, CR, `*`, `[`, `;`, `$(id)`, backticks, `${HOME}`, `\|`, Cyrillic-а homoglyph ×2, JSON array, JSON object | **1** | **not written** | **not written** | charset guard |
| 100 KB of `e` | **1** | **not written** | **not written** | no committed fixture (see nit N4) |
| JSON `7`, JSON `true` | **1** | **not written** | **not written** | no committed fixture |
| `"evals/workflow-path-audit\0x"` (embedded NUL) | **1** | **not written** | **not written** | NUL stripped by bash → `…auditx`, no such fixture |
| `"\0evals/workflow-path-audit"` (leading NUL) | **0** | `evals/workflow-path-audit` | `workflow-path-audit` | NUL stripped by bash — see nit **N3** |
| `evals/uncommitted-dir` (exists, no `fixture.yaml`) | **1** | **not written** | **not written** | no committed fixture |
| `evals/untracked-fixture` (on disk, not in git) | **0** | the value | `untracked-fixture` | **accepted — documented N-i behaviour** |
| `evals/symlinked` (`fixture.yaml` is a symlink) | **0** | the value | `symlinked` | **accepted — documented N-i behaviour** |

**Nothing was minted or exported before any rejection: on all 33 rejecting rows both output
files were absent.** Mutation (delete the `case` block) → the four multi-line rows go **rc 0**
and the *whole two-line string* is written to `eval-fixture` **and** `eval-key`.

**S5, 20 trials per size**, matching on the first line of the list:

| committed list | `printf … \| grep -Fxq` | `grep -Fxq -- "$f" <<<"$committed"` |
|---|---|---|
| 2,225 B (100 entries) | 20/20 | 20/20 |
| 66,025 B (3,000) | 20/20 | 20/20 |
| **110,025 B (5,000)** | **0/20 — always rejects** | **20/20** |
| **440,025 B (20,000)** | **0/20** | **20/20** |

No live shell line in the tree pipes into an early-exit reader; the only two `| grep`
occurrences in `eval.yml` are inside comment prose (one of them the comment explaining this
very fix). The `| grep -q` strings in `test/run_tests.py` are fixture *data* for the
`review-bash-ci-reliability` eval, which exists to detect that shape.

---

## 8. Findings

### Blockers
**None.**

### Should-fix

**S-A — the control guard's *contamination* side is proven only against a probe that answers
plurally, and production's prompt asks for a singular answer. For that case head is strictly
weaker than `34ab8fc`.**
`harness/guidance.py:111` (`GUARD_PROMPT`), `:570` (`run_guard`), `test/fake-claude`.

`GUARD_PROMPT` is *"If your context contains a magic word, reply with that magic **word** and
nothing else."* — singular. Since A4, a control arm carries **two** magic words when it is
contaminated: its own decoy and the leaked treatment token. `run_guard` sets
`contaminated = forbidden_token in reply`, so a probe that answers with one word can satisfy
`observed=True, contaminated=False` and the arm scores clean.

Measured, same fixture and same leaking probe, only the answer arity differs:

| probe answers | head `c5ea933` | ref `34ab8fc` |
|---|---|---|
| **every** magic word | rc 2 — `reported the TREATMENT token in a control arm` | n/a (no decoy) |
| **one** magic word (what the prompt asks for) | **rc 0 — contaminated control SCORES CLEAN** | **rc 2 — `expected False, observed True`** |

Round 1's one-sided guard caught it precisely *because* the control carried no decoy: there
was only one word to report. `test/fake-claude` was changed in this round to report every
magic word (its comment says why), so the hermetic suite exercises a probe behaviour the
production prompt does not request.

Impact is bounded: what actually prevents contamination is the per-arm `HOME` /
`CLAUDE_CONFIG_DIR` isolation, which is solid (my sweep: 256/256 paths under `/tmp`). This is
defence-in-depth, not a live hole — hence should-fix, not blocker.

*Honesty check, as the brief asked.* The residual **is** disclosed, in three places
(`guidance.py:47-52`, `README.md:191-193`, `DESIGN.md:467-471`), and the disclosure is
accurate: *"a probe asked for 'the magic word' when its context carries two may report either;
only a real dispatch settles it."* What it does **not** say is that this ambiguity is created
**by the decoy** and costs a detection round 1 had. A reader finishes those paragraphs
believing the guard is strictly stronger. That is what the worker's own summary meant by
"weakened guard", and the docs stop one sentence short of saying it.

*Fix:* one word — `"reply with **every** magic word"` — which `test/fake-claude` already
models. `test/issues/test_issue_97.py:556` pins `GUARD_PROMPT` equal to
`evals/guidance-bridge-canary/fixture.yaml`'s prompt, so both must move together (and the
canary fixture's own prompt too). Plus one clause in the residual paragraph naming what the
decoy costs.

**REPEAT?** No. This is not a round-1 item recurring — it **returns through the brief's own
prescribed remedy** (the DESIGN DECISION the brief told the worker to implement). The worker
implemented it exactly as specified and disclosed the residual.

---

**S-B — `TestTheRunnerItself.test_dash_k_on_the_command_line_still_reaches_the_discovered_subtree`
fork-bombs the machine when the defect it guards is reverted.**
`test/run_tests.py:9938-9963`.

The test spawns `python3 test/run_tests.py -v -k <target>` with `SKILLS_EVALS_SUITE_CHILD=1`.
Its own comment says *"test/issues/test_issue_97.py reads this and skips the two pins that
shell out to the whole suite, so a child can never fork"* — true of the **four** forking tests
in `test_issue_97.py`, all of which call `_skip_in_child()`. **This test does not.** Nothing
bounds its child except `-k` narrowing actually working — which is the very contract it is
there to test.

Measured. With `main()`'s argv routing reverted (the exact S3 defect), `-k` is ignored, the
child runs `run_tests.py`'s own classes, reaches this test, and forks again:

```
t=  30s   3 concurrent run_tests.py processes
t=  70s   5
t= 110s   7
t= 150s   8      (still growing; each level holds a 900 s timeout, so nothing terminates)
```

I hit this during the ordinary mutation battery, saw an 8-deep chain of identical
`run_tests.py -v -k …` processes on a 4-core box, and had to kill the tree by hand — which
also cost two other mutation slots their timing.

This is the round-1 incident's *class* at a new target: the standard revert-the-fix mutation
damages the reviewer's environment. Round-1 S1's own remedy landed and is proven safe (§5);
this is a **new** instance introduced by S3's new pin.

*Fix:* the same `_skip_in_child()` guard `test_issue_97.py` already uses — a
`SKILLS_EVALS_SUITE_CHILD` check at the top of the test, so the recursion is bounded by an
environment variable rather than by the behaviour under test. Two lines.

**REPEAT?** No. **Returns through the brief's own prescribed remedy** (S3(a)/(b), which asked
for a pin driven "end to end through the real entry point").

### Nits

**N1** — `_run_main` (`test/issues/test_issue_97.py:778`) calls `run_eval.main()`
**in-process**, so the A2 pin has no outer bound: with `validate_timeouts` removed, the suite
hangs forever (measured: a `fake-claude` guard probe alive **498 s** under
`subprocess.run(timeout=None)`, which *is* the defect, but a reviewer's mutation then never
returns). Same family as S-B, milder. Route the null-timeout rows through a subprocess with an
outer timeout.

**N2** — N-e's `evals/**/fixture.yaml` is correct but **unfalsifiable on the committed tree**:
the only path `**` finds that `*` does not is `evals/guidance/_delivery/fixture.yaml`, which
has no `skill:` key and is filtered out by the test itself, so the single-level mutation is
**0 red**. I proved it falsifiable *in principle* — with a nested skill fixture planted, head
**FAILS** and the `*` spelling reports **OK**. Worth a comment saying so, or a synthetic
nested fixture inside the test's own tmpdir.

**N3** — a **leading NUL** in the dispatch value is silently dropped by bash's command
substitution (`warning: command substitution: ignored null byte in input`), so
`"\0evals/workflow-path-audit"` is **accepted** as `evals/workflow-path-audit` (rc 0) and the
log prints a `fixture:` line that differs from what was dispatched. Fails safe — only a
committed fixture can result, and an *embedded* NUL is rejected — but the gate never sees the
byte it would have refused.

**N4** — a 100 KB all-alphanumeric value passes the charset guard and is then echoed
**verbatim** into the public Actions log by the "names no committed fixture" branch
(`eval.yml:294`). No injection is possible (the class excludes `:`, newline and control
characters, so no workflow command and no ANSI survive), and the charset guard's own message
correctly names the rule rather than the input — but the second message could truncate.

**N5** — reverting `status = 0 if result.wasSuccessful() else 1` leaves the process exiting
**0** while printing `FAILED`: nothing inside a runner can police the runner's own exit code.
In a non-child run two behavioural pins do go red on screen (they assert a *child's* rc); in
child mode the suite is fully green. Inherent limit — worth one line of comment beside the
assignment.

**N6** — `aa03ac0` in `34ab8fc..c5ea933` is authored `noreply@anthropic.com`. It is an
**ancestor of `origin/main`** (arrived with the PR #132 merge), not a commit of this branch —
recorded so the author scan is not read as a finding against #138. `noreply@anthropic.com` is
not a personal address, so there is no data-exposure question.

---

## 9. What I could not measure

- **No real dispatch.** Everything about the OIDC exchange, the WIF preflight and the real
  `claude` CLI is inference from the parsed workflow and the step's `run:` block executed
  locally. The gate's ordering guarantee is proven by step index and by execution; that the
  *exchange step* behaves as documented is not.
- **Real-model probe behaviour.** S-A's severity depends on how often a real model answers with
  one word when two are in context. I measured the harness's response to both arities; I could
  not measure the model.
- **`markdown-it-py`'s publish date** and the cross-parser agreement with `_agent-guidance`'s
  own JS pin (no network). The 28-row bytes test remains the de-facto cross-check; round 1
  measured 28/28 and nothing in this round's diff touches `h2_extents`' arithmetic.
- **N-b** has no separate mutation — it is a docstring-string assertion, so its only teeth are
  the ref FAIL, which I did measure.
- The **`_agent-guidance` sibling is pinned at `3d972b4`** in this container; a manifest change
  upstream would move the 28-row identity, and I could not test against any other revision.
