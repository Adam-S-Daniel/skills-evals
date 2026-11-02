"""The fleet hook runner in arms that stand for the real setup (ADR 0012,
fleet hooks addendum; skills-evals#535).

An in-place arm of a `fleet_hooks: true` fixture gets the hooks its context
deployed, installed the way adam-agentskills ADR 0020's installer installs
them, and nothing else:

- `freeze` reads every file of _agent-guidance's `templates/agent-checks/`
  at the guidance revision the context loads, from Git objects only, and
  proves it: for a skill fixture, the context repository's own
  `.githooks/agent-checks` at `context.revision` must be the frozen runner,
  byte for byte (a guidance fixture's source is the template itself). Any
  gap is `fleet_hooks_unproven`, before any paid call.
- `install_modules` installs markdown-it, the dated-phrasing pass's one
  dependency, from the frozen lockfile with `npm ci --ignore-scripts`,
  outside the sandbox (arms have no network), once per plan.
- `materialize` writes the set, those modules, the include file and the
  sandbox receipt into the arm's own scratch, outside `ws/` and `tmp/`, and
  makes it read-only. `agent_env` is the environment that reaches the
  include: `includeIf.hasconfig:remote.*.url:<fleet owner>` keys through
  `GIT_CONFIG_COUNT`/`KEY_n`/`VALUE_n`, never `core.hooksPath`, so a hook
  fires only in a repository whose remote is the fleet's, as on a real
  machine. The workspace gets a fleet `origin`, unreachable in the sandbox.
- The include's hook command runs the frozen runner only when its own
  network namespace differs from the one the harness recorded in the
  receipt, that is inside the arm's sandbox. A Claude Code hook runs outside
  the sandbox with the same environment, and a commit it made would
  otherwise run the agent-written `.agent-checks/local.sh` unconfined.
- `guard_hooks` is the frozen `agent-checks-guard.sh` (_agent-guidance ADR
  0021) as a PreToolUse hook, delivered through the arm's `--settings`, as
  the sync registers it in a consumer's project settings.

`HookSet.digest` covers each file's path, mode and bytes and the injected
configuration with the arm's directory as a placeholder, so both arms of a
pair carry one digest, and compute_gates pools hooked runs apart from
unhooked ones by it.
"""

from __future__ import annotations

import atexit
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import tempfile

import context
import guidance

TEMPLATE_DIR = "templates/agent-checks"
#: Where the sync delivers the runner in a consumer repository.
CONSUMER_RUNNER = ".githooks/agent-checks"
RUNNER = "agent-checks"
GUARD = "agent-checks-guard.sh"
PACKAGE = "dated-phrasing/package.json"
LOCKFILE = "dated-phrasing/package-lock.json"
#: The installer's events, owners and URL prefixes (adam-agentskills
#: scripts/install-agent-hooks.sh).
EVENTS = ("pre-commit", "pre-push")
OWNERS = ("Adam-S-Daniel", "adam-s-daniel", "jodidaniel")
URL_PREFIXES = ("https://github.com/", "git@github.com:", "ssh://git@github.com/")
#: The sync's guard registration (_agent-guidance scripts/sync.sh).
GUARD_MATCHER = "Bash|Edit|Write|MultiEdit|NotebookEdit"
GUARD_TIMEOUT_S = 10
#: In the arm's scratch, beside `ws/`, `home/` and `tmp/`. The set sits under
#: `.githooks/`, the layout the runner expects beside it (dated-phrasing.js,
#: the fleet allowlist, the lockfile), which the guard also protects.
DIRNAME = "fleet-hooks"
HOOKS_SUBDIR = ".githooks"
INCLUDE = "agent-hooks.inc"
RECEIPT = "harness-netns"
#: The arm's directory in the digested configuration.
PLACEHOLDER = "/FLEET_HOOKS_DIR"
NPM_TIMEOUT_S = 300


@dataclass(frozen=True)
class HookSet:
    revision: str
    files: Mapping[str, bytes]
    modes: Mapping[str, str]
    digest: str


def _unproven(message: str) -> context.ContextError:
    return context.ContextError("fleet_hooks_unproven", message)


def conditions() -> list[str]:
    return [f"hasconfig:remote.*.url:{prefix}{owner}/**"
            for owner in OWNERS for prefix in URL_PREFIXES]


