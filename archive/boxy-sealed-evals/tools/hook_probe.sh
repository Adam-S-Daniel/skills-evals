#!/bin/bash
n=0; d=0
for f in /proc/[0-9]*/environ; do
  if tr '\0' '\n' < "$f" 2>/dev/null | grep -q '^CLAUDE_CODE_OAUTH_TOKEN='; then
    n=$((n+1))
    tr '\0' '\n' < "$f" | grep -qx 'CLAUDE_CODE_OAUTH_TOKEN=dummy-not-a-token' && d=$((d+1))
  fi
done
echo "hook: environ files holding the token var=$n (dummy=$d)" >> /work/ws/hook-marker
