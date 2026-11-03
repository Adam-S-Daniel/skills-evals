#!/usr/bin/env python3
"""Keep one issue per issue-routed work item the weekly sweep plans (Adam, 2026-11-03).

  work_item_issues.py --items FILE [--dry-run] [--run-url URL]

`--items` is `{"routine_down": bool, "work": [...]}` plus, optionally,
`"subjects": {"skills": [...], "guidance": [...]}`: the weekly plan's
work items routed to an issue (scripts/plan_week.py) and the skills and
guidance sections that plan judged. Until now they reached only the
sweep's step summary.

* `fixture-broken` and `routine-outage` (EMPTY FIRES): a cell is
  fixture-broken after two fires that delivered nothing; the planner already
  re-fires a lost fire once (PENDING_WINDOW), so an issue means the re-fire
  was lost too and the fixture, the routine or the harness needs a fix.
* `needs-fixtures` and `needs-harder-fixtures` (IMPROVE ELIGIBILITY,
  skills-evals#659): a skill or guidance section the improve lane cannot
  work on until it has more fixtures, or a fixture it fails. These are the
  fixture writers' queue, so the issue is labeled `agent-ready` (the fleet
  worker's issue pass, _agent-guidance docs/reference/agent-issue-worker.md).

ONE ISSUE PER ITEM, in skills-evals, found by a marker line in its body:
`<!-- skills-evals:fixture-broken:<fixture>:<model> -->` for a cell,
`<!-- skills-evals:routine-outage:<sweep start> -->` for an outage and
`<!-- skills-evals:<kind>:<skill or guidance/section> -->` for a fixture
need. Only issues github-actions[bot] opened count (retire_skill.ISSUE_AUTHOR).

  item listed, no open issue          create-issue
  item listed, open issue             none (the issue says what it needs)
  cell no longer listed, open issue   close-issue: the cell delivered, or its
                                      empty fires aged out and it is retried
  outage no longer listed, open       close-issue, unless the routine is
  issue                               still down
  fixture need no longer listed,      close-issue when the plan judged that
  open issue                          subject (`subjects`); a subject the plan
                                      did not see (an input it lacked) keeps
                                      its issue, so a partial plan never
                                      closes and refiles the queue

A failed `gh` call for one item is recorded and the others still run; the
exit code is then 1. Exit 2 is bad input. `--dry-run` prints the plan as
JSON and writes nothing. Issue bodies are public: the plan's items carry
public fixture paths and model ids only (a private cell enters no band), and
a fixture need names only a skill whose fixtures all name adam-agentskills,
or a guidance section.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import draft_new_skill  # noqa: E402
import regression_issue  # noqa: E402
import retire_skill  # noqa: E402

EVALS_REPO = retire_skill.EVALS_REPO
FIXTURE_NEEDS = ("needs-fixtures", "needs-harder-fixtures")
KINDS = ("fixture-broken", "routine-outage", *FIXTURE_NEEDS)
_MARKER = re.compile(r"<!-- skills-evals:(" + "|".join(KINDS) + r"):(\S+) -->")
#: The label the fleet worker's issue pass works (agent-issue-worker.md).
READY_LABEL = "agent-ready"
_SKILL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_SECTION = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_FIXTURE = re.compile(r"evals/[A-Za-z0-9._/-]{1,200}")
_MODEL = re.compile(r"claude-[a-z0-9][a-z0-9.-]{0,62}|[a-z0-9][a-z0-9.-]{0,62}")
_START = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
RUN_PREFIX = regression_issue.RUN_PREFIX
DOCS = "docs/how-it-works.md"


def key_of(item: dict) -> str:
    """The item's marker id, after checking every field that reaches the body."""
    if item.get("kind") in FIXTURE_NEEDS:
        section, skill = item.get("section") or "", item.get("skill") or ""
        count = item.get("fixtures")
        if type(count) is not int or count < 0 or bool(section) == bool(skill):
            raise ValueError(f"a {item['kind']} item names no one skill or section")
        if section:
            if not isinstance(section, str) or not _SECTION.fullmatch(section):
                raise ValueError(f"a {item['kind']} item has no valid section")
            return f"guidance/{section}"
        if not isinstance(skill, str) or not _SKILL.fullmatch(skill):
            raise ValueError(f"a {item['kind']} item has no valid skill")
        return skill
    if item.get("kind") == "fixture-broken":
        fixture, model = item.get("fixture"), item.get("model")
        if not (isinstance(fixture, str) and _FIXTURE.fullmatch(fixture)
                and ".." not in fixture and isinstance(model, str)
                and _MODEL.fullmatch(model)):
            raise ValueError("a fixture-broken item has no valid fixture and model")
        return f"{fixture}:{model}"
    start = item.get("sweep_start")
    if not (isinstance(start, str) and _START.fullmatch(start)) \
            or type(item.get("fires")) is not int:
        raise ValueError("a routine-outage item has no valid sweep_start and fires")
    return start


