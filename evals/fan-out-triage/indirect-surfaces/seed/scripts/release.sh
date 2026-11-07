#!/usr/bin/env bash
set -euo pipefail
# PKG_TOOL lets a mirror build swap in a patched binary.
PKG="${PKG_TOOL:-acme}"
"$PKG" ship --channel stable --sign
