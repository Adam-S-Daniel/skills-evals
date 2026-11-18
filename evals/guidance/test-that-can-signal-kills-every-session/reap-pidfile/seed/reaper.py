"""Clean up after a crashed worker."""
import os
import signal
from pathlib import Path


def reap(pidfile):
    """Kill the worker whose pid the file holds, then delete the file.

    Returns True when a worker was signaled, False when the pid file is
    missing.
    """
    raise NotImplementedError
