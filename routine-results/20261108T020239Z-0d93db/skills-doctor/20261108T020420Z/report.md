# Eval report: skills-doctor

- Timestamp: 20261108T020420Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T020239Z-0d93db; started 2026-11-08T02:04:20Z, ended 2026-11-08T02:06:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.71 to 0.71, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.72 over 2 call(s); agent $0.72, judge $0.00, guard $0.00; last agent call $0.25

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.4750 / 0.4750 |
| without_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.2456 / 0.2456 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4750 / 0.4750 | 0.2456 / 0.2456 | +0.2294 | +0.2294 |
| num_turns | 8 / 8 | 6 / 6 | +2 | +2 |
| duration_ms | 62171 / 62171 | 41173 / 41173 | +20998 | +20998 |
| input_tokens | 16 / 16 | 12 / 12 | +4 | +4 |
| output_tokens | 4885 / 4885 | 3678 / 3678 | +1207 | +1207 |
| cache_creation_input_tokens | 40548 / 40548 | 16283 / 16283 | +24265 | +24265 |
| cache_read_input_tokens | 264495 / 264495 | 208868 / 208868 | +55627 | +55627 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
