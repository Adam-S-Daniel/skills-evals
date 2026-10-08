"""Real, remote-free Git execution regressions for issue 343."""
import ast
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'harness'))
import run_eval


class _WorkspaceGitFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='git-exploit-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.env = {'PATH': '/usr/bin:/bin', 'HOME': str(self.root),
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                    'GIT_TERMINAL_PROMPT': '0'}
        self.raw('init', '-q')
        self.raw('config', 'user.name', 'scratch-tree')
        self.raw('config', 'user.email', 'scratch@example.com')
        (self.repo / 'data').write_text('before\n')
        self.raw('add', '-A')
        self.raw('commit', '-qm', 'seed')
        self.assertEqual(self.raw('remote').stdout, '')
        refused = self.raw('push', 'origin', 'HEAD', check=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('does not appear to be a git repository', refused.stderr)
        self.marker = self.root / 'marker'
        self.script = self.root / 'marker.sh'
        self.script.write_text('#!/bin/sh\nprintf marker > ' + shlex.quote(str(self.marker)) + '\n')
        self.script.chmod(0o700)
        self.command = '/bin/sh ' + shlex.quote(str(self.script))
        (self.repo / 'data').write_text('after\n')

    def raw(self, *args, check=True):
        return subprocess.run(['/usr/bin/git', *args], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, check=check, timeout=10)

    def old_git(self, *args):
        # The pre-#343 `run_eval._git` argv, verbatim: repository discovery
        # and repository config are allowed, so the marker is a live exploit.
        email, name = run_eval.SEED_COMMIT_IDENTITY
        return subprocess.run(['git', '-c', f'user.email={email}',
                               '-c', f'user.name={name}', *args],
                              cwd=self.repo, env=self.env, capture_output=True,
                              text=True, check=False, timeout=10)

    def verify(self, *args):
        self.old_git(*args)
        self.assertTrue(self.marker.exists(), 'old Git path did not execute the marker')
        self.marker.unlink()
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._git(*args, cwd=self.repo)
        self.assertFalse(self.marker.exists(), 'trusted Git executed workspace code')



class WorkspaceGitExploitTests(_WorkspaceGitFixture, unittest.TestCase):
    def test_fsmonitor(self):
        self.raw('config', 'core.fsmonitor', self.command)
        self.verify('status', '--short')

    def test_hooks_path(self):
        hooks = self.root / 'hooks'
        hooks.mkdir()
        shutil.copyfile(self.script, hooks / 'pre-commit')
        (hooks / 'pre-commit').chmod(0o700)
        self.raw('config', 'core.hooksPath', str(hooks))
        self.verify('commit', '--allow-empty', '-qm', 'probe')

    def test_external_diff(self):
        self.raw('config', 'diff.external', self.command)
        self.verify('diff')

    def test_filter_attributes(self):
        self.raw('config', 'filter.marker.clean', self.command)
        (self.repo / '.gitattributes').write_text('data filter=marker\n')
        self.verify('add', '-A')

    def test_include(self):
        included = self.root / 'included'
        included.write_text('[core]\n fsmonitor = ' + self.command + '\n')
        self.raw('config', 'include.path', str(included))
        self.verify('status', '--short')

    def test_commondir(self):
        target = self.root / 'common'
        shutil.copytree(self.repo / '.git', target)
        subprocess.run(['/usr/bin/git', 'config', '--file', str(target / 'config'),
                        'core.fsmonitor', self.command], env=self.env, check=True, timeout=10)
        (self.repo / '.git' / 'commondir').write_text(str(target) + '\n')
        self.verify('status', '--short')

    def test_gitdir_file(self):
        target = self.root / 'redirect'
        self.raw('config', 'core.fsmonitor', self.command)
        shutil.move(self.repo / '.git', target)
        (self.repo / '.git').write_text('gitdir: ' + str(target) + '\n')
        self.verify('status', '--short')


class WorkspaceGitOverrideTests(_WorkspaceGitFixture, unittest.TestCase):
    """The -c overrides win over repository-local config even when validation
    is bypassed and Git is pointed straight at the planted metadata."""

    def direct(self, *args):
        import workspace_git
        return workspace_git._invoke(
            ['--git-dir=' + str(self.repo / '.git'),
             '--work-tree=' + str(self.repo), *args],
            cwd=self.repo, home=self.root, timeout=10)

    def test_every_override_wins_over_local_config(self):
        import workspace_git
        for option in workspace_git._OVERRIDES:
            key, _, value = option.partition('=')
            with self.subTest(key=key):
                self.raw('config', key, self.command)
                got = self.direct('config', '--get', key)
                self.assertEqual(got.stdout.rstrip('\n'), value, got.stderr)
                self.raw('config', '--unset-all', key)

    def test_identity_matches_seed_commit_identity(self):
        import workspace_git
        email, name = run_eval.SEED_COMMIT_IDENTITY
        self.assertIn(f'user.email={email}', workspace_git._OVERRIDES)
        self.assertIn(f'user.name={name}', workspace_git._OVERRIDES)

    def assert_old_runs_direct_does_not(self, *args):
        self.old_git(*args)
        self.assertTrue(self.marker.exists(), 'old Git path did not execute the marker')
        self.marker.unlink()
        self.direct(*args)
        self.assertFalse(self.marker.exists(), 'an override lost to local config')

    def test_fsmonitor_override(self):
        self.raw('config', 'core.fsmonitor', self.command)
        self.assert_old_runs_direct_does_not('status', '--short')

    def test_hooks_path_override(self):
        hooks = self.root / 'hooks'
        hooks.mkdir()
        shutil.copyfile(self.script, hooks / 'pre-commit')
        (hooks / 'pre-commit').chmod(0o700)
        self.raw('config', 'core.hooksPath', str(hooks))
        self.assert_old_runs_direct_does_not('commit', '--allow-empty', '-qm', 'probe')

    def test_default_hooks_dir_override(self):
        hook = self.repo / '.git' / 'hooks' / 'pre-commit'
        shutil.copyfile(self.script, hook)
        hook.chmod(0o700)
        self.assert_old_runs_direct_does_not('commit', '--allow-empty', '-qm', 'probe')

    def test_external_diff_override(self):
        self.raw('config', 'diff.external', self.command)
        self.assert_old_runs_direct_does_not('diff')

    def test_editor_override(self):
        self.raw('config', 'core.editor', self.command)
        self.assert_old_runs_direct_does_not('commit', '--allow-empty')

    def test_textconv_flag(self):
        self.raw('config', 'diff.marker.textconv', self.command)
        (self.repo / '.gitattributes').write_text('data diff=marker\n')
        self.old_git('diff')
        self.assertTrue(self.marker.exists(), 'old Git path did not execute the marker')
        self.marker.unlink()
        self.direct('diff', '--no-ext-diff', '--no-textconv')
        self.assertFalse(self.marker.exists())

    def test_hooks_dir_change_after_seal_refuses(self):
        import workspace_git
        workspace_git.seal(self.repo)
        self.addCleanup(workspace_git.release, self.repo)
        hook = self.repo / '.git' / 'hooks' / 'pre-commit'
        shutil.copyfile(self.script, hook)
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._build_judge_diff(self.repo)
        self.assertFalse(self.marker.exists())


class WorkspaceGitBoundaryTests(_WorkspaceGitFixture, unittest.TestCase):
    def test_git_symlink(self):
        target = self.root / 'redirect'
        shutil.move(self.repo / '.git', target)
        (self.repo / '.git').symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._git('status', cwd=self.repo)

    def test_builtin_attributes_are_data_not_refusals(self):
        # Nothing in the private config defines a driver, and the private
        # info/attributes unsets filter and diff, so built-in or undefined
        # drivers an agent might write are inert rather than a failed trial.
        (self.repo / '.gitattributes').write_text(
            '*.py diff=python\n*.bin filter=lfs diff=lfs merge=lfs -text\n'
            '[attr]evil filter=marker\ndata evil diff=marker\n')
        (self.repo / '.git' / 'info' / 'attributes').write_text('data diff=driver\n')
        diff = run_eval._build_judge_diff(self.repo)
        self.assertIn('+after', diff)
        self.assertFalse(self.marker.exists())

    def test_attribute_driver_defined_in_config_still_refuses(self):
        self.raw('config', 'filter.marker.clean', self.command)
        (self.repo / '.gitattributes').write_text('[attr]evil filter=marker\ndata evil\n')
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._git('add', '-A', cwd=self.repo)
        self.assertFalse(self.marker.exists())

    def test_textconv(self):
        self.raw('config', 'diff.marker.textconv', self.command)
        (self.repo / '.gitattributes').write_text('data diff=marker\n')
        self.verify('diff', '--textconv')

    def test_other_executable_keys(self):
        keys = ['core.sshCommand', 'core.pager', 'credential.helper',
                'core.alternateRefsCommand', 'interactive.diffFilter',
                'difftool.marker.cmd', 'mergetool.marker.cmd', 'merge.marker.driver',
                'uploadpack.packObjectsHook', 'gpg.ssh.defaultKeyCommand',
                'gc.recentObjectsHook', 'hook.marker.command', 'trailer.marker.command']
        for key in keys:
            with self.subTest(key=key):
                self.raw('config', key, self.command)
                with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
                    run_eval._git('status', cwd=self.repo)
                self.raw('config', '--unset', key)
        self.assertFalse(self.marker.exists())

    def test_host_git_environment_does_not_execute(self):
        from unittest import mock
        malicious = self.root / 'global'
        malicious.write_text('[core]\n fsmonitor = ' + self.command + '\n')
        hostile = {'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'core.fsmonitor',
                   'GIT_CONFIG_VALUE_0': self.command, 'GIT_CONFIG_GLOBAL': str(malicious),
                   'GIT_CONFIG_SYSTEM': str(malicious), 'GIT_CONFIG': str(malicious),
                   'GIT_DIR': str(self.root / 'elsewhere'), 'GIT_WORK_TREE': str(self.root),
                   'GIT_EXTERNAL_DIFF': self.command, 'GIT_PAGER': self.command,
                   'GIT_SSH_COMMAND': self.command, 'GIT_EXEC_PATH': str(self.root),
                   'PATH': str(self.root), 'HOME': str(self.root)}
        with mock.patch.dict(os.environ, hostile):
            run_eval._git('status', '--short', cwd=self.repo)
            run_eval._git('diff', cwd=self.repo)
        self.assertFalse(self.marker.exists())

    def test_alternates_and_metadata_symlinks(self):
        cases = ['commondir', 'gitdir', 'config.worktree', 'objects/info/alternates']
        for name in cases:
            with self.subTest(name=name):
                path = self.repo / '.git' / name
                path.parent.mkdir(exist_ok=True, parents=True)
                path.write_text(str(self.root) + '\n')
                with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
                    run_eval._git('status', cwd=self.repo)
                path.unlink()
        info = self.repo / '.git' / 'info'
        target = self.root / 'info'
        shutil.move(info, target)
        info.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._git('status', cwd=self.repo)

    def test_sealed_baseline_and_staging_are_outside_workspace(self):
        import workspace_git
        workspace_git.seal(self.repo)
        self.addCleanup(workspace_git.release, self.repo)
        record = workspace_git._CONTEXTS[str(self.repo.resolve())]
        self.assertFalse(record.private.exists(), 'baseline metadata remained writable by the arm')
        before = (self.repo / '.git' / 'index').read_bytes()
        diff = run_eval._build_judge_diff(self.repo)
        self.assertIn('+after', diff)
        self.assertEqual((self.repo / '.git' / 'index').read_bytes(), before)
        self.assertFalse(record.private.exists())

    def test_baseline_benign_config_edit_refuses(self):
        import workspace_git
        workspace_git.seal(self.repo)
        self.addCleanup(workspace_git.release, self.repo)
        self.raw('config', 'user.name', 'changed')
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._build_judge_diff(self.repo)

    def test_baseline_info_edit_and_added_file_refuse(self):
        import workspace_git
        workspace_git.seal(self.repo)
        self.addCleanup(workspace_git.release, self.repo)
        path = self.repo / '.git' / 'info' / 'new-data'
        path.write_text('benign\n')
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._git('diff', cwd=self.repo)
        path.unlink()
        (self.repo / '.git' / 'info' / 'exclude').write_text('changed\n')
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._git('diff', cwd=self.repo)

    def test_baseline_git_directory_replaced(self):
        import workspace_git
        workspace_git.seal(self.repo)
        self.addCleanup(workspace_git.release, self.repo)
        original = self.root / 'original'
        shutil.move(self.repo / '.git', original)
        shutil.copytree(original, self.repo / '.git')
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._git('diff', cwd=self.repo)

    def test_nested_tamper_rejected_before_root_add(self):
        nested = self.repo / 'nested'
        nested.mkdir()
        subprocess.run(['/usr/bin/git', 'init', '-q', str(nested)], env=self.env, check=True, timeout=10)
        subprocess.run(['/usr/bin/git', '-C', str(nested), 'config', 'core.fsmonitor', self.command],
                       env=self.env, check=True, timeout=10)
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._build_judge_diff(self.repo)
        self.assertFalse(self.marker.exists())

    def test_scorer_routes_refuse_config(self):
        from scorers import objective
        self.raw('config', 'core.fsmonitor', self.command)
        checks = [lambda: objective.git_ref_unchanged(str(self.root), [], path='repo',
                                                     ref='HEAD', expected='bad'),
                  lambda: objective.git_remote_url_is(str(self.root), [], path='repo',
                                                      remote='origin', expected_path='other'),
                  lambda: objective.git_worktree_list_matches(str(self.root), [], path='repo',
                                                             expected_names=['repo'])]
        for check in checks:
            passed, detail = check()
            self.assertFalse(passed)
            self.assertIn('workspace_git_tampered', detail)
        self.assertFalse(self.marker.exists())

    def test_bare_ref_and_worktree_inventory_are_data(self):
        from scorers import objective
        sha = self.raw('rev-parse', 'HEAD').stdout.strip()
        bare = self.root / 'bare'
        subprocess.run(['/usr/bin/git', 'clone', '--bare', '-q', str(self.repo), str(bare)],
                       env=self.env, check=True, timeout=10)
        subprocess.run(['/usr/bin/git', '-C', str(bare), 'remote', 'remove', 'origin'],
                       env=self.env, check=True, timeout=10)
        passed, detail = objective.git_ref_unchanged(str(self.root), [], path='bare', ref='HEAD', expected=sha)
        self.assertTrue(passed, detail)
        satellite = self.root / 'satellite'
        self.raw('worktree', 'add', '--detach', '-q', str(satellite))
        passed, detail = objective.git_worktree_list_matches(str(self.root), [], path='repo',
                                                            expected_names=['repo', 'satellite'])
        self.assertTrue(passed, detail)
        with self.assertRaisesRegex(RuntimeError, 'workspace_git_tampered'):
            run_eval._git('status', cwd=satellite)

    def test_no_raw_git_process_outside_helper(self):
        harness = Path(run_eval.__file__).parent
        # Modules whose git calls only ever read a trusted, harness-supplied
        # checkout, never an agent workspace: context.py resolves an ADR 0012
        # context from --context-repo clones through git cat-file/ls-tree.
        trusted_repo_readers = {'workspace_git.py', 'context.py'}
        for path in harness.rglob('*.py'):
            if path.name in trusted_repo_readers:
                continue
            tree = ast.parse(path.read_text())
            bindings = {}
            imported_sinks = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            bindings[target.id] = node.value
                elif isinstance(node, ast.ImportFrom) and node.module == 'subprocess':
                    imported_sinks.update(alias.asname or alias.name for alias in node.names
                                          if alias.name in {'run', 'Popen', 'check_call', 'check_output'})
            def resolve(node, seen=frozenset()):
                if isinstance(node, ast.Name) and node.id in bindings and node.id not in seen:
                    return resolve(bindings[node.id], seen | {node.id})
                return node
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                sink = ((isinstance(node.func, ast.Attribute)
                         and node.func.attr in {'run', 'Popen', 'check_call', 'check_output'})
                        or (isinstance(node.func, ast.Name) and node.func.id in imported_sinks))
                if not sink:
                    continue
                argv = resolve(node.args[0]) if node.args else None
                if argv is None:
                    argv = next((resolve(item.value) for item in node.keywords
                                 if item.arg == 'args'), None)
                if isinstance(argv, (ast.List, ast.Tuple)) and argv.elts:
                    first = resolve(argv.elts[0])
                    self.assertFalse(isinstance(first, ast.Constant)
                                     and first.value in {'git', '/usr/bin/git'}, str(path))

    def test_skill_arm_records_named_error_and_skips_judge(self):
        import argparse
        from unittest import mock
        seed = self.root / 'seed'
        seed.mkdir()
        (seed / 'data').write_text('seed\n')
        fixture = {'skill': 'test', 'prompt': 'test', 'model': 'test-model',
                   'judge': {'model': 'test-judge'}, 'judge_rubric': 'test'}
        args = argparse.Namespace(model=None, timeout=30, no_judge=False,
                                  results_dir=self.root / 'results')
        def arm(workspace, prompt, config):
            with open(workspace / '.git' / 'config', 'a') as stream:
                stream.write('\n[core]\n fsmonitor = ' + self.command + '\n')
            return {'transcript': 'done', 'raw': {}, 'usage': {}, 'cost_usd': 0,
                    'num_turns': 1, 'duration_ms': 1}
        with mock.patch.object(run_eval, 'run_agent', arm), \
                mock.patch.object(run_eval.judge, 'score') as judge:
            result = run_eval._run_arm('without_skill', fixture, seed, {}, args, 'test')
        self.assertEqual(result['error']['type'], 'workspace_git_tampered')
        self.assertIsNone(result['judge'])
        self.assertIsNone(result['objective_checks'])
        judge.assert_not_called()
        self.assertFalse(self.marker.exists())

    def test_guidance_arm_records_named_error_without_judge(self):
        import argparse
        from unittest import mock
        seed = self.root / 'seed'
        seed.mkdir()
        (seed / 'data').write_text('seed\n')
        fixture = {'prompt': 'test', 'model': 'test-model'}
        ctx = {'delivery': 'user', 'decoys': {}, 'token': 'token',
               'guidance_dir': self.root, 'row': {}, 'section': 'test', 'key': 'test'}
        arm = {'name': 'test', 'mode': 'none', 'objective_checks': []}
        args = argparse.Namespace(model=None, timeout=30, no_judge=True,
                                  results_dir=self.root / 'results')
        def agent(workspace, prompt, config):
            (workspace / '.git' / 'info' / 'extra').write_text('changed\n')
            return {'transcript': 'done', 'raw': {}, 'usage': {}, 'cost_usd': 0,
                    'num_turns': 1, 'duration_ms': 1}
        delivery = {'bytes': 0, 'verdict': 'test', 'installed': True, 'returncode': 0}
        with mock.patch.object(run_eval.guidance, 'assemble', return_value=''), \
                mock.patch.object(run_eval.guidance, 'deliver', return_value=delivery), \
                mock.patch.object(run_eval.guidance, 'run_guard', return_value={'ok': True}), \
                mock.patch.object(run_eval, 'run_agent', agent), \
                mock.patch.object(run_eval.judge, 'score') as judge:
            result = run_eval._run_guidance_arm(arm, fixture, seed, ctx, args, 'test')
        self.assertEqual(result['error']['type'], 'workspace_git_tampered')
        self.assertIsNone(result['judge'])
        self.assertIsNone(result['objective_checks'])
        judge.assert_not_called()


class WorkspaceGitCollectionTests(_WorkspaceGitFixture, unittest.TestCase):
    """Collection failures are a recorded trial error, never a crash."""

    def sealed(self):
        import workspace_git
        workspace_git.seal(self.repo)
        self.addCleanup(workspace_git.release, self.repo)

    def test_unix_socket_is_skipped_like_git_add(self):
        import socket
        self.sealed()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(server.close)
        server.bind(str(self.repo / 'app.sock'))
        diff = run_eval._build_judge_diff(self.repo)
        self.assertIn('+after', diff)
        self.assertNotIn('app.sock', diff)

    def test_fifo_is_skipped_like_git_add(self):
        self.sealed()
        os.mkfifo(self.repo / 'pipe')
        diff = run_eval._build_judge_diff(self.repo)
        self.assertIn('+after', diff)
        self.assertNotIn('pipe', diff)

    def test_symlink_and_executable_bit_survive_staging(self):
        self.sealed()
        (self.repo / 'link').symlink_to('data')
        tool = self.repo / 'tool.sh'
        tool.write_text('#!/bin/sh\n')
        tool.chmod(0o755)
        diff = run_eval._build_judge_diff(self.repo)
        self.assertIn('new file mode 120000', diff)
        self.assertIn('new file mode 100755', diff)

    def test_ignored_trees_are_not_copied_or_staged(self):
        from unittest import mock
        import workspace_git
        (self.repo / '.gitignore').write_text('node_modules/\n*.log\n')
        self.sealed()
        (self.repo / 'node_modules' / 'pkg').mkdir(parents=True)
        (self.repo / 'node_modules' / 'pkg' / 'index.js').write_text('x\n')
        (self.repo / 'debug.log').write_text('x\n')
        copied = []
        real = workspace_git._copy_regular
        def spy(source, target, mode, *remaining):
            copied.append(Path(source).relative_to(self.repo).as_posix())
            return real(source, target, mode, *remaining)
        with mock.patch.object(workspace_git, '_copy_regular', spy):
            diff = run_eval._build_judge_diff(self.repo)
        self.assertIn('+after', diff)
        self.assertNotIn('node_modules/pkg', diff)
        self.assertNotIn('debug.log', diff)
        self.assertFalse([path for path in copied
                          if path.startswith('node_modules/') or path == 'debug.log'],
                         copied)

    def test_unreadable_file_is_a_named_collection_error(self):
        import workspace_git
        self.sealed()
        locked = self.repo / 'locked'
        locked.write_text('x\n')
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o600)
        if os.access(locked, os.R_OK):
            self.skipTest('running as a user that bypasses file permissions')
        with self.assertRaisesRegex(workspace_git.WorkspaceGitError,
                                    'workspace_git_collection_failed'):
            run_eval._build_judge_diff(self.repo)

    def test_slow_add_is_a_named_collection_error(self):
        from unittest import mock
        import workspace_git
        self.sealed()
        slow = subprocess.TimeoutExpired(['git', 'add'], 1)
        with mock.patch.object(workspace_git, '_stage', side_effect=slow):
            with self.assertRaisesRegex(workspace_git.WorkspaceGitError,
                                        'workspace_git_collection_failed'):
                run_eval._build_judge_diff(self.repo)

    def test_bookkeeping_timeout_is_the_sink_ceiling(self):
        import guidance
        from unittest import mock
        import workspace_git
        with mock.patch.object(workspace_git, 'run') as run:
            run_eval._git('status', cwd=self.repo)
        self.assertEqual(run.call_args.kwargs['timeout'], guidance.MAX_TIMEOUT_S)

    def test_skill_arm_records_a_collection_failure(self):
        import argparse
        from unittest import mock
        import workspace_git
        seed = self.root / 'seed'
        seed.mkdir()
        (seed / 'data').write_text('seed\n')
        fixture = {'skill': 'test', 'prompt': 'test', 'model': 'test-model',
                   'judge': {'model': 'test-judge'}, 'judge_rubric': 'test'}
        args = argparse.Namespace(model=None, timeout=30, no_judge=False,
                                  results_dir=self.root / 'results')
        slow = mock.patch.object(workspace_git, '_stage',
                                 side_effect=subprocess.TimeoutExpired(['git', 'add'], 1))
        def arm(workspace, prompt, config):
            # The seed commit is real; only the post-arm add is slow.
            slow.start()
            self.addCleanup(slow.stop)
            return {'transcript': 'done', 'raw': {}, 'usage': {}, 'cost_usd': 0,
                    'num_turns': 1, 'duration_ms': 1}
        with mock.patch.object(run_eval, 'run_agent', arm), \
                mock.patch.object(run_eval.judge, 'score') as judge:
            result = run_eval._run_arm('without_skill', fixture, seed, {}, args, 'test')
        self.assertEqual(result['error']['type'], 'workspace_git_collection_failed')
        self.assertIsNone(result['judge'])
        judge.assert_not_called()
        summaries = list((self.root / 'results').rglob('*.json'))
        self.assertTrue(summaries, 'no summary was written')

    def test_skill_arm_with_a_fifo_is_scored(self):
        import argparse
        from unittest import mock
        seed = self.root / 'seed'
        seed.mkdir()
        (seed / 'data').write_text('seed\n')
        fixture = {'skill': 'test', 'prompt': 'test', 'model': 'test-model',
                   'judge': {'model': 'test-judge'}, 'judge_rubric': 'test'}
        args = argparse.Namespace(model=None, timeout=30, no_judge=False,
                                  results_dir=self.root / 'results')
        def arm(workspace, prompt, config):
            os.mkfifo(workspace / 'pipe')
            (workspace / 'data').write_text('changed\n')
            return {'transcript': 'done', 'raw': {}, 'usage': {}, 'cost_usd': 0,
                    'num_turns': 1, 'duration_ms': 1}
        with mock.patch.object(run_eval, 'run_agent', arm), \
                mock.patch.object(run_eval.judge, 'score',
                                  return_value={'overall': 5.0, 'dimensions': []}) as judge:
            result = run_eval._run_arm('without_skill', fixture, seed, {}, args, 'test')
        self.assertIsNone(result['error'])
        judge.assert_called_once()
        self.assertIn('+changed', judge.call_args.args[2])


