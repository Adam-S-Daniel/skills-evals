# Eval report: skills-doctor

- Timestamp: 20261111T132120Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T131950Z-5a526e; started 2026-11-11T13:21:20Z, ended 2026-11-11T13:22:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.63 over 4 call(s); agent $0.52, judge $0.11, guard $0.00; last agent call $0.18

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.3375 / 0.3375 |
| without_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.1801 / 0.1801 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3375 / 0.3375 | 0.1801 / 0.1801 | +0.1574 | +0.1574 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 47146 / 47146 | 35256 / 35256 | +11890 | +11890 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 4442 / 4442 | 3495 / 3495 | +947 | +947 |
| cache_creation_input_tokens | 40623 / 40623 | 15090 / 15090 | +25533 | +25533 |
| cache_read_input_tokens | 227544 / 227544 | 173602 / 173602 | +53942 | +53942 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
