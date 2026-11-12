# Eval report: skills-doctor

- Timestamp: 20261112T013600Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T013427Z-fccf8f; started 2026-11-12T01:36:00Z, ended 2026-11-12T01:37:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.39 to 0.39, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.50 over 2 call(s); agent $0.50, judge $0.00, guard $0.00; last agent call $0.18

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped: the version with the skill passed more checks (6 of 6 vs 5 of 6) | 0.3191 / 0.3191 |
| without_skill | 1 | 0 | 5/6 | skipped: the version with the skill passed more checks (6 of 6 vs 5 of 6) | 0.1766 / 0.1766 |

Judge: when the version with the skill or guidance passes more checks than its partner, the judge isn't needed and both are skipped. On a tie or a loss, the judge scores both from 0 to 10.

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3191 / 0.3191 | 0.1766 / 0.1766 | +0.1425 | +0.1425 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 43114 / 43114 | 35722 / 35722 | +7392 | +7392 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 3435 / 3435 | 3234 / 3234 | +201 | +201 |
| cache_creation_input_tokens | 39050 / 39050 | 15494 / 15494 | +23556 | +23556 |
| cache_read_input_tokens | 275243 / 275243 | 171839 / 171839 | +103404 | +103404 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
