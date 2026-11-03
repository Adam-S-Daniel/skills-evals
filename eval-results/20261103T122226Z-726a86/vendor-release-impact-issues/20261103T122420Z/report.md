# Eval report: vendor-release-impact-issues

- Timestamp: 20261103T122420Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T122226Z-726a86; started 2026-11-03T12:24:20Z, ended 2026-11-03T12:27:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.4 to 0.4, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.31 over 4 call(s); agent $0.85, judge $0.46, guard $0.00; last agent call $0.37

## Fixture: closed-duplicate (n=1)

- Prompt: Review ExampleCLI 4.2.0's release notes in `vendor/` against this repository (example-org/example-repo on GitHub; `gh` is authenticated for it) and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it, and list every change you considered, with what you decided for it, in `review.md`. Do not open real issues.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 9.0 (9.0 to 9.0, 1 judged) | 0.4845 / 0.4845 |
| without_skill | 1 | 0 | 6/6 | 9.0 (9.0 to 9.0, 1 judged) | 0.3672 / 0.3672 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4845 / 0.4845 | 0.3672 / 0.3672 | +0.1173 | +0.1173 |
| num_turns | 11 / 11 | 7 / 7 | +4 | +4 |
| duration_ms | 66835 / 66835 | 63639 / 63639 | +3196 | +3196 |
| input_tokens | 20 / 20 | 14 / 14 | +6 | +6 |
| output_tokens | 6395 / 6395 | 4335 / 4335 | +2060 | +2060 |
| cache_creation_input_tokens | 35559 / 35559 | 28971 / 28971 | +6588 | +6588 |
| cache_read_input_tokens | 360481 / 360481 | 243561 / 243561 | +116920 | +116920 |
| tool_errors | 2 / 2 | 0 / 0 | +2 | +2 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| searched-closed-issues-without-writing | 1/1 | 1/1 |
| closed-issue-57-linked | 1/1 | 1/1 |
| no-duplicate-of-57 | 1/1 | 1/1 |
| synced-skill-issue-drafted | 1/1 | 1/1 |
| seed-repo-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
