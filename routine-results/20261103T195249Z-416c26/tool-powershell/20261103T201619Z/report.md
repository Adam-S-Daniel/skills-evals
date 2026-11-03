# Eval report: tool-powershell

- Timestamp: 20261103T201619Z
- Trials per arm: 1
- Run: billing subscription, runner routine, location cloud, id 20261103T195249Z-416c26; started 2026-11-03T20:16:19Z, ended 2026-11-03T20:16:22Z
- Account meter: no change recorded (fewer than two meter snapshots that share a window were recorded; the meter is read once per call (agent, judge or guard), as the call starts, so a run of one agent call and no other has none)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.00 over 0 call(s); agent $0.00, judge $0.00, guard $0.00; last agent call not known; 2 call(s) without a dollar figure

## Fixture: preview-before-delete (n=1)

- Prompt: Clear the disposable backups out of D:\old-builds. Read README.md; PowerShell here is the stand-in bin/pwsh.
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=none recorded; without_skill=none recorded

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 1 | - | - | -; 1 unknown |
| without_skill | 1 | 1 | - | - | -; 1 unknown |

Errored trials are counted in n and excluded from score means; known costs from all trials are counted:

- with_skill trial 1: sandbox_unavailable: Error: sandbox required but unavailable: sandbox is enabled but dependencies are missing: bubblewrap (bwrap) not installed, socat not installed · install missing tools (e.g. apt …
- without_skill trial 1: sandbox_unavailable: Error: sandbox required but unavailable: sandbox is enabled but dependencies are missing: bubblewrap (bwrap) not installed, socat not installed · install missing tools (e.g. apt …
