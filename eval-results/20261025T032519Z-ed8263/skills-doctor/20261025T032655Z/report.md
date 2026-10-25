# Eval report: skills-doctor

- Timestamp: 20261025T032655Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T032519Z-ed8263; started 2026-10-25T03:26:55Z, ended 2026-10-25T03:36:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.17 to 0.19, seven_day 0.39 to 0.39, from 7 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | 9.4 (8.9 to 9.7, 3 judged) | 0.4192 / 1.2575 |
| without_skill | 3 | 0 | 4/5 | 8.9 (8.6 to 9.4, 3 judged) | 0.2911 / 0.8734 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4192 / 0.3190 | 0.2911 / 0.2862 | +0.1280 | +0.0327 |
| num_turns | 9.7 / 8 | 7 / 7 | +2.7 | +1 |
| duration_ms | 86932 / 73906 | 60922.7 / 62023 | +26009.3 | +11883 |
| input_tokens | 19.3 / 16 | 14 / 14 | +5.3 | +2 |
| output_tokens | 6350 / 5703 | 4962.7 / 4732 | +1387.3 | +971 |
| cache_creation_input_tokens | 27042.7 / 19342 | 17786.7 / 17764 | +9256 | +1578 |
| cache_read_input_tokens | 378794 / 292588 | 247664 / 247108 | +131130 | +45480 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 1/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 2/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
