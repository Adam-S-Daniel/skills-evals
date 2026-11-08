# Eval report: skills-doctor

- Timestamp: 20261108T071125Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T070814Z-8adac8; started 2026-11-08T07:11:25Z, ended 2026-11-08T07:12:35Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.30 over 4 call(s); agent $0.22, judge $0.08, guard $0.00; last agent call $0.09

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 6.0 (6.0 to 6.0, 1 judged) | 0.1301 / 0.1301 |
| without_skill | 1 | 0 | 6/6 | 7.5 (7.5 to 7.5, 1 judged) | 0.0895 / 0.0895 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1301 / 0.1301 | 0.0895 / 0.0895 | +0.0407 | +0.0407 |
| num_turns | 4 / 4 | 5 / 5 | -1 | -1 |
| duration_ms | 23040 / 23040 | 25571 / 25571 | -2531 | -2531 |
| input_tokens | 8 / 8 | 10 / 10 | -2 | -2 |
| output_tokens | 1817 / 1817 | 1878 / 1878 | -61 | -61 |
| cache_creation_input_tokens | 24897 / 24897 | 13425 / 13425 | +11472 | +11472 |
| cache_read_input_tokens | 123738 / 123738 | 169507 / 169507 | -45769 | -45769 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
