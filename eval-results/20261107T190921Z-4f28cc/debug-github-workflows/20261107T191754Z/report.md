# Eval report: debug-github-workflows

- Timestamp: 20261107T191754Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T190921Z-4f28cc; started 2026-11-07T19:17:54Z, ended 2026-11-07T19:21:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.63 to 0.64, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.71 over 6 call(s); agent $0.71, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: secret-name (n=3)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.7/8 | skipped (objective-decided) | 0.1196 / 0.3589 |
| without_skill | 3 | 0 | 6/8 | skipped (objective-decided) | 0.1157 / 0.3471 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1196 / 0.1086 | 0.1157 / 0.1158 | +0.0039 | -0.0071 |
| num_turns | 8.7 / 9 | 10.3 / 10 | -1.7 | -1 |
| duration_ms | 30761.3 / 29191 | 35007 / 34494 | -4245.7 | -5303 |
| input_tokens | 16 / 16 | 18.7 / 18 | -2.7 | -2 |
| output_tokens | 1902.7 / 1857 | 2020.7 / 2031 | -118 | -174 |
| cache_creation_input_tokens | 18197.7 / 15117 | 15565.3 / 15814 | +2632.3 | -697 |
| cache_read_input_tokens | 277675 / 280114 | 331813.3 / 321304 | -54138.3 | -41190 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/3 | 0/3 |
| secret-names-listed | 1/3 | 0/3 |
| workflow-reads-the-existing-secret | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| permissions-stay-read-only | 3/3 | 3/3 |
| reply-names-both-secrets | 3/3 | 3/3 |
| everything-else-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
