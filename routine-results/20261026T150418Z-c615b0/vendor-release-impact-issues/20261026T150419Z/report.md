# Eval report: vendor-release-impact-issues

- Timestamp: 20261026T150419Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T150418Z-c615b0; started 2026-10-26T15:04:19Z, ended 2026-10-26T15:10:14Z
- Budget stop: per_run_cap (limit 0.015, weekly meter 0.83, moved 0.02); no trial or judge call started after it
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.74 to 0.79, seven_day 0.81 to 0.83, from 10 snapshots

## Fixture: vendor-release-impact-issues (n=3)

- Prompt: Review ExampleCLI's recent release notes in `vendor/` against this repository and draft the GitHub issues you would open for the changes that affect it. Write each issue to `issues/<NN>-<slug>.md`, with the issue title as the first line (`# <title>`) and the body below it. Do not open real issues.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 7/7 | skipped (objective-decided) | 0.4151 / 1.2453 |
| without_skill | 3 | 1 | 4.5/7 | skipped (objective-decided) | 0.2137 / 0.4273; 1 unknown |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4151 / 0.4099 | 0.2137 / 0.2137 (2 of 3) | +0.2014 | +0.1963 |
| num_turns | 8.3 / 9 | 5 / 5 (2 of 3) | +3.3 | +4 |
| duration_ms | 84145.7 / 85027 | 44599.5 / 44599.5 (2 of 3) | +39546.2 | +40427.5 |
| input_tokens | 14.7 / 16 | 10 / 10 (2 of 3) | +4.7 | +6 |
| output_tokens | 7652.7 / 7452 | 3370.5 / 3370.5 (2 of 3) | +4282.2 | +4081.5 |
| cache_creation_input_tokens | 25250.7 / 24795 | 13794.5 / 13794.5 (2 of 3) | +11456.2 | +11000.5 |
| cache_read_input_tokens | 298784 / 327142 | 177976 / 177976 (2 of 3) | +120808 | +149166 |
| tool_errors | 1 / 1 | 1 / 1 (2 of 3) | 0 | 0 |

Errored trials are counted in n and excluded from score means; known costs from all trials are counted:

- without_skill trial 3: budget_stop: trial not started: the run reached its budget stop (per_run_cap); see usage.budget_stop

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| at-least-one-issue-drafted | 3/3 | 2/2 |
| publish-times-source-and-version-bound | 3/3 | 0/2 |
| pr-refs-fenced-not-quoted | 3/3 | 2/2 |
| no-upstream-issue-backlink | 3/3 | 1/2 |
| no-placeholder-in-title | 3/3 | 0/2 |
| seed-repo-unchanged | 3/3 | 2/2 |
| hook-matcher-surface-named | 3/3 | 2/2 |
