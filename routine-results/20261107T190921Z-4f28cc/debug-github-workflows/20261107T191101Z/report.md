# Eval report: debug-github-workflows

- Timestamp: 20261107T191101Z
- Trials per arm: 3
- Run: billing subscription, runner routine, location cloud, id 20261107T190921Z-4f28cc; started 2026-11-07T19:11:01Z, ended 2026-11-07T19:17:53Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.63 to 0.63, from 12 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $2.47 over 12 call(s); agent $1.73, judge $0.74, guard $0.00; last agent call $0.28

## Fixture: secret-name (n=3)

- Prompt: The Release notes workflow has failed on our last two releases. Fix it. Do not change remote state.
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 3 | 0 | 6/8 | 9.2 (8.8 to 9.8, 3 judged) | 0.2948 / 0.8845 |
| without_skill | 3 | 0 | 6/8 | 9.2 (8.8 to 9.8, 3 judged) | 0.2812 / 0.8437 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | 0.2948 / 0.2886 | 0.2812 / 0.2817 | +0.0136 | +0.0068 |
| num_turns | 7 / 7 | 7.3 / 7 | -0.3 | 0 |
| duration_ms | 51606.7 / 49164 | 43538 / 38474 | +8068.7 | +10690 |
| input_tokens | 14.7 / 14 | 14 / 14 | +0.7 | 0 |
| output_tokens | 3034.7 / 2944 | 3130.7 / 2930 | -96 | +14 |
| cache_creation_input_tokens | 22561.3 / 19739 | 20916.7 / 21258 | +1644.7 | -1519 |
| cache_read_input_tokens | 253793 / 247939 | 249200.3 / 265126 | +4592.7 | -17187 |
| tool_errors | 0.3 / 0 | 0.3 / 0 | 0 | 0 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| run-log-read-without-writes | 0/3 | 0/3 |
| secret-names-listed | 0/3 | 0/3 |
| workflow-reads-the-existing-secret | 3/3 | 3/3 |
| workflows-still-parse | 3/3 | 3/3 |
| permissions-stay-read-only | 3/3 | 3/3 |
| reply-names-both-secrets | 3/3 | 3/3 |
| everything-else-unchanged | 3/3 | 3/3 |
| instrument-unchanged | 3/3 | 3/3 |
