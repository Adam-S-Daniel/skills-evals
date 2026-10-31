#!/usr/bin/env bash
# Copy the Skill Evals Explorer page (tool/index.html) into a checkout of the
# adamdaniel.ai site repo, record provenance, and commit + force-push a
# sync/preview branch there.
#
# The site vendors the page verbatim at assets/tools/skills-evals/index.html
# (see the site repo's docs/CMS-ADMIN.md "Vendored-tool sync + previews"). This
# script is the single write path shared by both workflows:
#   site-sync.yml     BRANCH=tool-sync/skills-evals            (main -> auto-merge PR)
#   site-preview.yml  BRANCH=tool-preview/skills-evals-pr-<n>   (PR mirror, draft)
#
# Derived from claude-memory-map's scripts/sync-to-site.sh, the reference
# implementation; only the slug and source path differ (SLUG and SOURCE_FILE).
# The page has no build step, so the committed file IS the artifact.
#
# Inputs (env):
#   SITE_DIR       path to the site checkout (cloned with push credentials)
#   BRANCH         site branch to create/force-push (based on SITE_DIR's HEAD)
#   SOURCE_COMMIT  commit the copy comes from (must equal this repo's
#                  checked-out HEAD)
#   SOURCE_REF     provenance label: "main" or "pr-<n>"
#   SOURCE_PR      optional source PR number, recorded for preview mirrors
#   COMMIT_MSG     commit message for the site commit
#   SITE_SYNC_DRY_RUN  when "1", commit locally but do not push (tests)
#
# Outputs (appended to $GITHUB_OUTPUT when set, echoed either way):
#   changed=true|false      whether a site commit was made (and pushed)
#   previous_commit=<sha>   the source commit the site had before (may be empty)
set -euo pipefail

: "${SITE_DIR:?}" "${BRANCH:?}" "${SOURCE_COMMIT:?}" "${SOURCE_REF:?}" "${COMMIT_MSG:?}"

# Slug and paths: the only things to change when copying this for another tool.
SLUG=skills-evals
SOURCE_FILE=tool/index.html
SOURCE_REPO=Adam-S-Daniel/skills-evals

here=$(cd "$(dirname "$0")/.." && pwd)
asset_dir="$SITE_DIR/assets/tools/$SLUG"
data_dir="$SITE_DIR/_data/tool_sources"

out() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "$1" >>"$GITHUB_OUTPUT"; fi
  echo "$1"
}

if [ "$(git -C "$here" rev-parse HEAD)" != "$SOURCE_COMMIT" ]; then
  echo "::error::checkout HEAD does not match SOURCE_COMMIT=$SOURCE_COMMIT" >&2
  exit 1
fi

# The site opts in by having the vendored directory. Before that, syncing would
# create an orphan asset with no /tools/ page, so skip instead of surprising
# the site with new files.
if [ ! -d "$asset_dir" ]; then
  echo "::warning::$asset_dir does not exist on the site branch: the site has not vendored this tool (yet); skipping."
  out "changed=false"
  out "previous_commit="
  exit 0
fi

previous=$(sed -n 's/^commit: *//p' "$data_dir/$SLUG.yml" 2>/dev/null | head -1 || true)
out "previous_commit=${previous}"

commit_date=$(git -C "$here" show -s --format=%cI "$SOURCE_COMMIT")

git -C "$SITE_DIR" checkout -B "$BRANCH"

cp "$here/$SOURCE_FILE" "$asset_dir/index.html"
mkdir -p "$data_dir"
{
  echo "# Provenance of the vendored copy at assets/tools/$SLUG/."
  echo "# Maintained by the source repo's site-sync/site-preview workflows"
  echo "# (github.com/$SOURCE_REPO): don't hand-edit."
  echo "repo: $SOURCE_REPO"
  echo "ref: ${SOURCE_REF}"
  echo "commit: ${SOURCE_COMMIT}"
  echo "source_committed_at: ${commit_date}"
  if [ -n "${SOURCE_PR:-}" ]; then
    echo "source_pr: ${SOURCE_PR}"
  fi
} >"$data_dir/$SLUG.yml"

if [ -n "$(git -C "$SITE_DIR" status --porcelain)" ]; then
  git -C "$SITE_DIR" add "assets/tools/$SLUG" _data/tool_sources
  git -C "$SITE_DIR" \
    -c user.name="github-actions[bot]" \
    -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
    commit -m "$COMMIT_MSG"
  if [ "${SITE_SYNC_DRY_RUN:-}" = "1" ]; then
    echo "SITE_SYNC_DRY_RUN=1: committed locally, not pushing."
  else
    git -C "$SITE_DIR" push -f origin "$BRANCH"
  fi
  out "changed=true"
else
  echo "Site already has this content: nothing to push."
  out "changed=false"
fi
