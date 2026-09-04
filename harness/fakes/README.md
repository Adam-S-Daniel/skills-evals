# harness/fakes

Fake binaries shared across fixtures. A Class B eval (DESIGN.md, "Four
instruments") decides correctness by whether the agent reached a recorded root
cause, so its instrument is a stand-in for the tool the skill consults —
answering from canned payloads, refusing to mutate anything, and logging what
was asked. Same substitution move as `$CLAUDE_BIN` / `test/fake-claude`.

One fake lives here per faked tool. A fixture supplies **payloads**, never
code: it symlinks the binary onto its seed's `bin/` and ships its own payload
directory, so a behaviour fixed here is fixed for every fixture at once.

| Fake | Stands in for | Payload dir |
|---|---|---|
| [`gh`](gh) | the GitHub CLI | `$FAKE_GH_PAYLOADS` |

(`evals/windows-elevation-from-wsl/seed/bin/powershell.exe` predates this
directory and stays with its fixture — it is machine-specific and no second
fixture reuses it.)

## `gh`

### Wiring a fixture to it

```yaml
# evals/<skill>/fixture.yaml
env:
  PATH: "$WORKSPACE/bin:$PATH"          # the fake shadows any real gh
  FAKE_GH_PAYLOADS: "$WORKSPACE/.fake-gh/payloads"   # a dot-dir: see below
  FAKE_GH_REPO: "example-org/example-site"   # only shapes the 403's URL
```

```bash
# evals/<skill>/seed/bin/gh -> ../../../../harness/fakes/gh
ln -s ../../../../harness/fakes/gh evals/<skill>/seed/bin/gh
```

`$WORKSPACE` expands to the arm's temp workspace at run time (see
`harness/run_eval.py`'s `agent_env`), and `shutil.copytree` resolves the
symlink into a real executable there, so the arm gets a self-contained copy
and the repo keeps one source of truth.

**Keep the payloads in a dot-directory.** A payload tree beside the seed's own
files is part of the workspace the agent reads: it can `cat` the recorded run
log straight off disk, reach the root cause without asking `gh`, and then fail
the very check that was meant to tell those two apart. A `.fake-gh/` sibling
keeps them out of plain view, and the seed's README says nothing about them.

### The keying rule

The payload a call gets is decided by the **normalized argv**: positional
tokens only, flags dropped. That is what makes flag ORDER irrelevant —
`pr list --repo X --state open` and `pr list --state open --repo X` read the
same file.

| Invocation | Payload file |
|---|---|
| `gh pr list --repo X --state open --json …` | `pr-list.json` |
| `gh pr view 418 --json … --jq …` | `pr-view-418.json` |
| `gh run view 4471182930 --log` | `run-view-4471182930.log` |
| `gh run view 4471182930` | `run-view-4471182930.json` |
| `gh api repos/X/pulls/418` | `api/repos/X/pulls/418.json` |
| `gh api /repos/X/pulls/418?per_page=1` | `api/repos/X/pulls/418.json` |
| `gh auth status` | `auth-status.json`, falling back to `auth-status.txt` |

- `api <endpoint>` keys to `api/<endpoint>.json`; a leading `/` and any
  `?query` are stripped. A key that would escape the payload directory
  resolves to nothing (a 404), never to a file outside it.
- Everything else joins its positionals with `-`, with any `/` inside one of
  them flattened to `-` as well (`repo view owner/name` ->
  `repo-view-owner-name.json`): only `api` endpoints nest.
- `--log` / `--log-failed` are the only flags that reach the key, and only by
  choosing the `.log` extension: a run's log is a different artifact from its
  JSON summary, not a different command.
- A flag that takes a value may be written `--flag value`, `--flag=value`, or
  attached to its shorthand (`-XPOST`, `-fquery=…`, `-Rowner/name`) for the
  shorthands in `ATTACHED_VALUE_FLAGS`. Boolean flags are listed explicitly in
  `BOOLEAN_FLAGS` so `run view --log 12` cannot swallow the run id.
- **A shorthand whose meaning differs per subcommand must be written
  long-form.** `-w` is boolean `--web` on `gh pr view` but `--workflow <name>`
  on `gh run list`; a flat global set gets one of them wrong whichever way it
  is listed, so such shorthands are in neither set and a fixture writes
  `--workflow` / `--web` in full. The same applies to `-i`.
- A `.json` key falls back to a `.txt` payload, so a command whose real output
  is plain text (`gh auth status`, `gh pr diff`) gets a file named for what it
  holds. The key does not change — only which file backs it.
- `gh --version` and `gh --help`, as the WHOLE invocation, are answered by the
  fake itself and need no payload: a 404 there reads as "the tool is broken"
  and can derail a run before it reaches the fixture's own surface.
  `gh pr list --help` is still an ordinary `pr-list.json` read.

### Classes, and what each one does

Every invocation is appended to `$WORKSPACE/.gh-invocations.log` as

```
--- invocation (class=read key=pr-list.json exit=0) --- ["pr", "list", "--repo", "example-org/example-site", "--state", "open"]
```

so a fixture's objective checks can decide what the agent did from the log
alone (`file_matches` over `.gh-invocations.log`).

**Exactly one line per invocation, with the argv JSON-encoded.** An argv
element carrying a newline would otherwise write extra records, and a
`must_match` over the log could be satisfied by a command that never ran;
`json.dumps` turns that newline into a `\n` inside a string, and the resolved
key is escaped the same way. A fixture should still **anchor its log patterns
at `^`** (`"^--- invocation \\(class=write"`), so text sitting inside an argv
cannot pose as a record either way.

The record is written **before** any output, and any failure writing it is
swallowed: an argv that will not decode, a closed pipe or a full disk must not
cost the log its evidence. A fixture that asserts "the agent attempted no
write" should therefore also assert that the log EXISTS (`must_match:
"^--- invocation "`) — a `must_not_match` over a missing file passes, so
without it the check can pass on zero evidence.

The log goes to `$WORKSPACE/.gh-invocations.log`. With `WORKSPACE` unset it
falls back to the workspace the payload directory sits in — never the cwd,
which the agent chooses.

| Class | When | Result |
|---|---|---|
| `read` | a non-mutating call with a payload | the payload on stdout, exit 0 |
| `write` | `pr merge`, `pr close`, `workflow run`, `run rerun`, `gh api -X POST/PATCH/PUT/DELETE`, `gh api -f/-F/--input` with no method, plus the verbs that would write the arm's workspace or reach the network (`pr checkout`, `repo clone`, `run download`, `release download`, `issue develop`) | a real-shaped `HTTP 403: Resource not accessible by personal access token`, exit 1. Nothing is ever mutated |
| `unknown` | a read with no payload | `gh: Not Found (HTTP 404)`, exit 1 |

**`class=write` records INTENT, not what the fake would have done.** Some of
those verbs are plain reads against the API — `gh release download` is one —
and are refused anyway, because what a fixture needs to know is what the agent
reached for on a live queue, and because the local side effect is one no
stand-in can honestly perform. `gh api -X GET … -f k=v` is the other side of
the same rule: it is gh's own documented read idiom (on GET the fields go to
the query string, not a body), so it stays a `read`.

An unknown read is a 404 and never a Python traceback: an agent that guesses
an endpoint must see what `gh` would have shown it, not the harness's
internals — and the 404 names no payload and no key, so it cannot tell the
agent it is talking to a stand-in. The resolved key goes to the log, where the
fixture reads it. The write list lives in `WRITE_SUBCOMMANDS`; add to it there
rather than forking the file.

`gh` with no arguments prints its usage and exits 0, the way the real one
does; `gh --version` and `gh --help` are answered the same way, without a
payload.

### Deliberate non-features

`--jq`, `-q`, `--json` field selection and `--template` are accepted and
**ignored** — the whole payload is returned. Implementing them would mean
either shipping a jq dependency or reimplementing it, and neither is worth it
for a fake whose job is to hand over a recorded shape. So keep payloads
readable as raw JSON, and never write a fixture check that depends on a
`--jq` expression having been applied.
