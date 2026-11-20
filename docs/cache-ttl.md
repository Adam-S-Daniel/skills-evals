# Prompt-cache TTL: 1 hour where the meter allows it

Checked 2026-11-20 on Claude Code 2.1.328. Owner's rule (Adam, 2026-11-20):
use the 1-hour cache "where it's cheaper or nominally the same cost, since at
the same cost it can only save money due to more cache hits."

## Defaults, by surface

Claude Code sorts every request into two buckets: the **main** conversation
(interactive, `claude -p`, Agent SDK turns) and everything else, the
**subagent** bucket (subagents, workflows, background and helper requests).

| Surface | Billed in | Main default | Subagent default | Source |
| --- | --- | --- | --- | --- |
| Claude Code CLI on the workstation, signed in to the subscription | meter | 1 hour | 5 minutes | docs, and 3 days of the workstation transcripts |
| Cloud sessions and routines (claude.ai/code) | meter | 1 hour | 5 minutes | the same CLI on the same subscription; routine fires wrote 1-hour caches before 2026-11-08 (`harness/guidance.py` history) |
| Subscription past its included usage (overage) | dollars | 5 minutes | 5 minutes | docs |
| API key, federation, Bedrock, Vertex, Foundry: eval.yml runs and the API credit lane (`claude-credit`) | dollars | 5 minutes | 5 minutes | docs |
| Messages API called directly | dollars | 5 minutes (`cache_control` without `ttl`) | n/a | API docs |

The default is the same for Fable 5.2, Opus 5.5, Sonnet 5.5 and Haiku 5.5. The
docs name no per-model difference, and the workstation's transcripts from the last three
days show it: every model's main-conversation writes were 1-hour (Opus 16.0M
tokens, Fable 6.5M, Haiku 0.48M, Sonnet 0.09M) and every model's subagent
writes were 5-minute (Opus 8.4M, Sonnet 5.7M, Haiku 0.38M), with no exception.

