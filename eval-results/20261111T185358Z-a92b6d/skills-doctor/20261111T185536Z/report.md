# Eval report: skills-doctor

- Timestamp: 20261111T185536Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T185358Z-a92b6d; started 2026-11-11T18:55:36Z, ended 2026-11-11T18:57:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.82 over 4 call(s); agent $0.65, judge $0.17, guard $0.00; last agent call $0.25

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 8.5 (8.5 to 8.5, 1 judged) | 0.3975 / 0.3975 |
| without_skill | 1 | 0 | 5/5 | 9.4 (9.4 to 9.4, 1 judged) | 0.2524 / 0.2524 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3975 / 0.3975 | 0.2524 / 0.2524 | +0.1451 | +0.1451 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 58800 / 58800 | 56386 / 56386 | +2414 | +2414 |
| input_tokens | 18 / 18 | 14 / 14 | +4 | +4 |
| output_tokens | 5458 / 5458 | 5251 / 5251 | +207 | +207 |
| cache_creation_input_tokens | 44953 / 44953 | 19288 / 19288 | +25665 | +25665 |
| cache_read_input_tokens | 317750 / 317750 | 254572 / 254572 | +63178 | +63178 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 1/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
