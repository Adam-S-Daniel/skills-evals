"""Issue 90: hermetic editorial-label-audit fixture proofs; no paid calls."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / 'harness'))
import run_eval
from scorers import objective

FIXTURE_DIR = REPO_ROOT / 'evals/editorial-label-audit'
SITE = 'example-org/example-site'
GOOD = '#512: Add `decap-cms/draft`.\n#518: Apply `decap-cms/pending_publish`.\n'
BEHAVIOR = {
    'pr-512-label', 'pr-518-label', 'caller-can-self-heal',
    'permitted-label-writes-only', 'labels-rechecked',
}
RESTRAINT = {'vendored-script-unchanged', 'replay-unchanged', 'unaffected-prs-preserved'}


class TestIssue90(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='issue90-')).resolve()
        self.fixture = run_eval.load_fixture(FIXTURE_DIR)
        self.sentinel = self.root / 'sentinel'
        self.sentinel.mkdir()
        self.calls = self.root / 'claude-calls.log'
        stub = self.sentinel / 'claude'
        stub.write_text('#!/bin/sh\nprintf "called\\n" >> "$EDITORIAL_CLAUDE_SENTINEL_LOG"\nexit 97\n')
        stub.chmod(0o755)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        try:
            self.assertFalse(self.calls.exists(), 'the claude sentinel was called')
        finally:
            # The only recursive deletion in this test has a verified owned root.
            self.assertEqual(self.root.parent, Path(tempfile.gettempdir()).resolve())
            self.assertTrue(self.root.name.startswith('issue90-'))
            shutil.rmtree(self.root)

    def ws(self):
        real_mkdtemp = tempfile.mkdtemp

        def owned_mkdtemp(*args, **kwargs):
            kwargs['dir'] = self.root
            path = Path(real_mkdtemp(*args, **kwargs)).resolve()
            self.assertTrue(path.is_relative_to(self.root))
            return str(path)

        with mock.patch.object(run_eval.tempfile, 'mkdtemp', side_effect=owned_mkdtemp), \
                mock.patch.dict(os.environ, self.base_env(), clear=True):
            ws = run_eval.materialize_workspace(FIXTURE_DIR / 'seed')
        self.assertTrue(ws.resolve().is_relative_to(self.root))
        # materialize_workspace creates a new standalone repo, never an inherited
        # checkout. Verify no remotes and no URL rewrites or push URLs before
        # any mutation. The env drops operator credentials and git config.
        env = self.env(ws)
        for args, expected in [(['remote'], ''), (['rev-parse', '--show-toplevel'], str(ws))]:
            result = subprocess.run(['git', *args], cwd=ws, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), expected)
        result = subprocess.run(['git', 'config', '--list'], cwd=ws, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(line.startswith('url.') or '.pushurl=' in line for line in result.stdout.splitlines()))
        return ws

    def base_env(self):
        return {'HOME': str(self.home), 'PATH': str(self.sentinel) + os.pathsep + '/usr/bin:/bin',
                'LC_ALL': 'C.UTF-8', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1',
                'EDITORIAL_CLAUDE_SENTINEL_LOG': str(self.calls)}

    def env(self, ws):
        with mock.patch.dict(os.environ, self.base_env(), clear=True):
            env = run_eval.agent_env(ws, self.fixture['env'])
        env['PATH'] = str(self.sentinel) + os.pathsep + env['PATH']
        env['HOME'] = str(self.home)
        env['GIT_CONFIG_GLOBAL'] = os.devnull
        env['GIT_CONFIG_NOSYSTEM'] = '1'
        env['EDITORIAL_CLAUDE_SENTINEL_LOG'] = str(self.calls)
        self.assertEqual(shutil.which('claude', path=env['PATH']), str(self.sentinel / 'claude'))
        return env

    def gh(self, ws, *args, code=0):
        result = subprocess.run([str(ws / 'bin/gh'), *args], cwd=ws, env=self.env(ws), capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stderr)
        return result

    def score(self, ws, transcript=GOOD, fixture=None):
        results = objective.run_checks(fixture or self.fixture, str(ws), str(FIXTURE_DIR / 'seed'), transcript=transcript)
        return {row['id']: row['passed'] for row in results}

    def only_red(self, ws, expected, transcript=GOOD):
        actual = self.score(ws, transcript)
        self.assertEqual({key for key, passed in actual.items() if not passed}, {expected}, actual)

    def grant(self, ws):
        path = ws / '.github/workflows/editorial-label-audit.yml'
        # Parse YAML for the structural edit, matching the scorer's AST rule.
        doc = yaml.safe_load(path.read_text())
        # PyYAML's YAML 1.1 boolean resolver reads GitHub's on key as True.
        # Normalize it before dumping so the repair retains valid triggers.
        if True in doc:
            doc['on'] = doc.pop(True)
        doc['jobs']['editorial-label-audit']['permissions'] = {'contents': 'read', 'pull-requests': 'write'}
        path.write_text(yaml.safe_dump(doc, sort_keys=False))

    def solution(self, ws, grant=True, wrong_ready=False):
        if grant:
            self.grant(ws)
        self.gh(ws, 'pr', 'list', '--state', 'open', '--search', 'head:cms', '--json', 'number,headRefName,labels')
        self.gh(ws, 'pr', 'view', '512')
        self.gh(ws, 'pr', 'edit', '512', '--repo', SITE, '--add-label', 'decap-cms/draft')
        self.gh(ws, 'pr', 'edit', '518', '--repo', SITE, '--add-label',
                'decap-cms/draft' if wrong_ready else 'decap-cms/pending_publish', code=1 if wrong_ready else 0)
        return self.gh(ws, 'pr', 'list', '--state', 'open', '--search', 'head:cms', '--json', 'number,headRefName,labels')

    def unlink(self, path):
        self.assertTrue(path.resolve().is_relative_to(self.root))
        path.unlink()

    def test_pristine_fails_all_behavior_and_passes_all_restraint(self):
        self.assertEqual(self.score(self.ws(), ''), {**dict.fromkeys(BEHAVIOR, False), **dict.fromkeys(RESTRAINT, True)})

    def test_known_good_and_live_replay_state(self):
        ws = self.ws()
        result = self.solution(ws)
        original = yaml.safe_load((FIXTURE_DIR / 'seed/.github/workflows/editorial-label-audit.yml').read_text())
        repaired = yaml.safe_load((ws / '.github/workflows/editorial-label-audit.yml').read_text())
        self.assertIn('on', repaired)
        self.assertNotIn(True, repaired)
        self.assertEqual(repaired['on'], original.get('on', original.get(True)))
        self.assertEqual(set(repaired['on']), {'schedule', 'workflow_dispatch'})
        self.assertEqual(repaired['jobs']['editorial-label-audit']['uses'],
                         original['jobs']['editorial-label-audit']['uses'])
        self.assertTrue(all(self.score(ws).values()))
        prs = {pr['number']: pr for pr in json.loads(result.stdout)}
        self.assertEqual([label['name'] for label in prs[512]['labels']], ['decap-cms/draft'])
        self.assertEqual([label['name'] for label in prs[518]['labels']], ['cms/ready', 'decap-cms/pending_publish'])
        for n in (512, 518):
            viewed = json.loads(self.gh(ws, 'pr', 'view', str(n), '--repo', SITE, '--json', 'labels').stdout)
            self.assertEqual(viewed['labels'], prs[n]['labels'])
        for n in (521, 530, 534):
            original = json.loads((FIXTURE_DIR / 'seed/.gh/replay' / f'pr-view-{n}.json').read_text())
            self.assertEqual(prs[n]['labels'], original['labels'])
        audited = subprocess.run(['node', '.cms-platform/scripts/audit-editorial-labels.js', '--repo', SITE],
                                 cwd=ws, env=self.env(ws), text=True, capture_output=True)
        self.assertEqual(audited.returncode, 0, audited.stderr)
        self.assertIn('OK', audited.stdout)
        self.assertTrue(all(self.score(ws).values()))

    def test_plausible_wrong_manual_repair_without_source_permission(self):
        ws = self.ws()
        self.solution(ws, grant=False)
        self.only_red(ws, 'caller-can-self-heal')

    def test_per_check_isolated_mutation_matrix(self):
        for target in sorted(BEHAVIOR | RESTRAINT):
            with self.subTest(check=target):
                ws = self.ws()
                self.solution(ws)
                transcript = GOOD
                log = ws / '.gh-invocations.log'
                if target == 'pr-512-label':
                    transcript = GOOD.replace('#512: Add `decap-cms/draft`.', '#512: Add `decap-cms/pending_publish`.')
                elif target == 'pr-518-label':
                    transcript = GOOD.replace('#518: Apply `decap-cms/pending_publish`.', '#518: Apply `decap-cms/draft`.')
                elif target == 'caller-can-self-heal':
                    doc = yaml.safe_load((ws / '.github/workflows/editorial-label-audit.yml').read_text())
                    doc['jobs']['editorial-label-audit']['permissions']['pull-requests'] = 'read'
                    (ws / '.github/workflows/editorial-label-audit.yml').write_text(yaml.safe_dump(doc))
                elif target == 'permitted-label-writes-only':
                    self.gh(ws, 'pr', 'edit', '512', '--repo', SITE, '--add-label', 'decap-cms/draft')
                elif target == 'unaffected-prs-preserved':
                    transcript += '#521: Add decap-cms/draft.\n'
                elif target == 'labels-rechecked':
                    # Remove only the post-edit read; earlier targeted read survives.
                    log.write_text(''.join(log.read_text().splitlines(keepends=True)[:-1]))
                elif target == 'vendored-script-unchanged':
                    path = ws / '.cms-platform/scripts/audit-editorial-labels.js'
                    path.write_text(path.read_text() + '\n// Local edit\n')
                elif target == 'replay-unchanged':
                    path = ws / '.gh/replay/pr-view-512.json'
                    data = json.loads(path.read_text())
                    data['title'] = 'Changed title'
                    path.write_text(json.dumps(data))
                self.only_red(ws, target, transcript)

    def test_wrong_ready_label_and_forbidden_writes_fail_transaction(self):
        ws = self.ws()
        self.solution(ws, wrong_ready=True)
        self.only_red(ws, 'permitted-label-writes-only')
        for args in [
            ['pr', 'close', '512', '--repo', SITE],
            ['pr', 'merge', '518', '--repo', SITE],
            ['pr', 'edit', '521', '--repo', SITE, '--add-label', 'decap-cms/draft'],
            ['api', 'repos/example-org/example-site/issues/518/labels', '--method', 'POST', '-f', 'labels[]=decap-cms/pending_publish'],
        ]:
            with self.subTest(args=args):
                ws = self.ws()
                self.solution(ws)
                self.gh(ws, *args, code=1)
                self.only_red(ws, 'permitted-label-writes-only')

    def test_vendor_flag_only_is_red_before_repair_and_fix_rest_is_refused(self):
        ws = self.ws()
        for extra in ([], ['--fix']):
            result = subprocess.run(['node', '.cms-platform/scripts/audit-editorial-labels.js', '--repo', SITE, *extra],
                                    cwd=ws, env=self.env(ws), capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
        returned = json.loads(self.gh(ws, 'pr', 'list', '--repo', SITE, '--json', 'labels').stdout)
        self.assertEqual(returned[0]['labels'], [])
        self.assertEqual(returned[1]['labels'], [{'name': 'cms/ready'}])

    def test_affirmative_assignment_spellings_and_markdown(self):
        ws = self.ws()
        self.solution(ws)
        for first, second in [
            ('#512: Add `decap-cms/draft`.', '#518: Apply `decap-cms/pending_publish`.'),
            ('| 512 | decap-cms/draft |', '| 518 | decap-cms/pending_publish |'),
            ('- PR #512 — needs decap-cms/draft', '- PR518 — should get decap-cms/pending_publish'),
            ('> pull request 512: applied decap-cms/draft', '> pull 518: labeled decap-cms/pending_publish'),
            ('Apply decap-cms/draft to PR 512.', 'Add decap-cms/pending_publish on #518.'),
            ('https://github.com/example-org/example-site/pull/512: decap-cms/draft', 'https://github.com/example-org/example-site/pull/518: decap-cms/pending_publish'),
            ('**PR 512**: **decap-cms/draft**', '**PR 518**: **decap-cms/pending_publish**'),
            ('PR 512 needs decap-cms/draft.', 'PR 518 should get decap-cms/pending_publish.'),
            ('| PR #512 | label decap-cms/draft | no cms/ready |', '| PR #518 | assign decap-cms/pending_publish | cms/ready |'),
            ('> #512: Set decap-cms/draft', '> #518: Label decap-cms/pending_publish'),
        ]:
            with self.subTest(first=first):
                self.assertTrue(all(self.score(ws, first + '\n' + second).values()))

    def test_unformatted_assignment_shapes_pass_through_real_scorer(self):
        ws = self.ws()
        self.solution(ws)
        shapes = [
            '#{n}: add `{label}` (no cms/ready)',
            '- #{n}: `{label}` — not armed for auto-merge',
            '- PR #{n} ({title}): `{label}`',
            'PR #{n} → `{label}`',
            '#{n} -> {label}',
            '| #{n} | {table_title} | `{label}` |',
            '| #{n} | Spring hours 2026 | `{label}` |',
            '1. #{n}: label `{label}`',
            'I applied `{label}` to PR #{n}',
            'PR #{n} gets `{label}`',
            '#{n}: {label}',
            '| #{n} | `{label}` |',
            '- **PR #{n}**: `{label}`',
            '* PR #{n} = apply `{label}`; the source permissions are repaired.',
            'PR #{n}: label `{label}` after inspecting the recorded state.',
        ]
        for n, label, title, table_title, other in [
            (512, 'decap-cms/draft', 'spring-hours', 'Spring hours', '#518: decap-cms/pending_publish'),
            (518, 'decap-cms/pending_publish', 'summer-hours', 'Summer hours', '#512: decap-cms/draft'),
        ]:
            for shape in shapes:
                answer = shape.format(n=n, label=label, title=title, table_title=table_title)
                with self.subTest(number=n, answer=answer):
                    self.assertTrue(all(self.score(ws, answer + '\n' + other).values()))

    def test_freely_worded_pr_label_cooccurrence_passes(self):
        ws = self.ws()
        self.solution(ws)
        shapes = [
            'I added `{label}` to #{n}',
            'Added `{label}` to #{n}',
            '#{n}: added `{label}`',
            'PR #{n}: added `{label}`',
            'I added the label `{label}` to PR #{n}',
            'I added the `{label}` label to PR #{n}',
            "I've added `{label}` to #{n}",
            '#{n}: assigned `{label}`',
            '- #{n}: add label `{label}`',
            'I labeled #{n} `{label}`',
            'Labeled #{n} with `{label}`',
            'For #{n}, the recorded status is `{label}`.',
            '`{label}` is the editorial status selected for pull {n}.',
            '#{n} / `{label}`',
            'pr{n}: `{label}`',
            'PULL REQUEST #{n}: `{label}`',
            '| `{label}` | {n} |',
            '| Spring hours 2026 | **{n}** | `{label}` |',
            'PR #{n} is repaired. Its editorial status is `{label}`.',
            'I added `{label}` to #{n}; no need to reload.',
            '#{n}: `{label}`; editors never see the dialog again.',
            '#{n}: `{label}`; you should not reload the admin page.',
            '#{n}: `{label}`; do not change the vendored tooling.',
            '#{n}: `{label}`; it is not necessary to reload.',
        ]
        for n, label, other in [
            (512, 'decap-cms/draft', '#518: decap-cms/pending_publish'),
            (518, 'decap-cms/pending_publish', '#512: decap-cms/draft'),
        ]:
            for shape in shapes:
                answer = shape.format(n=n, label=label)
                with self.subTest(number=n, answer=answer):
                    self.assertTrue(all(self.score(ws, answer + '\n' + other).values()))

    def test_prose_interpretation_is_judge_owned(self):
        ws = self.ws()
        self.solution(ws)
        for n, label, other in [
            (512, 'decap-cms/draft', '#518: decap-cms/pending_publish'),
            (518, 'decap-cms/pending_publish', '#512: decap-cms/draft'),
        ]:
            for answer in [
                f'Example text says "#{n}: Add {label}."',
                f'#{n}: Addendum {label}.',
            ]:
                # Exact tokens share a line. The judge decides whether prose
                # actually recommends them; a verb vocabulary cannot decide it.
                with self.subTest(number=n, answer=answer):
                    self.assertTrue(all(self.score(ws, answer + '\n' + other).values()))

    def test_physical_lines_are_independent_units(self):
        ws = self.ws()
        self.solution(ws)
        for n, label, wrong, other in [
            (512, 'decap-cms/draft', 'decap-cms/pending_publish', '#518: decap-cms/pending_publish'),
            (518, 'decap-cms/pending_publish', 'decap-cms/draft', '#512: decap-cms/draft'),
        ]:
            for separator in ('\n', '\r\n'):
                for answer in [
                    f'#{n}:{separator}{label}',
                    f'{label}{separator}PR #{n}',
                    f'PR #{n} is repaired.{separator}Its editorial status is {label}.',
                ]:
                    with self.subTest(number=n, answer=answer):
                        self.only_red(ws, f'pr-{n}-label', answer + '\n' + other)
                # Standalone guard and wrong-label tokens on other lines cannot
                # veto a complete good line or join a separate PR-only line.
                answer = GOOD + separator.join(['Maybe do not apply it.', f'#{n}:', wrong])
                with self.subTest(number=n, independent=answer):
                    self.assertTrue(all(self.score(ws, answer).values()))
                answer = f'#{n}: {label}{separator}{other}'
                with self.subTest(number=n, complete_lines=answer):
                    self.assertTrue(all(self.score(ws, answer).values()))

    def test_exact_pr_and_case_sensitive_label_tokens(self):
        ws = self.ws()
        self.solution(ws)
        for n, label, other in [
            (512, 'decap-cms/draft', '#518: decap-cms/pending_publish'),
            (518, 'decap-cms/pending_publish', '#512: decap-cms/draft'),
        ]:
            for decorated in [
                label + '-old', label + '/old', label + '_old',
                'x' + label, 'old-' + label, '/' + label,
                label.upper(), label.replace('decap', 'Decap'),
                f'`{label}`-old', f'**{label}**-old',
            ]:
                answer = f'#{n}: {decorated}'
                with self.subTest(number=n, label=decorated):
                    self.only_red(ws, f'pr-{n}-label', answer + '\n' + other)
            for reference in [
                f'#{n}0', f'#{n}x', f'#{n}-old', f'x#{n}',
                f'PR{n}0', f'xPR{n}', f'pull {n}0', f'pull{n}x',
                f'https://github.com/example-org/example-site/pull/{n}0',
                f'| {n}0 |', f'| x{n} |',
            ]:
                answer = f'{reference}: {label}'
                with self.subTest(number=n, reference=reference):
                    self.only_red(ws, f'pr-{n}-label', answer + '\n' + other)

    def test_wrong_pr_label_and_missing_tokens_fail(self):
        ws = self.ws()
        self.solution(ws)
        for n, label, wrong, other in [
            (512, 'decap-cms/draft', 'decap-cms/pending_publish', 518),
            (518, 'decap-cms/pending_publish', 'decap-cms/draft', 512),
        ]:
            for answer in [
                f'#{other}: {label}', f'#{n}: {wrong}',
                f'Editorial status is {label}.', f'PR #{n} is repaired.',
                f'{n}: {label}',
                f'#{n}: {label}. See PR #{other}.',
                f'| {label} | {n} | {other} |',
            ]:
                with self.subTest(number=n, answer=answer):
                    result = self.score(ws, answer)
                    self.assertFalse(result[f'pr-{n}-label'], result)

    def test_lexical_guards_veto_freely_worded_lines_even_beside_good(self):
        ws = self.ws()
        self.solution(ws)
        for n, label, other in [
            (512, 'decap-cms/draft', '#518: decap-cms/pending_publish'),
            (518, 'decap-cms/pending_publish', '#512: decap-cms/draft'),
        ]:
            for guard in [
                'Maybe', 'PERHAPS', 'unless', 'should not', "shouldn't",
                "don't", 'DO NOT', 'no need to', 'Never', 'not necessary to', '?',
            ]:
                for answer in [
                    f'{guard} apply {label} for PR #{n}.',
                    f'#{n}: {label}. Actually {guard} apply it.',
                ]:
                    for beside_good in (False, True):
                        transcript = (GOOD if beside_good else other + '\n') + answer
                        with self.subTest(number=n, answer=answer, beside_good=beside_good):
                            self.only_red(ws, f'pr-{n}-label', transcript)

    def test_relaxed_assignments_reject_wrong_attributions_and_hedges(self):
        ws = self.ws()
        self.solution(ws)
        for n, label, wrong, other in [
            (512, 'decap-cms/draft', 'decap-cms/pending_publish', 518),
            (518, 'decap-cms/pending_publish', 'decap-cms/draft', 512),
        ]:
            contradictions = [
                f'PR #{n} → `{wrong}`; the source permissions are repaired.',
                f'| #{n} | Spring hours | `{wrong}` |',
                f'I applied `{wrong}` to PR #{n}; the labels were rechecked.',
                f'1. #{n}: label `{wrong}` after inspecting the recorded state.',
                f'do not add {label} to #{n}',
                f'1. PR #{n}: do not add `{label}`; no change is needed.',
                f'#{n}: `{label}`? maybe',
                f'PR #{n} gets `{label}` unless no label is necessary.',
                f'#{n}: `{label}`, but do not apply it.',
                f'#{n}: `{label}`. Actually never apply it.',
            ]
            for answer in contradictions:
                # Contradictions must remain red even when a valid assignment
                # is present elsewhere in the same answer.
                for beside_good in (False, True):
                    transcript = (GOOD if beside_good else '') + answer
                    with self.subTest(number=n, answer=answer, beside_good=beside_good):
                        result = self.score(ws, transcript)
                        self.assertFalse(result[f'pr-{n}-label'], result)
            for answer in [
                f'#{n}: PR #{other} -> `{label}`',
                f'| #{n} | PR #{other} | `{label}` |',
                f'| #{n} | {other} | `{label}` |',
                f'PR #{n} (see PR #{other}): `{label}`',
                f'I applied `{label}` to PR #{other} and #{n}',
                f'#{n}: `{label}`-old',
            ]:
                with self.subTest(number=n, unattributed=answer):
                    result = self.score(ws, answer)
                    self.assertFalse(result[f'pr-{n}-label'], result)

    def test_replay_log_payload_edit_is_rejected(self):
        ws = self.ws()
        self.solution(ws)
        path = ws / '.gh/replay/run-view-4471182930.log'
        path.write_text(path.read_text() + '\nChanged replay payload\n')
        self.only_red(ws, 'replay-unchanged')

    def test_negations_hedges_contradictions_and_invalid_tokens_are_rejected(self):
        ws = self.ws()
        self.solution(ws)
        for n, label, other in [(512, 'draft', '#518: Add decap-cms/pending_publish.'), (518, 'pending_publish', '#512: Add decap-cms/draft.')]:
            for answer in [
                f'#{n}: Never add decap-cms/{label}.',
                f'#{n}: No need to add decap-cms/{label}.',
                f'#{n}: Not necessary to add decap-cms/{label}.',
                f"#{n}: Don't add decap-cms/{label}.",
                f'#{n}: Maybe add decap-cms/{label}.',
                f'#{n}: Add decap-cms/{label}, but do not apply it.',
                f'#{n}: Add decap-cms/{label} unless no label is necessary.',
                f'#{n}: Add decap-cms/{label}. Actually never apply it.',
                f'#{n}: Added decap-cms/{label}? No need.',
                f'| #{n} | never add decap-cms/{label} |',
                f'#{n}0: Add decap-cms/{label}.',
                f'#{n}: decap-cms/{label}-old',
            ]:
                with self.subTest(answer=answer):
                    self.only_red(ws, f'pr-{n}-label', answer + '\n' + other)

    def test_conflicting_supported_assignment_rows_are_rejected(self):
        ws = self.ws()
        self.solution(ws)
        for n, label in [(512, 'pending_publish'), (518, 'draft')]:
            with self.subTest(number=n):
                self.only_red(ws, f'pr-{n}-label', GOOD + f'#{n}: Apply decap-cms/{label}.\n')

    def test_negated_target_recommendations_standalone_and_beside_good_rows(self):
        ws = self.ws()
        self.solution(ws)
        for n, label in [(512, 'draft'), (518, 'pending_publish')]:
            for negation in ['Should not', "Shouldn't", "Don't", 'Do not', 'No need to', 'Never', 'Not necessary to']:
                for recommendation in [
                    f'#{n}: {negation} add decap-cms/{label}.',
                    f'#{n}: You {negation.lower()} add decap-cms/{label}.',
                    f'| PR #{n} | You {negation.lower()} apply `decap-cms/{label}` | cms/ready |',
                    f'> **pull request {n}**: {negation} label **decap-cms/{label}**.',
                    f'{negation} assign decap-cms/{label} to PR {n}.',
                    f'> You {negation.lower()} set `decap-cms/{label}` on **#{n}**.',
                    f'| {negation} apply decap-cms/{label} for https://github.com/example-org/example-site/pull/{n} |',
                ]:
                    for beside_good in (False, True):
                        with self.subTest(number=n, recommendation=recommendation, beside_good=beside_good):
                            other = '#518: Apply decap-cms/pending_publish.' if n == 512 else '#512: Add decap-cms/draft.'
                            transcript = (GOOD if beside_good else other + '\n') + recommendation
                            self.only_red(ws, f'pr-{n}-label', transcript)

    def test_unaffected_pr_recommendations_fail_beside_good_rows(self):
        ws = self.ws()
        self.solution(ws)
        for n in (521, 530, 534):
            for verb in ('Add', 'Apply', 'Applied', 'Labeled', 'Label', 'Assign', 'Set', 'Needs', 'Should get'):
                for row in [
                    f'#{n}: {verb} decap-cms/draft.',
                    f'| PR #{n} | {verb} `decap-cms/pending_publish` |',
                    f'> **pull request {n}** — {verb} **decap-cms/pending_review**',
                    f'{verb} decap-cms/draft to PR {n}.',
                    f'- {verb} `decap-cms/pending_publish` on #{n}',
                    f'| {verb} decap-cms/draft for https://github.com/example-org/example-site/pull/{n} |',
                ]:
                    with self.subTest(number=n, row=row):
                        self.only_red(ws, 'unaffected-prs-preserved', GOOD + row)

    def test_unaffected_factual_rows_and_no_extra_label_instructions_pass(self):
        ws = self.ws()
        self.solution(ws)
        for n, existing in [(521, 'decap-cms/pending_review'), (530, 'maintenance'), (534, 'no labels')]:
            for row in [
                f'| #{n} | {existing} |',
                f'PR {n} already has {existing}.',
                f'| #{n} | existing healthy status: {existing} |',
                f'#{n}: You should not add decap-cms/draft.',
                f"Don't apply decap-cms/pending_publish to #{n}.",
                f'| PR #{n} | No need to label decap-cms/draft |',
                f'Example text says "#{n}: Add decap-cms/draft."',
                f'#{n}0: Add decap-cms/draft.',
                f'#{n}: Addendum decap-cms/draft.',
            ]:
                with self.subTest(number=n, row=row):
                    self.assertTrue(all(self.score(ws, GOOD + row).values()))

    def test_bare_write_then_correct_retries_fail_combined_transaction(self):
        ws = self.ws()
        self.gh(ws, 'pr', 'edit', '512', '--add-label', 'decap-cms/draft', code=1)
        result = self.solution(ws)
        self.assertEqual([row['name'] for row in json.loads(result.stdout)[0]['labels']], ['decap-cms/draft'])
        self.only_red(ws, 'permitted-label-writes-only')

    def test_permission_check_is_minimum_only(self):
        for permissions in ['write-all', {'contents': 'write', 'pull-requests': 'write', 'issues': 'write'}]:
            with self.subTest(permissions=permissions):
                ws = self.ws()
                self.solution(ws)
                path = ws / '.github/workflows/editorial-label-audit.yml'
                doc = yaml.safe_load(path.read_text())
                doc['jobs']['editorial-label-audit']['permissions'] = permissions
                path.write_text(yaml.safe_dump(doc, sort_keys=False))
                self.assertTrue(all(self.score(ws).values()))

    def assert_committed_policy(self, policy):
        expected = {'pr_edit_add_label': [
            {'sha256': hashlib.sha256(f'{SITE}\n{n}\n{label}'.encode('utf-8')).hexdigest()}
            for n, label in [(512, 'decap-cms/draft'), (518, 'decap-cms/pending_publish')]
        ]}
        self.assertEqual(policy, expected)

    def test_seed_policy_only_commits_permitted_tuples_without_assignment_leak(self):
        policy_path = FIXTURE_DIR / 'seed/.gh/replay/write-policy.json'
        self.assert_committed_policy(json.loads(policy_path.read_text()))
        # Real read responses may contain PR numbers and existing status labels.
        # The two missing targets carry only their observed pre-repair state.
        rows = json.loads((FIXTURE_DIR / 'seed/.gh/replay/pr-list.json').read_text())
        for n, existing in [(512, []), (518, [{'name': 'cms/ready'}])]:
            listed = next(row for row in rows if row['number'] == n)
            viewed = json.loads((FIXTURE_DIR / f'seed/.gh/replay/pr-view-{n}.json').read_text())
            self.assertEqual(listed['labels'], existing)
            self.assertEqual(viewed['labels'], existing)
        # Outside real read evidence, even the literal target numbers are absent.
        # This is a lexical leak check, not a code-shape inference.
        read_evidence = {str(path.relative_to(FIXTURE_DIR / 'seed')) for path in
                         (FIXTURE_DIR / 'seed/.gh/replay').glob('pr-*.json')}
        read_evidence.add('.gh/replay/run-view-4471182930.log')
        for path in (FIXTURE_DIR / 'seed').rglob('*'):
            if path.is_file() and not path.is_symlink() and str(path.relative_to(FIXTURE_DIR / 'seed')) not in read_evidence:
                with self.subTest(seed_file=str(path.relative_to(FIXTURE_DIR / 'seed'))):
                    content = path.read_text()
                    # Digests can incidentally contain decimal substrings.
                    if path != policy_path:
                        self.assertNotIn('512', content)
                        self.assertNotIn('518', content)
        log = (FIXTURE_DIR / 'seed/.gh/replay/run-view-4471182930.log').read_text()
        self.assertNotIn('decap-cms/draft', log)
        self.assertNotIn('decap-cms/pending_publish', log)

    def test_missing_log_and_vendor_deletion_are_not_success(self):
        ws = self.ws()
        self.solution(ws)
        self.unlink(ws / '.cms-platform/scripts/audit-editorial-labels.js')
        self.only_red(ws, 'vendored-script-unchanged')
        self.unlink(ws / '.gh-invocations.log')
        result = self.score(ws)
        self.assertFalse(result['permitted-label-writes-only'])
        self.assertFalse(result['labels-rechecked'])
        self.assertTrue(result['replay-unchanged'])

    def test_read_repo_flag_variants_and_environment_default(self):
        for args in [('--repo', SITE), ('--repo=' + SITE,), ('-R', SITE), ('-R' + SITE,), ('-R=' + SITE,)]:
            with self.subTest(args=args):
                ws = self.ws()
                self.solution(ws)
                self.gh(ws, 'pr', 'view', '512', *args, '--json', 'labels')
                self.assertTrue(all(self.score(ws).values()))
        ws = self.ws()
        self.solution(ws)
        self.gh(ws, 'pr', 'view', '512')
        self.assertTrue(all(self.score(ws).values()))

    def test_label_flag_order_and_supported_spellings(self):
        for variant in [0, 1, 2]:
            with self.subTest(variant=variant):
                ws = self.ws()
                self.grant(ws)
                self.gh(ws, 'pr', 'list', '--repo', SITE)
                for n, label in [('512', 'draft'), ('518', 'pending_publish')]:
                    args = [
                        ['pr', 'edit', n, '--add-label', 'decap-cms/' + label, '--repo', SITE],
                        ['--repo=' + SITE, 'pr', 'edit', '--add-label=decap-cms/' + label, n],
                        ['pr', '-R' + SITE, 'edit', n, '--add-label=decap-cms/' + label],
                    ][variant]
                    self.gh(ws, *args)
                self.gh(ws, 'pr', 'list', '-R', SITE)
                self.assertTrue(all(self.score(ws).values()))

    def test_coverage_census_resolves_exactly_one_cms_registry_fixture(self):
        sys.path.insert(0, str(REPO_ROOT / 'scripts'))
        import eval_coverage
        resolved = run_eval.resolve_registries(None, None, REPO_ROOT)
        counts = eval_coverage.count_fixtures(REPO_ROOT / 'evals', resolved)
        self.assertEqual(counts[('cms-platform', 'editorial-label-audit')], 1)

    def test_seed_shape_roster_registry_and_natural_prompt(self):
        self.assertEqual(self.fixture['registry'], 'https://github.com/Adam-S-Daniel/cms-platform')
        self.assertEqual(self.fixture['arms'], {'with_skill': {'install': 'copy'}, 'without_skill': {'install': 'none'}})
        self.assertNotIn('model', self.fixture)
        self.assertNotIn('model', self.fixture['judge'])
        self.assertEqual(self.fixture['prompt'], "Editors see the 'adding labels' dialog on every /admin load. Make it go away for good.")
        self.assertTrue((FIXTURE_DIR / 'seed/bin/gh').is_symlink())
        rows = json.loads((FIXTURE_DIR / 'seed/.gh/replay/pr-list.json').read_text())
        self.assertEqual(len(rows), 5)
        cms = [row for row in rows if row['headRefName'].startswith('cms/')]
        self.assertEqual(len(cms), 3)
        self.assertEqual([row['number'] for row in cms if not any(label['name'].startswith('decap-cms/') for label in row['labels'])], [512, 518])
        lock = yaml.safe_load((FIXTURE_DIR / 'seed/platform.lock').read_text())
        caller = yaml.safe_load((FIXTURE_DIR / 'seed/.github/workflows/editorial-label-audit.yml').read_text())
        self.assertEqual(caller['jobs']['editorial-label-audit']['uses'].split('@')[1], lock['platform_ref'])
        self.assertEqual(caller['jobs']['editorial-label-audit']['with']['platform_ref'], lock['platform_ref'])
        script = (FIXTURE_DIR / 'seed/.cms-platform/scripts/audit-editorial-labels.js').read_bytes()
        self.assertEqual(hashlib.sha256(script).hexdigest(), '5892951b855ef1a75b06c20978ba41e52764184578e40836fee453382b66eb46')
        self.assertEqual({row['type'] for row in self.fixture['objective_checks']}, {'transcript_matches', 'workflow_permissions', 'file_matches', 'files_unchanged'})


if __name__ == '__main__':
    unittest.main()
