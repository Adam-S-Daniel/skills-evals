# Eval report: skills-doctor

- Timestamp: 20261103T145012Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T144825Z-801e84; started 2026-11-03T14:50:12Z, ended 2026-11-03T14:52:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.48, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.67 over 2 call(s); agent $0.67, judge $0.00, guard $0.00; last agent call $0.30

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.3767 / 0.3767 |
| without_skill | 1 | 0 | 3/5 | skipped (objective-decided) | 0.2976 / 0.2976 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3767 / 0.3767 | 0.2976 / 0.2976 | +0.0792 | +0.0792 |
| num_turns | 7 / 7 | 7 / 7 | 0 | 0 |
| duration_ms | 53634 / 53634 | 54294 / 54294 | -660 | -660 |
| input_tokens | 14 / 14 | 14 / 14 | 0 | 0 |
| output_tokens | 4832 / 4832 | 4884 / 4884 | -52 | -52 |
| cache_creation_input_tokens | 28936 / 28936 | 18657 / 18657 | +10279 | +10279 |
| cache_read_input_tokens | 242652 / 242652 | 252838 / 252838 | -10186 | -10186 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 0/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
