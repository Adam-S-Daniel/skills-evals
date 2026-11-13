#!/usr/bin/env python3
"""Build docs/rules.md and docs/rules.json from the policy YAMLs in evals/.

The rules for keeping, removing, pausing and re-checking skills, guidance
sections and git hooks live in evals/gate-policy.yml, removal-policy.yml,
scope-policy.yml, hook-policy.yml, usage-unknown.yml and stakes.yml. This
script reads them with the same loaders the code uses (so a file the code
would refuse is refused here too) and writes:

  docs/rules.md    the rules in plain English, every number substituted from
                   the YAMLs, each linked to the key it comes from;
  docs/rules.json  every rule value keyed `<file>#<block>.<key>` (or
                   `<file>#<key>` for a file with no blocks), with its source
                   path, plus the names that may restate it in code
                   (`names`), for scripts/check_rule_restatements.py.

Usage:
  build_rules.py            write both files
  build_rules.py --check    exit 1 if either file differs from what the YAMLs
                            produce (CI runs this)

Stdlib and `yaml`; no network, no clock.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import eval_scope  # noqa: E402
import explorer_public  # noqa: E402
import gates  # noqa: E402
import removal_policy  # noqa: E402

EVALS = "evals"
MD_PATH = Path("docs") / "rules.md"
JSON_PATH = Path("docs") / "rules.json"
#: Where _agent-guidance keeps the weekly guidance merge window's bounds.
MERGE_WINDOW = ("https://github.com/Adam-S-Daniel/_agent-guidance/blob/main/"
                "scripts/base-md-merge-window.yml")
#: Names that restated a rule value in code before it moved into a YAML, or
#: that a reader may still use for it. scripts/check_rule_restatements.py
#: checks a number written next to any of them.
LEGACY_NAMES = {
    "gate-policy.yml#skills.high_stop_min_without": ["HIGH_STOP_MIN_WITHOUT"],
    "gate-policy.yml#skills.benefit_confidence": ["DEFAULT_BENEFIT_CONFIDENCE", "KEEP_AT"],
    "gate-policy.yml#skills.retire_confidence": ["DEFAULT_RETIRE_CONFIDENCE", "REMOVE_AT"],
    "gate-policy.yml#skills.floor_min_runs": ["FLOOR_MIN_RUNS"],
    "gate-policy.yml#skills.recheck_weeks": ["RECHECK_AFTER"],
    "gate-policy.yml#skills.recheck_weeks_high": ["RECHECK_AFTER_HIGH"],
    "gate-policy.yml#skills.max_removal_pauses": ["MAX_LOOP_PAUSES"],
    "removal-policy.yml#first_use_weeks": ["CENSUS_WEEKS"],
    "scope-policy.yml#ceiling_min_runs": ["CEILING_MIN_RUNS"],
    "scope-policy.yml#ceiling_share": ["CEILING_SHARE"],
    "scope-policy.yml#ceiling_judge": ["CEILING_JUDGE"],
    "scope-policy.yml#floor_share": ["FLOOR_SHARE"],
    "scope-policy.yml#keep_guard": ["KEEP_GUARD"],
    "hook-policy.yml#window_weeks": [],
}
#: Keys whose UPPER_CASE or camelCase form names something that is not this
#: rule: explorer/src/core/rules.js's WINDOW_WEEKS is the page's own pooling
#: window, not the hook policy's.
OWN_FORMS_ELSEWHERE = {"window_weeks"}
#: Rule names that no longer exist: a number set next to one in code is a
#: stale restatement whatever its value.
RETIRED_NAMES = {
    "ZERO_USE_MIN_SESSIONS": "the zero-use session minimum is gone: evals pause until a "
                             "skill's first recorded use, with no session minimum",
    "AUTO_MIN_HEADROOM_CELLS": "every retire verdict's removal is automatic; no headroom "
                               "minimum decides it",
    "HOOK_POLICY_DEFAULTS": "evals/hook-policy.yml is read strictly "
                            "(explorer_public.load_hook_policy); no defaults in code",
}


class RulesError(Exception):
    """A policy file the loaders refuse, or one this script cannot read."""


def _line_of(text: str, path: list[str]) -> int:
    """The 1-based line of the YAML key at `path` (a block, then a key) in
    `text`, found by walking the parsed node tree."""
    node = yaml.compose(text)
    for part in path:
        if not isinstance(node, yaml.MappingNode):
            raise RulesError(f"no key {'.'.join(path)}")
        for key, value in node.value:
            if key.value == part:
                found = key
                node = value
                break
        else:
            raise RulesError(f"no key {'.'.join(path)}")
    return found.start_mark.line + 1


def load(root: Path) -> dict:
    """{"rules": {id: {value, source, key, line, names}}, "lists": {...}}
    from the YAMLs under `root`/evals, each read by the loader the code
    uses."""
    evals = root / EVALS
    rules: dict = {}

    def add(file: str, path: list[str], value, text: str) -> None:
        rule_id = f"{file}#{'.'.join(path)}"
        # A nested key (`reread_usd_per_session.cloud`) is too generic a
        # word to check by name. A key is also checked in its UPPER_CASE
        # and camelCase forms, except where that names something else.
        key = path[-1] if len(path) == 1 or file == "gate-policy.yml" else None
        names = [] if key is None else [key] + (
            [] if key in OWN_FORMS_ELSEWHERE else
            [key.upper(), re.sub(r"_([a-z])", lambda m: m.group(1).upper(), key)])
        names = list(dict.fromkeys(names + LEGACY_NAMES.get(rule_id, [])))
        rules[rule_id] = {"value": value, "source": f"{EVALS}/{file}",
                          "key": ".".join(path), "line": _line_of(text, path),
                          "names": names}

    try:
        text = (evals / "gate-policy.yml").read_text(encoding="utf-8")
        gate = gates.parse_gate_policy(text)
        for block in ("skills", "guidance"):
            if gate[block] is None:
                continue
            for key, value in gate[block].items():
                add("gate-policy.yml", [block, key], value, text)

        text = (evals / "removal-policy.yml").read_text(encoding="utf-8")
        removal = removal_policy.parse(text)
        for key, value in removal.items():
            if isinstance(value, dict):
                for sub, v in value.items():
                    add("removal-policy.yml", [key, sub], v, text)
            else:
                add("removal-policy.yml", [key], value, text)

        text = (evals / "scope-policy.yml").read_text(encoding="utf-8")
        for key, value in eval_scope.parse_scope_policy(text).items():
            add("scope-policy.yml", [key], value, text)

        hook_path = evals / "hook-policy.yml"
        text = hook_path.read_text(encoding="utf-8")
        for key, value in explorer_public.load_hook_policy(hook_path).items():
            add("hook-policy.yml", [key], value, text)

        unknown = yaml.safe_load((evals / "usage-unknown.yml").read_text(encoding="utf-8"))
        stakes = yaml.safe_load((evals / "stakes.yml").read_text(encoding="utf-8"))
    except (OSError, ValueError, gates.GatePolicyError, removal_policy.PolicyError,
            eval_scope.ScopeError) as error:
        raise RulesError(str(error)) from None
    lists = {
        "usage-unknown.yml#skills": sorted(r["skill"] for r in unknown["skills"]),
        "stakes.yml#high": sorted(
            [f"skill {r['skill']}" for r in stakes.get("skills") or [] if r["stakes"] == "high"]
            + [f"section {r['section']}" for r in stakes.get("sections") or []
               if r["stakes"] == "high"]),
    }
    return {"rules": rules, "lists": lists}


def _num(value) -> str:
    """A value as a person reads it: 0.1 for 0.10, 10 for 10.0."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"{value:g}" if isinstance(value, float) else str(value)


