# Eval report: skills-doctor

- Timestamp: 20261111T141035Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T140609Z-edec11; started 2026-11-11T14:10:35Z, ended 2026-11-11T14:11:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | skipped: the version with the skill passed more checks (5 of 6 vs 4 of 6) | 0.1192 / 0.1192 |
| without_skill | 1 | 0 | 4/6 | skipped: the version with the skill passed more checks (5 of 6 vs 4 of 6) | 0.1084 / 0.1084 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1192 / 0.1192 | 0.1084 / 0.1084 | +0.0108 | +0.0108 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 30567 / 30567 | 47127 / 47127 | -16560 | -16560 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 3232 / 3232 | 4421 / 4421 | -1189 | -1189 |
| cache_creation_input_tokens | 26661 / 26661 | 17063 / 17063 | +9598 | +9598 |
| cache_read_input_tokens | 201721 / 201721 | 215075 / 215075 | -13354 | -13354 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 0/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
