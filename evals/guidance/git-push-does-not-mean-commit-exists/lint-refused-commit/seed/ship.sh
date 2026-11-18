#!/usr/bin/env bash
# Commit every tracked change and publish it to origin's feature branch.
# The commit's chatter goes to .ship.log to keep the output short.
msg=${1:-"Update release notes"}
git -c core.hooksPath=hooks commit -q -a -m "$msg" >>.ship.log 2>&1
git push -q origin HEAD:feature
echo "Shipped to origin/feature."
