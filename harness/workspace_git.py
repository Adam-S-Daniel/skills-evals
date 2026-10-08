"""Harness Git boundary for agent-controlled trees (ADR 0006 addendum).

Repository configuration is data to validate, never configuration to run.
Commands use a private metadata snapshot and constants-only process state.
"""
from __future__ import annotations

import atexit
import hashlib
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import tempfile

GIT = '/usr/bin/git'
DEFAULT_TIMEOUT_S = 10
_OVERRIDES = (
    'core.fsmonitor=false', 'core.hooksPath=/dev/null', 'diff.external=',
    'core.pager=cat', 'core.sshCommand=', 'credential.helper=',
    'protocol.allow=never', 'core.attributesFile=/dev/null',
    'core.editor=true', 'sequence.editor=true', 'core.askPass=',
    'core.gitProxy=', 'core.alternateRefsCommand=', 'interactive.diffFilter=',
    'commit.gpgSign=false', 'tag.gpgSign=false', 'push.gpgSign=false',
    'log.showSignature=false', 'gpg.program=/usr/bin/false', 'maintenance.auto=false',
    'gc.auto=0', 'submodule.recurse=false', 'diff.ignoreSubmodules=all',
    'fetch.recurseSubmodules=false', 'core.untrackedCache=false',
    'user.email=ci@example.com', 'user.name=ci',
)
_CONTEXTS: dict[str, '_Context'] = {}


class WorkspaceGitError(RuntimeError):
    """A named, recordable failure of harness Git on a workspace."""
    name = 'workspace_git_error'

    def __init__(self, reason: str):
        super().__init__(f'{self.name}: {reason}')


class WorkspaceGitTamperedError(WorkspaceGitError):
    """No Git command may run over this workspace's metadata."""
    name = 'workspace_git_tampered'


class WorkspaceGitCollectionError(WorkspaceGitError):
    """Collection could not finish (an unreadable file, a timeout)."""
    name = 'workspace_git_collection_failed'


def _refuse(reason: str) -> None:
    raise WorkspaceGitTamperedError(reason)


def _read_regular(path: Path) -> bytes:
    # O_NOFOLLOW closes the check/open symlink race. Private copies below
    # never hard-link agent files, so later modifications cannot affect Git.
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                _refuse('metadata is not a regular file')
            return stream.read()
    except OSError:
        _refuse('metadata cannot be read as a regular file')


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists() and not path.is_symlink():
        return digest.hexdigest()
    if path.is_symlink():
        _refuse('metadata symlink')
    if path.is_file():
        digest.update(_read_regular(path))
    elif path.is_dir():
        for entry in sorted(path.rglob('*')):
            name = str(entry.relative_to(path)).encode()
            digest.update(len(name).to_bytes(8, 'big'))
            digest.update(name)
            if entry.is_symlink():
                _refuse('metadata symlink')
            if entry.is_file():
                data = _read_regular(entry)
                digest.update(b'F' + len(data).to_bytes(8, 'big') + data)
            elif entry.is_dir():
                digest.update(b'D')
            else:
                _refuse('nonregular metadata')
    else:
        _refuse('nonregular metadata')
    return digest.hexdigest()


def _env(home: Path) -> dict[str, str]:
    return {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'XDG_CONFIG_HOME': str(home),
            'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_ATTR_NOSYSTEM': '1',
            'GIT_TERMINAL_PROMPT': '0', 'GIT_PAGER': 'cat',
            'GIT_OPTIONAL_LOCKS': '0', 'GIT_CEILING_DIRECTORIES': str(home)}


def _invoke(args: list[str], *, cwd: Path, home: Path, timeout: float,
            check: bool = False) -> subprocess.CompletedProcess:
    import guidance
    guidance.check_timeout(timeout, 'workspace_git._invoke(timeout=)',
                           guidance.SINK_TIMEOUT_REMEDY)
    options = [item for option in _OVERRIDES for item in ('-c', option)]
    if not any(arg.startswith('--git-dir=') for arg in args):
        options.append('--git-dir=/dev/null')
    return subprocess.run([GIT, '--no-pager', *options, *args], cwd=cwd,
                          env=_env(home), check=check, capture_output=True,
                          text=True, errors='replace', stdin=subprocess.DEVNULL,
                          timeout=timeout)


