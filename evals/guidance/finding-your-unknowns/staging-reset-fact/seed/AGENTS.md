# AGENTS.md

> **Managed by `example-org/agent-guidance`.**
> Edit only below the `## Repo-specific additions` header.
> Everything above it will be overwritten on the next sync.

## Working in this repo

- Run `python3 -m pytest tests/ -q` before calling a change done.
- Keep each commit to one logical change.

## Repo-specific additions

- `src/orders.py` talks to the staging API named by `$ORDERS_API_URL`.
