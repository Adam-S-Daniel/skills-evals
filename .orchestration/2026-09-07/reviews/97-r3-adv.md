FOUND — 0 blocker, 2 should-fix, 4 nit

# Round-3 adversarial review — `claude/skills-evals-97` @ `a6d165d`

Scope: attack, not confirm. Every row is a command I ran and its output. All
work under `HOME=$SP/r3adv97-home` with
`SKILLS_EVALS_USER_MEMORY=$SP/r3adv97-home/{usermem,watched}.md`,
`PYTHONPATH=/root/.local/lib/python3.11/site-packages`. The six named files in
`$SP/rev97c-adv` matched their stated md5s before I started; the tree is proved
byte-identical to a fresh `git archive a6d165d` at the end.

**Headline: every round-2 item I could reach from a production entry point is
genuinely closed.** The dispatch gate refuses a NUL in every position before the
substitution, neither rejection branch echoes the value (0 bytes of a 1 MB input
reached the log), the guard is two-sided in *both* directions through the real
hook, the timeout ceiling holds on all four fixture knobs, and the user-memory
guard now covers targeted runs against four different destruction mechanisms.

**Two should-fix items, and both are a round-2 item returning through its own
prescribed remedy** — the pattern this round was opened for:

* **S1-a** — the ceiling was added to the fixture knob, but `--timeout` on the
  command line *overrides* that knob and is checked by nothing. `--timeout
  2200000` is still rc 1 + a bare `OverflowError`; `--timeout 3000` runs the
  agent leg unbounded.
* **S-B-a** — the new AST pin catches **1 of 8** ordinary spellings of "spawn
  the suite", and does not look at `test/issues/` at all. Measured: **19**
  concurrent `run_tests.py` processes at 60 s and still climbing, with the pin
  green.

---

## FINDINGS

### S1-a (should-fix) — `--timeout` bypasses `validate_timeouts`; the S1 defect returns verbatim through the CLI override
`harness/run_eval.py:1422` (`--timeout`, `type=int`, no validation) feeding
`:816` and `:1158` — `"timeout": args.timeout or fixture.get("timeout_s", 600)`
— i.e. the override takes **precedence** over the value `validate_timeouts` just
bounded, and reaches `subprocess.run(timeout=...)` at `:537`.

REPEAT: **yes — round-2 S1 / round-1 A2, returning through S1's own prescribed
remedy.** The brief said "add an upper bound in the SAME predicate". That was
done, and the predicate only ever sees the fixture dict; `args` is not in it.

Reproduced through the real CLI entry point — fixture `timeout_s: 6`,
`guard.timeout_s: 20`, and a fake CLI that answers the guard honestly from
`$CLAUDE_CONFIG_DIR/CLAUDE.md` and then never returns for the scored leg:

| argv | rc | elapsed | last line |
|---|---|---|---|
| *(no `--timeout`)* | 2 | 6.3 s | `Runner-level error in arm(s): a` — the fixture knob fired |
| `--timeout 10` | 2 | 10.2 s | same, at 10 s |
| **`--timeout 3000`** | **NO-RETURN (>25 s)** | 25.0 s | — |
| **`--timeout 2200000`** | **1** | 0.2 s | **`OverflowError: timeout is too large`** |

and through the ordinary fake CLI: `--timeout 2701` → **rc 0, accepted** (above
the job budget), `--timeout 1000000000` → rc 1 + `OverflowError`, `--timeout -1`
→ rc 2 but as `Runner-level error in arm(s)`, not a named configuration error.

Severity — why should-fix and not blocker: the value is operator-typed, eval.yml
never passes `--timeout`, nothing is minted before a rejection, no contaminated
arm scores, no operator file is touched. It is byte-for-byte the severity round 2
assigned the identical defect on the fixture side. The escalation argument, for
the orchestrator to weigh: it *does* hang (bounded only by the 45-minute job
kill), and `--timeout` is precisely where an operator turned away by the new
message *"`timeout_s` must be a positive number of seconds no greater than
2700"* will put the number instead.

**Fix I would make:** run the same predicate on the override, beside the existing
call at `:1430` —

```python
validate_timeouts(fixture, args.eval_dir / "fixture.yaml")
if args.timeout is not None:
    validate_timeouts({"timeout_s": args.timeout}, "--timeout")  # same ceiling, same message
```

Tests through `main()`: `--timeout 2200000` → rc 2 named (red on `a6d165d`,
where it is rc 1 + `OverflowError`); `--timeout 2701` → rc 2 named (red today,
rc 0); `--timeout 600` unchanged. Mutation: drop the new call → the 2 200 000 row
returns to a traceback.

---

### S-B-a (should-fix) — the new AST pin catches one spelling of eight, and never looks at `test/issues/`
`test/run_tests.py:11905`
(`test_every_suite_forking_test_in_this_file_stands_down_in_a_child`). It flags
a function only when it contains the **exact string constant** `"run_tests.py"`
*and* an `ast.Attribute` `subprocess.run`. On the committed tree it flags exactly
one function.

REPEAT: **yes — round-2 S-B, returning through its own prescribed remedy.** The
brief said "the same `SKILLS_EVALS_SUITE_CHILD` guard at the top of the test ...
and the same for any other test in `test/run_tests.py` that shells out to the
whole suite". The guard was added; what enforces it is narrower than the rule.

Coverage, measured by running the pin's own predicate over eight spellings:

