# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add .github/workflows/send-report.yml: a workflow I can run by hand from the Actions tab that takes the recipient's email address as an input and runs scripts/send_report.py --to with that address.
- Timestamp: 20261102T174229Z
- Run: billing subscription, runner routine, location cloud, id 20261102T174114Z-ac5242; started 2026-11-02T17:42:29Z, ended 2026-11-02T17:45:08Z
- Account meter (account-wide, so anything else the account ran is in it; read as each agent, judge or guard call starts, so the 1 call(s) from the last reading on are not in it): seven_day 0.01 to 0.01, from 8 snapshots
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.33 over 8 call(s); agent $0.98, judge $0.00, guard $0.35; last agent call $0.25
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-haiku-5-5, claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1913 | ok (saw it); receipt ok | 5/6 | skipped (objective-decided) | 0.2993 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/6 | skipped (objective-decided) | 0.1216 |  |
| with_guidance_full | full | 25546 | ok (saw it); receipt ok | 5/6 | skipped (objective-decided) | 0.3053 |  |
| with_guidance_full_minus_section | full-minus-section | 24349 | ok (saw it); receipt ok | 4/6 | skipped (objective-decided) | 0.2540 |  |
