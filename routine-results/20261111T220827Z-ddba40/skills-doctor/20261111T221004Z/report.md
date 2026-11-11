# Eval report: skills-doctor

- Timestamp: 20261111T221004Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T220827Z-ddba40; started 2026-11-11T22:10:04Z, ended 2026-11-11T22:12:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 4 call(s); agent $0.58, judge $0.12, guard $0.00; last agent call $0.18

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.3989 / 0.3989 |
| without_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.1840 / 0.1840 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3989 / 0.3989 | 0.1840 / 0.1840 | +0.2149 | +0.2149 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 64544 / 64544 | 37836 / 37836 | +26708 | +26708 |
| input_tokens | 18 / 18 | 10 / 10 | +8 | +8 |
| output_tokens | 5814 / 5814 | 3568 / 3568 | +2246 | +2246 |
| cache_creation_input_tokens | 42969 / 42969 | 15560 / 15560 | +27409 | +27409 |
| cache_read_input_tokens | 338469 / 338469 | 173764 / 173764 | +164705 | +164705 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
