"""Tests for every billing README rule, including boundaries and invalid input."""
import datetime
import os
import threading
from http.server import HTTPServer
from urllib.request import urlopen

import pytest

from billing import build_invoices, format_cents, parse_orders
from app import Handler

HERE = os.path.dirname(os.path.abspath(__file__))


# --- Rule 1: CSV parsing ---

def test_rule1_simple_csv():
    orders = parse_orders("customer,item,unit_cents,qty,date\nCobalt,Nut,250,40,2026-03-01\n")
    assert orders == [{
        "customer": "Cobalt",
        "item": "Nut",
        "unit_cents": 250,
        "qty": 40,
        "date": datetime.date(2026, 3, 1),
    }]


def test_rule1_quoted_commas_and_doubled_quotes():
    text = (
        "customer,item,unit_cents,qty,date\n"
        '"Acme, Inc.","Bolt, 3""",106,1,2026-01-10\n'
    )
    orders = parse_orders(text)
    assert orders[0]["customer"] == "Acme, Inc."
    assert orders[0]["item"] == 'Bolt, 3"'


def test_rule1_blank_lines_ignored():
    text = (
        "customer,item,unit_cents,qty,date\n"
        "\n"
        "Cobalt,Nut,250,40,2026-03-01\n"
        "   \n"
        "Dune,A,100,1,2026-01-01\n"
    )
    assert len(parse_orders(text)) == 2


def test_rule1_columns_any_order():
    text = "date,qty,customer,unit_cents,item\n2026-03-01,40,Cobalt,250,Nut\n"
    orders = parse_orders(text)
    assert orders[0]["customer"] == "Cobalt"
    assert orders[0]["qty"] == 40
    assert orders[0]["unit_cents"] == 250
    assert orders[0]["item"] == "Nut"
    assert orders[0]["date"] == datetime.date(2026, 3, 1)


def test_rule1_missing_required_column_raises():
    with pytest.raises(ValueError, match="missing required column"):
        parse_orders("customer,item,qty,date\nCobalt,Nut,40,2026-03-01\n")


# --- Rule 2: validation and row numbers ---

def test_rule2_qty_must_be_at_least_1():
    text = "customer,item,unit_cents,qty,date\nCobalt,Nut,250,0,2026-03-01\n"
    with pytest.raises(ValueError, match=r"row 1"):
        parse_orders(text)


def test_rule2_qty_boundary_1_ok():
    text = "customer,item,unit_cents,qty,date\nCobalt,Nut,250,1,2026-03-01\n"
    assert parse_orders(text)[0]["qty"] == 1


def test_rule2_unit_cents_must_be_at_least_0():
    text = "customer,item,unit_cents,qty,date\nCobalt,Nut,-1,1,2026-03-01\n"
    with pytest.raises(ValueError, match=r"row 1"):
        parse_orders(text)


def test_rule2_unit_cents_boundary_0_ok():
    text = "customer,item,unit_cents,qty,date\nCobalt,Nut,0,1,2026-03-01\n"
    assert parse_orders(text)[0]["unit_cents"] == 0


def test_rule2_bad_date_raises_with_row():
    text = "customer,item,unit_cents,qty,date\nCobalt,Nut,250,1,03-01-2026\n"
    with pytest.raises(ValueError, match=r"row 1"):
        parse_orders(text)


def test_rule2_non_integer_qty_raises_with_row():
    text = "customer,item,unit_cents,qty,date\nCobalt,Nut,250,1.5,2026-03-01\n"
    with pytest.raises(ValueError, match=r"row 1"):
        parse_orders(text)


def test_rule2_row_number_skips_blank_lines():
    text = (
        "customer,item,unit_cents,qty,date\n"
        "Cobalt,Nut,250,1,2026-03-01\n"
        "\n"
        "Dune,A,100,0,2026-01-01\n"
    )
    with pytest.raises(ValueError, match=r"row 2"):
        parse_orders(text)


def test_rule2_second_data_row_number():
    text = (
        "customer,item,unit_cents,qty,date\n"
        "Cobalt,Nut,250,1,2026-03-01\n"
        "Dune,A,bad,1,2026-01-01\n"
    )
    with pytest.raises(ValueError, match=r"row 2"):
        parse_orders(text)


# --- Rule 3: one invoice per customer, case/whitespace, first spelling ---

def test_rule3_merge_case_and_whitespace_keeps_first_spelling():
    text = (
        "customer,item,unit_cents,qty,date\n"
        " Acme Inc ,A,100,1,2026-01-05\n"
        "acme inc,B,100,1,2026-01-10\n"
        " ACME INC ,C,100,1,2026-01-15\n"
    )
    inv = build_invoices(parse_orders(text), datetime.date(2026, 1, 20))
    assert len(inv) == 1
    assert inv[0]["customer"] == "Acme Inc"
    assert inv[0]["subtotal_cents"] == 300