class WorkspaceGitHostileTreeTests(_WorkspaceGitFixture, unittest.TestCase):
    """Issue 350: trees that crash, hang or flood collection are named errors."""

    def run_arm(self, mutate, during=None, expected='workspace_git_collection_failed'):
        """Drive `_run_arm` with `mutate(workspace)` as the agent's work and
        `during` (a started-in-the-arm patch) armed only after the seed commit."""
        import argparse
        from unittest import mock
        seed = self.root / 'seed'
        seed.mkdir()
        (seed / 'data').write_text('seed\n')
        fixture = {'skill': 'test', 'prompt': 'test', 'model': 'test-model',
                   'judge': {'model': 'test-judge'}, 'judge_rubric': 'test'}
        args = argparse.Namespace(model=None, timeout=30, no_judge=False,
                                  results_dir=self.root / 'results')
        started = []
        def arm(workspace, prompt, config):
            mutate(workspace)
            if during is not None:
                during.start()
                started.append(during)
            return {'transcript': 'done', 'raw': {}, 'usage': {}, 'cost_usd': 0,
                    'num_turns': 1, 'duration_ms': 1}
        try:
            with mock.patch.object(run_eval, 'run_agent', arm), \
                    mock.patch.object(run_eval.judge, 'score') as judge:
                result = run_eval._run_arm('without_skill', fixture, seed, {}, args, 'test')
        finally:
            for patch in started:
                patch.stop()
        judge.assert_not_called()
        self.assertIsNone(result['judge'])
        self.assertTrue(list((self.root / 'results').rglob('*.json')),
                        'no summary was written')
        self.assertEqual(result['error']['type'], expected, result['error'])
        return result

    def test_bogus_working_tree_encoding_is_a_named_collection_error(self):
        def mutate(workspace):
            (workspace / '.gitattributes').write_text(
                'data working-tree-encoding=BOGUS-CHARSET\n')
            (workspace / 'data').write_text('changed\n')
        result = self.run_arm(mutate)
        self.assertIn('git add', result['error']['detail'])

    def test_utf16_without_bom_is_a_named_collection_error(self):
        def mutate(workspace):
            (workspace / '.gitattributes').write_text('data working-tree-encoding=UTF-16\n')
            (workspace / 'data').write_bytes(b'abc')
        self.run_arm(mutate)

    def _no_work_tree_git(self):
        # A FIFO opened by Git blocks until the sink ceiling. Rather than
        # wait on a clock, fail the moment Git is pointed at any work tree
        # after the arm: refusal must come before Git runs at all.
        from unittest import mock
        import workspace_git
        real = workspace_git._invoke
        def guard(args, **kwargs):
            if any(arg.startswith('--work-tree=') for arg in args):
                raise AssertionError('Git ran over a tree holding a FIFO: ' + ' '.join(args))
            return real(args, **kwargs)
        return mock.patch.object(workspace_git, '_invoke', guard)

    def test_fifo_special_files_are_refused_before_git_runs(self):
        # `.git/info/exclude` is never opened by Git in the workspace: its
        # non-blocking private copy refuses it as a baseline change.
        for relative, expected in (('.gitignore', 'collection_failed'),
                                   ('.gitattributes', 'collection_failed'),
                                   ('sub/.gitignore', 'collection_failed'),
                                   ('sub/.gitattributes', 'collection_failed'),
                                   ('.git/info/exclude', 'tampered')):
            with self.subTest(relative=relative):
                shutil.rmtree(self.root / 'seed', ignore_errors=True)
                shutil.rmtree(self.root / 'results', ignore_errors=True)
                def mutate(workspace, relative=relative):
                    target = workspace / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if os.path.lexists(target):
                        target.unlink()
                    os.mkfifo(target)
                result = self.run_arm(mutate, during=self._no_work_tree_git(),
                                      expected='workspace_git_' + expected)
                self.assertRegex(result['error']['detail'],
                                 'not a regular file|nonregular metadata')

    def test_fifo_gitignore_is_refused_by_the_helper(self):
        import workspace_git
        os.mkfifo(self.repo / '.gitignore')
        with self._no_work_tree_git():
            for command in (('add', '-A'), ('status',), ('diff',), ('log', '-p')):
                with self.subTest(command=command):
                    with self.assertRaisesRegex(workspace_git.WorkspaceGitError,
                                                'workspace_git_collection_failed'):
                        workspace_git.run(*command, cwd=self.repo)

    def test_sparse_file_over_the_byte_cap_is_a_named_collection_error(self):
        import workspace_git
        copied = []
        from unittest import mock
        real = workspace_git._copy_regular
        def spy(source, target, mode, *remaining):
            copied.append(Path(source).name)
            return real(source, target, mode, *remaining)
        def mutate(workspace):
            with open(workspace / 'huge.bin', 'wb') as stream:
                stream.truncate(workspace_git.MAX_STAGED_BYTES + 1)
            # Sparse: the cap is checked on apparent size, never written out.
            self.assertLess(os.stat(workspace / 'huge.bin').st_blocks * 512,
                            1024 * 1024)
        result = self.run_arm(mutate, during=mock.patch.object(
            workspace_git, '_copy_regular', spy))
        self.assertIn('bytes', result['error']['detail'])
        self.assertNotIn('huge.bin', copied)

    def test_file_count_over_the_cap_is_a_named_collection_error(self):
        from unittest import mock
        import workspace_git
        def mutate(workspace):
            for index in range(5):
                (workspace / f'file{index}').write_text('x\n')
        result = self.run_arm(mutate, during=mock.patch.object(
            workspace_git, 'MAX_STAGED_FILES', 3))
        self.assertIn('files', result['error']['detail'])

    def test_caps_are_generous(self):
        import workspace_git
        self.assertGreaterEqual(workspace_git.MAX_STAGED_BYTES, 2 * 1024 ** 3)
        self.assertGreaterEqual(workspace_git.MAX_STAGED_FILES, 200_000)


