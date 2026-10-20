# Eval report: skills-doctor

- Timestamp: 20261020T205254Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261020T205143Z-d75e66; started 2026-10-20T20:52:54Z, ended 2026-10-20T20:58:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 7 call(s) from the last reading on are not in it): five_hour 0.08 to 0.1, seven_day 0.1 to 0.1, from 8 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.304 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 3.3/5 | 8.8 (8.6 to 9.2, 3 judged) | 0.1581 / 0.4743 |
| without_skill | 3 | 0 | 4/5 | 8.5 (8.0 to 8.9, 3 judged) | 0.1637 / 0.4910 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1581 / 0.1589 | 0.1637 / 0.1596 | -0.0056 | -0.0007 |
| num_turns | 5.3 / 5 | 5.3 / 5 | 0 | 0 |
| duration_ms | 35864.3 / 38947 | 41706.3 / 40908 | -5842 | -1961 |
| input_tokens | 10.7 / 10 | 10.7 / 10 | 0 | 0 |
| output_tokens | 3249.3 / 3273 | 3741.7 / 3548 | -492.3 | -275 |
| cache_creation_input_tokens | 27282 / 27402 | 27460.3 / 27224 | -178.3 | +178 |
| cache_read_input_tokens | 164482.7 / 152931 | 163850.3 / 151687 | +632.3 | +1244 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/3 | 3/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