def _config(gitdir: Path, private: Path, timeout: float) -> list[tuple[str, str]]:
    raw = _read_regular(gitdir / 'config')
    copy = private / 'untrusted-config'
    copy.write_bytes(raw)
    # Git's own parser handles quoted subsections, multiline values, casing,
    # and duplicate keys. --no-includes prevents even reading include targets.
    result = _invoke(['config', '--no-includes', '--file', str(copy), '-z', '--list'],
                     cwd=private, home=private, timeout=timeout)
    if result.returncode:
        _refuse('invalid repository configuration')
    entries = []
    for record in result.stdout.split('\0'):
        if not record:
            continue
        key, _, value = record.partition('\n')
        lower = key.lower()
        section = lower.split('.', 1)[0]
        executable = (section in {'include', 'includeif', 'filter', 'alias',
                                 'credential', 'gpg', 'pager', 'protocol', 'url',
                                 'hook', 'merge', 'trailer', 'difftool', 'mergetool'}
                      or lower in {'core.fsmonitor', 'core.hookspath', 'core.pager',
                                   'core.sshcommand', 'core.gitproxy', 'core.worktree',
                                   'core.attributesfile', 'core.alternateobjectsdirectory',
                                   'core.alternaterefscommand', 'interactive.difffilter', 'gc.recentobjectshook',
                                   'uploadpack.packobjectshook',
                                   'diff.external', 'extensions.worktreeconfig'}
                      or (section == 'diff' and lower.rsplit('.', 1)[-1]
                          in {'command', 'textconv'})
                      or (section == 'remote' and lower.rsplit('.', 1)[-1]
                          in {'vcs', 'proxy', 'uploadpack', 'receivepack'})
                      or lower in {'core.editor', 'sequence.editor', 'core.askpass',
                                   'core.pager', 'gpg.program', 'ssh.variant'})
        if executable:
            _refuse('executable repository configuration')
        entries.append((key, value))
    return entries


def _metadata(workspace: Path) -> Path:
    entry = workspace / '.git'
    if os.path.lexists(entry):
        return entry
    # Bare fixture repositories are data sources for read-only ref checks.
    # They never masquerade as a missing bookkeeping .git at a sealed root.
    if (workspace / 'HEAD').is_file() and (workspace / 'objects').is_dir():
        return workspace
    return entry


def _validate(workspace: Path, private: Path, timeout: float,
              baseline: tuple | None = None) -> list[tuple[str, str]]:
    gitdir = workspace / '.git' if baseline is not None else _metadata(workspace)
    try:
        identity = gitdir.lstat()
    except OSError:
        _refuse('.git is missing')
    if not stat.S_ISDIR(identity.st_mode):
        _refuse('.git is not a plain directory')
    if identity.st_uid != os.getuid():
        _refuse('.git ownership changed')
    for redirect in ('commondir', 'gitdir', 'config.worktree'):
        if os.path.lexists(gitdir / redirect):
            _refuse('redirected Git metadata')
    for relative in ('objects/info/alternates', 'objects/info/http-alternates'):
        if os.path.lexists(gitdir / relative):
            _refuse('alternate object store')
    if (gitdir / 'info').is_symlink():
        _refuse('metadata info symlink')
    # Attributes are not refused: the private config defines no filter or
    # diff driver (executable driver keys are refused above) and the private
    # info/attributes unsets both, so `diff=python` or `filter=lfs` is inert.
    entries = _config(gitdir, private, timeout)
    if baseline is not None:
        current = (identity.st_dev, identity.st_ino, _digest(gitdir / 'config'),
                   _digest(gitdir / 'info'), _digest(gitdir / 'hooks'))
        if current != baseline:
            _refuse('baseline configuration, info, or hooks changed')
    return entries