class WorkspaceGitGeneratedConfigTests(_WorkspaceGitFixture, unittest.TestCase):
    """Only the generated private config runs, never the workspace's."""

    def test_observable_workspace_keys_have_no_effect(self):
        import workspace_git
        excludes = self.root / 'excludes'
        excludes.write_text('hidden.txt\n')
        self.raw('config', 'core.excludesFile', str(excludes))
        self.raw('config', 'status.showUntrackedFiles', 'no')
        (self.repo / 'hidden.txt').write_text('x\n')
        # Red: Git honoring the workspace config hides the file.
        self.assertEqual(self.old_git('status', '--porcelain').stdout.strip(), 'M data')
        status = workspace_git.run('status', '--porcelain', cwd=self.repo)
        self.assertIn('?? hidden.txt', status.stdout)
        workspace_git.seal(self.repo)
        self.addCleanup(workspace_git.release, self.repo)
        self.assertIn('hidden.txt', run_eval._build_judge_diff(self.repo))


class WorkspaceGitLayoutTests(unittest.TestCase):
    def test_sealed_root_symlink_cannot_bypass_baseline_binding(self):
        import workspace_git
        with tempfile.TemporaryDirectory(prefix='git-layout-') as temporary:
            root = Path(temporary)
            repo = root / 'repo'
            repo.mkdir()
            run_eval._git('init', '-q', cwd=repo)
            run_eval._git('commit', '--allow-empty', '-qm', 'seed', cwd=repo)
            workspace_git.seal(repo)
            self.addCleanup(workspace_git.release, repo)
            original = root / 'original'
            repo.rename(original)
            repo.symlink_to(original, target_is_directory=True)
            with (original / '.git' / 'config').open('a') as stream:
                stream.write('\n[user]\n name = changed\n')
            with self.assertRaisesRegex(workspace_git.WorkspaceGitTamperedError,
                                        'workspace_git_tampered'):
                run_eval._git('diff', cwd=repo)
            with self.assertRaisesRegex(workspace_git.WorkspaceGitTamperedError,
                                        'workspace_git_tampered'):
                workspace_git.validate(repo)
            workspace_git.release(repo)
            self.assertNotIn(str(repo), workspace_git._CONTEXTS)
            self.assertNotIn(str(original), workspace_git._CONTEXTS)

    def test_unchanged_parent_alias_uses_the_same_baseline(self):
        import workspace_git
        with tempfile.TemporaryDirectory(prefix='git-layout-') as temporary:
            root = Path(temporary)
            parent = root / 'parent'
            parent.mkdir()
            alias = root / 'alias'
            alias.symlink_to(parent, target_is_directory=True)
            repo = parent / 'repo'
            repo.mkdir()
            run_eval._git('init', '-q', cwd=repo)
            run_eval._git('commit', '--allow-empty', '-qm', 'seed', cwd=repo)
            workspace_git.seal(alias / 'repo')
            self.addCleanup(workspace_git.release, alias / 'repo')
            workspace_git.validate(repo)
            workspace_git.validate(alias / 'repo')
            run_eval._git('diff', cwd=alias / 'repo')
            workspace_git.release(alias / 'repo')
            self.assertNotIn(str(repo), workspace_git._CONTEXTS)
            self.assertNotIn(str(alias / 'repo'), workspace_git._CONTEXTS)


