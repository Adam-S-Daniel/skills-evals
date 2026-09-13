FOUND — 0 blocker, 1 should-fix, 5 nit

# _agent-guidance PR #124 — code review, ROUND 4 (one-way-door class)

Head `8ec4cb30a5a5e7156467f961c92a742372f8f3ce` (thirteen commits `df01967..8ec4cb3` on the
round-3 head `0d73ac4`). `origin/main` `5f13def` is an ancestor of the head and is unchanged.
Effort: high — everything below is measured through a production entry point
(`bash .claude/hooks/instructions-loaded.sh` with JSON on stdin, `bash .claude/hooks/fleet-memory.sh`
as a SessionStart, `bash scripts/bootstrap-status.sh` / `scripts/register-bootstrap-hook.sh` with
exactly the environment `sync.sh` gives them, `bash scripts/instructions-report.sh`, and
`./test/run-tests.sh`), never read off the diff.

**Verdict.** Every one of the thirteen items landed, and twelve of the thirteen are killed by a
named mutation on the FULL suite. B1 — the round-3 blocker — is closed at the class level and not
at the measured row: the classifier now answers the CONTENT question through the link and the
file-type question separately, all five of its callers were re-checked, and the end-to-end sync
row is pinned (`M-B1` → 1704/12, first fail *the repo keeps the stub*). The round-3 code
should-fix (C1, the lost basename floor) is genuinely restored: `M-R1R7` is **red again, 1712/4**.
The one-way door needs nothing — parsed, `sync.yml` is identical to `main` once `on.push.paths`
is masked, and `git diff 0d73ac4..8ec4cb3 -- .github/` is empty by command.

