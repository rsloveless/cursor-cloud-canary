"""Order pricing. See README.md for the rules."""
import math


def discount_percent(qty):
    if qty >= 100:
        return 20
    if qty >= 10:
        return 10
    return 0


def total_cents(unit_cents, qty):
    if qty < 1:
        raise ValueError("quantity must be at least 1")
    if unit_cents < 0:
        raise ValueError("unit price cannot be negative")
    discount = discount_percent(qty)
    raw = unit_cents * qty * (1 - discount / 100)
    # Nearest cent; exact half rounds up.
    return math.floor(raw + 0.5)
