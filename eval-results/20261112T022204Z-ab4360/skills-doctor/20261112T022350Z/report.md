# Eval report: skills-doctor

- Timestamp: 20261112T022350Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T022204Z-ab4360; started 2026-11-12T02:23:50Z, ended 2026-11-12T02:26:41Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.39 to 0.39, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.90 over 4 call(s); agent $0.71, judge $0.18, guard $0.00; last agent call $0.31

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.4 (9.4 to 9.4, 1 judged) | 0.4050 / 0.4050 |
| without_skill | 1 | 0 | 5/5 | 8.6 (8.6 to 8.6, 1 judged) | 0.3082 / 0.3082 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4050 / 0.4050 | 0.3082 / 0.3082 | +0.0968 | +0.0968 |
| num_turns | 9 / 9 | 10 / 10 | -1 | -1 |
| duration_ms | 69071 / 69071 | 74322 / 74322 | -5251 | -5251 |
| input_tokens | 16 / 16 | 20 / 20 | -4 | -4 |
| output_tokens | 6320 / 6320 | 6539 / 6539 | -219 | -219 |
| cache_creation_input_tokens | 44614 / 44614 | 20201 / 20201 | +24413 | +24413 |
| cache_read_input_tokens | 277182 / 277182 | 381435 / 381435 | -104253 | -104253 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 1/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
