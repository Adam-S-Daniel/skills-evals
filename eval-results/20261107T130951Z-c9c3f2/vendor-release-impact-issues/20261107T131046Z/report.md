# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T131046Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T130951Z-c9c3f2; started 2026-11-07T13:10:46Z, ended 2026-11-07T13:13:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.46 over 6 call(s); agent $0.29, judge $0.17, guard $0.00; last agent call $0.10

## Fixture: closing-keywords (n=3)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 4.7/6 | 5.4 (4.7 to 6.5, 3 judged) | 0.0962 / 0.2886 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.0962 / 0.0958 |
| num_turns | 5 / 5 |
| duration_ms | 35306 / 32186 |
| input_tokens | 10 / 10 |
| output_tokens | 2866.7 / 2882 |
| cache_creation_input_tokens | 12434 / 12294 |
| cache_read_input_tokens | 177755.7 / 177577 |
| tool_errors | 1.3 / 1 |

| Check (passed / scored) | without_skill |
| --- | --- |
| pr-body-and-commit-message-written | 3/3 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 2/3 |
| quotes-in-issues-outside-blockquotes | 0/3 |
| settings-surface-named | 3/3 |
| tracking-doc-gained-4-4-0 | 3/3 |
| seed-repo-unchanged | 3/3 |
