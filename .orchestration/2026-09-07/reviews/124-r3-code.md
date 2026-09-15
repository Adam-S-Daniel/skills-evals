FOUND — 0 blocker, 1 should-fix, 2 nit

_agent-guidance PR #124 (issue #123), **round 3, code half**, head
`0d73ac4d4a4a31c87ce59ecd8692b1fee374a8f5`, fix round 2 (9 commits) on top of the
round-2 head `670e1ce`.

**Summary.** Every one of the 18 adversarial items and 6 code items in the fix
brief landed, and I confirmed all but the record-only ones by measurement rather
than by reading. The worker's three headline numbers reproduce exactly: **1584
passed / 0 failed** on head, **1479 / 0** on the ref, and **1524 / 60** for this
round's tests over the ref's code — and 1524 + 60 = 1584, so no assertion was
lost to an abort. All 60 red-first failures map to a named item. I ran **24
mutations on the FULL suite** (the 12 the brief required, the worker's other 10,
and 2 re-aimed round-1 floors). **23 are red. One is GREEN, and it is my
should-fix.**

The three round-2 repeats are genuinely closed, at the class level and not the
row level: a hard link and a FIFO now escape nothing at any of the four write
sites (`open_owned` fstats the fd, and `O_TRUNC` really is stripped and
re-applied after the check); the classifier and the registrar agree on all 15
`hooks` shapes I could construct, not just the fifth one; and `agents_verdict`
now gates on the synced payload beside the file, which silences
`packages/api/AGENTS.md`, `.claude/rules/AGENTS.md` and a symlink named
`AGENTS.md` while still judging a nested repo that really does carry the payload.
The one-way door is untouched: parsed with the `yaml` package, `sync.yml` at head
is **identical to `main` once `on.push.paths` is masked** — one entry added, none
removed, nothing else in the document different by so much as a key.

**The should-fix is a coverage regression, not a behaviour defect, and it arrives
through the brief's own prescribed remedy.** F1 asked for the payload lookup to be
moved above the structural checks. It was, correctly — and that made the payload
gate subsume the *basename* gate for every fixture in the suite. Round 2's `R7`
mutation (delete `if os.path.basename(path) != "AGENTS.md": return None`) was
**1473 / 6 red** on the round-2 head; on this head the identical mutation is
**1584 / 0, exit 0 — fully green**. The gate is still load-bearing: with that one
line gone, a synced consumer repo's root `CLAUDE.md` — the `@AGENTS.md` bridge
every repo in this fleet carries — is judged as the managed file and prints
`agents-md: MANAGED BLOCK MALFORMED` into the receipt and the next session start.
Round-1 adv-S6 in its most common form, one line away, with nothing left to catch
it.

---

## 1. Tree-integrity ledger

| item | value |
|---|---|
| `md5sum /root/.claude/CLAUDE.md` **before** my first command | `935c291f2efb1ff55a463bccfde55e6a` |
| `md5sum /root/.claude/CLAUDE.md` **after** my last command | `935c291f2efb1ff55a463bccfde55e6a` — **unchanged** |

`$SP/rev124c-code`, the eight named files, **at start** and **at end** — identical
both times, and matching the brief digit for digit:

```
120776f8ed4f3aee9f331d81a6629d33  .claude/hooks/instructions-loaded.sh
9ca597ed51b6dc3af8c1e5f64bf4e6ed  .claude/hooks/fleet-memory.sh
df01dc163f4e2ca98f4c4964f9831795  scripts/sync.sh
a361933dcbb63bc2a54b141339b40f39  scripts/instructions-report.sh
bc049f4b2d44afc1ecefd7bbca5c91b1  scripts/register-bootstrap-hook.sh
4ca0c2cb317f0e7653f91fefb90fcf16  scripts/bootstrap-status.sh
3566bc803884c0f797ee3f231b596ab9  test/run-tests.sh
02767fc3112ed83c6670e950608d0d1d  .github/workflows/sync.yml
```

`diff -rq --exclude=node_modules $SP/rev124c-code <fresh git archive 0d73ac4>` →
**no output: IDENTICAL.** The same check on `$SP/rev124c-ref` against a fresh
`git archive 670e1ce` → **IDENTICAL**; its end md5s (`instructions-loaded.sh
22308eeb…`, `fleet-memory.sh bdcfa92b…`, `sync.sh da87d40d…`, `bootstrap-status.sh
790487f8…`, `register-bootstrap-hook.sh 0d48d777…`, `run-tests.sh e182911c…`) are
the values I read at start. Neither tree was ever executed in place; every run
used a `git archive` export or a `cp -a` of one.

**Hygiene.** Every suite run, mutation, fixture drive and hook probe ran in a
throwaway copy under `$SP/r3mut124-<name>`, built from
`git -C /home/user/_agent-guidance archive <sha> | tar -x` (so no `.git`, no
inherited `origin`) or a `cp -a` of that export, with `PATH=$SP/bin:$PATH`
(mikefarah `yq` **v4.53.3** confirmed first on PATH), `HOME=$(mktemp -d)` and
`CLAUDE_CONFIG_DIR=$HOME/.claude`. `npm ci --ignore-scripts` exited **0** in both
base trees. **All `r3mut124-*` directories are deleted** — `ls -d
$SP/r3mut124-*` → *No such file or directory*; only logs and probe evidence
remain under `$SP/r3c124.*` and `$SP/r3c124-runs/`.

**`GH_TOKEN` / `GITHUB_TOKEN` were unset in every shell that ran `sync.sh` or any
script** — `unset GH_TOKEN GITHUB_TOKEN` at the top of the runner, the mutation
runner and both fixture drivers, and each driver **printed the two values as it
started**: `GH_TOKEN='<unset>' GITHUB_TOKEN='<unset>'`. A leakage scan over every
byte of every sync log I produced: `ghp_` 0, `github_pat_` 0, `ghs_` 0, `gho_` 0,
`Bearer ` 0, `/root/` 0, `/home/` 0, `@gmail` 0, `jodam.net` 0, **`github.com`
0** — the only absolute paths are the `file:///tmp/tmp.*` fixture bares.

