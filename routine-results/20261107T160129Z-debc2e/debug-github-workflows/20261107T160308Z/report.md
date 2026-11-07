# Eval report: debug-github-workflows

- Timestamp: 20261107T160308Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T160129Z-debc2e; started 2026-11-07T16:03:08Z, ended 2026-11-07T16:09:58Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.52 to 0.52, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.49 over 12 call(s); agent $1.63, judge $0.86, guard $0.00; last agent call $0.26

## Fixture: wrong-branch (n=3)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6.3/7 | 8.7 (8.2 to 9.0, 3 judged) | 0.2619 / 0.7856 |
| without_skill | 3 | 0 | 6.3/7 | 8.9 (8.8 to 9.0, 3 judged) | 0.2814 / 0.8442 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2619 / 0.2468 | 0.2814 / 0.2810 | -0.0195 | -0.0342 |
| num_turns | 6.3 / 6 | 7.7 / 8 | -1.3 | -2 |
| duration_ms | 38566.7 / 40417 | 53460 / 48950 | -14893.3 | -8533 |
| input_tokens | 12.7 / 12 | 15.3 / 16 | -2.7 | -4 |
| output_tokens | 2767 / 2673 | 3507.3 / 3611 | -740.3 | -938 |
| cache_creation_input_tokens | 20253.3 / 17807 | 19275 / 18995 | +978.3 | -1188 |
| cache_read_input_tokens | 222223.7 / 213039 | 284952.7 / 298253 | -62729 | -85214 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 2/3 | 2/3 |
| feature-comparison-read | 2/3 | 2/3 |
| main-differs-from-feature | 3/3 | 3/3 |
| merge-existing-fix | 3/3 | 3/3 |
| obsolete-command-diagnosed | 3/3 | 3/3 |
| repository-files-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