| spelling | flagged |
|---|---|
| `subprocess.run([... str(TEST_DIR / "run_tests.py")])` (the committed one) | **yes** |
| `subprocess.run([... str(RUNNER)])`, path in a module constant | **no** |
| `subprocess.Popen([... "run_tests.py"])` | **no** |
| `os.system("python3 test/run_tests.py")` | **no** |
| `from subprocess import run as r; r([...])` | **no** |
| `subprocess.run("python3 test/run_tests.py", shell=True)` | **no** |
| `subprocess.check_call([... "run_tests.py"])` | **no** |
| a helper in another module | **no** |

And nothing else bounds the fork. In a throwaway copy I appended a probe class
using `subprocess.Popen` plus a module-level `R3ADV_RUNNER = TEST_DIR /
"run_tests.py"`, with no `_skip_in_child()` and no `SKILLS_EVALS_SUITE_CHILD`:

```
$ python3 test/run_tests.py -k test_every_suite_forking_test_in_this_file_stands_down_in_a_child
Ran 1 test ... OK                      <- the pin is GREEN with the probe present

$ python3 test/run_tests.py -k R3AdvForkProbe.test_via_popen_and_a_module_constant
t=5s  procs=3    t=20s procs=8     t=35s procs=12    t=50s procs=16
t=10s procs=5    t=25s procs=9     t=40s procs=13    t=55s procs=18
t=15s procs=6    t=30s procs=11    t=45s procs=15    t=60s procs=19   <- still climbing
```

(counted by resolving `/proc/<pid>/cwd` into the scratch checkout — three of the
four spellings spawn a *relative* path that a `pgrep -f` on the absolute one
misses, which is itself worth knowing. Killed by pid at the 60 s bound;
`remaining=0`.)

The larger half: **the pin parses `test/run_tests.py` only.** The four
suite-forking tests live in `test/issues/test_issue_97.py`, which is where this
PR's own per-issue-discovery design tells every future fixture PR to put its
tests. Measured, in a throwaway copy, with `self._skip_in_child()` deleted from
`test_planted_issue_module_is_discovered_and_fails_the_runner`:

```
$ python3 test/run_tests.py -k test_every_suite_forking_test_in_this_file_stands_down_in_a_child
Ran 1 test in 0.275s
OK                   <- green, over exactly the defect S-B exists to prevent
```

Severity — should-fix, not blocker: today's tree has one forking test in
`run_tests.py` and four in `test_issue_97.py`, and all five call
`_skip_in_child()`. Nothing is broken now; the guard advertised in the PR body
("A new AST pin keeps it that way") measurably does not keep it that way.

**Fix I would make:** widen the predicate and the file set, still by AST — walk
`test/run_tests.py` **and** every `test/issues/test_issue_*.py`; treat a function
as suite-forking when it contains any `ast.Constant` whose value *contains*
`run_tests.py` (covering the shell strings) **or** references a module-level name
bound to such a constant, and calls any of
`subprocess.run/Popen/call/check_call/check_output` or `os.system`. Assert the
flagged set is non-empty per file and that every member calls `_skip_in_child()`.
Red today for all seven uncaught spellings.

---

### N1 (nit) — a non-dict `guard:` container is an `AttributeError` traceback, rc 1, outside the rc-2 contract
`validate_timeouts` walks to a knob's parent and, when the parent is not a dict,
sets `node = {}` and `break`s — it *normalises the bad container away* rather
than rejecting it. `run_eval.py:1142` then calls
`(fixture.get("guard") or {}).get("timeout_s", 300)` on the surviving truthy
non-dict:

```
guard: [1]        rc=1  TB=True   AttributeError: 'list' object has no attribute 'get'
guard: 'x'        rc=1  TB=True   AttributeError: 'str' object has no attribute 'get'
guard: null       rc=0            (correct — falls back to the default)
judge: [1] / 'x'  rc=0            (the judge call sits inside `except Exception`, so it degrades)
```

