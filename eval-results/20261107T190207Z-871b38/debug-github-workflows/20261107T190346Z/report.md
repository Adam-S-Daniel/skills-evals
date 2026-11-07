# Eval report: debug-github-workflows

- Timestamp: 20261107T190346Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T190207Z-871b38; started 2026-11-07T19:03:46Z, ended 2026-11-07T19:11:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.62 to 0.63, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.30 over 12 call(s); agent $1.57, judge $0.73, guard $0.00; last agent call $0.28

## Fixture: git-identity (n=3)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.3/7 | 9.0 (9.0 to 9.0, 3 judged) | 0.2734 / 0.8203 |
| without_skill | 3 | 0 | 6.7/7 | 8.9 (8.8 to 9.2, 3 judged) | 0.2511 / 0.7533 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2734 / 0.2668 | 0.2511 / 0.2556 | +0.0223 | +0.0111 |
| num_turns | 7.7 / 8 | 8.3 / 8 | -0.7 | 0 |
| duration_ms | 47737.7 / 45952 | 57270.7 / 64664 | -9533 | -18712 |
| input_tokens | 16 / 16 | 17.3 / 18 | -1.3 | -2 |
| output_tokens | 3009 / 3144 | 3052 / 3160 | -43 | -16 |
| cache_creation_input_tokens | 19762.3 / 17159 | 16161 / 16344 | +3601.3 | +815 |
| cache_read_input_tokens | 259957.7 / 249794 | 288409 / 287445 | -28451.3 | -37651 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 2/3 | 2/3 |
| suite-passes-without-a-git-identity | 3/3 | 3/3 |
| suite-still-catches-a-broken-changelog | 3/3 | 3/3 |
| reply-reads-the-exit-code | 3/3 | 3/3 |
| reply-names-the-git-identity | 2/3 | 3/3 |
| sources-tests-and-workflow-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
