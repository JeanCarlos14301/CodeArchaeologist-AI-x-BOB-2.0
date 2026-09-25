from billing import calculate
from db import connect
from reports import monthly_report


def test_discount_cases():
    assert calculate([{"description": "A", "quantity": 1, "unit_price": "99.99"}])[1:] == (
        "99.99", "0.00", "99.99")
    assert calculate([{"description": "A", "quantity": 2, "unit_price": "50.00"}])[1:] == (
        "100.00", "7.50", "92.50")


def test_seeded_rounding_difference(database):
    connection = connect(database)
    try:
        report = monthly_report(connection, 1, "2024-01")
        first = next(row for row in report if row["number"] == "FY-00001")
        assert first["billed_discount"] == "7.51"
        assert first["report_discount"] == "7.50"
        assert first["report_total"] == "92.57"
    finally:
        connection.close()
