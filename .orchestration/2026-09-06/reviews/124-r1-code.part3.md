
## Hostile inputs, through the production entry point

Every row: the event JSON on **stdin** to `bash .claude/hooks/instructions-loaded.sh` with
`CLAUDE_CONFIG_DIR` a temp dir under `$SP/r1w124/`, `HOME` a fresh empty temp dir,
`TMPDIR` a fresh empty temp dir, cwd a fresh temp dir, and a real installed block + state file
in the config dir so the verdict paths are live.

| Event | exit | stdout | traceback | log line |
|---|---|---|---|---|
| no `file_path` key | 0 | (silent) | none | none |
| `"file_path": null` | 0 | (silent) | none | none |
| empty stdin | 0 | (silent) | none | none |
| `not json at all` | 0 | (silent) | none | none |
| `[1,2,3]` (JSON, not an object) | 0 | (silent) | none | none |
| `42` (JSON scalar) | 0 | (silent) | none | none |
| non-existent file | 0 | (silent) | none | yes — `bytes:0, sha256:""`, path `.../cfg/nope.md` |
| a **directory** as `file_path` | 0 | (silent) | none | yes — `bytes:0, sha256:""` |
| path containing a **newline** | 0 | (silent) | none | yes — one physical line, `\n` escaped by `json.dumps` |
| file **outside** the config dir **and** outside the cwd | 0 | (silent) | none | yes — `.../sub/note.md`, never absolute |
| a **symlink** into the config dir | 0 | `fleet-guidance: loaded (…)` | none | yes — resolved content hashed, path `link-to-user.md` |
| relative `file_path` (`CLAUDE.md`) | 0 | (silent) | none | yes — `CLAUDE.md` |
| `../` traversal in `file_path` | 0 | (silent) | none | yes — normalised, still relative |
| fields **reordered** + extra keys + `globs`/`trigger_file_path`/`parent_file_path` present | 0 | `fleet-guidance: loaded (…)` | none | yes |
| `memory_type: 123`, `load_reason: ["a"]`, `session_id: {…}`, `cwd: 7` (wrong types) | 0 | (silent) | none | yes — coerced to `""` |
| **non-UTF-8 bytes** in the event | 0 | (silent) | none | none (decode fails → exit 0) |
| **non-UTF-8** inside `file_path` | 0 | (silent) | none | none |
| **10 MB** of `x` on stdin | 0 | (silent) | none | none (`STDIN_CAP`) |
| 10 MB **valid** JSON event | 0 | (silent) | none | none (`STDIN_CAP`) |
| `FLEET_GUIDANCE_SKIP` ∈ {1,true,yes,on,TRUE,anything} | 0 | (silent) | none | none, and the existing log/`.1`/receipt are **removed** |
| `FLEET_GUIDANCE_SKIP` ∈ {"",0,false,FALSE,no,NO,off,OFF} | 0 | as normal | none | yes — the OFF spellings really are OFF |
| no `HOME`, no `CLAUDE_CONFIG_DIR` | 0 | (silent) | none | none, and no `unbound variable` |

**"Nothing written outside `$CLAUDE_CONFIG_DIR`", measured rather than asserted.** Fresh `HOME`,
fresh cwd, fresh `TMPDIR`, plus an "outside" tree; full `find` listing of all four before and
after the whole battery:

```
diff before after  →  IDENTICAL: nothing written under HOME, cwd, outside, or TMPDIR
$CLAUDE_CONFIG_DIR gained exactly: instructions-log.jsonl, instructions-receipt.state
```

**Verdict paths, each reproduced directly** (temp config dir, real `fleet-memory.sh` install):

```
CLI reads memory from a dir we never wrote  → LOAD MISMATCH — block absent from the file the session loaded
state version moved on                      → LOAD MISMATCH — stale version (loaded v…, installed v…)
block cut to 154 bytes                      → LOAD MISMATCH — truncated (37 of 233 bytes, no END marker)
same length, one byte changed               → LOAD MISMATCH — content differs (same length, different bytes)
extra line inside the block                 → LOAD MISMATCH — content differs (24 bytes, installed 13)
untouched                                   → loaded (v3f7e4d19, 233 bytes)
```

**Rotation boundary.** Live log at 1 048 575 bytes → no rotation. At 1 048 576 (2^20) → rotates,
`…jsonl.1` = 1 048 576, live log = 235. A third event leaves exactly two log files. Bounded.

**Same-session guard.** Sequential `BEHIND` then `current` in one session keeps `agents=BEHIND`;
the same pair under a new `session_id` replaces it with `agents=current`. 30 rounds of the two
fired concurrently lost the `BEHIND` verdict 0/30 times (and 20 rounds of the cross-key
`fleet`/`agents` pair, 0/20) — see nit N8 for the theoretical window.

**On the repo's own real files** (`fleet-memory.sh` installing the real 57 007-byte payload):

```
fleet-guidance: loaded (v0f9ded5b, 57007 bytes)
agents-md: current (v0f9ded5b)                      ← the repo's own AGENTS.md, no false positive
(the @AGENTS.md bridge CLAUDE.md)                   ← logged, correctly not judged
instructions-report: 1 session(s), 3 files, 65075 bytes
  bytes by memory type   Project 7923 | User 57152
```

That last block is the measurement the issue asked for, working end to end.
