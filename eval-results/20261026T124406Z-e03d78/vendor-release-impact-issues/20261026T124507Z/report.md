# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T124507Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T124406Z-e03d78; started 2026-10-26T12:45:07Z, ended 2026-10-26T12:52:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.38 to 0.41, seven_day 0.65 to 0.66, from 9 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4372 / 1.3115 |
| without_skill | 3 | 0 | 4.7/7 | skipped (objective-decided) | 0.2486 / 0.7459 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4372 / 0.4271 | 0.2486 / 0.2581 | +0.1885 | +0.1690 |
| num_turns | 9.3 / 9 | 5.7 / 6 | +3.7 | +3 |
| duration_ms | 91098.3 / 91574 | 49236 / 51825 | +41862.3 | +39749 |
| input_tokens | 16 / 16 | 11.3 / 12 | +4.7 | +4 |
| output_tokens | 7951.3 / 8146 | 4132.3 / 4249 | +3819 | +3897 |
| cache_creation_input_tokens | 26292.7 / 25784 | 15554 / 15871 | +10738.7 | +9913 |
| cache_read_input_tokens | 337920 / 333798 | 206505.3 / 220228 | +131414.7 | +113570 |
| tool_errors | 1.7 / 2 | 0 / 0 | +1.7 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 1/3 |
| no-placeholder-in-title | 3/3 | 1/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
