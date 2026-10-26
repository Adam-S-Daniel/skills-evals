#!/usr/bin/env python3
"""Write a routine run's `vouch.json` (#70, round 5): a MAC over its results.

  printf %s "$NONCE" | python3 scripts/write_vouch.py eval-results/<run id>

The eval routine runs this after the harness and before it commits. The
nonce is the payload's `vouch_nonce`, which routine-eval-fire.yml derives
as HMAC-SHA256(VOUCH_KEY, run id) (`derive_nonce`) and sends to the routine
alone; nothing publishes it. It is read from stdin ONLY, never from argv or
the environment, and never printed.

`vouch.json` is {"mac": HMAC-SHA256(nonce, manifest) as hex}, where the
manifest (`manifest`) is, for every file the ingester keeps
(ingest_routine_results.KEEP_LONG_TERM: each summary.json and report.md at a
result path `parse_result_path` accepts) under the run directory, its path
relative to that directory and the hex sha256 of its bytes, sorted by path,
each field followed by a NUL. Files the ingester drops (tool traces) or
would reject are not in it: the MAC covers exactly what lands on
persistent/eval-results. routine-eval-ingest.yml's validate step, the one
verifier, re-derives the nonce from VOUCH_KEY and recomputes the MAC over
the files it staged, and stages nothing unless it matches. The MAC itself
is not secret; without the nonce no one can make one for other bytes.

Exit 0 when written; 2, with a reason that names no secret, when the nonce
is not 64 lowercase hex, the directory is missing, it holds a symlink, or it
has no file to vouch for.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent

VOUCH_FILE = "vouch.json"
NONCE_RE = re.compile(r"[0-9a-f]{64}")


def derive_nonce(key: bytes, run_id: str) -> str:
    """A run id's nonce: HMAC-SHA256(VOUCH_KEY, run id) as lowercase hex.
    routine-eval-fire.yml computes the same value in its fire step."""
    return hmac.new(key, run_id.encode("ascii"), hashlib.sha256).hexdigest()


def manifest(files: dict) -> bytes:
    """The canonical manifest of {relative path: bytes} (module docstring)."""
    return b"".join(rel.encode("utf-8") + b"\0" + hashlib.sha256(data).hexdigest().encode()
                    + b"\0" for rel, data in sorted(files.items()))


def mac(nonce: str, files: dict) -> str:
    return hmac.new(nonce.encode("ascii"), manifest(files), hashlib.sha256).hexdigest()


def vouched_files(run_dir: Path) -> dict:
    """{relative path: bytes} of the files the MAC covers, or ValueError for
    a symlink anywhere under `run_dir`."""
    # Imported here: the ingester imports this module for `mac`.
    sys.path.insert(0, str(SCRIPTS))
    import ingest_routine_results as ingest
    out = {}
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError("the run directory holds a symlink")
        if not path.is_file():
            continue
        rel = path.relative_to(run_dir).as_posix()
        if rel == VOUCH_FILE:
            continue
        try:
            kind = ingest.parse_result_path(rel)["kind"]
        except ingest.Rejected:
            continue
        if kind in ingest.KEEP_LONG_TERM:
            out[rel] = path.read_bytes()
    return out


def write(run_dir: Path, nonce: str) -> int:
    """Write `run_dir/vouch.json`; the number of files it covers."""
    files = vouched_files(run_dir)
    if not files:
        raise ValueError("the run directory has no result to vouch for")
    (run_dir / VOUCH_FILE).write_text(json.dumps({"mac": mac(nonce, files)}) + "\n",
                                      encoding="utf-8")
    return len(files)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: printf %s \"$NONCE\" | write_vouch.py RUN_DIR", file=sys.stderr)
        return 2
    nonce = sys.stdin.read()
    if nonce.endswith("\n"):
        nonce = nonce[:-1]
    if not NONCE_RE.fullmatch(nonce):
        print("write_vouch: the nonce on stdin is not 64 lowercase hex", file=sys.stderr)
        return 2
    run_dir = Path(args[0])
    if not run_dir.is_dir() or run_dir.is_symlink():
        print("write_vouch: the run directory does not exist", file=sys.stderr)
        return 2
    try:
        count = write(run_dir, nonce)
    except (ValueError, OSError) as exc:
        print(f"write_vouch: {exc}" if isinstance(exc, ValueError)
              else f"write_vouch: could not write vouch.json ({type(exc).__name__})",
              file=sys.stderr)
        return 2
    print(f"write_vouch: vouch.json covers {count} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
