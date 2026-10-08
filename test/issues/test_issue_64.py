#!/usr/bin/env python3
"""Issue #64 (local half) — `scripts/eval_coverage.py`, the coverage census.

Every test drives the production entry point (`python3 scripts/eval_coverage.py`
as a subprocess) against a synthetic world built under its own mkdtemp: four
registries named and laid out as `harness/registries.yml` says, an `evals/`
tree, and a non-coverage file. Nothing reads the operator's real registry
checkouts or `~/.claude`; no network, no clock.

The committed `evals/non-coverage.yml` and `evals/` tree are only LOADED
(against empty-ish synthetic registries), to prove they still parse; their
contents are not asserted skill by skill.

Discovered and run by test/run_tests.py (see `build_suite`/`DISCOVERY_DIR`
there); also runnable on its own with `python3 test/issues/test_issue_64.py`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

TEST_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TEST_DIR.parent
SCRIPT = REPO_ROOT / "scripts" / "eval_coverage.py"
REGISTRIES_YML = REPO_ROOT / "harness" / "registries.yml"
COMMITTED_NON_COVERAGE = REPO_ROOT / "evals" / "non-coverage.yml"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import eval_coverage  # noqa: E402

REGISTRIES = {e["name"]: e for e in yaml.safe_load(
    REGISTRIES_YML.read_text(encoding="utf-8"))["registries"]}
PRIVATE = "adam-agentskills-private"
PRIVATE_COVERED = "zz-private-covered-marker"
PRIVATE_GAP = "zz-private-gap-marker"

# Words the fleet's gitleaks generic rule keys on; none may be a field name in
# the committed non-coverage file.
SCANNER_WORDS = ("access", "auth", "api", "credential", "creds", "key",
                 "passwd", "password", "secret", "token")


class World:
    """A synthetic census input set under a scratch directory."""

    def __init__(self, test: unittest.TestCase):
        self.root = Path(tempfile.mkdtemp(prefix="issue64-"))
        test.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.evals = self.root / "evals"
        self.evals.mkdir()
        self.registry_dirs = {}
        for name in REGISTRIES:
            self.registry_dirs[name] = self.root / "reg" / name
            self.registry_dirs[name].mkdir(parents=True)
        self.skips: list[dict] = []
        self.private_skips: list[dict] = []
        self.populate()

    # building blocks ------------------------------------------------------

    def add_skill(self, registry: str, skill: str, bundle: str = "bundle-x"):
        parts = REGISTRIES[registry]["layout"].split("/")
        parts[-2] = skill
        # any remaining wildcard is the bundle segment
        parts = [bundle if p == "*" else p for p in parts]
        path = self.registry_dirs[registry].joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: {skill}\ndescription: stand-in.\n---\n",
                        encoding="utf-8")

    def add_fixture(self, relpath: str, skill: str | None, registry: str | None,
                    extra: dict | None = None):
        doc = dict(extra or {})
        if skill is not None:
            doc["skill"] = skill
        if registry is not None:
            doc["registry"] = REGISTRIES[registry]["url"]
        path = self.evals / relpath / "fixture.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(doc), encoding="utf-8")

    def skip(self, registry: str, skill: str, reason: str = "because",
             private: bool = False):
        (self.private_skips if private else self.skips).append(
            {"registry": registry, "skill": skill, "decision": "skip",
             "reason": reason})

    def populate(self):
        # three layouts: plugin bundles, flat, dot-dir
        for skill in ("alpha", "beta", "gamma", "delta"):
            self.add_skill("adam-agentskills", skill, "plug-a")
        self.add_skill("adam-agentskills", "epsilon", "plug-b")
        self.add_skill("cms-platform", "cms-covered")
        self.add_skill("cms-platform", "cms-gap")
        self.add_skill("adamdaniel.ai", "site-skill")
        self.add_skill(PRIVATE, PRIVATE_COVERED, "plug-p")
        self.add_skill(PRIVATE, PRIVATE_GAP, "plug-p")
        self.add_fixture("alpha", "alpha", "adam-agentskills")          # flat
        self.add_fixture("beta/one", "beta", "adam-agentskills")        # nested
        self.add_fixture("beta/two", "beta", "adam-agentskills")
        self.add_fixture("cms-covered", "cms-covered", "cms-platform")
        self.add_fixture(PRIVATE_COVERED, PRIVATE_COVERED, PRIVATE)
        # a non-skill subject: ignored, not refused
        self.add_fixture("guidance/_delivery", None, None,
                         {"subject": "guidance"})
        self.skip("adam-agentskills", "gamma", "machine-bound | WSL")

    def clear_all_gaps(self):
        self.skip("adam-agentskills", "delta")
        self.skip("adam-agentskills", "epsilon")
        self.skip("cms-platform", "cms-gap")
        self.skip("adamdaniel.ai", "site-skill")
        self.skip(PRIVATE, PRIVATE_GAP, private=True)

    @staticmethod
    def write_raw(path: Path, content: str | bytes) -> None:
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")

    def raw_fixture(self, relpath: str, content: str | bytes) -> None:
        path = self.evals / relpath / "fixture.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.write_raw(path, content)

    # running --------------------------------------------------------------

    def _write_skips(self, name: str, rows: list[dict]) -> Path:
        path = self.root / name
        path.write_text(yaml.safe_dump({"skips": rows}), encoding="utf-8")
        return path

    def run(self, *extra: str, omit: tuple[str, ...] = (),
            paths: dict | None = None, order: list[str] | None = None,
            use_private_file: bool = True,
            raw_non_coverage: str | bytes | None = None,
            raw_private: str | bytes | None = None):
        non_coverage = self._write_skips("non-coverage.yml", self.skips)
        if raw_non_coverage is not None:
            self.write_raw(non_coverage, raw_non_coverage)
        argv = [sys.executable, str(SCRIPT), "--evals-dir", str(self.evals),
                "--non-coverage", str(non_coverage)]
        if raw_private is not None:
            private = self.root / "private-non-coverage.yml"
            self.write_raw(private, raw_private)
            argv += ["--private-non-coverage", str(private)]
        elif self.private_skips and use_private_file:
            argv += ["--private-non-coverage",
                     str(self._write_skips("private-non-coverage.yml",
                                           self.private_skips))]
        paths = {**self.registry_dirs, **(paths or {})}
        for name in (order or list(REGISTRIES)):
            if name not in omit:
                argv += ["--registry", f"{name}={paths[name]}"]
        argv += list(extra)
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(self.root),
               "LC_ALL": "C.UTF-8"}
        return subprocess.run(argv, capture_output=True, text=True, env=env,
                              cwd=self.root, timeout=120)

    def json(self, *extra: str, **kw) -> dict:
        proc = self.run("--json", *extra, **kw)
        assert proc.returncode in (0, 1), proc.stderr
        return json.loads(proc.stdout)


def rows(doc: dict, registry: str) -> dict:
    reg = next(r for r in doc["registries"] if r["name"] == registry)
    return {r["skill"]: r for r in reg["skills"]}


class StatusesAndCounts(unittest.TestCase):
    def test_draft_fixture_does_not_close_a_gap(self):
        world = World(self)
        world.add_fixture("pending/delta", "delta", "adam-agentskills",
                          {"draft": True, "context": {
                              "repository": "Adam-S-Daniel/skills-evals",
                              "revision": "a" * 40,
                              "guidance_revision": "b" * 40,
                              "budget": {"guidance_bytes": 1,
                                         "skill_catalog_bytes": 1,
                                         "skill_payload_bytes": 1}}})
        doc = world.json()
        self.assertEqual(rows(doc, "adam-agentskills")["delta"]["status"], "gap")
        self.assertEqual(rows(doc, "adam-agentskills")["delta"]["fixtures"], 0)

    def test_every_status_fixture_count_and_reason(self):
        doc = World(self).json()
        a = rows(doc, "adam-agentskills")
        self.assertEqual(
            {k: (v["status"], v["fixtures"], v["bundle"]) for k, v in a.items()},
            {"alpha": ("covered", 1, "plug-a"),
             "beta": ("covered", 2, "plug-a"),       # nested fixtures count
             "gamma": ("skipped", 0, "plug-a"),
             "delta": ("gap", 0, "plug-a"),
             "epsilon": ("gap", 0, "plug-b")})
        self.assertEqual(a["gamma"]["reason"], "machine-bound | WSL")
        self.assertIsNone(a["alpha"]["reason"])
        # flat and dot-dir layouts resolve too, with no bundle
        cms = rows(doc, "cms-platform")
        self.assertEqual(cms["cms-covered"]["status"], "covered")
        self.assertEqual(cms["cms-gap"]["status"], "gap")
        self.assertIsNone(cms["cms-gap"]["bundle"])
        self.assertEqual(rows(doc, "adamdaniel.ai")["site-skill"]["status"], "gap")
        counts = {r["name"]: r["counts"] for r in doc["registries"]}
        self.assertEqual(counts["adam-agentskills"],
                         {"total": 5, "covered": 2, "skipped": 1, "gap": 2})
        self.assertEqual(doc["totals"],
                         {"total": 10, "covered": 4, "skipped": 1, "gap": 5})
        self.assertEqual(doc["problems"], [])

    def test_a_fixture_covers_by_its_own_fields_not_its_directory_name(self):
        w = World(self)
        # same skill name in a different registry must not cover cms-gap's
        # namesake, and a misleadingly named directory still covers `delta`
        w.add_fixture("misc/anything", "delta", "adam-agentskills")
        w.add_fixture("cms-gap", "cms-gap", "adam-agentskills")  # wrong registry
        doc = w.json()
        self.assertEqual(rows(doc, "adam-agentskills")["delta"]["fixtures"], 1)
        self.assertEqual(rows(doc, "cms-platform")["cms-gap"]["status"], "gap")
        self.assertIn("orphan_fixture", [p["kind"] for p in doc["problems"]])

    def test_markdown_table_has_status_counts_and_escapes_the_reason(self):
        proc = World(self).run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        md = proc.stdout
        self.assertIn("| adam-agentskills | 5 | 2 | 1 | 2 |", md)
        self.assertIn("| **Total** | 10 | 4 | 1 | 5 |", md)
        self.assertIn("| plug-a | gamma | skipped | 0 | machine-bound \\| WSL |", md)
        self.assertIn("| plug-a | delta | GAP | 0 |  |", md)
        self.assertIn("| plug-a | beta | covered | 2 |", md)

    def test_output_is_deterministic_and_has_no_local_paths(self):
        w = World(self)
        first = w.run("--json")
        second = w.run("--json", order=list(reversed(list(REGISTRIES))))
        self.assertEqual(first.stdout, second.stdout)
        self.assertNotIn(str(w.root), first.stdout + w.run().stdout)


class ExitCodes(unittest.TestCase):
    def test_a_gap_is_reported_but_only_fails_under_check(self):
        w = World(self)
        self.assertEqual(w.run().returncode, 0)
        proc = w.run("--check")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("delta", proc.stdout)  # the table still printed

    def test_check_passes_when_every_gap_is_covered_or_explicitly_skipped(self):
        w = World(self)
        w.clear_all_gaps()
        proc = w.run("--check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(w.json()["totals"]["gap"], 0)


class Refusals(unittest.TestCase):
    def assert_refused(self, proc, needle: str):
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout, "", "a refusal must not print a census")
        self.assertIn(needle, proc.stderr)

    def test_a_missing_registry_path_is_refused_not_counted_as_zero(self):
        w = World(self)
        proc = w.run("--check", paths={"cms-platform": w.root / "nope"})
        self.assert_refused(proc, "does not resolve to a directory")
        self.assertIn("cms-platform", proc.stderr)

    def test_a_registry_with_no_checkout_given_is_refused(self):
        # no fallback to a sibling directory
        self.assert_refused(World(self).run(omit=("adamdaniel.ai",)),
                            "has no --registry adamdaniel.ai=PATH")

    def test_a_registry_that_yields_no_skills_is_refused(self):
        w = World(self)
        shutil.rmtree(w.registry_dirs["cms-platform"])
        w.registry_dirs["cms-platform"].mkdir()
        self.assert_refused(w.run("--check"), "yields no skills")

    def test_an_unknown_registry_name_is_refused(self):
        w = World(self)
        proc = w.run("--registry", f"cms_platform={w.root}")
        self.assert_refused(proc, "cms_platform")

    def test_a_skill_fixture_without_a_known_registry_is_refused(self):
        w = World(self)
        w.add_fixture("noreg", "alpha", None)
        self.assert_refused(w.run(), "noreg")
        w2 = World(self)
        path = w2.evals / "badurl" / "fixture.yaml"
        path.parent.mkdir()
        path.write_text("skill: alpha\nregistry: https://example.com/x/y\n",
                        encoding="utf-8")
        self.assert_refused(w2.run(), "badurl")

    def test_a_skill_name_in_two_bundles_is_refused_in_every_mode(self):
        w = World(self)
        w.clear_all_gaps()
        w.add_skill("adam-agentskills", "alpha", "plug-b")
        for flags in ((), ("--json",), ("--check",), ("--json", "--check")):
            with self.subTest(flags=flags):
                self.assert_refused(w.run(*flags), "more than one bundle")
        self.assertIn("'alpha'", w.run().stderr)  # public: the name helps

    def test_invalid_utf8_in_any_input_file_is_refused_naming_the_file(self):
        bad = b"skips: []\n# \xff\xfe\n"
        w = World(self)
        self.assert_refused(w.run(raw_non_coverage=bad), "not valid UTF-8")
        self.assertIn("non-coverage.yml", w.run(raw_non_coverage=bad).stderr)
        w2 = World(self)
        w2.raw_fixture("badbytes", b"skill: alpha\n\xff\xfe\n")
        proc = w2.run()
        self.assert_refused(proc, "not valid UTF-8")
        self.assertIn("fixture.yaml", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        w3 = World(self)
        self.assert_refused(w3.run(raw_private=bad), "not valid UTF-8")

    def test_a_fixture_at_any_depth_counts_like_eval_ymls_find(self):
        # eval.yml: `find evals -mindepth 1 -name fixture.yaml`, any depth
        w = World(self)
        w.add_fixture("deep/er/still", "delta", "adam-agentskills")
        w.add_fixture("deep/er/still/and/deeper", "delta", "adam-agentskills")
        doc = w.json()
        self.assertEqual(rows(doc, "adam-agentskills")["delta"]["fixtures"], 2)
        self.assertEqual(rows(doc, "adam-agentskills")["delta"]["status"], "covered")
        self.assertEqual(doc["totals"]["covered"], 5)

    def test_a_fixture_with_a_null_or_blank_skill_is_refused(self):
        for body in ("skill:\nregistry: https://github.com/Adam-S-Daniel/"
                     "adam-agentskills\n",
                     "skill: ~\n", "skill: ''\n", "skill: '   '\n",
                     "skill: [alpha]\n"):
            with self.subTest(body=body):
                w = World(self)
                w.raw_fixture("nullskill", body)
                self.assert_refused(w.run(), "nullskill")
                self.assertIn("'skill:'", w.run().stderr)
        # the key ABSENT is still a non-skill subject, ignored
        w = World(self)
        w.raw_fixture("subject", "subject: guidance\n")
        self.assertEqual(w.run().returncode, 0)

    def test_an_evals_dir_with_no_fixture_is_refused(self):
        w = World(self)
        shutil.rmtree(w.evals)
        w.evals.mkdir()
        self.assert_refused(w.run(), "no fixture.yaml")
        (w.evals / "notes.txt").write_text("not a fixture", encoding="utf-8")
        self.assert_refused(w.run("--check"), "no fixture.yaml")

    def test_a_malformed_non_coverage_file_is_refused(self):
        for bad, needle in (
            ("skips: []\nextra: 1\n", "exactly one key"),
            ("- not a mapping\n", "exactly one key"),
            ("skips:\n  - {registry: cms-platform, skill: cms-gap, "
             "decision: skip, reasn: typo}\n", "exactly the fields"),
            ("skips:\n  - {registry: cms-platform, skill: cms-gap, "
             "decision: skip, reason: ''}\n", "non-blank"),
            ("skips:\n  - {registry: nowhere, skill: x, decision: skip, "
             "reason: r}\n", "not in harness/registries.yml"),
            ("skips:\n  - {registry: cms-platform, skill: cms-gap, "
             "decision: skip, reason: r}\n  - {registry: cms-platform, "
             "skill: cms-gap, decision: skip, reason: r}\n", "second row"),
        ):
            with self.subTest(bad=bad):
                self.assert_refused(World(self).run(raw_non_coverage=bad), needle)


class Problems(unittest.TestCase):
    def kinds(self, doc: dict) -> set:
        return {(p["kind"], p.get("skill")) for p in doc["problems"]}

    def test_a_stale_skip_is_reported_and_fails_check(self):
        w = World(self)
        w.clear_all_gaps()
        w.skip("cms-platform", "renamed-away")
        self.assertEqual(w.json()["problems"],
                         [{"kind": "stale_skip", "registry": "cms-platform",
                           "skill": "renamed-away"}])
        self.assertEqual(w.run("--check").returncode, 1)

    def test_a_skip_for_a_skill_that_also_has_a_fixture_is_reported(self):
        w = World(self)
        w.clear_all_gaps()
        w.skip("adam-agentskills", "alpha")
        self.assertEqual(self.kinds(w.json()), {("skip_but_covered", "alpha")})
        self.assertEqual(w.run("--check").returncode, 1)

    def test_a_fixture_for_a_vanished_skill_is_reported(self):
        w = World(self)
        w.clear_all_gaps()
        w.add_fixture("old", "renamed-away", "cms-platform")
        self.assertEqual(self.kinds(w.json()), {("orphan_fixture", "renamed-away")})
        self.assertEqual(w.run("--check").returncode, 1)



class PrivateNames(unittest.TestCase):
    def test_counts_only_by_default_in_both_formats(self):
        w = World(self)
        for flags in ((), ("--json",), ("--check",), ("--json", "--check")):
            with self.subTest(flags=flags):
                proc = w.run(*flags)
                self.assertIn(proc.returncode, (0, 1))
                self.assertNotIn("zz-private", proc.stdout + proc.stderr)
        doc = w.json()
        reg = next(r for r in doc["registries"] if r["name"] == PRIVATE)
        self.assertEqual((reg["names_withheld"], reg["skills"]), (True, []))
        self.assertEqual(reg["counts"],
                         {"total": 2, "covered": 1, "skipped": 0, "gap": 1})

    def test_names_appear_only_with_the_flag(self):
        w = World(self)
        doc = w.json("--include-private-names")
        self.assertEqual(rows(doc, PRIVATE)[PRIVATE_COVERED]["status"], "covered")
        self.assertEqual(rows(doc, PRIVATE)[PRIVATE_GAP]["status"], "gap")
        self.assertIn(PRIVATE_GAP, w.run("--include-private-names").stdout)

    def test_a_problem_in_the_private_registry_does_not_name_the_skill(self):
        w = World(self)
        w.skip(PRIVATE, "zz-private-renamed", private=True)
        w.add_fixture("old-private", "zz-private-vanished", PRIVATE)
        proc = w.run("--json")
        self.assertNotIn("zz-private-renamed", proc.stdout)
        self.assertNotIn("zz-private-vanished", proc.stdout)
        kinds = sorted(p["kind"] for p in json.loads(proc.stdout)["problems"])
        self.assertEqual(kinds, ["orphan_fixture", "stale_skip"])
        self.assertIn("zz-private-renamed",
                      w.run("--json", "--include-private-names").stdout)

    def test_no_refusal_path_prints_a_private_skill_name(self):
        marker = "zz-private-leak-marker"
        public_url = "https://github.com/Adam-S-Daniel/adam-agentskills"
        row = ("skips:\n  - {registry: %s, skill: %s, decision: skip, "
               "reason: r}\n")

        def duplicate(w):
            w.add_skill(PRIVATE, PRIVATE_COVERED, "plug-q")

        cases = {
            # fixture problems where the registry is unknown or missing
            "fixture, no registry": (lambda w: w.raw_fixture(
                "leaky/a", f"skill: {marker}\n"), "no 'registry:'"),
            "fixture, unknown registry": (lambda w: w.raw_fixture(
                "leaky/b", f"skill: {marker}\nregistry: https://example.com/x/y\n"),
                "unknown registry"),
            "fixture, invalid name": (lambda w: w.raw_fixture(
                "leaky/c", f"skill: '{marker}/..'\nregistry: {public_url}\n"),
                "not a valid skill name"),
            "fixture, broken YAML": (lambda w: w.raw_fixture(
                "leaky/d", f"skill: {marker}\nbad: [unclosed\n"),
                "not valid YAML"),
            "fixture, unknown YAML tag": (lambda w: w.raw_fixture(
                "leaky/e", f"skill: !{marker} x\n"), "not valid YAML"),
            # a private registry's own structural refusals
            "private duplicate": (duplicate, "more than one bundle"),
        }
        for label, (mutate, needle) in cases.items():
            with self.subTest(label):
                w = World(self)
                mutate(w)
                proc = w.run()
                self.assertEqual((proc.returncode, proc.stdout), (2, ""),
                                 proc.stderr)
                self.assertIn(needle, proc.stderr)
                self.assertNotIn(marker, proc.stderr)
                self.assertNotIn(PRIVATE_COVERED, proc.stderr)
        # the operator-held private file, every way it can be refused
        one = f"  - {{registry: {PRIVATE}, skill: {marker}, decision: skip, reason: r}}\n"
        for label, raw, needle in (
            ("duplicate row", "skips:\n" + one * 2, "second row"),
            ("invalid name", row % (PRIVATE, f'"{marker}/.."'),
             "not a valid skill name"),
            ("extra field", f"skips:\n  - {{registry: {PRIVATE}, skill: "
             f"{marker}, decision: skip, reason: r, x: 1}}\n",
             "exactly the fields"),
            ("broken YAML", f"skips: [{marker}: : :\n", "not valid YAML"),
            # PyYAML's own message quotes an unknown tag from the file
            ("unknown YAML tag", f"skips: !{marker} x\n", "not valid YAML"),
            ("public registry row", row % ("cms-platform", marker),
             "private registries only"),
        ):
            with self.subTest(f"private file, {label}"):
                w = World(self)
                proc = w.run(raw_private=raw)
                self.assertEqual((proc.returncode, proc.stdout), (2, ""),
                                 proc.stderr)
                self.assertIn(needle, proc.stderr)
                self.assertNotIn(marker, proc.stderr)
        # and the same row in the PUBLIC file
        w = World(self)
        proc = w.run(raw_non_coverage=row % (PRIVATE, marker))
        self.assertEqual((proc.returncode, proc.stdout), (2, ""))
        self.assertNotIn(marker, proc.stderr)

    def test_the_committed_file_refuses_private_rows(self):
        w = World(self)
        w.skip(PRIVATE, PRIVATE_GAP)  # in the PUBLIC file
        proc = w.run()
        self.assertEqual((proc.returncode, proc.stdout), (2, ""))
        self.assertIn("may not be committed", proc.stderr)
        self.assertNotIn(PRIVATE_GAP, proc.stderr)

    def test_the_operator_held_file_takes_private_rows_only(self):
        w = World(self)
        w.private_skips.append({"registry": "cms-platform", "skill": "cms-gap",
                                "decision": "skip", "reason": "r"})
        proc = w.run()
        self.assertEqual((proc.returncode, proc.stdout), (2, ""))
        self.assertIn("private registries only", proc.stderr)

    def test_a_private_skip_from_the_operator_file_clears_the_gap(self):
        w = World(self)
        w.clear_all_gaps()
        self.assertEqual(w.run("--check").returncode, 0)
        w.private_skips.clear()
        self.assertEqual(w.run("--check").returncode, 1)  # same census, no file


class RepoFiles(unittest.TestCase):
    def test_every_private_looking_registry_is_in_the_allowlist(self):
        private_named = {n for n in REGISTRIES if "private" in n}
        self.assertTrue(private_named)
        self.assertLessEqual(private_named, eval_coverage.PRIVATE_REGISTRIES)
        self.assertLessEqual(eval_coverage.PRIVATE_REGISTRIES, set(REGISTRIES))

    def test_the_committed_non_coverage_file_is_public_safe_and_well_formed(self):
        doc = yaml.safe_load(COMMITTED_NON_COVERAGE.read_text(encoding="utf-8"))
        self.assertEqual(list(doc), ["skips"])
        self.assertTrue(doc["skips"])
        for row in doc["skips"]:
            self.assertEqual(set(row), set(eval_coverage.SKIP_FIELDS))
            self.assertIn(row["registry"], REGISTRIES)
            self.assertNotIn(row["registry"], eval_coverage.PRIVATE_REGISTRIES)
            for field in row:
                self.assertFalse(
                    any(w in field.lower() for w in SCANNER_WORDS), field)
        pairs = [(r["registry"], r["skill"]) for r in doc["skips"]]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_test_canary_is_not_said_to_be_covered_by_the_propagation_arms(self):
        # Nothing under evals/propagation, the workflows or the harness
        # references test-canary; closed issue #17 built the adam-agentskills
        # propagation arms only, and no open issue tracks a test-canary probe.
        # The reason must say that, not claim coverage or a tracker.
        doc = yaml.safe_load(COMMITTED_NON_COVERAGE.read_text(encoding="utf-8"))
        row = next(r for r in doc["skips"] if r["skill"] == "test-canary")
        self.assertEqual(
            row["reason"], "internal canary; carries no guidance; no probe "
            "asserts its delivery (not built, untracked; closed issue #17 "
            "built other propagation arms)")

    def test_the_committed_evals_tree_and_skip_file_load_through_the_script(self):
        w = World(self)
        non_coverage = w.root / "committed.yml"
        shutil.copy(COMMITTED_NON_COVERAGE, non_coverage)
        argv = [sys.executable, str(SCRIPT), "--json",
                "--evals-dir", str(REPO_ROOT / "evals"),
                "--non-coverage", str(non_coverage)]
        for name, path in w.registry_dirs.items():
            argv += ["--registry", f"{name}={path}"]
        proc = subprocess.run(
            argv, capture_output=True, text=True, cwd=w.root, timeout=120,
            env={"PATH": os.environ.get("PATH", ""), "HOME": str(w.root)})
        # synthetic registries lack the real skills, so problems are expected;
        # what is asserted is that nothing was REFUSED.
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["schema"], 1)

    def test_the_script_imports_no_network_or_subprocess_module(self):
        tree = ast_imports(SCRIPT)
        self.assertFalse(tree & {"socket", "urllib", "http", "requests",
                                 "subprocess", "shutil"}, tree)


def ast_imports(path: Path) -> set[str]:
    import ast
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


if __name__ == "__main__":
    unittest.main()
