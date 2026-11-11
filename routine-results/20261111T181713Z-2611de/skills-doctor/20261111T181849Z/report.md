# Eval report: skills-doctor

- Timestamp: 20261111T181849Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T181713Z-2611de; started 2026-11-11T18:18:49Z, ended 2026-11-11T18:20:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.72 over 4 call(s); agent $0.60, judge $0.12, guard $0.00; last agent call $0.19

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.4132 / 0.4132 |
| without_skill | 1 | 0 | 5/6 | 9.5 (9.5 to 9.5, 1 judged) | 0.1869 / 0.1869 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4132 / 0.4132 | 0.1869 / 0.1869 | +0.2263 | +0.2263 |
| num_turns | 10 / 10 | 4 / 4 | +6 | +6 |
| duration_ms | 64514 / 64514 | 42598 / 42598 | +21916 | +21916 |
| input_tokens | 20 / 20 | 8 / 8 | +12 | +12 |
| output_tokens | 5880 / 5880 | 4163 / 4163 | +1717 | +1717 |
| cache_creation_input_tokens | 43093 / 43093 | 15355 / 15355 | +27738 | +27738 |
| cache_read_input_tokens | 400362 / 400362 | 134177 / 134177 | +266185 | +266185 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
