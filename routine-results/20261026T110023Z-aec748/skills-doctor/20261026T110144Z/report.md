# Eval report: skills-doctor

- Timestamp: 20261026T110144Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261026T110023Z-aec748; started 2026-10-26T11:01:44Z, ended 2026-10-26T11:08:34Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent call starts, so the 1 call(s) from the last reading on are not in it): five_hour 0.14 to 0.15, seven_day 0.6 to 0.6, from 6 snapshots

## Fixture: bucketed-account-store (n=3)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.310 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4/5 | skipped (objective-decided) | 0.3901 / 1.1704 |
| without_skill | 3 | 0 | 3.3/5 | skipped (objective-decided) | 0.2961 / 0.8884 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3901 / 0.3303 | 0.2961 / 0.2857 | +0.0940 | +0.0445 |
| num_turns | 8.3 / 9 | 7.3 / 7 | +1 | +2 |
| duration_ms | 73934.7 / 73439 | 60098.7 / 52942 | +13836 | +20497 |
| input_tokens | 16.7 / 18 | 14 / 14 | +2.7 | +4 |
| output_tokens | 5652.3 / 5350 | 5076.3 / 4883 | +576 | +467 |
| cache_creation_input_tokens | 26713.3 / 19545 | 18049 / 18241 | +8664.3 | +1304 |
| cache_read_input_tokens | 316643.3 / 334254 | 250810 / 245375 | +65833.3 | +88879 |
| tool_errors | 0 / 0 | 0.7 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-account-store-was-read-not-called-empty | 0/3 | 0/3 |
| the-duplicated-skill-is-named-with-its-two-sources | 3/3 | 1/3 |
| the-missing-section-is-identified | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
