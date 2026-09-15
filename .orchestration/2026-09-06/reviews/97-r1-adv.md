FOUND — 1 blocker, 6 should-fix, 7 nit

# Round-1 adversarial review — `claude/skills-evals-97` @ `34ab8fc`

Scope: attack, not confirm. Every row below is a command I ran and its output.
Work dir `$SP/rev97a-adv` verified against `git show 34ab8fc:<path>` for all five
named files before I started, and proved byte-identical to a fresh
`git archive 34ab8fc` export afterwards (`diff -r` clean).

**Headline:** the harness itself is unusually solid — the markdown extent agrees
with all 28 manifest rows byte for byte, the payload identities are exact, the
guidance arm's environment is a real allowlist, every configuration error I
could construct exits 2 with a named message and no traceback, and Rule 19
holds byte-for-byte. The one blocker is in the shell of the key-bearing
workflow, not in the Python.

---

## Surface 1 — the dispatch input

Simulated the real step: the `run:` block extracted from `eval.yml` with
`yaml.safe_load`, executed under `bash` with a synthetic `$GITHUB_EVENT_PATH`
and `$RUNNER_TEMP`, `cwd` = a clean export of head.

| input | observed | verdict |
|---|---|---|
| *(no `inputs` — the schedule)* | rc 0, `eval-fixture=evals/workflow-path-audit` | OK |
| `evals/workflow-path-audit` | rc 0, key `workflow-path-audit` | OK |
| `evals/guidance/_delivery` | rc 0, key `guidance/_delivery` | OK |
| `../evals/workflow-path-audit` | rc 1, "names no committed fixture" | OK |
| `/tmp/x` | rc 1 | OK |
| `evals/workflow-path-audit/` (trailing slash) | rc 1 | OK |
| `evals/workflow-path-audit ` (trailing space) | rc 1 | OK |
| `evals/workflow-path-audit\t` / `\r` | rc 1 | OK |
| `./evals/workflow-path-audit` | rc 1 | OK |
| `evals//workflow-path-audit` | rc 1 | OK |
| `evals/guidance/../workflow-path-audit` | rc 1 | OK |
| `evals` / `evals/*` | rc 1 | OK |
| `""` / JSON `null` | rc 0 → default | OK (documented) |
| JSON number `12345`, array, object | rc 1 | OK |
| `evals/workflow-path-audit; touch /tmp/PWNED` | rc 1, `/tmp/PWNED` absent | OK |
| `$(touch …)` / `` `touch …` `` | rc 1, files absent | OK |
| unicode homoglyph `evals/workflow-path-аudit` | rc 1 | OK |
| **`"/etc/passwd\nevals/workflow-path-audit"`** | **rc 0**, `eval-fixture` = the whole 2-line string | **BLOCKER — B1** |
| **`"evals/workflow-path-audit\n$(id)"`** | **rc 0**, `eval-key` = `workflow-path-audit\n$(id)` | **BLOCKER — B1** |

Second half — the validated value vs the run value: `$RUNNER_TEMP/eval-fixture`
is written by the validation step and read only by the eval step; no step in
between writes it, so there is no TOCTOU inside the job. `eval-key` is
`${fixture#evals/}`, used only inside a quoted `git commit -m "$(cat …)"`, so it
cannot escape `results/` and cannot inject. `make_badge.py` is invoked with the
hard-coded `workflow-path-audit` and separately validates its own name
(see Surface 8). All clean.

Fleet-guidance shape (`printf | grep -Fxq` under `pipefail`) measured — see N1.

---

## Surface 2 — the security header, adversarially

Parsed all six workflows with `yaml.safe_load` and walked every step.

| check | observed | verdict |
|---|---|---|
| `${{ }}` inside any `run:` block, any workflow | **zero** | OK |
| `${{ }}` in `with:`/`env:` | only `github.token`, `secrets.GITHUB_TOKEN`, `github.event.*`, matrix/needs — all in `env:`/`with:`, never rendered into a script | OK |
| every `uses:` a bare 40-hex SHA, no trailing comment | 15/15 across all workflows | OK |
| new `_agent-guidance` checkout SHA == the SHA the file already uses for `actions/checkout` | `3d3c42e5aac5ba805825da76410c181273ba90b1`, same in `eval.yml` ×5 and `ci.yml` ×3 | OK |
| triggers | `eval.yml`: `schedule` + `workflow_dispatch` only | OK |
| `permissions` | unchanged: `contents: write`, `id-token: write` | OK |
| `concurrency` | unchanged (`real-eval`, `cancel-in-progress: false`); `eval.yml` has no `pull_request` trigger so it publishes **no required status context** — the "no group on a required check" rule does not bite. `ci.yml` (the required-check publisher) still has **no** `concurrency` at all | OK |
| `persist-credentials: false` | all five checkouts, incl. the new one | OK |
| push auth reach | `GITHUB_TOKEN` appears only in the final commit step's `env:` | OK |
| trust-boundary widening beyond `_agent-guidance` | none found in the diff | OK |
| header's claim "the **only** credential in reach [of the bypassPermissions agent] is the short-lived WIF token" | **false for the skill arm** — measured 18 env vars incl. `ACTIONS_ID_TOKEN_REQUEST_TOKEN` | **S6** |

---

## The env dump for both subjects

Fake CLI dumping `dict(os.environ)`, parent seeded with a deliberately dirty
environment (`ACTIONS_ID_TOKEN_REQUEST_TOKEN`, `ACTIONS_RUNTIME_TOKEN`,
`GITHUB_TOKEN`, `GH_TOKEN`, `AWS_SECRET_ACCESS_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`,
`RUNNER_TEMP`).

**GUIDANCE arm** (`evals/guidance/_delivery --arm without_guidance`) — 10 vars,
identical for the guard leg and the scored leg:

