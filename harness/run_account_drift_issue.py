#!/usr/bin/env python3
"""Turn the Tier-3 account audit's published verdict into ONE tracking issue.

`evals/propagation/ROUTINE.md` step 5 asks the Routine-fired session to open,
edit and close this issue. It never has and it never can: those sessions carry
no `mcp__*` tool and this environment has no `gh` CLI, so the fired session has
no route to the GitHub API at all (measured — see ROUTINE.md, layer 3). The
issue lifecycle therefore has to belong to something that CAN reach the API,
which is CI. ROUTINE.md's own design note ("A second route the issue does not
consider") reaches the same conclusion and names the one trigger that a
CI-skip token in the publish message does not suppress: a `schedule`. That is
what `.github/workflows/account-store-drift.yml` runs, and this is the part of
it that decides anything.

The whole file is a PURE function of three published inputs plus a clock:
`latest.json`, the `.bootstrapped` marker, and `evals/propagation/fixture.yaml`.
It reaches no network, spawns nothing, and holds no credential — the `gh`
lookup and the writes live in the workflow, one step further out, where the
only thing that can reach the issue is a single scripted step below a dry-run
bail-out. That split is deliberate: the interesting logic is the one that has
to be testable, and a decision that needs a token to exercise is a decision
nobody exercises.

It keys every branch on `account_store.freshness_verdict`, which is also what
`run_propagation.py`'s freshness gate keys on. Duplicating the status rules
here — "red means status != pass, more or less" — is how the two repos' idea of
"drifted" quietly diverges, and the first sign of that would be an issue that
opens and closes on a different condition from the gate that people actually
watch.

Usage:
    python3 harness/run_account_drift_issue.py evals/propagation \\
        --account-latest ../eval-results/propagation/account/latest.json \\
        --account-marker ../eval-results/propagation/.bootstrapped \\
        --existing-issue-number "" --body-out "$RUNNER_TEMP/drift.md"

Exit codes: 0 always for a decision — "no issue is called for" is a finding,
not an error, and a runner that reds on it teaches people to ignore the run.
2 only for an invocation that could not be understood at all (no fixture, a
non-numeric issue number), because that is a broken caller rather than a
verdict.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from propagation import account_store  # noqa: E402

EXIT_OK, EXIT_USAGE = 0, 2

# The HTML comment that makes this issue findable by something other than its
# title. A title is edited by hand the first time someone rewords it; the
# marker is what the workflow's lookup matches on as well, so a reworded title
# degrades to "open a second issue" rather than to "silently edit whatever came
# back first". ROUTINE.md step 5 mandates this exact string, so the two halves
# of the design agree on one identifier even though CI now owns the lifecycle.
MARKER = "<!-- propagation-account-audit -->"

TITLE = "Account skill store drifted from registry (automated Tier-3 audit)"

# agentskills builds the upload artifact; nothing in this repo can. The link
# goes to the workflow rather than to an issue on purpose: agentskills#59, the
# repair issue ROUTINE.md and skills-evals#48 both point at, is CLOSED, and a
# body that sends a reader to a closed issue every morning is worse than one
# that sends them nowhere.
ZIPS_WORKFLOW = ("https://github.com/Adam-S-Daniel/agentskills/actions/"
                 "workflows/account-skill-zips.yml")

# Two shapes that must never reach a public issue body, scrubbed out of every
# finding detail before it is rendered. Both repos are public and so is every
# issue on them (fleet AGENTS.md, "Data exposure in CI and public repos").
#
# The paths are the live case rather than a hypothetical one: the
# `account-copy-missing` and `registry-description-unreadable` details are
# built by interpolating a real directory, and on the surface that publishes
# this result that directory sits under `$HOME`. The finding is worth
# rendering — it names the skill and what is wrong with it — but the absolute
# path in it says nothing a reader needs and quite a lot about a machine.
ADDRESS_RE = re.compile(r"[^\s<>@,;:]+@[^\s<>@,;:]+\.[A-Za-z]{2,}")
# Anchored on a LEADING slash and requiring at least one interior one, so a
# relative payload path inside a finding (`['scripts/run.py']` — the whole
# point of a `missing-payload` finding) survives untouched while
# `/home/…/.claude/skills/synced/x` does not.
ABSOLUTE_PATH_RE = re.compile(r"""(?:[A-Za-z]:)?/(?:[^\s/'"]+/)+[^\s/'",;\])]*""")


def load_fixture(eval_dir: Path) -> dict:
    with open(eval_dir / "fixture.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_summary(latest: Path | None) -> dict | None:
    """The published result, or None when it is absent or unusable.

    Unreadable collapses to None on purpose. `freshness_verdict` already
    distinguishes "never published" from "published and gone" via the marker,
    and a JSON error here is the same class of event as the file having
    vanished: the audit is not reaching us. Both land on a liveness status,
    which this script deliberately does nothing about — see `decide`.
    """
    if not (latest and latest.is_file()):
        return None
    try:
        summary = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return summary if isinstance(summary, dict) else None


def decide(status: str, *, existing_issue: int | None) -> str:
    """freshness status -> what to do with the ONE tracking issue.

    `update` rather than `create` whenever an issue is already open, and the
    workflow EDITS THAT BODY IN PLACE rather than commenting on it. A drift
    episode lasted four days the last time one happened (ROUTINE.md), and a
    daily job that files a fresh issue — or even a fresh comment — for a
    steady-state red produces a pile nobody reads. The failure mode is not
    noise for its own sake: a notification stream that is 90% the same fact
    gets filtered, and a filtered channel is silence with extra steps.

    The four liveness statuses do NOTHING here, which is the least obvious
    line in this file and the one most likely to be "fixed" later:

    * `stale`, `missing`, `unreadable`, `not-yet-bootstrapped` all say the
      audit is not reaching us. They say nothing whatever about the account
      store, so CLOSING a drift issue on them would retract a live finding on
      the strength of no measurement at all, and OPENING one would file an
      account-drift report for what is really a transport fault — sending the
      reader to claude.ai Settings when the thing to fix is a Routine binding.
    * They are not unwatched. `propagation.yml`'s freshness gate fails on
      exactly those statuses, on every pull request and on its own schedule,
      and that is the surface built to answer them. Two mechanisms reporting
      one fault in two vocabularies is how they end up contradicting each
      other; one owner each is why this returns "none".
    """
    if status == "reported-failure":
        return "update" if existing_issue else "create"
    if status == "fresh":
        # Nothing open means nothing to close. Reporting `close` here would
        # hand the workflow a write it cannot perform and make every green
        # day look, in the log, like a day something was cleaned up.
        return "close" if existing_issue else "none"
    return "none"


def scrub(text: str) -> str:
    return ABSOLUTE_PATH_RE.sub("<path>", ADDRESS_RE.sub("<address>", str(text)))


def cell(text) -> str:
    """One markdown table cell: scrubbed, single-line, pipes escaped.

    A finding detail is a free-text string written by `account_store`, and a
    raw `|` in one would silently split a row into extra columns — the finding
    would still be "present" and would read as garbage, which is the worst of
    both. Newlines do the same thing one row up.
    """
    return scrub(" ".join(str(text).split())).replace("|", r"\|")


def drifted_skills(summary: dict | None) -> list:
    findings = (summary or {}).get("findings") or []
    return sorted({str(f.get("skill")) for f in findings if f.get("skill")})


def render_body(status: str, message: str, summary: dict | None,
                *, action: str) -> str:
    """The issue body. ALWAYS starts with the marker — see MARKER.

    Everything rendered here is already inside the published artifact on the
    `eval-results` branch, which is public. Naming the drifted skills and their
    findings therefore discloses nothing new, and it is what makes the issue
    actionable without a second lookup: the reader gets the skill list in the
    notification instead of a link to a JSON file they then have to diff.
    Descriptions and file contents are NOT in the artifact and are not rendered
    — `account_store` deliberately reports description drift as a pair of
    lengths for that reason.
    """
    checked = (summary or {}).get("checked") or []
    skipped = (summary or {}).get("skipped") or []
    findings = (summary or {}).get("findings") or []
    drifted = drifted_skills(summary)

    lines = [MARKER, ""]
    if action == "close":
        lines += [
            "The Tier-3 account-store audit reads **pass** again: the account "
            "copies claude.ai serves match the registry, so this tracking "
            "issue is closed automatically.",
            "",
        ]
    elif action == "none":
        # Never posted by the workflow — `none` means it writes nothing at all.
        # Rendered anyway so a dry run prints a body for every verdict and the
        # renderer has no branch that only production ever reaches.
        lines += [
            f"No issue action is called for: the freshness verdict is "
            f"`{status}`, which says the audit is not reaching us rather than "
            "anything about the account store. `propagation.yml`'s freshness "
            "gate owns that failure.",
            "",
        ]
    else:
        lines += [
            "The daily Tier-3 audit reports that the **claude.ai account "
            "skill store has drifted from the registry**. Only a signed-in "
            "surface can see that store, so no run in this repository can "
            "reproduce or repair it — the route below is the repair.",
            "",
            "This issue is opened, edited in place and closed by "
            "`.github/workflows/account-store-drift.yml`. It is one issue for "
            "the whole episode, not one per day.",
            "",
        ]

    lines += [
        "| | |",
        "| --- | --- |",
        f"| verdict | `{status}` |",
        f"| generated_at | `{cell((summary or {}).get('generated_at', 'n/a'))}` |",
        f"| registry_ref | `{cell((summary or {}).get('registry_ref', 'n/a'))}` |",
        f"| checked | {len(checked)} |",
        f"| skipped | {len(skipped)} |",
        f"| drifted | {len(drifted)} |",
        "",
        f"<sub>{cell(message)}</sub>",
        "",
    ]

    if findings:
        lines += ["### What drifted", "",
                  "| skill | kind | detail |", "| --- | --- | --- |"]
        lines += [f"| `{cell(f.get('skill'))}` | `{cell(f.get('kind'))}` | "
                  f"{cell(f.get('detail'))} |" for f in findings]
        lines.append("")

    if action in ("create", "update"):
        lines += [
            "### How to repair it",
            "",
            "1. **Get the ZIP.** agentskills' [Account skill ZIPs]"
            f"({ZIPS_WORKFLOW}) workflow builds one downloadable artifact per "
            "drifted skill from this same published result — on its own daily "
            "schedule, or on demand from that page.",
            "2. **Upload it as-is.** Download the artifact on the phone and "
            "hand the file straight to claude.ai -> Settings -> Capabilities. "
            "Do not unzip it: GitHub serves an artifact *as* a zip with "
            "`SKILL.md` at its root, which is exactly the shape the upload "
            "expects.",
            "3. **Record it.** Dispatch agentskills' **Record an account "
            "upload** with the skill name and the run ID of the ZIP build, so "
            "the next build stops offering the same skill.",
            "4. **Leave this issue alone.** The next audit that reads `pass` "
            "closes it.",
            "",
        ]
    return "\n".join(lines) + "\n"


def write_outputs(values: dict) -> None:
    """Append `name=value` lines to $GITHUB_OUTPUT, when there is one.

    Every value here is single-line by construction (a word from a fixed
    vocabulary, a constant title, a path this process chose), and the assert
    keeps it that way: a newline inside a step output is how a value smuggles
    a second `name=value` line into the next step's environment, which is a
    step output setting a variable nobody wrote in the workflow.
    """
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    for name, value in values.items():
        if "\n" in str(value) or "\r" in str(value):
            raise ValueError(f"step output {name} is not single-line")
    with open(path, "a", encoding="utf-8") as handle:
        for name, value in values.items():
            handle.write(f"{name}={value}\n")


def parse_issue_number(raw: str, parser: argparse.ArgumentParser) -> int | None:
    """"" means no issue is open. Anything else must be a number.

    The empty string is the workflow's normal case, not an error: the lookup
    runs in the `gh` step because that is the only step holding a credential.
    A non-numeric value is a broken caller — silently reading it as "none"
    would file a duplicate issue every morning while looking healthy.
    """
    text = (raw or "").strip().lstrip("#")
    if not text:
        return None
    if not text.isdigit():
        parser.error(f"--existing-issue-number must be a number or empty, got {raw!r}")
    return int(text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eval_dir", type=Path,
                        help="the propagation eval dir holding fixture.yaml")
    parser.add_argument("--account-latest", type=Path, default=None,
                        help="the audit's published latest.json")
    parser.add_argument("--account-marker", type=Path, default=None,
                        help="propagation/.bootstrapped — absent means the "
                             "audit has never published, which is not a fault")
    parser.add_argument("--existing-issue-number", default="",
                        help="number of the open tracking issue, or empty")
    parser.add_argument("--body-out", type=Path, default=None,
                        help="where to render the issue body (default: "
                             "$RUNNER_TEMP, else the system temp dir)")
    parser.add_argument("--now", default=None,
                        help="ISO-8601 instant treated as now; tests pass it "
                             "so the freshness arithmetic is deterministic")
    args = parser.parse_args(argv)

    existing = parse_issue_number(args.existing_issue_number, parser)
    try:
        fixture = load_fixture(args.eval_dir)
    except (OSError, yaml.YAMLError) as exc:
        # A caller that cannot find the fixture is broken, not undecided:
        # returning "none" here would look exactly like a healthy green day.
        print(f"INCONCLUSIVE account-drift-issue: {exc}")
        return EXIT_USAGE

    now = (account_store.parse_iso8601(args.now) if args.now
           else datetime.now(timezone.utc))
    summary = read_summary(args.account_latest)
    _, status, message = account_store.freshness_verdict(
        summary, now=now,
        max_age_days=int(fixture["account_audit_max_age_days"]),
        bootstrapped=bool(args.account_marker and args.account_marker.exists()))

    action = decide(status, existing_issue=existing)
    body = render_body(status, message, summary, action=action)
    body_out = args.body_out or (
        Path(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir())
        / "account-drift-issue.md")
    body_out.parent.mkdir(parents=True, exist_ok=True)
    body_out.write_text(body, encoding="utf-8")

    write_outputs({"action": action, "title": TITLE, "marker": MARKER,
                   "body_file": str(body_out)})

    # Counts and a verdict word only. No skill names, no detail strings, no
    # paths under $HOME: the workflow's log is public, and this line exists to
    # say whether the reactor did anything, not to restate the artifact.
    print(f"account-drift-issue [{status}]: action={action} "
          f"checked={len((summary or {}).get('checked') or [])} "
          f"skipped={len((summary or {}).get('skipped') or [])} "
          f"drifted={len(drifted_skills(summary))} "
          f"open-issue={existing if existing else 'none'}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
