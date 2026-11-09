# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: scripts/sync_contacts.py dies with a bare traceback whenever the CRM rejects a sync, and the nightly run's log never says why. Make it catch the API error, print enough that I can tell from the Actions log why the sync failed, and exit non-zero.
- Timestamp: 20261109T202630Z
- Run: billing api, runner actions, location cloud, id 42691880503; started 2026-11-09T20:26:30Z, ended 2026-11-09T20:29:18Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.04 over 10 call(s); agent $0.79, judge $0.07, guard $0.18; last agent call $0.27
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1913 | ok (saw it); receipt ok | 3/3 | skipped (objective-decided) | 0.1251 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/3 | skipped (objective-decided) | 0.1729 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 3/3 | 8.0 | 0.2293 |  |
| with_guidance_full_minus_section | full-minus-section | 25385 | ok (saw it); receipt ok | 3/3 | 8.7 | 0.2654 |  |
