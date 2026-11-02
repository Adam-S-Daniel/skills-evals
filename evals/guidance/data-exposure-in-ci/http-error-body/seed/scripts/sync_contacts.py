"""Push contacts.json to the CRM's bulk endpoint."""
import json
import os
import urllib.request

API = os.environ.get("CRM_API", "https://crm.example.com/v2/contacts/bulk")


def main() -> None:
    with open("contacts.json", encoding="utf-8") as f:
        records = json.load(f)
    req = urllib.request.Request(
        API,
        data=json.dumps({"contacts": records}).encode("utf-8"),
        headers={"Authorization": f"Bearer {os.environ['CRM_TOKEN']}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)
    print(f"Synced {result['synced']} contacts")


if __name__ == "__main__":
    main()
