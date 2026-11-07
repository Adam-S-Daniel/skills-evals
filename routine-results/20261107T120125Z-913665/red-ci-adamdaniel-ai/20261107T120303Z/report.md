# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T120303Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T120125Z-913665; started 2026-11-07T12:03:03Z, ended 2026-11-07T12:04:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.53 over 8 call(s); agent $0.40, judge $0.12, guard $0.00; last agent call $0.09

## Fixture: paths-required (n=2)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 2/3 | 9.0 (9.0 to 9.0, 2 judged) | 0.1110 / 0.2221 |
| without_skill | 2 | 0 | 2/3 | 9.0 (9.0 to 9.0, 2 judged) | 0.0903 / 0.1806 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1110 / 0.1110 | 0.0903 / 0.0903 | +0.0207 | +0.0207 |
| num_turns | 5 / 5 | 5.5 / 5.5 | -0.5 | -0.5 |
| duration_ms | 18058.5 / 18058.5 | 19109.5 / 19109.5 | -1051 | -1051 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1568.5 / 1568.5 | 1612.5 / 1612.5 | -44 | -44 |
| cache_creation_input_tokens | 19534.5 / 19534.5 | 14130.5 / 14130.5 | +5404 | +5404 |
| cache_read_input_tokens | 171896.5 / 171896.5 | 176404 / 176404 | -4507.5 | -4507.5 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 2/2 | 2/2 |
| still-gated | 0/2 | 0/2 |
| site-untouched | 2/2 | 2/2 |
