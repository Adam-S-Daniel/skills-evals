# Eval report: guidance/section-go

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add FetchUser(id) to users.go: it GETs BaseURL + "/users/" + id and decodes the JSON body into a User. Add a test for it in users_test.go using httptest.
- Timestamp: 20261103T030342Z
- Run: billing api, runner actions, location cloud, id 41568178365; started 2026-11-03T03:03:42Z, ended 2026-11-03T03:06:04Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.34 over 8 call(s); agent $0.25, judge $0.00, guard $0.09; last agent call $0.08
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-sonnet-5-5; without_guidance=claude-sonnet-5-5; with_guidance_full=claude-sonnet-5-5; with_guidance_full_minus_section=claude-sonnet-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 347 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.0511 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0429 |  |
| with_guidance_full | full | 25875 | ok (saw it); receipt ok | 1/2 | skipped (objective-decided) | 0.0807 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.0773 |  |
