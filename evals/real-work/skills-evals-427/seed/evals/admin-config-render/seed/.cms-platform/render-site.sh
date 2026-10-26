#!/usr/bin/env bash
# Usage: render-site.sh <site_root> <build_dir>
# Render the Decap admin config for <site_root> into <build_dir>/admin with the
# vendored platform kit. Without the theme gem loaded, the kit's CLI reads its
# templates from <site_root>/admin, so stage them beside the site's own seam in
# a scratch directory and leave the site tree untouched.
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
site=$(cd "${1:?site_root}" && pwd)
build=${2:?build_dir}

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/admin"
cp "$site/_config.yml" "$stage/"
cp "$here"/theme/admin/*.yml "$stage/admin/"
if [ -f "$site/admin/collections.site.yml" ]; then
  cp "$site/admin/collections.site.yml" "$stage/admin/"
fi

ruby "$here/scripts/render-decap-config.rb" "$stage" "$stage/_site"

mkdir -p "$build/admin"
cp "$stage/_site/admin/"* "$build/admin/"
