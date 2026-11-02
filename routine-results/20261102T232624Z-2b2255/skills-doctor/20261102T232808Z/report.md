# Eval report: skills-doctor

- Timestamp: 20261102T232808Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261102T232624Z-2b2255; started 2026-11-02T23:28:08Z, ended 2026-11-02T23:29:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.24 to 0.24, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.45 over 4 call(s); agent $0.28, judge $0.17, guard $0.00; last agent call $0.10

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.1 (9.1 to 9.1, 1 judged) | 0.1811 / 0.1811 |
| without_skill | 1 | 0 | 4/5 | 8.9 (8.9 to 8.9, 1 judged) | 0.1027 / 0.1027 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1811 / 0.1811 | 0.1027 / 0.1027 | +0.0784 | +0.0784 |
| num_turns | 7 / 7 | 4 / 4 | +3 | +3 |
| duration_ms | 42497 / 42497 | 25448 / 25448 | +17049 | +17049 |
| input_tokens | 14 / 14 | 8 / 8 | +6 | +6 |
| output_tokens | 4034 / 4034 | 2728 / 2728 | +1306 | +1306 |
| cache_creation_input_tokens | 28935 / 28935 | 15505 / 15505 | +13430 | +13430 |
| cache_read_input_tokens | 250362 / 250362 | 133918 / 133918 | +116444 | +116444 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
