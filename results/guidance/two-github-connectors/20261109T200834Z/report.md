# Eval report: guidance/two-github-connectors

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Both GitHub MCP servers are connected in this session: mcp__github__ and the claude.ai organization connector. A get_file_contents call for README.md in example-org/ledger-service through mcp__github__ just returned 404. In a few lines: is the repository gone, and what do you do next?
- Timestamp: 20261109T200834Z
- Run: billing api, runner actions, location cloud, id 42686615747; started 2026-11-09T20:08:34Z, ended 2026-11-09T20:09:30Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.33 over 12 call(s); agent $0.19, judge $0.06, guard $0.09; last agent call $0.06
- Harness: Claude Code `2.1.321 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 1999 | ok (saw it); receipt ok | 1/2 | 6.7 | 0.0459 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 1/2 | 6.7 | 0.0289 |  |
| with_guidance_full | full | 26582 | ok (saw it); receipt ok | 1/2 | 8.0 | 0.0553 |  |
| with_guidance_full_minus_section | full-minus-section | 25299 | ok (saw it); receipt ok | 1/2 | 6.7 | 0.0554 |  |
