# Eval report: debug-github-workflows

- Timestamp: 20261107T115214Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T115036Z-cf7555; started 2026-11-07T11:52:14Z, ended 2026-11-07T11:53:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.42 to 0.42, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.37 over 4 call(s); agent $0.37, judge $0.00, guard $0.00; last agent call $0.08

## Fixture: wrong-branch (n=2)

- Prompt: CI is red on main. Investigate the root cause. Do not edit files or change remote state. Explain your findings and next steps.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 6/7 | skipped (objective-decided) | 0.1064 / 0.2129 |
| without_skill | 2 | 0 | 4.5/7 | skipped (objective-decided) | 0.0778 / 0.1555 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1064 / 0.1064 | 0.0778 / 0.0778 | +0.0287 | +0.0287 |
| num_turns | 5.5 / 5.5 | 4.5 / 4.5 | +1 | +1 |
| duration_ms | 20944 / 20944 | 16726.5 / 16726.5 | +4217.5 | +4217.5 |
| input_tokens | 10 / 10 | 9 / 9 | +1 | +1 |
| output_tokens | 1466.5 / 1466.5 | 1266 / 1266 | +200.5 | +200.5 |
| cache_creation_input_tokens | 18839 / 18839 | 12537.5 / 12537.5 | +6301.5 | +6301.5 |
| cache_read_input_tokens | 163890 / 163890 | 149398.5 / 149398.5 | +14491.5 | +14491.5 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| failing-log-read-without-writes | 1/2 | 1/2 |
| feature-comparison-read | 2/2 | 0/2 |
| main-differs-from-feature | 2/2 | 1/2 |
| merge-existing-fix | 1/2 | 1/2 |
| obsolete-command-diagnosed | 2/2 | 2/2 |
| repository-files-unchanged | 2/2 | 2/2 |
| instrument-unchanged | 2/2 | 2/2 |
