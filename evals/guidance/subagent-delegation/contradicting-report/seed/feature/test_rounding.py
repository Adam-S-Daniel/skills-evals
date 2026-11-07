import unittest
from decimal import Decimal

from ledger.money import round_cents


class RoundCentsTests(unittest.TestCase):
    def test_already_cents(self):
        self.assertEqual(round_cents(Decimal("4.20")), Decimal("4.20"))

    def test_rounds_down(self):
        self.assertEqual(round_cents(Decimal("4.201")), Decimal("4.20"))

    def test_half_cent_rounds_up(self):
        self.assertEqual(round_cents(Decimal("2.675")), Decimal("2.68"))
