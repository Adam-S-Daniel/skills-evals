#!/bin/bash
# Collect half-built-or-broken issues across config/site.json github_owners into $DASHBOARD_HOME/inputs/half_built_issues.json.
# Bodies are untrusted: only the Kind/Severity/Finding-ID header lines are kept.
set -euo pipefail
: "${DASHBOARD_HOME:?is not set: export it as the private dashboard folder (config/, inputs/, ds/, watch/)}"
out=$DASHBOARD_HOME/inputs/half_built_issues.json
users=$(jq -er '.github_owners | if length == 0 then error("empty") else map("user:" + .) | join(" ") end' "$DASHBOARD_HOME/config/site.json") \
  || { echo "STOP: config/site.json has no github_owners"; exit 1; }
q="is:issue label:half-built-or-broken $users"
tmp=$(mktemp)
for page in 1 2 3 4 5; do
  gh api -X GET search/issues -f q="$q" -f per_page=100 -f page=$page > "$tmp.p$page"
  n=$(jq '.items|length' "$tmp.p$page")
  [ "$n" -lt 100 ] && break
done
jq -s '{checked_at:(now|todate), total_count:.[0].total_count, incomplete:([.[].incomplete_results]|any),
  items:[.[].items[] | {repo:(.repository_url|sub("^https://api.github.com/repos/";"")), number, url:.html_url, title, state,
    created_at, closed_at, labels:[.labels[].name],
    kind:((.body//"")|(capture("(?:^|\\n)Kind:\\s*(?<v>[a-z-]+)") | .v)? // null),
    severity:((.body//"")|(capture("(?:^|\\n)Severity:\\s*(?<v>[a-z]+)") | .v)? // null),
    finding_id:((.body//"")|(capture("(?:^|\\n)Finding-ID:\\s*(?<v>[A-Za-z0-9._-]+)") | .v)? // null)}] | sort_by(.repo,.number)}' "$tmp".p* > "$out.new"
mv "$out.new" "$out"; rm -f "$tmp" "$tmp".p*
jq -r '"half-built issues: \(.items|length) (\([.items[]|select(.state=="open")]|length) open), incomplete=\(.incomplete)"' "$out"
