# Eval report: vendor-release-impact-issues

- Timestamp: 20261025T195616Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T195534Z-5b894e; started 2026-10-25T19:56:16Z, ended 2026-10-25T20:02:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.06 to 0.07, seven_day 0.43 to 0.43, from 7 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4886 / 1.4659 |
| without_skill | 3 | 0 | 4.3/7 | skipped (objective-decided) | 0.2437 / 0.7310 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4886 / 0.4446 | 0.2437 / 0.2422 | +0.2450 | +0.2024 |
| num_turns | 9 / 8 | 5 / 5 | +4 | +3 |
| duration_ms | 76271.3 / 72459 | 48374.3 / 48185 | +27897 | +24274 |
| input_tokens | 15.3 / 14 | 9.3 / 10 | +6 | +4 |
| output_tokens | 7487 / 7332 | 4460 / 4313 | +3027 | +3019 |
| cache_creation_input_tokens | 34599.3 / 25730 | 15130 / 14971 | +19469.3 | +10759 |
| cache_read_input_tokens | 309218 / 284505 | 166300.3 / 179159 | +142917.7 | +105346 |
| tool_errors | 1.3 / 1 | 0.7 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 0/3 |
| no-placeholder-in-title | 3/3 | 1/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