**What holds it.** A **FIFO (or a directory) at `$CLAUDE_CONFIG_DIR/instructions-receipt.state`
hangs `fleet-memory.sh` for the whole of its registered timeout and orphans a blocked `grep`** —
measured, rc 124 at a 15 s bound with the child alive afterwards, and the guidance is not
installed at all that session. It is not a regression against `0d73ac4`, but it IS introduced by
this PR (`main`'s `fleet-memory.sh` reads no receipt), it is R2-S2's exact class on the one
surface the remedy never enumerated, and this very round closed that class on the third surface
(`instructions-report.sh`, item N4/N5) while `instructions-loaded.sh` had already closed it on
four write sites. The sibling hook survives the identical plant in 46 ms. One line fixes it.

---

## 1. Tree integrity

| item | start | end |
|---|---|---|
| `md5sum /root/.claude/CLAUDE.md` | `935c291f2efb1ff55a463bccfde55e6a` | `935c291f2efb1ff55a463bccfde55e6a` — unchanged |
| the ten brief md5s on `$SP/rev124d-code` | all ten matched the brief | all ten matched again (listed below) |
| `diff -rq --exclude=node_modules $SP/rev124d-code <fresh git archive 8ec4cb3>` | — | **no output — byte-identical** |

```
f9b066b35c207d1f3d18faa1a408abe4  .claude/hooks/instructions-loaded.sh
0a872d4b09fafcb994332a936029eb8c  .claude/hooks/fleet-memory.sh
06c9cd21733b4bd8068759e02e02124f  .claude/settings.json
02767fc3112ed83c6670e950608d0d1d  .github/workflows/sync.yml
9e25051a3dc692640e9a448ab1cda768  scripts/sync.sh
2aa2f853966c2c84be915d10cbd3f94a  scripts/bootstrap-status.sh
81fa1f79f45aacab013740e2a3a6b3f3  scripts/register-bootstrap-hook.sh
544d52e8821d487a82cc289672b4cb5b  scripts/instructions-report.sh
e32fe8d839224b10fdea71a88248624b  scripts/drift-report.sh
390e2de6a47cfb659bd76623e3645182  test/run-tests.sh
```

**Hygiene.** Nothing was executed inside `$SP/rev124d-code` or `$SP/rev124d-ref` other than the
scripts under review being invoked from them with a throwaway `HOME`; every suite run and every
mutation ran in a `git archive` export or a `cp -a` of one under `$SP/r4mut124-*`, and **all four
base trees plus every mutation copy are deleted** (`ls -d $SP/r4mut124-*` → nothing). Every shell
that ran `sync.sh` or any script began `unset GH_TOKEN GITHUB_TOKEN` and printed
`GH_TOKEN='<unset>' GITHUB_TOKEN='<unset>'`. `sync.sh` ran **only** inside the suite, against the
fixture bares the suite builds under `mktemp -d` with its own `create_mock_gh`; no real repo, no
real `gh`, no real `claude`, no network, nothing posted to GitHub, no credential read beyond the
two `md5sum` calls above. `/home/user/_agent-guidance` was touched with read-only git only
(`log`, `show`, `diff`, `archive`, `status`, `rev-parse`, `merge-base`); it is clean and still on
its own branch. I did not enter `$SP/rev124d-adv`, `$SP/r4adv124-*`, `$SP/se-*` or any
`.claude/worktrees/*`.

**Processes: 5 killed, all mine.** Two from my head-tree FIFO probe (the blocked
`grep -m1 -- ^unread=` and its `fleet-memory.sh` parent, which outlived `timeout --foreground -k 3`
because bash defers the signal while a foreground child blocks); two more blocked `grep`s reaped
by the bounded probe's own `pkill`; and one `python3 -c` from the REF registrar blocked on a FIFO,
leaked by my hollow run (R2-N2 reproducing on `0d73ac4`, alive 2 421 s before I killed it).
Two foreign `fleet-memory.sh` processes under `/tmp/guidance-checkout-*` were observed, are not
mine, and were left alone. At the end nothing of mine survives.

**Provenance.** `git merge-base --is-ancestor 5f13def 8ec4cb3` → 0; `… 0d73ac4 8ec4cb3` → 0.
`git log --format='%ae %ce' 0d73ac4..8ec4cb3 | sort -u` → exactly one line,
`4205216+Adam-S-Daniel@users.noreply.github.com` twice. `git diff --stat 0d73ac4..8ec4cb3` =
8 files, +1500 / −169 (no `agents-md/`, no `AGENTS.md`, no `.github/`).

## 2. Verifier table

| run | tree | result | exit |
|---|---|---|---|
| head | `8ec4cb3` | **1716 passed, 0 failed** | **0** |
| ref | `0d73ac4` | **1584 passed, 0 failed** | **0** |
| red-first (head's `test/run-tests.sh` spliced onto a `0d73ac4` export) | — | **1642 passed, 74 failed** | 1 |
| head | `bash scripts/check-agents-md.sh` | — | **0** |
| head | `node scripts/check-guidance-coverage.js --check-bytes` | `28 gap · 1 skipped · 0 covered` | **0** |
| head | `node scripts/check-registry.js` | — | **0** |
| head | `node scripts/check-guidance-touch.js` | `no event file: GITHUB_EVENT_PATH is not set` | 2 (CI-only shape; not a finding) |
| — | `yq --version` | `v4.53.3` (mikefarah, first on PATH) | — |

Both counts match the brief exactly. Every count is parsed from the runner's own `Results:` line
with `$?` captured unpiped, never off a pipeline. 1642 + 74 = **1716**, the head's full total, so
the red-first run did not abort under `set -e` and all 74 failures are real.

## 3. Hollowness — where the 132 added assertions go

Assertion-NAME diff, head vs ref: **136 added, 4 removed, net +132** = 1716 − 1584. The four
removals are three renames of the same rows the new behaviour renamed (`directory argument ->
exit 2 caller error` → `-> unwritable, exit 0`; the two `symlinked settings.json` classifier/
registrar rows) plus one row whose name embeds a measured RSS number. **No coverage was deleted.**

Of the 136: **74 are RED on `0d73ac4` through the production entry points**, and every one maps to
a brief item —

| red rows | item |
|---|---|
| 1 (`directory argument -> unwritable, exit 0 (got rc=2)`) | S3 |
| 2–15 (`register: timeout 08/09/010/0100/019/0999 …`) | C2 |
| 16–24 (`symlinked settings (registered/no entry): …` via `sync.sh`, incl. `AGENTS.md changed (57971 bytes, was 5686)`) | B1 (a)(c)(d)(e) |
| 25–30 (`settings dir: the run exited 2`, `4 of 6 repos processed`, `the run reaches its summary`) | S3 |
| 31–35 (`claude dir link: 4 of 6 repos processed`, `the tally counts the one repo that failed`, `the run exited 128`) | S4 |
| 36–39, 51 (classifier/registrar on a registered link, a dangling link) | B1 (a)(b) |
| 40–44 (`settings shapes:` directory traceback, FIFO rc 124) | S3 / adv-N2 / adv-N3 |
| 45–50 (`weak needle:` `' '`, `'.'`, `'s'` on both halves) | N10 |
| 52–56 (`20 concurrent pairs produced 40 announcements`; `a failed rewrite says so out loud`; `a failed claim says so out loud too`) | S1, S2 |
| 57–63 (empty / over-cap payload, and `e3b0c442` never printed) | N9 |
| 64–69 (dir and FIFO at the state path reach the verdict AND the receipt) | N7 |
| 70–74 (dir and FIFO at the log path: exit 3, named, not "has not run here") | N4/N5 |

The other **61 are green on the ref by construction and are legitimate**: fixture preconditions
(`git really stored a symlink (mode 120000)`, `the fixture starts fully delivered and on the stub`
— which `return`s the whole test if it fails, so no row below it can prove nothing), negative
controls (`nothing was written through the link`, `the link is still a link`, `neither the
directory nor the FIFO was replaced`), in-range timeout rows, and two regression floors over
already-correct code: **C1** (`root CLAUDE.md / NOTES.md beside the payload is not judged`) whose
named mutation `M-R1R7` is red at 1712/4, and **N11** (`JSON that is not an object exits 3`) — see
nit 3. No unmapped failure; no floor without a red mutation except the two named in the nits.

**Vacuity.** All 12 new `assert_not_contains` uses: nine are red-first (so non-vacuous by
measurement); `…/out_root_notours "agents-md:"` reddens under `M-R1R7`; `…/out_log_fifo
"has not run here"` reddens under `M-N45`; `…/out_nondict "has not run here"` sits beside
`assert_contains "$d/out_nondict" "4 line(s)"` in the same block, so the file is proven non-empty.
Suite hygiene over the 934 added test lines: `/tmp/` literals **0**, writes under `$HOME`/`~`
**0** (the single `~/` is inside a comment), `../` traversal **0**, `/root`,`/Users`,`/home/`
**0**, email/real domains **0**; 3 `mkfifo`s against 11 `timeout --foreground` bounds.

## 4. Per-item certification

| # | commit | landed | red-first (line pasted from the 1642/74 run) | mutation on the FULL suite | surface enumerated | verdict |
|---|---|---|---|---|---|---|
| **B1** | `df01967` | `bootstrap-status.sh:166-224` (symlink answered by CONTENT, `unwritable` otherwise; `-f` **and** `-s` before `classify < "$1"`), `sync.sh:939-966,1144` (`unwritable` withholds the WRITE; `unparseable` unchanged), `register-bootstrap-hook.sh:81,100` (`refused-symlink` / `refused-not-a-regular-file`) | `FAIL: symlinked settings (registered): AGENTS.md changed (57971 bytes, was 5686)`; `FAIL: … the reason names the symlink, not a syntax error`; `FAIL: … 'hook=current payload=current settings=unwritable'` | **M-B1 1704/12**, first fail *the repo keeps the stub* | **all five callers of `bootstrap-status.sh`**: `sync.sh` ×3 (fleet :919, instr :926, skills-bootstrap :1131 — each has its own `unwritable` branch and its own `settings_shape` reason), `drift-report.sh` ×2 (**stdin `-` only**, so the file-type answer is unreachable there — its `!= "unparseable"` comparison stays correct), and the suite. Registrar's new answers are consumed only by `sync.sh`'s `WARN … ($result)` line, which prints whatever it gets. | **CLOSED** |
| **S1** | `47a2503` | `fleet-memory.sh:91-160` — `mv` to `.claim.$$` **before** the read; `restore_receipt` puts a copy back with `ln` (EEXIST loses to a newer receipt) and unlinks, so nlink returns to 1 | `FAIL: fleet-memory claim: 20 concurrent pairs produced 40 announcements, not 20` | **M-S1 1705/11** (`mv`→`cp`), first fail *the same verdict is never announced twice* | my own 20 zero-stagger pairs: **HEAD 20 announcements / 0 strays; REF 40 / 0.** Residual window (receipt name absent between claim and write-back) is documented in the file and costs a sibling key, not a wrong verdict. | **CLOSED** |
| **S2** | `47a2503` | `fleet-memory.sh:150-186` — `cleared` covers mktemp **and** the redirection; the claimed original is restored when the rewrite fails; a failed claim gets its own distinct sentence | `FAIL: … a failed rewrite says so out loud, not only a failed mktemp`; `FAIL: … a failed claim says so out loud too` | **M-S2 1714/2** | the other write in this file is `write_state`, already wrapped the same way; the receipt's own write side is `instructions-loaded.sh`'s `open_owned`. Both enumerated in the commit. | **CLOSED** |
| **S3** | `83b30cd` | `bootstrap-status.sh:206-224` (`! -f` → `unwritable`, `-f` is a stat so nothing is opened), `sync.sh:919/926/1131` `\|\| …="unparseable"`, `register-bootstrap-hook.sh:99` + `S_ISREG` on the **opened fd** | `FAIL: settings dir: the run exited 2`; `FAIL: settings dir: 4 of 6 repos processed`; `FAIL: settings shapes: the registrar answered rc=124 '' for fifoshape.json` | **M-S3 1710/6**; **M-S3b 1716/0** (see nit 2) | directory, FIFO, socket, device and dangling link all land on the same `! -f` branch; the registrar's second lock is on the fd, not the name. | **CLOSED** |
| **S4** | `e27ac62` | `sync.sh:196-213` `repo_git()`; guards on `cd`, both `git config`, `remote set-url` and `git add`; each failure `fail`s by repo name, `((FAIL_COUNT++))`, `cd "$REPO_ROOT"; continue` | `FAIL: claude dir link: 4 of 6 repos processed`; `FAIL: … the run exited 128` | **M-S4 1711/5** | the commit enumerates the rest of the loop's git calls (`check-ignore`, `diff --cached`, `commit`, `push`, `ls-remote`, `checkout`, `rev-parse`, `fetch`, `log`) as already inside an `if`/`\|\|`/`&&`; I re-read the loop and agree — these four were the bare ones. | **CLOSED** |
| **C1** | `45dc8b6` | test-only: a root `CLAUDE.md` bridge quoting `@AGENTS.md` + `BEGIN MANAGED SECTION`, and a `NOTES.md`, beside the payload, each asserted to produce no `agents-md:` line **and** no receipt key | (floor — green on the ref, correctly) | **M-R1R7 1712/4**, first fail *root CLAUDE.md beside the payload is not judged as AGENTS.md* — **red again** (it was 1584/0 green at round 3) | the sink is `agents_verdict`'s two gates; the payload gate keeps its own `M-N9`/`M-R2S6` cover, the basename gate now has its own. adv-N8's docstring `never` was narrowed rather than the code changed, and the docstring now claims exactly the basename-AND-payload pair. | **CLOSED** |
| **N7** | `5460b98` | `instructions-loaded.sh:351-383` `state_unusable()` returns a REASON (`not a regular file` / `over N bytes` / `not readable`), `None` for absent | `FAIL: a dir at the state path leaves a mark rather than nothing`; `… a fifo …`; `… reaches the receipt too` | **M-N7 1710/6** | absent stays silent (deliberate); a symlink to a regular file is still read through, which is `read_kv`'s pre-existing posture and fail-closed (no `version=` key ⇒ no verdict). | **CLOSED** |
| **N4/N5** | `f1c8171` | `instructions-report.sh:126-148` `lexists`+`isfile`+`O_NONBLOCK`, `unreadable` counter, new exit-3 branch | `FAIL: a dir at the log path exited 2, expected 3`; `FAIL: a fifo at the log path exited 124, expected 3` | **M-N45 1710/6** (all six rows, incl. the FIFO `assert_not_contains`) | the same guard covers the rotated `instructions-log.jsonl.1` (same `files` loop). | **CLOSED** |
| **N9** | `c3ee0c7` | `instructions-loaded.sh:639-657` — empty and over-cap payloads answer `cannot compare …` instead of a digest | `FAIL: an empty payload … says it cannot compare`; `FAIL: the sha of the empty string is never printed`; `FAIL: an over-cap payload … names the cap it went past` | **M-N9 1709/7** | a payload that is a directory/FIFO returns `None` from `read_bytes` and is silent — same answer as "not the synced AGENTS.md", which is defensible and unchanged (recorded). | **CLOSED** |
| **N10** | `8f5836d` | `bootstrap-status.sh:80-83` and `register-bootstrap-hook.sh:136-137`, both `^[A-Za-z0-9][A-Za-z0-9._-]*\.sh$` | `FAIL: weak needle: the classifier answered rc=0 'registered' for BASENAME=' '` (+5) | **M-N10 1710/6** | every caller passes a literal: `sync.sh` ×4 (`fleet-memory.sh`, `instructions-loaded.sh`), the two defaults `skills-bootstrap.sh`. I measured all of them plus `../x.sh` and `a.sh.bak` — accepted/refused as intended. | **CLOSED** |
| **C2** | `f9a284f` | `register-bootstrap-hook.sh:152-153` — the range is in the pattern, `^([1-9][0-9]{0,2}\|[1-2][0-9]{3}\|3[0-5][0-9]{2}\|3600)$` (tighter than the brief's suggestion, which would have admitted 3999) | `FAIL: register: timeout 08 wrote 2 lines on stderr` (+13) | **M-C2 1702/14** | my own matrix: `1,999,1000,2999,3000,3599,3600` accepted; `0,3601,4000,08,09,010,0100,abc,' 10 '` refused `refused-bad-env` rc 2, **one** stderr line, file untouched. | **CLOSED** |
| **N11** | `c007470` | `instructions-report.sh:157-172` — `isinstance` above the `.get`, with its own `try` around the `.get` pair | (floor — green on the ref) | **M-N11 1716/0 — green.** The class *is* pinned: deleting the guard **and** the inner `try` gives `AttributeError: 'int' object has no attribute 'get'`, rc 1 (measured). | see nit 3 | **LANDED, see nit** |
| **N12 + C0/DEL docs** | `34db5e1`, `8ec4cb3` | `run-tests.sh:19054-19071` now says the decision is the pair; the three `clean()` claims in `instructions-loaded.sh:420-427`, `instructions-report.sh:95-98` and `fleet-memory.sh:139-142` all say C0 and DEL and record C1 as surviving | — (prose) | — | all three strip sites named. | **CLOSED** |

## 5. Round-1 / round-2 regression rows (one measurement each, on head)

| row | measured |
|---|---|
| hard link / FIFO / symlink / directory at **every** write site (`instructions-log.jsonl`, `.jsonl.1`, `instructions-receipt.state`, `fleet-guidance.state`) — 16 plants | **rc 0 every row, 43–56 ms, the outside file byte-identical every time, zero stderr bytes, zero survivors** |
| announced exactly once | 20 zero-stagger pairs: **HEAD 20, REF 40**; a single receipt announced at SS#1 and silent at SS#2/#3; receipt left `unread=0` with the verdict preserved; 0 strays |
| classifier ↔ registrar agreement | 13 shapes measured by hand (regular registered/no-entry/unparseable/empty/absent; links to each of those, to a directory, to a FIFO, dangling; a directory; a FIFO): **every row agrees about what is written — nothing — and no link target changed md5.** The only pair that "disagrees" is by design: `registered` + `refused-symlink`, i.e. nothing needs writing and nothing may be written |
| withholding is the pair, not the repo | the eight `instr unusable (nope)` rows all pass at head, including *the repo keeps the STUB* and *AGENTS.md keeps the stub, not 52 kB of inline guidance* |
| dry/real parity | asserted byte-for-byte on the decision lines in both new symlink rows, and still passing on the `nope`/`null` rows |
| no control byte on any printed surface; hostile events exit 0 with empty stderr; no parseable JSON line | 33 hostile events (file_path null/number/list/empty/relative/`../`/`/dev/zero`/`/dev/null`/`/proc/self/environ`/NUL/newline/4 000 chars; `hook_event_name` wrong/empty/null/number/lowercase/list; `memory_type`/`session_id`/`load_reason` null/number/list/ANSI/200 kB; stdin empty/garbage/`[]`/`42`/`null`/valid-then-garbage/NUL/invalid UTF-8): **0 non-zero exits, 0 stderr bytes, 0 control-byte lines, 0 parseable JSON objects.** Positive control in the same harness: a User load prints `fleet-guidance: LOAD MISMATCH — block absent…` and writes the receipt, so the zeroes are not vacuous |
| delivered hook is VERBATIM | the suite clones the fixture bare fresh and `cmp -s`s the delivered `.claude/hooks/instructions-loaded.sh` against the repo source — passes at head (*instr repair: the deleted hook is restored byte-identical*), and `sync.sh` only ever `cp`s the source and states drift with `cmp -s` |

## 6. The one-way door, read independently

`git diff 0d73ac4..8ec4cb3 -- .github/` → **empty** (command run, no output).

Parsed with the repo's own `yaml` package (`YAML.parse` in node), head vs `main` `5f13def`:

| check | result |
|---|---|
| identical once `on.push.paths` is masked | **true** (deep string compare of the whole document) |
| paths added / removed | added `[".claude/hooks/instructions-loaded.sh"]`; removed `[]` |
| every `uses:` a bare 40-hex SHA | **3/3** — `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5`, `actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1` ×2; raw lines carry **no trailing comment** |
| `${{ }}` inside a `run:` | exactly one, `${{ inputs.dry_run }}` — **and `main` has exactly the same one**; `workflow_dispatch` input, `type: boolean`, `default: false`. Unchanged, so not a finding (R2-N11, record-only) |
| `pull_request` trigger | **absent**; triggers are `["push","workflow_dispatch"]`, same as `main` |
| permissions | top-level `{"contents":"read"}` on both; **no job- or step-level `permissions:`** on either |
| `concurrency` on a required context | **none**, workflow or job level, on either side |

**`scripts/sync.sh`, the delivery decision.** The `unset BOOTSTRAP_HOOK_*` seam is unchanged this
round (`:77-78`, above `mktemp -d` and far above the first classifier call). Every state is now
measured *before* any decision (the three `cmp`s moved out of the `else`), which is what makes the
log line describe the repo rather than the branch. `fleet_deliver` is withdrawn on exactly three
conditions — missing source, `.claude/` gitignored, and `unparseable`/`unwritable` where the hook
is *not* registered — and `$fleet_deliver || instr_deliver=false` plus the `if $fleet_deliver`
block that contains both writes means **the new hook reaches a consumer only on the same decision
that delivers `fleet-memory.sh`**, never on its own. The instr half can be withheld alone
(`unparseable`/`unwritable` on its own event key) without touching the fleet pair or the stub.
`git add` is now guarded, the settings path is added once, and the copy is a plain `cp` of the
repo source with a `cmp -s` drift test, so delivery is verbatim by construction and by assertion.

## 7. Gates and the guidance ledger

`check-agents-md.sh` 0 · `check-guidance-coverage.js --check-bytes` 0 (`28 gap · 1 skipped ·
0 covered`, so the `bytes: 1189` row was verified, not just present) · `check-registry.js` 0.
`agents-md/eval-coverage.yml` carries the row `id: session-start-verdict-is-not-what-loaded`,
`file: agents-md/base.md`, `status: gap`, `bytes: 1189`; `docs/guidance-impact.md` carries **two**
entries for that id — a `create` (2026-09-05) and a `rejected` (2026-09-07, recording why issue
#123's item 1(b) was not implemented). `check-guidance-touch.js` needs `GITHUB_EVENT_PATH` and so
can only run in CI; nothing changed under `agents-md/` this round, so it has nothing new to say.

---

## 8. Findings

### Should-fix

**S-1 — a FIFO or a directory at `$CLAUDE_CONFIG_DIR/instructions-receipt.state` hangs
`fleet-memory.sh` until its timeout kills it, leaks a blocked `grep`, and installs no guidance
that session. R2-S2's class, on the one surface its remedy never enumerated — and the surface this
PR added.**

`.claude/hooks/fleet-memory.sh:91-115`:

```bash
    [ -r "$RECEIPT_FILE" ] || return 0
    ...
    claim="$RECEIPT_FILE.claim.$$"
    if ! mv "$RECEIPT_FILE" "$claim" 2>/dev/null; then
    ...
    unread="$(grep -m1 -- '^unread=' "$claim" 2>/dev/null | cut -d= -f2-)"
```

`-r` is a stat, true for a FIFO; `mv` renames it happily; `grep` then opens it for reading and
**blocks for a writer that never comes**. `report_previous_session` runs before the hook installs
anything, so the whole hook is stuck there.

**Reproducing input** (bounded, on a throwaway `HOME`):

```bash
b=$(mktemp -d); mkdir -p "$b/.claude"; mkfifo "$b/.claude/instructions-receipt.state"
HOME=$b CLAUDE_CONFIG_DIR=$b/.claude timeout --foreground -k 3 15 \
  bash .claude/hooks/fleet-memory.sh <<< '{"hook_event_name":"SessionStart","session_id":"s1","source":"startup"}'
```

```
HEAD 8ec4cb3 : rc=124 at 15s, stdout EMPTY, one surviving `grep -m1 -- ^unread= …claim.24852`
REF  0d73ac4 : rc=124 at 15s, stdout EMPTY, one surviving `grep -m1 -- ^unread= …receipt.state`
main 5f13def : rc=0 in 0s — main's fleet-memory.sh reads no receipt at all
```

The same plant at the same path against the **sibling** hook, which solved this in round 2:
`instructions-loaded.sh` → **rc 0 in 46 ms, no survivor** (my 16-row write-site table above). So
the fix is not conjecture; it is the posture the other half of this PR already ships.

A **directory** at that path is the same guard's other half: `mv` succeeds, `grep` reads nothing,
`restore_receipt`'s `ln` fails, and the directory is left **abandoned in the config dir** as
`instructions-receipt.state.claim.<pid>` (measured — `entries left: … instructions-receipt.state.claim.4319`).

**Impact.** No wrong write and nothing escapes the config dir — but every session start in that
directory stalls for the hook's registered timeout (30 s in the shipped `settings.json`), the
fleet guidance is **not installed at all** for that session, and an orphaned process is left each
time. It does not self-heal: nothing removes the FIFO. Trigger is local write access to
`$CLAUDE_CONFIG_DIR`, which is exactly the privilege R2-S1/S2 were graded on — not reachable
through `sync.sh` or a consumer repo (git stores neither shape at a `$HOME` path).

**The fix I would make** — one line, before the claim, closing both shapes:

```bash
    [ -f "$RECEIPT_FILE" ] || return 0     # not a regular file: nothing to claim, and
                                           # grep on a FIFO blocks for a writer that never comes
```

plus a bounded test per shape (the suite already has the `timeout --foreground 20` idiom in the
`settings shapes` block), and the same `mv`-then-abandon problem disappears with it.

**REPEAT: YES — R2-S2's class, not its row.** R2-S2 was graded should-fix and its remedy was
described as "shut at all five write sites"; the receipt *read* in `fleet-memory.sh` was never in
the enumeration, and this round closed the identical class on `instructions-report.sh` (item
N4/N5, *"use `os.path.isfile` as the hook does"*) without turning the same eye on the hook that
runs on every session start in ~20 repos. It is **not** a regression against `0d73ac4` — it is
equally open there — but `main` cannot exhibit it, so the PR introduces it. Same severity as
R2-S2, same one-line shape of fix.

### Nits

1. **The stray `.claim.$$`.** `restore_receipt` (`fleet-memory.sh:188-193`) unlinks its source only
   when `ln` succeeds, and `report_previous_session`'s `unread != 1` path calls it and returns
   without a cleanup. If a load-time hook wrote a fresh receipt during the window, the claimed copy
   is left in the config dir forever. The `mark_receipt_read` path already cleans up both copies
   unconditionally; this path should too (`rm -f "$claim"` after the restore). Closed for the
   exotic shapes by S-1's one-liner; this is the ordinary-file half.
2. **`sync.sh`'s `|| …="unparseable"` tolerance has no reachable trigger.** `M-S3b` (both sync call
   sites' `||` removed) is **1716/0 green**: since the classifier no longer exits 2 for any file
   type, and `F6` unsets the ambient seam, nothing can make it answer non-zero. The brief asked for
   both belt and braces and both landed; the belt is pinned by `M-S3` (1710/6). Worth one clause in
   the comment saying the guard is deliberately unpinnable ("a standing guard against a FUTURE
   non-zero answer" — the comment nearly says this already), so the next reader does not file it as
   dead code or write a test that cannot exist.
3. **N11's moved guard is behaviourally inert.** `M-N11` (delete the `isinstance` check alone) is
   **1716/0 green**, because the `try` that now wraps the `.get` pair catches the same four shapes.
   The commit message says the guard "is one [doing something]" now; it is *reachable* now, which is
   a readability gain, but deleting it still changes nothing. The three new rows pin the class, not
   the line — and the class does have a red mutation (guard + inner `try` removed → `AttributeError:
   'int' object has no attribute 'get'`, rc 1, measured). No change needed; recorded so nobody
   re-derives it.
4. **A comment is attached to the wrong function.** `sync.sh:184-189` — *"What is actually AT a
   path, in words, for a withholding reason…"* — documents `settings_shape()`, but `e27ac62`
   inserted `repo_git()` and its own comment between them, so `settings_shape()` is now undocumented
   and `repo_git()` carries a paragraph about withholding reasons. In a file whose comments are the
   primary artifact this is worth the two-minute move.
5. **`repo_git` prints a git error line for a command whose argument carries the App token.**
   `sync.sh:207` prints `head -1` of git's combined output for, among others,
   `remote set-url origin https://x-access-token:$GH_TOKEN@github.com/…`, and this runs in a public
   Actions log. Measured: git answers `error: No such remote 'origin'` and never echoes the URL, so
   there is no leak today — one clause in the comment recording *why* it is safe would keep a future
   `--verbose` or a different git from turning it into one.

### Recorded, not filed

- A **symlink at `fleet-guidance.state`** is still read through (`read_kv`/`state_unusable` use
  `isfile`), unchanged posture, fail-closed (a foreign file yields no `version=` key and no verdict).
- A **directory at `fleet-guidance.md`** makes `agents_verdict` silent rather than "cannot compare";
  identical to "not the synced AGENTS.md", defensible, and outside N9's scope.
- The one `${{ inputs.dry_run }}` in a `run:` block is byte-identical to `main` (R2-N11).
- The three unguarded `cp`s at `sync.sh:1259/1267/1296` (R2-N10) are unchanged, as declared.
- `drift-report.sh` gained the same `||` tolerance plus an `if` where a `A && B || C` chain would
  have mis-set `unparseable` for every repo with no settings.json. Unasked-for but correct, and the
  classifier's file-type answers cannot reach it (it only ever uses stdin mode).

## 9. Mutation table — 13, all on the FULL suite, each anchor asserted unique, `bash -n` clean on all six shell files before every run

| # | what it removes | passed / failed | exit | first failing assertion |
|---|---|---|---|---|
| **M-B1** | the classifier's content-through-the-link answer (back to `unparseable`) | 1704 / 12 | 1 | `symlinked settings (registered): the repo keeps the stub` |
| **M-S1** | the atomic claim (`mv` → `cp`) | 1705 / 11 | 1 | `fleet-memory state: the same verdict is never announced twice` |
| **M-S2** | the loud line's cover of the rewrite | 1714 / 2 | 1 | `a failed rewrite says so out loud, not only a failed mktemp` |
| **M-S3** | `unwritable` for a directory (back to `exit 2`) | 1710 / 6 | 1 | `directory argument -> unwritable, exit 0 (got rc=2, stdout '')` |
| **M-S3b** | `sync.sh`'s `\|\| …="unparseable"` at both call sites | **1716 / 0** | **0** | — (nit 2) |
| **M-S4** | the `git add` guard | 1711 / 5 | 1 | `claude dir link: 4 of 6 repos processed` |
| **M-R1R7** | the basename gate in `agents_verdict` | 1712 / 4 | 1 | `root CLAUDE.md beside the payload is not judged as AGENTS.md` |
| **M-N7** | `state_unusable`'s non-regular-file reason | 1710 / 6 | 1 | `a dir at the state path leaves a mark rather than nothing` |
| **M-N45** | the report's `unreadable` counting | 1710 / 6 | 1 | `a dir at the log path exited 2, expected 3` |
| **M-N9** | the empty / over-cap payload branches | 1709 / 7 | 1 | `an empty payload beside AGENTS.md says it cannot compare` |
| **M-N10** | both basename-shape guards | 1710 / 6 | 1 | `weak needle: the classifier answered rc=0 'registered' for BASENAME=' '` |
| **M-C2** | the pattern range (back to the octal `-ge`) | 1702 / 14 | 1 | `register: timeout 08 wrote 2 lines on stderr` |
| **M-N11** | the moved `isinstance` guard | **1716 / 0** | **0** | — (nit 3; the pair mutation is red) |

## 10. What I could not measure

- **The real CLI.** Forbidden, so the event's fidelity, whether hook stdout reaches anything, and
  whether the CLI reaps a hook's grandchildren on timeout stay on the PR's word. My S-1 leak
  measurement is of `timeout --foreground -k`'s kill semantics, which is the same shape (a signal
  to the wrapper) and not a measurement of the CLI.
- **Whether any real consumer carries a symlinked `settings.json`, a symlinked `.claude/`, a
  directory at `settings.json`, or a FIFO in a config dir.** The fleet spans two owners and I
  cannot enumerate it from here; `_agent-guidance`'s own tree carries none of them.
- **Behaviour as a non-root user.** The container is root, so an unreadable file could not be made;
  I used directories, FIFOs, links and dangling links instead.
- **`shellcheck`** is not installed — `bash -n` only, clean on every tree including all 13 mutants.
- **The post-merge sync against real repositories** — out of scope, and the orchestrator's to run.
