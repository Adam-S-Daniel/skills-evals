# Eval report: consumer-repo-provisioning

- Timestamp: 20261107T104558Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T103832Z-1d05f2; started 2026-11-07T10:45:58Z, ended 2026-11-07T10:49:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.39 to 0.4, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.60 over 4 call(s); agent $0.60, judge $0.00, guard $0.00; last agent call $0.16

## Fixture: consumer-repo-provisioning (n=2)

- Prompt: The scheduled cms-automerge-nudge has failed since yesterday. What is missing, and exactly what do I set? Diagnose only; leave files and GitHub state alone. Finish with labeled lines or table rows for Missing secret, Token type, Resource owner, Repository access, Other permissions, and Secret listing. Include a permission/access table with one row for each permission needed. Keep each answer value unambiguous; put your reasoning in a separate paragraph.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 9/19 | skipped (objective-decided) | 0.1511 / 0.3022 |
| without_skill | 2 | 0 | 4.5/19 | skipped (objective-decided) | 0.1479 / 0.2959 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1511 / 0.1511 | 0.1479 / 0.1479 | +0.0031 | +0.0031 |
| num_turns | 6 / 6 | 10.5 / 10.5 | -4.5 | -4.5 |
| duration_ms | 25686.5 / 25686.5 | 67701.5 / 67701.5 | -42015 | -42015 |
| input_tokens | 10 / 10 | 18 / 18 | -8 | -8 |
| output_tokens | 2155 / 2155 | 3637.5 / 3637.5 | -1482.5 | -1482.5 |
| cache_creation_input_tokens | 28527 / 28527 | 19227.5 / 19227.5 | +9299.5 | +9299.5 |
| cache_read_input_tokens | 154051 / 154051 | 346154.5 / 346154.5 | -192103.5 | -192103.5 |
| tool_errors | 0 / 0 | 1.5 / 1.5 | -1.5 | -1.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| missing-actions-secret | 0/2 | 0/2 |
| fine-grained-pat | 0/2 | 0/2 |
| consumer-owner | 0/2 | 0/2 |
| single-consumer-repo | 0/2 | 0/2 |
| contents-write | 2/2 | 1/2 |
| pull-requests-write | 2/2 | 1/2 |
| issues-write | 2/2 | 0/2 |
| actions-write | 2/2 | 0/2 |
| commit-statuses-read | 2/2 | 1/2 |
| metadata-read | 2/2 | 0/2 |
| no-extra-grants | 0/2 | 0/2 |
| secret-listing-unavailable | 0/2 | 0/2 |
| run-metadata-read | 0/2 | 0/2 |
| failing-log-read | 0/2 | 0/2 |
| variables-read | 0/2 | 0/2 |
| secrets-read | 0/2 | 0/2 |
| no-write-attempted | 2/2 | 2/2 |
| workflows-unchanged | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
