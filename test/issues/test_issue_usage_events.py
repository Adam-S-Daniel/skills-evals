#!/usr/bin/env python3
"""Private usage events and hook rows: `scripts/model_usage_census.py
--events-out/--hook-logs` and the private half of
`scripts/publish_usage_census.sh`.

The events file holds timestamps, session ids, titles and repositories, so
it goes only to the private `persistent/usage-events` branch; the public
weekly file gets counts. Every transcript and hook log here is synthetic and
invented, written under a mkdtemp; git remotes are local bare repositories
over `file://`; `now` is always passed in. No network, no clock.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "test" / "issues"))
import model_usage_census as census  # noqa: E402
from test_issue_skill_usage import (  # noqa: E402
    ALLOW, NOW, NOW_TEXT, skill_call, typed, write_transcript)

SESSION = "00000000-1111-4222-8333-444444444444"


def with_session(entry, cwd=None, branch="feature/example", uuid=None):
    entry = dict(entry, sessionId=SESSION, gitBranch=branch)
    if cwd is not None:
        entry["cwd"] = cwd
    if uuid is not None:
        entry["uuid"] = uuid
    return entry


def git(*args, cwd=None):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="Fixture", GIT_COMMITTER_NAME="Fixture",
               GIT_AUTHOR_EMAIL="fixture@example.com",
               GIT_COMMITTER_EMAIL="fixture@example.com")
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


class EventTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="usage-events-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects = self.tmp / "projects"
        self.projects.mkdir()

    def events(self, *transcripts, allowlist=ALLOW):
        for index, entries in enumerate(transcripts):
            write_transcript(self.projects / "-home-example-proj" / f"s{index}.jsonl",
                             entries)
        found: list = []
        census.census_all(self.projects, NOW, 8, allowlist, found)
        return found

    def test_a_skill_call_becomes_one_record_with_every_field(self):
        records = self.events([with_session(skill_call(
            "adam-coding-anywhere:workflow-path-audit", "toolu_01"))])
        self.assertEqual(records, [{
            "v": 1, "id": "toolu_01", "ts": "2026-09-03T10:00:00.000Z", "kind": "skill",
            "name": "adam-coding-anywhere:workflow-path-audit", "surface": "local",
            "machine": census.machine_name(), "session_id": SESSION,
            "session_title": None, "cwd_repo": None, "branch": "feature/example"}])

    def test_a_typed_command_uses_the_entry_uuid_and_drops_the_slash(self):
        records = self.events([with_session(
            typed("<command-name>/adam-anything-anywhere:finding-unknowns</command-name>"),
            uuid="aaaaaaaa-0000-4000-8000-000000000001")])
        self.assertEqual([(r["id"], r["name"]) for r in records],
                         [("aaaaaaaa-0000-4000-8000-000000000001",
                           "adam-anything-anywhere:finding-unknowns")])

    def test_an_unlisted_skill_keeps_its_raw_name_but_a_built_in_is_skipped(self):
        records = self.events([skill_call("zz-private-skill"),
                               typed("<command-name>/clear</command-name>")])
        self.assertEqual([r["name"] for r in records], ["zz-private-skill"])

    def test_names_are_strings_only_and_capped(self):
        records = self.events([skill_call(7, "toolu_a"), skill_call("", "toolu_b"),
                               skill_call("y" * 500, "toolu_c")])
        self.assertEqual([len(r["name"]) for r in records], [census.EVENT_TEXT_CAP])

    def test_no_records_without_an_events_list_or_outside_the_window(self):
        write_transcript(self.projects / "p" / "s.jsonl", [
            skill_call("workflow-path-audit", "toolu_old", when="2026-07-01T10:00:00Z")])
        found: list = []
        census.census_all(self.projects, NOW, 8, ALLOW, found)
        self.assertEqual(found, [])
        self.assertEqual(census.census_all(self.projects, NOW, 8, ALLOW)[1]["invocations"],
                         {})

    def test_the_session_title_is_the_latest_summary_or_custom_title(self):
        records = self.events(
            [{"type": "summary", "summary": "First invented title", "leafUuid": "x"},
             skill_call("workflow-path-audit", "toolu_01"),
             {"type": "custom-title", "customTitle": "Renamed invented session"},
             {"type": "summary", "summary": None}],
            [skill_call("workflow-path-audit", "toolu_02")])
        self.assertEqual(sorted((r["id"], r["session_title"]) for r in records),
                         [("toolu_01", "Renamed invented session"), ("toolu_02", None)])

    def test_cwd_repo_reads_a_github_origin_and_caches_per_directory(self):
        work = self.tmp / "widgets"
        work.mkdir()
        git("init", "--quiet", cwd=work)
        git("remote", "add", "origin", "https://github.com/example-owner/widgets.git",
            cwd=work)
        cache: dict = {}
        self.assertEqual(census.cwd_repo(str(work), cache), "example-owner/widgets")
        git("remote", "set-url", "origin", "https://example.com/elsewhere.git", cwd=work)
        self.assertEqual(census.cwd_repo(str(work), cache), "example-owner/widgets")
        self.assertIsNone(census.cwd_repo(str(work), {}))
        self.assertIsNone(census.cwd_repo(str(self.tmp / "gone"), {}))
        self.assertIsNone(census.cwd_repo("relative/path", {}))
        self.assertIsNone(census.cwd_repo(None, {}))
        records = self.events([with_session(skill_call("workflow-path-audit"),
                                            cwd=str(work))])
        self.assertIsNone(records[0]["cwd_repo"])
        git("remote", "set-url", "origin", "git@github.com:example-owner/widgets.git",
            cwd=work)
        records = self.events([with_session(skill_call("workflow-path-audit"),
                                            cwd=str(work))])
        self.assertEqual(records[0]["cwd_repo"], "example-owner/widgets")

    def test_only_github_owner_name_shapes_become_a_repo(self):
        good = {"https://github.com/example-owner/widgets": "example-owner/widgets",
                "https://example-user@github.com/example-owner/w.git":
                    "example-owner/w",
                "ssh://git@github.com/example-owner/w.b_c-d": "example-owner/w.b_c-d"}
        for url, repo in good.items():
            self.assertEqual(census.github_repo(url), repo, url)
        for url in ("https://github.com.example.com/a/b", "https://example.com/a/b",
                    "https://github.com/a/b/c", "https://github.com/-a/b",
                    "https://github.com/a/..", "https://github.com/a b/c",
                    "https://github.com/a/b\n", None, 7):
            self.assertIsNone(census.github_repo(url), url)

    def test_the_events_file_is_sorted_and_the_public_files_do_not_change(self):
        write_transcript(self.projects / "-home-example-proj" / "s.jsonl", [
            with_session(skill_call("workflow-path-audit", "toolu_late",
                                    when="2026-09-03T12:00:00Z")),
            with_session(skill_call("finding-unknowns", "toolu_early",
                                    when="2026-09-01T09:00:00Z"))])
        outputs = {}
        for label, extra in (("plain", []), ("events", ["--events-out",
                                                        str(self.tmp / "events.jsonl")])):
            out, weekly = self.tmp / f"{label}.json", self.tmp / f"{label}-weekly.json"
            argv = ["model_usage_census.py", "--projects", str(self.projects),
                    "--out", str(out), "--weekly-out", str(weekly), "--now", NOW_TEXT,
                    "--hook-logs", "", *extra]
            with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                self.assertEqual(census.main(), 0)
            outputs[label] = (out.read_bytes(), weekly.read_bytes())
        self.assertEqual(outputs["plain"], outputs["events"])
        lines = (self.tmp / "events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual([json.loads(line)["id"] for line in lines],
                         ["toolu_early", "toolu_late"])
        self.assertNotIn(SESSION.encode(), outputs["events"][1])


PUBLIC = frozenset({"Adam-S-Daniel/skills-evals", "example-owner/public-widgets"})


def hook_line(ts="2026-09-03T10:00:00Z", event="pre-commit",
              repo="example-owner/public-widgets", checks=("lint-a", "lint-b"),
              failed=(), **extra):
    as_list = (lambda v: list(v) if isinstance(v, tuple) else v)
    return json.dumps({"v": 1, "ts": ts, "event": event, "repo": repo,
                       "checks": as_list(checks), "failed": as_list(failed), **extra})


class HookTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="usage-hooks-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def log(self, *lines, name="runs.jsonl"):
        path = self.tmp / name
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(path)

    def rows(self, *paths, events=None):
        self.hooks = census.hook_tally(paths, NOW, 8, PUBLIC, events, "example-host")
        tally = {"invocations": {}, "sessions": {}, "sessions_scanned": 0}
        self.doc = census.build_weekly_document(tally, NOW, 8, self.hooks)
        return [(r["week"], r["name"], r["repo"], r["invocations"], r["blocked"])
                for r in self.doc["rows"]]

    def test_runs_and_failures_per_check_with_an_all_row(self):
        rows = self.rows(self.log(
            hook_line(),
            hook_line(failed=["lint-b"]),
            hook_line(ts="2026-09-03T11:00:00Z", event="pre-push",
                      repo="Adam-S-Daniel/skills-evals", checks=["lint-a"])))
        self.assertEqual(rows, [
            ("2026-08-31", "all", None, 3, 1),
            ("2026-08-31", "lint-a", "Adam-S-Daniel/skills-evals", 1, 0),
            ("2026-08-31", "lint-a", "example-owner/public-widgets", 2, 0),
            ("2026-08-31", "lint-b", "example-owner/public-widgets", 2, 1)])
        for row in self.doc["rows"]:
            self.assertEqual(row["kind"], "hook")
            self.assertIsNone(row["sessions"])
            self.assertIsNone(row["overridden"])
        self.assertEqual(self.doc["sources"][1]["scope"], "hooks")
        self.assertEqual(self.doc["sources"][1]["runs_scanned"], 3)

    def test_unlisted_ids_and_repos_become_other_and_null_repo_stays_null(self):
        rows = self.rows(self.log(
            hook_line(repo="example-owner/private-thing",
                      checks=["Bad_ID", "x" * 42, "all"], failed=["Bad_ID"]),
            hook_line(repo=None, checks=["lint-a"])))
        self.assertEqual(rows, [
            ("2026-08-31", "all", None, 2, 1),
            ("2026-08-31", "lint-a", None, 1, 0),
            ("2026-08-31", "other", "other", 1, 1)])
        self.assertNotIn("private-thing", json.dumps(self.doc))

    def test_runs_are_bucketed_by_week_inside_the_window_only(self):
        rows = self.rows(self.log(
            hook_line(ts="2026-08-30T23:59:59Z"),          # Sunday of W35
            hook_line(ts="2026-08-31T00:00:00Z"),          # Monday of W36
            hook_line(ts="2026-07-01T00:00:00Z"),          # before the window
            hook_line(ts="2026-09-08T00:00:00Z")))         # after now
        self.assertEqual([(w, n, i) for w, n, _, i, _ in rows if n == "all"],
                         [("2026-08-24", "all", 1), ("2026-08-31", "all", 1)])

    def test_hostile_lines_are_skipped(self):
        hostile = ["{torn", "[]", "null", json.dumps({"v": 1}),
                   hook_line(v=2), hook_line(v=True), hook_line(event="post-merge"),
                   hook_line(ts="yesterday"), hook_line(ts=7),
                   hook_line(checks="lint-a"), hook_line(checks=[7]),
                   hook_line(checks=[""]), hook_line(failed=None),
                   hook_line(checks=["c"] * 201), hook_line(repo=7),
                   hook_line(repo="r" * 201), "\u0000" * 10]
        rows = self.rows(self.log(*hostile, hook_line()))
        self.assertEqual(rows[0], ("2026-08-31", "all", None, 1, 0))

    def test_missing_logs_mean_unknown_and_duplicates_count_once(self):
        self.assertIsNone(census.hook_tally([str(self.tmp / "absent")], NOW, 8, PUBLIC))
        tally = {"invocations": {}, "sessions": {}, "sessions_scanned": 0}
        self.assertEqual(len(census.build_weekly_document(tally, NOW, 8, None)["sources"]),
                         1)
        events: list = []
        line = hook_line(failed=["lint-a"])
        rows = self.rows(self.log(line), self.log(line, name="copy.jsonl"),
                         str(self.tmp / "absent"), events=events)
        self.assertEqual(rows[0], ("2026-08-31", "all", None, 1, 1))
        self.assertEqual(events, [{
            "v": 1, "id": hashlib.sha256(f"example-host\n{line}".encode()).hexdigest(),
            "ts": "2026-09-03T10:00:00.000Z", "kind": "hook", "event": "pre-commit",
            "repo": "example-owner/public-widgets", "checks": ["lint-a", "lint-b"],
            "failed": ["lint-a"], "surface": "local", "machine": "example-host"}])

    def test_public_repos_are_the_non_private_registries_plus_two(self):
        repos = census.public_repos()
        self.assertIn("Adam-S-Daniel/adam-agentskills", repos)
        self.assertIn("Adam-S-Daniel/_agent-guidance", repos)
        self.assertIn("Adam-S-Daniel/skills-evals", repos)
        self.assertNotIn("Adam-S-Daniel/adam-agentskills-private", repos)

    def test_the_cli_reads_hook_logs_and_skill_weight_ignores_hook_rows(self):
        projects = self.tmp / "projects"
        write_transcript(projects / "p" / "s.jsonl", [skill_call("workflow-path-audit")])
        log = self.log(hook_line(repo="Adam-S-Daniel/skills-evals",
                                 checks=["workflow-path-audit"]))
        weekly, events = self.tmp / "weekly.json", self.tmp / "events.jsonl"
        argv = ["model_usage_census.py", "--projects", str(projects),
                "--out", str(self.tmp / "latest.json"), "--weekly-out", str(weekly),
                "--events-out", str(events), "--now", NOW_TEXT,
                "--hook-logs", os.pathsep.join([str(self.tmp / "absent"), log])]
        with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
            self.assertEqual(census.main(), 0)
        doc = census.skill_usage.load(weekly)
        self.assertEqual(sorted((r["kind"], r["name"]) for r in doc["rows"]),
                         [("hook", "all"), ("hook", "workflow-path-audit"),
                          ("skill", "workflow-path-audit")])
        self.assertEqual(census.skill_usage.weight(doc, "workflow-path-audit", NOW), 1)
        kinds = [json.loads(line)["kind"]
                 for line in events.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sorted(kinds), ["hook", "skill"])

    def test_the_default_log_follows_agent_checks(self):
        with mock.patch.dict(os.environ, {"AGENT_CHECKS_LOG": "/x/runs.jsonl"}):
            self.assertEqual(census.default_hook_log(), "/x/runs.jsonl")
        with mock.patch.dict(os.environ, {"AGENT_CHECKS_LOG": "", "XDG_STATE_HOME": "/s"}):
            self.assertEqual(census.default_hook_log(), "/s/agent-checks/runs.jsonl")


if __name__ == "__main__":
    unittest.main()
