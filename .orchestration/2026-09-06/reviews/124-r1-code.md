FOUND — 0 blocker, 6 should-fix, 10 nit

_agent-guidance PR #124 (issue #123), round 1, head `521562842057b4d5244b370853635399819afdf7`.
Effort level `xhigh` (`CLAUDE_CODE_EFFORT_LEVEL=xhigh`).

Tree verified before any work: `find . -type f -print0 | sort -z | xargs -0 md5sum | md5sum` over
`$SP/rev124a-code` = `4a4a2080f8028d57db3ea180425bd273`, matching the brief. 16 files changed,
`+1722/-15` — I recomputed both and they match the brief's figures exactly.

**Summary.** The lane is sound. The hook is observe-only in fact, not just in intent: 22 hostile
event shapes all exit 0, nothing is written outside `$CLAUDE_CONFIG_DIR` (measured with a fresh
HOME, cwd and TMPDIR), no absolute path reaches any log line or verdict, `FLEET_GUIDANCE_SKIP`
removes what earlier sessions wrote, and every verdict path reproduces correctly against real
`fleet-memory.sh` installs. `test_fleet_memory_hook` is byte-for-byte unchanged, the counts match
the PR body, the registration seam is provably backward-compatible over 67 measurements, and the
workflow change is four lines with nothing else touched. The measurement the design rests on is
not only internally consistent with the code — I corroborated all four of its structural claims by
reading the shipped CLI bundle as data, including one thing the worker did not claim and that the
whole registration depends on.

The findings are: four coverage gaps that a mutation exposed (two of them with a demonstrated
operational consequence), one shape where the sync delivers a hook it cannot register, one place
where the hook breaks its own stated stdin invariant and already makes an assertion in this suite
flaky, and a doc sentence that is now false in a way an agent would act on.
## Verifiers

`export PATH=$SP/bin:$PATH` (mikefarah yq v4.53.3 first; `/usr/bin/yq` is a different tool),
`node_modules` copied from an existing checkout with a byte-identical `package-lock.json`
(no network, no `npm ci`).

| run | tree | environment | result | exit |
|---|---|---|---|---|
| 1 | `rev124a-code` (head `5215628`) | `env -u SP PATH=$SP/bin:$PATH` | **1359 passed, 0 failed** | 0 |
| 2 | `rev124a-ref` (`main` `3d972b4`) | same | **1256 passed, 0 failed** | 0 |
| 3 | `rev124a-code` | `env -i PATH=$SP/bin:/usr/bin:/bin:/usr/local/bin HOME=<scratch>` | **1359 passed, 0 failed** | 0 |

Both match the PR body exactly (it claims 1256 before, 1359 after). Head is green under a
constructed minimal environment too, so nothing in the new lane depends on ambient state.

**Assertion-set diff, not just counts.** Comparing the sorted PASS lines of run 1 against run 2:
105 lines present only at head, 2 present only at ref — and those 2 are the same two `big marker`
assertions with different numbers in their text (`74050-byte file` → `74816-byte file`), a benign
consequence of the guidance payload growing by the new section. **103 genuinely new assertions,
none removed** — exactly the 1359−1256 delta:

| area | new assertions |
|---|---|
| `instructions-loaded:` | 52 |
| `fleet-memory state:` | 21 |
| `instructions-report:` | 16 |
| `event seam:` | 7 |
| `self-hosted receipt:` | 3 |
| `repo-no-lock:` | 2 |
| `repo-ignored:` | 1 |
| `sync trigger: on.push.paths covers .claude/hooks/instructions-loaded.sh` | 1 |

**`test_fleet_memory_hook` is byte-for-byte unchanged.** Extracted from both trees
(233 lines each), `md5 = 92a1d08023562e441bf5ee4cdc005ef4` on both, `diff` empty. The PR body's
claim holds.

**Hollowness.** Head's `test/run-tests.sh` dropped onto the ref tree: the suite aborts under
`set -e` partway through `test_instructions_loaded_hook` (a `wc -l <` on a log the missing hook
never wrote), having already logged 29 FAILs. Re-run through a driver that sources the same
prelude with `set +e` and calls only the five new test functions:

