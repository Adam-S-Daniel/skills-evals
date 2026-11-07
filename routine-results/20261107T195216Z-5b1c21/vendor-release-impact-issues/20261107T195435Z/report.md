# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T195435Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T195216Z-5b1c21; started 2026-11-07T19:54:35Z, ended 2026-11-07T20:01:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.66, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.54 over 6 call(s); agent $2.54, judge $0.00, guard $0.00; last agent call $0.35

## Fixture: issue-hygiene (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4865 / 1.4596 |
| without_skill | 3 | 0 | 4.3/7 | skipped (objective-decided) | 0.3586 / 1.0758 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4865 / 0.4844 | 0.3586 / 0.3504 | +0.1279 | +0.1340 |
| num_turns | 8.7 / 9 | 4.7 / 4 | +4 | +5 |
| duration_ms | 80394.3 / 80133 | 56677.7 / 55121 | +23716.7 | +25012 |
| input_tokens | 17.3 / 18 | 9.3 / 8 | +8 | +10 |
| output_tokens | 7239 / 7016 | 5291 / 5034 | +1948 | +1982 |
| cache_creation_input_tokens | 35402.7 / 35324 | 27851.3 / 28111 | +7551.3 | +7213 |
| cache_read_input_tokens | 292392.7 / 304100 | 149676.3 / 123942 | +142716.3 | +180158 |
| tool_errors | 1.3 / 2 | 0.3 / 0 | +1 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 3/3 |
| publish-times-source-and-version-bound | 3/3 | 0/3 |
| pr-refs-fenced-not-quoted | 3/3 | 3/3 |
| no-upstream-issue-backlink | 3/3 | 0/3 |
| no-placeholder-in-title | 3/3 | 1/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
| hook-matcher-surface-named | 3/3 | 3/3 |
