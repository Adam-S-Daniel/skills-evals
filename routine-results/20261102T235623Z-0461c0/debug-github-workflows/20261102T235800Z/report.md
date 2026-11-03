# Eval report: debug-github-workflows

- Timestamp: 20261102T235800Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261102T235623Z-0461c0; started 2026-11-02T23:58:00Z, ended 2026-11-02T23:59:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.26 to 0.26, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.42 over 4 call(s); agent $0.25, judge $0.16, guard $0.00; last agent call $0.10

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.1481 / 0.1481 |
| without_skill | 1 | 0 | 6/8 | 7.4 (7.4 to 7.4, 1 judged) | 0.1042 / 0.1042 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1481 / 0.1481 | 0.1042 / 0.1042 | +0.0440 | +0.0440 |
| num_turns | 10 / 10 | 9 / 9 | +1 | +1 |
| duration_ms | 27643 / 27643 | 28421 / 28421 | -778 | -778 |
| input_tokens | 16 / 16 | 16 / 16 | 0 | 0 |
| output_tokens | 1885 / 1885 | 1765 / 1765 | +120 | +120 |
| cache_creation_input_tokens | 25561 / 25561 | 14592 / 14592 | +10969 | +10969 |
| cache_read_input_tokens | 270201 / 270201 | 281080 / 281080 | -10879 | -10879 |
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
