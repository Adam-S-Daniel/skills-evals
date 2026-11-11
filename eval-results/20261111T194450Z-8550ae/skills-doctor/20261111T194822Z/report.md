# Eval report: skills-doctor

- Timestamp: 20261111T194822Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T194450Z-8550ae; started 2026-11-11T19:48:22Z, ended 2026-11-11T19:49:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.20 over 2 call(s); agent $0.20, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | skipped: the version with the skill passed more checks (5 of 6 vs 4 of 6) | 0.1164 / 0.1164 |
| without_skill | 1 | 0 | 4/6 | skipped: the version with the skill passed more checks (5 of 6 vs 4 of 6) | 0.0881 / 0.0881 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1164 / 0.1164 | 0.0881 / 0.0881 | +0.0283 | +0.0283 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 28592 / 28592 | 25699 / 25699 | +2893 | +2893 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 3032 / 3032 | 2892 / 2892 | +140 | +140 |
| cache_creation_input_tokens | 26339 / 26339 | 15183 / 15183 | +11156 | +11156 |
| cache_read_input_tokens | 201912 / 201912 | 211537 / 211537 | -9625 | -9625 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 0/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
