# Eval report: skills-doctor

- Timestamp: 20261111T165817Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T165446Z-aa8d61; started 2026-11-11T16:58:17Z, ended 2026-11-11T16:59:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 4 call(s); agent $0.20, judge $0.07, guard $0.00; last agent call $0.09

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.1153 / 0.1153 |
| without_skill | 1 | 0 | 5/6 | 9.2 (9.2 to 9.2, 1 judged) | 0.0883 / 0.0883 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1153 / 0.1153 | 0.0883 / 0.0883 | +0.0271 | +0.0271 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 25832 / 25832 | 32669 / 32669 | -6837 | -6837 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3140 / 3140 | 2925 / 2925 | +215 | +215 |
| cache_creation_input_tokens | 26949 / 26949 | 15167 / 15167 | +11782 | +11782 |
| cache_read_input_tokens | 165462 / 165462 | 210846 / 210846 | -45384 | -45384 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
