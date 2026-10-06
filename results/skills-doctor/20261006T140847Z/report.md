# Eval report: skills-doctor

- Timestamp: 20261006T140847Z
- Trials per arm: 1

## Fixture: bucketed-account-store (n=1)

- Prompt: The capture in this directory is from a laptop where writing-adrs has started leaving a section out of the ADRs it writes, though the registry copy still asks for it. Work out what is actually being delivered to that session and why, and write your findings to FINDINGS.md at the top of this directory. Change nothing else.
- Harness: Claude Code `2.1.291 (Claude Code)`; models used: with_skill=claude-sonnet-5; without_skill=claude-sonnet-5

| Arm | n | Errors | Objective (mean) | Judge overall (mean, min to max) | Cost USD (mean / sum) |
| --- | --- | --- | --- | --- | --- |
| with_skill | 1 | 0 | 4/5 | 9.2 (9.2 to 9.2, 1 judged) | 0.2103 / 0.2103 |
| without_skill | 1 | 0 | 4/5 | 8.2 (8.2 to 8.2, 1 judged) | 0.1283 / 0.1283 |

| Check (passed / scored) | with_skill | without_skill |
| --- | --- | --- |
| findings-written | 1/1 | 1/1 |
| the-account-store-was-read-not-called-empty | 0/1 | 0/1 |
| the-duplicated-skill-is-named-with-its-two-sources | 1/1 | 1/1 |
| the-missing-section-is-identified | 1/1 | 1/1 |
| nothing-in-the-capture-was-repaired | 1/1 | 1/1 |