def _copy_metadata(source: Path, destination: Path, *, top: bool = True) -> None:
    # Only repository data is copied, with no hooks, configuration, includes,
    # alternates, or hard links. Reject symlinks before traversing directories.
    for entry in source.iterdir():
        if entry.name in {'config', 'config.worktree', 'hooks'} or (top and entry.name in {'info', 'commondir', 'gitdir'}):
            continue
        if entry.is_symlink():
            _refuse('metadata symlink')
        target = destination / entry.name
        if entry.is_dir():
            target.mkdir()
            _copy_metadata(entry, target, top=False)
        else:
            target.write_bytes(_read_regular(entry))
    # Root info/exclude is harmless fixture data and required by nested-repo
    # fixtures. Never copy the executable attributes file.
    exclude = source / 'info' / 'exclude'
    if top and (exclude.exists() or exclude.is_symlink()):
        (destination / 'info').mkdir(exist_ok=True)
        (destination / 'info' / 'exclude').write_bytes(_read_regular(exclude))


def _private_dir() -> Path:
    # Allocated without tempfile.mkdtemp: callers (and their tests) patch
    # that shared function to place the WORKSPACE, and private metadata
    # must never land on the same path.
    base = tempfile.gettempdir()
    for _ in range(100):
        path = Path(base) / ('trusted-git-' + secrets.token_hex(8))
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            continue
        return path
    raise FileExistsError('could not allocate a private Git directory')


class _Context:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.private = _private_dir()
        self.gitdir = self.private / 'metadata'
        self.baseline = None
        self.root_identity: tuple[int, int] | None = None
        self.saved_files: dict[str, bytes] = {}
        self.saved_dirs: list[str] = []

    def remember(self) -> None:
        self.saved_files = {}
        self.saved_dirs = []
        for entry in sorted(self.gitdir.rglob('*')):
            relative = str(entry.relative_to(self.gitdir))
            if entry.is_dir():
                self.saved_dirs.append(relative)
            else:
                self.saved_files[relative] = _read_regular(entry)

    def restore(self, source: '_Context') -> None:
        self.baseline = source.baseline
        self.gitdir.mkdir()
        for relative in source.saved_dirs:
            (self.gitdir / relative).mkdir(parents=True, exist_ok=True)
        for relative, data in source.saved_files.items():
            (self.gitdir / relative).write_bytes(data)

    def snapshot(self, entries: list[tuple[str, str]], timeout: float) -> None:
        self.gitdir.mkdir()
        _copy_metadata(_metadata(self.workspace), self.gitdir)
        bare = 'true' if _metadata(self.workspace) == self.workspace else 'false'
        (self.gitdir / 'config').write_text('[core]\n repositoryformatversion = 0\n bare = ' + bare + '\n')
        for key, value in entries:
            lower = key.lower()
            # Remote names/URLs are read-only scorer data; no rewrites or
            # transport options reach private Git. objectFormat is data too.
            if ((lower.startswith('remote.') and lower.rsplit('.', 1)[-1] == 'url')
                    or lower == 'extensions.objectformat'):
                _invoke(['config', '--file', str(self.gitdir / 'config'), key, value],
                        cwd=self.private, home=self.private, timeout=timeout, check=True)
        info = self.gitdir / 'info'
        info.mkdir(exist_ok=True)
        (info / 'attributes').write_text('* -filter !diff\n')

    def close(self):
        shutil.rmtree(self.private, ignore_errors=True)


def _logical_path(workspace: Path) -> Path:
    """Bind records before following a replaceable directory or parent."""
    return Path(os.path.abspath(os.fspath(workspace)))


