# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T154834Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T154000Z-03a2b4; started 2026-11-07T15:48:34Z, ended 2026-11-07T15:52:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.5 to 0.51, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 6 call(s); agent $1.01, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: closing-keywords (n=3)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | skipped (objective-decided) | 0.1938 / 0.5813 |
| without_skill | 3 | 0 | 4.7/6 | skipped (objective-decided) | 0.1442 / 0.4326 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1938 / 0.1888 | 0.1442 / 0.1451 | +0.0496 | +0.0437 |
| num_turns | 8 / 7 | 4.7 / 5 | +3.3 | +2 |
| duration_ms | 48806.3 / 45684 | 31663 / 33685 | +17143.3 | +11999 |
| input_tokens | 14 / 12 | 9.3 / 10 | +4.7 | +2 |
| output_tokens | 4998.7 / 4918 | 3290.3 / 3246 | +1708.3 | +1672 |
| cache_creation_input_tokens | 30582.7 / 30566 | 24196.7 / 24224 | +6386 | +6342 |
| cache_read_input_tokens | 214077 / 173339 | 144923.3 / 156864 | +69153.7 | +16475 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 3/3 | 3/3 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 3/3 | 2/3 |
| quotes-in-issues-outside-blockquotes | 3/3 | 0/3 |
| settings-surface-named | 3/3 | 3/3 |
| tracking-doc-gained-4-4-0 | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
