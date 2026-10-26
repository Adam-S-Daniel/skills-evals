#!/usr/bin/env bash
# Usage: bash .cms-platform/check-render.sh <renders|collections|fields>
# Render the site's admin config into a scratch directory, then check it. Exits
# 0 only when the render succeeds and the named check passes. Needs `ruby` on
# PATH.
#   renders      the render finishes without error
#   collections  the config lists exactly this site's collections, with no
#                unexpanded `$ref` left
#   fields       each site collection still has the fields it was authored with
set -euo pipefail

mode=${1:?usage: check-render.sh <renders|collections|fields>}
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
site=$(cd "$here/.." && pwd)

out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT

bash "$here/render-site.sh" "$site" "$out"
if [ "$mode" != renders ]; then
  ruby "$here/check-config.rb" "$mode" "$out/admin/config.yml"
fi
