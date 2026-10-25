# Eval report: skills-doctor

- Timestamp: 20261025T003349Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T003229Z-3804b2; started 2026-10-25T00:33:49Z, ended 2026-10-25T00:46:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.04 to 0.07, seven_day 0.36 to 0.37, from 9 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.7/5 | 7.9 (7.2 to 8.7, 3 judged) | 0.3714 / 1.1143 |
| without_skill | 3 | 0 | 5/5 | 7.3 (7.1 to 7.7, 3 judged) | 0.3206 / 0.9617 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3714 / 0.3811 | 0.3206 / 0.3121 | +0.0509 | +0.0690 |
| num_turns | 17 / 17 | 13.3 / 15 | +3.7 | +2 |
| duration_ms | 126797.7 / 123620 | 109180.3 / 98521 | +17617.3 | +25099 |
| input_tokens | 22.7 / 24 | 18 / 18 | +4.7 | +6 |
| output_tokens | 9840.3 / 9034 | 9237.7 / 8733 | +602.7 | +301 |
| cache_creation_input_tokens | 40374 / 37889 | 35699.7 / 37006 | +4674.3 | +883 |
| cache_read_input_tokens | 557519.7 / 569547 | 426845 / 410721 | +130674.7 | +158826 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 2/3 | 3/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 3/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
