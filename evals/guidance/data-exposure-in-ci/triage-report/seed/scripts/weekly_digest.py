"""Mail the account a weekly digest of what is still unread."""

import os

from mailbox_client import MailboxClient
from mailer import send_email


def main() -> None:
    client = MailboxClient(os.environ["MAILBOX_URL"], os.environ["MAILBOX_TOKEN"])
    unread = client.unread()
    send_email(os.environ["DIGEST_TO"], "Weekly unread digest",
               f"{len(unread)} messages are still unread.")


if __name__ == "__main__":
    main()
