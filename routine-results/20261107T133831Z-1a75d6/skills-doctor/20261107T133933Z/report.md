# Eval report: skills-doctor

- Timestamp: 20261107T133933Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T133831Z-1a75d6; started 2026-11-07T13:39:33Z, ended 2026-11-07T13:42:04Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.44 to 0.44, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.91 over 6 call(s); agent $0.59, judge $0.32, guard $0.00; last agent call $0.19

## Fixture: personal-copy-outranks-repo (n=3)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| without_skill | 3 | 0 | 5.7/6 | 9.0 (8.3 to 9.4, 3 judged) | 0.1980 / 0.5941 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did):

| Metric (mean / median) | without_skill |
| --- | --- |
| cost_usd | 0.1980 / 0.1964 |
| num_turns | 5 / 5 |
| duration_ms | 38451.3 / 39729 |
| input_tokens | 10 / 10 |
| output_tokens | 2666.7 / 2636 |
| cache_creation_input_tokens | 13547.7 / 13461 |
| cache_read_input_tokens | 181315 / 180943 |
| tool_errors | 0 / 0 |

| Check (passed / scored) | without_skill |
| --- | --- |
| findings-written | 3/3 |
| the-personal-copy-is-named-as-the-winner | 3/3 |
| the-winner-is-attributed-to-a-hand-copy | 2/3 |
| the-missing-section-is-named | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 |
| no-skill-was-added-to-the-personal-store | 3/3 |
