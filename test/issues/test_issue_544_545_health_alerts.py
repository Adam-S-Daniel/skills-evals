#!/usr/bin/env python3
"""skills-evals#544 and #545: the explorer's `broken` and `context-drift` alerts.

#544: an in-place fixture whose consumer `skills.lock`, at the fixture's pin,
adopts an older copy of the skill than main has is `broken` (reason
`pin-deploys-older-copy`): its with arm tests the old copy and never pools.
#545: the skills deployed beside the subject moved on the consumer's
first-parent history and stayed moved for CONTEXT_DRIFT_DAYS: `context-drift`
with `drift_since`. Both are report-only and public, so the HEALTH FILTER must
drop every private fixture before any Git read or count.

Hermetic: the consumer repositories are temporary Git repos, checked out the
way actions/checkout does it (`git init` + `git fetch`, no set-head), every
commit carries a fixed committer date, and `now` is passed in. No network, no
clock, no sleeps.
"""

from __future__ import annotations

import ast
import contextlib
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import explorer_data  # noqa: E402

context = explorer_data.context_mod
REG_URL = "https://github.com/Adam-S-Daniel/adam-agentskills"
PRIVATE_URL = explorer_data.plan_week.PRIVATE_REGISTRY_URL
CONSUMER = "Example-Owner/consumer"
OTHER = "Example-Owner/other-consumer"
GUIDANCE_PIN = "c" * 40
BUDGET = {"guidance_bytes": 1000, "skill_catalog_bytes": 1000, "skill_payload_bytes": 1000}
SKILL_MD = b"---\nname: x\ndescription: invented skill for a test\n---\nbody\n"
CURRENT = context._file_digest({"SKILL.md": SKILL_MD})  # the skill on main
STALE = "1" * 64
#: A private skill name distinctive enough that any occurrence is a leak.
PRIVATE_NAME = "zz-private-distinct-tool"
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
AS_OF = "2026-10-20T12:00:00Z"


def day(n: int) -> str:
    """An ISO committer date on day `n` of October 2026, noon UTC."""
    return f"2026-10-{n:02d}T12:00:00Z"


def git(cwd: Path, *args: str, date: str = day(1)) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
               GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main",
         "-c", "protocol.file.allow=always", *args],
        cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


def lock_bytes(skills: dict) -> bytes:
    bundles = sorted({k.split("/")[0] for k in skills})
    return json.dumps({"registry": "Adam-S-Daniel/adam-agentskills", "ref": "main",
                       "bundles": bundles,
                       "skills": {k: "sha256:" + v for k, v in sorted(skills.items())}},
                      indent=1).encode()


class Consumer:
    """A consumer repository's source, committed one lock at a time."""

    def __init__(self, root: Path, name: str):
        self.src = root / f"src-{name}"
        self.src.mkdir()
        git(self.src, "init", "-q")
        self.root = root
        self.name = name

    def commit(self, skills: dict | None, when: int, note: str = "x",
               raw: bytes | None = None, note_file: str = "note.txt") -> str:
        """Commit the lock `skills` (None: no lock change; `raw`: these bytes)."""
        (self.src / note_file).write_text(f"{note} {when}\n")
        if raw is not None:
            (self.src / "skills.lock").write_bytes(raw)
        elif skills is not None:
            (self.src / "skills.lock").write_bytes(lock_bytes(skills))
        git(self.src, "add", "-A")
        git(self.src, "commit", "-q", "-m", f"{note} {when}", date=day(when))
        return git(self.src, "rev-parse", "HEAD")

    def checkout(self, depth: int | None = None) -> Path:
        """What actions/checkout makes: `git init`, then fetch the branches."""
        out = self.root / f"checkout-{self.name}-{depth}"
        out.mkdir()
        git(out, "init", "-q")
        fetch = ["fetch", "-q", "--no-tags"] + ([f"--depth={depth}"] if depth else [])
        git(out, *fetch, "file://" + str(self.src), "+refs/heads/*:refs/remotes/origin/*")
        git(out, "checkout", "-q", "-B", "main", "refs/remotes/origin/main")
        return out


