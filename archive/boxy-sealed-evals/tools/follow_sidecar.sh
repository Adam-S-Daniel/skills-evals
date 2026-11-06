#!/bin/bash
# Follow the first *-credproxy/*-egress sidecar that appears; its log carries no header values.
out=$1
for i in $(seq 1 600); do
  name=$(docker ps --format '{{.Names}}' | grep -E '^skills-evals-[0-9]+-[0-9a-f]{8}-(credproxy|egress)$' | head -1)
  [ -n "$name" ] && break
  sleep 0.5
done
[ -n "$name" ] || exit 1
echo "# sidecar $name" > "$out"
exec docker logs -f "$name" >> "$out" 2>&1
