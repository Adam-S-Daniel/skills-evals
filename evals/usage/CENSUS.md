# The usage census

`scripts/model_usage_census.py` counts which Claude models this account
actually ran, per ISO week, from the local Claude Code transcripts under
`~/.claude/projects`. `scripts/publish_usage_census.sh` runs it and publishes
the result as `usage/latest.json` on the `persistent/eval-results` branch. `harness/roster.py`
reads that file to decide which models earn an arm's seat; when it is absent or
older than 14 days the roster falls back to "newest model per tier" and says so
in every arm's reason ("no fresh census"). Nothing fails silently — but nothing
refreshes the census either, until somebody schedules it.

## Skill usage

The same run also counts how often each skill is invoked, per ISO week, and
the publish script commits it beside the model census as
`usage/weekly-local.json`. The improvement planner reads it through
`harness/skill_usage.py`, so a frequently used skill is improved first; a
missing or stale file reads as unknown, never as zero.

Cloud sessions' skill uses (from the guidance-load Stop hook, _agent-guidance
ADR 0036) are counted through the cloud `skill-digest` rows: `weight` adds
them, and `zero_use` says whether a skill had no use on every surface it
reaches, counting the cloud surface from the week after its first record. Cloud
coverage is only the sessions that can push to adam-agentskills-private.

The schema is defined once, in `harness/skill_usage.py` (`row()`,
`hook_row()`, `document()`, `ROW_FIELDS`); hook rows (below) go into the same
file through it:

```json
{"generated_at": "2026-09-04T12:00:00Z", "schema": 1,
 "sources": [{"surface": "local", "scope": "transcripts",
              "from": "2026-07-13T00:00:00Z", "to": "2026-09-04T12:00:00Z",
              "sessions_scanned": 42}],
 "rows": [{"week": "2026-08-31", "kind": "skill", "name": "workflow-path-audit",
           "repo": null, "surface": "local", "invocations": 3, "sessions": 2,
           "blocked": null, "overridden": null, "outcome": null,
           "runner": null}]}
```

Every row carries the same fields (`ROW_FIELDS`): `week`, `kind`, `name`,
`repo`, `surface`, `invocations`, `sessions`, `blocked`, `overridden`,
`outcome` and `runner`. `runner` is null except on a hook row. A reader treats
it as optional (`.get`; absent is unknown), because `_agent-guidance`'s
`impact-report.js` writes `weekly-ci.json` rows in the same shape without it.

`week` is the Monday (UTC) of the ISO week; rows are sorted by week, kind and
name. `sessions` is the number of distinct transcript files that invoked the
name that week, and `sessions_scanned` the number of transcript files read
inside the window. Neither carries an id. A new run is published when the
rows or the window start changed; `to` and `sessions_scanned` alone do not
trigger a commit.

- **What is counted.** Each `Skill` tool call (once per tool-use id per
  transcript), and each typed slash command whose name is a skill. A plugin
  prefix is dropped (everything up to the last `:`):
  `adam-coding-anywhere:workflow-path-audit`, and an old prefix such as
  `adam:` or `adam-local:`, count as the bare skill name.
- **Allowlist, then `other`.** A skill name is published only when this repo
  already names it publicly: a skill fixture under `evals/` or an
  `evals/non-coverage.yml` row, in either case only when its registry is not
  private. Every other Skill tool call counts under `other`, private-registry
  skills included, and the planner reads their weight as unknown, never 0; a
  typed command that is not an allowlisted skill (`/clear`) is not counted at
  all.
- **Private plugin prefixes.** A Skill call or typed command whose plugin
  prefix (the text before the last `:`) is a plugin of a private registry
  (the `plugins:` list on that entry of `harness/registries.yml`, today
  `adam-private-anything-anywhere`) counts under `other`, even when the bare
  name is allowlisted. This protects prefixed invocations only: an unprefixed
  name resolves by the public allowlist alone.
