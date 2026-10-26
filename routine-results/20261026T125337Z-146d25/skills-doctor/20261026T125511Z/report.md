# Eval report: skills-doctor

- Timestamp: 20261026T125511Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T125337Z-146d25; started 2026-10-26T12:55:11Z, ended 2026-10-26T12:59:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.42 to 0.44, seven_day 0.66 to 0.66, from 7 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | skipped (objective-decided) | 0.1346 / 0.4037 |
| without_skill | 3 | 0 | 3.7/5 | skipped (objective-decided) | 0.1186 / 0.3557 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1346 / 0.1253 | 0.1186 / 0.1163 | +0.0160 | +0.0090 |
| num_turns | 5.7 / 6 | 5.7 / 6 | 0 | 0 |
| duration_ms | 46791 / 40806 | 37498.3 / 35381 | +9292.7 | +5425 |
| input_tokens | 11.3 / 12 | 11.3 / 12 | 0 | 0 |
| output_tokens | 3347.3 / 3384 | 3299 / 3254 | +48.3 | +130 |
| cache_creation_input_tokens | 20429.3 / 17282 | 16456.3 / 16294 | +3973 | +988 |
| cache_read_input_tokens | 193669.7 / 209259 | 197137 / 209896 | -3467.3 | -637 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 2/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
