#!/usr/bin/env python3
"""Keep one issue per issue-routed work item the weekly sweep plans (Adam, 2026-11-03).

  work_item_issues.py --items FILE [--dry-run] [--run-url URL]

`--items` is `{"routine_down": bool, "work": [...]}` plus, optionally,
`"subjects": {"skills": [...], "guidance": [...], "triggers": [...]}`: the
weekly plan's work items routed to an issue (scripts/plan_week.py), the
skills and guidance sections whose headroom that plan measured, and the
skills its trigger lane judged. Until now they reached only the sweep's step
summary.

* `fixture-broken` and `routine-outage` (EMPTY FIRES): a cell is
  fixture-broken after two fires that delivered nothing; the planner already
  re-fires a lost fire once (PENDING_WINDOW), so an issue means the re-fire
  was lost too and the fixture, the routine or the harness needs a fix.
* `needs-fixtures` and `needs-harder-fixtures` (IMPROVE ELIGIBILITY,
  skills-evals#659): a skill or guidance section the improve lane cannot
  work on until it has more fixtures, or a fixture it fails. These are the
  fixture writers' queue, so the issue is labeled `agent-ready` (the fleet
  worker's issue pass, _agent-guidance docs/reference/agent-issue-worker.md).
* `needs-trigger-set` (THE TRIGGER LANE, skills-evals#662): a rarely used
  skill with no reviewed evals/<skill>/trigger-eval-set.json. Also
  `agent-ready`: once the set lands, the weekly planner fires a trigger-only
  improve run for the skill.

KIND LABELS AND HEADER LINES (Adam, 2026-11-03, the fixture-queue tracking
the Evals Explorer shows, scripts/fixture_queue.py): a fleet-worker issue
carries ONE kind label beside `agent-ready`, the kind itself
(`needs-fixtures`, `needs-harder-fixtures` or `needs-trigger-set`), and
its body's marker line is followed by `Kind: <kind>`, `Subject: <key>` and
`Reason: <text>`, the reason fixed text built from the item's numbers
(`reason_of`). Labels may not exist yet: before any write that uses one,
`ensure_labels` lists the repository's labels and creates each missing one,
never editing one that exists; a create that fails is fine when a second
listing shows the label (another run made it). An open issue missing its
kind label gets it added (`add-label`), so issues filed before this change
catch up on the next run. An issue record without a `labels` list (unknown,
not empty) is never relabeled.

REAL FLEET WORK FIRST (Adam, 2026-11-03, skills-evals#656): a fixture
request asks the worker to rebuild a merged fleet pull request's situation,
with invented names, data and hosts, before inventing a task, and every new
fixture.yaml records where it came from in a top-level `origin:` mapping,
which scripts/fixture_pr_gate.py requires (`fixture_pr_gate.origin_problem`).
This replaces the real-work scaffold lane, paused in
routine-fixture-supply.yml.

ONE ISSUE PER ITEM, in skills-evals, found by a marker line in its body:
`<!-- skills-evals:fixture-broken:<fixture>:<model> -->` for a cell,
`<!-- skills-evals:routine-outage:<sweep start> -->` for an outage and
`<!-- skills-evals:<kind>:<skill or guidance/section> -->` for a fixture
need and `<!-- skills-evals:needs-trigger-set:<skill> -->` for a trigger set. Only issues github-actions[bot] opened count (retire_skill.ISSUE_AUTHOR).

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
  trigger set no longer listed,       close-issue when the trigger lane judged
  open issue                          that skill (`subjects.triggers`), by the
                                      same rule
  fleet-worker issue whose body       refresh-body: the instructions went
  differs from today's rendering      stale (the 2026-11-03 `origin:` line
                                      the fixture gate requires reached only
                                      new issues, so the worker followed the
                                      old text and its pull requests never
                                      merged). A changed run link alone is no
                                      difference; an issue labeled
                                      `agent-working` (a worker is mid-task)
                                      or without a `labels` list is left as is
  open fleet-worker issue without     add-label (beside whichever of the above
  its kind label                      applies)

A failed `gh` call for one item is recorded and the others still run; the
exit code is then 1. Exit 2 is bad input. `--dry-run` prints the plan as
JSON and writes nothing. Issue bodies are public: the plan's items carry
public fixture paths and model ids only (a private cell enters no band), and
a fixture need names only a skill whose fixtures all name adam-agentskills,
or a guidance section, and a trigger set only a public adam-agentskills skill
(the trigger lane never judges a private one).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import draft_new_skill  # noqa: E402
import fixture_pr_gate  # noqa: E402
import regression_issue  # noqa: E402
import retire_skill  # noqa: E402

EVALS_REPO = retire_skill.EVALS_REPO
FIXTURE_NEEDS = ("needs-fixtures", "needs-harder-fixtures")
TRIGGER_NEED = "needs-trigger-set"
#: The kinds filed for the fleet worker, labeled READY_LABEL.
READY_KINDS = (*FIXTURE_NEEDS, TRIGGER_NEED)
KINDS = ("fixture-broken", "routine-outage", *READY_KINDS)
_MARKER = re.compile(r"<!-- skills-evals:(" + "|".join(KINDS) + r"):(\S+) -->")
#: The label the fleet worker's issue pass works (agent-issue-worker.md).
READY_LABEL = "agent-ready"
#: Each label this script may put on an issue: (color, description), used
#: only to create a missing label; an existing one is never edited.
LABELS = {
    READY_LABEL: ("0e8a16", "Ready for the fleet worker's issue pass"),
    "needs-fixtures": ("1d76db", "Fixture request: a subject needs more fixtures"),
    "needs-harder-fixtures": ("5319e7", "Fixture request: a subject needs a fixture it fails"),
    TRIGGER_NEED: ("fbca04", "Fixture request: a skill needs a trigger eval set"),
}
_SKILL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_SECTION = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_FIXTURE = re.compile(r"evals/[A-Za-z0-9._/-]{1,200}")
_MODEL = re.compile(r"claude-[a-z0-9][a-z0-9.-]{0,62}|[a-z0-9][a-z0-9.-]{0,62}")
_START = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
RUN_PREFIX = regression_issue.RUN_PREFIX
DOCS = "docs/how-it-works.md"


def key_of(item: dict) -> str:
    """The item's marker id, after checking every field that reaches the body."""
    if item.get("kind") == TRIGGER_NEED:
        skill = item.get("skill")
        if not isinstance(skill, str) or not _SKILL.fullmatch(skill):
            raise ValueError(f"a {TRIGGER_NEED} item has no valid skill")
        return skill
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


