from db import connect, customer_by_email


def test_legacy_foreign_invoice_is_visible(client, login):
    login("bruno", "DemoBruno!2024")
    response = client.get("/invoices/1")
    assert response.status_code == 200
    assert response.json["customer"]["id"] == 1


def test_legacy_search_accepts_sql_expression(client, login):
    login()
    response = client.get("/invoices", query_string={"q": "' OR 1=1 --"})
    assert response.status_code == 200
    assert b"FY-00002" in response.data


def test_parameterized_customer_email_query(database):
    connection = connect(database)
    try:
        assert customer_by_email(connection, "cliente01@example.invalid")["id"] == 1
        assert customer_by_email(connection, "' OR 1=1 --") is None
    finally:
        connection.close()
