# Eval report: skills-doctor

- Timestamp: 20261103T012503Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T012234Z-dd66ce; started 2026-11-03T01:25:03Z, ended 2026-11-03T01:25:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.28 to 0.28, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 4 call(s); agent $0.22, judge $0.14, guard $0.00; last agent call $0.09

## Fixture: one-row-rejects-the-lock (n=1)

- Prompt: The capture in this directory is from a cloud session that loaded none of the skills its repo locks. Work out why, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Skills affected:` in the form `<n> of <total>`, counting the locked skills this cause keeps out of the session, and a line starting `Cause:` that names the lock entry responsible, if one is. Change nothing else.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | 9.5 (9.5 to 9.5, 1 judged) | 0.1309 / 0.1309 |
| without_skill | 1 | 0 | 5/5 | 9.5 (9.5 to 9.5, 1 judged) | 0.0861 / 0.0861 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1309 / 0.1309 | 0.0861 / 0.0861 | +0.0448 | +0.0448 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 19390 / 19390 | 18888 / 18888 | +502 | +502 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1888 / 1888 | 1747 / 1747 | +141 | +141 |
| cache_creation_input_tokens | 24014 / 24014 | 12936 / 12936 | +11078 | +11078 |
| cache_read_input_tokens | 159759 / 159759 | 169139 / 169139 | -9380 | -9380 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| every-locked-skill-is-affected | 1/1 | 1/1 |
| the-refused-row-is-named | 1/1 | 1/1 |
| the-case-is-the-defect | 1/1 | 1/1 |
| the-lock-was-not-repaired | 1/1 | 1/1 |
