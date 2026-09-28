#!/usr/bin/env python3
"""Ask the installed Claude Code CLI which model each family alias resolves to.

The roster seats a tier's vendor-default model the day it changes (#202,
docs/decisions/0002-roster-follows-vendor-defaults.md), so it needs to know
what the default IS. The source is the CLI itself, installed fresh at the
npm latest on every CI run (#203): for each family word on the policy's tier
ladder it starts

    claude -p <prompt> --model <alias> --output-format stream-json --verbose

and reads the `model` field of the first `{"type": "system", "subtype":
"init"}` event. The CLI resolves the alias before it emits that event and
before it sends anything to a model, and it does so with NO credential
(measured 2026-09-28 on 2.1.283 with an empty environment and a fresh HOME:
`apiKeySource` reported `none`). So the probe costs nothing: as soon as the
init event is read the process is terminated (SIGTERM, then SIGKILL after
`KILL_GRACE_SECONDS`), never left to try the API.

A word the CLI does not know as an alias is echoed back unchanged in the
init event (`mythos` on 2.1.283); it is recorded under `skipped`, not as a
default.

THE ENVIRONMENT IS SCRUBBED, whatever the caller's holds. The CLI is given
only PATH, a fresh temporary HOME per call (with the XDG directories inside
it, removed afterwards), and LANG=C — never a credential, a config dir or a
cloud-provider selector — with stdin from /dev/null and the temporary HOME as
its working directory, so no project or user settings are read either. See
`scrubbed_env`.

  --out   {"probed_at": <ISO timestamp>,
           "harness_version": <first line of `claude --version`, sanitised,
                               or null>,
           "defaults": {alias: model id},
           "skipped": [alias, ...],
           "errors": {alias: "no-init" | "timeout" | "bad-model" |
                             <exception class>}}

A FAILURE IS NOT FATAL. Whatever happens to one alias or all of them, --out
is written and the exit status is 0; `harness/roster.py` decides what a
missing default means (with none at all, every tier keeps the usage and
newest-in-tier rules, and says so). Only a usage error — bad arguments, an
unreadable --policy, an unwritable --out — exits non-zero.

The CLI's output is UNTRUSTED. Nothing it prints reaches this script's own
output or --out except a model id that matches `MODEL_ID_RE` and a version
line reduced to `VERSION_CHARS`; everything else is an error class from the
fixed list above or an exception's class name. This runs in a public CI log.

No model id appears in this file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "evals" / "roster-policy.yml"
#: Per-alias bound on waiting for the init event.
TIMEOUT_SECONDS = 60.0
#: How long a CLI gets to exit after SIGTERM before it is killed.
KILL_GRACE_SECONDS = 5.0
#: What the CLI is asked. Nothing is sent to a model before the init event,
#: and the process is terminated as soon as that event is read; the prompt
#: only keeps a CLI that demands input from exiting before init.
PROMPT = "."
#: A family word, as the ladder spells one.
ALIAS_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}\Z")
#: A conservative model-id shape: lowercase letters, digits, dashes and dots.
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,63}\Z")
#: The characters a version line may keep (the same set eval.yml's install
#: step keeps), and how much of the line is read.
VERSION_CHARS = re.compile(r"[^A-Za-z0-9._() -]")
VERSION_MAX = 80
#: Stdout read before the init event past which the CLI is not answering.
MAX_BYTES = 4 * 1024 * 1024


def scrubbed_env(home: Path) -> dict[str, str]:
    """The whole environment a probed CLI gets. Built from nothing rather
    than filtered from `os.environ`, so no ANTHROPIC_*, CLAUDE_*, AWS_*,
    GOOGLE_* or *TOKEN*/*KEY* variable can reach it however it is spelled."""
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "LANG": "C",
    }


def ladder_aliases(policy: dict) -> list[str]:
    """Every family word on the policy's tier ladder, in ladder order. A rung
    is a word or a list of peer words; a word that is not alias-shaped is
    not probed."""
    tiers = policy.get("tiers") if isinstance(policy, dict) else None
    if not isinstance(tiers, list):
        raise ValueError("the policy has no `tiers` list")
    words: list[str] = []
    for rung in tiers:
        for word in (rung if isinstance(rung, list) else [rung]):
            if isinstance(word, str) and ALIAS_RE.match(word) and word not in words:
                words.append(word)
    return words


class _Home:
    """A fresh temporary HOME with its XDG directories, removed on exit."""

    def __enter__(self) -> Path:
        self.path = Path(tempfile.mkdtemp(prefix="claude-probe-home-")).resolve()
        for sub in (".config", ".cache", ".local/share", ".local/state"):
            (self.path / sub).mkdir(parents=True, exist_ok=True)
        return self.path

    def __exit__(self, *_exc) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def _signal_group(proc: subprocess.Popen, sig: int) -> None:
    try:
        os.killpg(proc.pid, sig)
    except (ProcessLookupError, PermissionError):
        try:
            proc.send_signal(sig)
        except (ProcessLookupError, OSError):
            pass


def _stop(proc: subprocess.Popen) -> None:
    """Terminate the CLI and anything it started: SIGTERM, then SIGKILL."""
    if proc.poll() is None:
        _signal_group(proc, signal.SIGTERM)
        try:
            proc.wait(KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _signal_group(proc, signal.SIGKILL)
            proc.wait()
    if proc.stdout is not None:
        proc.stdout.close()


_NOT_INIT = object()


def _init_model(line: bytes):
    """The `model` of an init event on this line, or `_NOT_INIT`."""
    try:
        event = json.loads(line.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError):
        return _NOT_INIT
    if (isinstance(event, dict) and event.get("type") == "system"
            and event.get("subtype") == "init"):
        return event.get("model")
    return _NOT_INIT


def _read_init(proc: subprocess.Popen, timeout: float):
    """(model, None) from the first init event, or (None, error class)."""
    deadline = time.monotonic() + timeout
    fd = proc.stdout.fileno()
    buffer = b""
    total = 0
    with selectors.DefaultSelector() as selector:
        selector.register(fd, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                return None, "timeout"
            chunk = os.read(fd, 65536)
            if not chunk:
                found = _init_model(buffer) if buffer.strip() else _NOT_INIT
                return (found, None) if found is not _NOT_INIT else (None, "no-init")
            total += len(chunk)
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                found = _init_model(line)
                if found is not _NOT_INIT:
                    return found, None
            if total > MAX_BYTES:
                return None, "no-init"


def probe_alias(claude: str, alias: str, timeout: float) -> tuple[str, str]:
    """("default", model id), ("skipped", alias) or ("error", class)."""
    with _Home() as home:
        try:
            proc = subprocess.Popen(
                [claude, "-p", PROMPT, "--model", alias,
                 "--output-format", "stream-json", "--verbose"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, cwd=home, env=scrubbed_env(home),
                start_new_session=True)
        except Exception as exc:  # noqa: BLE001 -- the class name only
            return "error", type(exc).__name__
        try:
            model, error = _read_init(proc, timeout)
        except Exception as exc:  # noqa: BLE001
            model, error = None, type(exc).__name__
        finally:
            _stop(proc)
    if error:
        return "error", error
    if not (isinstance(model, str) and MODEL_ID_RE.match(model)):
        return "error", "bad-model"
    if model == alias:
        return "skipped", alias
    return "default", model


def harness_version(claude: str, timeout: float) -> str | None:
    """The first line of `claude --version`, cut and reduced to version
    characters; None when it fails or leaves nothing."""
    with _Home() as home:
        try:
            done = subprocess.run([claude, "--version"], stdin=subprocess.DEVNULL,
                                  capture_output=True, cwd=home,
                                  env=scrubbed_env(home), timeout=timeout)
        except Exception:  # noqa: BLE001 -- a version is optional
            return None
    if done.returncode != 0:
        return None
    line = done.stdout.decode("utf-8", "replace").split("\n", 1)[0]
    version = VERSION_CHARS.sub("", line[:VERSION_MAX]).strip()
    return version or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True,
                        help="where to write the defaults document")
    parser.add_argument("--claude", default="claude",
                        help="the Claude Code binary to probe (default: claude)")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY,
                        help="the roster policy whose tier ladder names the aliases")
    parser.add_argument("--timeout", type=float, default=TIMEOUT_SECONDS,
                        help="seconds to wait for each alias's init event")
    args = parser.parse_args()
    if not args.timeout > 0:
        parser.error("--timeout must be positive")

    try:
        with open(args.policy, encoding="utf-8") as handle:
            aliases = ladder_aliases(yaml.safe_load(handle))
    except (OSError, yaml.YAMLError, ValueError, UnicodeDecodeError) as exc:
        print(f"probe_model_defaults: cannot read the policy's tier ladder "
              f"({type(exc).__name__})", file=sys.stderr)
        return 2

    probed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    version = harness_version(args.claude, args.timeout)
    defaults: dict[str, str] = {}
    skipped: list[str] = []
    errors: dict[str, str] = {}
    for alias in aliases:
        kind, value = probe_alias(args.claude, alias, args.timeout)
        if kind == "default":
            defaults[alias] = value
        elif kind == "skipped":
            skipped.append(alias)
        else:
            errors[alias] = value

    document = {"probed_at": probed_at, "harness_version": version,
                "defaults": defaults, "skipped": skipped, "errors": errors}
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2)
            handle.write("\n")
    except OSError as exc:
        print(f"probe_model_defaults: cannot write --out ({type(exc).__name__})",
              file=sys.stderr)
        return 1
    # Validated aliases, validated ids and fixed error classes only.
    said = ", ".join(f"{a} -> {m}" for a, m in defaults.items()) or "none"
    failed = ", ".join(f"{a} ({e})" for a, e in errors.items()) or "none"
    print(f"probe_model_defaults: Claude Code {version or 'version unknown'}; "
          f"defaults: {said}; skipped (not an alias): "
          f"{', '.join(skipped) or 'none'}; failed: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
