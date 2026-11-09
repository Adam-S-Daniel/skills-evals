# Eval report: debug-github-workflows

- Timestamp: 20261109T231430Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T231028Z-940c26; started 2026-11-09T23:14:30Z, ended 2026-11-09T23:16:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.12 to 0.12, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.23, judge $0.08, guard $0.00; last agent call $0.09

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 8.6 (8.6 to 8.6, 1 judged) | 0.1454 / 0.1454 |
| without_skill | 1 | 0 | 8/8 | 7.4 (7.4 to 7.4, 1 judged) | 0.0882 / 0.0882 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1454 / 0.1454 | 0.0882 / 0.0882 | +0.0572 | +0.0572 |
| num_turns | 9 / 9 | 10 / 10 | -1 | -1 |
| duration_ms | 37941 / 37941 | 55880 / 55880 | -17939 | -17939 |
| input_tokens | 16 / 16 | 18 / 18 | -2 | -2 |
| output_tokens | 1977 / 1977 | 2024 / 2024 | -47 | -47 |
| cache_creation_input_tokens | 39995 / 39995 | 14366 / 14366 | +25629 | +25629 |
| cache_read_input_tokens | 256467 / 256467 | 320012 / 320012 | -63545 | -63545 |
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
