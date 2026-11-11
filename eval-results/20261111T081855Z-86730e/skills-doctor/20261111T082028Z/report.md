# Eval report: skills-doctor

- Timestamp: 20261111T082028Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T081855Z-86730e; started 2026-11-11T08:20:28Z, ended 2026-11-11T08:21:43Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.23 over 4 call(s); agent $0.18, judge $0.06, guard $0.00; last agent call $0.07

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.3 (8.3 to 8.3, 1 judged) | 0.1023 / 0.1023 |
| without_skill | 1 | 0 | 5/6 | 7.2 (7.2 to 7.2, 1 judged) | 0.0740 / 0.0740 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1023 / 0.1023 | 0.0740 / 0.0740 | +0.0283 | +0.0283 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 31496 / 31496 | 23955 / 23955 | +7541 | +7541 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1917 / 1917 | 2020 / 2020 | -103 | -103 |
| cache_creation_input_tokens | 25208 / 25208 | 14605 / 14605 | +10603 | +10603 |
| cache_read_input_tokens | 201283 / 201283 | 172831 / 172831 | +28452 | +28452 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
