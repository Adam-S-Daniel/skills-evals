# Egress sidecar for scripts/container_eval.sh: squid allowing only CONNECT to
# api.anthropic.com:443 (no TLS interception); everything else is denied.
# It sits on the internal eval network and on a network with a route out.
#
#   docker build -t skills-evals-egress docker/eval-egress
FROM debian:bookworm-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3
RUN apt-get update \
 && apt-get install -y --no-install-recommends squid \
 && rm -rf /var/lib/apt/lists/*
COPY squid.conf /etc/squid/squid.conf
USER proxy
EXPOSE 3128
ENTRYPOINT ["squid", "-N", "-f", "/etc/squid/squid.conf"]
