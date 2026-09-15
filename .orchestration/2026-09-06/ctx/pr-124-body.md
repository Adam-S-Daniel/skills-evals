# _agent-guidance PR #124 body (the worker's report), head 5215628

Closes #123.

## What

The session-start verdict (`fleet-guidance: installed / current / DEGRADED`) reports what `fleet-memory.sh` did **to the file**. It cannot report what the session **loaded**, and three things live in that gap: a `CLAUDE_CONFIG_DIR` the CLI reads no memory from; a block truncated *after* the session started (2026-09-05: 56,099 bytes → 154, silent until the next SessionStart); and a repo `AGENTS.md` behind the guidance in context or edited above its marker.

1. **`.claude/hooks/instructions-loaded.sh`** — observe-only, exits 0 on every well-formed or hostile event, writes nothing outside `$CLAUDE_CONFIG_DIR`, honours `FLEET_GUIDANCE_SKIP`. On a `User` load it compares the block in context against the state file: `fleet-guidance: loaded (v<id>, <n> bytes)`, or `LOAD MISMATCH — stale version / truncated / block absent / content differs`. On a `Project` load carrying the managed header: `agents-md: current (v<id>)`, `BEHIND — this repo ships v<x>, the session loaded v<y>`, or `EDITED ABOVE THE MARKER — <reason>`. Every event appends one JSON line — `ts, session, load_reason, memory_type, file_path, bytes, sha256` — to `instructions-log.jsonl`, rotated at 1 MB, with a **relative** `file_path`.
2. **`fleet-memory.sh`** gains exactly two things: it writes `fleet-guidance.state` (version, bytes, sha256, verdict), and it prints the *previous* session's receipt beside its own verdict. `test_fleet_memory_hook` is byte-for-byte unchanged (asserted against `origin/main` while working, not claimed).
3. **`scripts/instructions-report.sh`** totals the log per session — bytes per `memory_type`, files per `load_reason`. Exit 2 when there is nothing to report; never prints an absolute path.
4. **Registration**: `register-bootstrap-hook.sh` and `bootstrap-status.sh` grew one env seam (`BOOTSTRAP_HOOK_EVENT`, default `SessionStart`) rather than gaining a second registrar; `sync.sh` delivers and registers the hook on the same decision as `fleet-memory.sh`. `sync.yml` gains one `paths:` entry — which `test_sync_workflow_trigger` demanded on its own, since it derives the watched set from `sync.sh`'s `$REPO_ROOT` references.
5. **Docs**: the new verdict lines in `agents-md/stub.md`; one new `##` section in `agents-md/base.md` with its `eval-coverage.yml` row (#119) and its `docs/guidance-impact.md` entry (#120); a README section; `AGENTS.md` regenerated.

### Measurements, pasted as asked (also in the hook's header comment)

Taken on the CLI this container ships — **2.1.261** — against a **local stub API endpoint** (`ANTHROPIC_BASE_URL` → `127.0.0.1` serving one canned SSE message), never a real credential, with `CLAUDE_CONFIG_DIR` and `HOME` both pointed at throwaway directories.

**The event.** `claude -p` (exit 0, the stub's reply returned) fired exactly two events, one per memory file: a `User` load of `<cfg>/CLAUDE.md` and a `Project` load of `<proj>/CLAUDE.md`, both `load_reason: session_start`, each with `cwd`, `file_path`, `hook_event_name`, `session_id`, `transcript_path`. `globs`, `trigger_file_path` and `parent_file_path` are **absent** on a `session_start` load; the CLI's own schema marks all three optional and they carry only for the glob-match, include and nested-traversal reasons.

**A `compact` reload could not be reproduced**, and that is a measurement rather than an omission. The CLI sets that reason during post-compaction cleanup and consumes it on the *next* eager memory load; a `claude -p` process exits with the turn and never reaches one — measured directly: `/compact` in print mode (after eight accumulated turns, so it really did compact) fired no event beyond the two `session_start` ones, and a forced 12-turn tool loop reporting a near-full context did not trigger auto-compaction either. Interactive `claude` in this container cannot start without an OAuth login, which I did not attempt. The hook does not depend on it: `load_reason` is recorded verbatim and never branched on.

**Where the hook's stdout lands: nowhere.** A canary printed by the hook appeared in neither the CLI's stdout, its stderr, the transcript, nor any file under the config dir or HOME — on a failed run and on a successful one alike. The CLI's own hook description agrees: *"Exit code 0 — command completes successfully; other exit codes — show stderr to user only. This hook is observability-only."* Since this hook must always exit 0, it has **no channel to the session at all**. That is what forced the state-file design the issue anticipated: the verdict goes to `instructions-receipt.state` and the next session's SessionStart hook prints it, so a mismatch is silent for one session and no longer.

## Verifier output

`./test/run-tests.sh`, with mikefarah `yq` v4.53.3 first on PATH (`/usr/bin/yq` in this container is a different tool and reddens 31 assertions on `origin/main` before any change of mine) and `npm ci` done: before, on `origin/main`: **1256 passed, 0 failed — exit 0**; after, on this branch (post-merge of `origin/main`): **1359 passed, 0 failed — exit 0**.

Every behaviour was written red first, and each fix has a **named mutation** that turns its block red again — run, not asserted:

- receipt hook: rotation removed (2 red), paths left absolute (1), skip stops removing (1), truncation detection removed outright (1), structural check removed outright (7), stale-version check removed (4)
- `fleet-memory.sh`: install stops writing state (1), a no-op run stops recording current (1), previous-session line removed (4), skip stops removing the receipt lane (1), a healthy agents-md announced every session (1)
- report: rotated predecessor ignored (2), an empty log exits 0 (1), the default stops narrowing to the latest session (1), paths left absolute (2), unparseable lines silently dropped (2)
- registration: the classifier ignoring the event again (2), sync neither delivering nor registering (2)
- the three self-review fixes: a healthy verdict overwriting this session's mismatch (1), an unset HOME as a shell error (2), a value-less flag spinning (2), the same-session guard removed (1)

Two earlier mutations came back green and are recorded rather than hidden: disabling only the BEGIN-count check still trips the END-count check, and removing only the no-END branch still trips the byte comparison. Both were re-run as the sharper mutations above.

Other CI gates run locally: `check-agents-md.sh` ok, "Self-guidance is current" diff clean, `bridge-status.sh` = `bridge-ok`, `check-guidance-coverage.js --check-bytes` exit 0, `check-guidance-touch.js` against a synthetic PR event → *"1 section(s) touched, all have a sufficient entry"*, `check-cron-coverage.js` and `check-registry.js` exit 0.

## What I could not do

- **The `compact` load reason** — see above. Not reproducible non-interactively on 2.1.261; the code path and the failed attempts are documented rather than guessed at.
- **Two departures from the issue's wording**, both because the literal version would state something untrue:
  - The issue asks for the paragraph in *"`base.md`'s 'Fleet guidance is delivered once per session' section"*. That section lives in **`agents-md/stub.md`**, not `base.md` — `base.md` has no such heading. Both surfaces are updated: the verdict lines went to the stub (item 4's ask), and the pointer paragraph became one new `##` section in `base.md`, which is what makes #119's row and #120's entry applicable at all.
  - `agents-md: BEHIND (v<x> < v<y>)` claims an ordering between two content ids that nothing can establish — a digest is not a version number. The verdict keeps the name and says which is which: `BEHIND — this repo ships v<x>, the session loaded v<y>`. A test forbids the ` < v` form specifically.
- **`agents-md: EDITED ABOVE THE MARKER` detects structure, not prose.** A hand edit *inside* a well-formed managed block needs the template the block was generated from, and a consumer repo does not carry one. What it does catch is the shape that has actually happened here: the doubled managed block of `c86465f`, plus a missing END and markers out of order. The hook's own comment says this rather than implying more.
- **The post-merge sync run** is the issue's last verifier line and is not mine to read — the orchestrator holds the merge. Expect a one-line settings change plus the new hook file in each synced repo, or a no-op.
