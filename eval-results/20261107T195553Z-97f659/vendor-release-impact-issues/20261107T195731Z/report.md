# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T195731Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T195553Z-97f659; started 2026-11-07T19:57:31Z, ended 2026-11-07T20:04:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.66 to 0.66, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.45 over 6 call(s); agent $2.45, judge $0.00, guard $0.00; last agent call $0.34

## Fixture: closing-keywords (n=3)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | skipped (objective-decided) | 0.4680 / 1.4040 |
| without_skill | 3 | 0 | 4/6 | skipped (objective-decided) | 0.3486 / 1.0458 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4680 / 0.4646 | 0.3486 / 0.3387 | +0.1194 | +0.1259 |
| num_turns | 7.7 / 8 | 6.7 / 5 | +1 | +3 |
| duration_ms | 80858.3 / 77399 | 58749.3 / 56639 | +22109 | +20760 |
| input_tokens | 13.3 / 14 | 11.3 / 10 | +2 | +4 |
| output_tokens | 7626.7 / 7456 | 4968 / 4904 | +2658.7 | +2552 |
| cache_creation_input_tokens | 34277.3 / 33951 | 26501.3 / 26409 | +7776 | +7542 |
| cache_read_input_tokens | 206055.3 / 218971 | 186000.3 / 159750 | +20055 | +59221 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 3/3 | 3/3 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 3/3 | 0/3 |
| quotes-in-issues-outside-blockquotes | 3/3 | 0/3 |
| settings-surface-named | 3/3 | 3/3 |
| tracking-doc-gained-4-4-0 | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
