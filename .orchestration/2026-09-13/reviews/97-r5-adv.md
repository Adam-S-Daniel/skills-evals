FOUND — 0 blocker, 1 should-fix, 4 nit

# Round-5 adversarial review (one-way-door) — `claude/skills-evals-97` @ `3c558a5b0ee60f21567e403fd34ab17a3e2c50e8`

Scope: break it. Every row below is a command I ran and its output. All work
under `HOME=$SP/r5adv97-home`, `SKILLS_EVALS_USER_MEMORY=$SP/r5adv97-home/usermem.md`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=/root/.local/lib/python3.11/site-packages`.
The nine named files in `$SP/rev97e-adv` matched their stated md5s before my
first command and after my last, and the tree is proved byte-identical to a
fresh `git archive 3c558a5` at the end.

**Headline. Fix round 4 did what the brief asked almost everywhere, and the
sink discipline is real:** the timeout predicate at the sink refuses a source
no report has ever named (the process environment) with rc 2 and zero CLI
calls; `**opts` splats, positional `wait`/`communicate`, aliased `subprocess`
imports and a sink that checks one expression while handing over another are
all RED; `inside_checkout` is genuinely the only way `guidance.py` turns the
checkout into a path and every escape shape I could build is a named rc-2
refusal; the discovery dir is checked by `iterdir()` and a package, an `.so`, a
subdirectory, a symlinked dir and a FIFO are all RED; the arm-name gate, the
fixture-container and `env:` checks, the two-sided guard, the delivery refusal
and the 41-input dispatch gate all held; the rewritten `eval.yml` security
header is accurate in **every** particular I could mechanically check.

**One should-fix, and it is the same item for the fourth round running,
through the fourth version of its own remedy.** `SUITE_SCAN_DIRS = ("test",
"harness")` names the trees "a discovered test can import from" — and
`run_tests.py` itself puts a **third** one on `sys.path`, four lines below the
second, at line 57: `sys.path.insert(0, str(REPO_ROOT / "scripts"))`. A
forking helper at `scripts/r5fork.py` leaves both pins GREEN and runs the tree
to **85 processes at 45 s, still climbing**. A-N4's own new failure message
points a contributor straight at it, in the sentence written this round to
close round 4's version of exactly that mistake.

---

## FINDINGS

### S-B-a-3 (should-fix) — the scan walks two of the three importable trees, and the third is the one `run_tests.py` adds itself

`test/run_tests.py:20672` (`SUITE_SCAN_DIRS = ("test", "harness")`), whose
comment reads:

> The trees a discovered test can import from. `test/` is `sys.path[0]` for
> every `python3 test/run_tests.py` run — it is the directory the runner
> itself lives in — and `harness/` is on `sys.path` from the moment
> run_tests.py inserts it.

Measured, `run_tests.py` inserts **three** directories, not two:

```
53: sys.path.insert(0, str(HARNESS_DIR))
57: sys.path.insert(0, str(REPO_ROOT / "scripts"))     # then: import make_badge
```

`scripts/` is not a hypothetical location: it is a tracked directory holding
`scripts/make_badge.py`, the runner imports it, and **this PR modifies it**
(`git diff --stat origin/main..3c558a5 -- scripts/` = `scripts/make_badge.py |
58 ++++-`). It is the obvious third home for a shared helper, and it is
unscanned.

**Reproducing input.** In a throwaway copy of the committed tree, the ordinary
thing a contributor writes, with **no** `_skip_in_child()` and **no** marker
read anywhere:

```python
# scripts/r5fork.py
import subprocess, sys
from pathlib import Path
TEST_DIR = Path(__file__).resolve().parent.parent / "test"

def spawn_suite():
    return subprocess.run([sys.executable, str(TEST_DIR / "run_tests.py")],
                          capture_output=True, text=True, timeout=900)
