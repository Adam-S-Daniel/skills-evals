## Fix round 3 — verifier output (worker)

Eleven commits on `claude/skills-evals-97`, `a6d165d..f9115ce`, one per item. `CLAUDE_CODE_EFFORT_LEVEL=xhigh`.

**STEP 0:** `origin/main` is still `7c966ba`, so there was nothing to merge. `git merge-base --is-ancestor 7c966ba a6d165d` is true.

| commit | item |
|---|---|
| `dcd23d2` | S1-a — bound every timeout source, not just the fixture knob |
| `8350a36` | S-B-a — pin the whole fork surface, not one spelling in one file |
| `a2c5b3c` | F-1 — guidance content is read only from inside the checkout |
| `f46bbd0` | C-N2 — the committed fixture sweep falsifies its own glob |
| `9fc2e2a` | C-N3 — both residual reasons in all three places |
| `26fd51a` | C-N4 — `assertTrue` over `assertIn` |
| `d7bda1f` | A-N1 — a present mapping-typed fixture key is a mapping |
| `53ca857` | A-N2 — an arm name must name a new directory |
| `91f074c` | A-N3 — the fit test counts every per-arm cost |
| `ec6bfea` | A-N4 — nothing but test modules in the discovery dir |
| `f9115ce` | record-only — `run_guard`'s "fatal to the pair" clause |

## Verifiers

| verifier | before (`a6d165d`) | after (`f9115ce`) | rc |
|---|---|---|---|
| `python3 test/run_tests.py` | Ran 788, OK (skipped=2) | **Ran 807 in 205.9s, OK (skipped=2)** | **0** |
| `python3 test/run_tests.py -k TestIssue97` | 102 of 788 | **`NARROWED RUN: -k selected 120 of 807`**, Ran 120, OK | **0** |
| `python3 test/test_propagation.py` | Ran 164, OK (skipped=1) | **Ran 164 in 4.5s, OK (skipped=1)** | **0** |

Environment: `HOME` and `SKILLS_EVALS_USER_MEMORY` both throwaway, `markdown-it-py==4.2.0`, siblings `_agent-guidance` `5f13def4288442a44f28473836819a29bd490944` and `agentskills` `cd5ad3e1e7c0dc2bee74b1d148bb7e80cfd61ffc`. Serial per checkout throughout. `md5sum /root/.claude/CLAUDE.md` = `935c291f2efb1ff55a463bccfde55e6a` before the first run and after the last — unchanged. No real `claude`, no real `gh`, no session/routine/reminder created.

### Rule 19 — every fixture, `--arm objective-only`, head vs `origin/main`

Compared by exit code **and** by each check's `(id, passed)` pair.

| fixture | rc main/head | checks | |
|---|---|---|---|
| `disarm-inherited-reach` | 1/1 | 9 | identical |
| `github-actions-sha-pinning` | 1/1 | 10 | identical |
| `guidance-bridge-canary` | 2/2 | 0 | identical |
| `post-failure-comment` | 1/1 | 12 | identical |
| `propagation` | 2/2 | 0 | identical |
| `rename-pdfs` | 1/1 | 8 | identical |
| `review-bash-ci-reliability` | 1/1 | 11 | identical |
| `windows-elevation-from-wsl` | 1/1 | 7 | identical |
| `workflow-path-audit` | 1/1 | 8 | identical |
| `writing-adrs/bootstrap` | 1/1 | 9 | identical |
| `writing-adrs/existing-convention` | 1/1 | 7 | identical |
| `guidance/_delivery` (guidance canary) | — / **2** | — | N-f, rc 2 as documented |

**11 of 11 identical**, and the guidance canary's objective-only run exits 2.

### Tree

```
$ git diff a6d165d..HEAD -- .github/ evals/
$                                    # empty — 0 bytes

$ git diff --stat origin/main..HEAD -- .github/
 .github/workflows/ci.yml   |  16 +++-
 .github/workflows/eval.yml | 195 +++++++++++++++++++++++++++++++++++++++---
 2 files changed, 200 insertions(+), 11 deletions(-)
```

