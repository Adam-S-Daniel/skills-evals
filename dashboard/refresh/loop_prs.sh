#!/bin/bash
# Rebuild $DASHBOARD_HOME/inputs/loop_prs.json: PRs in config/site.json loop_pr_repos whose head branch starts with a loop prefix.
# Pages by hand: the proxy refuses --paginate's repositories/<id> next links.
set -euo pipefail
: "${DASHBOARD_HOME:?is not set: export it as the private dashboard folder (config/, inputs/, ds/, watch/)}"
DASHBOARD_HOME=$(cd "$DASHBOARD_HOME" && pwd); export DASHBOARD_HOME
OUT=$DASHBOARD_HOME/inputs/loop_prs.json
repos=$(jq -er '.loop_pr_repos | if length == 0 then error("empty") else .[] end' "$DASHBOARD_HOME/config/site.json") \
  || { echo "STOP: config/site.json has no loop_pr_repos"; exit 1; }
tmp=$(mktemp)
for repo in $repos; do
  for page in $(seq 1 20); do
    body=$(gh api "repos/$repo/pulls?state=all&per_page=100&page=$page")
    n=$(jq length <<<"$body")
    jq -c --arg repo "$repo" '.[] | select(.head.ref | test("^(eval-improve|draft-skill|retire-skill|eval-guidance-improve|retire-guidance)/")) | {repo: $repo, number, url: .html_url, head_ref: .head.ref, title, state, merged_at}' <<<"$body"
    [ "$n" -lt 100 ] && break
  done
done > "$tmp.lines"
python3 - "$tmp.lines" "$tmp" <<'PY'
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
rows.sort(key=lambda r:(r['repo'],r['number']))
json.dump(rows,open(sys.argv[2],'w'),indent=1); print(len(rows),'loop PRs')
PY
mv "$tmp" "$OUT"; rm -f "$tmp.lines"
