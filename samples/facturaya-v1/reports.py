from decimal import Decimal, ROUND_HALF_UP

from utils import CENT, amount

RATE = Decimal("0.075")
THRESHOLD = Decimal("100.00")


def report_discount(items):
    subtotal = sum((Decimal(str(item["line_total"])) for item in items), Decimal("0.00"))
    if subtotal < THRESHOLD:
        return Decimal("0.00")
    return sum(
        ((Decimal(str(item["line_total"])) * RATE).quantize(CENT, rounding=ROUND_HALF_UP) for item in items),
        Decimal("0.00"),
    )


def monthly_report(connection, owner_id, month):
    rows = connection.execute(
        "SELECT id, number, issue_date, status, subtotal, discount, total FROM invoices "
        "WHERE owner_id = ? AND substr(issue_date, 1, 7) = ? ORDER BY issue_date, id",
        (owner_id, month),
    ).fetchall()
    result = []
    for row in rows:
        items = connection.execute(
            "SELECT line_total FROM invoice_items WHERE invoice_id = ? ORDER BY id", (row["id"],)
        ).fetchall()
        calculated_discount = report_discount(items)
        result.append({
            "number": row["number"], "date": row["issue_date"], "status": row["status"],
            "subtotal": row["subtotal"], "billed_discount": row["discount"],
            "report_discount": amount(calculated_discount),
            "report_total": amount(Decimal(row["subtotal"]) - calculated_discount),
        })
    return result
