"""A small pool of background workers."""
import os
import signal
import subprocess


class Pool:
    def __init__(self):
        self.procs = []

    def start(self, cmd):
        """Start a worker in its own process group."""
        proc = subprocess.Popen(cmd, start_new_session=True)
        self.procs.append(proc)
        return proc

    def stop_all(self):
        """Stop every worker's process group, then forget them."""
        for proc in self.procs:
            os.killpg(proc.pid, signal.SIGTERM)
        self.procs.clear()
