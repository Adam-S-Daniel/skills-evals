"""The lock-kind digest of a skill directory, shared by every reader here.

`lock_digest` is, byte for byte, the algorithm of adam-agentskills'
`scripts/generate_skills_lock.py::digest_skill_dir` (and the bootstrap hook's
`digest_dir`, which mirrors it): the digest a `skills.lock` and the hook's
install record name. A manifest line `<posix relpath>\\0<sha256 hex of the
file's bytes>\\n` per regular file, sorted by relpath, hashed as UTF-8 with
sha256, returned as bare lowercase hex. Directories carry no bytes; a symbolic
link anywhere (the root included) is refused, as the generator refuses it.

Two refusals are this module's own. Each yields no digest rather than a
different one, so any digest returned is the generator's: an entry that is
neither a directory nor a regular file (a FIFO, a device) is refused, where
the generator skips it, since opening a FIFO can block; and a tree past
`MAX_FILES` files or `MAX_BYTES` bytes (counted as they are read) raises
`DigestTooLarge`, so a base directory that turns out to be a whole checkout
cannot stall a census run.

`git_ignored` is the generator's `ignored_paths`: the untracked files git
ignores under a work tree, as absolute paths, for `skip`. A tracked file that
matches an ignore rule is not in it and still counts.

`test/issues/test_issue_skill_digest.py` holds the test vector, and checks it
against the generator itself when an adam-agentskills checkout is beside this
one. `harness/propagation/arms.digest_skill_dir` is a separate copy and is not
this function.

Stdlib only.
"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from pathlib import PurePath

#: The most regular files a tree may hold before `DigestTooLarge`.
MAX_FILES = 2000
#: The most bytes (50 MiB) read across a tree before `DigestTooLarge`.
MAX_BYTES = 50 * 1024 * 1024
_CHUNK = 1024 * 1024
_SHA256_PREFIX = "sha256:"


class DigestRefused(Exception):
    """The tree holds something a lock digest cannot commit to: a symbolic
    link (the root included) or an entry that is not a regular file or a
    directory."""


class DigestTooLarge(Exception):
    """The tree passed `MAX_FILES` files or `MAX_BYTES` bytes."""


def normalize(digest: str) -> str:
    """`digest` without one leading `sha256:` (a lock may carry the prefix)."""
    return digest[len(_SHA256_PREFIX):] if digest.startswith(_SHA256_PREFIX) else digest


def _file_sha256(path: str, budget: list) -> str:
    """sha256 hex of `path`'s bytes, charging them to `budget` ([bytes left])
    as they are read."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(_CHUNK)
            if not chunk:
                break
            budget[0] -= len(chunk)
            if budget[0] < 0:
                raise DigestTooLarge(f"more than {MAX_BYTES} bytes")
            digest.update(chunk)
    return digest.hexdigest()


def lock_digest(root, skip=frozenset()) -> str:
    """The lock digest of the directory `root` (see the module docstring).

    `skip` holds absolute paths left out of the manifest, compared after
    `root` is resolved, as the generator compares them (`git_ignored`'s
    output fits). Raises DigestRefused, DigestTooLarge, or OSError
    (NotADirectoryError when `root` is not a directory).
    """
    if os.path.islink(root):
        raise DigestRefused("the skill directory is a symbolic link")
    top = os.path.realpath(root)
    if not os.path.isdir(top):
        raise NotADirectoryError(f"not a directory: {root}")
    skipped = {os.path.normpath(os.fspath(path)) for path in skip}
    files = []
    for directory, subdirs, names in os.walk(top, followlinks=False,
                                             onerror=_raise):
        for name in subdirs + names:
            path = os.path.join(directory, name)
            mode = os.lstat(path).st_mode
            if stat.S_ISLNK(mode):
                raise DigestRefused("a symbolic link in the skill directory")
            if stat.S_ISDIR(mode):
                continue
            if not stat.S_ISREG(mode):
                raise DigestRefused("an entry that is not a regular file")
            if path in skipped:
                continue
            files.append((PurePath(os.path.relpath(path, top)).as_posix(), path))
            if len(files) > MAX_FILES:
                raise DigestTooLarge(f"more than {MAX_FILES} files")
    budget = [MAX_BYTES]
    manifest = "".join(f"{relpath}\0{_file_sha256(path, budget)}\n"
                       for relpath, path in sorted(files, key=lambda f: f[0]))
    return hashlib.sha256(manifest.encode("utf-8")).hexdigest()


def _raise(error: OSError) -> None:
    raise error


def git_ignored(repo) -> frozenset:
    """Every untracked path git ignores under the work tree `repo`, absolute
    (the generator's `ignored_paths`). Raises OSError when git fails.

    The one git process in this module, exempted by its exact shape in
    test_issue_workspace_git.py's `test_no_raw_git_process_outside_helper`.
    It keeps the user's global configuration on purpose: the generator
    honors a global `core.excludesFile`, so the same set must. It adds only
    `core.fsmonitor=false` and `core.hooksPath=/dev/null`, which change no
    output and keep the checkout's own configuration from running a command.
    """
    proc = subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf",
         "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
         "-C", str(repo),
         "ls-files", "--others", "--ignored", "--exclude-standard", "-z"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
        check=False)
    if proc.returncode != 0:
        raise OSError("git ls-files --ignored failed")
    top = os.path.realpath(repo)
    return frozenset(os.path.normpath(os.path.join(top, os.fsdecode(name)))
                     for name in proc.stdout.split(b"\0") if name)
