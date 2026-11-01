#!/usr/bin/env python3
"""Write `explorer/latest.json`: the public data behind the Skill Evals Explorer (#72).

  explorer_data.py --results-tree DIR --roster evals/roster.yml
                   --policy evals/gate-policy.yml --as-of TIME
                   --repository-commit SHA --results-commit SHA --out FILE
                   [--evals-dir DIR] [--guidance-manifest eval-coverage.yml]
                   [--guidance DIR] [--registry NAME=PATH ...]
                   [--regression-issues FILE]

It reuses scripts/compute_gates.py for the validated run index
(`build_index`) and the verdicts (`compute`), then reshapes them for a page
that anyone can read. The document is PUBLIC, so what it leaves out matters
more than what it carries:

  * PRIVACY GATE. A skill is listed only if the census
    (`<results-tree>/coverage/latest.json`) names it in a registry with
    `private: false`. A skill with runs but no such census row (a private
    registry's skill, or a retired one) is dropped, and so is every alert
    about it. The census is the one source of what is public.
  * No session id, digest, harness commit, transcript or e-mail is ever
    copied from a run. `finish` is the last gate: it refuses (exit 2) a
    document containing a session-id prefix, an `@` outside a URL or a
    64-hex digest, so a future field added by mistake fails loudly instead
    of publishing.

Each skill and section also carries `confidence` (the levels its gate
bounds reach, `subject_confidence`) and `next_test` (its place in the
planner's eval queue or its next re-check, `test_queue`) and `stakes`
(its evals/stakes.yml level, `normal` with no row; scripts/stakes.py); each
skill carries
`usage`, its invocations in `usage/weekly-local.json`, whose window is the
top-level `usage` (None without a census: unknown, not zero).

Only paired skill runs are listed (a `with` and a `without` arm of one run
directory, fixture and model). A guidance run lists whichever of its modes
ran. Counts are per arm over the scored trials (infrastructure failures and
agent-errored trials are left out, as in the gate). Rates are not computed
here and nothing is rounded: the page rounds at display.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compute_gates  # noqa: E402
import gates  # noqa: E402  (harness/ is on sys.path via compute_gates)
import plan_week  # noqa: E402
import skill_usage  # noqa: E402
import stakes as stakes_mod  # noqa: E402

SCHEMA_VERSION = 1
SHA_RE = re.compile(r"[0-9a-f]{40}")
#: A guidance pair's role in the gate -> the mode the page names it by.
MODE_NAMES = {("in_situ", "with"): "full", ("in_situ", "without"): "full_minus_section",
              ("alone", "with"): "section", ("alone", "without"): "none"}
REGRESSION_MARKER = "skills-evals:regression:"
_URL_RE = re.compile(r"https?://\S+")
_DIGEST_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")


class Refused(Exception):
    """The document would leak something the contract forbids."""


def iso(stamp: str | None) -> str | None:
    """`YYYYMMDDTHHMMSSZ` as `YYYY-MM-DDTHH:MM:SSZ`."""
    if stamp is None:
        return None
    return f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z"


def bare_version(versions: list) -> str | None:
    """`2.1.304` from `2.1.304 (Claude Code)`; None when unknown."""
    for value in versions:
        if isinstance(value, str) and value.split():
            return value.split()[0]
    return None


def arm_numbers(record: dict) -> dict | None:
    """One arm of one run reduced to the contract's counts, or None when no
    trial counted. Only scored trials count: an infrastructure failure or an
    agent-errored trial has no checks to add up (harness/gates.py
    `trial_record`)."""
    scored = [t for t in record["trials"] if t.get("scored")]
    if not scored:
        return None
    judges = [t["judge"] for t in scored if t.get("judge") is not None]
    costs = [t["cost_usd"] for t in scored if t.get("cost_usd") is not None]
    return {"trials": len(scored),
            "checks_passed": sum(sum(1 for ok in t["checks"].values() if ok) for t in scored),
            "checks_total": sum(len(t["checks"]) for t in scored),
            "judge_mean": sum(judges) / len(judges) if judges else None,
            "cost_usd": sum(costs) if costs else None}


def _newest_first(runs: list) -> list:
    return sorted(runs, key=lambda r: (r["at"], r["report_url"]), reverse=True)


def skill_runs(index: dict) -> dict:
    """{skill: [run entries, newest first]}: only runs with both arms
    counted, paired by run directory, fixture and requested model."""
    groups: dict = {}
    for record in index["runs"]:
        groups.setdefault((record["skill"], record["path"], record["fixture"],
                           record["model"]), {}).setdefault(record["role"], record)
    out: dict = {}
    for (skill, _path, fixture, model), arms in groups.items():
        numbers = {role: arm_numbers(arms[role]) for role in ("with", "without") if role in arms}
        if len(numbers) != 2 or None in numbers.values():
            continue
        first = arms["with"]
        out.setdefault(skill, []).append({
            "fixture": fixture, "model": model, "at": iso(first["timestamp"]),
            "cli_version": bare_version(first["cli_versions"] + arms["without"]["cli_versions"]),
            "with": numbers["with"], "without": numbers["without"],
            "report_url": gates._link(first["report"])["url"]})
    return {skill: _newest_first(runs) for skill, runs in out.items()}


def guidance_runs(index: dict) -> dict:
    """{section: [run entries, newest first]}, each with the modes that ran."""
    groups: dict = {}
    for record in index["guidance_runs"]:
        mode = MODE_NAMES[(record["pair"], record["role"])]
        numbers = arm_numbers(record)
        if numbers is None:
            continue
        group = groups.setdefault((record["skill"], record["path"], record["fixture"],
                                   record["model"]), {"record": record, "modes": {}})
        group["modes"].setdefault(mode, numbers)
    out: dict = {}
    for (section, _path, fixture, model), group in groups.items():
        record = group["record"]
        out.setdefault(section, []).append({
            "fixture": fixture, "model": model, "at": iso(record["timestamp"]),
            "cli_version": bare_version(record["cli_versions"]),
            "modes": dict(sorted(group["modes"].items())),
            "report_url": gates._link(record["report"])["url"]})
    return {section: _newest_first(runs) for section, runs in out.items()}


def load_census(tree: Path) -> dict:
    """The coverage census, which is the privacy gate's only input."""
    try:
        doc = json.loads((tree / "coverage" / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"no readable coverage census in the results tree: {exc}") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("registries"), list):
        raise ValueError("the coverage census has no registries list")
    return doc


