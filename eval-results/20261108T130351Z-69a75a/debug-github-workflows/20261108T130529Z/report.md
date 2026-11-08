# Eval report: debug-github-workflows

- Timestamp: 20261108T130529Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T130351Z-69a75a; started 2026-11-08T13:05:29Z, ended 2026-11-08T13:07:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.76 to 0.76, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 4 call(s); agent $0.59, judge $0.32, guard $0.00; last agent call $0.26

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.3253 / 0.3253 |
| without_skill | 1 | 0 | 7/7 | 8.0 (8.0 to 8.0, 1 judged) | 0.2618 / 0.2618 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3253 / 0.3253 | 0.2618 / 0.2618 | +0.0635 | +0.0635 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 43605 / 43605 | 39290 / 39290 | +4315 | +4315 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 2833 / 2833 | 3214 / 3214 | -381 | -381 |
| cache_creation_input_tokens | 28452 / 28452 | 18291 / 18291 | +10161 | +10161 |
| cache_read_input_tokens | 204873 / 204873 | 255862 / 255862 | -50989 | -50989 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 0/1 | 1/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
