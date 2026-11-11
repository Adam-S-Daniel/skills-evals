# Eval report: skills-doctor

- Timestamp: 20261111T115829Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T115651Z-53938f; started 2026-11-11T11:58:29Z, ended 2026-11-11T12:01:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.34, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.93 over 4 call(s); agent $0.73, judge $0.20, guard $0.00; last agent call $0.25

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 8.8 (8.8 to 8.8, 1 judged) | 0.4856 / 0.4856 |
| without_skill | 1 | 0 | 4/5 | 8.9 (8.9 to 8.9, 1 judged) | 0.2468 / 0.2468 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4856 / 0.4856 | 0.2468 / 0.2468 | +0.2388 | +0.2388 |
| num_turns | 10 / 10 | 7 / 7 | +3 | +3 |
| duration_ms | 88301 / 88301 | 58033 / 58033 | +30268 | +30268 |
| input_tokens | 18 / 18 | 14 / 14 | +4 | +4 |
| output_tokens | 6522 / 6522 | 5168 / 5168 | +1354 | +1354 |
| cache_creation_input_tokens | 58399 / 58399 | 18537 / 18537 | +39862 | +39862 |
| cache_read_input_tokens | 315346 / 315346 | 253317 / 253317 | +62029 | +62029 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
