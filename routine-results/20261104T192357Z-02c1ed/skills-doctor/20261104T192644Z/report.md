# Eval report: skills-doctor

- Timestamp: 20261104T192644Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261104T192357Z-02c1ed; started 2026-11-04T19:26:44Z, ended 2026-11-04T19:29:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.03 to 0.03, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.49 over 4 call(s); agent $0.32, judge $0.17, guard $0.00; last agent call $0.14

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.318 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.1766 / 0.1766 |
| without_skill | 1 | 0 | 4/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.1438 / 0.1438 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1766 / 0.1766 | 0.1438 / 0.1438 | +0.0329 | +0.0329 |
| num_turns | 7 / 7 | 8 / 8 | -1 | -1 |
| duration_ms | 58460 / 58460 | 50743 / 50743 | +7717 | +7717 |
| input_tokens | 14 / 14 | 16 / 16 | -2 | -2 |
| output_tokens | 3734 / 3734 | 3985 / 3985 | -251 | -251 |
| cache_creation_input_tokens | 28756 / 28756 | 18622 / 18622 | +10134 | +10134 |
| cache_read_input_tokens | 242423 / 242423 | 293948 / 293948 | -51525 | -51525 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
