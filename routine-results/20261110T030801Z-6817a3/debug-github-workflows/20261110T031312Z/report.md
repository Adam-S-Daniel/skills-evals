# Eval report: debug-github-workflows

- Timestamp: 20261110T031312Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T030801Z-6817a3; started 2026-11-10T03:13:12Z, ended 2026-11-10T03:14:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.15 to 0.15, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.22 over 2 call(s); agent $0.22, judge $0.00, guard $0.00; last agent call $0.07

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped: the version with the skill passed more checks (8 of 8 vs 6 of 8) | 0.1427 / 0.1427 |
| without_skill | 1 | 0 | 6/8 | skipped: the version with the skill passed more checks (8 of 8 vs 6 of 8) | 0.0748 / 0.0748 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1427 / 0.1427 | 0.0748 / 0.0748 | +0.0679 | +0.0679 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 45066 / 45066 | 29720 / 29720 | +15346 | +15346 |
| input_tokens | 16 / 16 | 14 / 14 | +2 | +2 |
| output_tokens | 1932 / 1932 | 1561 / 1561 | +371 | +371 |
| cache_creation_input_tokens | 39065 / 39065 | 13900 / 13900 | +25165 | +25165 |
| cache_read_input_tokens | 256911 / 256911 | 244054 / 244054 | +12857 | +12857 |
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
