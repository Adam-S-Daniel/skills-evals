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

    # ------------------------------------------------------------------
    # Item 6 — scripts/make_badge.py accepts guidance/<id>
    # ------------------------------------------------------------------

    @staticmethod
    def _write_summary_file(run_dir: Path, arm: str, passed: int, total: int,
                            judge: float | None) -> None:
        arm_dir = run_dir / arm
        arm_dir.mkdir(parents=True, exist_ok=True)
        checks = [{"id": f"c{i}", "passed": i < passed} for i in range(total)]
        payload = {"arm": arm, "error": None, "objective_checks": checks,
                   "judge": {"overall": judge} if judge is not None else None}
        (arm_dir / "summary.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_make_badge_reads_a_guidance_runs_with_and_without_guidance_arms(self):
        tmp = Path(tempfile.mkdtemp(prefix="guidance-badge-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        results = tmp / "results"
        run = results / "guidance" / "security" / "20260904T070000Z"
        self._write_summary_file(run, "with_guidance", 4, 4, 8.0)
        self._write_summary_file(run, "without_guidance", 1, 4, 5.0)

        badge = make_badge.build_badge(results, "guidance/security")
        self.assertEqual(badge["label"], "guidance eval: security")
        self.assertEqual(badge["color"], "green")
        self.assertIn("with 4/4 vs without 1/4", badge["message"])
        self.assertIn("2026-09-04", badge["message"])

        out = tmp / "badges" / "guidance" / "security.json"
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "make_badge.py"),
             "guidance/security", "--results-dir", str(results), "--out", str(out)],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["label"],
                         "guidance eval: security")

    def test_make_badge_still_reads_skill_arms_for_a_skill_name(self):
        tmp = Path(tempfile.mkdtemp(prefix="skill-badge-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        results = tmp / "results"
        run = results / "workflow-path-audit" / "20260904T070000Z"
        self._write_summary_file(run, "with_skill", 4, 4, 8.0)
        self._write_summary_file(run, "without_skill", 1, 4, 5.0)
        badge = make_badge.build_badge(results, "workflow-path-audit")
        self.assertEqual(badge["label"], "skill eval: workflow-path-audit")
        self.assertEqual(badge["color"], "green")

    def test_make_badge_rejects_a_name_that_escapes_the_results_tree(self):
        for bad in ("../etc", "/abs/name", "guidance/../../x"):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    make_badge.build_badge(Path("results"), bad)

    # ------------------------------------------------------------------
    # Item 7 — the committed delivery canary, evals/guidance/_delivery
    # ------------------------------------------------------------------

    def _delivery_fixture(self) -> dict:
        return yaml.safe_load((DELIVERY_DIR / "fixture.yaml").read_text(encoding="utf-8"))

    def test_the_delivery_fixture_declares_one_arm_per_mode(self):
        fixture = self._delivery_fixture()
        self.assertEqual(fixture["subject"], "guidance")
        self.assertIsInstance(fixture["section"], str)
        modes = [arm["mode"] for arm in fixture["arms"].values()]
        self.assertEqual(sorted(modes), sorted(guidance.MODES),
                         "the delivery canary runs one arm per mode")
        self.assertEqual(len(fixture["arms"]), 5)
        # Every non-none arm asserts the token IS visible; the control arm
        # asserts it is not. The token is fresh per run, so the fixture names
        # it with the harness's placeholder.
        for name, arm in fixture["arms"].items():
            with self.subTest(arm=name):
                checks = arm["objective_checks"]
                self.assertEqual([c["type"] for c in checks], ["transcript_matches"])
                key = "must_not_match" if arm["mode"] == "none" else "must_match"
                self.assertEqual(checks[0][key], [run_eval.TOKEN_PLACEHOLDER])

    def test_the_delivery_fixtures_section_exists_in_the_real_manifest(self):
        if not (REAL_GUIDANCE_DIR / guidance.MANIFEST_REL).is_file():
            reason = (f"no _agent-guidance checkout at {REAL_GUIDANCE_DIR} — "
                      "skipping the section-id agreement check")
            print(reason)
            self.skipTest(reason)
        manifest = guidance.load_manifest(REAL_GUIDANCE_DIR)
        row = guidance.find_row(manifest, self._delivery_fixture()["section"],
                                REAL_GUIDANCE_DIR)
        self.assertTrue(row["heading"])

    def test_the_delivery_canary_runs_all_five_modes_against_the_real_guidance(self):
        if not (REAL_GUIDANCE_DIR / guidance.HOOK_REL).is_file():
            reason = (f"no _agent-guidance checkout at {REAL_GUIDANCE_DIR} — "
                      "skipping the end-to-end delivery-canary run")
            print(reason)
            self.skipTest(reason)
        tmp = Path(tempfile.mkdtemp(prefix="delivery-canary-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        results = tmp / "results"
        fixture = self._delivery_fixture()
        # The committed fixture carries no `env:` (it is production), so the
        # fake CLI's mode reaches the child through the allowlist's documented
        # test seam instead — the same one init_probe.py has.
        with mock.patch.object(guidance, "EXTRA_PASSTHROUGH", ("FAKE_CLAUDE_MODE",)), \
                mock.patch.dict(os.environ, {"FAKE_CLAUDE_MODE": "guidance_probe"}):
            rc, out = self._run_main([DELIVERY_DIR, "--arm", "both",
                                      "--guidance", REAL_GUIDANCE_DIR,
                                      "--results-dir", results, "--no-judge"])
        self.assertEqual(rc, 0, out)
        key = f"guidance/{fixture['section']}"
        for name, arm in fixture["arms"].items():
            with self.subTest(arm=name):
                summary = self._summary(results, key, name)
                self.assertTrue(summary["guard"]["ok"], summary["guard"])
                self.assertEqual(summary["guard"]["expected"], arm["mode"] != "none")
                self.assertEqual(summary["bytes"] > 0, arm["mode"] != "none")
                self.assertTrue(all(c["passed"] for c in summary["objective_checks"]),
                                summary["objective_checks"])
        stub = self._summary(results, key, "with_guidance_stub")["bytes"]
        full = self._summary(results, key, "with_guidance_full")["bytes"]
        minus = self._summary(results, key, "with_guidance_full_minus_section")["bytes"]
        section = self._summary(results, key, "with_guidance_section")["bytes"]
        self.assertLess(stub, full)
        self.assertLess(minus, full)
        self.assertLess(section, full)

    def test_every_committed_fixture_declares_a_known_subject(self):
        for path in sorted((REPO_ROOT / "evals").glob("**/fixture.yaml")):
            with self.subTest(fixture=str(path.relative_to(REPO_ROOT))):
                fixture = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIn(fixture.get("subject", "skill"),
                              ("skill", "guidance"))

    # ------------------------------------------------------------------
    # Item 8 + the dispatch input — .github/workflows/eval.yml
    # ------------------------------------------------------------------

    MARKDOWN_IT_PIN = "markdown-it-py==4.2.0"

    def _workflow(self) -> dict:
        return yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))

    def _eval_steps(self) -> list[dict]:
        return self._workflow()["jobs"]["eval"]["steps"]

    def _step_named(self, prefix: str) -> dict:
        for step in self._eval_steps():
            if (step.get("name") or "").startswith(prefix):
                return step
        self.fail(f"no step in eval.yml whose name starts with {prefix!r}")

    def test_dispatch_takes_a_fixture_input_defaulting_to_workflow_path_audit(self):
        # Without this input no fixture but workflow-path-audit can ever get a
        # real run on main, so a guidance fixture (or any backfill fixture)
        # could never be measured at all.
        doc = self._workflow()
        triggers = doc.get("on", doc.get(True))
        self.assertEqual(set(triggers), {"schedule", "workflow_dispatch"},
                         "eval.yml stays schedule + workflow_dispatch only")
        inputs = (triggers["workflow_dispatch"] or {}).get("inputs") or {}
        self.assertIn("fixture", inputs)
        self.assertEqual(inputs["fixture"].get("default"), "evals/workflow-path-audit",
                         "the scheduled run keeps its default")
        self.assertFalse(inputs["fixture"].get("required"),
                         "the schedule passes no inputs, so it must not be required")

    def test_the_fixture_input_is_read_from_the_event_file_never_interpolated(self):
        # `${{ inputs.fixture }}` inside a run: block is a shell-injection
        # surface in the one workflow that holds a live API key. The value is
        # read from $GITHUB_EVENT_PATH as data instead.
        for step in self._eval_steps():
            run = step.get("run") or ""
            with self.subTest(step=step.get("name")):
                self.assertNotIn("${{", run)
        scripts = [s.get("run") or "" for s in self._eval_steps()]
        reading = [s for s in scripts if "GITHUB_EVENT_PATH" in s]
        self.assertEqual(len(reading), 1,
                         "exactly one step reads the dispatch input, and it "
                         "reads it from the event file")
        self.assertIn("inputs.fixture", reading[0],
                      "the event file's .inputs.fixture is the value read")

    def test_the_fixture_is_validated_before_any_credential_step(self):
        names = [(s.get("name") or "") for s in self._eval_steps()]
        validate = next(i for i, s in enumerate(self._eval_steps())
                        if "GITHUB_EVENT_PATH" in (s.get("run") or ""))
        credential = next(i for i, name in enumerate(names)
                          if name.startswith("Mint OIDC token"))
        self.assertLess(validate, credential,
                        "a value that names no committed fixture must fail the "
                        "step before any credential is minted")
        run_step = self._step_named("Run the eval")
        self.assertIn("eval-fixture", run_step["run"],
                      "the run step must take the fixture from the file the "
                      "validation step wrote, not from the event again")

    def _validation_script(self) -> str:
        for step in self._eval_steps():
            if "GITHUB_EVENT_PATH" in (step.get("run") or ""):
                return step["run"]
        self.fail("no validation step found")

    def _run_validation(self, event: dict | None) -> subprocess.CompletedProcess:
        tmp = Path(tempfile.mkdtemp(prefix="eval-dispatch-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        event_path = tmp / "event.json"
        event_path.write_text(json.dumps(event if event is not None else {}),
                              encoding="utf-8")
        env = dict(os.environ, GITHUB_EVENT_PATH=str(event_path),
                   RUNNER_TEMP=str(tmp))
        proc = subprocess.run(["bash", "-c", self._validation_script()],
                              cwd=str(REPO_ROOT), env=env, capture_output=True,
                              text=True, timeout=120)
        proc.selected = (tmp / "eval-fixture").read_text(encoding="utf-8") \
            if (tmp / "eval-fixture").is_file() else None
        return proc

    def test_the_validation_step_accepts_every_committed_fixture(self):
        committed = sorted(str(p.parent.relative_to(REPO_ROOT))
                           for p in (REPO_ROOT / "evals").glob("**/fixture.yaml"))
        self.assertIn("evals/guidance/_delivery", committed)
        for fixture in committed:
            with self.subTest(fixture=fixture):
                proc = self._run_validation({"inputs": {"fixture": fixture}})
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(proc.selected, fixture)

    def test_the_validation_step_defaults_when_the_event_carries_no_input(self):
        # The scheduled run: no `inputs` in the event payload at all.
        for event in ({}, {"inputs": {}}, {"inputs": {"fixture": ""}}):
            with self.subTest(event=event):
                proc = self._run_validation(event)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertEqual(proc.selected, "evals/workflow-path-audit")

    def test_the_validation_step_rejects_anything_that_names_no_fixture(self):
        for bad in ("evals/nope", "../../etc/passwd", "/etc", "evals",
                    "evals/workflow-path-audit/seed", "evals/guidance",
                    "; rm -rf /", "evals/workflow-path-audit "):
            with self.subTest(fixture=bad):
                proc = self._run_validation({"inputs": {"fixture": bad}})
                self.assertEqual(proc.returncode, 1,
                                 f"{bad!r} must fail the step: "
                                 f"{proc.stdout + proc.stderr}")
                self.assertIn("names no committed fixture", proc.stdout + proc.stderr)
                self.assertIsNone(proc.selected)

    def test_agent_guidance_is_checked_out_side_by_side_without_credentials(self):
        checkout = next(
            s for s in self._eval_steps()
            if (s.get("with") or {}).get("repository", "").endswith("/_agent-guidance"))
        with_block = checkout["with"]
        self.assertEqual(with_block.get("path"), "_agent-guidance",
                         "side by side, so the harness's sibling default resolves")
        self.assertIs(with_block.get("persist-credentials"), False)
        self.assertRegex(checkout["uses"], r"^[A-Za-z0-9._/-]+@[0-9a-f]{40}$")
        run = self._step_named("Run the eval")["run"]
        self.assertNotIn("--registry _agent-guidance", run,
                         "_agent-guidance is not a skill registry")
        self.assertIn("--guidance ../_agent-guidance", run)

    def test_markdown_it_py_is_pinned_exact_in_both_workflows(self):
        for workflow in (EVAL_WORKFLOW, CI_WORKFLOW):
            with self.subTest(workflow=workflow.name):
                doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))
                installs = [s.get("run") or "" for job in doc["jobs"].values()
                            for s in job.get("steps", [])
                            if "pip install" in (s.get("run") or "")]
                self.assertTrue(installs, "no pip install step found")
                self.assertTrue(
                    any(self.MARKDOWN_IT_PIN in run for run in installs),
                    f"{workflow.name} must install {self.MARKDOWN_IT_PIN} — the "
                    "guidance payload parser is pinned exact, per the repo's "
                    "cooling-off convention")

    def test_the_security_header_carries_the_agent_guidance_clause(self):
        import itertools
        lines = EVAL_WORKFLOW.read_text(encoding="utf-8").splitlines()
        header = "\n".join(itertools.takewhile(
            lambda line: line.strip() == "" or line.lstrip().startswith("#"), lines))
        self.assertIn("_agent-guidance", header,
                      "the header must name every checked-out repo")
        self.assertIn("bypassPermissions", header)
        for phrase in ("write access", "equivalent to key access"):
            self.assertIn(phrase, header)
        guidance_clause = [para for para in header.split("#\n")
                           if "_agent-guidance" in para]
        self.assertTrue(
            any("key access" in para for para in guidance_clause),
            "the header must say that write access to _agent-guidance's "
            "default branch now equals key access here — the with arm "
            "executes its content under bypassPermissions")

    # ------------------------------------------------------------------
    # Item 1 — the ablation pair, and arm/schema validation
    # ------------------------------------------------------------------

    def test_the_default_arm_pair_is_section_versus_none(self):
        arms = run_eval.guidance_arms({}, "both")
        self.assertEqual([(a["name"], a["mode"]) for a in arms],
                         [("with_guidance", "section"), ("without_guidance", "none")])

    def test_ablation_runs_the_fixtures_declared_second_pair(self):
        fixture = {"ablation": ["full", "full-minus-section"]}
        arms = run_eval.guidance_arms(fixture, "both", ablation=True)
        self.assertEqual([(a["name"], a["mode"]) for a in arms],
                         [("ablation_full", "full"),
                          ("ablation_full_minus_section", "full-minus-section")])
        # Both ablation arms are delivered arms, so both must SEE the token —
        # the ablation asks about marginal value in situ, not about delivery.
        for arm in arms:
            self.assertTrue(guidance.guard_expectation(arm["mode"]))
        for bad in ({}, {"ablation": ["full"]}, {"ablation": "full"},
                    {"ablation": ["full", "full"]}):
            with self.subTest(fixture=bad):
                with self.assertRaises(guidance.GuidanceError):
                    run_eval.guidance_arms(bad, "both", ablation=True)

    def test_an_ablation_run_end_to_end_delivers_both_arms(self):
        tmp = Path(tempfile.mkdtemp(prefix="guidance-ablation-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = self._checkout()
        self._skip_without_real_hook(root)
        eval_dir = self._guidance_fixture(
            tmp, section="bravo", ablation=["full", "full-minus-section"])
        results = tmp / "results"
        rc, out = self._run_main([eval_dir, "--arm", "both", "--ablation",
                                  "--guidance", root, "--results-dir", results,
                                  "--no-judge"])
        self.assertEqual(rc, 0, out)
        full = self._summary(results, "guidance/bravo", "ablation_full")
        minus = self._summary(results, "guidance/bravo",
                              "ablation_full_minus_section")
        self.assertTrue(full["guard"]["ok"] and minus["guard"]["ok"])
        self.assertGreater(full["bytes"], minus["bytes"],
                           "the ablation arm is the corpus MINUS the section")

    def test_an_arm_whose_name_disagrees_with_its_mode_is_rejected(self):
        for arms in ({"with_guidance": {"mode": "none"}},
                     {"without_guidance": {"mode": "section"}},
                     {"with_guidance": {"mode": "nonsense"}},
                     {"with_guidance": {}},
                     {"../escape": {"mode": "section"}}):
            with self.subTest(arms=arms):
                with self.assertRaises(guidance.GuidanceError):
                    run_eval.guidance_arms({"arms": arms}, "both")

    def test_an_unknown_arm_name_lists_the_arms_the_fixture_declares(self):
        with self.assertRaises(guidance.GuidanceError) as ctx:
            run_eval.guidance_arms({}, "with_skill")
        self.assertIn("with_guidance", str(ctx.exception))

    def test_a_skill_fixture_rejects_a_guidance_arm_name(self):
        tmp = Path(tempfile.mkdtemp(prefix="skill-arm-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = subprocess.run(
            [sys.executable, str(HARNESS_DIR / "run_eval.py"),
             str(REPO_ROOT / "evals" / "workflow-path-audit"),
             "--arm", "with_guidance", "--results-dir", str(tmp)],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not valid for a skill fixture", proc.stdout + proc.stderr)

    # ------------------------------------------------------------------
    # Item 9 — README and DESIGN say what this subject does
    # ------------------------------------------------------------------

    def test_readme_and_design_document_the_guidance_subject(self):
        for doc_path in (REPO_ROOT / "README.md", REPO_ROOT / "DESIGN.md"):
            text = doc_path.read_text(encoding="utf-8")
            with self.subTest(doc=doc_path.name):
                self.assertIn("## Guidance subject", text)
                for mode in guidance.MODES:
                    self.assertIn(f"`{mode}`", text,
                                  f"{doc_path.name} must name the {mode} mode")
                for phrase in ("INCONCLUSIVE", "CLAUDE_CONFIG_DIR",
                               "fleet-memory"):
                    self.assertIn(phrase, text,
                                  f"{doc_path.name} must state the {phrase} rule")

    def test_a_checkout_without_the_hook_exits_2_naming_the_hook(self):
        # The guidance subject delivers through the REAL hook, so a checkout
        # that has the manifest but not the hook is a configuration problem
        # with a named message — never a traceback out of the middle of a run.
        tmp = Path(tempfile.mkdtemp(prefix="guidance-nohook-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = tmp / "checkout"
        make_guidance_checkout(root)
        hook = root / guidance.HOOK_REL
        hook.unlink(missing_ok=True)
        eval_dir = self._guidance_fixture(tmp)
        rc, out = self._run_main([eval_dir, "--arm", "with_guidance",
                                  "--guidance", root,
                                  "--results-dir", tmp / "results", "--no-judge"])
        self.assertEqual(rc, 2, out)
        self.assertIn("fleet-memory", out)

    def test_ci_checks_out_agent_guidance_so_the_hook_tests_actually_run(self):
        doc = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
        checkouts = [s for job in doc["jobs"].values()
                     for s in job.get("steps", [])
                     if (s.get("uses") or "").startswith("actions/checkout@")]
        guidance_checkout = next(
            (s for s in checkouts
             if (s.get("with") or {}).get("repository", "").endswith("/_agent-guidance")),
            None)
        self.assertIsNotNone(
            guidance_checkout,
            "without an _agent-guidance checkout the real-hook delivery tests "
            "skip in CI, and the delivery path is never exercised there")
        self.assertEqual((guidance_checkout["with"] or {}).get("path"),
                         "_agent-guidance")
        self.assertIs((guidance_checkout["with"] or {}).get("persist-credentials"),
                      False)
        self.assertRegex(guidance_checkout["uses"],
                         r"^[A-Za-z0-9._/-]+@[0-9a-f]{40}$")

    def test_an_arm_with_an_unknown_key_is_rejected_at_load_time(self):
        with self.assertRaises(guidance.GuidanceError) as ctx:
            run_eval.guidance_arms(
                {"arms": {"with_guidance": {"mode": "section",
                                            "objective_check": []}}}, "both")
        self.assertIn("objective_check", str(ctx.exception))

    def test_the_delivery_canary_fits_inside_the_workflow_job_timeout(self):
        fixture = self._delivery_fixture()
        doc = yaml.safe_load(EVAL_WORKFLOW.read_text(encoding="utf-8"))
        job_budget_s = doc["jobs"]["eval"]["timeout-minutes"] * 60
        per_arm = fixture["timeout_s"] + fixture["guard"]["timeout_s"]
        worst_case = per_arm * len(fixture["arms"])
        self.assertLess(
            worst_case, job_budget_s * 0.75,
            f"five arms x (agent {fixture['timeout_s']}s + guard "
            f"{fixture['guard']['timeout_s']}s) = {worst_case}s does not leave "
            f"room inside eval.yml's {job_budget_s}s job timeout for setup, "
            "the CLI install and the badge commit")
