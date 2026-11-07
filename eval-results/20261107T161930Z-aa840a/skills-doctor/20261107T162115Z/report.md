# Eval report: skills-doctor

- Timestamp: 20261107T162115Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T161930Z-aa840a; started 2026-11-07T16:21:15Z, ended 2026-11-07T16:26:16Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.53 to 0.54, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.70 over 6 call(s); agent $1.70, judge $0.00, guard $0.00; last agent call $0.23

## Fixture: personal-copy-outranks-repo (n=3)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 5.7/6 | skipped (objective-decided) | 0.3231 / 0.9693 |
| without_skill | 3 | 0 | 5.3/6 | skipped (objective-decided) | 0.2423 / 0.7270 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3231 / 0.3117 | 0.2423 / 0.2324 | +0.0808 | +0.0793 |
| num_turns | 6.3 / 7 | 5.3 / 5 | +1 | +2 |
| duration_ms | 51954 / 55411 | 45734.3 / 44006 | +6219.7 | +11405 |
| input_tokens | 12.7 / 14 | 10.7 / 10 | +2 | +4 |
| output_tokens | 3804.3 / 3877 | 3706.7 / 3532 | +97.7 | +345 |
| cache_creation_input_tokens | 25137.3 / 22776 | 16392.7 / 16071 | +8744.7 | +6705 |
| cache_read_input_tokens | 229274.3 / 255941 | 185080.3 / 171878 | +44194 | +84063 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-personal-copy-is-named-as-the-winner | 3/3 | 3/3 |
| the-winner-is-attributed-to-a-hand-copy | 2/3 | 1/3 |
| the-missing-section-is-named | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
| no-skill-was-added-to-the-personal-store | 3/3 | 3/3 |
