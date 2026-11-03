#!/usr/bin/env python3
"""skills-evals#660: every `persistent/eval-results` path has one writer.

propagation.yml's `coverage-publish` job and `scripts/scaffold_skill_gaps.py`
(run by skill-coverage.yml) both wrote `coverage/latest.json` and
`badges/coverage.json`, in two shapes. Whichever ran last decided what the
explorer saw, and the explorer's census date went null whenever propagation
won. `coverage/` and `badges/coverage.json` now belong to skill-coverage; the
fixture census moved to `fixture-census/` and `badges/fixture-census.json`.

These tests read the writers from their source: workflows are parsed as YAML
and each results-branch job's `git add` arguments are split with `shlex` (a
lexical tokenizer); Python writers are found with `ast`. A whole-directory
`git add` (eval.yml's `git add badges results`) names no file, so it is left
out of the comparison; only file paths and file patterns are compared.

Hermetic: reads committed files only.
"""

from __future__ import annotations

import ast
import fnmatch
import re
import shlex
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
SCRIPTS = ROOT / "scripts"
RESULTS_BRANCH = "persistent/eval-results"
SHELL_VARIABLE = re.compile(r"\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*")
SEPARATORS = {";", "&&", "||", "|", "&", "then", "fi", "do", "done", "else"}


def _pattern(raw: str) -> str:
    """A path with its shell or f-string substitutions turned into `*`."""
    return SHELL_VARIABLE.sub("*", raw)


def _is_file_path(path: str) -> bool:
    return "." in path.rsplit("/", 1)[-1]


def git_add_paths(script: str) -> list[str]:
    """The path arguments of every `git add` in a shell script."""
    paths = []
    for line in script.replace("\\\n", " ").splitlines():
        if "git" not in line or "add" not in line:
            continue  # lexical prefilter; a multi-line string elsewhere cannot split
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        tokens = list(lexer)
        for i in range(len(tokens) - 1):
            if tokens[i] != "git" or tokens[i + 1] != "add":
                continue
            for token in tokens[i + 2:]:
                if token in SEPARATORS:
                    break
                if not token.startswith("-"):
                    paths.append(_pattern(token))
    return paths


def workflow_writers() -> dict[str, set[str]]:
    """`<workflow>:<job>` -> the file paths that job adds on the results branch."""
    writers: dict[str, set[str]] = {}
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        for job_id, job in (doc.get("jobs") or {}).items():
            runs = [step["run"] for step in job.get("steps", []) if "run" in step]
            if not any(RESULTS_BRANCH in run for run in runs):
                continue
            files = {path for run in runs for path in git_add_paths(run)
                     if _is_file_path(path)}
            if files:
                writers[f"{workflow.name}:{job_id}"] = files
    return writers


def _string_value(node: ast.AST) -> str | None:
    """A literal or f-string with each substitution as `*`."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant) else "*"
                       for part in node.values)
    return None


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def scaffold_writes() -> set[str]:
    """The results-branch paths scaffold_skill_gaps.py PUTs through the contents API."""
    tree = ast.parse((SCRIPTS / "scaffold_skill_gaps.py").read_text(encoding="utf-8"))
    paths = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_name(node) == "_put_coverage":
            value = _string_value(node.args[1])
            assert value is not None, "a _put_coverage path is not a string literal"
            paths.add(value)
    return paths


def scaffold_guard_read() -> str:
    """The results-branch path `_latest_run` reads for its late-rerun guard."""
    tree = ast.parse((SCRIPTS / "scaffold_skill_gaps.py").read_text(encoding="utf-8"))
    function = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == "_latest_run")
    for node in ast.walk(function):
        value = _string_value(node)
        if value and "/contents/" in value:
            return value.split("/contents/", 1)[1].split("?", 1)[0]
    raise AssertionError("_latest_run reads no contents path")


def explorer_census_read() -> str:
    """The results-tree path explorer_data.load_census joins with `/`."""
    tree = ast.parse((SCRIPTS / "explorer_data.py").read_text(encoding="utf-8"))
    function = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == "load_census")

    def parts(node: ast.AST) -> list[str]:
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return parts(node.left) + parts(node.right)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        return []

    joins = [parts(node) for node in ast.walk(function)
             if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)]
    return "/".join(max(joins, key=len))


def _overlaps(a: str, b: str) -> bool:
    return a == b or fnmatch.fnmatchcase(a, b) or fnmatch.fnmatchcase(b, a)


def all_writers() -> dict[str, set[str]]:
    return {**workflow_writers(), "scripts/scaffold_skill_gaps.py": scaffold_writes()}


class SingleWriterTests(unittest.TestCase):
    def test_extraction_sees_both_coverage_writers(self):
        writers = all_writers()
        self.assertEqual(writers["propagation.yml:coverage-publish"], {
            "fixture-census/latest.json", "fixture-census/*.json",
            "fixture-census/latest.md", "badges/fixture-census.json"})
        self.assertEqual(writers["scripts/scaffold_skill_gaps.py"], {
            "coverage/*.json", "coverage/latest.json", "badges/coverage.json"})

    def test_no_two_writers_share_a_results_branch_path(self):
        writers = sorted(all_writers().items())
        clashes = [(left, right, a, b)
                   for i, (left, left_paths) in enumerate(writers)
                   for right, right_paths in writers[i + 1:]
                   for a in sorted(left_paths) for b in sorted(right_paths)
                   if _overlaps(a, b)]
        self.assertEqual(clashes, [])

    def test_the_census_readers_read_skill_coverage_paths(self):
        # The explorer's `publication.as_of` and the late-rerun guard's
        # `publication.run_id` exist only in scaffold_skill_gaps.py's shape.
        owned = scaffold_writes()
        self.assertEqual(explorer_census_read(), "coverage/latest.json")
        self.assertIn(explorer_census_read(), owned)
        self.assertEqual(scaffold_guard_read(), "coverage/latest.json")
        self.assertFalse(any(_overlaps(path, "coverage/*")
                             for path in workflow_writers()["propagation.yml:coverage-publish"]))

    def test_the_overlap_check_can_fail(self):
        # Negative control: the pre-#660 publisher line must read as a clash.
        old = ('git add -f coverage/latest.json "coverage/$stamp.json" '
               'coverage/latest.md badges/coverage.json')
        paths = set(git_add_paths(old))
        self.assertEqual(paths, {"coverage/latest.json", "coverage/*.json",
                                 "coverage/latest.md", "badges/coverage.json"})
        self.assertTrue(any(_overlaps(a, b) for a in paths for b in scaffold_writes()))

    def test_git_add_parsing_stops_at_shell_separators(self):
        self.assertEqual(git_add_paths("if [ -d roster ]; then git add -f roster; fi\n"
                                       "git add -- explorer/latest.json && git commit"),
                         ["roster", "explorer/latest.json"])


if __name__ == "__main__":
    unittest.main()
