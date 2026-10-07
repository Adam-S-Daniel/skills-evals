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
  * `snapshot --candidate` (run by routine-eval-fire.yml, where GraphQL
    works) writes it as JSON, the closing issue read through REST as the
    miner reads it; `build --issue-snapshot` takes that JSON, validated
    strictly, and reads no GitHub; the gate recomputes it and rejects a
    branch whose `issue-before-fix.txt` or times differ;
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

#: A fake `gh` that logs every call to `$FAKE_GH_LOG` and answers, from the
#: JSON object in `$FAKE_GH_DATA`, only these reads: `api graphql` (the
#: snapshot query, "graphql"), and the REST reads `api repos/<o>/<n>/pulls/<n>`
#: ("pull"), `api repos/<o>/<n>/issues/<n>` ("issues", by number; a missing
#: one is a 404) and `api repos/<o>/<n>` ("repo"). A key holding an integer
#: exits with it, as a refused read does; any other verb exits 3. With
#: `$FAKE_GH_GRAPHQL_403` set it answers GraphQL as a Claude Code cloud
#: session does.
FAKE_GH = r'''
import json, os, re, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\n")
with open(os.environ["FAKE_GH_DATA"], encoding="utf-8") as handle:
    data = json.load(handle)
rest = args[1] if len(args) == 2 and args[0] == "api" else ""
if args[:2] == ["api", "graphql"]:
    if os.environ.get("FAKE_GH_GRAPHQL_403"):
        sys.stderr.write("HTTP 403: GitHub GraphQL is not available from Claude Code sessions; "
                         "use the REST API (gh api repos/{owner}/{repo}/...)\n")
        raise SystemExit(1)
    answer = data["graphql"]
elif re.fullmatch(r"repos/[^/]+/[^/]+/pulls/[0-9]+", rest):
    answer = data["pull"]
elif re.fullmatch(r"repos/[^/]+/[^/]+/issues/[0-9]+", rest):
    answer = data["issues"].get(rest.rsplit("/", 1)[1])
    if answer is None:
        sys.stderr.write("gh: Not Found (HTTP 404)\n")
        raise SystemExit(1)
elif re.fullmatch(r"repos/[^/]+/[^/]+", rest):
    answer = data["repo"]
else:
    sys.stderr.write("fake gh: refused\n")
    raise SystemExit(3)
if isinstance(answer, int):
    sys.stderr.write("fake gh: HTTP 502\n")
    raise SystemExit(answer)
print(json.dumps(answer))
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


def closing(*numbers, repo="example/toy") -> dict:
    """The REST answers for a pull request whose body closes `numbers`: each
    number reads back as an issue of `repo` (another repository's issue does
    not count, as GitHub's own linking does not)."""
    return {"issues": {str(n): {"html_url": f"https://github.com/{repo}/issues/{n}"}
                       for n in numbers},
            "body": " ".join(f"Fixes #{n}." for n in numbers) or "No issue."}


def pull(number=7, merged_at="2026-09-02T00:00:00Z", body="Fixes #3.", base="main") -> dict:
    return {"number": number, "merged_at": merged_at, "body": body, "base": {"ref": base}}


def rest(*numbers, number=7, issue_repo="example/toy", full_name="example/toy",
         **pull_changes) -> dict:
    """The fake gh's REST answers: the pull request closing `numbers`, and the
    repository as GitHub names it (`full_name`, which a rename redirects)."""
    found = closing(*numbers, repo=issue_repo)
    return {"pull": pull(number, body=found["body"], **pull_changes), "issues": found["issues"],
            "repo": {"default_branch": "main", "full_name": full_name}}


#: The fleet the tests pin to, as `_agent-guidance` writes it: names in
#: repos.yml's cron_coverage.fleet, owners in sync.yml's SYNC_OWNERS.
FLEET_NAMES = ["toy", "_agent-guidance"]
FLEET_OWNERS = ["example", "Adam-S-Daniel"]


def write_fleet(root: Path, names=FLEET_NAMES, owners=FLEET_OWNERS) -> tuple[Path, Path]:
    registry = root / "repos.yml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(yaml.safe_dump({"cron_coverage": {"fleet": list(names)}}),
                        encoding="utf-8")
    sync = root / ".github" / "workflows" / "sync.yml"
    sync.parent.mkdir(parents=True, exist_ok=True)
    sync.write_text(yaml.safe_dump({"jobs": {"sync": {"env": {"SYNC_OWNERS": " ".join(owners)}}}}),
                    encoding="utf-8")
    return registry, sync


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
        self.registry, self.sync = write_fleet(self.tmp / "_agent-guidance")
        self.fleet = (list(FLEET_NAMES), list(FLEET_OWNERS))

    def fleet_args(self) -> list[str]:
        return ["--registry", str(self.registry), "--sync-workflow", str(self.sync)]

    def set_graphql(self, doc: dict) -> None:
        self.set_gh(graphql=doc)

    def set_gh(self, **answers) -> None:
        """Replace some of the fake gh's answers, keeping the others."""
        data = (json.loads(self.gh_data.read_text(encoding="utf-8"))
                if self.gh_data.exists() else rest(3))
        data.update(answers)
        self.gh_data.write_text(json.dumps(data), encoding="utf-8")

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

    def test_without_graphql_the_snapshot_gap_is_named_and_nothing_is_written(self):
        # s27 (2026-10-06): the routine runs in a Claude Code cloud session,
        # where every GitHub GraphQL request is refused with HTTP 403, and an
        # issue's body revisions (userContentEdits) have no REST read. The
        # build stops naming that gap instead of a bare `gh` failure, and never
        # falls back to the issue's current body.
        with mock.patch.dict(os.environ, {"FAKE_GH_GRAPHQL_403": "1"}):
            with self.assertRaises(scaffold.ScaffoldError) as caught:
                self.build()
        message = str(caught.exception)
        self.assertRegex(message, r"needs GitHub GraphQL")
        self.assertIn("userContentEdits", message)
        self.assertIn("not available", message)
        self.assertNotIn("Claude Code sessions", message, "status only, never gh's text")
        self.assertFalse((self.dest / "toy-7").exists())

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


def precomputed(**changes) -> dict:
    """The fire workflow's `issue_snapshot` for the toy candidate's issue 3."""
    doc = {"repo": "example/toy", "pr": 7, "issue": 3, "title": "add() subtracts",
           "body": ISSUE_BODY, "issue_created_at": "2026-09-01T09:00:00Z",
           "issue_last_edited_at": None, "first_commit_at": "2026-09-01T10:00:00Z"}
    doc.update(changes)
    return doc


class PrecomputedSnapshotTests(_BuildCase):
    """Routine sessions have no GraphQL (#322), so routine-eval-fire.yml
    computes the snapshot with `snapshot --candidate` and the routine passes it
    to `build --issue-snapshot` (Adam, 2026-10-06: "Fire workflow precomputes
    (Recommended)")."""

    def snapshot(self, key="example__toy__7"):
        out = self.tmp / "snap" / "issue-snapshot.json"
        out.parent.mkdir(exist_ok=True)
        out.unlink(missing_ok=True)
        with contextlib.redirect_stdout(io.StringIO()) as stdout, \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = scaffold.main(["snapshot", "--candidate", key, "--out", str(out),
                                  *self.fleet_args()])
        doc = json.loads(out.read_text(encoding="utf-8")) if out.exists() else "absent"
        return code, doc, stdout.getvalue(), stderr.getvalue()

    def build_with(self, doc, raw=None, **spec_changes) -> Path:
        snap = self.tmp / "issue-snapshot.json"
        snap.write_text(raw if raw is not None else json.dumps(doc), encoding="utf-8")
        path = self.tmp / "spec.json"
        path.write_text(json.dumps(spec(**spec_changes)), encoding="utf-8")
        return scaffold.build(self.candidates, "example__toy__7", self.clone, path, self.dest,
                              issue_snapshot=snap)

    def refused_with(self, pattern, doc, raw=None, **spec_changes):
        with self.assertRaisesRegex(scaffold.ScaffoldError, pattern):
            self.build_with(doc, raw, **spec_changes)
        self.assertFalse((self.dest / "toy-7").exists(), "a refused build writes nothing")

    def test_snapshot_writes_the_payload_and_prints_no_content(self):
        code, doc, out, err = self.snapshot()
        self.assertEqual(code, 0, err)
        self.assertEqual(doc, precomputed())
        self.assertEqual(list(doc), list(scaffold.SNAPSHOT_FIELDS))
        self.assertEqual(out, "issue_snapshot=issue 3\n")
        self.assertNotIn("subtracts", out + err)
        # REST for the pull request and its closing issue, as the miner reads
        # them (#322); GraphQL only for the snapshot itself.
        calls = [json.loads(line) for line in self.gh_log.read_text().splitlines()]
        self.assertEqual(calls[:3], [["api", "repos/example/toy/pulls/7"],
                                     ["api", "repos/example/toy"],
                                     ["api", "repos/example/toy/issues/3"]])
        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[3][:2], ["api", "graphql"])
        self.assertIn("pr=7", calls[3])
        self.assertIn("issue=3", calls[3])

    def test_snapshot_key_with_an_underscore_repository(self):
        self.set_gh(**rest(number=136, full_name="Adam-S-Daniel/_agent-guidance"))
        code, doc, out, err = self.snapshot("Adam-S-Daniel___agent-guidance__136")
        self.assertEqual((code, doc, out), (0, None, "issue_snapshot=none\n"), err)
        calls = [json.loads(line) for line in self.gh_log.read_text().splitlines()]
        self.assertEqual(calls[0], ["api", "repos/Adam-S-Daniel/_agent-guidance/pulls/136"])

    def test_no_closing_issue_is_null(self):
        self.set_gh(**rest())
        code, doc, out, _ = self.snapshot()
        self.assertEqual((code, doc, out), (0, None, "issue_snapshot=none\n"))
        self.assertEqual(len(self.gh_log.read_text().splitlines()), 2, "no snapshot read")

    def test_snapshot_refusals_write_nothing(self):
        cases = {
            "several issues": rest(3, 4),
            "closing issues read failed": {**rest(3), "issues": {"3": 4}},
            "not a merged pull request": rest(3, merged_at=None),
            "pull request read failed": {"pull": 4},
            "snapshot read failed": {"graphql": 4},
            "created after": {"graphql": graphql(createdAt="2026-09-01T11:00:00Z")},
        }
        for pattern, answers in cases.items():
            with self.subTest(pattern=pattern):
                self.gh_data.unlink()
                self.set_gh(**{"graphql": graphql(), **rest(3), **answers})
                code, doc, out, err = self.snapshot()
                self.assertEqual((code, doc, out), (2, "absent", ""))
                self.assertRegex(err, pattern)

    def test_only_this_repositorys_issue_into_the_default_branch_closes(self):
        for answers in ({**rest(3), "pull": pull(body="Fixes example/other#3.")},
                        rest(3, issue_repo="example/other"),
                        rest(3, base="release")):
            with self.subTest(answers=answers["pull"]):
                self.set_gh(**answers)
                self.assertEqual(self.snapshot()[1], None)

    def test_a_repository_outside_the_fleet_reads_nothing(self):
        # Adam, 2026-10-06: "Pin to fleet owners (Recommended)". The pin is
        # _agent-guidance's own registry, as the miner reads it.
        for key, pattern in (("attacker__toy__7", "not a fleet owner"),
                             ("example__other__7", "not in the fleet registry")):
            with self.subTest(key=key):
                self.gh_log.unlink(missing_ok=True)
                code, doc, out, err = self.snapshot(key)
                self.assertEqual((code, doc, out), (2, "absent", ""))
                self.assertIn(pattern, err)
                self.assertFalse(self.gh_log.exists())

    def test_an_unreadable_registry_refuses(self):
        self.registry.write_text("cron_coverage: {}\n", encoding="utf-8")
        code, doc, _, err = self.snapshot()
        self.assertEqual((code, doc), (2, "absent"))
        self.assertIn("fleet registry is unreadable", err)

    def test_a_renamed_repository_is_refused(self):
        # GitHub redirects an old name to the renamed repository; its
        # full_name is then not the name the key or header carries.
        self.set_gh(**rest(3, full_name="example/toy-renamed"))
        code, doc, _, err = self.snapshot()
        self.assertEqual((code, doc), (2, "absent"))
        self.assertIn("full name", err)

    def test_a_bad_key_reads_nothing(self):
        for key in ("example/toy#7", "example__toy__0", "example__toy", "ex_ample__toy__7",
                    "example__toy__7\n", "example__toy__12345678"):
            with self.subTest(key=key):
                code, doc, out, err = self.snapshot(key)
                self.assertEqual((code, doc), (2, "absent"))
                self.assertIn("not a miner key", err)
        self.assertFalse(self.gh_log.exists())

    def test_build_uses_the_payload_and_reads_no_github(self):
        target = self.build_with(precomputed())
        self.assertFalse(self.gh_log.exists(), "no gh call: GraphQL is refused in a routine")
        reference = self.tmp / "reference"
        self.dest, kept = reference, self.dest
        self.build()
        self.dest = kept
        for name in ("fixture.yaml", "issue-before-fix.txt"):
            with self.subTest(name=name):
                self.assertEqual((target / name).read_bytes(),
                                 (reference / "toy-7" / name).read_bytes(),
                                 "the precomputed snapshot builds the same bytes")

    def test_build_with_a_null_snapshot_and_no_issue(self):
        target = self.build_with(None, issue=None)
        self.assertFalse((target / "issue-before-fix.txt").exists())
        self.assertFalse(self.gh_log.exists())

    def test_build_refuses_a_payload_that_disagrees(self):
        cases = [
            ("names issue 4", precomputed(issue=4), {}),
            ("pull request", precomputed(pr=8), {}),
            ("repository", precomputed(repo="example/other"), {}),
            ("no closing issue", None, {}),
            ("spec names no issue", precomputed(), {"issue": None}),
        ]
        for pattern, doc, changes in cases:
            with self.subTest(pattern=pattern):
                self.refused_with(pattern, doc, **changes)

    def test_build_refuses_a_malformed_payload(self):
        cases = [
            ("keys", precomputed(extra=1), None),
            ("keys", {k: v for k, v in precomputed().items() if k != "body"}, None),
            ("issue", precomputed(issue="3"), None),
            ("issue", precomputed(issue=True), None),
            ("pr", precomputed(pr=7.0), None),
            ("title", precomputed(title="  "), None),
            ("title", precomputed(title="x" * (scaffold.MAX_TITLE_CHARS + 1)), None),
            ("body", precomputed(body=None), None),
            ("body", precomputed(body="x" * (scaffold.MAX_BODY_CHARS + 1)), None),
            ("NUL", precomputed(body="a\x00b"), None),
            ("ISO-8601", precomputed(first_commit_at="2026-09-01 10:00:00"), None),
            ("ISO-8601", precomputed(issue_last_edited_at=""), None),
            ("created after", precomputed(issue_created_at="2026-09-01T11:00:00Z"), None),
            ("between", precomputed(issue_last_edited_at="2026-09-01T10:30:00Z"), None),
            ("JSON", None, "{not json"),
            ("JSON", None, '{"repo": "a", "repo": "b"}'),
            ("JSON", None, "NaN"),
            ("object or null", None, "[]"),
            ("object or null", None, '"text"'),
            ("bytes", None, " " * (scaffold.MAX_SNAPSHOT_FILE_BYTES + 1)),
        ]
        for pattern, doc, raw in cases:
            with self.subTest(pattern=pattern, raw=(raw or "")[:20]):
                self.refused_with(pattern, doc, raw)
        self.assertFalse(self.gh_log.exists())

    def test_build_cli_takes_the_flag(self):
        snap = self.tmp / "issue-snapshot.json"
        snap.write_text(json.dumps(precomputed()), encoding="utf-8")
        path = self.tmp / "spec.json"
        path.write_text(json.dumps(spec()), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            code = scaffold.main(["build", "--candidates", str(self.candidates),
                                  "--key", "example__toy__7", "--clone", str(self.clone),
                                  "--spec", str(path), "--dest", str(self.dest),
                                  "--issue-snapshot", str(snap)])
        self.assertEqual(code, 0)
        self.assertFalse(self.gh_log.exists())


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
        self.assertTrue(mine_real_work.is_bot({"head": {"ref": "claude/scaffold-toy-7"}}))
        self.assertFalse(mine_real_work.is_bot({"head": {"ref": "claude/fix-toy"}}))


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
                             self.tmp / "out", fleet=self.fleet)

    def assertRejected(self, pattern, mutate=None, **kwargs):
        self.commit(mutate)
        with self.assertRaisesRegex(ingest.Rejected, pattern) as caught:
            self.gate(**kwargs)
        self.assertNotIn(MARKER, str(caught.exception))


class GateTests(_GateCase):

    def test_accepts_the_scaffold_and_writes_exactly_its_files(self):
        tip = self.commit()
        result = self.gate(expect=tip)
        # Exactly these keys reach $GITHUB_OUTPUT: none may carry branch
        # content (a title, the prompt) to the job holding a write token.
        self.assertEqual(set(result), {"fixture_id", "sha", "files"})
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = scaffold.main(["gate", "--repo", str(self.repo), "--base", "main",
                                  "--source", self.BRANCH, "--branch", self.BRANCH,
                                  "--out", str(self.tmp / "out-cli"), *self.fleet_args()])
        self.assertEqual(code, 0)
        self.assertEqual([line.split("=", 1)[0] for line in out.getvalue().splitlines()],
                         ["fixture_id", "sha", "files"])
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
                          self.tmp / "out", fleet=self.fleet)

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
        # claude/toy-7 and claude/eval-run-7 would be valid fixture ids under
        # a looser `claude/(?:scaffold-)?` pattern: only the prefix refuses them.
        for branch in ("claude/eval-20261006T194256Z-f944ea", "claude/scaffold-", "scaffold/toy-7",
                       "claude/scaffold-toy", "claude/scaffold-../x-1", "claude/toy-7",
                       "claude/eval-run-7", "claude/scaffoldtoy-7", "claude/scaffold-toy-7/x",
                       # Git allows these in a ref name; the id lands in a
                       # query string, a PR title and body. Over-long ids too.
                       "claude/scaffold-a&base=x-1", "claude/scaffold-a%26b-1",
                       "claude/scaffold-a#b-1", "claude/scaffold-a?b-1", "claude/scaffold-a=b-1",
                       "claude/scaffold-" + "a" * 65 + "-1", "claude/scaffold-toy-12345678"):
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
                                  "--out", str(self.tmp / "out"), *self.fleet_args()])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn(MARKER, err.getvalue())
        self.assertNotIn("operands", err.getvalue())


class GateSnapshotTests(_GateCase):
    """The real guarantee: the gate recomputes the snapshot on Actions, where
    GraphQL works, and rejects a branch whose snapshot or its times differ, so
    the routine cannot alter the issue text it was handed."""

    def edit(self, name, old, new):
        def mutate(where):
            path = where / name
            text = path.read_text(encoding="utf-8")
            self.assertIn(old, text)
            path.write_text(text.replace(old, new), encoding="utf-8")
        return mutate

    def test_an_unaltered_snapshot_passes_and_the_gate_reads_github(self):
        self.gh_log.unlink()
        self.commit()
        self.gate()
        calls = [json.loads(line) for line in self.gh_log.read_text().splitlines()]
        self.assertEqual(calls[0], ["api", "repos/example/toy/pulls/7"])
        self.assertEqual(len(calls), 4)

    def test_an_altered_snapshot_is_rejected(self):
        self.assertRejected("issue-before-fix.txt differs",
                            self.edit("issue-before-fix.txt", "It should add.",
                                      "It should add. " + MARKER))

    def test_an_appended_byte_is_rejected(self):
        self.assertRejected("issue-before-fix.txt differs",
                            self.edit("issue-before-fix.txt", "It should add.\n",
                                      "It should add.\n\n"))

    def test_an_issue_edited_on_github_is_caught(self):
        # Same branch bytes, different GitHub truth: the comparison is what
        # rejects, not the branch's shape.
        self.commit()
        self.set_graphql(graphql(body="A different body " + MARKER))
        with self.assertRaisesRegex(ingest.Rejected, "issue-before-fix.txt differs") as caught:
            self.gate()
        self.assertNotIn(MARKER, str(caught.exception))

    def test_an_altered_time_is_rejected(self):
        self.assertRejected("issue_created_at",
                            self.edit("fixture.yaml", "2026-09-01T09:00:00Z",
                                      "2026-09-01T08:00:00Z"))

    def test_a_dropped_snapshot_is_rejected(self):
        def drop(where):
            (where / "issue-before-fix.txt").unlink()
            path = where / "fixture.yaml"
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            for key in ("issue_before_fix", *answer_leak.PROVENANCE_KEYS):
                doc.pop(key)
            head = [line for line in path.read_text(encoding="utf-8").splitlines()
                    if line.startswith("#")]
            path.write_text("\n".join(head) + "\n\n" + yaml.safe_dump(doc, sort_keys=False),
                            encoding="utf-8")
        self.assertRejected("no issue snapshot", drop)

    def test_a_snapshot_pointed_elsewhere_is_rejected(self):
        def elsewhere(where):
            shutil.copy(where / "issue-before-fix.txt", where / "checker" / "notes.txt")
            path = where / "fixture.yaml"
            path.write_text(path.read_text(encoding="utf-8").replace(
                "issue_before_fix: issue-before-fix.txt",
                "issue_before_fix: checker/notes.txt"), encoding="utf-8")
        self.assertRejected("issue_before_fix", elsewhere)

    def test_a_snapshot_where_github_has_no_closing_issue_is_rejected(self):
        self.commit()
        self.set_gh(**rest())
        with self.assertRaisesRegex(ingest.Rejected, "no closing issue"):
            self.gate()

    def test_a_header_naming_another_pull_request_is_rejected(self):
        self.assertRejected("header",
                            self.edit("fixture.yaml", "https://github.com/example/toy/pull/7,",
                                      "https://github.com/example/toy/pull/8,"))

    def test_a_header_naming_another_issue_is_rejected(self):
        self.assertRejected("issue",
                            self.edit("fixture.yaml", "example/toy/issues/3.",
                                      "example/toy/issues/4."))

    def test_a_missing_header_is_rejected(self):
        self.assertRejected("header",
                            self.edit("fixture.yaml", "# https://github.com/example/toy/pull/7,",
                                      "# see"))

    def test_poc_owner_spoof(self):
        # Reviewer PoC (round 1, NOT CLEAN at 66cb94d4): the header names an
        # attacker's same-named repository, whose own pull request 7 and
        # issue 3 the fake gh serves as readily as GitHub would. The owner
        # pin rejects it before anything is read.
        def spoof(where):
            path = where / "fixture.yaml"
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("https://github.com/example/toy/"), 2)
            path.write_text(text.replace("https://github.com/example/toy/",
                                         "https://github.com/attacker/toy/"), encoding="utf-8")
        self.set_gh(**rest(3, issue_repo="attacker/toy", full_name="attacker/toy"))
        self.gh_log.unlink()
        self.assertRejected("not a fleet owner", spoof)
        self.assertFalse(self.gh_log.exists(), "nothing is read for a non-fleet repository")

    def test_a_renamed_repository_is_rejected(self):
        self.commit()
        self.set_gh(**rest(3, full_name="example/toy-renamed"))
        with self.assertRaisesRegex(ingest.Rejected, "full name"):
            self.gate()

    def test_the_cli_reads_the_fleet_registry(self):
        self.commit()
        write_fleet(self.registry.parent, owners=["someone-else"])
        with contextlib.redirect_stderr(io.StringIO()) as err, \
                contextlib.redirect_stdout(io.StringIO()):
            code = scaffold.main(["gate", "--repo", str(self.repo), "--base", "main",
                                  "--source", self.BRANCH, "--branch", self.BRANCH,
                                  "--out", str(self.tmp / "out-cli"), *self.fleet_args()])
        self.assertEqual(code, 1)
        self.assertIn("not a fleet owner", err.getvalue())

    def test_a_failed_recompute_rejects(self):
        self.commit()
        self.set_gh(graphql=4)
        with self.assertRaisesRegex(ingest.Rejected, "could not be recomputed"):
            self.gate()


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

    def test_the_longest_fixture_id_is_accepted(self):
        longest = "a" * 64 + "-1234567"
        self.assertEqual(len(longest), 72)
        self.assertEqual(self.resolve("workflow_run", self.push(f"claude/scaffold-{longest}"))
                         ["fixture_id"], longest)

    def test_rejections(self):
        for event in (self.push("claude/eval-20261006T194256Z-f944ea"),
                      self.push("claude/toy-7"), self.push("claude/eval-run-7"),
                      *(self.push(b) for b in ("claude/scaffold-a&base=x-1",
                                               "claude/scaffold-a%26b-1", "claude/scaffold-a#b-1",
                                               "claude/scaffold-a?b-1", "claude/scaffold-a=b-1",
                                               "claude/scaffold-" + "a" * 65 + "-1")),
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

    def test_validation_cannot_be_skipped_by_a_condition(self):
        validate = self.gate["jobs"]["validate"]
        self.assertEqual(" ".join(str(validate["if"]).split()),
                         "github.ref == format('refs/heads/{0}', "
                         "github.event.repository.default_branch) "
                         "&& (github.event_name == 'workflow_dispatch' "
                         "|| github.event.workflow_run.conclusion == 'success')")
        for step in validate["steps"]:
            self.assertNotIn("if", step, step.get("name"))

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
        self.assertEqual(len(found), 3)
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

    def test_it_opens_only_a_labeled_draft_and_never_merges_or_pushes(self):
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

    def test_the_pr_job_reads_only_the_validated_outputs(self):
        # The gate's outputs are the only values that cross from the job that
        # reads the untrusted branch into the job that holds a write token.
        # Each is pattern-checked; nothing taken from the branch's content
        # (the prompt, a title) may join them.
        validate = self.gate["jobs"]["validate"]
        self.assertEqual(validate["outputs"], {
            "base": "${{ github.event.repository.default_branch }}",
            "branch": "${{ steps.resolve.outputs.branch }}",
            "fixture_id": "${{ steps.gate.outputs.fixture_id }}",
            "sha": "${{ steps.gate.outputs.sha }}"})
        [step] = self.gate["jobs"]["draft-pr"]["steps"]
        self.assertEqual(step["env"], {
            "GH_TOKEN": "${{ github.token }}", "REPO": "${{ github.repository }}",
            "BASE": "${{ needs.validate.outputs.base }}",
            "BRANCH": "${{ needs.validate.outputs.branch }}",
            "FIXTURE_ID": "${{ needs.validate.outputs.fixture_id }}",
            "SHA": "${{ needs.validate.outputs.sha }}", "LABEL": scaffold.DRAFT_LABEL})
        # No other route in: no env above the step, and no event field
        # (a head commit message, a branch's own text) anywhere in the job.
        self.assertNotIn("env", self.gate)
        for name in ("validate", "draft-pr"):
            self.assertNotIn("env", self.gate["jobs"][name], name)
        job_text = yaml.safe_dump(self.gate["jobs"]["draft-pr"])
        self.assertIsNone(re.search(r"\$\{\{\s*github\.event", job_text))
        self.assertEqual(sorted(set(re.findall(r"\$\{\{\s*([^}]*?)\s*\}\}", job_text))), [
            "github.repository", "github.token", "needs.validate.outputs.base",
            "needs.validate.outputs.branch", "needs.validate.outputs.fixture_id",
            "needs.validate.outputs.sha"])
        [title] = re.findall(r'--title\s+("[^"]*")', step["run"])
        self.assertEqual(title, '"Draft real-work fixture: ${FIXTURE_ID}"')
        self.assertEqual(re.findall(r"\$\{?([A-Z_]+)", title), ["FIXTURE_ID"])

    def test_an_open_pr_is_found_by_head_owner_not_branch_name_alone(self):
        # `gh pr list --head` matches a branch name in any fork, so a fork's
        # same-named branch would suppress the PR. The REST query names the
        # head as <owner>:<branch>.
        [step] = self.gate["jobs"]["draft-pr"]["steps"]
        self.assertNotIn("gh pr list", step["run"])
        self.assertIn('owner="${REPO%%/*}"', step["run"])
        self.assertIn('pulls?state=open&head=${owner}:${BRANCH}&base=${BASE}', step["run"])

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
                      if str(s.get("uses", "")).startswith("actions/checkout@")
                      and "repository" not in s["with"]]
        self.assertEqual(checkout["with"]["ref"], "${{ github.event.repository.default_branch }}")
        self.assertIs(checkout["with"]["persist-credentials"], False)

    def test_the_gate_reads_the_fleet_from_agent_guidance_default_branch(self):
        steps = self.gate["jobs"]["validate"]["steps"]
        [ag] = [s for s in steps if (s.get("with") or {}).get("repository")
                == "Adam-S-Daniel/_agent-guidance"]
        self.assertTrue(ag["uses"].startswith("actions/checkout@"))
        self.assertEqual(ag["with"], {"repository": "Adam-S-Daniel/_agent-guidance",
                                      "path": "_agent-guidance",
                                      "persist-credentials": False},
                         "its default branch: no ref")
        gate_step = next(s for s in steps if s.get("id") == "gate")
        self.assertLess(steps.index(ag), steps.index(gate_step))
        self.assertIn("--registry ../_agent-guidance/repos.yml", gate_step["run"])
        self.assertIn("--sync-workflow ../_agent-guidance/.github/workflows/sync.yml",
                      gate_step["run"])

    def test_the_gate_step_reads_github_with_the_read_only_token(self):
        # The recompute needs the REST and GraphQL reads; the job's token is
        # `contents: read`, and no other step holds it.
        steps = self.gate["jobs"]["validate"]["steps"]
        gate_step = next(s for s in steps if s.get("id") == "gate")
        self.assertEqual(gate_step["env"]["GH_TOKEN"], "${{ github.token }}")
        for step in steps:
            if step is not gate_step:
                self.assertNotIn("GH_TOKEN", step.get("env") or {}, step.get("name"))

    def test_the_guards_can_fail(self):
        # Negative controls on the helpers the shape tests lean on.
        self.assertIsNone(PIN.match("actions/checkout@v4"))
        bad = {"jobs": {"j": {"steps": [{"run": "echo ${{ inputs.x }}"}]}}}
        self.assertIn("${{", run_blocks(bad)[0][1])
        self.assertIsNotNone(re.search(r"\bgh\s+pr\s+(merge|review|close|ready)\b",
                                       "gh pr merge --merge 1"))


if __name__ == "__main__":
    unittest.main()
