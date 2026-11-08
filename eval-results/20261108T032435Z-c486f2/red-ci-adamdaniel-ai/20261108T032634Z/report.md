# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261108T032634Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T032435Z-c486f2; started 2026-11-08T03:26:34Z, ended 2026-11-08T03:29:30Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.94 over 4 call(s); agent $0.69, judge $0.25, guard $0.00; last agent call $0.31

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 8.3 (8.3 to 8.3, 1 judged) | 0.3824 / 0.3824 |
| without_skill | 1 | 0 | 2/3 | 8.2 (8.2 to 8.2, 1 judged) | 0.3106 / 0.3106 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3824 / 0.3824 | 0.3106 / 0.3106 | +0.0718 | +0.0718 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 64243 / 64243 | 75695 / 75695 | -11452 | -11452 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 4848 / 4848 | 4507 / 4507 | +341 | +341 |
| cache_creation_input_tokens | 29426 / 29426 | 20176 / 20176 | +9250 | +9250 |
| cache_read_input_tokens | 212357 / 212357 | 261324 / 261324 | -48967 | -48967 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 1/1 |
