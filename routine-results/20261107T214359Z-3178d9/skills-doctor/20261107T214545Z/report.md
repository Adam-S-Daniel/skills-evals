# Eval report: skills-doctor

- Timestamp: 20261107T214545Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T214359Z-3178d9; started 2026-11-07T21:45:45Z, ended 2026-11-07T21:46:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 2 call(s); agent $0.27, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.1576 / 0.1576 |
| without_skill | 1 | 0 | 4/6 | skipped (objective-decided) | 0.1133 / 0.1133 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1576 / 0.1576 | 0.1133 / 0.1133 | +0.0443 | +0.0443 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 30614 / 30614 | 32579 / 32579 | -1965 | -1965 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3394 / 3394 | 3178 / 3178 | +216 | +216 |
| cache_creation_input_tokens | 26811 / 26811 | 15141 / 15141 | +11670 | +11670 |
| cache_read_input_tokens | 163676 / 163676 | 209171 / 209171 | -45495 | -45495 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 0/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
