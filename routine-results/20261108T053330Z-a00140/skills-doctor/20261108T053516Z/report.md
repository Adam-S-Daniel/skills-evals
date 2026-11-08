# Eval report: skills-doctor

- Timestamp: 20261108T053516Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T053330Z-a00140; started 2026-11-08T05:35:16Z, ended 2026-11-08T05:37:05Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.73 to 0.73, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.76 over 4 call(s); agent $0.55, judge $0.21, guard $0.00; last agent call $0.23

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | 9.1 (9.1 to 9.1, 1 judged) | 0.3217 / 0.3217 |
| without_skill | 1 | 0 | 6/6 | 9.7 (9.7 to 9.7, 1 judged) | 0.2287 / 0.2287 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.3217 / 0.3217 | 0.2287 / 0.2287 | +0.0930 | +0.0930 |
| num_turns | 6 / 6 | 5 / 5 | +1 | +1 |
| duration_ms | 43409 / 43409 | 42275 / 42275 | +1134 | +1134 |
| input_tokens | 12 / 12 | 10 / 10 | +2 | +2 |
| output_tokens | 3259 / 3259 | 3298 / 3298 | -39 | -39 |
| cache_creation_input_tokens | 27015 / 27015 | 16035 / 16035 | +10980 | +10980 |
| cache_read_input_tokens | 201753 / 201753 | 171858 / 171858 | +29895 | +29895 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 1/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
