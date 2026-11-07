#!/bin/sh
# Runs the ci workflow's jobs locally with act, before pushing.
set -eu
act pull_request \
  -W .github/workflows/ci.yml \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest
