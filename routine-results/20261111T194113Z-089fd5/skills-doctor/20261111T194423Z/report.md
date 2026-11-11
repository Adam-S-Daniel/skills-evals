# Eval report: skills-doctor

- Timestamp: 20261111T194423Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T194113Z-089fd5; started 2026-11-11T19:44:23Z, ended 2026-11-11T19:45:29Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 4 call(s); agent $0.17, judge $0.06, guard $0.00; last agent call $0.07

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 7.0 (7.0 to 7.0, 1 judged) | 0.0968 / 0.0968 |
| without_skill | 1 | 0 | 6/6 | 8.3 (8.3 to 8.3, 1 judged) | 0.0726 / 0.0726 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.0968 / 0.0968 | 0.0726 / 0.0726 | +0.0242 | +0.0242 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 21829 / 21829 | 22519 / 22519 | -690 | -690 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1825 / 1825 | 1883 / 1883 | -58 | -58 |
| cache_creation_input_tokens | 24888 / 24888 | 14569 / 14569 | +10319 | +10319 |
| cache_read_input_tokens | 162633 / 162633 | 172910 / 172910 | -10277 | -10277 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
