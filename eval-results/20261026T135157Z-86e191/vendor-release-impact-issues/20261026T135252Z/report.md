# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T135252Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T135157Z-86e191; started 2026-10-26T13:52:52Z, ended 2026-10-26T14:00:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.16 to 0.22, seven_day 0.69 to 0.7, from 10 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4154 / 1.2463 |
| without_skill | 3 | 0 | 5/7 | skipped (objective-decided) | 0.2245 / 0.6736 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4154 / 0.4113 | 0.2245 / 0.2084 | +0.1909 | +0.2029 |
| num_turns | 8.7 / 9 | 5 / 5 | +3.7 | +4 |
| duration_ms | 101041 / 109385 | 42331.3 / 42452 | +58709.7 | +66933 |
| input_tokens | 15.3 / 16 | 10 / 10 | +5.3 | +6 |
| output_tokens | 7788.7 / 7592 | 3697.7 / 3255 | +4091 | +4337 |
| cache_creation_input_tokens | 24526.7 / 24148 | 14291 / 13565 | +10235.7 | +10583 |
| cache_read_input_tokens | 315898.3 / 330406 | 179875.3 / 180177 | +136023 | +150229 |
| tool_errors | 1.3 / 1 | 0.3 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 2/3 |
| no-placeholder-in-title | 3/3 | 1/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