class World:
    """A skills-evals checkout (committed evals/), registries and consumers."""

    def __init__(self, test: unittest.TestCase):
        tmp = tempfile.TemporaryDirectory(prefix="health-")
        test.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = self.root / "skills-evals"
        self.evals = self.repo / "evals"
        self.evals.mkdir(parents=True)
        self.scheduled: list = []
        self.registries_root = self.root / "registries"
        self.repositories: dict = {}

    def skill(self, registry: str, bundle: str, name: str) -> None:
        d = self.registries_root / registry / "plugins" / bundle / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_bytes(SKILL_MD)

    def registries(self) -> dict:
        names = [p.name for p in sorted(self.registries_root.iterdir())] \
            if self.registries_root.is_dir() else []
        return explorer_data.compute_gates.flag_registries(
            [f"{n}={self.registries_root / n}" for n in names])

    def fixture(self, rel: str, skill: str, revision: str, *, repository: str = CONSUMER,
                registry: str = REG_URL, scheduled: bool = True, **extra) -> str:
        d = self.evals / rel
        d.mkdir(parents=True)
        doc = {"skill": skill, "registry": registry, "prompt": "invented",
               "context": {"repository": repository, "revision": revision,
                           "guidance_revision": GUIDANCE_PIN, "budget": BUDGET}, **extra}
        (d / "fixture.yaml").write_text(yaml.safe_dump(doc))
        if scheduled:
            self.scheduled.append(f"evals/{rel}")
        return f"evals/{rel}"

    def commit(self) -> None:
        (self.evals / "scheduled.yml").write_text(yaml.safe_dump(
            {"fixtures": [{"path": p, "readiness": "invented"} for p in self.scheduled]}))
        if not (self.repo / ".git").exists():
            git(self.repo, "init", "-q")
        git(self.repo, "add", "-A")

    def run(self, names=("subj",), now=NOW):
        self.commit()
        return explorer_data.health_alerts(self.evals, set(names), self.registries(),
                                           self.repositories, now)


def kinds(alerts: list) -> list:
    return sorted((a["kind"], a["fixture"]) for a in alerts)


class BrokenTests(unittest.TestCase):
    """#544: a pin that deploys an older copy of the subject."""

    def setUp(self):
        self.w = World(self)
        self.w.skill("adam-agentskills", "b1", "subj")
        self.c = Consumer(self.w.root, "c")

    def one(self, skills, raw=None, mapped=True):
        pin = self.c.commit(skills, 1, raw=raw)
        if mapped:
            self.w.repositories[CONSUMER] = self.c.checkout()
        fx = self.w.fixture("subj", "subj", pin)
        return fx, self.w.run()

    def test_an_adopted_stale_copy_is_broken(self):
        fx, (alerts, bu, du, _rows) = self.one({"b1/subj": STALE, "b1/sib": "2" * 64})
        self.assertEqual(alerts, [{"kind": "broken", "subject": "skill", "name": "subj",
                                   "fixture": fx, "model": None,
                                   "reasons": ["pin-deploys-older-copy"]}])
        self.assertEqual((bu, du), (0, 0))

    def test_an_adopted_current_copy_is_not(self):
        _fx, (alerts, bu, _du, rows) = self.one({"b1/subj": CURRENT})
        self.assertEqual(alerts, [])
        self.assertEqual((bu, rows[0]["broken"]), (0, "ok"))

    def test_a_lock_that_does_not_adopt_the_subject_is_not_applicable(self):
        _fx, (alerts, bu, _du, rows) = self.one({"b1/sib": "2" * 64})
        self.assertEqual((alerts, bu, rows[0]["broken"]), ([], 0, "n/a"))

    def test_no_lock_at_the_pin_is_not_applicable(self):
        _fx, (alerts, bu, du, rows) = self.one(None)
        self.assertEqual((alerts, bu, du), ([], 0, 0))
        self.assertEqual((rows[0]["broken"], rows[0]["drift"]), ("n/a", "n/a"))

    def test_an_invalid_lock_is_unknown(self):
        _fx, (alerts, bu, du, _rows) = self.one(None, raw=b'{"skills": {}}')
        self.assertEqual((alerts, bu, du), ([], 1, 1))

    def test_a_missing_checkout_is_unknown(self):
        _fx, (alerts, bu, du, _rows) = self.one({"b1/subj": STALE}, mapped=False)
        self.assertEqual((alerts, bu, du), ([], 1, 1))

    def test_a_skill_adopted_under_two_bundles_is_unknown(self):
        _fx, (alerts, bu, du, _rows) = self.one({"b1/subj": STALE, "b2/subj": STALE})
        self.assertEqual((alerts, bu, du), ([], 1, 1))

    def test_an_adopted_skill_with_no_main_copy_is_unknown(self):
        pin = self.c.commit({"b1/ghost": STALE}, 1)
        self.w.repositories[CONSUMER] = self.c.checkout()
        self.w.fixture("ghost", "ghost", pin)
        alerts, bu, du, rows = self.w.run(names=("ghost",))
        self.assertEqual((alerts, bu, du, rows[0]["broken"]), ([], 1, 0, "unknown"))


