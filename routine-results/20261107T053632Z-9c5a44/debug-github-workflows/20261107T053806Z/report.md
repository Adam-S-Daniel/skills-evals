# Eval report: debug-github-workflows

- Timestamp: 20261107T053806Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T053632Z-9c5a44; started 2026-11-07T05:38:06Z, ended 2026-11-07T05:39:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.25 over 2 call(s); agent $0.25, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1465 / 0.1465 |
| without_skill | 1 | 0 | 6/8 | skipped (objective-decided) | 0.1039 / 0.1039 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1465 / 0.1465 | 0.1039 / 0.1039 | +0.0426 | +0.0426 |
| num_turns | 9 / 9 | 9 / 9 | 0 | 0 |
| duration_ms | 37660 / 37660 | 25014 / 25014 | +12646 | +12646 |
| input_tokens | 18 / 18 | 16 / 16 | +2 | +2 |
| output_tokens | 1946 / 1946 | 1903 / 1903 | +43 | +43 |
| cache_creation_input_tokens | 24137 / 24137 | 14289 / 14289 | +9848 | +9848 |
| cache_read_input_tokens | 304848 / 304848 | 277302 / 277302 | +27546 | +27546 |
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
