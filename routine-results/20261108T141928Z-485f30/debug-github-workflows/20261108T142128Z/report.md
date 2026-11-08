# Eval report: debug-github-workflows

- Timestamp: 20261108T142128Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T141928Z-485f30; started 2026-11-08T14:21:28Z, ended 2026-11-08T14:24:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.78 to 0.78, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.63 over 2 call(s); agent $0.63, judge $0.00, guard $0.00; last agent call $0.28

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.3586 / 0.3586 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.2759 / 0.2759 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3586 / 0.3586 | 0.2759 / 0.2759 | +0.0828 | +0.0828 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 68812 / 68812 | 79027 / 79027 | -10215 | -10215 |
| input_tokens | 18 / 18 | 18 / 18 | 0 | 0 |
| output_tokens | 3386 / 3386 | 3557 / 3557 | -171 | -171 |
| cache_creation_input_tokens | 28514 / 28514 | 17750 / 17750 | +10764 | +10764 |
| cache_read_input_tokens | 283622 / 283622 | 292859 / 292859 | -9237 | -9237 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 1/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
