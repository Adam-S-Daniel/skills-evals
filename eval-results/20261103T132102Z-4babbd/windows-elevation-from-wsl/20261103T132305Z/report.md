# Eval report: windows-elevation-from-wsl

- Prompt: I'm in WSL. The nightly WSL-Backup scheduled task fires at 02:00, which collides with Windows Update's maintenance window; move it to 03:30. Update scripts/register-tasks.ps1 accordingly and apply the change to the live task.
- Timestamp: 20261103T132305Z
- Run: billing subscription, runner routine, location cloud, id 20261103T132102Z-4babbd; started 2026-11-03T13:23:05Z, ended 2026-11-03T13:24:50Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.43 to 0.43, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.60 over 2 call(s); agent $0.60, judge $0.00, guard $0.00; last agent call $0.29
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-haiku-5-5, claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/7 | skipped (objective-decided) | 0.3126 | 8 | 32728 |  |
| without_skill | 6/7 | skipped (objective-decided) | 0.2878 | 8 | 66405 |  |
