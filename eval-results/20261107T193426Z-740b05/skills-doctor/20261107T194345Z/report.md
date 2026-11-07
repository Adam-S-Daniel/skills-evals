# Eval report: skills-doctor

- Timestamp: 20261107T194345Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T193426Z-740b05; started 2026-11-07T19:43:45Z, ended 2026-11-07T19:49:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.65 to 0.65, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.09 over 12 call(s); agent $0.80, judge $0.30, guard $0.00; last agent call $0.12

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.7/5 | 8.3 (8.0 to 8.6, 3 judged) | 0.1428 / 0.4284 |
| without_skill | 3 | 0 | 4/5 | 8.4 (7.8 to 8.9, 3 judged) | 0.1229 / 0.3686 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1428 / 0.1455 | 0.1229 / 0.1168 | +0.0199 | +0.0287 |
| num_turns | 6 / 6 | 5.7 / 6 | +0.3 | 0 |
| duration_ms | 58255.3 / 55298 | 41412.3 / 41699 | +16843 | +13599 |
| input_tokens | 12 / 12 | 11.3 / 12 | +0.7 | 0 |
| output_tokens | 3695 / 3527 | 3502 / 3360 | +193 | +167 |
| cache_creation_input_tokens | 21191.3 / 18920 | 16972 / 16471 | +4219.3 | +2449 |
| cache_read_input_tokens | 210718.3 / 204567 | 199391 / 211376 | +11327.3 | -6809 |
| tool_errors | 0.3 / 0 | 0 / 0 | +0.3 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 2/3 | 3/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
