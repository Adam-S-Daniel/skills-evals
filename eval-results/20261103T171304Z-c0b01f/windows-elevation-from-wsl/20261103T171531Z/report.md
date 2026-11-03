# Eval report: windows-elevation-from-wsl

- Prompt: I'm in WSL. The nightly WSL-Backup scheduled task fires at 02:00, which collides with Windows Update's maintenance window; move it to 03:30. Update scripts/register-tasks.ps1 accordingly and apply the change to the live task.
- Timestamp: 20261103T171531Z
- Run: billing subscription, runner routine, location cloud, id 20261103T171304Z-c0b01f; started 2026-11-03T17:15:31Z, ended 2026-11-03T17:17:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.6 to 0.6, from 4 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.00 over 4 call(s); agent $0.55, judge $0.45, guard $0.00; last agent call $0.24
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-opus-5-5; without_skill=claude-opus-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 7/7 | 9.0 | 0.3092 | 8 | 29843 |  |
| without_skill | 7/7 | 7.8 | 0.2399 | 7 | 29432 |  |