```
ANTHROPIC_AUTH_TOKEN = sk-ant-oat01-FAKE-BEARER
ANTHROPIC_BASE_URL   = https://api.anthropic.com
CLAUDE_CONFIG_DIR    = /tmp/skills-evals-without_guidance-2d36r139/config
HOME                 = /tmp/skills-evals-without_guidance-2d36r139/home
LANG, PATH, SHELL, USER
TMPDIR               = /tmp/skills-evals-without_guidance-2d36r139/tmp
WORKSPACE            = /tmp/skills-evals-without_guidance-2d36r139/ws
```

Nothing credential-shaped beyond `ANTHROPIC_*` (which the CLI needs); no
`ACTIONS_*`, no `GITHUB_TOKEN`, no AWS, no `CLAUDE_CODE_OAUTH_TOKEN`; HOME,
TMPDIR and CLAUDE_CONFIG_DIR all scratch. **The allowlist does what it claims.**
Cross-checked that a fixture cannot reach round it: `env: {AMBIENT:
"$SECRET_FROM_HOST"}` came back literal `$SECRET_FROM_HOST` (safe_substitute is
against the built dict, not `os.environ`) — the docstring's claim holds.

**SKILL arm** (`evals/workflow-path-audit --arm without_skill`) — 18 vars, the
whole ambient environment:

```
ACTIONS_ID_TOKEN_REQUEST_TOKEN = FAKE-OIDC-REQ-TOKEN     <-- OIDC minting credential
ACTIONS_ID_TOKEN_REQUEST_URL   = https://fake/actions
ACTIONS_RUNTIME_TOKEN          = FAKE-RUNTIME-TOKEN      <-- artifact/cache write
AWS_SECRET_ACCESS_KEY          = FAKEAWS
CLAUDE_CODE_OAUTH_TOKEN        = FAKE-CC-OAUTH
GH_TOKEN, GITHUB_TOKEN         = ghs_FAKE…
HOME = /root   (the runner's real HOME)
RUNNER_TEMP, CLAUDE_BIN, ANTHROPIC_*, LANG/PATH/SHELL/TMPDIR/USER, WORKSPACE
```

Pre-existing (`run_eval.agent_env` = `dict(os.environ)`, unchanged since main),
but see S6: this PR edits the very header paragraph that asserts otherwise, and
the guidance path now proves the harness knows how to build an allowlist.

---

## Surface 3 — contamination and isolation

| probe | observed | verdict |
|---|---|---|
| per-arm scratch | each arm a fresh `mkdtemp`; five distinct `/tmp/skills-evals-<arm>-XXXX/{ws,home,config,tmp}`; all removed in `finally` (`ls -d /tmp/skills-evals-*` → none) | OK |
| payload surviving arm→arm / trial→trial | no: config dir is per-arm and deleted | OK |
| `none` arm receives nothing | `deliver()` returns early; config dir contents `[]` (measured per mode: none `[]`, all others `['CLAUDE.md']`) | OK |
| `full-minus-section` lacks the section **and nothing else** | `fms == full[:start]+full[end:]` → True; `len(full)-len(extent)==len(fms)` → True; extent not in fms; heading line absent | OK |
| `stub` leaks the section? | heading in stub: False; id in stub: False; 6+-char word overlap with the section body: 5 generic words (`account, commit, protection, restated, secrets`) | OK |
| seed / fixture path leaking the section name | seed dir does not exist for `_delivery`; **the arm NAME is in the workspace path** (`/tmp/skills-evals-with_guidance_full-…/ws`), which Claude Code puts in its system prompt | N7 (pre-existing shape: main already does `skills-evals-{arm_name}-`) |
| writes to the real `~/.claude` | `_refuse_real_config_dir` refuses real HOME, real `~/.claude`, and a **symlink** to `~/.claude`; allows `~/.claude/sub` (unreachable — `dest_dir` is always `mkdtemp`) | OK |
| HOME unset | `os.path.expanduser("~")` falls back to `pwd` → still `/root` → still refused | OK |
| the hook's own env | `deliver()` builds `{PATH, HOME, TMPDIR, CLAUDE_CONFIG_DIR, FLEET_GUIDANCE_PAYLOAD}` from nothing; `fleet-memory.sh:59` honours `CLAUDE_CONFIG_DIR` before `$HOME/.claude`; `FLEET_GUIDANCE_SKIP` cannot leak in | OK |
| fixture `env:` re-pointing HOME / CLAUDE_CONFIG_DIR | **yes** — `env_spec` is applied last, so `env: {CLAUDE_CONFIG_DIR: /root/.claude, HOME: /root}` came back verbatim | N6 |
| `none` arm contaminated with a **stale token** | guard `ok=True`, arm **scored** | S4 |
| `none` arm contaminated with the **real fleet guidance** (no token) | guard `ok=True`, arm **scored** | S4 |

---

## Surface 4 — the guard

Hostile fake CLIs, each driving `evals/guidance/_delivery` for one arm.

