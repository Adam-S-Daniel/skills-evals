# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T121326Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T121234Z-8243bc; started 2026-10-26T12:13:26Z, ended 2026-10-26T12:21:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.24 to 0.27, seven_day 0.62 to 0.63, from 10 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4481 / 1.3443 |
| without_skill | 3 | 0 | 4.7/7 | skipped (objective-decided) | 0.2535 / 0.7605 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4481 / 0.4329 | 0.2535 / 0.2426 | +0.1946 | +0.1902 |
| num_turns | 10.3 / 10 | 6 / 6 | +4.3 | +4 |
| duration_ms | 101564.7 / 99624 | 55191.7 / 48913 | +46373 | +50711 |
| input_tokens | 17.3 / 16 | 12 / 12 | +5.3 | +4 |
| output_tokens | 8068 / 7953 | 4170 / 4094 | +3898 | +3859 |
| cache_creation_input_tokens | 26502.7 / 25823 | 15674 / 15502 | +10828.7 | +10321 |
| cache_read_input_tokens | 372351 / 337093 | 222478.7 / 219776 | +149872.3 | +117317 |
| tool_errors | 2.7 / 2 | 0.7 / 1 | +2 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 1/3 |
| no-placeholder-in-title | 3/3 | 1/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
