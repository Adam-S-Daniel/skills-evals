# Eval report: skills-doctor

- Timestamp: 20261112T001202Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T001024Z-868c67; started 2026-11-12T00:12:02Z, ended 2026-11-12T00:14:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.73 over 4 call(s); agent $0.60, judge $0.12, guard $0.00; last agent call $0.22

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.3782 / 0.3782 |
| without_skill | 1 | 0 | 5/6 | 9.5 (9.5 to 9.5, 1 judged) | 0.2223 / 0.2223 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3782 / 0.3782 | 0.2223 / 0.2223 | +0.1559 | +0.1559 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 56615 / 56615 | 57594 / 57594 | -979 | -979 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 5405 / 5405 | 4705 / 4705 | +700 | +700 |
| cache_creation_input_tokens | 42317 / 42317 | 17110 / 17110 | +25207 | +25207 |
| cache_read_input_tokens | 292169 / 292169 | 212938 / 212938 | +79231 | +79231 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