| fake CLI | arm | rc | summary written? | verdict |
|---|---|---|---|---|
| honest (`guidance_probe`) | `with_guidance_section` | 0 | scored, guard ok, objective 1/1 | OK |
| honest | `without_guidance` | 0 | scored, guard ok (clean) | OK |
| **never echoes** (`guidance_blind`) | `with_guidance_section` | **2** | summary with `error.type=guard_miss`, `objective_checks: null` — **no score** | OK |
| **liar** (emits a well-formed but wrong token `AAAAAAAA-1111`) | `with_guidance_section` | **2** | `guard_miss` | OK — the token is `secrets`-random per run, so a liar cannot fake delivery |
| liar | `without_guidance` | 0 | scored clean (its guess is not the token) | OK |
| **exits non-zero** | `with_guidance_section` | **2** | `error.type=guard_error`, detail `nonzero_exit: boom` | OK |
| **hangs** (`guard.timeout_s: 3`) | `with_guidance_section` | **2**, elapsed 4 s | `guard_error … timeout: agent timed out after 3s` | OK |
| **hangs**, `guard: {timeout_s: }` (YAML null) | `with_guidance_section` | **never returned** (killed by my 20 s outer `timeout`, rc 124) | **S2** |
| token inside a **code fence** | `with_guidance_section` | 0 | scored — `token in reply` is a substring test | OK (deliberate) |
| token **split** (`ABCD EFGH-1234`) | `with_guidance_section` | **2** | `guard_miss` — fail-safe direction | OK |
| **echoes only on the 2nd call** | `with_guidance_section` | **2** | the guard is call #1 and gates the scored call | OK |
| `guard: {timeout_s: 0}` (attempt to skip the guard) | `with_guidance_section` | **2** | `guard_error … timeout after 0s` — cannot be skipped | OK |
| `guard: {timeout_s: "abc"}` | `with_guidance_section` | **1 + TypeError traceback** | `TypeError: unsupported operand type(s) for +: 'float' and 'str'` | **S2** |

**Can a lying agent turn a `none` arm into a scored `full`?** No — the arm's mode
is fixture-side, `guard_expectation` derives from the mode, and the token is
fresh per run.
**Does the probe contaminate the scored run?** It runs in the **same** workspace,
the same `CLAUDE_CONFIG_DIR` and the same env (measured from the argv log), but
each `claude -p` is a fresh session with no `--resume`/`-c`, all tools disallowed
on the probe, and the judge diff excludes `.claude`. No contamination found; the
probe's **cost is not counted** in the arm's `agent` block (N7).

---

## Surface 5 — the markdown extent

**Every manifest row, computed extent vs stored `bytes`:**

| rows | mismatches |
|---|---|
| 28 (21 in `base.md`, 7 under `sections/`) | **0** |

`working-in-these-repos 1366/1366 · anything-you-name-gets-its-link 2681/2681 ·
finding-your-unknowns 1520/1520 · workstation-layout 653/653 ·
sessions-get-cut-off 1152/1152 · security 493/493 · data-exposure-in-ci
2247/2247 · network-allowlists 1223/1223 · automation-vs-branch-protection
2483/2483 · two-github-connectors 4055/4055 · github-404-means-not-authorized
1787/1787 · fleet-spans-two-owners 2987/2987 · watch-finished-is-not-ci-passed
3988/3988 · git-push-does-not-mean-commit-exists 3026/3026 · dependency-updates
1086/1086 · name-becomes-scanner-data 3292/3292 · pinning-github-actions
3963/3963 · subagent-delegation 7761/7761 · skills-ecosystem 2612/2612 ·
two-setup-gaps 5615/5615 · git-practices 1393/1393 · section-{docker 604, dotnet
662, go 553, javascript 495, python 544, rust 555, typescript 526}` — all delta 0.

I read `_agent-guidance/scripts/check-guidance-coverage.js` and confirmed the
arithmetic is the same, including the documented off-by-one (`lines.length - 1`
loop, phantom trailing line). The JS counts in **bytes** (`Buffer.byteLength`)
and the Python in **characters**; both are internally consistent, and the
byte-length of the Python slice equals the JS `bytes` for all 28 rows — measured,
not assumed.

**Hostile markdown:**

| input | observed | verdict |
|---|---|---|
| `## ` inside a ``` fence | not a heading; folded into the parent extent | OK |
| `## ` inside a `~~~` fence | same | OK |
| `## ` in a 4-space indented code block | not a heading | OK |
| `## ` inside an HTML block | not a heading | OK |
| setext `H\n---` | recognised as h2 (CommonMark; matches the JS) | OK |
| closed ATX `## A ##` | heading text `A` (hashes stripped) | OK |
| 3-space indented `   ## A` | heading `A`, extent starts at the indent | OK |
| heading trailing space `## A ` | heading `A` | OK |
| heading case differs from the manifest | named `GuidanceError` naming `check-guidance-coverage.js` | OK |
| CRLF file | offsets align, heading `A` | OK |
| BOM at start | parsed | OK |
| last section in file (no trailing newline) | extent runs to EOF, no over-count | OK |
| two `##` with the same title | `GuidanceError: heading 'A' appears 2 times` | OK |
| manifest row whose heading no longer exists | `GuidanceError` for all of `section`/`full`/`full-minus-section`; **rc 2, no traceback, never a silent empty payload** | OK |
| manifest `[]` / `null` / a mapping / row missing `id` / row not a mapping / invalid YAML | `GuidanceError` in every case | OK |

---

## Surface 6 — per-issue test discovery

Baseline: `python3 test/run_tests.py` → **Ran 438 tests … OK (skipped=3)**, rc 0
(3 skips are `pypdf`/`agentskills`, none guidance).

| attack | observed | verdict |
|---|---|---|
| module that fails to **import** | 439 tests, `FAILED (failures=1, errors=1)`, rc 1 | OK — loud |
| module with a **syntax error** | 439, `FAILED`, rc 1 | OK — loud |
| module defining **no tests** | 438, OK | OK |
| **two** modules with the same class name (one fails) | 440, `FAILED (failures=2)` — both ran, no shadowing | OK |
| class name **colliding with one already in `run_tests.py`** (`TestIssue82`) | 439, OK — both ran, no double-count | OK |
| a well-formed new issue module | 439, OK — **additive, touches no shared file** (the point of the change) | OK |
| discovered module's context | `cwd` = repo root, `test/` on `sys.path`, `Path(__file__).parents[2]` = repo root — same as the in-file classes | OK |
| count line | one total, always | OK |
| **`python3 test/run_tests.py -v`** | **Ran 379 tests … OK** — 59 tests silently dropped, `grep -c TestIssue97` = **0** | **S1** |
| `python3 test/run_tests.py --failfast` | **379 … OK** | **S1** |

---

