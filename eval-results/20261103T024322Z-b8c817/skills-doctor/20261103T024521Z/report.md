# Eval report: skills-doctor

- Timestamp: 20261103T024521Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T024322Z-b8c817; started 2026-11-03T02:45:21Z, ended 2026-11-03T02:47:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.3 to 0.3, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 4 call(s); agent $0.27, judge $0.15, guard $0.00; last agent call $0.11

## Fixture: ssh-remote-is-durable (n=1)

- Prompt: The capture in this directory is from a VM I SSH into, where I think the skills bootstrap hook has stopped working. Work out whether skill delivery to that session is actually broken, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.1596 / 0.1596 |
| without_skill | 1 | 0 | 6/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.1132 / 0.1132 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1596 / 0.1596 | 0.1132 / 0.1132 | +0.0463 | +0.0463 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 45918 / 45918 | 40100 / 40100 | +5818 | +5818 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 3794 / 3794 | 3297 / 3297 | +497 | +497 |
| cache_creation_input_tokens | 26358 / 26358 | 15749 / 15749 | +10609 | +10609 |
| cache_read_input_tokens | 161768 / 161768 | 172365 / 172365 | -10597 | -10597 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-ok | 1/1 | 1/1 |
| the-delivering-channel-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-installed-by-hand | 1/1 | 1/1 |
