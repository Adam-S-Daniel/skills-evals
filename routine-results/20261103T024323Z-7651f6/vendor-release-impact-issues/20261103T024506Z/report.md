# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T024506Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T024323Z-7651f6; started 2026-11-03T02:45:06Z, ended 2026-11-03T02:46:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.3 to 0.3, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 2 call(s); agent $0.32, judge $0.00, guard $0.00; last agent call $0.14

## Fixture: closing-keywords (n=1)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1819 / 0.1819 |
| without_skill | 1 | 0 | 4/6 | skipped (objective-decided) | 0.1394 / 0.1394 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1819 / 0.1819 | 0.1394 / 0.1394 | +0.0426 | +0.0426 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 38199 / 38199 | 25942 / 25942 | +12257 | +12257 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 4134 / 4134 | 2805 / 2805 | +1329 | +1329 |
| cache_creation_input_tokens | 29797 / 29797 | 23886 / 23886 | +5911 | +5911 |
| cache_read_input_tokens | 213908 / 213908 | 157704 / 157704 | +56204 | +56204 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 1/1 | 1/1 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 1/1 | 0/1 |
| quotes-in-issues-outside-blockquotes | 1/1 | 0/1 |
| settings-surface-named | 1/1 | 1/1 |
| tracking-doc-gained-4-4-0 | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
