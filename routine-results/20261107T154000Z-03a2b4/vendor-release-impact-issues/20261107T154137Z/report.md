# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T154137Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T154000Z-03a2b4; started 2026-11-07T15:41:37Z, ended 2026-11-07T15:48:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.5, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.47 over 6 call(s); agent $2.47, judge $0.00, guard $0.00; last agent call $0.37

## Fixture: closing-keywords (n=3)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | skipped (objective-decided) | 0.4760 / 1.4280 |
| without_skill | 3 | 0 | 4.3/6 | skipped (objective-decided) | 0.3479 / 1.0438 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4760 / 0.4656 | 0.3479 / 0.3467 | +0.1281 | +0.1189 |
| num_turns | 8.3 / 8 | 5.3 / 6 | +3 | +2 |
| duration_ms | 84129 / 80003 | 50967.3 / 51074 | +33161.7 | +28929 |
| input_tokens | 14.7 / 14 | 10.7 / 12 | +4 | +2 |
| output_tokens | 7620 / 7287 | 4930 / 4944 | +2690 | +2343 |
| cache_creation_input_tokens | 34543 / 34433 | 26814.7 / 26448 | +7728.3 | +7985 |
| cache_read_input_tokens | 235913.3 / 221855 | 173807.3 / 199684 | +62106 | +22171 |
| tool_errors | 0.7 / 1 | 0.3 / 0 | +0.3 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 3/3 | 3/3 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 3/3 | 1/3 |
| quotes-in-issues-outside-blockquotes | 3/3 | 0/3 |
| settings-surface-named | 3/3 | 3/3 |
| tracking-doc-gained-4-4-0 | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
