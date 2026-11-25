# Eval report: workflow-path-audit

- Timestamp: 20261125T113339Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261125T113222Z-85849d; started 2026-11-25T11:33:39Z, ended 2026-11-25T11:37:09Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.17 to 0.17, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.14 over 2 call(s); agent $1.14, judge $0.00, guard $0.00; last agent call $0.55
- Estimated allowance (approximate, from token counts by type, weight table 2026-11-20): 0.06 points of the weekly meter (0.05 to 0.09); Fable meter 0.00 points

## Fixture: companion-skip-pair (n=1)

- Prompt: Check that the path filters on this repo's GitHub Actions workflows are right, and fix whatever isn't.
- Harness: Claude Code `2.1.332 (Claude Code)`; models used: with_skill=none recorded; without_skill=none recorded

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 1 | - | - | -; 1 unknown |
| without_skill | 1 | 1 | - | - | -; 1 unknown |

Errored trials are counted in n and excluded from score means; known costs from all trials are counted:

- with_skill trial 1: agent_wrote_agent_config: the agent wrote .claude/worktrees/workflow-path-audit/.editorconfig, .claude/worktrees/workflow-path-audit/.gh/replay/api/repos/example-org/example-service/rules/branches/ma…
- without_skill trial 1: agent_wrote_agent_config: the agent wrote .claude/worktrees/fix-workflow-path-filters/.editorconfig, .claude/worktrees/fix-workflow-path-filters/.gh/replay/api/repos/example-org/example-service/rules…
