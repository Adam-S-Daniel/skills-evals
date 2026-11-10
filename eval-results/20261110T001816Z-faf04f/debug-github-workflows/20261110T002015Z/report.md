# Eval report: debug-github-workflows

- Timestamp: 20261110T002015Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T001816Z-faf04f; started 2026-11-10T00:20:15Z, ended 2026-11-10T00:22:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.13 to 0.13, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.74 over 4 call(s); agent $0.59, judge $0.15, guard $0.00; last agent call $0.26

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.3311 / 0.3311 |
| without_skill | 1 | 0 | 8/8 | 9.8 (9.8 to 9.8, 1 judged) | 0.2579 / 0.2579 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3311 / 0.3311 | 0.2579 / 0.2579 | +0.0732 | +0.0732 |
| num_turns | 8 / 8 | 9 / 9 | -1 | -1 |
| duration_ms | 34928 / 34928 | 61142 / 61142 | -26214 | -26214 |
| input_tokens | 14 / 14 | 20 / 20 | -6 | -6 |
| output_tokens | 3004 / 3004 | 4102 / 4102 | -1098 | -1098 |
| cache_creation_input_tokens | 44771 / 44771 | 20299 / 20299 | +24472 | +24472 |
| cache_read_input_tokens | 235310 / 235310 | 345260 / 345260 | -109950 | -109950 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 1/1 |
| secret-names-listed | 0/1 | 1/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
