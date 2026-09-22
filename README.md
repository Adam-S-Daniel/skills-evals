# skills-evals — `eval-results`

**This branch carries published output only. It must never carry source.**

Fleet policy (`AGENTS.md`, "Automation vs branch protection"): generated data —
badges, run summaries, reports, dashboards — belongs on a dedicated unprotected
results branch, and consumers read from that branch and treat its content as
untrusted. This is that branch for `skills-evals`.

| Path | Written by | What it is |
|---|---|---|
| `badges/` | `.github/workflows/eval.yml` → `scripts/make_badge.py` | shields.io endpoint JSON, linked from READMEs |
| `results/` | `.github/workflows/eval.yml` → `harness/run_eval.py` | one directory per A/B eval run: `report.md` + per-arm `summary.json` |
| `propagation/` | the Tier-3 account propagation audit | dated account-store snapshots + `latest.json` |
| `.gitignore` | — | **load-bearing.** Keeps `results/**/transcripts/` and `results/**/*.jsonl` out of the commit. This is a public repo; raw agent transcripts must not be published here. Do not delete it. |

Source lives on `main`. Read the harness, the fixtures and the docs there.

## What each fixture measures

The plain-English guide is
[`docs/how-it-works.md` on `main`](https://github.com/Adam-S-Daniel/skills-evals/blob/main/docs/how-it-works.md):
what a run does, how every fixture is scored, what is left and what it costs.
The short version, so a reader of this branch can place a `results/` directory
(inventory of 2026-09-22; "objective" is the number of scripted pass/fail
checks on the finished workspace, "judge" the rubric dimensions a second
model scores, "runs" the count of real runs published here):

| Fixture (`results/<key>/`) | Skill or section measured | Objective | Judge | Runs |
|---|---|---|---|---|
| `workflow-path-audit` | `workflow-path-audit` (agentskills): make each Actions workflow trigger only on files it depends on | 8 | completeness 0.5, salience 0.3, restraint 0.2 | 14, weekly |
| `guidance/_delivery` | fleet-guidance delivery canary, one arm per delivery mode: does the hook really put guidance in context | 5 | none | 1 |
| `rename-pdfs` | `rename-pdfs` (agentskills): rename scanned PDFs to the date-type-issuer convention, body date over filename date | 8 | convention fidelity 0.5, date priority 0.3, restraint 0.2 | none yet |
| `post-failure-comment` | `post-failure-comment` (cms-platform): wire CI failure comments through the platform action with correct gating | 11 | convention fidelity 0.5, gitleaks explanation 0.2, restraint 0.3 | none yet |
| `github-actions-sha-pinning` | `github-actions-sha-pinning` (cms-platform): pin third-party actions to full SHAs, keep the cms-platform carve-out | 9 | carve-out 0.4, comment removal 0.3, restraint 0.3 | none under this name (6 under its predecessor) |
| `disarm-inherited-reach` | `disarm-inherited-reach` (agentskills): make a scratch checkout unable to reach the real remote before running a destructive script | 8 | procedure fidelity 0.5, restraint 0.2, explanation 0.3 | none yet |
| `review-bash-ci-reliability` | `review-bash-ci-reliability` (agentskills): find and fix the seeded shell reliability bugs, leave the decoys | 10 | correctness 0.5, restraint 0.2, explanation 0.3 | none yet |
| `writing-adrs` (two fixtures) | `writing-adrs` (agentskills): record a decision as an ADR, bootstrapping the folder or following the house convention | 9 and 7 | decision with alternatives 0.5, title is a decision 0.3, restraint 0.2 | none yet |
| `adam-writing-style` (three fixtures) | `adam-writing-style` (agentskills): a bio, a recruiter reply, a self-appraisal opening in the author's voice | 3, 4, 3 | pairwise rank against reference samples: specificity, register, no filler | none yet |
| `cms-stuck-pr-triage` | `cms-stuck-pr-triage` (cms-platform): diagnose three stuck PRs against a replay-only fake `gh`, attempt no writes | 7 | root cause 0.4, decisions 0.4, restraint 0.2 | none yet |
| `windows-elevation-from-wsl` | `windows-elevation-from-wsl` (agentskills): change a scheduled Windows task from WSL, hand off the elevated step correctly | 7 | diagnosis 0.4, handoff 0.4, restraint 0.2 | none yet |

Each run's `report.md` shows both arms' objective score, judge score, cost in
dollars, turns and duration; `badges/<fixture>.json` averages the newest five.

## Why there is nothing else here

Until 2026-08-17 this branch also carried a **full copy of the repo's source** —
35 tracked files including `README.md`, `DESIGN.md`, `harness/`, `test/` and
`evals/` — frozen at whatever `main` looked like when the branch was created.
Nothing ever refreshed it: the publish step does `git checkout -B eval-results
origin/eval-results` and then `git add badges results`, so only generated data is
ever updated. The mirror just sat there going staler, advertising retired evals
and a months-old harness to anyone who browsed the branch, and silently swapping
the live checkout for that old copy partway through every eval run.

It was removed. Results, badges and propagation snapshots were untouched —
nothing published was lost. If you find yourself adding a source file here, that
is the bug.
