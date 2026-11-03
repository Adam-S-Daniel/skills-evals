# Eval report: skills-doctor

- Timestamp: 20261103T202944Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T200626Z-4b1d57; started 2026-11-03T20:29:44Z, ended 2026-11-03T20:31:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.7 to 0.7, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.66 over 2 call(s); agent $0.66, judge $0.00, guard $0.00; last agent call $0.25

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.4085 / 0.4085 |
| without_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.2513 / 0.2513 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4085 / 0.4085 | 0.2513 / 0.2513 | +0.1572 | +0.1572 |
| num_turns | 7 / 7 | 6 / 6 | +1 | +1 |
| duration_ms | 43860 / 43860 | 48813 / 48813 | -4953 | -4953 |
| input_tokens | 14 / 14 | 12 / 12 | +2 | +2 |
| output_tokens | 3160 / 3160 | 3964 / 3964 | -804 | -804 |
| cache_creation_input_tokens | 37610 / 37610 | 16262 / 16262 | +21348 | +21348 |
| cache_read_input_tokens | 221744 / 221744 | 209361 / 209361 | +12383 | +12383 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
