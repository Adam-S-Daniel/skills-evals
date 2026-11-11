# Eval report: skills-doctor

- Timestamp: 20261111T160627Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T160324Z-17ed0f; started 2026-11-11T16:06:27Z, ended 2026-11-11T16:07:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.27 over 4 call(s); agent $0.20, judge $0.06, guard $0.00; last agent call $0.07

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 7.3 (7.3 to 7.3, 1 judged) | 0.1315 / 0.1315 |
| without_skill | 1 | 0 | 5/6 | 7.8 (7.8 to 7.8, 1 judged) | 0.0712 / 0.0712 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1315 / 0.1315 | 0.0712 / 0.0712 | +0.0603 | +0.0603 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 22446 / 22446 | 25229 / 25229 | -2783 | -2783 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1936 / 1936 | 1983 / 1983 | -47 | -47 |
| cache_creation_input_tokens | 38989 / 38989 | 13702 / 13702 | +25287 | +25287 |
| cache_read_input_tokens | 146494 / 146494 | 170763 / 170763 | -24269 | -24269 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
