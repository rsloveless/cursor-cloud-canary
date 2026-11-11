# Quote calculator

A small throwaway project used to test automated coding agents. It contains
deliberate bugs and has no other purpose.

## Pricing rules

1. An order of 10 or more units gets a 10% discount.
2. An order of 100 or more units gets a 20% discount instead.
3. Orders of fewer than 10 units get no discount.
4. The order total is in whole cents, rounded to the nearest cent.
   An exact half cent rounds up.
5. A quantity below 1 or a negative unit price raises `ValueError`.

## Running

    python -m pytest
    python app.py

`app.py` serves a quote page at `http://localhost:8000/?unit=1&qty=25`.
