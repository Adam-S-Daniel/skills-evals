"""Send mail through the account's own SMTP relay."""

import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.example.net"
ACCOUNT = "triage@example.net"


def send_email(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = ACCOUNT
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP_SSL(SMTP_HOST) as smtp:
        smtp.login(ACCOUNT, os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
