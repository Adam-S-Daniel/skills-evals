#!/usr/bin/env python3
"""`scripts/ingest_usage_sink.py`: cloud usage records dropped in the private
S3 bucket (_agent-guidance ADR 0037), ingested into the private store in the
files the census reads (`cloud_guidance_tally`, `cloud_skill_records`).

Every object, listing, manifest and store here is synthetic, under a mkdtemp;
`now` and every LastModified are passed in. No network, no clock. Each
rejection test has a control in which the valid object is accepted, so a
rejection means the check fired.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
import ingest_usage_sink as sink  # noqa: E402
import model_usage_census as census  # noqa: E402

SCRIPT = ROOT / "scripts" / "ingest_usage_sink.py"
NOW = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
SID = "0123456789abcdef"
SID2 = "fedcba9876543210"
KEY = "drop/2026-09-02/" + "a" * 32 + ".json"
KEY2 = "drop/2026-09-02/" + "b" * 32 + ".json"
KEY3 = "drop/2026-09-01/" + "c" * 32 + ".json"
#: The objects' S3 LastModified: just after the records' own times.
MODIFIED = "2026-09-02T10:10:30Z"
MODIFIED_AT = datetime(2026, 9, 2, 10, 10, 30, tzinfo=timezone.utc)
#: Invented strings that must never reach stdout or stderr.
MARKERS = ("toolu_marker_01", "toolu_marker_02", "marker-owner/marker-registry",
           "marker-skill", "remote_marker")
#: Arabic-Indic digits: `\d` matches them, `[0-9]` does not.
UNICODE_KEY = "drop/٢٠٢٦-٠٩-٠٢/" + "d" * 32 + ".json"


def guidance(**overrides) -> dict:
    """One record shaped as the hook's phase 1 uploads it (no `uploaded`)."""
    record = {"v": 1, "ts": "2026-09-02T10:00:00Z", "kind": "guidance-load",
              "session": SID, "surface": "remote_marker", "remote": True,
              "cli": "2.1.312", "state": "full", "repos": 2,
              "guidance_version": "0123abcd", "check_expected": True,
              "check_reported": "match", "registry_sha": None,
              "sources": [{"registry": "marker-owner/marker-registry", "ref": "e" * 40}],
              "sources_dropped": 0}
    record.update(overrides)
    return record


def skill(**overrides) -> dict:
    """One ADR 0036 shard line."""
    record = {"v": 1, "id": "toolu_marker_01", "ts": "2026-09-02T10:05:00Z",
              "kind": "skill", "surface": "cloud", "session": SID, "cli": "2.1.312",
              "name": "marker-skill", "base_kind": "plugin-cache",
              "registry": "marker-owner/marker-registry", "ref": None,
              "digest": "c" * 64, "digest_null_reason": None}
    record.update(overrides)
    return record


def hook(**overrides) -> dict:
    """One cloud hook line: an agent-checks run, in the key order the hook writes."""
    record = {"v": 1, "id": "0123456789abcdef", "ts": "2026-09-02T10:06:00Z",
              "kind": "hook", "surface": "cloud", "session": SID, "event": "pre-commit",
              "repo": "example/repo", "checks": ["rules-dir", "secret-file"],
              "failed": ["secret-file"], "runner": "0123456789ab"}
    record.update(overrides)
    return record


def setup(**overrides) -> dict:
    """One setup record, as a cloud environment's setup script sends it."""
    record = {"id": "0123456789abcdef0123456789abcdef", "ts": "2026-09-02T10:07:00Z",
              "launcher_version": 3, "launcher_sha256": "a" * 64,
              "script_source": "checkout", "script_sha256": "b" * 64,
              "script_commit": "c" * 40, "fleet_pin_commit": "d" * 40,
              "fleet_guidance_commit": "e" * 40, "fleet_guidance": "installed"}
    record.update(overrides)
    return record


def drop(guidance_records=None, skills=None, **overrides) -> dict:
    doc = {"v": 1, "kind": "usage-drop", "sent": "2026-09-02T10:10:00Z",
           "guidance": [guidance()] if guidance_records is None else guidance_records,
           "skills": ([skill(), skill(id="toolu_marker_02")] if skills is None else skills)}
    doc.update(overrides)
    return doc


def tree_digest(root: Path) -> dict:
    """{relative path: sha256} of every file under `root`."""
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


class SinkCase(unittest.TestCase):

    def setUp(self):
        base = Path(tempfile.mkdtemp(prefix="usage-sink-")).resolve()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        self.base = base
        self.store = base / "store"
        self.incoming = base / "incoming"
        self.store.mkdir()
        self.incoming.mkdir()
        self.manifest = {}

    def put(self, key, doc=None, raw=None, modified=MODIFIED, listed=True):
        """Download `doc` (or `raw`) to its key, and list it in the manifest."""
        path = self.incoming / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw if raw is not None else
                         json.dumps(doc, separators=(",", ":")).encode("utf-8"))
        if listed:
            self.manifest[key] = modified
        return path

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                              text=True, cwd=str(self.base), stdin=subprocess.DEVNULL)

    def apply(self, unreadable=None):
        manifest = self.base / "manifest.txt"
        manifest.write_text("".join(f"{k}\t{v}\n" for k, v in self.manifest.items()),
                            encoding="utf-8")
        args = ["apply", "--incoming", str(self.incoming), "--store", str(self.store),
                "--manifest", str(manifest)]
        if unreadable is not None:
            listed = self.base / "unreadable.txt"
            listed.write_text("".join(k + "\n" for k in unreadable), encoding="utf-8")
            args += ["--unreadable", str(listed)]
        proc = self.run_cli(*args)
        for marker in MARKERS:
            self.assertNotIn(marker, proc.stdout + proc.stderr)
        return proc

    def index(self, kind, month="2026-09"):
        path = self.store / "sink" / kind / f"{month}.txt"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def write_index(self, kind, *lines, month="2026-09"):
        path = self.store / "sink" / kind / f"{month}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write("".join(line + "\n" for line in lines))

    def events(self):
        return sorted(str(p.relative_to(self.store))
                      for p in (self.store / "events").rglob("*.jsonl")) \
            if (self.store / "events").exists() else []


