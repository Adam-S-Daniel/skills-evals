#!/usr/bin/env python3
"""Skill usage census: `scripts/model_usage_census.py --weekly-out`,
`scripts/publish_usage_census.sh`'s second file (`usage/weekly-local.json`),
and `harness/skill_usage.py`, which owns that file's schema.

The output is published on a public branch, so most of these tests are about
what may NOT become a key. Every transcript is synthetic and written under a
mkdtemp with an explicit mtime; the publisher runs against a local bare
repository over `file://`; `now` is always passed in. No network, no clock.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import model_usage_census as census  # noqa: E402
import skill_usage  # noqa: E402

NOW = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)   # ISO week 2026-W36
NOW_TEXT = "2026-09-04T12:00:00Z"
ALLOW = frozenset({"workflow-path-audit", "finding-unknowns"})
REGISTRY_URL = "https://github.com/Adam-S-Daniel/adam-agentskills"
PRIVATE_REGISTRY_URL = "https://github.com/Adam-S-Daniel/adam-agentskills-private"
SECRET_PATH = "/home/example/repos/private-client-work"
ARN = "arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/abcd1234"

#: Values a transcript could carry where a skill name is expected. None may
#: ever be a published key.
HOSTILE = (
    "../../home/example/.ssh/id_rsa",
    SECRET_PATH,
    "workflow-path-audit\n",
    "workflow-path-audit\nfinding-unknowns",
    ARN,
    "x" * 300,
    "Workflow-Path-Audit",
    "finding unknowns",
    "",
    "/",
)


def write_transcript(path: Path, entries: list, mtime: datetime = NOW) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n",
                    encoding="utf-8")
    os.utime(path, (mtime.timestamp(), mtime.timestamp()))
    return path


def skill_call(skill, call_id="toolu_01", when="2026-09-03T10:00:00Z",
               model=None, message_id=None, usage=None, **top_level):
    message = {"role": "assistant",
               "content": [{"type": "tool_use", "id": call_id, "name": "Skill",
                            "input": {"skill": skill}}]}
    if model is not None:
        message["model"] = model
    if message_id is not None:
        message["id"] = message_id
    if usage is not None:
        message["usage"] = usage
    return {"type": "assistant", "timestamp": when, "message": message,
            **top_level}


def typed(text, when="2026-09-03T10:00:00Z", as_items=False):
    content = [{"type": "text", "text": text}] if as_items else text
    return {"type": "user", "timestamp": when, "cwd": SECRET_PATH,
            "message": {"role": "user", "content": content}}


class CountingTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-usage-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects = self.tmp / "projects"
        self.projects.mkdir()

    def skills(self, *transcripts, allowlist=ALLOW, weeks=8):
        for index, entries in enumerate(transcripts):
            write_transcript(self.projects / "-home-example-proj" / f"s{index}.jsonl",
                             entries)
        self.tally = census.census_all(self.projects, NOW, weeks, allowlist)[1]
        return self.tally["invocations"]

    def test_a_skill_tool_call_is_counted_in_its_week(self):
        self.assertEqual(self.skills([skill_call("workflow-path-audit")]),
                         {"workflow-path-audit": {"2026-W36": 1}})

    def test_one_tool_use_id_counts_once_per_transcript(self):
        entries = [skill_call("workflow-path-audit", "toolu_01"),
                   skill_call("workflow-path-audit", "toolu_01"),
                   skill_call("workflow-path-audit", "toolu_02")]
        self.assertEqual(self.skills(entries),
                         {"workflow-path-audit": {"2026-W36": 2}})

    def test_the_same_id_in_two_transcripts_counts_in_each(self):
        entries = [skill_call("finding-unknowns", "toolu_01")]
        self.assertEqual(self.skills(entries, entries),
                         {"finding-unknowns": {"2026-W36": 2}})
        self.assertEqual(self.tally["sessions"], {"finding-unknowns": {"2026-W36": 2}})

    def test_sessions_count_distinct_transcripts_not_calls(self):
        busy = [skill_call("workflow-path-audit", f"toolu_{i}") for i in range(3)]
        idle = [typed("no command here")]
        self.assertEqual(self.skills(busy, idle),
                         {"workflow-path-audit": {"2026-W36": 3}})
        self.assertEqual(self.tally["sessions"], {"workflow-path-audit": {"2026-W36": 1}})
        self.assertEqual(self.tally["sessions_scanned"], 2)

    def test_a_typed_slash_command_for_a_skill_is_counted(self):
        text = ("<command-message>finding-unknowns</command-message>\n"
                "<command-name>/finding-unknowns</command-name>")
        self.assertEqual(self.skills([typed(text), typed(text, as_items=True)]),
                         {"finding-unknowns": {"2026-W36": 2}})

    def test_a_built_in_command_is_not_counted_at_all(self):
        self.assertEqual(self.skills([typed("<command-name>/clear</command-name>")]),
                         {})

    def test_a_tag_inside_a_tool_result_is_not_a_typed_command(self):
        entry = {"type": "user", "timestamp": "2026-09-03T10:00:00Z",
                 "message": {"role": "user", "content": [
                     {"type": "tool_result", "tool_use_id": "toolu_01",
                      "content": "<command-name>/finding-unknowns</command-name>"}]}}
        self.assertEqual(self.skills([entry]), {})

    def test_a_plugin_prefix_is_stripped(self):
        entries = [skill_call("adam-coding-anywhere:workflow-path-audit"),
                   typed("<command-name>/adam-anything-anywhere:finding-unknowns"
                         "</command-name>")]
        self.assertEqual(self.skills(entries),
                         {"workflow-path-audit": {"2026-W36": 1},
                          "finding-unknowns": {"2026-W36": 1}})

    def test_a_skill_outside_the_allowlist_counts_as_other(self):
        self.assertEqual(self.skills([skill_call("zz-unlisted-skill")]),
                         {"other": {"2026-W36": 1}})

    def test_a_private_plugin_prefix_counts_under_other_even_for_an_allowlisted_name(self):
        private = frozenset({"example-private-plugin"})
        entries = [skill_call("example-private-plugin:workflow-path-audit", "toolu_p"),
                   typed("<command-name>/example-private-plugin:workflow-path-audit"
                         "</command-name>"),
                   skill_call("adam-coding-anywhere:workflow-path-audit", "toolu_pub"),
                   skill_call("workflow-path-audit", "toolu_bare")]
        write_transcript(self.projects / "-home-example-proj" / "s0.jsonl", entries)
        tally = census.census_all(self.projects, NOW, 8, ALLOW, None, private)[1]
        self.assertEqual(tally["invocations"], {"other": {"2026-W36": 1},
                                                "workflow-path-audit": {"2026-W36": 2}})
        self.assertEqual(census.skill_key("example-private-plugin:x", frozenset({"x"}),
                                          private), "other")
        self.assertEqual(census.skill_key("example-private-plugin:x", frozenset({"x"})), "x")

    def test_hostile_names_never_become_keys(self):
        entries = [skill_call(value, f"toolu_{i}") for i, value in enumerate(HOSTILE)]
        entries += [skill_call({"skill": "workflow-path-audit"}, "toolu_dict"),
                    skill_call(7, "toolu_int")]
        entries += [typed(f"<command-name>/{value}</command-name>") for value in HOSTILE]
        counts = self.skills(entries)
        self.assertEqual(counts, {"other": {"2026-W36": len(HOSTILE) + 2}})
        blob = json.dumps(census.build_weekly_document(self.tally, NOW))
        for leaked in ("123456789012", "private-client-work", "id_rsa", "xxxxxxxx"):
            self.assertNotIn(leaked, blob)

    def test_an_allowlisted_name_still_has_to_look_like_a_skill(self):
        hostile_allowlist = frozenset(HOSTILE) | {"a" * 65}
        for value in sorted(hostile_allowlist):
            with self.subTest(value=value[:40]):
                self.assertEqual(census.skill_key(value, hostile_allowlist), "other")

    def test_only_weeks_inside_the_window_are_counted(self):
        entries = [skill_call("workflow-path-audit", "toolu_old",
                              when="2026-07-01T10:00:00Z"),       # W27: outside 8 weeks
                   skill_call("workflow-path-audit", "toolu_in",
                              when="2026-07-14T10:00:00Z"),       # W29: oldest week in
                   skill_call("workflow-path-audit", "toolu_future",
                              when="2026-09-08T10:00:00Z")]       # W37: after now
        self.assertEqual(self.skills(entries),
                         {"workflow-path-audit": {"2026-W29": 1}})

    def test_a_transcript_last_written_before_the_window_is_not_read(self):
        write_transcript(self.projects / "p" / "old.jsonl",
                         [skill_call("workflow-path-audit")],
                         mtime=NOW - timedelta(weeks=20))
        tally = census.census_all(self.projects, NOW, 8, ALLOW)[1]
        self.assertEqual(tally["invocations"], {})
        self.assertEqual(tally["sessions_scanned"], 0)

    def test_model_counts_are_unchanged_by_skill_counting(self):
        entries = [skill_call("workflow-path-audit", "toolu_01",
                              model="claude-opus-5", message_id="msg_01"),
                   skill_call("finding-unknowns", "toolu_02",
                              model="claude-opus-5", message_id="msg_01")]
        write_transcript(self.projects / "p" / "s.jsonl", entries)
        models, skills = census.census_all(self.projects, NOW, 8, ALLOW)
        self.assertEqual(models, census.census_counts(self.projects, NOW, 8))
        self.assertEqual(models, {"claude-opus-5": {"2026-W36": 1}})
        self.assertEqual(sorted(skills["invocations"]),
                         ["finding-unknowns", "workflow-path-audit"])

    def test_no_allowlist_counts_no_skills(self):
        self.assertEqual(self.skills([skill_call("workflow-path-audit")],
                                     allowlist=None), {})

    def test_the_weekly_document_has_the_published_shape(self):
        tally = {"invocations": {"workflow-path-audit": {"2026-W36": 3, "2026-W30": 1},
                                 "other": {"2026-W36": 2}},
                 "sessions": {"workflow-path-audit": {"2026-W36": 2, "2026-W30": 1},
                              "other": {"2026-W36": 1}},
                 "sessions_scanned": 5}
        doc = census.build_weekly_document(tally, NOW)
        self.assertEqual(sorted(doc), ["generated_at", "rows", "schema", "sources"])
        self.assertEqual(doc["schema"], 1)
        self.assertEqual(doc["generated_at"], NOW_TEXT)
        self.assertEqual(doc["sources"], [{
            "surface": "local", "scope": "transcripts",
            "from": "2026-07-13T00:00:00Z",          # Monday of 2026-W29
            "to": NOW_TEXT, "sessions_scanned": 5}])
        empty = {"repo": None, "surface": "local", "blocked": None,
                 "overridden": None, "outcome": None, "runner": None,
                 "kind": "skill"}
        self.assertEqual(doc["rows"], [
            {**empty, "week": "2026-07-20", "name": "workflow-path-audit",
             "invocations": 1, "sessions": 1},
            {**empty, "week": "2026-08-31", "name": "other",
             "invocations": 2, "sessions": 1},
            {**empty, "week": "2026-08-31", "name": "workflow-path-audit",
             "invocations": 3, "sessions": 2}])
        for entry in doc["rows"]:
            self.assertEqual(tuple(sorted(entry)), tuple(sorted(skill_usage.ROW_FIELDS)))


def make_allowlist_root(root: Path) -> Path:
    """A synthetic repo root: two skill fixtures (one a draft), one subject
    fixture, and a non-coverage file."""
    evals = root / "evals"
    for name, extra in (("workflow-path-audit", ""), ("zz-draft-only", "draft: true\n")):
        (evals / name).mkdir(parents=True)
        (evals / name / "fixture.yaml").write_text(
            f"skill: {name}\nregistry: {REGISTRY_URL}\n{extra}", encoding="utf-8")
    (evals / "zz-private-skill").mkdir()
    (evals / "zz-private-skill" / "fixture.yaml").write_text(
        f"skill: zz-private-skill\nregistry: {PRIVATE_REGISTRY_URL}\n", encoding="utf-8")
    (evals / "guidance").mkdir()
    (evals / "guidance" / "fixture.yaml").write_text("subject: guidance\n",
                                                     encoding="utf-8")
    (evals / "non-coverage.yml").write_text(
        "skips:\n"
        "  - registry: adam-agentskills\n"
        "    skill: zz-skipped-skill\n"
        "    decision: defer\n"
        "    reason: invented for a test\n", encoding="utf-8")
    return root


class AllowlistTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-allow-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_fixtures_and_non_coverage_rows_make_the_allowlist(self):
        root = make_allowlist_root(self.tmp / "repo")
        self.assertEqual(census.skill_allowlist(root),
                         {"workflow-path-audit", "zz-skipped-skill"})

    def test_a_private_registry_fixture_is_not_allowlisted(self):
        allow = census.skill_allowlist(make_allowlist_root(self.tmp / "repo"))
        self.assertNotIn("zz-private-skill", allow)
        self.assertIn("workflow-path-audit", allow)

    def test_a_private_skill_call_counts_under_other_not_by_name(self):
        root = make_allowlist_root(self.tmp / "repo")
        projects = self.tmp / "projects"
        write_transcript(projects / "p" / "s.jsonl", [
            skill_call("zz-private-skill", call_id="toolu_01"),
            skill_call("workflow-path-audit", call_id="toolu_02")])
        out, weekly_out = self.tmp / "latest.json", self.tmp / "weekly-local.json"
        argv = ["model_usage_census.py", "--projects", str(projects), "--out", str(out),
                "--weekly-out", str(weekly_out), "--now", NOW_TEXT, "--hook-logs", "",
                "--skill-allowlist-root", str(root)]
        with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
            self.assertEqual(census.main(), 0)
        text = weekly_out.read_text(encoding="utf-8")
        self.assertNotIn("zz-private-skill", text)
        rows = [(r["name"], r["invocations"]) for r in json.loads(text)["rows"]
                if r["kind"] == "skill"]
        self.assertEqual(sorted(rows), [("other", 1), ("workflow-path-audit", 1)])

    def test_the_coverage_census_adds_public_registry_gaps(self):
        root = make_allowlist_root(self.tmp / "repo")
        coverage = self.tmp / "latest.json"

        def write(registries):
            coverage.write_text(json.dumps({"registries": registries}), encoding="utf-8")

        def entry(name, skills, private=False, withheld=False):
            return {"name": name, "private": private, "names_withheld": withheld,
                    "skills": [{"registry": name, "skill": s} for s in skills]}

        write([entry("adam-agentskills", ["zz-gap-skill", "Not A Key"]),
               entry("adam-agentskills-private", ["zz-private-gap"], private=True),
               entry("adam-agentskills", ["zz-withheld"], withheld=True),
               entry("no-such-registry", ["zz-unknown-registry"]),
               # The census document says public; harness/registries.yml says
               # private, and the repository's own config wins.
               entry("adam-agentskills-private", ["zz-mislabeled"])])
        allow = census.skill_allowlist(root, coverage)
        self.assertEqual(allow, {"workflow-path-audit", "zz-skipped-skill", "zz-gap-skill"})
        for text in ("{", "[]", json.dumps({"registries": {}})):
            with self.subTest(text=text):
                coverage.write_text(text, encoding="utf-8")
                self.assertEqual(census.skill_allowlist(root, coverage),
                                 census.skill_allowlist(root))
        self.assertEqual(census.skill_allowlist(root, self.tmp / "missing.json"),
                         census.skill_allowlist(root))

    def test_a_gap_skill_call_counts_by_name_with_the_coverage_census(self):
        root = make_allowlist_root(self.tmp / "repo")
        coverage = self.tmp / "latest.json"
        coverage.write_text(json.dumps({"registries": [
            {"name": "adam-agentskills", "private": False, "names_withheld": False,
             "skills": [{"registry": "adam-agentskills", "skill": "zz-gap-skill"}]}]}),
            encoding="utf-8")
        projects = self.tmp / "projects"
        write_transcript(projects / "p" / "s.jsonl", [skill_call("zz-gap-skill")])
        out, weekly_out = self.tmp / "out.json", self.tmp / "weekly-local.json"
        argv = ["model_usage_census.py", "--projects", str(projects), "--out", str(out),
                "--weekly-out", str(weekly_out), "--now", NOW_TEXT, "--hook-logs", "",
                "--skill-allowlist-root", str(root), "--coverage-census", str(coverage)]
        with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
            self.assertEqual(census.main(), 0)
        rows = [(r["name"], r["invocations"])
                for r in json.loads(weekly_out.read_text(encoding="utf-8"))["rows"]
                if r["kind"] == "skill"]
        self.assertEqual(rows, [("zz-gap-skill", 1)])

    def test_the_committed_evals_tree_loads(self):
        allow = census.skill_allowlist()
        self.assertIn("workflow-path-audit", allow)
        # The committed private-registry fixtures never become public keys.
        self.assertNotIn("adam-writing-style", allow)
        self.assertTrue(all(census.SKILL_KEY_RE.fullmatch(name) for name in allow))

    def test_an_unreadable_allowlist_fails_closed(self):
        projects = self.tmp / "projects"
        write_transcript(projects / "p" / "s.jsonl", [skill_call("workflow-path-audit")])
        out, weekly_out = self.tmp / "latest.json", self.tmp / "weekly-local.json"
        argv = ["model_usage_census.py", "--projects", str(projects), "--out", str(out),
                "--weekly-out", str(weekly_out), "--now", NOW_TEXT,
                "--skill-allowlist-root", str(self.tmp / "no-repo-here")]
        err = io.StringIO()
        with mock.patch.object(sys, "argv", argv), mock.patch.object(sys, "stderr", err):
            self.assertEqual(census.main(), 2)
        self.assertFalse(out.exists())
        self.assertFalse(weekly_out.exists())
        self.assertNotIn(str(self.tmp), err.getvalue())


class CliTests(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-cli-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects = self.tmp / "projects"
        write_transcript(self.projects / "-home-example-proj" / "s.jsonl", [
            skill_call("workflow-path-audit", model="claude-opus-5", message_id="m1"),
            skill_call("zz-unlisted-skill", "toolu_02", model="claude-opus-5",
                       message_id="m2"),
            typed("<command-name>/finding-unknowns</command-name>"),
        ])

    def run_main(self, *extra):
        out = self.tmp / f"latest{len(extra)}.json"
        argv = ["model_usage_census.py", "--projects", str(self.projects),
                "--out", str(out), "--now", NOW_TEXT, *extra]
        printed = io.StringIO()
        with mock.patch.object(sys, "argv", argv), redirect_stdout(printed):
            self.assertEqual(census.main(), 0)
        return out.read_bytes(), printed.getvalue()

    def test_without_weekly_out_the_model_output_is_byte_identical(self):
        plain, plain_status = self.run_main()
        weekly_out = self.tmp / "weekly-local.json"
        with_skills, status = self.run_main("--weekly-out", str(weekly_out),
                                            "--hook-logs", "")
        self.assertEqual(plain, with_skills)
        self.assertNotIn("invocations", plain_status)
        self.assertIn("3 skill invocations", status)
        doc = json.loads(weekly_out.read_text(encoding="utf-8"))
        self.assertEqual([(r["name"], r["invocations"], r["sessions"]) for r in doc["rows"]
                          if r["kind"] == "skill"],
                         [("finding-unknowns", 1, 1), ("other", 1, 1),
                          ("workflow-path-audit", 1, 1)])
        self.assertEqual(skill_usage.load(weekly_out), doc)
        for leaked in ("zz-unlisted-skill", "private-client-work", "s.jsonl"):
            self.assertNotIn(leaked, weekly_out.read_text(encoding="utf-8"))
            self.assertNotIn(leaked, status)


class PublisherTests(unittest.TestCase):
    """scripts/publish_usage_census.sh through the same seams
    test/run_tests.py's TestPublishUsageCensus uses: a bare origin over
    file://, SKILLS_EVALS_URL, CENSUS_PROJECTS and CENSUS_NOW."""

    SCRIPT = REPO_ROOT / "scripts" / "publish_usage_census.sh"
    BRANCH = "persistent/eval-results"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-publish-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "home").mkdir()
        self.origin = self.tmp / "origin.git"
        self.env = {"PATH": os.environ.get("PATH", ""), "HOME": str(self.tmp / "home"),
                    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_TERMINAL_PROMPT": "0", "SKILLS_EVALS_URL": self.origin.as_uri(),
                    "CENSUS_NOW": NOW_TEXT, "USAGE_HOOK_LOGS": "",
                    "USAGE_EVENTS_URL": (self.tmp / "events.git").as_uri()}
        self.git("init", "--bare", "--quiet", str(self.tmp / "events.git"))
        self.git("config", "maintenance.auto", "false", cwd=self.tmp / "events.git")
        self.seed()
        self.projects = self.tmp / "projects"
        write_transcript(self.projects / "-home-example-proj" / "s.jsonl", [
            skill_call("workflow-path-audit", model="claude-opus-5", message_id="m1"),
            skill_call(ARN, "toolu_02", model="claude-opus-5", message_id="m2")])

    def git(self, *args, cwd=None):
        env = dict(self.env, GIT_AUTHOR_NAME="Fixture", GIT_COMMITTER_NAME="Fixture",
                   GIT_AUTHOR_EMAIL="fixture@example.com",
                   GIT_COMMITTER_EMAIL="fixture@example.com")
        return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def seed(self):
        self.git("init", "--bare", "--quiet", "-b", "main", str(self.origin))
        self.git("config", "maintenance.auto", "false", cwd=self.origin)
        seed = make_allowlist_root(self.tmp / "seed")
        self.git("init", "--quiet", "-b", "main", cwd=seed)
        (seed / "scripts").mkdir()
        for script in ("model_usage_census.py", "eval_coverage.py"):
            shutil.copy(REPO_ROOT / "scripts" / script, seed / "scripts")
        shutil.copytree(REPO_ROOT / "harness", seed / "harness",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(REPO_ROOT / "evals" / "roster-policy.yml", seed / "evals")
        self.git("add", ".", cwd=seed)
        self.git("commit", "--quiet", "-m", "seed", cwd=seed)
        self.git("push", "--quiet", self.origin.as_uri(), "main", cwd=seed)
        self.git("checkout", "--quiet", "--orphan", self.BRANCH, cwd=seed)
        self.git("rm", "-rfq", ".", cwd=seed)
        (seed / "roster.txt").write_text("unrelated\n", encoding="utf-8")
        self.git("add", "roster.txt", cwd=seed)
        self.git("commit", "--quiet", "-m", "results seed", cwd=seed)
        self.git("push", "--quiet", self.origin.as_uri(), self.BRANCH, cwd=seed)

    def run_script(self, *args):
        return subprocess.run(["bash", str(self.SCRIPT), *args],
                              env=dict(self.env, CENSUS_PROJECTS=str(self.projects)),
                              capture_output=True, text=True, timeout=120)

    def head(self):
        return self.git("rev-parse", self.BRANCH, cwd=self.origin)

    def test_a_dry_run_pushes_nothing(self):
        before = self.head()
        proc = self.run_script("--dry-run")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("2 skill invocations", proc.stdout)
        self.assertIn("dry run", proc.stdout)
        self.assertEqual(self.head(), before)

    def test_a_run_commits_exactly_the_two_files(self):
        before = self.head()
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        after = self.head()
        self.assertEqual(self.git("diff", "--name-only", before, after, cwd=self.origin),
                         "usage/latest.json\nusage/weekly-local.json")
        doc = json.loads(self.git("show", f"{self.BRANCH}:usage/weekly-local.json",
                                  cwd=self.origin))
        self.assertEqual([(r["name"], r["invocations"]) for r in doc["rows"]
                          if r["kind"] == "skill"],
                         [("other", 1), ("workflow-path-audit", 1)])
        printed = proc.stdout + proc.stderr
        for forbidden in ("workflow-path-audit", "123456789012", str(self.tmp)):
            self.assertNotIn(forbidden, printed)

    def test_the_results_branch_coverage_census_names_a_gap_skill(self):
        """A public registry's skill with no fixture or non-coverage row is
        counted by name once coverage/latest.json on the results branch
        lists it, and check_public accepts the key."""
        work = self.tmp / "results-work"
        self.git("clone", "--quiet", "--branch", self.BRANCH, self.origin.as_uri(), str(work))
        (work / "coverage").mkdir()
        (work / "coverage" / "latest.json").write_text(json.dumps({"registries": [
            {"name": "adam-agentskills", "private": False, "names_withheld": False,
             "skills": [{"registry": "adam-agentskills", "skill": "zz-gap-skill"}]}]}),
            encoding="utf-8")
        self.git("add", "coverage/latest.json", cwd=work)
        self.git("commit", "--quiet", "-m", "coverage", cwd=work)
        self.git("push", "--quiet", "origin", self.BRANCH, cwd=work)
        write_transcript(self.projects / "-home-example-proj" / "g.jsonl",
                         [skill_call("zz-gap-skill", "toolu_07")])
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        doc = json.loads(self.git("show", f"{self.BRANCH}:usage/weekly-local.json",
                                  cwd=self.origin))
        self.assertEqual(sorted((r["name"], r["invocations"]) for r in doc["rows"]
                                if r["kind"] == "skill"),
                         [("other", 1), ("workflow-path-audit", 1), ("zz-gap-skill", 1)])

    def test_a_change_to_skills_alone_is_published(self):
        """Same clock and the same model counts: latest.json's bytes do not
        move, so only weekly-local.json is staged, and the guard must allow it."""
        self.assertEqual(self.run_script().returncode, 0)
        first = self.head()
        write_transcript(self.projects / "-home-example-proj" / "t.jsonl",
                         [skill_call("workflow-path-audit", "toolu_09")])
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.git("diff", "--name-only", first, self.head(),
                                  cwd=self.origin), "usage/weekly-local.json")
        proc = self.run_script()
        self.assertIn("unchanged", proc.stdout)


