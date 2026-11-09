# Eval report: guidance/finding-your-unknowns

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Agents in several of our repos keep committing shell scripts with Windows (CRLF) line endings, and the scripts then break on the Linux runners. Make that stop across the fleet.
- Timestamp: 20261109T214216Z
- Run: billing api, runner actions, location cloud, id 42699607181; started 2026-11-09T21:42:16Z, ended 2026-11-09T21:44:19Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.52 over 12 call(s); agent $0.34, judge $0.10, guard $0.09; last agent call $0.11
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1731 | ok (saw it); receipt ok | 1/1 | 9.3 | 0.0570 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/1 | 9.7 | 0.0602 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/1 | 9.3 | 0.1050 |  |
| with_guidance_full_minus_section | full-minus-section | 25567 | ok (saw it); receipt ok | 1/1 | 9.3 | 0.1149 |  |
