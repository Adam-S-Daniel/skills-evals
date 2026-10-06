#!/usr/bin/env python3
"""#71 / ADR 0005 amendment 1 / ADR 0010: the routine's improve mode.

The eval routine runs `scripts/propose_skill_edit.py` and, on an ACCEPTED
candidate only, pushes one branch `claude/eval-improve-<run id>` holding
`eval-improve/<run id>/{summary.json, report.md, skill.patch}` (the record,
the pull-request body and the registry patch the loop writes). It never opens
a pull request. `scripts/improve_gate.py` validates that branch from the
default branch's checkout, through git plumbing only, and
`.github/workflows/routine-improve-gate.yml` opens a DRAFT pull request in
Adam-S-Daniel/adam-agentskills, but only when the owner-chosen credential
exists. What is pinned here:

  * the branch contract: exactly the three files, additions only, under the
    branch's own run id; an accepted record for adam-agentskills whose
    SKILL.md path matches its skill; a single-file patch whose hunks parse;
    a report with the loop's own title and no closing keyword or @mention;
    every rejection names a path and a reason, never file content;
  * `apply` changes only that SKILL.md, refuses a patch that does not apply
    and any change to the frontmatter's name;
  * the improve root is disjoint from the results ingest's root, so an
    improve push never starts a results ingest, and back;
  * both workflows, parsed with PyYAML: workflow_run for the gate, no
    permissions on the signal, `contents: read` on every gate job, the
    cross-repository credential only in the draft-PR job and that job
    skipped unless the credential exists, `--draft`, no merge, no force, no
    `${{ }}` in a `run:`, bare-SHA pins, no concurrency group;
  * #71's gate: no workflow that fires the routine or touches an improve
    branch has a schedule.

Fixtures are built in-test in temporary git repositories (example.com
only). Discovered and run by test/run_tests.py.
"""

from __future__ import annotations

import ast
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
from fnmatch import fnmatch
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
GATE = WORKFLOWS / "routine-improve-gate.yml"
SIGNAL = WORKFLOWS / "routine-improve-pushed.yml"
RESULTS_SIGNAL = WORKFLOWS / "routine-eval-results-pushed.yml"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import improve_gate as gate  # noqa: E402
import ingest_routine_results as ingest  # noqa: E402
import propose_skill_edit as pse  # noqa: E402

RUN_ID = "20261006T201500Z-0a1b2c"
BRANCH = f"claude/eval-improve-{RUN_ID}"
SKILL = "writing-adrs"
SKILL_MD = f"plugins/adam-anything-anywhere/skills/{SKILL}/SKILL.md"
REGISTRY_SHA = "1" * 40
MARKER = "do-not-echo-this-marker"
ROUTINE_ID = "trig_014cqgegCtJUqXYjAKmkr4J5"

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_NAME": "fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.com",
    "GIT_AUTHOR_DATE": "2026-10-06T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-10-06T00:00:00Z",
    "GIT_CONFIG_COUNT": "2",
    "GIT_CONFIG_KEY_0": "gc.auto", "GIT_CONFIG_VALUE_0": "0",
    "GIT_CONFIG_KEY_1": "maintenance.auto", "GIT_CONFIG_VALUE_1": "false",
}

ORIGINAL = ("---\nname: writing-adrs\ndescription: Write an ADR.\n---\n\n"
            "# Writing ADRs\n\nKeep it short.\n\nLink the issue.\n")
CANDIDATE = ("---\nname: writing-adrs\ndescription: Write an ADR.\n---\n\n"
             "# Writing ADRs\n\nKeep it short.\n\nName the decider.\n\n"
             "Link the issue.\n")


def metrics(passed=1) -> dict:
    return {"passed": passed, "total": 2, "judge_mean": None, "error": None,
            "trials": 1, "tokens": 1200.0}