class WorkspaceGitFollowupTests(_WorkspaceGitFixture, unittest.TestCase):
    """Issue 350 follow-ups: enforce bounds while copying stable Git data."""

    def _growing_stream(self, fd, *, payload_bytes):
        # Finite fake: every bounded read sees newly appended bytes, but EOF
        # remains reachable even if the production copier ignores its budget.
        class Growing:
            def __init__(self):
                self.left = payload_bytes
                self.read_sizes = []
            def __enter__(self):
                return self
            def __exit__(self, *args):
                os.close(fd)
            def fileno(self):
                return fd
            def read(self, size=-1):
                self.read_sizes.append(size)
                count = self.left if size < 0 else min(size, self.left)
                self.left -= count
                return b'x' * count
        return Growing()

    def test_growing_regular_file_is_bounded_during_copy(self):
        from unittest import mock
        import workspace_git
        source_root = self.root / 'source'
        source_root.mkdir()
        source = source_root / 'growing'
        source.write_bytes(b'x')
        streams = []
        def growing(fd, mode):
            stream = self._growing_stream(fd, payload_bytes=100)
            streams.append(stream)
            return stream
        with mock.patch.object(workspace_git, 'MAX_STAGED_BYTES', 7), \
                mock.patch.object(workspace_git.os, 'fdopen', growing):
            with self.assertRaisesRegex(workspace_git.WorkspaceGitCollectionError,
                                        'workspace_git_collection_failed.*bytes'):
                workspace_git._copy_view(source_root, self.root / 'stage',
                                         skip=lambda path: False, ignored=set())
        self.assertEqual(streams[0].read_sizes, [8])
        self.assertEqual((self.root / 'stage' / 'growing').stat().st_size, 0)

    def _copy_growing_files(self, budget, count):
        from unittest import mock
        import workspace_git
        source = self.root / 'source'
        source.mkdir()
        for index in range(count):
            (source / f'file{index}').write_bytes(b'x')
        streams = []
        def growing(fd, mode):
            stream = self._growing_stream(fd, payload_bytes=4)
            streams.append(stream)
            return stream
        with mock.patch.object(workspace_git, 'MAX_STAGED_BYTES', budget), \
                mock.patch.object(workspace_git.os, 'fdopen', growing):
            workspace_git._copy_view(source, self.root / 'stage',
                                     skip=lambda path: False, ignored=set())
        return streams

    def test_actual_copied_bytes_accumulate_across_growing_files(self):
        import workspace_git
        with self.assertRaisesRegex(workspace_git.WorkspaceGitCollectionError,
                                    'workspace_git_collection_failed.*bytes'):
            self._copy_growing_files(10, 3)
        self.assertLessEqual(sum(path.stat().st_size for path in
                                 (self.root / 'stage').iterdir()), 10)

    def test_exact_actual_byte_budget_is_allowed(self):
        streams = self._copy_growing_files(8, 2)
        self.assertEqual(sum(path.stat().st_size for path in
                             (self.root / 'stage').iterdir()), 8)
        self.assertTrue(all(all(size > 0 for size in stream.read_sizes)
                            for stream in streams))

    def test_special_file_swap_before_git_uses_the_private_copy(self):
        from unittest import mock
        import workspace_git
        real = workspace_git._invoke
        for name, contents in (('.gitignore', 'ignored.bin\n'),
                               ('.gitattributes', 'data -text\n')):
            for command in (('add', '-A'), ('status', '--porcelain'),
                            ('diff',), ('log', '-p')):
                with self.subTest(name=name, command=command):
                    special = self.repo / name
                    special.write_text(contents)
                    (self.repo / 'ignored.bin').write_bytes(b'ignored')
                    observed = []
                    def swap(args, **kwargs):
                        trees = [arg.split('=', 1)[1] for arg in args
                                 if arg.startswith('--work-tree=')]
                        if trees:
                            tree = Path(trees[0])
                            self.assertNotEqual(tree, self.repo)
                            self.assertEqual((tree / name).read_text(), contents)
                            if not observed:
                                special.unlink()
                                os.mkfifo(special)
                            observed.append(tree)
                        return real(args, **kwargs)
                    try:
                        with mock.patch.object(workspace_git, '_invoke', swap):
                            result = workspace_git.run(*command, cwd=self.repo)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertTrue(observed)
                    finally:
                        special.unlink()

    def test_special_swap_to_fifo_before_open_is_refused_without_git(self):
        from unittest import mock
        import workspace_git
        real = os.open
        for name in ('.gitignore', '.gitattributes'):
            with self.subTest(name=name):
                special = self.repo / name
                special.write_text('data\n')
                opened = []
                def swap(path, flags, *args, **kwargs):
                    if Path(path) == special:
                        opened.append(flags)
                        special.unlink()
                        os.mkfifo(special)
                    return real(path, flags, *args, **kwargs)
                try:
                    with mock.patch.object(workspace_git.os, 'open', swap), \
                            WorkspaceGitHostileTreeTests._no_work_tree_git(self):
                        with self.assertRaisesRegex(workspace_git.WorkspaceGitCollectionError,
                                                    'not a regular file'):
                            workspace_git.run('status', cwd=self.repo)
                    self.assertEqual(len(opened), 1)
                    self.assertTrue(opened[0] & os.O_NOFOLLOW)
                    self.assertTrue(opened[0] & os.O_NONBLOCK)
                finally:
                    special.unlink()

    def test_only_worktree_list_is_exempt_from_private_collection(self):
        import workspace_git
        os.mkfifo(self.repo / '.gitignore')
        self.assertEqual(workspace_git.run('worktree', 'list', '--porcelain',
                                          cwd=self.repo).returncode, 0)
        with WorkspaceGitHostileTreeTests._no_work_tree_git(self):
            for operation in ('add', 'remove'):
                with self.subTest(operation=operation):
                    with self.assertRaisesRegex(workspace_git.WorkspaceGitCollectionError,
                                                'not a regular file'):
                        workspace_git.run('worktree', operation, 'unused', cwd=self.repo)

    def test_seal_snapshot_failure_is_sanitized_and_cleaned_up(self):
        from unittest import mock
        import workspace_git
        self.raw('config', 'remote.test.url', 'agent-controlled-data')
        real = workspace_git._invoke
        allocated = []
        real_private = workspace_git._private_dir
        def private():
            path = real_private()
            allocated.append(path)
            return path
        def fail(args, **kwargs):
            if kwargs.get('check'):
                raise subprocess.CalledProcessError(128, ['agent-controlled-command'],
                                                    output='agent-controlled-output',
                                                    stderr='agent-controlled-error')
            return real(args, **kwargs)
        with mock.patch.object(workspace_git, '_private_dir', private), \
                mock.patch.object(workspace_git, '_invoke', fail):
            with self.assertRaises(workspace_git.WorkspaceGitCollectionError) as raised:
                workspace_git.seal(self.repo)
        self.assertEqual(str(raised.exception),
                         'workspace_git_collection_failed: git config exited 128')
        self.assertTrue(allocated)
        self.assertTrue(all(not path.exists() for path in allocated))
        self.assertIsNone(workspace_git._record(self.repo))


