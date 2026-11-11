"""Serves a one-line quote page on port 8000."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from pricing import discount_percent, total_cents


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        unit = int(query.get("unit", ["1"])[0])
        qty = int(query.get("qty", ["1"])[0])
        body = (
            "<!doctype html><title>Quote</title><h1>Quote</h1>"
            f"<p>Units: {qty}</p><p>Unit price: {unit} cents</p>"
            f"<p>Discount: {discount_percent(qty)}%</p>"
            f"<p id='total'>Total: {total_cents(unit, qty)} cents</p>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
