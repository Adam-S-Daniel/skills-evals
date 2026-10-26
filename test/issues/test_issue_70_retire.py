#!/usr/bin/env python3
"""Issue #70, part 2: scripts/retire_skill.py acts on a `retire` verdict.

Adam's decisions: build automatic removal (2026-10-25); removal pull requests
auto-merge with no human review (2026-10-25, ADR 0014); results are not
signed, the gate guards against honest mistakes (2026-10-26);
`retirement_mode` stays `proposal`, where a retire verdict files or updates
an issue instead of opening a pull request.

Hermetic: a hand-written gates document, registry checkouts in a temporary
directory (local git only), and a fake `gh` and `push`; no network, no clock.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test"))

from lockfile_pins import lock_problem  # noqa: E402
import gates as gates_module  # noqa: E402
import compute_gates  # noqa: E402
import retire_skill  # noqa: E402

SCHEDULE = {"GITHUB_EVENT_NAME": "schedule"}
AUTO_ENV = {**SCHEDULE, "GITHUB_ACTIONS": "true", "GITHUB_REF": "refs/heads/main"}
BOT = "github-actions[bot]"
MODELS = ["claude-opus-5-5", "claude-sonnet-5-5"]
SKILL = "example-skill"
PLUGIN = "adam-coding-anywhere"
IMPACT = """# skill-impact.md — the registry's skill-change audit trail

Header text.

---


## 2026-10-23 — adam-coding-anywhere/other-skill — edit

- Motivation: an earlier entry.
"""


def cell(fixture, model, cls="no-benefit"):
    return {"fixture": fixture, "model": model, "class": cls,
            "with": {"runs": 10}, "without": {"runs": 11},
            "objective": {"delta": 0.0, "benefit_lower": -0.1, "retire_upper": 0.04},
            "judge": {"delta": 0.1, "benefit_lower": -0.2, "retire_upper": 0.3},
            "looks": [{"n": 5, "class": cls}, {"n": 10, "class": cls}]}


def gates_doc(mode="proposal", verdicts=None):
    verdicts = verdicts if verdicts is not None else {
        SKILL: {"verdict": "retire", "reason": "every cell shows no benefit",
                "cells": [cell("basic", m) for m in MODELS] +
                         [cell("edge", m) for m in MODELS]},
        "kept-skill": {"verdict": "keep", "reason": "a cell shows benefit", "cells": []}}
    return {"schema_version": 1, "as_of": "20261025T120000Z", "roster_models": MODELS,
            "retirement_mode": mode, "skills": verdicts}


def issue(number, body, author=BOT, state="open"):
    """One record as open_issue's `--jq` filter shapes it."""
    return {"number": number, "body": body, "author": author, "state": state}


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t",
                           "-c", "user.email=t@example.com", *args],
                          check=True, capture_output=True, text=True).stdout


def make_registry(root: Path, skills=((PLUGIN, SKILL),), version="1.2.7") -> Path:
    root.mkdir(parents=True)
    plugins = {p for p, _ in skills} | {PLUGIN}
    for plugin in plugins:
        (root / "plugins" / plugin / ".claude-plugin").mkdir(parents=True)
        (root / "plugins" / plugin / "plugin.json").write_text(
            json.dumps({"name": plugin, "version": version}, indent=2) + "\n")
        (root / "plugins" / plugin / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": plugin, "version": version}, indent=2) + "\n")
    for plugin, skill in skills:
        directory = root / "plugins" / plugin / "skills" / skill
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(f"---\nname: {skill}\n---\nBody.\n")
    (root / "docs").mkdir()
    (root / "docs" / "skill-impact.md").write_text(IMPACT)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "seed")
    return root


class FakeGitHub:
    """Records every call; answers the two reads from canned data."""

    def __init__(self, prs=(), issues=()):
        self.prs, self.issues, self.calls, self.pushes = list(prs), list(issues), [], []

    def gh(self, args, stdin=None):
        self.calls.append((list(args), stdin))
        if args[:2] == ["api", "--paginate"] and "/pulls?" in args[2]:
            return "".join(json.dumps(p) + "\n" for p in self.prs)
        if args[:2] == ["api", "--paginate"] and "/issues?" in args[2]:
            return "".join(json.dumps(i) + "\n" for i in self.issues)
        if args[:2] == ["pr", "create"]:
            return "https://github.com/Adam-S-Daniel/adam-agentskills/pull/999\n"
        return ""

    def push(self, checkout, branch):
        self.pushes.append((Path(checkout), branch))

    def writes(self):
        return [args for args, _ in self.calls if args[0] != "api"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(self.tmp)], check=False))
        self.registry = make_registry(self.tmp / "agentskills")

    def write_gates(self, doc):
        path = self.tmp / "gates.json"
        path.write_text(json.dumps(doc))
        return path

    def run_main(self, doc, *extra, env=SCHEDULE, fake=None, registries=None):
        fake = fake or FakeGitHub()
        argv = ["--gates", str(self.write_gates(doc))]
        for flag in registries or [f"adam-agentskills={self.registry}"]:
            argv += ["--registry", flag]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            code = retire_skill.main([*argv, *extra], env=env, gh=fake.gh,
                                     push=fake.push, out=out)
        return code, out.getvalue(), err.getvalue(), fake

    def assertUntouched(self):
        self.assertEqual(git(self.registry, "status", "--porcelain"), "")
        self.assertEqual(git(self.registry, "branch", "--show-current").strip(), "main")
        self.assertTrue((self.registry / "plugins" / PLUGIN / "skills" / SKILL).is_dir())


