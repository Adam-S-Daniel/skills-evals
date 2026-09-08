FOUND — 0 blocker, 2 should-fix, 6 nit

# Round-4 adversarial review — `claude/skills-evals-97` @ `f9115ce`

Scope: break it, not confirm it. Every row below is a command I ran and its
output. All work under `HOME=$SP/r4adv97-home` with
`SKILLS_EVALS_USER_MEMORY=$SP/r4adv97-home/usermem.md`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=/root/.local/lib/python3.11/site-packages`.
The eight named files in `$SP/rev97d-adv` matched their stated md5s before I
started and the tree is proved byte-identical to a fresh `git archive f9115ce`
at the end.

**Headline: every item the fix brief names is genuinely closed at its own
entry point.** `--timeout` is bounded on all three CLIs and the flag still
wins over the knob when valid; a manifest `file:` can no longer escape the
checkout in any of the five shapes I could build; `.`/`..` arm names are
refused; a non-mapping `guard:`/`judge:`/`env:` is a named rc-2 error; the
dispatch gate refused 39 hostile inputs with nothing minted and nothing
echoed; the guard is two-sided in both directions; the env allowlist survives
a 95-name hostile parent at exactly 15 names.

**Two should-fix items, and both are the same shape this round exists to
catch — the fix landed where the brief pointed and the defect is standing in
the doorway beside it:**

* **S-B-a-2** — the fork pin's file set is two globs, and the surface is
  "anything importable that a discovered test can call". A forking helper at
  `test/r4forkhelper.py`, at `harness/r4harnessfork.py`, **and at
  `test/issues/r4helpers/__init__.py`** each leaves *both* new pins GREEN and
  runs away. The report's own claim that "the two pins hold each other up"
  is false at the exact seam it names, and A-N4's own failure message
  ("A helper shared between issue modules belongs somewhere that is not the
  discovery dir") points contributors straight into it.
* **S1-a-2** — the AST inventory checks that the source a table row NAMES is
  validated; it never checks that the named source is the one actually
  feeding the call. Rebinding `run_agent`'s timeout to an unvalidated fixture
  key leaves the inventory GREEN, the flag test GREEN, and all 120
  TestIssue97 tests OK, while a fixture reproduces S1 verbatim:
  `OverflowError: timeout is too large`, rc 1.

---

## FINDINGS

### S-B-a-2 (should-fix) — the fork pin's FILE SET is still narrower than the surface, and the pin it leans on does not close the gap it names

`test/run_tests.py:12213`
(`test_every_suite_forking_test_in_this_repo_stands_down_in_a_child`) walks
exactly `test/run_tests.py` + `test/issues/test_issue_*.py`. Three helper
locations defeat it, each measured in its own throwaway copy of the tree,
each with **no** `_skip_in_child()` and **no** marker read anywhere:

| helper module | fork pin | A-N4 pin | runs away? |
|---|---|---|---|
| `test/r4forkhelper.py` (imported from `test_issue_97.py`) | **GREEN** | **GREEN** | **yes — peak 3 procs at 45 s, climbing** |
| `harness/r4harnessfork.py` | **GREEN** | **GREEN** | **yes — peak 3 at 45 s** |
| `test/issues/r4helpers/__init__.py` (a PACKAGE inside the discovery dir) | **GREEN** | **GREEN** | **yes — peak 3 at 45 s** |

Baseline for comparison, same probe shape but the committed guarded test
(`test_planted_issue_module_is_discovered_and_fails_the_runner`) in a clean
copy: **peak 2, and 0 by t=45 s** — it spawns one child, the child stands
down, the tree collapses. Process counts taken by resolving `/proc/<pid>/cwd`
into my own copy, never by name; every tree killed by process-group id at its
bound, `KILLED_REMAINING=0` each time.

The helper source in all three cases is the ordinary thing a contributor
writes:

```python
def spawn_suite():
    return subprocess.run([sys.executable, str(TEST_DIR / "run_tests.py")],
                          capture_output=True, text=True, timeout=900)
```

REPEAT: **yes, third round running, and through the prescribed remedy each
time.** Round 2's S-B put the guard on one test; round 3's S-B-a found the
pin saw one spelling in one file and prescribed "walk both file sets by
`ast`"; the walk is two file sets and the surface is not two file sets.

**The report's own enumeration is what makes this a finding rather than a
residual.** `$SP/ctx/pr-138-fix3-report.md` says:

> The one gap left is a helper in a module the walk cannot parse — which is
> exactly what A-N4's new assertion (`ec6bfea`) forbids from living in
> `test/issues/` at all; the two pins hold each other up, and the docstring
> says so.

Both halves are measurably false:

* **`test/` and `harness/` are not `test/issues/`, and nothing forbids a
  helper in either.** `test/` is `sys.path[0]` for every `python3
  test/run_tests.py` run — it is the directory the runner itself lives in —
  so `import r4forkhelper` from a discovered module just works (proved by the
  runaway).
* **A-N4 does not even cover `test/issues/`.** Its assertion is
  `DISCOVERY_DIR.glob("*.py")` — `.py` *files*. A package DIRECTORY there is
  admitted, and a package is exactly what A-N4's own failure message tells
  the contributor to reach for: *"A helper shared between issue modules
  belongs somewhere that is not the discovery dir."*

Severity — should-fix, not blocker: nothing on the committed tree forks
unguarded (the flagged set is the six the report names, all guarded, verified
below), so this is a guard against future drift that has a hole where the
drift is most likely to arrive. It is not a nit because the shape is the one
a contributor would actually write and because it runs away when they do.

**Fix I would make.** Not a third enumeration. Invert it: make the ONE
spawner the only thing in the repo allowed to name the runner, and have it do
the marker check itself —

```python
def _run_suite(self, env_extra=None):
    if os.environ.get(CHILD_ENV):        # the helper stands down, not its callers
        raise unittest.SkipTest("child suite run")
    ...
