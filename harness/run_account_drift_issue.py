#!/usr/bin/env python3
"""Turn the Tier-3 account audit's published verdict into ONE tracking issue.

`evals/propagation/ROUTINE.md` step 5 asks the Routine-fired session to open,
edit and close this issue. It never has, and CI owns the lifecycle instead —
but NOT because the fired session cannot reach GitHub. That reason was written
here first and it does not survive measurement; the workflow's header carries
the measurement and the reasons that do hold, which are about keeping the thing
that measures separate from the thing that reports, and about a decision being
diffable and testable rather than living in a prompt. Read it there rather than
restating it here, and do not restore the old sentence.

This is the part of `.github/workflows/account-store-drift.yml` that decides
anything.

The whole file is a PURE function of three published inputs plus a clock:
`latest.json`, the `.bootstrapped` marker, and `evals/propagation/fixture.yaml`.
It reaches no network, spawns nothing, and holds no credential — the `gh`
lookup and the writes live in the workflow, one step further out, where the
only thing that can reach the issue is a single scripted step below a dry-run
bail-out. That split is deliberate: the interesting logic is the one that has
to be testable, and a decision that needs a token to exercise is a decision
nobody exercises.

Which is also why what this file returns is a POLICY (`open` / `close` /
`none`) and not a `gh` subcommand. Whether an issue is already open is not
knowable without a credential, so `create`-vs-`edit` was never a decision this
side of the split could make; an earlier cut that tried anyway is what left the
close path unreachable — see `decide`.

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
        --body-out "$RUNNER_TEMP/drift.md"

Exit codes: 0 always for a decision — "no issue is called for" is a finding,
not an error, and a runner that reds on it teaches people to ignore the run.
2 only for an invocation that could not be understood at all (no fixture),
because that is a broken caller rather than a verdict.
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


def decide(status: str) -> str:
    """freshness status -> the POLICY for the ONE tracking issue.

    Three words and deliberately not five: `open` (the store has drifted, so
    an issue should exist and say so), `close` (it is repaired, so no issue
    should be open), `none` (say nothing at all). Which `gh` call satisfies
    `open` — create a new issue, or edit the one already open — depends on a
    number that only a credentialed caller can look up, so the workflow's
    single privileged step maps policy x number onto the call.

    THAT SPLIT IS THE FIX FOR A REAL DEFECT, and the shape it replaced looks
    more helpful, so here is why it is not. This function used to take the
    open issue's number and return `create` / `update` / `close` / `none`.
    Nothing upstream of the credentialed step can know that number, so the
    workflow passed the empty string on every run — and `fresh` with no number
    returned `none`, which the write step reads as "nothing to do" and exits
    on before it ever looks the issue up. The close half of the lifecycle was
    therefore unreachable in every run that would ever happen: the issue
    opened on the first red, was edited daily while the drift lasted, and then
    stayed open forever, under a body promising "the next audit that reads
    `pass` closes it". Returning a policy is what makes that sentence true —
    the part that can be decided without a credential is decided here, where
    it is tested, and the part that cannot is not pretended about.

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
        return "open"
    if status == "fresh":
        # `close` on every green day, including the ones where nothing is
        # open. That is not a write on a quiet day: the write step's `close`
        # arm finds no open issue and prints that it found none. Suppressing
        # the policy here instead is what made this branch unreachable before
        # — the suppression needs a fact this side of the split cannot have.
        return "close"
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
                *, policy: str) -> str:
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
    if policy == "close":
        # Posted as the closing comment, and only when an issue was actually
        # open — on a green day with nothing open the workflow prints that it
        # found none and this body goes nowhere. Rendering it either way keeps
        # the renderer free of a branch that only one of the two ever reaches.
        lines += [
            "The Tier-3 account-store audit reads **pass** again: the account "
            "copies claude.ai serves match the registry, so this tracking "
            "issue is closed automatically.",
            "",
        ]
    elif policy == "none":
        # Never posted by the workflow — `none` means it writes nothing at all.
        # Rendered anyway so a dry run prints a body for every verdict and the
        # renderer has no branch that only production ever reaches.
        lines += [
            f"No issue write is called for: the freshness verdict is "
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

    if policy == "open":
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eval_dir", type=Path,
                        help="the propagation eval dir holding fixture.yaml")
    parser.add_argument("--account-latest", type=Path, default=None,
                        help="the audit's published latest.json")
    parser.add_argument("--account-marker", type=Path, default=None,
                        help="propagation/.bootstrapped — absent means the "
                             "audit has never published, which is not a fault")
    # No `--existing-issue-number` flag, deliberately, and it is not an
    # oversight to be restored: an earlier version took one, no caller could
    # supply it, and the decision it fed silently lost its `close` branch. The
    # issue number belongs to the one step that can look it up.
    parser.add_argument("--body-out", type=Path, default=None,
                        help="where to render the issue body (default: "
                             "$RUNNER_TEMP, else the system temp dir)")
    parser.add_argument("--now", default=None,
                        help="ISO-8601 instant treated as now; tests pass it "
                             "so the freshness arithmetic is deterministic")
    args = parser.parse_args(argv)

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

    policy = decide(status)
    body = render_body(status, message, summary, policy=policy)
    body_out = args.body_out or (
        Path(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir())
        / "account-drift-issue.md")
    body_out.parent.mkdir(parents=True, exist_ok=True)
    body_out.write_text(body, encoding="utf-8")

    write_outputs({"policy": policy, "title": TITLE, "marker": MARKER,
                   "body_file": str(body_out)})

    # Counts and a verdict word only. No skill names, no detail strings, no
    # paths under $HOME: the workflow's log is public, and this line exists to
    # say whether the reactor did anything, not to restate the artifact.
    print(f"account-drift-issue [{status}]: policy={policy} "
          f"checked={len((summary or {}).get('checked') or [])} "
          f"skipped={len((summary or {}).get('skipped') or [])} "
          f"drifted={len(drifted_skills(summary))}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
