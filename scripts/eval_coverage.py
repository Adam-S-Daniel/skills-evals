#!/usr/bin/env python3
"""Coverage census: every skill in every registry, and whether it has an eval.

Part of https://github.com/Adam-S-Daniel/skills-evals/issues/64. This is the
LOCAL, read-only half: it reads registry checkouts and this repo's `evals/`
tree, prints a table, and writes nothing. Publishing the table (a workflow
job, an `eval-results` commit, a README badge) is a separate step.

    python3 scripts/eval_coverage.py \\
        --registry adam-agentskills=PATH --registry cms-platform=PATH \\
        --registry adamdaniel.ai=PATH --registry adam-agentskills-private=PATH \\
        [--json] [--check] [--include-private-names]

WHAT A ROW IS. Every `SKILL.md` matched by a registry's `layout` glob in
`harness/registries.yml` is one row, resolved by the harness's own
`resolve_registries` (so `--registry NAME=PATH`, `$SKILLS_EVALS_REGISTRIES`
and the layouts are the ones `run_eval.py` uses, not a second copy). Its
status is mechanical:

  covered  at least one fixture under `evals/<x>/fixture.yaml` or
           `evals/<x>/<y>/fixture.yaml` names this skill in its `skill:` field
           and this registry in its `registry:` field. `fixtures` counts them,
           so one flat fixture and several nested ones both register.
  skipped  no fixture, but `evals/non-coverage.yml` has a row for the pair,
           and that row carries the reason.
  gap      neither.

A fixture with no `skill:` field (the `guidance` and `propagation` subjects)
is not a skill fixture and is ignored.

THE DENOMINATOR IS THE PART THAT LIES, so the script refuses (exit 2, nothing
printed to stdout) rather than report a partial census: a registry in
`harness/registries.yml` with no `--registry` path, a path that is not a
directory, a layout that matches no skill, a fixture whose `registry:` is
missing or unknown, a malformed or unknown-field `non-coverage.yml`. Nothing
falls back to a sibling directory: the operator names every checkout.

PROBLEMS, reported beside the rows and failing `--check`:

  stale_skip         a non-coverage row names a skill its registry no longer
                     has (a rename must not hide behind a skip)
  skip_but_covered   a non-coverage row for a skill that also has a fixture
  orphan_fixture     a fixture names a skill its registry does not have
  duplicate_skill    one skill name in two bundles of one registry, which
                     makes (registry, skill) ambiguous

EXIT CODES. 0: census printed (and, under `--check`, no gap and no problem).
1: `--check` and a gap or a problem. 2: refused, or a usage error.

PRIVATE REGISTRY. This repo is public and so is CI output. For a registry in
PRIVATE_REGISTRIES the table carries counts only: no skill name appears in
markdown or JSON unless `--include-private-names` is passed, and
`evals/non-coverage.yml` may not hold rows for it (the loader refuses). A
private skip lives in an operator-held file passed as
`--private-non-coverage PATH`, same schema, rows for private registries only.

Output is deterministic (registry order from registries.yml, then bundle and
skill name; no clock, no absolute paths). Stdlib plus PyYAML.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
import run_eval  # noqa: E402

# An explicit allowlist, not a name-pattern guess. test_issue_64 asserts every
# registries.yml entry whose name says "private" is listed here, so a new
# private registry cannot arrive with its skill names printable.
PRIVATE_REGISTRIES = frozenset({"adam-agentskills-private"})

DEFAULT_NON_COVERAGE = REPO_ROOT / "evals" / "non-coverage.yml"
DEFAULT_EVALS = REPO_ROOT / "evals"

# Field names are deliberately plain: a name such as "key" or "token" next to
# a high-entropy value trips the fleet's gitleaks rule.
SKIP_FIELDS = ("registry", "skill", "decision", "reason")

STATUSES = ("covered", "skipped", "gap")


class CensusRefusal(Exception):
    """The census cannot be trusted; refuse (exit 2) instead of printing."""


# --- inputs ---------------------------------------------------------------

def resolve(registry_flags: list[str] | None) -> dict[str, dict]:
    """One local checkout per registry in harness/registries.yml, via the
    harness's own resolver; no registry may fall back to a sibling default."""
    try:
        resolved = run_eval.resolve_registries(
            registry_flags, os.environ.get("SKILLS_EVALS_REGISTRIES"), REPO_ROOT)
    except ValueError as exc:
        raise CensusRefusal(str(exc)) from exc
    for name, entry in resolved.items():
        if entry["source"] == "sibling default":
            raise CensusRefusal(
                f"registry {name!r} has no --registry {name}=PATH: the census "
                "never guesses a checkout, because a registry it cannot see "
                "makes the denominator short")
        if not entry["path"].is_dir():
            raise CensusRefusal(
                f"registry {name!r} ({entry['source']}) does not resolve to a "
                "directory")
    return resolved


