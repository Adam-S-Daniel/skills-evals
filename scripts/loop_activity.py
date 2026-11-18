"""Which activity belongs to the continuous improvement loop.

The Explorer's Activity log shows only the loop's own work (Adam,
2026-11-18): eval runs, loop jobs and changes to targets. One rule serves the
public document (scripts/explorer_public.py) and the private dashboard
(dashboard/build.py; its live pull request and issue datasets apply the same
evals/loop-activity.json in explorer/src/private/loaders.js):

  * a workflow run or scheduled-task run is the loop's when
    evals/automatic-spend.yml marks its job `in_loop` (the same mark the spend
    forecast and the allowance guard use). A workflow is judged by its
    definition's name and `<repo>/<file>`, never by a run's title, which can
    name anything;
  * a pull request is the loop's when its head branch starts with one of
    `pull_branch_prefixes`;
  * an issue is the loop's when its title starts with one of
    `issue_title_prefixes` or it carries one of `issue_labels`.

evals/loop-activity.json holds the three lists (JSON, so the private page
bundles it; it has no room for comments). Keep them in step with
_agent-guidance docs/routines/fleet-worker.md (the loop role's pull requests
and loop issues) and the branch names the loop's scripts push.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml

import automatic_spend

EVALS = Path(__file__).resolve().parent.parent / "evals"
RULES_FILE = EVALS / "loop-activity.json"
SPEND_FILE = EVALS / "automatic-spend.yml"


@lru_cache(maxsize=None)
def rules(path: Path = RULES_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def spend_config(path: Path = SPEND_FILE) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _job_in_loop(name: str, extra: str = "") -> bool:
    cfg = spend_config()
    cat = automatic_spend.categorize(name, cfg["categories"], extra)
    return automatic_spend.loop_membership(name, cat, cfg, extra) is True


def workflow_in_loop(repo: str, path: str | None, name: str | None) -> bool:
    """`repo` is owner/name, `path` the run's `.github/workflows/<file>`,
    `name` the workflow's own name (not the run's title)."""
    file = str(path or "").rsplit("/", 1)[-1]
    if not file and not name:
        return False
    return _job_in_loop(name or file, f"{str(repo).split('/')[-1]}/{file}" if file else "")


def task_in_loop(name: str | None) -> bool:
    return bool(name) and _job_in_loop(str(name))


def pull_in_loop(head_ref) -> bool:
    return isinstance(head_ref, str) and head_ref.startswith(tuple(rules()["pull_branch_prefixes"]))


def issue_in_loop(title, labels) -> bool:
    names = {(lb.get("name") if isinstance(lb, dict) else lb) for lb in labels or []}
    return (isinstance(title, str) and title.startswith(tuple(rules()["issue_title_prefixes"]))) \
        or bool(names & set(rules()["issue_labels"]))
