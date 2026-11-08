# Eval report: debug-github-workflows

- Timestamp: 20261108T110843Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T110657Z-e107ac; started 2026-11-08T11:08:43Z, ended 2026-11-08T11:10:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.55 over 2 call(s); agent $0.55, judge $0.00, guard $0.00; last agent call $0.24

## Fixture: git-identity (n=1)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/7 | skipped (objective-decided) | 0.3134 / 0.3134 |
| without_skill | 1 | 0 | 6/7 | skipped (objective-decided) | 0.2365 / 0.2365 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3134 / 0.3134 | 0.2365 / 0.2365 | +0.0769 | +0.0769 |
| num_turns | 8 / 8 | 7 / 7 | +1 | +1 |
| duration_ms | 33112 / 33112 | 47861 / 47861 | -14749 | -14749 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 2578 / 2578 | 2757 / 2757 | -179 | -179 |
| cache_creation_input_tokens | 25737 / 25737 | 15826 / 15826 | +9911 | +9911 |
| cache_read_input_tokens | 279326 / 279326 | 246990 / 246990 | +32336 | +32336 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 1/1 | 0/1 |
| suite-passes-without-a-git-identity | 1/1 | 1/1 |
| suite-still-catches-a-broken-changelog | 1/1 | 1/1 |
| reply-reads-the-exit-code | 1/1 | 1/1 |
| reply-names-the-git-identity | 1/1 | 1/1 |
| sources-tests-and-workflow-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
