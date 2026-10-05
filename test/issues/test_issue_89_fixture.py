"""Hermetic proofs for the bounded CI watcher fixture and its shell AST guard.

Source-only seed copies inherit no git state or remote reach. Mutations touch
only allocated temporary workspaces; every subprocess sees a sentinel CLI.
The outer runner must use a PID namespace, including targeted pytest runs.
"""
from __future__ import annotations

import ast
import copy
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'harness'))
import run_eval
from scorers import objective, shell_capture
from scorers.bash_ast import BashParseError, parse_bash

EVAL = ROOT / 'evals/ci-watcher-loops'
SEED = EVAL / 'seed'
ID = '73019'
REPLY = 'Run 73019 completed with conclusion success.'
TRAP = 'RUN=$(gh workflow run deploy-preview &&\n sleep 5 &&\n gh run list --json databaseId\n)\n'
# The script uses separate captures and explicitly parses both status and
# conclusion. No sleep or clock advances the replay. It reports the third
# response, rather than a successful command's exit status.
GOOD_SCRIPT = '''#!/bin/bash
set -eu
dispatch=$(gh workflow run deploy-preview --repo example-org/example-site)
run_id=$(printf '%s' "$dispatch" | python3 -c 'import json,sys; print(json.load(sys.stdin)["databaseId"])')
for attempt in 1 2 3 4; do
  result=$(gh run view "$run_id" --json status,conclusion)
  status=$(printf '%s' "$result" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')
  if [ "$status" = completed ]; then
    printf '%s' "$result" | python3 -c 'import json,sys; print("conclusion=" + json.load(sys.stdin)["conclusion"])'
    exit 0
  fi
done
exit 1
'''
BEHAVIOR = {'dispatch-once', 'captured-run-polled-to-completion', 'poll-bound', 'final-conclusion-token'}
RESTRAINT = {'scripts-split-capture', 'reply-split-capture', 'repository-files-unchanged', 'instrument-unchanged'}


