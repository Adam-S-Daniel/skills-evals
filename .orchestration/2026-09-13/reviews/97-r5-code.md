FOUND — 0 blocker, 1 should-fix, 5 nit

# PR #138 round 5 — CODE half (one-way-door, measure not read)

Head `3c558a5b0ee60f21567e403fd34ab17a3e2c50e8`; ref `f9115ce`; `origin/main` `3fb20e1`.

**Verdict in one sentence.** Six of the seven round-4 items (S1-a-2, A-N4-2,
F-1-N, A-N1-2, A-N2-2, A-N3-2), the merge union, the three merge hazards and
all five reconciliations are closed over their whole surface, measured at the
sink and red-first; **S-B-a-2 is not** — its *spawner* half is genuinely at the
sink and holds, but its *membership scan* half, the only thing that can catch a
SECOND spawner, is still an enumeration of ways to SPELL the runner's name and
fails OPEN on anything it cannot resolve. Four of eleven planted forking
helpers walked past it, two of them naming the runner through `run_tests.py`'s
own published constants. That is the round-4 finding's shape returning through
the brief's own remedy, so it is graded a should-fix.

## Tree integrity

| | value |
|---|---|
| `md5sum /root/.claude/CLAUDE.md` before first command | `935c291f2efb1ff55a463bccfde55e6a` |
| `md5sum /root/.claude/CLAUDE.md` after last command | `935c291f2efb1ff55a463bccfde55e6a` (see ledger below) |
| `$SP/rev97e-code` md5s at start | all 13 match the brief exactly |
| `$SP/rev97e-code` md5s at end | all 13 match (see ledger) |
| `test/issues/` before | `test_issue_97.py` |
| `test/issues/` during | `test_issue_97.py`, `test_issue_zz_memory_probe.py` (planted by the suite, mid-run) |
| `test/issues/` after | `test_issue_97.py` |