def public_census(census: dict) -> tuple[dict, dict]:
    """({skill: census row} over the registries with `private: false`, the
    census totals over those registries). The first registry listing a name
    wins."""
    rows: dict = {}
    totals = {"covered": 0, "skipped": 0, "gap": 0, "total": 0}
    for registry in census["registries"]:
        if not isinstance(registry, dict) or registry.get("private") is not False:
            continue
        counts = registry.get("counts") or {}
        for key in totals:
            totals[key] += counts[key] if isinstance(counts.get(key), int) else 0
        for row in registry.get("skills") or []:
            if isinstance(row, dict) and isinstance(row.get("skill"), str):
                rows.setdefault(row["skill"], {**row, "registry": registry.get("name")})
    publication = census.get("publication")
    as_of = publication.get("as_of") if isinstance(publication, dict) else None
    return rows, {"as_of": as_of, **totals}


def load_manifest(path: Path | None) -> list:
    if path is None:
        return []
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("the guidance manifest is not a list")
    return [r for r in rows if isinstance(r, dict) and isinstance(r.get("id"), str)]


_MARKER_RE = re.compile(re.escape(REGRESSION_MARKER) + r"(?:guidance:)?[A-Za-z0-9._-]+")


def issue_markers(listing: list) -> dict:
    """{marker: issue url} from `gh issue list --json url,body` rows. The
    bodies are untrusted text: only a marker pattern is read from one, and
    only a github.com URL is kept."""
    out: dict = {}
    for row in listing:
        if not isinstance(row, dict) or not isinstance(row.get("url"), str):
            continue
        for marker in _MARKER_RE.findall(row.get("body") or ""):
            out.setdefault(marker, row["url"])
    return out


def regression_url(issues: dict, subject: str, name: str):
    marker = REGRESSION_MARKER + ("guidance:" if subject == "guidance" else "") + name
    url = issues.get(marker, issues.get(marker[len(REGRESSION_MARKER):]))
    return url if isinstance(url, str) and url.startswith("https://github.com/") else None


