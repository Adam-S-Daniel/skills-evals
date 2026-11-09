# Task: rename `calc_fee` to `shipping_fee`

`calc_fee(weight_kg, zone)` in `shipping/rates.py` is called from
`shipping/quote.py`, `shipping/invoice.py` and `tests/test_rates.py`. Rename it
to `shipping_fee` everywhere, keep the behavior identical, and leave no
reference to the old name.

This is a mechanical edit across three files; the existing tests cover it.
