#!/usr/bin/env python3
"""Give drafted skill fixtures an in-place context, then schedule them.

The draft loop (scripts/draft_new_skill.py) writes each new skill's fixtures
as isolation pairs, with no `context:`, because the skill is not on the
registry's main yet, and lists them in evals/unscheduled.yml with
`draft_new_skill.ISOLATION_REASON`. An isolation run's pooling key is
incomplete, so `gates.pool_cells` drops it, and the planner fires only
scheduled fixtures: left there, the skill could never reach keep or remove.
This step closes that gap with no person in the loop (Adam, 2026-10-26:
"closed loop with no human in the loop"). For each such row, once the
fixture's skill is on its registry's main, it:

1. picks the context repository (ADR 0012, decision 2): CONTEXT_FOR_SKILL,
   else the repository most of the skill's other in-place fixtures name,
   else CONTEXT_FOR_PLUGIN for the skill's bundle;
2. pins that repository's checked-out HEAD and the newest guidance revision
   whose bytes it shipped (`scaffold_real_work._build_context`);
3. measures both arms the way a run does (`run_eval._in_place_plan`, with
   main's copy of the skill in `with`) and sets each budget to the larger
   arm's bytes plus 25% (ADR 0012, "Context budgets");
4. appends the `context:` block to fixture.yaml and moves the row from
   unscheduled.yml to scheduled.yml with a "Promoted automatically" note.

A row whose skill is not on main yet, whose guidance cannot be proven, or
whose context does not resolve stays listed; the reason is printed and the
next run tries again. Nothing here runs a fixture or a model.

    python3 scripts/contextualize_fixtures.py \\
        --context-repo OWNER/REPO=PATH ... --registry NAME=PATH ... \\
        --as-of TIME [--apply]

stdout is `count=N` and `fixtures=<paths>`, for $GITHUB_OUTPUT.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "harness"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import yaml  # noqa: E402

import context  # noqa: E402
import delivery  # noqa: E402
import draft_new_skill  # noqa: E402
import run_eval  # noqa: E402
import scaffold_real_work as scaffold  # noqa: E402

#: The context repository for one skill, when its bundle's default is not the
#: repository it is for. red-ci-adamdaniel-ai is about that site's CI, and the
#: site's lock also deploys cms-platform's skills, which a session there loads
#: beside it (the overlap ADR 0012 exists to measure).
CONTEXT_FOR_SKILL = {"red-ci-adamdaniel-ai": "Adam-S-Daniel/adamdaniel.ai"}
#: The default context repository per adam-agentskills bundle. Both cloud-safe
#: bundles default to cms-platform, the CI-heaviest fleet repository and the
#: one most existing in-place fixtures name. The machine-bound bundles are
#: adopted by no fleet lock, so their skills are added to wsl-automation's
#: context, which a session on the owner's machine also loads (the
#: windows-elevation-from-wsl precedent): the `with` arm adds main's copy.
CONTEXT_FOR_PLUGIN = {
    "adam-anything-anywhere": "Adam-S-Daniel/cms-platform",
    "adam-coding-anywhere": "Adam-S-Daniel/cms-platform",
    "adam-coding-local": "Adam-S-Daniel/wsl-automation",
    "adam-non-coding-local": "Adam-S-Daniel/wsl-automation",
}
UNSCHEDULED = Path("evals") / "unscheduled.yml"
SCHEDULED = Path("evals") / "scheduled.yml"
FIXTURE_FILE = "fixture.yaml"


class Skip(Exception):
    """This fixture cannot be given a context now; the next run tries again."""


def candidates(root: Path) -> list[str]:
    """unscheduled.yml's isolation rows the draft loop wrote, whose fixture
    exists and still declares no `context:`, in file order."""
    doc = yaml.safe_load((root / UNSCHEDULED).read_text(encoding="utf-8"))
    out = []
    for row in doc.get("fixtures") or []:
        if row.get("reason") != draft_new_skill.ISOLATION_REASON:
            continue
        target = root / row["path"] / FIXTURE_FILE
        if not target.is_file():
            continue
        fixture = yaml.safe_load(target.read_text(encoding="utf-8"))
        if isinstance(fixture, dict) and "context" not in fixture \
                and isinstance(fixture.get("skill"), str):
            out.append(row["path"])
    return out


def sibling_repository(root: Path, skill: str, exclude: str) -> str | None:
    """The repository most of `skill`'s other in-place fixtures name (ties to
    the smallest name), or None."""
    counts = collections.Counter()
    base = root / "evals" / skill
    for path in sorted([base / FIXTURE_FILE, *base.glob(f"*/{FIXTURE_FILE}")]):
        if not path.is_file() or path.parent.relative_to(root).as_posix() == exclude:
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        ctx = doc.get("context") if isinstance(doc, dict) else None
        if isinstance(ctx, dict) and isinstance(ctx.get("repository"), str):
            counts[ctx["repository"]] += 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def choose_repository(root: Path, path: str, skill: str, bundle: str) -> str:
    if skill in CONTEXT_FOR_SKILL:
        return CONTEXT_FOR_SKILL[skill]
    sibling = sibling_repository(root, skill, path)
    if sibling:
        return sibling
    if bundle not in CONTEXT_FOR_PLUGIN:
        raise Skip(f"no default context repository for bundle {bundle}")
    return CONTEXT_FOR_PLUGIN[bundle]


def budgets(*arms: dict) -> dict:
    """Each key's limit: the larger arm's bytes plus 25%, rounded up."""
    return scaffold.measured_budgets({key: max(arm[key] for arm in arms)
                                      for key in context.BUDGET_KEYS})


class Measurer:
    """Resolves and measures a context from local checkouts, as a run does."""

    def __init__(self, repositories: dict[str, Path], registries: dict):
        self.repositories = repositories
        self.registries = registries
        #: One resolution per repository: its HEAD, guidance pin and frozen
        #: context are the same for every fixture placed there.
        self.built: dict[str, dict] = {}

    def bundle(self, skill: str, url: str | None) -> str:
        try:
            return run_eval.main_copy(self.registries, skill, url)[1]
        except delivery.DeliveryError as error:
            raise Skip(f"{skill} is not on its registry's main ({error.code})") from None

    def context_metadata(self, repository: str) -> dict:
        if repository in self.built:
            return self.built[repository]
        clone = self.repositories.get(repository)
        if clone is None:
            raise Skip(f"no checkout of {repository}")
        revision = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"],
                                  check=True, capture_output=True, text=True).stdout.strip()
        try:
            metadata, _ = scaffold._build_context(repository, revision, Path(clone),
                                                  self.repositories)
        except scaffold.ScaffoldError as error:
            raise Skip(str(error)) from None
        if metadata["guidance_revision"] is None:
            raise Skip(f"guidance unproven at {repository}@{revision[:12]}")
        self.built[repository] = metadata
        return metadata

    def __call__(self, fixture_dir: Path, repository: str) -> dict:
        metadata = self.context_metadata(repository)
        fixture = run_eval.load_fixture(fixture_dir)
        fixture["context"] = {**metadata, "budget": dict(context.BUDGET_MAX)}
        args = argparse.Namespace(context_repos=self.repositories)
        try:
            plan = run_eval._in_place_plan(fixture, args, self.registries, "skill")
        except (context.ContextError, delivery.DeliveryError) as error:
            raise Skip(f"the in-place plan refused ({error.code})") from None
        frozen = plan["frozen"]
        alone = dict(frozen.manifest["measurements"])
        with_arm = run_eval.with_arm_sizes(frozen, plan["subject"])
        return {**metadata, "budget": budgets(alone, with_arm),
                "action": plan["subject"].action}


def context_block(metadata: dict, date: str) -> str:
    how = ("the context deploys the skill, so the `without` arm leaves it out"
           if metadata["action"] == "removed" else
           "the context does not deploy the skill, so the `with` arm adds main's copy")
    b = metadata["budget"]
    return (f"\n# In-place context (ADR 0012), added on {date} by "
            "scripts/contextualize_fixtures.py:\n"
            f"# {how}. Each budget is the larger arm's measured bytes plus 25%.\n"
            "context:\n"
            f"  repository: {metadata['repository']}\n"
            f"  revision: {metadata['revision']}\n"
            f"  guidance_revision: {metadata['guidance_revision']}\n"
            "  budget:\n"
            f"    guidance_bytes: {b['guidance_bytes']}\n"
            f"    skill_catalog_bytes: {b['skill_catalog_bytes']}\n"
            f"    skill_payload_bytes: {b['skill_payload_bytes']}\n")


def write_context(target: Path, metadata: dict, date: str) -> None:
    text = target.read_text(encoding="utf-8")
    before = yaml.safe_load(text)
    if not isinstance(before, dict) or "context" in before:
        raise scaffold.ScaffoldError(f"{target}: already has a `context:`")
    added = text + ("" if text.endswith("\n") else "\n") + context_block(metadata, date)
    expected = {key: metadata[key] for key in ("repository", "revision", "guidance_revision",
                                               "budget")}
    if yaml.safe_load(added) != {**before, "context": expected}:
        raise scaffold.ScaffoldError(f"{target}: adding `context:` changed something else")
    target.write_text(added, encoding="utf-8")


def unlist(root: Path, path: str) -> None:
    target = root / UNSCHEDULED
    text = target.read_text(encoding="utf-8")
    before = yaml.safe_load(text)
    row = re.compile(rf"^  - path: {re.escape(path)}\n    reason: [^\n]*\n", re.M)
    if len(row.findall(text)) != 1:
        raise scaffold.ScaffoldError(f"{path}: not one two-line row in {UNSCHEDULED}")
    after_text = row.sub("", text)
    after = yaml.safe_load(after_text)
    kept = [r for r in before["fixtures"] if r["path"] != path]
    if after != {**before, "fixtures": kept}:
        raise scaffold.ScaffoldError(f"{path}: unlisting changed something else")
    target.write_text(after_text, encoding="utf-8")


def schedule(root: Path, rows: list[tuple[str, dict]], date: str) -> None:
    target = root / SCHEDULED
    lines = []
    for path, metadata in rows:
        note = (f"{scaffold.PROMOTED_NOTE} on {date} by contextualize_fixtures.py: a "
                f"drafted isolation pair given an in-place context on "
                f"{metadata['repository']} at {metadata['revision'][:12]} (ADR 0012), "
                "budgets measured with 25% headroom; its isolation pair ran when it was drafted.")
        lines.append(f"  - path: {path}\n    readiness: {json.dumps(note)}\n")
    text = target.read_text(encoding="utf-8")
    target.write_text(text + ("" if text.endswith("\n") else "\n") + "".join(lines),
                      encoding="utf-8")


def contextualize(root: Path, measure, date: str, apply: bool) -> tuple[list, list]:
    """(done, skipped): each done entry is (path, metadata); each skipped one
    (path, reason). With `apply`, the done fixtures are written."""
    done, skipped = [], []
    for path in candidates(root):
        fixture = yaml.safe_load((root / path / FIXTURE_FILE).read_text(encoding="utf-8"))
        skill = fixture["skill"]
        try:
            bundle = measure.bundle(skill, fixture.get("registry"))
            repository = choose_repository(root, path, skill, bundle)
            metadata = measure(root / path, repository)
        except Skip as why:
            skipped.append((path, str(why)))
            continue
        done.append((path, metadata))
    if apply:
        for path, metadata in done:
            write_context(root / path / FIXTURE_FILE, metadata, date)
            unlist(root, path)
        if done:
            schedule(root, done, date)
    return done, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--context-repo", action="append", default=[],
                        metavar="OWNER/REPO=PATH")
    parser.add_argument("--registry", action="append", default=[], metavar="NAME=PATH")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    import compute_gates  # noqa: PLC0415
    try:
        as_of = compute_gates.parse_as_of(args.as_of)
        repositories = context.parse_context_repos(args.context_repo)
        registries = run_eval.resolve_registries(args.registry, None, REPO_ROOT)
    except (ValueError, context.ContextError) as error:
        print(f"contextualize_fixtures: bad arguments ({type(error).__name__})", file=sys.stderr)
        return 2
    date = f"{as_of[:4]}-{as_of[4:6]}-{as_of[6:8]}"
    try:
        done, skipped = contextualize(REPO_ROOT, Measurer(repositories, registries), date,
                                      args.apply)
    except scaffold.ScaffoldError as error:
        print(f"contextualize_fixtures: {error}", file=sys.stderr)
        return 2
    for path, reason in skipped:
        print(f"skipped {path}: {reason}", file=sys.stderr)
    for path, metadata in done:
        print(f"{path}: {metadata['repository']}@{metadata['revision'][:12]} "
              f"({metadata['action']})", file=sys.stderr)
    print(f"count={len(done)}")
    print("fixtures=" + " ".join(path for path, _ in done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
