# Eval report: consumer-repo-provisioning

- Timestamp: 20261107T180212Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T175424Z-b2d1c0; started 2026-11-07T18:02:12Z, ended 2026-11-07T18:06:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.58 to 0.59, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.89 over 6 call(s); agent $0.89, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: consumer-repo-provisioning (n=3)

- Prompt: The scheduled cms-automerge-nudge has failed since yesterday. What is missing, and exactly what do I set? Diagnose only; leave files and GitHub state alone. Finish with labeled lines or table rows for Missing secret, Token type, Resource owner, Repository access, Other permissions, and Secret listing. Include a permission/access table with one row for each permission needed. Keep each answer value unambiguous; put your reasoning in a separate paragraph.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/19 | skipped (objective-decided) | 0.1455 / 0.4364 |
| without_skill | 3 | 0 | 8/19 | skipped (objective-decided) | 0.1507 / 0.4520 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1455 / 0.1395 | 0.1507 / 0.1593 | -0.0052 | -0.0198 |
| num_turns | 6 / 6 | 10 / 9 | -4 | -3 |
| duration_ms | 23838.7 / 24675 | 52606.7 / 55749 | -28768 | -31074 |
| input_tokens | 10.7 / 10 | 17.3 / 16 | -6.7 | -6 |
| output_tokens | 2221.7 / 2330 | 3164 / 3074 | -942.3 | -744 |
| cache_creation_input_tokens | 26569.7 / 23696 | 21914.3 / 22126 | +4655.3 | +1570 |
| cache_read_input_tokens | 169582.7 / 157264 | 313319.3 / 297400 | -143736.7 | -140136 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| missing-actions-secret | 0/3 | 0/3 |
| fine-grained-pat | 0/3 | 2/3 |
| consumer-owner | 0/3 | 1/3 |
| single-consumer-repo | 0/3 | 0/3 |
| contents-write | 3/3 | 3/3 |
| pull-requests-write | 3/3 | 3/3 |
| issues-write | 3/3 | 0/3 |
| actions-write | 3/3 | 0/3 |
| commit-statuses-read | 3/3 | 3/3 |
| metadata-read | 3/3 | 2/3 |
| no-extra-grants | 0/3 | 0/3 |
| secret-listing-unavailable | 0/3 | 0/3 |
| run-metadata-read | 0/3 | 0/3 |
| failing-log-read | 0/3 | 0/3 |
| variables-read | 0/3 | 0/3 |
| secrets-read | 0/3 | 1/3 |
| no-write-attempted | 3/3 | 3/3 |
| workflows-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