```

plus, in `test/issues/test_issue_97.py`, `import r5fork` and a test that calls
it.

| check | result |
|---|---|
| `-k test_every_suite_forking_test_in_this_repo_stands_down_in_a_child` | **Ran 1 test in 2.554s — OK** |
| `-k test_every_entry_in_the_discovery_dir_is_a_test_module` | **Ran 1 test in 0.000s — OK** |
| runaway probe, own process group, 45 s bound, counted by `/proc/<pid>/cwd` | **PEAK=85, FINAL_AT_45s=87, still climbing** |
| the same probe on the committed tree | **PEAK=2, 0 growth** |

(The 85-process figure is with the helper's spawn narrowed by `-k` so the
recursion is visible inside the bound; the unnarrowed helper recurses at one
level per full suite run and was at PEAK=2 at 45 s only because a level takes
~14 minutes. The unguarded recursion is the same in both.)

**The remedy's own message points here.** A-N4's rewritten failure text, added
this round, ends:

> Shared helpers belong outside the discovery dir; wherever they go,
> `test_every_suite_forking_test_in_this_repo_stands_down_in_a_child` scans the
> whole of test/ and harness/ and will still see one that forks the suite.

"Wherever they go" is false for `scripts/`, which is the one place outside
`test/` and `harness/` that the runner makes importable. Round 4's finding was
that A-N4's message sent a contributor to an unscanned location; the message
was rewritten and still does.

**Everything else in S-B-a-2 is closed** — measured, each in its own throwaway
copy, each with the pin run afterwards:

| planted forking helper | pin |
|---|---|
| `test/r5h.py` (round 4's row) | **RED** |
| `harness/r5h.py` (round 4's row) | **RED** |
| `test/issues/r5pkg/__init__.py` (round 4's package row) | **RED** |
| `Path(...).with_name("run_tests.py")` | **RED** |
| `R5SP = subprocess; R5SP.run(...)` (round-4 nit) | **RED** — closed |
| **`scripts/r5h.py`** | **GREEN — runs away** |
| `"run_" + "tests.py"` (round-4 nit) | GREEN — unchanged nit |
| `f"run_{STEM}.py"` (round-4 nit) | GREEN — unchanged nit |
| `TEST_DIR.glob("run_*.py")` (round-4 nit) | GREEN — unchanged nit |

and the spawner-membership rows all behave exactly as the brief prescribed:

| mutation | pin |
|---|---|
| delete the marker **SET** from `_run_suite` (round-4 N1) | **RED** |
| delete the **stand-down** from `_run_suite` | **RED** |
| a new forking test routed **through** `_run_suite` | **OK** — no guard, no table entry needed |
| a new test spawning the runner **directly** | **RED** |
| break the recogniser (`SUITE_RUNNER_NAME = "run_testsX.py"`) | **RED** (vacuity floor) |
| committed tree | **OK**, spawner set exactly `{test/issues/test_issue_97.py::_run_suite, test/run_tests.py::_spawn_suite}` |

**Severity — should-fix, not blocker.** Nothing on the committed tree forks
unguarded; this is a guard against future drift with a hole where the drift is
most likely to arrive, and the brief's own rule ("a spelling a contributor
WOULD write that runs away … is a should-fix") is the grade.

**Fix I would make — one line, and it stops being a list anybody maintains.**
Derive the scan set from the runner's own `sys.path` inserts rather than from a
tuple beside them: parse `run_tests.py` for its `sys.path.insert(...)` calls
and scan every repo-relative directory they name (plus `test/`, which is
`sys.path[0]` by construction), then assert the derived set is non-empty. That
is the same move the fix already made twice — from a file glob to a directory
walk, now from a hand-written directory list to the list the code itself
declares. A one-line stopgap (`SUITE_SCAN_DIRS = ("test", "harness",
"scripts")`) closes today's hole but is the third hand-maintained enumeration
in three rounds. Correct A-N4's failure message in the same commit.

**REPEAT determination: YES — same defect, same severity, same fix, fourth
round running, and returning through the brief's own prescribed remedy.**
Round 2 guarded one test; round 3 pinned two file globs; round 4 prescribed "a
scan of the trees a discovered test can import from" and got two of three
trees. The brief's rule for this round was "the scan walks the whole directory
tree rather than a file pattern" — the scan does walk whole trees, and the
enumeration simply moved up one level, from *which files* to *which trees*.

---

### N1 (nit) — the sink pin does not require the checked expression to still be the value at the spawn

`test/issues/test_issue_97.py::test_every_subprocess_timeout_sink_checks_the_value_before_it_spawns`
compares the SET of expressions handed to `timeout=` against the SET checked,
and requires `first_check < first_spawn` by statement index. Neither claim
survives a statement placed **between** the two.

**Reproducing input** — one line added to `run_agent`, immediately after the
check whose comment says the predicate sits here:

```python
    guidance.check_timeout(timeout, "run_eval.run_agent(timeout=)",
                           guidance.SINK_TIMEOUT_REMEDY)
+   timeout = int(os.environ.get("SKILLS_EVALS_AGENT_TIMEOUT_S", timeout))
```

| check | result |
|---|---|
| `-k ..._sink_checks_the_value_before_it_spawns` | **OK** |
| `-k ..._names_its_validated_source` | **OK** |
| `-k ..._flag_is_bounded_by_the_one_predicate` | **OK** |
| `run_eval.py` on a guidance fixture with `SKILLS_EVALS_AGENT_TIMEOUT_S=2200000` | **rc 1, `OverflowError: timeout is too large`, traceback, 1 CLI call already spent** |

The conditional variant is the same shape and also green on all three pins:
`if timeout is not None: guidance.check_timeout(...)` → sink pin **OK**,
inventory **OK**.

Both are bounded when the new sink lives in a NEW module (the inventory demands
a table row and is RED — measured, 5/5 planted new sinks RED on both pins);
they are unbounded only for an edit inside a function that already has a row.

**Severity: nit.** Adding a rebinding statement between a `check_timeout` call
and its spawn, under a comment that says the value is checked there, is a
deliberate act rather than the natural next edit — which is the distinction
that made round 4's version a should-fix and this one not: round 4's defect was
reachable by editing a CALL SITE in another function, with nothing on screen to
say a predicate depended on it. **Fix, ~6 lines:** in the same walk, reject any
`Assign`/`AugAssign`/`AnnAssign`/`NamedExpr` to a checked name at a statement
index between `first_check` and `first_spawn`, and require the check to sit at
the function's top level rather than inside an `If`/`Try`/`With` body.
**REPEAT: partial** — same family as S1-a/S1-a-2, one costume smaller, and not
through the brief's remedy (the remedy moved the read INTO the sink, which is
what makes the natural edit safe now).

---

### N2 (nit, pre-existing on `origin/main`) — `init_probe.probe`'s `timeout` parameter bounds nothing, and the new sink check sits beside it certifying a different constant

`harness/propagation/init_probe.py:234` declares `probe(..., timeout: int = 120, ...)`.
Measured: the name `timeout` appears in that function's body **nowhere** —
`arms.py` calls `_probe(scratch, timeout=ctx.timeout)` at eight sites and the
value is discarded. The event loop is `for index, line in proc.stdout:` with no
bound at all, so a CLI that starts, emits no init event and does not exit blocks
the run forever; `proc.kill()` is in a `finally` the loop never reaches.

This PR adds, at that function's entry:

```python
guidance.check_timeout(KILL_WAIT_TIMEOUT_S,
                       "init_probe.probe(<popen>.wait timeout=)",
                       guidance.SINK_TIMEOUT_REMEDY)