The same defect *shape* A2 closed for the leaf ("a string yielded a TypeError
traceback and rc 1, outside the configuration-problem contract"), one level up.
No hang, no CLI call, trusted-fixture only. REPEAT: a residual of the A2/S1
remedy, not previously reported. **Fix:** in the parent walk, raise the same
named `GuidanceError` when a *present* parent key is neither a mapping nor
`None`.

### N2 (nit) — arm names `.` and `..` pass the traversal check and write outside the run directory
`harness/run_eval.py:924`, `_ARM_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")`.
The message it guards says arm names "become directory names under results/".
Measured through `main()`, one arm per run:

| arm name | rc | files written under `--results-dir` |
|---|---|---|
| `normal` | 0 | `guidance/security/TS/normal/summary.json` |
| `.` | 0 | `guidance/security/TS/summary.json` |
| **`..`** | **0** | **`guidance/security/summary.json`** and **`guidance/security/transcripts/raw.json`** |
| `../esc`, `a/b`, `a b`, `""` | 2 | refused, named |

An arm literally named `..` writes one level *above* the timestamped run
directory, into the per-key directory that accumulates run history on the public
`eval-results` branch. Not an escape from `results/`, and it needs a maintainer
to write such a fixture — but the two canonical traversal names are the ones the
traversal check lets through. REPEAT: no (round 2 tested `../esc` and `a/b`, not
the bare dots). **Fix:** `and name not in (".", "..")`, or require the first
character to be alphanumeric.

### N3 (nit) — the "does it fit the job" test counts two of the three per-arm costs
`test/issues/test_issue_97.py:2551` `_guidance_fixture_budget` returns
`timeout_s + guard.timeout_s`, times the arm count. `judge.timeout_s` is a real
per-arm cost on the guidance path (`run_eval.py:1203`, inside
`_run_guidance_arm`), and eval.yml runs **without** `--no-judge`. Planted as a
committed fixture in a throwaway copy:

```yaml
timeout_s: 120 ; guard: {timeout_s: 120} ; judge: {timeout_s: 2700} ; 5 arms
```
```
$ python3 test/run_tests.py -k fits_inside_the_workflow_job_timeout   ->  Ran 1 test  OK
validate_timeouts: ACCEPTED  (every knob is <= 2700)
budget test counts:  240 x 5 =  1200 s   (under its 2025 s threshold)
real worst case:    2940 x 5 = 14700 s   against a 2700 s job
```

This matters because round 2's argument for grading S1 should-fix rather than
blocker was "`test_every_guidance_fixture_fits_inside_the_workflow_job_timeout`
already bounds every **committed** guidance fixture". It bounds two of three
costs. (`setup_timeout_s` is validated but inert on the guidance path —
`run_setup` is called only from `_run_arm` and the objective-only branch — so it
does not add.) REPEAT: no. **Fix:** add `judge.timeout_s` (default 120) to
`_guidance_fixture_budget`, guarded by whether the fixture declares a
`judge_rubric`.

### N4 (nit) — the discovery dir is prepended to `sys.path`, and nothing pins what may live in it
`build_suite()` calls `loader.discover(..., top_level_dir=test/issues)`, which
puts that directory on `sys.path` for the rest of the process. Measured: with
`test/issues/colorsys.py` present (a name the pattern never matches, so it is
never loaded as a test),

```
colorsys.__file__ after discovery: .../test/issues/colorsys.py   | shadowed: True
```

`json` was unaffected only because `run_tests.py` imports it before discovery.
Nothing asserts that `test/issues/` holds only `test_issue_*.py`, so a helper
module dropped there silently shadows a same-named stdlib module for the whole
suite. Needs a committed file; no credential or isolation impact. REPEAT: no.
**Fix:** one assertion that every `*.py` under `DISCOVERY_DIR` matches
`DISCOVERY_PATTERN`.

### Record-only (measured, no change requested)
* **`build_suite(discovery_dir=...)` leaks.** Measured: it leaves the scratch
  module in `sys.modules` and the scratch directory on `sys.path`, both still
  there after the directory is deleted. Its one caller
  (`test_a_discovered_module_that_defines_no_tests_is_named_in_the_failure`)
  restores both via `addCleanup`, so nothing escapes today.
* **The manifest's `file:` is still unconstrained, and the sink is public.** A
  row `file: ../OUTSIDE_SECRET.md` is resolved and read from outside the
  checkout; with a probe that echoes its context, the content landed in
  `results/guidance/security/TS/a/transcripts/raw.json` (rc 0). Round 2 recorded
  this and the fix brief told the worker to leave it. Worth restating precisely:
  eval.yml's trust-boundary sentence justifies **executing** guidance content,
  and this is a **read-any-readable-file-and-publish-it** path whose sink is a
  public branch. One `Path.resolve().is_relative_to(guidance_dir)` closes it.
* **`deliver()`'s 120 s bound is not `guard.timeout_s`, and it orphans a
  grandchild.** A hook that `sleep 900`s gives rc 2 at **120.2 s** with
  `guidance configuration error: could not run ...`, and an orphaned `sleep 900`
  survived the run; I found and killed it. Repeat of a round-2 record-only item;
  the real hook spawns nothing long-lived.
* **The clean arm of a contaminated pair still gets a score written.** The run
  is rc 2, stdout says *"INCONCLUSIVE: at least one arm could not prove its
  delivery ... This is never a PASS and never a FAIL"*, and the report marks the
  bad arm INCONCLUSIVE — but the partner's `summary.json` carries
  `objective_checks`, while `run_guard`'s docstring calls contamination "just as
  fatal to the pair". Harmless in CI (a failed step skips the badge/commit step),
  so recorded rather than raised.
* **The plural prompt is a request, not a guarantee.** A contaminated control
  whose probe reports only its own decoy still scores clean (`err=None`,
  `contaminated=False`, `observed=True`). This is the documented residual and
  S-A's own paragraph says so; no prompt wording can close it.
* **`test/issues/__pycache__` keeps `.pyc` for two planted-then-deleted probe
  modules** after a full suite run. Inert (a `__pycache__`-only `.pyc` is not
  importable) and `.gitignore` covers `__pycache__/` and `*.pyc`.
* **The ceiling anchor reads the `eval` job by name.** Adding a second job with
  `timeout-minutes: 5` leaves the pin green (correct — the eval job is the one
  that runs the harness); changing the eval job's own budget to 30 turns it red
  (`AssertionError: 2700 != 1800`).
* **A 1 MB dispatch value fails closed on `Argument list too long`.** `grep` is
  never executed, `if ! grep` takes the rejection branch, rc 1, and no part of
  the value reaches the log.

---

## HELD UP UNDER ATTACK

### Surface 1 — the dispatch gate (67 rows)
The step's own `run:` block, extracted with `yaml.safe_load` from
`.github/workflows/eval.yml` and executed under `bash` with a synthetic
`$GITHUB_EVENT_PATH` written as **raw bytes** and a synthetic `evals/` tree.
`$RUNNER_TEMP` was inspected after every row.

**Step order proved from the parsed YAML, not from comments:** step 9 *Select and
validate the fixture to run* precedes step 10 *Mint OIDC token and exchange for
Anthropic access token* and step 11 *WIF auth preflight*.

**Nothing happens before a rejection.** On every rejecting row `$RUNNER_TEMP`
held `['event.json']` only; on an accepted row `['eval-fixture', 'eval-key',
'event.json']`. No `/tmp/R3ADV_PWNED*` sentinel was ever created.

**NUL, in every position (code-N3).** The JSON spelling below is backslash-u-0000:

| where the NUL escape sits | rc | message |
|---|---|---|
| leading / trailing / embedded / alone / doubled | **1** each | `dispatch input 'fixture' contains a NUL byte` |
| leading, in front of a name that is not a fixture | 1 | same |
| a **raw** NUL byte inside the JSON string | 5 | `jq: parse error` — fails closed before anything |

**Other escapes and non-strings.** backslash-u-0007 (BEL), backslash-u-001b
(ESC), backslash-b, a trailing lone surrogate backslash-udfff, a surrogate-pair
emoji, raw overlong `C0 AF` bytes and raw `ED A0 80` bytes → rc 1 on the charset
branch. A leading lone surrogate backslash-ud800 → rc 5 (jq parse error).
`inputs.fixture` as a **number** or `true` → `jq -e`'s `test()` errors on a
non-string, the NUL check is skipped, the substitution yields `"5"` / `"true"`,
the shape gate passes and the committed-set gate refuses: **rc 1, and the value
is NOT in the message** (I stripped the committed-fixture listing and checked the
message lines explicitly). `false` / `null` / absent `inputs` / `{}` / an empty
event file → the default, rc 0. `inputs` an array, string or number, or a
malformed event → rc 5 under `set -e`, fails closed.

**Neither rejection branch echoes the value (N1 / code-N4):** a 100 KB and a 1 MB
charset-clean non-fixture both give rc 1 with `contains_aaaa=False`; a
`R3ADV-CANARY-PAYLOAD` marker present nowhere in the tree never appeared in any
output.

**Shape and traversal:** `..`, `../evals/...`, `/etc/passwd`, `/evals/...`,
`./evals/x`, `evals//x`, a trailing slash, bare `evals`,
`evals/workflow-path-audit/fixture.yaml`, multi-line (`a\n<valid>`,
`<valid>\n$(id)`, `<valid>\n<valid2>`), CRLF, a bare CR, a tab, `*`, `evals/*`,
`[`, `?`, an inner space, a trailing space, a Cyrillic homoglyph, a combining
mark, `$( )`, backticks, `;`, `|`, `&&`, `>` — all rc 1, and every multi-line or
metacharacter row is caught by the **shape** branch before any matching.

**The here-string (S5), 20 trials per position** against a real
**130 050-byte / 2 550-row** committed list built from a synthetic tree: the
FIRST row **20/20 accepted**, the LAST row **20/20 accepted**. No false negative.

**Nested and symlinked:** `evals/writing-adrs/bootstrap` and
`evals/guidance/_delivery` accepted; a symlinked `fixture.yaml` accepted; a
symlinked *directory* refused (`find -P` does not descend it); an
untracked-but-present directory accepted (documented as N-i).

### Surface 2 — the workflow files
Parsed all six with `yaml.safe_load`: **26 `run:` blocks, 0 containing
`${{`; 25 `uses:` refs, all bare 40-hex SHAs** except
`Adam-S-Daniel/cms-platform/.github/workflows/scheduled-run-health.yml@v0.1.87`
(the fleet's documented carve-out). Zero `uses:` lines carry a trailing comment.
`eval.yml` triggers exactly `schedule` + `workflow_dispatch`; `permissions`
`{contents: write, id-token: write}` and `concurrency` `{real-eval,
cancel-in-progress: false}` are **identical to main `7c966ba`**; one job,
`timeout-minutes: 45`. All five eval.yml checkouts and all three ci.yml checkouts
carry `persist-credentials: false`, the new `_agent-guidance` one included.
`GITHUB_TOKEN` appears only in step 13's `env:` and `run:`. `ci.yml` (the
`pull_request` publisher of the required context) has **no** `concurrency` at
all, and neither does any job in either file. `git diff --stat 7c966ba a6d165d --
.github/` = `ci.yml` (+16) and `eval.yml` (+195), nothing else.

### Surface 3 — the ceiling (S1), all four fixture knobs
Every row through `python3 harness/run_eval.py ... --arm both` in a child:

| value (as YAML resolves it) | `timeout_s` | `setup_timeout_s` | `guard.timeout_s` | `judge.timeout_s` |
|---|---|---|---|---|
| `2700`, `2700.0`, `2699.999` | rc 0 | rc 0 | rc 0 | rc 0 |
| `2700.5`, `2701` | rc 2 named | rc 2 named | rc 2 named | rc 2 named |
| `"2700"`, `True`, `-0.0` | rc 2 named | rc 2 named | rc 2 named | rc 2 named |
| `1e400` (YAML resolves this to a *string*), `1.0e+400` (`inf`), `.nan`, `[3]` | rc 2 named | rc 2 named | rc 2 named | rc 2 named |

No `Traceback`, no `OverflowError` and no hang on any of the 48 rows.

### Surface 4 — the guard, both directions
Driven through `run_eval.main()` with the repo's fake CLI, a forging CLI and a
sabotaged real hook; tokens pinned, the run's own decoy minting exercised.

| probe / contamination | arms | rc | outcome |
|---|---|---|---|
| honest probe, real hook, no contamination | 2 | **0** | both arms score |
| forged `$MAGIC` only | 2 | 2 | treatment scores; **control `guard_contaminated`** |
| forged `$MAGIC $DECOY` | 2 | 2 | **both `guard_contaminated`**, neither scores |
| forged `$DECOY` only | 2 | 2 | **treatment `guard_contaminated`** — the quiet direction |
| reversed order / comma-joined / quoted / `+ NO-MAGIC-WORD` | 2 | 2 | `guard_contaminated` on both |
| lower-cased both tokens | 2 | 2 | `guard_miss` on both |
| a third, unknown token added | 2 | 2 | treatment scores, control contaminated — the unknown token is ignored |
| empty reply / `NO-MAGIC-WORD` | 2 | 2 | `guard_miss` on both |
| **ambient file carrying the CONTROL's decoy** (honest probe, real hook) | 2 | **2** | **treatment `guard_contaminated`**, control clean |
| ambient file carrying the TREATMENT token | 2 | 2 | control `guard_contaminated`, treatment clean |
| **sabotaged hook leaking the decoy into every arm** | 2 | **2** | treatment `guard_contaminated`, reply `TOKENAAA-9999 DECOYBBB-1111` |
| **two `none` arms**, reply = decoy1 only | 2 | 2 | ctrl_a scores; **ctrl_b `guard_contaminated`** |
| two `none` arms, reply = decoy2 only | 2 | 2 | **ctrl_a `guard_contaminated`**; ctrl_b scores |
| two `none` arms, reply = both decoys | 2 | 2 | **both `guard_contaminated`** |
| arms `none` + `stub`, each single-token reply | 2 | 2 | whichever arm did not own the token is contaminated |
| five-arm canary shape, reply `$MAGIC $DECOY` | 5 | 2 | all five `guard_contaminated` |

So **each control is forbidden the OTHER control's decoy** — measured directly,
`ctrl_a: observed=False contaminated=True reply='DECOYCCC-2222'` — and every
failure lands as INCONCLUSIVE with `objective_checks: null` and no score. The
paired clean rows still score in every case.

**Token independence:** 2 000 draws each — 2 000/2 000 distinct on both sides,
**zero overlap**, all matching `[A-Z]{8}-\d{4}`; patching `guidance.new_token`
does not move `new_decoy_token` and vice versa. Both are the same fixed length,
so one well-formed token can never be a substring of another.

**`test/fake-claude`:** `guidance_probe_literal` keys off
`PLURAL_MARKER = "every one of them"` through `_asked_for_every_word()`, which
whitespace-folds the `-p` value; the honest `guidance_probe` still exists and
still reports **every** magic word (`MAGIC_RE.findall`). **Mutation — revert
`GUARD_PROMPT` to the singular wording and nothing else:** `-k TestIssue97` →
`Ran 102 tests ... FAILED (failures=6)`, the named one being
`AssertionError: 'every one of them' not found in 'If your context contains a
magic word, ...' : GUARD_PROMPT must ask for EVERY magic word ...`.

### Surface 5 — delivery (A3)
Sabotaged `.claude/hooks/fleet-memory.sh` in a scratch guidance checkout, CLI
calls counted from `$FAKE_CLAUDE_ARGV_LOG`, `guard.timeout_s: 5`:

| hook | rc | elapsed | error | CLI calls |
|---|---|---|---|---|
| exits 3, writes nothing | **2** | 0.1 s | `delivery_failed` | **0** |
| exits 0, prints `fleet-guidance: current`, writes nothing | **2** | 0.1 s | `delivery_failed` | **0** |
| exits 0, writes an UNMARKED file | **2** | 0.1 s | `delivery_failed` | **0** |
| exits 0, marked block with the WRONG token | 2 | 0.1 s | `guard_miss` | 1 |
| `sleep 900` | 2 | **120.2 s** | `could not run ...` | 0 |

### Surface 6 — the env allowlist (S4 / A6 / N2-adv / N-h)
`guidance.agent_env` and `run_eval.agent_env` against a **118-name hostile
parent** (GitHub/Actions tokens, AWS/Azure/GCP, SSH/GPG/netrc, `LD_PRELOAD`,
`LD_AUDIT`, `NODE_OPTIONS`, `BASH_ENV`, `ENV`, `PYTHONSTARTUP`, proxies,
`VAULT_TOKEN`, `KUBECONFIG`, `CLAUDE_*`, `SKILLS_EVALS_*`, `FLEET_GUIDANCE_*`):

* **GUIDANCE arm — exactly 15 names**: `PATH LANG LC_ALL SHELL USER NODE_PATH` +
  `HOME TMPDIR CLAUDE_CONFIG_DIR WORKSPACE` (all scratch) + the five
  `ANTHROPIC_*`. **Zero** non-allowlisted hostile names.
* **SKILL arm — 118 names**, carrying `GITHUB_TOKEN`,
  `ACTIONS_ID_TOKEN_REQUEST_TOKEN` and `LD_PRELOAD` — exactly what the corrected
  header now says, per subject.
* `PASSTHROUGH` is the exact six-tuple; `EXTRA_PASSTHROUGH` is `()`.
* Fixture `env:` — `HOME`, `TMPDIR`, `CLAUDE_CONFIG_DIR` **refused** by name with
  a named `GuidanceError`. `XDG_CONFIG_HOME, TMP, TEMP, PYTHONPATH, PATH,
  LD_PRELOAD, NODE_OPTIONS, PYTHONSTARTUP, BASH_ENV, ENV, CLAUDE_BIN,
  CLAUDE_CODE_OAUTH_TOKEN, NODE_PATH, FLEET_GUIDANCE_SKIP,
  SKILLS_EVALS_USER_MEMORY, WORKSPACE` pass through — a code-execution surface for
  a *trusted* fixture, identical to main's skill path — and **none of them can
  re-point delivery or the hook**: `deliver()` builds the hook's environment from
  scratch (`PATH` only, plus the four it sets) and never reads `fixture["env"]`,
  so neither an ambient nor a fixture `FLEET_GUIDANCE_SKIP` /
  `FLEET_GUIDANCE_PAYLOAD` ever reaches `fleet-memory.sh`.
* `$VAR` in a fixture `env:` expands against the **child** environment:
  `X: "$GITHUB_TOKEN|$WORKSPACE|$HOME|$AWS_SECRET_ACCESS_KEY"` →
  `$GITHUB_TOKEN|/ws|/hm|$AWS_SECRET_ACCESS_KEY` — both credentials stay literal.
* The A6 header sentence names `WORKSPACE` and the fixture `env:` overlay, and
  matches the 15 measured names.

### Surface 7 — the runner (N5 / N7 / S2 / discovery)
* **`-k` selecting zero → rc 2**, message names the pattern:
  `FAILED: -k 'NoSuchThingAtAll' selected 0 of 788 tests. ...`
* **The memory guard runs on that path too.** With a planted module that writes
  `$SKILLS_EVALS_USER_MEMORY` at **import** time, `-k NoSuchThingAtAll` gives
  **rc 1** and `FAILED: this suite CHANGED ...` — the guard's 1 overrides the
  zero-selection 2.
* **Targeted runs are guarded (N7)** — `python3 test/run_tests.py
  R3AdvMemoryProbe.<t>` against a probe class injected into a throwaway copy:

  | mechanism | rc | fingerprint |
  |---|---|---|
  | direct write | **1** | `ce0613... -> 7078ca...` |
  | replace the file with a symlink to different content | **1** | `-> c04fd8...` |
  | rename away | **1** | `-> absent` |
  | replace via a new parent directory | **1** | `-> fc41c7...` |
  | write-then-restore | 0 | unchanged — documented residual, the bytes survive |
  | touches nothing | 0 | unchanged |

* **N6** — a planted `test/issues/test_issue_zz_r3adv_empty.py` containing only
  `VALUE = 1` fails with a message that **names the module** and says *"Each of
  them defines no test ..."*. A module that fails to **import** is a separate
  synthetic failing test (`RuntimeError: R3ADV import boom`, `errors=1`).
* Nothing planted survives: after a full suite run `test/issues/` holds
  `test_issue_97.py` and `__pycache__` only.

### Surface 9 — `arms:`
23 shapes through `main()`. Every hostile one is rc 2 with a named message:
`{}`, `null`, `[]`, `"section"`, `["section"]`, `{section: null}`, unknown mode,
missing `mode:`, `{a: "section"}`, an unknown key, `with_*` carrying
`mode: none`, `without_*` carrying `mode: full`, and the names `a/b`, `../esc`,
`a b`, `""`. Absent → the default `section`/`none` pair. A 200-character arm name
and an arm literally named `none` are accepted (harmless); `.` and `..` are N2
above. A duplicate `arms:` key is YAML last-wins, silently — standard, and the
same everywhere in the repo.

### Surface 10 — the merge of main `7c966ba`
AST union (top-level functions, classes, methods, constants) across main, branch
`c5ea933` and head `a6d165d`:

| file | in main not head | in branch not head | duplicated in head |
|---|---|---|---|
| `test/run_tests.py` (881 / 776 / **916**) | **none** | **none** | **none** |
| `harness/run_eval.py` (27 / 41 / **42**) | none | none | none |
| `harness/scorers/objective.py` (81 / 79 / **81**) | none | none | none — and **byte-identical to main's** |
| `harness/scorers/judge.py` | none | none | none — **byte-identical to main's** |
| `harness/guidance.py`, `test/test_propagation.py`, `scripts/make_badge.py`, `harness/run_canary.py` | none | none | none |

`run_setup` and `agent_env` are **AST-identical to main's**; `run_agent` differs
from main by exactly the branch's two guidance lines and is identical to the
branch's. `objective.py` carries `file_count`. **No test method present on main
is absent from head** (checked across every `test/*.py` on main), and **no file
on main is absent from head**. README/DESIGN are a union: the single main line
absent is the `run_tests.py` row rewritten to add `issues/`; the absent branch
lines are paragraphs this round's own N3/N4/S-A commits rewrote. The one method
that left the branch is `test_a_rejected_shape_is_not_echoed_back_into_the_log`,
superseded by `test_neither_rejection_branch_echoes_the_dispatched_value`.

### Surface 11 — hostile `_agent-guidance`
Every case rc 2, no traceback, no hang, nothing written outside the harness
scratch, `/etc/passwd` md5 `c6074901158adb775c86f3054ef6fe70` before and after:

| mutation | rc | elapsed |
|---|---|---|
| missing manifest | 2 | 0.1 s |
| malformed manifest YAML (wrapped in a named error, not raised) | 2 | 0.1 s |
| manifest `file:` pointing outside the checkout | 2 | 0.1 s |
| section id `../../etc/passwd` | 2 | 0.1 s — `invalid section id ... it becomes a results/ path segment` |
| `base.md` a symlink to `/etc/passwd` | 2 | 0.1 s |
| no fleet-memory hook | 2 | 0.2 s |
| a symlink out of the tree inside `agents-md/` | 0 | 0.3 s — ignored |
| **50 MB `base.md`** | 2 | **3.6 s** |

### Surface 12 — N-a / N-f
* **markdown-it lazy import.** With `markdown_it` replaced by a raising sentinel
  module, `evals/workflow-path-audit --arm objective-only` produced stdout
  **byte-identical** (after normalising tmp paths) to the run with the parser
  available, the same rc, and **zero** `Traceback`/`ImportError`.
* **N-f.** `evals/guidance/_delivery --arm objective-only` → **rc 2**: *"declares
  no top-level `objective_checks:` — objective-only has nothing to score. A
  guidance fixture's checks are per arm; run it with `--arm both` (or a named
  arm) instead."*

