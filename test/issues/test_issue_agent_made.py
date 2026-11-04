#!/usr/bin/env python3
"""scripts/agent_made.py: which checks, skills and guidance sections agents
made (_agent-guidance#451, 2026-11-04).

Builds throwaway git repositories with fixed author and committer dates, so
nothing reads the network or the clock. Names and data are invented.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import agent_made  # noqa: E402

AGENT = ("Claude", "noreply@anthropic.com")
PERSON = ("Pat Example", "pat@example.com")
BOT = ("eval-loop[bot]", "loop@example.com")


class Repo:
    def __init__(self, path: Path):
        self.path = path
        path.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")

    def git(self, *args, env=None):
        return subprocess.run(["git", "-C", str(self.path), *args], check=True,
                              capture_output=True, text=True, env=env).stdout

    def commit(self, files: dict, who, date: str, message: str = "change"):
        for rel, text in files.items():
            p = self.path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            self.git("add", "--", rel)
        env = {**os.environ, "GIT_AUTHOR_NAME": who[0], "GIT_AUTHOR_EMAIL": who[1],
               "GIT_COMMITTER_NAME": who[0], "GIT_COMMITTER_EMAIL": who[1],
               "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date,
               "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        self.git("commit", "-q", "--no-verify", "-m", message, env=env)


def doc():
    return {
        "hooks": {"checks": [
            {"name": "old-check", "where": "fleet", "verdict": "never-fires",
             "window_totals": {"invocations": 10, "blocked": 0}},
            {"name": "new-check", "where": "fleet", "verdict": "blocks",
             "window_totals": {"invocations": 5, "blocked": 2}},
            {"name": "local-only", "where": "repo", "verdict": None, "window_totals": {}},
        ]},
        "skills": [
            {"name": "alpha-skill", "registry": "reg", "verdict": "keep", "usage": {"invocations": 4}},
            {"name": "beta-skill", "registry": "reg", "verdict": None, "usage": {"invocations": 0}},
            {"name": "gamma-skill", "registry": "elsewhere", "verdict": None, "usage": {}},
        ],
        "guidance": {"sections": [
            {"id": "first-rule", "heading": "First rule", "verdict": "insufficient",
             "current_text_runs": 3},
            {"id": "turn-lessons", "heading": "Turn lessons into checks, skills and guidance",
             "verdict": None, "current_text_runs": 0},
        ]},
    }


class AgentMadeTests(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        g = self.guidance = Repo(base / "guidance")
        g.commit({"agents-md/base.md": "# x\n\n## First rule\n\ntext\n",
                  "templates/agent-checks/agent-checks": "problem old-check x\n"},
                 PERSON, "2026-09-01T10:00:00-04:00")
        g.commit({"agents-md/base.md": "# x\n\n## First rule\n\nA rule becomes a check first.\n"},
                 AGENT, "2026-10-26T10:00:00Z")
        g.commit({"templates/agent-checks/agent-checks": "problem old-check x\nproblem new-check y\n"},
                 AGENT, "2026-10-30T10:00:00Z",
                 "Add new-check\n\nCaptures: check new-check\nAgent: claude-code\n")
        g.commit({"agents-md/base.md": "# x\n\n## First rule\n\nA rule becomes a check first.\n\n"
                  "## Turn lessons into checks, skills and guidance\n\nDo it.\n"},
                 AGENT, "2026-11-04T18:00:00Z")
        r = self.registry = Repo(base / "registry")
        r.commit({"plugins/p/skills/alpha-skill/SKILL.md": "a\n"}, PERSON, "2026-09-02T00:00:00Z",
                 "Add alpha\n\nCo-Authored-By: Claude Example <noreply@anthropic.com>\n")
        r.commit({"plugins/p/skills/beta-skill/SKILL.md": "b\n"}, BOT, "2026-11-01T00:00:00Z")
        self.manifest = [{"id": "first-rule", "file": "agents-md/base.md"},
                         {"id": "turn-lessons", "file": "agents-md/base.md"}]

    def build(self, guidance=True):
        return agent_made.build(doc(), self.guidance.path if guidance else None,
                                {"reg": self.registry.path}, self.manifest)

    def item(self, out, kind, ident):
        return next(i for i in out["items"] if i["kind"] == kind and i["id"] == ident)

    def test_rule_dates_from_the_routing_sentence(self):
        self.assertEqual(self.build()["rule_since"], "2026-10-26T10:00:00Z")

    def test_origins_and_methods(self):
        out = self.build()
        old = self.item(out, "check", "old-check")
        self.assertEqual((old["origin"], old["method"], old["under_rule"]),
                         ("person", "first-appearance", False))
        self.assertEqual(old["created"], "2026-09-01T14:00:00Z")  # normalized to UTC
        new = self.item(out, "check", "new-check")
        self.assertEqual((new["origin"], new["method"], new["under_rule"]),
                         ("agent", "trailer", True))
        alpha = self.item(out, "skill", "alpha-skill")
        self.assertEqual((alpha["origin"], alpha["method"]), ("agent", "first-add"))
        self.assertEqual(self.item(out, "skill", "beta-skill")["origin"], "loop")
        self.assertEqual(self.item(out, "section", "first-rule")["origin"], "person")
        turn = self.item(out, "section", "turn-lessons")
        self.assertEqual((turn["origin"], turn["under_rule"]), ("agent", True))

    def test_unreachable_subjects_are_unknown_not_guessed(self):
        out = self.build()
        gamma = self.item(out, "skill", "gamma-skill")
        self.assertIsNone(gamma["origin"])
        self.assertIsNone(gamma["under_rule"])
        self.assertNotIn("local-only", [i["id"] for i in out["items"]])
        none = self.build(guidance=False)
        self.assertIsNone(none["rule_since"])
        self.assertIsNone(self.item(none, "check", "new-check")["origin"])

    def test_summary_sums_agent_impact(self):
        s = self.build()["summary"]
        self.assertEqual(s["check"]["by_origin"], {"agent": 1, "loop": 0, "person": 1, "unknown": 0})
        self.assertEqual((s["check"]["agent_runs"], s["check"]["agent_blocked"]), (5, 2))
        self.assertEqual(s["check"]["agent_under_rule"], 1)
        self.assertEqual(s["skill"]["agent_invocations"], 4)
        self.assertEqual(s["skill"]["agent_verdicts"], {"keep": 1})
        self.assertEqual(s["section"]["by_origin"]["agent"], 1)

    def test_no_personal_data_in_output(self):
        text = json.dumps(self.build())
        for leak in ("Pat Example", "pat@example.com", "noreply@anthropic.com", "Captures"):
            self.assertNotIn(leak, text)

    def test_matches_the_schema(self):
        import jsonschema
        schema = json.loads((ROOT / "explorer" / "schema.json").read_text(encoding="utf-8"))
        sub = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/agent_made"}
        jsonschema.validate(self.build(), sub)

    def test_shallow_checkout_is_not_usable(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        clone = Path(tmp.name) / "shallow"
        subprocess.run(["git", "clone", "-q", "--depth", "1",
                        f"file://{self.guidance.path}", str(clone)], check=True)
        self.assertFalse(agent_made.usable(clone))
        self.assertTrue(agent_made.usable(self.guidance.path))


if __name__ == "__main__":
    unittest.main()