class DriftTests(unittest.TestCase):
    """#545: the in-scope lock entries left the pin's and stayed away."""

    BASE = {"b1/subj": CURRENT, "b1/sib": "2" * 64, "b2/other": "3" * 64}

    def setUp(self):
        self.w = World(self)
        self.w.skill("adam-agentskills", "b1", "subj")
        self.c = Consumer(self.w.root, "c")
        self.pin = self.c.commit(self.BASE, 1)

    def run_with(self, now=NOW, depth=None, revision=None, skill="subj"):
        self.w.repositories[CONSUMER] = self.c.checkout(depth=depth)
        self.w.fixture(skill, skill, revision or self.pin)
        return self.w.run(names=(skill,), now=now)

    def bump(self, key, value, when):
        return self.c.commit({**self.BASE, key: value}, when)

    def test_no_lock_change_is_no_drift(self):
        self.c.commit(None, 5, note="unrelated")
        alerts, _bu, du, rows = self.run_with()
        self.assertEqual((alerts, du, rows[0]["drift"]), ([], 0, "ok"))

    def test_an_in_scope_change_older_than_the_window_alerts_with_its_date(self):
        self.bump("b1/sib", "4" * 64, 5)
        self.c.commit(None, 6, note="unrelated")
        alerts, _bu, du, _rows = self.run_with()
        self.assertEqual(alerts, [{"kind": "context-drift", "subject": "skill", "name": "subj",
                                   "fixture": "evals/subj", "model": None,
                                   "repository": CONSUMER, "drift_since": day(5)}])
        self.assertEqual(du, 0)

    def test_the_window_is_the_re_pin_cadence(self):
        self.assertEqual(explorer_data.CONTEXT_DRIFT_DAYS, 7)
        self.bump("b1/sib", "4" * 64, 14)  # 6 days before NOW
        alerts, _bu, du, rows = self.run_with()
        self.assertEqual((alerts, du, rows[0]["drift_since"]), ([], 0, day(14)))
        self.assertEqual(rows[0]["drift"], "ok")

    def test_a_change_exactly_at_the_window_alerts(self):
        self.bump("b1/sib", "4" * 64, 13)  # 7 days before NOW, to the second
        alerts, _bu, _du, _rows = self.run_with()
        self.assertEqual([a["drift_since"] for a in alerts], [day(13)])

    def test_an_out_of_scope_change_is_not_drift_for_an_adopted_subject(self):
        self.bump("b2/other", "4" * 64, 5)
        alerts, _bu, du, rows = self.run_with()
        self.assertEqual((alerts, du, rows[0]["scope"]), ([], 0, "b1"))

    def test_any_bundle_is_in_scope_when_the_subject_is_not_adopted(self):
        self.c.commit({"b2/other": "3" * 64, "b3/x": "5" * 64}, 2)
        pin = git(self.c.src, "rev-parse", "HEAD")
        self.c.commit({"b2/other": "4" * 64, "b3/x": "5" * 64}, 5)
        alerts, _bu, _du, rows = self.run_with(revision=pin)
        self.assertEqual([(a["kind"], a["drift_since"]) for a in alerts],
                         [("context-drift", day(5))])
        self.assertEqual((rows[0]["broken"], rows[0]["scope"]), ("n/a", "all bundles"))

    def test_the_subjects_own_bump_is_not_context(self):
        self.bump("b1/subj", "6" * 64, 5)
        alerts, _bu, _du, _rows = self.run_with()
        self.assertEqual([a["kind"] for a in alerts], [])

    def test_a_change_reverted_to_the_pins_entries_is_no_drift(self):
        self.bump("b1/sib", "4" * 64, 3)
        self.c.commit(self.BASE, 5)
        alerts, _bu, du, _rows = self.run_with()
        self.assertEqual((alerts, du), ([], 0))

    def test_change_revert_change_dates_from_the_second_change(self):
        self.bump("b1/sib", "4" * 64, 3)
        self.c.commit(self.BASE, 4)
        self.bump("b1/sib", "5" * 64, 6)
        self.bump("b1/sib", "7" * 64, 8)  # still drifted: the date stays at 6
        alerts, _bu, _du, _rows = self.run_with()
        self.assertEqual([a["drift_since"] for a in alerts], [day(6)])

    def test_a_shallow_clone_is_unknown(self):
        self.bump("b1/sib", "4" * 64, 5)
        pin = git(self.c.src, "rev-parse", "HEAD~1")
        self.c.commit(None, 6, note="unrelated")
        alerts, bu, du, _rows = self.run_with(depth=3, revision=pin)
        self.assertEqual((alerts, bu, du), ([], 0, 1))

    def test_a_pin_that_is_not_an_ancestor_of_head_is_unknown(self):
        git(self.c.src, "checkout", "-q", "-b", "side")
        side = self.c.commit({**self.BASE, "b1/sib": "4" * 64}, 2)
        git(self.c.src, "checkout", "-q", "main")
        self.bump("b1/sib", "5" * 64, 5)
        alerts, bu, du, _rows = self.run_with(revision=side)
        self.assertEqual((alerts, bu, du), ([], 0, 1))

    def test_a_pin_off_the_first_parent_chain_is_unknown(self):
        git(self.c.src, "checkout", "-q", "-b", "side")
        side = self.c.commit({**self.BASE, "b1/sib": "4" * 64}, 2)
        git(self.c.src, "checkout", "-q", "main")
        self.c.commit(None, 3, note="main moves", note_file="main.txt")
        git(self.c.src, "merge", "-q", "--no-ff", "-m", "merge side", "side", date=day(4))
        alerts, _bu, du, _rows = self.run_with(revision=side)
        self.assertEqual((alerts, du), ([], 1))

    def test_an_unreadable_lock_in_the_history_is_unknown(self):
        self.c.commit(None, 3, raw=b"not json")
        self.bump("b1/sib", "4" * 64, 5)
        alerts, _bu, du, _rows = self.run_with()
        self.assertEqual((alerts, du), ([], 1))

    def test_the_lock_history_reader_refuses_any_other_git_command(self):
        reader = explorer_data._LockHistory(self.w.root)
        for args in (("fetch", "origin"), ("rev-list", "--first-parent", "HEAD"),
                     ("cat-file", "blob", "HEAD:skills.lock"),
                     ("show", f"{self.pin}:skills.lock"),
                     ("rev-list", "--first-parent", "--reverse", f"{self.pin}..{self.pin}",
                      "--", "other")):
            with self.subTest(args=args), self.assertRaises(explorer_data._Undecided):
                reader.run(*args)


