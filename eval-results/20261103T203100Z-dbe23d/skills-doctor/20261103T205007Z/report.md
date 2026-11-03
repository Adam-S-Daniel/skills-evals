# Eval report: skills-doctor

- Timestamp: 20261103T205007Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T203100Z-dbe23d; started 2026-11-03T20:50:07Z, ended 2026-11-03T20:52:11Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.71 over 2 call(s); agent $0.71, judge $0.00, guard $0.00; last agent call $0.30

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped (objective-decided) | 0.4085 / 0.4085 |
| without_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.2998 / 0.2998 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4085 / 0.4085 | 0.2998 / 0.2998 | +0.1087 | +0.1087 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 59608 / 59608 | 60906 / 60906 | -1298 | -1298 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 5750 / 5750 | 5137 / 5137 | +613 | +613 |
| cache_creation_input_tokens | 31499 / 31499 | 18326 / 18326 | +13173 | +13173 |
| cache_read_input_tokens | 207306 / 207306 | 252165 / 252165 | -44859 | -44859 |
| tool_errors | 1 / 1 | 1 / 1 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 1/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
