# Eval report: vendor-release-impact-issues

- Timestamp: 20261107T194708Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T194512Z-64d96e; started 2026-11-07T19:47:08Z, ended 2026-11-07T19:54:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.65, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.66 over 6 call(s); agent $2.66, judge $0.00, guard $0.00; last agent call $0.40

## Fixture: stamps-skip-quotes (n=3)

- Prompt: Review ExampleCLI's release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Every ExampleCLI version your issues mention must carry that release's publish time from `vendor/releases.json`. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/5 | skipped (objective-decided) | 0.4972 / 1.4917 |
| without_skill | 3 | 0 | 3/5 | skipped (objective-decided) | 0.3890 / 1.1670 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4972 / 0.4869 | 0.3890 / 0.3955 | +0.1082 | +0.0914 |
| num_turns | 8.7 / 9 | 5.3 / 5 | +3.3 | +4 |
| duration_ms | 84866 / 77586 | 60840.7 / 64861 | +24025.3 | +12725 |
| input_tokens | 16 / 16 | 10.7 / 10 | +5.3 | +6 |
| output_tokens | 7879.7 / 7364 | 6201 / 6468 | +1678.7 | +896 |
| cache_creation_input_tokens | 35740.7 / 35679 | 28711.3 / 28865 | +7029.3 | +6814 |
| cache_read_input_tokens | 268280 / 270473 | 176235.3 / 162621 | +92044.7 | +107852 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| quotes-kept-verbatim | 3/3 | 0/3 |
| quoted-text-unstamped | 1/3 | 3/3 |
| titles-unstamped | 3/3 | 0/3 |
| prose-versions-stamped | 3/3 | 3/3 |
| seed-repo-unchanged | 3/3 | 3/3 |
