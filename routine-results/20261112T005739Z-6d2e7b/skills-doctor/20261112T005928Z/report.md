# Eval report: skills-doctor

- Timestamp: 20261112T005928Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T005739Z-6d2e7b; started 2026-11-12T00:59:28Z, ended 2026-11-12T01:02:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.38, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.90 over 4 call(s); agent $0.72, judge $0.17, guard $0.00; last agent call $0.26

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.7 (9.7 to 9.7, 1 judged) | 0.4623 / 0.4623 |
| without_skill | 1 | 0 | 4/5 | 8.9 (8.9 to 8.9, 1 judged) | 0.2622 / 0.2622 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4623 / 0.4623 | 0.2622 / 0.2622 | +0.2001 | +0.2001 |
| num_turns | 11 / 11 | 7 / 7 | +4 | +4 |
| duration_ms | 75538 / 75538 | 59790 / 59790 | +15748 | +15748 |
| input_tokens | 18 / 18 | 14 / 14 | +4 | +4 |
| output_tokens | 6559 / 6559 | 5687 / 5687 | +872 | +872 |
| cache_creation_input_tokens | 49845 / 49845 | 19492 / 19492 | +30353 | +30353 |
| cache_read_input_tokens | 409201 / 409201 | 254571 / 254571 | +154630 | +154630 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
