# Skill eval coverage census

| Registry | Skills | Covered | Skipped | GAP |
|---|---:|---:|---:|---:|
| adam-agentskills | 21 | 13 | 8 | 0 |
| cms-platform | 13 | 10 | 3 | 0 |
| adamdaniel.ai | 1 | 1 | 0 | 0 |
| adam-agentskills-private | 3 | 1 | 0 | 2 |
| **Total** | 38 | 25 | 11 | 2 |

## adam-agentskills

| Bundle | Skill | Status | Fixtures | Reason |
|---|---|---|---:|---|
| adam-anything-anywhere | finding-unknowns | covered | 1 |  |
| adam-anything-anywhere | writing-adrs | covered | 4 |  |
| adam-coding-anywhere | ci-job-performance | covered | 1 |  |
| adam-coding-anywhere | debug-github-workflows | covered | 4 |  |
| adam-coding-anywhere | disarm-inherited-reach | covered | 1 |  |
| adam-coding-anywhere | github-actions-repo-settings | covered | 1 |  |
| adam-coding-anywhere | review-bash-ci-reliability | covered | 4 |  |
| adam-coding-anywhere | skills-doctor | covered | 4 |  |
| adam-coding-anywhere | vendor-release-impact-issues | covered | 4 |  |
| adam-coding-anywhere | workflow-path-audit | covered | 4 |  |
| adam-coding-local | launch-top-level-claude-session | skipped | 0 | machine-bound (WSL/WPF/browser surfaces); faking the surface costs more than the churn justifies today |
| adam-coding-local | migrate-claude-memory | skipped | 0 | machine-bound (WSL/WPF/browser surfaces); faking the surface costs more than the churn justifies today |
| adam-coding-local | sync-cc-settings-between-wsl-and-windows | skipped | 0 | machine-bound (WSL/WPF/browser surfaces); faking the surface costs more than the churn justifies today |
| adam-coding-local | windows-elevation-from-wsl | covered | 1 |  |
| adam-non-coding-local | add-from-address | skipped | 0 | dispatches a workflow in the fastmail-actions repository that edits a real Fastmail account&#x27;s sending identities with a real API token; a hermetic fixture cannot exercise it |
| adam-non-coding-local | add-received-from-addresses | skipped | 0 | dispatches a workflow in the fastmail-actions repository that scans a real Fastmail mailbox and adds sending identities with a real API token; a hermetic fixture cannot exercise it |
| adam-non-coding-local | compare-pdfpairs | skipped | 0 | machine-bound (WSL/WPF/browser surfaces); faking the surface costs more than the churn justifies today |
| adam-non-coding-local | fastmail | skipped | 0 | credentialed live service; a fixture may not carry real accounts, and a faked Fastmail is a harness project of its own |
| adam-non-coding-local | ocr-pdfs | skipped | 0 | machine-bound (WSL/WPF/browser surfaces); faking the surface costs more than the churn justifies today |
| adam-non-coding-local | pdf-ocr-audit | covered | 1 |  |
| adam-non-coding-local | rename-pdfs | covered | 1 |  |

## cms-platform

| Bundle | Skill | Status | Fixtures | Reason |
|---|---|---|---:|---|
|  | admin-config-render | covered | 1 |  |
|  | aws-bootstrap | skipped | 0 | staleness is the failure mode, not procedure quality |
|  | browser-testing | covered | 1 |  |
|  | ci-watcher-loops | covered | 1 |  |
|  | cms-stuck-pr-triage | covered | 1 |  |
|  | code-quality | covered | 1 |  |
|  | consumer-repo-provisioning | covered | 1 |  |
|  | editorial-label-audit | covered | 1 |  |
|  | github-actions-sha-pinning | covered | 1 |  |
|  | platform-release-and-bump | covered | 1 |  |
|  | post-failure-comment | covered | 1 |  |
|  | preview-environments | skipped | 0 | staleness is the failure mode, not procedure quality |
|  | test-canary | skipped | 0 | internal canary; carries no guidance; no probe asserts its delivery (not built, untracked; closed issue #17 built other propagation arms) |

## adamdaniel.ai

| Bundle | Skill | Status | Fixtures | Reason |
|---|---|---|---:|---|
|  | embeddable-tool-pages | covered | 1 |  |

## adam-agentskills-private

Skill names withheld for this private registry; counts above. `--include-private-names` lists them.

## Problems

None.

## Fixture metadata readiness

- Fixtures: 91; draft: 11.
- Context declared: 24; missing: 67; guidance unproven: 0.
- Paired context delivery verified: no. These counts validate metadata only; ADR 0012 currently resolves context without delivering it to either arm.
