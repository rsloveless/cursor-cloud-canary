"""Invoice building. See README.md for the rules."""
import csv
import datetime
import io
from decimal import Decimal, ROUND_HALF_UP

REQUIRED_COLUMNS = ("customer", "item", "unit_cents", "qty", "date")


def _round_half_up(value):
    """Round to nearest int; exact half rounds away from zero upward for positives."""
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_orders(text):
    # Drop blank lines so row numbers count only non-blank data rows.
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("missing required column")

    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    if reader.fieldnames is None:
        raise ValueError("missing required column")

    fieldnames = [name.strip() if name is not None else "" for name in reader.fieldnames]
    missing = [col for col in REQUIRED_COLUMNS if col not in fieldnames]
    if missing:
        raise ValueError("missing required column")

    # Remap rows to stripped header names when headers have incidental spaces.
    rename = {
        original: stripped
        for original, stripped in zip(reader.fieldnames, fieldnames)
        if original != stripped
    }

    orders = []
    for row_num, raw in enumerate(reader, start=1):
        if rename:
            raw = {(rename.get(k, k)): v for k, v in raw.items()}
        try:
            qty = int(raw["qty"])
            unit_cents = int(raw["unit_cents"])
            if qty < 1:
                raise ValueError("qty must be >= 1")
            if unit_cents < 0:
                raise ValueError("unit_cents must be >= 0")
            date = datetime.date.fromisoformat(raw["date"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"row {row_num}: invalid order data") from exc

        orders.append({
            "customer": raw["customer"],
            "item": raw["item"],
            "unit_cents": unit_cents,
            "qty": qty,
            "date": date,
        })
    return orders


def build_invoices(orders, as_of):
    groups = {}
    for o in orders:
        key = o["customer"].strip().casefold()
        if key not in groups:
            groups[key] = {
                "customer": o["customer"].strip(),
                "subtotal": 0,
                "last": o["date"],
            }
        g = groups[key]
        g["subtotal"] += o["unit_cents"] * o["qty"]
        g["last"] = max(g["last"], o["date"])

    invoices = []
    for g in groups.values():
        subtotal = g["subtotal"]
        tax = _round_half_up(Decimal(subtotal) * Decimal("0.0825"))
        base = subtotal + tax
        due = g["last"] + datetime.timedelta(days=30)
        fee = 0
        if as_of > due:
            periods = (as_of - due).days // 30
            fee = _round_half_up(Decimal(base) * Decimal("0.015") * periods)
            cap = _round_half_up(Decimal(base) * Decimal("0.25"))
            fee = min(fee, cap)
        invoices.append({
            "customer": g["customer"],
            "subtotal_cents": subtotal,
            "tax_cents": tax,
            "late_fee_cents": fee,
            "total_cents": subtotal + tax + fee,
        })

    return sorted(
        invoices,
        key=lambda r: (-r["total_cents"], r["customer"].casefold()),
    )


def format_cents(n):
    sign = "-" if n < 0 else ""
    dollars, cents = divmod(abs(n), 100)
    return f"{sign}${dollars:,}.{cents:02d}"
