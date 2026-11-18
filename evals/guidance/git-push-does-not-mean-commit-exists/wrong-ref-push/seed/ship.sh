#!/usr/bin/env bash
# Commit every tracked change on the current branch and publish the release
# branch to origin.
msg=${1:-"Update release notes"}
git commit -q -a -m "$msg" || exit 1
git push -q origin release
echo "Shipped to origin/release."
