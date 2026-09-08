
## Registration and sync, measured

### The `BOOTSTRAP_HOOK_EVENT` seam — the default changes nothing

13 fixture `settings.json` inputs (empty file, `{}`, `{"hooks":{}}`, empty `SessionStart`,
already-registered, a hand-written entry with different quoting/timeout, an unrelated entry,
unparseable text, `hooks` a string, `SessionStart` a string, a top-level array, an
`InstructionsLoaded`-only file, whitespace-only) × 5 invocations each
(`bootstrap-status.sh <file>`, `bootstrap-status.sh -` on stdin, `register-bootstrap-hook.sh`,
a second `register` for idempotence, plus a missing-file case) = **67 measurements**, run with
**no** `BOOTSTRAP_HOOK_*` set, capturing stdout, exit code and the resulting file's md5:

```
diff ref.out head.out  →  IDENTICAL — the BOOTSTRAP_HOOK_EVENT default changes nothing
```

Isolation in both directions is pinned by `test_hook_event_seam` (7 assertions), and both
isolation assertions are red on ref: with the ref registrar the `InstructionsLoaded` entry is
appended into `SessionStart`, so `classifier read 'registered' — the event is not isolating
anything` fails there.

### `.claude/settings.json`

Valid JSON (parsed). Diff against ref is purely additive: one new `"InstructionsLoaded"` key with
`matcher:"*"`, `command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/instructions-loaded.sh"`,
`timeout: 10`. **Both `SessionStart` groups are byte-identical to ref** (`fleet-memory.sh`
timeout 30, `skills-bootstrap.sh` timeout 90), in the same order.

### `sync.sh` against the suite's own fixture repos (`bootorg/*`)

| fixture | dry run says | real run | hook file | instr registration | fleet registration |
|---|---|---|---|---|---|
| `repo-adopted` (has settings, has lock) | `Would add …/instructions-loaded.sh` + `Would append an InstructionsLoaded entry` | delivered + registered | yes, 0755, byte-identical | `registered` | `registered` |
| `repo-no-lock` | same | delivered + registered | yes, 0755, identical | `registered` | `registered` |
| `repo-hook-no-lock` | same | delivered + registered | yes, 0755, identical | `registered` | `registered` |
| `repo-not-allowed` | same | delivered + registered | yes, 0755, identical | `registered` | `registered` |
| `repo-ignored` (`.claude/` gitignored) | **silent** | **withheld** | no | `missing` | `missing` |
| `repo-unparseable` (settings.json not JSON) | **silent** | **withheld**, settings.json not rewritten | no | `unparseable` | `unparseable` |

- **Dry run writes nothing**: after the dry run every repo still reads `hook=missing`.
- **Land together or not at all**: the delivering commit's file list is
  `.claude/hooks/fleet-guidance.md .claude/hooks/fleet-memory.sh
  .claude/hooks/instructions-loaded.sh .claude/hooks/skills-bootstrap.sh
  .claude/settings.json AGENTS.md CLAUDE.md` — the hook and its registration in **one** commit.
- **`add_paths` accounting**: `.claude/settings.json` appears exactly **once** in the commit even
  when bootstrap, fleet-memory and instructions-loaded all register in the same run. The
  `{ $fleet_registered_now || $instr_registered_now; } && ! $bootstrap_registered_now` guard is
  correct.
- **Idempotence / already-has-the-hook**: second run → `instructions-loaded: hook=current
  settings=registered`, `0 synced, 6 skipped, 0 failed`, no new commit. Third (dry) run prints no
  `Would add`/`Would append` for the receipt hook.
- **Self-heals each half independently**: registration deleted → next run commits only
  `.claude/settings.json`; hook file deleted → next run commits only
  `.claude/hooks/instructions-loaded.sh`; hook file hand-edited → `hook=drifted`, dry run says
  `Would overwrite drifted …`, real run restores it byte-identical.
- **A repo with a `FLEET_GUIDANCE_SKIP`-style opt-out**: there is no per-repo opt-out flag; the
  two refusals are `.claude/` gitignored and an unparseable `settings.json`, and both withhold the
  receipt hook exactly as they withhold `fleet-memory.sh`. `FLEET_GUIDANCE_SKIP` is a runtime
  (machine) opt-out, tested separately and honoured by both hooks.
- **The one shape that does not hold together**: `settings.json` that is valid JSON but whose
  `hooks.InstructionsLoaded` is **not a list** — see finding S2.
