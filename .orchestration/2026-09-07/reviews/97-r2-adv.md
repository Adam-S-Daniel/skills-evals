FOUND — 0 blocker, 1 should-fix, 6 nit

# Round-2 adversarial review — `claude/skills-evals-97` @ `c5ea933`

Scope: attack, not confirm. Every row below is a command I ran and its output.
All work under `HOME=$SP/r2adv97-home` with
`SKILLS_EVALS_USER_MEMORY=$SP/r2adv97-home/usermem.md`; the four named files in
`$SP/rev97b-adv` matched their stated md5s before I started, and the tree is
proved byte-identical to a fresh `git archive c5ea933` at the end.

**Headline: the round-1 blocker and all eleven should-fix items are genuinely
closed, and I could not break any of them.** The dispatch gate now rejects
shape before matching and nothing is minted or written on any rejection; the
control arm's guard is two-sided and a contaminated control goes INCONCLUSIVE;
a provably-failed delivery costs zero CLI calls; the env allowlist survived a
95-name hostile parent with zero leaks; and the revert-the-guard mutation that
destroyed a real `~/.claude/CLAUDE.md` in round 1 is now red with the sentinel
byte-unchanged. The one should-fix is a **narrowed return of round-1 A2**
through that item's own prescribed remedy: `validate_timeouts` bounds the
value below but not above, so a large finite number escapes the `GuidanceError`
contract as a bare `OverflowError` traceback (rc 1).

---

## FINDINGS

### S1 (should-fix) — `validate_timeouts` has no upper bound, so a large finite timeout escapes the rc-2 contract as a bare traceback
`harness/run_eval.py:67-95` (`validate_timeouts`), reaching
`subprocess.run(timeout=…)` at `:438`, `:517`, `:871/1174`, `:1113`.

REPEAT: **yes, a partial repeat of round-1 A2/S2, and it returns through that
item's own prescribed remedy.** The brief said "coerce and validate once … a
positive number, else `GuidanceError`". That is exactly what was implemented,
and "positive number" is the half that leaves this open.

Reproducing input — a guidance fixture carrying `timeout_s: 2200000` (and the
same for `guard.timeout_s`), through the real CLI entry point:

```
$ python3 harness/run_eval.py <fx> --arm with_guidance_section --guidance ../_agent-guidance --no-judge
rc=1
stdout: (empty)
stderr:     fd_event_list = self._selector.poll(timeout)
            OverflowError: timeout is too large
```

Measured boundary and the two sub-cases:

| `timeout_s` | `validate_timeouts` | what happens |
|---|---|---|
| `null`, `""`, `"600"`, `true`, `false`, `-1`, `0`, `inf`, `nan`, `[3]`, `{a:1}` | REJECTED, rc 2, named, **0 CLI calls**, 0.0 s | correct — the A2 fix |
| `3`, `600` (absent too) | accepted | correct |
| `2700 < t ≤ 2.147e6` (2^31 ms ≈ 24.9 days) | **accepted** | the harness timeout can no longer fire inside eval.yml's 2700 s job budget — the job is killed with no summary and no artifact, the exact failure the validator's own message describes for `null` |
| `t > 2.147e6` (incl. `1e9`, `1e308`) | **accepted** | uncaught `OverflowError`, **rc 1, bare traceback**, no summary — outside the `GuidanceError` contract, the same defect shape A2 closed for `"abc"` |

All four knobs behave identically (`timeout_s`, `setup_timeout_s`,
`guard.timeout_s`, `judge.timeout_s`) — I ran the 13-value battery against each:
36 rejections, all rc 2, all named, all at 0.0 s with an empty
`$FAKE_CLAUDE_ARGV_LOG`.

Severity — why should-fix and not blocker: it needs a deliberately absurd
fixture value, fixtures are maintainer-only trusted content, and
`test_every_guidance_fixture_fits_inside_the_workflow_job_timeout` already
bounds every **committed** guidance fixture at `worst_case < 2025 s`. So the
committed surface is safe; an uncommitted or experimental fixture is not. It
mints nothing, lets no contaminated arm score, and reaches no operator file.

What makes it worth fixing rather than recording: the rejection message
actively steers an operator toward the accepted-but-hostile value —

> "An explicit YAML null here means \"no timeout\" — a run that hangs until the
> job is killed, with no summary and no artifact. Omit the key to take the
> default instead."

— and the obvious next move after reading that is a very large number.

**Fix I would make:** add an upper bound in the same predicate, keyed to the
job budget rather than to a magic constant:

