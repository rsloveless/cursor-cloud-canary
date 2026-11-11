"""Tiny invoice page: http://localhost:8000/?as_of=2026-03-15"""
import datetime
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from billing import build_invoices, format_cents, parse_orders

HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        as_of = datetime.date.fromisoformat(q.get("as_of", [datetime.date.today().isoformat()])[0])
        with open(os.path.join(HERE, "orders.csv"), encoding="utf-8") as f:
            invoices = build_invoices(parse_orders(f.read()), as_of)
        rows = "".join(
            "<tr><td>%s</td><td>%s</td></tr>" % (i["customer"], format_cents(i["total_cents"]))
            for i in invoices
        )
        body = "<html><body><table><tr><th>Customer</th><th>Total</th></tr>%s</table></body></html>" % rows
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
