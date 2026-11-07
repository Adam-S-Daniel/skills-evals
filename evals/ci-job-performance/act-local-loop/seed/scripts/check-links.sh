#!/bin/sh
# Fails when a page links to a page that does not exist.
set -eu
for f in pages/*.md; do
  grep -o '](\([a-z-]*\)\.md)' "$f" | sed 's/](\(.*\))/\1/' | while read -r target; do
    test -f "pages/$target" || { echo "$f: broken link to $target" >&2; exit 1; }
  done
done
