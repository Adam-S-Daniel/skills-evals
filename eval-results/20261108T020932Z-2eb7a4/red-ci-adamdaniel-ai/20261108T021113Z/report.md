# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261108T021113Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T020932Z-2eb7a4; started 2026-11-08T02:11:13Z, ended 2026-11-08T02:13:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.79 over 2 call(s); agent $0.79, judge $0.00, guard $0.00; last agent call $0.29

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | skipped (objective-decided) | 0.4959 / 0.4959 |
| without_skill | 1 | 0 | 1/3 | skipped (objective-decided) | 0.2948 / 0.2948 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4959 / 0.4959 | 0.2948 / 0.2948 | +0.2011 | +0.2011 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 70513 / 70513 | 66614 / 66614 | +3899 | +3899 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 3906 / 3906 | 4010 / 4010 | -104 | -104 |
| cache_creation_input_tokens | 29903 / 29903 | 20210 / 20210 | +9693 | +9693 |
| cache_read_input_tokens | 251991 / 251991 | 223277 / 223277 | +28714 | +28714 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 0/1 |
