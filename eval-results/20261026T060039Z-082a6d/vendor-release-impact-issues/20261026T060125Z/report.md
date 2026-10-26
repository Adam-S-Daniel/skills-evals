# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T060125Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T060039Z-082a6d; started 2026-10-26T06:01:25Z, ended 2026-10-26T06:05:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.11 to 0.12, seven_day 0.56 to 0.56, from 6 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.2150 / 0.6450 |
| without_skill | 3 | 0 | 4.7/7 | skipped (objective-decided) | 0.0921 / 0.2763 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2150 / 0.1994 | 0.0921 / 0.0954 | +0.1229 | +0.1040 |
| num_turns | 7.7 / 7 | 4.3 / 4 | +3.3 | +3 |
| duration_ms | 58389.7 / 56885 | 26267 / 26822 | +32122.7 | +30063 |
| input_tokens | 11.3 / 10 | 8.7 / 8 | +2.7 | +2 |
| output_tokens | 5804 / 5661 | 2638.3 / 2622 | +3165.7 | +3039 |
| cache_creation_input_tokens | 33711 / 26529 | 12575.3 / 12786 | +21135.7 | +13743 |
| cache_read_input_tokens | 218380.7 / 193759 | 152202.7 / 139216 | +66178 | +54543 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 2/3 |
| no-placeholder-in-title | 3/3 | 0/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
