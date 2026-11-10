# Eval report: debug-github-workflows

- Timestamp: 20261110T034435Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261110T034012Z-b5dbff; started 2026-11-10T03:44:35Z, ended 2026-11-10T03:46:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.16 to 0.17, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 4 call(s); agent $0.23, judge $0.08, guard $0.00; last agent call $0.08

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/8 | 8.8 (8.8 to 8.8, 1 judged) | 0.1522 / 0.1522 |
| without_skill | 1 | 0 | 8/8 | 8.2 (8.2 to 8.2, 1 judged) | 0.0818 / 0.0818 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1522 / 0.1522 | 0.0818 / 0.0818 | +0.0703 | +0.0703 |
| num_turns | 9 / 9 | 9 / 9 | 0 | 0 |
| duration_ms | 34056 / 34056 | 28681 / 28681 | +5375 | +5375 |
| input_tokens | 18 / 18 | 16 / 16 | +2 | +2 |
| output_tokens | 1893 / 1893 | 1896 / 1896 | -3 | -3 |
| cache_creation_input_tokens | 41368 / 41368 | 13867 / 13867 | +27501 | +27501 |
| cache_read_input_tokens | 297788 / 297788 | 281664 / 281664 | +16124 | +16124 |
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
