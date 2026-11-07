# Eval report: github-actions-repo-settings

- Timestamp: 20261107T160652Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T160509Z-d408f6; started 2026-11-07T16:06:52Z, ended 2026-11-07T16:12:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.52 to 0.53, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.21 over 12 call(s); agent $1.53, judge $0.68, guard $0.00; last agent call $0.21

## Fixture: drift-diagnosis (n=3)

- Prompt: Tell me whether the two repositories match the declared settings and what to do about any differences. Inspect their current settings; do not make changes. Give your final answer as one neutral pipe-separated line per finding in this order: repository | setting or ruleset | observed | desired | recommendation. Use the setting keys and ruleset names from the sources, include a numeric ID for each ruleset you discuss, and add one overall line for each repository in the same format. In each overall line, use match or drift in the observed field.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3/9 | 7.6 (7.3 to 7.7, 3 judged) | 0.2932 / 0.8797 |
| without_skill | 3 | 0 | 4/9 | 8.0 (7.3 to 8.7, 3 judged) | 0.2170 / 0.6511 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2932 / 0.2829 | 0.2170 / 0.2091 | +0.0762 | +0.0737 |
| num_turns | 7.3 / 7 | 5.3 / 5 | +2 | +2 |
| duration_ms | 42668.7 / 37693 | 36043 / 37144 | +6625.7 | +549 |
| input_tokens | 14.7 / 14 | 10.7 / 10 | +4 | +4 |
| output_tokens | 2622.7 / 2579 | 2756.7 / 2753 | -134 | -174 |
| cache_creation_input_tokens | 24362 / 21475 | 15610.3 / 15064 | +8751.7 | +6411 |
| cache_read_input_tokens | 229180 / 216043 | 184874.3 / 172011 | +44305.7 | +44032 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| alpha-sha-drift | 0/3 | 1/3 |
| alpha-unmanaged-ruleset-facts | 0/3 | 0/3 |
| alpha-engine-does-not-delete | 0/3 | 0/3 |
| beta-overall-match | 0/3 | 0/3 |
| alpha-live-settings-read | 0/3 | 1/3 |
| beta-live-settings-read | 0/3 | 1/3 |
| no-write-attempted | 3/3 | 3/3 |
| config-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
