# Eval report: skills-doctor

- Timestamp: 20261103T095316Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T095129Z-a28e1a; started 2026-11-03T09:53:16Z, ended 2026-11-03T09:55:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.38, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.90 over 4 call(s); agent $0.55, judge $0.35, guard $0.00; last agent call $0.20

## Fixture: one-row-rejects-the-lock (n=1)

- Prompt: The capture in this directory is from a cloud session that loaded none of the skills its repo locks. Work out why, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Skills affected:` in the form `<n> of <total>`, counting the locked skills this cause keeps out of the session, and a line starting `Cause:` that names the lock entry responsible, if one is. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | 10.0 (10.0 to 10.0, 1 judged) | 0.3506 / 0.3506 |
| without_skill | 1 | 0 | 5/5 | 10.0 (10.0 to 10.0, 1 judged) | 0.2008 / 0.2008 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3506 / 0.3506 | 0.2008 / 0.2008 | +0.1498 | +0.1498 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 61801 / 61801 | 54155 / 54155 | +7646 | +7646 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 3384 / 3384 | 2580 / 2580 | +804 | +804 |
| cache_creation_input_tokens | 28402 / 28402 | 13513 / 13513 | +14889 | +14889 |
| cache_read_input_tokens | 278220 / 278220 | 205117 / 205117 | +73103 | +73103 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| every-locked-skill-is-affected | 1/1 | 1/1 |
| the-refused-row-is-named | 1/1 | 1/1 |
| the-case-is-the-defect | 1/1 | 1/1 |
| the-lock-was-not-repaired | 1/1 | 1/1 |
