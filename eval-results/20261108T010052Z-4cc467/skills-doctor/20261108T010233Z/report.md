# Eval report: skills-doctor

- Timestamp: 20261108T010233Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T010052Z-4cc467; started 2026-11-08T01:02:33Z, ended 2026-11-08T01:05:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.88 over 2 call(s); agent $0.88, judge $0.00, guard $0.00; last agent call $0.31

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | skipped (objective-decided) | 0.5635 / 0.5635 |
| without_skill | 1 | 0 | 3/5 | skipped (objective-decided) | 0.3117 / 0.3117 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.5635 / 0.5635 | 0.3117 / 0.3117 | +0.2518 | +0.2518 |
| num_turns | 12 / 12 | 7 / 7 | +5 | +5 |
| duration_ms | 84775 / 84775 | 66758 / 66758 | +18017 | +18017 |
| input_tokens | 24 / 24 | 14 / 14 | +10 | +10 |
| output_tokens | 6960 / 6960 | 5316 / 5316 | +1644 | +1644 |
| cache_creation_input_tokens | 40562 / 40562 | 19333 / 19333 | +21229 | +21229 |
| cache_read_input_tokens | 498645 / 498645 | 253168 / 253168 | +245477 | +245477 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 0/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