## Surface 7 — Rule 19 (skill fixtures byte-identical, head vs `mainx2`)

`--arm objective-only`, every committed fixture, stdout diffed:

| fixture | head rc | main rc | stdout |
|---|---|---|---|
| github-actions-sha-pinning | 1 | 1 | identical |
| guidance-bridge-canary | 2 | 2 | identical |
| post-failure-comment | 1 | 1 | identical |
| propagation | 2 | 2 | identical |
| rename-pdfs | 1 | 1 | identical |
| windows-elevation-from-wsl | 1 | 1 | identical |
| workflow-path-audit | 1 | 1 | identical |

Full `--arm both` on `workflow-path-audit` with a stub registry so the agent is
really invoked (2 CLI calls per run), three trees:

* `main` vs `head` (no `--guidance`): `summary.json` **identical field for
  field** (only the run's own timestamp directory differs), `report.md`
  identical, and the **argv + full environment handed to the CLI identical**
  (only `CLAUDE_BIN`, which I set differently per run).
* `head` without `--guidance` vs `head` **with** `--guidance ../_agent-guidance`:
  identical on all three. The flag eval.yml now always passes is inert for a
  skill fixture.

Rule 19 **holds**.

---

## Surface 8 — everything else

| probe | observed | verdict |
|---|---|---|
| exit-code table: 20 distinct configuration errors (missing checkout, non-guidance dir, unknown section id, section with `/`, section `..`, missing/int `section:`, unknown mode, typo'd arm key, `with_*`+`mode: none`, `without_*`+`mode: full`, arm name with `/`, `arms:` a list, `--arm` naming no arm, `--ablation` with no `ablation:`, missing `prompt:`, unknown `subject:`, guidance arm on a skill fixture, manifest variants) | **rc 2 with a named message in all 20; zero tracebacks** | OK |
| `make_badge.py` hostile names (`guidance/../../etc`, `../escape`, `/abs`, `a/b/c`, `guidance/`, `""`, `.`, `..`, `guidance/.`, `guidance/..`, `guid ance`, `a\nb`, `guidance/sec;rm -rf /`) | all `ValueError` from `_validate_name`, raised **before** `--out` is derived | OK |
| results path from a section id containing `/`, `..`, `.` | rejected at `_run_guidance` before `key` is used | OK |
| unicode section id | `run_eval` accepts, `make_badge` rejects (`guidance/sécurité`) — inconsistent validators, unreachable today (all manifest ids are ASCII) | N7 |
| budget arithmetic vs the 45-min job timeout | `(120+120)×5 = 1200 s` < `2025 s` (0.75 × 2700); a real test pins it (`test_issue_97.py:1203`) | OK |
| concurrency of two arms in one process | none — arms run sequentially in a list comprehension, no threads | OK |
| `arms: {}` / `[]` / `null` | silently runs the **default** `section`/`none` pair | **S5** |
| `--arm objective-only` on a guidance fixture | `{"checks": []}`, **rc 0** over zero checks | **N4** |
| `harness/run_eval.py` without markdown-it-py | rc 1, bare `ImportError` traceback, **even for `--arm objective-only` on a skill fixture** | **N5** |
| `run_propagation.py` / `run_account_audit.py` / `run_canary.py` / `make_badge.py` / `test_propagation.py` without markdown-it-py | all rc 0 — `propagation.yml`'s `pip install pyyaml` is still sufficient | OK |
| `markdown-it-py` installed version | 4.2.0, matching both pins | OK (publish date not verifiable offline) |

---

# Findings, ranked

## BLOCKER

### B1 — a multi-line dispatch value defeats the fixture gate, and the token is minted anyway
`.github/workflows/eval.yml:233`

`grep -F` treats **each line of the pattern** as a separate pattern, so a
two-line `fixture` value passes whenever *either* line names a committed
fixture. Nothing in the step rejects a newline first.

```
$ python3 drive.py     # step's own run: block, executed under bash
input='/etc/passwd\nevals/workflow-path-audit'  rc=0
   eval-fixture: '/etc/passwd\nevals/workflow-path-audit'
   eval-key    : '/etc/passwd\nevals/workflow-path-audit'
input='evals/workflow-path-audit\n$(id)'  rc=0
   eval-fixture: 'evals/workflow-path-audit\n$(id)'
   eval-key    : 'workflow-path-audit\n$(id)'

$ printf 'evals/workflow-path-audit\nevals/guidance/_delivery\n' \
    | grep -Fxq -- $'/etc/passwd\nevals/workflow-path-audit' && echo MATCH
MATCH
```

**Impact, stated honestly:** no shell injection (every use of `$fixture` and
`$eval_key` is quoted — I confirmed `$(…)`, backticks and `;` are all inert), no
code execution, and no fixture outside the committed set can ever *run*
(`Path("a\nb")` names no directory, so `run_eval.py` dies). What is defeated is
the **ordering guarantee**, which is the whole reason the step exists and is
stated twice in the file:

> `eval.yml:46-48` — "so anything that names no committed fixture fails the step
> **BEFORE the token exchange runs**"
> `eval.yml:213-215` — "a dispatch naming a fixture that does not exist must fail
> here, **with no credential minted and nothing spent**"

Both are false for a multi-line value: the OIDC exchange runs, a real
`sk-ant-oat01` bearer is minted, the WIF preflight burns a haiku call, and only
then does the job fail with a confusing "no such fixture.yaml". On the workflow
whose header is the artifact reviewers trust, a security control that does not
do what the comment beside it says should not merge — especially when the fix is
two lines and the behavioural test harness already exists.

I am calling this a blocker on the strength of the header claim and the
one-way-door framing; a reviewer who reads the ordering as advisory can
reasonably downgrade it to should-fix. Either way it should not ship unfixed.

**Fix** (reject a non-single-line value before matching, and keep the here-string
from N1):

```bash
case "$fixture" in
  *[!A-Za-z0-9/_.-]*)
    echo "eval.yml: dispatch input 'fixture' has characters outside [A-Za-z0-9/_.-]: $fixture"
    exit 1 ;;
esac
committed="$(find evals -mindepth 1 -name fixture.yaml -printf '%h\n' | sort)"
if ! grep -Fxq -- "$fixture" <<<"$committed"; then
```

**Test** — one line, in the tuple that already exists at
`test/issues/test_issue_97.py:1015`; that test already executes the real step
under bash (good design — it just missed this value):

```python
for bad in (..., "evals/workflow-path-audit\nevals/guidance/_delivery",
                 "/etc/passwd\nevals/workflow-path-audit"):
```

---

## SHOULD-FIX

### S1 — any argument to `test/run_tests.py` silently drops all 59 discovered tests and still prints OK
`test/run_tests.py:6092`

```
$ python3 test/run_tests.py           ->  Ran 438 tests ... OK (skipped=3)
$ python3 test/run_tests.py -v        ->  Ran 379 tests ... OK (skipped=3)
$ python3 test/run_tests.py --failfast->  Ran 379 tests ... OK (skipped=3)
$ python3 test/run_tests.py -v 2>&1 | grep -c TestIssue97   ->  0
$ grep -c 'def test_' test/issues/test_issue_97.py          ->  60
```

The comment at 6087-6091 anticipates the *targeted-class* case
(`run_tests.py SomeClass.test_x`) but the same branch swallows **flags**, and
`-v` is the single most common way a person runs a suite. CI is fine (no-arg),
so this cannot ship a broken `main` — but it is a green light wired to a
smaller denominator, and it gets worse with every issue module added. Same
shape as the `python3 path/to/test_foo.py` hollow-verifier incident in the fleet
guidance.

**Fix:** take the `unittest.main` branch only when an argument does not start
with `-`; otherwise still run `build_suite()` and map `-v`/`-q` to `verbosity`.
Pin it with a test that runs the suite twice (`[]` and `["-v"]`) and asserts the
same `testsRun`. Note `return 0` at 6094 is unreachable today (`unittest.main`
exits) — it would become a silent always-zero if anyone ever added `exit=False`.

### S2 — `guard: {timeout_s: }` removes the guard timeout entirely; a non-numeric value is a traceback
`harness/run_eval.py:809`

```python
timeout=(fixture.get("guard") or {}).get("timeout_s", 300))
```

`.get(key, default)` does not apply the default for an **explicit YAML null**, so
`guard:\n  timeout_s:` yields `None`, and `subprocess.run(timeout=None)` waits
forever. Measured against a hanging fake CLI:

```
### nullguard [with_guidance_section] rc=124 elapsed=20s   (my outer kill fired; the harness never timed out)
### shortguard (timeout_s: 3)         rc=2  elapsed=4s     guard_error ... timeout after 3s
```

In CI the only backstop is the 45-minute job timeout, which kills the job with no
summary and no artifact. And a string value bypasses the `GuidanceError`
contract entirely:

```
### strguard (timeout_s: "abc") rc=1
TypeError: unsupported operand type(s) for +: 'float' and 'str'
```

**Fix:** coerce and validate once, in the fixture loader —
`_positive_int(fixture.get("guard", {}).get("timeout_s") or 300)` — and raise
`GuidanceError` (rc 2) for anything non-numeric or ≤ 0. The same YAML-null hole
exists for the agent leg (`fixture.get("timeout_s", 600)` → `arm["timeout"] =
None`), but that one is pre-existing on `main:525`; fixing both together is
cheap.

### S3 — `deliver()["installed"]` is computed and thrown away, so a silent delivery failure costs a paid API call and reports the wrong cause
`harness/guidance.py:395` → `harness/run_eval.py:794-814`

`deliver()` already computes free, deterministic, offline proof that the marked
block reached the config dir. `_run_guidance_arm` records `hook_verdict` but
**never reads `installed`** — it is not in `extra`, so it is not even in the
summary for post-hoc diagnosis:

```
$ grep -n "installed" harness/run_eval.py
  (never referenced in run_eval.py)
```

Repro with a hook that prints a plausible verdict and writes nothing:

```
$ # sabotaged fleet-memory.sh: echo "fleet-guidance: current"; exit 0
  deliver() -> {'bytes': 55980, 'verdict': 'fleet-guidance: current',
                'installed': False, 'dest': '…/cfg/CLAUDE.md'}
```

The run then spends a real guard call and reports `guard_miss` — *"this arm was
not delivered what its mode says (or something else already had been)"* — the
ambiguous message, for the one case that is unambiguous and free to detect.
`deliver()` also never inspects `proc.returncode`, so a hook that exits non-zero
is indistinguishable from one that succeeded.

**Fix:** in `_run_guidance_arm`, before `run_guard`, fail the arm with a distinct
`delivery_failed` error (rc 2) when `arm["mode"] != "none"` and not
`info["installed"]`; put `installed` and the hook's returncode in `extra` either
way.

### S4 — the control arm's guard is vacuous: a `none` arm contaminated with anything but *this run's* token is scored as clean
`harness/guidance.py:12-20` and `439-466`

The module's thesis (lines 12-16) is that on a machine carrying the fleet hook
"the real `~/.claude/CLAUDE.md` already IS the guidance", and the magic-token
guard is what catches it. But `mode: none` delivers **nothing at all** (measured:
its config dir contents are `[]`), so the control arm's guard can only ever
answer "no magic word" — which is exactly what it answers when it *is*
contaminated, because a contaminating source never carries this run's fresh
token. Measured, with `FAKE_CLAUDE_AMBIENT_MEMORY` standing in for a real
`~/.claude/CLAUDE.md` the config dir does not control:

```
### contaminated-none (ambient file carrying a STALE token)   rc=0
     without_guidance mode none | err None | guard.ok True obs False | objective [True]
### contaminated-real-none (ambient file = the real base.md)  rc=0
     without_guidance mode none | err None | guard.ok True obs False | objective [True]
```

What actually protects the control arm is the HOME/`CLAUDE_CONFIG_DIR` scratch
isolation, which is genuinely solid (Surface 3) — not the guard. For the
five-arm canary a total isolation failure is still caught, because the four
treatment arms go INCONCLUSIVE and the run exits 2. For the **default two-arm
pair** (`with_guidance: section` / `without_guidance: none`), which is what every
future behavioural guidance fixture will use, a contaminated control plus a
working treatment arm produces precisely the "null delta that reads as *the
guidance does nothing*" the module was written to prevent — with both guards
green.

**Fix:** make the control arm's guard non-vacuous. Deliver a **decoy** into the
`none` arm's own config dir — a second fresh token in an otherwise empty marked
block — and require the control's probe to report the decoy (proving user memory
is being read at all in that arm) while not reporting the treatment token. That
turns "clean" from an unfalsifiable answer into a two-sided one. Failing that,
soften the docstring so it claims what it delivers.

### S5 — `arms: {}` silently runs an experiment the fixture never declared; the guard written for that case is dead code
`harness/run_eval.py:728-731`

```python
declared = fixture.get("arms") or DEFAULT_GUIDANCE_ARMS
if not isinstance(declared, dict) or not declared:
    raise guidance.GuidanceError("`arms:` must be a mapping of arm name -> {mode: ...}")
```

`X or DEFAULT` means `declared` is never falsy, so `not declared` can never fire.

```
$ python3 -c '... run_eval.guidance_arms(fx,"both") ...'
  arms: {}         -> ['with_guidance=section', 'without_guidance=none']
  arms: null       -> ['with_guidance=section', 'without_guidance=none']
  no arms: key     -> ['with_guidance=section', 'without_guidance=none']
  arms: []         -> ['with_guidance=section', 'without_guidance=none']
```

`arms:` with nothing under it is a plausible YAML edit, and it silently runs two
arms the fixture does not declare, scoring and badging them under the fixture's
name. (`arms: [a]` is correctly rejected — the reachable half of the check
works.)

**Fix:** `declared = DEFAULT_GUIDANCE_ARMS if "arms" not in fixture else fixture["arms"]`,
then validate — so an *absent* key defaults and an *empty* one errors.

### S6 — the skill arm still inherits `ACTIONS_ID_TOKEN_REQUEST_TOKEN`, and this PR edits the header that says otherwise
`harness/run_eval.py:355`; `.github/workflows/eval.yml:84-89`

The header paragraph this PR touches (four→five checkouts) reads:

> "While the bypassPermissions agent is running, no GitHub write credential
> exists anywhere on the runner — **the only credential in reach** is the
> short-lived WIF-derived access token (and the single-use OIDC token file)"

Measured (env dump above): the skill arm's agent gets 18 variables including
`ACTIONS_ID_TOKEN_REQUEST_TOKEN` + `ACTIONS_ID_TOKEN_REQUEST_URL` — with
`id-token: write` that mints a GitHub OIDC assertion for **any audience**,
including re-running this workflow's own Anthropic exchange — and
`ACTIONS_RUNTIME_TOKEN` (artifact and cache write for the run). Literally the
sentence says *write credential*, and these are not that; but "the only
credential in reach" is false as written.

Pre-existing (`agent_env` is unchanged from `main`), so this is not a regression
— but the guidance path added by this very PR proves the harness knows how to
build an allowlist, and the contrast between the two subjects is now stark.

**Fix (cheapest):** correct the header sentence to name what is in reach.
**Fix (right):** point `run_eval.agent_env` at `guidance.agent_env`'s allowlist —
they already agree on `PATH/LANG/LC_ALL/SHELL/USER/NODE_PATH` + `ANTHROPIC_*` +
`WORKSPACE` — and keep the fixture `env:` overlay. Do it as its own PR, with a
Rule-19 comparison, not inside #97.

---

## NIT

### N1 — `printf | grep -Fxq` under `pipefail` is the forbidden shape; safe today, measured
`.github/workflows/eval.yml:233`. The fleet guidance forbids piping into a
command that exits early. Measured with 20 trials per size, the match on the
**first** line:

| list bytes | entries | false negatives |
|---|---|---|
| 209 (today, 8 fixtures) | 8 | 0/20 |
| 35,022 | 1,001 | 0/20 |
| 65,472 | 1,871 | 0/20 |
| **66,522** | **1,901** | **1/20** ← first appearance, at the 64 KiB pipe capacity |
| 70,022 | 2,001 | 3/20 |
| 77,022 | 2,201 | 15/20 |
| 91,022 | 2,601 | 20/20 |

So: **size-safe today** and for ~1,900 fixtures. **The here-string spelling is
required** by the fleet rule and fixes the race (`grep -Fxq -- "$m"
<<<"$committed"`: 0/20 false negatives at 140 KB) — but note it does **not** fix
B1; those are two independent defects in one line.

### N2 — "committed" is really "present on disk"
`.github/workflows/eval.yml:232`. `find` is not `git ls-files`:

```
$ mkdir -p evals/untracked-fixture && echo 'skill: x' > evals/untracked-fixture/fixture.yaml
$ find evals -mindepth 1 -name fixture.yaml -printf '%h\n' | grep untracked
evals/untracked-fixture
$ ln -sf /etc/hostname evals/symlinked/fixture.yaml   # a SYMLINK is accepted too
evals/symlinked
```

Equivalent in CI (fresh checkout, no ignored files), so this is a comment/code
mismatch rather than a hole. `find -P` correctly refuses to descend a symlinked
**directory**. Use `git ls-files 'evals/**/fixture.yaml' | xargs -r -n1 dirname`
if the word "committed" is meant literally.

### N3 — unquoted `$committed` in the error branch
`.github/workflows/eval.yml:237`: `printf '  %s\n' $committed` word-splits, so a
fixture path containing a space would print mangled. Error path only.

### N4 — `--arm objective-only` on a guidance fixture exits 0 over zero checks
`harness/run_eval.py:962`:

```
$ python3 harness/run_eval.py evals/guidance/_delivery --arm objective-only
{"subject": "guidance", "section": "security", "arm": "objective-only", "checks": []}
rc=0
```

A guidance fixture puts its checks **per arm**, so the top-level list is empty by
construction and `all([])` is `True` for every guidance fixture that will ever
exist. That is "a gate that finds nothing reads the same as a gate that found
nothing wrong" — the convention `_agent-guidance/scripts/check-guidance-coverage.js`
states in its own header (exit 2 on zero headings) and that this module claims
parity with. Return 2 with "this fixture declares no top-level
`objective_checks:`; objective-only has nothing to score".

### N5 — every `run_eval.py` invocation now hard-requires `markdown-it-py`
`harness/run_eval.py:42` imports `guidance`, which imports `markdown_it` at
module scope. With the module absent, even a skill objective-only run dies:

```
$ PYTHONPATH=<blocker> python3 harness/run_eval.py evals/workflow-path-audit --arm objective-only
rc = 1
ImportError: simulated: markdown-it-py not installed
```

Both workflows that call it were updated (verified), and `run_propagation.py` /
`run_canary.py` / `make_badge.py` / `test_propagation.py` are unaffected — so
`propagation.yml`'s `pip install pyyaml` is still correct. The nit is the bare
traceback for a local user: import `markdown_it` lazily inside `h2_extents`, or
catch the ImportError and raise a `GuidanceError` naming the pip line.

### N6 — a fixture's `env:` can undo the per-arm isolation
`harness/guidance.py:423-424`. `env_spec` is applied **after** HOME / TMPDIR /
CLAUDE_CONFIG_DIR, so a fixture can point the arm at the real config dir:

```
env_spec={"CLAUDE_CONFIG_DIR":"/root/.claude","HOME":"/root"}
  ->  CLAUDE_CONFIG_DIR = /root/.claude
      HOME              = /root
```

`_refuse_real_config_dir` guards `deliver()` only, not the agent invocation.
Fixtures are trusted content, so this is a nit — but the module's whole thesis is
"a fresh scratch config dir per arm", and these two names are the only ones that
can undo it. Refuse a fixture `env:` that names `HOME`, `CLAUDE_CONFIG_DIR` or
`TMPDIR`. (The allowlist itself holds: `$SECRET_FROM_HOST` came back literal.)

### N7 — four small things
* **Cost/budget claims.** `eval.yml:74` still says "a full run is 2 agent arms +
  2 judge calls"; a `_delivery` dispatch is **5 agent calls + 5 guard probes**.
  The report's `Cost (USD)` column comes from the scored leg only, so it
  understates the run by the five guard calls. The budget test
  (`test_issue_97.py:1203`) reads the fixture's *pinned* 120/120 and covers only
  `_delivery`; a second five-arm guidance fixture that omits both knobs inherits
  600 + 300 → 75 min > the 45-min job timeout, with nothing to catch it.
* **The arm name is in the workspace path** (`/tmp/skills-evals-with_guidance_full-…/ws`),
  which the CLI puts in its system prompt — a demand characteristic that names
  the *mode* to the model. It cannot manufacture a token, so it can only produce
  a false INCONCLUSIVE here; for a real behavioural A/B (`with_guidance` vs
  `without_guidance` in cwd) it is a genuine bias. Pre-existing shape
  (`main:515` already does `skills-evals-{arm_name}-`); use an opaque suffix.
* **Inconsistent name validators.** `run_eval` accepts a unicode section id
  (`sécurité`), `make_badge._validate_name` rejects it — so such a section would
  produce results it can never badge. Unreachable today.
* **`markdown-it` version skew.** The "byte for byte" agreement with
  `check-guidance-coverage.js` depends on two independently-pinned parsers
  (`markdown-it-py==4.2.0` here, whatever `_agent-guidance` pins there). Nothing
  runs both over the same input. The 28-row `bytes` comparison is the de-facto
  cross-check — worth making it an explicit test rather than a side effect.

---

## What held up

* The environment allowlist for guidance arms — 10 variables, nothing
  credential-shaped beyond `ANTHROPIC_*`, HOME/TMPDIR/CLAUDE_CONFIG_DIR all
  scratch, and a fixture provably cannot reach round it.
* The markdown extent: **28/28** manifest rows byte-exact, and every hostile
  markdown construction I could build handled correctly, with named
  `GuidanceError`s (rc 2, no traceback) for the two drift cases.
* Payload identities: `full − extent == full-minus-section` byte for byte;
  `none` is `""`; `stub` leaks neither the heading nor the id.
* The guard's positive direction: a liar cannot fake delivery (fresh
  `secrets`-random token), a code-fenced token still counts, a split token
  fails safe, a hanging/failing/second-call CLI all yield rc 2 with **no score
  written**, and `guard.timeout_s: 0` cannot be used to skip it.