def _record(workspace: Path) -> _Context | None:
    logical = _logical_path(workspace)
    # The original path wins even after it becomes a redirect. Canonical
    # aliases support harmless parent aliases such as macOS /tmp.
    return (_CONTEXTS.get(str(logical))
            or _CONTEXTS.get(str(logical.resolve())))


def _check_root(workspace: Path, context: _Context) -> None:
    try:
        identity = _logical_path(workspace).lstat()
    except OSError:
        _refuse('baseline workspace directory is missing')
    if (not stat.S_ISDIR(identity.st_mode)
            or (identity.st_dev, identity.st_ino) != context.root_identity):
        _refuse('baseline workspace directory changed')


def _remove_record(context: _Context) -> None:
    for key in [key for key, record in _CONTEXTS.items() if record is context]:
        del _CONTEXTS[key]
    context.close()


def seal(workspace: Path) -> None:
    """Record the harness-written baseline OUTSIDE the agent's workspace."""
    logical = _logical_path(workspace)
    identity = logical.lstat()
    if not stat.S_ISDIR(identity.st_mode):
        _refuse('workspace is not a plain directory')
    previous = _record(logical)
    if previous:
        _remove_record(previous)
    if not os.path.lexists(logical / '.git'):
        # Nothing harness-made to seal (only when a caller stubs `_git`).
        # Every later run() still validates whatever metadata it finds.
        return
    workspace = logical.resolve()
    context = _Context(workspace)
    try:
        entries = _validate(workspace, context.private, DEFAULT_TIMEOUT_S)
        context.snapshot(entries, DEFAULT_TIMEOUT_S)
        context.root_identity = (identity.st_dev, identity.st_ino)
        identity = (workspace / '.git').lstat()
        context.baseline = (identity.st_dev, identity.st_ino,
                            _digest(workspace / '.git' / 'config'),
                            _digest(workspace / '.git' / 'info'),
                            _digest(workspace / '.git' / 'hooks'))
        context.remember()
        context.close()
        _CONTEXTS[str(logical)] = context
        _CONTEXTS[str(workspace)] = context
    except BaseException:
        context.close()
        raise


def release(workspace: Path) -> None:
    context = _record(workspace)
    if context:
        _remove_record(context)


def _release_all() -> None:
    for context in set(_CONTEXTS.values()):
        context.close()
    _CONTEXTS.clear()


atexit.register(_release_all)


def _stage(context: _Context, command: list[str], timeout: float,
           check: bool) -> subprocess.CompletedProcess:
    """Stage only a private filesystem view, never discover nested config."""
    workspace = context.workspace
    nested: dict[Path, str | None] = {}
    for root, dirs, files in os.walk(workspace, followlinks=False):
        dirs[:] = [name for name in dirs if name != '.git']
        current = Path(root)
        if current == workspace or not os.path.lexists(current / '.git'):
            continue
        dirs[:] = []
        entry = current / '.git'
        if entry.is_file() and not entry.is_symlink():
            # Linked fixture trees are visible in the structural report;
            # neither staging nor reporting follows their redirect file.
            nested[current] = None
            continue
        result = run('rev-parse', '--verify', 'HEAD', cwd=current, timeout=timeout)
        sha = result.stdout.strip()
        if result.returncode == 0 and re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', sha):
            nested[current] = sha
        else:
            nested[current] = None
    stage = context.private / 'stage'
    shutil.rmtree(stage, ignore_errors=True)
    ignored = _ignored(context, timeout)
    _copy_view(workspace, stage, skip=lambda path: path in nested,
               ignored=ignored)
    result = _invoke(['--git-dir=' + str(context.gitdir), '--work-tree=' + str(stage),
                      *command], cwd=context.private, home=context.private,
                     timeout=timeout, check=check)
    if result.returncode == 0:
        for path, sha in nested.items():
            if sha is not None:
                _invoke(['--git-dir=' + str(context.gitdir), '--work-tree=' + str(stage),
                         'update-index', '--add', '--cacheinfo', '160000', sha,
                         str(path.relative_to(workspace))], cwd=context.private,
                        home=context.private, timeout=timeout, check=True)
    return result


