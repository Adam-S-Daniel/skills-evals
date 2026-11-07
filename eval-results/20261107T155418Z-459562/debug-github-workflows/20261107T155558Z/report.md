# Eval report: debug-github-workflows

- Timestamp: 20261107T155558Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T155418Z-459562; started 2026-11-07T15:55:58Z, ended 2026-11-07T16:00:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.51 to 0.52, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.57 over 6 call(s); agent $1.57, judge $0.00, guard $0.00; last agent call $0.26

## Fixture: git-identity (n=3)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.2864 / 0.8592 |
| without_skill | 3 | 0 | 6.7/7 | skipped (objective-decided) | 0.2367 / 0.7100 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2864 / 0.2497 | 0.2367 / 0.2246 | +0.0497 | +0.0251 |
| num_turns | 9 / 9 | 8 / 8 | +1 | +1 |
| duration_ms | 50164.3 / 53390 | 45642 / 50328 | +4522.3 | +3062 |
| input_tokens | 18 / 18 | 15.3 / 14 | +2.7 | +4 |
| output_tokens | 3004.7 / 2801 | 2764 / 2672 | +240.7 | +129 |
| cache_creation_input_tokens | 20181.3 / 16801 | 15875 / 15460 | +4306.3 | +1341 |
| cache_read_input_tokens | 315144 / 321333 | 263624.7 / 250815 | +51519.3 | +70518 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 3/3 | 3/3 |
| suite-passes-without-a-git-identity | 3/3 | 3/3 |
| suite-still-catches-a-broken-changelog | 3/3 | 3/3 |
| reply-reads-the-exit-code | 3/3 | 3/3 |
| reply-names-the-git-identity | 3/3 | 2/3 |
| sources-tests-and-workflow-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
