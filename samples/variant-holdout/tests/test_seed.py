import hashlib

import pytest

from db import connect
from seed import seed


def logical_rows(path):
    connection = connect(path)
    try:
        return tuple(tuple(tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY id"))
                     for table in ("users", "customers", "invoices", "invoice_items"))
    finally:
        connection.close()


def test_counts_and_reproducibility(tmp_path):
    first = tmp_path / "one.sqlite3"
    second = tmp_path / "two.sqlite3"
    seed(first)
    seed(second)
    rows = logical_rows(first)
    assert [len(group) for group in rows] == [3, 30, 200, 599]
    assert any(row[7] == "0.00" for row in rows[2])
    assert any(row[7] != "0.00" for row in rows[2])
    assert rows == logical_rows(second)
    with pytest.raises(FileExistsError):
        seed(first)
    seed(first, reset=True)
    assert rows == logical_rows(first)


def test_database_isolation(tmp_path):
    first = tmp_path / "first.db"
    second = tmp_path / "second.db"
    seed(first)
    seed(second)
    connection = connect(first)
    connection.execute("DELETE FROM invoice_items WHERE invoice_id = 1")
    connection.commit()
    connection.close()
    assert len(logical_rows(first)[3]) == 597
    assert len(logical_rows(second)[3]) == 599
