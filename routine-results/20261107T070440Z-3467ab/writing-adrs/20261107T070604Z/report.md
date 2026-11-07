# Eval report: writing-adrs

- Timestamp: 20261107T070604Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T070440Z-3467ab; started 2026-11-07T07:06:04Z, ended 2026-11-07T07:06:49Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 8/9 | skipped (objective-decided) | 0.1625 / 0.1625 |
| without_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.1215 / 0.1215 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1625 / 0.1625 | 0.1215 / 0.1215 | +0.0410 | +0.0410 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 23332 / 23332 | 18569 / 18569 | +4763 | +4763 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 3023 / 3023 | 1894 / 1894 | +1129 | +1129 |
| cache_creation_input_tokens | 29767 / 29767 | 22618 / 22618 | +7149 | +7149 |
| cache_read_input_tokens | 131704 / 131704 | 120610 / 120610 | +11094 | +11094 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| readme-bootstrapped-in-skill-shape | 1/1 | 0/1 |
| index-gained-a-row-for-0001 | 1/1 | 0/1 |
| adr-0001-sections-in-order | 1/1 | 0/1 |
| retry-sh-links-the-adr | 1/1 | 1/1 |
| readme-index-links-resolve | 1/1 | 1/1 |
| retry-sh-link-resolves | 1/1 | 1/1 |
| exactly-one-adr-file | 1/1 | 1/1 |
| nothing-else-touched | 1/1 | 1/1 |
| agents-md-gained-the-pointer | 0/1 | 0/1 |
