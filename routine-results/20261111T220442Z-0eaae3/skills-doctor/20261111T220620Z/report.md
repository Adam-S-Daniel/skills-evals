# Eval report: skills-doctor

- Timestamp: 20261111T220620Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T220442Z-0eaae3; started 2026-11-11T22:06:20Z, ended 2026-11-11T22:07:55Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.54 over 4 call(s); agent $0.39, judge $0.14, guard $0.00; last agent call $0.16

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 8.5 (8.5 to 8.5, 1 judged) | 0.2312 / 0.2312 |
| without_skill | 1 | 0 | 6/6 | 8.8 (8.8 to 8.8, 1 judged) | 0.1633 / 0.1633 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2312 / 0.2312 | 0.1633 / 0.1633 | +0.0679 | +0.0679 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 42000 / 42000 | 32986 / 32986 | +9014 | +9014 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 3217 / 3217 | 2898 / 2898 | +319 | +319 |
| cache_creation_input_tokens | 26839 / 26839 | 14209 / 14209 | +12630 | +12630 |
| cache_read_input_tokens | 162976 / 162976 | 171063 / 171063 | -8087 | -8087 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
