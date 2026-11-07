# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T110923Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T110713Z-5c6d46; started 2026-11-07T11:09:23Z, ended 2026-11-07T11:11:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.41 to 0.41, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.60 over 4 call(s); agent $0.60, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: stamps-skip-quotes (n=2)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 4.5/5 | skipped (objective-decided) | 0.1703 / 0.3406 |
| without_skill | 2 | 0 | 3.5/5 | skipped (objective-decided) | 0.1303 / 0.2606 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1703 / 0.1703 | 0.1303 / 0.1303 | +0.0400 | +0.0400 |
| num_turns | 6 / 6 | 4 / 4 | +2 | +2 |
| duration_ms | 32964.5 / 32964.5 | 20144.5 / 20144.5 | +12820 | +12820 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 3725 / 3725 | 2329 / 2329 | +1396 | +1396 |
| cache_creation_input_tokens | 30027.5 / 30027.5 | 23726 / 23726 | +6301.5 | +6301.5 |
| cache_read_input_tokens | 129128 / 129128 | 121005.5 / 121005.5 | +8122.5 | +8122.5 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 2/2 | 0/2 |
| quoted-text-unstamped | 1/2 | 1/2 |
| titles-unstamped | 2/2 | 2/2 |
| prose-versions-stamped | 2/2 | 2/2 |
| seed-repo-unchanged | 2/2 | 2/2 |
