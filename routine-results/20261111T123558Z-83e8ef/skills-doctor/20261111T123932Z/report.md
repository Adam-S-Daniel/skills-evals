# Eval report: skills-doctor

- Timestamp: 20261111T123932Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T123558Z-83e8ef; started 2026-11-11T12:39:32Z, ended 2026-11-11T12:40:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.24, judge $0.06, guard $0.00; last agent call $0.08

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.1586 / 0.1586 |
| without_skill | 1 | 0 | 4/6 | 7.8 (7.8 to 7.8, 1 judged) | 0.0782 / 0.0782 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1586 / 0.1586 | 0.0782 / 0.0782 | +0.0804 | +0.0804 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 34414 / 34414 | 25232 / 25232 | +9182 | +9182 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 3583 / 3583 | 2484 / 2484 | +1099 | +1099 |
| cache_creation_input_tokens | 41646 / 41646 | 14479 / 14479 | +27167 | +27167 |
| cache_read_input_tokens | 186638 / 186638 | 171840 / 171840 | +14798 | +14798 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 0/1 | 0/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
