# Eval report: consumer-repo-provisioning

- Timestamp: 20261107T131841Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T131329Z-f71e9a; started 2026-11-07T13:18:41Z, ended 2026-11-07T13:21:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.66 over 6 call(s); agent $0.54, judge $0.12, guard $0.00; last agent call $0.11

## Fixture: consumer-repo-provisioning (n=3)

- Prompt: The scheduled cms-automerge-nudge has failed since yesterday. What is missing, and exactly what do I set? Diagnose only; leave files and GitHub state alone. Finish with labeled lines or table rows for Missing secret, Token type, Resource owner, Repository access, Other permissions, and Secret listing. Include a permission/access table with one row for each permission needed. Keep each answer value unambiguous; put your reasoning in a separate paragraph.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 7.3/19 | 5.3 (5.2 to 5.5, 3 judged) | 0.1802 / 0.5405 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1802 / 0.2091 |
| num_turns | 11 / 10 |
| duration_ms | 52927 / 56075 |
| input_tokens | 14 / 14 |
| output_tokens | 3747.7 / 3574 |
| cache_creation_input_tokens | 28451.7 / 34816 |
| cache_read_input_tokens | 288704.7 / 303912 |
| tool_errors | 1 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| missing-actions-secret | 0/3 |
| fine-grained-pat | 2/3 |
| consumer-owner | 1/3 |
| single-consumer-repo | 0/3 |
| contents-write | 0/3 |
| pull-requests-write | 3/3 |
| issues-write | 0/3 |
| actions-write | 0/3 |
| commit-statuses-read | 2/3 |
| metadata-read | 3/3 |
| no-extra-grants | 0/3 |
| secret-listing-unavailable | 0/3 |
| run-metadata-read | 0/3 |
| failing-log-read | 0/3 |
| variables-read | 0/3 |
| secrets-read | 2/3 |
| no-write-attempted | 3/3 |
| workflows-unchanged | 3/3 |
| instrument-unchanged | 3/3 |
