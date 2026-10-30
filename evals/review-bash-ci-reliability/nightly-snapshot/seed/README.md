# orders-snapshot

`data/` holds one CSV of daily order counts per region, appended to by hand.
Every night `.github/workflows/snapshot.yml` runs `scripts/publish-snapshot.sh`:
it rebuilds `snapshot/all.csv` from `data/` with `scripts/build-snapshot.sh`
and, when the snapshot changed, commits it to `main` with the release version
from `manifest.toml` in the message (`snapshot 1.4.2`) and pushes. On a night
with no new data there is nothing to commit and the job should stay green.
