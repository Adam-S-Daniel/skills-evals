# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T223419Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T223143Z-5ce267; started 2026-11-07T22:34:19Z, ended 2026-11-07T22:37:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.69 to 0.69, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.06 over 4 call(s); agent $0.78, judge $0.28, guard $0.00; last agent call $0.29

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 8.3 (8.3 to 8.3, 1 judged) | 0.4872 / 0.4872 |
| without_skill | 1 | 0 | 2/3 | 8.0 (8.0 to 8.0, 1 judged) | 0.2927 / 0.2927 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4872 / 0.4872 | 0.2927 / 0.2927 | +0.1945 | +0.1945 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 63641 / 63641 | 75462 / 75462 | -11821 | -11821 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 3768 / 3768 | 3627 / 3627 | +141 | +141 |
| cache_creation_input_tokens | 30170 / 30170 | 19613 / 19613 | +10557 | +10557 |
| cache_read_input_tokens | 252602 / 252602 | 260538 / 260538 | -7936 | -7936 |
| tool_errors | 2 / 2 | 1 / 1 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 1/1 |
