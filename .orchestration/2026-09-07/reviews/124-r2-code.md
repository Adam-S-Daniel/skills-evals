FOUND — 0 blocker, 1 should-fix, 5 nit

_agent-guidance PR #124 (issue #123), **round 2, code half**, head
`670e1ce03cdde3521dff504f72c118368d5f233e`, fix round 1 on top of `5215628`.

**Summary.** Every one of the 38 round-1 items landed, and I could confirm all but
the record-only ones by measurement rather than by reading. The four assertions
round 1 called unfalsifiable are falsifiable now (M17 reddens 6, M8 reddens 2).
All seven mutations that were GREEN on the full suite in round 1 — the code
half's M6/M7/M8/M9 and the adversarial half's M11/M12/M13 — are red. 17 of 17
mutations I ran on the full suite are red. The one-way door is intact: the whole
`.github/` diff against `main` is the four-line `paths:` entry, every `uses:` is
an unchanged bare 40-hex SHA, and a real fixture run preserves a foreign
`InstructionsLoaded` entry, an unrelated `env` key and an unrelated `SessionStart`
group byte-for-byte while landing the hook and its registration in one commit.

One should-fix: **adv-S6's false `MANAGED BLOCK MALFORMED` returns through the
brief's own prescribed remedy.** `basename == "AGENTS.md"` closes the three
shapes round 1 reproduced and nothing wider — any *other* file named `AGENTS.md`
(a monorepo `packages/api/AGENTS.md`, a `.claude/rules/AGENTS.md`) is still
judged as a managed one, still writes a false verdict into the receipt, and is
still printed at the next session start. That is a **REPEAT: YES**, and by the
brief's rule it is what decides whether the PR parks.

---

## Tree-integrity ledger

| item | value |
|---|---|
| `/root/.claude/CLAUDE.md` md5 **before** first command | `935c291f2efb1ff55a463bccfde55e6a` |
| `/root/.claude/CLAUDE.md` md5 **after** last command | `935c291f2efb1ff55a463bccfde55e6a` — **unchanged** |

`$SP/rev124b-code`, the five named files, **start** and **end** (identical, both
times, matching the brief):

```
22308eeb544d774218f50cdb5e502a78  .claude/hooks/instructions-loaded.sh
bdcfa92b6ec243b09c37fcfdbaa098fc  .claude/hooks/fleet-memory.sh
919feb5e318d191eeddedc5a3e782809  scripts/instructions-report.sh
da87d40dec323858cd9088975fd5a521  scripts/sync.sh
02767fc3112ed83c6670e950608d0d1d  .github/workflows/sync.yml
```

`diff -rq --exclude=node_modules $SP/rev124b-code <fresh git archive 670e1ce>`
→ **no output: IDENTICAL.**

`$SP/rev124b-ref` end md5s (read-only throughout; unchanged from the values I
read at start): `instructions-loaded.sh b481daf0…`, `fleet-memory.sh 618a8cbe…`,
`instructions-report.sh b6c1d27a…`, `sync.sh 79cc5e18…`, `bootstrap-status.sh
0b312bd3…`, `register-bootstrap-hook.sh df42263e…`.

**Hygiene.** Every suite run, mutation, fixture drive and hook probe ran in a
throwaway `cp -a` copy under `$SP/r2mut124-<name>` with `PATH=$SP/bin:$PATH`
(mikefarah yq v4.53.3 confirmed first), `HOME=$(mktemp -d)` and
`CLAUDE_CONFIG_DIR=$HOME/.claude`; `npm ci --ignore-scripts` exited 0 in each
(offline, from the local npm cache). All 22 such directories are deleted —
`ls -d $SP/r2mut124-*` → *No such file or directory*. Only logs remain
(`$SP/r2c.*`). `ps -eo pid,etimes,cmd | grep -E 'run-tests|sync.sh|instructions'`
at the end → **(none)**. `sync.sh` was run only against fixture bare repos built
by the suite's own `setup_mock_repos`/`setup_bootstrap_repos`/`create_mock_gh`
under `mktemp -d`; no real repository, no real token, no real `gh`, no real
`claude`, no network, no credential read or copied, nothing posted to GitHub, no
session/routine/reminder created. `/home/user/_agent-guidance` was touched only
with `git show`/`log`/`diff`/`archive`/`merge-base`. Nothing was written under
`/root/.claude` or any real HOME. Every pass/fail below is parsed from the
runner's own `Results: N passed, M failed` line with `$?` captured unpiped, never
off a pipeline's exit code. One honest leftover: ~6 `/tmp/tmp.*` directories
holding only `.gitconfig`/`.claude`/`.npm` are probably my suite runners' HOMEs,
but a concurrent session produces the identical shape, so I left them rather than
delete another session's state.

---

## Verifiers

| run | tree | result | exit |
|---|---|---|---|
| head, pristine copy of `rev124b-code` | `670e1ce` | **1479 passed, 0 failed** | 0 |
| ref, pristine copy of `rev124b-ref` | `5215628` | **1359 passed, 0 failed** | 0 |
| **red-first**: head's tests over the ref's six code files | — | **1413 passed, 66 failed** | 1 |

Both baselines match the worker's report exactly (it claims 1359 → 1479). The
suite did **not** abort under `set -e` in the red-first run, so all 66 are real.

