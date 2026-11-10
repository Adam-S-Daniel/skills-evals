# Eval report: skills-doctor

- Timestamp: 20261110T043508Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T043342Z-951d2d; started 2026-11-10T04:35:08Z, ended 2026-11-10T04:37:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.71 over 6 call(s); agent $0.54, judge $0.17, guard $0.00; last agent call $0.18

## Fixture: laptop-double-delivery (n=3)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5/6 | 9.7 (9.5 to 10.0, 3 judged) | 0.1801 / 0.5403 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1801 / 0.1791 |
| num_turns | 5.3 / 5 |
| duration_ms | 41142.3 / 42305 |
| input_tokens | 10.7 / 10 |
| output_tokens | 3651 / 3793 |
| cache_creation_input_tokens | 13559 / 13649 |
| cache_read_input_tokens | 196128.3 / 182100 |
| tool_errors | 0.3 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| findings-written | 3/3 |
| the-surface-is-durable | 3/3 |
| delivery-is-degraded | 3/3 |
| the-doubled-skills-are-named | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 |
| no-skill-was-deleted-by-hand | 0/3 |
