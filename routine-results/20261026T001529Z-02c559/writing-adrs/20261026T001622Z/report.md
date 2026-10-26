# Eval report: writing-adrs

- Timestamp: 20261026T001622Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T001529Z-02c559; started 2026-10-26T00:16:22Z, ended 2026-10-26T00:22:10Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.12 to 0.14, seven_day 0.5 to 0.51, from 8 snapshots

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.3805 / 1.1414 |
| without_skill | 3 | 0 | 3.7/9 | skipped (objective-decided) | 0.3289 / 0.9868 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3805 / 0.3788 | 0.3289 / 0.3228 | +0.0515 | +0.0560 |
| num_turns | 9.7 / 10 | 7.7 / 8 | +2 | +2 |
| duration_ms | 55761.7 / 54752 | 56266 / 51552 | -504.3 | +3200 |
| input_tokens | 17.3 / 18 | 14 / 14 | +3.3 | +4 |
| output_tokens | 4052.3 / 3994 | 4033.3 / 3890 | +19 | +104 |
| cache_creation_input_tokens | 29556 / 29229 | 25241 / 25199 | +4315 | +4030 |
| cache_read_input_tokens | 314431.3 / 325441 | 231364.7 / 231196 | +83066.7 | +94245 |
| tool_errors | 0.7 / 1 | 0.7 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 1/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 1/3 |
| nothing-else-touched | 3/3 | 3/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
