# Eval report: skills-doctor

- Timestamp: 20261108T031925Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T031740Z-4ec39c; started 2026-11-08T03:19:25Z, ended 2026-11-08T03:21:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.72 to 0.72, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.66 over 2 call(s); agent $0.66, judge $0.00, guard $0.00; last agent call $0.23

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.4274 / 0.4274 |
| without_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.2289 / 0.2289 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4274 / 0.4274 | 0.2289 / 0.2289 | +0.1985 | +0.1985 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 63288 / 63288 | 37524 / 37524 | +25764 | +25764 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 4223 / 4223 | 3348 / 3348 | +875 | +875 |
| cache_creation_input_tokens | 36454 / 36454 | 15951 / 15951 | +20503 | +20503 |
| cache_read_input_tokens | 256191 / 256191 | 171502 / 171502 | +84689 | +84689 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