Every commit `a6d165d..HEAD` is authored and committed by `4205216+Adam-S-Daniel@users.noreply.github.com`, and each one satisfies `git merge-base --is-ancestor <sha> origin/claude/skills-evals-97`.

## S1-a — the ceiling is a harness ceiling now (`dcd23d2`)

`MAX_TIMEOUT_S` and the predicate move to `harness/guidance.py`; `run_eval.py`, `run_canary.py` and `run_propagation.py` each run `guidance.check_timeout(args.timeout, ...)` in their own `main()` before anything else.

Rows through the real CLI entry point, `evals/workflow-path-audit --arm without_skill`:

| `--timeout` | a6d165d rc / last error line | head rc / first line |
|---|---|---|
| `2200000` | 1 — `OverflowError: timeout is too large` | **2** — ``configuration error: `--timeout` must be a positive number of seconds no greater than 2700`` |
| `1000000000` | 1 — `OverflowError: timeout is too large` | **2** — same |
| `2701` | **0** (accepted above the job budget) | **2** — same |
| `0` | **0** (swallowed by `args.timeout or …`) | **2** — same |
| `-1` | 2, but `Runner-level error in arm(s): without_skill` | **2** — same, named at parse time |
| `600` | 0 | 0 — unchanged |
| `2700` | 0 | 0 — unchanged |

`run_canary.py --timeout 2200000|2701|-1` → rc 2 named (`--timeout 60` unchanged); `run_propagation.py --timeout 2200000|2701|-1|0` → rc 2 named (`--timeout 120` → rc 0).

Test rows (`test_a_cli_timeout_override_is_held_to_the_same_ceiling`) go through `main()` in a bounded child with the ordinary probe CLI, so a rejection has to happen *before* the CLI. Red on a6d165d for all five:

```
AssertionError: True is not false : --timeout 2200000: the CLI was invoked
before the flag was checked — the override is validated before any subject
branch and before any CLI call
```

`test_a_cli_timeout_over_the_budget_does_not_reach_a_hanging_leg` (`--timeout 3000`, hanging scored leg) is red on a6d165d as the child's outer bound firing:

```
AssertionError: run_eval.py did not return inside 30s for … --timeout 3000
— a timeout knob reached subprocess.run() unchecked, which is the hang
validate_timeouts exists to prevent
```

### The AST inventory — 17 sites, each naming its validated source

`test_every_harness_subprocess_timeout_names_its_validated_source` parses every `harness/**/*.py`, resolves `import subprocess as sp` and `from subprocess import run as r`, and enumerates every `run/Popen/call/check_call/check_output` — plus `Popen.wait/communicate` — carrying `timeout=`. An unlisted site fails with its file and line; an empty inventory fails outright.

| file | function | call | `timeout=` | validated source |
|---|---|---|---|---|
| `harness/guidance.py` | `deliver` | `subprocess.run` | `timeout` | callee default `120` |
| `harness/propagation/account_store.py` | `git_tracked` | `subprocess.run` | `60` | literal |
| `harness/propagation/arms.py` | `_run_hook` | `subprocess.run` | `timeout` | flag: `run_propagation.py` |
| `harness/propagation/arms.py` | `arm_plugin_marketplace` | `subprocess.run` | `ctx.timeout` | flag: `run_propagation.py` |
| `harness/propagation/init_probe.py` | `probe` | `<popen>.wait` | `10` | literal |
| `harness/run_account_audit.py` | `registry_ref` | `subprocess.run` | `30` | literal |
| `harness/run_canary.py` | `claude_version` | `subprocess.run` | `30` | literal |
| `harness/run_canary.py` | `run_leg` | `subprocess.run` | `timeout` | flag: `run_canary.py` **and** knob `guard.timeout_s` |
| `harness/run_eval.py` | `_nested_repo_diff` | `subprocess.run` | `10` | literal |
| `harness/run_eval.py` | `run_agent` | `subprocess.run` | `timeout` | flag: `run_eval.py` **and** knob `timeout_s` |
| `harness/run_eval.py` | `run_setup` | `subprocess.run` | `timeout` | knob `setup_timeout_s` |
| `harness/scorers/judge.py` | `score` | `subprocess.run` | `timeout` | knob `judge.timeout_s` |
| `harness/scorers/objective.py` | `git_ref_unchanged` | `subprocess.run` | `10` | literal |
| `harness/scorers/objective.py` | `git_remote_url_is` | `subprocess.run` | `10` | literal |
| `harness/scorers/objective.py` | `git_worktree_list_matches` | `subprocess.run` | `10` | literal |
| `harness/scorers/objective.py` | `reaper_ran_in_standalone_repo` | `subprocess.run` | `10` (×2) | literal |

