"""Hermetic front-matter scorer and tool-page fixture coverage for issue #94."""

from __future__ import annotations

import builtins
from contextlib import contextmanager
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))
from scorers import objective


FIELDS = "slug: unit-converter\nembed_src: /assets/tools/unit-converter/\ntitle: Converter\ndescription: Useful\n"
CONSTRAINTS = {
    "equals": {"slug": "unit-converter", "embed_src": "/assets/tools/unit-converter/"},
    "nonempty_strings": ["title", "description"],
}


def page(fields=FIELDS, body="Body text"):
    return "---\n" + fields + "---\n" + body


ACCEPT = {
    "ordinary": page(),
    "crlf": page().replace("\n", "\r\n"),
    "bom": "\ufeff" + page(),
    "quoted_reordered": page('description: "Useful"\ntitle: \'Converter\'\nembed_src: "/assets/tools/unit-converter/"\nslug: "unit-converter"\n'),
    "folded": page(FIELDS.replace("description: Useful", "description: >\n  Useful\n  converter")),
    "literal": page(FIELDS.replace("description: Useful", "description: |\n  Useful\n  converter")),
    "extra_keys": page(FIELDS + "extra: [1, true, null]\n"),
    "benign_alias": page(FIELDS.replace("title: Converter\ndescription: Useful", "title: &label Converter\ndescription: *label")),
    "merge_override": page("defaults: &defaults {title: Default, description: Useful}\n<<: *defaults\nslug: unit-converter\nembed_src: /assets/tools/unit-converter/\ntitle: Converter\n"),
    "close_at_eof": page(body="").rstrip("\n"),
    "arbitrary_body": page(body="---\nslug: wrong\n: [malformed YAML\n\ufeff"),
    "huge_invalid_utf8_body": page(body="").encode() + b"\xff" * 100000,
}

REJECT = {
    "empty": "",
    "body_only": FIELDS,
    "blank_before_open": "\n" + page(),
    "text_before_open": "intro\n" + page(),
    "double_bom": "\ufeff\ufeff" + page(),
    "open_indented": page().replace("---", " ---", 1),
    "open_suffix": page().replace("---", "--- # comment", 1),
    "open_short": page().replace("---", "--", 1),
    "open_long": page().replace("---", "----", 1),
    "open_at_eof": "---",
    "cr_only": page().replace("\n", "\r"),
    "missing_close": "---\n" + FIELDS,
    "close_indented": "---\n" + FIELDS + " ---\n",
    "close_suffix": "---\n" + FIELDS + "--- # comment\n",
    "close_yaml_end": "---\n" + FIELDS + "...\n",
    "close_long": "---\n" + FIELDS + "----\n",
    "malformed_yaml": page(FIELDS + "extra: [unterminated\n"),
    "unsafe_tag": page(FIELDS + "extra: !!python/object:example.com {}\n"),
    "nonmapping_list": page("- slug\n- title\n"),
    "nonmapping_scalar": page("hello\n"),
    "nonmapping_null": page(""),
    "missing_slug": page(FIELDS.replace("slug: unit-converter\n", "")),
    "body_spoof": page(FIELDS.replace("slug: unit-converter\n", ""), body="slug: unit-converter\n"),
    "wrong_slug": page(FIELDS.replace("slug: unit-converter", "slug: wrong")),
    "wrong_slug_type": page(FIELDS.replace("slug: unit-converter", "slug: 123")),
    "missing_embed_src": page(FIELDS.replace("embed_src: /assets/tools/unit-converter/\n", "")),
    "duplicate_slug": page(FIELDS + "slug: unit-converter\n"),
    "duplicate_extra": page(FIELDS + "extra: one\nextra: two\n"),
    "duplicate_quoted": page(FIELDS + "'slug': unit-converter\n"),
    "duplicate_numeric": page(FIELDS + "1: one\n0x1: two\n"),
    "duplicate_bool_integer": page(FIELDS + "true: one\n1: two\n"),
    "duplicate_merge": page(FIELDS + "<<: {extra: one}\n<<: {other: two}\n"),
    "unhashable_key": page(FIELDS + "? [a, b]\n: value\n"),
    "recursive_anchor": page(FIELDS + "extra: &recursive [*recursive]\n"),
    "alias_bomb": page(FIELDS + "a: &a [a, a, a, a, a, a, a, a, a, a]\n" + "".join(f"n{i}: &n{i} [" + ", ".join(["*a" if i == 0 else f"*n{i-1}"] * 10) + "]\n" for i in range(5))),
    "merge_bomb": page(FIELDS + "a: &a {extra: value}\n" + "".join(f"n{i}: &n{i} {{<<: [" + ", ".join(["*a" if i == 0 else f"*n{i-1}"] * 10) + "]}\n" for i in range(5))),
    "too_deep": page(FIELDS + "extra: " + "[" * 65 + "value" + "]" * 65 + "\n"),
    "too_many_nodes": page(FIELDS + "extra: [" + ",".join(["value"] * 4097) + "]\n"),
    "oversize_header": page(FIELDS + "#" + "x" * 65536 + "\n"),
    "invalid_utf8_header": b"---\n" + FIELDS.encode() + b"extra: \xff\n---\n",
}
for field in ("title", "description"):
    for kind, value in (("missing", None), ("empty", '""'), ("whitespace", '"  \\t "'),
                        ("number", "42"), ("bool", "true"), ("null", "null"),
                        ("list", "[Useful]"), ("mapping", "{value: Useful}")):
        old = f"{field}: " + ("Converter" if field == "title" else "Useful") + "\n"
        REJECT[f"{field}_{kind}"] = page(FIELDS.replace(old, "" if value is None else f"{field}: {value}\n"))


class FrontMatterHasTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="front-matter-94-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.ws = self.root / "workspace"
        self.ws.mkdir()
        self.write("page.md", page())

    def write(self, path, text):
        target = self.ws / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text if isinstance(text, bytes) else text.encode())

    def check(self, paths=None, **constraints):
        return objective.front_matter_has(str(self.ws), ["page.md"] if paths is None else paths,
                                          **(constraints or CONSTRAINTS))

    def test_registered_and_constraint_routing(self):
        fixture = {"objective_checks": [{"id": "front-matter", "type": "front_matter_has",
                                         "paths": ["page.md"], **CONSTRAINTS}]}
        self.assertIs(objective.CHECKS.get("front_matter_has"), objective.front_matter_has)
        self.assertEqual(objective.run_checks(fixture, str(self.ws), str(self.ws))[0]["passed"], True)

    def test_unknown_constraint_raises(self):
        fixture = {"objective_checks": [{"id": "front-matter", "type": "front_matter_has",
                                         "paths": ["page.md"], "equal": {"slug": "unit-converter"}}]}
        with self.assertRaises(ValueError):
            objective.run_checks(fixture, str(self.ws), str(self.ws))

    def test_all_files_must_pass(self):
        self.write("second.md", page())
        self.assertTrue(self.check(["page.md", "second.md"])[0])
        self.write("second.md", page(FIELDS.replace("slug: unit-converter", "slug: wrong")))
        self.assertFalse(self.check(["page.md", "second.md"])[0])

    def test_internal_symlink_is_allowed(self):
        (self.ws / "link.md").symlink_to("page.md")
        self.assertTrue(self.check(["link.md"])[0])

    def test_reject_existing_absolute_path(self):
        self.assertFalse(self.check([str(self.ws / "page.md")])[0])

    def test_reject_existing_glob_named_file(self):
        self.write("*.md", page())
        self.assertFalse(self.check(["*.md"])[0])

    def test_symlink_escape_rejected(self):
        (self.root / "outside.md").write_text(page())
        (self.ws / "link.md").symlink_to(self.root / "outside.md")
        self.assertFalse(self.check(["link.md"])[0])

    def test_parent_symlink_escape_rejected(self):
        (self.root / "outside").mkdir()
        (self.root / "outside/page.md").write_text(page())
        (self.ws / "link").symlink_to(self.root / "outside", target_is_directory=True)
        self.assertFalse(self.check(["link/page.md"])[0])

    def test_unreadable_fails_without_content(self):
        with mock.patch.object(builtins, "open", side_effect=PermissionError("private content")):
            passed, detail = self.check()
        self.assertFalse(passed)
        self.assertNotIn("private content", detail)

    def test_parse_error_does_not_expose_content(self):
        self.write("page.md", page("private-content-marker: [\n"))
        passed, detail = self.check()
        self.assertFalse(passed)
        self.assertNotIn("private-content-marker", detail)

    def test_exact_types_recursively(self):
        self.write("page.md", page("value: {items: [1, {flag: true}]}\n"))
        self.assertTrue(self.check(equals={"value": {"items": [1, {"flag": True}]}})[0])
        self.assertFalse(self.check(equals={"value": {"items": [True, {"flag": True}]}})[0])
        self.assertFalse(self.check(equals={"value": {"items": [1, {"flag": 1}]}})[0])

    def test_boolean_is_not_integer(self):
        self.write("page.md", page("value: true\n"))
        self.assertFalse(self.check(equals={"value": 1})[0])

    def test_nested_mapping_key_types(self):
        self.write("page.md", page("value: {true: yes}\n"))
        self.assertFalse(self.check(equals={"value": {1: True}})[0])

    def test_yaml_set_types(self):
        self.write("page.md", page("value: !!set {true: null}\n"))
        self.assertTrue(self.check(equals={"value": {True}})[0])
        self.assertFalse(self.check(equals={"value": {1}})[0])

    def test_constraints_are_optional(self):
        self.write("page.md", page("extra: value\n"))
        self.assertTrue(objective.front_matter_has(str(self.ws), ["page.md"])[0])

    def test_mapping_node_that_constructs_to_set_fails(self):
        self.write("page.md", page("!!set {title: null}\n"))
        self.assertFalse(objective.front_matter_has(str(self.ws), ["page.md"])[0])

    def test_root_ordered_map_fails(self):
        self.write("page.md", page("!!omap [{title: Converter}]\n"))
        self.assertFalse(objective.front_matter_has(str(self.ws), ["page.md"])[0])

    def test_header_size_boundary(self):
        fields = FIELDS + "#" + "x" * (65536 - len(FIELDS.encode()) - 2) + "\n"
        self.write("page.md", page(fields))
        self.assertTrue(self.check()[0])

    def test_nested_duplicates_follow_safe_load(self):
        self.write("page.md", page(FIELDS + "extra: {name: first, name: last}\n"))
        self.assertTrue(self.check()[0])


