# Eval report: skills-doctor

- Timestamp: 20261026T105944Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T105806Z-11b1c8; started 2026-10-26T10:59:44Z, ended 2026-10-26T11:05:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.14 to 0.15, seven_day 0.6 to 0.6, from 7 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | 8.4 (8.3 to 8.6, 3 judged) | 0.1395 / 0.4184 |
| without_skill | 3 | 0 | 4/5 | 8.5 (8.3 to 8.6, 3 judged) | 0.1163 / 0.3490 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1395 / 0.1330 | 0.1163 / 0.1155 | +0.0231 | +0.0175 |
| num_turns | 6 / 6 | 5.7 / 6 | +0.3 | 0 |
| duration_ms | 50378 / 49009 | 49506 / 52189 | +872 | -3180 |
| input_tokens | 12 / 12 | 11.3 / 12 | +0.7 | 0 |
| output_tokens | 3583 / 3721 | 3197.7 / 3084 | +385.3 | +637 |
| cache_creation_input_tokens | 20721.7 / 17688 | 16202.7 / 15978 | +4519 | +1710 |
| cache_read_input_tokens | 207291 / 208832 | 195161.7 / 206774 | +12129.3 | +2058 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 3/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