Docs: [prompt caching in Claude Code](https://code.claude.com/docs/en/prompt-caching.md)
("Claude Code requests the one-hour TTL only on a Claude subscription within
your plan's included usage"), [settings](https://code.claude.com/docs/en/settings-reference.md),
[API prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md).

## The switches

In precedence order, highest first (docs, and the CLI 2.1.328 source):

1. `FORCE_PROMPT_CACHING_5M=1`: 5 minutes everywhere.
2. `CLAUDE_CODE_PROMPT_CACHE_TTL` (main) and `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL` (subagent): `5m` or `1h`.
3. Settings `promptCacheTtl` (main) and `subagentPromptCacheTtl` (subagent).
4. Agent frontmatter `experimental.cacheTtl` (ignored for `1h` on overage).
5. `ENABLE_PROMPT_CACHING_1H=1`: 1 hour in both buckets, on any billing.
6. The default above.

Levels 2, 3 and 5 apply even on dollar billing, so a 1-hour setting must be
kept away from API-billed runs.

## Is 1 hour cheaper on the meter?

Weights from the [usage estimator](https://github.com/Adam-S-Daniel/claude-plan-usage-estimator)
table `2026-11-20`, all-models weekly meter, points per million tokens:

| Model | 5-minute write | 1-hour write | Basis of the 1-hour figure |
| --- | --- | --- | --- |
| Fable 5.2 | 1.086 | 0.824 | measured (night 2): 24% cheaper |
| Fable 5.2, Fable-only meter | 1.643 | 1.657 | measured (night 2): 0.9% dearer, inside the 3% measurement floor |
| Opus 5.5 | 0.253 | 0.253 | assumed equal |
| Sonnet 5.5 | 0.191 | 0.191 | assumed equal |
| Haiku 5.5 | 0.0435 | 0.0435 | assumed equal |

So a 1-hour Fable write moves the all-models meter about 1.21M tokens a point
against 0.92M for a 5-minute one, and the Fable meter by the same amount
either way. The policy counts a 1-hour weight up to 3% above the 5-minute one
as "nominally the same" (3% is the estimator's floor on any measured range). In API dollars the 1-hour write costs 1.6 times the 5-minute one
(2x base input against 1.25x), so dollar-billed lanes stay on 5 minutes.

Opus, Sonnet and Haiku 1-hour writes have not been measured. No existing
dataset I found pairs their 1-hour writes with tick-level meter readings on a
quiet account: night 1 wrote only 5-minute caches, and the eval harness pinned
5 minutes from 2026-11-08. Under the owner's rule, an assumed-equal weight
counts as "nominally the same", so 1 hour wins. A cheap check after the weekly
reset: an `opus-cw1h` and a `sonnet-cw1h` block next to their `cw5` blocks in
the next estimator night (night 2's Fable 1-hour block cost 0.86 all-models
points). A new table that shows 1 hour dearer flips the policy below on its own.

## What changed

| Surface | Before | After |
| --- | --- | --- |
| CLI main conversation on the workstation, cloud, routines | 1 hour (default) | unchanged, left unset so overage still falls back to 5 minutes |
| CLI subagent bucket on the workstation (WSL) | 5 minutes | 1 hour, `subagentPromptCacheTtl` set by the AI Usage collector from the policy (Windows-side Claude Code keeps its own settings file and is not covered) |
| Eval harness, subscription lane (routine fires, local runs) | 5 minutes in both buckets (pinned 2026-11-08) | the policy's TTL in both buckets (1 hour today) |
| Eval harness, API lane (eval.yml) | 5 minutes | 5 minutes, forced |
| API credit lane (`claude-credit`) | 5 minutes (default) | 5 minutes, forced with `FORCE_PROMPT_CACHING_5M=1` so the subscription settings cannot leak in ([adam-agentskills#190](https://github.com/Adam-S-Daniel/adam-agentskills/pull/190)) |
| Cloud sessions' subagent bucket | 5 minutes | unchanged: needs `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL=1h` in each cloud environment's variables, which only the owner can set |

**Caveat.** `subagentPromptCacheTtl` still applies on overage, where the main
bucket falls back to 5 minutes. The account's guard stops loop work at 80% of
the week, so overage is not expected; if it is ever enabled, clear the setting.

**Verification noise.** `verify` cannot tell a transcript's billing lane, so
the workstation's API credit lane and API-billed eval runs (5-minute by design) show up
as a few 5-minute tokens in the main bucket. Read a small share as expected;
a bucket that is mostly the wrong TTL means the CLI changed its defaults or
stopped honoring the setting.

## How the policy is applied

**Where the code lives.** `harness/cache_ttl.py` holds the rule (pure,
stdlib only) and a small CLI (`verdict`, `apply-settings`, `verify`).
`guidance.cli_child_env` applies it to every CLI child (arms, judge, canary,
local eval) after the auto-memory switch, so an ambient value cannot override
it. `scripts/loop_status.py collect` reports it in a `cache_ttl` section.

**The rule.** Adam's rule: use the 1-hour cache "Where it's cheaper or
nominally the same cost, since at the same cost it can only save money due to
more cache hits." Cost is the locked meter weight table's `cache_write_5m` and
`cache_write_1h` (read through `allowance_points.table()`, so the lock and
checksums are checked once, there). A model is 1h only if, on every meter it
appears in, `w1h <= w5m * (1 + 0.03)`; 3% is the table's own measurement floor.
The CLI setting is not per model, so the subscription verdict is 1h only when
every model is 1h. If the table cannot be read, both buckets fall back to 5m.

**The lane split.** A child whose env holds an API credential or a cloud
provider switch (`cache_ttl.API_LANE_ENV`: API key, auth token, federation
or identity-token variables, Bedrock, Vertex, Foundry) bills dollars, where
1h writes cost 2x base input against 1.25x for 5m. It gets
`FORCE_PROMPT_CACHING_5M=1` and loses any ambient TTL variable. Every other
child (a subscription: routine fires, workstation runs) gets
`CLAUDE_CODE_PROMPT_CACHE_TTL` and `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`
set to the subscription verdict.

**The operator's own sessions.** `python3 harness/cache_ttl.py apply-settings
--settings ~/.claude/settings.json` sets only `subagentPromptCacheTtl`, never
`promptCacheTtl`: the main bucket already defaults to 1h on a subscription and
falls back to 5m on overage, and a setting would override that fallback.

**Collector flags.** `loop_status.py collect --claude-settings PATH` applies
that setting (`settings`: `applied`, `unchanged`, `error`, or `skipped` when
the flag is absent); `--claude-projects DIR` tallies observed cache writes by
bucket and model from the last 24 hours of transcripts (`verify`). Output is
numbers and fixed text; an error is a fixed message.

**A new weight table changes it automatically.** `evals/usage-weights.lock`
names the table; nothing else does. Moving the lock to a table where any
model's 1h weight exceeds its 5m weight by more than 3% on any meter flips the
subscription verdict to 5m at the next spawn and the next `apply-settings`;
no code change is needed.
