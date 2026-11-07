# Eval report: debug-github-workflows

- Timestamp: 20261107T160058Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T155418Z-459562; started 2026-11-07T16:00:58Z, ended 2026-11-07T16:03:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.52 to 0.52, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.53 over 6 call(s); agent $0.53, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=3)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/7 | skipped (objective-decided) | 0.0955 / 0.2866 |
| without_skill | 3 | 0 | 5.3/7 | skipped (objective-decided) | 0.0817 / 0.2451 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0955 / 0.0857 | 0.0817 / 0.0792 | +0.0139 | +0.0065 |
| num_turns | 5.3 / 5 | 5.7 / 5 | -0.3 | 0 |
| duration_ms | 21403 / 18797 | 22744.3 / 22437 | -1341.3 | -3640 |
| input_tokens | 10.7 / 10 | 11.3 / 10 | -0.7 | 0 |
| output_tokens | 1462.3 / 1439 | 1402 / 1308 | +60.3 | +131 |
| cache_creation_input_tokens | 15807 / 12445 | 12116.3 / 12321 | +3690.7 | +124 |
| cache_read_input_tokens | 176771.3 / 167810 | 191895 / 168131 | -15123.7 | -321 |
| tool_errors | 0.3 / 0 | 0.7 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/3 | 0/3 |
| suite-passes-without-a-git-identity | 3/3 | 3/3 |
| suite-still-catches-a-broken-changelog | 3/3 | 3/3 |
| reply-reads-the-exit-code | 2/3 | 1/3 |
| reply-names-the-git-identity | 3/3 | 3/3 |
| sources-tests-and-workflow-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
