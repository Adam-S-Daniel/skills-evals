# Eval report: vendor-release-impact-issues

- Timestamp: 20261104T200452Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T200244Z-d8676d; started 2026-11-04T20:04:52Z, ended 2026-11-04T20:06:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.05 to 0.06, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 2 call(s); agent $0.33, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: closing-keywords (n=1)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1878 / 0.1878 |
| without_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.1467 / 0.1467 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1878 / 0.1878 | 0.1467 / 0.1467 | +0.0411 | +0.0411 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 49475 / 49475 | 28451 / 28451 | +21024 | +21024 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 4944 / 4944 | 3348 / 3348 | +1596 | +1596 |
| cache_creation_input_tokens | 30264 / 30264 | 24369 / 24369 | +5895 | +5895 |
| cache_read_input_tokens | 172548 / 172548 | 156877 / 156877 | +15671 | +15671 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 1/1 | 1/1 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 1/1 | 1/1 |
| quotes-in-issues-outside-blockquotes | 1/1 | 0/1 |
| settings-surface-named | 1/1 | 1/1 |
| tracking-doc-gained-4-4-0 | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