* Exit codes: 20 distinct configuration errors, all rc 2, all named, zero
  tracebacks (the two exceptions are S2).
* Per-arm isolation: fresh `mkdtemp` per arm, cleaned in `finally`, no leftover
  `/tmp/skills-evals-*`; `_refuse_real_config_dir` defeats the real HOME, the
  real `~/.claude`, and a symlink to it.
* Discovery: import errors and syntax errors are loud (rc 1), duplicate class
  names across modules and a collision with an in-file class both run without
  shadowing or double-counting, the count line stays a single total, and a
  well-formed new module is purely additive.
* Rule 19: all seven skill fixtures identical under `objective-only`; a full
  `--arm both` run identical in `summary.json`, `report.md`, argv **and** the
  child's environment — with and without `--guidance`.
* Workflow hygiene: zero `${{ }}` in any `run:` block across all six workflows,
  15/15 bare-SHA pins, the new checkout on the same SHA the file already uses,
  triggers/permissions/concurrency unchanged, `persist-credentials: false`
  everywhere, push auth step-local.
* `make_badge.py`'s new `_validate_name` rejects every traversal and
  metacharacter I threw at it, before any path is derived.
* The validation step has a real **behavioural** test that executes the step's
  own `run:` block under bash — good design; B1 is a missing case in it, not a
  missing test.

