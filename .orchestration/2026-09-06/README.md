# Orchestration state snapshot, 2026-09-06 00:55 UTC

Durable copy of the evals orchestrator's container-only working state, taken when Adam ordered a 1.5-day pause (the account's weekly limit at 93%; resets 2026-09-07 17:00 UTC). The status board is skills-evals issue #126 (marker `<!-- skills-evals:orchestration -->`); this directory is the memory beside it. Not for merge; read-only reference for the orchestrator session https://claude.ai/code/session_01RhaAJ7F6AukVV5Z8S4QLbx.

- `state-log.md` — the append-only chronological log (container clock, UTC).
- `reviews/` — every review subagent report (`<PR>-r<N>[-code|-adv].md`); the `124-r1-code.part*.md` files are the partial report of the _agent-guidance#124 code half, still running at the snapshot.
- `briefs/` — every fix-round and dispatch brief sent to a worker session.
- `ctx/` — worker reports and issue context handed to reviewers.
- `prompts/` — earlier worker prompts.
- `board-0040.md`, `board-2335.md` — the last two board bodies.
- `cmpfix.py`, `verify*.sh` — the fresh-worktree verification scripts.

Credential-shaped test strings inside reviewer reports were replaced with `REDACTED-SHAPE` markers before this copy was made; none was a real credential.
