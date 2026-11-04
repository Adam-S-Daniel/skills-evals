# Image for scripts/container_eval.sh: runs scripts/local_eval.py in a container.
# Credentials never go in this image. The OAuth token (`claude setup-token`)
# comes in at run time through `docker run --env-file`, from a mode-600 file
# outside every repository.
#
# Build from the repository root:
#   docker build -f docker/eval-runner/Dockerfile \
#     --build-arg CLAUDE_CODE_VERSION=<version> -t skills-evals-runner .
#
# Run it under seccomp-bwrap.json, beside this file (container_eval.sh passes
# it). That profile is Docker's default seccomp profile as Docker Engine
# 29.8.0 ships it (moby/moby tag docker-v29.8.0, commit 3ce5872b7950, file
# vendor/github.com/moby/profiles/seccomp/default.json from module
# github.com/moby/profiles/seccomp v0.2.3, sha256 536529b665dd0972...) with
# one rule added: clone, clone3, mount, pivot_root, sethostname, setns,
# umount2 and unshare allowed unconditionally, and those names taken out of
# the CAP_SYS_ADMIN-only rule and the two no-CAP_SYS_ADMIN clone/clone3
# rules they replace. bubblewrap (the arms' CLI sandbox and the workspace
# scorers) needs them to build its namespaces as uid 1000 with every
# capability dropped. The default profile refuses them, and pivot_root even
# with CAP_SYS_ADMIN, which is why `--cap-add SYS_ADMIN` alone also fails.
#
# Stages: Git built from source (config-based fleet hooks need Git 2.54+, and
# bookworm ships 2.39), the native linux-x64 CLI binary fetched by itself
# (the npm package installs three ~330 MB binaries), Node 22 (CI's version)
# for the fleet hooks' `npm ci` and Node scorers, then the runtime.
FROM python:3.11-slim-bookworm@sha256:94a8fee35252d06ab75856f15f12c7bae67b10e8a6da93c7fded82b2610926cd AS base

FROM base AS git-build
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl ca-certificates \
      xz-utils libssl-dev libcurl4-openssl-dev zlib1g-dev libexpat1-dev \
 && rm -rf /var/lib/apt/lists/*
COPY scripts/dev_setup.sh /tmp/dev_setup.sh
RUN bash /tmp/dev_setup.sh --build-git /opt/git
# Git installs its builtins as hardlinks of one binary, which COPY --from
# would copy one by one; relink each group as relative symlinks and strip
# the ELF files' debug symbols.
RUN python3 - <<'PY'
import os
import subprocess
groups = {}
for root, _dirs, files in os.walk("/opt/git"):
    for name in files:
        path = os.path.join(root, name)
        st = os.lstat(path)
        if not os.path.islink(path) and st.st_nlink > 1:
            groups.setdefault(st.st_ino, []).append(path)
for paths in groups.values():
    keep, *rest = sorted(paths, key=lambda p: (len(p), p))
    for path in rest:
        os.unlink(path)
        os.symlink(os.path.relpath(keep, os.path.dirname(path)), path)
for root, _dirs, files in os.walk("/opt/git"):
    for name in files:
        path = os.path.join(root, name)
        if not os.path.islink(path):
            with open(path, "rb") as f:
                if f.read(4) == b"\x7fELF":
                    subprocess.run(["strip", "--strip-unneeded", path], check=True)
PY

FROM base AS claude-fetch
ARG CLAUDE_CODE_VERSION
RUN test -n "$CLAUDE_CODE_VERSION" || { \
      echo "error: pass --build-arg CLAUDE_CODE_VERSION=<version> (no default by design)" >&2; \
      exit 1; }
# The registry's own sha512 integrity for the platform package, as `npm
# install` checks it.
RUN python3 - <<'PY'
import base64, hashlib, io, json, os, re, tarfile, urllib.request
version = os.environ["CLAUDE_CODE_VERSION"]
if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
    raise SystemExit(f"CLAUDE_CODE_VERSION must be X.Y.Z, got {version!r}")
name = "@anthropic-ai/claude-code-linux-x64"
with urllib.request.urlopen(f"https://registry.npmjs.org/{name}/{version}", timeout=60) as r:
    dist = json.load(r)["dist"]
algo, _, want = dist["integrity"].partition("-")
if algo != "sha512":
    raise SystemExit(f"unexpected integrity algorithm {algo}")
with urllib.request.urlopen(dist["tarball"], timeout=600) as r:
    data = r.read()
if base64.b64encode(hashlib.sha512(data).digest()).decode() != want:
    raise SystemExit("claude-code-linux-x64 tarball failed its sha512 integrity check")
with tarfile.open(fileobj=io.BytesIO(data)) as tar:
    member = tar.getmember("package/claude")
    with open("/claude", "wb") as out:
        out.write(tar.extractfile(member).read())
os.chmod("/claude", 0o755)
PY

FROM node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da AS node

FROM base
# Git's runtime libraries, bubblewrap and socat (the CLI's Linux sandbox
# needs both), and the CA bundle.
RUN apt-get update \
 && apt-get install -y --no-install-recommends bubblewrap socat ca-certificates \
      libcurl4 libexpat1 zlib1g \
 && rm -rf /var/lib/apt/lists/*
# Git stays at the prefix it was built for (its exec path and templates are
# compiled in), first on PATH, and at /usr/bin/git, the one path the
# harness's own Git boundary runs (harness/workspace_git.py GIT).
COPY --from=git-build /opt/git /opt/git
RUN ln -s /opt/git/bin/git /usr/bin/git
ENV PATH=/opt/git/bin:$PATH
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && git --version && node --version && npm --version

# The same Python pins CI's test job installs, read from their one definition.
COPY scripts/dev_setup.sh /tmp/dev_setup.sh
RUN pip install --no-cache-dir $(bash /tmp/dev_setup.sh --print-pins) \
 && bash /tmp/dev_setup.sh --check-git \
 && rm /tmp/dev_setup.sh

COPY --from=claude-fetch /claude /usr/local/bin/claude
RUN claude --version

RUN useradd --create-home --home-dir /home/eval --shell /bin/bash eval \
 && mkdir -p /work /results && chown eval:eval /work /results
ENV HOME=/home/eval
USER eval
WORKDIR /work
