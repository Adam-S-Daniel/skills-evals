"""python -m usage_weights estimate|tables"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys

from .estimate import estimate
from .table import list_tables, load_table


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"usage_weights: {message}", file=sys.stderr)
        sys.exit(2)


def _read_records(path: str) -> list:
    records = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError as e:
                raise ValueError(f"{path} line {n}: not JSON ({e})") from None
    return records


def main(argv=None) -> int:
    ap = _Parser(prog="usage_weights")
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    est = sub.add_parser("estimate", help="estimate points for records in a JSONL file")
    est.add_argument("--table", required=True, help="table id or path")
    est.add_argument("--meter", default="all_models")
    est.add_argument("--on-unknown", choices=("error", "skip"), default="error")
    est.add_argument("file")
    sub.add_parser("tables", help="list packaged table ids")
    args = ap.parse_args(argv)
    if args.cmd == "tables":
        print("\n".join(list_tables()))
        return 0
    try:
        table = load_table(args.table)
        result = estimate(_read_records(args.file), table, args.meter, args.on_unknown)
    except (ValueError, OSError) as e:
        print(f"usage_weights: {e}", file=sys.stderr)
        return 2
    print(json.dumps(dataclasses.asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
