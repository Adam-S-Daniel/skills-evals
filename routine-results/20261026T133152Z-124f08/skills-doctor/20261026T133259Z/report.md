# Eval report: skills-doctor

- Timestamp: 20261026T133259Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T133152Z-124f08; started 2026-10-26T13:32:59Z, ended 2026-10-26T13:41:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.08 to 0.11, seven_day 0.67 to 0.68, from 9 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | 9.0 (8.3 to 9.7, 3 judged) | 0.4523 / 1.3568 |
| without_skill | 3 | 0 | 4.3/5 | 8.8 (8.3 to 9.1, 3 judged) | 0.3023 / 0.9069 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4523 / 0.4515 | 0.3023 / 0.2999 | +0.1499 | +0.1517 |
| num_turns | 9 / 9 | 7 / 7 | +2 | +2 |
| duration_ms | 82508.3 / 85481 | 60847 / 61232 | +21661.3 | +24249 |
| input_tokens | 17.3 / 16 | 13.3 / 12 | +4 | +4 |
| output_tokens | 5857 / 6104 | 5322.7 / 5357 | +534.3 | +747 |
| cache_creation_input_tokens | 32927 / 32932 | 18522.7 / 18785 | +14404.3 | +14147 |
| cache_read_input_tokens | 358147.7 / 329721 | 238104.7 / 212085 | +120043 | +117636 |
| tool_errors | 0 / 0 | 0.3 / 0 | -0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 1/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 3/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