class EventTests(Base):
    def test_refuses_outside_the_schedule(self):
        for env in ({}, {"GITHUB_EVENT_NAME": "workflow_dispatch"},
                    {"GITHUB_EVENT_NAME": "pull_request"},
                    {"GITHUB_EVENT_NAME": "pull_request_target"},
                    {"GITHUB_EVENT_NAME": "Schedule"}):
            for mode in ("proposal", "auto"):
                with self.subTest(env=env, mode=mode):
                    code, out, err, fake = self.run_main(gates_doc(mode), env=env)
                    self.assertEqual(code, 2)
                    self.assertIn("only the scheduled workflow", err)
                    self.assertEqual(fake.calls, [])
                    self.assertEqual(fake.pushes, [])
                    self.assertUntouched()

    def test_check_event_accepts_only_schedule(self):
        retire_skill.check_event({"GITHUB_EVENT_NAME": "schedule"})
        with self.assertRaises(retire_skill.RetireError):
            retire_skill.check_event({"GITHUB_EVENT_NAME": "workflow_dispatch"})


class ProposalTests(Base):
    def test_files_an_issue_when_none_is_open(self):
        code, out, err, fake = self.run_main(gates_doc("proposal"))
        self.assertEqual(code, 0, err)
        writes = fake.writes()
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][:4], ["issue", "create", "-R", "Adam-S-Daniel/skills-evals"])
        body = fake.calls[-1][1]
        self.assertIn(retire_skill.ISSUE_MARKER.format(skill=SKILL), body)
        self.assertIn(f"plugins/{PLUGIN}/skills/{SKILL}", body)
        self.assertIn("| basic | claude-opus-5-5 | 10 | 11 | 0.040 | 0.300 | 5, 10 |", body)
        self.assertEqual(fake.pushes, [])
        self.assertFalse(any(args[0] == "pr" for args in writes))
        self.assertUntouched()

    def test_updates_the_open_issue_found_by_its_marker(self):
        marker = retire_skill.ISSUE_MARKER.format(skill=SKILL)
        fake = FakeGitHub(issues=[issue(5, "unrelated"),
                                  issue(42, f"{marker}\nold text"),
                                  issue(7, retire_skill.ISSUE_MARKER.format(
                                      skill="other-skill"))])
        code, out, err, fake = self.run_main(gates_doc("proposal"), fake=fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.writes(), [["issue", "edit", "42", "-R",
                                          "Adam-S-Daniel/skills-evals", "--body-file", "-"]])
        self.assertIn("updated issue #42", out)

    def test_an_open_removal_pr_does_not_stop_a_proposal(self):
        fake = FakeGitHub(prs=[{"number": 1, "head": "retire-skill/x", "url": "u"}])
        code, _, err, fake = self.run_main(gates_doc("proposal"), fake=fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.writes()[0][:2], ["issue", "create"])

    def test_a_skill_not_found_once_is_still_proposed_and_says_so(self):
        registry = make_registry(self.tmp / "two", skills=((PLUGIN, SKILL),
                                                           ("adam-coding-local", SKILL)))
        code, _, err, fake = self.run_main(
            gates_doc("proposal"), registries=[f"adam-agentskills={registry}"])
        self.assertEqual(code, 0, err)
        self.assertIn("not located", fake.calls[-1][1])
        self.assertIn("found 2 time(s)", fake.calls[-1][1])

    def test_a_missing_or_invalid_mode_is_proposal(self):
        for mode in (None, "AUTO", "", 1):
            doc = gates_doc("proposal")
            doc["retirement_mode"] = mode
            self.assertEqual(retire_skill.mode_of(doc), "proposal")
        self.assertEqual(gates_module.parse_gate_policy(
            "skills:\n" + "".join(f"  {k}: {json.dumps(v)}\n"
                                  for k, v in self.policy_block().items()))["skills"]
            ["retirement_mode"], "proposal")

    @staticmethod
    def policy_block():
        doc = yaml.safe_load((ROOT / "evals" / "gate-policy.yml").read_text())
        block = dict(doc["skills"])
        block["retirement_mode"] = "sometimes"
        return block

    def test_the_committed_policy_stays_proposal(self):
        doc = yaml.safe_load((ROOT / "evals" / "gate-policy.yml").read_text())
        self.assertEqual(doc["skills"]["retirement_mode"], "proposal")