A `literal` row is checked to be positive and ≤ the ceiling; a `knob` row must be in `TIMEOUT_KNOBS` with `validate_timeouts(fixture, …)` still called in `main()`; a `flag` row must have `guidance.check_timeout` run on `args.timeout` in that module's own `main()` — all decided by parsing, so the table cannot become a comment. A second test enumerates the `--timeout` flags themselves (three today) so a fourth entry point cannot arrive unbounded.

**Mutation — drop the `run_eval` predicate:** `--timeout 2200000` returns to rc 1 + `OverflowError`, **and** the inventory goes red naming the site:

```
harness/run_eval.py run_agent() subprocess.run(timeout=timeout): is fed by
harness/run_eval.py's `--timeout`, and that module's main() no longer runs
guidance.check_timeout on `args.timeout` — the flag reaches subprocess.run
unbounded, which is the S1-a defect returning
```

**Other sources that reach the same sink, and why each is covered:** the 17 rows above are the complete enumeration, produced by the parse rather than by reading. Three `--timeout` flags existed under `harness/`, not one — `run_canary.py` (default 600) and `run_propagation.py` (default 120) had the identical unbounded `type=int`, and `run_canary.py --timeout 2200000` reproduced the same `OverflowError`. All three now share one predicate and one ceiling in `guidance.py` rather than three copies. `_git()` runs `subprocess.run` with no `timeout=` at all and so is not a timeout sink.

## S-B-a — the fork pin now covers the surface (`8350a36`)

`test_every_suite_forking_test_in_this_repo_stands_down_in_a_child` walks `test/run_tests.py` **and** every `test/issues/test_issue_*.py`.

Ten spellings planted unguarded, each in its own throwaway copy of the tree, running only the pin:

| spelling | old pin (a6d165d) | new pin |
|---|---|---|
| `subprocess.run([… str(TEST_DIR / "run_tests.py")])` | RED | **RED** |
| `subprocess.run([… str(RUNNER)])`, module constant | GREEN | **RED** |
| `subprocess.Popen([… "run_tests.py"])` | GREEN | **RED** |
| `os.system("python3 test/run_tests.py")` | GREEN | **RED** |
| `from subprocess import run as r3run; r3run([…])` | GREEN | **RED** |
| `subprocess.run("python3 test/run_tests.py", shell=True)` | GREEN | **RED** |
| `subprocess.check_call([… "run_tests.py"])` | GREEN | **RED** |
| a helper in ANOTHER `test_issue_*.py` module | GREEN | **RED** |
| a helper in the same module | GREEN | **RED** |
| a parameterised helper, `_spawn(RUNNER)` | GREEN | **RED** |

Each red names the function and its line, e.g. for the module-constant spelling:

```
AssertionError: False is not true : test/issues/test_issue_97.py:3017
test_probe() can spawn the whole suite but neither it nor any helper it
calls reads $SKILLS_EVALS_SUITE_CHILD (`self._skip_in_child()` is the
spelling both files use), so nothing bounds it when it IS the child: it
forks again, and again.
```

