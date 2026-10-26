# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T144553Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144552Z-e22ff3; started 2026-10-26T14:45:53Z, ended 2026-10-26T14:53:38Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.58 to 0.65, seven_day 0.78 to 0.79, from 12 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4395 / 1.3185 |
| without_skill | 3 | 0 | 4.7/7 | skipped (objective-decided) | 0.2668 / 0.8005 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4395 / 0.4143 | 0.2668 / 0.2559 | +0.1727 | +0.1584 |
| num_turns | 10.7 / 9 | 6.7 / 6 | +4 | +3 |
| duration_ms | 91580 / 85843 | 57034.3 / 58410 | +34545.7 | +27433 |
| input_tokens | 17.3 / 16 | 12 / 12 | +5.3 | +4 |
| output_tokens | 8021.7 / 7484 | 4863 / 4473 | +3158.7 | +3011 |
| cache_creation_input_tokens | 25694 / 24725 | 15661.3 / 15291 | +10032.7 | +9434 |
| cache_read_input_tokens | 366288.7 / 333271 | 220316.7 / 219244 | +145972 | +114027 |
| tool_errors | 1.3 / 1 | 0.7 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 1/3 |
| no-placeholder-in-title | 3/3 | 1/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