```

which is correct for the `proc.wait()` sink and makes the sink pin green — while
the parameter a reader would take for the function's bound still bounds nothing.
A second unbounded spawn, `run_eval.py:883`'s `_git(...)`, is byte-identical to
main's.

**Severity: nit, pre-existing, not a regression** (`git diff origin/main -- harness/propagation/init_probe.py`
is the `sys.path` preamble, `KILL_WAIT_TIMEOUT_S`, and the check — nothing else).
Worth recording because the new pin now certifies this function, so the next
reader has one more reason to believe the parameter is honoured.
**Fix:** pass the parameter to a bounded read (or delete it and the eight
`timeout=ctx.timeout` arguments). **REPEAT: no.**

---

### N3 (nit, pre-existing on `origin/main`) — `objective_checks:` of the wrong type is a traceback, after the arms have run

| input | head | `origin/main`, skill path |
|---|---|---|
| `objective_checks: 7` | **rc 1**, `TypeError: 'int' object is not iterable` (`objective.py:3334`), traceback, **2 CLI calls already spent** | identical |

The A-N1 family one key over: `validate_mapping_keys` types `guard:`, `judge:`
and `env:`, and `objective_checks:` is not among them. Unlike every covered
row, this one fires **after** the guard probes have been paid for, so it is the
one malformed-fixture shape that costs real calls before failing outside the
rc-2 contract. Trusted-fixture-only, unreachable from a dispatch.
**Fix, one line:** `_require_list(fixture.get("objective_checks"), ...)` beside
the existing mapping checks. **REPEAT: no** — same shape as round-4 N6, one key
over, and round-4 N6's own rows are all closed (measured below).

---

### N4 (nit) — the fix-round report overstates one A-N3-2 row

`pr-138-fix4-report.md` records the invented source for A-N3-2 as "a plain
**rename** of the branch key (not an alias) — head RED at 15,300 s". Measured:

```
harness/run_eval.py:  fixture.get("judge_rubric") -> fixture.get("judge_rubric_v2")
-k test_the_guidance_budget_counts_every_per_arm_cost   ->  OK
-k fits_inside_the_workflow_job_timeout                 ->  OK
```

and correctly so: with the key renamed, no committed fixture declares it, so the
judge costs nothing and the budget is right. The row that IS red is round 4's
own alias shape, which I reproduced:

```
harness:  fixture.get("judge_prompt", fixture.get("judge_rubric"))
evals/guidance/_zz_probe: 5 arms, judge_prompt:, judge: {timeout_s: 2700}
-k fits_inside_the_workflow_job_timeout -> FAILED
  AssertionError: 18600 not less than 2025.0 : evals/guidance/_zz_probe: 5 arms
  x (deliver + agent + guard + judge = 3720s) = 18600s ... (those are the keys
  _run_guidance_arm's judge branch reads, parsed out of the harness)
```

A-N3-2 is genuinely closed; only the report's description of its proof is wrong.
No code change. **REPEAT: no.**

---

## HELD UP UNDER ATTACK

### The timeout sink (S1-a-2)

**The sink list, built by my own `ast` walk of `harness/**/*.py`, is 16
functions** and matches the committed `SINK_DRIVERS` table exactly:
`guidance.deliver`, `account_store.git_tracked`, `arms._run_hook`,
`arms.arm_plugin_marketplace`, `init_probe.probe`, `judge._run_judge_cli`,
`run_canary.claude_version`, `run_canary.run_leg`, `run_account_audit.registry_ref`,
`run_eval.run_setup`, `run_eval.run_agent`, `run_eval._nested_repo_diff`, and
`objective.git_ref_unchanged` / `git_remote_url_is` / `reaper_ran_in_standalone_repo`
/ `git_worktree_list_matches`. Every one calls `guidance.check_timeout` on the
expression it hands over, before its first spawn, in statement order.

**The invented source the worker claims, reproduced.** In a throwaway copy,
`run_agent`'s read rebound to the **process environment** — no fixture key, no
flag, no literal, no callee default, no inventory key changed:

```python
-   timeout = arm.get("timeout", 600)
+   timeout = int(os.environ.get("SKILLS_EVALS_AGENT_TIMEOUT_S", "600"))
```

```
SKILLS_EVALS_AGENT_TIMEOUT_S=2200000  python3 harness/run_eval.py <guidance fixture> …
RC= 2   CLI_CALLS= 0   RESULTS_FILES= []   TRACEBACK= False
configuration error: `run_eval.run_agent(timeout=)` must be a positive number of
seconds no greater than 2700 … This is the subprocess sink itself: the value was
checked on entry to the function that spawns, whatever source it came from.
```

**Planted sinks, each in its own throwaway copy** (`pin` =
`..._sink_checks_the_value_before_it_spawns`, `inv` = the belt-and-braces
inventory):

| planted `harness/r5sink.py` | pin | inv |
|---|---|---|
| `opts = {"timeout": v}; subprocess.run(cmd, **opts)` | **RED** | **RED** |
| `proc.wait(v)` — positional | **RED** | **RED** |
| `proc.communicate(None, v)` — positional | **RED** | **RED** |
| plain new sink, no check | **RED** | **RED** |
| `import subprocess as sp; sp.run(..., timeout=v)` | **RED** | **RED** |
| checks one expression, hands over ANOTHER | **RED** | **RED** |
| new sink WITH the check | OK | RED (no table row — correct) |
| committed tree | **OK** | **OK** |

**Through the CLI, `evals/guidance` shape, `$FAKE_CLAUDE_ARGV_LOG` counted:**

| row | rc | CLI calls | results/ |
|---|---|---|---|
| ordinary run | 0 | 4 | full run dir |
| `--timeout 2200000` | **2 named** | 0 | empty |
| `timeout_s: 2200000` / `null` / `true` / `"600"` | **2 named** | 0 | empty |
| `guard.timeout_s: 99999` | **2 named** | 0 | empty |
| `setup_timeout_s: 2200000` | **2 named** | 0 | empty |
| `setup: true` + `setup_timeout_s: 99999` | **2 named** | 0 | empty |
| `judge.timeout_s: 2700` (at the ceiling) | 0 | 4 | full run dir |

`MAX_TIMEOUT_S` is 2700 and equals `eval.yml`'s `timeout-minutes: 45` × 60,
checked programmatically.

### Containment (F-1-N)

Every path `guidance.py` builds from `guidance_dir` goes through
`inside_checkout` (`MANIFEST_REL` ×2, `BASE_REL`, `STUB_REL`, `HOOK_REL`, every
manifest `file:`) — enumerated by grep over every `guidance_dir` use, 11 sites,
0 outside the funnel.

| mutation of the checkout | result |
|---|---|
| `agents-md/eval-coverage.yml` → symlink out | **GuidanceError**, outside ids never loaded |
| `.claude/hooks/fleet-memory.sh` → symlink out | **rc 2 named**, 0 CLI calls, outside script **not executed** (marker absent) |
| `agents-md/base.md` → symlink out | **rc 2 named**, 0 CLI calls |
| `agents-md` ITSELF → symlink out | **rc 2 named**, 0 CLI calls (the worker's invented source, reproduced) |
| `agents-md/stub.md` → symlink out, arms `section`/`none` | rc 0 — the stub is not read in those modes; correct |

| manifest `file:` | result |
|---|---|
| `../outside/X.md` | GuidanceError named |
| `/etc/passwd` | GuidanceError named |
| in-tree symlink CHAIN → outside | GuidanceError named |
| symlinked DIRECTORY `agents-md/linkdir/X.md` | GuidanceError named |
| `/proc/self/environ` via in-tree symlink | GuidanceError named |
| `agents-md/../agents-md/base.md` | **accepted** — inside after normalisation, correct |
| `agents-md/sections` (a directory) | GuidanceError `could not read … Is a directory` |
| `5`, `["agents-md/base.md"]`, `{"a": 1}`, `True` | GuidanceError **`row 0's `file:` must be a string`** — round-4 N6 closed |
| `null`, `""` | GuidanceError `missing required field` |

No refusal message contained `$HOME` or any environment value (checked on every
row). `--guidance`: a symlink to the checkout rc 0; a path with `..` rc 0;
trailing slash rc 0; a FILE rc 2 named; nonexistent rc 2 named; `/` rc 2 naming
the missing manifest; `""` falls back to the sibling (the recorded item,
unchanged).

### Mapping keys and `env:` after the merge (A-N1-2)

| fixture | rc | CLI | results/ | traceback |
|---|---|---|---|---|
| root is a list | 2 named | 0 | empty | no |
| EMPTY file (YAML `None`) | 2 named `(the file is empty)` | 0 | empty | no |
| `env: {"A=B": x}` | 2 named | 0 | empty | no |
| `guard: 7` / `judge: 7` / `env: 7` | 2 named, type AND repr | 0 | empty | no |
| `judge: {timeout_s: {}}` | 2 named | 0 | empty | no |
| YAML anchor making `guard` and `judge` one object | 2 named on the shared value | 0 | empty | no |
| merge key `<<: *b` | 2 named | 0 | empty | no |
| duplicate `guard:` (last hostile) | 2 named — last wins, and it is the one validated | 0 | empty | no |
| duplicate `guard:` (last sane) | proceeds | — | — | no |
| arm-level `guard:` | 2 named `arm 'a' has unknown key(s) ['guard']` | 0 | empty | no |
| unknown `subject:` | 2 named | 0 | empty | no |
| `arms:` omitted | runs the default pair | — | — | no |

**`invalid_judge_block` routing (the reconciliation commit):**

| fixture | rc | artifacts |
|---|---|---|
| `skill: workflow-path-audit` + `judge: 7` | **2**, stdout `invalid_judge_block: …` | `report.md` + `with_skill/summary.json` + `without_skill/summary.json` written |
| `skill: 7` + `judge: 7` (no usable skill) | **2**, plain `fixture configuration error:` | **nothing** under `--results-dir` |
| `skill: ../../etc` + `judge: 7` | **2**, plain line | **nothing** written |
| guidance fixture + `judge: 7` | **2**, plain line | **nothing** written |

**The two allowlists, measured through a 92-name hostile parent** (GitHub and
Actions tokens, AWS/Azure/GCP, SSH/GPG/netrc/vault/kube, `LD_PRELOAD`,
`LD_AUDIT`, `NODE_OPTIONS`, `BASH_ENV`, `ENV`, `PYTHONSTARTUP`, `PYTHONPATH`,
proxies, `CLAUDE_*`, `SKILLS_EVALS_*`, fillers), by calling the two `agent_env`
functions that build the child environment:

* **skill arm: exactly 43 names.** The 25 `_ALLOWED_ENV` names present,
  everything matching `ANTHROPIC_`/`CLAUDE_`/`LC_`/`XDG_`, `WORKSPACE`,
  `GH_CONFIG_DIR` (inside the workspace), and `GH_TOKEN`/`GITHUB_TOKEN`
  **empty**. `ACTIONS_ID_TOKEN_REQUEST_TOKEN`, `ACTIONS_ID_TOKEN_REQUEST_URL`
  and `ACTIONS_RUNTIME_TOKEN` **absent**. `PYTHONPATH`, `LD_PRELOAD`,
  `NODE_OPTIONS`, `BASH_ENV`, `SSH_AUTH_SOCK`, `KUBECONFIG`, `AWS_*`,
  `OPENAI_API_KEY`, `GITLAB_TOKEN`, `NPM_TOKEN` **absent**.
* **guidance arm: exactly 15 names** — `PATH LANG LC_ALL SHELL USER NODE_PATH`
  + the five `ANTHROPIC_*` + `HOME`/`TMPDIR`/`CLAUDE_CONFIG_DIR`/`WORKSPACE`,
  all four pointing at the arm's own scratch. Zero non-allowlisted names.
  `PASSTHROUGH` is the exact six-tuple, `EXTRA_PASSTHROUGH` is `()`.

**Fixture `env:` by name, on BOTH arms:**

| name | skill arm | guidance arm |
|---|---|---|
| `HOME`, `TMPDIR`, `CLAUDE_CONFIG_DIR` | accepted | **REFUSED by name** |
| `""`, `"A=B"`, a name containing NUL, a value containing NUL | **REFUSED** | **REFUSED** |
| `PATH`, `PYTHONPATH`, `LD_PRELOAD`, `NODE_OPTIONS`, `BASH_ENV`, `ANTHROPIC_API_KEY`, `GH_TOKEN`, `WORKSPACE`, `"A\n"` | accepted | accepted |

which is exactly what the rewritten header claims: `check_env_block` is shared
and bounds what a fixture may SPELL; the isolation refusal is the guidance
arm's alone. `run_setup`'s `expand()` substitutes against the ALLOWLISTED
environment, so `$HOME` in a `setup:` command is the allowlisted `HOME` and
`${GH_TOKEN}` is the empty string — no ambient value can be pulled in;
`guidance.agent_env`'s `string.Template(...).safe_substitute(env)` substitutes
against the same filtered env. `_run_guidance_arm` never calls `run_setup` at
all, so a guidance fixture's `setup:` is validated and then inert (which is what
the budget test asserts by parse).

