# Eval report: writing-adrs

- Timestamp: 20261108T145423Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261108T145319Z-f998a1; started 2026-11-08T14:54:23Z, ended 2026-11-08T14:55:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.79 to 0.79, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.44 over 6 call(s); agent $0.33, judge $0.10, guard $0.00; last agent call $0.08

## Fixture: pr-body-outgrows-itself (n=3)

- Prompt: I'm opening a PR for the change to config/retry.yaml: failed SMS sends used to back off exponentially and now retry on a fixed 30-second interval. That looks like a downgrade, and I know reviewers will ask why. The reason: the SMS gateway rate-limits by API key over a sliding window and treats any burst as abuse. After the March outage, exponential backoff with jitter made thousands of queued sends retry in the same few seconds, the gateway blocked our key for an hour, and no passcodes went out. A fixed interval spreads the retries evenly. Two things we ruled out: capping the backoff at 60 seconds still bunches the retries after a long outage, and a client-side token bucket can't work because three other services share the same API key, so our service can't see the gateway's real count. Please write the PR description in PR_BODY.md.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4.3/13 | 2.6 (2.3 to 3.1, 3 judged) | 0.1101 / 0.3303 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1101 / 0.0809 |
| num_turns | 3.7 / 4 |
| duration_ms | 17250.7 / 16296 |
| input_tokens | 7.3 / 8 |
| output_tokens | 1848.7 / 1765 |
| cache_creation_input_tokens | 19961.3 / 11138 |
| cache_read_input_tokens | 117641.7 / 139370 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| new-adr-0003-is-a-house-format-entry | 0/3 |
| adr-0003-records-the-reason | 0/3 |
| adr-0003-records-the-rejected-alternatives | 0/3 |
| index-gained-a-row-for-0003 | 0/3 |
| index-rows-for-0001-and-0002-kept | 3/3 |
| decision-log-links-resolve | 3/3 |
| retry-config-comment-points-at-0003 | 0/3 |
| retry-config-pointers-resolve | 3/3 |
| retry-config-values-unchanged | 3/3 |
| pr-body-links-the-adr | 0/3 |
| pr-body-is-short | 0/3 |
| exactly-one-new-adr-file | 0/3 |
| nothing-else-touched | 1/3 |
