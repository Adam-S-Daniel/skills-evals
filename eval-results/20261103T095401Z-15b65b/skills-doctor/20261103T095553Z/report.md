# Eval report: skills-doctor

- Timestamp: 20261103T095553Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T095401Z-15b65b; started 2026-11-03T09:55:53Z, ended 2026-11-03T09:57:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.38, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.07 over 4 call(s); agent $0.67, judge $0.40, guard $0.00; last agent call $0.23

## Fixture: ssh-remote-is-durable (n=1)

- Prompt: The capture in this directory is from a VM I SSH into, where I think the skills bootstrap hook has stopped working. Work out whether skill delivery to that session is actually broken, and write your findings to FINDINGS.md at the top of this directory. Include a line `Surface: ephemeral` or `Surface: durable`, and a line `Verdict: OK` or `Verdict: DEGRADED`, for skill delivery as a whole. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.4394 / 0.4394 |
| without_skill | 1 | 0 | 6/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.2277 / 0.2277 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4394 / 0.4394 | 0.2277 / 0.2277 | +0.2117 | +0.2117 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 45216 / 45216 | 62059 / 62059 | -16843 | -16843 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 4361 / 4361 | 3548 / 3548 | +813 | +813 |
| cache_creation_input_tokens | 39012 / 39012 | 15329 / 15329 | +23683 | +23683 |
| cache_read_input_tokens | 200139 / 200139 | 170396 / 170396 | +29743 | +29743 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-surface-is-durable | 1/1 | 1/1 |
| delivery-is-ok | 1/1 | 1/1 |
| the-delivering-channel-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-installed-by-hand | 1/1 | 1/1 |