def build_alerts(gates_doc: dict, regressions: dict | None, issues: dict,
                 skill_names: set, section_ids: set) -> list:
    """Retire verdicts and regression rows, about listed subjects only."""
    alerts = []
    for name, verdict in sorted(gates_doc["skills"].items()):
        if verdict["verdict"] == "retire" and name in skill_names:
            alerts.append({"kind": "retire", "subject": "skill", "name": name,
                           "text": f"{name} shows no measurable benefit and is due for "
                                   f"retirement: {verdict['reason']}.", "url": None})
    for name, verdict in sorted((gates_doc.get("guidance") or {}).items()):
        if verdict["verdict"] == "retire" and name in section_ids:
            alerts.append({"kind": "retire", "subject": "guidance", "name": name,
                           "text": f"The guidance section {name} shows no measurable benefit and "
                                   f"is due for retirement: {verdict['reason']}.", "url": None})
    for row in (regressions or {}).get("rows") or []:
        if not isinstance(row, dict) or row.get("verdict") not in ("regressed", "lost-delta"):
            continue
        subject, name = row.get("subject"), row.get("id")
        listed = skill_names if subject == "skill" else section_ids
        if subject not in ("skill", "guidance") or name not in listed:
            continue
        alert = {"kind": "regression", "subject": subject, "name": name,
                 "model": row.get("model"),
                 "text": f"{name} {row['verdict']}"
                         + (f" on {row['fixture']}" if row.get("fixture") else "")
                         + (f": {row['reason']}" if row.get("reason") else "") + ".",
                 "url": regression_url(issues, subject, name)}
        alerts.append(alert)
    return alerts


def skill_description(registries: dict | None, registry: str | None, name: str) -> str | None:
    """What the skill is for: the `description` in its SKILL.md front matter, in
    the census registry's checkout, whitespace collapsed. None when the checkout
    is absent, the skill has no single SKILL.md there, or it has no description.
    An `@` is dropped (a package name such as `@scope/pkg` reads the same
    without it), so a description never trips `finish`."""
    entry = (registries or {}).get(registry or "")
    if not entry or not compute_gates.run_eval._SKILL_NAME_RE.fullmatch(name):
        return None
    root = Path(entry["path"])
    matches = [p for p in sorted(root.glob(f"**/skills/{name}/SKILL.md"))
               if p.is_file() and not p.is_symlink()]
    if len(matches) != 1:
        return None
    try:
        text = matches[0].read_text(encoding="utf-8")
        if not text.startswith("---"):
            return None
        front = yaml.safe_load(text.split("---", 2)[1])
    except (OSError, UnicodeDecodeError, IndexError, yaml.YAMLError):
        return None
    desc = front.get("description") if isinstance(front, dict) else None
    if not isinstance(desc, str) or not desc.strip():
        return None
    return " ".join(desc.replace("@", "").split())


def current_text_runs(verdict: dict) -> int:
    """How many eval runs were made on the subject's CURRENT text: the with-arm
    run entries across its verdict cells (a guidance section's in-situ cells and
    its `alone` cells). Only the with arm counts because `gates.pool_cells` keeps
    a with-arm run only when its `tested_digest` equals the subject's digest on
    main, so an edit empties it; a without-arm run pools across text changes and
    says nothing about the current text. A cell with no `with` key counts 0, and
    a subject with no verdict has 0."""
    cells = list(verdict.get("cells") or [])
    cells += (verdict.get("alone") or {}).get("cells") or []
    return sum(len((c.get("runs") or {}).get("with") or []) for c in cells)


def subject_confidence(verdict: dict) -> dict:
    """How sure the gate is, as levels in [0, 1): `helps`, the highest
    confidence at which some cell's delta (objective or judge) is above 0, and
    `no_help`, the highest at which every cell's objective delta is under the
    margin (a cell with no objective figure gives 0). Both None while no
    cell has a figure. The keep and remove rules compare these with the policy levels;
    the page shows them as percentages."""
    cells = verdict.get("cells") or []
    if not cells:
        return {"helps": None, "no_help": None}
    helps = [d["helps_confidence"] for c in cells for d in (c.get("objective"), c.get("judge"))
             if isinstance(d, dict) and "helps_confidence" in d]
    no_help = [(c.get("objective") or {}).get("no_help_confidence", 0.0) for c in cells]
    if not helps:
        return {"helps": None, "no_help": None}
    return {"helps": max(helps), "no_help": min(no_help)}


#: The eval bands the page lists as the test queue, in the planner's order.
QUEUE_BANDS = ("safety", "missing", "near", "recheck")


