# Session capture — laptop, 2026-09-18

Copied off the machine so the delivery question can be answered away from it.

- `session/skills/` — the personal skill store as it stood, including whatever
  the claude.ai account sync had put there.
- `session/skills.lock` — the lock the bootstrap hook installs from.
- `registry/` — the checkout the bundles are built from, at the commit the lock
  names.

## What prompted the capture

`writing-adrs` has started leaving the "Alternatives considered" section out of
the ADRs it writes, on a machine where the registry copy still asks for it and
nothing in the repo changed. `adam-writing-style` behaves normally.

A first look found nothing:

```
$ ls -1 ~/.claude/skills/
adam-writing-style
writing-adrs
synced

$ ls -1 ~/.claude/skills/synced/
29094e6a-eeb7-4d76-982e-84e62238e605_d11d9c2e-1772-4767-9197-f59d6fe0ab5a
```

which was read as "nothing has been uploaded to the account", and the question
was left there.
