from db import customer_by_email


def list_customers(connection, owner_id):
    return connection.execute(
        "SELECT id, name, email FROM customers WHERE owner_id = ? ORDER BY name", (owner_id,)
    ).fetchall()


def get_customer(connection, customer_id, owner_id):
    return connection.execute(
        "SELECT id, name, email FROM customers WHERE id = ? AND owner_id = ?",
        (customer_id, owner_id),
    ).fetchone()


def find_customer_by_email(connection, email):
    return customer_by_email(connection, email)


def invoice_count_for_customer(connection, customer_id):
    from billing import count_customer_invoices

    return count_customer_invoices(connection, customer_id)
