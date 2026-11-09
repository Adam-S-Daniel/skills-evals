# Eval report: debug-github-workflows

- Timestamp: 20261109T200120Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T195911Z-1a8fd4; started 2026-11-09T20:01:20Z, ended 2026-11-09T20:02:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.08, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.52 over 2 call(s); agent $0.52, judge $0.00, guard $0.00; last agent call $0.19

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 7/8 | skipped (objective-decided) | 0.3298 / 0.3298 |
| without_skill | 1 | 0 | 6/8 | skipped (objective-decided) | 0.1919 / 0.1919 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3298 / 0.3298 | 0.1919 / 0.1919 | +0.1380 | +0.1380 |
| num_turns | 9 / 9 | 6 / 6 | +3 | +3 |
| duration_ms | 37251 / 37251 | 33866 / 33866 | +3385 | +3385 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3059 / 3059 | 2756 / 2756 | +303 | +303 |
| cache_creation_input_tokens | 44412 / 44412 | 18729 / 18729 | +25683 | +25683 |
| cache_read_input_tokens | 232661 / 232661 | 215186 / 215186 | +17475 | +17475 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/1 | 0/1 |
| secret-names-listed | 1/1 | 0/1 |
| workflow-reads-the-existing-secret | 1/1 | 1/1 |
| workflows-still-parse | 1/1 | 1/1 |
| permissions-stay-read-only | 1/1 | 1/1 |
| reply-names-both-secrets | 1/1 | 1/1 |
| everything-else-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