- **Blind spots.** Cloud sessions are not in local transcripts. A skill loaded
  without the Skill tool (read straight from its `SKILL.md`) is not counted.
  Local eval sessions do not inflate the counts: `local_eval.py` runs a
  one-turn arm without session persistence and moves a multi-turn arm's
  transcripts out of `~/.claude/projects` when it ends.

## Guidance rows

Each weekly row with `kind: "guidance"` counts the local sessions whose
loaded memory files held the full fleet guidance, only the repo stub, or
neither. The census reads the `attachment` entry of type `instructions` that
Claude Code writes to a transcript (every memory file it loaded, with its
text) and classifies each transcript file it already scans, with the same
roots, window and cross-root dedupe:

- `full`: some file contains `guidance-marker: fleet-full`, or the legacy
  heading `## Working in these repos`.
- `stub-only`: otherwise some file contains `guidance-marker: fleet-stub`, or
  the legacy line `Fleet guidance is delivered once per session`.
- `neither`: an instructions entry exists but nothing matched.
- `unknown`: the file has no instructions entry. Older CLI versions do not
  write one, so `unknown` is "could not tell", never "no guidance".

The signatures are constants in `scripts/model_usage_census.py` that mirror
the marker lines of `_agent-guidance`'s `agents-md/base.md` and `stub.md`.
A session counts once, in the ISO week (Monday UTC) of its first timestamped
entry; a session stored twice (Cowork, or under two roots) counts once, and a
subagent transcript (under a `subagents/` directory) is not counted. One row
per (week, state) with a nonzero count: `name` is the state, `repo` and
`invocations` are null, `sessions` the count. Readers that ask about skills
(`weight()`) ignore them. Cloud sessions are not in local transcripts; their
rows are described next. No guidance events go to the private events file.

## Cloud guidance rows

A cloud session's Stop hook in `_agent-guidance`
(`.claude/hooks/guidance-load-record.sh`) appends one record per session to
`events/<YYYY-MM>/cloud-guidance.jsonl` on the private `persistent/usage-events`
branch: `v`, `kind` `guidance-load`, `session` (a sha256 prefix, never the id),
`ts`, `state`, `check_expected`, `check_reported`, `registry_sha` (always null:
the bootstrap's install record names no commit, so a per-source install record
is a follow-up issue), `cli`, `repos` and `guidance_version`.
`scripts/publish_usage_census.sh` fetches that branch before the census and
passes the checkout as `--cloud-guidance DIR`. The census reads every
`events/*/cloud-guidance.jsonl` under it, read-only (it never writes a cloud
file; `merge_events` already refuses a machine named `cloud-…`), and publishes:

- `kind: "guidance"`, `surface: "cloud"`, `name` the session's `state` through
  the fixed set `full`, `stub-only`, `neither`, `unknown` (anything else is
  `invalid`);
- `kind: "guidance-check"`, `surface: "cloud"`, `name` the session's
  `check_reported` through `match`, `mismatch`, `none`, `absent` (anything
  else, or a record without one, is `unknown`).

Both count sessions (`sessions`; `invocations` and every other field null), so
a hostile or corrupt value can only ever appear as `invalid` or `unknown`. A
`guidance-check` row counts the same sessions as the `guidance` rows, so the
dashboard leaves it out of a sum of sessions per week and surface. No session
id, CLI version, repository count or guidance version reaches the public file.

A record before the start of the census window (the Monday of its oldest week)
is dropped, as is one in a later week than the census's. A session counts once,
at its earliest `ts`, however many lines or month files hold it. A malformed
line, or a record without a string `session` or a parseable `ts`, is skipped
and counted nowhere public.

The source is `{surface: "cloud", scope: "guidance-records", from, to,
records_scanned}`, present only when the branch was read. `records_scanned`
is the number of distinct sessions counted; `from` is the later of the census
window's start and the Monday of the earliest record's week, so it is always a
week boundary. **Coverage is unknown**: the hook records only the sessions it
ran in, and the census cannot tell how many cloud sessions wrote nothing, so a
count is a lower bound of unknown tightness, never a share of all sessions.

