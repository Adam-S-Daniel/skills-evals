# Eval report: skills-doctor

- Timestamp: 20261111T182240Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T182046Z-2e45a1; started 2026-11-11T18:22:40Z, ended 2026-11-11T18:24:18Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.60 over 4 call(s); agent $0.49, judge $0.12, guard $0.00; last agent call $0.17

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 10.0 (10.0 to 10.0, 1 judged) | 0.3128 / 0.3128 |
| without_skill | 1 | 0 | 6/6 | 8.8 (8.8 to 8.8, 1 judged) | 0.1741 / 0.1741 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3128 / 0.3128 | 0.1741 / 0.1741 | +0.1387 | +0.1387 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 42181 / 42181 | 36763 / 36763 | +5418 | +5418 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 3838 / 3838 | 3204 / 3204 | +634 | +634 |
| cache_creation_input_tokens | 38660 / 38660 | 15123 / 15123 | +23537 | +23537 |
| cache_read_input_tokens | 213372 / 213372 | 171748 / 171748 | +41624 | +41624 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
