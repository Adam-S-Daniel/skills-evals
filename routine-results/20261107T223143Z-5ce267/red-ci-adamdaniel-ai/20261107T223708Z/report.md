# Eval report: red-ci-adamdaniel-ai

- Timestamp: 20261107T223708Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T223143Z-5ce267; started 2026-11-07T22:37:08Z, ended 2026-11-07T22:38:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.69 to 0.69, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 4 call(s); agent $0.22, judge $0.06, guard $0.00; last agent call $0.09

## Fixture: paths-required (n=1)

- Prompt: A docs-only PR is stuck BLOCKED waiting for the `test` check to report. Fix the workflow so it stops blocking those PRs but still only does the site work when the site changed.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 2/3 | 9.0 (9.0 to 9.0, 1 judged) | 0.1330 / 0.1330 |
| without_skill | 1 | 0 | 2/3 | 9.0 (9.0 to 9.0, 1 judged) | 0.0891 / 0.0891 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1330 / 0.1330 | 0.0891 / 0.0891 | +0.0439 | +0.0439 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 18866 / 18866 | 20973 / 20973 | -2107 | -2107 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1765 / 1765 | 1592 / 1592 | +173 | +173 |
| cache_creation_input_tokens | 24686 / 24686 | 13908 / 13908 | +10778 | +10778 |
| cache_read_input_tokens | 165858 / 165858 | 175776 / 175776 | -9918 | -9918 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| no-paths-filter | 1/1 | 1/1 |
| still-gated | 0/1 | 0/1 |
| site-untouched | 1/1 | 1/1 |
