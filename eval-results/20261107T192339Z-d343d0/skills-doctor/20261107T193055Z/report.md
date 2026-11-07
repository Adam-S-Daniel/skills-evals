# Eval report: skills-doctor

- Timestamp: 20261107T193055Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T192339Z-d343d0; started 2026-11-07T19:30:55Z, ended 2026-11-07T19:34:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.64 to 0.64, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.81 over 12 call(s); agent $0.58, judge $0.23, guard $0.00; last agent call $0.09

## Fixture: personal-copy-outranks-repo (n=3)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 4.7/6 | 8.0 (7.7 to 8.5, 3 judged) | 0.1053 / 0.3158 |
| without_skill | 3 | 0 | 5.7/6 | 7.7 (7.0 to 8.3, 3 judged) | 0.0894 / 0.2683 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1053 / 0.0917 | 0.0894 / 0.0891 | +0.0158 | +0.0026 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 24285.3 / 25460 | 22911.7 / 22008 | +1373.7 | +3452 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1905.3 / 1923 | 1877.3 / 1932 | +28 | -9 |
| cache_creation_input_tokens | 17381.7 / 13860 | 13435 / 13542 | +3946.7 | +318 |
| cache_read_input_tokens | 166670.7 / 169970 | 169068.7 / 169146 | -2398 | +824 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 3/3 | 3/3 |
| the-personal-copy-is-named-as-the-winner | 3/3 | 3/3 |
| the-winner-is-attributed-to-a-hand-copy | 0/3 | 2/3 |
| the-missing-section-is-named | 3/3 | 3/3 |
| nothing-in-the-capture-was-repaired | 3/3 | 3/3 |
| no-skill-was-added-to-the-personal-store | 2/3 | 3/3 |