### Arm names (A-N2-2)

`.` and `..` refused; `report.md` refused by name; 234 / 255 / 256 / 4096
characters refused naming `MAX_ARM_NAME_LEN` = 233 (= 255 − `len("skills-evals-")` − 1 − 8);
`a`*233 accepted; NFC and NFD `éarm` both refused by the ASCII class, so no
normalisation collision is possible; `a/b`, `a\b`, `a b`, `""` refused;
`with_guidance` + `mode: none` refused by the name/mode agreement.
`...`, `.hidden`, `-`, `--results-dir`, `a.`, `none`, `None`, `CON`,
`summary.json`, `transcripts`, `raw.json`, `objective-only` accepted — and
**listed the run dir for each**: every one produced its own directory under the
run dir with `summary.json` + `transcripts/raw.json` inside it, nothing above
the run dir, and no collision with `report.md`.

### The fit test (A-N3-2)

`eval.yml` `jobs.eval.timeout-minutes: 45` → 2700 s; the test's line is
`job_budget_s * 0.75` = **2025 s**. `evals/guidance/_delivery`: 5 arms ×
(120 deliver + 120 agent + 120 guard + 0 judge) = **1800 s** — 225 s of
headroom against the test's line and 900 s against the real job. The judge keys
are parsed out of `_run_guidance_arm` (`_judge_branch_keys()`), and round 4's
alias shape is now RED at 18,600 s (above). `judge:` present with `timeout_s`
absent takes the 120 s default; `arms:` absent counts 2.

