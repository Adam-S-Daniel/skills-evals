"""Opt-in command checks; process-state isolation, not a filesystem sandbox.

See ADR 0006 for the trust boundary and the limits of optional network isolation.
No program output or exception text is included in published check details.
"""

from __future__ import annotations

import math
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_TIMEOUT_S = 30
MAX_TIMEOUT_S = 60
PROBE_TIMEOUT_S = 2
CLEANUP_TIMEOUT_S = 2
DIAGNOSTIC_BYTES = 4096
INTERPRETERS = {name: (f"/usr/bin/{name}", f"/bin/{name}")
                for name in ("bash", "sh", "python3", "node")}


def _executable(workspace: Path, name: str) -> str | None:
    if Path(name).name.casefold() in ("claude", "claude.exe"):
        return None
    if name in INTERPRETERS:
        return next((path for path in INTERPRETERS[name]
                     if os.path.isfile(path) and os.access(path, os.X_OK)), None)
    path = Path(name)
    path = path if path.is_absolute() else workspace / path
    path = path.resolve()
    if (not path.is_relative_to(workspace)
            or path.name.casefold() in ("claude", "claude.exe")):
        return None
    return str(path)


def _environment(root: Path) -> dict[str, str]:
    """A new environment, never a filtered copy of a credential-bearing one."""
    directories = {"HOME": "home", "XDG_CONFIG_HOME": "config",
                   "XDG_CACHE_HOME": "cache", "XDG_DATA_HOME": "data",
                   "XDG_STATE_HOME": "state", "XDG_RUNTIME_DIR": "runtime",
                   "GH_CONFIG_DIR": "gh", "TMPDIR": "tmp",
                   "TMP": "tmp", "TEMP": "tmp"}
    env = {name: str(root / relative) for name, relative in directories.items()}
    for directory in set(env.values()):
        Path(directory).mkdir(mode=0o700)
    private_bin = root / "bin"
    private_bin.mkdir(mode=0o700)
    refusal = private_bin / "claude"
    refusal.write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
    refusal.chmod(0o700)
    env.update(PATH=f"{private_bin}:/usr/bin:/bin", LANG="C", LC_ALL="C")
    return env


def _network_prefix(env: dict[str, str]) -> list[str]:
    """Use a new network namespace only when the Linux platform permits it."""
    import guidance
    guidance.check_timeout(PROBE_TIMEOUT_S, "_network_prefix timeout",
                           guidance.SINK_TIMEOUT_REMEDY)
    if not sys.platform.startswith("linux") or not Path("/usr/bin/unshare").is_file():
        return []
    prefix = ["/usr/bin/unshare", "--net", "--"]
    try:
        probe = subprocess.run(prefix + ["/usr/bin/true"], env=env,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=PROBE_TIMEOUT_S,
                               check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return prefix if probe.returncode == 0 else []


def _stop_process(proc) -> None:
    """Stop only our new session's group, including ordinary descendants."""
    import guidance
    guidance.check_timeout(CLEANUP_TIMEOUT_S, "_stop_process timeout",
                           guidance.SINK_TIMEOUT_REMEDY)
    pid = proc.pid
    # killpg(1, sig) is kill(-1, sig): it signals every process the user owns.
    if (type(pid) is not int or pid <= 1
            or pid in (os.getpid(), os.getpgrp())):
        raise ValueError("refusing to signal an unsafe process group id")
    try:
        if os.name == "posix":
            os.killpg(pid, signal.SIGKILL)
        elif proc.poll() is None:
            proc.kill()
    except ProcessLookupError:
        pass
    proc.wait(timeout=CLEANUP_TIMEOUT_S)


def _run_command(argv, workspace, env, stdout, stderr, timeout_s):
    """The guarded process sink, shared by every command-check entry path."""
    import guidance
    guidance.check_timeout(timeout_s, "_run_command timeout_s",
                           guidance.SINK_TIMEOUT_REMEDY)
    proc = subprocess.Popen(argv, cwd=workspace, env=env,
                            stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                            shell=False, start_new_session=os.name == "posix")
    try:
        return proc.wait(timeout=timeout_s)
    finally:
        _stop_process(proc)


def _output_metadata(stdout, stderr) -> str:
    sizes = [os.fstat(stream.fileno()).st_size for stream in (stdout, stderr)]
    truncated = any(size > DIAGNOSTIC_BYTES for size in sizes)
    return (f"stdout_bytes={min(sizes[0], DIAGNOSTIC_BYTES)} "
            f"stderr_bytes={min(sizes[1], DIAGNOSTIC_BYTES)} "
            f"output={'truncated' if truncated else 'suppressed'}")


def command_succeeds(workspace: str, paths: list[str], argv=None,
                     timeout_s=DEFAULT_TIMEOUT_S) -> tuple[bool, str]:
    """Pass only on exit zero from argv in the FINAL workspace.

    `paths` is registry metadata and is unused. No shell, interpolation, parent
    environment, user config, or credential is forwarded to the process.
    """
    if (not isinstance(argv, list) or not argv
            or any(not isinstance(arg, str) or "\x00" in arg for arg in argv)
            or not argv[0].strip()):
        return False, "command_invalid_argv"
    if (isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float))
            or not 0 < timeout_s <= MAX_TIMEOUT_S or not math.isfinite(timeout_s)):
        return False, "command_invalid_timeout"
    try:
        final_workspace = Path(workspace).resolve(strict=True)
        executable = _executable(final_workspace, argv[0])
    except (OSError, RuntimeError, ValueError):
        return False, "command_invalid_executable"
    if executable is None:
        return False, "command_invalid_executable"
    try:
        with tempfile.TemporaryDirectory(prefix="objective-command-") as temporary:
            env = _environment(Path(temporary))
            prefix = _network_prefix(env)
            network = "isolated" if prefix else "unavailable"
            with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
                try:
                    returncode = _run_command(prefix + [executable, *argv[1:]],
                                              final_workspace, env, stdout,
                                              stderr, timeout_s)
                except OSError:
                    return False, f"command_spawn_failed network={network}"
                except subprocess.TimeoutExpired:
                    return False, (f"command_timeout network={network} "
                                   + _output_metadata(stdout, stderr))
                status = "command_success" if returncode == 0 else "command_nonzero"
                return returncode == 0, (f"{status} exit={returncode} network={network} "
                                        + _output_metadata(stdout, stderr))
    except OSError:
        return False, "command_spawn_failed"