**Assertion-set diff** (sorted PASS lines, head vs ref): **128 added, 8 removed,
net +120** — the worker's claimed `+120`. The 8 removed are all benign: 2 `big
marker` lines whose byte numbers moved because the payload grew (74816 → 75517),
3 renamed by adv-S8 (`EDITED ABOVE THE MARKER` → `MANAGED BLOCK MALFORMED`,
×2, plus `does replace it` → `does replace an announced one` from adv-S4), and
the 3 grep-the-hook's-source assertions code-N10 asked to be made behavioural,
replaced by 6 that M17 reddens.

Gates on the head tree, each run unpiped with `$?` captured: `check-agents-md.sh`
**0** · `check-guidance-coverage.js --check-bytes` **0** (`28 gap · 1 skipped · 0
covered`) · `check-registry.js` **0** · `bridge-status.sh CLAUDE.md` → `bridge-ok`,
**0**.

`test_fleet_memory_hook` extracted from `origin/main`, `5215628` and `670e1ce`:
233 lines / 13 993 bytes and md5 `92a1d08023562e441bf5ee4cdc005ef4` on **all
three**, `diff` empty. The worker's claim holds.

**Commit identity.** Every commit in `5f13def..670e1ce` (the branch's own 23 plus
the merge) has author **and** committer `Adam-S-Daniel
<4205216+Adam-S-Daniel@users.noreply.github.com>`; filtering that pair out of
`git log --format='%h %ae %ce'` leaves an empty list. The one
`noreply@anthropic.com` commit `2f5f744` is main's own PR #125 commit:
`git merge-base --is-ancestor 2f5f744 origin/main` → **exit 0**, and
`origin/main` is `5f13def4288442a44f28473836819a29bd490944`. `5f13def` itself is
the GitHub merge commit (committer `GitHub <noreply@github.com>`), likewise an
ancestor of `origin/main`. Neither arrived on this branch.

---

## Per-item certification

`R#`/`M#` names are the worker's own mutation labels; "red-first" cites a FAIL
from the 66-failure run of head's tests over the ref's code, or the named
mutation where the item is a regression floor over already-correct code.

### Adversarial half

| Item | Landed (file:line) | Red-first | Mutation red | Independent probe |
|---|---|---|---|---|
| **S1** log/receipt `O_NOFOLLOW` | `instructions-loaded.sh:222-237` `open_owned()`; used at `:561` (receipt tmp) and `:636` (log); `:634` uses `lstat` so a link never rotates | "the log symlink escaped — … now 239 bytes"; "the receipt tmp symlink escaped" | **R1 → 1478/1, exit 1**, first fail *the log symlink escaped … now 259 bytes* | link planted at both paths: outside file still `PRE` (4 bytes), rc 0 |
| **S2** state/receipt size cap | `read_kv():263-287`, `STATE_CAP = 64<<10` at `:169` | "a state file too large to be ours is not read at all"; "**a 1 GB state file did not finish in 5s (rc 124)**"; "the oversized receipt was merged forward — 104857628 bytes" | R2 (not on my list) | 1 GB sparse state → rc 0 in **50 ms**, log line still written; 512 MB receipt → rc 0 in **39 ms**, receipt replaced at 64 bytes, verdict correct. Round 1 measured 6.19–17.27 s / ~2 GB RSS |
| **S3** token + control sanitiser | `VERSION_CHARS`/`CONTROL_CHARS:175-176`; `version_token():305-318`; `clean():321-330` applied to every stored value at `:556` | "a long version token wrote a 100111-byte receipt"; "the verdict line was 100080 bytes"; `control byte b'\x1b'` in the receipt / on stdout / carried forward | **R3 → 1477/2, exit 1** | 100 000-char token → 96-byte stdout, **112-byte** receipt, **187-byte** SessionStart line (was 100 111 / 100 171). `\x1b[2J\x1b[1;31mSYSTEM: …` → `v2J131mSYSTEMigno`, no ESC anywhere |
| **S4** `unread` flag | `write_receipt:540-555`, `updates` at `:646`; `fleet-memory.sh:91-95` gate + `mark_receipt_read:113-124` | "an unannounced mismatch survives a new session too"; "a second session cannot erase a verdict nobody has read"; "an unannounced verdict is marked unread"; "the same verdict is never announced twice"; "reading the receipt is what marks it read" | **R5 → 1477/2, exit 1** | S1↦S2↦S1↦S2 interleave now leaves `agents=BEHIND unread=1`; next SessionStart prints it, then `unread=0`; a second SessionStart re-announces nothing; once announced a healthy verdict replaces it |
| **S5** id-less event | `same_session = bool(sid) and …` at `:546` | "an id-less event does not make every later session the same one" | R4 (not on my list) | id-less mismatch recorded, then (after announce) an id-less healthy load replaces it |
| **S6** basename gate | `agents_verdict:449-450` | 6 fails (`rules/agents.md`, `rules/x.md`, `sub/CLAUDE.md` — verdict and receipt) | **R7 → 1473/6, exit 1** | all three shapes now silent — **but see F1: the gate is narrower than the class** |
| **S7** doubled block counted | `fleet_verdict:359-364` counts BEGIN, `:390-392` counts END | "a doubled fleet block is a LOAD MISMATCH"; "… is never reported loaded"; "… says how many it found" | R8 (not on my list) | `golden+golden` (114 576 B) → `LOAD MISMATCH — the managed block appears 2 times…`; one BEGIN + two ENDs → `expected exactly one END FLEET GUIDANCE line, found 2` |
| **S8** rename + 1(b) declined | `:429-435`, `:462`; `docs/guidance-impact.md` `rejected` entry; `stub.md`, `base.md`, `README.md`, regenerated `AGENTS.md` | 3 fails (`agents-md: MANAGED BLOCK MALFORMED` ×3) | — | one-byte prose edit inside an intact block still reads `agents-md: current` — and all four documents now say so in those words |
| **H1** fragment branch | assertions at `run-tests.sh:18020-18023` | — (floor) | **M11 → 1477/2, exit 1**, first fail *the fragment verdict names the line it found* | head prints `a truncated marker fragment on line 92 (see c86465f)`; M11 prints `expected exactly one "## Repo-specific additions" line, found 0` |
| **H2** timeout 10 | `run-tests.sh:18956-18965` | — (floor) | **M12 → 1478/1, exit 1**, *the InstructionsLoaded entry does not carry timeout 10* | |
| **H3** consumer matcher | `run-tests.sh:6479-6494`, asserted on the **synced fixture repo** | — (floor) | **M13 → 1478/1, exit 1**, *… is not ('\*', 10) — AssertionError: [('session_start', 10)]* | fixture drive: the entry sync writes is `("*", 10)` |
| **N2** `truncated` flag | hook `:609-617`, `record:627`; report `:144`, `:157`, `:179`, `:196` | 4 fails (over-/under-cap log line; report text; json) | — | 5 000 000-byte file logs `bytes=5000000 truncated=True`, 64-hex digest; report prints *1 file(s) over the 4 MiB read cap*; json `"truncated": 1`; an ordinary file `truncated=False` |
| **N5** `{"hooks": null}` | `register-bootstrap-hook.sh:150-155` | `register: {"hooks": null} -> rc=1 out='' stderr='Traceback…'` | **R14 → 1472/7** | |
| **N6** unusable hooks object | `bootstrap-status.sh:100-110`; `sync.sh:857-860` | 4 classifier fails + 3 sync fails | **R14 → 1472/7, exit 1** | fixture drive with `hooks.InstructionsLoaded = "nope"`: repo withheld, `mode=full`, settings byte-identical, no hook delivered |
| **N7** stub sentence | `stub.md:17-21` + regenerated `AGENTS.md:24` | — (docs) | — | "prints its own verdict as one of the lines below — and prints it **LAST**"; I verified the ordering claim: `report_previous_session` is called at `fleet-memory.sh:103` before every `degraded` path, so the final `fleet-guidance:` line is always this session's |
| **N8** registrar env values | `register-bootstrap-hook.sh:86-96`; `bootstrap-status.sh:59-62` | 15 fails (`TIMEOUT=abc/-1/''`, `EVENT=''`, `BASENAME=''`, `COMMAND=''`, classifier ×2) | R14 (classifier half) | |
| **N11** exit 3 | `instructions-report.sh:157-162` | 3 fails | **R16 → 1476/3, exit 1** | 3509 unparseable lines → exit **3** with *none of them parseable*; absent log → exit **2** |
| **N1** record-only | `set -uo pipefail` unchanged | — | — | `git diff` on both files shows no `set` line changed |
| **N3** record-only | `STATE_DIR` resolution unchanged | — | — | no sanity check added, as declared |
| **N4** commit subject | `sync.sh:1311-1324`, `:1338` | *instr repair: commit subject is 'chore: deliver the skills-bootstrap SessionStart hook' — it names the wrong artifact* | **M6** (3rd red) | |
| **N9** `${{ inputs.dry_run }}` | unchanged at `sync.yml:150` | — | — | pre-existing; see the one-way-door read |
| **N10** unguarded `cp` | unchanged | — | — | `git diff` shows no change to any `cp "$…_SOURCE"` line |

