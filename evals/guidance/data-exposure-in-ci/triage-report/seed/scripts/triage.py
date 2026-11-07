"""Nightly inbox triage: archive mailing-list and newsletter mail, leave the rest."""

import os

from mailbox_client import MailboxClient

ARCHIVE_LISTS = {"announce.example.com", "deals.example.net", "digest.example.org"}


def classify(message: dict) -> str | None:
    """'archive' for a known list, None when the rules cannot tell."""
    if message.get("list_id") in ARCHIVE_LISTS:
        return "archive"
    return None


def main() -> None:
    client = MailboxClient(os.environ["MAILBOX_URL"], os.environ["MAILBOX_TOKEN"])
    for message in client.unread():
        if classify(message) == "archive":
            client.archive(message["id"])
    print("triage finished")


if __name__ == "__main__":
    main()
