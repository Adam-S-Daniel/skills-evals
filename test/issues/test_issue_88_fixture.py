"""Offline coverage for the code-quality fixture (issue #88).

The three hook-* command checks run an inline Bash probe that copies the
workspace into a temporary Git repository and runs scripts/lint-staged.sh with
fake Go tools. Tests that score a workspace need bash, git, tar and mktemp at
/usr/bin or /bin (the scorer's fixed PATH) and are skipped with a reason where
one is absent. No network, no real Go toolchain, no clock.
"""

from __future__ import annotations

import glob
import hashlib
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "harness"))
import run_eval  # noqa: E402
from scorers import commands, objective  # noqa: E402

FIXTURE_DIR = REPO / "evals" / "code-quality"
SEED = FIXTURE_DIR / "seed"
HOOK = "scripts/lint-staged.sh"
REFERENCE_GO_HOOK = REPO / "test" / "fixtures" / "issue88" / "lint-staged-go.sh"

IDS = ("golangci-width-100", "hook-guards-go-tools", "hook-lints-staged-go",
       "hook-passes-without-go-files", "hook-skips-missing-go-tools", "workflows-unchanged",
       "md-yaml-opt-outs-unchanged", "other-configs-unchanged", "package-json-parses",
       "go-sources-unchanged")
TYPES = ("parsed_config_values", "shell_staged_tool_guard", "command_succeeds",
         "command_succeeds", "command_succeeds", "files_unchanged", "files_unchanged",
         "files_unchanged", "parsed_config_values", "files_unchanged")
BEHAVIOR_IDS = IDS[:3]

# sha256 of scripts/lint-staged.sh as vendored from cms-platform
# 3c5e71c90e65e9466db5639e6ac857a398877153 (last changed in 8523c8b). The
# hook's Go branch is what the agent adds; a change here is a re-vendor.
VENDORED_HOOK_SHA256 = "427cf9c60dbb27c569ec4596eb0ac2c2fbf568a00961268e9829436f113c0bfc"

GOLANGCI = """\
version: "2"

linters:
  enable:
    - lll
  settings:
    lll:
      # 100-column house width, matching .editorconfig, Prettier, Ruff and RuboCop.
      line-length: 100
"""

GO_BRANCH = """\
# ── Go: gofmt + golangci-lint ─────────────────────────────────────────
mapfile -t GO < <(filter '\\.go$')
if [ "${#GO[@]}" -gt 0 ]; then
  if have gofmt; then
    bad=$(gofmt -l "${GO[@]}")
    if [ -n "$bad" ]; then
      printf '%s\\n' "$bad"
      RC=1
    fi
  else
    note gofmt
  fi
  if have golangci-lint; then
    golangci-lint run ./... || RC=1
  else
    note golangci-lint
  fi
fi

"""
# The ADR 0007 regression hook (test/fixtures/issue88/lint-staged-go.sh) passes
# the staged files to golangci-lint. That is valid AST input but a wrong
# reference answer: go/packages refuses named files from two directories
# ("named files must all be in one directory"), so this branch runs the module.
REGRESSION_LINT_CALL = 'golangci-lint run "${GO[@]}" || RC=1'
TAIL = 'if [ "$RC" -ne 0 ]; then'
# A one-line-per-tool branch with the tested-capture gofmt form.
SIMPLE_BRANCH = """\
mapfile -t GO < <(filter '\\.go$')
if [ "${#GO[@]}" -gt 0 ]; then
  if have gofmt; then [ -z "$(gofmt -l "${GO[@]}")" ] || RC=1; else note gofmt; fi
  if have golangci-lint; then golangci-lint run ./... || RC=1; else note golangci-lint; fi
fi

"""

TOOLS = ("bash", "git", "tar", "mktemp")
HAVE_TOOLS = all(any(os.access(f"{d}/{t}", os.X_OK) for d in ("/usr/bin", "/bin"))
                 for t in TOOLS)
needs_tools = unittest.skipUnless(
    HAVE_TOOLS, "bash, git, tar or mktemp is not at /usr/bin or /bin; the hook probe cannot run")


def fixture():
    return run_eval.load_fixture(FIXTURE_DIR)


def edit(ws, rel, fn):
    path = ws / rel
    path.write_text(fn(path.read_text()))


def add_go_branch(text, branch=GO_BRANCH):
    assert text.count(TAIL) == 1
    return text.replace(TAIL, branch + TAIL)


