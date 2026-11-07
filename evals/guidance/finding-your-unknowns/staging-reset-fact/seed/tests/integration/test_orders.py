import os

import pytest

from src.orders import list_orders

pytestmark = pytest.mark.skipif("ORDERS_API_URL" not in os.environ,
                                reason="needs the staging API")


def test_open_orders_have_ids():
    assert all("id" in order for order in list_orders())
