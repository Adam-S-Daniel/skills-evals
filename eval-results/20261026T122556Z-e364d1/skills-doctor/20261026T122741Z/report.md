# Eval report: skills-doctor

- Timestamp: 20261026T122741Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T122556Z-e364d1; started 2026-10-26T12:27:41Z, ended 2026-10-26T12:32:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.31 to 0.34, seven_day 0.64 to 0.64, from 9 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | skipped (objective-decided) | 0.1369 / 0.4106 |
| without_skill | 3 | 0 | 3.7/5 | skipped (objective-decided) | 0.1296 / 0.3888 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1369 / 0.1207 | 0.1296 / 0.1285 | +0.0073 | -0.0077 |
| num_turns | 5.3 / 5 | 7 / 7 | -1.7 | -2 |
| duration_ms | 40455 / 40663 | 46985 / 46804 | -6530 | -6141 |
| input_tokens | 10.7 / 10 | 13.3 / 12 | -2.7 | -2 |
| output_tokens | 3717.7 / 3714 | 3624.7 / 3596 | +93 | +118 |
| cache_creation_input_tokens | 20386.7 / 16590 | 17426.7 / 17263 | +2960 | -673 |
| cache_read_input_tokens | 181298 / 172334 | 236245.7 / 209908 | -54947.7 | -37574 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 2/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
