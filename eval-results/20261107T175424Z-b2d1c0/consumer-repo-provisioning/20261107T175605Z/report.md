# Eval report: consumer-repo-provisioning

- Timestamp: 20261107T175605Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T175424Z-b2d1c0; started 2026-11-07T17:56:05Z, ended 2026-11-07T18:02:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.58 to 0.58, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.19 over 6 call(s); agent $2.19, judge $0.00, guard $0.00; last agent call $0.36

## Fixture: consumer-repo-provisioning (n=3)

- Prompt: The scheduled cms-automerge-nudge has failed since yesterday. What is missing, and exactly what do I set? Diagnose only; leave files and GitHub state alone. Finish with labeled lines or table rows for Missing secret, Token type, Resource owner, Repository access, Other permissions, and Secret listing. Include a permission/access table with one row for each permission needed. Keep each answer value unambiguous; put your reasoning in a separate paragraph.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9.3/19 | skipped (objective-decided) | 0.3227 / 0.9680 |
| without_skill | 3 | 0 | 8.7/19 | skipped (objective-decided) | 0.4058 / 1.2174 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3227 / 0.2969 | 0.4058 / 0.4241 | -0.0831 | -0.1272 |
| num_turns | 6.7 / 7 | 10.7 / 11 | -4 | -4 |
| duration_ms | 36073 / 36460 | 83387 / 76075 | -47314 | -39615 |
| input_tokens | 11.3 / 12 | 20 / 20 | -8.7 | -8 |
| output_tokens | 2660.7 / 2630 | 4829 / 4636 | -2168.3 | -2006 |
| cache_creation_input_tokens | 28947.7 / 25305 | 28151 / 27858 | +796.7 | -2553 |
| cache_read_input_tokens | 189145.3 / 199505 | 419598.3 / 433916 | -230453 | -234411 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| missing-actions-secret | 0/3 | 0/3 |
| fine-grained-pat | 0/3 | 3/3 |
| consumer-owner | 1/3 | 1/3 |
| single-consumer-repo | 0/3 | 0/3 |
| contents-write | 3/3 | 3/3 |
| pull-requests-write | 3/3 | 3/3 |
| issues-write | 3/3 | 0/3 |
| actions-write | 3/3 | 0/3 |
| commit-statuses-read | 3/3 | 3/3 |
| metadata-read | 2/3 | 3/3 |
| no-extra-grants | 0/3 | 0/3 |
| secret-listing-unavailable | 0/3 | 0/3 |
| run-metadata-read | 0/3 | 0/3 |
| failing-log-read | 0/3 | 0/3 |
| variables-read | 0/3 | 0/3 |
| secrets-read | 1/3 | 1/3 |
| no-write-attempted | 3/3 | 3/3 |
| workflows-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
