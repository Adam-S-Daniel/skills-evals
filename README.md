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
