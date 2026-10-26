# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T065015Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T064933Z-f0d47b; started 2026-10-26T06:50:15Z, ended 2026-10-26T06:56:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.13 to 0.14, seven_day 0.56 to 0.56, from 7 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4618 / 1.3854 |
| without_skill | 3 | 0 | 4.3/7 | skipped (objective-decided) | 0.2367 / 0.7100 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4618 / 0.4109 | 0.2367 / 0.2329 | +0.2251 | +0.1781 |
| num_turns | 7.7 / 7 | 5.3 / 5 | +2.3 | +2 |
| duration_ms | 78850.7 / 76272 | 48830 / 47440 | +30020.7 | +28832 |
| input_tokens | 13.3 / 12 | 10 / 10 | +3.3 | +2 |
| output_tokens | 7163 / 7237 | 4140.7 / 3923 | +3022.3 | +3314 |
| cache_creation_input_tokens | 33327.7 / 24908 | 14728.3 / 14666 | +18599.3 | +10242 |
| cache_read_input_tokens | 258625 / 236851 | 179234.3 / 178677 | +79390.7 | +58174 |
| tool_errors | 1.7 / 2 | 0.3 / 0 | +1.3 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 1/3 |
| no-placeholder-in-title | 3/3 | 0/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