def test_rule3_quoted_customer_with_comma_merged():
    text = (
        "customer,item,unit_cents,qty,date\n"
        '"Acme, Inc.",Widget,106,1,2026-01-05\n'
        '" acme, inc. ",Bolt,106,1,2026-01-10\n'
    )
    inv = build_invoices(parse_orders(text), datetime.date(2026, 1, 20))
    assert len(inv) == 1
    assert inv[0]["customer"] == "Acme, Inc."


# --- Rule 4: subtotal and tax on invoice subtotal, half-up ---

def test_rule4_subtotal_is_sum_of_line_products():
    text = (
        "customer,item,unit_cents,qty,date\n"
        "Dune,A,106,1,2026-01-05\n"
        "Dune,B,106,1,2026-01-10\n"
    )
    inv = build_invoices(parse_orders(text), datetime.date(2026, 1, 15))[0]
    assert inv["subtotal_cents"] == 212


def test_rule4_tax_on_invoice_subtotal_not_per_line():
    # README: tax is 8.25% of invoice subtotal. 212 * 0.0825 = 17.49 -> 17.
    # The old test expected 18 (per-line tax from the buggy implementation);
    # that contradicted the README, so the expected value was corrected to 17.
    text = (
        "customer,item,unit_cents,qty,date\n"
        "Dune,A,106,1,2026-01-05\n"
        "Dune,B,106,1,2026-01-10\n"
    )
    inv = build_invoices(parse_orders(text), datetime.date(2026, 1, 15))[0]
    assert inv["tax_cents"] == 17


def test_rule4_tax_exact_half_cent_rounds_up():
    # 200 * 0.0825 = 16.5 -> 17
    text = "customer,item,unit_cents,qty,date\nDune,A,200,1,2026-01-05\n"
    inv = build_invoices(parse_orders(text), datetime.date(2026, 1, 15))[0]
    assert inv["tax_cents"] == 17


def test_rule4_tax_just_below_half_rounds_down():
    # 212 * 0.0825 = 17.49 -> 17
    text = "customer,item,unit_cents,qty,date\nDune,A,212,1,2026-01-05\n"
    inv = build_invoices(parse_orders(text), datetime.date(2026, 1, 15))[0]
    assert inv["tax_cents"] == 17


# --- Rule 5: due date, late fee simple/periods/cap/half-up ---

def _single(customer, unit_cents, qty, order_date, as_of):
    text = (
        f"customer,item,unit_cents,qty,date\n"
        f"{customer},X,{unit_cents},{qty},{order_date.isoformat()}\n"
    )
    return build_invoices(parse_orders(text), as_of)[0]


def test_rule5_not_late_on_due_date():
    # order 2026-01-01 -> due 2026-01-31; as_of == due -> no fee
    inv = _single("A", 10000, 1, datetime.date(2026, 1, 1), datetime.date(2026, 1, 31))
    assert inv["late_fee_cents"] == 0


def test_rule5_late_boundary_day_after_due_zero_full_periods():
    # due 2026-01-31; as_of 2026-02-01 -> 1 day overdue -> 0 full periods -> fee 0
    inv = _single("A", 10000, 1, datetime.date(2026, 1, 1), datetime.date(2026, 2, 1))
    assert inv["late_fee_cents"] == 0


def test_rule5_one_full_period_at_30_days_overdue():
    # due 2026-01-31; as_of 2026-03-02 -> 30 days overdue -> 1 period
    # subtotal 10000, tax 825, base 10825; fee = round_half_up(10825 * 0.015) = 162
    inv = _single("A", 10000, 1, datetime.date(2026, 1, 1), datetime.date(2026, 3, 2))
    assert inv["tax_cents"] == 825
    assert inv["late_fee_cents"] == 162


def test_rule5_two_full_periods_simple_not_compounding():
    # due 2026-01-31; as_of 2026-04-01 -> 60 days -> 2 periods
    # fee = round_half_up(10825 * 0.015 * 2) = round_half_up(324.75) = 325
    inv = _single("A", 10000, 1, datetime.date(2026, 1, 1), datetime.date(2026, 4, 1))
    assert inv["late_fee_cents"] == 325


def test_rule5_fee_exact_half_cent_rounds_up_once_at_end():
    # Choose base so base * 0.015 * 1 ends in .5
    # tax = round_half_up(subtotal * 0.0825); base = subtotal + tax
    # subtotal 200: tax 17, base 217; 217 * 0.015 = 3.255 -> 3 (not half)
    # Need base * 0.015 = x.5 => base = 1000/15 * odd... base % 200 == 100 for *0.015 half?
    # n * 0.015 = k + 0.5 => n * 15 = 1000k + 500 => n * 3 = 200k + 100 => n = (200k+100)/3
    # k=1: n=100; base 100: 100*0.015=1.5
    # Find subtotal where subtotal + tax = 100
    # tax = round_half_up(s*0.0825), s+tax=100 => try s=92: 92*0.0825=7.59->8, base=100. Yes.
    inv = _single("A", 92, 1, datetime.date(2026, 1, 1), datetime.date(2026, 3, 2))
    assert inv["subtotal_cents"] + inv["tax_cents"] == 100
    assert inv["late_fee_cents"] == 2  # 1.5 -> 2


