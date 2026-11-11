# Eval report: skills-doctor

- Timestamp: 20261111T225031Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T224835Z-74d4cc; started 2026-11-11T22:50:31Z, ended 2026-11-11T22:52:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 4 call(s); agent $0.56, judge $0.14, guard $0.00; last agent call $0.21

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.3514 / 0.3514 |
| without_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.2075 / 0.2075 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3514 / 0.3514 | 0.2075 / 0.2075 | +0.1439 | +0.1439 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 53630 / 53630 | 51654 / 51654 | +1976 | +1976 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 4973 / 4973 | 4240 / 4240 | +733 | +733 |
| cache_creation_input_tokens | 41259 / 41259 | 15989 / 15989 | +25270 | +25270 |
| cache_read_input_tokens | 228080 / 228080 | 213578 / 213578 | +14502 | +14502 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