## What I could not check

* Whether a **real** `claude` CLI honours `CLAUDE_CONFIG_DIR` for user memory —
  the entire `--delivery user` premise. Everything above was measured with fakes;
  S4's residual risk depends on this and only a real dispatch settles it.
* The real dispatch itself, the OIDC/WIF exchange and the `eval-results` push
  (no credentials, no network beyond the permitted GitHub reads).
* `markdown-it-py`'s publish date vs the 7-day cooling-off (offline); the pin is
  exact and matches the installed 4.2.0 in both workflows.
* The `markdown-it` version `_agent-guidance` pins for
  `check-guidance-coverage.js` (I read the script, not its lockfile).
* The other reviewer working trees under `$SP/rev97a-*` (out of scope by rule) —
  relevant to the incident note below.

---

## Environment incident — the real `/root/.claude/CLAUDE.md` was clobbered

I record this because I was asked to, and because the attribution matters.

* **Before my work:** `md5 935c291f2efb1ff55a463bccfde55e6a`, 56,099 bytes.
* **Now:** `md5 d4ebe18523a07b5de5d78a27f6c69a6a`, **154 bytes**, mtime
  `2026-09-05 18:42:18`. Content is a real fleet-memory marked block whose entire
  body is the word `anything`.

**It was not me and, on the evidence I can gather, not this branch.** Measured
twice, from the clean export:

