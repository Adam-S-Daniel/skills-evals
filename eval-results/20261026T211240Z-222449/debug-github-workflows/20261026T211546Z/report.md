# Eval report: debug-github-workflows

- Timestamp: 20261026T211546Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T211240Z-222449; started 2026-10-26T21:15:46Z, ended 2026-10-26T21:18:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.18 to 0.19, seven_day 0.05 to 0.05, from 7 snapshots

## Fixture: swallowed-failure (n=3)

- Prompt: The nightly Sync labels workflow has been green all week, but the triage and needs-review labels never showed up on any of our repositories. Find out why and fix it. Do not change remote state.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.0796 / 0.2388 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.0901 / 0.2704 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0796 / 0.0782 | 0.0901 / 0.0953 | -0.0105 | -0.0172 |
| num_turns | 5.3 / 5 | 6.7 / 7 | -1.3 | -2 |
| duration_ms | 25321.7 / 24775 | 32369.3 / 32037 | -7047.7 | -7262 |
| input_tokens | 10 / 10 | 12.7 / 14 | -2.7 | -4 |
| output_tokens | 1631.7 / 1658 | 1844.7 / 1932 | -213 | -274 |
| cache_creation_input_tokens | 11350.3 / 10923 | 12156 / 12596 | -805.7 | -1673 |
| cache_read_input_tokens | 177421.3 / 177308 | 229197.7 / 254479 | -51776.3 | -77171 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/3 | 0/3 |
| working-listing-syncs-every-label | 3/3 | 3/3 |
| failed-listing-fails-the-script | 3/3 | 3/3 |
| reply-names-the-swallowing-construct | 1/3 | 0/3 |
| reply-names-the-missing-flag | 3/3 | 3/3 |
| workflow-and-inputs-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
