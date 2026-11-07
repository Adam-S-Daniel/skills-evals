def get_order(order_id: int) -> dict:
    """Return one order by id."""
    return {"id": order_id}


def list_orders(status: str = "open") -> list:
    """Return the orders in a status."""
    return []
