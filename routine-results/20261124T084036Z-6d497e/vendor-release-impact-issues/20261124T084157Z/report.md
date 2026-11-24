# Eval report: vendor-release-impact-issues

- Timestamp: 20261124T084157Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261124T084036Z-6d497e; started 2026-11-24T08:41:57Z, ended 2026-11-24T08:43:07Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.06 to 0.06, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 2 call(s); agent $0.32, judge $0.00, guard $0.00; last agent call $0.14
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.02 points of the weekly meter (0.02 to 0.03); Fable meter 0.00 points

## Fixture: closing-keywords (n=1)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.331 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped: the version with the skill passed more checks (6 of 6 vs 4 of 6) | 0.1839 / 0.1839 |
| without_skill | 1 | 0 | 4/6 | skipped: the version with the skill passed more checks (6 of 6 vs 4 of 6) | 0.1401 / 0.1401 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1839 / 0.1839 | 0.1401 / 0.1401 | +0.0438 | +0.0438 |
| num_turns | 8 / 8 | 4 / 4 | +4 | +4 |
| duration_ms | 35720 / 35720 | 23894 / 23894 | +11826 | +11826 |
| input_tokens | 14 / 14 | 8 / 8 | +6 | +6 |
| output_tokens | 4401 / 4401 | 3077 / 3077 | +1324 | +1324 |
| cache_creation_input_tokens | 29600 / 29600 | 24227 / 24227 | +5373 | +5373 |
| cache_read_input_tokens | 214223 / 214223 | 124087 / 124087 | +90136 | +90136 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 1/1 | 1/1 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 1/1 | 0/1 |
| quotes-in-issues-outside-blockquotes | 1/1 | 0/1 |
| settings-surface-named | 1/1 | 1/1 |
| tracking-doc-gained-4-4-0 | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
