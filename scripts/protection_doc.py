#!/usr/bin/env python3
"""The eval-protection document for registries whose results stay private.

_agent-guidance's scripts/eval-protected.js decides whether a pull request
edits an eval-protected subject from the public explorer document
(explorer/latest.json), reading only each skill's `name`, `registry`,
`verdict` and `current_text_runs` and each guidance section's `id`, `heading`,
`verdict` and `current_text_runs`. A private registry's skills must never
appear in that public document (#81): their results live in the private
repository's own `persistent/eval-results` branch. So the private
repository's CI builds the same small subset here, from its own results tree,
inside its own private job, and the gate reads it from there.

The shape is the explorer subset exactly (`schema_version` 1, `skills`, and an
empty `guidance.sections`), and the verdict and run count come from the same
code the explorer uses (compute_gates.compute, explorer_data.current_text_runs).
A skill is listed only when its registry is one of the `--registry` names
given. The only thing printed is a count; skill content is never echoed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compute_gates  # noqa: E402
import explorer_data  # noqa: E402

delivery = compute_gates.delivery
run_eval = compute_gates.run_eval


def fixture_registry_urls(evals_dir: Path, skill: str) -> set:
    """The `registry:` values of `skill`'s fixtures on main (empty when none
    names one or the skill has no readable fixture)."""
    eval_dir = evals_dir / skill
    try:
        directories = run_eval.resolve_fixture_dirs(eval_dir, None) if eval_dir.is_dir() else []
    except (run_eval.FixtureLayoutError, OSError):
        return set()
    urls = set()
    for directory in directories:
        try:
            doc = yaml.safe_load((directory / run_eval.FIXTURE_FILE).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            continue
        if isinstance(doc, dict) and doc.get("registry") is not None:
            urls.add(str(doc["registry"]))
    return urls


def skill_registry(registries: dict, evals_dir: Path, skill: str):
    """The name of the given registry that owns `skill`, or None. A fixture's
    `registry:` field decides, as in compute_gates.tested_digest; without one,
    the skill's single copy among the given checkouts."""
    try:
        urls = fixture_registry_urls(evals_dir, skill)
        if urls:
            if len(urls) != 1:
                return None
            return run_eval.registry_for_url(registries, next(iter(urls)))["name"]
        matches = delivery._registry_matches(registries, None, skill)
    except (ValueError, OSError, delivery.DeliveryError):
        return None
    if len(matches) != 1:
        return None
    for name, entry in registries.items():
        if delivery._identity(entry) == matches[0][0]:
            return entry.get("name", name)
    return None


def build(tree: Path, roster: Path, policy: Path, evals_dir: Path, as_of: str,
          registries: dict) -> dict:
    gates_doc = compute_gates.compute(tree, roster, policy, evals_dir,
                                      compute_gates.parse_as_of(as_of), registries, None)
    skills = []
    for name, verdict in sorted(gates_doc["skills"].items()):
        registry = skill_registry(registries, evals_dir, name)
        if registry is None:
            continue
        skills.append({"name": name, "registry": registry,
                       "verdict": verdict.get("verdict"),
                       "current_text_runs": explorer_data.current_text_runs(verdict)})
    return {"schema_version": 1, "skills": skills, "guidance": {"sections": []}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-tree", required=True, type=Path)
    parser.add_argument("--registry", action="append", required=True, metavar="NAME=PATH")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--evals-dir", type=Path, default=REPO_ROOT / "evals")
    parser.add_argument("--roster", type=Path, default=REPO_ROOT / "evals" / "roster.yml")
    parser.add_argument("--policy", type=Path, default=REPO_ROOT / "evals" / "gate-policy.yml")
    args = parser.parse_args(argv)
    try:
        registries = compute_gates.flag_registries(args.registry)
        doc = build(args.results_tree, args.roster, args.policy, args.evals_dir,
                    args.as_of, registries)
        text = json.dumps(doc, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (compute_gates.gates.GatePolicyError, ValueError, OSError, RecursionError) as exc:
        print(f"protection_doc: {type(exc).__name__}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"protection_doc: {len(doc['skills'])} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
