# Skill eval coverage census

| Registry | Skills | Covered | Skipped | GAP |
|---|---:|---:|---:|---:|
| adam-agentskills | 24 | 16 | 7 | 1 |
| cms-platform | 13 | 10 | 3 | 0 |
| adamdaniel.ai | 1 | 1 | 0 | 0 |
| adam-agentskills-private | 3 | 1 | 0 | 2 |
| **Total** | 41 | 28 | 10 | 3 |

## adam-agentskills

| Bundle | Skill | Status | Fixtures | Reason |
|---|---|---|---:|---|
| adam-anything-anywhere | finding-unknowns | covered | 1 |  |
| adam-anything-anywhere | writing-adrs | covered | 5 |  |
| adam-coding-anywhere | ci-job-performance | covered | 5 |  |
| adam-coding-anywhere | debug-github-workflows | covered | 4 |  |
| adam-coding-anywhere | disarm-inherited-reach | covered | 1 |  |
| adam-coding-anywhere | fan-out-triage | covered | 5 |  |
| adam-coding-anywhere | github-actions-repo-settings | covered | 4 |  |
| adam-coding-anywhere | red-ci-adamdaniel-ai | covered | 5 |  |
| adam-coding-anywhere | review-bash-ci-reliability | covered | 6 |  |
| adam-coding-anywhere | skills-doctor | covered | 5 |  |
| adam-coding-anywhere | vendor-release-impact-issues | covered | 4 |  |
| adam-coding-anywhere | workflow-path-audit | covered | 6 |  |
| adam-coding-local | launch-top-level-claude-session | GAP | 0 |  |
| adam-coding-local | migrate-claude-memory | skipped | 0 | rechecked 2026-11-05, holds on criterion 1 only: one recorded local use since 2026-09-14 (week of 2026-09-21). Its surface is Bash over ~/.claude/projects, which a fake HOME can stand in for, so reopen it if use grows |
| adam-coding-local | sync-cc-settings-between-wsl-and-windows | skipped | 0 | rechecked 2026-11-05, holds: fails criterion 1 (no recorded local use since 2026-09-14) and criterion 3 (needs Windows PowerShell 7 and the WSL UNC share, which a fixture cannot fake cheaply) |
| adam-coding-local | tool-powershell | covered | 8 |  |
| adam-coding-local | windows-elevation-from-wsl | covered | 1 |  |
| adam-non-coding-local | add-from-address | skipped | 0 | rechecked 2026-11-06, holds: fails criterion 3 (it dispatches a workflow in the fastmail-actions repository that edits a real Fastmail account&#x27;s sending identities with a real API token; a hermetic fixture cannot exercise it) and criterion 1 (no recorded local use since 2026-09-14) |
| adam-non-coding-local | add-received-from-addresses | skipped | 0 | dispatches a workflow in the fastmail-actions repository that scans a real Fastmail mailbox and adds sending identities with a real API token; a hermetic fixture cannot exercise it |
| adam-non-coding-local | compare-pdfpairs | skipped | 0 | rechecked 2026-11-05, holds on criterion 1 only: no recorded local use since 2026-09-14. Its surface (PowerShell 7 and poppler over a folder of PDFs) can be faked in a container, so reopen it if it is used |
| adam-non-coding-local | fastmail | skipped | 0 | rechecked 2026-11-06, holds: fails criterion 3 (credentialed live service; a fixture may not carry real accounts, and a faked Fastmail is a harness project of its own) and criterion 1 (one recorded local use since 2026-09-14, in the week of 2026-09-14) |
| adam-non-coding-local | ocr-pdfs | skipped | 0 | rechecked 2026-11-06, holds on criterion 1 only: no recorded local use since 2026-09-14. The machine-bound reason no longer fits: the skill calls the OCRmyPDF CLI directly, which a container can run, so reopen it if it is used |
| adam-non-coding-local | pdf-ocr-audit | covered | 1 |  |
| adam-non-coding-local | rename-pdfs | covered | 1 |  |

## cms-platform

| Bundle | Skill | Status | Fixtures | Reason |
|---|---|---|---:|---|
|  | admin-config-render | covered | 1 |  |
|  | aws-bootstrap | skipped | 0 | rechecked 2026-11-07, holds: fails criterion 3 (the procedure acts on live AWS with real credentials, which a hermetic fixture cannot score) and criterion 2 (its failure mode, staleness, is now checked by cms-platform&#x27;s e2e/skill-references-fresh.test.js and adam-agentskills&#x27; scheduled scripts/check\_skill\_freshness.py); no recorded use, local since 2026-09-14 or cloud since 2026-11-02 |
|  | browser-testing | covered | 1 |  |
|  | ci-watcher-loops | covered | 1 |  |
|  | cms-stuck-pr-triage | covered | 1 |  |
|  | code-quality | covered | 1 |  |
|  | consumer-repo-provisioning | covered | 1 |  |
|  | editorial-label-audit | covered | 1 |  |
|  | github-actions-sha-pinning | covered | 1 |  |
|  | platform-release-and-bump | covered | 1 |  |
|  | post-failure-comment | covered | 1 |  |
|  | preview-environments | skipped | 0 | rechecked 2026-11-07, holds: fails criterion 3 (the procedure acts on live AWS with real credentials, which a hermetic fixture cannot score) and criterion 2 (its failure mode, staleness, is now checked by cms-platform&#x27;s e2e/skill-references-fresh.test.js and adam-agentskills&#x27; scheduled scripts/check\_skill\_freshness.py); no recorded use, local since 2026-09-14 or cloud since 2026-11-02 |
|  | test-canary | skipped | 0 | rechecked 2026-11-07, holds: fails criterion 3 (the skill is a no-op marker, so a with arm has nothing to score) and criterion 5 (a verdict would change nothing); internal canary; carries no guidance; no probe asserts its delivery (not built, untracked; closed issue #17 built other propagation arms) |

## adamdaniel.ai

| Bundle | Skill | Status | Fixtures | Reason |
|---|---|---|---:|---|
|  | embeddable-tool-pages | covered | 1 |  |

## adam-agentskills-private

Skill names withheld for this private registry; counts above. `--include-private-names` lists them.

## Problems

None.

## Fixture metadata readiness

- Fixtures: 156; draft: 11.
- Context declared: 76; missing: 80; guidance unproven: 0.
- Paired context delivery verified: no. These counts validate metadata only; ADR 0012 currently resolves context without delivering it to either arm.
