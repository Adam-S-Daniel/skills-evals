"""Shared check that a workflow's `uses:` pin goes through actions.lock.

Third-party actions are named by release tag, and
`.github/workflows/actions.lock` locks each tag to an exact commit (ADR 0021
in Adam-S-Daniel/_agent-guidance). A step `uses:` that is not local (`./`,
`$/`), not `docker://` and not an `Adam-S-Daniel/cms-platform/` release-tag
ref must therefore have a lockfile entry keyed by the exact `uses:` string,
whose `commit` is `sha1-<40 lowercase hex>`, whose `ref` is the text after the
last `@`, and which the lockfile's `workflows` list for that file names.

The lockfile is read with PyYAML, never a line scan.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCKFILE = REPO_ROOT / ".github" / "workflows" / "actions.lock"
LOCKED_COMMIT = re.compile(r"sha1-[0-9a-f]{40}")
UNLOCKED_PREFIXES = ("./", "$/", "docker://", "Adam-S-Daniel/cms-platform/")


def load_lock(path: Path = LOCKFILE) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def lock_problem(uses: str, workflow: Path | str, lock: dict | None = None) -> str | None:
    """Why `uses` in `workflow` is not locked, or None when it is (or needs no lock)."""
    if uses.startswith(UNLOCKED_PREFIXES):
        return None
    lock = load_lock() if lock is None else lock
    key = f".github/workflows/{Path(workflow).name}"
    entry = (lock.get("dependencies") or {}).get(uses)
    if not isinstance(entry, dict):
        return f"{uses!r} has no actions.lock dependencies entry"
    commit = entry.get("commit")
    if not isinstance(commit, str) or not LOCKED_COMMIT.fullmatch(commit):
        return f"{uses!r} locks commit {commit!r}, not sha1-<40 lowercase hex>"
    if entry.get("ref") != uses.rsplit("@", 1)[-1]:
        return f"{uses!r} locks ref {entry.get('ref')!r}, not the tag it names"
    if uses not in ((lock.get("workflows") or {}).get(key) or []):
        return f"{uses!r} is missing from actions.lock's workflows[{key!r}]"
    return None