```python
ok = (not isinstance(value, bool) and isinstance(value, (int, float))
      and value == value and value not in (float("inf"), float("-inf"))
      and 0 < value <= MAX_TIMEOUT_S)   # MAX_TIMEOUT_S = 2700, eval.yml's timeout-minutes * 60
```

and extend the message to name the ceiling. Test: `timeout_s: 2200000` → rc 2
named (red today, where it is rc 1 + traceback); `timeout_s: 600` unchanged.
Mutation: drop the upper bound → the row goes back to a traceback.

---

### N1 (nit) — the validation step's comment says the rejected value is not echoed; the second branch echoes it
`.github/workflows/eval.yml` — the comment block above the `case` guard ends:

> "The rejected value is NOT echoed back: this log is public, so the message
> names the rule, not the input."

Fifteen lines later, in the same step:

```
$ # charset-clean value that names no fixture
eval.yml: dispatch input 'fixture' names no committed fixture: evals/SECRETish-value-not-a-fixture
```

No exposure: anything reaching that branch has already passed
`[A-Za-z0-9/_.-]`, so there is no newline, no control character and no ANSI
escape — log injection is impossible, and dispatch requires repo write access.
It is a comment/code contradiction inside the step whose header is the artifact
reviewers trust. REPEAT: no. **Fix:** either scope the sentence to the `case`
branch, or drop `: $fixture` from the second message too.

### N2 (nit) — the A6 header enumerates the guidance allowlist but omits `WORKSPACE` (and the fixture `env:` overlay)
`.github/workflows/eval.yml` — the header says a guidance arm gets "PATH, LANG,
LC_ALL, SHELL, USER, NODE_PATH, plus the HOME, TMPDIR and CLAUDE_CONFIG_DIR the
harness sets and every ANTHROPIC_* variable."

Measured through `guidance.agent_env` against a 95-name hostile parent — **15
names**, and the fifteenth is `WORKSPACE=/ws`, which the header does not name.
The A6 pin (`test_the_header_names_what_is_in_reach_for_each_subject`) requires
every `PASSTHROUGH` name and the three runner tokens, but not `WORKSPACE`.

