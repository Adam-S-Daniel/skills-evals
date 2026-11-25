# Eval report: writing-adrs

- Timestamp: 20261125T122940Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T122815Z-c44440; started 2026-11-25T12:29:40Z, ended 2026-11-25T12:30:47Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 4 call(s); agent $0.26, judge $0.07, guard $0.00; last agent call $0.12
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.01 to 0.03); Fable meter 0.00 points

## Fixture: pr-body-outgrows-itself (n=1)

- Prompt: I'm opening a PR for the change to config/retry.yaml: failed SMS sends used to back off exponentially and now retry on a fixed 30-second interval. That looks like a downgrade, and I know reviewers will ask why. The reason: the SMS gateway rate-limits by API key over a sliding window and treats any burst as abuse. After the March outage, exponential backoff with jitter made thousands of queued sends retry in the same few seconds, the gateway blocked our key for an hour, and no passcodes went out. A fixed interval spreads the retries evenly. Two things we ruled out: capping the backoff at 60 seconds still bunches the retries after a long outage, and a client-side token bucket can't work because three other services share the same API key, so our service can't see the gateway's real count. Please write the PR description in PR_BODY.md.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/13 | 3.3 (3.3 to 3.3, 1 judged) | 0.1423 / 0.1423 |
| without_skill | 1 | 0 | 5/13 | 2.6 (2.6 to 2.6, 1 judged) | 0.1203 / 0.1203 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1423 / 0.1423 | 0.1203 / 0.1203 | +0.0220 | +0.0220 |
| num_turns | 4 / 4 | 3 / 3 | +1 | +1 |
| duration_ms | 25184 / 25184 | 16766 / 16766 | +8418 | +8418 |
| input_tokens | 8 / 8 | 6 / 6 | +2 | +2 |
| output_tokens | 2985 / 2985 | 1918 / 1918 | +1067 | +1067 |
| cache_creation_input_tokens | 24940 / 24940 | 23081 / 23081 | +1859 | +1859 |
| cache_read_input_tokens | 127030 / 127030 | 88071 / 88071 | +38959 | +38959 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| new-adr-0003-is-a-house-format-entry | 0/1 | 0/1 |
| adr-0003-records-the-reason | 0/1 | 0/1 |
| adr-0003-records-the-rejected-alternatives | 0/1 | 0/1 |
| index-gained-a-row-for-0003 | 0/1 | 0/1 |
| index-rows-for-0001-and-0002-kept | 1/1 | 1/1 |
| decision-log-links-resolve | 1/1 | 1/1 |
| retry-config-comment-points-at-0003 | 0/1 | 0/1 |
| retry-config-pointers-resolve | 1/1 | 1/1 |
| retry-config-values-unchanged | 1/1 | 1/1 |
| pr-body-links-the-adr | 0/1 | 0/1 |
| pr-body-is-short | 0/1 | 0/1 |
| exactly-one-new-adr-file | 0/1 | 0/1 |
| nothing-else-touched | 1/1 | 1/1 |
