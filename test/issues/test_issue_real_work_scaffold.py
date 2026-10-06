#!/usr/bin/env python3
"""The real-work fixture scaffolder and its gate (#65, #98; owner decision Q6).

`scripts/scaffold_real_work.py` turns one miner candidate plus the routine's
spec (task text, `interface_strings:`, checker selection) into a draft
fixture, validates it with the harness's own code, and gates an untrusted
`claude/scaffold-<id>` branch; `.github/workflows/routine-scaffold-gate.yml`
runs the gate from the default branch on the `workflow_run` of
`routine-scaffold-pushed.yml`. Pinned here:

  * build writes the #311 shape from a throwaway source repository built
    in-test: a stripped, trimmed seed; the merge's test file as the checker;
    the rest of the diff as solution.patch; the issue snapshot and its three
    times; `draft: true`; and it reads GitHub only through `gh api graphql`;
  * the snapshot picks the revision and title from before the first commit;
  * the spec is validated, and an answer-leak hit refuses the build
    (LEAK_POLICY) unless an interface string or the issue's own earlier text
    exempts it;
  * `check --run` is red on the seed and green with the fix, inside the cap;
  * the gate accepts only additions under `evals/real-work/<id>/` and
    rejects everything else without quoting content;
  * both workflows, parsed with PyYAML, hold the trust boundary and never
    merge or push.

Offline: a fake `gh` answers from canned JSON and the network probe is mocked
off. example.com only. Discovered and run by test/run_tests.py.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
GATE = WORKFLOWS / "routine-scaffold-gate.yml"
SIGNAL = WORKFLOWS / "routine-scaffold-pushed.yml"
REAL_WORK = REPO_ROOT / "evals" / "real-work"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "harness"))

import answer_leak  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import mine_real_work  # noqa: E402
import scaffold_real_work as scaffold  # noqa: E402

PIN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(/[^@]+)?@[0-9a-f]{40}$")
MARKER = "do-not-echo-this-marker"

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.com",
    "GIT_AUTHOR_DATE": "2026-09-01T11:00:00Z", "GIT_COMMITTER_DATE": "2026-09-01T11:00:00Z",
    "GIT_CONFIG_COUNT": "2",
    "GIT_CONFIG_KEY_0": "gc.auto", "GIT_CONFIG_VALUE_0": "0",
    "GIT_CONFIG_KEY_1": "maintenance.auto", "GIT_CONFIG_VALUE_1": "false",
}

#: A fake `gh` that answers only `api graphql`, from `$FAKE_GH_DATA`, and logs
#: every call to `$FAKE_GH_LOG`; any other verb exits 3.
FAKE_GH = r'''
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\n")
if args[:2] != ["api", "graphql"]:
    sys.stderr.write("fake gh: refused\n")
    raise SystemExit(3)
with open(os.environ["FAKE_GH_DATA"], encoding="utf-8") as handle:
    print(handle.read())
'''

MANAGED_AGENTS = ("<!-- BEGIN MANAGED SECTION -->\n> **Managed by [`_agent-guidance`].**\n"
                  "Fleet text.\n<!-- END MANAGED SECTION -->\n## Repo-specific additions\n\n"
                  "- Run tests with python3 -m unittest.\n")
BASE_FILES = {
    "AGENTS.md": MANAGED_AGENTS,
    "CLAUDE.md": "<!-- Managed by _agent-guidance -->\n@AGENTS.md\n",
    ".claude/settings.json": "{}\n",
    "skills.lock": "bundle: example\n",
    "skills/demo/SKILL.md": "# demo\n",
    "README.md": "Toy tool. See https://example.com\n",
    "tool.py": "def add(a, b):\n    return a - b\n",
    "tests/__init__.py": "",
    "tests/test_tool.py": ("import unittest\n\nfrom tool import add\n\n\n"
                           "class ToolTests(unittest.TestCase):\n"
                           "    def test_import(self):\n        self.assertTrue(callable(add))\n"),
    "data/big.txt": "x" * (110 * 1024),
    "e2e/other.spec.js": "// another spec\n",
    "e2e/helpers.js": "// kept\n",
}
FIX = "def add(a, b):\n    return a + b  # sum the two operands\n"
TEST_AFTER = BASE_FILES["tests/test_tool.py"] + (
    "\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n")
ISSUE_BODY = "The add function in tool.py returns the difference.\r\nIt should add."


def graphql(**issue_changes) -> dict:
    issue = {"title": "add() subtracts", "body": ISSUE_BODY,
             "createdAt": "2026-09-01T09:00:00Z", "lastEditedAt": None,
             "userContentEdits": {"totalCount": 0, "nodes": []},
             "timelineItems": {"totalCount": 0, "nodes": []}}
    issue.update(issue_changes)
    return {"data": {"repository": {"issue": issue, "pullRequest": {"commits": {"nodes": [
        {"commit": {"committedDate": "2026-09-01T10:00:00Z"}}]}}}}}


def spec(**changes) -> dict:
    doc = {"task_text": "add() subtracts\n\nThe add function in tool.py returns the "
                        "difference. Make it return the sum.\n",
           "interface_strings": ["add"],
           "checker": {"files": ["tests/test_tool.py"], "argv": ["python3", "-m", "unittest"],
                       "fail_to_pass": ["tests.test_tool.ToolTests.test_add"],
                       "pass_to_pass": ["tests.test_tool.ToolTests.test_import"]}}
    doc.update(changes)
    return doc


class _Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        env = mock.patch.dict(os.environ, GIT_ENV)
        env.start()
        self.addCleanup(env.stop)
        net = mock.patch("scorers.commands._network_prefix", return_value=[])
        net.start()
        self.addCleanup(net.stop)

    def git(self, repo: Path, *args) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    @staticmethod
    def write(root: Path, files: dict) -> None:
        for name, data in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(data, bytes):
                path.write_bytes(data)
            else:
                path.write_text(data, encoding="utf-8")


class _BuildCase(_Case):
    """A source repository (base, merge) and a fake `gh` on PATH."""

    def setUp(self):
        super().setUp()
        self.clone = self.tmp / "toy"
        self.clone.mkdir()
        self.git(self.clone, "init", "-q", "-b", "main")
        self.write(self.clone, BASE_FILES)
        (self.clone / "run.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
        (self.clone / "run.sh").chmod(0o755)
        (self.clone / "link").symlink_to("tool.py")
        self.git(self.clone, "add", "-A")
        self.git(self.clone, "commit", "-q", "-m", "base")
        self.base = self.git(self.clone, "rev-parse", "HEAD")
        self.write(self.clone, {"tool.py": FIX, "tests/test_tool.py": TEST_AFTER,
                                "AGENTS.md": MANAGED_AGENTS + "- add sums.\n",
                                "skills/demo/SKILL.md": "# demo, changed\n"})
        self.git(self.clone, "commit", "-q", "-am", "fix")
        self.merge = self.git(self.clone, "rev-parse", "HEAD")
        self.candidates = self.tmp / "candidates.json"
        self.candidates.write_text(json.dumps({"candidates": [{
            "key": "example__toy__7", "repo": "example/toy", "pr": 7,
            "base_sha": self.base, "merge_sha": self.merge, "base_from": "pr-base-ref-oid",
            "closing_issues": [3], "test_files": ["tests/test_tool.py"],
            "source_files": ["tool.py"]}]}), encoding="utf-8")
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text(f"#!{sys.executable}\n" + FAKE_GH, encoding="utf-8")
        (bin_dir / "gh").chmod(0o755)
        self.gh_log = self.tmp / "gh.log"
        self.gh_data = self.tmp / "gh.json"
        self.set_graphql(graphql())
        env = mock.patch.dict(os.environ, {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_LOG": str(self.gh_log), "FAKE_GH_DATA": str(self.gh_data)})
        env.start()
        self.addCleanup(env.stop)
        self.dest = self.tmp / "dest" / "evals" / "real-work"

    def set_graphql(self, doc: dict) -> None:
        self.gh_data.write_text(json.dumps(doc), encoding="utf-8")

    def build(self, **spec_changes) -> Path:
        path = self.tmp / "spec.json"
        path.write_text(json.dumps(spec(**spec_changes)), encoding="utf-8")
        return scaffold.build(self.candidates, "example__toy__7", self.clone, path, self.dest)

    def assertRefused(self, pattern: str, **spec_changes):
        with self.assertRaisesRegex(scaffold.ScaffoldError, pattern):
            self.build(**spec_changes)
        self.assertFalse((self.dest / "toy-7").exists(), "a refused build writes nothing")


class BuildTests(_BuildCase):

    def test_writes_the_fixture_shape(self):
        target = self.build()
        self.assertEqual(target, self.dest / "toy-7")
        self.assertEqual(sorted(p.name for p in target.iterdir()),
                         ["checker", "fixture.yaml", "issue-before-fix.txt", "seed",
                          "solution.patch"])
        fixture = yaml.safe_load((target / "fixture.yaml").read_text(encoding="utf-8"))
        self.assertEqual(list(fixture)[:4], ["subject", "draft", "strip_agent_context", "prompt"])
        self.assertEqual((fixture["subject"], fixture["draft"], fixture["strip_agent_context"]),
                         ("any", True, True))
        self.assertEqual(fixture["prompt"], spec()["task_text"])
        self.assertEqual(fixture["interface_strings"], ["add"])
        self.assertEqual(fixture["issue_before_fix"], "issue-before-fix.txt")
        self.assertEqual((fixture["issue_created_at"], fixture["issue_last_edited_at"],
                          fixture["first_commit_at"]),
                         ("2026-09-01T09:00:00Z", None, "2026-09-01T10:00:00Z"))
        [check] = fixture["objective_checks"]
        self.assertEqual(check, {
            "id": "hidden-tests", "type": "repo_tests",
            "description": "The pull request's own tests, hidden from the agent",
            "overlay": "checker", "argv": ["python3", "-m", "unittest"],
            "fail_to_pass": ["tests.test_tool.ToolTests.test_add"],
            "pass_to_pass": ["tests.test_tool.ToolTests.test_import"]})
        self.assertEqual((target / "issue-before-fix.txt").read_text(encoding="utf-8"),
                         "add() subtracts\n\nThe add function in tool.py returns the "
                         "difference.\nIt should add.\n")
        text = (target / "fixture.yaml").read_text(encoding="utf-8")
        self.assertIn(f"base  {self.base}", text)
        self.assertIn(f"merge {self.merge}", text)
        self.assertIn("https://github.com/example/toy/pull/7", text)
        self.assertIn("written by a model", text)

    def test_seed_is_the_base_tree_stripped_and_trimmed(self):
        seed = self.build() / "seed"
        for gone in (".claude", "skills.lock", "skills", "data/big.txt", "link",
                     "e2e/other.spec.js"):
            self.assertFalse(os.path.lexists(seed / gone), gone)
        self.assertEqual((seed / "AGENTS.md").read_text(encoding="utf-8"),
                         MANAGED_AGENTS[MANAGED_AGENTS.index("## Repo-specific"):])
        self.assertEqual((seed / "CLAUDE.md").read_text(encoding="utf-8").strip(), "@AGENTS.md")
        self.assertEqual((seed / "tool.py").read_text(encoding="utf-8"), BASE_FILES["tool.py"])
        self.assertEqual((seed / "tests/test_tool.py").read_text(encoding="utf-8"),
                         BASE_FILES["tests/test_tool.py"])
        self.assertTrue((seed / "e2e/helpers.js").is_file())
        self.assertTrue(os.access(seed / "run.sh", os.X_OK), "git's executable bit is kept")
        header = (seed.parent / "fixture.yaml").read_text(encoding="utf-8").split("\n\n")[0]
        self.assertIn("# Trimmed from the seed: data/big.txt, link, skills.", header)
        self.assertIn("# Also every e2e spec but the checker's own (1 trimmed).", header)

    def test_a_plugin_manifest_gets_the_neutral_description_in_place(self):
        seed = self.tmp / "manifest-seed"
        text = ('{\n  "name": "cms-platform",\n  "description": "Skills: a, b and c.",\n'
                '  "author": { "name": "example" }\n}\n')
        self.write(seed, {"plugin.json": text})
        scaffold.trim_seed(seed, [], [], "cms-platform")
        self.assertEqual((seed / "plugin.json").read_text(encoding="utf-8"), text.replace(
            "Skills: a, b and c.", scaffold.NEUTRAL_MANIFEST_DESCRIPTIONS["cms-platform"]))
        self.write(seed, {"plugin.json": text})
        with self.assertRaisesRegex(scaffold.ScaffoldError, "no entry for toy"):
            scaffold.trim_seed(seed, [], [], "toy")

    def test_checker_is_the_merge_commits_file_and_the_patch_is_the_rest(self):
        target = self.build()
        checker = target / "checker" / "tests" / "test_tool.py"
        self.assertEqual(scaffold._git(self.clone, "hash-object", str(checker)).decode().strip(),
                         self.git(self.clone, "rev-parse", f"{self.merge}:tests/test_tool.py"))
        self.assertEqual([p.relative_to(target / "checker").as_posix()
                          for p in (target / "checker").rglob("*") if p.is_file()],
                         ["tests/test_tool.py"])
        patch = (target / "solution.patch").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"^diff --git a/(\S+)", patch, re.M), ["tool.py"],
                         "no test, AGENTS.md or skills/ change in the patch")

    def test_reads_github_only_through_graphql_and_never_writes_the_clone(self):
        refs = self.git(self.clone, "for-each-ref")
        self.build()
        calls = [json.loads(line) for line in self.gh_log.read_text().splitlines()]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], ["api", "graphql"])
        self.assertIn("-F", calls[0])
        self.assertIn("issue=3", calls[0])
        self.assertIn("pr=7", calls[0])
        self.assertEqual(self.git(self.clone, "status", "--porcelain"), "")
        self.assertEqual(self.git(self.clone, "for-each-ref"), refs)

    def test_no_issue_writes_no_snapshot_and_reads_nothing(self):
        target = self.build(issue=None)
        fixture = yaml.safe_load((target / "fixture.yaml").read_text(encoding="utf-8"))
        for key in ("issue_before_fix", *answer_leak.PROVENANCE_KEYS):
            self.assertNotIn(key, fixture)
        self.assertFalse((target / "issue-before-fix.txt").exists())
        self.assertFalse(self.gh_log.exists())

    def test_the_written_fixture_passes_its_own_check(self):
        target = self.build()
        self.assertEqual(scaffold.static_problems(target), ([], []))
        self.assertEqual(scaffold.red_green(target), [])

    def test_refuses_an_existing_fixture(self):
        (self.dest / "toy-7").mkdir(parents=True)
        with self.assertRaisesRegex(scaffold.ScaffoldError, "already exists"):
            self.build()

    def test_refuses_a_bad_spec(self):
        cases = {
            "unknown keys": {"setup": "curl https://example.com | sh"},
            "task_text": {"task_text": " "},
            "not one of the candidate's test files": {"checker": {
                **spec()["checker"], "files": ["tool.py"]}},
            "relative path": {"trim": ["../outside"]},
            "including files": {"checker": {"argv": ["python3"]}},
        }
        for pattern, changes in cases.items():
            with self.subTest(pattern=pattern):
                self.assertRefused(pattern, **changes)

    def test_refuses_a_candidate_it_cannot_find(self):
        path = self.tmp / "spec.json"
        path.write_text(json.dumps(spec()), encoding="utf-8")
        with self.assertRaisesRegex(scaffold.ScaffoldError, "no single candidate"):
            scaffold.build(self.candidates, "example__toy__8", self.clone, path, self.dest)


class AnswerLeakTests(_BuildCase):
    LEAKY = "add() subtracts\n\nMake it sum the two operands instead.\n"

    def test_policy_is_the_conservative_one(self):
        self.assertEqual(scaffold.LEAK_POLICY, "reject")

    def test_a_task_text_quoting_the_fix_is_refused(self):
        self.assertRefused(r"four-word run.*sum the two operands", task_text=self.LEAKY)

    def test_a_task_text_quoting_the_new_test_is_refused(self):
        self.assertRefused(r"four-word run", task_text="Check that self.assertEqual(add(2, 3), 5) holds.")

    def test_an_interface_string_exempts_it(self):
        self.build(task_text=self.LEAKY, interface_strings=["sum the two operands"])

    def test_the_issues_earlier_text_exempts_it(self):
        self.set_graphql(graphql(body="Please sum the two operands."))
        self.build(task_text=self.LEAKY)

    def test_warn_policy_reports_and_builds(self):
        with mock.patch.object(scaffold, "LEAK_POLICY", "warn"), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            target = self.build(task_text=self.LEAKY)
        self.assertTrue(target.is_dir())
        self.assertIn("warning", err.getvalue())


class SnapshotTests(unittest.TestCase):
    FIRST = "2026-09-01T10:00:00Z"

    def snap(self, **changes):
        return scaffold.snapshot_from_graphql(graphql(**changes))

    @staticmethod
    def edits(*pairs):
        nodes = [{"editedAt": at, "deletedAt": None, "diff": text} for at, text in pairs]
        return {"totalCount": len(nodes), "nodes": list(reversed(nodes))}

    def test_never_edited(self):
        got = self.snap()
        self.assertIsNone(got["issue_last_edited_at"])
        self.assertTrue(got["text"].startswith("add() subtracts\n\nThe add function"))

    def test_edited_before_the_first_commit_takes_that_revision(self):
        got = self.snap(lastEditedAt="2026-09-01T12:00:00Z", body="after", userContentEdits=self.edits(
            ("2026-09-01T09:00:00Z", "original"), ("2026-09-01T09:30:00Z", "earlier edit"),
            ("2026-09-01T12:00:00Z", "after")))
        self.assertEqual(got["issue_last_edited_at"], "2026-09-01T09:30:00Z")
        self.assertEqual(got["text"], "add() subtracts\n\nearlier edit\n")

    def test_edited_only_after_takes_the_original_with_a_null_time(self):
        got = self.snap(lastEditedAt="2026-09-01T12:00:00Z", body="after", userContentEdits=self.edits(
            ("2026-09-01T09:00:00Z", "original"), ("2026-09-01T12:00:00Z", "after")))
        self.assertIsNone(got["issue_last_edited_at"])
        self.assertEqual(got["text"], "add() subtracts\n\noriginal\n")

    def test_a_title_renamed_after_the_first_commit_reads_back(self):
        got = self.snap(title="Now renamed", timelineItems={"totalCount": 2, "nodes": [
            {"createdAt": "2026-09-01T09:10:00Z", "previousTitle": "first", "currentTitle": "Old"},
            {"createdAt": "2026-09-02T00:00:00Z", "previousTitle": "Old", "currentTitle": "Now renamed"}]})
        self.assertTrue(got["text"].startswith("Old\n\n"))

    def test_the_result_passes_the_harness_provenance_check(self):
        for got in (self.snap(), self.snap(lastEditedAt="2026-09-01T09:30:00Z",
                                           userContentEdits=self.edits(
                                               ("2026-09-01T09:00:00Z", "o"),
                                               ("2026-09-01T09:30:00Z", "e")))):
            with self.subTest(got=got["issue_last_edited_at"]):
                answer_leak._check_provenance({"issue_before_fix": "x", **{
                    k: got[k] for k in answer_leak.PROVENANCE_KEYS}})

    def test_refusals(self):
        cases = {
            "created after": {"createdAt": "2026-09-01T11:00:00Z"},
            "no revision": {"lastEditedAt": "2026-09-01T12:00:00Z", "userContentEdits": self.edits(
                ("2026-09-01T11:00:00Z", "late"))},
            "deleted": {"lastEditedAt": "2026-09-01T09:30:00Z", "userContentEdits": {
                "totalCount": 1, "nodes": [{"editedAt": "2026-09-01T09:30:00Z",
                                            "deletedAt": "2026-09-02T00:00:00Z", "diff": None}]}},
            "more revisions": {"userContentEdits": {"totalCount": 101, "nodes": []}},
            "reports an edit": {"lastEditedAt": "2026-09-01T09:30:00Z"},
            "not an ISO-8601": {"createdAt": "yesterday"},
        }
        for pattern, changes in cases.items():
            with self.subTest(pattern=pattern):
                with self.assertRaisesRegex(scaffold.ScaffoldError, pattern):
                    self.snap(**changes)


class RedGreenTests(_BuildCase):

    def test_a_patch_that_does_not_fix_is_caught(self):
        target = self.build()
        patch = target / "solution.patch"
        patch.write_text(patch.read_text(encoding="utf-8").replace("a + b", "a * b"),
                         encoding="utf-8")
        problems = scaffold.red_green(target)
        self.assertEqual(len(problems), 1)
        self.assertRegex(problems[0], r"^green: wanted fail_to_pass=1/1")

    def test_a_checker_green_on_the_seed_is_caught(self):
        target = self.build()
        (target / "seed" / "tool.py").write_text(FIX, encoding="utf-8")
        problems = scaffold.red_green(target)
        self.assertTrue(any(p.startswith("red: wanted fail_to_pass=0/1") for p in problems),
                        problems)

    def test_over_the_cap_is_caught(self):
        target = self.build()
        ticks = iter([0.0, 61.0, 100.0, 100.5])
        problems = scaffold.red_green(target, clock=lambda: next(ticks))
        self.assertEqual(problems, ["red: scoring took 61.0 s, over the 60 s cap"])

    def test_cli_check_run_exit_codes(self):
        target = self.build()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(scaffold.main(["check", "--fixture", str(target), "--run"]), 0)
        self.assertIn("check: 0 problem(s)", out.getvalue())
        (target / "solution.patch").write_text("not a patch\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(scaffold.main(["check", "--fixture", str(target), "--run"]), 1)
        self.assertIn("solution.patch does not apply", out.getvalue())


class CommittedFixturesTests(unittest.TestCase):

    def test_the_committed_fixtures_pass_the_static_check(self):
        # The #311 fixtures were written by hand; the scaffold's static check
        # must accept them, so its rules are the fixtures' own.
        names = sorted(p.name for p in REAL_WORK.iterdir() if (p / "fixture.yaml").is_file())
        self.assertGreaterEqual(len(names), 3)
        for name in names:
            with self.subTest(fixture=name):
                self.assertEqual(scaffold.static_problems(REAL_WORK / name, detail=True), ([], []))

    def test_the_miner_never_mines_a_scaffold_branch(self):
        self.assertTrue(mine_real_work.is_bot({"headRefName": "claude/scaffold-toy-7"}))
        self.assertFalse(mine_real_work.is_bot({"headRefName": "claude/fix-toy"}))


class _GateCase(_BuildCase):
    """A scratch skills-evals repository with a `main` and a scaffold branch."""

    BRANCH = "claude/scaffold-toy-7"

    def setUp(self):
        super().setUp()
        self.fixture = self.build()
        self.repo = self.tmp / "skills-evals"
        self.repo.mkdir()
        self.git(self.repo, "init", "-q", "-b", "main")
        self.write(self.repo, {"README.md": "see https://example.com\n",
                               ".github/workflows/ci.yml": "name: CI\n",
                               "evals/real-work/other-1/fixture.yaml": "subject: any\n"})
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-q", "-m", "main")
        self.git(self.repo, "checkout", "-q", "-b", self.BRANCH)
        self.where = self.repo / "evals" / "real-work" / "toy-7"

    def commit(self, mutate=None) -> str:
        shutil.copytree(self.fixture, self.where, symlinks=True)
        if mutate:
            mutate(self.where)
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-q", "--allow-empty", "-m", "scaffold")
        return self.git(self.repo, "rev-parse", "HEAD")

    def gate(self, branch=None, expect=None):
        branch = branch or self.BRANCH
        return scaffold.gate(str(self.repo), "main", self.BRANCH, branch, expect,
                             self.tmp / "out")

    def assertRejected(self, pattern, mutate=None, **kwargs):
        self.commit(mutate)
        with self.assertRaisesRegex(ingest.Rejected, pattern) as caught:
            self.gate(**kwargs)
        self.assertNotIn(MARKER, str(caught.exception))


class GateTests(_GateCase):

    def test_accepts_the_scaffold_and_writes_exactly_its_files(self):
        tip = self.commit()
        result = self.gate(expect=tip)
        self.assertEqual(result["fixture_id"], "toy-7")
        self.assertEqual(result["sha"], tip)
        out = self.tmp / "out" / "toy-7"
        written = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
        wanted = sorted(p.relative_to(self.fixture).as_posix()
                        for p in self.fixture.rglob("*") if p.is_file())
        self.assertEqual(written, wanted)
        self.assertEqual(int(result["files"]), len(wanted))
        self.assertTrue(os.access(out / "seed" / "run.sh", os.X_OK))

    def test_rejects_a_change_outside_the_fixture(self):
        def touch_main(where):
            (where.parents[2] / "README.md").write_text("changed\n", encoding="utf-8")
        self.assertRejected("modified or deleted", touch_main)

    def test_rejects_an_added_workflow(self):
        def add_workflow(where):
            self.write(where.parents[2], {".github/workflows/evil.yml": "name: x\n"})
        self.assertRejected("not under 'evals/real-work/toy-7/'", add_workflow)

    def test_rejects_a_modified_existing_fixture(self):
        def edit_other(where):
            (where.parent / "other-1" / "fixture.yaml").write_text("draft: false\n")
        self.assertRejected("modified or deleted", edit_other)

    def test_rejects_a_fixture_id_that_disagrees_with_the_branch(self):
        self.commit()
        with self.assertRaisesRegex(ingest.Rejected, "not under 'evals/real-work/toy-8/'"):
            scaffold.gate(str(self.repo), "main", self.BRANCH, "claude/scaffold-toy-8", None,
                          self.tmp / "out")

    def test_rejects_a_symlink(self):
        self.assertRejected("mode 120000", lambda w: (w / "seed" / "ln").symlink_to("tool.py"))

    def test_rejects_an_executable_outside_seed_and_checker(self):
        self.assertRejected("executable outside", lambda w: (w / "solution.patch").chmod(0o755))

    def test_rejects_an_unknown_top_level_file(self):
        self.assertRejected("not a file a scaffold writes",
                            lambda w: (w / "setup.sh").write_text("echo\n"))

    def test_rejects_a_fixture_that_is_not_a_draft(self):
        def undraft(where):
            path = where / "fixture.yaml"
            path.write_text(path.read_text().replace("draft: true", "draft: false"))
        self.assertRejected("not `draft: true`", undraft)

    def test_rejects_a_setup_key_without_quoting_it(self):
        def add_setup(where):
            path = where / "fixture.yaml"
            path.write_text(path.read_text() + f"setup: echo {MARKER}\n")
        self.assertRejected(r"keys a scaffold may not: 1 key\(s\)", add_setup)

    def test_rejects_an_unstripped_seed(self):
        self.assertRejected(r"seed: \.claude is present",
                            lambda w: self.write(w / "seed", {".claude/settings.json": "{}\n"}))

    def test_rejects_an_answer_leak_without_quoting_it(self):
        def leak(where):
            path = where / "fixture.yaml"
            path.write_text(path.read_text().replace(
                "Make it return the sum.", f"Make it sum the two operands {MARKER}."))
        self.assertRejected(r"shares 1 four-word run\(s\)", leak)

    def test_rejects_an_oversized_seed_file(self):
        self.assertRejected("over the seed's size cap",
                            lambda w: self.write(w / "seed", {"blob.txt": "y" * (101 * 1024)}))

    def test_rejects_bad_branches_and_moves(self):
        self.commit()
        for branch in ("claude/eval-20261006T194256Z-f944ea", "claude/scaffold-", "scaffold/toy-7",
                       "claude/scaffold-toy", "claude/scaffold-../x-1"):
            with self.subTest(branch=branch):
                with self.assertRaisesRegex(ingest.Rejected, "branch name"):
                    self.gate(branch=branch)
        with self.assertRaisesRegex(ingest.Rejected, "moved"):
            self.gate(expect="0" * 40)

    def test_cli_never_quotes_content(self):
        def leak(where):
            path = where / "fixture.yaml"
            path.write_text(path.read_text().replace(
                "Make it return the sum.", f"Make it sum the two operands {MARKER}."))
        self.commit(leak)
        with contextlib.redirect_stderr(io.StringIO()) as err, \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = scaffold.main(["gate", "--repo", str(self.repo), "--base", "main",
                                  "--source", self.BRANCH, "--branch", self.BRANCH,
                                  "--out", str(self.tmp / "out")])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn(MARKER, err.getvalue())
        self.assertNotIn("operands", err.getvalue())


class ResolveTests(unittest.TestCase):

    def resolve(self, name, event):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(event, handle)
        self.addCleanup(os.unlink, handle.name)
        return ingest.resolve(name, handle.name, scaffold.BRANCH_RE, "claude/scaffold-<id>")

    def push(self, branch):
        return {"repository": {"full_name": "example/skills-evals"},
                "workflow_run": {"event": "push", "head_branch": branch, "head_sha": "a" * 40,
                                 "head_repository": {"full_name": "example/skills-evals"}}}

    def test_a_same_repository_push_and_a_dispatch(self):
        self.assertEqual(self.resolve("workflow_run", self.push("claude/scaffold-cms-platform-221")),
                         {"branch": "claude/scaffold-cms-platform-221", "sha": "a" * 40,
                          "fixture_id": "cms-platform-221"})
        self.assertEqual(self.resolve("workflow_dispatch",
                                      {"inputs": {"branch": "claude/scaffold-_agent-guidance-196"}}),
                         {"branch": "claude/scaffold-_agent-guidance-196", "sha": "",
                          "fixture_id": "_agent-guidance-196"})

    def test_rejections(self):
        for event in (self.push("claude/eval-20261006T194256Z-f944ea"),
                      self.push("claude/scaffold-x-1\n::warning::")):
            with self.assertRaisesRegex(ingest.Rejected, "claude/scaffold-<id>"):
                self.resolve("workflow_run", event)

    def test_ingest_keeps_its_own_pattern(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(self.push("claude/scaffold-toy-7"), handle)
        self.addCleanup(os.unlink, handle.name)
        with self.assertRaisesRegex(ingest.Rejected, "claude/eval-<run id>"):
            ingest.resolve("workflow_run", handle.name)


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def triggers(doc: dict):
    return doc.get("on", doc.get(True))


def run_blocks(doc: dict) -> list[tuple[str, str]]:
    return [(name, step["run"]) for name, job in doc["jobs"].items()
            for step in job.get("steps") or [] if "run" in step]


def uses_nodes(node):
    if isinstance(node, yaml.MappingNode):
        for key, value in node.value:
            if isinstance(key, yaml.ScalarNode) and key.value == "uses":
                yield value
            yield from uses_nodes(value)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            yield from uses_nodes(item)


class WorkflowShapeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gate = load(GATE)
        cls.signal = load(SIGNAL)

    def test_the_gate_runs_on_workflow_run_of_the_signal(self):
        on = triggers(self.gate)
        self.assertEqual(set(on), {"workflow_run", "workflow_dispatch"})
        self.assertEqual(on["workflow_run"]["workflows"], [self.signal["name"]])
        self.assertEqual(on["workflow_run"]["types"], ["completed"])
        self.assertEqual(on["workflow_run"]["branches"], ["claude/scaffold-*"])
        self.assertEqual(set(on["workflow_dispatch"]["inputs"]), {"branch"})

    def test_signal_is_a_filtered_push_with_no_reach(self):
        on = triggers(self.signal)
        self.assertEqual(set(on), {"push"})
        self.assertEqual(on["push"]["branches"], ["claude/scaffold-*"])
        self.assertEqual(on["push"]["paths"], [f"{scaffold.REAL_WORK_ROOT}/**"])
        self.assertEqual(self.signal["permissions"], {})
        for job in self.signal["jobs"].values():
            self.assertNotIn("permissions", job)
            for step in job["steps"]:
                self.assertNotIn("uses", step, "the signal checks nothing out")

    def test_permissions_are_split_and_minimal(self):
        self.assertEqual(self.gate["permissions"], {})
        self.assertEqual(set(self.gate["jobs"]), {"validate", "draft-pr"})
        self.assertEqual(self.gate["jobs"]["validate"]["permissions"], {"contents": "read"})
        self.assertEqual(self.gate["jobs"]["draft-pr"]["permissions"],
                         {"contents": "read", "pull-requests": "write"})
        self.assertEqual(self.gate["jobs"]["draft-pr"]["needs"], "validate")

    def test_the_writing_job_never_touches_the_branch(self):
        steps = self.gate["jobs"]["draft-pr"]["steps"]
        self.assertFalse([s for s in steps if "uses" in s], "no checkout in the PR job")
        env = steps[0]["env"]
        for key in ("BRANCH", "FIXTURE_ID", "SHA"):
            self.assertTrue(env[key].startswith("${{ needs.validate.outputs."), key)

    def test_only_the_default_branch_copy_runs(self):
        self.assertIn("github.ref == format('refs/heads/{0}', "
                      "github.event.repository.default_branch)",
                      self.gate["jobs"]["validate"]["if"])
        self.assertIn("github.event.workflow_run.conclusion == 'success'",
                      self.gate["jobs"]["validate"]["if"])

    def test_no_pull_request_trigger_and_no_concurrency_group(self):
        for doc in (self.gate, self.signal):
            self.assertNotIn("pull_request", triggers(doc))
            self.assertNotIn("pull_request_target", triggers(doc))
            self.assertNotIn("concurrency", doc)
            for job in doc["jobs"].values():
                self.assertNotIn("concurrency", job)

    def test_every_uses_is_a_bare_sha_already_pinned_elsewhere(self):
        pinned = set()
        for other in WORKFLOWS.glob("*.yml"):
            if other not in (GATE, SIGNAL):
                pinned |= {n.value for n in uses_nodes(yaml.compose(other.read_text(encoding="utf-8")))}
        text = GATE.read_text(encoding="utf-8")
        lines = text.splitlines()
        found = list(uses_nodes(yaml.compose(text)))
        self.assertEqual(len(found), 2)
        for node in found:
            with self.subTest(uses=node.value):
                self.assertRegex(node.value, PIN)
                self.assertEqual(lines[node.end_mark.line][node.end_mark.column:].strip(), "",
                                 "a pin carries no trailing comment")
                self.assertIn(node.value, pinned)

    def test_no_expressions_in_run_blocks(self):
        for doc in (self.gate, self.signal):
            blocks = run_blocks(doc)
            self.assertTrue(blocks)
            for job, body in blocks:
                with self.subTest(job=job, body=body[:40]):
                    self.assertNotIn("${{", body, "pass values through env, never inline")

    def test_it_opens_only_a_labelled_draft_and_never_merges_or_pushes(self):
        bodies = "\n".join(body for _, body in run_blocks(self.gate))
        for verb in (r"\bgh\s+pr\s+(merge|review|close|ready)\b", r"\bgit\s+push\b",
                     r"\bgit\s+merge\b", r"--auto\b", r"\bgh\s+api\s+[^\n]*-X\b",
                     r"\b(delete|DELETE)\b"):
            with self.subTest(verb=verb):
                self.assertIsNone(re.search(verb, bodies))
        [create] = [line for line in bodies.splitlines() if "gh pr create" in line]
        tail = bodies[bodies.index("gh pr create"):]
        self.assertIn("--draft", create)
        self.assertIn('--label "$LABEL"', tail)
        self.assertEqual(self.gate["jobs"]["draft-pr"]["steps"][0]["env"]["LABEL"],
                         scaffold.DRAFT_LABEL)

    def test_the_pr_body_has_no_closing_keyword(self):
        [(_, body)] = [b for b in run_blocks(self.gate) if b[0] == "draft-pr"]
        self.assertIsNone(re.search(r"\b(close[sd]?|fix(e[sd])?|resolve[sd]?)\s+(#|https://)",
                                    body, re.I))
        self.assertIn("Part of https://github.com/Adam-S-Daniel/skills-evals/issues/65", body)

    def test_the_gate_step_runs_this_script(self):
        steps = {s.get("id"): s for s in self.gate["jobs"]["validate"]["steps"]}
        self.assertIn("scripts/scaffold_real_work.py resolve", steps["resolve"]["run"])
        self.assertIn("scripts/scaffold_real_work.py gate", steps["gate"]["run"])
        [checkout] = [s for s in self.gate["jobs"]["validate"]["steps"]
                      if str(s.get("uses", "")).startswith("actions/checkout@")]
        self.assertEqual(checkout["with"]["ref"], "${{ github.event.repository.default_branch }}")
        self.assertIs(checkout["with"]["persist-credentials"], False)

    def test_the_guards_can_fail(self):
        # Negative controls on the helpers the shape tests lean on.
        self.assertIsNone(PIN.match("actions/checkout@v4"))
        bad = {"jobs": {"j": {"steps": [{"run": "echo ${{ inputs.x }}"}]}}}
        self.assertIn("${{", run_blocks(bad)[0][1])
        self.assertIsNotNone(re.search(r"\bgh\s+pr\s+(merge|review|close|ready)\b",
                                       "gh pr merge --merge 1"))


if __name__ == "__main__":
    unittest.main()