def _weight(item: dict) -> str:
    value = item.get("weight")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "unknown"
    return f"{value:g}"


def reason_of(item: dict) -> str:
    """The `Reason:` line's text: fixed words and the item's numbers only,
    so scripts/fixture_queue.py and the dashboard can show it as is."""
    if item["kind"] == TRIGGER_NEED:
        return f"usage weight {_weight(item)}, no trigger set"
    return f"train headroom {_headroom(item)}, {item['fixtures']} fixture(s)"


def header(item: dict, key: str) -> list:
    """The marker line and the three header lines every fleet-worker issue
    body starts with (module docstring, KIND LABELS AND HEADER LINES)."""
    return [marker(item["kind"], key), f"Kind: {item['kind']}", f"Subject: {key}",
            f"Reason: {reason_of(item)}"]


#: The `origin:` mapping a fix PR's fixture.yaml must carry, shown in the
#: issue body as the worker should write it (fixture_pr_gate.origin_problem).
ORIGIN_EXAMPLE = [
    "```yaml",
    "origin:",
    "  kind: real-work   # or: invented",
    "  source: https://github.com/<owner>/<repo>/pull/<N>   # null when invented",
    f"  request: https://github.com/{EVALS_REPO}/issues/<this issue's number>",
    "```",
]


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
    lines = [*header(item, key), ""]
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
        listing = ("- its path appended to `evals/scheduled.yml`, so the weekly sweep runs "
                   "it, with a `readiness` note that starts exactly "
                   f"\"{fixture_pr_gate.FIXTURE_PR_NOTE} for skills-evals#<this issue's "
                   "number>:\" and then says what the fixture tests;")
    else:
        listing = ("- its path appended to `evals/unscheduled.yml` with exactly the reason "
                   f"\"{draft_new_skill.ISOLATION_REASON}\" (an isolation fixture, no "
                   "`context:`): routine-fixture-supply.yml gives it a context and moves "
                   "it to the schedule;")
    lines += ["", "Build it from real fleet work when you can (Adam, 2026-11-03): search "
              "merged pull requests in the fleet's repositories, under both owners "
              "(Adam-S-Daniel and jodidaniel), for one where the "
              f"{what}'s advice applied or an agent missed it, and rebuild that "
              "situation as a self-contained fixture with invented names, data and "
              "hosts (`example.com`). Never copy private content verbatim: this "
              "repository is public. When no real case fits, write an invented task "
              "instead.",
              "", "What a fix PR adds, in this repository:",
              f"- a new fixture at {where}, with objective checks that fail "
              "without the subject's advice and pass with it, not `draft: true`;",
              "- in that fixture.yaml, a top-level `origin:` mapping (required: the "
              "pull request does not merge itself without it). `kind: real-work` names "
              "the fleet pull request it was rebuilt from as `source`; `kind: invented` "
              "has `source: null`; `request` is this issue's URL:",
              *ORIGIN_EXAMPLE,
              listing,
              "- nothing else: no edit to an existing fixture, `harness/` or `scripts/`.",
              "", "A pull request that does exactly that, labeled `agent-authored`, merges "
              "itself once `test` passes (fixture-pr-gate.yml, scripts/fixture_pr_gate.py).",
              "Use `Refs` for this issue in the pull request, not `Closes`: the "
              "weekly sweep closes it once the plan stops listing this need, which "
              "takes runs of the new fixture.",
              "", f"The rule: `{DOCS}` and `scripts/plan_week.py`, IMPROVE ELIGIBILITY."]
    return title, lines


