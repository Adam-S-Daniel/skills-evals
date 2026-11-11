# Eval report: skills-doctor

- Timestamp: 20261111T173325Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T173148Z-58f9d3; started 2026-11-11T17:33:25Z, ended 2026-11-11T17:36:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.89 over 4 call(s); agent $0.73, judge $0.16, guard $0.00; last agent call $0.28

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.7 (9.7 to 9.7, 1 judged) | 0.4558 / 0.4558 |
| without_skill | 1 | 0 | 4/5 | 9.4 (9.4 to 9.4, 1 judged) | 0.2788 / 0.2788 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4558 / 0.4558 | 0.2788 / 0.2788 | +0.1770 | +0.1770 |
| num_turns | 12 / 12 | 8 / 8 | +4 | +4 |
| duration_ms | 89580 / 89580 | 66189 / 66189 | +23391 | +23391 |
| input_tokens | 24 / 24 | 16 / 16 | +8 | +8 |
| output_tokens | 6757 / 6757 | 5904 / 5904 | +853 | +853 |
| cache_creation_input_tokens | 44921 / 44921 | 20104 / 20104 | +24817 | +24817 |
| cache_read_input_tokens | 479664 / 479664 | 300751 / 300751 | +178913 | +178913 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