### Code half

| Item | Landed (file:line) | Red-first | Mutation red | Independent probe |
|---|---|---|---|---|
| **S1** `fleet_up_to_date` pinned | `test_sync_instructions_hook_repair()` at `run-tests.sh:6676` | — (floor; the code was already right) | **M6 → 1476/3, exit 1**: *the deleted hook was NOT restored — the sync called the repo up to date*; *the deleted registration is not restored*; *commit subject … names the wrong artifact* | |
| **S2** delivered hook nothing runs | `sync.sh:857-860` + `bootstrap-status.sh:100-110`; `test_sync_instructions_unusable_array()` at `:6749` | 3 fails | **R14 → 1472/7** | fixture drive as above; the fix chose *refuse the delivery*, the option adv-N6 named |
| **S3** floor paragraph | `stub.md` + regenerated `AGENTS.md` | — (docs) | — | measured text |
| **S4** `HOME` unbound | `instructions-report.sh:44`, `:71-74` | "an unset HOME is not a raw shell error"; "… says what to do about it" | R18 (not on my list) | `env -u HOME -u CLAUDE_CONFIG_DIR` → *neither CLAUDE_CONFIG_DIR nor HOME is set — pass --config-dir DIR*, **exit 1** (was `HOME: unbound variable`) |
| **S5** drain every early exit | `drain_stdin():110-117`, called at `:126`, `:131`, `:132` | 3 fails, each *reported 141 under pipefail — the writer took SIGPIPE* | **R19 → 1478/1, exit 1** | 10 MB payload, 5 trials each: SKIP 0/5, no-config-dir 0/5, no-python3 0/5, normal 0/5 non-zero. **Also the untested fallback branch** (no `cat` on PATH): 0/5 non-zero, 205 ms |
| **S6** sha comparison | `:407-409` (code unchanged) + 3 new assertions | — (floor) | **M9 → 1476/3, exit 1**: *an equal-length edit is a LOAD MISMATCH* | one-byte equal-length edit → `content differs (same length, different bytes)` |
| **N1** 1 MB stdin cap | `run-tests.sh:18300-18314` (a valid over-cap event, and a valid under-cap one) | — (floor) | **M7 → 1478/1, exit 1**: *a valid event past the 1 MB cap was parsed anyway* | over-cap event writes no log line; under-cap one does |
| **N2** traceback assertion falsifiable | `run-tests.sh:18246-18274` — the same hook with only its final `2>/dev/null` stripped | — (floor) | **M8 → 1477/2, exit 1**: *with stderr visible, no event produces an interpreter traceback* / *… a python error* | |
| **N3** `add_paths` comment | `sync.sh:1283-1288`, corrected and says what the old comment got wrong | — | — | |
| **N4** `write_state` redirection | `fleet-memory.sh:130-147`, outer `2>/dev/null` wraps the compound | *a blocked state or receipt tmp path reaches nobody — did not expect 'Is a directory'* | — | |
| **N5** `ts` in the receipt | dropped; `write_receipt` docstring says why | — | — | receipt is `session/unread/fleet/agents` only |
| **N6** headline vs mechanism | hook header **WHAT THIS DOES NOT REACH** (`:26-36`) + README | — | — | absent on ref (grep count 0), present at head (1) |
| **N7** `hook_event_name` | `:199-200` | 2 fails | **R23 → 1477/2, exit 1**: *an event for another hook was logged as a memory load* | a `FileChanged` event with a real `file_path` → rc 0, **no log line, no verdict** |
| **N8** read-modify-write | `write_receipt` comment `:521-531` | — | — | absent on ref (0), present at head (1) |
| **N9** record-only | unchanged | — | — | |
| **N10** source-grep assertions | `run-tests.sh:18645-18668` — 5 needles over what the hook **prints**, plus a JSON-object parse of every printed line | — (floor) | **M17 → 1473/6, exit 1**: all 5 needles plus *line 1 is a JSON object on stdout* | independently: over 8 event shapes plus a truncation the hook printed only `fleet-guidance: …` / `agents-md: …` lines; no line parses as a JSON object; zero `decision`/`continue`/`systemMessage` tokens |

