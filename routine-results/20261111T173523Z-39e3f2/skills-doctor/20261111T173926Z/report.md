# Eval report: skills-doctor

- Timestamp: 20261111T173926Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T173523Z-39e3f2; started 2026-11-11T17:39:26Z, ended 2026-11-11T17:40:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 4 call(s); agent $0.20, judge $0.07, guard $0.00; last agent call $0.08

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.5 (8.5 to 8.5, 1 judged) | 0.1219 / 0.1219 |
| without_skill | 1 | 0 | 5/6 | 9.0 (9.0 to 9.0, 1 judged) | 0.0830 / 0.0830 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1219 / 0.1219 | 0.0830 / 0.0830 | +0.0389 | +0.0389 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 32543 / 32543 | 27775 / 27775 | +4768 | +4768 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 3708 / 3708 | 2917 / 2917 | +791 | +791 |
| cache_creation_input_tokens | 27296 / 27296 | 14662 / 14662 | +12634 | +12634 |
| cache_read_input_tokens | 165140 / 165140 | 171282 / 171282 | -6142 | -6142 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