class TestCiWatcherFixture(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='ci-watcher-proof-'))
        self.owned_root = self.root.resolve()
        self.addCleanup(self._cleanup)
        (self.root / 'home').mkdir()
        (self.root / 'sentinel').mkdir()
        self.calls = self.root / 'claude-calls'
        self.calls.write_text('')
        stub = self.root / 'sentinel/claude'
        stub.write_text('#!/bin/sh\nprintf "called\\n" >> "$C59_SENTINEL_LOG"\nexit 97\n')
        stub.chmod(0o755)
        self.env = {'PATH': os.pathsep.join((str(stub.parent), str(Path(sys.executable).parent), os.defpath)),
                    'HOME': str(self.root / 'home'), 'LANG': 'C.UTF-8',
                    'C59_SENTINEL_LOG': str(self.calls),
                    'GH_REPO': 'example-org/example-site',
                    'GH_TOKEN': '', 'GITHUB_TOKEN': '', 'PYTHONDONTWRITEBYTECODE': '1',
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull}
        self.fixture = yaml.safe_load((EVAL / 'fixture.yaml').read_text())
        self.serial = 0

    def _cleanup(self):
        self.assertEqual(self.root.resolve(), self.owned_root)
        self.assertTrue(self.root.name.startswith('ci-watcher-proof-'))
        self.assertEqual(self.root.parent, Path(tempfile.gettempdir()))
        self.assertEqual(self.calls.read_text(), '', 'sentinel was invoked')
        shutil.rmtree(self.root)

    def _ws(self):
        self.serial += 1
        ws = self.root / f'workspace-{self.serial}'
        shutil.copytree(SEED, ws, symlinks=False)
        # This .git holds only the fake's anchor: not an inherited repository.
        (ws / '.git').mkdir()
        (ws / '.git/workspace-root').write_text(str(ws) + '\n')
        self.assertEqual(list((ws / '.git').iterdir()), [ws / '.git/workspace-root'])
        return ws

    def _run(self, ws, *args):
        env = {**self.env, 'GH_REPLAY_DIR': str(ws / '.gh/replay'),
               'PATH': os.pathsep.join((str(self.root / 'sentinel'), str(ws / 'bin'), self.env['PATH']))}
        proc = subprocess.run(args, cwd=ws, env=env, text=True, capture_output=True, timeout=15)
        self.assertEqual(self.calls.read_text(), '')
        return proc

    def _gh(self, ws, *args):
        proc = self._run(ws, str(ws / 'bin/gh'), *args)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def _good(self):
        ws = self._ws()
        (ws / 'watch-preview.sh').write_text(GOOD_SCRIPT)
        proc = self._run(ws, 'bash', 'watch-preview.sh')
        self.assertEqual((proc.returncode, proc.stdout), (0, 'conclusion=success\n'), proc.stderr)
        return ws

    def _score(self, ws, reply=REPLY):
        return {check['id']: check['passed'] for check in objective.run_checks(
            self.fixture, str(ws), str(SEED), transcript=reply)}

    def _fails_only(self, ws, wanted, reply=REPLY):
        scores = self._score(ws, reply)
        self.assertEqual({name for name, passed in scores.items() if not passed}, {wanted}, scores)

    def test_pristine_seed_fails_behaviors_and_passes_restraints(self):
        scores = self._score(self._ws(), None)
        self.assertEqual({key for key, passed in scores.items() if not passed}, BEHAVIOR)
        self.assertTrue(all(scores[key] for key in RESTRAINT))

    def test_scripted_good_loop_and_reply_pass_all_checks(self):
        ws = self._good()
        self.assertTrue(all(self._score(ws).values()))
        self.assertEqual(json.loads((ws / '.gh-timeline-state.json').read_text()),
                         {'counts': {'run-view-73019.json': 3}})

    def test_reply_claiming_success_on_in_progress_fails_completion(self):
        ws = self._ws()
        self._gh(ws, 'workflow', 'run', 'deploy-preview', '--repo', self.env['GH_REPO'])
        payload = self._gh(ws, 'run', 'view', ID)
        self.assertEqual((payload['status'], payload['conclusion']), ('in_progress', None))
        self._fails_only(ws, 'captured-run-polled-to-completion')

    def test_duplicate_dispatch_mutation_fails_only_dispatch_once(self):
        ws = self._good()
        self._gh(ws, 'workflow', 'run', 'deploy-preview', '--repo', self.env['GH_REPO'])
        self._fails_only(ws, 'dispatch-once')

    def test_lost_run_id_mutation_fails_only_captured_sequence(self):
        ws = self._good()
        path = ws / '.gh-invocations.log'
        path.write_text(path.read_text().replace('run-view-73019.json', 'run-view-73020.json')
                        .replace('"73019"', '"73020"'))
        self._fails_only(ws, 'captured-run-polled-to-completion')

    def test_wrong_event_order_mutation_fails_only_captured_sequence(self):
        ws = self._good()
        path = ws / '.gh-invocations.log'
        rows = path.read_text().splitlines()
        path.write_text('\n'.join(rows[1:] + rows[:1]) + '\n')
        self._fails_only(ws, 'captured-run-polled-to-completion')

    def test_missing_final_read_mutation_fails_only_captured_sequence(self):
        ws = self._good()
        path = ws / '.gh-invocations.log'
        path.write_text('\n'.join(path.read_text().splitlines()[:-1]) + '\n')
        self._fails_only(ws, 'captured-run-polled-to-completion')

    def test_poll_bound_mutation_fails_only_poll_bound(self):
        ws = self._good()
        for _ in range(5):
            self._gh(ws, 'run', 'list')
        self._fails_only(ws, 'poll-bound')

    def test_reply_token_mutation_fails_only_final_conclusion(self):
        self._fails_only(self._good(), 'final-conclusion-token', 'Run 73019 completed with conclusion failure.')

    def test_script_capture_mutation_fails_only_script_guard(self):
        ws = self._good()
        (ws / 'watch-preview.sh').write_text(TRAP)
        self._fails_only(ws, 'scripts-split-capture')

    def test_nested_hidden_script_is_also_guarded(self):
        ws = self._good()
        hidden = ws / '.watchers/nested'
        hidden.mkdir(parents=True)
        (hidden / 'watch.sh').write_text(TRAP)
        self._fails_only(ws, 'scripts-split-capture')

    def test_shell_candidate_cannot_escape_workspace(self):
        ws = self._good()
        outside = self.root / 'outside.sh'
        outside.write_text('echo harmless\n')
        (ws / 'outside.sh').symlink_to(outside)
        self._fails_only(ws, 'scripts-split-capture')

    def test_unreadable_script_fails_closed(self):
        ws = self._good()
        original = Path.read_text
        def read(path, *args, **kwargs):
            if path.name == 'watch-preview.sh':
                raise OSError('unreadable')
            return original(path, *args, **kwargs)
        with mock.patch.object(Path, 'read_text', read):
            self._fails_only(ws, 'scripts-split-capture')

    def test_reply_capture_mutation_fails_only_reply_guard(self):
        self._fails_only(self._good(), 'reply-split-capture', REPLY + '\n```bash\n' + TRAP + '```')

    def test_consumer_mutation_fails_only_repository_guard(self):
        ws = self._good()
        (ws / 'site/index.html').write_text('<h1>Altered</h1>\n')
        self._fails_only(ws, 'repository-files-unchanged')

    def test_instrument_mutation_fails_only_instrument_guard(self):
        ws = self._good()
        (ws / '.gh/replay/timeline/list-1.json').write_text('[]\n')
        self._fails_only(ws, 'instrument-unchanged')

    def test_optional_discovery_read_remains_within_bound(self):
        ws = self._good()
        self._gh(ws, 'run', 'list')
        self.assertTrue(all(self._score(ws).values()))

    # Read-only context probes an agent runs before dispatching. A 404 here
    # read as "no GitHub repository" and stopped a trial before dispatch
    # (skills-evals#89, local N=3 run, trial 2 in both arms).
    PROBES = [('repo', 'view'), ('repo', 'view', '--json', 'nameWithOwner,url'),
              ('repo', 'view', 'example-org/example-site'),
              ('api', 'user'), ('api', '/user', '--jq', '.login'), ('auth', 'status'),
              # Round 2 (skills-evals#89): each of these 404ed and read as
              # "the repository does not exist" or went unanswered.
              ('workflow', 'list'), ('workflow', 'list', '--json', 'name,path'),
              ('workflow', 'view', 'deploy-preview'), ('workflow', 'view', 'deploy-preview.yml'),
              ('api', 'repos/example-org/example-site'), ('auth', 'status', '-h', 'github.com'),
              ('repo', 'list'), ('repo', 'list', 'example-org'), ('auth', 'token')]

    def _probe(self, ws):
        for args in self.PROBES:
            proc = self._run(ws, str(ws / 'bin/gh'), *args)
            self.assertEqual(proc.returncode, 0, (args, proc.stderr))

    def test_context_probes_answer_from_the_seeded_repository(self):
        ws = self._ws()
        for args in (('repo', 'view'), ('repo', 'view', '--json', 'nameWithOwner'),
                     ('repo', 'view', self.env['GH_REPO'])):
            with self.subTest(args=args):
                payload = self._gh(ws, *args)
                self.assertEqual(payload['nameWithOwner'], self.env['GH_REPO'])
                self.assertEqual(urlparse(payload['url']).hostname, 'example.com')
        for args in (('api', 'user'), ('api', '/user', '--jq', '.login')):
            with self.subTest(args=args):
                self.assertEqual(self._gh(ws, *args)['login'], 'example-operator')
        proc = self._run(ws, str(ws / 'bin/gh'), 'auth', 'status')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('Logged in to example.com as example-operator', proc.stdout)
        records = (ws / '.gh-invocations.log').read_text().splitlines()
        self.assertEqual(len(records), 6)
        for record, key in zip(records, ['repo-view.json'] * 2 + ['repo-view-example-org-example-site.json']
                               + ['api/user.json'] * 2 + ['auth-status.json']):
            self.assertTrue(record.startswith(f'--- invocation (class=read key={key} exit=0) --- '), record)

    def test_context_probes_are_neither_dispatches_nor_polls(self):
        ws = self._ws()
        self._probe(ws)
        scores = self._score(ws, None)
        self.assertEqual({key for key, passed in scores.items() if not passed}, BEHAVIOR)
        ws = self._ws()
        self._probe(ws)
        (ws / 'watch-preview.sh').write_text(GOOD_SCRIPT)
        proc = self._run(ws, 'bash', 'watch-preview.sh')
        self.assertEqual((proc.returncode, proc.stdout), (0, 'conclusion=success\n'), proc.stderr)
        self._probe(ws)
        self.assertTrue(all(self._score(ws).values()))
        self.assertEqual(json.loads((ws / '.gh-timeline-state.json').read_text()),
                         {'counts': {'run-view-73019.json': 3}})

    def test_round_two_probes_answer_consistently_with_the_seeded_repository(self):
        ws = self._ws()
        listing = self._gh(ws, 'workflow', 'list', '--json', 'name,path,state')
        self.assertEqual([(w['name'], w['path'], w['state']) for w in listing],
                         [('deploy-preview', '.github/workflows/deploy-preview.yml', 'active')])
        self.assertTrue((ws / listing[0]['path']).is_file())
        for name in ('deploy-preview', 'deploy-preview.yml'):
            proc = self._run(ws, str(ws / 'bin/gh'), 'workflow', 'view', name)
            self.assertEqual((proc.returncode, proc.stdout),
                             (0, f'deploy-preview - deploy-preview.yml\nID: {listing[0]["id"]}\n'))
        repo = self._gh(ws, 'api', 'repos/' + self.env['GH_REPO'])
        self.assertEqual((repo['full_name'], urlparse(repo['html_url']).hostname, repo['permissions']['push']),
                         (self.env['GH_REPO'], 'example.com', True))
        for args in (('repo', 'list'), ('repo', 'list', 'example-org')):
            self.assertEqual([r['nameWithOwner'] for r in self._gh(ws, *args)], [self.env['GH_REPO']])
        proc = self._run(ws, str(ws / 'bin/gh'), 'auth', 'status', '-h', 'github.com')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('Logged in to example.com as example-operator', proc.stdout)
        proc = self._run(ws, str(ws / 'bin/gh'), 'auth', 'token')
        self.assertEqual((proc.returncode, proc.stdout), (0, 'example-sandbox-placeholder\n'))
        keys = [objective._LOG_RECORD.fullmatch(row).groups()[:3]
                for row in (ws / '.gh-invocations.log').read_text().splitlines()]
        self.assertEqual(keys, [('read', key, '0') for key in (
            'workflow-list.json', 'workflow-view-deploy-preview.json', 'workflow-view-deploy-preview.yml.json',
            'api/repos/example-org/example-site.json', 'repo-list.json', 'repo-list-example-org.json',
            'auth-status-github.com.json', 'auth-token.json')])

    def test_yml_dispatch_spelling_is_one_accepted_dispatch(self):
        replay = SEED / '.gh/replay'
        self.assertEqual((replay / 'workflow-run-deploy-preview.yml.json').read_bytes(),
                         (replay / 'workflow-run-deploy-preview.json').read_bytes())
        ws = self._ws()
        dispatch = self._gh(ws, 'workflow', 'run', 'deploy-preview.yml', '--repo', self.env['GH_REPO'])
        self.assertEqual(dispatch['databaseId'], int(ID))
        for _ in range(3):
            self._gh(ws, 'run', 'view', ID, '--json', 'status,conclusion')
        self.assertTrue(all(self._score(ws).values()))
        self.assertTrue((ws / '.gh-invocations.log').read_text().startswith(
            '--- invocation (class=write key=workflow-run-deploy-preview.yml.json exit=0) --- '))
        # Both spellings are two dispatches of one workflow.
        ws = self._good()
        self._gh(ws, 'workflow', 'run', 'deploy-preview.yml', '--repo', self.env['GH_REPO'])
        self._fails_only(ws, 'dispatch-once')

    # Refused forms seen in rounds 1 and 2 of skills-evals#89. Each used to
    # get a token-scope 403 that agents read as a credential problem.
    REFUSED = [('workflow', 'run', 'deploy-preview'),
               ('workflow', 'run', 'deploy-preview.yml', '--ref', 'master'),
               ('workflow', 'run', 'deploy-preview', '--repo', 'example-org/example-site', '--ref', 'master'),
               ('workflow', 'run', 'Deploy Preview', '--repo', 'example-org/example-site')]

    def test_refused_dispatch_forms_name_the_permitted_command_lines(self):
        ws = self._ws()
        for args in self.REFUSED:
            with self.subTest(args=args):
                proc = self._run(ws, str(ws / 'bin/gh'), *args)
                self.assertEqual((proc.returncode, proc.stdout), (1, ''))
                self.assertNotIn('scopes', proc.stderr)
                self.assertNotIn('403', proc.stderr)
                for name in ('deploy-preview', 'deploy-preview.yml'):
                    self.assertIn(f'\n  gh workflow run {name} --repo example-org/example-site\n', proc.stderr)
                record = (ws / '.gh-invocations.log').read_text().splitlines()[-1]
                self.assertRegex(record, r'^--- invocation \(class=write key=\S+ exit=1\) --- ')
        scores = self._score(ws, None)
        self.assertEqual({key for key, passed in scores.items() if not passed}, BEHAVIOR)
        (ws / 'watch-preview.sh').write_text(GOOD_SCRIPT)
        proc = self._run(ws, 'bash', 'watch-preview.sh')
        self.assertEqual((proc.returncode, proc.stdout), (0, 'conclusion=success\n'), proc.stderr)
        self.assertTrue(all(self._score(ws).values()))

    def test_probe_payload_mutation_fails_only_instrument_guard(self):
        for rel in ('auth-status.txt', 'api/user.json', 'repo-view.json',
                    'workflow-run-deploy-preview.yml.json', 'workflow-list.json',
                    'workflow-view-deploy-preview.txt', 'workflow-view-deploy-preview.yml.txt',
                    'api/repos/example-org/example-site.json', 'repo-list.json',
                    'auth-status-github.com.txt', 'auth-token.txt'):
            with self.subTest(payload=rel):
                ws = self._good()
                (ws / '.gh/replay' / rel).write_text('{}\n')
                self._fails_only(ws, 'instrument-unchanged')

    def test_unsupported_script_constructs_do_not_invalidate_split_captures(self):
        for construct in ['[[ -n preview ]]', 'n=0; n=$((n+1))',
                          'case preview in preview) : ;; esac',
                          'for ((n=0;n<1;n++)); do :; done',
                          'declare -a previews=(one two)']:
            with self.subTest(construct=construct):
                ws = self._good()
                (ws / 'watch-preview.sh').write_text(construct + '\n' + GOOD_SCRIPT)
                self.assertTrue(all(self._score(ws).values()))

    def test_unrelated_invalid_syntax_does_not_invalidate_split_captures(self):
        # The whole script does not parse, yet every candidate body does.
        for line in ['if true; then', 'x=(', 'function {', ')', '[[ -n']:
            with self.subTest(line=line):
                with self.assertRaises(BashParseError):
                    parse_bash(line + '\n' + GOOD_SCRIPT)
                ws = self._good()
                (ws / 'watch-preview.sh').write_text(line + '\n' + GOOD_SCRIPT)
                self.assertTrue(all(self._score(ws).values()))

    def test_skill_discovery_status_and_separate_conclusion_pattern(self):
        ws = self._ws()
        self._gh(ws, 'workflow', 'run', 'deploy-preview', '--repo', self.env['GH_REPO'])
        run_id = str(self._gh(ws, 'run', 'list')[0]['databaseId'])
        for _ in range(3):
            self._gh(ws, 'run', 'view', run_id, '--json', 'status')
        final = self._gh(ws, 'run', 'view', run_id, '--json', 'conclusion')
        self.assertEqual(final['conclusion'], 'success')
        self.assertTrue(all(self._score(ws).values()))
        # Five reads are the recommended pattern; two spare reads are allowed.
        for _ in range(2):
            self._gh(ws, 'run', 'list')
        self.assertTrue(all(self._score(ws).values()))
        self._gh(ws, 'run', 'list')
        self._fails_only(ws, 'poll-bound')

    def test_run_id_can_precede_or_follow_view_flags(self):
        for arguments in [('run', 'view', ID, '--json', 'status,conclusion'),
                          ('run', 'view', '--json', 'status,conclusion', ID)]:
            with self.subTest(arguments=arguments):
                ws = self._ws()
                self._gh(ws, 'workflow', 'run', 'deploy-preview', '--repo', self.env['GH_REPO'])
                for _ in range(3):
                    self._gh(ws, *arguments)
                self.assertTrue(all(self._score(ws).values()))
                rows = [objective._LOG_RECORD.fullmatch(row)
                        for row in (ws / '.gh-invocations.log').read_text().splitlines()]
                self.assertTrue(all(rows))
                self.assertEqual([row.group(2) for row in rows[1:]], ['run-view-73019.json'] * 3)

    def test_success_word_forms_are_decidable_tokens(self):
        ws = self._good()
        for word in ['success', 'successful', 'successfully']:
            with self.subTest(word=word):
                self.assertTrue(all(self._score(ws, 'Run completed ' + word + '.').values()))
        for word in ['unsuccessful', 'unsuccessfully', 'successfulness', 'success_1']:
            with self.subTest(word=word):
                self._fails_only(ws, 'final-conclusion-token', 'Run completed ' + word + '.')

    def test_review_fixture_spec_mutations_are_detected(self):
        # Mutate executable scorer configuration in memory, never a repo copy.
        checks = {check['id']: check for check in self.fixture['objective_checks']}
        ws = self._good()
        self._gh(ws, 'run', 'list')
        self._gh(ws, 'run', 'view', ID, '--json', 'conclusion')
        checks['poll-bound']['events'][1]['max'] = 4
        with self.assertRaises(AssertionError):
            self.assertTrue(all(self._score(ws).values()))
        checks['poll-bound']['events'][1]['max'] = 7
        for _ in range(3):
            self._gh(ws, 'run', 'list')
        checks['poll-bound']['events'][1]['max'] = 8
        with self.assertRaises(AssertionError):
            self._fails_only(ws, 'poll-bound')
        checks['poll-bound']['events'][1]['max'] = 7
        ws = self._ws()
        self._gh(ws, 'workflow', 'run', 'deploy-preview', '--repo', self.env['GH_REPO'])
        for _ in range(3):
            self._gh(ws, 'run', 'view', '--json', 'status,conclusion', ID)
        checks['captured-run-polled-to-completion']['events'][1]['match']['argv_prefix'] = ['run', 'view', '${run_id}']
        with self.assertRaises(AssertionError):
            self.assertTrue(all(self._score(ws).values()))
        del checks['captured-run-polled-to-completion']['events'][1]['match']['argv_prefix']
        checks['final-conclusion-token']['must_match'] = ['(?i)(?<![A-Za-z0-9_])success(?![A-Za-z0-9_])']
        with self.assertRaises(AssertionError):
            self.assertTrue(all(self._score(ws, 'Run completed successfully.').values()))

    def test_every_payload_is_json_and_every_public_url_is_example_only(self):
        for path in (SEED / '.gh/replay').rglob('*.json'):
            document = json.loads(path.read_text())
            def inspect(value):
                if isinstance(value, dict):
                    for child in value.values(): inspect(child)
                elif isinstance(value, list):
                    for child in value: inspect(child)
                elif isinstance(value, str) and value.startswith(('https://', 'http://')):
                    self.assertIn(urlparse(value).hostname, {'example.com', 'example.net'})
            inspect(document)
        for path in (SEED / '.gh/replay').rglob('*.txt'):
            # A workflow file name (deploy-preview.yml) is not a host.
            hosts = set(re.findall(r'\b(?:[a-z0-9-]+\.)+(?!ya?ml\b)[a-z]{2,}\b', path.read_text()))
            self.assertLessEqual(hosts, {'example.com', 'example.net'}, path)
        self.assertNotIn('73019', self.fixture['prompt'])
        self.assertNotIn('success', (SEED / 'README.md').read_text())
        self.assertNotIn('model', self.fixture)
        self.assertNotIn('model', self.fixture['judge'])
        self.assertEqual((SEED / 'bin/gh').resolve(), ROOT / 'harness/fakes/gh')
        workflow = yaml.safe_load((SEED / '.github/workflows/deploy-preview.yml').read_text())
        for step in workflow['jobs']['preview']['steps']:
            if 'uses' in step: self.assertRegex(step['uses'], '@[0-9a-f]{40}$')
            if 'run' in step: self.assertNotIn('${{', step['run'])

    # Round 3 on skills-evals#89: every with_skill trial watched in the
    # background and ended its turn after one run view, and one `claude -p`
    # call is never re-invoked, so the run stayed in_progress. The follow-ups
    # are the later wake-ups; these pin that they reach completion.
    def _turns(self, replies):
        run_eval.validate_followups(self.fixture, EVAL / 'fixture.yaml')
        self.assertEqual(len(replies), 1 + len(self.fixture['followups']))
        return run_eval._combine_turns([{'result': reply} for reply in replies],
                                       self.fixture['followups'])['transcript']

    def test_one_view_per_turn_reaches_the_completed_payload(self):
        ws = self._ws()
        self._gh(ws, 'workflow', 'run', 'deploy-preview', '--repo', self.env['GH_REPO'])
        seen = [self._gh(ws, 'run', 'view', ID, '--json', 'status,conclusion')
                for _ in range(1 + len(self.fixture['followups']))]
        self.assertEqual([(view['status'], view['conclusion']) for view in seen],
                         [('in_progress', None), ('in_progress', None), ('completed', 'success')])
        transcript = self._turns([
            'Dispatched run 73019; a background watcher is on it and I will report back.',
            'Not yet: run 73019 is still in_progress. The watcher is re-armed.',
            REPLY])
        self.assertTrue(all(self._score(ws, transcript).values()))

    def test_a_watch_that_stops_after_the_first_turn_still_fails(self):
        ws = self._ws()
        self._gh(ws, 'workflow', 'run', 'deploy-preview', '--repo', self.env['GH_REPO'])
        self._gh(ws, 'run', 'view', ID, '--json', 'status,conclusion')
        transcript = self._turns(['A background watcher is on run 73019.',
                                  'Still watching run 73019.', 'Still watching run 73019.'])
        scores = self._score(ws, transcript)
        self.assertEqual({name for name, passed in scores.items() if not passed},
                         {'captured-run-polled-to-completion', 'final-conclusion-token'}, scores)

    def test_a_foreground_poller_rereading_on_every_followup_stays_in_bound(self):
        ws = self._good()
        self._gh(ws, 'run', 'list')
        for _ in self.fixture['followups']:
            view = self._gh(ws, 'run', 'view', ID, '--json', 'status,conclusion')
            self.assertEqual((view['status'], view['conclusion']), ('completed', 'success'))
        transcript = self._turns([REPLY, 'Yes: run 73019 completed with conclusion success.',
                                  'Yes, it is done and it passed.'])
        self.assertTrue(all(self._score(ws, transcript).values()))

    def test_followups_are_neutral_questions_that_score_nothing(self):
        followups = self.fixture['followups']
        self.assertEqual(followups, [
            'Is it done yet? If it has finished, tell me whether it passed.',
            'Checking in again: is it done now, and did it pass?'])
        token = [check for check in self.fixture['objective_checks']
                 if check['id'] == 'final-conclusion-token'][0]['must_match']
        for text in followups:
            self.assertFalse(any(re.search(pattern, text) for pattern in token), text)
            self.assertNotIn('73019', text)
            for word in ('fake', 'fixture', 'harness', 'eval', 'replay', 'sandbox'):
                self.assertNotIn(word, text.lower())
        scores = self._score(self._ws(), self._turns(['Dispatched.', '', '']))
        self.assertFalse(scores['final-conclusion-token'])


