# Eval report: skills-doctor

- Timestamp: 20261111T233113Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T232938Z-d1e7af; started 2026-11-11T23:31:13Z, ended 2026-11-11T23:32:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.48 over 2 call(s); agent $0.48, judge $0.00, guard $0.00; last agent call $0.15

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped: the version with the skill passed more checks (6 of 6 vs 5 of 6) | 0.3266 / 0.3266 |
| without_skill | 1 | 0 | 5/6 | skipped: the version with the skill passed more checks (6 of 6 vs 5 of 6) | 0.1525 / 0.1525 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3266 / 0.3266 | 0.1525 / 0.1525 | +0.1741 | +0.1741 |
| num_turns | 9 / 9 | 4 / 4 | +5 | +5 |
| duration_ms | 72166 / 72166 | 31072 / 31072 | +41094 | +41094 |
| input_tokens | 18 / 18 | 8 / 8 | +10 | +10 |
| output_tokens | 4519 / 4519 | 2842 / 2842 | +1677 | +1677 |
| cache_creation_input_tokens | 33943 / 33943 | 13808 / 13808 | +20135 | +20135 |
| cache_read_input_tokens | 332404 / 332404 | 132965 / 132965 | +199439 | +199439 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
