# Eval report: skills-doctor

- Timestamp: 20261111T224521Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T224111Z-71cb32; started 2026-11-11T22:45:21Z, ended 2026-11-11T22:46:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 4 call(s); agent $0.26, judge $0.08, guard $0.00; last agent call $0.11

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 8.0 (8.0 to 8.0, 1 judged) | 0.1549 / 0.1549 |
| without_skill | 1 | 0 | 4/5 | 8.3 (8.3 to 8.3, 1 judged) | 0.1051 / 0.1051 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1549 / 0.1549 | 0.1051 / 0.1051 | +0.0498 | +0.0498 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 33212 / 33212 | 35584 / 35584 | -2372 | -2372 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 3413 / 3413 | 4058 / 4058 | -645 | -645 |
| cache_creation_input_tokens | 42276 / 42276 | 17240 / 17240 | +25036 | +25036 |
| cache_read_input_tokens | 150617 / 150617 | 213729 / 213729 | -63112 | -63112 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