class AutoTests(Base):
    def run_main(self, doc, *extra, env=AUTO_ENV, **kwargs):
        if "--allow-mode" not in extra:
            extra = (*extra, "--allow-mode", "auto")
        return super().run_main(doc, *extra, env=env, **kwargs)

    def test_prepares_pushes_opens_and_arms_the_removal(self):
        code, out, err, fake = self.run_main(gates_doc("auto"))
        self.assertEqual(code, 0, err)
        branch = f"retire-skill/{SKILL}"
        self.assertEqual(git(self.registry, "branch", "--show-current").strip(), branch)
        self.assertEqual(git(self.registry, "status", "--porcelain"), "")
        self.assertFalse((self.registry / "plugins" / PLUGIN / "skills" / SKILL).exists())
        changed = sorted(git(self.registry, "diff", "--name-only", "main", "HEAD").split())
        self.assertEqual(changed, sorted([
            "docs/skill-impact.md", f"plugins/{PLUGIN}/.claude-plugin/plugin.json",
            f"plugins/{PLUGIN}/plugin.json", f"plugins/{PLUGIN}/skills/{SKILL}/SKILL.md"]))
        for rel in (f"plugins/{PLUGIN}/plugin.json",
                    f"plugins/{PLUGIN}/.claude-plugin/plugin.json"):
            self.assertEqual(json.loads((self.registry / rel).read_text())["version"], "1.2.8")
        self.assertEqual(fake.pushes, [(self.registry.resolve(), branch)])
        writes = fake.writes()
        self.assertEqual(writes[0][:6], ["pr", "create", "-R",
                                         "Adam-S-Daniel/adam-agentskills", "--base", "main"])
        self.assertIn(branch, writes[0])
        self.assertEqual(writes[1], ["pr", "merge",
                                     "https://github.com/Adam-S-Daniel/adam-agentskills/pull/999",
                                     "-R", "Adam-S-Daniel/adam-agentskills", "--auto", "--merge"])
        body = next(stdin for args, stdin in fake.calls if args[:2] == ["pr", "create"])
        self.assertIn("no human review", body)
        self.assertIn("0014-removal-pull-requests-merge-without-review.md", body)
        self.assertIn("1.2.7 -> 1.2.8", body)
        self.assertFalse(any(args[0] == "issue" for args in writes))

    def test_one_open_removal_pr_at_a_time(self):
        fake = FakeGitHub(prs=[{"number": 3, "head": "retire-skill/other-skill",
                                "url": "https://github.com/Adam-S-Daniel/adam-agentskills/pull/3"}])
        code, _, err, fake = self.run_main(gates_doc("auto"), fake=fake)
        self.assertEqual(code, 2)
        self.assertIn("already open", err)
        self.assertIn("/pull/3", err)
        self.assertEqual(fake.writes(), [])
        self.assertEqual(fake.pushes, [])
        self.assertUntouched()

    def test_other_open_prs_do_not_hold_the_slot(self):
        fake = FakeGitHub(prs=[{"number": 4, "head": "claude/retire-skill-docs", "url": "u"},
                               {"number": 5, "head": "main-retire-skill/x", "url": "u"}])
        code, _, err, fake = self.run_main(gates_doc("auto"), fake=fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1)

    def test_basename_must_be_found_exactly_once(self):
        cases = {
            "two plugins": [f"adam-agentskills={make_registry(self.tmp / 'a', skills=((PLUGIN, SKILL), ('adam-coding-local', SKILL)))}"],
            "absent": [f"adam-agentskills={make_registry(self.tmp / 'b', skills=((PLUGIN, 'another-skill'),))}"],
            "another registry": [f"adam-agentskills={self.registry}",
                                 f"cms-platform={self.make_flat(self.tmp / 'c')}"],
        }
        for name, flags in cases.items():
            with self.subTest(name):
                code, _, err, fake = self.run_main(gates_doc("auto"), registries=flags)
                self.assertEqual(code, 2)
                self.assertIn("not exactly once", err)
                self.assertEqual(fake.writes(), [])
                self.assertEqual(fake.pushes, [])
        self.assertUntouched()

    def test_a_directory_without_skill_md_still_counts_as_a_copy(self):
        registry = make_registry(self.tmp / "d")
        (registry / "plugins" / "adam-coding-local" / "skills" / SKILL).mkdir(parents=True)
        code, _, err, _ = self.run_main(gates_doc("auto"),
                                        registries=[f"adam-agentskills={registry}"])
        self.assertEqual(code, 2)
        self.assertIn("not exactly once", err)

    def test_no_adam_agentskills_checkout_is_refused(self):
        code, _, err, fake = self.run_main(
            gates_doc("auto"), registries=[f"cms-platform={self.make_flat(self.tmp / 'e')}"])
        self.assertEqual(code, 2)
        self.assertEqual(fake.pushes, [])

    def test_manifests_that_disagree_are_refused(self):
        path = self.registry / "plugins" / PLUGIN / "plugin.json"
        path.write_text(json.dumps({"name": PLUGIN, "version": "1.2.6"}))
        git(self.registry, "commit", "-qam", "drift")
        code, _, err, fake = self.run_main(gates_doc("auto"))
        self.assertEqual(code, 2)
        self.assertIn("disagree", err)
        self.assertEqual(fake.pushes, [])

    def test_a_dirty_checkout_is_refused(self):
        (self.registry / "stray.txt").write_text("x\n")
        code, _, err, fake = self.run_main(gates_doc("auto"))
        self.assertEqual(code, 2)
        self.assertIn("uncommitted changes", err)
        self.assertEqual(fake.pushes, [])
        self.assertEqual(git(self.registry, "branch", "--show-current").strip(), "main")

    def test_auto_is_refused_where_the_caller_allows_only_proposal(self):
        code, _, err, fake = self.run_main(gates_doc("auto"), "--allow-mode", "proposal")
        self.assertEqual(code, 2)
        self.assertIn("has not wired", err)
        self.assertEqual(fake.calls, [])
        self.assertUntouched()

    @staticmethod
    def make_flat(root: Path) -> Path:
        (root / "skills" / SKILL).mkdir(parents=True)
        (root / "skills" / SKILL / "SKILL.md").write_text("x\n")
        return root


class VerdictTests(Base):
    def test_no_retire_verdict_does_nothing(self):
        doc = gates_doc("auto", verdicts={SKILL: {"verdict": "retire-pending", "cells": []}})
        code, out, err, fake = self.run_main(doc)
        self.assertEqual(code, 0, err)
        self.assertIn("no skill has a retire verdict", out)
        self.assertEqual(fake.calls, [])
        self.assertUntouched()

    def test_a_retire_the_cells_do_not_support_is_refused(self):
        bad = {
            "a cell is not no-benefit": [cell("basic", MODELS[0]),
                                         cell("basic", MODELS[1], "no-benefit-pending")],
            "a roster model is missing": [cell("basic", MODELS[0])],
            "an extra model": [cell("basic", m) for m in [*MODELS, "claude-old"]],
            "no cell": [],
        }
        for name, cells in bad.items():
            with self.subTest(name):
                doc = gates_doc("proposal", verdicts={SKILL: {"verdict": "retire",
                                                              "cells": cells}})
                code, _, err, fake = self.run_main(doc)
                self.assertEqual(code, 2)
                self.assertEqual(fake.writes(), [])

    def test_two_retire_verdicts_are_refused(self):
        cells = [cell("basic", m) for m in MODELS]
        doc = gates_doc("auto", verdicts={SKILL: {"verdict": "retire", "cells": cells},
                                          "second-skill": {"verdict": "retire",
                                                           "cells": cells}})
        code, _, err, fake = self.run_main(doc)
        self.assertEqual(code, 2)
        self.assertIn("2 skills", err)
        self.assertEqual(fake.calls, [])

    def test_a_malformed_gates_file_is_refused(self):
        for doc in ({}, {**gates_doc(), "schema_version": 2},
                    {**gates_doc(), "as_of": "yesterday"}, []):
            with self.subTest(doc=doc):
                code, _, err, fake = self.run_main(doc)
                self.assertEqual(code, 2)
                self.assertEqual(fake.calls, [])

    def test_a_name_that_is_not_a_basename_is_refused(self):
        cells = [cell("basic", m) for m in MODELS]
        doc = gates_doc("proposal", verdicts={"../escape": {"verdict": "retire",
                                                            "cells": cells}})
        code, _, err, fake = self.run_main(doc)
        self.assertEqual(code, 2)
        self.assertEqual(fake.calls, [])


