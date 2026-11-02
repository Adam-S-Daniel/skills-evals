# Eval report: pdf-ocr-audit

- Prompt: Audit archive/ and tell me which PDFs need OCR. Save the results in audit.md.
- Timestamp: 20261102T232307Z
- Run: billing subscription, runner routine, location cloud, id 20261102T232211Z-058dea; started 2026-11-02T23:23:07Z, ended 2026-11-02T23:24:06Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.24 to 0.24, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.21 over 2 call(s); agent $0.21, judge $0.00, guard $0.00; last agent call $0.08
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_skill=claude-haiku-5-5, claude-sonnet-5-5; without_skill=claude-haiku-5-5, claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 13/13 | skipped (objective-decided) | 0.1235 | 10 | 33382 |  |
| without_skill | 1/13 | skipped (objective-decided) | 0.0845 | 5 | 23127 |  |
