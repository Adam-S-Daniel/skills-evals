# Eval report: workflow-path-audit

- Timestamp: 20261125T081818Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T081657Z-9f4581; started 2026-11-25T08:18:18Z, ended 2026-11-25T08:19:36Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.16, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.40 over 4 call(s); agent $0.30, judge $0.11, guard $0.00; last agent call $0.15
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.04); Fable meter 0.00 points

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 6.8 (6.8 to 6.8, 1 judged) | 0.1413 / 0.1413 |
| without_skill | 1 | 0 | 6/10 | 6.9 (6.9 to 6.9, 1 judged) | 0.1546 / 0.1546 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1413 / 0.1413 | 0.1546 / 0.1546 | -0.0133 | -0.0133 |
| num_turns | 4 / 4 | 5 / 5 | -1 | -1 |
| duration_ms | 23202 / 23202 | 26217 / 26217 | -3015 | -3015 |
| input_tokens | 8 / 8 | 10 / 10 | -2 | -2 |
| output_tokens | 2796 / 2796 | 3010 / 3010 | -214 | -214 |
| cache_creation_input_tokens | 25190 / 25190 | 26949 / 26949 | -1759 | -1759 |
| cache_read_input_tokens | 125604 / 125604 | 166990 / 166990 | -41386 | -41386 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 0/1 | 0/1 |
| source-change-runs-only-the-tests | 0/1 | 0/1 |
| lockfile-change-runs-only-the-tests | 0/1 | 0/1 |
| agents-md-change-runs-nothing | 0/1 | 0/1 |
| tests-row-names-its-paths | 1/1 | 1/1 |
| docs-site-row-names-its-paths | 1/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 1/1 |