class WorkspaceGitTrackedIgnoreTests(_WorkspaceGitFixture, unittest.TestCase):
    def test_tracked_descendant_of_ignored_directory_is_copied(self):
        import workspace_git
        (self.repo / 'sub').mkdir()
        (self.repo / 'sub' / 'data').write_text('tracked before\n')
        self.raw('add', 'sub/data')
        self.raw('commit', '-qm', 'tracked descendant')
        workspace_git.seal(self.repo)
        self.addCleanup(workspace_git.release, self.repo)
        (self.repo / '.gitignore').write_text('sub/\n')
        (self.repo / 'sub' / 'data').write_text('tracked after\n')
        (self.repo / 'sub' / 'ignored').write_text('ignored content\n')
        diff = run_eval._build_judge_diff(self.repo)
        self.assertIn('+tracked after', diff)
        self.assertNotIn('ignored content', diff)


class WorkspaceGitNestedViewTests(_WorkspaceGitFixture, unittest.TestCase):
    def test_nested_gitlinks_and_removed_markers_keep_private_reads_working(self):
        import workspace_git
        nested = self.repo / 'nested'
        nested.mkdir()
        def nested_git(*args):
            return subprocess.run(['/usr/bin/git', '-c', 'user.name=ci',
                                   '-c', 'user.email=ci@example.com', *args],
                                  cwd=nested, env=self.env, check=True,
                                  capture_output=True, text=True, timeout=10)
        nested_git('init', '-q')
        (nested / 'inside').write_text('nested content\n')
        nested_git('add', '-A')
        nested_git('commit', '-qm', 'nested fixture commit')
        # A directory symlink to a repository must remain a symlink in the
        # view; pruning only applies to lstat-confirmed plain directories.
        (self.repo / 'repo-link').symlink_to(nested, target_is_directory=True)
        workspace_git.run('add', '-A', cwd=self.repo, check=True)
        self.raw('commit', '-qm', 'nested baseline')
        workspace_git.seal(self.repo)
        self.addCleanup(workspace_git.release, self.repo)
        for command in (('status', '--porcelain'), ('diff',), ('log', '-p')):
            with self.subTest(command=command, marker='present'):
                result = workspace_git.run(*command, cwd=self.repo, check=True)
                self.assertEqual(result.returncode, 0)
                if command[0] == 'status':
                    self.assertEqual(result.stdout, '')
        diff = run_eval._build_judge_diff(self.repo)
        self.assertIn('nested fixture commit', diff)
        self.assertIn('nested content', diff)
        shutil.rmtree(nested / '.git')
        for command in (('status', '--porcelain'), ('diff',), ('log', '-p')):
            with self.subTest(command=command, marker='removed'):
                result = workspace_git.run(*command, cwd=self.repo, check=True)
                self.assertEqual(result.returncode, 0)
                if command[0] == 'status':
                    self.assertEqual(result.stdout, '')
        # An exact tracked gitlink root still bypasses an ignore rule when
        # its type changes to a symlink; only descendants need --no-index.
        moved = self.root / 'removed-marker-tree'
        nested.rename(moved)
        nested.symlink_to(moved, target_is_directory=True)
        (self.repo / '.gitignore').write_text('nested\n')
        self.raw('add', '-A')
        native = self.raw('diff', '--cached').stdout
        workspace_git.run('add', '-A', cwd=self.repo, check=True)
        changed = workspace_git.run('diff', '--cached', cwd=self.repo,
                                    check=True).stdout
        self.assertEqual(changed, native)
        self.assertIn('new file mode 120000', changed)
        nested.unlink()
        moved.rename(nested)
        (self.repo / '.gitignore').unlink()
        self.raw('reset', '--mixed', 'HEAD')
        workspace_git.release(self.repo)
        workspace_git.seal(self.repo)
        # Match native Git when adding a former gitlink without its marker;
        # the symlink remains unchanged and ignore rules still apply.
        (nested / '.gitignore').write_text('ignored\n')
        (nested / 'ignored').write_text('ignored payload\n')
        self.raw('add', '-A')
        native = self.raw('diff', '--cached').stdout
        workspace_git.run('add', '-A', cwd=self.repo, check=True)
        diff = workspace_git.run('diff', '--cached', cwd=self.repo,
                                 check=True).stdout
        self.assertEqual(diff, native)
        self.assertNotIn('ignored payload', diff)
        self.assertNotIn('repo-link', diff)