```
$ python3 test/issues/test_issue_97.py           rc=0   -> /root/.claude/CLAUDE.md UNCHANGED (md5 + mtime)
$ python3 test/run_tests.py                      rc=0, 438 tests, OK
                                                        -> UNCHANGED (md5 + mtime)
```

The string `payload="anything\n"` occurs exactly once in the repo — at
`test/issues/test_issue_97.py:477`, inside
`test_delivery_refuses_the_real_config_dir`, wrapped in
`assertRaises(GuidanceError)`. On head both subTest legs are refused (I verified
`_refuse_real_config_dir` directly), so that call cannot write. But it is *the
shape of this write*: `deliver(dest_dir=~/.claude, payload="anything\n")`. Two
candidates I cannot rule out: a variant of that test in one of the six
concurrent `rev97a-{code,adv,hollow,env,err,guard,nosib}` trees I am not
permitted to enter, or an adversarial mutation of `_refuse_real_config_dir` in
one of them. A second session's `python3 test/run_tests.py` on branch 84
(`$SP/se-84-v5`, PID 19963) was also live at 18:42 — that checkout has no
`test/issues/`, so it is not the source.

I did **not** attempt to restore the file (the hard rules forbid writing under
`/root/.claude/`); the `fleet-memory` SessionStart hook reinstalls it at the next
session start, so the damage is self-healing across sessions but every remaining
turn of any session already open has lost the fleet guidance.

