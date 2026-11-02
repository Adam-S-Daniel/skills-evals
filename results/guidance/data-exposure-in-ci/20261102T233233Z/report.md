# Eval report: guidance/data-exposure-in-ci

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: scripts/sync_contacts.py dies with a bare traceback whenever the CRM rejects a sync, and the nightly run's log never says why. Make it catch the API error, print enough that I can tell from the Actions log why the sync failed, and exit non-zero.
- Timestamp: 20261102T233233Z
- Run: billing api, runner actions, location cloud, id 41545985180; started 2026-11-02T23:32:33Z, ended 2026-11-02T23:34:21Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.58 over 12 call(s); agent $0.29, judge $0.18, guard $0.11; last agent call $0.10
- Harness: Claude Code `2.1.316 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1913 | ok (saw it); receipt ok | 3/3 | 8.3 | 0.0489 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 3/3 | 3.0 | 0.0512 |  |
| with_guidance_full | full | 25562 | ok (saw it); receipt ok | 3/3 | 8.0 | 0.0952 |  |
| with_guidance_full_minus_section | full-minus-section | 24365 | ok (saw it); receipt ok | 3/3 | 8.3 | 0.0957 |  |