def trigger_need_body(key: str, item: dict | None = None) -> tuple:
    """(title, lines) of a needs-trigger-set issue: fixed text, the skill
    name, which key_of checked, and the item's usage weight. A trigger set
    carries no `origin:`: it is queries, not a rebuilt task."""
    item = item or {}
    path = f"evals/{key}/trigger-eval-set.json"
    lines = [*header({"kind": TRIGGER_NEED, **item}, key), "",
             f"The skill `{key}` is almost never used (at most one call in four weeks "
             "of the usage census), so its description is the likeliest reason. The "
             "trigger lane can improve that description with a trigger-only improve "
             "fire, which runs skill-creator's description loop, but only on a "
             "reviewed set of queries, and this skill has none.",
             "", "Before writing, read the skill's `SKILL.md` in adam-agentskills "
             f"(`plugins/*/skills/{key}/SKILL.md`): what it is for, and which nearby "
             "requests belong to another skill or to none.",
             "", "What a fix PR adds, in this repository:",
             f"- exactly one new file, `{path}`: a JSON list of objects with exactly "
             "the keys `query` (a string: a realistic user request, written as a user "
             "would type it) and `should_trigger` (a JSON boolean);",
             "- at least 8 should-trigger and 8 should-not-trigger queries (10 of each "
             "is better; `evals/writing-adrs/trigger-eval-set.json` is an example);",
             "- should-not-trigger queries that are near misses: adjacent topics where "
             "another skill or no skill fits, not random requests;",
             "- nothing else: no other file, fixture, `harness/` or `scripts/` change.",
             "", "A pull request that does exactly that, labeled `agent-authored`, merges "
             "itself once `test` passes (fixture-pr-gate.yml, scripts/fixture_pr_gate.py).",
             "Use `Refs` for this issue in the pull request, not `Closes`: the weekly "
             "sweep closes it once the plan stops listing this need. Once the set lands, "
             "the weekly planner fires a trigger-only improve run for the skill.",
             "", f"The rule: `{DOCS}` and `scripts/plan_week.py`, THE TRIGGER LANE."]
    return f"Needs a trigger eval set: skill {key}", lines


def body_of(item: dict, key: str, run_url: str | None) -> tuple:
    """(title, body) of a new issue."""
    if item["kind"] == TRIGGER_NEED:
        title, lines = trigger_need_body(key, item)
    elif item["kind"] in FIXTURE_NEEDS:
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


def fetch_issues(gh) -> list:
    """Every issue github-actions[bot] opened in skills-evals, any state:
    [{"number", "body", "state", "labels"}], `labels` the label names, or
    None when the record carries no list (unknown, so never relabeled).
    regression_issue.fetch_issues with the labels added."""
    text = gh(["api", "--paginate", f"repos/{EVALS_REPO}/issues?state=all&per_page=100",
               "--jq", ".[] | select(.pull_request == null) | "
                       "{number: .number, body: (.body // \"\"), author: .user.login, "
                       "state: .state, labels: [.labels[]?.name]}"])
    out = []
    for item in retire_skill._json_lines(text):
        if item.get("author") != retire_skill.ISSUE_AUTHOR:
            continue
        number, state, body = item.get("number"), item.get("state"), item.get("body")
        if type(number) is not int or number < 1 or state not in ("open", "closed") \
                or not isinstance(body, str):
            raise retire_skill.RetireError("an issue record from the API is malformed")
        labels = item.get("labels")
        if labels is not None and not (isinstance(labels, list)
                                       and all(isinstance(n, str) for n in labels)):
            raise retire_skill.RetireError("an issue record from the API is malformed")
        out.append({"number": number, "body": body, "state": state, "labels": labels})
    return out


def ensure_labels(gh, names, labels: dict = LABELS) -> None:
    """Create each label in `names` that skills-evals lacks, from `labels`'
    color and description; never edit one that exists. A create that fails
    is fine when a fresh listing shows the label (another run made it);
    otherwise RetireError."""
    def listing() -> set:
        text = gh(["api", "--paginate", f"repos/{EVALS_REPO}/labels?per_page=100",
                   "--jq", ".[].name"])
        return {line.strip() for line in text.splitlines() if line.strip()}

    have = listing()
    for name in sorted(set(names) - have):
        color, description = labels[name]
        try:
            gh(["label", "create", name, "-R", EVALS_REPO, "--color", color,
                "--description", description])
        except retire_skill.RetireError:
            if name not in listing():
                raise retire_skill.RetireError(f"could not create the label {name}") from None