---

## Mutations — 17 of 17 red on the full suite

Each in a fresh `cp -a` copy of the head tree; `bash -n` on the two shell files
and `compile()` on the hook's embedded python passed before every run, so no row
below is measuring a syntax error. Every anchor asserted exactly one occurrence
before substituting.

| # | what it removes | passed/failed | exit | first failing assertion |
|---|---|---|---|---|
| **M6** | both `instr_*` clauses in `sync.sh`'s `fleet_up_to_date` | 1476 / 3 | 1 | `instr repair: the deleted hook was NOT restored — the sync called the repo up to date` |
| **M7** | `if len(raw) > STDIN_CAP: sys.exit(0)` | 1478 / 1 | 1 | `a valid event past the 1 MB cap was parsed anyway` |
| **M8** | the `file_path` type/empty guard | 1477 / 2 | 1 | `with stderr visible, no event produces an interpreter traceback` |
| **M9** | the `sha256` comparison in `fleet_verdict` | 1476 / 3 | 1 | `an equal-length edit is a LOAD MISMATCH` |
| **M11** | the `if fragments:` branch | 1477 / 2 | 1 | `the fragment verdict names the line it found` |
| **M12** | registered `timeout` 10 → 900 | 1478 / 1 | 1 | `the InstructionsLoaded entry does not carry timeout 10` |
| **M13** | consumer matcher `*` → `session_start` | 1478 / 1 | 1 | `the synced InstructionsLoaded entry is not ('*', 10) — AssertionError: [('session_start', 10)]` |
| **M17** | `emit()` prints a control-JSON object | 1473 / 6 | 1 | `nothing it prints carries "decision"` |
| **R1** | log opened `open(LOG,"a")` again | 1478 / 1 | 1 | `the log symlink escaped — … is now 259 bytes` |
| **R3** | `version_token` returns the raw token | 1477 / 2 | 1 | `the verdict line was 100080 bytes` |
| **R5** | `unread` never consulted | 1477 / 2 | 1 | `an unannounced mismatch survives a new session too` |
| **R7** | basename gate removed | 1473 / 6 | 1 | `.claude/rules/agents.md is not judged as a managed AGENTS.md` |
| **R14** | classifier calls an unusable `hooks` object `no-entry` | 1472 / 7 | 1 | `unusable hooks object {"hooks": null} -> unparseable (got 'no-entry')` |
| **R16** | report exits 2 for "nothing parsed" | 1476 / 3 | 1 | `an unparseable log exited 2, expected 3` |
| **R19** | drain removed from the SKIP exit | 1478 / 1 | 1 | `the FLEET_GUIDANCE_SKIP exit reported 141 under pipefail — the writer took SIGPIPE` |
| **R23** | `hook_event_name` check removed | 1477 / 2 | 1 | `an event for another hook was logged as a memory load` |

Counts agree with the worker's table on every row where it gave one; three came
back **higher** than claimed (`R14` 7 vs 4, `M17` 6 vs 5, `R7` 6 vs 6 — matching)
because a full-suite run reaches assertions its targeted driver does not. **No
mutation came back green.** There is no F-2-class defence left in this PR that I
measured: every one of round 1's seven full-suite greens now reddens.

## Hollowness

Round 1's code half found **four** assertions that could not fail. All four are
gone, and their replacements are provably falsifiable:

- the three `assert_not_contains "$INSTR_HOOK" '"decision"'`/`"continue"`/
  `"systemMessage"` source greps → replaced by five needles over the hook's
  **stdout** plus a per-line JSON parse; **M17 reddens all six**.
- `no interpreter traceback reaches the session` (certifying `2>/dev/null`) →
  replaced by a copy of the hook with only that redirection stripped, driven over
  10 event shapes; **M8 reddens both**.
- the unpinned 1 MB cap (round-1 nit N1) → a valid over-cap event and a valid
  under-cap one; **M7 reddens it**.

`assert_not_contains` still passes silently on a missing or empty file
(`run-tests.sh:54-55`), so I checked each new use for that vacuity by finding a
mutation that reddens it: `out_everything` (M17), `out_loud` (M8), `out_bigstate`
(red-first), `out_notours` ×6 (R7), `out_wrong_event` (R23), `out_double`
(red-first), `out_samelen` (M9), the report's `out_nohome` and unreadable-log
pair (red-first / R16), and the two `fleet-memory state` negatives (red-first).
**I found no new assertion that cannot fail.**

One assertion is weaker than its name, without being hollow:
`instructions-loaded: a marker fragment is never also reported current`
(`run-tests.sh:18024`) passes under M11 for a reason unrelated to the branch it
guards — with the fragment branch disabled the fixture falls through to the
marker-count check and prints `MANAGED BLOCK MALFORMED — expected exactly one
"## Repo-specific additions" line, found 0` (reproduced directly against a
mutated hook copy). The branch itself is genuinely pinned by the two assertions
above it, which is why M11 is red at all. Recorded, not filed.

