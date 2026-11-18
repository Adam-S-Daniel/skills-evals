import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import reaper  # noqa: E402


def test_a_missing_pid_file_signals_nothing(tmp_path):
    assert reaper.reap(tmp_path / "worker.pid") is False
