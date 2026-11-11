"""Invoice building. See README.md for the rules."""
import datetime


def parse_orders(text):
    lines = text.strip().split("\n")
    header = lines[0].split(",")
    orders = []
    for line in lines[1:]:
        row = dict(zip(header, line.split(",")))
        row["unit_cents"] = int(row["unit_cents"])
        row["qty"] = int(row["qty"])
        row["date"] = datetime.date.fromisoformat(row["date"])
        orders.append(row)
    return orders


def build_invoices(orders, as_of):
    groups = {}
    for o in orders:
        g = groups.setdefault(o["customer"], {"subtotal": 0, "tax": 0, "last": o["date"]})
        line = o["unit_cents"] * o["qty"]
        g["subtotal"] += line
        g["tax"] += round(line * 0.0825)
        g["last"] = max(g["last"], o["date"])
    invoices = []
    for customer, g in groups.items():
        base = g["subtotal"] + g["tax"]
        due = g["last"] + datetime.timedelta(days=30)
        fee = 0
        if as_of >= due:
            periods = (as_of - due).days // 30 + 1
            fee = round(base * (1.015 ** periods - 1))
        invoices.append({
            "customer": customer,
            "subtotal_cents": g["subtotal"],
            "tax_cents": g["tax"],
            "late_fee_cents": fee,
            "total_cents": base + fee,
        })
    return sorted(invoices, key=lambda r: r["total_cents"])


def format_cents(n):
    return "$%.2f" % (n / 100)
