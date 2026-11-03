# Eval report: pdf-ocr-audit

- Prompt: Audit archive/ and tell me which PDFs need OCR. Save the results in audit.md.
- Timestamp: 20261103T070940Z
- Run: billing subscription, runner routine, location cloud, id 20261103T070758Z-372c4e; started 2026-11-03T07:09:40Z, ended 2026-11-03T07:10:56Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.35 to 0.35, from 2 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.28 over 2 call(s); agent $0.28, judge $0.00, guard $0.00; last agent call $0.10
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_skill=claude-sonnet-5-5; without_skill=claude-sonnet-5-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 11/13 | skipped (objective-decided) | 0.1753 | 9 | 45282 |  |
| without_skill | 1/13 | skipped (objective-decided) | 0.1002 | 6 | 27506 |  |
