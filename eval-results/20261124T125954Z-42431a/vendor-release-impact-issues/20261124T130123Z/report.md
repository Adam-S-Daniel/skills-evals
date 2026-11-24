# Eval report: vendor-release-impact-issues

- Timestamp: 20261124T130123Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261124T125954Z-42431a; started 2026-11-24T13:01:23Z, ended 2026-11-24T13:02:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.08 to 0.08, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.35 over 2 call(s); agent $0.35, judge $0.00, guard $0.00; last agent call $0.15
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.04); Fable meter 0.00 points

## Fixture: closing-keywords (n=1)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped: the version with the skill passed more checks (6 of 6 vs 4 of 6) | 0.2052 / 0.2052 |
| without_skill | 1 | 0 | 4/6 | skipped: the version with the skill passed more checks (6 of 6 vs 4 of 6) | 0.1477 / 0.1477 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2052 / 0.2052 | 0.1477 / 0.1477 | +0.0575 | +0.0575 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 48207 / 48207 | 29046 / 29046 | +19161 | +19161 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 5361 / 5361 | 3270 / 3270 | +2091 | +2091 |
| cache_creation_input_tokens | 32401 / 32401 | 24667 / 24667 | +7734 | +7734 |
| cache_read_input_tokens | 219571 / 219571 | 163607 / 163607 | +55964 | +55964 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 1/1 | 1/1 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 1/1 | 0/1 |
| quotes-in-issues-outside-blockquotes | 1/1 | 0/1 |
| settings-surface-named | 1/1 | 1/1 |
| tracking-doc-gained-4-4-0 | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