---

## The one-way door

### `.github/workflows/sync.yml`

`git diff --stat 5f13def 670e1ce -- .github/` → `.github/workflows/sync.yml | 4 ++++`
— **4 insertions, 0 deletions, one file**, and the whole diff is a 3-line comment
plus `      - ".claude/hooks/instructions-loaded.sh"` inside `on.push.paths`.

| rule | measured |
|---|---|
| every `uses:` a bare 40-hex SHA, no trailing comment | **yes**, 3 of them, parsed out of the YAML: `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5`, `actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1` ×2. `diff` of the `uses:` lines against `main` differs only in **line numbers** (+4), never in text |
| nothing else moved | `git diff 5f13def 670e1ce -- .github/workflows/sync.yml` is exactly the 4 added lines |
| `${{ }}` inside any `run:` | **one**, `if [[ "${{ inputs.dry_run }}" == "true" ]]` at **L150** (L146 on `main`) — byte-identical to `main`, not introduced or moved by this PR beyond the +4 offset. It interpolates `on.workflow_dispatch.inputs.dry_run`, declared `type: boolean, default: false`, reachable only by someone who can dispatch the workflow. **Not reachable by any untrusted input**: the only other trigger is `push.branches: [main]`, there is no `pull_request` trigger, and no `github.event.*` reaches a `run:` |
| triggers | parsed: `["push", "workflow_dispatch"]` — **identical to `main`**. `push.branches: ["main"]`; `push.paths` gains one entry |
| `pull_request` trigger | **absent** |
| `permissions:` | `{contents: read}` at the workflow level, **byte-identical to `main`**; no job- or step-level `permissions:` |
| `concurrency` | **none**, at either level — correct for a required-status-free `push`/`dispatch` job, and unchanged |
| App token minted step-locally | **yes** — two `create-github-app-token` steps with `id: token_adam_s_daniel` / `token_jodidaniel`, each `with: {client-id, private-key, owner}`; the tokens reach the two `run:` steps only through step-level `env:` as `GH_TOKEN_<OWNER>`, never interpolated into a `run:` body |
| file still parses | `yq -e '.'` exit 0 |

### `scripts/sync.sh`

`git diff --stat 5f13def 670e1ce -- scripts/sync.sh` → **+103 / −4**. I read every
non-comment added line; they are confined to the `instr_*` lane, the
`delivered_list` commit subject, and the `add_paths` comment correction.

- **What it writes into a consumer repo.** `cp "$INSTR_HOOK_SOURCE"
  "$INSTR_HOOK_REL_PATH"` + `chmod 0755` (`:1250-1255`), and one registration
  through `register-bootstrap-hook.sh` with `BOOTSTRAP_HOOK_EVENT=InstructionsLoaded`,
  `BOOTSTRAP_HOOK_BASENAME=instructions-loaded.sh`, `BOOTSTRAP_HOOK_MATCHER='*'`,
  `BOOTSTRAP_HOOK_TIMEOUT=10` (`:1258-1271`). Measured on a fixture: the delivered
  file is **byte-identical** to the reviewed source, mode **0755**, and it lands
  with `.claude/settings.json` in **one commit** (`.claude/hooks/fleet-guidance.md`,
  `fleet-memory.sh`, `instructions-loaded.sh`, `.claude/settings.json`,
  `AGENTS.md`, `CLAUDE.md` — settings.json exactly once).
- **An unusable `hooks` object withholds the repo rather than being coerced**
  (code-S2 / adv-N6). `instr_reg_state == "unparseable"` sets `fleet_deliver=false`
  (`:857-860`), and the whole write block is inside `if $fleet_deliver` (`:1212`),
  so nothing is written. Measured with `hooks.InstructionsLoaded = "nope"`:
  `mode=full`, no hook delivered, `AGENTS.md` keeps the full guidance, and a later
  run with a repaired settings.json delivers normally.
- **A consumer's `settings.json` is never clobbered.** Measured against a fixture
  carrying a foreign `InstructionsLoaded` entry (`bash /opt/audit/other-hook.sh`,
  matcher `session_start`, timeout 45), an unrelated `SessionStart` group, and an
  unrelated top-level `"env": {"KEEP_ME": "yes"}`: **all three survive
  byte-for-byte**; ours is appended after the foreign entry. The registrar is
  append-only and re-parses its own candidate bytes before writing
  (`register-bootstrap-hook.sh:169-176`), refusing rather than coercing.
- **Dry-run and real agree, exactly.** Dry run prints `Would add
  .claude/hooks/instructions-loaded.sh` + `Would append an InstructionsLoaded
  entry … (existing entries preserved)`; the real run prints `hook missing —
  written.` + `settings.json — registered.` The predicates match one for one
  (`instr_hook_state` ∈ {missing, drifted} vs `!= current`; `instr_reg_state !=
  registered` in both). The dry run wrote nothing — the real run that followed
  still saw `hook=missing settings=no-entry`.
- **Nothing prints a token, a path under HOME, or personal data.** The added lines
  interpolate only `$INSTR_HOOK_REL_PATH` and `$SETTINGS_REL_PATH`, both
  repo-relative string constants (`:37`, `:54`), plus fixed state words. No added
  line contains `$HOME`, `/home/`, `/root/`, `$PWD` or `$TMPDIR`; no added line
  interpolates a token. The one pre-existing token use (`git remote set-url` at
  `:793`) is untouched by this branch and is not printed. No fixture in the diff
  carries a domain other than `github.com` doc links.

### `.claude/hooks/instructions-loaded.sh`, read in full (667 lines)

