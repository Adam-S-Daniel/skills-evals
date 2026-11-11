# Eval report: skills-doctor

- Timestamp: 20261111T233300Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T232938Z-d1e7af; started 2026-11-11T23:33:00Z, ended 2026-11-11T23:34:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.24 over 4 call(s); agent $0.18, judge $0.06, guard $0.00; last agent call $0.07

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.1039 / 0.1039 |
| without_skill | 1 | 0 | 5/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.0733 / 0.0733 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1039 / 0.1039 | 0.0733 / 0.0733 | +0.0306 | +0.0306 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 24454 / 24454 | 24155 / 24155 | +299 | +299 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1962 / 1962 | 1957 / 1957 | +5 | +5 |
| cache_creation_input_tokens | 25642 / 25642 | 14587 / 14587 | +11055 | +11055 |
| cache_read_input_tokens | 201398 / 201398 | 172446 / 172446 | +28952 | +28952 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
