
## Findings

No blocker. The hook is observe-only in fact as well as in intent: 22 hostile shapes all exit 0,
nothing is written outside `$CLAUDE_CONFIG_DIR`, no absolute path reaches any log line or verdict,
and every existing behaviour I could measure is unchanged.

### Should-fix

**S1 — nothing in the suite pins that the receipt hook's state feeds `fleet_up_to_date`, and the
failure mode is a repo the sync silently stops repairing.**
Mutation `M6`: delete the two clauses `|| [[ "$instr_hook_state" != "current" ]] || [[
"$instr_reg_state" != "registered" ]]` from `scripts/sync.sh:860-864`. Full suite: **1359 passed,
0 failed** — completely green. Reproduction of what that costs, through `sync.sh` against the
suite's own `bootorg` fixtures with `M6` applied: deliver normally, then delete
`.claude/hooks/instructions-loaded.sh` from `repo-no-lock` and re-run:

```
=== bootorg/repo-no-lock ===
  fleet-memory: mode=stub hook=current payload=current settings=registered
  instructions-loaded: hook=missing settings=registered
  Up to date — skipping.
after run2: hook restored=NO
```

The sync prints `hook=missing` and then calls the repo up to date, forever. The head code is
correct; the point is that a regression removing it is invisible to 1359 assertions. The three
`fleet_*` clauses beside it are pinned (`W18` reddens 2). One assertion — a fixture repo whose
receipt hook is removed and then restored by a second sync — closes it.

**S2 — a `settings.json` that is valid JSON with a non-list `hooks.InstructionsLoaded` gets the
hook file delivered and committed while its registration is refused: "a delivered hook nothing
runs", which is the exact failure `sync.sh`'s own comment says the event seam exists to prevent.**
`bootstrap-status.sh` classifies a non-list value as `no-entry` (not `unparseable`), so
`fleet_deliver` stays true; `register-bootstrap-hook.sh` then correctly refuses with
`refused-unparseable`. Reproduction — set `"InstructionsLoaded": "nope"` on the `repo-adopted`
fixture and run `sync.sh`:

```
run 1:  instructions-loaded: hook missing — written.
        WARN: could not register instructions-loaded in .claude/settings.json (refused-unparseable) — leaving it untouched.
        Pushed directly to main.        ← the hook file is now committed, and nothing runs it
        === Sync complete: 6 synced, 0 skipped, 0 failed ===
run 2:  instructions-loaded: hook=current settings=no-entry
        WARN: could not register … (refused-unparseable) …
        Nothing to commit.
        === Sync complete: 0 synced, 6 skipped, 0 failed ===
```

Benign in the sense that no empty commit is made and no run fails — and that is the problem: the
tally reads `0 failed` forever while the repo carries a dead hook. The same disagreement exists on
`main` for `SessionStart`/`fleet-memory.sh` (I confirmed both trees behave identically for
`{"hooks":{"SessionStart":"nope"}}`), so this is a pre-existing class the PR now reaches with a
second hook, not a regression. Cheapest fix: have `bootstrap-status.sh` return `unparseable` when
`hooks.<event>` is present but not a list — that already routes to "refuse the whole repo, keep
the guidance inline", which is the posture the file's own header describes. Untested either way.

**S3 — the floor paragraph still says the hook "prints one line", and the new lines print
first.**
`agents-md/stub.md` (and the regenerated `AGENTS.md`) keeps `**Check the session-start verdict
before you rely on it.** The hook prints one line:` unchanged, while the same hook can now print
three, and `report_previous_session` runs *before* the hook's own verdict. Reproduction, head
`fleet-memory.sh` with a receipt present:

```
fleet-guidance: previous session LOAD MISMATCH — truncated (154 of 56099 bytes)
agents-md: previous session EDITED ABOVE THE MARKER — found 2
fleet-guidance: installed (vd2742c9f, 6 bytes) -> ~/.claude/CLAUDE.md
```

An agent that took the file at its word and read "the one line" would read *last* session's
`LOAD MISMATCH` as *this* session's verdict and declare itself degraded when it is not. The new
paragraph two screens down does explain it, but the sentence it contradicts comes first. Fix is
one word ("prints its verdict line") plus a clause saying the previous-session lines precede it —
or print them after. `base.md`'s new section already gets this right ("the NEXT session **opens
with**").

