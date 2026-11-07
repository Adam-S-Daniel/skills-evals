#!/bin/sh
# Installs nektos/act into ~/.local/bin so `scripts/local-ci.sh` can run.
set -eu
mkdir -p "$HOME/.local/bin"
curl -fsSL https://example.com/act/releases/latest/download/act_Linux_x86_64.tar.gz \
  | tar xz -C "$HOME/.local/bin" act
