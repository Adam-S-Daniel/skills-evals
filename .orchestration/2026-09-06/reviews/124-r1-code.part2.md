
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
| 1 | honours `FLEET_GUIDANCE_SKIP` (no output, no write) | P | `skip prints nothing at all`, `skip removes the log and the receipt it had written`, 4× `SKIP=<off-spelling> does NOT skip` | vacuous† | `W3` skip stops removing → 1 red |
| 1a | `User` + block: compare version and byte length against the state file | P | `a matching block reports loaded, with version and bytes` | yes | `W6` stale check removed → **4 red**; `W4` truncation removed → 1 red |
| 1a | `loaded (v<id>, <n> bytes)` / `LOAD MISMATCH — truncated / stale version / block absent` | P | 3 named blocks + `content differs` (an addition) | yes | `W4`, `W6`, `M9` |
| 1a | state file under `$CLAUDE_CONFIG_DIR` written by the SessionStart hook | P | `an install writes the state file` + 4 field assertions + an end-to-end assertion that both hooks agree about the same bytes | yes | `W7` install stops writing → 1 red; `W8` no-op stops recording → 1 red; `M10` state records the wrong byte count → 3 red |
| 1a | "the only change to that hook" | p | — | — | two changes: `write_state` **and** `report_previous_session`. The issue's own last sentence in item 1 authorises the second. |
| 1a | its existing tests stay unchanged and are extended | P | — | — | verified byte-for-byte above |
| 1b | `Project` + managed header: compare version | P | `a repo shipping the guidance in context reads current`, `… reads BEHIND` | yes | `W5` structural check removed → **7 red** |
| 1b | hash the managed region against "the synced template recorded in the state file" | – | — | — | **not implemented**, disclosed. Justified: nothing records such a template — `fleet-memory.sh` records the digest of the *payload*, and a repo's managed region is generated per-repo by `build-agents-md.sh` from its own `sections:`. The issue asked for a comparand that does not exist. Structural checks stand in. |
| 1b | `agents-md: current` / `BEHIND` / `EDITED ABOVE THE MARKER` | P | 5 assertions incl. `BEHIND claims no ordering it cannot establish` | yes | `W5` |
| 1c | every event appends `{ts, load_reason, memory_type, path, bytes, sha256}` | P | `carries every key the report and skills-evals#139 read` | yes | `M1` key renamed → 2 red |
| 1c | path relative to `$HOME` or the cwd, never absolute | P | `the log line is relative, and its bytes and sha256 are the file's` | yes | `W2` paths left absolute → 1 red; `M2` wrong sha input → 1 red |
| 1c | rotated at 1 MB | P | `the log rotates once it passes the bound`, `the live log restarts small` | yes | `W1` rotation removed → 2 red |
| 1c | measure where stdout lands first | P | — | — | pasted; **independently corroborated** below |
| 2 | `scripts/instructions-report.sh` sums per session | P | 16 assertions | yes | `W12`/`W13`/`W14`/`W15`/`W16`/`W21` |
| 2 | one paragraph in `base.md`'s "Fleet guidance is delivered once per session" section | p | `check-guidance-coverage --check-bytes`, `check-guidance-touch` | — | **departs**: that heading is in `agents-md/stub.md`; `base.md` has no `##` matching it (verified). One new `##` section in `base.md` (21→22) + the verdict lines in the stub. Justified and disclosed. |
| 2 | `eval-coverage.yml` row and `guidance-impact.md` entry, `none — no fixture yet` only if the row is `gap` | P | both gates | — | row is `status: gap`, entry is `- Eval: none — no fixture yet`. Consistent with the issue's condition. Removing the row reddens the coverage gate (negative control run). |
| 3 | registered beside the SessionStart hook, matcher = all load reasons | P | `self-hosted receipt: registered for every load reason` | yes | `M3` matcher `*`→`session_start` → 1 red |
| 3 | delivered by the same sync path as `fleet-memory.sh` | P | `the InstructionsLoaded hook rides with fleet-memory`, `… is registered, not just delivered`, `repo-ignored: withheld too` | yes | `W18` sync delivers/registers nothing → 2 red; `M4` wrong event → 2 red; `M5` omitted from `add_paths` → 1 red |
| 3 | `sync.yml` untouched unless the file list is enumerated there → then one line | P | `sync trigger: on.push.paths covers …` | yes | `M11` |
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
