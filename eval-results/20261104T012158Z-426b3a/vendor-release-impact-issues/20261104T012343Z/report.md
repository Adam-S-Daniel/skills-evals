# Eval report: vendor-release-impact-issues

- Timestamp: 20261104T012343Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T012158Z-426b3a; started 2026-11-04T01:23:43Z, ended 2026-11-04T01:24:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.84, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.31 over 2 call(s); agent $0.31, judge $0.00, guard $0.00; last agent call $0.14

## Fixture: closing-keywords (n=1)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1707 / 0.1707 |
| without_skill | 1 | 0 | 4/6 | skipped (objective-decided) | 0.1438 / 0.1438 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1707 / 0.1707 | 0.1438 / 0.1438 | +0.0269 | +0.0269 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 30495 / 30495 | 28375 / 28375 | +2120 | +2120 |
| input_tokens | 12 / 12 | 8 / 8 | +4 | +4 |
| output_tokens | 3852 / 3852 | 3432 / 3432 | +420 | +420 |
| cache_creation_input_tokens | 28806 / 28806 | 24346 / 24346 | +4460 | +4460 |
| cache_read_input_tokens | 169393 / 169393 | 121096 / 121096 | +48297 | +48297 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 1/1 | 1/1 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 1/1 | 0/1 |
| quotes-in-issues-outside-blockquotes | 1/1 | 0/1 |
| settings-surface-named | 1/1 | 1/1 |
| tracking-doc-gained-4-4-0 | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