**Deleting `_skip_in_child()` from `test_planted_issue_module_is_discovered_and_fails_the_runner`** (in `test/issues/`, which the old pin never parsed): old pin **GREEN**, new pin **RED**, naming `test/issues/test_issue_97.py:238`.

**Committed tree — green, with the flagged set asserted by exact membership:**

```
test/issues/test_issue_97.py::_run_suite
test/issues/test_issue_97.py::test_an_ordinary_run_leaves_the_watched_file_alone
test/issues/test_issue_97.py::test_planted_issue_module_is_discovered_and_fails_the_runner
test/issues/test_issue_97.py::test_removing_the_planted_module_puts_the_runner_back_to_zero
test/issues/test_issue_97.py::test_the_run_wide_user_memory_guard_fails_a_run_that_writes_the_file
test/run_tests.py::test_dash_k_on_the_command_line_still_reaches_the_discovered_subtree
```

**The committed shape, pinned:** the guard is on the TESTS. `_run_suite` is the spawner and carries no guard of its own — it *sets* `SKILLS_EVALS_SUITE_CHILD` in the child's environment, which is the opposite — and each of the four tests that call it opens with `self._skip_in_child()`. A guard detector that counted any mention of the marker would have called the spawner itself guarded, so only a **read** counts (`os.environ.get`, `in os.environ`, `os.environ[…]`). Either shape is accepted: the assertion is that somewhere in a forking test's own call closure the marker is read.

