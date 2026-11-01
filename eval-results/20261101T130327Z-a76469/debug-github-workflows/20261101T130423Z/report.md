# Eval report: debug-github-workflows

- Timestamp: 20261101T130423Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261101T130327Z-a76469; started 2026-11-01T13:04:23Z, ended 2026-11-01T13:06:15Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.84 to 0.85, from 7 snapshots

## Fixture: wrong-branch (n=1)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/7 | 9.0 (9.0 to 9.0, 1 judged) | 0.4110 / 0.4110 |
| without_skill | 1 | 0 | 7/7 | 8.8 (8.8 to 8.8, 1 judged) | 0.1869 / 0.1869 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4110 / 0.4110 | 0.1869 / 0.1869 | +0.2241 | +0.2241 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 28880 / 28880 | 27110 / 27110 | +1770 | +1770 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 2087 / 2087 | 1783 / 1783 | +304 | +304 |
| cache_creation_input_tokens | 41307 / 41307 | 13334 / 13334 | +27973 | +27973 |
| cache_read_input_tokens | 193285 / 193285 | 221871 / 221871 | -28586 | -28586 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/1 | 1/1 |
| feature-comparison-read | 0/1 | 1/1 |
| main-differs-from-feature | 1/1 | 1/1 |
| merge-existing-fix | 1/1 | 1/1 |
| obsolete-command-diagnosed | 1/1 | 1/1 |
| repository-files-unchanged | 1/1 | 1/1 |
| instrument-unchanged | 1/1 | 1/1 |
