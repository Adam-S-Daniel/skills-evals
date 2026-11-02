#!/usr/bin/env python3
"""Plan only reviewed scheduled fixtures, or the dispatch fixture list (1 to 20).

The routine sweep's banded, allowance-cut plan is scripts/plan_week.py,
which reads the reviewed list through `scheduled_fixtures` here.

`--in-place FIXTURE` exits 0 only for a committed fixture whose fixture.yaml
declares a top-level `context` mapping, the fixtures that run in place (ADR
0012); routine-eval-fire.yml runs it before it accepts `arms: bare`.

With no flag (eval.yml's plan job) it plans the matrix and REFUSES every
in-place fixture in it before any credential is minted (skills-evals#587):
eval.yml's runner is not the hosted container `delivery.require_hosted`
asks for, so an in-place pair could only fail there after the mint, and
running it as an isolation pair instead would mix isolation and in-place
results in one subject's verdict data. Refused fixtures leave the matrix
and are listed, with the reason, in the step summary; `count` (the
fixtures left) is what eval.yml's jobs gate on, `0` meaning none run.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

DEFAULT_FIXTURE = "evals/workflow-path-audit/required-check-routing"
MAX_DISPATCH_FIXTURES = 20
IN_PLACE_REFUSAL = ("in-place pair: runs only in the cloud routine, which hosts in-place "
                    "delivery; eval.yml cannot (skills-evals#587)")


def committed_fixtures(root):
    """Use Git's index rather than accepting untracked fixture directories."""
    # Raw git is fine here (#343): this repository's own checkout, never an agent-touched
    # workspace, so harness/workspace_git.py does not apply.
    files = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "evals"], cwd=root
    ).decode("utf-8").split("\0")
    return sorted(str(Path(name).parent) for name in files
                  if name.endswith("/fixture.yaml") and (root / name).is_file())


def validate_fixture(path, committed):
    if not isinstance(path, str) or not re.fullmatch(r"[A-Za-z0-9/_.-]+", path):
        raise ValueError("fixture has characters outside [A-Za-z0-9/_.-]")
    if not path.startswith("evals/") or path not in committed:
        raise ValueError("fixture names no committed fixture")
    return path[len("evals/"):]