`WORKSPACE` is a harness-set scratch path, not a credential, so the sentence's
security claim is not wrong — but A6 exists to make this enumeration honest and
it is one short. REPEAT: no (new, created by the A6 fix). **Fix:** add
`WORKSPACE` (and a clause for the fixture's own `env:` block) to the sentence,
and add `WORKSPACE` to the pin's required names.

### N3 (nit) — the docstring's stated REASON for the residual does not cover the residual I measured
`harness/guidance.py:47-53`:

> "…is prevented by the per-arm HOME and CLAUDE_CONFIG_DIR isolation rather
> than by the guard, because a probe asked for 'the magic word' when its
> context carries two may report either"

Measured, through `main()`:

| control-arm contamination | rc | guard | outcome |
|---|---|---|---|
| ambient file carrying the **treatment** token | **2** | `guard_contaminated` | no score — A4 works |
| ambient file carrying a **stale** token | 0 | ok | **scored clean** |
| ambient file = the **real `base.md`** (no token at all) | 0 | ok | **scored clean** |

Rows 2 and 3 are the documented, brief-prescribed residual and I am not
reporting them as defects — A4 explicitly said to state the residual rather
than close it, and the docstring does. The nit is that the stated reason ("may
report either") describes only the two-token case; row 3 fails for a simpler
reason the sentence does not give — a contaminating source that carries **no**
token is structurally invisible to a token-based guard, however the probe
behaves. REPEAT: this is round-1 S4's residual half, accepted by design.
**Fix:** one clause — "…and a contaminating source that carries no token of its
own is invisible to a token guard at all."

### N4 (nit) — the two-sided guard is one-sided in the other direction
`harness/run_eval.py:1111` passes `forbidden_token` only when `decoy is not
None`, i.e. only for a `mode: none` arm. Measured: a treatment arm whose probe
reports **both** the treatment token and the control's decoy scores clean
(rc 0), and so does one contaminated by an ambient file carrying the decoy.

Low impact — a control→treatment leak is the harmless direction, and the
reverse (which matters) *is* caught by the control's own forbidden token, so
any real cross-arm leak still fails the run through the control. REPEAT: no.
**Fix (optional):** give a treatment arm the run's decoys as forbidden tokens
too, or say in the docstring that the check is deliberately asymmetric.

### N5 (nit) — `-k` matching nothing exits 0 over zero tests
```
$ python3 test/run_tests.py -k NoSuchThingAtAll
NARROWED RUN: -k selected 0 of 685 tests — an OK from this run is not a full-suite pass.
Ran 0 tests in 0.000s
OK          rc=0
```
This is the shape N-f was fixed for ("a gate that finds nothing reads the same
as a gate that found nothing wrong"), and the repo cites
`check-guidance-coverage.js`'s exit-2-on-zero convention for it. It is much
milder here: the operator asked for the narrowing and the NARROWED RUN line
says so in the same breath. REPEAT: no. **Fix:** exit 2 when `-k` selects zero,
or leave it and note the deliberate difference.

### N6 (nit) — an issue module that matches the glob but defines no tests fails the whole suite
Planted `test/issues/test_issue_zz_r2adv_empty.py` containing only `VALUE = 1`:

```
Ran 685 tests ... FAILED (failures=4, skipped=2)      rc=1
FAIL: TestTheRunnerItself.test_build_suite_covers_every_discoverable_issue_module
```

`build_suite()` must carry ≥1 test from *every* globbed module, so a placeholder
or helper file named `test_issue_*.py` is a hard failure with a message about
discovery rather than about the empty file. Defensible as written (an issue
module with no tests is usually a mistake), but the failure reads as a
discovery break. REPEAT: no. **Fix (optional):** name the offending module in
the message, or exempt a module that defines no `TestCase` at all.

### Record-only (measured, no change requested)
* **The manifest's `file:` is not constrained to the checkout.** A
  `_agent-guidance` manifest row with `file: ../outside_target.md` was read and
  its content reached the run artifacts under `results/`, which are pushed to
  the public `eval-results` branch. Not an escalation — eval.yml's header
  states that write access to `_agent-guidance` is equivalent to key access —
  but it is a file-read/exfiltration path from inside that boundary.
* **`deliver()`'s timeout leaves a grandchild.** A hook that spawns
  `sleep 900` and is killed by `subprocess.run(timeout=…)` leaves the `sleep`
  orphaned (the direct `bash` child is killed, its descendants are not). I
  observed one and killed it. The real `fleet-memory.sh` spawns nothing
  long-lived.
* **The targeted-run branch takes no user-memory snapshot.** `main()` returns
  from the `opts.targets` branch (`:10013`) before `memory =
  user_memory_path()` (`:10024`), so `run_tests.py TestFoo.test_bar` runs with
  the S2 guard off. It addresses only `run_tests.py`'s own classes and prints
  a NARROWED RUN line.
* **The control arm is no longer a no-user-memory arm.** Its
  `$CLAUDE_CONFIG_DIR/CLAUDE.md` is now, verbatim, 34 payload bytes wrapped by
  the real hook:
  ```
  <!-- BEGIN FLEET GUIDANCE (managed by _agent-guidance) — DO NOT EDIT -->
  <!-- fleet-guidance-version: be5b662a -->

  The magic word is DECOYAAA-9999.
  <!-- END FLEET GUIDANCE -->
  ```
  This is the A4 trade-off and it is documented in the docstring, README (2
  places) and DESIGN (3 places). For an ablation it is arguably an improvement
  (the wrapper is now constant across arms instead of a second difference);
  for a behavioural A/B it is a small new perturbation of the control.
* **`NODE_PATH` is the one loader-influencing name in `PASSTHROUGH`** — an
  ambient `NODE_PATH` reaches the guidance agent (Claude Code is a Node
  program). Pre-existing and deliberate; S4's exact-tuple pin is what stops the
  set growing silently.
* **`dependabot-auto-merge.yml`'s two checkouts have no
  `persist-credentials: false`.** Pre-existing, untouched by this PR
  (`.github/` diff vs main is ci.yml + eval.yml only).
* **The new `_agent-guidance` checkout has no `ref:` pin** in either workflow,
  so it tracks that repo's moving default branch — the same convention as the
  three registry checkouts already there, and ci.yml is a required check.
* **`run_eval` still accepts a unicode section id that `make_badge` rejects.**
  Confirmed still unreachable: `make_badge._validate_name('guidance/sécurité')`
  raises `ValueError`, and `section: sécurité` dies at "unknown section id"
  because all 28 manifest ids are ASCII.
* **A duplicate `arms:` key is resolved last-wins by YAML**, silently. Standard
  behaviour, same everywhere in the repo.

---

## HELD UP UNDER ATTACK

### B1 + S5 — the dispatch gate (surface 1)
The step's own `run:` block, extracted with `yaml.safe_load` and executed under
`bash` with a synthetic `$GITHUB_EVENT_PATH`/`$RUNNER_TEMP` against a synthetic
`evals/` tree. **42 rows.** Nothing was written to `eval-fixture`/`eval-key` on
any rejection, and no `/tmp/R2ADV_PWNED*` sentinel was ever created.

| input | rc | eval-fixture |
|---|---|---|
| *(no inputs — the schedule)* | 0 | `evals/workflow-path-audit` |
| `evals/workflow-path-audit` / `evals/guidance/_delivery` / `evals/rename-pdfs` | 0 | the value |
| **`a\nevals/workflow-path-audit`** | **1** | — |
| **`evals/workflow-path-audit\n$(id)`** | **1** | — |
| **`evals/workflow-path-audit\nevals/guidance/_delivery`** | **1** | — |
| **`/etc/passwd\nevals/workflow-path-audit`** | **1** | — |
| CRLF `valid\r\nvalid`, bare `\r`, tab | 1 | — |
| `..`, `../evals/…`, `/etc/passwd`, `/evals/…` | 1 | — |
| `*`, `evals/*`, `evals/[`, `evals/…audi?` | 1 | — |
| space inside, trailing space, trailing slash, `./`, `//`, `..` inside | 1 | — |
| `evals/workflow-path-audit/fixture.yaml`, bare `evals` | 1 | — |
| `$( )`, backticks, `;`, `\|`, `&&`, `>` | 1 | — |
| NUL byte, 100 KB value, 1 MB value, valid + 100 KB second line | 1 | — |
| unicode homoglyph (Cyrillic а), combining mark | 1 | — |
| whitespace-only, tab-only | 1 | — |
| empty string / trailing `\n` on a valid value | 0 | default / the value (documented; `$( )` strips the trailing newline) |

* **Step order proved from the parsed YAML, not from comments:** step 9
  "Select and validate the fixture to run" precedes step 10 "Mint OIDC token
  and exchange for Anthropic access token" and step 11 "WIF auth preflight".
  The validation step contains no token, no export and no `::add-mask::`; it
  runs one `find` and writes only on success. So the header's twice-stated
  ordering guarantee is now true for every input above.
* **The `case` character class** is `*[!A-Za-z0-9/_.-]*` under an explicit
  `export LC_ALL=C`, and it precedes the `find`/`grep`.
* **The here-string, 20 trials per spelling** against a real 3,601-row /
  133,226-byte committed list built from a synthetic `evals/` tree, targeting
  the FIRST row (worst case for SIGPIPE):

  | spelling | accepted |
  |---|---|
  | `grep -Fxq -- "$fixture" <<<"$committed"` (head) | **20/20** |
  | `printf '%s\n' "$committed" \| grep -Fxq` (round-1) | **0/20** — fails closed |

  Targeting a row that sorts last, both are 20/20, which is exactly the
  size-and-position-dependent race S5 named.
* `$RUNNER_TEMP/eval-fixture` is written at one line only and read at one line
  only (grep of every `RUNNER_TEMP` reference in the file); no step between
  writes it.
* "Committed" = present on disk: an untracked `evals/untracked-fixture` and a
  symlinked `fixture.yaml` are both accepted (N-i, documented as such); a
  symlinked *directory* is refused, `find -P` not descending it.

### Workflow hygiene (surface 2)
Parsed all six workflows with `yaml.safe_load` and walked every step:
**26 `run:` steps, 24 `uses:` steps**; **zero** `${{ }}` inside any `run:`
block; **every** `uses:` a bare 40-hex SHA with no trailing comment (the only
`#` near a `uses:` in the tree is a prose comment in propagation.yml);
`eval.yml` triggers exactly `schedule` + `workflow_dispatch`; `permissions`
`{contents: write, id-token: write}` and `concurrency` `{real-eval,
cancel-in-progress: false}` unchanged from main; `eval.yml` has no
`pull_request` trigger so it publishes no required status context, and `ci.yml`
(the required-check publisher) still has no `concurrency` at all;
`persist-credentials: false` on all five eval.yml checkouts and all three
ci.yml checkouts, the new `_agent-guidance` one included; `GITHUB_TOKEN`
appears only in the final commit step's `env:` and `run:`, never in the step
that runs the agent. `.github/` diff vs main `d5e06ee` = ci.yml (+16) and
eval.yml (+164), nothing else.

### A4 — the decoy and the guard (surface 3)
Driven through `run_eval.main()` with the real hook and both the repo's fake
CLI and a purpose-built forging CLI.

| probe / contamination | arm | rc | error | scored? |
|---|---|---|---|---|
| honest, all five arms | all | **0** | — | all five, 10 CLI calls |
| blind (never echoes) | `without_guidance` | **2** | `guard_miss` | **no** — round-1 S4 closed |
| blind | `with_guidance_section` | 2 | `guard_miss` | no |
| blind, all five | all | 2 | `guard_miss` ×5 | none |
| ambient file with the TREATMENT token | `without_guidance` | **2** | `guard_contaminated` | **no** |
| forged reply = exact decoy | `without_guidance` | 0 | — | yes (correct) |
| forged = decoy lowercased | `without_guidance` | **2** | `guard_miss` | no |
| forged = decoy with a space inserted | `without_guidance` | **2** | `guard_miss` | no |
| forged = first 8 chars of the decoy | `without_guidance` | **2** | `guard_miss` | no |
| forged = BOTH tokens | `without_guidance` | **2** | `guard_contaminated` | no |
| forged = TREATMENT only | `without_guidance` | **2** | `guard_contaminated` | no |
| forged = neither / empty reply | `without_guidance` | **2** | `guard_miss` | no |
| forged = treatment token lowercased | `with_guidance_section` | **2** | `guard_miss` | no |
| forged = decoy only | `with_guidance_section` | **2** | `guard_miss` | no |
| **`new_token() == new_decoy_token()`** (p≈5e-16) | all five | **2** | control `guard_contaminated` | fails safe |

* **Token independence:** 2,000 draws of each — 2,000/2,000 distinct on both
  sides, zero overlap between the two sets, all matching `[A-Z]{8}-\d{4}`, and
  no member of one a substring of any member of the other. Keyspace
  26⁸·10⁴ = 2,088,270,645,760,000. Both call `_random_token()` but each is an
  independent `secrets` draw, so patching one test-side does not collapse the
  other.
* **The fake CLI reports EVERY magic word**, not the first
  (`MAGIC_RE.findall`) — proved by the BOTH-tokens row, which produces
  `guard_contaminated` rather than a `guard_miss`.
* Every failure lands as INCONCLUSIVE with rc 2, `objective_checks: null`, and
  no score — never a silent pass, never a PASS or FAIL.

### A3 — delivery (surface 4)
Sabotaged `.claude/hooks/fleet-memory.sh` in a scratch guidance checkout, CLI
invocations counted from `$FAKE_CLAUDE_ARGV_LOG`:

| hook | rc | error | `installed` | `hook_returncode` | CLI calls |
|---|---|---|---|---|---|
| exits 3, writes nothing | **2** | `delivery_failed` | False | 3 | **0** |
| exits 0, prints `fleet-guidance: current`, writes nothing | **2** | `delivery_failed` | False | 0 | **0** |
| exits 0, writes an UNMARKED file | **2** | `delivery_failed` | False | 0 | **0** |
| exits 0, marked block with the WRONG token | 2 | `guard_miss` | True | 0 | 1 |
| the REAL hook | **0** | — | True | 0 | 2 |

`installed` and `hook_returncode` are in the arm's `extra` on every path, and
the `delivery_failed` detail names the dest path and whether the block is
present. A hook that **hangs** is bounded by `deliver()`'s own hard-coded
120 s (not by `guard.timeout_s`): measured with `timeout=3`, it raised
`GuidanceError: could not run …` at 3.0 s → rc 2.

### S4 / A6 — the env allowlist (surface 5)
`guidance.agent_env` and `run_eval.agent_env` driven with a **95-name hostile
parent** (GitHub/Actions tokens, AWS/Azure/GCP, SSH/GPG/netrc, `LD_PRELOAD`,
`LD_AUDIT`, `NODE_OPTIONS`, `BASH_ENV`, `ENV`, `PYTHONSTARTUP`, proxies,
`VAULT_TOKEN`, `KUBECONFIG`, …):

* **GUIDANCE arm — 15 names**, and **zero** non-allowlisted hostile names:
  `PATH, LANG, LC_ALL, SHELL, USER, NODE_PATH` + `HOME, TMPDIR,
  CLAUDE_CONFIG_DIR` (all scratch) + `WORKSPACE` + the five `ANTHROPIC_*`.
* **SKILL arm — 96 names**, carrying every credential in the parent
  (`ACTIONS_ID_TOKEN_REQUEST_TOKEN`, `ACTIONS_RUNTIME_TOKEN`, `AWS_*`,
  `GITHUB_TOKEN`, `LD_PRELOAD`, `NODE_OPTIONS`, …) — which is exactly what the
  corrected header now says, per subject.
* `PASSTHROUGH` is pinned to the exact six-tuple and `EXTRA_PASSTHROUGH` to `()`.

**N-h**, fixture `env:` — `HOME`, `TMPDIR`, `CLAUDE_CONFIG_DIR` refused with a
named `GuidanceError` (rc 2). The rest pass through
(`XDG_CONFIG_HOME, TMP, TEMP, PYTHONPATH, PATH, LD_PRELOAD, NODE_OPTIONS,
PYTHONSTARTUP, BASH_ENV, ENV`) — but **none of them can re-point delivery**,
because `deliver()` builds the hook's environment from scratch (`PATH` only,
plus the four it sets) and never consults `fixture["env"]`. Measured:

| fixture `env:` | rc | `installed` |
|---|---|---|
| `FLEET_GUIDANCE_SKIP: "1"` | 0 | **True** — the hook still delivered |
| `FLEET_GUIDANCE_PAYLOAD: /dev/null` | 0 | **True** |
| `HOME: /root` / `CLAUDE_CONFIG_DIR: /root/.claude` | **2** | refused |
| `FOO: bar` | 0 | True |

The remaining names reach only the agent/probe child — a code-execution surface
for a *trusted* fixture that is identical on main's skill path.

### S3 / S2 — discovery, the runner and the memory guard (surface 6)
* **Flags no longer narrow the run.** Through the production
  `parse_argv`/`select_tests`: `[]`, `-v`, `-q`, `--failfast`, `-f`,
  `-v --failfast` all select **685 of 685**, ids identical to the no-argument
  suite. Round 1 was 379 with `grep -c TestIssue97` = 0; `-k TestIssue97` now
  selects 91.
* **Discovery-disabled mutation (m1):** `Ran 594 … FAILED (failures=2)`,
  **rc 1**, naming `missing: ['test_issue_97']`. The round-1 silent
  `379 … OK, exit 0` is gone.
* **A failing discovered test (m4):** `Ran 686 … FAILED`, **rc 1**, the planted
  failure reported by name — discovery failures reach the exit status.
* **The S2 guard fires (m2).** A planted test writing
  `$SKILLS_EVALS_USER_MEMORY` produced **rc 1** and:
  ```
  FAILED: this suite CHANGED …/mem/m2.md (f9d2b9b0… -> 816766d9…). No test may
  write the fleet's user memory: …
  ```
  plus an errored `tearDownModule (test_issue_97)` — three independent nets.
  The snapshot is taken before `build_suite()`, so import-time writes are
  covered.
* **The guard's coverage**, measured against `user_memory_fingerprint`:
  overwrite, delete, rename-away, replaced-by-a-symlink-to-different-content,
  and replaced-by-a-directory are all **caught**. The three it does not catch —
  symlink to byte-identical content, write-then-restore, chmod 000 as root —
  all leave the operator's bytes intact, which is the invariant.
* **Targeted runs** exit correctly: rc 0 on a pass, rc 1 on a failure, with the
  NARROWED RUN line.

### B0/S1 — the round-1 incident cannot recur
I applied the mutation that destroyed the real file in round 1: made
`_refuse_real_config_dir` a no-op and ran the whole suite, with a 467-byte
sentinel planted at `$HOME/.claude/CLAUDE.md` under the throwaway HOME.

```
Ran 685 tests ... FAILED (failures=10, skipped=2)     rc=1
FAIL: test_refuse_real_config_dir_rejects_both_of_its_arguments  (x8 subtests)
FAIL: test_delivery_refuses_the_real_config_dir                  (x3)
FAIL: test_an_ordinary_run_leaves_the_watched_file_alone
```
Every `dest=`/`home=` in those failures is under `/tmp/guidance-*`.

| file | before | after |
|---|---|---|
| sentinel `$HOME/.claude/CLAUDE.md` (throwaway HOME) | `e4860957a967abb32f7c9e020d0ebdd1`, 467 B | **`e4860957a967abb32f7c9e020d0ebdd1`, 467 B** |
| real `/root/.claude/CLAUDE.md` | `935c291f2efb1ff55a463bccfde55e6a` | **`935c291f2efb1ff55a463bccfde55e6a`** |

Sweep: no call to `deliver`/`assemble`/`agent_env` anywhere in `test/` takes a
real HOME path; the only three `expanduser("~")` uses are read-only
fingerprint helpers.

### A5 — `arms:` (surface 8)
17 shapes through `main()`; every hostile one rc 2 with a named message:
`{}`, `null`, `[]`, `"section"`, `["section"]`, `{"section": null}`,
unknown mode, missing `mode:`, `{"a": "section"}`, `with_*` carrying
`mode: none`, `without_*` carrying `mode: full`, and arm names `a/b`,
`../esc`, `a b`, `""`. Absent → the default `section`/`none` pair; two valid
arms run. A duplicate YAML key is last-wins (recorded above).

### The merges of main (surface 9)
AST union over `harness/run_eval.py`, `harness/scorers/objective.py` and
`test/run_tests.py` (top-level defs/classes/methods/constants), comparing main
`d5e06ee`, branch `34ab8fc` and head `c5ea933`:

| file | in main not head | in branch not head | duplicates in head |
|---|---|---|---|
| `run_eval.py` | **none** | **none** | none |
| `objective.py` | **none** | **none** | none |
| `run_tests.py` | **none** | **none** | none |

Everything present in head but in neither parent is a named item from this fix
round (`validate_timeouts`, `TIMEOUT_KNOBS`, `DECOY_PLACEHOLDER`,
`TestTheRunnerItself`, `parse_argv`, `select_tests`, `flatten_suite`,
`user_memory_path`, `user_memory_fingerprint`, `USER_MEMORY_ENV`).
`objective.py` is byte-identical to main's. `run_setup` is **AST-identical** to
main's. README/DESIGN are a pure union — the one removed README line is that
same row rewritten to add `issues/`. Commit authors/committers across
`34ab8fc..c5ea933` are all `…@users.noreply.github.com`, except GitHub's own
merge committer `noreply@github.com` and main's `noreply@anthropic.com`
(`aa03ac0`). Seeds unchanged since `34ab8fc`; the canary's fixture unchanged.

### N-a, N-b, N-f, N-g, N-c (surface 10)
* **markdown-it lazy import.** With `markdown_it` blocked by a raising
  sentinel module: `evals/workflow-path-audit --arm objective-only` → rc 1 with
  stdout **byte-identical** to the run with the parser available, and **zero**
  `ImportError`/`Traceback`. A guidance arm that needs the parser → rc 2 with
  the named message quoting `pip install markdown-it-py==4.2.0`.
* **N-f:** `evals/guidance/_delivery --arm objective-only` → **rc 2**, "declares
  no top-level `objective_checks:` … run it with `--arm both`".
* **The extent arithmetic claim.** All **28/28** manifest rows agree with their
  stored `bytes` exactly. The chars-vs-bytes distinction N-b documents is
  load-bearing: only **2 of 28** rows are pure ASCII, so for **26** rows the
  character count and the byte count genuinely differ.
* **N-c** is generalised over every committed guidance fixture with an
  anti-vacuity assertion, and pins the header's "guard probe" / "scored leg"
  wording.

### Hostile `_agent-guidance` (surface 11)
Every case rc 2, no traceback, no hang, nothing written outside the harness
scratch, `/etc/passwd` md5 unchanged: missing manifest; malformed manifest YAML
(the parser's message is wrapped in a named `guidance configuration error:`, not
raised); a section id containing `..`; a manifest `file:` pointing outside the
tree; `base.md` a symlink to `/etc/passwd`; and a **51 MB** `base.md` — bounded,
finished in 69 s, rc 2, no leftover arm scratch dirs. Fixture `section:` values
`../../etc/passwd`, `a/b`, `..`, `/etc/passwd`, `""` and `sécurité` are all rc 2
with a named message.

---

## VERIFIER TABLE

Run on `c5ea933` in a pristine export, `HOME=$SP/r2adv97-home`,
`SKILLS_EVALS_USER_MEMORY=$SP/r2adv97-home/usermem.md`,
`PYTHONPATH=/root/.local/lib/python3.11/site-packages`, siblings
`_agent-guidance` @ `3d972b4` and `agentskills` present.

| verifier | expected | measured | rc |
|---|---|---|---|
| `python3 test/run_tests.py` | 685, 2 skipped, exit 0 | **Ran 685 tests in 166.308s — OK (skipped=2)** | **0** |
| `python3 test/test_propagation.py` | 164, 1 skipped | **Ran 164 tests in 6.960s — OK (skipped=1)** | **0** |
| flags select the same suite | 685 each | `[]`/`-v`/`-q`/`--failfast`/`-f`/`-v --failfast` → **685/685**, ids identical | — |
| `-k TestIssue97` | narrowed, announced | **91 of 685**, NARROWED RUN printed | — |
| Rule 19: skill fixtures vs main `d5e06ee`, `--arm objective-only` | identical per check | **8/9 byte-identical stdout and rc**; `disarm-inherited-reach` differs **only** in the two `mkdtemp` paths and is identical after normalising them | matched per fixture |
| guidance canary objective-only | rc 2 (N-f) | rc 2, named | **2** |

Rule 19 detail — head rc / main rc / stdout:
`disarm-inherited-reach` 1/1 (tmp path only) · `github-actions-sha-pinning` 1/1
identical · `guidance-bridge-canary` 2/2 identical · `post-failure-comment` 1/1
identical · `propagation` 2/2 identical · `rename-pdfs` 1/1 identical ·
`review-bash-ci-reliability` 1/1 identical · `windows-elevation-from-wsl` 1/1
identical · `workflow-path-audit` 1/1 identical.

Mutation runs (each in its own checkout, serial per checkout):

| mutation | result | rc |
|---|---|---|
| m1 — `suite.addTests(loader.discover(...))` deleted | Ran **594**, FAILED (failures=2), names `missing: ['test_issue_97']` | **1** |
| m2 — a planted test writes `$SKILLS_EVALS_USER_MEMORY` | Ran 686, FAILED; run-wide guard prints `FAILED: this suite CHANGED …` | **1** |
| m3 — a planted `test_issue_*.py` with no tests | Ran 685, FAILED, discovery pin fires | **1** |
| m4 — a planted discovered test that fails | Ran 686, FAILED, the planted failure named | **1** |
| m5 — `_refuse_real_config_dir` made a no-op | Ran 685, FAILED (failures=10); sentinel **byte-unchanged** | **1** |

---

## TREE INTEGRITY AND SAFETY LEDGER

| item | start | end |
|---|---|---|
| `md5sum /root/.claude/CLAUDE.md` | **`935c291f2efb1ff55a463bccfde55e6a`** (56,099 B) | **`935c291f2efb1ff55a463bccfde55e6a`** (56,099 B) — **unchanged** |
| `$SP/rev97b-adv/harness/guidance.py` | `95c4bb22ee084a3dc974df968f920285` | matched at start |
| `$SP/rev97b-adv/harness/run_eval.py` | `9497375d0d37a57549ff072f31b0a865` | matched at start |
| `$SP/rev97b-adv/test/issues/test_issue_97.py` | `87b7e5bcb35e36b332537eab29600b22` | matched at start |
| `$SP/rev97b-adv/.github/workflows/eval.yml` | `95f4d9ea942cb10e6e74b8fe46d8441e` | matched at start |
| `$SP/rev97b-adv` vs a fresh `git archive c5ea933` | — | **`diff -rq` clean — byte-identical**, no `results/`, no `__pycache__`, no probe module (I never executed anything inside it; every run used a copy) |
| `/home/user/skills-evals` | clean | `git status --porcelain` = **0 files**, HEAD `527c729` — read-only git commands only |
| `$SP/rev97b-ref`, `$SP/mainx4`, `$SP/_agent-guidance`, `$SP/agentskills` | — | untouched |
| my scratch `$SP/r2adv97-*` | — | **all 13 directories deleted** |
| background processes I started | — | **none left** (`ps` clean); one orphaned `sleep 900` grandchild from a hanging-hook probe was found and killed |
| `/tmp` arm scratch dirs left by my killed runs | — | removed (`/tmp/skills-evals-*`); `/tmp/guidance-*` and `/tmp/memory-guard-*` belonging to other live sessions were left alone |
| network / GitHub writes / real `claude` / real `gh` | — | **none**; no sessions, routines or reminders created; nothing read under `~/.claude` beyond that one md5 |

---

## WHAT I COULD NOT MEASURE

* **Whether a real `claude` CLI honours `CLAUDE_CONFIG_DIR` for user memory** —
  the entire `--delivery user` premise, and the thing N3's residual turns on.
  Everything above was measured against `test/fake-claude` and a forging CLI I
  wrote. Only a real dispatch settles it. Unchanged from round 1.
* **The real dispatch**: the OIDC/WIF exchange, the `eval-results` push, and
  therefore whether a five-arm guidance dispatch really fits the 45-minute job
  timeout in practice (the arithmetic and its test are pinned; the wall-clock
  is not).
* **Whether the mid-range timeout hang in S1 is reachable in CI** — I proved
  the `OverflowError` half end-to-end and the acceptance half through
  `validate_timeouts`, but I did not run a real 45-minute job to watch the
  job-timeout kill.
* **`markdown-it-py`'s publish date** vs the 7-day cooling-off (offline), and
  the parser version `_agent-guidance` pins for
  `check-guidance-coverage.js` — the 28-row byte agreement remains the
  de-facto cross-check, and it is exact.
* **The other sessions' working trees** (`$SP/rev97b-code`, `$SP/r2mut97-*`,
  `$SP/se-*`) — out of scope by rule. I saw `r2mut97-slotB` suites running
  concurrently and left them alone; none of my runs shared a checkout with them.

---

## RECOMMENDATION

**Mergeable.** The round-1 blocker (B1) and every should-fix are closed, and I
could not break any of them from the production entry points. The one
should-fix I found (**S1**) is a bounded, trusted-input-only gap in the A2 fix
that a two-token change to one predicate closes; every committed fixture is
already outside its reach. I would take S1 and N1/N2 in a follow-up rather than
hold the PR, since none of them mints a credential, lets a contaminated arm
score, reaches an operator's files, or hangs.
