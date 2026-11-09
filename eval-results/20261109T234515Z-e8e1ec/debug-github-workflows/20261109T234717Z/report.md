# Eval report: debug-github-workflows

- Timestamp: 20261109T234717Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T234515Z-e8e1ec; started 2026-11-09T23:47:17Z, ended 2026-11-09T23:49:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 4 call(s); agent $0.53, judge $0.15, guard $0.00; last agent call $0.22

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 9.0 (9.0 to 9.0, 1 judged) | 0.3145 / 0.3145 |
| without_skill | 1 | 0 | 6/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.2202 / 0.2202 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3145 / 0.3145 | 0.2202 / 0.2202 | +0.0944 | +0.0944 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 30720 / 30720 | 53424 / 53424 | -22704 | -22704 |
| input_tokens | 12 / 12 | 16 / 16 | -4 | -4 |
| output_tokens | 2621 / 2621 | 3309 / 3309 | -688 | -688 |
| cache_creation_input_tokens | 44580 / 44580 | 19262 / 19262 | +25318 | +25318 |
| cache_read_input_tokens | 195828 / 195828 | 256815 / 256815 | -60987 | -60987 |
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
