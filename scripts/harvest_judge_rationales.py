#!/usr/bin/env python3
"""Candidate objective checks, harvested from recorded judge rationales
(skills-evals#550, form 1).

For a with/without pair the judge runs only when the objective checks do not
put the with arm strictly ahead (conditional judging), so a judged pair is a
case the checks failed to separate. When the judge then scores the arms
apart, its rationale says what it saw that the checks missed. This script
reads those rationales and lists the recurring ones as leads for a new check.

    python3 scripts/harvest_judge_rationales.py --results-tree <persistent/eval-results checkout> \\
        [--evals evals] [--min-recur 2] [--gap 3.0] [--json out.json]

Inputs: every `summary.json` under `results/` and `routine-results/`, found
and read exactly as compute_gates.py does (its `_summaries` and `_read`, so
the size caps and the no-symlink rule apply), and each fixture's current
`fixture.yaml` under --evals. Pairings: `with_skill` / `without_skill`, and
for guidance `with_guidance_section` / `without_guidance` and
`with_guidance_full` / `with_guidance_full_minus_section`. Arms with trial
files are paired by trial index; otherwise the arm summary is the one trial.
A Markdown report goes to stdout; --json writes the same data structured.

A pair is "judge-decided" when the with arm is not strictly ahead on passed
objective checks and both arms carry `judge.overall` at least 1.0 apart.
Each dimension scored at least --gap points apart in such a pair is a record;
a (fixture, dimension) group with --min-recur records is "recurring", and its
backtick-quoted spans and path-like tokens are counted across the rationales.

Guards:

  * It makes no model call and never edits a fixture: --evals is only read.
    The output is a report, not a patch.
  * Every proposal is for a reviewed pull request. A check derived after
    seeing which arm won can be fitted to the winner, so it must be proven on
    runs it was not derived from before it counts.
  * Style fixtures (`judge.mode` anything but absolute, as
    run_eval._judge_is_pairwise decides) are excluded: their verdict is
    relative, with no per-arm score to read a rationale from.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compute_gates  # noqa: E402

run_eval = compute_gates.run_eval

SKILL_PAIRS = (("with_skill", "without_skill"),)
GUIDANCE_PAIRS = (("with_guidance_section", "without_guidance"),
                  ("with_guidance_full", "with_guidance_full_minus_section"))
MIN_OVERALL_GAP = 1.0
PROPOSAL_LINE = ("Proposal only: write a deterministic check (file, command, git "
                 "state), prove it fails on the seed and passes a correct fix, and "
                 "prove it separates the arms on runs it was not derived from.")
BACKTICK_RE = re.compile(r"`([^`\n]{1,120})`")
PATH_RE = re.compile(r"[\w.\-]+(?:/[\w.\-]+)+/?|[\w\-]+\.(?:ya?ml|json|md|py|sh|js|ts|toml|txt)\b")


def _num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _passed(summary: dict):
    checks = summary.get("objective_checks")
    if not isinstance(checks, list) or not checks:
        return None
    return sum(1 for c in checks if isinstance(c, dict) and c.get("passed") is True)


def _dimensions(summary: dict) -> dict:
    judge = summary.get("judge")
    out = {}
    if isinstance(judge, dict) and isinstance(judge.get("dimensions"), list):
        for d in judge["dimensions"]:
            if isinstance(d, dict) and isinstance(d.get("name"), str) and _num(d.get("score")):
                out[d["name"]] = {"score": d["score"],
                                  "rationale": str(d.get("rationale") or "")}
    return out


def _overall(summary: dict):
    judge = summary.get("judge")
    value = judge.get("overall") if isinstance(judge, dict) else None
    return value if _num(value) else None


def observables(text: str) -> set:
    """Backtick-quoted spans and path-like tokens in `text`."""
    found = {m.strip() for m in BACKTICK_RE.findall(text)}
    found.update(m.rstrip(".,;:") for m in PATH_RE.findall(text))
    return {f for f in found if f}


def fixture_info(evals_dir: Path, key: str, fixture) -> dict:
    """{"pairwise", "check_ids", "found"} of the fixture's current fixture.yaml."""
    path = evals_dir / key / (fixture or "")
    alias = compute_gates.gates.FIXTURE_ALIASES.get((key, fixture or ""))
    if alias is not None and not (path / run_eval.FIXTURE_FILE).is_file():
        path = evals_dir / key / alias
    try:
        doc = yaml.safe_load((path / run_eval.FIXTURE_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        doc = None
    if not isinstance(doc, dict):
        return {"pairwise": False, "check_ids": [], "found": False}
    ids = [c["id"] for c in doc.get("objective_checks") or []
           if isinstance(c, dict) and isinstance(c.get("id"), str)]
    return {"pairwise": bool(run_eval._judge_is_pairwise(doc)), "check_ids": ids, "found": True}


def label(key: str, fixture) -> str:
    return f"{key}/{fixture}" if fixture else key


def _arm_docs(entry: dict) -> tuple:
    """(arm summary or None, {trial index: trial summary})."""
    arm = compute_gates._read(entry["summary"]) if entry["summary"] else None
    trials = {}
    for k, path in entry["trials"]:
        doc = compute_gates._read(path)
        if doc is not None:
            trials[k] = doc
    return arm, trials


def collect_pairs(tree: Path) -> list:
    """Every with/without pair: dicts with run_dir, key, fixture, pairing,
    trial, with, without (summaries). Trials pair by index when both arms
    have them, else the arm summaries pair."""
    arms = compute_gates._summaries(tree)
    groups = defaultdict(dict)
    for (run_dir, key, ts, fixture, arm), entry in sorted(
            arms.items(), key=lambda kv: tuple(str(p) for p in kv[0])):
        groups[(run_dir, key, ts, fixture)][arm] = entry
    pairs = []
    for (run_dir, key, ts, fixture), by_arm in groups.items():
        table = GUIDANCE_PAIRS if key.startswith("guidance/") else SKILL_PAIRS
        for with_arm, without_arm in table:
            if with_arm not in by_arm or without_arm not in by_arm:
                continue
            (arm_a, tr_a), (arm_b, tr_b) = _arm_docs(by_arm[with_arm]), _arm_docs(by_arm[without_arm])
            if tr_a and tr_b:
                matched = [(k, tr_a[k], tr_b[k]) for k in sorted(set(tr_a) & set(tr_b))]
            elif arm_a is not None and arm_b is not None:
                matched = [(None, arm_a, arm_b)]
            else:
                matched = []
            for k, w, wo in matched:
                name = fixture
                if key.startswith("guidance/") and isinstance(w.get("fixture_name"), str):
                    name = w["fixture_name"]
                pairs.append({"run_dir": run_dir, "key": key, "fixture": name,
                              "pairing": f"{with_arm} vs {without_arm}", "trial": k,
                              "with": w, "without": wo})
    return pairs


def analyze(tree: Path, evals_dir: Path, min_recur: int, gap: float) -> dict:
    info_cache: dict = {}
    pairs_total = judged = decided = 0
    decided_fixtures: set = set()
    split = {"skill": [0, 0, 0], "guidance": [0, 0, 0]}  # pairs, judged, decided
    records = defaultdict(list)
    for p in collect_pairs(tree):
        w, wo = p["with"], p["without"]
        pw, pwo = _passed(w), _passed(wo)
        if pw is None or pwo is None:
            continue
        ident = (p["key"], p["fixture"])
        if ident not in info_cache:
            info_cache[ident] = fixture_info(evals_dir, *ident)
        if info_cache[ident]["pairwise"]:
            continue
        kind = "guidance" if p["key"].startswith("guidance/") else "skill"
        pairs_total += 1
        split[kind][0] += 1
        dw, dwo = _dimensions(w), _dimensions(wo)
        if not (dw or dwo):
            continue
        judged += 1
        split[kind][1] += 1
        ow, owo = _overall(w), _overall(wo)
        if pw > pwo or ow is None or owo is None or abs(ow - owo) < MIN_OVERALL_GAP:
            continue
        decided += 1
        split[kind][2] += 1
        name_label = label(*ident)
        decided_fixtures.add(name_label)
        direction = "with better" if ow > owo else "with worse"
        for name in sorted(set(dw) & set(dwo)):
            if abs(dw[name]["score"] - dwo[name]["score"]) < gap:
                continue
            win_with = dw[name]["score"] > dwo[name]["score"]
            win, lose = (dw, dwo) if win_with else (dwo, dw)
            records[(ident, name)].append({
                "fixture": name_label, "dimension": name,
                "winner": "with" if win_with else "without",
                "direction": direction,
                "winner_score": win[name]["score"], "loser_score": lose[name]["score"],
                "winner_rationale": win[name]["rationale"],
                "loser_rationale": lose[name]["rationale"],
                "run_dir": p["run_dir"], "trial": p["trial"],
                "pairing": p["pairing"]})
    groups = []
    for (ident, name), recs in sorted(records.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        if len(recs) < min_recur:
            continue
        counts: Counter = Counter()
        for r in recs:
            counts.update(observables(r["loser_rationale"] + "\n" + r["winner_rationale"]))
        groups.append({
            "fixture": label(*ident), "dimension": name, "count": len(recs),
            "direction_counts": dict(Counter(r["direction"] for r in recs)),
            "winner_counts": dict(Counter(r["winner"] for r in recs)),
            "observables": [{"text": t, "records": n} for t, n in
                            sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]],
            "loser_rationales": [r["loser_rationale"] for r in recs[:3]],
            "existing_check_ids": info_cache[ident]["check_ids"],
            "records": recs})
    groups.sort(key=lambda g: (-g["count"], g["fixture"], g["dimension"]))
    return {"headline": {"pairs": pairs_total, "pairs_with_judge": judged,
                         "judge_decided": decided,
                         "judge_decided_share_of_judged": (decided / judged) if judged else None,
                         "by_kind": {k: {"pairs": v[0], "judged": v[1], "decided": v[2]}
                                     for k, v in split.items()},
                         "fixtures_with_judge_decided_pair": len(decided_fixtures),
                         "min_recur": min_recur, "gap": gap},
            "groups": groups}


def render(result: dict) -> str:
    h = result["headline"]
    share = h["judge_decided_share_of_judged"]
    lines = ["# Judge rationales: candidate objective checks", "",
             f"- Pairs (excluding style fixtures): {h['pairs']}",
             f"- Pairs with judge dimensions: {h['pairs_with_judge']}",
             f"- Judge-decided pairs: {h['judge_decided']}"
             + (f" ({share:.1%} of judged pairs)" if share is not None else ""),
             f"- Skill: {h['by_kind']['skill']['pairs']} pairs, {h['by_kind']['skill']['judged']} judged, "
             f"{h['by_kind']['skill']['decided']} judge-decided",
             f"- Guidance: {h['by_kind']['guidance']['pairs']} pairs, {h['by_kind']['guidance']['judged']} judged, "
             f"{h['by_kind']['guidance']['decided']} judge-decided",
             f"- Distinct fixtures with a judge-decided pair: {h['fixtures_with_judge_decided_pair']}",
             f"- Recurring groups (>= {h['min_recur']} records, gap >= {h['gap']}): {len(result['groups'])}", ""]
    for g in result["groups"]:
        lines += [f"## {g['fixture']} / {g['dimension']}", "",
                  f"- Fixture: `{g['fixture']}`", f"- Dimension: {g['dimension']}",
                  f"- Records: {g['count']}",
                  f"- Direction: {json.dumps(g['direction_counts'], sort_keys=True)}",
                  "- Top observables: " + (", ".join(f"`{o['text']}` ({o['records']})"
                                                    for o in g["observables"][:8]) or "none"),
                  "- Existing check ids: " + (", ".join(f"`{i}`" for i in g["existing_check_ids"]) or "none found"),
                  "- Loser rationales:"]
        lines += [f"  > {r}" for r in g["loser_rationales"]]
        lines += ["", PROPOSAL_LINE, ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--results-tree", required=True, type=Path)
    ap.add_argument("--evals", type=Path, default=Path("evals"))
    ap.add_argument("--min-recur", type=int, default=2)
    ap.add_argument("--gap", type=float, default=3.0)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)
    result = analyze(args.results_tree, args.evals, args.min_recur, args.gap)
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(render(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
