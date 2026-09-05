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

    def test_extents_agree_with_the_real_manifests_generated_bytes(self):
        # The cross-repo join: _agent-guidance generates each row's `bytes`
        # with its own scripts/check-guidance-coverage.js, and this harness
        # slices the same extent to build a payload. If the two ever disagree,
        # a `section` arm delivers something other than the bytes the
        # retirement gate weighed.
        if not (REAL_GUIDANCE_DIR / guidance.MANIFEST_REL).is_file():
            reason = (f"no _agent-guidance checkout at {REAL_GUIDANCE_DIR} — "
                      "skipping the cross-repo extent/bytes agreement check")
            print(reason)
            self.skipTest(reason)
        manifest = guidance.load_manifest(REAL_GUIDANCE_DIR)
        self.assertTrue(manifest)
        for row in manifest:
            if row.get("bytes") is None:
                continue
            with self.subTest(section=row["id"]):
                text = (REAL_GUIDANCE_DIR / row["file"]).read_text(encoding="utf-8")
                extent = guidance._extent_of(text, row["heading"], row["file"])
                self.assertEqual(
                    len(text[extent["start"]:extent["end"]].encode("utf-8")),
                    row["bytes"],
                    f"extent for {row['id']} disagrees with the manifest's "
                    "generated byte count")

    def test_the_guard_probe_is_the_canary_probe(self):
        # The guard reuses run_canary.run_leg; it must also reuse the canary's
        # PROMPT and tool controls. Without the controls the model forages
        # with Read/Glob and "finds" the token in a file on disk, which makes
        # a contaminated arm look delivered — the one failure this guard
        # exists to catch.
        fixture = yaml.safe_load((CANARY_DIR / "fixture.yaml").read_text(encoding="utf-8"))
        self.assertEqual(" ".join(fixture["prompt"].split()),
                         " ".join(guidance.GUARD_PROMPT.split()))
        self.assertEqual(fixture["disallowed_tools"], guidance.GUARD_DISALLOWED_TOOLS)

    # ------------------------------------------------------------------
    # Item 3 — delivery, the production way (the real hook)
    # ------------------------------------------------------------------

    def _skip_without_real_hook(self, root: Path) -> None:
        if not (root / guidance.HOOK_REL).is_file():
            reason = (f"no fleet-memory.sh under {REAL_GUIDANCE_DIR} — "
                      "skipping the real-hook delivery checks")
            print(reason)
            self.skipTest(reason)

    def test_the_real_hook_writes_the_marked_block_into_the_scratch_config_dir(self):
        root = self._checkout()
        self._skip_without_real_hook(root)
        scratch = Path(tempfile.mkdtemp(prefix="guidance-deliver-"))
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        home = scratch / "home"
        config = scratch / "config"
        home.mkdir()
        # A pre-existing user memory under this arm's OWN scratch HOME: the
        # hook is a guest in that file and must not touch it when
        # CLAUDE_CONFIG_DIR points elsewhere.
        (home / ".claude").mkdir()
        own_memory = home / ".claude" / "CLAUDE.md"
        own_memory.write_text("# my own memory\n\nkeep me\n", encoding="utf-8")
        before = own_memory.read_bytes()

        payload = guidance.assemble(root, self._row(root, "alpha"), "section",
                                    token="AAAAAAAA-1111")
        info = guidance.deliver(root, scratch=scratch, dest_dir=config,
                                home=home, payload=payload)

        delivered = (config / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(guidance.BEGIN_MARK, delivered)
        self.assertIn("<!-- END FLEET GUIDANCE -->", delivered)
        self.assertIn("fleet-guidance-version:", delivered,
                      "the hook's own version line must be in the block — "
                      "this is the real hook's output, not an imitation")
        self.assertIn("## Alpha", delivered)
        self.assertIn("The magic word is AAAAAAAA-1111.", delivered)
        self.assertTrue(info["installed"])
        self.assertEqual(info["bytes"], len(payload.encode("utf-8")))
        self.assertIn("fleet-guidance:", info["verdict"])
        self.assertNotIn("DEGRADED", info["verdict"])
        self.assertEqual(own_memory.read_bytes(), before,
                         "the hook must not touch a CLAUDE.md outside the "
                         "config dir it was pointed at")

    def test_mode_none_runs_no_hook_and_leaves_an_empty_config_dir(self):
        root = self._checkout()
        scratch = Path(tempfile.mkdtemp(prefix="guidance-deliver-none-"))
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        home = scratch / "home"
        config = scratch / "config"
        home.mkdir()
        config.mkdir()
        info = guidance.deliver(root, scratch=scratch, dest_dir=config,
                                home=home, payload="")
        self.assertEqual(info["bytes"], 0)
        self.assertIsNone(info["verdict"])
        self.assertFalse((config / "CLAUDE.md").exists())

    def test_delivery_refuses_the_real_config_dir(self):
        root = self._checkout()
        real_home = Path(os.path.expanduser("~")).resolve()
        scratch = Path(tempfile.mkdtemp(prefix="guidance-refuse-"))
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        for dest, home in ((real_home / ".claude", scratch), (scratch, real_home)):
            with self.subTest(dest=str(dest)):
                with self.assertRaises(guidance.GuidanceError) as ctx:
                    guidance.deliver(root, scratch=scratch, dest_dir=dest,
                                     home=home, payload="anything\n")
                self.assertIn("refusing", str(ctx.exception))
        self.assertFalse((scratch / "CLAUDE.md").exists())

    # ------------------------------------------------------------------
    # Item 5 — the environment allowlist
    # ------------------------------------------------------------------

    def test_agent_env_is_an_allowlist_that_still_carries_anthropic_vars(self):
        scratch = Path(tempfile.mkdtemp(prefix="guidance-env-"))
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        ambient = {
            "SKILLS_EVALS_AMBIENT_LEAK": "must not reach the child",
            "CLAUDE_CODE_ENTRYPOINT": "remote",
            "ANTHROPIC_AUTH_TOKEN": "sk-ant-oat01-fake",
            "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
        }
        with mock.patch.dict(os.environ, ambient):
            env = guidance.agent_env(
                workspace=scratch / "ws", home=scratch / "home",
                tmpdir=scratch / "tmp", config_dir=scratch / "config",
                env_spec={"FIXTURE_VAR": "$WORKSPACE/bin", "PLAIN": "value"})
        self.assertNotIn("SKILLS_EVALS_AMBIENT_LEAK", env)
        self.assertNotIn("CLAUDE_CODE_ENTRYPOINT", env,
                         "an arm that inherits the ambient session's CLAUDE_* "
                         "settings is not measuring the guidance")
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "sk-ant-oat01-fake",
                         "eval.yml exports the bearer step-locally; the CLI "
                         "must still see it")
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "https://api.anthropic.com")
        self.assertEqual(env["HOME"], str(scratch / "home"))
        self.assertEqual(env["TMPDIR"], str(scratch / "tmp"))
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], str(scratch / "config"))
        self.assertIn("PATH", env)
        self.assertEqual(env["FIXTURE_VAR"], f"{scratch / 'ws'}/bin")
        self.assertEqual(env["PLAIN"], "value")

    def test_extra_passthrough_is_empty_in_production(self):
        # Same lock harness/propagation/init_probe.py carries: the hermetic
        # suite widens this to let the fake CLI's mode variable through, and a
        # widening left behind would silently un-scrub every arm.
        self.assertEqual(guidance.EXTRA_PASSTHROUGH, ())

    # ------------------------------------------------------------------
    # Items 3-6 — a whole guidance run through the fake CLI
    # ------------------------------------------------------------------

    TOKEN = "TOKENAAA-9999"

    def _guidance_fixture(self, tmp: Path, **overrides) -> Path:
        eval_dir = tmp / "eval"
        eval_dir.mkdir(parents=True)
        fixture = {
            "subject": "guidance",
            "section": "alpha",
            "prompt": "Do the ordinary task the trap is hidden inside.",
            "arms": {"with_guidance": {"mode": "section"},
                     "without_guidance": {"mode": "none"}},
            "env": {"FAKE_CLAUDE_MODE": "guidance_probe"},
            "objective_checks": [
                {"id": "token-visible", "type": "transcript_matches",
                 "must_match": [self.TOKEN]},
            ],
        }
        fixture.update(overrides)
        (eval_dir / "fixture.yaml").write_text(
            yaml.safe_dump(fixture, sort_keys=False), encoding="utf-8")
        return eval_dir

    def _run_main(self, argv_tail) -> tuple[int, str]:
        """run_eval.main() in-process, with the fake CLI and a fixed token."""
        import contextlib
        import io
        argv = ["run_eval.py", *[str(a) for a in argv_tail]]
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.dict(os.environ, {"CLAUDE_BIN": str(FAKE_CLAUDE)}), \
                mock.patch.object(guidance, "new_token", lambda: self.TOKEN), \
                contextlib.redirect_stdout(buf):
            rc = run_eval.main()
        return rc, buf.getvalue()

    @staticmethod
    def _only_run_dir(results_dir: Path, key: str) -> Path:
        runs = sorted(p for p in (results_dir / key).iterdir() if p.is_dir())
        assert len(runs) == 1, f"expected one run dir, got {runs}"
        return runs[0]

    def _summary(self, results_dir: Path, key: str, arm: str) -> dict:
        path = self._only_run_dir(results_dir, key) / arm / "summary.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_a_guidance_run_writes_the_documented_summary_fields(self):
        tmp = Path(tempfile.mkdtemp(prefix="guidance-run-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        self._skip_without_real_hook(root)
        eval_dir = self._guidance_fixture(tmp)
        results = tmp / "results"
        rc, out = self._run_main([eval_dir, "--arm", "both", "--guidance", root,
                                  "--results-dir", results, "--no-judge"])
        self.assertEqual(rc, 0, out)

        with_summary = self._summary(results, "guidance/alpha", "with_guidance")
        self.assertEqual(with_summary["subject"], "guidance")
        self.assertEqual(with_summary["section"], "alpha")
        self.assertEqual(with_summary["mode"], "section")
        self.assertEqual(with_summary["delivery"], "user")
        self.assertGreater(with_summary["bytes"], 0)
        self.assertEqual(with_summary["guard"]["expected"], True)
        self.assertEqual(with_summary["guard"]["observed"], True)
        self.assertIsNone(with_summary["error"])
        self.assertTrue(all(c["passed"] for c in with_summary["objective_checks"]),
                        with_summary["objective_checks"])

        without = self._summary(results, "guidance/alpha", "without_guidance")
        self.assertEqual(without["mode"], "none")
        self.assertEqual(without["bytes"], 0)
        self.assertEqual(without["guard"]["expected"], False)
        self.assertEqual(without["guard"]["observed"], False)
        self.assertFalse(any(c["passed"] for c in without["objective_checks"]),
                         "the control arm must not see the magic word")

        report = (self._only_run_dir(results, "guidance/alpha")
                  / "report.md").read_text(encoding="utf-8")
        self.assertIn("guidance/alpha", report)
        self.assertIn("with_guidance=section", report,
                      "the report header must name the mode pair")
        self.assertIn("without_guidance=none", report)

    def test_a_guard_miss_on_the_with_arm_is_inconclusive_and_exits_2(self):
        # The `with` arm's probe came back blind: the guidance did not reach
        # the agent, so whatever that arm scored is meaningless. It must be
        # INCONCLUSIVE with no score written — never PASS, never FAIL.
        tmp = Path(tempfile.mkdtemp(prefix="guidance-guardmiss-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        self._skip_without_real_hook(root)
        eval_dir = self._guidance_fixture(
            tmp, env={"FAKE_CLAUDE_MODE": "guidance_blind"})
        results = tmp / "results"
        rc, out = self._run_main([eval_dir, "--arm", "with_guidance",
                                  "--guidance", root, "--results-dir", results,
                                  "--no-judge"])
        self.assertEqual(rc, 2, out)
        self.assertIn("INCONCLUSIVE", out)
        summary = self._summary(results, "guidance/alpha", "with_guidance")
        self.assertEqual(summary["guard"], dict(summary["guard"],
                                                expected=True, observed=False))
        self.assertIsNone(summary["objective_checks"],
                          "no score may be written for an arm whose delivery "
                          "could not be proved")
        self.assertIsNone(summary["judge"])
        self.assertEqual(summary["error"]["type"], "guard_miss")

    def test_a_contaminated_control_arm_is_inconclusive_and_exits_2(self):
        # The trap this whole subject exists for: on a machine carrying the
        # fleet hook, ~/.claude/CLAUDE.md IS the guidance, so a `none` arm can
        # be silently delivered-to and the A/B reports a null delta that reads
        # as "the guidance does nothing". Simulated here with an ambient
        # memory file the fake CLI loads regardless of the arm's config dir.
        tmp = Path(tempfile.mkdtemp(prefix="guidance-contam-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        ambient = tmp / "ambient-CLAUDE.md"
        ambient.write_text(f"The magic word is {self.TOKEN}.\n", encoding="utf-8")
        eval_dir = self._guidance_fixture(
            tmp, env={"FAKE_CLAUDE_MODE": "guidance_probe",
                      "FAKE_CLAUDE_AMBIENT_MEMORY": str(ambient)})
        results = tmp / "results"
        rc, out = self._run_main([eval_dir, "--arm", "without_guidance",
                                  "--guidance", root, "--results-dir", results,
                                  "--no-judge"])
        self.assertEqual(rc, 2, out)
        self.assertIn("INCONCLUSIVE", out)
        summary = self._summary(results, "guidance/alpha", "without_guidance")
        self.assertFalse(summary["guard"]["expected"])
        self.assertTrue(summary["guard"]["observed"])
        self.assertIsNone(summary["objective_checks"])

    def test_a_guard_that_cannot_run_is_inconclusive_not_a_skipped_guard(self):
        tmp = Path(tempfile.mkdtemp(prefix="guidance-guarderr-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        self._skip_without_real_hook(root)
        eval_dir = self._guidance_fixture(tmp, env={"FAKE_CLAUDE_MODE": "error"})
        results = tmp / "results"
        rc, out = self._run_main([eval_dir, "--arm", "with_guidance",
                                  "--guidance", root, "--results-dir", results,
                                  "--no-judge"])
        self.assertEqual(rc, 2, out)
        summary = self._summary(results, "guidance/alpha", "with_guidance")
        self.assertIsNone(summary["guard"]["observed"])
        self.assertEqual(summary["error"]["type"], "guard_error")
        self.assertIsNone(summary["objective_checks"])

    def _argv_lines(self, log: Path) -> list[dict]:
        return [json.loads(line) for line in
                log.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_guidance_arms_get_user_project_and_skill_arms_keep_project(self):
        tmp = Path(tempfile.mkdtemp(prefix="guidance-argv-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        self._skip_without_real_hook(root)
        log = tmp / "argv.jsonl"
        eval_dir = self._guidance_fixture(
            tmp, env={"FAKE_CLAUDE_MODE": "guidance_probe",
                      "FAKE_CLAUDE_ARGV_LOG": str(log)})
        rc, out = self._run_main([eval_dir, "--arm", "both", "--guidance", root,
                                  "--results-dir", tmp / "results", "--no-judge"])
        self.assertEqual(rc, 0, out)
        calls = self._argv_lines(log)
        self.assertEqual(len(calls), 4, "two arms x (guard probe + agent)")
        for call in calls:
            with self.subTest(argv=call["argv"]):
                argv = call["argv"]
                self.assertIn("--setting-sources", argv)
                self.assertEqual(argv[argv.index("--setting-sources") + 1],
                                 "user,project",
                                 "a guidance arm must read USER memory, which "
                                 "is where the fleet hook delivers")
                self.assertNotIn("SKILLS_EVALS_AMBIENT_LEAK", call["env_keys"])

        # And the skill subject is untouched: still `project`, still the
        # ambient environment it has always had.
        skill_log = tmp / "skill-argv.jsonl"
        with mock.patch.dict(os.environ, {
                "CLAUDE_BIN": str(FAKE_CLAUDE), "FAKE_CLAUDE_MODE": "agent",
                "FAKE_CLAUDE_ARGV_LOG": str(skill_log)}):
            proc = subprocess.run(
                [sys.executable, str(HARNESS_DIR / "run_eval.py"),
                 str(REPO_ROOT / "evals" / "workflow-path-audit"),
                 "--arm", "without_skill", "--no-judge",
                 "--results-dir", str(tmp / "skill-results")],
                cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        skill_calls = self._argv_lines(skill_log)
        self.assertEqual(len(skill_calls), 1, "one agent call, no guard probe")
        argv = skill_calls[0]["argv"]
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "project")

    def test_delivery_project_falls_back_to_workspace_memory(self):
        # The documented fallback for a CLI that does not read memory from
        # CLAUDE_CONFIG_DIR: same real hook, pointed at the workspace, read as
        # PROJECT memory — and `delivery: project` recorded in every summary.
        tmp = Path(tempfile.mkdtemp(prefix="guidance-project-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        self._skip_without_real_hook(root)
        log = tmp / "argv.jsonl"
        eval_dir = self._guidance_fixture(
            tmp, env={"FAKE_CLAUDE_MODE": "guidance_probe",
                      "FAKE_CLAUDE_ARGV_LOG": str(log)})
        results = tmp / "results"
        rc, out = self._run_main([eval_dir, "--arm", "with_guidance",
                                  "--guidance", root, "--delivery", "project",
                                  "--results-dir", results, "--no-judge"])
        self.assertEqual(rc, 0, out)
        summary = self._summary(results, "guidance/alpha", "with_guidance")
        self.assertEqual(summary["delivery"], "project")
        self.assertTrue(summary["guard"]["observed"])
        for call in self._argv_lines(log):
            argv = call["argv"]
            self.assertEqual(argv[argv.index("--setting-sources") + 1], "project")

    def test_a_whole_run_never_touches_the_real_user_memory(self):
        real = Path(os.path.expanduser("~")) / ".claude" / "CLAUDE.md"
        before = real.read_bytes() if real.is_file() else None
        tmp = Path(tempfile.mkdtemp(prefix="guidance-realhome-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        self._skip_without_real_hook(root)
        eval_dir = self._guidance_fixture(tmp)
        rc, out = self._run_main([eval_dir, "--arm", "both", "--guidance", root,
                                  "--results-dir", tmp / "results", "--no-judge"])
        self.assertEqual(rc, 0, out)
        after = real.read_bytes() if real.is_file() else None
        self.assertEqual(after, before,
                         f"{real} changed across a guidance run — every arm "
                         "gets a scratch config dir precisely so this file is "
                         "never delivered to")

    def test_unknown_section_id_through_main_exits_2_naming_the_manifest(self):
        tmp = Path(tempfile.mkdtemp(prefix="guidance-badid-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        eval_dir = self._guidance_fixture(tmp, section="no-such-section")
        rc, out = self._run_main([eval_dir, "--arm", "both", "--guidance", root,
                                  "--results-dir", tmp / "results", "--no-judge"])
        self.assertEqual(rc, 2)
        self.assertIn("eval-coverage.yml", out)

    def test_missing_guidance_checkout_through_main_exits_2_naming_the_flag(self):
        tmp = Path(tempfile.mkdtemp(prefix="guidance-nocheckout-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        eval_dir = self._guidance_fixture(tmp)
        rc, out = self._run_main([eval_dir, "--arm", "both",
                                  "--guidance", tmp / "nowhere",
                                  "--results-dir", tmp / "results", "--no-judge"])
        self.assertEqual(rc, 2)
        self.assertIn("--guidance", out)
