import unittest
from decimal import Decimal

from ledger.money import format_amount, parse_amount


class ParseTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(parse_amount("12.50"), Decimal("12.50"))

    def test_dollar_and_commas(self):
        self.assertEqual(parse_amount("$1,234.50"), Decimal("1234.50"))


class FormatTests(unittest.TestCase):
    def test_two_places(self):
        self.assertEqual(format_amount(Decimal("3")), "$3.00")

    def test_thousands(self):
        self.assertEqual(format_amount(Decimal("1234.5")), "$1,234.50")
