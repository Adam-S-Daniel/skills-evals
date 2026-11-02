"""Parse address-book entries and group them by email domain.

An entry is either a bare address or a display name with the address in
angle brackets, as an address-book export writes it.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass

_ADDRESS = re.compile(r"^[^@\s<>]+@([^@\s<>]+\.[^@\s<>]+)$")


@dataclass(frozen=True)
class Contact:
    name: str
    email: str

    @property
    def domain(self) -> str:
        return self.email.rsplit("@", 1)[1]


def parse_entry(entry: str) -> Contact:
    """Parse one entry; raise ValueError if it holds no valid address."""
    entry = entry.strip()
    name, address = "", entry
    if entry.endswith(">") and "<" in entry:
        name, _, address = entry[:-1].rpartition("<")
        name = name.strip().strip('"').strip()
    address = address.strip()
    if not _ADDRESS.match(address):
        raise ValueError(f"not an email address: {entry!r}")
    local, domain = address.rsplit("@", 1)
    return Contact(name=name, email=f"{local}@{domain.lower()}")


def load_csv(path: str) -> list[Contact]:
    """Read a CSV export with `name` and `email` columns, skipping bad rows."""
    contacts = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row["email"] if not row.get("name") else f'{row["name"]} <{row["email"]}>'
            try:
                contacts.append(parse_entry(raw))
            except ValueError:
                continue
    return contacts


def group_by_domain(contacts: list[Contact]) -> dict[str, list[Contact]]:
    """Contacts keyed by lowercased domain, each list in input order."""
    groups: dict[str, list[Contact]] = {}
    for contact in contacts:
        groups.setdefault(contact.domain, []).append(contact)
    return groups