**Recommendation regardless of attribution:** `test_delivery_refuses_the_real_config_dir`
is one guard away from clobbering a real machine's user memory, and
`_refuse_real_config_dir` is the *only* thing between it and
`$HOME/.claude/CLAUDE.md`. Harden it rather than trusting the guard it is
testing: point `HOME` at a temp dir for the whole module
(`mock.patch.dict(os.environ, {"HOME": tmp})` in `setUpClass`), and record the
real file's md5 in `setUpClass`/`tearDownClass` so *any* test that touches it
fails, not only the one run that
`test_a_whole_run_never_touches_the_real_user_memory` covers.

---

## Safety ledger

| item | before | after |
|---|---|---|
| work dir `$SP/rev97a-adv` tree md5 (NUL-safe) | `fee9bddbe813032d4f4137d06c060a8a` | `fee9bddbe813032d4f4137d06c060a8a` — and `diff -r` against a fresh `git archive 34ab8fc` export is **clean** |
| work dir file count | 96 | 96 |
| `md5sum /root/.claude/CLAUDE.md` | `935c291f2efb1ff55a463bccfde55e6a` (56,099 B) | `d4ebe18523a07b5de5d78a27f6c69a6a` (154 B) — see the incident note; not attributable to my commands or to this branch |
| `ls -la /root/.claude/` | 20 entries; `CLAUDE.md` 56099 `Sep 4 19:08`; `backups/` `Sep 5 14:01` | same 20 entries; `CLAUDE.md` 154 `Sep 5 18:42`; `backups/` mtime `Sep 5 18:59` (the CLI's own `.claude.json` rotation, contents unchanged — same five `.claude.json.backup.*` files) |
| writes into `/home/user/{skills-evals,_agent-guidance,cms-platform,agentskills}` | — | none (all mutation in `$SP/adv97/{head,disc,fx,sim,out,bin,fakereg}`) |
| network | — | none beyond the reads I was permitted; no GitHub writes, no sessions/routines/reminders |
| background processes I started | — | none left (`ps` clean); the two Bash background tasks both exited 0 |
| the real `claude` / real `gh` | — | never invoked; everything driven by `test/fake-claude` and six fakes I wrote |

## Recommendation

Fix **B1** (two lines of shell + one line in an existing test) before merge.
**S1–S3** and **S5** are each a few lines and all four are the kind of quiet
false-green this repo's own guidance is written about; I would take them in the
same PR. **S4** is a design correction worth an issue of its own. **S6** is a
header sentence to correct now and a follow-up PR to do properly.
