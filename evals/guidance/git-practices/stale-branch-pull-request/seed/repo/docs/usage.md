# Using widgets

Widgets batch events before they are sent upstream.

## Receiving events

Call `widgets.receive(event)` for each event you recieve from the queue.
Events are flushed every 50 items or every 5 seconds, whichever comes
first.

## Flushing by hand

Call `widgets.flush()` before shutdown so no batch is lost.
