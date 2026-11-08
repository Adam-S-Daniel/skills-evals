# Eval report: skills-doctor

- Timestamp: 20261108T162550Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T162154Z-b1648f; started 2026-11-08T16:25:50Z, ended 2026-11-08T16:26:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.81 to 0.81, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 4 call(s); agent $0.21, judge $0.05, guard $0.00; last agent call $0.08

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 6.0 (6.0 to 6.0, 1 judged) | 0.1324 / 0.1324 |
| without_skill | 1 | 0 | 6/6 | 8.8 (8.8 to 8.8, 1 judged) | 0.0761 / 0.0761 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1324 / 0.1324 | 0.0761 / 0.0761 | +0.0562 | +0.0562 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 21216 / 21216 | 25988 / 25988 | -4772 | -4772 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 1940 / 1940 | 1928 / 1928 | +12 | +12 |
| cache_creation_input_tokens | 39328 / 39328 | 14404 / 14404 | +24924 | +24924 |
| cache_read_input_tokens | 146358 / 146358 | 208154 / 208154 | -61796 | -61796 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
