# Eval report: skills-doctor

- Timestamp: 20261107T110511Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T110339Z-d1584d; started 2026-11-07T11:05:11Z, ended 2026-11-07T11:08:25Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.41 to 0.41, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.72 over 8 call(s); agent $0.52, judge $0.20, guard $0.00; last agent call $0.11

## Fixture: bucketed-account-store (n=2)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 3.5/5 | 8.8 (8.6 to 8.9, 2 judged) | 0.1483 / 0.2966 |
| without_skill | 2 | 0 | 4/5 | 8.6 (8.6 to 8.6, 2 judged) | 0.1106 / 0.2211 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1483 / 0.1483 | 0.1106 / 0.1106 | +0.0377 | +0.0377 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 40690 / 40690 | 34576.5 / 34576.5 | +6113.5 | +6113.5 |
| input_tokens | 11 / 11 | 10 / 10 | +1 | +1 |
| output_tokens | 3838.5 / 3838.5 | 2927.5 / 2927.5 | +911 | +911 |
| cache_creation_input_tokens | 22720 / 22720 | 16000.5 / 16000.5 | +6719.5 | +6719.5 |
| cache_read_input_tokens | 189905.5 / 189905.5 | 172628.5 / 172628.5 | +17277 | +17277 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 2/2 | 2/2 |
| the-account-store-was-read-not-called-empty | 0/2 | 0/2 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/2 | 2/2 |
| the-missing-section-is-identified | 2/2 | 2/2 |
| nothing-in-the-capture-was-repaired | 2/2 | 2/2 |
