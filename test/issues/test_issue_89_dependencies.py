"""Keep the shell_capture_safe scorer parser installed on every execution surface."""
from __future__ import annotations

import copy
from pathlib import Path
import unittest

import bashlex
import yaml

ROOT = Path(__file__).resolve().parents[2]
PIN = "bashlex==0.18"


def _nodes(value):
    if isinstance(value, bashlex.ast.node):
        yield value
        for child in vars(value).values():
            yield from _nodes(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _nodes(child)


def _install_commands(document):
    """Return pip-install argv from dependency steps parsed as shell ASTs."""
    commands = []
    for job in document.get("jobs", {}).values():
        for step in job.get("steps", []):
            if step.get("name") not in ("Install dependencies", "Install harness dependencies"):
                continue
            for node in _nodes(bashlex.parse(step.get("run", ""))):
                if node.kind == "command":
                    argv = [part.word for part in node.parts if part.kind == "word"]
                    if argv[:2] == ["pip", "install"]:
                        commands.append((step["name"], argv))
    return commands


def _assert_parser_installed(testcase, document):
    commands = _install_commands(document)
    testcase.assertTrue(commands, "no dependency install command was parsed")
    testcase.assertEqual([name for name, argv in commands if PIN not in argv], [])


class TestCiWatcherDependencies(unittest.TestCase):
    def test_ci_and_eval_install_the_pinned_shell_parser(self):
        ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
        evaluation = yaml.safe_load((ROOT / ".github/workflows/eval.yml").read_text(encoding="utf-8"))

        ci_commands = _install_commands(ci)
        eval_commands = _install_commands(evaluation)
        self.assertEqual([name for name, _ in ci_commands], ["Install dependencies"])
        self.assertEqual([name for name, _ in eval_commands],
                         ["Install harness dependencies", "Install harness dependencies"])
        _assert_parser_installed(self, ci)
        _assert_parser_installed(self, evaluation)

        # In-memory mutation proves the check catches a missing pin without
        # changing the workflow file under test.
        mutated = copy.deepcopy(evaluation)
        step = mutated["jobs"][next(iter(mutated["jobs"]))]["steps"]
        target = next(item for item in step if item.get("name") == "Install harness dependencies")
        target["run"] = "pip install pyyaml markdown-it-py==4.2.0"
        with self.assertRaises(AssertionError):
            _assert_parser_installed(self, mutated)
