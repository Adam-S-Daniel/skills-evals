# Eval report: skills-doctor

- Timestamp: 20261109T201153Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T201010Z-710556; started 2026-11-09T20:11:53Z, ended 2026-11-09T20:13:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.08, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 6 call(s); agent $0.32, judge $0.08, guard $0.00; last agent call $0.08

## Fixture: laptop-double-delivery (n=3)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4.3/6 | 7.7 (6.0 to 9.5, 3 judged) | 0.1061 / 0.3182 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1061 / 0.0839 |
| num_turns | 6 / 6 |
| duration_ms | 28053 / 28012 |
| input_tokens | 12 / 12 |
| output_tokens | 2730.7 / 2758 |
| cache_creation_input_tokens | 23017.3 / 13643 |
| cache_read_input_tokens | 212064.3 / 220829 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| findings-written | 3/3 |
| the-surface-is-durable | 3/3 |
| delivery-is-degraded | 1/3 |
| the-doubled-skills-are-named | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 |
| no-skill-was-deleted-by-hand | 0/3 |
