#!/usr/bin/env python3
"""Issue #97 — a `guidance` subject with five delivery modes and a per-arm
delivery guard, plus the per-issue test discovery this file is itself the
first user of.

Hermetic, like the rest of the suite: CLAUDE_BIN always points at
test/fake-claude, no network, no wall-clock, and — asserted below — never a
write into the real ~/.claude/CLAUDE.md.

This module is discovered and run by test/run_tests.py (see
`build_suite`/`DISCOVERY_DIR` there); it is also runnable on its own with
`python3 test/issues/test_issue_97.py`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
HARNESS_DIR = REPO_ROOT / "harness"
FAKE_CLAUDE = TEST_DIR / "fake-claude"
ISSUES_DIR = TEST_DIR / "issues"
DELIVERY_DIR = REPO_ROOT / "evals" / "guidance" / "_delivery"
CANARY_DIR = REPO_ROOT / "evals" / "guidance-bridge-canary"
EVAL_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "eval.yml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

sys.path.insert(0, str(HARNESS_DIR))
import guidance  # noqa: E402
import run_canary  # noqa: E402
import run_eval  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import make_badge  # noqa: E402

# A child `python3 test/run_tests.py` sets this, so the two discovery tests
# below (the only ones that shell out to the whole suite) skip inside it
# instead of forking the suite again, forever.
CHILD_ENV = "SKILLS_EVALS_SUITE_CHILD"

# A guidance checkout the payload tests build from scratch: base.md with a
# fenced `## ` that is NOT a heading, a `###` child that belongs to its
# parent's extent, and a sections/ file that is its own single `##`.
FIXTURE_BASE_MD = """\
# AGENTS.md

Intro paragraph, everything before the first `##`.

## Alpha

Alpha body.

## Bravo

Bravo body, which shows a fenced block:

```markdown
## Not A Heading

This line lives inside a fence and must never end Bravo's extent.
```

### Bravo child

The `###` child belongs to Bravo's extent.

## Charlie

Charlie body.
"""

FIXTURE_SECTION_MD = """\
## Delta

Delta body, an opt-in language section in its own file.
"""

FIXTURE_STUB_MD = """\
# AGENTS.md

## Fleet guidance is delivered once per session — not by this file

