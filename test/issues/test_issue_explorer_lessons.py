#!/usr/bin/env python3
"""The Evals Explorer's `lessons` (Adam, 2026-11-03): the session miner's
lesson proposals, published with public-safe fields only.

The proposals come from private local sessions, so these tests pin what the
document may carry (kind, subject, count, dates, draft, record sources and
signal counts, for public subjects only) and what it must never carry (a
proposal's examples, repos, id or check sketch; a record's excerpt, session,
record id or repo; a private skill or repository's name).

Hermetic: invented proposals and records only (example.com), no network.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))
sys.path.insert(0, str(ROOT / "test"))

import explorer_data  # noqa: E402
from test_issue_72_explorer_data import AS_OF, SHA_A, SHA_B, Tree  # noqa: E402
from lockfile_pins import lock_problem  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "explorer-data.yml"
SECRET_TEXT = "invented-secret-excerpt"
MANIFEST = [{"id": "sec-one", "heading": "Section one", "bytes": 100, "status": "covered"}]


def proposal(subject, kind, count=3, first="2026-10-01", last="2026-10-20"):
    doc = {"schema_version": 1, "id": "0123456789ab", "subject": subject, "kind": kind,
           "evidence_count": count, "first_seen": first, "last_seen": last,
           "examples": [f"2026-10-01 private-repo [rule] {SECRET_TEXT}"],
           "repos": ["private-repo-name"]}
    if kind == "agent-check":
        doc["check_sketch"] = f"block {SECRET_TEXT}"
    return doc


_IDS = iter(range(10 ** 6))


def record(signal, kind, name, source="wsl", excerpt="something went wrong", repo="example-repo",
           record_id=None):
    return {"schema_version": 1, "record_id": record_id or f"r{next(_IDS)}{SECRET_TEXT}", "session": "s" + SECRET_TEXT,
            "date": "2026-10-05", "source": source, "repo": repo, "signal": signal,
            "excerpt": excerpt, "subject": {"kind": kind, "name": name}}


class LessonTree:
    """A results tree plus a proposals directory and a records directory."""

    def __init__(self, test: unittest.TestCase):
        self.t = Tree(test)
        self.proposals = self.t.root / "lessons" / "proposals"
        self.records = self.t.root / "lessons" / "records"
        self.records.mkdir(parents=True)

    def day(self, date, *docs):
        folder = self.proposals / date
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "DIGEST.md").write_text(f"# Lessons {date}\n{SECRET_TEXT}\n")
        for n, doc in enumerate(docs):
            (folder / f"p{n}__{doc.get('kind', 'x')}.json").write_text(json.dumps(doc))

    def write_records(self, *rows, name="2026-10-05.jsonl"):
        with open(self.records / name, "a", encoding="utf-8") as f:
            for row in rows:
                f.write((row if isinstance(row, str) else json.dumps(row)) + "\n")

    def build(self, drafts=None, records=True, lessons=True, context_repos=None):
        return explorer_data.build(
            self.t.tree, self.t.roster, self.t.policy, self.t.evals, AS_OF, SHA_A, SHA_B,
            manifest=MANIFEST, context_repos=context_repos,
            lessons=self.proposals if lessons else None, draft_prs=drafts,
            lesson_records=self.records if records else None)


class LessonsTests(unittest.TestCase):

    def setUp(self):
        self.lt = LessonTree(self)
        # alpha, beta, gamma are public in the census; "secret-skill" is not.
        self.lt.day("2026-10-30",
                    proposal("tool-bash-git", "new-skill", 9))
        self.lt.day("2026-11-01",
                    proposal("tool-edit", "new-skill", 4),
                    proposal("tool-bash-git", "new-skill", 6),
                    proposal("red-ci-skills-evals", "new-skill", 5),
                    proposal("red-ci-agent-guidance", "new-skill", 2),
                    proposal("red-ci-secret-repo", "new-skill", 8),
                    proposal("skill:alpha", "skill-edit", 3),
                    proposal("skill:alpha", "fixture-candidate", 2),
                    proposal("skill:secret-skill", "skill-edit", 7),
                    proposal("skill:secret-skill", "fixture-candidate", 1),
                    proposal("guidance:sec-one", "guidance-edit", 2),
                    proposal("guidance:sec-one", "fixture-candidate", 1),
                    proposal("guidance:not-in-manifest", "guidance-edit", 1),
                    proposal("memory", "memory-note", 3),
                    proposal("none", "memory-note", 1),
                    proposal("none", "agent-check", 2),
                    proposal("skill:alpha", "invented-kind", 1),
                    proposal("none", "new-skill", 1))
        bad = proposal("tool-read", "new-skill")
        bad["first_seen"] = "2026-13-40"
        folder = self.lt.proposals / "2026-11-01"
        (folder / "bad__new-skill.json").write_text(json.dumps(bad))
        (folder / "torn__new-skill.json").write_text("{")
        (self.lt.proposals / "not-a-day").mkdir()
        self.lt.write_records(
            record("red-ci-after-push", "none", "", repo="skills-evals"),
            record("red-ci-after-push", "none", "", source="windows", repo="skills-evals"),
            record("red-ci-after-push", "none", "", source="a-private-host", repo="skills-evals"),
            record("repeated-tool-failure", "none", "", excerpt="Bash:git failed 3x: boom"),
            record("rule", "skill", "alpha", source="cloud"),
            record("interrupted", "skill", "alpha"),
            record("redirection", "skill", "alpha"),
            record("rule", "skill", "alpha", source="windows",
                   excerpt="never commit `secrets.env` to the repo"),
            record("skill-invoked", "skill", "alpha"),
            record("rule", "guidance", "sec-one", record_id="dup-1"),
            record("rule", "guidance", "sec-one", record_id="dup-1"),  # counted once
            "{torn",
            json.dumps({"schema_version": 2, "signal": "rule", "subject": {"kind": "skill", "name": "alpha"}}))
        self.doc = self.lt.build(
            drafts={"tool-edit": {"number": 12, "state": "merged",
                                  "url": "https://github.com/Adam-S-Daniel/adam-agentskills/pull/12"}},
            context_repos={"Adam-S-Daniel/_agent-guidance": self.lt.t.root})
        self.lessons = self.doc["lessons"]

    def item(self, kind, subject):
        return next(i for i in self.lessons["items"] if i["kind"] == kind and i["subject"] == subject)

    def test_newest_day_only_and_sorted(self):
        self.assertEqual(self.lessons["date"], "2026-11-01")
        self.assertEqual([(i["kind"], i["subject"]) for i in self.lessons["items"]], [
            ("new-skill", "tool-bash-git"), ("new-skill", "red-ci-skills-evals"),
            ("new-skill", "tool-edit"), ("new-skill", "red-ci-agent-guidance"),
            ("skill-edit", "skill:alpha"), ("guidance-edit", "guidance:sec-one"),
            ("fixture-candidate", "skill:alpha"), ("fixture-candidate", "guidance:sec-one")])
        self.assertEqual(self.item("new-skill", "tool-bash-git")["evidence_count"], 6)

    def test_only_allowed_fields(self):
        for item in self.lessons["items"]:
            want = {"kind", "subject", "evidence_count", "first_seen", "last_seen",
                    "sources", "signals"} | ({"draft"} if item["kind"] == "new-skill" else set())
            self.assertEqual(set(item), want, item["subject"])
            self.assertIs(type(item["evidence_count"]), int)
        self.assertEqual(set(self.lessons), {"date", "items", "left_out", "issues"})
        self.assertIsNone(self.lessons["issues"])  # no --lesson-issues file
        text = explorer_data.finish(self.doc)
        for forbidden in (SECRET_TEXT, "private-repo-name", "0123456789ab", "check_sketch",
                          "examples", "\"repos\"", "secret-skill", "secret-repo",
                          "a-private-host", "secrets.env", "record_id", "excerpt"):
            self.assertNotIn(forbidden, text)

    def test_left_out_counts(self):
        self.assertEqual(self.lessons["left_out"], {
            "memory_note": 2, "agent_check": 1,
            # red-ci-secret-repo, and secret-skill's edit and fixture idea
            "private": 3,
            # guidance:not-in-manifest, an unknown kind, a new skill named none
            "other": 3})

    def test_drafts(self):
        self.assertEqual(self.item("new-skill", "tool-edit")["draft"], {
            "number": 12, "state": "merged",
            "url": "https://github.com/Adam-S-Daniel/adam-agentskills/pull/12"})
        self.assertIsNone(self.item("new-skill", "tool-bash-git")["draft"])

    def test_sources_and_signals_follow_the_miners_routing(self):
        ci = self.item("new-skill", "red-ci-skills-evals")
        self.assertEqual(ci["sources"], ["other", "windows", "wsl"])
        self.assertEqual(ci["signals"], {"red-ci-after-push": 3})
        self.assertEqual(self.item("new-skill", "tool-bash-git")["signals"],
                         {"repeated-tool-failure": 1})
        # The checkable rule went to agent-check; usage and schema-2 records
        # and a torn line count nowhere.
        edit = self.item("skill-edit", "skill:alpha")
        self.assertEqual(edit["sources"], ["cloud"])
        self.assertEqual(edit["signals"], {"rule": 1})
        fix = self.item("fixture-candidate", "skill:alpha")
        self.assertEqual(fix["signals"], {"interrupted": 1, "redirection": 1})
        self.assertEqual(self.item("guidance-edit", "guidance:sec-one")["signals"], {"rule": 1})
        self.assertEqual(self.item("new-skill", "tool-edit")["sources"], [])
        self.assertEqual(self.item("new-skill", "tool-edit")["signals"], {})

    def test_record_target_mirrors_route(self):
        self.assertEqual(explorer_data.record_target(record("rule", "memory", "memory")),
                         ("memory", "memory-note"))
        self.assertIsNone(explorer_data.record_target(record("skill-invoked", "skill", "alpha")))
        self.assertIsNone(explorer_data.record_target(record("abandoned", "none", "")))
        self.assertEqual(explorer_data.record_target(
            record("red-ci-after-push", "none", "", repo="adamdaniel.ai")),
            ("red-ci-adamdaniel-ai", "new-skill"))

    def test_without_records_sources_and_signals_are_unknown(self):
        doc = self.lt.build(records=False)
        for item in doc["lessons"]["items"]:
            self.assertIsNone(item["sources"])
            self.assertIsNone(item["signals"])
        explorer_data.finish(doc)

    def test_null_without_lessons(self):
        self.assertIsNone(self.lt.build(lessons=False)["lessons"])
        doc = explorer_data.build(
            self.lt.t.tree, self.lt.t.roster, self.lt.t.policy, self.lt.t.evals, AS_OF,
            SHA_A, SHA_B, manifest=[], lessons=self.lt.t.root / "missing")
        self.assertIsNone(doc["lessons"])

    def test_the_slug_comes_from_a_context_repo(self):
        without = self.lt.build(context_repos={})
        subjects = {i["subject"] for i in without["lessons"]["items"]}
        self.assertNotIn("red-ci-agent-guidance", subjects)
        self.assertIn("red-ci-skills-evals", subjects)  # this repository is always public
        self.assertEqual(without["lessons"]["left_out"]["private"], 4)

    def test_finish_refuses_an_extra_or_leaky_field(self):
        good = self.doc
        explorer_data.finish(good)
        item = dict(self.lessons["items"][0])
        for bad in ({**item, "examples": ["x"]}, {**item, "repos": []},
                    {**item, "sources": ["a-private-host"]},
                    {**item, "signals": {"skill-invoked": 1}},
                    {k: v for k, v in item.items() if k != "draft"}):
            with self.subTest(bad=sorted(bad)):
                leaked = {**good, "lessons": {**self.lessons, "items": [bad]}}
                with self.assertRaises(explorer_data.Refused):
                    explorer_data.finish(leaked)
        with self.assertRaises(explorer_data.Refused):
            explorer_data.finish({**good, "lessons": {**self.lessons, "left_out": {}}})

    def test_the_cli_passes_the_directories_and_the_draft_file(self):
        drafts, out = self.lt.t.root / "drafts.json", self.lt.t.root / "out.json"
        drafts.write_text(json.dumps([{"head": "draft-skill/tool-edit", "number": 3,
                                       "state": "open", "merged": False}]))
        code = explorer_data.main([
            "--results-tree", str(self.lt.t.tree), "--roster", str(self.lt.t.roster),
            "--policy", str(self.lt.t.policy), "--evals-dir", str(self.lt.t.evals),
            "--as-of", AS_OF, "--repository-commit", SHA_A, "--results-commit", SHA_B,
            "--lessons", str(self.lt.proposals), "--lesson-records", str(self.lt.records),
            "--draft-prs", str(drafts), "--out", str(out)])
        self.assertEqual(code, 0)
        lessons = json.loads(out.read_text())["lessons"]
        tool = next(i for i in lessons["items"] if i["subject"] == "tool-edit")
        self.assertEqual(tool["draft"]["number"], 3)
        self.assertEqual(lessons["left_out"]["private"], 4)


class DraftPrTests(unittest.TestCase):

    def load(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "drafts.json"
            path.write_text(rows if isinstance(rows, str) else json.dumps(rows))
            return explorer_data.load_draft_prs(path)

    def test_newest_number_wins_and_bad_rows_are_ignored(self):
        rows = [{"head": "draft-skill/tool-edit", "number": 5, "state": "closed", "merged": False},
                {"head": "draft-skill/tool-edit", "number": 9, "state": "closed", "merged": True},
                {"head": "draft-skill/tool-edit", "number": 7, "state": "open", "merged": False},
                {"head": "draft-skill/tool-bash", "number": 20, "state": "open", "merged": True},
                {"head": "draft-skill/tool-bash", "number": "21", "state": "open", "merged": False},
                {"head": "draft-skill/tool-bash", "number": True, "state": "open", "merged": False},
                {"head": "draft-skill/tool-bash", "number": 22, "state": "draft", "merged": False},
                {"head": "draft-skill/tool-bash", "number": 23, "state": "open", "merged": 0},
                {"head": "eval-improve/alpha", "number": 30, "state": "open", "merged": False},
                {"head": "draft-skill/Bad Name", "number": 31, "state": "open", "merged": False},
                {"number": 32, "state": "open", "merged": False}, "x", None]
        self.assertEqual(self.load(rows), {"tool-edit": {
            "number": 9, "state": "merged",
            "url": "https://github.com/Adam-S-Daniel/adam-agentskills/pull/9"}})

    def test_absent_or_unreadable_is_none(self):
        self.assertIsNone(explorer_data.load_draft_prs(None))
        self.assertIsNone(self.load("{"))
        self.assertIsNone(self.load({"head": "draft-skill/x"}))
        self.assertEqual(self.load([]), {})


def memory_row(repo="Adam-S-Daniel/example-repo", number=4, title=None, private=False,
               state="open", created="2026-10-29T10:00:00Z"):
    return {"repo": repo, "number": number, "state": state, "created_at": created,
            "title": title or "Memory promotion 2026-10-29: 3 facts for docs/EXAMPLE.md",
            "private": private}


def proposal_row(number=8, body="Skill name: `example-new-skill`\n" + SECRET_TEXT, **over):
    row = {"number": number, "state": "open", "created_at": "2026-10-27T10:00:00Z",
           "updated_at": "2026-10-28T10:00:00Z", "title": f"Proposal {SECRET_TEXT}",
           "body": body, "author_association": "OWNER", "user": {"login": "Adam-S-Daniel"},
           "labels": [{"name": "skill-proposal"}]}
    row.update(over)
    return row


class LessonIssueTests(unittest.TestCase):

    def load(self, doc):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "issues.json"
            path.write_text(doc if isinstance(doc, str) else json.dumps(doc))
            return explorer_data.load_lesson_issues(path)

    def test_memory_titles_give_count_and_target_only(self):
        rows = [memory_row(number=1),
                memory_row(number=2, title="Memory promotion 2026-10-29: 7 facts for 4 files"),
                memory_row(repo="jodidaniel/example-site", number=3,
                           title="Memory promotion 2026-10-28: 2 agent-checks"),
                memory_row(number=4, title="Memory promotion 2026-10-29: 1 fact for ../etc/passwd"),
                memory_row(number=5, title="Memory promotion 2026-10-29: 1 fact for SKILL.md")]
        items = self.load({"memory": rows, "proposals": []})
        got = {i["number"]: (i["count"], i["target"]) for i in items}
        self.assertEqual(got, {1: (3, "docs/EXAMPLE.md"), 2: (7, "4 files"), 3: (2, "agent-checks"),
                               4: (1, None), 5: (1, "SKILL.md")})
        first = next(i for i in items if i["number"] == 1)
        self.assertEqual(first, {"source": "memory", "repo": "Adam-S-Daniel/example-repo",
                                 "number": 1, "state": "open", "opened": "2026-10-29",
                                 "count": 3, "target": "docs/EXAMPLE.md",
                                 "url": "https://github.com/Adam-S-Daniel/example-repo/issues/1"})

    def test_memory_rows_off_the_rules_are_dropped(self):
        rows = [memory_row(private=True), memory_row(private=None), memory_row(private="false"),
                memory_row(repo="someone-else/example-repo"), memory_row(repo="no-slash"),
                memory_row(title="Something else entirely"),
                memory_row(title="Memory promotion 2026-10-29: 3 facts for x " + SECRET_TEXT),
                memory_row(state="merged"), memory_row(number=True), memory_row(created="soon"),
                "x", None]
        self.assertEqual(self.load({"memory": rows, "proposals": []}), [])

    def test_proposals_need_the_owner_the_label_and_a_name_line(self):
        rows = [proposal_row(number=1), proposal_row(number=2, state="closed"),
                proposal_row(number=3, author_association="CONTRIBUTOR"),
                proposal_row(number=4, user={"login": "someone-else"}),
                proposal_row(number=5, labels=[]),
                proposal_row(number=6, body="no name line"),
                proposal_row(number=7, body="Skill name: `Not A Subject`"),
                proposal_row(number=9, pull_request={})]
        items = self.load({"memory": [], "proposals": rows})
        self.assertEqual([(i["number"], i["state"], i["target"]) for i in items],
                         [(1, "open", "example-new-skill"), (2, "closed", "example-new-skill")])
        self.assertEqual(items[0]["url"],
                         "https://github.com/Adam-S-Daniel/adam-agentskills/issues/1")
        self.assertIsNone(items[0]["count"])

    def test_order_memory_first_newest_first(self):
        items = self.load({"memory": [memory_row(number=1, created="2026-10-01T00:00:00Z"),
                                      memory_row(number=2)],
                           "proposals": [proposal_row(number=3)]})
        self.assertEqual([(i["source"], i["number"]) for i in items],
                         [("memory", 2), ("memory", 1), ("proposal", 3)])

    def test_absent_or_off_shape_is_none(self):
        self.assertIsNone(explorer_data.load_lesson_issues(None))
        self.assertIsNone(self.load("{"))
        self.assertIsNone(self.load([]))
        self.assertIsNone(self.load({"memory": []}))

    def test_in_the_document_and_through_the_gate(self):
        lt = LessonTree(self)
        issues = self.load({"memory": [memory_row()], "proposals": [proposal_row()]})
        doc = lt.build(lessons=False, records=False)
        self.assertIsNone(doc["lessons"])
        doc = explorer_data.build(lt.t.tree, lt.t.roster, lt.t.policy, lt.t.evals, AS_OF,
                                  SHA_A, SHA_B, manifest=[], lesson_issues=issues)
        self.assertEqual(doc["lessons"], {"date": None, "items": None, "left_out": None,
                                          "issues": issues})
        text = explorer_data.finish(doc)
        self.assertNotIn(SECRET_TEXT, text)
        self.assertNotIn("Memory promotion", text)
        for bad in ({**issues[0], "title": "x"}, {**issues[0], "url": "https://github.com/x/y/issues/1"},
                    {k: v for k, v in issues[0].items() if k != "count"}):
            with self.subTest(bad=sorted(bad)):
                with self.assertRaises(explorer_data.Refused):
                    explorer_data.finish({**doc, "lessons": {**doc["lessons"], "issues": [bad]}})

    def test_the_cli_passes_the_file(self):
        lt = LessonTree(self)
        path, out = lt.t.root / "issues.json", lt.t.root / "out.json"
        path.write_text(json.dumps({"memory": [memory_row()], "proposals": []}))
        code = explorer_data.main([
            "--results-tree", str(lt.t.tree), "--roster", str(lt.t.roster),
            "--policy", str(lt.t.policy), "--evals-dir", str(lt.t.evals),
            "--as-of", AS_OF, "--repository-commit", SHA_A, "--results-commit", SHA_B,
            "--lesson-issues", str(path), "--out", str(out)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.read_text())["lessons"]["issues"][0]["number"], 4)


class WorkflowLessonTests(unittest.TestCase):

    def setUp(self):
        self.steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["build"]["steps"]

    def step(self, name):
        return next(s for s in self.steps if s["name"] == name)

    def test_every_lessons_step_is_continue_on_error(self):
        for name in ("Mint the read-only token for the lessons", "Look for the lessons branch",
                     "Check out the lesson proposals (adam-agentskills-private)",
                     "List the skill draft pull requests",
                     "List the memory promotion and skill proposal issues"):
            with self.subTest(step=name):
                self.assertIs(self.step(name).get("continue-on-error"), True)

    def test_the_token_is_read_only_and_for_the_private_repo_alone(self):
        mint = self.step("Mint the read-only token for the lessons")
        self.assertTrue(mint["uses"].startswith("actions/create-github-app-token@"))
        self.assertIsNone(lock_problem(mint["uses"], WORKFLOW))
        self.assertEqual(mint["with"]["repositories"], "adam-agentskills-private")
        self.assertEqual(mint["with"]["permission-contents"], "read")
        checkout = self.step("Check out the lesson proposals (adam-agentskills-private)")
        self.assertEqual(checkout["with"]["ref"], "persistent/lessons")
        self.assertEqual(checkout["with"]["sparse-checkout"], "lessons")
        self.assertIs(checkout["with"]["persist-credentials"], False)

    def test_the_issue_listing_searches_both_owners_and_checks_privacy(self):
        run = self.step("List the memory promotion and skill proposal issues")["run"]
        self.assertIn("for owner in Adam-S-Daniel jodidaniel", run)
        self.assertIn('[ "$private" = false ] || continue', run)
        self.assertIn("labels=skill-proposal&state=all", run)
        self.assertNotIn("${{", run)

    def test_the_flags_are_passed_only_when_present(self):
        run = self.step("Build the explorer data")["run"]
        for flag in ("--lessons", "--lesson-records", "--draft-prs", "--lesson-issues"):
            self.assertIn(f"lessons+=({flag} ", run)
        self.assertIn('"${lessons[@]}"', run)


if __name__ == "__main__":
    unittest.main()