**Other spellings/files/callers that reach the same sink, and why each is covered:** the file set is both files, not one. Import spellings: `subprocess`, `import subprocess as X`, and names bound by `from subprocess import … as …`. Call spellings: `run`, `Popen`, `call`, `check_call`, `check_output`, `os.system`, `os.posix_spawn*`, and any `os.spawn*`/`os.exec*` by prefix. Naming the runner: a literal (shell strings included, by substring), a module- **or class-level** constant bound to a string or a path expression containing `run_tests.py` (nit N5's blind spot), or handing such an argument to a same-module spawner. Reachability: transitive closure over same-module callees **and** across the parsed files, so a helper in another `test_issue_*.py` is caught. The one gap left is a helper in a module the walk cannot parse — which is exactly what A-N4's new assertion (`ec6bfea`) forbids from living in `test/issues/` at all; the two pins hold each other up, and the docstring says so.

One deviation from the brief, stated plainly: it asked to "refuse an empty flagged set PER FILE that has any subprocess use". Taken literally that would false-alarm on a future `test/issues/test_issue_NN.py` that spawns `run_eval.py` and never the runner — a common and legitimate shape (this file already does it 7 times). Instead the pin asserts **exact membership** of the flagged set, which is the stronger vacuity guard (a recogniser that stops seeing today's spellings goes red immediately, not only when every file empties) and never false-alarms, plus a per-file floor for the two files the known set names, plus a global non-empty refusal.

## F-1 — guidance content is read only from inside the checkout (`a2c5b3c`)

Direct reproduction, same probe on both trees — a manifest row `file: ../OUTSIDE_SECRET.md` naming an existing file with a `## Alpha` heading, a one-arm guidance fixture, `canary_loader` (the probe that echoes its loaded memory), `--delivery project`:

```
### a6d165d
rc=0
files under results/ carrying the outside marker:
  ['guidance/alpha/<ts>/a/summary.json', 'guidance/alpha/<ts>/a/transcripts/raw.json']

### head
rc=2
stdout: guidance configuration error: the guidance path '../OUTSIDE_SECRET.md'
        resolves to /tmp/…/OUTSIDE_SECRET.md, which is OUTSIDE the checkout at
        /tmp/…/checkout. …
files under results/ carrying the outside marker: NONE
```

Test rows through `main()`, both **rc 0 on a6d165d** (`AssertionError: 0 != 2`) and rc 2 here:

- `file: ../outside.md` with the file present → rc 2, message names `OUTSIDE the checkout` and the checkout root, does not echo the refused content, and nothing under `results/` carries the marker.
- an in-tree `file:` that is a **symlink** pointing out of the checkout → rc 2, same message (both sides are `.resolve()`d before the comparison).
- an ordinary in-tree row → rc 0, unchanged.
- the real 28-row `_agent-guidance` manifest → every row resolves inside the checkout and is a file.

**Mutation — drop the containment comparison:** both escape rows return to rc 0.

**Enumeration of the other guidance paths opened from manifest data:** `row["file"]` is the only one. `base.md`, `stub.md`, the manifest itself and `fleet-memory.sh` are module constants (`BASE_REL`, `STUB_REL`, `MANIFEST_REL`, `HOOK_REL`). The fixture's `section:` never becomes a path into the checkout — `find_row` matches it against `row["id"]` — and `_run_guidance` already refuses a `/`, `.` or `..` in it before it becomes a `results/` segment (`invalid section id …: it becomes a results/ path segment`). `scratch/payload.md`, `dest_dir` and `home` are harness-chosen and additionally covered by `_refuse_real_config_dir`. An **absolute** `file:` is the same hole spelled shorter (`Path("/x") / "/etc/passwd"` is `/etc/passwd`) and is refused by the same comparison. The check runs in two places: `load_manifest` (before any arm exists, so nothing — including the control's decoy — is delivered first, whatever the arm order) and `_read`, the funnel every guidance file read passes through, so a future caller cannot arrive around it.

### The two new clauses, verbatim

`harness/guidance.py` module docstring:

> WHERE THE CONTENT COMES FROM, and why that is a boundary. Guidance content is EXECUTED by the arm — that is the subject, and eval.yml's header states it as the trust boundary a guidance dispatch accepts — but the harness reads that content only from inside the `_agent-guidance` checkout it was pointed at: every manifest `file:` is resolved with its symlinks followed and refused if it lands outside (`inside_checkout` below). Before that, a row `file: ../OUTSIDE_SECRET.md` was read, delivered, and written into `results/.../transcripts/raw.json`, which main pushes to the public `eval-results` branch — so a row could publish any file the runner can read.

`DESIGN.md`, guidance section:

> Guidance content is **executed** by the arm — that is what the subject measures, and `eval.yml`'s header states it as the trust boundary a guidance dispatch accepts — but the harness **reads** that content only from inside the `_agent-guidance` checkout it was pointed at: every manifest `file:` is resolved with its symlinks followed and refused if it lands outside the checkout root. The two are different boundaries and the second is not implied by the first: a manifest row naming `../OUTSIDE_SECRET.md` was read, delivered, and written verbatim into `results/guidance/<key>/<ts>/<arm>/transcripts/raw.json`, which `main` pushes to the public `eval-results` branch — so a row could publish any file the runner can read.

Both are pinned by their operative words (`only from inside`, `trust boundary`, `eval-results`), red on a6d165d in both documents.

## Nits

### C-N2 (`f46bbd0`) — the committed fixture sweep falsifies its own glob

Measured on the committed tree: `glob '*/fixture.yaml'` → 9 dirs, **7** with a `skill:`; `glob '**/fixture.yaml'` → 12 dirs, **9**. The two extra are `evals/writing-adrs/bootstrap` and `evals/writing-adrs/existing-convention`, both nested skill fixtures the merge of main brought in — so the docstring saying `*` and `**` scored identically was false, and the committed half stayed green under the mutation because it asserted only `checked > 0`.

`_check_skill_fixtures` returns the directories it checked; the committed half asserts set-equality against an independent `os.walk` + `yaml.safe_load` (independent of both the helper's glob and `run_eval.load_fixture`). No count is hardcoded. Stale sentence deleted.

**Mutation `**` → `*` on the committed tree** — was green, now red:

```
AssertionError: Lists differ: […] != […]
  …/evals/writing-adrs/bootstrap
```

**Other spellings that reach the same sink:** `_fixture_dirs` is the single glob both halves share, so there is one spelling to falsify and both halves now do. The independent walk deliberately uses `os.walk`, not `rglob`, so a shared bug in one glob spelling cannot make both sides agree.

### C-N3 (`9fc2e2a`) — both residual reasons in all three places

DESIGN gave only the first reason, README gave none. Both now give both in their own wording, and the pin covers all three documents by the operative words `may report either` and `no token of its own`. Red on a6d165d in exactly three of six rows:

```
README.md does not carry 'may report either'.  …
README.md does not carry 'no token of its own'. …
DESIGN.md does not carry 'no token of its own'. …
```

`assertTrue`, not `assertIn`, so the failure names the missing phrase instead of dumping the document.

### C-N4 (`26fd51a`) — `assertTrue` over `assertIn`

With one `CHILD_RC_PINS` target renamed, the failure was **7938 bytes** of names before the custom message; it is **219** now. No new test — this changes only what a failure prints.

### A-N1 (`d7bda1f`) — a present mapping-typed fixture key is a mapping

Rows through `main()` in a bounded child. a6d165d → head:

| fixture | a6d165d | head |
|---|---|---|
| `guard: [1]` / `'x'` / `7` | rc 1, `AttributeError: 'list'/'str'/'int' object has no attribute 'get'` | **rc 2 named, no traceback** |
| `judge: [1]` / `'x'` / `7` | rc 0 (silently degraded) | **rc 2 named** |
| `env: [1]` / `'x'` / `7` | rc 1, `AttributeError: … has no attribute 'items'` | **rc 2 named** |
| `guard: null`, `judge: null`, absent | rc 0 | rc 0 — unchanged |

Zero CLI invocations (argv log absent) on every row whose fixture `env:` can carry the log, and nothing written under `--results-dir` on any of them.

**Mutation — restore `node = {}` in the parent walk:** the through-`main()` rows stay green (`validate_mapping_keys` catches them) and `test_validate_timeouts_itself_refuses_a_non_mapping_parent` goes red on all six of its rows — which is why that unit row exists.

**Other keys that reach the same sink:** enumerating every fixture key the harness reads as a mapping found the identical defect one key over, on `env:` (`(env_spec or {}).items()`), which is not a timeout parent at all — so `MAPPING_FIXTURE_KEYS` **derives** the knob parents from `TIMEOUT_KNOBS` (a new nested knob cannot arrive with an unchecked parent, pinned by `test_every_timeout_knob_parent_is_a_checked_mapping_key`) and lists `env` explicitly. `arms:` was already validated by `_validate_arms`; `objective_checks:` is read as a list, not a mapping.

### A-N2 (`53ca857`) — an arm name must name a new directory

Measured through `main()`, one arm per run, files written under `--results-dir`:

| arm | a6d165d | head |
|---|---|---|
| `.` | rc 0 — `guidance/alpha/<ts>/{report.md,summary.json,transcripts/raw.json}` | **rc 2 named, nothing written** |
| `..` | rc 0 — **`guidance/alpha/summary.json`** and **`guidance/alpha/transcripts/raw.json`** (one level above the run dir) | **rc 2 named, nothing written** |

Stated as the property rather than a blocklist: joined to a run directory and normalised the way the filesystem will, an accepted name is a direct child still called what it was called. `...` and `.hidden` pass; `.` and `..` do not. Every arm name the committed guidance fixtures declare (`with_guidance_section`, `with_guidance_stub`, `with_guidance_full`, `with_guidance_full_minus_section`, `without_guidance`) is read out of the fixtures and still accepted, as are `normal` and `none`.

**Mutation — drop the property check:** both rows return to rc 0.

**Other callers that reach the same sink:** `_validate_arm_entry` is the single gate every declared arm name passes through (`guidance_arms` → `_validate_arms` → here), and the ablation path builds its arm names from `MODES` rather than from fixture data. The `section:` id, the other fixture string that becomes a `results/` segment, is refused separately for `/`, `.` and `..` in `_run_guidance`.

### A-N3 (`91f074c`) — the fit test counts every per-arm cost

`_guidance_fixture_budget` counted 2 of 4. It now counts the hook delivery (`deliver(..., timeout: int = 120)`, a fixed per-arm cost with no override — round 3 measured a sleeping hook at 120.2 s), the agent leg, the guard probe, and the judge when the fixture declares a `judge_rubric:` — the key `_run_guidance_arm` itself branches on, and eval.yml passes no `--no-judge`.

| fixture | before | after | threshold |
|---|---|---|---|
| `evals/guidance/_delivery` (5 arms) | 5 × 240 = 1 200 s | **5 × 360 = 1 800 s** | 2 025 s — fits, 225 s headroom |
| planted 5-arm `judge.timeout_s: 2700` | 5 × 240 = 1 200 s, **GREEN** | **5 × 3 060 = 15 300 s, RED** | 2 025 s |

```
AssertionError: 15300 not less than 2025.0 : evals/guidance/_zz_judge_probe:
5 arms x (deliver + agent + guard + judge = 3060s) = 15300s does not leave
room inside eval.yml's 2700s job timeout …
```

`setup_timeout_s` is deliberately **not** counted and that is not a gap: `run_setup` is called from `_run_arm` and the objective-only branch only, never from the guidance path — asserted by parsing `_run_guidance_arm`, not from memory, and said in a comment. The arithmetic is pinned directly; that pin grafted onto a6d165d's helper is red (`AttributeError: 'TestIssue97' object has no attribute 'DELIVER_BUDGET_S'`).

Beyond the brief's enumeration I added `deliver`'s 120 s, because a budget that counts *some* of the costs is the defect A-N3 is about. It costs 600 s of the fixture's headroom and it still fits.

### A-N4 (`ec6bfea`) — nothing but test modules in the discovery dir

The shadowing, measured with `test/issues/colorsys.py` planted:

```
colorsys.__file__ after discovery: …/base/test/issues/colorsys.py
shadowed: True
```

and **a6d165d's full suite runs 788 tests and reports OK with it sitting there**. One assertion in `TestTheRunnerItself`, with a vacuity floor; red with the plant (`AssertionError: Lists differ: ['colorsys.py'] != []`), green on the committed tree. Because this is a test-only addition, its "before" state is that a6d165d permits the stray module silently — that green full-suite run is the red.

## Record-only

Unchanged, as instructed: `build_suite(discovery_dir=…)` leaving the scratch module in `sys.modules` and the dir on `sys.path` (its one caller restores both); `deliver()`'s 120 s bound not being `guard.timeout_s` and orphaning a grandchild; the plural prompt being a request rather than a guarantee; `test/issues/__pycache__` keeping `.pyc` for the two transiently planted probe modules; the ceiling anchor reading the `eval` job by name; a 1 MB dispatch value failing closed on `Argument list too long`; `EXTRA_PASSTHROUGH = ()`. The code half's nit N5 is subsumed by S-B-a (a path built from a module- or class-level constant is now recognised).

The one record-only item that asked for a wording change is `f9115ce`: `run_guard`'s docstring now says which half of "fatal to the pair" is dead (the comparison; rc 2, INCONCLUSIVE) and what survives (the clean partner's own `summary.json` with its `objective_checks`, a record of one arm rather than a score for the pair, and skipped past by CI's failed step). Docstring only, no behaviour change, no new test.

## Not done

Nothing in the brief was left undone, and no item needed a `.github/` edit. `git diff a6d165d..HEAD -- .github/ evals/` is empty.

---
_Generated by [Claude Code](https://claude.ai/code)_