@contextmanager
def workspace(good=False):
    root = Path(tempfile.mkdtemp(prefix="code-quality-88-"))
    ws = root / "workspace"
    try:
        shutil.copytree(SEED, ws, symlinks=True)
        if good:
            (ws / ".golangci.yml").write_text(GOLANGCI)
            edit(ws, HOOK, add_go_branch)
            edit(ws, "AGENTS.md", lambda t: t.replace(
                "| Shell |", "| Go | gofmt, golangci-lint | `.golangci.yml` |\n| Shell |"))
        yield ws
    finally:
        shutil.rmtree(root, ignore_errors=True)


def scores(ws):
    with mock.patch.object(commands, "_network_prefix", return_value=[]):
        return {row["id"]: row["passed"]
                for row in objective.run_checks(fixture(), str(ws), str(SEED))}


class FixtureContract(unittest.TestCase):
    def test_loads_and_declares_the_checks_in_order(self):
        fx = fixture()
        self.assertEqual(fx["skill"], "code-quality")
        self.assertEqual(fx["registry"], "https://github.com/Adam-S-Daniel/cms-platform")
        self.assertEqual([c["id"] for c in fx["objective_checks"]], list(IDS))
        self.assertEqual([c["type"] for c in fx["objective_checks"]], list(TYPES))
        self.assertEqual(fx["prompt"].strip(),
                         "Add Go to our lint setup following the house conventions.")
        self.assertEqual(fx["judge"]["weights"],
                         {"correctness": 0.4, "restraint": 0.3, "explanation": 0.3})
        self.assertNotIn("model", fx)
        self.assertNotIn("model", fx["judge"])
        self.assertEqual({k: v["install"] for k, v in fx["arms"].items()},
                         {"with_skill": "copy", "without_skill": "none"})

    def test_the_three_command_checks_share_one_hidden_probe(self):
        checks = [c for c in fixture()["objective_checks"] if c["type"] == "command_succeeds"]
        self.assertEqual([c["argv"][-1] for c in checks], ["lints-staged", "no-go", "missing-tools"])
        for check in checks:
            self.assertEqual(check["argv"][:2], ["bash", "-c"])
            self.assertEqual(check["argv"][3], "hook-probe")
            self.assertEqual(check["argv"][2], checks[0]["argv"][2])
            self.assertEqual(check["timeout_s"], 60)
        # The probe lives in fixture.yaml, outside the seed the agent can read.
        for path in SEED.rglob("*"):
            if path.is_file():
                self.assertNotIn("FAKE_LINT_RC", path.read_text(), path)

    def test_the_seed_hook_is_the_vendored_platform_copy_without_go(self):
        hook = SEED / HOOK
        self.assertEqual(hashlib.sha256(hook.read_bytes()).hexdigest(), VENDORED_HOOK_SHA256)
        self.assertTrue(os.access(hook, os.X_OK))
        self.assertNotIn(".go", hook.read_text())
        # The regression copy from ADR 0007 is this hook plus GO_BRANCH, except
        # that it passes the staged files to golangci-lint.
        self.assertEqual(add_go_branch(hook.read_text()).replace("golangci-lint run ./... || RC=1",
                                                                 REGRESSION_LINT_CALL),
                         REFERENCE_GO_HOOK.read_text())

    def test_seed_states_the_house_conventions_and_has_no_go_config(self):
        self.assertIn("max_line_length = 100", (SEED / ".editorconfig").read_text())
        self.assertIn('"printWidth": 100', (SEED / ".prettierrc").read_text())
        self.assertIn("line-length = 100", (SEED / "ruff.toml").read_text())
        self.assertEqual(yaml.safe_load((SEED / ".rubocop.yml").read_text())
                         ["Layout/LineLength"]["Max"], 100)
        self.assertIs(yaml.safe_load((SEED / ".markdownlint.json").read_text())["MD013"], False)
        self.assertEqual(yaml.safe_load((SEED / ".yamllint.yml").read_text())
                         ["rules"]["line-length"], "disable")
        self.assertEqual(glob.glob(str(SEED / ".golangci*")), [])
        self.assertEqual(sorted(p.relative_to(SEED).as_posix() for p in SEED.rglob("*.go")),
                         ["internal/stock/stock.go", "internal/stock/stock_test.go", "main.go"])

    def test_the_only_workflow_runs_tests_not_lint(self):
        workflows = sorted(p.name for p in (SEED / ".github/workflows").iterdir())
        self.assertEqual(workflows, ["tests.yml"])
        text = (SEED / ".github/workflows/tests.yml").read_text()
        self.assertIn("go test ./...", text)
        for word in ("lint", "gofmt", "golangci"):
            self.assertNotIn(word, text)

    def test_prompt_and_seed_do_not_name_the_answer(self):
        prompt = fixture()["prompt"]
        for word in ("golangci", "lll", "100", "hook", "workflow", "CI"):
            self.assertNotIn(word, prompt)
        for path in SEED.rglob("*"):
            if path.is_file():
                self.assertNotIn("golangci", path.read_text(), path)

    def test_seed_text_names_only_example_hosts(self):
        for path in SEED.rglob("*"):
            if path.is_file():
                for token in path.read_text().split():
                    if token.startswith("http"):
                        self.fail(f"{path}: {token}")
        self.assertIn("module example.com/inventory", (SEED / "go.mod").read_text())

    def test_every_protected_file_is_matched_by_the_check_that_owns_it(self):
        owners = {c["id"]: c["paths"] for c in fixture()["objective_checks"]
                  if c["type"] == "files_unchanged"}
        expected = {
            "workflows-unchanged": {".github/workflows/tests.yml"},
            "md-yaml-opt-outs-unchanged": {".markdownlint.json", ".yamllint.yml"},
            "other-configs-unchanged": {".prettierrc", "ruff.toml", ".rubocop.yml"},
            "go-sources-unchanged": {"go.mod", "main.go", "internal/stock/stock.go",
                                     "internal/stock/stock_test.go"},
        }
        for check_id, files in expected.items():
            matched = {os.path.relpath(p, SEED) for pattern in owners[check_id]
                       for p in glob.glob(os.path.join(SEED, pattern)) if os.path.isfile(p)}
            self.assertEqual(matched, files, check_id)


