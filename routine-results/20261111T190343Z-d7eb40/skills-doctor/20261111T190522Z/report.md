# Eval report: skills-doctor

- Timestamp: 20261111T190522Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T190343Z-d7eb40; started 2026-11-11T19:05:22Z, ended 2026-11-11T19:07:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.75 over 4 call(s); agent $0.61, judge $0.14, guard $0.00; last agent call $0.19

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.4112 / 0.4112 |
| without_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.1945 / 0.1945 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4112 / 0.4112 | 0.1945 / 0.1945 | +0.2167 | +0.2167 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 49986 / 49986 | 50571 / 50571 | -585 | -585 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 4668 / 4668 | 4036 / 4036 | +632 | +632 |
| cache_creation_input_tokens | 56061 / 56061 | 15778 / 15778 | +40283 | +40283 |
| cache_read_input_tokens | 187323 / 187323 | 174313 / 174313 | +13010 | +13010 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
