import json
import os
import urllib.request


def list_orders(status: str = "open") -> list[dict]:
    base = os.environ["ORDERS_API_URL"]
    with urllib.request.urlopen(f"{base}/orders?status={status}", timeout=30) as resp:
        return json.load(resp)["orders"]