def test_queue(cells: list, model_weights: dict, now) -> dict:
    """{(kind, name): {"position", "band", "due"}} for every subject with a
    scheduled cell: `position` (1 = next) is the subject's first cell in the
    planner's eval bands, in `plan_week.allocate`'s order before the budget
    cuts it off; a subject with no cell in a band gets `due`, the earliest
    re-check of a cell the planner re-checks (newest run + plan_week.recheck_after), or
    neither when no test is planned. `scheduled` is False (from the caller)
    for a subject with no fixture on `evals/scheduled.yml`. The
    budget decides how far down the queue a sweep gets, so this is an order,
    not a date."""
    ctx = {"cells": cells, "model_weights": model_weights, "removal_prs": [],
           "reservation": 1.0, "overrun": 1.0, "points_per_usd": None}
    bands, _work = plan_week.eval_items(ctx, now)

    def key(cell_or_item):
        section = next((c["section"] for c in cells if c["fixture"] == cell_or_item["fixture"]
                        and c.get("section")), None)
        return ("guidance", section) if section else ("skill", cell_or_item["skill"])

    out, position = {}, 0
    for band in QUEUE_BANDS:
        for item in sorted(bands[band], key=lambda i: (*i["order"], i["cost"], i["fixture"],
                                                       i["model"], i["skill"])):
            subject = key(item)
            if subject not in out:
                position += 1
                out[subject] = {"position": position, "band": band, "due": None,
                                "scheduled": True}
    for cell in cells:
        subject = key(cell)
        newest = plan_week._stamp_time(cell["newest"])
        if subject in out and out[subject]["position"] is not None:
            continue
        entry = out.setdefault(subject, {"position": None, "band": None, "due": None,
                                         "scheduled": True})
        if newest is None or cell.get("stakes") == "none" \
                or (cell["class"] in ("missing", "insufficient") and cell.get("verdict") != "keep"):
            continue
        due = plan_week._iso(newest + plan_week.recheck_after(cell))
        if entry["due"] is None or due < entry["due"]:
            entry["due"] = due
    return out


def renumber(subjects: list) -> None:
    """Number the queued subjects of one list 1, 2, ... in queue order (in
    place), so a place in line counts only subjects the page lists: an
    unlisted (private) subject ahead in the planner's queue leaves no gap."""
    queued = sorted((s for s in subjects if s["next_test"]["position"] is not None),
                    key=lambda s: s["next_test"]["position"])
    for rank, subject in enumerate(queued, 1):
        subject["next_test"] = {**subject["next_test"], "position": rank}


def usage_counts(tree: Path) -> tuple:
    """({skill: invocations}, the window) from `usage/weekly-local.json`:
    every week of the file summed, so a skill the census never saw is 0 while
    the file exists. ({}, None) without a readable file (unknown, not zero).
    The census already folds every non-public name into `other`; the caller
    attaches a count only to a listed skill."""
    doc = skill_usage.load(tree / "usage" / "weekly-local.json")
    if doc is None:
        return {}, None
    counts = {}
    for row in doc["rows"]:
        if row["kind"] == "skill" and isinstance(row.get("invocations"), int):
            counts[row["name"]] = counts.get(row["name"], 0) + row["invocations"]
    source = next((s for s in doc["sources"] if s.get("scope") == "transcripts"), {})
    window = {"from": source.get("from"), "to": source.get("to"),
              "sessions_scanned": source.get("sessions_scanned"), "surface": source.get("surface")}
    return counts, window


