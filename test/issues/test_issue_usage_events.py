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
                    *extra]
            with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                self.assertEqual(census.main(), 0)
            outputs[label] = (out.read_bytes(), weekly.read_bytes())
        self.assertEqual(outputs["plain"], outputs["events"])
        lines = (self.tmp / "events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual([json.loads(line)["id"] for line in lines],
                         ["toolu_early", "toolu_late"])
        self.assertNotIn(SESSION.encode(), outputs["events"][1])


if __name__ == "__main__":
    unittest.main()
