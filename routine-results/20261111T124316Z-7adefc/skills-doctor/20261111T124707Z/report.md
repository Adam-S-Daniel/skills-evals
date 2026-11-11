# Eval report: skills-doctor

- Timestamp: 20261111T124707Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T124316Z-7adefc; started 2026-11-11T12:47:07Z, ended 2026-11-11T12:48:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 4 call(s); agent $0.21, judge $0.07, guard $0.00; last agent call $0.09

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.1185 / 0.1185 |
| without_skill | 1 | 0 | 4/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.0909 / 0.0909 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1185 / 0.1185 | 0.0909 / 0.0909 | +0.0276 | +0.0276 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 31668 / 31668 | 29324 / 29324 | +2344 | +2344 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3348 / 3348 | 2776 / 2776 | +572 | +572 |
| cache_creation_input_tokens | 27353 / 27353 | 16732 / 16732 | +10621 | +10621 |
| cache_read_input_tokens | 165793 / 165793 | 212500 / 212500 | -46707 | -46707 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 0/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
