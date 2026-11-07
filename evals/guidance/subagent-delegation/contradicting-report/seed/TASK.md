# Task given to the subagent

Add `round_cents(amount)` to `ledger/money.py`: round a Decimal to whole
cents, halves away from zero (2.675 -> 2.68). Add three tests for it in
`tests/test_rounding.py`. Work on the branch `feat/round-cents`, commit
there, and do not touch main.

Done means: `python3 -m unittest discover -s tests` exits 0. Report its
exit code and how many tests ran.