### Discovery dir (A-N4-2)

| planted under `test/issues/` | pin |
|---|---|
| `colorsys/__init__.py` (package) | **RED** |
| `colorsys.so` | **RED** |
| `colorsys.cpython-311-x86_64-linux-gnu.so` (the real tagged name) | **RED** |
| `colorsys.pth` | **RED** |
| `conftest.py`, `__init__.py` | **RED** |
| `test_issue_97.py.bak` | **RED** |
| symlink to `/dev/null` | **RED** |
| `sub/test_issue_x.py` | **RED** |
| symlinked directory | **RED** |
| a **FIFO** named `test_issue_fifo.py` | **RED in 0.005 s**, no hang, 0 survivors |
| `test_issue_.py` (empty stem) | OK — matches the pattern and is discovered; correct |
| `__pycache__` only | OK |
| committed tree | OK |

### The merge itself

* **The widened judge pin is not vacuous.** Adding a third `judge.score(...)`
  call with a `mode=` kwarg to `run_eval.py` → `test_run_eval_does_not_honour_judge_mode_yet`
  **RED**: `+ ['model', 'timeout', 'weights'] : run_eval.py's judge.score() call changed shape`.
  It iterates EVERY call site, not `calls[0]`.
* **`materialize_workspace`'s try/except does not swallow the guidance arm's
  workspace**: `except SetupFailedError: raise` (no `rmtree`, the caller owns
  it), `except Exception: rmtree; raise`. A sink `GuidanceError` from
  `run_setup` propagates out of both.