def _pct(value) -> str:
    return f"{_num(round(value * 100, 10))}%"


def render_md(doc: dict) -> str:
    rules = doc["rules"]

    def v(rule_id: str) -> str:
        return _num(rules[rule_id]["value"])

    def p(rule_id: str) -> str:
        return _pct(rules[rule_id]["value"])

    def ref(rule_id: str) -> str:
        r = rules[rule_id]
        return f"[`{r['key']}`](../{r['source']}#L{r['line']})"

    def same(key: str, fmt=v) -> str:
        """A value the skills and guidance blocks share, or both values."""
        s, g = f"gate-policy.yml#skills.{key}", f"gate-policy.yml#guidance.{key}"
        if g not in rules or rules[s]["value"] == rules[g]["value"]:
            return f"{fmt(s)} ({ref(s)})"
        return f"{fmt(s)} for skills ({ref(s)}), {fmt(g)} for guidance ({ref(g)})"

    S = "gate-policy.yml#skills."
    R = "removal-policy.yml#"
    C = "scope-policy.yml#"
    H = "hook-policy.yml#"
    margin = rules[S + "objective_margin"]["value"]
    n_star = (rules[R + "value_per_use_usd"]["value"] * rules[R + "prefix_tokens"]["value"]
              / (100 * rules[R + "reread_usd_per_session.cloud"]["value"]))
    exempt = ", ".join(f"`{s}`" for s in doc["lists"]["usage-unknown.yml#skills"])
    high = ", ".join(f"`{s.split(' ', 1)[1]}`" for s in doc["lists"]["stakes.yml#high"])
    lines = [
        "# Rules: keeping, removing and pausing skills, guidance and hooks",
        "",
        "<!-- Generated by scripts/build_rules.py from evals/*.yml. Do not edit this file:",
        "     edit the YAML, then run `python3 scripts/build_rules.py`. -->",
        "",
        "Generated from the policy files in [`evals/`](../evals/). **Edit the YAMLs, not "
        "this page**, then run `python3 scripts/build_rules.py`; CI fails when this page "
        "or [`rules.json`](rules.json) is stale. Anywhere else, link here instead of "
        "restating a number: `scripts/check_rule_restatements.py` fails on a restated "
        "value that disagrees.",
        "",
        "## Skills and guidance sections",
        "",
        "A skill and a guidance section are judged the same way, each from its own block "
        "of [`gate-policy.yml`](../evals/gate-policy.yml); where the blocks differ, both "
        "values are shown. Each eval fire runs one fixture on one model with and without "
        "the subject: a *pair*. A *cell* is one fixture on one model; its gain per pair is "
        "D = with − without (share of checks passed).",
        "",
        "**Keep.** The subject is kept when any cell shows D > 0 at "
        f"{same('benefit_confidence', p)} confidence overall, split evenly over the "
        "subject's cells.",
        "",
        "**No benefit.** A cell shows no benefit when it is confident at "
        f"{same('retire_confidence', p)} that D is below {same('objective_margin')}, "
        f"with pairs spanning at least {same('min_cli_versions')} Claude Code versions. "
        "A cell where the subject makes things worse (D < 0, at the same level) also counts "
        "as no benefit.",
        "",
        f"**Cap.** A cell is fired at most {same('max_runs_per_cell')} pairs. At the cap "
        "with neither test crossed, and pairs on enough Claude Code versions, it has *no "
        "clear effect*, which counts toward removal like no benefit. On one version, or "
        "with a test that crossed but has not decided, it stays *insufficient* and is "
        "listed as a `cell-at-cap` work item.",
        "",
        "**Ceiling (parked).** A cell whose without arm is confidently above "
        f"1 − margin (above {_num(round(1 - margin, 10))} today) cannot show the margin: it "
        "is parked as `ceiling`, stops being fired and does not vote on removal. A high "
        f"cell still undecided after {same('max_runs_high_cell')} pairs stops as "
        "`ceiling-unconfirmed` (also parked) when its no-harm test has passed and its "
        f"without arm averages at least {same('high_stop_min_without')}.",
        "",
        f"**Broken fixture.** A cell whose arms both pass at most {same('floor_fraction')} "
        f"of checks over {same('floor_min_runs')} pairs is `cannot-discriminate` and left "
        "out of the verdict.",
        "",
        "**Verdict**, first match: any keeping cell → `keep`; any cell still insufficient "
        "or missing → `insufficient`; every cell broken → `cannot-discriminate`; every "
        "counted cell parked → `ceiling` (when each shows it on its own runs, else "
        "`insufficient`); otherwise `retire`. For a guidance section, a `retire` whose "
        "section-alone pair (the section against no guidance) shows a benefit is "
        "`shorten-or-merge`, never a removal, and one whose alone pair is unfinished is "
        "`insufficient`. A cell paused by the zero-use rule (below) keeps "
        "its subject `insufficient`. The judge's score is shown but does not vote (its "
        f"margin: {same('judge_margin')} on 0 to 10).",
        "",
        "**Guidance only.** Under "
        f"`{rules['gate-policy.yml#guidance.rest_policy']['value']}` "
        f"({ref('gate-policy.yml#guidance.rest_policy')}) a section's cells pool pairs made "
        "beside every earlier version of the rest of the guidance, and every decision "
        "toward removal also needs at least "
        f"{v('gate-policy.yml#guidance.rest_guard_min_pairs')} pairs "
        f"({ref('gate-policy.yml#guidance.rest_guard_min_pairs')}) beside the current rest, "
        "deciding at the remove level on its own.",
        "",
        "## Removal",
        "",
        "**Every `retire` verdict removes automatically** while `retirement_mode` is "
        f"`auto` (today: {same('retirement_mode', lambda r: '`' + v(r) + '`')}): a removal pull request opens, passes a fresh-context agent review and "
        "merges with no human review. It acts only from the scheduled workflow, one "
        "removal per evaluation, and opens nothing while another loop pull request or an "
        "agent-stamped removal issue is open.",
        "",
        "Exceptions:",
        "",
        "- **Owner approval:** a skill whose removal would wait on adam-agentskills' "
        "`plugin-runtime-review` (its plugin runs code) gets a `proposal` issue for Adam "
        "instead; no agent approves one.",
        "- **Pause cap:** after the loop has withdrawn "
        f"{same('max_removal_pauses')} removals of one subject, its proposal issue is "
        "filed for Adam instead of another removal.",
        "- **Fleet worker:** a skill the bot cannot remove itself (its copy is in "
        "cms-platform or adamdaniel.ai, adam-agentskills' mechanical path refuses, or no "
        "write token reached the run) gets an `agent-ready` issue for the fleet worker.",
        "- **Guidance merge window:** a guidance removal merges only inside "
        f"_agent-guidance's weekly window ([`base-md-merge-window.yml`]({MERGE_WINDOW}); "
        "[ADR 0017](decisions/0017-guidance-loop-merges-wait-for-the-weekly-window.md)).",
        "",
        "**Unused skills** (reason `unused`, "
        "[`removal-policy.yml`](../evals/removal-policy.yml)) are removed, through the "
        "same flow, only when all hold: not listed in "
        "[`usage-unknown.yml`](../evals/usage-unknown.yml); reaches the cloud surface "
        f"(local-only removal: `{str(rules[R + 'local_removal']['value']).lower()}`, "
        f"{ref(R + 'local_removal')}); a current census counting every surface it reaches; "
        f"zero uses over {v(R + 'floor_weeks')} weeks ({ref(R + 'floor_weeks')}); and its "
        "description's re-read cost over those weeks reaches the value of one use:",
        "",
        "    sum over surfaces s of  sessions_s × d × R_s / P  ≥  V",
        "",
        f"with V = ${v(R + 'value_per_use_usd')} ({ref(R + 'value_per_use_usd')}), "
        f"P = {v(R + 'prefix_tokens')} tokens ({ref(R + 'prefix_tokens')}), "
        f"R = ${v(R + 'reread_usd_per_session.cloud')} per cloud session and "
        f"${v(R + 'reread_usd_per_session.local')} per local one "
        f"({ref(R + 'reread_usd_per_session.cloud')}), and d the skill's description size "
        f"in tokens. For d = 100 on the cloud alone that is {_num(round(n_star, 6))} "
        "sessions.",
        "",
        "## Pausing evals",
        "",
        "The eval scope pass ([`scripts/eval_scope.py`](../scripts/eval_scope.py)) pauses "
        "scheduled fixtures and resumes them; a paused fixture's decided cells still count.",
        "",
        "- **First use:** a skill with no recorded use in real work over the census's last "
        f"{v(R + 'first_use_weeks')} weeks ({ref(R + 'first_use_weeks')}) has every fixture "
        "paused, high stakes included, with no session minimum; they resume on its first "
        "recorded use. An unknown census (missing, stale, or stale for any surface the "
        "skill reaches) pauses nothing.",
        f"- **Usage unknown:** the skills in [`usage-unknown.yml`](../evals/usage-unknown.yml) "
        f"({exempt}) are never paused or removed for use; their eval verdict is their only "
        "path to removal.",
        f"- **Ceiling:** after {v(C + 'ceiling_min_runs')} runs since the fixture changed "
        f"({ref(C + 'ceiling_min_runs')}), a without arm passing at least "
        f"{v(C + 'ceiling_share')} of checks ({ref(C + 'ceiling_share')}) and, when judged, "
        f"scoring at least {v(C + 'ceiling_judge')} ({ref(C + 'ceiling_judge')}), on every "
        "roster model.",
        f"- **Floor:** both arms passing at most {v(C + 'floor_share')} "
        f"({ref(C + 'floor_share')}) over the same runs.",
        "- Ceiling and floor never pause a `stakes: high` subject, a kept one, or one whose "
        f"confidence that it helps is at least {v(C + 'keep_guard')} "
        f"({ref(C + 'keep_guard')}).",
        "- **Weekly guidance window:** no automated eval run, in any mode, starts while "
        f"_agent-guidance's weekly guidance merge window is open ([`base-md-merge-window.yml`]({MERGE_WINDOW}), "
        "US Eastern, so its UTC hours move with daylight saving time); a run already going "
        "finishes. Planned fires wait for the next sweep after it closes "
        "([ADR 0017](decisions/0017-guidance-loop-merges-wait-for-the-weekly-window.md)).",
        "",
        "## Re-checks and stakes",
        "",
        f"A decided subject is re-checked {same('recheck_weeks')} weeks after its newest "
        f"run, or {same('recheck_weeks_high')} weeks for a `stakes: high` one "
        f"([`stakes.yml`](../evals/stakes.yml): {high}). High-stakes subjects are tested "
        "first within each planning band. No re-check is planned while the subject's "
        "removal is `pr-open`, `worker`, `waiting-turn`, `queued`, `removed` or unknown.",
        "",
        "## Git hooks",
        "",
        "Each git hook check gets a verdict over the last "
        f"{v(H + 'window_weeks')} weeks ({ref(H + 'window_weeks')}):",
        "",
        "- `earning`: blocked at least once, and overridden in at most "
        f"{p(H + 'max_override_rate')} of its blocks ({ref(H + 'max_override_rate')});",
        "- `overridden-often`: overridden in more than that;",
        "- `never-blocked`: blocked nothing, and either ran or has runs no source counts;",
        "- `never-ran`: its runs are counted, none was recorded, and nothing was blocked.",
        "",
        "A check that blocked but whose overrides no source counts is `earning`, marked "
        "unmeasured; `overridden-often` needs a measured rate. Non-public repositories "
        f"get their own row only when at least {v(H + 'min_private_repos')} feed the data "
        f"({ref(H + 'min_private_repos')}); below that, their runs and blocks still count, "
        "unnamed, in each check's totals and verdict. **No rule removes a hook check**: the verdicts "
        "are reported, not acted on.",
        "",
    ]
    return "\n".join(lines)


def render_json(doc: dict) -> str:
    out = {
        "generated_by": "scripts/build_rules.py",
        "edit": "evals/*.yml",
        "rules": {k: {f: r[f] for f in ("value", "source", "key", "names")}
                  for k, r in sorted(doc["rules"].items())},
        "lists": doc["lists"],
        "retired_names": RETIRED_NAMES,
    }
    return json.dumps(out, indent=2, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="fail if docs/rules.md or docs/rules.json is stale")
    parser.add_argument("--root", type=Path, default=REPO_ROOT,
                        help="repository root (default: this checkout)")
    args = parser.parse_args(argv)
    try:
        doc = load(args.root)
    except RulesError as error:
        print(f"build_rules: {error}", file=sys.stderr)
        return 1
    want = {MD_PATH: render_md(doc), JSON_PATH: render_json(doc)}
    stale = []
    for rel, text in want.items():
        path = args.root / rel
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current == text:
            continue
        if args.check:
            stale.append(str(rel))
        else:
            path.write_text(text, encoding="utf-8")
    if stale:
        print(f"build_rules: {', '.join(stale)} is stale; run `python3 scripts/build_rules.py` "
              "and commit the result", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