def labels_of(action: dict) -> list:
    """The labels an action's commands put on an issue."""
    if action["action"] == "create-issue" and action["kind"] in READY_KINDS:
        return [READY_LABEL, action["kind"]]
    if action["action"] == "add-label":
        return [action["kind"]]
    return []


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


def judged_subjects(items: dict) -> tuple:
    """(the marker keys of every skill and section whose headroom the plan
    measured, the skills its trigger lane judged)."""
    subjects = items.get("subjects")
    if subjects is None:
        return set(), set()
    if not isinstance(subjects, dict) or any(
            not isinstance(subjects.get(k, []), list)
            or not all(isinstance(v, str) for v in subjects.get(k, []))
            for k in ("skills", "guidance", "triggers")):
        raise ValueError("--items `subjects` is not {skills: [...], guidance: [...], "
                         "triggers: [...]}")
    return (set(subjects.get("skills", []))
            | {f"guidance/{s}" for s in subjects.get("guidance", [])},
            set(subjects.get("triggers", [])))


def _stable(body: str) -> str:
    """The body without its workflow-run line and trailing blank lines, so a
    new run link or trailing whitespace alone is no change."""
    lines = [line.rstrip() for line in body.splitlines()
             if not line.startswith(RUN_PREFIX)]
    return "\n".join(lines).rstrip()


def plan(items: dict, issues: list, run_url: str | None) -> list:
    if not isinstance(items, dict) or not isinstance(items.get("work"), list) \
            or not isinstance(items.get("routine_down"), bool):
        raise ValueError("--items is not {routine_down, work}")
    judged, judged_triggers = judged_subjects(items)
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
        elif kind in READY_KINDS:
            title, body = body_of(item, key, run_url)
            if _stable(body) != _stable(found["body"]):
                labels = found.get("labels")
                if labels is None or "agent-working" in labels:
                    action["reason"] = "a worker is on it"
                else:
                    action.update(action="refresh-body", body=body,
                                  reason="the issue's instructions are out of date")
        actions.append(action)

    for (kind, key), found in sorted(existing.items()):
        if (kind, key) in listed:
            continue
        if kind == "routine-outage" and items["routine_down"]:
            actions.append({"kind": kind, "key": key, "issue": found["number"],
                            "action": "none", "reason": "the routine is still down"})
            continue
        if (kind in FIXTURE_NEEDS and key not in judged) \
                or (kind == TRIGGER_NEED and key not in judged_triggers):
            actions.append({"kind": kind, "key": key, "issue": found["number"],
                            "action": "none", "reason": "the plan did not judge this subject"})
            continue
        if kind == TRIGGER_NEED:
            why = ("the plan no longer lists this need: the skill has a trigger set, "
                   "or it is used more often, retiring or out of scope")
        elif kind in FIXTURE_NEEDS:
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
    closing = {a["issue"] for a in actions if a["action"] == "close-issue"}
    for (kind, key), found in sorted(existing.items()):
        if kind in READY_KINDS and found["number"] not in closing \
                and found.get("labels") is not None and kind not in found["labels"]:
            actions.append({"kind": kind, "key": key, "issue": found["number"],
                            "action": "add-label", "reason": "the issue lacks its kind label"})
    return actions


def commands(action: dict) -> list:
    issue = str(action["issue"])
    if action["action"] == "create-issue":
        label = [arg for name in labels_of(action) for arg in ("--label", name)]
        return [["gh", "issue", "create", "-R", EVALS_REPO, "--title", action["title"],
                 *label, "--body-file", "-"]]
    if action["action"] == "add-label":
        return [["gh", "issue", "edit", issue, "-R", EVALS_REPO, "--add-label", action["kind"]]]
    if action["action"] == "refresh-body":
        return [["gh", "issue", "edit", issue, "-R", EVALS_REPO, "--body-file", "-"]]
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
        actions = plan(items, fetch_issues(gh), args.run_url)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"work_item_issues: {exc}", file=sys.stderr)
        return 2
    except retire_skill.RetireError as exc:
        print(f"work_item_issues: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        out.write(json.dumps({"dry_run": True, "labels": sorted(
            {name for action in actions for name in labels_of(action)}), "actions": [
            {**a, "would_run": commands(a)} for a in actions]}, indent=2, sort_keys=True) + "\n")
        return 0
    needed = sorted({name for action in actions for name in labels_of(action)})
    if needed:
        try:
            ensure_labels(gh, needed)
        except retire_skill.RetireError as exc:
            # Without its labels no issue can be filed or relabeled.
            print(f"work_item_issues: {exc}", file=sys.stderr)
            return 1
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
