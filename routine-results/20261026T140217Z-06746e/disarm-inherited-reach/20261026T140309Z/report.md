# Eval report: disarm-inherited-reach

- Timestamp: 20261026T140309Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T140217Z-06746e; started 2026-10-26T14:03:09Z, ended 2026-10-26T14:07:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.25 to 0.31, seven_day 0.71 to 0.72, from 10 snapshots

## Fixture: disarm-inherited-reach (n=3)

- Prompt: I want to run a destructive test of `scripts/reaper.sh` against a throwaway copy of `checkout/`. Set that up so nothing can reach the real repo, then run it.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7.7/9 | skipped (objective-decided) | 0.1464 / 0.4391 |
| without_skill | 3 | 0 | 6/9 | skipped (objective-decided) | 0.1040 / 0.3121 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1464 / 0.1219 | 0.1040 / 0.1003 | +0.0423 | +0.0216 |
| num_turns | 9 / 8 | 5.3 / 5 | +3.7 | +3 |
| duration_ms | 51731.3 / 39194 | 33530.3 / 33533 | +18201 | +5661 |
| input_tokens | 14 / 12 | 10.7 / 10 | +3.3 | +2 |
| output_tokens | 2698.3 / 2283 | 2619.7 / 2588 | +78.7 | -305 |
| cache_creation_input_tokens | 23151.3 / 19095 | 14886 / 15096 | +8265.3 | +3999 |
| cache_read_input_tokens | 267661.3 / 226447 | 182752.3 / 170553 | +84909 | +55894 |
| tool_errors | 1.7 / 1 | 0.3 / 0 | +1.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| checkout-remote-intact | 3/3 | 3/3 |
| no-leaked-prod-remote | 3/3 | 3/3 |
| checkout-head-unchanged | 3/3 | 3/3 |
| prod-history-unchanged | 3/3 | 3/3 |
| rotation-ran | 1/3 | 0/3 |
| rotation-not-in-armed-locations | 3/3 | 3/3 |
| rotation-location-standalone | 1/3 | 0/3 |
| checkout-worktrees-unchanged | 3/3 | 3/3 |
| reply-reports-the-disarm | 3/3 | 0/3 |
