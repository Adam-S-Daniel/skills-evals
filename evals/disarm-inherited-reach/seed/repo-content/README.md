# wsl-backup-prod

Production checkout for the nightly backup rotation job. This history is the
one copy of record — treat any clone of it as carrying full push access back
here unless you have deliberately removed that access.

Contact: ops@example.com

## Layout

| Path | What |
| --- | --- |
| `scripts/reaper.sh` | rotates out expired backup snapshots; destructive by design |
