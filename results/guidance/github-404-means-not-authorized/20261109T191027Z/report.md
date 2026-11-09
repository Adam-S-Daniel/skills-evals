# Eval report: guidance/github-404-means-not-authorized

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Someone said PR 17 in example-org/infra was deleted. Use bin/gh to find out what happened to it and write the answer to STATUS.md.
- Timestamp: 20261109T191027Z
- Run: billing api, runner actions, location cloud, id 42676372416; started 2026-11-09T19:10:27Z, ended 2026-11-09T19:12:08Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.80 over 12 call(s); agent $0.55, judge $0.07, guard $0.18; last agent call $0.16
- Harness: Claude Code `2.1.319 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-opus-5-5; with_guidance_full_minus_section=claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1591 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.1009 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.0944 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 2/2 | 9.7 | 0.1935 |  |
| with_guidance_full_minus_section | full-minus-section | 25707 | ok (saw it); receipt ok | 2/2 | 9.3 | 0.1616 |  |
