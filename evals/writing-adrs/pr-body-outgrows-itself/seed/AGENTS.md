# AGENTS.md

Notify delivers one-time passcodes by SMS through a gateway that
rate-limits by API key.

## Conventions

- Keep retry settings in `config/retry.yaml`, not in code.
- Record user-visible changes in `CHANGELOG.md`.