def enumerate_skills(entry: dict) -> list[dict]:
    """Every SKILL.md the registry's layout matches, as unclassified rows."""
    layout = entry["layout"]
    try:
        parts = run_eval._layout_parts(layout)
    except ValueError as exc:
        raise CensusRefusal(f"registry {entry['name']!r}: {exc}") from exc
    # Wildcards before the skill-name segment are the bundle/plugin name.
    bundle_idx = [i for i, part in enumerate(parts[:-2]) if "*" in part]
    rows = []
    for skill_md in sorted(entry["path"].glob(layout)):
        if not skill_md.is_file():
            continue
        rel = skill_md.relative_to(entry["path"]).parts
        rows.append({
            "registry": entry["name"],
            "bundle": "/".join(rel[i] for i in bundle_idx) or None,
            "skill": skill_md.parent.name,
        })
    rows.sort(key=lambda r: (r["bundle"] or "", r["skill"]))
    if not rows:
        raise CensusRefusal(
            f"registry {entry['name']!r} yields no skills for layout "
            f"{layout!r}: a registry with nothing in it is a wrong path or a "
            "wrong layout, not a zero")
    return rows


def _load_yaml(path: Path, what: str):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except OSError as exc:
        raise CensusRefusal(f"cannot read {what} {path}: {exc.strerror}") from exc
    except yaml.YAMLError as exc:
        raise CensusRefusal(f"{what} {path} is not valid YAML: {exc}") from exc


def count_fixtures(evals_dir: Path, resolved: dict[str, dict]) -> dict:
    """{(registry name, skill): fixture count} from `skill:` / `registry:`."""
    if not evals_dir.is_dir():
        raise CensusRefusal(f"evals directory {evals_dir} is not a directory")
    paths = sorted(evals_dir.glob("*/fixture.yaml")) + sorted(
        evals_dir.glob("*/*/fixture.yaml"))
    counts: dict[tuple[str, str], int] = {}
    for path in paths:
        doc = _load_yaml(path, "fixture")
        if not isinstance(doc, dict):
            raise CensusRefusal(f"fixture {path.relative_to(evals_dir)} is not a mapping")
        skill = doc.get("skill")
        if skill is None:
            continue  # a guidance / propagation subject, not a skill fixture
        label = path.relative_to(evals_dir).as_posix()
        if not isinstance(skill, str):
            raise CensusRefusal(f"fixture {label}: 'skill:' must be a string")
        url = doc.get("registry")
        if not isinstance(url, str) or not url.strip():
            raise CensusRefusal(
                f"fixture {label} names skill {skill!r} but has no 'registry:'")
        try:
            run_eval._validate_skill_name(skill)
            name = run_eval.registry_for_url(resolved, url)["name"]
        except ValueError as exc:
            raise CensusRefusal(f"fixture {label}: {exc}") from exc
        counts[(name, skill)] = counts.get((name, skill), 0) + 1
    return counts


