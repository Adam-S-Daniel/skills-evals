#!/usr/bin/env python3
"""Adam, 2026-11-12: a skill nobody uses is removed once the context its
description cost passes the value of one use (evals/removal-policy.yml,
harness/removal_policy.py), by scripts/retire_skill.py with reason `unused`.

  * the policy file: its validation and the committed numbers;
  * the threshold and the decision (`unused_removal`): a worked number, the
    floor and coverage requirement, exemptions, local-only skills, any use,
    truncated listings and basename normalization;
  * the removal pull request: the same flow as a `retire` verdict, a body
    that states the figures and the restore command, one removal per run,
    and the `retire` verdict's priority;
  * `--withdraw-stale`: an unused removal is kept while the skill stays
    unused, withdrawn once it is used or exempt, and kept when the census is
    unknown.

Hermetic: hand-written census documents, registries in a temporary directory,
a fake `gh`; no network, no clock.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "test"))

import removal_policy  # noqa: E402
import retire_skill  # noqa: E402
import skill_usage  # noqa: E402
import test_issue_70_retire as t70  # noqa: E402
import test_issue_removal_withdrawal as tw  # noqa: E402

AS_OF = "20261025T120000Z"  # a Sunday in ISO week 2026-W43
NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)
WEEK = "2026-W43"
#: The Monday that starts the 8-week floor window W36 to W43.
FLOOR_START = "2026-08-31"
POLICY = removal_policy.load()
CLOUD, LOCAL = skill_usage.SURFACE_CLOUD, skill_usage.SURFACE_LOCAL
BOTH = (LOCAL, CLOUD)
SKILL = t70.SKILL
KEPT = t70.KEPT


def body_for(d: int) -> str:
    """A SKILL.md whose name and description are exactly 4 * d bytes."""
    name = "example-skill"
    return f"---\nname: {name}\ndescription: {'x' * (4 * d - len(name))}\n---\nBody.\n"


def census(*, cloud=0, local=0, truncated=0, uses=(), cloud_from=None, generated=NOW,
           cloud_source=True, recorded=True, keys=(SKILL, KEPT)):
    """A usage document whose 8-week window holds `local` full local listings,
    `truncated` cut ones and `cloud` cloud sessions, plus a `skill` row per
    (name, count) in `uses`. Both surfaces are counted from long before the
    window unless `cloud_from` says otherwise. `recorded` says the cloud records
    carried the install and listing fields (else cloud exposure is unknown);
    `keys` are the skill names the census tracks."""
    floor = NOW - timedelta(weeks=20)
    rows = [skill_usage.row(WEEK, "skill", name, count, 1) for name, count in uses]
    if local:
        rows.append(skill_usage.listing_row(WEEK, "full", local))
    if truncated:
        rows.append(skill_usage.listing_row(WEEK, "truncated", truncated))
    if cloud:
        rows.append(skill_usage.listing_row(WEEK, "full", cloud, CLOUD))
    doc = skill_usage.document(
        rows, generated, floor, sessions_scanned=1,
        cloud_guidance={"from": floor, "records_scanned": 1, "listing_recorded": recorded},
        skill_keys=list(keys))
    if cloud_source:
        skill_usage.add_rows(doc, [], skill_usage.digest_source(
            cloud_from or floor, generated, 0, surface=CLOUD))
    return doc


def decide(doc, *, d=100, surfaces=BOTH, exempt=(), policy=None, skill=SKILL):
    return removal_policy.unused_removal(policy or POLICY, doc, skill, surfaces, d, NOW,
                                         set(exempt))


class PolicyFileTests(unittest.TestCase):
    GOOD = ("value_per_use_usd: 10\nprefix_tokens: 119000\nreread_usd_per_session:\n"
            "  cloud: 3.50\n  local: 0.81\nfloor_weeks: 8\nlocal_removal: false\n")

    def test_the_committed_numbers(self):
        self.assertEqual(POLICY, {
            "value_per_use_usd": 10, "prefix_tokens": 119000,
            "reread_usd_per_session": {"cloud": 3.50, "local": 0.81},
            "floor_weeks": 8, "local_removal": False})

    def test_a_missing_negative_or_wrong_typed_key_is_refused(self):
        bad = [self.GOOD.replace("value_per_use_usd: 10\n", ""),
               self.GOOD.replace("prefix_tokens: 119000\n", ""),
               self.GOOD.replace("floor_weeks: 8\n", ""),
               self.GOOD.replace("local_removal: false\n", ""),
               self.GOOD.replace("value_per_use_usd: 10", "value_per_use_usd: -1"),
               self.GOOD.replace("value_per_use_usd: 10", "value_per_use_usd: 0"),
               self.GOOD.replace("value_per_use_usd: 10", "value_per_use_usd: ten"),
               self.GOOD.replace("value_per_use_usd: 10", "value_per_use_usd: true"),
               self.GOOD.replace("prefix_tokens: 119000", "prefix_tokens: 1.5"),
               self.GOOD.replace("prefix_tokens: 119000", "prefix_tokens: -5"),
               self.GOOD.replace("cloud: 3.50", "cloud: -3.5"),
               self.GOOD.replace("cloud: 3.50", "cloud: 0"),
               self.GOOD.replace("  cloud: 3.50\n", ""),
               self.GOOD.replace("floor_weeks: 8", "floor_weeks: 0"),
               self.GOOD.replace("floor_weeks: 8", "floor_weeks: 8.5"),
               self.GOOD.replace("local_removal: false", "local_removal: no-way"),
               self.GOOD + "surprise: 1\n",
               "- a list\n", ""]
        for text in bad:
            with self.subTest(text=text):
                with self.assertRaises(removal_policy.PolicyError):
                    removal_policy.parse(text)
        self.assertEqual(removal_policy.parse(self.GOOD), POLICY)

    def test_an_unreadable_file_is_refused(self):
        with self.assertRaises(removal_policy.PolicyError):
            removal_policy.load(ROOT / "evals" / "no-such-policy.yml")


class DescriptionTokensTests(unittest.TestCase):
    def test_ceil_of_a_quarter_of_the_name_and_description_bytes(self):
        self.assertEqual(removal_policy.description_tokens(body_for(100)), 100)
        text = "---\nname: abc\ndescription: defgh\n---\nbody\n"
        self.assertEqual(removal_policy.description_tokens(text), 2)  # 8 bytes
        text = "---\nname: abc\ndescription: defghi\n---\nbody\n"
        self.assertEqual(removal_policy.description_tokens(text), 3)  # 9 bytes

    def test_the_frontmatter_is_parsed_not_scanned(self):
        text = ("---\nname: abcd\ndescription: >\n  folded text\n  over lines\nother: ignored "
                "because it is long\n---\nname: not this\ndescription: nor this\n")
        # "abcd" (4) + "folded text over lines\n" (23): 27 bytes -> 7 tokens.
        self.assertEqual(removal_policy.description_tokens(text), 7)

    def test_multibyte_text_counts_bytes(self):
        text = "---\nname: ab\ndescription: \"éééé\"\n---\n"  # 2 + 8 bytes
        self.assertEqual(removal_policy.description_tokens(text), 3)

    def test_a_skill_without_a_readable_frontmatter_is_refused(self):
        for text in ("no frontmatter", "---\nname: a\n---\n", "---\nname: [\n---\n",
                     "---\nname: a\ndescription: b\n", "---\n- list\n---\n", ""):
            with self.subTest(text=text):
                with self.assertRaises(removal_policy.PolicyError):
                    removal_policy.description_tokens(text)


class ThresholdTests(unittest.TestCase):
    def test_the_worked_number(self):
        # d = 100 on cloud: 10 * 119000 / (100 * 3.5) = 3400.
        self.assertEqual(removal_policy.threshold(POLICY, 100, CLOUD), 3400)
        self.assertAlmostEqual(removal_policy.threshold(POLICY, 100, LOCAL),
                               10 * 119000 / (100 * 0.81))

    def test_a_longer_description_reaches_the_value_sooner(self):
        self.assertEqual(removal_policy.threshold(POLICY, 200, CLOUD), 1700)

    def test_bad_arguments_are_refused(self):
        for d, surface in ((0, CLOUD), (-1, CLOUD), (1.5, CLOUD), (100, "web")):
            with self.assertRaises(removal_policy.PolicyError):
                removal_policy.threshold(POLICY, d, surface)


class UnusedRemovalTests(unittest.TestCase):
    def test_removed_at_the_threshold_and_not_one_session_before(self):
        at = decide(census(cloud=3400))
        self.assertTrue(at["remove"], at["why"])
        self.assertEqual((at["uses"], at["exposure"], at["d"]),
                         (0, {"local": 0, "cloud": 3400}, 100))
        self.assertEqual(at["threshold"]["cloud"], 3400)
        self.assertAlmostEqual(at["accrued_usd"], 10.0)
        self.assertFalse(decide(census(cloud=3399))["remove"])

    def test_removal_keeps_its_exposure_rule_though_the_eval_pause_has_none(self):
        """2026-11-13: evals wait for a first use with no exposure minimum
        (`has_recorded_use`), but the irreversible removal still needs the
        500-session and accrued-cost evidence (`zero_use`)."""
        few = census(cloud=100, local=100)
        self.assertIs(skill_usage.has_recorded_use(few, SKILL, NOW), False)
        self.assertIsNone(skill_usage.zero_use(few, SKILL, NOW, surfaces=BOTH))
        self.assertFalse(decide(few)["remove"])

    def test_the_cost_adds_up_across_surfaces(self):
        # 1800 cloud sessions cost 5.29 and 7000 local ones 4.76: together over 10.
        both = decide(census(cloud=1800, local=7000))
        self.assertTrue(both["remove"], both["why"])
        self.assertFalse(decide(census(cloud=1800, local=6000))["remove"])
        self.assertFalse(decide(census(cloud=1800))["remove"])

    def test_any_use_blocks_whatever_the_exposure(self):
        got = decide(census(cloud=10 ** 6, uses=[(SKILL, 1)]))
        self.assertFalse(got["remove"])
        self.assertEqual(got["uses"], 1)

    def test_a_use_under_a_plugin_prefix_blocks(self):
        got = decide(census(cloud=10 ** 6, uses=[(f"adam-coding-anywhere:{SKILL}", 2)]))
        self.assertEqual((got["remove"], got["uses"]), (False, 2))

    def test_a_use_outside_the_floor_window_does_not_block(self):
        doc = census(cloud=3400)
        doc["rows"].append(skill_usage.row("2026-W30", "skill", SKILL, 5, 1))
        self.assertTrue(decide(doc)["remove"])

    def test_truncated_listings_are_not_exposure(self):
        got = decide(census(local=100, truncated=10 ** 6, cloud=0),
                     policy={**POLICY, "local_removal": True}, surfaces=(LOCAL,))
        self.assertEqual(got["exposure"], {"local": 100})
        self.assertFalse(got["remove"])

    def test_unknown_cloud_exposure_blocks_removal_but_not_a_pause(self):
        """Records without the install and listing fields: cloud exposure is
        unknown, so a cloud-reaching skill is not removed however many sessions
        there were; the reversible pause still rests on local exposure."""
        doc = census(cloud=10 ** 6, local=10 ** 7, recorded=False)
        self.assertIsNone(skill_usage.exposure_by_surface(doc, NOW)["cloud"])
        got = decide(doc)
        self.assertFalse(got["remove"])
        self.assertIn("cloud surface is unknown", got["why"])
        self.assertIs(skill_usage.zero_use(doc, SKILL, NOW, surfaces=BOTH), True)
        # Local-only with local removal on never looks at cloud exposure.
        self.assertTrue(decide(doc, surfaces=(LOCAL,),
                               policy={**POLICY, "local_removal": True})["remove"])

    def test_a_census_that_stops_before_the_window_ends_removes_nothing(self):
        old = (NOW - timedelta(days=1, minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertTrue(decide(census(cloud=10 ** 6))["remove"])
        for index in range(len(census(cloud=1)["sources"])):
            doc = census(cloud=10 ** 6)
            scope = doc["sources"][index]["scope"]
            doc["sources"][index]["to"] = old
            with self.subTest(source=scope):
                got = decide(doc)
                self.assertFalse(got["remove"])
                self.assertIn("within 1 day", got["why"])
        # generated_at is one of the dates the census must end near.
        got = decide(census(cloud=10 ** 6, generated=NOW - timedelta(days=2)))
        self.assertFalse(got["remove"])
        self.assertIn("within 1 day", got["why"])
        # A pause is reversible: zero_use still accepts a census 2 days old.
        self.assertIs(skill_usage.zero_use(
            census(local=600, generated=NOW - timedelta(days=2)), SKILL, NOW,
            surfaces=(LOCAL,)), True)

    def test_a_skill_the_census_does_not_track_is_not_zero_use_or_removable(self):
        doc = census(cloud=10 ** 6, local=600, keys=(KEPT,))
        got = decide(doc)
        self.assertFalse(got["remove"])
        self.assertIn("does not track it by name", got["why"])
        self.assertIsNone(skill_usage.zero_use(doc, SKILL, NOW))
        # An older document with no list cannot say either.
        del doc["sources"][0]["skill_keys"]
        self.assertFalse(decide(doc)["remove"])
        self.assertIsNone(skill_usage.zero_use(doc, SKILL, NOW))
        self.assertIs(skill_usage.zero_use(census(local=600), SKILL, NOW), True)

    def test_the_census_must_cover_the_floor_on_every_surface(self):
        # Cloud counts from the week after its `from`: 2026-08-31 + 7 days is
        # after the window's first Monday, 2026-08-31.
        late = census(cloud=10 ** 6, cloud_from=datetime(2026, 8, 31, tzinfo=timezone.utc))
        got = decide(late)
        self.assertFalse(got["remove"])
        self.assertIn(FLOOR_START, got["why"])
        # One week earlier it covers the floor exactly.
        early = census(cloud=10 ** 6, cloud_from=datetime(2026, 8, 24, tzinfo=timezone.utc))
        self.assertTrue(decide(early)["remove"])
        self.assertFalse(decide(census(cloud=10 ** 6, cloud_source=False))["remove"])

    def test_the_floor_window_comes_from_the_policy(self):
        late = census(cloud=10 ** 6, cloud_from=datetime(2026, 8, 31, tzinfo=timezone.utc))
        self.assertTrue(decide(late, policy={**POLICY, "floor_weeks": 6})["remove"])

    def test_an_exempt_skill_is_never_removed(self):
        got = decide(census(cloud=10 ** 6), exempt={SKILL})
        self.assertFalse(got["remove"])
        self.assertTrue(got["exempt"])

    def test_a_local_only_skill_is_never_removed(self):
        doc = census(local=10 ** 7)
        got = decide(doc, surfaces=(LOCAL,))
        self.assertFalse(got["remove"])
        self.assertIn("local removal is off", got["why"])
        self.assertTrue(decide(doc, surfaces=(LOCAL,),
                               policy={**POLICY, "local_removal": True})["remove"])

    def test_no_census_or_a_stale_one_is_unknown_and_removes_nothing(self):
        for doc in (None, census(cloud=10 ** 6, generated=NOW - timedelta(days=15))):
            got = decide(doc)
            self.assertEqual((got["remove"], got["known"], got["uses"]), (False, False, None))

    def test_full_precision_is_kept(self):
        got = decide(census(cloud=3400, local=1))
        self.assertEqual(got["accrued_usd"],
                         3400 * 100 * 3.5 / 119000 + 1 * 100 * 0.81 / 119000)


def unused_inputs(exempt=()):
    return lambda: (POLICY, set(exempt))


class UnusedRemovalFlowTests(t70.Base):
    """The removal pull request, through the same flow as a `retire` verdict."""

    def setUp(self):
        super().setUp()
        self.set_skills({SKILL: 100, KEPT: 100})
        self.usage = self.write_usage(census(cloud=3400, uses=[(KEPT, 1)]))

    def set_skills(self, sizes):
        """Rewrite each skill's SKILL.md to a description of `sizes[skill]`
        tokens, and commit it."""
        for skill, d in sizes.items():
            path = self.registry / "plugins" / t70.PLUGIN / "skills" / skill / "SKILL.md"
            path.write_text(body_for(d).replace("example-skill", skill, 1)
                            if skill != SKILL else body_for(d))
        t70.git(self.registry, "commit", "-qam", "descriptions", "--allow-empty")

    def write_usage(self, doc):
        path = self.tmp / "usage.json"
        path.write_text(json.dumps(doc))
        return path

    def gates(self, mode="auto", **verdicts):
        return t70.gates_doc(mode, {"kept-skill": {"verdict": "keep",
                                                   "reason": "a cell shows benefit",
                                                   "cells": []}, **verdicts})

    def go(self, doc=None, *extra, usage=True, exempt=(), env=t70.AUTO_ENV, **kw):
        argv = list(extra)
        if usage:
            argv += ["--usage", str(self.usage)]
        if "--allow-mode" not in argv:
            argv += ["--allow-mode", "auto"]
        with mock.patch.object(retire_skill, "unused_inputs", unused_inputs(exempt)):
            return t70.Base.run_main(self, doc or self.gates(), *argv, env=env, **kw)

    def test_opens_the_removal_with_the_same_flow_as_a_retire_verdict(self):
        code, out, err, fake = self.go()
        self.assertEqual(code, 0, err)
        branch = f"retire-skill/{SKILL}"
        self.assertEqual(t70.git(self.registry, "branch", "--show-current").strip(), branch)
        self.assertFalse((self.registry / "plugins" / t70.PLUGIN / "skills" / SKILL).exists())
        changed = sorted(t70.git(self.registry, "diff", "--name-only", "main", "HEAD").split())
        self.assertEqual(changed, sorted([
            "docs/skill-impact.md", f"plugins/{t70.PLUGIN}/.claude-plugin/plugin.json",
            f"plugins/{t70.PLUGIN}/plugin.json",
            f"plugins/{t70.PLUGIN}/skills/{SKILL}/SKILL.md",
            "scripts/plugin_layout.json", "README.md", "skills.lock"]))
        self.assertEqual(json.loads((self.registry / "plugins" / t70.PLUGIN /
                                     "plugin.json").read_text())["version"], "2.0.0")
        self.assertEqual(fake.pushes, [(self.registry.resolve(), branch)])
        url = "https://github.com/Adam-S-Daniel/adam-agentskills/pull/999"
        writes = [args for args, _ in fake.calls if args[:2] != ["api", "--paginate"]]
        self.assertEqual(writes[0][:2], ["pr", "create"])
        self.assertIn(f"Remove {t70.PLUGIN}/{SKILL}: unused", " ".join(writes[0]))
        self.assertIn("--auto", writes[3])  # armed, after the review passed
        self.assertEqual(writes[3][:3], ["pr", "merge", url])
        self.assertIn("agent-authored", writes[5])
        self.assertEqual(len(writes), 6)
        for message in t70.git(self.registry, "log", "--format=%B%x00", "main..HEAD").split("\0"):
            if message.strip():
                self.assertTrue(message.strip().endswith("Agent: claude-code"), message)
        self.assertIn(f"{t70.PLUGIN}/{SKILL}: unused",
                      t70.git(self.registry, "log", "--format=%s", "main..HEAD"))

    def test_the_skill_impact_entry_says_unused(self):
        self.go()
        text = t70.git(self.registry, "show", "HEAD:docs/skill-impact.md")
        self.assertIn(f"## 2026-10-25 — {t70.PLUGIN}/{SKILL} — remove", text)
        self.assertIn("reason `unused`", text)
        self.assertNotIn("no benefit", text.split("## 2026-10-23")[0])
        self.assertIn("python3 scripts/restore_skill.py example-skill", text)

    def test_the_body_states_the_figures_and_how_to_restore(self):
        _, _, _, fake = self.go()
        body = next(s for a, s in fake.calls if a[:2] == ["pr", "create"])
        first = body.split("\n")[0]
        self.assertTrue(retire_skill.UNUSED_BASIS_RE.match(first), first)
        self.assertEqual(retire_skill.BASIS_RE.match(first).group(1), AS_OF)
        self.assertIsNone(retire_skill.BASIS_RE.match("Removes `x`: it is **keep** as of "
                                                      f"{AS_OF} ("))
        for text in ("cloud: 3400 full-listing session(s)", "local: 0 full-listing",
                     "N* = V x P / (d x R) = 3400 sessions", "Uses in the window: 0",
                     "(description tokens", ": 100.", "$10.00, against V = $10 for one use",
                     f"the 8 ISO weeks from {FLOOR_START}",
                     "`python3 scripts/restore_skill.py example-skill`",
                     "fresh branch from main", "bumps the plugin's MINOR version",
                     "1.2.7 -> 2.0.0", "no human review", "Adversarial-review: pass"):
            self.assertIn(text, body)
        self.assertTrue(body.endswith(retire_skill.AGENT_MARKER + "\n"))
        notice = next(s for a, s in fake.calls if a[:2] == ["issue", "create"])
        self.assertIn("as **unused**", notice)
        self.assertIn("pull/999", notice)
        self.assertIn("restore_skill.py example-skill", notice)

    def test_a_retire_verdict_has_priority_and_only_one_removal_is_opened(self):
        verdict = {"verdict": "retire", "reason": "every cell shows no benefit",
                   "removal": "auto", "removal_reason": "4 cells with headroom",
                   "cells": [t70.cell(f, m) for f in ("basic", "edge") for m in t70.MODELS]}
        # `other-skill` is the retire verdict's; example-skill is the unused one.
        self.usage = self.write_usage(census(cloud=3400))
        code, out, err, fake = self.go(self.gates(**{KEPT: verdict}))
        self.assertEqual(code, 0, err)
        self.assertEqual(t70.git(self.registry, "branch", "--show-current").strip(),
                         f"retire-skill/{KEPT}")
        body = next(s for a, s in fake.calls if a[:2] == ["pr", "create"])
        self.assertIn("is **retire** as of", body.split("\n")[0])
        self.assertEqual(len([a for a, _ in fake.calls if a[:2] == ["pr", "create"]]), 1)
        self.assertTrue((self.registry / "plugins" / t70.PLUGIN / "skills" / SKILL).is_dir())

    def test_the_candidate_with_the_most_accrued_cost_is_picked(self):
        self.set_skills({SKILL: 100, KEPT: 200})
        self.usage = self.write_usage(census(cloud=3400))
        code, out, err, fake = self.go()
        self.assertEqual(code, 0, err)
        self.assertEqual(t70.git(self.registry, "branch", "--show-current").strip(),
                         f"retire-skill/{KEPT}")
        self.assertEqual(len(fake.pushes), 1)

    def test_a_tie_goes_to_the_name(self):
        self.set_skills({SKILL: 100, KEPT: 100})
        self.usage = self.write_usage(census(cloud=3400))
        self.go()
        self.assertEqual(t70.git(self.registry, "branch", "--show-current").strip(),
                         f"retire-skill/{SKILL}")  # example-skill < other-skill

    def test_a_candidate_decided_by_a_closed_pr_gives_way_to_the_next(self):
        self.usage = self.write_usage(census(cloud=3400))
        fake = t70.FakeGitHub(closed=[{
            "number": 8, "head": f"retire-skill/{SKILL}",
            "url": "https://github.com/Adam-S-Daniel/adam-agentskills/pull/8"}])
        code, out, err, fake = self.go(fake=fake)
        self.assertEqual(code, 0, err)
        self.assertEqual(t70.git(self.registry, "branch", "--show-current").strip(),
                         f"retire-skill/{KEPT}")

    def test_every_candidate_decided_opens_nothing(self):
        self.usage = self.write_usage(census(cloud=3400))
        fake = t70.FakeGitHub(closed=[{
            "number": n, "head": f"retire-skill/{s}",
            "url": f"https://github.com/Adam-S-Daniel/adam-agentskills/pull/{n}"}
            for n, s in ((8, SKILL), (9, KEPT))])
        code, out, err, fake = self.go(fake=fake)
        self.assertEqual(code, 0, err)
        self.assertIn("none removable now", out)
        self.assertEqual(fake.pushes, [])
        self.assertUntouched()

    def test_a_used_skill_is_not_removed(self):
        self.usage = self.write_usage(census(cloud=3400, uses=[(SKILL, 1), (KEPT, 1)]))
        code, out, err, fake = self.go()
        self.assertEqual(code, 0, err)
        self.assertIn("none is unused enough", out)
        self.assertEqual((fake.pushes, fake.writes()), ([], []))
        self.assertUntouched()

    def test_a_use_under_a_plugin_prefix_blocks_the_removal(self):
        self.usage = self.write_usage(census(cloud=3400, uses=[
            (f"adam-coding-anywhere:{SKILL}", 1), (f"adam:{KEPT}", 1)]))
        self.assertEqual(self.go()[3].pushes, [])

    def test_an_exempt_skill_is_not_removed(self):
        code, out, err, fake = self.go(exempt={SKILL, KEPT})
        self.assertEqual((code, fake.pushes), (0, []))
        self.assertUntouched()

    def test_too_little_exposure_removes_nothing(self):
        self.usage = self.write_usage(census(cloud=3399))
        self.assertEqual(self.go()[3].pushes, [])

    def registry_with(self, name, plugin):
        """A registry holding SKILL under `plugin` and KEPT (which has a use)
        under adam-coding-anywhere, each with a 100-token description."""
        root = t70.make_registry(self.tmp / name, skills=(
            (plugin, SKILL), (plugin, "third"), (t70.PLUGIN, KEPT)))
        for p in root.glob("plugins/*/skills/*"):
            (p / "SKILL.md").write_text(body_for(100).replace("example-skill", p.name, 1))
        t70.git(root, "commit", "-qam", "descriptions")
        return root

    def test_a_local_only_plugin_skill_is_never_removed(self):
        # 10 million full local listings and no cloud session: far past any
        # threshold, but a skill that reaches only the local surface is paused.
        self.usage = self.write_usage(census(local=10 ** 7, cloud=0, cloud_source=False,
                                             uses=[(KEPT, 1), ("third", 1)]))
        local = self.registry_with("local-only", "adam-coding-local")
        code, out, err, fake = self.go(registries=[f"adam-agentskills={local}"])
        self.assertEqual((code, fake.pushes), (0, []), err)
        self.assertIn("none is unused enough", out)
        # The control: the same census removes it once its plugin reaches cloud
        # (a cloud source is then needed too, so the cloud surface is counted).
        self.usage = self.write_usage(census(local=10 ** 7, cloud=0,
                                             uses=[(KEPT, 1), ("third", 1)]))
        anywhere = self.registry_with("anywhere", t70.PLUGIN)
        code, out, err, fake = self.go(registries=[f"adam-agentskills={anywhere}"])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.pushes), 1)
        self.assertEqual(t70.git(anywhere, "branch", "--show-current").strip(),
                         f"retire-skill/{SKILL}")

    def test_proposal_mode_or_no_auto_credential_opens_nothing(self):
        code, out, err, fake = self.go(self.gates("proposal"))
        self.assertEqual((code, fake.pushes, fake.writes()), (0, [], []))
        code, out, err, fake = self.go(self.gates(), "--allow-mode", "proposal")
        self.assertEqual((code, fake.pushes, fake.writes()), (0, [], []))
        code, out, err, fake = self.go(self.gates(), "--fallback-to-proposal",
                                       "--allow-mode", "proposal")
        self.assertEqual((code, fake.pushes, fake.writes()), (0, [], []))

    def test_no_usage_file_opens_nothing(self):
        code, out, err, fake = self.go(usage=False)
        self.assertEqual((code, fake.pushes), (0, []))
        self.assertIn("no skill has a retire verdict", out)

    def test_an_open_loop_pull_request_holds_the_slot(self):
        fake = t70.FakeGitHub(prs=[{"number": 3, "head": "eval-improve/x", "url":
                                    "https://github.com/Adam-S-Daniel/adam-agentskills/pull/3"}])
        code, out, err, fake = self.go(fake=fake)
        self.assertEqual((code, fake.pushes, fake.writes()), (0, [], []))
        self.assertIn("already open", out)

    def test_a_blocked_review_leaves_it_unarmed_like_any_removal(self):
        def blocked(subject, checkout, base, verdict, dirs):
            self.assertTrue(verdict.startswith("unused as of"), verdict)
            return {"outcome": "block", "rounds": [], "findings": [], "why": "a blocker"}
        code, out, err, fake = self.go(review=blocked)
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.pushes, [])
        self.assertIn("held the removal", out)
        self.assertTrue(any(a[:2] == ["issue", "create"] for a, _ in fake.calls))

    def test_the_dry_run_prints_the_plan_and_writes_nothing(self):
        code, out, err, fake = self.go(None, "--dry-run", env=t70.SCHEDULE)
        self.assertEqual(code, 0, err)
        plan = json.loads(out)
        self.assertEqual((plan["action"], plan["removal_reason"], plan["skill"]),
                         ("removal", "unused", SKILL))
        self.assertEqual(plan["unused"]["threshold"]["cloud"], 3400)
        self.assertEqual(fake.pushes, [])
        self.assertUntouched()

    def test_the_committed_policy_and_exemptions_are_what_main_reads(self):
        policy, exempt = retire_skill.unused_inputs()
        self.assertEqual(policy, POLICY)
        self.assertIn("finding-unknowns", exempt)
        self.assertIn("test-canary", exempt)


UNUSED_BODY = (f"Removes `plugins/{t70.PLUGIN}/skills/{SKILL}`: it is **unused** as of "
               f"{AS_OF} (no use in 8 weeks).\n\nFigures.\n")


def unused_pr(**kw):
    return {**tw.pr(created_at="2026-10-24T00:00:00Z", **kw), "body": UNUSED_BODY}


def verdicts_doc(mode="auto"):
    return tw.doc({"kept-skill": tw.VERDICTS["keep"]}, as_of=AS_OF, mode=mode)


class WithdrawUnusedTests(unittest.TestCase):
    """An unused removal has no `retire` verdict: it is kept while the skill
    stays unused and withdrawn once it is used or exempt."""

    def decide(self, check, mode="auto", **kw):
        return retire_skill.withdrawal_decision(unused_pr(**kw), verdicts_doc(mode),
                                                "skill", check)

    def test_kept_while_the_skill_stays_unused(self):
        got = self.decide(lambda s: ("supported", "still unused"))
        self.assertEqual((got["action"], got["subject"]), ("keep", SKILL))

    def test_withdrawn_when_the_skill_was_used_since(self):
        got = self.decide(lambda s: ("stale", "the skill has been used (2 use(s))"))
        self.assertEqual((got["action"], got["subject"]), ("withdraw", SKILL))
        self.assertTrue(got["unused"])
        self.assertIn("has been used", got["why"])

    def test_unknown_keeps_it(self):
        self.assertEqual(self.decide(lambda s: ("unknown", "no census"))["action"], "keep")
        self.assertEqual(self.decide(None)["action"], "keep")

    def test_the_proposal_switch_still_disarms_it(self):
        got = self.decide(lambda s: ("supported", "still unused"), mode="proposal")
        self.assertEqual(got["action"], "disarm")

    def test_a_removal_opened_on_newer_results_than_the_verdicts_is_kept(self):
        body = UNUSED_BODY.replace(AS_OF, "20261101T000000Z")
        pr = {**unused_pr(), "body": body, "created_at": "2026-11-01T01:00:00Z"}
        got = retire_skill.withdrawal_decision(pr, verdicts_doc(), "skill",
                                               lambda s: ("stale", "used"))
        self.assertEqual(got["action"], "keep")
        self.assertIn("newer results", got["why"])

    def test_a_retire_removal_is_still_judged_by_its_verdict(self):
        pr = {**tw.pr(), "body": f"Removes `x`: its retirement verdict in y is **retire** "
                                 "as of 20261024T000000Z (z)."}
        check = mock.Mock(return_value=("supported", "still unused"))
        gates = tw.doc({SKILL: tw.VERDICTS["keep"]}, as_of=AS_OF)
        got = retire_skill.withdrawal_decision(pr, gates, "skill", check)
        self.assertEqual(got["action"], "withdraw")  # its verdict is keep
        check.assert_not_called()

    def test_the_withdrawal_calls_and_texts_say_the_skill_is_used(self):
        gh = tw.FakeGh()
        lines = retire_skill.withdraw_stale(
            verdicts_doc(), [unused_pr()], "skill", gh, None,
            delete=lambda *a: None,
            items=retire_skill.withdraw_plan(verdicts_doc(), [unused_pr()], "skill", None,
                                             lambda s: ("stale", "the skill has been used")))
        self.assertTrue(lines[0].startswith("withdrew #41: the skill has been used"), lines)
        comment = next(s for a, s in gh.calls if a[:2] == ["pr", "comment"])
        self.assertIn("opened because the skill was unused, and it no longer is", comment)
        issue = next(s for a, s in gh.calls if a[:2] == ["issue", "create"])
        self.assertIn("the skill is no longer unused", issue)
        self.assertIn("if the skill is unused again", issue)

    def test_a_kept_unused_removal_makes_no_write(self):
        gh = tw.FakeGh()
        lines = retire_skill.withdraw_stale(
            verdicts_doc(), [unused_pr()], "skill", gh,
            items=retire_skill.withdraw_plan(verdicts_doc(), [unused_pr()], "skill", None,
                                             lambda s: ("supported", "still unused")))
        self.assertTrue(lines[0].startswith("kept #41"), lines)
        self.assertEqual(gh.writes(), [])


class UnusedCheckerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def usage(self, doc):
        path = self.tmp / "usage.json"
        path.write_text(json.dumps(doc))
        return path

    def check(self, doc, exempt=(), policy_ok=True):
        path = self.usage(doc) if doc is not None else self.tmp / "missing.json"
        inputs = (unused_inputs(exempt) if policy_ok else mock.Mock(
            side_effect=retire_skill.RetireError("bad")))
        with mock.patch.object(retire_skill, "unused_inputs", inputs):
            return retire_skill.unused_checker(verdicts_doc(), path)(SKILL)

    def test_still_unused_is_supported(self):
        self.assertEqual(self.check(census(cloud=100))[0], "supported")

    def test_a_use_in_the_floor_window_is_stale(self):
        state, why = self.check(census(cloud=100, uses=[(f"adam:{SKILL}", 3)]))
        self.assertEqual(state, "stale")
        self.assertIn("3 use(s) in the last 8 weeks", why)

    def test_becoming_exempt_is_stale(self):
        self.assertEqual(self.check(census(cloud=100), exempt={SKILL})[0], "stale")

    def test_a_missing_or_stale_census_or_policy_is_unknown(self):
        self.assertEqual(self.check(None)[0], "unknown")
        old = census(cloud=100, generated=NOW - timedelta(days=15))
        self.assertEqual(self.check(old)[0], "unknown")
        self.assertEqual(self.check(census(cloud=100), policy_ok=False)[0], "unknown")
        no_path = retire_skill.unused_checker(verdicts_doc(), None)
        with mock.patch.object(retire_skill, "unused_inputs", unused_inputs()):
            self.assertEqual(no_path(SKILL)[0], "unknown")


class WorkflowWiringTests(unittest.TestCase):
    """The workflows hand the usage census to every skill pass."""

    def test_each_skill_pass_gets_the_usage_file(self):
        for name in ("skill-coverage.yml", "loop-pr-refresh.yml"):
            text = (ROOT / ".github" / "workflows" / name).read_text()
            for marker in ("scripts/retire_skill.py --withdraw-stale \\\n"
                           "            --gates",):
                start = text.index(marker)
                step = text[start:text.index("\n\n", start)]
                self.assertIn("--usage", step, name)
        text = (ROOT / ".github" / "workflows" / "skill-coverage.yml").read_text()
        act = text[text.index("python3 scripts/retire_skill.py \\\n"):]
        self.assertIn("--usage", act.split("\n\n")[0])
        self.assertIn("registry-agentskills", act.split("\n\n")[0])


if __name__ == "__main__":
    unittest.main()
