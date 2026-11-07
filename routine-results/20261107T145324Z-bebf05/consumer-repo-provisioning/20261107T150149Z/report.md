# Eval report: consumer-repo-provisioning

- Timestamp: 20261107T150149Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T145324Z-bebf05; started 2026-11-07T15:01:49Z, ended 2026-11-07T15:07:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.47 to 0.48, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.95 over 6 call(s); agent $0.95, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: consumer-repo-provisioning (n=3)

- Prompt: The scheduled cms-automerge-nudge has failed since yesterday. What is missing, and exactly what do I set? Diagnose only; leave files and GitHub state alone. Finish with labeled lines or table rows for Missing secret, Token type, Resource owner, Repository access, Other permissions, and Secret listing. Include a permission/access table with one row for each permission needed. Keep each answer value unambiguous; put your reasoning in a separate paragraph.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/19 | skipped (objective-decided) | 0.1613 / 0.4839 |
| without_skill | 3 | 0 | 7/19 | skipped (objective-decided) | 0.1546 / 0.4638 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1613 / 0.1505 | 0.1546 / 0.1540 | +0.0067 | -0.0035 |
| num_turns | 7.7 / 8 | 12 / 12 | -4.3 | -4 |
| duration_ms | 40483 / 32990 | 64859 / 60734 | -24376 | -27744 |
| input_tokens | 13.3 / 14 | 18 / 18 | -4.7 | -4 |
| output_tokens | 2677.3 / 2734 | 3720.7 / 3732 | -1043.3 | -998 |
| cache_creation_input_tokens | 27759.3 / 24395 | 20718.3 / 20599 | +7041 | +3796 |
| cache_read_input_tokens | 234756.3 / 255039 | 344976.3 / 342437 | -110220 | -87398 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| missing-actions-secret | 0/3 | 0/3 |
| fine-grained-pat | 0/3 | 1/3 |
| consumer-owner | 0/3 | 0/3 |
| single-consumer-repo | 0/3 | 0/3 |
| contents-write | 3/3 | 3/3 |
| pull-requests-write | 3/3 | 3/3 |
| issues-write | 3/3 | 0/3 |
| actions-write | 3/3 | 0/3 |
| commit-statuses-read | 3/3 | 3/3 |
| metadata-read | 3/3 | 2/3 |
| no-extra-grants | 0/3 | 0/3 |
| secret-listing-unavailable | 0/3 | 0/3 |
| run-metadata-read | 2/3 | 0/3 |
| failing-log-read | 1/3 | 0/3 |
| variables-read | 0/3 | 0/3 |
| secrets-read | 0/3 | 0/3 |
| no-write-attempted | 3/3 | 3/3 |
| workflows-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
