# Scheduled task: dashboard refresh

Schedule: every 12 hours (7:29 AM and 7:29 PM ET), bound to the dashboard's project thread (so it can
post there and read project files). Prompt:

> Dashboard refresh, timed run. Follow `dashboard/README.md` ("Refresh") in
> skills-evals at origin/main to refresh the snapshot datasets of
> <dashboard artifact URL>, the `explorer` dataset (the results branch's
> `explorer/latest.json`) included. Use the config in <private config path>.
> Upload only changed files. Reply in the thread only if something needs the owner;
> otherwise update the checklist quietly.

The same steps run at once when a merge relay arrives (`merge-relay.md`). Skip
the run only when a refresh in the last 5 minutes already included that merge.
