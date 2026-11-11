import datetime

from billing import build_invoices, format_cents, parse_orders


def test_parse_simple():
    orders = parse_orders("customer,item,unit_cents,qty,date\nCobalt,Nut,250,40,2026-03-01\n")
    assert orders[0]["qty"] == 40


def test_tax_two_lines():
    orders = parse_orders(
        "customer,item,unit_cents,qty,date\n"
        "Dune,A,106,1,2026-01-05\n"
        "Dune,B,106,1,2026-01-10\n"
    )
    inv = build_invoices(orders, datetime.date(2026, 1, 15))[0]
    assert inv["tax_cents"] == 18


def test_format():
    assert format_cents(250) == "$2.50"
