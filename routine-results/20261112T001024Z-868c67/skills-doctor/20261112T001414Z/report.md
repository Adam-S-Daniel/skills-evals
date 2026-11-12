# Eval report: skills-doctor

- Timestamp: 20261112T001414Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T001024Z-868c67; started 2026-11-12T00:14:14Z, ended 2026-11-12T00:15:26Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 4 call(s); agent $0.20, judge $0.06, guard $0.00; last agent call $0.08

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 9.5 (9.5 to 9.5, 1 judged) | 0.1151 / 0.1151 |
| without_skill | 1 | 0 | 5/6 | 9.0 (9.0 to 9.0, 1 judged) | 0.0828 / 0.0828 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1151 / 0.1151 | 0.0828 / 0.0828 | +0.0323 | +0.0323 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 29234 / 29234 | 26974 / 26974 | +2260 | +2260 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 2909 / 2909 | 2863 / 2863 | +46 | +46 |
| cache_creation_input_tokens | 26334 / 26334 | 14790 / 14790 | +11544 | +11544 |
| cache_read_input_tokens | 201494 / 201494 | 171705 / 171705 | +29789 | +29789 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
