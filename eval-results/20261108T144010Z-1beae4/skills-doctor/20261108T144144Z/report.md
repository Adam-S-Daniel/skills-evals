# Eval report: skills-doctor

- Timestamp: 20261108T144144Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T144010Z-1beae4; started 2026-11-08T14:41:44Z, ended 2026-11-08T14:43:23Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.78 to 0.78, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.69 over 2 call(s); agent $0.69, judge $0.00, guard $0.00; last agent call $0.22

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.4651 / 0.4651 |
| without_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.2209 / 0.2209 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4651 / 0.4651 | 0.2209 / 0.2209 | +0.2442 | +0.2442 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 55584 / 55584 | 39869 / 39869 | +15715 | +15715 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 4431 / 4431 | 3160 / 3160 | +1271 | +1271 |
| cache_creation_input_tokens | 40415 / 40415 | 15431 / 15431 | +24984 | +24984 |
| cache_read_input_tokens | 265315 / 265315 | 170843 / 170843 | +94472 | +94472 |
| tool_errors | 0 / 0 | 1 / 1 | -1 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