One honest note about my own hygiene: my first head-suite run was interrupted by
the five-hour rate limit and left `test/issues/test_issue_zz_memory_probe.py`
behind. The next run in that checkout therefore read RED on the S2 snapshot
(`usermem.md absent -> 255867f7…`) and on
`test_an_ordinary_run_leaves_the_watched_file_alone` ("left over from an earlier
run"). Both were my residue, not the PR's: I removed the file, re-ran the whole
suite serially with a fresh throwaway `HOME`, and the clean run is the one
reported below. The same residue inflated one `-k NoSuchThingAtAll` reading to
`1185 tests`; re-measured clean it is 1184. Every mutation ran under
`HOME=$SP/r5w97-home` or `$SP/r5probe-home` (never the real one),
`SKILLS_EVALS_USER_MEMORY` pointed at a throwaway file, `PYTHONDONTWRITEBYTECODE=1`.

## Verifier

| verifier | tree | measured | expected | ✓ |
|---|---|---|---|---|
| `python3 test/run_tests.py` | head | **Ran 1184, OK (skipped=3)**, rc 0, 711 s | 1184, 3 skipped (agentskills sibling seen) | ✓ |
| `-k TestIssue97` | head | **NARROWED RUN: -k selected 138 of 1184**, **Ran 138, OK**, rc 0 (598 s — it forks four full child suites) | 138 of 1184 | ✓ |
| `-k NoSuchThingAtAll` | head | rc **2**, `selected 0 of 1184 tests` | rc 2 | ✓ |
| `python3 test/test_propagation.py` | head | **Ran 164**, OK (skipped=1), rc 0 | 164, 1 skipped | ✓ |
| `python3 test/run_tests.py` | `origin/main` (`3fb20e1`) | **Ran 1032, OK (skipped=3)**, rc 0 | 1032 | ✓ |
| `python3 test/run_tests.py` | ref (`f9115ce`) |  **Ran 807, OK (skipped=2)**, rc 0 | 807 | ✓ |

3 skipped, with both siblings present (`$SP/_agent-guidance`, `$SP/agentskills`).

## Per-item table

| item | commit | landed? | red-first? | mutation red? | surface enumerated by me & covered? | verdict |
|---|---|---|---|---|---|---|
| **S1-a-2** timeout ceiling at the sink | `a397327` | yes | yes (ref rc 1 `OverflowError`/tracebacks) | yes, 6 independent mutations | **yes** — my own AST walk found 16 `subprocess.run(timeout=)` sites + 1 `Popen.wait(timeout=)` in 16 functions; the committed table has exactly those 17 sites in 16 rows | **CLOSED** |
| **S-B-a-2** one spawner stands down | `8d443c3` | partly | yes (g3/g4 red) | spawner half yes; scan half **4 misses of 11** | **no** — see finding SF-1 | **NOT CLOSED (should-fix)** |
| **A-N4-2** discovery dir by entry | `edb59e4` | yes | yes | yes, 7 hostile entries red, `__pycache__` green | yes | **CLOSED** |
| **F-1-N** `inside_checkout` the only funnel | `d0816be` | yes | yes | yes (revert `_read`; drop `MANIFEST_REL`) | **yes** — my own AST walk of `guidance.py` + `run_eval.py` finds exactly ONE `guidance_dir`-derived path expression in the repo, and it is inside `inside_checkout` itself | **CLOSED** (one nit) |
| **A-N1-2** fixture container + `env:` | `8c6794a` | yes | yes (ref: 3 tracebacks rc 1) | yes | yes | **CLOSED** (one nit) |
| **A-N2-2** arm name vs every derived path | `a42f203` | yes | yes (ref: `IsADirectoryError`, `File name too long`) | yes | yes | **CLOSED** |
| **A-N3-2** budget reads the judge key by AST | `b583341` | yes | yes | yes (planted rename → 15 300 s vs 2 025 s) | yes | **CLOSED** |
| **merge union** | `6d6a832`,`4adbcb9` | yes | n/a | n/a | yes — exact union, 0 missing, 0 invented | **CLOSED** |
| hazard (a) judge-mode refusal + widened pin | `3c558a5` | yes | n/a | yes, at BOTH call sites | yes | **CLOSED** |
| hazard (b) two allowlists | merge | yes | n/a | yes (r1a/r1b/r1c) | yes, measured under a 93-name hostile parent | **CLOSED** |
| hazard (c) `$WORKSPACE`/`${WORKSPACE}` | merge | yes | n/a | n/a | yes, both spellings, both `agent_env`s and `expand()` | **CLOSED** |
| reconciliation 1 (header ↔ both envs) | `3c558a5` | yes | n/a | yes ×3 | yes | **CLOSED** |
| reconciliation 2 (`env:` passthrough) | `3c558a5` | yes | n/a | yes | yes | **CLOSED** |
| reconciliation 3 (judge call-site pin) | `3c558a5` | yes | n/a | yes ×2 | yes | **CLOSED** |
| reconciliation 4 (sink row → `_run_judge_cli`) | `3c558a5` | yes | n/a | yes | yes | **CLOSED** |
| reconciliation 5 (`invalid_judge_block` routing) | `3c558a5` | yes | n/a | n/a (both branches measured) | yes, both directions | **CLOSED** |
| regressions rounds 1–4 | — | n/a | n/a | n/a | yes, see below | **no regression found** |
| merge state | — | yes | n/a | n/a | yes | **CLOSED** |
| Rule 19 | — | yes | n/a | n/a | 15/15 identical, `_delivery` exit 2 | **CLOSED** |

## S1-a-2 — the sink, measured

**The sink.** My own `ast` walk of `harness/**/*.py` for every call to
`subprocess.{run,Popen,call,check_call,check_output}` carrying `timeout=` or a
`**` splat, plus every `.wait(`/`.communicate(` carrying a timeout, finds
**17 call sites in 16 functions**:

```
guidance.deliver · propagation/account_store.git_tracked · propagation/arms._run_hook ·
propagation/arms.arm_plugin_marketplace · propagation/init_probe.probe (Popen.wait) ·
run_account_audit.registry_ref · run_canary.claude_version · run_canary.run_leg ·
run_eval.run_setup · run_eval.run_agent · run_eval._nested_repo_diff ·
scorers/judge._run_judge_cli · scorers/objective.{git_ref_unchanged,git_remote_url_is,
reaper_ran_in_standalone_repo ×2, git_worktree_list_matches}
```

The committed `HARNESS_TIMEOUT_SINKS` table has exactly those 17 sites in 16
rows — no row I cannot account for, no site the table misses. A second walk of
my own confirms all 16 functions call `guidance.check_timeout` in a statement
that **precedes** their first spawn (16 guarded, 0 unguarded), and that the
expression checked is *textually identical* to the expression handed to
`timeout=` at every one of them, with no rebinding in between.

**Direct-call battery** (`subprocess.run` patched to count and abort), six
sinks × 8 hostile values `2200000, True, 0, -1, nan, inf, "600", None`: **48/48
`GuidanceError`, 0 spawns**; `600` spawns at every one.

**Through the real CLI** (`--timeout`), 0 CLI invocations on every rejection:

| flag | `run_eval.py` | `run_canary.py` | `run_propagation.py` |
|---|---|---|---|
| 2200000 / 2701 / 0 / −1 | rc **2** named, 0 calls | rc **2** named | rc **2** named |
| 600 / 2700 | rc **0** | runs | — |

**Judge path at the sink, not only at the knob.** With the `("timeout_s",
("judge",))` row deleted from `TIMEOUT_KNOBS` in a throwaway copy, a fixture
with `judge: {timeout_s: 2701}` + a rubric is still **rc 2** and names
``judge._run_judge_cli(timeout=)`` — the error routes out of the per-arm
try/except as the contract requires, not as `Runner-level error in arm(s)` and
not as a traceback. On the committed tree the load-time knob catches it first
(rc 2, ``judge.timeout_s``).

**Mutations (each in its own throwaway copy, `-k timeout`, 21 tests):**

| planted | result |
|---|---|
| `opts={"timeout": v}; subprocess.run(cmd, **opts)` in `run_eval.py` | **RED ×3**, naming `harness/run_eval.py:2196 r5_splat_sink()` |
| new module `harness/r5newsink.py` with `import subprocess as sp; sp.run(..., timeout=v)` | **RED ×3**, naming `harness/r5newsink.py:4 go()` |
| `subprocess.Popen(cmd).communicate(timeout=v)` in `run_canary.py` | **RED ×3**, naming `harness/run_canary.py:332 r5_comm_sink()` |
| wrapper forwarding `timeout` two frames down in `guidance.py` | **RED ×3**, naming `harness/guidance.py:871 _r5_inner()` |
| delete the predicate from `run_agent` | **RED ×9** (the sink pin + 8 direct-call rows) |
| delete the predicate from `judge._run_judge_cli` | **RED ×9** |

**My own invented source, named in no report.** `run_agent`'s timeout rebound to
a JSON file inside the arm's own workspace —
`json.loads((workspace/".r5timeout.json").read_text())["t"]` — no fixture key,
no flag, no constant, no environment variable, nothing an inventory could name.
Head: **rc 2**, `` `run_eval.run_agent(timeout=)` must be a positive number of
seconds no greater than 2700 … got 2200000``, **0 CLI calls, 0 files under
`results/`**. The same fixture on the unmutated tree runs and writes
`transcripts/raw.json`, so the row really did reach the spawn. This is the
proof the check is at the sink.

## S-B-a-2 — where it holds and where it does not

**The half that holds (the sink).** `_run_suite` reads `SKILLS_EVALS_SUITE_CHILD`
before it spawns and writes it into the child's environment; `_spawn_suite` does
the same. Both are pinned by `ast` for read-before-spawn and for the marker
WRITE. Measured:

| mutation | result |
|---|---|
| delete the marker SET from `_run_suite` | **RED** — "`_run_suite` no longer writes $SKILLS_EVALS_SUITE_CHILD…" |
| delete the stand-down from `_run_suite` | **RED** — "spawns the whole suite and never reads $SKILLS_EVALS_SUITE_CHILD" |
| break the recogniser (`SUITE_RUNNER_NAME = "run_testsX.py"`) | **RED** on the vacuity floor |
| a NEW guarded forking test calling `_run_suite`, no pin edit | **GREEN** — the payoff, confirmed |
| a new test spawning the runner directly with `subprocess.run` | **RED**, naming `test_r5_direct_spawn` |

**The half that does not (the membership scan).** Eleven forking helpers
planted, each unguarded, each in its own throwaway copy:

| # | planted spelling | pin |
|---|---|---|
| f1 | `test/r5forkhelper.py`, module const `Path(__file__).parent / "run_tests.py"` | RED ✓ |
| f2 | `harness/r5fork.py`, `subprocess.Popen` | RED ✓ |
| f3 | `test/issues/r5helpers/__init__.py` (package in the discovery dir) | RED ✓ |
| f4 | `runpy.run_path(".../run_tests.py")` | green (declared out of scope) |
| f5 | in-process `run_tests.main()` | RED ✓ |
| f6 | `multiprocessing.Process(target=run_tests.main)` | RED ✓ |
| f7 | `python -m unittest discover test` | green (declared out of scope) |
| g10 | `os.system("python3 test/run_tests.py")` | RED ✓ |
| g8 | one-hop: helper in `harness/` takes the path as a parameter, caller in `test_issue_97.py` hands it `TEST_DIR / "run_tests.py"` | RED ✓ |
| **g7** | `NAME = "run_tests"` … `parent / (NAME + ".py")`, `subprocess.run` | **GREEN — miss** |
| **g6** | deep package `harness/propagation/r5deep.py`, f-string from two class attributes, `os.posix_spawn` | **GREEN — miss** |
| **g9** | `from run_tests import TEST_DIR, SUITE_RUNNER_NAME` … `subprocess.run([sys.executable, str(TEST_DIR / SUITE_RUNNER_NAME)])` | **GREEN — miss** |
| **g11** | `import run_tests` … `run_tests.TEST_DIR / run_tests.SUITE_RUNNER_NAME` | **GREEN — miss** |

g9 and g11 are the ones with teeth: they are the runner's **own committed
spelling**, lifted out of `_spawn_suite`
(`[sys.executable, str(TEST_DIR / SUITE_RUNNER_NAME), …]`) into another file.
`_names_the_runner` recognises a string constant containing `run_tests.py`, or a
name bound **in the same file** to something mentioning it; an imported name or
a module-qualified attribute is neither, so the scan concludes the call does not
name the runner and the function is not flagged. The failure is silent and open,
which is the property the round-4 report objected to.

I confirmed the fork is real rather than only unpinned: with g9's helper called
from a discovered test, `python3 test/run_tests.py -k R5Runaway` does not return
(killed at the 100 s bound) because the child is running the whole suite, and
running the same command with `SKILLS_EVALS_SUITE_CHILD=1` already set in the
parent forks **anyway** — i.e. the marker is inert for this path, so each
generation re-forks. I did not let it run to a second generation (a generation
is ~12 minutes), so I report the mechanism and not a process count.

## A-N4-2 — the discovery dir, by entry

`DISCOVERY_DIR.iterdir()`, asserted as "regular file matching
`test_issue_*.py`, or `__pycache__`". Rows, each in its own copy, `-k discovery_dir`:

| entry | pin |
|---|---|
| `colorsys/__init__.py` (package) | **RED** `['colorsys/']` |
| `colorsys.so` | **RED** `['colorsys.so']` |
| `colorsys.pth` | **RED** |
| `conftest.py` | **RED** |
| `__init__.py` | **RED** |
| `sub/test_issue_x.py` | **RED** `['sub/']` |
| symlink `colorsys.py -> /dev/null` | **RED** |
| `__pycache__/` | **GREEN** |
| committed tree | **GREEN** |

## F-1-N — the funnel

My own `ast` walk of `harness/guidance.py` and `harness/run_eval.py` for every
`<expr> / <expr>` join and every `Path(...)` call mentioning `guidance_dir`
returns **exactly one hit, `Path(guidance_dir)` at guidance.py:509, inside
`inside_checkout` itself**; `run_eval.py` builds none. So the funnel really is
the only way a path is built from the checkout — not a list of callers that all
happen to use it.

Rows, all through `run_eval.py main()` against hostile `_agent-guidance`
checkouts (marker file `OUTSIDE_SECRET_MARKER_R5`, an outside hook that
`touch`es a marker):

| row | rc | hook executed | marker in stdout | marker under `results/` | CLI calls |
|---|---|---|---|---|---|
| `agents-md/eval-coverage.yml` → symlink out | **2** named | no | no | 0 | 0 |
| `.claude/hooks/fleet-memory.sh` → symlink out | **2** named | **no** | no | 0 | 0 |
| `agents-md` itself a symlink out | **2** named | no | no | 0 | 0 |
| manifest row `file: ../out/secret.md` | **2** named | no | no | 0 | 0 |
| in-tree symlink out | **2** named | no | no | 0 | 0 |
| symlink CHAIN out | **2** named | no | no | 0 | 0 |
| symlinked DIRECTORY out | **2** named | no | no | 0 | 0 |
| absolute `file: /etc/hostname` | **2** named | no | no | 0 | 0 |
| `file: 5` | **2** named | no | no | 0 | 0 |
| `file: [ … ]` | **2** named | no | no | 0 | 0 |
| clean checkout (control) | 2 INCONCLUSIVE at the delivery guard — containment passed, the run reached the guard | — | — | — | — |

Direct calls: `_read(checkout, "../x.md")`, `"/etc/hostname"`,
`"agents-md/../../x"` → `GuidanceError` each; `assemble()` with a hand-built row
that never went through `load_manifest` → `GuidanceError` for the two traversal
spellings. Mutations: revert `_read` to a plain join → **RED**; drop the
`MANIFEST_REL` containment → **RED**, each naming the offending expression and line.

## A-N1-2 — the fixture container and `env:`

Through `main()`, argv log counted, `results/` counted:

| fixture | head | ref (`f9115ce`) |
|---|---|---|
| root is a list | rc **2** named, 0 CLI, 0 files | rc 1 `AttributeError: 'list' object has no attribute 'get'` |
| empty file (YAML `None`) | rc **2** named, 0 CLI, 0 files | rc 1 `TypeError: argument of type 'NoneType' is not iterable` |
| `env: {"A=B": x}` | rc **2** named, 0 CLI, 0 files | rc 1 `ValueError: illegal environment variable name` |
| `guard:` non-mapping | rc **2** named, 0 files | — |
| `judge:` non-mapping | rc **2** `invalid_judge_block`, report.md + summary.json written | — |
| `env:` non-mapping | rc **2** named, 0 files | — |
| `env: {"": x}` | rc **2** named | — |
| `env: {"A\n": x}` | rc **0** — **deliberate**: the rule is `execve`'s, which refuses only `=` and NUL; a newline is a legal name byte and the OS takes it | — |
| `env: {A: [1]}` / `{A: null}` | rc **0** — deliberate stringification, documented in `check_env_entry` | — |
| duplicate keys | rc **0**, last-wins silently (nit N3) | — |

`MappingFixtureKeyError` names the key it refused (`judge`, `guard`, `env`
measured). Reconciliation 5 both ways: `judge:` malformed **with** a usable
`skill:` → `invalid_judge_block` + `report.md` + one `summary.json`; with
`skill:` absent, non-string, or traversal-shaped (`../evil`) → the plain rc-2
configuration line and **nothing written**.

## A-N2-2 — an arm name against every path it becomes

`MAX_ARM_NAME_LEN` is derived (255 − len("skills-evals-") − 1 − 8 = **233**),
not a magic number. Through `main()` on the real guidance fixture:

| arm name | head | files written |
|---|---|---|
| `.` / `..` | rc **2** named | none |
| `report.md` | rc **2** named | none |
| `a`×234 / 256 / 4096 | rc **2** named ("at most 233") | none |
| `a`×233 | rc 2 INCONCLUSIVE (the run proceeds) | only under the timestamped run dir |
| `...` / `-` / `summary.json` / `transcripts` | accepted | only under the timestamped run dir, no collision with `report.md`, nothing above it |
| `--results-dir` | argparse refuses the *flag*; the name itself is a legal new directory | none |
| NFC and NFD `café` | refused by the character class | none |
| ref (`f9115ce`): `report.md` | uncaught `IsADirectoryError` after the arm had been spent | summary + transcripts already written |
| ref: `a`×234 | uncaught `OSError: [Errno 36] File name too long` from the workspace `mkdtemp` | — |

## A-N3-2 — the budget reads the harness

`_judge_branch_keys()` parses `_run_guidance_arm`'s `args.no_judge` branch. I
re-derived it independently: committed → `('judge_rubric',)`; with the harness
renamed to `judge_prompt` → `('judge_prompt',)`; with the aliased spelling →
`('judge_prompt', 'judge_rubric')`. The threshold I derived myself from
`eval.yml`: `timeout-minutes: 45` × 60 × 0.75 = **2025 s**. Committed
`_delivery`: 5 arms × (120 agent + 120 guard + 0 judge + 120 deliver) = **1800 s
< 2025** ✓. Planted: the renamed key **plus** a fixture declaring it and
`judge.timeout_s: 2700` → **RED at 15 300 s against 2 025 s**, on both the
renamed and the unrenamed harness — the A-N3 defect one key-spelling over, now
caught.

## The merge

**Union, reproduced independently.** Every `class` and top-level/`def test_*`
qualified name of `3fb20e1:<file>` and of `b583341:<file>`, against head:

| file | main | ref | union | head | missing | invented |
|---|---|---|---|---|---|---|
| `test/run_tests.py` | 1256 | 854 | 1302 | **1302** | 0 | 0 |
| `harness/run_eval.py` | 29 | 34 | 40 | 42 | 0 | 2 — `MappingFixtureKeyError`, `.__init__`, both added by the declared reconciliation 5 in `3c558a5` |
| `harness/scorers/judge.py` | 19 | 4 | 19 | **19** | 0 | 0 |
| `test/issues/test_issue_97.py` | 0 | 194 | 194 | **194** | 0 | 0 |
| `harness/guidance.py` | 0 | 26 | 26 | **26** | 0 | 0 |
| `test/fake-claude` (line-set) | 301 | 301 | — | 410 | 0 from either parent | 0 lines in neither parent |

**Hazard (a) — main's `8a99c19` judge-mode refusal.** Still true of the merged
runner: `judge: {mode: pairwise}` → rc **2** `judge_mode_unsupported: cannot
drive judge mode 'pairwise' yet…`, case-folded (`PAIRWISE` likewise), `absolute`
still runs; byte-identical message on `origin/main`. The widened pin is
load-bearing at **both** call sites: adding a `mode=` kwarg to `_run_arm`'s call
→ RED; adding it to `_run_guidance_arm`'s → RED. A `calls[0]` pin would have
missed the second.

**Hazard (b) — two allowlists, neither widened.** `_ALLOWED_ENV` (25 names) and
`_ALLOWED_ENV_PREFIXES` (4) are **byte-identical to `origin/main`'s**;
`PASSTHROUGH` and `EXTRA_PASSTHROUGH` are **byte-identical to `f9115ce`'s**.
Measured through the real functions under a 93-name hostile parent
(60 `HOSTILE_*` plus every runner/credential name):

```
skill arm    (18): ANTHROPIC_API_KEY CLAUDE_BIN CLAUDE_CONFIG_DIR GH_CONFIG_DIR
                   GH_TOKEN('') GITHUB_TOKEN('') HOME LANG LC_ALL PATH SHELL
                   SSL_CERT_FILE TERM TMPDIR TZ USER WORKSPACE XDG_CONFIG_HOME
guidance arm (11): ANTHROPIC_API_KEY CLAUDE_CONFIG_DIR(harness's) HOME(harness's)
                   LANG LC_ALL NODE_PATH PATH SHELL TMPDIR USER WORKSPACE
```

`ACTIONS_ID_TOKEN_REQUEST_TOKEN`, `ACTIONS_ID_TOKEN_REQUEST_URL`,
`ACTIONS_RUNTIME_TOKEN`, `AWS_SECRET_ACCESS_KEY`,
`GOOGLE_APPLICATION_CREDENTIALS`, `LD_PRELOAD`, `NODE_OPTIONS`, `BASH_ENV`,
`ENV`, `PYTHONSTARTUP`, `SSH_AUTH_SOCK`, `NPM_TOKEN` and all 60 `HOSTILE_*`:
**absent from both**. `check_env_block` refuses `""` and `A=B` at **both**
`agent_env`s; `HOME`/`TMPDIR`/`CLAUDE_CONFIG_DIR` in a fixture `env:` are
refused by name on the **guidance** path (`ISOLATION_NAMES`). `PATH`,
`LD_PRELOAD`, `NODE_OPTIONS`, `BASH_ENV` from a fixture's own `env:` are
**accepted on both paths** — exactly as round 4 recorded ("the owed skill-arm
allowlist follow-up, not this PR"); fixtures are committed, trusted content, so
this is a recorded limit rather than a regression.

**Hazard (c) — `$WORKSPACE`.** Both spellings expand, in
`run_eval.agent_env`, `guidance.agent_env` and `run_eval.expand()` (main's
version, used by `run_setup`): `$WORKSPACE/x` → `/tmp/WS/x`,
`${WORKSPACE}/y` → `/tmp/WS/y`, `bash ${WORKSPACE}/s.sh` → `bash /tmp/WS/s.sh`.
`$VAR` expands against the **allowlisted** environment, and an unknown `$NOPE`
is left literal.

**The five reconciliations, each load-bearing:**

| # | assertion | mutation | result |
|---|---|---|---|
| 1 | header ↔ both environments | add `R5_SNEAKY_NAME` to `_ALLOWED_ENV` | **RED** "'R5_SNEAKY_NAME' not found in …" |
| 1 | — | make `guidance.agent_env` return `{}` | **RED** "guidance.agent_env returned nothing" (the anti-vacuity guard) |
| 1 | — | rename `ACTIONS_RUNTIME_TOKEN` in the header | **RED** |
| 2 | `FAKE_CLAUDE_*` via the fixture `env:` | drop the `env:` merge from `run_eval.agent_env` | **RED** |
| 3 | every `judge.score` call pinned | add a kwarg at either call site | **RED** ×2 |
| 4 | sink row follows `score` → `_run_judge_cli` | delete the predicate from `_run_judge_cli` | **RED** ×9 |
| 5 | `invalid_judge_block` routing | both branches driven through `main()` | artifacts only when `skill:` is usable; otherwise plain rc 2, nothing written |

Each measures what its name says.

## Regression of rounds 1 → 4 — one measurement each

| round item | measurement | result |
|---|---|---|
| B1 gate rows | the workflow gate executed against 25 hostile inputs (table below) | all correct |
| **B0/S1 no real-HOME path** | `deliver()` and `guidance.agent_env()` instrumented in a copy to log every resolved `scratch`/`dest_dir`/`home`/`tmpdir`/`config_dir`, full suite run | **2055 logged paths, 0 under `/root`** — every one under `/tmp/…`; the instrumented suite itself ran **1184, OK (skipped=3)** |
| S2 run-wide snapshot | fired for real on my contaminated run, naming the file and both digests | live, not decorative |
| S3 discovery pin | `test_this_module_is_reachable_through_the_discovery_pattern` + the two runner pins present; `-k` reaching the discovered subtree pinned | present, green |
| S4 `PASSTHROUGH` exact | asserted equal to the committed tuple, `EXTRA_PASSTHROUGH == ()`; both byte-identical to `f9115ce` | unchanged |
| S5 no pipe into `grep -q` | the workflow gate uses a here-string (`grep -Fxq -- "$fixture" <<<"$committed"`) with the SIGPIPE reasoning in a comment; the only `\| grep -q` strings under `test/` are eval FIXTURE content, not harness code | held |
| A3 `delivery_failed` | present in `run_eval.py` ×2 and pinned ×4 in the test module | present |
| A4 decoy | `new_decoy_token` / `DECOY_PLACEHOLDER` wired through `guidance.py` (8) and `run_eval.py` (6); `guard_expectation` returns True for every mode, control included | present |
| A5 empty arms | `arms: {}` → rc **2** named; `arms: [a, b]` → rc **2** named | held |
| A6 header | reconciliation 1 above, three mutations red | held, rewritten |
| round-2 S1 knob ceiling | `timeout_s: 2701`, `guard.timeout_s: 2701`, `timeout_s: null`, `"600"`, `true` → rc **2** named each | held |
| N4-adv symmetric guard | `guard_expectation` is derived from the MODE, not the arm name; control arm two-sided in the committed fixture | held |
| S-A plural prompt | the guard prompt asks for every magic word (commit `5cec429` present in the merged `test/fake-claude` line-union) | held |
| S-B child guard | reconciliation table above; `_run_suite`'s read + write both pinned, both mutations red | held (scan half: finding SF-1) |
| N3-code NUL refusal | the workflow gate refuses a NUL leading, trailing and embedded, **before** any command substitution | held |
| N5/N6/N7-adv runner | full suite 1184 OK; `-k` narrowed banner printed; a `-k` matching nothing is rc 2 | held |
| round-4 S1-a, S-B-a, F-1, C-N2/3/4, A-N1…A-N4 | per-item table above | 6 of 7 closed |

No test present on `f9115ce` or on `origin/main` is missing from head (AST
union, 0 missing across all five files plus `test/fake-claude` by line-set), so
nothing from rounds 1–4 was dropped.

## Rule 19

`--arm objective-only` on head and on `$SP/mainx5` (`3fb20e1`), all 15 fixtures
present on both — including the three `adam-writing-style/*` and the two nested
`writing-adrs/*`. **Exit codes identical on all 15**, and the full stdout
(per-check JSON included) **byte-identical on all 15** after normalising the
tree root, `/tmp/…` paths, the run timestamp and `duration_ms`: `identical=15
differing=0`. `evals/guidance/_delivery` is head-only and exits **2**.

`evals/` differs from `f9115ce` in 60 files, and **every one of them is
byte-identical to `origin/main`** (checked file by file). The only two `evals/`
paths that differ from main are the PR's own
`guidance-bridge-canary/fixture.yaml` and `guidance/_delivery/fixture.yaml`, and
both are **unchanged since `f9115ce`**. So `evals/` differs only by what
`origin/main` brought.

## Merge state

| check | result |
|---|---|
| `3fb20e1` ancestor of head | **true** |
| `1530b51` ancestor of head | **true** (also `7c966ba`, `70148ab`, `b583341`, `f9115ce`) |
| `git merge-tree --write-tree origin/main 3c558a5` | rc **0**, clean |
| `harness/fakes/*` vs main | **byte-identical** (`gh`, `README.md`) |
| `harness/scorers/objective.py` vs main | **differs by 43 insertions** — the four S1-a-2 sink checks plus the `GIT_TIMEOUT_S` constant and the lazy-import preamble, added by `a397327`. The brief expected "byte-identical"; that expectation is stale, because S1-a-2 legitimately owns four sinks in this file. `harness/scorers/{invisibles,wrapping}.py` **are** byte-identical to main |
| every test main gained since `7c966ba` | present by name (0 missing) |
| commit authorship `f9115ce..head` | all `4205216+Adam-S-Daniel@users.noreply.github.com` |

## The one-way-door read

```
$ git diff --name-only f9115ce..3c558a5 -- .github/
.github/workflows/eval.yml
$ diff <(git show f9115ce:.github/workflows/eval.yml | grep -vE '^\s*#') \
       <(git show 3c558a5:.github/workflows/eval.yml | grep -vE '^\s*#') ; echo $?
0
# and with EVERY comment line stripped wherever it sits: 187 lines vs 187, equal: True
$ git diff --name-only origin/main..3c558a5 -- .github/
.github/workflows/ci.yml
.github/workflows/eval.yml
```

So `.github/` differs from `f9115ce` by **comment lines in `eval.yml` only**,
and from main by those two files only — as required.

| property | measured |
|---|---|
| every `uses:` a bare 40-hex SHA, no trailing comment | **yes** — 25 `uses:` directives across the repo, 24 of them a bare `@<40 hex>` with nothing after it; the 25th is `Adam-S-Daniel/cms-platform/.github/workflows/scheduled-run-health.yml@v0.1.87`, the documented own-account tag carve-out |
| `${{ }}` inside any `run:` | **zero**, in every workflow in the repo (parsed, not grepped) |
| `eval.yml` triggers | exactly `schedule` (`0 7 * * 1`) + `workflow_dispatch` (one input, `fixture`) |
| `eval.yml` permissions | `contents: write`, `id-token: write` — **identical to main's**, only the line numbers moved |
| push auth step-local | yes: the badge-commit step is the only one with `env: GITHUB_TOKEN` |
| all five checkouts | `persist-credentials: false`, including `_agent-guidance`, all pinned to the same 40-hex `actions/checkout` |
| fixture validation BEFORE the OIDC exchange | **yes** — parsed step order: step 9 "Select and validate the fixture to run", step 10 "Mint OIDC token and exchange…" |
| `concurrency` on a job publishing a required context | none — `eval.yml`'s `real-eval` group is workflow-level on a schedule/dispatch-only workflow, which publishes no PR status context; `ci.yml` has no `concurrency` at all |

**The rewritten security header, claim by claim, against the code.** Every
entry of `_ALLOWED_ENV` and every prefix family it names is in the header and in
the code (the reconciled test asserts this both ways, and my own comparison
agrees). The three runner tokens it names are out of reach for both arms —
measured above. "no GitHub write credential exists anywhere on the runner"
while the agent runs: the only credential-bearing step is the final badge
commit. The one claim I would qualify is under nit N1.

**The validation step's `run:` block, EXECUTED** under `bash` against a
synthetic tree (`evals/workflow-path-audit`, `evals/writing-adrs/bootstrap`,
plus a decoy directory), with a synthetic `$GITHUB_EVENT_PATH`:

| input | rc | message | `$RUNNER_TEMP/eval-fixture` | value echoed |
|---|---|---|---|---|
| `evals/workflow-path-audit` | 0 | `fixture: …` | `evals/workflow-path-audit`, key `workflow-path-audit` | it IS the committed path |
| `evals/writing-adrs/bootstrap` (nested) | 0 | — | written, key `writing-adrs/bootstrap` | — |
| `../etc` | **1** | names no committed fixture | **not written** | no |
| `evals/../../etc` | **1** | names no committed fixture | not written | no |
| `/etc/passwd` | **1** | names no committed fixture | not written | no |
| multi-line, valid line first | **1** | characters outside `[A-Za-z0-9/_.-]` | not written | no |
| multi-line, valid line second | **1** | characters outside … | not written | no |
| NUL leading / trailing / embedded | **1** | `contains a NUL byte` (checked on the event file, before any `$( )`) | not written | no |
| `*` / `[` | **1** | characters outside … | not written | no |
| spaces | **1** | characters outside … | not written | no |
| trailing slash | **1** | names no committed fixture | not written | no |
| `evals/workflow-path-audit/fixture.yaml` | **1** | names no committed fixture | not written | no |
| symlink to a committed fixture dir | **1** | names no committed fixture | not written | no |
| `$(id)` / `` `id` `` | **1** | characters outside … | not written | no |
| empty string | 0 | falls back to the default | default written | no |
| `inputs` absent / `inputs: null` | 0 | default | default written | no |
| `inputs.fixture: 5` | **1** | names no committed fixture | not written | no |
| `inputs.fixture: {…}` / `[…]` | **1** | characters outside … | not written | no |

**Nothing is minted or exported before a rejection**: every rejection is a
non-zero exit from step 9, and the OIDC exchange is step 10. No rejection
branch echoes the dispatched value; the only place the value is printed is the
`fixture: $fixture` success line, after it has been proven equal to a committed
path.

## Hollowness of every test new since `f9115ce`

By AST diff against **both** parents, head adds exactly **19** test methods —
18 in `test/issues/test_issue_97.py`, 1 in `test/run_tests.py`, 0 in
`test/test_propagation.py`:

| new test | why it is not hollow |
|---|---|
| `test_every_subprocess_timeout_sink_checks_the_value_before_it_spawns` | RED on 6 independent mutations (4 planted sinks, 2 deleted predicates), each naming file:line:function; carries its own anti-vacuity floor ("no subprocess timeout sink found anywhere") |
| `test_every_subprocess_timeout_sink_refuses_a_bad_value_before_it_spawns` | RED ×8 values per deleted predicate; drives each sink directly with a spawn counter |
| `test_every_subprocess_timeout_sink_accepts_an_ordinary_value` | positive twin; I reproduced it (600 spawns at every sink) |
| `test_a_sink_still_spawns_with_an_ordinary_timeout` | the floor that stops the two above passing by refusing everything |
| `test_a_source_no_inventory_row_names_is_still_refused_at_the_sink` | mutates a harness COPY and drives the real CLI; my own invented source (a workspace JSON file) reproduces its contract |
| `test_every_entry_in_the_discovery_dir_is_a_test_module` | RED on 7 planted entries, GREEN on `__pycache__`; two anti-vacuity floors |
| `test_the_checkout_funnel_is_the_only_way_a_path_is_built` | RED on both funnel mutations, naming the expression and line |
| `test_a_symlinked_manifest_cannot_be_read_from_outside_the_checkout` | I reproduced the row through `main()`: rc 2, no ids in stdout, nothing under `results/` |
| `test_a_symlinked_hook_is_never_executed_from_outside_the_checkout` | I reproduced it with a marker-writing outside hook: **marker absent** |
| `test_a_non_string_manifest_file_is_a_named_configuration_error` | red-first: `file: 5` / `file: [ … ]` are rc 1 `TypeError` on the ref |
| `test_read_refuses_a_relative_escape_when_called_directly` | direct call, `GuidanceError` reproduced |
| `test_a_fixture_whose_root_is_not_a_mapping_is_a_named_error` | red-first on the ref: `AttributeError: 'list' object has no attribute 'get'` |
| `test_require_mapping_refuses_a_non_mapping_fixture_directly` | red-first on the ref: `TypeError: argument of type 'NoneType' is not iterable` |
| `test_an_illegal_env_entry_is_a_named_error_before_any_cli_call` | red-first on the ref: `ValueError: illegal environment variable name` |
| `test_an_ordinary_env_block_and_an_absent_one_still_run` | the positive floor; reproduced (rc 0 with `env: {}` and with no `env:`) |
| `test_the_arm_name_refusal_covers_every_file_the_run_writes` | parses `run_eval.py` for write-opens and refuses any run-dir filename in neither tuple — a new report file cannot arrive unclassified |
| `test_the_arm_name_length_cap_is_the_workspace_prefixs_own_limit` | the cap is derived (233) and compared with the real `mkdtemp` prefix, not asserted against a literal |
| `test_a_colliding_or_overlong_arm_name_is_refused_before_anything_runs` | red-first on the ref: `IsADirectoryError` and `File name too long` |
| `test_every_committed_arm_name_is_still_accepted` | the positive floor; every committed arm name still accepted |

No new test is a tautology, and every one either fails on the ref through the
production entry point or has a named red mutation I ran myself.

## Findings

### SF-1 (should-fix) — the fork scan still enumerates spellings, and fails open

**Severity: should-fix. REPEAT: yes** — same defect, same severity and the same
class of fix as round-2 S-B → round-3 S-B-a → round-4 S-B-a-2, and it returns
through the brief's own remedy, which prescribed "rewrite the scan … flagging
every spelling the round-3 and round-4 reports list". That is an enumeration
again, one level up from the file globs it replaced: the trees ARE now walked
(that half is fixed and verified), but what the walk looks for is still a list
of ways to spell the runner's name, and an expression it cannot resolve is
treated as "not the runner".

**Reproducing inputs** (each a new file, each unguarded, each with the whole
`-k stands_down_in_a_child` pin GREEN):

```python
# test/r5const.py                                  ← g9
from run_tests import TEST_DIR, SUITE_RUNNER_NAME
def fork_it():
    return subprocess.run([sys.executable, str(TEST_DIR / SUITE_RUNNER_NAME)])

# test/r5modconst.py                               ← g11
import run_tests
def fork_it():
    target = run_tests.TEST_DIR / run_tests.SUITE_RUNNER_NAME
    return subprocess.run([sys.executable, str(target)])

# test/r5concat.py                                 ← g7
NAME = "run_tests"
def fork_it():
    return subprocess.run([sys.executable, str(Path(__file__).parent / (NAME + ".py"))])

# harness/propagation/r5deep.py                    ← g6
class _Where:
    BASE = Path(__file__).resolve().parent.parent.parent / "test"
    LEAF = "run_tests"
def fork_it():
    return os.posix_spawn(sys.executable,
                          [sys.executable, f"{_Where.BASE}/{_Where.LEAF}.py"], os.environ)
```

g9 and g11 are the runner's own committed spelling — `_spawn_suite` itself
writes `[sys.executable, str(TEST_DIR / SUITE_RUNNER_NAME), …]` — moved into
another file. `_names_the_runner` matches a string constant containing
`run_tests.py`, or a name/attribute bound **in the same module** to something
mentioning it; an imported name (`from run_tests import SUITE_RUNNER_NAME`) and
a module attribute (`run_tests.SUITE_RUNNER_NAME`) are neither, so the call is
not recognised as naming the runner and the function is never flagged. The scan
already tracks `import run_tests` for the in-process `run_tests.main()` case, so
the module IS resolved — just not for its constants.

I verified the consequence is a real fork and not merely a missing pin: with
g9's helper called from a discovered test module, `python3 test/run_tests.py -k
R5Runaway` never returns inside 100 s (the child is running the whole suite),
and it forks **even with `SKILLS_EVALS_SUITE_CHILD=1` already set in the
parent** — the marker is inert on this path, so each generation re-forks. I did
not run it to a second generation (≈12 minutes per generation) and so report the
mechanism rather than a process count.

**The fix I would make** — and it is the version that is true by construction,
in the round-4 reviewer's own phrase "not much more code": make the scan
**fail closed**. Flag every spawn of a Python interpreter (`sys.executable`, a
`python*` constant) anywhere under `test/`+`harness/` unless the scan can PROVE
the target is not the runner — i.e. resolve the argv expression to a constant
that does not name `run_tests.py`, and flag it when it cannot. The committed
tree has exactly **17** interpreter spawns across both trees; 15 of them resolve
to another script by an in-file constant and 2 are the declared spawners, so a
fail-closed rule has zero false positives today and catches g6, g7, g9 and g11.
Resolving `from run_tests import …` / `run_tests.<CONST>` against `run_tests`'s
own module-level bindings is the smaller, weaker alternative: it closes g9 and
g11 but leaves g7's concatenation and g6's f-string open.

**What this does NOT undermine:** the spawner half of the item is genuinely at
the sink — `_run_suite` and `_spawn_suite` each stand down on the marker before
spawning, both pinned by AST, both mutations red, and a new forking test routed
through `_run_suite` needs no guard of its own (measured GREEN with no pin
edit). The committed tree is correct and green. The gap is about a *future*
second spawner, which is exactly what the membership pin exists to prevent.

## Nits

**N1.** The rewritten header says "the guidance one is the narrower" allowlist.
Measured, neither list is a subset of the other: `NODE_PATH` is in
`guidance.PASSTHROUGH` and is in neither `_ALLOWED_ENV` nor any of its four
prefixes, so a guidance arm inherits one name a skill arm does not. Everything
else the sentence is doing (HOME/TMPDIR/CLAUDE_CONFIG_DIR are the harness's on
the guidance path) is true. One clause: "narrower except `NODE_PATH`".

**N2.** `inside_checkout(guidance_dir, rel)` still accepts a non-`str` `rel` and
raises `TypeError: unsupported operand type(s) for /` rather than a named
`GuidanceError`: `guidance._read(checkout, 5)` and `guidance.assemble(checkout,
{"file": 5}, "section", tok)` both reproduce it. Through the CLI this is
unreachable — `load_manifest` now type-checks `row["file"]`, which is what the
brief prescribed and what makes `file: 5` rc 2 — but the type check sits at the
loader (a source) while the containment sits at the funnel (the sink). One
`isinstance(rel, (str, os.PathLike))` line inside `inside_checkout` would make
the funnel total.

**N3.** A duplicated key in a fixture is silently last-wins:
`prompt: p` / `prompt: q` loads as `q` with rc 0 and no message. This is the same
class as the typo'd `objective_check:` the arm validator explicitly refuses
("would drop the arm's whole check list and still report green"). PyYAML
behaviour, pre-existing, cheap to close with a duplicate-key-refusing loader.

**N4.** `harness/scorers/objective.py` now does a module-scope
`sys.path.insert(0, <harness>)` so its four sinks can `import guidance` lazily.
That mutates `sys.path` for every process that imports the scorer, putting
`harness/` ahead of the stdlib. No collision today (no module under `harness/`
shares a stdlib name — I checked), but it is a global side effect of importing a
scoring module, and it is the same shadowing mechanic A-N4-2 exists to prevent
one directory over. A relative import, or the insert scoped to the function that
needs it, avoids it.

**N5.** `run_eval._git()` (main's code, used by `materialize_workspace`) calls
`subprocess.run` with **no `timeout=` at all**, so the seed-commit `git` calls
are bounded by nothing. The S1-a-2 invariant is stated over values that reach a
timeout, so this is outside it by construction and outside this PR's scope — but
the inventory's own subject is "the harness cannot hang", and a missing timeout
is the same hazard as an infinite one. Worth a row in a later round rather than
this one.

## Recorded (not findings)

* Fixture `env:` passes `PATH`, `LD_PRELOAD`, `NODE_OPTIONS`, `BASH_ENV`,
  `ENV`, `PYTHONSTARTUP` and friends through to the arm on **both** paths —
  identical to main's skill path, and round 4 recorded it as the owed skill-arm
  allowlist follow-up. Fixtures are committed, trusted content.
* `env: {"A\n": x}` and `env: {A: [1]}` are accepted deliberately: the predicate
  is `execve`'s rule (no `=`, no NUL, non-empty) on the stringified forms, which
  is documented in `check_env_entry` and is the correct boundary.
* The brief's expectation that `harness/scorers/objective.py` is byte-identical
  to main's is stale: S1-a-2 legitimately owns four sinks in that file (43
  insertions, commit `a397327`). `harness/fakes/*` and the other two scorers
  ARE byte-identical.
* `runpy.run_path` and `python -m unittest discover test` pass the fork pin and
  are declared out of scope by the brief; I did not re-measure whether they fork.

## What I could not measure

* The second generation of the g9/g11 runaway (each generation is a full ~12
  minute suite run). I established the fork happens and that the child-marker is
  inert for that path, which is the mechanism; I did not produce a peak process
  count.
* Whether `origin/main` would still be at `3fb20e1` at merge time — I read it
  once, at the start and the end of this review, and it did not move.

## Ledger

* `md5sum /root/.claude/CLAUDE.md`: **`935c291f2efb1ff55a463bccfde55e6a`** before my
  first command and **`935c291f2efb1ff55a463bccfde55e6a`** after my last —
  unchanged. Nothing was ever written under `/root/.claude`.
* `$SP/rev97e-code` at the end: all 13 named md5s match the brief, and
  `diff -rq` against a fresh `git -C /home/user/skills-evals archive 3c558a5 |
  tar -x` reports **byte-identical** (the only delta before I purged it was
  `harness/__pycache__` and `harness/scorers/__pycache__`, which I removed;
  no `results/` was left behind). `test/issues/` holds `test_issue_97.py` and
  nothing else. The throwaway archive was deleted.
* `/home/user/skills-evals` was used read-only throughout (`show`, `log`,
  `diff`, `archive`, `merge-tree`, `merge-base`); no branch, no commit, no push.
* Mutations lived under `$SP/r5mut97-*` (49 throwaway copies, each a tar
  extract or a copy of one, none carrying a `.git` and therefore none carrying
  an `origin`). All 49 are deleted, along with every scratch
  guidance checkout, synthetic tree and throwaway `HOME`.
* Processes I started: every suite and probe was tracked by resolving
  `/proc/<pid>/cwd` and filtering to my own paths; at the end **0** of mine
  remain. Concurrent runs by other agents (a worktree under
  `/home/user/skills-evals/.claude/worktrees/se-147`, and the adversarial
  reviewer) were excluded by that filter and never entered.
* No network, no real `claude`, no real `gh`, no credential read or copied,
  nothing posted to GitHub, no session/routine/reminder created.

## The one-line verdict for the orchestrator

Six of seven round-4 items, the merge, the three hazards and all five
reconciliations are closed and measured at the sink. **S-B-a-2's membership
scan is not**: it is still an enumeration of ways to spell the runner's name,
it fails open, and four planted spawners — two of them using `run_tests.py`'s
own published constants — walk past it with the pin green. Under this round's
stated rule that is a repeat, and a repeat is a should-fix, so this half of the
review is **NOT CLEAN**.
