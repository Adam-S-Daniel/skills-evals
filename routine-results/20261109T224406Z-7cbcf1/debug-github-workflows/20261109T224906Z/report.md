# Eval report: debug-github-workflows

- Timestamp: 20261109T224906Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T224406Z-7cbcf1; started 2026-11-09T22:49:06Z, ended 2026-11-09T22:51:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.11 to 0.11, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.64 over 2 call(s); agent $0.64, judge $0.00, guard $0.00; last agent call $0.30

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.3341 / 0.3341 |
| without_skill | 1 | 0 | 6/8 | skipped (objective-decided) | 0.3036 / 0.3036 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3341 / 0.3341 | 0.3036 / 0.3036 | +0.0305 | +0.0305 |
| num_turns | 8 / 8 | 8 / 8 | 0 | 0 |
| duration_ms | 44505 / 44505 | 79905 / 79905 | -35400 | -35400 |
| input_tokens | 16 / 16 | 18 / 18 | -2 | -2 |
| output_tokens | 3313 / 3313 | 5090 / 5090 | -1777 | -1777 |
| cache_creation_input_tokens | 42675 / 42675 | 26119 / 26119 | +16556 | +16556 |
| cache_read_input_tokens | 272143 / 272143 | 314468 / 314468 | -42325 | -42325 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 1/1 | 0/1 |
| secret-names-listed | 1/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
