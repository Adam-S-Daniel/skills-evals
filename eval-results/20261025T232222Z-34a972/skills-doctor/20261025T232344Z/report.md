# Eval report: skills-doctor

- Timestamp: 20261025T232344Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261025T232222Z-34a972; started 2026-10-25T23:23:44Z, ended 2026-10-25T23:32:45Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.07 to 0.09, seven_day 0.49 to 0.49, from 7 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.3/5 | 8.9 (8.6 to 9.1, 3 judged) | 0.3915 / 1.1745 |
| without_skill | 3 | 0 | 4.3/5 | 8.5 (8.3 to 8.6, 3 judged) | 0.3196 / 0.9587 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3915 / 0.3380 | 0.3196 / 0.3219 | +0.0719 | +0.0161 |
| num_turns | 9 / 8 | 7.3 / 7 | +1.7 | +1 |
| duration_ms | 73199 / 65607 | 64515.7 / 64423 | +8683.3 | +1184 |
| input_tokens | 17.3 / 14 | 14.7 / 14 | +2.7 | 0 |
| output_tokens | 5912 / 5992 | 5629.7 / 5549 | +282.3 | +443 |
| cache_creation_input_tokens | 25876.3 / 20723 | 19192.7 / 19202 | +6683.7 | +1521 |
| cache_read_input_tokens | 330965 / 261562 | 266939.7 / 254331 | +64025.3 | +7231 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 1/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/3 | 3/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