class PrivacyTests(unittest.TestCase):
    """The HEALTH FILTER runs before any read or count, for both alerts."""

    def world(self, case: str, private: bool) -> World:
        w = World(self)
        c = Consumer(w.root, "c")
        if case == "broken":
            pin = c.commit({"b1/pub": STALE, "b1/col": STALE, "pb/" + PRIVATE_NAME: STALE}, 1)
        else:
            pin = c.commit({"b1/pub": CURRENT, "b1/col": CURRENT, "b1/sib": "2" * 64,
                            "pb/" + PRIVATE_NAME: CURRENT, "pb/psib": "2" * 64}, 1)
            c.commit({"b1/pub": CURRENT, "b1/col": CURRENT, "b1/sib": "4" * 64,
                      "pb/" + PRIVATE_NAME: CURRENT, "pb/psib": "4" * 64}, 3)
        w.repositories[CONSUMER] = c.checkout()
        for name in ("pub", "col"):
            w.skill("adam-agentskills", "b1", name)
        w.skill("adam-agentskills-private", "pb", PRIVATE_NAME)
        w.fixture("pub", "pub", pin)
        # A public fixture of a skill whose name a private fixture also uses.
        w.fixture("col/public", "col", pin)
        if private:
            w.fixture("col/private-twin", "col", pin, registry=PRIVATE_URL)
            w.fixture(PRIVATE_NAME, PRIVATE_NAME, pin, registry=PRIVATE_URL)
            # Would be unknown if it were ever counted: no checkout is mapped.
            w.fixture(f"{PRIVATE_NAME}-elsewhere", PRIVATE_NAME, pin, repository=OTHER,
                      registry=PRIVATE_URL)
        w.commit()
        return w

    def document(self, w: World) -> tuple:
        """The full public document (build + finish) for the world."""
        tree = w.root / "tree"
        (tree / "coverage").mkdir(parents=True)
        (tree / "coverage" / "latest.json").write_text(json.dumps({
            "publication": {"as_of": AS_OF},
            "registries": [
                {"name": "adam-agentskills", "private": False,
                 "counts": {"covered": 2, "skipped": 0, "gap": 0, "total": 2},
                 "skills": [{"skill": "pub", "status": "covered"},
                            {"skill": "col", "status": "covered"}]},
                {"name": "adam-agentskills-private", "private": True,
                 "skills": [{"skill": PRIVATE_NAME, "status": "covered"}]}]}))
        roster = w.root / "roster.yml"
        roster.write_text(yaml.safe_dump({"arms": [{"id": "model-a"}],
                                          "judge": {"id": "model-j"}}))
        policy = ROOT / "evals" / "gate-policy.yml"
        doc = explorer_data.build(tree, roster, policy, w.evals, AS_OF, "a" * 40, "b" * 40,
                                  registries=w.registries(), context_repos=w.repositories)
        return doc, explorer_data.finish(doc)

    @staticmethod
    def unfiltered(evals_dir, _skill_names):
        """The HEALTH FILTER switched off: every scheduled fixture with a context."""
        sched = yaml.safe_load((evals_dir / "scheduled.yml").read_text())
        out = []
        for row in sched["fixtures"]:
            doc = yaml.safe_load((evals_dir.parent / row["path"] / "fixture.yaml").read_text())
            out.append({"fixture": row["path"], "skill": doc["skill"], "bundle": None,
                        "registry": doc["registry"], "context": doc["context"]})
        return out

    def test_private_names_never_reach_the_document(self):
        for case in ("broken", "context-drift"):
            with self.subTest(case=case):
                w = self.world(case, private=True)
                doc, text = self.document(w)
                self.assertNotIn(PRIVATE_NAME, text)
                self.assertNotIn("private-twin", text)
                health = [a for a in doc["alerts"] if a["kind"] == case]
                # The colliding public fixture is filtered too; only `pub` alerts.
                self.assertEqual([a["fixture"] for a in health], ["evals/pub"])
                self.assertEqual((doc["broken_unknown"], doc["context_drift_unknown"]), (0, 0))

    def test_negative_control_the_private_fixture_would_alert_unfiltered(self):
        for case in ("broken", "context-drift"):
            with self.subTest(case=case):
                w = self.world(case, private=True)
                with mock.patch.object(explorer_data, "health_fixtures", self.unfiltered):
                    doc, _text = self.document(w)
                alerts = [a for a in doc["alerts"] if a["kind"] == case]
                self.assertIn(PRIVATE_NAME, {a["name"] for a in alerts})
                self.assertIn(PRIVATE_NAME, json.dumps(doc))
                self.assertGreater(doc["broken_unknown"] + doc["context_drift_unknown"], 0)

    def test_unknown_counts_do_not_move_with_a_private_fixture(self):
        for case in ("broken", "context-drift"):
            with self.subTest(case=case):
                with_private = self.document(self.world(case, private=True))[0]
                without = self.document(self.world(case, private=False))[0]
                for key in ("broken_unknown", "context_drift_unknown"):
                    self.assertEqual(with_private[key], without[key], key)

    def test_finish_accepts_the_document(self):
        doc, text = self.document(self.world("context-drift", private=True))
        self.assertNotRegex(text, r"[0-9a-f]{64}")
        self.assertNotIn("@", text.replace("https://", ""))
        kinds_seen = {a["kind"] for a in doc["alerts"]}
        self.assertIn("context-drift", kinds_seen)
        for alert in doc["alerts"]:
            if alert["kind"] in ("broken", "context-drift"):
                self.assertLessEqual(set(alert), {"kind", "subject", "name", "fixture", "model",
                                                  "reasons", "repository", "drift_since"})


