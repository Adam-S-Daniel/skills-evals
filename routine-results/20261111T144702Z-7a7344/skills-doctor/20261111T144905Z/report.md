# Eval report: skills-doctor

- Timestamp: 20261111T144905Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T144702Z-7a7344; started 2026-11-11T14:49:05Z, ended 2026-11-11T14:51:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 4 call(s); agent $0.55, judge $0.14, guard $0.00; last agent call $0.19

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.3552 / 0.3552 |
| without_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.1930 / 0.1930 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3552 / 0.3552 | 0.1930 / 0.1930 | +0.1622 | +0.1622 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 53874 / 53874 | 51963 / 51963 | +1911 | +1911 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 4792 / 4792 | 3869 / 3869 | +923 | +923 |
| cache_creation_input_tokens | 41567 / 41567 | 16111 / 16111 | +25456 | +25456 |
| cache_read_input_tokens | 257407 / 257407 | 175041 / 175041 | +82366 | +82366 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
