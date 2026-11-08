# Eval report: skills-doctor

- Timestamp: 20261108T015130Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T014918Z-8a8228; started 2026-11-08T01:51:30Z, ended 2026-11-08T01:52:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.29 over 2 call(s); agent $0.29, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.1621 / 0.1621 |
| without_skill | 1 | 0 | 4/6 | skipped (objective-decided) | 0.1252 / 0.1252 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1621 / 0.1621 | 0.1252 / 0.1252 | +0.0369 | +0.0369 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 37007 / 37007 | 39024 / 39024 | -2017 | -2017 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 3431 / 3431 | 3953 / 3953 | -522 | -522 |
| cache_creation_input_tokens | 26931 / 26931 | 16049 / 16049 | +10882 | +10882 |
| cache_read_input_tokens | 200246 / 200246 | 214609 / 214609 | -14363 | -14363 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 0/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
