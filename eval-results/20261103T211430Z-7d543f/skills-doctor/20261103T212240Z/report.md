# Eval report: skills-doctor

- Timestamp: 20261103T212240Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T211430Z-7d543f; started 2026-11-03T21:22:40Z, ended 2026-11-03T21:24:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.47 over 4 call(s); agent $0.29, judge $0.17, guard $0.00; last agent call $0.13

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.1602 / 0.1602 |
| without_skill | 1 | 0 | 4/5 | 8.3 (8.3 to 8.3, 1 judged) | 0.1347 / 0.1347 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1602 / 0.1602 | 0.1347 / 0.1347 | +0.0255 | +0.0255 |
| num_turns | 6 / 6 | 7 / 7 | -1 | -1 |
| duration_ms | 28129 / 28129 | 57056 / 57056 | -28927 | -28927 |
| input_tokens | 12 / 12 | 14 / 14 | -2 | -2 |
| output_tokens | 3127 / 3127 | 3783 / 3783 | -656 | -656 |
| cache_creation_input_tokens | 27214 / 27214 | 17913 / 17913 | +9301 | +9301 |
| cache_read_input_tokens | 200498 / 200498 | 251629 / 251629 | -51131 | -51131 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
