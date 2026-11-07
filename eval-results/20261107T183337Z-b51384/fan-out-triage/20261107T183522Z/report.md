# Eval report: fan-out-triage

- Timestamp: 20261107T183522Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T183337Z-b51384; started 2026-11-07T18:35:22Z, ended 2026-11-07T18:40:59Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.61, from 6 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.75 over 6 call(s); agent $1.75, judge $0.00, guard $0.00; last agent call $0.29

## Fixture: single-file (n=3)

- Prompt: The release notes for acme 2.x are in notes/acme-2.x.md and this repo builds and ships with acme. Go through the notes and work out which items affect us and in which file. Put the working files under triage/ and the final answer in triage/results.tsv; I will review it item by item, so make it easy to check against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 2.7/6 | skipped (objective-decided) | 0.2990 / 0.8969 |
| without_skill | 3 | 0 | 1/6 | skipped (objective-decided) | 0.2842 / 0.8525 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2990 / 0.2609 | 0.2842 / 0.2843 | +0.0148 | -0.0234 |
| num_turns | 6.3 / 6 | 7 / 7 | -0.7 | -1 |
| duration_ms | 51633 / 50755 | 56001.7 / 55255 | -4368.7 | -4500 |
| input_tokens | 12.7 / 12 | 14 / 14 | -1.3 | -2 |
| output_tokens | 4495.3 / 4321 | 5068.3 / 5149 | -573 | -828 |
| cache_creation_input_tokens | 20854 / 16456 | 16596.3 / 16434 | +4257.7 | +22 |
| cache_read_input_tokens | 210916 / 214078 | 249836 / 248984 | -38920 | -34906 |
| tool_errors | 0 / 0 | 0 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 1/3 | 0/3 |
| results-follow-the-contract | 1/3 | 0/3 |
| ids-match-their-source-text | 1/3 | 0/3 |
| affected-items-found-and-decoys-not-strong | 1/3 | 0/3 |
| read-count-is-the-item-count | 1/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