def content_test(content, expected):
    def test(self):
        self.write("page.md", content)
        passed, detail = self.check()
        self.assertEqual(passed, expected, detail)
    return test


for name, content in ACCEPT.items():
    setattr(FrontMatterHasTests, "test_accept_" + name, content_test(content, True))
for name, content in REJECT.items():
    setattr(FrontMatterHasTests, "test_reject_" + name, content_test(content, False))


def invalid_path_test(paths):
    def test(self):
        self.assertFalse(self.check(paths)[0])
    return test


for name, paths in {
    "empty_paths": [], "absolute": ["/page.md"], "parent": ["../outside.md"],
    "normalized_parent": ["sub/../page.md"], "glob": ["*.md"],
    "missing": ["missing.md"], "directory": ["."], "invalid_path_type": [1],
    "paths_string": "page.md", "nul": ["bad\x00.md"],
}.items():
    setattr(FrontMatterHasTests, "test_reject_path_" + name, invalid_path_test(paths))


def invalid_spec_test(constraints):
    def test(self):
        self.assertFalse(objective.front_matter_has(str(self.ws), ["page.md"], **constraints)[0])
    return test


for name, constraints in {
    "equals_list": {"equals": []}, "equals_string": {"equals": "slug"},
    "equals_null": {"equals": None},
    "equals_numeric_key": {"equals": {1: "value"}},
    "nonempty_string": {"nonempty_strings": "title"},
    "nonempty_mapping": {"nonempty_strings": {"title": True}},
    "nonempty_numeric": {"nonempty_strings": [1]},
    "nonempty_null": {"nonempty_strings": None},
}.items():
    setattr(FrontMatterHasTests, "test_reject_spec_" + name, invalid_spec_test(constraints))


FIXTURE_DIR = Path(__file__).resolve().parents[2] / "evals" / "embeddable-tool-pages"
FIXTURE_SEED = FIXTURE_DIR / "seed"
FIXTURE_IDS = ("asset-copy", "tool-front-matter", "source-unchanged",
               "existing-tool-unchanged", "site-wiring-unchanged")
SOURCE_APP = "seed/new-tool/index.html"
PUBLISHED_APP = "assets/tools/unit-converter/index.html"
TOOL_ENTRY = "_tools/unit-converter.md"
EXISTING_PATHS = ("assets/tools/existing/index.html", "_data/tool_sources/existing.yml",
                  "_tools/existing.md")
WIRING_PATHS = ("_config.yml", "_layouts/tool.html", "_layouts/default.html",
                "_includes/header.html", "tools/index.html", "admin/collections.site.yml")


