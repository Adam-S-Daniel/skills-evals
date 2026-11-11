# Eval report: skills-doctor

- Timestamp: 20261111T111800Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T111622Z-000400; started 2026-11-11T11:18:00Z, ended 2026-11-11T11:20:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.79 over 2 call(s); agent $0.79, judge $0.00, guard $0.00; last agent call $0.26

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | skipped: the version with the skill passed more checks (5 of 5 vs 4 of 5) | 0.5316 / 0.5316 |
| without_skill | 1 | 0 | 4/5 | skipped: the version with the skill passed more checks (5 of 5 vs 4 of 5) | 0.2553 / 0.2553 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5316 / 0.5316 | 0.2553 / 0.2553 | +0.2763 | +0.2763 |
| num_turns | 12 / 12 | 7 / 7 | +5 | +5 |
| duration_ms | 111396 / 111396 | 57809 / 57809 | +53587 | +53587 |
| input_tokens | 22 / 22 | 14 / 14 | +8 | +8 |
| output_tokens | 8062 / 8062 | 5206 / 5206 | +2856 | +2856 |
| cache_creation_input_tokens | 56653 / 56653 | 19951 / 19951 | +36702 | +36702 |
| cache_read_input_tokens | 434900 / 434900 | 256785 / 256785 | +178115 | +178115 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 1/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
