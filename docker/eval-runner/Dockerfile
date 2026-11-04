# Image for scripts/container_eval.sh: runs scripts/local_eval.py in a container.
# Credentials never go in this image. The OAuth token (`claude setup-token`)
# comes in at run time through `docker run --env-file`, from a mode-600 file
# outside every repository.
#
# Build from the repository root:
#   docker build -f docker/eval-runner/Dockerfile \
#     --build-arg CLAUDE_CODE_VERSION=<version> -t skills-evals-runner .
FROM python:3.11-slim-bookworm

ARG CLAUDE_CODE_VERSION
RUN test -n "$CLAUDE_CODE_VERSION" || { \
      echo "error: pass --build-arg CLAUDE_CODE_VERSION=<version> (no default by design)" >&2; \
      exit 1; }

# Debian's git can be older than scripts/dev_setup.sh's GIT_MIN; suites that
# need the newer git are not what this image is for (local_eval.py runs).
RUN apt-get update \
 && apt-get install -y --no-install-recommends git bubblewrap nodejs npm ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# The same Python pins CI's test job installs, read from their one definition.
COPY scripts/dev_setup.sh /tmp/dev_setup.sh
RUN pip install --no-cache-dir $(bash /tmp/dev_setup.sh --print-pins) \
 && rm /tmp/dev_setup.sh

RUN npm install -g --no-audit --no-fund "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"

RUN useradd --create-home --home-dir /home/eval --shell /bin/bash eval \
 && mkdir -p /work /results && chown eval:eval /work /results
ENV HOME=/home/eval
USER eval
WORKDIR /work
