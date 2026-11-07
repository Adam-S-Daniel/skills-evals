"""Pull the inventory export from the inventory service into a JSON file."""

import argparse
import json
import os

import requests

DEFAULT_URL = "https://inventory.example.com"


def fetch_inventory(base_url: str, token: str) -> dict:
    resp = requests.get(f"{base_url}/v1/export",
                        headers={"Authorization": f"Bearer {token}"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("INVENTORY_URL", DEFAULT_URL))
    parser.add_argument("--out", default="inventory.json")
    args = parser.parse_args(argv)
    data = fetch_inventory(args.base_url, os.environ["INVENTORY_TOKEN"])
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {len(data.get('items', []))} items to {args.out}")


if __name__ == "__main__":
    main()