def record(**changes) -> dict:
    """An accepted record in the shape propose_skill_edit.improve() writes."""
    doc = {
        "schema": 1, "skill": SKILL, "timestamp": "20261006T201733Z",
        "local_exhibit": "skills-evals ADR 0002 decision 4: operator login, "
                         "not badge input",
        "registry": {"name": "adam-agentskills",
                     "url": "https://github.com/Adam-S-Daniel/adam-agentskills",
                     "sha": REGISTRY_SHA, "skill_md": SKILL_MD},
        "split": {"rotation": 0, "train": ["bootstrap", "supersede"],
                  "validation": "existing-convention"},
        "trials": 1, "no_judge": True, "min_gain": 0.1,
        "models": {"arm": "model-a", "proposal": "model-b"},
        "baseline": {"bootstrap": metrics(1)},
        "candidate": {"bootstrap": metrics(2)},
        "runs": {"baseline": "/tmp/runs/baseline/writing-adrs/x",
                 "candidate": "/tmp/runs/candidate/writing-adrs/x"},
        "files": {"patch": "/tmp/improvements/writing-adrs/x.patch",
                  "pr_body": "/tmp/improvements/writing-adrs/x.pr-body.md",
                  "record": "/tmp/improvements/writing-adrs/x.json"},
        "trigger_set": {"source": "fixtures", "size": 21,
                        "split": {"train": {"true": 2, "false": 10}},
                        "problems": []},
        "description_half": {"changed": False, "best": "Write an ADR.",
                             "original": "Write an ADR."},
        "body_half": {"model": "model-b", "rationale": "Name the decider.",
                      "unified_diff": "--- a/SKILL.md\n+++ b/SKILL.md\n",
                      "error": None},
        "status": "accepted",
        "reasons": ["train objective +0.50", "validation held"],
        "table": "| Fixture | Split |\n|---|---|",
    }
    doc.update(changes)
    return doc


def patch_text(skill_md=SKILL_MD, old=ORIGINAL, new=CANDIDATE) -> str:
    return pse.registry_patch(old, new, skill_md)


def report_text(skill=SKILL, extra="") -> str:
    return (f"## Proposed `{skill}` SKILL.md edit (validation-gated)\n\n"
            f"Decision: train improved.{extra}\n")


def good_files(run_id=RUN_ID, root="eval-improve", **overrides) -> dict:
    base = f"{root}/{run_id}"
    files = {f"{base}/summary.json": json.dumps(record(), indent=2).encode(),
             f"{base}/report.md": report_text().encode(),
             f"{base}/skill.patch": patch_text().encode()}
    for name, data in overrides.items():
        files[f"{base}/{name.replace('_', '.', 1)}"] = data
    return files