* **The per-arm judge `except` re-raises `GuidanceError`** at both call sites
  (`_run_arm` and `_run_guidance_arm`), so a sink refusal lands on `main()`'s
  rc-2 contract rather than being recorded as a judge error and scoring the arm.
* **`objective.FixtureError` and `guidance.GuidanceError` both reach rc 2
  named with no traceback** through `main()` (`strip_seed`/`invalid_fixture` and
  every guidance row above). The one gap in the pair is `objective_checks:` of
  the wrong type — N3.
* **`_write_pre_run_error` does not fire for guidance fixtures**: it is reached
  only on `exc.key == "judge" and usable_skill`, and a guidance fixture has no
  `skill:` — measured, nothing written.
* **`judge.score_fixture` is still unwired** (`run_eval.py` calls `judge.score`
  only), and `check_timeout` now sits on `_run_judge_cli`, the one function in
  that module that hands a timeout to subprocess for both the absolute and the
  pairwise instruments.

### The guard, both directions

Driven through `run_eval.main()` with pinned tokens and a forging CLI whose
reply I control (delivered through the fixture's own `env:`, since the arm's
environment is an allowlist):

| forged reply | arms | rc | outcome |
|---|---|---|---|
| `$MAGIC` only | treat + control | **2** | treatment scores; **control `guard_contaminated`** |
| `$MAGIC $DECOY` | treat + control | **2** | **both contaminated**, neither scored |
| `$DECOY` only | treat + control | **2** | **treatment contaminated** — the quiet direction |
| `NO-MAGIC-WORD` / empty | treat + control | 2 | `guard_miss` on both, neither scored |
| decoy_a | two `none` arms | 2 | ctrl_a scores; **ctrl_b contaminated** |
| decoy_b | two `none` arms | 2 | **ctrl_a contaminated**; ctrl_b scores |
| both decoys | two `none` arms | 2 | **both contaminated** |

No contaminated arm was ever scored. The clean partner of a contaminated pair
still gets its own `summary.json` with checks while the run is rc 2 — the
recorded item, unchanged.

### Delivery

| sabotaged hook | rc | elapsed | CLI calls | arms |
|---|---|---|---|---|
| exits 3, writes nothing | **2** | 0.2 s | **0** | both `delivery_failed` |
| exits 0, prints `fleet-guidance: current`, writes nothing | **2** | 0.2 s | **0** | both `delivery_failed` |
| exits 0, writes an UNMARKED file | **2** | 0.2 s | **0** | both `delivery_failed` |
| `sleep 900`, `guard.timeout_s: 5` | **2** | **120.2 s** | 0 | `could not run …` |

The 120 s is `deliver()`'s own bound, not `guard.timeout_s` — the recorded
round-2/3 item, unchanged. It orphaned a `sleep 900` grandchild; I found it
(`etimes=139`) and killed it.

### The dispatch gate — 41 hostile inputs, executed under `bash`

Step 9's `run:` block extracted with `yaml.safe_load`, run against a synthetic
`$GITHUB_EVENT_PATH` written as raw bytes and a synthetic `evals/` tree built
from the 16 committed fixture paths. `$RUNNER_TEMP` inspected after every row.

**Every rejecting row left `$RUNNER_TEMP` empty — nothing minted, nothing
exported, before any rejection. No row echoed the value** (a `R5GATE` marker
inside a 64 KB payload never appeared in any output).

| class | rows | result |
|---|---|---|
| committed (default, workflow-path-audit, guidance/_delivery, writing-adrs/bootstrap) | 4 | rc 0, both temp files |
| NUL leading / trailing / embedded / alone / doubled / appended to a committed path | 6 | rc 1, `contains a NUL byte` |
| a RAW NUL byte inside the JSON | 1 | rc 5, `jq: parse error` — closed before anything |
| charset (`$(id)`, backticks, `;`, `*`, `evals/*`, spaces, TAB, CR, two multi-line shapes, unicode, an object input) | 12 | rc 1, charset branch, **before** any matching |
| traversal / near-misses (`..`, `/etc/passwd`, `./evals/…`, `evals//…`, trailing slash, bare `evals`, `…/fixture.yaml`, `/evals/…`, `..` alone) | 9 | rc 1, `names no committed fixture` |
| non-strings (`5`, `true`) | 2 | rc 1, value not in the message |
| 64 KB marker payload, 100 KB charset-clean | 2 | rc 1, marker absent from the log |
| `null` input, empty string, empty event file | 3 | rc 0, the default |
| `inputs` an array, malformed JSON | 2 | rc 5 under `set -e`, fails closed |

**Step order, from the parsed YAML:** step 9 *Select and validate the fixture to
run* precedes step 10 *Mint OIDC token and exchange for Anthropic access token*
and step 11 *WIF auth preflight*.

### The workflow files, and the rewritten header sentence by sentence

`git diff f9115ce..3c558a5 -- .github/` is `eval.yml` alone, 24 + / 12 −, and
**every changed line is a comment** — proved two ways: the non-comment,
non-blank filter over `git diff -U0` is empty, and `yaml.safe_load` of both
revisions of BOTH workflow files compares **equal** (`PARSED-IDENTICAL`).
`.github/` vs `origin/main` is `eval.yml` + `ci.yml` only.

