# Eval report: vendor-release-impact-issues

- Timestamp: 20261108T153615Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T153432Z-af8fda; started 2026-11-08T15:36:15Z, ended 2026-11-08T15:38:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.8 to 0.8, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.70 over 2 call(s); agent $0.70, judge $0.00, guard $0.00; last agent call $0.28

## Fixture: issue-hygiene (n=1)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.4235 / 0.4235 |
| without_skill | 1 | 0 | 4/7 | skipped (objective-decided) | 0.2764 / 0.2764 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4235 / 0.4235 | 0.2764 / 0.2764 | +0.1471 | +0.1471 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 70707 / 70707 | 58827 / 58827 | +11880 | +11880 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 6512 / 6512 | 5315 / 5315 | +1197 | +1197 |
| cache_creation_input_tokens | 48854 / 48854 | 27547 / 27547 | +21307 | +21307 |
| cache_read_input_tokens | 244616 / 244616 | 161793 / 161793 | +82823 | +82823 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 1/1 | 1/1 |
| publish-times-source-and-version-bound | 1/1 | 0/1 |
| pr-refs-fenced-not-quoted | 1/1 | 1/1 |
| no-upstream-issue-backlink | 1/1 | 0/1 |
| no-placeholder-in-title | 1/1 | 0/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| hook-matcher-surface-named | 1/1 | 1/1 |
