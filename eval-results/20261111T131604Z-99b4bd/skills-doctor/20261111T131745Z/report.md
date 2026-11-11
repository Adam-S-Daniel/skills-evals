# Eval report: skills-doctor

- Timestamp: 20261111T131745Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T131604Z-99b4bd; started 2026-11-11T13:17:45Z, ended 2026-11-11T13:19:13Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.34 to 0.34, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.60 over 4 call(s); agent $0.46, judge $0.15, guard $0.00; last agent call $0.16

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 8.8 (8.8 to 8.8, 1 judged) | 0.2955 / 0.2955 |
| without_skill | 1 | 0 | 6/6 | 9.1 (9.1 to 9.1, 1 judged) | 0.1600 / 0.1600 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2955 / 0.2955 | 0.1600 / 0.1600 | +0.1355 | +0.1355 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 36395 / 36395 | 30190 / 30190 | +6205 | +6205 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 3009 / 3009 | 2740 / 2740 | +269 | +269 |
| cache_creation_input_tokens | 41105 / 41105 | 14186 / 14186 | +26919 | +26919 |
| cache_read_input_tokens | 148840 / 148840 | 171236 / 171236 | -22396 | -22396 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
