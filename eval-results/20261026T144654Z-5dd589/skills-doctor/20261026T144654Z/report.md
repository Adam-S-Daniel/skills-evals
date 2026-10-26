# Eval report: skills-doctor

- Timestamp: 20261026T144654Z
- Trials per arm: 3
- Run: billing subscription, runner workstation, location cloud, id 20261026T144654Z-5dd589; started 2026-10-26T14:46:54Z, ended 2026-10-26T14:51:01Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.58 to 0.63, seven_day 0.78 to 0.79, from 11 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | skipped (objective-decided) | 0.1337 / 0.4012 |
| without_skill | 3 | 0 | 3.7/5 | skipped (objective-decided) | 0.1198 / 0.3593 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1337 / 0.1336 | 0.1198 / 0.1193 | +0.0139 | +0.0143 |
| num_turns | 5.7 / 5 | 6 / 6 | -0.3 | -1 |
| duration_ms | 35741 / 34165 | 39683.7 / 36903 | -3942.7 | -2738 |
| input_tokens | 11.3 / 10 | 12 / 12 | -0.7 | -2 |
| output_tokens | 3339.7 / 3160 | 3354 / 3386 | -14.3 | -226 |
| cache_creation_input_tokens | 20206.3 / 17510 | 16380.3 / 16490 | +3826 | +1020 |
| cache_read_input_tokens | 194806.7 / 171597 | 206901.7 / 206046 | -12095 | -34449 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 2/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
