# ADR 0002: The roster seats each tier's vendor-default model at once and retires the version it superseded after a buffer

- **Status:** accepted (2026-09-27)
- **Issue:** [#202](https://github.com/Adam-S-Daniel/skills-evals/issues/202)
- **Deciders:** Adam, 2026-09-27

## Context

Since 2026-09-22 the roster seated two kinds of arm: every model at or above
the 10% entry bar of rankable census usage, and the newest model past the
7-day cooling-off in a tier that some model already qualified by usage. Both
read the fleet's usage of individual VERSIONS.

Opus 5.5 shipped on 2026-09-22 and became the `opus` alias's default in
Claude Code. The roster step of
[run 35812851203](https://github.com/Adam-S-Daniel/skills-evals/actions/runs/35812851203)
excluded it as inside the cooling-off, so the earliest it could be seated was
about 2026-09-29, and paid eval runs were put on hold until then (HANDOFF.md,
"Eval runs on hold"). Meanwhile `claude-opus-5` kept a usage seat on 45.2%
of the 2026-09-22 census that the fleet will move off as soon as the alias
does.

Evals are valued going forward only. What the fleet will run next week is the
vendor's default version of each family it uses, not the version its history
happened to accumulate usage on.

## Decision

1. **Read the vendor defaults from the docs.**
   `scripts/fetch_model_defaults.py` fetches the Markdown build of the Claude
   Code model-config page (`https://code.claude.com/docs/en/model-config.md`)
   and parses it with `markdown-it-py`: the "Anthropic API" row of the table
   whose header is `Provider` plus backticked alias columns, and prose of the
   form "the `<alias>` alias resolves to <Name> <version>". The table wins
   where both name an alias. `harness/roster.py --defaults` matches each
   display name ("Opus 5.5") to the one available model whose Models API
   `display_name` is that name or `Claude <name>` and whose id is in the
   alias's own tier. No match, several, or a match in another tier leaves that
   tier unresolved, with a `roster: ` warning.
2. **New default → seat now.** In a tier whose default resolved, the default
   is an arm whenever the tier is on the roster — a model in it clears the
   entry bar, a previous arm is in it, or the census is unusable (the existing
   all-tiers fallback). **No cooling-off.** Its reason names the docs source
   and fetch time and why the tier is on the roster.
3. **Usage picks tiers, not versions.** Inside such a tier a superseded
   model earns no seat from its usage however large; its usage still counts
   toward qualifying the tier. A model newer than the default (a release the
   vendor has not made the default) takes no seat.
4. **Superseded → retire after a buffer.** A previous arm superseded by its
   tier's default keeps its seat until `superseded_exit_weeks` (new policy
   key, **1**) complete ISO weeks — Monday 00:00 UTC to Monday, beginning at
   or after the default's `created_at` and ended by the census's
   `generated_at` — have passed, **and** its share over the most recent such
   weeks is under `arm_exit_usage_pct` (2%). A stale census, or a buffer
   window under either ranked-usage floor, holds it. `0` retires it on the
   first run that sees it superseded. The 8-week exit window does not apply
   to a superseded arm.
5. **Unchanged:** a tier with no resolved default keeps both usage rules
   verbatim, cooling-off included; the preflight pick keeps its cooling-off;
   the judge rule is unchanged. With no defaults document — absent, errored,
   empty or junk — the roster is byte-for-byte the one computed without it.

## Consequences

- **The 2026-09-22 census proposes `claude-sonnet-5`, `claude-opus-5` and
  `claude-opus-5-5` at once**, and `claude-opus-5` retires on the first run
  whose census covers a complete ISO week (2026-W40 or later) with it under
  2%. The eval hold no longer waits on the cooling-off.
- **Usage now only picks tiers.** A tier's version churn no longer re-weighs
  the arm set; a fleet that keeps using an old version after its default
  moves on is no longer measured on it once the buffer has run.
- **A docs format change degrades loudly to today's rules.** A fetch or parse
  failure writes `defaults: {}` with an HTTP status or exception class, never
  a body; the roster then applies the usage rules to every tier and warns.
  Nothing fails the workflow step. A silently wrong parse is bounded by the
  display-name match: a name that matches no model in its own tier seats
  nothing.
- **The published roster records what it read** (`defaults`: source, fetch
  time, `{alias: id}`, and unresolved aliases with reasons), so a reviewer of
  a proposal can see why a seat appeared.
- **One more unauthenticated network read** in the roster step. It runs
  before the Models API bearer is exported and carries no credential.

## Alternatives considered

- **Probe `claude --model <alias>` and read the `system/init` event's
  `model`.** Rejected. The probe works with an invalid key and costs nothing,
  but the CLI resolves aliases itself, so it reports the defaults of whichever
  CLI version is installed. Measured 2026-09-27 with an invalid key: CLI
  2.1.283 resolves `opus` → `claude-opus-5-5`, while CI's pinned 2.1.211
  resolves `opus` → `claude-opus-4-8` and `fable` → `claude-fable-5`. Running
  an unpinned latest CLI in the key-bearing job to get a current answer would
  break the pinning convention.
- **Shorten the cooling-off.** Rejected: it would still seat by age rather
  than by what the vendor defaults to, and would also seat a preview the
  vendor has not made the default.
