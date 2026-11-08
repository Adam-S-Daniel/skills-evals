# Eval report: skills-doctor

- Timestamp: 20261108T004226Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T004047Z-5f4bdd; started 2026-11-08T00:42:26Z, ended 2026-11-08T00:43:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.1537 / 0.1537 |
| without_skill | 1 | 0 | 4/6 | skipped (objective-decided) | 0.1096 / 0.1096 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1537 / 0.1537 | 0.1096 / 0.1096 | +0.0441 | +0.0441 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 26553 / 26553 | 27802 / 27802 | -1249 | -1249 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2884 / 2884 | 2877 / 2877 | +7 | +7 |
| cache_creation_input_tokens | 26216 / 26216 | 14989 / 14989 | +11227 | +11227 |
| cache_read_input_tokens | 199422 / 199422 | 208164 / 208164 | -8742 | -8742 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 0/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
