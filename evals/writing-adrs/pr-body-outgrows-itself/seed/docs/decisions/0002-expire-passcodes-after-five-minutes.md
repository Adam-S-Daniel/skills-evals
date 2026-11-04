# 0002. Expire passcodes after five minutes

- **Status:** Accepted
- **Date:** 2025-12-09

## Context

Passcodes sent by SMS can sit unread on a lock screen for a long time. A
passcode that stays valid for an hour is a long window for anyone who sees
the message.

## Decision

A passcode stops verifying five minutes after it is sent.

## Consequences

Stolen messages are useful for a short time only. A customer who is slow to
type the code has to request another.

## Alternatives considered

A 15-minute expiry was rejected: support data showed nearly every
legitimate verification completes within two minutes, so the extra time
only widened the window for misuse.