def published_row(week, name, invocations, kind="skill", surface="local", repo=None):
    return {"week": week, "kind": kind, "name": name, "repo": repo,
            "surface": surface, "invocations": invocations, "sessions": 1,
            "blocked": None, "overridden": None, "outcome": None}


class SkillUsageReaderTests(unittest.TestCase):

    # NOW is in 2026-W36 (Monday 2026-08-31); four weeks back reach W33
    # (Monday 2026-08-10). W32 (2026-08-03) is outside.
    DOC = {"generated_at": "2026-09-04T06:00:00Z", "schema": 1,
           "sources": [{"surface": "local", "scope": "transcripts",
                        "from": "2026-07-13T00:00:00Z", "to": "2026-09-04T06:00:00Z",
                        "sessions_scanned": 9}],
           "rows": [published_row("2026-08-03", "workflow-path-audit", 100),
                    published_row("2026-08-10", "workflow-path-audit", 3),
                    published_row("2026-08-31", "workflow-path-audit", 2),
                    published_row("2026-08-31", "workflow-path-audit", 4,
                                  surface="cloud", repo="example/repo"),
                    published_row("2026-08-31", "workflow-path-audit", 50, kind="hook")]}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-reader-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, value, text=None):
        path = self.tmp / "weekly-local.json"
        path.write_text(text if text is not None else json.dumps(value),
                        encoding="utf-8")
        return path

    def test_load_returns_a_well_formed_document(self):
        self.assertEqual(skill_usage.load(self.write(self.DOC)), self.DOC)

    def test_load_returns_none_for_missing_unparseable_or_misshapen(self):
        self.assertIsNone(skill_usage.load(self.tmp / "absent.json"))
        self.assertIsNone(skill_usage.load(self.write(None, text="{torn")))
        row = self.DOC["rows"][0]
        for bad in ([], {**self.DOC, "rows": {}}, {**self.DOC, "generated_at": "soon"},
                    {**self.DOC, "schema": 2}, {**self.DOC, "sources": "local"},
                    {**self.DOC, "rows": [{**row, "invocations": True}]},
                    {**self.DOC, "rows": [{**row, "invocations": -1}]},
                    {**self.DOC, "rows": [{**row, "name": None}]},
                    {**self.DOC, "rows": [3]}):
            with self.subTest(bad=bad):
                self.assertIsNone(skill_usage.load(self.write(bad)))

    def test_is_fresh_within_fourteen_days_only(self):
        made = datetime(2026, 9, 4, 6, 0, 0, tzinfo=timezone.utc)
        self.assertTrue(skill_usage.is_fresh(self.DOC, made + timedelta(days=14)))
        self.assertFalse(skill_usage.is_fresh(self.DOC, made + timedelta(days=14, seconds=1)))
        self.assertFalse(skill_usage.is_fresh(self.DOC, made - timedelta(seconds=1)))
        self.assertFalse(skill_usage.is_fresh(None, made))

    def test_weight_sums_the_last_four_weeks(self):
        # W36..W33 across surfaces and repos (2 + 4 + 3); the hook row and
        # W32's 100 do not count.
        self.assertEqual(skill_usage.weight(self.DOC, "workflow-path-audit", NOW), 9)
        self.assertEqual(skill_usage.weight(self.DOC, "workflow-path-audit", NOW,
                                            weeks=5), 109)

    def test_weight_is_zero_for_a_skill_absent_from_a_fresh_census(self):
        self.assertEqual(skill_usage.weight(self.DOC, "finding-unknowns", NOW), 0)

    def test_weight_is_unknown_without_a_fresh_census(self):
        self.assertIsNone(skill_usage.weight(None, "workflow-path-audit", NOW))
        stale = NOW + timedelta(days=15)
        self.assertIsNone(skill_usage.weight(self.DOC, "workflow-path-audit", stale))
        self.assertIsNone(skill_usage.weight(self.DOC, "finding-unknowns", stale))


