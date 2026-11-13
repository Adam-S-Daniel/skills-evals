#!/bin/bash
# usage: mark_published.sh [page]
# Run after uploading this run's datasets (and, with "page", after writing the
# page). Records what is now live, so the next refresh.sh compares against it.
set -euo pipefail
: "${DASHBOARD_HOME:?is not set: export it as the private dashboard folder (config/, inputs/, ds/, watch/)}"
S=${REFRESH_WORK:-/tmp/dashboard-refresh}; SE=$(cd "$(dirname "$0")/../.." && pwd)
for f in "$S"/ds_now/*.json; do
  if [ "$(basename "$f")" = explorer_private.json ]; then   # private artifact only: keep a hash, never the file
    sha256sum "$f" | cut -d' ' -f1 > $DASHBOARD_HOME/watch/private_published.sha256; continue
  fi
  cp "$f" "$DASHBOARD_HOME/ds/"
done
if [ "${1:-}" = page ]; then
  sha256sum "$SE/dashboard/page/index.html" | cut -d' ' -f1 > $DASHBOARD_HOME/watch/page_published.sha256
fi
echo "baseline updated"
