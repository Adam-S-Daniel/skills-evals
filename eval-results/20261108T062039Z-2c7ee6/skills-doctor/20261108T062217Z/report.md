# Eval report: skills-doctor

- Timestamp: 20261108T062217Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T062039Z-2c7ee6; started 2026-11-08T06:22:17Z, ended 2026-11-08T06:23:39Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 2 call(s); agent $0.50, judge $0.00, guard $0.00; last agent call $0.20

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.3043 / 0.3043 |
| without_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.1980 / 0.1980 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3043 / 0.3043 | 0.1980 / 0.1980 | +0.1063 | +0.1063 |
| num_turns | 5 / 5 | 4 / 4 | +1 | +1 |
| duration_ms | 42229 / 42229 | 36465 / 36465 | +5764 | +5764 |
| input_tokens | 10 / 10 | 8 / 8 | +2 | +2 |
| output_tokens | 3121 / 3121 | 2960 / 2960 | +161 | +161 |
| cache_creation_input_tokens | 26204 / 26204 | 14037 / 14037 | +12167 | +12167 |
| cache_read_input_tokens | 161046 / 161046 | 132146 / 132146 | +28900 | +28900 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