`sync.sh` ran **only** against fixture bare repos built by the suite's own
`setup_mock_repos` / `setup_bootstrap_repos` / `create_mock_gh` under `mktemp -d`.
No real repository, no real token, no real `gh`, no real `claude`, no network, no
credential read or copied anywhere, nothing posted to GitHub, no session, routine
or reminder created. `/home/user/_agent-guidance` was touched with read-only git
only (`show`, `log`, `diff`, `archive`, `merge-base`, `status`); it is still on
`main` with a clean tree. Nothing was written under `/root/.claude` or any real
HOME, and **no hook was ever handed a `file_path` under a real HOME** — every
probe built its own `home/`, `cfg/`, `proj/` and `outside/` under a fresh
`mktemp -d`. I did not enter `$SP/ag-123-v3`, `$SP/rev124c-adv`, `$SP/rev129l-*`,
`$SP/rev97c-*`, `$SP/r3mut129-*`, `$SP/r3adv*` or `$SP/se-*`.

**Processes.** At the end, `ps -eo pid,etimes,cmd | grep -E
'run-tests|sync\.sh|instructions'` → **no output at all**, and a `/proc` sweep for
anything referencing my run or scratch names → **NONE**. Two disclosures, both
mine and both closed:

- My red-first suite run and my first ref probe each left **blocked `python3` hook
  children on the FIFO rows** — which is R2-S2 itself, reproducing on the ref. One
  (pid 26223, `ppid 1`, alive 428 s, reparented to init) held my harness's pipe
  open and hung the probe. I recorded it, killed it by pid, rewrote the probe to
  redirect the hook's output to files rather than pipes, and re-ran. **No head row
  ever produced a survivor.**
- One `bash ./test/run-tests.sh` (pid 6873) was running when I started, with its
  cwd in `$SP/ag-123-v3` — another session's verification worktree. **Not mine, not
  touched, not killed.**

