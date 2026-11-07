# Eval report: consumer-repo-provisioning

- Timestamp: 20261107T104004Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T103832Z-1d05f2; started 2026-11-07T10:40:04Z, ended 2026-11-07T10:45:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.39 to 0.39, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.98 over 8 call(s); agent $1.46, judge $0.52, guard $0.00; last agent call $0.32

## Fixture: consumer-repo-provisioning (n=2)

- Prompt: The scheduled cms-automerge-nudge has failed since yesterday. What is missing, and exactly what do I set? Diagnose only; leave files and GitHub state alone. Finish with labeled lines or table rows for Missing secret, Token type, Resource owner, Repository access, Other permissions, and Secret listing. Include a permission/access table with one row for each permission needed. Keep each answer value unambiguous; put your reasoning in a separate paragraph.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 8.5/19 | 8.1 (7.6 to 8.6, 2 judged) | 0.3685 / 0.7369 |
| without_skill | 2 | 0 | 8.5/19 | 6.2 (6.2 to 6.2, 2 judged) | 0.3604 / 0.7207 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3685 / 0.3685 | 0.3604 / 0.3604 | +0.0081 | +0.0081 |
| num_turns | 5.5 / 5.5 | 8.5 / 8.5 | -3 | -3 |
| duration_ms | 28976.5 / 28976.5 | 111088 / 111088 | -82111.5 | -82111.5 |
| input_tokens | 9 / 9 | 16 / 16 | -7 | -7 |
| output_tokens | 2298.5 / 2298.5 | 3917.5 / 3917.5 | -1619 | -1619 |
| cache_creation_input_tokens | 37240.5 / 37240.5 | 27010 / 27010 | +10230.5 | +10230.5 |
| cache_read_input_tokens | 122715 / 122715 | 329384.5 / 329384.5 | -206669.5 | -206669.5 |
| tool_errors | 0 / 0 | 0.5 / 0.5 | -0.5 | -0.5 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| missing-actions-secret | 0/2 | 0/2 |
| fine-grained-pat | 0/2 | 2/2 |
| consumer-owner | 0/2 | 1/2 |
| single-consumer-repo | 0/2 | 0/2 |
| contents-write | 2/2 | 2/2 |
| pull-requests-write | 2/2 | 2/2 |
| issues-write | 2/2 | 0/2 |
| actions-write | 2/2 | 0/2 |
| commit-statuses-read | 2/2 | 2/2 |
| metadata-read | 1/2 | 1/2 |
| no-extra-grants | 0/2 | 0/2 |
| secret-listing-unavailable | 0/2 | 0/2 |
| run-metadata-read | 0/2 | 0/2 |
| failing-log-read | 0/2 | 0/2 |
| variables-read | 0/2 | 0/2 |
| secrets-read | 0/2 | 1/2 |
| no-write-attempted | 2/2 | 2/2 |
| workflows-unchanged | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
