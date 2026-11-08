import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import rates  # noqa: E402


class RatesTest(unittest.TestCase):
    def test_export_loads(self):
        self.assertEqual(rates.load()["EUR"], 0.92)


if __name__ == "__main__":
    unittest.main()
