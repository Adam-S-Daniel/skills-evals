# Eval report: skills-doctor

- Timestamp: 20261111T092346Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T092213Z-5e5c89; started 2026-11-11T09:23:46Z, ended 2026-11-11T09:24:48Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.33 to 0.33, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.26 over 4 call(s); agent $0.20, judge $0.06, guard $0.00; last agent call $0.07

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.5 (8.5 to 8.5, 1 judged) | 0.1318 / 0.1318 |
| without_skill | 1 | 0 | 6/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.0725 / 0.0725 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1318 / 0.1318 | 0.0725 / 0.0725 | +0.0593 | +0.0593 |
| num_turns | 5 / 5 | 5 / 5 | 0 | 0 |
| duration_ms | 21592 / 21592 | 21893 / 21893 | -301 | -301 |
| input_tokens | 10 / 10 | 10 / 10 | 0 | 0 |
| output_tokens | 1741 / 1741 | 1938 / 1938 | -197 | -197 |
| cache_creation_input_tokens | 39823 / 39823 | 14361 / 14361 | +25462 | +25462 |
| cache_read_input_tokens | 148138 / 148138 | 172261 / 172261 | -24123 | -24123 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