# --- plan -------------------------------------------------------------------------

class PlanTests(SinkCase):

    def listing(self, contents, raw=None):
        path = self.base / "listing.json"
        path.write_text(raw if raw is not None else json.dumps({"Contents": contents}),
                        encoding="utf-8")
        return path

    @staticmethod
    def item(key, size=100, modified="2026-09-02T10:10:30+00:00"):
        return {"Key": key, "Size": size, "LastModified": modified}

    def plan(self, path, *extra):
        proc = self.run_cli("plan", "--listing", str(path), "--store", str(self.store),
                            *extra)
        return proc.returncode, proc.stdout.splitlines(), proc.stderr.splitlines()

    def test_keeps_only_well_formed_ascii_keys(self):
        bad = ["drop/2026-09-02/" + "A" * 32 + ".json",
               "drop/2026-09-02/" + "a" * 31 + ".json",
               "drop/2026-9-2/" + "a" * 32 + ".json",
               "other/2026-09-02/" + "a" * 32 + ".json",
               "drop/2026-09-02/x/" + "a" * 32 + ".json",
               "drop/2026-09-02/" + "a" * 32 + ".json\n",
               "drop/2026-09-02/" + "a" * 32 + ".txt",
               UNICODE_KEY,
               "drop/２０２６-09-02/" + "a" * 32 + ".json"]
        code, out, err = self.plan(self.listing(
            [self.item(KEY), *(self.item(k) for k in bad), {"Key": 7}, "not-an-item"]))
        self.assertEqual((code, out), (0, [f"{KEY}\t{MODIFIED}"]))
        self.assertEqual(err[-1], "planned=1 backlog=1 skipped_bad_date=0 skipped_size=0")
        self.assertIsNone(sink.KEY_RE.fullmatch(UNICODE_KEY))

    def test_size_filter(self):
        code, out, err = self.plan(self.listing([
            self.item(KEY, size=sink.SIZE_CAP), self.item(KEY2, size=sink.SIZE_CAP + 1),
            self.item(KEY3, size="10")]))
        self.assertEqual(out, [f"{KEY}\t{MODIFIED}"])
        self.assertEqual(err[-1], "planned=1 backlog=1 skipped_bad_date=0 skipped_size=2")

    def test_date_part_must_be_last_modified_day_or_the_day_before(self):
        keys = {d: f"drop/{d}/" + h * 32 + ".json"
                for d, h in (("2026-09-02", "1"), ("2026-09-01", "2"), ("2026-08-31", "3"),
                             ("2026-09-03", "4"), ("2026-02-30", "5"), ("0000-00-00", "6"))}
        code, out, err = self.plan(self.listing(
            [self.item(k) for k in keys.values()]
            + [self.item(KEY, modified="yesterday"), self.item(KEY2, modified=None)]))
        self.assertEqual(code, 0)
        self.assertEqual([line.split("\t")[0] for line in out],
                         [keys["2026-09-01"], keys["2026-09-02"]])
        self.assertEqual(err[-1], "planned=2 backlog=2 skipped_bad_date=6 skipped_size=0")

    def test_last_modified_is_read_in_utc(self):
        # 01:00 at +02:00 is 23:00 the day before in UTC.
        late = "2026-09-03T01:00:00.123+02:00"
        key3 = "drop/2026-09-03/" + "e" * 32 + ".json"
        code, out, err = self.plan(self.listing([self.item(KEY, modified=late),
                                                 self.item(key3, modified=late)]))
        self.assertEqual(out, [f"{KEY}\t2026-09-02T23:00:00Z"])
        self.assertEqual(err[-1], "planned=1 backlog=1 skipped_bad_date=1 skipped_size=0")
        _, out, _ = self.plan(self.listing([self.item(KEY, modified="2026-09-02T10:10:30.5Z")]))
        self.assertEqual(out, [f"{KEY}\t{MODIFIED}"])

    def test_orders_by_last_modified_oldest_first(self):
        k1 = "drop/2026-09-02/" + "f" * 32 + ".json"
        k2 = "drop/2026-09-02/" + "0" * 32 + ".json"
        k3 = "drop/2026-09-01/" + "9" * 32 + ".json"
        _, out, _ = self.plan(self.listing([
            self.item(k1, modified="2026-09-02T08:00:00Z"),
            self.item(k2, modified="2026-09-02T09:00:00Z"),
            self.item(k3, modified="2026-09-02T09:00:00Z"),
            self.item(KEY, modified="2026-09-02T01:00:00Z")]))
        self.assertEqual([line.split("\t")[0] for line in out], [KEY, k1, k3, k2])  # a tie goes by key

    def test_max_caps_the_output_and_backlog_counts_the_rest(self):
        items = [self.item(f"drop/2026-09-02/{h * 32}.json",
                           modified=f"2026-09-02T10:0{i}:00Z")
                 for i, h in enumerate("1234")]
        path = self.listing(items)
        _, out, err = self.plan(path, "--max", "2")
        self.assertEqual([line.split("\t")[0] for line in out],
                         ["drop/2026-09-02/" + "1" * 32 + ".json",
                          "drop/2026-09-02/" + "2" * 32 + ".json"])
        self.assertEqual(err[-1], "planned=2 backlog=4 skipped_bad_date=0 skipped_size=0")
        self.assertEqual(self.plan(path, "--max", "0")[1], [])
        self.assertEqual(len(self.plan(path)[1]), 4)
        self.assertNotEqual(self.plan(path, "--max", "-1")[0], 0)
        self.assertNotEqual(self.plan(path, "--max", "٢")[0], 0)

    def test_default_max_is_300(self):
        items = [self.item(f"drop/2026-09-02/{i:032x}.json") for i in range(305)]
        _, out, err = self.plan(self.listing(items))
        self.assertEqual(len(out), 300)
        self.assertEqual(err[-1], "planned=300 backlog=305 skipped_bad_date=0 skipped_size=0")

    def test_skips_keys_already_ingested_or_rejected_for_good(self):
        keys = [f"drop/2026-09-02/{h * 32}.json" for h in "123456"]
        listing = self.listing([self.item(k) for k in keys])
        self.assertEqual(len(self.plan(listing)[1]), 6)
        self.write_index("ingested", f"{keys[0]} {'0' * 64}",
                         f"{keys[1]} {'0' * 64} partial=1")
        self.write_index("rejected", f"{keys[2]} unreadable v1", f"{keys[3]} bad-envelope v1",
                         f"{keys[4]} unreadable")
        _, out, err = self.plan(listing)
        self.assertEqual([line.split("\t")[0] for line in out], [keys[5]])
        self.assertEqual(err[-1], "planned=1 backlog=1 skipped_bad_date=0 skipped_size=0")

    def test_older_version_rejections_are_eligible_again(self):
        keys = [f"drop/2026-09-02/{h * 32}.json" for h in "1234"]
        listing = self.listing([self.item(k) for k in keys])
        # Lines written before versions existed read as v1.
        self.write_index("rejected", f"{keys[0]} bad-skill-record", f"{keys[1]} bad-keys v1",
                         f"{keys[2]} bad-guidance-record v{sink.VALIDATOR_VERSION}", f"{keys[3]} bad-envelope")
        self.assertEqual([line.split("\t")[0] for line in self.plan(listing)[1]],
                         keys[:2])
        with mock.patch.object(sink, "VALIDATOR_VERSION", sink.VALIDATOR_VERSION + 1):
            planned, _ = sink.plan(listing, self.store)
        self.assertEqual([key for key, _ in planned], keys[:3])

    def test_an_empty_listing_plans_nothing(self):
        code, out, err = self.plan(self.listing(None, raw='{"Prefix": "drop/"}'))
        self.assertEqual((code, out), (0, []))
        self.assertEqual(err, ["planned=0 backlog=0 skipped_bad_date=0 skipped_size=0"])

    def test_an_unreadable_listing_exits_nonzero(self):
        code, out, _ = self.plan(self.listing(None, raw="{not json"))
        self.assertEqual((code, out), (2, []))
        self.assertEqual(self.plan(self.base / "missing.json")[0], 2)
        self.assertEqual(self.plan(self.listing(None, raw='{"Contents": 5}'))[0], 2)


