# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T112640Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T112508Z-22e3e0; started 2026-11-07T11:26:40Z, ended 2026-11-07T11:29:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.67 over 4 call(s); agent $0.67, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: closing-keywords (n=2)

- Prompt: Review ExampleCLI 4.4.0's release notes in `vendor/` against this repository and prepare its tracking pull request, without committing, pushing or opening anything: add the review to `docs/vendor-tracking.md`, draft one issue per affected change as `issues/<NN>-<slug>.md` (the issue title as the first line, `# <title>`, and the body below it), and write the pull request's description to `pr-body.md` and its commit message to `commit-message.txt`.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 5.5/6 | skipped (objective-decided) | 0.1886 / 0.3773 |
| without_skill | 2 | 0 | 4.5/6 | skipped (objective-decided) | 0.1450 / 0.2899 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1886 / 0.1886 | 0.1450 / 0.1450 | +0.0437 | +0.0437 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 39826.5 / 39826.5 | 29149.5 / 29149.5 | +10677 | +10677 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 5067 / 5067 | 3238 / 3238 | +1829 | +1829 |
| cache_creation_input_tokens | 30209 / 30209 | 24213 / 24213 | +5996 | +5996 |
| cache_read_input_tokens | 171190.5 / 171190.5 | 156995 / 156995 | +14195.5 | +14195.5 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| pr-body-and-commit-message-written | 2/2 | 2/2 |
| pr-body-and-commit-free-of-closing-keywords-and-quotes | 1/2 | 1/2 |
| quotes-in-issues-outside-blockquotes | 2/2 | 0/2 |
| settings-surface-named | 2/2 | 2/2 |
| tracking-doc-gained-4-4-0 | 2/2 | 2/2 |
| seed-repo-unchanged | 2/2 | 2/2 |
