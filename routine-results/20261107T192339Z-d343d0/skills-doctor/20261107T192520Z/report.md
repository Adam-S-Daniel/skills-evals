# Eval report: skills-doctor

- Timestamp: 20261107T192520Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T192339Z-d343d0; started 2026-11-07T19:25:20Z, ended 2026-11-07T19:30:54Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.32 over 12 call(s); agent $1.73, judge $0.60, guard $0.00; last agent call $0.21

## Fixture: personal-copy-outranks-repo (n=3)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/6 | 9.9 (9.7 to 10.0, 3 judged) | 0.3603 / 1.0809 |
| without_skill | 3 | 0 | 6/6 | 9.3 (8.6 to 9.7, 3 judged) | 0.2148 / 0.6444 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3603 / 0.3656 | 0.2148 / 0.2113 | +0.1455 | +0.1543 |
| num_turns | 7.7 / 7 | 5 / 5 | +2.7 | +2 |
| duration_ms | 57596.3 / 54717 | 35335.7 / 34122 | +22260.7 | +20595 |
| input_tokens | 15.3 / 14 | 10 / 10 | +5.3 | +4 |
| output_tokens | 4006 / 3767 | 2975.3 / 3028 | +1030.7 | +739 |
| cache_creation_input_tokens | 28144.3 / 23572 | 15130 / 14588 | +13014.3 | +8984 |
| cache_read_input_tokens | 274820 / 257017 | 171033 / 170783 | +103787 | +86234 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-personal-copy-is-named-as-the-winner | 3/3 | 3/3 |
| the-winner-is-attributed-to-a-hand-copy | 3/3 | 3/3 |
| the-missing-section-is-named | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
| no-skill-was-added-to-the-personal-store | 3/3 | 3/3 |