# --- apply ------------------------------------------------------------------------

class ApplyTests(SinkCase):

    def test_a_valid_object_reaches_both_census_readers(self):
        body = self.put(KEY, drop()).read_bytes()
        proc = self.apply()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("1 ingested (0 partial", proc.stdout)
        self.assertEqual(self.events(), ["events/2026-09/cloud-guidance.jsonl",
                                         f"events/2026-09/cloud-skills/{SID}.jsonl"])
        self.assertEqual([r["id"] for r in census.cloud_skill_records(self.store)],
                         ["toolu_marker_01", "toolu_marker_02"])
        tally = census.cloud_guidance_tally(self.store, NOW, 8)
        self.assertEqual(tally["records_scanned"], 1)
        self.assertEqual(tally["guidance"], {"full": {"2026-W36": 1}})
        self.assertEqual(tally["checks"], {"match": {"2026-W36": 1}})
        self.assertEqual(self.index("ingested"),
                         [f"{KEY} {hashlib.sha256(body).hexdigest()}"])
        self.assertEqual(self.index("rejected"), [])
        line = (self.store / "events/2026-09/cloud-guidance.jsonl").read_text()
        self.assertEqual(line, json.dumps(guidance(), separators=(",", ":")) + "\n")

    def test_records_file_under_the_month_of_their_own_ts(self):
        key = "drop/2026-10-01/" + "e" * 32 + ".json"
        self.put(key, drop([guidance(ts="2026-10-01T00:00:01Z")],
                           [skill(ts="2026-09-30T23:59:59Z")]),
                 modified="2026-10-01T00:05:00Z")
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(self.events(), [f"events/2026-09/cloud-skills/{SID}.jsonl",
                                         "events/2026-10/cloud-guidance.jsonl"])
        self.assertEqual(len(self.index("ingested", month="2026-10")), 1)

    def test_uploaded_key_is_accepted_and_not_stored(self):
        for value in (True, False, None):
            self.assertTrue(sink.guidance_record_ok(guidance(uploaded=value)))
        self.assertFalse(sink.guidance_record_ok(guidance(uploaded="yes")))
        self.put(KEY, drop([guidance(uploaded=True)], []))
        self.assertEqual(self.apply().returncode, 0)
        stored = json.loads((self.store / "events/2026-09/cloud-guidance.jsonl").read_text())
        self.assertEqual(stored, guidance())

    def test_a_store_file_without_a_final_newline_gets_one(self):
        path = self.store / "events/2026-09/cloud-guidance.jsonl"
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{"session":"' + SID2.encode() + b'"}')
        self.put(KEY, drop(None, []))
        self.assertEqual(self.apply().returncode, 0)
        lines = path.read_bytes().split(b"\n")
        self.assertEqual(lines[0], b'{"session":"' + SID2.encode() + b'"}')
        self.assertEqual(json.loads(lines[1]), guidance())
        self.assertEqual(lines[2], b"")

    def test_objects_not_in_the_manifest_are_ignored(self):
        self.put(KEY, drop(), listed=False)
        proc = self.apply()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0 objects read", proc.stdout)
        self.assertIn("1 other entries ignored", proc.stdout)
        self.assertEqual(self.events(), [])
        self.assertEqual(self.index("ingested") + self.index("rejected"), [])

    def test_unreadable_keys_are_rejected_for_good(self):
        self.manifest[KEY] = MODIFIED            # planned, but the GET failed
        self.manifest[KEY2] = MODIFIED           # planned, neither fetched nor listed
        proc = self.apply(unreadable=[KEY, KEY3])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.index("rejected"),
                         [f"{KEY3} unreadable v4", f"{KEY} unreadable v4"])
        self.assertEqual(self.index("ingested"), [])
        self.assertIn("1 planned but missing", proc.stdout)
        self.assertIn("rejected by reason: unreadable 2", proc.stdout)
        listing = self.base / "listing.json"
        listing.write_text(json.dumps({"Contents": [
            PlanTests.item(k) for k in (KEY, KEY2)]}))
        self.assertEqual([key for key, _ in sink.plan(listing, self.store)[0]], [KEY2])

    def test_bad_manifest_or_unreadable_list_exits_two(self):
        manifest = self.base / "bad-manifest.txt"
        for text in (f"{KEY}\n", f"{KEY}\t2026-09-02 10:10:30\n", f"{UNICODE_KEY}\t{MODIFIED}\n",
                     f"{KEY}\t2026-02-30T10:10:30Z\n"):
            manifest.write_text(text, encoding="utf-8")
            proc = self.run_cli("apply", "--incoming", str(self.incoming),
                                "--store", str(self.store), "--manifest", str(manifest))
            self.assertEqual(proc.returncode, 2, text)
        manifest.write_text("", encoding="utf-8")
        listed = self.base / "unreadable.txt"
        listed.write_text(UNICODE_KEY + "\n", encoding="utf-8")
        proc = self.run_cli("apply", "--incoming", str(self.incoming), "--store",
                            str(self.store), "--manifest", str(manifest),
                            "--unreadable", str(listed))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(self.index("rejected"), [])


