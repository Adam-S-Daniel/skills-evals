# Egress sidecar for scripts/container_eval.sh: squid allowing only CONNECT to
# port 443 of a fixed host list (no TLS interception); everything else is
# denied. Every run starts one, on the internal eval network and on a network
# with a route out. It holds no credential.
#
# EGRESS_PROFILE (set by container_eval.sh, validated by egress-entrypoint:
# exactly one of the two, else exit 2) picks the list:
#
#   proxy      --seal proxy: registry.npmjs.org, rubygems.org and
#              index.rubygems.org. The agent holds no real credential here;
#              the credential-proxy sidecar adds it, and the runner reaches
#              that sidecar directly (NO_PROXY), not through this one.
#   allowlist  --seal allowlist: those three plus api.anthropic.com. The
#              runner holds the token and reaches the API through this proxy.
#
# The entrypoint writes the list to /tmp/egress-hosts.txt, so the container
# needs a tmpfs /tmp (container_eval.sh gives it one) and a read-only root.
#
#   docker build -t skills-evals-egress docker/eval-egress
FROM debian:bookworm-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3
RUN apt-get update \
 && apt-get install -y --no-install-recommends squid \
 && rm -rf /var/lib/apt/lists/*
COPY squid.conf /etc/squid/squid.conf
COPY entrypoint.sh /usr/local/bin/egress-entrypoint
USER proxy
EXPOSE 3128
ENTRYPOINT ["/usr/local/bin/egress-entrypoint"]