```

then pin, by an `ast` walk over **every** `*.py` under `test/` and `harness/`,
that no function outside that helper names `run_tests.py` at a spawn. That is
one scan over a directory tree instead of two globs, and it does not have to
be right about where a future helper will live. If the committed shape (guard
on the tests) is kept instead, the walk must at minimum become
`(REPO_ROOT/"test").rglob("*.py")` + `(REPO_ROOT/"harness").rglob("*.py")`,
and A-N4 must assert over `DISCOVERY_DIR.iterdir()` rather than `glob("*.py")`.

**The other spellings I planted, for the record** — ten more, each unguarded
in its own copy, "runs away" measured only for the ones the pin missed:

| spelling | pin | runs away? | grade |
|---|---|---|---|
| class-level `RUNNER = TEST_DIR / "run_tests.py"` | **RED** | — | closed |
| `Path(__file__).resolve().parent.parent / "run_tests.py"` | **RED** | — | closed |
| `os.execv(sys.executable, [..., str(TEST_DIR/"run_tests.py")])` | **RED** | — | closed |
| `os.posix_spawnp(...)` | **RED** | — | closed |
| `-c "import runpy; runpy.run_path('test/run_tests.py')"` | **RED** | — | closed |
| `"run_" + "tests.py"` | GREEN | yes, peak 3 @60 s | nit (nobody concatenates a fixed filename) |
| `f"run_{stem}.py"` | GREEN | yes, peak 3 @45 s | nit |
| `TEST_DIR.glob("run_*.py")` | GREEN | yes, peak 3 @45 s | nit |
| `R4SP = subprocess; R4SP.run(...)` (module alias by assignment, not `import as`) | GREEN | yes, peak 3 @45 s | nit |
| `run_tests.main()` in-process | GREEN | **hangs — 97 nested iterations in 40 CPU-s, never returns** | nit (an obvious hang on first run, no processes) |
| `multiprocessing.Process(target=run_tests.main)` | GREEN | **yes — 55 nested processes in 40 s** | nit |
| `runpy.run_path(...)` | GREEN | no — `SystemExit(1)` propagates, one error | out of scope |
| `exec(compile(src, ...))` | GREEN | no — `NameError: name '__file__' is not defined` | out of scope |
| `python -m unittest discover -s test` | GREEN | no — `run_tests.py` does not match `test*.py` | out of scope |

**Exact-membership behaviour, as asked.** A legitimate NEW guarded forking
test → pin RED via the membership assertion, and the message is clear about
what to do:

> the set of functions that can spawn `python3 test/run_tests.py` has changed.
> Every one of them must stand down inside a child, and the list is here so
> adding one is a decision rather than an accident. Add or remove the entry —
> and if a NEW entry is a surprise, that function forks the whole suite and
> probably should not.

An ordinary new `test/issues/test_issue_zz_ordinary.py` (no forking) leaves
both pins GREEN — no false alarm. Breaking the recogniser
(`SUITE_RUNNER_NAME = "run_testsX.py"`) is RED on the vacuity floor:
`AssertionError: {} is not true : no function anywhere spawns the suite`.

**The committed flagged set**, computed with the pin's own `_SuiteForkScan`,
matches the report exactly:

```
test/run_tests.py::test_dash_k_on_the_command_line_still_reaches_the_discovered_subtree  guarded=True
test/issues/test_issue_97.py::_run_suite                                                 guarded=False
test/issues/test_issue_97.py::test_an_ordinary_run_leaves_the_watched_file_alone         guarded=True
test/issues/test_issue_97.py::test_planted_issue_module_is_discovered_and_fails_the_runner guarded=True
test/issues/test_issue_97.py::test_removing_the_planted_module_puts_the_runner_back_to_zero guarded=True
test/issues/test_issue_97.py::test_the_run_wide_user_memory_guard_fails_a_run_that_writes_the_file guarded=True
```

---

### S1-a-2 (should-fix) — the inventory checks that the NAMED source is validated, never that it is the source

`test/issues/test_issue_97.py:2101`
(`test_every_harness_subprocess_timeout_names_its_validated_source`). The
table maps `(file, function, spelling, argument-source-text) -> sources`, and
for a `knob` row it asserts the knob is in `TIMEOUT_KNOBS` and that `main()`
still calls `validate_timeouts(fixture, ...)`; for a `flag` row, that the
module's `main()` still calls `check_timeout(args.timeout, ...)`. Neither
question is "does that source actually feed this call".

**Measured.** In a throwaway copy, both `run_agent` call sites rebound to an
unvalidated fixture key — the whole edit, and it changes no inventory key
because the argument at the call site is still the local name `timeout`:

```python
-  "timeout": args.timeout or fixture.get("timeout_s", 600),
+  "timeout": args.timeout or fixture.get("agent_timeout_s", 600),
```

| check | result |
|---|---|
| `-k names_its_validated_source` | **GREEN** |
| `-k bounded_by_the_one_predicate` | **GREEN** |
| `-k TestIssue97` | **Ran 120 tests in 178.3s — OK** |
| a guidance fixture with `agent_timeout_s: 2200000`, through the real CLI | **rc 1, `OverflowError: timeout is too large`** |

That is S1 verbatim, with every gate this round added reading green.

**Two spellings the scanner cannot see at all**, each planted as a new module
under `harness/`:

| planted sink | inventory |
|---|---|
| `opts = {"timeout": args.timeout}; subprocess.run(cmd, **opts)` | **GREEN** — `**kwargs` is `keyword(arg=None)`, and the walk filters `k.arg == "timeout"` |
| `proc.wait(fixture.get("probe_timeout_s", 30))` — **positional** timeout on `Popen.wait` | **GREEN** — same keyword-only filter |
| `signal.alarm(...)` / `asyncio.wait_for(..., timeout=...)` fed by a fixture value | GREEN — not a subprocess sink; **out of scope**, the invariant says subprocess |

And three the scanner catches correctly, each RED with file and line:

| planted sink | inventory |
|---|---|
| a wrapper `def _run(cmd, timeout): subprocess.run(cmd, timeout=timeout)` | **RED** — `harness/r4wrap.py:5 in _run() — subprocess.run(timeout=timeout)` |
| `subprocess.Popen(cmd).communicate(timeout=fixture.get(...))` | **RED** — `<popen>.communicate` |
| `import subprocess as sp; sp.run(..., timeout=...)` in a NEW harness module | **RED** |

`check_timeout` itself is sound — 23 values through it: `True`/`False`,
`Decimal("600")`, `Fraction(600,1)`, a duck-typed comparable, `"600"`,
`" 600"`, `nan`, `inf`, `-inf`, `10**30`, `2**63`, `0`, `-0.0`, `-1`,
`2700.0000001`, `None`, `[600]`, `{...}` all **refused**; only a real
`int`/`float` in `(0, 2700]` accepted (a `float` subclass — the numpy-like
case — is accepted, which is correct: it IS a float).

REPEAT: **it returns through the fix brief's own prescribed remedy.** The
brief prescribed "(b) an AST inventory ... require each call site to appear in
an explicit table inside the test that names which validated source bounds
it", and the worker built exactly that. The table's site→source binding is
the part no parse checks, and the report overclaims it: *"all decided by
parsing, so the table cannot become a comment"*.

Severity — should-fix, not blocker: every S1-a row the brief lists is closed
on the committed tree (rows below), nothing is unbounded today, and the
inventory does force a table row for any new sink spelled ordinarily. It is
not a nit because reaching for a new per-fixture timeout key and wiring it
into `run_agent` is an ordinary thing to do and every gate stays green.

**Fix I would make.** Put the predicate at the SINK, not at the sources:
`guidance.check_timeout(timeout, "<where>", ...)` on entry to `run_agent`,
`run_setup`, `judge.score`, `run_canary.run_leg`, `arms._run_hook` and
`guidance.deliver`. Then "no value that reaches a subprocess timeout anywhere
under `harness/` may be non-numeric, boolean, non-positive, non-finite, or
above `MAX_TIMEOUT_S`, whatever its source" is true by construction rather
than by a table of beliefs, and the inventory becomes belt-and-braces instead
of the only rope. Keep the `**opts` and positional-`wait` blind spots in mind
for the inventory either way (`any(k.arg in (None, "timeout") ...)` and the
positional argument of `wait`/`communicate`).

---

### N1 (nit) — `_run_suite`'s SET of the child marker is unpinned, and removing it runs the fork away with the pin green

The pin asserts the helper does **not** read the marker
(`assertFalse(issue97.stands_down["_run_suite"])`), which is right — but
nothing anywhere asserts it SETS it. One-line mutation:

```python
-  env = dict(os.environ, **{CHILD_ENV: "1"}, **(env_extra or {}))
+  env = dict(os.environ, **(env_extra or {}))
```

| | result |
|---|---|
| `-k stands_down_in_a_child` | **GREEN** (`Ran 1 test in 0.735s / OK`) |
| `-k test_planted_issue_module_is_discovered_and_fails_the_runner`, 60 s bound | **peak 3 procs, still climbing** |
| the same probe on an unmutated copy | peak 2, **0 by t=45 s** |

`grep` over both files: the only readers are `test_issue_97.py:232` and
`run_tests.py:11999`; the only writers are `test_issue_97.py:220` and
`run_tests.py:12456`. Nothing asserts either write.

Severity: nit — deleting the one expression a helper exists for is a
deliberate act, not drift. **Fix:** one assertion in the pin (which already
parses the file): `_run_suite` must contain a WRITE of `SUITE_CHILD_ENV` into
the child's env.

### N2 (nit) — F-1's containment misses the two module-constant paths that do not pass through `_read`

The report's F-1 enumeration says: *"`row["file"]` is the only one.
`base.md`, `stub.md`, the manifest itself and `fleet-memory.sh` are module
constants (`BASE_REL`, `STUB_REL`, `MANIFEST_REL`, `HOOK_REL`)."* A module
constant is a NAME, not a location — and two of those four go through
`_read` (hence `inside_checkout`) while two do not. Measured on head:

| mutation of the checkout | rc | outcome |
|---|---|---|
| `agents-md/base.md` replaced by a symlink out (goes through `_read`) | **2** | refused, named — leak on `a6d165d` |
| `agents-md/eval-coverage.yml` replaced by a symlink out (`load_manifest` calls `path.read_text()` directly, :286) | **0** | **the outside file IS read as the manifest**; its ids reach stdout: `... carries it (known ids: R4ADV_OUTSIDE_MARKER_SECRET_FROM_OUTSIDE_FILE, alpha)` |
| `.claude/hooks/fleet-memory.sh` replaced by a symlink out (`deliver`, :630) | **0** | **the OUTSIDE script executed** — my wrapper wrote its marker file, then chained to the real hook, and the run finished rc 0 |

Both are identical on `a6d165d` — pre-existing, not regressions — but F-1's
stated invariant is *"the harness reads guidance content only from inside the
`_agent-guidance` checkout it was given"*, and these are the two reads that
still do not.

Severity: nit. Planting either symlink needs a commit inside the checkout,
which is the trusted side of the stated boundary, and anyone who can do that
can put hostile content in `base.md` instead; nothing lands in `results/`
(`leakfiles=0` on both). It is worth fixing because it costs two lines and
makes the enumeration true: `path = inside_checkout(guidance_dir,
MANIFEST_REL)` in `load_manifest`, and the same for `HOOK_REL` in `deliver`.

### N3 (nit) — A-N4's invariant is "every `*.py`", the sink is "everything importable"

`build_suite()` puts `test/issues/` on `sys.path` for the rest of the
process. The new assertion globs `*.py`:

| planted under `test/issues/` | A-N4 | stdlib `colorsys` after `build_suite()` |
|---|---|---|
| `colorsys/__init__.py` (a package) | **GREEN** | **shadowed** — `.../test/issues/colorsys/__init__.py` |
| `colorsys.so` (empty) | **GREEN** | **shadowed** — `ImportError: ... file too short` (the loader chose it) |
| `colorsys.pth` | GREEN | not shadowed — `.pth` is only processed in site dirs; correctly harmless |
| `colorsys.py` | RED | — |
| `colorsys.py -> /dev/null` (symlink) | RED | — |
| `__init__.py` | RED | — |
| `conftest.py` | RED | — |
| `test_issue_97.py.bak` | GREEN | not importable; correct |
| `test_issue_.py` (empty stem) | GREEN | matches the pattern and IS discovered (808) — correct |
| `sub/test_issue_x.py` | GREEN | **neither flagged nor discovered** — a failing test module that silently never runs (807, unchanged) |

The package row is what makes this matter: combined with S-B-a-2 it is a
forking helper inside the discovery dir that both pins pass.
**Fix:** assert over `DISCOVERY_DIR.iterdir()` — every entry is a file
matching `DISCOVERY_PATTERN`, or `__pycache__`.

### N4 (nit, pre-existing) — an arm name still becomes paths A-N2's property does not model

`_names_a_new_directory` models one path: the arm directory under the run
directory. The arm name also becomes the run's own sibling files, and the
workspace prefix at `run_eval.py:1130`
(`mkdtemp(prefix=f"skills-evals-{arm['name']}-")`).

| arm name | head | `a6d165d` |
|---|---|---|
| `report.md` | **rc 1, `IsADirectoryError: [Errno 21] Is a directory: .../report.md`** — the arm's `summary.json` and `transcripts/raw.json` are written first, then `_render_report` collides with the arm dir | identical |
| `a`*255, `a`*256, `a`*4096 | **rc 1, `OSError: [Errno 36] File name too long`** from the workspace `mkdtemp` | identical |
| `summary.json`, `transcripts`, `...`, `.hidden`, `-`, `a.`, `none`, `None`, `CON`, `NUL` | rc 0, harmless (per-arm files, no collision) | identical |
| `.`, `..` | **rc 2 named, nothing written** | rc 0, wrote above/into the run dir |
| NFC `éarm` / NFD `éarm` | rc 2 named — the ASCII class refuses both, so no normalisation collision is possible | identical |
| `--results-dir` as an arm name | rc 2 — argparse eats it (`--arm: expected one argument`) | identical |

Severity: nit, pre-existing, and it needs a maintainer to write an absurd arm
name into a committed fixture. Worth one clause: cap the length and refuse a
name equal to `report.md`.

### N5 (nit) — the fit test's coupling to the harness key is a literal, not a parse

A-N3 says *"use the key the harness reads"*, and `_guidance_fixture_budget`
hardcodes `fixture.get("judge_rubric")`. `test_the_guidance_budget_counts_every_per_arm_cost`
parses `_run_guidance_arm` for the `setup_timeout_s` claim but not for this
one. In a throwaway copy, one harness edit plus a committed five-arm fixture:

```python
-  if not args.no_judge and fixture.get("judge_rubric"):
+  if not args.no_judge and fixture.get("judge_prompt", fixture.get("judge_rubric")):
```
```yaml
# evals/guidance/_zz_probe/fixture.yaml — 5 arms, judge: {timeout_s: 2700}, judge_prompt: score it
```
```
-k fits_inside_the_workflow_job_timeout   ->  Ran 1 test in 0.100s  OK
-k counts_every_per_arm_cost              ->  Ran 1 test in 0.009s  OK
budget counted:   5 x 360 = 1800 s        (threshold 2025 s)
real worst case:  5 x 3060 = 15300 s      (job 2700 s)
```

The A-N3 defect, verbatim, one key-spelling over. Severity: nit — no
committed fixture declares a rubric, and adding a second accepted spelling is
unlikely. **Fix:** read the branch key out of `_run_guidance_arm` by `ast`,
the way the `setup_timeout_s` claim already is.

**The threshold, derived independently as asked:** `eval.yml` `jobs.eval.timeout-minutes: 45`
→ 2700 s; the test's line is `job_budget_s * 0.75` = **2025 s**.
`evals/guidance/_delivery` declares `timeout_s: 120`, `guard.timeout_s: 120`,
no `judge:`, no `judge_rubric:`, 5 arms → 5 × (120 deliver + 120 agent + 120
guard + 0 judge) = **1800 s**. 225 s of headroom against the test's own line —
but **900 s against the real 2700 s job**, which is the number that matters,
and 5 checkouts + `npm i -g` + pip + the OIDC/WIF exchange + the badge push do
not plausibly reach 900 s. The headroom is fine; the 0.75 factor is the
conservative part, not the tight part. `guidance-bridge-canary` is a *skill*
fixture (no `subject:`), so exactly one guidance fixture is checked and
`checked > 0` holds.

### N6 (nit, all pre-existing) — three shapes still leave the rc-2 contract by traceback

| input | head | `a6d165d` |
|---|---|---|
| manifest row `file: 5` | rc 1, `TypeError: unsupported operand type(s) for /: 'PosixPath' and 'int'` — **raised inside the new `inside_checkout`** | identical |
| manifest row `file: ["agents-md/base.md"]` | rc 1, same `TypeError` with `'list'` | identical |
| a fixture whose ROOT is a list | rc 1, `AttributeError: 'list' object has no attribute 'get'` (`run_eval.py:1531`) | identical |
| an EMPTY fixture file (YAML `None`) | rc 1, **`TypeError: argument of type 'NoneType' is not iterable` at `run_eval.py:88`, inside A-N1's own new `_require_mapping`** | rc 1, one line later in `fixture.get("subject")` |
| `env: {"A=B": x}` | rc 1, `ValueError: illegal environment variable name` from `subprocess` | identical |

A-N1's invariant is about mapping-typed KEYS; the container that holds them,
and the values inside `env:`, are the same defect one level out and one level
in. All trusted-fixture-only, none reachable from a dispatch. **Fix:** one
`isinstance(fixture, dict)` at `load_fixture`, one `isinstance(row["file"],
str)` in the manifest loader, and a name/value check on `env:` entries.

A-N1's own rows are all correct: `guard: {}` rc 0; `guard: {timeout_s: {}}`,
`{timeout_s: [1]}`, `guard: 7`, `guard: true`, `guard: 7.5`,
`judge: {timeout_s: 'x'}` all **rc 2 named, no traceback, 0 files written**; a
YAML anchor making `guard` and `judge` the same object, and a merge key, both
accepted (they are mappings); a duplicate `guard:` key is YAML last-wins and
the **last** one is the one validated (rc 2 when it is 99999); arm-level
`guard:`/`timeout_s:` are refused by name (`arm 'a' has unknown key(s)
['guard']`), so no arm-level knob reaches anything unvalidated.

---

## HELD UP UNDER ATTACK

### The timeout ceiling, harness-wide (S1-a)
Through the real CLI entry points, `evals/workflow-path-audit` and a
scratch guidance fixture:

| `--timeout` | `run_eval.py` | `run_canary.py` | `run_propagation.py` |
|---|---|---|---|
| `2200000` | **2** named | **2** named | **2** named |
| `1000000000` | **2** named | — | — |
| `2701` | **2** named | **2** named | **2** named |
| `0` | **2** named | **2** named | **2** named |
| `-1` | **2** named | **2** named | **2** named |
| `600` / `2700` / `60` / `120` | 0 / 0 / (runs) / (runs) | | |

`10**30`, `2700.5`, `nan`, `inf`, `1e3`, `0x10`, `True`, `""` are refused by
argparse's own `type=int` (rc 2, usage). `00600`, `+600`, `" 600"`, `1_000`
are valid ints to argparse and then valid to `check_timeout` — correct.
The message names the flag and the ceiling:

> ``configuration error: `--timeout` must be a positive number of seconds no greater than 2700 (eval.yml gives the eval job that many), got 2701.``

**Flag vs knob — which wins, and is the winner the validated one?** With a CLI
that answers the guard honestly and then never returns on the scored leg:

| | rc | elapsed |
|---|---|---|
| `timeout_s: 8`, no flag | 2 | **8 s** |
| `timeout_s: 2700` + `--timeout 6` | 2 | **6 s** — the flag wins |
| `timeout_s: 6` + `--timeout 12` | 2 | **13 s** — the flag wins |
| `timeout_s: 6` + `--timeout 3000` | **2, in 0 s** | refused at parse — round 3's no-return row, closed |

**Mutation — drop the `--timeout` predicate from `run_eval.main()`:** BOTH
catch it, as the report claims. The row test is red —
`AssertionError: True is not false : --timeout 2200000: the CLI was invoked
before the flag was checked` — and the inventory is red naming the site:

> `AssertionError: False is not true : harness/run_eval.py run_agent() subprocess.run(timeout=timeout): is fed by harness/run_eval.py's --timeout, and that module's main() no longer runs guidance.check_timeout on args.timeout — the flag reaches subprocess.run unbounded, which is the S1-a defect returning`

### Containment (F-1) — every `file:` escape shape I could build, closed
Same probe on both trees (`canary_loader`, which echoes its loaded memory, so
outside content would land in the transcript):

| manifest row | `a6d165d` | `f9115ce` |
|---|---|---|
| `file: ../OUTSIDE.md` | rc 0, **leaked into `.../a/transcripts/raw.json` and `summary.json`** | **rc 2 named, leak=[]** |
| `file: /abs/path/OUTSIDE.md` | rc 0, **leaked** | **rc 2 named, leak=[]** |
| in-tree symlink CHAIN (link1 → link2 → outside) | rc 0, **leaked** | **rc 2 named, leak=[]** |
| symlinked DIRECTORY `agents-md/linkdir -> /outside`, `file: agents-md/linkdir/x.md` | rc 0, **leaked** | **rc 2 named, leak=[]** |
| `agents-md/base.md` itself a symlink out | rc 0, **leaked** | **rc 2 named, leak=[]** |
| `/proc/self/environ` via an in-tree symlink | rc 2 | **rc 2 named** |
| `file: agents-md/../agents-md/base.md` (inside after normalisation) | rc 0 | **rc 0 — accepted, correct** |
| `file: agents-md/sections` (a directory) | — | rc 2, `could not read ...` |

**The refusal message cannot be made to leak the runner's environment.**
`inside_checkout` does no `expanduser` and no `$VAR` expansion: `~/secret.md`,
`$HOME/secret.md` and `${HOME}/x.md` are all resolved *literally* under the
checkout (accepted as ordinary in-tree names), and the refusal text for `../x`
and `/etc/passwd` contains the manifest's own string plus the checkout root
and nothing else — `$HOME` appears in neither.

**`--guidance` itself:** a symlink to the checkout → rc 0 (both sides
`.resolve()`d); a path containing `..` → rc 0; a trailing slash → rc 0; a
FILE → rc 2 named; nonexistent → rc 2 named; `/` → rc 2 naming the missing
manifest. `--guidance ""` falls back to `$AGENT_GUIDANCE_DIR`/the sibling
because `resolve_guidance_dir` tests truthiness — an explicitly-passed empty
flag is silently ignored rather than refused. Pre-existing, harmless, noted.

**Size:** a 50 MB in-tree section file is read and delivered at rc 0 in **102 s**
on head and **110 s** on `a6d165d` — a slow markdown parse of a trusted
in-tree file, not a hang and not a regression. Recorded.

**Mutation — drop the containment comparison:** `-k manifest_file` RED
(`AssertionError: 0 != 2`) on both escape rows.

### The dispatch gate — 39 hostile inputs, executed
The step's own `run:` block, extracted with `yaml.safe_load` from
`.github/workflows/eval.yml` and run under `bash` against a synthetic
`$GITHUB_EVENT_PATH` written as raw bytes and a synthetic `evals/` tree built
from the committed fixture list. `$RUNNER_TEMP` inspected after every row.

**Nothing happens before a rejection:** every rejecting row left `$RUNNER_TEMP`
**empty**; every accepting row left exactly `['eval-fixture', 'eval-key']`.
**No row echoed the value** — a `R4ADVGATE` marker present nowhere in the tree
never appeared in any output, including a 100 KB charset-clean non-fixture.

| class | rows | result |
|---|---|---|
| committed (default, `writing-adrs/bootstrap`, `guidance/_delivery`) | 3 | rc 0, both temp files |
| NUL leading / trailing / embedded / alone / doubled | 5 | rc 1, `contains a NUL byte` |
| a RAW NUL byte inside the JSON | 1 | rc 5, `jq: parse error` — closed before anything |
| shape (`*`, `evals/*`, spaces, `$(id)`, backticks, `;`, tab, CRLF, multi-line ×2, an object input) | 11 | rc 1, charset branch, **before** any matching |
| traversal / near-misses (`..`, `/etc/passwd`, `./evals/…`, `evals//…`, trailing slash, bare `evals`, `…/fixture.yaml`) | 7 | rc 1, `names no committed fixture` |
| non-strings (`5`, `true`) | 2 | rc 1, `names no committed fixture`, value not in the message |
| `false`, `null` inputs, absent `inputs`, empty event file, empty string | 5 | rc 0, the default |
| `inputs` an array, malformed JSON | 2 | rc 5 under `set -e`, fails closed |
| a symlinked directory under `evals/` | 1 | rc 1 — `find -P` does not descend it |
| a 100 KB marker payload | 1 | rc 1, marker absent from the log |

**Step order proved from the parsed YAML:** step 9 *Select and validate the
fixture to run* precedes step 10 *Mint OIDC token and exchange for Anthropic
access token* and step 11 *WIF auth preflight*.

### The workflow files (byte-unchanged since round 3, confirmed)
`git diff a6d165d..f9115ce -- .github/ evals/` = **0 bytes**.
`.github/workflows/eval.yml` md5 `5e2ccf934b89a62d7b8dcc8749f19c75`.
Parsed all six workflows: **26 `run:` blocks, 0 containing `${{`**; **25
`uses:` refs, every one a bare 40-hex SHA** except
`Adam-S-Daniel/cms-platform/.github/workflows/scheduled-run-health.yml@v0.1.87`
(the fleet's documented carve-out); **zero `uses:` lines carry a trailing
comment**. `eval.yml` triggers exactly `{schedule, workflow_dispatch}`;
`permissions {contents: write, id-token: write}` and `concurrency {group:
real-eval, cancel-in-progress: false}` are **identical to main `7c966ba`**;
one job, `timeout-minutes: 45`. All five `eval.yml` checkouts and all three
`ci.yml` checkouts carry `persist-credentials: false`. `GITHUB_TOKEN` appears
in step 13 only. **`ci.yml` — the `pull_request` publisher of the required
context — has no `concurrency` at all**, at workflow or job level, and neither
does any `eval.yml` job.

### The guard, both directions
Driven through `run_eval.main()` with pinned tokens and a forging CLI whose
reply I control:

| forged reply | arms | rc | outcome |
|---|---|---|---|
| `$MAGIC` only | treat + control | **2** | treatment scores; **control `guard_contaminated`, not scored** |
| `$MAGIC $DECOY` | treat + control | **2** | **both `guard_contaminated`**, neither scored |
| `$DECOY` only | treat + control | **2** | **treatment `guard_contaminated`** — the quiet direction |
| `NO-MAGIC-WORD` / empty | treat + control | 2 | `guard_miss` on both |
| decoy1 | two `none` arms | 2 | ctrl_a scores; **ctrl_b contaminated** |
| decoy2 | two `none` arms | 2 | **ctrl_a contaminated**; ctrl_b scores |
| both decoys | two `none` arms | 2 | **both contaminated** |
| `$MAGIC $DECOY` | five-arm canary shape | 2 | **all five contaminated**, none scored |
| honest probe, real hook | treat + control | **0** | both arms score |

Every failure is INCONCLUSIVE, rc 2, `objective_checks` absent on the bad arm;
the clean partner of a contaminated pair still gets its own `summary.json`
with checks — the recorded record-only item, unchanged.

### Delivery and the env allowlist
Sabotaged `.claude/hooks/fleet-memory.sh`, `guard.timeout_s: 5`, CLI calls
counted from `$FAKE_CLAUDE_ARGV_LOG`:

| hook | rc | elapsed | error | CLI calls |
|---|---|---|---|---|
| exits 3, writes nothing | **2** | 0 s | `delivery_failed` | **0** |
| exits 0, prints `fleet-guidance: current`, writes nothing | **2** | 0 s | `delivery_failed` | **0** |
| exits 0, writes an UNMARKED file | **2** | 0 s | `delivery_failed` | **0** |
| `sleep 900` | **2** | **120 s** | `could not run ...` | 0 |

The 120 s bound is `deliver()`'s own, not `guard.timeout_s: 5`, and it
orphaned a `sleep 900` grandchild — I found it (`etimes=162`) and killed it.
Both are the recorded round-2/round-3 items, unchanged.

`guidance.agent_env` against a **95-name hostile parent** (GitHub/Actions
tokens, AWS/Azure/GCP, SSH/GPG/netrc/vault/kube, `LD_PRELOAD`, `LD_AUDIT`,
`NODE_OPTIONS`, `BASH_ENV`, `ENV`, `PYTHONSTARTUP`, proxies, `CLAUDE_*`,
`SKILLS_EVALS_*`, `FLEET_GUIDANCE_*`, 18 filler names):

* **exactly 15 names** reach a guidance arm — `PATH LANG LC_ALL SHELL USER
  NODE_PATH` + `HOME TMPDIR CLAUDE_CONFIG_DIR WORKSPACE` (all scratch) + the
  five `ANTHROPIC_*`. **Zero** non-allowlisted hostile names.
* `PASSTHROUGH` is the exact six-tuple; `EXTRA_PASSTHROUGH` is `()`.
* Fixture `env:` — `HOME`, `TMPDIR`, `CLAUDE_CONFIG_DIR` **refused by name**;
  `PATH`, `PYTHONPATH`, `LD_PRELOAD`, `NODE_OPTIONS`, `BASH_ENV`, `ENV`,
  `PYTHONSTARTUP`, `XDG_CONFIG_HOME`, `CLAUDE_BIN`, `FLEET_GUIDANCE_SKIP`,
  `SKILLS_EVALS_USER_MEMORY`, `WORKSPACE` pass through — a code-execution
  surface for a *trusted* fixture, identical to main's skill path, and
  `deliver()` builds the hook's environment from scratch so none of them can
  re-point delivery.

### The runner (S2 / S3 / N5 / N6 / N7)
* `-k NoSuchThingAtAll` → **rc 2**, `FAILED: -k 'NoSuchThingAtAll' selected 0
  of 807 tests. A pattern that matches nothing is a typo, not a clean run`.
* **Targeted runs are guarded** — `python3 test/run_tests.py R4MemProbe.<t>`
  against a probe class injected above the `__main__` guard:

  | mechanism | rc | watched file after |
  |---|---|---|
  | direct write | **1** | changed |
  | replace with a symlink to other content | **1** | changed |
  | rename away | **1** | absent |
  | replace via a new parent directory | **1** | changed |
  | write-then-restore | 0 | unchanged — the documented residual |
  | touches nothing | 0 | unchanged |

* **N6** — a planted `test/issues/test_issue_zz_r4empty.py` containing only
  `VALUE = 1` fails `test_build_suite_covers_every_discoverable_issue_module`
  by name; a module that raises on import becomes a synthetic failing test
  (`RuntimeError: R4 import boom`).
* **Nothing is left behind.** `test/issues/` in the copy that ran the full
  807-test suite holds `test_issue_97.py` and nothing else — not even
  `__pycache__` (I ran with `PYTHONDONTWRITEBYTECODE=1`).

### The prescribed mutations, all red
| mutation | test | result |
|---|---|---|
| drop the `--timeout` predicate | `cli_timeout_override` | **RED** — `True is not false : --timeout 2200000: the CLI was invoked before the flag was checked` |
| drop the `--timeout` predicate | the AST inventory | **RED** — names `run_agent()` and "the S1-a defect returning" |
| break the fork recogniser (`SUITE_RUNNER_NAME`) | `stands_down_in_a_child` | **RED** — `{} is not true : no function anywhere spawns the suite` |
| a legitimate new guarded forking test | `stands_down_in_a_child` | **RED** on exact membership, message says to add the entry |
| drop the containment comparison | `manifest_file…` | **RED** — `0 != 2` |
| restore `node = {}` in the parent walk | `non_mapping_parent` | **RED** — `GuidanceError not raised` |
| drop `_names_a_new_directory` | `arm_name` | **RED** — `0 != 2` |
| `**/fixture.yaml` → `*/fixture.yaml` | `resolves_its_registry` | **RED** — the two `writing-adrs` dirs are the difference |
| strip `no token of its own` from README | `residual_paragraphs_name_both_reasons` | **RED** — `README.md does not carry 'no token of its own'` |
| plant `test/issues/colorsys.py` | `discovery_dir_is_a_test_module` | **RED** — `Lists differ: ['colorsys.py'] != []` |

---

## VERIFIER TABLE

Run on `f9115ce` in a fresh copy of the read-only export, throwaway `HOME`
and `SKILLS_EVALS_USER_MEMORY`, siblings `_agent-guidance` and `agentskills`
present, `markdown-it-py` 4.2.0 on `PYTHONPATH`. Serial per checkout.

| verifier | expected | measured | rc |
|---|---|---|---|
| `python3 test/run_tests.py` | 807, 2 skipped, exit 0 | **Ran 807 tests in 207.1s — OK (skipped=2)** | **0** |
| `python3 test/run_tests.py -k TestIssue97` | 120 of 807 | **`NARROWED RUN: -k selected 120 of 807`**, Ran 120 in 193.4s, OK | **0** |
| `python3 test/test_propagation.py` | 164, 1 skipped | **Ran 164 tests in 4.7s — OK (skipped=1)** | **0** |
| `python3 test/run_tests.py -k NoSuchThingAtAll` | rc 2, named | **`FAILED: -k … selected 0 of 807 tests`** | **2** |
| Rule 19: every skill fixture vs `$SP/mainx5` under `--arm objective-only` | identical per check | **11 of 11 identical** by (rc, per-check `(id, passed)`) | matched |
| `evals/guidance/_delivery --arm objective-only` | rc 2 (N-f) | rc 2 | **2** |
| `git diff a6d165d..f9115ce -- .github/ evals/` | empty | **0 bytes** | — |
| `git diff --stat origin/main..f9115ce -- .github/` | ci.yml + eval.yml only | **exactly those two** (+16 / +195) | — |
| `git merge-base --is-ancestor 7c966ba f9115ce` | true | **true** | 0 |
| `git merge-tree --write-tree origin/main f9115ce` | clean | **clean**, tree `41edff2b8373a5e92d265b461218f308802dc041` | **0** |
| `git log --format='%ae %ce' a6d165d..f9115ce` | all noreply | **one identity: `4205216+Adam-S-Daniel@users.noreply.github.com`** | — |
| eleven commits, one per item | `dcd23d2 8350a36 a2c5b3c f46bbd0 9fc2e2a 26fd51a d7bda1f 53ca857 91f074c ec6bfea f9115ce` | present, in that order | — |

Rule 19 detail (rc main/head, check count): `disarm-inherited-reach` 1/1, 9 ·
`github-actions-sha-pinning` 1/1, 10 · `guidance-bridge-canary` 2/2, 0 ·
`post-failure-comment` 1/1, 12 · `propagation` 2/2, 0 · `rename-pdfs` 1/1, 8 ·
`review-bash-ci-reliability` 1/1, 11 · `windows-elevation-from-wsl` 1/1, 7 ·
`workflow-path-audit` 1/1, 8 · `writing-adrs/bootstrap` 1/1, 9 ·
`writing-adrs/existing-convention` 1/1, 7. Nine of the eleven are **byte-identical
stdout**; the two that differ (`guidance-bridge-canary`, `propagation`) differ
in exactly one line and only in the checkout root inside the path — same as
round 3. `guidance/_delivery` is head-only, rc 2.

---

## TREE INTEGRITY AND SAFETY LEDGER

| item | start | end |
|---|---|---|
| `md5sum /root/.claude/CLAUDE.md` | **`935c291f2efb1ff55a463bccfde55e6a`** | **`935c291f2efb1ff55a463bccfde55e6a`** (56 099 B) — **unchanged** |
| `$SP/rev97d-adv/harness/guidance.py` | `48cd216b76a40a95528fb36419fb2ed5` | same |
| `$SP/rev97d-adv/harness/run_eval.py` | `5013e085026480ccb0cd8c4dac233703` | same |
| `$SP/rev97d-adv/harness/run_canary.py` | `d673dc1030980e0fe018f938631ba8eb` | same |
| `$SP/rev97d-adv/harness/run_propagation.py` | `27ba4764d7a36b723ab07548b6b69b3e` | same |
| `$SP/rev97d-adv/test/run_tests.py` | `adafa45930148ba2aa23ca75eb4ce6da` | same |
| `$SP/rev97d-adv/test/issues/test_issue_97.py` | `266a4431b4926d1a6703251229623b0a` | same |
| `$SP/rev97d-adv/.github/workflows/eval.yml` | `5e2ccf934b89a62d7b8dcc8749f19c75` | same |
| `$SP/rev97d-adv/test/fake-claude` | `6863402fa23ca1b69f6340f817734b3f` | same |
| `$SP/rev97d-adv` vs a fresh `git archive f9115ce` | — | **`diff -rq` clean, exit 0 — byte-identical.** No `results/`, no `__pycache__`, no probe module |
| `$SP/rev97d-adv/test/issues/` | `test_issue_97.py` only | **`test_issue_97.py` only** |
| a working copy's `test/issues/` after a full 807-test run | `test_issue_97.py` | **`test_issue_97.py` only** — not even `__pycache__` |
| `/home/user/skills-evals` | clean, HEAD `527c729` | `git status --porcelain` empty, HEAD `527c729` — read-only git only |
| `$SP/rev97d-ref`, `$SP/mainx5`, `$SP/_agent-guidance`, `$SP/agentskills` | — | untouched (read only; `_agent-guidance` and `agentskills` were COPIED into my scratch to serve as siblings, never written) |
| my scratch `$SP/r4adv97-work`, `$SP/r4adv97-home` | — | **deleted** |
| my `/tmp` leftovers (`r4msg-*`, `r4env-*`, `r4guard*`, `gate-*`, `r19-*`, `r19b-*`, `r4adv97-hookmarker.txt`) | — | **removed, 0 remain.** The 92 `/tmp/r4d-*` directories are dated Sep 5, before my first command, and belong to another session — left alone |
| background processes I started | — | **0 remain**, counted by resolving `/proc/<pid>/cwd` into my own copy. Every fork tree killed by process-group id at its bound; one orphaned `sleep 900` grandchild from the hanging-hook probe was found and killed |
| network / GitHub writes / real `claude` / real `gh` / sessions, routines, reminders | — | **none**; nothing read under `~/.claude` beyond the two md5s |

---

## WHAT I COULD NOT MEASURE

* **Whether a real `claude` CLI honours `CLAUDE_CONFIG_DIR` for user memory** —
  the whole `--delivery user` premise. Everything above ran against
  `test/fake-claude` and two CLIs I wrote. Unchanged from rounds 1–3.
* **The real dispatch** — the OIDC/WIF exchange, the `eval-results` push, and
  therefore whether a five-arm guidance run really fits 45 minutes in
  wall-clock. The arithmetic is pinned (with N5's key-coupling gap); the clock
  is not.
* **How far the S-B-a-2 fork trees would climb**, and how deep the in-process
  and `multiprocessing` recursions go before they die. I bounded every one at
  40–60 s / 3 GB / 40 CPU-s in a shared container and killed by process group,
  so "peak 3 and climbing" and "97 nested iterations in 40 CPU-s" are floors,
  not limits.
* **`markdown-it-py`'s publish date** against the 7-day cooling-off (offline).
* **Other sessions' trees** (`$SP/rev97d-code`, `$SP/r4mut97-*`, `$SP/se-*`,
  `$SP/r4d-*`) — out of scope by rule. Several were running concurrently; my
  process accounting resolved `/proc/<pid>/cwd` precisely so as not to count
  or kill theirs.

---

## RECOMMENDATION

**Mergeable with two follow-ups, or one more fix pass — the orchestrator's
call, and the budget argues for follow-ups.** Nothing I found mints or exports
before a rejection, lets a contaminated arm score, lets a hostile env,
manifest or fixture reach the operator's files or publish a file from outside
the checkout, or hangs on the committed surface. F-1 is a real closure: five
distinct escape shapes that leaked into `transcripts/raw.json` on `a6d165d`
are rc-2 refusals here. The `--timeout` ceiling now holds on three entry
points with the flag still winning when valid. The dispatch gate, the
two-sided guard, the delivery refusal, the env allowlist and the user-memory
guard survived everything.

Both should-fix items are guards-against-future-drift with holes, not live
defects — and both have the same underlying cause, which is worth saying
plainly because it is now the third round in a row it has produced a finding:
**each remedy enumerates the sources it can think of instead of checking the
sink.** The timeout invariant is enforced by a table of beliefs about where
values come from rather than by a predicate at the six functions that call
`subprocess.run(timeout=...)`; the fork invariant is enforced by two file
globs rather than by a scan of the trees a discovered test can import from.
Each has a version that is true by construction and is not much more code.
Whatever this round decides, that is the sentence I would put in the next
brief.
