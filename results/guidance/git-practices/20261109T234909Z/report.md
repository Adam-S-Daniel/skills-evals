# Eval report: guidance/git-practices

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: docs/usage.md misspells "receive" as "recieve". Fix it and open a pull request against main with gh (it is set up for example-org/widgets here; push your branch to origin first).
- Timestamp: 20261109T234909Z
- Run: billing api, runner actions, location cloud, id 42718601638; started 2026-11-09T23:49:09Z, ended 2026-11-09T23:50:47Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.43 over 12 call(s); agent $0.27, judge $0.07, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 2112 | ok (saw it); receipt ok | 0/2 | 6.7 | 0.0715 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | 5.0 | 0.0432 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 0/2 | 4.7 | 0.0811 |  |
| with_guidance_full_minus_section | full-minus-section | 25186 | ok (saw it); receipt ok | 0/2 | 5.7 | 0.0783 |  |
