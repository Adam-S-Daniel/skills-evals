"""Opt-in command checks inside a mandatory filesystem and PID sandbox.

See ADR 0006 for the trust boundary and the limits of optional network isolation.
No program output or exception text is included in published check details.
"""

from __future__ import annotations

import math
import os
import shutil
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
BWRAP_PATHS = ("/usr/bin/bwrap", "/bin/bwrap", str(Path.home() / ".local/bin/bwrap"))
SANDBOX_STARTUP_MARKER = b"scorer-sandbox-started\n"
SANDBOX_BOOTSTRAP = (
    "import os, sys\n"
    "fd = int(sys.argv[1])\n"
    "os.write(fd, b'scorer-sandbox-started\\n')\n"
    "os.close(fd)\n"
    "os.execv(sys.argv[2], sys.argv[2:])\n"
)
SYSTEM_PATH = ("/usr/bin", "/bin")
INTERPRETERS = {name: (f"/usr/bin/{name}", f"/bin/{name}")
                for name in ("bash", "sh", "python3", "node")}


def _fixed_interpreter(name: str) -> str | None:
    return next((path for path in INTERPRETERS[name]
                 if os.path.isfile(path) and os.access(path, os.X_OK)), None)


def _executable(workspace: Path, name: str) -> str | None:
    if Path(name).name.casefold() in ("claude", "claude.exe"):
        return None
    if name in INTERPRETERS:
        fixed = _fixed_interpreter(name)
        # Runners keep node outside /usr/bin and /bin; use the same harness node
        # the child's PATH gets, with the same refusals.
        return fixed if fixed is not None or name != "node" else _harness_node(workspace)
    path = Path(name)
    path = path if path.is_absolute() else workspace / path
    path = path.resolve()
    if (not path.is_relative_to(workspace)
            or path.name.casefold() in ("claude", "claude.exe")):
        return None
    return str(path)


def _harness_node(workspace: Path | None) -> str | None:
    """The harness's own node, for hosts that install it outside /usr/bin.

    GitHub's runner image puts node in /usr/local/bin and setup-node in its
    tool cache, so neither a bare `node` argv nor a verifier's PATH lookup of
    `node` finds it there. Only node is exposed, and never one resolved inside
    the workspace the agent wrote.
    """
    if _fixed_interpreter("node") is not None:
        return None
    found = shutil.which("node")
    if found is None or not os.path.isabs(found):
        return None
    resolved = Path(found).resolve()
    if workspace is not None and resolved.is_relative_to(workspace.resolve()):
        return None
    return str(resolved) if os.access(resolved, os.X_OK) else None


def _environment(root: Path, workspace: Path | None = None) -> dict[str, str]:
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
    path = ":".join((str(private_bin), *SYSTEM_PATH))
    node = _harness_node(workspace)
    if node is not None:
        # A directory holding only node, after the fixed ones, so stubs still win
        # and no other host tool beside the harness's node becomes reachable.
        node_bin = root / "node-bin"
        node_bin.mkdir(mode=0o700)
        (node_bin / "node").symlink_to(node)
        path += f":{node_bin}"
    env.update(PATH=path, LANG="C", LC_ALL="C")
    return env


class ScorerSandboxUnavailable(RuntimeError):
    """A sanitized failure to establish the mandatory scoring boundary."""

    def __init__(self, exit_code=None):
        code = str(exit_code) if type(exit_code) is int else "-1"
        super().__init__(f"scorer_sandbox_unavailable exit={code}")


def _bubblewrap(workspace: Path | None = None, read_denied=()) -> str | None:
    """Resolve the harness's runner before hiding HOME, never agent code."""
    if not sys.platform.startswith("linux"):
        return None
    # PATH may name an agent-planted bwrap in the original workspace.
    # The HOME-local fallback is fixed when the harness module is imported.
    blocked = [Path(p).resolve() for p in read_denied
               if Path(p).resolve() != Path.home().resolve()]
    for candidate in BWRAP_PATHS:
        if not candidate or not os.path.isabs(candidate):
            continue
        try:
            path = Path(candidate).resolve(strict=True)
            if ((workspace is not None and path.is_relative_to(workspace.resolve()))
                    or any(path.is_relative_to(root) for root in blocked)):
                continue
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
        except (OSError, RuntimeError, ValueError):
            continue
    return None


def _read_denied(read_denied) -> list[Path]:
    """Trusted caller roots plus direct-call protection for harness and HOME."""
    roots = [Path(__file__).resolve().parents[2], Path.home(), *(read_denied or ())]
    out = []
    for root in roots:
        path = Path(root).resolve()
        if not path.exists():
            continue
        if path == Path("/") or not path.is_dir():
            raise ScorerSandboxUnavailable()
        if path not in out:
            out.append(path)
    return out


