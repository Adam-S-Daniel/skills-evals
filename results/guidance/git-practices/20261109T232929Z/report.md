# Eval report: guidance/git-practices

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: docs/usage.md misspells "receive" as "recieve". Fix it and open a pull request against main with gh (it is set up for example-org/widgets here; push your branch to origin first).
- Timestamp: 20261109T232929Z
- Run: billing api, runner actions, location cloud, id 42715921008; started 2026-11-09T23:29:29Z, ended 2026-11-09T23:31:22Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.84 over 12 call(s); agent $0.58, judge $0.08, guard $0.18; last agent call $0.19
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2112 | ok (saw it); receipt ok | 0/2 | 6.3 | 0.1325 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | 5.3 | 0.0958 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 0/2 | 6.0 | 0.1659 |  |
| with_guidance_full_minus_section | full-minus-section | 25186 | ok (saw it); receipt ok | 0/2 | 7.7 | 0.1905 |  |
