# Eval report: skills-doctor

- Timestamp: 20261111T173710Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T173523Z-39e3f2; started 2026-11-11T17:37:10Z, ended 2026-11-11T17:39:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 4 call(s); agent $0.57, judge $0.12, guard $0.00; last agent call $0.22

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.3458 / 0.3458 |
| without_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.2196 / 0.2196 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3458 / 0.3458 | 0.2196 / 0.2196 | +0.1262 | +0.1262 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 53525 / 53525 | 65684 / 65684 | -12159 | -12159 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 4888 / 4888 | 4509 / 4509 | +379 | +379 |
| cache_creation_input_tokens | 41535 / 41535 | 17319 / 17319 | +24216 | +24216 |
| cache_read_input_tokens | 201689 / 201689 | 214118 / 214118 | -12429 | -12429 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
