# Eval report: debug-github-workflows

- Timestamp: 20261026T211745Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261026T211328Z-470e6e; started 2026-10-26T21:17:45Z, ended 2026-10-26T21:19:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.18 to 0.19, seven_day 0.05 to 0.05, from 4 snapshots

## Fixture: swallowed-failure (n=1)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.1145 / 0.1145 |
| without_skill | 1 | 0 | 6/7 | 8.2 (8.2 to 8.2, 1 judged) | 0.0998 / 0.0998 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1145 / 0.1145 | 0.0998 / 0.0998 | +0.0147 | +0.0147 |
| num_turns | 9 / 9 | 8 / 8 | +1 | +1 |
| duration_ms | 54005 / 54005 | 43391 / 43391 | +10614 | +10614 |
| input_tokens | 18 / 18 | 16 / 16 | +2 | +2 |
| output_tokens | 2177 / 2177 | 2066 / 2066 | +111 | +111 |
| cache_creation_input_tokens | 14762 / 14762 | 12381 / 12381 | +2381 | +2381 |
| cache_read_input_tokens | 335237 / 335237 | 294352 / 294352 | +40885 | +40885 |
| tool_errors | 1 / 1 | 2 / 2 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 0/1 |
| working-listing-syncs-every-label | 1/1 | 1/1 |
| failed-listing-fails-the-script | 1/1 | 1/1 |
| reply-names-the-swallowing-construct | 0/1 | 1/1 |
| reply-names-the-missing-flag | 1/1 | 1/1 |
| workflow-and-inputs-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