| tree | result |
|---|---|
| head | 99 passed, 0 failed |
| ref + head's tests | **18 passed, 59 failed** |

The 18 that pass on ref are all vacuous-by-construction negatives against a file that does not
exist there (`assert_not_contains "$INSTR_HOOK" '"decision"'`, "nothing outside the config dir was
written", "no interpreter traceback", "an unset HOME is not a shell error", "earlier sessions are
not in the default report"). Every positive assertion in the five blocks is red on the base.

## The issue, item by item

`P` = present, `p` = partial, `–` = absent.

"Red on ref" is from the hollowness run above. `vacuous†` means the assertion **passes** on the
base tree for a reason that has nothing to do with the behaviour — it is a negative assertion
against a file that does not exist there — but the behaviour itself is head-only, which I
established with a direct ref-vs-head probe of the same input. Where the hollow run aborted
before reaching an assertion, † likewise marks a direct probe. Mutation names are from the
table two sections down.

### "Do"

| # | Item | State | Test that pins it | Red on ref | Mutation I ran that reddens it at head |
|---|---|---|---|---|---|
| 1 | hook is bash, no network, exits 0 always | P | `every hostile event exits 0`, `no HOME and no config dir still exits 0` | vacuous† | `W20` unset-HOME → 2 red |
| 1 | `set -euo pipefail` | p | — | — | departs to `set -uo pipefail`, documented in the file (`read -d ''` returns 1 at EOF; an always-exit-0 hook must not inherit `-e`). Justified. |
| 1 | honours `FLEET_GUIDANCE_SKIP` (no output, no write) | P | `skip prints nothing at all`, `skip removes the log and the receipt it had written`, 4× `SKIP=<off-spelling> does NOT skip` | vacuous† | **not measured** (`W3` killed at the limit); direct probe instead: skip removes log/`.1`/receipt, writes nothing anywhere, exits 0 — hostile table |
| 1a | `User` + block: compare version and byte length against the state file | P | `a matching block reports loaded, with version and bytes` | yes | **not measured** (`W4`, `W6` killed at the limit); `M10` (state records the wrong byte count) → 3 red exercises the same comparison end to end, and every verdict was reproduced directly |
| 1a | `loaded (v<id>, <n> bytes)` / `LOAD MISMATCH — truncated / stale version / block absent` | P | 3 named blocks + `content differs` (an addition) | yes | `M9` (sha check removed) → **GREEN, see S6**; `W4`/`W6` **not measured**; all four verdicts reproduced directly |
| 1a | state file under `$CLAUDE_CONFIG_DIR` written by the SessionStart hook | P | `an install writes the state file` + 4 field assertions + an end-to-end assertion that both hooks agree about the same bytes | yes | `M10` (state records the wrong byte count) → **3 red**; `W7`/`W8` **not measured** (killed at the limit) |
| 1a | "the only change to that hook" | p | — | — | two changes: `write_state` **and** `report_previous_session`. The issue's own last sentence in item 1 authorises the second. |
| 1a | its existing tests stay unchanged and are extended | P | — | — | verified byte-for-byte above |
| 1b | `Project` + managed header: compare version | P | `a repo shipping the guidance in context reads current`, `… reads BEHIND` | yes | `W5` **not measured** (killed at the limit); both verdicts reproduced directly |
| 1b | hash the managed region against "the synced template recorded in the state file" | – | — | — | **not implemented**, disclosed. Justified: nothing records such a template — `fleet-memory.sh` records the digest of the *payload*, and a repo's managed region is generated per-repo by `build-agents-md.sh` from its own `sections:`. The issue asked for a comparand that does not exist. Structural checks stand in. |
| 1b | `agents-md: current` / `BEHIND` / `EDITED ABOVE THE MARKER` | P | 5 assertions incl. `BEHIND claims no ordering it cannot establish` | yes | `W5` **not measured**; three of the four shapes are red on ref in the hollow run |
| 1c | every event appends `{ts, load_reason, memory_type, path, bytes, sha256}` | P | `carries every key the report and skills-evals#139 read` | yes | `M1` key renamed → 2 red |
| 1c | path relative to `$HOME` or the cwd, never absolute | P | `the log line is relative, and its bytes and sha256 are the file's` | yes | `M2` wrong sha input → **1 red**; `W2` (paths left absolute) **not measured**; no absolute path appeared in any of the 22 hostile-event log lines |
| 1c | rotated at 1 MB | P | `the log rotates once it passes the bound`, `the live log restarts small` | yes | `W1` rotation removed → 2 red |
| 1c | measure where stdout lands first | P | — | — | pasted; **independently corroborated** below |
| 2 | `scripts/instructions-report.sh` sums per session | P | 16 assertions | yes | `W12`/`W13`/`W14`/`W15`/`W16`/`W21` |
| 2 | one paragraph in `base.md`'s "Fleet guidance is delivered once per session" section | p | `check-guidance-coverage --check-bytes`, `check-guidance-touch` | — | **departs**: that heading is in `agents-md/stub.md`; `base.md` has no `##` matching it (verified). One new `##` section in `base.md` (21→22) + the verdict lines in the stub. Justified and disclosed. |
| 2 | `eval-coverage.yml` row and `guidance-impact.md` entry, `none — no fixture yet` only if the row is `gap` | P | both gates | — | row is `status: gap`, entry is `- Eval: none — no fixture yet`. Consistent with the issue's condition. Removing the row reddens the coverage gate (negative control run). |
| 3 | registered beside the SessionStart hook, matcher = all load reasons | P | `self-hosted receipt: registered for every load reason` | yes | `M3` matcher `*`→`session_start` → 1 red |
| 3 | delivered by the same sync path as `fleet-memory.sh` | P | `the InstructionsLoaded hook rides with fleet-memory`, `… is registered, not just delivered`, `repo-ignored: withheld too` | yes | `W18` sync delivers/registers nothing → 2 red; `M4` wrong event → 2 red; `M5` omitted from `add_paths` → 1 red |
| 3 | `sync.yml` untouched unless the file list is enumerated there → then one line | P | `sync trigger: on.push.paths covers …` | yes | `M11` **not measured**; the assertion is red on ref and the path is derived from `sync.sh`, so it cannot be decorative |
| 4 | new verdict lines in the floor paragraph | P | — | — | in `stub.md` + regenerated `AGENTS.md`; see finding S3 |
| 4 | README pointer | P | — | — | `## The load-time receipt` + a bullet in the layout list |

### "Tests (red first)"

| Bullet | State | Red on ref |
|---|---|---|
| current block → `loaded` | P | yes |
| version behind the state → `LOAD MISMATCH` | P | yes (4 assertions) |
| the 154-byte truncated block → `LOAD MISMATCH` | P | yes |
| block absent → `LOAD MISMATCH` | P | yes |
| AGENTS.md header behind → `BEHIND` | P | yes |
| managed region edited → `EDITED ABOVE THE MARKER` | P | yes (doubled block + markers out of order) |
| a project file without the header → log line only | P | yes (the log-line half) |
| log line appended with a relative path and the right byte count | P | yes |
| rotation at the bound | P | yes |
| `FLEET_GUIDANCE_SKIP` → no output, no write | P | vacuous on ref† |
| hostile: no `file_path`, newline path, 10 MB stdin, non-existent file, directory → exit 0, no traceback, nothing outside `$CLAUDE_CONFIG_DIR` | P | vacuous on ref† — see nits N1/N2, the assertions are weaker than they read |
| SessionStart hook's existing tests unchanged and green | P | n/a |
| + the state-file write and the "previous session" line | P | yes / † |
| `--` before every grep needle | P | all four new `grep` calls use `--` |

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

## Gates

| Gate | How I ran it | Result |
|---|---|---|
| `check-guidance-coverage.js --check-bytes` (#119) | in the head tree | `28 gap · 1 skipped · 0 covered`, **exit 0** |
| … negative control | same, with the new manifest row deleted | **exit 1**: `heading ""fleet-guidance: current" is not "the guidance is in context"" … has no row` — the gate is real, and the row's `bytes: 1053` is what `--check-bytes` accepts |
| `check-guidance-touch.js` (#120) | a throwaway two-commit git repo built **under `$SP/r1w124/`** (ref tree = base commit, head tree = head commit) with a synthetic `$GITHUB_EVENT_PATH` | `1 section(s) touched, all have a sufficient docs/guidance-impact.md entry`, **exit 0** — verbatim the PR body's claim |
| `check-agents-md.sh` | head tree | exit 0 |
| "Self-guidance is current" | `printf '%s\n%s\n' "$(./scripts/build-agents-md.sh)" "$(sed -n '/^## Repo-specific additions/,$p' AGENTS.md)"` then `diff` | **clean** |
| `bridge-status.sh CLAUDE.md` | head tree | `bridge-ok` |
| `check-registry.js` | head tree | exit 0 |
| `check-cron-coverage.js` | head tree (a `git archive`, not a repo) → exit 1 `not a repository`; **re-run inside a real git repo built from the same tree** | **exit 0**, `All audited repos covered`. Identical on ref, so the exit-1 is an artefact of the archive, not the branch. |
| `.claude/settings.json` | `json.load` | valid |
| `bash -n` | all six touched shell files | clean |
| embedded python | `compile()` on both heredocs | clean; the hook's program is **pure ASCII** as its comment claims |

Docs: `agents-md/base.md` gains exactly one `##` section (21 → 22) with the eval-coverage row
(`status: gap`) and the `guidance-impact.md` entry (`- Eval: none — no fixture yet`) — the
combination the issue explicitly permits. `.claude/hooks/fleet-guidance.md` is byte-identical to
`agents-md/base.md` (and ends in a newline, which is what makes the hook's byte arithmetic exact).
`stub.md` and the regenerated `AGENTS.md` carry the same three new verdict bullets. The README
gains `## The load-time receipt` plus a pointer bullet, and its layout listing is updated.

**The two wording departures.** Both are justified and both are tested:

1. *"the paragraph in `base.md`'s 'Fleet guidance is delivered once per session' section"* — that
   heading exists only in `agents-md/stub.md`; `grep '^##' agents-md/base.md` has no match for it
   (verified on the ref tree, so this is not something the branch created). Splitting it — verdict
   lines to the stub, a new `##` section to `base.md` — is what makes #119's row and #120's entry
   applicable at all. Both gates pass.
2. *`agents-md: BEHIND (v<x> < v<y>)`* — two truncated sha256 digests have no ordering, so the
   literal form would assert something false. The replacement names which is which, and
   `assert_not_contains "$d/out_agents_behind" " < v"` forbids the original form specifically. That mutation (`W5`) is **not measured** — killed at the
   limit — but the assertion exists and the `BEHIND` wording was reproduced directly.

## The workflow line, line by line

`git diff` of `.github/workflows/sync.yml`: **4 lines added, 0 removed, 0 modified.**

| Check | Result |
|---|---|
| exactly one `paths:` entry plus its comment | yes — 3 comment lines + `      - ".claude/hooks/instructions-loaded.sh"`, inserted after the `fleet-memory.sh` entry |
| any `uses:` changed | no — all four `uses:` lines (`actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5`, two × `actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1`) are byte-identical to ref; every one is a bare 40-hex SHA with no trailing version comment |
| any `${{ }}` inside a `run:` | none added. The one that exists — `if [[ "${{ inputs.dry_run }}" == "true" ]]` — is at ref line 146 and head line 150, i.e. pre-existing and untouched, and it interpolates a `workflow_dispatch` boolean, not a PR-controlled field |
| `pull_request` trigger added | no — triggers are `push` + `workflow_dispatch` on **both** trees; the only occurrence of the string `pull_request` in the file is inside a comment about token scopes |
| permissions | `permissions: contents: read` — identical on both trees |
| file still parses | `yq -e '.'` OK |
| the entry is *demanded*, not decorative | `test_sync_workflow_trigger` derives the watched set from `sync.sh`'s `$REPO_ROOT/…` references; the new `INSTR_HOOK_SOURCE="$REPO_ROOT/.claude/hooks/instructions-loaded.sh"` puts the path in the derived set, and the new assertion `sync trigger: on.push.paths covers .claude/hooks/instructions-loaded.sh` is one of the 103 |

## Mutations

Each mutation was applied to a **fresh copy of the head tree under `$SP/r1w124/mut/`** and run
through the **full suite** (`./test/run-tests.sh`, pinned yq first on PATH). `$SP/rev124a-code`
itself was never touched. 36 were prepared and validated as applying cleanly; **24 completed
before the stop** — 14 of the worker's 22 and 10 of my own 14. The 12 that were killed mid-run are
listed as *not measured* below and are never used as evidence anywhere in this report.

"Claimed" is the red-assertion count the PR body states for its own version of the mutation. My
edit is not textually identical to the worker's, so a difference in count is not by itself a
discrepancy — a **GREEN** row is.

### Measured (24)

| Mutation | Claimed | Red | Verdict |
|---|---|---|---|
| `M1_log_key_renamed` | — | 2 | 2 red |
| `M2_log_sha_wrong_input` | — | 1 | 1 red |
| `M3_settings_matcher_narrowed` | — | 1 | 1 red |
| `M4_sync_registers_wrong_event` | — | 2 | 2 red |
| `M5_sync_omits_add_path` | — | 1 | 1 red |
| `M6_sync_uptodate_ignores_instr` | — | 0 | **GREEN — not caught** |
| `M7_stdin_cap_removed` | — | 0 | **GREEN — not caught** |
| `M8_file_path_guard_removed` | — | 0 | **GREEN — not caught** |
| `M9_sha_equal_length_check_removed` | — | 0 | **GREEN — not caught** |
| `M10_fm_state_bytes_wrong` | — | 3 | 3 red |
| `W1_rotation_removed` | 2 | 2 | 2 red |
| `W10_fm_skip_keeps_receipt` | 1 | 1 | 1 red |
| `W11_fm_healthy_agents_announced` | 1 | 2 | 2 red |
| `W12_report_ignores_rotated` | 2 | 2 | 2 red |
| `W13_report_empty_exits0` | 1 | 1 | 1 red |
| `W14_report_no_narrowing` | 1 | 1 | 1 red |
| `W15_report_abs_paths` | 2 | 2 | 2 red |
| `W16_report_drops_unparseable` | 2 | 2 | 2 red |
| `W17_classifier_ignores_event` | 2 | 4 | 4 red |
| `W18_sync_no_deliver` | 2 | 2 | 2 red |
| `W19_healthy_overwrites` | 1 | 1 | 1 red |
| `W20_unset_home_error` | 2 | 2 | 2 red |
| `W21_report_flag_spins` | 2 | 2 | 2 red |
| `W22_same_session_guard_removed` | 1 | 1 | 1 red |

Every one of the worker's 14 that I re-ran reddens the suite, and the counts agree with the PR
body's own numbers on 12 of 14. The two that differ are both *higher* than claimed
(`W11` 2 vs 1, `W17` 4 vs 2) — my edit was blunter than the worker's, not weaker. No claimed
mutation came back green.

Red assertions, for the ones where the identity matters:

```
M1   instructions-loaded: log line — missing keys: ['file_path']
M2   instructions-loaded: log line — sha256 mismatch
M3   self-hosted receipt: no '*' matcher — some load reasons would fire nothing
M4   repo-no-lock: the delivered hook reads 'no-entry' — a hook nothing runs
     re-run: still exactly 3 SessionStart groups — got 4
M5   repo-no-lock: the InstructionsLoaded hook was not delivered
M10  fleet-memory state: bytes=194, payload is 49
     fleet-memory state: the receipt hook reads a real install as loaded
     fleet-memory state: end to end, the byte count is the payload's own
W10  fleet-memory state: skip left the state, receipt or log behind
W11  fleet-memory state: a current agents-md from last session stays quiet
     instructions-loaded: skip exit 141            ← unrelated to the mutation; this is finding S5
```

### The four green ones — the real output of this exercise

| Mutation | What it deletes | Consequence | Finding |
|---|---|---|---|
| `M6_sync_uptodate_ignores_instr` | the two `instr_*` clauses in `sync.sh`'s `fleet_up_to_date` | a repo whose receipt hook is deleted reads `Up to date — skipping` forever (reproduced) | **S1** |
| `M9_sha_equal_length_check_removed` | the `sha256` comparison in `fleet_verdict` | an equal-length tamper reads as `loaded` | **S6** |
| `M7_stdin_cap_removed` | `if len(raw) > STDIN_CAP: sys.exit(0)` | the 1 MB bound is unenforced; the test named for it passes either way | N1 |
| `M8_file_path_guard_removed` | the `file_path` type/empty guard | the program dies with an `AttributeError`, invisibly | N2 |

### Not measured (12) — prepared, validated as applying cleanly, killed mid-run at the stop

`W2_paths_absolute`, `W3_skip_no_remove`, `W4_truncation_removed`, `W5_structural_removed`,
`W6_stale_version_removed`, `W7_fm_install_no_state`, `W8_fm_current_no_state`,
`W9_fm_no_prev_line` (the worker's), and `M11_syncyml_entry_removed`, `M12_no_log_write`,
`M13_begin_count_only`, `M14_no_end_branch_only` (mine, the last two being the worker's two
recorded *green* mutations, which I therefore could not confirm). Every behaviour those eight
worker mutations would have covered was instead reproduced directly through the hook's own entry
point (truncation, stale version, block absent, content differs, structural checks, the state
file, the previous-session line) — but *whether the suite would catch a regression in them* is
**not measured**, except where the hollowness run already shows the assertion red on `main`.

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

## What I could not check

- **12 of the 36 mutations** — see the mutation section. The programme stopped for the account's
  weekly limit mid-batch; eight of the worker's own listed mutations (`W2`–`W9`) and four of mine
  never finished. Their targets were all exercised directly through the hook instead, but their
  *test-coverage* half is **not measured**.
- **The CLI measurement's empirical half.** I never ran `claude`, per the brief. I audited the
  measurement for internal consistency against the hook's code and corroborated every structural
  claim by reading the shipped bundle as data; what I cannot confirm is that `claude -p` fired
  exactly two events, that a stdout canary appeared nowhere, and that `/compact` in print mode
  produced no third event. The static evidence makes all three plausible.
- **Whether the CLI emits an event for an `@AGENTS.md` import.** The fleet reaches `AGENTS.md`
  through a `CLAUDE.md` bridge, and the `agents-md:` lane only fires on a file carrying the
  managed markers — i.e. on `AGENTS.md`, not on the bridge. `include` is in the reason enum and
  the `*` matcher would catch it, but the worker's measurement used a project with no import, so
  the lane's real-world trigger is unmeasured on both sides.
- **The post-merge sync run** — the issue's last verifier line, held by whoever merges.
- **Behaviour as a non-root user.** This container runs as root, so a read-only
  `$CLAUDE_CONFIG_DIR` is not actually read-only here; I exercised the write-failure paths with a
  directory blocking the target path instead (N4).
- **`shellcheck`** is not installed in this container; `bash -n` only.
- The commit message `sync.sh` picks when *only* the receipt hook needs delivering is one of four
  fixed strings and does not name the artefact; I read the code but did not capture that
  particular message from a run — **not measured**, and pre-existing either way (N3).

## Tree integrity

```
$SP/rev124a-code  before: 4a4a2080f8028d57db3ea180425bd273   (brief's expected value — matched)
$SP/rev124a-code  after:  4a4a2080f8028d57db3ea180425bd273
$SP/rev124a-ref   after:  5614be2474b350d6290a28bca8b07cec
```

**Unchanged.** Every mutation, suite run and fixture ran in a copy under `$SP/r1w124/`;
`$SP/rev124a-code` and `$SP/rev124a-ref` were only ever read. The throwaway two-commit git repo
built for the #120 touch gate lives at `$SP/r1w124/touchgate`; nothing was run against
`/home/user/_agent-guidance` beyond `git cat-file -t` and `git log`. No network, no `claude`
binary executed (the bundle was read as bytes, never run), no credential touched, nothing posted
to GitHub. All background processes I started have been killed and verified gone.
