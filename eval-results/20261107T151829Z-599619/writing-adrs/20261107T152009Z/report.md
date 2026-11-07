# Eval report: writing-adrs

- Timestamp: 20261107T152009Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T151829Z-599619; started 2026-11-07T15:20:09Z, ended 2026-11-07T15:26:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.49 to 0.49, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.15 over 6 call(s); agent $2.15, judge $0.00, guard $0.00; last agent call $0.31

## Fixture: bootstrap (n=3)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 9/9 | skipped (objective-decided) | 0.3771 / 1.1312 |
| without_skill | 3 | 0 | 5/9 | skipped (objective-decided) | 0.3386 / 1.0157 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3771 / 0.3791 | 0.3386 / 0.3313 | +0.0385 | +0.0478 |
| num_turns | 8 / 8 | 9.3 / 9 | -1.3 | -1 |
| duration_ms | 54631 / 53789 | 62765 / 73830 | -8134 | -20041 |
| input_tokens | 16 / 16 | 15.3 / 14 | +0.7 | +2 |
| output_tokens | 4303.7 / 4194 | 4051.3 / 3890 | +252.3 | +304 |
| cache_creation_input_tokens | 30084.7 / 30201 | 25623 / 25725 | +4461.7 | +4476 |
| cache_read_input_tokens | 251330.3 / 250447 | 262408.7 / 238014 | -11078.3 | +12433 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 3/3 | 0/3 |
| index-gained-a-row-for-0001 | 3/3 | 0/3 |
| adr-0001-sections-in-order | 3/3 | 0/3 |
| retry-sh-links-the-adr | 3/3 | 3/3 |
| readme-index-links-resolve | 3/3 | 3/3 |
| retry-sh-link-resolves | 3/3 | 3/3 |
| exactly-one-adr-file | 3/3 | 3/3 |
| nothing-else-touched | 3/3 | 3/3 |
| agents-md-gained-the-pointer | 3/3 | 0/3 |
