# Eval report: skills-doctor

- Timestamp: 20261107T162617Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T161930Z-aa840a; started 2026-11-07T16:26:17Z, ended 2026-11-07T16:29:19Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.54 to 0.54, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.62 over 6 call(s); agent $0.62, judge $0.00, guard $0.00; last agent call $0.10

## Fixture: personal-copy-outranks-repo (n=3)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.3/6 | skipped (objective-decided) | 0.1080 / 0.3239 |
| without_skill | 3 | 0 | 5/6 | skipped (objective-decided) | 0.0980 / 0.2939 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1080 / 0.0920 | 0.0980 / 0.0979 | +0.0100 | -0.0059 |
| num_turns | 5.3 / 5 | 5.7 / 6 | -0.3 | -1 |
| duration_ms | 24181.3 / 24014 | 33848.3 / 31301 | -9667 | -7287 |
| input_tokens | 10.7 / 10 | 10.7 / 10 | 0 | 0 |
| output_tokens | 1833.3 / 1802 | 2173.3 / 2290 | -340 | -488 |
| cache_creation_input_tokens | 17882.3 / 13970 | 14477.3 / 14478 | +3405 | -508 |
| cache_read_input_tokens | 180782.3 / 170779 | 183099.7 / 171585 | -2317.3 | -806 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-personal-copy-is-named-as-the-winner | 3/3 | 3/3 |
| the-winner-is-attributed-to-a-hand-copy | 2/3 | 0/3 |
| the-missing-section-is-named | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
| no-skill-was-added-to-the-personal-store | 2/3 | 3/3 |