BOTH = ("--allow-mode", "auto", "--allow-mode", "proposal")


class DryRunTests(Base):
    def test_dry_run_writes_nothing_and_prints_the_plan(self):
        for mode, action in (("proposal", "create-issue"), ("auto", "removal")):
            for env in (SCHEDULE, {}):
                with self.subTest(mode=mode, env=env):
                    code, out, err, fake = self.run_main(gates_doc(mode), "--dry-run",
                                                         *BOTH, env=env)
                    self.assertEqual(code, 0, err)
                    plan = json.loads(out)
                    self.assertTrue(plan["dry_run"])
                    self.assertEqual(plan["action"], action)
                    self.assertEqual(fake.writes(), [])
                    self.assertEqual(fake.pushes, [])
                    self.assertTrue(plan["would_run"])
                    self.assertUntouched()

    def test_dry_run_auto_names_every_write(self):
        code, out, err, _ = self.run_main(gates_doc("auto"), "--dry-run", *BOTH)
        plan = json.loads(out)
        self.assertEqual(plan["path"], f"plugins/{PLUGIN}/skills/{SKILL}")
        self.assertEqual(plan["branch"], f"retire-skill/{SKILL}")
        heads = [command[:3] for command in plan["would_run"]]
        self.assertIn(["git", "push", "origin"], heads)
        self.assertIn(["gh", "pr", "create"], heads)
        self.assertIn(["gh", "pr", "merge"], heads)
        self.assertEqual(plan["would_run"][-1][-2:], ["--auto", "--merge"])
        self.assertIn("## 2026-10-25 —", plan["impact_entry"])

    def test_dry_run_still_honors_the_one_open_pr_limit(self):
        fake = FakeGitHub(prs=[{"number": 3, "head": "retire-skill/x", "url": "u"}])
        code, _, err, _ = self.run_main(gates_doc("auto"), "--dry-run", *BOTH, fake=fake)
        self.assertEqual(code, 2)
        self.assertIn("already open", err)


class UsageLineTests(Base):
    """The issue names the skill's recent invocations from --usage, and the
    decision does not depend on it."""

    def usage(self, generated_at="2026-10-25T06:00:00Z", rows=None):
        rows = rows if rows is not None else [
            {"week": "2026-10-19", "kind": "skill", "name": SKILL, "repo": None,
             "surface": "local", "invocations": 3, "sessions": 2, "blocked": None,
             "overridden": None, "outcome": None},
            {"week": "2026-10-19", "kind": "hook", "name": SKILL, "repo": None,
             "surface": "local", "invocations": 50, "sessions": None, "blocked": 0,
             "overridden": None, "outcome": None}]
        path = self.tmp / "weekly-local.json"
        path.write_text(json.dumps({"generated_at": generated_at, "schema": 1,
                                    "sources": [], "rows": rows}))
        return str(path)

    def body(self, *extra):
        code, _, err, fake = self.run_main(gates_doc("proposal"), *extra)
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.writes()[0][:2], ["issue", "create"])
        return fake.calls[-1][1]

    def test_a_fresh_census_gives_the_count(self):
        self.assertIn("Recent use: 3 local invocation(s) in the four weeks to "
                      "20261025T120000Z", self.body("--usage", self.usage()))

    def test_a_skill_absent_from_a_fresh_census_is_zero(self):
        self.assertIn("Recent use: 0 local invocation(s)",
                      self.body("--usage", self.usage(rows=[])))

    def test_no_stale_or_unreadable_census_is_unknown(self):
        for extra in ((), ("--usage", self.usage(generated_at="2026-10-01T00:00:00Z")),
                      ("--usage", str(self.tmp / "absent.json"))):
            with self.subTest(extra=extra):
                self.assertIn("Recent use: unknown (no fresh usage census).",
                              self.body(*extra))

    def test_the_workflow_passes_the_published_census(self):
        doc = yaml.safe_load((ROOT / ".github" / "workflows" / "skill-coverage.yml")
                             .read_text(encoding="utf-8"))
        act = next(s for s in doc["jobs"]["retirement"]["steps"]
                   if "scripts/retire_skill.py" in s.get("run", ""))
        self.assertIn('--usage "$GITHUB_WORKSPACE/eval-results/usage/weekly-local.json"',
                      act["run"])


