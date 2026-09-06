
## The pasted measurement — audited, and independently corroborated

I did **not** run the CLI. Instead I (a) checked the hook's code against every claim, and
(b) read the shipped CLI bundle as data (`grep`/`python3` over `/opt/claude-code/bin/claude`,
never executed). That bundle's highest embedded version string is exactly **`2.1.261`** — the
version the worker names.

**Does the hook depend on anything the measurement says is absent?** No.
`grep 'event.get('` returns exactly five fields: `file_path`, `memory_type`, `load_reason`,
`cwd`, `session_id` — all in the measured set. `globs`, `trigger_file_path`, `parent_file_path`
appear **only inside comments**.

**Does it branch on `load_reason`?** No. Its only two non-comment occurrences are the assignment
and `"load_reason": load_reason` in the log record. Recorded verbatim, never compared.

**Does it rely on stdout reaching the session?** No. Every verdict is written to
`instructions-receipt.state` as well as emitted, `emit()` swallows its own exceptions, and
`fleet-memory.sh` prints the receipt next session. Deleting `emit()` would not change the receipt
lane.

**Corroboration from the bundle** (all four claims):

| Claim | Evidence in `/opt/claude-code/bin/claude` |
|---|---|
| the event's schema | `hook_event_name:C("InstructionsLoaded"), file_path:s(), memory_type:X(["User","Project","Local","Managed"]), load_reason:X(["session_start","nested_traversal","path_glob_match","include","compact"]), globs:k(s()).optional(), trigger_file_path:s().optional(), parent_file_path:s().optional()` |
| `globs`/`trigger_file_path`/`parent_file_path` absent on `session_start` | the emitter `j_t` destructures them from an optional argument (`let {globs:f,triggerFilePath:y,parentFilePath:E,…}=d??{}`) and sets them to `undefined` when the caller passes none — `JSON.stringify` drops undefined keys. Exactly "absent, and optional in the schema". |
| **stdout lands nowhere** | the emitter calls `await TE({session,hookInput:N,timeoutMs:v,matchQuery:o,…});` — **the result is discarded**, unlike the generic runner nearby which reads `.systemMessage`/`.watchPaths` off it. And the CLI's own description: *"Exit code 0 - command completes successfully / Other exit codes - show stderr to user only / This hook is observability-only and does not support blocking."* (The worker quoted this, eliding the trailing "and does not support blocking".) |
| `compact` is a real reason it could not reproduce | it is in the `load_reason` enum and in `matcherMetadata.values`; nothing in the hook depends on it. Non-reproducibility in `claude -p` I cannot check. |

**A bonus the worker did not claim, and it matters.** The matcher for this event is matched
against `load_reason` (`case "InstructionsLoaded": return e.load_reason`, and
`matcherMetadata.fieldToMatch:"load_reason"`), and matchers are otherwise compiled as **regexes**
(`new RegExp(t)`; there is even an `Invalid regex pattern in hook matcher` path). A bare `*` is
not a valid regex — but the matcher function short-circuits first:

```js
function Kmr(e,t,r,o,d,f){ if(!t||t==="*") return true; … }
```

So `"matcher": "*"` is correct and does fire on every load reason. Worth stating because if that
special case did not exist the whole registration would be dead on arrival.

**Does the state-file design close "never silent for more than one session"?** Yes, mechanically,
and I reproduced the full loop: a mismatch recorded by the load-time hook is printed by the next
session's `fleet-memory.sh` **before** its own verdict, and before anything that can degrade, so a
DEGRADED run still reports it. The previous-session line is pinned by 5 assertions in
`test_fleet_memory_state_file`; it is head-only behaviour — the ref hook with the identical
receipt file present prints nothing (`previous session` count = 0) and writes no state file.

One nuance neither the PR body nor the hook header states, and it bears on the headline incident:
`fleet-memory.sh` runs **before memory is assembled** (its own measurement 2), so within a session
it repairs a truncated block *before* the `session_start` load event fires. With only
`session_start` events — the only reason the worker could reproduce — a mid-session truncation is
therefore invisible to the receipt on the next session too; it is caught only if the CLI emits a
reload event (`compact`, `nested_traversal`, `path_glob_match`, `include`) after the truncation.
I reproduced both halves: fire a reload event after truncating and the next session opens with
`fleet-guidance: previous session LOAD MISMATCH — truncated (37 of 233 bytes, no END marker)`;
skip it and the receipt still reads `loaded`. The other two gaps in the stated trio (a config dir
the CLI reads no memory from → `block absent`; an `AGENTS.md` behind or edited) are fully closed
and I reproduced both. Graded as nit N6 rather than a defect: the hook is right, the claim is
just wider than the mechanism.
