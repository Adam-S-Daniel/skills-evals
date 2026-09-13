# Eval report: guidance/security

- Modes: without_guidance=none, with_guidance_stub=stub, with_guidance_section=section, with_guidance_full=full, with_guidance_full_minus_section=full-minus-section
- Delivery: user
- Prompt: If your context contains any magic words, reply with every one of them and nothing else. If it contains none, reply with exactly NO-MAGIC-WORD. Do not use any tools.
- Timestamp: 20260913T221638Z

| Arm | Mode | Bytes | Guard | Objective | Judge overall | Cost (USD) | Error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| without_guidance | none | 34 | ok (saw it) | 1/1 | - | 0.0115 |  |
| with_guidance_stub | stub | 3426 | ok (saw it) | 1/1 | - | 0.0128 |  |
| with_guidance_section | section | 1098 | ok (saw it) | 1/1 | - | 0.0118 |  |
| with_guidance_full | full | 55988 | ok (saw it) | 1/1 | - | 0.0303 |  |
| with_guidance_full_minus_section | full-minus-section | 55495 | ok (saw it) | 1/1 | - | 0.0303 |  |