**S4 — `scripts/instructions-report.sh` dies with `HOME: unbound variable` when neither `HOME` nor
`CLAUDE_CONFIG_DIR` is set — the same defect this PR fixed in the hook, in the sibling file it
adds in the same commit.**

```
$ env -u HOME -u CLAUDE_CONFIG_DIR scripts/instructions-report.sh
scripts/instructions-report.sh: line 35: HOME: unbound variable      (exit 1)
```

Line 35 is `CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"`; the hook writes
`"${CLAUDE_CONFIG_DIR:-${HOME:-}/.claude}"` at its line 81 with a five-line comment explaining
exactly this, and pins it with `instructions-loaded: no HOME and no config dir still exits 0`
(the PR body lists "an unset HOME as a shell error (2)" among its self-review fixes). The report
is human-run so the blast radius is small, but the message is a shell error rather than the
script's own, and no test covers it. `${HOME:-}` plus the existing usage error closes it.

**S5 — three early-exit paths in the hook do not drain stdin, reintroducing exactly the SIGPIPE
class the hook's own comment says it closed; it already makes one assertion in this suite flaky.**
The python program opens with

```python
# Read stdin to EOF BEFORE deciding whether to parse it. Exiting early on an
# oversized event would leave the writer holding a closed pipe: it takes
# SIGPIPE, exits 141, and a caller running under `pipefail` reads that as the
# hook failing. Draining first costs one buffer and removes the whole class.
raw = sys.stdin.buffer.read()
```

but three shell-level guards above it exit without reading anything: the `FLEET_GUIDANCE_SKIP`
branch (`rm -f …; exit 0`, line 93), `[ -d "$STATE_DIR" ] || exit 0` (line 98), and
`command -v python3 … || exit 0` (line 99). Measured, 200 runs each, `printf … | hook` under
`pipefail` — which is how the suite itself invokes it:

| path | small event | event larger than the 64 KiB pipe buffer |
|---|---|---|
| `FLEET_GUIDANCE_SKIP=1` | **1/200 exit 141** | **10/10 exit 141** |
| `$CLAUDE_CONFIG_DIR` not a directory | **1/200 exit 141** | **10/10 exit 141** |
| normal path (drains) | 0/200 | 0/10 |

I did not go looking for this: mutation `W11` — which only edits a `case` in `fleet-memory.sh` —
came back with a second, unrelated red, `instructions-loaded: skip exit 141`. That is
`test_instructions_loaded_hook`'s `instructions-loaded: skip exits 0` losing the race. A ~0.5%
flake on one assertion in a suite CI runs on every PR is a red run every couple of hundred runs
with no cause in the diff — the kind the fleet's own guidance says not to ship.

Production impact is limited, and I checked rather than assumed: the CLI registers a stdin
`error` handler on both hook paths, and the backgrounded one logs
*"Async hook stdin write failed (…); hook command likely exited without reading stdin"* — it
tolerates the EPIPE. So this is a flaky-test and broken-invariant finding, not a session-breaking
one. `cat >/dev/null 2>&1` before each of the three `exit 0`s closes it.

**S6 — the `sha256` comparison has zero test coverage: the state file's digest is asserted to be
*written* and never asserted to be *read*.**
Mutation `M9`: delete

```python
    want_sha = state.get("sha256", "")
    if want_sha and hashlib.sha256(payload).hexdigest() != want_sha:
        return mismatch("content differs (same length, different bytes)")
```

Full suite: **1359 passed, 0 failed**. `test_fleet_memory_state_file` asserts
`fleet-memory state: records the payload's sha256`, so the field is pinned on the writer side and
nothing at all on the reader side. It is the only detector for an equal-length edit — which I
reproduced directly against the real hook (`CANARY-V` → `CANARY-X` inside an otherwise perfect
block gives `LOAD MISMATCH — content differs (same length, different bytes)`), so the code is
right and only the test is missing. One assertion, using the fixture that already exists three
lines above the truncation case.

### Nits

**N1 — the 1 MB stdin cap is unpinned.** Mutation `M7`: delete `if len(raw) > STDIN_CAP:
sys.exit(0)`. Full suite: **1359 passed, 0 failed**. The test named for it
(`a 10 MB stdin still exits 0` / `produces no traceback`) holds with or without the bound, because
a 10 MB non-JSON string fails `json.loads` and exits 0 anyway. Asserting that the 10 MB case
writes **no log line** — or that a 10 MB *valid* event is refused (I measured that it is) — would
pin it.

