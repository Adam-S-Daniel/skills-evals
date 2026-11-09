#!/usr/bin/env bash
# Succeeds when the exact marker line is present in the release notes text.
set -euo pipefail

notes_file=$1
marker=$2

notes=$(cat "$notes_file")
if printf '%s\n' "$notes" | grep -qxF -- "$marker"; then
  echo "marker present"
else
  echo "marker missing" >&2
  exit 1
fi