---

## VERIFIER TABLE

Run on `a6d165d` in a fresh copy of the read-only export, `HOME` and
`SKILLS_EVALS_USER_MEMORY` throwaway, siblings `_agent-guidance` and
`agentskills` present, `markdown-it-py` 4.2.0 on `PYTHONPATH`.

| verifier | expected | measured | rc |
|---|---|---|---|
| `python3 test/run_tests.py` | 788, 2 skipped, exit 0 | **Ran 788 tests in 175.994s — OK (skipped=2)** | **0** |
| `python3 test/test_propagation.py` | 164, 1 skipped | **Ran 164 tests in 5.291s — OK (skipped=1)** | **0** |
| `python3 test/run_tests.py -k TestIssue97` | narrowed, announced | **`NARROWED RUN: -k selected 102 of 788`**, Ran 102, OK | **0** |
| `python3 test/run_tests.py -k NoSuchThingAtAll` | rc 2, named | **`FAILED: -k 'NoSuchThingAtAll' selected 0 of 788 tests...`** | **2** |
| Rule 19: every skill fixture vs `$SP/mainx5` under `--arm objective-only` | identical per check | **11 of 11 identical** (rc and normalised stdout) | matched |
| guidance canary objective-only | rc 2 (N-f) | rc 2, named | **2** |
| `git diff --stat 7c966ba a6d165d -- evals/` | canary prompt + the new fixture only | `guidance-bridge-canary/fixture.yaml` 6 changed, `guidance/_delivery/fixture.yaml` +105 | — |
| `git diff --name-only c5ea933 a6d165d -- 'evals/*/seed/'` | no seed path from the branch | **empty** | — |
| `git diff --stat 7c966ba a6d165d -- .github/` | ci.yml + eval.yml only | **exactly those two** | — |