| surface | measured |
|---|---|
| `O_NOFOLLOW` opens (adv-S1) | `open_owned():222-237` wraps `os.open(path, flags \| O_NOFOLLOW, 0o600)`; used for the receipt tmp (`:561`) and the log (`:636`). Rotation sizes come from `os.lstat` (`:634`) so a symlink never rotates and never becomes the `.1` the report reads. Both escapes measured closed |
| 64 KiB read cap (adv-S2) | `read_kv():278` refuses on `os.path.getsize > STATE_CAP` before opening, and caps the read itself at `fh.read(STATE_CAP)`. 1 GB → 50 ms |
| token sanitiser (adv-S3) | `version_token():305-318` — `[^0-9a-zA-Z._-]` stripped, truncated to 16, `or "unknown"`; applied to both the loaded and the installed token (`:348`, `:371`, `:477`). `clean():321-330` strips `[\x00-\x1f\x7f]` and caps at 200, applied to **every** stored value (`:556`), so a hostile token cannot forge a second `key=value` line |
| `unread` + same-session guard (adv-S4/S5) | `:540-555`. `same_session = bool(sid) and existing.get("session","") == sid`; a mismatch is withheld from replacement while `same_session or unread`; `updates` always carries `unread: "1"` (`:646`); `fleet-memory.sh:94` gates the announcement on it and `mark_receipt_read:113-124` clears it |
| basename gate (adv-S6) | `:449-450`. Closes the three named shapes; **F1** is what it does not close |
| BEGIN/END count (adv-S7) | `:359-364` (`begins`) and `:390-392` (`ends`), with distinct wording per shape |
| renamed verdict + declined 1(b) (adv-S8) | `:429-435` docstring, `:462` `MANAGED BLOCK MALFORMED`; `docs/guidance-impact.md` carries a dated `rejected` entry naming the comparand that does not exist |
| every early exit drains stdin (code-S5) | `drain_stdin():110-117` called at `:126` (SKIP), `:131` (no config dir), `:132` (no python3); the python program drains first at `:182`. All four measured 0/5 non-zero under `pipefail` with a 10 MB payload, including the `cat`-less fallback |
| 1 MB stdin cap | `STDIN_CAP:167`, enforced at `:183-184` after the drain. M7 red |
| `file_path` guard | `:202-204` — non-`str` or empty exits 0. M8 red |
| `emit()` contract | `:573-583` writes `line.encode("utf-8") + b"\n"` and swallows every exception. Over 8 event shapes plus a truncated block it printed only `fleet-guidance: …` / `agents-md: …`; **no line parses as a JSON object**; zero `decision`/`continue`/`systemMessage` tokens. **M17 → 1473/6** |
| containment | fresh `HOME`, cwd, `TMPDIR` and an "outside" tree, full `find` before and after 9 hostile events: **identical**. The config dir gained only `instructions-log.jsonl` and `instructions-receipt.state`. Mean runtime on a healthy 57 KB load: **34 ms** against the registered 10 s |
| the payload cannot trip its own checks | `agents-md/base.md` == `.claude/hooks/fleet-guidance.md` (byte-identical) and neither contains a line-initial `## Repo-specific additions` or any `MANAGED SECTION` / `FLEET GUIDANCE` marker, so inlining it into ~20 consumer `AGENTS.md` files cannot create a second marker. The repo's own `AGENTS.md` has exactly one BEGIN (L1), one END (L91), one marker (L92) |

---

## The 15 deleted scratch blobs

All 15 recovered from `6044336^:test/.drive-prelude-<pid>.sh` (they remain
reachable in history), 13 959 976 bytes scanned in total. **Counts only, no
matched values:**

| pattern | matches across all 15 |
|---|---|
| `ghp_` · `github_pat_` · `ghs_` · `gho_` | 0 · 0 · 0 · 0 |
| `sk-ant` · `AKIA[0-9A-Z]{16}` · `xox[baprs]-` | 0 · 0 · 0 |
| `BEGIN .*PRIVATE` · `-----BEGIN` · `Bearer <20+>` | 0 · 0 · 0 |
| `@gmail` · `@jodam` · any `@<domain>.(com\|net\|org)` | 0 · 0 · 0 |
| `password[[:space:]]*=` · `token\s*=\s*"<20+>"` | 0 · 0 |
| `/root/` | 0 |
| `/home/user/` | **15** (one line per file) |

The 15 `/home/user/` hits are the **same single pre-existing comment line** —
``#     `gitdir: /home/user/_agent-guidance/.git` and audited under a`` — which is
in `test/run-tests.sh` on the **ref** at line 7345 and at head line 7627. It is a
container checkout path already on `main`, not a real user HOME, and not
introduced by these blobs.

Content: 11 of the 15 are exact **byte-prefixes** of `test/run-tests.sh` at the
commit that introduced them (they are the runner's prelude, materialised inside
`test/`); the other 4 are prefixes of an intermediate working-tree state, and I
diffed each against its nearest committed version — the deltas are 2 to 29 lines
of ordinary test code (an assertion name, a `sed` on the receipt, a session id).
**Nothing in any blob is anything other than test code.** They were introduced
across six commits (`59be5b4`, `8563af9`, `b428687`, `1e2fdbb`, `e72a4be`,
`5fd91f5`), matching the worker's account.

---

## Findings

### Should-fix

**F1 — the false `MANAGED BLOCK MALFORMED` of adv-S6 returns through the brief's
own prescribed remedy, for any Project memory file whose basename is
`AGENTS.md` but which is not the repo's synced one.**

`.claude/hooks/instructions-loaded.sh:449-450`

```python
    if os.path.basename(path) != "AGENTS.md":
        return None
```

