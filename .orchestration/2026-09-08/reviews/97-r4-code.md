FOUND — 0 blocker, 0 should-fix, 5 nit

Round-4 code review (one-way-door half) — PR [#138](https://github.com/Adam-S-Daniel/skills-evals/pull/138),
issue [#97](https://github.com/Adam-S-Daniel/skills-evals/issues/97), head
`f9115ce9dd51415db78e6b6e76fcb4cf95d38a62`, round-3 head `a6d165d`, base `origin/main` = `7c966ba`.

**Every round-3 item (S1-a, S-B-a, F-1, C-N2, C-N3, C-N4, A-N1, A-N2, A-N3, A-N4, the
record-only docstring) landed and is red under a mutation driven through the production entry
point.** The two items that returned in round 3 through their own remedies are closed over the
surface, not the line: `--timeout` is bounded in all **three** entry points that declare it
(`run_eval.py`, `run_canary.py`, `run_propagation.py` — rc 2 named, zero CLI calls, on every row),
and the fork pin is RED over **14 of 14** spellings I planted, including three of my own, in both
files it parses. No round-1, round-2 or round-3 item regressed (17 measurements, one each).
`.github/` and `evals/` are **byte-unchanged** since `a6d165d` by command. Rule 19 holds: 11 of 11
fixtures identical to main by exit code *and* by full per-check JSON. The key-bearing workflow's
gate was **executed under bash against 40 inputs** and nothing was minted or exported before any
rejection.

The five nits are all "the pin does not cover one more path to the same sink". **None is
reachable on the committed tree** — each needs new code to be written first — which is why none
is graded should-fix. Two of them (N1, N2) arrive through the brief's own prescribed remedies and
are marked as such.

---

## 0. Safety ledger and tree integrity

| | Before first command | After last command |
|---|---|---|
| `/root/.claude/CLAUDE.md` | **`935c291f2efb1ff55a463bccfde55e6a`** | **`935c291f2efb1ff55a463bccfde55e6a`** — unchanged |

mtime unchanged at `2026-09-06 01:56:03`, size 56099. Every suite run, probe and mutation ran with
`HOME=$SP/r4w97-home` and `SKILLS_EVALS_USER_MEMORY=$SP/r4w97-home/*.md`; `markdown-it-py` 4.2.0
was reached with `PYTHONPATH=/root/.local/lib/python3.11/site-packages`, never by pointing HOME at
the real one. Nothing was written under `/root/.claude`.

**No code path under test resolves a path under the real HOME — measured, not asserted.** I
instrumented `guidance.deliver`, `guidance.agent_env` and `guidance._refuse_real_config_dir` in a
throwaway copy and ran the whole 807-test suite through it (`Ran 807 tests in 213.822s`,
`OK (skipped=2)`, rc 0):

```
distinct (fn, arg, path) tuples: 2945
by function: {'agent_env': 1200, 'deliver': 1075, '_refuse_real_config_dir': 670}
path roots: {'tmp': 2945}     under /root: 0     NOT under /tmp: 0
```

**Work-dir integrity.** All thirteen named md5s verified at start **and** at end, identical to the
brief:

```
48cd216b76a40a95528fb36419fb2ed5  harness/guidance.py
5013e085026480ccb0cd8c4dac233703  harness/run_eval.py
d673dc1030980e0fe018f938631ba8eb  harness/run_canary.py
27ba4764d7a36b723ab07548b6b69b3e  harness/run_propagation.py
adafa45930148ba2aa23ca75eb4ce6da  test/run_tests.py
266a4431b4926d1a6703251229623b0a  test/issues/test_issue_97.py
5e2ccf934b89a62d7b8dcc8749f19c75  .github/workflows/eval.yml
aa540eb0a52779a08f40dc19cbee1acd  .github/workflows/ci.yml
6863402fa23ca1b69f6340f817734b3f  test/fake-claude
cc70a869e850f02912ac010e3d400241  evals/guidance/_delivery/fixture.yaml
e8d70f0a7ebda25e6927f357454b6640  evals/guidance-bridge-canary/fixture.yaml
094672e55d76c1c7df3ec25f3965333a  DESIGN.md
260614fc2e7c3823f0915259864ee2c0  README.md
```

`diff -rq $SP/rev97d-code <(fresh git archive f9115ce)` → **BYTE-IDENTICAL** after cleanup.
`rev97d-ref` is byte-identical to `a6d165d`; `mainx5` byte-identical to `7c966ba`; the
`_agent-guidance` and `agentskills` siblings have **0** files modified in the last 6 h. I entered
none of the other reviewers' directories (`rev97d-adv`, `r4adv97-*`, `rev129*`, `r2mut129-*`,
`r3adv129-*`, `rev124*`, `se-*`).

**`test/issues/` before and after a full run.**

| | contents |
|---|---|
| before | `test_issue_97.py` |
| **during** a full run | `test_issue_97.py`, **`test_issue_zz_memory_probe.py`** (caught in the act — a `cp -a` I took mid-run picked it up; I removed it from all four copies before using them) |
| after a full 807-test run | `test_issue_97.py`, `__pycache__/` |
| after my cleanup | `test_issue_97.py` |

The transiently planted probe modules are the round-3 record-only item, unchanged. `__pycache__/`
is gitignored; I removed it, and the tree is byte-identical to the archive.

**Processes.** Four orphaned `test/fake-claude` children (319–547 s old) survived the hollowness
splice run on the **ref** tree — which is itself a datum for S1-a: on `a6d165d` a `--timeout`
above the ceiling reaches an unbounded leg and the child's outer bound leaves the grandchild
behind. I killed all four by pid; **survivors from my work: 0**. All mutation copies
(`$SP/r4mut97-*`) and the throwaway HOME are deleted.

---

## 1. Verifiers

| Verifier | Exit | Result | Skips |
|---|---|---|---|
| `python3 test/run_tests.py` | **0** | **Ran 807 tests** in 218.9 s, `OK` | **2** |
| `python3 test/run_tests.py` (instrumented copy, §0) | **0** | **Ran 807 tests** in 213.8 s, `OK` | 2 |
| `python3 test/run_tests.py -k TestIssue97` | **0** | `NARROWED RUN: -k selected 120 of 807`; **Ran 120 tests** in 202.5 s, `OK` | 0 |
| `python3 test/run_tests.py -k NoSuchThingAtAll` | **2** | `FAILED: -k 'NoSuchThingAtAll' selected 0 of 807 tests. A pattern that matches nothing is a typo…` | — |
| `python3 test/test_propagation.py` | **0** | **Ran 164 tests** in 7.5 s, `OK` | **1** |

Every number matches the brief's expectation exactly (807/2, 120 of 807, rc 2, 164/1). Both skips
are `pypdf not installed`; both siblings are present, so it is 2 and not 3.

**Exit codes were captured from the process, never from a pipeline.** My first `-k` batch read
`rc=0` off a `| tail` and I discarded it; every row above is `$?` of the python process itself.

---

## 2. Per-item certification

Mutations ran in throwaway copies under `$SP/r4mut97-*` with `PYTHONDONTWRITEBYTECODE=1` and every
`__pycache__` deleted first, driven through the production entry point.

| Item | Landed? | Red-first / red-mutation | Surface enumerated & covered? | Verdict |
|---|---|---|---|---|
| **S1-a** `dcd23d2` | yes | 5 rejecting rows rc 2 / 0 CLI in **3** entry points; ref: rc 1 `OverflowError`, rc 0 at 2701, runner-level at −1. Four mutations red (§2.1) | **yes** — my own AST walk of `harness/**/*.py` finds **17** sites / 16 keys, **identical** to the test's table: 0 unlisted, 0 stale, 0 count mismatch | **PASS** (nit N1) |
| **S-B-a** `8350a36` | yes | **14/14** planted spellings RED naming the function+line; `_skip_in_child()` deletion in `test/issues/` RED | **yes for the two files it parses**; one directory (`test/` itself) is outside it | **PASS** (nit N2) |
| **F-1** `a2c5b3c` | yes | 3 escape shapes rc 2 / 0 CLI / nothing in results; ref rc 0 with the marker in `summary.json` **and** `transcripts/raw.json`; drop-both mutation → rc 0 + marker, 2 tests red | **yes** — `row["file"]` is the only manifest-derived path (my own AST enumeration of every `open`/`read_*`/`Path()`/`shutil`/`subprocess` in both modules) | **PASS** (nits N4, N5) |
| **C-N2** `f46bbd0` | yes | `**`→`*` on the **committed** tree → RED naming `evals/writing-adrs/bootstrap`; scratch half also red | yes — one glob spelling, both halves falsify it; no hardcoded count | **PASS** |
| **C-N3** `9fc2e2a` | yes | 6 rows on head; **exactly 3** RED on the ref (README ×2, DESIGN ×1); `assertTrue` form confirmed in source | yes — 3 docs × 2 reasons, phrase census reproduced by independent grep | **PASS** |
| **C-N4** `26fd51a` | yes | `assertTrue(name in defined, …)` confirmed; one `CHILD_RC_PINS` target renamed → **330 B** failure block vs **8 524 B** with `assertIn` restored | yes — both `CHILD_RC_PINS` entries | **PASS** |
| **A-N1** `d7bda1f` | yes | 9 rows (`guard`/`judge`/`env` × `[1]`/`'x'`/`7`) → rc 2, **no traceback**, 0 CLI, 0 files; ref: 6 tracebacks + 3 silent rc 0 | **yes** — my own scan finds `guard` the only `(fixture.get(X) or {}).get()`; `MAPPING_FIXTURE_KEYS` = `('guard','judge','env')` **derived** from `TIMEOUT_KNOBS` + `env` | **PASS** |
| **A-N2** `53ca857` | yes | `.`/`..` rc 2 with **0 files** under `--results-dir`; mutation → `..` writes `guidance/alpha/{summary.json,transcripts/raw.json}` **above** the run dir | yes — 12 names tested incl. all 5 committed arm names; `_validate_arm_entry` is the single gate | **PASS** |
| **A-N3** `91f074c` | yes | planted 5-arm `judge.timeout_s: 2700` → **RED** `15300 not less than 2025.0`; ref-style helper grafted → the arithmetic pin RED (`30 != 150`) | yes — 4 costs; `deliver()`'s 120 confirmed **actually passed** (the one caller passes no `timeout=`, by AST); the judge branch key is `fixture.get('judge_rubric')`, the same key `_run_guidance_arm` uses (by AST); `run_setup` absent from `_run_guidance_arm` **asserted by `ast`**, not a comment | **PASS** |
| **A-N4** `ec6bfea` | yes | `colorsys.py` plant → RED `Lists differ: ['colorsys.py'] != []`; committed tree green; vacuity floor fires on an empty dir | **`*.py` only** — a package is invisible and shadows identically | **PASS** (nit N3) |
| **docstring** `f9115ce` | yes | `git diff f9115ce^ f9115ce` is one hunk in `run_guard`'s docstring; **AST equal ignoring docstrings = True**, and the only docstring that changed is `run_guard`'s | n/a | **PASS** |
| **regression, rounds 1–3** | — | 17 measurements, §5 | — | **NO REGRESSION** |
| **merge state** | — | §6 | — | **CLEAN** |

### 2.1 S1-a — the ceiling is a harness ceiling, measured through the real CLI

`CLAUDE_BIN=test/fake-claude … python3 harness/run_eval.py evals/workflow-path-audit --arm
without_skill --no-judge --timeout N`, with `$FAKE_CLAUDE_ARGV_LOG` set:

| `--timeout` | head rc / CLI calls | ref (`a6d165d`) |
|---|---|---|
| `2200000`, `1000000000` | **2**, **0 CLI** — `` configuration error: `--timeout` must be a positive number of seconds no greater than 2700 `` | rc 1, bare `OverflowError: timeout is too large` |
| `2701` | **2**, 0 CLI | rc 0 — accepted above the job budget |
| `0` | **2**, 0 CLI | rc 0 — swallowed by `args.timeout or …` |
| `-1` | **2**, 0 CLI, named at parse time | rc 2 as `Runner-level error in arm(s)` |
| `600`, `2700` | **0**, 1 CLI | rc 0 |
| `3000` **against a CLI that sleeps 3000 s** | **2 in 0 s** | (the round-3 no-return case) |

The same five rejecting rows on **`run_canary.py`** (`evals/guidance-bridge-canary`) and
**`run_propagation.py`** (`evals/propagation --self-test`): rc 2, 0 CLI calls, the same message;
`--timeout 60` / `--timeout 120` unaffected (canary rc 0 with 4 CLI calls; propagation reaches its
own registry check).

**The AST inventory, reproduced independently.** My own walk (`ast`, resolving
`import subprocess as X` and `from subprocess import run as r`, `run/Popen/call/check_call/
check_output` plus `.wait(`/`.communicate(` carrying `timeout=`) over all 13 `harness/**/*.py`:

```
my sites: 17   my keys: 16
IN MINE NOT IN TABLE: []     IN TABLE NOT IN MINE: []     COUNT MISMATCH: []
```

Two spawner calls carry no `timeout=` at all and are correctly absent:
`harness/propagation/init_probe.py:237 subprocess.Popen` (bounded by its `.wait(timeout=10)` at
:276, which IS in the table) and `harness/run_eval.py:608 subprocess.run` (`_git`).

**What the walk CANNOT see, and whether it exists on head** — I probed for all four, and the
answer is **none exist**: `**kwargs` unpacked into a spawner (0), a positional
`wait(10)`/`communicate(x, 10)` (0), `getattr(subprocess, "run")(…)` (0), a module-level name
bound to `subprocess.<fn>` (0). What it *structurally* cannot see is a **caller** overriding a
callee's default — that is nit N1.

Mutations:

| mutation | result |
|---|---|
| drop the `run_eval` `--timeout` predicate | `--timeout 2200000` returns to rc 1 + `OverflowError`; inventory RED naming `harness/run_eval.py run_agent() subprocess.run(timeout=timeout): … the S1-a defect returning`; the flag test RED too |
| drop the `run_canary` predicate | inventory RED naming `harness/run_canary.py run_leg()` |
| plant `subprocess.run(["true"], timeout=args.new_flag)` in `harness/run_eval.py` | inventory RED: `Lists differ: ['harness/run_eval.py:602 in _r4_planted()…'] != []` |
| `eval.yml` `timeout-minutes: 45` → `30` | `AssertionError: 2700 != 1800 : harness/run_eval.py's MAX_TIMEOUT_S must equal eval.yml's 'timeout-minutes' x 60 for the eval job` |

The anchor is parsed, not matched: `_job_budget_s` is
`yaml.safe_load(EVAL_WORKFLOW…)["jobs"]["eval"]["timeout-minutes"] * 60`.

### 2.2 S-B-a — the fork pin over the whole surface

Each spelling planted **unguarded** in its own throwaway copy, running only the pin
(`-k test_every_suite_forking_test_in_this_repo_stands_down_in_a_child`, which selects 1 test, so
no planted forker ever executes):

| # | spelling | verdict |
|---|---|---|
| 01 | `subprocess.run([… str(TEST_DIR / "run_tests.py")])` | **RED** |
| 02 | module constant `RUNNER = TEST_DIR / "run_tests.py"` | **RED** |
| 03 | `subprocess.Popen([… "test/run_tests.py"])` | **RED** |
| 04 | `os.system("python3 test/run_tests.py")` | **RED** |
| 05 | `from subprocess import run as r3run` | **RED** |
| 06 | `subprocess.run("python3 test/run_tests.py", shell=True)` | **RED** |
| 07 | `subprocess.check_call([…])` | **RED** |
| 08 | a helper in **another** `test_issue_*.py` | **RED** (and the helper's own module named too) |
| 09 | a helper in the same module | **RED** |
| 10 | a parameterised helper `_spawn(RUNNER)` | **RED** |
| **11** | **mine:** a **class-level** constant `MY_RUNNER = TEST_DIR / "run_tests.py"` | **RED** |
| **12** | **mine:** `os.posix_spawn(…)` | **RED** |
| **13** | **mine:** `subprocess.call([sys.executable, str(Path(__file__).parent.parent / "run_tests.py")])` | **RED** |
| **14** | **mine:** the same, planted in `test/run_tests.py` itself | **RED** |

Every red is the guard branch, naming the function and its line, e.g.

```
AssertionError: False is not true : test/issues/test_issue_97.py:3486 test_r4probe_eleven()
can spawn the whole suite but neither it nor any helper it calls reads
$SKILLS_EVALS_SUITE_CHILD (`self._skip_in_child()` is the spelling both files use) …
```

(My first pass named the probes `zzprobe_*`; the pin correctly routed them to its *helper* branch
instead, because `_unittest_runs` keys on a `test`/`setUp`/`tearDown` prefix. I re-ran all 14 with
`test_`-prefixed names to exercise the guard branch. Both branches are red, with different
messages — worth knowing.)

**Deleting `_skip_in_child()` from `test_planted_issue_module_is_discovered_and_fails_the_runner`
(in `test/issues/`, which the round-3 pin never parsed):** **RED**, naming
`test/issues/test_issue_97.py:238`.

**Committed tree: green, and the flagged set is exactly the six**, reproduced by driving
`_SuiteForkScan` myself over the same file set:

```
test/run_tests.py::test_dash_k_on_the_command_line_still_reaches_the_discovered_subtree  guarded=True
test/issues/test_issue_97.py::_run_suite                                                guarded=False
test/issues/test_issue_97.py::test_an_ordinary_run_leaves_the_watched_file_alone         guarded=True
test/issues/test_issue_97.py::test_planted_issue_module_is_discovered_and_fails_the_runner guarded=True
test/issues/test_issue_97.py::test_removing_the_planted_module_puts_the_runner_back_to_zero guarded=True
test/issues/test_issue_97.py::test_the_run_wide_user_memory_guard_fails_a_run_that_writes_the_file guarded=True
```

The guard shape it pins is a **READ** of `SKILLS_EVALS_SUITE_CHILD` somewhere in the forking
test's own call closure (`os.environ.get` / `in os.environ` / `os.environ[…]`), and it asserts
explicitly that `_run_suite` — which SETS the marker — is **not** guarded. That is the committed
shape, and it is stated rather than implied.

**RULING on the worker's declared deviation.** The brief said "refuse an empty flagged set PER
FILE that has any subprocess use"; the worker shipped exact membership + a per-file floor for the
two files `KNOWN_SUITE_FORKERS` names + a global non-empty refusal.

* **Stronger on the axis that matters, measured.** Exact membership goes red the moment the
  recogniser loses *one* spelling; the brief's rule only fires when a whole file empties. Round 3's
  defect was a recogniser that saw 1 of 8 — under the brief's literal rule that state is GREEN
  (the file still had one flagged function); under exact membership it is RED.
* **The false alarm is real, and I measured it.** I planted a legitimate
  `test/issues/test_issue_zz_r4nofork.py` that spawns `harness/run_eval.py` and never the runner:
  `has-subprocess-use=True, flagged=[]` → **the brief's literal rule fails that file**, the
  worker's pin stays green (rc 0). `test_issue_97.py` itself has that shape many times over.
* **Weaker in one direction:** a *future third file* that really does fork, whose spelling the
  recogniser misses, is caught by the brief's rule (if it also has other subprocess use) and not by
  the per-file floor, which covers only the two named files. Given the recogniser now handles 14
  spellings including `os.spawn*`/`os.exec*` by prefix, that gap is small.
* **Net: stronger, and the deviation is accepted.**

**Does exact membership make every legitimate new forking test a mandatory edit of the pin?**
**Yes** — measured, all 14 plants also fail the membership `assertEqual`. That is acceptable
because the failure message says so in as many words: *"the list is here so adding one is a
decision rather than an accident. Add or remove the entry — and if a NEW entry is a surprise, that
function forks the whole suite and probably should not."* An ordinary new `test/issues/` module
adds nothing to the list (measured above).

### 2.3 F-1 — the read boundary

Rows through `main()` (`python3 harness/run_eval.py <guidance fixture> --arm a --no-judge
--guidance <checkout> --delivery project --results-dir …`), synthetic checkout, marker
`R4CODE-F1-OUTSIDE-SECRET` in a file one level **above** the checkout:

| manifest row | head | ref `a6d165d` |
|---|---|---|
| `file: ../OUTSIDE_SECRET.md` | **rc 2**, `the guidance path '../OUTSIDE_SECRET.md' resolves to … which is OUTSIDE the checkout at …`, **0 CLI**, marker in **0** files under `results/`, marker **not echoed** | **rc 0**, marker in `guidance/alpha/<ts>/a/transcripts/raw.json` **and** `…/summary.json` |
| in-tree symlink `agents-md/linked.md` → outside | **rc 2**, same message | **rc 0**, same two files |
| absolute `file: /…/OUTSIDE_SECRET.md` | **rc 2**, same message | **rc 0**, same two files |
| ordinary in-tree `file: agents-md/base.md` | **rc 0**, 2 CLI calls | rc 0 |
| the real 28-row `_agent-guidance` manifest | 8 distinct files, all under `agents-md/`, all resolve inside — and `test_the_real_manifest_rows_all_resolve_inside_the_checkout` is RED on the ref | — |

**Mutations.**

| mutation | escape rows | tests |
|---|---|---|
| drop containment in **`_read` only** | **still rc 2, all three** — `load_manifest`'s check catches every row, because every `file:` is validated at load | `-k TestIssue97`: **120 tests, rc 0, OK** → the `_read` half is **unpinned** (nit N4) |
| drop containment in **both** | **rc 0, all three**, marker in 2 files each | `-k TestIssue97` rc 1, **`test_a_manifest_file_outside_the_checkout_is_refused_by_name`** and **`test_a_manifest_file_symlinked_out_of_the_checkout_is_refused`** RED |

**Independent enumeration of every path `guidance.py` / `run_eval.py` opens from manifest or
fixture data** (AST over `open`, `read_text`, `read_bytes`, `Path(...)`, `shutil.*`, `subprocess`
cwd/args): in `guidance.py`, `row["file"]` at `_read` (via `inside_checkout`) and at `corpus`
(a `Path(row["file"]) == BASE_REL` **comparison**, not an open) are the only manifest-derived
paths; `MANIFEST_REL`, `BASE_REL`, `STUB_REL`, `HOOK_REL` are module constants; `deliver`'s
`payload_path`/`dest_dir` and `_refuse_real_config_dir`'s targets are harness-chosen. In
`run_eval.py` the fixture-derived paths are `eval_dir/"fixture.yaml"`, `eval_dir/"seed"`, the arm
dir (now guarded by A-N2), `mkdtemp`s, and the registry paths (operator-supplied). The `section:`
id never becomes a path into the checkout — `_run_guidance` refuses `/`, `.` and `..` in it before
it becomes a `results/` segment (`harness/run_eval.py:1336-1340`, read and confirmed).

The two clauses are pinned by `only from inside`, `trust boundary`, `eval-results` in
`guidance.__doc__` **and** `DESIGN.md`, with `assertTrue` (not `assertIn`), and
`test_the_containment_boundary_is_written_down_in_both_places` is **RED on the ref**.

### 2.4 A-N3 — is 225 s of headroom enough?

Derived myself from `eval.yml`: threshold = `jobs.eval.timeout-minutes` × 60 × **0.75** = 2700 ×
0.75 = **2025 s**. `evals/guidance/_delivery`: agent 120 + guard 120 + judge **0** (no
`judge_rubric:` declared — confirmed) + deliver **120** = **360 s** per arm × **5** arms =
**1800 s**. Headroom to the threshold: **225 s**.

**The brief's question mis-frames the number slightly, and the answer is better than it looks.**
225 s is the margin a *future fixture author* has before the test goes red — it is not the
overhead allowance. The overhead allowance is what the 0.75 factor reserves: the assertion
guarantees the arms cannot claim more than 2025 s of a 2700 s job, leaving **675 s (11 min 15 s)**
for checkouts, `npm i` of the CLI, `pip install`, the gate, the OIDC exchange, the WIF preflight,
the badge commit/push and the artifact upload; against today's committed fixture the real slack is
**900 s (15 min)**. Both are generous for that step list. And these are *timeout* budgets, not
expected durations — a run that spends the full 1800 s has already failed five arms. I judge the
headroom adequate; I could not measure the real non-arm overhead (no real dispatch — §8).

`deliver()`'s 120 is confirmed to be the value **actually passed**: the single call site
(`harness/run_eval.py:1159`) passes `scratch`, `home`, `payload`, `dest_dir` and **no** `timeout=`
(by AST). The judge branch key is `fixture.get('judge_rubric')` inside `_run_guidance_arm` (by
AST) — the same key the budget helper uses. `setup_timeout_s`'s inertness is asserted by parsing
`_run_guidance_arm` with `ast` and checking `run_setup` is not among its `Name` calls — **not** a
comment.

---

## 3. Hollowness — every NEW test, run on a throwaway copy of `a6d165d`

**Named by AST diff**, not by reading: `test/run_tests.py` 688 → 689 methods (+2 −1),
`test/issues/test_issue_97.py` 102 → 120 (+19 −1). **21 new, 2 removed, net +19** — which is
exactly `807 − 788`. The two removals are renames
(`…_in_this_file_…` → `…_in_this_repo_…`; `test_the_residual_paragraph_names_both_reasons…` →
`test_all_three_residual_paragraphs_name_both_reasons…`).

Head's `test/issues/test_issue_97.py` spliced onto a copy of the ref tree and run through the
production entry point (`python3 test/run_tests.py -v -k TestIssue97`, never `python3 <file>`):
**Ran 120 tests, FAILED (failures=31, errors=39), rc 1.**

| new test | on ref |
|---|---|
| `test_a_cli_timeout_over_the_budget_does_not_reach_a_hanging_leg` | **RED** |
| `test_a_cli_timeout_override_is_held_to_the_same_ceiling` | **RED** |
| `test_a_manifest_file_outside_the_checkout_is_refused_by_name` | **RED** |
| `test_a_manifest_file_symlinked_out_of_the_checkout_is_refused` | **RED** |
| `test_a_non_mapping_fixture_key_is_a_named_configuration_error` | **RED** |
| `test_all_three_residual_paragraphs_name_both_reasons_the_guard_cannot_settle` | **RED** (3 of 6 subtests) |
| `test_every_harness_subprocess_timeout_names_its_validated_source` | **RED** |
| `test_every_harness_timeout_flag_is_bounded_by_the_one_predicate` | **RED** |
| `test_every_timeout_knob_parent_is_a_checked_mapping_key` | **RED** |
| `test_the_arm_name_rule_is_the_new_directory_property` | **RED** |
| `test_the_containment_boundary_is_written_down_in_both_places` | **RED** |
| `test_the_real_manifest_rows_all_resolve_inside_the_checkout` | **RED** |
| `test_the_two_traversal_arm_names_are_refused` | **RED** |
| `test_validate_timeouts_itself_refuses_a_non_mapping_parent` | **RED** |
| `test_a_cli_timeout_override_inside_the_ceiling_still_runs_the_arm` | green — **floor**; named mutation `if False:` in `check_timeout` → **RED** (values 600, 2700) |
| `test_an_explicit_null_or_absent_mapping_key_still_runs_the_arm` | green — **floor**; named mutation: `_require_mapping` stops allowing `None` → **RED** (`guard: null`, `judge: null`) |
| `test_an_ordinary_in_tree_manifest_row_is_untouched` | green — **floor**; named mutation: `inside_checkout` refuses everything → **RED** |
| `test_ordinary_and_committed_arm_names_are_accepted` | green — **floor**; named mutation: `_names_a_new_directory` returns False → **RED** (8 errors) |
| `test_the_guidance_budget_counts_every_per_arm_cost` | green — **floor** (the helper travels with the test); named mutation: graft the ref's `return agent + guard` → **RED** `30 != 150` |

**14 RED, 5 green-with-a-red-named-mutation, of 19.**

The two new `test/run_tests.py` tests are both **regression floors over already-correct code** —
a whole-file splice would carry the fix with the test, since in both cases the test *is* the fix:

| new test | on ref's own tree | named mutation |
|---|---|---|
| `test_every_python_file_in_the_discovery_dir_is_a_test_module` | would be green (no stray `.py`) | plant `test/issues/colorsys.py` → **RED**, `Lists differ: ['colorsys.py'] != []`; empty dir → **RED** on the vacuity floor |
| `test_every_suite_forking_test_in_this_repo_stands_down_in_a_child` | would be green (all 5 forkers guarded on the ref too) | **15** named mutations red: the 14 plants above **plus** deleting `_skip_in_child()` from a `test/issues/` forker |

---

## 4. Rule 19 / identity per check

Every committed fixture scored with `--arm objective-only --no-judge` on head and on `$SP/mainx5`
(`7c966ba`), `--results-dir` outside both trees, stdout + stderr + exit code compared after
normalising tree roots, `/tmp/...` paths and timestamps. The objective-only output **is** the
per-check JSON (`{"skill","arm","checks":[{"id","passed","detail"}…]}`), so this is per-check
identity, not just a rc comparison.

| Fixture | rc main/head | checks | per-check |
|---|---|---|---|
| `evals/disarm-inherited-reach` | 1/1 | 9 | **identical** |
| `evals/github-actions-sha-pinning` | 1/1 | 10 | **identical** |
| `evals/guidance-bridge-canary` | 2/2 | 0 | **identical** |
| `evals/post-failure-comment` | 1/1 | 12 | **identical** |
| `evals/propagation` | 2/2 | 0 | **identical** |
| `evals/rename-pdfs` | 1/1 | 8 | **identical** |
| `evals/review-bash-ci-reliability` | 1/1 | 11 | **identical** |
| `evals/windows-elevation-from-wsl` | 1/1 | 7 | **identical** |
| `evals/workflow-path-audit` | 1/1 | 8 | **identical** |
| **`evals/writing-adrs/bootstrap`** | 1/1 | 9 | **identical** |
| **`evals/writing-adrs/existing-convention`** | 1/1 | 7 | **identical** |
| `evals/guidance/_delivery` | — / **2** | — | new on the branch; the documented N-f message (`declares no top-level objective_checks:`), not `{"checks": []}` |

**11 of 11 identical** by exit code *and* every `(id, passed)` pair *and* the full JSON document,
both nested `writing-adrs/*` fixtures included. `git diff a6d165d..f9115ce -- evals/` is **empty**,
so no fixture prompt or seed changed this round.

---

## 5. Round-1 / 2 / 3 regression — one measurement each

| Item | Measurement on this head | Result |
|---|---|---|
| **B1** dispatch gate | the step's own `run:` block executed under bash against **40** inputs (§7); every rejecting row wrote nothing | **HOLDS** |
| **B0/S1** no real HOME path | 2 945 instrumented `(fn, arg, path)` tuples across the full 807-test suite, **100 % under `/tmp`**, 0 under `/root`; real `CLAUDE.md` md5 + mtime + size unchanged | **HOLDS** |
| **S2** run-wide memory snapshot | `if True: return status` in `memory_guard` → **2 red**: `…guard_fails_a_run_that_writes_the_file` **and** `test_a_targeted_run_is_covered_by_the_user_memory_guard_too` | **HOLDS** |
| **S3** discovery + argv | `if False and discovery_dir.is_dir():` → **2 red** (`test_build_suite_covers_every_discoverable_issue_module`, `test_dash_k_…_discovered_subtree`) | **HOLDS** |
| **S4** `PASSTHROUGH` exact | append `GITHUB_TOKEN` → **1 red** (`test_passthrough_is_exactly_the_committed_six`) | **HOLDS** |
| **S5** no pipe into grep | restore `printf … \| grep -Fxq` → **19 of 20 trials RED** on `test_the_fixture_match_survives_a_committed_list_far_larger_than_a_pipe` (the SIGPIPE race, exactly as documented — one trial passed) | **HOLDS** |
| **A3** `delivery_failed` | rename the error type → **2 red** | **HOLDS** |
| **A4** decoy / two-sided control | `decoy = None` → **3 red** (`…_control_arm_is_inconclusive_and_exits_2`, `…_prompt_obeying_probe`, `…_reports_the_controls_decoy_is_contaminated`) | **HOLDS** |
| **A5** `arms:` shapes | restore `fixture.get("arms") or DEFAULT_GUIDANCE_ARMS` → **2 tests / 6 subtests red** | **HOLDS** |
| **A6** header per subject | add `NEWLY_ADDED_ALLOWLIST_NAME` to `agent_env`'s output → **1 red**, `…is in the guidance arm's environment (measured through guidance.agent_env) and the header does not name it` | **HOLDS** |
| **round-2 S1** knob ceiling | drop `<= MAX_TIMEOUT_S` from the predicate → **3 red** across the `ceiling` tests | **HOLDS** |
| **N4-adv** symmetric guard | revert `forbidden` to the control-only token → **1 red** (`test_a_treatment_arm_that_reports_the_controls_decoy_is_contaminated`); the paired clean row stays green | **HOLDS** |
| **S-A** plural prompt | revert `GUARD_PROMPT` to the singular → **2 red** (`test_the_guard_prompt_asks_for_every_magic_word`, `test_a_contaminated_control_is_caught_by_a_prompt_obeying_probe`) | **HOLDS** |
| **S-B** child guard | delete `self._skip_in_child()` from `test_dash_k_…` in `test/run_tests.py` → **1 red** on the new pin | **HOLDS** |
| **N3-code** NUL refusal | delete the `jq -e` block from `eval.yml` → **4 red** subtests; and by execution, all 5 NUL positions still rc 1 with nothing written (§7) | **HOLDS** |
| **N5-adv** `-k` zero → 2 | `-k NoSuchThingAtAll` → **rc 2** with the named message | **HOLDS** |
| **N6-adv** empty module named | replace the "contribute NO test" message with the old discovery wording → **1 red**, `'test_issue_zz_empty' not found in …: the failure must NAME the offending module`; committed tree green | **HOLDS** |
| **N7-adv** targeted run guarded | covered by the S2 mutation above (`test_a_targeted_run_is_covered_by_the_user_memory_guard_too` red) | **HOLDS** |

No round-1, round-2 or round-3 item regressed.

---

## 6. Merge state

* `git merge-base --is-ancestor 7c966ba f9115ce` → **true**.
* `git merge-tree --write-tree origin/main f9115ce` → **rc 0**, tree `41edff2b…` — **clean**.
* `harness/scorers/objective.py` **byte-identical to main** (`726ef62a…` both sides);
  `harness/scorers/judge.py` byte-identical (`65990035…`). (`harness/objective.py` does not exist
  on either side — the file is `harness/scorers/objective.py`.)
* **The 85 tests main gained with #136** (`d5e06ee` → `7c966ba`, 588 → 673 methods in
  `test/run_tests.py`), named by AST: **0 missing from head**. `TestIssue80` 44,
  `FileCountCheckTests` 21, `LinkTargetsExistCheckTests` 17, `CiDispatchTests` 3.
* **Zero** of main's test methods are absent from head (`main − head = ∅`).
* All 11 commits `a6d165d..f9115ce` authored **and** committed as
  `4205216+Adam-S-Daniel@users.noreply.github.com`.

---

## 7. The one-way-door read

```
$ git diff a6d165d..f9115ce -- .github/ evals/   |  wc -c
0                                                       # and --name-only lists nothing
$ git diff --name-only 7c966ba..f9115ce -- .github/
.github/workflows/ci.yml
.github/workflows/eval.yml                              # +16 / +195, nothing else
```

| Rule | Result |
|---|---|
| Every `uses:` a bare 40-hex SHA | **25 across 6 workflows; 24 pass.** The one exception is `scheduled-run-health.yml:41` → `Adam-S-Daniel/cms-platform/.github/workflows/scheduled-run-health.yml@v0.1.87` — the documented `cms-platform` release-tag carve-out, pre-existing and outside this PR's diff |
| No trailing version comment on any `uses:` | **PASS** — zero, on all 25 |
| Zero `${{ }}` inside any `run:` | **PASS** — 26 `run:` blocks parsed from YAML, **0** containing `${{`. `eval.yml` has three `${{` occurrences total: two in comment prose (:44, :251) and one live at `:413`, `GITHUB_TOKEN: ${{ github.token }}` in step 14's own `env:` |
| `inputs.fixture` never interpolated | **PASS** — it appears only inside the two `jq` programs reading `$GITHUB_EVENT_PATH` as data (:284, :289) |
| `eval.yml` triggers | **PASS** — exactly `schedule` + `workflow_dispatch`; no `pull_request`, no `pull_request_target` |
| `permissions` minimal and unchanged from main | **PASS** — `{contents: write, id-token: write}` on head **and** on `7c966ba`; no job-level `permissions`. `ci.yml` `{contents: read}`, also identical to main |
| No `concurrency` on a job publishing a required context | **PASS** — `eval.yml`'s is workflow-level `{real-eval, cancel-in-progress: false}`, **identical to main**; **no** job-level `concurrency` anywhere; `ci.yml` (the `pull_request` publisher) has **none at all** |
| All checkouts pinned + `persist-credentials: false` | **PASS** — 5 in `eval.yml`, 3 in `ci.yml`, all on `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `_agent-guidance` checkout | **PASS** — `repository: Adam-S-Daniel/_agent-guidance`, `path: _agent-guidance`, `persist-credentials: false`, same pin, in both workflows |
| Push auth step-local | **PASS** — `GITHUB_TOKEN` in exactly one step's `env:` (step 14, the badge commit) and used only inside that step's `run:` |
| Validation **before** the OIDC/token exchange | **PASS, by parsed step index** — step **10** "Select and validate the fixture to run", step **11** "Mint OIDC token and exchange for Anthropic access token", step **12** "WIF auth preflight" |

### The executed gate — step 10's `run:` block under bash, 40 inputs

The block was extracted with `yaml.safe_load` and run under `bash` against a synthetic `evals/`
tree (3 top-level committed fixtures, the two **nested** `writing-adrs/*`, `guidance/_delivery`,
one existing directory with no `fixture.yaml`, one whose `fixture.yaml` is a **symlink**), with
`$GITHUB_EVENT_PATH` written as **raw bytes** and `$RUNNER_TEMP` inspected after every row. `\0`
below is a real NUL byte. `MARK` is a 24-char canary present nowhere in the tree.

| Input | rc | outputs written | value echoed? | rejected by |
|---|---|---|---|---|
| `evals/workflow-path-audit` | **0** | `eval-fixture`, `eval-key=workflow-path-audit` | — | accepted |
| **`evals/writing-adrs/bootstrap`** (nested) | **0** | key `writing-adrs/bootstrap` | — | accepted |
| `evals/guidance/_delivery` | **0** | key `guidance/_delivery` | — | accepted |
| `evals/symlinked` (symlinked `fixture.yaml`) | **0** | key `symlinked` | — | accepted (documented N-i) |
| `..`, `../../etc/passwd`, `/etc/passwd`, `/evals/…`, trailing slash, `evals/…/fixture.yaml`, `evals/uncommitted-dir` | **1** | **none** | **no** (227 B, constant) | no committed fixture |
| `evals/<MARK>`, **`evals/<MARK>` + 100 KB** | **1** | **none** | **no** — 227 B, *the same length as the short row* | no committed fixture |
| `*`, `evals/*`, `[`, leading/inner/trailing space, multi-line (2nd line committed), multi-line + `$(id)`, JSON array, JSON object | **1** | **none** | no (74 B) | **charset (`case`) guard** |
| **`\0` leading**, **`\0` trailing**, **`\0` embedded**, **`\0` alone**, **`\0` + MARK**, **`\0` + `*`** | **1** | **none** | no (55 B) | **NUL guard** — `contains a NUL byte` |
| empty string, `inputs` absent, `inputs: null`, `inputs` without `fixture`, `fixture: null`, empty event file | **0** | default `evals/workflow-path-audit` | — | schedule default |
| JSON `7`, JSON `true` | **1** | **none** | no | no committed fixture |
| malformed JSON, `inputs` a number, a **raw** NUL byte inside the JSON string | **5** | **none** | no | `jq` under `set -e` — fails closed |

```
REJECTED-BUT-WROTE-OUTPUT: []
ECHOED-VALUE ROWS:         []
```

**Nothing was minted or exported before any rejection**, on any of the 40 rows.
**Ordering, proved by execution:** a value that is *both* NUL-bearing and charset-violating
(`\0` + `*`) gives the **NUL** message — so the NUL check really runs before the substitution and
before the `case` guard.

---

## 8. Findings

### Blockers
**None.**

### Should-fix
**None.**

### Nits

**N1 — S1-a's inventory has four source kinds, and the one that makes a claim about CALLERS does
not check it.**
`test/issues/test_issue_97.py`, `HARNESS_TIMEOUT_SINKS` / `test_every_harness_subprocess_timeout_
names_its_validated_source`.

The table's `("default", "120")` kind is documented as *"a keyword default in the callee's own
signature, **no caller overriding it**"*, and the test verifies only `float("120") <= ceiling`. The
second half is never measured.

Reproducing input — in a throwaway copy, change `harness/run_eval.py:1159`'s one call to

```python
info = guidance.deliver(
    ctx["guidance_dir"], scratch=scratch, home=home, payload=payload,
    dest_dir=config if delivery == "user" else workspace,
    timeout=fixture.get("deliver_timeout_s", 2200000))
```

```
$ python3 test/run_tests.py -k test_every_harness_subprocess_timeout_names_its_validated_source
Ran 1 test ... OK                     rc=0
$ python3 test/run_tests.py -k test_every_harness_timeout_flag_is_bounded_by_the_one_predicate
Ran 1 test ... OK                     rc=0
$ python3 harness/run_eval.py <guidance fixture> --arm a --no-judge --guidance <checkout> …
rc=1
    fd_event_list = self._selector.poll(timeout)
OverflowError: timeout is too large
```

The sink's inventory key is unchanged (`… deliver, subprocess.run, "timeout"`), so both pins stay
green while an unvalidated fixture value reaches `subprocess.run(timeout=…)`.

**Not live.** I enumerated the whole caller surface: 8 functions under `harness/` carry a
`timeout` parameter through to a spawner, and **every** call site today passes a validated knob
(`ctx.timeout`, `judge_cfg.get('timeout_s', 120)`, `(fixture.get('guard') or {}).get('timeout_s',
300)`), a validated flag, or nothing at all — `guidance.deliver` and `judge.score` are the two with
defaults, and `deliver`'s only caller passes no `timeout=` (by AST).

**REPEAT?** Not at the same severity and not with the same fix: round-3 S1-a was a *live*
should-fix through an operator-typed flag. But it **does return through the brief's own prescribed
remedy** — the brief asked for a table that "names which validated source bounds" each site, and
one of the four kinds names a condition the table cannot enforce. Recorded on that basis.
*Fix, ~4 lines:* for a `("default", N)` row, also assert that no call to that callee anywhere under
`harness/` passes `timeout=` — the walk that builds the inventory already has the data.

---

**N2 — S-B-a's file set is `test/run_tests.py` + `test/issues/test_issue_*.py`; a helper module
under `test/` itself is reachable by an importing test and is covered by neither pin.**
`test/run_tests.py`, `test_every_suite_forking_test_in_this_repo_stands_down_in_a_child`.

The pin's docstring says: *"A helper in a module this walk does not parse still cannot be reached
— which is exactly why `test_every_python_file_in_the_discovery_dir_is_a_test_module` refuses a
non-test `.py` under `test/issues/` at all."* Measured, that sentence is false: A-N4 governs
`test/issues/`, and `test/` itself is `sys.path[0]` whenever the runner is invoked as
`python3 test/run_tests.py`.

Reproducing input — in a throwaway copy, add `test/forkhelper.py`:

```python
def r4_fork_the_suite():
    subprocess.run([sys.executable, str(TEST_DIR / "run_tests.py")])
```

and, in `test/issues/test_issue_97.py`, `import forkhelper as _r4fh` plus a test that calls it:

```
$ python3 test/run_tests.py -k test_every_suite_forking_test_in_this_repo_stands_down_in_a_child
Ran 1 test ... OK                                  rc=0      <- the pin
$ python3 test/run_tests.py -k test_every_python_file_in_the_discovery_dir_is_a_test_module
Ran 1 test ... OK                                  rc=0      <- A-N4
$ python3 -c "import sys; sys.path.insert(0,'test'); import forkhelper; print(forkhelper.__file__)"
.../test/forkhelper.py
```

An unguarded forking test written that way runs unbounded, which is the S-B defect. `test/` holds
a third `.py` today — `test/test_propagation.py` — which the pin does not parse; I checked it by
AST and it contains **no** constant mentioning `run_tests.py`, so nothing is broken now.

**REPEAT?** Round-3 S-B-a was should-fix over **7 of 8** ordinary spellings *inside the files the
pin already parsed*; this pin now handles **14 of 14** there, and the residual is one directory
with zero live instances. Not the same severity, not the same fix. It does, however, sit on the
same sink, and the docstring's mutual-support claim is the part that is wrong.
*Fix, one line + one clause:* build the file set from `sorted(TEST_DIR.rglob("*.py"))` (3 files
today), and correct the docstring sentence to say what actually bounds `test/`.

---

**N3 — A-N4 globs `*.py` and is blind to a PACKAGE, which shadows identically.**
`test/run_tests.py`, `test_every_python_file_in_the_discovery_dir_is_a_test_module`
(`present = sorted(DISCOVERY_DIR.glob("*.py"))`).

Reproducing input — plant `test/issues/colorsys/__init__.py` containing `HELPER = 1`:

```
$ python3 test/run_tests.py -k test_every_python_file_in_the_discovery_dir_is_a_test_module
Ran 1 test ... OK                                  rc=0

# and the shadowing the assertion exists to forbid still happens:
loader.discover(test/issues, pattern="test_issue_*.py", top_level_dir=test/issues)
import colorsys  ->  .../test/issues/colorsys/__init__.py     SHADOWED: True
```

The `.py` plant is correctly RED (`Lists differ: ['colorsys.py'] != []`) and the vacuity floor
fires on an empty dir — both measured. A package is simply outside the glob, and a package is also
somewhere a fork helper could live where N2's pin cannot parse it.
**REPEAT?** No. *Fix, ~3 lines:* also refuse any subdirectory under `DISCOVERY_DIR` other than
`__pycache__` (which a run does create).

---

**N4 — F-1's `_read` half is unpinned: it can be deleted silently.**
`harness/guidance.py:453` (`_read` → `inside_checkout`).

Reproducing input — in a throwaway copy, revert `_read` alone to `path = Path(guidance_dir) / rel`,
leaving `load_manifest`'s check:

```
$ python3 test/run_tests.py -k TestIssue97
NARROWED RUN: -k selected 120 of 807 tests
Ran 120 tests in 227.970s
OK                                    rc=0
```

and all three escape rows are still rc 2 through `main()` — `load_manifest` catches every one,
because every `file:` is validated at load. So the funnel is real defence-in-depth (it is what
stops a *future* caller arriving around `load_manifest`, and the comment says so), but nothing
would notice its removal. Dropping **both** is caught (2 tests red, §2.3).
**REPEAT?** No. *Fix, ~6 lines:* one direct-call test —
`self.assertRaises(guidance.GuidanceError, guidance._read, checkout, "../x.md")` — or drive
`assemble()` with a hand-built row that never went through `load_manifest`.

---

**N5 — a non-string manifest `file:` is a traceback, not the named rc 2.**
`harness/guidance.py:281-303` (`load_manifest`) with `inside_checkout`.

`missing = [f for f in ("id","heading","file") if not row.get(f)]` is a truthiness test, so
`file: 5` passes it; `inside_checkout` then evaluates `root / 5` → `TypeError: unsupported operand`,
rc 1 with a traceback, outside the rc-2 configuration contract every other malformed row gets.
Pre-existing in shape (the ref did `guidance_dir / 5` at `_read`), but F-1 moved the failure
earlier without typing the field, and the manifest is exactly the surface F-1 exists to bound.
Very low: the manifest lives in the `_agent-guidance` checkout the operator points at.
**REPEAT?** No — though it is the same *shape* as A-N1 (a present key of the wrong type reaching an
operator that assumes its type), one file over. *Fix, one line:* add
`isinstance(row["file"], str)` to the same loop and raise the existing `GuidanceError`.

### Record-only (measured, no change requested)

- **The ref leaks grandchildren; the head does not.** My hollowness splice run on `a6d165d` left
  **four** orphaned `test/fake-claude` processes alive 319–547 s after the parent returned — the
  unbounded-leg behaviour S1-a closes, observed from the outside. I killed all four; survivors 0.
  (Related to, but distinct from, the round-2/3 record-only note about `deliver()` orphaning a
  grandchild.)
- **The suite still plants `test_issue_zz_*.py` into the repo's own `test/issues/` during a run.**
  I caught one in a `cp -a` taken mid-run and had to remove it from four mutation copies. Inherent
  and already recorded; it is why "run the suite serially per checkout" is a standing instruction,
  and it is a live hazard for any reviewer copying a tree while a suite is running.
- **The S-B-a pin has two failure branches with different messages**, keyed on
  `RUNNABLE_PREFIXES = ("test", "setUp", "tearDown")`. A forking function not named that way is
  reported as an unreachable *helper* ("no flagged function in its own module calls it"), not as an
  unguarded test. Both are red; the distinction is worth knowing when reading a failure.
- **`EXTRA_PASSTHROUGH = ()` is inert against a name not in `os.environ`.** Adding
  `("NEWLY_ADDED_ALLOWLIST_NAME",)` to it does **not** turn the A6 header pin red, because
  `agent_env` only copies names that are actually set. The A6 pin does derive from the live
  `guidance.agent_env` output — mutating `agent_env` to set a new key is red — so the pin is sound;
  the extension point simply cannot be exercised that way.
- **`test_the_runner_says_what_can_and_cannot_police_its_own_exit_code`'s first assertion is a text
  `in` over the runner's source.** A comment-string pin, not a code-shape claim, so outside the
  "parse an AST, never a regex" rule; the code-shape half is parsed with `ast`.
- **A `1e400`-style knob, a `2700.5`, a `"2700"` string** and the rest of round 3's 48-row knob
  matrix were not re-run here; round-2 S1's regression was measured by the drop-the-ceiling
  mutation instead (3 red).

---

## 9. What I could not measure

- **No real dispatch.** Everything about the OIDC exchange, the WIF preflight and the real `claude`
  CLI is inference from the parsed workflow plus the validation step's `run:` block executed
  locally. The **ordering** guarantee is proven by parsed step index *and* by execution; the
  exchange step's own behaviour is not. This is also why A-N3's *actual* non-arm overhead
  (checkouts, `npm i`, `pip install`, badge push) is an estimate: I can bound what the arms may
  claim (2025 s of 2700 s) but not what the rest of the job really costs.
- **Real-model probe behaviour.** S-A's residual still depends on how often a real model answers
  with one word when two magic words are in context. I measured the harness's response to both
  arities through the production prompt; I could not measure the model.
- **The `_agent-guidance` sibling is pinned at the export in `$SP`** (28 manifest rows, 8 distinct
  files). A manifest change upstream would move the extent identity; I could not test another
  revision.
- **`test_the_fixture_match_survives_a_committed_list_far_larger_than_a_pipe` under the S5 mutation
  was 19/20 red, not 20/20** — the SIGPIPE race is size- and timing-dependent, exactly as
  `_agent-guidance`'s own guidance records. One green trial there is not evidence of a fix; nineteen
  reds are evidence of the defect.
- **Two concurrent full-suite runs in one checkout** would race over the planted probe modules. I
  ran serially per checkout throughout, and the one cross-tree race I hit (a `cp -a` during a run)
  is recorded above rather than absorbed.