If the fetch fails (the repository does not answer, or the clone fails; a
branch that does not exist yet is not a failure), the publish still goes ahead,
as it does for any private failure: the previous public file's cloud rows and
cloud source are carried forward verbatim (they are already public), the local
rows and `latest.json` are published as usual, the summary line says `cloud:
carried forward`, and the script exits 1 at the end. A carried source whose
`to` is more than 14 days old is dropped with its rows (the roster treats a
census older than 14 days as missing, and an old count must not look current),
and the summary says `cloud: not read`.

## Loaded skill copies (`skill-digest` rows)

#562 (2026-11-02). Which copy of a skill each local use loaded, counted per
week from the private records (below) and published as:

```
{"week", "kind": "skill-digest", "name", "repo", "surface": "local",
 "invocations", "sessions", "digest", "blocked": null, "overridden": null,
 "outcome": null, "runner": null}
```

- *Which uses.* This run's counted uses of allowlisted skills, the same ones
  the `skill` rows count (typed commands included); a use counted under
  `other` gets no row. For every published name and every week on or after
  the source's `from`, the `skill-digest` invocations sum to the `skill`
  row's. `sessions` is the distinct sessions for that row (never summed
  across weeks).
- *Which copy.* Each use's id is resolved once across the store's machine
  files (`events/*/<machine>.jsonl`; `cloud-*` files are not read here) and
  its cloud shards (below): a
  non-null `digest` beats null, two different non-null digests publish as
  `unknown:conflict`, an id the store does not hold yet takes this run's
  record, and a stored id is final. A stored line whose `digest` is not 64
  lowercase hex, or whose `digest_null_reason` is not a known reason, is
  skipped. An id whose stored lines all predate the copy keys (no `digest`
  key) is excluded, and the source's `from` moves to the Monday after the
  latest such use's week, so no week before `from` has rows.
