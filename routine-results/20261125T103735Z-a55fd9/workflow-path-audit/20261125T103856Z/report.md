# Eval report: workflow-path-audit

- Timestamp: 20261125T103856Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T103735Z-a55fd9; started 2026-11-25T10:38:56Z, ended 2026-11-25T10:43:22Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 3 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.33 over 3 call(s); agent $1.20, judge $0.13, guard $0.00; last agent call $0.66
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.08 points of the weekly meter (0.06 to 0.11); Fable meter 0.02 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=none recorded; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 1 | - | - | -; 1 unknown |
| without_skill | 1 | 0 | 8/8 | 8.4 (8.4 to 8.4, 1 judged) | 0.6593 / 0.6593 |

Efficiency per trial (a trial that did not report a metric is left out and the cell says how many did; delta is with_skill minus without_skill):

| Metric (mean / median) | with_skill | without_skill | Delta mean | Delta median |
| --- | --- | --- | --- | --- |
| cost_usd | - | 0.6593 / 0.6593 | - | - |
| num_turns | - | 10 / 10 | - | - |
| duration_ms | - | 163600 / 163600 | - | - |
| input_tokens | - | 22 / 22 | - | - |
| output_tokens | - | 12581 / 12581 | - | - |
| cache_creation_input_tokens | - | 37121 / 37121 | - | - |
| cache_read_input_tokens | - | 454606 / 454606 | - | - |
| tool_errors | - | 7 / 7 | - | - |

Errored trials are counted in n and excluded from score means; known costs from all trials are counted:

- with_skill trial 1: agent_wrote_agent_config: the agent wrote .claude/worktrees/workflow-path-audit/.editorconfig, .claude/worktrees/workflow-path-audit/.gh/replay/api/repos/example-org/example-service/rules/branches/ma…

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| required-check-gates-inside-one-workflow | - | 1/1 |
| companion-skip-workflow-removed | - | 1/1 |
| docs-change-still-reports-the-required-check | - | 1/1 |
| source-change-skips-the-docs-site | - | 1/1 |
| workflows-still-parse | - | 1/1 |
| event-only-workflows-unfiltered | - | 1/1 |
| ruleset-unchanged | - | 1/1 |
| project-files-unchanged | - | 1/1 |