Parsed all six workflows: **0 `run:` blocks containing `${{`**; every `uses:`
is a bare 40-hex SHA (the one `Adam-S-Daniel/cms-platform/...@v0.1.87` is the
fleet's documented carve-out); **zero `uses:` lines carry a trailing comment**.
`eval.yml` triggers exactly `{schedule, workflow_dispatch}`; `permissions
{contents: write, id-token: write}` is **identical to `origin/main`**; the only
`concurrency` is workflow-level `real-eval` and the job has none; `ci.yml` — the
`pull_request` publisher of the required context — has **no `concurrency` at
all**, at workflow or job level, same as main. All five `eval.yml` checkouts and
all three `ci.yml` checkouts carry `persist-credentials: false`; `GITHUB_TOKEN`
appears in step 13's `env` and nowhere else.

**The rewritten header, measured claim by claim against the code:**

| header sentence | measured |
|---|---|
| skill arm's allowlist is `_ALLOWED_ENV` + `_ALLOWED_ENV_PREFIXES` | true |
| the 25 names it lists | **all 25 present in the code tuple, and every code name is named in the header** — 0 missing either way |
| "every variable whose name begins ANTHROPIC_, CLAUDE_, LC_ or XDG_" | exactly `('ANTHROPIC_','CLAUDE_','LC_','XDG_')` |
| "the harness's own WORKSPACE and GH_CONFIG_DIR" | true, `GH_CONFIG_DIR` inside the workspace |
| "the deliberately EMPTIED GH_TOKEN and GITHUB_TOKEN" | `_BLANKED_ENV`, measured as empty strings |
| "last the fixture's own `env:` block" | true, applied last |
| "None of those three is in reach for either arm now" | **true, measured on both arms under a hostile parent** |
| guidance arm: `PATH, LANG, LC_ALL, SHELL, USER, NODE_PATH` | exactly `PASSTHROUGH` |
| "plus the HOME, TMPDIR, CLAUDE_CONFIG_DIR and WORKSPACE the harness sets and every ANTHROPIC_* variable" | true — the 15 names measured |
| "HOME, TMPDIR, CLAUDE_CONFIG_DIR are refused by name" | true, `ISOLATION_NAMES`, guidance arm only |
| "the three GitHub runner tokens above are NOT in that set either" | true |
| "the guidance one is the narrower" | true — 15 vs 43 |
| "What they share is the predicate … (`guidance.check_env_block`), which bounds what a fixture may SPELL rather than what is inherited" | **true — the same function is called from both `agent_env`s, and the name/value rows above are identical on both arms** |

I could not falsify a single sentence of it.

### Round-4 items, re-measured

Round-4 N1 (the marker SET unpinned) **closed**; N2 (`test/` helper) closed;
N3 (the package in the discovery dir) closed; N4 (`report.md` / long arm names)
closed; N5 (the fit test's literal key) closed; N6's manifest `file: 5`, `file:
[...]`, list-rooted fixture, empty fixture and `env: {"A=B": x}` rows all
closed. The module-alias-by-assignment fork nit is closed. The concatenation,
f-string and glob fork nits are unchanged (still nits). The record-only list is
unchanged, with one addition (N2 above).

---

## VERIFIER TABLE

Run on `3c558a5` in a fresh copy of the read-only export, throwaway `HOME` and
`SKILLS_EVALS_USER_MEMORY`, siblings `_agent-guidance` (`5f13def4`) and
`agentskills` (`cd5ad3e1`) present, `markdown-it-py` 4.2.0, `PyYAML` 6.0.1.
Serial per checkout.

| verifier | expected | measured | rc |
|---|---|---|---|
| `python3 test/run_tests.py` | 1184, 3 skipped | **Ran 1184 tests in 830.6 s — OK (skipped=3)** | **0** |
| `python3 test/run_tests.py -k TestIssue97` | 138 | **`NARROWED RUN: -k selected 138 of 1184`**, Ran 138 in 618.9 s, OK | **0** |
| `python3 test/test_propagation.py` | 164, 1 skipped | **Ran 164 tests in 7.7 s — OK (skipped=1)** | **0** |
| Rule 19: every shared fixture vs `$SP/mainx5` under `--arm objective-only` | identical per check | **15 of 15 IDENTICAL** by (rc, full `(id, passed)` list); 14 of 15 byte-identical stdout, `disarm-inherited-reach` differs only in the checkout root inside a path | matched |
| `evals/guidance/_delivery --arm objective-only` | rc 2 | rc 2, the documented "declares no top-level `objective_checks:`" message | **2** |
| committed fixtures | 16 | **16** (15 shared + `evals/guidance/_delivery`) | — |
| `git diff f9115ce..3c558a5 -- .github/` non-comment lines | empty | **empty**; `yaml.safe_load` of `eval.yml` and `ci.yml` **PARSED-IDENTICAL** across the two revisions | — |
| `git diff --stat origin/main..3c558a5 -- .github/` | ci.yml + eval.yml only | **exactly those two** (+16 / +207) | — |
| `git merge-base --is-ancestor 3fb20e1 3c558a5` | true | **true** | 0 |
| `git merge-tree --write-tree origin/main 3c558a5` | clean | **clean**, tree `c78d7d794b951a168eeac4d80bd51e330ec0419a` | **0** |
| `MAX_TIMEOUT_S` == `eval.yml` job budget | 2700 | **2700 == 45 × 60** | — |

Rule 19 detail (rc, check count, head/main): `adam-writing-style/proposal-bio`
1, 3/3 · `…/recruiter-reply` 1, 4/4 · `…/self-appraisal-opening` 1, 3/3 ·
`cms-stuck-pr-triage` 1, 7/7 · `disarm-inherited-reach` 1, 9/9 ·
`github-actions-sha-pinning` 1, 10/10 · `guidance-bridge-canary` 2, 0/0 ·
`post-failure-comment` 1, 12/12 · `propagation` 2, 0/0 · `rename-pdfs` 1, 8/8 ·
`review-bash-ci-reliability` 1, 11/11 · `windows-elevation-from-wsl` 1, 7/7 ·
`workflow-path-audit` 1, 8/8 · `writing-adrs/bootstrap` 1, 9/9 ·
`writing-adrs/existing-convention` 1, 7/7.

---

## TREE INTEGRITY AND SAFETY LEDGER

| item | start | end |
|---|---|---|
| `md5sum /root/.claude/CLAUDE.md` | **`935c291f2efb1ff55a463bccfde55e6a`** | **`935c291f2efb1ff55a463bccfde55e6a`** — unchanged; nothing written under `/root/.claude` |
| the nine named files in `$SP/rev97e-adv` | all matched the brief | **all matched again** |
| `$SP/rev97e-adv` vs a fresh `git archive 3c558a5` | — | **`diff -rq` clean — BYTE-IDENTICAL** (after removing the two `__pycache__` dirs an in-place import created; `PYTHONDONTWRITEBYTECODE` was not set on that one direct-import probe) |
| `$SP/rev97e-adv/test/issues/` | `test_issue_97.py` only | **`test_issue_97.py` only** — the suite left NO file there, in any copy |
| `$SP/rev97e-ref`, `$SP/mainx5`, `$SP/_agent-guidance`, `$SP/agentskills` | — | untouched (read-only; `_agent-guidance` and `agentskills` were COPIED into my scratch to serve as siblings and their `origin` remotes removed on the copies, never on the originals) |
| `/home/user/skills-evals` | HEAD `1530b51`, `.claude/worktrees/` untracked | unchanged — read-only git only |
| my scratch (`r5adv97-c2…c9`, `-cc`, `-cf`, `-ck`, `-cr`, `-cr2`, `-cs`, `-r19`, `-verify-*`) | — | **deleted**; `r5adv97-w`, `-work`, `-home` remain and are mine to delete |
| my `/tmp` leftovers (`r5drv-*`, `r19-*`, `r19b-*`, `r5gate-*`, `r5f1*`, `r5g-*`, `r5d-*`, `r5subdir`) | — | **removed, 0 remain** |
| background processes I started | — | **0 remain**, counted by resolving `/proc/<pid>/cwd` into my own copies. Every fork tree killed by process-group id at its bound; one orphaned `sleep 900` grandchild from the hanging-hook probe was found and killed |
| network / GitHub writes / real `claude` / real `gh` / credentials copied / sessions, routines, reminders | — | **none** |

One self-inflicted incident, recorded because it cost a re-run: my first
orphan-reaping loop matched `*r5adv97*` and killed the baseline full-suite run
in my own work copy. Nothing outside my scratch was touched; the baseline was
re-run from scratch and is the 1184/3-skipped row above.

---

## WHAT I COULD NOT MEASURE

* **Whether a real `claude` CLI honours `CLAUDE_CONFIG_DIR` for user memory** —
  the whole `--delivery user` premise. Everything above ran against
  `test/fake-claude` and two CLIs I wrote. Unchanged from rounds 1–4.
* **The real dispatch** — the OIDC/WIF exchange, the `eval-results` push, and
  therefore whether a five-arm guidance run really fits 45 minutes in
  wall-clock. The arithmetic is pinned at 1800 s of 2025 s; the clock is not.
* **How far the `scripts/` fork tree would climb.** I bounded it at 45 s in its
  own process group and killed by pgid, so "85 and climbing" is a floor.
* **Whether `probe()`'s unbounded stdout loop is reachable with a real CLI** —
  it needs a CLI that starts, emits no init event and never exits. I read it
  statically and did not drive it.
* **`markdown-it-py`'s publish date** against the 7-day cooling-off (offline).
* **Other sessions' trees** — out of scope by rule; my process accounting
  resolved `/proc/<pid>/cwd` so as not to count or kill theirs.

---

## RECOMMENDATION

**One should-fix, and the brief's own rule says a should-fix parks the PR.** I
will not pretend otherwise: `scripts/` is the third directory `run_tests.py`
puts on `sys.path`, it is a tracked directory this PR itself edits, a helper
there runs the suite away with both pins green, and A-N4's new failure message
sends a contributor to it by name. That is the same defect for the fourth round,
arriving through the fourth version of its own remedy.

But the shape of the round is different from round 4's, and that is worth
saying plainly for whoever decides. Everything else the brief asked for landed
**at the sink and holds by construction**: the timeout predicate refused a
source nobody had named, in a mutation I invented, with zero CLI calls and
nothing written; six planted sink spellings that defeated round 3's walk are
RED; every containment escape shape is a named rc-2 refusal; the discovery dir
is checked by entry and a FIFO cannot hang it; the env allowlists are exactly
what the header now says they are, on both arms, under a 92-name hostile
parent; and the header itself — the one thing in this round that is only
prose — did not contain a single sentence I could falsify. Nothing mints or
exports before a rejection, no contaminated arm scores, nothing hostile reaches
the operator's files or publishes a file from outside the checkout, and nothing
on the committed surface hangs.

The remaining gap is one directory name in one tuple, and the durable version
of the fix is to stop writing that tuple by hand: derive it from the
`sys.path.insert` calls `run_tests.py` already makes. If the orchestrator has
any appetite left for a bounded change, that is a handful of lines plus one
corrected sentence in a failure message, and it is the version that cannot come
back a fifth time.