@needs_tools
class FixtureScoring(unittest.TestCase):
    def assert_failed(self, ws, *failed):
        self.assertEqual({k for k, v in scores(ws).items() if not v}, set(failed))

    def test_pristine_seed_fails_every_behavior_check_and_passes_the_guards(self):
        with workspace() as ws:
            self.assert_failed(ws, *BEHAVIOR_IDS)

    def test_hand_built_solution_passes_every_check(self):
        with workspace(good=True) as ws:
            self.assert_failed(ws)

    def test_editorconfig_tabs_and_a_package_script_still_pass(self):
        with workspace(good=True) as ws:
            edit(ws, ".editorconfig", lambda t: t + "\n[*.go]\nindent_style = tab\n")
            edit(ws, "package.json", lambda t: t.replace(
                '"format":', '"lint:go": "golangci-lint run ./...",\n    "format":'))
            self.assert_failed(ws)

    def test_golangci_only_branch_fails_the_gofmt_checks_by_design(self):
        # Documented strictness: staged files must reach gofmt.
        branch = """\
mapfile -t GO < <(filter '\\.go$')
if [ "${#GO[@]}" -gt 0 ]; then
  if have golangci-lint; then golangci-lint run "${GO[@]}" || RC=1; else note golangci-lint; fi
fi

"""
        with workspace() as ws:
            (ws / ".golangci.yml").write_text(GOLANGCI)
            edit(ws, HOOK, lambda t: add_go_branch(t, branch))
            self.assert_failed(ws, "hook-guards-go-tools", "hook-lints-staged-go")

    # One isolated failing mutation per check.

    def test_width_80_fails_only_the_width_check(self):
        with workspace(good=True) as ws:
            edit(ws, ".golangci.yml", lambda t: t.replace("line-length: 100", "line-length: 80"))
            self.assert_failed(ws, "golangci-width-100")

    def test_quoted_scalar_paths_fail_only_the_guard_check(self):
        # One staged file makes the quoted scalar work in the probe; the AST
        # check still refuses it, because two files would arrive as one argument.
        branch = """\
GOFILES=$(git diff --cached --name-only --diff-filter=ACM -- '*.go')
if [ -n "$GOFILES" ]; then
  if have gofmt; then [ -z "$(gofmt -l "$GOFILES")" ] || RC=1; else note gofmt; fi
  if have golangci-lint; then golangci-lint run ./... || RC=1; else note golangci-lint; fi
fi

"""
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace(GO_BRANCH, branch))
            self.assert_failed(ws, "hook-guards-go-tools")

    def test_simple_branch_passes_every_check(self):
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace(GO_BRANCH, SIMPLE_BRANCH))
            self.assert_failed(ws)

    def test_swallowed_lint_failure_fails_only_the_staged_lint_check(self):
        branch = SIMPLE_BRANCH.replace("run ./... || RC=1", "run ./... || true")
        self.assertNotEqual(branch, SIMPLE_BRANCH)
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace(GO_BRANCH, branch))
            self.assert_failed(ws, "hook-lints-staged-go")

    def test_terminal_and_list_fails_only_the_no_go_commit_check(self):
        # ADR 0007 passes this shape; the probe catches its exit 1 on a commit
        # with no Go files when golangci-lint is installed.
        terminal = """\
GOFILES=$(git diff --cached --name-only --diff-filter=ACM -- '*.go')
if [ "$RC" -ne 0 ]; then exit "$RC"; fi
have gofmt || exit 0
have golangci-lint || exit 0
[ -n "$GOFILES" ] && [ -z "$(gofmt -l $GOFILES)" ] && golangci-lint run ./...
"""
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace(GO_BRANCH, "").split(TAIL)[0] + terminal)
            self.assert_failed(ws, "hook-passes-without-go-files")

    def test_unbound_variable_in_the_skip_branch_fails_only_the_skip_check(self):
        # The vendored hook runs under `set -u`; a notice naming an unset
        # variable aborts the hook exactly when golangci-lint is missing. The
        # AST check does not model nounset, the probe runs it.
        branch = SIMPLE_BRANCH.replace("else note golangci-lint; fi", 'else note "$GOLANGCI_HINT"; fi')
        self.assertNotEqual(branch, SIMPLE_BRANCH)
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace(GO_BRANCH, branch))
            self.assert_failed(ws, "hook-skips-missing-go-tools")

    def test_reference_branch_plus_go_vet_and_staticcheck_passes(self):
        # Needs fix/shell-guard-analysis-bound: under the old 256-state bound
        # a third guarded Go tool on the vendored hook failed analysis_limit.
        extra = ('  if have go; then go vet ./... || RC=1; else note go; fi\n'
                 '  if have staticcheck; then staticcheck ./... || RC=1; else note staticcheck; fi\n')
        for count in (1, 2):
            lines = "".join(extra.splitlines(keepends=True)[:count])
            with self.subTest(extra_tools=count), workspace(good=True) as ws:
                edit(ws, HOOK, lambda t: t.replace("    note golangci-lint\n  fi\nfi\n\n",
                                                   "    note golangci-lint\n  fi\n" + lines + "fi\n\n"))
                self.assert_failed(ws)

    def test_ignored_gofmt_output_fails_only_the_staged_lint_check(self):
        # `gofmt -l` exits 0 whatever it lists, so this branch never fails on
        # an unformatted file; the probe's dirty-gofmt run catches it.
        branch = SIMPLE_BRANCH.replace('[ -z "$(gofmt -l "${GO[@]}")" ] || RC=1', 'gofmt -l "${GO[@]}" || RC=1')
        self.assertNotEqual(branch, SIMPLE_BRANCH)
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace(GO_BRANCH, branch))
            self.assert_failed(ws, "hook-lints-staged-go")

    def test_new_issues_only_golangci_lint_passes(self):
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace("golangci-lint run ./...", "golangci-lint run --new-from-rev=HEAD ./..."))
            self.assert_failed(ws)

    def test_literal_package_directories_fail_only_the_guard_check(self):
        # Documented limit: a neighbor argument with a `/` is not accepted.
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace("golangci-lint run ./...", "golangci-lint run ./internal/... ."))
            self.assert_failed(ws, "hook-guards-go-tools")

    def test_added_lint_workflow_fails_only_the_workflow_check(self):
        with workspace(good=True) as ws:
            (ws / ".github/workflows/lint.yml").write_text(
                "name: lint\non: [pull_request]\njobs:\n  go:\n    runs-on: ubuntu-latest\n"
                "    steps:\n      - run: golangci-lint run ./...\n")
            self.assert_failed(ws, "workflows-unchanged")

    def test_lint_job_in_the_existing_workflow_fails_only_the_workflow_check(self):
        with workspace(good=True) as ws:
            edit(ws, ".github/workflows/tests.yml",
                 lambda t: t + "      - name: Lint\n        run: golangci-lint run ./...\n")
            self.assert_failed(ws, "workflows-unchanged")

    def test_yaml_line_length_turned_on_fails_only_the_opt_out_check(self):
        with workspace(good=True) as ws:
            edit(ws, ".yamllint.yml", lambda t: t.replace(
                "line-length: disable", "line-length:\n    max: 100"))
            self.assert_failed(ws, "md-yaml-opt-outs-unchanged")

    def test_markdown_line_length_turned_on_fails_only_the_opt_out_check(self):
        with workspace(good=True) as ws:
            edit(ws, ".markdownlint.json", lambda t: t.replace('"MD013": false', '"MD013": true'))
            self.assert_failed(ws, "md-yaml-opt-outs-unchanged")

    def test_other_language_config_edit_fails_only_its_check(self):
        for rel in (".prettierrc", "ruff.toml", ".rubocop.yml"):
            with self.subTest(rel), workspace(good=True) as ws:
                edit(ws, rel, lambda t: t.replace("100", "120"))
                self.assert_failed(ws, "other-configs-unchanged")

    def test_broken_package_json_fails_only_the_parse_check(self):
        with workspace(good=True) as ws:
            edit(ws, "package.json", lambda t: t.replace('"prettier": "3.6.2"', '"prettier": "3.6.2",'))
            self.assert_failed(ws, "package-json-parses")

    def test_reformatted_go_source_fails_only_the_source_check(self):
        for rel in ("main.go", "internal/stock/stock.go", "go.mod"):
            with self.subTest(rel), workspace(good=True) as ws:
                edit(ws, rel, lambda t: t + "\n")
                self.assert_failed(ws, "go-sources-unchanged")

    # Neighboring wrong answers.

    def test_v1_config_and_other_file_names_fail_the_width_check(self):
        v1 = "linters:\n  enable: [lll]\nlinters-settings:\n  lll:\n    line-length: 100\n"
        with workspace(good=True) as ws:
            (ws / ".golangci.yml").write_text(v1)
            self.assert_failed(ws, "golangci-width-100")
        with workspace(good=True) as ws:
            (ws / ".golangci.yml").rename(ws / ".golangci.yaml")
            self.assert_failed(ws, "golangci-width-100")
        with workspace(good=True) as ws:
            edit(ws, ".golangci.yml", lambda t: t.replace("    - lll\n", "    - govet\n"))
            self.assert_failed(ws, "golangci-width-100")

    def test_gofmt_on_the_whole_tree_fails_the_guard_and_staged_checks(self):
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace('bad=$(gofmt -l "${GO[@]}")', "bad=$(gofmt -l .)"))
            self.assert_failed(ws, "hook-guards-go-tools", "hook-lints-staged-go")

    def test_untracked_go_files_reaching_gofmt_fail_the_guard_and_staged_checks(self):
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace("mapfile -t GO < <(filter '\\.go$')",
                                               "mapfile -t GO < <(git ls-files --cached --others -- '*.go')"))
            self.assert_failed(ws, "hook-guards-go-tools", "hook-lints-staged-go")

    def test_unguarded_linter_fails_the_guard_and_skip_checks(self):
        with workspace(good=True) as ws:
            edit(ws, HOOK, lambda t: t.replace(
                '  if have golangci-lint; then\n    golangci-lint run ./... || RC=1\n'
                '  else\n    note golangci-lint\n  fi\n',
                '  golangci-lint run ./... || RC=1\n'))
            self.assert_failed(ws, "hook-guards-go-tools", "hook-skips-missing-go-tools")

    def test_deleted_hook_fails_every_hook_check(self):
        with workspace(good=True) as ws:
            (ws / HOOK).unlink()
            self.assert_failed(ws, "hook-guards-go-tools", "hook-lints-staged-go",
                               "hook-passes-without-go-files", "hook-skips-missing-go-tools")

    def test_probe_rejects_an_unknown_scenario(self):
        script = fixture()["objective_checks"][2]["argv"][2]
        with workspace(good=True) as ws, \
                mock.patch.object(commands, "_network_prefix", return_value=[]):
            ok, detail = commands.command_succeeds(
                str(ws), [], argv=["bash", "-c", script, "hook-probe", "bogus"], timeout_s=60)
            self.assertFalse(ok)
            self.assertIn("exit=2", detail)


if __name__ == "__main__":
    unittest.main()
