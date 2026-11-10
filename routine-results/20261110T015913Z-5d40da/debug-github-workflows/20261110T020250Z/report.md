# Eval report: debug-github-workflows

- Timestamp: 20261110T020250Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T015913Z-5d40da; started 2026-11-10T02:02:50Z, ended 2026-11-10T02:04:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.14 to 0.14, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 2 call(s); agent $0.24, judge $0.00, guard $0.00; last agent call $0.09

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped: the version with the skill passed more checks (8 of 8 vs 6 of 8) | 0.1519 / 0.1519 |
| without_skill | 1 | 0 | 6/8 | skipped: the version with the skill passed more checks (8 of 8 vs 6 of 8) | 0.0850 / 0.0850 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1519 / 0.1519 | 0.0850 / 0.0850 | +0.0669 | +0.0669 |
| num_turns | 10 / 10 | 9 / 9 | +1 | +1 |
| duration_ms | 37868 / 37868 | 40333 / 40333 | -2465 | -2465 |
| input_tokens | 18 / 18 | 16 / 16 | +2 | +2 |
| output_tokens | 2175 / 2175 | 2026 / 2026 | +149 | +149 |
| cache_creation_input_tokens | 40207 / 40207 | 14649 / 14649 | +25558 | +25558 |
| cache_read_input_tokens | 296080 / 296080 | 281163 / 281163 | +14917 | +14917 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/1 | 0/1 |
| secret-names-listed | 1/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