Every pass/fail below is parsed from the runner's own `Results: N passed, M
failed` line with `$?` captured **unpiped**; no verdict is read off a pipeline's
exit code.

---

## 2. Provenance, identity and the worker's checkout disclosure

| check | result |
|---|---|
| `git merge-base --is-ancestor 670e1ce 0d73ac4` | **exit 0** — ancestor |
| `git merge-base --is-ancestor 5f13def 0d73ac4` (`origin/main`) | **exit 0** — ancestor |
| `git merge-base --is-ancestor 5215628 0d73ac4` (the stale local branch the worker disclosed) | **exit 0** — ancestor, so nothing was discarded |
| merge commits in `670e1ce..0d73ac4` | **none** — all nine have exactly one parent, a straight chain `670e1ce → 988846e → f05795f → d57cfa8 → 16fcdcd → 632f5e0 → d50f38e → 511b2c0 → 7d46133 → 0d73ac4` |
| author **and** committer on all nine | `Adam-S-Daniel <4205216+Adam-S-Daniel@users.noreply.github.com>`; filtering that exact pair out of `git log --format='%an <%ae> \| %cn <%ce>'` leaves **0 lines** |
| `origin/claude/agent-guidance-123` | `0d73ac4d4a4a31c87ce59ecd8692b1fee374a8f5` — the head under review is the branch tip |
| `git diff --stat 670e1ce 0d73ac4` | 8 files, **+1095 / −141** — matches the brief |

The worker's disclosure checks out. `5f13def` (the brief's `5f13def`, i.e.
`origin/main`) is an ancestor; note the brief also names `5f13def` where the
worker's report says the branch started from the merge of `main` at that sha —
both resolve to `5f13def4288442a44f28473836819a29bd490944`, and it is an ancestor
of the head.

`test_fleet_memory_hook`, extracted from `main`, `670e1ce` and `0d73ac4`:
**233 lines / 13 970 bytes / md5 `926432b6a746abad9e1daea7c1726949` on all
three**, `diff` empty in both directions. The round-1 claim still holds.

---

## 3. Verifiers

| run | tree | result | exit |
|---|---|---|---|
| pristine head | `0d73ac4` | **1584 passed, 0 failed** | **0** |
| pristine ref | `670e1ce` | **1479 passed, 0 failed** | **0** |
| **red-first**: this round's `test/run-tests.sh` over the ref's **seven** changed code files | — | **1524 passed, 60 failed** | **1** |

Both baselines match the worker's report exactly. The red-first run reached
**1524 + 60 = 1584** assertions — the head's full total — so the suite did not
abort under `set -e` and **all 60 failures are real**, not the tail of a dead run.
The worker claimed 60; it is 60.

**Assertion-set diff** (sorted `PASS` lines, head vs ref): **111 added, 6 removed,
net +105** — the worker's claimed `+105`. I checked all six removals rather than
assuming they were benign:

- 2 were **renamed**, and now appear **twice each** at head (`instr unusable
  (nope): …` and `instr unusable (null): …`) — strictly more coverage;
- 3 asserted the **old, wrong** behaviour R2-S5 exists to remove (*"AGENTS.md
  carries the full guidance, not the stub"*, *"the repo keeps the FULL guidance
  rather than the stub"*, *"the sync says why it is keeping the guidance
  inline"*) — correctly deleted;
- 1 (*"a state file too large to be ours is not read at all"*) was **replaced by a
  stronger pair** for R2-N9, and I proved the replacement still pins the read
  refusal (§6).

**No coverage was lost to a deletion.** Gates on the head tree, each run unpiped
with `$?` captured: `check-agents-md.sh` **0** · `check-guidance-coverage.js
--check-bytes` **0** (`28 gap · 1 skipped · 0 covered`) · `check-registry.js`
**0** · `bridge-status.sh CLAUDE.md` → `bridge-ok`, **0** · `bash -n` clean on all
eight touched shell files, and the hook's embedded python `compile()`s
(31 275 bytes).

---

## 4. Per-item certification

Line numbers are the head's. "Red-first" cites a FAIL from the 60-failure run;
where an item is a regression floor over already-correct code, its named mutation
is cited instead. Every "independent probe" was driven through a production entry
point — `bash .claude/hooks/instructions-loaded.sh` with JSON on stdin, `bash
.claude/hooks/fleet-memory.sh`, `bash scripts/instructions-report.sh`, the two
seam scripts with exactly the environment `sync.sh` gives them, and `bash
scripts/sync.sh` dry and real against fixture bares.

### Adversarial half

| Item | Landed (file:line) | Red-first | Mutation red (full suite) | Independent probe |
|---|---|---|---|---|
| **R2-S1** hard link | `instructions-loaded.sh:278-292` — `truncate = bool(flags & os.O_TRUNC)`, `os.open(..., (flags & ~O_TRUNC) \| O_NOFOLLOW \| O_NONBLOCK)`, `fstat` → `S_ISREG` + `st_nlink != 1`, then `ftruncate` | 2 (`the hard link at the log escaped … now 259 bytes`; `… at the receipt tmp escaped`) | **M-R2S1 → 1582/2**; **M-R2S1t → 1583/1**, first fail *the hard link at the receipt tmp escaped — now 0 bytes* | 8 rows (4 sites × {hard link, FIFO}) on head: **rc 0, outside md5 unchanged, 0 survivors, 46–136 ms**. Ref: log/hard and receipt.tmp/hard both **ESCAPED** |
| **R2-S2** FIFO | same lines; `O_NONBLOCK` at `:279` | 4 (`a FIFO at the log exited 124`; `… left blocked python3 child(ren): 7831`; ×2 for the receipt tmp) | **M-R2S2 → 1580/4**, first fail *a FIFO at the log exited 124* | head: FIFO at all 4 sites → rc 0 in 46–136 ms, **no survivor**. Ref: rc **124** at 6 002/6 004 ms with a surviving `python3` each time |
| **R2-S3** `unread` | `:770` (`updates = {"session": …}`) + `:677` (`if any(key in updates for key in ("fleet","agents")): updates["unread"] = "1"`) | 4 (`a suppressed healthy reload does not re-flag …`; `the same stale verdict was announced again at 5 of 5 session starts`; +2) | **M-R2S3 → 1580/4** | mismatch(S1) → 1 announcement → 3 same-session healthy reloads → **`unread=0`**, and **0 re-announcements over the next 5 session starts** (ref: `unread=1`, 1 re-announcement) |
| **R2-S4** classifier | `bootstrap-status.sh:118` `isinstance(hooks, dict) and event in hooks and not isinstance(groups, list)` | 3 (`{"hooks": {"SessionStart": null}} -> unparseable (got 'no-entry')`; event-seam ×2) | **M-R2S4 → 1577/7** | **15-shape classifier × registrar matrix: agreement on every row** — every `unparseable` is `refused-unparseable` with the file byte-identical, every `no-entry` is `registered`. `null` under the event key: head `unparseable`; ref `no-entry` |
| **R2-S5** withhold the pair | `sync.sh:833`, `:882` `instr_deliver=false`, `:890` `$fleet_deliver \|\| instr_deliver=false`, `:901-910` `instr_needs_work`, `:1135`, `:1294`, `:1302` | 5 (`the repo keeps the STUB`; `is not dragged back to the inline guidance`; `AGENTS.md changed (57971 bytes, was 5686)`; +2) | **M-R2S5 → 1577/7** | fixture drive, `"nope"` and `null`: **mode=stub**, `AGENTS.md` byte-identical at **5 687 bytes**, settings.json byte-identical, fleet-memory hook + payload + registration all present, **bare `main` did not move (no commit)**. Ref: 5 687 → **57 971** with fleet-memory still registered |
| **R2-S6 / F1** payload gate | `:560` basename, `:563-565` `read_bytes(<dir>/.claude/hooks/fleet-guidance.md)` → `return None` | 4 (`packages/api/AGENTS.md is not judged …` + receipt; `.claude/rules/AGENTS.md …` + receipt) | **M-R2S6 → 1580/4** | 9 shapes: `packages/api/AGENTS.md`, a second one quoting BEGIN, `.claude/rules/AGENTS.md`, lowercase `agents.md`, a **symlink named `AGENTS.md`** with no payload beside it → **no verdict, no receipt entry** at head; **5 false `MANAGED BLOCK MALFORMED` on the ref**. Positive controls: the root `AGENTS.md` → `current`, and a **nested repo carrying its own payload** → `current`, its malformed twin → still `MALFORMED` |
| **R2-S7** read-side sanitiser | `fleet-memory.sh:105-106` | 2 (`control byte b'\x1b' reached the session start`; `a previous-session line was 5035 characters`) | **M-R2S7 → 1582/2** | planted receipt with ESC + a 5 000-char value: head **0 control bytes, longest line 228 chars, 377 bytes total**; ref **3 control bytes, 5 028-char line, 5 180 bytes** |
| **R2-N1** report text mode | `instructions-report.sh:95-100`, `:202`, `:217-218` | 1 (`control byte b'\x1b' reached the text report`) | **M-R2N1 → 1583/1** | a hostile `load_reason` through the hook into the text report: head **0 control bytes**, ref **3**. `--format json` still escapes (0 raw). No regression on the `(unset)` / `unknown` fallbacks — both fields are `str` by construction (`:136`, `:150`), so `clean()` never sees `None`; measured identical on head and ref |
| **R2-N2** `bytes` display | `:465-471` — number and display string derived separately; `want = raw_want if want_n is not None else "?"` | 2 (`control byte b'\x1b' reached the verdict line`; `a bytes= that is not a number is reported as unknown`) | **M-R2N2 → 1582/2** | a `bytes=` carrying ANSI → head prints `… (17143 of ? bytes, …)`, **0 control bytes**; ref prints the escapes raw |
| **R2-N3 / F3** receipt mode | `fleet-memory.sh:145-158` — `mktemp` (0600) replaces the fixed name | 1 (`the receipt is 644 after a session start, not 600`) | **M-F3 → 1583/1** | under `umask 022`: **0600 after the hook writes it, and still 0600 after a session start reads it** (ref: 600 → **644**) |
| **R2-N4** blocked `.read.tmp` | same lines | 2 (`a directory at the old fixed tmp name still clears the flag`; `… does not re-announce`) | **M-R2N4 → 1580/4** | a **directory** planted at `<receipt>.read.tmp`: head announces **1 time over 5 session starts** (cleared); ref **5 of 5**, stderr empty. Also: **no tmp-file accumulation** — 12 announce/clear cycles leave 0 stray `.read.*` files |
| **R2-N5** "truncated" | `:477-482` — `if want_n is not None and present >= want_n: "no END marker (%d bytes present, %s installed)"` | 2 (`a block at or past the installed length is not called truncated`; `the no-END-marker line still names both byte counts`) | **M-R2N5 → 1582/2** | `bytes=48` with 17 143 present → head `no END marker (17143 bytes present, 48 installed)`; ref `truncated (17143 of 48 bytes, no END marker)` |
| **R2-N6** MATCHER / TIMEOUT | `register-bootstrap-hook.sh:112`, `:118-119` | 8 (`MATCHER=` ×2; `TIMEOUT=0` ×2, `=3601` ×2, `=99999999999999999999` ×2) | **M-R2N6m → 1582/2**; **M-R2N6t → 1578/6** | full matrix: **1, 10, 30, 3600 accepted and stored**; **0, 3601, 99999999999999999999, abc, -1, '', ' 10 ' refused (`refused-bad-env`, rc 2, file untouched)**; `MATCHER=''` refused, `'*'` / `startup` accepted. **One gap — see finding C2** |
| **R2-N7** symlinked settings | `bootstrap-status.sh:164`; `register-bootstrap-hook.sh:73` | 3 (`the classifier said 'no-entry'`; `the registrar answered rc=0 'registered'`; `the write went through the link`) | **M-R2N7c → 1583/1**; **M-R2N7r → 1582/2** | head: classifier `unparseable`, registrar `refused-unparseable` (3), **outside target unchanged**. Ref: `no-entry` / `registered`, **the write went through the link** |
| **R2-N8** bounded stdin | `:194-196` `read(STDIN_CAP + 1)` + discard loop | 1 (`48 MiB of stdin took the hook to 63224 KiB`) | **M-R2N8 → 1583/1** | `getrusage(RUSAGE_CHILDREN).ru_maxrss` from a **fresh process that has reaped no other child** and whose parent never holds the payload: head **15 220 KiB**, ref **63 096 KiB**, threshold 32 768. (My first attempt read 60 332 KiB for head — a fork/COW artifact of a parent holding 48 MB; named in §7) |
| **R2-N9** oversized state | `:351-368` `state_oversized()`, called at `:775` | 3 (`an oversized state file leaves a mark rather than nothing`; `names the cap it hit`; `reaches the receipt`) | **M-R2N9 → 1581/3** | a 70 kB state file: head prints `LOAD MISMATCH — fleet-guidance.state is over 65536 bytes, so nothing could be compared this session` and writes it to the receipt; ref prints **nothing at all** (0 bytes of stdout) |
| **R2-N10** unguarded `cp` | unchanged at `sync.sh:1296` | — (record-only) | — | `git diff 670e1ce 0d73ac4` touches no `cp "$…_SOURCE"` line. Confirmed unchanged, as declared |
| **R2-N11** `${{ inputs.dry_run }}` | unchanged at `sync.yml:150` | — (record-only) | — | see the one-way-door checklist; byte-identical to `main`, `type: boolean`, dispatch-only |

### Code half

| Item | Landed (file:line) | Red-first | Mutation red (full suite) | Independent probe |
|---|---|---|---|---|
| **F1** (= R2-S6) | `:560`, `:563-565`; docstring narrowed at `:529-558` | 4 | **M-R2S6 → 1580/4** | as R2-S6 above. The docstring now claims exactly the payload criterion and no more. **But see finding C1** |
| **F2** withholding reason | `sync.sh:853`, `:1057`; `drift-report.sh:1174`, `:1407` | 4 (`the withholding reason covers the whole widened class`; `a valid JSON file is not reported as a syntax error`; `repo-unparseable: refusal is logged`; `drift report: … Notes name the reason`) | **M-F2 → 1582/2** | on a `{"hooks": []}` the test first proves is **valid JSON**: head *"is one we cannot parse or cannot append to"*; ref *"is not parseable JSON"* |
| **F3** (= R2-N3) | `fleet-memory.sh:145-158` | 1 | **M-F3 → 1583/1** | 600 → 600 (ref 600 → 644) |
| **F4** `cat`-less drain | `:117` `while read -r -N 65536 _` | — (floor: the branch was already correct, only untested) | **M-F4 → 1582/2**, first fail *the no cat and no python3 exit reported 141 under pipefail* | 10 MiB payload under `pipefail`, PATH containing **neither `cat` nor `python3`**: **0/5 non-zero**, and 0/5 on the SKIP, no-config-dir and normal paths too |
| **F5** SessionStart window | `fleet-memory.sh:134-144` — documented, not closed | — (documentation, as the brief permitted) | — | the comment states the window, why it was not provoked, and what closing it would cost. Matches what `write_receipt` does for its own side |
| **F6** ambient seam | `sync.sh:77-78` `unset BOOTSTRAP_HOOK_*` | 4 (`the run exited 2`; `the run reaches its summary`; `the classifier is never handed the ambient value`; `1 of 6 repos processed`) | **M-F6 → 1580/4** | `BOOTSTRAP_HOOK_EVENT="" BOOTSTRAP_HOOK_BASENAME=""`: head **exit 0, all 6 fixture repos processed, `=== Sync complete: 0 synced, 6 skipped, 0 failed ===`, 0 occurrences of "must be non-empty"**; ref **exit 2 after 1 of 6, no summary** |

### Round-1 should-fix regression rows

Each re-driven through the production entry point on the head, not read off the
suite.

| Round-1 item | Still closed? | Measured |
|---|---|---|
| **adv-S1** symlink escape | **YES** | a symlink out of the config dir at **all four** write sites → rc 0 in 38–50 ms, outside file still `PRE`, **unchanged** at every site |
| **adv-S2** state size cap | **YES, and improved** | 1 GB sparse state → **rc 0 in 37 ms**; and where round 2 measured silence, head now names it. The cap itself is still load-bearing: removing `read_kv`'s `getsize > STATE_CAP` refusal makes a 70 kB state parse and print `fleet-guidance: loaded` |
| **adv-S3** token sanitiser | **YES** | ANSI token → `v2J131mSYSTEMpu`, **0 control bytes**, stdout 96 B, receipt 110 B; a 3 000-char token → 16 chars; a **newline** token forges no second key (receipt keys are exactly `session`, `unread`, `fleet`) |
| **adv-S4 / S5** `unread`, id-less events | **YES** | a new session's healthy load replaces the announced mismatch and is itself **announced once, re-announced 0** |
| **adv-S6** false `agents-md` verdict | **YES (behaviour)** | all five non-synced shapes silent. **Coverage regressed — finding C1** |
| **adv-S7** doubled block | **YES** | `golden+golden` → `LOAD MISMATCH — the managed block appears 2 times in the file the session loaded` |
| **adv-S8** verdict rename | **YES** | the verdict is `MANAGED BLOCK MALFORMED` everywhere I provoked it |
| **H1 / H2 / H3** | **YES** | all three assertions pass at head; `sync.sh:1302-1310` still passes `MATCHER='*' TIMEOUT="10"`, and the registrar stores exactly `[10]` with `"matcher": "*"` |
| **code-S1** repair of a deleted hook | **YES** | **M-R1M6** (this round's rewritten `\|\| $instr_needs_work` clause neutralised) → **1581/3**, first fail *instr repair: the deleted hook was NOT restored — the sync called the repo up to date*. The rewrite did **not** lose this floor |
| **code-S2** delivered hook nothing runs | **YES** | the 15-shape agreement matrix; `sync.sh` withholds and makes **no commit** |
| **code-S4** unset `HOME` | **YES** | `instructions-report.sh:44,71-74` unchanged this round; gates pass |
| **code-S5** drain every early exit | **YES** | 4 exits × 5 trials × 10 MiB under `pipefail` → **0/20 non-zero**, including the `cat`-less fallback |
| **code-S6** sha comparison | **YES** | unchanged this round; `fleet_verdict`'s `content differs (same length, different bytes)` path intact |

---

## 5. Mutations — 24 on the FULL suite, 23 red, **1 green**

Each in a fresh `cp -a` of the head export. Before every run: the mutation script
**asserted its anchor occurs exactly once** and aborted otherwise; `bash -n` on
all six touched shell files; and a `compile()` of the hook's embedded python. So
no row below measures a syntax error or a crashing mutant.

| # | what it removes | passed / failed | exit | first failing assertion |
|---|---|---|---|---|
| **M-R2S1** | the `S_ISREG` / `st_nlink` checks in `open_owned` | 1582 / 2 | 1 | `the hard link at the log escaped — … is now 259 bytes` |
| **M-R2S1t** | the `O_TRUNC` strip (flag passed straight to `os.open`) | 1583 / 1 | 1 | `the hard link at the receipt tmp escaped — now 0 bytes` |
| **M-R2S2** | `os.O_NONBLOCK` | 1580 / 4 | 1 | `a FIFO at the log exited 124 (124 = it blocked past the bound)` |
| **M-R2S3** | `unread` back in the initial `updates` | 1580 / 4 | 1 | `a suppressed healthy reload does not re-flag the receipt as unread` |
| **M-R2S4** | `event in hooks` → `groups is not None` | 1577 / 7 | 1 | `unusable hooks object {"hooks": {"SessionStart": null}} -> unparseable (got 'no-entry')` |
| **M-R2S5** | `instr_deliver=false` → `fleet_deliver=false` | 1577 / 7 | 1 | `instr unusable (nope): the repo keeps the STUB — the fleet-memory pair is not withheld with it` |
| **M-R2S6** | the sibling-payload guard in `agents_verdict` | 1580 / 4 | 1 | `packages/api/AGENTS.md is not judged as the synced AGENTS.md` |
| **M-R2S7** | the control-strip and cap in `report_previous_session` | 1582 / 2 | 1 | `control byte b'\x1b' reached the session start` |
| **M-F6** | the `unset BOOTSTRAP_HOOK_*` line | 1580 / 4 | 1 | `ambient env: the run exited 2 — … must be non-empty` |
| **M-R2N7c** | the classifier's symlink refusal | 1583 / 1 | 1 | `symlinked settings.json: the classifier said 'no-entry'` |
| **M-R2N8** | the bounded read + drain loop | 1583 / 1 | 1 | `48 MiB of stdin took the hook to 63376 KiB — the read is not bounded` |
| **M-R2N9** | the `state_oversized()` call | 1581 / 3 | 1 | `an oversized state file leaves a mark rather than nothing` |
| **M-F2** | the reworded withholding reason | 1582 / 2 | 1 | `the withholding reason covers the whole widened class` |
| **M-F3** | `chmod 0644` on the receipt tmp | 1583 / 1 | 1 | `the receipt is 644 after a session start, not 600` |
| **M-F4** | the `read -r -N` fallback drain loop | 1582 / 2 | 1 | `the no cat and no python3 exit reported 141 under pipefail` |
| **M-R2N1** | `clean()` in `instructions-report.sh` | 1583 / 1 | 1 | `control byte b'\x1b' reached the text report` |
| **M-R2N2** | the digit check on the `bytes` display value | 1582 / 2 | 1 | `control byte b'\x1b' reached the verdict line` |
| **M-R2N4** | `mktemp` back to the fixed `.read.tmp` name | 1580 / 4 | 1 | `a blocked state or receipt tmp path reaches nobody — did not expect 'Is a directory'` |
| **M-R2N5** | the `present >= want_n` branch | 1582 / 2 | 1 | `a block at or past the installed length is not called truncated` |
| **M-R2N6m** | the empty-`MATCHER` refusal | 1582 / 2 | 1 | `register: BOOTSTRAP_HOOK_MATCHER= -> rc=0 out='registered'` |
| **M-R2N6t** | the 1–3600 timeout range | 1578 / 6 | 1 | `register: BOOTSTRAP_HOOK_TIMEOUT=0 -> rc=0 out='registered'` |
| **M-R2N7r** | the registrar's symlink refusal | 1582 / 2 | 1 | `symlinked settings.json: the registrar answered rc=0 'registered'` |
| **M-R1M6** *(round-1 floor, re-aimed at the rewritten clause)* | `\|\| $instr_needs_work` → `\|\| false` | 1581 / 3 | 1 | `instr repair: the deleted hook was NOT restored — the sync called the repo up to date` |
| **M-R1R7** *(round-1 floor)* | the **basename gate** `if os.path.basename(path) != "AGENTS.md": return None` | **1584 / 0** | **0** | **— none. GREEN. See finding C1** |

The worker ran nineteen of its twenty-two rows on a targeted subset only; all
twenty-two are re-run here on the full suite, and every count is at least as high
as its claim. **The one green is the row the worker never ran** — its `M-R2S6`
mutates the *payload* guard, not the basename one.

---

## 6. Hollowness

`assert_not_contains` still passes silently on a missing or empty file
(`run-tests.sh:54-55`), so I checked **every one of the 10 new uses** this round
added (755 added test lines; an 11th match is a comment).

- **9 of 10 are red-first** in the 60-failure run, so they are non-vacuous by
  measurement: added-lines 98, 101, 124, 146, 188, 220, 307, 408, 449 (449 twice,
  once per shape).
- **The 10th** — `assert_not_contains "$d/out_bigstate" "fleet-guidance: loaded"`
  — passes on the ref because the ref writes an *empty* `out_bigstate`, so it
  would be vacuous there. I proved it falsifiable directly: with `read_kv`'s
  `getsize > STATE_CAP` refusal removed, a 70 148-byte state file parses and the
  hook prints `fleet-guidance: loaded (v21ccba97, 57143 bytes)` — **the assertion
  reddens.** Non-vacuous at head, and it carries the coverage of the one
  assertion this round deleted.

The **two `[[ -e ]] && grep` rows the worker rewrote** (added-lines 451-459) are
correct and are the right call: `assert_not_contains` on a receipt whose *passing*
state is "never created" would have been permanently vacuous, and the rewrite
makes "no `agents=` key" the explicit condition. They are followed in the same
fixture by a **positive control** — the root `AGENTS.md` beside the payload is
still judged `current`, and a malformed root `AGENTS.md` is still caught — so a
gate that silenced everything could not satisfy the block.

**I found no assertion that cannot fail.** Suite hygiene over the 755 added test
lines: **0** hard-coded `/tmp/` literals, **0** writes under `$HOME` or `~`, **0**
`../` traversal, **0** `/root/`, **0** email addresses, **0** real domains (the
two apparent hits are `re.compile` and `/proc/<pid>/comm`). The one `~/` string is
a **JSON value inside a synthetic log record** written to `$TEST_DIR` — the
`relativize`d form the hook emits — not a path any test opens.

---

## 7. The one-way door

### `.github/workflows/sync.yml` — parsed with the repo's own `yaml` package, never a regex

`git diff --stat 5f13def 0d73ac4 -- .github/` → `.github/workflows/sync.yml | 4
++++` — **4 insertions, 0 deletions, one file**, and the whole diff is a 3-line
comment plus `      - ".claude/hooks/instructions-loaded.sh"` inside
`on.push.paths`. No other file under `.github/` changed.

| rule | measured |
|---|---|
| diff vs `main` is only the four-line `paths:` entry | **yes** — and, parsed, the head document is **identical to `main`'s once `on.push.paths` is masked**: `paths added: [".claude/hooks/instructions-loaded.sh"]`, `paths removed: []`, everything else deep-equal |
| every `uses:` a bare 40-hex SHA, no trailing comment | **yes, 3 of 3**, extracted from the parsed steps: `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5`, `actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1` ×2. `bare40hex=true`, `trailingComment=false` on all three, and a text diff of the `uses:` lines against `main` is **empty** |
| `${{ }}` inside any `run:` | **exactly one**, `${{ inputs.dry_run }}` at **L150** (L146 on `main`) — byte-identical to `main`. Declared at L44-49 under `workflow_dispatch.inputs` as `type: boolean, default: false`. **0** `run:` blocks reference `github.event.*` |
| triggers unchanged, no `pull_request` | **`["push","workflow_dispatch"]`, identical to `main`**; `push.branches: ["main"]`; `pull_request` **absent** |
| permissions unchanged and minimal | top-level **`{contents: read}`**, byte-identical to `main`; **no job- or step-level `permissions:`** |
| App token minted step-locally | **yes** — `steps[2]`/`steps[3]` with `id: token_adam_s_daniel` / `token_jodidaniel`; the tokens reach `run:` **only** through step-level `env:` (`GH_TOKEN_ADAM_S_DANIEL`, `GH_TOKEN_JODIDANIEL`), never interpolated into a `run:` body |
| no `concurrency` group added | **none at workflow or job level**, on either side |
| file still parses | `yq -e '.'` exit **0** |

### `scripts/sync.sh` — the diff since `670e1ce` (+64 / −20 = the 84 in the brief)

- **What it now writes into a consumer repo, per branch.** *Delivering:*
  `cp "$INSTR_HOOK_SOURCE" "$INSTR_HOOK_REL_PATH"` + `chmod 0755` (`:1294-1300`)
  and one registration through the registrar with `EVENT=InstructionsLoaded`,
  `BASENAME=instructions-loaded.sh`, `MATCHER='*'`, `TIMEOUT="10"`
  (`:1302-1310`). *Withheld:* **nothing at all** — measured, the bare's `main` did
  not move, `settings.json` and `AGENTS.md` are byte-identical to what was pushed,
  and no hook file appears. *Mixed* (fleet half broken, instr half withheld): the
  commit contains **exactly** `.claude/hooks/fleet-guidance.md` and
  `.claude/hooks/fleet-memory.sh`, under the subject `chore: deliver the
  fleet-memory hook`; `settings.json` is not in it and `hooks.InstructionsLoaded`
  is still `{'broken': True}` afterwards.
- **A consumer's `settings.json` is never clobbered on any branch I could reach.**
  Byte-identical after the withheld run, after the mixed run, and after every
  refusal in the 15-shape registrar matrix. The registrar refuses rather than
  coerces, and now refuses a symlink before following it.
- **Dry-run and real agree on every branch.** On `"nope"` and `null` the two
  sections are **byte-identical**; on the mixed branch the dry run prints
  `[DRY RUN] Would NOT touch .claude/hooks/instructions-loaded.sh or its
  registration (the fleet-memory pair and AGENTS.md are delivered as usual)` and
  the real run does exactly that. On the ref, the `null` dry run promised
  *"Would append an InstructionsLoaded entry"* the real run then refused — parity
  is **restored**.
- **The ambient `BOOTSTRAP_HOOK_*` seam is unset before use** — `:77-78`, above
  `WORK_DIR=$(mktemp -d)` and far above the first classifier call at `:850`.
- **Nothing prints a token, a path under HOME, or personal data.** Over **340
  added production lines** across all seven changed scripts: `$HOME` 0, `/home/`
  0, `/root/` 0, `/Users/` 0, `ghp_` 0, `github_pat_` 0, emails 0. The two
  `token` hits are the words "version token" in a comment; the one `TOKEN` hit is
  the comment naming `GH_TOKEN`/`GITHUB_TOKEN` hygiene. The only "domain" is
  `re.com`, from `re.compile(`.

### `.claude/hooks/instructions-loaded.sh`, read in full (794 lines)

| surface | measured |
|---|---|
| `open_owned`, both flags paths | `:278-292`. The `O_TRUNC` path (receipt tmp) strips the flag, checks the fd, then `ftruncate`s; the append path (log) never carries it. Both refuse a symlink, a hard link, a FIFO, a directory. `O_NONBLOCK` is what lets the `fstat` run at all on a FIFO |
| the two **rename** sites | `os.replace` at `:757` (log → `.1`) and `:686` (tmp → receipt) act on the **name**; measured with a hard link, a FIFO and a symlink planted at each — outside content untouched every time. Rotation size comes from `os.lstat` (`:756`), so a planted link never rotates |
| bounded stdin read | `:194-196`; 48 MiB → **15 220 KiB** children RSS, 42 ms |
| drain fallbacks | `drain_stdin():111-119`, called at `:128` (SKIP), `:133` (no config dir), `:134` (no python3); the python program drains at `:195`. **0/20 non-zero** across 4 exits × 5 trials at 10 MiB under `pipefail`, including with neither `cat` nor `python3` on PATH |
| every early exit is `exit 0` and drains | measured: **every** one of the ~20 hostile shapes I drove exited **0** with empty stderr |
| `emit()` is observability-only | **M17 re-measured**: 12 event shapes (healthy, truncated, doubled, absent, Project, hostile `session_id`/`memory_type`/`cwd`/`load_reason`, no session id, wrong event, garbage stdin, a JSON array) → 586 bytes of stdout, **only two line prefixes** (`fleet-guidance`, `agents-md`), **no line parses as a JSON object**, and `"decision"` 0 · `"continue"` 0 · `"systemMessage"` 0 · `hookSpecificOutput` 0 · `"block"` 0 · `"suppressOutput"` 0 · control bytes 0 |

---

## 8. Findings

### Should-fix

**C1 — the basename gate in `agents_verdict` is now completely unpinned: round 2's
`R7` mutation went from 6 red to fully green, and the line it deletes is still
load-bearing for the most common file in every consumer repo.**

`.claude/hooks/instructions-loaded.sh:560-561`

```python
    if os.path.basename(path) != "AGENTS.md":
        return None
```

**Reproducing input.** Delete those two lines (nothing else) and run the full
suite:

```
M-R1R7   Results: 1584 passed, 0 failed   exit 0
```

On the round-2 head the identical mutation was **1473 passed / 6 failed**. The
coverage was not moved — it was retired.

**Why it went green.** F1's prescribed remedy was to move the
`fleet-guidance.md` lookup above the structural checks. That was done correctly
(`:563-565`), and the payload gate now silences every fixture the basename gate
used to silence: round 1's three shapes (`.claude/rules/agents.md`,
`.claude/rules/x.md`, `sub/CLAUDE.md`) and this round's two
(`packages/api/AGENTS.md`, `.claude/rules/AGENTS.md`) all sit in directories with
no `.claude/hooks/fleet-guidance.md` beside them. **Nothing in the suite puts a
non-`AGENTS.md` memory file in a directory that HAS the payload** — which is
precisely a synced repo's root.

**Why the line still matters.** Measured, in a scratch repo built like a synced
consumer (root `AGENTS.md` + `.claude/hooks/fleet-guidance.md`), one `Project`
event per row:

```
                        gate intact          gate removed (M-R1R7)
CLAUDE.md            -> (no verdict)         agents-md: MANAGED BLOCK MALFORMED — expected exactly one END MANAGED SECTION line, found 0
agents.md            -> (no verdict)         agents-md: MANAGED BLOCK MALFORMED — expected exactly one END MANAGED SECTION line, found 0
NOTES.md             -> (no verdict)         agents-md: MANAGED BLOCK MALFORMED — expected exactly one BEGIN MANAGED SECTION line, found 0
.claude/rules/house.md -> (no verdict)       (no verdict)          <- the payload gate covers this one
AGENTS.md            -> current (v21ccba97)  current (v21ccba97)
```

The first row is the one with teeth: **this fleet's own convention is a root
`CLAUDE.md` bridge containing `@AGENTS.md`**, and `_agent-guidance` itself ships
one. Every consumer repo has that file, at the root, beside the payload. So the
single line standing between the current behaviour and round-1 adv-S6 firing on
~20 repos' most-loaded Project memory file is now guarded by **zero assertions**.

**Severity: should-fix, not blocker.** The behaviour at head is correct — I could
not produce a false verdict from any shape. What is gone is the regression floor,
and the brief's rule 18 ("every fix … is killed by a NAMED mutation after") is
exactly the rule this breaks.

**The fix I would make** — two lines, in the fixture that already exists. The
`test_instructions_loaded_hook` repo already has the payload and the positive
control (added-lines 461-476); beside `out_root_still`, add a root-level file that
is *not* named `AGENTS.md` and *does* quote a marker, and assert no verdict:

```bash
printf '# bridge\n\n@AGENTS.md\n\nKeep the\nBEGIN MANAGED SECTION comment intact.\n' \
    > "$repo/CLAUDE.md"
rm -f "$receipt"
instr_run "$d/out_root_bridge" "$(instr_event Project session_start "$repo/CLAUDE.md")"
assert_not_contains "$d/out_root_bridge" "agents-md:" \
    "instructions-loaded: a root CLAUDE.md beside the synced payload is not judged as AGENTS.md"
```

That reddens under `M-R1R7` and is non-vacuous (the file is written by the same
run that the positive control reads).

**REPEAT: YES — through the brief's own prescribed remedy, though not the same
defect.** It arrives *because* F1's "move the lookup above the structural checks"
was implemented exactly as written, which is the brief's stated repeat test. But
it is **not** the return of round-1 adv-S6 or round-2 R2-S6/F1 at the same
severity: those were live false verdicts; this is a lost regression floor over
behaviour that is currently correct. I am flagging both halves rather than
choosing the convenient one, because the two-strikes decision turns on which
reading the orchestrator takes.

### Nits

**C2 — a `BOOTSTRAP_HOOK_TIMEOUT` with a leading zero containing an 8 or a 9
leaks a raw bash arithmetic error before the clean refusal, and the bounds check
evaluates a different number from the one that gets stored.**

`scripts/register-bootstrap-hook.sh:118-119`

```bash
[[ "$HOOK_TIMEOUT" =~ ^[0-9]{1,4}$ ]] || bad_env "…"
[[ "$HOOK_TIMEOUT" -ge 1 && "$HOOK_TIMEOUT" -le 3600 ]] || bad_env "…"
```

`[[ x -ge y ]]` does arithmetic evaluation, where a leading zero means **octal**.
Measured, against `{"hooks":{"SessionStart":[]}}`:

```
TIMEOUT='08'   rc=2   register-bootstrap-hook.sh: line 119: [[: 08: value too great for base (error token is "08")
                      refused-bad-env
                      register-bootstrap-hook.sh: BOOTSTRAP_HOOK_TIMEOUT must be between 1 and 3600 seconds, got '08'
                      file changed: NO   stored: none
TIMEOUT='09'   rc=2   (same shape)          TIMEOUT='019' rc=2  (same)   TIMEOUT='0999' rc=2  (same)
TIMEOUT='010'  rc=0   registered            stored=[10]    <- bounds-checked as octal 8
TIMEOUT='0100' rc=0   registered            stored=[100]   <- bounds-checked as octal 64
```

The **decision is right in every row** — nothing wrong is ever written, the file
is untouched on every refusal, and no value can actually store a timeout above
3600 (a leading-zero 4-digit value maxes at `0777` → stored 777). What breaks is
the property round 1's adv-N8 closure was *measured on* — *"`refused-bad-env`,
rc 2, **one line on stderr**, file untouched"*. For `08` it is two lines, the
first naming the script and its line number.

Not reachable from `sync.sh` (which passes the literal `10`) or from CI; reachable
by the human experimenting with the seam that R2-N6 exists for. **Fix:** put the
range in the regex and drop the arithmetic comparison —
`^([1-9][0-9]{0,2}|[1-3][0-9]{3}|3600)$` — or force base 10 with
`(( 10#$HOOK_TIMEOUT >= 1 && 10#$HOOK_TIMEOUT <= 3600 ))`, which also makes the
check and the stored value agree.

**REPEAT: YES on the narrow clause, NO on severity.** It arrives through R2-N6's
own prescribed remedy (the new `-ge`/`-le` comparison is what introduced it), and
it dents adv-N8's measured "one line on stderr". It is nit-for-nit: no decision
changes, nothing is written, and both prior items were nits.

**C3 — `bootstrap-status.sh`'s pre-existing directory guard still aborts the whole
fleet sync at the first repo, which is the other half of the class F6 closed.
Pre-existing on `main`; not introduced or widened by this PR.**

`scripts/bootstrap-status.sh:158-161` (unchanged since before this branch) exits
**2** when the target is a directory, and `sync.sh` calls it in a plain command
substitution under `set -euo pipefail` (`:850`, `:870`). Measured on the fixture
bares with `.claude/settings.json` committed as a **symlink to a directory**:

```
head 0d73ac4 : exit=2  repos processed=1 of 6  "Sync complete"=0
               last line: bootstrap-status.sh: .claude/settings.json is a directory; pass its .claude/settings.json
main 5f13def : exit=2  repos processed=1 of 6  "Sync complete"=0     (identical)
control, unbroken: exit=0, 6 repos
```

This round *narrowed* the hazard — a symlink to a **file** is now classified
`unparseable` and handled gracefully (`:164`) — but a symlink to a **directory**
still hits the older `-d` branch first. F6's remedy closed the operator-shell
route into this failure; the consumer-repo route remains, and it is the one CI can
actually hit, since the sync runs against ~20 real repos. Filing it as a nit
because the repo shape is far-fetched and **the PR is not its author**; naming it
because it sits squarely in the class this round just worked in. **Fix:** have
`sync.sh` tolerate a non-zero classifier exit
(`state=$(… ) || state="unparseable"`), which turns any future exit-2 shape into
one withheld repo instead of a dead fleet run.

**REPEAT: NO.** Present and identical on `main`; neither introduced nor widened
by these nine commits.

### Recorded, not filed

- A **symlink named `AGENTS.md` in a directory that does carry the payload** is
  followed and judged (`linkdir2` in my gate probe → `MANAGED BLOCK MALFORMED`).
  Round 2 recorded the same shape as *"defensible, recorded"*; the head is
  strictly narrower than the ref here, so this is unchanged, not new.
- `state_oversized()` fires for **any** `User` memory load, so on a machine with an
  oversized state file a User memory file that is not the guidance also gets the
  `fleet-guidance.state is over 65536 bytes` line. The message names exactly what
  it measured and self-heals in one session; not a false verdict.
- `pairs()` in `instructions-report.sh:202` caps the **key** at 200 chars, so two
  `memory_type` values differing only after char 200 would print identically.
  Cosmetic; the values are computed integers.
- **R2-N10** (`sync.sh:1296`'s unguarded `cp`) and **R2-N11** (`${{ inputs.dry_run
  }}`) are record-only by the brief and are confirmed **unchanged**.

---

## 9. What I could not measure

- **The real CLI.** The brief forbids running `claude`, so the event's fidelity
  and "hook stdout reaches nothing on 2.1.261" are still taken on the PR's word.
  Everything downstream of "the hook is handed this JSON on stdin" is measured.
- **Whether any of the ~20 consumer repos actually carries a root `CLAUDE.md`
  bridge that quotes a marker** (C1's live trigger), a `.claude/rules/AGENTS.md`,
  a nested `AGENTS.md`, a `null` under a hooks event key, or a symlinked
  `settings.json`. I cannot enumerate the fleet from this session, and it spans
  two owners. `_agent-guidance`'s own tree carries a root `CLAUDE.md` (the
  `@AGENTS.md` bridge) but it quotes no marker.
- **Behaviour as a non-root user.** The container is root, so a genuinely
  read-only config dir is untestable; I used directories, FIFOs, hard links and
  symlinks blocking the target paths instead. This is also why I could not drive
  `mark_receipt_read`'s `mktemp`-fails branch.
- **`shellcheck`** is not installed; `bash -n` only (clean everywhere, in every
  mutated copy).
- **My own first `ru_maxrss` reading was wrong and I am naming it**: measuring
  `RUSAGE_CHILDREN` from a parent that had just held a 48 MB buffer reported
  60 332 KiB for the head — a fork/COW artifact, since a forked child inherits the
  parent's RSS as its own high-water mark. Re-measured from a fresh process that
  writes the payload in 1 MiB chunks and has reaped no other child: head
  **15 220 KiB**, ref **63 096 KiB**. Only the second measurement is evidence.
- **The post-merge sync against real repositories** — out of scope, and the
  orchestrator's to run.

---

## 10. Recommendation

**One more fix round — but a two-line one, and nothing else is holding this PR.**

Every behavioural item in the round-2 brief is closed, and closed at the class
level rather than at the row that was measured: 60 red-first assertions, 23 of 24
full-suite mutations red, a 15-shape classifier/registrar agreement matrix with no
disagreement, hard links and FIFOs sealed at all four write sites with zero
process survivors, "announced exactly once" true through three separate routes, no
hollow assertion, and a one-way door that parses **identical to `main`** but for
one `paths:` entry. That is a materially better state than round 2.

**C1 is the only thing I would hold for, and it is a test, not a code change.**
The behaviour is right; the floor under it is gone, and it went silently — the
worker had no way to see it, because its own `M-R2S6` mutates the payload guard
while the line that lost its cover is the basename one. Left as is, the next
person to tidy `agents_verdict` deletes two lines that look redundant (the payload
gate appears to subsume them) and ships round-1 adv-S6 to ~20 repos' `CLAUDE.md`
bridges with a green suite. One assertion beside the positive control that already
exists closes it, and `M-R1R7` is the named mutation that proves it. C2 and C3 are
nits and can ride along or follow.
