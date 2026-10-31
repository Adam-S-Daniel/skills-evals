"""Issues #72 and #123: the Skill Evals Explorer page (tool/index.html).

The page's own tests are plain Node (tool/test/run.js, no dependencies, no
network). This module runs them inside the existing suite, so they gate the
required `test` check without a separate job, and cross-checks the committed
guidance id list against _agent-guidance's manifest with a real YAML parser
when that checkout sits beside this one.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tool" / "test" / "run.js"
COMMITTED_IDS = ROOT / "tool" / "test" / "guidance-ids.json"


def manifest_path() -> Path:
    override = os.environ.get("AGENT_GUIDANCE_MANIFEST")
    if override:
        return Path(override)
    return ROOT.parent / "_agent-guidance" / "agents-md" / "eval-coverage.yml"


class ExplorerPageTests(unittest.TestCase):
    def test_node_suite_passes(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("`node` is not on PATH, so tool/test/run.js cannot run here")
        proc = subprocess.run([node, str(RUNNER)], cwd=ROOT, capture_output=True,
                              text=True, timeout=120, check=False)
        self.assertEqual(proc.returncode, 0,
                         f"node tool/test/run.js exited {proc.returncode}:\n"
                         f"{proc.stdout}\n{proc.stderr}")
        self.assertRegex(proc.stdout, r"\b[1-9]\d* passed, 0 failed\b",
                         "the runner must report a nonzero pass count")

    def test_committed_ids_match_the_manifest(self):
        path = manifest_path()
        if not path.is_file():
            self.skipTest(f"no _agent-guidance manifest at {path.name}; "
                          "the node suite still checks the committed list")
        import yaml
        rows = yaml.safe_load(path.read_text(encoding="utf-8"))
        manifest = [row["id"] for row in rows]
        committed = json.loads(COMMITTED_IDS.read_text(encoding="utf-8"))
        self.assertEqual(committed, manifest,
                         "tool/test/guidance-ids.json is out of step with "
                         "agents-md/eval-coverage.yml; update the list and add a "
                         "gloss to GLOSSES in tool/index.html for any new id")


if __name__ == "__main__":
    unittest.main()
