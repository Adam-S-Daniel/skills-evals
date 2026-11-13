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

## Addendum (2026-11-13): US Eastern bounds, and the eval pause

Adam asked that evals pause Mondays from noon to 2 PM Eastern, so that no eval
run lands on guidance that is half merged.

1. **The bounds are in US Eastern time.** _agent-guidance's bounds file gains
   a required `timezone` key (`America/New_York`) and reads 12:00 to 14:00
   ([its ADR 0039 addendum](https://github.com/Adam-S-Daniel/_agent-guidance/blob/main/docs/decisions/0039-fleet-guidance-merges-are-batched-into-one-weekly-window.md)).
   `guidance_merge_window.py` converts with `zoneinfo`, so the window is
   17:00 to 19:00 UTC in winter and 16:00 to 18:00 UTC in summer. Cron is
   UTC, so every Monday cron entry that must land inside the window sits in
   17:00 to 17:30 UTC, inside it in both seasons (`guidance-merge-window.yml`
   at 17:07 and 17:27, `skill-coverage.yml` at 17:19); a test pins each.
   Automation arms only while at least 30 minutes of the window are left
   (`ARM_MARGIN`), so an armed pull request merges, after _agent-guidance's
   few-minute required checks, before the pause lifts.
2. **The same window is the eval pause.** `guidance_merge_window.py
   eval-pause` (exit 0 may start, 3 paused, 1 unreadable) is asked by every
   automated launcher: `routine-eval-fire.yml` in every mode, before the
   allowance guard (a paused fire ends cancelled, as a guard refusal does);
   `eval.yml`'s plan job (an empty plan); and `plan_week.py`, so a sweep
   inside the window plans no fire instead of dispatching legs that would be
   refused. The bounds are read from the same file; no launcher holds a copy.
   An unreadable file pauses (fail closed) and fails the run so it is seen.
   `scripts/local_eval.py`, run by a person on their own machine, is not
   gated.
3. **A run already going when the window opens finishes.** A routine fire
   clones _agent-guidance once, at its start, so a fire dispatched before the
   window measures one consistent version; stopping it would waste its spend
   for no gain. `eval.yml`'s legs can start well after its plan (they queue
   behind the roster jobs and `max-parallel`), so every leg checks out the
   exact _agent-guidance commit the plan judged the pause on, never a later
   main. The residual risk is a routine fire dispatched in the last minutes
   before the window that clones after a merge has already landed in it;
   the earliest in-window merges come from the arming runs and the fleet
   worker, both minutes after the window opens.
4. **Planned fires resume on their own.** The watchdog's half-hourly check
   re-plans after the window closes; no fire is lost, only delayed.

Consequence: the ingest-driven backstop run of `guidance-merge-window.yml`
fires less inside the window, since no new runs start there; the two cron
entries remain the primary arming path.
