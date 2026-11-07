# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T200441Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T195553Z-97f659; started 2026-11-07T20:04:41Z, ended 2026-11-07T20:08:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.66 to 0.67, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.98 over 6 call(s); agent $0.98, judge $0.00, guard $0.00; last agent call $0.16

## Fixture: closing-keywords (n=3)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | skipped (objective-decided) | 0.1807 / 0.5421 |
| without_skill | 3 | 0 | 4/6 | skipped (objective-decided) | 0.1461 / 0.4384 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1807 / 0.1810 | 0.1461 / 0.1405 | +0.0346 | +0.0405 |
| num_turns | 6.3 / 6 | 5.3 / 5 | +1 | +1 |
| duration_ms | 38855.7 / 37587 | 29791.7 / 27810 | +9064 | +9777 |
| input_tokens | 10.7 / 10 | 10.7 / 10 | 0 | 0 |
| output_tokens | 4668 / 4711 | 3169.7 / 2882 | +1498.3 | +1829 |
| cache_creation_input_tokens | 29941.3 / 29818 | 24370.7 / 23990 | +5570.7 | +5828 |
| cache_read_input_tokens | 142349 / 128987 | 169322.3 / 157117 | -26973.3 | -28130 |
| tool_errors | 0.3 / 0 | 0.7 / 1 | -0.3 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 3/3 | 3/3 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 3/3 | 0/3 |
| quotes-in-issues-outside-blockquotes | 3/3 | 0/3 |
| settings-surface-named | 3/3 | 3/3 |
| tracking-doc-gained-4-4-0 | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