def declares_context(directory):
    """Whether the fixture in `directory` runs in place (ADR 0012): its
    fixture.yaml parses to a mapping with a top-level `context` mapping, the
    test harness/run_eval.py applies. An unreadable file is not in place."""
    import yaml

    try:
        document = yaml.safe_load((Path(directory) / "fixture.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return False
    return isinstance(document, dict) and isinstance(document.get("context"), dict)


def scheduled_fixtures(path, committed):
    import yaml

    class UniqueLoader(yaml.SafeLoader):
        pass

    def mapping(loader, node):
        pairs = loader.construct_pairs(node, deep=True)
        result = {}
        for key, value in pairs:
            if not isinstance(key, str) or key in result:
                raise ValueError("schedule has an invalid or duplicate key")
            result[key] = value
        return result

    UniqueLoader.add_constructor("tag:yaml.org,2002:map", mapping)
    try:
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)
    except yaml.YAMLError:
        raise ValueError("invalid schedule YAML") from None
    if not isinstance(document, dict) or set(document) != {"fixtures"}:
        raise ValueError("schedule must contain only fixtures")
    entries = document["fixtures"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 256:
        raise ValueError("schedule must contain 1 to 256 fixtures")
    fixtures = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "readiness"}:
            raise ValueError("schedule entries need exactly path and readiness")
        note = entry["readiness"]
        if not isinstance(note, str) or not note.strip() or any(
                ord(char) < 32 or char in "\x7f\u0085\u2028\u2029" for char in note):
            raise ValueError("readiness must be a nonempty one-line note")
        fixture = entry["path"]
        validate_fixture(fixture, committed)
        if fixture in fixtures:
            raise ValueError("schedule repeats a fixture")
        fixtures.append(fixture)
    return fixtures


def plan(root, event_name, event):
    committed = committed_fixtures(root)
    if event_name == "schedule":
        fixtures = scheduled_fixtures(root / "evals/scheduled.yml", committed)
    elif event_name == "workflow_dispatch":
        inputs = event.get("inputs")
        if inputs is None:
            inputs = {}
        if not isinstance(inputs, dict):
            raise ValueError("dispatch inputs must be an object")
        raw = inputs.get("fixture")
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            raise ValueError("dispatch fixture must be a string")
        fixtures = raw.split()
        if not fixtures:
            fixtures = [DEFAULT_FIXTURE]
        if len(fixtures) > MAX_DISPATCH_FIXTURES:
            raise ValueError("dispatch names too many fixtures")
        if len(set(fixtures)) != len(fixtures):
            raise ValueError("dispatch repeats a fixture")
    else:
        raise ValueError("unsupported eval event")
    return {"include": [{"fixture": fixture,
                         "eval_key": validate_fixture(fixture, committed),
                         "slot": slot} for slot, fixture in enumerate(fixtures)]}


def refuse_in_place(root, matrix):
    """Split a planned matrix into the legs eval.yml can run and the in-place
    fixtures it refuses (`declares_context`, the routine's rule). Kept legs
    keep their planned slot; there is no fallback to isolation."""
    kept, refused = [], []
    for leg in matrix["include"]:
        if declares_context(Path(root) / leg["fixture"]):
            refused.append(leg["fixture"])
        else:
            kept.append(leg)
    return {"include": kept}, refused


def refusal_summary(refused, count):
    """The step-summary markdown for refused fixtures; empty when none was.
    Each path already passed validate_fixture, so it is [A-Za-z0-9/_.-]."""
    if not refused:
        return ""
    lines = ["### Fixtures refused before any credential", ""]
    lines += [f"- `{fixture}`: {IN_PLACE_REFUSAL}" for fixture in refused]
    lines.append("")
    if count:
        lines.append(f"{count} fixture(s) left to run.")
    else:
        lines.append("No fixture is left to run, so no eval leg runs and, unless this "
                     "is a `roster_only` dispatch, no job mints a credential. The run "
                     "ends here, successfully.")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--committed", action="store_true")
    parser.add_argument("--validate", nargs=3, metavar=("FIXTURE", "KEY", "SLOT"))
    parser.add_argument("--in-place", metavar="FIXTURE")
    args = parser.parse_args()
    root = Path.cwd()
    try:
        if args.committed:
            print("\n".join(committed_fixtures(root)))
        elif args.validate:
            fixture, key, slot = args.validate
            expected = validate_fixture(fixture, committed_fixtures(root))
            if key != expected or not re.fullmatch(r"(?:0|[1-9][0-9]{0,2})", slot) or int(slot) > 255:
                raise ValueError("matrix key or slot does not match a validated fixture")
            print(f"eval_key={expected}")
        elif args.in_place is not None:
            validate_fixture(args.in_place, committed_fixtures(root))
            if not declares_context(root / args.in_place):
                raise ValueError("fixture does not run in place")
        else:
            event_path = os.environ.get("GITHUB_EVENT_PATH")
            event = json.loads(Path(event_path).read_text()) if event_path else {}
            if not isinstance(event, dict):
                raise ValueError("event must be an object")
            matrix, refused = refuse_in_place(
                root, plan(root, os.environ["GITHUB_EVENT_NAME"], event))
            count = len(matrix["include"])
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write("matrix=" + json.dumps(matrix, separators=(",", ":")) + "\n")
                output.write(f"count={count}\n")
            if refused:
                print(f"::notice::{len(refused)} in-place fixture(s) refused, {count} left "
                      "to run; see the step summary (skills-evals#587)")
                summary = os.environ.get("GITHUB_STEP_SUMMARY")
                if summary:
                    with open(summary, "a", encoding="utf-8") as output:
                        output.write(refusal_summary(refused, count))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError):
        # Never echo event content or exception bodies into the public log.
        print("::error::Invalid eval plan or committed fixture selection")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
