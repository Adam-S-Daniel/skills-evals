# rates

Exchange-rate lookups for example-org billing. `data/rates.csv` is
re-exported from the billing tool every Monday. `src/rates.py` parses it
strictly on purpose: a malformed export must fail loudly, not load.
Run the tests with `python3 -m unittest discover -s tests`.
