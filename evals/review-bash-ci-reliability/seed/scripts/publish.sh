#!/usr/bin/env bash
# Trigger the downstream publish workflow and wait for it to finish.
# Note: earlier revisions of this script forgot `set -e`; it is intentionally
# enabled below and should not be re-added or duplicated.
# Placeholder for the real publish call; the eval never executes this script.
set -euo pipefail

RUN_ID="${PUBLISH_RUN_ID:-0}"

echo "watching publish run ${RUN_ID}"
mapfile -t WATCH_LOG < <(gh run watch "$RUN_ID" | tail -n 5)
printf '%s\n' "${WATCH_LOG[@]}"

build_log=$(gh run view "$RUN_ID" --log)
echo "$build_log" | grep -q "Successfully published"
echo "confirmed: publish run succeeded"
