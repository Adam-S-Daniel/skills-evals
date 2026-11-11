# Eval report: skills-doctor

- Timestamp: 20261111T101621Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T101450Z-0b2b10; started 2026-11-11T10:16:21Z, ended 2026-11-11T10:17:31Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 4 call(s); agent $0.20, judge $0.06, guard $0.00; last agent call $0.08

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 9.5 (9.5 to 9.5, 1 judged) | 0.1132 / 0.1132 |
| without_skill | 1 | 0 | 5/6 | 9.5 (9.5 to 9.5, 1 judged) | 0.0822 / 0.0822 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1132 / 0.1132 | 0.0822 / 0.0822 | +0.0311 | +0.0311 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 27446 / 27446 | 26302 / 26302 | +1144 | +1144 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2753 / 2753 | 2775 / 2775 | -22 | -22 |
| cache_creation_input_tokens | 26208 / 26208 | 14876 / 14876 | +11332 | +11332 |
| cache_read_input_tokens | 201554 / 201554 | 171927 / 171927 | +29627 | +29627 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
