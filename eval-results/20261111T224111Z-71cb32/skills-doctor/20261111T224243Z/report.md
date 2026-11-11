# Eval report: skills-doctor

- Timestamp: 20261111T224243Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T224111Z-71cb32; started 2026-11-11T22:42:43Z, ended 2026-11-11T22:45:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.99 over 4 call(s); agent $0.80, judge $0.19, guard $0.00; last agent call $0.25

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.7 (9.7 to 9.7, 1 judged) | 0.5529 / 0.5529 |
| without_skill | 1 | 0 | 4/5 | 8.9 (8.9 to 8.9, 1 judged) | 0.2490 / 0.2490 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5529 / 0.5529 | 0.2490 / 0.2490 | +0.3039 | +0.3039 |
| num_turns | 12 / 12 | 7 / 7 | +5 | +5 |
| duration_ms | 80286 / 80286 | 54386 / 54386 | +25900 | +25900 |
| input_tokens | 24 / 24 | 14 / 14 | +10 | +10 |
| output_tokens | 7497 / 7497 | 5262 / 5262 | +2235 | +2235 |
| cache_creation_input_tokens | 61083 / 61083 | 18583 / 18583 | +42500 | +42500 |
| cache_read_input_tokens | 487300 / 487300 | 253751 / 253751 | +233549 | +233549 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