class IssueHistoryTests(Base):
    """Finding 2 (and 11): one issue per skill, ever, and only the bot's."""

    def marker(self, skill=SKILL):
        return retire_skill.ISSUE_MARKER.format(skill=skill)

    def test_the_search_covers_closed_issues(self):
        code, _, err, fake = self.run_main(gates_doc("proposal"))
        self.assertEqual(code, 0, err)
        search = next(args for args, _ in fake.calls
                      if args[0] == "api" and "/issues?" in args[2])
        self.assertIn("state=all", search[2])
        self.assertNotIn("state=open", search[2])

    def test_a_closed_issue_is_already_decided(self):
        fake = FakeGitHub(issues=[issue(42, f"{self.marker()}\nold", state="closed")])
        code, out, err, fake = self.run_main(gates_doc("proposal"), fake=fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.writes(), [])
        self.assertIn("#42", out)
        self.assertIn("already decided", out)

    def test_an_open_issue_is_updated_even_beside_a_closed_one(self):
        fake = FakeGitHub(issues=[issue(3, self.marker(), state="closed"),
                                  issue(42, self.marker())])
        code, _, err, fake = self.run_main(gates_doc("proposal"), fake=fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.writes()[0][:3], ["issue", "edit", "42"])

    def test_the_lowest_open_issue_is_the_one_updated(self):
        fake = FakeGitHub(issues=[issue(90, self.marker()), issue(12, self.marker()),
                                  issue(55, self.marker())])
        code, _, err, fake = self.run_main(gates_doc("proposal"), fake=fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.writes()[0][:3], ["issue", "edit", "12"])

    def test_a_human_issue_quoting_the_marker_neither_suppresses_nor_is_edited(self):
        for state in ("open", "closed"):
            with self.subTest(state=state):
                fake = FakeGitHub(issues=[issue(9, self.marker(), author="someone",
                                                state=state)])
                code, _, err, fake = self.run_main(gates_doc("proposal"), fake=fake)
                self.assertEqual(code, 0, err)
                self.assertEqual([w[:2] for w in fake.writes()], [["issue", "create"]])

    def test_the_jq_filter_returns_author_and_state(self):
        code, _, err, fake = self.run_main(gates_doc("proposal"))
        search = next(args for args, _ in fake.calls
                      if args[0] == "api" and "/issues?" in args[2])
        jq = search[search.index("--jq") + 1]
        self.assertIn(".user.login", jq)
        self.assertIn(".state", jq)

    def test_a_malformed_issue_record_is_refused(self):
        for record in ({"number": "42", "body": self.marker(), "author": BOT,
                        "state": "open"},
                       {"number": True, "body": self.marker(), "author": BOT,
                        "state": "open"},
                       {"number": 42, "body": self.marker(), "author": BOT,
                        "state": "merged"}):
            with self.subTest(record=record):
                code, _, err, fake = self.run_main(gates_doc("proposal"),
                                                   fake=FakeGitHub(issues=[record]))
                self.assertEqual(code, 2)
                self.assertEqual(fake.writes(), [])


class CrossProductTests(Base):
    """Finding 3: every (fixture, roster model) cell exactly once, each no-benefit."""

    def refused(self, cells, mode="proposal"):
        doc = gates_doc(mode, verdicts={SKILL: {"verdict": "retire",
                                                "reason": "r", "cells": cells}})
        code, _, err, fake = self.run_main(doc)
        self.assertEqual(code, 2, err)
        self.assertEqual(fake.writes(), [])
        return err

    def test_a_missing_cell_is_refused(self):
        err = self.refused([cell("basic", m) for m in MODELS] + [cell("edge", MODELS[0])])
        self.assertIn("cross product", err)

    def test_a_duplicate_cell_is_refused(self):
        self.refused([cell("basic", m) for m in MODELS] + [cell("basic", MODELS[0])])

    def test_a_duplicate_standing_in_for_a_missing_cell_is_refused(self):
        self.refused([cell("basic", m) for m in MODELS]
                     + [cell("edge", MODELS[0]), cell("edge", MODELS[0])])

    def test_one_failing_cell_among_many_is_refused(self):
        self.refused([cell("basic", m) for m in MODELS]
                     + [cell("edge", MODELS[0]), cell("edge", MODELS[1], "benefit")])

    def test_a_full_flat_cross_product_retires(self):
        doc = gates_doc("proposal", verdicts={SKILL: {
            "verdict": "retire", "reason": "r", "cells": [cell(None, m) for m in MODELS]}})
        code, _, err, fake = self.run_main(doc)
        self.assertEqual(code, 0, err)
        self.assertIn("| (flat) | claude-opus-5-5 |", fake.calls[-1][1])


class InputTypeTests(Base):
    """Finding 4: a wrong type fails closed with exit 2, never a crash or a pass."""

    def test_wrong_types_in_the_gates_file_are_refused(self):
        good = [cell("basic", m) for m in MODELS]
        docs = {
            "skills a list": {**gates_doc(), "skills": []},
            "roster a string": {**gates_doc(), "roster_models": "claude-opus-5-5"},
            "roster of numbers": {**gates_doc(), "roster_models": [1, 2]},
            "roster mixed": {**gates_doc(), "roster_models": [1, MODELS[0]]},
            "roster duplicated": {**gates_doc(verdicts={SKILL: {
                "verdict": "retire", "reason": "r", "cells": [cell("basic", MODELS[0])]}}),
                "roster_models": [MODELS[0], MODELS[0]]},
            "roster empty string": {**gates_doc(), "roster_models": [""]},
            "as_of a number": {**gates_doc(), "as_of": 20261025},
            "cells a dict": gates_doc(verdicts={SKILL: {"verdict": "retire", "reason": "r",
                                                        "cells": {"a": 1}}}),
            "a model a list": gates_doc(verdicts={SKILL: {"verdict": "retire", "reason": "r",
                                                          "cells": [{**good[0], "model": ["x"]},
                                                                    good[1]]}}),
            "a fixture a number": gates_doc(verdicts={SKILL: {
                "verdict": "retire", "reason": "r",
                "cells": [{**c, "fixture": 3} for c in good]}}),
            "a fixture with markup": gates_doc(verdicts={SKILL: {
                "verdict": "retire", "reason": "r",
                "cells": [{**c, "fixture": "a|b\n@someone"} for c in good]}}),
            "a fixture empty": gates_doc(verdicts={SKILL: {
                "verdict": "retire", "reason": "r",
                "cells": [{**c, "fixture": ""} for c in good]}}),
            "a reason not text": gates_doc(verdicts={SKILL: {"verdict": "retire",
                                                             "reason": {"x": 1},
                                                             "cells": good}}),
            "looks a number": gates_doc(verdicts={SKILL: {
                "verdict": "retire", "reason": "r",
                "cells": [{**c, "looks": 5} for c in good]}}),
        }
        for mode in ("proposal", "auto"):
            for name, doc in docs.items():
                with self.subTest(name, mode=mode):
                    doc = {**doc, "retirement_mode": mode}
                    code, _, err, fake = self.run_main(
                        doc, "--allow-mode", "auto", "--allow-mode", "proposal",
                        env=AUTO_ENV)
                    self.assertEqual(code, 2, err)
                    self.assertIn("retire_skill:", err)
                    self.assertEqual(fake.writes(), [])
                    self.assertEqual(fake.pushes, [])
                    self.assertUntouched()

    def test_a_manifest_that_is_not_an_object_is_refused(self):
        for rel in ("plugin.json", ".claude-plugin/plugin.json"):
            with self.subTest(rel):
                registry = make_registry(self.tmp / rel.replace("/", "_"))
                (registry / "plugins" / PLUGIN / rel).write_text("[1]\n")
                git(registry, "commit", "-qam", "list")
                code, _, err, fake = self.run_main(
                    gates_doc("auto"), "--allow-mode", "auto", env=AUTO_ENV,
                    registries=[f"adam-agentskills={registry}"])
                self.assertEqual(code, 2, err)
                self.assertEqual(fake.pushes, [])