def _ignored(context: _Context, timeout: float) -> set[str]:
    """Untracked paths Git would ignore, so staging never copies them.

    Git reads only `.gitignore` data here, against private metadata and
    config; ignored directories come back whole, ending in a slash.
    """
    result = _invoke(['--git-dir=' + str(context.gitdir),
                      '--work-tree=' + str(context.workspace), 'ls-files', '-z',
                      '--others', '--ignored', '--exclude-standard', '--directory'],
                     cwd=context.private, home=context.private, timeout=timeout)
    if result.returncode:
        return set()  # copying more than needed is safe; add re-applies ignores
    return {entry.rstrip('/') for entry in result.stdout.split('\0') if entry}


def _copy_regular(source: Path, target: Path, mode: int) -> None:
    # O_NONBLOCK plus fstat: an entry swapped for a FIFO is never read.
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            return
        with open(target, 'xb') as out:
            shutil.copyfileobj(stream, out)
    os.chmod(target, stat.S_IMODE(mode) | stat.S_IRUSR | stat.S_IWUSR)


def _copy_view(workspace: Path, stage: Path, *, skip, ignored: set[str]) -> None:
    """Copy what `git add -A` could track: directories, regular files and
    symlinks (never followed). FIFOs, sockets and devices are skipped as Git
    skips them; `.git` entries, nested repositories and ignored paths too."""
    stage.mkdir()
    for root, dirs, files in os.walk(workspace, followlinks=False):
        current = Path(root)
        target_root = stage / current.relative_to(workspace)
        keep = []
        for name in sorted(dirs) + sorted(files):
            path = current / name
            relative = path.relative_to(workspace).as_posix()
            if name == '.git' or skip(path) or relative in ignored:
                continue
            mode = path.lstat().st_mode
            target = target_root / name
            if stat.S_ISLNK(mode):
                os.symlink(os.readlink(path), target)
            elif stat.S_ISDIR(mode):
                target.mkdir()
                keep.append(name)
            elif stat.S_ISREG(mode):
                _copy_regular(path, target, mode)
        dirs[:] = [name for name in dirs if name in keep]


