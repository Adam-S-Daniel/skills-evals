"""The Explorer's loop pull-request patterns against what the gates emit.

explorer/src/views/loop.js names the loop's pull requests by head branch
(`LOOP_BRANCH`, the rule for data carrying `head_ref`) and by title
(`LOOP_TITLE`, for older data). A gate that renames its branch prefix or its
title would silently drop its pull requests from the public Loop page, so this
imports loop.js in node and reads the two exported patterns as built (they
are assembled from the LOOP_SOURCES table, so there is no literal to parse),
and every gate's title and branch prefix out of the gates themselves: `ast`
for the Python scripts, `yaml` for the workflows. The scan counts what it
found, so a parser that finds nothing fails instead of passing.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
WORKFLOWS = ROOT / ".github" / "workflows"
EXTRACT = """
const m = await import(process.argv[1]);
const out = {};
for (const [name, value] of Object.entries(m)) if (/^LOOP_/.test(name) && value instanceof RegExp) out[name] = { pattern: value.source };
console.log(JSON.stringify(out));
"""


def loop_patterns() -> dict:
    node = shutil.which("node")
    if node is None:
        raise unittest.SkipTest("node is not installed")
    done = subprocess.run([node, "--input-type=module", "-e", EXTRACT, str(ROOT / "explorer" / "src" / "views" / "loop.js")],
                          cwd=ROOT / "explorer", capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
    found = json.loads(done.stdout)
    assert set(found) == {"LOOP_TITLE", "LOOP_BRANCH"}, found
    return {k: re.compile(v["pattern"]) for k, v in found.items()}


def render(node) -> str | None:
    """A string constant or f-string as text, each placeholder as `X`."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "X" for v in node.values)
    return None


def module_constants(path: Path) -> dict:
    out = {}
    for n in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            value = n.value
            if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
                parts = [out.get(p.id) if isinstance(p, ast.Name) else render(p) for p in (value.left, value.right)]
                text = "".join(parts) if all(isinstance(p, str) for p in parts) else None
            else:
                text = render(value)
            if text is not None:
                out[n.targets[0].id] = text
    return out


def python_titles() -> list[str]:
    """Pull-request titles in the gates' Python: a `title` dict entry that
    starts "Remove " (retire_skill's removal actions) and the `--title`
    argument of guidance_improve_gate's `gh pr create`."""
    titles = []
    for tree in (ast.parse((SCRIPTS / f).read_text(encoding="utf-8"))
                 for f in ("retire_skill.py", "guidance_improve_gate.py")):
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value == "title" and (text := render(v)) \
                            and text.startswith("Remove "):
                        titles.append(text)
            if isinstance(node, ast.List):
                for a, b in zip(node.elts, node.elts[1:]):
                    if isinstance(a, ast.Constant) and a.value == "--title" and (text := render(b)):
                        titles.append(text)
    return titles


def workflow_titles() -> list[str]:
    """The `--title "..."` of each loop gate's pull request, from the parsed
    workflow's run scripts (`gh pr create` and the flag's quoted text are
    lexical tokens; an issue's `--title` is not a pull request's)."""
    titles = []
    for name in ("routine-improve-gate.yml", "routine-draft-skill-gate.yml"):
        wf = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
        for job in wf["jobs"].values():
            for step in job.get("steps", []):
                for m in re.finditer(r'gh pr create(?:[^"\n]|\\\n|"[^"]*")*?--title "([^"]+)"', step.get("run") or ""):
                    titles.append(re.sub(r"\$\{[A-Z_]+\}", "X", m.group(1)))
    return titles


class LoopPatternTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = loop_patterns()

    def test_every_gate_pull_request_title_matches_loop_title(self):
        titles = python_titles() + workflow_titles()
        # Fixture pull requests are a different lane (draft-skill-fixtures/).
        titles = [t for t in titles if not t.startswith("Fixtures for the drafted")]
        self.assertGreaterEqual(len(titles), 6, titles)
        for title in titles:
            with self.subTest(title=title):
                self.assertRegex(title, self.patterns["LOOP_TITLE"])

    def test_every_gate_branch_prefix_matches_loop_branch(self):
        consts = {f: module_constants(SCRIPTS / f) for f in
                  ("retire_skill.py", "guidance_improve_gate.py", "improve_gate.py", "draft_new_skill.py")}
        refs = [consts["retire_skill.py"]["BRANCH_PREFIX"], consts["retire_skill.py"]["GUIDANCE_BRANCH_PREFIX"],
                consts["guidance_improve_gate.py"]["TARGET_BRANCH"], consts["improve_gate.py"]["TARGET_BRANCH"],
                consts["draft_new_skill.py"]["TARGET_BRANCH"]]
        self.assertEqual(len(refs), 5)
        for ref in refs:
            with self.subTest(ref=ref):
                self.assertRegex(ref.format(skill="s", section="s", subject="s"), self.patterns["LOOP_BRANCH"])

    def test_the_fixture_lane_and_ordinary_branches_are_not_the_loop(self):
        self.assertIsNone(self.patterns["LOOP_BRANCH"].search("draft-skill-fixtures/x"))
        self.assertIsNone(self.patterns["LOOP_BRANCH"].search("claude/x"))
        self.assertIsNone(self.patterns["LOOP_TITLE"].search("Fixtures for the drafted x skill (draft run 1)"))


if __name__ == "__main__":
    unittest.main()
