# Eval report: skills-doctor

- Timestamp: 20261103T161705Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T161329Z-e2b8de; started 2026-11-03T16:17:05Z, ended 2026-11-03T16:20:32Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.56 to 0.56, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.39 over 4 call(s); agent $0.91, judge $0.48, guard $0.00; last agent call $0.33

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/5 | 9.7 (9.7 to 9.7, 1 judged) | 0.5848 / 0.5848 |
| without_skill | 1 | 0 | 5/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.3284 / 0.3284 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5848 / 0.5848 | 0.3284 / 0.3284 | +0.2564 | +0.2564 |
| num_turns | 11 / 11 | 8 / 8 | +3 | +3 |
| duration_ms | 77242 / 77242 | 89095 / 89095 | -11853 | -11853 |
| input_tokens | 22 / 22 | 16 / 16 | +6 | +6 |
| output_tokens | 6689 / 6689 | 5607 / 5607 | +1082 | +1082 |
| cache_creation_input_tokens | 45592 / 45592 | 19607 / 19607 | +25985 | +25985 |
| cache_read_input_tokens | 430886 / 430886 | 296796 / 296796 | +134090 | +134090 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 1/1 | 1/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
