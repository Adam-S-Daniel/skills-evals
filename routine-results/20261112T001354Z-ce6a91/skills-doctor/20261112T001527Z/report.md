# Eval report: skills-doctor

- Timestamp: 20261112T001527Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261112T001354Z-ce6a91; started 2026-11-12T00:15:27Z, ended 2026-11-12T00:16:52Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.37 to 0.37, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.52 over 4 call(s); agent $0.40, judge $0.12, guard $0.00; last agent call $0.19

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.322 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 8.8 (8.8 to 8.8, 1 judged) | 0.2124 / 0.2124 |
| without_skill | 1 | 0 | 6/6 | 9.1 (9.1 to 9.1, 1 judged) | 0.1922 / 0.1922 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2124 / 0.2124 | 0.1922 / 0.1922 | +0.0202 | +0.0202 |
| num_turns | 5 / 5 | 6 / 6 | -1 | -1 |
| duration_ms | 28457 / 28457 | 36089 / 36089 | -7632 | -7632 |
| input_tokens | 10 / 10 | 12 / 12 | -2 | -2 |
| output_tokens | 2630 / 2630 | 3348 / 3348 | -718 | -718 |
| cache_creation_input_tokens | 25461 / 25461 | 16538 / 16538 | +8923 | +8923 |
| cache_read_input_tokens | 162514 / 162514 | 212549 / 212549 | -50035 | -50035 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
