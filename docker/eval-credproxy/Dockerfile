# Credential-injection sidecar for scripts/container_eval.sh: nginx reverse
# proxy to https://api.anthropic.com that replaces Authorization with the real
# token read from /run/secrets/oauth.env, a file mounted into THIS container
# only. The eval-runner container holds a dummy and never sees the token.
#
# What it can reach: https://api.anthropic.com, and only POST /v1/messages and
# /v1/messages/count_tokens (nginx.conf returns 403 for any other path). It
# is the one container that holds the real token (--seal proxy only; under
# --seal allowlist it is not started). Package registries are not its job: the
# egress sidecar (docker/eval-egress) carries those.
#
#   docker build -t skills-evals-credproxy docker/eval-credproxy
FROM debian:bookworm-slim@sha256:99c0b25c46d0214d5a2091092e7908907dcaecd6a962cde0ac700acee222b6f3
RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx-light ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY nginx.conf /etc/nginx/credproxy.conf
COPY entrypoint.sh /usr/local/bin/credproxy-entrypoint
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/credproxy-entrypoint"]