class TestCiWatcherShellCapture(unittest.TestCase):
    def _reply(self, text):
        return shell_capture.shell_capture_safe('', [], source='transcript', transcript=text)[0]

    def test_ast_rejects_multiline_chained_capture_with_sleep(self):
        self.assertFalse(self._reply('```bash\n' + TRAP + '```'))

    def test_inline_and_prose_captures_are_inspected(self):
        self.assertFalse(self._reply('success. `RUN=$(gh workflow run x && gh run list --limit 1)`'))
        self.assertFalse(self._reply('success. Used $(gh workflow run x && gh run list --limit 1).'))

    def test_split_capture_comments_and_quoted_data_pass(self):
        for script in [GOOD_SCRIPT, '# ' + TRAP.replace('\n', '\n# '),
                       "echo '$(gh workflow run x && gh run list --limit 1)'\n",
                       'x=$(echo one && echo two\n)\n',
                       'gh workflow run x && gh run list --limit 1\n',
                       'x=$(gh workflow run x); y=$(gh run list --limit 1)\n',
                       'x=$(gh run list; gh workflow run x)\n']:
            with self.subTest(script=script):
                self.assertTrue(self._reply('```bash\n' + script + '```'))

    def test_one_operand_compound_does_not_create_cross_operand_capture(self):
        for script in [
            'x=$(if true; then gh workflow run x; else gh run list; fi && echo okay\n)\n',
        ]:
            with self.subTest(script=script):
                self.assertTrue(self._reply('```bash\n' + script + '```'))

    def test_compounds_in_distinct_and_operands_are_rejected(self):
        self.assertFalse(self._reply(
            '```bash\nx=$({ gh workflow run x; } && { gh run list; }\n)\n```'))

    def test_guard_is_load_bearing_source_mutation(self):
        root = parse_bash('gh workflow run x && gh run list\n')
        self.assertTrue(shell_capture._unsafe_capture(root))
        with mock.patch.object(shell_capture, '_unsafe_capture', return_value=False):
            with self.assertRaises(AssertionError):
                self.assertFalse(self._reply('```bash\n' + TRAP + '```'))
        self.assertFalse(self._reply('```bash\n' + TRAP + '```'))

    def test_unparseable_candidate_only_fails_closed_with_dispatch_token(self):
        for script in ['x=$(', 'x=$(echo one && echo', 'x=$([[ -n )', 'x=$(echo one; function {)']:
            with self.subTest(script=script):
                self.assertTrue(self._reply('```bash\n' + script + '\n```'))
        for script in ['x=$(gh workflow run x &&', 'x=$(gh workflow run x; [[ -n )',
                       'x=$(function {; gh workflow run x)']:
            with self.subTest(script=script):
                self.assertFalse(self._reply('```bash\n' + script + '\n```'))

    def test_case_keywords_in_arguments_do_not_swallow_later_captures(self):
        for harmless in ['echo case in value', 'echo case subject in value', 'printf "%s" case in value',
                         'echo "case" in value']:
            with self.subTest(harmless=harmless):
                script = 'x=$(' + harmless + '); dispatch=$(gh workflow run x)'
                self.assertTrue(self._reply('```bash\n' + script + '\n```'))
        for script in ['x=$(case "$x" in x) gh workflow run x; gh run list;; esac)',
                       'x=$(if true; then case x in x) gh workflow run x; gh run list;; esac; fi)']:
            with self.subTest(script=script):
                self.assertFalse(self._reply('```bash\n' + script + '\n```'))

    def test_variable_case_subjects_keep_dispatch_inside_candidate(self):
        for subject in ['"$kind"', '$kind', '${kind}', '$(echo x)']:
            with self.subTest(subject=subject):
                script = 'x=$(case ' + subject + ' in x) gh workflow run x; gh run list;; esac)'
                self.assertFalse(self._reply('```bash\n' + script + '\n```'))

    def test_ansi_c_quoted_display_with_escaped_apostrophe_is_literal(self):
        script = "printf '%s' $'literal\\'$(gh workflow run x; gh run list)'\n"
        self.assertTrue(self._reply('```bash\n' + script + '```'))

    def test_quoted_or_escaped_dispatch_tokens_are_recognized_in_parsed_body(self):
        for command in ['"gh" workflow run x', "gh 'workflow' run x", 'g\\h workflow run x',
                        '"gh" "workflow" "run" x']:
            with self.subTest(command=command):
                script = 'x=$([[ true ]]; ' + command + '; gh run list)'
                self.assertFalse(self._reply('```bash\n' + script + '\n```'))

    def test_single_line_candidate_is_parsed_without_outer_parentheses(self):
        self.assertTrue(self._reply('`x=$(echo one && echo two)`'))
        self.assertTrue(self._reply('```bash\nx=$(echo one && echo two)\n```'))
        self.assertFalse(self._reply('`x=$(gh workflow run x && gh run list)`'))

    def test_all_sequential_separators_are_guarded(self):
        for separator in [' && ', '; ', '\n']:
            for script in ['x=$(gh workflow run x' + separator + 'gh run list)',
                           'x=`gh workflow run x' + separator + 'gh run list`',
                           'x=$(if true; then gh workflow run x' + separator + 'gh run list; fi)']:
                with self.subTest(script=script):
                    self.assertFalse(self._reply('```bash\n' + script + '\n```'))

    def test_lexical_quotes_escapes_comments_and_nested_substitutions(self):
        self.assertEqual(shell_capture._substitutions('n=$((n+1))'), [])
        bad = '$(gh workflow run x; gh run list)'
        for script in ['echo "' + bad + '"', 'x=$(echo ' + bad + ')',
                       'n=$((1 + ' + bad + '))', 'x=`echo ' + bad + '`']:
            with self.subTest(script=script):
                self.assertFalse(self._reply('```bash\n' + script + '\n```'))
        for script in ["echo '" + bad + "'", '# ' + bad, 'echo \\' + bad,
                       'echo \\`gh workflow run x; gh run list\\`',
                       'n=$((1+1))', 'echo example#' + bad.replace('gh workflow run', 'echo')]:
            with self.subTest(script=script):
                self.assertTrue(self._reply('```bash\n' + script + '\n```'))
        self.assertFalse(self._reply('Used $(gh workflow run x; # ignore ) here\ngh run list).'))
        self.assertFalse(self._reply("I've used " + bad + '.'))
        self.assertFalse(self._reply('```bash\nx=$(gh workflow run x; echo $(gh run list))\n```'))
        self.assertFalse(self._reply('```bash\nx=`gh workflow run x; echo \\`gh run list\\``\n```'))

    def test_heredoc_expansion_and_quoted_literal_bodies(self):
        trap = '$(gh workflow run x; gh run list)'
        for opener, ending, prefix, active in [('EOF', 'EOF', '', True),
                                              ("'EOF'", 'EOF', '', False),
                                              ('"EOF"', 'EOF', '', False),
                                              ('\\EOF', 'EOF', '', False),
                                              ('-EOF', 'EOF', '\t', True),
                                              ("-'EOF'", 'EOF', '\t', False)]:
            with self.subTest(opener=opener):
                script = 'cat <<' + opener + '\n' + prefix + trap + '\n' + prefix + ending + '\n'
                self.assertEqual(self._reply('```bash\n' + script + '```'), not active)
        self.assertFalse(self._reply('```bash\ncat <<A <<B\nliteral\nA\n' + trap + '\nB\n```'))

    def test_reply_status_prose_is_not_shell_and_shell_labels_are_guarded(self):
        status = 'run 73019 (deploy-preview): completed (success)'
        for reply in ['```\n' + status + '\n```', '`completed (success)`',
                      '```bash\n' + status + '\n```', '```\nx=$(echo one &&\n```']:
            with self.subTest(reply=reply):
                self.assertTrue(self._reply(reply))
        for label in ['bash', 'sh', 'shell', 'console', 'zsh', '']:
            with self.subTest(label=label):
                self.assertFalse(self._reply('```' + label + '\n' + TRAP + '```'))
        self.assertTrue(self._reply('```python\n' + TRAP + '```'))

    @staticmethod
    def _mutate_expression(function_name, expression, replacement):
        """Compile one source AST mutation in memory, with no inherited git reach."""
        tree = ast.parse(Path(shell_capture.__file__).read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == function_name)
        target = ast.dump(ast.parse(expression, mode='eval').body)
        substitute = ast.parse(replacement, mode='eval').body
        class Replace(ast.NodeTransformer):
            changed = 0
            def visit(self, node):
                if ast.dump(node) == target:
                    self.changed += 1
                    return ast.copy_location(copy.deepcopy(substitute), node)
                return super().visit(node)
        mutator = Replace()
        function = mutator.visit(function)
        if mutator.changed != 1:
            raise AssertionError(f'expected one AST source mutation, got {mutator.changed}')
        namespace = dict(shell_capture.__dict__)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                     '<shell-capture-mutant>', 'exec'), namespace)
        return namespace[function_name]

    def test_review_source_mutations_are_detected(self):
        # Whole-script parsing reintroduces finding 1 (an unrelated open `if`
        # would invalidate the script). Missing candidate filtering
        # reintroduces finding 4; dropping the AST list check loses all separators.
        mutations = [
            ('shell_capture_safe', '_substitutions(text, prose=prose)', '[(text, True)]',
             lambda: self.assertTrue(self._reply('```bash\nif true; then\n' + GOOD_SCRIPT + '```'))),
            ('shell_capture_safe', '_mentions_dispatch(body, unverifiable=True)', 'True',
             lambda: self.assertTrue(self._reply('```bash\nx=$(echo one &&\n```'))),
            ('_transcript_shell', "label in {'bash', 'sh', 'shell', 'console', 'zsh'}", 'True',
             lambda: self.assertTrue(self._reply('```python\n' + TRAP + '```'))),
            ('_flow', "words[:3] == ['gh', 'run', 'list'] and True in states", 'False',
             lambda: self.assertFalse(self._reply('```bash\nx=$(gh workflow run x; gh run list)\n```'))),
            ('_substitutions', "text.startswith('$((', cursor)", 'False',
             lambda: self.assertEqual(shell_capture._substitutions('n=$((n+1))'), [])),
        ]
        for function, expression, replacement, regression in mutations:
            with self.subTest(function=function, expression=expression):
                mutant = self._mutate_expression(function, expression, replacement)
                with mock.patch.object(shell_capture, function, mutant):
                    with self.assertRaises(AssertionError):
                        regression()

    def test_constructs_the_parser_supports_are_decided_by_the_ast(self):
        # Each body parses, so none of these reaches the fail-closed token rule.
        safe = ['x=$([[ -n "$k" ]] && gh workflow run x)',
                'x=$(n=$((n+1)); gh run list)',
                'x=$(for ((n=0;n<2;n++)); do gh run list; done)',
                'x=$(declare -a a=(one two); gh workflow run x)',
                'x=$(case k in a) gh workflow run x;; b) gh run list;; esac)',
                'x=$(if a; then gh workflow run x; elif b; then gh run list; fi)',
                'x=$(gh run list; case k in a) gh workflow run x;; esac)',
                'x=$(case x in x) echo x;; esac)']
        unsafe = ['x=$([[ -n "$k" ]] && gh workflow run x && gh run list)',
                  'x=$(n=$((n+1)); gh workflow run x; gh run list)',
                  'x=$(for ((n=0;n<2;n++)); do gh workflow run x; gh run list; done)',
                  'x=$(declare -a a=(one two); gh workflow run x; gh run list)',
                  'x=$(case k in a) gh workflow run x;; esac; gh run list)',
                  'x=$(case $(gh workflow run x) in a) gh run list;; esac)',
                  'x=$(gh workflow run x; case x in x) gh run list;; esac)',
                  'x=$(case x in x) gh workflow run x; gh run list;; esac)',
                  'x=$(case x in x) :;; y) gh workflow run x; gh run list;; esac)',
                  'x=$(if a; then gh workflow run x; elif b; then :; fi; gh run list)',
                  'x=$(if gh workflow run x; then :; elif gh run list; then :; fi)']
        for script in safe + unsafe:
            with self.subTest(script=script):
                body, complete = shell_capture._substitutions(script)[0]
                self.assertTrue(complete)
                parse_bash(body + '\n')
                self.assertEqual(self._reply('```bash\n' + script + '\n```'), script in safe)

    def test_case_terminators_fall_through_or_end_the_arm(self):
        # (script, safe): `;;` ends the case; `;&` runs the next body; `;;&`
        # tests the next patterns. Each terminator also ends the arm lexically.
        table = [
            ('id=$(case x in x) gh workflow run d ;; x) gh run list ;; esac)', True),
            ('id=$(case x in x) gh workflow run d ;& y) gh run list ;; esac)', False),
            ('id=$(case x in x) gh workflow run d ;;& x) gh run list ;; esac)', False),
            ('id=$(case x in x) gh workflow run d ;& y) : ;; z) gh run list ;; esac)', True),
            ('id=$(case x in x) gh workflow run d ;& y) : ;& z) gh run list ;; esac)', False),
            ('id=$(case x in a) : ;& x) gh workflow run d; gh run list ;; esac)', False),
            ('id=$(case x in a) : ;;& x) gh workflow run d; gh run list ;; esac)', False),
            ('id=$(case x in a) : ;& x) gh workflow run d ;; esac); y=$(gh run list)', True),
        ]
        for script, safe in table:
            with self.subTest(script=script):
                body, complete = shell_capture._substitutions(script)[0]
                self.assertTrue(complete)
                self.assertTrue(body.endswith('esac'))
                self.assertEqual(self._reply('```bash\n' + script + '\n```'), safe)

    def test_loops_functions_and_ansi_c_words_are_followed(self):
        table = [
            ('x=$(for i in 1 2; do gh run list; gh workflow run x; done)', False),
            ('x=$(while true; do gh run list; gh workflow run x; done)', False),
            ('x=$(until false; do gh run list; gh workflow run x; done)', False),
            ('x=$(for ((i=0;i<2;i++)); do gh run list; gh workflow run x; done)', False),
            ('x=$(for i in 1 2; do gh run list; done; gh workflow run x)', True),
            ('x=$(f() { gh run list; }; gh workflow run x; f)', False),
            ('x=$(function f { gh workflow run x; }; f; gh run list)', False),
            ('x=$(f() { gh run list; }; f; gh workflow run x)', True),
            ('x=$(f() { gh workflow run x; gh run list; })', True),
            ('x=$(f() { f; }; f)', True),
            ("x=$($'gh' workflow run x; gh run list)", False),
            ("x=$($'g\\x68' workflow run x; gh run list)", False),
            ("x=$($'g\\150' workflow run x; gh run list)", False),
            ("x=$(echo $'it\\'s'; gh run list)", True),
        ]
        for script, safe in table:
            with self.subTest(script=script):
                self.assertEqual(self._reply('```bash\n' + script + '\n```'), safe)

    def test_redefined_function_and_dynamic_name_keep_their_bindings(self):
        table = [
            ('x=$(f(){ f(){ gh run list; }; }; f; gh workflow run d; f)', False),
            ('x=$(f(){ f(){ :; }; }; f; gh workflow run d; f; gh run list)', False),
            ('x=$(f(){ f(){ :; }; }; gh workflow run d; f; f)', True),
            ('x=$($cmd; f(){ gh run list; }; gh workflow run d; f)', False),
        ]
        for script, safe in table:
            with self.subTest(script=script):
                self.assertEqual(self._reply('```bash\n' + script + '\n```'), safe)

    def test_flow_step_bound_fails_closed_only_for_dispatch_bodies(self):
        nested = 'for i in 1; do ' * 16 + ':' + '; done' * 16
        shallow = 'for i in 1; do ' * 8 + ':' + '; done' * 8
        with self.assertRaises(shell_capture._AnalysisLimit):
            shell_capture._unsafe_capture(parse_bash(nested + '\n'))
        self.assertFalse(shell_capture._unsafe_capture(parse_bash(shallow + '\n')))
        self.assertTrue(self._reply('```bash\nx=$(' + nested + ')\n```'))
        self.assertTrue(self._reply('```bash\nx=$(' + shallow + '; gh workflow run x)\n```'))
        ok, detail = shell_capture.shell_capture_safe(
            '', [], source='transcript',
            transcript='```bash\nx=$(' + nested + '; gh workflow run x)\n```')
        self.assertEqual((ok, detail), (False, 'reply shell example: shell analysis exceeded its bound'))

    def test_unverifiable_bodies_decode_quoted_dispatch_names(self):
        # Bodies over the step bound or that do not parse fall back to the
        # lexical scan, which must see the same quoted spellings of `gh`.
        nested = 'for i in 1; do ' * 11 + ':' + '; done' * 11 + '; '
        unparseable = '; if'
        with self.assertRaises(shell_capture._AnalysisLimit):
            shell_capture._unsafe_capture(parse_bash(nested + ':\n'))
        with self.assertRaises(BashParseError):
            parse_bash('echo one' + unparseable + '\n')
        spellings = ["$'gh'", "$'\\x67h'", "$'\\147h'", '$"gh"', 'g""h', "'g'h", '\\gh',
                     "$'\\e'"]
        for spelling in spellings:
            for prefix, suffix in [(nested, ''), ('', unparseable)]:
                script = 'x=$(' + prefix + spelling + ' workflow run d; gh run list' + suffix + ')'
                with self.subTest(script=script):
                    self.assertFalse(self._reply('```bash\n' + script + '\n```'))
        for script in ['x=$(' + nested + 'echo gh workflow; gh run list)',
                       'x=$(echo one' + unparseable + ')',
                       'x=$(echo "g\\x68 flow"' + unparseable + ')']:
            with self.subTest(script=script):
                self.assertTrue(self._reply('```bash\n' + script + '\n```'))
        # A literal "$'" inside double quotes opens a bogus $'...' span in the
        # lexical scan; decoding it must never hide a plain dispatch inside.
        for body, reply in [
                ('printf "$\'\\n"\nid=$(gh workflow run d && gh run list)\necho \'done\'',
                 '```\n{}\n```'),
                ('printf "$\'\\e"; id=$(gh workflow run d && gh run list); echo \'ok\'', '`{}`'),
                ('x=$(echo "$\'\\n"; gh workflow run d; gh run list; echo \' x\'; if)',
                 '```bash\n{}\n```')]:
            with self.subTest(body=body):
                self.assertTrue(shell_capture._mentions_dispatch(body))
                self.assertFalse(self._reply(reply.format(body)))
        # A bogus span can pair with the quote that opens a disguised word, so
        # an unverifiable body fails closed on any $' or on `workflow run`.
        bogus = 'echo "$\'\\n"; '
        for script in ['x=$(' + bogus + '"gh" workflow run d; gh run list; echo \'x\'; if)',
                       'x=$(' + bogus + '$\'\\x67h\' workflow run d; gh run list; if)',
                       'x=$(' + bogus + '$\'\\147h\' workflow run d; gh run list; if)',
                       'x=$(' + nested + bogus + '$\'\\x67h\' workflow run d; gh run list)',
                       'x=$(' + nested + bogus + '$\'\\147h\' workflow run d; gh run list)',
                       'x=$(' + bogus + 'gh $\'\\x77orkflow\' run d; gh run list; if)',
                       'x=$(' + bogus + 'gh workflow $\'\\x72un\' d; gh run list; if)',
                       'x=$(' + nested + bogus + 'gh $\'\\x77orkflow\' run d; gh run list)',
                       'x=$(' + nested + bogus + 'gh workflow $\'\\x72un\' d; gh run list)',
                       # No $': a name the spelling scan cannot read still
                       # fails closed on `workflow run` in the unquoted text.
                       'x=$("$GH" workflow run d; gh run list' + unparseable + ')',
                       'x=$(' + nested + '"$GH" work""flow run d; gh run list)',
                       # Any $' fails an unverifiable body closed, even a harmless one.
                       "x=$(echo $'g\\x68 flow'" + unparseable + ')']:
            with self.subTest(script=script):
                self.assertFalse(self._reply('```bash\n' + script + '\n```'))
        # The spelling-aware scan alone still sees a quoted name in a bogus span.
        self.assertTrue(shell_capture._mentions_dispatch(
            bogus + '"gh" workflow run d; gh run list; echo \'x\''))
        # A verifiable body that only mentions "workflow run" is decided by
        # the AST, not the fallback, so it stays clean.
        listed = 'echo "$\'\\n workflow run"; gh run list'
        self.assertFalse(shell_capture._unsafe_capture(parse_bash(listed + '\n')))
        self.assertTrue(self._reply('```bash\nx=$(' + listed + ')\n```'))
        # A parsed $"gh" is the literal word gh.
        self.assertFalse(self._reply('```bash\nx=$($"gh" workflow run d; gh run list)\n```'))
        self.assertTrue(self._reply('```bash\nx=$($"gh" workflow run d)\n```'))

    def test_unavailable_parser_raises_instead_of_passing(self):
        from scorers import bash_ast
        with mock.patch.dict(sys.modules, {'tree_sitter': None}):
            # A scorer error (never a pass, never a failed check), whether or
            # not the reply has anything to parse.
            for reply in ('```bash\nx=$(echo one)\n```', 'no shell here'):
                with self.assertRaisesRegex(bash_ast.ScorerUnavailableError, 'tree-sitter-bash==0.25.1'):
                    self._reply(reply)

    def test_invalid_source_is_rejected(self):
        with self.assertRaises(ValueError):
            shell_capture.shell_capture_safe('', [], source='other')


if __name__ == '__main__':
    unittest.main()
