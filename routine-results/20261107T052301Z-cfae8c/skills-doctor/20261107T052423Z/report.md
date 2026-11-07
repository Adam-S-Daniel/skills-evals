# Eval report: skills-doctor

- Timestamp: 20261107T052423Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261107T052301Z-cfae8c; started 2026-11-07T05:24:23Z, ended 2026-11-07T05:25:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 4 call(s); agent $0.29, judge $0.10, guard $0.00; last agent call $0.12

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 8.9 (8.9 to 8.9, 1 judged) | 0.1663 / 0.1663 |
| without_skill | 1 | 0 | 4/5 | 8.3 (8.3 to 8.3, 1 judged) | 0.1187 / 0.1187 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1663 / 0.1663 | 0.1187 / 0.1187 | +0.0476 | +0.0476 |
| num_turns | 6 / 6 | 6 / 6 | 0 | 0 |
| duration_ms | 35535 / 35535 | 35984 / 35984 | -449 | -449 |
| input_tokens | 12 / 12 | 12 / 12 | 0 | 0 |
| output_tokens | 3538 / 3538 | 3018 / 3018 | +520 | +520 |
| cache_creation_input_tokens | 27716 / 27716 | 16864 / 16864 | +10852 | +10852 |
| cache_read_input_tokens | 200629 / 200629 | 210356 / 210356 | -9727 | -9727 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
