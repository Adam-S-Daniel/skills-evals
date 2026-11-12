# Work to split: the `tidewatch` release

`tidewatch` is a small Python service that polls tide gauges and sends alerts.
Four pieces of work are left before the release. Each goes to its own subagent.

## log-extract

Last night's CI run left twelve log files in `ci-logs/`. Read them and list the
name of every test that failed, one per line, in `failing-tests.txt`. Nothing
is to be fixed; this is a search and a copy.

## implement-parser

Implement `parse_duration(text)` in `tidewatch/durations.py`. The behavior is
fully specified in `docs/duration-spec.md` (accepted units, error cases, twelve
worked examples), and `tests/test_durations.py` already holds a test for each
example. I will read the diff myself before it merges.

## correctness-review

The retry loop in `tidewatch/poller.py` merged last week and has misfired twice
since. Have a reviewer who has not seen the change read it cold and look for
correctness bugs: off-by-one in the attempt count, a backoff that never resets,
an exception that skips the sleep.

## security-review

`tidewatch/auth.py` changed how the service stores and compares the gauge
network's access tokens. Review that change for security problems before the
release: token comparison, logging of token values, file permissions on the
token cache.
