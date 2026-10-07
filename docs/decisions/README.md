# Architecture Decision Records

Lightweight [Nygard-style](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
records of the non-obvious, load-bearing decisions this repo has made — one file
per decision, numbered in the order they were taken, never rewritten once
accepted (a decision that stops holding is superseded by a later record rather
than edited into agreement with the present). Each states the context that
forced the choice, the choice itself, and the consequences the repo now lives
with, so the next session can tell a deliberate constraint from an accident.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-roster-trusted-on-main.md) | The roster the harness runs on is committed on `main`; a computed roster is a proposal | accepted (2026-09-13); amended by 0003 and 0004 |
| [0002](0002-runs-bill-the-api-org-not-the-subscription.md) | Real runs bill the API organisation; subscription credentials are not adopted | accepted (2026-09-23); decision 1 superseded for routine runs only by 0010 |
| [0002](0002-roster-follows-vendor-defaults.md) | The roster seats each tier's vendor-default model at once and retires the version it superseded after a buffer | accepted (2026-09-27; decision 1 revised 2026-09-28) |
| [0003](0003-roster-merges-automatically.md) | The roster proposal merges automatically, behind `roster_mode` | accepted (2026-09-28; round 6, the roster App, 2026-09-29); amended by 0004 |
| [0004](0004-eval-runs-on-the-roster-its-run-merged.md) | The scheduled eval runs on the roster its own run just merged | accepted (2026-09-30) |
| [0005](0005-improvement-loop-reuses-skill-creator.md) | The improvement loop reuses skill-creator's description loop and measures with this harness | accepted (2026-10-06); amended 2026-10-06: run path moves to the ADR 0010 routine, acceptance basis becomes real-work fixtures plus tokens/cost; amended 2026-10-07: tokens are the total across every model |
| [0006](0006-run-objective-commands-with-isolated-process-state.md) | Run objective commands with isolated process state | accepted (2026-10-04) |
| [0007](0007-parse-config-and-staged-shell-guards.md) | Parse configuration values and staged shell guards before scoring | accepted (2026-10-04); amended 2026-10-05 |
| [0008](0008-run-ready-fixtures-on-the-weekly-schedule.md) | Run ready fixtures on the weekly schedule | proposed (2026-10-04) |
| [0009](0009-fixture-followup-turns.md) | A fixture may send scripted follow-up turns, identically in both arms | proposed (2026-10-05) |
| [0010](0010-run-ai-eval-steps-in-a-routine-fired-by-actions.md) | Run the AI steps of skill and guidance evals in a routine fired by Actions, and measure agent effectiveness on real work | accepted (2026-10-06); supersedes 0002 (billing) decision 1 for routine runs only |
