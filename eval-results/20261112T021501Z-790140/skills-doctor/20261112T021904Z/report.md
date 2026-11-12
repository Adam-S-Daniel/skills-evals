# Eval report: skills-doctor

- Timestamp: 20261112T021904Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T021501Z-790140; started 2026-11-12T02:19:04Z, ended 2026-11-12T02:20:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.39 to 0.39, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.24, judge $0.06, guard $0.00; last agent call $0.09

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.5 (8.5 to 8.5, 1 judged) | 0.1514 / 0.1514 |
| without_skill | 1 | 0 | 5/6 | 9.8 (9.8 to 9.8, 1 judged) | 0.0854 / 0.0854 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1514 / 0.1514 | 0.0854 / 0.0854 | +0.0659 | +0.0659 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 29651 / 29651 | 23833 / 23833 | +5818 | +5818 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3288 / 3288 | 2640 / 2640 | +648 | +648 |
| cache_creation_input_tokens | 41388 / 41388 | 15185 / 15185 | +26203 | +26203 |
| cache_read_input_tokens | 149940 / 149940 | 210441 / 210441 | -60501 | -60501 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
