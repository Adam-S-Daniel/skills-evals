# Eval report: debug-github-workflows

- Timestamp: 20261026T201933Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T201829Z-b639e6; started 2026-10-26T20:19:33Z, ended 2026-10-26T20:24:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.11 to 0.12, seven_day 0.03 to 0.04, from 14 snapshots

## Fixture: swallowed-failure (n=3)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3/7 | 8.8 (8.8 to 8.8, 3 judged) | 0.1295 / 0.3885 |
| without_skill | 3 | 0 | 3/7 | 8.3 (8.0 to 8.8, 3 judged) | 0.0819 / 0.2456 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1295 / 0.0975 | 0.0819 / 0.0773 | +0.0476 | +0.0202 |
| num_turns | 7 / 7 | 5.7 / 5 | +1.3 | +2 |
| duration_ms | 38594 / 42351 | 28938.3 / 27492 | +9655.7 | +14859 |
| input_tokens | 14 / 14 | 10.7 / 10 | +3.3 | +4 |
| output_tokens | 1824 / 1849 | 1660.3 / 1506 | +163.7 | +343 |
| cache_creation_input_tokens | 21631 / 12402 | 11477.7 / 11016 | +10153.3 | +1386 |
| cache_read_input_tokens | 245436.7 / 254885 | 191341.3 / 178309 | +54095.3 | +76576 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/3 | 0/3 |
| working-listing-syncs-every-label | 0/3 | 0/3 |
| failed-listing-fails-the-script | 0/3 | 0/3 |
| reply-names-the-swallowing-construct | 0/3 | 0/3 |
| reply-names-the-missing-flag | 3/3 | 3/3 |
| workflow-and-inputs-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