class GuidanceRowTests(unittest.TestCase):
    """`kind: "guidance"` rows: which memory a session loaded."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guidance-usage-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    @staticmethod
    def session(uuid, texts=None, when="2026-09-03T10:00:00Z"):
        entries = [{"type": "user", "uuid": uuid, "timestamp": when,
                    "message": {"role": "user", "content": "hello"}}]
        if texts is not None:
            files = [{"path": f"/example/M{i}.md", "type": "User", "content": t}
                     for i, t in enumerate(texts)]
            entries.append({"type": "attachment", "timestamp": when,
                            "attachment": {"type": "instructions", "files": files}})
        return entries

    def states(self, *sessions, roots=1):
        dirs = []
        for r in range(roots):
            root = self.tmp / f"root{r}"
            for index, entries in enumerate(sessions):
                write_transcript(root / "-proj" / f"s{index}.jsonl", entries)
            dirs.append(root)
        return census.census_all(dirs, NOW, 8, ALLOW)[1]["guidance"]

    def write(self, doc):
        path = self.tmp / "weekly-local.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def test_each_state_is_classified(self):
        got = self.states(
            self.session("u1", ["x\n<!-- c -->guidance-marker: fleet-full"]),
            self.session("u2", ["# Notes\n## Working in these repos"]),
            self.session("u3", ["guidance-marker: fleet-stub"]),
            self.session("u4", ["Fleet guidance is delivered once per session"]),
            self.session("u5", ["just project notes"]),
            self.session("u6", None))
        self.assertEqual(got, {"full": {"2026-W36": 2}, "stub-only": {"2026-W36": 2},
                               "neither": {"2026-W36": 1}, "unknown": {"2026-W36": 1}})

    def test_full_wins_over_stub_across_files(self):
        got = self.states(self.session("u1", ["guidance-marker: fleet-stub",
                                              "guidance-marker: fleet-full"]))
        self.assertEqual(got, {"full": {"2026-W36": 1}})

    def test_a_session_under_two_roots_counts_once(self):
        got = self.states(self.session("u1", ["guidance-marker: fleet-full"]), roots=2)
        self.assertEqual(got, {"full": {"2026-W36": 1}})

    def test_subagent_transcripts_are_not_counted(self):
        root = self.tmp / "root0"
        write_transcript(root / "-proj" / "s0.jsonl",
                         self.session("u1", ["guidance-marker: fleet-full"]))
        write_transcript(root / "-proj" / "s0" / "subagents" / "agent-a.jsonl",
                         self.session("u2", None))
        got = census.census_all([root], NOW, 8, ALLOW)[1]["guidance"]
        self.assertEqual(got, {"full": {"2026-W36": 1}})

    def test_week_is_that_of_the_first_timestamped_entry(self):
        entries = self.session("u1", ["guidance-marker: fleet-full"],
                               when="2026-08-30T23:59:59Z")   # Sunday: W35
        entries.append({"type": "user", "uuid": "u2", "timestamp": "2026-08-31T00:00:00Z",
                        "message": {"role": "user", "content": "later"}})
        self.assertEqual(self.states(entries), {"full": {"2026-W35": 1}})
        self.assertEqual(self.states(self.session("u9", None, when="2026-08-31T00:00:00Z")),
                         {"unknown": {"2026-W36": 1}})

    def test_rows_have_the_published_shape_and_do_not_change_weights(self):
        tally = census.census_all(
            [self.tmp / "none"], NOW, 8, ALLOW)[1]
        tally["guidance"] = {"full": {"2026-W36": 3}, "unknown": {"2026-W36": 1}}
        doc = census.build_weekly_document(tally, NOW)
        self.assertEqual(doc["rows"], [
            skill_usage.guidance_row("2026-W36", "full", 3),
            skill_usage.guidance_row("2026-W36", "unknown", 1)])
        self.assertEqual(doc["rows"][0], {
            "week": "2026-08-31", "kind": "guidance", "name": "full", "repo": None,
            "surface": "local", "invocations": None, "sessions": 3, "blocked": None,
            "overridden": None, "outcome": None, "runner": None})
        base = {**doc, "rows": [skill_usage.row("2026-W36", "skill", "finding-unknowns", 2, 1)]}
        both = {**doc, "rows": base["rows"] + doc["rows"]}
        self.assertEqual(skill_usage.weight(both, "finding-unknowns", NOW),
                         skill_usage.weight(base, "finding-unknowns", NOW))
        self.assertEqual(skill_usage.weight(both, "full", NOW), 0)
        self.assertEqual(skill_usage.load(self.write(both)), both)


def cloud_record(session, ts="2026-09-03T10:00:00Z", state="full",
                 check="match", **extra):
    """An invented cloud guidance record, with every field the hook writes."""
    return {"v": 1, "ts": ts, "kind": "guidance-load", "session": session,
            "surface": "cli", "remote": True, "cli": "9.9.9-fake", "state": state,
            "repos": 3, "guidance_version": "fakevers", "check_expected": True,
            "check_reported": check, "registry_sha": None, "uploaded": None, **extra}


class CloudGuidanceTests(unittest.TestCase):
    """The cloud guidance reader: `--cloud-guidance` and the carry-forward."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cloud-guidance-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.branch = self.tmp / "branch"

    def put(self, month, lines):
        path = self.branch / "events" / month / "cloud-guidance.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join((l if isinstance(l, str) else json.dumps(l)) + "\n"
                                for l in lines), encoding="utf-8")
        return path

    def tally(self):
        return census.cloud_guidance_tally(self.branch, NOW, 8)

    def doc(self, cloud=None):
        return census.build_weekly_document(
            {"invocations": {}, "sessions": {}, "sessions_scanned": 0}, NOW, 8, None,
            self.tally() if cloud is None else cloud)

    def cloud_rows(self, doc):
        return [(r["kind"], r["name"], r["week"], r["sessions"]) for r in doc["rows"]
                if r["surface"] == "cloud"]

    def test_a_session_in_two_month_files_counts_once_at_its_earliest_ts(self):
        self.put("2026-08", [cloud_record("aaaa", "2026-08-31T09:00:00Z", "stub-only")])
        self.put("2026-09", [cloud_record("aaaa", "2026-09-02T09:00:00Z", "full"),
                             cloud_record("bbbb", "2026-09-02T10:00:00Z", "full")])
        tally = self.tally()
        self.assertEqual(tally["records_scanned"], 2)
        self.assertEqual(tally["guidance"], {"stub-only": {"2026-W36": 1},
                                             "full": {"2026-W36": 1}})

    def test_a_session_twice_in_one_file_counts_once(self):
        self.put("2026-09", [cloud_record("aaaa", "2026-09-02T09:00:00Z", "full"),
                             cloud_record("aaaa", "2026-09-01T09:00:00Z", "neither")])
        tally = self.tally()
        self.assertEqual(tally["records_scanned"], 1)
        self.assertEqual(tally["guidance"], {"neither": {"2026-W36": 1}})
        self.assertEqual(tally["checks"], {"match": {"2026-W36": 1}})

    def test_hostile_state_and_check_values_publish_only_as_invalid_or_unknown(self):
        hostile = ["/home/example/fake-path", "fake prose about nothing", "e" * 64, 7,
                   ["full"], {"s": "match"}, None, True, "FULL", "full\n", ""]
        self.put("2026-09", [cloud_record(f"s{i}", state=v, check=v)
                             for i, v in enumerate(hostile)])
        doc = self.doc()
        self.assertEqual(self.cloud_rows(doc), [
            ("guidance", "invalid", "2026-08-31", len(hostile)),
            ("guidance-check", "unknown", "2026-08-31", len(hostile))])
        blob = json.dumps(doc)
        for leaked in ("fake-path", "fake prose", "e" * 64):
            self.assertNotIn(leaked, blob)

    def test_a_missing_check_value_counts_as_unknown(self):
        record = cloud_record("aaaa")
        del record["check_reported"], record["state"]
        self.put("2026-09", [record, cloud_record("bbbb", check="absent"),
                             cloud_record("cccc", check="mismatch"),
                             cloud_record("dddd", check="none")])
        self.assertEqual(self.cloud_rows(self.doc()), [
            ("guidance", "full", "2026-08-31", 3),
            ("guidance", "invalid", "2026-08-31", 1),
            ("guidance-check", "absent", "2026-08-31", 1),
            ("guidance-check", "mismatch", "2026-08-31", 1),
            ("guidance-check", "none", "2026-08-31", 1),
            ("guidance-check", "unknown", "2026-08-31", 1)])

    def test_records_before_the_window_or_unusable_are_dropped(self):
        self.put("2026-07", [
            cloud_record("old", "2026-07-12T23:59:59Z"),          # before W29's Monday
            cloud_record("edge", "2026-07-13T00:00:00Z"),         # the window's first instant
            cloud_record("late", "2026-09-14T00:00:00Z"),         # a later week than NOW's
            cloud_record("nots", ts=None), cloud_record("badts", ts="not a time"),
            cloud_record(None), cloud_record(""), cloud_record(7),
            "not json", "[1, 2]", ""])
        self.assertEqual(self.tally()["records_scanned"], 1)
        self.assertEqual(list(self.tally()["guidance"]["full"]), ["2026-W29"])

    def test_the_source_starts_on_a_week_boundary_at_the_earliest_record(self):
        self.put("2026-08", [cloud_record("aaaa", "2026-08-27T15:30:00Z")])  # Thursday
        source = [s for s in self.doc()["sources"] if s["surface"] == "cloud"]
        self.assertEqual(source, [{
            "surface": "cloud", "scope": "guidance-records",
            "from": "2026-08-24T00:00:00Z", "to": NOW_TEXT, "records_scanned": 1}])

    def test_the_source_never_starts_before_the_window_and_is_absent_when_unread(self):
        self.put("2026-07", [cloud_record("aaaa", "2026-07-13T00:00:00Z")])
        self.assertEqual([s["from"] for s in self.doc()["sources"]
                          if s["surface"] == "cloud"], ["2026-07-13T00:00:00Z"])
        empty = census.cloud_guidance_tally(self.tmp / "nothing", NOW, 8)
        self.assertEqual(empty["records_scanned"], 0)
        self.assertEqual([s["from"] for s in self.doc(empty)["sources"]
                          if s["surface"] == "cloud"], ["2026-07-13T00:00:00Z"])
        unread = census.build_weekly_document(
            {"invocations": {}, "sessions": {}, "sessions_scanned": 0}, NOW, 8)
        self.assertEqual([s["surface"] for s in unread["sources"]], ["local"])

    def test_no_identifying_field_reaches_a_cloud_row(self):
        self.put("2026-09", [cloud_record("fake-session-id")])
        blob = json.dumps(self.doc())
        for leaked in ("fake-session-id", "9.9.9-fake", "fakevers"):
            self.assertNotIn(leaked, blob)
        row = [r for r in self.doc()["rows"] if r["surface"] == "cloud"][0]
        self.assertEqual(tuple(sorted(row)), tuple(sorted(skill_usage.ROW_FIELDS)))
        self.assertIsNone(row["invocations"])

    def test_the_reader_writes_nothing_and_skips_a_linked_file(self):
        path = self.put("2026-09", [cloud_record("aaaa")])
        outside = self.tmp / "outside.jsonl"
        outside.write_text(json.dumps(cloud_record("zzzz")) + "\n", encoding="utf-8")
        (self.branch / "events" / "2026-08").mkdir()
        (self.branch / "events" / "2026-08" / "cloud-guidance.jsonl").symlink_to(outside)
        snapshot = {p: (p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
                    for p in self.tmp.rglob("*")}
        self.assertEqual(self.tally()["records_scanned"], 1)
        self.assertEqual({p: (p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
                          for p in self.tmp.rglob("*")}, snapshot)
        self.assertTrue(path.is_file())

    def test_the_cli_flag_adds_cloud_rows_and_the_model_output_is_unchanged(self):
        self.put("2026-09", [cloud_record("aaaa")])
        projects = self.tmp / "projects"
        write_transcript(projects / "-home-example-proj" / "s.jsonl", [
            skill_call("workflow-path-audit", model="claude-opus-5", message_id="m1")])
        outs = {}
        for name, extra in (("plain", []), ("cloud", ["--cloud-guidance", str(self.branch)])):
            latest, weekly = self.tmp / f"{name}-latest.json", self.tmp / f"{name}-weekly.json"
            argv = ["model_usage_census.py", "--projects", str(projects), "--out", str(latest),
                    "--weekly-out", str(weekly), "--hook-logs", "", "--now", NOW_TEXT, *extra]
            with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                self.assertEqual(census.main(), 0)
            outs[name] = (latest.read_bytes(), json.loads(weekly.read_text(encoding="utf-8")))
        self.assertEqual(outs["plain"][0], outs["cloud"][0])
        self.assertEqual(self.cloud_rows(outs["plain"][1]), [])
        self.assertEqual(self.cloud_rows(outs["cloud"][1]), [
            ("guidance", "full", "2026-08-31", 1), ("guidance-check", "match", "2026-08-31", 1)])
        self.assertEqual(skill_usage.load(self.tmp / "cloud-weekly.json"), outs["cloud"][1])

    def test_a_guidance_check_row_must_have_null_invocations(self):
        row = skill_usage.guidance_check_row("2026-W36", "match", 2)
        doc = {"generated_at": NOW_TEXT, "schema": 1, "sources": [], "rows": [row]}
        path = self.tmp / "w.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        self.assertEqual(skill_usage.load(path), doc)
        path.write_text(json.dumps({**doc, "rows": [{**row, "invocations": 1}]}),
                        encoding="utf-8")
        self.assertIsNone(skill_usage.load(path))

    def test_surface_orders_otherwise_equal_rows(self):
        rows = [skill_usage.guidance_row("2026-W36", "full", 1, "cloud"),
                skill_usage.guidance_row("2026-W36", "full", 1)]
        doc = skill_usage.document(rows, NOW, NOW - timedelta(weeks=8), 0)
        self.assertEqual([r["surface"] for r in doc["rows"]], ["cloud", "local"])

    def previous(self, to):
        cloud = {"from": datetime(2026, 8, 24, tzinfo=timezone.utc), "records_scanned": 3}
        rows = [skill_usage.guidance_row("2026-W35", "full", 3, "cloud"),
                skill_usage.guidance_check_row("2026-W35", "match", 3)]
        before = datetime.fromisoformat(to.replace("Z", "+00:00"))
        return skill_usage.document(rows + [skill_usage.row("2026-W35", "skill", "x", 9, 9)],
                                    before, before - timedelta(weeks=8), 5, None, cloud)

    def test_carry_forward_copies_cloud_rows_and_source_verbatim(self):
        previous = self.previous("2026-08-30T12:00:00Z")      # 5 days old
        new = skill_usage.document(
            [skill_usage.row("2026-W36", "skill", "y", 1, 1)], NOW, NOW - timedelta(weeks=8), 7)
        before = json.dumps(new["rows"])
        self.assertEqual(skill_usage.carry(previous, new),
                         {"cloud": 2, "skill copies": None, "cloud skill copies": None})
        self.assertEqual([r for r in new["rows"] if r["surface"] == "cloud"],
                         [r for r in previous["rows"] if r["surface"] == "cloud"])
        self.assertEqual([s for s in new["sources"] if s["surface"] == "cloud"],
                         [s for s in previous["sources"] if s["surface"] == "cloud"])
        self.assertEqual(sum(1 for r in new["rows"] if r["kind"] == "skill"), 1)
        self.assertNotEqual(json.dumps(new["rows"]), before)

    def test_a_carried_source_older_than_14_days_is_dropped(self):
        for to, carried in (("2026-08-21T12:00:00Z", 2), ("2026-08-20T11:59:59Z", None)):
            new = skill_usage.document([], NOW, NOW - timedelta(weeks=8), 7)
            self.assertEqual(skill_usage.carry(self.previous(to), new)["cloud"], carried, to)
            self.assertEqual(any(s["surface"] == "cloud" for s in new["sources"]),
                             bool(carried))
            self.assertEqual(any(r["surface"] == "cloud" for r in new["rows"]),
                             bool(carried))

    def test_nothing_is_carried_from_a_missing_or_cloudless_document(self):
        local = skill_usage.document([], NOW, NOW - timedelta(weeks=8), 7)
        for previous in (None, {}, local):
            new = skill_usage.document([], NOW, NOW - timedelta(weeks=8), 7)
            self.assertEqual(skill_usage.carry(previous, new),
                             {"cloud": None, "skill copies": None,
                              "cloud skill copies": None})
            self.assertEqual(new["sources"], local["sources"])


class CloudUseTests(unittest.TestCase):
    """`weight` adds cloud `skill-digest` uses; `counted_from` and `zero_use`
    say whether a surface was counted back to the window's start."""

    # NOW is in W36; a 4-week window starts Monday 2026-08-10.
    GEN = "2026-09-04T06:00:00Z"
    LOCAL_SOURCE = {"surface": "local", "scope": "transcripts",
                    "from": "2026-07-01T00:00:00Z", "to": GEN, "sessions_scanned": 5}

    @staticmethod
    def cloud_source(floor):
        return skill_usage.digest_source(floor, NOW, 3, skill_usage.SURFACE_CLOUD)

    def doc(self, rows=(), cloud_from=datetime(2026, 7, 20, tzinfo=timezone.utc),
            local=True, generated=GEN):
        sources = [dict(self.LOCAL_SOURCE)] if local else []
        if cloud_from is not None:
            sources.append(self.cloud_source(cloud_from))
        return {"generated_at": generated, "schema": 1, "sources": sources,
                "rows": list(rows)}

    def cloud_row(self, name="finding-unknowns", n=2, week="2026-08-31"):
        return skill_usage.digest_row(week, name, None, "unknown:gone", n, 1,
                                      skill_usage.SURFACE_CLOUD)

    def test_weight_adds_cloud_digest_invocations(self):
        doc = self.doc([skill_usage.row("2026-W36", "skill", "finding-unknowns", 3, 1),
                        self.cloud_row(n=2)])
        self.assertEqual(skill_usage.weight(doc, "finding-unknowns", NOW), 5)

    def test_weight_ignores_local_digest_rows_and_other_windows(self):
        doc = self.doc([skill_usage.row("2026-W36", "skill", "finding-unknowns", 3, 1),
                        skill_usage.digest_row("2026-08-31", "finding-unknowns", None,
                                               "unknown:gone", 3, 1),
                        self.cloud_row(n=7, week="2026-08-03"),
                        self.cloud_row(name="workflow-path-audit", n=9)])
        self.assertEqual(skill_usage.weight(doc, "finding-unknowns", NOW), 3)

    def test_counted_from_local(self):
        self.assertEqual(skill_usage.counted_from(self.doc(), skill_usage.SURFACE_LOCAL),
                         datetime(2026, 7, 1, tzinfo=timezone.utc))

    def test_counted_from_cloud_is_a_week_after_the_source_from(self):
        self.assertEqual(skill_usage.counted_from(self.doc(), skill_usage.SURFACE_CLOUD),
                         datetime(2026, 7, 27, tzinfo=timezone.utc))

    def test_counted_from_is_none_when_unknown(self):
        self.assertIsNone(skill_usage.counted_from(
            self.doc(cloud_from=None), skill_usage.SURFACE_CLOUD))
        self.assertIsNone(skill_usage.counted_from(
            self.doc(local=False), skill_usage.SURFACE_LOCAL))
        self.assertIsNone(skill_usage.counted_from(self.doc(), "other"))
        bad = self.doc()
        bad["sources"][0]["from"] = "yesterday"
        self.assertIsNone(skill_usage.counted_from(bad, skill_usage.SURFACE_LOCAL))

    def test_zero_use_is_unknown_without_a_fresh_document(self):
        self.assertIsNone(skill_usage.zero_use(None, "finding-unknowns", NOW))
        stale = self.doc(generated="2026-08-01T00:00:00Z")
        self.assertIsNone(skill_usage.zero_use(stale, "finding-unknowns", NOW))

    def test_zero_use_is_unknown_when_a_surface_is_not_covered(self):
        missing = self.doc(cloud_from=None)
        self.assertIsNone(skill_usage.zero_use(missing, "finding-unknowns", NOW))
        # Cloud counted from 2026-08-17 + 7 days, after the window start 08-10.
        recent = self.doc(cloud_from=datetime(2026, 8, 17, tzinfo=timezone.utc))
        self.assertIsNone(skill_usage.zero_use(recent, "finding-unknowns", NOW))

    def test_zero_use_true_when_covered_and_unused(self):
        doc = self.doc([self.cloud_row(name="workflow-path-audit")])
        self.assertIs(skill_usage.zero_use(doc, "finding-unknowns", NOW), True)

    def test_zero_use_false_for_a_cloud_only_use(self):
        doc = self.doc([self.cloud_row()])
        self.assertIs(skill_usage.zero_use(doc, "finding-unknowns", NOW), False)

    def test_zero_use_local_surface_ignores_a_missing_cloud_source(self):
        doc = self.doc(cloud_from=None)
        self.assertIs(skill_usage.zero_use(
            doc, "finding-unknowns", NOW, surfaces=(skill_usage.SURFACE_LOCAL,)), True)


    def test_zero_use_is_unknown_while_a_local_listing_was_cut(self):
        """#668: a skill listed by name only can rarely trigger, so a zero in a
        window holding a cut listing says nothing about its value."""
        cut = skill_usage.listing_row("2026-W35", "truncated", 1)
        doc = self.doc([self.cloud_row(name="workflow-path-audit"), cut])
        self.assertIsNone(skill_usage.zero_use(doc, "finding-unknowns", NOW))
        self.assertIsNone(skill_usage.zero_use(
            doc, "finding-unknowns", NOW, surfaces=(skill_usage.SURFACE_LOCAL,)))
        # Cloud-only skills are not judged by the local listing.
        self.assertIs(skill_usage.zero_use(
            doc, "finding-unknowns", NOW, surfaces=(skill_usage.SURFACE_CLOUD,)), True)

    def test_a_cut_listing_outside_the_window_or_a_full_one_does_not_block(self):
        old = skill_usage.listing_row("2026-W30", "truncated", 4)
        full = skill_usage.listing_row("2026-W36", "full", 9)
        doc = self.doc([self.cloud_row(name="workflow-path-audit"), old, full])
        self.assertEqual(skill_usage.truncated_listings(doc, NOW), 0)
        self.assertIs(skill_usage.zero_use(doc, "finding-unknowns", NOW), True)


class ListingRowTests(unittest.TestCase):
    """`kind: "listing"` rows: whether a session's first skill listing kept
    every plugin skill's description (#668)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="listing-usage-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    @staticmethod
    def session(uuid, content=None, initial=True, when="2026-09-03T10:00:00Z"):
        entries = [{"type": "user", "uuid": uuid, "timestamp": when,
                    "message": {"role": "user", "content": "hello"}}]
        if content is not None:
            entries.append({"type": "attachment", "timestamp": when,
                            "attachment": {"type": "skill_listing", "content": content,
                                           "isInitial": initial, "skillCount": 2,
                                           "names": []}})
        return entries

    def states(self, *sessions):
        root = self.tmp / "root"
        for index, entries in enumerate(sessions):
            write_transcript(root / "-proj" / f"s{index}.jsonl", entries)
        return census.census_all([root], NOW, 8, ALLOW)[1]["listing"]

    def test_each_state_is_classified(self):
        got = self.states(
            self.session("u1", "- alpha:one: Does one thing.\n- init: Starts.\n"),
            self.session("u2", "- alpha:one: Does one thing.\n- alpha:two\n"),
            self.session("u3", "- init\n- alpha:one: Does one thing."),
            self.session("u4", None))
        self.assertEqual(got, {"full": {"2026-W36": 2}, "truncated": {"2026-W36": 1},
                               "unknown": {"2026-W36": 1}})

    def test_only_the_first_initial_listing_counts(self):
        entries = self.session("u1", "- alpha:two\n", initial=False)
        entries += self.session("u2", "- alpha:one: Fine.\n")[1:]
        entries += self.session("u3", "- alpha:two\n")[1:]
        self.assertEqual(self.states(entries), {"full": {"2026-W36": 1}})

    def test_rows_have_the_published_shape_and_pass_the_publish_check(self):
        tally = census.census_all([self.tmp / "none"], NOW, 8, ALLOW)[1]
        tally["listing"] = {"truncated": {"2026-W36": 2}}
        doc = census.build_weekly_document(tally, NOW)
        self.assertEqual(doc["rows"], [{
            "week": "2026-08-31", "kind": "listing", "name": "truncated", "repo": None,
            "surface": "local", "invocations": None, "sessions": 2, "blocked": None,
            "overridden": None, "outcome": None, "runner": None}])
        self.assertEqual(skill_usage.check_public(doc, ALLOW, frozenset()), [])
        path = self.tmp / "weekly-local.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        self.assertEqual(skill_usage.load(path), doc)
        self.assertEqual(skill_usage.truncated_listings(doc, NOW), 2)


if __name__ == "__main__":
    unittest.main()
