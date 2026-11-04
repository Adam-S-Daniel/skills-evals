# Eval report: vendor-release-impact-issues

- Timestamp: 20261104T040306Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T040130Z-30d64f; started 2026-11-04T04:03:06Z, ended 2026-11-04T04:04:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.9 to 0.91, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 2 call(s); agent $0.33, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: closing-keywords (n=1)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1708 / 0.1708 |
| without_skill | 1 | 0 | 4/6 | skipped (objective-decided) | 0.1550 / 0.1550 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1708 / 0.1708 | 0.1550 / 0.1550 | +0.0158 | +0.0158 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 31561 / 31561 | 34048 / 34048 | -2487 | -2487 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3927 / 3927 | 3583 / 3583 | +344 | +344 |
| cache_creation_input_tokens | 29632 / 29632 | 24921 / 24921 | +4711 | +4711 |
| cache_read_input_tokens | 129384 / 129384 | 194446 / 194446 | -65062 | -65062 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 1/1 | 1/1 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 1/1 | 0/1 |
| quotes-in-issues-outside-blockquotes | 1/1 | 0/1 |
| settings-surface-named | 1/1 | 1/1 |
| tracking-doc-gained-4-4-0 | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