def _config_value(value: str) -> str:
    if "\n" in value or "\0" in value:
        raise _unproven("the fleet hooks directory path cannot be written into Git config")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def include_text(directory: str) -> str:
    """The include file: one config-based hook per event, as the installer
    writes it, but running the frozen runner, and only inside the sandbox."""
    root = shlex.quote(directory)
    lines = ["# Written by skills-evals harness/fleet_hooks.py (ADR 0012, fleet hooks addendum)."]
    for event in EVENTS:
        command = (f"d={root}; r=$(cat \"$d/{RECEIPT}\" 2>/dev/null) "
                   "&& n=$(readlink /proc/self/ns/net 2>/dev/null) "
                   "&& [ -n \"$r\" ] && [ -n \"$n\" ] && [ \"$n\" != \"$r\" ] || exit 0; "
                   f"exec bash \"$d/{HOOKS_SUBDIR}/{RUNNER}\" {event}")
        lines += [f'[hook "agent-checks-{event}"]', f"\tevent = {event}",
                  f"\tcommand = {_config_value(command)}"]
    return "\n".join(lines) + "\n"


def agent_env(directory) -> dict[str, str]:
    """What the agent's environment gains: the include, reached only from a
    fleet remote, plus the runner's markdown-it and its run log off."""
    directory = str(directory)
    env = {"GIT_CONFIG_COUNT": str(len(conditions()))}
    for index, condition in enumerate(conditions()):
        env[f"GIT_CONFIG_KEY_{index}"] = f"includeIf.{condition}.path"
        env[f"GIT_CONFIG_VALUE_{index}"] = f"{directory}/{INCLUDE}"
    env["AGENT_CHECKS_LOG"] = "off"
    env["AGENT_CHECKS_DATED_PHRASING_MODULES"] = \
        f"{directory}/{HOOKS_SUBDIR}/dated-phrasing/node_modules"
    return env


def guard_hooks(directory) -> dict:
    """The `hooks` value of the arm's `--settings`."""
    command = "bash " + shlex.quote(f"{directory}/{HOOKS_SUBDIR}/{GUARD}")
    return {"PreToolUse": [{"matcher": GUARD_MATCHER, "hooks": [
        {"type": "command", "command": command, "timeout": GUARD_TIMEOUT_S}]}]}


def _digest(files: Mapping[str, bytes], modes: Mapping[str, str]) -> str:
    manifest = {"files": [{"path": name, "mode": modes[name],
                           "digest": hashlib.sha256(raw).hexdigest()}
                          for name, raw in sorted(files.items())],
                "include": include_text(PLACEHOLDER), "env": agent_env(PLACEHOLDER),
                "guard": guard_hooks(PLACEHOLDER)}
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


def freeze(frozen: context.FrozenContext, repositories: Mapping[str, Path], *,
           guidance_subject: bool) -> HookSet:
    """The proven hook set for `frozen` (module docstring)."""
    repository = frozen.manifest["repository"]
    if repository.split("/", 1)[0] not in OWNERS:
        raise _unproven(f"{repository} is not a fleet repository, so no fleet hook "
                        "would fire in its clone")
    revision = frozen.manifest["guidance"]["revision"]
    try:
        source = context._Git(context.GUIDANCE_REPOSITORY, repositories)
        tree = source.tree(source.revision(revision))
        prefix = TEMPLATE_DIR + "/"
        names = sorted(name for name in tree if name.startswith(prefix))
        files = {name[len(prefix):]: source.read(tree, name) for name in names}
        modes = {name[len(prefix):]: tree[name][0] for name in names}
        missing = [name for name in (RUNNER, GUARD, PACKAGE, LOCKFILE) if name not in files]
        if missing:
            raise _unproven(f"{context.GUIDANCE_REPOSITORY} at {revision} has no "
                            f"{TEMPLATE_DIR}/{missing[0]}")
        if not guidance_subject:
            consumer = context._Git(repository, repositories)
            shipped = consumer.read(consumer.tree(consumer.revision(frozen.manifest["revision"])),
                                    CONSUMER_RUNNER, optional=True)
            if shipped != files[RUNNER]:
                raise _unproven(f"{repository}'s {CONSUMER_RUNNER} at the context revision is "
                                f"{'absent' if shipped is None else 'not'} the runner "
                                f"{context.GUIDANCE_REPOSITORY} shipped at {revision}")
    except context.ContextError as exc:
        if exc.code == "fleet_hooks_unproven":
            raise
        raise _unproven(f"the fleet hook set cannot be read ({exc.code})") from exc
    return HookSet(revision, context._freeze(files), context._freeze(modes),
                   _digest(files, modes))


