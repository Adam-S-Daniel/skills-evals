# Eval report: writing-adrs

- Timestamp: 20261107T042354Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T042033Z-15d392; started 2026-11-07T04:23:54Z, ended 2026-11-07T04:25:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.84 over 2 call(s); agent $0.84, judge $0.00, guard $0.00; last agent call $0.32

## Fixture: bootstrap (n=1)

- Prompt: Record the retry-policy decision properly.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 9/9 | skipped (objective-decided) | 0.5149 / 0.5149 |
| without_skill | 1 | 0 | 5/9 | skipped (objective-decided) | 0.3211 / 0.3211 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5149 / 0.5149 | 0.3211 / 0.3211 | +0.1938 | +0.1938 |
| num_turns | 11 / 11 | 9 / 9 | +2 | +2 |
| duration_ms | 50914 / 50914 | 38995 / 38995 | +11919 | +11919 |
| input_tokens | 18 / 18 | 14 / 14 | +4 | +4 |
| output_tokens | 4812 / 4812 | 3788 / 3788 | +1024 | +1024 |
| cache_creation_input_tokens | 45276 / 45276 | 24815 / 24815 | +20461 | +20461 |
| cache_read_input_tokens | 281679 / 281679 | 233673 / 233673 | +48006 | +48006 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

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
| agents-md-gained-the-pointer | 1/1 | 0/1 |