class FilterTests(unittest.TestCase):

    def test_only_scheduled_public_skill_fixtures_with_a_context_are_in_scope(self):
        w = World(self)
        pin = "a" * 40
        w.fixture("pub", "pub", pin)
        w.fixture("unlisted", "unlisted", pin)  # no public census row
        w.fixture("pub-off", "pub", pin, scheduled=False)
        d = w.evals / "iso"
        d.mkdir()
        (d / "fixture.yaml").write_text(yaml.safe_dump({"skill": "pub", "prompt": "x"}))
        w.scheduled.append("evals/iso")
        d = w.evals / "guidance" / "sec" / "g"
        d.mkdir(parents=True)
        (d / "fixture.yaml").write_text(yaml.safe_dump({"subject": "guidance", "section": "sec"}))
        w.scheduled.append("evals/guidance/sec/g")
        w.commit()
        got = explorer_data.health_fixtures(w.evals, {"pub"})
        self.assertEqual([e["fixture"] for e in got], ["evals/pub"])


class ReportTests(unittest.TestCase):

    def test_the_local_report_prints_the_in_scope_rows(self):
        w = World(self)
        w.skill("adam-agentskills", "b1", "subj")
        c = Consumer(w.root, "c")
        pin = c.commit({"b1/subj": STALE, "b1/sib": "2" * 64}, 1)
        c.commit({"b1/subj": STALE, "b1/sib": "4" * 64, "b1/new": "5" * 64}, 5)
        w.fixture("subj", "subj", pin)
        w.commit()
        tree = w.root / "tree" / "coverage"
        tree.mkdir(parents=True)
        (tree / "latest.json").write_text(json.dumps({"registries": [
            {"name": "adam-agentskills", "private": False, "skills": [{"skill": "subj"}]}]}))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = explorer_data.main([
                "context-drift-report", "--results-tree", str(w.root / "tree"),
                "--as-of", AS_OF, "--evals-dir", str(w.evals),
                "--registry", f"adam-agentskills={w.registries_root / 'adam-agentskills'}",
                "--context-repo", f"{CONSUMER}={c.checkout()}"])
        self.assertEqual(code, 0)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0].split(), ["fixture", "broken", "drift", "adopted", "scope",
                                            "changed", "added", "removed", "drift_since"])
        self.assertEqual(lines[1].split(),
                         ["evals/subj", "alert", "alert", "True", "b1", "1", "1", "0", day(5)])


