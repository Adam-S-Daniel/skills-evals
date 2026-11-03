# Eval report: guidance/section-go

- Modes: with_guidance_section=section, without_guidance=none, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: Add FetchUser(id) to users.go: it GETs BaseURL + "/users/" + id and decodes the JSON body into a User. Add a test for it in users_test.go using httptest.
- Timestamp: 20261103T054351Z
- Run: billing api, runner actions, location cloud, id 41585078142; started 2026-11-03T05:43:51Z, ended 2026-11-03T05:48:54Z
- Account meter: no change recorded (API-billed run: the subscription's account meter does not apply)
- Estimated cost (an estimate from the CLI's own per-call dollar figures, not a meter reading): $0.90 over 8 call(s); agent $0.69, judge $0.00, guard $0.21; last agent call $0.26
- Harness: Claude Code `2.1.317 (Claude Code)`; models used: with_guidance_section=claude-opus-5-5; without_guidance=claude-opus-5-5; with_guidance_full=claude-haiku-5-5, claude-opus-5-5; with_guidance_full_minus_section=claude-haiku-5-5, claude-opus-5-5

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| with_guidance_section | section | 347 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.1221 |  |
| without_guidance | none | 34 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.1055 |  |
| with_guidance_full | full | 25875 | ok (saw it); receipt ok | 2/2 | skipped (objective-decided) | 0.2042 |  |
| with_guidance_full_minus_section | full-minus-section | 25562 | ok (saw it); receipt ok | 0/2 | skipped (objective-decided) | 0.2605 |  |
