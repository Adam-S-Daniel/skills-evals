# Eval report: skills-doctor

- Timestamp: 20261028T072619Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T072520Z-be74c3; started 2026-10-28T07:26:19Z, ended 2026-10-28T07:28:46Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.06 to 0.07, seven_day 0.26 to 0.26, from 6 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3.7/5 | 8.8 (8.6 to 8.9, 3 judged) | 0.1104 / 0.3311 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1104 / 0.1129 |
| num_turns | 5.3 / 5 |
| duration_ms | 39592.7 / 37854 |
| input_tokens | 10.7 / 10 |
| output_tokens | 3098 / 3010 |
| cache_creation_input_tokens | 14863 / 15075 |
| cache_read_input_tokens | 197546.3 / 185353 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| findings-written | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 2/3 |
| the-missing-section-is-identified | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 |
