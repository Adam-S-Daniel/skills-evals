#!/usr/bin/env python3
"""Add the private registry's ingested routine runs to a results tree.

    overlay_private_results.py --private DIR --tree DIR

Evals of a skill in adam-agentskills-private push their results to that
repository, not here, and its own ingest writes them to its
`persistent/eval-results` branch (Adam, 2026-10-31: private-skill results
live in the private skills repo and stay off the public explorer). The
weekly planner and the fire workflow's allowance guard still have to count
those runs, so each copies `<private>/routine-results/<run id>/` into
`<tree>/routine-results/` in the runner's workspace, never on a branch.

Data only: nothing is executed. A run directory whose name is not a run id,
a symlink anywhere, or a run id already present in the tree is refused
(exit 1) with a fixed message; the log carries counts, never file contents
or names from the private tree. A missing `<private>/routine-results/`
adds nothing (exit 0).
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = "routine-results"
RUN_ID_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{6}")


class OverlayError(Exception):
    pass


def _check_no_symlinks(path: Path) -> None:
    for child in path.rglob("*"):
        if child.is_symlink():
            raise OverlayError("a private run holds a symlink")


def overlay(private: Path, tree: Path) -> int:
    """Copy every private run into `tree`; return how many were copied."""
    source = private / ROOT
    if source.is_symlink():
        raise OverlayError("the private routine-results is a symlink")
    if not source.is_dir():
        return 0
    dest = tree / ROOT
    if dest.is_symlink():
        raise OverlayError("the tree's routine-results is a symlink")
    runs = sorted(source.iterdir())
    for run in runs:
        if run.is_symlink() or not run.is_dir() or not RUN_ID_RE.fullmatch(run.name):
            raise OverlayError("a private entry is not a run directory")
        if (dest / run.name).exists() or (dest / run.name).is_symlink():
            raise OverlayError("a private run id is already in the tree")
        _check_no_symlinks(run)
    dest.mkdir(parents=True, exist_ok=True)
    for run in runs:
        shutil.copytree(run, dest / run.name, symlinks=True)
    return len(runs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--tree", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        count = overlay(args.private, args.tree)
    except OverlayError as exc:
        print(f"::error::private results overlay: {exc}")
        return 1
    print(f"private results overlay: {count} run(s) added")
    return 0


if __name__ == "__main__":
    sys.exit(main())