def _export_data(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for entry in source.iterdir():
        target = destination / entry.name
        if entry.is_dir():
            _export_data(entry, target)
        else:
            data = _read_regular(entry)
            if target.exists() and _read_regular(target) == data:
                continue
            if os.path.lexists(target):
                target.unlink()
            target.write_bytes(data)


def validate(workspace: Path) -> None:
    """Check the sealed root before scoring, including runs without a judge."""
    stored = _record(workspace)
    if stored is not None:
        _check_root(workspace, stored)
    elif not os.path.lexists(Path(workspace) / '.git'):
        return  # never sealed and no metadata: no harness Git will run here
    private = _private_dir()
    try:
        _validate(Path(workspace).resolve(), private, DEFAULT_TIMEOUT_S,
                  stored.baseline if stored else None)
    finally:
        shutil.rmtree(private, ignore_errors=True)


def run(*args: str, cwd: Path, timeout: float = DEFAULT_TIMEOUT_S,
        check: bool = False) -> subprocess.CompletedProcess:
    """The only harness Git entrypoint, for initialization and collection.

    Sealed roots keep their private baseline refs and staging index. Other
    standalone repositories get a fresh validated snapshot for each read.
    Before sealing, init/add/commit export metadata for the arm to use.
    """
    import guidance
    guidance.check_timeout(timeout, 'workspace_git.run(timeout=)',
                           guidance.SINK_TIMEOUT_REMEDY)
    stored = _record(cwd)
    if stored is not None:
        _check_root(cwd, stored)
    workspace = Path(cwd).resolve()
    temporary = stored is None
    use_baseline = stored is not None and bool(args) and args[0] in {'add', 'diff'}
    context = _Context(workspace)
    if use_baseline:
        context.restore(stored)
    elif stored is not None:
        context.baseline = stored.baseline
    try:
        if args and args[0] == 'init':
            if os.path.lexists(workspace / '.git'):
                entry = workspace / '.git'
                if entry.is_symlink() or not entry.is_dir():
                    _refuse('.git is not a plain directory')
                for name in ('commondir', 'gitdir', 'config.worktree'):
                    if os.path.lexists(entry / name):
                        _refuse('redirected Git metadata')
                if (entry / 'config').exists():
                    _validate(workspace, context.private, timeout)
                elif any(child.name != 'info' for child in entry.iterdir()):
                    _refuse('unexpected incomplete Git metadata')
                else:
                    _digest(entry / 'info')
            context.gitdir.mkdir()
            result = _invoke(['--git-dir=' + str(context.gitdir),
                              '--work-tree=' + str(workspace), 'init', '-q'], cwd=context.private,
                             home=context.private, timeout=timeout, check=check)
            # init records the explicit work-tree path; remove that bootstrap
            # option before exporting ordinary standalone metadata to the arm.
            _invoke(['config', '--file', str(context.gitdir / 'config'),
                     '--unset-all', 'core.worktree'], cwd=context.private,
                    home=context.private, timeout=timeout)
            # Like Git's own re-init, never overwrite existing metadata (a
            # fixture setup may have initialized the root with its own refs).
            def copy_missing(source: str, target: str) -> None:
                if not os.path.lexists(target):
                    shutil.copy2(source, target)
            shutil.copytree(context.gitdir, workspace / '.git', dirs_exist_ok=True,
                            copy_function=copy_missing)
            return result
        entries = _validate(workspace, context.private, timeout, context.baseline)
        if _metadata(workspace) == workspace and (not args or args[0] not in {'rev-parse', 'remote', 'log', 'show', 'worktree'}):
            _refuse('bare metadata supports read-only inspection')
        if not use_baseline:
            context.snapshot(entries, timeout)
        command = list(args)
        if command and command[0] in {'diff', 'log', 'show'}:
            command[1:1] = ['--no-ext-diff', '--no-textconv']
        if command and command[0] == 'add':
            result = _stage(context, command, timeout, check)
        else:
            result = _invoke(['--git-dir=' + str(context.gitdir),
                              '--work-tree=' + str(workspace), *command],
                             cwd=context.private, home=context.private, timeout=timeout, check=check)
        if temporary and command and command[0] in {'add', 'commit'}:
            # Setup happens before the arm. Keep its observable metadata in
            # sync; after seal all writes stay exclusively in private metadata.
            for name in ('objects', 'refs', 'logs'):
                source = context.gitdir / name
                if source.exists():
                    _export_data(source, workspace / '.git' / name)
            for name in ('HEAD', 'index', 'COMMIT_EDITMSG'):
                source = context.gitdir / name
                if source.exists():
                    (workspace / '.git' / name).write_bytes(source.read_bytes())
        # Scorers describe the logical workspace directory, not our private
        # copy. The operation was still executed against only private data.
        if command[:3] == ['rev-parse', '--path-format=absolute', '--git-dir'] and result.returncode == 0:
            result.stdout = str(_metadata(workspace)) + '\n'
        if command[:3] == ['worktree', 'list', '--porcelain'] and result.returncode == 0:
            result.stdout = result.stdout.replace('worktree ' + str(context.gitdir),
                                                  'worktree ' + str(workspace))
        if stored is not None and command and command[0] == 'add':
            context.remember()
            stored.saved_files = context.saved_files
            stored.saved_dirs = context.saved_dirs
        return result
    except subprocess.TimeoutExpired:
        raise WorkspaceGitCollectionError(
            f'git {args[0] if args else ""} exceeded {timeout}s') from None
    except OSError as exc:
        raise WorkspaceGitCollectionError(
            f'{type(exc).__name__} ({exc.strerror or "error"}) while collecting') from None
    finally:
        context.close()
