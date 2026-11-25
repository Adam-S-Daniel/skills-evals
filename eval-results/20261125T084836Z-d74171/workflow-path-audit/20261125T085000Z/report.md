# Eval report: workflow-path-audit

- Timestamp: 20261125T085000Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T084836Z-d74171; started 2026-11-25T08:50:00Z, ended 2026-11-25T08:53:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.39 over 4 call(s); agent $1.12, judge $0.27, guard $0.00; last agent call $0.47
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.08 points of the weekly meter (0.06 to 0.11); Fable meter 0.03 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 9.8 (9.8 to 9.8, 1 judged) | 0.6500 / 0.6500 |
| without_skill | 1 | 0 | 8/8 | 8.4 (8.4 to 8.4, 1 judged) | 0.4673 / 0.4673 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.6500 / 0.6500 | 0.4673 / 0.4673 | +0.1828 | +0.1828 |
| num_turns | 13 / 13 | 9 / 9 | +4 | +4 |
| duration_ms | 72438 / 72438 | 107110 / 107110 | -34672 | -34672 |
| input_tokens | 28 / 28 | 20 / 20 | +8 | +8 |
| output_tokens | 5505 / 5505 | 8319 / 8319 | -2814 | -2814 |
| cache_creation_input_tokens | 53474 / 53474 | 27085 / 27085 | +26389 | +26389 |
| cache_read_input_tokens | 514678 / 514678 | 371803 / 371803 | +142875 | +142875 |
| tool_errors | 1 / 1 | 2 / 2 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | 1/1 | 1/1 |
| companion-skip-workflow-removed | 1/1 | 1/1 |
| docs-change-still-reports-the-required-check | 1/1 | 1/1 |
| source-change-skips-the-docs-site | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| ruleset-unchanged | 1/1 | 1/1 |
| project-files-unchanged | 1/1 | 1/1 |
