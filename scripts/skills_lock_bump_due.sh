#!/usr/bin/env bash
# Decide whether _agent-guidance's skills-lock-bump.yml should be dispatched
# (skills-lock-bump-dispatch.yml, _agent-guidance#413).
#
#   skills_lock_bump_due.sh RUNS_JSON REGISTRY_COMMITTED_AT NOW_EPOCH
#
# RUNS_JSON is the workflow's runs listing (newest first). Prints "due" or
# "not due: <reason>" and exits 0; a malformed input exits 2.
#
# Due when the registry's main was committed after the SECOND-newest run
# started (every change gets two runs: propose, then sweep), no run is queued
# or in progress, and none started in the last 30 minutes (time for a
# consumer's checks to report before the sweep reads them).
set -euo pipefail
runs="$1" committed="$2" now="$3"
iso='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'
if ! [[ "$committed" =~ $iso ]] || ! [[ "$now" =~ ^[0-9]+$ ]] \
   || ! jq -e '.workflow_runs | type == "array"' "$runs" > /dev/null 2>&1; then
  echo "malformed input" >&2
  exit 2
fi
active="$(jq '[.workflow_runs[] | select(.status != "completed")] | length' "$runs")"
newest="$(jq -r '.workflow_runs[0].created_at // ""' "$runs")"
second="$(jq -r '.workflow_runs[1].created_at // ""' "$runs")"
c="$(date -u -d "$committed" +%s)"
n=0 s=0
if [[ "$newest" =~ $iso ]]; then n="$(date -u -d "$newest" +%s)"; fi
if [[ "$second" =~ $iso ]]; then s="$(date -u -d "$second" +%s)"; fi
if [ "$active" != 0 ]; then
  echo "not due: a skills-lock-bump run is queued or in progress"
elif [ $(( now - n )) -lt 1800 ]; then
  echo "not due: a skills-lock-bump run started less than 30 minutes ago"
elif [ "$c" -le "$s" ]; then
  echo "not due: two runs have started since the registry's main last changed"
else
  echo "due"
fi
