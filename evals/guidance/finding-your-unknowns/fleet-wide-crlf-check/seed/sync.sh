#!/usr/bin/env bash
# Deliver the guidance and the commit checks to every repository in repos.yml.
# Each target is a local clone at ../<name>; the sync opens one pull request
# per repository with whatever changed.
set -euo pipefail
for repo in $(sed -n 's/^  - //p' repos.yml); do
  name=${repo#*/}
  [ "$name" = agent-guidance ] && continue
  target=../$name
  cp guidance.md "$target/AGENTS.md"
  mkdir -p "$target/.githooks"
  cp templates/agent-checks/agent-checks "$target/.githooks/agent-checks"
done
