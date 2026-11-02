# crm-sync

A public repository. `scripts/sync_contacts.py` pushes the contact list in
`contacts.json` to the CRM; `.github/workflows/nightly-sync.yml` runs it
every night. The CRM's API is described in `docs/crm-api.md`.
Pin every `uses:` to a full commit SHA, as the workflows do.
