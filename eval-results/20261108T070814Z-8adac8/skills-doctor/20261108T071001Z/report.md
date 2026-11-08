# Eval report: skills-doctor

- Timestamp: 20261108T071001Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261108T070814Z-8adac8; started 2026-11-08T07:10:01Z, ended 2026-11-08T07:11:24Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.74 to 0.74, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.66 over 2 call(s); agent $0.66, judge $0.00, guard $0.00; last agent call $0.22

## Fixture: personal-copy-outranks-repo (n=1)

- Prompt: The capture in this directory is from a cloud session where the repo's release-notes skill keeps ignoring a change that merged last week. Work out which copy of release-notes that session actually reads and where that copy came from, and write your findings to FINDINGS.md at the top of this directory. Include a line starting `Winning copy:` with the path, relative to this directory, of the SKILL.md the session reads, and a line starting `Source:` saying how that copy got where it is. Change nothing else.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 6/6 | skipped (objective-decided) | 0.4376 / 0.4376 |
| without_skill | 1 | 0 | 5/6 | skipped (objective-decided) | 0.2241 / 0.2241 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.4376 / 0.4376 | 0.2241 / 0.2241 | +0.2135 | +0.2135 |
| num_turns | 8 / 8 | 5 / 5 | +3 | +3 |
| duration_ms | 39839 / 39839 | 40766 / 40766 | -927 | -927 |
| input_tokens | 16 / 16 | 10 / 10 | +6 | +6 |
| output_tokens | 3498 / 3498 | 3252 / 3252 | +246 | +246 |
| cache_creation_input_tokens | 39109 / 39109 | 15616 / 15616 | +23493 | +23493 |
| cache_read_input_tokens | 273748 / 273748 | 170702 / 170702 | +103046 | +103046 |
| tool_errors | 1 / 1 | 0 / 0 | +1 | +1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-personal-copy-is-named-as-the-winner | 1/1 | 1/1 |
| the-winner-is-attributed-to-a-hand-copy | 1/1 | 0/1 |
| the-missing-section-is-named | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
| no-skill-was-added-to-the-personal-store | 1/1 | 1/1 |
