#!/usr/bin/env python3
"""skills-evals#562 PR B (2026-11-02): the reader of the cloud shards that
_agent-guidance's Stop hook writes from cloud sessions (ADR 0036), at
`events/<YYYY-MM>/cloud-skills/<16 hex>.jsonl` on the private branch, and
the `surface: "cloud"` `skill-digest` rows built from them.

Every store, registry and transcript here is synthetic, under a mkdtemp;
the registry "mirror" is a local bare clone. `now` is always passed in.
Each rejection test has a control in which the valid line is accepted, so
a skip means the check fired.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test" / "issues"))
import model_usage_census as census  # noqa: E402
import skill_usage  # noqa: E402
# Modules, never their TestCase classes by name (test/run_tests.py's
# suite-coverage check rejects a class collected twice).
import test_issue_562_loaded_copies as lc562  # noqa: E402
import test_issue_skill_usage as su  # noqa: E402

PUBLIC, FORK, SKILL = lc562.PUBLIC, lc562.FORK, lc562.SKILL
ENTRIES = lc562.ENTRIES
NOW = su.NOW                                        # 2026-09-04, ISO week 2026-W36
SID = "0123456789abcdef"
SID2 = "fedcba9876543210"
DIGEST = "c" * 64
START = census.window_from(NOW, 8)


def cloud_line(**overrides) -> dict:
    """One well-formed shard line (ADR 0036's fields, no `machine`)."""
    line = {"v": 1, "id": "toolu_cloud_01", "ts": "2026-09-02T10:00:00.000Z",
            "kind": "skill", "surface": "cloud", "session": SID, "cli": "2.1.312",
            "name": SKILL, "base_kind": "plugin-cache", "registry": PUBLIC,
            "ref": None, "digest": DIGEST, "digest_null_reason": None}
    line.update(overrides)
    return line


class StoreCase(unittest.TestCase):

    def setUp(self):
        self.store = Path(tempfile.mkdtemp(prefix="cloud-562-")).resolve()
        self.addCleanup(shutil.rmtree, self.store, ignore_errors=True)

    def shard(self, *lines, month="2026-09", sid=SID, raw=()):
        path = self.store / "events" / month / census.CLOUD_SKILLS_DIR / f"{sid}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write("".join(json.dumps(line) + "\n" for line in lines))
            f.write("".join(text + "\n" for text in raw))
        return path

    def machine(self, *lines, name="box-one"):
        path = self.store / "events" / "2026-09" / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write("".join(line + "\n" for line in lines))

    def ids(self):
        return [r["id"] for r in census.cloud_skill_records(self.store)]


# --- reading the shards --------------------------------------------------------

class ShardReaderTests(StoreCase):

    def test_a_valid_line_is_read_and_has_no_machine_key(self):
        self.shard(cloud_line())
        self.assertEqual(census.cloud_skill_records(self.store), [cloud_line()])
        self.assertNotIn("machine", census.CLOUD_KEYS)

    def test_only_a_month_directory_and_a_16_hex_stem_are_read(self):
        self.shard(cloud_line(id="good"))
        for label, month, sid in (("short stem", "2026-09", "0123"),
                                  ("upper-case stem", "2026-09", SID.upper()),
                                  ("17 hex", "2026-09", SID + "0"),
                                  ("bad month", "2026-9", SID),
                                  ("word month", "latest", SID)):
            with self.subTest(label):
                self.shard(cloud_line(id=label.replace(" ", "-"), ts="2026-09-02T10:00:00Z"),
                           month=month, sid=sid)
        # A shard filed one level up is a machine-file name and not a shard.
        flat = self.store / "events" / "2026-09" / f"{SID}.jsonl"
        flat.write_text(json.dumps(cloud_line(id="flat")) + "\n", encoding="utf-8")
        self.assertEqual(self.ids(), ["good"])

    def test_links_are_never_followed(self):
        real = self.shard(cloud_line(id="real", session=SID2), sid=SID2)
        outside = Path(tempfile.mkdtemp(prefix="cloud-562-outside-")).resolve()
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        for month in ("2026-08", "2026-07"):
            shard = outside / month / "cloud-skills" / f"{SID}.jsonl"
            shard.parent.mkdir(parents=True)
            shard.write_text(json.dumps(cloud_line(id=f"via-{month}", ts=f"{month}-02T10:00:00Z"))
                             + "\n", encoding="utf-8")
        (self.store / "events" / "2026-08").symlink_to(outside / "2026-08")    # month link
        (self.store / "events" / "2026-07").mkdir()
        (self.store / "events" / "2026-07" / census.CLOUD_SKILLS_DIR).symlink_to(
            outside / "2026-07" / "cloud-skills")                               # dir link
        (real.parent / f"{SID}.jsonl").symlink_to(real)                         # file link
        self.assertEqual(self.ids(), ["real"])

    def test_every_malformed_field_skips_the_line(self):
        bad = {
            "extra machine key": cloud_line(machine="box"),
            "extra typed key": cloud_line(typed=False),
            "missing ref": {k: v for k, v in cloud_line().items() if k != "ref"},
            "v true": cloud_line(v=True), "v 2": cloud_line(v=2), "v string": cloud_line(v="1"),
            "kind": cloud_line(kind="hook"), "surface": cloud_line(surface="local"),
            "session of another shard": cloud_line(session=SID2),
            "session not hex": cloud_line(session="session-raw-id00"),
            "id with a slash": cloud_line(id="a/b"), "id empty": cloud_line(id=""),
            "id too long": cloud_line(id="a" * 129), "id not a string": cloud_line(id=7),
            "name with a path": cloud_line(name="/home/example/skill"),
            "name too long": cloud_line(name="a" * 65),
            "name null": cloud_line(name=None),
            "ts without Z": cloud_line(ts="2026-09-02T10:00:00+00:00"),
            "ts in another month": cloud_line(ts="2026-08-31T10:00:00Z"),
            "ts not a date": cloud_line(ts="2026-09-99T10:00:00Z"),
            "ts year out of range": cloud_line(ts="2101-09-02T10:00:00Z"),
            "cli prose": cloud_line(cli="the cli"), "cli number": cloud_line(cli=2),
            "base_kind": cloud_line(base_kind="somewhere"),
            "registry url": cloud_line(registry="https://github.com/" + PUBLIC),
            "registry with token": cloud_line(registry="user:tok@host/o/r"),
            "ref short": cloud_line(ref="a" * 39), "ref upper": cloud_line(ref="A" * 40),
            "digest upper": cloud_line(digest="C" * 64),
            "digest short": cloud_line(digest="c" * 63),
            "digest with a reason": cloud_line(digest_null_reason="gone"),
            "null digest without a reason": cloud_line(digest=None),
            "null digest, unknown reason": cloud_line(digest=None, digest_null_reason="invented"),
            "null digest, public-only reason": cloud_line(digest=None,
                                                          digest_null_reason="conflict"),
        }
        for label, line in bad.items():
            with self.subTest(label):
                shutil.rmtree(self.store / "events", ignore_errors=True)
                self.shard(line)
                self.assertEqual(self.ids(), [], label)
        for label, raw in (("not JSON", "{torn"), ("a list", "[1]"), ("a string", '"x"')):
            with self.subTest(label):
                shutil.rmtree(self.store / "events", ignore_errors=True)
                self.shard(raw=(raw,))
                self.assertEqual(self.ids(), [], label)
        # Controls: each value the shape allows is read.
        good = (cloud_line(), cloud_line(ref="a" * 40, cli=None, registry=None),
                cloud_line(digest=None, digest_null_reason="bad-name", name="invalid",
                           base_kind="unknown", ts="2026-09-30T23:59:59Z"),
                cloud_line(name="example-plugin:finding-unknowns", base_kind="user-skills"))
        shutil.rmtree(self.store / "events", ignore_errors=True)
        self.shard(*[dict(line, id=f"g{i}") for i, line in enumerate(good)],
                   raw=("{torn",))
        self.assertEqual(self.ids(), ["g0", "g1", "g2", "g3"])


# --- one id across a shard and a machine file ------------------------------------

class ResolutionTests(StoreCase):

    def test_an_id_in_a_shard_and_a_machine_file_resolves_together(self):
        self.machine(lc562.store_line("toolu_cloud_01", digest=None, digest_null_reason="gone",
                                      registry=PUBLIC))
        self.shard(cloud_line())
        copy = census.store_digests(self.store)["toolu_cloud_01"]
        self.assertEqual((copy["digest"], copy["reason"], copy["registry"]),
                         (DIGEST, None, PUBLIC))
        self.assertEqual(census.machine_skill_ids(self.store), {"toolu_cloud_01"})

    def test_two_different_digests_across_them_are_a_conflict(self):
        self.machine(lc562.store_line("toolu_cloud_01", digest="d" * 64,
                                      digest_null_reason=None, registry=PUBLIC))
        self.shard(cloud_line())
        copy = census.store_digests(self.store)["toolu_cloud_01"]
        self.assertEqual((copy["digest"], copy["reason"]), (None, "conflict"))

    def test_a_malformed_shard_line_does_not_take_part(self):
        self.machine(lc562.store_line("toolu_cloud_01", digest="d" * 64,
                                      digest_null_reason=None, registry=PUBLIC))
        self.shard(cloud_line(machine="box"))           # malformed: an extra key
        self.assertEqual(census.store_digests(self.store)["toolu_cloud_01"]["digest"], "d" * 64)


# --- the cloud plan and rows ------------------------------------------------------

class CloudRowTests(StoreCase):

    def plan(self, local_ids=frozenset()):
        cloud = census.cloud_digest_plan(census.cloud_skill_records(self.store), set(local_ids),
                                         census.store_digests(self.store), START, NOW, su.ALLOW)
        return {"from": START.strftime(skill_usage.STAMP), "uses": [], "registries": [],
                **({"cloud": cloud} if cloud is not None else {})}

    def doc(self, plan, mirrors=None):
        rows, _ = census.digest_rows(plan, ENTRIES, mirrors or {})
        doc = skill_usage.document([], NOW, START, 0)
        census.add_digest_rows(doc, plan, rows, NOW)
        return doc

    def cloud_rows(self, doc):
        return [r for r in doc["rows"] if r["kind"] == "skill-digest" and r["surface"] == "cloud"]

    def test_rows_count_each_distinct_id_once_and_skip_other_and_out_of_window(self):
        self.shard(cloud_line(id="a"), cloud_line(id="b", ts="2026-09-03T10:00:00Z"),
                   cloud_line(id="a"),                                  # re-uploaded
                   cloud_line(id="other-1", name="not-allowlisted"),
                   cloud_line(id="future", ts="2026-09-30T10:00:00Z"))  # after now
        self.shard(cloud_line(id="a", session=SID2), sid=SID2)          # a second shard
        self.shard(cloud_line(id="w35", ts="2026-08-25T10:00:00Z", session=SID2,
                              digest=None, digest_null_reason="gone"),
                   month="2026-08", sid=SID2)
        self.shard(cloud_line(id="old", ts="2026-01-05T10:00:00Z"), month="2026-01")
        plan = self.plan()
        doc = self.doc(plan)
        rows = self.cloud_rows(doc)
        self.assertEqual(sorted((r["week"], r["digest"], r["invocations"], r["sessions"])
                                for r in rows),
                         [("2026-08-24", "unknown:gone", 1, 1),
                          ("2026-08-31", "unknown:unverified-commit", 2, 1)])
        # The invariant: per (name, week), invocations == the distinct ids
        # counted (a, b in W36; w35 in W35).
        sums: dict = {}
        for r in rows:
            sums[(r["name"], r["week"])] = sums.get((r["name"], r["week"]), 0) + r["invocations"]
        self.assertEqual(sums, {(SKILL, "2026-08-31"): 2, (SKILL, "2026-08-24"): 1})
        self.assertEqual(len(plan["cloud"]["uses"]), 3)
        source = next(s for s in doc["sources"] if s["surface"] == "cloud")
        self.assertEqual(source, {"surface": "cloud", "scope": "skill-records",
                                  "from": START.strftime(skill_usage.STAMP),
                                  "to": su.NOW_TEXT, "events_scanned": 3})
        self.assertEqual(skill_usage.check_public(doc, su.ALLOW, {PUBLIC}), [])
        blob = json.dumps(doc)
        for private in (SID, SID2, DIGEST, "toolu_cloud"):
            self.assertNotIn(private, blob)

    def test_an_id_also_recorded_locally_counts_once_there(self):
        self.shard(cloud_line(id="teleported"), cloud_line(id="cloud-only"))
        uses = self.plan(local_ids={"teleported"})["cloud"]["uses"]
        self.assertEqual(len(uses), 1)
        self.assertEqual(len(self.plan()["cloud"]["uses"]), 2)            # control

    def test_from_is_the_monday_of_the_earliest_line_inside_the_window(self):
        self.shard(cloud_line(id="x", ts="2026-08-27T10:00:00Z"), month="2026-08")
        self.shard(cloud_line(id="y"))
        self.assertEqual(self.plan()["cloud"]["from"], "2026-08-24T00:00:00Z")

    def test_no_shard_line_means_no_cloud_source_unknown_not_zero(self):
        self.shard(cloud_line(machine="box"))                           # malformed only
        plan = self.plan()
        self.assertNotIn("cloud", plan)
        doc = self.doc(plan)
        self.assertEqual([s["surface"] for s in doc["sources"] if s["scope"] == "skill-records"],
                         ["local"])

    def test_a_private_registry_is_unlisted_and_a_public_one_publishes_its_prefix(self):
        tmp = Path(tempfile.mkdtemp(prefix="cloud-562-mirror-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        files = lc562.skill_files("cloud text")
        lc562.registry(tmp / "work", [("2026-08-01T00:00:00Z", files)])
        mirror = lc562.mirror_of(tmp / "work", tmp / "mirror.git")
        (tmp / "scratch").mkdir()
        digest = lc562.digest_of(files, tmp / "scratch")
        for registry, shown, repo in ((FORK, "unknown:unlisted-registry", None),
                                      (PUBLIC, digest[:12], PUBLIC)):    # the control
            with self.subTest(registry=registry):
                shutil.rmtree(self.store / "events", ignore_errors=True)
                self.shard(cloud_line(registry=registry, digest=digest))
                doc = self.doc(self.plan(), {PUBLIC: str(mirror)})
                self.assertEqual([(r["digest"], r["repo"]) for r in self.cloud_rows(doc)],
                                 [(shown, repo)])
                self.assertNotIn(FORK, json.dumps(doc))
                self.assertNotIn(digest, json.dumps(doc))

    def test_the_cli_adds_cloud_rows_from_the_store(self):
        tmp = Path(tempfile.mkdtemp(prefix="cloud-562-cli-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "projects").mkdir()
        self.shard(cloud_line(digest=None, digest_null_reason="too-large"))
        plan_path, weekly = tmp / "plan.json", tmp / "w.json"
        argv = ["model_usage_census.py", "--projects", str(tmp / "projects"),
                "--out", str(tmp / "o.json"), "--weekly-out", str(weekly),
                "--now", su.NOW_TEXT, "--hook-logs", "", "--event-store", str(self.store),
                "--skill-allowlist-root", str(su.make_allowlist_root(tmp / "allow"))]
        for extra in ([], ["--digest-plan-out", str(plan_path)]):
            with self.subTest(extra=extra), mock.patch.object(sys, "argv", argv + extra), \
                    mock.patch("sys.stdout"):
                self.assertEqual(census.main(), 0)
        self.assertIn("cloud", json.loads(plan_path.read_text(encoding="utf-8")))
        census.apply_digest_plan(plan_path, weekly, {})
        doc = json.loads(weekly.read_text(encoding="utf-8"))
        # The CLI's allowlist (su.make_allowlist_root) holds workflow-path-audit,
        # not SKILL: the line counts under `other` and gets no row.
        self.assertEqual(self.cloud_rows(doc), [])
        self.assertEqual(next(s for s in doc["sources"] if s["surface"] == "cloud"
                              and s["scope"] == "skill-records")["events_scanned"], 0)
        shutil.rmtree(self.store / "events")
        self.shard(cloud_line(name="workflow-path-audit", digest=None,
                              digest_null_reason="too-large"))
        with mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout"):
            self.assertEqual(census.main(), 0)
        doc = json.loads(weekly.read_text(encoding="utf-8"))
        self.assertEqual([(r["name"], r["digest"]) for r in self.cloud_rows(doc)],
                         [("workflow-path-audit", "unknown:too-large")])
        self.assertNotIn(SID, weekly.read_text(encoding="utf-8"))


# --- carry on a failed fetch ------------------------------------------------------

class CloudCarryTests(unittest.TestCase):

    def previous(self, to):
        when = skill_usage.parse_ts(to)
        doc = skill_usage.document([], when, when - timedelta(weeks=8), 5)
        skill_usage.add_rows(doc, [skill_usage.digest_row("2026-08-24", SKILL, PUBLIC,
                                                          "abcdef012345", 2, 1, "cloud")],
                             skill_usage.digest_source(when - timedelta(weeks=1), when, 2,
                                                       "cloud"))
        return doc

    def test_cloud_rows_are_carried_unless_older_than_14_days(self):
        for to, carried in (("2026-08-21T12:00:00Z", 1), ("2026-08-20T11:59:59Z", None)):
            with self.subTest(to=to):
                new = skill_usage.document([], NOW, NOW - timedelta(weeks=8), 7)
                self.assertEqual(skill_usage.carry(self.previous(to), new),
                                 {"cloud": None, "skill copies": None,
                                  "cloud skill copies": carried,
                                  "cloud hooks": None})
                self.assertEqual([(r["kind"], r["surface"]) for r in new["rows"]],
                                 [("skill-digest", "cloud")] if carried else [])

    def test_the_carry_entry_is_scoped_to_cloud_skill_records(self):
        self.assertIn(("cloud skill copies", skill_usage.DIGEST_SCOPE,
                       (skill_usage.DIGEST_KIND,), skill_usage.SURFACE_CLOUD),
                      skill_usage.CARRIED)


if __name__ == "__main__":
    unittest.main()
