"""Is this process inside a sealed eval container (scripts/container_eval.sh)?

The sealed lane runs an eval on the owner's workstation in a Docker container
on an internal network whose only ways out are sidecars. `container_eval.sh`
sets `SKILLS_EVALS_IN_CONTAINER=1` and `EVAL_SEAL` to the seal it built:

- `proxy` (the default): the real token stays in a credential-proxy sidecar.
  This container holds `CLAUDE_CODE_OAUTH_TOKEN=dummy-not-a-token` and
  `ANTHROPIC_BASE_URL=http://<sidecar>:<port>`; the sidecar replaces the
  Authorization header.
- `allowlist` (the fallback): the real token is in this container, and an
  egress sidecar lets it reach api.anthropic.com only.

`sealed_container` answers which seal holds, or None. Every condition must
hold, and anything else is None, so a caller that keys a widening (an
in-place pair outside a hosted session, a credential name in an arm's
environment) on it fails closed outside the container.
"""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

DOCKERENV = Path("/.dockerenv")
CONTAINER_FLAG = "SKILLS_EVALS_IN_CONTAINER"
SEAL_VAR = "EVAL_SEAL"
SEALS = ("proxy", "allowlist")
TOKEN_NAME = "CLAUDE_CODE_OAUTH_TOKEN"
BASE_URL_NAME = "ANTHROPIC_BASE_URL"
#: The only value the proxy seal's base URL may take: the run's sidecar, one
#: lowercase DNS label with an explicit port. Never a dotted public host,
#: userinfo or a path.
BASE_URL_RE = re.compile(r"http://[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?:[0-9]{1,5}")
#: What the proxy seal hands this container in place of the token.
DUMMY_TOKEN = "dummy-not-a-token"


def sealed_container(environ: Mapping[str, str] | None = None,
                     dockerenv: Path = DOCKERENV) -> str | None:
    """`"proxy"` or `"allowlist"` when this process is in a sealed container,
    else None.

    All of: `dockerenv` exists, `SKILLS_EVALS_IN_CONTAINER` is exactly `1`,
    and `EVAL_SEAL` names a seal whose own condition holds:

    - proxy: `ANTHROPIC_BASE_URL` fully matches BASE_URL_RE and
      `CLAUDE_CODE_OAUTH_TOKEN` is exactly the dummy;
    - allowlist: `CLAUDE_CODE_OAUTH_TOKEN` is non-empty and
      `ANTHROPIC_BASE_URL` is not set.

    Reads values only to compare them; never returns or logs one.
    """
    environ = os.environ if environ is None else environ
    if not Path(dockerenv).exists() or environ.get(CONTAINER_FLAG) != "1":
        return None
    seal = environ.get(SEAL_VAR)
    token = environ.get(TOKEN_NAME, "")
    if seal == "proxy":
        base_url = environ.get(BASE_URL_NAME, "")
        if BASE_URL_RE.fullmatch(base_url) and token == DUMMY_TOKEN:
            return "proxy"
        return None
    if seal == "allowlist":
        if token and BASE_URL_NAME not in environ:
            return "allowlist"
        return None
    return None
