# Eval report: skills-doctor

- Timestamp: 20261111T105712Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T105536Z-137d74; started 2026-11-11T10:57:12Z, ended 2026-11-11T10:58:20Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 4 call(s); agent $0.20, judge $0.06, guard $0.00; last agent call $0.07

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.1328 / 0.1328 |
| without_skill | 1 | 0 | 6/6 | 7.0 (7.0 to 7.0, 1 judged) | 0.0698 / 0.0698 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1328 / 0.1328 | 0.0698 / 0.0698 | +0.0630 | +0.0630 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 24694 / 24694 | 24624 / 24624 | +70 | +70 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1949 / 1949 | 1898 / 1898 | +51 | +51 |
| cache_creation_input_tokens | 39404 / 39404 | 13462 / 13462 | +25942 | +25942 |
| cache_read_input_tokens | 147343 / 147343 | 170996 / 170996 | -23653 | -23653 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
