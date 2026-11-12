#!/usr/bin/env python3
"""Cloud sessions' git hook runs (agent-checks pre-commit and pre-push), the
third surface `cloud` beside `local` and `ci`.

A cloud session's Stop hook uploads one record per run to the private branch
at `events/<YYYY-MM>/cloud-hooks/<16 hex>.jsonl` (the S3 route is covered in
test_issue_usage_sink.py). This file covers the receiving side: the census
reader and its rows and source, the schema helpers and the carry-forward, and
the public explorer's `hooks.totals.cloud` and `hooks.cloud_from`, which exist
only when the usage file says cloud hook records were read.

Every store is synthetic under a mkdtemp; `now` is always passed in.
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))
import explorer_public as pub  # noqa: E402
import model_usage_census as census  # noqa: E402
import skill_usage  # noqa: E402
import test_issue_skill_usage as su  # noqa: E402

NOW = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)   # ISO week 2026-W36
SID = "0123456789abcdef"
SID2 = "fedcba9876543210"
PUBLIC = frozenset({"example/open"})
EMPTY_TALLY = {"invocations": {}, "sessions": {}, "sessions_scanned": 0}


def hook(**overrides) -> dict:
    record = {"v": 1, "id": "0123456789abcdef", "ts": "2026-09-02T10:06:00Z",
              "kind": "hook", "surface": "cloud", "session": SID, "event": "pre-commit",
              "repo": "example/open", "checks": ["rules-dir", "secret-file"],
              "failed": ["secret-file"], "runner": "0123456789ab"}
    record.update(overrides)
    return record


class StoreCase(unittest.TestCase):

    def setUp(self):
        self.store = Path(tempfile.mkdtemp(prefix="cloud-hooks-")).resolve()
        self.addCleanup(shutil.rmtree, self.store, ignore_errors=True)

    def shard(self, *lines, month="2026-09", sid=SID, raw=()):
        path = self.store / "events" / month / "cloud-hooks" / f"{sid}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(line) + "\n" for line in lines)
                        + "".join(text + "\n" for text in raw), encoding="utf-8")
        return path

    def tally(self, now=NOW, weeks=8):
        return census.cloud_hook_tally(self.store, now, weeks, PUBLIC)

    def doc(self, tally):
        return census.build_weekly_document(EMPTY_TALLY, NOW, 8, None, None, None, None, tally)


class ReaderTests(StoreCase):

    def test_a_well_formed_line_is_read_and_a_control_for_every_rejection(self):
        self.shard(hook())
        self.assertEqual([r["id"] for r in census.cloud_hook_records(self.store)],
                         ["0123456789abcdef"])

    def test_every_malformed_line_is_skipped(self):
        bad = [hook(extra=1), hook(kind="skill"), hook(surface="local"), hook(v=2),
               hook(id="XYZ"), hook(session=SID2), hook(event="ci"), hook(repo="a b"),
               hook(checks=["A"], failed=[]), hook(failed=["not-run"]),
               hook(checks=["a", "a"], failed=[]), hook(runner="short"),
               hook(ts="2026-08-31T10:06:00Z"),       # another month than the shard's
               hook(ts="2026-09-02T10:06:00.250Z"), hook(checks=None)]
        missing = hook()
        del missing["runner"]
        self.shard(*bad, missing, raw=["not json", "[1]"])
        self.assertEqual(census.cloud_hook_records(self.store), [])

    def test_links_and_other_shapes_are_skipped(self):
        real = self.shard(hook())
        (real.parent / "0000000000000001.jsonl").symlink_to(real)
        (real.parent / "short.jsonl").write_text(json.dumps(hook()) + "\n")
        month = self.store / "events" / "2026-10"
        month.mkdir()
        (month / "cloud-hooks").symlink_to(real.parent)
        self.assertEqual(len(census.cloud_hook_records(self.store)), 1)

    def test_no_records_is_none_not_zero(self):
        self.assertIsNone(self.tally())
        self.shard(hook(extra=1))
        self.assertIsNone(self.tally())
        self.assertIsNone(census.cloud_hook_tally(self.store / "missing", NOW, 8, PUBLIC))


class TallyTests(StoreCase):

    def test_rows_count_runs_and_failures_per_check_and_all(self):
        self.shard(hook(),
                   hook(id="1111111111111111", failed=[]),
                   hook(id="2222222222222222", event="pre-push", repo=None,
                        checks=["rules-dir"], failed=[], runner=None))
        rows = self.tally()["rows"]
        w = "2026-W36"
        self.assertEqual(rows, {
            (w, "all", None, "0123456789ab"): [2, 1],
            (w, "rules-dir", "example/open", "0123456789ab"): [2, 0],
            (w, "secret-file", "example/open", "0123456789ab"): [2, 1],
            (w, "all", None, None): [1, 0],
            (w, "rules-dir", None, None): [1, 0]})

    def test_a_check_id_the_local_log_never_counted_is_other(self):
        # The drop is untrusted: only ids the trusted local log counted are
        # published by name.
        self.shard(hook(checks=["rules-dir", "made-up-name"], failed=["made-up-name"]))
        rows = census.cloud_hook_tally(self.store, NOW, 8, PUBLIC, frozenset({"rules-dir"}))["rows"]
        names = {name for (_, name, _, _) in rows}
        self.assertEqual(names, {"all", "rules-dir", "other"})
        self.assertEqual(rows[("2026-W36", "other", "example/open", "0123456789ab")], [1, 1])

    def test_a_repo_outside_the_public_list_is_other(self):
        self.shard(hook(repo="example/closed"), hook(id="1111111111111111", repo=None))
        self.assertEqual(sorted({k[2] for k in self.tally()["rows"] if k[1] != "all"},
                                key=str), [None, "other"])

    def test_a_record_counts_once_per_id_across_shards(self):
        self.shard(hook(), sid=SID)
        self.shard(hook(session=SID2), sid=SID2)
        tally = self.tally()
        self.assertEqual(tally["records_scanned"], 1)
        self.assertEqual(tally["rows"][("2026-W36", "all", None, "0123456789ab")], [1, 1])

    def test_the_window_edges(self):
        self.shard(hook(id="aaaaaaaaaaaaaaaa", ts="2026-07-12T23:59:59Z"),   # before W29
                   hook(id="bbbbbbbbbbbbbbbb", ts="2026-07-13T00:00:00Z"),   # first instant
                   month="2026-07")
        self.shard(hook(id="cccccccccccccccc", ts="2026-09-14T00:00:00Z"))   # a later week
        tally = self.tally()
        self.assertEqual(tally["records_scanned"], 1)
        self.assertEqual(list(tally["rows"])[0][0], "2026-W29")
        # The earliest record of the STORE, even outside the window.
        self.assertEqual(tally["earliest"], datetime(2026, 7, 12, 23, 59, 59, tzinfo=timezone.utc))

    def test_records_only_outside_the_window_still_prove_the_store_has_records(self):
        self.shard(hook(ts="2026-01-02T10:00:00Z"), month="2026-01")
        tally = self.tally()
        self.assertEqual((tally["rows"], tally["records_scanned"]), ({}, 0))


class RowsAndSourceTests(StoreCase):

    def test_cloud_hook_rows_have_the_local_shape_with_surface_cloud(self):
        self.shard(hook())
        doc = self.doc(self.tally())
        rows = [r for r in doc["rows"] if r["kind"] == "hook"]
        self.assertEqual(len(rows), 3)
        self.assertEqual({r["surface"] for r in rows}, {"cloud"})
        self.assertIn({"week": "2026-08-31", "kind": "hook", "name": "secret-file",
                       "repo": "example/open", "surface": "cloud", "invocations": 1,
                       "sessions": None, "blocked": 1, "overridden": None,
                       "outcome": None, "runner": "0123456789ab"}, rows)
        self.assertEqual(skill_usage.hook_row("2026-W36", "x", None, 1, 0),
                         {**skill_usage.hook_row("2026-W36", "x", None, 1, 0, None, "local")})
        self.assertEqual(skill_usage.hook_row("2026-W36", "x", None, 1, 0)["surface"], "local")

    def test_the_source_starts_at_the_monday_of_the_earliest_record(self):
        self.shard(hook(ts="2026-08-27T15:30:00Z", id="aaaaaaaaaaaaaaaa"),   # Thursday
                   month="2026-08")
        self.shard(hook(id="bbbbbbbbbbbbbbbb"))
        source = [s for s in self.doc(self.tally())["sources"] if s["surface"] == "cloud"]
        self.assertEqual(source, [{"surface": "cloud", "scope": "hook-records",
                                   "from": "2026-08-24T00:00:00Z", "to": "2026-09-04T12:00:00Z",
                                   "records_scanned": 2}])

    def test_from_is_never_before_the_window_start(self):
        self.shard(hook(ts="2026-01-02T10:00:00Z"), month="2026-01")
        source = self.doc(self.tally())["sources"][-1]
        self.assertEqual((source["scope"], source["from"], source["records_scanned"]),
                         ("hook-records", "2026-07-13T00:00:00Z", 0))

    def test_no_records_adds_no_rows_and_no_source(self):
        doc = self.doc(self.tally())
        self.assertEqual(doc["rows"], [])
        self.assertEqual([s["scope"] for s in doc["sources"]], ["transcripts"])

    def test_the_local_hook_rows_and_all_row_are_unchanged(self):
        # The refactor that shares the row counting must not move a local count.
        log = self.store / "runs.jsonl"
        log.write_text(json.dumps({"v": 1, "ts": "2026-09-02T10:06:00Z", "event": "pre-commit",
                                   "repo": "example/open", "checks": ["a", "b"],
                                   "failed": ["b"], "runner": None}) + "\n")
        tally = census.hook_tally([str(log)], NOW, 8, PUBLIC)
        self.assertEqual(tally["rows"], {("2026-W36", "all", None, None): [1, 1],
                                         ("2026-W36", "a", "example/open", None): [1, 0],
                                         ("2026-W36", "b", "example/open", None): [1, 1]})

    def test_check_public_allows_cloud_hook_rows(self):
        self.shard(hook())
        doc = self.doc(self.tally())
        self.assertEqual(skill_usage.check_public(doc, frozenset(), frozenset()), [])

    def test_the_cli_reads_the_checkout_given_as_cloud_guidance(self):
        root = su.make_allowlist_root(self.store / "repo")
        projects = self.store / "projects"
        projects.mkdir()
        branch = self.store / "branch"
        for records in ([hook()], []):
            shutil.rmtree(branch, ignore_errors=True)
            (branch / "events").mkdir(parents=True)
            if records:
                path = branch / "events" / "2026-09" / "cloud-hooks" / f"{SID}.jsonl"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(hook()) + "\n", encoding="utf-8")
            weekly = self.store / "weekly-local.json"
            argv = ["model_usage_census.py", "--projects", str(projects),
                    "--out", str(self.store / "latest.json"), "--weekly-out", str(weekly),
                    "--now", "2026-09-04T12:00:00Z", "--hook-logs", "",
                    "--skill-allowlist-root", str(root), "--cloud-guidance", str(branch)]
            with mock.patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                self.assertEqual(census.main(), 0)
            doc = json.loads(weekly.read_text(encoding="utf-8"))
            cloud = [r for r in doc["rows"] if r["kind"] == "hook"]
            scopes = [s["scope"] for s in doc["sources"] if s["surface"] == "cloud"]
            # No local hook log, so no id is known: both checks fold into
            # `other`, leaving an `all` row and an `other` row.
            self.assertEqual((len(cloud), "hook-records" in scopes), (2, True) if records
                             else (0, False))
            self.assertEqual(skill_usage.load(weekly), doc)


class CarryTests(unittest.TestCase):

    def previous(self, to="2026-08-30T12:00:00Z"):
        rows = [skill_usage.hook_row("2026-W35", "all", None, 3, 1, None, "cloud"),
                skill_usage.hook_row("2026-W35", "all", None, 9, 2)]
        doc = skill_usage.document(rows, NOW, NOW - timedelta(weeks=8), 7,
                                   cloud_hooks={"from": NOW - timedelta(weeks=1),
                                                "records_scanned": 3})
        for source in doc["sources"]:
            if source["scope"] == "hook-records":
                source["to"] = to
        return doc

    def test_a_failed_read_carries_only_the_cloud_hook_rows_and_source(self):
        new = skill_usage.document([], NOW, NOW - timedelta(weeks=8), 7)
        carried = skill_usage.carry(self.previous(), new)
        self.assertEqual(carried["cloud hooks"], 1)
        self.assertEqual([(r["surface"], r["kind"]) for r in new["rows"]], [("cloud", "hook")])
        self.assertEqual([s["scope"] for s in new["sources"]], ["transcripts", "hook-records"])

    def test_an_old_source_is_dropped_with_its_rows(self):
        new = skill_usage.document([], NOW, NOW - timedelta(weeks=8), 7)
        self.assertIsNone(skill_usage.carry(self.previous("2026-08-20T11:59:59Z"), new)["cloud hooks"])
        self.assertEqual(new["rows"], [])

    def test_nothing_is_carried_when_the_new_file_has_its_own_source(self):
        new = skill_usage.document([], NOW, NOW - timedelta(weeks=8), 7,
                                   cloud_hooks={"from": NOW, "records_scanned": 0})
        self.assertIsNone(skill_usage.carry(self.previous(), new)["cloud hooks"])


def usage_doc(rows, sources=()):
    return {"schema": 1, "generated_at": "2026-09-04T12:00:00Z", "sources": list(sources),
            "rows": rows}


CLOUD_SOURCE = {"surface": "cloud", "scope": "hook-records", "from": "2026-08-24T00:00:00Z",
                "to": "2026-09-04T12:00:00Z", "records_scanned": 4}


class ExplorerPublicTests(unittest.TestCase):

    def setUp(self):
        self.tree = Path(tempfile.mkdtemp(prefix="explorer-hooks-")).resolve()
        self.addCleanup(shutil.rmtree, self.tree, ignore_errors=True)
        (self.tree / "usage").mkdir()

    def build(self, rows, sources=()):
        (self.tree / "usage" / "weekly-local.json").write_text(
            json.dumps(usage_doc(rows, sources)), encoding="utf-8")
        return pub.build_hooks(self.tree, NOW, None, {}, PUBLIC, dict(pub.HOOK_POLICY_DEFAULTS))

    @staticmethod
    def rows():
        return [skill_usage.hook_row("2026-W36", "all", None, 9, 1),
                skill_usage.hook_row("2026-W36", "all", None, 4, 1, None, "cloud"),
                skill_usage.hook_row("2026-W36", "rules-dir", "example/open", 3, 1, None, "cloud"),
                skill_usage.hook_row("2026-W36", "rules-dir", "example/open", 5, 0)]

    def test_cloud_totals_are_published_with_a_cloud_source(self):
        hooks = self.build(self.rows(), [CLOUD_SOURCE])
        self.assertEqual(sorted(hooks["totals"]), ["ci", "cloud", "local"])
        self.assertEqual(hooks["totals"]["cloud"], [
            {"week": "2026-08-31", "surface": "cloud", "repo": None, "invocations": 4,
             "blocked": 1, "overridden": None}])
        self.assertEqual(hooks["totals"]["local"][0]["invocations"], 9)
        self.assertEqual(hooks["cloud_from"], "2026-08-24")

    def test_without_a_cloud_source_the_cloud_key_is_absent_and_rows_are_dropped(self):
        hooks = self.build(self.rows())
        self.assertEqual(sorted(hooks["totals"]), ["ci", "local"])
        self.assertNotIn("cloud_from", hooks)
        # Another surface's source does not count.
        self.assertNotIn("cloud", self.build(self.rows(), [
            {**CLOUD_SOURCE, "scope": "guidance-records"}])["totals"])

    def test_a_source_with_no_readable_from_does_not_count(self):
        hooks = self.build(self.rows(), [{**CLOUD_SOURCE, "from": "nope"}])
        self.assertNotIn("cloud", hooks["totals"])
        self.assertNotIn("cloud_from", hooks)

    def test_per_check_use_rows_carry_the_cloud_surface_only_with_a_source(self):
        extra = [skill_usage.hook_row("2026-W36", "repo-local", "example/open", 1, 0),
                 skill_usage.hook_row("2026-W36", "repo-local", "example/open", 2, 1, None,
                                      "cloud")]
        for sources, surfaces in (([CLOUD_SOURCE], ["cloud", "local"]), ([], ["local"])):
            hooks = self.build(self.rows() + extra, sources)
            entry = next(c for c in hooks["checks"] if c["name"] == "repo-local")
            self.assertEqual(sorted({u["surface"] for u in entry["use"]}), surfaces)

    def test_the_schema_accepts_both_shapes(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is not installed")
        schema = json.loads((ROOT / "explorer" / "schema.json").read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(
            {"$ref": "#/$defs/hooks", "$defs": schema["$defs"]})
        for sources in ([CLOUD_SOURCE], []):
            hooks = self.build(self.rows(), sources)
            self.assertEqual(list(validator.iter_errors(hooks)), [])


if __name__ == "__main__":
    unittest.main()
