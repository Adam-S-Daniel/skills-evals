# Eval report: skills-doctor

- Timestamp: 20261111T165626Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T165446Z-aa8d61; started 2026-11-11T16:56:26Z, ended 2026-11-11T16:58:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.36, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.66 over 4 call(s); agent $0.53, judge $0.13, guard $0.00; last agent call $0.18

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.3477 / 0.3477 |
| without_skill | 1 | 0 | 5/6 | 9.5 (9.5 to 9.5, 1 judged) | 0.1842 / 0.1842 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3477 / 0.3477 | 0.1842 / 0.1842 | +0.1635 | +0.1635 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 53176 / 53176 | 37588 / 37588 | +15588 | +15588 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 4933 / 4933 | 3608 / 3608 | +1325 | +1325 |
| cache_creation_input_tokens | 40738 / 40738 | 15473 / 15473 | +25265 | +25265 |
| cache_read_input_tokens | 226658 / 226658 | 173210 / 173210 | +53448 | +53448 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
