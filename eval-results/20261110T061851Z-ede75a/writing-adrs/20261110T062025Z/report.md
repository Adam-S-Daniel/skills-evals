# Eval report: writing-adrs

- Timestamp: 20261110T062025Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261110T061851Z-ede75a; started 2026-11-10T06:20:25Z, ended 2026-11-10T06:22:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.19 to 0.19, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.57 over 6 call(s); agent $0.43, judge $0.14, guard $0.00; last agent call $0.14

## Fixture: pr-body-outgrows-itself (n=3)

- Prompt: I'm opening a PR for the change to config/retry.yaml: failed SMS sends used to back off exponentially and now retry on a fixed 30-second interval. That looks like a downgrade, and I know reviewers will ask why. The reason: the SMS gateway rate-limits by API key over a sliding window and treats any burst as abuse. After the March outage, exponential backoff with jitter made thousands of queued sends retry in the same few seconds, the gateway blocked our key for an hour, and no passcodes went out. A fixed interval spreads the retries evenly. Two things we ruled out: capping the backoff at 60 seconds still bunches the retries after a long outage, and a client-side token bucket can't work because three other services share the same API key, so our service can't see the gateway's real count. Please write the PR description in PR_BODY.md.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5/13 | 2.8 (2.6 to 3.1, 3 judged) | 0.1430 / 0.4289 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1430 / 0.1376 |
| num_turns | 5 / 5 |
| duration_ms | 27893.3 / 26990 |
| input_tokens | 10 / 10 |
| output_tokens | 2516 / 2389 |
| cache_creation_input_tokens | 11255.3 / 11267 |
| cache_read_input_tokens | 181657 / 181831 |
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
| nothing-else-touched | 3/3 |
