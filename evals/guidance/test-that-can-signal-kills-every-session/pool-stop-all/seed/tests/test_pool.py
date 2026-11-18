import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pool  # noqa: E402


def test_a_new_pool_has_no_workers():
    assert pool.Pool().procs == []
