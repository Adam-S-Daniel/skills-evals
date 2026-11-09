# Eval report: debug-github-workflows

- Timestamp: 20261109T214622Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261109T214256Z-199888; started 2026-11-09T21:46:22Z, ended 2026-11-09T21:48:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.1 to 0.1, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.64 over 2 call(s); agent $0.64, judge $0.00, guard $0.00; last agent call $0.23

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.4100 / 0.4100 |
| without_skill | 1 | 0 | 6/8 | skipped (objective-decided) | 0.2331 / 0.2331 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4100 / 0.4100 | 0.2331 / 0.2331 | +0.1769 | +0.1769 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 61724 / 61724 | 50830 / 50830 | +10894 | +10894 |
| input_tokens | 20 / 20 | 16 / 16 | +4 | +4 |
| output_tokens | 4389 / 4389 | 3714 / 3714 | +675 | +675 |
| cache_creation_input_tokens | 49912 / 49912 | 20421 / 20421 | +29491 | +29491 |
| cache_read_input_tokens | 332390 / 332390 | 261595 / 261595 | +70795 | +70795 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

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