class AllowModeTests(Base):
    """Finding 5: proposal unless auto is asked for, and auto only on Actions' main."""

    def test_allow_mode_defaults_to_proposal(self):
        code, _, err, fake = self.run_main(gates_doc("auto"), env=AUTO_ENV)
        self.assertEqual(code, 2)
        self.assertIn("has not wired", err)
        self.assertIn("allowed: proposal)", err)
        self.assertEqual(fake.calls, [])
        self.assertUntouched()

    def test_proposal_runs_with_no_allow_mode(self):
        code, _, err, fake = self.run_main(gates_doc("proposal"))
        self.assertEqual(code, 0, err)

    def test_auto_refuses_off_actions_or_off_the_default_branch(self):
        for env in (SCHEDULE,
                    {**AUTO_ENV, "GITHUB_ACTIONS": "True"},
                    {**AUTO_ENV, "GITHUB_ACTIONS": "1"},
                    {k: v for k, v in AUTO_ENV.items() if k != "GITHUB_REF"},
                    {**AUTO_ENV, "GITHUB_REF": "refs/heads/feature"},
                    {**AUTO_ENV, "GITHUB_REF": "refs/pull/1/merge"},
                    {**AUTO_ENV, "GITHUB_REF": "refs/tags/main"}):
            with self.subTest(env=env):
                code, _, err, fake = self.run_main(gates_doc("auto"), "--allow-mode", "auto",
                                                   env=env)
                self.assertEqual(code, 2)
                self.assertIn("auto mode", err)
                self.assertEqual(fake.writes(), [])
                self.assertEqual(fake.pushes, [])
                self.assertUntouched()

    def test_execute_itself_refuses_a_removal_off_actions(self):
        registries = compute_gates.flag_registries([f"adam-agentskills={self.registry}"])
        fake = FakeGitHub()
        action = retire_skill.plan(gates_doc("auto"), registries, fake.gh, allowed=("auto",))
        for env in (SCHEDULE, {**AUTO_ENV, "GITHUB_REF": "refs/heads/feature"}):
            with self.subTest(env=env):
                with self.assertRaises(retire_skill.RetireError):
                    retire_skill.execute(action, registries, fake.gh, fake.push, env)
                self.assertEqual(fake.writes(), [])
                self.assertEqual(fake.pushes, [])
                self.assertUntouched()

    def test_proposal_does_not_need_the_actions_environment(self):
        code, _, err, _ = self.run_main(gates_doc("proposal"), env=SCHEDULE)
        self.assertEqual(code, 0, err)


class SymlinkTests(AutoTests):
    """Finding 6: never act through a symlink or outside the registry checkout."""

    def relink(self, rel, target):
        """Move `rel` to `target` (both under the registry) and link it back."""
        src, dst = self.registry / rel, self.registry / target
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        src.symlink_to(Path("../" * (len(Path(rel).parts) - 1) + target))
        git(self.registry, "add", "-A")
        git(self.registry, "commit", "-qm", "link")

    def assertRefused(self, *, proposal_located=False):
        code, _, err, fake = self.run_main(gates_doc("auto"))
        self.assertEqual(code, 2, err)
        self.assertIn("symlink", err)
        self.assertEqual(fake.writes(), [])
        self.assertEqual(fake.pushes, [])
        self.assertEqual(git(self.registry, "status", "--porcelain"), "")
        self.assertEqual(git(self.registry, "branch", "--show-current").strip(), "main")
        code, _, err, fake = self.run_main(gates_doc("proposal"), "--allow-mode", "proposal")
        self.assertEqual(code, 0, err)
        self.assertIn("not located", fake.calls[-1][1])

    def test_a_plugin_directory_symlink_is_refused(self):
        self.relink(f"plugins/{PLUGIN}", f"vendor/{PLUGIN}")
        self.assertRefused()

    def test_a_skills_directory_symlink_is_refused(self):
        self.relink(f"plugins/{PLUGIN}/skills", "shared/skills")
        self.assertRefused()

    def test_a_skill_directory_symlink_is_refused(self):
        self.relink(f"plugins/{PLUGIN}/skills/{SKILL}", f"shared/{SKILL}")
        self.assertRefused()

    def test_a_manifest_symlink_out_of_the_checkout_is_never_written(self):
        outside = self.tmp / "outside.json"
        outside.write_text(json.dumps({"name": PLUGIN, "version": "1.2.7"}, indent=2) + "\n")
        manifest = self.registry / "plugins" / PLUGIN / "plugin.json"
        manifest.unlink()
        manifest.symlink_to(outside)
        git(self.registry, "add", "-A")
        git(self.registry, "commit", "-qm", "link")
        code, _, err, fake = self.run_main(gates_doc("auto"))
        self.assertEqual(code, 2, err)
        self.assertIn("symlink", err)
        self.assertEqual(json.loads(outside.read_text())["version"], "1.2.7")
        self.assertEqual(fake.pushes, [])
        self.assertEqual(git(self.registry, "branch", "--show-current").strip(), "main")

    def test_an_impact_file_symlink_is_never_written(self):
        outside = self.tmp / "impact.md"
        outside.write_text(IMPACT)
        impact = self.registry / "docs" / "skill-impact.md"
        impact.unlink()
        impact.symlink_to(outside)
        git(self.registry, "add", "-A")
        git(self.registry, "commit", "-qm", "link")
        code, _, err, fake = self.run_main(gates_doc("auto"))
        self.assertEqual(code, 2, err)
        self.assertEqual(outside.read_text(), IMPACT)
        self.assertEqual(fake.pushes, [])
        self.assertEqual(git(self.registry, "branch", "--show-current").strip(), "main")


