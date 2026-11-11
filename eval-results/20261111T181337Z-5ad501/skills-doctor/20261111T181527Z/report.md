# Eval report: skills-doctor

- Timestamp: 20261111T181527Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T181337Z-5ad501; started 2026-11-11T18:15:27Z, ended 2026-11-11T18:18:03Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.93 over 4 call(s); agent $0.75, judge $0.18, guard $0.00; last agent call $0.25

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.4 (9.4 to 9.4, 1 judged) | 0.4935 / 0.4935 |
| without_skill | 1 | 0 | 4/5 | 8.9 (8.9 to 8.9, 1 judged) | 0.2550 / 0.2550 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4935 / 0.4935 | 0.2550 / 0.2550 | +0.2386 | +0.2386 |
| num_turns | 10 / 10 | 8 / 8 | +2 | +2 |
| duration_ms | 72479 / 72479 | 60477 / 60477 | +12002 | +12002 |
| input_tokens | 18 / 18 | 16 / 16 | +2 | +2 |
| output_tokens | 6439 / 6439 | 5192 / 5192 | +1247 | +1247 |
| cache_creation_input_tokens | 58730 / 58730 | 18348 / 18348 | +40382 | +40382 |
| cache_read_input_tokens | 355179 / 355179 | 296650 / 296650 | +58529 | +58529 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