def tool_fixture():
    return yaml.safe_load((FIXTURE_DIR / "fixture.yaml").read_text())


@contextmanager
def tool_workspace(good=False):
    root = Path(tempfile.mkdtemp(prefix="tool-fixture-94-"))
    owned_root = root.resolve()
    workspace = root / "workspace"
    try:
        # Copy fixture inputs only: no repository, remote, or credentials.
        shutil.copytree(FIXTURE_SEED, workspace)
        if good:
            target = workspace / PUBLISHED_APP
            target.parent.mkdir(parents=True)
            shutil.copyfile(workspace / SOURCE_APP, target)
            (workspace / TOOL_ENTRY).write_text(page())
            post = workspace / "_posts/2026-01-01-example.md"
            post.write_text(post.read_text().replace(
                "\n## Working with estimates", "\n<!-- html-embed:start -->\n"
                '<div class="post-embed">\n'
                '<iframe src="/assets/tools/unit-converter/" title="Length Converter" '
                'loading="lazy" style="width:100%; height:80vh; border:0;"></iframe>\n'
                '<p><a href="/tools/unit-converter/">Open the full-page version</a></p>\n'
                "</div>\n<!-- html-embed:end -->\n\n## Working with estimates"))
        yield root, workspace
    finally:
        assert workspace.resolve().is_relative_to(owned_root)
        if workspace.exists():
            shutil.rmtree(workspace)
        assert root.resolve() == owned_root and root.resolve().is_relative_to(owned_root)
        root.rmdir()


def tool_scores(workspace):
    return {row["id"]: row["passed"] for row in objective.run_checks(
        tool_fixture(), str(workspace), str(FIXTURE_SEED))}


