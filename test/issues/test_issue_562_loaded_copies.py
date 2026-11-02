#!/usr/bin/env python3
"""skills-evals#562 PR A (2026-11-02): which copy of a skill sessions loaded,
from the private records to the public `skill-digest` rows, the dashboard's
`usage_digests` dataset and the explorer's `copies` field and `loaded-copy`
alert.

Every repository, home, transcript and store here is synthetic, under a
mkdtemp; registry "mirrors" are local bare clones, so nothing reaches the
network. `now` is always passed in. Every privacy test that asserts a value
is ABSENT also asserts that the private side holds it (so absence means
something) and has a control in which the same value, made publishable,
does appear (so the check can fail).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))
import eval_coverage  # noqa: E402
import explorer_data  # noqa: E402
import model_usage_census as census  # noqa: E402
import run_eval  # noqa: E402
import skill_digest  # noqa: E402
import skill_usage  # noqa: E402
# Modules, never their TestCase classes by name: a class bound here would be
# collected a second time (test/run_tests.py's suite-coverage check).
import test_issue_72_explorer_data as ex72  # noqa: E402
import test_issue_loaded_copy as lc  # noqa: E402
import test_issue_skill_digest as sd  # noqa: E402
import test_issue_skill_usage as su  # noqa: E402

_spec = importlib.util.spec_from_file_location("dashboard_build_562", ROOT / "dashboard" / "build.py")
dashboard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dashboard)

PUBLIC = "Adam-S-Daniel/adam-agentskills"
FORK = "example-fork/adam-agentskills"
SKILL = "finding-unknowns"
OTHER_SKILL = "workflow-path-audit"
SESSION = "sess-0f0f-example"
NOW = su.NOW                                        # 2026-09-04, ISO week 2026-W36
ENTRIES = [{"repo": PUBLIC, "layout": "plugins/*/skills/*/SKILL.md"},
           {"repo": "Adam-S-Daniel/cms-platform", "layout": "skills/*/SKILL.md"}]
WORKFLOW = ROOT / ".github" / "workflows" / "explorer-data.yml"


def git(*args, cwd, date=None):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="Fixture", GIT_COMMITTER_NAME="Fixture",
               GIT_AUTHOR_EMAIL="fixture@example.com",
               GIT_COMMITTER_EMAIL="fixture@example.com")
    if date is not None:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def skill_files(text: str) -> dict:
    return {"SKILL.md": f"---\nname: {SKILL}\n---\n{text}\n".encode(), "notes.md": b"notes\n"}


def digest_of(files: dict, scratch: Path) -> str:
    """The lock digest of a directory holding exactly `files`."""
    root = scratch / f"digest-{len(list(scratch.glob('digest-*')))}"
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    return skill_digest.lock_digest(root)


def registry(work: Path, versions: list, name: str = SKILL) -> list:
    """A work tree in the adam-agentskills layout, one commit per (date,
    files) on `main`; returns the commit shas."""
    work.mkdir(parents=True)
    git("init", "-q", "-b", "main", cwd=work)
    shas = []
    for date, files in versions:
        target = work / "plugins" / "example-plugin" / "skills" / name
        shutil.rmtree(target, ignore_errors=True)
        for rel, data in files.items():
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            (target / rel).write_bytes(data)
        git("add", "-A", cwd=work)
        git("commit", "-q", "-m", f"version at {date}", cwd=work, date=date)
        shas.append(git("rev-parse", "HEAD", cwd=work))
    return shas


def mirror_of(work: Path, bare: Path) -> Path:
    git("clone", "-q", "--bare", str(work), str(bare), cwd=work.parent)
    return bare


def use(digest=None, reason=None, registry=PUBLIC, refs=(), name=SKILL,
        week="2026-08-31", session="s1"):
    return {"week": week, "name": name, "session": session, "digest": digest,
            "reason": reason, "registry": registry, "refs": list(refs)}


def store_line(id_, **fields):
    return json.dumps({"v": 1, "id": id_, "kind": "skill", "ts": "2026-09-01T10:00:00.000Z",
                       **fields})


# --- registries.yml `private` ------------------------------------------------

class RegistryPrivacyTests(unittest.TestCase):

    def test_private_true_names_are_exactly_PRIVATE_REGISTRIES(self):
        entries = run_eval._load_registries_config()
        self.assertEqual({e["name"] for e in entries if e["private"] is True},
                         set(eval_coverage.PRIVATE_REGISTRIES))
        self.assertTrue(all(type(e["private"]) is bool for e in entries))

    def test_public_registries_exclude_the_private_ones_and_sit_inside_public_repos(self):
        public = set(census.public_registries().values())
        private = {census.github_repo(e["url"]) for e in run_eval._load_registries_config()
                   if e["private"]}
        self.assertTrue(public)
        self.assertFalse(public & private)
        self.assertLessEqual(public, census.public_repos())
        # Hook-only repositories hold no skills, so they are not registries.
        self.assertFalse(public & census.ALWAYS_PUBLIC_REPOS)

    def test_a_missing_or_non_bool_private_fails_the_loader(self):
        base = ("registries:\n  - name: one\n    url: https://example.com/one\n"
                "    layout: 'skills/*/SKILL.md'\n")
        for label, extra in (("absent", ""), ("string", "    private: 'false'\n"),
                             ("int", "    private: 0\n"), ("null", "    private: null\n")):
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "registries.yml"
                path.write_text(base + extra, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "private"):
                    run_eval._load_registries_config(path)
        with tempfile.TemporaryDirectory() as tmp:          # control: a bool loads
            path = Path(tmp) / "registries.yml"
            path.write_text(base + "    private: false\n", encoding="utf-8")
            self.assertIs(run_eval._load_registries_config(path)[0]["private"], False)

    def test_the_public_reasons_start_with_the_records_null_reasons(self):
        self.assertEqual(skill_usage.UNKNOWN_REASONS[:8], census.DIGEST_NULL_REASONS)
        self.assertEqual(skill_usage.UNKNOWN_REASONS[8:],
                         ("conflict", "unlisted-registry", "unverified-commit"))


# --- resolving an id across the private store ---------------------------------

class StoreResolutionTests(unittest.TestCase):

    def setUp(self):
        self.store = Path(tempfile.mkdtemp(prefix="store-562-"))
        self.addCleanup(shutil.rmtree, self.store, ignore_errors=True)

    def write(self, rel, *lines):
        path = self.store / "events" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write("".join(line + "\n" for line in lines))

    def test_a_non_null_digest_beats_null_across_machine_files(self):
        d = "a" * 64
        self.write("2026-09/box-one.jsonl", store_line("x", digest=None, digest_null_reason="gone",
                                                       registry=PUBLIC))
        self.write("2026-09/box-two.jsonl", store_line("x", digest=d, digest_null_reason=None,
                                                       registry=PUBLIC, ref="c" * 40))
        self.assertEqual(census.store_digests(self.store)["x"],
                         {"digest": d, "reason": None, "registry": PUBLIC, "refs": ["c" * 40]})

    def test_two_different_digests_are_a_conflict(self):
        self.write("2026-09/box.jsonl",
                   store_line("x", digest="a" * 64, digest_null_reason=None, registry=PUBLIC),
                   store_line("x", digest="b" * 64, digest_null_reason=None, registry=PUBLIC))
        self.assertEqual(census.store_digests(self.store)["x"]["reason"], "conflict")
        self.assertIsNone(census.store_digests(self.store)["x"]["digest"])

    def test_registries_that_disagree_leave_no_registry(self):
        self.write("2026-09/box.jsonl",
                   store_line("x", digest="a" * 64, digest_null_reason=None, registry=PUBLIC),
                   store_line("x", digest="a" * 64, digest_null_reason=None, registry=FORK))
        self.assertIsNone(census.store_digests(self.store)["x"]["registry"])

    def test_all_null_takes_the_earliest_reason(self):
        late = json.loads(store_line("x", digest=None, digest_null_reason="gone"))
        early = dict(late, ts="2026-08-31T10:00:00.000Z", digest_null_reason="too-large")
        self.write("2026-09/box.jsonl", json.dumps(late), json.dumps(early))
        self.assertEqual(census.store_digests(self.store)["x"]["reason"], "too-large")

    def test_malformed_lines_are_skipped_and_block_nothing(self):
        self.write("2026-09/box.jsonl",
                   store_line("x", digest="A" * 64, digest_null_reason=None),
                   store_line("x", digest=None, digest_null_reason="made-up"),
                   store_line("x", digest="a" * 63, digest_null_reason=None),
                   "{not json",
                   store_line("x", digest="a" * 64, digest_null_reason=None, registry=PUBLIC))
        self.assertEqual(census.store_digests(self.store)["x"]["digest"], "a" * 64)
        self.write("2026-09/box.jsonl", store_line("y", digest="A" * 64, digest_null_reason=None))
        self.assertNotIn("y", census.store_digests(self.store))   # absent, not pre-record

    def test_a_line_without_the_key_is_pre_record_and_cloud_files_are_not_read(self):
        self.write("2026-08/box.jsonl", store_line("old", name=SKILL))
        self.write("2026-09/cloud-skills.jsonl",
                   store_line("cloudy", digest="a" * 64, digest_null_reason=None))
        found = census.store_digests(self.store)
        self.assertEqual(found["old"], census.PRE_RECORD)
        self.assertNotIn("cloudy", found)


# --- the plan: which uses, which weeks, the floor ----------------------------

class PlanTests(unittest.TestCase):
    """census_all on synthetic transcripts, then the plan and the rows."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="plan-562-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projects = self.tmp / "projects"
        self.store = self.tmp / "store"
        session = {"sessionId": SESSION}
        first = [dict(su.skill_call(SKILL, "toolu_01", when="2026-09-02T10:00:00Z"), **session),
                 dict(su.skill_call(SKILL, "toolu_02", when="2026-08-26T10:00:00Z"), **session),
                 dict(su.skill_call("not-allowlisted", "toolu_03",
                                    when="2026-09-02T10:00:00Z"), **session),
                 dict(lc.typed(OTHER_SKILL, "u-typed", when="2026-09-03T10:00:00Z"), **session)]
        # A resumed transcript: the same call id in a second file counts again.
        second = [dict(su.skill_call(SKILL, "toolu_01", when="2026-09-02T10:00:00Z"),
                       sessionId="sess-second")]
        su.write_transcript(self.projects / "-home-example-proj" / "a.jsonl", first)
        su.write_transcript(self.projects / "-home-example-proj" / "b.jsonl", second)

    def tally(self):
        events = []
        _, tally = census.census_all(self.projects, NOW, 8, su.ALLOW, events)
        return tally

    def document(self, tally, plan):
        rows, _ = census.digest_rows(plan, ENTRIES, {})
        return census.build_weekly_document(tally, NOW, 8, digests=(plan, rows))

    def test_rows_sum_to_the_skill_rows_for_every_published_name_and_week(self):
        tally = self.tally()
        plan = census.skill_digest_plan(tally["counted"], census.store_digests(self.store),
                                        census.window_from(NOW, 8), census.public_registries())
        doc = self.document(tally, plan)
        skill = {(r["week"], r["name"]): r["invocations"] for r in doc["rows"]
                 if r["kind"] == "skill" and r["name"] != "other"}
        digest: dict = {}
        for r in doc["rows"]:
            if r["kind"] == "skill-digest":
                digest[(r["week"], r["name"])] = digest.get((r["week"], r["name"]), 0) + r["invocations"]
        self.assertEqual(digest, skill)
        self.assertEqual(skill[("2026-08-31", SKILL)], 2)            # the repeated id, twice
        self.assertEqual(skill[("2026-08-31", OTHER_SKILL)], 1)      # a typed command
        self.assertNotIn("other", {r["name"] for r in doc["rows"] if r["kind"] == "skill-digest"})
        source = next(s for s in doc["sources"] if s["scope"] == "skill-records")
        self.assertEqual(source, {"surface": "local", "scope": "skill-records",
                                  "from": "2026-07-13T00:00:00Z", "to": su.NOW_TEXT,
                                  "events_scanned": 4})
        self.assertEqual(sum(r["invocations"] for r in doc["rows"] if r["kind"] == "skill-digest"),
                         4)
        row = next(r for r in doc["rows"] if r["kind"] == "skill-digest"
                   and r["week"] == "2026-08-31" and r["name"] == SKILL)
        self.assertEqual((row["digest"], row["repo"], row["sessions"]),
                         ("unknown:no-base-dir", None, 2))
        self.assertEqual(skill_usage.check_public(doc, su.ALLOW, {PUBLIC}), [])

    def test_a_pre_record_use_moves_the_floor_past_its_week(self):
        path = self.store / "events" / "2026-08" / "box.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(store_line("toolu_02", name=SKILL) + "\n", encoding="utf-8")
        tally = self.tally()
        plan = census.skill_digest_plan(tally["counted"], census.store_digests(self.store),
                                        census.window_from(NOW, 8), census.public_registries())
        doc = self.document(tally, plan)
        self.assertEqual(plan["from"], "2026-08-31T00:00:00Z")      # the Monday after W35
        self.assertEqual({r["week"] for r in doc["rows"] if r["kind"] == "skill-digest"},
                         {"2026-08-31"})
        self.assertIn(("2026-08-24", SKILL), {(r["week"], r["name"]) for r in doc["rows"]
                                              if r["kind"] == "skill"})

    def test_a_stored_id_is_final_over_this_runs_record(self):
        path = self.store / "events" / "2026-09" / "box.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text(store_line("toolu_01", digest=None, digest_null_reason="too-large",
                                   registry=None) + "\n", encoding="utf-8")
        tally = self.tally()
        plan = census.skill_digest_plan(tally["counted"], census.store_digests(self.store),
                                        census.window_from(NOW, 8), census.public_registries())
        reasons = sorted(u["reason"] for u in plan["uses"] if u["name"] == SKILL)
        self.assertEqual(reasons, ["no-base-dir", "too-large", "too-large"])

    def test_the_cli_writes_a_private_plan_or_the_rows(self):
        out, weekly, plan = self.tmp / "o.json", self.tmp / "w.json", self.tmp / "plan.json"
        self.store.mkdir()
        argv = ["model_usage_census.py", "--projects", str(self.projects), "--out", str(out),
                "--weekly-out", str(weekly), "--now", su.NOW_TEXT, "--hook-logs", "",
                "--event-store", str(self.store)]
        for extra, has_rows in (([], True), (["--digest-plan-out", str(plan)], False)):
            with self.subTest(extra=extra), mock.patch.object(sys, "argv", argv + extra), \
                    mock.patch("sys.stdout"):
                self.assertEqual(census.main(), 0)
                doc = json.loads(weekly.read_text(encoding="utf-8"))
                self.assertEqual(any(r["kind"] == "skill-digest" for r in doc["rows"]), has_rows)
        self.assertEqual(plan.stat().st_mode & 0o777, 0o600)
        self.assertIn(SESSION, plan.read_text(encoding="utf-8"))  # private: why it is 0600
        skill_rows = sum(r["invocations"] for r in doc["rows"] if r["kind"] == "skill"
                         and r["name"] != "other")
        self.assertFalse(census.apply_digest_plan(plan, weekly, {}))
        doc = json.loads(weekly.read_text(encoding="utf-8"))
        self.assertEqual(sum(r["invocations"] for r in doc["rows"] if r["kind"] == "skill-digest"),
                         skill_rows)
        self.assertNotIn(SESSION, weekly.read_text(encoding="utf-8"))

    def test_a_mirror_flag_must_name_a_public_registry(self):
        argv = ["model_usage_census.py", "--projects", str(self.projects),
                "--out", str(self.tmp / "o.json"), "--weekly-out", str(self.tmp / "w.json"),
                "--now", su.NOW_TEXT, "--hook-logs", "", "--event-store", str(self.tmp),
                "--registry-mirror", f"{FORK}={self.tmp}"]
        with mock.patch.object(sys, "argv", argv), mock.patch("sys.stderr") as err:
            self.assertEqual(census.main(), 2)
        self.assertNotIn(FORK, "".join(str(c) for c in err.write.call_args_list))