def load_skips(path: Path, resolved: dict[str, dict], *, private: bool,
               into: dict) -> None:
    """Merge one non-coverage file into `into`: {(registry, skill): row}."""
    doc = _load_yaml(path, "non-coverage file")
    if not isinstance(doc, dict) or set(doc) != {"skips"} or not isinstance(
            doc["skips"], list):
        raise CensusRefusal(
            f"{path.name}: expected a mapping with exactly one key, 'skips:', "
            "a list of rows")
    for i, row in enumerate(doc["skips"]):
        where = f"{path.name} skips[{i}]"
        if not isinstance(row, dict) or set(row) != set(SKIP_FIELDS):
            raise CensusRefusal(
                f"{where}: a row has exactly the fields "
                f"{', '.join(SKIP_FIELDS)}")
        for field in SKIP_FIELDS:
            if not isinstance(row[field], str) or not row[field].strip():
                raise CensusRefusal(f"{where}: '{field}' must be a non-blank string")
        registry, skill = row["registry"], row["skill"]
        if registry not in resolved:
            raise CensusRefusal(
                f"{where}: registry {registry!r} is not in harness/registries.yml")
        if (registry in PRIVATE_REGISTRIES) != private:
            raise CensusRefusal(
                f"{where}: " + (
                    "the operator-held private file takes rows for private "
                    "registries only" if private else
                    "rows for a private registry may not be committed (the "
                    "skill name would be public); use --private-non-coverage"))
        try:
            run_eval._validate_skill_name(skill)
        except ValueError as exc:
            raise CensusRefusal(f"{where}: {exc}") from exc
        if (registry, skill) in into:
            raise CensusRefusal(f"{where}: a second row for the same registry and skill")
        into[(registry, skill)] = row


# --- the census -----------------------------------------------------------

def build_census(resolved: dict[str, dict], fixtures: dict, skips: dict) -> dict:
    registries = []
    problems = []
    seen_skills = set()
    for name, entry in resolved.items():
        rows = enumerate_skills(entry)
        by_name: dict[str, int] = {}
        for row in rows:
            by_name[row["skill"]] = by_name.get(row["skill"], 0) + 1
            seen_skills.add((name, row["skill"]))
            key = (name, row["skill"])
            row["fixtures"] = fixtures.get(key, 0)
            row["reason"] = None
            if row["fixtures"]:
                row["status"] = "covered"
            elif key in skips:
                row["status"] = "skipped"
                row["reason"] = skips[key]["reason"]
            else:
                row["status"] = "gap"
        for skill, n in sorted(by_name.items()):
            if n > 1:
                problems.append({"kind": "duplicate_skill", "registry": name,
                                 "skill": skill})
        counts = {"total": len(rows)}
        for status in STATUSES:
            counts[status] = sum(1 for r in rows if r["status"] == status)
        registries.append({
            "name": name, "layout": entry["layout"],
            "private": name in PRIVATE_REGISTRIES,
            "counts": counts, "skills": rows})
    for (name, skill), row in sorted(skips.items()):
        if (name, skill) not in seen_skills:
            problems.append({"kind": "stale_skip", "registry": name, "skill": skill})
        elif fixtures.get((name, skill)):
            problems.append({"kind": "skip_but_covered", "registry": name,
                             "skill": skill})
    for (name, skill), _n in sorted(fixtures.items()):
        if (name, skill) not in seen_skills:
            problems.append({"kind": "orphan_fixture", "registry": name,
                             "skill": skill})
    problems.sort(key=lambda p: (p["registry"], p["kind"], p["skill"]))
    totals = {"total": sum(r["counts"]["total"] for r in registries)}
    for status in STATUSES:
        totals[status] = sum(r["counts"][status] for r in registries)
    return {"schema": 1, "registries": registries, "totals": totals,
            "problems": problems}


