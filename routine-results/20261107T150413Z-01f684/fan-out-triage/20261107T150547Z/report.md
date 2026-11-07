# Eval report: fan-out-triage

- Timestamp: 20261107T150547Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T150413Z-01f684; started 2026-11-07T15:05:47Z, ended 2026-11-07T15:14:14Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 2 call(s) from the last reading on are not in it): seven_day 0.48 to 0.48, from 11 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.41 over 11 call(s); agent $1.65, judge $0.76, guard $0.00; last agent call $0.27; 1 call(s) without a dollar figure

## Fixture: single-file (n=3)

- Prompt: The release notes for acme 2.x are in notes/acme-2.x.md and this repo builds and ships with acme. Go through the notes and work out which items affect us and in which file. Put the working files under triage/ and the final answer in triage/results.tsv; I will review it item by item, so make it easy to check against the notes.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 1/6 | 9.1 (9.0 to 9.4, 3 judged) | 0.2619 / 0.7858 |
| without_skill | 3 | 0 | 1/6 | 9.0 (9.0 to 9.0, 2 judged); 1 judge error(s) | 0.2890 / 0.8670 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2619 / 0.2366 | 0.2890 / 0.2797 | -0.0271 | -0.0431 |
| num_turns | 5 / 5 | 7.7 / 8 | -2.7 | -3 |
| duration_ms | 43372 / 41739 | 59990 / 59596 | -16618 | -17857 |
| input_tokens | 10 / 10 | 15.3 / 16 | -5.3 | -6 |
| output_tokens | 3771.3 / 3799 | 4978 / 4727 | -1206.7 | -928 |
| cache_creation_input_tokens | 19081 / 15671 | 16758 / 16264 | +2323 | -593 |
| cache_read_input_tokens | 169168.3 / 172137 | 276632.3 / 288017 | -107464 | -115880 |
| tool_errors | 0.3 / 0 | 1 / 1 | -0.7 | -1 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| inventory-cites-real-lines | 0/3 | 0/3 |
| results-follow-the-contract | 0/3 | 0/3 |
| ids-match-their-source-text | 0/3 | 0/3 |
| affected-items-found-and-decoys-not-strong | 0/3 | 0/3 |
| read-count-is-the-item-count | 0/3 | 0/3 |
| repo-and-notes-untouched | 3/3 | 3/3 |