class MutationTests(Base):
    """Finding 7: branches that no earlier test pinned down."""

    def test_a_pr_with_no_head_name_does_not_hold_the_slot(self):
        fake = FakeGitHub(prs=[{"number": 4, "head": None, "url": "u"},
                               {"number": 5, "url": "u"}])
        code, _, err, fake = self.run_main(gates_doc("auto"), "--allow-mode", "auto",
                                           env=AUTO_ENV, fake=fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1)

    def test_the_removal_pr_search_reads_open_pulls_of_the_registry(self):
        code, _, err, fake = self.run_main(gates_doc("auto"), "--allow-mode", "auto",
                                           env=AUTO_ENV)
        search = next(args for args, _ in fake.calls if args[0] == "api")
        self.assertEqual(search[2], "repos/Adam-S-Daniel/adam-agentskills/pulls"
                                    "?state=open&per_page=100")

    def test_the_run_url_needs_this_repository_and_a_numeric_id(self):
        for env, expected in (
                ({"GITHUB_RUN_ID": "77", "GITHUB_REPOSITORY": "Adam-S-Daniel/skills-evals"},
                 "actions/runs/77"),
                ({"GITHUB_RUN_ID": "77", "GITHUB_REPOSITORY": "someone/fork"}, None),
                ({"GITHUB_RUN_ID": "77x", "GITHUB_REPOSITORY": "Adam-S-Daniel/skills-evals"},
                 None),
                ({"GITHUB_REPOSITORY": "Adam-S-Daniel/skills-evals"}, None)):
            with self.subTest(env=env):
                code, _, err, fake = self.run_main(gates_doc("proposal"),
                                                   env={**SCHEDULE, **env})
                self.assertEqual(code, 0, err)
                body = fake.calls[-1][1]
                if expected:
                    self.assertIn(f"Workflow run: https://github.com/Adam-S-Daniel/"
                                  f"skills-evals/{expected}", body)
                else:
                    self.assertNotIn("Workflow run:", body)

    def test_a_version_not_written_once_is_refused_before_the_commit(self):
        registry = make_registry(self.tmp / "compact")
        for rel in ("plugin.json", ".claude-plugin/plugin.json"):
            (registry / "plugins" / PLUGIN / rel).write_text(
                json.dumps({"name": PLUGIN, "version": "1.2.7"}, separators=(",", ":")))
        git(registry, "commit", "-qam", "compact")
        code, _, err, fake = self.run_main(gates_doc("auto"), "--allow-mode", "auto",
                                           env=AUTO_ENV,
                                           registries=[f"adam-agentskills={registry}"])
        self.assertEqual(code, 2)
        self.assertIn("not written once", err)
        self.assertEqual(fake.pushes, [])

    def test_an_unreadable_manifest_is_refused(self):
        registry = make_registry(self.tmp / "nomanifest")
        git(registry, "rm", "-q", f"plugins/{PLUGIN}/.claude-plugin/plugin.json")
        git(registry, "commit", "-qm", "drop")
        code, _, err, fake = self.run_main(gates_doc("auto"), "--allow-mode", "auto",
                                           env=AUTO_ENV,
                                           registries=[f"adam-agentskills={registry}"])
        self.assertEqual(code, 2)
        self.assertIn(f"cannot read plugins/{PLUGIN}/.claude-plugin/plugin.json", err)

    def test_a_manifest_changed_under_the_plan_is_refused(self):
        gates = gates_doc("auto")
        registries = compute_gates.flag_registries([f"adam-agentskills={self.registry}"])
        action = retire_skill.plan(gates, registries, FakeGitHub().gh, allowed=("auto",))
        path = self.registry / "plugins" / PLUGIN / "plugin.json"
        path.write_text(json.dumps({"name": PLUGIN, "version": "9.9.9"}, indent=2) + "\n")
        git(self.registry, "commit", "-qam", "race")
        with self.assertRaises(retire_skill.RetireError) as caught:
            retire_skill.prepare_branch(self.registry, action)
        self.assertIn("changed under the plan", str(caught.exception))

    def test_a_figure_that_is_not_a_number_reads_n_a(self):
        self.assertEqual(retire_skill._figure({"retire_upper": "0.1"}, "retire_upper"), "n/a")
        self.assertEqual(retire_skill._figure(None, "retire_upper"), "n/a")
        self.assertEqual(retire_skill._figure({"retire_upper": 0.04449}, "retire_upper"),
                         "0.044")

    def test_a_push_failure_reports_only_its_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "r"
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            git(repo, "commit", "-q", "--allow-empty", "-m", "x")
            git(repo, "remote", "add", "origin", str(Path(tmp) / "missing"))
            with self.assertRaises(retire_skill.RetireError) as caught:
                retire_skill.default_push(repo, "b")
            self.assertRegex(str(caught.exception), r"^git push exited \d+$")


