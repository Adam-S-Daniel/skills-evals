# Eval report: workflow-path-audit

- Timestamp: 20261108T035352Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T035202Z-c1079e; started 2026-11-08T03:53:52Z, ended 2026-11-08T03:56:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.03 over 4 call(s); agent $0.80, judge $0.23, guard $0.00; last agent call $0.40

## Fixture: workflow-doc-in-step (n=1)

- Prompt: Both of our CI workflows run on every change. Fix their triggers so each runs only when it needs to.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 10/10 | 9.1 (9.1 to 9.1, 1 judged) | 0.4016 / 0.4016 |
| without_skill | 1 | 0 | 10/10 | 9.1 (9.1 to 9.1, 1 judged) | 0.4003 / 0.4003 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4016 / 0.4016 | 0.4003 / 0.4003 | +0.0012 | +0.0012 |
| num_turns | 8 / 8 | 9 / 9 | -1 | -1 |
| duration_ms | 72384 / 72384 | 58834 / 58834 | +13550 | +13550 |
| input_tokens | 16 / 16 | 18 / 18 | -2 | -2 |
| output_tokens | 3850 / 3850 | 3672 / 3672 | +178 | +178 |
| cache_creation_input_tokens | 33954 / 33954 | 31537 / 31537 | +2417 | +2417 |
| cache_read_input_tokens | 228880 / 228880 | 341909 / 341909 | -113029 | -113029 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| docs-change-builds-only-the-docs | 1/1 | 1/1 |
| source-change-runs-only-the-tests | 1/1 | 1/1 |
| lockfile-change-runs-only-the-tests | 1/1 | 1/1 |
| agents-md-change-runs-nothing | 1/1 | 1/1 |
| tests-row-names-its-paths | 1/1 | 1/1 |
| docs-site-row-names-its-paths | 1/1 | 1/1 |
| agents-md-keeps-the-rest | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| event-only-workflows-unfiltered | 1/1 | 1/1 |
| no-second-workflow-doc | 1/1 | 1/1 |
