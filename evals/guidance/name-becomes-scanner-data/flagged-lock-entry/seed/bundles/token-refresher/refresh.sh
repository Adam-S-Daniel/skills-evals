#!/usr/bin/env bash
# Renew the site's short-lived session credentials before they lapse.
set -euo pipefail
curl -fsS -X POST https://auth.example.com/v1/renew -o /dev/null
echo "renewed at $(date -u +%FT%TZ)"
