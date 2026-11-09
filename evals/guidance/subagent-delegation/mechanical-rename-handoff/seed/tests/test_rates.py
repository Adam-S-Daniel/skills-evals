import unittest

from shipping.quote import quote
from shipping.rates import calc_fee


class RateTests(unittest.TestCase):
    def test_local(self):
        self.assertEqual(calc_fee(2, 1), 4.0)

    def test_international(self):
        self.assertEqual(calc_fee(1.5, 3), 16.5)

    def test_quote(self):
        self.assertEqual(quote(1, 2), {"fee": 4.5, "currency": "USD"})
