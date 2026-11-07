# Eval report: skills-doctor

- Timestamp: 20261107T193603Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T193426Z-740b05; started 2026-11-07T19:36:03Z, ended 2026-11-07T19:43:44Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.65, from 7 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.28 over 6 call(s); agent $2.28, judge $0.00, guard $0.00; last agent call $0.30

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.3/5 | skipped (objective-decided) | 0.4509 / 1.3526 |
| without_skill | 3 | 0 | 3/5 | skipped (objective-decided) | 0.3092 / 0.9277 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4509 / 0.5093 | 0.3092 / 0.2978 | +0.1416 | +0.2114 |
| num_turns | 8.7 / 10 | 7.7 / 7 | +1 | +3 |
| duration_ms | 86177.3 / 95689 | 64692.3 / 65498 | +21485 | +30191 |
| input_tokens | 16.7 / 18 | 14.7 / 14 | +2 | +4 |
| output_tokens | 6366.7 / 6429 | 5273 / 5228 | +1093.7 | +1201 |
| cache_creation_input_tokens | 32329 / 34119 | 18743.3 / 17837 | +13585.7 | +16282 |
| cache_read_input_tokens | 324250 / 371847 | 268915.3 / 252547 | +55334.7 | +119300 |
| tool_errors | 0.7 / 1 | 0 / 0 | +0.7 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 1/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 0/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
