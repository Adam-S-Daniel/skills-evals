"""Mail the weekly digest of merged pull requests to one recipient."""

import argparse
import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.example.net"


def build_digest() -> str:
    return "Merged this week:\n- (generated from the repository's history)\n"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--to", required=True)
    args = parser.parse_args(argv)
    msg = EmailMessage()
    msg["Subject"] = "Weekly digest"
    msg["From"] = "digest@example.net"
    msg["To"] = args.to
    msg.set_content(build_digest())
    with smtplib.SMTP_SSL(SMTP_HOST) as smtp:
        smtp.login("digest@example.net", os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
    print("digest sent")


if __name__ == "__main__":
    main()
