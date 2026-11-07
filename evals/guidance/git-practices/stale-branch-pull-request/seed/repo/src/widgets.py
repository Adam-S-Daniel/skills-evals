"""Batch widget events before sending them upstream."""

BATCH_SIZE = 50
_batch = []


def receive(event):
    _batch.append(event)
    if len(_batch) >= BATCH_SIZE:
        flush()


def flush():
    sent = list(_batch)
    _batch.clear()
    return sent
