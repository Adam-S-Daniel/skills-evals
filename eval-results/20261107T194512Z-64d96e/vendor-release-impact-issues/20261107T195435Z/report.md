# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T195435Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T194512Z-64d96e; started 2026-11-07T19:54:35Z, ended 2026-11-07T19:57:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.66, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 6 call(s); agent $0.91, judge $0.00, guard $0.00; last agent call $0.13

## Fixture: stamps-skip-quotes (n=3)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | skipped (objective-decided) | 0.1747 / 0.5241 |
| without_skill | 3 | 0 | 3.3/5 | skipped (objective-decided) | 0.1270 / 0.3811 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1747 / 0.1733 | 0.1270 / 0.1252 | +0.0476 | +0.0481 |
| num_turns | 6.3 / 6 | 4 / 4 | +2.3 | +2 |
| duration_ms | 30671.3 / 31691 | 20091 / 19998 | +10580.3 | +11693 |
| input_tokens | 10.7 / 10 | 8 / 8 | +2.7 | +2 |
| output_tokens | 3933.7 / 3807 | 2080.3 / 1934 | +1853.3 | +1873 |
| cache_creation_input_tokens | 30227.7 / 30569 | 23528 / 23440 | +6699.7 | +7129 |
| cache_read_input_tokens | 144158.3 / 129368 | 121074 / 121155 | +23084.3 | +8213 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 3/3 | 1/3 |
| quoted-text-unstamped | 0/3 | 0/3 |
| titles-unstamped | 3/3 | 3/3 |
| prose-versions-stamped | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
