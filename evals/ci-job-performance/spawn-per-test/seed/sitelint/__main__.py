"""Command line: python3 -m sitelint [--json] PAGE...

Exit status is 0 when no page has a finding, 1 when any page has one, and 2
on a usage error or an unreadable page.
"""

import argparse
import json
import sys

from sitelint.rules import lint_file


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sitelint", description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print findings as a JSON list")
    parser.add_argument("pages", nargs="+", help="HTML files to check")
    args = parser.parse_args(argv)

    findings = []
    for page in args.pages:
        try:
            findings.extend(lint_file(page))
        except OSError as exc:
            print(f"sitelint: cannot read {page}: {exc.strerror}", file=sys.stderr)
            return 2

    if args.json:
        json.dump([f._asdict() for f in findings], sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for f in findings:
            print(f"{f.path}:{f.line}: {f.rule}: {f.message}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