**N2 — `no interpreter traceback reaches the session` cannot fail.** The hook ends with
`python3 -c "$PROGRAM" … 2>/dev/null`, so *every* stderr byte is discarded regardless of what the
program does. Reproduction: remove the `file_path` type guard, feed the no-`file_path` event —
`rc=0`, output empty, `Traceback` absent, and no log line written; with the `2>/dev/null` removed
the same run shows `AttributeError: 'NoneType' object has no attribute 'startswith'` at
`relativize`. The silence is deliberate and right; the assertion just certifies the redirection,
not the code. Asserting "a log line **was** written" for each hostile event that names a real
path would catch a crash.

**N3 — an inaccurate comment in `sync.sh`.** "the array is also what the commit message
enumerates, and a path listed twice there reads as a bug" (around `add_paths`, line 1271):
`add_paths` is used only for `git add`; the commit message is one of four fixed strings and lists
no paths. Measured: the delivering commit's subject is `chore: sync AGENTS.md from
_agent-guidance` with no file list. The de-duplication is still worth having (`git add` of a
duplicate is merely harmless), but the stated reason is not the real one.

**N4 — a shell redirection error can still reach the session from `write_state`.** `{ … } >
"$STATE_FILE.tmp" 2>/dev/null` does not cover the failure of its *own* redirection. With a
directory at that path: `fleet-memory.sh: line 99: …/fleet-guidance.state.tmp: Is a directory`
appears beside the verdict (exit still 0, verdict still correct). Contrived, but the file's whole
posture is "a state file that cannot be written costs the next session its verdict and nothing
else". `2>/dev/null` on the outer scope, or `printf … > "$tmp" 2>/dev/null || return 0`, closes it.

**N5 — the receipt's `ts` is written and never read.** `fleet-memory.sh` prints
`previous session …` from whatever is in the file, with no staleness bound. On a machine where the
load-time hook stops running (an older CLI, a repo whose settings lost the entry), a mismatch
recorded once is re-announced as "previous session" every session indefinitely. The field needed
to say "3 weeks ago" is already in the file.

**N6 — the headline incident is narrower than the prose.** `fleet-memory.sh` runs before memory
is assembled, so within a session it repairs a truncated block before the `session_start` load
event fires; with only `session_start` events (the only reason reproducible per the PR's own
measurement) a mid-session truncation is invisible to the receipt on the next session too. Caught
only if the CLI emits a reload event after the truncation — which the `*` matcher does cover, and
which I reproduced by firing one. The other two gaps in the stated trio are fully closed. The hook
is right; the WHY comment and the README lead with the one case the mechanism cannot reach on its
own.

**N7 — the hook never checks `hook_event_name`.** It acts on any JSON object carrying a
`file_path`. Registered only under `InstructionsLoaded` today, so unreachable — but a copy-pasted
settings entry under, say, `FileChanged` (which also carries `file_path`) would silently log
edited files as memory loads. One `if event.get("hook_event_name") != "InstructionsLoaded":
sys.exit(0)` costs nothing.

**N8 — the receipt is read-modify-write, not atomic across concurrent events.** `write_receipt`
reads, merges and `os.replace`s; two hook processes for two files in the same session can
interleave so that a healthy verdict overwrites a mismatch for the *same* key, which is precisely
what the same-session guard exists to prevent. The replace itself is atomic, so nothing is ever
corrupted, and I could not provoke a loss: 30 rounds of a concurrent `BEHIND`/`current` pair on
the same key and 20 rounds of the cross-key pair both lost 0. Recording it because the window is
real, not because I saw it bite.

**N9 — `set -uo pipefail`, not the issue's `set -euo pipefail`.** Documented in the file with a
correct reason (`read -r -d ''` returns 1 at EOF; an always-exit-0 hook must not inherit `-e`).
Noting only because the issue named the flags literally; `|| true` would have satisfied both.

**N10 — three assertions grep the hook's own source.** `assert_not_contains "$INSTR_HOOK"
'"decision"'` (and `"continue"`, `"systemMessage"`) pass on any tree where the file does not
exist, which is why they are among the 18 that stay green on `main`. They are cheap and worth
keeping, but they are a lint of the source, not a test of the behaviour.
