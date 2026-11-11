# Eval report: skills-doctor

- Timestamp: 20261111T232742Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T232605Z-7bdc68; started 2026-11-11T23:27:42Z, ended 2026-11-11T23:30:17Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.92 over 4 call(s); agent $0.75, judge $0.16, guard $0.00; last agent call $0.26

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.7 (9.7 to 9.7, 1 judged) | 0.4917 / 0.4917 |
| without_skill | 1 | 0 | 4/5 | 8.8 (8.8 to 8.8, 1 judged) | 0.2626 / 0.2626 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4917 / 0.4917 | 0.2626 / 0.2626 | +0.2291 | +0.2291 |
| num_turns | 10 / 10 | 8 / 8 | +2 | +2 |
| duration_ms | 76023 / 76023 | 61462 / 61462 | +14561 | +14561 |
| input_tokens | 18 / 18 | 16 / 16 | +2 | +2 |
| output_tokens | 6446 / 6446 | 5452 / 5452 | +994 | +994 |
| cache_creation_input_tokens | 58548 / 58548 | 18847 / 18847 | +39701 | +39701 |
| cache_read_input_tokens | 349983 / 349983 | 296377 / 296377 | +53606 | +53606 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