class SkillImpactTests(unittest.TestCase):
    def test_entry_text(self):
        entry = retire_skill.impact_entry(
            gates_doc("auto"), SKILL, PLUGIN,
            "https://github.com/Adam-S-Daniel/skills-evals/actions/runs/123")
        self.assertEqual(entry, (
            f"## 2026-10-25 — {PLUGIN}/{SKILL} — remove\n\n"
            "- Motivation: skills-evals#70's retirement verdict is `retire`: every cell "
            "(2 fixture(s) x 2 roster model(s)) shows no benefit at two fixed looks.\n"
            f"- Change: `plugins/{PLUGIN}/skills/{SKILL}/` removed and the `{PLUGIN}` "
            "patch version raised, by skills-evals' scheduled retirement (workflow run "
            "https://github.com/Adam-S-Daniel/skills-evals/actions/runs/123).\n"
            "- Eval: pooled runs as of 20261025T120000Z, policy evals/gate-policy.yml; "
            "fixtures basic, edge; per-cell bounds in the pull request.\n"
            "- Outcome: auto-merges once required checks pass, with no human review "
            "(skills-evals ADR 0014, Adam's 2026-10-25 decision).\n"))

    def test_entry_goes_newest_first_after_the_rule(self):
        text = retire_skill.insert_entry(IMPACT, "## NEW — remove\n\n- x\n")
        head, rest = text.split("\n---\n", 1)
        self.assertEqual(rest, "\n## NEW — remove\n\n- x\n\n## 2026-10-23 — "
                               "adam-coding-anywhere/other-skill — edit\n\n"
                               "- Motivation: an earlier entry.\n")
        self.assertTrue(head.endswith("Header text.\n"))

    def test_a_file_without_the_rule_is_refused(self):
        with self.assertRaises(retire_skill.RetireError):
            retire_skill.insert_entry("# no rule\n", "entry")

    def test_the_auto_commit_carries_the_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = make_registry(Path(tmp) / "r")
            fake = FakeGitHub()
            path = Path(tmp) / "gates.json"
            path.write_text(json.dumps(gates_doc("auto")))
            code = retire_skill.main(
                ["--gates", str(path), "--registry", f"adam-agentskills={registry}",
                 "--allow-mode", "auto"],
                env={**AUTO_ENV, "GITHUB_RUN_ID": "77",
                     "GITHUB_REPOSITORY": "Adam-S-Daniel/skills-evals"},
                gh=fake.gh, push=fake.push, out=io.StringIO())
            self.assertEqual(code, 0)
            text = (registry / "docs" / "skill-impact.md").read_text()
            self.assertIn(f"\n---\n\n## 2026-10-25 — {PLUGIN}/{SKILL} — remove\n", text)
            self.assertIn("actions/runs/77", text)
            self.assertIn("## 2026-10-23", text)

    def test_bump(self):
        self.assertEqual(retire_skill.bump("1.2.9"), "1.2.10")
        for bad in ("1.2", "v1.2.3", None, "1.2.3-rc1"):
            with self.assertRaises(retire_skill.RetireError):
                retire_skill.bump(bad)


class GitHubCallTests(unittest.TestCase):
    def test_a_gh_failure_reports_only_its_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_gh = Path(tmp) / "gh"
            fake_gh.write_text("#!/bin/sh\necho 'secret body' ; echo 'secret err' >&2\nexit 4\n")
            fake_gh.chmod(0o755)
            import os
            from unittest import mock
            with mock.patch.dict(os.environ, {"PATH": f"{tmp}:{os.environ['PATH']}"}):
                with self.assertRaises(retire_skill.RetireError) as caught:
                    retire_skill.default_gh(["api", "x"])
            self.assertEqual(str(caught.exception), "gh api exited 4")


class WorkflowTests(unittest.TestCase):
    """The scheduled wiring, read with a YAML parser, never a line scan."""

    def setUp(self):
        self.doc = yaml.safe_load((ROOT / ".github/workflows/skill-coverage.yml").read_text())
        self.job = self.doc["jobs"]["retirement"]

    def test_runs_only_on_the_schedule_from_main(self):
        condition = self.job["if"]
        self.assertIn("github.event_name == 'schedule'", condition)
        self.assertIn("github.ref == 'refs/heads/main'", condition)
        self.assertNotIn("workflow_dispatch", condition)

    def test_minimal_permissions(self):
        self.assertEqual(self.doc["permissions"], {})
        self.assertEqual(self.job["permissions"], {"contents": "read", "issues": "write"})

    def test_pins_checkouts_and_no_interpolation_in_run(self):
        for step in self.job["steps"]:
            if "uses" in step:
                self.assertIsNone(lock_problem(step["uses"], "skill-coverage.yml"))
                if step["uses"].startswith("actions/checkout@"):
                    self.assertIs(step["with"]["persist-credentials"], False)
                    self.assertNotIn("token", step["with"])
            if "run" in step:
                self.assertNotIn("${{", step["run"])

    def test_acts_in_proposal_mode_only_with_the_repo_token(self):
        act = next(s for s in self.job["steps"]
                   if "scripts/retire_skill.py" in s.get("run", ""))
        self.assertEqual(act["env"], {"GH_TOKEN": "${{ github.token }}"})
        self.assertIn("--allow-mode proposal", act["run"])
        self.assertNotIn("--allow-mode auto", act["run"])
        self.assertNotIn("--dry-run", act["run"])
        compute = next(s for s in self.job["steps"]
                       if "scripts/compute_gates.py" in s.get("run", ""))
        self.assertLess(self.job["steps"].index(compute), self.job["steps"].index(act))
        self.assertNotIn("env", compute)
        results = next(s for s in self.job["steps"]
                       if s.get("with", {}).get("ref") == "persistent/eval-results")
        self.assertEqual(results["with"]["path"], "eval-results")


class AdrTests(unittest.TestCase):
    def test_the_adr_is_indexed_and_names_the_matching_adrs(self):
        name = "0014-removal-pull-requests-merge-without-review.md"
        text = (ROOT / "docs" / "decisions" / name).read_text()
        self.assertIn("2026-10-25", text)
        self.assertIn("repo-settings", text)
        self.assertIn("adam-agentskills", text)
        self.assertEqual(len(list((ROOT / "docs" / "decisions").glob("0014-*.md"))), 1)
        self.assertIn(f"]({name})", (ROOT / "docs" / "decisions" / "README.md").read_text())
        self.assertTrue(retire_skill.ADR.endswith(name))


if __name__ == "__main__":
    unittest.main()
