# Eval report: skills-doctor

- Timestamp: 20261112T000824Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T000650Z-bc445f; started 2026-11-12T00:08:24Z, ended 2026-11-12T00:11:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.95 over 4 call(s); agent $0.76, judge $0.18, guard $0.00; last agent call $0.26

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.4 (9.4 to 9.4, 1 judged) | 0.5072 / 0.5072 |
| without_skill | 1 | 0 | 4/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.2555 / 0.2555 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5072 / 0.5072 | 0.2555 / 0.2555 | +0.2517 | +0.2517 |
| num_turns | 10 / 10 | 7 / 7 | +3 | +3 |
| duration_ms | 77554 / 77554 | 60076 / 60076 | +17478 | +17478 |
| input_tokens | 18 / 18 | 14 / 14 | +4 | +4 |
| output_tokens | 6943 / 6943 | 5569 / 5569 | +1374 | +1374 |
| cache_creation_input_tokens | 59313 / 59313 | 18533 / 18533 | +40780 | +40780 |
| cache_read_input_tokens | 358709 / 358709 | 257138 / 257138 | +101571 | +101571 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
