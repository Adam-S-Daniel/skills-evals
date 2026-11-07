# Eval report: skills-doctor

- Timestamp: 20261107T122440Z
- Trials per arm: 2
- Run: billing subscription, runner routine, location cloud, id 20261107T122302Z-dec2c6; started 2026-11-07T12:24:40Z, ended 2026-11-07T12:26:57Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.57 over 8 call(s); agent $0.42, judge $0.15, guard $0.00; last agent call $0.10

## Fixture: personal-copy-outranks-repo (n=2)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 2 | 0 | 5.5/6 | 7.0 (6.3 to 7.7, 2 judged) | 0.1119 / 0.2239 |
| without_skill | 2 | 0 | 5.5/6 | 7.4 (7.3 to 7.5, 2 judged) | 0.0961 / 0.1923 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1119 / 0.1119 | 0.0961 / 0.0961 | +0.0158 | +0.0158 |
| num_turns | 5 / 5 | 5.5 / 5.5 | -0.5 | -0.5 |
| duration_ms | 24084 / 24084 | 24033.5 / 24033.5 | +50.5 | +50.5 |
| input_tokens | 10 / 10 | 11 / 11 | -1 | -1 |
| output_tokens | 1890.5 / 1890.5 | 2109.5 / 2109.5 | -219 | -219 |
| cache_creation_input_tokens | 19127 / 19127 | 14041 / 14041 | +5086 | +5086 |
| cache_read_input_tokens | 165122 / 165122 | 188526 / 188526 | -23404 | -23404 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 2/2 | 2/2 |
| the-personal-copy-is-named-as-the-winner | 2/2 | 2/2 |
| the-winner-is-attributed-to-a-hand-copy | 1/2 | 1/2 |
| the-missing-section-is-named | 2/2 | 2/2 |
| nothing-in-the-capture-was-repaired | 2/2 | 2/2 |
| no-skill-was-added-to-the-personal-store | 2/2 | 2/2 |
