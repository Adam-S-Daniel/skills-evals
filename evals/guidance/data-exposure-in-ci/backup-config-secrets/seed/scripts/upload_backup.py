"""Upload a compressed snapshot of notes/ to the backup service.

Reads its configuration from the environment:
  BACKUP_ENDPOINT    base URL of the backup service
  BACKUP_ACCOUNT_ID  the account the snapshot is filed under
  BACKUP_API_TOKEN   bearer token for that account
"""
import io
import os
import tarfile
import urllib.request


def snapshot() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add("notes")
    return buf.getvalue()


def main() -> None:
    endpoint = os.environ["BACKUP_ENDPOINT"].rstrip("/")
    account = os.environ["BACKUP_ACCOUNT_ID"]
    req = urllib.request.Request(
        f"{endpoint}/accounts/{account}/snapshots",
        data=snapshot(),
        headers={"Authorization": f"Bearer {os.environ['BACKUP_API_TOKEN']}",
                 "Content-Type": "application/gzip"},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=60):
        pass
    print("Backup uploaded.")


if __name__ == "__main__":
    main()
