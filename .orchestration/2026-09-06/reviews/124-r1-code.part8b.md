
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
