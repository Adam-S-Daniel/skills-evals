# Eval report: skills-doctor

- Timestamp: 20261111T144153Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T143957Z-706d88; started 2026-11-11T14:41:53Z, ended 2026-11-11T14:44:28Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.86 over 4 call(s); agent $0.66, judge $0.20, guard $0.00; last agent call $0.29

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.4 (9.4 to 9.4, 1 judged) | 0.3758 / 0.3758 |
| without_skill | 1 | 0 | 4/5 | 9.4 (9.4 to 9.4, 1 judged) | 0.2881 / 0.2881 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3758 / 0.3758 | 0.2881 / 0.2881 | +0.0878 | +0.0878 |
| num_turns | 7 / 7 | 9 / 9 | -2 | -2 |
| duration_ms | 59482 / 59482 | 67765 / 67765 | -8283 | -8283 |
| input_tokens | 12 / 12 | 18 / 18 | -6 | -6 |
| output_tokens | 5460 / 5460 | 6049 / 6049 | -589 | -589 |
| cache_creation_input_tokens | 45543 / 45543 | 19799 / 19799 | +25744 | +25744 |
| cache_read_input_tokens | 194347 / 194347 | 340052 / 340052 | -145705 | -145705 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
