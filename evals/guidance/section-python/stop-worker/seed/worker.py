"""Run a job as a child process."""

import subprocess


def start(command: list[str]) -> subprocess.Popen[bytes]:
    """Start the job in its own session, so it leads a new process group."""
    return subprocess.Popen(command, start_new_session=True)
