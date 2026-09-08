## Fix round 4 — verifier output (worker)

`CLAUDE_CODE_EFFORT_LEVEL=xhigh`. Base `f9115ce` → head `b583341`. STEP 0: `origin/main` is still `7c966ba`, so there was nothing to merge.

Siblings: `_agent-guidance` `5f13def4288442a44f28473836819a29bd490944`, `agentskills` `cd5ad3e1e7c0dc2bee74b1d148bb7e80cfd61ffc`. `markdown-it-py==4.2.0`. Every run under a throwaway `HOME`/`SKILLS_EVALS_USER_MEMORY`, `PYTHONDONTWRITEBYTECODE=1`, serial per checkout.

### Suites

| verifier | before (`f9115ce`) | after (`b583341`) |
|---|---|---|
| `python3 test/run_tests.py` | **Ran 807**, `OK (skipped=2)`, rc **0** | **Ran 825**, `OK (skipped=2)`, rc **0** |
| `python3 test/run_tests.py -k TestIssue97` | 120 of 807 | **`NARROWED RUN: -k selected 138 of 825`**, `OK`, rc 0 |
| `python3 test/test_propagation.py` | 164, 1 skipped | **Ran 164**, `OK (skipped=1)`, rc **0** |
| `python3 test/run_tests.py -k NoSuchThingAtAll` | rc 2 | **rc 2**, `selected 0 of 825 tests` |

### One commit per item

| commit | item |
|---|---|
| `a397327` | S1-a-2 — the timeout ceiling at the subprocess sink |
| `8d443c3` | S-B-a-2 — the one spawner stands down itself; the scan walks the trees |
| `edb59e4` | A-N4-2 — the discovery dir checked by entry, not by `*.py` glob |
| `d0816be` | F-1-N — `inside_checkout` is the only way a path is built from the checkout |
| `8c6794a` | A-N1-2 — the fixture container and the `env:` entries |
| `a42f203` | A-N2-2 — an arm name checked against every path it becomes |
| `b583341` | A-N3-2 — the budget reads the judge key out of the harness |

### The sink / enumeration / invented-source triple, per item

**S1-a-2** — sink: every function under `harness/` that hands a value to a subprocess timeout, found by an `ast` walk of `harness/**/*.py` (**16**, not the review's six; the walk governs). Enumeration: `**` splats, positional `wait`/`communicate`, `import subprocess as sp`, `from subprocess import run as r`, a name assigned `subprocess.run` — all covered because the check is on entry to the function that spawns, whatever the caller passed. Invented source: **the process environment** — rebinding `run_agent`'s call site to `int(os.environ.get("SKILLS_EVALS_AGENT_TIMEOUT_S","600"))` (no fixture key, no flag, no literal, no callee default; the inventory key is unchanged). Every existing source-side pin GREEN on both trees; `f9115ce` rc 1 `OverflowError: timeout is too large`; head **rc 2 named, 0 CLI calls, nothing written**.

**S-B-a-2** — sink: the two spawners (`test_issue_97.py::_run_suite`, `run_tests.py::_spawn_suite`), membership exact over an `ast` walk of every `*.py` under `test/` and `harness/`. Enumeration: the round-3/4 spellings plus the in-process `run_tests.main()` / `multiprocessing.Process(target=run_tests.main)`, all covered because a caller cannot fork except through a spawner that has already checked. Invented source: **`test/fixtures/r4invented/tools/spawn_it.py`**, three levels down in a directory of non-Python fixtures, naming the runner through a module-level **tuple** constant unpacked at a `Popen` — RED, and demonstrably outside the round-3/4 file set.

**A-N4-2** — sink: `DISCOVERY_DIR.iterdir()`. Invented source: **`colorsys.cpython-311-x86_64-linux-gnu.so`**, the real tagged extension filename — it shadows stdlib `colorsys` after `build_suite()` (`ImportError: file too short`), `f9115ce`'s `glob("*.py")` rule is GREEN, the new one RED.

**F-1-N** — sink: `inside_checkout`, the only place `guidance.py` may turn `guidance_dir` into a path (pinned by `ast`). Invented source: **`agents-md` itself a symlink out**, relocating `MANIFEST_REL`/`BASE_REL`/`STUB_REL` through their shared parent, with the outside manifest's rows pointing at a file that resolves inside — on `f9115ce` the outside ids reach stdout; on head it is refused at the manifest.

**A-N1-2** — sink: `load_fixture` (all three CLIs) + `_require_mapping`, and `check_env_block` at both `agent_env`s. Invented source: **delete the load-time check** — the illegal `env:` is still rc 2 named with 0 CLI calls, from the function that builds the child's environment.

**A-N2-2** — sink: the arm-name gate, against every derived path. Invented source: **a name of 234–241 characters** — the arm DIRECTORY is creatable, the workspace prefix is not. `f9115ce` rc 1 `File name too long`; head rc 2 named; `a`*233 still rc 0 on both.

**A-N3-2** — sink: the judge branch key(s) parsed out of `_run_guidance_arm`. Invented source: a plain **rename** of the branch key (not an alias) — head RED at 15,300 s, `f9115ce` silently green.

### Rule 19 — `--arm objective-only`, head vs `7c966ba`

**11 of 11 identical** by exit code and by the full per-check JSON (after normalising tree roots and `/tmp` paths): `disarm-inherited-reach` 1/1, 9 · `github-actions-sha-pinning` 1/1, 10 · `guidance-bridge-canary` 2/2 · `post-failure-comment` 1/1, 12 · `propagation` 2/2 · `rename-pdfs` 1/1, 8 · `review-bash-ci-reliability` 1/1, 11 · `windows-elevation-from-wsl` 1/1, 7 · `workflow-path-audit` 1/1, 8 · **`writing-adrs/bootstrap` 1/1, 9** · **`writing-adrs/existing-convention` 1/1, 7**. `evals/guidance/_delivery` is head-only and exits **2** with the documented N-f message.

### One-way door

```
$ git diff f9115ce..HEAD -- .github/ evals/ | wc -c
0
$ git diff --name-only f9115ce..HEAD -- .github/ evals/
(empty)
$ git diff --stat origin/main..HEAD -- .github/
 .github/workflows/ci.yml   |  16 +++-
 .github/workflows/eval.yml | 195 ++++++++++++++++++++++++++++++++++++++++++---
$ git log --format='%ae %ce' f9115ce..HEAD | sort -u
4205216+Adam-S-Daniel@users.noreply.github.com 4205216+Adam-S-Daniel@users.noreply.github.com
```

`git merge-base --is-ancestor origin/main HEAD` true; `git merge-tree --write-tree origin/main HEAD` rc 0. Every one of the seven commits verified an ancestor of `origin/claude/skills-evals-97`.

### Ledger

`md5sum /root/.claude/CLAUDE.md` — `935c291f2efb1ff55a463bccfde55e6a` before the first command and after the last, 56099 bytes, **unchanged**. Background processes I started, counted by resolving `/proc/<pid>/cwd`: **0**. `test/issues/` holds `test_issue_97.py` and nothing else; the checkout is clean. No real `claude`, no real `gh`, no credential copied anywhere.

The fork runaway probe on the committed tree (own process group, 45 s bound, killed by pgid): **peak 2, 0 at the bound, 0 survivors**. With the marker WRITE deleted from `_run_suite`: **peak 3, still 3 at the bound** — the shape round 4 measured.

---
_Generated by [Claude Code](https://claude.ai/code)_