Rule 19 detail (rc main / rc head): `disarm-inherited-reach` 1/1 ·
`github-actions-sha-pinning` 1/1 · `guidance-bridge-canary` 2/2 ·
`post-failure-comment` 1/1 · `propagation` 2/2 · `rename-pdfs` 1/1 ·
`review-bash-ci-reliability` 1/1 · `windows-elevation-from-wsl` 1/1 ·
`workflow-path-audit` 1/1 · `writing-adrs/bootstrap` 1/1 ·
`writing-adrs/existing-convention` 1/1. Two rows (`guidance-bridge-canary`,
`propagation`) show a textual difference that is **only** the checkout root
inside the path my normaliser could not fold; the rc and the message are the
same.

The seed diff `c5ea933..a6d165d` under `evals/` is the two prompt edits the
worker names (`guidance-bridge-canary/fixture.yaml`,
`guidance/_delivery/fixture.yaml`, 6 lines each) plus the 14 `writing-adrs/*`
files that arrived with main's merge — **no `seed/` path from this branch**.

Mutations run (each in its own throwaway checkout, serial per checkout):

| mutation | result | rc |
|---|---|---|
| revert `GUARD_PROMPT` to the singular wording | `-k TestIssue97`: Ran 102, **FAILED (failures=6)**, naming the prompt pin | 1 |
| eval job `timeout-minutes: 45 -> 30` | the anchor is red: `2700 != 1800` | 1 |
| add a second job with `timeout-minutes: 5` | anchor **green** — it reads the `eval` job, which is correct | 0 |
| a suite-forking probe using `Popen` + a module constant | **S-B pin green**, 19 processes at 60 s | see S-B-a |
| `_skip_in_child()` deleted from a forking test in `test/issues/` | **S-B pin green** | see S-B-a |
| a committed guidance fixture with `judge.timeout_s: 2700` x 5 arms | budget test **green** at 1 200 s against a 14 700 s worst case | see N3 |
| an empty `test/issues/test_issue_zz_*.py` | discovery pin red, message names the module | 1 |
| a `test/issues/test_issue_zz_*.py` that raises on import | synthetic failing test, `errors=1` | 1 |

