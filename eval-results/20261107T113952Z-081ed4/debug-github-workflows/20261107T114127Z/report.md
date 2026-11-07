# Eval report: debug-github-workflows

- Timestamp: 20261107T114127Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T113952Z-081ed4; started 2026-11-07T11:41:27Z, ended 2026-11-07T11:43:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.51 over 8 call(s); agent $0.35, judge $0.15, guard $0.00; last agent call $0.08

## Fixture: git-identity (n=2)

- Prompt: CI on main has failed ever since the changelog tests landed, but `bash test/run-tests.sh` passes on my laptop. Fix it so the tests pass in CI too. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 6/7 | 8.6 (8.2 to 9.0, 2 judged) | 0.1004 / 0.2008 |
| without_skill | 2 | 0 | 6/7 | 8.7 (8.4 to 9.0, 2 judged) | 0.0757 / 0.1514 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1004 / 0.1004 | 0.0757 / 0.0757 | +0.0247 | +0.0247 |
| num_turns | 5.5 / 5.5 | 5 / 5 | +0.5 | +0.5 |
| duration_ms | 21108.5 / 21108.5 | 18492.5 / 18492.5 | +2616 | +2616 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1315.5 / 1315.5 | 1192.5 / 1192.5 | +123 | +123 |
| cache_creation_input_tokens | 17738.5 / 17738.5 | 11754.5 / 11754.5 | +5984 | +5984 |
| cache_read_input_tokens | 162791.5 / 162791.5 | 167443 / 167443 | -4651.5 | -4651.5 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failure-evidence-read-without-writes | 0/2 | 0/2 |
| suite-passes-without-a-git-identity | 2/2 | 2/2 |
| suite-still-catches-a-broken-changelog | 2/2 | 2/2 |
| reply-reads-the-exit-code | 2/2 | 2/2 |
| reply-names-the-git-identity | 2/2 | 2/2 |
| sources-tests-and-workflow-unchanged | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
