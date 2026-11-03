# Eval report: skills-doctor

- Timestamp: 20261103T024507Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T024330Z-e70a74; started 2026-11-03T02:45:07Z, ended 2026-11-03T02:46:12Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.3 to 0.3, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.38 over 4 call(s); agent $0.23, judge $0.15, guard $0.00; last agent call $0.09

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 7.2 (7.2 to 7.2, 1 judged) | 0.1403 / 0.1403 |
| without_skill | 1 | 0 | 5/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.0902 / 0.0902 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1403 / 0.1403 | 0.0902 / 0.0902 | +0.0501 | +0.0501 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 23979 / 23979 | 21137 / 21137 | +2842 | +2842 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 1973 / 1973 | 1795 / 1795 | +178 | +178 |
| cache_creation_input_tokens | 25162 / 25162 | 13795 / 13795 | +11367 | +11367 |
| cache_read_input_tokens | 198664 / 198664 | 170011 / 170011 | +28653 | +28653 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
