# Eval report: skills-doctor

- Timestamp: 20261111T165247Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T165110Z-5af7de; started 2026-11-11T16:52:47Z, ended 2026-11-11T16:55:37Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.81 over 4 call(s); agent $0.63, judge $0.18, guard $0.00; last agent call $0.28

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.1 (9.1 to 9.1, 1 judged) | 0.3582 / 0.3582 |
| without_skill | 1 | 0 | 5/5 | 8.3 (8.3 to 8.3, 1 judged) | 0.2763 / 0.2763 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3582 / 0.3582 | 0.2763 / 0.2763 | +0.0820 | +0.0820 |
| num_turns | 10 / 10 | 8 / 8 | +2 | +2 |
| duration_ms | 72842 / 72842 | 68017 / 68017 | +4825 | +4825 |
| input_tokens | 20 / 20 | 16 / 16 | +4 | +4 |
| output_tokens | 6235 / 6235 | 5841 / 5841 | +394 | +394 |
| cache_creation_input_tokens | 31496 / 31496 | 19853 / 19853 | +11643 | +11643 |
| cache_read_input_tokens | 379821 / 379821 | 300564 / 300564 | +79257 | +79257 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 1/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
