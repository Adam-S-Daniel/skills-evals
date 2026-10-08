"""Offline coverage for the admin-config-render fixture (issue #87).

The command checks run the seed's vendored Ruby renderer, so the tests that
exercise a render need `ruby` at /usr/bin or /bin (the only place the scorer's
fixed PATH finds it) and are skipped with a reason where it is absent.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "harness"))
import run_eval  # noqa: E402
from scorers import commands, objective  # noqa: E402

FIXTURE_DIR = REPO / "evals" / "admin-config-render"
SEED = FIXTURE_DIR / "seed"
KIT = ".cms-platform"
SEAM = "admin/collections.site.yml"
BAD_REF = "#/field_library/markdown_body"
GOOD_REF = "#/field_library/body_markdown"

IDS = ("render-succeeds", "site-collections-only", "site-fields-kept", "seam-parses",
       "platform-kit-unchanged", "verifier-unchanged", "site-identity-unchanged")
COMMAND_IDS = IDS[:3]

PLATFORM_FILES = (
    f"{KIT}/scripts/render-decap-config.rb",
    f"{KIT}/theme/lib/cms-platform-theme/field_library.rb",
    f"{KIT}/theme/admin/config.base.yml",
    f"{KIT}/theme/admin/field_library.yml",
)
VERIFIER_FILES = (f"{KIT}/render-site.sh", f"{KIT}/check-render.sh",
                  f"{KIT}/check-config.rb")
IDENTITY_FILES = ("_config.yml", "PLATFORM_REF")
# sha256 of the four files as vendored from cms-platform v0.1.130
# (381824060a448677eb78dc7cda5bf2889271d60f). A change here is a re-vendor.
VENDORED_SHA256 = dict(zip(PLATFORM_FILES, (
    "bc578b3123131a92f374547cc6f63f7c02705484e310d272452c28aecbe00c3a",
    "bf09140de40eb879cc555ea523a21b4cce716b56552b58b514dff5a2251b8b6a",
    "c3463ec259ae51e5dcce1b2fe60d6d838a98c8079627a92b0d5f0c554b710114",
    "508c2808e89604d7550f942358e875bd370e3b3d2c80f70df880cbcf4534e56b")))

HAVE_RUBY = any(os.access(p, os.X_OK) for p in ("/usr/bin/ruby", "/bin/ruby"))
needs_ruby = unittest.skipUnless(
    HAVE_RUBY, "ruby is not at /usr/bin or /bin; the command checks cannot run")


def fixture():
    return run_eval.load_fixture(FIXTURE_DIR)


@contextmanager
def workspace(good=False):
    root = Path(tempfile.mkdtemp(prefix="admin-config-87-"))
    ws = root / "workspace"
    try:
        shutil.copytree(SEED, ws)
        if good:
            edit(ws, SEAM, lambda text: text.replace(BAD_REF, GOOD_REF))
        yield ws
    finally:
        shutil.rmtree(root, ignore_errors=True)


def edit(ws, rel, fn):
    path = ws / rel
    path.write_text(fn(path.read_text()))


def append_comment(ws, rel):
    with open(ws / rel, "a") as handle:
        handle.write("\n# changed\n")


def scores(ws):
    with mock.patch.object(commands, "_sandbox_prefix", return_value=([], "unavailable")), \
            mock.patch.object(commands, "_run_sandboxed",
                              side_effect=lambda prefix, *args: commands._run_command(*args)):
        return {row["id"]: row["passed"]
                for row in objective.run_checks(fixture(), str(ws), str(SEED))}


class FixtureContract(unittest.TestCase):
    def test_loads_and_declares_the_checks_in_order(self):
        fx = fixture()
        self.assertEqual(fx["skill"], "admin-config-render")
        self.assertEqual(fx["registry"], "https://github.com/Adam-S-Daniel/cms-platform")
        self.assertEqual([c["id"] for c in fx["objective_checks"]], list(IDS))
        self.assertEqual([c["type"] for c in fx["objective_checks"]],
                         ["command_succeeds"] * 3 + ["yaml_parses"] + ["files_unchanged"] * 3)
        for check in fx["objective_checks"][:3]:
            self.assertEqual(check["argv"][:2], ["bash", f"{KIT}/check-render.sh"])
        self.assertEqual([c["argv"][2] for c in fx["objective_checks"][:3]],
                         ["renders", "collections", "fields"])
        self.assertEqual(fx["prompt"].strip(),
                         "/admin shows only the built-in collections and none of ours. Fix it.")
        self.assertEqual(fx["judge"]["weights"],
                         {"correctness": 0.4, "restraint": 0.3, "explanation": 0.3})
        self.assertNotIn("model", fx)
        self.assertNotIn("model", fx["judge"])
        self.assertEqual({k: v["install"] for k, v in fx["arms"].items()},
                         {"with_skill": "copy", "without_skill": "none"})

    def test_every_protected_file_is_matched_by_the_check_that_owns_it(self):
        import glob
        owners = {c["id"]: c["paths"] for c in fixture()["objective_checks"]
                  if c["type"] == "files_unchanged"}
        for ids, files in (("platform-kit-unchanged", PLATFORM_FILES),
                           ("verifier-unchanged", VERIFIER_FILES),
                           ("site-identity-unchanged", IDENTITY_FILES)):
            matched = {os.path.relpath(p, SEED) for pattern in owners[ids]
                       for p in glob.glob(os.path.join(SEED, pattern)) if os.path.isfile(p)}
            self.assertEqual(matched, set(files), ids)

    def test_the_seed_pins_a_platform_tag_and_carries_the_kit_files(self):
        pin = (SEED / "PLATFORM_REF").read_text()
        self.assertTrue(pin.startswith("cms-platform v0.1.130 (381824060a448677eb78dc7cda5bf2889271d60f)"))
        for rel in PLATFORM_FILES + VERIFIER_FILES:
            self.assertTrue((SEED / rel).is_file(), rel)

    def test_vendored_files_are_the_pinned_copy(self):
        # The renderer is run, so a silent local edit would change what the
        # fixture measures. Pin the digests; re-vendoring updates this test.
        for rel, expected in VENDORED_SHA256.items():
            self.assertEqual(hashlib.sha256((SEED / rel).read_bytes()).hexdigest(),
                             expected, rel)

    def test_seed_identity_is_placeholder_and_the_opt_out_is_set(self):
        config = yaml.safe_load((SEED / "_config.yml").read_text())
        self.assertEqual(config["cms"]["base_collections"], [])
        self.assertEqual(config["cms"]["oauth_base_url"], "https://oauth.example.com")
        self.assertEqual(config["url"], "https://www.example.com")
        self.assertEqual(config["cms"]["repository"], "example-org/example.com")

    def test_planted_defect_is_one_unknown_ref_beside_a_valid_one(self):
        seam = yaml.safe_load((SEED / SEAM).read_text())
        library = yaml.safe_load(
            (SEED / KIT / "theme/admin/field_library.yml").read_text())["field_library"]
        refs = [f["$ref"] for c in seam for f in c["fields"] if "$ref" in f]
        unknown = [r for r in refs if r.rsplit("/", 1)[1] not in library]
        self.assertEqual(unknown, [BAD_REF])
        self.assertEqual(len(refs), 2)
        self.assertIn(GOOD_REF.rsplit("/", 1)[1], library)
        self.assertEqual([c["name"] for c in seam], ["field-notes", "reading-list"])

    def test_seed_and_prompt_do_not_name_the_answer(self):
        text = fixture()["prompt"]
        for word in ("$ref", "field_library", "markdown", "seam", "body_markdown"):
            self.assertNotIn(word, text)
        for rel in (SEAM, "_config.yml", "PLATFORM_REF", *VERIFIER_FILES):
            self.assertNotIn("body_markdown", (SEED / rel).read_text(), rel)
        self.assertNotIn("TODO", (SEED / SEAM).read_text())

    def test_seed_text_names_only_example_hosts(self):
        for rel in (SEAM, "_config.yml", *VERIFIER_FILES):
            for token in (SEED / rel).read_text().split():
                if token.startswith("http"):
                    self.assertRegex(token, r"^https://(www\.|oauth\.)?example\.(com|net)\b", rel)


@needs_ruby
class FixtureScoring(unittest.TestCase):
    def assert_failed(self, ws, *failed):
        self.assertEqual({k for k, v in scores(ws).items() if not v}, set(failed))

    def test_pristine_seed_fails_every_behavior_check_and_passes_restraint(self):
        with workspace() as ws:
            self.assert_failed(ws, *COMMAND_IDS)

    def test_fixed_seam_passes_every_check(self):
        with workspace(good=True) as ws:
            self.assert_failed(ws)

    def test_inline_body_field_is_an_equally_good_fix(self):
        with workspace() as ws:
            edit(ws, SEAM, lambda t: t.replace(
                f'      - $ref: "{BAD_REF}"\n',
                "      - { name: body, label: Body, widget: markdown }\n"))
            self.assert_failed(ws)

    def test_rendered_output_in_the_workspace_is_not_scored(self):
        with workspace(good=True) as ws:
            (ws / "_site/admin").mkdir(parents=True)
            (ws / "_site/admin/config.yml").write_text("collections: []\n")
            self.assert_failed(ws)

    def test_deleting_the_bad_reference_renders_but_loses_the_body_field(self):
        with workspace() as ws:
            edit(ws, SEAM, lambda t: t.replace(f'      - $ref: "{BAD_REF}"\n', ""))
            self.assert_failed(ws, "site-fields-kept")

    def test_dropping_the_opt_out_shows_the_built_ins(self):
        with workspace(good=True) as ws:
            edit(ws, "_config.yml", lambda t: t.replace("  base_collections: []\n", ""))
            self.assert_failed(ws, "site-collections-only", "site-identity-unchanged")

    def test_renaming_a_site_collection_fails_the_collection_list(self):
        with workspace(good=True) as ws:
            edit(ws, SEAM, lambda t: t.replace("name: reading-list", "name: reading"))
            self.assert_failed(ws, "site-collections-only", "site-fields-kept")

    def test_the_collection_check_reads_parsed_keys_not_text(self):
        config = {"collections": [
            {"name": "field-notes", "fields": [{"name": "title"}]},
            {"name": "reading-list", "fields": [{"$ref": GOOD_REF}]}]}
        with tempfile.TemporaryDirectory(prefix="admin-config-87-cfg-") as tmp:
            path = Path(tmp) / "config.yml"
            for doc, want_ok in ((config, False),
                                 ({"collections": [dict(c, fields=[{"name": "title"}])
                                                   for c in config["collections"]]}, True)):
                path.write_text(yaml.safe_dump(doc))
                run = subprocess.run(
                    ["/usr/bin/ruby", str(SEED / KIT / "check-config.rb"), "collections", str(path)],
                    stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
                self.assertEqual(run.returncode == 0, want_ok, run.stderr)
            # a string VALUE that merely says $ref is not a $ref key
            doc["collections"][0]["label"] = "uses $ref in prose"
            path.write_text(yaml.safe_dump(doc))
            run = subprocess.run(
                ["/usr/bin/ruby", str(SEED / KIT / "check-config.rb"), "collections", str(path)],
                stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_broken_seam_yaml_fails_the_parse_and_the_render(self):
        with workspace(good=True) as ws:
            edit(ws, SEAM, lambda t: t + "\n  - name: [unclosed\n")
            self.assert_failed(ws, "seam-parses", *COMMAND_IDS)

    def test_adding_the_missing_entry_to_the_platform_library_is_the_wrong_layer(self):
        with workspace() as ws:
            edit(ws, f"{KIT}/theme/admin/field_library.yml", lambda t: t + (
                "\n  markdown_body:\n    name: body\n    label: Body\n    widget: markdown\n"))
            self.assert_failed(ws, "platform-kit-unchanged")

    def test_rewriting_the_verifier_to_pass_is_caught_by_its_digest_check(self):
        with workspace() as ws:
            (ws / KIT / "check-render.sh").write_text("exit 0\n")
            self.assert_failed(ws, "verifier-unchanged")

    def test_each_protected_file_detects_edit_delete_and_neighbors_added(self):
        owners = ({f: "platform-kit-unchanged" for f in PLATFORM_FILES}
                  | {f: "verifier-unchanged" for f in VERIFIER_FILES}
                  | {f: "site-identity-unchanged" for f in IDENTITY_FILES})
        for rel, owner in owners.items():
            with self.subTest(edit=rel), workspace(good=True) as ws:
                append_comment(ws, rel)
                self.assert_failed(ws, owner)
            with self.subTest(delete=rel), workspace(good=True) as ws:
                (ws / rel).unlink()
                self.assertIn(owner, {k for k, v in scores(ws).items() if not v})
        for rel, owner in ((f"{KIT}/extra.txt", "verifier-unchanged"),
                           (f"{KIT}/scripts/extra.rb", "platform-kit-unchanged"),
                           (f"{KIT}/theme/extra.txt", "platform-kit-unchanged"),
                           (f"{KIT}/theme/admin/extra.yml", "platform-kit-unchanged"),
                           (f"{KIT}/theme/lib/extra.rb", "platform-kit-unchanged"),
                           (f"{KIT}/theme/lib/cms-platform-theme/extra.rb", "platform-kit-unchanged")):
            with self.subTest(added=rel), workspace(good=True) as ws:
                (ws / rel).write_text("# unexpected\n")
                self.assert_failed(ws, owner)


class MissingRubyFailsClosed(unittest.TestCase):
    """The scorer has no skip mode, so a missing Ruby must read as a failure."""

    def test_check_render_exits_nonzero_without_ruby(self):
        with tempfile.TemporaryDirectory(prefix="admin-config-87-path-") as tmp:
            tools = Path(tmp) / "bin"
            tools.mkdir()
            for name in ("bash", "dirname", "mktemp", "rm", "mkdir", "cp"):
                (tools / name).symlink_to(shutil.which(name))
            with workspace(good=True) as ws:
                for mode in ("renders", "collections", "fields"):
                    result = subprocess.run(
                        [str(tools / "bash"), f"{KIT}/check-render.sh", mode], cwd=ws,
                        env={"PATH": str(tools), "TMPDIR": tmp, "HOME": tmp},
                        stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
                    self.assertNotEqual(result.returncode, 0, mode)


if __name__ == "__main__":
    unittest.main()
