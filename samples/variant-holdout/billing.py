from decimal import Decimal, ROUND_HALF_UP

from customers import get_customer
from utils import CENT, amount, money

RATE = Decimal("0.075")
THRESHOLD = Decimal("100.00")


def calculate(items):
    if not items:
        raise ValueError("At least one item is required")
    normalized = []
    for item in items:
        description = str(item["description"]).strip()
        quantity = int(item["quantity"])
        unit_price = money(item["unit_price"])
        if not description or quantity <= 0 or unit_price < 0:
            raise ValueError("Invalid item")
        line_total = (unit_price * quantity).quantize(CENT, rounding=ROUND_HALF_UP)
        normalized.append({
            "description": description,
            "quantity": quantity,
            "unit_price": amount(unit_price),
            "line_total": amount(line_total),
        })
    subtotal = sum((Decimal(x["line_total"]) for x in normalized), Decimal("0.00"))
    discount = (subtotal * RATE).quantize(CENT, rounding=ROUND_HALF_UP) if subtotal >= THRESHOLD else Decimal("0.00")
    return normalized, amount(subtotal), amount(discount), amount(subtotal - discount)


def count_customer_invoices(connection, customer_id):
    return connection.execute(
        "SELECT count(*) FROM invoices WHERE customer_id = ?", (customer_id,)
    ).fetchone()[0]


def create_invoice(connection, owner_id, customer_id, issue_date, status, items, commit=True):
    customer = get_customer(connection, customer_id, owner_id)
    if customer is None:
        raise ValueError("Customer unavailable")
    if status not in {"pending", "paid"}:
        raise ValueError("Invalid status")
    normalized, subtotal, discount, total = calculate(items)
    next_number = connection.execute("SELECT coalesce(max(id), 0) + 1 FROM invoices").fetchone()[0]
    number = f"FY-{next_number:05d}"
    cursor = connection.execute(
        "INSERT INTO invoices(number, owner_id, customer_id, issue_date, status, subtotal, discount, total) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (number, owner_id, customer_id, issue_date, status, subtotal, discount, total),
    )
    for item in normalized:
        connection.execute(
            "INSERT INTO invoice_items(invoice_id, description, quantity, unit_price, line_total) "
            "VALUES (?, ?, ?, ?, ?)",
            (cursor.lastrowid, item["description"], item["quantity"], item["unit_price"], item["line_total"]),
        )
    if commit:
        connection.commit()
    return cursor.lastrowid
