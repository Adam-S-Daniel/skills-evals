# Eval report: skills-doctor

- Timestamp: 20261112T021652Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T021501Z-790140; started 2026-11-12T02:16:52Z, ended 2026-11-12T02:19:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.39 to 0.39, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.81 over 4 call(s); agent $0.66, judge $0.15, guard $0.00; last agent call $0.20

## Fixture: laptop-double-delivery (n=1)

- Prompt: The capture in this directory is from my laptop. The session-start line said OK and every skill I locked seems to be there, so I think skill delivery is fine. Check that, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.4675 / 0.4675 |
| without_skill | 1 | 0 | 5/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.1956 / 0.1956 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4675 / 0.4675 | 0.1956 / 0.1956 | +0.2719 | +0.2719 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 60789 / 60789 | 54915 / 54915 | +5874 | +5874 |
| input_tokens | 18 / 18 | 10 / 10 | +8 | +8 |
| output_tokens | 5669 / 5669 | 4068 / 4068 | +1601 | +1601 |
| cache_creation_input_tokens | 57751 / 57751 | 15866 / 15866 | +41885 | +41885 |
| cache_read_input_tokens | 326445 / 326445 | 174249 / 174249 | +152196 | +152196 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-degraded | 1/1 | 1/1 |
| the-doubled-skills-are-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-deleted-by-hand | 0/1 | 0/1 |
