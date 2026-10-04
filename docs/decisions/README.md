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
| [0002](0002-runs-bill-the-api-org-not-the-subscription.md) | Real runs bill the API organisation; subscription credentials are not adopted | accepted (2026-09-23) |
| [0002](0002-roster-follows-vendor-defaults.md) | The roster seats each tier's vendor-default model at once and retires the version it superseded after a buffer | accepted (2026-09-27; decision 1 revised 2026-09-28) |
| [0003](0003-roster-merges-automatically.md) | The roster proposal merges automatically, behind `roster_mode` | accepted (2026-09-28; round 6, the roster App, 2026-09-29); amended by 0004 |
| [0004](0004-eval-runs-on-the-roster-its-run-merged.md) | The scheduled eval runs on the roster its own run just merged | accepted (2026-09-30) |
| [0005](0005-improvement-loop-reuses-skill-creator.md) | The improvement loop reuses skill-creator's description loop and measures with this harness | proposed (2026-10-04) |