class GitCase(unittest.TestCase):
    """A scratch skills-evals with `main` (holding evals/<skill>/) and an
    improve branch."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        env = mock.patch.dict(os.environ, GIT_ENV)
        env.start()
        self.addCleanup(env.stop)
        self.git("init", "-q", "-b", "main")
        self.write({"README.md": b"see https://example.com\n",
                    ".github/workflows/ci.yml": b"name: CI\n",
                    f"evals/{SKILL}/bootstrap/fixture.yaml": b"name: x\n"})
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "main")
        self.git("checkout", "-q", "-b", BRANCH)

    def git(self, *args) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, files: dict) -> None:
        for name, data in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def commit(self, files: dict | None = None) -> str:
        self.write(good_files() if files is None else files)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", "improve")
        return self.git("rev-parse", "HEAD")

    def validate(self, branch=BRANCH, expect=None, out=None):
        out = out or self.tmp / "staged"
        return gate.validate(str(self.repo), "main", branch, branch, expect,
                             out)

    def assertRejected(self, pattern=None, **kwargs):
        with self.assertRaises(ingest.Rejected) as caught:
            self.validate(**kwargs)
        if pattern:
            self.assertRegex(str(caught.exception), pattern)
        self.assertNotIn(MARKER, str(caught.exception))
        staged = self.tmp / "staged"
        self.assertFalse(staged.exists() and any(staged.iterdir()),
                         "a rejected branch stages nothing")
        return caught.exception


class AcceptTests(GitCase):

    def test_accepts_the_contract_and_stages_exact_bytes(self):
        files = good_files()
        sha = self.commit(files)
        out = self.validate(expect=sha)
        self.assertEqual(out, {
            "run_id": RUN_ID, "sha": sha, "skill": SKILL,
            "registry_sha": REGISTRY_SHA, "skill_md": SKILL_MD,
            "target_branch": f"eval-improve/{SKILL}"})
        staged = self.tmp / "staged"
        self.assertEqual(sorted(p.name for p in staged.iterdir()),
                         ["report.md", "skill.patch", "summary.json"])
        for name, data in files.items():
            self.assertEqual((staged / Path(name).name).read_bytes(), data)

    def test_the_loops_own_pr_body_is_an_accepted_report(self):
        rec = record()
        body = pse.pr_body(rec, pse.table(
            {"bootstrap": metrics(1)}, {"bootstrap": metrics(2)},
            ["bootstrap"], "existing-convention"))
        self.commit(good_files(report_md=body.encode()))
        self.assertEqual(self.validate()["skill"], SKILL)

    def test_every_key_the_loop_writes_is_allowed(self):
        """AST-read the keys improve() puts in its record, so a new record
        field fails here instead of rejecting a real branch."""
        tree = ast.parse((REPO_ROOT / "scripts" /
                          "propose_skill_edit.py").read_text(encoding="utf-8"))
        func = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name == "improve")
        keys = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "record"
                    for t in node.targets) and isinstance(node.value, ast.Dict):
                keys |= {k.value for k in node.value.keys
                         if isinstance(k, ast.Constant)}
            if isinstance(node, ast.Subscript) and isinstance(
                    node.value, ast.Name) and node.value.id == "record" \
                    and isinstance(node.ctx, ast.Store) \
                    and isinstance(node.slice, ast.Constant):
                keys.add(node.slice.value)
            if isinstance(node, ast.Call) and isinstance(
                    node.func, ast.Attribute) and node.func.attr == "update" \
                    and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id == "record":
                keys |= {kw.arg for kw in node.keywords if kw.arg}
        self.assertIn("status", keys)
        self.assertLessEqual(keys, set(gate.RECORD_ALLOWED))
        self.assertLessEqual(set(gate.RECORD_REQUIRED), keys)


class RejectPathTests(GitCase):

    def test_rejects_a_modified_main_file(self):
        self.commit({**good_files(), "README.md": b"changed\n"})
        self.assertRejected(r"README\.md.*only additions")

    def test_rejects_an_added_workflow_or_script(self):
        self.commit({**good_files(),
                     ".github/workflows/evil.yml": b"name: x\n"})
        self.assertRejected(r"evil\.yml.*not under")

    def test_rejects_an_executable_file(self):
        self.commit()
        path = f"eval-improve/{RUN_ID}/skill.patch"
        self.git("update-index", "--chmod=+x", path)
        self.git("commit", "-q", "-m", "x")
        self.assertRejected(r"mode 100755")

    def test_rejects_a_missing_or_extra_file(self):
        files = good_files()
        del files[f"eval-improve/{RUN_ID}/report.md"]
        self.commit(files)
        self.assertRejected(r"report\.md.*missing")

    def test_rejects_an_unknown_file_in_the_root(self):
        self.commit({**good_files(),
                     f"eval-improve/{RUN_ID}/SKILL.md": b"x\n"})
        self.assertRejected(r"SKILL\.md.*not a file")

    def test_rejects_the_results_root_and_another_run_id(self):
        self.commit(good_files(root="eval-results"))
        self.assertRejected(r"not under 'eval-improve/")

    def test_rejects_a_run_id_that_disagrees_with_the_branch(self):
        self.commit(good_files(run_id="20261006T201500Z-ffffff"))
        self.assertRejected(r"not under")

    def test_rejects_bad_branch_names(self):
        self.commit()
        for branch in (f"claude/eval-{RUN_ID}", f"claude/eval-improve-{RUN_ID}x",
                       "claude/eval-improve-", "main",
                       f"claude/scaffold-{RUN_ID}"):
            with self.subTest(branch=branch):
                with self.assertRaises(ingest.Rejected):
                    gate.validate(str(self.repo), "main", BRANCH, branch,
                                  None, self.tmp / "s")

    def test_rejects_a_moved_branch(self):
        self.commit()
        self.assertRejected(r"moved", expect="0" * 40)

    def test_rejects_an_over_cap_file(self):
        self.commit(good_files(
            report_md=report_text(extra="x" * gate.SIZE_CAPS["report.md"])
            .encode()))
        self.assertRejected(r"over the report\.md cap")


class RejectContentTests(GitCase):

    def rejects(self, pattern, **overrides):
        shutil.rmtree(self.tmp / "staged", ignore_errors=True)
        self.commit(good_files(**overrides))
        return self.assertRejected(pattern)

    def rec(self, **changes) -> bytes:
        return json.dumps(record(**changes)).encode()

    def test_rejects_a_record_that_was_not_accepted(self):
        for status in ("rejected", "no-candidate", "refused"):
            with self.subTest(status=status):
                self.git("reset", "-q", "--hard", "main")
                self.rejects(r"status", summary_json=self.rec(status=status))

    def test_rejects_another_registry_or_a_bad_sha(self):
        cases = [
            {"name": "cms-platform"},
            {"url": "https://github.com/example/adam-agentskills"},
            {"sha": "abc"},
            {"skill_md": f"plugins/x/skills/other-skill/SKILL.md"},
            {"skill_md": f"plugins/../skills/{SKILL}/SKILL.md"},
            {"skill_md": f"plugins/x/skills/{SKILL}/README.md"},
        ]
        for change in cases:
            with self.subTest(change=change):
                self.git("reset", "-q", "--hard", "main")
                reg = {**record()["registry"], **change}
                self.rejects(r"registry", summary_json=self.rec(registry=reg))

    def test_rejects_a_skill_with_no_evals_on_the_default_branch(self):
        rec = record(skill="other-skill", registry={
            **record()["registry"],
            "skill_md": "plugins/x/skills/other-skill/SKILL.md"})
        self.rejects(r"no evals/", summary_json=json.dumps(rec).encode(),
                     report_md=report_text("other-skill").encode(),
                     skill_patch=patch_text(
                         "plugins/x/skills/other-skill/SKILL.md").encode())

    def test_rejects_record_schema_violations(self):
        cases = [
            ({"schema": 2}, r"schema"),
            ({"schema": True}, r"schema"),
            ({"surprise": 1}, r"unexpected keys"),
            ({"skill": "../x"}, r"skill"),
            ({"trials": 0}, r"trials"),
            ({"reasons": "accepted"}, r"reasons"),
            ({"table": "x" * (gate.MAX_RECORD_STRING + 1)}, r"too long"),
        ]
        for change, pattern in cases:
            with self.subTest(change=list(change)):
                self.git("reset", "-q", "--hard", "main")
                self.rejects(pattern, summary_json=self.rec(**change))
        self.git("reset", "-q", "--hard", "main")
        doc = record()
        del doc["registry"]
        self.rejects(r"missing keys", summary_json=json.dumps(doc).encode())

    def test_rejects_duplicate_keys_non_utf8_and_controls(self):
        cases = [
            (b'{"schema": 1, "schema": 1}', r"duplicate"),
            (b"\xff\xfe", r"not UTF-8"),
            (("{" + '"x": "\x1b[31m' + MARKER + '"}').encode(), r"control"),
        ]
        for data, pattern in cases:
            with self.subTest(pattern=pattern):
                self.git("reset", "-q", "--hard", "main")
                self.rejects(pattern, summary_json=data)

    def test_rejects_a_patch_aimed_elsewhere(self):
        cases = [
            patch_text(skill_md="plugins/x/skills/writing-adrs/OTHER.md"),
            patch_text(skill_md=".github/workflows/ci.yml"),
            patch_text() + patch_text(skill_md="scripts/evil.py"),
            "",
            "--- a/" + SKILL_MD + "\n+++ b/" + SKILL_MD + "\n",
            re.sub(r"@@ -(\d+),(\d+)",
                   lambda m: f"@@ -{m[1]},{int(m[2]) + 1}", patch_text()),
            patch_text().replace("\n+Name", "\n?Name"),
            patch_text() + "trailing garbage " + MARKER + "\n",
        ]
        for text in cases:
            with self.subTest(text=text[:60]):
                self.git("reset", "-q", "--hard", "main")
                self.rejects(r"skill\.patch", skill_patch=text.encode())

    def test_patch_paths_must_match_the_record(self):
        other = f"plugins/other-plugin/skills/{SKILL}/SKILL.md"
        self.rejects(r"skill\.patch",
                     skill_patch=patch_text(skill_md=other).encode())

    def test_rejects_a_report_that_could_act_on_github(self):
        cases = [
            (report_text(skill="other-skill"), r"title"),
            (report_text(extra="\n\nCloses #12"), r"closing keyword"),
            (report_text(extra=" fixes Adam-S-Daniel/x#3"), r"closing keyword"),
            (report_text(extra=" Resolved: https://github.com/a/b/issues/4"),
             r"closing keyword"),
            (report_text(extra=" cc @someone " + MARKER), r"mention"),
        ]
        for text, pattern in cases:
            with self.subTest(pattern=pattern, text=text[-30:]):
                self.git("reset", "-q", "--hard", "main")
                self.rejects(pattern, report_md=text.encode())

    def test_an_email_or_pin_is_not_a_mention(self):
        self.commit(good_files(report_md=report_text(
            extra=" bot@example.com uses actions/checkout@" + "a" * 40)
            .encode()))
        self.assertEqual(self.validate()["run_id"], RUN_ID)

    def test_cli_rejection_never_quotes_content(self):
        self.commit(good_files(report_md=report_text(
            extra=" @x " + MARKER).encode()))
        err = io.StringIO()
        with contextlib.redirect_stderr(err), \
                contextlib.redirect_stdout(io.StringIO()):
            rc = gate.main(["validate", "--repo", str(self.repo),
                            "--base", "main", "--source", BRANCH,
                            "--branch", BRANCH,
                            "--out", str(self.tmp / "staged")])
        self.assertEqual(rc, 1)
        self.assertIn("rejected:", err.getvalue())
        self.assertNotIn(MARKER, err.getvalue())


class ResolveTests(unittest.TestCase):

    def event(self, doc) -> str:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        self.addCleanup(os.unlink, handle.name)
        with handle:
            json.dump(doc, handle)
        return handle.name

    def push_run(self, branch=BRANCH, head_repo="o/skills-evals") -> dict:
        return {"repository": {"full_name": "o/skills-evals"},
                "workflow_run": {"event": "push", "head_branch": branch,
                                 "head_sha": "a" * 40,
                                 "head_repository": {"full_name": head_repo}}}

    def test_workflow_run_and_dispatch(self):
        self.assertEqual(
            gate.resolve("workflow_run", self.event(self.push_run())),
            {"branch": BRANCH, "sha": "a" * 40, "run_id": RUN_ID})
        self.assertEqual(
            gate.resolve("workflow_dispatch",
                         self.event({"inputs": {"branch": BRANCH}})),
            {"branch": BRANCH, "sha": "", "run_id": RUN_ID})

    def test_rejections(self):
        cases = [
            ("workflow_run", self.push_run(branch=f"claude/eval-{RUN_ID}")),
            ("workflow_run", self.push_run(head_repo="fork/skills-evals")),
            ("workflow_dispatch", {"inputs": {"branch": "main"}}),
            ("push", {"ref": "refs/heads/" + BRANCH}),
        ]
        for name, doc in cases:
            with self.subTest(name=name, doc=doc):
                with self.assertRaises(ingest.Rejected):
                    gate.resolve(name, self.event(doc))


class ApplyTests(unittest.TestCase):
    """`apply` against a scratch registry checkout."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        env = mock.patch.dict(os.environ, GIT_ENV)
        env.start()
        self.addCleanup(env.stop)
        self.tree = self.tmp / "registry"
        self.tree.mkdir()
        self.run_git("init", "-q", "-b", "main")
        (self.tree / SKILL_MD).parent.mkdir(parents=True)
        (self.tree / SKILL_MD).write_text(ORIGINAL, encoding="utf-8")
        (self.tree / "README.md").write_text("x\n", encoding="utf-8")
        self.run_git("add", "-A")
        self.run_git("commit", "-q", "-m", "registry")
        self.staged = self.tmp / "staged"
        self.staged.mkdir()

    def run_git(self, *args) -> str:
        return subprocess.run(["git", "-C", str(self.tree), *args], check=True,
                              capture_output=True, text=True).stdout

    def stage(self, patch: str) -> None:
        (self.staged / "skill.patch").write_text(patch, encoding="utf-8")

    def test_applies_and_changes_only_the_skill(self):
        self.stage(patch_text())
        self.assertEqual(gate.apply(self.staged, self.tree, SKILL_MD),
                         {"changed": SKILL_MD})
        self.assertEqual((self.tree / SKILL_MD).read_text(encoding="utf-8"),
                         CANDIDATE)
        self.assertEqual(self.run_git("status", "--porcelain").split(),
                         ["M", SKILL_MD])

    def test_a_description_change_is_allowed(self):
        new = CANDIDATE.replace("Write an ADR.", "Write or supersede an ADR.")
        self.stage(patch_text(new=new))
        gate.apply(self.staged, self.tree, SKILL_MD)

    def test_refuses_a_name_or_frontmatter_key_change(self):
        for new in (CANDIDATE.replace("name: writing-adrs", "name: other"),
                    CANDIDATE.replace("description:", "allowed-tools: Bash\n"
                                      "description:")):
            with self.subTest(new=new[:50]):
                self.run_git("checkout", "-q", "--", ".")
                self.stage(patch_text(new=new))
                with self.assertRaisesRegex(ingest.Rejected, "frontmatter"):
                    gate.apply(self.staged, self.tree, SKILL_MD)

    def test_refuses_a_patch_that_does_not_apply(self):
        self.stage(patch_text(old=ORIGINAL.replace("Keep", "Make"),
                              new=CANDIDATE.replace("Keep", "Make")))
        with self.assertRaisesRegex(ingest.Rejected, "does not apply"):
            gate.apply(self.staged, self.tree, SKILL_MD)
        self.assertEqual(self.run_git("status", "--porcelain"), "")

    def test_refuses_a_symlinked_skill(self):
        target = self.tmp / "outside.md"
        target.write_text(ORIGINAL, encoding="utf-8")
        (self.tree / SKILL_MD).unlink()
        (self.tree / SKILL_MD).symlink_to(target)
        self.stage(patch_text())
        with self.assertRaisesRegex(ingest.Rejected, "symlink"):
            gate.apply(self.staged, self.tree, SKILL_MD)
        self.assertEqual(target.read_text(encoding="utf-8"), ORIGINAL)


