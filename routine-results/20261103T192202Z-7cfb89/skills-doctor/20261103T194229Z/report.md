# Eval report: skills-doctor

- Timestamp: 20261103T194229Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T192202Z-7cfb89; started 2026-11-03T19:42:29Z, ended 2026-11-03T19:43:40Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.68 to 0.68, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 4 call(s); agent $0.24, judge $0.15, guard $0.00; last agent call $0.09

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 7.7 (7.7 to 7.7, 1 judged) | 0.1421 / 0.1421 |
| without_skill | 1 | 0 | 5/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.0941 / 0.0941 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1421 / 0.1421 | 0.0941 / 0.0941 | +0.0480 | +0.0480 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 27908 / 27908 | 20547 / 20547 | +7361 | +7361 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 2252 / 2252 | 1778 / 1778 | +474 | +474 |
| cache_creation_input_tokens | 25849 / 25849 | 13906 / 13906 | +11943 | +11943 |
| cache_read_input_tokens | 161796 / 161796 | 206514 / 206514 | -44718 | -44718 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
