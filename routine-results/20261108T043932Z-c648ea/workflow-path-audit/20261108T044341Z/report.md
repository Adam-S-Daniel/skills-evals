# Eval report: workflow-path-audit

- Timestamp: 20261108T044341Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T043932Z-c648ea; started 2026-11-08T04:43:41Z, ended 2026-11-08T04:44:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 4 call(s); agent $0.27, judge $0.09, guard $0.00; last agent call $0.13

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/10 | 7.6 (7.6 to 7.6, 1 judged) | 0.1402 / 0.1402 |
| without_skill | 1 | 0 | 10/10 | 9.4 (9.4 to 9.4, 1 judged) | 0.1280 / 0.1280 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1402 / 0.1402 | 0.1280 / 0.1280 | +0.0122 | +0.0122 |
| num_turns | 4 / 4 | 5 / 5 | -1 | -1 |
| duration_ms | 22821 / 22821 | 20643 / 20643 | +2178 | +2178 |
| input_tokens | 8 / 8 | 10 / 10 | -2 | -2 |
| output_tokens | 2721 / 2721 | 1685 / 1685 | +1036 | +1036 |
| cache_creation_input_tokens | 25173 / 25173 | 23785 / 23785 | +1388 | +1388 |
| cache_read_input_tokens | 122762 / 122762 | 159990 / 159990 | -37228 | -37228 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 0/1 | 1/1 |
| source-change-runs-only-the-tests | 0/1 | 1/1 |
| lockfile-change-runs-only-the-tests | 0/1 | 1/1 |
| agents-md-change-runs-nothing | 0/1 | 1/1 |
| tests-row-names-its-paths | 1/1 | 1/1 |
| docs-site-row-names-its-paths | 1/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 1/1 |