class WorkflowAndPageTests(unittest.TestCase):

    def test_every_context_repo_is_full_history_and_passed(self):
        wf = yaml.safe_load((ROOT / ".github/workflows/explorer-data.yml").read_text())
        steps = wf["jobs"]["build"]["steps"]
        checkouts = {s["with"]["path"]: s["with"] for s in steps
                     if s.get("uses", "").startswith("actions/checkout@")
                     and s["with"].get("path") != "eval-results"}
        for path, opts in checkouts.items():
            with self.subTest(path=path):
                self.assertEqual(opts.get("fetch-depth"), 0)
                self.assertIs(opts.get("persist-credentials"), False)
        self.assertEqual(checkouts["registry-site"].get("filter"), "blob:none")
        run = next(s["run"] for s in steps if s.get("name") == "Build the explorer data")
        flags = {}
        for token in run.split("--context-repo")[1:]:
            name, path = token.split()[0].strip('"').split("=", 1)
            flags[name] = path.split("/")[-1]
        self.assertEqual(flags, {
            "Adam-S-Daniel/skills-evals": "skills-evals",
            "Adam-S-Daniel/adam-agentskills": "registry-agentskills",
            "Adam-S-Daniel/cms-platform": "registry-cms",
            "Adam-S-Daniel/adamdaniel.ai": "registry-site",
            "Adam-S-Daniel/_agent-guidance": "agent-guidance",
            "Adam-S-Daniel/repo-settings": "context-repo-settings",
            "Adam-S-Daniel/wsl-automation": "context-wsl-automation"})
        self.assertEqual(set(flags.values()), set(checkouts))

    def test_the_page_lists_every_kind_the_script_can_emit(self):
        """Parse explorer_data.py (a real AST, not a pattern): every dict
        literal with a constant `"kind"` key is an alert the page must label;
        tool/test/run.js checks each listed kind has a label."""
        tree = ast.parse((ROOT / "scripts" / "explorer_data.py").read_text(encoding="utf-8"))
        emitted = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "kind":
                        self.assertIsInstance(value, ast.Constant, "a kind must be a literal")
                        emitted.add(value.value)
        listed = json.loads((ROOT / "tool" / "test" / "alert-kinds.json").read_text())
        self.assertEqual(sorted(emitted), listed)


if __name__ == "__main__":
    unittest.main()
