# Eval report: skills-doctor

- Timestamp: 20261111T054952Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T054820Z-662b5a; started 2026-11-11T05:49:52Z, ended 2026-11-11T05:51:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.32 to 0.32, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 4 call(s); agent $0.25, judge $0.08, guard $0.00; last agent call $0.10

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 3/5 | 9.7 (9.7 to 9.7, 1 judged) | 0.1463 / 0.1463 |
| without_skill | 1 | 0 | 3/5 | 8.3 (8.3 to 8.3, 1 judged) | 0.1038 / 0.1038 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1463 / 0.1463 | 0.1038 / 0.1038 | +0.0425 | +0.0425 |
| num_turns | 5 / 5 | 7 / 7 | -2 | -2 |
| duration_ms | 26515 / 26515 | 34976 / 34976 | -8461 | -8461 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 2839 / 2839 | 3800 / 3800 | -961 | -961 |
| cache_creation_input_tokens | 41169 / 41169 | 17831 / 17831 | +23338 | +23338 |
| cache_read_input_tokens | 149425 / 149425 | 211733 / 211733 | -62308 | -62308 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 0/1 | 0/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
