# Eval report: skills-doctor

- Timestamp: 20261107T152456Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T151454Z-2d653c; started 2026-11-07T15:24:56Z, ended 2026-11-07T15:29:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.49 to 0.49, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.75 over 6 call(s); agent $0.75, judge $0.00, guard $0.00; last agent call $0.12

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | skipped (objective-decided) | 0.1367 / 0.4100 |
| without_skill | 3 | 0 | 3.3/5 | skipped (objective-decided) | 0.1140 / 0.3420 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1367 / 0.1228 | 0.1140 / 0.1174 | +0.0227 | +0.0055 |
| num_turns | 5.7 / 6 | 5.3 / 5 | +0.3 | +1 |
| duration_ms | 37420.3 / 35965 | 42828 / 36854 | -5407.7 | -889 |
| input_tokens | 11.3 / 12 | 10.7 / 10 | +0.7 | +2 |
| output_tokens | 3434.3 / 3480 | 3141.3 / 3192 | +293 | +288 |
| cache_creation_input_tokens | 20689.3 / 17463 | 16026.3 / 16142 | +4663 | +1321 |
| cache_read_input_tokens | 195511 / 210462 | 184488.3 / 173106 | +11022.7 | +37356 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 1/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
