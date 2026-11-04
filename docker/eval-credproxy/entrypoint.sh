#!/bin/sh
# Read the token from the one file mounted into this container, render the
# header directive nginx includes into a private tmpfs file, and start nginx.
# The value is checked against the token alphabet so it cannot change the
# config; it is never echoed.
set -eu
src=${CREDPROXY_TOKEN_FILE:-/run/secrets/oauth.env}
[ -f "$src" ] || { echo "credproxy: no token file at $src" >&2; exit 2; }
line=$(grep -m1 '^CLAUDE_CODE_OAUTH_TOKEN=' "$src" || true)
value=${line#CLAUDE_CODE_OAUTH_TOKEN=}
[ -n "$line" ] && [ -n "$value" ] || { echo "credproxy: $src has no CLAUDE_CODE_OAUTH_TOKEN= line" >&2; exit 2; }
case "$value" in
  *[!A-Za-z0-9_-]*) echo "credproxy: token has characters outside [A-Za-z0-9_-]; refusing" >&2; exit 2 ;;
esac
umask 077
mkdir -p /tmp/credproxy
printf 'proxy_set_header Authorization "Bearer %s";\n' "$value" > /tmp/credproxy/authorization.conf
unset line value
exec nginx -e stderr -c /etc/nginx/credproxy.conf -g 'daemon off;'