class EnvelopeTests(SinkCase):
    """A bad envelope rejects the whole object, as `bad-envelope`."""

    def assert_rejected(self, doc=None, raw=None):
        self.put(KEY, doc, raw=raw)
        proc = self.apply()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.events(), [], "nothing from a rejected object is written")
        self.assertEqual(self.index("ingested"), [])
        self.assertEqual(self.index("rejected"), [f"{KEY} bad-envelope v4"])
        self.assertIn("rejected by reason: bad-envelope 1", proc.stdout)

    def test_control_the_valid_object_is_accepted(self):
        self.put(KEY, drop())
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(self.index("rejected"), [])
        self.assertEqual(len(self.index("ingested")), 1)

    def test_an_extra_top_level_key(self):
        self.assert_rejected(drop(extra=1))

    def test_a_missing_top_level_key(self):
        doc = drop()
        del doc["sent"]
        self.assert_rejected(doc)

    def test_wrong_version(self):
        self.assert_rejected(drop(v=True))

    def test_wrong_kind(self):
        self.assert_rejected(drop(kind="usage"))

    def test_bad_sent(self):
        self.assert_rejected(drop(sent="2026-09-02T10:10:00.5Z"))

    def test_two_guidance_records(self):
        self.assert_rejected(drop([guidance(), guidance(session=SID2)]))

    def test_skills_not_a_list(self):
        self.assert_rejected(drop(skills={"a": 1}))

    def test_a_duplicated_json_key(self):
        text = json.dumps(drop(), separators=(",", ":"))
        self.assert_rejected(raw=('{"v":1,' + text[1:]).encode())

    def test_not_json(self):
        self.assert_rejected(raw=b'{"v": NaN}')

    def test_not_utf8(self):
        self.assert_rejected(raw=b"\xff\xfe")

    def test_too_large(self):
        self.assert_rejected(raw=b" " * (sink.SIZE_CAP + 1))


