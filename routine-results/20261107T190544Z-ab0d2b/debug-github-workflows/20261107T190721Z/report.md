# Eval report: debug-github-workflows

- Timestamp: 20261107T190721Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T190544Z-ab0d2b; started 2026-11-07T19:07:21Z, ended 2026-11-07T19:14:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.63 to 0.63, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.39 over 12 call(s); agent $1.50, judge $0.90, guard $0.00; last agent call $0.23

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.3/7 | 8.3 (8.0 to 8.8, 3 judged) | 0.2755 / 0.8266 |
| without_skill | 3 | 0 | 6.3/7 | 8.7 (8.4 to 9.0, 3 judged) | 0.2233 / 0.6700 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2755 / 0.2683 | 0.2233 / 0.2186 | +0.0522 | +0.0497 |
| num_turns | 6.7 / 7 | 6.3 / 6 | +0.3 | +1 |
| duration_ms | 38653 / 36909 | 39942 / 37972 | -1289 | -1063 |
| input_tokens | 13.3 / 14 | 12 / 12 | +1.3 | +2 |
| output_tokens | 2857.3 / 2756 | 2572.7 / 2497 | +284.7 | +259 |
| cache_creation_input_tokens | 21330 / 19234 | 16189.3 / 16184 | +5140.7 | +3050 |
| cache_read_input_tokens | 238518.3 / 244137 | 211650.7 / 211897 | +26867.7 | +32240 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/3 | 3/3 |
| feature-comparison-read | 1/3 | 1/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 2/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
