# ADR 0017: The guidance loops merge only in _agent-guidance's weekly window

- **Status:** accepted (2026-11-07). Amends the merge timing of
  [ADR 0005](0005-improvement-loop-reuses-skill-creator.md)'s guidance
  improvement addendum and [ADR 0014](0014-removal-pull-requests-merge-without-review.md)'s
  guidance removals; their decisions otherwise stand.
- **Deciders:** Adam, 2026-11-07: merges of `agents-md/base.md` are batched
  into one weekly window. The rule and the other paths it covers are
  _agent-guidance's ADR 0039.

## Context

Every edit to `agents-md/base.md` changes the "rest digest" of every guidance
section and restarts their eval evidence. Two loops in this repository change
those files with no human review: the guidance improvement gate
(`eval-guidance-improve/<section>` pull requests, auto-merge armed at open)
and the guidance retirement pass (`retire-guidance/<section>`, armed at open).
Each merged whenever its checks finished.

## Decision

1. **The bounds are not written here.** `scripts/guidance_merge_window.py`
   reads _agent-guidance's `scripts/base-md-merge-window.yml` (Monday 17:00 up
   to 19:00 UTC today) from a checkout of it. A missing or malformed file
   means closed.
2. **Improvements are queued, then armed.** Outside the window the gate opens
   the pull request ready and labeled but does not arm auto-merge, and its
   body and job summary say it is queued. `guidance-merge-window.yml` runs on
   Mondays inside the window and arms every queued pull request the loop
   opened (loop App author, `agent-authored`, not draft, not `on-hold`).
3. **Removals are not opened outside the window.** A removal is armed the
   moment it opens, and the withdrawal logic reads an unarmed one as a
   person's hold, so queueing it would change what the rounds of ADR 0014
   proved. `retire_skill.py --target guidance` therefore returns without
   writing anything when the window is closed, and `skill-coverage.yml` has a
   second cron entry on Monday at 17:19 UTC so a pass lands inside it. Every
   job in that workflow is idempotent, so the extra pass is harmless.
4. **A person may merge any time.** A manual merge outside the window
   restarts the evidence of every guidance section.

## Consequences

- An accepted improvement waits up to a week. A pull request armed at the
  start of the window can finish its checks after 19:00; the window bounds
  when automation arms, not when the merge button fires.
- The existing rule of one open guidance-loop pull request at a time means at
  most one queued improvement is armed per window; a candidate that arrives
  while one is queued waits on its branch.
- `retire_skill.py`'s `guidance_execute` takes a `window_open` callable so its
  tests do not read a clock or a checkout.
