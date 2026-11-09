#!/usr/bin/env python3
"""adam-agentskills#134: no lane pushes a loop branch that the registry's own
one-way-door check would fail, because a red loop pull request holds the
loop's one slot. scripts/loop_door_check.py runs that check, read from the
base commit, on the branch about to be pushed, and files an issue instead.

Pins: the base commit's script runs, never the branch's copy; the pull
request it judges is the App's, ready, with the given body; it runs with no
credential in its environment; exit 2 and an unnamed failure cannot pass;
the issue is filed once per lane and subject, in a fence; and both workflow
lanes run the check before any push and file the issue on the job token.

Hermetic: local git only, a stub check script and a fake `gh`.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import loop_door_check as ldc  # noqa: E402

#: A stand-in for adam-agentskills' check: records what it was given, fails
#: when the head adds a file named `bad`, and exits as EXIT says otherwise.
STUB = '''import json, os, subprocess, sys
args = sys.argv[1:]
base, head, pr = args[args.index("--base") + 1], args[args.index("--head") + 1], \\
    args[args.index("--pr-json") + 1]
with open(os.path.join(os.getcwd(), ".seen.json"), "w") as fh:
    json.dump({"pr": json.load(open(pr)), "env": sorted(os.environ), "cwd": os.getcwd(),
               "base": base, "head": head, "copy": "MARK"}, fh)
code = int(open(os.path.join(os.getcwd(), ".exit")).read()) if os.path.exists(".exit") else None
if code is not None:
    sys.exit(code)
names = subprocess.run(["git", "diff", "--name-only", base, head], capture_output=True,
                       text=True).stdout.split()
if "bad" in names:
    print("one-way-doors: FAIL: \\"bad\\" is not a plain Markdown file (mode 100644)")
    print("one-way-doors: FAIL: second rule")
    sys.exit(1)
print("one-way-doors: pass.")
'''


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
                           *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout


class Registry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="skills-evals-test-")
        self.addCleanup(self.tmp.cleanup)
        self.reg = Path(self.tmp.name) / "reg"
        self.reg.mkdir()
        git(self.reg, "init", "-q", "-b", "main")
        (self.reg / "scripts").mkdir()
        (self.reg / ldc.CHECK).write_text(STUB.replace("MARK", "base"))
        (self.reg / ".gitignore").write_text(".seen.json\n.exit\n")
        git(self.reg, "add", "-A")
        git(self.reg, "commit", "-qm", "base")
        self.base = git(self.reg, "rev-parse", "HEAD").strip()

    def commit(self, name, text="x\n"):
        (self.reg / name).parent.mkdir(parents=True, exist_ok=True)
        (self.reg / name).write_text(text)
        git(self.reg, "add", "-A")
        git(self.reg, "commit", "-qm", name)
        return git(self.reg, "rev-parse", "HEAD").strip()

    def seen(self):
        return json.loads((self.reg / ".seen.json").read_text())


class CheckTests(Registry):
    def test_a_pass_is_empty_and_the_pr_is_the_apps_ready_one(self):
        head = self.commit("ok.md")
        os.environ["GH_TOKEN"] = "not-for-the-check"
        self.addCleanup(os.environ.pop, "GH_TOKEN", None)
        self.assertEqual(ldc.check(self.reg, self.base, head, "eval-improve/x", "B"), [])
        seen = self.seen()
        self.assertEqual(seen["pr"]["user"], {"login": ldc.LOOP_AUTHOR, "type": "Bot"})
        self.assertIs(seen["pr"]["draft"], False)
        self.assertEqual(seen["pr"]["body"], "B")
        self.assertEqual(seen["pr"]["head"], {"ref": "eval-improve/x",
                                              "repo": {"full_name": ldc.REGISTRY_REPO}})
        self.assertEqual(seen["pr"]["base"], {"repo": {"full_name": ldc.REGISTRY_REPO}})
        self.assertEqual((seen["base"], seen["head"]), (self.base, head))
        self.assertEqual(Path(seen["cwd"]).resolve(), self.reg.resolve())
        self.assertTrue(set(seen["env"]) <= {"PATH", "HOME", "LANG", "LC_CTYPE"},
                        seen["env"])

    def test_a_failure_returns_the_messages(self):
        head = self.commit("bad")
        self.assertEqual(ldc.check(self.reg, self.base, head, "draft-skill/x"),
                         ['"bad" is not a plain Markdown file (mode 100644)', "second rule"])

    def test_the_base_commits_script_runs_never_the_branchs(self):
        # The branch rewrites the script to always pass; the base's copy runs.
        (self.reg / "bad").write_text("x\n")
        (self.reg / ldc.CHECK).write_text("import sys\nsys.exit(0)\n")
        git(self.reg, "add", "-A")
        git(self.reg, "commit", "-qm", "neuter")
        head = git(self.reg, "rev-parse", "HEAD").strip()
        self.assertEqual(len(ldc.check(self.reg, self.base, head, "eval-improve/x")), 2)
        self.assertEqual(self.seen()["copy"], "base")

    def test_a_base_without_the_script_passes(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        git(empty, "init", "-q", "-b", "main")
        (empty / "a.md").write_text("a\n")
        git(empty, "add", "-A")
        git(empty, "commit", "-qm", "a")
        base = git(empty, "rev-parse", "HEAD").strip()
        (empty / ldc.CHECK).parent.mkdir()
        (empty / ldc.CHECK).write_text("import sys\nsys.exit(1)\n")
        git(empty, "add", "-A")
        git(empty, "commit", "-qm", "b")
        self.assertEqual(ldc.check(empty, base, "HEAD", "eval-improve/x"), [])

    def test_it_cannot_pass_when_the_check_cannot_run(self):
        head = self.commit("ok.md")
        for code in ("2", "3"):
            with self.subTest(code=code):
                (self.reg / ".exit").write_text(code)
                with self.assertRaises(ldc.DoorError):
                    ldc.check(self.reg, self.base, head, "eval-improve/x")
        (self.reg / ".exit").write_text("1")
        with self.assertRaisesRegex(ldc.DoorError, "named no rule"):
            ldc.check(self.reg, self.base, head, "eval-improve/x")
        with self.assertRaises(ldc.DoorError):
            ldc.check(self.reg, "0" * 40, head, "eval-improve/x")

    def test_the_cli_exit_codes(self):
        head = self.commit("bad")
        out = io.StringIO()
        code = ldc.main(["check", "--tree", str(self.reg), "--base", self.base, "--head",
                         head, "--branch", "draft-skill/x"], out=out)
        self.assertEqual(code, 1)
        self.assertEqual(len(out.getvalue().splitlines()), 2)
        (self.reg / ".exit").write_text("2")
        self.assertEqual(ldc.main(["check", "--tree", str(self.reg), "--base", self.base,
                                   "--head", head, "--branch", "draft-skill/x"],
                                  out=io.StringIO()), 2)


class FakeGh:
    def __init__(self, issues=()):
        self.issues, self.calls = list(issues), []

    def __call__(self, args, stdin=None):
        self.calls.append((list(args), stdin))
        if args[:2] == ["api", "--paginate"]:
            return "".join(json.dumps(i) + "\n" for i in self.issues)
        return "https://github.com/Adam-S-Daniel/skills-evals/issues/7\n"


SOURCE = "https://github.com/Adam-S-Daniel/skills-evals/actions/runs/77"


class IssueTests(unittest.TestCase):
    def test_files_one_fenced_issue(self):
        gh = FakeGh()
        msg = ldc.file_issue("draft-skill", "new-skill",
                             ["a ~~~ b @someone <b>x</b>", "y" * 900], SOURCE, gh)
        self.assertIn("filed", msg)
        [(args, body)] = [c for c in gh.calls if c[0][:2] == ["issue", "create"]]
        self.assertIn("draft-skill/new-skill", args[args.index("--title") + 1])
        self.assertIn(ldc.ISSUE_MARKER.format(lane="draft-skill", subject="new-skill"), body)
        fence = body.split("~~~text\n", 1)[1].split("\n~~~", 1)[0]
        self.assertNotIn("~~~", fence)
        self.assertTrue(all(len(line) <= ldc.MESSAGE_LIMIT for line in fence.splitlines()))
        self.assertTrue(body.rstrip().endswith(ldc.AGENT_MARKER))

    def test_an_existing_issue_in_any_state_is_not_filed_again(self):
        marker = ldc.ISSUE_MARKER.format(lane="eval-improve", subject="s")
        for state in ("open", "closed"):
            with self.subTest(state=state):
                gh = FakeGh([{"number": 5, "author": ldc.ISSUE_AUTHOR, "body": marker,
                              "state": state}])
                self.assertIn("#5 already", ldc.file_issue("eval-improve", "s", ["e"],
                                                            SOURCE, gh))
                self.assertFalse(any(a[:2] == ["issue", "create"] for a, _ in gh.calls))

    def test_an_issue_someone_else_opened_does_not_count(self):
        marker = ldc.ISSUE_MARKER.format(lane="eval-improve", subject="s")
        gh = FakeGh([{"number": 5, "author": "someone", "body": marker}])
        ldc.file_issue("eval-improve", "s", ["e"], SOURCE, gh)
        self.assertTrue(any(a[:2] == ["issue", "create"] for a, _ in gh.calls))

    def test_malformed_inputs_are_refused(self):
        for lane, subject, source in (("retire-skill", "s", SOURCE),
                                      ("eval-improve", "a b", SOURCE),
                                      ("eval-improve", "s", "https://example.com/x")):
            with self.subTest(lane=lane, subject=subject, source=source):
                with self.assertRaises(ldc.DoorError):
                    ldc.file_issue(lane, subject, ["e"], source, FakeGh())

    def test_the_cli_needs_messages(self):
        with tempfile.TemporaryDirectory(prefix="skills-evals-test-") as tmp:
            path = Path(tmp) / "e"
            path.write_text("\n")
            self.assertEqual(ldc.main(["issue", "--lane", "draft-skill", "--subject", "s",
                                       "--errors-file", str(path), "--source", SOURCE],
                                      gh=FakeGh(), out=io.StringIO()), 2)
            path.write_text("rule\n")
            gh = FakeGh()
            self.assertEqual(ldc.main(["issue", "--lane", "draft-skill", "--subject", "s",
                                       "--errors-file", str(path), "--source", SOURCE],
                                      gh=gh, out=io.StringIO()), 0)


def load(name):
    return yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text())


class WorkflowTests(unittest.TestCase):
    def lane(self, name, job, step):
        doc = load(name)
        steps = doc["jobs"][job]["steps"]
        return doc, steps, next(s for s in steps if s.get("name") == step)

    def assertChecksBeforeAnyPush(self, run):
        check = run.index("loop_door_check.py check")
        self.assertNotIn("push origin", run[:check])
        self.assertIn('door_rc" -eq 1', run[check:])
        self.assertIn("door=fail", run)

    def test_the_draft_lane_checks_before_the_push_and_files_the_issue(self):
        doc, steps, step = self.lane("routine-draft-skill-gate.yml", "skill-pr",
                                     "Open the skill's pull request in adam-agentskills")
        self.assertChecksBeforeAnyPush(step["run"])
        self.assertLess(step["run"].index("loop_door_check.py check"),
                        step["run"].index('push origin "HEAD:refs/heads/${target}"'))
        self.assertEqual(doc["jobs"]["skill-pr"]["outputs"]["door"],
                         "${{ steps.open.outputs.door }}")
        self.assertIssueJob(doc, "skill-pr", "draft-skill")

    def test_the_improvement_lane_checks_while_holding_no_credential(self):
        doc, steps, build = self.lane("routine-improve-gate.yml", "registry-pr",
                                      "Build the registry commits")
        self.assertChecksBeforeAnyPush(build["run"])
        mint = steps.index(next(s for s in steps if s.get("id") == "app-token"))
        self.assertLess(steps.index(build), mint)
        for s in steps[mint:]:
            self.assertEqual(s.get("if"), "steps.build.outputs.door != 'fail'", s["name"])
        self.assertIssueJob(doc, "registry-pr", "eval-improve")

    def assertIssueJob(self, doc, needs, lane):
        job = doc["jobs"]["door-issue"]
        self.assertIn(needs, job["needs"])
        self.assertEqual(job["if"], f"needs.{needs}.outputs.door == 'fail'")
        self.assertEqual(job["permissions"], {"contents": "read", "issues": "write"})
        run = job["steps"][-1]["run"]
        self.assertNotIn("${{", run)
        self.assertIn(f"--lane {lane}", run)
        self.assertEqual(job["steps"][-1]["env"]["GH_TOKEN"], "${{ github.token }}")


if __name__ == "__main__":
    unittest.main()
