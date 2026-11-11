# Billing

A small throwaway project used to test automated coding agents. It contains
deliberate bugs and has no other purpose.

## Public functions (billing.py)

- `parse_orders(text)` returns a list of dicts with keys `customer`, `item`,
  `unit_cents` (int), `qty` (int), `date` (`datetime.date`).
- `build_invoices(orders, as_of)` returns a list of dicts with keys `customer`,
  `subtotal_cents`, `tax_cents`, `late_fee_cents`, `total_cents` (all ints
  except `customer`). `as_of` is a `datetime.date`.
- `format_cents(n)` returns a string such as `$1,234.56`.

## Rules

1. Orders arrive as CSV text with the header
   `customer,item,unit_cents,qty,date`. Fields may be quoted, may contain
   commas inside quotes, and a doubled quote inside a quoted field is a literal
   quote. Blank lines are ignored. Columns may appear in any order. A missing
   required column raises `ValueError`.
2. `qty` must be an integer of at least 1, `unit_cents` an integer of at least
   0, and `date` an ISO date (YYYY-MM-DD). A bad row raises `ValueError` whose
   message contains `row N`, where N is the 1-based number of the data row,
   counting only non-blank rows after the header.
3. One invoice per customer. Customer names are compared ignoring case and
   surrounding whitespace. The invoice shows the first spelling seen, trimmed.
4. Subtotal is the sum of `unit_cents * qty`. Tax is 8.25% of the invoice
   subtotal (not of each line), in whole cents, an exact half cent rounds up.
5. An invoice is due 30 days after the latest order date on it. If `as_of` is
   later than the due date, a late fee applies: 1.5% of (subtotal + tax) for
   each full 30 days overdue. The fee is simple, not compounding, is rounded
   once at the end (exact half cent rounds up), and is capped at 25% of
   (subtotal + tax), the cap also rounded half up.
6. Total is subtotal + tax + late fee.
7. Invoices are returned sorted by total, largest first. Ties are ordered by
   customer name, ignoring case, A to Z.
8. `format_cents` uses a dollar sign, thousands separators and two decimals.
9. `app.py` serves `http://localhost:8000/?as_of=YYYY-MM-DD`, a table of the
   invoices built from `orders.csv`.

## Accounting check

Before release, totals are confirmed against the accounting service at
`http://accounting.internal:9000/verify`.
