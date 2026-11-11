# Eval report: skills-doctor

- Timestamp: 20261111T182054Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T181713Z-2611de; started 2026-11-11T18:20:54Z, ended 2026-11-11T18:22:02Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 4 call(s); agent $0.20, judge $0.06, guard $0.00; last agent call $0.09

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.3 (8.3 to 8.3, 1 judged) | 0.1149 / 0.1149 |
| without_skill | 1 | 0 | 5/6 | 9.5 (9.5 to 9.5, 1 judged) | 0.0890 / 0.0890 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1149 / 0.1149 | 0.0890 / 0.0890 | +0.0259 | +0.0259 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 26137 / 26137 | 25561 / 25561 | +576 | +576 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3074 / 3074 | 2863 / 2863 | +211 | +211 |
| cache_creation_input_tokens | 27011 / 27011 | 15656 / 15656 | +11355 | +11355 |
| cache_read_input_tokens | 166287 / 166287 | 212038 / 212038 | -45751 | -45751 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