class TestIssue94Fixture(unittest.TestCase):
    def assert_only_failed(self, workspace, *failed):
        self.assertEqual(tool_scores(workspace),
                         {key: key not in failed for key in FIXTURE_IDS})

    def test_fixture_contract_and_source_digest(self):
        fixture = tool_fixture()
        self.assertEqual(fixture["skill"], "embeddable-tool-pages")
        self.assertEqual(fixture["registry"], "https://github.com/Adam-S-Daniel/adamdaniel.ai")
        self.assertEqual(fixture["prompt"].strip(), "Publish seed/new-tool as a Tools page at "
                         "/tools/unit-converter/ and embed it in the post "
                         "_posts/2026-01-01-example.md below the intro.")
        self.assertEqual([c["id"] for c in fixture["objective_checks"]], list(FIXTURE_IDS))
        self.assertEqual([c["type"] for c in fixture["objective_checks"]],
                         ["file_digests_match", "front_matter_has"] + ["files_unchanged"] * 3)
        self.assertEqual(fixture["objective_checks"][0]["sha256"],
                         hashlib.sha256((FIXTURE_SEED / SOURCE_APP).read_bytes()).hexdigest())
        self.assertEqual(fixture["judge"]["weights"],
                         {"correctness": .5, "restraint": .2, "explanation": .3})
        self.assertNotIn("model", fixture)
        self.assertNotIn("model", fixture["judge"])
        for path in FIXTURE_SEED.rglob("*"):
            if path.is_file():
                self.assertNotIn("unit-converter", path.read_text())
                self.assertNotIn("html-embed:", path.read_text())
        self.assertFalse((FIXTURE_SEED / SOURCE_APP).read_text().startswith("---"))

    def test_pristine_fails_behavior_and_passes_restraint(self):
        with tool_workspace() as (_root, workspace):
            self.assert_only_failed(workspace, "asset-copy", "tool-front-matter")

    def test_known_good_passes_every_check(self):
        with tool_workspace(good=True) as (_root, workspace):
            self.assert_only_failed(workspace)

    def test_plausible_body_only_front_matter_fails(self):
        with tool_workspace(good=True) as (_root, workspace):
            (workspace / TOOL_ENTRY).write_text("# Length Converter\n\n" + FIELDS)
            self.assert_only_failed(workspace, "tool-front-matter")

    def test_each_check_has_an_isolated_mutation_and_restoration(self):
        mutations = {"asset-copy": PUBLISHED_APP, "tool-front-matter": TOOL_ENTRY,
                     "source-unchanged": SOURCE_APP,
                     "existing-tool-unchanged": EXISTING_PATHS[0],
                     "site-wiring-unchanged": WIRING_PATHS[0]}
        for check_id, path in mutations.items():
            with self.subTest(check=check_id), tool_workspace(good=True) as (_root, workspace):
                self.assert_only_failed(workspace)
                target = workspace / path
                original = target.read_bytes()
                if check_id == "tool-front-matter":
                    target.write_text(page(FIELDS.replace("slug: unit-converter", "slug: wrong")))
                else:
                    target.write_bytes(original + b"\nchanged\n")
                self.assert_only_failed(workspace, check_id)
                target.write_bytes(original)
                self.assert_only_failed(workspace)

    def test_all_protected_paths_detect_edits_deletions_and_additions(self):
        owners = {"source-unchanged": (SOURCE_APP,),
                  "existing-tool-unchanged": EXISTING_PATHS,
                  "site-wiring-unchanged": WIRING_PATHS}
        for owner, paths in owners.items():
            for path in paths:
                for mutation in ("edit", "delete"):
                    with self.subTest(path=path, mutation=mutation), tool_workspace(good=True) as (root, workspace):
                        target = workspace / path
                        original = target.read_bytes()
                        if mutation == "delete":
                            assert target.resolve().is_relative_to(root.resolve())
                            target.unlink()
                        else:
                            target.write_bytes(original + b"\nchanged\n")
                        self.assert_only_failed(workspace, owner)
                        target.write_bytes(original)
                        self.assert_only_failed(workspace)
        for path, owner in (("_data/tool_sources/extra.yml", "existing-tool-unchanged"),
                            ("_data/tool_sources/extra.json", "existing-tool-unchanged"),
                            ("_layouts/extra.html", "site-wiring-unchanged"),
                            ("_includes/extra.html", "site-wiring-unchanged")):
            with self.subTest(added=path), tool_workspace(good=True) as (_root, workspace):
                (workspace / path).write_text("unexpected addition\n")
                self.assert_only_failed(workspace, owner)

    def test_each_required_front_matter_field_is_enforced(self):
        for field, value in (("slug", "unit-converter"), ("embed_src", "/assets/tools/unit-converter/"),
                             ("title", "Converter"), ("description", "Useful")):
            for replacement in ("", f'{field}: ""\n', f"{field}: true\n"):
                with self.subTest(field=field, replacement=replacement), tool_workspace(good=True) as (_root, workspace):
                    (workspace / TOOL_ENTRY).write_text(page(FIELDS.replace(f"{field}: {value}\n", replacement)))
                    self.assert_only_failed(workspace, "tool-front-matter")
        for field, wrong in (("slug", "wrong"), ("embed_src", "/tools/unit-converter/")):
            with self.subTest(wrong=field), tool_workspace(good=True) as (_root, workspace):
                values = dict(line.split(": ", 1) for line in FIELDS.splitlines())
                values[field] = wrong
                (workspace / TOOL_ENTRY).write_text(page("".join(f"{k}: {v}\n" for k, v in values.items())))
                self.assert_only_failed(workspace, "tool-front-matter")

    def test_front_matter_variants_accept_structure_and_reject_spoofs(self):
        variants = {
            "quoted_reordered": (ACCEPT["quoted_reordered"], True),
            "multiline": (ACCEPT["folded"], True),
            "different_title": (page(FIELDS.replace("title: Converter", "title: Distance Helper")), True),
            "body_only": (REJECT["body_only"], False),
            "malformed": (REJECT["malformed_yaml"], False),
            "duplicate": (REJECT["duplicate_slug"], False),
            "hedged_body": (page(FIELDS.replace("embed_src: /assets/tools/unit-converter/",
                                                "embed_src: /tools/unit-converter/"),
                                 body="Maybe it works; never use /assets/tools/unit-converter/ here."), False),
        }
        for name, (content, accepted) in variants.items():
            with self.subTest(variant=name), tool_workspace(good=True) as (_root, workspace):
                (workspace / TOOL_ENTRY).write_text(content)
                self.assert_only_failed(workspace, *(() if accepted else ("tool-front-matter",)))

    def test_editing_source_and_copy_cannot_redefine_expected_bytes(self):
        with tool_workspace(good=True) as (_root, workspace):
            modified = (workspace / SOURCE_APP).read_bytes() + b"\n<!-- altered app -->\n"
            (workspace / SOURCE_APP).write_bytes(modified)
            (workspace / PUBLISHED_APP).write_bytes(modified)
            self.assert_only_failed(workspace, "asset-copy", "source-unchanged")


if __name__ == "__main__":
    unittest.main()