# --- verification against a mirror's content history --------------------------

class MirrorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="mirror-562-"))
        cls.old, cls.new = skill_files("old text"), skill_files("new text")
        cls.shas = registry(cls.tmp / "work", [("2026-08-01T00:00:00Z", cls.old),
                                               ("2026-08-20T00:00:00Z", cls.new)])
        cls.mirror = mirror_of(cls.tmp / "work", cls.tmp / "mirror.git")
        # A fork with one more commit the public mirror never saw.
        git("clone", "-q", str(cls.tmp / "work"), str(cls.tmp / "fork"), cwd=cls.tmp)
        (cls.tmp / "fork" / "README.md").write_text("fork\n", encoding="utf-8")
        git("add", "README.md", cwd=cls.tmp / "fork")
        git("commit", "-q", "-m", "fork only", cwd=cls.tmp / "fork")
        cls.fork_sha = git("rev-parse", "HEAD", cwd=cls.tmp / "fork")
        scratch = cls.tmp / "scratch"
        scratch.mkdir()
        cls.d_old = digest_of(cls.old, scratch)
        cls.d_new = digest_of(cls.new, scratch)
        cls.d_never = digest_of(skill_files("never committed"), scratch)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def rows(self, *uses, mirrors=None):
        plan = {"from": "2026-07-13T00:00:00Z", "uses": list(uses), "registries": [PUBLIC]}
        return census.digest_rows(plan, ENTRIES,
                                  {PUBLIC: str(self.mirror)} if mirrors is None else mirrors)

    def shown(self, *uses, **kw):
        return [r["digest"] for r in self.rows(*uses, **kw)[0]]

    def test_the_tree_digest_is_the_shared_vector(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = sd.build_vector_tree(Path(tmp))
            self.assertEqual(skill_digest.tree_digest(root.parent, "HEAD", "skill"),
                             sd.VECTOR_GIT_IGNORED_SKIPPED)

    def test_a_digest_equal_to_an_older_commits_tree_verifies(self):
        self.assertEqual(self.shown(use(self.d_old)), [self.d_old[:12]])
        self.assertEqual(self.shown(use(self.d_new)), [self.d_new[:12]])

    def test_content_never_committed_stays_unverified(self):
        self.assertEqual(self.shown(use(self.d_never)), ["unknown:unverified-commit"])

    def test_a_ref_only_in_a_fork_stays_unverified_and_one_on_a_branch_verifies(self):
        self.assertEqual(self.shown(use(self.d_new, refs=[self.fork_sha])),
                         ["unknown:unverified-commit"])
        self.assertEqual(self.shown(use(self.d_new, refs=[self.shas[0]])), [self.d_new[:12]])

    def test_a_fork_registry_is_unlisted_with_no_repo(self):
        rows, _ = self.rows(use(self.d_new, registry=FORK))
        self.assertEqual((rows[0]["digest"], rows[0]["repo"]), ("unknown:unlisted-registry", None))
        self.assertNotIn("example-fork", json.dumps(rows))
        rows, _ = self.rows(use(self.d_new, registry=PUBLIC.lower()))  # control: case-insensitive
        self.assertEqual((rows[0]["digest"], rows[0]["repo"]), (self.d_new[:12], PUBLIC))

    def test_a_missing_or_broken_mirror_is_unverified_and_says_not_read(self):
        for label, mirrors in (("absent", {}), ("not a repo", {PUBLIC: str(self.tmp / "nope")})):
            with self.subTest(label):
                rows, unread = self.rows(use(self.d_new), mirrors=mirrors)
                self.assertEqual(rows[0]["digest"], "unknown:unverified-commit")
                self.assertTrue(unread)
        self.assertFalse(self.rows(use(self.d_new))[1])

    def test_null_digests_and_conflicts_keep_their_reasons(self):
        self.assertEqual(sorted(self.shown(use(None, "gone", week="2026-08-24"),
                                           use(None, "conflict", registry=None))),
                         ["unknown:conflict", "unknown:gone"])

    def test_tree_digest_refuses_odd_revisions_and_paths(self):
        for rev, rel in (("--output=x", "a"), ("HEAD", "../x"), ("HEAD", "-a"), ("HEAD", "/a")):
            with self.subTest(rev=rev, rel=rel), self.assertRaises(ValueError):
                skill_digest.tree_digest(self.mirror, rev, rel)


# --- the publisher's last gate -----------------------------------------------

class CheckPublicTests(unittest.TestCase):

    def doc(self, **row):
        good = skill_usage.digest_row("2026-08-31", SKILL, PUBLIC, "abcdef012345", 1, 1)
        return {"generated_at": su.NOW_TEXT, "schema": 1, "sources": [],
                "rows": [dict(good, **row)]}

    def test_a_clean_document_passes(self):
        self.assertEqual(skill_usage.check_public(self.doc(), su.ALLOW, {PUBLIC}), [])
        self.assertEqual(skill_usage.check_public(
            self.doc(digest="unknown:gone", repo=None), su.ALLOW, {PUBLIC}), [])

    def test_each_refusal_fires(self):
        hook = skill_usage.hook_row("2026-W36", "all", None, 1, 0)
        for label, doc in (
                ("64-hex digest", self.doc(digest="a" * 64)),
                ("13-hex digest", self.doc(digest="a" * 13)),
                ("40-hex anywhere", dict(self.doc(), extra="b" * 40)),
                ("reason outside the list", self.doc(digest="unknown:made-up")),
                ("repo outside the public set", self.doc(repo=FORK)),
                ("prefix without a repo", self.doc(repo=None)),
                ("other row", self.doc(name="other")),
                ("name outside the allowlist", self.doc(name="private-skill")),
                ("digest on another kind", {**self.doc(), "rows": [dict(hook, digest="unknown:gone")]}),
                ("skill row outside the allowlist", {**self.doc(), "rows": [
                    skill_usage.row("2026-W36", "skill", "private-skill", 1, 1)]})):
            with self.subTest(label):
                self.assertTrue(skill_usage.check_public(doc, su.ALLOW, {PUBLIC}), label)


# --- carry on a failed fetch ---------------------------------------------------

class CarryTests(unittest.TestCase):

    def previous(self, to):
        when = datetime.fromisoformat(to.replace("Z", "+00:00"))
        doc = skill_usage.document([skill_usage.guidance_row("2026-W35", "full", 3, "local")],
                                   when, when - timedelta(weeks=8), 5)
        skill_usage.add_rows(doc, [skill_usage.digest_row("2026-08-24", SKILL, PUBLIC,
                                                          "abcdef012345", 2, 1)],
                             skill_usage.digest_source(when - timedelta(weeks=1), when, 2))
        return doc

    def test_local_rows_and_source_are_carried_and_aged_by_their_own_source(self):
        for to, carried in (("2026-08-21T12:00:00Z", 1), ("2026-08-20T11:59:59Z", None)):
            with self.subTest(to=to):
                new = skill_usage.document([], NOW, NOW - timedelta(weeks=8), 7)
                self.assertEqual(skill_usage.carry(self.previous(to), new),
                                 {"cloud": None, "skill copies": carried,
                                  "cloud skill copies": None})
                kinds = [r["kind"] for r in new["rows"]]
                self.assertEqual(kinds, ["skill-digest"] if carried else [])  # never local guidance
                self.assertEqual(any(s["scope"] == "skill-records" for s in new["sources"]),
                                 bool(carried))

    def test_a_document_that_has_its_own_source_is_not_overwritten(self):
        new = skill_usage.document([], NOW, NOW - timedelta(weeks=8), 7)
        skill_usage.add_rows(new, [], skill_usage.digest_source(NOW, NOW, 0))
        self.assertIsNone(skill_usage.carry(self.previous("2026-09-01T00:00:00Z"), new)
                          ["skill copies"])
        self.assertEqual(new["rows"], [])


# --- end to end through the publisher: three outputs, one store ---------------

class PublishTests(unittest.TestCase):
    """scripts/publish_usage_census.sh with local bare repositories only:
    the results branch, the private store and the registry "mirrors"
    (REGISTRY_MIRROR_BASE). Records are dated 2099 so the synthetic skill
    copies' ctime precedes them (lc.FUTURE)."""

    _base = su.PublisherTests.__dict__
    SCRIPT, BRANCH = _base["SCRIPT"], _base["BRANCH"]
    setUp_publisher, git_ = _base["setUp"], _base["git"]
    seed, run_script, head = _base["seed"], _base["run_script"], _base["head"]
    del _base
    EVENTS = "persistent/usage-events"
    # The publisher's seed allowlist (su.make_allowlist_root) holds these two.
    PUB_NAME, FORK_NAME = OTHER_SKILL, "zz-skipped-skill"

    def git(self, *args, cwd=None):
        return self.git_(*args, cwd=cwd)

    def setUp(self):
        self.setUp_publisher()
        self.tmp = self.tmp.resolve()
        self.env["CENSUS_NOW"] = lc.NOW_FUTURE_TEXT
        claude = self.tmp / "home" / ".claude"
        self.pub_files, self.fork_files = skill_files("public text"), skill_files("fork edit")
        self.pub_skill = self.cache(claude, "mkt-pub", self.PUB_NAME, self.pub_files)
        self.fork_skill = self.cache(claude, "mkt-fork", self.FORK_NAME, self.fork_files)
        (claude / "plugins" / "known_marketplaces.json").write_text(json.dumps({
            "mkt-pub": {"source": {"source": "github", "repo": PUBLIC}},
            "mkt-fork": {"source": {"source": "github", "repo": FORK}}}), encoding="utf-8")
        # The public registry: SKILL's content is on main.
        self.shas = registry(self.tmp / "registry-work", [("2026-08-01T00:00:00Z", self.pub_files)],
                             name=self.PUB_NAME)
        mirror_of(self.tmp / "registry-work", self.tmp / "mirrors" / PUBLIC.split("/")[0]
                  / (PUBLIC.split("/")[1] + ".git"))
        self.env["REGISTRY_MIRROR_BASE"] = (self.tmp / "mirrors").as_uri() + "/"
        self.unpushed = "e" * 40                 # a commit the mirror never had
        (claude / "plugins" / "installed_plugins.json").write_text(json.dumps({
            "version": 2, "plugins": {
                "example-plugin@mkt-pub": [{"installPath": str(self.pub_skill.parent.parent),
                                            "gitCommitSha": self.shas[0]}],
                "example-plugin@mkt-fork": [{"installPath": str(self.fork_skill.parent.parent),
                                             "gitCommitSha": self.unpushed}]}}),
            encoding="utf-8")
        session = {"sessionId": SESSION}
        su.write_transcript(self.projects / "-home-example-proj" / "s.jsonl", [
            dict(lc.skill_call(self.PUB_NAME, "toolu_51"), **session),
            lc.meta(lc.base_text(self.pub_skill), sourceToolUseID="toolu_51"),
            dict(lc.skill_call(self.FORK_NAME, "toolu_52"), **session),
            lc.meta(lc.base_text(self.fork_skill), sourceToolUseID="toolu_52")],
            mtime=lc.NOW_FUTURE)
        scratch = self.tmp / "scratch"
        scratch.mkdir()
        self.d_pub = digest_of(self.pub_files, scratch)
        self.d_fork = digest_of(self.fork_files, scratch)

    def cache(self, claude, marketplace, name, files):
        root = claude / "plugins" / "cache" / marketplace / "example-plugin" / "1.0.0" / "skills" / name
        return lc.make_skill(root, files)

    def weekly(self):
        return json.loads(self.git("show", f"{self.BRANCH}:usage/weekly-local.json", cwd=self.origin))

    def store_text(self):
        names = self.git("ls-tree", "-r", "--name-only", self.EVENTS,
                         cwd=self.tmp / "events.git").split()
        return "".join(self.git("show", f"{self.EVENTS}:{n}", cwd=self.tmp / "events.git")
                       for n in names if n.startswith("events/"))

    def outputs(self, weekly: dict) -> dict:
        """The census document, the dashboard's usage_digests dataset and the
        explorer document, each as text, all from one published weekly file."""
        results = self.tmp / "results-tree"
        shutil.rmtree(results, ignore_errors=True)
        (results / "usage").mkdir(parents=True)
        (results / "usage" / "weekly-local.json").write_text(json.dumps(weekly), encoding="utf-8")
        _rows, _sources, digests = dashboard.usage(str(results))
        explorer = explorer_tree(self, weekly, {"adam-agentskills": self.tmp / "registry-work"},
                                 as_of="2099-01-08T13:00:00Z",
                                 names=[self.PUB_NAME, self.FORK_NAME])
        return {"census": json.dumps(weekly), "dashboard": json.dumps(digests),
                "explorer": explorer_data.finish(explorer)}

    def test_only_a_verified_prefix_reaches_the_three_outputs(self):
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("registry: not read", proc.stdout)
        weekly = self.weekly()
        rows = {r["name"]: r for r in weekly["rows"] if r["kind"] == "skill-digest"}
        self.assertEqual((rows[self.PUB_NAME]["digest"], rows[self.PUB_NAME]["repo"]), (self.d_pub[:12], PUBLIC))
        self.assertEqual((rows[self.FORK_NAME]["digest"], rows[self.FORK_NAME]["repo"]),
                         ("unknown:unlisted-registry", None))
        outputs = self.outputs(weekly)
        store = self.store_text()
        transcript = (self.projects / "-home-example-proj" / "s.jsonl").read_text(encoding="utf-8")
        # Each value is on the private side (so absence means something) ...
        for value in (FORK, SESSION, self.d_fork, self.unpushed, self.shas[0]):
            self.assertIn(value, store, value)
        self.assertIn(str(self.fork_skill), transcript)  # paths are never stored at all
        # ... and in none of the three public outputs.
        for label, text in outputs.items():
            for value in (FORK, "example-fork", SESSION, str(self.fork_skill), str(self.tmp),
                          self.d_fork[:12], self.unpushed, self.shas[0], self.d_pub):
                with self.subTest(output=label, value=value[:20]):
                    self.assertNotIn(value, text)
            with self.subTest(output=label, control="verified prefix"):
                self.assertIn(self.d_pub[:12], text)

    def test_the_fork_copy_publishes_its_prefix_once_its_registry_is_public(self):
        """The control for the fork rule: the same copy, from a public
        marketplace whose mirror holds the content, is published."""
        claude = self.tmp / "home" / ".claude"
        (claude / "plugins" / "known_marketplaces.json").write_text(json.dumps({
            "mkt-pub": {"source": {"source": "github", "repo": PUBLIC}},
            "mkt-fork": {"source": {"source": "github", "repo": PUBLIC}}}), encoding="utf-8")
        work = self.tmp / "registry-work"
        target = work / "plugins" / "example-plugin" / "skills" / self.FORK_NAME
        for rel, data in self.fork_files.items():
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            (target / rel).write_bytes(data)
        self.git("add", "-A", cwd=work)
        self.git("commit", "-q", "-m", "publish it", cwd=work)
        self.git("push", "-q", str(self.tmp / "mirrors" / "Adam-S-Daniel" / "adam-agentskills.git"),
                 "main", cwd=work)
        (claude / "plugins" / "installed_plugins.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.run_script().returncode, 0)
        rows = {r["name"]: r["digest"] for r in self.weekly()["rows"] if r["kind"] == "skill-digest"}
        self.assertEqual(rows[self.FORK_NAME], self.d_fork[:12])

    def test_a_failed_mirror_says_only_registry_not_read(self):
        self.env["REGISTRY_MIRROR_BASE"] = (self.tmp / "no-mirrors").as_uri() + "/"
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("; registry: not read;", proc.stdout)
        rows = {r["name"]: r["digest"] for r in self.weekly()["rows"] if r["kind"] == "skill-digest"}
        self.assertEqual(rows[self.PUB_NAME], "unknown:unverified-commit")
        printed = proc.stdout + proc.stderr
        for value in (str(self.tmp), "no-mirrors", "file://", PUBLIC, self.shas[0], self.d_pub[:12],
                      "adam-agentskills.git"):
            self.assertNotIn(value, printed)


# --- the explorer: copies and the loaded-copy alert ----------------------------

def explorer_census(skills):
    return {"include_private_names": False, "problems": [],
            "publication": {"as_of": "2026-10-31T14:00:00Z"},
            "registries": [{"name": "adam-agentskills", "private": False, "names_withheld": False,
                            "counts": {"covered": len(skills), "skipped": 0, "gap": 0,
                                       "total": len(skills)},
                            "skills": [{"skill": s, "bundle": "example-plugin", "status": "covered",
                                        "reason": None, "fixtures": 1} for s in skills]}]}


def explorer_tree(test, weekly, registries, as_of=ex72.AS_OF, names=(SKILL, OTHER_SKILL)):
    """explorer_data.build over a minimal results tree holding `weekly`."""
    tree = ex72.Tree(test)
    tree.write_json("coverage/latest.json", explorer_census(list(names)))
    if weekly is not None:
        tree.write_json("usage/weekly-local.json", weekly)
    return explorer_data.build(tree.tree, tree.roster, tree.policy, tree.evals, as_of,
                               ex72.SHA_A, ex72.SHA_B,
                               registries={k: {"path": Path(v)} for k, v in registries.items()})


class ExplorerCopiesTests(unittest.TestCase):
    """AS_OF 2026-10-31: the window is the weeks of Oct 19 and Oct 26."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="explorer-562-"))
        files = {k: skill_files(k) for k in ("ancient", "start", "inwindow")}
        registry(cls.tmp / "work", [("2026-09-01T00:00:00Z", files["ancient"]),
                                    ("2026-10-01T00:00:00Z", files["start"]),
                                    ("2026-10-22T00:00:00Z", files["inwindow"])])
        scratch = cls.tmp / "scratch"
        scratch.mkdir()
        cls.p = {k: digest_of(v, scratch)[:12] for k, v in files.items()}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def weekly(self, counts, to="2026-10-31T16:00:00Z", week="2026-10-26", source=True):
        rows = [skill_usage.digest_row(week, SKILL, PUBLIC, d, n, n) for d, n in counts]
        doc = {"generated_at": to, "schema": 1, "rows": rows,
               "sources": [{"surface": "local", "scope": "transcripts", "from": "2026-09-07T00:00:00Z",
                            "to": to, "sessions_scanned": 9}]}
        if source:
            doc["sources"].append(skill_usage.digest_source(
                datetime(2026, 9, 7, tzinfo=timezone.utc),
                datetime.fromisoformat(to.replace("Z", "+00:00")), sum(n for _, n in counts)))
        return doc

    def build(self, weekly, checkout=None):
        doc = explorer_tree(self, weekly, {"adam-agentskills": checkout or self.tmp / "work"})
        return doc, next(s for s in doc["skills"] if s["name"] == SKILL)

    def test_main_and_the_window_start_and_an_in_window_update(self):
        doc, skill = self.build(self.weekly([(self.p["start"], 5), (self.p["inwindow"], 1),
                                             ("unknown:gone", 7)]))
        copies = skill["copies"]
        self.assertEqual(copies["main"], self.p["inwindow"])
        self.assertEqual(copies["window"], {"from": "2026-10-19", "to": "2026-10-31"})
        self.assertEqual({e["digest"]: e["vs_main"] for e in copies["loaded"]},
                         {self.p["start"]: "in-window", self.p["inwindow"]: "current",
                          "unknown:gone": "unknown"})
        self.assertEqual(copies["alert"], {"local": False, "cloud": None})
        self.assertNotIn("loaded-copy", [a["kind"] for a in doc["alerts"]])
        explorer_data.finish(doc)

    def test_an_older_copy_that_leads_alerts(self):
        doc, skill = self.build(self.weekly([(self.p["ancient"], 5), (self.p["inwindow"], 2)]))
        self.assertEqual(skill["copies"]["alert"]["local"], True)
        self.assertIn({"kind": "loaded-copy", "subject": "skill", "name": SKILL, "surface": "local",
                       "loaded": self.p["ancient"], "main": self.p["inwindow"]}, doc["alerts"])
        self.assertIn('"loaded-copy"', explorer_data.finish(doc))

    def test_a_tie_with_a_main_copy_is_quiet(self):
        _, skill = self.build(self.weekly([(self.p["ancient"], 3), (self.p["inwindow"], 3)]))
        self.assertIs(skill["copies"]["alert"]["local"], False)

    def test_rows_outside_the_window_do_not_count(self):
        _, skill = self.build(self.weekly([(self.p["ancient"], 3)], week="2026-10-12"))
        self.assertEqual(skill["copies"]["loaded"], [])
        self.assertIsNone(skill["copies"]["alert"]["local"])

    def test_unknown_without_a_source_a_fresh_source_or_full_history(self):
        _, skill = self.build(self.weekly([(self.p["ancient"], 3)], source=False))
        self.assertIsNone(skill["copies"])
        _, skill = self.build(None)
        self.assertIsNone(skill["copies"])
        _, skill = self.build(self.weekly([(self.p["ancient"], 3)], to="2026-10-16T00:00:00Z",
                                          week="2026-10-19"))
        self.assertIsNone(skill["copies"]["alert"]["local"])
        shallow = self.tmp / "shallow"
        if not shallow.exists():
            git("clone", "-q", "--depth", "1", (self.tmp / "work").as_uri(), str(shallow),
                cwd=self.tmp)
        _, skill = self.build(self.weekly([(self.p["ancient"], 3)]), checkout=shallow)
        self.assertIsNone(skill["copies"]["main"])
        self.assertEqual(skill["copies"]["alert"], {"local": None, "cloud": None})
        self.assertEqual(skill["copies"]["loaded"][0]["vs_main"], "unknown")

    def test_finish_refuses_long_hex_in_copies_and_alerts_and_passes_the_normal_build(self):
        doc, skill = self.build(self.weekly([(self.p["ancient"], 5)]))
        self.assertEqual(doc["source"]["repository_commit"], ex72.SHA_A)   # 40 hex, allowed
        explorer_data.finish(doc)
        for label, value in (("64-hex", "a" * 64), ("40-hex", "b" * 40), ("13-hex", "c" * 13),
                             ("made-up reason", "unknown:made-up")):
            with self.subTest(where="copies", value=label):
                broken = json.loads(json.dumps(doc))
                target = next(s for s in broken["skills"] if s["name"] == SKILL)
                target["copies"]["loaded"][0]["digest"] = value
                with self.assertRaises(explorer_data.Refused):
                    explorer_data.finish(broken)
            with self.subTest(where="alert", value=label):
                broken = json.loads(json.dumps(doc))
                next(a for a in broken["alerts"] if a["kind"] == "loaded-copy")["loaded"] = value
                with self.assertRaises(explorer_data.Refused):
                    explorer_data.finish(broken)


class WorkflowTests(unittest.TestCase):

    def test_the_registry_checkouts_keep_full_history_and_reach_the_script(self):
        doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        steps = doc["jobs"]["build"]["steps"]
        checkouts = {s["with"]["repository"]: s["with"] for s in steps
                     if str(s.get("uses", "")).startswith("actions/checkout")
                     and "repository" in s.get("with", {})}
        run = "\n".join(s.get("run", "") for s in steps)
        for name, path in (("adam-agentskills", "registry-agentskills"),
                           ("cms-platform", "registry-cms"), ("adamdaniel.ai", "registry-site")):
            with self.subTest(name):
                self.assertEqual(checkouts[f"Adam-S-Daniel/{name}"]["fetch-depth"], 0)
                self.assertEqual(checkouts[f"Adam-S-Daniel/{name}"]["path"], path)
                self.assertIn(f'--registry "{name}=$GITHUB_WORKSPACE/{path}"', run)


if __name__ == "__main__":
    unittest.main()
