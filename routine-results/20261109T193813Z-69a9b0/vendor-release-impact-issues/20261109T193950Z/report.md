# Eval report: vendor-release-impact-issues

- Timestamp: 20261109T193950Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261109T193813Z-69a9b0; started 2026-11-09T19:39:50Z, ended 2026-11-09T19:42:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.07 to 0.07, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 6 call(s); agent $0.67, judge $0.34, guard $0.00; last agent call $0.18

## Fixture: closing-keywords (n=3)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4/6 | 5.2 (4.7 to 6.2, 3 judged) | 0.2227 / 0.6681 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2227 / 0.1820 |
| num_turns | 4.7 / 5 |
| duration_ms | 39623.3 / 38646 |
| input_tokens | 9.3 / 10 |
| output_tokens | 3922 / 3956 |
| cache_creation_input_tokens | 22487.7 / 13281 |
| cache_read_input_tokens | 158920.3 / 181655 |
| tool_errors | 1.3 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| pr-body-and-commit-message-written | 3/3 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 0/3 |
| quotes-in-issues-outside-blockquotes | 0/3 |
| settings-surface-named | 3/3 |
| tracking-doc-gained-4-4-0 | 3/3 |
| seed-repo-unchanged | 3/3 |