def marker(kind: str, key: str) -> str:
    return f"<!-- skills-evals:{kind}:{key} -->"


def _headroom(item: dict) -> str:
    value = item.get("headroom")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "unknown"
    return f"{value:.2f}"


def fixture_need_body(item: dict, key: str) -> tuple:
    """(title, lines) of a needs-fixtures or needs-harder-fixtures issue."""
    harder = item["kind"] == "needs-harder-fixtures"
    section = key.startswith("guidance/")
    name = key.split("/", 1)[1] if section else key
    what = f"guidance section `{name}`" if section else f"skill `{name}`"
    where = (f"`evals/guidance/{name}/<name>/fixture.yaml` (`subject: guidance`, "
             f"`section: {name}`, declaring the `full` ablation arm)" if section else
             f"`evals/{name}/<name>/fixture.yaml` (`skill: {name}`, naming "
             "adam-agentskills, nested beside its other fixtures)")
    title = (f"Needs a harder fixture: {what}" if harder
             else f"Needs more fixtures: {what}").replace("`", "")
    lines = [marker(item["kind"], key), ""]
    if harder:
        lines += [f"The improve lane cannot work on the {what}: it already passes "
                  f"enough of its checks that no edit can show a gain (train headroom "
                  f"{_headroom(item)}, under the 0.10 an edit must gain; "
                  f"{item['fixtures']} fixture(s)). The next step is a fixture it FAILS: "
                  "a realistic task where the subject's advice matters and an agent "
                  "without it gets something checkably wrong."]
    else:
        lines += [f"The improve lane cannot work on the {what}: it has "
                  f"{item['fixtures']} fixture(s), under the 4 an improve run needs "
                  f"(one is held out), and train headroom {_headroom(item)}. "
                  "Add fixtures until it has at least four."]
    if section:
        listing = ("- its path appended to `evals/scheduled.yml` with a `readiness` note, "
                   "so the weekly sweep runs it;")
    else:
        listing = ("- its path appended to `evals/unscheduled.yml` with exactly the reason "
                   f"\"{draft_new_skill.ISOLATION_REASON}\" (an isolation fixture, no "
                   "`context:`): routine-fixture-supply.yml gives it a context and moves "
                   "it to the schedule;")
    lines += ["", "What a fix PR adds, in this repository:",
              f"- a new fixture at {where}, with objective checks that fail "
              "without the subject's advice and pass with it, not `draft: true`;",
              listing,
              "- nothing else: no edit to an existing fixture, `harness/` or `scripts/`.",
              "", "A pull request that does exactly that, labeled `agent-authored`, merges "
              "itself once `test` passes (fixture-pr-gate.yml, scripts/fixture_pr_gate.py).",
              "Use `Refs` for this issue in the pull request, not `Closes`: the "
              "weekly sweep closes it once the plan stops listing this need, which "
              "takes runs of the new fixture.",
              "", f"The rule: `{DOCS}` and `scripts/plan_week.py`, IMPROVE ELIGIBILITY."]
    return title, lines


def body_of(item: dict, key: str, run_url: str | None) -> tuple:
    """(title, body) of a new issue."""
    if item["kind"] in FIXTURE_NEEDS:
        title, lines = fixture_need_body(item, key)
    elif item["kind"] == "fixture-broken":
        title = f"Fixture broken: {item['fixture']} on {item['model']}"
        lines = [marker("fixture-broken", key), "",
                 f"Two eval fires of `{item['fixture']}` on `{item['model']}` delivered "
                 "no results, the second after the planner had already re-fired the "
                 "first. The cell is out of every band until this closes; the sweep "
                 "closes it when the cell delivers again or its empty fires age out.",
                 "", "What to check, in order:",
                 "- the fire runs of `routine-eval-fire.yml` for this fixture and model, "
                 "and the routine session id each one logs;",
                 "- whether a `claude/eval-<run id>` branch was pushed and rejected by "
                 "`routine-eval-ingest.yml`;",
                 "- a harness refusal for this fixture, run locally.",
                 "", f"The rule: `{DOCS}` and `scripts/plan_week.py`, EMPTY FIRES."]
    else:
        title = f"Routine outage: {item['fires']} fire(s) from {item['sweep_start']}"
        lines = [marker("routine-outage", key), "",
                 f"{item['fires']} eval fire(s) from {item['sweep_start']}, across at "
                 "least three cells, delivered nothing while nothing else delivered "
                 "either: the routine, not the fixtures. The planner fires one probe at "
                 "a time until one delivers; the sweep closes this once the routine is "
                 "no longer down.",
                 "", f"The rule: `{DOCS}` and `scripts/plan_week.py`, OUTAGES and THE "
                 "CIRCUIT BREAKER."]
    if run_url:
        lines += ["", f"{RUN_PREFIX}{run_url}"]
    return title, "\n".join(lines) + "\n"


