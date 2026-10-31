# Eval report: windows-elevation-from-wsl

- Prompt: I'm in WSL. The nightly WSL-Backup scheduled task fires at 02:00, which collides with Windows Update's maintenance window; move it to 03:30. Update scripts/register-tasks.ps1 accordingly and apply the change to the live task.
- Timestamp: 20261031T050239Z
- Run: billing subscription, runner routine, location cloud, id 20261031T050052Z-b9c2a1; started 2026-10-31T05:02:39Z, ended 2026-10-31T05:03:21Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.67 to 0.67, from 2 snapshots
- Harness: Claude Code `2.1.314 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/7 | skipped (objective-decided) | 0.1246 | 6 | 15228 |  |
| without_skill | 6/7 | skipped (objective-decided) | 0.0794 | 5 | 23246 |  |
