# Eval report: skills-doctor

- Timestamp: 20261103T212513Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T211035Z-c09d65; started 2026-11-03T21:25:13Z, ended 2026-11-03T21:26:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 2 call(s); agent $0.23, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.1354 / 0.1354 |
| without_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.0988 / 0.0988 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1354 / 0.1354 | 0.0988 / 0.0988 | +0.0366 | +0.0366 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 31420 / 31420 | 31676 / 31676 | -256 | -256 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 2018 / 2018 | 2214 / 2214 | -196 | -196 |
| cache_creation_input_tokens | 24796 / 24796 | 14876 / 14876 | +9920 | +9920 |
| cache_read_input_tokens | 160604 / 160604 | 171401 / 171401 | -10797 | -10797 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
