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

`tree_digest` (#562, 2026-11-02) is the same digest of a skill directory as
committed at a revision, read with `git archive` under the generator's
`_GIT_VERBATIM` (`GIT_VERBATIM` here) and extracted with tarfile's `data`
filter, as the generator reads a ref. `skill_relpath`, `content_digests` and
`commit_on_branch` read a registry mirror (a bare, possibly blob-less clone of
a public registry) or a registry checkout, to say whether a recorded digest
was ever the content of a public branch. Every one of them goes through
`git_read`, the module's second git process: no caller `GIT_*`, no global or
system config, no credential helper, no prompt, no hooks, no fsmonitor, and
stderr captured so a failure prints nothing that names a path or a URL.

`test/issues/test_issue_skill_digest.py` holds the test vector, and checks it
against the generator itself when an adam-agentskills checkout is beside this
one. `harness/propagation/arms.digest_skill_dir` is a separate copy and is not
this function.

Stdlib only.
"""

from __future__ import annotations

import fnmatch
import hashlib
import io
import os
import re
import stat
import subprocess
import tarfile
import tempfile
from pathlib import PurePath, PurePosixPath

#: The most regular files a tree may hold before `DigestTooLarge`.
MAX_FILES = 2000
#: The most bytes (50 MiB) read across a tree before `DigestTooLarge`.
MAX_BYTES = 50 * 1024 * 1024
_CHUNK = 1024 * 1024
_SHA256_PREFIX = "sha256:"
#: The generator's `_GIT_VERBATIM` (adam-agentskills
#: scripts/generate_skills_lock.py): no end-of-line translation, so a tree
#: reads byte for byte as committed whatever the machine's settings.
GIT_VERBATIM = ("-c", "core.autocrlf=false", "-c", "core.eol=lf")
#: What `git_read` adds: no fsmonitor or hook command from the repository's
#: own config, and no credential helper (a mirror is public, cloned anonymously).
_GIT_HARDENED = ("-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
                 "-c", "credential.helper=")
_SHA_RE = re.compile(r"[0-9a-f]{40}")


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
        ["git", *GIT_VERBATIM,
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


def _git_env(lazy: bool) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1")
    if not lazy:
        # A blob-less mirror would otherwise ask its promisor remote (the
        # public origin) for an object it lacks; an existence check must
        # answer from the mirror alone.
        env["GIT_NO_LAZY_FETCH"] = "1"
    return env


def git_read(repo, *args: str, lazy: bool = True) -> subprocess.CompletedProcess:
    """One read-only git command in `repo`, hardened (see the module
    docstring), stdout and stderr captured as bytes. Callers check the
    return code; nothing here prints. The second git process in this module,
    exempted by its exact shape in test_issue_workspace_git.py."""
    return subprocess.run(["git", *GIT_VERBATIM, *_GIT_HARDENED, "-C", str(repo), *args],
                          env=_git_env(lazy), stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def _rev(rev: str) -> str:
    if rev != "HEAD" and not _SHA_RE.fullmatch(rev):
        raise ValueError("a revision must be HEAD or a 40-hex commit")
    return rev


def _relpath(relpath: str) -> str:
    parts = PurePosixPath(relpath).parts
    if (not parts or relpath.startswith(("/", "-")) or ".." in parts
            or PurePosixPath(relpath).as_posix() != relpath):
        raise ValueError("not a plain relative path")
    return relpath


def tree_digest(repo, rev: str, relpath: str) -> str:
    """The lock digest of the directory `relpath` as committed at `rev` in
    `repo` (a checkout or a bare mirror): `git archive` of that path alone,
    extracted with the `data` filter into a scratch directory removed on
    return. Raises OSError when git fails or the path is not a directory at
    `rev`, and whatever `lock_digest` raises."""
    rev, relpath = _rev(rev), _relpath(relpath)
    # After `--end-of-options`, git archive reads a `--` as a path, so none.
    proc = git_read(repo, "archive", "--format=tar", "--end-of-options", rev, relpath)
    if proc.returncode != 0:
        raise OSError("git archive failed")
    # A reviewed prefix (test_issue_arm_read_isolation): an eval arm's
    # sandbox denies reads under it, though no arm runs this.
    with tempfile.TemporaryDirectory(prefix="usage-census-tree-digest-") as scratch:
        try:
            with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as archive:
                archive.extractall(scratch, filter="data")
        except tarfile.TarError as exc:
            raise OSError("git archive output could not be read") from exc
        return lock_digest(os.path.join(scratch, *PurePosixPath(relpath).parts))


def skill_relpath(repo, layout: str, name: str, rev: str = "HEAD") -> str:
    """The directory of skill `name` at `rev`, by the registries.yml `layout`
    (its second-to-last `*` is the name, any earlier `*` one path segment),
    when exactly one tracked SKILL.md matches; else ValueError. Unlike the
    explorer's `skill_description` glob, which searches any depth in a
    checkout, this reads the committed tree and the registry's own layout."""
    parts = layout.split("/")
    if len(parts) < 2 or parts[-1] != "SKILL.md" or parts[-2] != "*":
        raise ValueError("a layout must end in */SKILL.md")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", name):
        raise ValueError("not a skill name")
    pattern = parts[:-2] + [name, "SKILL.md"]
    proc = git_read(repo, "ls-tree", "-r", "-z", "--name-only", "--end-of-options", _rev(rev))
    if proc.returncode != 0:
        raise OSError("git ls-tree failed")
    found = []
    for raw in proc.stdout.split(b"\0"):
        path = os.fsdecode(raw).split("/")
        if len(path) == len(pattern) and all(fnmatch.fnmatchcase(seg, pat)
                                             for seg, pat in zip(path, pattern)):
            found.append("/".join(path[:-1]))
    if len(found) != 1:
        raise ValueError("the layout does not name exactly one copy of the skill")
    return found[0]


def content_digests(repo, relpath: str) -> frozenset:
    """Every lock digest the directory `relpath` has had on any branch of
    `repo`: `tree_digest` at each commit `git rev-list --branches -- relpath`
    lists (the commits that changed it). A digest in this set was, at some
    commit, the published content of that path. Raises OSError when git
    fails."""
    relpath = _relpath(relpath)
    proc = git_read(repo, "rev-list", "--branches", "--", relpath)
    if proc.returncode != 0:
        raise OSError("git rev-list failed")
    shas = [line for line in proc.stdout.decode("ascii", "replace").split() if line]
    digests = set()
    for sha in shas:
        try:
            digests.add(tree_digest(repo, sha, relpath))
        except (OSError, ValueError, DigestRefused, DigestTooLarge):
            continue  # a commit that deleted the path, or one we cannot read
    return frozenset(digests)


def commit_on_branch(repo, sha: str) -> bool:
    """True when the commit `sha` is in `repo` itself (no lazy fetch from a
    promisor remote) and some branch there contains it."""
    if not _SHA_RE.fullmatch(sha or ""):
        return False
    if git_read(repo, "cat-file", "-e", f"{sha}^{{commit}}", lazy=False).returncode != 0:
        return False
    proc = git_read(repo, "for-each-ref", "--format=%(refname)", f"--contains={sha}",
                    "refs/heads/", lazy=False)
    return proc.returncode == 0 and bool(proc.stdout.strip())