class PartialTests(SinkCase):
    """With a valid envelope, bad records are dropped and the rest kept."""

    def test_one_bad_skill_line_keeps_the_rest(self):
        body = self.put(KEY, drop(None, [skill(), skill(id="toolu_marker_02", v=2)])).read_bytes()
        proc = self.apply()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("1 ingested (1 partial, 1 invalid records dropped)", proc.stdout)
        self.assertEqual([r["id"] for r in census.cloud_skill_records(self.store)],
                         ["toolu_marker_01"])
        self.assertEqual(census.cloud_guidance_tally(self.store, NOW, 8)["records_scanned"], 1)
        self.assertEqual(self.index("ingested"),
                         [f"{KEY} {hashlib.sha256(body).hexdigest()} partial=1"])
        self.assertEqual(self.index("rejected"), [])

    def test_a_bad_guidance_record_keeps_the_skill_lines(self):
        self.put(KEY, drop([guidance(note="x")]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(self.events(), [f"events/2026-09/cloud-skills/{SID}.jsonl"])
        self.assertTrue(self.index("ingested")[0].endswith(" partial=1"))

    def test_drifted_surface_and_cli_lose_only_that_record(self):
        self.put(KEY, drop([guidance(surface="remote projects", cli="2.1.312 (x)")]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(len(census.cloud_skill_records(self.store)), 2)

    def test_every_record_bad_is_ingested_with_nothing_written(self):
        self.put(KEY, drop([guidance(remote=False)], [skill(machine="box"), "x"]))
        proc = self.apply()
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self.events(), [])
        self.assertTrue(self.index("ingested")[0].endswith(" partial=3"))

    def test_guidance_value_shapes(self):
        bad = [guidance(remote=False), guidance(session="0123"), guidance(state="partial"),
               guidance(session="٠" * 16),
               guidance(ts="2026-09-02T10:00:00.123Z"), guidance(repos=-1),
               guidance(repos=True), guidance(check_reported="maybe"),
               guidance(registry_sha="e" * 40), guidance(guidance_version="xyz"),
               guidance(check_expected=False), guidance(cli="not a version"),
               guidance(cli="2.١.3"),
               guidance(state="unknown", repos=0, check_expected=True,
                        check_reported="absent"),
               guidance(sources=None), guidance(sources_dropped=None),
               guidance(sources=[{"registry": "a/b", "ref": "e" * 40, "x": 1}]),
               guidance(sources=[{"registry": "b/b", "ref": "e" * 40},
                                 {"registry": "a/b", "ref": "e" * 40}]),
               guidance(sources=[{"registry": "a/b", "ref": "e" * 40}] * 17)]
        for record in bad:
            self.assertFalse(sink.guidance_record_ok(record), record)
        good = [guidance(), guidance(sources=None, sources_dropped=None),
                guidance(state="unknown", repos=0, check_expected=None,
                         check_reported="absent", surface=None, cli=None,
                         guidance_version=None),
                guidance(check_expected=False, check_reported="none", sources=[])]
        for record in good:
            self.assertTrue(sink.guidance_record_ok(record), record)
        self.assertFalse(sink.skill_line_ok(skill(id="toolu_١")))
        self.assertTrue(sink.skill_line_ok(skill()))


class BackdatingTests(SinkCase):
    """A record's ts must be within 48 h before, 10 min after LastModified."""

    def test_window_edges(self):
        def at(delta):
            return (MODIFIED_AT + delta).strftime("%Y-%m-%dT%H:%M:%SZ")
        inside = [timedelta(hours=-48), timedelta(hours=-47), timedelta(minutes=9),
                  timedelta(minutes=10)]
        outside = [timedelta(hours=-48, seconds=-1), timedelta(days=-27),
                   timedelta(minutes=10, seconds=1), timedelta(days=1)]
        for delta in inside:
            self.assertTrue(sink.guidance_record_ok(guidance(ts=at(delta)), MODIFIED_AT))
            self.assertTrue(sink.skill_line_ok(skill(ts=at(delta)), MODIFIED_AT))
        for delta in outside:
            self.assertFalse(sink.guidance_record_ok(guidance(ts=at(delta)), MODIFIED_AT))
            self.assertFalse(sink.skill_line_ok(skill(ts=at(delta)), MODIFIED_AT))

    def test_a_backdated_record_is_dropped_at_apply(self):
        self.put(KEY, drop([guidance(ts="2026-08-06T10:00:00Z")],
                           [skill(), skill(id="toolu_marker_02", ts="2026-09-02T10:30:00Z")]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(census.cloud_guidance_tally(self.store, NOW, 8)["records_scanned"], 0)
        self.assertEqual([r["id"] for r in census.cloud_skill_records(self.store)],
                         ["toolu_marker_01"])
        self.assertTrue(self.index("ingested")[0].endswith(" partial=2"))


class VersionTests(SinkCase):

    def test_an_older_rejection_is_applied_again(self):
        self.write_index("rejected", f"{KEY} bad-skill-record", f"{KEY2} bad-envelope v1")
        self.put(KEY, drop())
        self.put(KEY2, drop(None, [], extra=1))
        proc = self.apply()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("1 already recorded", proc.stdout)
        self.assertEqual([line.split(" ")[0] for line in self.index("ingested")], [KEY])
        self.assertEqual(self.index("rejected"),
                         [f"{KEY} bad-skill-record", f"{KEY2} bad-envelope v1"])
        self.assertEqual(sink.VALIDATOR_VERSION, 4)


class DedupeTests(SinkCase):

    def test_a_guidance_session_already_in_any_month_is_not_appended(self):
        other = self.store / "events/2026-08/cloud-guidance.jsonl"
        other.parent.mkdir(parents=True)
        other.write_text(json.dumps(guidance(ts="2026-08-30T00:00:00Z")) + "\n")
        self.put(KEY, drop(None, []))
        self.put(KEY2, drop([guidance(session=SID2)], []))
        self.assertEqual(self.apply().returncode, 0)
        added = (self.store / "events/2026-09/cloud-guidance.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(line)["session"] for line in added], [SID2])
        self.assertEqual(len(self.index("ingested")), 2)
        self.assertNotIn("partial", "".join(self.index("ingested")))

    def test_a_skill_id_already_in_its_shard_is_not_appended(self):
        shard = self.store / f"events/2026-09/cloud-skills/{SID}.jsonl"
        shard.parent.mkdir(parents=True)
        before = json.dumps(skill(), separators=(",", ":")) + "\n"
        shard.write_text(before)
        self.put(KEY, drop([], [skill(), skill(id="toolu_marker_02")]))
        self.put(KEY2, drop([], [skill(id="toolu_marker_02")]))
        self.assertEqual(self.apply().returncode, 0)
        text = shard.read_text()
        self.assertTrue(text.startswith(before), "existing lines are kept byte for byte")
        self.assertEqual([json.loads(line)["id"] for line in text.splitlines()],
                         ["toolu_marker_01", "toolu_marker_02"])

    def test_a_second_apply_changes_nothing(self):
        self.put(KEY, drop())
        self.put(KEY2, drop(extra=1))
        self.put(KEY3, drop(None, [skill(v=2)]))
        self.assertEqual(self.apply(unreadable=["drop/2026-09-02/" + "9" * 32 + ".json"])
                         .returncode, 0)
        first = tree_digest(self.store)
        proc = self.apply(unreadable=["drop/2026-09-02/" + "9" * 32 + ".json"])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0 ingested", proc.stdout)
        self.assertIn("0 rejected, 4 already recorded", proc.stdout)
        self.assertEqual(tree_digest(self.store), first)

    def test_an_interrupted_run_is_finished_without_doubling(self):
        self.put(KEY, drop())
        self.assertEqual(self.apply().returncode, 0)
        # Lose the index line, as if the run died after the data was written.
        (self.store / "sink/ingested/2026-09.txt").unlink()
        events = {p: p.read_bytes() for p in (self.store / "events").rglob("*.jsonl")}
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual({p: p.read_bytes() for p in events}, events)
        self.assertEqual(len(self.index("ingested")), 1)


class LinkTests(SinkCase):

    def test_a_linked_month_directory_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.store / "events").mkdir()
        os.symlink(outside, self.store / "events" / "2026-09")
        self.put(KEY, drop())
        self.assertEqual(self.apply().returncode, 1)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(self.index("ingested"), [])

    def test_a_linked_store_file_is_refused(self):
        target = self.base / "target.jsonl"
        target.write_text("")
        shard = self.store / f"events/2026-09/cloud-skills/{SID}.jsonl"
        shard.parent.mkdir(parents=True)
        os.symlink(target, shard)
        self.put(KEY, drop([], None))
        self.assertEqual(self.apply().returncode, 1)
        self.assertEqual(target.read_text(), "")

    def test_a_linked_index_directory_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.store / "sink").mkdir()
        os.symlink(outside, self.store / "sink" / "rejected")
        self.put(KEY, drop(extra=1))
        self.assertEqual(self.apply().returncode, 1)
        self.assertEqual(list(outside.iterdir()), [])

    def test_linked_incoming_entries_and_other_names_are_ignored(self):
        real = self.base / "real.json"
        real.write_text(json.dumps(drop()))
        (self.incoming / "drop" / "2026-09-02").mkdir(parents=True)
        os.symlink(real, self.incoming / KEY)
        self.manifest[KEY] = MODIFIED
        self.put("drop/2026-09-02/readme.txt", raw=b"x", listed=False)
        self.put("other.json", drop(), listed=False)
        self.put(UNICODE_KEY, drop(), listed=False)
        proc = self.apply()
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0 objects read", proc.stdout)
        self.assertIn("1 planned but missing", proc.stdout)
        self.assertIn("4 other entries ignored", proc.stdout)
        self.assertEqual(self.events(), [])
        self.assertEqual(self.index("ingested") + self.index("rejected"), [])

    def test_missing_directories_exit_two(self):
        manifest = self.base / "manifest.txt"
        manifest.write_text("")
        proc = self.run_cli("apply", "--incoming", str(self.base / "none"),
                            "--store", str(self.store), "--manifest", str(manifest))
        self.assertEqual(proc.returncode, 2)


class HookLineTests(SinkCase):
    """The optional `hooks` list of the envelope: cloud agent-checks runs."""

    def stored(self, session=SID, month="2026-09"):
        path = self.store / f"events/{month}/cloud-hooks/{session}.jsonl"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def test_an_envelope_without_hooks_is_still_accepted(self):
        self.put(KEY, drop())
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(self.index("rejected"), [])
        self.assertEqual(self.stored(), [])
        self.assertEqual([e for e in self.events() if "cloud-hooks" in e], [])

    def test_hooks_reach_the_census_reader_and_are_stored_as_sent(self):
        runs = [hook(), hook(id="fedcba9876543210", event="pre-push", repo=None,
                            checks=[], failed=[], runner=None)]
        self.put(KEY, drop(None, [], hooks=runs))
        proc = self.apply()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("2 hook lines added", proc.stdout)
        self.assertEqual(self.stored(),
                         [json.dumps(r, separators=(",", ":")) for r in runs])
        self.assertEqual([r["id"] for r in census.cloud_hook_records(self.store)],
                         ["0123456789abcdef", "fedcba9876543210"])
        self.assertEqual(self.index("rejected"), [])
        self.assertNotIn("partial", "".join(self.index("ingested")))

    def test_an_empty_hooks_list_is_valid(self):
        self.put(KEY, drop(None, [], hooks=[]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(len(self.index("ingested")), 1)

    def test_a_hook_id_already_in_its_shard_is_not_appended_again(self):
        self.put(KEY, drop(None, [], hooks=[hook()]))
        self.put(KEY2, drop(None, [], hooks=[hook(), hook(id="fedcba9876543210")]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual([json.loads(line)["id"] for line in self.stored()],
                         ["0123456789abcdef", "fedcba9876543210"])

    def test_a_rerun_changes_no_byte(self):
        self.put(KEY, drop(None, [], hooks=[hook()]))
        self.assertEqual(self.apply().returncode, 0)
        before = tree_digest(self.store)
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(tree_digest(self.store), before)

    def test_hooks_file_under_their_own_month_and_session(self):
        self.put(KEY, drop(None, [], hooks=[
            hook(), hook(id="1111111111111111", session=SID2),
            hook(id="2222222222222222", ts="2026-08-31T23:00:00Z")]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(len(self.stored()), 1)
        self.assertEqual(len(self.stored(SID2)), 1)
        self.assertEqual(len(self.stored(month="2026-08")), 1)

    def test_a_bad_hook_line_loses_only_itself(self):
        bad = [hook(extra=1), hook(kind="skill"), hook(surface="local"),
               hook(v=2), hook(id="short"), hook(session="nope"), hook(event="ci"),
               hook(repo="not a repo"), hook(checks="x"), hook(runner="ABCDEF012345"),
               hook(failed=["other-check"]), hook(checks=["Bad_Id"], failed=[]),
               hook(checks=["a", "a"], failed=[]), hook(ts="2026-09-02T10:06:00.5Z"),
               hook(checks=[f"c{i}" for i in range(65)], failed=[]), "text", 7, None]
        self.put(KEY, drop(None, [], hooks=[hook(id="aaaaaaaaaaaaaaaa"), *bad]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual([json.loads(line)["id"] for line in self.stored()],
                         ["aaaaaaaaaaaaaaaa"])
        self.assertTrue(self.index("ingested")[0].endswith(f" partial={len(bad)}"))

    def test_a_missing_key_is_invalid(self):
        line = hook()
        del line["runner"]
        self.put(KEY, drop(None, [], hooks=[line]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(self.stored(), [])

    def test_non_ascii_digits_and_ids_are_invalid(self):
        self.put(KEY, drop(None, [], hooks=[
            hook(ts="2026-09-02T10:06:00Z".replace("2026", "\u0662\u0660\u0662\u0666")),
            hook(session="\u0660" * 16), hook(id="\u0660" * 16),
            hook(checks=["r\u00fcles"], failed=[])]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(self.stored(), [])

    def test_hooks_must_be_a_list(self):
        for bad in (None, {}, "x", 3):
            with self.subTest(hooks=bad):
                self.setUp()
                self.put(KEY, drop(None, [], hooks=bad))
                self.assertEqual(self.apply().returncode, 0)
                self.assertEqual(self.index("rejected"), [f"{KEY} bad-envelope v4"])
                self.assertEqual(self.events(), [])

    def test_hooks_beyond_the_cap_are_dropped(self):
        lines = [hook(id=f"{i:016x}") for i in range(sink.MAX_HOOKS + 3)]
        guidance_records, skills, kept, setups, dropped = sink.split_records(
            drop(None, [], hooks=lines), MODIFIED_AT)
        self.assertEqual((len(kept), dropped), (sink.MAX_HOOKS, 3))

    def test_ts_is_held_to_last_modified_like_the_other_records(self):
        def at(delta):
            return (MODIFIED_AT + delta).strftime("%Y-%m-%dT%H:%M:%SZ")
        for delta in (timedelta(hours=-48), timedelta(minutes=10)):
            self.assertTrue(sink.hook_line_ok(hook(ts=at(delta)), MODIFIED_AT))
        for delta in (timedelta(hours=-48, seconds=-1), timedelta(minutes=10, seconds=1)):
            self.assertFalse(sink.hook_line_ok(hook(ts=at(delta)), MODIFIED_AT))

    def test_no_hook_content_reaches_stdout_or_stderr(self):
        self.put(KEY, drop(None, [], hooks=[hook(), hook(extra="marker-skill")]))
        proc = self.apply()
        self.assertEqual(proc.stderr, "")
        self.assertNotIn(SID, proc.stdout)
        self.assertNotIn("example/repo", proc.stdout)


class SetupRecordTests(SinkCase):
    """The optional `setups` list of the envelope: cloud setup-script runs."""

    def stored(self, month="2026-09"):
        path = self.store / f"events/{month}/cloud-setup.jsonl"
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    def setup_only(self, *records):
        return drop([], [], setups=list(records))

    def test_a_setup_only_envelope_is_ingested(self):
        self.put(KEY, self.setup_only(setup()))
        proc = self.apply()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("1 setup records added", proc.stdout)
        self.assertEqual(self.stored(), [json.dumps(setup(), separators=(",", ":"))])
        self.assertEqual(self.events(), ["events/2026-09/cloud-setup.jsonl"])
        self.assertEqual(self.index("rejected"), [])
        self.assertNotIn("partial", "".join(self.index("ingested")))

    def test_empty_optional_values_are_valid(self):
        record = setup(launcher_sha256="", script_commit="", fleet_pin_commit="",
                       fleet_guidance_commit="", fleet_guidance="", script_source="download")
        self.put(KEY, self.setup_only(record))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(len(self.stored()), 1)

    def test_a_failed_guidance_install_is_a_valid_state(self):
        self.put(KEY, self.setup_only(setup(fleet_guidance="failed", fleet_guidance_commit="")))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(len(self.stored()), 1)

    def test_a_version_3_envelope_still_passes(self):
        self.put(KEY, drop(None, [], hooks=[hook()]))
        self.put(KEY2, drop())
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(self.index("rejected"), [])
        self.assertEqual(self.stored(), [])

    def test_setups_beside_guidance_skills_and_hooks(self):
        self.put(KEY, drop(None, None, hooks=[hook()], setups=[setup()]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(len(self.stored()), 1)
        self.assertEqual(self.index("rejected"), [])

    def test_the_same_id_is_not_appended_again_and_a_rerun_changes_no_byte(self):
        self.put(KEY, self.setup_only(setup()))
        self.put(KEY2, self.setup_only(setup(), ) | {"sent": "2026-09-02T10:10:01Z"})
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(len(self.stored()), 1)
        before = tree_digest(self.store)
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(tree_digest(self.store), before)

    def test_files_under_the_month_of_its_ts(self):
        self.put(KEY, self.setup_only(setup(ts="2026-08-31T23:00:00Z")))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(len(self.stored("2026-08")), 1)
        self.assertEqual(self.stored(), [])

    def test_each_bad_record_is_dropped_and_counted(self):
        missing = setup()
        del missing["fleet_guidance"]
        far = (MODIFIED_AT - timedelta(hours=48, seconds=1)).strftime(sink.ISO)
        cases = {
            "short id": setup(id="a" * 31), "uppercase id": setup(id="A" * 32),
            "short script sha": setup(script_sha256="b" * 63),
            "uppercase sha": setup(script_sha256="B" * 64),
            "bad launcher sha": setup(launcher_sha256="a" * 40),
            "short commit": setup(script_commit="c" * 39),
            "uppercase commit": setup(fleet_pin_commit="D" * 40),
            "long guidance commit": setup(fleet_guidance_commit="e" * 64),
            "extra key": setup(extra=1), "missing key": missing,
            "bool launcher_version": setup(launcher_version=True),
            "zero launcher_version": setup(launcher_version=0),
            "big launcher_version": setup(launcher_version=10000),
            "str launcher_version": setup(launcher_version="3"),
            "bad source": setup(script_source="cache"),
            "bad guidance state": setup(fleet_guidance="full"),
            "non-ascii digits": setup(ts="\u0662\u0660\u0662\u0666-09-02T10:07:00Z"),
            "ts far before": setup(ts=far),
            "ts after": setup(ts="2026-09-02T10:21:00Z"),
            "fractional ts": setup(ts="2026-09-02T10:07:00.5Z"),
            "not a dict": "text", "null": None}
        for name, bad in cases.items():
            with self.subTest(name):
                self.assertFalse(sink.setup_record_ok(bad, MODIFIED_AT))
        self.assertTrue(sink.setup_record_ok(setup(), MODIFIED_AT))
        self.assertTrue(sink.setup_record_ok(setup()))
        for name, bad in cases.items():
            with self.subTest(name, end_to_end=True):
                self.setUp()
                self.put(KEY, self.setup_only(bad))
                self.assertEqual(self.apply().returncode, 0)
                self.assertEqual(self.stored(), [])
                self.assertEqual(self.events(), [])
                self.assertTrue(self.index("ingested")[0].endswith(" partial=1"))
                self.assertEqual(self.index("rejected"), [])

    def test_a_bad_record_loses_only_itself(self):
        self.put(KEY, drop([], [], setups=[setup(extra=1)]) | {"hooks": [hook()]})
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(self.stored(), [])
        self.assertTrue(self.index("ingested")[0].endswith(" partial=1"))
        self.assertEqual(len([e for e in self.events() if "cloud-hooks" in e]), 1)

    def test_more_than_one_setup_rejects_the_envelope(self):
        self.put(KEY, self.setup_only(setup(), setup(id="1" * 32)))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(self.index("rejected"), [f"{KEY} bad-envelope v4"])
        self.assertEqual(self.events(), [])

    def test_setups_must_be_a_list(self):
        for bad in (None, {}, "x", 3):
            with self.subTest(setups=bad):
                self.setUp()
                self.put(KEY, drop([], [], setups=bad))
                self.assertEqual(self.apply().returncode, 0)
                self.assertEqual(self.index("rejected"), [f"{KEY} bad-envelope v4"])
                self.assertEqual(self.events(), [])

    def test_an_empty_setups_list_is_valid(self):
        self.put(KEY, drop([], [], setups=[]))
        self.assertEqual(self.apply().returncode, 0)
        self.assertEqual(len(self.index("ingested")), 1)

    def test_a_linked_setup_file_is_refused(self):
        target = self.base / "elsewhere.jsonl"
        target.write_text("")
        month = self.store / "events" / "2026-09"
        month.mkdir(parents=True)
        (month / "cloud-setup.jsonl").symlink_to(target)
        self.put(KEY, self.setup_only(setup()))
        self.assertEqual(self.apply().returncode, 1)
        self.assertEqual(target.read_text(), "")
        self.assertEqual(self.index("ingested"), [])

    def test_no_setup_content_reaches_stdout_or_stderr(self):
        self.put(KEY, self.setup_only(setup(script_commit="marker-skill")))
        proc = self.apply()
        self.assertEqual(proc.stderr, "")
        self.assertNotIn("0123456789abcdef0123", proc.stdout)


class OutputTests(SinkCase):

    def test_no_record_content_reaches_stdout_or_stderr(self):
        self.put(KEY, drop())
        self.put(KEY2, drop(None, [skill(), skill(id="toolu_marker_02", extra="x")]))
        self.put(KEY3, drop([guidance(surface="remote_marker extra")], []),
                 modified="2026-09-02T10:10:30Z")
        proc = self.apply()                 # apply() asserts every marker is absent
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(len(proc.stdout.splitlines()), 1)
        for text in (KEY, KEY2, KEY3, SID):
            self.assertNotIn(text, proc.stdout)


if __name__ == "__main__":
    unittest.main()
