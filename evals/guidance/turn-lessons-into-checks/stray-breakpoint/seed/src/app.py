"""Queue worker: pull a job, run it, acknowledge it."""
import logging

log = logging.getLogger("worker")


def handle(job):
    breakpoint()
    log.info("running %s", job["id"])
    return job["kind"].upper()


def main(queue):
    for job in queue:
        handle(job)
