"""Strict reader for data/rates.csv: plain UTF-8 `code,rate` rows."""
from pathlib import Path


def load(path="data/rates.csv"):
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{path}: byte order mark found; exports must be plain UTF-8")
    rows = raw.decode("utf-8").strip().split("\n")
    header, *body = rows
    if header != "code,rate":
        raise ValueError(f"{path}: bad header {header!r}")
    return {code: float(rate) for code, rate in (line.split(",") for line in body)}