The brief prescribed exactly this (*"Gate the structural checks on `basename ==
AGENTS.md`"*), and the three shapes round 1 reproduced are closed — I confirmed
all three are silent, and R7 reddens 6 assertions. But the gate is a **name**,
and the structural checks still run on every file that happens to carry that
name. Reproducing input (fresh `HOME`/`CLAUDE_CONFIG_DIR`, a real
`fleet-memory.sh` install, a scratch repo with the head `AGENTS.md` and
`.claude/hooks/fleet-guidance.md`), one `Project` event per row:

```
packages/api/AGENTS.md  = "# API package\n\n## Repo-specific additions\n\nlocal notes\n"
→ agents-md: MANAGED BLOCK MALFORMED — expected exactly one BEGIN MANAGED SECTION line, found 0

packages/api/AGENTS.md  = "# notes\n\nDo not remove the BEGIN MANAGED SECTION comment when editing.\n"
→ agents-md: MANAGED BLOCK MALFORMED — expected exactly one END MANAGED SECTION line, found 0

.claude/rules/AGENTS.md = "Keep the\nBEGIN MANAGED SECTION comment intact.\n"
→ agents-md: MANAGED BLOCK MALFORMED — expected exactly one END MANAGED SECTION line, found 0

control: packages/api/AGENTS.md with no marker at all  → no verdict (correct)
```

and the false verdict travels the whole way, exactly as round 1 described:

```
receipt:  agents=MANAGED BLOCK MALFORMED — expected exactly one BEGIN MANAGED SECTION line, found 0
next SessionStart:
  agents-md: previous session MANAGED BLOCK MALFORMED — expected exactly one BEGIN MANAGED SECTION line, found 0
  fleet-guidance: current (v21ccba97, 57143 bytes) — ~/.claude/CLAUDE.md
```

Reach: the CLI loads nested `CLAUDE.md` files and `.claude/rules/*.md` as Project
memory, and this fleet's own convention is a `CLAUDE.md` bridge containing
`@AGENTS.md` — so a consumer repo with a per-package `sub/CLAUDE.md` bridge, or a
rules file named `AGENTS.md`, trips it. `_agent-guidance` itself carries exactly
one `AGENTS.md`, so nothing here would show it; the ~20 consumer repos are where
it would fire, and I cannot enumerate them from this session.

The test set mirrors the defect: the three new no-verdict assertions use
`.claude/rules/agents.md`, `.claude/rules/x.md` and `sub/CLAUDE.md` — three
non-`AGENTS.md` basenames. Nothing exercises a second file that *is* named
`AGENTS.md`.

**The fix I would make**, and it is lossless here: `agents_verdict` already
computes `read_bytes(os.path.join(os.path.dirname(path), ".claude", "hooks",
"fleet-guidance.md"))` at `:479-482` and returns `None` when it is absent — move
that lookup **above** the structural checks and judge only a file that has the
synced payload beside it. Every repo where this hook is registered at all is a
repo `sync.sh` delivered `fleet-guidance.md` to (the whole write block is inside
`if $fleet_deliver`), so the root `AGENTS.md` always has the sibling and a nested
one never does. That is strictly better than the `<!-- Source: _agent-guidance -->`
line the docstring rejects at `:445-447`, because a separate file survives damage
to `AGENTS.md` in a way a line inside it does not — which is the docstring's own
stated criterion. One assertion beside the three existing ones (a second file
named `AGENTS.md`, in a directory with no `.claude/hooks/fleet-guidance.md`,
producing no verdict) pins it.

**REPEAT: YES.** Same defect (a false `agents-md:` structural verdict on a Project
memory file that is not a synced `AGENTS.md`), same consequence (into the receipt,
printed at the next session start on ~20 repos), same severity as round-1 adv-S6,
and it survives *because* the brief's prescribed remedy was implemented literally:
the fix closed the three reproductions rather than the class.

### Nits

**F2 — the widened `unparseable` classification now makes two pre-existing sync
messages assert something false about a consumer's `settings.json`.**
`scripts/sync.sh:830` and `scripts/sync.sh:1021` both read
`"$SETTINGS_REL_PATH is not parseable JSON — refusing to edit it…"`, and neither
was touched this round (`git diff 5215628 670e1ce -- scripts/sync.sh | grep -c
'not parseable JSON'` → 0) — while the classification they branch on was widened
to include valid-JSON files with an unusable `hooks` object. Measured, driving
`sync.sh` against a fixture repo whose `.claude/settings.json` is `{"hooks": []}`:

```
=== bootorg/repo-no-lock ===
  fleet-memory: .claude/settings.json is not parseable JSON — refusing to edit it, keeping the full guidance inline.
  fleet-memory: mode=full hook=missing payload=missing settings=unparseable
classifier: SessionStart/fleet-memory.sh -> unparseable
           SessionStart/skills-bootstrap.sh -> unparseable
           InstructionsLoaded/instructions-loaded.sh -> unparseable
is it valid JSON? -> YES, valid JSON   (python3 json.load succeeds)
```

The *behaviour* is right and is what adv-N6 asked for; only the operator-facing
reason is now wrong, and it sends whoever reads the sync log hunting for a JSON
syntax error that does not exist. `scripts/drift-report.sh:1174` publishes the
same widened state as `` `settings.json` unparseable `` into the drift report.
The instr lane got a correct new message at `:859`; these two did not.
Fix: reword both to match `bootstrap-status.sh`'s own updated header — "we cannot
parse or cannot append to". **REPEAT: NO** — round 1 named no message-accuracy
defect here; this arises from the remedy but is not the return of a round-1
finding.

**F3 — `mark_receipt_read` drops the 0600 mode this same round deliberately gave
the receipt.** `.claude/hooks/instructions-loaded.sh:237` creates the receipt
through `open_owned(..., 0o600)` with a docstring saying "0600 keeps a file we
create private rather than inheriting the umask" (added by `59be5b4`).
`.claude/hooks/fleet-memory.sh:113-124` (added by `1e2fdbb`) rewrites it with
`sed … > "$tmp"` + `mv`, so the mode becomes the umask's. Measured with
`umask 0022`:

```
receipt mode as written by the hook:      600
log mode as written by the hook:          600
receipt mode after SessionStart read it:  644
```

No secret is exposed (verdict strings and a truncated session-id digest), which
is why this is a nit and not more — but one commit in this round undoes a
property another commit in the same round introduced. Fix: `umask 077` around the
compound, or `chmod 600 "$tmp"` before the `mv`. **REPEAT: NO** — new code, new
defect.

**F4 — the `drain_stdin` fallback branch has no test.**
`.claude/hooks/instructions-loaded.sh:114` (`while read -r -N 65536 _`) is
reachable only when `cat` is not on PATH, and `drain_case "no python3"`
(`run-tests.sh:18370`) symlinks `cat` **into** the PATH directory it uses
(`:18357`), so only the `cat` branch is exercised. I measured the fallback
directly — 10 MB payload through `cat big | env PATH=<empty dir> /usr/bin/bash
hook` under `pipefail`, on both the no-config-dir and the SKIP exits: **0/5
non-zero, 205 ms**. So the branch works; it is a coverage gap, not a defect. Fix:
one more `drain_case` whose PATH directory contains neither `cat` nor `python3`.
**REPEAT: NO.**

**F5 — a second read-modify-write window, on the SessionStart side, undocumented.**
`fleet-memory.sh:94` greps `unread` out of the receipt, announces, then
`mark_receipt_read` (`:113-124`) re-reads the file and `sed`s `unread=1` →
`unread=0`. A verdict written by a load-time hook **between** that grep and that
sed is marked read without ever having been announced, and a later healthy
verdict then replaces it freely — the exact "silent for more than one session"
failure the `unread` flag exists to prevent, re-entering through a race. The
window is microseconds and `fleet-memory.sh` runs before memory is assembled, so
I **did not provoke it** and am recording it because it is real, not because I
saw it. The hook documents this shape for its own side (`write_receipt`,
`:521-531`); the sibling that now has the same shape says nothing. Fix: a
sentence in `mark_receipt_read`, or `sed` the exact verdict it announced rather
than whatever the file holds now. **REPEAT: NO.**

**F6 — an ambient empty `BOOTSTRAP_HOOK_*` now aborts the whole fleet sync
instead of one repo.** `scripts/bootstrap-status.sh:59-62` exits 2 on an empty
`BOOTSTRAP_HOOK_BASENAME`/`EVENT` (correct, and what adv-N8 asked for), but
`sync.sh` calls it in a plain command substitution (`:826`, `:847`) under
`set -euo pipefail`. Measured against fixture repos:

```
BOOTSTRAP_HOOK_EVENT="" ./scripts/sync.sh   → exit 2
  last line: bootstrap-status.sh: BOOTSTRAP_HOOK_BASENAME and BOOTSTRAP_HOOK_EVENT must be non-empty; …
  repos processed: 1 of 6      "Sync complete": 0
control, variable unset       → exit 0, 6 repos, "Sync complete": 1
```

Not reachable from CI (`sync.yml` sets no `BOOTSTRAP_HOOK_*`), and it aborts at
the first repo's classifier call — before any write — so no partial-fleet state
results. It is reachable for a human running `sync.sh` after experimenting with
the seam, and the run then ends with one line and no summary. Fix: `unset
BOOTSTRAP_HOOK_EVENT BOOTSTRAP_HOOK_BASENAME BOOTSTRAP_HOOK_COMMAND
BOOTSTRAP_HOOK_MATCHER BOOTSTRAP_HOOK_TIMEOUT` near the top of `sync.sh` — the
same ambient-variable hygiene the suite already applies to `GH_TOKEN`/
`GITHUB_TOKEN` at `run-tests.sh:24`, and for the same reason. **REPEAT: NO.**

---

## What I could not measure

- **Whether any of the ~20 consumer repos actually contains a second file named
  `AGENTS.md`** (F1's trigger). I can show the classifier judges one; I cannot
  enumerate the fleet from this session, and the fleet spans two owners.
  `_agent-guidance` itself carries exactly one.
- **The CLI measurements the design rests on** — the real event shape, and that
  hook stdout reaches nothing on 2.1.261. The brief forbids running `claude`.
  Everything downstream of "the hook is handed this JSON on stdin" is measured.
  Round 1 corroborated the structural half by reading the shipped bundle as data;
  I did not repeat that.
- **`R2`, `R4`, `R6`, `R8`, `R13`, `R15`, `R18`, `R24`, `R26`** — the worker's
  targeted mutations for adv-S2, adv-S5, the announce-once half of adv-S4,
  adv-S7, adv-N2, adv-N8's timeout half, code-S4, code-N4 and adv-N4. Each of
  those items is nonetheless red-first in the 66-failure run and, for most, also
  reproduced through the hook's own entry point; what is unmeasured is only
  whether that *specific* edit reddens the full suite.
- **`shellcheck`** is not installed here; `bash -n` only (clean on every touched
  shell file, in every mutated copy).
- **Behaviour as a non-root user.** This container runs as root, so a read-only
  config dir is not really read-only; I exercised the write-failure paths with
  directories and symlinks blocking the target paths instead.
- **The post-merge sync run** against real repositories — out of scope, and held
  by whoever merges.

## Recommendation

**Park on F1, then merge.** The round-1 work is otherwise complete and unusually
well pinned: 128 new assertions, 66 of them red on the round-1 code, all seven
previously-green mutations now red, 17 of 17 mutations red on the full suite,
zero assertions I could show cannot fail, and a one-way door that measures clean
line by line. F1 is the only finding that matters, and it matters because of what
it is rather than how big it is: the same defect at the same severity with the
same consequence, surviving *because* the brief's prescribed remedy was
implemented exactly as written. It is a one-line move of an existing lookup plus
one assertion. F2–F6 are nits and can ride along or follow.
