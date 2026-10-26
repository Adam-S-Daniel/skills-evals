# Eval report: skills-doctor

- Timestamp: 20261026T135341Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T135200Z-d337f3; started 2026-10-26T13:53:41Z, ended 2026-10-26T13:58:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.17 to 0.21, seven_day 0.69 to 0.7, from 8 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | 8.6 (8.3 to 8.9, 3 judged) | 0.1288 / 0.3864 |
| without_skill | 3 | 0 | 4.3/5 | 8.2 (8.0 to 8.6, 3 judged) | 0.1166 / 0.3497 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1288 / 0.1162 | 0.1166 / 0.1143 | +0.0123 | +0.0019 |
| num_turns | 5 / 5 | 5.7 / 6 | -0.7 | -1 |
| duration_ms | 37551 / 33367 | 39428.3 / 38527 | -1877.3 | -5160 |
| input_tokens | 10 / 10 | 11.3 / 12 | -1.3 | -2 |
| output_tokens | 3172.3 / 3245 | 3181.7 / 2936 | -9.3 | +309 |
| cache_creation_input_tokens | 20033.3 / 16498 | 16270.3 / 16165 | +3763 | +333 |
| cache_read_input_tokens | 169348.3 / 172411 | 196332.3 / 208366 | -26984 | -35955 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 1/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 3/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