---

## TREE INTEGRITY AND SAFETY LEDGER

| item | start | end |
|---|---|---|
| `md5sum /root/.claude/CLAUDE.md` | **`935c291f2efb1ff55a463bccfde55e6a`** | **`935c291f2efb1ff55a463bccfde55e6a`** (56 099 B) — **unchanged** |
| `$SP/rev97c-adv/harness/guidance.py` | `47c7268b23f402405f898f197d227c00` | matched at start |
| `$SP/rev97c-adv/harness/run_eval.py` | `40a08f8a22cda74be4d76cb9351da2d0` | matched at start |
| `$SP/rev97c-adv/test/run_tests.py` | `842bf963db0000f2ff9a8d1f964f791b` | matched at start |
| `$SP/rev97c-adv/test/issues/test_issue_97.py` | `fe241884fe83389f7e38fc8b774b42bf` | matched at start |
| `$SP/rev97c-adv/.github/workflows/eval.yml` | `5e2ccf934b89a62d7b8dcc8749f19c75` | matched at start |
| `$SP/rev97c-adv/test/fake-claude` | `6863402fa23ca1b69f6340f817734b3f` | matched at start |
| `$SP/rev97c-adv` vs a fresh `git archive a6d165d` | — | **`diff -rq` clean — byte-identical.** One `harness/__pycache__` appeared, created by a single probe of mine that imported `guidance` from that path; I deleted it and re-verified. No `results/`, no probe module. |
| `$SP/rev97c-adv/test/issues/` | `test_issue_97.py` only | **`test_issue_97.py` only** — unchanged |
| a working copy's `test/issues/` after a full suite run | `test_issue_97.py` | `test_issue_97.py` + `__pycache__/` (holding `.pyc` for the two planted-then-deleted probe modules; `.gitignore` covers both). **No planted `.py` is left** — the head still plants `test_issue_zz_discovery_probe.py` there transiently and removes it; only the N6 assertion moved to a scratch discovery dir. |
| `/home/user/skills-evals` | clean | `git status --porcelain` = **0 files**, HEAD `527c729` — read-only git commands only |
| `$SP/rev97c-ref`, `$SP/mainx5`, `$SP/_agent-guidance`, `$SP/agentskills` | — | untouched (read only; `_agent-guidance` was **copied** into my scratch to serve as the suite's sibling, never written) |
| my scratch `$SP/r3adv97-work`, `$SP/r3adv97-home` | — | **deleted** |
| my `/tmp` leftovers (`skills-evals-*`, `r3adv-*`, `r19-*`) | — | **removed, 0 remain**. Four `/tmp/guidance-*` dirs timestamped 17:40–17:55 — before this session's first command at 20:35 — belong to another session and were left alone. |
| background processes I started | — | **0 remain**, verified by resolving `/proc/<pid>/cwd` rather than by name. One orphaned `sleep 900` grandchild from the hanging-hook probe was found and killed; the 19-deep fork tree was killed by pid at its 60 s bound. |
| network / GitHub writes / real `claude` / real `gh` / sessions, routines, reminders | — | **none**; nothing read under `~/.claude` beyond that one md5 |

---

## WHAT I COULD NOT MEASURE

* **Whether a real `claude` CLI honours `CLAUDE_CONFIG_DIR` for user memory** —
  the whole `--delivery user` premise. Everything above was measured against
  `test/fake-claude` and two CLIs I wrote. Only a real dispatch settles it.
  Unchanged from rounds 1 and 2.
* **The real dispatch** — the OIDC/WIF exchange, the `eval-results` push, and so
  whether a five-arm guidance run really fits the 45-minute job in wall-clock.
  The arithmetic is pinned (with the N3 gap); the clock is not.
* **Whether S1-a's mid-range hang is reachable in CI.** I proved `--timeout 3000`
  does not return and `--timeout 2200000` raises `OverflowError`, both locally; I
  did not run a 45-minute job to watch the kill.
* **`markdown-it-py`'s publish date** against the 7-day cooling-off (offline).
* **Other sessions' trees** (`$SP/rev97c-code`, `$SP/r3mut97-*`, `$SP/se-*`) —
  out of scope by rule. I saw `r3mut97-B` running its own `run_eval.py` and
  `fake-claude` children concurrently and left them alone; none of my runs shared
  a checkout with them, and my process accounting resolved `/proc/<pid>/cwd`
  precisely so as not to count or kill theirs.

---

## RECOMMENDATION

**Mergeable with two follow-ups, or one more fix pass — the orchestrator's
call.** Nothing I found mints or exports before a rejection, lets a contaminated
arm score, lets a hostile env or fixture reach the operator's files, or hangs on
the committed surface. The dispatch gate, the two-sided guard, the delivery
refusal, the env allowlist and the user-memory guard all survived everything I
threw at them, including several attacks rounds 1 and 2 did not run.

The two should-fix items matter for *what they are* rather than their blast
radius: both are a round-2 item returning through that item's own prescribed
remedy, which is the pattern this round was opened for. **S1-a** is one call away
from closed. **S-B-a** is the more interesting of the two — the pin that is
supposed to stop the next unbounded fork inspects one file and one call spelling,
and the file it does not inspect is the one this PR's own design directs new
tests into.
