# Eval report: skills-doctor

- Timestamp: 20261103T095405Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T095244Z-307f5f; started 2026-11-03T09:54:05Z, ended 2026-11-03T09:55:51Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.38 to 0.38, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.92 over 4 call(s); agent $0.53, judge $0.39, guard $0.00; last agent call $0.20

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.8 (8.8 to 8.8, 1 judged) | 0.3235 / 0.3235 |
| without_skill | 1 | 0 | 6/6 | 9.2 (9.2 to 9.2, 1 judged) | 0.2028 / 0.2028 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3235 / 0.3235 | 0.2028 / 0.2028 | +0.1207 | +0.1207 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 37291 / 37291 | 36511 / 36511 | +780 | +780 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 3374 / 3374 | 2655 / 2655 | +719 | +719 |
| cache_creation_input_tokens | 26940 / 26940 | 14450 / 14450 | +12490 | +12490 |
| cache_read_input_tokens | 202140 / 202140 | 170078 / 170078 | +32062 | +32062 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
