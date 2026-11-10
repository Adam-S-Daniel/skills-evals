# Eval report: debug-github-workflows

- Timestamp: 20261110T042315Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T042059Z-dea229; started 2026-11-10T04:23:15Z, ended 2026-11-10T04:25:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.18 to 0.18, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.74 over 4 call(s); agent $0.58, judge $0.16, guard $0.00; last agent call $0.23

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 9.8 (9.8 to 9.8, 1 judged) | 0.3501 / 0.3501 |
| without_skill | 1 | 0 | 6/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.2336 / 0.2336 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3501 / 0.3501 | 0.2336 / 0.2336 | +0.1165 | +0.1165 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 51806 / 51806 | 48799 / 48799 | +3007 | +3007 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 3363 / 3363 | 3462 / 3462 | -99 | -99 |
| cache_creation_input_tokens | 46007 / 46007 | 21460 / 21460 | +24547 | +24547 |
| cache_read_input_tokens | 237049 / 237049 | 263077 / 263077 | -26028 | -26028 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 0/1 |
| secret-names-listed | 0/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
