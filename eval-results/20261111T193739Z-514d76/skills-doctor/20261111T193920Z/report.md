# Eval report: skills-doctor

- Timestamp: 20261111T193920Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T193739Z-514d76; started 2026-11-11T19:39:20Z, ended 2026-11-11T19:41:33Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 2 call(s); agent $0.76, judge $0.00, guard $0.00; last agent call $0.29

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | skipped: the version with the skill passed more checks (4 of 5 vs 3 of 5) | 0.4675 / 0.4675 |
| without_skill | 1 | 0 | 3/5 | skipped: the version with the skill passed more checks (4 of 5 vs 3 of 5) | 0.2896 / 0.2896 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4675 / 0.4675 | 0.2896 / 0.2896 | +0.1779 | +0.1779 |
| num_turns | 10 / 10 | 9 / 9 | +1 | +1 |
| duration_ms | 62861 / 62861 | 66583 / 66583 | -3722 | -3722 |
| input_tokens | 18 / 18 | 18 / 18 | 0 | 0 |
| output_tokens | 5841 / 5841 | 5954 / 5954 | -113 | -113 |
| cache_creation_input_tokens | 57727 / 57727 | 20410 / 20410 | +37317 | +37317 |
| cache_read_input_tokens | 309804 / 309804 | 342165 / 342165 | -32361 | -32361 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 0/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
