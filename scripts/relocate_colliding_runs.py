#!/usr/bin/env python3
"""Move a downloaded eval run off a run directory the results branch already holds.

    relocate_colliding_runs.py SNAPSHOT_RESULTS BRANCH_RESULTS

eval.yml's `publish` job copies one leg's downloaded `results/` onto
`persistent/eval-results`. A run directory is named by its UTC start second
(`%Y%m%dT%H%M%SZ`), and a guidance section's fixtures share
`results/guidance/<section>/<timestamp>/`, told apart only by each summary's
`fixture_name`. Two legs that start in the same second therefore name the
same directory: run 41587675812's `done-summary` leg found `handoff`'s
already published there, and the checkout refused to overwrite the
downloaded copy, so the paid result was lost. Copying it over instead would
have replaced `handoff`'s.

So before the copy, each downloaded run directory that the branch already
holds with DIFFERENT content moves to the next free second, and every
summary.json under it, and its report.md, are rewritten to that timestamp.
A run directory whose every file matches the branch's byte for byte is the
same run published again and is left alone. Prints one line per move,
naming only the two directory paths.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import sys

TIMESTAMP_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z")
FORMAT = "%Y%m%dT%H%M%SZ"
#: More seconds than any one run's legs could share.
MAX_SHIFT = 600


def run_dirs(results: Path) -> list[Path]:
    """Every directory under `results` named like a timestamp, outermost only."""
    found = []
    for path in sorted(results.rglob("*")):
        if not path.is_dir() or not TIMESTAMP_RE.fullmatch(path.name):
            continue
        if any(TIMESTAMP_RE.fullmatch(p.name) for p in path.relative_to(results).parents
               if p.name):
            continue
        found.append(path)
    return found


def same_run(downloaded: Path, published: Path) -> bool:
    files = [p for p in downloaded.rglob("*") if p.is_file()]
    return bool(files) and all(
        (published / p.relative_to(downloaded)).is_file()
        and (published / p.relative_to(downloaded)).read_bytes() == p.read_bytes()
        for p in files)


def free_timestamp(old: str, *parents: Path) -> str:
    start = datetime.strptime(old, FORMAT)
    for shift in range(1, MAX_SHIFT + 1):
        name = (start + timedelta(seconds=shift)).strftime(FORMAT)
        if not any((parent / name).exists() for parent in parents):
            return name
    raise SystemExit(f"no free run directory within {MAX_SHIFT}s of {old}")


def retimestamp(run_dir: Path, old: str, new: str) -> None:
    for summary in run_dir.rglob("summary.json"):
        doc = json.loads(summary.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and doc.get("timestamp") == old:
            doc["timestamp"] = new
            summary.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    for report in run_dir.rglob("report.md"):
        text = report.read_text(encoding="utf-8")
        report.write_text(text.replace(f"- Timestamp: {old}\n", f"- Timestamp: {new}\n"),
                          encoding="utf-8")


def relocate(snapshot: Path, branch: Path) -> list[tuple[str, str]]:
    moved = []
    for downloaded in run_dirs(snapshot):
        rel = downloaded.relative_to(snapshot)
        published = branch / rel
        if not published.exists() or same_run(downloaded, published):
            continue
        new = free_timestamp(downloaded.name, published.parent, downloaded.parent)
        target = downloaded.with_name(new)
        downloaded.rename(target)
        retimestamp(target, downloaded.name, new)
        moved.append((str(rel), str(target.relative_to(snapshot))))
    return moved


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    snapshot, branch = Path(argv[0]), Path(argv[1])
    if not snapshot.is_dir():
        return 0
    for old, new in relocate(snapshot, branch):
        print(f"::warning::run directory {old} is already published with other "
              f"content; publishing this run as {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
