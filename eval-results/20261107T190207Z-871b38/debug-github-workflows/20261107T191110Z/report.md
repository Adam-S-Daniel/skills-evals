# Eval report: debug-github-workflows

- Timestamp: 20261107T191110Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T190207Z-871b38; started 2026-11-07T19:11:10Z, ended 2026-11-07T19:14:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.63 to 0.63, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 12 call(s); agent $0.51, judge $0.25, guard $0.00; last agent call $0.07

## Fixture: git-identity (n=3)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5/7 | 7.2 (6.8 to 7.4, 3 judged) | 0.0944 / 0.2832 |
| without_skill | 3 | 0 | 5.3/7 | 7.6 (7.4 to 7.8, 3 judged) | 0.0759 / 0.2276 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0944 / 0.0881 | 0.0759 / 0.0706 | +0.0185 | +0.0175 |
| num_turns | 5.3 / 6 | 4.7 / 4 | +0.7 | +2 |
| duration_ms | 20414 / 22667 | 19638.7 / 17702 | +775.3 | +4965 |
| input_tokens | 10.7 / 12 | 9.3 / 8 | +1.3 | +4 |
| output_tokens | 1336 / 1412 | 1262.3 / 1099 | +73.7 | +313 |
| cache_creation_input_tokens | 15822 / 13067 | 11924.3 / 11676 | +3897.7 | +1391 |
| cache_read_input_tokens | 177325.7 / 194538 | 155409 / 130790 | +21916.7 | +63748 |
| tool_errors | 0.7 / 1 | 1 / 1 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/3 | 0/3 |
| suite-passes-without-a-git-identity | 3/3 | 3/3 |
| suite-still-catches-a-broken-changelog | 3/3 | 3/3 |
| reply-reads-the-exit-code | 0/3 | 1/3 |
| reply-names-the-git-identity | 3/3 | 3/3 |
| sources-tests-and-workflow-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
