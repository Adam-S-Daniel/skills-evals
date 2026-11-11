# Eval report: skills-doctor

- Timestamp: 20261111T173140Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261111T172816Z-363fac; started 2026-11-11T17:31:40Z, ended 2026-11-11T17:32:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.36 to 0.36, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 4 call(s); agent $0.22, judge $0.06, guard $0.00; last agent call $0.07

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 5/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.1455 / 0.1455 |
| without_skill | 1 | 0 | 5/6 | 8.0 (8.0 to 8.0, 1 judged) | 0.0720 / 0.0720 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.1455 / 0.1455 | 0.0720 / 0.0720 | +0.0735 | +0.0735 |
| num_turns | 7 / 7 | 5 / 5 | +2 | +2 |
| duration_ms | 27495 / 27495 | 23753 / 23753 | +3742 | +3742 |
| input_tokens | 14 / 14 | 10 / 10 | +4 | +4 |
| output_tokens | 2260 / 2260 | 1864 / 1864 | +396 | +396 |
| cache_creation_input_tokens | 40138 / 40138 | 14458 / 14458 | +25680 | +25680 |
| cache_read_input_tokens | 225484 / 225484 | 172417 / 172417 | +53067 | +53067 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 0/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