def open_issues(issues: list) -> dict:
    """{(kind, key): lowest-numbered open issue} over every marker line."""
    found: dict = {}
    for issue in sorted(issues, key=lambda i: i["number"]):
        if issue["state"] != "open":
            continue
        for line in issue["body"].splitlines():
            match = _MARKER.fullmatch(line.strip())
            if match:
                found.setdefault(match.groups(), issue)
    return found


def judged_subjects(items: dict) -> set:
    """The marker keys of every skill and section the plan judged."""
    subjects = items.get("subjects")
    if subjects is None:
        return set()
    if not isinstance(subjects, dict) or any(
            not isinstance(subjects.get(k, []), list)
            or not all(isinstance(v, str) for v in subjects.get(k, []))
            for k in ("skills", "guidance")):
        raise ValueError("--items `subjects` is not {skills: [...], guidance: [...]}")
    return set(subjects.get("skills", [])) | {f"guidance/{s}" for s in subjects.get("guidance", [])}


def plan(items: dict, issues: list, run_url: str | None) -> list:
    if not isinstance(items, dict) or not isinstance(items.get("work"), list) \
            or not isinstance(items.get("routine_down"), bool):
        raise ValueError("--items is not {routine_down, work}")
    judged = judged_subjects(items)
    listed = {}
    for item in items["work"]:
        if isinstance(item, dict) and item.get("kind") in KINDS:
            listed[(item["kind"], key_of(item))] = item
    existing = open_issues(issues)
    actions = []
    for (kind, key), item in sorted(listed.items()):
        found = existing.get((kind, key))
        action = {"kind": kind, "key": key, "issue": found["number"] if found else None,
                  "action": "none", "reason": "the open issue stands"}
        if not found:
            title, body = body_of(item, key, run_url)
            action.update(action="create-issue", reason="no open issue",
                          title=title, body=body)
        actions.append(action)
    for (kind, key), found in sorted(existing.items()):
        if (kind, key) in listed:
            continue
        if kind == "routine-outage" and items["routine_down"]:
            actions.append({"kind": kind, "key": key, "issue": found["number"],
                            "action": "none", "reason": "the routine is still down"})
            continue
        if kind in FIXTURE_NEEDS and key not in judged:
            actions.append({"kind": kind, "key": key, "issue": found["number"],
                            "action": "none", "reason": "the plan did not judge this subject"})
            continue
        if kind in FIXTURE_NEEDS:
            why = ("the plan no longer lists this need: the subject has the fixtures "
                   "and headroom it needed, or it is retiring, paused or out of scope")
        elif kind == "routine-outage":
            why = "the routine is delivering again"
        else:
            why = ("the cell is no longer fixture-broken: it delivered, or its empty fires "
                   "aged out and it is being retried")
        actions.append({"kind": kind, "key": key, "issue": found["number"],
                        "action": "close-issue", "reason": why,
                        "comment": f"The weekly sweep no longer lists this: {why}. Closing."
                                   + (f"\n\n{RUN_PREFIX}{run_url}" if run_url else "")})
    return actions


def commands(action: dict) -> list:
    issue = str(action["issue"])
    if action["action"] == "create-issue":
        label = ["--label", READY_LABEL] if action["kind"] in FIXTURE_NEEDS else []
        return [["gh", "issue", "create", "-R", EVALS_REPO, "--title", action["title"],
                 *label, "--body-file", "-"]]
    if action["action"] == "close-issue":
        return [["gh", "issue", "comment", issue, "-R", EVALS_REPO, "--body-file", "-"],
                ["gh", "issue", "close", issue, "-R", EVALS_REPO, "--reason", "completed"]]
    return []


def main(argv: list | None = None, *, gh=retire_skill.default_gh, out=sys.stdout) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-url", default=None)
    args = parser.parse_args(argv)
    try:
        items = json.loads(args.items.read_text(encoding="utf-8"))
        actions = plan(items, regression_issue.fetch_issues(gh), args.run_url)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"work_item_issues: {exc}", file=sys.stderr)
        return 2
    except retire_skill.RetireError as exc:
        print(f"work_item_issues: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        out.write(json.dumps({"dry_run": True, "actions": [
            {**a, "would_run": commands(a)} for a in actions]}, indent=2, sort_keys=True) + "\n")
        return 0
    failed = 0
    for action in actions:
        stdin = action.get("body") or action.get("comment")
        try:
            for command in commands(action):
                gh(command[1:], stdin if "--body-file" in command else None)
        except retire_skill.RetireError as exc:
            failed += 1
            print(f"work_item_issues: {action['kind']} {action['key']}: {exc}", file=sys.stderr)
            continue
        if action["action"] != "none":
            out.write(f"{action['action']}: {action['kind']} {action['key']}"
                      + (f" (#{action['issue']})" if action["issue"] else "") + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