def build(tree: Path, roster_path: Path, policy_path: Path, evals_dir: Path, as_of: str,
          repository_commit: str, results_commit: str, registries: dict | None = None,
          guidance_dir: Path | None = None, manifest: list | None = None,
          issues: dict | None = None) -> dict:
    compact = compute_gates.parse_as_of(as_of)
    gates_doc = compute_gates.compute(tree, roster_path, policy_path, evals_dir, compact,
                                      registries, guidance_dir)
    index = compute_gates.build_index(tree, evals_dir, compact)
    census_rows, coverage = public_census(load_census(tree))
    roster = yaml.safe_load(roster_path.read_text(encoding="utf-8"))
    by_skill, by_section = skill_runs(index), guidance_runs(index)
    now = plan_week._stamp_time(compact)
    queue = {}
    if (evals_dir / "scheduled.yml").is_file():
        queue = test_queue(plan_week.eval_cells(evals_dir, gates_doc, [], now),
                           plan_week.model_weights(tree, gates_doc["roster_models"]), now)
    counts, usage_window = usage_counts(tree)
    unqueued = {"position": None, "band": None, "due": None, "scheduled": False}
    table = stakes_mod.load(evals_dir / "stakes.yml", evals_dir)

    def stakes_of(kind, name):
        entry = table.get((kind, name))
        return {"level": entry["stakes"], "reason": entry["reason"],
                "covered_by": entry["covered_by"]} if entry else {"level": "normal"}

    skills = []
    for name, row in sorted(census_rows.items()):
        verdict = gates_doc["skills"].get(name) or {}
        skills.append({"name": name, "registry": row["registry"], "bundle": row.get("bundle"),
                       "description": skill_description(registries, row["registry"], name),
                       "status": row.get("status"), "skip_reason": row.get("reason"),
                       "verdict": verdict.get("verdict"), "verdict_reason": verdict.get("reason"),
                       "current_text_runs": current_text_runs(verdict),
                       "confidence": subject_confidence(verdict),
                       "next_test": queue.get(("skill", name), unqueued),
                       "stakes": stakes_of("skill", name),
                       "usage": None if usage_window is None
                       else {"invocations": counts.get(name, 0)},
                       "runs": by_skill.get(name, [])})

    renumber(skills)

    guidance_verdicts = gates_doc.get("guidance") or {}
    rows = manifest or [{"id": s, "heading": s, "status": "covered"} for s in sorted(by_section)]
    sections = []
    for row in rows:
        verdict = guidance_verdicts.get(row["id"]) or {}
        sections.append({
            "id": row["id"], "heading": row.get("heading", row["id"]),
            "bytes": row.get("bytes"), "status": row.get("status"),
            "skip_reason": row.get("reason"), "verdict": verdict.get("verdict"),
            "verdict_reason": verdict.get("reason"),
            "current_text_runs": current_text_runs(verdict),
            "alone_verdict": (verdict.get("alone") or {}).get("verdict"),
            "confidence": subject_confidence(verdict),
            "next_test": queue.get(("guidance", row["id"]), unqueued),
            "stakes": stakes_of("guidance", row["id"]),
            "runs": by_section.get(row["id"], [])})

    renumber(sections)

    try:
        regressions = json.loads((tree / "regressions" / "latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        regressions = None
    alerts = build_alerts(gates_doc, regressions if isinstance(regressions, dict) else None,
                          issues or {}, {s["name"] for s in skills}, {s["id"] for s in sections})
    stamps = [r["at"] for s in (*skills, *sections) for r in s["runs"]]
    policy = gates_doc["policy"]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso(compact),
        "newest_run": max(stamps, default=None),
        "source": {"repository": "Adam-S-Daniel/skills-evals",
                   "repository_commit": repository_commit, "results_commit": results_commit},
        "roster": {"arms": [{"model": a["id"], "reason": a.get("reason")}
                            for a in roster["arms"]],
                   "judge": {"model": roster["judge"]["id"],
                             "reason": roster["judge"].get("reason")}},
        "policy": {k: policy[k] for k in ("benefit_confidence", "retire_confidence",
                                          "min_cli_versions", "objective_margin")},
        "skills": skills, "guidance": {"sections": sections},
        "coverage": coverage, "alerts": alerts, "usage": usage_window}


def finish(doc: dict) -> str:
    """The document as text, or Refused: the last gate before it is public."""
    text = json.dumps(doc, indent=1, sort_keys=True, allow_nan=False) + "\n"
    for forbidden in ("cse_", "session_"):
        if forbidden in text:
            raise Refused(f"the document contains {forbidden!r}")
    if "@" in _URL_RE.sub("", text):
        raise Refused("the document contains an '@' outside a URL")
    if _DIGEST_RE.search(text):
        raise Refused("the document contains a 64-hex digest")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-tree", required=True, type=Path)
    parser.add_argument("--roster", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    parser.add_argument("--guidance-manifest", type=Path, metavar="PATH",
                        help="_agent-guidance's agents-md/eval-coverage.yml")
    parser.add_argument("--guidance", type=Path, metavar="PATH",
                        help="an _agent-guidance checkout, passed to compute_gates")
    parser.add_argument("--registry", action="append", metavar="NAME=PATH")
    parser.add_argument("--regression-issues", type=Path, metavar="FILE",
                        help="JSON {marker: issue url}, or the raw `gh issue list --json url,body` "
                             "list, for the regression alerts")
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--results-commit", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        for sha in (args.repository_commit, args.results_commit):
            if not SHA_RE.fullmatch(sha):
                raise ValueError("a commit is not a 40-character lowercase hex sha")
        issues = (json.loads(args.regression_issues.read_text(encoding="utf-8"))
                  if args.regression_issues else {})
        if isinstance(issues, list):  # raw `gh issue list --json url,body`
            issues = issue_markers(issues)
        if not isinstance(issues, dict):
            raise ValueError("--regression-issues is not a JSON object or issue list")
        doc = build(args.results_tree, args.roster, args.policy, args.evals_dir,
                    args.as_of, args.repository_commit, args.results_commit,
                    compute_gates.flag_registries(args.registry), args.guidance,
                    load_manifest(args.guidance_manifest), issues)
        text = finish(doc)
    except Refused as exc:
        print(f"explorer_data: refusing to publish: {exc}", file=sys.stderr)
        return 2
    except (gates.GatePolicyError, ValueError, OSError, KeyError, RecursionError,
            yaml.YAMLError) as exc:
        print(f"explorer_data: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
