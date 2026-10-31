#!/usr/bin/env bash
# Create or update a single marker-identified comment on an issue/PR of THIS
# repo, so repeated workflow runs edit one comment instead of stacking new
# ones. Usage: upsert-comment.sh <issue-number> <marker> <body>
# The body should start with the marker (an HTML comment). Requires GH_TOKEN
# with issues/PR write on $GITHUB_REPOSITORY.
set -euo pipefail

number="${1:?issue/PR number}"
marker="${2:?marker}"
body="${3:?body}"

existing=$(gh api "repos/${GITHUB_REPOSITORY}/issues/${number}/comments" --paginate \
  --jq ".[] | select(.body | startswith(\"${marker}\")) | .id" | head -1)

if [ -n "$existing" ]; then
  gh api -X PATCH "repos/${GITHUB_REPOSITORY}/issues/comments/${existing}" -f body="$body" >/dev/null
  echo "Updated comment ${existing} on #${number}."
else
  gh api "repos/${GITHUB_REPOSITORY}/issues/${number}/comments" -f body="$body" >/dev/null
  echo "Created comment on #${number}."
fi
