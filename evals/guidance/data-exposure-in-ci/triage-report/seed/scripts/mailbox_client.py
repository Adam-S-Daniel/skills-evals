"""A small client for the mailbox service's JSON API."""

import json
import urllib.request


class MailboxClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _call(self, method: str, path: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, method=method,
                                     headers={"Authorization": f"Bearer {self.token}",
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def unread(self) -> list[dict]:
        """Unread messages: dicts with id, sender, subject and list_id."""
        return self._call("GET", "/messages?unread=1")["messages"]

    def archive(self, message_id: str) -> None:
        self._call("POST", f"/messages/{message_id}/archive", {})
