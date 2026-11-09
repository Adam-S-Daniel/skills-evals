# Eval report: debug-github-workflows

- Timestamp: 20261109T234904Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T234515Z-e8e1ec; started 2026-11-09T23:49:04Z, ended 2026-11-09T23:50:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.25, judge $0.08, guard $0.00; last agent call $0.09

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.1594 / 0.1594 |
| without_skill | 1 | 0 | 8/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.0898 / 0.0898 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1594 / 0.1594 | 0.0898 / 0.0898 | +0.0696 | +0.0696 |
| num_turns | 12 / 12 | 8 / 8 | +4 | +4 |
| duration_ms | 40841 / 40841 | 26253 / 26253 | +14588 | +14588 |
| input_tokens | 20 / 20 | 16 / 16 | +4 | +4 |
| output_tokens | 2440 / 2440 | 2008 / 2008 | +432 | +432 |
| cache_creation_input_tokens | 40562 / 40562 | 16282 / 16282 | +24280 | +24280 |
| cache_read_input_tokens | 335110 / 335110 | 289712 / 289712 | +45398 | +45398 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/1 | 1/1 |
| secret-names-listed | 1/1 | 1/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
