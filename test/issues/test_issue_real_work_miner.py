#!/usr/bin/env python3
"""The read-only real-work miner and its admission rules (#65, #98).

`scripts/mine_real_work.py` turns merged fleet pull requests into fixture
candidates (DESIGN.md "Real-work fixtures from merged pull requests"). These
tests drive it in-process against a fake `gh` answered from canned JSON, so
nothing touches the network; `prepare` runs against a throwaway local git
repository.

Discovered and run by test/run_tests.py; also runnable on its own with
`python3 test/issues/test_issue_real_work_miner.py`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import mine_real_work  # noqa: E402

#: A fake `gh` answered from `$FAKE_GH_DATA`. Every call is logged to
#: `$FAKE_GH_LOG`; anything but the miner's read verbs exits 3.
FAKE_GH = r'''
import json
import os
import sys

args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\n")
with open(os.environ["FAKE_GH_DATA"], encoding="utf-8") as handle:
    data = json.load(handle)


def missing(name):
    sys.stderr.write(f"GraphQL: Could not resolve to a Repository with the name '{name}'.\n")
    raise SystemExit(1)


if args[:2] == ["repo", "view"]:
    view = data["repos"].get(args[2])
    if view is None:
        missing(args[2])
    print(json.dumps(view))
elif args[:2] == ["pr", "list"]:
    repo = args[args.index("--repo") + 1]
    if repo not in data["prs"]:
        sys.stderr.write("HTTP 404: Not Found\n")
        raise SystemExit(1)
    print(json.dumps(data["prs"][repo]))
elif args[:2] == ["pr", "diff"]:
    key = args[args.index("--repo") + 1] + "#" + args[2]
    if key in data.get("diff_errors", {}):
        sys.stderr.write(data["diff_errors"][key] + "\n")
        raise SystemExit(1)
    sys.stdout.write(data["diffs"][key])
elif args[0] == "api" and len(args) == 2:
    repo, sha = args[1].removeprefix("repos/").split("/commits/")
    parents = data.get("parents", {}).get(sha, ["b" * 40, "c" * 40])
    if parents is None:
        sys.stderr.write("HTTP 404: Not Found\n")
        raise SystemExit(1)
    print(json.dumps({"sha": sha, "parents": [{"sha": p} for p in parents]}))
else:
    sys.stderr.write("fake gh: refused " + " ".join(args) + "\n")
    raise SystemExit(3)
'''

ADAM, JODI = "Adam-S-Daniel", "jodidaniel"


def _view(owner, name, visibility="PUBLIC"):
    return {"nameWithOwner": f"{owner}/{name}", "visibility": visibility,
            "isFork": False, "isArchived": False}


def _pr(number, *, head="feat/x", login="Adam-S-Daniel", is_bot=False, body="Fix the bug.",
        files=("scripts/tool.py", "test/test_tool.py"), labels=(), merged="2026-09-01T10:00:00Z"):
    return {"number": number, "title": f"PR {number}", "body": body,
            "files": [{"path": p} for p in files], "closingIssuesReferences": [{"number": 7}],
            "mergeCommit": {"oid": f"{number:040x}"}, "headRefName": head,
            "additions": 10, "deletions": 2, "author": {"login": login, "is_bot": is_bot},
            "mergedAt": merged, "labels": [{"name": n} for n in labels],
            "url": f"https://github.com/example/r/pull/{number}", "baseRefOid": "d" * 40}


DIFF = ("diff --git a/scripts/tool.py b/scripts/tool.py\n--- a/scripts/tool.py\n"
        "+++ b/scripts/tool.py\n@@ -1 +1,2 @@\n x = 1\n"
        "+    return parse_listing(page, truncated=True)\n"
        "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n"
        "@@ -1 +1,2 @@\n+The listing parser now reports truncation.\n")


def _junit(cases):
    rows = []
    for name, outcome, message in cases:
        inner = ""
        if outcome == "fail":
            inner = f'<failure message="{message}"/>'
        rows.append(f'<testcase classname="suite" name="{name}">{inner}</testcase>')
    return "<testsuites><testsuite>" + "".join(rows) + "</testsuite></testsuites>"


class _MinerCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text(f"#!{sys.executable}\n" + FAKE_GH, encoding="utf-8")
        gh.chmod(0o755)
        self.log = self.tmp / "gh.log"
        self.data_path = self.tmp / "gh-data.json"
        self.env = mock.patch.dict(os.environ, {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_LOG": str(self.log), "FAKE_GH_DATA": str(self.data_path)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.out = self.tmp / "out" / "candidates.json"

    def registry(self, fleet, owners="Adam-S-Daniel jodidaniel"):
        root = self.tmp / "agent-guidance"
        (root / ".github/workflows").mkdir(parents=True, exist_ok=True)
        (root / "repos.yml").write_text(
            "exclude: []\ncron_coverage:\n  fleet:\n"
            + "".join(f"    - {name}\n" for name in fleet), encoding="utf-8")
        (root / ".github/workflows/sync.yml").write_text(
            "jobs:\n  sync:\n    steps:\n      - name: Sync\n        env:\n"
            f'          SYNC_OWNERS: "{owners}"\n        run: scripts/sync.sh\n',
            encoding="utf-8")
        return root / "repos.yml"

    def gh_data(self, repos, prs, diffs=None, parents=None, diff_errors=None):
        diffs = dict(diffs or {})
        for repo, rows in prs.items():
            for row in rows:
                diffs.setdefault(f"{repo}#{row['number']}", DIFF)
        self.data_path.write_text(json.dumps({"repos": repos, "prs": prs, "diffs": diffs,
                                              "parents": parents or {},
                                              "diff_errors": diff_errors or {}}),
                                  encoding="utf-8")

    def run_main(self, *argv):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = mine_real_work.main(list(argv))
        return rc, err.getvalue()

    def mine(self, registry):
        rc, err = self.run_main("mine", "--registry", str(registry), "--out", str(self.out))
        self.assertEqual(rc, 0, err)
        self.stderr = err
        return json.loads(self.out.read_text(encoding="utf-8"))

    def calls(self):
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]


class TestFleetEnumeration(_MinerCase):
    def _both_owner_world(self):
        self.gh_data(
            repos={f"{ADAM}/skills-evals": _view(ADAM, "skills-evals"),
                   f"{JODI}/jodidaniel.com": _view(JODI, "jodidaniel.com"),
                   f"{ADAM}/repo-settings": _view(ADAM, "repo-settings", "PRIVATE"),
                   # The rename redirect DESIGN.md §1.1 measured: one repo, two names.
                   f"{ADAM}/_agent-guidance": _view(ADAM, "_agent-guidance"),
                   f"{JODI}/_agent-guidance": _view(ADAM, "_agent-guidance")},
            prs={f"{ADAM}/skills-evals": [_pr(1)], f"{JODI}/jodidaniel.com": [_pr(2)],
                 f"{ADAM}/_agent-guidance": [_pr(3)], f"{ADAM}/repo-settings": [_pr(4)]})
        return self.registry(["skills-evals", "jodidaniel.com", "repo-settings", "_agent-guidance"])

    def test_both_owners_are_enumerated_from_the_registry(self):
        doc = self.mine(self._both_owner_world())
        self.assertEqual(doc["owners"], [ADAM, JODI])
        repos = sorted(c["repo"] for c in doc["candidates"])
        self.assertEqual(repos, [f"{ADAM}/_agent-guidance", f"{ADAM}/skills-evals",
                                 f"{JODI}/jodidaniel.com"])
        probed = {c[2] for c in self.calls() if c[:2] == ["repo", "view"]}
        self.assertEqual(probed, {f"{o}/{n}" for o in (ADAM, JODI) for n in
                                  ("skills-evals", "jodidaniel.com", "repo-settings",
                                   "_agent-guidance")})

    def test_a_one_owner_registry_fails_instead_of_shrinking_the_fleet(self):
        self._both_owner_world()
        registry = self.registry(["skills-evals", "jodidaniel.com", "repo-settings",
                                  "_agent-guidance"], owners=ADAM)
        rc, err = self.run_main("mine", "--registry", str(registry), "--out", str(self.out))
        self.assertEqual(rc, 2)
        self.assertIn("jodidaniel.com", err)
        self.assertFalse(self.out.exists())

    def test_a_private_repo_is_skipped_and_never_listed(self):
        doc = self.mine(self._both_owner_world())
        self.assertEqual(doc["skipped"], [{"repo": f"{ADAM}/repo-settings", "reason": "not-public"}])
        listed = [c for c in self.calls() if c[:2] == ["pr", "list"]]
        self.assertNotIn(f"{ADAM}/repo-settings", [c[c.index("--repo") + 1] for c in listed])

    def test_only_read_verbs_reach_gh(self):
        self.mine(self._both_owner_world())
        for call in self.calls():
            if call[0] == "api":
                self.assertEqual(len(call), 2, call)
                self.assertRegex(call[1], r"^repos/[^/]+/[^/]+/commits/[0-9a-f]{40}$")
            else:
                self.assertIn(tuple(call[:2]), {("repo", "view"), ("pr", "list"), ("pr", "diff")})
            self.assertFalse({"-X", "--method", "-f", "-F", "--field"} & set(call), call)

    def test_a_repo_whose_pull_requests_404_is_skipped_with_a_warning(self):
        self.gh_data(repos={f"{ADAM}/skills-evals": _view(ADAM, "skills-evals"),
                            f"{ADAM}/GHA-bench": _view(ADAM, "GHA-bench")},
                     prs={f"{ADAM}/skills-evals": [_pr(1)]})
        doc = self.mine(self.registry(["GHA-bench", "skills-evals"]))
        self.assertEqual([c["repo"] for c in doc["candidates"]], [f"{ADAM}/skills-evals"])
        self.assertEqual(doc["skipped"], [{"repo": f"{ADAM}/GHA-bench", "reason": "pr-list-404"}])
        self.assertIn("GHA-bench: pull requests not readable", self.stderr)

    def test_out_inside_the_main_checkout_is_refused_from_a_worktree(self):
        main = self.tmp / "main"
        main.mkdir()
        git = ["git", "-c", "user.name=seed", "-c", "user.email=seed@example.com",
               "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "-C", str(main), "init", "-q"], check=True)
        subprocess.run([*git, "-C", str(main), "commit", "-q", "--allow-empty", "-m", "seed"],
                       check=True)
        worktree = self.tmp / "main-wt"
        subprocess.run([*git, "-C", str(main), "worktree", "add", "-q", str(worktree)],
                       check=True, capture_output=True)
        target = main / "candidates.json"
        with mock.patch.object(mine_real_work, "REPO_ROOT", worktree.resolve()):
            rc, err = self.run_main("mine", "--registry", str(self.registry(["x"])),
                                    "--out", str(target))
        self.assertEqual(rc, 2)
        self.assertIn("never writes the repo", err)
        self.assertFalse(target.exists())

    def test_out_inside_the_repo_is_refused_and_nothing_is_written(self):
        registry = self._both_owner_world()
        inside = REPO_ROOT / "candidates.json"
        rc, err = self.run_main("mine", "--registry", str(registry), "--out", str(inside))
        self.assertEqual(rc, 2)
        self.assertIn("never writes the repo", err)
        self.assertFalse(inside.exists())
        self.assertFalse(self.log.exists(), "refused before any gh call")


class TestCandidateFilters(_MinerCase):
    def _mine(self, prs, diffs=None, parents=None):
        self.gh_data(repos={f"{ADAM}/cms-platform": _view(ADAM, "cms-platform")},
                     prs={f"{ADAM}/cms-platform": prs}, diffs=diffs, parents=parents)
        return self.mine(self.registry(["cms-platform"]))

    def test_bot_prs_are_excluded_by_head_ref_and_author(self):
        doc = self._mine([
            _pr(1), _pr(2, head="dependabot/npm/yaml-2"), _pr(3, head="cms/posts/hello"),
            _pr(4, head="scaffold/cms-platform-693"), _pr(5, head="agents-md-sync"),
            _pr(6, login="app/github-actions"), _pr(7, login="renovate[bot]"),
            _pr(8, login="someone", is_bot=True)])
        self.assertEqual([c["pr"] for c in doc["candidates"]], [1])
        self.assertEqual(doc["summary"][0]["bot"], 7)

    def test_on_hold_unreplayable_and_bodiless_prs_are_excluded(self):
        doc = self._mine([
            _pr(1), _pr(2, labels=("on-hold",)), _pr(3, files=("scripts/tool.py",)),
            _pr(4, files=("test/test_tool.py", "README.md")), _pr(5, body="  ")])
        self.assertEqual([c["pr"] for c in doc["candidates"]], [1])
        summary = doc["summary"][0]
        self.assertEqual((summary["on_hold"], summary["not_replayable"], summary["no_task_text"]),
                         (1, 2, 1))

    def test_candidate_records_merge_date_base_and_the_body_as_task_text(self):
        body = "The poller drops the last page.\n\n```js\nfetchAll()\n```"
        cand = self._mine([_pr(9, body=body, merged="2025-12-31T23:00:00Z")])["candidates"][0]
        self.assertEqual(cand["merged_at"], "2025-12-31T23:00:00Z")
        self.assertEqual(cand["merge_sha"], f"{9:040x}")
        self.assertEqual((cand["base_sha"], cand["base_from"]), ("b" * 40, "merge-first-parent"))
        self.assertEqual(cand["task_text"], body)
        self.assertEqual(cand["spec_style"], "sketch")
        self.assertEqual((cand["test_files"], cand["source_files"]),
                         (["test/test_tool.py"], ["scripts/tool.py"]))
        self.assertEqual(cand["key"], "Adam-S-Daniel__cms-platform__9")
        self.assertNotIn("subject", cand)

    def test_a_single_parent_merge_takes_the_prs_base_ref_oid(self):
        # A rebase merge's first parent is the previous rebased commit, not the base.
        cand = self._mine([_pr(9)], parents={f"{9:040x}": ["e" * 40]})["candidates"][0]
        self.assertEqual((cand["base_sha"], cand["base_from"]), ("d" * 40, "pr-base-ref-oid"))

    def test_a_pr_without_a_readable_merge_commit_is_skipped_with_a_warning(self):
        no_commit = _pr(2)
        no_commit["mergeCommit"] = None
        doc = self._mine([_pr(1), no_commit, _pr(3)], parents={f"{3:040x}": None})
        self.assertEqual([c["pr"] for c in doc["candidates"]], [1])
        self.assertEqual(doc["summary"][0]["no_merge_commit"], 2)
        self.assertIn("#2: no readable merge commit", self.stderr)
        self.assertIn("#3: no readable merge commit", self.stderr)

    def _mine_with_diff_error(self, number, message):
        repo = f"{ADAM}/skills-evals"
        self.gh_data(repos={repo: _view(ADAM, "skills-evals")},
                     prs={repo: [_pr(1), _pr(number), _pr(3)]},
                     diff_errors={f"{repo}#{number}": message})
        return self.registry(["skills-evals"])

    def test_a_diff_github_will_not_render_skips_that_pr_and_mining_continues(self):
        # skills-evals#311 (300+ files): HTTP 406 aborted the whole mine.
        for kind in ("files (300)", "lines (20000)"):
            with self.subTest(kind=kind):
                registry = self._mine_with_diff_error(
                    2, "could not find pull request diff: HTTP 406: Sorry, the diff exceeded "
                       f"the maximum number of {kind}. Consider using 'List pull requests "
                       "files' API or locally cloning the repository instead. "
                       "(https://api.github.com/repos/o/r/pulls/2)")
                doc = self.mine(registry)
                self.assertEqual([c["pr"] for c in doc["candidates"]], [1, 3])
                self.assertEqual(doc["summary"][0]["diff_too_large"], 1)
                self.assertIn("skills-evals#2: diff too large", self.stderr)
                self.assertNotIn("Consider using", self.stderr)
                self.assertNotIn("api.github.com", self.stderr)

    def test_an_unknown_diff_failure_still_fails_loudly_without_echoing_the_body(self):
        for message in ("HTTP 500: server secret-body-text",
                        "HTTP 406: Not Acceptable secret-body-text",
                        "diff exceeded the maximum number of lines secret-body-text"):
            with self.subTest(message=message):
                registry = self._mine_with_diff_error(2, message)
                rc, err = self.run_main("mine", "--registry", str(registry), "--out", str(self.out))
                self.assertEqual(rc, 2)
                self.assertIn("gh pr diff failed (exit 1)", err)
                self.assertNotIn("secret-body-text", err)
                self.assertFalse(self.out.exists())

    def test_answer_leak_flags_a_body_that_quotes_an_added_line(self):
        doc = self._mine([
            _pr(1, body="Make it call `return parse_listing(page, truncated=True)` instead."),
            _pr(2, body="The listing drops its last page."),
            _pr(3, body="Docs: The listing parser now reports truncation.")])
        leak = {c["pr"]: c["answer_leak"] for c in doc["candidates"]}
        self.assertEqual(leak[1], {"flag": True,
                                   "quoted_lines": ["return parse_listing(page, truncated=True)"]})
        self.assertEqual(leak[2], {"flag": False, "quoted_lines": []})
        self.assertFalse(leak[3]["flag"], "a quoted doc line is not the answer")


class TestAdmission(unittest.TestCase):
    CAND = {"key": "k", "task_text": "Report a truncated listing.",
            "source_files": ["scripts/health.js"], "merged_at": "2026-09-01T00:00:00Z"}
    RUN = {"red_secs": 4, "green_secs": 4, "timed_out": False}

    @staticmethod
    def side(**cases):
        return {name: {"outcome": outcome, "message": message}
                for name, (outcome, message) in cases.items()}

    def test_fixture_8_environmental_failures_are_excluded_from_fail_to_pass(self):
        env = {f"env{i}": ("fail", "node_modules/yaml is missing") for i in range(8)}
        red = self.side(partial_a=("fail", "AssertionError: marker absent"),
                        partial_b=("fail", "AssertionError: marker absent"),
                        steady=("pass", ""), **env)
        green = self.side(partial_a=("pass", ""), partial_b=("pass", ""), steady=("pass", ""), **env)
        row = mine_real_work.admit(self.CAND, red, green, self.RUN)
        self.assertTrue(row["admitted"], row)
        self.assertEqual(row["fail_to_pass"], ["partial_a", "partial_b"])
        self.assertEqual(row["pass_to_pass"], ["steady"])
        self.assertEqual(len(row["environmental"]), 8)

    def test_a_test_that_fails_on_the_merge_too_is_environmental_whatever_it_says(self):
        red = self.side(fixed=("fail", "AssertionError"), both=("fail", "AssertionError: 1 != 2"))
        green = self.side(fixed=("pass", ""), both=("fail", "AssertionError: 1 != 2"))
        row = mine_real_work.admit(self.CAND, red, green, self.RUN)
        self.assertEqual((row["fail_to_pass"], row["environmental"]), (["fixed"], ["both"]))

    def test_a_candidate_whose_red_failures_are_all_environmental_is_rejected(self):
        red = self.side(a=("fail", "node_modules/yaml is missing"),
                        b=("fail", "ModuleNotFoundError: No module named 'yaml'"),
                        c=("fail", "getaddrinfo ENOTFOUND registry.example.com"))
        green = self.side(a=("fail", "node_modules/yaml is missing"), b=("pass", ""), c=("pass", ""))
        row = mine_real_work.admit(self.CAND, red, green, self.RUN)
        self.assertFalse(row["admitted"])
        self.assertEqual(row["reasons"], ["environmental"])
        self.assertEqual(row["environmental"], ["a", "b", "c"])

    def test_fixture_4_interface_coupled_red_failure_is_rejected(self):
        red = self.side(health=("fail", "TypeError: health.isListingTruncated is not a function"),
                        other=("fail", "AssertionError: expected 3"))
        green = self.side(health=("pass", ""), other=("pass", ""))
        row = mine_real_work.admit(self.CAND, red, green, self.RUN)
        self.assertFalse(row["admitted"])
        self.assertEqual(row["reasons"], ["interface-coupled"])
        self.assertEqual(row["interface_coupled"], [{"test": "health", "name": "isListingTruncated"}])

    def test_interface_named_by_the_task_text_is_admitted(self):
        cand = dict(self.CAND, task_text="Add isListingTruncated(page) to the health module.")
        red = self.side(health=("fail", "TypeError: health.isListingTruncated is not a function"))
        row = mine_real_work.admit(cand, red, self.side(health=("pass", "")), self.RUN)
        self.assertTrue(row["admitted"], row)
        self.assertEqual(row["fail_to_pass"], ["health"])

    def test_python_and_module_shapes_of_interface_coupling(self):
        cases = {
            "imp": "ImportError: cannot import name 'parse_listing' from 'tool'",
            "attr": "AttributeError: module 'tool' has no attribute 'parse_listing'",
            "esm": "SyntaxError: The requested module './health.js' does not provide an export named 'probe'",
            "rel": "Error: Cannot find module './listing-helper'",
            "ours": "ModuleNotFoundError: No module named 'scripts.health'",
        }
        for name, message in cases.items():
            with self.subTest(name=name):
                row = mine_real_work.admit(self.CAND, self.side(t=("fail", message)),
                                           self.side(t=("pass", "")), self.RUN)
                self.assertFalse(row["admitted"], row)
                self.assertIn("interface-coupled", row["reasons"], row)

    def test_over_the_cap_is_rejected(self):
        red, green = self.side(t=("fail", "AssertionError")), self.side(t=("pass", ""))
        for run in ({"red_secs": 85, "green_secs": 4}, {"red_secs": 4, "green_secs": 4, "timed_out": True}):
            with self.subTest(run=run):
                row = mine_real_work.admit(self.CAND, red, green, run)
                self.assertEqual(row["reasons"], ["over-cap"])

    def test_a_repeated_test_id_cannot_hide_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "red.xml"
            path.write_text(_junit([("a", "fail", "AssertionError"), ("a", "pass", ""),
                                    ("b", "pass", ""), ("b", "fail", "AssertionError")]),
                            encoding="utf-8")
            cases = mine_real_work.read_junit(path)
        self.assertEqual({k: v["outcome"] for k, v in cases.items()},
                         {"suite::a": "fail", "suite::b": "fail"})

    def test_malformed_junit_rejects_only_that_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "candidates.json").write_text(json.dumps({"candidates": [
                dict(self.CAND, key="broken"), dict(self.CAND, key="fine")]}), encoding="utf-8")
            for key, red in (("broken", "<testsuites><testsuite><testcase name="),
                             ("fine", _junit([("a", "fail", "AssertionError")]))):
                where = tmp / "rg" / key
                where.mkdir(parents=True)
                (where / "red.xml").write_text(red, encoding="utf-8")
                (where / "green.xml").write_text(_junit([("a", "pass", "")]), encoding="utf-8")
                (where / "run.json").write_text(json.dumps(self.RUN), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = mine_real_work.main(["admit", "--candidates", str(tmp / "candidates.json"),
                                          "--results", str(tmp / "rg"), "--out", str(tmp / "a.json")])
            self.assertEqual(rc, 0)
            rows = {r["key"]: r for r in json.loads((tmp / "a.json").read_text())["admissions"]}
        self.assertEqual((rows["broken"]["admitted"], rows["broken"]["reasons"]),
                         (False, ["unreadable-results"]))
        self.assertTrue(rows["fine"]["admitted"], rows["fine"])

    def test_admit_cli_reads_junit_and_reports_unrun_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "candidates.json").write_text(json.dumps({"candidates": [
                dict(self.CAND, key="ran"), dict(self.CAND, key="unrun")]}), encoding="utf-8")
            where = tmp / "rg" / "ran"
            where.mkdir(parents=True)
            (where / "red.xml").write_text(_junit([("a", "fail", "AssertionError: 1 != 2"),
                                                   ("b", "pass", "")]), encoding="utf-8")
            (where / "green.xml").write_text(_junit([("a", "pass", ""), ("b", "pass", "")]),
                                             encoding="utf-8")
            (where / "run.json").write_text(json.dumps(self.RUN), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = mine_real_work.main(["admit", "--candidates", str(tmp / "candidates.json"),
                                          "--results", str(tmp / "rg"), "--out", str(tmp / "a.json")])
            self.assertEqual(rc, 0)
            doc = json.loads((tmp / "a.json").read_text(encoding="utf-8"))
            self.assertEqual(doc["not_run"], ["unrun"])
            self.assertEqual(doc["admissions"][0]["fail_to_pass"], ["suite::a"])
            self.assertEqual(doc["admissions"][0]["pass_to_pass"], ["suite::b"])
            self.assertTrue(doc["admissions"][0]["admitted"])


class TestPrepare(unittest.TestCase):
    def test_red_tree_is_base_with_the_merge_tests_laid_over(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            clone = tmp / "clone"
            clone.mkdir()

            def git(*args):
                return subprocess.run(
                    ["git", "-C", str(clone), "-c", "user.name=seed",
                     "-c", "user.email=seed@example.com", "-c", "commit.gpgsign=false", *args],
                    check=True, capture_output=True, text=True).stdout.strip()

            git("init", "-q")
            (clone / "test").mkdir()
            (clone / "tool.py").write_text("BUG = True\n", encoding="utf-8")
            (clone / "test/test_tool.py").write_text("old\n", encoding="utf-8")
            git("add", "-A")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD")
            (clone / "tool.py").write_text("BUG = False\n", encoding="utf-8")
            (clone / "test/test_tool.py").write_text("new\n", encoding="utf-8")
            git("commit", "-qam", "fix")
            merge = git("rev-parse", "HEAD")
            out = tmp / "rg"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = mine_real_work.main(["prepare", "--clone", str(clone), "--base", base,
                                          "--merge", merge, "--test-file", "test/test_tool.py",
                                          "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertEqual((out / "red/tool.py").read_text(encoding="utf-8"), "BUG = True\n")
            self.assertEqual((out / "red/test/test_tool.py").read_text(encoding="utf-8"), "new\n")
            self.assertEqual((out / "green/tool.py").read_text(encoding="utf-8"), "BUG = False\n")
            # Both paths name a real file outside the merge tree, so only the
            # escape guard (not "not in the merge tree") can refuse them.
            for n, escape in enumerate(("../../clone/tool.py", "/etc/hostname")):
                with self.subTest(escape=escape):
                    if escape.startswith("/"):
                        self.assertTrue(Path(escape).is_file())
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        again = mine_real_work.main(
                            ["prepare", "--clone", str(clone), "--base", base, "--merge", merge,
                             "--test-file", escape, "--out", str(tmp / f"esc{n}")])
                    self.assertEqual(again, 2)
                    self.assertIn("escapes the tree", err.getvalue())


if __name__ == "__main__":
    unittest.main()