- *`digest`.* The first 12 hex of the lock digest, only when the copy's
  `registry` is a `private: false` registry in `harness/registries.yml`
  (case-insensitive; `repo` is then its canonical `owner/repo`) AND that
  registry's mirror shows the digest was, at some commit on one of its
  branches, the content of that skill's path (the registry's `layout`, one
  match at the mirror's HEAD): `git rev-list --branches -- <path>`, each
  commit's tree digested as the generator digests a ref. That covers every
  base kind, bootstrap `user-skills` copies included. For a `plugin-cache`
  record whose `ref` is 40 hex, the commit must also be in the mirror itself
  (no lazy fetch) and on a branch there; a record without `ref` (every line
  stored before #562) is decided by content history alone. Otherwise the
  value is `unknown:<reason>`, one of a fixed list
  (`harness/skill_usage.UNKNOWN_REASONS`): the eight `digest_null_reason`
  values, `conflict`, `unlisted-registry` (no public registry, a fork among
  them: `repo` is null and the fork's name stays private) and
  `unverified-commit` (the mirror does not show it, or could not be read).
  An unpublished local edit, for example a dirty skill in a checkout, shows
  as unknown.
- *Source.* `{surface: "local", scope: "skill-records", from, to,
  events_scanned}`, where `events_scanned` is the uses counted on or after
  `from`; present only when the store was read (an empty store when the
  branch does not exist yet). No source means unknown, not zero.
- *Mirrors.* After the census, the publisher clones, bare and blob-less
  (`--filter=blob:none`), only the public registries the run's uses point
  at, anonymously (no credential helper, no global or system config, no
  prompt), into its temp directory. A clone that fails leaves those uses
  `unknown:unverified-commit`, and the summary says `registry: not read`,
  never which registry or why.
- *The last gate.* Before anything is staged, `skill_usage.check_public`
  refuses the weekly file (exit 1, `refusing to publish`) if it holds any
  hex run longer than 12, a `digest` on another kind, a prefix without a
  public `repo`, a `repo` outside the public registries, a reason outside
  the list, or a name outside the allowlist.
- *Carry.* When the store fetch fails, the previous file's local
  `skill-digest` rows and their source are carried forward verbatim, aged
  by that source's `to` like the cloud rows, and the summary says `skill
  copies: carried forward` (or `not read`). The sum rule is not re-checked
  on carried rows; the old `to` shows they are stale.

### Cloud skill copies

#562 PR B, from `_agent-guidance` ADR 0036. A cloud session's Stop hook
(`guidance-load-record.sh`, phase 2) uploads one line per skill use, read from
the main transcript and subagent transcripts, to
`events/<YYYY-MM>/cloud-skills/<16 hex>.jsonl` on the private branch: one
shard per session (the stem is `sha256(session id)[:16]`), each use in the
month of its own `ts`.

```
{"v": 1, "id", "ts", "kind": "skill", "surface": "cloud", "session", "cli",
 "name", "base_kind", "registry", "ref", "digest", "digest_null_reason"}
```

- *Read strictly.* Only a month directory `YYYY-MM` and a 16-hex stem are
  read, never through a link. A line must have exactly these keys: `v` 1,
  `id` `[A-Za-z0-9_-]{1,128}`, `ts` UTC with `Z` in the shard's month,
  `session` equal to the stem, `cli` null or a version, `name` a skill name
  (or the hook's `invalid`), `base_kind` one of `BASE_KINDS`, `registry` null
  or `owner/repo`, `ref` null or 40 hex, and either a 64-hex `digest` with a
  null reason or a null `digest` with one of the eight reasons. Any other
  line is skipped whole. There is no `machine` key.
- *Rows.* `skill-digest` rows with `surface: "cloud"`, by the same chain as
  local (`unknown:<reason>`, `unlisted-registry`, `unverified-commit`, or the
  prefix), one use per distinct id of an allowlisted skill (`other` gets no
  row). An id that is also in this run's records or in a machine file (a
  session teleported to a durable machine) counts once, as local, and its
  lines resolve together. Source `{surface: "cloud", scope: "skill-records",
  from, to, events_scanned}`, `from` being the later of the window's start
  and the Monday of the earliest shard line's week; present only when the
  store was read and holds at least one well-formed shard line (before the
  hook ships, cloud copies are unknown, not zero).
- *Coverage is records seen, never complete.* Uses after a session's last
  successful upload die with the container, and a session that cannot reach
  the private repository records nothing.
- *No cloud `skill` rows.* The totals stay local-only, so the dashboard's
  skill counts do not change; adding cloud totals is Adam's call.
- *`ref`.* The hook records it where it has one (a plugin-cache
  `gitCommitSha`, a user-skills install record's ref) and null otherwise; a
  stale fleet copy of the hook records `ref: null` until its next sync. A
  40-hex `ref` must be on a branch of the mirror, as for local records.
- *Carry.* A failed store fetch carries the previous file's cloud
  `skill-digest` rows and source like the local ones; the summary says
  `cloud skill copies: carried forward` (or `not read`).

## Transcript roots

`--projects` may be repeated or carry several roots separated by `:`. On WSL
the publish script reads, besides `~/.claude/projects`:

- every existing `/mnt/c/Users/*/.claude/projects`: desktop Code-tab and
  remote-control sessions write to the Windows root;
- every `.claude/projects` directory below
  `/mnt/c/Users/*/AppData/Local/Claude-Data/*/local-agent-mode-sessions`: the
  desktop app's Cowork sandbox.

`CENSUS_PROJECTS` replaces all of them. A session reachable from two roots
counts once: a turn, Skill call or typed command whose id an earlier root
counted is skipped. Inside a Cowork root the same holds across files,
because Cowork stores each session twice; inside an ordinary root a resumed
session still counts in each file, as before.

Claude Code on Windows deletes transcripts older than 30 days unless
`cleanupPeriodDays` is set in its settings, so the Windows root covers about
four of the census's eight weeks until that is raised.

## Hook rows

The fleet's git hook runner (agent-checks, managed in `_agent-guidance`)
appends one JSON line per local hook run to
`${AGENT_CHECKS_LOG:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-checks/runs.jsonl}`:
`{"v":1,"ts":"…Z","event":"pre-commit|pre-push","repo":"owner/name"|null,"checks":[ids],"failed":[ids]}`.
The census reads that file (`--hook-logs`, `:`-separated; on WSL the publish
script adds each existing `/mnt/c/Users/*/.local/state/agent-checks/runs.jsonl`,
and `USAGE_HOOK_LOGS` replaces the list) and adds `kind: "hook"` rows:

- `name` is the check id when it matches `^[a-z0-9][a-z0-9-]{0,40}$`, else
  `other`; one `all` row per week counts every run, so totals do not depend
  on the id allowlist.
- `repo` is `owner/name` only for a public repository: a registry in
  `harness/registries.yml` that is not private, `Adam-S-Daniel/skills-evals`
  or `Adam-S-Daniel/_agent-guidance`. Any other repository is `other`; a run
  with no repository is null.
- `invocations` is the runs in which the check ran, `blocked` the runs in
  which it failed; `sessions` and `overridden` are null.
- `runner` is the first 12 hex of the runner file's sha256 that the log line
  carries (`"runner"`, or null). It is published only when it is a string
  matching `^[0-9a-f]{12}$`, else null. It is part of a row's key, including
  the `all` row, so two runner builds in one week give two rows whose
  `invocations` sum to the old single row; readers that sum hook rows
  (`hook_block_report.py`, the dashboard, the publisher's summary) sum across
  it, and the dashboard drops the field.
- Malformed lines are skipped, and a line found in two logs counts once.
  A `scope: "hooks"` source with `runs_scanned` is added only when a log was
  read, so no hook source means unknown, not zero.

## Private usage events

Fine-grained records, kept for refined reporting later, live **only** in the
private repository: branch `persistent/usage-events` of
`Adam-S-Daniel/adam-agentskills-private`, as
`events/<YYYY-MM>/<machine>.jsonl`. The census writes them with
`--events-out`; the publish script merges them in after the public publish.

- **Skill records:** `{"v":1,"id","ts","kind":"skill","name","model","effort","context_tokens","surface":"local","root","cli","machine","session_id","session_title","cwd_repo","branch"}`.
  `id` is the tool-use id, or the user entry's uuid for a typed command;
  `name` is the skill id as invoked (`plugin:skill`), raw but capped;
  `root` is `wsl`, `windows` or `cowork`; `session_title` is the
  transcript's latest summary or custom title; `cwd_repo` is the `owner/name`
  of the session directory's github.com `origin` when that directory still
  exists. `model` is the session's model at the call (for a typed command,
  the next assistant turn's that is not `<synthetic>`), sanitized like the
  census keys (non-model-id values become `other`), null when unknown;
  `effort` (the turn's effort level, allowlisted, else `other`) and
  `context_tokens` (input plus cached input tokens on that turn, i.e. how
  full the context was) come from the same assistant turn, null when
  unknown; earlier records lack them and are not rewritten (merge keeps
  existing lines byte for byte). `cli` is the Claude Code version, read from
  the `version` field of that transcript line (the value at use time), null
  when the line has none.
- **Which copy was loaded** (skill records only):
  `"digest","digest_null_reason","base_kind","registry","ref"`. No path is
  ever recorded. None of the five reaches a public file except as the 12-hex
  prefix of a verified `digest` in a `skill-digest` row (above).
  - *Base directory.* Taken only from a later user entry with `isMeta` true
    that links to the call (a Skill call by `sourceToolUseID`, a typed
    command by `parentUuid` equal to the typed entry's `uuid`) and whose
    FIRST line is `Base directory for this skill: <path>`. A
    `C:\…` path reads as `/mnt/c/…`, a `\\wsl.localhost\<distro>\…` or
    `\\wsl$\<distro>\…` path as the Linux path; then symbolic links are
    resolved.
  - *`base_kind`.* `plugin-cache` (`<.claude>/plugins/cache/<marketplace>/<plugin>/<version>/skills/<name>`),
    `account-sync` (under `<.claude>/skills/synced/`), `account-plugin` (a
    Cowork `local-agent-mode-sessions` path), `repo` (inside a git work
    tree), `user-skills` (`<.claude>/skills/<name>` outside one), `builtin`
    (`schedule`, `update-config`, `loop` or `simplify` with no base
    directory, or a path under a `bundled-skills` directory), else `unknown`.
  - *`digest`.* The lock digest a `skills.lock` names
    (`harness/skill_digest.py`; a `repo` copy leaves out the files git
    ignores), bare hex. The directory is hashed at most once per run.
  - *`digest_null_reason`*, null when there is a digest: `bad-name` (the
    name, less one `plugin:` prefix, is not a skill directory name),
    `no-base-dir` (no linked message, or its directory has another name),
    `builtin`, `outside-known-roots` (kind `unknown`; not hashed), `gone`
    (the directory is missing or unreadable), `changed-since-load` (some
    file or directory in the skill tree has an mtime or ctime later than the
    record's `ts`; for `plugin-cache` the tree is `skills/<name>` only),
    `refused-by-registry-rules` (a symbolic link or a special file) or
    `too-large` (over 2000 files or 50 MiB).
  - *`registry`.* `plugin-cache`: the `owner/repo` of a `github` source for
    that marketplace in `<.claude>/plugins/known_marketplaces.json`.
    `user-skills`: the skills-bootstrap install record's registry for that
    name (`<.claude>/skills/.skills-bootstrap-installed.json`), only when
    its digest equals this copy's and its URL is
    `https://github.com/<owner>/<repo>`. `repo`: the checkout's github.com
    `origin`. Null otherwise. Earlier records lack all four keys and are
    not rewritten.
  - *`ref`* (#562). `plugin-cache` only: the `gitCommitSha` that
    `<.claude>/plugins/installed_plugins.json` (version 2) records for the
    install whose `installPath` is this copy's version root, when it is 40
    lowercase hex; null otherwise and for every other kind. It is the
    marketplace clone's commit, shared by every plugin installed from it,
    which is harmless: it only has to be a commit on a public branch.
    Records stored before #562 lack it and are not rewritten.
- **Hook records:** `{"v":1,"id","ts","kind":"hook","event","repo","checks","failed","runner","surface":"local","root","machine"}`,
  `id` being the SHA-256 of the machine name and the raw log line. `runner`
  is the sanitized digest above, null when absent or malformed. Hook lines
  already merged keep their bytes; nothing is back-filled.
- **Reserved `cloud-` machine prefix.** Files `events/*/cloud-*.jsonl` and
  the shards `events/*/cloud-skills/<16 hex>.jsonl` are written by cloud
  hooks, never by this census: `merge_events` refuses a machine name starting
  with `cloud-` (ValueError), the publish script refuses to stage any such
  file, and `hook_block_report.py` skips them when loading.
  They cannot be regenerated; a re-created branch loses them.
- **Merge.** By `id`: existing lines are kept as they are, new ids are added,
  each file stays sorted by `ts`. A commit (`usage events [skip ci]`) is made
  only when something was added; the push gets one `pull --rebase` retry and
  is verified with `git merge-base --is-ancestor`. Only `events/…` files (and
  the README when the branch is created) may be staged, and a path through a
  symbolic link is refused, so nothing is ever written under `lessons/`.
- **Privacy.** The records carry timestamps, session ids and titles,
  repositories and branches, which is why they never reach the public
  branch. The publish script's output names counts only.
- **Regenerable for the last 8 weeks only.** If the branch is deleted, the
  next run recreates it as an orphan with a README, from what the machine
  still holds: the census window. Anything older exists only on the branch.
- **No ruleset.** Rulesets cannot protect a branch of that private repository
  on this plan, so nothing guards it against deletion or a force push.
- **Failure is isolated.** A private publish that fails prints one line
  naming the step and nothing else, and the script exits 1 after the public
  census has been published.

## Weekly review of blocked hook runs

`scripts/hook_block_report.py` reads the private events and the two public
weekly files, groups blocked local hook runs by repository, check and hour,
flags one repository driving most blocks or a steady hourly repeat (a
scheduled job retrying), and checks that each source is fresh. Its output
names repositories and machines, so it is private: a weekly routine files it
as an issue in the private repository and fixes what it finds. The procedure
is [`docs/hook-block-review-routine.md`](../../docs/hook-block-review-routine.md).

## Why it runs on the owner's durable machine

It reads transcripts, and only the machine where Claude Code is used day to day
has them. A GitHub runner has none, and a cloud session has only its own. So
this is neither a workflow nor a Routine: it is a scheduled task on the owner's
own machine, which is why the owner sets it up himself (below).

It used to ride along as a step of the Tier-3 account-store Routine. That
Routine, and the audit it existed for, were retired on 2026-09-28 (see
`HANDOFF.md`, the 2026-09-28 amendment near the top), so the census needed its own home.

## The privacy contract

The public output is committed to a **public** branch, so it is the narrowest thing
that answers the question: `{model_id: {iso_week: count}}`, plus the metadata
keys `generated_at` and `weeks`. No project names, no paths, no prompt or reply
text, no session ids, no timestamp finer than a week. The transcripts carry every
one of those; `~/.claude/projects/` encodes the project path in the directory
name alone.

- Weekly buckets, not daily: a daily series over one account is a record of when
  a person was at their desk, and the roster policy only asks about 4- and
  8-week windows.
- Keys are not trusted either. `message.model` is whatever the routing layer
  wrote, and has been observed carrying a Bedrock ARN (an AWS account number), a
  Vertex path (a GCP project id) and free prose. Only values shaped like a model
  id become keys; everything else is counted under the single key `other`.
- The guard is a test, not a convention:
  `test/run_tests.py::TestIssue67::test_census_emits_only_model_week_counts_and_leaks_nothing`
  (and its `TestIssue67Review` siblings) runs the parser over a transcript
  carrying a project path and prose and asserts neither survives into the output.
  `TestPublishUsageCensus` runs the same shape end to end through the publish
  script against a local bare repository and asserts the pushed file holds only
  those keys and that the script's one summary line holds totals only.
- The publish script prints one line — model count, turn total, skill
  invocation total, hook run total, week count, and how many private events
  were new — with no path under `$HOME`, no per-model or per-skill figures and
  no record content. It handles no token: it uses the git credentials the
  machine already has.

## Setting it up (the owner does this once)

Prerequisites on the machine: `git` with push access to
`Adam-S-Daniel/skills-evals` and `Adam-S-Daniel/adam-agentskills-private` over
HTTPS or SSH (the credentials you already use),
`python3`, and PyYAML (`python3 -m pip install --user pyyaml`; the census reads
the tier ladder from `evals/roster-policy.yml` through `harness/roster.py`).

Try it first. A dry run does everything except the push:

```bash
bash /path/to/skills-evals/scripts/publish_usage_census.sh --dry-run
```

It prints e.g. `usage census: 4 models, 1234 assistant turns, 56 skill
invocations, 210 hook runs, 8 weeks; dry run, committed locally and pushed
nothing; private events: 12 new of 266, dry run`. The script clones skills-evals into a temp
dir itself, so it always runs the census from `main`, and it re-publishes at least
every 6 days even when the counts have not moved, so an idle account does not age
out of the roster's 14-day freshness window.

### Option A: a Claude Desktop scheduled task

Create a scheduled task, daily, with this prompt (replace the path with where
your checkout of skills-evals lives on that machine):

```text
Run exactly this command and report its single output line, or its error if it
fails. Do not edit any file, do not run anything else, and do not print the
contents of any Claude Code transcript.

bash ~/repos/Adam-S-Daniel/skills-evals/scripts/publish_usage_census.sh
```

### Option B: cron (or a systemd timer) in WSL

Daily at 06:37 local time, with the output kept in a log you can read:

```cron
37 6 * * * bash "$HOME/repos/Adam-S-Daniel/skills-evals/scripts/publish_usage_census.sh" >> "$HOME/.cache/usage-census.log" 2>&1
```

Add it with `crontab -e`. WSL only runs cron while a WSL instance is running and
the `cron` service is started, so a laptop that sleeps will skip days; the
14-day freshness window tolerates that. A systemd user timer that runs the same
`bash …/publish_usage_census.sh` line is equivalent.

### Option C: a Windows Task Scheduler task that runs `wsl.exe` invisibly

On a Windows machine where Claude Code runs inside WSL, register the census
alongside the other WSL tasks from
[`wsl-automation`](https://github.com/Adam-S-Daniel/wsl-automation). Its
`scripts\register-tasks.ps1` (elevated PowerShell 7) now adds a task named
**Usage Census Publish** whose action is `wsl.exe` itself, with no PowerShell in
between:

```text
C:\Windows\System32\wsl.exe --distribution Ubuntu --cd "<wsl-automation checkout>\scripts" --exec /bin/bash ./publish-usage-census.sh
```

- **Invisible.** The task runs as the owning user with an S4U logon ("run
  whether the user is logged on or not", no stored password), so it runs in
  session 0, where no console window can appear. It needs the "Log on as a
  batch job" right, which wsl-automation's other background tasks already
  require (`scripts\grant-keeper-batch-logon.ps1`).
- **Always `main`.** `publish-usage-census.sh` shallow-clones skills-evals and
  runs that clone's `publish_usage_census.sh`, so what runs does not depend on
  which branch a local checkout happens to be on.
- **Daily at 12:37**, with no catch-up: a day the machine sleeps through is
  skipped, which the 14-day window and the 6-day re-publish absorb. A catch-up
  at wake would land in WSL's post-wake transition window, and 12:37 stays
  clear of the backup task's on-the-hour retries (`wsl --export` stops the
  distro).
- **Git credentials come from WSL.** An S4U logon has no stored password, so
  do not count on a Windows-side credential helper such as Git Credential
  Manager. `gh auth git-credential` with the token in `~/.config/gh/hosts.yml`
  works.
- **A log you can read.** Each run appends one line to `~/.cache/usage-census.log`
  inside WSL: a UTC timestamp, the exit code and the script's summary line.

### Checking that it works

`git ls-remote https://github.com/Adam-S-Daniel/skills-evals persistent/eval-results` should
move after a run that found changed counts, and the branch's
`usage/latest.json` carries the run's `generated_at`. The next roster run
(`roster/latest.json`) reports the census timestamp in its `source.census_at`.

For Option C, run it once on demand and read the result:

```powershell
Start-ScheduledTask -TaskName 'Usage Census Publish'
(Get-ScheduledTaskInfo -TaskName 'Usage Census Publish').LastTaskResult   # 0 once it finishes
wsl.exe -d Ubuntu -- tail -n 3 '~/.cache/usage-census.log'
```

`LastTaskResult` is `267009` while the task is still running. Quote the `~`:
PowerShell 7 would otherwise expand it to the Windows home before `wsl.exe`
sees it.

## Known gap: Windows-native publishing

Under WSL the Windows and Cowork roots are read (see "Transcript roots").
Running the publish script natively on Windows, outside WSL, is not
supported.
