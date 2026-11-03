# Eval report: skills-doctor

- Timestamp: 20261103T021951Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T021847Z-f44eb9; started 2026-11-03T02:19:51Z, ended 2026-11-03T02:20:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.29 to 0.29, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.60 over 4 call(s); agent $0.23, judge $0.37, guard $0.00; last agent call $0.10

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 7.7 (7.7 to 7.7, 1 judged) | 0.1331 / 0.1331 |
| without_skill | 1 | 0 | 5/6 | 6.2 (6.2 to 6.2, 1 judged) | 0.0955 / 0.0955 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1331 / 0.1331 | 0.0955 / 0.0955 | +0.0376 | +0.0376 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 20810 / 20810 | 21686 / 21686 | -876 | -876 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1884 / 1884 | 2201 / 2201 | -317 | -317 |
| cache_creation_input_tokens | 24551 / 24551 | 14125 / 14125 | +10426 | +10426 |
| cache_read_input_tokens | 160361 / 160361 | 169790 / 169790 | -9429 | -9429 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