The stub.
"""

FIXTURE_MANIFEST = [
    {"id": "alpha", "heading": "Alpha", "file": "agents-md/base.md", "status": "gap"},
    {"id": "bravo", "heading": "Bravo", "file": "agents-md/base.md", "status": "gap"},
    {"id": "charlie", "heading": "Charlie", "file": "agents-md/base.md", "status": "gap"},
    {"id": "section-delta", "heading": "Delta",
     "file": "agents-md/sections/delta.md", "status": "gap"},
]


def make_guidance_checkout(root: Path) -> Path:
    """A minimal `_agent-guidance` checkout: manifest, base.md, stub.md, a
    sections/ file, and the REAL fleet-memory.sh copied from the sibling
    checkout when one exists (tests that need the real hook skip without it).
    """
    (root / "agents-md" / "sections").mkdir(parents=True)
    (root / "agents-md" / "base.md").write_text(FIXTURE_BASE_MD, encoding="utf-8")
    (root / "agents-md" / "stub.md").write_text(FIXTURE_STUB_MD, encoding="utf-8")
    (root / "agents-md" / "sections" / "delta.md").write_text(
        FIXTURE_SECTION_MD, encoding="utf-8")
    (root / "agents-md" / "eval-coverage.yml").write_text(
        yaml.safe_dump(FIXTURE_MANIFEST, sort_keys=False), encoding="utf-8")
    hook_dir = root / ".claude" / "hooks"
    hook_dir.mkdir(parents=True)
    real_hook = REAL_GUIDANCE_DIR / ".claude" / "hooks" / "fleet-memory.sh"
    if real_hook.is_file():
        shutil.copy2(real_hook, hook_dir / "fleet-memory.sh")
        (hook_dir / "fleet-guidance.md").write_text(
            "# shipped payload\n", encoding="utf-8")
    return root


# The sibling checkout the harness itself defaults to. Present in CI (eval.yml
# checks it out side by side) and on a dev box; tests that need the REAL hook
# or the REAL manifest skip with a printed reason when it is not.
REAL_GUIDANCE_DIR = (REPO_ROOT / ".." / "_agent-guidance").resolve()


class TestIssue97(unittest.TestCase):
    """Every new assertion for #97 lives in this one class."""

    maxDiff = None

    # ------------------------------------------------------------------
    # Per-issue test discovery (the structural half of this PR)
    #
    # Every fixture PR used to append its tests to the bottom of
    # test/run_tests.py, so every fixture PR conflicted with every other at
    # the same four append points. run_tests.py now DISCOVERS
    # test/issues/test_issue_*.py in addition to its own classes, and this
    # file is the first module to arrive that way. The two tests below are
    # the pin: a planted module with one failing test must make the runner
    # exit 1, and removing it must put it back to 0. They shell out to the
    # whole suite, so they skip inside a child run (or they would fork the
    # suite forever).
    # ------------------------------------------------------------------

    PLANTED = ISSUES_DIR / "test_issue_zz_discovery_probe.py"
    PLANTED_SOURCE = (
        "import unittest\n\n\n"
        "class DiscoveryProbe(unittest.TestCase):\n"
        "    def test_planted_failure(self):\n"
        "        self.fail('discovery-probe: planted by TestIssue97')\n"
    )

    def _run_suite(self) -> subprocess.CompletedProcess:
        env = dict(os.environ, **{CHILD_ENV: "1"})
        return subprocess.run(
            [sys.executable, str(TEST_DIR / "run_tests.py")],
            cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
            timeout=900)

    @staticmethod
    def _ran_counts(output: str) -> list[int]:
        return [int(n) for n in re.findall(r"^Ran (\d+) tests?", output,
                                           flags=re.MULTILINE)]

    def _skip_in_child(self) -> None:
        if os.environ.get(CHILD_ENV):
            reason = ("child suite run — the discovery pin does not re-fork "
                      "the suite from inside itself")
            print(reason)
            self.skipTest(reason)

    def test_planted_issue_module_is_discovered_and_fails_the_runner(self):
        self._skip_in_child()
        self.assertFalse(self.PLANTED.exists(),
                         f"{self.PLANTED} is left over from an earlier run")
        self.PLANTED.write_text(self.PLANTED_SOURCE, encoding="utf-8")
        self.addCleanup(lambda: self.PLANTED.unlink(missing_ok=True))
        proc = self._run_suite()
        output = proc.stdout + proc.stderr
        self.assertEqual(
            proc.returncode, 1,
            "a planted test/issues/test_issue_*.py with one failing test must "
            f"make `python3 test/run_tests.py` exit 1; got {proc.returncode}\n"
            f"{output[-3000:]}")
        self.assertIn("discovery-probe: planted by TestIssue97", output,
                      "the planted module's failure must be reported by name")
        counts = self._ran_counts(output)
        self.assertEqual(len(counts), 1,
                         "the runner must print ONE total for the whole suite, "
                         f"got {counts}")

    def test_removing_the_planted_module_puts_the_runner_back_to_zero(self):
        self._skip_in_child()
        self.assertFalse(self.PLANTED.exists(),
                         f"{self.PLANTED} is left over from an earlier run")
        proc = self._run_suite()
        output = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0,
                         "with no planted module the suite must exit 0\n"
                         f"{output[-3000:]}")
        counts = self._ran_counts(output)
        self.assertEqual(len(counts), 1,
                         f"one printed total for the whole suite, got {counts}")
        self.assertGreater(
            counts[0], 379,
            "the single total must span run_tests.py's own classes AND the "
            "discovered test/issues/ modules — this file alone adds more than "
            "the 379 that predate it")

    def test_this_module_is_reachable_through_the_discovery_pattern(self):
        # The discovery contract in one assertion: this file lives in the
        # discovered subtree and matches the pattern the runner globs, so a
        # future fixture PR can add test/issues/test_issue_<n>.py instead of
        # appending to run_tests.py.
        self.assertEqual(Path(__file__).resolve().parent, ISSUES_DIR)
        discovered = sorted(p.name for p in ISSUES_DIR.glob("test_issue_*.py"))
        self.assertIn("test_issue_97.py", discovered)

    # ------------------------------------------------------------------
    # Item 2 — payload assembly (pure)
    # ------------------------------------------------------------------

    def _checkout(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="guidance-checkout-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        return make_guidance_checkout(tmp)

    def _row(self, guidance_dir: Path, section_id: str) -> dict:
        return guidance.find_row(guidance.load_manifest(guidance_dir),
                                 section_id, guidance_dir)

    def test_section_extent_stops_at_the_next_h2_and_keeps_its_h3_child(self):
        root = self._checkout()
        payload = guidance.assemble(root, self._row(root, "bravo"), "section")
        self.assertIn("## Bravo", payload)
        self.assertIn("### Bravo child", payload,
                      "a `###` child belongs to its parent's extent")
        self.assertNotIn("## Charlie", payload,
                         "the extent stops at the line before the next `##`")
        self.assertNotIn("## Alpha", payload)

    def test_a_fenced_h2_never_ends_an_extent(self):
        # The reason this is a real markdown parse and not a regex: `## Not A
        # Heading` sits inside a fenced block in Bravo's body, and a line scan
        # would end Bravo there and lose everything after it.
        root = self._checkout()
        payload = guidance.assemble(root, self._row(root, "bravo"), "section")
        self.assertIn("## Not A Heading", payload,
                      "the fenced line is part of Bravo's body, not a heading")
        self.assertIn("### Bravo child", payload,
                      "content AFTER the fence must still be in the extent")
        headings = [s["heading"] for s in guidance.h2_extents(FIXTURE_BASE_MD)]
        self.assertEqual(headings, ["Alpha", "Bravo", "Charlie"],
                         "a `## ` inside a fence is not a heading")

    def test_section_payload_prepends_the_files_intro(self):
        root = self._checkout()
        payload = guidance.assemble(root, self._row(root, "alpha"), "section")
        self.assertTrue(payload.startswith("# AGENTS.md\n"))
        self.assertIn("Intro paragraph, everything before the first `##`.", payload)
        self.assertIn("## Alpha", payload)
        self.assertNotIn("## Bravo", payload)

    def test_full_minus_section_is_full_minus_exactly_the_extent(self):
        root = self._checkout()
        for section_id in ("alpha", "bravo", "charlie", "section-delta"):
            with self.subTest(section=section_id):
                row = self._row(root, section_id)
                full = guidance.assemble(root, row, "full")
                minus = guidance.assemble(root, row, "full-minus-section")
                extent = guidance._extent_of(
                    guidance.corpus(root, row), row["heading"], "corpus")
                length = extent["end"] - extent["start"]
                self.assertGreater(length, 0)
                self.assertEqual(len(full) - length, len(minus))
                self.assertNotIn(f"## {row['heading']}", minus)

    def test_full_is_the_corpus_verbatim_and_stub_is_the_stub(self):
        root = self._checkout()
        row = self._row(root, "alpha")
        self.assertEqual(guidance.assemble(root, row, "full"), FIXTURE_BASE_MD)
        self.assertEqual(guidance.assemble(root, row, "stub"), FIXTURE_STUB_MD)

    def test_a_sections_file_is_its_own_single_h2(self):
        root = self._checkout()
        row = self._row(root, "section-delta")
        self.assertEqual(guidance.assemble(root, row, "section"), FIXTURE_SECTION_MD)
        # `full` for an opt-in language section is base.md WITH it; the
        # ablation arm is therefore base.md alone, which is the only reading
        # under which the ablation pair differs at all.
        self.assertEqual(guidance.assemble(root, row, "full"),
                         FIXTURE_BASE_MD + FIXTURE_SECTION_MD)
        self.assertEqual(guidance.assemble(root, row, "full-minus-section"),
                         FIXTURE_BASE_MD)

    def test_mode_none_delivers_nothing_at_all_not_even_the_token(self):
        root = self._checkout()
        row = self._row(root, "alpha")
        self.assertEqual(guidance.assemble(root, row, "none", token="TOK-1"), "")

    def test_every_non_none_payload_carries_the_magic_word_paragraph(self):
        root = self._checkout()
        row = self._row(root, "bravo")
        for mode in ("stub", "section", "full", "full-minus-section"):
            with self.subTest(mode=mode):
                payload = guidance.assemble(root, row, mode, token="ZZZZZZZZ-1234")
                self.assertTrue(payload.endswith(
                    "\nThe magic word is ZZZZZZZZ-1234.\n"),
                    f"{mode} payload must end in the magic-word paragraph")
                self.assertEqual(
                    payload.count("ZZZZZZZZ-1234"), 1,
                    "exactly one occurrence, so a probe reply naming it is "
                    "unambiguous")

    def test_tokens_are_fresh_per_run(self):
        # A token an earlier run could reproduce would let a stale, real
        # ~/.claude/CLAUDE.md satisfy this run's guard — the exact
        # contamination the guard exists to catch.
        tokens = {guidance.new_token() for _ in range(50)}
        self.assertEqual(len(tokens), 50)
        for token in tokens:
            self.assertRegex(token, r"^[A-Z]{8}-\d{4}$")

    def test_unknown_section_id_names_the_manifest(self):
        root = self._checkout()
        with self.assertRaises(guidance.GuidanceError) as ctx:
            self._row(root, "no-such-section")
        message = str(ctx.exception)
        self.assertIn("no-such-section", message)
        self.assertIn("eval-coverage.yml", message,
                      "the message must name the manifest, which is the file "
                      "to go and look at")
        self.assertIn("alpha", message, "and list the ids it does know")

    def test_unknown_mode_is_rejected_by_name(self):
        root = self._checkout()
        with self.assertRaises(guidance.GuidanceError) as ctx:
            guidance.assemble(root, self._row(root, "alpha"), "sekshun")
        self.assertIn("sekshun", str(ctx.exception))

    def test_missing_checkout_names_the_flag(self):
        missing = Path(tempfile.mkdtemp()) / "not-a-checkout"
        self.addCleanup(shutil.rmtree, missing.parent, ignore_errors=True)
        with self.assertRaises(guidance.GuidanceError) as ctx:
            guidance.require_guidance_dir(missing)
        self.assertIn("--guidance", str(ctx.exception))
        self.assertIn("AGENT_GUIDANCE_DIR", str(ctx.exception))

    def test_guidance_dir_resolution_order(self):
        base = REPO_ROOT
        self.assertEqual(
            guidance.resolve_guidance_dir("/tmp/flag", "/tmp/env", base),
            Path("/tmp/flag"))
        self.assertEqual(
            guidance.resolve_guidance_dir(None, "/tmp/env", base),
            Path("/tmp/env"))
        self.assertEqual(
            guidance.resolve_guidance_dir(None, None, base),
            (base / ".." / "_agent-guidance").resolve())
