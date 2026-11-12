# Eval report: skills-doctor

- Timestamp: 20261112T001105Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T000650Z-bc445f; started 2026-11-12T00:11:05Z, ended 2026-11-12T00:12:27Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.32 over 4 call(s); agent $0.25, judge $0.07, guard $0.00; last agent call $0.10

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.1541 / 0.1541 |
| without_skill | 1 | 0 | 3/5 | 8.3 (8.3 to 8.3, 1 judged) | 0.0956 / 0.0956 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1541 / 0.1541 | 0.0956 / 0.0956 | +0.0585 | +0.0585 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 30428 / 30428 | 31667 / 31667 | -1239 | -1239 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 3008 / 3008 | 3171 / 3171 | -163 | -163 |
| cache_creation_input_tokens | 42096 / 42096 | 16937 / 16937 | +25159 | +25159 |
| cache_read_input_tokens | 187238 / 187238 | 215073 / 215073 | -27835 | -27835 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 0/1 | 0/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
