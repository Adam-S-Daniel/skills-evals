# Eval report: workflow-path-audit

- Prompt: Audit this repository's GitHub Actions workflows and make each one trigger only when a file it actually depends on has changed.
- Timestamp: 20261006T140444Z
- Harness: Claude Code `2.1.291 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | Objective | Judge overall | Cost (USD) | Turns | Duration (ms) | Error |
| --- | --- | --- | --- | --- | --- | --- |
| with_skill | 8/8 | 9.7 | 0.1854 | 19 | 53603 |  |
| without_skill | 8/8 | 8.9 | 0.2320 | 13 | 122204 |  |