def _npm_ci(directory: Path) -> None:
    """The network seam: markdown-it from the frozen lockfile, no scripts."""
    guidance.check_timeout(NPM_TIMEOUT_S, "fleet_hooks._npm_ci(timeout=)",
                           guidance.SINK_TIMEOUT_REMEDY)
    try:
        result = subprocess.run(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund",
                                 "--loglevel=error"], cwd=directory, stdin=subprocess.DEVNULL,
                                capture_output=True, timeout=NPM_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise context.ContextError("fleet_hooks_install_failed",
                                   f"npm ci for markdown-it failed ({type(exc).__name__})") from exc
    if result.returncode:
        raise context.ContextError("fleet_hooks_install_failed",
                                   f"npm ci for markdown-it exited {result.returncode}")


def install_modules(hooks: HookSet) -> Path:
    """A directory holding `node_modules` with markdown-it, removed at exit."""
    # A prefix run_eval.HARNESS_TEMP_PREFIXES lists, so no arm reads it.
    target = Path(tempfile.mkdtemp(prefix="fleet-hooks-modules-"))
    atexit.register(shutil.rmtree, target, True)
    for name in (PACKAGE, LOCKFILE):
        (target / Path(name).name).write_bytes(hooks.files[name])
    _npm_ci(target)
    if not (target / "node_modules" / "markdown-it" / "package.json").is_file():
        raise context.ContextError("fleet_hooks_install_failed",
                                   "npm ci left no node_modules/markdown-it")
    return target


def _set_writable(directory: Path, writable: bool) -> None:
    for current, dirs, files in os.walk(directory):
        for name in files:
            path = Path(current) / name
            if not path.is_symlink():
                mode = path.stat().st_mode
                path.chmod((mode | stat.S_IWUSR) if writable
                           else mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        Path(current).chmod(0o755 if writable else 0o555)


def materialize(hooks: HookSet, directory: Path, modules: Path) -> None:
    """Write the set, its modules, the include and the receipt, read-only."""
    directory.mkdir()
    root = directory / HOOKS_SUBDIR
    for name, raw in hooks.files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o755 if hooks.modes[name] == "100755" else 0o644)
    shutil.copytree(modules / "node_modules", root / "dated-phrasing" / "node_modules",
                    symlinks=True)
    (directory / INCLUDE).write_text(include_text(str(directory)), encoding="utf-8")
    try:
        receipt = os.readlink("/proc/self/ns/net")
    except OSError as exc:
        raise context.ContextError("fleet_hooks_no_receipt", "this host has no network "
                                   "namespace id to tell the arm's sandbox apart") from exc
    (directory / RECEIPT).write_text(receipt + "\n", encoding="utf-8")
    _set_writable(directory, False)


def unlock(directory: Path) -> None:
    """Make a materialized set removable again (before its scratch goes)."""
    try:
        if directory.is_dir() and not directory.is_symlink():
            _set_writable(directory, True)
    except OSError:
        pass  # cleanup is best effort, like the rmtree after it


def tree_digest(directory: Path) -> str:
    """Every path under `directory` with its mode and bytes (or link target),
    read before the first turn and after each; any change is the agent's."""
    digest = hashlib.sha256()
    for current, dirs, files in os.walk(directory):
        dirs.sort()
        for name in sorted(dirs + files):
            path = Path(current) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                body = b"link:" + os.readlink(path).encode()
            elif stat.S_ISREG(info.st_mode):
                body = hashlib.sha256(path.read_bytes()).digest()
            else:
                body = b""
            digest.update(path.relative_to(directory).as_posix().encode() + b"\0"
                          + str(info.st_mode).encode() + b"\0" + body + b"\n")
    return digest.hexdigest()

