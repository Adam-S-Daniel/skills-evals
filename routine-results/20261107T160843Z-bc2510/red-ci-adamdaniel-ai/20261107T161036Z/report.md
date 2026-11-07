# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T161036Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T160843Z-bc2510; started 2026-11-07T16:10:36Z, ended 2026-11-07T16:18:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.53 to 0.53, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.24 over 6 call(s); agent $2.24, judge $0.00, guard $0.00; last agent call $0.37

## Fixture: paths-required (n=3)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 2/3 | skipped (objective-decided) | 0.3687 / 1.1062 |
| without_skill | 3 | 0 | 1.7/3 | skipped (objective-decided) | 0.3765 / 1.1295 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3687 / 0.3841 | 0.3765 / 0.3725 | -0.0078 | +0.0116 |
| num_turns | 6.7 / 7 | 7.3 / 7 | -0.7 | 0 |
| duration_ms | 71343 / 69994 | 83028.7 / 84777 | -11685.7 | -14783 |
| input_tokens | 14 / 14 | 16 / 14 | -2 | 0 |
| output_tokens | 4542.3 / 4546 | 5532 / 5678 | -989.7 | -1132 |
| cache_creation_input_tokens | 23014 / 19660 | 21049 / 21769 | +1965 | -2109 |
| cache_read_input_tokens | 245500.3 / 261005 | 276533 / 259938 | -31032.7 | +1067 |
| tool_errors | 0.7 / 1 | 1 / 1 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 3/3 | 3/3 |
| still-gated | 0/3 | 0/3 |
| site-untouched | 3/3 | 2/3 |
