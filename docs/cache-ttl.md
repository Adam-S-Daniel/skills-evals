# Prompt-cache TTL

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
