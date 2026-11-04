# Eval report: debug-github-workflows

- Timestamp: 20261104T005808Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T005623Z-592a85; started 2026-11-04T00:58:08Z, ended 2026-11-04T00:59:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.83 to 0.83, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 2 call(s); agent $0.26, judge $0.00, guard $0.00; last agent call $0.11

## Fixture: secret-name (n=1)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/8 | skipped (objective-decided) | 0.1520 / 0.1520 |
| without_skill | 1 | 0 | 6/8 | skipped (objective-decided) | 0.1102 / 0.1102 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1520 / 0.1520 | 0.1102 / 0.1102 | +0.0417 | +0.0417 |
| num_turns | 10 / 10 | 8 / 8 | +2 | +2 |
| duration_ms | 38864 / 38864 | 26313 / 26313 | +12551 | +12551 |
| input_tokens | 18 / 18 | 16 / 16 | +2 | +2 |
| output_tokens | 2185 / 2185 | 1853 / 1853 | +332 | +332 |
| cache_creation_input_tokens | 24835 / 24835 | 15911 / 15911 | +8924 | +8924 |
| cache_read_input_tokens | 307273 / 307273 | 280127 / 280127 | +27146 | +27146 |
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
