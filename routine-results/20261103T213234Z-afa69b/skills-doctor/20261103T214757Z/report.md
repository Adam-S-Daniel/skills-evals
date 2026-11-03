# Eval report: skills-doctor

- Timestamp: 20261103T214757Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T213234Z-afa69b; started 2026-11-03T21:47:57Z, ended 2026-11-03T21:50:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.75, from 5 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.01 over 4 call(s); agent $0.63, judge $0.38, guard $0.00; last agent call $0.20

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.4245 / 0.4245 |
| without_skill | 1 | 0 | 6/6 | 9.1 (9.1 to 9.1, 1 judged) | 0.2039 / 0.2039 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4245 / 0.4245 | 0.2039 / 0.2039 | +0.2206 | +0.2206 |
| num_turns | 9 / 9 | 5 / 5 | +4 | +4 |
| duration_ms | 73754 / 73754 | 31030 / 31030 | +42724 | +42724 |
| input_tokens | 18 / 18 | 10 / 10 | +8 | +8 |
| output_tokens | 3609 / 3609 | 2759 / 2759 | +850 | +850 |
| cache_creation_input_tokens | 35572 / 35572 | 14343 / 14343 | +21229 | +21229 |
| cache_read_input_tokens | 338344 / 338344 | 169545 / 169545 | +168799 | +168799 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