def redact(census: dict, include_private_names: bool) -> dict:
    """The publishable form: counts only for a private registry (rows and the
    skill of any problem in it are dropped) unless names were asked for."""
    out = {**census, "include_private_names": include_private_names,
           "registries": [], "problems": []}
    for reg in census["registries"]:
        withheld = reg["private"] and not include_private_names
        reg = {**reg, "names_withheld": withheld}
        if withheld:
            reg["skills"] = []
        out["registries"].append(reg)
    private_names = {r["name"] for r in census["registries"] if r["private"]}
    for problem in census["problems"]:
        if problem["registry"] in private_names and not include_private_names:
            problem = {k: v for k, v in problem.items() if k != "skill"}
        out["problems"].append(problem)
    return out


# --- rendering ------------------------------------------------------------

def _cell(text) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render_json(census: dict) -> str:
    return json.dumps(census, indent=2, sort_keys=True) + "\n"


def render_markdown(census: dict) -> str:
    lines = ["# Skill eval coverage census", "",
             "| Registry | Skills | Covered | Skipped | GAP |",
             "|---|---:|---:|---:|---:|"]
    for reg in census["registries"]:
        c = reg["counts"]
        lines.append(f"| {_cell(reg['name'])} | {c['total']} | {c['covered']} | "
                     f"{c['skipped']} | {c['gap']} |")
    t = census["totals"]
    lines.append(f"| **Total** | {t['total']} | {t['covered']} | {t['skipped']} "
                 f"| {t['gap']} |")
    for reg in census["registries"]:
        lines += ["", f"## {reg['name']}", ""]
        if reg["names_withheld"]:
            lines.append("Skill names withheld for this private registry; "
                         "counts above. `--include-private-names` lists them.")
            continue
        lines += ["| Bundle | Skill | Status | Fixtures | Reason |",
                  "|---|---|---|---:|---|"]
        for row in reg["skills"]:
            status = "GAP" if row["status"] == "gap" else row["status"]
            lines.append(
                f"| {_cell(row['bundle'] or '')} | {_cell(row['skill'])} | "
                f"{status} | {row['fixtures']} | {_cell(row['reason'] or '')} |")
    lines += ["", "## Problems", ""]
    if not census["problems"]:
        lines.append("None.")
    for problem in census["problems"]:
        who = f" `{problem['skill']}`" if "skill" in problem else ""
        lines.append(f"- {problem['kind']}: {problem['registry']}{who}")
    return "\n".join(lines) + "\n"


# --- entry point ----------------------------------------------------------

def run(args: argparse.Namespace) -> tuple[int, str]:
    resolved = resolve(args.registry)
    fixtures = count_fixtures(args.evals_dir, resolved)
    skips: dict = {}
    load_skips(args.non_coverage, resolved, private=False, into=skips)
    if args.private_non_coverage:
        load_skips(args.private_non_coverage, resolved, private=True, into=skips)
    census = redact(build_census(resolved, fixtures, skips),
                    args.include_private_names)
    text = render_json(census) if args.json else render_markdown(census)
    failed = census["totals"]["gap"] or census["problems"]
    return (1 if args.check and failed else 0), text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Census of every skill in every registry: covered / "
                    "skipped / GAP. Read-only.")
    ap.add_argument("--registry", action="append", metavar="NAME=PATH",
                    help="local checkout of a registry in harness/registries.yml "
                         "(repeatable; every registry there needs one)")
    ap.add_argument("--evals-dir", type=Path, default=DEFAULT_EVALS)
    ap.add_argument("--non-coverage", type=Path, default=DEFAULT_NON_COVERAGE)
    ap.add_argument("--private-non-coverage", type=Path,
                    help="operator-held skip file for private registries")
    ap.add_argument("--json", action="store_true",
                    help="JSON instead of markdown")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 on a GAP or a problem")
    ap.add_argument("--include-private-names", action="store_true",
                    help="list private-registry skill names (never in CI)")
    args = ap.parse_args(argv)
    try:
        code, text = run(args)
    except CensusRefusal as exc:
        print(f"eval_coverage: refusing: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
