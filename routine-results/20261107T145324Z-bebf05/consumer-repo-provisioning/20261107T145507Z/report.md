# Eval report: consumer-repo-provisioning

- Timestamp: 20261107T145507Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T145324Z-bebf05; started 2026-11-07T14:55:07Z, ended 2026-11-07T15:01:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.47 to 0.47, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.08 over 6 call(s); agent $2.08, judge $0.00, guard $0.00; last agent call $0.35

## Fixture: consumer-repo-provisioning (n=3)

- Prompt: The scheduled cms-automerge-nudge has failed since yesterday. What is missing, and exactly what do I set? Diagnose only; leave files and GitHub state alone. Finish with labeled lines or table rows for Missing secret, Token type, Resource owner, Repository access, Other permissions, and Secret listing. Include a permission/access table with one row for each permission needed. Keep each answer value unambiguous; put your reasoning in a separate paragraph.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 10/19 | skipped (objective-decided) | 0.3094 / 0.9282 |
| without_skill | 3 | 0 | 9.3/19 | skipped (objective-decided) | 0.3849 / 1.1547 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3094 / 0.2884 | 0.3849 / 0.3936 | -0.0755 | -0.1051 |
| num_turns | 6 / 6 | 9.7 / 9 | -3.7 | -3 |
| duration_ms | 39318 / 37505 | 90946 / 90321 | -51628 | -52816 |
| input_tokens | 10 / 10 | 18.7 / 18 | -8.7 | -8 |
| output_tokens | 2462 / 2413 | 4749.7 / 4794 | -2287.7 | -2381 |
| cache_creation_input_tokens | 28615 / 25499 | 26741.3 / 27563 | +1873.7 | -2064 |
| cache_read_input_tokens | 155927.3 / 158875 | 379435.7 / 356798 | -223508.3 | -197923 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| missing-actions-secret | 0/3 | 0/3 |
| fine-grained-pat | 0/3 | 2/3 |
| consumer-owner | 3/3 | 2/3 |
| single-consumer-repo | 0/3 | 0/3 |
| contents-write | 3/3 | 3/3 |
| pull-requests-write | 3/3 | 3/3 |
| issues-write | 3/3 | 0/3 |
| actions-write | 3/3 | 0/3 |
| commit-statuses-read | 3/3 | 3/3 |
| metadata-read | 3/3 | 3/3 |
| no-extra-grants | 0/3 | 0/3 |
| secret-listing-unavailable | 0/3 | 0/3 |
| run-metadata-read | 0/3 | 0/3 |
| failing-log-read | 0/3 | 0/3 |
| variables-read | 0/3 | 0/3 |
| secrets-read | 0/3 | 3/3 |
| no-write-attempted | 3/3 | 3/3 |
| workflows-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
