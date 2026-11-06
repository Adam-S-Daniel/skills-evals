#!/bin/sh
# Write the host list for EGRESS_PROFILE to the file squid.conf's dstdomain
# ACL reads (on the container's tmpfs /tmp), then start squid. Exactly one of
# the two profiles is accepted; anything else, or none, refuses to start so a
# typo can never widen or empty the list silently.
#
#   proxy      registry.npmjs.org rubygems.org index.rubygems.org
#   allowlist  those three and api.anthropic.com
#
# EGRESS_HOSTS_FILE is for tests only: squid.conf reads the default path.
set -eu
hosts_file=${EGRESS_HOSTS_FILE:-/tmp/egress-hosts.txt}
registries='registry.npmjs.org rubygems.org index.rubygems.org'
case "${EGRESS_PROFILE-}" in
  proxy) hosts=$registries ;;
  allowlist) hosts="$registries api.anthropic.com" ;;
  *) echo "egress: EGRESS_PROFILE must be exactly proxy or allowlist" >&2; exit 2 ;;
esac
umask 077
: > "$hosts_file"
for host in $hosts; do
  printf '%s\n' "$host" >> "$hosts_file"
done
exec squid -N -f /etc/squid/squid.conf
