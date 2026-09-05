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
| [`gh`](gh) | the GitHub CLI | `$GH_REPLAY_DIR` |

(`evals/windows-elevation-from-wsl/seed/bin/powershell.exe` predates this
directory and stays with its fixture — it is machine-specific and no second
fixture reuses it.)

## `gh`

### Wiring a fixture to it

```yaml
# evals/<skill>/fixture.yaml
env:
  PATH: "$WORKSPACE/bin:$PATH"          # the fake shadows any real gh
  GH_REPLAY_DIR: "$WORKSPACE/.gh/replay"   # a dot-dir: see below
  GH_REPO: "example-org/example-site"   # only shapes the 403's URL
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
the very check that was meant to tell those two apart. A `.gh/replay/` sibling
keeps them out of plain view, and the seed's README says nothing about them.

**And name nothing after this harness.** The arm's workspace is the agent's
cwd under `bypassPermissions`, so `pwd`, `ls -a`, `git log`, `env` and `cat
bin/gh` are all reachable. That is why the variables are `GH_REPLAY_DIR` and
`GH_REPO` rather than `FAKE_GH_*`, why the payload directory is `.gh/replay`
rather than `.fake-gh/payloads`, why `run_eval.py`'s `WORKSPACE_PREFIX` and
`SEED_COMMIT_IDENTITY` say nothing about this repository or the arm, and why
[`gh`](gh) reads as a plain offline replay of the CLI: the word "fake"
appears nowhere in it. Keep it that way — the source of truth for what an arm
may read is here, not in the file the agent gets a copy of.
`TestIssue84Review.test_nothing_the_arm_can_read_names_the_instrument`
materializes an arm workspace with the harness's own code and greps every
byte of it — and every variable of the environment it hands over.

**That environment is an ALLOWLIST.** `agent_env` forwards, from the
harness's own environment, only the exact names in `_ALLOWED_ENV` (`PATH`,
`HOME`, `USER`, `LOGNAME`, `SHELL`, `TERM`, the locale and timezone names,
the temp-dir names, the proxy names in both cases, and the CA-bundle names)
and the prefixes in `_ALLOWED_ENV_PREFIXES` (`ANTHROPIC_`, `CLAUDE_`, `LC_`,
`XDG_`), each carrying its reason in the source. Everything else is dropped.
On top of that it sets `WORKSPACE`, points `GH_CONFIG_DIR` at a directory
inside the workspace, and sets `GH_TOKEN` / `GITHUB_TOKEN` to empty strings
— empty rather than absent, because an absent token sends `gh` looking in
its config and the keyring for another one. The fixture's own `env:` block
is applied last, so a fixture that wants a name back says so.

It was a denylist until round 5, and a denylist forwards whatever nobody
named. Measured then, through `run_eval.py --arm without_skill` with a
stand-in `claude` that dumps its own environment: `GH_HOST`,
`GH_ENTERPRISE_TOKEN` and `GITHUB_ENTERPRISE_TOKEN` — the other half of
`gh`'s own credential resolution — arrived verbatim, along with `AWS_*`,
`NPM_TOKEN`, `GITLAB_TOKEN`, `OPENAI_API_KEY`, `HF_TOKEN`, `SSH_AUTH_SOCK`,
`KUBECONFIG`, `DOCKER_CONFIG`, `GIT_ASKPASS`, `PYTHONPATH`, `LD_PRELOAD`
and variables whose values name the operator's checkout.

So what an arm that reaches a REAL `gh` by absolute path — past the
stand-in on `PATH`, under `bypassPermissions` — finds in its environment is:
no host (`GH_HOST` is not on the list), and no usable token (`GH_TOKEN` and
`GITHUB_TOKEN` are empty; `GH_ENTERPRISE_TOKEN` and `GITHUB_ENTERPRISE_TOKEN`
are not on the list). `TestIssue84Round5` measures that end to end — it
launches `run_eval.py` as a subprocess whose whole environment the test
builds, plants the runner set and eighteen operator variables alongside the
forwarded ones, and compares the SET of names the arm received against the
set the allowlist admits. What a `gh` config or keyring somewhere else on
the machine might still hold is outside what those tests measure;
`GH_CONFIG_DIR` moves the config lookup into the workspace, which ships no
`hosts.yml`.

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
- **A bare `-` after a value-taking flag is that flag's value**, as it is in
  pflag, which is what gh parses with: `--body-file -` means "read the body
  from stdin". Read as a positional instead, it shifted every later
  positional by one — `pr comment 421 --body-file -` keyed to
  `pr-comment-421--.json`, and `api --input - repos/o/r/pulls/421` keyed to
  `api/-.json`, a payload no response set ships, on a call whose real
  endpoint was never looked up. A bare `-` in any other position is still a
  positional.
- **A shorthand whose meaning differs per subcommand must be written
  long-form, unless one subcommand owns it.** `-w` is boolean `--web` on
  `gh pr view` but `--workflow <name>` on `gh run list`; a flat global set
  gets one of them wrong whichever way it is listed, so such shorthands are
  in neither set and a fixture writes `--workflow` / `--web` in full. Where
  naming the subcommand settles it, `SUBCOMMAND_BOOLEAN_FLAGS` does that
  instead: `-i` is boolean `--include` on `gh api` and `--interval
  <duration>` on `gh pr checks`, so it is boolean under `api` and takes its
  value everywhere else. Listed globally it swallowed the duration; omitted
  entirely it swallowed the endpoint, and `gh api -i repos/…` 404'd.
- **A flag given twice is last-wins, as in gh.** `-X GET -X POST` POSTs,
  because both tokens bind one variable — and a shorthand binds the same
  variable as its long form, so `-X POST --method GET` is a GET. Shorthands
  whose long form is consulted (`-X`, `-R`, `-f`, `-F`) are normalized to it
  at parse time, which is what keeps the two spellings in one argv-ordered
  list. Taking the FIRST value classed `-X GET -X POST` a read and let the
  mutation through unrecorded.
- A `.json` key falls back to a `.txt` payload, so a command whose real output
  is plain text (`gh auth status`, `gh pr diff`) gets a file named for what it
  holds. The key does not change — only which file backs it.
- `gh --version` and `gh --help`, as the WHOLE invocation, are answered by the
  fake itself and need no payload: a 404 there reads as "the tool is broken"
  and can derail a run before it reaches the fixture's own surface.
  `gh pr list --help` is still an ordinary `pr-list.json` read.

### Classes, and what each one does

Every invocation is appended to `.gh-invocations.log` at the root of the
checkout the stand-in sits in (see "Where the log lives" below) as

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

**`key=` is the normalized-argv key, not a claim that a payload was served.**
It is recorded for every class — an `unknown` read logs the key that resolved
to nothing, and a refused `write` logs the key its argv normalizes to. That is
what lets a fixture name the *target* of a write mechanically: flags are
dropped from the key, so `pr close --delete-branch 421` and `pr close 421
--delete-branch` are the same `key=pr-close-421.json`, and flag order cannot
dodge a check. Deciding the same thing by reading the agent's prose does not
work — see `evals/cms-stuck-pr-triage/fixture.yaml`'s `pr-c-left-alone`.

The record is written **before** any output, and any failure writing it is
swallowed: an argv that will not decode, a closed pipe or a full disk must not
cost the log its evidence. A fixture that asserts "the agent attempted no
write" should therefore set **`require_present: true`** on that check — a
`must_not_match` over a missing file passes, so without it the check can pass
on zero evidence, and with it the scorer fails the check by name when the log
is absent or empty. (Listing a positive `must_match: "^--- invocation "`
beside the negative patterns is still worth doing — it says what a used log
looks like — but it is no longer what makes the check fail closed.)

### Where the log lives

**Where the workspace says, in an anchor the harness wrote.** ONE rule, and
the whole of it: two directories up from the binary's own real path is
`<root>`; the single line in `<root>/.git/workspace-root` names the
directory the log sits in. `materialize_workspace` writes that anchor after
the baseline commit. In an arm's workspace the binary is `<root>/bin/gh`,
so the anchor is the workspace's own path and the log is
`<root>/.gh-invocations.log`.

The anchor is under `.git/` for four reasons at once: `git status` never
shows it (measured), no objective check in this repository globs into
`.git/` (measured across every fixture, and `glob` does not match a leading
dot without being told to), `cp -a` of the WHOLE workspace carries it — and
it still names the ORIGINAL, so a copy of the workspace records where the
original does — and a bare copy, or a hard link, of the binary alone does
not have it.

**With no anchor to read, it refuses.** One `gh`-shaped line on stderr, exit
1, no payload on stdout, and no log written: each row below asserts that no
`.gh-invocations.log` appears anywhere under the directory the copy was run
from, and that the workspace's own log is byte-identical to before. That
covers a copy of the
binary in some other `bin/`, a hard link in one, a copy at
`$WORKSPACE/.gh/bin/gh`, a copy outside any `bin/`, the shipped binary run
in place from its own directory (so a stray run leaves nothing behind in the
repo), the source piped into an interpreter, and a workspace moved after it
was materialized.

Two earlier rules were weaker in ways that were measured, not guessed.
Deducing the directory from a VARIABLE let a shell move one record and leave
every earlier read in place: `WORKSPACE=/elsewhere gh pr close 421` first,
and then `GH_REPLAY_DIR=/tmp/x gh pr close 421` — a write is refused before
any payload is looked up, so moving the responses cost it nothing — and both
times the checks that read the workspace log scored the run clean. Deducing
it from a directory NAME (was the parent called `bin`?) let a COPY of the
binary in any other `.../bin/` record into that directory's parent, and a
copy at `$WORKSPACE/.gh/bin/gh` record into `$WORKSPACE/.gh`, both out of
sight of anything reading the workspace root. Measured on the branch that
shipped the name rule: `gh pr close 421` through such a copy left
`pr-c-left-alone`, `no-write-attempted` and `loop-log-was-read` all passing.

**What this does not bound, stated plainly.** Relocating a record now takes
editing the anchor or editing the log — both ordinary files in the arm's own
workspace, which is the evidence-editing class
`evals/cms-stuck-pr-triage/fixture.yaml`'s trust-model paragraph already
concedes and leaves to the judge. The interpreter sits under the same
ceiling: `PYTHONPATH` plus a planted `sitecustomize.py` that stubs
`os.path.realpath` is a knob below this file, not one it reads. So the claim
is "nothing THIS FILE reads is settable", not "nothing settable is
consulted".

A fixture author who wants to run the binary outside `materialize_workspace`
writes the anchor by hand — one line, the workspace's absolute path, at
`<workspace>/.git/workspace-root`.

| Class | When | Result |
|---|---|---|
| `read` | a non-mutating call with a payload | the payload on stdout, exit 0 |
| `write` | `pr merge`, `pr close`, `workflow run`, `run rerun`, `gh api -X POST/PATCH/PUT/DELETE`, `gh api -f/-F/--input` with no method, plus the verbs that would write the arm's workspace or reach the network (`pr checkout`, `repo clone`, `run download`, `release download`, `issue develop`) | a real-shaped `HTTP 403: Resource not accessible by personal access token`, exit 1. Nothing is ever mutated |
| `unknown` | a read with no payload, or one that will not decode as UTF-8 | `gh: Not Found (HTTP 404)`, exit 1 |

`gh api graphql` is decided by its DOCUMENT, not by its method or its body
flags: every graphql call is a POST on the wire, so `-f query=query{…}` is a
`read` and `-f query=mutation{…}` is a `write`. A document the fake cannot
read (`-F query=@file.graphql`, or no `query=` field) counts as no mutation,
so an ordinary read is never refused.

`--` ends gh's own flag parsing, but not this one's reading of intent: on
`gh api -- <endpoint> -X POST` the tokens behind the `--` are still scanned
for a method and body fields, so the call is classed `write`. The payload key
is unaffected — it is built from the endpoint, which is the first positional
either way.

**`class=write` records INTENT, not what the fake would have done.** Some of
those verbs are plain reads against the API — `gh release download` is one —
and are refused anyway, because what a fixture needs to know is what the agent
reached for on a live queue, and because the local side effect is one no
stand-in can honestly perform. `gh api -X GET … -f k=v` is the other side of
the same rule: it is gh's own documented read idiom (on GET the fields go to
the query string, not a body), so it stays a `read`.

`exit=` is the code the CALLER got, not the one intended: the record goes
down before the payload, and is corrected in place if writing that payload
then fails. A read logged `exit=0` whose output never arrived would say a
payload was served when it was not.

Which is why **a check asking whether a file was READ should not anchor
`exit=`**: the caller's code is the caller's business, and a large payload
piped into a reader that stops early (a `head`, a closed pipe, a full disk)
lands `exit=1` on a read that served the payload in full. Match
`class=read key=<key>` and stop there. A read with no payload is
`class=unknown`, so the class alone already separates the two.

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