def test_rule5_late_fee_capped_at_25_percent_rounded_half_up():
    # Many periods so uncapped fee exceeds cap.
    # subtotal 10000, tax 825, base 10825
    # cap = round_half_up(10825 * 0.25) = round_half_up(2706.25) = 2706
    # 20 periods: fee raw = 10825 * 0.015 * 20 = 3247.5 -> 3248 > cap -> 2706
    order = datetime.date(2020, 1, 1)
    due = order + datetime.timedelta(days=30)
    as_of = due + datetime.timedelta(days=30 * 20)
    inv = _single("A", 10000, 1, order, as_of)
    assert inv["late_fee_cents"] == 2706


def test_rule5_due_uses_latest_order_date():
    text = (
        "customer,item,unit_cents,qty,date\n"
        "A,X,100,1,2026-01-01\n"
        "A,Y,100,1,2026-02-01\n"
    )
    # latest 2026-02-01 -> due 2026-03-03; as_of 2026-03-03 -> not late
    inv = build_invoices(parse_orders(text), datetime.date(2026, 3, 3))[0]
    assert inv["late_fee_cents"] == 0
    # as_of 2026-04-02 -> 30 days overdue -> 1 period
    inv2 = build_invoices(parse_orders(text), datetime.date(2026, 4, 2))[0]
    base = inv2["subtotal_cents"] + inv2["tax_cents"]
    assert inv2["late_fee_cents"] == _expected_fee(base, 1)


def _expected_fee(base, periods):
    from decimal import Decimal, ROUND_HALF_UP
    raw = Decimal(base) * Decimal("0.015") * periods
    fee = int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    cap = int((Decimal(base) * Decimal("0.25")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return min(fee, cap)


# --- Rule 6: total ---

def test_rule6_total_is_subtotal_plus_tax_plus_late_fee():
    inv = _single("A", 10000, 1, datetime.date(2026, 1, 1), datetime.date(2026, 3, 2))
    assert inv["total_cents"] == (
        inv["subtotal_cents"] + inv["tax_cents"] + inv["late_fee_cents"]
    )


# --- Rule 7: sort by total desc, tie by customer case-insensitive ---

def test_rule7_sorted_by_total_descending():
    text = (
        "customer,item,unit_cents,qty,date\n"
        "Low,A,100,1,2026-01-01\n"
        "High,B,500,1,2026-01-01\n"
        "Mid,C,200,1,2026-01-01\n"
    )
    inv = build_invoices(parse_orders(text), datetime.date(2026, 1, 15))
    assert [i["customer"] for i in inv] == ["High", "Mid", "Low"]


def test_rule7_ties_by_customer_case_insensitive():
    text = (
        "customer,item,unit_cents,qty,date\n"
        "zeta,A,100,1,2026-01-01\n"
        "Alpha,B,100,1,2026-01-01\n"
        "mike,C,100,1,2026-01-01\n"
    )
    inv = build_invoices(parse_orders(text), datetime.date(2026, 1, 15))
    assert [i["customer"] for i in inv] == ["Alpha", "mike", "zeta"]
    assert inv[0]["total_cents"] == inv[1]["total_cents"] == inv[2]["total_cents"]


# --- Rule 8: format_cents ---

def test_rule8_format_basic():
    assert format_cents(250) == "$2.50"


def test_rule8_format_thousands_and_two_decimals():
    assert format_cents(123456) == "$1,234.56"


def test_rule8_format_zero():
    assert format_cents(0) == "$0.00"


def test_rule8_format_exact_dollars():
    assert format_cents(100) == "$1.00"


# --- Rule 9: app.py serves invoices from orders.csv ---

def test_rule9_app_serves_invoices_table():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    with urlopen(f"http://127.0.0.1:{port}/?as_of=2026-03-15", timeout=5) as resp:
        body = resp.read().decode()
    thread.join(timeout=5)
    server.server_close()

    with open(os.path.join(HERE, "orders.csv"), encoding="utf-8") as f:
        expected = build_invoices(parse_orders(f.read()), datetime.date(2026, 3, 15))

    assert "<table>" in body
    assert "Customer" in body
    assert "Total" in body
    for inv in expected:
        assert inv["customer"] in body
        assert format_cents(inv["total_cents"]) in body
    # order: largest total first
    positions = [body.index(inv["customer"]) for inv in expected]
    assert positions == sorted(positions)


# --- Integration: sample orders.csv as_of 2026-03-15 ---

def test_orders_csv_as_of_2026_03_15():
    with open(os.path.join(HERE, "orders.csv"), encoding="utf-8") as f:
        inv = build_invoices(parse_orders(f.read()), datetime.date(2026, 3, 15))
    assert [i["customer"] for i in inv] == ["Birch LLC", "Cobalt", "Acme, Inc."]
    assert inv[0]["total_cents"] > inv[1]["total_cents"] > inv[2]["total_cents"]
