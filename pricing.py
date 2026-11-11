"""Order pricing. See README.md for the rules."""


def discount_percent(qty):
    if qty > 100:
        return 20
    if qty > 10:
        return 10
    return 0


def total_cents(unit_cents, qty):
    discount = discount_percent(qty)
    return int(unit_cents * qty * (1 - discount / 100))