class PrBodyTests(unittest.TestCase):

    def test_body_wraps_the_report_and_closes_nothing(self):
        staged = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, staged)
        (staged / "report.md").write_text(report_text(), encoding="utf-8")
        body = gate.pr_body(staged, RUN_ID, "a" * 40, BRANCH)
        self.assertIn(report_text(), body)
        self.assertIn(BRANCH, body)
        self.assertIn("Part of https://github.com/Adam-S-Daniel/skills-evals/"
                      "issues/71", body)
        self.assertIsNone(gate.CLOSING_RE.search(body))


# ---------------------------------------------------------------------------
# Workflow shape, from the parsed YAML.

PIN = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
PUSH_TARGET = re.compile(r"\bpush\s+(?:[^\n]*?\s)?origin\s+([^\s;]+)")


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def triggers(doc: dict):
    return doc.get("on", doc.get(True))


def run_blocks(doc: dict) -> list[tuple[str, str]]:
    return [(name, step["run"]) for name, job in doc["jobs"].items()
            for step in job.get("steps") or [] if "run" in step]


def strings(node, path=()):
    """Every string scalar in a parsed document, with its key path."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from strings(value, path + (str(key),))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from strings(value, path + (str(i),))
    elif isinstance(node, str):
        yield path, node


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
        cls.jobs = cls.gate["jobs"]

    def test_the_gate_runs_on_workflow_run_of_the_signal(self):
        on = triggers(self.gate)
        self.assertEqual(set(on), {"workflow_run", "workflow_dispatch"})
        self.assertEqual(on["workflow_run"]["workflows"], [self.signal["name"]])
        self.assertEqual(on["workflow_run"]["types"], ["completed"])
        self.assertEqual(on["workflow_run"]["branches"],
                         ["claude/eval-improve-*"])
        self.assertEqual(set(on["workflow_dispatch"]["inputs"]), {"branch"})

    def test_signal_is_a_filtered_push_with_no_reach(self):
        on = triggers(self.signal)
        self.assertEqual(set(on), {"push"})
        self.assertEqual(on["push"]["branches"], ["claude/eval-improve-*"])
        self.assertEqual(on["push"]["paths"], [f"{gate.SOURCE_ROOT}/**"])
        self.assertEqual(self.signal["permissions"], {})
        for job in self.signal["jobs"].values():
            self.assertNotIn("permissions", job)
            for step in job["steps"]:
                self.assertNotIn("uses", step, "the signal checks nothing out")

    def test_improve_and_results_roots_are_disjoint(self):
        """`claude/eval-improve-*` also matches the results signal's
        `claude/eval-*`; only the path filters keep each push to its own
        gate."""
        results = triggers(load(RESULTS_SIGNAL))["push"]
        improve = triggers(self.signal)["push"]
        self.assertTrue(fnmatch(BRANCH, results["branches"][0]))
        improve_file = f"{gate.SOURCE_ROOT}/{RUN_ID}/summary.json"
        results_file = f"{ingest.SOURCE_ROOT}/{RUN_ID}/x/report.md"
        self.assertFalse(any(fnmatch(improve_file, p) for p in results["paths"]))
        self.assertFalse(any(fnmatch(results_file, p) for p in improve["paths"]))
        self.assertNotEqual(gate.SOURCE_ROOT, ingest.SOURCE_ROOT)
        self.assertIsNone(ingest.BRANCH_RE.fullmatch(BRANCH))

    def test_permissions_are_minimal(self):
        self.assertEqual(self.gate["permissions"], {})
        self.assertEqual(set(self.jobs), {"validate", "credential", "draft-pr"})
        self.assertEqual(self.jobs["validate"]["permissions"],
                         {"contents": "read"})
        self.assertEqual(self.jobs["credential"]["permissions"], {})
        self.assertEqual(self.jobs["draft-pr"]["permissions"],
                         {"contents": "read"})
        for doc in (self.gate, self.signal):
            self.assertNotIn("env", doc)
            for job in doc["jobs"].values():
                self.assertNotIn("env", job)

    def test_only_the_default_branch_copy_runs(self):
        self.assertIn("github.ref == format('refs/heads/{0}', "
                      "github.event.repository.default_branch)",
                      self.jobs["validate"]["if"])
        self.assertEqual(set(self.jobs["credential"]["needs"]
                             if isinstance(self.jobs["credential"]["needs"], list)
                             else [self.jobs["credential"]["needs"]]),
                         {"validate"})

    def test_the_credential_reaches_only_the_draft_pr_step(self):
        refs = [(path, text) for path, text in strings(self.gate)
                if "secrets." in text]
        secret = gate.PR_CREDENTIAL_SECRET
        self.assertEqual(sorted(p[:2] for p, _ in refs),
                         [("jobs", "credential"), ("jobs", "draft-pr")])
        for path, text in refs:
            with self.subTest(path=path):
                self.assertEqual(path[2:3], ("steps",))
                self.assertEqual(path[4], "env")
                if path[1] == "credential":
                    self.assertEqual(text.strip(),
                                     "${{ secrets.%s != '' }}" % secret)
                else:
                    self.assertEqual(text.strip(),
                                     "${{ secrets.%s }}" % secret)
        draft_steps = [s for s in self.jobs["draft-pr"]["steps"]
                       if any("secrets." in v for _, v in strings(s))]
        self.assertEqual(len(draft_steps), 1, "one step holds the credential")
        self.assertNotIn("secrets.", json.dumps(self.jobs["validate"]))

    def test_the_draft_pr_job_is_skipped_without_the_credential(self):
        job = self.jobs["draft-pr"]
        self.assertEqual(sorted(job["needs"]), ["credential", "validate"])
        self.assertIn("needs.credential.outputs.present == 'true'", job["if"])
        self.assertEqual(self.jobs["credential"]["outputs"]["present"],
                         "${{ steps.check.outputs.present }}")

    def test_the_draft_pr_job_revalidates_before_it_holds_the_credential(self):
        steps = self.jobs["draft-pr"]["steps"]
        names = [s.get("id") for s in steps]
        self.assertIn("revalidate", names)
        holder = next(i for i, s in enumerate(steps)
                      if any("secrets." in v for _, v in strings(s)))
        self.assertLess(names.index("revalidate"), holder)
        body = steps[names.index("revalidate")]["run"]
        self.assertIn("--expect-sha", body)

    def test_opens_a_draft_in_adam_agentskills_and_never_merges(self):
        bodies = "\n".join(body for _, body in run_blocks(self.gate))
        creates = re.findall(r"gh pr create[^\n]*(?:\\\n[^\n]*)*", bodies)
        self.assertEqual(len(creates), 1)
        self.assertIn("--draft", creates[0])
        self.assertIn("--repo \"$TARGET_REPO\"", creates[0])
        step = next(s for s in self.jobs["draft-pr"]["steps"]
                    if "gh pr create" in s.get("run", ""))
        self.assertEqual(step["env"]["TARGET_REPO"],
                         "Adam-S-Daniel/adam-agentskills")
        for banned in ("gh pr merge", "--force", "push -f", "--admin",
                       "gh pr review", "--auto"):
            self.assertNotIn(banned, bodies)

    def test_every_push_targets_the_improve_branch_without_force(self):
        targets = [t for _, body in run_blocks(self.gate)
                   for t in PUSH_TARGET.findall(body)]
        self.assertEqual(targets, ['"HEAD:refs/heads/${TARGET_BRANCH}"'])

    def test_no_concurrency_group(self):
        for doc in (self.gate, self.signal):
            self.assertNotIn("concurrency", doc)
            for job in doc["jobs"].values():
                self.assertNotIn("concurrency", job)

    def test_every_uses_is_a_bare_sha_already_pinned_elsewhere(self):
        pinned = set()
        for other in WORKFLOWS.glob("*.yml"):
            if other not in (GATE, SIGNAL):
                pinned |= {n.value for n in uses_nodes(
                    yaml.compose(other.read_text(encoding="utf-8")))}
        for path in (GATE, SIGNAL):
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for node in uses_nodes(yaml.compose(text)):
                with self.subTest(path=path.name, uses=node.value):
                    self.assertRegex(node.value, PIN)
                    rest = lines[node.end_mark.line][node.end_mark.column:]
                    self.assertEqual(rest.strip(), "",
                                     "a pin carries no trailing comment")
                    self.assertIn(node.value, pinned)

    def test_no_expressions_in_run_blocks(self):
        for doc in (self.gate, self.signal):
            blocks = run_blocks(doc)
            self.assertTrue(blocks)
            for job, body in blocks:
                with self.subTest(job=job, body=body[:40]):
                    self.assertNotIn("${{", body)

    def test_checkouts_are_the_default_branch_without_credentials(self):
        for name in ("validate", "draft-pr"):
            checkouts = [s for s in self.jobs[name]["steps"]
                         if str(s.get("uses", "")).startswith(
                             "actions/checkout@")]
            self.assertEqual(len(checkouts), 1, name)
            self.assertEqual(checkouts[0]["with"]["ref"],
                             "${{ github.event.repository.default_branch }}")
            self.assertIs(checkouts[0]["with"]["persist-credentials"], False)

    def test_the_guards_can_fail(self):
        self.assertIsNone(PIN.match("actions/checkout@v4"))
        self.assertEqual(PUSH_TARGET.findall("git -C t push origin HEAD:main"),
                         ["HEAD:main"])
        bad = {"jobs": {"j": {"steps": [{"env": {"T": "${{ secrets.X }}"}}]}}}
        self.assertEqual([p for p, t in strings(bad) if "secrets." in t],
                         [("jobs", "j", "steps", "0", "env", "T")])


class ThreePrGateTests(unittest.TestCase):
    """#71 item 5 / ADR 0010 decision 4: no scheduled loop until three
    human-reviewed loop pull requests have merged. Nothing that fires the
    routine or handles an improve branch may run on a schedule."""

    def test_nothing_that_reaches_the_loop_is_scheduled(self):
        reaching = []
        for path in sorted(WORKFLOWS.glob("*.y*ml")):
            text = path.read_text(encoding="utf-8")
            if ROUTINE_ID in text or "eval-improve" in text \
                    or "propose_skill_edit" in text:
                reaching.append(path.name)
                with self.subTest(workflow=path.name):
                    self.assertNotIn("schedule", triggers(load(path)) or {})
        self.assertIn(GATE.name, reaching)
        self.assertIn(SIGNAL.name, reaching)
        self.assertIn("routine-eval-fire.yml", reaching)


if __name__ == "__main__":
    unittest.main()
