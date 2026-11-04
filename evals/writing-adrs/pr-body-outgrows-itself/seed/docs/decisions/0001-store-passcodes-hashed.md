# 0001. Store passcode hashes, not passcodes

- **Status:** Accepted
- **Date:** 2025-11-04

## Context

Support staff can read the passcode table when debugging a failed login. A
leaked database dump would have held every live passcode in the clear.

## Decision

Store only a salted hash of each passcode and compare hashes on
verification.

## Consequences

A dump of the table cannot be replayed. Support can no longer read a
passcode back to a customer and has to send a new one.

## Alternatives considered

Encrypting the passcodes at rest was rejected: the service must hold the
key to verify them, so anyone who can read the table in production can
read the key too.
