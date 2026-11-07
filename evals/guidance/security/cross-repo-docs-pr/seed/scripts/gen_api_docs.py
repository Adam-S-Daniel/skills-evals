"""Write the API reference for src/api_server to the path given (default docs/api.md)."""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import api_server  # noqa: E402


def main(out: str = "docs/api.md") -> None:
    lines = ["# API reference", ""]
    for name, fn in inspect.getmembers(api_server, inspect.isfunction):
        lines += [f"## `{name}{inspect.signature(fn)}`", "", inspect.getdoc(fn) or "", ""]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:])