def _sandbox_mounts(workspace: Path, env_root: Path, denied) -> list[str]:
    """Hide ancestors first, then reopen only execution and environment roots."""
    writable = (workspace.resolve(), env_root.resolve())
    denied = {Path(p).resolve() for p in denied}
    if (Path("/") in writable
            or any(path.is_relative_to(root) for path in denied for root in writable)):
        # Reopening a writable parent must never reopen a denied child.
        raise ScorerSandboxUnavailable()
    collapsed = []
    for path in sorted(denied, key=lambda p: (len(p.parts), str(p))):
        if not any(path.is_relative_to(parent) for parent in collapsed):
            collapsed.append(path)
    mounts = ["--ro-bind", "/", "/"]
    for path in collapsed:
        mounts += ["--tmpfs", str(path)]
    for path in writable:
        mounts += ["--bind", str(path), str(path)]
    # Destination directories must exist before their hidden ancestor is made
    # read-only. Remounting only that mount leaves the two binds writable.
    for path in collapsed:
        mounts += ["--remount-ro", str(path)]
    return mounts


def _sandbox_prefix(workspace: Path, env_root: Path, env: dict[str, str],
                    read_denied=None) -> tuple[list[str], str]:
    """Probe the exact filesystem/PID boundary; only network may fall back."""
    import guidance
    guidance.check_timeout(PROBE_TIMEOUT_S, "_sandbox_prefix timeout",
                           guidance.SINK_TIMEOUT_REMEDY)
    denied = _read_denied(read_denied)
    executable = _bubblewrap(workspace, denied)
    if executable is None:
        raise ScorerSandboxUnavailable()
    mounts = _sandbox_mounts(workspace, env_root, denied)
    base = [executable, *mounts, "--unshare-pid", "--proc", "/proc", "--dev", "/dev",
            "--die-with-parent", "--chdir", str(workspace), "--"]
    last_code = None
    for network in ("isolated", "unavailable"):
        prefix = [*base[:-1], *(("--unshare-net",) if network == "isolated" else ()), "--"]
        try:
            probe = subprocess.run(prefix + ["/usr/bin/true"], cwd=workspace, env=env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=PROBE_TIMEOUT_S, check=False)
        except (OSError, subprocess.TimeoutExpired):
            last_code = None
            continue
        last_code = probe.returncode
        if last_code == 0:
            return prefix, network
    raise ScorerSandboxUnavailable(last_code)


def _sandbox_started(stream) -> bool:
    stream.seek(0)
    return stream.read(len(SANDBOX_STARTUP_MARKER) + 1) == SANDBOX_STARTUP_MARKER


def _run_sandboxed(prefix, argv, workspace, env, stdout, stderr, timeout_s):
    """Confirm actual sandbox startup, independently of the command's exit."""
    with tempfile.TemporaryFile() as started:
        fd = started.fileno()
        python = _fixed_interpreter("python3")
        if python is None:
            raise ScorerSandboxUnavailable()
        # bubblewrap's info-fd reports a fork before mount/loopback setup.
        # Isolated system Python reaches this marker only after all setup;
        # it closes the descriptor before replacing itself with agent code.
        launch = [*prefix, python, "-I", "-S", "-c", SANDBOX_BOOTSTRAP,
                  str(fd), *argv]
        try:
            code = _run_command(launch, workspace, env, stdout, stderr, timeout_s,
                                pass_fds=(fd,))
        except OSError:
            raise ScorerSandboxUnavailable() from None
        except subprocess.TimeoutExpired:
            if not _sandbox_started(started):
                raise ScorerSandboxUnavailable() from None
            raise
        if not _sandbox_started(started):
            raise ScorerSandboxUnavailable(code)
        return code


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


def _run_command(argv, workspace, env, stdout, stderr, timeout_s, *, pass_fds=()):
    """The guarded process sink, shared by every command-check entry path."""
    import guidance
    guidance.check_timeout(timeout_s, "_run_command timeout_s",
                           guidance.SINK_TIMEOUT_REMEDY)
    proc = subprocess.Popen(argv, cwd=workspace, env=env,
                            stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                            shell=False, start_new_session=os.name == "posix",
                            pass_fds=pass_fds)
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
                     timeout_s=DEFAULT_TIMEOUT_S, *, read_denied=None) -> tuple[bool, str]:
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
            env = _environment(Path(temporary), final_workspace)
            prefix, network = _sandbox_prefix(final_workspace, Path(temporary), env, read_denied)
            if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
                return False, f"command_spawn_failed network={network}"
            with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
                try:
                    returncode = _run_sandboxed(prefix, [executable, *argv[1:]],
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
    except ScorerSandboxUnavailable as exc:
        return False, str(exc)
    except OSError:
        return False, "command_spawn_failed"
