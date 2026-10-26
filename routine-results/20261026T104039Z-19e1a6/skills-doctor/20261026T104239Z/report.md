# Eval report: skills-doctor

- Timestamp: 20261026T104239Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T104039Z-19e1a6; started 2026-10-26T10:42:39Z, ended 2026-10-26T10:49:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.11 to 0.12, seven_day 0.59 to 0.6, from 8 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | skipped (objective-decided) | 0.4404 / 1.3212 |
| without_skill | 3 | 0 | 3.3/5 | skipped (objective-decided) | 0.2925 / 0.8776 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4404 / 0.4962 | 0.2925 / 0.2735 | +0.1479 | +0.2227 |
| num_turns | 9.3 / 9 | 7.7 / 7 | +1.7 | +2 |
| duration_ms | 79719.7 / 75845 | 60383.7 / 55564 | +19336 | +20281 |
| input_tokens | 16.7 / 16 | 15.3 / 14 | +1.3 | +2 |
| output_tokens | 5894.7 / 5572 | 4744.3 / 4495 | +1150.3 | +1077 |
| cache_creation_input_tokens | 31987 / 34403 | 17804.7 / 17293 | +14182.3 | +17110 |
| cache_read_input_tokens | 332674.7 / 306228 | 275746 / 247342 | +56928.7 | +58886 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 1/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
