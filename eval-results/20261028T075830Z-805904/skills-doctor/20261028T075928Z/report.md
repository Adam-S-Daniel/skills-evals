# Eval report: skills-doctor

- Timestamp: 20261028T075928Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261028T075830Z-805904; started 2026-10-28T07:59:28Z, ended 2026-10-28T08:02:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.08 to 0.08, seven_day 0.26 to 0.27, from 10 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.312 (Claude Code)`; models used: without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 3.7/5 | 8.6 (8.6 to 8.6, 3 judged) | 0.2627 / 0.7882 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.2627 / 0.2536 |
| num_turns | 6.7 / 7 |
| duration_ms | 51038 / 51098 |
| input_tokens | 12 / 12 |
| output_tokens | 4120.3 / 4062 |
| cache_creation_input_tokens | 16852 / 16128 |
| cache_read_input_tokens | 226435 / 226128 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| findings-written | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 2/3 |
| the-missing-section-is-identified | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 |
