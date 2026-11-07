# Eval report: skills-doctor

- Timestamp: 20261107T151629Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T151454Z-2d653c; started 2026-11-07T15:16:29Z, ended 2026-11-07T15:24:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.48 to 0.49, from 13 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.84 over 12 call(s); agent $1.98, judge $0.86, guard $0.00; last agent call $0.31

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | 9.2 (8.3 to 9.7, 3 judged) | 0.3405 / 1.0214 |
| without_skill | 3 | 0 | 4/5 | 9.2 (9.1 to 9.4, 3 judged) | 0.3203 / 0.9608 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3405 / 0.3139 | 0.3203 / 0.3138 | +0.0202 | +0.0001 |
| num_turns | 7 / 7 | 7.7 / 7 | -0.7 | 0 |
| duration_ms | 67696.7 / 69163 | 66943.3 / 71000 | +753.3 | -1837 |
| input_tokens | 13.3 / 12 | 14.7 / 14 | -1.3 | -2 |
| output_tokens | 5425 / 5664 | 5458 / 5482 | -33 | +182 |
| cache_creation_input_tokens | 22975.7 / 19709 | 19658.7 / 19514 | +3317 | +195 |
| cache_read_input_tokens | 240525.3 / 216121 | 268887 / 254090 | -28361.7 | -37969 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 3/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
