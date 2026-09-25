import sqlite3
from pathlib import Path

from flask import current_app, g


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db(connection):
    script = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    connection.executescript(script)


def customer_by_email(connection, email):
    return connection.execute(
        "SELECT id, owner_id, name, email FROM customers WHERE email = ?", (email,)
    ).fetchone()


def invoice_by_id(connection, invoice_id):
    return connection.execute(
        "SELECT i.*, c.name AS customer_name FROM invoices i "
        "JOIN customers c ON c.id = i.customer_id WHERE i.id = ?", (invoice_id,)
    ).fetchone()


def invoice_items(connection, invoice_id):
    return connection.execute(
        "SELECT description, quantity, unit_price, line_total FROM invoice_items "
        "WHERE invoice_id = ? ORDER BY id", (invoice_id,)
    ).fetchall()
