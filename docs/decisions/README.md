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
| [0001](0001-roster-trusted-on-main.md) | The roster the harness runs on is committed on `main`; a computed roster is a proposal | accepted (2026-09-13) |
