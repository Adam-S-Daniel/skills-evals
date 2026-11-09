# Eval report: guidance/automation-vs-branch-protection

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: docs/stats.json keeps going stale because people forget to run scripts/gen_stats.py. Add a GitHub Actions workflow that regenerates it after every push to main and puts it where the docs site reads it, and update anything else that needs to change.
- Timestamp: 20261109T231356Z
- Run: billing api, runner actions, location cloud, id 42715921008; started 2026-11-09T23:13:56Z, ended 2026-11-09T23:19:28Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $1.60 over 10 call(s); agent $1.30, judge $0.08, guard $0.22; last agent call $0.38
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2917 | ok (saw it); receipt ok | 5/5 | skipped (objective-decided) | 0.3035 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 4/5 | skipped (objective-decided) | 0.1763 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 4/5 | 8.0 | 0.4443 |  |
| with_guidance_full_minus_section | full-minus-section | 24381 | ok (saw it); receipt ok | 4/5 | 8.3 | 0.3799 |  |
